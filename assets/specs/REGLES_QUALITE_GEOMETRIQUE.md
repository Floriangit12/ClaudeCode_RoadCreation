# Règles de qualité géométrique (régularisation « plan de VRD professionnel »)

Version 1.0 du 2026-10-10 — format `regles_conception/1.0` (même format que `regles_conception.json`). Source unique : `regles_qualite_geometrique.json` ; ce fichier est généré par `recon/pcg/decrire/regulariser_regles.py`.

## Objet

Faire de la description un plan de VRD professionnel : bordures, bords de trottoir, contours d'îlots, limites de surfaces et axes de marquage dessinés en droites, arcs de cercle (et clothoïdes pour les axes de voie) raccordés tangentiellement, dans la tolérance de la source, avec une topologie exacte (nœuds partagés, contacts en T, limites communes identiques). La géométrie levée (GAM 2026, PCRS 2019, plan 2025, ortho, v1) n'est qu'une mesure : elle est ajustée, jamais recopiée avec ses cassures et ses ondulations.

Chaîne : decrire/regulariser.py (crochets dans sol_composer.familles_sol, surfaces.construire_partition et composer.py) → description_scene_v2 (primitives + polyligne densifiée) → Houdini 22 → UE 5.8.3.

Repère et conventions : local = Lambert-93 − O (917279.43, 6460289.98) ; cap en radians depuis l'axe x (est), sens trigonométrique ; courbure k > 0 à gauche du sens de parcours ; bordures orientées côté haut à gauche (face vue à droite).

## Synthèse

| Id | Action | Énoncé (résumé) | Source principale |
|---|---|---|---|
| GQ-PRI-001 | générer | Les bordures (arête avant au fil d'eau), les bords de trottoir, les contours d'îlots et les limites de surfaces sont décrits par une suite de droites et d'arcs de cercle seulement | PCRS_V2 (§B.1.1 (p. 14) : seules les courbes formées de segments de d) |
| GQ-PRI-002 | générer | Les axes des lignes de marquage longitudinales sont décrits par des droites, des arcs et, si nécessaire, des clothoïdes (raccordements progressifs des bords de voie) ; une ligne oblique qui fait une cassure importante avec la ligne longitudinale lui est raccordée par une courbe de rayon approprié, voisin de celui des bords de chaussée | ODR19 (§9.1 à §9.6 : ligne de référence faite de droites, spirales ) |
| GQ-PRI-003 | générer | Chaque entité régularisée porte sa suite de primitives (type, s0, s1, point de départ en Lambert-93, cap de départ, courbure, rayon) et sa polyligne densifiée ; la suite de primitives fait foi, la polyligne en est l'échantillonnage | INTERNE (contrat Claude décrit / Houdini fabrique (ARCHITECTURE.md §1) |
| GQ-CON-001 | contraindre | Continuité de position et de tangente (G1) partout, sauf aux coins voulus (GQ-CON-002) : au raccord de deux primitives, le saut de cap est nul (≤ 0,01° numériquement) ; sur la polyligne densifiée, aucune cassure > 1° hors des coins voulus (mesure GQ-VAL-001) | ODR19 (« A road reference line shall have no gaps. » ; « A road ref) |
| GQ-CON-002 | contraindre | Un coin (G0) n'est admis que s'il est voulu : la déviation est d'au moins 20°, un congé constructible (rayon ≥ 0,25 m et longueur ≥ longueur minimale de pièce) passerait à plus de la tolérance du sommet levé, et le sommet est porté par deux alignements droits (écart ≤ T sur ≤ 1 m de part et d'autre) ou dévie de 45° au moins | INTERNE (critère déduit de la tolérance (GQ-TOL-001) et des pièces co) |
| GQ-CON-003 | vérifier | La continuité de courbure (G2) n'est pas exigée pour les bordures et les limites (pose en éléments droits et pièces courbes : droite et arc se raccordent tangentiellement sans clothoïde) ; elle est mesurée et rapportée (sauts de courbure aux raccords, peignes de courbure) | ODR19 (§9.4 Spiral : raccordement progressif de courbure entre droi) |
| GQ-TOL-001 | contraindre | L'écart entre la géométrie régularisée et la source (distance symétrique, points de la source vers la courbe et courbe vers la polyligne source) respecte la tolérance T de la source : 99 % des écarts ≤ T et aucun > 1,5 T (gabarit de l'arrêté du 16/09/2003, art | ARR2003 (art. 5 : au plus 1 % des écarts au-delà de T = k·[yy], aucun) |
| GQ-TOL-002 | contraindre | Pas de biais systématique : l'ajustement est refusé si l'écart moyen des points de la source dépasse T / 2 (contrainte) ; le contrôle signale un écart moyen au-delà de T / 3,23 (condition d'écart moyen de l'arrêté du 16/09/2003 en dimension 1 : Emoy ≤ [yy] avec T = 3,23·[yy]) | ARR2003 (art. 5, première condition (écart moyen en position)) |
| GQ-TOL-003 | contraindre | Ajustement robuste : résidus pondérés de Huber (seuil T/2) pour qu'un sommet aberrant isolé (pointe de levé, saut de dédoublonnage) ne déforme pas la ligne ; les allers-retours (> 170°) et les sommets à moins de 5 mm sont retirés avant l'ajustement | PCRS_V2 (§B.1.3 (p. 15) : aucun segment de longueur nulle (points con) |
| GQ-SEG-001 | contraindre | Pas de micro-pièce : longueur minimale d'une primitive de 0,50 m pour une bordure (un demi-élément ; 0,20 m pour un arc de rayon ≤ 1,2 m, pièce courbe ou quart de rond du catalogue), 0,30 m pour une limite de surface, 0,50 m pour un axe de marquage ; un tronçon entre deux coins plus court est une seule droite | SPEC_BORD_EL (element (0,994 m / 0,494 m), pieces_courbes (R 0,5 à 9 m), q) |
| GQ-SEG-002 | générer | Parcimonie : le nombre de primitives est le plus petit qui tient la tolérance ; deux primitives voisines sont fusionnées dès que la tolérance le permet ; un objet continu n'est pas découpé sans raison (profil, coin, bout) | PCRS_V2 (§B.1.3 (p. 15) : « limiter le plus possible le découpage d'o) |
| GQ-RAY-001 | contraindre | Rayon minimal d'un arc de bordure : 0,25 m (quart de rond TU/I1/I2 R 25) ; de 0,25 à 0,75 m, pièce courbe (R 0,5) ; de 0,75 à 3 m, pièce courbe du catalogue ou éléments courts ; au-delà, éléments droits de 0,5 ou 1 m posés en corde (flèche ≤ 10,5 mm) | SPEC_BORD_EL (regle_pas_rayon (table) et quarts_de_rond (R 0,25)) |
| GQ-RAY-002 | vérifier | Rayons de bordure d'angle en bord de chaussée circulée : 3-4 m très serré (sans bus ni PL), 5-6 m serré, 8-10 m normal, 12 m ligne de bus régulière, 16-20 m à éviter en urbain dense | LYON_DIM (p. 10 « Giration des véhicules, calcul des rayons de courbur) |
| GQ-RAY-003 | générer | Rayons normalisés : un arc est ramené au rayon le plus proche de la série (catalogue de pièces : 0,25 ; 0,5 ; 1,2 ; 1,4 ; 1,6 ; 1,8 ; 2 ; 3 ; 4 ; 5 ; 6 ; 7 ; 8 ; 9 m ; rayons de projet : 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500 m) si l'écart de rayon est ≤ 10 % et que la tolérance GQ-TOL-001 reste tenue ; un arc dont la flèche L²/(8R) est < T/2 (ou R > 500 m) devient une droite dans les mêmes conditions | SPEC_BORD_EL (regle_pas_rayon.pieces_courbes.rayons_m (choix du rayon cata) |
| GQ-RAY-004 | vérifier | Nez d'îlot : arrondi de rayon 0,25 à 1,5 m (deux quarts de rond R 0,25 dos à dos, pièce courbe R 0,5, ou arcs du catalogue jusqu'à 1,5 m) ; un nez vif (coin) n'est admis que si le levé le montre (GQ-CON-002) | SPEC_BORD_EL (quarts_de_rond.usage : « nez d'îlot arrondi R 0,25 : 2 quart) |
| GQ-TOP-001 | contraindre | Deux bouts de bordure distants de moins de 1,5·max(T) (10 cm au plus) partagent un nœud exact (même coordonnée) ; si les deux bordures se prolongent (écart de direction ≤ 15°), elles partagent aussi le cap au nœud (G1 à travers le nœud) ; sinon le nœud est un coin | PCRS_V2 (§B.1.3 (p. 15) : un objet continu représenté par plusieurs o) |
| GQ-TOP-002 | contraindre | Un bout de bordure à moins de 1,5·max(T) de l'intérieur d'une autre bordure (contact en T) est posé exactement sur la courbe régularisée de celle-ci (projection orthogonale), après la régularisation de la bordure traversante | RC_TQ_SOL_001 (topologie 2D préparée avant Houdini (accrochages, aucun trou) |
| GQ-TOP-003 | contraindre | Une bordure en anneau dont la lacune de fermeture est ≤ 1,5 T est refermée exactement (anneau G1 si aucun coin, sinon départ au premier coin) ; au-delà la lacune est réelle (ceinture synthétique d'îlot, ilots.py) | PCRS_V2 (§B.1.3 : extrémités communes aux tolérances près) |
| GQ-TOP-004 | vérifier | La partition des surfaces est reconstruite à partir des limites régularisées : 0 trou et 0 recouvrement (aire(union) = Σ aires à 1e-6 m² près, carré de 300 m), limites partagées identiques (une arête n'existe qu'une fois), aucune arête < 5 mm | RC_TQ_SOL_001 (contrôle aire(union) = somme(aires), 0 recouvrement) |
| GQ-TOP-005 | générer | Toute géométrie dépendante est re-dérivée de la géométrie régularisée : abscisses des intervalles de profil, des abaissés, des chartières et des courbes de pose remappées par projection sur la nouvelle ligne (ordre et partition exacte de [0, L] conservés) ; Z interpolé à l'abscisse remappée ; arête arrière, emprises, rampes et surfaces recalculées par la partition ; interruptions des lignes de marquage remappées | INTERNE (cohérence de la description (une seule géométrie de référenc) |
| GQ-LAR-001 | contraindre | Largeur constante : une limite levée (revêtement, végétation, talus) qui longe l'arête arrière d'une bordure à une distance dont la variation reste ≤ 2·T (et ≤ 6 cm) sur au moins 5 m est remplacée, sur ce tronçon, par le décalé exact de la bordure régularisée à la distance médiane (trottoir, piste, séparateur ou bande à largeur constante) ; raccords aux bouts par la limite levée régularisée | PARIS_SH (§ files de circulation : lignes « généralement tracées paral) |
| GQ-PAR-001 | contraindre | Les lignes de marquage longitudinales sont parallèles au bord de voie ou à la bordure qu'elles longent : une ligne (≥ 2 m) qui longe sur toute sa longueur une bordure à moins de 1,5 m, à distance variant de moins de min(2T, 6 cm), devient le décalé exact de la bordure régularisée à la distance médiane (si la tolérance GQ-TOL-001 reste tenue) ; le contrôle signale toute ligne à moins de 1,5 m d'une bordure, parallèle à 5° près, dont la distance à la face varie de plus de 3 cm | PARIS_SH (« Les lignes sont généralement tracées parallèlement à la bo) |
| GQ-SYM-001 | vérifier | Passage piéton : bandes parallèles à l'axe de la chaussée (cap identique dans une traversée), de même longueur, de largeur 0,50 m, intervalle constant (0,50 à 0,80 m) pour une même traversée ; dimensions prises perpendiculairement à l'axe de la chaussée même pour une traversée biaise | IISR7 (art. 118 : bandes rectangulaires « parallèles à l'axe de la ) |
| GQ-SYM-002 | vérifier | Abaissé de traversée : la bordure est rectiligne en plan sur la partie abaissée (droite, ou arc de rayon ≥ 12 m posé en éléments de 1 m), pour que la traversée soit perpendiculaire au trottoir et que la BEV ne soit pas dans l'arrondi ; un abaissé dans un arc plus serré est signalé | LYON_ACC (« La traversée créée doit être la plus perpendiculairement p) |
| GQ-SYM-003 | contraindre | Quai de bus en ligne ou en avancée : bordure de quai en alignement droit avec le bord de chaussée ; la partie QUAI_BUS d'une bordure est ajustée en une seule droite si la tolérance le permet, sinon signalée (quai en courbe à proscrire) | CEREMA_BUS2018 (p. 73-75 : « le quai est en alignement droit avec le bord de) |
| GQ-ORI-001 | contraindre | Les voies circulées driving et bus de l'OpenDRIVE 2026 (lanes_2026, échantillonneur xodr) sont toujours du côté BAS d'une bordure (à droite de la polyligne, face vue) | LOC_REVUE_P6 (recon/out/paquet_jardin/v2/description/coherence (revue)) |
| GQ-ORI-002 | contraindre | Sans voie OpenDRIVE adjacente, et si le MNT n'est pas décisif (|dz| < 2,5 cm, critère d'origine « cote_haut_relief », « surfaces_v1 » ou « defaut »), la classe d'indice v1 tranche : chaussée ou parking du côté haut (≥ 0,6) et trottoir, quai, îlot ou espace vert du côté bas (≥ 0,6) : la bordure est retournée | LOC_REVUE_P6 (classe chaussée du côté haut (KS-0588-1, KS-0563-1)) |
| GQ-ORI-003 | vérifier | Deux bordures qui se prolongent (nœud G1 de GQ-TOP-001) ont le même sens : la fin de l'une est le début de l'autre | INTERNE (continuité d'une file de bordures (côté haut constant le lon) |
| GQ-DEN-001 | générer | Polyligne densifiée depuis les primitives : flèche de corde ≤ 2 mm, pas ≤ 0,5 m sur les bordures (un Z par sommet) et ≤ 1 m sur les limites de surface, sommet à chaque raccord de primitives et à chaque coin ; les axes de marquage droits gardent leurs deux bouts | INTERNE (cohérent avec TQ-MQG-013 (erreur de corde ≤ 1 mm pour les gl) |
| GQ-PRO-001 | générer | Provenance : la source levée reste dans prov.geometrie ; prov.regularisation ajoute src = regle:regles_qualite_geometrique.GQ-TOL-001, l'écart maximal, l'écart p99 et la tolérance ; la géométrie source (avant régularisation) est archivée dans base/regularisation_sources.geojson (non fabriquée) pour les contrôles et les planches | LOC_V2DESC (prov {attribut: {src, ref, conf}}) |
| GQ-VAL-001 | vérifier | Histogramme des cassures avant / après : cassure discrète à chaque sommet = |déviation au sommet − déviation attendue de la courbure voisine| ; 0 cassure > 1° hors coins voulus après régularisation ; rapport par famille et par source | ODR19 (« should have no kinks ») |
| GQ-VAL-002 | vérifier | Dégagement des marquages aux bordures après régularisation : aucune ligne, transversale ou bande de passage ne croise l'arête avant d'une bordure (hors marques portées sur bordure et interruptions décrites) ; l'axe d'une ligne longeant une bordure reste à ≥ largeur/2 + 0,05 m de la face | RC_MQ_DET_010 (interruptions des marques aux bordures et obstacles) |
| GQ-VAL-003 | vérifier | Revue visuelle : planches avant / après sur l'ortho 2022 (coins, nez d'îlots, trottoirs de la capture utilisateur, traversée Verdun SO, trottoir NE, arrêt de bus) et peignes de courbure de 5 bordures, regardées avant livraison | INTERNE (pratique de contrôle des tracés (peigne de courbure)) |

## Primitives de dessin

### GQ-PRI-001 (générer)

Les bordures (arête avant au fil d'eau), les bords de trottoir, les contours d'îlots et les limites de surfaces sont décrits par une suite de droites et d'arcs de cercle seulement. Pas de spline libre ni de polyligne brute de levé dans la description finale : la polyligne n'est qu'une densification de la suite de primitives.

Paramètres : `primitives` = ['droite', 'arc'], `spline` = interdite, `polyligne_brute` = interdite (source archivée à part).

Condition : familles bordures, ilots, surfaces (limites issues de lignes levées ou de fermetures).

Source : **PCRS_V2**, CNIG, Géostandard Plan de Corps de Rue Simplifié (PCRS) v2.0, §B.1.1 (p. 14) : seules les courbes formées de segments de droite et d'arcs (GM_LineString, GM_ArcString), en séquence, sont admises ; les splines sont exclues — <https://cnig.gouv.fr/IMG/documents_wordpress/2017/06/CNIG_RTGE_PCRS_v2.0_SoumisRevue.pdf>.
Source secondaire : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, regle_pas_rayon et pieces_courbes : la bordure se pose en éléments droits (cordes) ou en pièces courbes à rayon catalogue.

Confiance : haute ; applicabilité : immediate.

Implémentation : regulariser_geometrie.ajuster_polyligne (droites et arcs) ; regulariser.bordures, regulariser.lignes_partition.

Notes : Une bordure se fabrique en éléments de 1 m (ou 0,5 m, pièces courbes) : une droite et des arcs tangents sont la description naturelle de l'ouvrage ; les ondulations du levé (DAO, dédoublonnage de la double arête, résidus raster) ne sont pas des formes réelles.

### GQ-PRI-002 (générer)

Les axes des lignes de marquage longitudinales sont décrits par des droites, des arcs et, si nécessaire, des clothoïdes (raccordements progressifs des bords de voie) ; une ligne oblique qui fait une cassure importante avec la ligne longitudinale lui est raccordée par une courbe de rayon approprié, voisin de celui des bords de chaussée.

Paramètres : `primitives` = ['droite', 'arc', 'clothoide'], `clothoide` = admise, utilisée seulement si droites et arcs ne tiennent pas la tolérance.

Condition : marquages de classe ligne (ML-*) ; transversales et passages : droites (géométrie normative FUS-SNP-004).

Source : **ODR19**, ASAM OpenDRIVE 1.9.0, chapitre 9 « Geometries », §9.1 à §9.6 : ligne de référence faite de droites, spirales (clothoïdes), arcs et cubiques paramétriques — <https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/09_geometries/09_02_road_reference_line.html>.
Source secondaire : **IISR7**, IISR 7e partie « Marques sur chaussées », version consolidée VC20250404, art. 115-4 (lignes obliques) : cassure raccordée « par une courbe de rayon approprié ».

Confiance : haute ; applicabilité : immediate.

Implémentation : regulariser.marquages (droites et arcs ; aucune ligne du site n'a demandé de clothoïde dans sa tolérance).

### GQ-PRI-003 (générer)

Chaque entité régularisée porte sa suite de primitives (type, s0, s1, point de départ en Lambert-93, cap de départ, courbure, rayon) et sa polyligne densifiée ; la suite de primitives fait foi, la polyligne en est l'échantillonnage. Les abscisses s des primitives sont celles de la polyligne densifiée.

Paramètres : `champ` = geometrie_reguliere, `cles_primitive` = ['type', 's0', 's1', 'x0', 'y0', 'cap0_rad', 'k0', 'k1 (clothoïde)', 'rayon_m (arc)', 'coin (premier élément après un coin voulu)'].

Condition : toutes les entités régularisées.

Source : **INTERNE**, Proposition de la synthèse « qualité géométrique » (convention de description), contrat Claude décrit / Houdini fabrique (ARCHITECTURE.md §1.1) — <file:///D:/ClaudeCode_RoadCreation/recon/pcg/ARCHITECTURE.md>.

Confiance : haute ; applicabilité : immediate.

## Continuité et coins voulus

### GQ-CON-001 (contraindre)

Continuité de position et de tangente (G1) partout, sauf aux coins voulus (GQ-CON-002) : au raccord de deux primitives, le saut de cap est nul (≤ 0,01° numériquement) ; sur la polyligne densifiée, aucune cassure > 1° hors des coins voulus (mesure GQ-VAL-001). Pas de lacune dans une ligne.

Paramètres : `saut_cap_raccord_max_deg` = 0.01, `cassure_polyligne_max_deg` = 1.0, `lacune_max_m` = 0.0.

Condition : toutes les entités régularisées.

Source : **ODR19**, ASAM OpenDRIVE 1.9.0, §9.2 « Road reference line », « A road reference line shall have no gaps. » ; « A road reference line should have no kinks. » — <https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/09_geometries/09_02_road_reference_line.html>.
Source secondaire : **IISR7**, IISR 7e partie, art. 115-4 : raccordement des cassures par une courbe.

Confiance : haute ; applicabilité : immediate.

Implémentation : paramétrisation intrinsèque (départ, cap, pièces L/k) : G1 par construction.

Notes : Les cassures visibles dans UE (marches, coins vifs des bords de trottoir) viennent des sommets levés repris tels quels ; la paramétrisation intrinsèque les rend impossibles.

### GQ-CON-002 (contraindre)

Un coin (G0) n'est admis que s'il est voulu : la déviation est d'au moins 20°, un congé constructible (rayon ≥ 0,25 m et longueur ≥ longueur minimale de pièce) passerait à plus de la tolérance du sommet levé, et le sommet est porté par deux alignements droits (écart ≤ T sur ≤ 1 m de part et d'autre) ou dévie de 45° au moins. Position du coin : intersection des deux alignements ajustés si elle est à ≤ 1,5 T du sommet levé. Cas typiques : retours et abouts de bordure, angles de jardinière, angles de bâtiment, encoches de quai.

Paramètres : `deviation_min_deg` = 20, `deviation_sans_alignements_deg` = 45, `rayon_conge_min_m` = 0.25, `fenetre_alignement_m` = 1.0, `deplacement_coin_max_ratio_T` = 1.5.

Condition : toutes les polylignes à régulariser ; dernier recours : un tronçon hors tolérance reçoit un coin à son sommet le plus dévié (au plus 6 fois).

Source : **INTERNE**, Proposition de la synthèse « qualité géométrique », critère déduit de la tolérance (GQ-TOL-001) et des pièces constructibles (GQ-RAY-001, GQ-SEG-001) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/REGLES_QUALITE_GEOMETRIQUE.md>.
Source secondaire : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, quarts_de_rond (R 0,25) : la pièce la plus serrée du catalogue.
Source secondaire : **PCRS_V2**, CNIG PCRS v2.0, §B.3 ObjetVecteurPCRS (p. 37) : un point levé sur toute rupture, sur lequel s'appuie la géométrie.

Confiance : moyenne ; applicabilité : immediate ; conflits : CF-GQ-01.

### GQ-CON-003 (vérifier)

La continuité de courbure (G2) n'est pas exigée pour les bordures et les limites (pose en éléments droits et pièces courbes : droite et arc se raccordent tangentiellement sans clothoïde) ; elle est mesurée et rapportée (sauts de courbure aux raccords, peignes de courbure). Pour les axes de marquage suivant un bord de voie à clothoïde, un saut de courbure > 0,05 m⁻¹ est signalé.

Paramètres : `g2_bordures` = non exigé (mesuré), `saut_courbure_signale_axes_m_1` = 0.05.

Condition : rapport de régularisation, peignes de courbure.

Source : **ODR19**, ASAM OpenDRIVE 1.9.0, §9.4 Spiral : raccordement progressif de courbure entre droite et arc — <https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/09_geometries/09_04_spiral.html>.

Confiance : moyenne ; applicabilité : immediate.

## Tolérances par source

### GQ-TOL-001 (contraindre)

L'écart entre la géométrie régularisée et la source (distance symétrique, points de la source vers la courbe et courbe vers la polyligne source) respecte la tolérance T de la source : 99 % des écarts ≤ T et aucun > 1,5 T (gabarit de l'arrêté du 16/09/2003, art. 5 : 1 % au-delà de T, aucun au-delà de 1,5 T). T par source : levé GAM 2026 0,03 m ; plan projet 2025 calé 0,05 m ; PCRS 2019 (classe 10 cm) 0,10 m ; LiDAR, ortho 2022, v1 0,10 m ; aires OSM 0,30 m ; fermetures d'origine raster 0,25 m ; bordures a priori (ponts, ceintures) 0,05 m ; règles 0,02 m.

Paramètres : `T_m` = {'gam': 0.03, 'plan2025': 0.05, 'pcrs2019': 0.1, 'lidar2021': 0.1, 'ortho2022': 0.1, 'v1': 0.1, 'osm': 0.3, 'fermeture_raster': 0.25, 'a_priori': 0.05, 'regle': 0.02, 'xodr': 0.02}, `quantile_ratio` = 0.99, `max_ratio_T` = 1.5.

Condition : toute entité régularisée ; la source la plus précise de l'entité fixe T.

Source : **ARR2003**, Arrêté du 16 septembre 2003 portant sur les classes de précision applicables aux catégories de travaux topographiques (présentation CNIG Geopos, rappel de l'art. 5), art. 5 : au plus 1 % des écarts au-delà de T = k·[yy], aucun au-delà de 1,5·T (k = 3,23 en dimension 1) — <https://cnig.gouv.fr/IMG/documents_wordpress/2021/03/Geopos_arrete2003.pdf>.
Source secondaire : **PCRS_V2**, CNIG PCRS v2.0, §A.2 (p. 7) : objets vecteurs du PCRS de classe de précision 10 cm (arrêté de 2003).
Source secondaire : **LOC_PLAN2025**, Plan projet 2025, raster calé par affine (261 points, RMSE 0,030 m), data/sites/paquet_jardin/plan_projet_2025/georef.json.
Source secondaire : **BOFIP_TOPO**, BOFIP BOI-CAD-TOPO-60 (classes de précision, arrêté du 16/09/2003), relations entre classes et vérification (art. 5).

Confiance : moyenne ; applicabilité : immediate ; conflits : CF-GQ-01, CF-GQ-02.

Notes : T du GAM : levé topographique de récolement (classe centimétrique non publiée) ; 3 cm laisse passer le bruit de numérisation DWG et les deux arêtes dédoublonnées, pas une forme fausse. Points au-delà de 1,5 T : coin ajouté (GQ-CON-002) ou entité signalée « hors_tolerance ».

### GQ-TOL-002 (contraindre)

Pas de biais systématique : l'ajustement est refusé si l'écart moyen des points de la source dépasse T / 2 (contrainte) ; le contrôle signale un écart moyen au-delà de T / 3,23 (condition d'écart moyen de l'arrêté du 16/09/2003 en dimension 1 : Emoy ≤ [yy] avec T = 3,23·[yy]). Une source bruitée (PCRS, ortho) peut dépasser T / 3,23 sans biais : avertissement seulement.

Paramètres : `k_dimension_1` = 3.23, `ecart_moyen_signale_ratio_T` = 0.31, `ecart_moyen_max_ratio_T` = 0.5.

Condition : toute entité régularisée.

Source : **ARR2003**, Arrêté du 16 septembre 2003 (présentation CNIG Geopos), art. 5, première condition (écart moyen en position) — <https://cnig.gouv.fr/IMG/documents_wordpress/2021/03/Geopos_arrete2003.pdf>.

Confiance : moyenne ; applicabilité : immediate.

### GQ-TOL-003 (contraindre)

Ajustement robuste : résidus pondérés de Huber (seuil T/2) pour qu'un sommet aberrant isolé (pointe de levé, saut de dédoublonnage) ne déforme pas la ligne ; les allers-retours (> 170°) et les sommets à moins de 5 mm sont retirés avant l'ajustement.

Paramètres : `huber_ratio_T` = 0.5, `pointe_deg` = 170, `fusion_sommets_m` = 0.005.

Condition : toute polyligne source.

Source : **PCRS_V2**, CNIG PCRS v2.0, §B.1.3 (p. 15) : aucun segment de longueur nulle (points confondus dans la précision du levé) — <https://cnig.gouv.fr/IMG/documents_wordpress/2017/06/CNIG_RTGE_PCRS_v2.0_SoumisRevue.pdf>.
Source secondaire : **RC_TQ_SOL_001**, regles_conception.json TQ-SOL-001, sommets à moins de 5 mm fusionnés.

Confiance : moyenne ; applicabilité : immediate.

## Longueurs minimales et parcimonie

### GQ-SEG-001 (contraindre)

Pas de micro-pièce : longueur minimale d'une primitive de 0,50 m pour une bordure (un demi-élément ; 0,20 m pour un arc de rayon ≤ 1,2 m, pièce courbe ou quart de rond du catalogue), 0,30 m pour une limite de surface, 0,50 m pour un axe de marquage ; un tronçon entre deux coins plus court est une seule droite. Aucun segment < 5 mm dans la polyligne densifiée.

Paramètres : `bordure_m` = 0.5, `bordure_arc_serre_m` = 0.2, `limite_surface_m` = 0.3, `marquage_m` = 0.5, `segment_polyligne_min_m` = 0.005.

Condition : toutes les entités régularisées.

Source : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, element (0,994 m / 0,494 m), pieces_courbes (R 0,5 à 9 m), quarts_de_rond (R 0,25) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/bordures_elements.json>.
Source secondaire : **RC_TQ_SOL_001**, regles_conception.json TQ-SOL-001, arêtes de moins de 5 mm fusionnées.

Confiance : moyenne ; applicabilité : immediate.

### GQ-SEG-002 (générer)

Parcimonie : le nombre de primitives est le plus petit qui tient la tolérance ; deux primitives voisines sont fusionnées dès que la tolérance le permet ; un objet continu n'est pas découpé sans raison (profil, coin, bout).

Paramètres : `strategie` = découpe au pire point tant que l'écart dépasse T, puis fusion des raccords inutiles.

Condition : toutes les entités régularisées.

Source : **PCRS_V2**, CNIG PCRS v2.0, §B.1.3 (p. 15) : « limiter le plus possible le découpage d'objets linéaires continus » — <https://cnig.gouv.fr/IMG/documents_wordpress/2017/06/CNIG_RTGE_PCRS_v2.0_SoumisRevue.pdf>.

Confiance : moyenne ; applicabilité : immediate.

## Rayons

### GQ-RAY-001 (contraindre)

Rayon minimal d'un arc de bordure : 0,25 m (quart de rond TU/I1/I2 R 25) ; de 0,25 à 0,75 m, pièce courbe (R 0,5) ; de 0,75 à 3 m, pièce courbe du catalogue ou éléments courts ; au-delà, éléments droits de 0,5 ou 1 m posés en corde (flèche ≤ 10,5 mm). Les limites de surface et les axes de marquage suivent un rayon minimal de 0,20 m.

Paramètres : `rayon_min_bordure_m` = 0.25, `rayon_min_autres_m` = 0.2, `table_pose` = regle:bordures_elements.regle_pas_rayon.

Condition : arcs des bordures (courbes recalculées depuis les primitives : champ courbes).

Source : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, regle_pas_rayon (table) et quarts_de_rond (R 0,25) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/bordures_elements.json>.

Confiance : moyenne ; applicabilité : immediate.

### GQ-RAY-002 (vérifier)

Rayons de bordure d'angle en bord de chaussée circulée : 3-4 m très serré (sans bus ni PL), 5-6 m serré, 8-10 m normal, 12 m ligne de bus régulière, 16-20 m à éviter en urbain dense. Un arc de bordure qui longe une voie circulée (driving/bus) et tourne de plus de 45° avec un rayon < 3 m est signalé (sauf nez d'îlot, GQ-RAY-004) ; le rayon levé prime toujours (GA-RAY-001).

Paramètres : `classes_m` = [[3, 4], [5, 6], [8, 10], [12, 12], [16, 20]], `rayon_angle_min_signale_m` = 3.0, `deviation_angle_min_deg` = 45.

Condition : bordures dont le côté bas est une voie OpenDRIVE driving/bus.

Source : **LYON_DIM**, Métropole de Lyon, Référentiel de conception et de gestion des espaces publics : Cohérence des dimensions, p. 10 « Giration des véhicules, calcul des rayons de courbure » — <file:///D:/ClaudeCode_RoadCreation/data/raw/normes/metropoles/grandlyon_referentiel_coherence_dimensions_2010.pdf>.
Source secondaire : **RC_GA_RAY_001**, regles_conception.json GA-RAY-001 / GA-RAY-002, rayons d'angle et véhicules de projet.

Confiance : moyenne ; applicabilité : immediate.

### GQ-RAY-003 (générer)

Rayons normalisés : un arc est ramené au rayon le plus proche de la série (catalogue de pièces : 0,25 ; 0,5 ; 1,2 ; 1,4 ; 1,6 ; 1,8 ; 2 ; 3 ; 4 ; 5 ; 6 ; 7 ; 8 ; 9 m ; rayons de projet : 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400, 500 m) si l'écart de rayon est ≤ 10 % et que la tolérance GQ-TOL-001 reste tenue ; un arc dont la flèche L²/(8R) est < T/2 (ou R > 500 m) devient une droite dans les mêmes conditions.

Paramètres : `serie_m` = [0.25, 0.5, 1.2, 1.4, 1.6, 1.8, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 150.0, 200.0, 250.0, 300.0, 400.0, 500.0], `ecart_rayon_max_ratio` = 0.1, `fleche_droite_max_ratio_T` = 0.5.

Condition : arcs de toutes les entités régularisées.

Source : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, regle_pas_rayon.pieces_courbes.rayons_m (choix du rayon catalogue le plus proche, écart ≤ 10 %) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/bordures_elements.json>.
Source secondaire : **LYON_DIM**, Métropole de Lyon, Cohérence des dimensions, p. 10 : rayons de projet en valeurs rondes (3-4, 5-6, 8-10, 12, 16-20 m).

Confiance : moyenne ; applicabilité : immediate ; conflits : CF-GQ-02.

Notes : La série au-delà de 9 m est une convention de dessin (valeurs rondes), non une norme : elle ne s'applique que dans la tolérance de la source.

### GQ-RAY-004 (vérifier)

Nez d'îlot : arrondi de rayon 0,25 à 1,5 m (deux quarts de rond R 0,25 dos à dos, pièce courbe R 0,5, ou arcs du catalogue jusqu'à 1,5 m) ; un nez vif (coin) n'est admis que si le levé le montre (GQ-CON-002). Le rayon de nez décrit (ilots.nez.rayon_m) est relu sur les primitives.

Paramètres : `rayon_min_m` = 0.25, `rayon_max_m` = 1.5.

Condition : îlots (famille ilots), sommets convexes du contour.

Source : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, quarts_de_rond.usage : « nez d'îlot arrondi R 0,25 : 2 quarts de rond dos à dos » — <file:///D:/ClaudeCode_RoadCreation/assets/specs/bordures_elements.json>.
Source secondaire : **IISR7**, IISR 7e partie, art. 117-2 B (îlots) ; nez : regle:bordures_elements.quarts_de_rond (cité par GA-ILO-007).

Confiance : moyenne ; applicabilité : immediate.

## Topologie

### GQ-TOP-001 (contraindre)

Deux bouts de bordure distants de moins de 1,5·max(T) (10 cm au plus) partagent un nœud exact (même coordonnée) ; si les deux bordures se prolongent (écart de direction ≤ 15°), elles partagent aussi le cap au nœud (G1 à travers le nœud) ; sinon le nœud est un coin.

Paramètres : `accrochage_ratio_T` = 1.5, `accrochage_max_m` = 0.1, `prolongement_max_deg` = 15.

Condition : bouts de bordures (familles bordures, ceintures d'îlots).

Source : **PCRS_V2**, CNIG PCRS v2.0, §B.1.3 (p. 15) : un objet continu représenté par plusieurs objets « partageant une extrémité commune de même planimétrie et altimétrie aux tolérances de précisions près » — <https://cnig.gouv.fr/IMG/documents_wordpress/2017/06/CNIG_RTGE_PCRS_v2.0_SoumisRevue.pdf>.
Source secondaire : **RC_TQ_SOL_001**, regles_conception.json TQ-SOL-001, arcs partagés identiques, sans trou ni recouvrement.
Source secondaire : **RC_GA_BOR_005**, regles_conception.json GA-BOR-005, contacts entre bouts de bordure.

Confiance : haute ; applicabilité : immediate.

### GQ-TOP-002 (contraindre)

Un bout de bordure à moins de 1,5·max(T) de l'intérieur d'une autre bordure (contact en T) est posé exactement sur la courbe régularisée de celle-ci (projection orthogonale), après la régularisation de la bordure traversante.

Paramètres : `accrochage_ratio_T` = 1.5, `accrochage_max_m` = 0.1.

Condition : bouts de bordure sans nœud bout à bout.

Source : **RC_TQ_SOL_001**, regles_conception.json TQ-SOL-001, topologie 2D préparée avant Houdini (accrochages, aucun trou) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/regles_conception.json>.

Confiance : haute ; applicabilité : immediate.

### GQ-TOP-003 (contraindre)

Une bordure en anneau dont la lacune de fermeture est ≤ 1,5 T est refermée exactement (anneau G1 si aucun coin, sinon départ au premier coin) ; au-delà la lacune est réelle (ceinture synthétique d'îlot, ilots.py).

Paramètres : `fermeture_max_ratio_T` = 1.5, `longueur_min_anneau_m` = 4.0.

Condition : bordures dont les bouts se rejoignent.

Source : **PCRS_V2**, CNIG PCRS v2.0, §B.1.3 : extrémités communes aux tolérances près — <https://cnig.gouv.fr/IMG/documents_wordpress/2017/06/CNIG_RTGE_PCRS_v2.0_SoumisRevue.pdf>.

Confiance : haute ; applicabilité : immediate.

### GQ-TOP-004 (vérifier)

La partition des surfaces est reconstruite à partir des limites régularisées : 0 trou et 0 recouvrement (aire(union) = Σ aires à 1e-6 m² près, carré de 300 m), limites partagées identiques (une arête n'existe qu'une fois), aucune arête < 5 mm.

Paramètres : `tolerance_aire_m2` = 1e-06, `arete_min_m` = 0.005.

Condition : famille surfaces (partition vectorielle, surfaces.py).

Source : **RC_TQ_SOL_001**, regles_conception.json TQ-SOL-001, contrôle aire(union) = somme(aires), 0 recouvrement — <file:///D:/ClaudeCode_RoadCreation/assets/specs/regles_conception.json>.

Confiance : haute ; applicabilité : immediate.

### GQ-TOP-005 (générer)

Toute géométrie dépendante est re-dérivée de la géométrie régularisée : abscisses des intervalles de profil, des abaissés, des chartières et des courbes de pose remappées par projection sur la nouvelle ligne (ordre et partition exacte de [0, L] conservés) ; Z interpolé à l'abscisse remappée ; arête arrière, emprises, rampes et surfaces recalculées par la partition ; interruptions des lignes de marquage remappées.

Paramètres : `remappage` = projection orthogonale de l'ancien point sur la nouvelle courbe, puis monotonie forcée.

Condition : entités régularisées et tout ce qui en dépend.

Source : **INTERNE**, Proposition de la synthèse « qualité géométrique », cohérence de la description (une seule géométrie de référence) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/REGLES_QUALITE_GEOMETRIQUE.md>.

Confiance : haute ; applicabilité : immediate.

## Largeurs constantes et parallélisme

### GQ-LAR-001 (contraindre)

Largeur constante : une limite levée (revêtement, végétation, talus) qui longe l'arête arrière d'une bordure à une distance dont la variation reste ≤ 2·T (et ≤ 6 cm) sur au moins 5 m est remplacée, sur ce tronçon, par le décalé exact de la bordure régularisée à la distance médiane (trottoir, piste, séparateur ou bande à largeur constante) ; raccords aux bouts par la limite levée régularisée.

Paramètres : `variation_largeur_max_ratio_T` = 2.0, `variation_largeur_max_m` = 0.06, `longueur_min_m` = 5.0, `distance_max_m` = 6.0, `parallelisme_max_deg` = 5.0.

Condition : limites GAM (limite_revetement, vegetation, talus_haut, talus_bas) le long des bordures.

Source : **PARIS_SH**, Ville de Paris, Guide de la signalisation horizontale (2015), § files de circulation : lignes « généralement tracées parallèlement à la bordure » (largeurs d'axe en axe constantes) — <file:///D:/ClaudeCode_RoadCreation/data/raw/normes/metropoles/paris_guide_signalisation_horizontale.pdf>.
Source secondaire : **LYON_DIM**, Métropole de Lyon, Cohérence des dimensions, largeurs de cheminement et de trottoir fixées par profil type.
Source secondaire : **INTERNE**, pratique de dessin VRD (profils en travers types), décalés parallèles de l'arête de référence.

Confiance : moyenne ; applicabilité : immediate.

### GQ-PAR-001 (contraindre)

Les lignes de marquage longitudinales sont parallèles au bord de voie ou à la bordure qu'elles longent : une ligne (≥ 2 m) qui longe sur toute sa longueur une bordure à moins de 1,5 m, à distance variant de moins de min(2T, 6 cm), devient le décalé exact de la bordure régularisée à la distance médiane (si la tolérance GQ-TOL-001 reste tenue) ; le contrôle signale toute ligne à moins de 1,5 m d'une bordure, parallèle à 5° près, dont la distance à la face varie de plus de 3 cm. Aucune ligne ne croise l'arête avant d'une bordure (GQ-VAL-002).

Paramètres : `distance_max_m` = 1.5, `parallelisme_max_deg` = 5.0, `variation_distance_max_m` = 0.03, `longueur_min_m` = 2.0.

Condition : marquages de classe ligne (hors sur_bordure).

Source : **PARIS_SH**, Ville de Paris, Guide de la signalisation horizontale (2015), « Les lignes sont généralement tracées parallèlement à la bordure » — <file:///D:/ClaudeCode_RoadCreation/data/raw/normes/metropoles/paris_guide_signalisation_horizontale.pdf>.
Source secondaire : **RC_GA_ILO_007**, regles_conception.json GA-ILO-007, face de bordure à 3,5u de l'axe de la ligne d'îlot.

Confiance : moyenne ; applicabilité : immediate.

## Régularité des ouvrages (traversées, bateaux, quais)

### GQ-SYM-001 (vérifier)

Passage piéton : bandes parallèles à l'axe de la chaussée (cap identique dans une traversée), de même longueur, de largeur 0,50 m, intervalle constant (0,50 à 0,80 m) pour une même traversée ; dimensions prises perpendiculairement à l'axe de la chaussée même pour une traversée biaise.

Paramètres : `largeur_bande_m` = 0.5, `intervalle_m` = [0.5, 0.8], `ecart_cap_max_deg` = 1.0, `ecart_longueur_max_m` = 0.0.

Condition : marquages de classe passage type zebra (géométrie paramétrique FUS-SNP-004).

Source : **IISR7**, IISR 7e partie « Marques sur chaussées », art. 118 : bandes rectangulaires « parallèles à l'axe de la chaussée », largeur 0,50 m, interdistance 0,50 à 0,80 m — <https://equipementsdelaroute.cerema.fr/IMG/pdf/iisr_7epartie_vc_20250404.pdf>.
Source secondaire : **PARIS_SH**, Ville de Paris, Guide de la signalisation horizontale, §9 Passages pour piétons : espacement « constant pour une même traversée », dimensions perpendiculaires à l'axe même pour les traversées biaises.

Confiance : haute ; applicabilité : immediate.

### GQ-SYM-002 (vérifier)

Abaissé de traversée : la bordure est rectiligne en plan sur la partie abaissée (droite, ou arc de rayon ≥ 12 m posé en éléments de 1 m), pour que la traversée soit perpendiculaire au trottoir et que la BEV ne soit pas dans l'arrondi ; un abaissé dans un arc plus serré est signalé.

Paramètres : `rayon_min_abaisse_m` = 12.0.

Condition : abaissés de type traversee (bordures.abaisses).

Source : **LYON_ACC**, Métropole de Lyon, Recueil sur l'accessibilité des aménagements (2021), « La traversée créée doit être la plus perpendiculairement possible du trottoir afin que la BEV ne soit pas dans l'arrondi » — <file:///D:/ClaudeCode_RoadCreation/data/raw/normes/metropoles/grandlyon_recueil_accessibilite_amenagements_2021.pdf>.
Source secondaire : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, regle_pas_rayon : éléments de 1 m si R ≥ 12 m.

Confiance : moyenne ; applicabilité : immediate.

### GQ-SYM-003 (contraindre)

Quai de bus en ligne ou en avancée : bordure de quai en alignement droit avec le bord de chaussée ; la partie QUAI_BUS d'une bordure est ajustée en une seule droite si la tolérance le permet, sinon signalée (quai en courbe à proscrire).

Paramètres : `primitive_quai` = droite, `rayon_min_toléré_m` = 500.

Condition : intervalles de profil QUAI_BUS.

Source : **CEREMA_BUS2018**, Cerema, Points d'arrêt de bus et de car accessibles à tous (2018), p. 73-75 : « le quai est en alignement droit avec le bord de la chaussée » ; arrêté du 15/01/2007 art. 1er §12 : quais en alignement droit obligatoires en milieu urbain sauf impossibilité, arrêt le long d'un trottoir en courbe à proscrire — <file:///D:/ClaudeCode_RoadCreation/data/raw/normes/cerema/cerema_points_arret_bus_car_accessibles_2018.pdf>.

Confiance : haute ; applicabilité : immediate.

## Orientation des bordures

### GQ-ORI-001 (contraindre)

Les voies circulées driving et bus de l'OpenDRIVE 2026 (lanes_2026, échantillonneur xodr) sont toujours du côté BAS d'une bordure (à droite de la polyligne, face vue). Test : points à 0,3 / 0,6 / 1,0 / 1,5 m de part et d'autre, rayons arrêtés à la première autre bordure rencontrée ; si la part de voie circulée du côté haut est ≥ 0,5 et dépasse d'au moins 0,3 celle du côté bas, la bordure est retournée (intervalles, abaissés, chartières, courbes, caniveau et bouts remappés), le conflit avec le critère d'origine (MNT, relief) est journalisé.

Paramètres : `decalages_m` = [0.3, 0.6, 1.0, 1.5], `part_min_ratio` = 0.5, `marge_ratio` = 0.3, `types_voie` = ['driving', 'bus'].

Condition : toutes les bordures ; avant la partition (les surfaces dépendantes sont re-dérivées).

Source : **LOC_REVUE_P6**, Revue adverse du solveur de cohérence, constat P6 (repli « cote_haut_relief » : côté haut vers la chaussée sur KS-0669-1, KS-0666-1, K-0666, KS-0382-1, KS-0632-1, KS-0588-1, KS-0563-1), recon/out/paquet_jardin/v2/description/coherence (revue) — <file:///D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/description/coherence/REPORT.md>.
Source secondaire : **LOC_V2DESC**, README recon/pcg : convention d'orientation des bordures, « côté haut à gauche, face vue à droite ».
Source secondaire : **SPEC_BORD_EL**, assets/specs/bordures_elements.json, repere.element : polyligne d'arête avant orientée trottoir à gauche.

Confiance : haute ; applicabilité : immediate ; conflits : CF-GQ-03.

### GQ-ORI-002 (contraindre)

Sans voie OpenDRIVE adjacente, et si le MNT n'est pas décisif (|dz| < 2,5 cm, critère d'origine « cote_haut_relief », « surfaces_v1 » ou « defaut »), la classe d'indice v1 tranche : chaussée ou parking du côté haut (≥ 0,6) et trottoir, quai, îlot ou espace vert du côté bas (≥ 0,6) : la bordure est retournée. Avec une voie adjacente, la classe raster n'est qu'un contrôle : un désaccord est journalisé.

Paramètres : `part_classe_min_ratio` = 0.6, `dz_decisif_m` = 0.025, `classes_basses` = ['chaussee', 'parking', 'acces_riverain'], `classes_hautes` = ['trottoir', 'quai_bus', 'ilot', 'terre_plein_vegetal', 'espace_vert'].

Condition : bordures sans voie circulée adjacente.

Source : **LOC_REVUE_P6**, Revue adverse du solveur de cohérence, constat P6, classe chaussée du côté haut (KS-0588-1, KS-0563-1) — <file:///D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/description/coherence/REPORT.md>.

Confiance : moyenne ; applicabilité : immediate.

### GQ-ORI-003 (vérifier)

Deux bordures qui se prolongent (nœud G1 de GQ-TOP-001) ont le même sens : la fin de l'une est le début de l'autre. Un sens opposé est signalé (il indique une orientation douteuse de l'une des deux).

Paramètres : `prolongement_max_deg` = 15.

Condition : nœuds G1 entre bordures.

Source : **INTERNE**, Proposition de la synthèse « qualité géométrique », continuité d'une file de bordures (côté haut constant le long d'une file) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/REGLES_QUALITE_GEOMETRIQUE.md>.

Confiance : moyenne ; applicabilité : immediate.

## Densification et provenance

### GQ-DEN-001 (générer)

Polyligne densifiée depuis les primitives : flèche de corde ≤ 2 mm, pas ≤ 0,5 m sur les bordures (un Z par sommet) et ≤ 1 m sur les limites de surface, sommet à chaque raccord de primitives et à chaque coin ; les axes de marquage droits gardent leurs deux bouts.

Paramètres : `fleche_max_m` = 0.002, `pas_max_bordure_m` = 0.5, `pas_max_limite_m` = 1.0, `pas_max_marquage_m` = None.

Condition : toutes les entités régularisées.

Source : **INTERNE**, Proposition de la synthèse « qualité géométrique », cohérent avec TQ-MQG-013 (erreur de corde ≤ 1 mm pour les glyphes) et TQ-BOR-007 (flèche de corde des éléments ≤ 10,5 mm) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/regles_conception.json>.

Confiance : haute ; applicabilité : immediate.

### GQ-PRO-001 (générer)

Provenance : la source levée reste dans prov.geometrie ; prov.regularisation ajoute src = regle:regles_qualite_geometrique.GQ-TOL-001, l'écart maximal, l'écart p99 et la tolérance ; la géométrie source (avant régularisation) est archivée dans base/regularisation_sources.geojson (non fabriquée) pour les contrôles et les planches.

Paramètres : `archive` = base/regularisation_sources.geojson.

Condition : toutes les entités régularisées.

Source : **LOC_V2DESC**, README recon/pcg : provenance par attribut, prov {attribut: {src, ref, conf}} — <file:///D:/ClaudeCode_RoadCreation/recon/pcg/README.md>.

Confiance : haute ; applicabilité : immediate.

## Contrôles

### GQ-VAL-001 (vérifier)

Histogramme des cassures avant / après : cassure discrète à chaque sommet = |déviation au sommet − déviation attendue de la courbure voisine| ; 0 cassure > 1° hors coins voulus après régularisation ; rapport par famille et par source.

Paramètres : `seuils_deg` = [0.5, 1, 2, 5, 10, 30], `cassure_max_apres_deg` = 1.0.

Condition : toutes les entités régularisées.

Source : **ODR19**, ASAM OpenDRIVE 1.9.0 §9.2, « should have no kinks » — <https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/09_geometries/09_02_road_reference_line.html>.

Confiance : haute ; applicabilité : immediate.

### GQ-VAL-002 (vérifier)

Dégagement des marquages aux bordures après régularisation : aucune ligne, transversale ou bande de passage ne croise l'arête avant d'une bordure (hors marques portées sur bordure et interruptions décrites) ; l'axe d'une ligne longeant une bordure reste à ≥ largeur/2 + 0,05 m de la face.

Paramètres : `degagement_min_m` = 0.05.

Condition : marquages × bordures régularisées.

Source : **RC_MQ_DET_010**, regles_conception.json MQ-DET-010 / MQ-LIG-002, interruptions des marques aux bordures et obstacles — <file:///D:/ClaudeCode_RoadCreation/assets/specs/regles_conception.json>.

Confiance : moyenne ; applicabilité : immediate.

### GQ-VAL-003 (vérifier)

Revue visuelle : planches avant / après sur l'ortho 2022 (coins, nez d'îlots, trottoirs de la capture utilisateur, traversée Verdun SO, trottoir NE, arrêt de bus) et peignes de courbure de 5 bordures, regardées avant livraison.

Paramètres : `zooms_n` = 6, `peignes_n` = 5.

Condition : chaque régénération de la description.

Source : **INTERNE**, Proposition de la synthèse « qualité géométrique », pratique de contrôle des tracés (peigne de courbure) — <file:///D:/ClaudeCode_RoadCreation/assets/specs/REGLES_QUALITE_GEOMETRIQUE.md>.

Confiance : haute ; applicabilité : immediate.

## Conflits

- **CF-GQ-01** (Continuité G1 contre fidélité au levé) : la tolérance prime : si aucune chaîne G1 constructible ne tient T, un coin voulu est ajouté au sommet le plus dévié (GQ-CON-002), au plus 6 fois ; sinon la source nettoyée est gardée et signalée « source_gardee » — principe : on ne déforme pas un ouvrage levé pour le lisser ; règles GQ-CON-001, GQ-CON-002, GQ-TOL-001.
- **CF-GQ-02** (Rayon normalisé contre tolérance) : le rayon n'est arrondi que si la tolérance reste tenue après réajustement des autres pièces — principe : mesure > convention de dessin ; règles GQ-RAY-003, GQ-TOL-001.
- **CF-GQ-03** (Orientation des bordures : voies OpenDRIVE contre MNT 2026) : une voie driving/bus adjacente (sans bordure intermédiaire) fixe le côté bas, même contre le MNT : le MNT 2026 garde par endroits des niveaux 2021 ou de chantier ; chaque retournement contraire au MNT est journalisé (rapport_regularisation.json, orientation) — principe : sémantique 2026 > relief interpolé ; règles GQ-ORI-001, GQ-ORI-002.

## Sources

- **PCRS_V2** : CNIG, Géostandard Plan de Corps de Rue Simplifié (PCRS) v2.0 (version soumise à revue, 2017) <https://cnig.gouv.fr/IMG/documents_wordpress/2017/06/CNIG_RTGE_PCRS_v2.0_SoumisRevue.pdf> ; copie locale `data/raw/normes/geometrie/cnig_pcrs_v2.0_geostandard.pdf`.
- **ODR19** : ASAM OpenDRIVE 1.9.0, chapitre 9 « Geometries » (9.2 Road reference line, 9.3 Straight line, 9.4 Spiral, 9.5 Arc, 9.6 Parametric cubic curve) <https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.9.0/specification/09_geometries/09_02_road_reference_line.html>.
- **ARR2003** : Arrêté du 16 septembre 2003 portant sur les classes de précision applicables aux catégories de travaux topographiques (rappel de l'art. 5 par la commission Geopos du CNIG, oct. 2020) <https://cnig.gouv.fr/IMG/documents_wordpress/2021/03/Geopos_arrete2003.pdf> ; copie locale `data/raw/normes/geometrie/cnig_geopos_arrete2003_classes_precision.pdf`.
- **BOFIP_TOPO** : BOFIP, BOI-CAD-TOPO-60 (classes de précision de l'arrêté du 16/09/2003) <https://bofip.impots.gouv.fr/node/9575>.
- **IISR7** : IISR 7e partie « Marques sur chaussées », version consolidée VC20250404 (Cerema / DSR-DGITM) <https://equipementsdelaroute.cerema.fr/IMG/pdf/iisr_7epartie_vc_20250404.pdf> ; copie locale `data/raw/normes/cerema/iisr_7epartie_vc_20250404.pdf`.
- **PARIS_SH** : Ville de Paris, Guide de la signalisation horizontale à Paris (11/03/2015) <https://cdn.paris.fr/paris/2019/07/24/c63bc81ff4044e9dd71a888afbb05306.pdf> ; copie locale `data/raw/normes/metropoles/paris_guide_signalisation_horizontale.pdf`.
- **LYON_DIM** : Métropole de Lyon, Référentiel de conception et de gestion des espaces publics : Cohérence des dimensions (2010) ; copie locale `data/raw/normes/metropoles/grandlyon_referentiel_coherence_dimensions_2010.pdf`.
- **LYON_ACC** : Métropole de Lyon, Recueil sur l'accessibilité des aménagements (2021) ; copie locale `data/raw/normes/metropoles/grandlyon_recueil_accessibilite_amenagements_2021.pdf`.
- **CEREMA_BUS2018** : Cerema, Points d'arrêt de bus et de car accessibles à tous : de la norme au confort (2018) ; copie locale `data/raw/normes/cerema/cerema_points_arret_bus_car_accessibles_2018.pdf`.
- **SPEC_BORD_EL** : assets/specs/bordures_elements.json (éléments, regle_pas_rayon, pièces courbes, quarts de rond) ; copie locale `assets/specs/bordures_elements.json`.
- **RC_TQ_SOL_001** : regles_conception.json TQ-SOL-001 (topologie 2D avant Houdini) ; copie locale `assets/specs/regles_conception.json`.
- **RC_GA_RAY_001** : regles_conception.json GA-RAY-001 / GA-RAY-002 ; copie locale `assets/specs/regles_conception.json`.
- **RC_GA_BOR_005** : regles_conception.json GA-BOR-005 ; copie locale `assets/specs/regles_conception.json`.
- **RC_GA_ILO_007** : regles_conception.json GA-ILO-007 ; copie locale `assets/specs/regles_conception.json`.
- **RC_MQ_DET_010** : regles_conception.json MQ-DET-010 / MQ-LIG-002 ; copie locale `assets/specs/regles_conception.json`.
- **LOC_PLAN2025** : Plan projet 2025, raster calé par affine (261 points, RMSE 0,030 m) ; copie locale `data/sites/paquet_jardin/plan_projet_2025/georef.json`.
- **LOC_REVUE_P6** : Revue adverse du solveur de cohérence (workflow concurrent), constat P6 : orientation des bordures en repli « cote_haut_relief » ; copie locale `recon/out/paquet_jardin/v2/description/coherence/`.
- **LOC_V2DESC** : recon/pcg/README.md (conventions de la description v2) ; copie locale `recon/pcg/README.md`.
- **INTERNE** : Proposition de la synthèse « qualité géométrique » (convention de dessin ou de contrôle, non normative).
