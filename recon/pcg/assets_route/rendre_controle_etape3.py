"""Rendus Karma XPU de contrôle de l'étape 3 de la bibliothèque route_fr : une ou plusieurs planches par famille, chacune
≤ 1092 px de côté (entrée image native, pas de découpe nécessaire), numérotées, légende sous l'image.

    hython recon/pcg/assets_route/rendre_controle_etape3.py                         # toutes les planches
    hython recon/pcg/assets_route/rendre_controle_etape3.py --planches feux retenue_beton
    hython recon/pcg/assets_route/rendre_controle_etape3.py --liste

Reprend la mise en scène de rendre_controle_route.py (soleil normalisé 38°, ciel, exposition FIXE, cadrage calculé,
lentilles et luminaires allumés) ; sortie : D:/DocRoute/14_Assets_Route_Statics/controle/etape3/ (PNG + bilan JSON).
Fichiers temporaires dans assets/lib/route_fr/_tmp_rendu_e3 (sur D:, supprimés) ; seules les .rat créées pendant le rendu sous
assets/lib/route_fr sont supprimées (celles des autres équipes ne sont pas touchées).
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

import rendre_controle_route as R

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
LIB = DEPOT / "assets" / "lib" / "route_fr"
CATALOGUE = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
SORTIE = Path("D:/DocRoute/14_Assets_Route_Statics/controle/etape3")
RES = (1092, 720)


def decouper(ids, n):
    return [ids[k:k + n] for k in range(0, len(ids), n)]


def planches(cat):
    e3 = [a for a in cat["assets"] if a.get("etape") == 3]
    par = {}
    for a in e3:
        par.setdefault(a["famille"], []).append(a["id"])
    P = {}

    def ajoute(nom, ids, **kw):
        ids = [i for i in ids if i]
        if ids:
            P[nom] = dict(ids=ids, **kw)
    ret = par.get("retenue", [])
    ajoute("retenue_beton", [i for i in ret if i.endswith("L100") or "L0165" in i], ncol=6, az=-35, el=22)
    ajoute("retenue_zoom_GS2_GBA", ["retenue_glissiere_GS2_module_L400", "retenue_GBA_L100", "retenue_DBA_L100"], ncol=3, az=-20, el=12)
    ajoute("retenue_glissieres_modules", [i for i in ret if "module" in i], ncol=3, az=-35, el=18)
    ajoute("retenue_glissieres_extremites", [i for i in ret if "glissiere" in i and "extremite" in i], ncol=1, az=-30, el=16)
    ajoute("retenue_beton_extremites_20m", [i for i in ret if "L2000" in i], ncol=1, az=-30, el=16)
    ajoute("retenue_attenuateurs", [i for i in ret if "attenuateur" in i], ncol=4, az=-55, el=20)
    for k, ch in enumerate(decouper(par.get("balises", []), 6)):
        ajoute(f"balises_{k + 1}", ch, ncol=6, az=-25, el=10)
    ajoute("assainissement", par.get("assainissement", []), ncol=3, az=-30, el=45)
    ecl = par.get("eclairage", [])
    ajoute("eclairage_routier", [i for i in ecl if "routier" in i], ncol=4, az=-20, el=6)
    ajoute("eclairage_urbain", [i for i in ecl if "urbain" in i], ncol=4, az=-20, el=6)
    mob = par.get("mobilier", [])
    ajoute("mobilier_bancs_corbeilles_arceaux", [i for i in mob if not i.startswith("abri")], ncol=4, az=-30, el=16)
    ajoute("mobilier_abris", [i for i in mob if i.startswith("abri")], ncol=2, az=-20, el=14)
    ajoute("potelets_barrieres", par.get("potelets", []) + par.get("barrieres", []), ncol=7, az=-25, el=10)
    ajoute("feux", par.get("feux", []), ncol=8, az=160, el=8, soleil_az=150.0)
    sup = par.get("supports", [])
    ajoute("supports_mats", [i for i in sup if not i.startswith(("potence", "portique", "collier"))], ncol=6, az=150, el=12, soleil_az=150.0)
    ajoute("supports_colliers", [i for i in sup if i.startswith("collier")], ncol=5, az=150, el=20, soleil_az=150.0)
    ajoute("potences_feux", [i for i in sup if i.startswith("potence_feux")], ncol=1, az=-15, el=10)
    ajoute("potence_portique_signalisation", [i for i in sup if i.startswith(("potence_signalisation", "portique"))], ncol=1, az=150, el=10, soleil_az=150.0)
    bord = par.get("bordures", []) + par.get("caniveaux", [])
    for pid in ("T1", "T3", "A2", "I2", "CS2", "CC1", "GR_T2"):
        ajoute(f"bordures_courbes_{pid}", [i for i in bord if i.startswith(f"bordure_{pid}_courbe")], ncol=3, az=-30, el=40)
    ajoute("bordures_granit_rampants", [i for i in bord if "courbe" not in i], ncol=4, az=-35, el=24)
    ilots = par.get("ilots", [])
    ajoute("giratoires", [i for i in ilots if i.startswith("giratoire")], ncol=5, az=-30, el=30)
    ajoute("ilots", [i for i in ilots if i.startswith("ilot")], ncol=4, az=-30, el=30)
    ajoute("dalles_paves_galets", par.get("dalles", []) + par.get("paves", []), ncol=6, az=-30, el=40)
    # panneaux : un échantillon par famille de signaux (12 maximum) + gammes + ensembles
    pan = [a for a in e3 if a["famille"] == "panneaux"]
    par_sig = {}
    for a in pan:
        par_sig.setdefault(a["famille_signal"], []).append(a["id"])
    for fam, ids in sorted(par_sig.items()):
        pas = max(1, len(ids) // 12)
        ajoute(f"panneaux_{fam}", ids[::pas][:12], ncol=6, az=180, el=16, soleil_az=165.0, soulever=True)
    ens = par.get("panneaux_montes", [])
    for k, ch in enumerate(decouper(ens, 8)):
        ajoute(f"panneaux_montes_{k + 1}", ch, ncol=8, az=165, el=8, soleil_az=150.0)
    ajoute("feux_montes", par.get("feux_montes", []), ncol=3, az=150, el=8, soleil_az=150.0)
    man = json.loads((ICI / "manifeste_materiaux_etape3.json").read_text(encoding="utf-8"))
    noms = [m["nom"] for m in man["materiaux"] if (LIB / "materiaux" / m["nom"] / f"{m['nom']}.usda").exists()]
    for k, ch in enumerate(decouper(noms, 8)):
        ajoute(f"materiaux_{k + 1}", ch, materiaux=True, az=-15, el=48)
    return P


def scene_materiaux(nom, noms, tmp, res, cote=2.0, ncol=4):
    """Planche de matériaux : dalles carrées de `cote` m posées au sol (UV st et st1 en mètres), vue oblique."""
    st = Usd.Stage.CreateNew(str(tmp / f"{nom}.usda"))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    monde = UsdGeom.Xform.Define(st, "/Monde")
    st.SetDefaultPrim(monde.GetPrim())
    coins, poses = [], []
    g = 0.25
    for k, m in enumerate(noms):
        c, r = k % ncol, k // ncol
        x0, y0 = c * (cote + g), -r * (cote + g)
        pts = [Gf.Vec3f(x0, y0, 0), Gf.Vec3f(x0 + cote, y0, 0), Gf.Vec3f(x0 + cote, y0 + cote, 0), Gf.Vec3f(x0, y0 + cote, 0)]
        me = UsdGeom.Mesh.Define(st, f"/Monde/M_{k:02d}")
        me.CreatePointsAttr(pts)
        me.CreateFaceVertexCountsAttr([4])
        me.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        me.CreateNormalsAttr([Gf.Vec3f(0, 0, 1)] * 4)
        me.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        for nv in ("st", "st1"):
            UsdGeom.PrimvarsAPI(me).CreatePrimvar(nv, Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
                [Gf.Vec2f(p[0], p[1]) for p in pts])
        mat = UsdShade.Material.Define(st, f"/Monde/Looks/m_{k:02d}")
        mat.GetPrim().GetReferences().AddReference(Path(os.path.relpath(LIB / "materiaux" / m / f"{m}.usda", tmp)).as_posix())
        UsdShade.MaterialBindingAPI.Apply(me.GetPrim())
        UsdShade.MaterialBindingAPI(me).Bind(mat)
        coins += [[x0, y0, 0], [x0 + cote, y0 + cote, 0], [x0, y0 + cote, 0.01], [x0 + cote, y0, 0.01]]
        poses.append((m, np.array([x0 + cote / 2, y0 + cote, 0.0])))
    spec = dict(az=-15, el=48, soleil_az=-40.0)
    from pxr import UsdLux, UsdRender
    sun = UsdLux.DistantLight.Define(st, "/Monde/Soleil")
    sun.CreateIntensityAttr(R.SOLEIL)
    sun.CreateAngleAttr(0.53)
    sun.CreateNormalizeAttr(True)
    sun.CreateColorAttr(Gf.Vec3f(1.0, 0.97, 0.92))
    xf = UsdGeom.Xformable(sun)
    xf.AddRotateZOp().Set(spec["soleil_az"])
    xf.AddRotateXOp().Set(90.0 - R.SOLEIL_ELEV)
    dome = UsdLux.DomeLight.Define(st, "/Monde/Ciel")
    dome.CreateIntensityAttr(R.CIEL)
    dome.CreateColorAttr(Gf.Vec3f(0.85, 0.90, 1.0))
    W, H = res
    focale, ouv_h = 50.0, 36.0
    tan_h = ouv_h / (2 * focale)
    tan_v = tan_h * H / W
    c, eye, base = R.cadrer(np.array(coins, float), spec["az"], spec["el"], tan_h, tan_v)
    cam = UsdGeom.Camera.Define(st, "/Monde/Camera")
    cam.CreateFocalLengthAttr(focale)
    cam.CreateHorizontalApertureAttr(ouv_h)
    cam.CreateVerticalApertureAttr(ouv_h * H / W)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.02, 2000.0))
    m4 = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye.tolist()), Gf.Vec3d(*c.tolist()), Gf.Vec3d(0, 0, 1)).GetInverse()
    UsdGeom.Xformable(cam).AddTransformOp().Set(m4)
    rs = UsdRender.Settings.Define(st, "/Render/rendersettings")
    rs.CreateResolutionAttr(Gf.Vec2i(W, H))
    rs.CreateCameraRel().SetTargets([cam.GetPath()])
    st.GetRootLayer().Save()
    etiq = [(m, R.projeter(p, eye, base, tan_h, tan_v, W, H)) for m, p in poses]
    return tmp / f"{nom}.usda", etiq


def developper(exr, png, etiquettes, titre):
    """Comme rendre_controle_route.developper, avec une légende sur 2 colonnes si les identifiants sont longs."""
    import OpenImageIO as oiio
    from PIL import ImageDraw, ImageFont
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * R.EXPOSITION
    ep = 0.75
    y = np.where(a <= ep, a, ep + (1 - ep) * (1 - np.exp(-(a - ep) / (1 - ep))))
    im = Image.fromarray((R.srgb(y) * 255 + 0.5).astype(np.uint8))
    try:
        f = ImageFont.truetype("arial.ttf", 15)
        fb = ImageFont.truetype("arialbd.ttf", 17)
    except Exception:  # noqa: BLE001
        f = fb = ImageFont.load_default()
    d0 = ImageDraw.Draw(im)
    for k, (i, (x, y_)) in enumerate(etiquettes):
        x, y_ = int(x), int(y_) - 26
        d0.rectangle([x - 14, y_ - 11, x + 14, y_ + 11], fill=(255, 255, 255), outline=(0, 0, 0))
        d0.text((x - 11, y_ - 10), f"{k + 1:02d}", fill="black", font=fb)
    ncols = 2 if max(len(i) for i, _ in etiquettes) > 34 else 3
    lignes = (len(etiquettes) + ncols - 1) // ncols
    out = Image.new("RGB", (im.width, im.height + 26 + 20 * lignes + 8), "white")
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.text((8, im.height + 4), titre, fill="black", font=fb)
    for k, (i, _) in enumerate(etiquettes):
        col, lig = k % ncols, k // ncols
        d.text((8 + col * (im.width // ncols), im.height + 28 + 20 * lig), f"{k + 1:02d} {i}", fill="black", font=f)
    out.save(png)


def rendre(nom, spec, cat, tmp, limite):
    if spec.get("soulever"):                      # panneaux : panonceaux sous le pivot -> posés sur le sol pour la planche
        boite0 = R.boite

        def boite_soulevee(fichier):
            mn, mx = boite0(fichier)
            if mn[2] < 0:
                d = -mn[2]
                mn, mx = mn.copy(), mx.copy()
                mn[2] += d
                mx[2] += d
            return mn, mx
        R.boite = boite_soulevee
    if spec.get("materiaux"):
        usd, etiq = scene_materiaux(nom, spec["ids"], tmp, RES)
    else:
        usd, etiq = R.scene(nom, spec, cat, tmp, RES)
    if spec.get("soulever"):
        R.boite = boite0
        st = Usd.Stage.Open(str(usd))
        for prim in st.GetPrimAtPath("/Monde").GetChildren():
            if prim.GetName().startswith("A_"):
                bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(prim).ComputeAlignedRange()
                if bb.GetMin()[2] < 0:
                    op = UsdGeom.Xformable(prim).GetOrderedXformOps()[0]
                    v = op.Get()
                    op.Set(Gf.Vec3d(v[0], v[1], v[2] - bb.GetMin()[2]))
        st.GetRootLayer().Save()
    exr = tmp / f"{nom}.exr"
    cmd = [R.husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/rendersettings", "--camera", "/Monde/Camera",
           "--res", str(RES[0]), str(RES[1]), "--frame", "1", "--output", exr.as_posix(), "--make-output-path",
           "--timelimit", str(limite), "--verbose", "1", usd.as_posix()]
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    r = subprocess.run(cmd, env=env, cwd=str(tmp), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not exr.exists():
        print(nom, "ÉCHEC", r.stdout[-800:], r.stderr[-800:], flush=True)
        return None
    png = SORTIE / f"e3_{nom}.png"
    developper(exr, png, etiq, f"route_fr étape 3 — « {nom} » (Karma XPU, exposition fixe {R.EXPOSITION:.3f})")
    im = Image.open(png)
    if max(im.size) > 1092:
        im.thumbnail((1092, 1092))
        im.save(png)
    return png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planches", nargs="*")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--limite", type=int, default=60)
    a = ap.parse_args()
    cat = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    P = planches(cat)
    if a.liste:
        for k, v in P.items():
            print(f"{k:42s} {len(v['ids'])}")
        return
    SORTIE.mkdir(parents=True, exist_ok=True)
    rat_avant = set(LIB.rglob("*.rat"))
    (LIB / "_tmp_rendu_e3").mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="rendu_", dir=str(LIB / "_tmp_rendu_e3")))
    fbilan = SORTIE / "rendus_controle_etape3.json"
    bilan = json.loads(fbilan.read_text(encoding="utf-8")) if fbilan.exists() else {}
    try:
        for nom, spec in P.items():
            if a.planches and nom not in a.planches:
                continue
            t0 = time.time()
            png = rendre(nom, spec, cat, tmp, a.limite)
            if png:
                taille = Image.open(png).size
                bilan[nom] = dict(png=png.name, taille_px=list(taille), assets=spec["ids"],
                                  camera=dict(azimut_deg=spec["az"], elevation_deg=spec["el"], focale_mm=50),
                                  exposition=round(R.EXPOSITION, 4), duree_s=round(time.time() - t0, 1))
                print(nom, "->", png, taille, f"{time.time() - t0:.0f} s", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for rat in set(LIB.rglob("*.rat")) - rat_avant:
            try:
                rat.unlink()
            except OSError:
                pass
    fbilan.write_text(json.dumps(bilan, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
