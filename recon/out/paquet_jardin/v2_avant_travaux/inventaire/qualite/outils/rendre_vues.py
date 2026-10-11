"""Rendus Karma CPU de la fabrication fabrique_hda (copie locale) aux poses des vignettes photo."""
import json, math, os, subprocess, sys, time
from pathlib import Path
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, Vt
S = Path("C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q")
FAB = S / "fab"
CAMS = json.load(open("D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2_avant_travaux/inventaire/qualite/photos_non_versionnees/cameras_vignettes.json"))
COUCHES = ("sol.usdc", "bordures.usdc", "caniveaux.usda", "ilots.usda", "marquages_lignes.usda", "passages.usda", "symboles.usda", "zones.usda", "materiaux_ue.usda")
st = Usd.Stage.CreateInMemory()
lay = st.GetRootLayer()
lay.subLayerPaths = [f"./fab/{c}" for c in COUCHES]
UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
UsdGeom.Xform.Define(st, "/Controle")
doc = json.load(open(FAB / "points/symboles.json", encoding="utf-8"))
assets = sorted({p["asset"] for p in doc["points"]})
pi = UsdGeom.PointInstancer.Define(st, "/Controle/symboles")
UsdGeom.Scope.Define(st, "/Controle/symboles/Prototypes")
cib = []
for a in assets:
    pr = st.DefinePrim(f"/Controle/symboles/Prototypes/{a}", "Xform")
    pr.GetReferences().AddReference("./fab/prototypes/symboles.usda", f"/World/PJ_Marquages/{a}")
    cib.append(pr.GetPath())
pi.CreatePrototypesRel().SetTargets(cib)
idx = {a: i for i, a in enumerate(assets)}
pi.CreateProtoIndicesAttr(Vt.IntArray([idx[p["asset"]] for p in doc["points"]]))
pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(*p["p"]) for p in doc["points"]]))
pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(p["q"][3], p["q"][0], p["q"][1], p["q"][2]) for p in doc["points"]]))
pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(*p["s"]) for p in doc["points"]]))
UsdGeom.Xform.Define(st, "/Controle/Lumieres")
sol = UsdLux.DistantLight.Define(st, "/Controle/Lumieres/soleil")
sol.CreateIntensityAttr(1.0); sol.CreateExposureAttr(2.0); sol.CreateAngleAttr(0.53)
sol.CreateColorAttr(Gf.Vec3f(1.0, 0.95, 0.88)); sol.CreateNormalizeAttr(True)
UsdGeom.Xformable(sol).AddRotateXYZOp().Set(Gf.Vec3f(90.0 - 29.0, 0.0, 180.0 - 220.0))
dome = UsdLux.DomeLight_1.Define(st, "/Controle/Lumieres/ciel")
dome.CreateTextureFileAttr(Sdf.AssetPath("./fab/ciel_clair.hdr")); dome.CreateIntensityAttr(1.0)
dome.CreateTextureFormatAttr("latlong"); dome.CreatePoleAxisAttr("scene")
dome.GetPrim().CreateAttribute("inputs:karma:light:renderlightgeo", Sdf.ValueTypeNames.Bool).Set(True)
UsdGeom.Scope.Define(st, "/Cams")
for nom, c in CAMS.items():
    Rm = np.array(c["R"]); C = np.array(c["C"])
    d, a, h = Rm[0], Rm[1], Rm[2]
    m = Gf.Matrix4d(d[0], d[1], d[2], 0, h[0], h[1], h[2], 0, -a[0], -a[1], -a[2], 0, C[0], C[1], C[2], 1)
    cam = UsdGeom.Camera.Define(st, f"/Cams/c_{nom}")
    ha = 36.0; va = ha * c["H"] / c["W"]
    cam.CreateFocalLengthAttr((ha / 2) / math.tan(math.radians(c["hfov"]) / 2))
    cam.CreateHorizontalApertureAttr(ha); cam.CreateVerticalApertureAttr(va)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.05, 3000.0))
    cam.AddTransformOp().Set(m)
rs = UsdRender.Settings.Define(st, "/Render/rendersettings")
rs.CreateResolutionAttr(Gf.Vec2i(960, 640))
rs.GetPrim().CreateAttribute("karma:global:pathtracedsamples", Sdf.ValueTypeNames.Int).Set(16)
st.SetMetadata("renderSettingsPrimPath", "/Render/rendersettings")
scene = S / "scene_vues.usda"
lay.Export(str(scene))
husk = Path(sys.executable).parent / "husk.exe"
vues = sys.argv[1].split(",") if len(sys.argv) > 1 else list(CAMS)
for nom in vues:
    exr = S / f"rendu_{nom}.exr"
    t = time.time()
    cmd = [str(husk), "-R", "BRAY_HdKarma", "--settings", "/Render/rendersettings", "--camera", f"/Cams/c_{nom}", "--res", "960", "640",
           "--frame", "1", "--output", exr.as_posix(), "--make-output-path", "--timelimit", "400", "--verbose", "1", scene.as_posix()]
    r = subprocess.run(cmd, cwd=str(S), capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(nom, r.returncode, exr.exists(), round(time.time() - t, 1), r.stderr[-800:] if r.returncode else "")
