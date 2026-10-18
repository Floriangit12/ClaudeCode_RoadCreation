"""Pilote du lot L3 (carrefours plans ; hython Houdini 22) : chaîne L1 + L2 + L2b avec le solveur de carrefours.

    hython recon/generateur/fabriquer_carrefours.py SCENE.yaml [SCENE.yaml ...] [--sortie DOSSIER] [--rendus]
                                                    [--vues dessus,conducteur] [--construire-hda] [--verifier-determinisme]
                                                    [--sans-balayages]

Même chaîne que fabriquer_generateur.py --l2b (fonctions importées sans modification ; l'agent d'intégration fusionnera),
avec les HDA du lot (recon/generateur/hda/rg_carrefours) :
    rg::lire_modele ─► rg::carrefours (solveur : coins, coupes, nez, frontière) ─► rg::graphe ─► rg::profils
                                         │                                       └► rg::nivellement ─► rg::sol ─┐
                                         └► SOLVEUR ─────────────────────────────► rg::carrefours_sol ─────────┤
       sol total (branches + carrefour) ◄────────────────────────────────────────────────────────────────────────┘
       entités (branches + bordures du carrefour) ─► pj::bordure, pj::caniveau ; marques du carrefour ─► pj::marquage_solide
Avant la fabrication, les balayages des trajectoires du modèle sont calculés avec vehicules/balayage.py (lot L3a : VL,
bus standard 12 m) et passés au solveur (nez des îlots au premier contact + 0,30 m).
Sorties : celles du lot L2 / L2b dans recon/out/generateur/<scene>/ et l3/ (carrefours.json : solveur, faces de
bordure, frontière, nez, balayages ; mesures_l3.json : étanchéité des raccords, marches) ; rendus (2 vues ; 3 pour J5).
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

VERSION = "fabriquer_carrefours/1.0 (lot L3)"
VUES_DEFAUT = ("dessus", "conducteur")
VUES_PHARES = {"J5_carrefour_complexe": ("dessus", "conducteur", "oblique")}
VEHICULES = ("vl", "bus_standard_12m")
TMP_L3 = ICI / "tmp" / "carrefours"


def _r(x, n=6):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------- HDA
def construire_hda(forcer=False):
    sigs = FG.construire_hda(forcer=forcer, l2=True)
    sigs.update(F2.installer_pj())
    sigs.update(F2B.construire_hda(forcer=forcer))
    spec = importlib.util.spec_from_file_location("construire_rg_carrefours", ICI / "hda" / "rg_carrefours" / "construire.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a, b = mod.construire(ICI / "hda" / "rg_carrefours")
    sigs[f"rg::carrefours::{R.VERSION}"] = R.signature(a)
    sigs[f"rg::carrefours_sol::{R.VERSION}"] = R.signature(b)
    return sigs


# ------------------------------------------------------------------------------------------------------- réseau
def _sous_reseau(obj, nom, entrees, construction):
    """Subnet SOP à plusieurs sorties (Output SOP outputidx) ; entrees = [(nœud, sortie)] (≤ 4)."""
    sub = obj.createNode("subnet", nom)
    for k, (n, o) in enumerate(entrees):
        sub.setInput(k, n, o)
    ind = sub.indirectInputs()
    sorties = construction(sub, ind)
    for k, n in enumerate(sorties):
        out = sub.createNode("output", f"sortie_{k}")
        out.setInput(0, n)
        out.parm("outputidx").set(k)
    sub.layoutChildren()
    return sub


def reseau(avant_l2b=None):
    """avant_l2b(obj, lire, graphe, prof, n2) : crochet appelé avant la chaîne L2b (intégration de l'étape 2 : sol des
    musoirs de rg::autoroute dans une scène à carrefours)."""
    lire, graphe, prof = FG.reseau()
    obj = lire.parent()
    car = obj.createNode(R.nom_type("carrefours"), "carrefours")
    car.setInput(0, lire, 0)
    car.setInput(1, lire, 4)
    car.parm("fichier").setExpression('chs("../lire_modele/fichier")', hou.exprLanguage.Hscript)
    graphe.setInput(0, car, 0)
    graphe.setInput(1, car, 1)
    prof.setInput(1, car, 1)
    n2 = F2.reseau(obj, lire, graphe, R.nom_type)
    n2["nivellement"].setInput(1, car, 1)
    n2["vers_entites"].setInput(1, car, 1)
    cs = obj.createNode(R.nom_type("carrefours_sol"), "carrefours_sol")
    cs.setInput(0, n2["nivellement"], 0)
    cs.setInput(1, car, 1)
    cs.setInput(2, car, 2)
    cs.setInput(3, graphe, 0)
    cs.parm("amorce").setExpression('ch("../carrefours/amorce")', hou.exprLanguage.Hscript)
    m_cs = obj.createNode("merge", "carrefour_sol_bev")
    m_cs.setInput(0, cs, 0)
    m_cs.setInput(1, cs, 1)

    def sol_total(sub, ind):
        sans = sub.createNode("blast", "sol_carrefour")
        sans.setInput(0, ind[3])
        sans.parm("group").set("dalles")
        sans.parm("grouptype").set("prims")
        bev = sub.createNode("blast", "bev_carrefour")
        bev.setInput(0, ind[3])
        bev.parm("group").set("dalles")
        bev.parm("grouptype").set("prims")
        bev.parm("negate").set(1)
        ms = sub.createNode("merge", "sol")
        ms.setInput(0, ind[1])
        ms.setInput(1, sans)
        mb = sub.createNode("merge", "bev")
        mb.setInput(0, ind[2])
        mb.setInput(1, bev)
        return ms, mb

    sol_w = _sous_reseau(obj, "sol_total", [(graphe, 0), (n2["sol"], 0), (n2["sol"], 1), (m_cs, 0)], sol_total)

    def ent_total(sub, ind):
        me = sub.createNode("merge", "entites")
        me.setInput(0, ind[0])
        me.setInput(1, ind[3])
        return me, ind[1], ind[2]

    ve = n2["vers_entites"]
    ent_w = _sous_reseau(obj, "entites_total", [(ve, 0), (ve, 1), (ve, 2), (cs, 2)], ent_total)
    for k in ("bordures", "caniveaux"):
        n2[k].setInput(0, ent_w, 0)
    n2["controle_heightfield"].setInput(0, sol_w, 0)
    n2["sol_branches"], n2["vers_entites_branches"] = n2["sol"], ve
    n2["sol"], n2["vers_entites"] = sol_w, ent_w
    n2["carrefours"], n2["carrefours_sol"] = car, cs
    if avant_l2b is not None:
        avant_l2b(obj, lire, graphe, prof, n2)
    n2b = F2B.reseau(obj, lire, graphe, n2)
    n2b["marquages"].setInput(2, car, 1)
    mm = obj.createNode("merge", "marques_et_carrefour")
    mm.setInput(0, n2b["marquages"], 1)
    mm.setInput(1, cs, 3)
    n2b["peinture_marques"].setInput(0, mm)
    obj.layoutChildren()
    return lire, car, graphe, prof, n2, n2b


def cuire(noeuds, scene):
    F2.cuire({k: noeuds[k] for k in ("nivellement", "sol", "vers_entites", "bordures", "caniveaux",
                                      "controle_heightfield")}, scene)
    for k in ("carrefours", "carrefours_sol"):
        n = noeuds[k]
        err = [f"{c.path()} : {e}" for c in (n,) + n.allSubChildren() for e in c.errors()]
        if err:
            raise SystemExit(f"{scene} : erreurs de cuisson ({k})" + chr(10) + chr(10).join(err[:20]))


# ------------------------------------------------------------------------------------------------------- balayages
def balayages(chemin_modele, dossier):
    """Enveloppes balayées des trajectoires du modèle (lot L3a) : VL et bus standard 12 m ; JSON local (x, y)."""
    sys.path.insert(0, str(ICI))
    from vehicules import balayage as B
    m = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
    o = m["repere"]["origine_l93"]
    out = []
    for c in m.get("carrefours", []):
        if c.get("type") in ("giratoire", "mini_giratoire", "bifurcation"):
            continue
        az = {b["id"]: math.radians(float(b.get("azimut_deg", 0.0))) for b in c["branches"]}
        for t in c.get("trajectoires", []):
            axe = [(float(x) - o[0], float(y) - o[1]) for x, y in t.get("geometrie") or []]
            if len(axe) < 2:
                continue
            # approche et sortie dans l'axe des voies (la trajectoire du modèle va d'une frontière à l'autre ; son premier
            # segment peut être oblique, guidage à l'indonésienne) : 15 m de droite le long de la branche d'entrée avant
            # le départ, 15 m le long de la branche de sortie après l'arrivée ; l'amorce du lot L3a prolonge l'approche
            a_in = az.get((t.get("de") or {}).get("branche"))
            a_out = az.get((t.get("vers") or {}).get("branche"))
            if a_in is not None:
                x0, y0 = axe[0]
                axe = [(x0 + 15.0 * math.cos(a_in), y0 + 15.0 * math.sin(a_in))] + axe
            if a_out is not None:
                x1, y1 = axe[-1]
                axe = axe + [(x1 + 15.0 * math.cos(a_out), y1 + 15.0 * math.sin(a_out))]
            for nv in VEHICULES:
                d = B.balayage_detail(nv, axe)
                pg = d["polygone"]
                out.append({"trajectoire": t["id"], "mouvement": t.get("mouvement", ""), "vehicule": nv,
                            "carrefour": c["id"], "de_branche": (t.get("de") or {}).get("branche", ""),
                            "vers_branche": (t.get("vers") or {}).get("branche", ""),
                            "faisable": bool(d["faisable"]), "rayon_axe_min_m": _r(d["rayon_axe_min"], 4),
                            "rayon_min_vehicule_m": _r(d["rayon_min_vehicule"], 4),
                            "exterieur": [[_r(x, 5), _r(y, 5)] for x, y in pg.exterieur]})
    dossier.mkdir(parents=True, exist_ok=True)
    f = dossier / "balayages.json"
    f.write_text(json.dumps({"schema": "rg_balayages/0.1", "vehicules": list(VEHICULES), "balayages": out},
                            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return f, out


def _axe_vehicule(P, r_l4, r_min):
    """Axe suivi par un véhicule dont le rayon minimal dépasse celui de la trajectoire L4 : mêmes axes de voie d'entrée et
    de sortie (droites du premier et du dernier segment), arc tangent de rayon r_min (règle de L4 : rayon ≥ rayon d'axe
    minimal du véhicule de projet, RF-GV-TRJ-006) ; points de tangence reculés sur les axes si besoin."""
    if r_l4 <= 0 or r_l4 >= r_min - 1e-6 or len(P) < 3:
        return list(P), r_l4
    import numpy as np
    p0, p1 = np.array(P[0], float), np.array(P[-1], float)
    ha = np.array(P[1], float) - p0
    ha /= np.linalg.norm(ha)
    hb = p1 - np.array(P[-2], float)
    hb /= np.linalg.norm(hb)
    cr = ha[0] * hb[1] - ha[1] * hb[0]
    if abs(cr) < 1e-9:
        return list(P), r_l4
    # intersection des deux axes
    w = p1 - p0
    t = (w[0] * hb[1] - w[1] * hb[0]) / cr
    I = p0 + t * ha
    dl = math.atan2(cr, float(ha @ hb))
    T = r_min * math.tan(abs(dl) / 2.0)
    a1, a2 = I - T * ha, I + T * hb
    sg = 1.0 if dl > 0 else -1.0
    c = a1 + sg * r_min * np.array([-ha[1], ha[0]])
    a0 = math.atan2(a1[1] - c[1], a1[0] - c[0])
    n = max(8, int(math.ceil(abs(dl) / math.radians(0.8))))
    arc = [(float(c[0] + r_min * math.cos(a0 + sg * abs(dl) * k / n)), float(c[1] + r_min * math.sin(a0 + sg * abs(dl) * k / n)))
           for k in range(n + 1)]
    debut = [tuple(p0)] if float((a1 - p0) @ ha) > 1e-6 else []
    fin = [tuple(p1)] if float((p1 - a2) @ hb) > 1e-6 else []
    return debut + arc + fin, r_min


def balayages_l4(chemin_modele, trajectoires_l4, dossier, nom="balayages.json"):
    """Enveloppes balayées (lot L3a) sur les trajectoires FINALES du lot L4 (correction après le contrôle de l'étape 2 :
    une seule source de trajectoires ; L3 balayait auparavant les géométries du compilateur, TAG de J1 à J4 à R = 4,47 m,
    infaisables donc exclus). Véhicules : ceux du mouvement (modèle : trajectoires[].usagers ; à défaut VL et bus 12 m).
    Le VL suit la trajectoire L4 ; un véhicule de rayon minimal supérieur suit les mêmes axes de voie avec un arc de son
    rayon minimal (_axe_vehicule). Approche et sortie : 15 m dans l'axe (comme auparavant)."""
    sys.path.insert(0, str(ICI))
    from vehicules import balayage as B
    m = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
    usagers = {t["id"]: t.get("usagers") for c in m.get("carrefours", []) for t in c.get("trajectoires", [])}
    rmin = {v: float(B.rayon_min(v)) for v in VEHICULES}
    out = []
    for t in trajectoires_l4:
        if t.get("tags") == "velo" or len(t["points"]) < 2:
            continue
        vs = [v for v in (usagers.get(t["id"]) or VEHICULES) if v in VEHICULES]
        for nv in vs:
            P0 = [tuple(p) for p in t["points"]]
            r_l4 = float(t.get("rayon") or 0.0)
            P, r_ax = _axe_vehicule(P0, r_l4, math.ceil(rmin[nv] * 100.0 - 1e-6) / 100.0) if nv != "vl" else (P0, r_l4)
            u = (P[1][0] - P[0][0], P[1][1] - P[0][1])
            nu = math.hypot(*u)
            v_ = (P[-1][0] - P[-2][0], P[-1][1] - P[-2][1])
            nv_ = math.hypot(*v_)
            axe = [(P[0][0] - 15.0 * u[0] / nu, P[0][1] - 15.0 * u[1] / nu)] + P + \
                  [(P[-1][0] + 15.0 * v_[0] / nv_, P[-1][1] + 15.0 * v_[1] / nv_)]
            d = B.balayage_detail(nv, axe)
            pg = d["polygone"]
            out.append({"trajectoire": t["id"], "mouvement": t.get("mouvement", ""), "vehicule": nv,
                        "carrefour": t.get("carrefour", ""), "de_branche": t.get("de_branche", ""),
                        "vers_branche": t.get("vers_branche", ""), "source": "L4" if abs(r_ax - r_l4) < 1e-9 else
                        f"L4, arc porté au rayon minimal du véhicule ({r_ax:.2f} m au lieu de {r_l4:.2f} m)",
                        "rayon_l4_m": _r(r_l4, 4), "rayon_axe_suivi_m": _r(r_ax, 4),
                        "faisable": bool(d["faisable"]), "rayon_axe_min_m": _r(d["rayon_axe_min"], 4),
                        "rayon_min_vehicule_m": _r(d["rayon_min_vehicule"], 4),
                        "exterieur": [[_r(x, 5), _r(y, 5)] for x, y in pg.exterieur]})
    dossier.mkdir(parents=True, exist_ok=True)
    f = dossier / nom
    f.write_text(json.dumps({"schema": "rg_balayages/0.2", "source": "trajectoires L4 (une seule source)",
                             "vehicules": list(VEHICULES), "balayages": out},
                            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return f, out


# ------------------------------------------------------------------------------------------------------- exports
def _pts(pr):
    return [[_r(p.position()[0]), _r(-p.position()[2])] for p in pr.points()]


def _val(o, nom):
    try:
        v = o.attribValue(nom)
    except hou.OperationFailed:
        return None
    if isinstance(v, float):
        return _r(v)
    if isinstance(v, tuple):
        return [(_r(x) if isinstance(x, float) else x) for x in v]
    return v


def exporter_carrefours(noeuds, dossier, info_bal):
    g = noeuds["carrefours"].geometry(2)
    br = []
    gb = g.findPointGroup("branche")
    noms_b = [a.name() for a in g.pointAttribs()]
    for p in (gb.points() if gb else []):
        br.append({n: _val(p, n) for n in noms_b if n not in ("P",)})
    prims = {}
    for grp in ("coin", "nez", "embouchure", "frontiere", "ilot", "ligne", "passage_libre"):
        gg = g.findPrimGroup(grp)
        if gg is None:
            continue
        noms_p = [a.name() for a in g.primAttribs()]
        prims[grp] = [{"points": _pts(pr), **{n: _val(pr, n) for n in noms_p},
                       **({"parties": [p.attribValue("partie") for p in pr.points()]} if grp in ("coin", "frontiere") else {})}
                      for pr in gg.prims()]
    gc = noeuds["carrefours_sol"].geometry(4)
    faces = []
    gf = gc.findPrimGroup("face")
    noms_f = [a.name() for a in gc.primAttribs()]
    for pr in (gf.prims() if gf else gc.prims()):
        faces.append({"points": _pts(pr), **{n: _val(pr, n) for n in noms_f}})
    av = list(gc.attribValue("rg_carrefours_avertissements")) if gc.findGlobalAttrib("rg_carrefours_avertissements") else []
    ent = []
    ge = noeuds["carrefours_sol"].geometry(2)
    for pr in ge.prims():
        ent.append({"id": pr.attribValue("id"), "xyz": [[_r(p.position()[0]), _r(-p.position()[2]), _r(p.position()[1])]
                                                          for p in pr.points()],
                    "intervalles": [{k: (_r(v) if isinstance(v, float) else v) for k, v in sorted(iv.items())}
                                    for iv in pr.attribValue("intervalles")],
                    "niv_s": [_r(x) for x in pr.attribValue("niv_s")],
                    "niv_z_pied": [_r(x) for x in pr.attribValue("niv_z_pied")],
                    "niv_z_tete": [_r(x) for x in pr.attribValue("niv_z_tete")]})
    d = {"schema": "rg_carrefours_l3/0.1", "branches": br, "solveur": prims, "faces": faces, "entites": ent,
         "avertissements": av, "balayages": info_bal}
    (dossier / "carrefours.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"branches": len(br), "coins": len(prims.get("coin", [])), "nez": len(prims.get("nez", [])),
            "faces": len(faces), "entites": len(ent), "avertissements": len(av)}


def mesurer_raccords(noeuds, dossier):
    """Étanchéité des raccords branche / carrefour (géométrie fabriquée) : pour chaque arête de bord d'une face visible
    du carrefour, rayon vertical à 2 cm de part et d'autre du milieu de l'arête ; l'une des deux sondes trouve la face
    voisine (branche ou carrefour) à |ΔZ| ≤ seuil, sinon l'arête est un bord libre (contour extérieur du domaine :
    bord du trottoir ou de l'accotement, compté à part)."""
    sol = noeuds["sol"].geometry(0)
    branches = noeuds["sol_branches"].geometry(0)
    car = noeuds["carrefours_sol"].geometry(0)
    vis = hou.Geometry()
    vis.merge(branches)
    pos, nrm, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()

    def sonde(geo, x, y, z0):
        best = None
        for h0 in (z0 + 0.5,):
            pr = geo.intersect(hou.Vector3(x, h0, -y), hou.Vector3(0, -1, 0), pos, nrm, uvw, None, 0, 1e9, 1e-7)
            if pr >= 0:
                best = float(pos[1])
        return best
    # arêtes de bord du maillage du carrefour (faces visibles et cachées : sol étanche)
    aretes = {}
    for pr in car.prims():
        vs = [v.point().number() for v in pr.vertices()]
        for a, b in zip(vs, vs[1:] + vs[:1]):
            k = (min(a, b), max(a, b))
            aretes[k] = aretes.get(k, 0) + 1
    P = car.pointFloatAttribValues("P")
    bord = [k for k, n in aretes.items() if n == 1]
    ecarts, libres, raccords = [], 0, 0
    pires = []
    # bords extérieurs du domaine (bord extérieur des trottoirs et accotements de coin) : bords libres attendus
    ext = []
    gc = noeuds["carrefours_sol"].geometry(4)
    for pr in gc.prims():
        try:
            ov = pr.attribValue("exterieur")
        except hou.OperationFailed:
            continue
        if ov:
            ov = list(ov)
            ext.append([(ov[i], ov[i + 1]) for i in range(0, len(ov) - 2, 3)])

    def sur_exterieur(x, y):
        for Q in ext:
            for (ax, ay), (bx, by) in zip(Q, Q[1:]):
                vx, vy = bx - ax, by - ay
                l2 = vx * vx + vy * vy
                u = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / l2)) if l2 > 1e-18 else 0.0
                if math.hypot(x - ax - u * vx, y - ay - u * vy) < 2e-3:
                    return True
        return False
    libres_int = []
    for a, b in bord:
        A = (P[3 * a], P[3 * a + 1], P[3 * a + 2])
        B = (P[3 * b], P[3 * b + 1], P[3 * b + 2])
        if abs(A[1] - B[1]) > 0.05 and math.hypot(A[0] - B[0], A[2] - B[2]) < 1e-6:
            continue                                    # arête verticale (mur)
        mx, my, mz = 0.5 * (A[0] + B[0]), -0.5 * (A[2] + B[2]), 0.5 * (A[1] + B[1])
        dx, dy = B[0] - A[0], -(B[2] - A[2])
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        nx, ny = -dy / L, dx / L
        z = None
        for f in (0.5, 0.25, 0.75):
            px_, py_ = A[0] + f * (B[0] - A[0]), -(A[2] + f * (B[2] - A[2]))
            pz_ = A[1] + f * (B[1] - A[1])
            for sgn in (1, -1):
                zz = sonde(vis, px_ + sgn * 0.005 * nx, py_ + sgn * 0.005 * ny, pz_)
                if zz is not None and abs(zz - pz_) < 0.02:
                    z, mz = zz, pz_
                    break
            if z is not None:
                break
        if z is None:
            libres += 1
            if not sur_exterieur(mx, my):
                libres_int.append([_r(mx, 3), _r(my, 3), _r(mz, 4)])
            continue
        raccords += 1
        ecarts.append(abs(z - mz))
        pires.append((abs(z - mz), _r(mx, 3), _r(my, 3), _r(mz, 4), _r(z, 4)))
    m = {"aretes_de_bord": len(bord), "raccords_branches": raccords, "bords_libres": libres,
         "ecart_max_m": _r(max(ecarts) if ecarts else 0.0, 7),
         "pires": [list(x) for x in sorted(pires, reverse=True)[:8]],
         "bords_libres_hors_exterieur": len(libres_int), "exemples_bords_libres_hors_exterieur": libres_int[:12],
         "note": "écart vertical entre le bord du sol du carrefour et le sol de la branche voisine (sondes à 5 mm du "
                 "milieu de l'arête, puis au quart et aux trois quarts) ; bords libres = contour extérieur (trottoirs, accotements) et arêtes sans voisin"}
    (dossier / "mesures_l3.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return m


# ------------------------------------------------------------------------------------------------------- rendus
def st_route0(geo, x, y):
    """(s, t) d'un point local (x, y) dans le repère de la route 0 du rendu (rendu_l2b.Route : polyligne échantillonnée,
    prolongée par ses tangentes au-delà des bouts)."""
    pr = geo.prims()[0]
    pts = pr.points()
    S = [p.attribValue("s") for p in pts]
    P = [(p.position()[0], -p.position()[2]) for p in pts]
    best = None
    n = len(P)
    for i in range(n - 1):
        (ax, ay), (bx, by) = P[i], P[i + 1]
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        if L2 < 1e-12:
            continue
        u = ((x - ax) * vx + (y - ay) * vy) / L2
        if i > 0:
            u = max(u, 0.0)
        if i < n - 2:
            u = min(u, 1.0)
        fx, fy = ax + u * vx, ay + u * vy
        d = math.hypot(x - fx, y - fy)
        if best is None or d < best[0]:
            L = math.sqrt(L2)
            t = ((x - fx) * (-vy) + (y - fy) * vx) / L
            best = (d, S[i] + u * (S[i + 1] - S[i]), t)
    return best[1], best[2]


def voie_entrante(m, rid, s):
    """t du centre de la voie entrante la plus à droite (bande voie_* de sens « avant ») du profil de la route en s."""
    r = next(x for x in m["routes"] if x["id"] == rid)
    sec = [x for x in r["sections"] if x["s0"] <= s + 1e-9][-1]
    pr = next(x for x in m["profils"] if x["id"] == sec["profil"])
    w = [float(b["largeur"]) if isinstance(b["largeur"], (int, float)) else 3.0 for b in pr["bandes"]]
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


def vues_carrefour(m, car_geo, graphe_geo, vues):
    """Caméras du carrefour (repère (s, t, h) de la route 0 du rendu) : conducteur sur la branche à ligne CÉDEZ / STOP
    (sinon la branche la plus large), 30 m avant la limite de la chaussée abordée, voie entrante de droite, 1,20 m ;
    oblique 3/4 du carrefour depuis le sud-ouest (scènes phares) ; vue de dessus centrée sur le carrefour."""
    gb = car_geo.findPointGroup("branche")
    brs = list(gb.points())
    c = brs[0].attribValue("centre")
    cx, cy = c[0], c[1]
    def score(p):
        reg = p.attribValue("regime")
        lt = p.attribValue("ligne_type")
        return (2 if reg in ("cedez", "stop") or lt in ("CEDEZ", "STOP") else 0,
                abs(p.attribValue("t_g") - p.attribValue("t_d")), -p.attribValue("rang"))
    b = max(brs, key=score)
    P0 = b.attribValue("Pf")
    d = b.attribValue("dir")
    n = b.attribValue("nrm")
    tl = voie_entrante(m, b.attribValue("route"), b.attribValue("s_front") - 1.0)
    oeil = (P0[0] - 30.0 * d[0] + tl * n[0], P0[1] - 30.0 * d[1] + tl * n[1])
    cible = (P0[0] + 10.0 * d[0] + tl * n[0], P0[1] + 10.0 * d[1] + tl * n[1])
    so, to = st_route0(graphe_geo, *oeil)
    sc_, tc = st_route0(graphe_geo, *cible)
    propres = {"conducteur_carrefour": ((so, to, 1.20), (sc_, tc, 0.5), 24)}
    if "oblique" in vues:
        a = math.radians(225.0)
        oe = (cx + 34.0 * math.cos(a), cy + 34.0 * math.sin(a))
        s1, t1 = st_route0(graphe_geo, *oe)
        s2, t2 = st_route0(graphe_geo, cx, cy)
        propres["oblique_carrefour"] = ((s1, t1, 26.0), (s2, t2, 0.0), 24)
    xs, ys = [], []
    for pr in car_geo.findPrimGroup("coin").prims():
        for p in pr.points():
            xs.append(p.position()[0])
            ys.append(-p.position()[2])
    ext = max(max(abs(x - cx) for x in xs), max(abs(y - cy) for y in ys)) if xs else 20.0
    largeur = min(max(2.0 * ext + 6.0, 36.0), 110.0)
    return propres, (cx, cy), largeur, b.attribValue("branche")


NOMS_VUES = {"conducteur": "conducteur_carrefour", "oblique": "oblique_carrefour"}


def installer_rendu(vues, propres, centre, largeur, branche=""):
    """Vue de dessus centrée sur le carrefour (largeur du domaine), vues propres (conducteur, oblique) ; planche
    ≤ 1092 px."""
    import rendu_l2b as RB
    import planches as PL
    origine = RB.rendre_scene
    dessus_origine = RB._dessus

    def rendre_scene(n2, n2b, sc, dossier, parent, decor_etape2=False, echantillons=None):
        def dessus(stage, c, z, larg, res):
            return dessus_origine(stage, centre, z, largeur, res)
        RB._dessus = dessus
        noms = [NOMS_VUES.get(v, v) for v in vues]
        try:
            origine(n2, n2b, sc, dossier, parent, vues=propres, decor_etape2=decor_etape2,
                    seulement=noms, echantillons=echantillons)
        finally:
            RB._dessus = dessus_origine
        d = Path(dossier) / "rendus"
        pngs = {p.stem: p for p in d.glob("*.png") if not p.stem.startswith("planche")}
        PL.planche_vues(sc, pngs, [v for v in noms if v in pngs], d / f"planche_{sc}.png",
                        legendes={"conducteur_carrefour": f"conducteur (1,20 m), branche {branche}",
                                  "oblique_carrefour": "vue oblique 3/4 du carrefour"})
    return rendre_scene


# ------------------------------------------------------------------------------------------------------- pilote
def fabriquer(entrees, sortie, signatures, rendus=False, vues=VUES_DEFAUT, avec_balayages=True):
    lire, car, graphe, prof, n2, n2b = reseau()
    produits = []
    for e in entrees:
        scene, chemin_modele, info = FG.preparer_entree(e, sortie)
        dsc = Path(sortie) / scene
        d1 = dsc / "l1"
        d3 = dsc / "l3"
        d1.mkdir(parents=True, exist_ok=True)
        d3.mkdir(parents=True, exist_ok=True)
        info_bal = []
        if avec_balayages:
            fb, bal = balayages(chemin_modele, TMP_L3 / scene)
            car.parm("balayages").set(str(fb).replace("\\", "/"))
            info_bal = [{k: v for k, v in b.items() if k != "exterieur"} for b in bal]
        else:
            car.parm("balayages").set("")
        lire.parm("fichier").set(str(chemin_modele).replace("\\", "/"))
        for n in (lire, car, graphe, prof):
            try:
                n.cook(force=True)
            except hou.OperationFailed:
                pass
            err = [f"{c.path()} : {x}" for c in (n,) + n.allSubChildren() for x in c.errors()]
            if err:
                raise SystemExit(f"{scene} : erreurs de cuisson" + chr(10) + chr(10).join(err))
        donnees = FG.extraire(lire, graphe, prof)
        courbes = {"schema": "rg_courbes_controle/0.1", "scene": scene, "lot": "L1 (+ L3 : routes coupées au carrefour)",
                   "modele": {"fichier": FG.rel(chemin_modele), "sha256": FG.sha256(chemin_modele)}}
        courbes.update(donnees)
        (d1 / "courbes_controle.json").write_text(json.dumps(courbes, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
        man1 = {"schema": "rg_manifest/0.1", "pilote": VERSION, "scene": scene, "entree": info, "modele": courbes["modele"],
                "houdini": hou.applicationVersionString(), "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
                "hda": signatures, "parametres": donnees["parametres"], "comptes": donnees["comptes"],
                "avertissements": FG.avertissements(lire, car, graphe, prof),
                "fichiers": {"courbes_controle.json": FG.sha256(d1 / "courbes_controle.json")}}
        (d1 / "manifest_l1.json").write_text(json.dumps(man1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        cuire(n2, scene)
        d2, man2 = F2.fabriquer_scene(n2, scene, dsc, signatures, info)
        d2b, man2b = F2B.fabriquer_scene(n2b, scene, dsc, signatures, info)
        c3 = exporter_carrefours(n2, d3, info_bal)
        m3 = mesurer_raccords(n2, d3)
        fichiers = {p.name: sha256(p) for p in sorted(d3.iterdir()) if p.is_file() and p.name != "manifest_l3.json"}
        man = {"schema": "rg_manifest_l3/0.1", "pilote": VERSION, "scene": scene, "entree": info,
               "houdini": hou.applicationVersionString(), "hda": signatures, "comptes": c3, "raccords": m3,
               "fichiers": fichiers}
        (d3 / "manifest_l3.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{scene} : L3 {c3} ; raccords {m3['raccords_branches']} (écart max {m3['ecart_max_m']} m), "
              f"bords libres {m3['bords_libres']} ; L2 sol {man2['controles_houdini']['faces_sol']} faces -> {FG.rel(dsc)}")
        if rendus:
            m = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
            vv = VUES_PHARES.get(scene, vues)
            propres, centre, largeur, bcond = vues_carrefour(m, car.geometry(2), graphe.geometry(), vv)
            print(f"{scene} : rendus {list(vv)} ; conducteur sur {bcond} ; dessus {largeur:.1f} m")
            installer_rendu(vv, propres, centre, largeur, bcond)(n2, n2b, scene, dsc, lire.parent())
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
    ap.add_argument("--sans-balayages", action="store_true")
    a = ap.parse_args()
    signatures = construire_hda(forcer=a.construire_hda)
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items()))
    produits = fabriquer(a.entrees, a.sortie, signatures, rendus=a.rendus, vues=tuple(v for v in a.vues.split(",") if v),
                         avec_balayages=not a.sans_balayages)
    if a.verifier_determinisme:
        autre = TMP_L3 / "determinisme"
        r = subprocess.run([sys.executable, __file__] + a.entrees + ["--sortie", str(autre)],
                           env=dict(os.environ, RG_PILOTE_ENV=""), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("second processus en échec")
        from commun import determinisme as DET
        ecarts, n = DET.comparer([str(Path(p) / "l1") for p in produits], autre, True, True)
        # fichiers du lot L3 (manifeste : chemins de sortie retirés)
        for p in produits:
            for f in sorted((Path(p) / "l3").glob("*.json")):
                if f.name == "manifest_l3.json":
                    continue
                g = autre / Path(p).name / "l3" / f.name
                n += 1
                if not g.exists() or g.read_bytes() != f.read_bytes():
                    ecarts.append(str(f))
        print("déterminisme :", f"identique ({n} fichiers)" if not ecarts else f"DIFFÉRENT : {ecarts}")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
