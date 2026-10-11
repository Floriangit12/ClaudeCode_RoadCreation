# Marquages vectoriels exacts de l'état avant travaux (05/2022 – 06/2025) : sources, précision mesurée, méthode

Carrefour « Paquet Jardin », Meylan. Inventaire `v2_avant_travaux`, 11/10/2026.

**Conventions**
- Repère : local = L93 − (917279,43 ; 6460289,98), z = NGF − 216,30.
- Passage vers UE : X = 100·x, Y = −100·y, Z = 100·z, yaw_UE = −yaw (yaw trigonométrique local).
- Gabarits : `assets/specs/marquages_geometrie.json` (IISR 7e partie, VC 04/04/2025).
- Chemins relatifs à ce dossier, sauf mention contraire.

## 0. En bref

1. **La source de géométrie est l'ortho PCRS 5 cm du 10/05/2022.** Le pilote vectorise chaque marque sans recourir au réseau OpenDRIVE 2026, puis l'ajuste à son gabarit IISR. Résultats sur les zones pilotes (2 zones, 50 bandes de zébra, 7 flèches, 139 m de lignes) :
   - bandes : largeur médiane **0,501 m** (norme 0,50), pas médian **0,997 m** (norme 0,50 + 0,50) ;
   - bords des bandes rectilignes à **0,97 cm** RMS ;
   - centres sur le pas régulier à **0,55 cm** (médiane).

   Précision intrinsèque, mesurée sur images synthétiques à 5 cm :

   | Marque | Erreur |
   |---|---|
   | Flèche neuve, position | 0,9 cm en moyenne, p95 2,0 cm |
   | Flèche neuve, cap | p95 0,30° |
   | Flèche usée, position | p95 2,7 cm |
   | Bande de zébra, largeur et centre | ≤ 1,1 cm (p95) |
   | Trait de 0,15 m, position latérale | p95 0,3 cm |
   | Trait de 0,15 m, largeur | biais de +1,1 cm, à corriger |

2. **Le levé GAM n'est pas un état d'avant travaux.** `vector/gam_topo_sol_signalisation_horizontale_*` et `etat_2026/signalisation_horizontale_*` sont un seul et même levé : 409 polylignes sur 409 identiques à moins de 1 cm. Il en va de même pour les bordures (622/622), les limites de revêtement (429/429), les caniveaux et les arbres. Tous ont été extraits le 06/10/2026.
   - C'est une compilation de relevés de géomètres sans date par objet. Le résumé WFS geoflux le dit : « ces données ne sont pas nécessairement à jour ».
   - Au cœur et sur Verdun SO, il contient du récolement postérieur à 08/2024 : quai de bus à zigzags absent en 2022 comme en 2024 ; passages de la Revirée et du sud décalés de 0,35 et 0,39 m et tournés de 3,6 et 4,3° ; traversée neuve du secteur est.
   - Il ne sert donc que de **contrôle**, là où il coïncide avec 2022. Sur 5 passages : écart médian 7,0 cm, IoU 0,79. Sur le passage NE : **2,3 cm**, IoU 0,90.
3. **De 2022 à juin 2025, les marquages du cœur n'ont pas bougé.**
   - Sur la BD ORTHO du 09/08/2024 recalée, les 11 passages du cœur sont à la même place : décalage optimal de 0 à 5 cm pour 9 d'entre eux, ≤ 0,18 m pour tous.
   - Projetés aux poses calées, les vecteurs 2022 retombent sur la peinture dans les photos Panoramax du 24/08/2024 et du 18/05/2025 : zébras, pavés jaunes délavés, flèches NE, flèche TAD SO.
   - Une observation antérieure le confirme : « zébras et marquages 2022 encore en place au cœur le 31/08/2025 » (VISION-PANORAMAX-2-21).
   - Restent à traiter : les reprises d'enrobé de 2024 au centre (OR-V-002) et le secteur est construit en 2023-2024 (16 % des surfaces circulées).
4. **Pièges mesurés :**
   - la BD ORTHO 2024 (20 cm) donne de faux « absents » : pavés jaunes, et flèche TAD SO (support 0,20) pourtant visible sur photo en 05/2025 ;
   - une branche de flèche usée rend TD et TD_TAD indiscernables (marge d'IoU de 0,011) ;
   - le trident de Vercors est hors IISR ;
   - les pavés jaunes de 2022 mesurent 0,40 × 0,49 m au pas de 0,59 m, alors que le gabarit Chronovélo 2025 est de 0,70 × 0,37 m ;
   - les logos vélo du site ont des roues évidées, différentes de la figurine IISR ;
   - sans traitement, les bords d'ombres d'arbres passent pour de la peinture : il faut calculer le fond séparément à l'ombre et au soleil (c'est fait).
5. **Couverture estimée sur le site** (§5). **84 %** des marques d'avant travaux de l'inventaire de référence ont une preuve de peinture directe sur l'ortho 2022 (576 sur 690). Par famille :

   | Famille | Part visible sur l'ortho 2022 |
   |---|---|
   | Passages | 98 % |
   | Lignes continues | 93 % |
   | Lignes discontinues | 81 % |
   | Damiers | 71 % |
   | Flèches | 67 % |
   | Logos vélo | 36 % |

   Le reste relève de l'inférence (houppiers 11,5 % des surfaces, véhicules 2 %) et des photos. Le secteur construit en 2023-2024 relève de la BD ORTHO 2024 et des photos.

## 1. Ce que « avant travaux » veut dire pour les marquages

| Date | Preuve | Ce qu'elle établit |
|---|---|---|
| 10/05/2022 | ortho PCRS 5 cm (`data/sites/paquet_jardin/ortho5cm_2022`) | géométrie de toutes les marques visibles (référence) |
| 18/03/2023 | Panoramax (obs. pano_0-55) | flèches NE : TD_TAG à gauche, TD_TAD à droite |
| 2023-2024 | surfaces v1 « construit_2023_2024 », orthos 2024 | secteur est aménagé (4 861 m² de surfaces circulées) : marques absentes en 2022 |
| 01/05/2024, 24/08/2024 | Panoramax (obs_pano_*, vignettes du pilote) | traversée cyclable verte NO, zébras, pavés jaunes, flèches NE et SO en place |
| 09/08/2024 | BD ORTHO IGN 20 cm, recalée de +3,5 / +2,9 cm sur le PCRS | mêmes passages à la même place ; reprises d'enrobé sombres au centre (OR-V-002) |
| 18/05/2025 | Panoramax (52 photos) | dernier état photographié avant le chantier du 23/06/2025 ; marques 2022 en place |
| 31/08/2025 | Panoramax (en chantier) | zébras et marquages 2022 encore en place au cœur |

**Conclusion.** Pour les marquages, l'état avant travaux est celui du PCRS 2022, à trois réserves près :
- les marques de guidage qui traversent les reprises d'enrobé de 2024, à vérifier sur les photos de 2024-08 et 2025-05 ;
- le secteur construit en 2023-2024 ;
- les repeintes éventuelles. Aucune n'est détectée sur les 11 passages et 7 flèches contrôlés ; les décalages 2022 → 2024 sont de 0 à 5 cm.

## 2. Sources évaluées

### 2.1 Par source

| Source | Date / résolution | État représenté | Usage | Précision mesurée |
|---|---|---|---|---|
| **Ortho PCRS 5 cm** | 10/05/2022, 5 cm (JPEG) | avant travaux, hors secteur est | **géométrie, toutes familles** | bords ≈ 1 cm RMS ; pose des flèches 1-2 cm ; traits fins +1,1 cm de largeur (flou) |
| `marquages/contraste_5cm` | dérivé du même PCRS | idem | visualisation (aucune information nouvelle) | — |
| Analyse v1 (`analysis/paquet_jardin/figures/etat_actuel_sur_ortho2022`) | PCRS 2022 + superposition 2026 | idem | lecture humaine ; confirme la visibilité | pas de géométrie |
| Paquet v1 (`package/donnees/marquages/marquages_2026.geojson`, 996 marques) | mélange GAM 2026, plan 2025, ortho 2022 (top-hat) | mélange | indice sémantique (types, fantômes, usure) | bandes : écart médian 11,2 cm et p90 41 cm au pilote (43 bandes) |
| Levé GAM `SOL_SIGNALISATION_HORIZONTALE` (= `etat_2026`) | compilation sans date, extraite le 06/10/2026 | 2025-2026 au cœur et à Verdun SO ; plus ancien ailleurs | contrôle là où il coïncide (`datation_gam.geojson`) | coïncident : 7,0 cm (médiane), IoU 0,79 ; meilleur cas 2,3 cm |
| BD ORTHO IGN 2024 (recalage 4 cm) | 09/08/2024, 20 cm | avant travaux | persistance des grandes marques, secteur est, reprises d'enrobé | décalage des zébras de 0 à 5 cm ; faux absents sur marques usées ou colorées |
| Pléiades 2025 | ≈ 50 cm | avant travaux (date non publiée) | présence de grands ensembles seulement | inutilisable pour la géométrie |
| Photos Panoramax / Mapillary 2024-2025 (65 / 400 posées) | 2024-05 → 2025-05 | avant travaux | **type, persistance, repeinte, couleur** ; marques masquées sur l'ortho | projection à ±0,1-0,4 m (erreur de pose) |
| Code V2 (`recon/pcg/decrire/detection_*`, `marquages_ortho.py`) | — | — | idées reprises (NCC de gabarits, périodicité) | inadapté au cœur avant travaux : bandes rectifiées le long des voies OpenDRIVE 2026 ; évaluation V2 : précision des flèches 0,30, lignes 0,63 / 0,62 |

### 2.2 Par famille de marquage

| Famille | Géométrie | Type / existence | Gabarit | Mesuré au pilote |
|---|---|---|---|---|
| Passages piétons | PCRS : bandes au bord sous-pixel, pas régulier | PCRS, photos | bande 0,50 × L, pas mesuré | 50 bandes : largeur 0,497 ± 0,03 ; pas 0,988-1,036 ; L de 2,50 à 3,47 |
| Flèches directionnelles | PCRS : gabarit posé (origine, cap) | PCRS si marge ≥ 0,05, sinon photo ou GAM coïncident | TD, TAD, TAG, TD_TAD, TD_TAG + TRIDENT site | 7 flèches, IoU 0,67-0,87 ; 1 ambiguïté TD / TD_TAD tranchée par photo |
| Lignes longitudinales | PCRS : axe + largeur, polynôme local | PCRS (modulation mesurée) | largeur normée + modulation IISR + phase | tirets de Vercors 3,40 / 1,38 m ; largeur 0,151 (p90 0,159) ; continue courbe : bruit 1,2 cm |
| Pavés jaunes 2022 | PCRS par périodicité (la chroma JPEG fond les pavés) | photos (couleur, présence) | pavé site 0,40 × 0,49, pas 0,59 | 6 files, 50 pavés, pas 0,580-0,597 |
| Carrés blancs 0,50, damier bus 1,00 | PCRS : centres et pas des files | PCRS | CARRE_TRAVERSEE_CYCLABLE, DAMIER_BUS | 1 file, pas 1,011 |
| Logos vélo | PCRS : position et cap | PCRS, photos | gabarit site à vectoriser (roues évidées) | figurine IISR non discriminante : IoU 0,50-0,61 partout |
| « 50 » / « 30 » cerclés | PCRS : centre du cercle, cap | photos (chiffres) | à vectoriser (déjà prévu par la spec) | non traité automatiquement |
| Lignes transversales (effet des feux 0,15 en T'2, STOP 0,50, cédez) | PCRS : traits T'2 alignés | règle + photos | modulation T'2 0,50 / 0,50 | file T'2 à Vercors : 0,78 / 0,53 (usée) |
| Zigzags bus, hachures, chevrons | PCRS : sommets | PCRS, photos | spec zigzag_bus ; hachures à 26,565° | zigzag jaune 2022 de Verdun SO ≠ GAM (quai déplacé en 2025) |

## 3. Pilote mesuré

### 3.1 Code, zones et sorties

Le code est dans `pilote/`. Il utilise numpy, Pillow et pyproj, sans aucun import de `recon/pcg`. Il est déterministe. Lancement : `python -I pilote/pilote.py`.

| Module | Rôle |
|---|---|
| `detection.py` | fond au 30e percentile sur 2,6 m, calculé séparément à l'ombre et au soleil (Otsu sur l'éclairement lissé) ; seuil adaptatif max(22 DN ; 0,15 × fond) ; composantes 8-connexes ; classement géométrique |
| `zebras.py` | regroupement des bandes ; bords au niveau 50 % de la luminance par tranches de 10 cm ; pas régulier par moindres carrés ; lignes de début et de fin |
| `fleches.py` | IoU douce entre gabarit et probabilité de peinture ; Nelder-Mead en deux étapes (composante entière, puis tampon de 0,30 m) ; pose normée et échelle libre ; typage sur la composante |
| `lignes.py` | tirets (droite), lignes courbes (centres par tranches et profils perpendiculaires) ; files ; modulation la plus proche |
| `damiers.py` | files de pavés par autocorrélation et créneau ; carrés |
| `comparer.py` | comparaison au GAM (rectangles, segments de flèches, lignes) ; persistance 2024 |
| `synthetique.py` | précision intrinsèque sur images synthétiques |
| `planches.py`, `verif_photos.py` | planches ortho ; projection dans les photos 360° Panoramax |
| `datation_gam.py`, `carte_site.py`, `couverture_site.py` | datation du GAM ; cartes du site ; couverture |

Zones :
- **A, Vercors approche nord** : 917280-917320 × 6460225-6460261,5 ;
- **B, cœur** : 917253-917307 × 6460261,5-6460312.

Sorties :
- `pilote_resultats.json` ;
- `marquages_pilote_2022.geojson` : L93, `pose_locale` (x, y, yaw), gabarit et indicateurs de qualité par entité ;
- `planches/pilote_A_*.jpg` et `planches/pilote_B_*.jpg`, chacune en trois versions : vue d'ensemble 5 cm, zooms à 1-1,3 cm/px, vecteurs 2022 sur l'ortho 2024.

### 3.2 Zone A : flèches et lignes de Vercors

| Id | Gabarit | IoU normée | Marge au 2e type | Échelle libre (x / y) | Azimut | Origine L93 |
|---|---|---|---|---|---|---|
| A-FL01 | TRIDENT (site) | 0,695 | 0,147 | 0,94 / 1,19 | 342,3° | 917296,95 ; 6460259,05 |
| A-FL02 | TAG | 0,695 | 0,363 | 1,00 / 0,95 | 341,7° | 917294,21 ; 6460258,49 |
| A-FL03 | TRIDENT (site) | 0,681 | 0,125 | 0,97 / 1,15 | 343,9° | 917304,61 ; 6460236,74 |
| A-FL04 | TAG | 0,869 | 0,475 | 0,99 / 0,99 | 343,1° | 917301,63 ; 6460236,98 |

**Flèches.**
- 18 candidats ; les 14 rejetés plafonnent à 0,54 d'IoU (gravier, végétation, bordures). Le seuil de 0,60 sépare les deux populations.
- Les TAG sont conformes à l'IISR à ±5 %.
- Le trident peint a des têtes latérales plus basses que l'union TD_TAD + TD_TAG : il faut un gabarit `TRIDENT_SITE`.
- L'échelle y de 1,15-1,19 est un artefact : un tiret touche la tige. On garde la pose normée.

**Lignes.**
- 7 files, 61,6 m.
- Tirets de séparation des voies : 7 traits de 3,40 m et vides de 1,38 m (T3 aux traits allongés). Largeur 0,151 m (p90 0,159).
- Continue courbe de 25,0 m : largeur 0,16 m, bruit local d'axe 1,2 cm.

**GAM.** Les lignes du GAM sur Vercors sont à 9,7 cm des axes 2022 (médiane sur 12 lignes, p90 22 cm). Vercors a été refait jusqu'au 30/01/2026.

**2024.** Les 4 flèches sont présentes au même endroit (support de 0,47 à 0,79, décalage ≤ 0,11 m).

### 3.3 Zone B : passages piétons et cœur

Sur les 11 passages (50 bandes) :

| Mesure | Médiane | Autres valeurs |
|---|---|---|
| Largeur de bande | 0,5005 m | moyenne 0,497 |
| Pas | 0,997 m | moyenne 1,000 |
| Longueur de bande | 3,03 m | 2,50 à 3,47 m |
| Rectitude des bords | 0,97 cm RMS | p90 1,9 cm |
| Écart au pas régulier | 0,55 cm | p90 1,9 cm |

| Passage (centre L93) | Bandes | Pas | Largeur | L | GAM : écart médian, angle, IoU | Lecture |
|---|---|---|---|---|---|---|
| B-PP03 Verdun NE (917286,9 ; 6460300,3) | 6 | 0,992 | 0,496 | 3,03 | **2,3 cm**, 0,04°, 0,90 | même peinture qu'en 2022 |
| B-PP05 Verdun NE après TPC (917293,0 ; 6460294,6) | 6 | 0,998 | 0,514 | 3,01 | 7,9 cm, 0,2°, 0,76 | idem |
| B-PP06 SE (917290,1 ; 6460278,4) | 4 | 0,993 | 0,485 | 3,30 | 9,4 cm, 0,6°, 0,81 | idem |
| B-PP08 (917287,4 ; 6460275,4) | 2 | 1,036 | 0,495 | 3,47 | 9,3 cm, 1,2°, 0,85 | idem (2 bandes vues) |
| B-PP01 (917281,5 ; 6460305,5) | 3 | 0,996 | 0,505 | 3,03 | 10,6 cm, 2,3°, 0,66 | idem (groupe court) |
| B-PP02 Revirée (917275,0 ; 6460302,8) | 5 | 0,988 | 0,501 | 2,99 | 34,6 cm, 3,6°, 0,22 | le GAM est le passage refait en 2025 |
| B-PP10 Vercors S (917283,0 ; 6460271,3) | 4 | 1,004 | 0,526 | 3,32 | 39,4 cm, 4,3°, 0,17 | le GAM est le passage refait en 2025 |
| B-PP04, B-PP07, B-PP09, B-PP11 (NO, SO ×2, S) | 3-6 | 0,99-1,01 | 0,47-0,52 | 2,5-3,0 | aucun rectangle GAM | supprimés ou déplacés en 2025 ; seule source : 2022 |

**Flèches.**
- B-FL03, TAD SO : IoU 0,857, marge 0,43.
- B-FL01, NE : typée TD avec une IoU de 0,773, mais à seulement 0,011 de TD_TAD, la branche étant usée. Le GAM, à la même place (2,2 cm), et les photos de 03/2023, 08/2024 et 05/2025 disent **TD_TAD** : on retient TD_TAD.
- B-FL02, TD_TAG : IoU 0,667. Le GAM est décalé de 8,3 cm, avec un résidu de forme de 5,5 cm : la flèche NE est un peu plus étroite que l'IISR (écart déjà noté dans `ecarts_site.fleches_gam`).

**Pavés jaunes.**
- 6 files, 50 pavés.
- Pas : 0,589 m (médiane).
- Plein le long de la file : 0,399 m ; largeur de bande : 0,485 m.
- Carrés blancs : 1 file de 3, au pas de 1,011 m.

### 3.4 Précision : cinq mesures indépendantes

1. **Interne.**
   - Bords de bande : 0,97 cm RMS (médiane).
   - Pas : 0,55 cm.
   - Bruit d'axe des lignes : 0,45 à 1,2 cm (médiane du RMS d'axe : 0,45 cm en A, 0,57 cm en B).
2. **Synthétique** (`pilote_synthetique.json`). Gabarits IISR rendus à 5 cm avec flou σ 0,7 px, bruit 4 DN, texture d'enrobé et JPEG q85 ; même chaîne que sur l'ortho.

   | Cas | Peinture neuve | Peinture usée (185 DN) |
   |---|---|---|
   | Flèches trouvées | 32/32 | 27/32 |
   | Type correct | 32/32 | 26/27 |
   | Erreur d'origine | moyenne 0,92 cm, p95 1,95 cm | moyenne 1,19 cm, p95 2,71 cm |
   | Erreur de cap | moyenne 0,15°, p95 0,30° | p95 0,50° |
   | Zébras : largeur (p95) | 0,6 cm | 1,1 cm |
   | Zébras : pas (p95) | 0,9 mm | 1,8 mm |
   | Zébras : centre en travers (p95) | 0,3 cm | 0,7 cm |
   | Zébras : longueur (p95) | 0,9 cm | 2,2 cm |
   | Zébras : angle (p95) | 0,11° | 0,32° |
   | Traits de 0,15 : largeur | +1,1 cm (biais systématique) | +1,2 cm |
   | Traits de 0,15 : latéral (p95) | 0,23 cm | 0,27 cm |
   | Traits de 0,15 : extrémités (p95) | 8,5 cm | 31 cm |

3. **GAM coïncident.** 5 passages, 21 bandes.

   | Écart | Médiane | p90 |
   |---|---|---|
   | Centres | 7,0 cm | 13,9 cm |
   | En travers | 3,9 cm | 9,9 cm |
   | Le long de la bande | 3,5 cm | 13,5 cm |
   | Angle | 0,20° | 2,3° |
   | IoU | 0,79 | 0,91 |

   Lignes GAM au cœur : 2,9 cm (médiane sur 14, p90 15 cm). Ce sont des écarts entre deux mesures du même objet ; l'erreur propre du levé GAM y est incluse.
4. **Paquet v1.** 43 bandes : 11,2 cm (médiane), p90 41 cm, IoU 0,73. La v1 mêle le GAM 2026 et l'ortho : ce n'est pas une référence d'avant travaux.
5. **Persistance 2022 → 2024-2025.**
   - 11 passages : décalage optimal ≤ 0,18 m (9 entre 0 et 5 cm).
   - 6 flèches sur 7 : support 2024 de 0,47 à 0,84 sans décalage.
   - B-FL03 : support 0,20 en 2024, mais **présente** sur la photo du 18/05/2025 (31d16b8e, à 3,8 m).
   - Pavés jaunes : en 2024, jaunissement de 2 à 10 DN, contre 38-40 en 2022 (et 13 à 21 sur d'autres peintures jaunes en 2024). Ils sont pourtant **présents et délavés** sur les photos du 24/08/2024 (2ab4efbc) et du 18/05/2025 (119d9094).

   Les vignettes sont dans `photos_non_versionnees/verif_*.jpg` (non versionnées), indexées dans `verif_photos.json`.

### 3.5 Limites constatées

- **Extrémités des tirets usés** : jusqu'à 31 cm d'erreur (p95). On les régularise par la modulation et la phase de la file, jamais tiret par tiret.
- **Branche de flèche usée** : seuil de marge de type de 0,05, au-dessous duquel on arbitre par photo ou par GAM coïncident.
- **Glyphes hors IISR** (trident, flèches NE étroites, logos vélo, « 50 / 30 », pavés 2022) : à vectoriser une fois sur l'ortho, en moyennant les occurrences recalées, comme gabarits « site ».
- **Petites flèches et guidages du centre**, en partie sur les reprises de 2024 : non détectés. Il faut un examen manuel sur ortho et photos.
- **Longues continues accolées aux bordures** : souvent fusionnées avec la bordure claire. Seulement 14 % sont reprises automatiquement (§5). Il faut un suivi de ligne guidé par la bordure.
- **Ombres d'arbres** : le fond calculé séparément supprime les faux positifs des bords d'ombre (contrôlé sur Verdun NE), mais le contraste y reste plus faible. Il faut une revue des lignes sous l'alignement d'arbres de Verdun NE.

## 4. Méthode recommandée

### 4.1 Ordre de priorité des sources, par attribut

| Attribut | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Géométrie (position, cap, dimensions) | **PCRS 5 cm 2022** ajusté aux gabarits | GAM seulement si `present_identique` en 2022 et écart < 0,10 m | BD ORTHO 2024 recalée (secteur est, grandes marques) | règle d'inférence (§4.3) |
| Type (flèche, modulation, couleur) | PCRS si marge ≥ 0,05 | photos 2024-08 / 2025-05 projetées aux poses calées | GAM coïncident | IISR + affectation des voies 2022 |
| Existence au 06/2025 | photos 2024-2025 (présence) | BD ORTHO 2024 (présence seulement ; une absence n'y est pas une preuve) | PCRS 2022 + persistance (vérifiée sur 11 passages et 7 flèches) | — |
| Usure, aspect | photos 2025-05 | PCRS (contraste) | — | — |

### 4.2 Ajustement aux gabarits (static meshes paramétriques)

- **Passages** : un mesh `BANDE_PASSAGE_PIETON` de 0,50 × L par bande.
  - Centres sur la grille c0 + k·pas, avec le pas mesuré.
  - Orientation commune, corrigée de la pente des bords.
  - Extrémités sur les lignes de début et de fin ajustées (passages biais acceptés).
  - Largeur IISR 0,50 conservée (écart mesuré : 0,3 cm).
- **Flèches** : origine IISR (milieu du pied de tige) et cap de la pose **normée**.
  - Gabarit IISR si l'IoU est ≥ 0,60 et la marge ≥ 0,05. Sinon, arbitrage par photo ou GAM et statut `a_verifier`.
  - Gabarit site si son IoU dépasse celle de l'IISR de plus de 0,05 (décision utilisateur n° 10).
- **Lignes** :
  - axe mesuré, simplifié par Douglas-Peucker à 1 cm ;
  - largeur = mesure − 1,1 cm, ramenée à la largeur normée la plus proche (0,10 / 0,12 / 0,15 / 0,18 / 0,25 / 0,30) ;
  - modulation IISR, ou modulation mesurée si l'écart dépasse 10 % (Vercors : traits de 3,40 m) ;
  - phase ajustée par moindres carrés sur toute la file.
- **Pavés, damiers, carrés** : centres de file, pas et phase mesurés ; gabarit au format mesuré.
- **Symboles** : position et cap mesurés ; gabarit site.
- **Par entité**, la sortie contient :
  - `pose_locale` (x, y, yaw), `gabarit`, dimensions ;
  - `src`, `date_preuve` ;
  - les indicateurs de qualité : IoU, marge, RMS des bords, support 2024, identifiant de la photo de contrôle.

### 4.3 Inférence quand la marque est masquée (véhicule, houppier, ombre dense)

| Cas | Règle |
|---|---|
| Zébra | Compléter la grille régulière entre les bandes vues, puis jusqu'aux bordures (± 0,5 m). Les bandes manquantes prennent la longueur des lignes de début et de fin. Conditions : au moins 2 bandes vues, résidu de pas < 3 cm. |
| Tirets / continues | Prolonger l'axe (polynôme local) et la phase à travers le masque si la ligne est vue des deux côtés, colinéaire à moins de 3 cm. Sinon, arrêter la ligne et poser `a_verifier`. |
| Flèches | Reprendre le type vu sur la même voie et la même rangée (IISR 115-3 C : 2 à 3 par voie, interdistance constante). Une rangée masquée se place à l'interdistance des voies voisines. Si le type reste inconnu : photo, puis affectation de voie 2022. Jamais l'OpenDRIVE 2026 au cœur. |
| Pavés / carrés | Prolonger pas et phase jusqu'aux bords de la traversée. |
| Lignes d'effet des feux / STOP | Perpendiculaires à la voie, à au moins 0,50 m en amont du passage (IISR 118), sur les seules voies commandées. Seulement si un tronçon est vu ou si une photo le montre : les 6 lignes d'effet des feux de la v1 sont absentes en 2022 (ajouts 2025). |
| Ombre | Pas d'inférence : la détection avec fond par classe d'éclairement suffit. Une revue est nécessaire sous les alignements d'arbres. |
| Secteur construit 2023-2024 | BD ORTHO 2024 + photos 2024-2025 (±0,1-0,2 m), avec `src: ortho2024/photo`. Jamais de copie du GAM sans test de coïncidence avec 2024. |
| Reprises d'enrobé de 2024 | Vérifier chaque marque par photo ; une marque absente de la photo de 2025-05 est retirée. |

### 4.4 Contrôle qualité

- **Seuils d'acceptation** :
  - IoU ≥ 0,60 et marge de type ≥ 0,05 ;
  - RMS des bords ≤ 3 cm et résidu de pas ≤ 3 cm ;
  - bruit d'axe ≤ 3 cm ;
  - dissymétrie de fond ≤ 20 DN, pour écarter les bordures.
- **Planches** à 1-1,3 cm/px pour chaque flèche et chaque passage (`*_zooms.jpg`), à revoir par branche.
- **GAM coïncident** : on attend moins de 10 cm d'écart. Au-delà, l'entité GAM est postérieure ; on garde 2022.
- **Vignettes photo de 2025-05** : présence et type de chaque flèche et de chaque élément coloré.

## 5. Taux de couverture estimé sur tout le site

Sources du calcul : `couverture_site.json`, `marquages_site_2022_auto.geojson` et `planches/couverture_site.jpg`. L'emprise fait 300 × 300 m. Les surfaces circulées sont celles du paquet v1 (chaussée, parking, piste cyclable, accès riverain, quai bus), soit **30 508 m²** au total :

| Zone | Surface | Part | Commentaire |
|---|---|---|---|
| Inchangée depuis 2022 | 21 225 m² | 70 % | — |
| Zone des travaux 2025 | 4 458 m² | 15 % | celle dont on veut l'état d'avant travaux |
| Construite en 2023-2024 | 4 861 m² | 16 % | absente de l'ortho 2022 |

**Lisibilité de l'ortho 2022** sur ces surfaces (grille de 25 cm) :

| Zone | Dégagé | Ombre ou objet sombre | Véhicule ou objet clair | Houppier |
|---|---|---|---|---|
| Tout | 69,9 % | 16,3 % | 2,3 % | 11,5 % |
| Zone des travaux 2025 | **86,7 %** | 5,4 % | 1,6 % | 6,3 % |
| Inchangé 2022 | 65,9 % | 19,8 % | 1,9 % | 12,4 % |

Les ombres restent lisibles, avec un contraste réduit. Houppiers et véhicules masquent la peinture.

**Inventaire de référence** : 690 marques v1 d'avant travaux dans l'emprise (états `conserve`, `fantome`, `refait_2025_identique`). On compte une marque comme visible si son support de peinture 2022 est ≥ 0,4.

| Type v1 | n | Visible sur l'ortho 2022 | Reprise par l'extraction auto (non revue) | Reprise parmi les visibles |
|---|---|---|---|---|
| Bandes de passage | 58 | **98 %** | 60 % | 61 % |
| Lignes continues | 160 | **93 %** | 14 % | 15 % |
| Fantômes 2022 (supprimés en 2025) | 118 | **92 %** | 55 % | 59 % |
| Lignes discontinues | 256 | **81 %** | 40 % | 50 % |
| Damiers / pavés | 42 | 71 % | 50 % | 70 % |
| Flèches | 12 | 67 % | 50 % | 75 % |
| Hachures, texte | 10 | 100 % | — | — |
| Logos vélo | 14 | 36 % | — | — |
| Autres symboles | 13 | 23 % | — | — |
| Lignes d'effet des feux | 6 | 0 % (ajouts 2025) | — | — |
| **Total** | **690** | **84 % (576)** | — | — |

**Extraction automatique** sur tout le site (≈ 15 min, non revue) :
- 18 passages et 77 bandes ;
- 14 flèches retenues sur 498 candidats ;
- 492 segments de ligne, soit 1 211 m ;
- 8 files de pavés (64 pavés).

**Estimation de couverture de la méthode recommandée**, revue comprise :

| Part des marques | Moyen | Précision |
|---|---|---|
| **≈ 84 %** | géométrie directe sur l'ortho 2022, ajustée aux gabarits | 1-3 cm (pose), < 1 cm (largeur et pas des zébras) |
| **≈ 8-10 %** | inférence par règles : masques sous houppier (11,5 % des surfaces) et véhicules (2 %), lignes et zébras complétés | 5-10 cm |
| **≈ 6-8 %** | photos 2024-2025 ou à vérifier : symboles (logos vélo 64 % non visibles, chiffres), petites flèches de guidage, marques sur les reprises de 2024 | 0,1-0,4 m |

À cela s'ajoute le secteur construit en 2023-2024 (16 % des surfaces circulées), traité à part : BD ORTHO 2024 et photos, géométrie à ±0,1-0,2 m.

Sans revue, la chaîne automatique actuelle reprend directement 40 à 60 % des marques (75 % des flèches visibles). Le reste demande les compléments listés au §3.5 et une revue sur planches : environ 5 à 10 minutes par branche, 1 à 2 heures pour le site.

## 6. Fichiers produits

| Fichier | Contenu |
|---|---|
| `MARQUAGES.md` | ce rapport |
| `pilote/*.py` | code du pilote ; aucun fichier existant du dépôt n'a été modifié |
| `pilote_resultats.json` | mesures détaillées des zones A et B ; comparaisons GAM, 2024 et v1 |
| `marquages_pilote_2022.geojson` | 158 entités ajustées du pilote : 50 bandes, 7 flèches (9 polygones), 49 axes de ligne, 50 pavés (L93, pose locale, gabarit, qualité) |
| `pilote_synthetique.json` | précision intrinsèque sur images synthétiques |
| `datation_gam.json`, `datation_gam.geojson` | statut 2022 / 2024 de chaque polyligne GAM, par secteur |
| `couverture_site.json`, `marquages_site_2022_auto.geojson` | lisibilité du site ; extraction automatique **non revue** |
| `verif_photos.json` | index des vignettes photo (identifiants, dates, cibles ; aucune image) |
| `planches/pilote_{A,B}_*.jpg` | ortho 2022 + vecteurs ; zooms ; vue 2024 |
| `planches/datation_gam_2022.jpg`, `planches/couverture_site.jpg` | carte de datation du GAM ; carte de couverture |
| `photos_non_versionnees/` | 9 vignettes Panoramax (CC-BY-SA, Eric S) avec contours projetés : **à ne pas versionner** |

Le cache des cartes du site est hors dépôt. Pour le régénérer : `PJ_CACHE_MARQUAGES=<dossier> python -I pilote/carte_site.py --millesime 2022` (puis `2024`).

### Datation du GAM par secteur (`datation_gam.json`)

Le calcul compare 401 polylignes GAM (2 544 m) à l'ortho 2022, avec un décalage cherché à ±1,2 m. Les parts sont exprimées en longueur.

| Secteur | Identique à 2022 | Décalé | Incertain | Absent en 2022 |
|---|---|---|---|---|
| Cœur | 45 % | 37 % | 17 % | 1,5 % |
| Verdun NE | 36 % | 19 % | 22 % | 23 % |
| Verdun SO | 28 % | 14 % | 37 % | 21 % |
| Vercors S | 76 % | 13 % | 9 % | 2 % |
| Revirée N | 99 % | 1 % | 0 % | 0 % |
| **Tout** | **44 %** | **20 %** | **22 %** | **14 %** |

Absents à la fois en 2022 et en 2024 :
- le quai de bus de Verdun SO (45 m de zigzags en 917240,7 ; 6460255,9) ;
- 72 m de zigzags en 917227,7 ; 6460238,1 ;
- la traversée du secteur est (917330-917334 ; 6460257).

Ces trois éléments datent le levé, au moins par endroits, d'après 08/2024.

## 7. Points ouverts

1. **Date cible.** Recommandé : 05/2025, juste avant le chantier, en prenant la géométrie 2022 contrôlée par les photos de 2024-08 et 2025-05. Les différences ne portent que sur le secteur est et les reprises de 2024.
2. **Gabarits « site » à vectoriser** une fois : TRIDENT_SITE, flèches NE étroites, logo vélo à roues évidées, « 50 » et « 30 », pavé jaune 2022 (0,40 × 0,49).
3. **Largeurs.** Mesuré : 0,15 m sur Vercors et 0,13 m au cœur, avant correction de +1,1 cm, soit ≈ 0,14 et ≈ 0,12. À trancher : u = 5 cm ou 6 cm selon l'axe (décision n° 10).
4. **Revue des petites flèches et des guidages du centre** sur les photos de 2024-08 et 2025-05 : non traités par le pilote.
5. **Longues continues accolées aux bordures** : la reprise automatique n'est que de 14 %. Il faut un suivi de ligne guidé par les bordures pour la mise à l'échelle du site.
