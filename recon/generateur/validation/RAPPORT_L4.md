# Rapport du lot L4 : marquages, trajectoires, conflits et zone de conflit des carrefours plans

*`recon/generateur/validation/RAPPORT_L4.md` — 18/10/2026. Critères : `validation/rapport_L4.json` ; détail mesuré :
`validation/controles_L4.json` (contrôle indépendant `validation/controler_L4.py` : Python, numpy, shapely, véhicules du
lot L3a ; sans Houdini). Documentation de l'API : `hda/rg_marquages_carrefour/README_L4.md` (à reporter au § 10 de
`hda/README_RG.md` par l'agent d'intégration).*

Demande : « le PCG doit reproduire des autoroutes, des ronds-points, plusieurs types de bordures… et **surtout les
carrefours complexes** » (îlots directionnels, zone centrale de conflit, trajectoires de giration matérialisées par des
marquages discontinus). Ce lot fait les étapes 7 à 10 du solveur (plan § 2.4) sur les cinq carrefours J1-J5 du lot
« scenes », dans Houdini, en aval du lot L3 : marquages d'approche, trajectoires voie à voie, conflits, guidage
matérialisé seulement là où il est décrit, zone de conflit, graphe de voies. Route seule : sol neutre, ciel simple.

## 1. Ce qui a été fait

| Élément | Fichier | Rôle |
|---|---|---|
| HDA `rg::marquages_carrefour::1.0` | `hda/rg_marquages_carrefour/` (`construire.py`, `vex_l4.py`, `lecteur_marquages_carrefour.py`) | voies, guidage, trajectoires, conflits, zone, flèches, sas, axe prioritaire, filtre des lignes de section |
| Pilote | `fabriquer_marquages_carrefour.py` | chaîne L1 + L2 + L2b + L3 (fonctions de `fabriquer_carrefours.py` importées sans modification) + L4 ; exports `l4/` ; rendus (J5 : 4 vues ; J1-J4 : 2) |
| Contrôle, plan, rapport | `validation/controler_L4.py`, `validation/dessiner_L4.py`, `validation/faire_rapport_L4.py` | mesures indépendantes ; plan de contrôle `l4/plan_l4.png` |
| Documentation | `hda/rg_marquages_carrefour/README_L4.md` | API (entrées, sorties, exports, commandes, limites) |

Aucun fichier partagé n'est modifié : `fabriquer_generateur.py`, `fabriquer_carrefours.py`, `fabriquer_l2*.py`, les HDA
`rg::*` et `pj::*` existantes, `rendu/*.py`, `description/*`, `README_RG.md` et les specs sont intacts. `pj::symbole_iisr`
n'a pas eu besoin d'une version 2 (voir § 4).

**Réseau.** L'HDA prend le SOLVEUR de `rg::carrefours`, les NIVEAUX, les références et les LIGNES + MARQUES de
`rg::marquages` (fusionnées par le pilote). Elle rend les lignes (section filtrée, guidage, axe prolongé) et les marques
(section filtrée, flèches, figurines) au contrat de `pj::marquage_solide`. Le pilote retire des ponctuels lus par
`rg::marquages` les flèches « fleche » ancrées à un carrefour : le compilateur les avait mal placées (pied à 149,43 m,
pointe 0,43 m **au-delà** de la ligne d'effet de J5 ; constat sur le rendu : flèche doublée), l'HDA les pose au gabarit et
à la règle.

**Principe des trajectoires.** Droite – arc tangent – droite **sur l'axe réel des voies** (la position de l'arc est
itérée quand il commence en amont de l'embouchure ; une voie qui se décale plus loin, comme à l'ouverture d'îlot de J4,
est suivie telle quelle). Rayons : TAD = rayon du coin + écart de l'axe de voie au bord (RF-GV-TRJ-006) ; TAG = plus grand
rayon tenant dans les embouchures ; tout rayon ≥ rayon d'axe minimal du VL (5,467 m, lot L3a, arrondi au cm). Deux TAG
opposés non guidés reçoivent le plus petit rayon commun qui sépare leurs axes (convention des 16 croisements du CU), si
chaque véhicule reste dans sa voie au droit des nez d'îlots. TAG guidé : plus petit rayon qui garde la caisse du VL de
son côté de la ligne de guidage sans toucher la peinture. La limite de jonction de chaque branche (`s_j`) est reculée
jusqu'au plus lointain point de tangence : toutes les trajectoires d'une branche partent du même point de voie
(graphe continu, raccords ≤ 0,04 mm, ≤ 0,4°).

## 2. Les cinq scènes

| Scène | Fabriqué | Mesures clés |
|---|---|---|
| J1 T en cédez | 6 trajectoires ; axe de la rue principale prolongé (1 tiret T'1 réparti entre les derniers tirets) | conflits 3 croisements / 9 (combinatoire du T) |
| J2 croix en STOP (RD) | 12 trajectoires ; axe T1 de la RD prolongé (1 tiret de 3 m, intervalles 7,5 m) ; rives T2 de la RD interrompues au droit de la VC (16 morceaux retirés, du point de tangence du coin à l'embouchure) | 16 croisements / 32 (= CU) |
| J3 croix à feux | 12 trajectoires ; aucune ligne dans le carrefour (tirets d'axe entre passage et frontière retirés) | 16 / 32 (= CU) ; zone 235 m² |
| J4 îlots | 12 trajectoires dont le TAD par la voie directe (R 26,5 m, axe concentrique au coin R 25) ; TAG opposés de la rue à R 6,77 m (séparés) ; axe de l'avenue prolongé (2 tirets) | 16 / 32 |
| **J5 carrefour complexe** | 16 trajectoires (14 + 2 vélos) ; 12 flèches (2 par voie : voie de stockage de 43 m) ; 4 figurines de sas ; ligne de guidage T'2 0,10 des TAG à l'indonésienne (11 traits) ; zone de conflit 1 188 m² ; 40 morceaux de lignes retirés ou coupés à la ligne d'effet | 25 croisements / 39 points ; TAG guidés R 9,13 m sans croisement |

Rendus (Karma XPU ; planches ≤ 1092 px regardées en entier, vues de plus de 1092 px en tuiles natives) :
`recon/out/generateur/J*/rendus/planche_J*.png` ; J5 : dessus, oblique 3/4, conducteur dans la voie de TAG de l'artère
ouest et dans la voie entrante de la rue sud. Plans de contrôle : `recon/out/generateur/J*/l4/plan_l4.png`.

## 3. Critères mesurés

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| L4-1 flèches d'affectation : sommets = gabarit du dossier 08 | écart max 0,003 mm (12 flèches) | ± 1 mm | oui |
| L4-2 flèches centrées dans la voie (axe L1 des voies) | 0,00 cm | ± 2 cm | oui |
| L4-3 flèches orientées le long de la voie | 0,000° | ± 0,5° | oui |
| L4-4 pointe de la dernière flèche à la ligne (bord amont de la peinture) | 1,501 à 1,501 m (6 voies) | 1,50 ± 0,02 m | oui |
| L4-5 interdistance des flèches (pointe à pointe) | 20,000 à 20,000 m (6) | 20 ± 0,05 m | oui |
| L4-6 nombre de flèches : 3 par voie, 2 si la voie (formée et droite) est courte | B-est/tag1 2/3, B-est/v3 2/3, B-est/v4 2/3, B-ouest/tag1 2/3, B-ouest/v3 2/3, B-ouest/v4 2/3 | posées = min(demandées, tenant dans la voie) ≥ 2 | oui |
| L4-7 sas vélos : figurine dans l'axe de chaque voie, centrée entre les lignes ; profondeur | 4 figurines ; axe ≤ 0,000 m ; centrage ≤ 0,000 m ; profondeur 3,852 m | ± 2 cm ; 3 à 5 m (bord à bord) | oui |
| L4-8 trajectoires de rayon ≥ rayon d'axe minimal du véhicule de projet (VL, lot L3a) | rayon mesuré min 5,506 m ; 56/56 trajectoires | ≥ 5,467 m (100 %) | oui |
| L4-9 trajectoires droite – arc – droite tangentes aux voies (bouts sur l'axe L1, tangence) ; rupture des polylignes | bouts 0,0 mm, 0,398° ; rupture max 0,798° | ≤ 1 cm, ≤ 0,5° ; ≤ 0,8° (pas angulaire des arcs) | oui |
| L4-10 guidage seulement là où il est décrit (ARB-08) | J1 0 ligne(s) / 0 trajectoire(s) décrite(s), J2 0 ligne(s) / 0 trajectoire(s) décrite(s), J3 0 ligne(s) / 0 trajectoire(s) décrite(s), J4 0 ligne(s) / 0 trajectoire(s) décrite(s), J5 1 ligne(s) / 2 trajectoire(s) décrite(s) | J5 : 1 ligne pour 2 TAG décrits ; J1-J4 : 0 | oui |
| L4-11 ligne de guidage T'2 0,10 : traits, intervalles (le long de la courbe), largeur | 11 traits 0,5000-0,5000 m ; intervalles 0,5000-0,5000 m ; largeur 0,1000-0,1000 m | 0,50 ± 0,01 ; 0,50 ± 0,01 ; 0,10 ± 0,002 m | oui |
| L4-12 TAG à l'indonésienne (phase spéciale P2) : axes sans croisement ; caisse du VL (1,80 m) de son côté de la ligne | croisements 0 ; garde 0,054 m | 0 ; ≥ 0 m | oui |
| L4-13 balayages du VL (lot L3a, rétroviseurs 2,10 m) des deux TAG guidés : disjoints et hors bordures | recouvrement 2,27 m² ; contre le nez du TPC 0,63, 0,63 m | 0 m² ; 0 m | **non** |
| L4-14 zone de conflit : aucune ligne longitudinale dedans hors guidage (et hors discontinue de la route prioritaire, RF-MQ-CAR-01) | 0 ligne(s) ; 56 morceaux retirés, 8 coupés à la ligne d'arrêt | 0 | oui |
| L4-15 points de conflit comptés et rapportés avec la liste des mouvements ; croix complète J2, J3 = CU (16 croisements, 32 conflits) | croisements/total : J1 3/9, J2 16/32, J3 16/32, J4 16/32, J5 25/39 | J2, J3 : 16 / 32 | oui |
| L4-16 conflits : géométrie (intersections des axes) = topologie (ordre des bouts autour du centre) | 1 écart(s) : T-nord.v2.TAG / T-sud.v2.TAG : géométrie croisement, topologie - | 0 écart | **non** |
| L4-17 graphe de voies : chaque voie entrante a ≥ 1 successeur ; ≤ 32 étiquettes ; raccords | 25 voies entrantes, 0 sans successeur ; étiquettes ≤ 6 ; raccords ≤ 0,04 mm, 0,398° | 0 ; ≤ 32 ; ≤ 1 mm, ≤ 0,5° | oui |
| L4-18 peinture du lot posée sur le sol fabriqué : dessus − sol = 2 mm (lignes) / 3 mm (marques) | écart max 0,230 mm (sommets et centres des faces du dessus) | ± 0,3 mm | oui |
| L4-19 discontinue axiale de la route prioritaire non interrompue au droit de l'intersection ; rives interrompues au droit des affluentes | J1 : 1 tiret(s); J2 : 1 tiret(s); J4 : 2 tiret(s) ; rives restantes 0 | ≥ 1 tiret par carrefour à route prioritaire ; 0 rive | oui |
| L4-20 planches de rendu regardées en entier (≤ 1092 px), vues en tuiles natives (J5 : 4 vues ; J1-J4 : 2) | 5/5 | 5/5 | oui |
| L4-21 déterminisme (deux processus, une fois en fin de lot, 2 scènes) | identique (76 fichiers : J1 et J5, lots L1, L2, L2b, L3, L4) | identique | oui |

19/21 critères atteints (L4-13 et L4-16 non atteints : § 4).

## 4. Problèmes restants et écarts (honnêtement)

- **L4-13, balayages des TAG à l'indonésienne de J5 (non atteint).** Les axes ne se croisent pas et la caisse (1,80 m)
  reste de son côté de la ligne (garde 5 cm), mais les balayages du VL du lot L3a (2,10 m rétroviseurs compris, porte-à-faux
  avant 1,01 m) des deux TAG opposés se recouvrent de 2,27 m² au centre, et chacun touche le nez du TPC (0,63 m de
  contact). Essai sur le rayon (balayage L3a) : à R ≥ 10 m les balayages se séparent mais le contact avec le nez du TPC
  passe à 0,93 m ; à R 9 m la caisse seule touche à peine (5 mm) mais les balayages se recouvrent de 2,8 m². La géométrie
  décrite ne permet pas les deux à la fois : le cœur ne fait que 9 m dans l'axe de l'artère (rue de 8 m) et les nez du TPC
  sont à la frontière (lot L3 : recul plafonné par les refuges). À trancher dans la description (lot scenes) : rue plus
  large, voies de TAG plus décalées, ou nez du TPC reculés avec refuge déplacé.
- **L4-16, TAG opposés de la rue de J5 (écart géométrie / topologie).** En phase P3, les TAG nord et sud de la rue se
  croisent (axes) : avec les îlots de 2 m de la rue, aucun rayon ne les sépare sans qu'un des deux véhicules sorte de sa
  voie au droit du nez du TPC de l'artère (R ≈ 15 m nécessaire). Le croisement est compté (25 au lieu des 24 de la
  combinatoire) et signalé par l'HDA (`rg_l4_avertissements`). Même cas résolu sur J4 (R 6,77 m).
- **Flèches : 2 par voie sur J5 au lieu de 3.** La voie de stockage de TAG n'atteint sa largeur qu'à 43 m de la ligne
  d'effet, et les voies directes sont dans le déport et le S de l'artère au-delà : la 3e flèche serait sur un biseau ou
  inclinée de 3,4° (mesuré au premier essai). ARB-11 admet 2 flèches pour une voie courte ; le compilateur en plaçait 3.
- **Lignes du compilateur (lot scenes) non utilisées.** Ligne de guidage du modèle (polyligne à angles vifs) et trajectoires
  du modèle (TAG à 4,47 m de rayon, TAG guidés à 45°) : l'HDA reconstruit les deux depuis les voies réelles. Figurines
  `figurine_velo` et polygone `sas_velo` du modèle : non peints par `rg::marquages` ; l'HDA pose les figurines depuis la
  consigne de sas.
- **Choix [G] déclarés** : rayon des raccords de la ligne de guidage (le plus grand tenant entre l'embouchure et l'oblique,
  3,62 m sur J5 ; l'IISR ne cote pas les rayons) ; phase des traits (motif centré) ; répartition des tirets de l'axe
  prolongé entre les derniers tirets des deux branches (intervalles de 6,25 m sur J1, 7,5 m sur J2 et 4,0 m sur J4 au
  lieu de 5, 10 et 5 m : les motifs des deux branches ne se raccordent pas exactement) ; flèches seulement sur une voie formée (≥ 99 %)
  et droite (≤ 0,5°) ; mouvements cyclables en tout droit d'une bande à la bande alignée (aucun n'est décrit) ; zone de
  conflit = cœur + bandes d'approche jusqu'au bord amont de la ligne d'arrêt / d'effet (ou du passage si la ligne est
  virtuelle).
- **Critères du plan hors de ce lot ou sans objet** : modulations sur 100 m, hachures, nombre de bandes de passage (section
  courante : lot L2b, inchangé) ; damier TC (aucune ligne TC décrite) ; × 4/3 (carrefours plans en agglomération) ;
  **symboles v2 (`pj::symbole_iisr::2.0`) : non faits** — les flèches et figurines sont peintes par empreintes exactes
  (gabarit du dossier 08, ± 0,003 mm) ; les instances pour Unreal restent à faire.
- **Plis des axes de voie** (biseaux des lois de largeur du profil, jusqu'à 2,9° sur J4) : ils appartiennent au profil
  (lot L1) ; le contrôle les rapporte à part de la rupture des trajectoires.
- Deux autres processus hython ont tourné en même temps que ce lot (autres agents) ; les sorties finales viennent de
  passes séquentielles de ce lot.

## 5. Interface pour les autres lots

`hda/rg_marquages_carrefour/README_L4.md` : sorties de l'HDA (DONNÉES : voies, trajectoires, conflits, zone, guidage,
table des marques), exports `l4/` (dont `graphe_voies.json`, format `rg_graphe_voies/0.1`), commandes. **À intégrer**
(agent d'intégration) : option `--marquages-carrefour` de `fabriquer_generateur.py` reprenant `reseau()` et
`fabriquer()` de `fabriquer_marquages_carrefour.py` ; § 10 de `README_RG.md` depuis `README_L4.md`. Le lot L6
(signalisation) peut lire `l4/trajectoires.json` (voies, phases) et `l4/zone_conflit.json` ; le lot L7 (OpenDRIVE) les
connecteurs de `l4/graphe_voies.json` (limites de jonction `s_j`).
