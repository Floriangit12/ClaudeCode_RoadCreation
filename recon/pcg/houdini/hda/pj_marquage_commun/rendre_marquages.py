"""Vues de contrôle des HDA de marquage (Karma XPU, husk) et planche de comparaison au levé GAM 2026.

    hython recon/pcg/houdini/hda/pj_marquage_commun/rendre_marquages.py [--vues v1,v2] [--res 1600]

Ouvre la scène maîtresse (sorties fab_* des branches de marquage, déjà câblées), ajoute en mémoire un réseau
d'aperçu (sol : HeightField de nivellement maillé et coloré par classe de surface ; marquages : maillages des quatre
branches + instances de symboles dépaquetées), écrit un USD par vue dans le dossier de travail et le rend avec husk.
Vues (README_HDA.md § 7) :
    fleche_td_tad_1m30     flèche TD_TAD MF-6014 (Verdun SO, plan 2025) vue d'un conducteur, œil à 1,30 m
    detail_fleche_0m25     pointe de la même flèche à 0,25 m (peinture extrudée de 3 mm, chanfrein de 1 mm)
    zebra_verdun_so_1m60   zébra MP-5246 (Verdun SO, levé GAM) vu d'un piéton, œil à 1,60 m
    traversee_cyclable     traversée cyclable Chronovélo MP-0001 (centre), vue oblique
    zigzag_dessus, hachures_dessus   zigzag d'arrêt de bus MZ-5300 et hachures MZ-5160 vus de dessus
    centre_dessus          vue de dessus du centre (emprise de l'image 12 : x -24..24, y -34..14)
plus controle/marquages_planche_centre.png : ortho 2022 + levé GAM (magenta) | ortho + marquages fabriqués | rendu.
Aucune géométrie de marquage n'est produite ici : le script ne fait que lire les sorties des HDA et rendre.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parents[0] / "commun"))
import pj_hda_outils as O  # noqa: E402

RACINE = O.RACINE
HIP = RACINE / "recon/pcg/houdini/paquet_jardin_pcg.hip"
DESCRIPTION = RACINE / "recon/out/paquet_jardin/v2/description/base"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda"
ORTHO = RACINE / "data/sites/paquet_jardin/ortho5cm_2022"
GAM = RACINE / "data/sites/paquet_jardin/etat_2026/signalisation_horizontale_lin_L93.geojson"
OX, OY = 917279.43, 6460289.98
BRANCHES = ("marquages_lignes", "passages", "symboles", "zones")
CENTRE = (-24.0, -34.0, 24.0, 14.0)            # emprise de l'image 12 (couverture_marquages_a_centre)

VEX_SOL = r"""
// Aperçu : couleur du sol par classe de la surface sous le point (rayon vertical sur les surfaces à plat, entrée 2).
vector pos, uvw;
int pr = intersect(1, set(@P.x, 50.0, @P.z), {0, -100, 0}, pos, uvw);
string cl = pr >= 0 ? prim(1, "classe", pr) : "";
vector c = {0.075, 0.075, 0.075};
if (cl == "trottoir" || cl == "quai_bus" || cl == "autre") c = {0.20, 0.19, 0.18};
else if (cl == "espace_vert" || cl == "terre_plein_vegetal") c = {0.045, 0.075, 0.03};
else if (cl == "emprise_bordure") c = {0.38, 0.37, 0.35};
else if (cl == "ilot") c = {0.17, 0.15, 0.12};
else if (cl == "piste_cyclable") c = {0.09, 0.085, 0.08};
v@Cd = c;
"""

VEX_PEINTURE = r"""
// Aperçu : peinture blanche ou jaune, usure (0-1) mêlée vers l'enrobé
string m = s@materiau_id;
vector c = find(m, "jaune") >= 0 ? {0.78, 0.56, 0.06} : {0.86, 0.86, 0.83};
v@Cd = lerp(c, {0.09, 0.09, 0.09}, 0.35 * f@usure);
"""


def l93(x, y):
    return x + OX, y + OY


def vues(description):
    """Caméras (repère local Z haut) calculées depuis la description (positions des entités)."""
    feats = {f["properties"]["id"]: f for f in json.load(open(description / "marquages.geojson", encoding="utf-8"))["features"]}

    def loc(c):
        return c[0] - OX, c[1] - OY

    out = {}
    f = feats["MF-6014"]["properties"]
    ox, oy = loc(f["pose"]["point_l93"])
    cap = math.radians(f["pose"]["cap_deg"])
    d = (math.cos(cap), math.sin(cap))
    out["fleche_td_tad_1m30"] = {"oeil": (ox - 9.0 * d[0], oy - 9.0 * d[1], 1.30), "cible": (ox + 2.0 * d[0], oy + 2.0 * d[1], 0.0),
                                 "focale": 24.0, "res": (1600, 900), "boite": (ox - 16, oy - 16, ox + 16, oy + 16)}
    n = (-d[1], d[0])
    tip = (ox + 4.0 * d[0], oy + 4.0 * d[1])
    out["detail_fleche_0m25"] = {"oeil": (tip[0] + 0.9 * d[0] + 0.45 * n[0], tip[1] + 0.9 * d[1] + 0.45 * n[1], 0.25),
                                 "cible": (ox + 3.2 * d[0], oy + 3.2 * d[1], 0.0), "focale": 35.0, "res": (1600, 900),
                                 "boite": (ox - 10, oy - 10, ox + 10, oy + 10)}
    c = feats["MP-5246"]["geometry"]["coordinates"]
    a, b = loc(c[0]), loc(c[-1])
    L = math.dist(a, b)
    u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    out["zebra_verdun_so_1m60"] = {"oeil": (a[0] - 2.2 * u[0] + 0.6 * u[1], a[1] - 2.2 * u[1] - 0.6 * u[0], 1.60),
                                   "cible": (b[0] + 1.0 * u[0], b[1] + 1.0 * u[1], 0.0), "focale": 20.0, "res": (1600, 900),
                                   "boite": (min(a[0], b[0]) - 14, min(a[1], b[1]) - 14, max(a[0], b[0]) + 14, max(a[1], b[1]) + 14)}
    c = feats["MP-0001"]["geometry"]["coordinates"][0]
    a, b = loc(c[0]), loc(c[-1])
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    L = math.dist(a, b)
    u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    n = (-u[1], u[0])
    out["traversee_cyclable"] = {"oeil": (m[0] + 6.5 * n[0] - 2.0 * u[0], m[1] + 6.5 * n[1] - 2.0 * u[1], 2.2),
                                 "cible": (m[0], m[1], 0.0), "focale": 22.0, "res": (1600, 900),
                                 "boite": (m[0] - 15, m[1] - 15, m[0] + 15, m[1] + 15)}
    for nom, ident in (("zigzag_dessus", "MZ-5300"), ("hachures_dessus", "MZ-5160")):
        g = feats[ident]["geometry"]
        cs = g["coordinates"] if g["type"] == "LineString" else g["coordinates"][0]
        xs = [c[0] - OX for c in cs]
        ys = [c[1] - OY for c in cs]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        larg = max(max(xs) - min(xs), max(ys) - min(ys)) + 6.0
        out[nom] = {"ortho": (cx, cy, larg), "res": (1400, 1400),
                    "boite": (cx - larg / 2 - 1, cy - larg / 2 - 1, cx + larg / 2 + 1, cy + larg / 2 + 1)}
    x0, y0, x1, y1 = CENTRE
    out["centre_dessus"] = {"ortho": ((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0), "res": (2000, 2000),
                            "boite": (x0 - 1, y0 - 1, x1 + 1, y1 + 1)}
    out["centre_dessus_marques"] = dict(out["centre_dessus"], sans_sol=True)
    return out


def reseau_marquages(geo):
    """SOP : maillages des branches de marquage (sortie 1) + instances de symboles dépaquetées (sortie 4), colorés."""
    fus = geo.createNode("merge", "marquages")
    k = 0
    for b in BRANCHES:
        om = geo.createNode("object_merge", f"m_{b}")
        om.parm("objpath1").set(f"/obj/paquet_jardin/SORTIE_{b}")
        fus.setInput(k, om)
        k += 1
    om = geo.createNode("object_merge", "m_instances")
    om.parm("objpath1").set("/obj/paquet_jardin/fab_symboles/APERCU_INSTANCES")
    up = geo.createNode("unpack", "depaqueter")
    up.setInput(0, om)
    up.parm("transfer_attributes").set("materiau_id usure")
    fus.setInput(k, up)
    col = geo.createNode("attribwrangle", "peinture")
    col.setInput(0, fus)
    col.parm("class").set(1)
    col.parm("snippet").set(VEX_PEINTURE)
    ad = geo.createNode("attribdelete", "attributs")
    ad.setInput(0, col)
    ad.parm("negate").set(1)
    ad.parm("ptdel").set("")
    ad.parm("vtxdel").set("N")
    ad.parm("primdel").set("Cd")
    ad.parm("dtldel").set("")
    pr = geo.createNode("attribpromote", "couleur_points")
    pr.setInput(0, ad)
    pr.parm("inname").set("Cd")
    pr.parm("inclass").set("primitive")
    pr.parm("outclass").set("vertex")
    out = geo.createNode("null", "OUT")
    out.setInput(0, pr)
    return out


VEX_BOITE = r"""
// Aperçu : marquages limités à la boîte de la vue (pas de marques hors du sol maillé)
vector c = prim(0, "P", @primnum);
float x = c.x, y = -c.z;
if (x < ch("x0") || x > ch("x1") || y < ch("y0") || y > ch("y1")) removeprim(0, @primnum, 1);
"""


def marquages_vue(geo, marques, boite):
    om = geo.createNode("object_merge", "marquages")
    om.parm("objpath1").set(marques.path())
    w = geo.createNode("attribwrangle", "dans_la_boite")
    w.setInput(0, om)
    w.parm("class").set(1)
    w.parm("snippet").set(VEX_BOITE)
    tpl = w.parmTemplateGroup()
    for n, v in zip(("x0", "y0", "x1", "y1"), boite):
        tpl.append(hou.FloatParmTemplate(n, n, 1, default_value=(v,)))
    w.setParmTemplateGroup(tpl)
    out = geo.createNode("null", "OUT_MARQUES")
    out.setInput(0, w)
    return out


def reseau_sol(geo, boite):
    """SOP : HeightField du nivellement dans la boîte, maillé au pas de 0,10 m, coloré par classe de surface."""
    lire = geo.createNode("pj::lire_description::1.0", "lire_sol")
    lire.parm("dossier").set(DESCRIPTION.as_posix())
    for fam in ("bordures", "ilots", "ponctuels_sol", "marquages"):
        lire.parm(f"fam_{fam}").set(0)
    lire.parm("emprise").set("boite")
    lire.parmTuple("boite_min").set(boite[:2])
    lire.parmTuple("boite_max").set(boite[2:])
    lire.parm("altitude").set("plat")
    lire.parm("niv_marge").set(0.0)
    cv = geo.createNode("convertheightfield", "maillage_sol")
    cv.setInput(0, lire, 1)
    surf = geo.createNode("divide", "surfaces_convexes")
    surf.setInput(0, lire, 0)
    surf.parm("convex").set(1)
    w = geo.createNode("attribwrangle", "couleur_sol")
    w.setInput(0, cv)
    w.setInput(1, surf)
    w.parm("class").set(2)
    w.parm("snippet").set(VEX_SOL)
    nor = geo.createNode("normal", "normales_sol")
    nor.setInput(0, w)
    ad = geo.createNode("attribdelete", "attributs_sol")
    ad.setInput(0, nor)
    ad.parm("negate").set(1)
    ad.parm("ptdel").set("Cd N")
    ad.parm("vtxdel").set("N")
    ad.parm("primdel").set("")
    ad.parm("dtldel").set("")
    out = geo.createNode("null", "OUT_SOL")
    out.setInput(0, ad)
    return out


def scene(nom, vue, sop_marques, sop_sol, dossier_usd):
    """LOP : marquages + sol + matériau couleur de sommet + caméra + soleil + ciel + Karma XPU -> USD."""
    st = hou.node("/stage")
    net = st.createNode("subnet", f"apercu_marquages_{nom}")
    si = net.createNode("sopimport", "marquages")
    si.parm("soppath").set(sop_marques.path())
    si.parm("enable_savepath").set(0)
    si.parm("copycontents").set("on")
    si.parm("enable_pathprefix").set(1)
    si.parm("pathprefix").set("/apercu/marquages")
    prec = si
    if not vue.get("sans_sol"):
        ss = net.createNode("sopimport", "sol")
        ss.setInput(0, si)
        ss.parm("soppath").set(sop_sol.path())
        ss.parm("enable_savepath").set(0)
        ss.parm("copycontents").set("on")
        ss.parm("enable_pathprefix").set(1)
        ss.parm("pathprefix").set("/apercu/sol")
        prec = ss
    cam = net.createNode("camera", "camera")
    cam.setInput(0, prec)
    cam.parm("primpath").set("/apercu/camera")
    rx, ry = vue["res"]
    cam.parm("aspectratiox").set(rx)
    cam.parm("aspectratioy").set(ry)
    if "ortho" in vue:
        cx, cy, larg = vue["ortho"]
        cam.parm("projection").set("orthographic")
        for k, v in zip(("tx", "ty", "tz", "rx"), (cx, 200.0, -cy, -90.0)):
            cam.parm(k).set(v)
        cam.parm("horizontalAperture").set(larg * 1000.0)
        cam.parm("clippingRange1").set(1.0)
        cam.parm("clippingRange2").set(1000.0)
    else:
        e, c = vue["oeil"], vue["cible"]
        for k, v in zip(("tx", "ty", "tz"), (e[0], e[2], -e[1])):
            cam.parm(k).set(v)
        cam.parm("lookatenable").set(1)
        for k, v in zip(("lookatpositionx", "lookatpositiony", "lookatpositionz"), (c[0], c[2], -c[1])):
            cam.parm(k).set(v)
        cam.parm("focalLength").set(vue["focale"])
        cam.parm("horizontalAperture").set(36.0)
        cam.parm("clippingRange1").set(0.05)
        cam.parm("clippingRange2").set(2000.0)
    ml = net.createNode("materiallibrary", "materiau")
    ml.setInput(0, cam)
    sh = ml.createNode("mtlxstandard_surface", "couleur_sommets")
    lu = ml.createNode("mtlxgeompropvalue", "lire_couleur")
    lu.parm("signature").set("color3")
    lu.parm("geomprop").set("displayColor")
    sh.setInput(sh.inputIndex("base_color"), lu)
    sh.parm("specular").set(0.25)
    sh.parm("specular_roughness").set(0.45)
    ml.parm("materials").set(1)
    ml.parm("matnode1").set("couleur_sommets")
    ml.parm("matpath1").set("/apercu/materiaux/couleur_sommets")
    ml.parm("assign1").set(1)
    ml.parm("geopath1").set("/apercu/**")
    sol = net.createNode("distantlight::2.0", "soleil")
    sol.setInput(0, ml)
    sol.parm("primpath").set("/apercu/soleil")
    sol.parm("rx").set(-35)
    sol.parm("ry").set(-150)
    sol.parm("xn__inputsintensity_i0a").set(2.6)
    dome = net.createNode("domelight::3.0", "ciel")
    dome.setInput(0, sol)
    dome.parm("primpath").set("/apercu/ciel")
    dome.parm("xn__inputsintensity_i0a").set(0.0 if vue.get("sans_sol") else 0.55)
    kp = net.createNode("karmarenderproperties", "rendu")
    kp.setInput(0, dome)
    kp.parm("camera").set("/apercu/camera")
    kp.parm("engine").set("xpu")
    kp.parm("res_mode").set("manual")
    for n, v in (("resolutionx", rx), ("resolutiony", ry)):
        kp.parm(n).lock(False)
        kp.parm(n).deleteAllKeyframes()
        kp.parm(n).set(v)
    kp.parm("samplesperpixel").set(24)
    rop = net.createNode("usd_rop", "rop")
    rop.setInput(0, kp)
    usd = Path(dossier_usd) / f"apercu_marquages_{nom}.usdc"
    for p, v in (("lopoutput", usd.as_posix()), ("savetimeinfo", 0), ("flattensoplayers", 1),
                 ("clearhoudinicustomdata", 1)):
        rop.parm(p).set(v)
    rop.render()
    return usd


def husk(usd, png):
    exe = Path(sys.executable).parent / "husk.exe"
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    cmd = [str(exe), "-R", "BRAY_HdKarmaXPU", "--settings", "/Render/rendersettings", "--camera", "/apercu/camera",
           "--frame", "1", "--output", Path(png).as_posix(), "--make-output-path", usd.as_posix()]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not Path(png).exists():
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"rendu {png} en échec")


def ciel(png):
    """Fond transparent du rendu (alpha 0) remplacé par un ciel en dégradé (lisibilité des vues)."""
    from PIL import Image
    im = Image.open(png).convert("RGBA")
    w, h = im.size
    fond = Image.new("RGBA", (w, h))
    px = fond.load()
    for j in range(h):
        t = j / max(h - 1, 1)
        c = (int(150 + 60 * t), int(175 + 50 * t), int(205 + 30 * t), 255)
        for i in range(w):
            px[i, j] = c
    Image.alpha_composite(fond, im).convert("RGB").save(png)


def ortho(boite, px):
    """Mosaïque de l'ortho 2022 (5 cm, dalles de 50 m) sur la boîte locale, rééchantillonnée à px pixels de côté."""
    from PIL import Image
    x0, y0, x1, y1 = boite
    X0, Y0 = l93(x0, y0)
    X1, Y1 = l93(x1, y1)
    res = 0.05
    W, H = int(round((X1 - X0) / res)), int(round((Y1 - Y0) / res))
    im = Image.new("RGB", (W, H), (40, 40, 40))
    for tx in range(int(X0 // 50) * 50, int(X1 // 50 + 1) * 50, 50):
        for ty in range(int(Y0 // 50) * 50, int(Y1 // 50 + 1) * 50, 50):
            f = ORTHO / f"pcrs5cm_{tx}_{ty}.jpg"
            if not f.exists():
                continue
            t = Image.open(f)
            ox = int(round((tx - X0) / res))
            oy = int(round((Y1 - (ty + 50)) / res))
            im.paste(t, (ox, oy))
    return im.resize((px, int(round(px * H / W))), Image.LANCZOS)


def planche(boite, rendu, marques, png):
    """Ortho + levé GAM (magenta, comme l'image 12) | ortho + marquages fabriqués (rendu sans sol) | rendu avec sol."""
    from PIL import Image, ImageDraw, ImageFont
    px = 1000
    fond = ortho(boite, px)
    x0, y0, x1, y1 = boite
    s = px / (x1 - x0)

    def pix(x, y):
        return ((x - x0) * s, (y1 - y) * s)

    a = fond.copy()
    dr = ImageDraw.Draw(a)
    for f in json.load(open(GAM, encoding="utf-8"))["features"]:
        g = f["geometry"]
        lignes = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for l in lignes:
            q = [pix(c[0] - OX, c[1] - OY) for c in l]
            if len(q) >= 2:
                dr.line(q, fill=(255, 0, 255), width=2)
    m = Image.open(marques).convert("RGBA").resize((px, px), Image.LANCZOS)
    r, g, bb, al = m.split()
    masque = al.point(lambda v: 255 if v > 100 else 0)
    jaune = Image.merge("RGB", (r, g, bb)).convert("HSV").split()[1].point(lambda v: 255 if v > 90 else 0)
    b = fond.copy()
    b.paste(Image.new("RGB", (px, px), (0, 235, 255)), (0, 0), masque)          # peinture blanche : cyan
    b.paste(Image.new("RGB", (px, px), (255, 120, 0)), (0, 0),
            Image.composite(jaune, Image.new("L", (px, px), 0), masque))     # peinture jaune : orange
    c = Image.open(rendu).convert("RGB").resize((px, px), Image.LANCZOS)
    out = Image.new("RGB", (3 * px + 40, px + 60), (20, 20, 20))
    for k, (im, titre) in enumerate(((a, "ortho 2022 + levé GAM 2026 (magenta)"),
                                     (b, "ortho 2022 + marquages fabriqués (cyan : blanc, orange : jaune)"),
                                     (c, "rendu Karma XPU : marquages sur le nivellement"))):
        out.paste(im, (k * (px + 20), 50))
        ImageDraw.Draw(out).text((k * (px + 20) + 10, 15), titre, fill=(240, 240, 240),
                                 font=ImageFont.load_default(size=22))
    out.save(png)


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vues", default="")
    ap.add_argument("--travail", default=str(Path(os.environ.get("TEMP", "/tmp")) / "pj_marquages_apercu"))
    a = ap.parse_args()
    t0 = time.time()
    hou.hipFile.load(str(HIP), suppress_save_prompt=True, ignore_load_warnings=True)
    O.installer_tout()
    hou.hscript(f'set -g PJ_DESCRIPTION = "{DESCRIPTION.as_posix()}"')
    hou.hscript(f'set -g PJ_SORTIE = "{SORTIE.as_posix()}"')
    hou.hscript("varchange")
    travail = Path(a.travail)
    travail.mkdir(parents=True, exist_ok=True)
    geo = hou.node("/obj").createNode("geo", "apercu_marquages")
    marques = reseau_marquages(geo)
    toutes = vues(DESCRIPTION)
    choix = [v for v in a.vues.split(",") if v] or list(toutes)
    images = {}
    for nom in choix:
        v = toutes[nom]
        g = hou.node("/obj").createNode("geo", f"apercu_sol_{nom}")
        sol = reseau_sol(g, v["boite"])
        if "oeil" in v:                                  # hauteur de l'œil au-dessus du sol sous la caméra
            hf = g.node("lire_sol").geometry(1)
            vol = [p for p in hf.prims() if p.attribValue("name") == "height"][0]
            ex, ey, eh = v["oeil"]
            v["oeil"] = (ex, ey, vol.sample((ex, 0.0, -ey)) + eh)
            cx, cy, _ = v["cible"]
            v["cible"] = (cx, cy, vol.sample((cx, 0.0, -cy)))
        usd = scene(nom, v, marquages_vue(g, marques, v["boite"]), sol, travail)
        png = SORTIE / "controle" / f"marquages_{nom}.png"
        t = time.time()
        husk(usd, png)
        if not v.get("sans_sol"):
            ciel(png)
        images[nom] = png
        print(f"   vue {nom} : {time.time() - t:.0f} s -> {png}")
    if "centre_dessus" in images and "centre_dessus_marques" in images:
        p = SORTIE / "controle" / "marquages_planche_centre.png"
        planche(CENTRE, images["centre_dessus"], images["centre_dessus_marques"], p)
        print(f"   planche -> {p}")
    print(f"   durée {time.time() - t0:.0f} s")


if __name__ == "__main__":
    principal()
