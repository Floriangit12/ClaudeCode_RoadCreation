"""Pilote du lot L5, partie giratoires (hython Houdini 22) : chaîne L1 + L2 + L2b + L3 avec le solveur des giratoires.

    hython recon/generateur/fabriquer_giratoires.py SCENE.yaml [SCENE.yaml ...] [--sortie DOSSIER] [--rendus]
                                                    [--vues dessus,conducteur] [--construire-hda] [--verifier-determinisme]

Même chaîne que fabriquer_carrefours.py (fonctions importées sans modification ; l'agent d'intégration fusionnera), avec
les HDA du lot (recon/generateur/hda/rg_giratoires) :
    rg::lire_modele ─► rg::carrefours ─► rg::giratoires ─► routes coupées (sans anneaux), profils (+ réduits) ─► rg::graphe…
                                                       ├► SOLVEUR fusionné ─► rg::carrefours_sol (cœur : anneau, bouches, coins)
                                                       └► GIRATOIRES ─► rg::giratoires_sol (couronne, îlot central, dôme,
                                                                         îlots séparateurs, marques de l'anneau)
       sol total = branches + cœur + îlots posés ; entités = branches + coins + îlots ; marques = profils + cœur + anneau
Sorties : celles des lots L2 / L2b / L3 dans recon/out/generateur/<scene>/ et l5/ (giratoires.json : anneau, congés,
faces des îlots, dessus, marques ; mesures_l5.json ; manifest_l5.json) ; rendus (2 vues ; 3 pour G1).
Le pilote se relance avec HOUDINI_VEX_DISABLE_JIT=1 et les dossiers temporaires sur D: (rien n'est écrit sur C:).
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent                 # recon/generateur
DEPOT = ICI.parents[1]
TMP = ICI / "tmp" / "hython"
SORTIE_DEFAUT = DEPOT / "recon" / "out" / "generateur"

if os.environ.get("RG_PILOTE_ENV") != "1":
    TMP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, RG_PILOTE_ENV="1", PYTHONDONTWRITEBYTECODE="1", TEMP=str(TMP), TMP=str(TMP),
               HOUDINI_TEMP_DIR=str(TMP).replace("\\", "/"), HOUDINI_VEX_DISABLE_JIT="1")
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=env))

import tempfile  # noqa: E402

tempfile.tempdir = str(TMP)
import hou  # noqa: E402

sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI / "hda" / "commun"))
sys.path.insert(0, str(ICI / "rendu"))
import rg_hda_outils as R  # noqa: E402
import fabriquer_generateur as FG  # noqa: E402
import fabriquer_l2 as F2  # noqa: E402
import fabriquer_l2b as F2B  # noqa: E402
import fabriquer_carrefours as FC  # noqa: E402

VERSION = "fabriquer_giratoires/1.0 (lot L5 giratoires)"
VUES_DEFAUT = ("dessus", "conducteur")
VUES_PHARES = {"G1_giratoire_urbain_D40": ("dessus", "conducteur", "oblique")}
TMP_L5 = ICI / "tmp" / "giratoires"


def _r(x, n=6):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------- HDA
def construire_hda(forcer=False):
    sigs = FC.construire_hda(forcer=forcer)
    spec = importlib.util.spec_from_file_location("construire_rg_giratoires", ICI / "hda" / "rg_giratoires" / "construire.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a, b = mod.construire(ICI / "hda" / "rg_giratoires")
    sigs[f"rg::giratoires::{R.VERSION}"] = R.signature(a)
    sigs[f"rg::giratoires_sol::{R.VERSION}"] = R.signature(b)
    return sigs


# ------------------------------------------------------------------------------------------------------- réseau
def reseau():
    """Réseau du lot L3 (fabriquer_carrefours.reseau) ; rg::giratoires inséré après rg::carrefours (ses sorties
    remplacent celles de rg::carrefours partout) et rg::giratoires_sol branché sur le sol sans îlots ; sol, BEV,
    entités et marques des îlots fusionnés avec ceux des branches et du cœur."""
    lire, car, graphe, prof, n2, n2b = FC.reseau()
    gir = inserer(lire, car, graphe, prof, n2, n2b)
    return lire, car, gir, graphe, prof, n2, n2b


def inserer(lire, car, graphe, prof, n2, n2b):
    """rg::giratoires et rg::giratoires_sol ajoutées au réseau du lot L3 : réutilisée par fabriquer_generateur.py."""
    obj = lire.parent()
    gir = obj.createNode(R.nom_type("giratoires"), "giratoires")
    for k in range(3):
        gir.setInput(k, car, k)
    gir.parm("fichier").setExpression('chs("../lire_modele/fichier")', hou.exprLanguage.Hscript)
    graphe.setInput(0, gir, 0)
    graphe.setInput(1, gir, 1)
    prof.setInput(1, gir, 1)
    n2["nivellement"].setInput(1, gir, 1)
    n2["vers_entites_branches"].setInput(1, gir, 1)
    cs = n2["carrefours_sol"]
    cs.setInput(1, gir, 1)
    cs.setInput(2, gir, 2)
    n2b["marquages"].setInput(2, gir, 1)
    sans = obj.createNode("merge", "sol_sans_ilots")
    sans.setInput(0, n2["sol_branches"], 0)
    sans.setInput(1, cs, 0)
    gs = obj.createNode(R.nom_type("giratoires_sol"), "giratoires_sol")
    gs.setInput(0, gir, 3)
    gs.setInput(1, sans, 0)
    m_cs = obj.node("carrefour_sol_bev")
    m_cs.setInput(2, gs, 0)
    m_cs.setInput(3, gs, 1)
    m_ent = obj.createNode("merge", "entites_carrefour_et_ilots")
    m_ent.setInput(0, cs, 2)
    m_ent.setInput(1, gs, 2)
    n2["vers_entites"].setInput(3, m_ent, 0)              # subnet entites_total : entrée 3 = entités du carrefour
    mm = obj.node("marques_et_carrefour")
    mm.setInput(2, gs, 3)
    n2["carrefours_l3"] = car
    n2["carrefours"] = gir                                  # SOLVEUR fusionné en sortie 3 (geometry(2)) : contrat L3
    n2["giratoires"], n2["giratoires_sol"] = gir, gs
    obj.layoutChildren()
    return gir


def cuire(noeuds, scene):
    FC.cuire(noeuds, scene)
    for k in ("giratoires", "giratoires_sol"):
        n = noeuds[k]
        try:
            n.cook(force=True)
        except hou.OperationFailed:
            pass
        err = [f"{c.path()} : {e}" for c in (n,) + n.allSubChildren() for e in c.errors()]
        if err:
            raise SystemExit(f"{scene} : erreurs de cuisson ({k})" + chr(10) + chr(10).join(err[:20]))


# ------------------------------------------------------------------------------------------------------- exports
def _val(o, nom):
    try:
        v = o.attribValue(nom)
    except hou.OperationFailed:
        return None
    if isinstance(v, float):
        return _r(v)
    if isinstance(v, (tuple, list)):
        return [(_r(x) if isinstance(x, float) else (list(x) if not isinstance(x, (str, int, dict)) else x)) for x in v]
    if type(v).__name__.startswith("Vector"):
        return [_r(x) for x in v]
    return v


def _pts(pr):
    return [[_r(p.position()[0]), _r(-p.position()[2]), _r(p.position()[1])] for p in pr.points()]


def exporter_giratoires(noeuds, dossier):
    """l5/giratoires.json : points giratoire (anneau, rayons), branches (congés), coins des giratoires (SOLVEUR), faces
    des îlots (pied, vue, abaissés), dessus (étendue en Z par îlot), entités, BEV, marques (comptes)."""
    gg = noeuds["giratoires"].geometry(3)
    out = {"schema": "rg_giratoires_l5/0.1"}
    noms_p = sorted(a.name() for a in gg.pointAttribs() if a.name() != "P")   # ordre stable (intégration)
    for grp, cle in (("giratoire", "giratoires"), ("branche", "branches"), ("passage", "passages")):
        g = gg.findPointGroup(grp)
        out[cle] = [{n: _val(p, n) for n in noms_p} for p in (g.points() if g else [])]
    noms_pr = sorted(a.name() for a in gg.primAttribs())
    for grp, cle in (("coin", "coins"), ("ilot_g", "ilots_modele"), ("embouchure", "embouchures")):
        g = gg.findPrimGroup(grp)
        out[cle] = [{"points": _pts(pr), **{n: _val(pr, n) for n in noms_pr},
                     **({"parties": [p.attribValue("partie") for p in pr.points()]} if grp == "coin" else {})}
                    for pr in (g.prims() if g else [])]
    gf = noeuds["giratoires_sol"].geometry(4)
    noms_f = sorted(a.name() for a in gf.primAttribs())
    out["faces"] = [{"points": _pts(pr), **{n: _val(pr, n) for n in noms_f}} for pr in gf.prims()]
    av = list(gf.attribValue("rg_giratoires_sol_avertissements")) if gf.findGlobalAttrib("rg_giratoires_sol_avertissements") else []
    av0 = list(gg.attribValue("rg_giratoires_avertissements")) if gg.findGlobalAttrib("rg_giratoires_avertissements") else []
    out["avertissements"] = av0 + av
    gs = noeuds["giratoires_sol"].geometry(0)
    dessus = {}
    for pr in gs.prims():
        if pr.attribValue("zone") != "ilot":
            continue
        ref = pr.attribValue("ref")
        zs = [p.position()[1] for p in pr.points()]
        d = dessus.setdefault(ref, {"faces": 0, "z_min": 1e9, "z_max": -1e9, "materiau": pr.attribValue("materiau_id")})
        d["faces"] += 1
        d["z_min"] = min(d["z_min"], min(zs))
        d["z_max"] = max(d["z_max"], max(zs))
    out["dessus"] = {k: {kk: (_r(vv) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in sorted(dessus.items())}
    # coupe radiale des dessus (couronne, îlot central, dôme) : z en fonction du rayon, au sud du centre
    coupes = {}
    for gp in out["giratoires"]:
        cx, cy = gp["centre"][0], gp["centre"][1]
        pts = []
        for r in [x * 0.05 for x in range(0, int(gp["Rg"] / 0.05) + 1)]:
            hit = hou.Vector3()
            nn = hou.Vector3()
            uvw = hou.Vector3()
            o = hou.Vector3(cx + 0.0, 10.0, -(cy - r))
            k = gs.intersect(o, hou.Vector3(0, -1, 0), hit, nn, uvw, None, 0, 1e9, 1e-7)
            if k >= 0:
                pts.append([_r(r, 3), _r(hit[1]), gs.prim(k).attribValue("ref")])
        coupes[gp["id"]] = pts
    out["coupes_dessus"] = coupes
    ge = noeuds["giratoires_sol"].geometry(2)
    out["entites"] = [{"id": pr.attribValue("id"), "xyz": _pts(pr),
                       "intervalles": [{k: (_r(v) if isinstance(v, float) else v) for k, v in sorted(iv.items())}
                                       for iv in pr.attribValue("intervalles")],
                       "niv_z_pied": [_r(x) for x in pr.attribValue("niv_z_pied")],
                       "niv_z_tete": [_r(x) for x in pr.attribValue("niv_z_tete")]} for pr in ge.prims()]
    gb = noeuds["giratoires_sol"].geometry(1)
    out["bev"] = [{"id": pr.attribValue("id"), "points": _pts(pr)} for pr in gb.prims()]
    gm = noeuds["giratoires_sol"].geometry(3)
    marques = {}
    for pr in gm.prims():
        k = pr.attribValue("id").rsplit("_t", 1)[0]
        m = marques.setdefault(k, {"pieces": 0, "rayon_m": _r(pr.attribValue("rayon_m")), "largeur_m": _r(pr.attribValue("largeur_m")),
                                   "modulation": pr.attribValue("modulation"), "traits": set()})
        m["pieces"] += 1
        m["traits"].add(pr.attribValue("rang"))
    out["marques"] = {k: {**{kk: vv for kk, vv in v.items() if kk != "traits"}, "traits": len(v["traits"])}
                      for k, v in sorted(marques.items())}
    (dossier / "giratoires.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"giratoires": len(out["giratoires"]), "coins": len(out["coins"]), "faces": len(out["faces"]),
            "entites": len(out["entites"]), "bev": len(out["bev"]), "marques": len(out["marques"]),
            "avertissements": len(out["avertissements"])}


def mesurer_ilots(noeuds, dossier):
    """Étanchéité des îlots posés : arêtes de bord du sol des îlots (dessus + jupes) ; une jupe descend sous le sol posé
    (bord bas libre attendu, caché) ; les autres arêtes de bord sont comptées."""
    g = noeuds["giratoires_sol"].geometry(0)
    aretes = {}
    for pr in g.prims():
        vs = [v.point().number() for v in pr.vertices()]
        for a, b in zip(vs, vs[1:] + vs[:1]):
            k = (min(a, b), max(a, b))
            aretes[k] = aretes.get(k, 0) + 1
    bord = [k for k, n in aretes.items() if n == 1]
    sol = noeuds["giratoires_sol"].inputs()[1].geometry()
    pos, nrm, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()
    sous, libres = 0, []
    for a, b in bord:
        A, B = g.point(a).position(), g.point(b).position()
        m = (A + B) * 0.5
        k = sol.intersect(hou.Vector3(m[0], m[1] + 5.0, m[2]), hou.Vector3(0, -1, 0), pos, nrm, uvw, None, 0, 1e9, 1e-7)
        if k >= 0 and pos[1] > m[1] + 1e-4:
            sous += 1
        else:
            libres.append([_r(m[0], 3), _r(-m[2], 3), _r(m[1], 4)])
    res = {"aretes_de_bord": len(bord), "sous_le_sol": sous, "bords_libres_au_dessus_du_sol": len(libres),
           "exemples": libres[:10],
           "note": "arêtes de bord du sol des îlots posés : le bas des jupes est sous le sol posé (attendu, caché) ; les "
                   "autres sont des bords libres visibles"}
    (dossier / "mesures_l5.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return res


# ------------------------------------------------------------------------------------------------------- vues
def _largeur(w, s):
    if isinstance(w, (int, float)):
        return float(w)
    pts = (w or {}).get("points") or []
    if not pts:
        return 0.0
    if s <= pts[0][0]:
        return float(pts[0][1])
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if a <= s <= b:
            return float(va) + (float(vb) - float(va)) * (s - a) / max(b - a, 1e-12)
    return float(pts[-1][1])


def t_voie_entrante(m, rid, s):
    """t du centre de la voie entrante la plus à droite (bande voie_* de sens « avant ») en s, lois de largeur
    évaluées (évasement de l'entrée du giratoire ; fabriquer_carrefours.voie_entrante prend 3,00 m pour une loi)."""
    r = next(x for x in m["routes"] if x["id"] == rid)
    sec = [x for x in r["sections"] if x["s0"] <= s + 1e-9][-1]
    pr = next(x for x in m["profils"] if x["id"] == sec["profil"])
    w = [_largeur(b["largeur"], s) for b in pr["bandes"]]
    ref = int(pr["reference"]["limite"])
    T = [0.0] * (len(w) + 1)
    T[ref] = -float(pr["reference"].get("decalage_m", 0.0))
    for i in range(ref - 1, -1, -1):
        T[i] = T[i + 1] + w[i]
    for i in range(ref + 1, len(w) + 1):
        T[i] = T[i - 1] - w[i - 1]
    cand = [0.5 * (T[i] + T[i + 1]) for i, b in enumerate(pr["bandes"])
            if b["type"].startswith("voie") and b.get("sens") == "avant"]
    return min(cand) if cand else -1.5


def _point_route(m, rid, s, t):
    r = next(x for x in m["routes"] if x["id"] == rid)
    o = m["repere"]["origine_l93"]
    P = [(x - o[0], y - o[1]) for x, y in r["ligne_reference"]["geometrie"]]
    acc = 0.0
    for a, b in zip(P, P[1:]):
        L = math.dist(a, b)
        if acc + L >= s or b == P[-1]:
            u = (s - acc) / max(L, 1e-12)
            dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            return (a[0] + u * (b[0] - a[0]) - t * dy, a[1] + u * (b[1] - a[1]) + t * dx)
        acc += L
    return P[-1]


def vues_giratoire(m, solveur, graphe_geo, vues):
    """Caméras du giratoire (repère (s, t, h) de la route 0 du rendu) : conducteur sur la branche entrante de rang 0,
    30 m avant la ligne CÉDEZ, au centre de la voie entrante à cette abscisse, 1,20 m, regard vers l'îlot central (voie
    entrante à la frontière, 10 m dans l'anneau) ; oblique 3/4 et vue de dessus : fabriquer_carrefours.vues_carrefour."""
    propres, centre, largeur, bnom = FC.vues_carrefour(m, solveur, graphe_geo, vues)
    gb = solveur.findPointGroup("branche")
    brs = [p for p in gb.points() if p.attribValue("regime") == "entree_giratoire"] or list(gb.points())
    b = min(brs, key=lambda p: p.attribValue("rang"))
    rid, sf = b.attribValue("route"), b.attribValue("s_front")
    t_oeil = t_voie_entrante(m, rid, sf - 30.0)
    t_cib = t_voie_entrante(m, rid, sf - 0.5)
    oeil = _point_route(m, rid, sf - 30.0, t_oeil)
    d = b.attribValue("dir")
    p_f = _point_route(m, rid, sf, t_cib)
    cible = (p_f[0] + 10.0 * d[0], p_f[1] + 10.0 * d[1])
    so, to = FC.st_route0(graphe_geo, *oeil)
    sc_, tc = FC.st_route0(graphe_geo, *cible)
    propres["conducteur_carrefour"] = ((so, to, 1.20), (sc_, tc, 0.5), 24)
    return propres, centre, largeur, b.attribValue("branche")


# ------------------------------------------------------------------------------------------------------- pilote
def fabriquer(entrees, sortie, signatures, rendus=False, vues=VUES_DEFAUT):
    lire, car, gir, graphe, prof, n2, n2b = reseau()
    produits = []
    for e in entrees:
        scene, chemin_modele, info = FG.preparer_entree(e, sortie)
        dsc = Path(sortie) / scene
        d1, d3, d5 = dsc / "l1", dsc / "l3", dsc / "l5"
        for d in (d1, d3, d5):
            d.mkdir(parents=True, exist_ok=True)
        fb, bal = FC.balayages(chemin_modele, TMP_L5 / scene)
        car.parm("balayages").set(str(fb).replace("\\", "/"))
        info_bal = [{k: v for k, v in b.items() if k != "exterieur"} for b in bal]
        lire.parm("fichier").set(str(chemin_modele).replace("\\", "/"))
        for n in (lire, car, gir, graphe, prof):
            try:
                n.cook(force=True)
            except hou.OperationFailed:
                pass
            err = [f"{c.path()} : {x}" for c in (n,) + n.allSubChildren() for x in c.errors()]
            if err:
                raise SystemExit(f"{scene} : erreurs de cuisson" + chr(10) + chr(10).join(err))
        donnees = FG.extraire(lire, graphe, prof)
        courbes = {"schema": "rg_courbes_controle/0.1", "scene": scene,
                   "lot": "L1 (+ L3 / L5 : routes coupées aux carrefours et aux giratoires)",
                   "modele": {"fichier": FG.rel(chemin_modele), "sha256": FG.sha256(chemin_modele)}}
        courbes.update(donnees)
        (d1 / "courbes_controle.json").write_text(json.dumps(courbes, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
        man1 = {"schema": "rg_manifest/0.1", "pilote": VERSION, "scene": scene, "entree": info, "modele": courbes["modele"],
                "houdini": hou.applicationVersionString(), "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
                "hda": signatures, "parametres": donnees["parametres"], "comptes": donnees["comptes"],
                "avertissements": FG.avertissements(lire, car, gir, graphe, prof),
                "fichiers": {"courbes_controle.json": FG.sha256(d1 / "courbes_controle.json")}}
        (d1 / "manifest_l1.json").write_text(json.dumps(man1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        cuire(n2, scene)
        d2, man2 = F2.fabriquer_scene(n2, scene, dsc, signatures, info)
        d2b, man2b = F2B.fabriquer_scene(n2b, scene, dsc, signatures, info)
        c3 = FC.exporter_carrefours(n2, d3, info_bal)
        m3 = FC.mesurer_raccords(n2, d3)
        f3 = {p.name: sha256(p) for p in sorted(d3.iterdir()) if p.is_file() and p.name != "manifest_l3.json"}
        (d3 / "manifest_l3.json").write_text(json.dumps(
            {"schema": "rg_manifest_l3/0.1", "pilote": VERSION, "scene": scene, "entree": info,
             "houdini": hou.applicationVersionString(), "hda": signatures, "comptes": c3, "raccords": m3,
             "fichiers": f3}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        c5 = exporter_giratoires(n2, d5)
        m5 = mesurer_ilots(n2, d5)
        f5 = {p.name: sha256(p) for p in sorted(d5.iterdir()) if p.is_file() and p.name != "manifest_l5.json"}
        (d5 / "manifest_l5.json").write_text(json.dumps(
            {"schema": "rg_manifest_l5/0.1", "pilote": VERSION, "scene": scene, "entree": info,
             "houdini": hou.applicationVersionString(), "hda": signatures, "comptes": c5, "ilots": m5,
             "fichiers": f5}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{scene} : L3 {c3} ; raccords {m3['raccords_branches']} (écart max {m3['ecart_max_m']} m), "
              f"bords libres {m3['bords_libres']} (hors extérieur {m3['bords_libres_hors_exterieur']}) ; L5 {c5} ; "
              f"îlots : bords libres {m5['bords_libres_au_dessus_du_sol']} -> {FG.rel(dsc)}")
        if rendus:
            m = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
            vv = VUES_PHARES.get(scene, vues)
            propres, centre, largeur, bcond = vues_giratoire(m, gir.geometry(2), graphe.geometry(), vv)
            print(f"{scene} : rendus {list(vv)} ; conducteur sur {bcond} ; dessus {largeur:.1f} m")
            FC.installer_rendu(vv, propres, centre, largeur, bcond)(n2, n2b, scene, dsc, lire.parent())
        produits.append(str(dsc))
    return produits


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrees", nargs="+")
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    ap.add_argument("--rendus", action="store_true")
    ap.add_argument("--vues", default=",".join(VUES_DEFAUT))
    ap.add_argument("--construire-hda", action="store_true")
    ap.add_argument("--verifier-determinisme", action="store_true")
    a = ap.parse_args()
    signatures = construire_hda(forcer=a.construire_hda)
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items()))
    produits = fabriquer(a.entrees, a.sortie, signatures, rendus=a.rendus, vues=tuple(v for v in a.vues.split(",") if v))
    if a.verifier_determinisme:
        autre = TMP_L5 / "determinisme"
        r = subprocess.run([sys.executable, __file__] + a.entrees + ["--sortie", str(autre)],
                           env=dict(os.environ, RG_PILOTE_ENV=""), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("second processus en échec")
        from commun import determinisme as DET
        ecarts, n = DET.comparer([str(Path(p) / "l1") for p in produits], autre, True, True)
        for p in produits:
            for sous in ("l3", "l5"):
                for f in sorted((Path(p) / sous).glob("*.json")):
                    if f.name.startswith("manifest_"):
                        continue
                    g = autre / Path(p).name / sous / f.name
                    n += 1
                    if not g.exists() or g.read_bytes() != f.read_bytes():
                        ecarts.append(str(f))
        print("déterminisme :", f"identique ({n} fichiers)" if not ecarts else f"DIFFÉRENT : {ecarts}")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
