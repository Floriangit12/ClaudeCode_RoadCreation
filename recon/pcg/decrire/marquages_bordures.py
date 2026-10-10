"""Bordures et sol sous les marquages (description) : dégagement des marques au droit des bordures (IISR 7e partie,
art. 113-2 : espace non peint de 2u entre une ligne et la bordure) et marques posées hors chaussée.

Obstacles (sol surélevé, la face de bordure étant leur bord) :
- emprise pilote (zone_pilote.geojson) : surfaces v2 de la description (trottoir, espace vert, îlot, terre-plein, quai)
  et arêtes avant des bordures v2 hors abaissés franchissables (vue ≤ 0,02 m) ; côté haut à gauche de l'arête
  (face_vue « droite »), corps de bordure compris jusqu'à 0,30 m ;
- ailleurs : surfaces v1 (surfaces_2026) de mêmes classes et bâtiments ; leur contour porte les faces verticales des
  bordures v1 (paquet v1, layers/bordures.usdc : faces sur le contour des surfaces, écart médian 0 mm).
Distance signée sd d'un point : distance au bord d'obstacle le plus proche, négative dans l'obstacle.
Règles (degager) :
- ligne / transversale (échantillons de l'axe peint au pas de 0,05 m) :
  - le long d'un bord (|cos| ≥ 0,90 sur ≥ 0,5 m) : l'axe est décalé vers la chaussée pour que le bord peint soit à
    2u du bord d'obstacle (décalage constant ≤ 0,25 m ; ancrage xodr : t_off, axe propre : polyligne décalée) ;
    position latérale levée (axe GAM, t_off pris sur le levé, ajout GAM) : décalage limité à un dégagement de 0,02 m
    (le levé prime sur la règle, écart noté dans ecarts_iisr) ;
  - en travers (bout de ligne contre la bordure, ligne qui franchit un obstacle) : interruption sur l'étendue où le
    bout peint (demi-largeur projetée) est à moins de 2u (interruptions_bordures) ;
  - ligne entièrement dans un obstacle : retirée (arête de bordure ou de surface lue comme une ligne sur l'ortho) ;
- passages, symboles paramétriques, zones, fantômes : découpes = rectangles posés sur le bord d'obstacle décalé de 2u
  vers la chaussée, du côté de l'obstacle (decoupes [{motif, obstacle, degagement_m, polygone_l93}]), retirés à la
  fabrication ; flèches, figurines et glyphes (gabarits) : jamais coupés, déplacés le long de leur cap (≤ 0,6 m) ou
  signalés ;
- marque entièrement dans un obstacle : retirée.
"""
import collections
import copy
import functools
import json
import math

import numpy as np

import marquages_commun as M
from commun import (DONNEES, SORTIE, ZONE, abscisses, anneaux, dans_polygone, decaler, distance_segments, lire_geojson,
                    point_a, repere)

DEGAGEMENT_U = 2              # espace non peint (en u) entre une marque et le bord d'un obstacle
DEGAGEMENT_LEVE = 0.02        # dégagement minimal d'une ligne dont la position latérale est levée (m)
VUE_MIN = 0.02                # bordure franchissable (abaissé de traversée) en dessous
CORPS = 0.30                  # profondeur du corps de bordure v2 côté haut (m)
CORPS_PASSAGE = 2.0           # passages : tout le côté haut d'une bordure v2 (sur 2 m) est obstacle (bande arrêtée à la bordure)
PARALLELE = 0.90              # |cos| minimal ligne / bord : conflit « le long »
ARETE_PRISE = 0.06            # axe lu sur l'ortho à moins de 6 cm d'une arête sur 60 % de sa longueur : arête prise pour une ligne
DECALAGE_MAX = 0.25           # décalage latéral maximal d'une ligne (m)
DECALAGE_LEVE = 0.03          # décalage latéral maximal d'une ligne dont la position latérale est levée (m)
DEPLACEMENT_MAX = 0.60        # déplacement maximal d'un gabarit le long de son cap (m)
CLASSES_V2 = ("trottoir", "espace_vert", "ilot", "terre_plein_vegetal", "quai_bus")
CLASSES_V1 = ("trottoir", "espace_vert", "ilot", "terre_plein_vegetal", "quai_bus", "batiment")
VEGETAL = {"espace_vert", "terre_plein_vegetal"}


@functools.lru_cache(maxsize=None)
def emprise_pilote():
    f = lire_geojson(ZONE)[0]
    return [repere(np.asarray(r, float)[:, :2]) for r in anneaux(f["geometry"])[0]]


def dans_pilote(Q):
    return dans_polygone(np.atleast_2d(Q), emprise_pilote())


@functools.lru_cache(maxsize=None)
def obstacles():
    """Polygones surélevés et segments de bord, par emprise (pilote : v2 ; ailleurs : v1).
    -> {"pilote"|"hors": {"polys": [(id, classe, anneaux, bbox)], "A", "B" (segments), "id": [...], "face": bool[]}}."""
    out = {}
    zp = emprise_pilote()
    # --- v2
    polys, A, B, I, Fc, H = [], [], [], [], [], []
    for f in sorted(lire_geojson(SORTIE / "base/surfaces.geojson"), key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p.get("classe") not in CLASSES_V2:
            continue
        for poly in anneaux(f["geometry"]):
            rs = [repere(r) for r in poly]
            polys.append((p["id"], p["classe"], rs, (*rs[0].min(axis=0), *rs[0].max(axis=0))))
            for r in rs:
                A.append(r)
                B.append(np.roll(r, -1, axis=0))
                I += [p["id"]] * len(r)
                Fc += [False] * len(r)
                H += [0.0] * len(r)
    for f in sorted(lire_geojson(SORTIE / "base/bordures.geojson"), key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        P = repere(np.asarray(f["geometry"]["coordinates"], float)[:, :2])
        S = abscisses(P)
        ferme = [(a["s0"], a["s1"]) for a in p.get("abaisses", []) if (a.get("vue_m") if a.get("vue_m") is not None else 1) <= VUE_MIN]
        ferme += [(it["s0"], it["s1"]) for it in p.get("intervalles", []) if (it.get("vue_m") or 0) <= VUE_MIN]
        mil = 0.5 * (S[:-1] + S[1:])
        ok = np.array([not any(a <= x <= b for a, b in ferme) for x in mil], bool)
        haut = 1.0 if p.get("face_vue", "droite") == "droite" else -1.0
        seg = P[1:] - P[:-1]
        n = np.c_[-seg[:, 1], seg[:, 0]] / np.maximum(np.hypot(*seg.T), 1e-12)[:, None] * haut
        for k in np.where(ok)[0]:
            a, b = P[k], P[k + 1]
            r = np.array([a, b, b + n[k] * CORPS, a + n[k] * CORPS])
            if haut < 0:
                r = r[::-1]
            polys.append((p["id"], "bordure", [r], (*r.min(axis=0), *r.max(axis=0))))
            A.append(P[k:k + 1])
            B.append(P[k + 1:k + 2])
            I.append(p["id"])
            Fc.append(True)
            H.append(haut)
    out["pilote"] = {"polys": polys, "A": np.vstack(A), "B": np.vstack(B), "id": I, "face": np.array(Fc, bool)}
    # passages de la zone pilote : seules les bordures comptent (les trottoirs v2 couvrent les abaissés et les plateaux) ;
    # côté haut sur CORPS_PASSAGE : une bande qui franchit la bordure est arrêtée devant elle
    fc = np.array(Fc, bool)
    out["pilote_bordures"] = {"polys": [], "A": np.vstack(A)[fc], "B": np.vstack(B)[fc],
                              "id": [i for i, f in zip(I, Fc) if f], "face": fc[fc], "haut": np.array([h for h, f in zip(H, Fc) if f])}
    # toutes les arêtes avant v2, abaissés compris (arête de bordure prise pour une ligne)
    AA, BB, II = [], [], []
    for f in sorted(lire_geojson(SORTIE / "base/bordures.geojson"), key=lambda f: f["properties"]["id"]):
        P = repere(np.asarray(f["geometry"]["coordinates"], float)[:, :2])
        AA.append(P[:-1])
        BB.append(P[1:])
        II += [f["properties"]["id"]] * (len(P) - 1)
    out["aretes_v2"] = {"A": np.vstack(AA), "B": np.vstack(BB), "id": II}
    # --- v1
    polys, A, B, I = [], [], [], []
    for f in sorted(lire_geojson(DONNEES / "surfaces/surfaces_2026.geojson"), key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p.get("classe") not in CLASSES_V1:
            continue
        for poly in anneaux(f["geometry"]):
            rs = [repere(r) for r in poly]
            polys.append((p["id"], p["classe"], rs, (*rs[0].min(axis=0), *rs[0].max(axis=0))))
            for r in rs:
                A.append(r)
                B.append(np.roll(r, -1, axis=0))
                I += [p["id"]] * len(r)
    out["hors"] = {"polys": polys, "A": np.vstack(A), "B": np.vstack(B), "id": I, "face": np.ones(sum(len(a) for a in A), bool)}
    return out


def _dedans(Q, polys):
    """Indice du premier obstacle contenant chaque point, −1 sinon."""
    res = np.full(len(Q), -1)
    lo, hi = Q.min(axis=0), Q.max(axis=0)
    for k, (_, _, rs, bb) in enumerate(polys):
        if bb[2] < lo[0] or bb[0] > hi[0] or bb[3] < lo[1] or bb[1] > hi[1]:
            continue
        m = res < 0
        if not m.any():
            break
        d = dans_polygone(Q[m], rs)
        res[np.where(m)[0][d]] = k
    return res


def distance_signee(Q, faces_seules=False):
    """Points Q (N, 2) -> (sd, vers_obstacle (N, 2) unitaire, tangente du bord (N, 2), obstacle (id, classe) par point).
    sd < 0 dans un obstacle ; inf loin (> 3 m) de tout obstacle ; faces_seules : dans l'emprise pilote, bordures v2
    seulement (passages : les trottoirs v2 couvrent les abaissés de traversée et les plateaux)."""
    Q = np.atleast_2d(np.asarray(Q, float))
    n = len(Q)
    sd = np.full(n, np.inf)
    vo = np.zeros((n, 2))
    tg = np.zeros((n, 2))
    ob = [None] * n
    pil = dans_pilote(Q)
    O = obstacles()
    for cle, m in (("pilote_bordures" if faces_seules else "pilote", pil), ("hors", ~pil)):
        if not m.any():
            continue
        q = Q[m]
        o = O[cle]
        lo, hi = q.min(axis=0) - 3.0, q.max(axis=0) + 3.0
        A, B = o["A"], o["B"]
        sel = ~((np.maximum(A[:, 0], B[:, 0]) < lo[0]) | (np.minimum(A[:, 0], B[:, 0]) > hi[0])
                | (np.maximum(A[:, 1], B[:, 1]) < lo[1]) | (np.minimum(A[:, 1], B[:, 1]) > hi[1]))
        if not sel.any():
            continue
        idx = np.where(sel)[0]
        d, j, pr = distance_segments(q, A[idx], B[idx])
        j = idx[j]
        t = B[j] - A[j]
        t /= np.maximum(np.hypot(*t.T), 1e-12)[:, None]
        if cle == "pilote_bordures":
            # côté haut d'une arête avant (face_vue « droite » : à gauche), projection à l'intérieur du segment, à moins de
            # CORPS_PASSAGE : dans la bordure (pas d'éventail sur les arcs ni de débord sur les abaissés voisins)
            L = np.maximum(np.hypot(*(B[j] - A[j]).T), 1e-12)
            u_ = ((q - A[j]) * (B[j] - A[j])).sum(axis=1) / (L * L)
            cr = t[:, 0] * (q - A[j])[:, 1] - t[:, 1] * (q - A[j])[:, 0]
            dd = np.where((u_ > 1e-6) & (u_ < 1 - 1e-6) & (cr * o["haut"][j] > 0) & (d < CORPS_PASSAGE), 0, -1)
        else:
            dd = _dedans(q, o["polys"])
        v = pr - q
        nv = np.hypot(*v.T)
        v = np.where(nv[:, None] > 1e-9, v / np.maximum(nv, 1e-12)[:, None], np.c_[-t[:, 1], t[:, 0]])
        ins = dd >= 0
        v[ins] = -v[ins]
        s = np.where(ins, -d, d)
        s = np.where(d > 3.0, np.inf, s)
        w = np.where(m)[0]
        sd[w], vo[w], tg[w] = s, v, t
        for k, i in enumerate(w):
            if np.isfinite(s[k]):
                if cle == "pilote_bordures":
                    ob[i] = (o["id"][j[k]], "bordure") if dd[k] >= 0 else (o["id"][j[k]], None)
                else:
                    ob[i] = (o["polys"][dd[k]][0], o["polys"][dd[k]][1]) if dd[k] >= 0 else (o["id"][j[k]], None)
    return sd, vo, tg, ob


def aretes_proches(Q):
    """Distance, tangente et identifiant de l'arête la plus proche (arêtes avant v2 abaissés compris et bords des
    surfaces v2 dans l'emprise pilote, bords d'obstacles v1 ailleurs)."""
    Q = np.atleast_2d(np.asarray(Q, float))
    d = np.full(len(Q), np.inf)
    tg = np.zeros((len(Q), 2))
    ids = [None] * len(Q)
    pil = dans_pilote(Q)
    O = obstacles()
    for cle, m in (("aretes_v2", pil), ("pilote", pil), ("hors", ~pil)):
        if not m.any():
            continue
        o = O[cle]
        dd, j, _ = distance_segments(Q[m], o["A"], o["B"])
        t = o["B"][j] - o["A"][j]
        t /= np.maximum(np.hypot(*t.T), 1e-12)[:, None]
        w = np.where(m)[0]
        mieux = dd < d[w]
        d[w[mieux]] = dd[mieux]
        tg[w[mieux]] = t[mieux]
        for k in np.where(mieux)[0]:
            ids[w[k]] = o["id"][j[k]]
    return d, tg, ids


# --------------------------------------------------------------------------- lignes
def sur_sol_sureleve(e, Q, sd, ob, leve):
    """Marque posée pour moitié au moins sur un sol surélevé -> None (non) ou {"retire": raison} / {"support": note} :
    - marque d'un état 2022 dans l'emprise pilote (sol 2026 de la description) : supprimée par le réaménagement 2025 ;
    - marque levée (GAM), du plan 2025 ou symbole posé : gardée sur ce sol (piste, bande ou stationnement au niveau du
      trottoir), sans dégagement ;
    - sinon (ligne ou zone lue sur l'ortho 2022) : bord de bordure ou de surface pris pour une marque."""
    f_in = float((sd < 0).mean()) if len(sd) else 0.0
    if f_in < 0.5 or e["classe"] == "fantome":
        return None
    noms = ", ".join(sorted({f"{o[0]} ({o[1]})" for o in ob if o is not None and o[1]})[:3])
    if float(dans_pilote(Q).mean()) >= 0.5 and e.get("etat") in ("conserve", "refait_2025_identique") and not leve:
        return {"retire": f"marque de 2022 sur le sol 2026 {noms} ({f_in:.0%}) de la zone pilote : supprimée par le réaménagement de 2025"}
    classes = {o[1] for o in ob if o is not None and o[1]}
    if e.get("etat") == "neuf_2025" and not leve and classes and classes <= VEGETAL:
        # marque du plan 2025 sur un espace vert du sol v1 2025 : le sol du paquet n'a pas la piste ; peinte, elle serait sur
        # l'herbe -> gardée, non fabriquée
        return {"non_fabrique": f"marque du plan 2025 posée sur {noms} ({f_in:.0%}) du sol v1 : piste ou chaussée 2025 absente "
                                "du paquet (sol non à jour), marque gardée non fabriquée"}
    if leve or e.get("etat") == "neuf_2025" or e["classe"] in ("symbole", "fleche"):
        return {"support": f"posée sur {noms} ({f_in:.0%}) : piste, bande ou stationnement au niveau du trottoir "
                           f"({'levé GAM' if leve else ('plan 2025' if e.get('etat') == 'neuf_2025' else 'symbole posé')}) ; gardée sur ce sol"}
    return {"retire": f"{'axe' if e['classe'] in ('ligne', 'transversale') else 'marque'} dans {noms} ({f_in:.0%}, sol surélevé) : "
                      "bord de bordure ou de surface lu comme une marque sur l'ortho 2022"}


def _leve(e):
    """Position latérale levée (GAM) ?"""
    a = e.get("ancrage", {})
    if a.get("type") == "axe" and a.get("source") == "gam":
        return True
    if e.get("ajout"):
        return True
    ref = json.dumps(e.get("prov", {}).get("geometrie", {}), ensure_ascii=False)
    return a.get("type") == "xodr" and ("levé GAM" in ref or "tirets levés GAM" in ref)


def _echantillons(e, P, pas=0.05):
    from marquages_controles import _pieces
    q = dict(e, type="discontinue") if e["classe"] == "transversale" else e
    iv = _pieces(q, P)
    out_s = [np.arange(a, b + 1e-9, pas) if b - a > pas else np.array([a, b]) for a, b in iv]
    s = np.concatenate(out_s) if out_s else np.zeros(0)
    Q, T = point_a(P, s) if len(s) else (np.zeros((0, 2)), np.zeros((0, 2)))
    return s, Q, T


def _u(e):
    import marquages_lignes as LG
    piste = "chronovelo" in (e.get("groupe") or "") or e.get("role") == "rive_piste"
    return LG.u_itineraire(e.get("branche"), piste)


def degager_ligne(e, reseau_chaines):
    """Décalage latéral puis interruptions de bout d'une ligne / transversale -> journal (dict) ou None ; e modifiée.
    Renvoie {"retire": raison} si la ligne est entièrement dans un obstacle."""
    P = e["geom"][1]
    s, Q, T = _echantillons(e, P)
    if not len(s):
        return None
    sd, vo, tg, ob = distance_signee(Q)
    if not np.isfinite(sd).any():
        return None
    w = float(e["largeur_m"])
    u = _u(e)
    g2u = DEGAGEMENT_U * u
    journal = {}
    leve = _leve(e)
    sur = sur_sol_sureleve(e, Q, sd, ob, leve)
    if sur:
        return sur
    c = np.abs((T * tg).sum(axis=1))
    a = e.get("ancrage", {})
    if not leve and a.get("type") == "axe" and a.get("source") == "v1" and e["prov"]["geometrie"].get("src") == "ortho2022":
        da, ta, ia = aretes_proches(Q)
        sur = (da < ARETE_PRISE) & (np.abs((T * ta).sum(axis=1)) >= PARALLELE)
        if sur.mean() >= 0.6:
            noms = sorted({str(i) for k, i in enumerate(ia) if sur[k]})
            return {"retire": f"axe lu sur l'ortho 2022 à moins de {ARETE_PRISE * 100:.0f} cm de l'arête de {', '.join(noms[:3])} sur "
                              f"{sur.mean():.0%} de sa longueur : arête de bordure prise pour une ligne, pas un marquage"}
    g_par = DEGAGEMENT_LEVE if leve else g2u
    besoin = g_par + w / 2 - sd
    par = (c >= PARALLELE) & (besoin > 0.002)
    if par.sum() * 0.05 >= 0.5 and e["classe"] == "ligne":
        nl = np.c_[-T[:, 1], T[:, 0]]
        sens = float(np.sign(np.mean(np.einsum("ij,ij->i", nl[par], -vo[par]))))
        # position levée : décalage borné à DECALAGE_LEVE (tolérance du levé), le reste devient interruption
        dec = float(min(np.max(besoin[par]), DECALAGE_LEVE if leve else DECALAGE_MAX))
        if sens != 0 and dec > 0.002:
            dec = round(dec + 0.001, 3)
            avant = {k: copy.deepcopy(e[k]) for k in ("geom", "ancrage", "interruptions", "longueur_m", "prov")}
            _decaler(e, sens * dec, reseau_chaines)
            P2 = e["geom"][1]
            s2, Q2, T2 = _echantillons(e, P2)
            sd2, vo2, tg2, ob2 = distance_signee(Q2)
            c2 = np.abs((T2 * tg2).sum(axis=1))
            reste = (c2 >= PARALLELE) & (g_par + w / 2 - sd2 > 0.002)
            if reste.mean() > 0.10 and not leve:
                # un décalage constant ne dégage pas la ligne (bord courbe, obstacles des deux côtés) : annulé
                for k, v in avant.items():
                    e[k] = v
                journal["decalage_annule"] = {"decalage_m": round(sens * dec, 3), "reste_en_conflit": round(float(reste.mean()), 2)}
            else:
                journal["decalage_m"] = round(sens * dec, 3)
                journal["regle"] = ("dégagement 0,02 m (position levée GAM gardée)" if leve else f"dégagement 2u = {g2u:.2f} m")
                if leve and float(np.min(sd2[c2 >= PARALLELE] - w / 2)) < g2u if (c2 >= PARALLELE).any() else False:
                    e.setdefault("ecarts_iisr", []).append(
                        f"espace non peint de {max(0.0, float(np.min(sd2[c2 >= PARALLELE] - w / 2))):.2f} m entre la ligne et la bordure < 2u = "
                        f"{g2u:.2f} m : position levée GAM gardée")
                P, s, Q, T, sd, vo, tg, ob, c = P2, s2, Q2, T2, sd2, vo2, tg2, ob2, c2
    # interruptions : bout peint (demi-largeur projetée sur la normale du bord) à moins de 2u, ou parallèle restant
    reach = np.where(c >= PARALLELE, sd - w / 2, sd - (w / 2) * np.sqrt(np.maximum(0.0, 1.0 - c ** 2)))
    lim = np.where(c >= PARALLELE, g_par, g2u)
    conf = reach < lim - 1e-4
    if conf.any():
        L = float(abscisses(P)[-1])
        ks = np.where(conf)[0]
        iv = []
        deb = ks[0]
        for a, b in zip(ks[:-1], ks[1:]):
            if b != a + 1 or s[b] - s[a] > 0.051:
                iv.append((deb, a))
                deb = b
        iv.append((deb, ks[-1]))
        inter = []
        for i0, i1 in iv:
            a, b = float(s[i0]) - 0.05, float(s[i1]) + 0.05
            # extension jusqu'au bout de la partie peinte si le conflit la touche
            inter.append([round(max(0.0, a), 3), round(min(L, b), 3)])
        e["interruptions"] = _fusion(e.get("interruptions", []) + inter)
        e["interruptions_bordures"] = _fusion(e.get("interruptions_bordures", []) + inter)
        journal["interruptions"] = inter
        journal["obstacles"] = sorted({o[0] for k, o in enumerate(ob) if conf[k] and o is not None})
    return journal or None


def _fusion(iv):
    out = []
    for a, b in sorted([list(x) for x in iv]):
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _decaler(e, d, chaines):
    """Décale l'axe d'une ligne de d (> 0 à gauche du sens de l'axe)."""
    a = e["ancrage"]
    if a.get("type") == "xodr" and a.get("bords"):
        b0 = a["bords"][0]
        ch = chaines[(a["route"], round(float(b0["section_s"]), 3), int(b0["voie"]))]
        a["t_off_m"] = round(float(a["t_off_m"]) + d, 4)
        P = ch.axe(a["t_off_m"], a["s0"], a["s1"], profil=a.get("t_off_profil"))
    else:
        P = decaler(e["geom"][1], d)
    e["geom"] = ("LineString", M.douglas_peucker(P, 0.001))
    L = float(abscisses(e["geom"][1])[-1])
    k = L / max(e["longueur_m"], 1e-9)
    if abs(k - 1) > 1e-6:
        e["interruptions"] = [[round(x * k, 3), round(y * k, 3)] for x, y in e.get("interruptions", [])]
    e["longueur_m"] = round(L, 3)
    e.setdefault("prov", {}).setdefault("geometrie", {})
    e["prov"]["geometrie"] = dict(e["prov"]["geometrie"], ref=e["prov"]["geometrie"].get("ref", "") + f" ; décalée de {d:+.3f} m (dégagement de la bordure)")


# --------------------------------------------------------------------------- polygones
def _bord_polys(polys, pas=0.02):
    pts = []
    for poly in polys:
        for r in poly:
            r = np.asarray(r, float)
            R = np.vstack([r, r[:1]])
            for a, b in zip(R[:-1], R[1:]):
                n = max(1, int(math.ceil(np.hypot(*(b - a)) / pas)))
                pts.append(a + np.linspace(0, 1, n, endpoint=False)[:, None] * (b - a))
    return np.vstack(pts)


def decoupes(polys, g2u, faces_seules=False):
    """Découpes (local) le long des bords d'obstacle à moins de 2u des points de bord de la marque : rubans qui suivent le
    bord d'obstacle (projections des points en conflit), du bord décalé de 2u vers la chaussée jusqu'à 0,5 m au moins dans
    l'obstacle, prolongés de 0,15 m aux bouts -> [(obstacle, polygone (n, 2))]. Points regroupés par orientation du bord
    (± 10°) et côté de l'obstacle."""
    Q = _bord_polys(polys, 0.02)
    sd, vo, tg, ob = distance_signee(Q, faces_seules)
    conf = sd < g2u - 1e-4
    if not conf.any():
        return []
    out = []
    restants = np.where(conf)[0]
    while len(restants) and len(out) < 24:
        k0 = restants[0]
        t0 = tg[k0]
        v0 = vo[k0]
        meme = restants[(np.abs((tg[restants] * t0).sum(axis=1)) > math.cos(math.radians(10)))
                        & ((vo[restants] * v0).sum(axis=1) > 0.5)]
        p = Q[meme] + vo[meme] * sd[meme][:, None]          # points du bord d'obstacle
        x = p @ t0
        o = np.argsort(x, kind="stable")
        p, x = p[o], x[o]
        # morceaux continus le long du bord (écart < 0,30 m), sous-échantillonnés au pas de 5 cm ; décalages selon la
        # normale moyenne du groupe (bande sans repli)
        coupes = np.where(np.diff(x) > 0.30)[0]
        for i0, i1 in zip(np.r_[0, coupes + 1], np.r_[coupes, len(x) - 1]):
            pp, xx = p[i0:i1 + 1], x[i0:i1 + 1]
            garde = [0]
            for k in range(1, len(xx)):
                if xx[k] - xx[garde[-1]] >= 0.05:
                    garde.append(k)
            if garde[-1] != len(xx) - 1:
                garde.append(len(xx) - 1)
            pp = pp[garde]
            prof = float(max(0.5, np.max((Q[meme] - (pp.mean(axis=0) - v0 * g2u)) @ v0) + 0.2))
            a0, a1 = pp[0] - t0 * 0.15, pp[-1] + t0 * 0.15
            route = np.vstack([a0, pp, a1]) - v0 * g2u
            fond = (np.vstack([a0, pp, a1]) + v0 * prof)[::-1]
            out.append((ob[k0][0] if ob[k0] else None, np.vstack([route, fond])))
        restants = np.setdiff1d(restants, meme)
    return out


def deplacer_gabarit(e):
    """Gabarit (flèche, figurine, glyphe) à moins de 2u d'un obstacle : plus petit déplacement (le long du cap ≤
    DEPLACEMENT_MAX, en travers ≤ 0,3 m compté double, pas de 5 cm) qui le dégage -> (le long, travers) en m, None si rien à
    faire, (nan, nan) si impossible."""
    import marquages_reprises as RP
    polys = e["geom"][1]
    g2u = DEGAGEMENT_U * _u(e)
    Q = _bord_polys(polys, 0.04)
    sd, _, _, _ = distance_signee(Q)
    if not (sd < g2u - 1e-4).any():
        return None
    for a, b, v in RP.candidats(e["pose"]["cap_deg"], DEPLACEMENT_MAX, 0.3):
        sd2, _, _, _ = distance_signee(Q + v)
        if not (sd2 < g2u - 1e-4).any():
            return round(a, 3), round(b, 3)
    return float("nan"), float("nan")


def translater(e, v):
    """Translation (local) de la pose et de la géométrie d'une entité posée."""
    e["pose"]["origine_local"] = np.asarray(e["pose"]["origine_local"], float) + v
    e["geom"] = (e["geom"][0], [[np.asarray(r, float) + v for r in poly] for poly in e["geom"][1]])


# --------------------------------------------------------------------------- passe complète
def polygones_entite(e):
    """Polygones peints (local) d'une entité non linéaire de la description (avant conversion GeoJSON)."""
    if e["classe"] == "passage" and e["type"] == "zebra":
        A, B = e["geom"][1][:2]
        ax = (B - A) / max(float(np.hypot(*(B - A))), 1e-9)
        h = math.radians(e["cap_bandes_deg"])
        u = np.array([math.cos(h), math.sin(h)])
        n = np.array([-u[1], u[0]])
        out = []
        for k in range(int(e.get("nb_emplacements") or e["nb_bandes"])):
            if k in e.get("coupures", []):
                continue
            c = A + ax * k * e["pas_axe_m"]
            L, W = e["longueur_bande_m"], e["largeur_bande_m"]
            out.append([np.array([c - u * L / 2 - n * W / 2, c + u * L / 2 - n * W / 2, c + u * L / 2 + n * W / 2, c - u * L / 2 + n * W / 2])])
        return out
    if e["classe"] == "passage":
        out = []
        for fl in e["files"]:
            ax = np.vstack(fl["axe"])
            d = np.array([math.cos(math.radians(fl["cap_deg"])), math.sin(math.radians(fl["cap_deg"]))])
            pas = fl["pas_m"]
            nk = int(round(float(np.hypot(*(ax[-1] - ax[0]))) / pas)) + 1 if pas > 0 and len(ax) > 1 else 1
            if "gabarit" in fl:
                polys = M.gabarit(fl["gabarit"])
            else:
                tx, ty = fl["tuile_m"]["perp_file"], fl["tuile_m"]["le_long_file"]
                polys = [[np.array([[-tx / 2, -ty / 2], [tx / 2, -ty / 2], [tx / 2, ty / 2], [-tx / 2, ty / 2]])]]
            for k in range(nk):
                if k in fl.get("absents", []):
                    continue
                c = ax[0] + d * pas * k
                out += [[M.poser(r, c, fl["cap_deg"]) for r in poly] for poly in polys]
        return out
    t, g = e["geom"]
    if t in ("Polygon", "MultiPolygon"):
        return g
    return []


def _non_fabrique(e, raison, devenir):
    """Entité gardée dans la description mais non fabriquée (sol absent ou non à jour) : devenir garde_non_fabrique."""
    e["fabrication"] = {"statut": "non_fabrique", "raison": raison}
    for mq in e["lien_v1"]:
        devenir[mq] = ("garde_non_fabrique", e["id"], raison)


def degager(entites, reseau, devenir):
    """Passe de dégagement sur toutes les entités (modifiées sur place) -> (entités gardées, journal)."""
    import marquages_lignes as LG
    chaines = {}
    for ch in LG.chaines_reseau(reseau):
        for b in ch.bords:
            chaines[(ch.route, round(b.section_s, 3), b.voie)] = ch
    journal = {"lignes": {}, "decoupes": {}, "deplacements": {}, "retraits": {}, "sur_sol_sureleve": {}, "non_fabriques": {}, "non_resolus": []}
    gardees = []
    for e in sorted(entites, key=lambda e: e["id"]):
        g2u = DEGAGEMENT_U * _u(e)
        if (e.get("fabrication") or {}).get("statut") == "non_fabrique":
            gardees.append(e)                # gardée sans fabrication (sol absent) : rien à dégager
            continue
        if e["classe"] in ("ligne", "transversale"):
            j = degager_ligne(e, chaines)
            if j and "retire" in j:
                journal["retraits"][e["id"]] = j["retire"]
                for mq in e["lien_v1"]:
                    devenir[mq] = ("retire", None, j["retire"])
                continue
            if j and "support" in j:
                e["support_sol"] = j["support"]
                journal["sur_sol_sureleve"][e["id"]] = j["support"]
                gardees.append(e)
                continue
            if j and "non_fabrique" in j:
                _non_fabrique(e, j["non_fabrique"], devenir)
                journal["non_fabriques"][e["id"]] = j["non_fabrique"]
                gardees.append(e)
                continue
            if j:
                journal["lignes"][e["id"]] = j
            gardees.append(e)
            continue
        polys = polygones_entite(e)
        if not polys:
            gardees.append(e)
            continue
        Q = _bord_polys(polys, 0.05)
        fs = e["classe"] == "passage"
        sd, _, _, ob = distance_signee(Q, fs)
        sur = None if fs else sur_sol_sureleve(e, Q, sd, ob, _leve(e) or "gam" == (e.get("prov", {}).get("geometrie", {}).get("src")))
        if sur and "retire" in sur:
            journal["retraits"][e["id"]] = sur["retire"]
            for mq in e["lien_v1"]:
                devenir[mq] = ("retire", None, sur["retire"])
            continue
        if sur and "non_fabrique" in sur:
            _non_fabrique(e, sur["non_fabrique"], devenir)
            journal["non_fabriques"][e["id"]] = sur["non_fabrique"]
            gardees.append(e)
            continue
        if sur:
            e["support_sol"] = sur["support"]
            journal["sur_sol_sureleve"][e["id"]] = sur["support"]
            gardees.append(e)
            continue
        if e["classe"] in ("fleche",) or e.get("type") in ("velo", "pmr", "texte", "t_stationnement"):
            dd = deplacer_gabarit(e)
            if dd is not None and math.isfinite(dd[0]):
                import marquages_reprises as RP
                c = math.radians(e["pose"]["cap_deg"])
                RP._translater(e, dd[0] * np.array([math.cos(c), math.sin(c)]) + dd[1] * np.array([-math.sin(c), math.cos(c)]))
                e["deplacement_bordure_m"] = [dd[0], dd[1]]
                e.setdefault("prov", {})["pose"] = dict(e["prov"].get("pose", {"src": "regle:marquages_bordures"}),
                                                        ref=e["prov"].get("pose", {}).get("ref", "") + f" ; déplacée de {dd[0]:+.2f} m le long du cap et de "
                                                        f"{dd[1]:+.2f} m en travers (dégagement 2u de la bordure)")
                journal["deplacements"][e["id"]] = [dd[0], dd[1]]
            elif dd is not None:
                journal["non_resolus"].append([e["id"], "gabarit à moins de 2u d'une bordure, non dégageable par un déplacement ≤ 0,6 m"])
            gardees.append(e)
            continue
        dc = decoupes(polys, g2u, fs)
        if dc:
            e["decoupes"] = [{"motif": "degagement_bordure", "obstacle": o, "degagement_m": round(g2u, 3), "polygone_local": r} for o, r in dc]
            journal["decoupes"][e["id"]] = sorted({str(o) for o, _ in dc})
        gardees.append(e)
    return gardees, journal


if __name__ == "__main__":
    O_ = obstacles()
    print({k: (len(v["polys"]), len(v["A"])) for k, v in O_.items()})
