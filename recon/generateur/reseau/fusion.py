# -*- coding: utf-8 -*-
"""Fusion des tronçons aux nœuds de raccord (lot N1) : continuité « par construction » d'une route qui traverse un
nœud partagé sans carrefour (CHAINE_CONSTRUCTION P3, ruptures R-01, R-05, R-06, R-08).

Un nœud de valence 2 sans carrefour relie deux tronçons qui se suivent : ils deviennent UN tronçon (polyligne
continue ; profil du second posé en évènement « profil » à l'abscisse du raccord ; évènements et panneaux du second
décalés de la longueur du premier). À un nœud de valence ≥ 3 sans carrefour (divergence, convergence de bretelles),
seule la paire la mieux alignée (écart de cap ≤ 15°, et meilleure de 5° au moins que la suivante) est fusionnée ; les
autres tronçons gardent une limite de carte au nœud et sont rapportés (besoin B2 du lot B).
Un tronçon est retourné quand les deux arrivent tête-bêche et qu'il ne porte que des évènements retournables.
Utilisé par le résolveur (raccords internes à un site) et par la composition de sites.
"""
from __future__ import annotations

import copy
import math
import re
import sys
from pathlib import Path

GEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEN))
from description import description_vers_modele as D  # noqa: E402
from description import vocabulaire as V  # noqa: E402

SENS = {"gauche": "droite", "droite": "gauche"}


class ErreurFusion(ValueError):
    pass


def _r(x, nd=3):
    return round(float(x), nd) + 0.0


def _bas(x):
    return math.floor(float(x) * 1e6) / 1e6


def inverser_profil_texte(p: str) -> str:
    """Profil lu dans l'autre sens : éléments dans l'ordre inverse, flèches échangées, dévers changés de signe."""
    out = []
    for e in reversed([x.strip() for x in str(p).split("|")]):
        e = e.replace("<->", "\x02").replace("↔", "\x02")
        e = e.replace("←", "\x00").replace("<-", "\x00").replace("→", "←").replace("->", "←").replace("\x00", "→")
        e = e.replace("\x02", "↔")
        e = re.sub(r"(d[ée]vers\s+)(-?)(\d)", lambda m: m.group(1) + ("" if m.group(2) else "-") + m.group(3), e)
        out.append(e)
    return " | ".join(out)


def a_evenement(e):
    if isinstance(e, dict) and len(e) == 1:
        (_, prm), = e.items()
        if isinstance(prm, dict) and isinstance(prm.get("a"), (int, float)):
            return float(prm["a"])
        return None
    m = re.match(r"^\s*(?:à|a)?\s*(\d+(?:[.,]\d+)?)\s*m?\s*:", str(e))
    return float(m.group(1).replace(",", ".")) if m else None


def decaler_ev(e, ds: float):
    if isinstance(e, dict) and len(e) == 1:
        (typ, prm), = e.items()
        prm = dict(prm)
        if isinstance(prm.get("a"), (int, float)):
            prm["a"] = _r(prm["a"] + ds)
        return {typ: prm}
    m = re.match(r"^(\s*(?:à|a)?\s*)(\d+(?:[.,]\d+)?)(\s*m?\s*:.*)$", str(e), re.S)
    if not m:
        raise ErreurFusion(f"évènement sans abscisse lisible : « {e} »")
    v = float(m.group(2).replace(",", ".")) + ds
    return f"à {_r(v, 3):g}{m.group(3)}"


def longueur(t: dict, origine) -> float:
    return D.lire_trace(t, origine, str(t.get("id", "?"))).longueur


def cap_bout(t: dict, bout: str) -> float:
    pts = t["polyligne"] if t.get("polyligne") else [t["de"], t["vers"]]
    a, b = (pts[0], pts[1]) if bout == "de" else (pts[-2], pts[-1])
    c = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return c if bout == "vers" else (c + 180.0) % 360.0      # cap en arrivant au nœud (bout « vers ») / en repartant


def profil_texte(p):
    """Profil en ligne (« a | b | c ») ; une liste de textes est jointe ; une forme structurée (dicts) rend None."""
    if isinstance(p, str):
        return p
    if isinstance(p, list) and all(isinstance(x, str) for x in p):
        return " | ".join(x.strip() for x in p)
    return None


def contexte_effectif(t: dict) -> tuple:
    """Contexte comparable de deux tronçons : agglomération, vitesse, catégorie (vocabulaire du format, défaut « rue » en
    agglomération), u (m)."""
    c = dict(t.get("contexte") or {})
    agglo = V.booleen(c.get("agglomeration", "oui"), "contexte.agglomeration") if c.get("agglomeration") is not None else None
    v = c.get("vitesse", c.get("vitesse_kmh"))
    v = V.nombre(v, "contexte.vitesse") if v is not None else None
    cat = c.get("categorie")
    cat = V.CATEGORIES.get(V.norm(cat), V.norm(cat)) if cat is not None else ("rue" if agglo else None)
    u = c.get("u", c.get("u_m"))
    u = V.nombre(u, "contexte.u", "cm") if isinstance(u, str) and "cm" in u else (V.nombre(u, "contexte.u") if u is not None else None)
    return (agglo, v, cat, round(u, 4) if u is not None else None)


def inverser(t: dict, L: float) -> dict:
    """Tronçon parcouru dans l'autre sens ; ErreurFusion si un évènement ne se retourne pas sans perte. Les
    changements de profil (« profil » sans transition, « ouverture » vers l'avant, « fermeture ») sont retournés : une
    ouverture devient une fermeture et inversement, sur la même zone de transition."""
    t = copy.deepcopy(t)
    if "trace" in t or ("longueur" in t and "polyligne" not in t and "de" not in t):
        raise ErreurFusion("tracé en droites / arcs : retournement non porté")
    if t.get("polyligne"):
        t["polyligne"] = list(reversed(t["polyligne"]))
    else:
        t["de"], t["vers"] = t["vers"], t["de"]
    if t.get("objets") or t.get("vegetation"):
        raise ErreurFusion("objets ou végétation rattachés aux bandes : retournement non porté")
    base = profil_texte(t.get("profil"))
    if base is None:
        raise ErreurFusion("profil en forme structurée : retournement non porté")
    chg = []                          # (a, profil après, genre, longueur, raccord)
    autres = []
    for e in t.get("evenements") or []:
        if isinstance(e, dict) and len(e) == 1:
            (typ, prm), = e.items()
            if typ in ("profil", "ouverture", "fermeture") and isinstance(prm, dict) and isinstance(prm.get("nouveau"), str):
                if typ == "profil" and prm.get("transition"):
                    raise ErreurFusion("changement de profil avec transition : retournement non porté")
                if typ == "ouverture" and V.SENS.get(V.norm(str(prm.get("sens", "→")))) not in (None, "avant"):
                    raise ErreurFusion("ouverture vers l'arrière : retournement non porté")
                chg.append((float(prm["a"]), prm["nouveau"], typ, float(prm.get("longueur") or 0.0), prm.get("raccord")))
                continue
            if typ in ("passage_pieton", "dos_d_ane", "plateau", "plateau_pieton", "coussin", "panneau", "abaisse"):
                prm = dict(prm)
                prm["a"] = _r(L - float(prm["a"]))
                if "cote" in prm:
                    prm["cote"] = SENS.get(V.norm(prm["cote"]), prm["cote"])
                autres.append({typ: prm})
                continue
            raise ErreurFusion(f"évènement « {typ} » : retournement non porté")
        m = re.match(r"^\s*(?:à|a)?\s*(\d+(?:[.,]\d+)?)\s*m?\s*:\s*(.+)$", str(e))
        if m and re.match(r"^(passage|plateau|dos|coussin)", V.norm(m.group(2))) and not re.search(
                r"gauche|droite|→|←", m.group(2)):
            autres.append(f"à {_r(L - float(m.group(1).replace(',', '.')), 3):g} : {m.group(2)}")
            continue
        raise ErreurFusion(f"évènement « {e} » : retournement non porté")
    chg.sort(key=lambda x: x[0])
    profils = [base] + [x[1] for x in chg]            # profils[i] en vigueur après le i-ème changement
    t["profil"] = inverser_profil_texte(profils[-1])
    evs = []
    for i in range(len(chg) - 1, -1, -1):
        a, _, genre, lg, rac = chg[i]
        avant = inverser_profil_texte(profils[i])         # profil d'avant le changement, lu à l'envers
        if genre == "profil":
            evs.append({"profil": {"a": _r(L - a), "nouveau": avant}})
            continue
        neuf = {"ouverture": "fermeture", "fermeture": "ouverture"}[genre]
        prm = {"a": _bas(L - a + lg), "longueur": _r(lg), "nouveau": avant}
        if rac is not None:
            prm["raccord"] = rac
        evs.append({neuf: prm})
    t["evenements"] = sorted(evs + autres, key=lambda e: a_evenement(e) or 0.0)
    if not t["evenements"]:
        t.pop("evenements")
    sig = []
    for s in t.get("signalisation") or []:
        s = dict(s)
        if isinstance(s.get("a"), (int, float)):
            s["a"] = _r(L - float(s["a"]))
        if "cote" in s:
            s["cote"] = SENS.get(V.norm(s["cote"]), s["cote"])
        sig.append(s)
    if sig:
        t["signalisation"] = sig
    if isinstance(t.get("abords"), dict):
        t["abords"] = {SENS.get(k, k): v for k, v in t["abords"].items()}
    return t


def profil_fin(t: dict):
    """Texte du profil en vigueur au bout d'un tronçon (dernier changement « profil », « fermeture » ou « ouverture »
    vers l'avant) ; None si une voie est ajoutée ou retirée ensuite (rabattement, élargissement)."""
    dernier, a_der = profil_texte(t.get("profil")), -1.0
    for e in t.get("evenements") or []:
        if isinstance(e, dict) and len(e) == 1:
            (typ, prm), = e.items()
            if not isinstance(prm, dict) or not isinstance(prm.get("a"), (int, float)):
                continue
            if typ in ("profil", "fermeture") or (typ == "ouverture" and V.SENS.get(V.norm(str(prm.get("sens", "→")))) in (None, "avant")):
                if prm["a"] >= a_der and isinstance(prm.get("nouveau"), str):
                    dernier, a_der = prm["nouveau"], float(prm["a"])
    for e in t.get("evenements") or []:
        if isinstance(e, dict) and len(e) == 1:
            (typ, prm), = e.items()
            if typ in ("rabattement", "elargissement") and isinstance(prm, dict) and float(prm.get("a", 0)) >= a_der:
                return None
    return dernier


def fusionner(A: dict, B: dict, LA: float, noeud: str) -> tuple:
    """A (fin au nœud) + B (début au nœud) → (tronçon, pertes)."""
    M = copy.deepcopy(A)
    pa = A["polyligne"] if A.get("polyligne") else [A["de"], A["vers"]]
    pb = B["polyligne"] if B.get("polyligne") else [B["de"], B["vers"]]
    if math.dist(pa[-1], pb[0]) > 0.01:
        raise ErreurFusion(f"extrémités distantes de {math.dist(pa[-1], pb[0]):.3f} m au nœud {noeud}")
    for k in ("de", "vers"):
        M.pop(k, None)
    M["polyligne"] = pa + pb[1:]
    pertes = []
    if contexte_effectif(A) != contexte_effectif(B):
        raise ErreurFusion(f"contextes différents au nœud {noeud} ({A.get('contexte')} / {B.get('contexte')})")
    if (A.get("contexte") or {}) != (B.get("contexte") or {}):
        pertes.append(f"contexte de {B['id']} ({B.get('contexte')}) équivalent à celui de {A['id']} ({A.get('contexte')}) : "
                      "celui de A est gardé")
    for k in ("materiaux", "marquages", "confiance"):
        if A.get(k) != B.get(k):
            pertes.append(f"{k} de {B['id']} ({B.get(k)}) remplacés par ceux de {A['id']} ({A.get(k)})")
    if B.get("objets") or B.get("vegetation"):
        raise ErreurFusion(f"objets ou végétation de {B['id']} rattachés à ses bandes")
    if B.get("abords") and A.get("abords") != B.get("abords"):
        if A.get("abords"):
            pertes.append(f"abords de {B['id']} ({B['abords']}) remplacés par ceux de {A['id']}")
        else:
            M["abords"] = B["abords"]
            pertes.append(f"abords de {B['id']} ({B['abords']}) étendus à {A['id']}")
    if profil_texte(A.get("profil")) is None:
        raise ErreurFusion(f"profil de {A['id']} en forme structurée : fusion non portée")
    M["profil"] = profil_texte(A.get("profil"))
    evs = list(A.get("evenements") or [])
    if B.get("profil") is not None:
        pb_txt = profil_texte(B["profil"])
        if pb_txt is None:
            raise ErreurFusion(f"profil de {B['id']} en forme structurée : fusion non portée")
        if profil_fin(A) != pb_txt:
            # profil de B posé 1 mm avant le raccord : à abscisse égale, le compilateur garderait ce changement-ci et
            # perdrait une ouverture de raccord qui commence au début de B (max sur s0)
            evs.append({"profil": {"a": _r(LA - 0.001), "nouveau": pb_txt}})
    evs += [decaler_ev(e, LA) for e in (B.get("evenements") or [])]
    M["evenements"] = evs
    sig = list(A.get("signalisation") or []) + [dict(s, a=_r(float(s["a"]) + LA)) if isinstance(s.get("a"), (int, float))
                                                 else s for s in (B.get("signalisation") or [])]
    if sig:
        M["signalisation"] = sig
    if B.get("nom") and A.get("nom") != B.get("nom"):
        M["nom"] = f"{A.get('nom') or A['id']} / {B['nom']}"
    return M, pertes


def renommer_ref(o, ren: dict):
    """Références de tronçons dans un carrefour / giratoire / bretelle (« id », « id TD »)."""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k in ("troncon", "de", "vers", "principale", "bretelle") and isinstance(v, str):
                out[k] = ren.get(v, v)
            elif k in ("mouvements", "pietons") and isinstance(v, list):
                out[k] = [_renommer_mvt(x, ren) for x in v]
            elif k == "vehicule" and isinstance(v, dict):
                out[k] = {u: [_renommer_mvt(x, ren) for x in (lst or [])] for u, lst in v.items()}
            else:
                out[k] = renommer_ref(v, ren)
        return out
    if isinstance(o, list):
        return [renommer_ref(x, ren) for x in o]
    return o


def _renommer_mvt(x, ren):
    if not isinstance(x, str):
        return x
    p = x.split()
    if p and p[0] in ren:
        p[0] = ren[p[0]]
    return " ".join(p)


def fusionner_aux_noeuds(troncons: list, fins: dict, bloques: set, origine, objets: dict, rapport: dict) -> list:
    """troncons : liste de dicts (id, géométrie locale à `origine`, profil, évènements…) ; fins : nœud → [(id, bout)] ;
    bloques : nœuds qui sont des centres de carrefour. Modifie `objets` (références renommées) et `rapport`
    (« fusions », « noeuds_non_fusionnes ») ; rend la nouvelle liste de tronçons."""
    par_id = {t["id"]: t for t in troncons}
    ordre = [t["id"] for t in troncons]
    remplace = {}
    fus = rapport.setdefault("fusions", [])
    non = rapport.setdefault("noeuds_non_fusionnes", [])
    joints = {}

    def actuel(i):
        while i in remplace:
            i = remplace[i]
        return i

    for n in sorted(fins):
        if n in bloques:
            continue
        bouts = [(actuel(i), b) for i, b in fins[n]]
        if len(bouts) < 2:
            continue
        paires = []
        if len(bouts) == 2:
            tx, ty = par_id[bouts[0][0]], par_id[bouts[1][0]]
            ecart = abs(((cap_bout(tx, bouts[0][1]) - (cap_bout(ty, bouts[1][1]) + 180.0) % 360.0) + 180.0) % 360.0 - 180.0)
            if ecart > 30.0:
                non.append({"noeud": n, "raison": f"les deux tronçons ne se suivent pas (écart de cap {ecart:.0f}° : "
                            "divergence ou convergence, besoin B2)", "troncons": [i for i, _ in bouts]})
                continue
            paires = [(bouts[0], bouts[1], ecart)]
        else:
            # la paire la mieux alignée (continuité de cap au nœud) : arrivée d'un côté, départ de l'autre
            for i, x in enumerate(bouts):
                for y in bouts[i + 1:]:
                    tx, ty = par_id[x[0]], par_id[y[0]]
                    cx = cap_bout(tx, x[1])
                    cy = cap_bout(ty, y[1])
                    # deux bouts alignés : l'un arrive (cap c), l'autre repart (cap c) — caps « en arrivant »
                    ecart = abs(((cx - (cy + 180.0) % 360.0) + 180.0) % 360.0 - 180.0)
                    paires.append((x, y, ecart))
            paires.sort(key=lambda p: p[2])
            if not paires or paires[0][2] > 15.0 or (len(paires) > 1 and paires[1][2] - paires[0][2] < 5.0):
                non.append({"noeud": n, "raison": f"valence {len(bouts)} sans carrefour, aucune continuité nette "
                            "(divergence, convergence ou chaussées séparées : besoin B2)",
                            "troncons": [i for i, _ in bouts]})
                continue
            paires = paires[:1]
        (ia, ba), (ib, bb), _ = paires[0]
        autres = [i for i, _ in bouts if i not in (ia, ib)]
        if ia == ib:
            non.append({"noeud": n, "raison": "boucle", "troncons": [ia]})
            continue
        A, B = par_id[ia], par_id[ib]
        rev_a = rev_b = False
        try:
            LA, LB = longueur(A, origine), longueur(B, origine)
            if (ba, bb) == ("de", "vers"):
                A, B, ba, bb, LA, LB = B, A, bb, ba, LB, LA
            if (ba, bb) == ("vers", "vers"):
                try:
                    B, rev_b = inverser(B, LB), True
                except ErreurFusion:
                    A, B, LA, LB, rev_b = B, inverser(A, LA), LB, LA, True
            elif (ba, bb) == ("de", "de"):
                try:
                    A, rev_a = inverser(A, LA), True
                except ErreurFusion:
                    A, B, LA, LB, rev_a = inverser(B, LB), A, LB, LA, True
            M, pertes = fusionner(A, B, LA, n)
        except (ErreurFusion, D.ErreurDescription) as e:
            non.append({"noeud": n, "raison": str(e), "troncons": [ia, ib]})
            continue
        if autres:
            non.append({"noeud": n, "raison": f"valence {len(bouts)} : {A['id']} et {B['id']} fusionnés (continuité de "
                        "cap), les autres gardent une limite de carte au nœud (besoin B2)", "troncons": autres})
        # raccords déjà contenus dans A et B : abscisses ramenées dans le tronçon fusionné
        for k in joints.get(A["id"], []):
            if rev_a:
                fus[k]["s"] = _r(LA - fus[k]["s"], 3)
        for k in joints.get(B["id"], []):
            fus[k]["s"] = _r((LB - fus[k]["s"] if rev_b else fus[k]["s"]) + LA, 3)
        fus.append({"noeud": n, "troncons": [A["id"], B["id"]], "longueur_premier_m": _r(LA, 2), "s": _r(LA, 3),
                    "retournes": [x for x, r_ in ((A["id"], rev_a), (B["id"], rev_b)) if r_], "pertes": pertes})
        joints[A["id"]] = joints.get(A["id"], []) + joints.pop(B["id"], []) + [len(fus) - 1]
        par_id[A["id"]] = M
        par_id.pop(B["id"], None)
        remplace[B["id"]] = A["id"]
        ordre = [x for x in ordre if x != B["id"]]
        for cle in list(objets):
            objets[cle] = [renommer_ref(c, {B["id"]: A["id"]}) for c in objets[cle]]
    for tid, ks in joints.items():
        for k in ks:
            fus[k]["troncon_final"] = tid
    return [par_id[i] for i in ordre]
