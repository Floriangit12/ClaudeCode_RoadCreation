"""Contrôle visuel de l'intégration : toutes les couches USD fabriquées par la scène maîtresse, composées dans une scène de
rendu, plus les symboles instanciés (points/symboles.json -> PointInstancer sur prototypes/symboles.usda), rendus par
husk (Karma XPU). Lecture seule des sorties ; écrit controle/integration.usda et controle/integration_<vue>.png.

    hython recon/pcg/houdini/hda/commun/rendre_integration.py [--sortie DIR] [--vues site,centre,...] [--res 1600]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, Vt

RACINE = Path(__file__).resolve().parents[5]
SORTIE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda"
COUCHES = ("sol", "bordures", "caniveaux", "ilots", "marquages_lignes", "passages", "symboles", "zones")
# vues : (oeil, cible) en repère local Z haut (m) et focale (mm), ou ("ortho", centre, largeur)
VUES = {
    "site": ("ortho", (0.0, 0.0), 300.0),
    "centre": ("ortho", (0.0, 0.0), 70.0),
    "oblique_centre": ((-38.0, -46.0, 32.0), (2.0, 0.0, 0.0), 24.0),
    "oblique_pilote": ((-12.0, -22.0, 14.0), (22.0, 14.0, 0.0), 24.0),
    "rue": ((-24.0, -4.0, 1.7), (6.0, 1.0, 0.2), 20.0),
}


def scene(sortie):
    """controle/integration.usda : sous-couches de toutes les branches + symboles instanciés + caméras + éclairage."""
    sortie = Path(sortie)
    f = sortie / "controle" / "integration.usda"
    lay = Sdf.Layer.CreateNew(str(f)) if not f.exists() else Sdf.Layer.FindOrOpen(str(f))
    lay.Clear()
    couches = []
    for b in COUCHES:
        for ext in ("usdc", "usda"):
            if (sortie / f"{b}.{ext}").exists():
                couches.append(f"../{b}.{ext}")
                break
    couches.append("../materiaux_ue.usda")
    lay.subLayerPaths = couches
    st = Usd.Stage.Open(lay)
    st.SetMetadata("upAxis", "Z")
    st.SetMetadata("metersPerUnit", 1.0)
    ap = UsdGeom.Scope.Define(st, "/Apercu")
    n_inst = 0
    pts_f = sortie / "points" / "symboles.json"
    protos_f = sortie / "prototypes" / "symboles.usda"
    if pts_f.exists() and protos_f.exists():
        doc = json.loads(pts_f.read_text(encoding="utf-8"))
        assets = sorted({p["asset"] for p in doc["points"]})
        pi = UsdGeom.PointInstancer.Define(st, "/Apercu/symboles")
        UsdGeom.Scope.Define(st, "/Apercu/symboles/Prototypes")
        cibles = []
        for a in assets:
            pr = st.DefinePrim(f"/Apercu/symboles/Prototypes/{a}", "Xform")
            pr.GetReferences().AddReference("../prototypes/symboles.usda", f"/World/PJ_Marquages/{a}")
            cibles.append(pr.GetPath())
        pi.CreatePrototypesRel().SetTargets(cibles)
        idx = {a: i for i, a in enumerate(assets)}
        pi.CreateProtoIndicesAttr(Vt.IntArray([idx[p["asset"]] for p in doc["points"]]))
        pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(*p["p"]) for p in doc["points"]]))
        pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(p["q"][3], p["q"][0], p["q"][1], p["q"][2])
                                                 for p in doc["points"]]))
        pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(*p["s"]) for p in doc["points"]]))
        n_inst = len(doc["points"])
    for nom, v in VUES.items():
        cam = UsdGeom.Camera.Define(st, f"/Apercu/camera_{nom}")
        if v[0] == "ortho":
            (cx, cy), largeur = v[1], v[2]
            cam.CreateProjectionAttr("orthographic")
            cam.CreateHorizontalApertureAttr(largeur * 10.0)      # dixièmes d'unité de scène
            cam.CreateVerticalApertureAttr(largeur * 10.0)
            m = Gf.Matrix4d().SetTranslate(Gf.Vec3d(cx, cy, 250.0))
            cam.CreateClippingRangeAttr(Gf.Vec2f(1.0, 1000.0))
        else:
            oeil, cible, focale = v
            vue = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*oeil), Gf.Vec3d(*cible), Gf.Vec3d(0, 0, 1))
            m = vue.GetInverse()
            cam.CreateFocalLengthAttr(focale)
            cam.CreateHorizontalApertureAttr(36.0)
            cam.CreateVerticalApertureAttr(36.0 * 10 / 16)
            cam.CreateClippingRangeAttr(Gf.Vec2f(0.05, 2000.0))
        cam.AddTransformOp().Set(m)
    sol = UsdLux.DistantLight.Define(st, "/Apercu/soleil")
    sol.CreateIntensityAttr(2.6)
    sol.CreateAngleAttr(0.53)
    xf = UsdGeom.Xformable(sol)
    xf.AddRotateXYZOp().Set(Gf.Vec3f(48.0, 0.0, -135.0))
    ciel = UsdLux.DomeLight.Define(st, "/Apercu/ciel")
    ciel.CreateIntensityAttr(0.55)
    ciel.CreateColorAttr(Gf.Vec3f(0.75, 0.85, 1.0))
    rs = UsdRender.Settings.Define(st, "/Render/rendersettings")
    rs.CreateCameraRel().SetTargets([Sdf.Path("/Apercu/camera_site")])
    rs.CreateResolutionAttr(Gf.Vec2i(1600, 1000))
    lay.Save()
    return f, n_inst, couches


def rendre(f, sortie, vues, res):
    husk = Path(sys.executable).parent / "husk.exe"
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    out = {}
    for nom in vues:
        png = Path(sortie) / "controle" / f"integration_{nom}.png"
        rx, ry = (res, res) if VUES[nom][0] == "ortho" else (res, int(res * 10 / 16))
        cmd = [str(husk), "-R", "BRAY_HdKarmaXPU", "--settings", "/Render/rendersettings", "--camera",
               f"/Apercu/camera_{nom}", "--res", str(rx), str(ry), "--frame", "1", "--output", png.as_posix(),
               "--make-output-path", "--verbose", "1", Path(f).as_posix()]
        t = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not png.exists():
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit(f"rendu {nom} en échec")
        out[nom] = {"png": png.relative_to(RACINE).as_posix(), "duree_s": round(time.time() - t, 1)}
        print(f"   {nom} : {out[nom]['duree_s']} s -> {png}")
    return out


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=str(SORTIE))
    ap.add_argument("--vues", default=",".join(VUES))
    ap.add_argument("--res", type=int, default=1600)
    a = ap.parse_args()
    f, n, couches = scene(a.sortie)
    print(json.dumps({"scene": str(f), "symboles_instancies": n, "couches": couches}, ensure_ascii=False))
    rendre(f, a.sortie, [v for v in a.vues.split(",") if v], a.res)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
