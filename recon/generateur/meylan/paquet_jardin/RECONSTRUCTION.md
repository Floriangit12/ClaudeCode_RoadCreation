# Carrefour Paquet Jardin (M01) — reconstruction, étape 3

*`recon/generateur/meylan/paquet_jardin/RECONSTRUCTION.md` — 18/10/2026, lot « carrefours ». État décrit : **avant les
travaux de 2025, au 18/05/2025** (décision prise avec l'utilisateur). Aucune photo ni planche n'est versionnée.*

## 0. Passe v2 — le centre (18/10/2026, soir)

Remarque de l'utilisateur : « avec 6-10 photos tu ne peux pas comprendre toute la scène, et surtout le centre avec la
zone de conflit » ; le rendu de l'itération 1 avait un **centre vide et trop simple** et des passages décalés de 2 à 6 m.

**Résultat** : ressemblance du centre **moyenne à bonne en plan** (itération 1 : faible) — chaque branche a son îlot au
droit du passage, l'îlot central du Vercors et le grand îlot de l'angle sud existent, la bretelle contourne le cœur,
les passages tombent sur les zébras réels à ≈ 1 m (contours du modèle sur le PCRS 5 cm :
`recon/out/generateur/meylan_paquet_jardin/comparaison/meylan_paquet_jardin/dessus/contours_centre_pcrs2022.png`).
Ce qui reste faux au centre relève du générateur (`BESOINS.md` PJ-1 à PJ-8) : ligne mixte et flèches du cœur,
traversées cyclables jaunes et vertes, forme des îlots (triangle du Vercors, îlot rond de la Chronovélo, angles plantés).

| Étape | Ce qui a été fait | Fichiers |
|---|---|---|
| Dossier v2 | préparé par l'auteur de l'outil sur le modèle de l'itération 1 (60 photos dont 30 dans la fenêtre d'état 24/08/2024-22/06/2025, 123 vues, 54 du centre, 9 photos dans le cœur, 7 couches d'ortho datées) ; relu tel quel | `…/comparaison/meylan_paquet_jardin/comprehension/LISEZMOI.md` |
| Fusion dans le modèle | lu en tuiles natives : 7 orthos (zoom du centre, planches de dates, 9 tuiles PCRS du site), 13 planches du centre (52 vues), 13 vues natives ; 12 lectures à grille de 1 m posées sur le PCRS 5 cm et l'IGN 2024 | `COMPREHENSION.md` ; `…/_travail/v2/lecture/` (sans photo) |
| Description | itération 2 : centre sur la médiane réelle, axes réels des branches, passages par retrait, îlots de chaque branche, îlot central du Vercors, bretelle en îlot directionnel, angles ; contrôlée avant fabrication par superposition du modèle compilé sur le PCRS (3 essais : `modele_iter2a/b/c`) | `description.yaml`, `DESCRIPTION.md` § 1 et § 7 |
| Fabrication | `hython …/_travail/fabriquer_lot_a.py description.yaml --complet --angle-sol 0` : 0 erreur, 0 non-conformité non admise ; L2 511 354 faces de sol, 73 950 de bordures ; L3 4 coins, 4 nez ; L4 14 trajectoires, 45 conflits ; premier essai planté dans `rg::sol` (PJ-8), d'où `--angle-sol 0` | `…/_travail/v2/fab_iter2.log`, `fab_iter2b.log` |
| Rendus seuls | vue de dessus (110 m) et oblique 3/4 | `recon/out/generateur/meylan_paquet_jardin/rendus/dessus.png`, `oblique_carrefour.png`, `planche_meylan_paquet_jardin.png` |
| Recomparaison v2 | `comparer_multivues.py meylan_paquet_jardin --v2 … --depuis 2024-08-24 --jusqu-au 2025-06-22 --etapes pose,rendu,dessus,planches,dossier` (34 min, GPU partagé) : 123 vues rendues, poses affinées 88 / 123 ; recouvrement des contours à 3 px médian 0,12 → 0,33, écart moyen médian 17,3 → 11,4 px | `…/_travail/v2/comp_v2_iter2.log`, `rapport.json`, `ecarts.json` → `centre_zone_conflit` (rempli) |

Regardé moi-même après fabrication : rendu de dessus du centre, contours du modèle sur le PCRS 2022, oblique 3/4,
planches photo | rendu 119d9094_-045 (vers le sud : îlot de Verdun SO et triangle du Vercors de part et d'autre, comme
la photo ; ligne mixte absente), 31d16b8e_-113 (angle sud : îlot présent, mais d'un seul tenant au lieu de deux îlots
séparés par les rectangles jaunes), 119d9094_+114 (Revirée : îlot et demi-passages présents, bandes vertes absentes,
îlot effilé du mauvais côté).

| Élément du centre | Itération 1 | Itération 2 |
|---|---|---|
| îlots des branches | 4 refuges rectangulaires décalés de 2 à 5 m | sur les îlots réels à ≈ 0,5-1 m (Verdun NE, Revirée, Verdun SO, Vercors) |
| angle sud, bretelle | bretelle entrant dans le cœur | voie directe derrière un îlot d'angle (forme imposée, PJ-5) |
| passages | décalés de 2 à 6 m | sur les zébras réels (≤ 1 m) ; demi-passages décalés rendus d'un seul tenant |
| ligne mixte, flèches du cœur | absentes | absentes (hors format, PJ-3) |
| traversées cyclables jaunes / vertes | absentes | absentes (hors format, PJ-1, PJ-2) |
| angles plantés ouest et est | trottoir | trottoir (PJ-7) |

Pas d'itération 3 : les écarts restants du centre ne sont plus des écarts de description.

## 1. Résultat en bref

- **Fabriqué et rendu** (rendu seul, sans photo) : `recon/out/generateur/meylan_paquet_jardin/rendus/dessus.png`
  (vue de dessus, 61,6 m de côté), `oblique_carrefour.png` (oblique 3/4), planche `planche_meylan_paquet_jardin.png`.
- **Ressemblance** : **bonne sur le cœur et sur les approches nord-est et sud-ouest**, moyenne sur le côté nord-ouest
  de Verdun sud-ouest. Itération 1 : 4 photos « bonne », 2 « moyenne », 1 inexploitable sur 7 ; grille 27 conformes,
  13 différents, 9 non visibles (itération 0 : 3 / 3 / 1 ; 25 / 15 / 9).
- **Écarts restants** : surtout des manques du générateur (traversée Chronovélo en pavés jaunes et bandes vertes,
  fissures pontées de l'enrobé, bretelle de tourne-à-droite longue), voir `BESOINS.md`.
- **Contournement déclaré** : la fabrication plantait (Triangulate 2D du cœur, besoin G2) ; les rendus ont été faits
  avec `angle_min = 0` sur l'instance `rg::carrefours_sol` (enveloppe non versionnée
  `recon/out/generateur/meylan_paquet_jardin/_travail/fabriquer_lot_a.py`), sans modifier le code partagé.

## 2. Ce qui a été fait

| Étape | Commande / fichier | Résultat |
|---|---|---|
| Relecture | `DESCRIPTION.md`, `description.yaml` ; tuiles natives 119d9094 (l+0, l+102.9), 20d1a815 (t006), plan annoté | description cohérente avec l'état avant travaux |
| Fabrication | `hython …/_travail/fabriquer_lot_a.py recon/generateur/meylan/paquet_jardin/description.yaml --complet` (résolveur réseau → compilateur → HDA) | 0 erreur, 0 non-conformité ; itération 1 : L2 537 571 faces de sol, 67 383 de bordures ; L3 4 coins, 4 nez ; L4 14 trajectoires, 44 conflits |
| Comparaison | `python …/_travail/comparer_lot_a.py --sortie recon/out/generateur/meylan_paquet_jardin/comparaison --sites-conf recon/generateur/meylan/paquet_jardin/comparaison_site.json meylan_paquet_jardin --depuis 2024-08-24 --jusqu-au 2025-06-22` | 7 photos (24/08/2024, 12/01/2025, 18/05/2025), 4 quadrants, positions chaussée / hors modèle ; 50 photos postérieures au 22/06/2025 (chantier) retirées |
| Grille | `comparaison/meylan_paquet_jardin/ecarts.json` (+ `ecarts_iter0.json`, `ecarts_iter1.json`) remplie d'après les 7 planches et la synthèse regardées en entier (≤ 1 092 px) | voir § 4 |

L'enveloppe de comparaison (`comparer_lot_a.py`) ne change que la racine des sorties (dossier du site), le repli de la
recherche Panoramax sur les instances IGN et OSM-FR (méta-catalogue en erreur 500 le 18/10/2026) et la date maximale ;
les seuils de l'outil sont inchangés.

## 3. Itérations

| Itération | Changement de la description | Preuve | Effet |
|---|---|---|---|
| 0 | description du lot réseau (N1), état avant travaux | — | séparation bretelle / Verdun sud-ouest rendue comme un terre-plein bordé en galets sur ≈ 85 m (0fe2656f, 034cb578 : « différent ») |
| 1 | `terre-plein ≈ 1,7 galets` → `zone hachurée ≈ 1,7` entre Verdun sud-ouest et la bretelle (et dans l'évènement de fermeture) | photos 0fe2656f (24/08/2024) et 034cb578 (18/05/2025) : lignes continues, pas d'îlot ; l'îlot en galets IA-2 du cœur ne fait que ≈ 22 m² (inventaire avant travaux) | 0fe2656f et 034cb578 passent de « moyenne » à « bonne » ; refuge du passage sud-ouest gardé au droit du passage |

Pas d'itération 2 : les écarts restants ne relèvent plus de la description (§ 5).

## 4. Ressemblance par photo (itération 1)

| Photo | Date | Vue | Pose | Ressemblance | Constat principal |
|---|---|---|---|---|---|
| 119d9094 | 18/05/2025 | depuis le centre vers Verdun nord-est | orientation, 13,8 px | bonne | 2 + 2 voies, îlot au passage, bandes de 3 m ; traversée Chronovélo (pavés jaunes) absente |
| 9834f494 | 18/05/2025 | Verdun nord-est, vers le carrefour | redressement, 12,2 px | moyenne | voies et flèches justes ; zone hachurée plus présente que sur la photo près du passage |
| e86aa913 | 24/08/2024 | Verdun nord-est, vers le carrefour | métadonnées, 13,6 px | bonne | îlot avec B21, flèches, bordure basse et herbe à droite |
| aa9d7e12 | 24/08/2024 | Verdun sud-ouest, vers le nord-ouest | orientation, 9,7 px | moyenne | côté nord-ouest simplifié (bandes dans un autre ordre près du carrefour), traversée Chronovélo absente |
| 0fe2656f | 24/08/2024 | Verdun sud-ouest, vers la bretelle | orientation, 6,5 px | bonne | séparation peinte de la bretelle (itération 1) |
| 034cb578 | 18/05/2025 | Verdun sud-ouest à ≈ 90 m | métadonnées, 8,9 px | bonne | géométrie juste ; « 50 » au sol absent |
| 29fb102d | 12/01/2025 | Vercors | rejetée (360° au casque inclinée de 14,8°) | inexploitable | rendu pris de trop haut |

Mesures de l'outil (médianes avant → après affinage) : recouvrement des contours à 3 px 0,23 → 0,31, écart moyen
13,6 → 12,2 px.

## 5. Écarts restants

- Traversée de la Chronovélo sur Verdun sud-ouest (pavés jaunes, bande verte) et bandes vertes de la Revirée : pas de
  mot dans le format (besoin A2 / G4).
- Enrobé ancien très fissuré avec pontages : rendu uniforme (G8).
- Bretelle de tourne-à-droite SE : décrite comme voie de droite de Verdun sud-ouest jusqu'au carrefour ; en réalité elle
  contourne le cœur et rejoint directement le Vercors avec ses passages à feux (P1).
- Côté nord-ouest de Verdun sud-ouest près du carrefour (contre-allée, bande fleurie, Chronovélo) : ordre des bandes
  simplifié (aa9d7e12) ; inscription « 50 » non décrite (événement `inscription` possible, non fait faute de position
  sûre).
- Branche du Vercors : aucune planche exploitable (29fb102d inexploitable) ; non jugée.

## 6. Fichiers

- Versionnés : `description.yaml` (itération 1), `DESCRIPTION.md`, `BESOINS.md`, ce rapport.
- Non versionnés : `recon/out/generateur/meylan_paquet_jardin/` (modèle, L1-L4, rendus) ;
  `…/comparaison/meylan_paquet_jardin/` (`selection.json`, `poses.json`, `ecarts*.json`, `plan_site.png`, rendus de
  comparaison ; planches dans `photos_non_versionnees/`, itérations archivées dans `photos_non_versionnees/iter0|iter1`) ;
  `…/_travail/` (enveloppes, journaux, jugements, description de l'itération 0).
