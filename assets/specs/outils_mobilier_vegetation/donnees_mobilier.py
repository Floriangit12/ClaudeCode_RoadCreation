"""Fiches du mobilier réellement présent (carrefour Paquet Jardin, état octobre 2026).

Cotes : mesures sur les tuiles Panoramax 1000x1000 natives (projection équirectangulaire
5760x2880 : 16 px par degré, horizon à y = 440 dans les tuiles de la rangée r01 et à y = 1440 en
coordonnées image) avec hauteur de caméra 1,6-1,9 m (GoPro Max sur toit de voiture, calée sur une
tête R11v de 0,95-1,0 m), distances données par le GPS de la photo et la position de l'objet
(atelier objets / OSM) ; recoupées avec le LiDAR HD 2021 (hauteurs de mâts), l'ortho 5 cm 2022,
OSM 2026, le plan projet 2025 et les dimensions normalisées. Chaque cote porte sa méthode.
Gabarits : élévations 2D (m) utilisées par planches_controle.py ; plan « YZ » = vue de côté
(+Y à droite), « XZ » = vue de face (+X à droite, l'observateur regarde vers −Y).
"""
from commun import tuile

T_BC579 = "2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460"
T_734A = "2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a"
T_31D1 = "2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3"
T_1149 = "2024-05-01_1149e115-2c88-48fc-a908-bbf633abaa72"
T_A275 = "2023-03-18_a275b2ea-ca5a-4224-b4ad-f335ddbfe981"
T_5C0D = "2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a"
T_A1FF = "2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0"
T_2AB4 = "2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c"
T_AB4C = "2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c"
T_F8D9 = "2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb"
T_2374 = "2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8"
T_9834 = "2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433"
T_E540 = "2025-05-18_e540bf1d-c8ab-4f0a-ae4e-19d7ea07ddc3"
T_9FC8 = "2025-05-18_9fc8ba46-9a08-483b-92f7-ad37798f9330"
T_D888 = "2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe"
T_FFC2 = "2026-07-28_ffc2e8ac-50a1-422d-8a27-6514243a81e5"
T_DED0 = "2026-07-28_ded07efa-75ec-4289-972a-56c9e98a1309"
T_E5D7 = "2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5"
T_119D = "2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c"
T_DD2A = "2024-05-01_dd2a9c8c-6044-453b-9377-32ddad938138"   # V2 : arceaux vélo du quai NO sous ciel couvert
T_B401 = "2024-05-01_b4013696-1d02-4d94-9a89-456a56298e04"   # V2 : feuilles de la haie (laurier-cerise)
T_0508 = "2026-07-28_05089869-a37a-40f8-a2bc-cd764ec7d7f9"   # V2 : allée de L'Horloge (magnolias / grand feuillu voisin)
T_7A18 = "2025-05-18_7a182db7-30c9-4964-a0d1-b8b50e80fb42"   # V2 : houppier du Populus alba (Verdun NE)


def trap(h, z0, z1, d0, d1, c):
    return {"t": "trap", "h": h, "z0": z0, "z1": z1, "d0": d0, "d1": d1, "c": c}


def rect(h0, z0, h1, z1, c):
    return {"t": "rect", "h0": h0, "z0": z0, "h1": h1, "z1": z1, "c": c}


def line(p, w, c):
    return {"t": "line", "p": p, "w": w, "c": c}


def circ(h, z, r, c):
    return {"t": "circ", "h": h, "z": z, "r": r, "c": c}


def poly(p, c):
    return {"t": "poly", "p": p, "c": c}


def _lanterne(h, z, L=0.75, e=0.13, c="gris_aluminium"):
    return [poly([[h - L / 2, z], [h + L / 2, z + 0.02], [h + L / 2 - 0.05, z + e], [h - L / 2 + 0.08, z + e]], c)]


def _ganivelle():
    g = [rect(-1.0, 0, -0.93, 1.25, "bois_creosote"), rect(0.93, 0, 1.0, 1.25, "bois_creosote")]
    x = -0.9
    while x < 0.92:
        g.append(rect(x, 0.05, x + 0.035, 1.12, "chataignier_grise"))
        x += 0.09
    for z in (0.25, 0.6, 0.95):
        g.append(line([[-1.0, z], [1.0, z]], 0.006, "galvanise_vieilli"))
    return g


def _cloture():
    g = [rect(-1.28, 0, -1.22, 1.85, "vert_6005"), rect(1.22, 0, 1.28, 1.85, "vert_6005")]
    for z in (0.05, 0.6, 1.2, 1.8):
        g.append(line([[-1.22, z], [1.22, z]], 0.012, "vert_6005"))
    x = -1.2
    while x <= 1.21:
        g.append(line([[x, 0.05], [x, 1.8]], 0.006, "vert_6005"))
        x += 0.2
    return g


def _arceau(h0=0.0, L=0.65, H=0.82, r=0.08):
    """V2 : arceau anthracite 0,65 x 0,82 m, angles de rayon ≈ 0,08 m (photo 2024-05-01 dd2a9c8c r01_c00)."""
    a = L / 2
    return [line([[h0 - a, 0], [h0 - a, H - r], [h0 - a + r * 0.3, H - r * 0.3], [h0 - a + r, H], [h0 + a - r, H],
                  [h0 + a - r * 0.3, H - r * 0.3], [h0 + a, H - r], [h0 + a, 0]], 0.05, "anthracite_7016")]


CANDELABRE_DIFFUSION = ("Les cotes de fût/lanterne sont des estimations photo (pas de catalogue fabricant) ; la hauteur "
                        "est mise à l'échelle par instance dans la scène (sz = hauteur LiDAR / hauteur de l'asset).")

FICHES = [
    # ------------------------------------------------------------------ éclairage
    {
        "asset": "candelabre_double_crosse", "categorie_lib": "eclairage",
        "designation": "Candélabre routier de l'avenue de Verdun : fût cylindro-conique galvanisé, double crosse en T (bras opposés), 2 lanternes plates LED",
        "classement_atelier": {"type": "lampadaire", "sous_type": "mât à crosse", "nb_crosses": 2},
        "etat_2026": "présent", "confiance": "haute (modèle) / moyenne (positions des 2 mâts déplacés en 2025)", "priorite": 1,
        "quantite": {"estimation": 7, "min": 6, "max": 9,
                     "methode": "atelier objets (LiDAR 2021 : crosses de part et d'autre du mât) : 6 mâts réf. 2352-2358 sur le séparateur planté de Verdun SO + réf. 2350 (îlot NO du cœur, vu en T sur la photo 2024-05-01 alors que l'atelier le classe en crosse simple) ; le catalogue des besoins (≈ 12) comptait aussi les mâts à crosse simple de Verdun NE"},
        "dimensions_m": {"hauteur_totale_nominale": 12.05, "hauteur_lidar_2021": "10,7-12,4 (médiane 12,15)",
                         "fut_diametre_pied": 0.20, "fut_diametre_tete": 0.09, "hauteur_raccord_crosses": 11.75,
                         "portee_horizontale_par_crosse": 2.4, "remontee_crosse_deg": 6,
                         "lanterne_LxlxH": [0.75, 0.32, 0.13], "inclinaison_lanterne_deg": "0-5",
                         "platine": [0.40, 0.40, 0.03], "trappe_de_visite": "0,30 x 0,10 à 0,6 m du sol, côté opposé à la chaussée"},
        "geometrie": [
            "fût tronconique lisse (16 segments suffisent), raccord en T soudé en tête",
            "2 crosses tubulaires Ø 0,076 m, droites, légèrement remontantes (≈ 6°), portée 2,4 m chacune ; +Y = crosse au-dessus de la chaussée principale, −Y = crosse au-dessus de la contre-allée / piste",
            "2 lanternes plates (boîtier fonte d'alu, vasque plane en verre vers le bas) fixées en bout de crosse",
            "option saisonnière/permanente : cadre de décoration lumineuse (fil de fer + guirlande, ≈ 1,2 x 2,0 m) fixé sur le fût à 4-7 m, vu en janvier, mai et août → présent toute l'année sur plusieurs mâts",
            "option : affiches de cirque (décals 0,4 x 0,6) collées sur le fût à 1,5-2,5 m",
        ],
        "gabarit_2d": {"plan": "YZ", "elements": [
            rect(-0.2, 0, 0.2, 0.03, "galvanise_vieilli"), trap(0, 0, 11.8, 0.20, 0.09, "galvanise_vieilli"),
            line([[0, 11.75], [2.4, 12.0]], 0.076, "galvanise_vieilli"), line([[0, 11.75], [-2.4, 12.0]], 0.076, "galvanise_vieilli"),
            *_lanterne(2.3, 11.9), *_lanterne(-2.3, 11.9)]},
        "materiaux": [
            {"partie": "fût, crosses, platine", "materiau": "acier galvanisé à chaud brut, patiné", "couleur": "galvanise_vieilli",
             "usure": "marbrures plus sombres, coulures sous les colliers, pied plus sale (0-0,5 m), traces de colliers de panneaux"},
            {"partie": "lanterne", "materiau": "fonte d'aluminium peinte", "couleur": "gris_aluminium"},
            {"partie": "vasque", "materiau": "verre plat", "note": "émissif LED 3000-4000 K (hypothèse) ; la nuit : photométrie routière type II, ≈ 10-15 klm par lanterne (ordre de grandeur, à remplacer par un IES si disponible)"},
        ],
        "cotes_mesurees": [
            {"grandeur": "hauteur totale", "valeur": "12,1-12,4 m sur Verdun SO (10,7 et 11,5 m pour les 2 mâts déplacés)", "methode": "LiDAR HD 2021 (atelier objets, hauteur_lidar_2021_m)"},
            {"grandeur": "écart entre lanternes", "valeur": "≈ 4,8 m (lanternes à t ≈ −6,4 et −11,2 m du repère de l'analyse verdun_so)", "methode": "ortho 5 cm 2022 (analyse verdun_so-34) ; portée 2,4 m par crosse"},
            {"grandeur": "proportions crosse/fût", "valeur": "envergure en T ≈ 0,4 x hauteur ; crosses quasi horizontales", "methode": "photo 2024-05-01 1149e115 r01_c02 (mât de l'îlot NO, ≈ 8-10 m de distance)"},
        ],
        "photos_reference": [tuile(T_1149, "r01_c02"), tuile(T_A275, "r00_c01"), tuile(T_31D1, "r01_c02")],
        "reference_normative": "NF EN 40 (candélabres d'éclairage public) ; NF EN 13201 (éclairage public, classes de performance)",
        "source_recommandee": "maison Houdini 22 (fût = Tube SOP conique, crosses = Sweep, lanterne = boîte chanfreinée) ; ≈ 2 500 triangles LOD0",
        "budget": {"triangles_lod0": 2500, "lod1": 800, "collision": "capsule sur le fût"},
        "pivot_orientation": "pivot au centre du pied du fût (z = 0 au sol fini) ; +Y = crosse côté chaussée principale",
        "notes": CANDELABRE_DIFFUSION,
    },
    {
        "asset": "candelabre_crosse_simple", "categorie_lib": "eclairage",
        "designation": "Candélabre à crosse simple (branche NE de Verdun, Vercors, abords du P+R) : même famille, un seul bras ≈ 2 m, lanterne plate",
        "classement_atelier": {"type": "lampadaire", "sous_type": "mât à crosse / mât à crosse (crosse longue)", "nb_crosses": 1},
        "etat_2026": "présent", "confiance": "moyenne (modèle exact de la branche NE vu de loin)", "priorite": 1,
        "quantite": {"estimation": 8, "min": 6, "max": 10,
                     "methode": "atelier objets : réf. 2341-2349 (Verdun NE, 5), 3153, 13624569647 (2026), lidar_VERC_E ; la réf. 2350, classée crosse simple par l'atelier, est comptée en double crosse (vue en T sur la photo 2024-05-01)"},
        "dimensions_m": {"hauteur_totale_nominale": 10.3, "hauteur_lidar_2021": "8,8-10,4 (médiane 10,3)",
                         "fut_diametre_pied": 0.18, "fut_diametre_tete": 0.085, "portee_horizontale_crosse": 2.1,
                         "remontee_crosse_deg": 8, "lanterne_LxlxH": [0.75, 0.32, 0.13]},
        "geometrie": ["fût tronconique galvanisé", "une crosse droite Ø 0,076 m remontante (≈ 8°), portée 2,1 m (photo : ≈ 0,22 x hauteur)",
                      "lanterne plate identique à candelabre_double_crosse", "option cadre lumineux et affiches comme candelabre_double_crosse"],
        "gabarit_2d": {"plan": "YZ", "elements": [
            rect(-0.18, 0, 0.18, 0.03, "galvanise_vieilli"), trap(0, 0, 9.95, 0.18, 0.085, "galvanise_vieilli"),
            line([[0, 9.9], [2.1, 10.2]], 0.076, "galvanise_vieilli"), *_lanterne(2.0, 10.1)]},
        "materiaux": [{"partie": "fût, crosse", "materiau": "acier galvanisé", "couleur": "galvanise_vieilli"},
                      {"partie": "lanterne", "materiau": "fonte d'aluminium", "couleur": "gris_aluminium"}],
        "cotes_mesurees": [
            {"grandeur": "hauteur", "valeur": "10,0-10,4 m (Verdun NE), 9,3 (réf. 3153), 8,8 (Vercors E)", "methode": "LiDAR HD 2021"},
            {"grandeur": "portée de crosse", "valeur": "≈ 0,22 x hauteur → ≈ 2,1-2,3 m", "methode": "photo 2024-08-24 5c0d1d39 r01_c03 (mât de gauche, crosse vue de profil)"},
        ],
        "photos_reference": [tuile(T_5C0D, "r01_c03"), tuile(T_734A, "r01_c03"), tuile(T_A1FF, "r01_c00")],
        "reference_normative": "NF EN 40",
        "source_recommandee": "maison Houdini (même réseau que candelabre_double_crosse, paramètre nb_crosses = 1)",
        "budget": {"triangles_lod0": 1800, "lod1": 600, "collision": "capsule"},
        "pivot_orientation": "pivot au pied ; +Y = crosse (vers la chaussée)",
        "notes": CANDELABRE_DIFFUSION,
    },
    {
        "asset": "candelabre_mat_droit_led", "categorie_lib": "eclairage",
        "designation": "Mât droit 6-9 m à lanterne LED plate en tête (Revirée, allée de L'Horloge, P+R, cheminements), plaque de numéro bleue",
        "classement_atelier": {"type": "lampadaire", "sous_type": "mât droit / mât (type inconnu)", "nb_crosses": 0},
        "etat_2026": "présent", "confiance": "haute", "priorite": 1,
        "quantite": {"estimation": 23, "min": 20, "max": 26,
                     "methode": "atelier objets : 27 mâts droits ou de type inconnu, moins 4 lanternes sodium (OSM lamp_type=high_pressure_sodium) → 23"},
        "dimensions_m": {"hauteur_totale_nominale": 8.0, "hauteurs_site": "6,0 (valeur par défaut OSM, 15 mâts) ; 7,0-9,1 mesurées (LiDAR) ; 10,1 (réf. 0525, à vérifier)",
                         "fut_diametre_pied": 0.15, "fut_diametre_tete": 0.076, "lanterne_LxlxH": [0.62, 0.30, 0.11],
                         "porte_a_faux_lanterne": 0.35, "inclinaison_lanterne_deg": "5-10 (relevée vers la voie)",
                         "plaque_numero": "autocollant bleu vertical ≈ 0,05 x 0,22 m, chiffres blancs (ex. « 0456 »), à ≈ 2,6 m"},
        "geometrie": ["fût cylindro-conique lisse, gris clair", "embout + lanterne LED plate (type « top » sur crosse courte de 0,3-0,4 m)",
                      "colliers de panneaux (B6a1, C13a, C113, AB3a selon les mâts : voir specs/panneaux.json)", "massif béton affleurant (anneau Ø 0,4 m)"],
        "gabarit_2d": {"plan": "YZ", "elements": [
            circ(0, 0.0, 0.2, "beton_clair"), trap(0, 0, 7.95, 0.15, 0.076, "galvanise_vieilli"),
            line([[0, 7.9], [0.35, 7.98]], 0.06, "galvanise_vieilli"), *_lanterne(0.3, 7.92, L=0.62, e=0.11),
            rect(-0.085, 2.5, -0.06, 2.72, "bleu_5010")]},
        "materiaux": [{"partie": "fût", "materiau": "acier galvanisé (ou thermolaqué gris clair)", "couleur": "galvanise_vieilli"},
                      {"partie": "lanterne", "materiau": "aluminium", "couleur": "gris_aluminium", "note": "LED 3000-4000 K"},
                      {"partie": "plaque de numéro", "materiau": "adhésif", "couleur": "bleu_5010", "note": "texte blanc"}],
        "cotes_mesurees": [
            {"grandeur": "hauteur", "valeur": "9,1 m (réf. 0456), 8,0-8,1 m (Revirée), 7,0 (parc NO)", "methode": "LiDAR HD 2021"},
            {"grandeur": "diamètre de pied", "valeur": "≈ 0,15 m", "methode": "photo 2026-07-28 f8d91bb1 r01_c04 (mât 0456 vu à ≈ 4 m, comparé au B6a1)"},
        ],
        "photos_reference": [tuile(T_F8D9, "r01_c04"), tuile(T_F8D9, "r01_c03"), tuile(T_5C0D, "r01_c04")],
        "reference_normative": "NF EN 40",
        "source_recommandee": "maison Houdini",
        "budget": {"triangles_lod0": 1200, "lod1": 400, "collision": "capsule"},
        "pivot_orientation": "pivot au pied ; +Y = côté lanterne (vers la voie éclairée)",
    },
    {
        "asset": "candelabre_mat_droit_shp", "categorie_lib": "eclairage",
        "designation": "Variante Revirée : mât droit ≈ 8 m, lanterne routière fermée à lampe sodium haute pression (lumière orangée 2000 K)",
        "classement_atelier": {"type": "lampadaire", "osm_lamp_type": "high_pressure_sodium"},
        "etat_2026": "présent (lanternes non vues de près)", "confiance": "faible (modèle de lanterne)", "priorite": 3,
        "quantite": {"estimation": 4, "min": 3, "max": 4, "methode": "OSM lamp_type=high_pressure_sodium : nœuds 9530354220, 9530354517, 12894141026, 12894130974"},
        "dimensions_m": {"hauteur_totale_nominale": 8.0, "fut": "identique à candelabre_mat_droit_led", "lanterne_LxlxH": [0.70, 0.30, 0.20]},
        "geometrie": ["fût de candelabre_mat_droit_led", "lanterne routière à vasque bombée (capot gris, vasque translucide), crosse courte 0,5 m"],
        "gabarit_2d": {"plan": "YZ", "elements": [
            trap(0, 0, 7.9, 0.15, 0.076, "galvanise_vieilli"), line([[0, 7.85], [0.5, 7.95]], 0.06, "galvanise_vieilli"),
            poly([[0.2, 7.85], [0.9, 7.88], [0.85, 8.05], [0.3, 8.05]], "gris_aluminium")]},
        "materiaux": [{"partie": "lanterne", "materiau": "aluminium + vasque polycarbonate", "couleur": "gris_aluminium", "note": "émission 2000 K (SHP)"}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "7,9-8,2 m", "methode": "LiDAR HD 2021 (analyse reviree_no-28)"}],
        "photos_reference": [],
        "source_recommandee": "maison (variante de candelabre_mat_droit_led : seule la lanterne change)",
        "budget": {"triangles_lod0": 1200},
        "pivot_orientation": "pivot au pied ; +Y = lanterne",
    },
    {
        "asset": "poteau_bois_reseau", "categorie_lib": "eclairage",
        "designation": "Poteau bois de réseau aérien (télécom / basse tension), brun, avec ferrures, câbles et affichettes",
        "classement_atelier": {"type": "poteau_reseau", "osm_material": "wood"},
        "etat_2026": "présent", "confiance": "haute (poteau NE) / moyenne (autres : bois ou acier brun)", "priorite": 2,
        "quantite": {"estimation": 2, "min": 1, "max": 5,
                     "methode": "1 confirmé (poteau_bois_NE : LiDAR 10,0 m + photo 119d9094) ; les 6 autres poteaux OSM sont en acier (material=steel) → asset mat_illumination_cable ; le catalogue des besoins (5) regroupait les deux familles"},
        "dimensions_m": {"hauteur_hors_sol": 10.0, "diametre_pied": 0.24, "diametre_tete": 0.16, "ferrures": "2-4 consoles + isolateurs ou pinces d'ancrage à 8,5-9,8 m"},
        "geometrie": ["fût bois rond légèrement conique, fentes de séchage verticales", "plaque d'identification métallique à 2 m",
                      "départs de câbles (Sweep de courbes caténaires, Ø 0,015-0,02 m, flèche 0,3-0,6 m) — à poser dans la scène, pas dans l'asset",
                      "affichettes et affiches de cirque (décals)"],
        "gabarit_2d": {"plan": "YZ", "elements": [trap(0, 0, 10.0, 0.24, 0.16, "bois_creosote"),
                                                  line([[-0.25, 9.6], [0.25, 9.6]], 0.05, "galvanise_vieilli"),
                                                  rect(-0.12, 1.9, 0.12, 2.15, "galvanise_vieilli")]},
        "materiaux": [{"partie": "fût", "materiau": "bois traité (créosote / sels), vieilli", "couleur": "bois_creosote"}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "10,0 m", "methode": "LiDAR HD 2021 (poteau_bois_NE)"}],
        "photos_reference": [tuile(T_119D, "r01_c00"), tuile(T_5C0D, "r01_c03"), tuile(T_9834, "r01_c02")],
        "source_recommandee": "maison Houdini (ou CARLA /Game/Carla/Static/Pole/PoweLine en retirant les traverses américaines)",
        "budget": {"triangles_lod0": 800},
        "pivot_orientation": "pivot au pied",
    },
    {
        "asset": "mat_illumination_cable", "categorie_lib": "eclairage",
        "designation": "Mât acier peint brun-orangé portant des câbles aériens transversaux (guirlandes, illuminations, réseau) ; certains avec bras horizontal porte-câbles",
        "classement_atelier": {"type": "poteau_reseau", "osm_material": "steel"},
        "etat_2026": "présent", "confiance": "moyenne", "priorite": 3,
        "quantite": {"estimation": 6, "min": 2, "max": 7, "methode": "OSM power/poteaux material=steel ×6 (atelier objets, 9 m par défaut) ; 2 vus avec bras porte-câbles (photos 2025-05-18)"},
        "dimensions_m": {"hauteur_hors_sol": 9.0, "diametre_pied": 0.22, "diametre_tete": 0.12, "bras_porte_cables": "option : longueur 4,0-5,0 m à ≈ 8,4 m, tube Ø 0,06 + tirant"},
        "geometrie": ["fût conique lisse peint brun, coulures de rouille", "variante A sans bras (fût seul + pinces d'ancrage)", "variante B avec bras horizontal + tirant oblique"],
        "gabarit_2d": {"plan": "YZ", "elements": [trap(0, 0, 9.0, 0.22, 0.12, "brun_8023"), line([[0, 8.4], [4.5, 8.4]], 0.06, "brun_8023"),
                                                  line([[0, 8.95], [3.6, 8.45]], 0.02, "brun_8023")]},
        "materiaux": [{"partie": "fût et bras", "materiau": "acier peint", "couleur": "brun_8023", "usure": "peinture farinée, rouille aux soudures"}],
        "cotes_mesurees": [{"grandeur": "silhouette", "valeur": "bras ≈ 0,5 x hauteur", "methode": "photo 2025-05-18 2374105b r01_c03 (mât brun et bras vers la chaussée)"}],
        "photos_reference": [tuile(T_2374, "r01_c03"), tuile(T_734A, "r01_c01"), tuile(T_31D1, "r01_c03")],
        "source_recommandee": "maison Houdini",
        "budget": {"triangles_lod0": 600},
        "pivot_orientation": "pivot au pied ; +Y = bras porte-câbles",
    },
    # ------------------------------------------------------------------ transport
    {
        "asset": "abri_bus_m_reso", "categorie_lib": "transport",
        "designation": "Abri voyageurs du réseau M (exploitant JCDecaux d'après OSM) : ossature anthracite, paroi arrière vitrée, toit mince légèrement cintré, panneau publicitaire (MUPI) double face en extrémité, plan/horaires, banc, distributeur de titres",
        "classement_atelier": {"type": "abri_bus", "prototype_atelier": "abri_bus_JCDecaux"},
        "etat_2026": "présent (2 quais refaits en 2025 ; modèle supposé identique à 2025)", "confiance": "haute (présence) / moyenne (modèle 2026)", "priorite": 1,
        "quantite": {"estimation": 2, "min": 2, "max": 2, "methode": "OSM 2025-10 (way 185326914) + plan projet 2025 (« Abri Bus » aux 2 quais)"},
        "dimensions_m": {"longueur_toit": 4.4, "profondeur_toit": 1.75, "hauteur_toit": 2.5, "hauteur_sous_toit": 2.25,
                         "modules": "3 travées de ≈ 1,40 m", "paroi_arriere_vitree": "h ≈ 2,05 m, de 0,10 à 2,15 m",
                         "mupi_extremite": {"affiche": [1.20, 1.76], "caisson_LxPxH": [1.35, 0.14, 2.30], "double_face": True},
                         "banc_integre": {"longueur": 1.5, "hauteur_assise": 0.45},
                         "debord_toit_avant": 0.25},
        "geometrie": [
            "toit : plaque mince (0,06-0,08 m) légèrement cintrée, rive avant amincie, gris clair translucide",
            "4 poteaux anthracite (profil 0,08 x 0,08) dont 2 en façade ouverte côté chaussée (+Y)",
            "paroi arrière en verre feuilleté clair (bandes blanches sérigraphiées anti-collision à ≈ 1,0 et 1,6 m)",
            "extrémité gauche (vue de la chaussée) : caisson MUPI double face perpendiculaire à la façade",
            "intérieur : banc (assise 1,5 m), cadre plan de réseau + horaires (0,8 x 1,2), poteau d'arrêt intégré à l'extrémité droite (voir poteau_arret_m_reso) ; distributeur de titres bleu/jaune contre la paroi (voir fiches_complementaires)",
        ],
        "gabarit_2d": {"plan": "XZ", "elements": [
            rect(-2.0, 0.10, 2.0, 2.15, "verre_abri"),
            rect(-2.08, 0, -2.0, 2.4, "anthracite_7016"), rect(-0.72, 0, -0.64, 2.4, "anthracite_7016"),
            rect(0.64, 0, 0.72, 2.4, "anthracite_7016"), rect(2.0, 0, 2.08, 2.4, "anthracite_7016"),
            poly([[-2.2, 2.38], [2.2, 2.38], [2.2, 2.44], [0, 2.50], [-2.2, 2.44]], "gris_aluminium"),
            rect(-2.2, 0.0, -2.08, 2.3, "noir_9005"), rect(-0.75, 0.42, 0.75, 0.47, "bois_banc"),
            rect(0.9, 0.9, 1.7, 2.1, "blanc_9016"),
            rect(2.12, 0, 2.2, 3.6, "anthracite_7016"), circ(2.16, 3.82, 0.17, "noir_9005")]},
        "materiaux": [
            {"partie": "ossature", "materiau": "acier/aluminium thermolaqué", "couleur": "anthracite_7016", "note": "RAL exact à confirmer (photos : gris anthracite)"},
            {"partie": "vitrages", "materiau": "verre feuilleté", "couleur": "verre_abri"},
            {"partie": "toit", "materiau": "verre ou polycarbonate sérigraphié gris", "couleur": "gris_aluminium"},
            {"partie": "MUPI", "materiau": "caisson aluminium + affiche rétroéclairée", "couleur": "noir_9005", "note": "texture d'affiche générique (pas de marque réelle)"},
        ],
        "cotes_mesurees": [
            {"grandeur": "emprise du toit", "valeur": "4,41 x 1,77 m", "methode": "polygone OSM way/185326914 (abri du quai SE, 2025-10)"},
            {"grandeur": "hauteur sous toit / hors tout", "valeur": "2,25-2,4 / 2,5-2,6 m", "methode": "photo 2025-05-18 bc579b89 r01_c03 : élévations angulaires (16 px/°) à ≈ 7,1-7,6 m ; personne debout ≈ 1,7 m pour contrôle"},
        ],
        "photos_reference": [tuile(T_BC579, "r01_c03"), tuile(T_734A, "r01_c01"), tuile(T_2374, "r01_c03")],
        "reference_normative": "arrêté du 15 janvier 2007 (accessibilité de la voirie) : espace d'attente, contraste des vitrages",
        "source_recommandee": "maison Houdini (formes simples) ; CARLA static.prop.busstop = silhouette proche seulement (couleurs et banc rouge à éviter)",
        "budget": {"triangles_lod0": 4500, "lod1": 1500, "collision": "boîtes (poteaux, paroi, toit)"},
        "pivot_orientation": "pivot au sol au milieu de la façade ouverte ; +Y = côté ouvert vers la bordure de quai ; +X le long du quai",
    },
    {
        "asset": "poteau_arret_m_reso", "categorie_lib": "transport",
        "designation": "Poteau d'arrêt du réseau M (SMMAG) : mât anthracite, disque « M » en tête, drapeau nominatif « La Revirée », boîtier des lignes (C1 : pastille jaune), cadre horaires",
        "classement_atelier": {"type": "poteau_arret", "prototype_atelier": "poteau_arret_bus"},
        "etat_2026": "présent", "confiance": "haute (modèle 2025) / faible (positions exactes 2026 aux quais refaits)", "priorite": 1,
        "quantite": {"estimation": 3, "min": 2, "max": 3, "methode": "1 en tête de chaque quai de Verdun (accolé à l'abri) + 1 poteau seul sur la Revirée (OSM node 13261073976, Flexo 42, horaires papier)"},
        "dimensions_m": {"hauteur_totale": 3.9, "mat_diametre": 0.09, "disque_M_diametre": 0.35, "centre_disque": 3.72,
                         "drapeau_nom": {"LxH": [0.65, 0.16], "centre_z": 3.40}, "boitier_lignes": {"LxHxP": [0.55, 0.40, 0.10], "centre_z": 2.75},
                         "cadre_horaires": {"LxH": [0.32, 0.45], "centre_z": 1.50}},
        "geometrie": ["mât rond anthracite", "disque noir « M » blanc (double face) en tête", "drapeau noir, texte blanc « La Revirée » (côté chaussée)",
                      "boîtier noir des lignes : pastille jaune « C1 » + codes de lignes (texture)", "cadre horaires A3 vers le quai"],
        "gabarit_2d": {"plan": "YZ", "elements": [
            trap(0, 0, 3.55, 0.09, 0.09, "anthracite_7016"), circ(0, 3.72, 0.175, "noir_9005"),
            rect(0.05, 3.32, 0.70, 3.48, "noir_9005"), rect(0.05, 2.55, 0.60, 2.95, "noir_9005"), circ(0.17, 2.82, 0.07, "jaune_1023"),
            rect(-0.36, 1.27, -0.05, 1.73, "blanc_9016")]},
        "materiaux": [{"partie": "mât", "materiau": "acier thermolaqué", "couleur": "anthracite_7016"},
                      {"partie": "disque, drapeau, boîtier", "materiau": "aluminium laqué + adhésifs", "couleur": "noir_9005", "note": "textures depuis la photo bc579b89 r01_c03 (à redessiner en vectoriel : logo M, « La Revirée », « C1 »)"}],
        "cotes_mesurees": [{"grandeur": "hauteur du disque / drapeau / boîtier", "valeur": "sommet ≈ 3,9-4,1 m ; drapeau 3,25-3,55 m ; boîtier 2,55-2,95 m ; disque Ø ≈ 0,33-0,35 m",
                            "methode": "photo 2025-05-18 bc579b89 r01_c03 (élévations angulaires, pied à ≈ 7,7-8,1 m)"}],
        "photos_reference": [tuile(T_BC579, "r01_c03")],
        "source_recommandee": "maison Houdini (textures redessinées)",
        "budget": {"triangles_lod0": 600},
        "pivot_orientation": "pivot au pied ; +Y = face du drapeau vers la chaussée",
    },
    {
        "asset": "totem_pr_smmag", "categorie_lib": "transport",
        "designation": "Totem de jalonnement « P+R PARKING RELAIS → / M » (SMMAG) : caisson noir, bandeau bleu « P+R » en tête, arcs de couleur, grand « M » blanc, logo SMMAG en pied",
        "classement_atelier": {"type": "totem_PR"},
        "etat_2026": "présent (position 2026 déduite, îlot de 2022 supprimé)", "confiance": "haute (modèle) / faible (position)", "priorite": 2,
        "quantite": {"estimation": 1, "min": 1, "max": 1, "methode": "photos 2024-05 et 2025-05 ; plan projet 2025"},
        "dimensions_m": {"hauteur": 5.5, "hauteur_plage": "5,0-6,0", "largeur": 1.0, "epaisseur": 0.28, "bandeau_bleu_hauteur": 0.95,
                         "platines": "2 pieds sur dalle béton 1,2 x 0,5"},
        "geometrie": ["caisson parallélépipédique à arêtes vives", "faces avant/arrière identiques (double face probable)", "2 platines boulonnées sur dalle"],
        "gabarit_2d": {"plan": "XZ", "elements": [rect(-0.6, 0, 0.6, 0.05, "beton_clair"), rect(-0.5, 0.05, 0.5, 5.5, "noir_9005"),
                                                  rect(-0.5, 4.55, 0.5, 5.5, "bleu_pr_smmag"), circ(0, 2.6, 0.32, "blanc_9016")]},
        "materiaux": [{"partie": "caisson", "materiau": "aluminium laqué + adhésifs", "couleur": "noir_9005"},
                      {"partie": "bandeau", "materiau": "adhésif", "couleur": "bleu_pr_smmag", "note": "face = texture à redessiner (P+R, PARKING RELAIS, flèche, arcs bleu/jaune/rouge et vert/violet, M, SMMAG)"}],
        "cotes_mesurees": [
            {"grandeur": "hauteur", "valeur": "≈ 5,5 m (4,6-6,0 selon la hauteur de caméra retenue)", "methode": "photo 2025-05-18 734a0da6 : pied r01_c03 y=780 (−21,3°), sommet r00_c03 y=822 (+38,6°) à 3,6-4,9 m ; recoupé par 31d16b8e r01_c02 (sommet +11,3° à ≈ 19-21 m pour une largeur de 2,7°)"},
            {"grandeur": "largeur", "valeur": "≈ 0,9-1,0 m", "methode": "mêmes photos (12,8° à ≈ 4,4 m ; 2,7° à ≈ 20 m)"},
        ],
        "ecart_inventaire": "le catalogue des besoins indique ≈ 3,6 m et l'atelier objets 2,8 m : les mesures angulaires donnent ≈ 5-6 m (le totem domine nettement les voitures et atteint la moitié de la hauteur du candélabre voisin)",
        "photos_reference": [tuile(T_734A, "r00_c03"), tuile(T_734A, "r01_c03"), tuile(T_31D1, "r01_c02")],
        "source_recommandee": "maison (boîte + texture redessinée ; marques déposées : pas de logo officiel copié, dessin simplifié)",
        "budget": {"triangles_lod0": 200},
        "pivot_orientation": "pivot au pied au centre ; +Y = face lue par les véhicules venant de Grenoble (azimut 45° dans l'atelier)",
    },
    # ------------------------------------------------------------------ mobilier
    {
        "asset": "armoire_commande_feux", "categorie_lib": "mobilier",
        "designation": "Armoire métallique grise du contrôleur de feux, chapeau débordant, 2 portes, sur socle béton (souvent taguée)",
        "classement_atelier": {"type": "armoire", "id": "armoire_feux_VERC"},
        "etat_2026": "présent", "confiance": "haute", "priorite": 2,
        "quantite": {"estimation": 1, "min": 1, "max": 2, "methode": "photo 2025-01-12 + ortho 2022 (bande séparative Vercors / piste)"},
        "dimensions_m": {"LxPxH_corps": [1.0, 0.45, 1.25], "socle": 0.15, "chapeau": "débord 0,05, 4 pentes, h 0,10", "hauteur_totale": 1.5},
        "geometrie": ["socle béton", "corps 2 portes à joint vertical, serrures", "chapeau à 4 pentes", "tags et autocollants (décals)"],
        "gabarit_2d": {"plan": "XZ", "elements": [rect(-0.55, 0, 0.55, 0.15, "beton_clair"), rect(-0.5, 0.15, 0.5, 1.40, "gris_clair_7035"),
                                                  poly([[-0.55, 1.40], [0.55, 1.40], [0.45, 1.50], [-0.45, 1.50]], "gris_clair_7035"),
                                                  line([[0, 0.2], [0, 1.35]], 0.01, "anthracite_7016")]},
        "materiaux": [{"partie": "corps", "materiau": "tôle d'acier / polyester", "couleur": "gris_clair_7035", "usure": "tags noirs et bleus, autocollants, salissures en pied"}],
        "cotes_mesurees": [{"grandeur": "hauteur du corps", "valeur": "≈ 1,35-1,45 m", "methode": "photo 2025-01-12 a1ffea74 r01_c01 (vue à ≈ 2,7 m, caméra piéton ≈ 1,7 m)"}],
        "photos_reference": [tuile(T_A1FF, "r01_c01"), tuile(T_9834, "r01_c02")],
        "source_recommandee": "maison",
        "budget": {"triangles_lod0": 300},
        "pivot_orientation": "pivot au sol au centre ; +Y = portes",
    },
    {
        "asset": "armoire_technique", "categorie_lib": "mobilier",
        "designation": "Armoire technique de réseaux (beige ; une armoire La Poste au NO)",
        "classement_atelier": {"type": "armoire", "id": "armoire_1313238971 (La Poste)"},
        "etat_2026": "présent", "confiance": "haute", "priorite": 3,
        "quantite": {"estimation": 2, "min": 1, "max": 3, "methode": "photo 2025-01-12 (rive est du Vercors) + OSM (operator La Poste)"},
        "dimensions_m": {"LxPxH": [0.62, 0.30, 1.15], "socle": 0.08},
        "geometrie": ["coffret polyester à 1 porte, toit plat débordant de 1 cm"],
        "gabarit_2d": {"plan": "XZ", "elements": [rect(-0.33, 0, 0.33, 0.08, "beton_clair"), rect(-0.31, 0.08, 0.31, 1.18, "beige_1015"),
                                                  rect(-0.32, 1.18, 0.32, 1.21, "beige_1015")]},
        "materiaux": [{"partie": "coffret", "materiau": "polyester armé", "couleur": "beige_1015"}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "≈ 1,0-1,2 m (comparée au poteau d'incendie voisin ≈ 0,9 m)", "methode": "photo 2025-01-12 d88855f2 r01_c01"}],
        "photos_reference": [tuile(T_D888, "r01_c01")],
        "source_recommandee": "maison",
        "budget": {"triangles_lod0": 150},
        "pivot_orientation": "pivot au sol ; +Y = porte",
    },
    {
        "asset": "barriere_croix_saint_andre", "categorie_lib": "mobilier",
        "designation": "Barrière de ville à croisillons (croix de Saint-André) en tube d'acier gris, modules scellés",
        "classement_atelier": {"type": "(non instancié par l'atelier)"},
        "etat_2026": "présent avant travaux ; implantation 2026 à reconfirmer (îlot du couloir bus supprimé en 2025)", "confiance": "haute (modèle) / faible (2026)", "priorite": 1,
        "quantite": {"estimation": 15, "min": 6, "max": 20, "methode": "≈ 9 modules sur ≈ 12 m (îlot du couloir bus, ortho 2022) + ≥ 6 le long du quai SO (photos 2025-05) ; unité = module"},
        "dimensions_m": {"longueur_module": 1.5, "longueur_plage": "1,2-2,0", "hauteur": 1.0, "poteaux": "tube Ø 0,06 (ou carré 0,06)", "lisses": "tube Ø 0,05 à 0,15 et 0,98 m", "croisillon": "2 tubes Ø 0,035"},
        "geometrie": ["module : 2 poteaux + 2 lisses + croix", "modules juxtaposés (poteau partagé) : instancier le long d'une courbe (BP_Wall CARLA / Copy to Points Houdini)"],
        "gabarit_2d": {"plan": "XZ", "elements": [rect(-0.78, 0, -0.72, 1.0, "galvanise_vieilli"), rect(0.72, 0, 0.78, 1.0, "galvanise_vieilli"),
                                                  line([[-0.75, 0.97], [0.75, 0.97]], 0.05, "galvanise_vieilli"), line([[-0.75, 0.15], [0.75, 0.15]], 0.05, "galvanise_vieilli"),
                                                  line([[-0.72, 0.17], [0.72, 0.95]], 0.035, "galvanise_vieilli"), line([[-0.72, 0.95], [0.72, 0.17]], 0.035, "galvanise_vieilli")]},
        "materiaux": [{"partie": "tubes", "materiau": "acier galvanisé ou thermolaqué gris", "couleur": "galvanise_vieilli",
                       "note": "photos 2025-05 : gris moyen légèrement brillant (le catalogue des besoins dit « anthracite » : retenir gris moyen ≈ RAL 9007 / galvanisé)"}],
        "cotes_mesurees": [{"grandeur": "module", "valeur": "≈ 1,3-1,6 m x ≈ 1,0 m", "methode": "photo 2025-05-18 734a0da6 r01_c01 (comparaison avec la voiture garée derrière, Peugeot 2008 ≈ 4,3 m)"}],
        "photos_reference": [tuile(T_734A, "r01_c01"), tuile(T_31D1, "r01_c02")],
        "source_recommandee": "maison",
        "budget": {"triangles_lod0": 400},
        "pivot_orientation": "pivot au sol au centre du module ; module le long de +X ; +Y = côté chaussée",
    },
    {
        "asset": "potelet_noir", "categorie_lib": "mobilier",
        "designation": "Potelet anti-stationnement noir à tête blanche contrastée (bande rétroréfléchissante)",
        "classement_atelier": {"type": "potelet"},
        "etat_2026": "présent", "confiance": "moyenne", "priorite": 1,
        "quantite": {"estimation": 8, "min": 6, "max": 12, "methode": "atelier objets : 6 positions (3 Revirée sur ortho 2022, 3 OSM dont 1 amovible) + surface centrale sud (photos 2025-01, non positionnés)"},
        "dimensions_m": {"hauteur_hors_sol": 1.0, "diametre": 0.09, "tete": "calotte bombée", "bande_claire": "0,10 m sous la tête"},
        "geometrie": ["fût cylindrique Ø 0,09 m", "tête bombée blanche ou bande blanche rétroréfléchissante de 0,10 m", "variante amovible : embase à serrure affleurante"],
        "gabarit_2d": {"plan": "YZ", "elements": [trap(0, 0, 0.97, 0.09, 0.09, "noir_9005"), rect(-0.046, 0.84, 0.046, 0.94, "blanc_retro"), circ(0, 0.97, 0.045, "noir_9005")]},
        "materiaux": [{"partie": "fût", "materiau": "acier/fonte laqué", "couleur": "noir_9005"}, {"partie": "bande", "materiau": "film rétroréfléchissant", "couleur": "blanc_retro"}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "≈ 0,9-1,1 m", "methode": "photo 2025-01-12 a1ffea74 r01_c00 (potelets de la surface centrale, vus de loin) ; ombres sur l'ortho 2022 (reviree_no-14)"}],
        "photos_reference": [tuile(T_A1FF, "r01_c00"), tuile(T_2AB4, "r01_c03")],
        "reference_normative": "arrêté du 15 janvier 2007, art. 1 (mobilier sur cheminement : partie contrastée en tête pour les éléments bas)",
        "source_recommandee": "maison (CARLA static.prop.chainbarrierend : proche, sans bande blanche)",
        "budget": {"triangles_lod0": 150},
        "pivot_orientation": "pivot au pied",
    },
    {
        "asset": "banc_bois_metal", "categorie_lib": "mobilier",
        "designation": "Banc à lattes de bois avec dossier, piétement métallique sombre",
        "classement_atelier": {"type": "banc"},
        "etat_2026": "présent", "confiance": "haute", "priorite": 2,
        "quantite": {"estimation": 2, "min": 2, "max": 3, "methode": "OSM 2026-03 (material=wood, backrest=yes), aux 2 quais"},
        "dimensions_m": {"LxPxH": [1.80, 0.60, 0.80], "hauteur_assise": 0.45, "lattes": "5 lattes d'assise + 3 de dossier, 0,09 x 0,04"},
        "geometrie": ["2 ou 3 piétements en fonte/acier en forme de L", "lattes bois chanfreinées", "accoudoirs latéraux (option)"],
        "gabarit_2d": {"plan": "YZ", "elements": [line([[-0.22, 0], [-0.22, 0.43], [0.25, 0.43]], 0.04, "anthracite_7016"), line([[0.2, 0], [0.2, 0.43]], 0.04, "anthracite_7016"),
                                                  rect(-0.26, 0.43, 0.26, 0.47, "bois_banc"), line([[-0.24, 0.5], [-0.31, 0.80]], 0.05, "bois_banc")]},
        "materiaux": [{"partie": "lattes", "materiau": "bois lasuré", "couleur": "bois_banc"}, {"partie": "piétement", "materiau": "fonte/acier laqué", "couleur": "anthracite_7016"}],
        "cotes_mesurees": [{"grandeur": "gabarit", "valeur": "≈ 1,8 m de long (≈ 0,45 x longueur de l'abri voisin)", "methode": "photo 2025-05-18 bc579b89 r01_c03 (banc à droite de la chaussée) et 734a0da6 r01_c01"}],
        "photos_reference": [tuile(T_BC579, "r01_c03"), tuile(T_734A, "r01_c01")],
        "source_recommandee": "CARLA static.prop.bench01 (proche : retexturer bois brun + piétement sombre) ou maison",
        "budget": {"triangles_lod0": 1200},
        "pivot_orientation": "pivot au sol au centre ; +Y = face de l'assise (côté où l'on s'assoit)",
    },
    {
        "asset": "corbeille_cylindrique", "categorie_lib": "mobilier",
        "designation": "Corbeille cylindrique en tôle à lames horizontales ajourées, couvercle jaune",
        "classement_atelier": {"type": "corbeille"},
        "etat_2026": "présent", "confiance": "haute (quais) / moyenne (3 corbeilles du NO : modèle non vu)", "priorite": 2,
        "quantite": {"estimation": 5, "min": 4, "max": 6, "methode": "OSM 2022-2026 (5 nœuds waste_basket) + plan projet 2025 (« Corbeille » aux quais)"},
        "dimensions_m": {"diametre": 0.46, "hauteur_corps": 0.80, "couvercle": "Ø 0,48 x 0,06, jaune", "socle": "pied central ou embase Ø 0,30"},
        "geometrie": ["cylindre de tôle à fentes horizontales (texture opacité ou géométrie)", "couvercle jaune débordant à ouverture frontale", "sac visible par les fentes (option)"],
        "gabarit_2d": {"plan": "XZ", "elements": [rect(-0.15, 0, 0.15, 0.05, "galvanise_vieilli"), rect(-0.23, 0.05, 0.23, 0.80, "galvanise_vieilli"),
                                                  rect(-0.24, 0.80, 0.24, 0.86, "jaune_1023")]},
        "materiaux": [{"partie": "corps", "materiau": "tôle d'acier galvanisée", "couleur": "galvanise_vieilli"}, {"partie": "couvercle", "materiau": "acier laqué", "couleur": "jaune_1023"}],
        "cotes_mesurees": [{"grandeur": "diamètre / hauteur", "valeur": "0,45-0,47 m / 0,78-0,83 m", "methode": "photo 2025-05-18 bc579b89 r01_c03 (pied à −19,4°, sommet −10,8°, largeur 5,3° ; caméra 1,7-1,8 m → distance 4,8-5,1 m)"}],
        "photos_reference": [tuile(T_BC579, "r01_c03")],
        "source_recommandee": "maison (CARLA static.prop.trashcan03 : silhouette proche, aspect différent)",
        "budget": {"triangles_lod0": 800},
        "pivot_orientation": "pivot au sol ; +Y = ouverture du couvercle",
    },
    {
        "asset": "arceau_velo", "categorie_lib": "mobilier",
        "designation": "Arceau vélo en U renversé à angles arrondis, tube d'acier thermolaqué anthracite, scellé",
        "classement_atelier": {"type": "stationnement_velos (bicycle_parking=stands)"},
        "etat_2026": "présent", "confiance": "haute", "priorite": 2,
        "quantite": {"estimation": 20, "min": 13, "max": 25,
                     "methode": "6 arceaux au quai NO (photo 2025-05 + plan projet « Stationnement vélos ») ; emprise : groupes OSM bicycle_parking=stands, capacité/2 arceaux (10, 8, 15, 6 places → ≈ 20 arceaux) ; les groupes wall_loops / handlebar_holder / bollard sont d'autres modèles"},
        "dimensions_m": {"longueur": 0.65, "longueur_plage": "0,60-0,70", "hauteur": 0.82, "hauteur_plage": "0,80-0,85", "tube_diametre": 0.05, "rayon_angles": 0.08, "entraxe_rangee": 1.0,
                         "v2": "V1 : 0,80 x 0,85 m, rayon 0,15 m, galvanisé → corrigé d'après la vue rapprochée dd2a9c8c (2024-05-01, ciel couvert)"},
        "geometrie": ["tube cintré en U renversé, pieds scellés (ou platines)", "rangée : instancier tous les 1,0 m, perpendiculairement à la bordure"],
        "gabarit_2d": {"plan": "XZ", "elements": _arceau()},
        "materiaux": [{"partie": "tube", "materiau": "acier thermolaqué", "couleur": "anthracite_7016",
                       "note": ("V2 : tranché sur la vue rapprochée 2024-05-01 dd2a9c8c r01_c00 (lumière diffuse, ≈ 3-6 m) : tubes gris anthracite mat "
                                "(≈ RAL 7016), pieds plus clairs (poussière) ; la vue V1 à contre-jour (2374105b) ne permettait pas de trancher")}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "≈ 0,85-1,0 m (V1, contre-jour)", "methode": "photo 2025-05-18 2374105b r01_c03 (pied −10°, sommet −4,1° pour une caméra à 1,7 m ; vélo garé pour contrôle)"},
                           {"grandeur": "rapport largeur / hauteur (V2)", "valeur": "0,70-0,72 sur 2 arceaux vus presque de face (pieds au même niveau image) ; roues de vélo garé ≈ 0,66-0,70 m de diamètre à côté → hauteur ≈ 0,80-0,85 m, largeur ≈ 0,60-0,70 m", "methode": "photo 2024-05-01 dd2a9c8c r01_c00 (arceaux x 355-460 et 487-603, sommets y 432-470, pieds y 578-637)"}],
        "photos_reference": [tuile(T_DD2A, "r01_c00"), tuile(T_2374, "r01_c03"), tuile(T_734A, "r01_c03")],
        "source_recommandee": "maison",
        "budget": {"triangles_lod0": 300},
        "pivot_orientation": "pivot au sol au centre ; l'arceau est dans le plan XZ",
    },
    {
        "asset": "barriere_levante", "categorie_lib": "mobilier",
        "designation": "Barrière levante de parking : fût bleu, lisse blanche reposant sur une fourche",
        "classement_atelier": {"type": "barriere_levante"},
        "etat_2026": "présent", "confiance": "haute", "priorite": 3,
        "quantite": {"estimation": 3, "min": 2, "max": 3, "methode": "OSM lift_gate ×2 + atelier objets (parking de L'Horloge, accès NO)"},
        "dimensions_m": {"fut_LxPxH": [0.30, 0.30, 1.05], "lisse_longueur": 4.4, "lisse_diametre": 0.08, "hauteur_lisse": 0.90, "fourche_hauteur": 0.88},
        "geometrie": ["fût parallélépipédique arrondi, capot", "lisse tubulaire (fermée), option ouverte à 85°", "poteau-fourche d'appui en bout"],
        "gabarit_2d": {"plan": "XZ", "elements": [rect(-0.15, 0, 0.15, 1.0, "bleu_5010"), rect(-0.17, 1.0, 0.17, 1.07, "bleu_5010"),
                                                  line([[0.15, 0.9], [4.5, 0.9]], 0.08, "blanc_9016"), line([[4.4, 0], [4.4, 0.86]], 0.05, "galvanise_vieilli")]},
        "materiaux": [{"partie": "fût", "materiau": "acier laqué", "couleur": "bleu_5010"}, {"partie": "lisse", "materiau": "aluminium laqué", "couleur": "blanc_9016"}],
        "cotes_mesurees": [{"grandeur": "lisse", "valeur": "≈ 4,0-4,5 m à ≈ 0,9 m", "methode": "photo 2026-07-28 ffc2e8ac r01_c00 (comparée à la voiture et au B1)"}],
        "photos_reference": [tuile(T_FFC2, "r01_c00")],
        "source_recommandee": "maison",
        "budget": {"triangles_lod0": 500},
        "pivot_orientation": "pivot au pied du fût ; lisse le long de +X ; +Y = côté entrée",
    },
    {
        "asset": "poteau_incendie", "categorie_lib": "mobilier",
        "designation": "Poteau d'incendie rouge (hydrant à colonne sèche DN 100, 2-3 sorties)",
        "classement_atelier": {"type": "poteau_incendie"},
        "etat_2026": "présent", "confiance": "haute", "priorite": 3,
        "quantite": {"estimation": 3, "min": 3, "max": 3, "methode": "OSM fire_hydrant pillar (réf. 210, 211, 213)"},
        "dimensions_m": {"hauteur": 0.95, "diametre_fut": 0.20, "chapeau": "Ø 0,24 x 0,10", "sorties": "1 x Ø 0,10 face + 2 x Ø 0,065 latérales à ≈ 0,6 m"},
        "geometrie": ["fût cylindrique", "chapeau bombé avec écrou de manœuvre pentagonal", "bouchons de sorties chaînés"],
        "gabarit_2d": {"plan": "XZ", "elements": [trap(0, 0, 0.85, 0.20, 0.18, "rouge_3000"), rect(-0.12, 0.85, 0.12, 0.95, "rouge_3000"),
                                                  circ(-0.13, 0.6, 0.04, "rouge_3000"), circ(0.13, 0.6, 0.04, "rouge_3000")]},
        "materiaux": [{"partie": "corps", "materiau": "fonte peinte", "couleur": "rouge_3000"}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "≈ 0,8-1,0 m", "methode": "photo 2025-01-12 d88855f2 r01_c01"}],
        "photos_reference": [tuile(T_D888, "r01_c01")],
        "reference_normative": "NF EN 14384 (poteaux d'incendie) ; couleur rouge (NF S 61-213)",
        "source_recommandee": "maison (pas d'hydrant américain)",
        "budget": {"triangles_lod0": 600},
        "pivot_orientation": "pivot au pied ; +Y = sortie principale",
    },
    {
        "asset": "ganivelle_bois", "categorie_lib": "mobilier",
        "designation": "Ganivelle en lattes de châtaignier refendues, liées par fils de fer torsadés, sur piquets (protection des plantations 2025)",
        "classement_atelier": {"type": "(non instancié)"},
        "etat_2026": "présent (semi-provisoire)", "confiance": "moyenne", "priorite": 3,
        "quantite": {"estimation": 40, "min": 20, "max": 80, "methode": "mètres linéaires (rive est du Vercors, 2026-07) ; module de 2 m"},
        "dimensions_m": {"hauteur": 1.2, "module": 2.0, "lattes": "0,03-0,04 de large, entraxe 0,09", "piquets": "Ø 0,08-0,10 tous les 2 m", "fils": "3 rangs torsadés"},
        "geometrie": ["lattes = géométrie fine ou carte d'opacité sur un plan", "piquets ronds"],
        "gabarit_2d": {"plan": "XZ", "elements": _ganivelle()},
        "materiaux": [{"partie": "lattes", "materiau": "châtaignier brut", "couleur": "chataignier_grise"}, {"partie": "piquets", "materiau": "bois", "couleur": "bois_creosote"}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "≈ 1,0-1,2 m", "methode": "photo 2026-07-28 f8d91bb1 r01_c02 et r01_c03 (comparaison avec le panneau AB3a et les voitures)"}],
        "photos_reference": [tuile(T_F8D9, "r01_c02"), tuile(T_F8D9, "r01_c03")],
        "source_recommandee": "maison (module de 2 m à instancier le long d'une courbe)",
        "budget": {"triangles_lod0": 1500},
        "pivot_orientation": "pivot au sol au centre du module ; module le long de +X",
    },
    {
        "asset": "cloture_grillage_rigide", "categorie_lib": "mobilier",
        "designation": "Clôture en panneaux de grillage rigide soudé (limites de propriétés)",
        "classement_atelier": {"type": "cloture (OSM fence metal)"},
        "etat_2026": "présent", "confiance": "moyenne", "priorite": 3,
        "quantite": {"estimation": 900, "min": 600, "max": 950, "methode": "mètres (GAM SOL_CLOTURES ≈ 913 m dans l'emprise)"},
        "dimensions_m": {"hauteur": 1.8, "hauteur_plage": "1,2-2,0", "panneau": 2.5, "maille": "0,20 x 0,05", "fil": 0.005, "plis": "2-3 plis horizontaux en V", "poteaux": "0,06 x 0,04"},
        "geometrie": ["panneau = plan + carte d'opacité (maille) + 2-3 plis", "poteaux à encoches"],
        "gabarit_2d": {"plan": "XZ", "elements": _cloture()},
        "materiaux": [{"partie": "panneaux et poteaux", "materiau": "acier galvanisé plastifié", "couleur": "vert_6005", "note": "variante gris anthracite RAL 7016"}],
        "cotes_mesurees": [{"grandeur": "hauteur", "valeur": "1,8 m (OSM / atelier)", "methode": "valeur type ; non mesurée sur photo"}],
        "photos_reference": [],
        "source_recommandee": "CC0/maison (Megascans/Fab : clôtures rigides génériques) ; CARLA BP_Wall pour la pose",
        "budget": {"triangles_lod0": 200},
        "pivot_orientation": "pivot au sol au centre du panneau ; panneau le long de +X",
    },
    {
        "asset": "bev_podotactile", "categorie_lib": "bordures",
        "designation": "Bande d'éveil de vigilance (BEV) : dalles podotactiles à plots tronconiques en quinconce, gris clair/blanc, en tête des traversées",
        "classement_atelier": {"type": "(dans la couche voirie : décal ou maillage fin)"},
        "etat_2026": "présent", "confiance": "haute", "priorite": 1,
        "quantite": {"estimation": 18, "min": 12, "max": 24, "methode": "2 bandes par traversée à feux (une par rive / deux dos à dos sur les refuges) ; OSM tactile_paving=yes sur 7 traversées ; plan projet 2025 (rectangles hachurés aux traversées)"},
        "dimensions_m": {"profondeur_standard": 0.5875, "profondeur_reduite": 0.42, "profondeur_observee": "0,40-0,60",
                         "longueur": "largeur de l'abaissé (≥ 1,20 ; 2-4 m sur le site)", "plot_diametre": 0.025, "plot_hauteur": 0.005,
                         "entraxe_plots": 0.075, "disposition": "lignes de plots en quinconce (8 lignes en largeur standard)",
                         "recul": "première ligne de plots à 0,50 m du nez de la bordure abaissée", "epaisseur_dalle": "0,03 (dalle rapportée ≤ 3 mm de semelle)"},
        "geometrie": ["dalles de 0,40 x 0,40 ou 0,42 x 0,60 m (joints visibles)", "plots : géométrie (≈ 12 tri/plot en LOD0) ou normal map + POM ; en lointain : simple texture",
                      "pose : affleurante, bord aligné parallèlement à la bordure ; voir bordures.json (abaisse_chartiere)"],
        "gabarit_2d": {"plan": "YZ", "elements": [rect(0, 0, 0.5875, 0.005, "beton_clair")] + [circ(0.03 + 0.075 * i, 0.0075, 0.0125, "beton_clair") for i in range(8)]},
        "materiaux": [{"partie": "dalles", "materiau": "béton gris clair (ou résine blanche)", "couleur": "beton_clair",
                       "note": "contraste ≥ 70 % avec l'enrobé voisin ; sur le site : béton gris clair à blanc sale"}],
        "cotes_mesurees": [{"grandeur": "profondeur de bande", "valeur": "≈ 0,40-0,45 m (photos) ; ≈ 0,55-0,60 m sur le plan projet 2025", "methode": "photos 2025-08-31 ab4cfacd r01_c02, 2025-05-18 31d16b8e r01_c03 ; plan projet 150 dpi"}],
        "photos_reference": [tuile(T_AB4C, "r01_c02"), tuile(T_31D1, "r01_c03"), tuile(T_5C0D, "r01_c04")],
        "reference_normative": "NF P98-351 (2010) : plots Ø 25 mm, hauteur 5 mm, entraxe 75 mm en quinconce ; largeur standard 587,5 mm, réduite 400-420 mm ; arrêté du 15 janvier 2007 (abaissés ≥ 1,20 m, ressaut ≤ 2 cm) ; fiche CFPSAA « BEV » (recul 0,50 m)",
        "source_recommandee": "maison (dalle + plots instanciés) + matériau béton CC0 (manifeste_cc0.json : beton_bordure)",
        "budget": {"triangles_lod0": 4000, "note": "par bande de 3 m avec plots géométriques ; sinon 2 triangles + normal map"},
        "pivot_orientation": "pivot au coin avant gauche de la bande au niveau du sol ; +Y = vers la chaussée (bord à 0,50 m du nez), longueur selon +X",
    },
    # ------------------------------------------------------------------ chantier (scénarios)
    {
        "asset": "separateur_modulaire_K16", "categorie_lib": "mobilier",
        "designation": "Séparateur modulaire de voie (K16) en plastique lestable, alternance rouge/blanc",
        "etat_2026": "absent (travaux terminés en janvier 2026) — scénarios travaux", "confiance": "haute (observé 2020-2025)", "priorite": 3,
        "quantite": {"estimation": 0, "min": 0, "max": 0, "methode": "aucun en 2026"},
        "dimensions_m": {"longueur": 1.0, "largeur_base": 0.40, "hauteur": 0.80, "emboitement": "tenon-mortaise aux extrémités"},
        "gabarit_2d": {"plan": "XZ", "elements": [poly([[-0.5, 0], [0.5, 0], [0.45, 0.8], [-0.45, 0.8]], "rouge_k"), poly([[-0.1, 0], [0.1, 0], [0.09, 0.8], [-0.09, 0.8]], "blanc_9016")]},
        "materiaux": [{"partie": "corps", "materiau": "polyéthylène", "couleur": "rouge_k", "note": "éléments alternés rouges et blancs"}],
        "photos_reference": [tuile("2025-08-31_a83dae90-c92a-472e-8d22-2e8863c47968", "r01_c01")],
        "reference_normative": "IISR 8e partie (signalisation temporaire) : K16",
        "source_recommandee": "maison",
        "budget": {"triangles_lod0": 400},
        "pivot_orientation": "pivot au sol au centre ; longueur le long de +X",
    },
    {
        "asset": "barriere_chantier_rouge_blanc", "categorie_lib": "mobilier",
        "designation": "Barrière de chantier métallique à bandes rouges et blanches (type K2) et clôtures mobiles grillagées sur plots",
        "etat_2026": "absent — scénarios travaux", "confiance": "haute (observé 2020-2025)", "priorite": 3,
        "quantite": {"estimation": 0, "min": 0, "max": 0, "methode": "aucun en 2026"},
        "dimensions_m": {"barriere_K2": {"longueur": 2.0, "hauteur": 1.0, "lisse": "0,25 de haut, bandes alternées 0,25"},
                         "cloture_mobile": {"longueur": 3.5, "hauteur": 2.0, "plots_beton": "0,6 x 0,2 x 0,15"}},
        "gabarit_2d": {"plan": "XZ", "elements": [rect(-1.0, 0, -0.96, 1.0, "galvanise_vieilli"), rect(0.96, 0, 1.0, 1.0, "galvanise_vieilli")]
                       + [rect(-0.96 + 0.24 * i, 0.72, -0.72 + 0.24 * i, 0.97, "rouge_k" if i % 2 == 0 else "blanc_9016") for i in range(8)]},
        "materiaux": [{"partie": "lisse", "materiau": "acier peint + film rétroréfléchissant", "couleur": "rouge_k"}],
        "photos_reference": [tuile(T_AB4C, "r01_c02"), tuile("2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a", "r01_c01")],
        "reference_normative": "IISR 8e partie : barrage K2",
        "source_recommandee": "maison (CARLA static.prop.streetbarrier : à éviter, modèle américain jaune)",
        "budget": {"triangles_lod0": 600},
        "pivot_orientation": "pivot au sol au centre ; +Y = face vue par les usagers",
    },
]

# Objets présents dans la scène (atelier objets) mais absents du catalogue des besoins :
# noms proposés, à ajouter au catalogue si l'on veut les remplacer.
COMPLEMENTS = [
    {"asset_propose": "balise_J11", "prototype_atelier": "balise_J11", "quantite": 2, "priorite": 2,
     "designation": "Balise de délimitation J11 (cylindre sombre à tête blanche rétroréfléchissante) sur l'axe du fuseau de la Revirée",
     "dimensions_m": {"diametre": 0.20, "hauteur": 1.0}, "source": "analyse reviree_no-08 (ortho 2022)", "recommandation": "maison"},
    {"asset_propose": "distributeur_titres_m_reso", "prototype_atelier": "distributeur (vending=public_transport_tickets)", "quantite": 1, "priorite": 3,
     "designation": "Distributeur de titres du réseau M, corps bleu, tête jaune, sous l'abri du quai NO",
     "dimensions_m": {"LxPxH": [0.50, 0.40, 1.75]}, "source": "OSM 2026-03 ; photo 2025-05-18 bc579b89 r01_c03 (sous l'abri)", "recommandation": "maison"},
    {"asset_propose": "distributeur_sacs_canins", "prototype_atelier": "distributeur (vending=excrement_bags)", "quantite": 1, "priorite": 3,
     "designation": "Distributeur de sacs canins sur poteau", "dimensions_m": {"LxPxH": [0.30, 0.15, 1.5]}, "source": "OSM", "recommandation": "maison"},
    {"asset_propose": "panneau_information_plan", "prototype_atelier": "panneau_information", "quantite": 4, "priorite": 3,
     "designation": "Panneau d'information (plan de quartier / réseau) sur 2 pieds", "dimensions_m": {"LxPxH": [1.2, 0.12, 2.2]}, "source": "OSM", "recommandation": "maison"},
    {"asset_propose": "mupi_publicitaire", "prototype_atelier": "mobilier_publicitaire", "quantite": 2, "priorite": 3,
     "designation": "MUPI double face (OSM réf. 19 et 25) : très probablement le caisson d'extrémité des 2 abris (à ne pas instancier en double)",
     "dimensions_m": {"LxPxH": [1.35, 0.14, 2.3]}, "source": "OSM 2026-03 ; photos 2025-05", "recommandation": "intégré à abri_bus_m_reso"},
    {"asset_propose": "conteneur_verre", "prototype_atelier": "conteneur_verre", "quantite": 1, "priorite": 3,
     "designation": "Colonne d'apport volontaire du verre (aérienne)", "dimensions_m": {"LxPxH": [1.2, 1.2, 1.7]}, "source": "OSM", "recommandation": "CARLA static.prop.glasscontainer (proche) ou maison"},
    {"asset_propose": "boite_aux_lettres_poste", "prototype_atelier": "boite_aux_lettres", "quantite": 1, "priorite": 3,
     "designation": "Boîte aux lettres La Poste jaune sur pied", "dimensions_m": {"LxPxH": [0.45, 0.35, 1.3]}, "source": "OSM", "recommandation": "maison (CARLA static.prop.mailbox : modèle américain, à éviter)"},
    {"asset_propose": "borne_fontaine", "prototype_atelier": "fontaine", "quantite": 1, "priorite": 3,
     "designation": "Borne fontaine d'eau potable", "dimensions_m": {"hauteur": 1.1}, "source": "OSM", "recommandation": "CARLA static.prop.streetfountain (proche) ou maison"},
    {"asset_propose": "chicane_cycles", "prototype_atelier": "chicane", "quantite": 1, "priorite": 3,
     "designation": "Barrière en chicane (3 éléments) d'accès piétons/cycles", "dimensions_m": {"element": [1.2, 0.05, 1.0]}, "source": "OSM cycle_barrier=triple", "recommandation": "maison (variante de barriere_croix_saint_andre)"},
    {"asset_propose": "portail_prive", "prototype_atelier": "portail", "quantite": 8, "priorite": 3,
     "designation": "Portails et portillons privés (coulissant, battants)", "dimensions_m": {"hauteur": 1.6, "largeur": "1,1-7,0"}, "source": "OSM", "recommandation": "générique (Fab/CC0)"},
    {"asset_propose": "mat_camera_video", "prototype_atelier": "mat_camera (node 9831317323)", "quantite": 1, "priorite": 3,
     "designation": "Mât droit 6 m portant une caméra fixe de vidéoprotection (l'autre « mat_camera » de l'atelier = mat_feu_crosse_camera du lot feux)",
     "dimensions_m": {"hauteur": 6.0}, "source": "OSM", "recommandation": "maison (variante de candelabre_mat_droit_led)"},
    {"asset_propose": "souche_arbre", "prototype_atelier": "souche", "quantite": 2, "priorite": 3,
     "designation": "Souche d'arbre abattu (h 0,3-0,5 m)", "dimensions_m": {"diametre": 0.6, "hauteur": 0.4}, "source": "atelier objets ; photos 2026-07-28 ded07efa / f8d91bb1", "recommandation": "Fab/Megascans (souches photogrammétriques) ou maison"},
]

NON_RETENUS = [
    {"type": "bornes anti-stationnement en pierre / béton, bornes de recharge", "raison": "non observées dans l'emprise (le catalogue des besoins les classe non retenues)"},
    {"type": "potence de feux", "raison": "non observée (lot feux)"},
    {"type": "bancs autres que bois/métal, jardinières", "raison": "non observés"},
]
