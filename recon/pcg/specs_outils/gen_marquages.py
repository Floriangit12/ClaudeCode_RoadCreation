# -*- coding: utf-8 -*-
"""Génère assets/specs/marquages_geometrie.json (spec géométrique IISR 7e partie VC20250404).

Les polygones des flèches sont calculés depuis les cotes des annexes B1/B2/B3 ; la tête de la flèche
de rabattement (sans cote horizontale) et la figurine vélo (raster D1) sont mesurées sur les images
natives de l'annexe (scripts mesure_rab.py, vectoriser_velo.py du même dossier).
"""
import json
import math
import sys

import numpy as np

SORTIE = sys.argv[1]
VELO = sys.argv[2]          # velo_vecteur.json (vectoriser_velo.py)
TOL_CORDE = 0.001           # m : erreur de corde maximale des arcs et ellipses discrétisés

IISR = "IISR 7e partie, version consolidée VC20250404 (Cerema, 04/04/2025)"
IISR_URL = "https://equipementsdelaroute.cerema.fr/IMG/pdf/iisr_7epartie_vc_20250404.pdf"


def r4(v):
    return round(float(v) + 0.0, 4)


def aire(P):
    P = np.asarray(P, float)
    return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


def miroir(P):
    """Symétrie x -> -x en gardant le sens trigonométrique (ordre inversé)."""
    return [[-x, y] for x, y in P][::-1]


def arc_x(y, x_min, R, y_t):
    """Bord en arc de cercle, tangente verticale en y_t (abscisse x_min), centre à droite (x_min + R, y_t)."""
    return x_min + R - math.sqrt(R * R - (y - y_t) ** 2)


def echantillonner_arc(y0, y1, x_min, R, y_t, tol=TOL_CORDE):
    """Points de l'arc entre y0 et y1 (inclus), pas angulaire constant tel que la flèche de corde <= tol."""
    t0, t1 = math.asin((y0 - y_t) / R), math.asin((y1 - y_t) / R)
    dmax = 2.0 * math.acos(1.0 - tol / R)
    n = max(1, math.ceil(abs(t1 - t0) / dmax))
    pts = []
    for k in range(n + 1):
        t = t0 + (t1 - t0) * k / n
        y = y_t + R * math.sin(t)
        pts.append([arc_x(y, x_min, R, y_t), y])
    return pts, n


def ellipse(cx, cy, a, b, tol=TOL_CORDE):
    """Ellipse discrétisée (sens trigonométrique), n tel que l'erreur de corde <= tol (contrôlé)."""
    for n in range(16, 400, 4):
        th = np.linspace(0, 2 * np.pi, n, endpoint=False)
        P = np.c_[cx + a * np.cos(th), cy + b * np.sin(th)]
        # erreur max : milieu de chaque corde vs point de l'ellipse au paramètre médian
        thm = th + np.pi / n
        M = np.c_[cx + a * np.cos(thm), cy + b * np.sin(thm)]
        C = (P + np.roll(P, -1, 0)) / 2
        if np.max(np.hypot(*(M - C).T)) <= tol:
            return P.tolist(), n
    raise RuntimeError("ellipse")


def gabarit(libelle, poly, longueur, largeur, origine, source, confiance, trous=None, derive_de=None,
            notes=None, construction=None, famille="fleche", couleur="blanc"):
    P = [[r4(x), r4(y)] for x, y in poly]
    g = {"libelle": libelle, "famille": famille, "couleur": couleur,
         "longueur_m": longueur, "largeur_m": largeur,
         "origine": origine,
         "polygone": P}
    if trous:
        g["trous"] = [[[r4(x), r4(y)] for x, y in t] for t in trous]
    a = aire(P) + sum(aire(t) for t in (g.get("trous") or []))
    xs = [p[0] for p in P]
    ys = [p[1] for p in P]
    g["aire_m2"] = round(a, 4)
    g["n_sommets"] = len(P) + sum(len(t) for t in (g.get("trous") or []))
    g["boite"] = {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)]}
    if construction:
        g["construction"] = construction
    if derive_de:
        g["derive_de"] = derive_de
    g["source"] = source
    g["confiance"] = confiance
    if notes:
        g["notes"] = notes
    return g


ORIG_FLECHE = "milieu du pied de la tige (y = 0), x latéral positif à droite, y dans le sens de circulation"
SRC_B2 = {"texte": IISR + ", annexe B.2 « Flèches directionnelles » (art. 115-3 C)", "page": 62, "url": IISR_URL,
          "methode": "sommets calculés depuis les cotes du schéma (0,15 / 0,70 / 2,00 / 4,00 / 0,50 / 0,35 / 0,25 / 2,25 / 2,60)"}
SRC_B3 = {"texte": IISR + ", annexe B.3 « Flèche bidirectionnelle » (art. 115-3 C)", "page": 63, "url": IISR_URL,
          "methode": "sommets calculés depuis les cotes du schéma (0,15 / 0,50 / 0,35 / 0,25 / 0,50 / 1,00 / 1,25 / 2,00 / 4,00)"}
SYM = "art. 115-3 C (p. 23) : « la flèche de tourne-à-gauche se déduit par symétrie de la flèche de tourne-à-droite »"

# ---------------------------------------------------------------- flèches directionnelles (cotes exactes)
TD = [[-0.075, 0], [0.075, 0], [0.075, 2.0], [0.35, 2.0], [0, 4.0], [-0.35, 2.0], [-0.075, 2.0]]
TAD = [[-0.075, 0], [0.075, 0], [0.075, 2.25], [0.575, 2.75], [0.575, 2.0], [0.925, 3.0], [0.575, 4.0],
       [0.575, 3.25], [-0.075, 2.6]]
TD_TAD = [[-0.075, 0], [0.075, 0], [0.075, 0.75], [0.575, 1.25], [0.575, 0.5], [0.925, 1.5], [0.575, 2.5],
          [0.575, 1.75], [0.075, 1.25], [0.075, 2.0], [0.35, 2.0], [0, 4.0], [-0.35, 2.0], [-0.075, 2.0]]

# ---------------------------------------------------------------- flèche de rabattement (B1)
R_D, YT_D, XB_D = 21.0, 1.155, -0.11     # bord droit : arc R 21, tangente verticale à y = 1,155, x = -0,11 au pied
R_G, YT_G, XB_G = 18.38, 0.72, -0.36     # bord gauche : vertical jusqu'à 0,72 puis arc R 18,38
XMIN_D = XB_D - (R_D - math.sqrt(R_D ** 2 - YT_D ** 2))
Y_ENCOCHE, Y_CASSURE = 3.92, 4.12
POINTE, BARBE_G, BARBE_D = [0.50, 6.00], [-0.24, 4.50], [0.26, 3.50]
bord_d, n_d = echantillonner_arc(0.0, Y_ENCOCHE, XMIN_D, R_D, YT_D)
bord_g, n_g = echantillonner_arc(YT_G, Y_CASSURE, XB_G, R_G, YT_G)
RAB_D = [[XB_G, 0.0]] + bord_d + [BARBE_D, POINTE, BARBE_G] + bord_g[::-1]
# bord_d commence à (XB_D, 0) ; bord_g[::-1] finit à (XB_G, 0.72) puis fermeture sur (XB_G, 0)
assert abs(bord_d[0][0] - XB_D) < 1e-9 and abs(bord_g[0][0] - XB_G) < 1e-9
ENCOCHE = bord_d[-1]
CASSURE = bord_g[-1]

# ---------------------------------------------------------------- triangles « cédez-le-passage » (D7)
def triangle_cedez(base, longueur, trait, bandeau):
    """Pointe à l'origine (côté véhicules qui arrivent), base à y = longueur ; trait mesuré perpendiculairement aux côtés."""
    k = (base / 2) / longueur                         # demi-largeur par mètre
    off = trait * math.sqrt(1 + k * k)                 # décalage horizontal équivalent au trait perpendiculaire
    y_haut = longueur - bandeau
    y_pointe_int = off / k
    ext = [[0, 0], [base / 2, longueur], [-base / 2, longueur]]
    xi = k * y_haut - off
    trou = [[0, y_pointe_int], [-xi, y_haut], [xi, y_haut]]   # sens horaire
    return ext, trou, y_pointe_int


TRI60, TRI60_T, TRI60_YP = triangle_cedez(1.00, 2.00, 0.10, 0.50)
TRI60P, TRI60P_T, TRI60P_YP = triangle_cedez(2.00, 6.00, 0.15, 1.00)

# ---------------------------------------------------------------- figurine vélo (D1)
velo = json.load(open(VELO, encoding="utf-8"))
corps = max(velo, key=lambda r: r["n_brut"])       # le plus long contour = corps + tête
roue_g, n_e = ellipse(0.15, 0.275, 0.15, 0.275)
roue_d, _ = ellipse(0.65, 0.275, 0.15, 0.275)
# repère : origine au milieu du bas de la boîte (x de -0,40 à 0,40), y vers le haut de la figure = sens de circulation
dec = lambda P: [[x - 0.40, y] for x, y in P]
VELO_CORPS, VELO_RG, VELO_RD = dec(corps["anneau"]), dec(roue_g), dec(roue_d)

# ---------------------------------------------------------------- éléments de damiers
def rect(lx, ly):
    return [[-lx / 2, -ly / 2], [lx / 2, -ly / 2], [lx / 2, ly / 2], [-lx / 2, ly / 2]]


gab = {}
gab["TD"] = gabarit("tout droit", TD, 4.00, 0.70, ORIG_FLECHE, SRC_B2, "haute",
                    notes="tige 0,15 x 2,00 ; tête triangulaire 0,70 x 2,00")
gab["TAD"] = gabarit("tourne-à-droite", TAD, 4.00, 1.00, ORIG_FLECHE, SRC_B2, "haute",
                     notes="branche à 45° (largeur perpendiculaire 0,354), tête 0,35 x 2,00 dont le dos est à 0,50 à droite de la tige ; encoches à 0,25 de part et d'autre de la pointe")
gab["TAG"] = gabarit("tourne-à-gauche", miroir(TAD), 4.00, 1.00, ORIG_FLECHE, {"texte": SYM, "page": 23, "url": IISR_URL},
                     "haute", derive_de={"gabarit": "TAD", "transformation": "symétrie x -> -x (ordre des sommets inversé)"})
gab["TD_TAD"] = gabarit("tout droit + tourne-à-droite", TD_TAD, 4.00, 1.275, ORIG_FLECHE, SRC_B3, "haute",
                        notes="branche à 45° de y 0,75-1,25 (bord bas) à 1,25-1,75 (bord haut) ; tête droite de y 0,50 à 2,50, pointe à x = 0,925, y = 1,50")
gab["TD_TAG"] = gabarit("tout droit + tourne-à-gauche", miroir(TD_TAD), 4.00, 1.275, ORIG_FLECHE,
                        {"texte": SYM.replace("tourne-à-gauche » se déduit par symétrie de la flèche de « tourne-à-droite",
                                              "tourne-à-gauche et direct » se déduit par symétrie de la flèche « tourne-à-droite et direct"),
                         "page": 23, "url": IISR_URL}, "haute",
                        derive_de={"gabarit": "TD_TAD", "transformation": "symétrie x -> -x (ordre des sommets inversé)"})
cons_rab = {
    "pied": {"x": [XB_G, XB_D], "largeur": 0.25, "cote": "0,36 et 0,11 depuis l'axe"},
    "bord_droit": {"type": "arc", "rayon": R_D, "tangente_verticale_y": YT_D, "x_tangente": r4(XMIN_D),
                   "x_pied": XB_D, "de_y": 0.0, "a_y": Y_ENCOCHE, "segments": n_d,
                   "lecture": "la cote R = 21 est horizontale à y = 1,155 : tangente verticale en ce point, arc passant par x = -0,11 au pied"},
    "bord_gauche": {"type": "vertical puis arc", "x": XB_G, "vertical_jusqu_a_y": YT_G, "rayon": R_G,
                    "a_y": Y_CASSURE, "segments": n_g,
                    "lecture": "vertical jusqu'à 0,72 puis arc R 18,38 (RMS 1,5 cm sur le schéma contre 2,6 cm pour un arc tangent en 0,72 et passant par -0,36 au pied)"},
    "tete": {"pointe": POINTE, "barbe_gauche": BARBE_G, "barbe_droite": BARBE_D,
             "encoche": [r4(ENCOCHE[0]), Y_ENCOCHE], "cassure": [r4(CASSURE[0]), Y_CASSURE],
             "cotes_y_iisr": {"barbe_droite": 3.50, "encoche": 3.92, "cassure": 4.12, "barbe_gauche": 4.50, "pointe": 6.00},
             "x_mesures": "pas de cote horizontale pour la tête : x de la pointe et des barbes mesurés sur l'image native du schéma B1 (197,5 px/m ; ajustement de droites sur le contour, résidu RMS ≤ 3 mm) : pointe 0,50 (intersection des bords à y = 5,98), barbe gauche -0,24 (y = 4,48), barbe droite 0,26 (y = 3,49) ; l'encoche (0,041 ; 3,92) tombe exactement sur l'arc R 21 (mesure 0,041), la cassure sur l'arc R 18,38 (mesure -0,048 à y = 4,09)",
             "incertitude_m": 0.02},
    "tolerance_corde_m": TOL_CORDE,
}
gab["RAB_D"] = gabarit("rabattement vers la droite", RAB_D, 6.00, r4(POINTE[0] - XB_G),
                       "intersection de l'axe de la voie (ou de la chaussée, ou de la ligne d'annonce) et de la ligne de référence perpendiculaire ; x positif du côté du rabattement, y dans le sens de circulation",
                       {"texte": IISR + ", annexe B.1 « Flèche de rabattement » (art. 115-3 B)", "page": 61, "url": IISR_URL,
                        "methode": "arcs et cotes verticales du schéma ; x de la tête mesurés sur l'image native"},
                       "moyenne", construction=cons_rab,
                       notes="largeur = boîte (pied à -0,36, pointe à +0,50) ; le pied fait 0,25 m ; à cheval sur la ligne d'annonce (route à 2 voies) ou dans l'axe de la voie supprimée")
gab["RAB_G"] = gabarit("rabattement vers la gauche", miroir(RAB_D), 6.00, r4(POINTE[0] - XB_G), "comme RAB_D, x positif à droite",
                       {"texte": "symétrie de B.1 (flèche dessinée pour un rabattement à droite)", "page": 61, "url": IISR_URL},
                       "moyenne", derive_de={"gabarit": "RAB_D", "transformation": "symétrie x -> -x (ordre des sommets inversé)"})
SRC_D7 = {"texte": IISR + ", annexe D.7 « Présignalisation au sol du cédez-le-passage » (art. 117-4 B)", "page": 79, "url": IISR_URL}
lect_trait = ("trait mesuré perpendiculairement aux côtés (lecture retenue : la cote est portée entre deux traits parallèles au côté) ; "
              "lecture horizontale : pointe intérieure à {:.3f} au lieu de {:.3f}")
gab["CEDEZ_V60"] = gabarit("triangle cédez-le-passage, V ≤ 60 km/h", TRI60, 2.00, 1.00,
                           "pointe du triangle (côté des véhicules qui arrivent), y vers la base (sens de circulation) ; base parallèle à la ligne T'2",
                           SRC_D7, "moyenne", trous=[TRI60_T], famille="symbole",
                           notes="base 1,00, longueur 2,00, trait 0,10, bandeau de base 0,50 ; " + lect_trait.format(0.10 / 0.25, TRI60_YP))
gab["CEDEZ_V60P"] = gabarit("triangle cédez-le-passage, V > 60 km/h", TRI60P, 6.00, 2.00,
                            "comme CEDEZ_V60", SRC_D7, "moyenne", trous=[TRI60P_T], famille="symbole",
                            notes="base 2,00, longueur 6,00, trait 0,15, bandeau 1,00 ; " + lect_trait.format(0.15 / (1 / 6), TRI60P_YP))
gab["VELO"] = gabarit("figurine vélo", VELO_CORPS, 1.28, 0.80,
                      "milieu du bas de la boîte 0,80 x 1,28 (bas des roues), y vers le haut de la figure = sens de circulation",
                      {"texte": IISR + ", annexe D.1 « Figurine pour voie cyclable » (art. 118-1)", "page": 66, "url": IISR_URL,
                       "methode": "image native de l'annexe (grille 8 x 13 cases de 0,10 m ; 520 px/m en x, 491,5 px/m en y) : lignes de grille effacées, isovaleur à mi-chemin fond/blanc (marching squares), Douglas-Peucker 4 mm ; roues = ellipses exactes 0,30 x 0,55"},
                      "moyenne", trous=None, famille="symbole",
                      notes="polygone = corps + tête (une seule composante) ; roues dans 'parties' ; demi-taille autorisée (homothétie 1/2 : 0,40 x 0,64) ; incertitude du tracé ±5 mm")
gab["VELO"]["parties"] = {
    "roue_arriere": {"polygone": [[r4(x), r4(y)] for x, y in VELO_RG], "ellipse": {"centre": [-0.25, 0.275], "demi_axes": [0.15, 0.275]}},
    "roue_avant": {"polygone": [[r4(x), r4(y)] for x, y in VELO_RD], "ellipse": {"centre": [0.25, 0.275], "demi_axes": [0.15, 0.275]}},
    "tolerance_corde_m": TOL_CORDE, "segments_ellipse": n_e,
    "aire_totale_m2": round(aire(VELO_CORPS) + aire(VELO_RG) + aire(VELO_RD), 4),
}
_tous = VELO_CORPS + VELO_RG + VELO_RD
gab["VELO"]["boite"] = {"x": [r4(min(p[0] for p in _tous)), r4(max(p[0] for p in _tous))],
                        "y": [r4(min(p[1] for p in _tous)), r4(max(p[1] for p in _tous))],
                        "note": "boîte de la figure complète (corps, tête, roues)"}
gab["VELO"]["aire_m2"] = gab["VELO"]["parties"]["aire_totale_m2"]
gab["VELO"]["n_sommets"] = len(VELO_CORPS) + len(VELO_RG) + len(VELO_RD)
gab["DAMIER_BUS"] = gabarit("carré de damier bus / TC", rect(1.00, 1.00), 1.00, 1.00, "centre du carré", {
    "texte": IISR + ", art. 118-3 D (carrés blancs de 0,80 m à 1,20 m de côté)", "page": 51, "url": IISR_URL},
    "haute (dimension) / faible (disposition)", famille="damier",
    notes="côté paramétrable 0,80-1,20 (défaut 1,00) ; disposition en échiquier non cotée par l'IISR : voir zones.damier_bus")
gab["PAVE_CHRONOVELO"] = gabarit("pavé jaune Chronovélo (traversée cyclable)", rect(0.70, 0.37), 0.37, 0.70, "centre du pavé ; y le long de la file",
                                 {"texte": "pratique du site, NON IISR : plan projet 2025 et charte Chronovélo (Grenoble-Alpes Métropole) ; mesuré sur marquages_2026.geojson (42 pavés : 0,700 x 0,371, pas 0,58 le long de la file, grand côté perpendiculaire à la file)",
                                  "page": None, "url": None}, "moyenne", famille="damier", couleur="jaune",
                                 notes="non normatif (hors IISR) ; pas 0,60 le long de la file (vide 0,23)")
gab["CARRE_TRAVERSEE_CYCLABLE"] = gabarit("carré blanc 0,50 de traversée cyclable", rect(0.50, 0.50), 0.50, 0.50, "centre du carré",
                                          {"texte": "pratique du site, NON IISR : 19 carrés relevés (0,50 x 0,50, pas 0,97-1,00)", "page": None, "url": None},
                                          "moyenne", famille="damier",
                                          notes="pas 1,00 le long de la traversée (carré 0,50 + vide 0,50)")

# ---------------------------------------------------------------- document
u_tab = [
    {"ligne": "axe ou délimitation de voies, continue", "modulation": "continue", "largeur_u": 2},
    {"ligne": "axe ou délimitation de voies en agglomération", "modulation": "T1, T'1 ou T3", "largeur_u": 2},
    {"ligne": "annonce de ligne continue", "modulation": "T3", "largeur_u": 2},
    {"ligne": "rive (en ville souvent la bordure seule)", "modulation": "T2", "largeur_u": 3},
    {"ligne": "rive aux abords de carrefour (à partir de la 1re flèche de rabattement)", "modulation": "T'3", "largeur_u": 3},
    {"ligne": "contour d'îlot, de TPC, de giratoire", "modulation": "continue", "largeur_u": 3},
    {"ligne": "bande cyclable, couloir bus, voie pour véhicules lents", "modulation": "T3", "largeur_u": 5},
    {"ligne": "couloir bus permanent ou à contresens", "modulation": "continue", "largeur_u": 5},
    {"ligne": "voie d'insertion / de décélération, séparation de courants", "modulation": "T2", "largeur_u": 5},
    {"ligne": "voies spécialisées ou affectées en agglomération", "modulation": "T3 (T2 5u si contrainte)", "largeur_u": 2},
    {"ligne": "accès riverain (interruption d'une continue sur ≈ 2,50 m)", "modulation": "T'2", "largeur_u": "2-3"},
    {"ligne": "stationnement (blanc ou bleu), interdiction (jaune)", "modulation": "T'2 ou continue", "largeur_u": 2},
]
for r in u_tab:
    if isinstance(r["largeur_u"], int):
        r["u5_m"] = round(r["largeur_u"] * 0.05, 3)
        r["u6_m"] = round(r["largeur_u"] * 0.06, 3)
        r["u3_piste_m"] = round(r["largeur_u"] * 0.03, 3)

mod = {}
for k, t, v, emploi in [
    ("T1", 3.00, 10.00, "axe / délimitation de voies (rase campagne)"),
    ("T'1", 1.50, 5.00, "axe / délimitation de voies en agglomération ; axe des pistes cyclables"),
    ("T2", 3.00, 3.50, "rive ; voies d'insertion et de décélération (5u)"),
    ("T'2", 0.50, 0.50, "lignes transversales (cédez, effet des feux, effet des passages piétons), accès riverains, stationnement"),
    ("T3", 3.00, 1.33, "annonce de ligne continue, bandes cyclables et couloirs bus (5u), voies affectées"),
    ("T'3", 20.00, 6.00, "rive aux abords des carrefours"),
    ("T4", 39.00, 13.00, "bande d'arrêt d'urgence"),
]:
    mod[k] = {"trait_m": t, "vide_m": v, "periode_m": round(t + v, 2), "plein_sur_vide": round(t / v, 3), "emploi": emploi}

doc = {
    "schema": "pj_specs/marquages_geometrie/1.0",
    "version": 1,
    "date": "2026-10-10",
    "role": "Géométrie normative des marques sur chaussée pour la fabrication V2 (Houdini pj_marquages, prototypes de symboles) : modulations, largeurs, lignes transversales, passages, hachures, zigzags, damiers et polygones exacts des flèches et symboles. L'aspect (couleurs, usure, rétroréflexion) reste dans peinture.json.",
    "source_principale": {"texte": IISR, "url": IISR_URL,
                          "articles": "113-1 (p. 5-7), 113-2 (p. 8-10), 114-5 (p. 15), 115-3 (p. 20-23), 117-2 (p. 37-38), 117-4 (p. 41-43), 118 (p. 44), 118-1 (p. 44-46), 118-3 (p. 50-51) ; annexes B1 (p. 61), B2 (p. 62), B3 (p. 63), C3 (p. 65), D1 (p. 66), D7 (p. 79)",
                          "valeur": "version consolidée à valeur documentaire (seuls font foi les textes publiés au JO)"},
    "repere": {
        "unites": "mètres",
        "gabarits": "repère local du gabarit : x latéral (positif à droite du sens de circulation), y longitudinal (sens de circulation), Z nul (posé à +3 mm sur la chaussée par pj_marquages)",
        "pose": "point d'insertion = origine du gabarit ; orientation = tangente de la voie (OpenDRIVE) au point ; repère de scène : local = Lambert-93 - O (917279.43, 6460289.98), z = NGF - 216.30",
        "polygones": "anneau extérieur dans le sens trigonométrique (aire > 0), trous dans le sens horaire, non fermés (dernier sommet ≠ premier), sommets en m arrondis au 0,1 mm",
        "discretisation": "arcs et ellipses : erreur de corde ≤ 1 mm",
    },
    "unite_u": {
        "valeurs_m": {"autoroute_chaussees_separees": 0.075, "route_grande_circulation": 0.06, "autres_routes": 0.05, "pistes_cyclables": 0.03},
        "regle": "u homogène sur un itinéraire",
        "site": "u non décidé (statut route à grande circulation inconnu) : défaut u = 0,05 ; u = 0,06 sur l'axe de Verdun (0,12 mesuré dominant, décision utilisateur n° 10) ; garder largeur_m mesurée quand elle existe",
        "largeurs_m": {"2u": {"u5": 0.10, "u6": 0.12}, "3u": {"u5": 0.15, "u6": 0.18}, "5u": {"u5": 0.25, "u6": 0.30}},
        "source": {"texte": IISR + ", art. 113-1 C (p. 7) et 113-2", "page": 7}, "confiance": "haute",
    },
    "largeurs_par_ligne": {"table": u_tab, "regles": [
        "avant un îlot, la ligne passe à 3u sur L/6",
        "espace non peint de 2u entre une ligne 3u et les hachures ou la bordure",
        "accès riverain : une ligne continue est interrompue sur ≈ 2,50 m par une T'2 2u (art. 114-5)"],
        "source": {"texte": IISR + ", art. 113-2 (p. 8-10), 114-5 (p. 15), 117-2 (p. 37-38)", "page": 8}, "confiance": "haute"},
    "modulations": {"table": mod,
                    "regle": "modulations (trait + vide) multiples ou sous-multiples de 13 m, sauf T'2 (1 m)",
                    "phase": "phase_m (abscisse du début du premier trait) portée par la description ; phasage sur les 155 tirets GAM quand ils existent",
                    "source": {"texte": IISR + ", art. 113-1 B (tableau p. 6, schéma p. 7)", "page": 6}, "confiance": "haute"},
    "lignes_transversales": {
        "STOP": {"modulation": "continue", "largeur_m": 0.50, "etendue": "toute la largeur des voies concernées", "jamais_sans": "panneau AB4",
                 "source": {"texte": IISR + ", art. 117-4 A", "page": 41}, "confiance": "haute"},
        "CEDEZ": {"modulation": "T'2", "largeur_m": 0.50, "motif": "pavés 0,50 x 0,50 espacés de 0,50", "jamais_sans": "panneau AB3a",
                  "triangle_amont": "gabarits.CEDEZ_V60 / CEDEZ_V60P (facultatif), pointe vers les véhicules qui arrivent",
                  "source": {"texte": IISR + ", art. 117-4 B", "page": 41}, "confiance": "haute"},
        "EFFET_FEUX": {"modulation": "T'2", "largeur_m": 0.15, "trait_m": 0.50, "vide_m": 0.50,
                       "etendue": "uniquement les voies commandées par le feu", "position": "en amont du feu ou du passage piéton s'il existe",
                       "note": "0,15 m de large et non 0,50 (les 23 lignes du site mesurent 0,50 x 0,15 : un tiret)",
                       "source": {"texte": IISR + ", art. 117-4 C et 118", "page": 42}, "confiance": "haute"},
        "EFFET_FEUX_MIXTE_TC": {"description": "T'2 0,15 + continue 0,15 espacées de 2u, la continue du côté du site TC",
                                "source": {"texte": IISR + ", art. 117-4", "page": 43}, "confiance": "haute"},
        "EFFET_PASSAGE_PIETONS": {"modulation": "T'2", "largeur_m": 0.15, "distance_amont_m": [2.0, 5.0],
                                  "source": {"texte": IISR + ", art. 117-4 F", "page": 43}, "confiance": "haute"},
        "CEDEZ_CYCLISTE": {"modulation": "0,25 / 0,25", "largeur_m": 0.25, "source": {"texte": IISR + ", art. 118-1", "page": 45}, "confiance": "moyenne"},
        "STOP_CYCLISTE": {"modulation": "continue", "largeur_m": 0.25, "source": {"texte": IISR + ", art. 118-1", "page": 45}, "confiance": "moyenne"},
        "GUIDAGE_CARREFOUR": {"description": "T'2 de 0,10 (tourne-à-gauche, baïonnette) ou de 0,15 doublée d'une continue 0,15 (carrefour complexe)",
                              "source": {"texte": IISR + ", art. 117-4", "page": 42}, "confiance": "moyenne"},
        "annonce_longitudinale": "STOP et cédez sur route à double sens sans îlot : continue 2u sur 10 à 20 m en amont (ou T3 si chaussée étroite)",
    },
    "passages_pietons": {
        "bande_largeur_m": 0.50, "intervalle_m": {"min": 0.50, "max": 0.80, "defaut_site": 0.50},
        "longueur_bande_m": {"ville_min": 2.50, "rase_campagne": [4.0, 6.0]},
        "orientation": "bandes parallèles à l'axe de la chaussée",
        "nombre_bandes": [{"largeur_roulable_m": [4, 6], "bandes": [3, 5]}, {"largeur_roulable_m": [6, 8], "bandes": [5, 7]},
                          {"largeur_roulable_m": [8, 10], "bandes": [6, 9]}, {"largeur_roulable_m": [10, 12], "bandes": [8, 11]},
                          {"largeur_roulable_m": [12, 14], "bandes": [9, 13]}],
        "interruption_lignes_m": 0.50,
        "regle_interruption": "le marquage axial et de délimitation des voies s'arrête à 0,50 m de part et d'autre du passage",
        "plateau_trapezoidal": "bandes prolongées de 0,50 m de part et d'autre du plateau",
        "coupure_refuge": "bandes interrompues au droit d'un refuge (dans la description : intervalles de coupure)",
        "site": "pas mesuré ≈ 1,00 (bande 0,50 + vide 0,50) sur l'ortho 2022 et le GAM ; bandes GAM 0,50 x 2,80-3,50",
        "source": {"texte": IISR + ", art. 118", "page": 44}, "confiance": "haute"},
    "hachures": {
        "bande_m": 0.50, "espacement_entre_paralleles_m": 1.35, "pas_perpendiculaire_m": 1.85,
        "inclinaison": "2 (parallèlement à la rive) pour 1 (perpendiculairement)",
        "angle_avec_rive_deg": round(math.degrees(math.atan(0.5)), 3),
        "le_long_de_la_rive_m": {"bande": round(0.50 / math.sin(math.atan(0.5)), 3), "vide": round(1.35 / math.sin(math.atan(0.5)), 3),
                                 "pas": round(1.85 / math.sin(math.atan(0.5)), 3),
                                 "note": "le schéma C3 arrondit à 1,12 + 3,00 (pas 4,12)"},
        "sens": "l'inclinaison ramène le conducteur vers la chaussée circulable",
        "espace_non_peint_u": 2, "contour": "continue 3u",
        "pointe_aplat_m": 0.30, "regle_pointe": "aplat blanc là où la largeur disponible est < 0,30 m",
        "reduction": "réduction homothétique possible pour les petits îlots",
        "source": {"texte": IISR + ", art. 117-2 A et schéma C3", "page": 37}, "confiance": "haute"},
    "chevrons": {"regle": "mêmes dimensions que les hachures, inclinées par rapport à la bissectrice, pointe vers le conducteur",
                 "site": "chevrons GAM 0,77 x 0,76, trait 0,12 (16 entités)",
                 "source": {"texte": IISR + ", art. 117-2", "page": 37}, "confiance": "haute"},
    "zigzag_bus": {
        "couleur": "jaune", "largeur_trait_u": 2, "angle_deg": 45, "amplitude_m": 2.50, "demi_periode_m": 2.50, "periode_m": 5.00,
        "longueur_min_m": 10.0, "extremites": "trait perpendiculaire à la bordure de 2,50 m à chaque extrémité (le motif commence et finit en sommet)",
        "longueur": "multiple de 5,00 m (site : 30,00 et 34,97 m = 6 et 7 périodes)",
        "lecture": "amplitude à l'axe du trait, depuis la bordure ; emprise = 2,50 + u (site : 2,55-2,58 m, trait 0,12)",
        "source": {"texte": IISR + ", art. 118-3 C et schéma", "page": 51}, "confiance": "haute"},
    "zones": {
        "damier_bus": {"carre_m": {"min": 0.80, "max": 1.20, "defaut": 1.00}, "couleur": "blanc", "gabarit": "DAMIER_BUS",
                       "disposition": "échiquier sur la largeur de la voie TC, 2 rangées alternées (pratique courante ; disposition non cotée par l'IISR)",
                       "emploi": "traversée d'un carrefour ou d'une voie TC, début de voie réservée",
                       "source": {"texte": IISR + ", art. 118-3 D", "page": 51}, "confiance": "faible (disposition)"},
        "damier_chronovelo": {"gabarit": "PAVE_CHRONOVELO", "pas_m": 0.60, "pave_m": [0.70, 0.37], "couleur": "jaune",
                              "disposition": "une file de chaque côté de la traversée cyclable, grand côté perpendiculaire à la file",
                              "source": {"texte": "pratique du site (plan projet 2025, charte Chronovélo), NON IISR", "page": None}, "confiance": "moyenne", "normatif": False},
        "carres_traversee_cyclable": {"gabarit": "CARRE_TRAVERSEE_CYCLABLE", "pas_m": 1.00, "carre_m": 0.50, "couleur": "blanc (jaune sur la traversée SW)",
                                      "source": {"texte": "pratique du site, NON IISR", "page": None}, "confiance": "moyenne", "normatif": False},
    },
    "cycles": {
        "u_m": 0.03, "axe_piste": "continue 2u (0,06) ou T'1 2u", "rive_piste": "3u (0,09)",
        "bande_cyclable": "T3 5u ; début/fin : trait oblique 5u coupé de 0,50 m en son milieu",
        "bandes_traversee": "homothétie 1/2 des bandes piétonnes : 0,25 m, espacées de 0,40 (min 0,25)",
        "figurine": "gabarits.VELO (0,80 x 1,28 ; demi-taille 0,40 x 0,64 autorisée)",
        "fleches_velo": "flèches directionnelles à l'homothétie 1/2 (2,00 m)",
        "sas_velo": "deux lignes d'effet des feux T'2 0,15 distantes de 3 à 5 m, figurine dans l'axe de chaque voie",
        "doubles_chevrons": "autorisés, aucune cote officielle",
        "source": {"texte": IISR + ", art. 118-1 et annexe D1", "page": 45}, "confiance": "haute"},
    "symboles_a_vectoriser": {
        "PMR": {"boite_m": {"limite": [0.50, 0.60], "limite_petit": [0.25, 0.30], "centre_place": [1.00, 1.20]}, "statut": "à vectoriser (annexe sans contour exploitable ici)", "source": {"texte": IISR + ", art. 118-2 C", "page": 48}},
        "recharge_electrique": {"boite_m": [[0.60, 0.30], [0.30, 0.15]], "statut": "à vectoriser", "source": {"texte": IISR + ", art. 118-2 C", "page": 48}},
        "chiffres_30_50": {"hauteur_caractere_m": "≥ 1,50 si V ≤ 50 ; 4 (3 min) si V > 50", "statut": "à vectoriser (annexes D3-D6, images)", "source": {"texte": IISR + ", art. 118-7, annexes D3-D6", "page": 70}},
        "BUS_TRAM": {"statut": "à vectoriser (lettres art. 118-7)", "source": {"texte": IISR + ", art. 118-3 E", "page": 51}},
    },
    "homotheties": {"autoroute": round(4 / 3, 4), "velo": 0.5,
                    "regle": "flèches directionnelles x 4/3 sur autoroutes et routes à chaussées séparées à carrefours dénivelés ; x 1/2 pour les voies cyclables (art. 118-1)"},
    "implantation_fleches": {
        "directionnelles": ["au milieu de chaque voie, toutes dans un même profil en travers",
                            "3 par voie (2 en agglomération si la place manque), interdistance constante",
                            "la dernière au plus près de la ligne d'arrêt ou du point de divergence",
                            "dès qu'une voie est affectée, toutes les voies adjacentes sont équipées",
                            "types autorisés à l'exclusion de tout autre : TD, TAD, TAG, TD_TAD, TD_TAG"],
        "rabattement": {
            "nombre": "3 (2 en agglomération si la longueur manque)",
            "transversal": "à cheval sur la ligne d'annonce (route à 2 voies) ; dans l'axe de la voie supprimée (3 voies et plus)",
            "premiere": "à L/2 en amont du début de la ligne oblique (réduction de voies, rétrécissement)",
            "L_m": [39, 78, 117, 156, 195, 234],
            "interdistances_m": [{"L": 234, "i1": 91, "i2": 78, "d_continue": 65}, {"L": 195, "i1": 78, "i2": 65, "d_continue": 52},
                                 {"L": 156, "i1": 65, "i2": 52, "d_continue": 39}, {"L": 117, "i1": 52, "i2": 39, "d_continue": 26},
                                 {"L": 78, "i1": 39, "i2": 26, "d_continue": 13}],
            "note": "L = 39 : ligne du tableau illisible dans l'extraction (26 / 13) ; correspondance V15 -> L mal alignée dans l'extraction (valeurs L sûres) ; en ville, ligne T3 de longueur L sans flèches possible à faible vitesse",
            "source": {"texte": IISR + ", art. 115-3 A et B", "page": 21}, "confiance": "moyenne"},
        "source": {"texte": IISR + ", art. 115-3 C", "page": 23}, "confiance": "haute"},
    "gabarits": gab,
    "ecarts_site": {
        "fleches_gam": "les gabarits GAM / plan projet du site sont plus étroits que l'IISR (TD+TAD 1,10 contre 1,275 ; TAG 0,69-0,92 contre 1,00) : on pose les gabarits IISR sauf preuve photo contraire (décision utilisateur n° 10)",
        "largeur_T3": "T3 à 0,12 (xodr, 130 lignes) ou 0,15 (63 tirets) : harmonisation à décider ; la spec ne tranche pas",
        "velo_site": "symbole vélo mesuré 1,32 x 0,69 (IISR 1,28 x 0,80)",
    },
    "historique": [{"version": 1, "date": "2026-10-10",
                    "contenu": "création V2 : modulations, u, transversales, passages, hachures, zigzag, damiers, 13 gabarits polygonaux (flèches B1-B3, triangles D7, figurine D1 vectorisée, éléments de damiers) ; contrôles de simplicité, d'orientation et de dimensions"}],
}
json.dump(doc, open(SORTIE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("écrit", SORTIE)
for k, g in gab.items():
    print(f"{k:26s} L {g['longueur_m']:5.3f} W {g['largeur_m']:5.3f}  n {g['n_sommets']:3d}  aire {g['aire_m2']:.4f}  boite {g['boite']}")
