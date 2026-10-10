# -*- coding: utf-8 -*-
"""Génère assets/specs/bordures_elements.json : compléments de bordures.json pour la fabrication en éléments."""
import json
import math
import sys

SORTIE = sys.argv[1]
B = json.load(open("D:/ClaudeCode_RoadCreation/assets/specs/bordures.json", encoding="utf-8"))
P = B["profils"]

CELTYS = "Celtys, catalogue « Bordures – Travaux publics » (hellopro, 8 p.) : https://www.hellopro.fr//documentation/pdf_prod/0/4/0/36050_9cb0dc8651512a6c9ced73c97a4dac56_6058040.pdf"
SEPA = "Sepa (groupe Leonhart), fiches techniques CS1 / CS2 / CS3, éd. 01/01/2017 (NF EN 1340, NF P98-340/CN) : https://www.hellopro.fr//documentation/pdf_prod/8/0/1/1590519_0f3b266202a9e5e84c6b1229e21e1fa9_6058108.pdf"
ARRETE = "arrêté du 15 janvier 2007 (accessibilité de la voirie), art. 1, 5°"
PHOTOS_U = "photos utilisateur 1.png (bordure basse et abaissé d'entrée), 2.png (éléments béton ~1 m, joints, BRF), 3.png (bordure autour d'un lit de gravier), 4.webp (bordures calcaire autour d'un îlot pavé) — conversation du 2026-10-10, hors dépôt"


def r4(v):
    return round(float(v) + 0.0, 4)


def arrondi(cx, cy, r, a0, a1, n):
    return [[r4(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n))), r4(cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))] for k in range(n + 1)]


def pose(contour, tv):
    return [[x, r4(y + tv)] for x, y in contour]


# ---------------------------------------------------------------- profils complémentaires
# TU : 25 x 16, arête avant haute arrondie r ≈ 0,03 (dessin Celtys p. 2 lu à 8x : arc de 3,0 x 2,8 cm)
tu = [[0.0, 0.0]] + arrondi(0.03, 0.13, 0.03, 180, 90, 4) + [[0.25, 0.16], [0.25, 0.0]]
# AC1 : bordure-caniveau 35 x 18 (12 côté chaussée) ; sommets lus sur le dessin Celtys p. 2 (27,3 px/cm)
ac1 = [[0.0, 0.0], [0.0, 0.104], [0.015, 0.12], [0.1325, 0.110], [0.139, 0.1125], [0.144, 0.122], [0.153, 0.131],
       [0.224, 0.18], [0.35, 0.18], [0.35, 0.0]]
# CS3 : 250, 165 / 140, chanfrein 15 x 15 à 45° côté chaussée (Sepa)
cs3 = [[0.0, 0.0], [0.0, 0.15], [0.015, 0.1635], [0.25, 0.14], [0.25, 0.0]]

profils_comp = {
    "TU": {"famille": "T (bordure basse à tête large, îlots et fosses d'arbres)", "section_cm": "25 x 16", "base": 0.25, "H": 0.16,
           "rayon_arete": 0.03, "vue_courante": [0.03, 0.10], "poids_kg_ml": 91,
           "contour": tu, "pose_exemple": {"vue_m": 0.06, "translation_v_m": -0.10, "contour_pose": pose(tu, -0.10),
                                            "lecture": "origine = pied de la face vue au niveau de la chaussée ; v = 0 = chaussée"},
           "elements_m": [1.00, 0.16], "quart_de_rond": "TU_R25",
           "nb_points": len(tu), "source_cotes": CELTYS + " : dessin p. 2 (25 x 16, arête arrondie r ≈ 3 cm mesurée), tableau p. 7 (91 kg)",
           "confiance": "moyenne (rayon d'arête mesuré sur le dessin ; vue courante a priori)"},
    "AC1": {"famille": "A (bordure-caniveau monobloc, franchissable)", "section_cm": "35 x 18 (12 côté chaussée)", "base": 0.35, "H": 0.18,
            "vue_courante": [0.06, 0.07], "poids_kg_ml": 119,
            "contour": ac1, "fil_d_eau": {"u": 0.1325, "v": 0.110},
            "pose_exemple": {"vue_m": 0.06, "translation_v_m": -0.12, "contour_pose": pose(ac1, -0.12),
                             "lecture": "origine = arête côté chaussée au niveau de la chaussée (u = 0) ; dessus de la partie bordure à +0,06, fil d'eau à -0,01"},
            "nb_points": len(ac1), "source_cotes": CELTYS + " : dessin p. 2 lu à 8x (sommets ±3 mm), tableau p. 7 (35 x 18, 119 kg)",
            "confiance": "moyenne (sommets lus sur le dessin, bec de fil d'eau simplifié)"},
    "CS3": {"famille": "caniveau simple pente", "section_cm": "25 x 14/16,5", "largeur": 0.25, "h_cote_chaussee": 0.165, "h_cote_bordure": 0.14,
            "pente_dessus": "25 mm sur 250 (10 %) vers la bordure", "chanfrein_mm": [15, 15],
            "contour": cs3, "pose": "u = 0 côté chaussée, u = 0,25 contre la bordure",
            "pose_exemple": {"translation_v_m": -0.165, "contour_pose": pose(cs3, -0.165), "lecture": "origine = arête côté chaussée au niveau de la chaussée"},
            "longueur_element_m": 0.992, "nb_points": len(cs3), "source_cotes": SEPA + " : fiche CS3 (longueur 992 mm)", "confiance": "haute"},
}
quarts = {
    "TU_R25": {"profil": "TU", "rayon_exterieur_m": 0.25, "angle_deg": 90, "H": 0.16,
               "construction": "révolution de 90° du contour TU autour de l'axe vertical u = 0,25 (arrière) : face vue = arc de rayon 0,25, arrière = l'axe (quart de disque plein)",
               "source": CELTYS + " : « Bordure TU R 25 » (photo p. 2)", "confiance": "haute"},
    "I1_R25": {"profil": "I1", "rayon_exterieur_m": 0.25, "angle_deg": 90, "construction": "révolution de 90° du contour I1 de bordures.json autour de u = 0,25",
               "source": CELTYS + " : « Bordure I1 R 25 » (p. 3)", "confiance": "haute"},
    "I2_R25": {"profil": "I2", "rayon_exterieur_m": 0.25, "angle_deg": 90, "construction": "révolution de 90° du contour I2 autour de u = 0,25",
               "source": CELTYS + " : « Bordure I2 0,16 R 25 » (p. 3)", "confiance": "haute"},
    "usage": "nez d'îlot arrondi R 0,25 : 2 quarts de rond dos à dos (demi-cercle) entre les deux files droites ; pas de joint de coupe",
}
pieces_courbes = {
    "profils": ["T2", "T3"],
    "rayons_m": [0.5, 1.2, 1.4, 1.6, 1.8, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
    "longueur": "mesurée sur l'arc extérieur ; élément courbe d'angle 1,00/R rad (R ≥ 1 m) ou quart de cercle (R 0,5)",
    "construction": "balayage du contour sur un arc de rayon R (face vue sur l'arc), abouts radiaux",
    "choix": "rayon catalogue le plus proche du rayon local de la face vue ; écart de rayon ≤ 10 % sinon éléments droits courts",
    "source": "hellopro (Aumusse : T2 courbes R 0,5 et 3 m) ; autre gamme R 1,20-2,00 au pas de 0,20 puis 3-9 m au pas de 1 (inventaire normes V2)",
    "confiance": "moyenne",
}

# ---------------------------------------------------------------- corrections de profils existants (paramètres, pas de duplication)
corr = {
    "CS1": {"chanfrein_cote_chaussee_mm": [15, 15], "remplace_sommets": {"de": [[0.0, 0.115], [0.005, 0.12]], "par": [[0.0, 0.105], [0.015, 0.1185]]},
            "longueur_element_m": 0.992, "source": SEPA + " : fiche CS1 (chanfrein 15 x 15 à 45°, longueur 992 mm)",
            "note": "bordures.json met un chanfrein de 5 mm (sans source) ; à reporter dans bordures.json par le lot en cours"},
    "CS2": {"chanfrein_cote_chaussee_mm": [15, 15], "remplace_sommets": {"de": [[0.0, 0.13], [0.005, 0.135]], "par": [[0.0, 0.12], [0.015, 0.1335]]},
            "longueur_element_m": 0.994, "source": SEPA + " : fiche CS2 (chanfrein 15 x 15, cote 994 sur le dessin, « longueur 992 mm » dans l'en-tête)",
            "note": "idem CS1"},
    "T4": {"statut": "non vérifié (un revendeur cite 20 x 30 x 100) ; ne pas utiliser sans preuve photo", "source": "inventaire normes V2"},
    "T3": {"note": "le tableau Celtys p. 7 imprime 15 x 25 mais 108 kg/ml et le dessin coté donnent 17 x 28 (contour de bordures.json correct)"},
}
for k in ("CS1", "CS2"):
    c = P[k]["contour"]
    assert [list(map(float, p)) for p in c[1:3]] == corr[k]["remplace_sommets"]["de"], (k, c)

# ---------------------------------------------------------------- arêtes par profil
def ar(avant, arriere="chanfrein 5 x 5 mm (arête vive cassée, pratique de moulage)", about="chanfrein 3 x 3 mm sur les arêtes d'about de la tête et de la face vue", note=None):
    d = {"arete_avant_haute": avant, "arete_arriere_haute": arriere, "aretes_about": about}
    if note:
        d["note"] = note
    return d


aretes = {
    "T1": ar("arrondi r 0,015 (déjà dans le contour de bordures.json)"),
    "T2": ar("arrondi r 0,02 (contour)"),
    "T3": ar("arrondi r 0,02 (contour)"),
    "T2_bateau": ar("arrondi convexe de 4 cm (contour)"),
    "A1": ar("chanfrein 8 x 6 cm (contour)", "chanfrein 5 x 5 mm (contour)"),
    "A2": ar("chanfrein 8 x 6 cm (contour)", "chanfrein 5 x 5 mm (contour)"),
    "P1": ar("arrondi r 0,02 (contour)", "chanfrein 3 x 3 mm"),
    "P2": ar("tête ronde (contour)", "tête ronde (contour)"),
    "P3": ar("chanfrein 3 x 3 mm (contour rectangulaire)", "chanfrein 3 x 3 mm"),
    "I1": ar("chanfrein 1 cm + dessus galbé (contour)", "arête vive cassée 3 mm"),
    "I2": ar("chanfrein 1 cm + dessus galbé (contour)", "arête vive cassée 3 mm"),
    "IL": ar("chanfrein 1 cm + dessus galbé (contour)", "arête vive cassée 3 mm"),
    "QUAI_BUS": ar("petit chanfrein de tête (contour)"),
    "PAVES_GRANIT": ar("arrondis 4-15 mm (contour)", "arrondis 4-15 mm (contour)", "pavés : joints de 12 mm, pas d'about chanfreiné",
                       "pavés instanciés (0,14 + joint 0,012), rotation et hauteur ± 5 mm (bordures.json)"),
    "CS1": ar("chanfrein 15 x 15 mm à 45° côté chaussée (correction Sepa)", "arête vive côté bordure (contre la face vue)"),
    "CS2": ar("chanfrein 15 x 15 mm à 45° côté chaussée (correction Sepa)", "arête vive côté bordure"),
    "CS3": ar("chanfrein 15 x 15 mm à 45° côté chaussée (contour)", "arête vive côté bordure"),
    "CC1": ar("chanfrein 5 mm des deux côtés (contour)", "chanfrein 5 mm (contour)"),
    "CC2": ar("arête vive (contour)", "arête vive (contour)"),
    "TU": ar("arrondi r 0,03 (contour)"),
    "AC1": ar("chanfrein 15 x 16 mm côté chaussée (contour)"),
    "regle_generale": "les arrondis et chanfreins de la face vue et de la tête viennent du contour ; on ajoute seulement les petites cassures d'arêtes (about, arrière), qui rendent les joints lisibles en « V » comme sur les photos utilisateur 1 et 2 ; l'about d'un élément de coupe est scié net (sans chanfrein)",
    "fabrication": "pj_bordure_prototypes : extrusion du contour sur la longueur réelle, puis PolyBevel des arêtes listées (profil d'arrondi 3 segments pour r ≥ 10 mm, 1 segment pour les chanfreins) ; normales lissées aux arrondis, dures ailleurs",
    "source": CELTYS + " ; " + SEPA + " ; " + PHOTOS_U,
}

# ---------------------------------------------------------------- règle de pas selon le rayon
def fleche(L, R):
    return L * L / (8 * R)


table_pas = [
    {"R_min_m": 12.0, "R_max_m": None, "element_m": 1.00, "fleche_max_mm": round(fleche(1.0, 12) * 1000, 1)},
    {"R_min_m": 3.0, "R_max_m": 12.0, "element_m": 0.50, "fleche_max_mm": round(fleche(0.5, 3) * 1000, 1)},
    {"R_min_m": 1.3, "R_max_m": 3.0, "element_m": 0.33, "fleche_max_mm": round(fleche(0.33, 1.3) * 1000, 1),
     "alternative": "pièce courbe T2/T3 au rayon catalogue le plus proche (préférée si disponible)"},
    {"R_min_m": 0.75, "R_max_m": 1.3, "element_m": 0.25, "fleche_max_mm": round(fleche(0.25, 0.75) * 1000, 1),
     "alternative": "pièce courbe R 1,20 ; éléments de 0,16 pour TU / I1 / I2"},
    {"R_min_m": None, "R_max_m": 0.75, "element_m": "pièce courbe R 0,5 (T2/T3) ou quart de rond R 0,25 (TU, I1, I2)", "fleche_max_mm": None},
]

doc = {
    "schema": "pj_specs/bordures_elements/1.0",
    "version": 1,
    "date": "2026-10-10",
    "role": "Compléments de bordures.json pour fabriquer les bordures en ÉLÉMENTS préfabriqués (pj_bordure_prototypes, pj_bordure_pose) : longueurs et joints, pas selon le rayon, arêtes, épaufrures, jitter, abaissés et chartières, BEV, caniveaux en éléments, matériaux, teintes et aspect. Les profils restent dans bordures.json et sont cités par leur nom ; seuls TU, AC1, CS3 et les quarts de rond, absents de bordures.json, sont définis ici.",
    "references": {
        "profils": "assets/specs/bordures.json (profils, regles_affectation, abaisses.chartieres_gam, caniveaux)",
        "bev": "assets/specs/mobilier.json (modeles[asset = bev_podotactile])",
        "peinture": "assets/specs/peinture.json (couleurs.blanc, usure)",
        "materiaux": "assets/specs/materiaux_sol.json",
        "donnees_site": "recon/out/paquet_jardin/package/donnees/relief/{bordures_hauteurs.geojson, relief_zones_2026.geojson, heightmap_3025_10cm.png}",
        "photos_utilisateur": PHOTOS_U,
    },
    "repere": {
        "profil": "celui de bordures.json : u perpendiculaire (0 = face vue, positif vers l'arrière), v vertical (0 = dessous du bloc), contour fermé horaire, premier point = coin avant bas",
        "element": "s le long de la bordure (0 au début de l'élément, sens de la polyligne), u, v ; la polyligne d'arête avant est orientée trottoir à gauche (sinon pj_bordure_pose l'inverse)",
        "pivot_prototype": "milieu de l'élément (s = L/2), u = 0 (face vue), v = 0 (dessous du bloc) ; axes du prototype : X = s, Y = u, Z = v (USD Z-up, m) ; UE : X = s·100, Y = -u·100 (repère main gauche, même convention que la scène)",
        "z_instance": "z_dessous = z_chaussee_au_pied + vue - H, avec z_chaussee_au_pied = fil d'eau (z_fil_eau_2021_m de bordures_hauteurs.geojson) hors zones de travaux 2025, sinon modèle 2026 (heightmap_3025_10cm + h_modele_2026_m) ; jamais les maillages v1 (jusqu'à +1,77 m au-dessus du MNT 2026)",
        "conversion": "local = Lambert-93 - O (917279.43, 6460289.98), z = NGF - 216.30 : une seule fonction de conversion (recon/pcg)",
    },
    "element": {
        "pas_nominal_m": 1.00,
        "longueur_reelle_m": 0.994,
        "joint_mm": {"defaut": 6, "min": 3, "max": 8, "parametre_description": "joint_mm (par bordure)"},
        "justification": "fiches Sepa : CS1 et CS3 de 992 mm, CS2 coté 994 mm, posés au pas de 1,00 m, soit des joints de 6 à 8 mm ; bordures.json annonçait 3-5 mm sans source. Défaut 6 mm (élément 0,994 m), paramétrable ; à recaler par FFT des joints sur les photos (piste P)",
        "longueurs_m": {"courant": 1.00, "court": 0.50, "coupe_chantier": [0.33, 0.25], "petit_element": 0.16,
                        "notes": "0,50 « existe aussi en 0,50 ml » (T2, Celtys) ; 0,16 pour TU, I1, I2 ; 0,33 / 0,25 = éléments recoupés sur chantier"},
        "longueur_reelle": "longueur nominale - joint_mm (ex. 0,494 ; 0,324 ; 0,244 ; 0,154)",
        "tolerance_nf": "NF EN 1340 : longueur ±1 % (±4 mm sous 0,4 m, ±10 mm au-dessus de 1 m) ; faces vues ±3 % ; en rendu : jitter de longueur ±1 mm seulement",
        "joint_rendu": "vide de joint_mm sur toute la hauteur vue ; fond de joint en mortier gris foncé en retrait de 3-5 mm (ou vide sombre) ; jamais de joint peint en texture",
        "prototypes": "par profil : éléments 0,994 / 0,494 / 0,324 / 0,244 / 0,154 m (0,154 pour TU, I1, I2), 3 variantes d'épaufrures chacun, chartières gauche/droite, quarts de rond, pièces courbes T2/T3 aux rayons catalogue ; export /Game/PJ/Lib/Bordures/SM_<profil>_<L>_v<n> (Nanite)",
        "source": SEPA + " ; " + CELTYS,
        "confiance": "haute (longueurs), moyenne (joint retenu)",
    },
    "regle_pas_rayon": {
        "rayon": "rayon local de la face vue, estimé sur la polyligne lissée (cercle par 3 points espacés de 1 m, médiane glissante sur 3 m)",
        "critere": "flèche de corde s = L²/(8R) ≤ 10,5 mm pour un élément droit posé en corde",
        "table": table_pas,
        "joint_en_coin": "élément droit sur une courbe : le joint vaut joint_mm sur la face vue ; côté arrière (profondeur b), il s'ouvre de b·L/R si l'arrière est côté convexe ; si l'arrière est côté concave et b·L/R > joint, raccourcir L (ligne suivante de la table) ou tailler l'about en biais (coupe radiale)",
        "pieces_courbes": pieces_courbes,
        "source": "inventaire normes V2 (règle déduite de la flèche de corde) ; architecture V2 §1.4",
        "confiance": "moyenne (règle de pratique, pas une norme)",
    },
    "pose": {
        "points_durs": ["chartière / abaissé (début et fin de la partie abaissée)", "angle vif (déviation > 30° sur moins de 0,5 m)",
                        "nez d'îlot (quart de rond)", "changement de profil ou de matériau", "extrémités de la ligne",
                        "blocs CHARTIERE du GAM (21, bordures.json abaisses.chartieres_gam)"],
        "file": "chaque file part d'un point dur avec des éléments entiers et se termine par un élément de coupe contre le point dur suivant",
        "element_de_coupe": {"longueur": "reste - joint_mm", "min_m": 0.20,
                             "si_reste_court": "si la coupe ferait moins de 0,20 m : remplacer les deux derniers éléments par deux coupes égales de (pas + reste)/2 - joint",
                             "about": "scié net (pas de chanfrein d'about), arêtes vives"},
        "phase": "phase_m (abscisse du premier joint) prise sur l'observé (joints relevés sur photo, FFT des bandes de bordure) quand il existe ; sinon 0 au point dur de départ",
        "vue": "vue_m de l'intervalle de la description (arrondie au mm) ; profil choisi par bordures.json regles_affectation",
        "orientation": "X le long de la corde de l'élément (début -> fin), Z vertical ; tangage = pente du fil d'eau sur la corde ; pas de dévers au-delà du jitter",
        "contacts": "aucun interstice > 5 mm entre bordure et trottoir : pj_sol coupe le trottoir sur l'arête arrière (u = base) de l'élément posé",
    },
    "jitter": {
        "hauteur_mm": 2.0, "lacet_deg": 0.3, "lateral_mm": 1.0, "longueur_mm": 1.0, "roulis_deg": 0.15,
        "loi": "uniforme centrée ; graine = hash(id_bordure, index_element, version_regle) ; sorties identiques à l'octet",
        "correlation_hauteur": "composante lente corrélée sur 3-5 éléments (tassements, ±1,5 mm) + composante indépendante (±1 mm), total borné à ±2 mm",
        "exclusions": "pas de jitter de hauteur sur les éléments abaissés (vue 0,02 ± 0,005 imposée) ni sur les chartières",
        "source": "architecture V2 §1.4 ; photos utilisateur 1-4 (légers désaffleurements entre éléments)",
    },
    "aretes": aretes,
    "epaufrures": {
        "variantes": [
            {"id": "v0", "description": "élément intact"},
            {"id": "v1", "description": "une épaufrure d'angle (about, arête avant haute) : 15-30 mm de long, 5-10 mm de profondeur"},
            {"id": "v2", "description": "une épaufrure le long de l'arête avant haute (30-60 mm x 4-8 mm) et une petite d'angle"},
            {"id": "v3", "description": "deux ou trois épaufrures sur l'arête avant et un coin écorné (15-25 mm) côté arrière"},
        ],
        "repartition": {"neuf_2025": {"v0": 0.85, "v1": 0.12, "v2": 0.03, "v3": 0.0},
                        "ancien": {"v0": 0.45, "v1": 0.30, "v2": 0.18, "v3": 0.07}},
        "position": "surtout l'arête avant haute (pneus, chasse-neige) et les angles d'about ; jamais sur les faces enterrées",
        "fabrication": "soustraction booléenne de formes rocheuses bruitées (sphères déformées par bruit, ou fracture Voronoi) dans pj_bordure_prototypes ; 3 variantes v1-v3 par profil et longueur, sélection par l'attribut d'instance 'variante'",
        "source": "constat p2025_01_vercors-26 (analysis/paquet_jardin/constats_verifies.md : bordures claires en bon état) ; inventaire (épaufrures, mousses) ; photos utilisateur",
        "confiance": "moyenne (répartitions a priori)",
    },
    "abaisses": {
        "traversee": {
            "profil": "T2_bateau", "vue_m": 0.02, "tolerance_m": 0.005,
            "largeur": "largeur de la traversée (≥ 1,20 m ; 2-4 m sur le site), sans jitter de hauteur",
            "regle": ARRETE + " : ressaut ≤ 2 cm à bord arrondi ou chanfreiné (≤ 4 cm avec chanfrein à 1 pour 3) ; abaissé obligatoire à chaque traversée ; ressauts successifs espacés d'au moins 2,50 m",
            "chartieres": {
                "nombre": 2, "longueur_m": 1.00, "noms": ["CHARTIERE_GAUCHE", "CHARTIERE_DROITE"],
                "geometrie": "élément de raccord : la vue passe linéairement de la vue courante (profil courant posé à sa vue) à 0,02 sur 1,00 m ; loft entre le contour courant et le contour T2_bateau posés au même pied ; face vue verticale, tête en pente",
                "pente_tete": "(vue_courante - 0,02) / 1,00, ex. 12 % pour une T2 de vue 0,14",
                "source": CELTYS + " (raccords T2/A2 gauche et droit, 1,00 m, 73 kg) ; blocs CHARTIERE du GAM",
            },
            "rampe_trottoir": "pente ≤ 5 % (8 % sur ≤ 2 m, 12 % sur ≤ 0,50 m) : pj_sol",
            "donnees": "relief_zones_2026.geojson : 13 zones 'traversee_bordure_abaissee' (hauteur_m 0,02) ; 192 tronçons traversee=True de bordures_hauteurs.geojson ; 21 CHARTIERE du GAM ; la v1 n'abaissait pas ces bordures",
            "confiance": "haute",
        },
        "entree_charretiere": {
            "profil": "T2_bateau (A2 si la bordure courante est A2)", "vue_m": {"min": 0.02, "max": 0.04, "defaut": 0.03},
            "chartieres": "comme la traversée : 2 x 1,00 m (vue courante -> vue d'entrée)",
            "detection": "contact entre une bordure et un polygone acces_riverain (15 sur le site) dans la description",
            "src_si_non_observe": "a_priori:bordures_elements.abaisses.entree_charretiere",
            "source": "pratique (inventaire normes V2) ; photo utilisateur 1 (abaissé d'entrée en vue de quelques cm)",
            "confiance": "moyenne",
        },
        "raccord_quai_bus": {"longueur_m": [1.0, 2.0], "pente_max": "5 %", "profil": "raccords de quai A/B 35 x 29,5 (Celtys) vers la T2",
                             "source": CELTYS, "confiance": "moyenne"},
    },
    "bev": {
        "reference": "mobilier.json, modèle bev_podotactile (dalles 0,40 x 0,40 ou 0,42 x 0,60, plots Ø 25 mm h 5 mm, entraxe 75 mm en quinconce)",
        "profondeur_m": {"defaut": 0.42, "standard_nf": 0.5875, "observe": [0.40, 0.45]},
        "recul_m": 0.50,
        "lecture_recul": "0,50 m entre l'arête avant haute (nez) de la bordure abaissée et le bord avant de la bande (mobilier.json : première ligne de plots à 0,50 ; écart de 3 cm sans effet visible)",
        "longueur": "toute la largeur de la partie abaissée à 0,02 (chartières exclues)",
        "pose": "affleurante, bord parallèle à l'arête avant ; dalles de 0,40 m avec joints de 3 mm",
        "materiau": "bev_podotactile (manifeste_cc0.json)",
        "source": "NF P98-351 ; mobilier.json ; photos Panoramax 2025-08-31 ab4cfacd r01_c02 et 2025-05-18 31d16b8e r01_c03 (profondeur 0,40-0,45)",
        "confiance": "haute (règle), moyenne (profondeur)",
    },
    "caniveaux": {
        "profils": {"CS1": {"longueur_reelle_m": 0.992}, "CS2": {"longueur_reelle_m": 0.994}, "CS3": {"longueur_reelle_m": 0.992}},
        "pas_m": 1.00, "joint_mm": {"defaut": 6, "max": 8},
        "pose": "u = 0 côté chaussée (arête chanfreinée au niveau de l'enrobé), u = largeur contre la face vue de la bordure ; le bord bas côté bordure forme le fil d'eau ; la vue de la bordure se mesure depuis ce fil d'eau",
        "joints": "alignés sur ceux de la bordure par défaut (decalage_joints_m = 0), paramétrable (0,5 = joints alternés)",
        "materiau": "beton_bordure_gris, salissure 0,5-0,8 concentrée au fil d'eau (sable, feuilles, traînées sombres)",
        "site": "138,8 m de SOL_CANIVEAU GAM (12 lignes, data/sites/paquet_jardin/vector/gam_topo_sol_caniveau_lin.geojson) : CS2 au pied des T2 de Verdun ; caniveau à fente le long du quai SE (hors catalogue)",
        "source": SEPA,
        "confiance": "haute (géométrie), moyenne (affectation CS2)",
    },
    "profils_complementaires": profils_comp,
    "quarts_de_rond": quarts,
    "corrections_profils": corr,
    "materiaux": {
        "beton_gris": {"materiau_id": "beton_bordure_gris", "albedo_cible": [0.354, 0.369, 0.336],
                       "source": "manifeste_cc0.json beton_bordure (photo 2374105b 2025-05-18) ; la v1 utilisait 0,66, soit 1,8 x trop clair", "confiance": "haute"},
        "beton_clair": {"materiau_id": "beton_bordure_clair", "albedo_cible": [0.45, 0.455, 0.43],
                        "source": "a priori : bordures « presque blanches » des îlots du Vercors (constat p2025_01_vercors-26) ; photo utilisateur 2 (rapport tête de bordure / enrobé 1,94 x enrobé vieilli 0,24 = 0,47)",
                        "confiance": "faible"},
        "granit": {"materiau_id": "granit_bordure", "albedo_cible": [0.362, 0.353, 0.299],
                   "source": "cible de paves_granit (manifeste) ; aucune bordure granit relevée sur le site", "confiance": "faible"},
        "calcaire": {"materiau_id": "calcaire_bordure", "albedo_cible": [0.46, 0.43, 0.36],
                     "source": "a priori, photo utilisateur 4 ; texture Travertine009 (manifeste calcaire_bordure)", "confiance": "faible"},
        "peint_blanc": {"materiau_id": "beton_bordure_gris + couche peinture_blanc", "peinture": "peinture.json couleurs.blanc (en service : albédo 0,60), usure 2-3, couverture 0,6-0,8 de la tête et de la face vue",
                        "usage": "nez et bordures d'îlots rendus visibles de nuit (IISR 7e partie, art. 117-2 B), refuges en D de Verdun SO (à vérifier en 2026)",
                        "confiance": "moyenne"},
        "variation_par_element": {"albedo_pct": 4.0, "teinte_ab": 1.0,
                                  "loi": "décalage uniforme par élément (graine) : les éléments d'une même file diffèrent légèrement, comme sur les photos utilisateur 2 et 4",
                                  "donnee_instance": "teinte"},
    },
    "aspect": {
        "salissure": {"plage": [0.0, 1.0], "defaut": {"neuf_2025": 0.15, "ancien": 0.45},
                      "rendu": "assombrissement x (1 - 0,35·s) concentré au pied (fil d'eau) et sur la tête côté chaussée, gradient vertical sur la face vue"},
        "mousse_joints": {"plage": [0.0, 1.0], "defaut": {"neuf_2025": 0.0, "ancien": 0.3},
                          "rendu": "mousse vert sombre dans les joints (5-20 mm) et au pied des faces nord ; masque de joints issu de s"},
        "herbe_joints": {"plage": [0.0, 1.0], "defaut": {"neuf_2025": 0.0, "ancien": 0.2},
                         "rendu": "touffes PCG (PG_Joints) : probabilité par joint = 0,5 x herbe_joints, hauteur 3-15 cm (octobre)",
                         "source": "constat p2025_05_360-32 (herbes dans les joints des îlots)"},
        "usure_arete_mm": {"neuf_2025": 0, "ancien": [1, 3], "rendu": "arrondi d'usure ajouté à l'arête avant (variante de prototype ou normal map)"},
        "donnees_instance": "points/bordures.json : cd = [usure, salissure, mousse_joints, herbe_joints, teinte] ; variante = v0..v3 ; graine",
    },
    "controles_phase1": [
        "joints visibles tous les 1,00 m (0,50 si R < 12 m) et élément de coupe en fin de file",
        "vue de 0,02 ± 0,005 m aux traversées ; rampe ≤ 5 %",
        "aucun interstice > 5 mm entre bordure et trottoir",
        "remplissage d'îlot 3 à 5 cm sous le dessus de la bordure (materiaux_sol.json, remplissages)",
        "sorties identiques à l'octet sur 2 exécutions",
    ],
    "historique": [{"version": 1, "date": "2026-10-10",
                    "contenu": "création V2 : élément 0,994 / joint 6 mm, pas selon le rayon, arêtes, épaufrures, jitter, abaissés et chartières, BEV, caniveaux en éléments, TU / AC1 / CS3 / quarts de rond, corrections CS1/CS2 (chanfrein 15 mm), matériaux et aspect"}],
}
json.dump(doc, open(SORTIE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# contrôles : contours simples et horaires, références de profils
def aire(c):
    return 0.5 * sum(c[i][0] * c[(i + 1) % len(c)][1] - c[(i + 1) % len(c)][0] * c[i][1] for i in range(len(c)))
for k, v in profils_comp.items():
    a = aire(v["contour"])
    xs = [p[0] for p in v["contour"]]
    ys = [p[1] for p in v["contour"]]
    print(f"{k:4s} aire {abs(a) * 1e4:6.1f} cm²  sens {'horaire' if a < 0 else 'TRIGO !'}  boîte {max(xs) - min(xs):.3f} x {max(ys) - min(ys):.3f}  poids estimé {abs(a) * 2300:.0f} kg/ml (catalogue {v.get('poids_kg_ml', '-')})")
ref = {"T2", "T3", "T2_bateau", "A2", "P1", "I1", "I2", "CS1", "CS2"}
assert ref <= set(P), ref - set(P)
assert set(aretes) - {"regle_generale", "fabrication", "source"} <= set(P) | set(profils_comp), set(aretes) - set(P) - set(profils_comp)
print("écrit", SORTIE)
