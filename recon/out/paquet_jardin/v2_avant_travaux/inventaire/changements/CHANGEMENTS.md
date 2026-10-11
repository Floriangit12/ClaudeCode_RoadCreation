# Changements du site Paquet Jardin entre mai 2022 et juin 2025 (veille des travaux)

Fenêtre étudiée : du **10/05/2022** (PCRS 5 cm) au **22/06/2025** (veille des travaux du carrefour, 23/06/2025 → 05/12/2025 ; trottoirs du Vercors jusqu'au 30/01/2026).
Emprise : le carré de 300 m du site (local −150..+150 m ; local = L93 − (917279,43 ; 6460289,98)).

Livrables :

- `changements_2022_2025.geojson` : 21 entités en L93, avec `nature`, `date_min`, `date_max`, `preuve`, `confiance`, `observe`, `effet_pcrs_2022` et `source_recommandee`.
- `planches/zones/CHG-xxx.png` : une planche ortho PCRS 2022 | IGN 2024 | Pléiades 2025 par changement.
- `planches/carte_changements_2022_2025.png` : la carte d'ensemble.
- `donnees/statistiques.json` : les chiffres ci-dessous.

---

## 1. Conclusion : date cible recommandée

**Je recommande comme date cible « printemps 2025, veille des travaux ».** Elle se cale sur la séance photo du **18/05/2025**, la dernière qui couvre le carrefour avant le 23/06/2025. Les preuves sont admissibles du **24/08/2024 au 22/06/2025** : la scène y est stable. L'ortho IGN du 09/08/2024 sert de référence couleur pour tout le site. Le PCRS 2022 reste la référence géométrique fine partout où rien n'a changé.

| Critère | Mai 2022 (PCRS) | Printemps 2025 (veille des travaux) |
|---|---|---|
| **(a) Quantité de preuves** | Ortho **5 cm** (la meilleure) et LiDAR HD 2021, un an avant. **Aucune photo calée.** 44 photos Mapillary en 2022 (05/03 sur le Vercors, 10/06 sur Verdun) et 53 le 18/03/2023, toutes en pose a priori. Aucune image Panoramax en 2022. | Ortho IGN **20 cm** RVB et IRC du 09/08/2024, Pléiades 50 cm 2025, SPOT 2025. **153 photos** en 3 séances (24/08/2024, 12/01/2025, 18/05/2025). **58 poses calées** : 13 Panoramax et 45 Mapillary, soit 100 % des poses calées du dépôt. 26 photos le 01/05/2024. |
| **(b) Stabilité de la scène** | Le secteur est est un **chantier actif** : grue, gros œuvre, base vie, terre nue. Il n'est décrit en 3D par aucune source (le LiDAR 2021 est antérieur, la BD TOPO ne l'a pas). Entre mai 2022 et août 2024, **26,6 %** de l'emprise change de géométrie. | Entre le 24/08/2024 et le 18/05/2025, seuls changent les abords de la rive SE de Verdun NE (clôtures retirées, CHG-006 et CHG-007, hors chaussée) et les finitions paysagères des cœurs d'îlot du quartier est (CHG-021, terre nue en août 2024, aménagés sur Pléiades 2025). Chaussée, bordures, îlots, zébras et marquages sont identiques sur les photos calées des deux dates. |
| **(c) Intérêt ADAS** | Bords de chaussée de chantier : palissades, accès d'engins. Scène atypique, que les photos ne permettent pas de valider. | Quartier livré : nouvelle branche de carrefour avec STOP (Mitaillères), accès et parkings riverains, configuration hachurée de Verdun NE. Les vues de contrôle sont possibles aux 58 poses calées, et le parti est cohérent avec la phase de validation de l'architecture V2 (§ 1.7). |

**Ce que la date cible 2025 implique :**

- Au cœur (r ≤ 40 m), la géométrie du PCRS 2022 reste valable sur **91 %** de la surface. Les seules différences sont la base vie SE (CHG-005) et les amorces des abords de Verdun NE (CHG-006) et de la rive est du Vercors (CHG-004).
- En revanche, l'**aspect** de la chaussée du cœur a changé : les reprises d'enrobé de 2024 couvrent **18 %** du cœur (CHG-009). Le marquage de l'approche NE a aussi changé (CHG-008, 10 % du cœur).
- Sur le Vercors, la dernière observation date du **12/01/2025** (photos à vélo). Des travaux y sont annoncés d'avril à novembre 2025 (CHG-019, non observé). Je retiens donc l'état du 12/01/2025 pour le Vercors.

**Une alternative presque équivalente : le 09/08/2024 (date IGN).** Elle ne diffère du printemps 2025 que par CHG-006 et CHG-007 (clôtures et bungalows de chantier le long de Verdun NE).

**Une source à demander.** Le PCRS 5 cm 2025 de la Métropole (CRAIG, RVB et IRC, « juin-juillet 2025 ») n'est diffusé que sur abonnement : `https://tiles.rtge.craig.fr/pcrs/service` répond HTTP 401 (voir `catalogue_orthos.json`). Si ses dalles du carrefour ont été volées avant le 23/06/2025, ce serait l'ortho 5 cm exacte de la date cible.

---

## 2. Zones où il faut une autre source que le PCRS 2022 (date cible : printemps 2025)

| Id | Zone (local) | Ce qui n'est plus valable | Source à utiliser |
|---|---|---|---|
| CHG-001 | Immeubles du quartier est, x 37..156, y −67..92 (11 emprises BD TOPO) | Tout : chantier en 2022 | Emprises **BD TOPO** (créées le 04/07/2025). **IGN 2024** pour les toits. Hauteurs absentes de la BD TOPO et du LiDAR 2021 : les estimer par les ombres IGN 2024 (soleil connu, `outils/soleil.py`) et les photos du 24/08/2024. |
| CHG-002 | Espaces extérieurs du quartier : voies, parkings, cheminements, parc et noue (≈ 21 000 m²) | Sol, bordures, végétation | **Levé topo GAM**, cohérent avec l'IGN 2024 dans ce secteur (`planches/topo_gam/est.jpg`). IGN 2024. **31 photos Mapillary du 24/08/2024 calées sur les bordures.** |
| CHG-003 | Carrefour Vercors / allée des Mitaillères, x 18..78, y −143..−112 | Branche est, îlot planté, bordures, STOP | IGN 2024, 22 photos calées du 24/08/2024, levé GAM (hors emprise des travaux), photos du 12/01/2025 (STOP) |
| CHG-004 | Rive est du Vercors, x 22..40, y −62..−33 | Bordure, trottoir, allée | IGN 2024 et photos du 12/01/2025. Ne pas prendre le levé GAM : les trottoirs du Vercors ont été refaits jusqu'au 30/01/2026. |
| CHG-005 | Base vie SE du carrefour, x 16..31, y −33..−17 | Objet absent en 2022 | IGN 2024, Pléiades 2025, photos du 12/01/2025 |
| CHG-006 / 007 | Rive SE de Verdun NE, bande de 3 à 24 m, x 20..125 | Abords : clôtures et bungalows en 2024, haies et parkings en 2025 ; entrée de parking vers (72 ; 62) | **Photos du 18/05/2025** (8 Panoramax et 14 Mapillary calées), Pléiades 2025 |
| CHG-008 | Approche NE sur Verdun, x 1..66, y −1..66 | **Marquages** : zone hachurée et répartition des voies. Les bordures restent valables. | IGN 2024, ortho-photos tirées des 360° calées (`outils/photo_ortho.py`), levé GAM (cohérent avec 2024) |
| CHG-009 | Cœur, x −16..10, y −12..18, et voie SO | Texture : reprises d'enrobé | IGN 2024 pour l'emprise, photos 2024-08 et 2025-05 pour l'aspect |
| CHG-010 | Verdun SO, chaussée NO, de (−131 ; −128) à (−45 ; −44) | Texture : bande de tranchée de 3,5 m | IGN 2024 et photos |
| CHG-011 | Chemin de la Revirée, de (−60 ; 105) à (−22 ; 37) | Texture : bande de tranchée de 2,5 m | IGN 2024 |
| CHG-012 / 020 | Immeuble nord (h 20,5 m) ; toit commercial NO | Apparence : toit et façade | IGN 2024 et photos du 18/05/2025 |
| CHG-013 à 017 | Parc est | 4 arbres abattus, 5 jeunes plantés : les hauteurs LiDAR 2021 sont fausses | IGN et IRC 2024 |
| CHG-018 | Noue du parc est | Lits minéraux d'août 2024, plus visibles en 2025 (faible) | Pléiades 2025, à confirmer |
| CHG-021 | Cœurs d'îlot du quartier est, x 100..150, y 5..35 et x 115..142, y 62..95 | Terre nue sur l'IGN 2024, aménagés en 2025 : ni le PCRS 2022 ni l'IGN 2024 ne valent | Pléiades 2025, levé GAM à vérifier |
| CHG-019 | Avenue du Vercors (bande de ±15 m) | **Risque** : travaux annoncés d'avril à novembre 2025, non observés | État du 12/01/2025 et Pléiades 2025 |

**Valable tel quel pour une date cible au printemps 2025 :**

- le PCRS 2022 en dehors de ces zones, soit **69,8 %** de l'emprise sur aucune zone observée (hors texture : 71,5 %) ;
- la géométrie et les marquages du cœur, hors texture de chaussée ;
- l'arrêt La Revirée sur Verdun SO (abri, quai, zigzag jaune), identique en 2022 et en 2024 ;
- les pistes cyclables de Verdun et du Vercors ;
- le secteur ouest (Paquet Jardin) et le secteur nord-ouest.

**Pour les sources vectorielles :**

- **Levé topo GAM.** 33,9 % de la longueur des bordures (2 327 m sur 6 868) et 26,3 % des marquages (669 m sur 2 544) tombent dans des zones changées depuis 2022. Ce sont précisément les zones où le levé GAM décrit l'état 2024-2025 : il y est utile.
- **PCRS vecteur 2019.** 10,3 % de sa longueur est périmée (432 m sur 4 192).
- **Description V2 actuelle.** 27,8 % de la longueur des bordures de `description/base` (1 918 m sur 6 896) tombe dans ces zones.

---

## 3. Le levé GAM : c'est l'état après travaux, pas l'état avant

- `vector/gam_topo_sol_*` et `etat_2026/*_L93` sont le **même levé** : même DWG `Meylan_Topo.dwg`, 622/622 bordures, 409/409 lignes de signalisation, 429/429 limites et 12/12 caniveaux, 0 cm d'écart. Mesure refaite ici, et cohérente avec `inventaire/sources/gam_datation.json` et `inventaire/sol/comparaison_gam_etat2026.json`.
- Le levé décrit le carrefour **après travaux**. Dans `planches/topo_gam/verdun_SO_mid.jpg`, le zigzag et les quais de l'arrêt La Revirée qu'il contient (cyan, x −50..−25) ne coïncident ni avec le PCRS 2022 ni avec l'IGN 2024 : les quais ont été « déplacés et mutualisés » pendant les travaux (panneau `data/raw/docs_web/meylan_fr/Panneau-Amenagement-carrefour-Verdun-Vercors.pdf`). Au cœur (`topo_gam/coeur.jpg`), les nez d'îlots du levé ne correspondent pas non plus aux images de 2022 ou de 2024.
- Dans le secteur est et sur Verdun NE, en revanche, le levé coïncide avec l'IGN 2024 (`topo_gam/est.jpg`, `topo_gam/verdun_ne.jpg`). C'est donc la meilleure source vectorielle pour CHG-001 à CHG-003 et CHG-008, à condition de rester hors de l'emprise des travaux 2025.
- Conclusion : **le dépôt ne contient aucun levé vectoriel daté d'avant travaux** en dehors du PCRS vecteur 2019 (`date_leve` 2019-01-01, précision 10 cm), qui est antérieur au quartier est.

---

## 4. Chronologie observée

| Date | Source | Observation |
|---|---|---|
| 2022-03-05 | Mapillary, 11 photos (Vercors, vers le nord) | État d'avant le quartier ; rive est du Vercors en chantier |
| **2022-05-10** | PCRS 5 cm | Quartier est en gros œuvre (grue, voiles de 925 et 929-931), terre nue ailleurs ; base vie de chantier |
| 2022-06-10 | Mapillary, 32 photos (axe de Verdun) | Échafaudages et filets sur l'immeuble nord (CHG-012) ; palissade blanche sur la rive SE de Verdun NE |
| 2023 (SPOT 1,5 m) | IGN | Immeubles est déjà élevés (toits et ombres) |
| 2023-03-18 | Panoramax 25 et Mapillary 28 (axe de Verdun) | Verdun NE **sans** zone hachurée (photos d7279ab8, e005e86b) |
| 2024-02-24 | Mapillary, 76 photos (Revirée, gymnase) | Chaussée de la Revirée uniforme, sans tranchée |
| avril 2024 | MMV-166 | 1re phase du réseau de chaleur urbain de Meylan |
| **2024-05-01** | Panoramax, 26 photos | **Chantier de tranchées au cœur** (pelles, clôtures Heras, enrobé découpé à l'angle NE) ; pelles et barrières sur la rive SE de Verdun NE |
| **2024-08-09** | IGN BD ORTHO 20 cm RVB et IRC | Reprises d'enrobé au cœur, bandes de tranchée sur Verdun SO et la Revirée, quartier est livré, base vie SE, zone hachurée sur Verdun NE |
| 2024-08-24 | Panoramax 49 et Mapillary 52 (mêmes prises), 36 poses calées | Cœur identique à l'IGN ; clôtures et bungalows le long de Verdun NE ; îlot neuf aux Mitaillères |
| 2025-01-12 | Panoramax, 12 photos (vélo sur le Vercors) | Base vie bleue, STOP aux Mitaillères, rive est du Vercors finie |
| 2025 (date non publiée) | Pléiades 50 cm | Carrefour dans l'état 2024, sans emprise de chantier au cœur ; ombres plus courtes qu'au 09/08/2024 (soleil plus haut) et feuillage complet, donc de mai à juillet, probablement avant le 23/06 |
| avril → novembre 2025 | Panneau C1 | Travaux annoncés sur l'avenue du Vercors (traversées, regroupement d'arrêts) |
| **2025-05-18** | Panoramax 19 et Mapillary 21, 22 poses calées | **Aucun chantier visible** au cœur, sur Verdun ou à l'entrée du Vercors (119d9094, azimuts 152 à 168) ; abords de Verdun NE réaménagés |
| 2025-06-23 → 12-05 | Commune | Travaux du carrefour |
| 2025-07-04 | BD TOPO | Création des 11 emprises du quartier est (date de saisie, pas de construction) |
| 2025-08-31 | Panoramax, 35 photos | Pendant les travaux (hors fenêtre) |

---

## 5. Inventaire par thème (constats, y compris les absences de changement)

- **Chaussée.**
  - Reprises d'enrobé au cœur (CHG-009). La bande sombre de la voie SO couvre ≈ 4,5 m × 22 m.
  - Bandes de tranchée refermées sur Verdun SO (CHG-010) et sur la Revirée (CHG-011).
  - Le détecteur automatique d'enrobé neuf (`outils/enrobes_neufs.py`) trouve 6 135 m² de cellules plus sombres en 2024. Une bonne partie se trouve dans le quartier est, où le sol est neuf, et une autre vient d'ombres. Seules les bandes vues à l'œil sont retenues.
  - Aucune modification de bordure de chaussée au cœur ni sur Verdun.
- **Marquages.**
  - Verdun NE refait entre le 18/03/2023 et le 09/08/2024 (CHG-008).
  - Cœur : zébras des 4 traversées, traversées cyclables jaunes et vertes, cercles « 50 » et flèches aux mêmes places en 2022, 2024 et 2025 (`revue_zoom/coeur_3dates.jpg` ; photos 2023-03, 2024-05, 2024-08 et 2025-05).
  - Verdun SO : zigzag et flèches inchangés.
  - La carte de peinture automatique (`planches/peinture/`) est dominée par la différence de résolution entre 5 et 20 cm et par les voitures. Elle ne sert que d'indice.
- **Bordures, îlots, trottoirs.** Changements limités au quartier est et à ses raccords : CHG-002, la branche est et l'îlot des Mitaillères (CHG-003), la rive est du Vercors (CHG-004). Aucun îlot du cœur ni de Verdun n'a changé avant les travaux.
- **Pistes cyclables.** Pistes bidirectionnelles de Verdun et du Vercors inchangées. Dans OSM, seuls des tags ont changé (largeurs ajoutées en 2024).
- **Arbres.**
  - 4 sujets abattus dans le parc est (CHG-013 à 016) et 5 jeunes plantés (CHG-017). Ce sont les observations OR-V-003 à OR-V-011 de la revue précédente, revérifiées.
  - L'alignement de Verdun et les arbres du cœur sont inchangés.
  - La bande plantée ouest du Vercors apparaît en terre nue le 12/01/2025, mais verte en mai 2022 et en août 2024 : c'est un massif en hiver, que je ne retiens pas.
  - La couche « évolution de la canopée 2021-2024 » de la Métropole (COSIA, téléchargée par un autre atelier dans `data/sites/paquet_jardin/avant_travaux/gam_geoflux_2026-10-11/`) confirme une perte de 117 m² au point de CHG-013 (143 ; −57). Elle signale aussi des pertes de 42 à 118 m² le long de la rive ouest du Vercors (x 7..23, y −127..−61). Je ne les ai pas confirmées hiver contre hiver : photos Mapillary du 05/03/2022 contre Panoramax du 12/01/2025 (`photos_non_versionnees/sequences/vercors_hiver_vers_N.jpg`, `vercors_hiver_vers_S.jpg`). L'intervalle COSIA commence d'ailleurs avant mai 2022. Je n'en fais pas d'entité ; c'est à vérifier.
- **Mobilier.**
  - Totem P+R « M » de la Revirée présent dès 2020.
  - L'armoire de rue (7,6 ; −37,1), ajoutée à OSM le 25/04/2025, existe déjà sur le PCRS 2022 (`revue_zoom/armoire_vercors_zoom.jpg`).
  - Les caméras de surveillance ajoutées à OSM en mai et juin 2025 sont sur un mât déjà visible le 18/03/2023 (`chrono_camera_coeur`).
  - Cédez-le-passage et panneau sur la contre-allée NO de Verdun NE : vus en 2024 et 2025, ajoutés à OSM le 18/09/2024.
- **Bâtiments.** Quartier est (CHG-001), base vie (CHG-005), rénovations de l'immeuble nord (CHG-012) et d'un toit au NO (CHG-020). L'emprise BD TOPO 2025 …537 (x −129..−115, y −98..−83) ne montre aucun changement visible : je l'ai exclue.
- **Transports en commun.** Les arrêts La Revirée gardent leurs positions de 2022 jusqu'en mai 2025 (ortho et photos). Dans OSM, seul le réseau change (TAG → M réso, 03/01/2025). Le déplacement et la mutualisation des quais datent des travaux de 2025.
- **Travaux préparatoires avant le 23/06/2025.** Rien sur les 40 photos du 18/05/2025 : ni clôture, ni panneau « travaux », ni marquage jaune provisoire, au cœur comme sur Verdun. La base vie SE existe depuis août 2024 au plus tard, et rien ne la rattache aux travaux de 2025. Les tranchées de 2024 sont antérieures de plus d'un an. Au-delà de l'entrée du Vercors (vue sans chantier le 18/05/2025), aucune photo du Vercors entre le 12/01/2025 et le 23/06/2025 (CHG-019).

---

## 6. Méthode et sources

- **Orthos, recalées dans le cadre du PCRS 2022** (`recon/pcg/enrichir/orthos_recentes.py`, `recalage.json`) :
  - PCRS 5 cm du 10/05/2022 ;
  - IGN BD ORTHO 2024 RVB et IRC, PVA du 09/08/2024 d'après le graphe de mosaïquage WFS, recalée de (+0,035 ; +0,029) m ;
  - Pléiades 2025, recalée de (+0,47 ; +1,17) m, avec des toits déversés de 5 à 6 m ;
  - SPOT 2022 à 2025 à 1,5 m, non recalées.
  - Service : `https://data.geopf.fr/wms-r`.
- **Revue à l'œil :**
  - 16 planches de 75 m aux 3 dates (`planches/revue_75m/`) ;
  - 21 zooms (`planches/revue_zoom/`) ;
  - le levé GAM superposé (`planches/topo_gam/`) ;
  - les ombres (`planches/ombres/`).
- **Détecteurs automatiques, comme candidats seulement :**
  - `outils/detection_auto.py` (2022 → 2024, 70 composantes ≥ 12 m², hors végétation, ombres et toits) ;
  - `outils/diff_2024_2025.py` ;
  - `outils/enrobes_neufs.py` ;
  - `outils/peinture_2022_2024.py`.
- **Photos Panoramax et Mapillary** (CC-BY-SA 4.0), avec les poses de `recon/out/paquet_jardin/v2/enrichi/poses/poses.json` et `.../mapillary/poses/poses_mapillary.json`, sinon les poses a priori :
  - chronologies d'un point (`outils/chrono.py`) ;
  - paires et séquences homologues (`paires.py`, `sequences.py`) ;
  - planches 360° orientées au nord (`planche_360.py`) ;
  - **ortho-photos de sol** tirées des 360° calées (`photo_ortho.py`).
  - Toutes ces images sont dans `photos_non_versionnees/` (non versionné) ; l'attribution figure dans les `.json` voisins. Les identifiants complets et les liens sont dans les `preuve` du GeoJSON.
  - Jeton Mapillary : non utilisé, aucun nouveau téléchargement Mapillary.
- **OSM historique.** Overpass `[date:"2022-05-10"]` et `[date:"2025-06-20"]` sur 45,2058..45,2095 N × 5,7652..5,7712 E (`https://overpass-api.de/api/interpreter`). Les instantanés sont dans `data/sites/paquet_jardin/avant_travaux/osm/`, le diff dans `donnees/osm_diff_2022-05-10_2025-06-20.json`. 207 objets diffèrent (106 ajoutés, 101 modifiés), surtout des tags. Les dates OSM sont des dates de **cartographie** ; je ne les utilise que comme indices.
- **Documents.**
  - `data/raw/docs_web/meylan_fr/Panneau-generique-travaux-d-amelioration-ligne-C1.pdf` : calendrier C1.
  - `MMV-165.pdf` et `MMV-166-decembre25-janvier26.pdf` : point travaux C1, réseau de chaleur urbain (1re phase en avril 2024).
- **Confiance.**
  - `haute` : vu sur au moins 2 sources indépendantes datées, dont une ortho.
  - `moyenne` : une seule source nette, ou pose a priori.
  - `faible` : indice seul.
  - `observe=false` : annoncé, non constaté.

**Limites :**

- L'IGN 2024 (20 cm) ne montre pas les petits objets : potelets, panneaux.
- Les photos 2024-2025 suivent surtout l'axe de Verdun et du Vercors. La Revirée nord n'a pas de photo après le 24/02/2024.
- La date Pléiades est estimée, pas mesurée.
- Les hauteurs des immeubles neufs restent à mesurer.
- La végétation basse de la rive ouest du Vercors (haie, massifs) n'est pas tranchée entre 2022 et 2025 (voir § 5, Arbres).

## 7. Reproduire

Depuis `recon/out/paquet_jardin/v2_avant_travaux/inventaire/changements/outils/` (Python, lecture seule du dépôt) :

```
python vue_ensemble.py ; python zones_75m.py ; python superpose_topo.py
python detection_auto.py ; python diff_2024_2025.py ; python enrobes_neufs.py ; python composantes_enrobe.py
python -I osm_diff.py <snapshot_2022-05-10.json> <snapshot_2025-06-20.json> ../donnees/osm_diff_2022-05-10_2025-06-20.json
python -I construire_changements.py      # GeoJSON + planches/zones + carte d'ensemble
python -I statistiques.py                # donnees/statistiques.json
python -I chrono.py <nom> x y ; python -I paires.py <nom> az1,az2 <ids> ; python -I photo_ortho.py <nom> x0 y0 x1 y1
```
