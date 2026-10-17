"""Rendus Karma XPU de contrôle du lot L2 (hython Houdini 22 : pxr, husk, OpenImageIO) : couches USD des géométries
fabriquées, matériaux PBR CC0 de la bibliothèque (assets/lib/route_fr, assets/lib/materiaux), soleil et ciel, caméras
piéton, oblique et de dessus, développement à exposition fixe, découpe en tuiles natives (recon/pcg/vision/decoupe.py).

Utilisé par recon/generateur/fabriquer_generateur.py (--l2 --rendus). Rien de ce module ne fabrique la route : il
écrit les maillages déjà fabriqués (rg::sol, pj::bordure, pj::caniveau, BEV) en USD Z haut et pose un décor de rendu
(fond herbeux au-delà des abords, arbres procéduraux simples aux points d'arbres du modèle, ciel en dégradé), déclaré
comme tel dans le manifeste des rendus.
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

DEPOT = Path(__file__).resolve().parents[3]
LIB_ROUTE = DEPOT / "assets" / "lib" / "route_fr" / "materiaux"
LIB_SITE = DEPOT / "assets" / "lib" / "materiaux"
DECOUPE = DEPOT / "recon" / "pcg" / "vision" / "decoupe.py"
# peintures routières (lot L2b) : une bibliothèque, un Material par couleur et classe d'usure (peinture_<couleur>_u<n>)
PEINTURE = LIB_ROUTE / "peinture_routiere" / "peinture_routiere.usda"

# matériaux : materiau_id -> (bibliothèque, nom) ; sinon couleur simple (albédo linéaire, rugosité)
ALIAS = {
    "beton_bordure_gris": ("site", "beton_bordure"),
    "beton_bordure_clair": ("site", "beton_bordure"),
    "beton_bordure": ("site", "beton_bordure"),
    "caniveau_beton": ("site", "beton_bordure"),
    "dalles_beton": ("route", "dalles_beton_40"),          # dalles claires (albédo moyen 0,56 ; grises : 0,38)
    # caniveau à grille au droit d'un ralentisseur et grilles d'avaloir au pied des rampes de plateau (correction
    # après contrôle) : grille de la bibliothèque (ambientCG Grate001, CC0, catalogue_assets_route.json)
    "grille_caniveau": ("site", "decal_grille_avaloir"),
    "grille_avaloir": ("site", "decal_grille_avaloir"),
}
# cartes de rugosité inversées dans la bibliothèque (moyenne 0,26 : un gazon brillant comme de l'eau, qui reflète les
# troncs) : inversées au rendu (UsdUVTexture scale −1, bias 1), à corriger dans assets/lib (signalé au rapport L2)
INVERSER_RUGOSITE = {"gazon_tondu"}
SIMPLES = {
    "mortier_joint": ((0.05, 0.05, 0.048), 0.9),
    "mortier_clair": ((0.25, 0.245, 0.23), 0.9),
    "sol_cache": ((0.04, 0.04, 0.04), 1.0),
    "PJ_Neutre": ((0.3, 0.3, 0.3), 0.8),
    "ecorce": ((0.07, 0.055, 0.04), 0.85),
    "feuillage": ((0.045, 0.085, 0.025), 0.6),
    "feuillage_clair": ((0.07, 0.11, 0.03), 0.6),
    "peinture_blanche": ((0.62, 0.62, 0.60), 0.45),
}

# éclairage (unités UsdLux, DistantLight normalisée : ASSETS_ROUTE.md § 3) ; exposition fixe
SOLEIL = 4.2
CIEL_ZENITH = (0.10, 0.20, 0.42)
CIEL_HORIZON = (0.42, 0.48, 0.56)
SOL_LOINTAIN = (0.06, 0.07, 0.05)


def chemin_materiau(mid):
    """Fichier .usda de la bibliothèque pour un materiau_id (ou None : matériau simple)."""
    if mid in ALIAS:
        lib, nom = ALIAS[mid]
        base = LIB_ROUTE if lib == "route" else LIB_SITE
        f = base / nom / f"{nom}.usda"
        return f if f.exists() else None
    for base in (LIB_SITE, LIB_ROUTE):                 # bibliothèque du site d'abord (albédos étalonnés)
        f = base / mid / f"{mid}.usda"
        if f.exists():
            return f
    return None


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------- géométrie -> USD
def maillages(geo, nom_couche, attr_mat="materiau_id", filtre=None):
    """hou.Geometry (Y haut) -> {materiau_id: (points Z haut, comptes, indices, normales fV, uv fV)}.
    Faces Houdini : enroulement gauche (orientation USD leftHanded, comme pj::preparer_export avant inversion)."""
    import hou  # noqa: F401
    out = {}
    P = np.array(geo.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
    attN = geo.findVertexAttrib("N")
    attUV = geo.findVertexAttrib("uv")
    for pr in geo.prims():
        if filtre is not None and not filtre(pr):
            continue
        try:
            mid = pr.attribValue(attr_mat) or "PJ_Neutre"
        except Exception:  # noqa: BLE001
            mid = "PJ_Neutre"
        vs = pr.vertices()
        if len(vs) < 3:
            continue
        d = out.setdefault(mid, {"pts": {}, "P": [], "n": [], "i": [], "N": [], "uv": []})
        d["n"].append(len(vs))
        for v in vs:
            pn = v.point().number()
            j = d["pts"].get(pn)
            if j is None:
                j = len(d["P"])
                d["pts"][pn] = j
                x, y, z = P[pn]
                d["P"].append((x, -z, y))
            d["i"].append(j)
            if attN is not None:
                nx, ny, nz = v.attribValue(attN)
                d["N"].append((nx, -nz, ny))
            if attUV is not None:
                u = v.attribValue(attUV)
                d["uv"].append((u[0], u[1]))
    return out


def ecrire_couche(stage, chemin, donnees, liaisons):
    """Écrit les maillages {materiau_id: ...} sous chemin (Xform) ; liaisons[materiau_id] = UsdShade.Material."""
    from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt
    UsdGeom.Xform.Define(stage, chemin)
    for mid in sorted(donnees):
        d = donnees[mid]
        nom = "".join(c if c.isalnum() else "_" for c in mid)
        m = UsdGeom.Mesh.Define(stage, f"{chemin}/{nom}")
        m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in d["P"]]))
        m.CreateFaceVertexCountsAttr(Vt.IntArray(d["n"]))
        m.CreateFaceVertexIndicesAttr(Vt.IntArray(d["i"]))
        m.CreateOrientationAttr(UsdGeom.Tokens.leftHanded)
        m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        if d["N"]:
            m.CreateNormalsAttr(Vt.Vec3fArray([Gf.Vec3f(*n) for n in d["N"]]))
            m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
        if d["uv"]:
            for pv in ("st", "st1"):
                p = UsdGeom.PrimvarsAPI(m).CreatePrimvar(pv, Sdf.ValueTypeNames.TexCoord2fArray,
                                                         UsdGeom.Tokens.faceVarying)
                p.Set(Vt.Vec2fArray([Gf.Vec2f(*u) for u in d["uv"]]))
        UsdShade.MaterialBindingAPI.Apply(m.GetPrim())
        UsdShade.MaterialBindingAPI(m).Bind(liaisons[mid])


def materiaux(stage, ids, dossier_usd, racine="/Looks"):
    """Matériaux <racine>/<id> : référence au .usda de la bibliothèque, sinon UsdPreviewSurface simple. Une couche
    destinée à être référencée range ses matériaux sous son prim par défaut (racine = /Monde/Looks)."""
    from pxr import Gf, Sdf, UsdShade
    liaisons, sources = {}, {}
    for mid in sorted(ids):
        nom = "".join(c if c.isalnum() else "_" for c in mid)
        chemin = f"{racine}/{nom}"
        f = chemin_materiau(mid)
        if mid.startswith("peinture_") and PEINTURE.exists():
            m = UsdShade.Material.Define(stage, chemin)
            m.GetPrim().GetReferences().AddReference(Path(os.path.relpath(PEINTURE, dossier_usd)).as_posix(),
                                                     f"/peinture_routiere/{mid}")
            sources[mid] = str(PEINTURE.relative_to(DEPOT)).replace("\\", "/") + f" </peinture_routiere/{mid}>"
        elif f is not None:
            m = UsdShade.Material.Define(stage, chemin)
            m.GetPrim().GetReferences().AddReference(Path(os.path.relpath(f, dossier_usd)).as_posix())
            sources[mid] = str(f.relative_to(DEPOT)).replace("\\", "/")
            if f.stem in INVERSER_RUGOSITE:
                rug = stage.OverridePrim(chemin + "/Rugosite")
                rug.CreateAttribute("inputs:scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1, -1, -1, 1))
                rug.CreateAttribute("inputs:bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(1, 1, 1, 0))
                sources[mid] += " (rugosité inversée au rendu)"
        else:
            col, rug = SIMPLES.get(mid, SIMPLES["PJ_Neutre"])
            m = UsdShade.Material.Define(stage, chemin)
            sh = UsdShade.Shader.Define(stage, chemin + "/Surface")
            sh.CreateIdAttr("UsdPreviewSurface")
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*col))
            sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rug)
            sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
            m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
            sources[mid] = "simple" if mid in SIMPLES else "simple (materiau_id sans fichier : gris neutre)"
        liaisons[mid] = UsdShade.Material(stage.GetPrimAtPath(chemin))
    return liaisons, sources


def ciel_exr(chemin):
    """Ciel en dégradé (lat-long 1024 × 512, linéaire) : zénith bleu, horizon clair, sol lointain sombre."""
    import OpenImageIO as oiio
    W, H = 1024, 512
    v = (np.arange(H) + 0.5) / H                       # 0 = zénith, 1 = nadir
    el = (0.5 - v) * math.pi                           # élévation
    img = np.zeros((H, W, 3), dtype=np.float32)
    for c in range(3):
        haut = CIEL_HORIZON[c] + (CIEL_ZENITH[c] - CIEL_HORIZON[c]) * np.clip(np.sin(np.maximum(el, 0)), 0, 1) ** 0.6
        bas = SOL_LOINTAIN[c]
        col = np.where(el >= 0, haut, bas)
        img[:, :, c] = col[:, None]
    spec = oiio.ImageSpec(W, H, 3, oiio.FLOAT)
    o = oiio.ImageOutput.create(str(chemin))
    o.open(str(chemin), spec)
    o.write_image(img)
    o.close()


def exposition():
    """Exposition fixe : éclairement horizontal du soleil (40°) et du ciel (radiance moyenne de la demi-sphère)."""
    ciel_moy = sum(0.5 * (a + b) for a, b in zip(CIEL_ZENITH, CIEL_HORIZON)) / 3
    e = SOLEIL * math.sin(math.radians(40.0)) + math.pi * ciel_moy
    return math.pi / e * 1.10


def lumieres(stage, azimut_soleil_deg, ciel):
    from pxr import Gf, Sdf, UsdGeom, UsdLux
    sun = UsdLux.DistantLight.Define(stage, "/Lumieres/Soleil")
    sun.CreateIntensityAttr(SOLEIL)
    sun.CreateAngleAttr(0.53)
    sun.CreateNormalizeAttr(True)        # Karma / USD 26 : sans normalisation, éclairage 15 000 fois trop faible
    sun.CreateColorAttr(Gf.Vec3f(1.0, 0.96, 0.90))
    xf = UsdGeom.Xformable(sun)
    xf.AddRotateZOp().Set(azimut_soleil_deg)
    xf.AddRotateXOp().Set(90.0 - 40.0)
    dome = UsdLux.DomeLight.Define(stage, "/Lumieres/Ciel")
    dome.CreateIntensityAttr(1.0)
    UsdGeom.Xformable(dome).AddRotateXOp().Set(90.0)   # texture lat-long Y haut -> scène Z haut
    dome.CreateTextureFileAttr(Sdf.AssetPath(Path(ciel).as_posix()))
    dome.CreateTextureFormatAttr(UsdLux.Tokens.latlong)
    # Karma : le dôme n'est visible de la caméra (fond de ciel) qu'avec « Render Light Geometry »
    dome.GetPrim().CreateAttribute("karma:light:renderlightgeo", Sdf.ValueTypeNames.Bool).Set(True)


def camera(stage, nom, oeil, cible, focale=28.0, res=(1600, 1000), ortho=None):
    """Caméra (repère local Z haut) ; ortho = (largeur, hauteur) en m pour une vue orthographique de dessus."""
    from pxr import Gf, UsdGeom
    cam = UsdGeom.Camera.Define(stage, f"/Cameras/{nom}")
    W, H = res
    if ortho:
        cam.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
        cam.CreateHorizontalApertureAttr(ortho[0] * 10.0)        # unités de 1/10 de scène (mm -> cm conventions USD)
        cam.CreateVerticalApertureAttr(ortho[1] * 10.0)
    else:
        cam.CreateFocalLengthAttr(focale)
        cam.CreateHorizontalApertureAttr(36.0)
        cam.CreateVerticalApertureAttr(36.0 * H / W)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.05, 5000.0))
    haut = Gf.Vec3d(0, 0, 1)
    d = Gf.Vec3d(*cible) - Gf.Vec3d(*oeil)
    if abs(d.GetNormalized()[2]) > 0.999:
        haut = Gf.Vec3d(0, 1, 0)
    m4 = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*oeil), Gf.Vec3d(*cible), haut).GetInverse()
    UsdGeom.Xformable(cam).AddTransformOp().Set(m4)
    return cam


def fond(stage, centre, z, liaison, demi=400.0):
    """Décor : grand plan herbeux sous et autour de la scène (au-delà des abords du modèle), à la cote z donnée (1 mm sous son bord)."""
    from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt
    cx, cy = centre
    m = UsdGeom.Mesh.Define(stage, "/Decor/Fond")
    pts = [(cx - demi, cy - demi, z), (cx + demi, cy - demi, z), (cx + demi, cy + demi, z), (cx - demi, cy + demi, z)]
    m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
    m.CreateFaceVertexCountsAttr(Vt.IntArray([4]))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray([0, 1, 2, 3]))
    m.CreateNormalsAttr(Vt.Vec3fArray([Gf.Vec3f(0, 0, 1)] * 4))
    m.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    for pv in ("st", "st1"):
        p = UsdGeom.PrimvarsAPI(m).CreatePrimvar(pv, Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
        p.Set(Vt.Vec2fArray([Gf.Vec2f(p_[0], p_[1]) for p_ in pts]))
    UsdShade.MaterialBindingAPI.Apply(m.GetPrim())
    UsdShade.MaterialBindingAPI(m).Bind(liaison)


def husk():
    h = Path(sys.executable).parent / "husk.exe"
    if h.exists():
        return str(h)
    return str(sorted(Path("C:/Program Files/Side Effects Software").glob("Houdini 22*/bin/husk.exe"))[-1])


def python_systeme():
    if os.environ.get("RG_PYTHON"):
        return os.environ["RG_PYTHON"]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        f = Path(d) / "python.exe"
        if f.exists() and not any(k in str(f).lower() for k in ("side effects", "sideef", "houdin", "windowsapps")):
            return str(f)
    return "python"


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def developper(exr, png, expo):
    import OpenImageIO as oiio
    from PIL import Image
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * expo
    ep = 0.75
    y = np.where(a <= ep, a, ep + (1 - ep) * (1 - np.exp(-(a - ep) / (1 - ep))))
    Image.fromarray((srgb(y) * 255 + 0.5).astype(np.uint8)).save(png)


def rendre(usd, cameras, dossier, res, limite_s=120, tmp=None):
    """husk (Karma XPU) pour chaque caméra -> EXR -> PNG (exposition fixe) ; renvoie {camera: png}."""
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    tmp = Path(tmp or dossier)
    tmp.mkdir(parents=True, exist_ok=True)
    out = {}
    for nom in cameras:
        exr = tmp / f"{nom}.exr"
        cmd = [husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/reglages", "--camera",
               f"/Cameras/{nom}", "--res", str(res[0]), str(res[1]), "--frame", "1", "--output", exr.as_posix(),
               "--make-output-path", "--timelimit", str(limite_s), "--verbose", "1", Path(usd).as_posix()]
        # garde : husk doit rendre la main (limite de rendu + chargement) ; sinon le rendu est en échec
        r = subprocess.run(cmd, env=env, cwd=str(tmp), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=limite_s + 180)
        if r.returncode != 0 or not exr.exists():
            raise RuntimeError(f"rendu {nom} en échec : {r.stdout[-1500:]} {r.stderr[-1500:]}")
        png = Path(dossier) / f"{nom}.png"
        developper(exr, png, exposition())
        exr.unlink()
        out[nom] = png
    return out


def tuiles(png, dossier):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "HOUDINI", "HFS", "H_"))}
    shutil.rmtree(dossier, ignore_errors=True)
    r = subprocess.run([python_systeme(), str(DECOUPE), "image", str(png), str(dossier)], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"découpe {png} : {r.stdout[-800:]} {r.stderr[-800:]}")
    m = json.loads((Path(dossier) / "tuiles.json").read_text(encoding="utf-8"))
    return m


def nettoyer_rat():
    for base in (LIB_ROUTE, LIB_SITE):
        for rat in base.rglob("*.rat"):
            rat.unlink()
