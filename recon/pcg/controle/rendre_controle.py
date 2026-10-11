"""Rendus Karma XPU de contrôle visuel de la fabrication v2 seule (aucun sol ni marquage v1) : sol, bordures,
caniveaux, îlots, marquages (lignes, passages, symboles drapés et symboles instanciés), ciel et soleil.

    hython recon/pcg/controle/rendre_controle.py [--vues a,b] [--res 1400] [--spp 64] [--sortie DIR]

Caméras (toutes recopiées dans recon/out/paquet_jardin/v2/controle/rendu/cameras_controle.usda) :
- les 4 vues de contrôle de recon/pc/houdini/cameras.usda ; les vues basses (œil à moins de 3 m du sol v1) sont
  translatées verticalement pour garder la même hauteur d'œil au-dessus du sol v2 fabriqué ;
- les 6 vues pilote de recon/pc/houdini/cameras_v2_pilote.usda (inchangées) ;
- 5 vues nouvelles aux endroits signalés par l'utilisateur : centre vu de dessus à 40 m (comme le levé GAM de
  l'image 12), traversée et îlot de Verdun SO à 1,60 m, trottoir NE (falaises du v1), gros plan de flèche à 1,30 m,
  trottoir de Verdun SO de la capture 7.
Éclairage : soleil (azimut 220°, hauteur 29°, 10 octobre, recon/pcg/houdini/pj_rendu.py), ciel clair procédural
(copie de fabrique/ciel/ciel_clair.hdr) ; développement EXR -> PNG : exposition, épaule douce, sRGB
(même chaîne que recon/pcg/houdini/rendre_pilote.py). Sorties : recon/pc/rendus/v2_site/<vue>.png.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, Vt

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
FAB = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda"
DESC = RACINE / "recon/out/paquet_jardin/v2/description/base"
REND = RACINE / "recon/out/paquet_jardin/v2/controle/rendu"
CACHE = RACINE / "recon/out/paquet_jardin/v2/controle/cache"
SORTIE = RACINE / "recon/pc/rendus/v2_site"
CIEL_SRC = RACINE / "recon/out/paquet_jardin/v2/fabrique/ciel/ciel_clair.hdr"
COUCHES = ("sol.usdc", "bordures.usdc", "caniveaux.usda", "ilots.usda", "marquages_lignes.usda", "passages.usda",
           "symboles.usda", "zones.usda", "materiaux_ue.usda")
O = (917279.43, 6460289.98)
SOLEIL = {"azimut_deg": 220.0, "hauteur_deg": 29.0, "exposition": 2.0, "couleur": (1.0, 0.95, 0.88)}
EV = 0.2
EPAULE = 0.6


# ----------------------------------------------------------------------------------------------- sol v2
class Sol:
    """Hauteur du sol fabriqué (cache sol_grille.npz du vérificateur, grille de 0,10 m), interpolation bilinéaire."""

    def __init__(self):
        d = np.load(CACHE / "sol_grille.npz")
        self.z = d["z"].astype(np.float64)

    def __call__(self, x, y):
        fi, fj = (x + 150.0) / 0.1, (y + 150.0) / 0.1
        i, j = int(math.floor(fi)), int(math.floor(fj))
        t, u = fi - i, fj - j
        v = self.z[j:j + 2, i:i + 2]
        if v.shape != (2, 2) or not np.isfinite(v).all():
            vv = self.z[max(0, j - 3):j + 4, max(0, i - 3):i + 4]
            return float(np.nanmedian(vv)) if np.isfinite(vv).any() else 0.0
        return float((v[0, 0] * (1 - t) + v[0, 1] * t) * (1 - u) + (v[1, 0] * (1 - t) + v[1, 1] * t) * u)


def regard(oeil, cible, haut=(0, 0, 1)):
    m = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*map(float, oeil)), Gf.Vec3d(*map(float, cible)), Gf.Vec3d(*haut))
    return m.GetInverse()


def focale(hfov, ouverture=36.0):
    return (ouverture / 2.0) / math.tan(math.radians(hfov) / 2.0)


def geo_desc(nom):
    return json.loads((DESC / f"{nom}.geojson").read_text(encoding="utf-8"))["features"]


def centroide(coords):
    a = np.asarray(coords, float)[:, :2] - np.array(O)
    return a.mean(0)


def vues_nouvelles(sol):
    """(nom, oeil, cible, hfov, aspect, doc) des 5 vues nouvelles, placées depuis la description."""
    out = []
    # n1 : centre du carrefour vu de dessus à 40 m (nord en haut), comme l'image 12 (levé GAM sur l'ortho)
    c = (-1.569, -5.089)
    zc = sol(*c)
    out.append(("n1_centre_dessus_40m", (c[0], c[1], zc + 40.0), (c[0], c[1], zc), 68.0, 1.0,
                "centre du carrefour vu de dessus à 40 m, nord en haut (comparable au levé GAM 2026, image 12)",
                (0, 1, 0)))
    # n2 : traversées de Verdun SO (MP-5246 et zébra de la chaussée sens SW) et refuge du TPC entre elles, à hauteur
    # d'œil 1,60 m, depuis la chaussée sens NE (côté SE du TPC), 10 m en amont
    c = np.array([-16.0, -20.0])
    u = np.array([math.cos(math.radians(45.0)), math.sin(math.radians(45.0))])
    n = np.array([-u[1], u[0]])
    oe = c - 10.0 * u - 3.0 * n
    ci2 = c + 1.0 * u
    out.append(("n2_verdun_so_traversee_ilot_1m60", (oe[0], oe[1], sol(*oe) + 1.60), (ci2[0], ci2[1], sol(*ci2)),
                70.0, 1.6, "traversées de Verdun SO et refuge du TPC entre elles (îlots I-0333 / I-0339), œil à 1,60 m "
                "sur la chaussée sens NE, 10 m en amont", (0, 0, 1)))
    # n3 : trottoir NE (grande face piétonne S-0213a où le v1 montrait des falaises), vue oblique à 4 m
    q = np.array([79.0, 44.3])
    oe = q + np.array([-11.0, -9.0])
    out.append(("n3_trottoir_ne_falaises", (oe[0], oe[1], sol(*oe) + 4.0), (q[0], q[1], sol(*q)), 70.0, 1.6,
                "trottoir NE (S-0213a, marches et pentes signalées par GA-RES-001 / GA-TRO-004), vue oblique à 4 m",
                (0, 0, 1)))
    # n4 : gros plan de la flèche MF-6014 (TD_TAD, Verdun SO) à 1,30 m, derrière sa queue dans l'axe de la voie
    fl = next(f for f in geo_desc("marquages") if f["properties"]["id"] == "MF-6014")
    cap = math.radians(fl["properties"]["pose"]["cap_deg"])
    u = np.array([math.cos(cap), math.sin(cap)])
    cf = centroide(fl["geometry"]["coordinates"][0])
    oe = cf - 5.5 * u
    cib = cf + 0.8 * u
    out.append(("n4_fleche_gros_plan_1m30", (oe[0], oe[1], sol(*oe) + 1.30), (cib[0], cib[1], sol(*cib)), 60.0, 1.6,
                "gros plan de la flèche MF-6014 (TD_TAD, Verdun SO) depuis 1,30 m, 5,5 m en arrière dans l'axe",
                (0, 0, 1)))
    # n5 : trottoir de Verdun SO de la capture 7 (falaises du v1 ; recon/pcg/houdini/hda/pj_bordure/controle_f1.py)
    oe, cib = np.array([-14.5, -40.0]), np.array([-25.0, -28.5])
    out.append(("n5_trottoir_so_capture7", (oe[0], oe[1], sol(*oe) + 2.2), (cib[0], cib[1], sol(*cib)), 62.0, 1.6,
                "trottoir et îlot de Verdun SO de la capture 7 (falaises du v1), œil à 2,20 m", (0, 0, 1)))
    return out


def ecrire_cameras(sol):
    """cameras_controle.usda : /World/Cameras_controle/<vue> ; renvoie {vue: (aspect, doc)}."""
    f = REND / "cameras_controle.usda"
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.Scope.Define(st, "/World/Cameras_controle")
    infos = {}
    for src, prefixe in ((RACINE / "recon/pc/houdini/cameras.usda", "c"), (RACINE / "recon/pc/houdini/cameras_v2_pilote.usda", "p")):
        s0 = Usd.Stage.Open(str(src))
        for p in s0.TraverseAll():
            if p.GetTypeName() != "Camera":
                continue
            cam0 = UsdGeom.Camera(p)
            m = UsdGeom.Xformable(p).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            t = m.ExtractTranslation()
            cd = p.GetCustomData()
            dz = 0.0
            if "z_sol_local_m" in cd and t[2] - cd["z_sol_local_m"] < 3.0:
                dz = sol(t[0], t[1]) - float(cd["z_sol_local_m"])       # même hauteur d'œil au-dessus du sol v2
            m2 = Gf.Matrix4d(m)
            m2.SetTranslateOnly(Gf.Vec3d(t[0], t[1], t[2] + dz))
            nom = f"{prefixe}_{p.GetName()}"
            cam = UsdGeom.Camera.Define(st, f"/World/Cameras_controle/{nom}")
            cam.CreateFocalLengthAttr(cam0.GetFocalLengthAttr().Get())
            ha, va = cam0.GetHorizontalApertureAttr().Get(), cam0.GetVerticalApertureAttr().Get()
            cam.CreateHorizontalApertureAttr(ha)
            cam.CreateVerticalApertureAttr(va)
            cam.CreateClippingRangeAttr(Gf.Vec2f(0.02, 3000.0))
            cam.CreateFStopAttr(0.0)
            cam.AddTransformOp().Set(m2)
            doc = p.GetMetadata("documentation") or ""
            cam.GetPrim().SetMetadata("documentation", doc + (f" [œil translaté de {dz:+.3f} m : même hauteur au-dessus "
                                                              "du sol v2 fabriqué]" if dz else ""))
            infos[nom] = (ha / va, doc, dz)
    for nom, oeil, cible, hfov, aspect, doc, haut in vues_nouvelles(sol):
        cam = UsdGeom.Camera.Define(st, f"/World/Cameras_controle/{nom}")
        cam.CreateFocalLengthAttr(focale(hfov))
        cam.CreateHorizontalApertureAttr(36.0)
        cam.CreateVerticalApertureAttr(36.0 / aspect)
        cam.CreateClippingRangeAttr(Gf.Vec2f(0.02, 3000.0))
        cam.CreateFStopAttr(0.0)
        cam.AddTransformOp().Set(regard(oeil, cible, haut))
        cam.GetPrim().SetMetadata("documentation", doc)
        infos[nom] = (aspect, doc, 0.0)
    if f.exists():
        f.unlink()
    st.GetRootLayer().Export(str(f))
    return infos


def ecrire_scene(infos):
    """scene_controle.usda : couches v2 fabriquées + symboles instanciés + caméras + ciel et soleil."""
    f = REND / "scene_controle.usda"
    REND.mkdir(parents=True, exist_ok=True)
    ciel = REND / "ciel_clair.hdr"
    if not ciel.exists() or ciel.stat().st_size != CIEL_SRC.stat().st_size:
        shutil.copy2(CIEL_SRC, ciel)
    st = Usd.Stage.CreateInMemory()
    lay = st.GetRootLayer()
    lay.subLayerPaths = ["./cameras_controle.usda"] + [f"../../fabrique_hda/{c}" for c in COUCHES]
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    lay.documentation = ("Scène de contrôle visuel de la fabrication v2 seule (recon/pcg/controle/rendre_controle.py) : "
                         "aucune géométrie v1.")
    # instances (points pj_points/0.1 sur les prototypes de bibliothèque) : symboles, et éclats épars des îlots (contrôle
    # de l'échelle TQ-PCG-001 : s = taille, éclats de 1,5 à 6 cm, revue conformité du 11/10/2026)
    for fam, couche_proto in (("symboles", "PJ_Marquages"), ("ilots", "PJ_Lib_Ilots")):
        fp = FAB / f"points/{fam}.json"
        if not fp.exists() or not (FAB / f"prototypes/{fam}.usda").exists():
            continue
        doc = json.loads(fp.read_text(encoding="utf-8"))
        assets = sorted({p["asset"] for p in doc["points"]})
        pi = UsdGeom.PointInstancer.Define(st, f"/Controle/{fam}")
        UsdGeom.Scope.Define(st, f"/Controle/{fam}/Prototypes")
        cibles = []
        for a in assets:
            pr = st.DefinePrim(f"/Controle/{fam}/Prototypes/{a}", "Xform")
            pr.GetReferences().AddReference(f"../../fabrique_hda/prototypes/{fam}.usda", f"/World/{couche_proto}/{a}")
            cibles.append(pr.GetPath())
        pi.CreatePrototypesRel().SetTargets(cibles)
        idx = {a: i for i, a in enumerate(assets)}
        pi.CreateProtoIndicesAttr(Vt.IntArray([idx[p["asset"]] for p in doc["points"]]))
        pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(*p["p"]) for p in doc["points"]]))
        pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(p["q"][3], p["q"][0], p["q"][1], p["q"][2]) for p in doc["points"]]))
        pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(*p["s"]) for p in doc["points"]]))
    # soleil et ciel (recon/pcg/houdini/pj_rendu.py) ; parents Xform (lumières sous des prims imageables)
    UsdGeom.Xform.Define(st, "/Controle")
    UsdGeom.Xform.Define(st, "/Controle/Lumieres")
    sol = UsdLux.DistantLight.Define(st, "/Controle/Lumieres/soleil")
    sol.CreateIntensityAttr(1.0)
    sol.CreateExposureAttr(SOLEIL["exposition"])
    sol.CreateAngleAttr(0.53)
    sol.CreateColorAttr(Gf.Vec3f(*SOLEIL["couleur"]))
    sol.CreateNormalizeAttr(True)                       # puissance indépendante du diamètre apparent (0,53°)
    UsdGeom.Xformable(sol).AddRotateXYZOp().Set(Gf.Vec3f(90.0 - SOLEIL["hauteur_deg"], 0.0, 180.0 - SOLEIL["azimut_deg"]))
    dome = UsdLux.DomeLight_1.Define(st, "/Controle/Lumieres/ciel")
    dome.CreateTextureFileAttr(Sdf.AssetPath("./ciel_clair.hdr"))
    dome.CreateIntensityAttr(1.0)
    dome.CreateExposureAttr(0.0)
    dome.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))
    dome.CreateTextureFormatAttr("latlong")
    dome.CreatePoleAxisAttr("scene")                    # pôle du latlong selon l'axe haut de la scène (Z)
    dome.GetPrim().CreateAttribute("inputs:karma:light:renderlightgeo", Sdf.ValueTypeNames.Bool).Set(True)
    rs = UsdRender.Settings.Define(st, "/Render/rendersettings")
    rs.CreateResolutionAttr(Gf.Vec2i(1400, 1400))
    rs.GetPrim().CreateAttribute("karma:global:pathtracedsamples", Sdf.ValueTypeNames.Int).Set(64)
    st.SetMetadata("renderSettingsPrimPath", "/Render/rendersettings")
    if f.exists():
        f.unlink()
    lay.Export(str(f))
    return f


# ----------------------------------------------------------------------------------------------- développement
def courbe(x):
    k = 1.0 - EPAULE
    return np.where(x <= EPAULE, x, EPAULE + k * (1.0 - np.exp(-(x - EPAULE) / k)))


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def gains_balance():
    """Balance des blancs de recon/pcg/houdini/pj_rendu.py (carte grise horizontale soleil + ciel)."""
    zen, hor = np.array((0.30, 0.42, 0.70)), np.array((0.80, 0.86, 0.95))
    l, h = 256, 128
    el = (0.5 - (np.arange(h) + 0.5) / h) * np.pi
    t = np.clip(np.sin(np.maximum(el, 0.0)), 0, 1) ** 0.45
    ligne = np.where(el[:, None] >= 0, hor * (1 - t[:, None]) + zen * t[:, None], hor * 0.5)
    dw = (np.pi / h) * (2 * np.pi / l) * np.cos(el)
    E = float(np.sum((ligne.mean(axis=1) * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0]))
    E_s = 2.0 ** SOLEIL["exposition"] * math.sin(math.radians(SOLEIL["hauteur_deg"]))
    k = E_s / 3.5 / E
    Ec = np.array([float(np.sum((ligne[:, c] * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0])) for c in range(3)]) * k
    g = np.array((1.0, 1.0, 0.94)) / (np.array(SOLEIL["couleur"]) * E_s + Ec)
    return g / g[1]


def developper(exr, png, ev, gains):
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * (2.0 ** ev) * np.asarray(gains, dtype=np.float32)
    y = srgb(courbe(np.maximum(a, 0.0))).astype(np.float32)
    b = oiio.ImageBuf(oiio.ImageSpec(y.shape[1], y.shape[0], 3, oiio.FLOAT))
    b.set_pixels(oiio.ROI(), y)
    b = oiio.ImageBufAlgo.clamp(b, 0.0, 1.0)
    b.specmod().attribute("Software", "rendre_controle.py")
    if not b.write(str(png), "uint8"):
        raise RuntimeError(b.geterror())


def principal():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vues", default="")
    ap.add_argument("--res", type=int, default=1400)
    ap.add_argument("--spp", type=int, default=64)
    ap.add_argument("--sortie", default=str(SORTIE))
    ap.add_argument("--limite", type=int, default=600)
    a = ap.parse_args()
    REND.mkdir(parents=True, exist_ok=True)
    sol = Sol()
    infos = ecrire_cameras(sol)
    scene = ecrire_scene(infos)
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    husk = Path(sys.executable).parent / "husk.exe"
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    gains = gains_balance()
    vues = [v for v in a.vues.split(",") if v] or sorted(infos)
    tmp = Path(tempfile.mkdtemp(prefix="pj_controle_"))
    bilan = {}
    try:
        for nom in vues:
            aspect, doc, dz = infos[nom]
            rx = a.res
            ry = int(round(a.res / aspect))
            exr = tmp / f"{nom}.exr"
            cmd = [str(husk), "-R", "BRAY_HdKarmaXPU", "--settings", "/Render/rendersettings", "--camera",
                   f"/World/Cameras_controle/{nom}", "--res", str(rx), str(ry), "--frame", "1", "--output", exr.as_posix(),
                   "--make-output-path", "--timelimit", str(a.limite), "--verbose", "1", scene.as_posix()]
            t = time.time()
            r = subprocess.run(cmd, env=env, cwd=str(REND), capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            if r.returncode != 0 or not exr.exists():
                print(r.stdout[-2500:], r.stderr[-2500:])
                bilan[nom] = "échec"
                continue
            png = sortie / f"{nom}.png"
            developper(exr, png, EV, gains)
            rel = png.relative_to(RACINE).as_posix() if png.is_relative_to(RACINE) else png.as_posix()
            bilan[nom] = {"png": rel, "duree_s": round(time.time() - t, 1),
                          "translation_oeil_m": round(dz, 3), "doc": doc}
            print(f"   {nom} : {time.time() - t:.0f} s -> {png}", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for rat in sorted(REND.glob("*.rat")):
            rat.unlink()
    (REND / "rendus_controle.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                               encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
