# Audit du pipeline V2 : rendre la chaîne paramétrable par une date cible (état avant travaux)

Audit en lecture seule du 11/10/2026. Aucun fichier source n'a été modifié. Les numéros de ligne renvoient à un **instantané figé du code** (`recon/pcg`, copié le 2026-10-11 à 08:32:34 ; empreintes SHA-1 dans `instantane_code_sha1.txt`). Un autre workflow modifie le code en parallèle : à 08:46, deux fichiers avaient changé depuis l'instantané. Dans `controle/ctl_reseau.py`, les lignes au-delà de 757 sont décalées de +8. Dans `decrire/marquages_chronovelo.py`, les lignes 155 à 181 ont changé, mais la ligne 29 citée ici est intacte.

Fichiers de ce dossier :

| Fichier | Contenu |
|---|---|
| `AUDIT_PIPELINE.md` | ce rapport |
| `occurrences_cablees.csv` / `.json` | relevé automatique : 1 505 lignes dans 157 fichiers, classées en 11 catégories, avec l'extrait (`outils/scanner_occurrences.py`). C'est un signal, pas un verdict : la catégorie COUVERTURE_COEUR attrape aussi « strictement ». Les tableaux ci-dessous sont vérifiés à la main. |
| `proposition_etat_cible_avant_travaux.json` | configuration proposée de l'état avant travaux (non branchée) |
| `proposition_etat_cible_2026.json` | configuration 2026 qui doit reproduire à l'octet les sorties actuelles, y compris les constantes héritées qui se contredisent |
| `instantane_code_sha1.txt` | empreintes des 250 fichiers .py/.md/.json audités |

---

## 0. En bref

1. **Le câblage sur 2026 se trouve à quatre niveaux, pas seulement dans les chemins.**
   - (a) Chemins de sortie : `recon/out/paquet_jardin/v2/...` apparaît en dur dans 9 modules hors `decrire`. Dans `decrire`, 19 modules lisent `commun.SORTIE`.
   - (b) Références de données de l'état 2026 :
     - paquet v1 `*_2026` : `surfaces_2026`, `marquages_2026`, `relief_zones_2026`, `lanes_2026`, `manoeuvres_2026` ;
     - `paquet_jardin_2026.xodr` ;
     - MNT « sol nu octobre 2026 » ;
     - levé GAM `etat_2026` ;
     - plan projet 2025.
   - (c) Règles de chronologie : dates des travaux, classes de date relatives aux travaux, `valide_2026`, couverture stricte, priorité « photo_2026 d'abord ».
   - (d) Sémantique des objets : `statut_2026`, présence 2026 (Q4), « absent 2026 », « planté 2025 », « déduit 2026 ».
2. **La fin des travaux est codée de quatre façons différentes** selon le module :
   - 2025-08-31 dans `coherence_objets` ;
   - 2025-12-05 dans fusion, résolution, cohérence, mapillary et orthos ;
   - 2026-01-30 dans `orthos_recentes` ;
   - 2026-01-31 dans `gcp`.

   Le début est lui aussi codé de deux façons : 2025-06-01 dans `gcp` et 2025-06-23 dans `orthos_recentes`. Ce sont 11 constantes ou littéraux répartis dans 9 fichiers (§ 2.2). Une configuration unique `etat_cible` est donc nécessaire, même pour l'état 2026.
3. **`gam_topo_sol_*` et `etat_2026/*_L93` sont le même levé** (mesuré § 2.3) :
   - bordures : 622/622 lignes et 6 983 m de chaque côté ;
   - limites de revêtement : 429/429 lignes ;
   - signalisation : 409/409 lignes ;
   - caniveaux : 12/12 lignes ;
   - 100 % des sommets échantillonnés sont à moins de 5 cm d'un sommet de l'autre couche ;
   - même DWG : `Meylan_Topo.dwg`, `/sigdata/Planotheque/esp_publics/MEYLAN/PLAN_GLOBAL/`.

   **Le dépôt ne contient donc aucun levé vectoriel d'avant travaux** en dehors du PCRS vecteur (`gam_*_pcrs`, `date_leve` 2019-01-01, précision 10 cm en plan et 20 cm en altitude).
4. **Trois entrées sont absentes et non régénérables**, car `recon/stages` n'est pas dans le dépôt :
   - un `.xodr` d'avant travaux (le seul `.xodr` porte `etat = octobre 2026 (apres travaux C1 2025)`, `vendor = recon/stages/opendrive.py`) ;
   - le MNT 2021 en flottant (`dtm_sol_10cm.tif`, cité par `README_relief.md`, n'est pas sur le disque ; les rasters `data/sites/paquet_jardin/lidar/dtm_*` sont des aperçus JPEG en RVB, dalles de 1 000 × 1 000 px sans décodage d'altitude documenté dans `index.json` : au mieux 8 bits sur 6,8 m, soit environ 2,7 cm, ce qui ne suffit pas pour des vues de bordure) ;
   - les couches v1 « avant ».

   Ces trois éléments sont sur le chemin critique.
5. **Ce que l'état avant travaux gagne :**
   - **Observations** : 1 392 des 1 475 observations du recensement (94,4 %) sont datées entre le 01/01/2022 et le 22/06/2025. Seules 59 sont postérieures aux travaux et 18 datent du chantier.
   - **Couverture stricte actuelle du cœur** : 9,0 % (226/2 522, dont 0 après travaux). Elle est faite à 100 % de preuves d'avant travaux, qui deviendraient directement probantes. Ajoutées aux 258 « indice seulement » et aux 86 « non valable 2026 », elles bornent la couverture stricte avant travaux du cœur entre 9,0 % et 22,6 %, avant tout nouveau recensement.
   - **Bordures** : 68,0 % de la longueur de `bordures_hauteurs` (hors travaux, existantes en 2021) est valable telle quelle. 13,1 % l'est encore si la date cible suit la livraison du quartier est (2024). 11,5 % est mesuré au LiDAR 2021 dans l'emprise. Il reste 5,9 % à reconstruire et 1,4 % (plan projet) à retirer.
6. **Ce qui est réutilisable tel quel :**
   - les 10 HDA `pj_*` et le dossier `hda/commun` (ils ne lisent que des attributs ; seul le chemin par défaut est câblé) ;
   - les specs normatives et 213 des 255 règles de conception ;
   - le solveur de cohérence, la régularisation, la partition, le nivellement (le MNT y est injecté) et les détecteurs ;
   - les outils et les **poses déjà calculées** (65 Panoramax, 400 Mapillary : une pose ne dépend pas de l'état).

   **Ce qui doit être réécrit** : la logique de date de la fusion (`fusion_recensement.py`, 262 occurrences dans 4 415 lignes), une partie de la cohérence (Q3, Q4, Q8), les règles RES-* temporelles, les tables d'âge et de matériau de `bordures` / `surfaces` / `ilots`, et les références du contrôleur. Ce dernier compte **48 règles sur 128** qui dépendent de l'état, dont 31 du réseau `.xodr`, des voies et des manœuvres 2026.
7. **Proposition** :
   - un module `recon/pcg/etat/etat_cible.py`, avec deux configurations (2026 et avant travaux) ;
   - une variable `PJ_ETAT` (et `--etat`) ;
   - une fonction de validité temporelle unique `valide(date_obs, emprise) -> {vrai | incertain | faux}` fondée sur une table d'événements datés et localisés ;
   - des sorties sous `recon/out/paquet_jardin/v2_avant_travaux/` (§ 4) ;
   - une non-régression à l'octet de l'état 2026.

   Effort total : environ **15 à 25 jours-agent**, dont 4 à 8 pour produire les données d'avant travaux qui manquent.

---

## 1. Périmètre et méthode

- **Code audité** : `recon/pcg/{decrire, enrichir, houdini, controle, ue, schema, specs_outils}`, plus `ARCHITECTURE.md` et `README.md`. Cela fait 466 fichiers, dont 229 Python.
- **Données consultées en lecture**, pour chiffrer et non pour modifier :
  - `recon/out/paquet_jardin/package/donnees` (paquet v1) ;
  - `data/sites/paquet_jardin/{etat_2026, vector, lidar}` ;
  - `recon/out/paquet_jardin/v2/{enrichi, description/enrichi, fabrique_hda}` ;
  - `assets/specs/*.json`, en lecture seule ; aucune modification, en particulier sur `bordures`, `vegetation`, `mobilier` et `carla_correspondances`.
- **Relevé automatique** : `outils/scanner_occurrences.py`. Il cherche par expressions régulières les chemins `v2`, `etat_2026`, les couches `*_2026`, le MNT 2026, le plan 2025, l'ortho 2022, le PCRS ou `gam_topo`, les dates et mots de travaux, la date d'état, `terrain2026` et la couverture stricte. Les scripts Python lancés sur les données l'ont été avec `-I`.

Le relevé, par module (nombre de lignes, une ligne pouvant porter plusieurs catégories) :

| module | SORTIE_V2 | GAM_2026 | V1_2026 | MNT_2026 | PLAN_2025 | ORTHO_2022 | PCRS/GAM_TOPO | CHRONO | DATE_ETAT | TERRAIN_2026 | total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| decrire | 29 | 66 | 81 | 42 | 95 | 102 | 14 | 217 | 8 | 15 | 722 |
| enrichir | 15 | 26 | 19 | 13 | 4 | 57 | 7 | 293 | 1 | 2 | 580 |
| houdini | 31 | 3 | 6 | 15 | 6 | 6 | 0 | 18 | 3 | 0 | 94 |
| controle | 13 | 4 | 8 | 2 | 20 | 17 | 0 | 7 | 1 | 0 | 82 |
| ue | 29 | 4 | 3 | 4 | 2 | 0 | 0 | 11 | 20 | 0 | 73 |
| schema | 0 | 0 | 0 | 3 | 4 | 4 | 2 | 6 | 3 | 4 | 26 |
| specs_outils | 0 | 0 | 4 | 2 | 2 | 3 | 1 | 9 | 0 | 0 | 29 |
| ARCHITECTURE.md + README.md | 4 | 5 | 0 | 8 | 6 | 4 | 2 | 10 | 4 | 3 | 50 |

Les fichiers les plus chargés :

| fichier | lignes relevées |
|---|---|
| `enrichir/fusion_recensement.py` | 341 |
| `enrichir/orthos_recentes.py` | 60 |
| `enrichir/gcp.py` | 49 |
| `decrire/marquages.py` | 42 |
| `enrichir/mapillary.py` | 37 |
| `controle/ctl_detection.py` | 35 |
| `decrire/bordures.py` | 32 |
| `decrire/marquages_sources.py` | 31 |
| `decrire/coherence_sorties.py` | 30 |

**Effort** : S ≤ 0,5 jour-agent ; M de 0,5 à 2 ; L de 2 à 5 ; XL au-delà de 5.

**Risque** : risque de casser l'état 2026, ou de produire un état avant travaux faux.

---

## 2. Constats transverses

### 2.1 Quatre niveaux de câblage

| Niveau | Exemples (fichier:ligne) | Conséquence |
|---|---|---|
| Chemins | `decrire/commun.py:25` `SORTIE = …/v2/description` ; `controle/ctl_commun.py:25-29` ; `houdini/fabriquer_hda.py:45-46` ; `enrichir/fusion_recensement.py:47-52` ; `hda/pj_lire_description/construire.py:22` (chemin absolu `D:/…/v2/description/base`) | Une exécution « avant travaux » écraserait `v2`, que l'autre workflow utilise. |
| Références de données 2026 | `decrire/composer.py:34-54`, `sol_composer.py:25-37`, `marquages.py:66-73`, `xodr_echantillonne.py:39-40`, `ctl_commun.py:592-652`, `commun.py:121-126` (MNT) | La géométrie, les indices de classe, le réseau et le Z sont ceux de 2026. |
| Chronologie | `marquages_sources.py:35-51`, `fusion_recensement.py:61-79` et `REGLES` (`:96-140`), `resoudre_regles.py:11-107`, `coherence_objets.py:25-26, 204-224`, `coherence_photos.py:43, 67-68`, `gcp.py:37-38` | Le temps est réduit à « avant ou après le 05/12/2025 », avec la cible implicite T = octobre 2026. |
| Sémantique des objets | `statut_2026` (paquet v1, lu par `gcp.py:65`, `triangulation.py:206`, `coherence_objets.py:86`, `ue/vegetation/arbres.py:140-143`, `ctl_sol.py:1076, 1771`), `presence_2026` (`coherence_presence.py`), verdict `absent_2026` (fusion, résolution) | Un objet « absent 2026 » retiré pendant les travaux était présent avant. Aujourd'hui il est filtré partout, par exemple les 10 arbres retirés que UE ignore. |

### 2.2 Constantes de travaux : une même notion, onze valeurs

| fichier:ligne | constante | valeur |
|---|---|---|
| `enrichir/orthos_recentes.py:47` | `DEBUT_TRAVAUX, FIN_TRAVAUX, FIN_TROTTOIRS_VERCORS` | 2025-06-23, 2025-12-05, 2026-01-30 |
| `enrichir/fusion_recensement.py:61` | `FIN_TRAVAUX` | 2025-12-05 |
| `decrire/resoudre_regles.py:107` | `FIN_TRAVAUX` | 2025-12-05 |
| `decrire/coherence_photos.py:43` | `FIN_TRAVAUX_2025` | 2025-12-05 |
| `decrire/coherence_mesures.py:60` | `FIN_TRAVAUX_2025` | 2025-12-05 |
| `decrire/coherence_marquages.py:607` | littéral | « 2025-12-05 » |
| `decrire/coherence_objets.py:25-26` | `FIN_TRAVAUX`, `FIN_TRAVAUX_REEL` | **2025-08-31**, 2025-12-05 |
| `decrire/coherence_objets.py:209` | littéral | « 2025-08-31 » |
| `enrichir/gcp.py:37-38` | `DEBUT_TRAVAUX_2025`, `FIN_TRAVAUX_2025` | **2025-06-01**, **2026-01-31** |
| `enrichir/gcp.py:131, 206` | littéral (fin de validité « avant ») | « 2025-05-31 » |
| `enrichir/mapillary.py:764, 782, 950` | littéraux | « 2025-12-05 » |

Proposition : une table `evenements` dans `etat_cible`, avec un identifiant, des dates de début et de fin et une emprise par événement. La configuration 2026 garde provisoirement ces valeurs dans `constantes_heritees` pour l'identité à l'octet. L'harmonisation est une décision séparée, car elle changera les sorties 2026.

### 2.3 Sources d'avant travaux réellement disponibles

| Source | Date | Valeur pour l'état avant travaux | Mesure faite pendant l'audit |
|---|---|---|---|
| Levé GAM `etat_2026/*_L93` = `vector/gam_topo_sol_*` | ≈ 2025-12 selon le code (`fusion_recensement.py:106`, FUS-VAL-03 : « levé GAM postérieur aux travaux ≈ 2025-12 ») ; à dater | Valable **hors emprise des travaux** seulement | Les deux couches sont identiques : 622/622 bordures (6 983 m), 429/429 limites (4 598 m), 409/409 signalisations (2 544 m), 12/12 caniveaux (139 m) ; 100 % des sommets à moins de 5 cm ; même DWG. `sol_site.py:64-66` le dit déjà (« même calque en WGS84 »). |
| PCRS vecteur `gam_*_pcrs` | `date_leve` 2019-01-01, producteur geofit, précision 10 cm en plan et 20 cm en altitude | Seul vecteur d'avant travaux de l'emprise (107 limites de voirie, 35 changements de revêtement). Antérieur à la construction du secteur est. | `bordures_hauteurs` n'en garde que les lignes absentes du levé GAM, et **hors** zone de travaux : 1 395 tronçons sur 1 396 sont hors zone. Les bordures supprimées par les travaux n'y sont donc pas. |
| LiDAR HD 2021 | 12/08 et 06/09/2021 | `bordures_hauteurs` porte `h_lidar_2021_m`, `z_fil_eau_2021_m`, `z_dessus_2021_m` (1 326/1 585 tronçons de la zone de travaux ont une mesure) | MNT flottant absent du disque ; seulement des aperçus JPEG en RVB (`lidar/dtm_15cm`, `dtm_25cm`) |
| Ortho PCRS 5 cm | 10/05/2022 | Marquages et limites, sauf dans le secteur construit en 2023-2024 | 624 observations (ortho_A + ortho_B) |
| BD ORTHO IGN 20 cm recalée à 4 cm | 09/08/2024 | Présence, zébras, flèches et revêtements ; trop grossière pour les lignes fines | 202 observations ; `ortho_recentes/planches/carte_changements_2022_2024.jpg` existe |
| Pléiades | 2025, date non publiée | Masses seulement | — |
| Photos Panoramax et Mapillary | 2022 à 2025-06 | 2023 : 22 observations ; 2024 : 493 ; 2025-S1 : 253 | Poses Panoramax acceptées : 2024-08-24 (5) et 2025-05-18 (8). Mapillary posées : 2022 (44), 2023-03 (28), 2024-02 (76), 2024-08 (52), 2025-05 (21). |
| Paquet v1 | état 2026 | Indice hors emprise ; dans l'emprise, il décrit l'état après travaux (contre-indice) | Surfaces : 471 (279 inchange_2022, 122 construit_2023_2024, 70 modifie_2025). Marquages : 996 (516 conserve, 424 refait_2025, 56 resurface_2025). Arbres : 467 (432 existants, 15 « planté 2025 », 10 « absent 2026 », 10 à vérifier). Mobilier : 204 (135 existants, 45 « 2026 confirmé », 14 « déduit 2026 », 10 à vérifier). |

### 2.4 Entrées non régénérables (générateur `recon/stages` absent)

| Entrée | Utilisée par | Ce qu'il faut pour l'état avant travaux |
|---|---|---|
| `package/paquet_jardin_2026.xodr` : en-tête `etat="octobre 2026 (apres travaux C1 2025)"`, 20 routes, 1 jonction, 31 signaux | `xodr_echantillonne.py:39`, `marquages_lignes`, `nivellement_xodr`, `regulariser.py:84-88` (GQ-ORI-001), `ctl_commun.py:592`, 31 règles du contrôleur | `paquet_jardin_avant_travaux.xodr` : reprendre les routes hors jonction si elles n'ont pas changé, et refaire la jonction et les voies du cœur depuis le PCRS 2019 et l'ortho 2022 (L à XL) |
| `opendrive/lanes_2026.geojson`, `manoeuvres_2026.json` | `sol_site.py:385-388`, `surfaces.py:259-263`, `marquages_inference.py:191`, `ctl_commun.py:615-635`, `coherence_carte.py:301-305` | Dérivés du `.xodr` d'avant travaux, avec les attendus de flèches par voie (INF-FLE-004) |
| `relief/heightmap_3025_10cm` (sol nu octobre 2026 modélisé) | `commun.MNT` → bordures, îlots, nivellement, cohérence, `camera.z_sol`, `projection`, UE panoramax | Sol nu 2021 en flottant, à 10 cm : méthode de `README_relief.md`, étapes 1 et 3, sur les dalles LiDAR HD IGN classées (publiques). Le régalage des Saules Blancs est à garder si T ≥ 2024. |
| `relief/relief_zones_2026.geojson` (chaussée 2026, zones rehaussées en 2025) | `sol_site.py:183-201`, `contexte.py:57-96`, `marquages_verifier.py:48-67`, `marquages_controles.py:191` | Masque de chaussée d'avant travaux. Les zones « rehaussées en 2025 » deviennent l'emprise de l'événement TRV-C1-2025. |
| `surfaces/surfaces_2026`, `marquages/marquages_2026` | indices v1 dans `sol_site`, `marquages_indices_v1`, `marquages_sources.zones()`, `gcp`, cohérence | Gardés comme **indices hors emprise** et comme **emprise datée** (`etat`, `zone`). Dans l'emprise, il faut des indices d'avant travaux tirés de l'ortho 2022 et 2024. |

### 2.5 Évolutions 2021-2025 non tracées : le temps n'est pas binaire

Le code suppose qu'il n'y a que deux états : LiDAR 2021 / ortho 2022 d'un côté, 2026 de l'autre. `decrire/surfaces.py:91-94` (surf_0344) en donne un contre-exemple. Le LiDAR 2021 y montre un prolongement de terre-plein surélevé de +0,16 m, alors que la photo du 18/05/2025, prise **avant** les travaux, montre un terre-plein **peint à niveau**. Il y a donc eu au moins un changement entre 2021 et mai 2025 hors chantier C1. La table d'événements doit pouvoir recevoir des événements ponctuels, constatés par comparaison entre l'ortho 2022, l'ortho 2024 et les photos.

---

## 3. Proposition : le paramètre `etat_cible`

### 3.1 Contenu (voir `proposition_etat_cible_*.json`)

```
etat_cible = {
  id, libelle, date_cible (T), date_etat, fenetre_preuves {de, a, preferee},
  saison {nom, mois, feuillage, jaunissement, feuilles_mortes_sol, soleil},
  evenements [{id, type, debut, fin, emprise {sources de l'emprise, marge_m}}],
  sources {gam, pcrs2019, lidar2021, ortho2022, ortho2024, pleiades2025, photos, plan2025, v1, regle :
           fichiers, date, r, admissible, tolerance_m},
  v_temporelle_marquages {source: {etat_de_zone: poids}},
  regles_chronologie {validite, classes_date, priorite, absence, statut_objets_v1, age_surfaces_v1,
                      marquages_v1_zone, bordures_hauteurs},
  references {xodr, lanes, manoeuvres, mnt, surfaces_v1, marquages_v1, relief_zones, bordures_hauteurs, objets_v1},
  dossier_sortie, entrees_partagees {poses, observations brutes}, ue {niveau, racine_contenu_etat},
  schema_description {version, date_etat, z_ref, src_ajoutees}
}
```

Cela couvre les quatre paramètres demandés :

| Paramètre demandé | Champs de `etat_cible` |
|---|---|
| date | `date_cible`, `date_etat`, `fenetre_preuves` |
| sources_prioritaires | `sources` et `v_temporelle_marquages` |
| regles_chronologie | `evenements` et `regles_chronologie` |
| dossier_sortie | `dossier_sortie` |

### 3.2 Une seule fonction de validité temporelle

Elle remplace `valide_2026`, FUS-DATE-02, `apres_travaux()`, `anterieure_travaux()`, `valide_pour_photo()` et les tranches probantes.

> Une observation datée d vaut pour la date cible T au point p si aucun événement dont l'emprise (marge comprise) contient p n'a un intervalle [début ; fin] qui chevauche [min(d, T) ; max(d, T)]. Elle est « incertaine » si p est à moins de `marge_m` du bord d'une telle emprise. Elle est « non valable » si d tombe pendant un événement qui touche p.

- **Avec T = octobre 2026**, on retrouve le comportement actuel : les photos d'avant travaux ne valent qu'hors emprise. La règle « appui de règle » de FUS-DATE-02 devient un cas particulier : l'entité a traversé l'événement sans changer.
- **Avec T = 18/05/2025**, les photos de 2024 et 2025-S1 sont contemporaines. Les ortho et photos de 2022 valent partout, sauf dans le secteur construit en 2023-2024. Le levé GAM ne vaut que hors emprise de TRV-C1-2025 et de TRV-VERCORS-TROTTOIRS.
- **La priorité** devient : la preuve valable **la plus proche de T** décide. Cela généralise FUS-DATE-01, qui dit aujourd'hui « photo_2026 d'abord ».

### 3.3 Branchement sans casser l'état 2026

1. Créer un nouveau module `recon/pcg/etat/etat_cible.py`, avec `recon/pcg/etat/etats/{apres_travaux_2026, avant_travaux_2025}.json`. Il expose `charger()`, `E.dossier(sous)`, `E.reference(cle)`, `E.source(cle)`, `E.v_temporelle`, `E.valide(date, emprise)`, `E.classe_date(...)`, `E.statut_objet(statut_2026)` et `E.age(...)`.
2. **Sélection** : la variable d'environnement `PJ_ETAT`, qui vaut `apres_travaux_2026` par défaut. Les modules calculent leurs chemins **à l'import** (par exemple `commun.SORTIE`, ou `coherence_carte.COHERENCE = SORTIE / "coherence"`), donc un argument `--etat` lu après les imports ne suffit pas. On prévoit un lanceur `python recon/pcg/etat/lancer.py --etat avant_travaux_2025 -- decrire/composer.py …` qui fixe `PJ_ETAT` avant d'importer. Côté Houdini, `hython fabriquer_hda.py --etat …` fixe `$PJ_DESCRIPTION` et `$PJ_SORTIE`.
3. **Garde-fous** :
   - chaque manifeste écrit `etat_cible {id, sha256}` ;
   - le lanceur refuse d'écrire dans un `dossier_sortie` dont le `etat_cible.json` figé a un autre identifiant ;
   - l'absence de `PJ_ETAT` dans un dossier `v2_avant_travaux` est une erreur.
4. **Non-régression** : avec la configuration 2026, `hash_description` et `hash_marquages` du manifeste, `manifest_fabrication_hda.json` et `rapport_regles.json` doivent rester identiques à l'octet, à code égal, avant et après le branchement. C'est le critère d'acceptation du lot 0 (§ 7).

---

## 4. Organisation des sorties : les deux états coexistent

```
recon/out/paquet_jardin/
  package/                          paquet v1 (état 2026) : lecture seule, inchangé
  v2/                               état 2026 : INCHANGÉ (etat_cible apres_travaux_2026)
  v2_avant_travaux/                 état avant travaux (etat_cible avant_travaux_2025)
    etat_cible.json                 copie figée de la configuration utilisée (sha256 cité par chaque manifeste)
    inventaire/                     audits et inventaires (dont ce dossier audit/)
    sources/                        entrées propres à l'état, produites une fois
      opendrive/                    paquet_jardin_avant_travaux.xodr, lanes_avant_travaux.geojson, manoeuvres_avant_travaux.json
      relief/                       dtm_sol_2021_10cm.tif (non versionné), heightmap_avant_10cm.{png,json}, relief_zones_avant.geojson
      v1_reclasse/                  surfaces/marquages indices, objets_presence.geojson, bordures_hauteurs_avant.geojson
      leve_emprise/                 bordures et limites de l'emprise reconstruites (PCRS 2019 + ortho 2022 + LiDAR 2021)
      inventaires/                  panneaux_avant.json, feux_avant.json (assets/specs décrit l'état 2026)
    description/                    même arborescence que v2/description
      base/  regularisation/  coherence/  enrichi/  resolue/{base,objets,planches}  controle_sol/
      description_scene_v2.json
    enrichi/
      recensement/obs_reliees.json  observations re-datées (valide_cible) et ré-appariées ; les brutes restent dans v2
      photos_non_versionnees/       vignettes et planches de photos de tiers (ignoré par git)
    fabrique_hda/                   USD, points, prototypes, manifest_fabrication_hda.json
    controle/                       rapport_regles.json, RAPPORT_REGLES.md, rendu/, cache/
    ue_pilote/                      captures, points et planches UE de l'état
  commun/ (à terme)                 poses Panoramax et Mapillary, triangulations : indépendants de l'état
```

**Ce qui est partagé, en lecture seule, depuis `v2`** (`entrees_partagees`) :
- `v2/enrichi/poses/poses.json` ;
- `v2/enrichi/recensement/mapillary/poses/poses_mapillary.json` ;
- `v2/enrichi/recensement/mapillary/triangulation_mixte.json` ;
- `v2/enrichi/recensement/obs_*.json`.

Les déplacer vers `commun/` serait plus propre, mais cela touche les chemins de l'autre workflow : c'est à faire après sa passe.

**Houdini** :
- même `paquet_jardin_pcg.hip` et mêmes HDA ;
- `$PJ_DESCRIPTION = v2_avant_travaux/description/resolue/base`, ou `…/description/base`. À choisir explicitement : la fabrication 2026 actuelle lit `v2/description/base` et non `resolue/base` (`manifest_fabrication_hda.json`, champ `description`) ;
- `$PJ_SORTIE = v2_avant_travaux/fabrique_hda` ;
- une exécution d'état ne sauvegarde jamais le `.hip`. Seul `--construire-hip` le fait (`fabriquer_hda.py:228`).

**Unreal** :
- niveau `/Game/PJ/Maps/PJ_AvantTravaux_2025` ;
- données propres à l'état sous `/Game/PJ/Etats/AvantTravaux_2025/{Import, PCG/Donnees}`. Aujourd'hui `/Game/PJ/Import/Sol` et `/Game/PJ/PCG/Donnees/PDA_*` sont uniques et entreraient en collision ;
- partagés : `/Game/PJ/{Lib, Materials, Textures}` et les graphes PCG.

---

## 5. Audit par module

### 5.1 `schema/` et validation

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `schema/description_scene_v2.schema.json:5` | description « état octobre 2026 » | Texte générique avec l'état en paramètre | S | faible |
| `…schema.json:13, 23` | `date_etat` requis, `{"const": "2026-10"}` | `{"pattern": "^\\d{4}-\\d{2}$"}` ; version 0.4, compatible | S | faible |
| `…schema.json:122-123` | énumération et motif `src` : gam, pcrs2019, lidar2021, xodr, ortho2022, plan2025, **terrain2026**, … | Ajouter `ortho2024`, `pleiades2025`, `mapillary:<id>`, `photo:<plateforme>:<id>` ; garder `terrain2026` | S | faible |
| `…schema.json:163` | `materiau_id` contient `enrobe_bbsg_neuf_2025` | Garder. L'état avant travaux n'utilise pas ce matériau (âge relatif à T, § 5.3). | — | — |
| `…schema.json:251, 269-270` | `zone_travaux_2025` requis ; `z_ref` ∈ {fil_eau_2021, modele_2026, nivellement_2026} | Garder le champ, avec le sens « dans l'emprise d'un événement postérieur à T » ; ajouter `nivellement_avant_travaux` à `z_ref` | S | faible |
| `…schema.json:300, 314` | `age` ∈ {ancien, recent, neuf_2025, inconnu} ; `niveau.ref` ∈ {mnt_2026, …, nivellement_2026} | Âge relatif à T, avec ajout de `neuf` ; `niveau.ref` étendu | S | faible |
| `…schema.json:425` | `src_marquage` : gam, plan2025, ortho2022, v1, regle | Ajouter `ortho2024`, `pcrs2019`, `photo` | S | faible |
| `decrire/valider.py:11, 25, 309` | Z dans la plage du MNT 2026 ; `SCHEMA` ; dossier par défaut `SORTIE` | MNT et dossier pris dans `E` | S | faible |

Le schéma est partagé avec l'autre workflow. Il faut des ajouts seulement (enum et motifs) et une version mineure 0.4.

### 5.2 `decrire/` : socle (`commun`, `contexte`, `composer`)

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `commun.py:21-28` | `PAQUET`, `DONNEES`, `VECTEURS`, `SORTIE = …/v2/description`, `ZONE`, `SCHEMA` | `SORTIE = E.dossier("description")`. Les autres restent. 19 modules importent `SORTIE` : apercu, coherence_carte, coherence_mesures, composer, detection_evaluation, marquages, marquages_apercu, marquages_bordures, marquages_controles, marquages_couverture, marquages_indices_v1, marquages_ortho, marquages_supports, regulariser_apercu, regulariser_controles, resoudre, resoudre_sources, sol_apercu, valider. | S | faible |
| `commun.py:1, 121-126` | `MNT()` par défaut sur `heightmap_3025_10cm` (sol nu octobre 2026) | `chemin_json = E.reference("mnt")` | S, plus la production du MNT 2021 (L, § 2.4) | moyen |
| `contexte.py:14, 48, 57-59, 92-96, 110, 144, 217, 230, 248, 260` | `surfaces_2026`, `relief_zones_2026`, `dans_chaussee_2026`, `etat_2026/bordure_pct` et `caniveau`, `marquages_2026`, OSM actuel, objets v1 (`statut_2026`) | `E.reference(...)` ; indices v1 filtrés hors emprise ; OSM historique à T (Overpass `[date:"<T>"]`) | M | moyen |
| `composer.py:34-54` | `REFERENCES` : `relief_zones_2026`, `mnt_2026`, `surfaces_v1`, `marquages_v1`, `gam_bordure_pct` | Construites depuis `E.references` | S | faible |
| `composer.py:62-74` | `REGLES_PCG` dont « R-feuilles-automne » | Tirées de `E.saison` (pas de feuilles mortes en mai) | S | faible |
| `composer.py:121-122, 207-209` | `photo_utilisateur` daté « 2026-10 » ; `date_etat: "2026-10"`, saison automne 0,4 / 0,3 | `E.date_etat`, `E.saison` ; ajouter `etat_cible {id, sha256}` au manifeste | S | faible |
| `composer.py:243` | `--sortie` vaut par défaut `SORTIE` | inchangé (suit `E`) | — | — |

### 5.3 `decrire/` : familles de sol (`sol_site`, `sol_composer`, `bordures`, `surfaces`, `ilots`, `sol_lacunes`, `nivellement`, `regulariser`)

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `sol_site.py:61-84` (`gam_lignes`) | Levé GAM 2026 : `etat_2026` en L93, ou le même calque `gam_topo_sol` en WGS84 | Filtrer par admissibilité (`E.sources.gam` : hors emprise TRV-C1 et TRV-VERCORS plus marge). Ajouter la source `pcrs2019` (`gam_limite_voirie_pcrs`, `gam_changement_revetements_pcrs`) et les levés d'emprise reconstruits (`sources/leve_emprise`). | L | **élevé** : géométrie d'avant travaux du cœur |
| `sol_site.py:88-101` | Blocs CHARTIERE du levé 2026 | Hors emprise seulement | S | faible |
| `sol_site.py:113-120, 174` | Indices `surfaces_2026` | Indices hors emprise ; dans l'emprise, indices d'avant travaux (classification ortho 2022/2024) | M | moyen |
| `sol_site.py:183-201` | `zones_relief`, `carte_chaussee_2026`, `dans_chaussee_2026` | `E.reference("relief_zones")` vers un masque de chaussée d'avant travaux | M | moyen |
| `sol_site.py:252-300` | Passages tirés des bandes v1 `marquages_2026` | Passages d'avant travaux (ortho 2022/2024, photos 2024-2025) | M | moyen |
| `sol_site.py:344, 405` | `osm_crossings`, `osm_parking` actuels | OSM historique à T | S | faible |
| `sol_site.py:385-388` | `voies_xodr` sur `lanes_2026` | `E.reference("lanes")` | S, après le `.xodr` d'avant travaux | élevé tant que le `.xodr` manque |
| `sol_composer.py:6, 25-37, 74` | `REFERENCES` GAM 2026, `lanes_2026`, `xodr_2026` ; `niveau.ref = nivellement_2026` | `E` | S | faible |
| `bordures.py:16-17, 134-139` | `bordures_hauteurs` (GAM + PCRS 2019 + plan 2025) | Reclassement par `E.regles_chronologie.bordures_hauteurs` : retirer les 121 tronçons « plan projet » ; remplacer les 496 tronçons « créés ou modifiés » de la zone de travaux ; ajouter les lignes PCRS 2019 de l'emprise (absentes du fichier) | L | élevé |
| `bordures.py:147-153` | `code_source` → gam, pcrs2019, plan2025 | Ajouter les sources d'emprise | S | faible |
| `bordures.py:254-269` | Côté haut par `xodr_2026`, puis `ancienne_chaussee_rehaussee_2025` et `mnt_2026` | `.xodr` d'avant travaux, puis dz du MNT 2021 | M | moyen |
| `bordures.py:558-563` | Masque `travaux` = `creee_apres_2021` OU `modifiee_2025` OU plan projet | **Séparer les trois cas.** `creee_apres_2021` hors zone (1 085 tronçons, 13,1 %) = bordures du quartier est, présentes à T si T ≥ livraison et **neuves** à T. `modifiee_2025` : vue = `h_lidar_2021_m` et non `h_modele_2026_m`. Plan projet : absente. | M | moyen |
| `bordures.py:569, 637` | `dans_chaussee_2026` | Masque d'avant travaux | S | moyen |
| `bordures.py:631, 771` | Source de la vue : `lidar2021` ou `a_priori:relief_hauteur_standard` | Avant travaux : la mesure LiDAR 2021 fait foi dans l'emprise ; moins d'a priori | S | faible |
| `bordures.py:669, 942-959` | `bev_attendue(travaux=…)` : OSM `tactile_paving=no` écarté en zone de travaux, « traversée refaite en 2025 » | Avant travaux : OSM historique à T décide, sans conflit « refaite en 2025 » | S | faible |
| `bordures.py:731-741` | `beton_clair` et `ASPECT_NEUF` si posée après 2021 ; sinon `beton_gris` et `ASPECT_ANCIEN` | Âge relatif à T : neuve si pose dans [T − 2 ans ; T] ; `prov a_priori:usure_par_age` avec T | S | faible |
| `bordures.py:747-760, 794-811` | `z_ref = modele_2026` ; Z = fil d'eau MNT 2026 à 0,30 m ; `prov z a_priori:mnt_2026_fil_eau` | `z_ref = E.schema_description.z_ref`. Z = `z_fil_eau_2021_m` mesuré là où il existe : c'est **mieux** qu'en 2026. | S | faible |
| `bordures.py:1054-1061` | Constats p2025_01_vercors-26 (12/01/2025) et p2025_05_360-32 (18/05/2025), « reconduits » pour 2026 | Pour l'état avant travaux, ce sont des preuves **contemporaines** : confiance haute, `src constat`. La table de constats passe dans un fichier de données par état. | S | faible |
| `surfaces.py:12, 741-765, 880-893, 927` | Marques GAM 2026 comme preuve de revêtement (MQ-DET-010, TQ-SOL-001) | Seulement les marques admissibles à T | S | moyen |
| `surfaces.py:19-20, 259-263, 360` | Vote de classe : masque de chaussée 2026 et voies OpenDRIVE 2026 | `E.references` | S | moyen |
| `surfaces.py:57-76` | Table des matériaux : `modifie_2025` → `enrobe_bbsg_neuf_2025`, `massif_plante modifie_2025` → `brf_bois_concasse` | Table indexée par l'âge relatif à T. Avant travaux, l'emprise est en enrobé ancien et en anciens îlots. | S | moyen |
| `surfaces.py:85` | `AGE = {inchange_2022: ancien, construit_2023_2024: recent, modifie_2025: neuf_2025}` | `E.regles_chronologie.age_surfaces_v1` | S | faible |
| `surfaces.py:89-94` | Constats de surface (`surf_0121`, `surf_0344` arasement) | Table par état. `surf_0344` montre une évolution 2021-2025 hors chantier (§ 2.5). | S | moyen |
| `surfaces.py:897-916, 941` | `modifie_2025` → enrobé neuf ; noue « massif 2025 en creux » ; `niveau.ref nivellement_2026` | Selon l'âge à T ; la noue n'existe pas avant travaux si elle a été créée en 2025 (à vérifier) | S | moyen |
| `ilots.py:28-50` | Table `REMPLISSAGES` : Vercors gravier (12/01/2025, « reconduit ») ; goutte NE `surf_0297` en BRF d'après la photo utilisateur (« terre et herbe avant travaux : coeur-31 ») ; TPC NE en enrobé (18/05/2025) | Table par état. **Avant travaux, la goutte NE est en terre et herbe (observé), et non en BRF a priori.** Gravier et TPC NE deviennent des observations contemporaines. | S | faible |
| `ilots.py:136, 157, 264-266, 443-444` | Z MNT 2026 ; `zone_travaux_2025` ; GQ-TOP-004 (plan 2025) ; matériau `src plan2025` si `modifie_2025` | `E` | S | moyen |
| `sol_lacunes.py:254-270` | `bev_attendue(travaux=zone_travaux_2025)` | `E` | S | faible |
| `nivellement.py:19, 255-307` | MNT injecté (`mnt` en paramètre) | Rien à changer : on passe le MNT d'avant travaux | — | — |
| `nivellement_xodr.py` | élévation et dévers du `.xodr` 2026 (TQ-SOL-004) | `.xodr` d'avant travaux | S | élevé tant que le `.xodr` manque |
| `regulariser.py:55-57, 84-88, 232-236` | Tolérance par source (GQ-TOL-001) ; orientation GQ-ORI-001 sur `lanes_2026` | Tolérances des nouvelles sources (ortho2024 0,25 m ; levés d'emprise 0,10 m) dans une surcharge d'état ; voies d'avant travaux | S | moyen |

### 5.4 `decrire/` : marquages

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `marquages_sources.py:1-24, 35-51` | Ordre FUS-SRC-001 (gam 0,95 > plan2025 0,85 > ortho2022 0,80 > règle > v1) et table `V_TEMPORELLE` | `SOURCES` et `V_TEMPORELLE` lus dans `E` (proposition avant travaux : plan2025 = 0 partout ; ortho2022 = 1 sauf secteur construit ; gam = 1 seulement en zone « conserve » ou « construit » ; ortho2024 = 0,6 partout). **C'est le module le mieux préparé : tout est en tables.** | S | faible |
| `marquages_sources.py:101-144` (`zones()`) | Raster des états de zone tiré du plan CAO 2025, des `surfaces_2026.etat` et des `marquages_2026.zone` | **Réutilisable tel quel** : c'est exactement l'emprise de l'événement TRV-C1-2025 | — | — |
| `marquages_commun.py:23-25` | `V1 = marquages_2026`, `GAM_LIN` et `GAM_PCT = etat_2026` | `E.reference` / `E.source` | S | faible |
| `marquages.py:1-35, 66-73` | Docstring « GAM d'abord » ; `REFERENCES` : `plan_projet_2025`, `relief_zones_2026`, `manoeuvres_2026`, `gam_bordure_lin` | `E` | S | faible |
| `marquages.py:108-120` et `detection_indices.py:55-57` | `rasters_pour(etat)` → (plan2025, ortho2022) | Liste lue dans `E` : ajouter `ortho2024` ; `plan2025` sort de la liste | S | faible |
| `detection_commun.py:29, 37-60` | `PLAN = plan_projet_2025`, lecteur ortho 2022 | Ajouter un lecteur ortho 2024 (20 cm, rééchantillonné à 5 cm) ; détecteurs inchangés | M | moyen (résolution) |
| `marquages_ortho.py:1, 25` | Dalles de l'ortho 2022 | Réutilisable | — | — |
| `marquages_gam_classer.py`, `marquages_gam_entites.py` | Classification du DWG GAM | Réutilisable sur le GAM hors emprise | — | — |
| `marquages_contraintes.py:21` | `BORDURES_GAM = etat_2026/bordure_lin` (dégagement des marques) | Utiliser les bordures **de la description de l'état** et non le levé 2026 | S | moyen |
| `marquages_chronovelo.py:29` | Pavés orange du plan projet 2025 | Avant travaux : à désactiver, ou à détecter sur l'ortho et les photos (LOC-CHR-009 : pavés Chronovélo depuis 2021-2022 sur l'itinéraire) | S | moyen |
| `marquages_inference.py:191` | `manoeuvres_2026` (INF-FLE-004) | `E.reference("manoeuvres")` | S | élevé tant que les manœuvres d'avant travaux manquent |
| `marquages_lignes.py:1125`, `xodr_echantillonne.py:6, 39-40, 406` | `XODR = paquet_jardin_2026.xodr`, `LANES = lanes_2026` | `E` ; l'échantillonneur est réutilisable | S | élevé (`.xodr`) |
| `marquages_indices_v1.py:39-46, 298, 471, 675` | Indices v1 (état 2026) | Indices hors emprise seulement | S | moyen |
| `marquages_verifier.py:19-20, 44-71` ; `marquages_controles.py:11, 88, 183-192, 371, 434-435` | `lanes_2026`, `chaussee_2026`, `etat_2026/bordure_pct`, `surfaces_2026`, `marquages_2026` | `E` | S | faible |

### 5.5 `enrichir/` : poses, recensement, fusion

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `camera.py:40, 44-54, 222` | Sortie des poses `v2/enrichi/poses` ; porteurs par date ; `z_sol` = MNT 2026 | Les poses sont **indépendantes de l'état** : on les réutilise. Le MNT vient de `E` pour les photos d'avant travaux dans l'emprise (écart de 0,15 à 0,20 m sur les zones rehaussées). | S | faible |
| `poses.py:4, 46-51, 855, 1203-1205` | Sélection (360° à moins de 60 m, plus la série du 2025-08-31) ; `G.FIN_TRAVAUX_2025` | Réutilisable ; pas de nouveau calcul de pose | — | — |
| `gcp.py:37-38, 65-72, 131, 147-155, 203-210, 289-303, 366-370, 576, 623, 695` | Validité `valide_de` / `valide_a` par point d'appui, avec bornes codées en dur ; objets « absent 2026 » exclus (`:65-72` : `continue`) | **Le modèle temporel est déjà le bon.** Il suffit de tirer les bornes de `E.evenements`, d'**admettre les objets « absent 2026 »** comme points d'appui avant travaux, et de prendre le Z du MNT de l'état. | S à M | faible |
| `projection.py:7, 21, 195` | Ortho 2022 drapée sur le MNT 2026 | MNT de `E` | S | faible |
| `triangulation.py:149, 206-208, 358-404` | « Placement pour la scène 2026 » ; objets « déduit 2026 / 2026 » prouvés seulement par des photos postérieures | `E.statut_objet` et `E.valide` | S à M | moyen |
| `calage_sequence.py:3-31, 50, 206` | Série du 2026-07-28 et points d'appui nommés du levé GAM 2026 | Sans objet avant travaux. Réutilisable pour d'autres séries avec des points d'appui valides à leur date. | — | — |
| `mapillary.py:68, 732` | Chemins `v2` | `E.dossier` | S | faible |
| `mapillary.py:764, 782, 950` | `valide_de = "2025-12-05"` pour les entités 2025 ; `date < "2025-12-05"` | `E.evenements` | S | faible |
| `mapillary.py:1466-1485` | `validite_2026(eid, date_image)` | Remplacer par `E.valide(date, emprise de l'entité)` ; la logique est la même, généralisée | S | faible |
| `orthos_recentes.py:47-53, 1275-1281, 1292, 1324, 1377` | Dates de travaux ; chemins ; `_validite_auto` (« incertain » à moins de 3 m de la zone de travaux ou à moins de 15 m du Vercors) | `E` ; avec T = 2025-05, l'ortho du 09/08/2024 devient **contemporaine et valable partout**, sauf événement intercalé | S | faible |
| `controle_auto.py:38`, `planche.py` | Ortho 2022 ; planches | Réutilisables | — | — |
| `fusion_recensement.py:47-58` | `DESC`, `BASE`, `COH`, `OUT`, `RECENS`, `POSES_2026` codés sous `v2` | `E.dossier` ; observations brutes et poses via `E.entrees_partagees` | S | faible |
| `fusion_recensement.py:61-79` | `FIN_TRAVAUX` ; `CATEGORIES` (photo_2026 en premier) ; `TRANCHES` (`non_valable_2026`) ; `CLASSES_DATE` ; `TRANCHES_STRICTES` | Classes relatives à T (`E.classe_date`) : contemporaine, antérieure ou postérieure sans changement, séparée par un événement, pendant un événement | M | moyen |
| `fusion_recensement.py:86` | `VERDICTS_RETRAIT = absent_2026, …` | `absent_cible` (alias de compatibilité) | S | faible |
| `fusion_recensement.py:96-140` (`REGLES`) | FUS-VAL-01/02/04 (« validité 2026 »), FUS-DATE-01 (« priorité photo_2026 »), FUS-DATE-02 (classes autour du 05/12/2025), FUS-ZONE-01, FUS-VAL-03, FUS-COUV-01/02, FUS-EXI-01/03/04, FUS-ADD-03, FUS-TMP-01, FUS-SRC-01, FUS-STAT-01 | Réécrire avec T en paramètre (§ 3.2). Le texte des règles est recopié dans les sorties : il faut aussi le paramétrer. | L | élevé |
| `fusion_recensement.py:877, 1564, 1604, 3053, 3275, 3326, 3900` | Lecture et propagation de `o["valide_2026"]` (saisi par l'atelier ou calculé) | Calculer **`valide_cible`** au chargement depuis `date_image`, la position et l'emprise, avec `E.valide`. Garder `valide_2026` brut pour la traçabilité. Les 1 475 observations n'ont pas à être ressaisies. | M | moyen |
| `fusion_recensement.py:1516, 1526, 3477-3490, 3742` | `surfaces_2026` et `relief_zones_2026` comme zone de travaux ; ortho 2022 en fond de carte | Emprise des événements de `E` | S | faible |
| Champ `lien_description` des observations | Identifiants de la description 2026 (K-, S-, MP-, …) | **Ré-appariement** au chargement : l'identifiant s'il existe dans la description d'avant travaux (hors emprise, les identifiants `K-<ligne GAM>` sont stables), sinon l'appariement spatial (FUS-LIEN-04/06 existe déjà). Une observation « absent_de_description » de 2024-2025 devient candidate à l'ajout avant travaux (par exemple un objet retiré par les travaux). | M | élevé (identifiants instables dans l'emprise) |
| `description/enrichi/arbitrages_fusion.json` (données) | Décisions de revue sur la description 2026 | Un fichier par état ; on ne garde que les arbitrages dont l'entité et la position sont inchangées | S | moyen |

### 5.6 `decrire/coherence*` (questions Q1 à Q8)

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `coherence.py:7-29` | Q3 (`absent_2026`), Q4 (présence 2026), z posé sur le sol 2026 | Q3 et Q4 relatifs à T (« présence à T » sur les photos contemporaines : avant travaux, il y en a beaucoup, notamment la série 360 du 2025-05-18) | M | moyen |
| `coherence.py:88-91` | σ de la preuve doublé si elle précède les travaux en zone de travaux | `E.valide` → incertain ×2 | S | faible |
| `coherence.py:105-115, 158, 166-169, 1019-1021` | « obsolete_probable » et `a_verifier_terrain2026` si la preuve est antérieure aux travaux et qu'un marquage 2025 ou une surface `modifie_2025` est sur place | Événement intercalé entre la preuve et T ; drapeau `a_verifier_archive` à la place de « terrain 2026 » (pas de visite possible pour un état passé) | S | moyen |
| `coherence.py:536-564` | Emprise des objets : MNT 2026 surélevé | MNT de `E` | S | faible |
| `coherence.py:859-866` (`emprise_travaux`) | Bordure modifiée à moins de 3 m ou surface `modifie_2025` | `E.evenements` | S | faible |
| `coherence.py:891-930, 944-972, 1058` | Q3 et Q4 « présence 2026 » (objets à moins de 25 m d'une photo postérieure aux travaux) | Photos contemporaines de T | M | moyen |
| `coherence_objets.py:24-27` | `TRIANGULATION`, `ENTITES_VERIFIEES` sous `v2` ; `FIN_TRAVAUX = 2025-08-31`, `FIN_TRAVAUX_REEL = 2025-12-05` | `E` | S | faible |
| `coherence_objets.py:86, 136, 146, 181, 198` | `statut_2026` des objets | `E.statut_objet` | S | moyen |
| `coherence_objets.py:204-224` | `anterieure_travaux()`, `valide_pour_photo()` (Q8 : déplacé pendant les travaux) | `E.valide(date_photo, objet)` | S | faible |
| `coherence_carte.py:29-46, 147-185, 209, 261-285, 301-305, 327, 449-450, 575-603, 737, 789-799` | `COHERENCE = SORTIE / "coherence"` ; `SRC_BASE surfaces_2026` ; `modifiee_2025` ; `lanes_2026` ; `marquages_poses_2025` | `E` ; « marquages posés en 2025 » devient « marquages postérieurs à T » | M | moyen |
| `coherence_photos.py:19-27, 43, 67-68, 83-93, 262` | `apres_travaux()`, et éléments levés « avant travaux » restreints aux bordures non modifiées | La validité d'un élément **à la date de la photo** ne dépend pas de T : `E.valide(date_photo, …)`. Réutilisable presque tel quel. | S | faible |
| `coherence_verifs.py:2-3, 73, 106, 148, 188-196` | Q4 sur les photos postérieures aux travaux | Photos contemporaines de T | S | faible |
| `coherence_mesures.py:13, 32-33, 50-60, 93-96, 401-418, 495` | `deplace_par_travaux` ; `FIN_TRAVAUX_2025` ; `presence_2026` | `E` | M | moyen |
| `coherence_poses.py:4-12, 43-44, 86-101` | `POSES_2026` (2026-07-28) et `POSES_MLY` sous `v2` | `E.entrees_partagees` ; les poses 2026 ne servent pas avant travaux | S | faible |
| `coherence_presence.py:1-20, 66-84` | Sortie `presence_2026.json` | `presence_cible.json` (alias) | S | faible |
| `coherence_politique.py:10, 63-65` | « déduit 2026 », « projet » (plan 2025) | `E.statut_objet` | S | faible |
| `coherence_sorties.py:568-579` | Chemins `v2` codés en dur (bordures, surfaces, marquages, poses, fusion, `poses_2026`, triangulation) | `E` | S | faible |
| `coherence_marquages.py:8, 147, 600-612` | Retrait de la fusion contre le levé GAM 2026 si la date est ≤ 2025-12-05 | `E` (GAM admissible ?) | S | faible |
| `coherence_ombres.py:53` | `TRIANG_MIXTE` sous `v2` | `E.entrees_partagees` ; soleil à la date de la photo, déjà correct | S | faible |
| `coherence_regles.py` (Solveur), `coherence_accord.py` | Lisent `regles_implantation.json` (GEN-07 « réancrage après travaux », SIG-04 sur `lanes_2026`) | Solveur **réutilisable**. Paramètres GEN-07 et SIG-04 par état (surcharge). | S | moyen |

### 5.7 `decrire/resoudre*` (règles RES-*)

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `resoudre.py:9-20, 38, 50, 142, 181, 187, 215, 275` | `SORTIE_RESOLUE = SORTIE / "resolue"` ; `"etat": "2026-10"` ; `fin_travaux` | `E` ; manifeste avec `etat_cible` | S | faible |
| `resoudre_sources.py:18-23, 28-46` | `BASE`, `ENRICHI`, `COHERENCE` dérivés de `SORTIE` (bien) ; `coherence_presence_2026` ; `poses_2026 = SORTIE.parent / "enrichi/recensement/pano_2026/…"` | `E.entrees_partagees` | S | faible |
| `resoudre_regles.py:11-100` | Textes RES-EXI-001 (absence 2026), RES-EXI-002 (garde temporelle 05/12/2025, levé GAM 2026), RES-EXI-003 (photos 2026), RES-POS-006 (« déplacé lors des travaux 2025 »), RES-POS-007, RES-MQ-004 (géométrie 2026), RES-ADD-001 (tranches), RES-NRE-002 (présence 2026) | Textes et seuils paramétrés par T ; RES-EXI-002 devient « événement intercalé » | M | moyen |
| `resoudre_regles.py:101-107` | `RAYON_PRESENCE_2026_M`, `TRANCHES_PROBANTES`, `DEPLACE_TRAVAUX_M`, `FIN_TRAVAUX` | `E` | S | faible |
| `resoudre_regles.py:113-129` (`STATIONS`) | Stations de terrain S1 à S15 (`PROTOCOLE_TERRAIN.md`, visite 2026) | Avant travaux, aucune visite n'est possible : les non-résolus renvoient vers une **archive à consulter** (Panoramax, Mapillary, ortho, OSM historique) et non vers une station de terrain | S | faible |
| `resoudre_objets.py:144-176, 405, 606-608, 691-696` | `absent_2026` ; « absence vue avant la fin des travaux » ; RES-POS-006 ; `tranche_stricte == apres_travaux` | `E.classe_date` | M | moyen |
| `resoudre_marquages.py:123-166, 324, 511-516, 581-582, 625` | Idem pour les marquages (levé GAM 2026, posé ou refait en 2025) | `E` | M | moyen |
| `resoudre_ajouts.py:4, 54-59, 89-144` | `valide_2026 is not True` ; `tranche_stricte` | `valide_cible` | S | faible |
| `resoudre_sol.py:42, 84, 152` | `obs_strictes` | Générique, réutilisable | — | — |
| `resoudre_revue.py` (données, 490 lignes) | Verdicts des revues adverses v1, v2 et v3 sur les décisions 2026, dans du code | Les sortir dans un fichier de données par état. Ne réutiliser que les verdicts de position d'objets inchangés : RES-SRC-002 compare déjà la position relue à 5 cm près. | M | moyen |

### 5.8 `houdini/` (HDA et pilotes)

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `fabriquer_hda.py:44-46` | `HIP` ; `DESCRIPTION = v2/description/base` ; `SORTIE = v2/fabrique_hda` | `E` | S | faible |
| `fabriquer_hda.py:104-106, 120` | `$PJ_DESCRIPTION` et `$PJ_SORTIE` ; `pj::lire_description.dossier = $PJ_DESCRIPTION` | **Déjà paramétré** par variables | — | — |
| `fabriquer_hda.py:550-558, 663, 689-701, 721, 786-791` | `fabriquer()` passe toujours la constante `DESCRIPTION` ; `--sortie` existe, mais il n'y a ni `--description` ni `--etat` | Ajouter `--etat` et `--description` (trois lignes) ; le manifeste écrit l'état | S | faible |
| `pj_commun.py:5, 26-30, 585-624, 632` | `DESCRIPTION`, `FABRIQUE`, `PAQUET_V1` ; classe `Description(dossier=DESCRIPTION)` ; MNT 2026 (ancienne voie numpy) | `E` (la classe prend déjà un `dossier`) | S | faible |
| `pj_contexte.py:3` | Contexte v1 hors du carré de 300 m | Réutilisable (inchangé loin du carrefour) | — | — |
| `hda/pj_lire_description/construire.py:22, 168` | Chemin absolu par défaut du paramètre `dossier` | Garder (surchargé par `$PJ_DESCRIPTION`) | — | — |
| `hda/pj_lire_description/lecteur.py:233-240, 300-311, 434, 457-458, 479-480` | Lecture générique de `dossier/*.geojson`, `nivellement*` et du manifeste parent | **Réutilisable tel quel** | — | — |
| `hda/pj_bordure/construire.py:78, 99, 126, 153-154` | Joints et éclats selon l'âge (attributs `aspect.*` de la description) | **Réutilisable** : l'âge vient de la description | — | — |
| HDA `pj_sol`, `pj_ilot`, `pj_caniveau`, `pj_marquage_{commun,ligne,passage,symbole,zone}` | Aucune logique de date (seulement des dates de revue en commentaire) | **Réutilisables tels quels** | — | — |
| `hda/pj_bordure/controles_f1.py:33-35`, `controle_f1.py:26-27`, `hda/pj_marquage_commun/rendre_marquages.py:35-36`, `verifier_marquages.py:35-37`, `hda/commun/essai_houdini_engine.py:17`, `rendre_integration.py:18`, `hda/ue/piloter_essai_he.py:26` | Chemins `v2` codés en dur (scripts de contrôle et d'essai) | `E` | S (7 × une ligne) | faible |
| `pj_sol.py`, `pj_marquages*.py`, `pj_decals.py`, `pj_ilot.py`, `fabriquer.py` (ancienne voie numpy) | MNT 2026, chemins `v2/fabrique` | Hors chemin critique (remplacée par les HDA). Ne pas porter. | — | — |

### 5.9 `controle/` (vérificateur de règles)

**48 des 128 règles contrôlées dépendent de l'état** :
- 31 du `.xodr`, des voies et des manœuvres ;
- 14 du plan 2025 ou de l'ortho 2022 ;
- 5 du levé GAM 2026 ;
- 5 d'attendus propres au site ;
- 3 de `statut_2026` ;
- 2 de la zone de travaux ;
- 1 du MNT 2026.

Liste par catégorie (une règle peut figurer dans plusieurs) :
- **réseau** : TQ-SOL-014, GA-CHA-001, MQ-LIG-001, MQ-LIG-007, MQ-LIG-008, MQ-LIG-009, MQ-LEF-004, INF-FLE-004, INF-FLE-006, MQ-FLE-008, MQ-FLE-009, MQ-RAB-003, VAL-FLE-001, MQ-CYC-001, MQ-RAB-002, GA-CHA-005, MQ-LAR-002, MQ-LAR-003, GA-RAY-003, GA-RAY-002, MQ-PP-002, GA-ILO-007, MQ-CYC-013, GA-CYC-005, VAL-XOD-008, VAL-COV-006, VAL-JCT-010, DET-FLE-005, DET-FLE-007, DET-LIG-010, FUS-CON-005 ;
- **GAM 2026** : VAL-KRB-005, VAL-FLE-001, VAL-LIG-002, DET-FLE-008, DET-PLN-016 ;
- **attendus de site** : INF-FLE-004, VAL-FLE-001, VAL-COV-006, VAL-JCT-010, FUS-CON-005.

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `ctl_commun.py:25-33` | `V2`, `DESCRIPTION`, `FABRIQUE`, `SORTIE`, `DONNEES`, `SITE` ; `HYTHON` | `E` | S | faible |
| `ctl_commun.py:592, 615-618, 635, 648` | `X.XODR` (2026) ; `lanes_2026` ; `manoeuvres_2026` ; `etat_2026/<nom>_L93` | `E.reference` / `E.source` ; le GAM est filtré hors emprise | S | élevé tant que le `.xodr` manque |
| `verifier_regles.py:41-47` | `--description`, `--fabrique`, `--sortie`, `--regles` existent déjà | Ajouter `--etat` (valeurs par défaut tirées de `E`) | S | faible |
| `ctl_marquages.py:656-660` (INF-FLE-004) et `regles_conception.json` → `parametres.attendu_site` | Attendus R1.v-1 TD_TAG, R1.v-2 TD_TAD, R3.v-1 TD_TAG, R3.v-2 TD_TAD, R6.v2 TAG, R6.v3 TD_TAD, R5 aucune (manœuvres 2026) | Attendus par état dans une **surcharge** `recon/pcg/etat/etats/<id>.regles.json` (sans toucher à `assets/specs`) | M | moyen |
| `ctl_marquages.py:406, 735-755, 829-840, 917-926` | Sources admises gam, ortho2022, plan2025 ; Chronovélo | `E.sources` | S | faible |
| `ctl_sol.py:518` (TQ-SOL-013) | pied − fil d'eau MNT 2026 | MNT de `E` | S | faible |
| `ctl_sol.py:759` | jonction 100 de `lanes_2026` | `E` | S | élevé (`.xodr`) |
| `ctl_sol.py:1076, 1085` | `statut_2026` « absent » | `E.statut_objet` | S | faible |
| `ctl_sol.py:1495-1528` (VAL-KRB-005) | Écart p95 au levé GAM 2026 ; vue LiDAR hors zone de travaux 2025 | Avant travaux : écart au levé **admissible** (GAM hors emprise, PCRS 2019 dans l'emprise, tolérance 0,10 m) ; vue LiDAR 2021 **partout** (plus forte qu'en 2026) | S | moyen |
| `ctl_sol.py:1762-1771` (GA-ARB-005) | Arbres « planté 2025 » | `E.statut_objet` (sans objet avant travaux) | S | faible |
| `ctl_reseau.py:3-4, 53, 107-180, 221, 295` et `661-856` (VAL-XOD-008, décalé de +8 après l'instantané) | `.xodr` 2026, `autorisee_2026`, largeurs des voies | `.xodr` et manœuvres d'avant travaux | M | élevé |
| `ctl_detection.py:30-46, 120, 149-157, 253-260, 276-282, 297-303` | DET-FLE-003/004 (ortho 2022, plan 2025), DET-KRB-015 (zone de travaux), DET-PLN-016 (plan 2025 contre GAM 2026), géoréférencement du plan 2025 | Règles « plan2025 » sans objet avant travaux (marquées « non applicables à l'état ») ; ortho 2024 en plus | S à M | faible |
| `ctl_detection.py:323-336` (FUS-SRC-001) | Table d'admissibilité **codée en dur** (`adm = {conserve: …, neuf_2025: …}`) | Lire `E.v_temporelle_marquages` (même table que `marquages_sources`) | S | faible |
| `ctl_detection.py:473-477, 490-556` (VAL-IMG-007) | Top-hat de l'ortho 2022 ; zones refaites contrôlées sur le plan 2025 | Avant travaux : ortho 2022 partout sauf secteur construit (ortho 2024 là) | S | faible |
| `rapport.py:7`, `rendre_controle.py:6, 34-39`, `extraire_fabrication.py:26-27` | Niveau `PJ_2026` ; chemins `v2` (fabrique_hda, controle, cache, ciel) | `E` (le ciel HDR peut rester partagé) | S | faible |

### 5.10 `ue/`

| fichier:ligne | Câblé | Modification proposée | Effort | Risque |
|---|---|---|---|---|
| `pilote/pilote.py:1, 8-9, 67` ; `pilote/ue/niveau_2026.py:1, 18` | Niveau `/Game/PJ/Maps/PJ_2026` ; entrée `v2/fabrique_ue_snapshot` | `E.ue.niveau` ; script `niveau.py` paramétré (renommage) | S | faible |
| `pj_tools/pj_tools/eclairage.py:28-35` | `SOLEIL` (azimut 220°, élévation 27,6°, mi-octobre), EV100 14 | `E.saison.soleil` (mai : soleil plus haut, à calculer) ; EV100 à revoir | S | faible |
| `contexte/contexte.py:2, 16, 55, 127` ; `clotures.py:22`, `lointain.py:25, 97`, `mobilier.py:26`, `horizon.py:30`, `planches.py:22`, `relief_usd.py:36, 218` | Sorties `v2/ue_pilote` ; « mi-octobre » ; `etat_2026` | `E.dossier("ue_pilote")` | S | faible |
| `contexte/preparer_usd.py:5-11, 50-51, 60-73, 262, 281-284, 382-389, 648` | Couches USD du paquet v1 2026 ; `SOL_2025 = {chaussee: enrobe_bbsg_neuf_2025}` ; classes `_2025` ; `statut_2026` absent | `E` : avant travaux, pas de sol « _2025 » | S à M | moyen |
| `contexte/panoramax.py:27, 35-38, 92-94, 127` | Vues aux poses Panoramax du **18/05/2025 (avant travaux)**, comparées à un rendu 2026 (incohérence reconnue dans le code) | **Réutilisable tel quel pour l'état avant travaux** : c'est la bonne comparaison ; MNT de `E` | S | faible |
| `vegetation/arbres.py:72, 140-143` et `vegetation/correspondance_carla.json` (`saison` mi-octobre ; `ignores.statut_contient = ["absent"]`) | Les 10 arbres « absent 2026 » sont ignorés ; les 15 « planté 2025 » sont posés | `E.statut_objet` : avant travaux, poser les 10 arbres retirés et ignorer les 15 plantés ; variantes de saison | S | faible |
| `contexte/ue/feuilles.py:1, 131`, `contexte/ue/pg_herbe.py:1, 48`, `contexte/ue/materiaux_contexte.py:14`, `pilote/ue/materiaux_maison.py:10, 111`, `correctifs/carla_feuillage_automne.py` | Feuilles mortes et teintes d'octobre | Désactivés ou paramétrés par `E.saison` | S | faible |
| `materiaux/catalogue.py:28, 68, 180, 217` ; `materiaux.py:11, 27` | Sortie `v2/ue_materiaux` ; MI `enrobe_bbsg_neuf_2025` | Bibliothèque de matériaux **partagée entre états** : garder | — | — |
| Chemins de contenu `/Game/PJ/Import/Sol`, `/Game/PJ/PCG/Donnees/PDA_{Bordures, Arbres, Mobilier, Clotures}` | Uniques | `/Game/PJ/Etats/<id>/…` par état (§ 4) | M | moyen (collision dans le projet UE partagé) |

### 5.11 `specs_outils/` et `assets/specs/` (lecture seule ; aucune modification proposée sur place)

| Élément | Constat | Proposition | Effort | Risque |
|---|---|---|---|---|
| `specs_outils/gen_bordures_elements.py:155, 162, 216-217, 291-298` | Répartition des éclats et valeurs par défaut d'aspect sous les clés `neuf_2025` et `ancien` | Réutilisable : ces clés désignent l'âge (neuf ou ancien). Il faut seulement une correspondance âge-à-T → clé dans la description. | — | — |
| `specs_outils/gen_materiaux_sol.py:79`, `ajouter_manifeste.py`, `valider_regles*.py`, `vectoriser_velo.py` | Matériau `enrobe_bbsg_neuf_2025` ; outils génériques | Réutilisables | — | — |
| `assets/specs/regles_conception.json` | **42 règles sur 255** citent 2025, 2026, les travaux, le plan 2025 ou le levé GAM hors des champs de source : MQ-LIG-007, MQ-LEF-001/002/011, MQ-PP-011/014, INF-FLE-004, MQ-FLE-004/005, MQ-RAL-001, MQ-V50-001, MQ-Z30-001, MQ-CHR-001, MQ-CYC-007/013, GA-QBU-002, GA-ILO-005, MQ-STA-001, GA-CHA-003, GA-BOR-002, GA-RAY-001, GA-ASS-001/005, DET-FLE-003/004/006, DET-KRB-014, DET-LIG-010, DET-PLN-016, DET-PRE-002, DET-REG-001, DET-ZEB-009, MQ-DET-009, FUS-CON-005, FUS-SCO-002, FUS-SRC-001, VAL-IMG-007, VAL-KRB-005, VAL-XOD-008, TQ-SOL-013, TQ-OMB-002, TQ-ADAS-001 | Les énoncés normatifs restent valables. Les paramètres d'état (`attendu_site`, `type_priorite` « manoeuvres_2026 », sources « au plan 2025 ») passent dans une surcharge par état, hors `assets/specs`. | M | moyen |
| `assets/specs/regles_locales_meylan.json` | 14 règles sur 46 sont datées : LOC-CTX-002 (âge des ouvrages en octobre 2026), LOC-CTX-003, LOC-CHR-007/008/009, LOC-TRV-002, LOC-TC-004 (arrêt C1 après travaux), LOC-FEU-001/002, LOC-MAT-001/002, LOC-VEG-001/002/003 | Applicabilité par état dans la surcharge | S | faible |
| `assets/specs/regles_implantation.json` | Champ `etat_cible: "octobre 2026, après les travaux 2025"` (déjà la notion d'état cible) ; GEN-04 (MNT 2026), GEN-07 (réancrage après travaux), SIG-04 (`lanes_2026`), VEG-03 (plan 2025) | Surcharge par état | S | faible |
| `assets/specs/regles_qualite_geometrique.json` | GQ-TOL-001 (T par source, sans ortho2024), GQ-ORI-001 (OpenDRIVE 2026), GQ-VAL-003 (planches ortho 2022) | Tolérances des nouvelles sources dans la surcharge | S | faible |
| `assets/specs/panneaux.json`, `feux.json` | **Inventaires de l'état octobre 2026**, et non des normes | Variante d'avant travaux à produire dans `v2_avant_travaux/sources/inventaires/` (Mapillary 2024-2025, Panoramax 2025-05-18) ; les faces PNG sont réutilisables | M | moyen |
| `bordures.json`, `bordures_elements.json`, `marquages_geometrie.json`, `materiaux_sol.json`, `peinture.json`, `materiaux_rendu_v2.json` | Normes et catalogues indépendants de la date (des exemples datés figurent dans les sources) | **Réutilisables tels quels**. Rappel : `bordures`, `vegetation`, `mobilier` et `carla_correspondances` appartiennent à l'autre équipe et ne doivent pas être touchés. | — | — |

### 5.12 Documentation

`ARCHITECTURE.md` est à mettre à jour après la mise en œuvre :
- § 0, « Aucune image ouverte ne montre le carrefour après les travaux » ;
- § 1.3, la liste des `src` ;
- § 1.5, le niveau `PJ_2026` ;
- § 1.6, l'arborescence `v2/`.

`README.md` est aussi à mettre à jour : « MNT sol nu octobre 2026 », manifeste « date 2026-10 », « levé GAM 2026 d'abord ».

Il faut ajouter dans les deux une section « États cibles ».

---

## 6. Réutilisable, à adapter, à réécrire

| Catégorie | Éléments |
|---|---|
| **Réutilisable tel quel** | **HDA** : `pj_bordure`, `pj_caniveau`, `pj_ilot`, `pj_lire_description`, `pj_marquage_commun`, `pj_marquage_ligne`, `pj_marquage_passage`, `pj_marquage_symbole`, `pj_marquage_zone`, `pj_sol`, `commun` (contrat USD et `pj_points`), avec la même scène `.hip`.<br>**Specs normatives** : bordures, bordures_elements, marquages_geometrie, materiaux_sol, peinture, velo_vecteur ; 213 des 255 règles de conception ; règles de qualité géométrique (sauf tolérances).<br>**Algorithmes** : `regulariser_geometrie` (Levenberg-Marquardt, G1), `sol_partition`, `sol_geometrie`, `nivellement` et `nivellement_requete` (MNT injecté), `detection_fleches`, `detection_zebras`, `detection_lignes`, `marquages_gam_classer`, `marquages_gam_entites`, `marquages_fusion` (FUS-ASS, SCO, SNP, CON), `marquages_glyphes`, `marquages_symboles`, solveur `coherence_regles`, `coherence_accord`, `coherence_ombres`, `resoudre_journal`, `resoudre_comparaison`, `resoudre_planches`, `marquages_sources.zones()` (emprise des travaux).<br>**Outils de pose** : `camera`, `poses`, `gcp` (modèle temporel par point), `projection`, `triangulation`, `calage_sequence`, `planche`, `controle_auto`, avec **les poses calculées** (65 Panoramax, 400 Mapillary).<br>**UE** : `pj_tools`, client MCP, graphes PCG, matériaux, bibliothèque de bordures, vues Panoramax du 2025-05-18. |
| **À adapter (paramétrage par `E`)** | Chemins de tous les modules (§ 5) ; `composer`, `valider`, `contexte`, `sol_site`, `sol_composer` ; tables de `marquages_sources` et `detection_indices` ; `xodr_echantillonne` ; `gcp`, `mapillary`, `orthos_recentes`, `triangulation`, `projection` ; `coherence_objets`, `coherence_photos`, `coherence_verifs`, `coherence_poses`, `coherence_presence`, `coherence_politique`, `coherence_sorties`, `coherence_marquages` ; `resoudre`, `resoudre_sources`, `resoudre_ajouts` ; `fabriquer_hda` (`--etat`) ; `ctl_commun`, `verifier_regles`, `ctl_detection` ; UE (niveau, saison, racines de contenu, filtres de statut des arbres) ; schéma 0.4. |
| **À réécrire (logique propre à 2026)** | **Fusion** : dates, validité et couverture stricte dans `fusion_recensement` (FUS-DATE, FUS-VAL, FUS-COUV, FUS-EXI, FUS-ZONE, FUS-STAT), plus le ré-appariement des liens.<br>**Cohérence** : Q3, Q4 et Q8 (`coherence.py`, `coherence_mesures.py`, `coherence_carte.py`).<br>**Résolution** : règles RES-EXI-001/002/003, RES-POS-006/007, RES-NRE-002, stations de terrain.<br>**Description** : tables âge et matériau de `bordures.py:558-563, 731-741`, `surfaces.py:57-94`, `ilots.py:28-50` ; constats « reconduits » à sortir dans des fichiers par état.<br>**Contrôleur** : attendus de site du contrôleur (INF-FLE-004 et suivantes).<br>**Revues** : verdicts de revue (`resoudre_revue.py`) et arbitrages (`arbitrages_fusion.json`) par état. |
| **Données à produire (hors code partagé)** | `.xodr`, voies et manœuvres d'avant travaux ; MNT 2021 en flottant ; masque de chaussée d'avant travaux ; bordures et limites de l'emprise (PCRS 2019, ortho 2022, LiDAR 2021, vérifiés sur l'ortho 2024 et les photos 2024-2025) ; passages ; OSM historique à T ; inventaire des panneaux et feux d'avant travaux ; table d'événements complétée (§ 2.5) ; **date du levé GAM** (qui conditionne son admissibilité). |

---

## 7. Plan de mise en œuvre proposé

Il est à lancer **après** la passe de l'autre workflow sur `decrire`, `houdini`, `controle` et `v2`, en lots courts et sans édition concurrente.

| Lot | Contenu | Effort | Critère d'acceptation | Risque principal |
|---|---|---|---|---|
| 0 Socle | `recon/pcg/etat/etat_cible.py`, deux configurations, lanceur `PJ_ETAT` ; `commun.SORTIE` et `MNT`, `ctl_commun`, `fabriquer_hda --etat`, chemins d'`enrichir`, de la cohérence et de la résolution | M (1 j) | **Configuration 2026 : sorties identiques à l'octet** (manifestes de description, de fabrication et de contrôle) | Oubli d'un chemin codé en dur (liste complète au § 5 et dans `occurrences_cablees.csv`) |
| 1 Données d'avant travaux | MNT 2021 depuis les dalles LiDAR HD IGN ; `.xodr`, voies et manœuvres d'avant travaux ; masque de chaussée ; levé d'emprise reconstruit ; OSM historique ; inventaires de signalisation ; date du levé GAM | L à XL (4 à 8 j) | Planches de superposition sur l'ortho 2022 et l'ortho 2024 ; écart des bordures d'emprise au PCRS 2019 p95 ≤ 0,10 m ; Z au fil d'eau 2021 p95 ≤ 0,03 m | **Le `.xodr` d'avant travaux** (générateur absent) |
| 2 Chronologie | `E.valide`, `E.classe_date`, `E.statut_objet`, `E.age` ; tables `marquages_sources` et `ctl_detection` ; schéma 0.4 ; `valider` | M (1 à 2 j) | Tests unitaires : T = 2026-10 donne les mêmes classes qu'aujourd'hui (sur les 1 475 observations) ; T = 2025-05-18 donne les classes attendues | Constantes héritées (§ 2.2) |
| 3 Description de base | Familles de sol et marquages avec la configuration d'avant travaux → `v2_avant_travaux/description/base` | L (3 à 5 j) | `valider.py` OK ; planches ; couverture de bordures ≥ 98 % des lignes admissibles | Géométrie de l'emprise |
| 4 Enrichissement, cohérence, résolution | `valide_cible` recalculée, ré-appariement, fusion, Q3 et Q4 sur les photos contemporaines (2025-05-18, Mapillary 2024-2025), résolution → `description/resolue` | L à XL (4 à 6 j) | Couverture stricte du cœur > 9,0 % (borne haute estimée à 22,6 % avant nouveau recensement) ; aucune décision fondée sur une photo séparée de T par un événement | Identifiants instables dans l'emprise |
| 5 Fabrication, contrôle, UE | `fabriquer_hda --etat avant_travaux_2025` ; contrôleur avec les attendus de l'état ; niveau UE, saison, racine de contenu | M (1 à 2 j) | Fabrication déterministe ; rapport de règles sans régression sur les règles indépendantes de l'état ; vues aux poses du 2025-05-18 | Collisions d'assets UE |

Total : environ 15 à 25 jours-agent.

**Risques transverses**

| Risque | Parade |
|---|---|
| Écriture concurrente dans `v2` par l'autre workflow | Dossier `v2_avant_travaux` et garde-fou `etat_cible.json` |
| Specs d'une autre équipe | Aucune modification ; surcharges dans `recon/pcg/etat/` |
| Photos de tiers | Vignettes uniquement dans `photos_non_versionnees/` |
| Pas de visite de terrain possible pour un état passé | Les non-résolus renvoient vers des archives (Panoramax, Mapillary, ortho, OSM historique) |

---

## 8. Décisions à demander à l'utilisateur

1. **Date cible précise** dans « 2022 à 2025 environ ».
   - **Défaut proposé : 18/05/2025.**
     - Série Panoramax 360° du jour, 8 poses acceptées.
     - Mapillary 2025-05 : 21 images posées.
     - Ortho IGN 2024 et Pléiades 2025.
     - Quartier est livré.
     - 253 observations en 2025-S1 et 493 en 2024.
   - **Variante : 24/08/2024**, avec l'ortho IGN du 09/08/2024 à 15 jours, 5 poses Panoramax acceptées et 52 images Mapillary.
   - **Déconseillé : 10/05/2022.** L'ortho 5 cm est idéale, mais le secteur est était en chantier (122 surfaces `construit_2023_2024`).
2. **Saison de rendu** : celle de la date cible (printemps, plein feuillage) ou l'automne du simulateur actuel.
3. **Chaîne de fabrication** : fabriquer depuis `description/resolue/base` ou `description/base`. Aujourd'hui, l'état 2026 fabrique depuis `base`.
4. **Harmonisation des dates de travaux pour l'état 2026** (§ 2.2) : à faire, en acceptant que les sorties 2026 changent.
