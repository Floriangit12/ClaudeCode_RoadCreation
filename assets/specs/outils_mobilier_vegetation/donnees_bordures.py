"""Profils de bordures et caniveaux béton français (NF EN 1340 + complément national NF P98-340/CN)
en polylignes 2D (m) prêtes pour un Sweep Houdini, et règles d'affectation sur le site.

Repère d'un profil (« repère bloc ») : u horizontal perpendiculaire à la bordure, u = 0 sur la face
vue (côté chaussée), u > 0 vers l'arrière (trottoir / îlot) ; v vertical, v = 0 sous le bloc.
Contour fermé parcouru dans le sens horaire (u vers la droite, v vers le haut), premier point = coin avant bas. Pour la pose : la chaussée
est à v = H − vue ; « profil_pose » translate le bloc pour que l'origine soit le pied de la face
vue au niveau de la chaussée (fil d'eau), ce qui correspond à la courbe GAM / atelier relief.

Cotes : dessins cotés des catalogues de fabricants certifiés NF (bordures T1, T2, T3, A1, A2, P1,
P2, P3, CS1, CS2, CC1, CC2, I1, I2, IL, quai bus) consultés le 2026-10-09 ; voir SOURCES.
"""
import math

SOURCES = [
    "Celtys (bétons industriels), catalogue « Bordures – Travaux publics » (profils cotés T1/T2/T3/T2 bateau/TU/A1/A2/AC1/CC1/CC2/CS1/CS2/I1/I2/IL/P1/P2/P3, bordure quai de bus), via hellopro.fr : https://www.hellopro.fr//documentation/pdf_prod/0/4/0/36050_9cb0dc8651512a6c9ced73c97a4dac56_6058040.pdf",
    "Fiches techniques Groupe Daniel / Sopravem (CC1, CS2 110/135 mm, P1 80 x 200 r 20, T2 basse 150 x 150), via groupe-samse.fr : https://medias.groupe-samse.fr/Fiche_technique/Fiche_technique_1246113.pdf (et 1246112, 1246130, 1246135)",
    "Fabemi, fiche bordure A2 150 x 200 (chanfrein 5 x 5), via chausson.fr : https://www.chausson.fr/media/article-document/243625",
    "Tableau des bordures (T1 12x20, T2 15x25, A2 15x20, P1 20x8, CS1 20x12, CS2 25x13,5, CC1 40x12, CC2 50x14), via chausson.fr : https://www.chausson.fr/media/article-document/210472",
    "NF P98-351 / fiche CFPSAA « Bande d'éveil de vigilance » (aveuglesdefrance.org, 2021) ; fiche produit BEV (vinci-construction.com, 2024) : plots Ø 25 mm, h 5 mm, entraxe 75 mm",
    "arrêté du 15 janvier 2007 (accessibilité de la voirie) : abaissés ≥ 1,20 m, ressaut ≤ 2 cm, pente ≤ 5 % (8 % sur ≤ 2 m, 12 % sur ≤ 0,5 m)",
]


def arc(cx, cy, r, a0, a1, n=4):
    """Points d'un arc (degrés), extrémités incluses."""
    return [[round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), 4),
             round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 4)] for i in range(n + 1)]


def profil_T(base, H, tete, h_fruit, r):
    """Bordure de trottoir type T : face vue verticale puis fruit (face inclinée) sur les h_fruit
    supérieurs, tête de largeur `tete`, arête avant arrondie (rayon ≈ r, Bézier quadratique)."""
    f = base - tete                      # retrait horizontal du fruit
    v_fruit = H - h_fruit
    t = r / math.hypot(f, h_fruit)
    p0 = (f * (1 - t), H - h_fruit * t)  # point de la face inclinée à r du coin
    p1 = (f, H)                          # coin vif théorique
    p2 = (f + r, H)                      # point de la tête à r du coin
    pts = [[0.0, 0.0], [0.0, round(v_fruit, 4)], [round(p0[0], 4), round(p0[1], 4)]]
    for s_ in (0.25, 0.5, 0.75):
        a, b, c = (1 - s_) ** 2, 2 * (1 - s_) * s_, s_ ** 2
        pts.append([round(a * p0[0] + b * p1[0] + c * p2[0], 4), round(a * p0[1] + b * p1[1] + c * p2[1], 4)])
    pts += [[round(p2[0], 4), round(H, 4)], [round(base, 4), round(H, 4)], [round(base, 4), 0.0]]
    return pts


def profil_A(base, H, plat, ch_h, ch_v, e=0.005):
    """Bordure franchissable type A : face vue verticale puis chanfrein (ch_h x ch_v)."""
    return [[0.0, 0.0], [0.0, round(H - ch_v, 4)], [round(ch_h, 4), round(H, 4)], [round(base - e, 4), round(H, 4)],
            [round(base, 4), round(H - e, 4)], [round(base, 4), 0.0]]


def profil_I(base, h_arr, h_av, n=6):
    """Bordure d'îlot franchissable type I : dessus convexe de h_av (face vue) à h_arr (arrière)."""
    pts = [[0.0, 0.0], [0.0, round(h_av - 0.01, 4)], [0.01, round(h_av, 4)]]
    for i in range(1, n + 1):
        s = i / n
        u = 0.01 + (base * 0.82 - 0.01) * s
        v = h_av + (h_arr - h_av) * math.sin(s * math.pi / 2)
        pts.append([round(u, 4), round(v, 4)])
    pts += [[round(base, 4), round(h_arr, 4)], [round(base, 4), 0.0]]
    return pts


PROFILS = {
    "T1": {"famille": "T (trottoir, non franchissable)", "section_cm": "12 x 20", "base": 0.12, "H": 0.20, "tete": 0.10,
           "fruit": "face inclinée sur les 10 cm supérieurs (retrait 2 cm)", "rayon_arete": 0.015, "vue_courante": [0.10, 0.14], "poids_kg_ml": 54,
           "contour": profil_T(0.12, 0.20, 0.10, 0.10, 0.015)},
    "T2": {"famille": "T (trottoir, non franchissable)", "section_cm": "15 x 25", "base": 0.15, "H": 0.25, "tete": 0.12,
           "fruit": "face inclinée sur les 14 cm supérieurs (retrait 3 cm)", "rayon_arete": 0.02, "vue_courante": [0.12, 0.16], "poids_kg_ml": 83,
           "contour": profil_T(0.15, 0.25, 0.12, 0.14, 0.02)},
    "T3": {"famille": "T (trottoir, non franchissable)", "section_cm": "17 x 28", "base": 0.17, "H": 0.28, "tete": 0.14,
           "fruit": "face inclinée sur les 14 cm supérieurs (retrait 3 cm)", "rayon_arete": 0.02, "vue_courante": [0.16, 0.20], "poids_kg_ml": 108,
           "contour": profil_T(0.17, 0.28, 0.14, 0.14, 0.02),
           "note": ("V2 : le tableau Celtys p. 7 imprime « T3 15 x 25 » mais 108 kg/ml, poids d'une section 17 x 28 (0,17 x 0,28 x 2,3 t/m³ ≈ 109 kg) "
                    "et le dessin coté p. 2 donne 17 x 28 (face inclinée 14 cm, tête 14 cm) : coquille du tableau ; retenir 17 x 28 pour les vues de 18-21 cm")},
    "T2_bateau": {"famille": "T, élément abaissé (bateau)", "section_cm": "15 x 16", "base": 0.15, "H": 0.16, "tete": 0.11,
                  "fruit": "face vue de 12 cm puis arrondi convexe de 4 cm", "vue_courante": [0.00, 0.04],
                  "contour": [[0.0, 0.0], [0.0, 0.12]] + arc(0.04, 0.12, 0.04, 180, 90, 4)[1:] + [[0.15, 0.16], [0.15, 0.0]]},
    "A1": {"famille": "A (franchissable)", "section_cm": "20 x 25", "base": 0.20, "H": 0.25, "plat": 0.12, "chanfrein": "8 x 6 cm",
           "vue_courante": [0.06, 0.12], "poids_kg_ml": 112, "contour": profil_A(0.20, 0.25, 0.12, 0.08, 0.06)},
    "A2": {"famille": "A (franchissable)", "section_cm": "15 x 20", "base": 0.15, "H": 0.20, "plat": 0.07, "chanfrein": "8 x 6 cm (+ chanfreins 5 x 5 mm)",
           "vue_courante": [0.04, 0.10], "poids_kg_ml": 67, "contour": profil_A(0.15, 0.20, 0.07, 0.08, 0.06)},
    "P1": {"famille": "P (bordurette de jardin, parcs)", "section_cm": "8 x 20", "base": 0.08, "H": 0.20, "rayon_arete": 0.02, "vue_courante": [0.00, 0.06],
           "poids_kg_ml": 35, "contour": [[0.0, 0.0], [0.0, 0.18]] + arc(0.02, 0.18, 0.02, 180, 90, 4)[1:] + [[0.08, 0.20], [0.08, 0.0]]},
    "P2": {"famille": "P (bordurette)", "section_cm": "6 x 28 (tête ronde)", "base": 0.06, "H": 0.28, "vue_courante": [0.00, 0.08],
           "contour": [[0.0, 0.0], [0.003, 0.255]] + arc(0.03, 0.255, 0.025, 180, 0, 6)[1:-1] + [[0.057, 0.255], [0.06, 0.0]]},
    "P3": {"famille": "P (bordurette)", "section_cm": "8 x 20 (rectangulaire)", "base": 0.08, "H": 0.20, "vue_courante": [0.00, 0.06],
           "contour": [[0.0, 0.0], [0.0, 0.20], [0.08, 0.20], [0.08, 0.0]]},
    "CS1": {"famille": "caniveau simple pente", "section_cm": "20 x 10/12", "largeur": 0.20, "h_cote_chaussee": 0.12, "h_cote_bordure": 0.10,
            "pente_dessus": "10 % vers la bordure (fil d'eau au pied de la bordure)", "poids_kg_ml": 54,
            "contour": [[0.0, 0.0], [0.0, 0.115], [0.005, 0.12], [0.20, 0.10], [0.20, 0.0]],
            "pose": "u = 0 côté chaussée (dessus au niveau de la chaussée), u = 0,20 contre la face vue de la bordure"},
    "CS2": {"famille": "caniveau simple pente", "section_cm": "25 x 11/13,5", "largeur": 0.25, "h_cote_chaussee": 0.135, "h_cote_bordure": 0.11,
            "pente_dessus": "10 % vers la bordure", "poids_kg_ml": 68,
            "contour": [[0.0, 0.0], [0.0, 0.13], [0.005, 0.135], [0.25, 0.11], [0.25, 0.0]],
            "pose": "u = 0 côté chaussée, u = 0,25 contre la bordure"},
    "CC1": {"famille": "caniveau double pente", "section_cm": "40 x 12", "largeur": 0.40, "creux": 0.015,
            "contour": [[0.0, 0.0], [0.0, 0.115], [0.005, 0.12], [0.20, 0.105], [0.395, 0.12], [0.40, 0.115], [0.40, 0.0]]},
    "CC2": {"famille": "caniveau double pente (fond arrondi)", "section_cm": "50 x 14", "largeur": 0.50, "creux": 0.03,
            "contour": [[0.0, 0.0], [0.0, 0.14], [0.06, 0.14]] + [[round(0.06 + 0.38 * i / 8, 4), round(0.14 - 0.03 * math.sin(math.pi * i / 8), 4)] for i in range(1, 8)]
                       + [[0.44, 0.14], [0.50, 0.14], [0.50, 0.0]]},
    "I1": {"famille": "I (îlot franchissable, dessus galbé)", "section_cm": "25 x 13 (face vue 6)", "base": 0.25, "vue_courante": [0.06, 0.06],
           "contour": profil_I(0.25, 0.13, 0.06)},
    "I2": {"famille": "I (îlot franchissable)", "section_cm": "25 x 18 (face vue 11)", "base": 0.25, "vue_courante": [0.11, 0.11],
           "contour": profil_I(0.25, 0.18, 0.11)},
    "IL": {"famille": "I (lotissement, très bas)", "section_cm": "20 x 9 (face vue 3)", "base": 0.20, "vue_courante": [0.03, 0.03],
           "contour": profil_I(0.20, 0.09, 0.03)},
    "QUAI_BUS": {"famille": "bordure de quai bus accessible (plancher bas)", "section_cm": "35 x 29,5", "base": 0.35, "H": 0.295,
                 "face": "verticale sur 11 cm puis inclinée à 73° sur 18 cm (guidage des pneus), petit chanfrein en tête", "vue_courante": [0.18, 0.21],
                 "contour": [[0.0, 0.0], [0.0, 0.11], [0.051, 0.278], [0.062, 0.295], [0.35, 0.295], [0.35, 0.0]],
                 "note": "dessus antidérapant clair (bande d'environ 0,30 m vue sur les photos) ; éléments de raccordement A/B (pente < 5 %) vers la T2 aux extrémités"},
    "PAVES_GRANIT": {"famille": "rangée de pavés de granit sertis (anneau d'îlot)", "section_cm": "14 x 14 x 14-20", "base": 0.14, "H": 0.17,
                     "vue_courante": [0.10, 0.13],
                     "contour": [[0.0, 0.0], [0.0, 0.14]] + arc(0.03, 0.14, 0.03, 180, 90, 3)[1:] + [[0.11, 0.17]] + arc(0.11, 0.14, 0.03, 90, 0, 3)[1:] + [[0.14, 0.0]],
                     "note": "préférer des pavés instanciés (Copy to Points le long de la courbe, 0,14 m + joint 0,012 m, rotation/hauteur aléatoires ± 5 mm) plutôt qu'un sweep continu"},
}

# ----------------------------------------------------------------------------- assets
ASSETS = [
    {"asset": "bordure_T2", "profil": "T2", "materiau": "beton_bordure (manifeste_cc0.json)", "couleur": "beton_clair",
     "usage": "bordure courante des trottoirs, terre-pleins, refuges et îlots (vue 0,09-0,175 m)", "priorite": 1,
     "aspect": "béton gris clair, joints tous les 1,00 m (3-5 mm), épaufrures d'arêtes, mousses et herbes dans les joints, salissures noires au fil d'eau",
     "photos_reference": ["2025-05-18_9834f494 r01_c02 (TPC de Verdun NE)", "2025-05-18_31d16b8e r01_c02 (îlot du mât caméra)", "2024-08-24_5c0d1d39 r01_c03 (îlot D21)"]},
    {"asset": "bordure_T2_peinte_blanc", "profil": "T2", "materiau": "beton_bordure + peinture_blanche (usure 2-3)", "couleur": "beton_clair",
     "usage": "refuges en D de Verdun SO (si conservés en 2026) : tête et face vue peintes en blanc, peinture écaillée", "priorite": 1,
     "aspect": "même maillage que bordure_T2 ; matériau : masque de peinture sur la tête + la face vue, couverture 0,6-0,8",
     "photos_reference": ["2024-08-24_2ab4efbc r01_c01"]},
    {"asset": "bordure_quai_bus", "profil": "QUAI_BUS", "materiau": "beton_bordure (tête claire antidérapante)", "couleur": "beton_clair",
     "usage": "quais bus La Revirée (2 quais de Verdun refaits en 2025, vue 0,18-0,21 m, standard atelier relief 0,20 m)", "priorite": 1,
     "aspect": "tête très claire (bande ≈ 0,3 m), face inclinée plus sombre, pied noirci ; raccords de 1-2 m en pente < 5 % vers la T2",
     "photos_reference": ["2025-05-18_2374105b r01_c03", "2025-05-18_bc579b89 r01_c03"]},
    {"asset": "bordure_A2", "profil": "A2", "materiau": "beton_bordure", "couleur": "beton_clair",
     "usage": "bordures basses franchissables : séparateurs de la piste bidirectionnelle, rives de piste, accotements (vue 0,03-0,09 m)", "priorite": 1,
     "aspect": "béton gris, arête chanfreinée, salissures ; type exact (A2 / I1 / T2 basse) non vu de près : profil A2 retenu (confiance moyenne)",
     "photos_reference": ["2024-08-24_2ab4efbc r01_c03", "2025-05-18_31d16b8e r01_c03", "2025-01-12_a1ffea74 r01_c00"]},
    {"asset": "bordure_P1", "profil": "P1", "materiau": "beton_bordure", "couleur": "beton_clair",
     "usage": "bordurettes d'espaces verts, de parkings et de cheminements, limites à niveau (vue 0-0,03 m ; pose affleurante)", "priorite": 1,
     "aspect": "bordurette étroite, souvent salie, herbe débordante",
     "photos_reference": ["2026-07-28_f8d91bb1 r01_c03", "2026-07-28_ded07efa r01_c02"]},
    {"asset": "caniveau_cs", "profil": "CS2", "variante": "CS1 (20 cm) ; caniveau à fente le long du quai SE (grille continue)", "materiau": "beton_bordure (plus sale)",
     "couleur": "beton_clair", "usage": "fil d'eau béton à joints transversaux au pied des T2 de Verdun (GAM SOL_CANIVEAU)", "priorite": 1,
     "aspect": "béton gris plus sombre et taché que la bordure, dépôts (sable, feuilles) au fil d'eau, joints tous les 1 m",
     "photos_reference": ["2025-05-18_734a0da6 r01_c03"]},
    {"asset": "bordure_paves_granit", "profil": "PAVES_GRANIT", "materiau": "paves_granit (manifeste_cc0.json)", "couleur": "granit_clair",
     "usage": "anneaux des petits îlots ronds portant un B21a1 (Ø ≈ 2 m, vue ≈ 0,12 m)", "priorite": 2,
     "aspect": "pavés clairs à tête bombée, joints mortier, centre de l'îlot en enrobé ou gravillons",
     "photos_reference": ["2025-05-18_119d9094 r01_c00"]},
    {"asset": "abaisse_chartiere", "profil": "T2_bateau", "materiau": "beton_bordure", "couleur": "beton_clair",
     "usage": "abaissés aux traversées : T2 bateau (vue 0,02 m) sur la largeur de la traversée + 2 chartières (gauche/droite) de 1,00 m où la vue passe linéairement de la vue courante à 0,02 m", "priorite": 1,
     "aspect": "comme bordure_T2 ; BEV posée derrière (voir mobilier.json : bev_podotactile)",
     "photos_reference": ["2024-08-24_5c0d1d39 r01_c04", "2025-08-31_ab4cfacd r01_c02"]},
    {"asset": "bordure_T3", "profil": "T3", "hors_catalogue_v1": True, "materiau": "beton_bordure", "couleur": "beton_clair",
     "usage": ("V2 : profil haut (vue 0,175-0,27 m ; ≈ 280 m sur le site d'après les vues mesurées) : îlots du Vercors (vue 0,18-0,21), quelques bordures de quai "
               "et de trottoir surélevées. En V1 cette plage était confiée à « bordure_T2 (maillage T3) », soit un même nom pour deux maillages : nom distinct en V2"),
     "priorite": 1,
     "aspect": "comme bordure_T2 (bordures très claires, presque blanches, aux îlots du Vercors sur les photos 2025-01)",
     "photos_reference": ["2025-01-12_a1ffea74 r01_c00", "2025-01-12_d88855f2 r01_c01"]},
]

# V2 : provenance des cotes de chaque profil (planches cotées relues à 200 dpi, tuiles 1000x1000)
_CELTYS = "Celtys, catalogue « Bordures Travaux publics » (hellopro, 8 p.) : plan coté p. {p}, tableau p. 7 ; relu en V2 (2026-10-09)"
SOURCES_PROFILS = {
    "T1": _CELTYS.format(p=2) + " — 12 x 20, tête 10, face inclinée sur 10 cm", "T2": _CELTYS.format(p=2) + " — 15 x 25, tête 12, face inclinée sur 14 cm",
    "T3": _CELTYS.format(p=2) + " — 17 x 28, tête 14, face inclinée sur 14 cm (tableau p. 7 : coquille « 15 x 25 »)",
    "T2_bateau": _CELTYS.format(p=2) + " — 15 x 16, face vue 12 cm + arrondi 4 cm",
    "A1": _CELTYS.format(p=2) + " — 20 x 25, plat 12, chanfrein 8 x 6", "A2": _CELTYS.format(p=2) + " — 15 x 20, plat 7, chanfrein 8 x 6 ; recoupé Chausson (A2 15x20x100, 69-73 kg)",
    "P1": _CELTYS.format(p=4) + " — 8 x 20", "P2": _CELTYS.format(p=4) + " — 6 x 28", "P3": _CELTYS.format(p=4) + " — 8 x 20 rectangulaire",
    "CS1": _CELTYS.format(p=3) + " — 20 x 10/12", "CS2": _CELTYS.format(p=3) + " — 25 x 11/13,5", "CC1": _CELTYS.format(p=3) + " — 40 x 12",
    "CC2": _CELTYS.format(p=3) + " — 50 x 14", "I1": _CELTYS.format(p=3) + " — 25 x 13, face vue 6", "I2": _CELTYS.format(p=3) + " — 25 x 18, face vue 11",
    "IL": _CELTYS.format(p=3) + " — 20 x 9, face vue 3",
    "QUAI_BUS": ("profil générique de quai bus accessible à face inclinée (type « Kassel » / BQB) : Celtys p. 6 montre le système (raccords A et B < 5 %, "
                 "dalles d'éveil) SANS coupe cotée → cotes 35 x 29,5 indicatives, confiance moyenne ; vue réelle 0,18-0,21 m mesurée sur le site"),
    "PAVES_GRANIT": "pavés de granit 14 x 14 estimés sur la photo 2025-05-18 119d9094 r01_c00 (anneau d'îlot B21a1)",
}
VERIFICATION_V2 = ("V2 : plans cotés Celtys des pages 2-3 et 6 rendus à 200 dpi et relus en tuiles 1000x1000 : T1, T2, T2 bateau, T3, A1, A2 conformes aux contours "
                   "de ce fichier (A2 : plat 7 cm, chanfrein 8 x 6 cm côté chaussée ; A1 : plat 12 cm). Les dessins montrent une légère pente de la tête vers la "
                   "chaussée (≈ 2-4 %, quelques mm) que les contours ignorent (sans effet visible). Tableau Chausson/Cambounet (A2 15x20x100, 69-73 kg) concordant.")


# Règles d'affectation d'un profil à un tronçon de 1 m de recon/out/paquet_jardin/relief/bordures_hauteurs.geojson
# (contexte, traversee, h_vue_m). Appliquées dans l'ordre ; la première qui convient l'emporte.
REGLES = [
    {"si": "traversee et h_vue ≤ 0,06", "profil": "T2_bateau", "asset": "abaisse_chartiere", "vue_pose": "0,02"},
    {"si": "contexte = quai_bus et h_vue ≥ 0,15", "profil": "QUAI_BUS", "asset": "bordure_quai_bus", "vue_pose": "h_vue (0,18-0,21)"},
    {"si": "h_vue < 0,03", "profil": "P1", "asset": "bordure_P1", "vue_pose": "h_vue (0-0,03), ou pas de bordure si limite de revêtement"},
    {"si": "0,03 ≤ h_vue < 0,09", "profil": "A2", "asset": "bordure_A2", "vue_pose": "h_vue"},
    {"si": "0,09 ≤ h_vue < 0,175", "profil": "T2", "asset": "bordure_T2", "vue_pose": "h_vue"},
    {"si": "0,175 ≤ h_vue < 0,30", "profil": "T3", "asset": "bordure_T3", "vue_pose": "h_vue (0,175-0,27) ; T3 plutôt que T2 enterrée de moins de 8 cm"},
    {"si": "h_vue ≥ 0,30", "profil": "MURET_TALUS", "asset": "(aucun : muret, soutènement ou talus — à modéliser avec le terrain / les murs GAM)", "vue_pose": "—"},
]


def regle(contexte, traversee, h):
    if h is None:
        return None
    if traversee and h <= 0.06:
        return "T2_bateau"
    if contexte == "quai_bus" and h >= 0.15:
        return "QUAI_BUS"
    if h < 0.03:
        return "P1"
    if h < 0.09:
        return "A2"
    if h < 0.175:
        return "T2"
    if h < 0.30:
        return "T3"
    return "MURET_TALUS"


USAGE_SITE = [
    {"zone": "trottoirs de Verdun, de la Revirée et de l'allée de L'Horloge", "profil": "T2", "vue_m": "0,10-0,13 (mesures LiDAR 2021 ; standard 2025 : 0,14)", "asset": "bordure_T2"},
    {"zone": "îlots du Vercors (îlot effilé gravillonné, îlot triangulaire)", "profil": "T2 (vue ≤ 0,175) / T3 (vue 0,18-0,21)", "vue_m": "0,16-0,21", "asset": "bordure_T2 / bordure_T3",
     "note": "bordures très claires (presque blanches) sur les photos 2025-01"},
    {"zone": "quais bus La Revirée (Verdun, refaits en 2025)", "profil": "QUAI_BUS", "vue_m": "0,20 (ancien quai 0,16-0,22)", "asset": "bordure_quai_bus"},
    {"zone": "terre-plein central de Verdun NE et terre-plein planté SO (2025), refuges", "profil": "T2", "vue_m": "0,15-0,17", "asset": "bordure_T2"},
    {"zone": "refuges en D de Verdun SO (2022, peints en blanc)", "profil": "T2", "vue_m": "≈ 0,15", "asset": "bordure_T2_peinte_blanc", "note": "à vérifier en 2026 (zone des travaux)"},
    {"zone": "séparateurs et rives de la piste bidirectionnelle (Chronovélo), accotements", "profil": "A2", "vue_m": "0,05-0,09", "asset": "bordure_A2"},
    {"zone": "espaces verts, parkings, cheminements, quartier des Saules Blancs (limites à niveau)", "profil": "P1", "vue_m": "0-0,05", "asset": "bordure_P1"},
    {"zone": "traversées piétonnes (21 chartières GAM, abaissés)", "profil": "T2_bateau + chartières 1 m", "vue_m": "0,02", "asset": "abaisse_chartiere"},
    {"zone": "fil d'eau de Verdun (GAM SOL_CANIVEAU ≈ 139 m) et caniveau à fente du quai SE", "profil": "CS2 (CS1)", "vue_m": "—", "asset": "caniveau_cs"},
    {"zone": "petits îlots ronds à B21a1 (approches NE et Revirée)", "profil": "PAVES_GRANIT", "vue_m": "0,10-0,13", "asset": "bordure_paves_granit"},
    {"zone": "surface centrale sud à niveau (refuge piétons/cycles)", "profil": "IL ou P1 affleurant", "vue_m": "0-0,03", "asset": "bordure_P1"},
]
