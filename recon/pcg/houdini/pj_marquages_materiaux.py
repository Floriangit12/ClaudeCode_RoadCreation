"""Peinture routière des marquages v2 : un Material par classe `peinture_<couleur>_u<usure>` de
assets/specs/peinture.json (instances MI_peinture_<couleur>_u<usure> côté Unreal).

Deux réseaux par matériau :
- MaterialX (contexte `mtlx`, Karma), /World/Looks_marquages/<mid> : recette `usure.principe` de
  peinture.json, masques procéduraux (aucune texture City Sample ; seule texture : albédo et normale CC0 de
  l'enrobé neuf (materiau_id enrobe_bbsg_neuf_2025, assets/lib/materiaux/enrobe_bbsg_neuf), pour la macrotexture lue à travers le film) :
  - R écaillage fin : fractal3d (2,5 cm, 3 octaves), égalisé ;
  - G aléa par plaque : cellnoise2d sur une grille de 0,35 m déformée (fractal3d vector3, 0,45 cellule) ;
  - B fissures : distance au bord de la plaque, largeur 1 cm ; plaques de 0,30 m le long de l'axe de la marque sur 1,0 m
    en travers (primvar axe_marque : fissures surtout transversales), bord rendu irrégulier par un bruit fin
    (fractal3d 2,5 cm, 0,25 plaque) ;
  - A variation lente : fractal3d (1,6 m, 2 octaves), égalisé ;
  - égalisation : u = 1 / (1 + exp(−1,702 x / σ)) (fonction logistique, approximation de la loi normale à
    1 % près), σ mesurés sous Karma XPU (calibration du 10/10 : 0,285 pour 3 octaves, 0,278 pour 2) ;
  - score = R·wR + G·wG + A·wA ; peinture = smoothstep(seuil ± 0,004, score)·(1 − fissure) ; le seuil vient
    du primvar `seuil_usure` (par face, tiré de la couverture décrite de l'entité, table
    usure.seuils_score) et vaut par défaut celui de la classe ;
  - couleur = mix(gris, couleur neuve, chroma[u])·(albédo enrobé / moyenne)^transparence[u], salie vers
    l'albédo de l'enrobé par salete[u]·(0,6 + 0,8 A) ;
  - hors peinture : usures 0 et 1, trous transparents (la chaussée réelle se voit) ; usures 2, 3, F
    (OpacityMaskEmprise), empreinte = voile semi-transparent (opacité 1 − FondContraste, couleur
    moyenne·(FondGain − FondContraste)/(1 − FondContraste)) : résultat = FondContraste·sol + … ≈ recette
    `fond` quel que soit le sol réel (v1 ou v2) ; fissures : voile noir d'opacité 0,45 (sol × 0,55) ;
  - rugosité mix(0,90, Rugosite[u], peinture) (F : 0,82 = enrobé − 0,08) ; normale de l'enrobé aplatie de
    70 % sous la peinture ;
- UsdPreviewSurface (contexte universel) : couleur moyenne attendue, rugosité, opacité de l'emprise.
Écarts à la recette de peinture.json (ECARTS, revues réalisme du 10/10, tracés dans le manifeste) :
- usure 0 : grains isolés seuls (poids R = 1, seuil 0,005 : ≈ 0,5 % de manques uniformes, plus de grappes du canal A),
  transparence 0,05 ;
- usure 1 : micro-écaillage fin seul (poids R = 1), film à 0,62 de l'albédo neuf (FacteurFilm), voile 10 %,
  transparence 0,15 ; seuil = 1 − part peinte (score uniforme), part peinte interpolée sur la table niveaux_obtenus ;
- facteurs de film calés sur le contrôle de luminance des rendus (pj_marquages_luminance : rapport peinture / enrobé
  visé 1,45-1,65 en usure 1, 1,30-1,50 en usure 2, 1,12-1,32 en usure 3) ;
- usures 2 et 3 : grisaillement continu plutôt que plaques arrachées : poids [0,8 ; 0 ; 0,2] et [0,75 ; 0 ; 0,25] (plus de
  plaques G), manques hors traces de roues plafonnés à ≈ 8 % et 15 % (SeuilMax 0,16 et 0,22), film à 0,54 et 0,48 de
  l'albédo neuf, salissure 0,25 et 0,40, transparence 0,6 et 0,8 ; fissures moins nombreuses (FissureA 0,6 en usure 2) ;
- fantôme F : empreinte lisse gris clair qui suit l'albédo réel du sol (FondContraste 0,95, FondGain 1,15 : sol x 0,95
  + 0,04, soit +10 à +25 %), rugosité de l'empreinte = enrobé − 0,08, résidus de peinture en grains fins (R seul) sur
  1 % (seuil 0,99), couleur du film d'usure 3 (0,48 de l'albédo neuf) ;
- jaune neuf : vert 0,55 au lieu de 0,613 (G/R ≈ 0,88 sur la photo 2026 f8d91bb1) ;
- traces de roues (usure.traces_de_roues_option) : seuil x √(manque_roues) (primvar par sommet de toutes les marques
  d'usure 1 à 3 hors fantômes : f = 1 + 1,5·exp(−((|t| − 0,85)/0,20)²), t = écart au centre de la voie) ; la part de
  manques est multipliée par ≈ f ;
- salissure du caniveau : salete + 0,2·(1 − d/0,15) à moins de 0,15 m d'une bordure (primvar dist_bordure, par sommet) ;
- rendu Karma : primvar karma:object:rendervisibility = « -shadow » sur les maillages (film de 0,5 mm en réalité : le
  décalage de 3 mm ne doit pas ombrer les manques).
Liaison Unreal (CONTRAT_EXPORT.md) : Material /World/Looks/<mid> (UsdPreviewSurface + outputs:unreal:surface ->
/Game/PJ/Materials/MI_<mid>) en material:binding:preview (pj_commun.lier_ue).
"""
from pxr import Gf, Sdf, UsdShade

import pj_commun as K
import pj_usd as U

T = Sdf.ValueTypeNames
LOOKS = "/World/Looks_marquages"
SIGMA = {1: 0.249, 2: 0.278, 3: 0.285}         # écart type de ND_fractal3d_float (Karma XPU 22.0.459)
MOYENNE_SOL = 0.20                              # albédo moyen d'enrobé pour l'empreinte (v1 ortho 0,26 ; v2 neuf 0,12)
RUGOSITE_SOL = 0.90
ENROBE = "enrobe_bbsg_neuf_2025"                # materiau_id de la macrotexture lue à travers le film (CC0 Asphalt033)
COULEURS_ORDRE = ("blanc", "jaune", "ocre", "vert", "cyan", "bleu", "rouge")
USURES = ("0", "1", "2", "3", "F")


ECARTS = {"0": {"PoidsRGA": [1.0, 0.0, 0.0], "Transparence": 0.05, "Seuil": 0.005},
          "1": {"PoidsRGA": [1.0, 0.0, 0.0], "Salete": 0.10, "Transparence": 0.15, "FacteurFilm": 0.62},
          "2": {"PoidsRGA": [0.8, 0.0, 0.2], "Salete": 0.25, "Transparence": 0.6, "FacteurFilm": 0.54, "FissureA": 0.6,
                "SeuilMax": 0.16},
          "3": {"PoidsRGA": [0.75, 0.0, 0.25], "Salete": 0.40, "Transparence": 0.8, "FacteurFilm": 0.48, "SeuilMax": 0.22},
          "F": {"PoidsRGA": [1.0, 0.0, 0.0], "Seuil": 0.99, "FondContraste": 0.95, "FondGain": 1.15, "FacteurFilm": 0.48}}
ECARTS_COULEUR = {"jaune": {"CouleurNeuve": [0.764, 0.55, 0.212]}}
SEUIL_RESIDUS_F = 0.99
SEUIL_NEUF = 0.005               # usure 0 : ≈ 0,5 % de grains isolés (film continu, pas de grappes)
CELLULE = (0.30, 1.0)            # plaques de faïençage : le long de l'axe de la marque, en travers (m)
SALETE_CANIVEAU = (0.20, 0.15)   # salissure ajoutée et distance d'effet à la bordure (m)


def mid(couleur, usure):
    return f"peinture_{couleur}_u{usure}"


def parametres(peinture, couleur, usure):
    """Paramètres d'une classe : table unreal_5_8.instances de peinture.json (MI_peinture_<c>_u<u>), écarts ECARTS."""
    v = dict(peinture["unreal_5_8"]["instances"]["valeurs"][f"MI_{mid(couleur, usure)}"])
    v.update(ECARTS.get(usure, {}))
    v.update(ECARTS_COULEUR.get(couleur, {}))
    v.setdefault("FacteurFilm", 1.0)
    v["couverture_classe"] = float(peinture["lien_scene"]["couverture_scene"][usure])
    return v


def seuil_face(peinture, usure, couverture):
    """Seuil par face : usure 0 : SEUIL_NEUF ; usure 1 (score = R uniforme) : 1 − part peinte interpolée en couverture
    entre les niveaux 0 et 1 de la table ; F : résidus fixes (SEUIL_RESIDUS_F) ; sinon seuil_de_couverture."""
    if usure == "F":
        return SEUIL_RESIDUS_F
    if usure == "0":
        return SEUIL_NEUF
    if usure == "1":
        ni = peinture["usure"]["seuils_score"]["niveaux_obtenus"]
        c0, p0 = float(ni["1"]["couverture_effective"]), float(ni["1"]["peinture"])
        c1, p1 = float(ni["0"]["couverture_effective"]), float(ni["0"]["peinture"])
        c = min(max(float(couverture), c0 - 0.05), c1)
        part = p0 + (p1 - p0) * (c - c0) / max(c1 - c0, 1e-9)
        return float(min(max(1.0 - part, 0.0), 0.2))
    # usures 2-3 : manques plafonnés (grisaillement plutôt que plaques arrachées)
    return float(min(seuil_de_couverture(peinture, couverture), ECARTS.get(usure, {}).get("SeuilMax", 1.0)))


def seuil_de_couverture(peinture, couverture):
    """Seuil du score donnant la couverture effective décrite (interpolation de usure.seuils_score)."""
    ni = peinture["usure"]["seuils_score"]["niveaux_obtenus"]
    pts = sorted((float(ni[u]["couverture_effective"]), float(ni[u]["seuil"])) for u in USURES)
    c = min(max(float(couverture), pts[0][0]), pts[-1][0])
    for (c0, s0), (c1, s1) in zip(pts[:-1], pts[1:]):
        if c0 <= c <= c1:
            return s0 + (s1 - s0) * (c - c0) / max(c1 - c0, 1e-9)
    return pts[-1][1]


class _G:
    def __init__(self, st, base):
        self.st, self.base = st, base

    def n(self, nom, idn, ent, typ):
        sh = UsdShade.Shader.Define(self.st, f"{self.base}/{nom}")
        sh.CreateIdAttr(idn)
        for k, (t, v) in ent.items():
            i = sh.CreateInput(k, t)
            if isinstance(v, UsdShade.Output):
                i.ConnectToSource(v)
            else:
                i.Set(v)
        return sh.CreateOutput("out", typ)

    def f(self, nom, op, a, b):
        return self.n(nom, f"ND_{op}_float", {"in1": (T.Float, a), "in2": (T.Float, b)}, T.Float)


def _egaliser(g, nom, x, sigma):
    """u = 1 / (1 + exp(−1,702 x / σ))."""
    k = g.f(nom + "_k", "multiply", x, -1.702 / sigma)
    e = g.n(nom + "_exp", "ND_exp_float", {"in": (T.Float, k)}, T.Float)
    d = g.f(nom + "_den", "add", e, 1.0)
    return g.f(nom, "divide", 1.0, d)


def materiau_mtlx(st, couleur, usure, peinture, depuis, specs):
    m_id = mid(couleur, usure)
    v = parametres(peinture, couleur, usure)
    path = f"{LOOKS}/{m_id}"
    mat = UsdShade.Material.Define(st, path)
    mat.GetPrim().SetCustomDataByKey("materiau_id", m_id)
    mat.GetPrim().SetCustomDataByKey("ue_materiau", f"/Game/PJ/Materials/MI_{m_id}")
    mat.GetPrim().SetCustomDataByKey("source", f"assets/specs/peinture.json : unreal_5_8.instances.valeurs.MI_{m_id}")
    g = _G(st, path)
    pos = g.n("position", "ND_position_vector3", {"space": (T.String, "world")}, T.Float3)
    # --- masques
    pr = g.n("R_pos", "ND_multiply_vector3FA", {"in1": (T.Float3, pos), "in2": (T.Float, 40.0)}, T.Float3)
    r = g.n("R_bruit", "ND_fractal3d_float", {"position": (T.Float3, pr), "octaves": (T.Int, 3)}, T.Float)
    R = _egaliser(g, "R", r, SIGMA[3])
    pa = g.n("A_pos", "ND_multiply_vector3FA", {"in1": (T.Float3, pos), "in2": (T.Float, 1.0 / 1.6)}, T.Float3)
    a = g.n("A_bruit", "ND_fractal3d_float", {"position": (T.Float3, pa), "octaves": (T.Int, 2)}, T.Float)
    A = _egaliser(g, "A", a, SIGMA[2])
    # repère de la marque : a = axe (primvar axe_marque, par sommet), n = normale ; plaques CELLULE[0] le long de a,
    # CELLULE[1] en travers ; déformation lente (0,45 plaque) et bruit fin du bord (2,5 cm, 0,25 plaque)
    ax = g.n("axe_marque", "ND_geompropvalue_vector2", {"geomprop": (T.String, "axe_marque"),
                                                         "default": (T.Float2, Gf.Vec2f(1.0, 0.0))}, T.Float2)
    axx = g.n("axe_x", "ND_extract_vector2", {"in": (T.Float2, ax), "index": (T.Int, 0)}, T.Float)
    axy = g.n("axe_y", "ND_extract_vector2", {"in": (T.Float2, ax), "index": (T.Int, 1)}, T.Float)
    px_ = g.n("pos_x", "ND_extract_vector3", {"in": (T.Float3, pos), "index": (T.Int, 0)}, T.Float)
    py_ = g.n("pos_y", "ND_extract_vector3", {"in": (T.Float3, pos), "index": (T.Int, 1)}, T.Float)
    pa = g.f("pos_a", "add", g.f("pos_a1", "multiply", px_, axx), g.f("pos_a2", "multiply", py_, axy))
    pn = g.f("pos_n", "subtract", g.f("pos_n1", "multiply", py_, axx), g.f("pos_n2", "multiply", px_, axy))
    ca = g.f("G_ca", "multiply", pa, 1.0 / CELLULE[0])
    cn = g.f("G_cn", "multiply", pn, 1.0 / CELLULE[1])
    pc = g.n("G_pos", "ND_combine3_vector3", {"in1": (T.Float, ca), "in2": (T.Float, cn), "in3": (T.Float, 0.0)}, T.Float3)
    pw = g.n("G_pos_def", "ND_multiply_vector3FA", {"in1": (T.Float3, pc), "in2": (T.Float, 0.8)}, T.Float3)
    dw = g.n("G_def", "ND_fractal3d_vector3", {"position": (T.Float3, pw), "octaves": (T.Int, 2),
                                               "amplitude": (T.Float3, Gf.Vec3f(0.45, 0.45, 0.0))}, T.Float3)
    ph = g.n("G_pos_hf", "ND_multiply_vector3FA", {"in1": (T.Float3, pos), "in2": (T.Float, 40.0)}, T.Float3)
    dh = g.n("G_hf", "ND_fractal3d_vector3", {"position": (T.Float3, ph), "octaves": (T.Int, 2),
                                              "amplitude": (T.Float3, Gf.Vec3f(0.25, 0.25, 0.0))}, T.Float3)
    q3 = g.n("G_q3", "ND_add_vector3", {"in1": (T.Float3, pc), "in2": (T.Float3, dw)}, T.Float3)
    q3h = g.n("G_q3h", "ND_add_vector3", {"in1": (T.Float3, q3), "in2": (T.Float3, dh)}, T.Float3)
    q = g.n("G_q", "ND_convert_vector3_vector2", {"in": (T.Float3, q3)}, T.Float2)
    qh = g.n("B_q", "ND_convert_vector3_vector2", {"in": (T.Float3, q3h)}, T.Float2)
    G = g.n("G", "ND_cellnoise2d_float", {"texcoord": (T.Float2, q)}, T.Float)
    fr = g.n("B_fract", "ND_modulo_vector2FA", {"in1": (T.Float2, qh), "in2": (T.Float, 1.0)}, T.Float2)
    fx = g.n("B_fx", "ND_extract_vector2", {"in": (T.Float2, fr), "index": (T.Int, 0)}, T.Float)
    fy = g.n("B_fy", "ND_extract_vector2", {"in": (T.Float2, fr), "index": (T.Int, 1)}, T.Float)
    ex = g.n("B_ex", "ND_min_float", {"in1": (T.Float, fx), "in2": (T.Float, g.f("B_1mx", "subtract", 1.0, fx))}, T.Float)
    ey = g.n("B_ey", "ND_min_float", {"in1": (T.Float, fy), "in2": (T.Float, g.f("B_1my", "subtract", 1.0, fy))}, T.Float)
    exm = g.f("B_ex_m", "multiply", ex, CELLULE[0])
    eym = g.f("B_ey_m", "multiply", ey, CELLULE[1])
    e = g.n("B_e", "ND_min_float", {"in1": (T.Float, exm), "in2": (T.Float, eym)}, T.Float)
    # B = clamp(1 − (F2 − F1)/largeur) avec F2 − F1 ≈ 2 e (m) ; largeur 1 cm
    em = g.f("B_e_m", "multiply", e, 2.0 / 0.01)
    B = g.n("B", "ND_clamp_float", {"in": (T.Float, g.f("B_inv", "subtract", 1.0, em)), "low": (T.Float, 0.0),
                                    "high": (T.Float, 1.0)}, T.Float)
    # --- peinture présente
    wR, wG, wA = v["PoidsRGA"]
    sc = g.f("score_r", "multiply", R, float(wR))
    sc = g.f("score_rg", "add", sc, g.f("score_g", "multiply", G, float(wG)))
    sc = g.f("score", "add", sc, g.f("score_a", "multiply", A, float(wA)))
    seuil0 = g.n("seuil_face", "ND_geompropvalue_float", {"geomprop": (T.String, "seuil_usure"),
                                                          "default": (T.Float, float(v["Seuil"]))}, T.Float)
    if usure != "F":
        # traces de roues : seuil x √f (f = primvar manque_roues, 1 par défaut)
        f_r = g.n("manque_roues", "ND_geompropvalue_float", {"geomprop": (T.String, "manque_roues"),
                                                             "default": (T.Float, 1.0)}, T.Float)
        seuil = g.f("seuil", "multiply", seuil0, g.n("manque_roues_racine", "ND_sqrt_float", {"in": (T.Float, f_r)}, T.Float))
    else:
        seuil = seuil0
    p = g.n("peinture_brute", "ND_smoothstep_float", {"in": (T.Float, sc), "low": (T.Float, g.f("seuil_bas", "subtract", seuil, 0.004)),
                                                       "high": (T.Float, g.f("seuil_haut", "add", seuil, 0.004))}, T.Float)
    if float(v["FissureB"]) < 1.5:
        fb = g.n("fiss_b", "ND_ifgreatereq_float", {"value1": (T.Float, B), "value2": (T.Float, float(v["FissureB"])),
                                                    "in1": (T.Float, 1.0), "in2": (T.Float, 0.0)}, T.Float)
        fa = g.n("fiss_a", "ND_ifgreatereq_float", {"value1": (T.Float, A), "value2": (T.Float, float(v["FissureA"])),
                                                    "in1": (T.Float, 1.0), "in2": (T.Float, 0.0)}, T.Float)
        fiss = g.f("fissure", "multiply", fb, fa)
        p = g.f("peinture", "multiply", p, g.f("non_fissure", "subtract", 1.0, fiss))
    else:
        fiss = None
    # --- couleurs
    cn_ = [float(x) * float(v["FacteurFilm"]) for x in v["CouleurNeuve"]]
    y = 0.2126 * cn_[0] + 0.7152 * cn_[1] + 0.0722 * cn_[2]
    ch = float(v["Chroma"])
    cu = Gf.Vec3f(*[y + (c - y) * ch for c in cn_])
    sp = specs.materiau_rendu(ENROBE)
    tile = float(sp["tile_m"])
    moy_tex = (sp.get("texture_mesuree") or {}).get("albedo_moyen_lineaire") or [0.3, 0.3, 0.3]
    uv = g.n("uv", "ND_geompropvalue_vector2", {"geomprop": (T.String, "st1")}, T.Float2)
    uvs = g.n("uv_tuile", "ND_multiply_vector2FA", {"in1": (T.Float2, uv), "in2": (T.Float, 1.0 / tile)}, T.Float2)
    lib = sp["source_cc0"]["nom"]
    tex = K.LIB_MAT / lib / "textures" / f"{lib}_albedo.jpg"
    alb = g.n("enrobe_albedo", "ND_hextiledimage_color3", {
        "file": (T.Asset, Sdf.AssetPath(U.chemin_relatif(tex, depuis))), "texcoord": (T.Float2, uvs),
        "rotationrange": (T.Float2, Gf.Vec2f(0, 360)), "scalerange": (T.Float2, Gf.Vec2f(0.85, 1.15)),
        "falloff": (T.Float, 0.12)}, T.Color3f)
    # albédo relatif (moyenne 1) puis albédo d'enrobé ramené à MOYENNE_SOL
    relc = g.n("enrobe_rel", "ND_divide_color3", {"in1": (T.Color3f, alb), "in2": (T.Color3f, Gf.Vec3f(*map(float, moy_tex)))}, T.Color3f)
    relc = g.n("enrobe_rel_borne", "ND_clamp_color3FA", {"in": (T.Color3f, relc), "low": (T.Float, 0.2), "high": (T.Float, 3.0)}, T.Color3f)
    trp = g.n("transparence", "ND_power_color3FA", {"in1": (T.Color3f, relc), "in2": (T.Float, float(v["Transparence"]))}, T.Color3f)
    coul = g.n("couleur_film", "ND_multiply_color3", {"in1": (T.Color3f, cu), "in2": (T.Color3f, trp)}, T.Color3f)
    sol = g.n("albedo_sol", "ND_multiply_color3FA", {"in1": (T.Color3f, relc), "in2": (T.Float, MOYENNE_SOL)}, T.Color3f)
    dbo = g.n("dist_bordure", "ND_geompropvalue_float", {"geomprop": (T.String, "dist_bordure"), "default": (T.Float, 10.0)}, T.Float)
    can = g.n("salete_caniveau", "ND_clamp_float", {"in": (T.Float, g.f("salete_can_1", "subtract", 1.0,
                                                                         g.f("salete_can_d", "multiply", dbo, 1.0 / SALETE_CANIVEAU[1]))),
                                                     "low": (T.Float, 0.0), "high": (T.Float, 1.0)}, T.Float)
    sal0 = g.f("salete_brute", "multiply", float(v["Salete"]), g.f("salete_a", "add", 0.6, g.f("salete_a8", "multiply", A, 0.8)))
    sal = g.n("salete", "ND_clamp_float", {"in": (T.Float, g.f("salete_tot", "add", sal0, g.f("salete_can", "multiply", can, SALETE_CANIVEAU[0]))),
                                           "low": (T.Float, 0.0), "high": (T.Float, 1.0)}, T.Float)
    coul = g.n("couleur_peinture", "ND_mix_color3", {"fg": (T.Color3f, sol), "bg": (T.Color3f, coul), "mix": (T.Float, sal)}, T.Color3f)
    # empreinte (hors peinture) : voile (couleur X, opacité α) ; trous transparents sinon
    if v["OpacityMaskEmprise"]:
        alpha = 1.0 - float(v["FondContraste"])
        X = MOYENNE_SOL * (float(v["FondGain"]) - float(v["FondContraste"])) / max(alpha, 1e-3)
        fond_c, fond_a = Gf.Vec3f(X, X, X * 0.97), alpha
    else:
        fond_c, fond_a = Gf.Vec3f(MOYENNE_SOL, MOYENNE_SOL, MOYENNE_SOL), 0.0
    fondc = g.n("fond", "ND_constant_color3", {"value": (T.Color3f, fond_c)}, T.Color3f)
    fonda = g.n("fond_opacite", "ND_constant_float", {"value": (T.Float, fond_a)}, T.Float)
    if fiss is not None:
        fondc = g.n("fond_fissure", "ND_mix_color3", {"fg": (T.Color3f, Gf.Vec3f(0, 0, 0)), "bg": (T.Color3f, fondc), "mix": (T.Float, fiss)}, T.Color3f)
        fonda = g.n("fond_fissure_opacite", "ND_mix_float", {"fg": (T.Float, 0.45), "bg": (T.Float, fonda), "mix": (T.Float, fiss)}, T.Float)
    base = g.n("base_color", "ND_mix_color3", {"fg": (T.Color3f, coul), "bg": (T.Color3f, fondc), "mix": (T.Float, p)}, T.Color3f)
    op = g.n("opacite", "ND_mix_float", {"fg": (T.Float, 1.0), "bg": (T.Float, fonda), "mix": (T.Float, p)}, T.Float)
    opc = g.n("opacite_c", "ND_convert_float_color3", {"in": (T.Float, op)}, T.Color3f)
    rug_p = float(v["Rugosite"]) if float(v["Rugosite"]) > 0 else RUGOSITE_SOL + float(v["Rugosite"])
    rug_fond = RUGOSITE_SOL - 0.08 if usure == "F" else RUGOSITE_SOL         # empreinte grenaillée plus lisse
    rug = g.n("rugosite", "ND_mix_float", {"fg": (T.Float, rug_p), "bg": (T.Float, rug_fond), "mix": (T.Float, p)}, T.Float)
    texn = K.LIB_MAT / lib / "textures" / f"{lib}_normale.png"
    nt = g.n("normale_enrobe", "ND_hextilednormalmap_vector3", {
        "file": (T.Asset, Sdf.AssetPath(U.chemin_relatif(texn, depuis))), "texcoord": (T.Float2, uvs),
        "rotationrange": (T.Float2, Gf.Vec2f(0, 360)), "scalerange": (T.Float2, Gf.Vec2f(0.85, 1.15)),
        "falloff": (T.Float, 0.12)}, T.Float3)
    ng = g.n("normale_geo", "ND_normal_vector3", {"space": (T.String, "world")}, T.Float3)
    km = g.f("aplat", "multiply", p, 0.7)
    nm = g.n("normale_mix", "ND_mix_vector3", {"fg": (T.Float3, ng), "bg": (T.Float3, nt), "mix": (T.Float, km)}, T.Float3)
    nn = g.n("normale", "ND_normalize_vector3", {"in": (T.Float3, nm)}, T.Float3)
    ss = g.n("surface", "ND_standard_surface_surfaceshader", {
        "base": (T.Float, 1.0), "base_color": (T.Color3f, base), "specular": (T.Float, 0.5),
        "specular_roughness": (T.Float, rug), "opacity": (T.Color3f, opc), "normal": (T.Float3, nn)}, T.Token)
    mat.CreateSurfaceOutput("mtlx").ConnectToSource(ss)
    # repli UsdPreviewSurface : couleur moyenne attendue de la classe
    cov = v["couverture_classe"]
    moy = [MOYENNE_SOL + (c - MOYENNE_SOL) * cov for c in (cu[0], cu[1], cu[2])]
    s = UsdShade.Shader.Define(st, f"{path}/ups_surface")
    s.CreateIdAttr("UsdPreviewSurface")
    s.CreateInput("diffuseColor", T.Color3f).Set(Gf.Vec3f(*moy))
    s.CreateInput("roughness", T.Float).Set(float(rug_p))
    s.CreateInput("metallic", T.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(s.CreateOutput("surface", T.Token))
    return path, moy, rug_p


def ecrire(st, classes, peinture, depuis, specs):
    """Matériaux des classes [(couleur, usure)] triées ; renvoie {mid: (chemin Karma, aperçu, rugosité)}."""
    U.scope(st, LOOKS)
    out = {}
    for c, u in sorted(classes, key=lambda cu: (COULEURS_ORDRE.index(cu[0]) if cu[0] in COULEURS_ORDRE else 99, cu[0], USURES.index(cu[1]))):
        out[mid(c, u)] = materiau_mtlx(st, c, u, peinture, depuis, specs)
    return out


def doc_recette():
    return ("peinture.json usure.principe ; masques procéduraux MaterialX (fractal3d, cellnoise2d sur grille anisotrope "
            f"{CELLULE} m le long / en travers de l'axe de la marque (primvar axe_marque), bord irrégulier), égalisation "
            f"logistique (σ {SIGMA}) ; seuil par face (primvar seuil_usure, seuil_face) x √manque_roues ; enrobé CC0 {ENROBE} "
            f"(macrotexture) ; empreinte en voile (moyenne d'enrobé {MOYENNE_SOL}) ; écarts {ECARTS} ; couleurs {ECARTS_COULEUR} ; "
            f"salissure du caniveau {SALETE_CANIVEAU} (primvar dist_bordure) ; ombres portées des marques désactivées sous "
            "Karma (karma:object:rendervisibility -shadow)")
