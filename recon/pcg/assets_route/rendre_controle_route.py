"""Rendus Karma XPU de contrôle de la bibliothèque route_fr (hython Houdini 22 : pxr, husk, OpenImageIO).

    hython recon/pcg/assets_route/rendre_controle_route.py                       # toutes les planches
    hython recon/pcg/assets_route/rendre_controle_route.py --planches feux potelets
    hython recon/pcg/assets_route/rendre_controle_route.py --controle D:/DocRoute/14_Assets_Route_Statics/controle

Pour chaque planche : une scène USD (références vers les assets exportés, posés en grille ; sol en enrobé BBSG usé
route_fr ; soleil + ciel ; caméra perspective dont la distance est calculée pour que toutes les boîtes englobantes
entrent dans le cadre) rendue par husk (Karma XPU) en EXR, développée en PNG sRGB avec une exposition FIXE déduite
de l'éclairement (un gris d'albédo 0,18 au soleil sort à 0,18 : les teintes des matériaux sont comparables d'une
planche à l'autre), numérotée (numéro projeté au-dessus de chaque asset, légende sous l'image) puis découpée en
tuiles natives (recon/pcg/vision/decoupe.py image) pour l'examen visuel.

Les lentilles des feux sont rendues ALLUMÉES (émission = customData route:emission_allumee_lineaire du matériau),
pour contrôler l'ordre des couleurs. Fichiers temporaires : <controle>/../tmp/rendu (supprimés à la fin).
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
LIB = DEPOT / "assets" / "lib" / "route_fr"
CONTROLE_DEFAUT = Path("D:/DocRoute/14_Assets_Route_Statics/controle")
CATALOGUE = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
DECOUPE = DEPOT / "recon" / "pcg" / "vision" / "decoupe.py"

# éclairage (unités UsdLux) : soleil à 38° d'élévation, ciel uniforme ; rapport soleil / ciel ≈ 4 (ciel clair)
SOLEIL, SOLEIL_ELEV, CIEL = 5.0, 38.0, 0.25
ECLAIREMENT = SOLEIL * math.sin(math.radians(SOLEIL_ELEV)) + math.pi * CIEL     # sur un plan horizontal
EXPOSITION = math.pi / ECLAIREMENT * 1.15                 # albédo 0,18 -> ≈ 0,21 (légère surexposition lisible)


# ---------------------------------------------------------------------------------------------- planches
def ids_planches(cat):
    par = {}
    for a in cat["assets"]:
        par.setdefault(a["famille"], []).append(a["id"])
    b = par.get("bordures", [])
    droits = lambda prof: [f"bordure_{p}_L100" for p in prof if f"bordure_{p}_L100" in b]  # noqa: E731
    P = {
        "bordures_T_droits": dict(ids=droits(("T1", "T2", "T3", "T4", "T2_basse", "T2_surbaissee", "T3_basse", "T3_surbaissee",
                                              "ACCESBUS")), ncol=5, az=-38, el=24),
        "bordures_A_I_P_granit": dict(ids=droits(("A1", "A2", "I1", "I2", "I3", "I4", "P1", "P1_basse", "P2", "P3", "GR_T2",
                                                  "GR_T1", "GR_P1")) + [i for i in b if i.startswith("bordure_P4_")],
                                      ncol=5, az=-38, el=24),
        "bordures_angles_courbes": dict(ids=[i for i in b if any(k in i for k in ("angle", "quart_rond", "courbe"))],
                                        ncol=5, az=-30, el=38),
        "bordures_raccords_bateaux": dict(ids=[i for i in b if "raccord" in i] + ["bordure_T2_L100", "bordure_T2_surbaissee_L100",
                                                                                  "bordure_T2_basse_L100"], ncol=3, az=-38, el=26),
        "caniveaux": dict(ids=[i for i in par.get("caniveaux", []) if i.endswith("_L100")], ncol=3, az=-38, el=26),
        "dalles_paves_bev": dict(ids=par.get("dalles", []) + par.get("paves", []), ncol=5, az=-30, el=40),
        "potelets": dict(ids=par.get("potelets", []), ncol=5, az=-25, el=14),
        "supports": dict(ids=[i for i in par.get("supports", []) if "potence" not in i], ncol=7, az=-25, el=12),
        "feux": dict(ids=par.get("feux", []), ncol=8, az=160, el=10, soleil_az=150.0),
        "garde_corps_barrieres": dict(ids=par.get("garde_corps", []) + par.get("barrieres", []), ncol=4, az=-28, el=16),
        "potence_mat_feux": dict(ids=[i for i in par.get("supports", []) if "potence" in i or i.startswith("mat_feux")],
                                 ncol=2, az=-30, el=12),
        "zoom_T2_angles_courbes": dict(ids=[i for i in ("bordure_T2_angle_sortant", "bordure_T2_angle_rentrant",
                                                        "bordure_T2_courbe_ext_R120", "bordure_T2_courbe_int_R120",
                                                        "bordure_T2_quart_rond_ext_R020", "bordure_raccord_T2_T2_surbaissee_droite")
                                            if i in b], ncol=3, az=-35, el=35),
    }
    return {k: v for k, v in P.items() if v["ids"]}


def boite(fichier):
    st = Usd.Stage.Open(str(fichier))
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(st.GetDefaultPrim()).ComputeAlignedRange()
    return np.array(bb.GetMin()), np.array(bb.GetMax())


# ---------------------------------------------------------------------------------------------- caméra
def base_camera(az, el):
    """Direction cible -> œil : az = 0 face à -Y (devant une bordure), az > 0 vers +X ; el au-dessus de l'horizon."""
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    f = -d
    r = np.cross(f, [0.0, 0.0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return d, f, r, u


def cadrer(coins, az, el, tan_h, tan_v, marge=0.90):
    """Centre et distance tels que tous les coins entrent dans le cadre (projection perspective)."""
    d, f, r, u = base_camera(az, el)
    c = coins.mean(axis=0)
    dist = 1.0
    for _ in range(4):
        lo, hi = 0.05, 500.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            eye = c + d * mid
            rel = coins - eye
            z = rel @ f
            ok = np.all(z > 0.05) and np.all(np.abs(rel @ r) / z <= tan_h * marge) and np.all(np.abs(rel @ u) / z <= tan_v * marge)
            hi, lo = (mid, lo) if ok else (hi, mid)
        dist = hi
        eye = c + d * dist
        rel = coins - eye
        z = rel @ f
        x, y = (rel @ r) / z, (rel @ u) / z
        cx, cy = 0.5 * (x.min() + x.max()), 0.5 * (y.min() + y.max())
        zc = float(np.median(z))
        c = c + r * cx * zc + u * cy * zc                     # recentrer le cadre sur l'emprise projetée
    return c, c + d * dist, (f, r, u)


def projeter(p, eye, base, tan_h, tan_v, W, H):
    f, r, u = base
    rel = np.asarray(p) - eye
    z = rel @ f
    return (0.5 * W * (1 + (rel @ r) / z / tan_h), 0.5 * H * (1 - (rel @ u) / z / tan_v))


# ---------------------------------------------------------------------------------------------- scène
def scene(nom, spec, cat, dossier, res):
    par = {a["id"]: a for a in cat["assets"]}
    ids = spec["ids"]
    st = Usd.Stage.CreateNew(str(dossier / f"{nom}.usda"))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    monde = UsdGeom.Xform.Define(st, "/Monde")
    st.SetDefaultPrim(monde.GetPrim())
    boites = [boite(LIB / par[i]["fichiers"]["usd"]) for i in ids]
    tailles = np.array([mx - mn for mn, mx in boites])
    ncol = min(spec.get("ncol", 4), len(ids))
    gx = max(0.25, 0.35 * float(np.median(tailles[:, 0])))
    gy = max(0.45, 0.6 * float(np.max(tailles[:, 1])))
    # rangées « tassées » : chaque asset occupe sa propre largeur (+ gx) ; rangées centrées en X
    rangs = [list(range(k, min(k + ncol, len(ids)))) for k in range(0, len(ids), ncol)]
    largeurs = [sum(tailles[k, 0] for k in r) + gx * (len(r) - 1) for r in rangs]
    places, y = {}, 0.0
    for r, lr in zip(rangs, largeurs):
        x = -0.5 * lr
        prof = max(tailles[k, 1] for k in r)
        for k in r:
            places[k] = (x + 0.5 * tailles[k, 0], y - 0.5 * prof)
            x += tailles[k, 0] + gx
        y -= prof + gy                                    # rangée 0 au fond (+Y), les suivantes vers -Y
    coins, poses = [], []
    for k, i in enumerate(ids):
        mn, mx = boites[k]
        cx, cy = places[k]
        t = np.array([cx - 0.5 * (mn[0] + mx[0]), cy - 0.5 * (mn[1] + mx[1]), 0.0])
        p = UsdGeom.Xform.Define(st, f"/Monde/A_{k:02d}")
        p.GetPrim().GetReferences().AddReference(Path(os.path.relpath(LIB / par[i]["fichiers"]["usd"], dossier)).as_posix())
        p.AddTranslateOp().Set(Gf.Vec3d(*t.tolist()))
        a, b = mn + t, mx + t
        a[2] = max(a[2], 0.0)                             # parties enterrées (scellements) hors cadrage
        coins += [[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])]
        poses.append((i, np.array([0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]), b[2]])))
    coins = np.array(coins)
    # feux : lentilles allumées (surcharges sur la couche racine)
    for prim in st.Traverse():
        if prim.GetTypeName() == "Material":
            em = prim.GetCustomDataByKey("route:emission_allumee_lineaire")
            if em is not None:
                sh = UsdShade.Shader(prim.GetChild("Surface"))
                if sh:
                    sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*[2.5 * x for x in em]))
    # sol : enrobé BBSG usé (UV en mètres par st1)
    cx, cy = coins[:, 0].mean(), coins[:, 1].mean()
    ext = 400.0
    sol = UsdGeom.Mesh.Define(st, "/Monde/Sol")
    pts = [Gf.Vec3f(cx - ext, cy - ext, -0.0005), Gf.Vec3f(cx + ext, cy - ext, -0.0005), Gf.Vec3f(cx + ext, cy + ext, -0.0005),
           Gf.Vec3f(cx - ext, cy + ext, -0.0005)]
    sol.CreatePointsAttr(pts)
    sol.CreateFaceVertexCountsAttr([4])
    sol.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    sol.CreateNormalsAttr([Gf.Vec3f(0, 0, 1)] * 4)
    sol.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    for nomv in ("st", "st1"):
        pv = UsdGeom.PrimvarsAPI(sol).CreatePrimvar(nomv, Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
        pv.Set([Gf.Vec2f(p[0], p[1]) for p in pts])
    mat_sol = LIB / "materiaux" / "enrobe_bbsg_use" / "enrobe_bbsg_use.usda"
    m = UsdShade.Material.Define(st, "/Monde/Looks/sol")
    m.GetPrim().GetReferences().AddReference(Path(os.path.relpath(mat_sol, dossier)).as_posix())
    UsdShade.MaterialBindingAPI.Apply(sol.GetPrim())
    UsdShade.MaterialBindingAPI(sol).Bind(m)
    # lumières
    sun = UsdLux.DistantLight.Define(st, "/Monde/Soleil")
    sun.CreateIntensityAttr(SOLEIL)
    sun.CreateAngleAttr(0.53)
    sun.CreateNormalizeAttr(True)        # USD 26 / Karma : sans normalisation, l'intensité d'une DistantLight est une
    #                                      luminance (éclairement = intensité × angle solide du disque, ≈ 7e-5 sr à 0,53°)
    sun.CreateColorAttr(Gf.Vec3f(1.0, 0.97, 0.92))
    xf = UsdGeom.Xformable(sun)
    xf.AddRotateZOp().Set(spec.get("soleil_az", -40.0))
    xf.AddRotateXOp().Set(90.0 - SOLEIL_ELEV)
    dome = UsdLux.DomeLight.Define(st, "/Monde/Ciel")
    dome.CreateIntensityAttr(CIEL)
    dome.CreateColorAttr(Gf.Vec3f(0.85, 0.90, 1.0))
    # caméra
    W, H = res
    focale, ouv_h = 50.0, 36.0
    tan_h = ouv_h / (2 * focale)
    tan_v = tan_h * H / W
    c, eye, base = cadrer(coins, spec["az"], spec["el"], tan_h, tan_v)
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
    etiquettes = [(i, projeter(p, eye, base, tan_h, tan_v, W, H)) for i, p in poses]
    return dossier / f"{nom}.usda", etiquettes


def husk():
    h = Path(sys.executable).parent / "husk.exe"
    if h.exists():
        return str(h)
    return str(sorted(Path("C:/Program Files/Side Effects Software").glob("Houdini 22*/bin/husk.exe"))[-1])


def python_systeme():
    """Python du système (PIL, numpy) pour decoupe.py : PYTHON_SYSTEME, sinon le premier python du PATH hors Houdini."""
    if os.environ.get("PYTHON_SYSTEME"):
        return os.environ["PYTHON_SYSTEME"]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        f = Path(d) / "python.exe"
        if f.exists() and not any(k in str(f).lower() for k in ("side effects", "sideef", "houdin", "windowsapps")):
            return str(f)
    return "python"


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def developper(exr, png, etiquettes, titre):
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * EXPOSITION
    ep = 0.75                                               # épaule douce au-dessus de 0,75
    y = np.where(a <= ep, a, ep + (1 - ep) * (1 - np.exp(-(a - ep) / (1 - ep))))
    img = (srgb(y) * 255 + 0.5).astype(np.uint8)
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray(img)
    try:
        f = ImageFont.truetype("arial.ttf", 16)
        fb = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:  # noqa: BLE001
        f = fb = ImageFont.load_default()
    d0 = ImageDraw.Draw(im)
    for k, (i, (x, y_)) in enumerate(etiquettes):
        t = f"{k + 1:02d}"
        x, y_ = int(x), int(y_) - 26
        d0.rectangle([x - 14, y_ - 11, x + 14, y_ + 11], fill=(255, 255, 255), outline=(0, 0, 0))
        d0.text((x - 11, y_ - 10), t, fill=(0, 0, 0), font=fb)
    ncols = 3
    lignes = (len(etiquettes) + ncols - 1) // ncols
    out = Image.new("RGB", (im.width, im.height + 26 + 22 * lignes + 8), "white")
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.text((8, im.height + 4), titre, fill="black", font=fb)
    for k, (i, _) in enumerate(etiquettes):
        col, lig = k % ncols, k // ncols
        d.text((8 + col * (im.width // ncols), im.height + 28 + 22 * lig), f"{k + 1:02d} {i}", fill="black", font=f)
    out.save(png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planches", nargs="*")
    ap.add_argument("--res", type=int, nargs=2, default=(2184, 940))
    ap.add_argument("--limite", type=int, default=90, help="temps de rendu maximal par planche (s)")
    ap.add_argument("--controle", default=str(CONTROLE_DEFAUT))
    ap.add_argument("--sans-tuiles", action="store_true")
    a = ap.parse_args()
    controle = Path(a.controle)
    cat = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    P = ids_planches(cat)
    controle.mkdir(parents=True, exist_ok=True)
    tmp = controle.parent / "tmp" / "rendu"
    tmp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    fbilan = controle / "rendus_controle.json"
    bilan = json.loads(fbilan.read_text(encoding="utf-8")) if fbilan.exists() else {}
    bilan = {k: v for k, v in bilan.items() if k in P}
    try:
        for nom, spec in P.items():
            if a.planches and nom not in a.planches:
                continue
            usd, etiq = scene(nom, spec, cat, tmp, a.res)
            exr = tmp / f"{nom}.exr"
            cmd = [husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/rendersettings",
                   "--camera", "/Monde/Camera", "--res", str(a.res[0]), str(a.res[1]), "--frame", "1",
                   "--output", exr.as_posix(), "--make-output-path", "--timelimit", str(a.limite), "--verbose", "1", usd.as_posix()]
            r = subprocess.run(cmd, env=env, cwd=str(tmp), capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0 or not exr.exists():
                print(nom, "ÉCHEC", r.stdout[-1500:], r.stderr[-1500:])
                continue
            png = controle / f"rendu_{nom}.png"
            developper(exr, png, etiq, f"route_fr — planche « {nom} » (Karma XPU, exposition fixe {EXPOSITION:.3f})")
            tuiles = controle / "tuiles" / f"rendu_{nom}"
            if not a.sans_tuiles:
                shutil.rmtree(tuiles, ignore_errors=True)
                env_py = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "HOUDINI", "HFS", "H_"))}
                subprocess.run([python_systeme(), str(DECOUPE), "image", str(png), str(tuiles)], check=False, env=env_py)
            bilan[nom] = dict(png=png.relative_to(controle.parent).as_posix(),
                              tuiles=tuiles.relative_to(controle.parent).as_posix(), assets=spec["ids"],
                              camera=dict(azimut_deg=spec["az"], elevation_deg=spec["el"], focale_mm=50),
                              exposition=round(EXPOSITION, 4), limite_s=a.limite)
            print(nom, "->", png, flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for rat in LIB.rglob("*.rat"):
            rat.unlink()
    fbilan.write_text(json.dumps(bilan, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
