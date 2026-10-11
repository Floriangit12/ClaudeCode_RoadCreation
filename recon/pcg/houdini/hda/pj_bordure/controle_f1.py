"""Vues de contrôle des HDA de l'agent F1 (pj::bordure, pj::caniveau, pj::sol, pj::ilot) : rendus Karma XPU (husk).

    hython recon/pcg/houdini/hda/pj_bordure/controle_f1.py [--vues a,b] [--sortie DIR] [--res 1600]

Scène : pj::lire_description (boîte autour des vues, altitude = nivellement) -> HDA de branche installées (celles qui
manquent sont sautées) -> couleur d'aperçu par materiau_id (albédo de materiaux_sol.json, variation par élément) ->
Solaris (SOP Import, MaterialX lisant displayColor, soleil + ciel, caméras perspective) -> USD -> husk.
Les caméras sont posées en repère local (x, y) avec un z relatif au nivellement (nivellement_requete, numpy).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
HDA = ICI.parent
sys.path.insert(0, str(HDA / "commun"))
import pj_hda_outils as O  # noqa: E402

RACINE = O.RACINE
BASE = RACINE / "recon/out/paquet_jardin/v2/description/base"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda/controle"
sys.path.insert(0, str(RACINE / "recon/pcg/decrire"))

# vue : (boîte d'emprise locale x0, y0, x1, y1), caméra (x, y, dz au-dessus du sol), cible (x, y, dz), focale (mm)
VUES = {
    # file de T2 (K-0627) vue depuis la chaussée : joints, coupes, chanfreins d'about
    "f1_file_joints": ((-46, -50, -32, -38), (-39.70, -47.48, 0.6), (-38.36, -44.51, 0.08), 35.0),
    # gros plan au ras de la file de K-0627 (alignement des éléments, joints, assise sur la chaussée)
    "f1_file_gros_plan": ((-44, -48, -34, -38), (-40.15, -46.65, 0.32), (-37.35, -44.20, 0.08), 35.0),
    # abaissé de K-0385 (bateau, chartières de raccord, BEV-0385-1) vu depuis la chaussée
    "f1_abaisse_bev": ((8, -4, 24, 10), (14.71, 5.82, 1.5), (16.28, 2.15, 0.0), 28.0),
    # îlot de BRF I-0333 (nez R 0,43 m, ceinture T2, éclats débordant sur la chaussée)
    "f1_ilot_brf": ((-52, -58, -38, -44), (-49.0, -55.5, 1.7), (-45.0, -50.6, 0.0), 30.0),
    # zone de la capture 7 (trottoirs où la v1 montrait des falaises) : vue oblique haute et vue au sol
    "f1_trottoir_capture7": ((-46, -56, -12, -22), (-16.0, -52.0, 14.0), (-30.0, -38.0, 0.0), 28.0),
    "f1_capture7_sol": ((-34, -44, -12, -22), (-14.5, -40.0, 2.2), (-25.0, -28.5, 0.0), 26.0),
    # gros plan de K-0388 devant le massif de BRF S-0281a (capture 7)
    "f1_capture7_bordure": ((-30, -42, -16, -30), (-25.0, -34.6, 0.9), (-20.8, -37.6, 0.0), 30.0),
    # quai bus et caniveau CS2 de K-0381 (Verdun SO)
    "f1_caniveau": ((-30, -24, -14, -8), (-24.7, -21.2, 1.5), (-23.4, -16.2, 0.0), 28.0),
    # vue de dessus du centre (contrôle d'ensemble)
    "f1_vue_dessus_centre": ((-60, -60, 30, 30), (-15.0, -15.0, 120.0), (-15.0, -14.9, 0.0), 35.0),
}
BRANCHES_F1 = (("bordures", "pj::bordure::1.0"), ("caniveaux", "pj::caniveau::1.0"), ("sol", "pj::sol::1.0"),
               ("ilots", "pj::ilot::1.0"))


def albedos():
    m = json.loads((RACINE / "assets/specs/materiaux_sol.json").read_text(encoding="utf-8"))["materiaux"]
    t = {}
    for k, v in m.items():
        a = v.get("albedo_cible_lineaire") or (v.get("texture_mesuree") or {}).get("albedo_moyen_lineaire") or [0.3] * 3
        t[k] = [float(x) for x in a]
    t.update({"mortier_joint": [0.05, 0.05, 0.048], "mortier_clair": [0.25, 0.245, 0.23],
              "eclat_brf": [0.16, 0.11, 0.07], "eclat_gravier": [0.2, 0.2, 0.19], "PJ_Neutre": [0.5, 0.5, 0.5]})
    return t


VEX_COULEUR = r"""
// Couleur d'aperçu : albédo du materiau_id (materiaux_sol.json), variation par élément (graine) pour lire les joints.
string m = s@materiau_id;
int i = find(s[]@mats, m);
vector c = i >= 0 ? set(f[]@ar[i], f[]@ag[i], f[]@ab[i]) : {0.8, 0.1, 0.8};
int g = hasprimattrib(0, "graine") ? i@graine : random_shash(s@id);
float v = 1.0 + 0.10 * (rand(g % 100003) - 0.5);
v@Cd = c * v;
"""


VEX_PLANCHE = r"""
// planche de prototypes : un prototype par case (ordre alphabétique des assets), rangées de 6, pas 1,3 m x 0,6 m
string noms[] = uniquevals(0, "prim", "asset");
int k = find(noms, s@asset);
int pts[] = primpoints(0, @primnum);
"""
VEX_PLANCHE_PT = r"""
// déplacement des points vers la case de leur prototype (Y haut ; X = s, Z = −u)
string noms[] = uniquevals(0, "prim", "asset");
int prs[] = pointprims(0, @ptnum);
string a = prim(0, "asset", prs[0]);
int k = find(noms, a);
@P += set((k % 4) * 1.5, 0, -(k / 4) * 0.9);
"""


def planche_prototypes(sortie, res=2000, motif="element_T2_L994_v* element_T2_L494_v0 coupe_T2_L494 coupe_T2_L294 joint_T2 jointf_T2 chartiere_T2145* chartiere_T2140* element_A2_L994_v0 element_T3_L994_v0"):
    """Planche des prototypes de pj::bordure (sortie 3) : éléments, coupes, chartières, joints, épaufrures."""
    O.installer_tout()
    geo = hou.node("/obj").createNode("geo", "planche_f1")
    lire = geo.createNode("pj::lire_description::1.0", "lire")
    lire.parm("dossier").set(BASE.as_posix())
    lire.parm("emprise").set("pilote")
    e = geo.createNode("blast", "b")
    e.setInput(0, lire)
    e.parm("group").set("b_bordures")
    e.parm("negate").set(1)
    f = geo.createNode("pj::bordure::1.0", "fab")
    f.setInput(0, e)
    f.setInput(1, lire, 1)
    sel = geo.createNode("blast", "selection")
    sel.setInput(0, f, 2)
    sel.parm("group").set(" ".join(f"@asset={m}" for m in motif.split()))
    sel.parm("negate").set(1)
    w = geo.createNode("attribwrangle", "cases")
    w.parm("class").set(2)
    w.parm("snippet").set(VEX_PLANCHE_PT)
    w.setInput(0, sel)
    col = geo.createNode("attribwrangle", "couleur")
    col.parm("class").set(1)
    col.parm("snippet").set('v@Cd = s@materiau_id == "mortier_joint" ? {0.05, 0.05, 0.05} : (s@materiau_id == '
                            '"mortier_clair" ? {0.3, 0.3, 0.28} : {0.42, 0.43, 0.40});')
    col.setInput(0, w)
    out = geo.createNode("null", "OUT")
    out.setInput(0, col)
    g = out.geometry()
    n = len(set(p.attribValue("asset") for p in g.prims()))
    st = hou.node("/stage")
    si = st.createNode("sopimport", "planche")
    si.parm("soppath").set(out.path())
    si.parm("enable_savepath").set(0)
    si.parm("copycontents").set("on")
    si.parm("enable_pathprefix").set(1)
    si.parm("pathprefix").set("/controle/geo")
    rangees = (n + 3) // 4
    c = st.createNode("camera", "camera_planche")
    c.setInput(0, si)
    c.parm("primpath").set("/controle/camera_f1_planche_prototypes")
    cx, cz = 1.5 * 1.5, -(rangees - 1) * 0.9 / 2
    for k, val in zip(("tx", "ty", "tz"), (cx - 0.8, 1.1 + 0.55 * rangees, cz + 1.6 + 0.75 * rangees)):
        c.parm(k).set(val)
    c.parm("lookatenable").set(1)
    for k, val in zip(("lookatpositionx", "lookatpositiony", "lookatpositionz"), (cx, 0.1, cz)):
        c.parm(k).set(val)
    c.parm("aspectratiox").set(16.0)
    c.parm("aspectratioy").set(10.0)
    c.parm("focalLength").set(35.0)
    c.parm("horizontalAperture").set(36.0)
    _rendre_stage(c, ["f1_planche_prototypes"], sortie, res, "planche_prototypes_bordures")
    return n


def scene(boite, branches):
    O.installer_tout()
    obj = hou.node("/obj")
    geo = obj.createNode("geo", "controle_f1")
    lire = geo.createNode("pj::lire_description::1.0", "lire")
    lire.parm("dossier").set(BASE.as_posix())
    lire.parm("emprise").set("boite")
    lire.parmTuple("boite_min").set(boite[:2])
    lire.parmTuple("boite_max").set(boite[2:])
    lire.parm("altitude").set("nivellement")
    fus = geo.createNode("merge", "fusion")
    k = 0
    faits = []
    for b, t in BRANCHES_F1:
        if b not in branches:
            continue
        nt = hou.nodeType(hou.sopNodeTypeCategory(), t)
        if nt is None or nt.definition() is None:
            continue
        e = geo.createNode("blast", f"entrees_{b}")
        e.setInput(0, lire)
        e.parm("group").set(f"b_{b}")
        e.parm("negate").set(1)
        f = geo.createNode(t, f"fab_{b}")
        for i, src in enumerate((e, (lire, 1), lire)[:nt.maxNumInputs()]):
            if isinstance(src, tuple):
                f.setInput(i, src[0], src[1])
            else:
                f.setInput(i, src)
        if b == "ilots" and f.parm("couverture_dense"):
            f.parm("couverture_dense").set(1)          # aperçu : couverture dense d'éclats (dans UE : matériau Nanite)
            f.parm("densite_facteur").set(0.35)
        fus.setInput(k, f)
        k += 1
        faits.append(b)
    al = albedos()
    det = geo.createNode("attribwrangle", "table")
    det.parm("class").set(0)
    noms = sorted(al)
    det.parm("snippet").set("s[]@mats = array(%s);\nf[]@ar = array(%s);\nf[]@ag = array(%s);\nf[]@ab = array(%s);\n" % (
        ", ".join(f'"{n}"' for n in noms), ", ".join(str(al[n][0]) for n in noms),
        ", ".join(str(al[n][1]) for n in noms), ", ".join(str(al[n][2]) for n in noms)))
    det.setInput(0, fus)
    col = geo.createNode("attribwrangle", "couleur")
    col.parm("class").set(1)
    col.parm("snippet").set(VEX_COULEUR)
    col.setInput(0, det)
    ad = geo.createNode("attribdelete", "garder")
    ad.setInput(0, col)
    ad.parm("negate").set(1)
    ad.parm("ptdel").set("")
    ad.parm("vtxdel").set("N uv")
    ad.parm("primdel").set("Cd")
    ad.parm("dtldel").set("")
    out = geo.createNode("null", "OUT")
    out.setInput(0, ad)
    out.setDisplayFlag(True)
    out.setRenderFlag(True)
    return out, faits


def camera_z(niv, x, y, dz):
    import numpy as np
    z = niv.z(x, y)[0]
    if not np.isfinite(z):
        z = 0.0
    return float(z) + dz


def rendre(vues, sortie, res):
    from nivellement_requete import Nivellement
    niv = Nivellement(BASE)
    xs0 = min(VUES[v][0][0] for v in vues)
    ys0 = min(VUES[v][0][1] for v in vues)
    xs1 = max(VUES[v][0][2] for v in vues)
    ys1 = max(VUES[v][0][3] for v in vues)
    t0 = time.time()
    out, faits = scene((xs0, ys0, xs1, ys1), [b for b, _ in BRANCHES_F1])
    g = out.geometry()
    print(f"   scène : branches {faits}, {len(g.prims())} primitives, cuisson {time.time() - t0:.0f} s")
    st = hou.node("/stage")
    si = st.createNode("sopimport", "geometrie")
    si.parm("soppath").set(out.path())
    si.parm("enable_savepath").set(0)
    si.parm("copycontents").set("on")
    si.parm("enable_pathprefix").set(1)
    si.parm("pathprefix").set("/controle/geo")
    prec = si
    for v in vues:
        _, cam, cible, focale = VUES[v]
        c = st.createNode("camera", f"camera_{v}")
        c.setInput(0, prec)
        c.parm("primpath").set(f"/controle/camera_{v}")
        cz = camera_z(niv, cam[0], cam[1], cam[2])
        tz = camera_z(niv, cible[0], cible[1], cible[2])
        for k, val in zip(("tx", "ty", "tz"), (cam[0], cz, -cam[1])):
            c.parm(k).set(val)
        c.parm("lookatenable").set(1)
        for k, val in zip(("lookatpositionx", "lookatpositiony", "lookatpositionz"), (cible[0], tz, -cible[1])):
            c.parm(k).set(val)
        c.parm("aspectratiox").set(16.0)
        c.parm("aspectratioy").set(10.0)
        c.parm("focalLength").set(focale)
        c.parm("horizontalAperture").set(36.0)
        c.parm("clippingRange1").set(0.05)
        c.parm("clippingRange2").set(2000.0)
        prec = c
    return _rendre_stage(prec, vues, sortie, res, "controle_f1")


def _rendre_stage(prec, vues, sortie, res, nom_usd, prefixe=None):
    """Matériau (displayColor), soleil, ciel, Karma XPU, USD ROP et rendus husk des caméras /controle/camera_<vue>."""
    st = hou.node("/stage")
    ml = st.createNode("materiallibrary", "materiau")
    ml.setInput(0, prec)
    sh = ml.createNode("mtlxstandard_surface", "couleur_sommets")
    lu = ml.createNode("mtlxgeompropvalue", "lire_couleur")
    lu.parm("signature").set("color3")
    lu.parm("geomprop").set("displayColor")
    sh.setInput(sh.inputIndex("base_color"), lu)
    sh.parm("specular").set(0.15)
    sh.parm("specular_roughness").set(0.6)
    ml.parm("materials").set(1)
    ml.parm("matnode1").set("couleur_sommets")
    ml.parm("matpath1").set("/controle/materiaux/couleur_sommets")
    ml.parm("assign1").set(1)
    ml.parm("geopath1").set("/controle/geo/**")
    sol = st.createNode("distantlight::2.0", "soleil")
    sol.setInput(0, ml)
    sol.parm("primpath").set("/controle/soleil")
    sol.parm("rx").set(-35)
    sol.parm("ry").set(-140)
    sol.parm("xn__inputsintensity_i0a").set(2.6)
    sol.parm("xn__inputsangle_m4a").set(0.53) if sol.parm("xn__inputsangle_m4a") else None
    dome = st.createNode("domelight::3.0", "ciel")
    dome.setInput(0, sol)
    dome.parm("primpath").set("/controle/ciel")
    dome.parm("xn__inputsintensity_i0a").set(0.55)
    kp = st.createNode("karmarenderproperties", "rendu")
    kp.setInput(0, dome)
    kp.parm("camera").set(f"/controle/camera_{vues[0]}")
    kp.parm("engine").set("xpu")
    kp.parm("res_mode").set("manual")
    for n in ("resolutionx", "resolutiony"):
        kp.parm(n).lock(False)
        kp.parm(n).deleteAllKeyframes()
    kp.parm("resolutionx").set(res)
    kp.parm("resolutiony").set(int(res * 10 / 16))
    kp.parm("samplesperpixel").set(32)
    rop = st.createNode("usd_rop", "rop")
    rop.setInput(0, kp)
    sortie = Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    usd = sortie / f"{nom_usd}.usdc"
    for p, val in (("lopoutput", usd.as_posix()), ("savetimeinfo", 0), ("flattensoplayers", 1),
                   ("clearhoudinicustomdata", 1)):
        rop.parm(p).set(val)
    rop.render()
    husk = Path(sys.executable).parent / "husk.exe"
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    images = []
    for v in vues:
        png = sortie / f"{prefixe + '_' + v if prefixe else v}.png"
        cmd = [str(husk), "-R", "BRAY_HdKarmaXPU", "--settings", "/Render/rendersettings", "--camera",
               f"/controle/camera_{v}", "--res", str(res), str(int(res * 10 / 16)), "--frame", "1", "--output",
               png.as_posix(), "--make-output-path", usd.as_posix()]
        t = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not png.exists():
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit(f"rendu {v} en échec")
        print(f"   {v} : {time.time() - t:.0f} s -> {png}")
        images.append(png)
    usd.unlink(missing_ok=True)
    return images


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vues", default=",".join(VUES))
    ap.add_argument("--sortie", default=str(SORTIE))
    ap.add_argument("--res", type=int, default=1600)
    ap.add_argument("--planche", action="store_true", help="planche des prototypes de bordure")
    a = ap.parse_args()
    if a.planche:
        print("   prototypes :", planche_prototypes(a.sortie, a.res))
    else:
        rendre(a.vues.split(","), a.sortie, a.res)
