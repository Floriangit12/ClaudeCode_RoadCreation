"""Matériaux v2 (materiaux_v2.usda) : un Material par materiau_id de assets/specs/materiaux_sol.json.

Deux réseaux par matériau, sur les mêmes textures CC0 de assets/lib/materiaux/<nom>/textures :
- MaterialX (contexte `mtlx`, lu par Karma) : standard_surface ; albédo, rugosité, normale (OpenGL)
  et AO en tuilage hexagonal (ND_hextiledimage : rotation / décalage aléatoires par cellule, pas
  de répétition visible) ; variation macro (fractal 3D sur la position monde, quelques mètres) ;
  primvars facultatifs : `teinte` (gain par instance), `uv_decalage` (décalage par instance),
  `salissure` (assombrissement, sommet ou instance), `z_pied` (bordures : fil d'eau dans le repère
  de l'élément, salissure concentrée au pied) et `couleur` (gain RVB par instance, éclats) ;
- UsdPreviewSurface (contexte universel, import Unreal / visualiseurs) : textures simples.
UV : primvar `st1` en mètres, mis à l'échelle par 1 / tile_m. Côté Unreal, chaque maillage porte
`unrealMaterial = /Game/PJ/Materials/MI_<materiau_id>` (remappage par materiau_id).
Surcharges de rendu (source CC0, albédo visé, réglages de famille) : assets/specs/materiaux_rendu_v2.json
(Specs.materiau_rendu) ; matériaux maison sans texture : mortiers, bitume de pontage, touffes d'herbe ;
peinture routière à macrotexture d'enrobé. Béton de bordure : moucheté d'agrégats fins et vieillissement
piloté par l'aspect décrit (_bordure_details). Normale de texture omise sous une force de 0,05 (Karma
XPU n'applique pas `strength` de ND_hextilednormalmap).
"""
from pathlib import Path

from pxr import Gf, Sdf, UsdShade

import pj_commun as K
import pj_usd as U

T = Sdf.ValueTypeNames
LOOKS = "/World/Looks_v2"

# réglages de rendu par famille (amplitude macro, fréquence macro 1/m, gain de salissure)
# + contraste de l'albédo autour de sa moyenne, force de la normale, échelle de la tuile
# (béton de bordure : texture CC0 à granulats apparents, ramenée au grain fin d'un élément
# vibro-pressé : tuile x 0,35, contraste 0,45, normale 0,25 ; photos utilisateur 1 et 2)
FAMILLES = {
    "sol": {"macro": 0.14, "freq": 0.18, "sal": 0.45, "hex": True, "contraste": 1.0, "normale": 1.0, "tuile": 1.0},
    "bordure": {"macro": 0.05, "freq": 0.35, "sal": 0.55, "hex": True, "contraste": 0.45, "normale": 0.25, "tuile": 0.35,
                "pied_bas_m": -0.01, "pied_haut_m": 0.06},
    "remplissage": {"macro": 0.14, "freq": 0.5, "sal": 0.0, "hex": True, "contraste": 1.0, "normale": 1.0, "tuile": 1.0},
    "bev": {"macro": 0.06, "freq": 0.3, "sal": 0.3, "hex": False, "contraste": 1.0, "normale": 1.0, "tuile": 1.0},
    "eclat": {"macro": 0.10, "freq": 0.6, "sal": 0.0, "hex": False, "contraste": 1.0, "normale": 0.6, "tuile": 1.0},
}


def familles(specs):
    """FAMILLES mises à jour par materiaux_rendu_v2.json (familles.<nom>, clés numériques et booléennes)."""
    out = {k: dict(v) for k, v in FAMILLES.items()}
    for nom, reg in (specs.rendu.get("familles") or {}).items():
        out.setdefault(nom, dict(FAMILLES["sol"]))
        out[nom].update({k: v for k, v in reg.items() if isinstance(v, (int, float, bool))})
    return out

# matériaux maison sans texture (couleur linéaire, rugosité)
CONSTANTS = {
    "mortier_joint": {"couleur": (0.055, 0.055, 0.052), "rugosite": 0.95,
                      "description": "fond de joint de bordure (mortier sombre en retrait de 4 mm)"},
    "mortier_clair": {"couleur": (0.27, 0.265, 0.25), "rugosite": 0.92,
                      "description": "joint de bordure ancienne au mortier clair, à fleur (photo utilisateur 1)"},
    "bitume_pontage": {"couleur": (0.030, 0.029, 0.027), "rugosite": 0.86,
                       "description": "pontage de fissures et joint de reprise au bitume (bande de 4 à 8 cm, mate)"},
    "herbe_touffe": {"couleur": (0.060, 0.082, 0.030), "rugosite": 0.6, "couleur_instance": True,
                     "description": "touffes d'herbe 3D (joints de bordures anciennes, limites de gazon) ; gain RVB par "
                                    "instance (primvar couleur) : vert terne d'octobre à jaune sec"},
}
PEINTURES = {
    "peinture_blanche": {"couleur": (0.74, 0.74, 0.72), "rugosite": 0.65, "usure_seuil": 0.26,
                         "description": "peinture routière blanche (zébras) : macrotexture de l'enrobé à travers le film, "
                                        "usure qui fait réapparaître l'enrobé"},
}


def ue_chemin(mid):
    return f"/Game/PJ/Materials/MI_{mid}.MI_{mid}"


class _Graphe:
    """Petit constructeur de réseau MaterialX dans un Material USD."""

    def __init__(self, st, mat_path):
        self.st, self.base, self.n = st, mat_path, 0

    def noeud(self, nom, idn, entrees, sortie_type):
        sh = UsdShade.Shader.Define(self.st, f"{self.base}/{nom}")
        sh.CreateIdAttr(idn)
        for k, (typ, val) in entrees.items():
            inp = sh.CreateInput(k, typ)
            if isinstance(val, UsdShade.Output):
                inp.ConnectToSource(val)
            else:
                inp.Set(val)
        return sh.CreateOutput("out", sortie_type)


def _texture(lib, nom, suffixe, depuis):
    f = K.LIB_MAT / lib / "textures" / f"{lib}_{suffixe}"
    if not f.exists():
        raise FileNotFoundError(f)
    return Sdf.AssetPath(U.chemin_relatif(f, depuis))


def materiau_mtlx(st, mid, spec, famille, depuis, fams=None):
    """Réseau MaterialX + UsdPreviewSurface d'un materiau_id texturé."""
    fam = (fams or FAMILLES)[famille]
    lib = spec["source_cc0"]["nom"]
    tile = float(spec["tile_m"]) * fam["tuile"]
    fa = spec.get("facteur_albedo") or [1.0, 1.0, 1.0]
    moy = (spec.get("texture_mesuree") or {}).get("albedo_moyen_lineaire") or [0.3, 0.3, 0.3]
    rug_cible = float((spec.get("rugosite") or {}).get("valeur", 0.8))
    rug_tex = float((spec.get("texture_mesuree") or {}).get("rugosite_moyenne", rug_cible))
    gain_rug = rug_cible / max(rug_tex, 0.05)
    path = f"{LOOKS}/{mid}"
    m = UsdShade.Material.Define(st, path)
    m.GetPrim().SetCustomDataByKey("materiau_id", mid)
    m.GetPrim().SetCustomDataByKey("ue_materiau", ue_chemin(mid).split(".")[0])
    m.GetPrim().SetCustomDataByKey("source_cc0", f"{lib} ({spec['source_cc0'].get('origine', '')})")
    m.GetPrim().SetCustomDataByKey("tile_m", tile)
    g = _Graphe(st, path)
    pos = g.noeud("position", "ND_position_vector3", {"space": (T.String, "world")}, T.Float3)
    uv = g.noeud("uv", "ND_geompropvalue_vector2", {"geomprop": (T.String, "st1")}, T.Float2)
    dec = g.noeud("uv_decalage", "ND_geompropvalue_vector2",
                  {"geomprop": (T.String, "uv_decalage"), "default": (T.Float2, Gf.Vec2f(0, 0))}, T.Float2)
    uv2 = g.noeud("uv_plus", "ND_add_vector2", {"in1": (T.Float2, uv), "in2": (T.Float2, dec)}, T.Float2)
    uvs = g.noeud("uv_tuile", "ND_multiply_vector2FA", {"in1": (T.Float2, uv2), "in2": (T.Float, 1.0 / tile)}, T.Float2)

    def image(nom, suffixe, typ="color3"):
        if fam["hex"]:
            ent = {"file": (T.Asset, _texture(lib, mid, suffixe, depuis)), "texcoord": (T.Float2, uvs),
                   "rotationrange": (T.Float2, Gf.Vec2f(0, 360)), "scalerange": (T.Float2, Gf.Vec2f(0.85, 1.15)),
                   "falloff": (T.Float, float(fam.get("falloff", 0.35)))}
            if typ == "normal":
                ent["strength"] = (T.Float, fam["normale"])
                return g.noeud(nom, "ND_hextilednormalmap_vector3", ent, T.Float3)
            o = g.noeud(nom, "ND_hextiledimage_color3", ent, T.Color3f)
            if typ == "float":
                return g.noeud(nom + "_r", "ND_extract_color3", {"in": (T.Color3f, o), "index": (T.Int, 0)}, T.Float)
            return o
        ent = {"file": (T.Asset, _texture(lib, mid, suffixe, depuis)), "texcoord": (T.Float2, uvs)}
        if typ == "normal":
            n = g.noeud(nom + "_img", "ND_image_vector3", ent, T.Float3)
            return g.noeud(nom, "ND_normalmap_float", {"in": (T.Float3, n), "scale": (T.Float, fam["normale"])}, T.Float3)
        if typ == "float":
            return g.noeud(nom, "ND_image_float", ent, T.Float)
        return g.noeud(nom, "ND_image_color3", ent, T.Color3f)

    alb = image("albedo", "albedo.jpg")
    if abs(fam["contraste"] - 1.0) > 1e-6:          # < 1 : adouci ; > 1 : extrapolé autour de la moyenne
        alb = g.noeud("albedo_contraste", "ND_mix_color3", {"fg": (T.Color3f, alb), "bg": (T.Color3f, Gf.Vec3f(*map(float, moy))),
                                                             "mix": (T.Float, fam["contraste"])}, T.Color3f)
        if fam["contraste"] > 1.0:
            alb = g.noeud("albedo_positif", "ND_max_color3FA", {"in1": (T.Color3f, alb), "in2": (T.Float, 0.004)}, T.Color3f)
    alb = g.noeud("albedo_gain", "ND_multiply_color3", {"in1": (T.Color3f, alb),
                                                         "in2": (T.Color3f, Gf.Vec3f(*map(float, fa)))}, T.Color3f)
    part_ao = 1.0 if fam.get("ao_plein") else float(fam.get("ao", 0.5))
    if part_ao > 0 and (K.LIB_MAT / lib / "textures" / f"{lib}_ao.jpg").exists():   # AO facultative
        ao = image("ao", "ao.jpg", "float")
        ao = g.noeud("ao_doux", "ND_mix_float", {"fg": (T.Float, ao), "bg": (T.Float, 1.0),
                                                 "mix": (T.Float, part_ao)}, T.Float)
        alb = g.noeud("albedo_ao", "ND_multiply_color3FA", {"in1": (T.Color3f, alb), "in2": (T.Float, ao)}, T.Color3f)
    # variation macro (monde)
    posf = g.noeud("position_freq", "ND_multiply_vector3FA", {"in1": (T.Float3, pos), "in2": (T.Float, fam["freq"])}, T.Float3)
    fr = g.noeud("macro", "ND_fractal3d_float", {"position": (T.Float3, posf), "octaves": (T.Int, 3)}, T.Float)
    a = fam["macro"]
    rm = g.noeud("macro_gain", "ND_remap_float", {"in": (T.Float, fr), "inlow": (T.Float, -0.5), "inhigh": (T.Float, 0.5),
                                                  "outlow": (T.Float, 1.0 - a), "outhigh": (T.Float, 1.0 + a)}, T.Float)
    alb = g.noeud("albedo_macro", "ND_multiply_color3FA", {"in1": (T.Color3f, alb), "in2": (T.Float, rm)}, T.Color3f)
    # teinte par instance, couleur par instance
    te = g.noeud("teinte", "ND_geompropvalue_float", {"geomprop": (T.String, "teinte"), "default": (T.Float, 1.0)}, T.Float)
    alb = g.noeud("albedo_teinte", "ND_multiply_color3FA", {"in1": (T.Color3f, alb), "in2": (T.Float, te)}, T.Color3f)
    co = g.noeud("couleur", "ND_geompropvalue_color3", {"geomprop": (T.String, "couleur"),
                                                         "default": (T.Color3f, Gf.Vec3f(1, 1, 1))}, T.Color3f)
    alb = g.noeud("albedo_couleur", "ND_multiply_color3", {"in1": (T.Color3f, alb), "in2": (T.Color3f, co)}, T.Color3f)
    # salissure
    sal = g.noeud("salissure", "ND_geompropvalue_float", {"geomprop": (T.String, "salissure"), "default": (T.Float, 0.0)}, T.Float)
    if famille == "bordure":
        po = g.noeud("position_objet", "ND_position_vector3", {"space": (T.String, "object")}, T.Float3)
        zo = g.noeud("z_objet", "ND_extract_vector3", {"in": (T.Float3, po), "index": (T.Int, 2)}, T.Float)
        zp = g.noeud("z_pied", "ND_geompropvalue_float", {"geomprop": (T.String, "z_pied"), "default": (T.Float, -10.0)}, T.Float)
        dz = g.noeud("dz_pied", "ND_subtract_float", {"in1": (T.Float, zo), "in2": (T.Float, zp)}, T.Float)
        pied = g.noeud("masque_pied", "ND_smoothstep_float", {"in": (T.Float, dz), "low": (T.Float, fam["pied_bas_m"]),
                                                              "high": (T.Float, fam["pied_haut_m"])}, T.Float)
        pied = g.noeud("masque_pied_inv", "ND_subtract_float", {"in1": (T.Float, 1.0), "in2": (T.Float, pied)}, T.Float)
        # liseré irrégulier le long de la file (bruit fractal monde, ~3 /m)
        pf = g.noeud("pied_freq", "ND_multiply_vector3FA", {"in1": (T.Float3, pos), "in2": (T.Float, 3.0)}, T.Float3)
        bn = g.noeud("pied_bruit", "ND_fractal3d_float", {"position": (T.Float3, pf), "octaves": (T.Int, 3)}, T.Float)
        bn = g.noeud("pied_bruit_gain", "ND_remap_float", {"in": (T.Float, bn), "inlow": (T.Float, -0.5), "inhigh": (T.Float, 0.5),
                                                           "outlow": (T.Float, 0.45), "outhigh": (T.Float, 1.25)}, T.Float)
        pied = g.noeud("masque_pied_bruite", "ND_multiply_float", {"in1": (T.Float, pied), "in2": (T.Float, bn)}, T.Float)
        sal = g.noeud("salissure_pied", "ND_multiply_float", {"in1": (T.Float, sal), "in2": (T.Float, pied)}, T.Float)
    sg = g.noeud("salissure_gain", "ND_multiply_float", {"in1": (T.Float, sal), "in2": (T.Float, -fam["sal"])}, T.Float)
    sg = g.noeud("salissure_fact", "ND_add_float", {"in1": (T.Float, sg), "in2": (T.Float, 1.0)}, T.Float)
    alb = g.noeud("albedo_final", "ND_multiply_color3FA", {"in1": (T.Color3f, alb), "in2": (T.Float, sg)}, T.Color3f)
    if famille == "bordure":
        alb = _bordure_details(g, alb, pos, fam)
    rug = image("rugosite", "rugosite.jpg", "float")
    rug = g.noeud("rugosite_gain", "ND_multiply_float", {"in1": (T.Float, rug), "in2": (T.Float, gain_rug)}, T.Float)
    rug = g.noeud("rugosite_borne", "ND_clamp_float", {"in": (T.Float, rug), "low": (T.Float, float(fam.get("rugosite_min", 0.05))),
                                                       "high": (T.Float, 1.0)}, T.Float)
    ent = {"base": (T.Float, 1.0), "base_color": (T.Color3f, alb), "specular": (T.Float, 0.5),
           "specular_roughness": (T.Float, rug)}
    # normale de texture : omise sous 0,05 (Karma XPU n'applique pas `strength` de ND_hextilednormalmap : à
    # 0,02 comme à 0,08, la normale à granulats de Concrete037 donnait le même crépi ; revue réalisme r2)
    if fam["normale"] >= 0.05:
        ent["normal"] = (T.Float3, image("normale", "normale.png", "normal"))
    ss = g.noeud("surface", "ND_standard_surface_surfaceshader", ent, T.Token)
    m.CreateSurfaceOutput("mtlx").ConnectToSource(ss)
    _preview(st, path, m, lib, tile, fa, rug_cible, depuis)
    return m



def _bordure_details(g, alb, pos, fam):
    """Béton de bordure (revue réalisme r2) : moucheté d'agrégats fins (cellnoise monde à ~700 /m : 5 % de
    grains x 0,6, 4 % x 1,15 ; béton vibro-pressé lisse des photos 2 et 3) et vieillissement piloté par
    l'aspect décrit (primvars d'instance) : assombrissement global (1 − 0,3·salissure), crasse en dégradé
    sur la face vue (du fil d'eau à 12 cm au-dessus), lichens sur la tête (worley 150 /m, couverture ∝
    salissure), mousse aux abouts (|x objet| > demi_longueur − 15 mm, x mousse_joints)."""
    T_ = T
    pf = g.noeud("mouch_pos", "ND_multiply_vector3FA", {"in1": (T_.Float3, pos), "in2": (T_.Float, fam.get("mouch_freq", 700.0))}, T_.Float3)
    cn = g.noeud("mouch_cell", "ND_cellnoise3d_float", {"position": (T_.Float3, pf)}, T_.Float)
    gs = g.noeud("mouch_sombre", "ND_ifgreater_float", {"value1": (T_.Float, fam.get("mouch_sombre_part", 0.05)), "value2": (T_.Float, cn),
                                                         "in1": (T_.Float, fam.get("mouch_sombre_gain", 0.6)), "in2": (T_.Float, 1.0)}, T_.Float)
    gc = g.noeud("mouch_clair", "ND_ifgreater_float", {"value1": (T_.Float, cn), "value2": (T_.Float, 1.0 - fam.get("mouch_clair_part", 0.04)),
                                                        "in1": (T_.Float, fam.get("mouch_clair_gain", 1.15)), "in2": (T_.Float, 1.0)}, T_.Float)
    gm = g.noeud("mouch_gain", "ND_multiply_float", {"in1": (T_.Float, gs), "in2": (T_.Float, gc)}, T_.Float)
    alb = g.noeud("albedo_moucheture", "ND_multiply_color3FA", {"in1": (T_.Color3f, alb), "in2": (T_.Float, gm)}, T_.Color3f)
    sal = g.noeud("vieil_sal", "ND_geompropvalue_float", {"geomprop": (T_.String, "salissure"), "default": (T_.Float, 0.0)}, T_.Float)
    # assombrissement global
    ga = g.noeud("vieil_gain", "ND_remap_float", {"in": (T_.Float, sal), "inlow": (T_.Float, 0.0), "inhigh": (T_.Float, 1.0),
                                                  "outlow": (T_.Float, 1.0), "outhigh": (T_.Float, 1.0 - fam.get("vieil_assombri", 0.3))}, T_.Float)
    alb = g.noeud("albedo_vieil", "ND_multiply_color3FA", {"in1": (T_.Color3f, alb), "in2": (T_.Float, ga)}, T_.Color3f)
    # crasse en dégradé sur la face (hauteur au-dessus du fil d'eau, repère de l'élément)
    po = g.noeud("vieil_pos_objet", "ND_position_vector3", {"space": (T_.String, "object")}, T_.Float3)
    zo = g.noeud("vieil_z_objet", "ND_extract_vector3", {"in": (T_.Float3, po), "index": (T_.Int, 2)}, T_.Float)
    zp = g.noeud("vieil_z_pied", "ND_geompropvalue_float", {"geomprop": (T_.String, "z_pied"), "default": (T_.Float, -10.0)}, T_.Float)
    dz = g.noeud("vieil_dz", "ND_subtract_float", {"in1": (T_.Float, zo), "in2": (T_.Float, zp)}, T_.Float)
    hc = g.noeud("crasse_haut", "ND_smoothstep_float", {"in": (T_.Float, dz), "low": (T_.Float, 0.0),
                                                        "high": (T_.Float, fam.get("crasse_face_m", 0.12))}, T_.Float)
    hc = g.noeud("crasse_bas", "ND_subtract_float", {"in1": (T_.Float, 1.0), "in2": (T_.Float, hc)}, T_.Float)
    cr = g.noeud("crasse_force", "ND_multiply_float", {"in1": (T_.Float, hc), "in2": (T_.Float, sal)}, T_.Float)
    cr = g.noeud("crasse_gain", "ND_remap_float", {"in": (T_.Float, cr), "inlow": (T_.Float, 0.0), "inhigh": (T_.Float, 1.0),
                                                   "outlow": (T_.Float, 1.0), "outhigh": (T_.Float, 1.0 - fam.get("crasse_face", 0.25))}, T_.Float)
    alb = g.noeud("albedo_crasse", "ND_multiply_color3FA", {"in1": (T_.Color3f, alb), "in2": (T_.Float, cr)}, T_.Color3f)
    # lichens sur la tête (normale monde vers le haut)
    pl = g.noeud("lichen_pos", "ND_multiply_vector3FA", {"in1": (T_.Float3, pos), "in2": (T_.Float, fam.get("lichen_freq", 150.0))}, T_.Float3)
    wl = g.noeud("lichen_worley", "ND_worleynoise3d_float", {"position": (T_.Float3, pl), "jitter": (T_.Float, 1.0)}, T_.Float)
    rl = g.noeud("lichen_aire", "ND_multiply_float", {"in1": (T_.Float, sal), "in2": (T_.Float, fam.get("lichen_couverture", 0.12) / 3.1416)}, T_.Float)
    rl = g.noeud("lichen_rayon", "ND_sqrt_float", {"in": (T_.Float, rl)}, T_.Float)
    rl0 = g.noeud("lichen_rayon_int", "ND_multiply_float", {"in1": (T_.Float, rl), "in2": (T_.Float, 0.6)}, T_.Float)
    ml = g.noeud("lichen_tache", "ND_smoothstep_float", {"in": (T_.Float, wl), "low": (T_.Float, rl0), "high": (T_.Float, rl)}, T_.Float)
    ml = g.noeud("lichen_masque", "ND_subtract_float", {"in1": (T_.Float, 1.0), "in2": (T_.Float, ml)}, T_.Float)
    nw = g.noeud("lichen_normale", "ND_normal_vector3", {"space": (T_.String, "world")}, T_.Float3)
    nz = g.noeud("lichen_nz", "ND_extract_vector3", {"in": (T_.Float3, nw), "index": (T_.Int, 2)}, T_.Float)
    ht = g.noeud("lichen_tete", "ND_smoothstep_float", {"in": (T_.Float, nz), "low": (T_.Float, 0.6), "high": (T_.Float, 0.9)}, T_.Float)
    ml = g.noeud("lichen_masque_tete", "ND_multiply_float", {"in1": (T_.Float, ml), "in2": (T_.Float, ht)}, T_.Float)
    ml = g.noeud("lichen_mix", "ND_multiply_float", {"in1": (T_.Float, ml), "in2": (T_.Float, 0.85)}, T_.Float)
    alb = g.noeud("albedo_lichen", "ND_mix_color3", {"fg": (T_.Color3f, Gf.Vec3f(0.12, 0.12, 0.10)), "bg": (T_.Color3f, alb),
                                                     "mix": (T_.Float, ml)}, T_.Color3f)
    # mousse aux abouts (joints)
    xo = g.noeud("mousse_x", "ND_extract_vector3", {"in": (T_.Float3, po), "index": (T_.Int, 0)}, T_.Float)
    xa = g.noeud("mousse_absx", "ND_absval_float", {"in": (T_.Float, xo)}, T_.Float)
    dl = g.noeud("mousse_demi", "ND_geompropvalue_float", {"geomprop": (T_.String, "demi_longueur"), "default": (T_.Float, 100.0)}, T_.Float)
    dl0 = g.noeud("mousse_demi_int", "ND_subtract_float", {"in1": (T_.Float, dl), "in2": (T_.Float, fam.get("mousse_joint_m", 0.015))}, T_.Float)
    mm = g.noeud("mousse_bout", "ND_smoothstep_float", {"in": (T_.Float, xa), "low": (T_.Float, dl0), "high": (T_.Float, dl)}, T_.Float)
    mj = g.noeud("mousse_joints", "ND_geompropvalue_float", {"geomprop": (T_.String, "mousse_joints"), "default": (T_.Float, 0.0)}, T_.Float)
    pm = g.noeud("mousse_pos", "ND_multiply_vector3FA", {"in1": (T_.Float3, pos), "in2": (T_.Float, 40.0)}, T_.Float3)
    fm = g.noeud("mousse_bruit", "ND_fractal3d_float", {"position": (T_.Float3, pm), "octaves": (T_.Int, 3)}, T_.Float)
    fm = g.noeud("mousse_bruit_gain", "ND_remap_float", {"in": (T_.Float, fm), "inlow": (T_.Float, -0.5), "inhigh": (T_.Float, 0.5),
                                                         "outlow": (T_.Float, 0.0), "outhigh": (T_.Float, 2.4)}, T_.Float)
    mm = g.noeud("mousse_force", "ND_multiply_float", {"in1": (T_.Float, mm), "in2": (T_.Float, mj)}, T_.Float)
    mm = g.noeud("mousse_force_b", "ND_multiply_float", {"in1": (T_.Float, mm), "in2": (T_.Float, fm)}, T_.Float)
    mm = g.noeud("mousse_masque", "ND_clamp_float", {"in": (T_.Float, mm), "low": (T_.Float, 0.0), "high": (T_.Float, 0.9)}, T_.Float)
    return g.noeud("albedo_mousse", "ND_mix_color3", {"fg": (T_.Color3f, Gf.Vec3f(0.05, 0.07, 0.03)), "bg": (T_.Color3f, alb),
                                                      "mix": (T_.Float, mm)}, T_.Color3f)

def _preview(st, path, m, lib, tile, fa, rug, depuis):
    """Réseau UsdPreviewSurface (contexte universel)."""
    def sh(nom, idn):
        s = UsdShade.Shader.Define(st, f"{path}/ups_{nom}")
        s.CreateIdAttr(idn)
        return s
    lec = sh("st", "UsdPrimvarReader_float2")
    lec.CreateInput("varname", T.String).Set("st1")
    o = lec.CreateOutput("result", T.Float2)
    ech = sh("echelle", "UsdTransform2d")
    ech.CreateInput("in", T.Float2).ConnectToSource(o)
    ech.CreateInput("scale", T.Float2).Set(Gf.Vec2f(1.0 / tile, 1.0 / tile))
    oe = ech.CreateOutput("result", T.Float2)

    def tex(nom, suffixe, cs, sortie, typ):
        t = sh(nom, "UsdUVTexture")
        t.CreateInput("file", T.Asset).Set(_texture(lib, None, suffixe, depuis))
        t.CreateInput("sourceColorSpace", T.Token).Set(cs)
        t.CreateInput("wrapS", T.Token).Set("repeat")
        t.CreateInput("wrapT", T.Token).Set("repeat")
        t.CreateInput("st", T.Float2).ConnectToSource(oe)
        return t, t.CreateOutput(sortie, typ)
    ta, oa = tex("albedo", "albedo.jpg", "sRGB", "rgb", T.Float3)
    ta.CreateInput("scale", T.Float4).Set(Gf.Vec4f(float(fa[0]), float(fa[1]), float(fa[2]), 1.0))
    _, orr = tex("rugosite", "rugosite.jpg", "raw", "r", T.Float)
    tn, on = tex("normale", "normale.png", "raw", "rgb", T.Float3)
    tn.CreateInput("scale", T.Float4).Set(Gf.Vec4f(2, 2, 2, 1))
    tn.CreateInput("bias", T.Float4).Set(Gf.Vec4f(-1, -1, -1, 0))
    s = sh("surface", "UsdPreviewSurface")
    s.CreateInput("diffuseColor", T.Color3f).ConnectToSource(oa)
    s.CreateInput("roughness", T.Float).ConnectToSource(orr)
    s.CreateInput("normal", T.Normal3f).ConnectToSource(on)
    s.CreateInput("metallic", T.Float).Set(0.0)
    m.CreateSurfaceOutput().ConnectToSource(s.CreateOutput("surface", T.Token))


def materiau_constant(st, mid, c):
    path = f"{LOOKS}/{mid}"
    m = UsdShade.Material.Define(st, path)
    m.GetPrim().SetCustomDataByKey("materiau_id", mid)
    m.GetPrim().SetCustomDataByKey("description", c["description"])
    g = _Graphe(st, path)
    base = Gf.Vec3f(*c["couleur"])
    if c.get("couleur_instance"):
        co = g.noeud("couleur", "ND_geompropvalue_color3", {"geomprop": (T.String, "couleur"),
                                                             "default": (T.Color3f, Gf.Vec3f(1, 1, 1))}, T.Color3f)
        base = g.noeud("albedo", "ND_multiply_color3", {"in1": (T.Color3f, base), "in2": (T.Color3f, co)}, T.Color3f)
    ss = g.noeud("surface", "ND_standard_surface_surfaceshader", {
        "base": (T.Float, 1.0), "base_color": (T.Color3f, base),
        "specular_roughness": (T.Float, c["rugosite"])}, T.Token)
    m.CreateSurfaceOutput("mtlx").ConnectToSource(ss)
    s = UsdShade.Shader.Define(st, f"{path}/ups_surface")
    s.CreateIdAttr("UsdPreviewSurface")
    s.CreateInput("diffuseColor", T.Color3f).Set(Gf.Vec3f(*c["couleur"]))
    s.CreateInput("roughness", T.Float).Set(c["rugosite"])
    m.CreateSurfaceOutput().ConnectToSource(s.CreateOutput("surface", T.Token))
    return m


def materiau_peinture(st, mid, c, depuis=None, specs=None):
    """Peinture routière (revue réalisme r2 : zébras en autocollant vinyle) : la macrotexture de l'enrobé
    support se lit à travers le film (normale de l'enrobé neuf en tuilage hexagonal sur st1 en mètres,
    force 0,8) ; l'usure fait réapparaître l'enrobé (mélange vers son albédo ≈ 0,12, masque = têtes de
    granulats ~200 /m + passage des roues ~2 /m, couverture visée 6-8 % pour un zébra de 2025) ;
    rugosité 0,65."""
    path = f"{LOOKS}/{mid}"
    m = UsdShade.Material.Define(st, path)
    m.GetPrim().SetCustomDataByKey("materiau_id", mid)
    m.GetPrim().SetCustomDataByKey("description", c["description"])
    g = _Graphe(st, path)
    pos = g.noeud("position", "ND_position_vector3", {"space": (T.String, "world")}, T.Float3)
    pf = g.noeud("usure_freq", "ND_multiply_vector3FA", {"in1": (T.Float3, pos), "in2": (T.Float, 200.0)}, T.Float3)
    fr = g.noeud("usure_bruit", "ND_fractal3d_float", {"position": (T.Float3, pf), "octaves": (T.Int, 2)}, T.Float)
    pr = g.noeud("usure_roues_freq", "ND_multiply_vector3FA", {"in1": (T.Float3, pos), "in2": (T.Float, 2.0)}, T.Float3)
    fw = g.noeud("usure_roues", "ND_fractal3d_float", {"position": (T.Float3, pr), "octaves": (T.Int, 2)}, T.Float)
    fw = g.noeud("usure_roues_gain", "ND_remap_float", {"in": (T.Float, fw), "inlow": (T.Float, -0.4), "inhigh": (T.Float, 0.4),
                                                        "outlow": (T.Float, -0.12), "outhigh": (T.Float, 0.12)}, T.Float)
    fr = g.noeud("usure_somme", "ND_add_float", {"in1": (T.Float, fr), "in2": (T.Float, fw)}, T.Float)
    us = g.noeud("usure", "ND_smoothstep_float", {"in": (T.Float, fr), "low": (T.Float, c.get("usure_seuil", 0.26)),
                                                  "high": (T.Float, c.get("usure_seuil", 0.26) + 0.08)}, T.Float)
    alb = g.noeud("albedo", "ND_mix_color3", {"fg": (T.Color3f, Gf.Vec3f(0.12, 0.12, 0.115)), "bg": (T.Color3f, Gf.Vec3f(*c["couleur"])),
                                              "mix": (T.Float, us)}, T.Color3f)
    ent = {"base": (T.Float, 1.0), "base_color": (T.Color3f, alb), "specular_roughness": (T.Float, c["rugosite"])}
    if depuis is not None and specs is not None:
        sp = specs.materiau_rendu("enrobe_bbsg_neuf_2025")
        lib = sp["source_cc0"]["nom"]
        uv = g.noeud("uv", "ND_geompropvalue_vector2", {"geomprop": (T.String, "st1")}, T.Float2)
        uvs = g.noeud("uv_tuile", "ND_multiply_vector2FA", {"in1": (T.Float2, uv), "in2": (T.Float, 1.0 / float(sp["tile_m"]))}, T.Float2)
        nrm = g.noeud("normale_enrobe", "ND_hextilednormalmap_vector3", {
            "file": (T.Asset, _texture(lib, mid, "normale.png", depuis)), "texcoord": (T.Float2, uvs),
            "rotationrange": (T.Float2, Gf.Vec2f(0, 360)), "scalerange": (T.Float2, Gf.Vec2f(0.85, 1.15)),
            "falloff": (T.Float, 0.12), "strength": (T.Float, 0.8)}, T.Float3)
        ent["normal"] = (T.Float3, nrm)
    ss = g.noeud("surface", "ND_standard_surface_surfaceshader", ent, T.Token)
    m.CreateSurfaceOutput("mtlx").ConnectToSource(ss)
    s = UsdShade.Shader.Define(st, f"{path}/ups_surface")
    s.CreateIdAttr("UsdPreviewSurface")
    s.CreateInput("diffuseColor", T.Color3f).Set(Gf.Vec3f(*c["couleur"]))
    s.CreateInput("roughness", T.Float).Set(c["rugosite"])
    m.CreateSurfaceOutput().ConnectToSource(s.CreateOutput("surface", T.Token))
    return m


def famille_de(mid, spec=None):
    if spec and spec.get("famille_rendu"):
        return spec["famille_rendu"]
    if mid.startswith("beton_bordure") or mid in ("caniveau_beton", "granit_bordure", "calcaire_bordure"):
        return "bordure"
    if mid == "bev_podotactile":
        return "bev"
    if mid.startswith("eclat_"):
        return "eclat"
    return "sol"


def ecrire(specs, ids, chemin, eclats=None, ref=None):
    """materiaux_v2.usda : matériaux des ids demandés (triés) ; eclats = {id_eclat: materiau_source} ;
    ref : emplacement de référence des chemins de textures relatifs (défaut : chemin)."""
    chemin = Path(chemin)
    depuis = Path(ref) if ref else chemin
    st = U.scene("Matériaux v2 Paquet Jardin (pj_materiaux.py) : MaterialX (Karma) + UsdPreviewSurface, "
                 "textures CC0 de assets/lib/materiaux, UV st1 en mètres.",
                 data={"source": "assets/specs/materiaux_sol.json", "version": K.VERSION})
    U.scope(st, LOOKS)
    fams = familles(specs)
    faits = []
    for mid in sorted(ids):
        if mid in CONSTANTS:
            materiau_constant(st, mid, CONSTANTS[mid])
        elif mid in PEINTURES:
            materiau_peinture(st, mid, PEINTURES[mid], depuis, specs)
        else:
            sp = specs.materiau_rendu(mid)
            materiau_mtlx(st, mid, sp, famille_de(mid, sp), depuis, fams)
        faits.append(mid)
    for eid, src in sorted((eclats or {}).items()):
        materiau_mtlx(st, eid, specs.materiau(src), "eclat", depuis, fams)
        faits.append(eid)
    U.enregistrer(st, chemin)
    return faits
