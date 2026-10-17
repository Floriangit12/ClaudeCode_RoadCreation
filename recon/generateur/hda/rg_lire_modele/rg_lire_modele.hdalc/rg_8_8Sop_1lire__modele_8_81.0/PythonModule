"""rg::lire_modele : module Python embarqué (section PythonModule de l'HDA).

Seul code Python de conversion du générateur (README_HDA.md, préambule) : modèle `modele_voie/0.1` (JSON, Lambert-93)
-> géométrie Houdini Y haut avec attributs. Les coordonnées sont converties une seule fois : local = L93 −
repere.origine_l93, puis Houdini (x, z, −y). Aucune opération géométrique ici (abscisses, échantillonnage, décalages,
lois : HDA rg::graphe et rg::profils, en VEX) : on recopie les valeurs du modèle et on les range en attributs.

Points d'entrée (un par Python SOP interne, une sortie de l'HDA chacun) :
    lire_routes(sop)      1 routes : polyligne `ligne_reference.geometrie` + géométrie régulière et sections en tableaux
    lire_noeuds(sop)      2 nœuds (et carrefours rattachés) : points
    lire_zones(sop)       3 zones et îlots : polygones (anneau 0 extérieur, ≥ 1 trous)
    lire_ponctuels(sop)   4 objets, signaux, marquages : points (rattachement route / s / t, dimensions)
    lire_profils(sop)     5 profils : un point par profil (bandes, lois de largeur aplaties, limites)
Le modèle est lu une fois par fichier (cache : chemin, date, taille). Tout ce qui n'est pas pris en charge est une
erreur du nœud, jamais un silence : primitive parampoly3, interpolation « cubique_lisse » (non définie par le
schéma 0.1), transition d'entrée autre que « instantanee », surcharge de section non reconnue, profil inconnu. Les
familles du modèle qui ne servent pas avant les lots suivants (carrefours, ouvrages, contrôleurs, graphe de voies)
sont comptées dans le détail `rg_modele.non_lus` et signalées en avertissement.
"""
import copy
import hashlib
import json
import math
import os
import re

import hou

SCHEMA = "modele_voie/0.1"
CLES_RACINE = {"schema", "meta", "repere", "contexte", "profils", "noeuds", "routes", "carrefours", "ilots", "ouvrages",
               "signaux", "controleurs", "objets", "marquages", "zones", "graphe_voies"}
NON_LUS_L1 = ("carrefours", "ouvrages", "controleurs", "graphe_voies")
TYPES_GEO = {"droite": 0, "arc": 1, "clothoide": 2}
LOI_POINTS = {"lineaire": 1, "palier": 2}
_CACHE = {}


class ErreurModele(Exception):
    pass


# ----------------------------------------------------------------------------------------------- lecture
def _texte(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sans_prov(d):
    if isinstance(d, dict):
        return {k: _sans_prov(v) for k, v in d.items() if k != "prov"}
    if isinstance(d, list):
        return [_sans_prov(v) for v in d]
    return d


def _hda(sop):
    return sop.parent()


def _chemin(hda):
    return hda.evalParm("fichier").replace("\\", "/")


def modele(hda):
    """(données préparées, sha256) du fichier désigné par le paramètre « fichier » de l'HDA."""
    chemin = _chemin(hda)
    if not chemin or not os.path.exists(chemin):
        raise hou.NodeError(f"modèle introuvable : « {chemin} »")
    st = os.stat(chemin)
    cle = (st.st_mtime_ns, st.st_size)
    e = _CACHE.get(chemin)
    if e is None or e[0] != cle:
        with open(chemin, "rb") as f:
            octets = f.read()
        try:
            prep = preparer(json.loads(octets.decode("utf-8")))
        except ErreurModele as x:
            raise hou.NodeError(str(x))
        e = (cle, prep, hashlib.sha256(octets).hexdigest())
        _CACHE[chemin] = e
    return e[1], e[2]


def preparer(m):
    """Contrôle et mise en forme (sans calcul géométrique) : profils effectifs des sections, lois aplaties."""
    if m.get("schema") != SCHEMA:
        raise ErreurModele(f"schéma « {m.get('schema')} » : {SCHEMA} attendu")
    inconnues = sorted(set(m) - CLES_RACINE)
    if inconnues:
        raise ErreurModele(f"clés racine inconnues du schéma {SCHEMA} : {', '.join(inconnues)}")
    rep = m.get("repere") or {}
    o = rep.get("origine_l93")
    if not o or len(o) < 2:
        raise ErreurModele("repere.origine_l93 absent")
    origine = (float(o[0]), float(o[1]), float(o[2]) if len(o) > 2 else 0.0)
    profils = {p["id"]: p for p in m.get("profils", [])}
    effectifs = {}                      # id effectif -> (profil, origine de l'id)
    routes = []
    for r in m.get("routes", []):
        lr = r["ligne_reference"]
        geo = []
        for k, p in enumerate(lr.get("geometrie_reguliere") or []):
            if p["type"] not in TYPES_GEO:
                raise ErreurModele(f"{r['id']} : primitive « {p['type']} » non prise en charge (lot L1 : droite, arc, "
                                   "clothoïde)")
            k0 = float(p.get("courbure0", 0.0)) if p["type"] != "droite" else 0.0
            k1 = float(p.get("courbure1", k0)) if p["type"] == "clothoide" else k0
            if p["type"] == "arc" and abs(k0) < 1e-12:
                raise ErreurModele(f"{r['id']} : arc de courbure nulle (primitive {k})")
            geo.append({"type": TYPES_GEO[p["type"]], "s0": float(p["s0"]), "longueur": float(p["longueur"]),
                        "x0": float(p["x0"]) - origine[0], "y0": float(p["y0"]) - origine[1],
                        "cap": math.radians(float(p["cap_deg"])), "k0": k0, "k1": k1})
        secs = []
        for k, s in enumerate(r["sections"]):
            pr = s["profil"]
            if isinstance(pr, dict):
                pid = f"{r['id']}~S{k}"
                base = pr
            else:
                if pr not in profils:
                    raise ErreurModele(f"{r['id']} section {k} : profil « {pr} » inconnu")
                pid, base = pr, profils[pr]
            if s.get("surcharges"):
                base = surcharger(base, s["surcharges"], f"{r['id']} section {k}")
                pid = f"{pid}~{r['id']}~S{k}"
            te = (s.get("transition_entree") or {}).get("type", "")
            if te not in ("", "instantanee"):
                raise ErreurModele(f"{r['id']} section {k} : transition d'entrée « {te} » non prise en charge au lot L1 "
                                   "(écrire la transition en loi de largeur, comme le compilateur de description)")
            effectifs.setdefault(pid, base)
            secs.append({"s0": float(s["s0"]), "s1": float(s["s1"]), "profil": pid, "transition": te})
        routes.append({"r": r, "geo": geo, "secs": secs})
    prof_prep = {pid: aplatir_profil(pid, p) for pid, p in sorted(effectifs.items())}
    non_lus = {k: len(m[k]) for k in NON_LUS_L1 if m.get(k)}
    return {"m": m, "origine": origine, "routes": routes, "profils": prof_prep, "non_lus": non_lus}


def surcharger(p, sur, ou):
    q = copy.deepcopy(p)
    for chemin, v in sorted(sur.items()):
        mt = re.fullmatch(r"(bandes|limites)\[(\d+)\]\.([a-z_]+)", chemin)
        if not mt or int(mt.group(2)) >= len(q[mt.group(1)]):
            raise ErreurModele(f"{ou} : surcharge « {chemin} » non reconnue (bandes[i].champ ou limites[i].champ)")
        q[mt.group(1)][int(mt.group(2))][mt.group(3)] = v
    return q


def _loi(v, ou):
    """(type, s[], v[]) d'une loi de s : 0 nombre, 1 points linéaire, 2 points palier, 4 poly3."""
    if isinstance(v, (int, float)):
        return 0, [], [float(v)]
    if v.get("type") == "points":
        it = v.get("interpolation", "lineaire")
        if it not in LOI_POINTS:
            raise ErreurModele(f"{ou} : interpolation « {it} » non définie par le schéma 0.1 (aucune règle) : refusée")
        pts = v["points"]
        if any(b[0] < a[0] for a, b in zip(pts, pts[1:])):
            raise ErreurModele(f"{ou} : points de la loi non triés en s")
        return LOI_POINTS[it], [float(a) for a, _ in pts], [float(b) for _, b in pts]
    if v.get("type") == "poly3":
        S, V = [], []
        for x in v["morceaux"]:
            S.append(float(x["s0"]))
            V += [float(x["a"]), float(x.get("b", 0.0)), float(x.get("c", 0.0)), float(x.get("d", 0.0))]
        return 4, S, V
    raise ErreurModele(f"{ou} : loi de s inconnue ({v})")


def _evenements_limite(lim):
    """Abscisses des évènements portés par une limite (abaissés, intervalles et interruptions de marquage) : elles
    deviennent des sommets obligatoires de l'échantillonnage (rg::graphe)."""
    out = []
    b = lim.get("bordure") or {}
    for a in b.get("abaisses", []) or []:
        out += [a["s0"], a["s1"]]
    for mq in lim.get("marquages", []) or []:
        iv = mq.get("intervalle")
        if iv:
            out += [iv["s0"], iv["s1"]]
        for it in mq.get("interruptions", []) or []:
            out += [it["s0"], it["s1"]]
    return [float(x) for x in out]


def aplatir_profil(pid, p):
    bandes, limites = p["bandes"], p["limites"]
    if len(limites) != len(bandes) + 1:
        raise ErreurModele(f"profil {pid} : {len(limites)} limites pour {len(bandes)} bandes (n + 1 attendues)")
    r = int(p["reference"]["limite"])
    if not 0 <= r <= len(bandes):
        raise ErreurModele(f"profil {pid} : limite de référence {r} hors du profil")
    a = {"profil": pid, "ref_limite": r, "ref_decalage": float(p["reference"].get("decalage_m", 0.0)),
         "n_bandes": len(bandes), "larg_type": [], "larg_s0": [], "larg_v0": [], "larg_n": [], "larg_s": [],
         "larg_v": [], "bande_id": [], "bande_type": [], "bande_sous_type": [], "bande_sens": [], "bande_materiau": [],
         "niv_reference": [], "niv_dz": [], "niv_devers": [], "niv_forme": [], "bande_json": [],
         "lim_nature": [], "lim_bordure": [], "lim_vue": [], "lim_vue_loi": [], "lim_cote_haut": [], "lim_caniveau": [],
         "lim_marquages": [], "lim_separateur": [], "lim_json": [], "evts_s": []}
    for i, b in enumerate(bandes):
        typ, S, V = _loi(b["largeur"], f"profil {pid} bande {b['id']} : largeur")
        a["larg_type"].append(typ)
        a["larg_s0"].append(len(a["larg_s"]))
        a["larg_v0"].append(len(a["larg_v"]))
        a["larg_n"].append(len(S) if typ else 1)
        a["larg_s"] += S
        a["larg_v"] += V
        a["evts_s"] += S
        niv = b.get("niveau") or {}
        a["bande_id"].append(str(b["id"]))
        a["bande_type"].append(b["type"])
        a["bande_sous_type"].append(b.get("sous_type", ""))
        a["bande_sens"].append(b["sens"])
        a["bande_materiau"].append(b.get("materiau_id", ""))
        a["niv_reference"].append(niv.get("reference", ""))
        a["niv_dz"].append(float(niv.get("dz_m", 0.0)))
        a["niv_devers"].append(float(niv.get("devers_pct", 0.0)))
        a["niv_forme"].append(niv.get("forme", ""))
        a["bande_json"].append(_texte(_sans_prov(b)))
    for lim in limites:
        bo = lim.get("bordure") or {}
        vue = bo.get("vue_m")
        a["lim_nature"].append("+".join(lim["nature"]))
        a["lim_bordure"].append(bo.get("profil", ""))
        a["lim_vue"].append(float(vue) if isinstance(vue, (int, float)) else (-1.0 if vue is None else
                                                                              float(_loi(vue, pid)[2][0])))
        a["lim_vue_loi"].append(_texte(vue) if isinstance(vue, dict) else "")
        a["lim_cote_haut"].append(bo.get("cote_haut", ""))
        a["lim_caniveau"].append(((bo.get("caniveau") or {}).get("profil", "")))
        a["lim_marquages"].append(_texte(lim["marquages"]) if lim.get("marquages") else "")
        a["lim_separateur"].append(_texte(lim["separateur"]) if lim.get("separateur") else "")
        a["lim_json"].append(_texte(_sans_prov(lim)))
        a["evts_s"] += _evenements_limite(lim)
    a["evts_s"] = sorted(set(a["evts_s"]))
    a["props"] = _texte(_sans_prov({k: v for k, v in p.items() if k not in ("bandes", "limites")}))
    return a


# ----------------------------------------------------------------------------------------------- géométrie
def _h(origine, xy):
    """Coordonnées Lambert-93 -> Houdini (x, z, −y), z = 0 (courbes de contrôle planimétriques)."""
    return (float(xy[0]) - origine[0], 0.0, -(float(xy[1]) - origine[1]))


def _detail(geo, prep, sha, chemin, sortie):
    m = prep["m"]
    comptes = {k: len(m.get(k) or []) for k in sorted(CLES_RACINE - {"schema", "meta", "repere", "contexte"})}
    d = {"fichier": chemin, "sha256": sha, "schema": m["schema"], "origine_l93": list(prep["origine"]),
         "comptes": comptes, "non_lus": prep["non_lus"], "sortie": sortie,
         "zone": (m.get("meta") or {}).get("zone", ""), "titre": (m.get("meta") or {}).get("titre", "")}
    geo.addAttrib(hou.attribType.Global, "rg_modele", {})
    geo.setGlobalAttribValue("rg_modele", d)


def _ajouter(geo, classe, nom, defaut):
    geo.addAttrib(classe, nom, defaut)


def _tableau(geo, classe, nom, genre):
    geo.addArrayAttrib(classe, nom, {"f": hou.attribData.Float, "i": hou.attribData.Int,
                                     "s": hou.attribData.String}[genre])


def lire_routes(sop):
    hda = _hda(sop)
    prep, sha = modele(hda)
    geo = sop.geometry()
    o = prep["origine"]
    P = hou.attribType.Prim
    for nom, d in (("id", ""), ("nom", ""), ("categorie", ""), ("sens_unique", ""), ("noeud_debut", ""),
                   ("noeud_fin", ""), ("props", "")):
        _ajouter(geo, P, nom, d)
    for nom in ("agglomeration", "prioritaire", "geometrie_reguliere"):
        _ajouter(geo, P, nom, 0)
    for nom in ("vitesse_kmh", "longueur_m"):
        _ajouter(geo, P, nom, 0.0)
    for nom in ("geo_s0", "geo_longueur", "geo_x0", "geo_y0", "geo_cap", "geo_k0", "geo_k1", "sec_s0", "sec_s1"):
        _tableau(geo, P, nom, "f")
    _tableau(geo, P, "geo_type", "i")
    for nom in ("sec_profil", "sec_transition"):
        _tableau(geo, P, nom, "s")
    grp = geo.createPrimGroup("routes")
    for e in prep["routes"]:
        r = e["r"]
        lr = r["ligne_reference"]
        pts = geo.createPoints([_h(o, q) for q in lr["geometrie"]])
        pr = geo.createPolygon(is_closed=False)
        for p in pts:
            pr.addVertex(p)
        grp.add(pr)
        pr.setAttribValue("id", r["id"])
        pr.setAttribValue("nom", r.get("nom", ""))
        pr.setAttribValue("categorie", r.get("categorie", ""))
        pr.setAttribValue("sens_unique", r.get("sens_unique", ""))
        pr.setAttribValue("noeud_debut", r.get("noeud_debut", ""))
        pr.setAttribValue("noeud_fin", r.get("noeud_fin", ""))
        pr.setAttribValue("agglomeration", 1 if r.get("agglomeration") else 0)
        pr.setAttribValue("prioritaire", -1 if r.get("prioritaire") is None else int(bool(r["prioritaire"])))
        pr.setAttribValue("vitesse_kmh", float(r.get("vitesse_kmh") or 0.0))
        pr.setAttribValue("longueur_m", float(lr.get("longueur_m") or 0.0))
        pr.setAttribValue("geometrie_reguliere", 1 if e["geo"] else 0)
        g = e["geo"]
        pr.setAttribValue("geo_type", [x["type"] for x in g])
        for cle, nom in (("s0", "geo_s0"), ("longueur", "geo_longueur"), ("x0", "geo_x0"), ("y0", "geo_y0"),
                         ("cap", "geo_cap"), ("k0", "geo_k0"), ("k1", "geo_k1")):
            pr.setAttribValue(nom, [x[cle] for x in g])
        pr.setAttribValue("sec_s0", [s["s0"] for s in e["secs"]])
        pr.setAttribValue("sec_s1", [s["s1"] for s in e["secs"]])
        pr.setAttribValue("sec_profil", [s["profil"] for s in e["secs"]])
        pr.setAttribValue("sec_transition", [s["transition"] for s in e["secs"]])
        sans = {k: v for k, v in _sans_prov(r).items() if k != "ligne_reference"}
        sans["ligne_reference"] = {k: v for k, v in lr.items() if k != "geometrie"}
        pr.setAttribValue("props", _texte(sans))
    _detail(geo, prep, sha, _chemin(hda), "routes")
    if prep["non_lus"]:
        sop.addWarning("familles non lues au lot L1 : " + ", ".join(f"{k} ({n})" for k, n in prep["non_lus"].items()))


def lire_noeuds(sop):
    hda = _hda(sop)
    prep, sha = modele(hda)
    geo = sop.geometry()
    o = prep["origine"]
    Pt = hou.attribType.Point
    for nom in ("id", "type", "carrefour", "props"):
        _ajouter(geo, Pt, nom, "")
    _tableau(geo, Pt, "routes", "s")
    for n in prep["m"].get("noeuds", []):
        p = geo.createPoint()
        p.setPosition(_h(o, n["position"]))
        p.setAttribValue("id", n["id"])
        p.setAttribValue("type", n.get("type", ""))
        p.setAttribValue("carrefour", n.get("carrefour", ""))
        p.setAttribValue("routes", [str(x) for x in n.get("routes", [])])
        p.setAttribValue("props", _texte(_sans_prov(n)))
    _detail(geo, prep, sha, _chemin(hda), "noeuds")


def lire_zones(sop):
    hda = _hda(sop)
    prep, sha = modele(hda)
    geo = sop.geometry()
    o = prep["origine"]
    P = hou.attribType.Prim
    for nom in ("id", "famille_modele", "type", "materiau_id", "props"):
        _ajouter(geo, P, nom, "")
    _ajouter(geo, P, "anneau", 0)
    gt = geo.createPrimGroup("trou")
    for fam in ("zones", "ilots"):
        for z in prep["m"].get(fam, []):
            pg = z.get("polygone") or {}
            anneaux = [pg.get("exterieur") or []] + list(pg.get("trous") or [])
            for k, ann in enumerate(anneaux):
                if len(ann) < 3:
                    continue
                if ann[0] == ann[-1]:
                    ann = ann[:-1]
                pts = geo.createPoints([_h(o, q) for q in ann])
                pr = geo.createPolygon()
                for p in pts:
                    pr.addVertex(p)
                pr.setAttribValue("id", z["id"])
                pr.setAttribValue("famille_modele", fam[:-1])
                pr.setAttribValue("type", z.get("type", ""))
                pr.setAttribValue("materiau_id", (z.get("attributs") or {}).get("materiau_id", z.get("materiau_id", "")))
                pr.setAttribValue("anneau", k)
                pr.setAttribValue("props", _texte(_sans_prov(z)))
                if k:
                    gt.add(pr)
    _detail(geo, prep, sha, _chemin(hda), "zones")


def lire_ponctuels(sop):
    hda = _hda(sop)
    prep, sha = modele(hda)
    geo = sop.geometry()
    o = prep["origine"]
    Pt = hou.attribType.Point
    for nom in ("id", "famille_modele", "famille", "type", "route", "bande", "props"):
        _ajouter(geo, Pt, nom, "")
    for nom in ("s", "t", "longueur_m", "largeur_m", "hauteur_m", "rayon_m", "orientation_deg"):
        _ajouter(geo, Pt, nom, -1.0 if nom == "s" else 0.0)
    _ajouter(geo, Pt, "a_position", 0)
    _tableau(geo, Pt, "regles", "s")
    m = prep["m"]
    for fam, cle_r in (("objets", "rattachement"), ("signaux", "position"), ("marquages", "ancrage")):
        for x in m.get(fam, []):
            p = geo.createPoint()
            # position du modèle (objets : xy) ; signaux et marquages : rattachement (route, s, t) seulement, posés
            # aux lots L4 / L6 (géométrie éventuelle dans props) : point à l'origine, a_position = 0
            pos = x.get("position") if fam == "objets" else None
            if pos is not None:
                p.setPosition(_h(o, pos))
            p.setAttribValue("a_position", 1 if pos is not None else 0)
            ra = x.get(cle_r) if isinstance(x.get(cle_r), dict) else {}
            dims = x.get("dimensions") or {}
            p.setAttribValue("id", x["id"])
            p.setAttribValue("famille_modele", fam[:-1])
            p.setAttribValue("famille", x.get("famille", ""))
            p.setAttribValue("type", x.get("type", x.get("code", "")) if fam != "signaux" else x.get("code", ""))
            p.setAttribValue("route", ra.get("route", ""))
            p.setAttribValue("bande", ra.get("bande", ""))
            if ra.get("s") is not None:
                p.setAttribValue("s", float(ra["s"]))
            p.setAttribValue("t", float(ra.get("t", 0.0) or 0.0))
            for k in ("longueur_m", "largeur_m", "hauteur_m", "rayon_m"):
                p.setAttribValue(k, float(dims.get(k, 0.0)))
            p.setAttribValue("orientation_deg", float(x.get("orientation_deg", 0.0) or 0.0))
            p.setAttribValue("regles", [str(v) for v in (x.get("regles") or [])])
            p.setAttribValue("props", _texte(_sans_prov(x)))
    _detail(geo, prep, sha, _chemin(hda), "ponctuels")


def lire_profils(sop):
    hda = _hda(sop)
    prep, sha = modele(hda)
    geo = sop.geometry()
    Pt = hou.attribType.Point
    for nom in ("profil", "props"):
        _ajouter(geo, Pt, nom, "")
    for nom in ("ref_limite", "n_bandes"):
        _ajouter(geo, Pt, nom, 0)
    _ajouter(geo, Pt, "ref_decalage", 0.0)
    tabs = {"i": ("larg_type", "larg_s0", "larg_v0", "larg_n"),
            "f": ("larg_s", "larg_v", "niv_dz", "niv_devers", "lim_vue", "evts_s"),
            "s": ("bande_id", "bande_type", "bande_sous_type", "bande_sens", "bande_materiau", "niv_reference",
                  "niv_forme", "bande_json", "lim_nature", "lim_bordure", "lim_vue_loi", "lim_cote_haut",
                  "lim_caniveau", "lim_marquages", "lim_separateur", "lim_json")}
    for genre, noms in tabs.items():
        for nom in noms:
            _tableau(geo, Pt, nom, genre)
    for k, (pid, a) in enumerate(sorted(prep["profils"].items())):
        p = geo.createPoint()
        p.setPosition((0.0, 0.0, 0.0))
        for nom in ("profil", "props", "ref_limite", "n_bandes", "ref_decalage"):
            p.setAttribValue(nom, a[nom])
        for genre, noms in tabs.items():
            for nom in noms:
                p.setAttribValue(nom, [float(v) for v in a[nom]] if genre == "f" else
                                 ([int(v) for v in a[nom]] if genre == "i" else [str(v) for v in a[nom]]))
    _detail(geo, prep, sha, _chemin(hda), "profils")
