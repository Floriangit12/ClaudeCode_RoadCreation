# Plan de reconstruction de l'état d'avant travaux : carrefour « Paquet Jardin », Meylan

Rédigé le 11/10/2026 à partir des sept inventaires de ce dossier : `sources/`, `changements/`, `audit/`, `marquages/`, `sol/`, `objets/` et `qualite/`. Les chiffres clés ont été recontrôlés dans leurs JSON (voir l'annexe A).

Statut : **proposition**. Aucun module du pipeline n'est encore modifié. Aucun fichier existant du dépôt n'a été touché pour écrire ce plan.

Conventions :
- repère local = L93 − (917279,43 ; 6460289,98), z = NGF − 216,30 ;
- UE : X = 100·x, Y = −100·y, Z = 100·z ;
- les « j-agent » sont des jours de travail d'un agent ;
- les références `fichier:ligne` du § 3 renvoient à l'instantané du code du 11/10/2026 à 08:32 (`audit/instantane_code_sha1.txt`). L'autre workflow modifie le code en parallèle et les lignes peuvent bouger.

---

## 0. En bref

1. **Date cible : le 18/05/2025, veille des travaux** (`date_etat` 2025-05).
   - Ce jour-là a lieu la dernière séance photo du carrefour avant le chantier (23/06/2025 → 05/12/2025).
   - La scène est stable du 24/08/2024 au 22/06/2025.
   - Toutes les poses calées du dépôt datent de cette période : 45 vues distinctes, du 24/08/2024 et du 18/05/2025.
   - Sur l'avenue du Vercors, au-delà de l'entrée du carrefour, on retient l'état du 12/01/2025, marqué incertain : des travaux y étaient annoncés dès avril 2025, sans qu'aucune photo ne le confirme.
2. **Le levé GAM n'est pas un état d'avant travaux.** `vector/gam_topo_sol_*` et `etat_2026/*` sont une même extraction du 06/10/2026 : 1 807 objets, écart 0,000 m, attributs identiques. `Meylan_Topo.dwg` est un plan vivant, mis à jour par morceaux et sans date par objet.
   - Il n'entre dans la description qu'**après datation tronçon par tronçon**. Sur 7 005 m de bordures : 44,6 % de relief en 2021, 13,2 % arasées visibles en 2022, 6,0 % apparues de 2022 à 2024, 4,7 % absentes avant 08/2024 (7,2 % au cœur).
   - Côté marquages, il ne sert que de contrôle, là où il coïncide avec 2022 : 44 % de la longueur.
3. **La géométrie de référence est mesurée, pas déduite :**
   - ortho PCRS 5 cm du 10/05/2022 pour les marquages (1 à 3 cm) et les contours (p50 4,7 cm) ;
   - PCRS vecteur 2019 et LiDAR HD 2021 pour les bordures et le relief. Le nuage COPC de 151 Mo est **déjà téléchargé**, et PDAL 2.8.2 est disponible dans QGIS ;
   - BD ORTHO IGN du 09/08/2024 et photos 2024-2025 pour ce qui a changé entre 2022 et 2025.
4. **Ce qui a changé entre 2022 et 2025 tient en 21 entités datées**, réunies dans `changements_2022_2025.geojson`.
   - La géométrie de 2022 n'est plus valable sur 26,6 % de l'emprise de 300 m, surtout dans le quartier est construit en 2023-2024.
   - Au cœur (r ≤ 40 m), elle reste valable sur 91 % de la surface. Seuls l'aspect de la chaussée (reprises d'enrobé 2024, 18 %) et les marquages de l'approche NE (10 %) y ont changé.
   - Ces entités, augmentées des travaux de 2025, forment la **table d'événements** qui règle toute la chronologie (§ 2.1).
5. **Les sources « 2026 » sont à exclure dans l'emprise des travaux** : `etat_2026`, plan projet 2025, OSM actuel, MNT « octobre 2026 », paquet v1, `.xodr` 2026.
   - Remplaçants déjà disponibles : OSM au 01/06/2025 et au 20/06/2025, 759 objets d'avant travaux, pilotes de marquages et de sol.
   - Restent à produire : le MNT 2021 en flottant, le `.xodr` d'avant travaux et le masque de chaussée.
6. **Le pipeline devient paramétrable par un `etat_cible`**, chargé par la variable `PJ_ETAT`.
   - Une seule fonction de validité temporelle, fondée sur la table d'événements, remplace les 11 constantes de travaux réparties dans 9 fichiers.
   - Les sorties vont dans `recon/out/paquet_jardin/v2_avant_travaux/`, et l'état 2026 reste dans `v2/`.
   - Réutilisables tels quels : les 10 HDA `pj_*`, les poses (65 Panoramax, 400 Mapillary), le solveur de cohérence et la régularisation G1.
7. **Les six causes du « super mal fait » sont corrigées dès le départ**, pas après coup :
   - une seule époque, avec sources datées ;
   - matériaux MaterialX texturés (aujourd'hui 0 sur 51) ;
   - contexte composé : bâtiments, arbres, 11 supports de feux, panneaux FR ;
   - sol en partition topologique, Z de conception calé sur le LiDAR, sans flou ni retrait de triangles ;
   - import UE complet, sans v1 ;
   - validation **par l'image** : au moins 30 vues calées, planches photo / rendu, revue en aveugle.
8. **Le travail se fait en 8 phases**, avec des critères chiffrés (§ 4.2 et § 5). L'effort est estimé à **31 à 47 j-agent**, dont 20 à 30 sur le chemin critique. Les données d'avant travaux (phase 1) et la piste qualité indépendante de la date peuvent démarrer **tout de suite**, sans toucher au code de l'autre workflow.
9. **Trois questions à l'utilisateur** (§ 6.2) :
   - confirmer la date cible ;
   - garder ou geler l'état 2026 ;
   - demander à la Métropole l'ortho PCRS 5 cm de 2025.

---

## 1. Date cible

### 1.1 Recommandation

| Paramètre | Valeur |
|---|---|
| `date_cible` T | **2025-05-18** (séance Panoramax et Mapillary 360°, de 13 h 38 à 13 h 45 UTC) |
| `date_etat` | 2025-05 |
| Fenêtre des preuves contemporaines | du 24/08/2024 au 22/06/2025 (aucun changement au cœur ni sur Verdun pendant cette période, sauf CHG-006, 007 et 021) |
| Preuves plus anciennes (2019-2023) | admises partout où aucun événement ne les sépare de T (§ 2.1) : PCRS 2022, PCRS 2019 et LiDAR 2021 valent au cœur |
| Avenue du Vercors au-delà de l'entrée | état du 12/01/2025 (12 vues 360°), marqué `incertain` (CHG-019) |
| Saison et soleil du niveau | mi-mai, plein feuillage, aucune feuille morte ; soleil du 18/05/2025 (235,2° / 53,5° à 13 h 38 UTC) pour les vues de validation |

### 1.2 Preuves disponibles par période (chiffres réconciliés)

| Période | Orthos | Vecteurs / relief | Photos uniques (dont centre r ≤ 35 m) | Vues calées acceptées (distinctes) | OSM historique | Stabilité de la scène |
|---|---|---|---|---|---|---|
| 2021 | BD ORTHO 13/08/2021 (20 cm) | LiDAR HD : 12/08/2021 (77,9 % des points), 06/09/2021 (21,8 %) | 0 | 0 | — | secteur est avant construction |
| **2022** | **PCRS 5 cm du 10/05/2022** ; SPOT 29/05 et 17/06 | PCRS vecteur 2019 (Geofit, 10 cm) | 64 (7) : Mapillary 05/03, 10/06 et 03/11 | **0** (44 poses a priori) | 10/05/2022 : 150 objets | **secteur est en gros œuvre** (grue, base vie) |
| 2023 | SPOT 19/07 et 02/09 (1,5 m) | — | 35 (9) : 18/03/2023 | 0 (28 a priori) | 01/06/2023 | immeubles est en élévation |
| **2024** | **BD ORTHO 09/08/2024 (RVB et IRC, 20 cm, recalée à 4 cm)** ; SPOT juillet | canopée COSIA 2024 | 322 (10), dont 225 dans les parkings (24/02) | **31** (24/08/2024 : 5 Panoramax et 26 Mapillary) | 01/06/2024 | quartier est livré ; reprises d'enrobé au cœur (chantier de tranchées vu le 01/05/2024) |
| **2025, 1er semestre** | Pléiades 2025 (50 cm, date non publiée, estimée entre fin avril et le 22/06) | BD TOPO 2025-03-15 (non téléchargée) | 36 (5) : 12/01 (Vercors) et 18/05 (Verdun NE → SO) | **14** (18/05/2025 : 8 Panoramax et 6 Mapillary) | **01/06/2025 : 214 objets** ; 20/06 et 22/06/2025 | aucun chantier visible au cœur le 18/05/2025 |
| après le 23/06/2025 | SPOT 25/06/2025 | levé GAM (mosaïque datée jusqu'à 2025-2026) | 50 | 0 | actuel | travaux : **exclu** |

Les 58 « poses calées » des rapports `changements` et `sources` comptent deux fois 13 prises : chaque prise Panoramax acceptée a aussi sa copie Mapillary (`calee_panoramax`). Cela fait **45 vues distinctes**, dont **20 à moins de 80 m du centre** (contrôle sur `poses.json` et `poses_mapillary.json`, annexe A).

### 1.3 Pourquoi le 18/05/2025

- **(a) Preuves.**
  - 100 % des poses calées du dépôt sont de 2024-2025 ; aucune n'est de 2022-2023.
  - 1 392 des 1 475 observations du recensement (94,4 %) sont datées entre le 01/01/2022 et le 22/06/2025. Avec T = 18/05/2025, les 746 observations de 2024 et 2025-S1 deviennent contemporaines.
  - La couverture stricte du cœur passerait de 9,0 % à au plus 22,6 % par simple re-datation, avant tout nouveau calage.
  - Objets : 85,3 % des objets du cœur (hors arbres et clôtures) sont vus sur au moins 2 photos calées.
- **(b) Stabilité.**
  - Entre le 24/08/2024 et le 18/05/2025, ne changent que :
    - les abords SE de Verdun NE (clôtures et bungalows remplacés par des haies et des parkings, CHG-006 et 007) ;
    - les cœurs d'îlot du quartier est (CHG-021).
  - Chaussée, bordures, îlots, zébras et marquages du cœur sont identiques sur les photos calées des deux dates.
  - Les 11 passages du cœur sont restés à la même place de 2022 à 2024 : décalage de 0 à 5 cm pour 9 d'entre eux, ≤ 0,18 m pour tous.
  - En mai 2022, au contraire, le quartier est était un chantier actif qu'aucune source ne décrit en 3D.
- **(c) Intérêt ADAS.** C'est la configuration d'avant le projet C1. Elle comprend :
  - la bretelle de tourne-à-droite SE vers le Vercors, avec son îlot, et la contre-allée de Verdun SO ;
  - les quais La Revirée d'origine ;
  - 11 supports de feux et deux traversées à feux, supprimés en 2025 ;
  - les îlots en galets ;
  - les pavés Chronovélo de 2022 ;
  - le quartier est livré, avec une branche nouvelle et un STOP (Mitaillères).

  La scène est validable à chaque pose calée : on compare des photos du même état.

### 1.4 Alternatives et leur coût

| Variante | Ce qui change | Coût par rapport au 18/05/2025 |
|---|---|---|
| **24/08/2024** (ortho IGN à 15 jours) | CHG-006 et 007 : clôtures et bungalows le long de Verdun NE au lieu des haies et parkings ; CHG-021 en terre nue ; STOP des Mitaillères non attesté (vu le 12/01/2025) | ≈ 0 j-agent. Perd la contemporanéité des 14 vues du 18/05/2025 dans les zones CHG-006 et 007 seulement. Équivalente ailleurs. |
| **10/05/2022** (jour du PCRS) | Quartier est en chantier (grue, terre nue, base vie) ; marquages de Verdun NE de 2022 (CHG-008) ; arbres CHG-013 à 016 présents | **+4 à 7 j-agent** : il faut modéliser un chantier sans source 3D, retirer les 6 % de traits GAM apparus en 2022-2024 et caler les photos de 2022 (aucune pose acceptée aujourd'hui). Les photos de 2024-2025 ne valent plus hors du cœur. La validation par l'image est faible : 7 photos au centre, aucune calée. **Déconseillé.** |

---

## 2. Sources retenues par famille et règles de chronologie

### 2.1 Règle unique : la table d'événements

Une observation datée d, au point p, pour une famille f (géométrie, marquage, texture, objet, végétation, apparence), vaut pour T si **aucun événement E** ne remplit les trois conditions suivantes :
- E touche f ;
- l'emprise de E, marge comprise, contient p ;
- l'intervalle [date_min ; date_max] de E chevauche [min(d, T) ; max(d, T)].

Deux cas particuliers :
- **incertain** : p est à moins de `marge_m` du bord de l'emprise, ou T tombe dans l'intervalle d'un événement non observé ;
- **non valable** : d tombe pendant un événement qui touche p.

Pour arbitrer, **la preuve valable la plus proche de T** l'emporte. Ce modèle généralise celui de `gcp.py` (`valide_de` / `valide_a`) et remplace :
- `valide_2026`, FUS-DATE-01 et 02 ;
- `apres_travaux()`, `anterieure_travaux()` ;
- `TRANCHES_PROBANTES`.

Nouveauté par rapport à la proposition de l'audit : **chaque événement déclare les familles qu'il touche**. Par exemple, une reprise d'enrobé (CHG-009) invalide la texture de 2022, mais pas la géométrie des bordures ni des marquages.

| Id | Nature | date_min → date_max | Emprise (repère local) | Familles touchées | Effet pour T = 18/05/2025 |
|---|---|---|---|---|---|
| CHG-001 / 002 (CONSTR-EST) | quartier est : 11 bâtiments, voies, parkings, parc | 10/05/2022 → 09/08/2024 | x 37..156, y −67..92, plus ≈ 21 000 m² extérieurs (`changements_2022_2025.geojson`) | toutes | PCRS 2022, PCRS 2019 et LiDAR 2021 non valables ; IGN 2024, photos 2024-2025, BD TOPO 2025 et GAM daté valables |
| CHG-003 | carrefour Vercors / Mitaillères : branche, îlot, STOP | 10/05/2022 → 09/08/2024 (STOP vu le 12/01/2025) | x 18..78, y −143..−112 | géométrie, marquage, objet | idem |
| CHG-004 | rive est du Vercors : bordure, trottoir, allée | 10/05/2022 → 09/08/2024 | x 22..40, y −62..−33 | géométrie | IGN 2024 et photos du 12/01/2025 ; **pas le GAM** (trottoirs refaits jusqu'au 30/01/2026) |
| CHG-005 | base vie bleue SE | → 09/08/2024 | x 16..31, y −33..−17 | objet | présente à T |
| CHG-006 / 007 | abords SE de Verdun NE, nouvel accès riverain | 24/08/2024 → 18/05/2025 | bande de 3 à 24 m, x 20..125 | géométrie des abords, objet, végétation | seules valent les preuves du 18/05/2025 et la Pléiades |
| CHG-008 | marquages de l'approche NE de Verdun (zone hachurée) | 18/03/2023 → 09/08/2024 | x 1..66, y −1..66 | **marquage** | PCRS 2022 non valable pour les marquages ; bordures valables |
| CHG-009 | reprises d'enrobé au cœur (réseau de chaleur, chantier vu le 01/05/2024) | 18/03/2023 → 09/08/2024 | x −16..10, y −12..18, plus la voie SO | **texture** | géométrie 2022 valable ; aspect d'après IGN 2024 et photos 2024-2025 |
| CHG-010 / 011 | tranchées refermées : Verdun SO (3,5 × 120 m), Revirée (2,5 m) | 2022 → 09/08/2024 | (−131 ; −128) → (−45 ; −44) ; (−60 ; 105) → (−22 ; 37) | texture | idem |
| CHG-012 / 020 | rénovations : immeuble nord, toit commercial NO | 10/05/2022 → 09/08/2024 | emprises BD TOPO | apparence | façades et toits d'après IGN 2024 et photos du 18/05/2025 |
| CHG-013 à 017 | 4 arbres abattus, 5 plantés (parc est) | 10/05/2022 → 09/08/2024 | parc est, dont (143 ; −57) | végétation | hauteurs LiDAR 2021 non valables |
| CHG-018 / 021 | noue et cœurs d'îlot du quartier est | 09/08/2024 → 22/06/2025 | x 100..150, y 5..35 ; x 115..142, y 62..95 | sol, végétation | IGN 2024 non valable ; Pléiades 2025 et GAM daté, à vérifier |
| CHG-019 (non observé) | travaux annoncés sur l'avenue du Vercors | 01/04/2025 → 30/11/2025 | bande de ±15 m autour de l'axe | toutes | T tombe dans l'intervalle : état du 12/01/2025, `incertain` |
| SURF-0344 (audit § 2.5) | terre-plein arasé et peint à niveau | 12/08/2021 → 18/05/2025 | `surf_0344` (`decrire/surfaces.py:91-94`) | géométrie, Z | LiDAR 2021 non valable ; à resserrer sur l'ortho 2022 |
| TRV-C1-2025 | travaux du carrefour, arrêts La Revirée relogés | 23/06/2025 → 05/12/2025 | `marquages_sources.zones()` (plan CAO dilaté de 3 m), plus `relief_zones_2026`, plus `zone_travaux_2025`, marge de 3 m | toutes | toute preuve postérieure au 22/06/2025 non valable dans l'emprise |
| TRV-VERCORS-TROTTOIRS | trottoirs du Vercors | 23/06/2025 → 30/01/2026 | ±15 m autour de l'axe | géométrie | idem |

Format retenu :
- `recon/pcg/etat/etats/avant_travaux_2025.evenements.geojson`, en L93 ;
- propriétés : `id`, `date_min`, `date_max`, `familles`, `observe`, `confiance`, `marge_m`, `preuve` ;
- il est produit en phase 1 à partir de `changements_2022_2025.geojson` et des emprises de l'audit.

### 2.2 Statut des sources communes

| Source | Date | Statut pour T = 18/05/2025 |
|---|---|---|
| Ortho PCRS 5 cm (`ortho5cm_2022`) | 10/05/2022 | **référence géométrique** hors CHG-001 à 004 et hors marquages de CHG-008 |
| PCRS vecteur (`gam_*_pcrs`) | 2019 (date_leve) | bordures et limites de voirie, précision 10 cm. Seule source vectorielle de l'ancienne bretelle SE, de la contre-allée et du bord ouest de l'ancien îlot du tourne-à-droite (n° 28). Périmé sur 432 m sur 4 192 (CHG-001 à 004). |
| LiDAR HD, COPC `LHD_FXX_0917_6461` | 12/08 et 06/09/2021 | relief, vues de bordure, hauteurs des mâts et des arbres, sauf CHG-001 à 004, 013 à 017 et SURF-0344 |
| BD ORTHO IGN 2024 (RVB et IRC) | 09/08/2024 | référence couleur et contrôle de non-changement ; géométrie du quartier est (±0,1 à 0,2 m). **Prouve une présence, jamais une absence** : elle donne de faux absents sur les pavés jaunes délavés et la flèche TAD SO. |
| Pléiades 2025 | entre fin avril et le 22/06/2025 (estimée) | contrôle de présence ou d'absence de masses seulement (50 cm, recalée de +0,47 / +1,17 m) |
| Levé GAM `Meylan_Topo.dwg` (= `etat_2026` = `gam_topo_sol_*`) | mosaïque non datée | **admissible tronçon par tronçon** selon sa classe de datation (`sol/datation/gam_bordures_datation.geojson`, `marquages/datation_gam.geojson`). Jamais en bloc. |
| OSM « attic » | 01/06/2025, 20/06/2025, 22/06/2025 | topologie, arrêts, feux, traversées, ancienne position du mobilier. Prouve une présence, pas une absence : les lampadaires passent de 23 à 38 puis à 43 par simple enrichissement. |
| BD TOPO D038 | édition 2025-03-15 | emprises de bâtiments, tronçons, haies (à télécharger, 472 Mo) |
| Photos Panoramax / Mapillary | 2022 → 22/06/2025 | type, existence, matériaux, aspect, validation ; poses à étendre (phase 1i) |
| **Exclues** | — | `plan_projet_2025` (sauf comme emprise de TRV-C1), paquet v1 dans l'emprise (contre-indice), `osm_*` actuels du dépôt, heightmap « 3025 » dans les 69 zones modifiées, `.xodr`, `lanes` et `manoeuvres` 2026, `assets/specs/{panneaux,feux}.json` (inventaires 2026) |

### 2.3 Sol : bordures, surfaces, îlots, nivellement

| Attribut | 1 | 2 | 3 | 4 | Contrôle | Précision mesurée |
|---|---|---|---|---|---|---|
| Bordure en plan (arête avant seule) | Ligne GAM de classe `relief_2021`, `arasee_visible`, `masquee`, ou `apparue_2022_2024` (T ≥ 2024) | PCRS 2019 hors CHG-001 à 004 | Crête LiDAR 2021 (détection), puis contour sur l'ortho 2022 (`sol/pilote/ilot_coeur.py`) | IGN 2024 (CONSTR-EST, CHG-003 et 004, si le GAM manque) | Photos 2024-2025 aux poses calées | GAM / PCRS p50 3,5 cm ; contour ortho / GAM p50 4,7 cm, p90 12,3 cm ; bruit 0,7 à 0,9 cm |
| Classes GAM rejetées ou à revoir | `absente_avant` : rejetée (4,7 %) | `relief_seul` (449 m) et `terrain_remanie_2021` : revue sur planche | — | — | — | fausse alarme bornée à 2,2 % (témoin PCRS 2019) |
| Bordures absentes de tout vecteur | îlots IA-1 (7,02 m²) et IA-2 (22,26 m²) du cœur ; séparateur de Verdun NE (62 % non levé) ; 13 crêtes sans ligne (≈ 433 m) | si le dessus est en enrobé : crête décalée de 0,27 m vers l'intérieur, ou profil sur le LAZ | — | — | 2 photos 2024-2025 | anneaux G1 fermés, rayon ≥ 0,30 m |
| Vue (hauteur) et abaissés | Profils sur les **points LiDAR 2021** (LAZ) tous les 1 m | `bordures_hauteurs.h_lidar_2021_m` (heightmap 16 bits, p50 0,9 cm) | MNT JPEG (p90 6,3 cm), avec `conf: moyenne` | règle du profil (`a_priori`) | Abaissé = trou de crête et vue < 4 cm sur ≥ 0,8 m, recoupé par les chartières datées et la fin des zébras de 2022 | Pilote B : abaissé à ≤ 0,12 m des chartières |
| Nivellement Z | Sol nu LiDAR 2021 (classe 2), flottant à 10 cm, à produire depuis le COPC | Surfaces de conception (dévers de 1,5 à 2 %, fil d'eau continu, avaloirs) calées sur ce sol nu | CONSTR-EST : conception raccordée aux rives mesurées, marquée `a_priori` | — | G3 (§ 4.2) | heightmap / points : z p50 0,6 cm |
| Matériaux | Signatures de l'ortho 2022 (grain, ExG, R−B, luminance) et intensité LiDAR | Photos 2024-2025 | IGN 2024 (reprises CHG-009 à 011) | `a_priori` signalé | — | galets / enrobé : grain 6,9 contre 2,2 |
| Remplissage des îlots | Îlots du cœur : **galets** (photos 119d9094 et 31d16b8e du 18/05/2025) ; goutte NE : **terre et herbe** (constat coeur-31) | — | — | — | — | v2 2026 : gravier et BRF, faux |
| Âge (usure) | relatif à T : reprises 2024 = récent ; chaussées de Verdun refaites par COLAS en mars-avril 2019 = 6 ans ; quartier est = neuf (≤ 1 an) ; le reste = ancien | — | — | — | — | — |

Règles de construction, toutes reprises des pilotes de `sol/` :
- un **graphe planaire unique**, où le trou d'une chaussée est l'anneau même de l'îlot ;
- chaînes G1 dont chaque extrémité est un nœud typé (anneau, chartière, T, raccord), avec troncature à ≤ 0,10 m aux jonctions de sources ;
- un abaissé est un **intervalle de vue**, jamais un trou dans la bordure ;
- toute zone non décrite devient une face explicite.

### 2.4 Marquages

| Attribut | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Géométrie | **Ortho PCRS 2022** ajustée aux gabarits (pilote `marquages/pilote/`) : flèches 1 à 2 cm, zébras < 1 cm, largeur des traits −1,1 cm de biais | GAM seulement s'il est `present_identique` en 2022 à < 0,10 m | IGN 2024 et ortho-photos tirées des 360° calées (CHG-008, CONSTR-EST, CHG-003), ±0,1 à 0,2 m | règles d'inférence (`MARQUAGES.md` § 4.3) |
| Type | PCRS si l'IoU est ≥ 0,60 et la marge de type ≥ 0,05 | photos 2024-08 / 2025-05 projetées | GAM coïncident | affectation des voies de 2022 (jamais OpenDRIVE 2026) |
| Existence à T | photos 2024-2025 | IGN 2024 (présence seulement) | persistance depuis 2022 (vérifiée sur 11 passages et 7 flèches) | — |
| Usure, aspect | photos 2025-05 | contraste de l'ortho 2022 (médiane 0,42) | — | — |

Exclusions :
- le plan 2025 (52 marques de la v2) ;
- le zigzag du quai de Verdun SO du levé GAM (45 m et 72 m, absents en 2022 comme en 2024) ;
- les passages de la Revirée et du sud du levé, décalés de 0,35 et 0,39 m ;
- les 6 lignes d'effet des feux ajoutées en 2025.

À réintégrer : les 109 marques `retire_fantome` et les 309 marques v1 « retire » de la v2. Ce sont les marquages d'avant travaux.

Gabarits « site » à vectoriser une fois :
- `TRIDENT_SITE` ;
- flèches NE étroites ;
- logo vélo à roues évidées ;
- « 50 » et « 30 » cerclés ;
- pavé jaune 2022 de 0,40 × 0,49 m au pas de 0,589 m (et non le gabarit Chronovélo 2025 de 0,70 × 0,37).

Cas réglé : la flèche B-FL01 se pose en TD_TAD (photos de 2023, 2024 et 2025).

### 2.5 Objets : signalisation, feux, mobilier, réseaux

Base : `objets/objets_avant_travaux.geojson`.
- 759 objets : 471 présents, 219 présumés, 69 incertains ;
- 97 exclus, chacun avec sa raison.

| Attribut | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Position | Triangulation sur photos d'avant travaux (≥ 3 vues, angle ≥ 20°, σ ≤ 0,25 m) | Mât LiDAR 2021 (σ 0,15 m) hors CONSTR-EST | Ortho 2022 (σ 0,25 m) | OSM au 20/06/2025 (objets relogés) | Description 2026 hors emprise (684 objets) ; Mapillary seul (σ 3 m) avec contraintes d'implantation dures |
| Existence | Photo ou ortho datée 2022-2025 | Détection Mapillary jointe à LiDAR, OSM ou GAM | OSM d'avant travaux (présence seulement) | — | — |
| Orientation | Mapillary `aligned_direction` (azimut L93 = azimut vrai − 2,0086°) | Annotations Panoramax du 18/05/2025 (face ou dos) | Règles SIG-04, FEU-05, ECL-02 | — | — |
| Z, hauteur | MNT 2021 (l'ancienne chaussée a été rehaussée en 2025) | Hauteur LiDAR 2021 (334 objets), puis amas de classe 1 de plus de 3 m dans le COPC pour les mâts | Triangulation du sommet | Défaut par type | — |

Points imposés :
- **Arrêts La Revirée** à leur position d'avant travaux. Les travaux ont déplacé l'arrêt SE de 36,8 m vers le SO et l'arrêt NO de 18,1 m vers le NE ; on applique le déplacement inverse.
- Le poteau d'arrêt SE (`node/6569621813`) et les deux traversées à feux supprimées en 2025 (`node/1722505401`, `node/6569621810`).
- 11 supports de feux et 21 panneaux à moins de 60 m du centre.
- Les 22 objets d'emprise absents de la v2 2026 et les 53 objets hors emprise qu'elle oublie (22 lampadaires, 12 panneaux, 5 poteaux).
- Exclus : les 26 objets ajoutés par les travaux, dont 14 arbres plantés en 2025.
- `feu_SW_TPC` reste incertain : aucun mât n'est visible sur les vues de 2024 et de 2025.

Ponctuels au sol : tampons et avaloirs relevés sur l'ortho 5 cm. Il n'y en a aucun dans la v2 aujourd'hui (QUALITE a5).

Inventaires d'état : `sources/inventaires/{panneaux_avant,feux_avant}.json`, hors `assets/specs`.

### 2.6 Végétation

| Élément | Source primaire | Contrôle | Règle de chronologie |
|---|---|---|---|
| Arbres (466) : position | Levé GAM `arbre_pct` hors emprise, LiDAR 2021 et ortho 2022 | Photos 2024-2025, IRC 2024 | Poser les 10 arbres « absent 2026 » (présents avant) ; exclure les 14 plantés en 2025 et les 6 disparus avant travaux (`arbre_018`, `114`, `184`, `269`, `365`, `435`) |
| Arbres : hauteur et couronne | LiDAR 2021 | IGN 2024 | Pas de LiDAR pour CHG-013 à 017 ni pour les plantations du quartier est : prendre les ombres IGN 2024 (`changements/outils/soleil.py`) et les photos |
| Haies, massifs, gazons | Ortho 2022, IRC 2024, canopée COSIA 2024 | Photos 2025-05 | Rive ouest du Vercors : pertes COSIA 2021-2024 **non confirmées**, à vérifier. La bande plantée du Vercors est un massif (terre nue en hiver), pas une perte. |
| Saison | mi-mai | Photos du 18/05/2025 | Plein feuillage, aucun jaunissement ni feuille morte (règle `R-feuilles-automne` désactivée) |

### 2.7 Contexte : bâtiments, périphérie, lumière

| Élément | Source primaire | Complément | Remarque |
|---|---|---|---|
| Emprises de bâtiments | BD TOPO 2025-03-15 | IGN 2024 | Le quartier est (11 emprises) n'a de hauteur ni dans la BD TOPO ni dans le LiDAR 2021 |
| Hauteurs | LiDAR 2021 (±1 m) hors CHG-001 | Ombres IGN 2024 (soleil connu) et photos du 24/08/2024 pour CHG-001 | Tolérance proposée de ±1,5 m dans le quartier est, à confirmer par la mesure |
| Façades, toits | Photos 2024-2025 (type, couleur mesurée) | IGN 2024 (toits, CHG-012 et 020) | Base vie SE présente (CHG-005) |
| Périphérie ≥ 500 m, horizon | BD TOPO et RGE ALTI, ou dalles LiDAR HD voisines (0916_6461, 0916_6460, 0917_6460) | — | Aucun « bord du monde » visible (C5) |
| Lumière | Éphéméride à la date et à l'heure de chaque photo (validation) ; 18/05/2025 pour le niveau | Exposition dérivée de la luminance de la photo à même pose | Remplace le soleil d'octobre (220° / 29°) |

---

## 3. Changements du pipeline

### 3.1 Principe

- **Un état = une configuration** `etat_cible`. Ses champs :
  - `id`, `date_cible`, `date_etat`, `saison` ;
  - `evenements`, `sources`, `v_temporelle_marquages`, `regles_chronologie` ;
  - `references`, `dossier_sortie`, `entrees_partagees`, `ue`, `schema_description`.

  L'ébauche est dans `audit/proposition_etat_cible_avant_travaux.json`. Elle est **à corriger** sur quatre points, d'après les inventaires :
  - le GAM n'a pas de date unique : il est admissible par classe de datation ;
  - côté marquages, l'ortho 2022 passe avant le GAM ;
  - la liste des événements est celle du § 2.1 ;
  - le COPC 2021 est disponible.
- **Sélection** : `PJ_ETAT=avant_travaux_2025`, posé par un lanceur **avant les imports**, car les modules calculent leurs chemins à l'import (`commun.SORTIE`). Côté Houdini : `hython fabriquer_hda.py --etat …`.
- **Coexistence** : l'état 2026 garde `v2/` et la configuration `apres_travaux_2026`, avec ses constantes héritées. L'état avant travaux écrit **uniquement** sous `v2_avant_travaux/`. Si l'état 2026 est gelé (question 2), on supprime l'exigence de non-régression à l'octet.

### 3.2 Nouveaux fichiers (aucun fichier existant n'est remplacé)

| Fichier | Rôle |
|---|---|
| `recon/pcg/etat/etat_cible.py` | `charger()`, `E.dossier()`, `E.reference()`, `E.source()`, `E.valide(date, point, famille)`, `E.classe_date()`, `E.statut_objet()`, `E.age()`, `E.v_temporelle` |
| `recon/pcg/etat/etats/apres_travaux_2026.json` | reproduit le comportement actuel (11 constantes héritées comprises) |
| `recon/pcg/etat/etats/avant_travaux_2025.json` | configuration de ce plan |
| `recon/pcg/etat/etats/avant_travaux_2025.evenements.geojson` | table du § 2.1 |
| `recon/pcg/etat/etats/avant_travaux_2025.regles.json` | surcharge des paramètres d'état des règles : `attendu_site` d'INF-FLE-004, applicabilité des LOC-*, GEN-07 « à rebours », SIG-04 sur les voies d'avant travaux, tolérances GQ-TOL-001 d'`ortho2024` (0,25 m) et de `leve_emprise` (0,10 m) |
| `recon/pcg/etat/lancer.py` | fixe `PJ_ETAT` puis exécute le module ; refuse d'écrire dans un dossier dont `etat_cible.json` a un autre `id` |
| `recon/pcg/etat/tests/test_valide.py` | tests de la fonction de validité (critères de la phase 0) |
| `recon/pcg/etat/sources/{mnt_2021.py, evenements.py, xodr_avant.py, masque_chaussee.py, leve_emprise.py, osm_historique.py, inventaires_signalisation.py}` | producteurs des entrées propres à l'état (phase 1) |
| `recon/pcg/decrire/datation_leve.py` | datation GAM tronçon par tronçon, promue depuis `sol/pilote/dater_gam.py` et `marquages/pilote/datation_gam.py` |
| `recon/pcg/decrire/sol_graphe.py` | chaînes G1, nœuds typés, partition planaire (depuis `sol/pilote/{trottoir_abaisse, partition_A, ilot_coeur, geom_contours}.py`) |
| `recon/pcg/decrire/marquages_ortho_gabarits/` | détection et ajustement aux gabarits sur ortho, indépendants d'OpenDRIVE (depuis `marquages/pilote/{detection, zebras, fleches, lignes, damiers}.py`) |
| `recon/pcg/decrire/objets_etat.py` | fusion des objets à T (depuis `objets/scripts/inventaire.py`) |
| `recon/pcg/validation/{planches_photo_rendu.py, mesures_realisme.py}` | P4, M2, M3, L1, V1 automatisés (depuis `qualite/outils/`) |
| `assets/specs/marquages_gabarits_site.json` | gabarits « site » (nouveau fichier ; `marquages_geometrie.json` reste intact) |

### 3.3 Organisation des sorties

```
recon/out/paquet_jardin/
  package/                     paquet v1 (état 2026) : lecture seule
  v2/                          état 2026 : inchangé (apres_travaux_2026)
  v2_avant_travaux/            état avant travaux (avant_travaux_2025)
    etat_cible.json            copie figée ; son sha256 est cité par chaque manifeste
    inventaire/                inventaires du 11/10/2026 (ce dossier)
    sources/
      evenements/              evenements.geojson (copie figée de la table)
      relief/                  dtm_sol_2021_10cm.tif (non versionné), heightmap_avant_10cm.{png,json}, masque_chaussee_avant.geojson
      opendrive/               paquet_jardin_avant_travaux.xodr, lanes_avant_travaux.geojson, manoeuvres_avant_travaux.json
      leve_emprise/            bordures et limites reconstruites (PCRS 2019, LiDAR 2021, ortho 2022) avec leur classe de datation
      osm_2025-06-01/          couches osm_* découpées (copie de inventaire/sources/osm_2025-06-01)
      inventaires/             panneaux_avant.json, feux_avant.json
      poses_complementaires/   poses des séries 2022-06-10, 2023-03-18, 2025-01-12 et 2025-05-18 calées sur des GCP d'avant travaux
    description/{base, regularisation, coherence, enrichi, resolue/{base,objets,planches}, controle_sol}/, description_scene_v2.json
    enrichi/recensement/obs_reliees.json   observations re-datées (valide_cible) et ré-appariées
    fabrique_hda/              USD, points, prototypes, manifest_fabrication_hda.json (fabriqué depuis description/resolue/base)
    controle/                  rapport_regles.json, RAPPORT_REGLES.md, rendu/, mesures_realisme.json
    validation/                planches photo | rendu | superposition par pose, grille de revue en aveugle
    ue_pilote/                 captures et mesures UE de l'état
    photos_non_versionnees/    vignettes de photos de tiers (ignoré par git)
```

Partagés en lecture seule depuis `v2/` :
- `enrichi/poses/poses.json` ;
- `enrichi/recensement/mapillary/poses/poses_mapillary.json` ;
- `triangulation_mixte.json` ;
- `obs_*.json`.

Les déplacer vers `recon/out/paquet_jardin/commun/` est souhaitable, mais seulement après la passe de l'autre workflow.

Non versionnés :
- `photos_non_versionnees/` ;
- le COPC ;
- le MNT flottant.

Unreal :
- niveau `/Game/PJ/Maps/PJ_AvantTravaux_2025` ;
- données de l'état sous `/Game/PJ/Etats/AvantTravaux_2025/{Import,PCG/Donnees}`. Aujourd'hui, `/Game/PJ/Import/Sol` et `/Game/PJ/PCG/Donnees/PDA_*` sont uniques, d'où un risque de collision ;
- partagés : `/Game/PJ/{Lib,Materials,Textures}` et les graphes PCG.

### 3.4 Modifications fichier par fichier

Le détail complet, avec effort et risque, est dans `audit/AUDIT_PIPELINE.md` § 5 et dans `audit/occurrences_cablees.csv` (1 505 lignes dans 157 fichiers). Ce tableau en retient les décisions.

| Module | Fichier : lignes | Changement | Phase |
|---|---|---|---|
| schema | `description_scene_v2.schema.json:5, 13, 23, 122-123, 251, 269-270, 300, 314, 425` | Version 0.4, **ajouts seulement** : `date_etat` en motif `^\d{4}-\d{2}$` ; `src` ortho2024, pleiades2025, mapillary:<id>, photo:<plateforme>:<id>, leve_emprise ; `z_ref` nivellement_avant_travaux ; âge relatif à T (`neuf`) | 0 |
| decrire, socle | `commun.py:21-28` (SORTIE), `:121-126` (MNT) | `SORTIE = E.dossier("description")` (19 modules suivent) ; `MNT = E.reference("mnt")` | 0 |
| decrire, socle | `composer.py:34-54, 62-74, 121-122, 207-209` ; `valider.py:11, 25, 309` ; `contexte.py` (sources v1 et OSM) | Références, saison et `date_etat` tirées de `E` ; manifeste `etat_cible {id, sha256}` ; OSM à T | 0 |
| decrire, sol | `sol_site.py:61-84` (`gam_lignes`), `:88-101`, `:113-120`, `:183-201`, `:252-300`, `:344`, `:385-405` | GAM filtré par classe de datation (`datation_leve.py`) ; ajout de `pcrs2019` et `leve_emprise` ; masque de chaussée, passages et OSM d'avant travaux ; voies d'avant travaux | 2 |
| decrire, sol | `bordures.py:16-17, 134-139, 254-269, 558-563, 631, 669, 731-741, 747-811, 942-959, 1054-1061` | Séparer les trois cas mélangés en `558-563` (quartier est, modifiée 2025, plan projet) ; vue = `h_lidar_2021_m` ; `z_ref` d'après `E` ; âge relatif à T ; constats du 12/01 et du 18/05/2025 en preuves **contemporaines** (table par état) | 2 |
| decrire, sol | `surfaces.py:12-20, 57-94, 259-263, 741-765, 880-941` ; `ilots.py:28-50, 136-157, 264-266, 443-444` ; `sol_lacunes.py:254-270` | Tables matériau et âge indexées par l'âge à T ; constats (`surf_0121`, `surf_0344`) et remplissages par état (galets au cœur, terre et herbe sur la goutte NE) ; masques d'après `E` | 2 |
| decrire, sol | `sol_composer.py:6, 25-37, 74` ; `nivellement_xodr.py` ; `regulariser.py:55-57, 84-88, 232-236` | Références d'après `E` ; `.xodr` d'avant travaux ; tolérances de la surcharge | 2 |
| decrire, sol | **nouveau** `sol_graphe.py` branché après `regulariser` | Partition par graphe planaire et contrôles bloquants (T1) | 2 |
| decrire, marquages | `marquages_sources.py:1-24, 35-51` ; `ctl_detection.py:323-336` (FUS-SRC-001 codée en dur) | Tables `SOURCES` et `V_TEMPORELLE` lues dans `E` (même table aux deux endroits) ; `plan2025` = 0 ; l'ortho 2022 passe devant le GAM | 0 |
| decrire, marquages | `marquages.py:66-73, 108-120` ; `detection_indices.py:55-57` ; `detection_commun.py:29, 37-60` ; `marquages_commun.py:23-25` ; `marquages_contraintes.py:21` ; `marquages_chronovelo.py:29` ; `marquages_inference.py:191` ; `marquages_lignes.py:1125` ; `xodr_echantillonne.py:39-40` ; `marquages_indices_v1.py` ; `marquages_verifier.py`, `marquages_controles.py` | Rasters `ortho2022` et `ortho2024` (lecteur à 20 cm) ; bordures de l'état et non `etat_2026` ; pavés jaunes 2022 détectés au lieu du plan 2025 ; manœuvres et `.xodr` d'avant travaux ; indices v1 hors emprise seulement ; intégration de `marquages_ortho_gabarits/` | 2 |
| enrichir | `fusion_recensement.py:47-58, 61-79, 86, 96-140, 877…3900` | **Réécriture de la logique de date** : `valide_cible` calculée au chargement (`E.valide`) ; classes relatives à T ; règles FUS-* paramétrées ; `absent_cible` ; ré-appariement de `lien_description` (identifiant stable hors emprise, sinon appariement spatial FUS-LIEN-04/06) | 3 |
| enrichir | `gcp.py:37-38, 65-72, 131, 206` ; `mapillary.py:68, 732, 764, 782, 950, 1466-1485` ; `orthos_recentes.py:47-53, 1275-1377` ; `camera.py:222` ; `projection.py:7, 21, 195` ; `triangulation.py:149, 206-208, 358-404` | Bornes tirées de `E.evenements` ; objets « absent 2026 » admis comme GCP ; `validite_2026` remplacée par `E.valide` ; MNT de l'état. **Le recalage Mapillary sur les bordures doit lire les bordures de l'état, pas le GAM 2026.** | 1, 3 |
| decrire, cohérence | `coherence.py:7-29, 88-115, 158-169, 536-564, 859-972, 1019-1058` ; `coherence_objets.py:24-27, 86-224` ; `coherence_carte.py` ; `coherence_mesures.py` ; `coherence_photos.py:43, 67-68` ; `coherence_verifs.py` ; `coherence_poses.py` ; `coherence_presence.py` ; `coherence_politique.py` ; `coherence_sorties.py:568-579` ; `coherence_marquages.py:600-612` ; `coherence_ombres.py:53` | Q3, Q4 et Q8 relatives à T, sur photos contemporaines ; `a_verifier_terrain2026` devient `a_verifier_archive` (une visite est impossible pour un état passé) ; chemins d'après `E` | 4 |
| decrire, résolution | `resoudre.py` ; `resoudre_sources.py` ; `resoudre_regles.py:11-129` ; `resoudre_objets.py` ; `resoudre_marquages.py` ; `resoudre_ajouts.py` ; `resoudre_revue.py` (verdicts codés en dur) | Textes et seuils RES-* paramétrés par T (RES-EXI-002 devient « événement intercalé ») ; stations de terrain remplacées par des archives ; verdicts de revue sortis dans un fichier de données par état | 4 |
| houdini | `fabriquer_hda.py:44-46, 550-558, 689-701` | `--etat` et `--description` ; fabrication depuis `description/resolue/base` | 0 |
| houdini | `fabriquer_hda.py:431-473` (`ecrire_materiaux`) ; `controle/rendre_controle.py:40-45` | **MaterialX texturé unique** (porté depuis `pj_materiaux.py`) ; le rendu de contrôle compose toutes les couches ; HDRI ou ciel physique, courbe de tons standard | Q, 5 |
| houdini | `hda/pj_sol/construire.py:67, 197-248` ; `hda/pj_bordure/construire.py:361-372` ; `pj_decals.py:114-124` ; `pj_ilot` (`eclats_debordement`) | Suppression du flou de Z et du retrait des « falaises » ; sol posé sur des surfaces de conception ; épaufrures sur les arêtes, sans sphères ; aucun pontage ni éclat sans preuve | Q, 5 |
| houdini | `pj_commun.py:5, 26-30` ; 7 scripts de contrôle et d'essai avec des chemins `v2` (`controles_f1.py`, `rendre_marquages.py`, …) | Chemins tirés de `E` | 0 |
| controle | `ctl_commun.py:25-33, 592-652` ; `verifier_regles.py:41-47` | `--etat` ; références et GAM filtré d'après `E` | 0 |
| controle | `ctl_marquages.py:406, 656-660, 735-840, 917-926` ; `ctl_sol.py:518, 759, 1076, 1495-1528, 1762-1771` ; `ctl_reseau.py` (VAL-XOD-008) ; `ctl_detection.py:30-46, 120-303, 473-556` | Attendus de site lus dans la surcharge ; VAL-KRB-005 contre le levé admissible ; règles « plan2025 » marquées « non applicables à l'état » ; ortho 2024 en plus | 6 |
| controle | **nouveau** : famille `realisme_validation` | P4, M2, M3, L1 et V1 rapportés par `verifier_regles.py` (dans la surcharge d'état, sans modifier `regles_conception.json` tant que l'autre workflow y travaille) | 6 |
| ue | `pilote/pilote.py:8-9, 67` ; `pilote/ue/niveau_2026.py` ; `pj_tools/eclairage.py:28-35` ; `contexte/*.py` (chemins `v2/ue_pilote`) ; `contexte/preparer_usd.py:5-11, 60-73, 262-284` ; `vegetation/arbres.py:140-143` ; `feuilles.py`, `pg_herbe.py`, `carla_feuillage_automne.py` | Niveau, soleil, saison et racines de contenu d'après `E` ; **import de la fabrication HDA du site entier, sans v1** (au lieu de `fabrique_ue_snapshot`) ; arbres filtrés par statut à T ; feuillage de printemps | 7 |
| specs | `regles_conception.json` (42 règles sur 255 datées), `regles_locales_meylan.json` (14 sur 46), `regles_implantation.json` (`etat_cible` « octobre 2026 »), `regles_qualite_geometrique.json` (GQ-TOL-001) | **Aucune modification** : paramètres d'état dans la surcharge. `bordures`, `vegetation`, `mobilier` et `carla_correspondances` restent intouchés (autre équipe). | 0 |
| docs | `ARCHITECTURE.md` § 0, 1.3, 1.5, 1.6 ; `README.md` | Section « États cibles » ; suppression de « aucune image après travaux » comme hypothèse de base | 7 |

### 3.5 Garde-fous de coexistence

1. Chaque manifeste (description, fabrication, contrôle, UE) écrit `etat_cible {id, sha256}`. Le lanceur refuse une écriture croisée, et l'absence de `PJ_ETAT` dans un dossier `v2_avant_travaux` est une erreur.
2. Si l'état 2026 est gardé, la configuration `apres_travaux_2026` doit reproduire **à l'octet** :
   - `hash_description` et `hash_marquages` ;
   - `manifest_fabrication_hda.json` ;
   - `rapport_regles.json`.

   L'harmonisation des 11 dates de travaux est une décision séparée, qui changera les sorties 2026.
3. Une exécution d'état ne sauvegarde jamais `paquet_jardin_pcg.hip` (seul `--construire-hip` le fait).
4. La phase 0, qui touche environ 60 fichiers partagés, se fait **après** la passe en cours de l'autre workflow sur `decrire`, `houdini`, `controle` et `v2`, en lots courts, sur une branche dédiée et sans édition concurrente.

---

## 4. Qualité : correctifs intégrés dès le départ et définition de « terminé »

### 4.1 Causes racines et correctifs

| Cause racine (`qualite/QUALITE.md`) | Constat mesuré sur la v2 2026 | Correctif intégré | Phase | Critère |
|---|---|---|---|---|
| RC1 Époque non contrôlée, sources mélangées | 419 bordures sur 504 issues du GAM post-travaux ; 154 marquages GAM, 52 du plan 2025 ; Z « MNT 2026 » ; bordures à ≤ 10 cm d'une arête 2022 : 84,8 % hors travaux, mais 58,6 % en zone de travaux | Table d'événements et `E.valide` ; GAM par classe de datation ; plan 2025 et `etat_2026` exclus ; MNT 2021 | 0, 1, 2 | S1, P1 |
| RC2 Rendu sans matériau ni contexte | 51 `UsdPreviewSurface` à albédo constant ; énergie de détail de la chaussée 5 à 8, contre 14 à 37 sur photo | MaterialX texturé unique Karma / UE ; albédos calés sur photos datées | Q, 5 | M1 à M3 |
| RC3 Sol tiré d'un MNT corrigé a posteriori | 4 passes de flou de 40 itérations ; 30 % des trottoirs au-dessus de 8 % sur 2 m ; pied de bordure − MNT p95 24 cm ; 76 cuvettes ; 11 m² de recouvrements | Graphe planaire ; surfaces de conception calées sur le LiDAR 2021 ; ni flou ni retrait de triangles ; avaloirs décrits | 2, 5 | T1, G2 à G5 |
| RC4 Description limitée au sol | 0 sur 13 mâts de feux, 0 sur 29 têtes, 0 sur ≈ 30 panneaux posés ; bâtiments en trous | Objets, végétation et contexte décrits dès la phase 2 ; prototypes FR de feux et panneaux (piste Q) | Q, 2, 5, 7 | C1 à C4, OB1 |
| RC5 UE en patchwork v2 / v1 | v2 sur 71 × 100 m seulement ; v1 ailleurs (119 924 triangles de bordures en murs) | Import de la fabrication du site entier, 0 maillage v1, racine par état | 7 | U1 |
| RC6 « Terminé » = conformité aux normes | 13 poses Panoramax acceptées ; 2 planches photo / UE ; NCC des marquages médiane 0,35 | Famille `realisme_validation` ; au moins 30 vues ; planches automatiques ; revue en aveugle | 1i, 6 | S3, P4, V1, V2 |
| RC7 Détails procéduraux sans preuve | Pontages aléatoires à 0,10 m/m² ; épaufrures en sphères ; 397 éclats | Usure, reprises et pontages **observés** seulement (ortho 5 cm, photos) | 5 | M4 |
| Éclairage | Ciel (0,46 ; 0,50 ; 0,55) contre 0,65 à 0,94 sur photo ; dynamique 0,35 à 0,57 contre 0,80 à 0,95 ; soleil d'octobre | Soleil et saison de chaque photo pour la validation ; exposition dérivée de la luminance | 5, 7 | L1, L2 |

À garder :
- la fidélité au tracé (p95 1,6 cm sur les lignes admissibles) ;
- la régularisation G1 et le déterminisme ;
- les poses calées ;
- le look-dev du pilote ;
- les classes de surface, cohérentes avec l'ortho 2022 hors travaux (2,2 % d'aire incohérente).

### 4.2 Définition de « terminé » (tout est mesuré automatiquement et rapporté avec sa valeur)

| ID | Critère | Seuil | Mesure | Actuel (v2 2026) |
|---|---|---|---|---|
| **S1** | Chaque entité porte `date_validite` et des sources admissibles à T (`E.valide`) | 100 % ; 0 entité du plan 2025 ; 0 ligne GAM `absente_avant` | Script de provenance | 154 marquages GAM post-travaux, 52 du plan 2025, 139 `neuf_2025` |
| **S2** | Part `a_priori` | ≤ 15 % de l'aire de sol ; matériau des bordures ≤ 10 % de la longueur à ±80 m et ≤ 35 % sur le site | Manifeste | Classe a priori : 766 surfaces sur 1 410 ; matériau des bordures : 499 sur 504 |
| **S3** | Vues calées d'avant travaux | ≥ 30 vues distinctes acceptées à ≤ 80 m, dont ≥ 3 par branche photographiée (Verdun NE, Verdun SO, Vercors, centre) et ≥ 5 de 2022 ; Revirée : exception documentée (aucune photo n'en remonte la branche depuis le 19/02/2020) | `poses*.json` | 20 vues à ≤ 80 m ; 0 de 2022 ; 0 acceptée le 12/01/2025 |
| **T1** | Topologie de la description | Σ aires = domaine ; recouvrement = trou = 0 (pixels de 2 cm) ; chaque bordure citée par 2 faces ; chaque îlot = 1 anneau fermé ; chaque extrémité de bordure sur un nœud typé | `sol_graphe.py` | 704 m² non décrits ; 11 bordures orphelines ; ceinture de I-0297 ouverte de 19,6 m |
| **P1** | Bordures et arête de l'ortho de référence (PCRS 2022 ; IGN 2024 dans CONSTR-EST et CHG-003 / 004) | PCRS : ≥ 90 % des échantillons de 1 m à ≤ 10 cm, ≤ 3 % sans arête, p90 ≤ 12 cm. IGN 2024 : ≥ 90 % à ≤ 25 cm | `qualite/outils/ecart_ortho2.py` | 84,8 % hors travaux ; 58,6 % en zone de travaux |
| **P2** | Marquages et image de référence | IoU ≥ 0,60 et marge de type ≥ 0,05 (sinon arbitrage photo) ; NCC ≥ 0,5 pour ≥ 90 % ; zébras : largeur 0,50 ± 0,01 m, résidu de pas < 3 cm ; tirets : phase p95 ≤ 0,10 m, latéral p95 ≤ 0,05 m | Pilote de marquages, VAL-IMG-007 | NCC médiane 0,35 ; 84 marques sur 194 sous le seuil |
| **P3** | Classes de surface et ortho | ≤ 2 % d'aire incohérente, **y compris** dans l'emprise des travaux | `qualite/outils/classes.py` | 2,2 % hors travaux ; non mesuré dans l'emprise |
| **P4** | Reprojection des arêtes dans les photos calées (entités valides à la date de la photo) | Médiane ≤ 3 px, p90 ≤ 8 px à 960 px / 90° | `validation/mesures_realisme.py` | non mesuré ; faux au cœur |
| **MQ1** | Couverture des marquages | ≥ 95 % des 576 marques visibles sur l'ortho 2022 décrites ; 100 % des 11 passages, 7 flèches et 6 files de pavés du cœur ; longues continues reprises ≥ 90 % (auto : 15 %) | `marquages/couverture_site.py` | auto non revu : 40 à 60 % |
| **OB1** | Signalisation du cœur | 11 sur 11 supports de feux et 21 sur 21 panneaux à ≤ 60 m triangulés (≥ 3 vues, σ ≤ 0,25 m) ou au LiDAR ; 0 objet à σ > 0,5 m au cœur | `triangulation.py` | 57 objets en Mapillary seul (σ 3 m) |
| **OB2** | Objets relogés et supprimés par les travaux | Arrêts La Revirée, poteau SE et traversées à feux à leur position du 20/06/2025 (± σ) ; 0 objet ajouté en 2025 | Comparaison avec `objets_avant_travaux.geojson` | v2 : 13 objets à la position 2026 |
| **G1** | Continuité G1 (bordures, limites, lignes) | 0 cassure > 2° hors coins voulus ; rayon ≥ gabarit | Règles GQ-* étendues aux limites | limites raster non régularisées |
| **G2** | Sol étanche | 0 trou > 0,005 m² ; 0 recouvrement > 3 mm ; 0 triangle retiré | TQ-SOL-009, compteur de falaises | 4 trous (0,16 m²) ; 11 m² de recouvrements |
| **G3** | Z et LiDAR 2021 hors événements | Chaussée et trottoir − sol nu : RMS ≤ 3 cm, p95 ≤ 5 cm ; pied de bordure p95 ≤ 3 cm ; vue de bordure − LiDAR p95 ≤ 2 cm | TQ-SOL-013, VAL-KRB-005 | pied − MNT p95 24,2 cm ; vue p95 7,5 cm |
| **G4** | Pentes | Trottoirs : dévers de 1 à 3 %, pente sur 2 m ≤ 5 % pour ≥ 95 % de l'aire hors rampes ; 0 cuvette > 3 mm sans avaloir décrit | GA-TRO-004, VAL-SOL-009 | 30 % des trottoirs au-dessus de 8 % ; 76 cuvettes ; 0 avaloir |
| **G5** | Raccords de bordures | GA-BOR-005 à 100 % (pied ≤ 1 cm, tête ≤ 2 cm) | Contrôleur | 27 % |
| **G6** | Échelle | Bâtiments : ±1 m au LiDAR (±1,5 m dans le quartier est) ; arbres : ≤ 15 % pour 90 %, aucun plafonnement | Comparaison des hauteurs | arbres plafonnés à 22-23 m dans UE |
| **M1** | Matériaux | 100 % des maillages visibles texturés (albédo, normale, rugosité), UV en mètres, sans répétition visible à plus de 20 m | Contrôle USD | 0 sur 51 |
| **M2** | Rapports d'albédo, rendu contre photo à même pose | écart ≤ 15 % (bordure / enrobé, peinture / enrobé, remplissage / enrobé) | `rapports_photos_rendus` généralisé | bordure / enrobé 1,01-1,21 contre 4,48 |
| **M3** | Détail de la chaussée (énergie du laplacien) | rendu ≥ 60 % de la photo, bruit de rendu soustrait | M-C | 5-8 contre 14-37 |
| **M4** | Détails | 100 % des reprises et pontages visibles sur l'ortho 5 cm décrits ; 0 détail non sourcé | Revue de provenance | pontages statistiques |
| **L1** | Ciel et dynamique | dynamique p99 − p1 ≥ 0,75 ; ciel à ±15 % (RVB) de la photo de même pose | M-C | 0,35-0,57 ; ciel gris |
| **L2** | Soleil, saison | azimut et hauteur à ±2° de l'éphéméride de chaque photo ; feuillage de la saison de la photo | EXIF et calcul solaire | octobre contre mai |
| **V1** | Ressemblance à même pose sur ≥ 30 vues | IoU sémantique ≥ 0,7 pour les classes de sol et ≥ 0,5 pour bâtiments et arbres | Planches photo / rendu / superposition | 2 planches UE |
| **V2** | Revue indépendante en aveugle (ARCHITECTURE § 1.7) | moyenne ≥ 2 sur 3, aucun 0, puis accord de l'utilisateur | Agent séparé | non faite |
| **C1** | Bâtiments à T | 100 % posés, aucun trou de sol, façade par type et couleur mesurée | Inventaire BD TOPO 2025 / ortho | Karma 0 ; UE 34 boîtes |
| **C2** | Végétation à T | 100 % des arbres retenus (statut à T), essence, saison de mai | `objets_avant_travaux` (arbres) | Karma 0 |
| **C3** | Feux et signalisation verticale à T | 100 % des mâts, têtes et panneaux ; positions à ≤ 0,5 m des photos | Inventaire de l'état | UE : 0 sur 13 mâts |
| **C4** | Mobilier et réseaux | ≥ 95 % de l'inventaire, dont avaloirs et tampons | Idem | 58 objets, 0 avaloir |
| **C5** | Périphérie et horizon | terrain, bâti et arbres simplifiés jusqu'à ≥ 500 m ; aucun bord du monde visible | Vues de contrôle | bord visible (n3) |
| **U1** | Niveau UE = fabrication du site | hash de description identique à Karma ; 0 maillage v1 | Inventaire des acteurs | v2 sur 71 × 100 m seulement |
| **U2** | Performance | ≥ 60 i/s en 1080p sur la RTX 5070 (Lumen) | `contexte_perf` | 68 i/s sur le pilote |
| **U3** | Coexistence (si 2026 gardé) | sorties 2026 identiques à l'octet ; 0 asset UE partagé écrasé | Manifestes, chemins `/Game/PJ/Etats` | — |
| **D1** | Déterminisme | deux exécutions donnent des sorties identiques à l'octet | Manifestes | conforme (à garder) |

**Terminé** : tous les critères sont au seuil, V2 est passée et l'utilisateur donne son accord. Un rendu ne part plus vers l'utilisateur tant que S1, T1, P1, M1, L2 et V1 ne sont pas mesurés.

---

## 5. Phases ordonnées

Ordre logique : description → vérification photo → résolution → HDA → contrôle → UE. Deux phases le précèdent : le socle (phase 0) et les données d'avant travaux (phase 1). Une piste qualité Q, indépendante de la date, court en parallèle.

```
            maintenant                         après la passe de l'autre workflow
 P1 Données d'avant travaux (sources/) ──┐     P0 Socle etat_cible (code partagé)
   1a MNT 2021   1b événements           │       │
   1c datation GAM   1d levé d'emprise   ├──────►P2 Description de base ──► P3 Vérif. photo ──► P4 Résolution ──► P5 HDA ──► P6 Contrôle ──► P7 UE
   1e .xodr   1f masque   1g téléchargts │       (2a sol ∥ 2b marquages ∥ 2c objets/végétation/contexte)      ▲
   1h inventaires   1i poses ────────────┘                                                                    │
 Q  Piste qualité : MaterialX unique, prototypes FR feux/panneaux, gabarits marquages site, partition HDA ──────┘
```

### Phase 0 : socle `etat_cible` (2 à 3 j-agent, après la passe de l'autre workflow)

- **Contenu** :
  - `recon/pcg/etat/` (module, configurations, surcharge des règles, lanceur, tests) ;
  - branchement de `E` dans les chemins et références (§ 3.4, lignes marquées 0) ;
  - schéma 0.4 ;
  - tables de `marquages_sources` et `ctl_detection` lues dans `E`.
- **Critères de fin** :
  - (a) si l'état 2026 est gardé : manifestes de description, de fabrication et de contrôle 2026 identiques à l'octet avant et après branchement (U3) ;
  - (b) `E.valide` avec T = 2026-10 donne les mêmes classes qu'aujourd'hui sur les 1 475 observations ; avec T = 18/05/2025, les 1 392 observations de 2022 à juin 2025 sont classées, et 0 observation postérieure au 22/06/2025 est valable dans TRV-C1 ;
  - (c) relevé `occurrences_cablees` : 0 chemin `v2/` en dur dans les modules du chemin avant travaux ;
  - (d) le lanceur refuse une écriture croisée (test).

### Phase 1 : données d'avant travaux (5 à 8 j-agent ; peut démarrer tout de suite ; écrit seulement sous `v2_avant_travaux/sources/` et dans de nouveaux scripts)

| Lot | Contenu | Critère de fin |
|---|---|---|
| 1a | Sol nu 2021 en flottant à 10 cm depuis le COPC (PDAL de QGIS, méthode `README_relief.md` étapes 1 et 3) ; MNT d'avant travaux (régalage du quartier est raccordé aux rives) | z − points de `bordures_hauteurs` : p95 ≤ 2 cm sur les 1 722 tronçons ; vues d'IA-1 et IA-2 mesurées sur points (aujourd'hui 13,5 à 17,2 cm au JPEG) ; profil I2 ou T2 / T3 tranché |
| 1b | Table d'événements (§ 2.1) en GeoJSON, avec les emprises polygonales et les familles | 21 CHG, plus TRV-C1, TRV-VERCORS et SURF-0344 ; carte regardée et superposée à l'ortho 2022 et à l'IGN 2024 |
| 1c | Datation GAM promue (`datation_leve.py`) ; revue sur planche des 449 m `relief_seul` et des `terrain_remanie_2021` du cœur | 100 % des 7 005 m de bordures, 4 601 m de limites et 2 544 m de marquages classés ; 0 `relief_seul` non revu à ±80 m |
| 1d | Levé d'emprise : bordures et limites reconstruites (PCRS 2019, crêtes LiDAR, contours sur l'ortho 2022), dont IA-1, IA-2, le séparateur de Verdun NE et l'ancienne bretelle SE | P1 ≥ 90 % sur l'emprise ; anneaux fermés G1 ; écart au PCRS 2019 p95 ≤ 0,10 m là où il existe |
| 1e | `.xodr`, voies et manœuvres d'avant travaux : topologie OSM du 01/06/2025 (bretelles SE et vers le Vercors, contre-allée), bords de voie tirés des lignes 2022, 11 feux, échantillonneur `xodr_echantillonne.py` réutilisé | Bords de voie − lignes 2022 : p95 ≤ 5 cm ; manœuvres cohérentes avec 100 % des flèches 2022 du cœur ; jonction valide (VAL-JCT, VAL-XOD) |
| 1f | Masque de chaussée d'avant travaux (remplace `relief_zones_2026` et `dans_chaussee_2026`) | Écart à l'ortho 2022 : ≤ 2 % d'aire incohérente |
| 1g | Téléchargements de données publiques : BD TOPO D038 du 2025-03-15 (472 Mo) ; 43 photos Panoramax 2023-2025 manquantes (`objets/.../recherche_2022_2025.json`) ; dalles LiDAR ou RGE ALTI de la périphérie si C5 l'exige | Fichiers dans `data/sites/paquet_jardin/avant_travaux/<source>/`, lus avec `python -I` ; photos hors git |
| 1h | Inventaires `panneaux_avant.json` et `feux_avant.json` depuis `objets_avant_travaux.geojson` | 11 supports de feux, 57 panneaux, avec code, support et azimut quand il est connu |
| 1i | Poses complémentaires **calées sur des GCP d'avant travaux** (coins de zébras et marques de l'ortho 2022, pieds de mâts LiDAR 2021, objets « absent 2026 ») : 24 vues 360° du 18/05/2025, 12 du 12/01/2025, 32 Mapillary du 10/06/2022, séries du 18/03/2023 ; revalidation des 5 poses Mapillary `calee_bordures` situées entre 40 et 80 m (calées sur le GAM 2026) | S3 : ≥ 30 vues distinctes acceptées à ≤ 80 m (aujourd'hui 20), ≥ 3 sur le Vercors, ≥ 5 de 2022 ; erreur moyenne ≤ 0,5° (360°) ou ≤ 8 px |

### Phase 2 : description de base (6 à 9 j-agent, en 3 sous-lots parallèles ; sortie `v2_avant_travaux/description/base`)

- **2a Sol** : bordures datées et chaînées, îlots, surfaces, caniveaux, ponctuels (tampons, avaloirs), matériaux, nivellement sur le MNT 2021 et les surfaces de conception, partition par `sol_graphe.py`.
  - Critères : T1, P1, P3, G1, G3 et G4 (au niveau de la description) ; S2 pour le sol ; galets au cœur et terre et herbe sur la goutte NE.
- **2b Marquages** :
  - extraction sur tout le site depuis l'ortho 2022, avec les gabarits IISR et site ;
  - suivi des longues continues guidé par les bordures ;
  - IGN 2024 et ortho-photos pour CHG-008 et le quartier est ;
  - réintégration des 109 fantômes et des 309 marques v1 ;
  - revue sur planches (1 à 2 h).
  - Critères : MQ1, P2 ; 0 marque du plan 2025 ; marques sur trottoir (MQ-DET-010) = 0 hors cas voulus.
- **2c Objets, végétation, contexte** : 759 objets, avec leur statut à T ; 466 arbres ; haies et massifs ; bâtiments de la BD TOPO 2025 avec hauteurs (LiDAR, ombres) ; périphérie.
  - Critères : OB2 ; C1, C2 et C4 au niveau de l'inventaire ; 0 objet ajouté par les travaux ; 22 lampadaires et 12 panneaux oubliés par la v2 présents.
- **Jonction** : `valider.py` passe ; chaque objet est implanté contre les bordures **de l'état** (GEN-07 à rebours dans l'emprise) ; S1 = 100 %.

### Phase 3 : vérification photo (3 à 4 j-agent ; sortie `v2_avant_travaux/enrichi`)

- **Contenu** :
  - `valide_cible` recalculée sur les 1 475 observations, ré-appariement des liens ;
  - projection de la description dans toutes les vues acceptées ;
  - triangulation des objets verticaux (priorité : 57 objets Mapillary seuls, 22 objets d'emprise, `feu_SW_TPC`, objets relogés) ;
  - extraction d'attributs (matériaux, types de flèches, état d'usure), en deux passes indépendantes.
- **Critères de fin** :
  - P4 sur ≥ 30 vues ;
  - OB1 ;
  - couverture stricte du cœur ≥ 22,6 % par simple re-datation, puis valeur rapportée après les nouvelles poses ;
  - 0 décision fondée sur une photo séparée de T par un événement ;
  - chaque attribut enrichi cite sa photo et ses pixels.

### Phase 4 : résolution, cohérence et RES (2 à 3 j-agent ; sortie `description/resolue`)

- **Contenu** : Q3, Q4 et Q8 relatives à T ; règles RES-* paramétrées ; arbitrages et verdicts de revue par état ; les non-résolus renvoient vers une **archive à consulter**, pas vers une station de terrain.
- **Critères de fin** :
  - S1 et S2 au seuil ;
  - 0 conflit non arbitré à ±80 m ;
  - liste `a_verifier_archive` publiée, avec pour chaque entrée la source à consulter ;
  - T1 toujours vrai après résolution.

### Phase 5 : fabrication HDA (3 à 5 j-agent, si la piste Q est faite ; sortie `fabrique_hda`)

- **Contenu** :
  - `hython fabriquer_hda.py --etat avant_travaux_2025 --description …/resolue/base` ;
  - MaterialX texturé ; sol sans flou ni retrait de triangles ;
  - contexte composé : bâtiments, arbres, feux, panneaux, mobilier ;
  - détails observés seulement ;
  - rendu Karma de contrôle aux poses calées, avec soleil de la photo.
- **Critères de fin** : G2, G5, M1, M4, D1 ; le rendu de contrôle compose toutes les couches ; M2, M3 et L1 mesurés sur ≥ 10 poses (seuils atteints ou écart justifié avant la phase 7).

### Phase 6 : contrôle (1 à 2 j-agent ; sortie `controle`)

- **Contenu** : `verifier_regles.py --etat avant_travaux_2025` avec la surcharge (attendus tirés des manœuvres d'avant travaux, règles « plan2025 » non applicables) et la famille `realisme_validation`.
- **Critères de fin** :
  - 0 violation bloquante ;
  - toutes les mesures du § 4.2 rapportées avec leur valeur ;
  - planches photo / rendu / superposition générées aux ≥ 30 poses ;
  - revue en aveugle V2 lancée.

### Phase 7 : Unreal (3 à 5 j-agent)

- **Contenu** :
  - niveau `PJ_AvantTravaux_2025` et racine `/Game/PJ/Etats/AvantTravaux_2025` ;
  - import de la fabrication du site entier, 0 maillage v1 ;
  - feux et panneaux FR posés ; arbres filtrés par statut à T, feuillage de mai ;
  - soleil et exposition calés sur les photos ;
  - vues CineCamera aux poses de validation.
- **Critères de fin** : U1, U2, U3, C3, C5, L1, L2 et V1 (≥ 30 vues) ; V2 ≥ 2 sans aucun 0 ; accord de l'utilisateur.

### Piste Q : qualité indépendante de la date (4 à 6 j-agent, en parallèle dès maintenant pour ce qui est nouveau, après la passe de l'autre workflow pour ce qui touche `houdini/`)

- **Matériaux** : une seule définition MaterialX pour Karma et UE (port de `pj_materiaux.py` dans `fabriquer_hda.py:431-473`), avec tuilage hexagonal et albédos calés sur les photos datées (charte enrobé / bordure / peinture).
- **Prototypes FR** : feux R11v, R12, R13c, mâts, panneaux (faces PNG de `panneaux.json`), abri, potelets, en assets de bibliothèque.
- **Gabarits de marquage « site »** dans `assets/specs/marquages_gabarits_site.json`.
- **HDA** :
  - `pj_sol` sur partition topologique (arc partagé maillé une seule fois) et surfaces de conception ;
  - `pj_bordure` avec épaufrures sur les arêtes ;
  - `pj_ilot` sans éclats par défaut.

### Effort et parallélisme

| Phase | j-agent | Parallélisable avec |
|---|---|---|
| P0 | 2-3 | P1, Q (sauf fichiers `houdini/` partagés) |
| P1 | 5-8 | P0, Q ; lots 1a à 1i entre eux (1d dépend de 1a et 1c ; 1e de 1d ; 1i est indépendant) |
| P2 | 6-9 | 2a ∥ 2b ∥ 2c, puis jonction |
| P3 | 3-4 | — (dépend de P2 et de 1i) |
| P4 | 2-3 | — |
| P5 | 3-5 | Q doit être terminée |
| P6 | 1-2 | début de P7 (import d'essai) |
| P7 | 3-5 | — |
| Q | 4-6 | P0 à P4 |
| **Total** | **31-47** | chemin critique d'environ 20 à 30 j-agent (P1 → P2a → P3 → P4 → P5 → P6 → P7) |

Les 15 à 25 j-agent de l'audit couvrent P0, P1 et une partie de P2 à P4. Le reste correspond aux correctifs de qualité (RC2 à RC7) qui n'y figuraient pas.

---

## 6. Risques et questions

### 6.1 Risques

| # | Risque | Impact | Parade |
|---|---|---|---|
| R1 | **`.xodr` d'avant travaux à recréer** : le générateur `recon/stages` est absent. Il conditionne 31 règles du contrôleur, les manœuvres et les attendus de flèches. | Chemin critique (lot 1e) | Topologie OSM du 01/06/2025, lignes 2022 mesurées, échantillonneur existant réutilisé ; validation par les bords de voie (p95 ≤ 5 cm) |
| R2 | **Concurrence avec l'autre workflow** sur `decrire`, `houdini`, `controle` et `v2` | Conflits, régression 2026 | Phase 1 et piste Q sans toucher aux fichiers existants ; P0 après sa passe, en lots courts sur branche ; garde-fous du § 3.5 |
| R3 | **Quartier est** (16 % des surfaces circulées) : ni LiDAR ni hauteurs après 2021 ; BD TOPO sans hauteur | Z et hauteurs a priori | Conception raccordée aux rives, ombres IGN 2024, photos du 24/08/2024 ; tolérance de ±1,5 m signalée ; entités marquées `a_priori` |
| R4 | **Vercors** : travaux annoncés d'avril à novembre 2025, non observés ; aucune photo entre le 12/01 et le 23/06/2025 | État faux sur ±15 m autour de l'axe | État du 12/01/2025, `incertain` ; Pléiades 2025 en contrôle de masses |
| R5 | **Couverture photo déséquilibrée** : centre vu par 5 photos 2025, toutes depuis la même voie (NE → SO) ; Revirée sans photo qui en remonte la branche depuis le 19/02/2020 ; 0 pose acceptée en 2022 | S3, V1 et P4 limités sur certaines branches | Lot 1i (séries 2022-06, 2023-03, 2025-01) ; exception documentée pour la Revirée, contrôle par ortho seulement |
| R6 | **Poses calées sur le GAM 2026** : 27 Mapillary `calee_bordures`, dont 5 entre 40 et 80 m | Biais de pose dans l'emprise | Revalidation sur GCP d'avant travaux (1i) |
| R7 | **Datation GAM imparfaite** : fausse alarme 2,2 % ; tronçons < 1,5 m peu fiables ; 449 m `relief_seul` | Lignes 2025 admises par erreur, ou lignes réelles rejetées | Revue sur planche obligatoire à ±80 m ; contrôle P1 sur l'ortho 2022 |
| R8 | **Date Pléiades 2025 inconnue** | Mauvaise interprétation d'une absence | Contrôle de présence seulement ; jamais de preuve d'absence |
| R9 | **Glyphes hors IISR et marques usées** (trident, logos vélo, flèche TD / TD_TAD, extrémités de tirets à 31 cm p95) | Types ou extrémités faux | Gabarits site ; phase des tirets ajustée sur la file ; arbitrage par photo sous une marge de 0,05 |
| R10 | **Licences** (CC-BY-SA des photos, CC-BY CARLA, City Sample réservé à UE) | Non-conformité | Vignettes dans `photos_non_versionnees/` ; COPC et MNT flottant hors git ; `meta.json` d'attribution |
| R11 | **Ampleur (31 à 47 j-agent)** | Dérive | Phases courtes à critères chiffrés ; aucune livraison visuelle avant S1, T1, P1, M1, L2 et V1 mesurés |

### 6.2 Questions pour l'utilisateur (seulement celles qui changent le plan)

1. **Date cible : confirmez-vous le 18/05/2025, veille des travaux ?**
   - La saison et le soleil suivent cette date : mi-mai, plein feuillage.
   - Variante quasi équivalente : le 24/08/2024 (coût nul ; seuls les abords de Verdun NE diffèrent).
   - Le 10/05/2022 coûte 4 à 7 j-agent de plus. Le quartier est y est un chantier sans source 3D, et aucune photo de 2022 n'est calée : je le déconseille.
2. **L'état 2026 doit-il rester maintenu en parallèle, ou être gelé tel quel ?**
   - Maintenu : non-régression à l'octet (U3), coordination continue avec l'autre workflow, puis harmonisation des 11 dates de travaux. Cela ajoute environ 2 à 3 j-agent et des contraintes sur chaque lot.
   - Gelé : `v2/` est archivé, la chaîne n'est paramétrée que pour l'avant travaux, sans exigence d'octet.
3. **Acceptez-vous de demander à la Métropole ou au CRAIG l'ortho PCRS 5 cm de 2025, accessible seulement sur abonnement (HTTP 401) ?**
   - À demander aussi : son jour de vol et, si possible, les plans de l'existant du marché C1.
   - Si le vol précède le 23/06/2025, cette ortho devient la référence géométrique et couleur exacte de la date cible : elle remplace le couple 2022 + 2024 au cœur et lève les incertitudes CHG-008, 009 et 019.
   - Sinon, le plan reste tel quel.

---

## Annexe A. Chiffres réconciliés entre les inventaires

| Sujet | Écart entre rapports | Valeur retenue (vérifiée) |
|---|---|---|
| Poses calées | `changements` : 58 ; `qualite` : 13 ; `objets` : 64 caméras (19 Panoramax et 45 Mapillary) | `poses.json` : 13 Panoramax `accepte` (5 le 24/08/2024, 8 le 18/05/2025). `poses_mapillary.json` : 45 calées (27 `calee_bordures`, 5 `calee_gcp`, 13 `calee_panoramax`, ces dernières étant les **mêmes prises** que les Panoramax). Soit **45 vues distinctes** (31 le 24/08/2024, 14 le 18/05/2025), dont 20 à ≤ 80 m. L'inventaire `objets` applique un critère de calage plus large côté Panoramax. |
| Nuage LiDAR 2021 | `sol` : « absent, téléchargement à autoriser » | **Présent** : `data/sites/paquet_jardin/avant_travaux/lidar_hd/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz` (150 890 899 octets, 11/10 à 08:47, ignoré par git). PDAL 2.8.2 : `C:/Program Files/QGIS 4.2.3/bin/pdal.exe`. |
| Date du levé GAM | `audit` : « ≈ 2025-12, à dater » | Il n'y a pas de date unique : c'est une compilation sans date par objet, extraite le 06/10/2026, qui contient des tronçons de 2019 à 2025-2026. L'admissibilité se juge **par classe de datation**. |
| Priorité des marquages | `audit` (proposition) : GAM 0,95 avant ortho 2022 | Ortho 2022 d'abord : 1 à 3 cm, contre 7,0 cm de médiane pour le GAM coïncident. Le GAM ne vient qu'en 2e rang, s'il est `present_identique` à < 0,10 m. |
| Bordures au cœur | `sources` : PCRS 2019 d'abord ; `sol` : GAM daté d'abord | GAM daté admissible (levé de géomètre, PCRS / GAM p50 3,5 cm) ; PCRS 2019 là où le GAM est absent ou rejeté ; puis LiDAR et ortho 2022. Les deux avis convergent tronçon par tronçon. |
| Changements 2022-2025 | « 17 de confiance haute ou moyenne, 3 faibles, 1 risque » | GeoJSON : 21 entités (10 haute, 7 moyenne, 4 faible dont CHG-019 non observé) |
| Surfaces | `statistiques.json` | Géométrie invalide sur 23 943 m² (26,6 % de l'emprise), 9,0 % à r ≤ 40 m ; texture de chaussée 18,3 % à r ≤ 40 m ; marquages 9,9 % à r ≤ 40 m ; 69,8 % de l'emprise sans changement observé |
| Objets | `objets_avant_travaux.geojson` | 759 (471 / 219 / 69), confiance 339 / 198 / 222 ; 97 exclus |

## Annexe B. Fichiers d'appui

- Sources : `sources/SOURCES.md`, `sources/sources.json`, `sources/photos_inventaire.json`, `sources/osm_2025-06-01/osm_*.geojson`, `sources/lidar_dates.json`.
- Changements : `changements/CHANGEMENTS.md`, `changements/changements_2022_2025.geojson`, `changements/donnees/statistiques.json`, `changements/planches/carte_changements_2022_2025.png`.
- Audit : `audit/AUDIT_PIPELINE.md`, `audit/occurrences_cablees.csv`, `audit/proposition_etat_cible_{avant_travaux,2026}.json`, `audit/instantane_code_sha1.txt`.
- Marquages : `marquages/MARQUAGES.md`, `marquages/marquages_pilote_2022.geojson`, `marquages/datation_gam.geojson`, `marquages/couverture_site.json`, `marquages/pilote/*.py`.
- Sol : `sol/SOL.md`, `sol/datation/gam_bordures_datation.geojson`, `sol/pilote_A/ilots_avant_travaux.geojson`, `sol/pilote_B/bordure_rive_B.geojson`, `sol/precision_hauteurs.json`, `sol/pilote/*.py`.
- Objets : `objets/OBJETS.md`, `objets/objets_avant_travaux.geojson`, `objets/objets_exclus.geojson`, `objets/comparaison_2026.json`.
- Qualité : `qualite/QUALITE.md`, `qualite/mesures_qualite.json`, `qualite/planche_n1_rendu2026_vs_ortho2022.png`.
- Téléchargements : `data/sites/paquet_jardin/avant_travaux/{lidar_hd, osm_2022-05-10, osm_2025-06-01, osm_actuel_2026-10-11, osm_historique, mapillary_map_features, panoramax, panoramax_semantique, gam_geoflux_2026-10-11, ign}/`.
