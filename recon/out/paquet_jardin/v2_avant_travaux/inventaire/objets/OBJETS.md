# Objets de l'état avant travaux (printemps 2025) : recensement et preuves

**État visé** : le carrefour Paquet Jardin juste avant le chantier, qui court du 23/06/2025 au 05/12/2025 (trottoirs du Vercors jusqu'au 30/01/2026). Les preuves retenues datent de 2022 à 2025 ; tout ce qui est postérieur au 22/06/2025 est écarté.
**Livrable principal** : `objets_avant_travaux.geojson`. Il compte 759 objets, en EPSG:2154. Les objets exclus sont dans `objets_exclus.geojson` (97), chacun avec sa raison.
**Chaîne reproductible** : les scripts sont dans `scripts/` et se lancent depuis la racine du dépôt, avec `python -I`.

```
python -I recon/out/paquet_jardin/v2_avant_travaux/inventaire/objets/scripts/mly_map_features.py data/sites/paquet_jardin/avant_travaux/mapillary_map_features
python -I .../scripts/osm_historique.py data/sites/paquet_jardin/avant_travaux/osm_historique
python -I .../scripts/pnx_semantique.py data/sites/paquet_jardin/panoramax_pictures.geojson data/sites/paquet_jardin/avant_travaux/panoramax_semantique
python -I .../scripts/inventaire.py      # fusion -> objets_avant_travaux.geojson, objets_exclus.geojson, inventaire_stats.json
python -I .../scripts/vignettes.py [--mapillary-seul]   # vignettes photo (non versionnées)
python -I .../scripts/comparaison.py     # comptes, couverture, comparaison 2026 -> comparaison_2026.json
python -I .../scripts/carte.py           # cartes/carte_site.png, carte_coeur.png, carte_arret_reviree.png
```

## 1. Résultat en bref

| | nombre |
|---|---|
| Objets avant travaux, tous types (hors exclus) | **759** |
| — présents (au moins une preuve directe datée 2022-2025 : photo, ortho, constat, ou détection confirmée) | 471 |
| — présumés (LiDAR 2021, OSM d'avant travaux, détection automatique seule ou levé GAM non daté hors chantier) | 219 |
| — incertains | 69 |
| Confiance haute / moyenne / faible | 339 / 198 / 222 |
| Mobilier et signalisation (hors arbres et clôtures) | 243 |
| Objets à moins de 3 m de l'emprise des travaux 2025 | 161 |
| Objets avec orientation connue (`azimut_face_deg`) | 128 |
| Objets avec hauteur LiDAR 2021 | 334 |
| Exclus : vus seulement de 2017 à 2020 | 54 |
| Exclus : absents avant travaux (plan 2025, OSM ou photo postérieurs) | 26 |
| Exclus : disparus avant travaux | 6 |
| Exclus : doublons | 5 |
| Exclus : objets de chantier temporaires | 5 |
| Exclus : faux positif | 1 |

**Découverte principale : les deux arrêts « La Revirée » ont été déplacés par les travaux.** Dans OSM, après le 20/06/2025, tout le mobilier de chaque arrêt a été translaté d'un même vecteur.

- **Arrêt SE** : déplacé de **36,8 m vers le SO** (dx −28,7, dy −23,0). Cela concerne l'abri `way/185326914`, le banc, la corbeille, le caisson d'affichage et le plan de quartier ; le nœud d'arrêt `node/498507091` a bougé de 41,8 m.
- **Arrêt NO** : déplacé de **18,1 m vers le NE** (+12,6, +13,0). Cela concerne l'abri `way/185326911`, la corbeille, le distributeur, l'affichage et le plan, ainsi que le nœud d'arrêt `node/514050476`.

L'ancienne position est confirmée par trois sources indépendantes :

- les détections Mapillary d'avant travaux, situées à l'ancienne position et non à la nouvelle (banc 2022-06, corbeille 2017-2023, affichage 2018-2022) ;
- l'ortho PCRS 2022, qui montre les deux abris aux anciennes positions (`cartes/carte_arret_reviree.png`) ;
- deux Panoramax calées (734a0da6 du 18/05/2025 et aa9d7e12 du 24/08/2024), où l'abri SE, le banc et la corbeille tombent sur l'axe.

La description 2026 place ces 10 objets à leur position d'après travaux. L'inventaire les ramène à leur position du 20/06/2025 (`position_2026_l93` et `ecart_position_2026_m` sont conservés). Le poteau d'arrêt SE d'avant travaux (`node/6569621813`, vu sur Mapillary le 10/06/2022 et sur Panoramax le 18/05/2025) a été supprimé d'OSM après les travaux. Il est absent de la description 2026.

## 2. Sources et téléchargements

Toutes les sources sont des données publiques, traitées comme non fiables : elles sont lues par des scripts lancés avec `python -I`, et les scripts sont rangés hors des dossiers de téléchargement.

| Source | Requête | Contenu obtenu | Rangement |
|---|---|---|---|
| Mapillary « map features » (points et panneaux) | `https://graph.mapillary.com/map_features` sur l'emprise 5.7660-5.77035 / 45.2062-45.2091, en 12 tuiles, puis `/{id}/detections` et `/images?image_ids=` | 473 objets avec `first_seen_at`, `last_seen_at`, `aligned_direction` et images ; 1 536 images détectantes datées de 2017-06 à 2025-05 (2022 : 54, 2023-03 : 36, 2024-02 : 229, 2024-08 : 63, 2025-05 : 16) | `data/sites/paquet_jardin/avant_travaux/mapillary_map_features/` |
| OSM historique | Overpass `[date:"…"]` sur overpass-api.de (repli : overpass.private.coffee, maps.mail.ru) ; nœuds étiquetés, ainsi que les ways `barrier`, `amenity=shelter`, `bicycle_parking` et `tree_row` | instantanés 2020-06-01 (63 éléments), 2022-05-10 (102), 2023-06-01 (107), 2024-06-01 (112), **2025-06-20 (165, référence avant travaux)** et actuel du 11/10/2026 (190) | `data/sites/paquet_jardin/avant_travaux/osm_historique/` |
| Panoramax, recherche fédérée | `https://api.panoramax.xyz/api/search` (bbox, période 2022-01-01 à 2025-06-22) | 174 photos, dont **43 absentes de l'index local** : 13 en 2023-03, 12 en 2024-05, 10 en 2024-08, 1 en 2025-01, 7 en 2025-05 | `.../panoramax_semantique/recherche_2022_2025.json` |
| Panoramax, sémantique | `{instance}/api/collections/{c}/items/{id}` (`properties.annotations`) | 35 photos annotées (modèles SGBlur-yolo11s et classify_fr_road_signs) avec des codes FR. Avant travaux, seulement 2025-05 (11 photos) ; une seule photo annotée plus ancienne (24/08/2024, un cèdre) | `.../panoramax_semantique/annotations.json` |

**Jeton Mapillary.** Il est lu uniquement dans `%USERPROFILE%\.config\meylan_adas\mapillary_token.txt` et transmis par l'en-tête `Authorization: OAuth`. Il n'est jamais affiché ni écrit, et les URL enregistrées en sont purgées.

Les sources déjà présentes dans le dépôt :

- description 2026 résolue (`v2/description/resolue/objets/{mobilier,arbres}.geojson` : 235 objets de mobilier et 486 arbres, lus et non modifiés) ;
- 1 441 observations V2 `v2/enrichi/recensement/obs_*.json`, dont seules celles antérieures au 23/06/2025 valent preuve ;
- `triangulation_mixte.json` (31 axes) ;
- les constats de `analysis/paquet_jardin/constats_verifies.json` (640, datés par `date_source`) ;
- les poses Panoramax (`poses.json`) et Mapillary (`poses_mapillary.json`).

**Constats sur les données du dépôt**

- **`gam_topo_sol_*` (vector) et `etat_2026/` sont identiques.**
  - Les 285 symboles d'arbre et les 4 614 sommets de bordure coïncident à 10⁻⁸ m près, une fois reprojetés de WGS84 en L93.
  - Ce levé GAM n'est donc pas un levé d'avant travaux. Je le traite comme « levé non daté (identique à etat_2026) ».
  - Il n'atteste l'avant-travaux que hors de l'emprise du chantier.
- **Les rasters LiDAR `height_above_ground_15cm` et `25cm` ne sont que des aperçus JPG 8 bits.** L'échelle est écrêtée à 0-0,5 m (`pipeline/lidar_raster.py`, paramètre `to_png(hag, 0, 0.5)`), ce qui les rend inutilisables pour les mâts. Les hauteurs LiDAR 2021 utilisées viennent des attributs `hauteur_lidar_2021_m` de la description (334 objets). Un autre agent télécharge la dalle COPC `LHD_FXX_0917_6461`, dont je n'ai vu que l'en-tête.

## 3. Méthode de fusion (`scripts/inventaire.py`)

### 3.1 Les candidats

Il y a cinq familles de candidats.

1. **Les objets de la description 2026.** Les preuves sont tirées du texte `source`, des `resolution.decisions`, de la hauteur LiDAR et du contrôle de verdure de l'ortho 2024 pour les arbres. Une preuve datée d'après le 22/06/2025 est classée `post_travaux`.
2. **Les observations V2 antérieures aux travaux.**
   - Une observation liée à un objet (`lien_description`) devient une preuve. Son statut `absent_sur_image` produit une absence datée, et le statut `incertain` produit un indice.
   - Une observation `absent_de_description` donne un nouvel objet. Il y en a 17.
   - Les champs `type_reel` sont exploités : par exemple, `lamp_lidar_SW_NO` est requalifié en poteau de réseau en bois.
3. **OSM.**
   - Un élément est associé par son identifiant, à défaut par sa position.
   - La preuve « osm_historique » liste les instantanés où l'élément est présent.
   - Un élément présent le 20/06/2025 mais inconnu de la description devient un nouvel objet.
4. **Mapillary.**
   - Une détection est associée à l'objet de même type le plus proche, dans un rayon égal à 1,6 fois le rayon du type plus 1 m.
   - Une détection de mât générique peut porter un panneau, un feu ou un lampadaire.
   - À défaut d'association, un nouvel objet (σ 3 m) est créé s'il y a au moins 2 images détectantes ou un panneau codé. Il y en a 120.
   - Les détections au sol (marquages, regards, avaloirs) et les enseignes sont ignorées (124).
5. **Les annotations Panoramax du 18/05/2025 sur photos calées.** Un relèvement à 2,5° près associe l'annotation à un panneau : 19 associées, 4 libres.

### 3.2 Position d'avant travaux

La position est corrigée dans deux cas.

- **Cas A : l'élément OSM a bougé d'au moins 5 m après le 20/06/2025.** On reprend sa position du 20/06/2025, sauf si une observation photo d'avant travaux confirme la position 2026. C'est le cas des arceaux `node/12125436855`, confirmés le 24/08/2024 par MLY-MOB-034 : leur déplacement OSM est une correction.
- **Cas B : objet dans l'emprise des travaux (3 m ou moins) dont la position 2026 dépend du plan 2025 ou d'une source postérieure.** On reprend, par ordre de priorité, la triangulation V2 sur des vues d'avant travaux, puis la position corrigée sur photo, puis la position OSM du 20/06/2025.

Au total, 22 positions ont été ramenées à l'état d'avant travaux (13 relogements de 9,5 à 36,8 m, 9 retouches de 0,25 à 4,9 m dont une fusionnée en doublon).

### 3.3 Doublons et revue visuelle

- **Doublons (GEN-06).** Deux objets de même type à moins de 1 m sont fusionnés (sauf les panneaux, les arbres et les feux), ainsi que les candidats Mapillary et OSM proches d'un objet déjà retenu.
- **Revue visuelle (`revue_visuelle_objets.json`).** J'ai examiné 103 vignettes, sur 8 planches.
  - Bilan : 60 confirmations, 5 doublons (dont 2 « feux » Mapillary mal positionnés), 2 panneaux de chantier temporaires, 1 faux positif (jeune arbre tuteuré), 1 absence (arbre_184) et 3 incertains.
  - Exemples de confirmations : les 20 candélabres du quartier neuf (est) et de l'ouest, absents d'OSM et de la description ; la borne d'incendie ; un banc et une corbeille ; les panneaux B1, B13, B6d, B21a1, B22a et D21 ; les poteaux de la ligne aérienne qui suit Verdun.

### 3.4 Statut avant travaux et confiance

| Statut | Condition |
|---|---|
| `present` | au moins une preuve forte (photo ou ortho) datée 2022-2025, ou deux sources directes, ou une détection jointe à LiDAR, OSM ou GAM |
| `present_presume` | détection, indice, LiDAR 2021 ou OSM d'avant travaux, sans observation confirmée |
| `incertain` | levé GAM seul dans l'emprise ; objet absent de l'ortho 2022 mais levé ensuite hors chantier ; attesté seulement après travaux, hors emprise |
| `non_revu_2022_2025` (exclu) | vu seulement de 2017 à 2020 |
| `disparu_avant_travaux` (exclu) | absence constatée après la dernière preuve positive, avant juin 2025 |
| `absent_avant_travaux` (exclu) | aucune preuve positive avant travaux |

La **confiance** porte sur l'existence de l'objet ; la position a son propre `sigma_position_m`.

| Confiance | Condition |
|---|---|
| haute | au moins deux sources indépendantes dont une forte, et σ ≤ 0,6 m |
| moyenne | les autres objets présents ; un objet présumé avec au moins deux signaux |
| faible | le reste |

### 3.5 Couverture photo

`nb_photos_visibles` compte les photos du 01/01/2023 au 22/06/2025 dont la pose est calée et qui voient l'objet géométriquement :

- distance maximale par type, de 15 m (potelet) à 50 m (abri) ;
- champ horizontal pour les images à plat ;
- occultation par les emprises bâties (`batiments_local`) ; la végétation et les véhicules ne sont pas pris en compte.

Il y a 64 caméras calées : 19 Panoramax et 45 Mapillary. On calcule aussi :

- `nb_photos_visibles_a_priori` : le même calcul sur 244 poses a priori (SfM Mapillary, GNSS Panoramax) ;
- `nb_photos_detecte` : le nombre d'images où l'objet est réellement détecté ou observé (Mapillary, annotations Panoramax, observations V2, revue visuelle).

### 3.6 Champs du GeoJSON

| Rubrique | Champs |
|---|---|
| Identité | `id`, `type`, `sous_type`, `code`, `code_source` |
| Dimensions et orientation | `hauteur_m`, `hauteur_source`, `hauteur_lidar_2021_m`, `azimut_face_deg` (grille L93), `azimut_source` |
| Statut | `etat_avant_travaux`, `confiance`, `raison` |
| Position | `sigma_position_m`, `origine_position`, `position_source`, `position_2026_l93`, `ecart_position_2026_m` |
| Dates et photos | `vu_de`, `vu_a`, `nb_photos_visibles`, `nb_photos_visibles_acceptees`, `nb_photos_visibles_a_priori`, `nb_photos_detecte`, `photos_visibles` |
| Preuves | `preuves[{source, id, date, nature, …}]`, `absences[]` |
| Identifiants externes | `osm_ids`, `osm_instantanes`, `mapillary_ids`, `mapillary_dates` |
| Lien avec 2026 | `lien_2026`, `statut_2026` |
| Contexte | `d_zone_travaux_m`, `d_constructions_2023_2024_m`, `triangulation_v2`, `revue_visuelle`, `notes`, `x_local`, `y_local` |

## 4. Comptes par type

Les colonnes de couverture sont des nombres d'objets. « Calées » = vus sur au moins 2 photos datées 2023-2025 à pose calée ; « toutes poses » ajoute les poses a priori ; « détecté » = détecté sur au moins 2 images.

| Type | n | Présent | Présumé | Incertain | Haute | Moyenne | Faible | Cœur ≤ 60 m | ≥ 2 photos calées | ≥ 2 photos (toutes poses) | Détecté ≥ 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| arbre | 466 | 292 | 132 | 42 | 250 | 94 | 122 | 54 | 189 | 337 | 3 |
| lampadaire | 64 | 55 | 9 | 0 | 23 | 38 | 3 | 8 | 33 | 52 | 41 |
| barrière (dont 51 clôtures linéaires) | 62 | 1 | 45 | 16 | 1 | 2 | 59 | 12 | 21 | 33 | 0 |
| panneau (police, directionnel, information, balises) | 57 | 41 | 9 | 7 | 16 | 28 | 13 | 21 | 42 | 49 | 34 |
| autre mobilier (affichage, totems P+R, distributeurs, blocs, conteneurs, portique) | 34 | 27 | 7 | 0 | 17 | 10 | 7 | 7 | 6 | 30 | 8 |
| poteau (réseau bois, ligne aérienne, mât caméra) | 19 | 11 | 6 | 2 | 5 | 6 | 8 | 8 | 14 | 19 | 13 |
| feu (tricolore, piétons, cycles) | 11 | 10 | 0 | 1 | 9 | 1 | 1 | 11 | 11 | 11 | 10 |
| arceaux vélos | 10 | 3 | 6 | 1 | 1 | 3 | 6 | 2 | 2 | 5 | 1 |
| banc | 8 | 7 | 1 | 0 | 5 | 2 | 1 | 1 | 1 | 3 | 3 |
| potelet | 8 | 8 | 0 | 0 | 6 | 2 | 0 | 2 | 4 | 5 | 2 |
| armoire / coffret | 7 | 7 | 0 | 0 | 3 | 4 | 0 | 4 | 1 | 4 | 0 |
| corbeille | 6 | 4 | 2 | 0 | 1 | 3 | 2 | 1 | 1 | 4 | 2 |
| borne (incendie) | 4 | 3 | 1 | 0 | 2 | 2 | 0 | 1 | 0 | 2 | 1 |
| abri bus | 2 | 1 | 1 | 0 | 0 | 2 | 0 | 1 | 2 | 2 | 1 |
| poteau d'arrêt | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 |
| **Total** | **759** | **471** | **219** | **69** | **339** | **198** | **222** | 134 | 328 | 557 | 120 |

Origine des positions :

- 684 viennent de la description 2026, avec σ de 0,25 à 0,6 m (OSM, GAM, LiDAR, ortho 2022, triangulation) ;
- 57 viennent de Mapillary seul (σ 3 m) ;
- 17 viennent des observations V2 ;
- 1 vient d'OSM 2025.

Signalisation verticale et feux du cœur, avant travaux : 11 supports de feux et 21 panneaux dans un rayon de 60 m. Les codes viennent de la description, des annotations Panoramax du 18/05/2025 (FR:B1, B2a, B2b, B21a1, C113, C114, J5, AB4) et des panneaux Mapillary.

## 5. Couverture photo

| Ensemble | n | Vus sur ≥ 2 photos 2023-2025 à pose calée | Idem, poses acceptées seules | Idem, avec poses a priori | Détectés sur ≥ 2 images | Détectés sur ≥ 1 image |
|---|---|---|---|---|---|---|
| Tous les objets | 759 | **43,2 %** | 42,8 % | 73,4 % | 15,8 % | 24,8 % |
| Hors arbres et clôtures | 231 | **51,1 %** | 50,6 % | 81,0 % | 50,6 % | 55,8 % |
| Cœur (≤ 60 m) | 134 | **79,9 %** | 77,6 % | 88,8 % | 37,3 % | 47,0 % |
| Cœur, hors arbres et clôtures | 68 | **85,3 %** | 83,8 % | 95,6 % | 69,1 % | 79,4 % |
| Emprise des travaux (≤ 3 m) | 161 | **74,5 %** | 73,9 % | 96,9 % | 32,9 % | 40,4 % |

Les photos calées se concentrent au cœur : Panoramax du 01/05/2024, du 24/08/2024 et du 18/05/2025, et sphériques Mapillary du 24/08/2024 et du 18/05/2025. Au-delà de 60 m, il ne reste que les poses a priori, notamment la séquence Mapillary à plat du 24/02/2024 (229 images détectantes) et celle du 18/03/2023.

Pour les arbres, la couverture « détectée » est quasi nulle : Mapillary ne détecte pas les arbres, et les observations V2 n'en confirment qu'une partie.

## 6. Comparaison avec la description 2026

Le détail figure dans `comparaison_2026.json` ; les cartes sont dans `cartes/`.

### 6.1 Objets de la description 2026 (721)

| Catégorie | n | Détail |
|---|---|---|
| Conservés (même position à 0,3 m près) | 597 | 422 arbres, 45 clôtures et barrières, 39 lampadaires, 29 panneaux, 22 autres, 7 feux, 7 poteaux… |
| Déplacés par les travaux (≥ 5 m) | 13 | Les deux arrêts La Revirée : abris, banc, 2 corbeilles, distributeur, 2 affichages, 2 plans. S'y ajoutent 2 arceaux (10-12 m) et 1 portillon (9,5 m), à vérifier (correction OSM possible) |
| Position d'avant travaux différente (0,3 à 5 m) | 7 | 3 feux (triangulation V2 sur vues 2024-08 et 2025-05 : `feu_SW_cycles_SE` 2,09 m, `feu_SW_droite` 0,88 m, `feu_VERC_O_pietons` 0,85 m), 3 lampadaires (OSM 2025 : `lamp_9514795519` 4,87 m, `lamp_12882680524` 3,07 m, `lamp_9514795817` 0,88 m), 1 poteau en bois (`poteau_reseau_12888048898`, 1,81 m) |
| Ajoutés par les travaux ou après | 26 | 14 arbres plantés en 2025 (plan projet) et `arbre_144` (inventaire « abattu », absent de l'ortho 2024 et le 18/05/2025, absent en 2026 : jamais présent sur la période) ; `feu_SW_cycles_NO` et `pan_B21a1_3` (plan 2025 seul) ; poteaux d'arrêt `poteau_NO_0021` (plan 2025) et `poteau_REV_ligne42` (absent le 18/05/2025) ; potelets `13827066657/58` (OSM 2026, dans l'emprise) ; lampadaires `13539965051` (absent sur l'ortho 2022 et sur Mapillary 2024) et `13624569647` ; portail `12976463291`, clôture `1305902500`, boîte aux lettres |
| Incertains avant travaux | 69 | 42 arbres (levé GAM seul dans l'emprise, ou absents de l'ortho 2022 puis levés), 16 clôtures GAM, 7 panneaux attestés seulement en 2026 (ENR-PAN-004/005/006/009, `pan_B1_2`, `pan_C13a_1`, `panneau_information_13539969129`), `feu_SW_TPC` (aucun mât à la position déduite du plan sur deux vues 2024 et 2025), 2 poteaux OSM 2026, 1 arceau |
| Disparus avant travaux | 6 | arbres `arbre_018`, `114` et `365` (vus en 2021-2022, absents de l'ortho IGN du 09/08/2024), `arbre_184` (absent sur deux vues 2024 et 2025, revue visuelle), `arbre_269` et `435` (absents de l'ortho 2022) |
| Non revus de 2022 à 2025 | 2 | `feu_SW_NO_pietons` et `poteau_SE_0396` (déduits 2026) |

### 6.2 Objets d'avant travaux absents de la description 2026 (75)

**Dans l'emprise des travaux (22) : probablement supprimés par les travaux, ou oubliés par la description.**

- le poteau d'arrêt SE d'avant travaux (OSM `node/6569621813`, supprimé d'OSM après les travaux) ;
- 2 armoires : une armoire de commande des feux probable à l'angle SE (VISION-PANORAMAX-2-1, 24/08/2024) et un coffret maçonné sur la rive E du Vercors ;
- 3 groupes de lames directionnelles D21 (Mapillary 2022) ;
- 2 balises B21a1 et 2 plaques de rue ;
- 2 totems P+R (Mapillary 2020-2023, sur l'îlot supprimé) et 1 totem d'information ;
- 2 affichages et 1 plaque sur clôture ;
- 4 poteaux (ligne aérienne et bois) ;
- 1 lampadaire résidentiel ;
- 1 coffre à conteneurs.

**Hors emprise (53) : lacunes de la description 2026, probablement toujours en place.**

- **22 lampadaires.** Il s'agit de 11 luminaires LED du quartier neuf est (Mapillary du 24/08/2024) et de 9 luminaires du parc et de l'allée à l'ouest (Mapillary du 24/02/2024), tous confirmés en revue visuelle, plus un luminaire au SO (Mapillary 2018-2024, sans revue) et une borne globe vue sur l'ortho 2022.
- **12 panneaux** : B1, B13 3,5 t « dalle sur parking », B6d, B22a, 2 B21a1, AB4, AB3a, un grand panneau D21/D42 vu sur l'ortho 2022, et 3 panneaux non codés.
- **5 poteaux.**
- **Divers** : 2 bancs, corbeille, borne d'incendie, bac roulant, conteneurs à déchets, 2 files de potelets inox du quartier neuf, 2 coffrets, portique d'entrée de la jardinerie, arceaux, 2 éléments végétaux (souche ou massif, arbustes en boule).

### 6.3 Chronologie OSM autour des travaux (instantanés du 20/06/2025 et du 11/10/2026)

- **Supprimés après le 20/06/2025** :
  - 2 traversées à feux (`node/1722505401`, `node/6569621810`) ;
  - le nœud `traffic_signals` `1959011179` ;
  - l'arrêt `node/514050473` ;
  - le poteau d'arrêt `6569621813` ;
  - un emplacement d'autopartage.
- **Créés après les travaux** :
  - 5 lampadaires (`13539939799`, `…946625`, `…950055`, `…965051`, `13624569647`) ; 3 d'entre eux sont visibles sur l'ortho 2022, donc anciens mais cartographiés tard ;
  - 3 poteaux de réseau, 2 potelets, 3 portillons, la barrière levante `3375058657`, une armoire et des arceaux.
- **Avant les travaux**, OSM passe de 23 lampadaires (2022-2024) à 38 (2025-06-20) puis à 43 (2026). Un instantané OSM daté ne prouve donc pas l'absence d'un objet ; il prouve seulement sa présence.

## 7. Limites

- **Positions Mapillary seules (57 objets, σ 3 m).** Deux « feux » triangulés par Mapillary se sont révélés mal placés (à plus de 7 m) en revue visuelle. Les panneaux directionnels et les totems P+R du cœur peuvent être des doublons d'objets de la description dont la position diffère de plus de 6,6 m.
- **Visibilité géométrique.** Elle ignore la végétation. La moitié des « vus sur ≥ 2 photos » n'ont aucune détection réelle, surtout les arbres et les clôtures.
- **Panoramax : 43 photos 2023-2025 non téléchargées, et séries non calées.** La série du 18/03/2023 (25 photos de l'index et 13 de plus) n'a pas de pose calée ; elle n'est comptée qu'en « a priori ».
- **Couverture temporelle.** Mapillary n'a aucune image entre le 18/05/2025 et les travaux. Les détections les plus récentes datent du 18/05/2025.
- **Clôtures GAM (51).** Elles ne sont prouvées que par le levé (non daté). La revue Mapillary 2024-2025 en voit souvent une haie et non une clôture.

## 8. Méthode recommandée de placement précis

1. **Constituer la base de photos d'avant travaux, et rien qu'elle.**
   - Photos à retenir : Panoramax 2024-05-01, 2024-08-24 et 2025-05-18 (19 poses calées), Mapillary sphériques 2024-08-24 et 2025-05-18 (45 calées).
   - Photos à caler en plus : Panoramax 2023-03-18, et Mapillary 2023-03-18 et 2024-02-24 (à plat), avec `poses.py` / `mapillary.py --poses --recaler`.
   - Ne caler qu'avec des GCP valides avant travaux : mâts LiDAR 2021, coins de zébras et marques de l'ortho 2022, « fantômes ». Jamais avec les bordures GAM 2026 dans l'emprise : le recalage sur les bordures de `mapillary.py` utilise le GAM, qui est l'état 2026.
   - Télécharger les 43 Panoramax manquantes, listées dans `recherche_2022_2025.json`.
2. **Trianguler chaque objet vertical sur ces seules photos** avec `triangulation.py` (`trianguler_verticale`, RANSAC, pose réajustée sans l'objet).
   - Amorcer chaque visée par la boîte de détection Mapillary (décodée par `vignettes.py:mvt_bbox`), qui donne directement l'azimut de l'objet dans l'image, ou par l'annotation Panoramax.
   - Critères d'acceptation, ceux du README `enrichir` : au moins 3 vues, angle d'intersection ≥ 20°, σ ≤ 0,25 m, stabilité leave-one-out. Revue visuelle obligatoire au-delà de 0,75 m d'écart.
   - Ordre de priorité :
     - (a) les 57 objets Mapillary seuls, dont les 22 lampadaires et 12 panneaux absents de 2026 ;
     - (b) les 22 objets de l'emprise absents de 2026 ;
     - (c) `feu_SW_TPC` et les 7 positions retouchées ;
     - (d) les 13 objets relogés des arrêts, dont la position vient d'OSM à ±1 m.
   - Les arrêts sont visibles depuis 734a0da6 (18/05/2025) et aa9d7e12 (24/08/2024), entre 17 et 23 m.
3. **Hauteurs et Z.**
   - Hauteur : LiDAR 2021 en priorité (334 objets). À défaut, la triangulation du sommet (élévation angulaire depuis 3 vues), puis le défaut par type.
   - Z : MNT LiDAR 2021, et non le MNT 2026, dans l'emprise des travaux, car l'ancienne chaussée a été rehaussée en 2025.
   - Les mâts sans hauteur sont à ré-extraire de la dalle COPC `LHD_FXX_0917_6461` : amas fins de classe 1 de plus de 3 m, emprise inférieure à 0,5 m.
4. **Règles d'implantation** (`assets/specs/regles_implantation.json`, 66 règles, `resolution.qualite_preuve`).
   - **Sigma des sources** : LiDAR 2021 0,15 m, ortho 2022 0,25 m, triangulation PnP 0,3 m, Panoramax brut et Mapillary 1,5 à 3 m. Au-dessus de `seuil_sigma_normatif_m` (0,5 m), les règles « majeures » deviennent des contraintes dures, ce qui vaut pour tout objet Mapillary seul :
     - GEN-01 : pas de support sur la chaussée ;
     - GEN-03 : recul de 0,30 m ;
     - ECL-01 : candélabre à 0,50-1,20 m derrière la bordure ;
     - ECL-03 et ECL-04 : alignement et pas régulier des rangées (utiles pour caler la rangée de LED du quartier est) ;
     - SIG-05 : côté droit ; SIG-10 et SIG-11 : balises J5 et B21a1 en nez d'îlot ;
     - FEU-01 et FEU-04 ;
     - POT-01 et POT-02 ;
     - TC-01 et TC-02 : abri et poteau sur le quai d'avant travaux.
   - **Ne jamais « corriger » un objet bien prouvé au nom de la norme**, conformément à `resolution.politique`.
   - **Le fichier est écrit pour l'`etat_cible` d'octobre 2026.** Pour l'avant-travaux, il faut appliquer les règles aux bordures et surfaces d'avant travaux : ortho 2022, `bordures_hauteurs` « fil d'eau 2021 », couches `gam_*_pcrs` si elles datent d'avant 2025. Dans l'emprise (161 objets à 3 m ou moins), GEN-07 s'applique à rebours : réancrage sur la bordure d'avant travaux.
5. **Orientation.**
   - Règles : SIG-04 (face perpendiculaire à la voie visée, tournée de 3 à 5° vers l'extérieur), FEU-05, ECL-02 (crosse perpendiculaire à la bordure) et MOB-02.
   - Sources : `aligned_direction` Mapillary (converti en grille : azimut L93 = azimut vrai − 2,0086°) pour les panneaux codés, et face ou dos des annotations Panoramax.
   - 128 objets ont déjà un azimut.
6. **Contrôle final.** Projeter l'inventaire dans les vues calées d'avant travaux (`planche.py`, `vignettes.py`) et faire relire les planches par une revue indépendante, comme en V2. Pour l'arrêt SE, contrôler en plus sur l'ortho Pléiades 2025 et sur l'IGN 2024.

## 9. Fichiers

Fichiers versionnables :

- `objets_avant_travaux.geojson` (759) et `objets_exclus.geojson` (97) ;
- `inventaire_stats.json` et `comparaison_2026.json` ;
- `revue_visuelle_objets.json` (verdicts, identifiants d'images, sans photo) ;
- `cartes/carte_site.png`, `carte_coeur.png` et `carte_arret_reviree.png`, sur fond d'ortho PCRS 2022 (GAM, données ouvertes) ;
- `scripts/`.

Fichiers à ne pas versionner : `photos_non_versionnees/`. Ce dossier contient environ 110 vignettes et 7 planches tirées de photos Panoramax et Mapillary sous licence CC-BY-SA 4.0. Les auteurs et les identifiants figurent dans les noms de fichiers et dans `vignettes_index.json`.

Téléchargements : `data/sites/paquet_jardin/avant_travaux/{mapillary_map_features, osm_historique, panoramax_semantique}/`.
