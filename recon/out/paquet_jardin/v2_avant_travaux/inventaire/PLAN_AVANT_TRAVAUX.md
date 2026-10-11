# Plan de reconstruction de l'état d'avant travaux : carrefour « Paquet Jardin », Meylan

Révision 1 du 11/10/2026 (10 h 30). Elle intègre la relecture adverse du plan et des sept inventaires de ce dossier : `sources/`, `changements/`, `audit/`, `marquages/`, `sol/`, `objets/` et `qualite/`.
- Chaque critique a été recontrôlée. Le § 7 liste celles qui sont rejetées, en tout ou en partie, et l'annexe C la suite donnée à chacune.
- Les chiffres nouveaux ou corrigés sont recalculés par `revision/outils/verifier_critiques.py` (lancé avec `python -I`), qui écrit `revision/verifications_revision.json` et la planche `revision/chg019_coeur_poses.jpg`.
- La version précédente est conservée dans `revision/PLAN_AVANT_TRAVAUX_v0_2026-10-11_0957.md`.

Statut : **proposition**. Aucun module du pipeline n'est modifié. Aucun fichier existant du dépôt n'a été touché pour écrire ce plan.

Conventions :
- repère local = L93 − (917279,43 ; 6460289,98), z = NGF − 216,30 ;
- UE : X = 100·x, Y = −100·y, Z = 100·z ;
- **effort** = jours de travail d'un agent (j-agent), sommés sur tous les lots ; **durée** = jours calendaires sur le chemin critique, lots indépendants menés en parallèle ;
- les références `fichier:ligne` du § 3 renvoient à l'instantané du code du 11/10/2026 à 08:32 (`audit/instantane_code_sha1.txt`). À 10 h 20, 3 fichiers sur 250 avaient déjà changé (`controle/ctl_reseau.py`, `decrire/marquages_chronovelo.py`, `houdini/hda/README_HDA.md`) : les lignes citées peuvent bouger.

---

## 0. En bref

1. **Date cible recommandée : le 24/08/2024**, sous réserve de la réponse à la question 1. La variante est le 18/05/2025, veille des travaux. Le plan précédent recommandait le 18/05/2025 ; la comparaison chiffrée du § 1.3 renverse ce choix :
   - **Certitude au cœur.** Le 24/08/2024, la géométrie au cœur (r ≤ 40 m) est valable et certaine sur **91,2 %** de la surface. Le 18/05/2025, ce n'est que **75,7 %**, car l'emprise CHG-019 (travaux annoncés sur le Vercors à partir du 01/04/2025, jamais photographiés) couvre 18,5 % du cœur. Elle descend jusqu'à 7,7 m du centre et englobe la bretelle SE et son îlot.
   - **Preuves du jour même.**
     - Le 24/08/2024 : 31 vues calées sur 45, et 56 photos uniques couvrant les cinq secteurs, dont 7 sur le Vercors et 25 dans le quartier est.
     - Le 18/05/2025 : 14 vues calées et 24 photos, sur Verdun et au centre seulement.
     - Près du centre, l'écart est faible : 9 vues contre 11 à 80 m ou moins.
   - **Ortho.** L'ortho IGN du 09/08/2024 précède le 24/08/2024 de 15 jours. Le 18/05/2025 dépend au contraire de la date de la Pléiades 2025, qui n'est pas prouvée : elle se situe entre le 03/05 et le 08/08/2025.
   - **Saison.** Le 24/08/2024 est dans la même saison que 69 % des vues de validation (31 sur 45).
   - **Coûts.** Le 24/08/2024 oblige à modéliser les clôtures de chantier et les bungalows de la rive SE de Verdun NE (CHG-006 et 007) : +0,5 à 1 j-agent. Le 18/05/2025 coûte +1 à 2 j-agent (rognage de CHG-019 par observations négatives, état incertain du Vercors et des CHG-018 / 021).
2. **Le levé GAM n'est pas un état d'avant travaux.**
   - `vector/gam_topo_sol_*`, `etat_2026/*` et `data/vector_gz/gam` sont une même extraction : 4 574 sommets de bordure identiques sur 4 614, le reste venant de la découpe. Les commits 42ee3af et b4a8384 datent tous deux du 06/10/2026. `Meylan_Topo.dwg` est un plan vivant, sans date par objet.
   - Sa datation tronçon par tronçon (7 005 m de bordures) donne 44,6 % de relief 2021, 13,2 % d'arasées visibles en 2022, 6,0 % apparues de 2022 à 2024 et 4,7 % absentes avant 08/2024. **31,4 % restent indéterminés** : relief seul 6,4 %, terrain remanié 18,5 %, masquées 6,5 %.
   - Seul le taux de fausse alarme est mesuré (2,2 %). Le rappel sur des lignes de 2025 ne l'est pas. Dans l'emprise des travaux, une ligne GAM ne sera donc admise que si elle coïncide **à moins de 0,10 m** avec une arête de 2022 (§ 2.3), et ce rappel sera mesuré sur un jeu témoin (lot 1c).
3. **La géométrie de référence est mesurée, pas déduite :**
   - ortho PCRS 5 cm du 10/05/2022 pour les marquages (1 à 3 cm) et les contours (p50 4,7 cm) ;
   - PCRS vecteur 2019 et LiDAR HD 2021 pour les bordures et le relief. Le COPC (150 890 899 octets) est déjà téléchargé ; **PDAL 2.10.0** est disponible dans QGIS 4.2.3 ;
   - BD ORTHO IGN du 09/08/2024 (20 cm) et photos 2024-2025 pour ce qui a changé. Le recalage IGN 2024 est une translation globale de (0,035 ; 0,029) m. La précision locale reste de **±0,1 à 0,2 m** : écart médian absolu (MAD) de 0,10 / 0,05 m, fenêtres jusqu'à 0,51 m. Elle ne prouve pas une persistance à quelques centimètres près.
4. **La chronologie est réglée par une table d'événements datés** (§ 2.1). Elle comporte :
   - les 21 changements 2022-2025, les travaux de 2025 et SURF-0344 ;
   - les **événements de 2019 à 05/2022**, jusqu'ici non inventoriés : réfection COLAS de 2019, réseaux 2019-2022, terrassements du secteur est, rive est du Vercors en chantier dès le 05/03/2022 ;
   - des **observations négatives** : « état vu inchangé le jour d, dans la zone Z » ;
   - un champ `observe_post`, date de la première observation de l'état d'après.

   La règle d'arbitrage donne la priorité, attribut par attribut, à la **précision**. La proximité de T ne sert qu'à départager deux sources de précision comparable.
5. **Les sources « 2026 » sont exclues dans l'emprise des travaux** : `etat_2026` en bloc, plan projet 2025, OSM actuel, MNT « octobre 2026 », paquet v1, `.xodr` 2026.
   - Les **poses calées ne sont pas réutilisables telles quelles**. `gcp.py` tire ses GCP de `marquages_2026` (paquet v1) et son z du MNT 2026, et 27 poses Mapillary sont calées sur les bordures GAM 2026. Les 45 vues sont donc recalculées avec des GCP de l'état (lot 1i).
   - La **BD TOPO 2025-03-15 est abandonnée** : les 12 emprises du quartier est n'y entrent que le 04/07/2025, sans hauteur. On la remplace par les 111 lignes de bâtiments du levé GAM dans le secteur est, datées par l'IGN 2024, et par l'extrait BD TOPO déjà présent.
6. **Le pipeline devient paramétrable par un `etat_cible`** (`PJ_ETAT=avant_travaux`, la date étant un paramètre).
   - Une seule fonction de validité, `E.valide`, remplace les 11 constantes de travaux réparties dans 9 fichiers.
   - Les sorties vont sous `v2_avant_travaux/`.
   - Les 10 HDA `pj_*` ne sont réutilisables **qu'après les correctifs de la piste Q**. `pj_sol` (flou et falaises), `pj_bordure` (sphères), `pj_decals` (pontages) et `pj_ilot` (397 éclats) portent les causes RC3 et RC7 du rendu 2026.
7. **Les six causes du « super mal fait » sont corrigées dès le départ** :
   - une époque, avec des sources datées ;
   - matériaux MaterialX texturés (aujourd'hui 0 sur 51) ;
   - contexte composé : bâtiments, arbres, 11 supports de feux, panneaux FR ;
   - sol en partition topologique sur des surfaces de conception calées sur le LiDAR, sans flou ;
   - import UE complet, sans v1 ;
   - validation **par l'image**, avec un critère de couverture spatiale et des seuils compatibles avec la précision des poses.

   Une **porte G0** (tranche verticale) impose un rendu complet du cœur, mesuré aux 9 vues calées à 35 m ou moins, **avant** d'étendre au site. En 2026, le premier rendu complet n'est arrivé qu'à la fin.
8. **L'effort est de 36 à 55 j-agent** (8 phases, la porte G0 et la piste Q), et de 2 à 3 de plus si l'état 2026 est maintenu.
   - La durée du chemin critique est de **20 à 31 jours**, plus l'attente de la passe de l'autre workflow si celle-ci retarde la phase 0 au-delà de la fin du lot critique de la phase 1.
   - La phase 1 démarre tout de suite pour ses lots indépendants du code partagé : 1a à 1d, 1f à 1h et 1j. Le lot 1i commence par un solveur de poses autonome, en nouveaux fichiers. Le lot 1e attend 1d et 1j.
9. **Trois questions à l'utilisateur, dans cet ordre** (§ 6.2) :
   - **Q2 d'abord** : geler l'état 2026 (recommandé, avec une étiquette git posée par l'utilisateur) ou le maintenir ;
   - Q1 : la date cible, avec la matrice du § 1.3 ;
   - Q3 : les demandes à la Métropole (ortho PCRS 2025 et son jour de vol, version d'avant récolement de `Meylan_Topo.dwg`, récolements VRD des Saules Blancs).

---

## 1. Date cible

### 1.1 Recommandation

| Paramètre | Valeur recommandée (T = 24/08/2024) | Variante (T = 18/05/2025) |
|---|---|---|
| `date_cible` | **2024-08-24** : séance Panoramax et Mapillary 360°, de 15:05:21 à 15:11:01 UTC (56 photos uniques) | 2025-05-18 : séance de 13:37:08 à 13:38:10 UTC (24 photos uniques, doublées par 24 copies Mapillary) |
| `date_etat` | 2024-08 | 2025-05 |
| Stabilité | Tous les changements de 2022 à 2024 (CHG-001 à 005 et 008 à 017) sont achevés au 09/08/2024. Seuls CHG-018 et 021 (quartier est, au-delà de 80 m) ont une `date_min` égale à celle de l'IGN : 15 jours d'incertitude entre l'ortho et T | Changent entre le 24/08/2024 et T : CHG-006 et 007 (abords de Verdun NE, x 20..125), CHG-018 et 021 (quartier est, date Pléiades) et CHG-019 (Vercors, non observé, T dans l'intervalle) |
| Preuves plus anciennes (2019-2023) | admises là où aucun événement ne les sépare de T (§ 2.1) : PCRS 2022, PCRS 2019 et LiDAR 2021 au cœur, hors CHG-001 à 006 | idem, mais au cœur seulement hors CHG-019 tant qu'il n'est pas rogné |
| Preuves postérieures | photos du 12/01/2025 et du 18/05/2025 admises hors CHG-006 / 007 / 018 / 021, et hors CHG-019 sauf observation négative | photos du 24/08/2024 admises hors CHG-006 / 007 / 018 / 021 / 019 |
| Avenue du Vercors | photos du jour même (7 uniques), IGN 2024 ; certain | état du 12/01/2025 (12 vues 360°, aucune pose acceptée), `incertain` |
| Saison et soleil du niveau | fin août, plein feuillage ; soleil de 248,6° / 34,3° à 249,8° / 33,3° pendant la séance | mi-mai ; soleil de 235,2° / 53,9° à 235,6° / 53,8° pendant la séance |

### 1.2 Preuves disponibles par période (chiffres réconciliés)

| Période | Orthos | Vecteurs / relief | Photos uniques (dont centre r ≤ 35 m) | Vues calées acceptées (distinctes), avant recalcul 1i | OSM historique | Stabilité de la scène |
|---|---|---|---|---|---|---|
| 2018-2021 | BD ORTHO 21/08/2018 et 13/08/2021 (20 cm) ; ortho GAM 02/07/2018 (25 cm) | PCRS vecteur 2019 (Geofit, `date_leve` 2019-01-01) ; LiDAR HD : 12/08/2021 (77,9 % des points), 06/09/2021 (21,8 %) | 2021 : 0 | 0 | 01/06/2020 | réfection COLAS mars-avril 2019 ; réseaux 2019-2022 ; secteur est remanié dès 2021 (classe `terrain_remanie_2021`) |
| **2022** | **PCRS 5 cm du 10/05/2022** ; SPOT 29/05 et 17/06 | — | 64 (7) : Mapillary 05/03, 10/06 et 03/11 | **0** (44 poses a priori) | 10/05/2022 : 150 objets | rive est du Vercors en chantier dès le 05/03/2022 ; secteur est en gros œuvre |
| 2023 | SPOT 19/07 et 02/09 (1,5 m) | — | 35 (9) : 18/03/2023 | 0 (28 a priori) | 01/06/2023 | immeubles est en élévation |
| **2024** | **BD ORTHO 09/08/2024 (RVB et IRC, 20 cm ; translation (0,035 ; 0,029) m, précision locale ±0,1-0,2 m)** ; CRAIG ortho 2024 (20 cm) ; SPOT juillet | canopée COSIA 2024 | 322 (10), dont 225 dans les parkings (24/02) et 14 à 80 m ou moins le 01/05/2024 | **31** le 24/08/2024 : 5 Panoramax, 24 Mapillary calées sur bordures GAM 2026, 2 sur GCP | 01/06/2024 | quartier est livré ; reprises d'enrobé au cœur (chantier de tranchées vu le 01/05/2024) |
| **2025, jusqu'au 22/06** | Pléiades 2025 (50 cm ; date non publiée, entre le 03/05 et le 08/08/2025 d'après les ombres, § 2.2) | BD TOPO 2025-03-15 (sans les bâtiments est : abandonnée) | 36 (5) : 12/01 (Vercors, 12) et 18/05 (Verdun NE → SO, 24) | **14** le 18/05/2025 : 8 Panoramax, 3 Mapillary sur bordures, 3 sur GCP | 01/06/2025 : 214 objets ; 20/06 et 22/06/2025 | aucun chantier visible au cœur le 18/05/2025 ; rien n'est photographié sur le Vercors après le 12/01 |
| après le 23/06/2025 | SPOT 25/06/2025 ; PCRS 5 cm 2025 (accès restreint, juin-juillet) | levé GAM (mosaïque datée jusqu'à 2025-2026) | 50 | 0 | actuel | travaux : **exclu** |

Les comptes de séance sont maintenant réconciliés :
- 18/05/2025 : **24 photos Panoramax uniques**, chacune doublée par une copie Mapillary, soit 48 fichiers. Les rapports donnaient 19 (CHANGEMENTS § 4, Panoramax posées), 24, 40 et 52 ;
- 24/08/2024 : 56 photos uniques, plus 57 copies Mapillary ;
- 45 vues calées distinctes : les 13 `calee_panoramax` de Mapillary sont les mêmes prises que les 13 Panoramax acceptées. Elles comptent 31 vues du 24/08/2024 et 14 du 18/05/2025. 20 sont à 80 m ou moins (9 et 11), dont 9 à 35 m ou moins (4 et 5).

### 1.3 Comparaison chiffrée des deux dates candidates (matrice de la question 1)

| Critère | 24/08/2024 | 18/05/2025 | Source du chiffre |
|---|---|---|---|
| Géométrie 2022 valable et certaine au cœur r ≤ 40 m | **91,2 %** (8,8 % non valables, CHG-001 à 006, remplacés par l'IGN 2024 et les photos du jour) | **75,7 %** : 8,8 % non valables et 18,5 % incertains (CHG-019) ; de 81 à 91 % après rognage de CHG-019 par observation négative (lot 1b), non garanti | `verifications_revision.json` (raster de 0,25 m) ; `statistiques.json` : 946 m², soit 18,8 % |
| m² incertains sur le site | 0 au cœur ; ≈ 2 575 m² au-delà de 80 m (CHG-018 / 021, fenêtre de 15 jours entre l'IGN et T, état d'avant retenu) | ≈ 4 340 m² (CHG-019, dont 946 m² au cœur), plus ≈ 2 575 m² (CHG-018 / 021, fenêtre de 9 à 12 mois, date Pléiades inconnue) | `changements_2022_2025.geojson`, `statistiques.json` |
| Dépendance à la date Pléiades | aucune (état du 09/08/2024 vu 15 jours avant) | CHG-018 et 021 : `date_max` = 08/2025, donc incertains à T | § 2.2 |
| Vues calées le jour même (avant recalcul 1i) | 31, dont 9 à ≤ 80 m et 4 à ≤ 35 m | 14, dont 11 à ≤ 80 m et 5 à ≤ 35 m | `poses.json`, `poses_mapillary.json` |
| Photos uniques du jour même, par secteur | 56 : est 25, Verdun NE 9, Verdun SO 8, Vercors 7, centre 4, autre 3 | 24 : Verdun NE 10, Verdun SO 9, centre 5 ; ni Vercors, ni secteur est | `photos_inventaire.json` |
| Ortho la plus proche | IGN 09/08/2024, 20 cm, site entier (T − 15 j) | Pléiades 2025, 50 cm, date inconnue | `sources/SOURCES.md` § 3 |
| Saison des vues de validation | identique pour 31 vues sur 45 (69 %) | identique pour 14 vues sur 45 (31 %) | — |
| Objets à modéliser en plus | clôtures de chantier et bungalows de la rive SE de Verdun NE (CHG-006 et 007), base vie SE (CHG-005) | haies et parkings de CHG-006 et 007 ; base vie SE | `CHANGEMENTS.md` |
| STOP des Mitaillères | non vu le jour même ; attesté par les photos du 12/01/2025, valables à T (aucun événement intercalé) | attesté | CHG-003 |
| Distance aux travaux | 10 mois avant | 5 semaines avant | — |
| Effort propre à la date | +0,5 à 1 j-agent (objets de chantier en 2c) | +1 à 2 j-agent (rognage de CHG-019, revue Pléiades, Vercors incertain) | estimation |

Les deux dates donnent la même configuration de voirie : celle d'avant le projet C1. On y trouve :
- la bretelle de tourne-à-droite SE avec son îlot ;
- la contre-allée de Verdun SO ;
- les quais La Revirée d'origine ;
- les deux traversées à feux supprimées en 2025 ;
- les îlots en galets ;
- les pavés Chronovélo de 2022 ;
- le quartier est livré.

La différence porte sur la certitude et sur les abords de Verdun NE.

Le 24/08/2024 l'emporte sur six critères : certitude, Pléiades, couverture par secteur, ortho, saison et effort. Le 18/05/2025 l'emporte sur la proximité des travaux, la couverture à 80 m ou moins (+2 vues) et l'état fini des abords de Verdun NE.

Ce classement doit être reconfirmé après le recalcul des poses du lot 1i. Si moins de 15 des 26 poses Mapillary du 24/08/2024 survivent au recalcul sans bordures GAM, la matrice est refaite avant de figer la date.

### 1.4 Pourquoi pas le 10/05/2022

Le jour du PCRS coûte **+4 à 7 j-agent** :
- le quartier est est un chantier sans source 3D (grue, terre nue, base vie) ;
- il faut retirer les 6 % de traits GAM apparus en 2022-2024 ;
- les marquages de Verdun NE sont ceux de 2022 (CHG-008).

La validation par l'image y est faible : 7 photos au centre, perspectives Mapillary sans pose acceptée. Les photos de 2024-2025 ne valent plus hors du cœur. **Déconseillé.**

---

## 2. Sources retenues par famille et règles de chronologie

### 2.1 Règle unique : la table d'événements

Une observation datée d, au point p, pour une famille f (géométrie, marquage, texture, objet, végétation, apparence), est **valable** pour T si aucun événement E ne remplit les trois conditions suivantes :
- E touche f ;
- l'emprise de E, marge comprise, contient p ;
- E a pu se produire entre d et T, c'est-à-dire que l'intervalle [date_min ; date_max] de E chevauche [min(d, T) ; max(d, T)].

Cas particuliers :
- **non valable** : d tombe dans l'intervalle d'un événement observé qui touche p ;
- **incertain** : p est à moins de `marge_m` du bord de l'emprise, ou d ou T tombe dans l'intervalle d'un événement **non observé** ;
- **observation négative** : une observation qui montre la zone A inchangée à la date d1, avec une pose acceptée et une visibilité calculée, retire A de tout événement non observé dont la date_min précède d1. C'est ainsi que les photos du 18/05/2025, sans chantier sur les 40 premiers mètres du Vercors, rognent CHG-019. Le champ `observe_post` (première observation de l'état d'après) resserre de même la `date_max` d'un événement, zone par zone.

**Arbitrage** entre preuves valables : on applique d'abord la priorité par attribut des § 2.3 à 2.7, puis la précision (σ). La proximité de T ne départage que deux preuves dont les σ diffèrent d'un facteur 1,5 au plus. Exemple : l'IGN 2024 (±0,1 à 0,2 m) ne remplace jamais le PCRS 2022 (5 cm) là où les deux sont valables. Elle ne sert qu'à l'aspect et là où 2022 n'est pas valable.

Ce modèle généralise celui de `gcp.py` (`valide_de` / `valide_a`). Il remplace :
- `valide_2026`, FUS-DATE-01 et 02 ;
- `apres_travaux()`, `anterieure_travaux()` ;
- `TRANCHES_PROBANTES`.

Chaque événement déclare les familles qu'il touche. Par exemple, une reprise d'enrobé (CHG-009) invalide la texture de 2022, mais pas la géométrie des bordures.

| Id | Nature | date_min → date_max (observe_post) | Emprise (repère local) | Familles | Effet pour T = 24/08/2024 | Effet pour T = 18/05/2025 |
|---|---|---|---|---|---|---|
| EVT-2019-COLAS | réfection de chaussée COLAS, Verdun SO et NE | 01/03/2019 → 30/04/2019 | autour de (−54 ; −53) et (44 ; 37), selon les arrêtés | texture (géométrie à vérifier) | PCRS vecteur 2019 (`date_leve` 2019-01-01) à confronter à l'ortho 2022 sur ces tronçons | idem |
| EVT-2019-2022-RESEAUX | tranchées ENEDIS, GRDF, eau (16 arrêtés) | 2019 → 05/2022 | emprises des arrêtés | texture | aspect 2022 valable seulement après la dernière date | idem |
| CHG-001 / 002 (CONSTR-EST) | quartier est : bâtiments, voies, parkings, parc | **≤ 12/08/2021** → 09/08/2024 (terrain déjà remanié sur le LiDAR) | x 37..156, y −67..92, plus ≈ 21 000 m² extérieurs | toutes | PCRS 2022 et 2019, LiDAR 2021 non valables ; IGN 2024, photos du 24/08/2024 (25 dans le secteur) et GAM daté valables | idem, plus les photos du 18/05/2025 hors CHG-006 |
| CHG-003 | carrefour Vercors / Mitaillères : branche, îlot, STOP | 10/05/2022 → 09/08/2024 (STOP vu le 12/01/2025) | x 18..78, y −143..−112 | géométrie, marquage, objet | IGN 2024, photos du 24/08/2024 et du 12/01/2025 | IGN 2024, photos du 12/01/2025 ; incertain dans CHG-019 |
| CHG-004 | rive est du Vercors : bordure, trottoir, allée | **≤ 05/03/2022** → 09/08/2024 | x 22..40, y −62..−33 | géométrie | IGN 2024 et photos du 24/08/2024 ; **pas le GAM** (trottoirs refaits jusqu'au 30/01/2026) | IGN 2024 et photos du 12/01/2025 ; incertain (CHG-019) |
| CHG-005 | base vie bleue SE | → 09/08/2024 | x 16..31, y −33..−17 | objet | présente | présente |
| CHG-006 / 007 | abords SE de Verdun NE, nouvel accès riverain | 24/08/2024 → 18/05/2025 | bande de 3 à 24 m, x 20..125 | géométrie des abords, objet, végétation | **état du jour** : clôtures de chantier, bungalows (photos du 24/08/2024, IGN 2024) ; photos de 2025 non valables | haies et parkings (photos du 18/05/2025) ; photos de 2024 non valables |
| CHG-008 | marquages de l'approche NE de Verdun (zone hachurée) | 18/03/2023 → 09/08/2024 | x 1..66, y −1..66 | **marquage** | PCRS 2022 non valable pour les marquages ; IGN 2024 et photos du 24/08/2024 | idem, plus les photos du 18/05/2025 |
| CHG-009 | reprises d'enrobé au cœur (chantier vu le 01/05/2024) | 18/03/2023 → 09/08/2024 (`observe_post` à fixer par zone) | x −35..10, y −33..18 | **texture** | aspect d'après l'IGN 2024 et les photos du 24/08/2024 ; âge « récent » (< 1 an) | idem, plus les photos du 18/05/2025 |
| CHG-010 / 011 | tranchées refermées : Verdun SO (3,5 × 120 m), Revirée (2,5 m) | 2022 (011 : 24/02/2024) → 09/08/2024 | (−131 ; −128) → (−45 ; −44) ; (−60 ; 105) → (−22 ; 37) | texture | idem | idem |
| CHG-012 / 020 | rénovations : immeuble nord, toit commercial NO | 10/05/2022 → 09/08/2024 | emprises BD TOPO | apparence | IGN 2024 et photos du jour | IGN 2024 et photos du 18/05/2025 |
| CHG-013 à 017 | 4 arbres abattus, 5 plantés (parc est) | 10/05/2022 → 09/08/2024 | parc est, dont (143 ; −57) | végétation | hauteurs LiDAR 2021 non valables | idem |
| CHG-018 / 021 | noue et cœurs d'îlot du quartier est | 09/08/2024 → **08/2025** (fin de la fenêtre Pléiades, tant que sa date est inconnue) | x 118..147, y −52..−40 ; x 100..150, y 5..95 | sol, végétation | T est 15 jours après la `date_min` : état du 09/08/2024 (terre nue, lits minéraux) retenu avec `confiance: moyenne` ; certain là où les photos du 24/08/2024 voient encore l'état d'avant (`date_min` portée au 24/08/2024) | **incertain** : Pléiades et GAM daté, à vérifier |
| CHG-019 (non observé) | travaux annoncés sur l'avenue du Vercors | 01/04/2025 → 30/11/2025 | x −10..56, y −150..−5 (4 338 m², jusqu'à 7,7 m du centre) | toutes | **sans objet** (T est avant) ; photos du 18/05/2025 admises seulement dans la zone rognée par observation négative | T dans l'intervalle : **incertain** sur 18,5 % du cœur, à rogner (lot 1b) |
| SURF-0344 (audit § 2.5) | terre-plein arasé et peint à niveau | 12/08/2021 → 18/05/2025 | `surf_0344` (`decrire/surfaces.py:91-94`) | géométrie, Z | à dater sur l'ortho 2022, l'IGN 2024 et les photos du 24/08/2024 (lot 1b) | arasé (photo du 18/05/2025) |
| TRV-C1-2025 | travaux du carrefour, arrêts La Revirée relogés | 23/06/2025 → 05/12/2025 | `marquages_sources.zones()` (plan CAO dilaté de 3 m), plus `relief_zones_2026`, plus `zone_travaux_2025`, marge de 3 m | toutes | toute preuve postérieure au 22/06/2025 non valable dans l'emprise | idem |
| TRV-VERCORS-TROTTOIRS | trottoirs du Vercors | 23/06/2025 → 30/01/2026 | ±15 m autour de l'axe | géométrie | idem | idem |
| OBS-… (observations négatives) | zones vues inchangées | une date chacune | polygones de visibilité des poses acceptées | selon la vue | rognent les événements non observés | idem |

Format retenu :
- `recon/pcg/etat/etats/avant_travaux.evenements.geojson`, en L93 ;
- propriétés : `id`, `date_min`, `date_max`, `observe_post`, `familles`, `observe`, `confiance`, `marge_m`, `preuve`, `type` (`evenement` ou `observation_negative`) ;
- il est produit en phase 1 (lot 1b).

La planche `revision/chg019_coeur_poses.jpg` montre l'emprise de CHG-019 au cœur, sur l'ortho 2022, avec les 45 poses. On y voit :
- l'emprise englobe la bretelle SE, son îlot et les traversées sud ;
- les poses du 18/05/2025 sont toutes sur l'axe Verdun NE → SO ;
- 6 poses du 24/08/2024 (5 calées sur bordures GAM, 1 sur GCP) tombent dans CHG-019, à 135 à 143 m du centre.

### 2.2 Statut des sources communes (T = 24/08/2024 ; écarts pour le 18/05/2025 entre parenthèses)

| Source | Date | Statut |
|---|---|---|
| Ortho PCRS 5 cm (`ortho5cm_2022`) | 10/05/2022 | **référence géométrique** hors CHG-001 à 006 et hors marquages de CHG-008 |
| PCRS vecteur (`gam_*_pcrs`) | 2019 (`date_leve`) | bordures et limites, précision 10 cm, hors EVT-2019-COLAS non vérifié. Seule source vectorielle de l'ancienne bretelle SE, de la contre-allée et du bord ouest de l'ancien îlot du tourne-à-droite (n° 28). Périmé sur 432 m sur 4 192 (CHG-001 à 004). |
| LiDAR HD, COPC `LHD_FXX_0917_6461` | 12/08 et 06/09/2021 | relief, vues de bordure, hauteurs des mâts et des arbres, hors CHG-001 à 004, 013 à 017 et SURF-0344 ; contrôle réservé : lignes de vol du 06/09 contre celles du 12/08 |
| BD ORTHO IGN 2024 (RVB et IRC) et CRAIG ortho 2024 | 09/08/2024 | **référence d'aspect du site à T − 15 j** ; géométrie là où 2022 n'est pas valable (±0,1 à 0,2 m). Prouve une présence, jamais une absence : elle donne de faux absents sur les pavés jaunes délavés et la flèche TAD SO. |
| Pléiades 2025 | entre le 03/05 et le 08/08/2025 | contrôle de persistance des masses après T, hors CHG-006, 018 et 021 (50 cm, recalée de +0,47 / +1,17 m). À contrôler par la SPOT du 25/06/2025 et à faire dater par l'IGN / DINAMIS. |
| Levé GAM `Meylan_Topo.dwg` (= `etat_2026` = `gam_topo_sol_*` = `data/vector_gz/gam`) | mosaïque non datée | admissible tronçon par tronçon selon sa classe de datation et la règle des 0,10 m dans TRV-C1 (§ 2.3). Jamais en bloc. |
| OSM « attic » | **24/08/2024 (à télécharger, lot 1g)**, 01/06/2024 et 01/06/2025 (présents) | topologie, arrêts, feux, traversées. Prouve une présence, pas une absence : les lampadaires passent de 23 à 38 puis 43 par simple enrichissement de la carte. |
| BD TOPO | extrait actuel du dépôt (`vector/bdtopo_batiment.geojson`) | 22 emprises anciennes (2012) ; les 12 emprises du quartier est sont créées le 04/07/2025 par « Processus IA métrique », sans hauteur. **L'édition 2025-03-15 n'est pas téléchargée** : elle ne les contient pas. |
| Levé GAM, bâtiments du secteur est | mosaïque | 111 lignes `batiment_lin`, 38 escaliers et rampes, 18 talus dans la boîte x 37..156, y −67..92 ; admis là où l'IGN 2024 et les photos du 24/08/2024 les confirment |
| Photos Panoramax et Mapillary | 2022 → 22/06/2025 | type, existence, matériaux, aspect, validation. **Poses à recalculer** (lot 1i). |
| **Exclues** | — | `plan_projet_2025` (sauf comme emprise de TRV-C1 et jeu témoin du lot 1c) ; paquet v1 dans l'emprise ; `osm_*` actuels ; heightmap « 3025 » ; `.xodr`, `lanes` et `manoeuvres` 2026 ; `assets/specs/{panneaux,feux}.json` (inventaires 2026) ; sources interdites du § 2.8 |

### 2.3 Sol : bordures, surfaces, îlots, nivellement

| Attribut | 1 | 2 | 3 | 4 | Contrôle | Précision mesurée |
|---|---|---|---|---|---|---|
| Bordure en plan, **dans TRV-C1** (emprise des travaux, où PCRS et GAM s'écartent de 25 cm en médiane entre 35 et 80 m, 54 % à ≤ 0,30 m) | PCRS 2019, hors événements 2019-2022 | Crête LiDAR 2021, puis contour sur l'ortho 2022 (`sol/pilote/ilot_coeur.py`) | Ligne GAM **seulement** si son arête coïncide à < 0,10 m avec une arête de rang 1 ou 2 (elle sert alors à affiner) | IGN 2024 (CHG-003, CHG-004) | Photos 2024-2025 aux poses recalculées | contour ortho / GAM p50 4,7 cm, p90 12,3 cm |
| Bordure en plan, **hors TRV-C1** | Ligne GAM `relief_2021` ou `arasee_visible` ; `apparue_2022_2024` dans CONSTR-EST si l'IGN 2024 la confirme | PCRS 2019 hors CHG-001 à 004 | Crête LiDAR 2021, contour ortho 2022 | IGN 2024 | Photos | GAM / PCRS p50 3,5 cm hors travaux (99 % à ≤ 0,30 m entre 35 et 80 m) |
| Classes GAM à revoir | `relief_seul` (449 m), `terrain_remanie_2021` (1 298 m), `masquee` (457 m) : **revue sur planche obligatoire** à ±80 m, conservées au-delà avec `confiance: faible` | `absente_avant` : rejetée (4,7 %) | — | — | Jeu témoin du lot 1c | fausse alarme 2,2 % (témoin PCRS 2019) ; rappel à mesurer |
| Bordures absentes de tout vecteur | îlots IA-1 (7,02 m²) et IA-2 (22,26 m²) du cœur ; séparateur de Verdun NE (62 % non levé) ; 13 crêtes sans ligne (≈ 433 m) | si le dessus est en enrobé : crête décalée de 0,27 m vers l'intérieur, ou profil sur le LAZ | — | — | 2 photos 2024-2025 | anneaux G1 fermés, rayon ≥ 0,30 m |
| Vue (hauteur) et abaissés | Profils sur les **points LiDAR 2021** (LAZ), tous les 1 m | `bordures_hauteurs.h_lidar_2021_m` (heightmap 16 bits, p50 0,9 cm) | MNT JPEG (p90 6,3 cm), `conf: moyenne` | règle du profil (`a_priori`) | Abaissé = trou de crête et vue < 4 cm sur ≥ 0,8 m, recoupé par les chartières et la fin des zébras de 2022 | Pilote B : abaissé à ≤ 0,12 m des chartières |
| Nivellement Z | Sol nu LiDAR 2021 (classe 2), flottant à 10 cm | Surfaces de conception (dévers de 1,5 à 2 %, fil d'eau continu, avaloirs) calées sur ce sol nu | **Quartier est** : récolements VRD des Saules Blancs (Q3), sinon triangulation de points de sol sur les 25 photos 360° du 24/08/2024 dans le secteur, sinon conception raccordée, **comptée dans S2b** | — | G3 sur blocs réservés (§ 4.2) | heightmap / points : z p50 0,6 cm |
| Matériaux | Signatures de l'ortho 2022 (grain, ExG, R−B, luminance) et intensité LiDAR | Photos 2024-2025 | IGN 2024 (reprises CHG-009 à 011) | `a_priori` signalé | — | galets / enrobé : grain 6,9 contre 2,2 |
| Remplissage des îlots | Îlots du cœur : **galets** (photos 119d9094 et 31d16b8e du 18/05/2025, valables à T) ; goutte NE : **terre et herbe** (constat coeur-31) | — | — | — | — | v2 2026 : gravier et BRF, faux |
| Âge (usure) | relatif à T : reprises 2024 = récentes ; chaussées de Verdun refaites en mars-avril 2019 = 5 ans ; quartier est = neuf ; le reste = ancien | — | — | — | — | — |

Règles de construction, reprises des pilotes de `sol/` :
- un **graphe planaire unique**, où le trou d'une chaussée est l'anneau même de l'îlot ;
- des chaînes G1 dont chaque extrémité est un nœud typé (anneau, chartière, T, raccord), avec troncature à ≤ 0,10 m aux jonctions de sources ;
- un abaissé est un **intervalle de vue**, jamais un trou dans la bordure ;
- toute zone non décrite devient une face explicite.

### 2.4 Marquages

| Attribut | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Géométrie | **Ortho PCRS 2022** ajustée aux gabarits (pilote `marquages/pilote/`) : flèches 1 à 2 cm, zébras < 1 cm, largeur des traits −1,1 cm de biais | GAM seulement s'il est `present_identique` en 2022 à < 0,10 m | IGN 2024 et ortho-photos tirées des 360° calées (CHG-008, CONSTR-EST, CHG-003), ±0,1 à 0,2 m | règles d'inférence (`MARQUAGES.md` § 4.3) |
| Type | PCRS si l'IoU est ≥ 0,60 et la marge de type ≥ 0,05 | photos 2024-08 et 2025-05 projetées | GAM coïncident | affectation des voies de 2022 (jamais OpenDRIVE 2026) |
| Existence à T | photos du 24/08/2024 (et du 18/05/2025 hors événements) | IGN 2024 (présence seulement) | persistance depuis 2022, vérifiée sur 11 passages et 7 flèches, **à la précision de l'IGN 2024** (±0,1-0,2 m ; écart maximal mesuré 0,18 m) | — |
| Usure, aspect | photos 2024-08 | contraste de l'ortho 2022 (médiane 0,42) | — | — |

Exclusions :
- le plan 2025 (52 marques de la v2) ;
- le zigzag du quai de Verdun SO du levé GAM (45 m et 72 m, absents en 2022 comme en 2024) ;
- les passages de la Revirée et du sud du levé, décalés de 0,35 et 0,39 m ;
- les 6 lignes d'effet des feux ajoutées en 2025.

**Marques v1 et fantômes : des germes, pas une réintégration en bloc.**
- Les 109 `retire_fantome` et les 309 marques v1 « retire » de la v2 servent de **germes de détection** seulement. Chacune est ré-ajustée sur l'ortho 2022 (IoU ≥ 0,60), puis filtrée par `E.valide`.
- La v1 mêle GAM 2026, plan 2025 et ortho 2022 : ses bandes s'écartent de 11,2 cm en médiane et de 41 cm au p90.
- Sur les 690 marques v1 de référence, 79 sont dans CHG-008 et 67 dans CHG-002 / 003, donc non valables à T, sauf confirmation par l'IGN 2024 ou les photos. 66 autres tombent dans CHG-019, incertaines si T = 18/05/2025.

Gabarits « site », à vectoriser une fois :
- `TRIDENT_SITE` ;
- flèches NE étroites ;
- logo vélo à roues évidées ;
- « 50 » et « 30 » cerclés ;
- pavé jaune 2022 de 0,40 × 0,49 m au pas de 0,589 m (et non le gabarit Chronovélo 2025 de 0,70 × 0,37).

Cas réglé : la flèche B-FL01 se pose en TD_TAD (photos de 2023, 2024 et 2025).

### 2.5 Objets : signalisation, feux, mobilier, réseaux

Base : `objets/objets_avant_travaux.geojson`.
- 759 objets : 471 présents, 219 présumés, 69 incertains ;
- 97 exclus, chacun avec sa raison ;
- origine des positions : 684 de la description 2026, 57 de Mapillary seul, 17 d'observations V2, 1 d'OSM 2025. **113 des 684 sont dans l'emprise des travaux.**

| Attribut | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Position | Triangulation sur photos d'avant travaux aux poses recalculées (≥ 3 vues, angle ≥ 20°, σ ≤ 0,25 m) | Mât LiDAR 2021 (σ 0,15 m) hors CONSTR-EST | Ortho 2022 (σ 0,25 m) | OSM à T ; au 20/06/2025 pour les objets relogés par les travaux | Description 2026 **hors emprise seulement** ; Mapillary seul (σ 3 m) avec contraintes d'implantation dures |
| Existence | Photo ou ortho datée et valable à T | Détection Mapillary jointe à LiDAR, OSM ou GAM | OSM d'avant travaux (présence seulement) | — | — |
| Orientation | Mapillary `aligned_direction` (azimut L93 = azimut vrai − 2,0086°) | Annotations Panoramax du 18/05/2025 (face ou dos) | Règles SIG-04, FEU-05, ECL-02 | — | — |
| Z, hauteur | MNT 2021 (l'ancienne chaussée a été rehaussée en 2025) | Hauteur LiDAR 2021 (334 objets), puis amas de classe 1 de plus de 3 m dans le COPC pour les mâts | Triangulation du sommet | Défaut par type | — |

Points imposés :
- **Les 113 objets de l'emprise positionnés depuis la description 2026 sont triangulés ou confirmés sur le LiDAR 2021 ou l'ortho 2022 avant la jonction de la phase 2.** Parmi eux, les 11 supports de feux, tous positionnés depuis la description 2026 : 6 « existant (inchangé) », 4 « déduit 2026 (à vérifier) », 1 « à vérifier ».
- **Arrêts La Revirée** à leur position d'avant travaux. Les travaux ont déplacé l'arrêt SE de 36,8 m vers le SO et l'arrêt NO de 18,1 m vers le NE ; on applique le déplacement inverse.
- Le poteau d'arrêt SE (`node/6569621813`), les deux traversées à feux (`node/1722505401`, `node/6569621810`) et le nœud de feux `1959011179`, supprimés d'OSM après le 20/06/2025.
- 11 supports de feux et 21 panneaux à moins de 60 m du centre.
- Les 22 objets d'emprise absents de la v2 2026 et les 53 objets hors emprise qu'elle oublie (22 lampadaires, 12 panneaux, 5 poteaux).
- Exclus : les 26 objets ajoutés par les travaux, dont 14 arbres plantés en 2025.
- `feu_SW_TPC` reste incertain : aucun mât n'est visible sur les vues de 2024 et de 2025.
- Si T = 24/08/2024 : clôtures de chantier et bungalows de CHG-006 et 007, base vie SE (CHG-005).

Visibilité au cœur (68 objets hors arbres et clôtures) :
- 83,8 % sont visibles sur au moins 2 poses **acceptées** (calcul géométrique, sans la végétation) ;
- 69,1 % sont réellement détectés sur au moins 2 images.

Le 85,3 % cité auparavant comptait 6 poses Panoramax rejetées (5 du 01/05/2024, 1 du 18/05/2025).

Ponctuels au sol : tampons et avaloirs relevés sur l'ortho 5 cm. Il n'y en a aucun dans la v2 aujourd'hui (QUALITE a5).

Inventaires d'état : `sources/inventaires/{panneaux_avant,feux_avant}.json`, hors `assets/specs`.

### 2.6 Végétation

| Élément | Source primaire | Contrôle | Règle de chronologie |
|---|---|---|---|
| Arbres (466) : position | Levé GAM `arbre_pct` hors emprise, LiDAR 2021 et ortho 2022 | Photos 2024-2025, IRC 2024 | Poser les 10 arbres « absent 2026 » (présents avant) ; exclure les 14 plantés en 2025 et les 6 disparus avant T (`arbre_018`, `114`, `184`, `269`, `365`, `435`) |
| Arbres : hauteur et couronne | LiDAR 2021 | IGN 2024 | Pas de LiDAR pour CHG-013 à 017 ni pour les plantations du quartier est : ombres IGN 2024 (`changements/outils/soleil.py`) et photos |
| Arbres : essence | Le levé GAM ne donne que le bloc (`ARBRE_FEUILLU`…), pas l'essence : genre identifié sur les vignettes 2024-2025, sinon `a_priori` | Inventaire arboré de la Ville ou de la Métropole, s'il est publié (à rechercher en 1g) | — |
| Haies, massifs, gazons | Ortho 2022, IRC 2024, canopée COSIA 2024 | Photos du 24/08/2024 | Rive ouest du Vercors : pertes COSIA 2021-2024 **non confirmées**, à vérifier. La bande plantée du Vercors est un massif (terre nue en hiver), pas une perte. |
| Saison | fin août (variante : mi-mai) | Photos de la date cible | Plein feuillage ; état des gazons mesuré sur les photos (sécheresse estivale possible) ; règle `R-feuilles-automne` désactivée |

### 2.7 Contexte : bâtiments, périphérie, lumière

| Élément | Source primaire | Complément | Remarque |
|---|---|---|---|
| Emprises de bâtiments | BD TOPO de l'extrait du dépôt (22 emprises de 2012) ; **quartier est : lignes `batiment_lin` du levé GAM (111), confirmées par l'IGN 2024**, et 12 emprises BD TOPO « IA » | IGN 2024 | Aucune hauteur dans la BD TOPO ni dans le LiDAR 2021 pour le quartier est |
| Hauteurs | LiDAR 2021 (±1 m) hors CHG-001 | Quartier est : triangulation des acrotères sur les photos 360° du 24/08/2024 (référence de contrôle), ombres IGN 2024 (source) | Tolérance de ±1,5 m dans le quartier est, contrôlée sur les triangulations non utilisées comme source |
| Escaliers, rampes, talus du secteur est | Levé GAM (38 escaliers et rampes, 18 talus), datés par l'IGN 2024 | Photos du 24/08/2024 | Absents des versions précédentes du plan |
| Façades, toits | Photos de la date cible (type, couleur mesurée en ΔE) | IGN 2024 (toits, CHG-012 et 020) | Base vie SE présente (CHG-005) |
| Périphérie ≥ 500 m, horizon | BD TOPO et RGE ALTI, ou dalles LiDAR HD voisines (0916_6461, 0916_6460, 0917_6460) | — | C5 (§ 4.2) |
| Lumière | Éphéméride à la date et à l'heure de chaque photo (validation) ; date cible pour le niveau | Exposition dérivée de la luminance de la photo à même pose | Remplace le soleil d'octobre (220° / 29°) |

### 2.8 Licences et sources interdites

- **Sources interdites**, à lister dans `etat_cible.sources_interdites` et à contrôler par le lanceur : Google Street View, Google Earth, Apple Look Around, Bing Streetside et toute imagerie de rue commerciale. Jusqu'ici, seul `SOURCES.md` écartait Street View.
- **Photos de tiers** (Panoramax et Mapillary, CC-BY-SA 4.0) : jamais versionnées.
  - Planches et vignettes vont sous `v2_avant_travaux/photos_non_versionnees/`, y compris les planches photo / rendu de validation.
  - Seuls les JSON de mesure sont versionnés.
  - L'attribution passe par `meta.json`.
- **OSM (ODbL 1.0)** : `objets_avant_travaux.geojson` et `sources/osm_*/osm_*.geojson` dérivent en partie d'OSM. Il faut la mention « © contributeurs OpenStreetMap, ODbL » dans les `meta.json`, et le partage à l'identique de toute base dérivée diffusée hors du dépôt privé.
- **Plan projet 2025** (document public de la commune, droits du maître d'œuvre non précisés) : statut à clarifier. D'ici là, il sert seulement d'emprise et de jeu témoin, et les planches `*_plan2025.jpg` sont traitées comme des photos de tiers (phase 0).
- **City Sample** (contenu réservé à Unreal) : le MaterialX commun ne référence que `assets/lib` (CC0). Les variantes `MI_<id>__citysample` de `ue/materiaux/construire_materiaux.py` restent optionnelles côté UE et sont exclues des mesures M2 et V1. Le contrôle automatique exige « 0 chemin CitySample dans les USD de `fabrique_hda` ».
- **CARLA** (CC-BY) : attribution dans `meta.json`.

---

## 3. Changements du pipeline

### 3.1 Principe

- **Un état = une configuration** `etat_cible`. Ses champs :
  - `id`, `date_cible`, `date_etat`, `saison` ;
  - `evenements`, `sources`, `sources_interdites`, `v_temporelle_marquages`, `regles_chronologie` ;
  - `references`, `dossier_sortie`, `entrees_partagees`, `ue`, `schema_description`.

  L'id `avant_travaux` est indépendant de la date choisie en Q1. L'ébauche est dans `audit/proposition_etat_cible_avant_travaux.json`. Elle est **à corriger** sur six points :
  - le GAM est admissible par classe de datation, avec la règle des 0,10 m dans TRV-C1 ;
  - côté marquages, l'ortho 2022 passe avant le GAM ;
  - les événements sont ceux du § 2.1, avec les observations négatives ;
  - le COPC 2021 est disponible ;
  - l'arbitrage se fait par précision (§ 2.1) ;
  - la liste des sources interdites est ajoutée.
- **Sélection** : `PJ_ETAT=avant_travaux`, posé par un lanceur **avant les imports**, car les modules calculent leurs chemins à l'import (`commun.SORTIE`). Côté Houdini : `hython fabriquer_hda.py --etat …`.
- **Coexistence** : recommandée par **gel** de l'état 2026 (Q2). L'utilisateur pose une étiquette git sur le dernier commit 2026 ; `v2/` devient alors une archive en lecture seule, et l'exigence de non-régression à l'octet sur une base que l'autre workflow modifie encore disparaît. Si l'état 2026 est maintenu, voir le § 3.5, point 2.

### 3.2 Nouveaux fichiers (aucun fichier existant n'est remplacé)

| Fichier | Rôle |
|---|---|
| `recon/pcg/etat/etat_cible.py` | `charger()`, `E.dossier()`, `E.reference()`, `E.source()`, `E.valide(date, point, famille)` (avec observations négatives), `E.classe_date()`, `E.statut_objet()`, `E.age()`, `E.v_temporelle`, `E.source_interdite()` |
| `recon/pcg/etat/etats/avant_travaux.json` | configuration de ce plan (date fixée par Q1) |
| `recon/pcg/etat/etats/apres_travaux_2026.json` | seulement si l'état 2026 est maintenu : reproduit le comportement actuel (11 constantes héritées comprises) |
| `recon/pcg/etat/etats/avant_travaux.evenements.geojson` | table du § 2.1 |
| `recon/pcg/etat/etats/avant_travaux.regles.json` | surcharge des paramètres d'état des règles : `attendu_site` d'INF-FLE-004, applicabilité des LOC-*, GEN-07 « à rebours », SIG-04 sur les voies d'avant travaux, tolérances GQ-TOL-001 d'`ortho2024` (0,25 m) et de `leve_emprise` (0,10 m) |
| `recon/pcg/etat/lancer.py` | fixe `PJ_ETAT` puis exécute le module ; refuse d'écrire dans un dossier dont `etat_cible.json` a un autre `id` |
| `recon/pcg/etat/controle_licences.py` | avant commit : 0 image de tiers versionnée sous `v2_avant_travaux/` (d'après les manifestes et les motifs), 0 chemin CitySample dans `fabrique_hda`, 0 source interdite citée |
| `recon/pcg/etat/tests/test_valide.py` | tests de la fonction de validité (critères de la phase 0) |
| `recon/pcg/etat/sources/{mnt_2021.py, evenements.py, lignes_2022.py, xodr_avant.py, masque_chaussee.py, leve_emprise.py, osm_historique.py, inventaires_signalisation.py}` | producteurs des entrées propres à l'état (phase 1) |
| `recon/pcg/etat/sources/poses_etat.py` | **solveur de poses autonome** (lot 1i) : réutilise les modèles de caméra par import, mais lit les GCP de l'état et le MNT 2021, et n'utilise ni `marquages_2026` ni `z_sol` 2026 |
| `recon/pcg/decrire/datation_leve.py` | datation GAM tronçon par tronçon, promue depuis `sol/pilote/dater_gam.py` et `marquages/pilote/datation_gam.py` |
| `recon/pcg/decrire/sol_graphe.py` | chaînes G1, nœuds typés, partition planaire (depuis `sol/pilote/{trottoir_abaisse, partition_A, ilot_coeur, geom_contours}.py`) |
| `recon/pcg/decrire/marquages_ortho_gabarits/` | détection et ajustement aux gabarits sur ortho, indépendants d'OpenDRIVE (depuis `marquages/pilote/{detection, zebras, fleches, lignes, damiers}.py`) |
| `recon/pcg/decrire/objets_etat.py` | fusion des objets à T (depuis `objets/scripts/inventaire.py`) |
| `recon/pcg/validation/{planches_photo_rendu.py, mesures_realisme.py}` | P4, M2, M3, L1, V1 automatisés (depuis `qualite/outils/`) ; les planches vont dans `photos_non_versionnees/validation/` |
| `assets/specs/marquages_gabarits_site.json` | gabarits « site » (nouveau fichier ; `marquages_geometrie.json` reste intact) |

### 3.3 Organisation des sorties

```
recon/out/paquet_jardin/
  package/                     paquet v1 (état 2026) : lecture seule
  v2/                          état 2026 : gelé (Q2) ou inchangé (apres_travaux_2026)
  v2_avant_travaux/            état avant travaux (avant_travaux)
    etat_cible.json            copie figée ; son sha256 est cité par chaque manifeste
    inventaire/                inventaires du 11/10/2026 et révision (ce dossier)
    sources/
      evenements/              evenements.geojson (copie figée de la table)
      relief/                  dtm_sol_2021_10cm.tif (non versionné), heightmap_avant_10cm.{png,json}, masque_chaussee_avant.geojson
      lignes_2022/             lignes longitudinales du site extraites de l'ortho 2022 (lot 1j)
      opendrive/               paquet_jardin_avant_travaux.xodr, lanes_avant_travaux.geojson, manoeuvres_avant_travaux.json
      leve_emprise/            bordures et limites reconstruites (PCRS 2019, LiDAR 2021, ortho 2022), avec leur classe de datation
      osm_2024-08-24/          couches osm_* découpées (ODbL)
      inventaires/             panneaux_avant.json, feux_avant.json
      poses/                   poses_etat.json : les 45 poses recalculées et les nouvelles, Δpose par rapport aux poses 2026
    description/{base, regularisation, coherence, enrichi, resolue/{base,objets}, controle_sol}/, description_scene_v2.json
    enrichi/recensement/obs_reliees.json   observations re-datées (valide_cible) et ré-appariées ; JSON seulement
    fabrique_hda/              USD, points, prototypes, manifest_fabrication_hda.json (fabriqué depuis description/resolue/base)
    controle/                  rapport_regles.json, RAPPORT_REGLES.md, rendu/, mesures_realisme.json
    validation/                mesures JSON seulement (P4, M2, M3, L1, V1, V2)
    ue_pilote/                 captures et mesures UE de l'état (rendus seulement)
    photos_non_versionnees/    vignettes, planches photo | rendu | superposition, grilles de revue (ignoré par git)
```

Les poses 2026 sont lues depuis `v2/`, en lecture seule, comme **points de départ** du solveur : `enrichi/poses/poses.json` et `enrichi/recensement/mapillary/poses/poses_mapillary.json`. Les poses de l'état sont écrites dans `v2_avant_travaux/sources/poses/`.

Non versionnés :
- `photos_non_versionnees/` ;
- le COPC ;
- le MNT flottant.

`.gitignore` (phase 0, à faire par une passe autorisée à le modifier) : les motifs de photos de tiers ne visent aujourd'hui que `v2/` (lignes 40 à 66). Il faut les dupliquer pour `v2_avant_travaux/` (ou les écrire en `v2*/`) :
- `enrichi/**/*.jpg`, `enrichi/recensement/**/*.png` ;
- `description/coherence/**/*.jpg`, `description/resolue/planches/*.jpg`, `description/enrichi/arbitrages/*.jpg` ;
- `**/planche_photos*.png`, `**/planche_panoramax*.png` ;
- `validation/**/*.{jpg,png}`.

Unreal :
- niveau `/Game/PJ/Maps/PJ_AvantTravaux` ;
- données de l'état sous `/Game/PJ/Etats/AvantTravaux/{Import,PCG/Donnees}`. Aujourd'hui, `/Game/PJ/Import/Sol` et `/Game/PJ/PCG/Donnees/PDA_*` sont uniques, d'où un risque de collision ;
- partagés : `/Game/PJ/{Lib,Materials,Textures}` et les graphes PCG.

### 3.4 Modifications fichier par fichier

Le détail complet, avec effort et risque, est dans `audit/AUDIT_PIPELINE.md` § 5 et dans `audit/occurrences_cablees.csv` (1 505 lignes dans 157 fichiers). Ce tableau en retient les décisions.

| Module | Fichier : lignes | Changement | Phase |
|---|---|---|---|
| schema | `description_scene_v2.schema.json:5, 13, 23, 122-123, 251, 269-270, 300, 314, 425` | Version 0.4, **ajouts seulement** : `date_etat` en motif `^\d{4}-\d{2}$` ; `src` ortho2024, pleiades2025, mapillary:<id>, photo:<plateforme>:<id>, leve_emprise ; `z_ref` nivellement_avant_travaux ; âge relatif à T (`neuf`) | 0 |
| decrire, socle | `commun.py:21-28` (SORTIE), `:121-126` (MNT) | `SORTIE = E.dossier("description")` (19 modules suivent) ; `MNT = E.reference("mnt")` | 0 |
| decrire, socle | `composer.py:34-54, 62-74, 121-122, 207-209` ; `valider.py:11, 25, 309` ; `contexte.py` (sources v1 et OSM) | Références, saison et `date_etat` tirées de `E` ; manifeste `etat_cible {id, sha256}` ; OSM à T | 0 |
| decrire, sol | `sol_site.py:61-84` (`gam_lignes`), `:88-101`, `:113-120`, `:183-201`, `:252-300`, `:344`, `:385-405` | GAM filtré par classe de datation et par la règle des 0,10 m dans TRV-C1 (`datation_leve.py`) ; ajout de `pcrs2019` et `leve_emprise` ; masque de chaussée, passages et OSM d'avant travaux ; voies d'avant travaux | 2 |
| decrire, sol | `bordures.py:16-17, 134-139, 254-269, 558-563, 631, 669, 731-741, 747-811, 942-959, 1054-1061` | Séparer les trois cas mélangés en `558-563` (quartier est, modifiée 2025, plan projet) ; vue = `h_lidar_2021_m` ; `z_ref` d'après `E` ; âge relatif à T ; constats du 24/08/2024, du 12/01 et du 18/05/2025 classés par `E.valide` | 2 |
| decrire, sol | `surfaces.py:12-20, 57-94, 259-263, 741-765, 880-941` ; `ilots.py:28-50, 136-157, 264-266, 443-444` ; `sol_lacunes.py:254-270` | Tables matériau et âge indexées par l'âge à T ; constats (`surf_0121`, `surf_0344`) et remplissages par état (galets au cœur, terre et herbe sur la goutte NE) ; masques d'après `E` | 2 |
| decrire, sol | `sol_composer.py:6, 25-37, 74` ; `nivellement_xodr.py` ; `regulariser.py:55-57, 84-88, 232-236` | Références d'après `E` ; `.xodr` d'avant travaux ; tolérances de la surcharge | 2 |
| decrire, sol | **nouveau** `sol_graphe.py` branché après `regulariser` | Partition par graphe planaire et contrôles bloquants (T1) | 2 |
| decrire, marquages | `marquages_sources.py:1-24, 35-51` ; `ctl_detection.py:323-336` (FUS-SRC-001 codée en dur) | Tables `SOURCES` et `V_TEMPORELLE` lues dans `E` (même table aux deux endroits) ; `plan2025` = 0 ; l'ortho 2022 passe devant le GAM | 0 |
| decrire, marquages | `marquages.py:66-73, 108-120` ; `detection_indices.py:55-57` ; `detection_commun.py:29, 37-60` ; `marquages_commun.py:23-25` ; `marquages_contraintes.py:21` ; `marquages_chronovelo.py:29` ; `marquages_inference.py:191` ; `marquages_lignes.py:1125` ; `xodr_echantillonne.py:39-40` (chemins `paquet_jardin_2026.xodr` et `lanes_2026.geojson` en dur) ; `marquages_indices_v1.py` ; `marquages_verifier.py`, `marquages_controles.py` | Rasters `ortho2022` et `ortho2024` (lecteur à 20 cm) ; bordures de l'état et non `etat_2026` ; pavés jaunes 2022 détectés au lieu du plan 2025 ; manœuvres et `.xodr` d'avant travaux ; indices v1 comme germes seulement ; intégration de `marquages_ortho_gabarits/` | 2 |
| enrichir | `fusion_recensement.py:47-58, 61-79, 86, 96-140, 877…3900` | **Réécriture de la logique de date** : `valide_cible` calculée au chargement (`E.valide`) ; classes relatives à T ; règles FUS-* paramétrées ; `absent_cible` ; ré-appariement de `lien_description` (identifiant stable hors emprise, sinon appariement spatial FUS-LIEN-04/06) | 3 |
| enrichir | `gcp.py:3-10, 37-38, 65-72, 131, 146-170, 206` ; `camera.py:221-222` (`z_sol` = MNT 2026) ; `mapillary.py:68, 732, 764, 782, 950, 1466-1485` ; `orthos_recentes.py:47-53, 1275-1377` ; `projection.py:7, 21, 195` ; `triangulation.py:149, 206-208, 358-404` | **Phase 1 : aucune modification** ; le solveur autonome `etat/sources/poses_etat.py` lit les GCP de l'état. Phase 3 : bornes tirées de `E.evenements`, `validite_2026` remplacée par `E.valide`, MNT de l'état, recalage Mapillary sur les bordures **de l'état** et jamais sur le GAM dans TRV-C1 | 3 |
| decrire, cohérence | `coherence.py:7-29, 88-115, 158-169, 536-564, 859-972, 1019-1058` ; `coherence_objets.py:24-27, 86-224` ; `coherence_carte.py` ; `coherence_mesures.py` ; `coherence_photos.py:43, 67-68` ; `coherence_verifs.py` ; `coherence_poses.py` ; `coherence_presence.py` ; `coherence_politique.py` ; `coherence_sorties.py:568-579` ; `coherence_marquages.py:600-612` ; `coherence_ombres.py:53` | Q3, Q4 et Q8 relatives à T, sur photos valables à T ; `a_verifier_terrain2026` devient `a_verifier_archive` (une visite est impossible pour un état passé) ; chemins d'après `E` | 4 |
| decrire, résolution | `resoudre.py` ; `resoudre_sources.py` ; `resoudre_regles.py:11-129` ; `resoudre_objets.py` ; `resoudre_marquages.py` ; `resoudre_ajouts.py` ; `resoudre_revue.py` (verdicts codés en dur) | Textes et seuils RES-* paramétrés par T (RES-EXI-002 devient « événement intercalé ») ; stations de terrain remplacées par des archives ; verdicts de revue sortis dans un fichier de données par état | 4 |
| houdini | `fabriquer_hda.py:44-46, 550-558, 689-701` | `--etat` et `--description` ; fabrication depuis `description/resolue/base` | 0 |
| houdini | `fabriquer_hda.py:431-473` (`ecrire_materiaux`) ; `controle/rendre_controle.py:40-45` | **MaterialX texturé unique**, porté depuis `pj_materiaux.py`, qui ne référence que `assets/lib` ; le rendu de contrôle compose toutes les couches ; HDRI ou ciel physique, courbe de tons standard | Q, G0, 5 |
| houdini | `hda/pj_sol/construire.py:67, 197-248` ; `hda/pj_bordure/construire.py:361-372` ; `pj_decals.py:114-124` ; `pj_ilot` (`eclats_debordement`) | Suppression du flou de Z et du retrait des « falaises » ; sol posé sur des surfaces de conception ; épaufrures sur les arêtes, sans sphères ; aucun pontage ni éclat sans preuve. **Préalable à toute réutilisation des HDA.** | Q, G0 |
| houdini | `pj_commun.py:5, 26-30` ; 7 scripts de contrôle et d'essai avec des chemins `v2` (`controles_f1.py`, `rendre_marquages.py`, …) | Chemins tirés de `E` | 0 |
| controle | `ctl_commun.py:25-33, 592-652` ; `verifier_regles.py:41-47` | `--etat` ; références et GAM filtré d'après `E` | 0 |
| controle | `ctl_marquages.py:406, 656-660, 735-840, 917-926` ; `ctl_sol.py:518, 759, 1076, 1495-1528, 1762-1771` ; `ctl_reseau.py` (VAL-XOD-008, fichier modifié depuis l'instantané) ; `ctl_detection.py:30-46, 120-303, 473-556` | Attendus de site lus dans la surcharge ; VAL-KRB-005 contre le levé admissible ; règles « plan2025 » marquées « non applicables à l'état » ; ortho 2024 en plus | 6 |
| controle | **nouveau** : famille `realisme_validation` | P4, M2, M3, L1 et V1 rapportés par `verifier_regles.py` (dans la surcharge d'état, sans modifier `regles_conception.json` tant que l'autre workflow y travaille) | 6 |
| ue | `pilote/pilote.py:8-9, 67` ; `pilote/ue/niveau_2026.py` ; `pj_tools/eclairage.py:28-35` ; `contexte/*.py` (chemins `v2/ue_pilote`) ; `contexte/preparer_usd.py:5-11, 60-73, 262-284` ; `vegetation/arbres.py:140-143` ; `feuilles.py`, `pg_herbe.py`, `carla_feuillage_automne.py` ; `materiaux/construire_materiaux.py` (variantes `__citysample` optionnelles) | Niveau, soleil, saison et racines de contenu d'après `E` ; **import de la fabrication HDA du site entier, sans v1** (au lieu de `fabrique_ue_snapshot`) ; arbres filtrés par statut à T ; feuillage de la date cible | 7 |
| specs | `regles_conception.json` (42 règles sur 255 datées), `regles_locales_meylan.json` (14 sur 46), `regles_implantation.json` (`etat_cible` « octobre 2026 »), `regles_qualite_geometrique.json` (GQ-TOL-001) | **Aucune modification** : paramètres d'état dans la surcharge. `bordures`, `vegetation`, `mobilier` et `carla_correspondances` restent intouchés (autre équipe). | 0 |
| docs | `ARCHITECTURE.md` § 0, 1.3, 1.5, 1.6 ; `README.md` | Section « États cibles » ; suppression de « aucune image après travaux » comme hypothèse de base | 7 |

### 3.5 Garde-fous de coexistence

1. Chaque manifeste (description, fabrication, contrôle, UE) écrit `etat_cible {id, sha256}`. Le lanceur refuse une écriture croisée, et l'absence de `PJ_ETAT` dans un dossier `v2_avant_travaux` est une erreur.
2. **Gel recommandé** (Q2) : étiquette git posée par l'utilisateur, `v2/` en lecture seule, aucune exigence d'octet.
   - Si l'état 2026 est **maintenu**, la configuration `apres_travaux_2026` reproduit à l'octet `hash_description`, `hash_marquages`, `manifest_fabrication_hda.json` et `rapport_regles.json`, **mesurés sur un commit figé de l'autre workflow** et non sur une base en mouvement.
   - L'harmonisation des 11 dates de travaux reste une décision séparée.
3. Une exécution d'état ne sauvegarde jamais `paquet_jardin_pcg.hip` (seul `--construire-hip` le fait).
4. La phase 0, qui touche environ 60 fichiers partagés, se fait **après** la passe en cours de l'autre workflow sur `decrire`, `houdini`, `controle` et `v2`. Elle se fait en lots courts, sur une branche dédiée, sans édition concurrente, et après un relevé `sha1` comparé à `audit/instantane_code_sha1.txt`.
5. `controle_licences.py` tourne avant chaque commit qui touche `v2_avant_travaux/`.

---

## 4. Qualité : correctifs intégrés dès le départ et définition de « terminé »

### 4.1 Causes racines et correctifs

| Cause racine (`qualite/QUALITE.md`) | Constat mesuré sur la v2 2026 | Correctif intégré | Phase | Critère |
|---|---|---|---|---|
| RC1 Époque non contrôlée, sources mélangées | 419 bordures sur 504 issues du GAM post-travaux ; 154 marquages GAM, 52 du plan 2025 ; Z « MNT 2026 » ; bordures à ≤ 10 cm d'une arête 2022 : 84,8 % hors travaux, 58,6 % en zone de travaux ; poses calées sur GCP et MNT 2026 | Table d'événements et `E.valide` ; GAM par classe de datation et règle des 0,10 m ; plan 2025 et `etat_2026` exclus ; MNT 2021 ; poses recalculées | 0, 1, 2 | S1, P1, P4 |
| RC2 Rendu sans matériau ni contexte | 51 `UsdPreviewSurface` à albédo constant ; énergie de détail de la chaussée 5 à 8, contre 14 à 37 sur photo | MaterialX texturé unique Karma / UE (`assets/lib`) ; albédos calés sur photos datées | Q, G0, 5 | M1 à M3 |
| RC3 Sol tiré d'un MNT corrigé a posteriori | 4 passes de flou de 40 itérations ; 30 % des trottoirs au-dessus de 8 % sur 2 m ; pied de bordure − MNT p95 24 cm ; 76 cuvettes ; 11 m² de recouvrements ; quartier est régalé (e5) | Graphe planaire ; surfaces de conception calées sur le LiDAR 2021 ; ni flou ni retrait de triangles ; avaloirs décrits ; Z du quartier est tiré du récolement ou triangulé, sinon compté a priori | 1, 2, Q, G0 | T1, G2 à G5, S2b |
| RC4 Description limitée au sol | 0 sur 13 mâts de feux, 0 sur 29 têtes, 0 sur ≈ 30 panneaux posés ; bâtiments en trous | Objets, végétation et contexte décrits dès la phase 2 ; prototypes FR de feux et panneaux (piste Q) | Q, 2, 5, 7 | C1 à C4, OB1 |
| RC5 UE en patchwork v2 / v1 | v2 sur 71 × 100 m seulement ; v1 ailleurs (119 924 triangles de bordures en murs) | Import de la fabrication du site entier, 0 maillage v1, racine par état | 7 | U1 |
| RC6 « Terminé » = conformité aux normes | 13 poses Panoramax acceptées ; 2 planches photo / UE ; NCC des marquages médiane 0,35 ; premier rendu complet en fin de chaîne | Famille `realisme_validation` ; couverture spatiale par les vues ; planches automatiques ; revue en aveugle protocolée ; **porte G0** | 1i, G0, 6 | S3, P4, V1, V2 |
| RC7 Détails procéduraux sans preuve | Pontages aléatoires à 0,10 m/m² ; épaufrures en sphères ; 397 éclats | Usure, reprises et pontages **observés** seulement (ortho 5 cm, photos) | Q, 5 | M4 |
| Éclairage | Ciel (0,46 ; 0,50 ; 0,55) contre 0,65 à 0,94 sur photo ; dynamique 0,35 à 0,57 contre 0,80 à 0,95 ; soleil d'octobre | Soleil et saison de chaque photo pour la validation ; exposition dérivée de la luminance | G0, 5, 7 | L1, L2 |

À garder :
- la fidélité au tracé (p95 1,6 cm sur les lignes admissibles) ;
- la régularisation G1 et le déterminisme ;
- le look-dev du pilote ;
- les classes de surface, cohérentes avec l'ortho 2022 hors travaux (2,2 % d'aire incohérente).

Les poses calées ne sont gardées que comme points de départ du solveur.

### 4.2 Définition de « terminé »

Tout est mesuré automatiquement et rapporté avec sa valeur. **B** = bloquant (le rendu ne part pas vers l'utilisateur et la phase ne se ferme pas) ; **I** = indicatif (valeur publiée, écart justifié).

Résolution de référence des mesures image : 960 px pour 90° de champ, soit 10,67 px par degré.

| ID | B/I | Critère | Seuil | Mesure | Actuel (v2 2026) |
|---|---|---|---|---|---|
| **S1** | B | Chaque entité porte `date_validite` et des sources admissibles à T (`E.valide`) | 100 % ; 0 entité du plan 2025 ; 0 ligne GAM `absente_avant` ; 0 ligne GAM dans TRV-C1 hors règle des 0,10 m ; 0 source interdite | Script de provenance | 154 marquages GAM post-travaux, 52 du plan 2025, 139 `neuf_2025` |
| **S2a** | B | Classe ou matériau `a_priori` | ≤ 15 % de l'aire de sol ; matériau des bordures ≤ 10 % de la longueur à ±80 m et ≤ 35 % sur le site | Manifeste | 766 surfaces sur 1 410 ; bordures 499 sur 504 |
| **S2b** | B | Z `a_priori` | ≤ 5 % de l'aire circulée hors quartier est. Quartier est (16 % des surfaces circulées) : récolement ou ≥ 50 points de sol triangulés (σz ≤ 5 cm), sinon compté et signalé | Manifeste | quartier est entièrement régalé |
| **S3** | B | **Couverture spatiale** par des vues valables à T | Pour tout point de chaussée du cœur (r ≤ 60 m) : au moins 1 vue acceptée et valable en ce point à ≤ 25 m (critère QUALITE S3). Par branche, au moins 3 vues contemporaines (du jour de T ou séparées de T par aucun événement au point visé) : Verdun NE, Verdun SO, centre, Vercors, secteur est. Les vues de 2022-2023 ne comptent que hors événements. Exceptions documentées : la Revirée (aucune photo n'en remonte la branche depuis le 19/02/2020) et, si T = 18/05/2025, le Vercors (aucune photo après le 12/01/2025). | `poses_etat.json`, carte de couverture | non mesuré ; 20 vues à ≤ 80 m |
| S3n | I | Nombre de vues distinctes acceptées à ≤ 80 m | valeur publiée ; cible ≥ 25. Plafond : 33 photos uniques à ≤ 80 m entre le 24/08/2024 et le 22/06/2025 (15 + 5 + 13), plus 71 de 2022 à 05/2024 en perspective a priori | idem | 20 |
| **T1** | B | Topologie de la description | Σ aires = domaine ; recouvrement = trou = 0 (pixels de 2 cm) ; chaque bordure citée par 2 faces ; chaque îlot = 1 anneau fermé ; chaque extrémité de bordure sur un nœud typé | `sol_graphe.py` | 704 m² non décrits ; 11 bordures orphelines ; ceinture de I-0297 ouverte de 19,6 m |
| **P1** | B | Bordures et arête de l'ortho de référence (PCRS 2022 ; IGN 2024 dans CONSTR-EST et CHG-003 / 004) | PCRS : ≥ 90 % des échantillons de 1 m à ≤ 10 cm, ≤ 3 % sans arête, p90 ≤ 12 cm. IGN 2024 : ≥ 90 % à ≤ 25 cm. Bordures tirées du contour ortho (rang 3) : mesure sur **blocs spatiaux réservés** (20 %, non utilisés à l'extraction) | `qualite/outils/ecart_ortho2.py` | 84,8 % hors travaux ; 58,6 % en zone de travaux |
| **P2** | B | Marquages et image de référence | IoU ≥ 0,60 et marge de type ≥ 0,05 (sinon arbitrage photo) ; NCC ≥ 0,5 pour ≥ 90 % ; zébras : largeur 0,50 ± 0,01 m, résidu de pas < 3 cm ; tirets : phase p95 ≤ 0,10 m, latéral p95 ≤ 0,05 m | Pilote de marquages, VAL-IMG-007 | NCC médiane 0,35 ; 84 marques sur 194 sous le seuil |
| **P3** | B | Classes de surface et ortho | ≤ 2 % d'aire incohérente, **y compris** dans l'emprise des travaux | `qualite/outils/classes.py` | 2,2 % hors travaux ; non mesuré dans l'emprise |
| **P4** | B | Reprojection des arêtes valables à la date de la photo, **sur des arêtes réservées** (jamais utilisées comme GCP), après raffinement de pose | médiane ≤ 6 px (0,56°), p90 ≤ 12 px (1,1°). Le résidu de pose (validation croisée sans le point, `leave-one-out`) est publié à côté. Rappel : l'acceptation des poses tolère 0,5°, soit 5,3 px. | `validation/mesures_realisme.py` | non mesuré ; faux au cœur |
| P4f | I | idem, cible fine | médiane ≤ 3 px, p90 ≤ 8 px au cœur r ≤ 40 m | idem | — |
| **MQ1** | B | Couverture des marquages | ≥ 95 % des marques **valables à T** décrites. Référence : 20 tuiles de 10 × 10 m tirées au hasard dans la chaussée du site, annotées à la main sans voir l'extraction. 100 % des 11 passages, 7 flèches et 6 files de pavés du cœur. Longues continues reprises à ≥ 90 %. Le dénominateur « 576 sur 690 marques v1 » n'est plus utilisé : 79 de ces marques sont dans CHG-008 et 67 dans CHG-002 / 003. | `marquages/couverture_site.py` + annotation | auto non revu : 40 à 60 % |
| **OB1** | B | Position de la signalisation et des feux | **Seuil unique : écart de position ≤ 0,30 m** (triangulation σ ≤ 0,25 m sur ≥ 3 vues, ou LiDAR) pour 11 sur 11 supports de feux et 21 sur 21 panneaux à ≤ 60 m ; 0 objet à σ > 0,5 m au cœur ; les 113 objets d'emprise issus de la description 2026 triangulés ou confirmés | `triangulation.py` aux poses de l'état | 57 objets en Mapillary seul (σ 3 m) |
| **OB2** | B | Objets relogés et supprimés par les travaux | Arrêts La Revirée, poteau SE et traversées à feux à leur position d'avant travaux (± σ) ; 0 objet ajouté en 2025 | Comparaison avec `objets_avant_travaux.geojson` | v2 : 13 objets à la position 2026 |
| **G1** | B | Continuité G1 (bordures, limites, lignes) | 0 cassure > 2° hors coins voulus ; rayon ≥ gabarit | Règles GQ-* étendues aux limites | limites raster non régularisées |
| **G2** | B | Sol étanche | 0 trou > 0,005 m² ; 0 recouvrement > 3 mm ; 0 triangle retiré | TQ-SOL-009, compteur de falaises | 4 trous (0,16 m²) ; 11 m² de recouvrements |
| **G3** | B | Z contre le LiDAR 2021 hors événements, **sur données réservées** : surfaces calées sur la ligne de vol du 12/08/2021, contrôlées sur celle du 06/09/2021 dans les recouvrements, et sur 20 % de blocs non utilisés | Chaussée et trottoir − sol nu : RMS ≤ 3 cm, p95 ≤ 5 cm ; pied de bordure p95 ≤ 3 cm ; vue de bordure − LiDAR p95 ≤ 2 cm | TQ-SOL-013, VAL-KRB-005 | pied − MNT p95 24,2 cm ; vue p95 7,5 cm |
| **G4** | B | Pentes | Trottoirs : dévers de 1 à 3 %, pente sur 2 m ≤ 5 % pour ≥ 95 % de l'aire hors rampes ; 0 cuvette > 3 mm sans avaloir décrit | GA-TRO-004, VAL-SOL-009 | 30 % des trottoirs au-dessus de 8 % ; 76 cuvettes ; 0 avaloir |
| **G5** | B | Raccords de bordures | GA-BOR-005 à 100 % (pied ≤ 1 cm, tête ≤ 2 cm) | Contrôleur | 27 % |
| G6 | I | Échelle | Bâtiments : ±1 m au LiDAR (hors quartier est) ; quartier est : ±1,5 m contre les triangulations d'acrotères non utilisées comme source ; arbres : ≤ 15 % pour 90 %, aucun plafonnement | Comparaison des hauteurs | arbres plafonnés à 22-23 m dans UE |
| **M1** | B | Matériaux | 100 % des maillages visibles texturés (albédo, normale, rugosité), UV en mètres ; répétition : pic d'autocorrélation de la luminance de la chaussée ≤ 0,3 aux périodes de tuilage, sur 5 vues à 20-40 m | Contrôle USD et `mesures_realisme.py` | 0 sur 51 |
| **M2** | B | Rapports d'albédo, rendu contre photo à même pose | écart ≤ 15 % (bordure / enrobé, peinture / enrobé, remplissage / enrobé), sur ≥ 10 poses ; variantes City Sample exclues | `rapports_photos_rendus` généralisé | bordure / enrobé 1,01-1,21 contre 4,48 |
| M3 | I | Détail de la chaussée (énergie du laplacien) | rendu ≥ 60 % de la photo, bruit de rendu soustrait | M-C | 5-8 contre 14-37 |
| **M4** | B | Détails | 100 % des reprises et pontages visibles décrits, contrôlés sur l'ortho 5 cm **hors CHG-009 à 011** et sur les photos 2024-08 et 2025-05 projetées dans ces zones ; 0 détail non sourcé | Revue de provenance | pontages statistiques |
| **L1** | B | Ciel et dynamique | dynamique p99 − p1 ≥ 0,75 ; ciel à ±15 % (RVB) de la photo de même pose | M-C | 0,35-0,57 ; ciel gris |
| **L2** | B | Soleil, saison | azimut et hauteur à ±2° de l'éphéméride de chaque photo ; feuillage de la saison de la photo (deux états de végétation tant que la validation utilise les deux séances) | EXIF et calcul solaire | octobre contre mai et août |
| **V1** | B | Ressemblance sémantique à même pose | IoU par classe ≥ 0,7 pour le sol (chaussée, trottoir, îlot ; bordure élargie à 5 px) et ≥ 0,5 pour bâtiments et arbres, sur 12 vues (6 par séance). Photo : masques SAM (Apache 2.0, sans classe) étiquetés à la main ; rendu : image d'identifiants issue de la description. **Aucun modèle entraîné sur Cityscapes ou Mapillary Vistas** (licences non commerciales). | Planches photo / rendu / superposition (non versionnées) | 2 planches UE |
| **V2** | B | Revue indépendante en aveugle (ARCHITECTURE § 1.7), par un agent séparé sans accès à la description | (a) Grille 0-3 avec ancrages écrits sur 6 critères (géométrie au sol, marquages, matériaux, objets verticaux, végétation, lumière) : moyenne ≥ 2, aucun 0. (b) Choix forcé sur 12 poses : photo + 2 rendus (état T et état piégé : bordure décalée de 0,5 m, marque manquante ou objet déplacé), ≥ 11 sur 12 justes. (c) Accord de l'utilisateur. | Agent séparé | non faite |
| C1 | I | Bâtiments à T | 100 % posés, aucun trou de sol ; façade par type ; couleur moyenne ΔE2000 ≤ 10 contre la photo à même pose après normalisation d'exposition | Inventaire bâti / ortho | Karma 0 ; UE 34 boîtes |
| C2 | I | Végétation à T | 100 % des arbres retenus (statut à T) ; genre identifié pour ≥ 80 % des arbres du cœur (r ≤ 60 m), sinon `a_priori` ; saison de la date cible | `objets_avant_travaux` (arbres) | Karma 0 |
| C3 | I | Feux et signalisation verticale du site (hors cœur couvert par OB1) | 100 % des mâts, têtes et panneaux ; même seuil de position que OB1 (≤ 0,30 m) là où des vues existent | Inventaire de l'état | UE : 0 sur 13 mâts |
| C4 | I | Mobilier et réseaux | ≥ 95 % de l'inventaire, dont avaloirs et tampons | Idem | 58 objets, 0 avaloir |
| **C5** | B | Périphérie et horizon | Terrain, bâti et arbres simplifiés jusqu'à ≥ 500 m. « Bord du monde » = pixel de fond vide ou arête de terrain sous la ligne d'horizon : 0 pixel sur les 45 vues de validation et sur 8 vues d'horizon (tous les 45°, à 1,6 m de haut, depuis le centre) | Vues de contrôle | bord visible (n3) |
| **U1** | B | Niveau UE = fabrication du site | hash de description identique à Karma ; 0 maillage v1 | Inventaire des acteurs | v2 sur 71 × 100 m seulement |
| **U2** | B | Performance | ≥ 60 i/s en 1080p sur la RTX 5070 (Lumen) | `contexte_perf` | 68 i/s sur le pilote |
| U3 | B si 2026 maintenu | Coexistence | sorties 2026 identiques à l'octet sur un commit figé ; 0 asset UE partagé écrasé | Manifestes, chemins `/Game/PJ/Etats` | — |
| **D1** | B | Déterminisme | deux exécutions donnent des sorties identiques à l'octet | Manifestes | conforme (à garder) |
| **LIC** | B | Licences | `controle_licences.py` : 0 photo de tiers versionnée, 0 chemin CitySample dans `fabrique_hda`, attribution ODbL et CC-BY-SA présente | Script | — |

**Terminé** : tous les critères B sont au seuil, les critères I sont publiés avec leur écart justifié, V2 est passée et l'utilisateur donne son accord.

Aucun rendu ne part vers l'utilisateur tant que S1, T1, P1, P4, M1, L2 et V1 ne sont pas mesurés. La porte G0 les mesure une première fois sur le cœur.

---

## 5. Phases ordonnées

Ordre logique : données de l'état → socle → tranche verticale du cœur (G0) → description du site → vérification photo → résolution → HDA → contrôle → UE. Une piste qualité Q, indépendante de la date, court en parallèle.

```
 maintenant (nouveaux fichiers seulement)              après la passe de l'autre workflow (W)
 P1 Données de l'état                                  P0 Socle etat_cible (gel 2026 par défaut)
   1a MNT 2021 ─┐                                        │
   1c datation ─┴► 1d levé d'emprise ─┐                  │
   1j lignes 2022 du site ────────────┴► 1e .xodr ──┐    │
   1b événements, 1f masque, 1g archives, 1h inv. ──┼────┴► G0 Tranche verticale du cœur ──► P2 Site ──► P3 Vérif. photo ──► P4 Résolution ──► P5 HDA ──► P6 Contrôle ──► P7 UE
   1i solveur de poses autonome + 45 poses ─────────┘         (r ≤ 40 m, 9 vues ≤ 35 m)                                          ▲
 Q  MaterialX (assets/lib), prototypes FR, gabarits site, correctifs pj_sol / pj_bordure / pj_decals / pj_ilot ──► (G0 : MaterialX + pj_sol) ──► (P5 : tout)
```

### Phase 0 : socle `etat_cible` (2 à 3 j-agent si l'état 2026 est gelé ; +2 à 3 s'il est maintenu ; après W)

- **Prérequis** : réponse à Q2 ; étiquette git posée par l'utilisateur en cas de gel ; relevé `sha1` du code partagé.
- **Contenu** :
  - `recon/pcg/etat/` : module, configuration, surcharge des règles, lanceur, `controle_licences.py`, tests ;
  - branchement de `E` dans les chemins et références (§ 3.4, lignes marquées 0) ;
  - schéma 0.4 ;
  - tables de `marquages_sources` et `ctl_detection` lues dans `E` ;
  - motifs `.gitignore` pour `v2_avant_travaux/` (§ 3.3) ;
  - planches `*_plan2025.jpg` traitées comme photos de tiers.
- **Critères de fin** :
  - (a) si l'état 2026 est maintenu : U3 sur un commit figé ;
  - (b) `E.valide` avec T = 24/08/2024 et T = 18/05/2025 classe les 1 475 observations (1 441 recensées, plus 34 web) ; 0 observation postérieure au 22/06/2025 n'est valable dans TRV-C1 ; une observation négative rogne bien un événement non observé (test) ;
  - (c) 0 chemin `v2/` en dur dans les modules du chemin avant travaux ;
  - (d) le lanceur refuse une écriture croisée (test) ;
  - (e) `controle_licences.py` passe sur l'arbre courant.

### Phase 1 : données de l'état (10 à 15 j-agent ; durée critique 3,5 à 5,5 j)

Elle écrit seulement sous `v2_avant_travaux/sources/` et dans de nouveaux scripts sous `recon/pcg/etat/`. Aucun fichier existant n'est modifié.

| Lot | Contenu | Effort | Dépend de | Critère de fin |
|---|---|---|---|---|
| 1a | Sol nu 2021 flottant à 10 cm depuis le COPC, avec un **pipeline PDAL 2.10.0 écrit à neuf** : `recon/stages/relief.py`, cité par `README_relief.md`, n'existe pas dans le dépôt. MNT d'avant travaux hors quartier est ; quartier est en Z provisoire `a_priori`. | 1 à 1,5 | — | z − points de `bordures_hauteurs` : p95 ≤ 2 cm sur les 1 722 tronçons ; écart entre les lignes de vol du 12/08 et du 06/09/2021 publié ; vues d'IA-1 et IA-2 mesurées sur points (aujourd'hui 13,5 à 17,2 cm au JPEG) ; profil I2 ou T2 / T3 tranché |
| 1b | Table d'événements v2 : 21 CHG, TRV-C1, TRV-VERCORS, SURF-0344, EVT 2019-2022, `observe_post` et observations négatives. Sources : BD ORTHO 21/08/2018 et 13/08/2021, ortho GAM 02/07/2018, 16 arrêtés, photos | 1 à 1,5 | — | toutes les entités avec dates, familles et preuve ; carte regardée sur l'ortho 2022 et l'IGN 2024 ; CHG-019 rogné par les vues du 18/05/2025 ; **part du cœur « valable et certaine » publiée pour les deux dates** ; CHG-004 et CONSTR-EST redatés (≤ 05/03/2022 et ≤ 12/08/2021) ; SURF-0344 daté |
| 1c | Datation GAM promue (`datation_leve.py`), règle des 0,10 m dans TRV-C1 (emprise déjà disponible : `marquages_sources.zones()`, `relief_zones_2026`, `zone_travaux_2025`). **Jeu témoin de lignes 2025 connues** : goutte de la zone A (40 % du contour à 7,7 cm d'une ligne ancienne), courbe K-0385 (0,28 à 1,0 m de l'ancien îlot), quais en zigzag de Verdun SO (45 m et 72 m), lignes du plan 2025 géoréférencé à 3 cm. Revue sur planche des 449 m `relief_seul`, 1 298 m `terrain_remanie_2021` et 457 m `masquee` à ±80 m. | 1 à 1,5 | — | 100 % des 7 005 m de bordures, 4 601 m de limites et 2 544 m de marquages classés ; **rappel ≥ 95 %** (lignes témoins de 2025 rejetées) ; fausse alarme ≤ 3 % (témoin PCRS 2019) ; 0 ligne à revoir non revue à ±80 m |
| 1d | Levé d'emprise : bordures et limites reconstruites (PCRS 2019, crêtes LiDAR, contours sur l'ortho 2022), dont IA-1, IA-2, le séparateur de Verdun NE et l'ancienne bretelle SE | 1 à 1,5 | 1a, 1c | P1 ≥ 90 % sur l'emprise (blocs réservés compris) ; anneaux fermés G1 ; écart au PCRS 2019 p95 ≤ 0,10 m là où il existe |
| 1j | **Lignes 2022 du site** : extraction des lignes longitudinales et des bords de voie sur l'ortho 2022, sur les 300 × 300 m. Le pilote ne couvre que 2 zones et 139 m de lignes ; la v1 n'est utilisée que comme germe. Avancé depuis la phase 2b. | 1 à 1,5 | — | longues continues reprises à ≥ 90 % sur 20 tuiles annotées à la main ; tirets : phase p95 ≤ 0,10 m |
| 1e | `.xodr`, voies et manœuvres d'avant travaux : topologie OSM à T (24/08/2024, ou 01/06/2025 pour la variante ; bretelles SE et vers le Vercors, contre-allée), bords de voie tirés de 1j, 11 feux. `xodr_echantillonne.py` est réutilisé par import avec des chemins passés en paramètre (il a `paquet_jardin_2026.xodr` en dur, l. 39-40) ; sinon, copie dans `etat/sources/xodr_avant.py`. | 1,5 à 2,5 | 1d, 1j, 1g (OSM) | Bords de voie − lignes 2022 : p95 ≤ 5 cm ; manœuvres cohérentes avec 100 % des flèches 2022 valables à T au cœur ; jonction valide (VAL-JCT, VAL-XOD) |
| 1f | Masque de chaussée d'avant travaux (remplace `relief_zones_2026` et `dans_chaussee_2026`) | 0,5 | 1d | Écart à l'ortho 2022 : ≤ 2 % d'aire incohérente ; CONSTR-EST contre l'IGN 2024 |
| 1g | Téléchargements et archives publics, dans `data/sites/paquet_jardin/avant_travaux/<source>/`, lus avec `python -I` : OSM attic au 24/08/2024 ; liste des campagnes `PCRS_5cm` du WebDAV CRAIG 2017-2024 (une campagne 2024 sur Meylan serait la référence idéale pour T = 24/08/2024) ; arrêtés municipaux de Meylan 2022-2025 ; archives Wayback des dossiers de concertation (2022, puis 2023-2024) pour les plans de l'existant et le début de CHG-019 ; inventaire arboré public s'il existe ; 43 photos Panoramax 2023-2025 manquantes ; dalles LiDAR ou RGE ALTI de la périphérie (C5). **Pas de BD TOPO 2025-03-15.** | 0,5 | — | fichiers datés et sourcés (URL) ; photos hors git ; conclusion écrite sur l'existence d'une campagne PCRS 2024 |
| 1h | Inventaires `panneaux_avant.json` et `feux_avant.json` depuis `objets_avant_travaux.geojson` | 0,5 | — | 11 supports de feux, 57 panneaux, avec code, support, azimut connu et origine de position |
| 1i | **Solveur de poses autonome** (`etat/sources/poses_etat.py`). GCP de l'état : coins de marques de l'ortho 2022 hors CHG-002 / 003 / 008 ; pieds de mâts LiDAR 2021 ; z du MNT 2021 ; IGN 2024 (σ 0,2 m) dans CONSTR-EST pour les photos 2024-2025. Aucune bordure GAM dans TRV-C1. **Recalcul des 45 poses acceptées**, puis calage des 56 photos du 24/08/2024 (dont 25 du secteur est et 7 du Vercors), des 24 du 18/05/2025, des 12 du 12/01/2025, des 18 Mapillary du 10/06/2022 à ≤ 80 m et des 17 du 18/03/2023. | 2 à 3 | 1a | Δpose publié pour les 45 : au-delà de 0,25° ou 0,30 m, la pose 2026 est réputée biaisée et tout ce qui en dépend (triangulations, observations V2) est recalculé ; acceptation ≤ 0,5° (360°) ou ≤ 8 px ; S3 mesuré ; les 6 poses du 24/08/2024 situées dans CHG-019 traitées comme les autres |

Effort de la phase 1 : 1a 1-1,5 + 1b 1-1,5 + 1c 1-1,5 + 1d 1-1,5 + 1j 1-1,5 + 1e 1,5-2,5 + 1f 0,5 + 1g 0,5 + 1h 0,5 + 1i 2-3, soit 10 à 15 j-agent.

Durée critique : (1a ∥ 1c) → 1d → 1e, soit 3,5 à 5,5 j. 1b, 1g, 1h, 1j et 1i tournent en parallèle ; 1j et 1g doivent être finis avant 1e.

### Porte G0 : tranche verticale du cœur (2 à 3 j-agent ; après P0, 1a à 1d et 1i sur le cœur, Q partielle)

- **Contenu** :
  - description du cœur r ≤ 40 m seulement (sol, marquages, objets, contexte proche) ;
  - HDA corrigés (`pj_sol` sans flou, MaterialX `assets/lib`) ;
  - rendu Karma aux **9 vues calées à 35 m ou moins** (4 du 24/08/2024, 5 du 18/05/2025), au soleil de chaque photo.
- **Critères de fin** :
  - T1, S1 et P4 au seuil sur le cœur ;
  - M2 et L1 mesurés et publiés, avec l'analyse des écarts ;
  - planches photo / rendu montrées à l'utilisateur (non versionnées) ;
  - décision écrite « étendre au site » ou « corriger d'abord ».

### Phase 2 : description du site (6 à 9 j-agent, en 3 sous-lots parallèles ; sortie `v2_avant_travaux/description/base`)

- **2a Sol** : bordures datées et chaînées, îlots, surfaces, caniveaux, ponctuels (tampons, avaloirs), matériaux, nivellement sur le MNT 2021 et les surfaces de conception, partition par `sol_graphe.py`. Quartier est : Z du récolement (Q3) ou triangulé sur les 25 vues 360° du 24/08/2024, sinon compté en S2b.
  - Critères : T1, P1, P3, G1, G3 et G4 au niveau de la description ; S2a et S2b ; galets au cœur, terre et herbe sur la goutte NE.
- **2b Marquages** :
  - gabarits IISR et site appliqués aux lignes de 1j et aux marques ponctuelles du site ;
  - IGN 2024 et ortho-photos pour CHG-008 et le quartier est ;
  - marques v1 et fantômes utilisés comme **germes** ré-ajustés (IoU ≥ 0,60) et filtrés par `E.valide` ;
  - revue sur planches (1 à 2 h).
  - Critères : MQ1, P2 ; 0 marque du plan 2025 ; marques sur trottoir (MQ-DET-010) = 0 hors cas voulus.
- **2c Objets, végétation, contexte** :
  - 759 objets, avec leur statut à T ; **les 113 objets d'emprise positionnés depuis 2026 triangulés ou confirmés avant la jonction** ;
  - 466 arbres ; haies et massifs ;
  - bâtiments : extrait BD TOPO et lignes GAM du secteur est, hauteurs LiDAR, triangulations et ombres ;
  - escaliers, rampes et talus du secteur est ; périphérie ;
  - si T = 24/08/2024 : clôtures de chantier et bungalows de CHG-006 et 007.
  - Critères : OB2 ; C1, C2 et C4 au niveau de l'inventaire ; 0 objet ajouté par les travaux ; 22 lampadaires et 12 panneaux oubliés par la v2 présents.
- **Jonction** : `valider.py` passe ; chaque objet est implanté contre les bordures **de l'état** (GEN-07 à rebours dans l'emprise) ; S1 = 100 %.

### Phase 3 : vérification photo (3 à 4 j-agent ; sortie `v2_avant_travaux/enrichi`, JSON seulement)

- **Contenu** :
  - `valide_cible` recalculée sur les 1 475 observations, ré-appariement des liens ;
  - projection de la description dans toutes les vues acceptées **aux poses de l'état** ;
  - triangulation des objets verticaux (priorité : 11 feux, 57 objets Mapillary seuls, 22 objets d'emprise, `feu_SW_TPC`, objets relogés) ;
  - extraction d'attributs (matériaux, types de flèches, état d'usure), en deux passes indépendantes.
- **Critères de fin** :
  - P4 sur toutes les vues acceptées (arêtes réservées) ;
  - OB1 ; S3 ;
  - **couverture stricte du cœur publiée** : nombre d'entités du cœur ayant au moins une observation valable à T sur pose acceptée, divisé par le nombre d'entités du cœur. La valeur par simple re-datation est publiée d'abord ; l'audit la bornait entre 9,0 et 22,6 %, ce dernier chiffre étant un maximum. La cible chiffrée est fixée à la fin du lot 1i, d'après la couverture S3 obtenue ;
  - 0 décision fondée sur une photo séparée de T par un événement ;
  - chaque attribut enrichi cite sa photo et ses pixels.

### Phase 4 : résolution, cohérence et RES (2 à 3 j-agent ; sortie `description/resolue`)

- **Contenu** : Q3, Q4 et Q8 relatives à T ; règles RES-* paramétrées ; arbitrages et verdicts de revue par état ; les non-résolus renvoient vers une **archive à consulter**, pas vers une station de terrain.
- **Critères de fin** :
  - S1, S2a et S2b au seuil ;
  - 0 conflit non arbitré à ±80 m ;
  - liste `a_verifier_archive` publiée, avec pour chaque entrée la source à consulter ;
  - T1 toujours vrai après résolution.

### Phase 5 : fabrication HDA (3 à 5 j-agent ; Q terminée ; sortie `fabrique_hda`)

- **Contenu** :
  - `hython fabriquer_hda.py --etat avant_travaux --description …/resolue/base` ;
  - MaterialX texturé (`assets/lib`) ; sol sans flou ni retrait de triangles ;
  - contexte composé : bâtiments, arbres, feux, panneaux, mobilier ;
  - détails observés seulement ;
  - rendu Karma de contrôle aux poses de l'état, avec le soleil de chaque photo.
- **Critères de fin** : G2, G5, M1, M4, D1, LIC ; le rendu de contrôle compose toutes les couches ; M2 et L1 au seuil et M3 publié sur au moins 10 poses.

### Phase 6 : contrôle (1 à 2 j-agent ; sortie `controle`)

- **Contenu** : `verifier_regles.py --etat avant_travaux` avec la surcharge (attendus tirés des manœuvres d'avant travaux, règles « plan2025 » non applicables) et la famille `realisme_validation`.
- **Critères de fin** :
  - 0 violation bloquante ;
  - tous les critères du § 4.2 rapportés avec leur valeur ;
  - V1 sur 12 vues ;
  - planches photo / rendu / superposition générées pour toutes les vues acceptées (non versionnées) ;
  - revue V2 lancée.

### Phase 7 : Unreal (3 à 5 j-agent)

- **Contenu** :
  - niveau `PJ_AvantTravaux` et racine `/Game/PJ/Etats/AvantTravaux` ;
  - import de la fabrication du site entier, 0 maillage v1 ;
  - feux et panneaux FR posés ;
  - arbres filtrés par statut à T, feuillage de la date cible ;
  - soleil et exposition calés sur les photos ;
  - vues CineCamera aux poses de validation.
- **Critères de fin** : U1, U2, C3, C5, L1, L2, V1 ; V2 passée ; accord de l'utilisateur.

### Piste Q : qualité indépendante de la date (4 à 6 j-agent ; dès maintenant pour ce qui est nouveau, après W pour ce qui touche `houdini/`)

- **Matériaux** : une seule définition MaterialX pour Karma et UE, portée de `pj_materiaux.py` dans `fabriquer_hda.py:431-473`. Elle ne référence que `assets/lib` (CC0), avec tuilage hexagonal et albédos calés sur les photos datées (charte enrobé / bordure / peinture). Les variantes City Sample restent optionnelles côté UE.
- **Prototypes FR** : feux R11v, R12, R13c, mâts, panneaux (faces PNG de `panneaux.json`), abri, potelets, en assets de bibliothèque.
- **Gabarits de marquage « site »** dans `assets/specs/marquages_gabarits_site.json`.
- **HDA**, correctifs préalables à toute réutilisation :
  - `pj_sol` : partition topologique (arc partagé maillé une seule fois), surfaces de conception, plus de flou ni de falaises ;
  - `pj_bordure` : épaufrures sur les arêtes, plus de sphères ;
  - `pj_decals` : plus de pontages aléatoires ;
  - `pj_ilot` : sans éclats par défaut.

Le MaterialX et `pj_sol` sont faits en premier, car G0 en dépend.

### Effort, durée et parallélisme

| Phase | Effort (j-agent) | Durée sur le chemin critique (j) | Dépend de |
|---|---|---|---|
| P0 | 2-3 (+2-3 si 2026 maintenu) | 2-3, après W | W, Q2 |
| P1 | 10-15 | 3,5-5,5 | — |
| G0 | 2-3 | 2-3 | P0 ; 1a à 1d et 1i sur le cœur ; Q (MaterialX, `pj_sol`) |
| P2 | 6-9 | 2-3 (extension de 2a au site, 2b et 2c en parallèle) | G0 |
| P3 | 3-4 | 3-4 | P2, 1i |
| P4 | 2-3 | 2-3 | P3 |
| P5 | 3-5 | 3-5 | P4 ; Q terminée |
| P6 | 1-2 | 1-2 | P5 |
| P7 | 3-5 | 3-5 | P6 (import d'essai dès P6) |
| Q | 4-6 | 0 tant qu'elle finit avant P5 | W pour `houdini/` |
| **Total** | **36-55** (38-58 si 2026 maintenu) | **20-31**, plus max(0 ; W + P0 − durée critique de P1) | — |

Calcul de la durée : max(P1 : 3,5-5,5 ; W + P0 ; W + partie de Q dont G0 dépend, MaterialX et `pj_sol`, ≈ 1,5-2 j) + G0 2-3 + P2 2-3 + P3 3-4 + P4 2-3 + P5 3-5 + P6 1-2 + P7 3-5. Avec W ≤ 1,5 j, cela donne de 19,5 à 30,5 j.

Effet de la date (§ 1.3) : +0,5 à 1 j-agent pour le 24/08/2024, +1 à 2 pour le 18/05/2025.

L'audit estimait 15 à 25 j-agent, ce qui couvrait P0, P1 et une partie de P2 à P4. La différence tient :
- aux correctifs de qualité (RC2 à RC7) ;
- à G0 ;
- au solveur de poses ;
- au `.xodr` et au MNT réécrits ;
- à la datation renforcée.

Correction par rapport à la version précédente : son tableau s'additionnait à 29-45 j-agent, et non 31-47. Son chemin critique, compté en efforts de phase entiers, faisait 23-36, et non 20-30.

---

## 6. Risques et questions

### 6.1 Risques

| # | Risque | Impact | Parade |
|---|---|---|---|
| R1 | **`.xodr` et MNT d'avant travaux à recréer** : le générateur `recon/stages` (dont `relief.py`) est absent. Le `.xodr` conditionne 31 règles du contrôleur, les manœuvres et les attendus de flèches. | Chemin critique (lots 1a et 1e) | Rebudgétés (1a : 1-1,5 j ; 1e : 1,5-2,5 j) ; lignes 2022 du site extraites avant (1j) ; validation par les bords de voie (p95 ≤ 5 cm) |
| R2 | **Concurrence avec l'autre workflow** sur `decrire`, `houdini`, `controle` et `v2` (3 fichiers déjà modifiés depuis l'instantané de 08:32) | Conflits, base mouvante | Q2 posée en premier, gel par défaut ; phase 1 et piste Q sans toucher aux fichiers existants ; P0 après W, en lots courts sur branche, après relevé `sha1` |
| R3 | **Quartier est** (16 % des surfaces circulées) : ni LiDAR ni hauteurs après 2021 ; BD TOPO sans hauteur | Z et hauteurs a priori ; défaut e5 de 2026 reproduit | Récolements VRD des Saules Blancs (Q3) ; triangulation sur les 25 vues 360° du 24/08/2024 ; S2b et G6 comptés à part |
| R4 | **Vercors et CHG-019** : travaux annoncés d'avril à novembre 2025, non observés ; aucune photo entre le 12/01 et le 23/06/2025 | Si T = 18/05/2025 : 18,5 % du cœur incertain | T = 24/08/2024 recommandé ; sinon rognage par observations négatives, arrêtés municipaux et archives Wayback |
| R5 | **Poses biaisées par 2026** : `gcp.py` tire ses GCP de `marquages_2026` (v1) et son z du MNT 2026 ; 27 Mapillary sont calées sur le GAM 2026, dont 5 entre 40 et 80 m et 6 poses dans CHG-019 | P4, V1, OB1 et C3 validés contre 2026 | Solveur autonome (1i), Δpose publié, recalcul en aval |
| R6 | **Recalcul des poses défavorable** : moins de poses acceptées sans GCP 2026 | S3 non atteint ; date à revoir | Seuil de reconfirmation de Q1 (moins de 15 poses Mapillary du 24/08/2024 sur 26) ; séries 2022 et 2023 en appoint hors événements |
| R7 | **Datation GAM imparfaite** : fausse alarme 2,2 %, rappel inconnu ; 31,4 % de la longueur indéterminée ; tronçons < 1,5 m peu fiables | Lignes 2025 admises par erreur | Règle des 0,10 m dans TRV-C1 ; jeu témoin (rappel ≥ 95 %) ; revue obligatoire des trois classes à ±80 m |
| R8 | **Date Pléiades 2025 inconnue** (03/05 → 08/08/2025 d'après les ombres) | Interprétation circulaire de CHG-018 / 021 | `date_max` = 08/2025 ; contrôle SPOT du 25/06/2025 ; demande à l'IGN / DINAMIS ; sans effet si T = 24/08/2024 |
| R9 | **Glyphes hors IISR et marques usées** (trident, logos vélo, flèche TD / TD_TAD, extrémités de tirets à 31 cm p95) | Types ou extrémités faux | Gabarits site ; phase des tirets ajustée sur la file ; arbitrage par photo sous une marge de 0,05 |
| R10 | **Licences** : CC-BY-SA des photos ; ODbL d'OSM ; CC-BY CARLA ; City Sample réservé à UE ; plan 2025 au statut flou ; imagerie de rue commerciale interdite | Non-conformité, versionnement de photos | § 2.8 ; motifs `.gitignore` en phase 0 ; `controle_licences.py` ; planches dans `photos_non_versionnees/` ; liste `sources_interdites` |
| R11 | **Ampleur (36 à 55 j-agent)** | Dérive ; premier rendu trop tardif (scénario 2026) | Porte G0 sur le cœur avant extension ; critères B et I séparés ; aucune livraison visuelle avant S1, T1, P1, P4, M1, L2 et V1 mesurés |
| R12 | **Événements 2019 → 05/2022 non inventoriés** (COLAS 2019, réseaux, terrassements est, rive est du Vercors) | PCRS 2019 ou LiDAR 2021 admis à tort | Lot 1b (BD ORTHO 2018 et 2021, arrêtés) |

### 6.2 Questions pour l'utilisateur (dans cet ordre, seulement celles qui changent le plan)

1. **(Q2, à poser en premier) L'état 2026 doit-il être gelé tel quel ou maintenu en parallèle ?**
   - **Gelé (recommandé)** : vous posez une étiquette git sur le dernier commit 2026 et `v2/` devient une archive. La chaîne n'est paramétrée que pour l'avant travaux. La phase 0 coûte 2 à 3 j-agent, sans exigence d'octet sur une base que l'autre workflow modifie encore.
   - Maintenu : non-régression à l'octet (U3) sur un commit figé, coordination continue, harmonisation des 11 dates de travaux. Cela ajoute 2 à 3 j-agent et des contraintes sur chaque lot.
2. **(Q1) Date cible : le 24/08/2024 (recommandé) ou le 18/05/2025 (veille des travaux) ?**
   - Matrice au § 1.3.
   - Le 24/08/2024 donne 91,2 % du cœur valable et certain, contre 75,7 %. Il offre 31 vues calées le jour même contre 14, et 56 photos couvrant les cinq secteurs contre 24 sur trois. Il est indépendant de la date Pléiades et tombe en fin d'été.
   - Le 18/05/2025 est l'état à 5 semaines des travaux, au printemps, avec 2 vues de plus à 80 m ou moins et les abords définitifs de Verdun NE.
   - Le choix sera reconfirmé après le recalcul des poses (lot 1i).
3. **(Q3) Acceptez-vous de demander à la Métropole ou au CRAIG :**
   - l'**ortho PCRS 5 cm de 2025** (accès restreint, HTTP 401) et son **jour de vol** ;
   - la **version d'avant récolement C1** de `Meylan_Topo.dwg` ou son historique, et les plans de l'existant du marché C1 ;
   - les **plans de récolement VRD des Saules Blancs** (Z du quartier est) ?

   Si le vol PCRS 2025 précède le 23/06/2025, cette ortho devient la référence géométrique de la veille des travaux et rend la variante du 18/05/2025 aussi certaine que le 24/08/2024 au cœur.

---

## 7. Critiques de la relecture : rejetées, en tout ou en partie

Les 23 critiques (F1 à F23), les chiffres signalés comme faux et les correctifs proposés ont été recontrôlés dans les fichiers (`revision/verifications_revision.json`). **Aucune critique n'est rejetée sur le fond.** Les points suivants sont rejetés ou corrigés :

| Critique | Point rejeté ou corrigé | Constat recontrôlé |
|---|---|---|
| F1 | « 6 poses Mapillary `calee_bordures` dans CHG-019 (x 35..43) » | Ce sont **5 `calee_bordures` et 1 `calee_gcp`**, toutes du 24/08/2024, entre (35,3 ; −138,2) et (43,1 ; −129,0). La pose (45,3 ; −127,8) est hors de l'emprise. |
| F3 | « CHG-019 commence à y = −5, à 18,1 m du centre » | y max = −4,6 confirmé. Mais l'emprise descend jusqu'à **7,7 m** du centre des couronnes (−1,57 ; −5,09) et à 11,7 m de l'origine : le défaut est plus grave qu'annoncé. Part du cœur : 18,5 % au raster de 0,25 m, 18,8 % (946 m²) dans `statistiques.json`. La critique ne relevait pas que la règle « non valable si d tombe pendant un événement » rendait en plus les photos du 18/05/2025 non valables dans cette bande : d'où les observations négatives. |
| F7 | « S3 (30 vues) est quasi inatteignable, 91 % de réussite exigée » | Vrai pour la seule fenêtre du 24/08/2024 au 22/06/2025 (33 photos uniques à ≤ 80 m). Il existe cependant 71 autres photos uniques à ≤ 80 m de 2022 à 05/2024 (6 + 18 + 17 + 16 + 14), admissibles hors événements : le plafond n'est pas physique, mais ces perspectives n'ont aujourd'hui aucune pose acceptée. La reformulation spatiale proposée est retenue (S3) ; le nombre devient indicatif (S3n). |
| F10 | « Le chemin critique omet P0 et la piste Q » | P0 (2-3 j) court en parallèle de P1, et Q (4-6 j) en parallèle de P1 à P4 (12,5 j au moins) : ni l'une ni l'autre n'allonge le chemin critique, sauf par l'attente W de l'autre workflow (et la part de Q dont dépend G0). Celle-ci est désormais dans la formule. Les sommes corrigées (29-45 ; 23-36) sont confirmées pour l'ancien tableau. |
| F12 | « 13 bâtiments créés le 04/07/2025, Processus IA métrique, hauteur nulle » ; « 40 escaliers / rampes et 9 talus » | 13 créations le 04/07/2025, dont **12 dans le secteur est, toutes « Processus IA métrique » sans hauteur**. La 13e est un petit bâtiment « Lidar HD » de 2,5 m en (−120 ; −90). Dans la boîte x 37..156, y −67..92 : **38** escaliers / rampes et **18** talus (13 bas, 5 hauts) ; les comptes dépendent de la boîte. 111 lignes de bâtiments : confirmé. |
| F14 | « La séance du 01/05/2024 (14 photos à ≤ 80 m) est perdue pour CHG-009 » | Le compte de 14 est confirmé. Mais aucune de ses 11 poses Panoramax n'est acceptée (5 calculées puis rejetées) : elle ne contribue à rien aujourd'hui, quel que soit le modèle. Le champ `observe_post` est retenu ; son gain dépend du calage de cette séance. |
| F16 | « 7 des 11 feux sont "existant (inchangé)" 2026 » | **6** « existant (inchangé) », 4 « déduit 2026 (à vérifier) », 1 « à vérifier ». Les 11 sont tous positionnés depuis la description 2026. Les 7 « feux conservés à 0,3 m près » d'OBJETS § 6.1 comptent les objets de la description 2026, pas l'inventaire d'avant travaux. |
| F17 | « P1 se contrôle avec sa propre source » | Seulement pour les bordures tirées du contour ortho (rang 3). Les lignes PCRS 2019 et GAM (rangs 1 et 2) sont indépendantes de l'ortho 2022. Le contrôle sur blocs réservés est retenu pour le rang 3. |
| F18 | « OB1 (σ ≤ 0,25 m) et C3 (≤ 0,5 m) se contredisent » | Pas une contradiction : l'un borne l'incertitude de triangulation, l'autre l'écart de position. Mais les deux seuils sur les mêmes objets prêtaient à confusion : seuil unique de 0,30 m (OB1), C3 limité au site hors cœur. |
| F18 | « Modèles Cityscapes / Vistas : risque de licence » | Retenu par prudence : les jeux de données sont sous licence non commerciale, et le statut des poids entraînés est discuté. Ces modèles sont écartés. |
| F4 (iv) | « Le niveau de mai obligerait à deux états de végétation » | Toute validation sur les deux séances exige deux états de végétation (L2), quelle que soit T. Ce qui est retenu, c'est que 69 % des vues ont la saison de T = 24/08/2024. |
| F19 | « Mapillary 13:37:14 → 13:38:06 » | Les 21 images Mapillary du 18/05/2025 de `poses_mapillary.json` vont de 13:37:10 à 13:38:06 (heure sans fuseau). La séance Panoramax va de 13:37:08 à 13:38:10 UTC. Écart sans conséquence. |
| F20 | « Recommandé dans SOURCES § 9.1 » | C'est SOURCES § 9, point 1. Le fond est retenu (Q3, lot 1g). |
| Soleil | « 235,5° / 53,8° à 13 h 38 UTC » | Confirmé : 235,6° / 53,8° à 13:38:10 et 235,2° / 53,9° à 13:37:08. L'ancien plan écrivait 235,2° / 53,5° : la hauteur est corrigée. |

Chiffres de l'ancien plan confirmés **faux** et corrigés ici :
- PDAL 2.8.2 → 2.10.0 ;
- séance du 18/05/2025 « de 13 h 38 à 13 h 45 » → de 13:37:08 à 13:38:10 UTC ;
- « IGN recalée à 4 cm » → translation globale de 4 cm, précision locale ±0,1-0,2 m ;
- 85,3 % → 83,8 % (poses acceptées) et 69,1 % (objets détectés) ;
- « ≥ 22,6 % » (borne haute employée comme minimum) → valeur publiée, cible fixée après 1i ;
- efforts 31-47 / 20-30 → effort recalculé et durée définie ;
- comptes de la séance du 18/05/2025 réconciliés ;
- « 11 supports de feux supprimés » → seules les deux traversées à feux et le nœud `1959011179` sont supprimés ;
- longueur GAM : 6 868 m (CHANGEMENTS, sur 300 × 300 m découpés) et 6 983 m (AUDIT, appariement) contre **7 005 m** (SOL, classes de datation), retenue ici.

---

## Annexe A. Chiffres réconciliés entre les inventaires

| Sujet | Écart entre rapports | Valeur retenue (vérifiée) |
|---|---|---|
| Poses calées | `changements` : 58 ; `qualite` : 13 ; `objets` : 64 caméras (19 Panoramax et 45 Mapillary) | `poses.json` : 13 Panoramax `accepte` (5 le 24/08/2024, 8 le 18/05/2025), plus 6 calculées puis rejetées (5 du 01/05/2024, 1 du 18/05/2025) que l'inventaire `objets` comptait. `poses_mapillary.json` : 45 calées (27 `calee_bordures`, 5 `calee_gcp`, 13 `calee_panoramax` = mêmes prises). **45 vues distinctes** (31 + 14), dont 20 à ≤ 80 m (9 + 11) et 9 à ≤ 35 m (4 + 5). Toutes à recalculer (1i). |
| Séances photo | 18/05/2025 : 19, 24, 40 ou 52 | Panoramax : 18/05/2025 = 24 uniques (13:37:08 → 13:38:10 UTC) + 24 copies Mapillary ; 24/08/2024 = 56 uniques (15:05:21 → 15:11:01 UTC) + 57 copies ; 12/01/2025 = 12 (12:11:35 → 12:11:57 UTC) |
| Nuage LiDAR 2021 | `sol` : « absent, téléchargement à autoriser » | **Présent** : `data/sites/paquet_jardin/avant_travaux/lidar_hd/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz` (150 890 899 octets, ignoré par git). **PDAL 2.10.0** : `C:/Program Files/QGIS 4.2.3/bin/pdal.exe`. |
| Date du levé GAM | `audit` : « ≈ 2025-12, à dater » | Pas de date unique : compilation sans date par objet, extraite le 06/10/2026 (commits 42ee3af et b4a8384), identique dans `vector/`, `etat_2026/` et `data/vector_gz/gam` (4 574 sommets de bordure sur 4 614). Admissible **par classe de datation**, avec la règle des 0,10 m dans TRV-C1. |
| Longueur des bordures GAM | 6 868 m (CHANGEMENTS), 6 983 m (AUDIT), 7 005 m (SOL) | 7 005 m (datation) ; les écarts viennent de la découpe et de l'appariement |
| Priorité des marquages | `audit` (proposition) : GAM 0,95 avant ortho 2022 | Ortho 2022 d'abord : 1 à 3 cm, contre 7,0 cm de médiane pour le GAM coïncident. Le GAM ne vient qu'en 2e rang, s'il est `present_identique` à < 0,10 m. |
| Bordures | `sources` : PCRS 2019 d'abord ; `sol` : GAM daté d'abord | **Dans TRV-C1** : PCRS 2019, LiDAR et ortho 2022 d'abord, GAM seulement s'il coïncide à < 0,10 m. **Hors TRV-C1** : GAM daté d'abord (PCRS / GAM p50 3,5 cm, 99 % à ≤ 0,30 m entre 35 et 80 m). |
| Recalage IGN 2024 | « recalée à 4 cm » | translation (0,035 ; 0,029) m ; MAD (0,102 ; 0,053) m ; 37 fenêtres retenues, jusqu'à 0,51 m (`v2/enrichi/recensement/ortho_recentes/recalage.json`) |
| Changements 2022-2025 | « 17 de confiance haute ou moyenne, 3 faibles, 1 risque » | GeoJSON : 21 entités (10 haute, 7 moyenne, 4 faible dont CHG-019 non observé), plus 2 événements antérieurs à 2022 à créer (1b) |
| Surfaces | `statistiques.json` | Géométrie 2022 invalide sur 23 943 m² (26,6 % de l'emprise), 9,0 % à r ≤ 40 m ; texture de chaussée 18,3 % à r ≤ 40 m ; marquages 9,9 % à r ≤ 40 m ; risque non observé (CHG-019) 946 m², soit 18,8 % à r ≤ 40 m |
| Cœur valable et certain | — | 91,2 % (T = 24/08/2024) ; 75,7 % (T = 18/05/2025) ; raster de 0,25 m, CHG-001 à 006 et 019 |
| Objets | `objets_avant_travaux.geojson` | 759 (471 / 219 / 69), confiance 339 / 198 / 222 ; 97 exclus ; positions : 684 description 2026 (dont 113 dans l'emprise), 57 Mapillary, 17 V2, 1 OSM |
| Visibilité des objets du cœur | 85,3 % | 83,8 % sur poses acceptées ; 69,1 % détectés |
| Datation GAM des bordures | — | 44,6 % `relief_2021`, 13,2 % `arasee_visible`, 6,0 % `apparue_2022_2024`, 4,7 % `absente_avant` ; indéterminés 31,4 % (6,4 + 18,5 + 6,5) |
| BD TOPO | « 2025-03-15 pour figer les bâtiments » | 12 emprises du secteur est créées le 04/07/2025 (IA, sans hauteur) : absentes de l'édition 2025-03-15 |
| Observations | — | 1 475 (1 441 recensées + 34 web) |

## Annexe B. Fichiers d'appui

- Révision : `revision/outils/verifier_critiques.py`, `revision/verifications_revision.json`, `revision/chg019_coeur_poses.jpg` (fond ortho PCRS 2022, aucune photo de tiers), `revision/PLAN_AVANT_TRAVAUX_v0_2026-10-11_0957.md`.
- Sources : `sources/SOURCES.md`, `sources/sources.json`, `sources/photos_inventaire.json`, `sources/osm_2025-06-01/osm_*.geojson`, `sources/lidar_dates.json`.
- Changements : `changements/CHANGEMENTS.md`, `changements/changements_2022_2025.geojson`, `changements/donnees/statistiques.json`, `changements/planches/carte_changements_2022_2025.png`.
- Audit : `audit/AUDIT_PIPELINE.md`, `audit/occurrences_cablees.csv`, `audit/proposition_etat_cible_{avant_travaux,2026}.json`, `audit/instantane_code_sha1.txt`.
- Marquages : `marquages/MARQUAGES.md`, `marquages/marquages_pilote_2022.geojson`, `marquages/datation_gam.geojson`, `marquages/couverture_site.json`, `marquages/pilote/*.py`.
- Sol : `sol/SOL.md`, `sol/datation/gam_bordures_datation.geojson`, `sol/datation/datation_resume.json`, `sol/pilote_A/ilots_avant_travaux.geojson`, `sol/pilote_B/bordure_rive_B.geojson`, `sol/precision_hauteurs.json`, `sol/pilote/*.py`.
- Objets : `objets/OBJETS.md`, `objets/objets_avant_travaux.geojson`, `objets/objets_exclus.geojson`, `objets/comparaison_2026.json`.
- Qualité : `qualite/QUALITE.md`, `qualite/mesures_qualite.json`, `qualite/planche_n1_rendu2026_vs_ortho2022.png`.
- Code cité : `recon/pcg/enrichir/gcp.py` (l. 3-10, 146-170), `recon/pcg/enrichir/camera.py` (l. 221-222), `recon/pcg/decrire/xodr_echantillonne.py` (l. 39-40), `recon/out/paquet_jardin/package/donnees/relief/README_relief.md` (l. 1-3), `recon/pcg/ue/materiaux/construire_materiaux.py` (l. 11, 18), `.gitignore` (l. 40-66).
- Téléchargements : `data/sites/paquet_jardin/avant_travaux/{lidar_hd, osm_2022-05-10, osm_2025-06-01, osm_actuel_2026-10-11, osm_historique, mapillary_map_features, panoramax, panoramax_semantique, gam_geoflux_2026-10-11, ign}/`.

## Annexe C. Suite donnée à chaque critique

| Critique | Verdict | Où dans ce plan |
|---|---|---|
| F1 Poses non réutilisables | acceptée (corrigée : 5 + 1 poses dans CHG-019) | § 0.5, 2.2, 3.2 (`poses_etat.py`), 3.4 (enrichir), lot 1i, R5, R6 |
| F2 Datation GAM : rappel non mesuré | acceptée | § 0.2, 2.3, lot 1c, S1, R7 |
| F3 CHG-019 au cœur | acceptée et aggravée (7,7 m du centre ; photos du 18/05/2025 non valables dans la bande) | § 1.3, 2.1 (observations négatives), lot 1b, R4 |
| F4 Comparaison des dates | acceptée ; **recommandation renversée** au profit du 24/08/2024 | § 0.1, 1.1, 1.3, Q1 |
| F5 Date Pléiades circulaire | acceptée (03/05 → 08/08/2025 d'après les hauteurs solaires) | § 1.2, 2.1 (CHG-018 / 021), 2.2, R8 |
| F6 `.gitignore` | acceptée | § 2.8, 3.3, phase 0, LIC |
| F7 S3 | acceptée sur la reformulation, rejetée sur « plafond physique » | § 4.2 (S3, S3n), § 7 |
| F8 P4 contre acceptation des poses | acceptée | § 4.2 (P4, P4f) |
| F9 22,6 % | acceptée | phase 3 |
| F10 Efforts | acceptée (sommes) ; rejetée pour P0 et Q sur le chemin critique | § 5 (effort et durée), § 7 |
| F11 Phase 1 pas indépendante | acceptée | lots 1a, 1e, 1i, 1j ; R1 |
| F12 BD TOPO 2025-03-15 | acceptée (comptes corrigés) | § 0.5, 2.2, 2.7, lot 1g |
| F13 Arbitrage | acceptée | § 2.1 |
| F14 Événements 2019-2022, `observe_post` | acceptée (gain du 01/05/2024 nuancé) | § 2.1, lot 1b, R12 |
| F15 HDA et régalage du quartier est | acceptée | § 0.6, 2.3, 3.4, Q, G0, S2b |
| F16 v1, fantômes et objets 2026 | acceptée (6 feux et non 7) | § 2.4, 2.5, 2c, OB1 |
| F17 Critères circulaires | acceptée (P1 nuancé) | MQ1, M4, G3, P1, G6 |
| F18 Critères vagues | acceptée (OB1 / C3 nuancé) | V1, V2, M1, C1, C2, C5, colonne B/I |
| F19 Chiffres faux | acceptée | § 7, annexe A |
| F20 Sources oubliées | acceptée | lot 1g, Q3 |
| F21 Licences | acceptée | § 2.8, LIC, piste Q |
| F22 Ordre Q2 et tranche verticale | acceptée | § 0.9, 3.1, 3.5, G0, Q2 |
| F23 « Scène stable » | acceptée | § 1.1 (stabilité listée avec ses exceptions) |
