# Sources de l'état d'avant travaux (2021 → 22/06/2025) – carrefour Paquet Jardin, Meylan

Inventaire établi le 11/10/2026. Emprise : carré de ± 150 m autour de O (L93 917279,43 / 6460289,98). Cœur : carré de ± 80 m. Centre : r ≤ 35 m.
Repère local : local = L93 − O, z = NGF − 216,30.
Travaux du carrefour : du 23/06/2025 au 05/12/2025. Trottoirs de l'avenue du Vercors : jusqu'au 30/01/2026. La présentation du 03/04/2025 annonce aussi « avenue du Vercors, par secteurs, d'avril à novembre 2025 ».
Données détaillées : `sources.json`. Scripts reproductibles : `outils/`.

## 0. En bref

1. **Il n'existe pas d'extraction GAM ancienne.** `data/sites/paquet_jardin/vector/gam_topo_sol_*` et `data/sites/paquet_jardin/etat_2026/*` sont la même extraction du 06/10/2026, l'une en WGS84, l'autre reprojetée en L93. Les 7 couches sont identiques : 1 807 objets, mêmes attributs, écart 0,000 m. Le levé « Meylan_Topo.dwg » est une compilation sans date (Z = 0) :
   - hors de la zone des travaux, il coïncide avec le PCRS vecteur 2019. Entre 35 et 80 m, 99 % de la longueur est à moins de 0,30 m (médiane 2,4 cm) ;
   - dans la zone des travaux, il porte la géométrie du projet C1 : seulement 23 % de la longueur des marquages situés entre 35 et 80 m existaient sur l'ortho de 2022.

   **Ce n'est donc pas le levé d'avant travaux.** Il ne vaut qu'en dehors de la zone des travaux.
2. **Pour les bordures avant travaux au cœur, la meilleure source est le PCRS vecteur GAM.** Il a été levé en 2019 (`date_leve` = 2019, Geofit, précision 10 cm), couvre la voirie publique seulement et contient encore l'ancienne bretelle SE et la contre-allée de Verdun SO.
3. **Dates exactes.**
   - PCRS 5 cm : 10/05/2022.
   - BD ORTHO IGN : 21/08/2018, 13/08/2021, 09/08/2024.
   - LiDAR HD sur le site : 12/08/2021 (78 % des points) et 06/09/2021 (22 %).
   - Pléiades 2025 : **date introuvable** (aucune métadonnée publique). Fenêtre estimée entre fin avril et le 22/06/2025.
   - SPOT : scènes du 29/05 et du 17/06/2022, du 19/07 et du 02/09/2023, des 15 et 17/07/2024, et du 25/06/2025.
4. **Photos d'avant travaux, en prises de vue uniques** (Mapillary et Panoramax publient souvent les mêmes images) :

   | Période | Photos uniques | Au centre |
   |---|---|---|
   | 2022 | 64 | 7 |
   | 2023 | 35 | 9 |
   | 2024 | 322 | 10 |
   | 2025, 1er semestre | 36 | 5 |

   Aucune photo de 2021. Le printemps 2025 tient en une seule séquence 360°, celle du 18/05/2025 (Verdun NE → SO). L'avenue du Vercors n'a été photographiée que le 12/01/2025.
5. **OSM au 01/06/2025 obtenu** par Overpass en mode historique (« attic ») : 795 éléments, dont 214 objets dans les couches routières. Depuis, 23 objets ont été supprimés (15 à moins de 80 m du centre), 50 ajoutés et 42 ont changé de géométrie. Parmi les suppressions : la bretelle SE, la bretelle vers Vercors, la contre-allée, le quai La Revirée et 3 feux.

## 1. Tableau chronologique

| Source | Date d'acquisition | Résolution | Couverture du site | Licence | État représenté → usage |
|---|---|---|---|---|---|
| BD ORTHO IGN 2018 | **21/08/2018** (graphe WFS) | 20 cm | 100 % | Etalab 2.0 | 2018 → contexte (hors période) |
| Ortho GAM 2018 | 02/07/2018 (résumé WMS) | 25 cm | 100 % | Licence Ouverte | 2018 → contexte |
| Arrêtés de travaux GAM | 2014 → 06/2022 | — | 16 arrêtés à ± 180 m | Licence Ouverte | réfection de chaussée COLAS en mars–avril 2019 sur Verdun SO et NE → âge des enrobés |
| PCRS vecteur GAM | **2019** (`date_leve`) | 10 cm (plani.), 20 cm (alti.) | voirie publique : 111 bordures, 35 limites de revêtement | Licence Ouverte | 2019, avant les travaux et avant le secteur est → **bordures avant travaux au cœur** |
| LiDAR HD IGN (dalle 0917_6461) | **12/08/2021 (78 %) + 06/09/2021 (22 %)** | ≈ 24 pts/m² | 100 % | Etalab 2.0 | été 2021 → relief, fil d'eau, hauteurs (hors secteur est) |
| BD ORTHO IGN 2021 (et ASP PAC 2022, ortho_gam2021) | **13/08/2021** | 20 cm | 100 % | Etalab 2.0 | été 2021 → contrôle |
| BD TOPO, édition 2022-03-15 | 15/03/2022 (édition) | métrique | 100 % | Etalab 2.0 | 2022 → non téléchargée |
| OSM « attic » | **10/05/2022** | ≈ 1 m | 556 éléments, 150 objets | ODbL | jour du PCRS → topologie 2022 |
| **PCRS image 5 cm GAM** | **10/05/2022** (9 dalles) | 5 cm | 100 % | Licence Ouverte (CRAIG / GAM) | **référence géométrique de l'état 2022** |
| SPOT 6/7 2022 | 29/05 et 17/06/2022 | 1,5 m | 100 % | Etalab 2.0 | trop grossière |
| Mapillary 2022 | 05/03, 10/06 et 03/11/2022 | perspective 2048 px | 64 photos, 7 au centre | CC-BY-SA | aspect en 2022 |
| Panoramax = Mapillary 2023 | 18/03/2023 | perspective | 35 uniques, 9 au centre | CC-BY-SA | aspect en 2023 |
| SPOT 6/7 2023 | 19/07 et 02/09/2023 | 1,5 m | 100 % | Etalab 2.0 | — |
| Canopée GAM (COSIA) | 2018 / 2021 / 2024 | polygones | 98 / 96 / 120 polygones | Licence Ouverte | houppiers avant travaux |
| BD TOPO, édition 2024-03-15 | 15/03/2024 | métrique | 100 % | Etalab 2.0 | non téléchargée |
| Mapillary 2024 | 24/02/2024 | perspective | 232 photos (parkings NO, Revirée) | CC-BY-SA | hors carrefour |
| Panoramax 2024 | 01/05/2024 | 360° | 34 photos, 6 au centre | CC-BY-SA | aspect en 2024 |
| SPOT 6/7 2024 | 15 et 17/07/2024 | 1,5 m | 100 % | Etalab 2.0 | — |
| **BD ORTHO IGN 2024** (IRC, Ortho-express 2024, ASP PAC 2025, CRAIG ortho_2024) | **09/08/2024** | 20 cm | 100 % | Etalab 2.0 | **dernière ortho aérienne avant travaux** (10,5 mois avant), recalée à 4 cm |
| Panoramax = Mapillary 2024 | 24/08/2024 | 360° | 56 uniques (25 dans le secteur est) | CC-BY-SA | secteur est construit |
| Panoramax 2025 | **12/01/2025** | 360° | 12 photos, avenue du Vercors | CC-BY-SA | Vercors en hiver 2025 |
| BD TOPO, édition 2025-03-15 | 15/03/2025 | métrique | 100 % (472 Mo pour le département 38) | Etalab 2.0 | **juste avant travaux** (non téléchargée) |
| Présentation de la réunion publique | 03/04/2025 | — | — | public | planning : Vercors d'avril à novembre 2025, carrefour de juillet à octobre 2025 |
| Panneau du carrefour Verdun/Vercors | 03/04/2025 | plan à 4 cm | carrefour + Verdun SO | public | fond = PCRS 2022 ; délimite la zone transformée |
| **Panoramax = Mapillary 2025** | **18/05/2025** | 360° | 24 photos, 5 au centre, Verdun NE et SO | CC-BY-SA | **seule preuve photo du cœur juste avant travaux** |
| **Pléiades 2025** | non publiée, **fin avril – 22/06/2025 (estimée)** | 50 cm | 100 % | Etalab 2.0 | printemps 2025, sans chantier au cœur |
| **OSM « attic »** | **01/06/2025** et 22/06/2025 | ≈ 1 m | 795 éléments, 214 objets | ODbL | **topologie juste avant travaux** |
| SPOT 6/7 2025 | 25/06/2025 | 1,5 m | 100 % | Etalab 2.0 | 2 jours après le début des travaux |
| PCRS image 5 cm GAM 2025 | juin–juillet 2025 (jour inconnu) | 5 cm | 100 % | **accès restreint** (RTGE, HTTP 401) | à demander à la Métropole |
| Levé topo GAM « Meylan_Topo.dwg » (= `etat_2026`) | **non daté** (extrait le 06/10/2026) | levé de géomètre | site entier | Licence Ouverte | mosaïque de dates → **hors zone des travaux seulement** |

Couches sans donnée sur le site (catalogue IGN / CRAIG du 10/10/2026) :
- ORTHOPHOTOS2022 et 2023 (l'Isère n'a pas été volée ces années-là) ;
- Pléiades 2022, 2023, 2024 et 2026 ;
- Ortho-express 2023, 2025 et 2026 ;
- ASP PAC 2024 et 2026 ;
- THR et PCRS.LAMB93 ;
- CRAIG 2022, 2023 et 2025 (autres départements) ;
- PCRS open data CRAIG : années 2017 à 2024 seulement, sans campagne 2025.

Pour les prises de vue aériennes de l'IGN (`pva:image`), la dernière mission sur le site est P18000282, du 21/08/2018. KartaView n'a aucune photo à moins de 573 m (`docs/SOURCES.md`). Street View est exclu pour raison de licence.

## 2. Couches GAM : nature et date

**Identité des deux jeux.**
- Le script `outils/gam_datation.py` compare les 7 couches communes :
  - bordure_lin 622, bordure_pct 22, arbre_pct 285, caniveau_lin 12 ;
  - limite_revetement_lin 429, signalisation_horizontale_lin 409, signalisation_horizontale_pct 28.

  Les géométries reprojetées sont identiques (écart 0,0 m) et les 1 807 jeux d'attributs aussi.
- Les deux jeux ont été ajoutés le 06/10/2026 :
  - `vector/` par le commit 42ee3af, à 15:08 ;
  - `etat_2026/` par le commit b4a8384, à 16:02 (« géométrie après travaux, levés topo Métropole »).
- Le WFS geoflux, ré-interrogé le 11/10/2026 (`gam_wfs_2026-10-11_vs_etat_2026.json`), redonne 98,6 % des bordures, 97,1 % des marquages linéaires et 100 % des symboles à moins de 5 cm. Il sert chaque objet environ 4 fois sous des identifiants différents.

**Attributs.** Le levé topo ne porte aucune date : calque, répertoire `/sigdata/Planotheque/esp_publics/MEYLAN/PLAN_GLOBAL/`, fichier `Meylan_Topo.dwg`, type_geom, Z = 0. Le résumé du WFS indique que ces données sont « issues des relevés de géomètres, … pas nécessairement à jour ». Le PCRS vecteur, lui, porte `date_leve` = 2019-01-01 (100 % des objets), producteur Geofit, précision 10 / 20 cm.

**Comparaison géométrique** (zone des travaux approchée : disque de 40 m, plus Verdun SO de u = −115 à 0 m avec |v| ≤ 22 m, plus l'avenue du Vercors à ≤ 14 m de son axe) :

| Indicateur | Hors travaux 35–80 m | Hors travaux 80–150 m | Zone travaux r ≤ 35 m | Zone travaux 35–80 m |
|---|---|---|---|---|
| Marquages du levé visibles sur l'ortho 2022 (part de la longueur) | 74 % | 64 % | 70 % | **23 %** |
| PCRS 2019 à ≤ 0,30 m d'une bordure du levé, là où les deux existent | **99 %** (médiane 2,4 cm) | 64 % (médiane 15 cm ; 22 cm au SO) | 72 % (5 cm) | 54 % (25 cm) |

Les cartes `cartes/gam_topo_vs_pcrs2019_coeur.png` et `cartes/gam_topo_vs_pcrs2019_site.png` font apparaître trois cas :
- **NO, Revirée et Verdun NE** : le levé et le PCRS 2019 se superposent.
- **Coin SE** : le PCRS dessine l'ancienne bretelle vers Vercors, le levé la nouvelle bordure et le nez d'îlot.
- **Verdun SO** : le PCRS dessine la contre-allée et les anciens quais, le levé le terre-plein, le refuge et les zébras déplacés d'environ 9 m.

Dans le **secteur est**, le levé contient les voies et les bâtiments construits en 2023–2024, absents du PCRS 2019 et en chantier sur l'ortho 2022. Le levé a donc été mis à jour par morceaux.

**Conclusion.** L'extraction du dépôt n'est **pas** le levé d'avant travaux, et aucune version historique n'est publiée :
- le WFS ne propose aucune couche datée (142 types d'objets listés, `donnees_referentielles_topo` sans date) ;
- les couches `d_ref_pcrs_voiries`, `d_ref_pcrs_vecteur` et `app-sygetrack` sont identiques (111 objets, 2019).

Pour l'état d'avant travaux, il faut :
- au cœur, s'appuyer sur le PCRS vecteur 2019, le PCRS image 2022, l'IGN 2024 et les photos de 2025 ;
- ailleurs, garder le levé topo, qui coïncide avec 2019–2022.

## 3. Orthophotographies 2018 → juin 2025

Les dates ont été vérifiées le 11/10/2026 :
- **BD ORTHO** : par les graphes de mosaïquage du WFS IGN (`ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2016-2020`, `GRAPHE.2021-2023`, `GRAPHE-MOSAIQUAGE`) interrogés en 9 points du site (centre, NO, NE, SO, SE, est, ouest, nord, sud) : 21/08/2018, 13/08/2021 et 09/08/2024 partout.
- **PCRS 2022** : par l'index des dalles CRAIG.
- **SPOT** : par le catalogue STAC DINAMIS (`https://api.stac.teledetection.fr`, collection `dinamis-openspot-6-7`), qui donne les scènes couvrant le carrefour. La scène retenue dans chaque mosaïque IGN n'est pas publiée.

**Pléiades 2025, date de prise de vue : non trouvée.** Sources interrogées sans résultat :
- la couche WMS `ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025` n'est pas interrogeable (`LayerNotQueryable`) ;
- le WFS IGN ne contient aucun graphe de mosaïquage Pléiades (seulement SPOT 2014–2017) ;
- la fiche CSW `IGNF_ORTHO-SAT` ne donne que des dates de publication (2010–2026) ;
- la fiche data.gouv « ORTHO SAT » ne date pas les images ;
- le STAC DINAMIS public ne contient que SPOT.

Estimation :
- feuillage complet, donc après la fin avril ;
- au cœur, zébras, îlots et kiosque de 2024 toujours en place, sans emprise de chantier, donc avant le chantier du carrefour (23/06/2025) ;
- secteur est achevé.

Fenêtre retenue : **fin avril – 22/06/2025**.

La mesure des ombres n'a pas abouti. Les toits sont déversés de 3 à 7 m, et l'ombre portée se confond avec les façades à 0,5 m de résolution. L'azimut apparent (environ 347°) est incompatible avec un passage vers 10 h 15 – 10 h 30 TU.

## 4. LiDAR HD : dates exactes

Le site entier tient dans une seule dalle, `LHD_FXX_0917_6461` (mission 21LHD6PM, Sintegra, deux RIEGL VQ-780 II-S, 24 199 488 points, édition du 25/03/2025). Le WFS la date du 12/08/2021 au 06/09/2021.

Le temps GPS des points du site a été lu avec le PDAL de QGIS (`outils/lidar_dates.py`, 1 point sur 5 dans le carré de ± 150 m). Le temps est en « adjusted standard » (bit non positionné dans l'en-tête ; UTC = GPS − 18 s).

| Jour | Lignes de vol | Heures (TU) | Part du site | Part du cœur ± 80 m | Part du sol (classe 2) |
|---|---|---|---|---|---|
| **12/08/2021** | 7208, 7209, 7210, 7211 | 12:03 – 12:17 | 77,9 % | 77,7 % | 74,5 % |
| **06/09/2021** | 7020 | 05:11 – 05:12 | 21,8 % | 22,1 % | 24,9 % |
| aberrants | 12, 13, 60, 63, 78 | (2011 / 2019) | 0,3 % | 0,3 % | 0,6 % |

L'en-tête COPC donne gpstime_max = 06/09/2021 05:12 TU (gpstime_min n'est pas renseigné). Le LiDAR est antérieur au secteur est construit en 2023–2024.

## 5. Photos de rue (Panoramax + Mapillary)

Les comptages couvrent toutes les photos disponibles, posées ou non :
- Panoramax : 246 photos dans l'emprise, toutes dates confondues (STAC `api.panoramax.xyz`, interrogé le 11/10/2026, `data/sites/paquet_jardin/avant_travaux/panoramax/search_site_tout.json`) ;
- Mapillary : 1 867 photos (inventaire du 10/10/2026, `data/raw/mapillary/paquet_jardin/images.json`, sous la limite de 2 000).

Une photo Mapillary compte comme **doublon** d'une photo Panoramax quand elle est prise à ±3 s (à un nombre entier d'heures près, pour absorber le fuseau horaire) et à ≤ 15 m. Doublons trouvés :
- 18/03/2023 : 33 photos, décalage de +1 h ;
- 24/08/2024 : 57 ;
- 18/05/2025 : 24 ;
- 21/05/2020 : 36.

Secteurs :
- **centre** : r ≤ 35 m ;
- **branche** : axe OSM (Verdun NE / SO, Revirée, Vercors) à ≤ 15 m ;
- **est** : azimut 60–150°, voies nouvelles ;
- **autre** : parkings et dessertes.

« Voient le centre » : photo 360° à ≤ 100 m, ou perspective à ≤ 120 m orientée vers O à ± 40°.

Prises de vue uniques dans l'emprise :

| Période | Photos (Panoramax / Mapillary) | **Uniques** | Centre | Verdun NE | Verdun SO | Vercors | Revirée | Est | Autre | Cœur ± 80 m | Voient le centre | Posées (acceptées) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017–2021 | 1 442 (36 / 1 406) | 1 406 | 215 | 358 | 413 | 308 | 40 | 0 | 72 | 731 | 504 | 179 (0) |
| **2022** | 64 (0 / 64) | **64** | 7 | 12 | 18 | 11 | 8 | 0 | 8 | 28 | 27 | 44 (0) |
| **2023** | 68 (34 / 34) | **35** | 9 | 12 | 14 | 0 | 0 | 0 | 0 | 20 | 12 | 28 (0) |
| **2024** | 379 (90 / 289) | **322** | 10 | 23 | 13 | 7 | 19 | 25 | 225 | 75 | 45 | 142 (36) |
| **2025-S1** (≤ 22/06) | 60 (36 / 24) | **36** | 5 | 10 | 9 | 12 | 0 | 0 | 0 | 21 | 22 | 34 (22) |
| après le 23/06/2025 | 50 (50 / 0) | 50 | 13 | 14 | 16 | 0 | 0 | 0 | 7 | 29 | 21 | 35 (0) |

Par mois (avant travaux), toutes photos confondues :
- **2022** : 03 → 11 ; 06 → 37 ; 11 → 16.
- **2023** : 03 → 34 + 34.
- **2024** : 02 → 232 ; 05 → 34 ; 08 → 56 + 57.
- **2025** : 01 → 12 ; 05 → 24 + 24.
- **Aucune photo en 2021**, ni entre 12/2022 et 02/2023, ni entre 09/2024 et 12/2024, ni en juin 2025.

Séquences et contenus utiles :
- **2022-06-10** (37 photos, perspective) : Verdun NE → centre → Verdun SO. C'est la photo la plus proche du PCRS 2022 (un mois après).
- **2022-03-05** : avenue du Vercors.
- **2023-03-18** : Verdun NE → SO.
- **2024-05-01** : 360°, Verdun et centre.
- **2024-08-24** : 360°, Verdun, secteur est et Vercors.
- **2025-01-12** : 360°, avenue du Vercors (les immeubles de l'est sont achevés, les palissades de chantier encore là).
- **2025-05-18** : 360°, Verdun NE → SO. On y voit l'état d'avant travaux du centre : zébras, ancienne traversée cyclable, bandes podotactiles jaunes, îlots. Vérifié sur la vue `photos_non_versionnees/centre_2025-05-18_bande.jpg`, non versionnée.

**Lacunes.**
- La Revirée n'a, depuis 2022, que 27 photos prises en bordure de la branche : 8 à l'extrémité NO en 11/2022, et 19 sur l'accès au parking, entre 55 et 80 m du centre, en 02/2024. Aucune ne remonte la branche.
- Le Vercors n'a pas de photo après le 12/01/2025.
- Le centre n'a que 5 photos au printemps 2025, toutes prises depuis la même voie, dans le sens NE → SO.

Cartes (positions seulement, sur fond PCRS 2022) :
- `cartes/couverture_photos_2017-2021.png`, `_2022.png`, `_2023.png`, `_2024.png`, `_2025-S1.png`, `_apres_debut_travaux.png` ;
- la planche `cartes/couverture_photos_synthese.png` ;
- l'histogramme `cartes/photos_par_mois.png`.

Le détail par photo (identifiant, date, x, y, secteur, doublon, pose) est dans `photos_inventaire.json`.

## 6. OSM historique (Overpass, mode « attic »)

Requête : `[out:json][timeout:300][date:"…"];(nwr(45.206347,5.766223,45.208953,5.770177););out meta geom;` sur `https://overpass-api.de/api/interpreter`, base du 11/10/2026.

Téléchargements :
- `data/sites/paquet_jardin/avant_travaux/osm_2025-06-01/overpass_2025-06-01T00Z.json` (795 éléments) ;
- `…/osm_2025-06-01/overpass_2025-06-22T22Z.json` (810) ;
- `…/osm_2022-05-10/overpass_2022-05-10T00Z.json` (556) ;
- `…/osm_actuel_2026-10-11/overpass_actuel.json` (872).

Les couches au 01/06/2025, découpées comme `pipeline/osm.py`, sont dans `osm_2025-06-01/osm_*.geojson`. Comparaisons détaillées : `osm_comparaison.json`. Carte : `cartes/osm_2025-06-01_vs_actuel.png`.

Évolution des objets tagués dans l'emprise :

| Comparaison | Objets avant → après | Supprimés (≤ 80 m) | Ajoutés (≤ 80 m) | Géométrie modifiée > 0,5 m (≤ 80 m) | Tags modifiés |
|---|---|---|---|---|---|
| 10/05/2022 → 01/06/2025 | 150 → 214 | 3 (0) | 67 (17) | 12 (9) | 92 |
| 01/06/2025 → 22/06/2025 | 214 → 220 | 0 | 6 lampadaires | 1 | 7 |
| 01/06/2025 → actuel (11/10/2026) | 214 → 241 | **23 (15)** | **50 (25)** | **42 (27)** | 75 |

**Supprimés par les travaux** :
- voies : way 168730949 (voie SE de Verdun, à sens unique), way 312004805 (bretelle vers Vercors), way 4247835 (tronçon du Vercors), way 185326637 (contre-allée), parking 156705516 ;
- arrêt La Revirée : quai 185326912, poteau 6569621813, arrêt 514050473 ;
- feux : traversées à feux 1722505401 et 6569621810, feu 1959011179 ;
- trottoirs 699599898, 759539696 et 1311524320.

Entre 2022 et 2025, OSM a surtout été **enrichi** : 137 des 214 objets du 01/06/2025 ont leur dernière version entre août 2024 et mai 2025.

Comparé aux couches du dépôt (`data/sites/paquet_jardin/vector/osm_*`, extraites en octobre 2026), l'état au 01/06/2025 diffère, par exemple :

| Couche | Dépôt | 01/06/2025 | Seulement dans le dépôt | Seulement au 01/06/2025 |
|---|---|---|---|---|
| roads | 49 | 46 | 14 | 11 |
| footways | 46 | 35 | 16 | 5 |
| parking | 49 | 42 | 17 | 10 |
| street_lamps | 39 | 28 | 11 | 0 |
| traffic_signals | 14 | 17 | 0 | 3 |
| public_transport | 7 | 7 | 3 | 3 |

**Les couches `osm_*` du dépôt décrivent donc l'état après travaux.** Pour l'état avant travaux, il faut prendre `osm_2025-06-01/`.

Les dates des géométries modifiées sont des dates de version des voies (way). Un déplacement de nœud ne change pas la version de la voie.

## 7. Documents publics

- **Panneau « Aménagement carrefour Verdun/Vercors »** (PDF du 03/04/2025, meylan.fr). Le fond est l'ortho PCRS 2022, donc l'état existant ; le dessin, le projet. Il est déjà géoréférencé (`data/sites/paquet_jardin/plan_projet_2025`, RMSE 3 cm).
- **Présentation de la réunion publique du 03/04/2025.**
  - Planning : avenue du Vercors par secteurs d'avril à novembre 2025 ; carrefour Verdun/Vercors de juillet à octobre 2025.
  - Bilan avant / après de la phase 2 : chaussée et îlots bitumés passent de 7 350 à 6 130 m², les surfaces végétalisées de 1 700 à 2 400 m².
  - **Attention** : sur l'avenue du Vercors, l'« avant travaux » peut s'arrêter dès avril 2025. Aucune photo n'en témoigne : la dernière date du 12/01/2025.
- **Présentation du 14/05/2024.** Historique : décision de décembre 2022, études en 2023, carrefour prévu à l'été 2025. Sa « situation existante » porte sur Granier/Taillefer, pas sur notre carrefour.
- **Magazines Meylan ma ville** n° 164 (juin 2025) et 165 (octobre 2025, p. 12) : description du projet seulement.
- **Arrêtés de travaux GAM** (open data arrêté en juin 2022) : réfection de chaussée COLAS en mars–avril 2019 à (−54, −53) et (44, 37) ; réseaux ENEDIS, GRDF et eau de 2019 à 2022.
- **Non trouvés en ligne** : les dossiers de concertation (préalable de mars–avril 2022, réglementaire de novembre 2023 à mars 2024), qui contiendraient des plans de l'existant, et le plan de récolement. Ils sont à demander à la SMMAG ou à la Métropole.

## 8. Conclusion : quelle source pour quel état

**État « juste avant travaux » (printemps 2025)**

| Thème | Sources |
|---|---|
| Géométrie au sol du cœur | Aucune source directe à moins de 5 cm. Base : PCRS vecteur 2019 (bordures) + PCRS image 2022 (marquages, revêtements). Contrôle de non-changement : BD ORTHO 2024-08-09 (20 cm) puis Pléiades 2025 (50 cm). |
| Aspect au cœur | Photos du 18/05/2025 (24 vues 360°, dont 5 au centre). |
| Aspect sur le Vercors | Photos du 12/01/2025 (12 vues 360°). |
| Topologie, arrêts, feux, traversées | OSM au 01/06/2025, ou au 22/06/2025. |
| Hors zone des travaux | Levé topo GAM (concorde avec 2019–2022) et secteur est tel que construit : IGN 2024, Pléiades 2025, OSM 2025-06. |

**État 2022**

| Thème | Sources |
|---|---|
| Géométrie | PCRS image 5 cm du 10/05/2022 + PCRS vecteur 2019 + LiDAR HD (12/08 et 06/09/2021) pour le relief et la hauteur des bordures. |
| Topologie | OSM au 10/05/2022. |
| Aspect | Mapillary du 10/06/2022 (37 photos, dont 7 au centre) et du 05/03/2022 (Vercors). Le 18/03/2023 (35) comme complément proche. |
| Contrôle | BD ORTHO 2021-08-13. |

Le secteur est est alors en chantier.

**Entre 2022 et juin 2025**, le cœur change peu sur les orthos (`carte_changements_2022_2024.jpg`) : seul le secteur est se transforme. L'état 2022 sert donc de base géométrique à l'état du printemps 2025, en mettant à jour le secteur est et l'aspect (usure, végétation) à partir des photos de 2024 et 2025.

## 9. Recommandations

1. Demander à la Métropole ou au CRAIG (convention PCRS) l'**ortho PCRS 5 cm de 2025** et son jour de vol. S'il précède le 23/06/2025, c'est la source idéale. Demander aussi les **plans de l'existant ou les levés d'avant projet** du marché C1, et l'historique du fichier `Meylan_Topo.dwg`.
2. Télécharger la **BD TOPO 2025-03-15** (département 38, 472 Mo) pour figer les tronçons, bâtiments et haies juste avant travaux.
3. Poser en priorité les **24 vues 360° du 18/05/2025** et les **12 du 12/01/2025** : aujourd'hui, 8 vues Panoramax de 2025 sur 36 ont une pose acceptée. Poser aussi les 37 photos Mapillary du 10/06/2022 : 32 n'ont qu'une pose a priori, aucune n'a de pose acceptée.
4. Recaler la Pléiades 2025 (c'est déjà fait : +0,47 / +1,17 m) et ne l'employer qu'en contrôle de présence ou d'absence.
5. Pour les branches que les travaux n'ont pas touchées (Revirée au-delà d'environ 40 m, Verdun NE au-delà du passage), une prise de vue de terrain actuelle documenterait l'aspect, inchangé depuis 2022–2025. La dernière séquence qui remonte la Revirée date du 19/02/2020 (Mapillary).

## Fichiers produits

- Racine `recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources/` :
  - `SOURCES.md`, `sources.json` (27 sources) ;
  - `gam_datation.json`, `gam_wfs_2026-10-11_vs_etat_2026.json` ;
  - `lidar_dates.json`, `photos_inventaire.json`, `osm_comparaison.json`, `osm_2025-06-01/osm_*.geojson`.
- `cartes/` :
  - `couverture_photos_*.png` (6 périodes), `couverture_photos_synthese.png`, `photos_par_mois.png` ;
  - `gam_topo_vs_pcrs2019_coeur.png`, `gam_topo_vs_pcrs2019_site.png` ;
  - `osm_2025-06-01_vs_actuel.png`.
- `outils/` : `inventaire_photos.py`, `osm_historique.py`, `gam_datation.py`, `gam_wfs_reextraction.py`, `lidar_dates.py`, `construire_sources.py`, `compacter_cartes.py` (palette fixe des PNG).
- `photos_non_versionnees/` : deux bandes de contrôle tirées de photos Panoramax (ne pas versionner).
- Téléchargements, dans `data/sites/paquet_jardin/avant_travaux/` :
  - `lidar_hd/` (COPC de 151 Mo et en-tête, avec un `.gitignore`) ;
  - `gam_geoflux_2026-10-11/` (topo, PCRS, canopée) ;
  - `panoramax/search_site_tout.json` ;
  - `osm_2022-05-10/`, `osm_2025-06-01/`, `osm_actuel_2026-10-11/`.

## Sources consultées (URL)

- WFS IGN : https://data.geopf.fr/wfs/ows. Couches `ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho`, `ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2016-2020:graphe_bdortho`, `ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2021-2023:graphe_bdortho`, `IGNF_LIDAR-HD_METADONNEE:metadata`, `pva:dataset`, `pva:image`, `GRAPHE.PCRS.ANCT:graphe_pcrs_anct`, `BDTOPO_V3_DIFF:*`.
- WMS IGN : https://data.geopf.fr/wms-r (GetCapabilities ; GetFeatureInfo sur Pléiades 2025). CSW : https://data.geopf.fr/csw (`IGNF_ORTHO-SAT`).
- LiDAR HD : https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_PM_2025-03-25/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz
- BD TOPO : https://data.geopf.fr/telechargement/resource/BDTOPO
- data.gouv ORTHO SAT : https://www.data.gouv.fr/datasets/ortho-sat
- STAC DINAMIS / Maison de la Télédétection : https://api.stac.teledetection.fr (collection `dinamis-openspot-6-7`). Webinaire DINAMIS 2026 : https://theia.sedoo.fr/wp-content-theia/uploads/sites/6/2026/05/WEBINAIRE-7-Mai-LL.pdf
- WFS GAM geoflux : https://geoflux.grenoblealpesmetropole.fr/geoserver/wfs (GetCapabilities : 142 types d'objets)
- WebDAV CRAIG PCRS : https://drive.opendata.craig.fr/public.php/webdav/ortho/PCRS_5cm/
- Panoramax : https://api.panoramax.xyz/api/search. Mapillary : https://graph.mapillary.com (inventaire existant)
- Overpass : https://overpass-api.de/api/interpreter
- Documents : https://www.meylan.fr (copies dans `data/raw/docs_web/meylan_fr/`)
