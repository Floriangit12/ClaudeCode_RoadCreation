"""pj_rendu : caméras de contrôle de la zone pilote et scène racine Karma.

- recon/pc/houdini/cameras_v2_pilote.usda : 6 caméras /World/Cameras_v2/<vue>, placées depuis la
  géométrie de la description (bordure + abscisse, îlot), au style des photos de référence de
  l'utilisateur (vue piéton le long d'une file, abaissé de traversée et BEV, entrée charretière sur
  trottoir en enrobé, îlot BRF et sa ceinture, îlot gravillonné, vue d'ensemble à 14 m) ;
- fabrique/rendu_pilote.usda : racine = caméras v2 + couches fabriquées + masque v1 + décor de rendu +
  scène de contrôle v1 (recon/pc/houdini/rendu_controle.usda : paquet v1, réglages Karma) ; surcharges
  de lumière (revue réalisme r1 : éclairage plat, ciel uniforme) :
  - ciel : dôme texturé par un ciel clair procédural (fabrique/ciel/ciel_clair.hdr, latlong, horizon
    clair, zénith bleu, brume claire sous l'horizon ; aucune image téléchargée), luminance calibrée pour
    un rapport d'éclairement horizontal soleil / ciel de 3,5:1 ;
  - soleil : azimut 220°, hauteur 29° (10 octobre, 45,2° N), exposition 2,0 ; balance des blancs calculée
    sur une carte grise horizontale (gains_balance) ;
  - échantillons : 128 chemins par pixel (le rendu se fait à 2 x la résolution, rendre_pilote.py) ;
- fabrique/contexte/decor_rendu.usda : arbres v1 (boules) masqués (invisibleIds) pour les rendus de
  contrôle (le regard reste sur le sol v2 ; végétation v2 en phase 4) ; bâtiments v1 sur un enduit CC0
  d'albédo 0,47 légèrement chaud, toits et espaces verts v1 sur des matériaux CC0 (projection
  triplanaire) ; le paquet v1 n'est pas modifié ;
- objectif : focale et ouverture en dixièmes d'unité (convention USD, 0,36 = 36 mm), profondeur de
  champ légère (f/8) sur les vues rapprochées.
Rendu : hython recon/pcg/houdini/rendre_pilote.py (husk Karma XPU en EXR, exposition par vue, courbe
d'épaule douce, PNG sRGB 1000 x 1000 dans recon/pc/rendus/v2_pilote).
"""
import math
from pathlib import Path

import numpy as np

import pj_commun as K
import pj_usd as U
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

C = K.C
# objectif en dixièmes d'unité de scène (convention USD : ici des décimètres, 0,36 = 36 mm) : le champ ne
# dépend que du rapport focale / ouverture, mais la profondeur de champ de Karma utilise les tailles réelles
APERTURE = 0.36
# 10 octobre, 45,21° N (déclinaison ≈ −6,8°) : à l'azimut 220°, le soleil est à ≈ 29° (revue réalisme r2 :
# 38° n'est atteint qu'au midi solaire, ombres 28 % trop courtes)
SOLEIL = {"azimut_deg": 220.0, "hauteur_deg": 29.0, "exposition": 2.0}
SOLEIL_COULEUR = (1.0, 0.95, 0.88)     # recon/pc/houdini/rendu_controle.usda (soleil), inchangée
CIEL_ZENITH = (0.30, 0.42, 0.70)       # revue réalisme r2 : zénith (0,22 ; 0,38 ; 0,78) trop saturé, reflets bleus
CIEL_HORIZON = (0.80, 0.86, 0.95)
# balance des blancs (rendre_pilote.py) : une carte grise horizontale au soleil et sous le ciel ressort
# légèrement chaude, comme les photos de référence (B/R linéaire 0,86-0,91 sur les photos 2 et 3)
BLANC_CIBLE = (1.0, 1.0, 0.94)
RAPPORT_SOLEIL_CIEL = 3.5          # éclairement horizontal soleil / ciel (ciel clair voilé, mi-octobre)
DECOR_MAX_M = -1.0                 # arbres v1 (boules) masqués dans les rendus de contrôle (< 0 : tous)

# (nom, réglage) : le long d'une bordure, face à un abaissé, autour d'un îlot, libre
# ev : correction d'exposition de la vue (rendre_pilote.py) ; f : ouverture (0 = sans profondeur de champ)
VUES = [
    ("a_pieton_file_joints", {"type": "le_long", "bordure": "K-0369", "s": 1.2, "s_cible": 5.5, "recul": 0.55,
                              "h": 1.6, "hfov": 50, "f": 8.0, "ev": 0.0,
                              "doc": "piéton (œil 1,60 m) sur la chaussée contre une file de T2 de 1 m (K-0369), regard plongeant le long de la file : joints, arrondi d'arête, massifs BRF derrière (photo utilisateur 2)"}),
    ("b_abaisse_traversee_bev", {"type": "face", "bordure": "K-0385", "s": 5.15, "recul": 3.0, "h": 1.6, "hfov": 50,
                                 "biais_deg": 20, "f": 8.0, "ev": 0.0, "tangage_deg": -5.0,
                                 "doc": "abaissé de la traversée NE (A-0385-1) : bateau T2 à 0,02 m, deux chartières de 1 m, BEV à 0,50 m du nez, zébra"}),
    ("c_entree_charretiere", {"type": "points", "oeil": (44.6, 68.4), "cible": (47.3, 65.9), "h": 1.6, "h_cible": 0.03,
                              "hfov": 55, "f": 8.0, "ev": 0.0,
                              "doc": "entrée charretière de l'accès riverain (S-0265) : bordures abaissées A2 / T2 bateau à 0,04 m (A-0177-1, A-0182-1) entre l'accès en enrobé et la piste (photo utilisateur 1)"}),
    ("d_ilot_brf", {"type": "ilot", "ilot": "I-0297", "azimut_deg": 250, "distance": 1.4, "h": 1.65, "hfov": 50,
                    "f": 8.0, "ev": 0.0,
                    "doc": "îlot en goutte de BRF (I-0297) et sa ceinture de bordures, regard plongeant (photo utilisateur 2)"}),
    ("e_ilot_gravier", {"type": "ilot", "ilot": "I-0390", "azimut_deg": 300, "distance": 1.3, "h": 1.65, "hfov": 50,
                        "f": 8.0, "ev": 0.0,
                        "doc": "îlot gravillonné du Vercors (I-0390, gravier concassé 6/10) dans sa ceinture T2, regard plongeant (photo utilisateur 3)"}),
    ("f_vue_ensemble", {"type": "libre", "cible": (14.0, 6.0), "azimut_deg": 210, "distance": 24.0, "h": 14.0,
                        "hfov": 64, "f": 0.0, "ev": 0.0,
                        "doc": "vue d'ensemble de la zone pilote depuis 14 m (traversée NE, TPC, îlots BRF et Vercors)"}),
]


def regard(oeil, cible):
    m = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*map(float, oeil)), Gf.Vec3d(*map(float, cible)), Gf.Vec3d(0, 0, 1))
    return m.GetInverse()


def focale(hfov):
    return APERTURE / (2 * math.tan(math.radians(hfov) / 2))


def placer(desc, sol, nom, v):
    """Œil et cible (repère local) d'une vue."""
    if v["type"] in ("le_long", "face"):
        b = sol.bandes[v["bordure"]]
        B = b.B
        s = v["s"]
        p, tg = B.point(s)
        p, tg = p[0], tg[0]
        n = np.array([-tg[1], tg[0]])
        zfe = float(B.z_fe(s))
        if v["type"] == "le_long":
            q, _ = B.point(v["s_cible"])
            oeil = np.r_[p - n * v["recul"], zfe + v["h"]]
            cible = np.r_[q[0] + n * 0.1, float(B.z_fe(v["s_cible"])) + 0.15]
        else:
            a = math.radians(v.get("biais_deg", 0))
            d = -n * math.cos(a) + tg * math.sin(a)
            oeil = np.r_[p + d * v["recul"], zfe + v["h"]]
            cible = np.r_[p + n * 0.3, zfe + 0.05]
        if v.get("tangage_deg"):            # regard abaissé (+ = relevé) autour de l'œil (revue réalisme r2)
            d = cible - oeil
            hz = math.hypot(d[0], d[1])
            a = math.atan2(d[2], hz) + math.radians(v["tangage_deg"])
            L_ = float(np.linalg.norm(d))
            cible = oeil + np.r_[d[:2] / hz * math.cos(a) * L_, math.sin(a) * L_]
    elif v["type"] == "ilot":
        # regard plongeant (photos utilisateur 2 et 3) : œil à `distance` du bord de l'îlot, cible 0,8 m à
        # l'intérieur du bord
        il = next(i for i in desc.ilots if i["id"] == v["ilot"])
        r = il["polys"][0][0]
        c = r.mean(axis=0)
        az = math.radians(v["azimut_deg"])
        d = np.array([math.sin(az), math.cos(az)])
        rayon = float(np.max((r - c) @ d))
        xy = c + d * (rayon + v["distance"])
        cxy = c + d * max(rayon - 0.8, 0.0)
        oeil = np.r_[xy, float(sol.z_points(xy[None])[0]) + v["h"]]
        cible = np.r_[cxy, float(sol.z_points(cxy[None])[0])]
    elif v["type"] == "points":
        o, c = np.array(v["oeil"], dtype=float), np.array(v["cible"], dtype=float)
        oeil = np.r_[o, float(sol.z_points(o[None])[0]) + v["h"]]
        cible = np.r_[c, float(sol.z_points(c[None])[0]) + v["h_cible"]]
    else:
        c = np.array(v["cible"])
        az = math.radians(v["azimut_deg"])
        xy = c + np.array([math.sin(az), math.cos(az)]) * v["distance"]
        zc = float(sol.z_points(c[None])[0])
        oeil = np.r_[xy, zc + v["h"]]
        cible = np.r_[c, zc]
    return oeil, cible


def ecrire_cameras(desc, sol, chemin):
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    st.GetRootLayer().documentation = (
        "Caméras de contrôle de la zone pilote v2 (recon/pcg/houdini/pj_rendu.py) : repère local "
        "(L93 − O, Z = NGF − 216,30), mètres, Z haut ; ouverture 36 x 36 mm, notée 0,36 (dixièmes d'unité, convention USD) ; rendus carrés. "
        "Couche à empiler au-dessus de la scène (rendu_pilote.usda).")
    st.GetRootLayer().customLayerData = {"origine_locale_L93_NGF": "917279.43 6460289.98 216.3",
                                         "source": "recon/out/paquet_jardin/v2/description + fabrique"}
    w = st.OverridePrim("/World")
    st.SetDefaultPrim(w)
    UsdGeom.Scope.Define(st, "/World/Cameras_v2")
    infos = {}
    for nom, v in VUES:
        oeil, cible = placer(desc, sol, nom, v)
        cam = UsdGeom.Camera.Define(st, f"/World/Cameras_v2/{nom}")
        cam.CreateFocalLengthAttr(round(focale(v["hfov"]), 6))
        cam.CreateHorizontalApertureAttr(APERTURE)
        cam.CreateVerticalApertureAttr(APERTURE)
        cam.CreateClippingRangeAttr(Gf.Vec2f(0.02, 3000))
        cam.CreateFStopAttr(float(v.get("f", 0.0)))
        cam.CreateFocusDistanceAttr(float(np.linalg.norm(cible - oeil)))
        cam.CreateProjectionAttr("perspective")
        UsdGeom.Xformable(cam).AddTransformOp().Set(regard(oeil, cible))
        prim = cam.GetPrim()
        prim.SetDocumentation(v["doc"])
        l93 = K.repere(oeil[None], "l93")[0]
        d = cible - oeil
        prim.SetCustomDataByKey("exposition_ev", float(v.get("ev", 0.0)))
        infos[nom] = {"oeil_local": K.r3(oeil, 3), "cible_local": K.r3(cible, 3), "hfov_deg": v["hfov"],
                      "f_stop": v.get("f", 0.0), "exposition_ev": v.get("ev", 0.0),
                      "azimut_deg": round((math.degrees(math.atan2(d[0], d[1])) + 360) % 360, 1),
                      "plongee_deg": round(math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))), 1),
                      "oeil_L93_NGF": K.r3(l93, 3), "doc": v["doc"]}
        for k, val in (("oeil_local_m", Gf.Vec3d(*map(float, oeil))), ("cible_locale_m", Gf.Vec3d(*map(float, cible))),
                       ("hfov_deg", float(v["hfov"]))):
            prim.SetCustomDataByKey(k, val)
    if chemin.exists():
        chemin.unlink()
    st.GetRootLayer().Export(str(chemin))
    return infos


def ecrire_hdr(chemin, img):
    """Image Radiance RGBE (.hdr) sans compression, octets identiques d'une exécution à l'autre (l'EXR
    d'OpenImageIO porte une date)."""
    h, l, _ = img.shape
    m = img.max(axis=2)
    e = np.zeros(m.shape, dtype=np.int32)
    f = np.zeros(m.shape)
    ok = m > 1e-32
    f[ok], e[ok] = np.frexp(m[ok])
    s = np.where(ok, f * 256.0 / np.maximum(m, 1e-32), 0.0)
    rgbe = np.zeros((h, l, 4), dtype=np.uint8)
    rgbe[..., :3] = np.clip(np.floor(img * s[..., None]), 0, 255).astype(np.uint8)
    rgbe[..., 3] = np.where(ok, e + 128, 0).astype(np.uint8)
    tete = ("#?RADIANCE\n# pj_rendu.py : ciel clair procedural\nFORMAT=32-bit_rle_rgbe\n\n"
            f"-Y {h} +X {l}\n").encode("ascii")
    Path(chemin).write_bytes(tete + rgbe.tobytes())


def ecrire_ciel(chemin, l=1024):
    """Ciel clair procédural en latlong (Radiance .hdr, identique à l'octet) : luminance
    horizon -> zénith (dégradé en sin(élévation)^0,45), brume claire sous l'horizon (le bord du décor
    ne se découpe pas sur un fond sombre). Renvoie le facteur d'échelle appliqué pour l'éclairement horizontal visé."""
    h = l // 2
    el = (0.5 - (np.arange(h) + 0.5) / h) * np.pi            # +π/2 en haut (zénith, pôle = Z de la scène)
    zen = np.array(CIEL_ZENITH)
    hor = np.array(CIEL_HORIZON)
    sol = hor * 0.5                                           # sous l'horizon : brume claire (bord du décor)
    t = np.clip(np.sin(np.maximum(el, 0.0)), 0, 1) ** 0.45
    ligne = np.where(el[:, None] >= 0, hor * (1 - t[:, None]) + zen * t[:, None],
                     sol + (hor - sol) * np.exp(-(-np.minimum(el, 0.0)[:, None]) / 0.08))
    # éclairement horizontal du ciel (hémisphère haut) : ∫ L cos θ dΩ
    dw = (np.pi / h) * (2 * np.pi / l) * np.cos(el)
    E = float(np.sum((ligne.mean(axis=1) * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0]))
    E_soleil = 2.0 ** SOLEIL["exposition"] * math.sin(math.radians(SOLEIL["hauteur_deg"]))
    k = E_soleil / RAPPORT_SOLEIL_CIEL / E
    img = np.repeat((ligne * k)[:, None, :], l, axis=1).astype(np.float64)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    ecrire_hdr(chemin, img)
    # couleur de l'éclairement horizontal du ciel (∫ L cos θ dΩ par canal) : balance des blancs
    Ec = np.array([float(np.sum((ligne[:, c] * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0])) for c in range(3)]) * k
    carte = np.array(SOLEIL_COULEUR) * E_soleil + Ec
    gains = np.array(BLANC_CIBLE) / carte
    gains = gains / gains[1]
    return {"fichier": chemin.name, "facteur": round(k, 4), "eclairement_horizontal_ciel": round(E * k, 4),
            "eclairement_horizontal_soleil": round(E_soleil, 4), "rapport": RAPPORT_SOLEIL_CIEL,
            "carte_grise_rvb": K.r3(carte / carte[1], 4), "gains_balance_blancs": K.r3(gains, 4),
            "soleil": dict(SOLEIL), "ciel_zenith": list(CIEL_ZENITH)}


def gains_balance():
    """Gains RVB de balance des blancs (carte grise horizontale soleil + ciel -> BLANC_CIBLE), sans écrire
    le ciel (rendre_pilote.py)."""
    l = 256
    h = l // 2
    el = (0.5 - (np.arange(h) + 0.5) / h) * np.pi
    zen, hor = np.array(CIEL_ZENITH), np.array(CIEL_HORIZON)
    t = np.clip(np.sin(np.maximum(el, 0.0)), 0, 1) ** 0.45
    ligne = np.where(el[:, None] >= 0, hor * (1 - t[:, None]) + zen * t[:, None], hor * 0.5)
    dw = (np.pi / h) * (2 * np.pi / l) * np.cos(el)
    E = float(np.sum((ligne.mean(axis=1) * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0]))
    E_soleil = 2.0 ** SOLEIL["exposition"] * math.sin(math.radians(SOLEIL["hauteur_deg"]))
    k = E_soleil / RAPPORT_SOLEIL_CIEL / E
    Ec = np.array([float(np.sum((ligne[:, c] * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0])) for c in range(3)]) * k
    carte = np.array(SOLEIL_COULEUR) * E_soleil + Ec
    g = np.array(BLANC_CIBLE) / carte
    return g / g[1]


# matériaux de décor (rendus de contrôle seulement ; revue réalisme r2 : bâtiments v1 en boîtes blanches à
# 236 sRGB, zone la plus claire du cadre) : (prim v1, nom, texture CC0, tuile m, albédo linéaire visé RVB)
DECOR_MATERIAUX = [
    (["/World/Batiments/murs"], "decor_enduit", "beton_bordure", 2.5, (0.49, 0.47, 0.43)),
    (["/World/Batiments/toits"], "decor_toit", "enrobe_bbsg_neuf", 2.0, (0.20, 0.17, 0.15)),
    (["/World/Terrain/espace_vert", "/World/Terrain/espace_vert_2025", "/World/Terrain/terre_plein_vegetal",
      "/World/Terrain/terre_plein_vegetal_2025"], "decor_gazon", "gazon_tondu", 1.4, (0.055, 0.075, 0.032)),
]


def materiau_decor(st, nom, lib, tile, cible, depuis):
    """Matériau de décor : texture CC0 en projection triplanaire (repère objet = monde pour le paquet v1,
    pas d'UV requis), albédo moyen ramené à `cible`, variation macro, AO de la texture."""
    from pxr import UsdShade
    import pj_materiaux as M
    T = Sdf.ValueTypeNames
    path = f"/World/Looks_v2_decor/{nom}"
    m = UsdShade.Material.Define(st, path)
    g = M._Graphe(st, path)
    meta = K.LIB_MAT / lib / "meta.json"
    moy = K.lire_json(meta).get("albedo_moyen_lineaire") if meta.exists() else None
    moy = moy or [0.3, 0.3, 0.3]
    po = g.noeud("position", "ND_position_vector3", {"space": (T.String, "object")}, T.Float3)
    ps = g.noeud("position_tuile", "ND_multiply_vector3FA", {"in1": (T.Float3, po), "in2": (T.Float, 1.0 / tile)}, T.Float3)
    no = g.noeud("normale", "ND_normal_vector3", {"space": (T.String, "object")}, T.Float3)
    f = U.chemin_relatif(K.LIB_MAT / lib / "textures" / f"{lib}_albedo.jpg", depuis)
    alb = g.noeud("albedo", "ND_triplanarprojection_color3", {
        "filex": (T.Asset, Sdf.AssetPath(f)), "filey": (T.Asset, Sdf.AssetPath(f)), "filez": (T.Asset, Sdf.AssetPath(f)),
        "position": (T.Float3, ps), "normal": (T.Float3, no), "blend": (T.Float, 0.5)}, T.Color3f)
    gain = Gf.Vec3f(*[float(c) / max(float(mm), 1e-3) for c, mm in zip(cible, moy)])
    alb = g.noeud("albedo_gain", "ND_multiply_color3", {"in1": (T.Color3f, alb), "in2": (T.Color3f, gain)}, T.Color3f)
    pf = g.noeud("macro_pos", "ND_multiply_vector3FA", {"in1": (T.Float3, po), "in2": (T.Float, 0.3)}, T.Float3)
    fr = g.noeud("macro", "ND_fractal3d_float", {"position": (T.Float3, pf), "octaves": (T.Int, 3)}, T.Float)
    rm = g.noeud("macro_gain", "ND_remap_float", {"in": (T.Float, fr), "inlow": (T.Float, -0.5), "inhigh": (T.Float, 0.5),
                                                  "outlow": (T.Float, 0.85), "outhigh": (T.Float, 1.15)}, T.Float)
    alb = g.noeud("albedo_macro", "ND_multiply_color3FA", {"in1": (T.Color3f, alb), "in2": (T.Float, rm)}, T.Color3f)
    ss = g.noeud("surface", "ND_standard_surface_surfaceshader", {"base": (T.Float, 1.0), "base_color": (T.Color3f, alb),
                                                                  "specular_roughness": (T.Float, 0.85)}, T.Token)
    m.CreateSurfaceOutput("mtlx").ConnectToSource(ss)
    return m


def ecrire_decor(stage_v1, R, chemin, ref=None):
    """Couche de rendu : arbres v1 à plus de DECOR_MAX_M de l'emprise masqués (invisibleIds) ; bâtiments,
    toits et espaces verts v1 hors emprise sur des matériaux CC0 de décor (DECOR_MATERIAUX)."""
    from pxr import UsdShade
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    st.GetRootLayer().documentation = (
        "Décor des rendus de contrôle v2 (pj_rendu.py) : arbres v1 (boules) masqués "
        + (f"à plus de {DECOR_MAX_M:g} m de l'emprise pilote" if DECOR_MAX_M >= 0 else "partout")
        + " (végétation v2 : phase 4) ; bâtiments (enduit d'albédo 0,47, légèrement chaud), toits et espaces "
          "verts v1 sur des matériaux CC0 en projection triplanaire ; paquet v1 inchangé.")
    depuis = Path(ref) if ref else Path(chemin)
    UsdGeom.Scope.Define(st, "/World/Looks_v2_decor")
    liaisons = {}
    for prims, nom, lib, tile, cible in DECOR_MATERIAUX:
        mat = materiau_decor(st, nom, lib, tile, cible, depuis)
        for pp in prims:
            if stage_v1.GetPrimAtPath(pp):
                o = st.OverridePrim(pp)
                UsdShade.MaterialBindingAPI.Apply(o).Bind(mat, UsdShade.Tokens.strongerThanDescendants)
                liaisons[pp] = nom
    n = 0
    for racine in ("/World/Vegetation",):
        rp = stage_v1.GetPrimAtPath(racine)
        if not rp:
            continue
        for p in sorted(rp.GetChildren(), key=lambda q: q.GetName()):
            if not p.IsA(UsdGeom.PointInstancer):
                continue
            P = np.array(UsdGeom.PointInstancer(p).GetPositionsAttr().Get(), dtype=np.float64)
            x0, y0, x1, y1 = R
            d = np.hypot(np.maximum(np.maximum(x0 - P[:, 0], P[:, 0] - x1), 0),
                         np.maximum(np.maximum(y0 - P[:, 1], P[:, 1] - y1), 0))
            loin = np.where(d > DECOR_MAX_M)[0] if DECOR_MAX_M >= 0 else np.arange(len(P))
            if len(loin):
                UsdGeom.PointInstancer(st.OverridePrim(p.GetPath())).CreateInvisibleIdsAttr().Set(
                    Vt.Int64Array([int(i) for i in loin]))
                n += len(loin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists():
        chemin.unlink()
    st.GetRootLayer().Export(str(chemin))
    return {"arbres_masques": n, "distance_m": DECOR_MAX_M, "materiaux_decor": liaisons}


def ecrire_racine(chemin, cameras, couches, controle, ref=None, ciel=None):
    """Racine de rendu : caméras + couches v2 (les plus fortes en premier) + scène de contrôle v1 ;
    ref : emplacement de référence des chemins relatifs (défaut : chemin) ; ciel : texture du dôme."""
    ref = ref or chemin
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    lay = st.GetRootLayer()
    lay.documentation = (
        "Scène de rendu Karma de la zone pilote v2 (pj_rendu.py) : caméras v2, couches fabriquées "
        "(îlots, bordures, sol, matériaux CC0), masque du v1 dans l'emprise pilote, puis la scène de "
        "contrôle v1 (paquet v1 hors emprise, réglages Karma). Soleil : azimut 220°, hauteur 29°, exposition 2 ; "
        "ciel clair procédural (rapport d'éclairement soleil / ciel 3,5:1).")
    for c in [cameras] + list(couches) + [controle]:
        lay.subLayerPaths.append(U.chemin_relatif(c, ref))
    w = st.OverridePrim("/World")
    st.SetDefaultPrim(w)
    sol = st.OverridePrim("/World/Lumieres/soleil")
    a = 90.0 - SOLEIL["hauteur_deg"]
    c = 180.0 - SOLEIL["azimut_deg"]
    sol.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Float3).Set(Gf.Vec3f(a, 0.0, c))
    sol.SetCustomDataByKey("soleil", f"azimut {SOLEIL['azimut_deg']:g}° (depuis le nord, horaire), hauteur {SOLEIL['hauteur_deg']:g}° : "
                                     "DistantLight émet selon −Z, rotateXYZ = (90 − h, 0, 180 − az)")
    sol.CreateAttribute("inputs:exposure", Sdf.ValueTypeNames.Float).Set(float(SOLEIL["exposition"]))
    if ciel is not None:
        dome = st.OverridePrim("/World/Lumieres/ciel")
        dome.CreateAttribute("inputs:texture:file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(U.chemin_relatif(ciel, ref)))
        dome.CreateAttribute("inputs:color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 1.0, 1.0))
        dome.CreateAttribute("inputs:exposure", Sdf.ValueTypeNames.Float).Set(0.0)
        dome.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(1.0)
    rs = st.OverridePrim("/Render/rendersettings")
    rs.CreateAttribute("karma:global:pathtracedsamples", Sdf.ValueTypeNames.Int).Set(128)
    st.SetMetadata("renderSettingsPrimPath", "/Render/rendersettings")
    if chemin.exists():
        chemin.unlink()
    lay.Export(str(chemin))
