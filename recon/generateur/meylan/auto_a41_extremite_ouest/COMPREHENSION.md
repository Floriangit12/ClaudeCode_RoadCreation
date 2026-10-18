# Compréhension de la scène — `auto_a41_extremite_ouest` (A41, bout ouest, entrée et sortie 27 Mi-Plaine)

*18/10/2026, lot SITES (autoroute et axes), comparaison v2. Cette compréhension est faite par le modèle qui regarde
lui-même les images, en tuiles natives (≤ 1 092 px) : orthos de plusieurs dates, vues tirées des photos Panoramax
(360°, plusieurs directions par photo), rendus du modèle fabriqué. Aucune fusion algorithmique. Aucune image dans ce
fichier : les chemins sont relatifs à `recon/out/generateur/meylan_auto_a41_extremite_ouest/comparaison/<fenêtre>/`
(orthos et dessus diffusables ; photos et planches sous `photos_non_versionnees/`, jamais versionnées).*

## 1. Images regardées

| Fenêtre | Emprise (repère du site) | Photos / vues | Dates des photos | Orthos |
|---|---|---|---|---|
| `meylan_auto_a41_extremite_ouest` (f1) | x −13 → 427, y −21 → 145 : bout de l'autoroute, butte du départ, réduction 3 → 2, entrée de Mi-Plaine | 13 / 52 (Panoramax, 4 séquences de voiture, les deux sens) | 01/06/2025, 14/06/2025, 28/02/2026, 28/07/2026 | IGN 2024 (09/08/2024), 2021 (13/08/2021), 2018, 2015, IRC 2024, Pléiades 2025, Plan IGN |
| `meylan_auto_a41_extremite_ouest_f2` | x 440 → 800, y 120 → 260 : sortie 27 (voie de décélération, musoir) | 13 / 52 | 01/06/2025, 14/06/2025, 28/02/2026 | mêmes couches |

Lues en tuiles natives : `orthos/tuiles_natives/site_ign2024_t00` à `t02` (f1), `t00` et `t01` (f2) ; `site_ign2021_t01` ;
planches de dates `orthos/planche_dates_site_p01`, `p02` ; `orthos/contexte_planign` ; vue de dessus
`dessus/planche_dessus_site_ign_t02`, `t04` et `dessus/contours_site_ign_t00`, `t04` ; vues natives
`photos_non_versionnees/v2/vues/vue_<clé>.png` et planches `photos_non_versionnees/v2/planches/planche_<clé>.png`
citées ci-dessous.

## 2. La scène en une phrase

L'A41 naît (ou finit) sur le carrefour à feux de l'avenue de Verdun : les deux chaussées s'écartent autour d'une butte
enherbée plantée de candélabres, puis se rapprochent derrière un terre-plein d'herbe sèche à une seule glissière (côté
sens Chambéry) ; vers Chambéry trois voies se réduisent à deux au bout d'une centaine de mètres ; vers Grenoble, la
bretelle du giratoire de Mi-Plaine plonge en courbe serrée et devient la troisième voie au droit d'un petit musoir à
chevrons, et 500 m plus à l'est la sortie 27 se détache par une voie de décélération et un long musoir à chevrons.

## 3. Ce qu'il y a où

### 3.1 Butte du départ (x ≈ 0-50)

- **Terre-plein central en butte** d'environ 15 m au départ (≈ 18 m entre bords de chaussée à x ≈ 0, ≈ 10 m à x ≈ 40),
  enherbé, **sans glissière**, bordé d'une **bordure** béton côté sens Grenoble, portant des **candélabres** :
  `vue_80d3d532_-114`, `vue_80d3d532_-142` (14/06/2025, vers NO : talus enherbé d'environ 1-1,5 m, feu du carrefour
  derrière), `planche_cb457c16_-023` (01/06/2025, sens Grenoble : bordure, butte, panneau de fin d'autoroute sur la
  butte), ortho IGN 2024 `site_ign2024_t00` et `planche_dessus_site_ign_t04` (les deux chaussées s'écartent : sens
  Grenoble vers y ≈ 13-26, sens Chambéry vers y ≈ −5…−19 à x ≈ 0).
- Le sens Grenoble tourne vers le nord-ouest pour rejoindre l'avenue de Verdun (`contexte_planign`, `t04`) : le
  modèle, droit, place cette chaussée environ 8 m trop au sud à x ≈ 0 (`planche_dessus_site_ign_t04`).
- **C28** (réduction du nombre de voies) **à gauche, sur la butte**, et à droite d'après le relevé de 2025
  (`planche_80d3d532_-029`) ; flèche de rabattement dans la voie de gauche du sens Chambéry.
- La **glissière du TPC commence vers x ≈ 50**, avec une balise jaune à son about (`vue_80d3d532_-029`).

### 3.2 Sens Chambéry (chaussée sud) et réduction 3 → 2

- 3 voies au départ, rive gauche continue sur la butte, rive droite continue avec ≈ 1 m d'enrobé puis glissière,
  grillage, chemin de service parallèle en vieil enrobé derrière (`vue_80d3d532_-029`, `vue_2f651fe1_-164` du
  28/07/2026 prise sur ce chemin).
- Réduction 3 → 2 par rabattement de la voie de gauche (`vue_80d3d532_-029` : flèche ; relevé 2025 : C28) ; position
  conforme à la description (biseau finissant vers s ≈ 108).
- Ensuite : BDG ≈ 1 m, **une glissière** contre elle, TPC d'herbe haute (sèche l'été, rase l'hiver) : `vue_121deee8_+013`
  (28/02/2026), `vue_661269be_-040` (14/06/2025), `vue_5221bda4_+038` (28/02/2026), `planche_cb374a8d_-119`
  (14/06/2025 : le rendu montre deux glissières, la photo une seule).

### 3.3 Sens Grenoble (chaussée nord) et TPC vu du nord

- 3 voies de la jonction de Mi-Plaine jusqu'au carrefour (`vue_140623f2_-017`, `vue_c97bad2a_-015`, `vue_cb457c16_-023`) ;
  **B14 70** des deux côtés vers x ≈ 140 (`vue_c97bad2a_-015`), panneau « ZONE » (circulation restreinte) et
  candélabres à droite, glissière et grillage à droite.
- À gauche : **pas de glissière** (`vue_140623f2_-017`, `vue_c1e3c195_-014` : BDG ≈ 1 m puis herbe haute et une balise
  blanche ; la seule glissière est de l'autre côté du TPC).
- Entre x ≈ 107 et 163 environ, une **large bande d'enrobé** (≈ 4-5 m) occupe le côté nord du TPC
  (`vue_c97bad2a_-015`, `vue_121deee8_+013`, `site_ign2024_t00` et `t01`, présente aussi en 2021 et 2018).

### 3.4 Entrée de Mi-Plaine (zone de conflit de f1)

- La bretelle quitte le giratoire de Mi-Plaine (x ≈ 272, y ≈ 120) et descend en **courbe serrée** ; sa voie devient la
  3e voie du sens Grenoble au droit d'un **petit musoir à chevrons en V** vers x ≈ 255-265, y ≈ 97-100
  (`site_ign2024_t01`, `site_ign2021_t01`, `planche_dessus_site_ign_t02`) ; panneau de sens interdit visible depuis
  l'A41 près du giratoire (`vue_5221bda4_+038`).
- Le modèle de l'itération 0 suivait l'axe OSM, qui court ensuite 60 m **sur** la chaussée de l'A41 : bretelle posée
  en travers de la BAU et des voies, 3e voie commençant à x ≈ 207 (`planche_dessus_site_ign_t02`).

### 3.5 Sortie 27 (zone de conflit de f2)

- Voie de décélération du sens Grenoble ouverte vers x ≈ 770-790 (début dans `auto_a41_section_courante`), séparée des
  voies par une ligne à **tirets larges** ; la bretelle s'en sépare vers x ≈ 665 ; **musoir à chevrons** de x ≈ 665 à
  597 (nez) ; au-delà, terre-plein d'herbe entre la bretelle et l'A41 qui s'élargit jusqu'au giratoire
  (x ≈ 470-490) : `f2/orthos/tuiles_natives/site_ign2024_t00`, `t01`.
- Entre les voies du sens Grenoble, tirets courts de dissuasion (T3) avant la sortie (`t01`, relevé 2025 8eb030a9).
- TPC : herbe, **une glissière** contre le sens Chambéry (ombre portée nette sur `f2 … t01`).
- Vues de f2 : `f2/…/vue_c48d56a7_-010` (01/06/2025, x ≈ 746, sens Grenoble) : 2 voies + voie de décélération déjà
  ouverte à droite, séparée par des **tirets larges** ; tirets **courts** (T3) entre les deux voies ; TPC d'herbe, glissière
  côté sud seulement. `vue_89fcd0fa_-005` (01/06/2025, x ≈ 658) : **musoir** entre deux lignes continues, **chevrons**
  pointés vers le conducteur, **balise J14a** verte et blanche au nez, bretelle à une voie à droite avec sa glissière,
  panneaux B14 et de direction au loin.

## 4. Contradictions entre dates, résolues

- Orthos 2015, 2018, 2021, 2024 et Pléiades 2025 : même géométrie (butte, entrée, sortie 27, TPC) ; la chaussée sud est
  refaite entre 2018 et 2021 (enrobé noir en 2021) ; la bande d'enrobé du TPC (x ≈ 107-163) est visible en 2018, 2021
  et 2024. Rien ne contredit les photos de 2025-2026 : état décrit = 14/06/2025 (photos 2026 cohérentes).
- Relevé de 2025 (lot B) : « deux files de glissière au TPC » ; les vues v2 des deux sens montrent une seule file
  (côté sud) : corrigé.

## 5. Ce qui reste incertain

- Hauteur de la butte du départ (≈ 1-1,5 m estimée sur photo) et type de bordure.
- Position exacte du nez de l'entrée (± 5 m) et largeur de la bande d'enrobé du TPC (± 1 m).
- Plans de feux du carrefour terminal (hors site, non observables).

## 6. Écarts au modèle et suite donnée

| Élément | Itération 0 (modèle du lot B) | Réalité (images) | Suite |
|---|---|---|---|
| Glissières du TPC | deux files de bout en bout | une file, côté sud, à partir de x ≈ 50 | description corrigée (it. 1) |
| Butte du départ | TPC plat de 10 m à deux glissières | butte de ≈ 15 m sans glissière | TPC de 15 m se resserrant à 8,1 m (it. 1) ; butte et bordure : BESOINS A41O-1 |
| Chaussée nord au départ | droite, ≈ 8 m trop au sud | s'écarte vers le nord-ouest | premier point de la médiane relevé de 4,5 m (it. 1) |
| Entrée de Mi-Plaine | axe OSM sur la chaussée, 3e voie dès x ≈ 207 | courbe serrée, 3e voie au nez x ≈ 259 | nœud N_A41_MIPLAINE déplacé, bretelle retracée (it. 1) ; chevrons du musoir : BESOINS A41O-2 |
| Bande d'enrobé du TPC | absente | x ≈ 107-163, ≈ 4-5 m | non décrite (chevauche le biseau de rabattement du sens est ; BESOINS A41O-3) |
| Sortie 27 | axe OSM de x = 753 sur la chaussée, pas de voie de décélération | voie de décélération x ≈ 528-420 (s), séparation x ≈ 662, chevrons jusqu'au nez x ≈ 597, J14a | voie de décélération (évènements à s = 420,3 et fermeture 498-528), zone hachurée à la place de la BAU de s = 350,4 à 420,3, bretelle partant de la voie de décélération (it. 1) ; chevrons et J14a : BESOINS A41O-2 |
| Resserrement du TPC (14 → 7 m) | transitions de 160 et 248 m ignorées (tronçons fusionnés : comparaison au profil de départ, B13) : sauts brusques à x ≈ 207 et 560 | resserrement progressif de x ≈ 400 à 778 | deux sauts placés au milieu des zones (x ≈ 450 et 560) ; transition réelle : BESOINS A41O-4 (B13) |
