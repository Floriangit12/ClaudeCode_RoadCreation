# Géométrie du sol de l'état avant travaux : sources, précision mesurée, méthode

Carrefour « Paquet Jardin », Meylan. État visé : avant le chantier du carrefour (23/06/2025 → 05/12/2025, trottoirs de l'avenue du Vercors jusqu'au 30/01/2026).

Repère local : local = L93 − (917279,43 ; 6460289,98), z = NGF − 216,30.

Les chiffres viennent des scripts du pilote (`pilote/`, lancés avec `python -I`) et des JSON écrits à côté de ce fichier. Les planches sont dans `planches/` et ont toutes été regardées. Les vignettes Panoramax sont dans `photos_non_versionnees/`, qui n'est pas versionné.

Aucun fichier existant du dépôt n'a été modifié et rien n'a été téléchargé.

## 0. En bref

1. **Le levé GAM « ancien » et `etat_2026` sont le même fichier.** Les calques `vector/gam_topo_sol_*` (WGS84) et `etat_2026/*_L93` ont été comparés :
   - mêmes entités : 622 bordures, 22 blocs, 12 caniveaux, 429 limites de revêtement, 409 + 28 marquages, 285 arbres ;
   - mêmes sommets : 4 614 pour les bordures, écart maximal 0,0 cm ;
   - attributs identiques.

   Il n'existe donc pas de levé GAM d'avant travaux sur le PC (`comparaison_gam_etat2026.json`). `Meylan_Topo.dwg` est un plan vivant, mis à jour par morceaux. Au cœur du carrefour, il contient déjà des récolements de 2025, par exemple la « goutte » de la zone A et la bordure posée sur l'ancien tourne-à-droite de la zone B.
2. **Le levé GAM se date tronçon par tronçon** (`pilote/dater_gam.py`). Chaque échantillon de 0,5 m est confronté à trois sources : la crête de pente du LiDAR 2021, la marche du MNT 2021 et l'arête sur l'ortho de mai 2022 et sur celle d'août 2024. Sur 7 005 m de traits GAM :
   - 44,6 % ont un relief en 2021 ;
   - 13,2 % sont des bordures à niveau visibles en 2022 ;
   - 6,0 % sont apparus entre 2022 et 2024 (constructions à l'est : 14,3 % de ce secteur) ;
   - 4,7 % sont absents avant 08/2024 (7,2 % au cœur).

   Le témoin daté de 2019 (PCRS vecteur) ne compte que 2,2 % de « postérieur », ce qui borne le taux de fausse alarme.
3. **Au cœur, des bordures d'avant travaux ne sont dans aucune source vectorielle**, ni GAM ni PCRS 2019 :
   - l'îlot triangulaire de la traversée de Vercors (IA-1) et l'îlot allongé en galets (IA-2), tous deux disparus en 2025 ;
   - la plus grande partie du séparateur de Verdun NE (seuls 38 % de son contour sont levés).

   Au cœur, 13 composantes de crête LiDAR 2021 n'ont aucune ligne vectorielle, soit environ 433 m en équivalent bordure, faux positifs compris (`cretes_sans_ligne.json`).
4. **Méthode pilotée : « le LiDAR 2021 détecte, l'ortho 2022 de 5 cm précise ».**
   - Anneaux fermés, sans auto-intersection, virage maximal de 19° par pas de 10 cm, rayon minimal de 0,30 m.
   - Bruit de détection : p50 0,7 à 0,9 cm, p90 2,0 à 2,6 cm.
   - Justesse mesurée sur un îlot que le levé GAM porte encore : p50 4,7 cm, p90 12,3 cm.
5. **Hauteurs de vue : la source au cm est le nuage de points LiDAR 2021, absent du PC.**
   - Seuls les tronçons de 1 m de `bordures_hauteurs.geojson` (paquet v1) en dérivent, et seulement le long des lignes GAM et PCRS.
   - La heightmap v1 en 16 bits suit ces points à 0,9 cm près (p50 ; p90 2,6 cm), mais elle **arase les anciens îlots** dans la zone des travaux.
   - Le MNT 2021 en JPEG couleur, une fois décodé, ne donne la vue qu'à 2,5 cm près (p50 ; p90 6,3 cm).
   - Pour les îlots disparus, il faut donc le LAZ 2021, à télécharger avec l'accord de l'utilisateur.
6. **Les matériaux se séparent sur l'ortho 2022.** Le grain sépare galets et enrobé (6,9 contre 2,2), l'indice de vert ExG sépare le gazon (64), et l'intensité LiDAR sépare la végétation (205 à 223) de l'enrobé (93 à 130). La photo Panoramax du 18/05/2025 confirme des **galets** dans les îlots du cœur, alors que la v2 2026 y met du `gravier_concasse_6_10`.
7. **Les défauts de 2026 viennent surtout de la fabrication et du mélange de sources non datées.** La description 2D v2 est déjà une partition propre :
   - 0 m² de recouvrement ;
   - 7,1 m² de fissures fines ;
   - 704 m² de zones non décrites, en 14 composantes.

   Le pilote A montre qu'une partition bâtie sur des anneaux partagés tombe juste au pixel de 2 cm : 672,0 m² = 672,0 m², sans recouvrement ni trou.

## 1. État visé et chronologie des sources

| Période | Sources disponibles | Usage pour l'état « avant travaux » |
|---|---|---|
| 12/08 et 06/09/2021 | LiDAR HD IGN (23,9 pts/m², dont 1,11 M de points sol sur 9 ha, soit environ 12 pts sol/m²). Sur le PC : rasters JPEG 15/25 cm (`data/sites/paquet_jardin/lidar`) et dérivés du paquet v1 (`bordures_hauteurs.geojson`, heightmap 16 bits) | Existence et vue des bordures, nivellement. Le chantier des Saules Blancs (secteur est) est en cours |
| 2019 (`date_leve` 2019-01-01, geofit) | PCRS vecteur GAM : bordures (précision annoncée 10 cm en plan, 20 cm en Z) | Bordures de 2019. Témoin de datation |
| 10/05/2022 | Ortho PCRS 5 cm | Géométrie fine (arêtes) et matériaux |
| 09/08/2024 | BD ORTHO IGN 20 cm, recalée de 3 à 4 cm sur le PCRS 2022 | Secteur est construit, présence des îlots du cœur |
| 2025, probablement avant le 23/06 | Pléiades 50 cm | Contrôle grossier |
| 2024-05 → 2025-05 | Panoramax : 13 poses calées acceptées avant travaux (5 du 2024-08, 8 du 2025-05). Mapillary : 128 poses en 2024, 21 au premier semestre 2025 | Matériaux, type de bordure, contrôle |
| 2025-06 → 2026-01 | Travaux. Le levé GAM (`Meylan_Topo.dwg`) est mis à jour par morceaux | À écarter tronçon par tronçon (§ 2) |

**Date de référence recommandée : printemps 2025, avant le 23/06/2025.** Le cœur est alors dans son état 2021-2022, à quelques réfections d'enrobé près, et le secteur est est construit, comme sur l'ortho de 2024. Cette date coïncide avec les 13 poses Panoramax et les 149 poses Mapillary de 2024 et 2025.

Si l'utilisateur préfère « mai 2022 », le secteur est redevient un chantier et 6 % des traits GAM (`apparue_2022_2024`) sont à retirer.

## 2. Datation du levé GAM (`datation/`)

Pour chaque échantillon de 0,5 m d'une ligne, quatre preuves indépendantes sont relevées :

- **R21** : crête de pente du LiDAR 2021 à ± 0,30 m ;
- **H21** : marche d'au moins 5 cm sur le MNT 2021 ;
- **E22** : arête de luminance sur l'ortho 2022 à ± 0,15 m ;
- **E24** : même test sur l'ortho 2024.

Les classes sont lissées sur 2,5 m. On en tire six classes :

- `relief_2021` ;
- `arasee_visible` (bordure à niveau ou bateau visible en 2022) ;
- `apparue_2022_2024` ;
- `absente_avant` (postérieure au 09/08/2024) ;
- `relief_seul` (relief sans arête sur l'ortho : douteux) ;
- `terrain_remanie_2021` (crête dans un terrain accidenté : non probante).

Les tronçons sans arête ni relief sous une ortho masquée (canopée, ombre) restent `masquee`, c'est-à-dire indéterminés.

| Longueur échantillonnée | Total | relief 2021 | arasée visible | relief seul | terrain remanié | masquée | apparue 2022-24 | absente avant 08/2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GAM bordures, site | 7 005 m | 44,6 % | 13,2 % | 6,4 % | 18,5 % | 6,5 % | 6,0 % | 4,7 % |
| — cœur (rayon de 40 m) | 810 m | 50,5 % | 17,1 % | 10,8 % | 9,3 % | 1,0 % | 4,0 % | **7,2 %** |
| — secteur est (constructions) | 2 287 m | 24,3 % | 11,0 % | 8,3 % | 24,8 % | 10,2 % | **14,3 %** | 7,1 % |
| PCRS 2019 bordures (témoin) | 4 192 m | 69,4 % | 13,2 % | 4,9 % | 6,6 % | 3,5 % | 1,3 % | 0,9 % |
| GAM caniveaux | 139 m | 16,5 % | 19,1 % | 11,5 % | — | — | 38,1 % | 14,7 % |
| GAM limites de revêtement | 4 601 m | 39,7 % | 13,0 % | 5,1 % | 22,2 % | 7,4 % | 6,6 % | 6,0 % (15,9 % au cœur) |

Planches : `planches/datation_site_ortho2022|2024.jpg`, `datation_coeur_*.jpg`, `datation_A_*.jpg`, `datation_B_*.jpg`.

On y voit en rouge les deux récolements de 2025 :

- la « goutte » qui entoure l'ancien triangle de la zone A ;
- la courbe posée sur l'ancien tourne-à-droite de la zone B.

On y voit aussi les lignes de 2025 au sud du cœur (nouveau quai, refuge).

Le secteur est est en orange : parking et voiries du quartier livré en 2024.

**Conséquence : aucune ligne GAM n'entre dans la description « avant » sans sa classe de datation.** La règle est la suivante :

| Classe | Traitement |
|---|---|
| `relief_2021`, `arasee_visible`, `masquee` | Gardées |
| `apparue_2022_2024` | Gardée si la date cible est 2024 ou après |
| `absente_avant` | Retirée |
| `relief_seul`, `terrain_remanie_2021` | Contrôle visuel sur la planche |

Ce contrôle visuel est nécessaire : 449 m sont en `relief_seul`. Ce sont surtout des bordures de rive à l'ombre, réelles, et, au cœur, des tronçons de 2025 qui longent une ancienne crête.

## 3. Sources par élément du sol

| Élément | Source primaire avant travaux | Contrôle | À éviter | Précision mesurée |
|---|---|---|---|---|
| Bordure : arête avant, en plan | Ligne GAM datée (§ 2), sinon PCRS 2019, en ne gardant que l'arête la plus proche de la chaussée quand le levé GAM trace deux arêtes | Ortho 2022, crête LiDAR | Lignes GAM `absente_avant`, plan 2025 | PCRS / GAM sur la même bordure : p50 3,5 cm, p90 23 cm (61 % < 5 cm, n = 3 016) |
| Bordure absente des vecteurs (îlots disparus) | Crête LiDAR 2021 (détection), puis arête sur l'ortho 2022 (filtre adapté « tête claire / extérieur sombre ») | Ortho 2024, photos 2024-2025 | Contour au milieu de la crête LiDAR seule (biais de 27 cm vers l'extérieur) | Ortho / GAM : p50 4,7 cm, p90 12,3 cm (IV-2). Bruit : p50 0,7-0,9 cm |
| Hauteur de vue | Points sol LiDAR 2021 : `bordures_hauteurs.geojson` le long des lignes GAM et PCRS ; le LAZ 2021 (à télécharger) pour toute autre ligne | Heightmap v1 hors zones modifiées | Heightmap v1 dans les zones de travaux (îlots arasés, hauteurs standard), MNT JPEG pour une valeur au cm, Z du PCRS | Heightmap / points : p50 0,9 cm, p90 2,6 cm. JPEG / points : p50 2,5 cm, p90 6,3 cm. Z PCRS / LiDAR : p50 2,8 cm, p90 7,1 cm, sans savoir quelle arête a été levée (63 % plus près du dessus) |
| Abaissés, bateaux | Trou dans la crête LiDAR et vue < 4 cm sur ≥ 0,8 m. Blocs `CHARTIERE_*` du levé GAM s'ils sont datés | Fin du zébra sur l'ortho 2022 | Abaissés standard de 2025 (heightmap v1 : traversée = 0,02 m imposé) | Zone B : abaissé LiDAR en s 17,38-20,38 contre chartières en s 17,28-20,26, soit ≤ 0,12 m |
| Caniveaux | GAM `SOL_CANIVEAU` datés (139 m dans le site, 38 % apparus de 2022 à 2024 à l'est, 56 % des 28,5 m « autres » absents avant 08/2024 : réfection des trottoirs du Vercors) | Ortho 2022 (bande claire de 0,20 à 0,25 m) | Caniveau CS2 « par défaut » | Pas de vue propre : le fil d'eau suit la vue de la bordure |
| Trottoirs, limites de revêtement | Limites GAM datées (15,9 % absentes avant au cœur), ortho 2022 | Photos | Les 209 limites d'origine raster de la v1 | Comme les arêtes de l'ortho : quelques cm |
| Îlots (contour et remplissage) | Anneau G1 (pilote A). Matériau d'après la signature ortho et la photo | Intensité LiDAR | Remplissage « a priori » de la v1 | Voir § 5 |
| Pistes cyclables | Marquages (lot marquages), limites GAM datées, ortho 2022 (enrobé teinté, bandes vertes et jaunes) | Photos 2024-2025 | OSM 2026, BD TOPO Chronovélo (dates 2025-2026) | — |
| Nivellement (z) | Sol nu LiDAR 2021, classe 2, débruité : le `dtm_sol_10cm.tif` du paquet v1, à régénérer car absent du PC, ou la heightmap v1 **hors** `relief_zones_2026.geojson` | `bordures_hauteurs` (z dessus / fil d'eau) | Heightmap v1 dans les 69 zones modifiées (chaussée 2026 lissée, anciens îlots arasés) | Heightmap / points : z p50 0,6 cm, p90 1,6-1,8 cm (n = 1 722) |

## 4. Précision mesurée (récapitulatif, en cm)

| Grandeur | Méthode | Référence | p50 | p90 | n |
|---|---|---|---:|---:|---:|
| Position d'une bordure | PCRS 2019 / GAM, même bordure | GAM | 3,5 | 23 | 3 016 échantillons |
| Contour d'îlot | Ortho 2022, filtre adapté | Levé GAM (îlot inchangé IV-2) | 4,7 | 12,3 | 79 |
| Bruit de détection du contour | Résidu à la courbe lissée | — | 0,7-0,9 | 2,0-2,6 | 370 |
| Contour | Ortho 2024 (20 cm) / ortho 2022 | Ortho 2022 | 11-29 | 23-54 | 2 îlots |
| Contour | Milieu de crête de pente LiDAR / ortho 2022 | Ortho 2022 | 27-28 (biais) | 51 | 2 îlots |
| Vue | Heightmap v1 / points LiDAR | Points | 0,9 | 2,6 | 1 722 tronçons de 1 m |
| z (fil d'eau, dessus) | Heightmap v1 / points | Points | 0,6 | 1,6-1,8 | 1 722 |
| Vue | MNT JPEG décodé / points | Points | 2,5 (biais −1,1) | 6,3 | 1 965 |
| z | MNT JPEG décodé / points | Points | 1,7 | 4,5 | 1 965 |
| z | MNT JPEG décodé / heightmap, validation croisée en damier de 10 m | Heightmap | 2,4 | 13,6 | 1,4 M pixels |
| Z du PCRS 2019 | Z vecteur / LiDAR (arête la plus proche) | LiDAR | 2,8 | 7,1 | 322 sommets |
| Position d'un abaissé | Trou dans la marche JPEG / chartières GAM | GAM | ≤ 12 | — | 2 extrémités |
| Datation | « Postérieur » trouvé sur des traits datés de 2019 | PCRS 2019 | 2,2 % de fausse alarme | — | 4 192 m |

Les fichiers de ces mesures sont `precision_hauteurs.json`, `precision_vecteurs.json`, `dtm_jpg_decodage.json`, `pilote_A|V/mesures_*.json` et `pilote_B/mesures_B.json`.

La référence « points » (`bordures_hauteurs`) vient du même vol LiDAR que la heightmap. L'écart mesure donc la méthode (TIN débruité ou médiane de points), pas l'exactitude absolue du LiDAR HD : l'IGN annonce environ 10 cm en Z absolu. Pour une vue, différence locale, ce biais absolu s'annule.

## 5. Pilote A : îlots du cœur disparus en 2025 (`pilote/ilot_coeur.py`, `partition_A.py`)

Zone locale : (−4 ; −34) → (20 ; −6). Planches : `A_ortho2022.jpg`, `A_ortho2024.jpg`, `A_pente2021.jpg`, `A_plan2025.jpg`, `A_hauteurs.jpg`, `A_partition.jpg`, `zone_A_ombrage.jpg`.

| | IA-1, refuge triangulaire (feu, panneau B21) | IA-2, îlot allongé |
|---|---|---|
| Sources vectorielles | Aucune : le levé GAM porte la goutte de 2025, qui reprend 40 % du contour à 7,7 cm près | Aucune (3,8 % du contour à moins de 0,5 m d'une ligne GAM) |
| Anneau (arête avant) | Fermé, aire 7,02 m², périmètre 10,49 m | Fermé, aire 22,26 m², périmètre 26,47 m |
| Contrôle G1 | 0 auto-intersection, virage maximal de 19,2° par 10 cm, rayon minimal de 0,30 m, 33 sommets après Douglas-Peucker à 1 cm | 0 auto-intersection, 19,3°, 0,30 m, 60 sommets |
| Affinage sur l'ortho 2022 | 96 % des profils retenus, résidu p50 0,9 cm, p90 2,6 cm | 98 %, p50 0,7 cm, p90 2,0 cm |
| Largeur de la bande claire (tête) | p50 0,25 m (p25-p75 : 0,23-0,27) | p50 0,27 m (0,24-0,29) |
| Vue, MNT 2021 JPEG | p50 17,2 cm (p10-p90 : 12,5-19,8). Un tronçon de points vaut 14,5 cm | p50 13,5 cm (9,4-18,8) |
| Vue dans la heightmap v1 (« 2026 ») | 3,8 cm : arasé | 1,0 cm : arasé |
| Remplissage | Galets : grain 6,9, ExG 4, intensité 130. Confirmés sur la photo Panoramax 119d9094 du 2025-05-18 | Galets (photo 31d16b8e du 2025-05-18) |

Partition d'avant travaux de la zone (`pilote_A/partition_A.geojson`). Elle se compose d'une chaussée (rectangle moins les deux anneaux), de deux emprises de bordure (arête avant moins arête arrière, largeur mesurée) et de deux remplissages. Le contrôle est fait par remplissage exact aux centres de pixels de 2 cm :

- **recouvrement : 0,0000 m²** ;
- **trou : 0,0000 m²** ;
- somme des faces = 672,0 m² = aire de la zone.

Ce qu'il reste à trancher :

- La bande claire de 0,25 à 0,27 m correspond à la largeur d'une I2 (25 cm, dessus galbé, vue de 11 cm). Mais la vue mesurée, de 13,5 à 17 cm avec un biais JPEG d'environ −2 cm, penche vers une T2 ou une T3.
- Le LAZ 2021 et un gros plan Panoramax ou Mapillary de 2024-2025 permettront de choisir le profil.
- Validation : la même chaîne, appliquée à la zone V (îlot rond et séparateur de Verdun NE encore levés par GAM, `pilote_V/`), donne IV-2 contre GAM à p50 4,7 cm et p90 12,3 cm.
- Vues sur IV-2 : JPEG 11,5 cm, heightmap 15,6 cm, points 14,3 cm.
- Sur le séparateur IV-1, à dessus en enrobé (même matériau que la chaussée), l'ortho n'a pas de contraste du côté éclairé. Le contour y erre et il faut la crête LiDAR corrigée de son biais, ou le LAZ (planche `V_ortho2022.jpg`).

## 6. Pilote B : trottoir avec abaissé, angle E Verdun NE / Vercors (`pilote/trottoir_abaisse.py`)

Zone locale : (8 ; −8) → (28 ; 12). Planches : `B_ortho2022.jpg`, `B_ortho2024.jpg`, `B_pente2021.jpg`, `B_plan2025.jpg`, `B_profil_vue.png`, `zone_B_*.jpg`, `datation_B_*.jpg`.

**Chaîne G1 de la bordure de rive** (`pilote_B/bordure_rive_B.geojson`). Elle est assemblée à partir de trois morceaux de sources différentes :

- GAM 369 ;
- GAM 385, coupé par la datation à 8,0 m : 13,0 m de courbe de 2025 sont écartés dans la zone ;
- PCRS 2019 n° 28 : bord ouest de l'ancien îlot du tourne-à-droite, absent du levé GAM.

| Contrôle | Résultat |
|---|---|
| Jonctions | 0,10 m et 0,9°, puis 0,03 m et 17,1° après troncature de 1,3 m du morceau précédent |
| Virage maximal | 6,8° par pas de 0,25 m, aucun au-delà de 10° |
| Écart dû au lissage | ≤ 2,6 cm |
| Longueur | 33,7 m |

Points notables :

- La bordure reste **continue à travers l'abaissé**, comme dans le levé GAM. Dans le PCRS 2019, la bordure s'interrompt sur 3,1 m à cet endroit : dans une description, un abaissé est un intervalle de vue, pas un trou.
- **Vue** :
  - points LiDAR 2021 : p50 14,4 cm ;
  - heightmap hors zones : 13,5 cm (|heightmap − points| p50 1,5 cm) ;
  - JPEG : 10,9 cm (−3,1 cm ; p90 9,6 cm).
- **Abaissé 2021** : s 17,38-20,38, soit 3,25 m. La vue y vaut 0 cm au JPEG et 3,7 cm aux points. Il tombe sur les chartières GAM (s 17,28 et 20,26) et sur la fin du zébra de 2022.
- La 2ᵉ plage basse détectée (s 30,4-31,6) n'est confirmée par aucun point. Elle tombe hors de la zone, au sud, sur le bord ouest de l'îlot : douteuse.
- **Matériaux** :
  - devant la bordure, enrobé de chaussée (L 162) ;
  - derrière, sur 0,5 à 1,5 m, massif terre et paillage (L 80, intensité ≈ 0, végétation basse) le long de la rive NE, puis herbe sèche dans l'îlot (ExG 22, R−B 12,5, intensité 205) ;
  - le trottoir est en enrobé clair (L 162, grain 2,5), avec deux dalles brunes, probablement des regards, à confirmer sur photo.
- Photo de contrôle : e5d79de9 du 2025-05-18.

## 7. Ce qui change par rapport à la v2 2026 (`description/base`)

| | Avant travaux (pilote) | v2 2026 | Écart |
|---|---|---|---|
| Îlot refuge du cœur | IA-1 : 7,02 m², galets, vue ≈ 15 à 17 cm | I-0390 « ilot_separateur » : goutte de 18,5 m², `gravier_concasse_6_10`, vue 0,15 | IoU 0,38, centres à 0,93 m. Matériau faux en 2026 comme avant (les galets sont vus en photo) |
| Îlot allongé | IA-2 : 22,26 m², galets | I-0629 : triangle mince de 8,85 m² dans la moitié ouest de l'ancien îlot (forme du plan 2025) | IoU 0,28, centres à 1,33 m |
| Chaussée de la zone A | Enrobé ancien (réfection au centre visible en 2024) | `enrobe_bbsg_neuf_2025`, état `modifie_2025` | — |
| Bordure de rive, zone B, partie NE et abaissé | Vue 14,4 cm, abaissé en s 17,4-20,4 | K-0369 (vue 0,135) et K-0385 (traversée en s 17,28-20,26, vue 0,02) | Identique : la partie NE n'a pas bougé |
| Bord ouest de l'ancien îlot (tourne-à-droite) | Bordure avec vue de 10 à 20 cm (JPEG), PCRS 2019 n° 28 | Absente. Remplacée par la courbe de 2025 (K-0385), avec une nouvelle traversée en s 30,2-33,6, à 0,28-1,0 m de l'ancienne ligne | Une voie d'enrobé d'environ 3 m devient espace vert en BRF : 46 m² en `brf_bois_concasse` dans la zone |
| Nivellement des îlots | LiDAR 2021 (crêtes nettes) | Heightmap « 2026 » : anciens îlots arasés, hauteurs standard 0,14 / 0,15 / 0,20 / 0,02 m | Le Z de 2026 est déduit, celui d'avant est mesuré |

## 8. Défauts constatés en 2026 : causes probables et parade d'une description d'avant travaux bien sourcée

Le diagnostic de la description 2D v2 (`pilote/partition_v2.py`, `diagnostic_v2_2026.json`, planches `diag_v2_*.jpg`) est fait par remplissage exact aux centres de pixels de 5 cm. Il donne :

- 0 m² de recouvrement entre les 1 410 surfaces ;
- 711 m² de trous hors bâtiments BD TOPO, dont 7,1 m² de fissures fines (< 0,3 m) et 704 m² dans 14 zones non décrites : 249 m² vers (6,5 ; 127,9), 190 m² vers (−130,5 ; −80,6), etc. ;
- 11 bordures (86,5 m) qu'aucune surface ne cite.

Les défauts visibles naissent donc surtout à la fabrication, de choix de sources que la description n'arbitre pas.

### 8.1 Sol en double couche (≈ 350 m² constatés)

**Causes probables :**

1. **Les surfaces à trous dépendent de l'orientation des anneaux.** Le lecteur orientait tous les anneaux de la même façon, et Triangulate 2D ne retirait pas les trous. S-0094a a ainsi été maillée sur 14 722 m² au lieu de 11 598 (§ 10 de `recon/pcg/houdini/hda/README_HDA.md`), soit 3 124 m² en double, ramenés à environ 6 m² après correction.
2. **Le sol est posé en plusieurs couches de Z différents.** Il se compose de l'emprise sous la bordure (au pied), du trottoir (coupé à l'arête arrière) et de la chaussée (coupée à la face). Toute imprécision de ces décalages recrée des recouvrements : TQ-SOL-009 en compte encore 14, dont un pire cas de 1,40 m² sur T_05_04 et 7 recouvrements sur T_02_02.
3. **Deux états se superposent sur le même sol.** La goutte de 2025 (I-0390, issue du levé GAM) recouvre l'emprise de l'ancien triangle, et I-0629 (plan 2025) se loge dans l'ancien IA-2. La régularisation doit alors trancher entre géométries concurrentes et crée des lamelles.

**Parade :**

- un seul état, une ligne datée par tronçon (§ 2) ;
- toutes les faces construites depuis **un graphe planaire unique**, avec des anneaux partagés : le trou d'une chaussée est l'anneau même de l'îlot, pas une copie ;
- contrôle : Σ aires = aire du domaine, 0 recouvrement, 0 trou (le pilote A le vérifie à 2 cm).

### 8.2 Fissures sans surface (≈ 70 m² constatés)

**Causes probables :**

- Des surfaces de part et d'autre d'une même bordure se touchent au-delà de son bout : environ 100 sommets de fissure en sol ouvert près des bouts de bordure (§ 8 du README_HDA). Les Z diffèrent alors de la vue, soit 10 à 20 cm.
- Une bordure s'arrête sans nœud, alors qu'elle devrait :
  - se refermer en anneau ;
  - finir sur une chartière (vue → 0) ;
  - ou finir en T sur une autre bordure.
- Le contrôleur relève 326 jonctions « en T contre le dos » (GA-BOR-005), K-0232 et K-0238 notamment.
- Enfin, 704 m² du domaine ne sont décrits par aucune surface.

**Parade :**

- **Chaînes G1 dont chaque extrémité est un nœud typé.** Le pilote B le montre : la bordure est continue à travers l'abaissé, et l'abaissé est un intervalle de vue mesuré entre deux chartières. Les jonctions entre sources différentes sont mesurées (écart ≤ 0,10 m) et tronquées, sans recouvrement.
- Ainsi le Z est continu au bout de toute bordure (vue 0), et deux surfaces ne se touchent qu'au droit d'une bordure ou d'un rampant décrit.
- Toute zone non décrite devient une face explicite (`autre`, `prive_non_decrit`), jamais un trou.

### 8.3 Refuge éclaté

**Causes probables :**

- Des ceintures d'îlots non fermées, ou faites de plusieurs bordures et de plusieurs surfaces :

  | Îlot | Ceinture | Écart maximal entre extrémités |
  |---|---|---:|
  | I-0297 | 3 bordures | 19,6 m |
  | I-0331 | 4 bordures | 9,0 m |
  | I-0339 | 6 bordures, 4 surfaces | 2,4 m |
  | I-0333 | — | 2,4 m |
  | I-0628 | — | 2,05 m |

  Le refuge I-0242 est en 3 surfaces.
- S'y ajoute le mélange plan 2025 / levé GAM / v1 au cœur (I-0629 : IoU 0,28 avec l'îlot réel d'avant). Dans le README, les « refuges en éclats » sont la conséquence directe des trous non retirés.

**Parade :**

- un îlot, c'est un anneau fermé G1 : IA-1 et IA-2 sont fermés, sans auto-intersection, avec une somme des virages de 360,0° ;
- une face d'emprise et une face de remplissage par îlot ;
- la coupe d'une traversée qui passe entre deux îlots, ou dans un îlot, est une face « passage » au niveau de la chaussée, bornée par deux bouts de bordure à chartière. Ce cas existe au cœur avant travaux : le zébra de Vercors passe entre IA-1 et IA-2.

### 8.4 Bordure orpheline

**Causes probables :**

- Les 11 bordures v2 qu'aucune surface ne cite sont **toutes dans le secteur est** (x de 99 à 147 m). Ce sont des lignes GAM de 2022-2024 (classes `apparue_2022_2024` ou `arasee_visible` à la datation : K-0479, K-0482, K-0506, K-0520, etc.).
- Les indices de classe de la v1 (2021-2022) y décrivent encore un chantier, si bien qu'aucune surface ne s'y appuie.
- Les doubles arêtes du levé GAM (deux traits par bordure) et les bordures « synthetique » du plan 2025 (K-9297a, K-0386z) produisent le même effet.

**Parade :**

- choisir la date cible et classer le secteur est à partir de l'ortho 2024 si la cible est 2024-2025 ;
- dédoublonner les arêtes (arête avant seule) ;
- contrôle bloquant : chaque bordure doit être citée par les deux faces qu'elle sépare.

### 8.5 Z incohérents (cause commune aux fissures)

TQ-SOL-013 trouve un écart pied − fil d'eau du MNT de 15 cm au p95 sur K-0380, et VAL-KRB-005 relève 961 cas de vue posée fausse. La cause : le « MNT 2026 » est synthétique dans la zone des travaux (îlots arasés, hauteurs standard).

Avant travaux, le LiDAR 2021 **est** l'état réel : il ne faut aucune hauteur standard au cœur, sauf là où aucune mesure n'existe, et ces endroits doivent être signalés.

## 9. Méthode recommandée (ordre de la chaîne)

1. **Fixer la date cible**, de préférence avant le 23/06/2025, et le masque de zone de travaux (`relief_zones_2026.geojson` + emprise du plan 2025).
2. **Rassembler les candidats vectoriels** : levé GAM `SOL_BORDURE`, `SOL_CANIVEAU` et `SOL_LIMITE_REVETEMENT`, et bordures PCRS 2019. Les dater tronçon par tronçon (`dater_gam.py`), garder selon la règle du § 2 et vérifier les `relief_seul` sur planche.
3. **Compléter les manques** : crêtes LiDAR 2021 sans ligne (`cretes_sans_ligne.py`), puis contours d'îlots sur l'ortho 2022 (`ilot_coeur.py`).
   - Si le dessus de l'îlot est en enrobé, il n'y a pas de contraste : utiliser la crête LiDAR, décalée de 0,27 m vers l'intérieur (biais mesuré), ou le LAZ.
   - Contrôle sur 2 photos 2024-2025 (`photos_controle.py`).
4. **Dédoublonner** : une seule arête avant par bordure, la plus proche de la chaussée.
5. **Chaîner en G1** (`trottoir_abaisse.construire_chaine`) :
   - morceaux ordonnés, coupés par la datation ;
   - troncature aux raccords, écart ≤ 0,10 m ;
   - extrémités sur des nœuds typés : anneau, chartière, T, raccord.
6. **Mesurer les vues** :
   - le long des lignes GAM et PCRS : `bordures_hauteurs` (points 2021) ;
   - pour les lignes nouvelles : profils sur le **LAZ 2021** ;
   - à défaut : MNT JPEG (±6 cm p90) plus la règle du profil, avec l'étiquette `conf: moyenne`.
   - Abaissés : trou dans la crête + vue < 4 cm sur ≥ 0,8 m, recoupés par les chartières et la fin du zébra de 2022.
7. **Niveler** sur le sol nu LiDAR 2021 sans aucune modification de 2025. Régénérer `dtm_sol_10cm.tif` avec l'étape relief de la v1, ou repartir du LAZ. La heightmap 3025 n'est utilisable qu'hors `relief_zones_2026`.
8. **Attribuer les matériaux** :
   - signatures sur l'ortho 2022 (grain, ExG, R−B, luminance) et intensité LiDAR (`materiaux.py`), puis confirmation sur les photos 2024 à 2025-S1 ;
   - BRF et pavés restent à calibrer sur d'autres placettes : aucune dans les zones pilotes ;
   - remplissage des îlots du cœur : **galets**.
9. **Construire la partition** depuis le graphe planaire (`partition_A.py` en donne le schéma), avec les contrôles bloquants avant fabrication :
   - Σ aires = domaine ;
   - recouvrement = trou = 0 (centres de pixels à 2 à 5 cm) ;
   - chaque bordure citée par 2 faces ;
   - chaque îlot = 1 anneau fermé ;
   - chaque extrémité de bordure sur un nœud.

## 10. Limites et suites

- **Nuage LiDAR HD 2021 classé (LAZ / COPC, IGN Géoplateforme, dalle de 1 km couvrant x 917-918 km, y 6460-6461 km)**. Il n'est pas sur le PC et n'a pas été téléchargé : c'est à l'utilisateur de l'autoriser. Il donnerait les vues au cm des îlots disparus, du séparateur de Verdun NE et des crêtes sans ligne, et permettrait de régénérer le sol nu sans les modifications de 2025.
- Les rasters `lidar/dtm_*` du dépôt sont des JPEG couleur à palette : utiles pour détecter, pas pour mesurer au cm. `slope_pct_15cm` est très utile pour la datation.
- La classe `relief_seul` (449 m) et les 13 crêtes sans ligne au cœur demandent une revue visuelle. Les 3 crêtes rondes de 3,6 à 4,6 m sont probablement des pieds de mâts.
- Le profil des bordures d'îlot (I2 ou T2 / T3) et la tête mesurée de 0,25 à 0,27 m sont à confirmer : LAZ plus gros plans Mapillary 2024 ou Panoramax 2025-05.
- La datation est faite à 0,5 m avec un lissage de 2,5 m. Les tronçons très courts (< 1,5 m) sont peu fiables.

## Fichiers

Scripts (`pilote/`) :

| Script | Rôle |
|---|---|
| `commun_sol.py` | Repère, mosaïques, heightmap, zones modifiées |
| `geom_contours.py` | Composantes, contours, G1, remplissage exact |
| `comparer_gam_etat2026.py` | Comparaison du levé GAM et de `etat_2026` |
| `dtm_jpg.py` | Décodage du MNT JPEG |
| `precision_hauteurs.py` | Précision des hauteurs selon la source |
| `precision_vecteurs.py` | Cohérence GAM / PCRS et Z du PCRS |
| `dater_gam.py` | Datation tronçon par tronçon |
| `planche_datation.py` | Planches de datation |
| `planche_apercu.py`, `planche_zone.py` | Planches d'aperçu et de zone |
| `ilot_coeur.py` | Pilote A (et zone V avec `2 -2 34 30 V`) |
| `partition_A.py` | Partition de la zone A et comparaison v2 |
| `trottoir_abaisse.py` | Pilote B |
| `photos_controle.py` | Vignettes photo de contrôle |
| `materiaux.py` | Signatures des matériaux |
| `cretes_sans_ligne.py` | Crêtes LiDAR sans ligne vectorielle |
| `partition_v2.py` | Diagnostic topologique de la v2 2026 |

Ordre de lancement : `comparer_gam_etat2026` → `dtm_jpg` → `precision_hauteurs` → `dater_gam` → `ilot_coeur` (A, puis V) → `partition_A` → `trottoir_abaisse` → `photos_controle` → `materiaux` → `cretes_sans_ligne` → `partition_v2` → `precision_vecteurs` → planches.

Résultats :

- `comparaison_gam_etat2026.json`, `datation/{gam_bordures_datation.geojson, datation_resume.json}`, `precision_hauteurs.json`, `precision_vecteurs.json`, `dtm_jpg_decodage.json`, `materiaux_signatures.json`, `cretes_sans_ligne.json`, `diagnostic_v2_2026.json` ;
- `pilote_A/{ilots_avant_travaux.geojson, partition_A.geojson, mesures_A.json, comparaison_v2_A.json}`, `pilote_B/{bordure_rive_B.geojson, mesures_B.json}`, `pilote_V/` ;
- 46 planches dans `planches/` et 6 vignettes non versionnées.
