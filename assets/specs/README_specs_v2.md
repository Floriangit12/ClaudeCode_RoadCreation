# Specs V2 : marquages, éléments de bordure, matériaux de sol

Trois specs complètent `bordures.json`, `peinture.json` et `mobilier.json` pour la fabrication V2. Le principe : Claude décrit la scène en données vectorielles (`description_scene_v2`), Houdini la fabrique (HDAs `pj_*`, hython), UE 5.8 pose les assets.

Ces specs portent la seule géométrie normative. Houdini n'invente aucune valeur : chaque cote vient d'une entrée de spec, citée comme `src: "regle:<fichier>.<clé>"`.

| Fichier | Contenu | Utilisé par |
|---|---|---|
| `marquages_geometrie.json` | u, largeurs, modulations, lignes transversales, passages, hachures, zigzag, damiers, 13 gabarits polygonaux | `pj_marquages`, prototypes de symboles, `PG_Symboles` |
| `bordures_elements.json` | éléments et joints, pas selon le rayon, arêtes, épaufrures, jitter, abaissés et chartières, BEV, caniveaux, TU / AC1 / CS3 / quarts de rond, matériaux et aspect | `pj_bordure_prototypes`, `pj_bordure_pose`, `PG_Bordures`, `PG_Joints` |
| `materiaux_sol.json` | 34 `materiau_id` : texture CC0, tuile, albédo cible, rugosité, appareillage ou couche, chemins UE | `pj_sol`, `pj_ilot`, rendu Karma, remappage UE `MI_<id>` |

**Repère.**
- Scène : local = Lambert-93 − O (917279.43, 6460289.98), z = NGF − 216.30, en mètres, Z vers le haut. Une seule fonction de conversion.
- Gabarits : x latéral (positif à droite du sens de circulation), y longitudinal (sens de circulation).
- Profils : u, v, comme dans `bordures.json`.

## marquages_geometrie.json

Source principale : IISR 7e partie, version consolidée VC20250404. Chaque entrée cite son article ou son annexe, avec la page et sa confiance.

- **u et largeurs.** u vaut 5 cm par défaut, 6 cm sur Verdun si la décision n° 10 le retient. Les largeurs 2u / 3u / 5u valent 0,10 / 0,15 / 0,25 m avec u = 5 cm, et 0,12 / 0,18 / 0,30 m avec u = 6 cm.
- **Modulations (trait / vide, en m).**
  - T1 : 3 / 10 ; T'1 : 1,5 / 5 ; T2 : 3 / 3,5.
  - T'2 : 0,5 / 0,5 ; T3 : 3 / 1,33 ; T'3 : 20 / 6 ; T4 : 39 / 13.
  - La phase (`phase_m`) est portée par la description.
- **Lignes transversales.** STOP : continue de 0,50. Cédez : T'2 de 0,50. Effet des feux : T'2 de **0,15**.
- **Passages piétons.** Bandes de 0,50, vide de 0,50 à 0,80 (0,50 sur le site), longueur ≥ 2,50. Les lignes s'arrêtent à 0,50 m du passage.
- **Hachures.** Bande de 0,50, vide de 1,35, angle de 26,565° avec la rive.
- **Zigzag bus.** Jaune 2u, amplitude 2,50 à 45°, période 5,00 m.
- **Gabarits.** Polygones sans trou, ou avec trous pour les triangles, orientés dans le sens trigonométrique. Les arcs et ellipses sont discrétisés avec une erreur de corde ≤ 1 mm.

| Gabarit | Longueur × largeur (m) | Sommets | Aire (m²) | Origine | Confiance |
|---|---|---|---|---|---|
| TD (tout droit) | 4,00 × 0,70 | 7 | 1,000 | milieu du pied de la tige | haute (cotes B2) |
| TAD / TAG | 4,00 × 1,00 | 9 | 1,001 | idem (TAG = miroir) | haute |
| TD_TAD / TD_TAG | 4,00 × 1,275 | 14 | 1,600 | idem | haute (cotes B3) |
| RAB_D / RAB_G (rabattement) | 6,00 × 0,86 | 25 | 1,495 | axe × ligne de référence | moyenne : arcs R 21 et R 18,38 cotés, x de la tête mesurés sur le schéma (±2 cm) |
| CEDEZ_V60 | 2,00 × 1,00 (trait 0,10, bandeau 0,50) | 3 + 3 (trou) | 0,704 | pointe | moyenne |
| CEDEZ_V60P | 6,00 × 2,00 (trait 0,15, bandeau 1,00) | 3 + 3 | 3,215 | pointe | moyenne |
| VELO (figurine D1) | 1,28 × 0,80 | 63 (corps) + 2 × 40 (roues) | 0,413 | milieu du bas | moyenne : corps vectorisé depuis l'image de l'annexe, ±5 mm |
| DAMIER_BUS | 1,00 × 1,00 (0,80 à 1,20) | 4 | 1,000 | centre | haute ; disposition non cotée |
| PAVE_CHRONOVELO | 0,37 × 0,70, pas de 0,60 | 4 | 0,259 | centre | pratique du site, **non IISR** |
| CARRE_TRAVERSEE_CYCLABLE | 0,50 × 0,50, pas de 1,00 | 4 | 0,250 | centre | pratique du site, **non IISR** |

**Contrôles.** Les 13 gabarits sont simples (aucune arête ne se coupe), orientés dans le sens trigonométrique et conformes à leurs dimensions annoncées (tolérance 0,6 mm ; 12 mm pour la figurine vectorisée, qui mesure 1,282 m de haut). Autres contrôles passés :
- cotes de tige, de tête et de branche à 45° ;
- TAG est le miroir exact de TAD ;
- pied du rabattement de 0,25 ;
- erreur de corde des arcs : 0,97 mm à droite, 1,00 mm à gauche ;
- encoche et cassure posées sur leurs arcs ;
- trait perpendiculaire des triangles : 0,100 et 0,150.

Le symbole PMR, le pictogramme de recharge, les chiffres « 30 » / « 50 » et le mot BUS restent **à vectoriser** : les cotes de leur boîte sont données.

**Fabrication.**
- `pj_marquages` génère les lignes depuis les bords de voie OpenDRIVE, puis les découpe selon la modulation.
- Les transversales, zébras, hachures et zigzags sont générés depuis leurs paramètres.
- Les gabarits deviennent des prototypes, posés par `points/marquages_symboles.json`. L'orientation suit la tangente de voie : 3 flèches par voie (2 en ville), la dernière au plus près de la ligne d'arrêt.

## bordures_elements.json

Ce fichier ne duplique aucun profil : il cite ceux de `bordures.json` par leur nom.

- **Élément.**
  - Pas nominal 1,00 m, longueur réelle **0,994 m**, **joint de 6 mm** par défaut, paramétrable de 3 à 8 mm (`joint_mm`).
  - Les fiches Sepa donnent 992 à 994 mm au pas de 1 m. Le 3-5 mm de `bordures.json` n'était pas sourcé.
  - Prototypes de 0,994 / 0,494 / 0,324 / 0,244 / 0,154 m.
- **Pas selon le rayon.** La règle limite la flèche de corde L²/8R à 10,5 mm :

  | Rayon R | Élément |
  |---|---|
  | R ≥ 12 m | 1,00 m |
  | 3 ≤ R < 12 m | 0,50 m |
  | 1,3 ≤ R < 3 m | 0,33 m |
  | 0,75 ≤ R < 1,3 m | 0,25 m |
  | R < 0,75 m | pièces courbes T2 / T3 (R 0,5 à 9 m) ou quarts de rond R 0,25 (TU, I1, I2) |

  Les pièces courbes sont préférées sous 3 m quand le catalogue les propose.
- **Pose.**
  - Chaque file part d'un point dur (chartière, angle, nez, bloc CHARTIERE du GAM) et finit par un élément de coupe d'au moins 0,20 m, à about scié net.
  - Le Z vient du fil d'eau 2021 ou du modèle 2026 (MNT 10 cm), **jamais des maillages v1**.
- **Jitter.** Hauteur ±2 mm (en partie corrélée sur 3 à 5 éléments), lacet ±0,3°, latéral ±1 mm, longueur ±1 mm, roulis ±0,15°. Aucun jitter sur les abaissés.
- **Arêtes.**
  - Les arrondis et chanfreins de la tête viennent des contours de `bordures.json`.
  - S'y ajoutent des chanfreins de 3 mm aux abouts (joints lisibles en « V », comme sur les photos de l'utilisateur) et de 5 mm à l'arrière.
  - CS1 et CS2 ont un chanfrein de **15 × 15 mm** (Sepa, au lieu de 5 mm dans `bordures.json`) : seuls les sommets à remplacer sont donnés.
- **Épaufrures.** Quatre variantes de v0 à v3, avec des répartitions différentes pour les bordures neuves (2025) et anciennes.
- **Abaissés.**
  - Traversée : T2_bateau en **vue 0,02 ± 0,005**, plus 2 chartières de 1,00 m où la vue passe linéairement de la vue courante à 0,02.
  - Entrée charretière : vue de 0,02 à 0,04 (0,03 par défaut).
  - BEV : profondeur de 0,42 (0,5875 en standard NF), recul de 0,50 depuis le nez, sur toute la largeur abaissée.
- **Nouveaux profils**, aux contours vérifiés par le poids linéique du catalogue :
  - TU 25 × 16 (r 3 cm) : 92 kg/ml calculés pour 91 annoncés ;
  - AC1 35 × 18 : 118 pour 119 ;
  - CS3 25 × 16,5 / 14 ;
  - quarts de rond TU_R25, I1_R25 et I2_R25.
- **Matériaux.**
  - `beton_gris` : albédo 0,354. En v1, 0,66 était 1,8 fois trop clair.
  - `beton_clair` : 0,45 (a priori, Vercors).
  - `granit`, `calcaire` (photo 4 de l'utilisateur) et `peint_blanc` (`peinture.json`).
  - Variation de ±4 % d'un élément à l'autre.
- **Aspect.** `salissure`, `mousse_joints`, `herbe_joints` et usure d'arête, avec des valeurs par défaut différentes pour les bordures neuves et anciennes. Ces valeurs passent dans les données d'instance de `points/bordures.json`.

## materiaux_sol.json

Pour chaque `materiau_id`, le fichier donne :
- la texture CC0 locale (`assets/lib/materiaux/<nom>/<nom>.usda`, réservée à Karma) ;
- `tile_m` ;
- l'albédo cible, repris du `cible` du manifeste quand il existe ;
- l'albédo et la rugosité mesurés sur la texture téléchargée ;
- la rugosité visée ;
- l'appareillage (module, joints) ou la couche (épaisseur, granulométrie, retrait de 3 à 5 cm sous la bordure, débordement) ;
- `ue_cc0` (`/Game/PJ/Materials/MI_<id>`) et les candidats `ue_carla` (CC-BY) et `ue_citysample` (réservé à UE).

`beton_balaye`, `beton_desactive`, `dalles_beton`, `paves_beton` et `granit_bordure` sont des **proxys** : ils empruntent la texture d'un autre matériau en attendant une source dédiée, dont les candidats CC0 sont listés.

**Nouveaux matériaux CC0** ajoutés à `assets/manifeste_cc0.json` et téléchargés en 2K par `assets/telecharger_cc0.py` :

| Nom | Source | Tuile | Cible |
|---|---|---|---|
| `brf_bois_concasse` | ambientCG WoodChips003 | 1,60 m | brun moyen, albédo 0,138 / 0,120 / 0,108 (lit vu, photo 2 de l'utilisateur, revue UE du 10/10 ; l'ancienne cible 0,062 / 0,047 / 0,038, tirée des médianes, rendait le lit 3 à 4 fois trop sombre ; texture de `assets/lib` à recaler pour Karma) |
| `brf_bois_gris` | ambientCG WoodChips001 | 1,80 m, estimée | couleur propre de la texture (BRF vieilli) |
| `gravier_concasse_6_10` | Poly Haven gravel_floor_02 | 2,00 m | grains anguleux ; même cible que `gravillons_ilot` (ortho du Vercors) |
| `calcaire_bordure` | ambientCG Travertine009 | 1,20 m | 0,46 / 0,43 / 0,36 ; veinage atténué (gain_L 0,6), rugosité ramenée à 0,70 (travertin poli à l'origine) |

WoodChips002 est écarté : sa texture est en 2:1 (1024 × 512), ce que refuse le contrôle « carré » du script, et ses copeaux frais sont trop clairs.

## Points ouverts

- u = 5 ou 6 cm, et harmonisation des T3 à 0,12 ou 0,15 m.
- Remplissage réel de chaque îlot (décision n° 5).
- Matériau des bordures neuves. Les cibles `beton_clair`, `calcaire` et BRF sont a priori, faute de photo du site après les travaux.
- Phase et largeur des joints à recaler par FFT sur les photos Panoramax.
- Report dans `bordures.json` (lot en cours) des chanfreins CS de 15 mm, des longueurs 992 / 994 mm et des profils TU, AC1 et CS3.
