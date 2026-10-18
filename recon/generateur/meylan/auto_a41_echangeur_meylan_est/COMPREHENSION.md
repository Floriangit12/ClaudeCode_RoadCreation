# Compréhension de la scène — `auto_a41_echangeur_meylan_est` (A41, échangeur 26 Meylan-Est)

*18/10/2026, lot SITES, comparaison v2. Compréhension faite par le modèle en regardant lui-même, en tuiles natives
(≤ 1 092 px), les orthos de plusieurs dates, les vues tirées des photos Panoramax 360° et les rendus du modèle ; aucune
fusion algorithmique. Chemins relatifs à `recon/out/generateur/meylan_auto_a41_echangeur_meylan_est/comparaison/<fenêtre>/`
(photos et planches sous `photos_non_versionnees/`, jamais versionnées ; aucune image ici).*

## 1. Images regardées

| Fenêtre | Emprise (repère du site) | Photos / vues | Dates | Orthos |
|---|---|---|---|---|
| `meylan_auto_a41_echangeur_meylan_est` (f1) | x −207 → 266, y −313 → −32 : pont de l'échangeur, musoir de la sortie 26, branche N87, entrée et sortie de Meylan-Est | 13 / 52 (4 séquences de voiture) | 23/06/2024, 01/06/2025, 14/06/2025, 28/02/2026, 13/09/2026 | IGN 2024, 2021, 2018, 2015, IRC 2024, Pléiades 2025, Plan IGN |
| `…_f2` | x 560 → 1000, y 40 → 330 : fin de la double glissière, convergence 2 + 2 → 4 → 3 | 13 / ≈ 50 | (§ 3.4) | mêmes couches |

Lues : vue générale `orthos/site_ign2024` ; tuiles natives `orthos/tuiles_natives/site_ign2024_t03` (pont, sortie de la
branche) et `t04` (musoirs) ; vue de dessus `dessus/planche_dessus_site_ign_t06`, contours `dessus/contours_site_ign_t06`
et `t09` ; vues et planches citées ci-dessous.

## 2. La scène en une phrase

L'A41 à 3 + 2 voies, séparées par une GBA béton, passe sous le pont à piles de l'échangeur ; au nord, la sortie 26 du
sens Grenoble quitte une voie de décélération par un long musoir à chevrons ; au sud, derrière une double glissière,
la branche venue de la N87 (2 voies) perd d'abord sa voie de droite vers Meylan-Est (boucle vers le sud), puis reçoit
l'entrée de Meylan-Est par une voie d'insertion et un musoir à chevrons ; 900 m plus loin la double glissière cesse et
les deux chaussées se juxtaposent (4 voies) avant que la voie de droite ne disparaisse.

## 3. Ce qu'il y a où

### 3.1 A41 au droit de l'échangeur

- Sens Grenoble (nord) : 3 voies + voie de décélération à droite séparée par des **tirets larges** (déjà ouverte à
  x ≈ 145 : `vue_6714e161_-022`, 23/06/2024), BAU, glissière, rideau d'arbres ; TPC : **GBA béton** (`vue_6714e161_-022`,
  `vue_6ae77446_-030`).
- Sens Chambéry (sud) : 2 voies + BAU, puis **double glissière** (deux rails séparés par une bande d'herbe) et la
  branche N87 : `vue_6ae77446_-030` (13/09/2026, depuis la branche).
- Pont de l'échangeur à x ≈ −115 (tablier sur piles, `site_ign2024_t03`) : non fabriqué (BESOINS ND-2).

### 3.2 Musoir de la sortie 26 (zone de conflit, sens Grenoble)

- Voie de décélération de x ≈ 230 (début) à x ≈ 88 (séparation) ; **chevrons** de x ≈ 88 au **nez** x ≈ 27, la
  bretelle s'écarte alors vers l'ouest-nord-ouest, gazon entre elle et l'A41 : `site_ign2024_t04`,
  `contours_site_ign_t06` (chevrons à x ≈ 30-76 bien visibles).
- Modèle de l'itération 0 : divergence à x ≈ 142 (s = 364) et bretelle posée sur l'axe OSM, qui court sur la
  chaussée de l'A41 de x = 140 à x ≈ 30 avec sa berme et sa glissière (`planche_dessus_site_ign_t06` : bande en
  travers des voies ; `planche_bf1d49e3_-032` : glissière du modèle au milieu des voies du sens Grenoble).

### 3.3 Branche N87 : sortie vers Meylan-Est et entrée de Meylan-Est (zones de conflit, sens Chambéry)

- Sortie de la branche : la voie de droite de la branche (3e voie, parallèle) s'en sépare vers x ≈ −35…−20 et
  plonge en boucle vers le sud (`site_ign2024_t03`, `contours_site_ign_t09` : le tracé OSM du modèle suit bien la
  boucle).
- Entrée de Meylan-Est : la bretelle remonte du sud en courbe et rejoint la branche par une **voie d'insertion** ;
  **musoir à chevrons** de x ≈ 90 à 122 au sud de la branche (`site_ign2024_t04`, `contours_site_ign_t06`). Le modèle de
  l'itération 0 la faisait arriver à x ≈ 144 sur la chaussée de la branche (OSM), sans musoir.

### 3.4 Fin de la double glissière et convergence (f2)

- D'après le relevé du lot B (d7473696, efe0ae74) et l'ortho : vers x ≈ 690 la double glissière s'arrête, les deux
  groupes de 2 voies se juxtaposent (ligne de séparation en tirets courts), cédez-le-passage (AB3a) à droite, puis la
  voie de droite disparaît en biseau. *(vues v2 de la fenêtre f2 : à compléter après sa comparaison.)*

## 4. Contradictions entre dates, résolues

- Photos 2024-2026 et orthos 2015-2024 : même géométrie ; aucune trace de travaux. État décrit : 28/02/2026, valable
  depuis le 23/06/2024 (inchangé).

## 5. Ce qui reste incertain

- Début exact de la voie de décélération (± 20 m) et du musoir de l'entrée (± 5 m).
- Fin de la voie d'insertion de la branche (non relevée, biseau supposé).

## 6. Écarts au modèle et suite donnée

| Élément | Itération 0 | Réalité | Suite (itération 1) |
|---|---|---|---|
| Sortie 26 | divergence à x ≈ 142, bretelle sur la chaussée | séparation x ≈ 88, nez x ≈ 27 | divergence à s = 305,9, zone hachurée à la place de la BAU de s = 240,8 à 305,9, bretelle partant de la voie de décélération ; chevrons de musoir côté ← : BESOINS A41E-1 |
| Entrée de Meylan-Est | arrivée à x ≈ 144 sur la branche, sans musoir | nez x ≈ 109, chevrons | bretelle d'entrée déclarée (`bretelles`, type entrée) : obliquité 0,046, musoir peint de 51 m² à la compilation |
| Sortie de la branche | voie parallèle depuis le nœud | voie parallèle puis séparation x ≈ −30 | inchangée |
