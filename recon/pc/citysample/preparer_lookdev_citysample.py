# -*- coding: utf-8 -*-
"""Prépare le look-dev optionnel « City Sample » du carrefour Paquet Jardin (Karma / MaterialX).

À lancer avec hython (Houdini 22 : pxr, numpy et OpenImageIO inclus), APRÈS
exporter_textures_citysample.py (export Unreal des textures vers textures/brut/) :

  hython recon/pc/citysample/preparer_lookdev_citysample.py

Étapes :
  1. textures/brut/*.png -> textures/<nom>.png avec hoiiotool : 2048 px max, albédo redimensionné
     en linéaire et gardé en sRGB, cartes de données linéaires (canal extrait des cartes rangées),
     normales converties en OpenGL (+Y) quand la source est DirectX ;
  2. statistiques numpy : albédo linéaire moyen de chaque détail (normalisation du grain),
     masque d'usure de la peinture égalisé (couverture moyenne exacte) ;
  3. écrit correspondances_citysample.json (versionné, sans image) ;
  4. écrit ../houdini/lookdev_citysample.usda : surcharges MaterialX des /World/Looks/<matériau>
     existants (outputs:mtlx:surface), sans toucher au paquet. Karma préfère le contexte mtlx ;
     Unreal et les autres outils gardent l'UsdPreviewSurface.

Licence : les textures City Sample / Megascans (EULA Unreal Engine) ne sont pas redistribuables ;
textures/ est ignoré par git (recon/pc/.gitignore). Seuls le code, le JSON et la couche USD
(chemins relatifs) sont versionnés.
"""
import json
import os
import subprocess
import sys

import numpy as np
import OpenImageIO as oiio
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

ICI = os.path.dirname(os.path.abspath(__file__))
RECON = os.path.normpath(os.path.join(ICI, "..", ".."))
BRUT = os.path.join(ICI, "textures", "brut")
TEX = os.path.join(ICI, "textures")
COUCHE = os.path.normpath(os.path.join(ICI, "..", "houdini", "lookdev_citysample.usda"))
JSON_SORTIE = os.path.join(ICI, "correspondances_citysample.json")
PAQUET = os.path.join(RECON, "out", "paquet_jardin", "package")
MATERIAUX_PAQUET = os.path.join(PAQUET, "layers", "materiaux.usda")
MANIFESTE_CC0 = os.path.normpath(os.path.join(RECON, "..", "assets", "manifeste_cc0.json"))
SPEC_PEINTURE = os.path.normpath(os.path.join(RECON, "..", "assets", "specs", "peinture.json"))
TAILLE_MAX = 2048

# chemins écrits dans la couche (relatifs à recon/pc/houdini/)
REL_TEX = "./../citysample/textures/"
REL_MACRO = "../../out/paquet_jardin/package/textures/albedo_macro_8192.jpg"


def _hoiiotool():
    for d in (os.environ.get("HFS", ""), r"C:/Program Files/Side Effects Software/Houdini 22.0.459"):
        p = os.path.join(d, "bin", "hoiiotool.exe")
        if d and os.path.isfile(p):
            return p
    return "hoiiotool"


# ---------------------------------------------------------------------------------------------
# Détails City Sample retenus. Nom Megascans -> taille de tuile (…_2x2_M… = 2 m).
# canal : canal de la carte rangée (AOMRD : R=AO G=métal B=rugosité A=hauteur ; AORMD : R=AO
# G=rugosité B=métal A=hauteur ; vérifié sur les statistiques des canaux).
DETAILS = {
    "enrobe_ancien": {
        "libelle": "Enrobé ancien gris clair à granulats apparents (Asphalt_Road_2x2_M_03)",
        "albedo": "asphalt_road_03_albedo", "normale": "asphalt_road_03_normal",
        "rugosite": ("asphalt_road_03_roughness", "R"), "tile_m": 2.0,
        "tile_source": "nom Megascans Asphalt_Road_2x2_M_03",
    },
    "enrobe_piste": {
        "libelle": "Enrobé plus fermé et homogène (Asphalt_Road_2x2_M_02, enrobé de référence de City Sample)",
        "albedo": "asphalt_road_02_albedo", "normale": "asphalt_road_02_normal",
        "rugosite": ("asphalt_road_02_roughness", "R"), "tile_m": 2.0,
        "tile_source": "nom Megascans Asphalt_Road_2x2_M_02",
    },
    "enrobe_trottoir": {
        "libelle": "Enrobé fin de trottoir (Asphalt_Dried01_2x2)",
        "albedo": "asphalt_dried01_albedo", "normale": "asphalt_dried01_normal",
        "rugosite": ("asphalt_dried01_aomrd", "B"), "tile_m": 2.0,
        "tile_source": "nom Megascans Asphalt_Dried01_2x2",
    },
    "enrobe_neuf": {
        "libelle": "Enrobé neuf sombre (albédo Asphalt_Fresh_2x2_M_00 ; relief et rugosité d'Asphalt_Road_2x2_M_02, "
                   "seule l'albédo existe dans City Sample)",
        "albedo": "asphalt_fresh_00_albedo", "normale": "asphalt_road_02_normal",
        "rugosite": ("asphalt_road_02_roughness", "R"), "tile_m": 2.0,
        "tile_source": "nom Megascans Asphalt_Fresh_2x2_M_00",
    },
    "beton_clair": {
        "libelle": "Béton rugueux clair à pores (Concrete_Rough_2x2_M_00) : îlots, quais",
        "albedo": "concrete_rough_2x2_albedo", "normale": "concrete_rough_2x2_normal",
        "rugosite": ("concrete_rough_2x2_aomrd", "B"), "tile_m": 2.0,
        "tile_source": "nom Megascans Concrete_Rough_2x2_M_00",
    },
    "beton_bordure": {
        "libelle": "Béton fin un peu sale (T_ConcreteDirty, Building) : bordures",
        "albedo": "concrete_dirty_albedo", "normale": "concrete_dirty_normal",
        "rugosite": ("concrete_dirty_aormd", "G"), "tile_m": 2.0,
        "tile_source": "estimée (pas de taille dans le nom de l'asset)",
    },
}

# Masque d'usure de la peinture (bruit de taches tuilable, égalisé pour que la couverture soit exacte).
USURE_PEINTURE = {"source": "grunge_00_roughness", "canal": "R", "tile_m": 3.0, "fichier": "usure_peinture_citysample"}

# Looks du paquet surchargés. ancre : "macro" (ortho, primvar st), "paquet" (couleur unie de
# l'UsdPreviewSurface du paquet) ou "manifeste:<nom>" (albédo cible de assets/manifeste_cc0.json).
#   force_grain : 0 = pas de grain, 1 = détail/moyenne tel quel ; normale : intensité ;
#   rugosite : (min, max) de la sortie après remappage linéaire de la carte (None = carte brute).
LOOKS = {
    "sol_chaussee_macro":       {"detail": "enrobe_ancien", "ancre": "macro"},
    "sol_parking_macro":        {"detail": "enrobe_ancien", "ancre": "macro"},
    "sol_acces_riverain_macro": {"detail": "enrobe_ancien", "ancre": "macro"},
    "sol_piste_cyclable_macro": {"detail": "enrobe_piste", "ancre": "macro"},
    "sol_trottoir_macro":       {"detail": "enrobe_trottoir", "ancre": "macro"},
    "sol_ilot_macro":           {"detail": "beton_clair", "ancre": "macro"},
    "sol_quai_bus_macro":       {"detail": "beton_clair", "ancre": "macro"},
    # zones refaites en 2025 : couleur unie du paquet (l'ortho 2022 montre l'état d'avant travaux)
    "sol_parking":              {"detail": "enrobe_ancien", "ancre": "paquet"},
    "sol_acces_riverain":       {"detail": "enrobe_ancien", "ancre": "paquet"},
    "sol_piste_cyclable":       {"detail": "enrobe_piste", "ancre": "paquet"},
    "sol_trottoir":             {"detail": "enrobe_trottoir", "ancre": "paquet"},
    "sol_ilot":                 {"detail": "beton_clair", "ancre": "paquet"},
    "sol_quai_bus":             {"detail": "beton_clair", "ancre": "paquet"},
    # sans macro : albédo du détail ramenée sur l'albédo mesurée sur photos (assets/manifeste_cc0.json)
    # enrobé neuf : l'albédo Asphalt_Fresh est très mouchetée (écart-type relatif 0,9 contre 0,4-0,47 pour
    # les autres enrobés) -> grain réduit à 0,45 pour un enrobé noir fermé ; relief emprunté atténué
    "sol_chaussee_2025":        {"detail": "enrobe_neuf", "ancre": "manifeste:enrobe_bbsg_neuf",
                                 "force_grain": 0.45, "normale": 0.6, "rugosite": (0.62, 0.86)},
    "bordure":                  {"detail": "beton_bordure", "ancre": "manifeste:beton_bordure",
                                 "projection": "triplanaire"},
}
REGLAGES_DEFAUT = {"force_grain": 1.0, "normale": 1.0, "rugosite": None}

# Journal des essais de rendu (husk, Karma XPU 400x400, racine temporaire : cette couche + caméras + paquet,
# soleil + dôme), comparés au même rendu sans la couche.
ITERATIONS = [
    "v1 : réglages par défaut (grain 1, normale 1, rugosité brute). Teinte du site conservée (moyenne du sol "
    "rendu à ±5 % du rendu sans couche, vue d'ensemble à ±1 %). Enrobés anciens, trottoirs, îlots crédibles à "
    "1,3-1,6 m ; peinture usée par plaques selon la couverture. Défaut : enrobé neuf trop moucheté (albédo "
    "Asphalt_Fresh d'écart-type relatif 0,9).",
    "v2 : enrobé neuf grain 0,45 -> enrobé noir fermé homogène ; pas de répétition visible des tuiles de 2 m "
    "(basse fréquence des détails < 5 %) ni à 60 m ni au sol.",
]


# ---------------------------------------------------------------------------------------------
def _lancer(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("hoiiotool a échoué : %s\n%s" % (" ".join(args), r.stderr))


def _taille(chemin):
    spec = oiio.ImageInput.open(chemin).spec()
    return spec.width, spec.height, spec.nchannels


def _resize_args(chemin):
    w, h, _ = _taille(chemin)
    if max(w, h) <= TAILLE_MAX:
        return []
    k = TAILLE_MAX / float(max(w, h))
    return ["--resize", "%dx%d" % (round(w * k), round(h * k))]


def _export_info():
    p = os.path.join(BRUT, "export_citysample.json")
    with open(p, encoding="utf-8") as f:
        return {r["nom"]: r for r in json.load(f) if r.get("fichier")}


def preparer_albedo(nom):
    src, dst = os.path.join(BRUT, nom + ".png"), os.path.join(TEX, nom + ".png")
    _lancer([_hoiiotool(), src, "--ch", "R,G,B", "--colorconvert", "sRGB", "linear"] + _resize_args(src)
            + ["--colorconvert", "linear", "sRGB", "-d", "uint8", "-o", dst])
    return dst


def preparer_normale(nom, source_directx):
    """Normale tangente en convention OpenGL (+Y, attendue par MaterialX/Karma)."""
    src, dst = os.path.join(BRUT, nom + ".png"), os.path.join(TEX, nom + ".png")
    inv = ["--mulc", "1,-1,1", "--addc", "0,1,0"] if source_directx else []
    _lancer([_hoiiotool(), src, "--ch", "R,G,B"] + inv + _resize_args(src) + ["-d", "uint8", "-o", dst])
    return dst


def preparer_canal(nom, canal, sortie):
    """Extrait un canal (R, G, B ou A) en image 1 canal linéaire."""
    src, dst = os.path.join(BRUT, nom + ".png"), os.path.join(TEX, sortie + ".png")
    idx = str("RGBA".index(canal))
    _lancer([_hoiiotool(), src, "--ch", idx] + _resize_args(src) + ["-d", "uint8", "-o", dst])
    return dst


def _lire(chemin):
    return oiio.ImageBuf(chemin).get_pixels(oiio.FLOAT)


def srgb_vers_lineaire(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def preparer_usure():
    """Masque d'usure égalisé (rang / n) : la part de pixels au-dessus de 1-c vaut exactement c."""
    src = preparer_canal(USURE_PEINTURE["source"], USURE_PEINTURE["canal"], USURE_PEINTURE["fichier"])
    a = _lire(src)[..., 0]
    rang = np.empty(a.size)
    rang[np.argsort(a, axis=None, kind="stable")] = np.arange(a.size)
    eg = (rang / (a.size - 1)).reshape(a.shape).astype(np.float32)
    sortie = oiio.ImageOutput.create(src)
    spec = oiio.ImageSpec(a.shape[1], a.shape[0], 1, oiio.UINT16)
    sortie.open(src, spec)
    sortie.write_image(eg.reshape(a.shape[0], a.shape[1], 1))
    sortie.close()
    return src


def preparer_textures():
    os.makedirs(TEX, exist_ok=True)
    info = _export_info()
    stats = {}
    for cle, d in DETAILS.items():
        alb = preparer_albedo(d["albedo"])
        lin = srgb_vers_lineaire(_lire(alb)[..., :3])
        moy = lin.reshape(-1, 3).mean(0)
        src_dx = not info[d["normale"]]["flip_green"]
        preparer_normale(d["normale"], src_dx)
        rug_src, canal = d["rugosite"]
        rug_nom = rug_src if canal == "R" and rug_src.endswith("roughness") else rug_src + "_rugosite"
        rug = preparer_canal(rug_src, canal, rug_nom)
        r = _lire(rug)[..., 0]
        stats[cle] = {"albedo_moyen_lineaire": [round(float(x), 4) for x in moy],
                      "rugosite_moyenne": round(float(r.mean()), 3),
                      "rugosite_p05_p95": [round(float(np.percentile(r, 5)), 3), round(float(np.percentile(r, 95)), 3)],
                      "normale_source": "DirectX (-Y), vert inversé" if src_dx else "OpenGL (+Y), inchangée",
                      "fichier_rugosite": rug_nom}
        print("  %-16s albédo moyen %s  rugosité %.3f  normale %s" % (
            cle, stats[cle]["albedo_moyen_lineaire"], stats[cle]["rugosite_moyenne"], stats[cle]["normale_source"]))
    preparer_usure()
    return stats, info


# ---------------------------------------------------------------------------------------------
def couleurs_paquet():
    """diffuseColor / opacity / roughness des UsdPreviewSurface du paquet (lecture seule)."""
    st = Usd.Stage.Open(MATERIAUX_PAQUET)
    res = {}
    for p in st.GetPrimAtPath("/World/Looks").GetChildren():
        sh = st.GetPrimAtPath(p.GetPath().AppendChild("Surface"))
        if not sh:
            continue
        s = UsdShade.Shader(sh)
        v = {}
        for n in ("diffuseColor", "opacity", "roughness"):
            i = s.GetInput(n)
            if i and i.Get() is not None and not i.HasConnectedSource():
                v[n] = i.Get()
        res[p.GetName()] = v
    return res


def cibles_manifeste():
    try:
        with open(MANIFESTE_CC0, encoding="utf-8") as f:
            m = json.load(f)
        return {x["nom"]: x["cible"]["albedo_lineaire"] for x in m["materiaux"] if x.get("cible")}
    except (OSError, KeyError, ValueError):
        return {}


def salete_usure(nom_look, defaut=0.18):
    """Salissure de la classe d'usure du look (peinture_<couleur>_u0..u3/uF) selon
    assets/specs/peinture.json (usure.niveaux.<u>.salete : 0.02 pour u0 neuf 2025 ... 0.40 pour u3)."""
    u = nom_look.rsplit("_u", 1)[-1] if "_u" in nom_look else None
    try:
        with open(SPEC_PEINTURE, encoding="utf-8") as f:
            return float(json.load(f)["usure"]["niveaux"][u]["salete"])
    except (OSError, KeyError, ValueError, TypeError):
        return defaut


# ---------------------------------------------------------------------------------------------
class Graphe:
    """Petit utilitaire d'écriture de shaders MaterialX (UsdShade) sous un Material surchargé."""

    def __init__(self, stage, mat_path):
        self.stage, self.mat = stage, mat_path

    def noeud(self, nom, ident, entrees=None):
        sh = UsdShade.Shader.Define(self.stage, self.mat.AppendChild(nom))
        sh.CreateIdAttr(ident)
        for k, (typ, val) in (entrees or {}).items():
            inp = sh.CreateInput(k, typ)
            if isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], UsdShade.Shader):
                inp.ConnectToSource(val[0].ConnectableAPI(), val[1])
            elif isinstance(val, UsdShade.Shader):
                inp.ConnectToSource(val.ConnectableAPI(), "out")
            else:
                inp.Set(val)
        return sh

    def image(self, nom, ident, fichier, uv, espace, typ_def, defaut, adresse="periodic"):
        sh = self.noeud(nom, ident, {"texcoord": (Sdf.ValueTypeNames.Float2, uv), "default": (typ_def, defaut)})
        f = sh.CreateInput("file", Sdf.ValueTypeNames.Asset)
        f.Set(Sdf.AssetPath(fichier))
        f.GetAttr().SetColorSpace(espace)
        sh.CreateInput("uaddressmode", Sdf.ValueTypeNames.String).Set(adresse)
        sh.CreateInput("vaddressmode", Sdf.ValueTypeNames.String).Set(adresse)
        return sh


def _sortie(sh, typ):
    sh.CreateOutput("out", typ)
    return sh


def construire_look(stage, nom_look, cfg, d, st, couleur_ancre):
    """Réseau : base = ancre × mix(1, détail/moyenne, force) ; rugosité et normale du détail (st1 / tile)."""
    T = Sdf.ValueTypeNames
    mat_path = Sdf.Path("/World/Looks").AppendChild(nom_look)
    stage.OverridePrim(mat_path)
    g = Graphe(stage, mat_path)
    tri = cfg.get("projection") == "triplanaire"
    k_tile = 1.0 / d["tile_m"]
    moy = st["albedo_moyen_lineaire"]
    inv_moy = Gf.Vec3f(*[1.0 / max(x, 1e-4) for x in moy])
    f_alb, f_nrm = REL_TEX + d["albedo"] + ".png", REL_TEX + d["normale"] + ".png"
    f_rug = REL_TEX + st["fichier_rugosite"] + ".png"

    if tri:
        # faces verticales sans UV utiles : projection triplanaire sur la position objet (mètres)
        pos = _sortie(g.noeud("mx_position", "ND_position_vector3", {"space": (T.String, "object")}), T.Float3)
        pos_t = _sortie(g.noeud("mx_position_tuile", "ND_multiply_vector3FA",
                                {"in1": (T.Float3, pos), "in2": (T.Float, k_tile)}), T.Float3)
        alb = g.noeud("mx_detail_albedo", "ND_triplanarprojection_color3",
                      {"position": (T.Float3, pos_t), "blend": (T.Float, 0.5), "default": (T.Color3f, Gf.Vec3f(*moy))})
        rug_img = g.noeud("mx_detail_rugosite", "ND_triplanarprojection_float",
                          {"position": (T.Float3, pos_t), "blend": (T.Float, 0.5), "default": (T.Float, 0.8)})
        for sh, fic, esp in ((alb, f_alb, "srgb_texture"), (rug_img, f_rug, "raw")):
            for ax in ("filex", "filey", "filez"):
                a = sh.CreateInput(ax, T.Asset)
                a.Set(Sdf.AssetPath(fic))
                a.GetAttr().SetColorSpace(esp)
        _sortie(alb, T.Color3f)
        _sortie(rug_img, T.Float)
        nrm = None
    else:
        st1 = _sortie(g.noeud("mx_st1", "ND_geompropvalue_vector2", {"geomprop": (T.String, "st1")}), T.Float2)
        uv = _sortie(g.noeud("mx_uv_detail", "ND_multiply_vector2FA",
                             {"in1": (T.Float2, st1), "in2": (T.Float, k_tile)}), T.Float2)
        alb = _sortie(g.image("mx_detail_albedo", "ND_image_color3", f_alb, uv, "srgb_texture",
                              T.Color3f, Gf.Vec3f(*moy)), T.Color3f)
        rug_img = _sortie(g.image("mx_detail_rugosite", "ND_image_float", f_rug, uv, "raw", T.Float, 0.8), T.Float)
        nrm_img = _sortie(g.image("mx_detail_normale", "ND_image_vector3", f_nrm, uv, "raw",
                                  T.Float3, Gf.Vec3f(0.5, 0.5, 1.0)), T.Float3)
        nrm = _sortie(g.noeud("mx_normale", "ND_normalmap_float",
                              {"in": (T.Float3, nrm_img), "scale": (T.Float, float(cfg["normale"]))}), T.Float3)

    grain = _sortie(g.noeud("mx_grain", "ND_multiply_color3",
                            {"in1": (T.Color3f, alb), "in2": (T.Color3f, inv_moy)}), T.Color3f)
    grain_f = _sortie(g.noeud("mx_grain_force", "ND_mix_color3",
                              {"fg": (T.Color3f, grain), "bg": (T.Color3f, Gf.Vec3f(1, 1, 1)),
                               "mix": (T.Float, float(cfg["force_grain"]))}), T.Color3f)
    if couleur_ancre is None:
        stv = _sortie(g.noeud("mx_st", "ND_geompropvalue_vector2", {"geomprop": (T.String, "st")}), T.Float2)
        ancre = _sortie(g.image("mx_macro", "ND_image_color3", REL_MACRO, stv, "srgb_texture",
                                T.Color3f, Gf.Vec3f(0.26, 0.27, 0.25), adresse="clamp"), T.Color3f)
        base = _sortie(g.noeud("mx_base", "ND_multiply_color3",
                               {"in1": (T.Color3f, ancre), "in2": (T.Color3f, grain_f)}), T.Color3f)
    else:
        base = _sortie(g.noeud("mx_base", "ND_multiply_color3",
                               {"in1": (T.Color3f, grain_f), "in2": (T.Color3f, Gf.Vec3f(*couleur_ancre))}), T.Color3f)

    if cfg["rugosite"]:
        lo, hi = st["rugosite_p05_p95"]
        rug = _sortie(g.noeud("mx_rugosite", "ND_range_float",
                              {"in": (T.Float, rug_img), "inlow": (T.Float, lo), "inhigh": (T.Float, hi),
                               "outlow": (T.Float, float(cfg["rugosite"][0])),
                               "outhigh": (T.Float, float(cfg["rugosite"][1])), "doclamp": (T.Bool, True)}), T.Float)
    else:
        rug = rug_img

    entrees = {"base": (T.Float, 1.0), "base_color": (T.Color3f, base), "specular": (T.Float, 1.0),
               "specular_roughness": (T.Float, rug), "specular_IOR": (T.Float, 1.5), "metalness": (T.Float, 0.0)}
    if nrm is not None:
        entrees["normal"] = (T.Float3, nrm)
    surf = g.noeud("mx_surface", "ND_standard_surface_surfaceshader", entrees)
    surf.CreateOutput("out", Sdf.ValueTypeNames.Token)
    UsdShade.Material(stage.GetPrimAtPath(mat_path)).CreateSurfaceOutput("mtlx").ConnectToSource(
        surf.ConnectableAPI(), "out")


def construire_peinture(stage, nom_look, valeurs):
    """Peinture : couleur et rugosité du paquet, manques réels (opacité) selon la primvar
    « couverture » par face et le masque d'usure égalisé (moyenne de l'opacité = couverture)."""
    T = Sdf.ValueTypeNames
    mat_path = Sdf.Path("/World/Looks").AppendChild(nom_look)
    stage.OverridePrim(mat_path)
    g = Graphe(stage, mat_path)
    couleur = valeurs.get("diffuseColor", Gf.Vec3f(0.85, 0.85, 0.83))
    rug0 = float(valeurs.get("roughness", 0.6))
    couv0 = float(valeurs.get("opacity", 1.0))
    st1 = _sortie(g.noeud("mx_st1", "ND_geompropvalue_vector2", {"geomprop": (T.String, "st1")}), T.Float2)
    uv = _sortie(g.noeud("mx_uv_usure", "ND_multiply_vector2FA",
                         {"in1": (T.Float2, st1), "in2": (T.Float, 1.0 / USURE_PEINTURE["tile_m"])}), T.Float2)
    bruit = _sortie(g.image("mx_usure", "ND_image_float", REL_TEX + USURE_PEINTURE["fichier"] + ".png",
                            uv, "raw", T.Float, 1.0), T.Float)  # défaut 1 : peinture pleine si texture absente
    couv = _sortie(g.noeud("mx_couverture", "ND_geompropvalue_float",
                           {"geomprop": (T.String, "couverture"), "default": (T.Float, couv0)}), T.Float)
    seuil = _sortie(g.noeud("mx_seuil", "ND_subtract_float", {"in1": (T.Float, 1.0), "in2": (T.Float, couv)}), T.Float)
    bas = _sortie(g.noeud("mx_seuil_bas", "ND_subtract_float", {"in1": (T.Float, seuil), "in2": (T.Float, 0.04)}), T.Float)
    haut = _sortie(g.noeud("mx_seuil_haut", "ND_add_float", {"in1": (T.Float, seuil), "in2": (T.Float, 0.04)}), T.Float)
    opa = _sortie(g.noeud("mx_opacite", "ND_smoothstep_float",
                          {"in": (T.Float, bruit), "low": (T.Float, bas), "high": (T.Float, haut)}), T.Float)
    opa3 = _sortie(g.noeud("mx_opacite3", "ND_convert_float_color3", {"in": (T.Float, opa)}), T.Color3f)
    # encrassement selon la classe d'usure (salete de peinture.json) : une peinture neuve 2025 (u0)
    # reste presque propre, les vestiges (u3) sont ternes et rugueux
    s = salete_usure(nom_look)
    k = min(1.0, s / 0.18)  # 0.18 = salete de u2, amplitude de référence de la rugosité
    sale = _sortie(g.noeud("mx_salissure", "ND_range_float",
                           {"in": (T.Float, bruit), "inlow": (T.Float, 0.0), "inhigh": (T.Float, 1.0),
                            "outlow": (T.Float, 1.0 - s), "outhigh": (T.Float, 1.0), "doclamp": (T.Bool, True)}), T.Float)
    coul = _sortie(g.noeud("mx_couleur", "ND_multiply_color3FA",
                           {"in1": (T.Color3f, Gf.Vec3f(*couleur)), "in2": (T.Float, sale)}), T.Color3f)
    rug = _sortie(g.noeud("mx_rugosite", "ND_range_float",
                          {"in": (T.Float, bruit), "inlow": (T.Float, 0.0), "inhigh": (T.Float, 1.0),
                           "outlow": (T.Float, min(rug0 + 0.15 * k, 0.95)),
                           "outhigh": (T.Float, max(rug0 - 0.1 * k, 0.3)), "doclamp": (T.Bool, True)}), T.Float)
    surf = g.noeud("mx_surface", "ND_standard_surface_surfaceshader",
                   {"base": (T.Float, 1.0), "base_color": (T.Color3f, coul), "specular": (T.Float, 1.0),
                    "specular_roughness": (T.Float, rug), "metalness": (T.Float, 0.0), "opacity": (T.Color3f, opa3)})
    surf.CreateOutput("out", Sdf.ValueTypeNames.Token)
    UsdShade.Material(stage.GetPrimAtPath(mat_path)).CreateSurfaceOutput("mtlx").ConnectToSource(
        surf.ConnectableAPI(), "out")


def ecrire_couche(stats):
    paquet = couleurs_paquet()
    cibles = cibles_manifeste()
    if os.path.exists(COUCHE):
        os.remove(COUCHE)
    stage = Usd.Stage.CreateNew(COUCHE)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    lay = stage.GetRootLayer()
    lay.defaultPrim = "World"
    lay.documentation = ("Look-dev OPTIONNEL City Sample (Karma / MaterialX) du carrefour Paquet Jardin. "
                         "Couche de surcharges à placer AU-DESSUS du paquet (sublayer le plus fort). "
                         "Textures non versionnées (EULA Unreal Engine) : recon/pc/citysample/README.md. "
                         "Généré par recon/pc/citysample/preparer_lookdev_citysample.py.")
    lay.customLayerData = {"genere_par": "recon/pc/citysample/preparer_lookdev_citysample.py",
                           "textures": "recon/pc/citysample/textures (non versionnées, EULA Unreal Engine)",
                           "contexte": "outputs:mtlx:surface (Karma) ; outputs:surface UsdPreviewSurface inchangé"}
    stage.OverridePrim("/World")
    stage.OverridePrim("/World/Looks")
    resume = {}
    for nom, cfg0 in LOOKS.items():
        if nom not in paquet:
            print("  look absent du paquet, ignoré :", nom)
            continue
        cfg = dict(REGLAGES_DEFAUT, **cfg0)
        d, st = DETAILS[cfg["detail"]], stats[cfg["detail"]]
        anc = cfg["ancre"]
        if anc == "macro":
            couleur = None
        elif anc.startswith("manifeste:") and anc.split(":", 1)[1] in cibles:
            couleur = cibles[anc.split(":", 1)[1]]
        else:
            couleur = list(paquet[nom].get("diffuseColor", (0.3, 0.3, 0.3)))
        construire_look(stage, nom, cfg, d, st, couleur)
        resume[nom] = {"detail": cfg["detail"], "ancre": anc,
                       "couleur_ancre_lineaire": [round(float(x), 4) for x in couleur] if couleur else "macro (st)",
                       "force_grain": cfg["force_grain"], "normale": cfg["normale"] if cfg.get("projection") != "triplanaire" else None,
                       "rugosite_sortie": cfg["rugosite"], "projection": cfg.get("projection", "st1 / tile_m")}
    for nom in sorted(paquet):
        if nom.startswith("peinture_"):
            construire_peinture(stage, nom, paquet[nom])
            c = paquet[nom].get("opacity")
            resume[nom] = {"detail": "usure_peinture", "couverture_defaut": round(float(c), 3) if c is not None else None}
    # Define() a transformé les ancêtres en « def » sans type : on les remet en « over » (surcharge pure)
    for chemin in ["/World", "/World/Looks"] + ["/World/Looks/" + n for n in resume]:
        spec = lay.GetPrimAtPath(chemin)
        if spec:
            spec.specifier = Sdf.SpecifierOver
    lay.Save()
    return resume


def ecrire_json(stats, info, resume):
    cartes = {}
    for cle, d in DETAILS.items():
        rug_src, canal = d["rugosite"]
        cartes[cle] = {
            "libelle": d["libelle"], "tile_m": d["tile_m"], "tile_m_source": d["tile_source"],
            "albedo": {"asset_ue": info[d["albedo"]]["asset"], "fichier": "textures/%s.png" % d["albedo"],
                       "espace": "sRGB", "moyenne_lineaire": stats[cle]["albedo_moyen_lineaire"]},
            "normale": {"asset_ue": info[d["normale"]]["asset"], "fichier": "textures/%s.png" % d["normale"],
                        "espace": "données (raw)", "convention_sortie": "OpenGL (+Y)",
                        "source": stats[cle]["normale_source"],
                        "flip_green_unreal": info[d["normale"]]["flip_green"]},
            "rugosite": {"asset_ue": info[rug_src]["asset"], "fichier": "textures/%s.png" % stats[cle]["fichier_rugosite"],
                         "canal_source": canal, "espace": "données (raw)",
                         "moyenne": stats[cle]["rugosite_moyenne"], "p05_p95": stats[cle]["rugosite_p05_p95"]},
        }
    out = {
        "version": 1,
        "description": "Correspondances classes du paquet -> textures City Sample (Epic Games) pour le look-dev "
                       "optionnel Karma/MaterialX (recon/pc/houdini/lookdev_citysample.usda).",
        "licence": "Contenu City Sample / Megascans sous EULA Unreal Engine : NON redistribuable. Les fichiers "
                   "image ne sont jamais versionnés (recon/pc/.gitignore) ; ce JSON ne contient que des chemins.",
        "projet_source": "C:/Users/flori/Documents/Unreal Projects/CitySample/CitySample.uproject (Unreal Engine 5.7)",
        "dossier_textures": "recon/pc/citysample/textures (2048 px max ; brut/ = export Unreal pleine résolution)",
        "regeneration": [
            "UnrealEditor-Cmd.exe <CitySample.uproject> -run=pythonscript "
            "-script=<depot>/recon/pc/citysample/exporter_textures_citysample.py -unattended -nop4 -nosplash -NullRHI",
            "hython recon/pc/citysample/preparer_lookdev_citysample.py"],
        "conventions": {
            "uv_detail": "primvar st1 (mètres du repère local) × 1/tile_m ; bordures : projection triplanaire "
                         "de la position objet (faces verticales, st1 dégénérée)",
            "uv_macro": "primvar st (0-1 sur l'emprise), ../../out/paquet_jardin/package/textures/albedo_macro_8192.jpg",
            "couleur": "base = ancre × mix(1, détail / moyenne_lineaire_du_détail, force_grain) ; ancre = macro "
                       "(ortho) ou couleur unie du paquet (zones 2025) ou albédo mesurée sur photos "
                       "(assets/manifeste_cc0.json : enrobé neuf, béton de bordure)",
            "normales": "tangentes OpenGL (+Y). Les sources Unreal marquées flip_green_channel sont déjà en OpenGL "
                        "(Unreal les retourne à la compilation) ; les autres sont en DirectX et ont le vert inversé. "
                        "Vérifié par corrélation normale / carte de hauteur sur 3 textures.",
            "rangement_canaux": {"AOMRD": "R=AO G=métal B=rugosité A=hauteur",
                                 "AORMD": "R=AO G=rugosité B=métal A=hauteur",
                                 "RAODM": "R=rugosité G=AO B=hauteur (A non utilisé, =1)"},
        },
        "details": cartes,
        "usure_peinture": {"asset_ue": info[USURE_PEINTURE["source"]]["asset"],
                           "fichier": "textures/%s.png" % USURE_PEINTURE["fichier"], "tile_m": USURE_PEINTURE["tile_m"],
                           "traitement": "canal R égalisé (rang) en 16 bits : opacité = smoothstep(1-c±0,04, bruit), "
                                         "moyenne = couverture c (primvar uniforme « couverture » des marquages)"},
        "looks": resume,
        "essais_rendu": ITERATIONS,
        "absents_de_city_sample": {
            "gazon / pelouse": "aucune texture d'herbe dans City Sample (ville minérale) : sol_espace_vert* et "
                               "sol_terre_plein_vegetal* gardent l'UsdPreviewSurface (CC0 Grass004 : assets/manifeste_cc0.json)",
            "piste cyclable colorée": "aucun enrobé rouge/ocre : la teinte vient de l'ortho ou de la couleur du paquet",
            "enrobé neuf": "albédo seule (Asphalt_Fresh_2x2_M_00) : relief et rugosité empruntés à Asphalt_Road_2x2_M_02",
        },
        "remarques_export": {
            "sidewalk_concrete_nolines_aor": "export vide (tous les canaux à 0) : non utilisée",
            "bordures_city_sample": "le kit Small_Curb_A utilise des textures propres aux maillages (UV non tuilables) : "
                                    "béton tuilable T_ConcreteDirty retenu à la place",
        },
        "textures_exportees": [
            {"nom": r["nom"], "asset_ue": r["asset"], "srgb": r["srgb"], "compression": r["compression"],
             "flip_green": r["flip_green"]} for r in info.values()],
    }
    with open(JSON_SORTIE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


def main():
    if not os.path.isdir(BRUT):
        sys.exit("Textures brutes absentes (%s) : lance d'abord exporter_textures_citysample.py dans Unreal." % BRUT)
    print("Préparation des textures (hoiiotool)…")
    stats, info = preparer_textures()
    print("Couche look-dev :", COUCHE)
    resume = ecrire_couche(stats)
    ecrire_json(stats, info, resume)
    print("Correspondances :", JSON_SORTIE)


if __name__ == "__main__":
    main()
