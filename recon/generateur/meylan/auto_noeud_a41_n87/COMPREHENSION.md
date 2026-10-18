# Compréhension de la scène — `auto_noeud_a41_n87` (nœud A41 / N87)

*18/10/2026, lot SITES, comparaison v2. Compréhension faite par le modèle en regardant lui-même, en tuiles natives
(≤ 1 092 px) et en zooms au plus proche voisin, les orthos de plusieurs dates, les vues tirées des photos Panoramax 360°
et les rendus du modèle ; aucune fusion algorithmique. Chemins relatifs à
`recon/out/generateur/meylan_auto_noeud_a41_n87/comparaison/<fenêtre>/` ; zooms d'ortho sous
`recon/generateur/tmp/lotB_sites/zooms/` (IGN, licence ouverte) ; photos et planches sous `photos_non_versionnees/`
(jamais versionnées ; aucune image ici).*

## 1. Images regardées

| Fenêtre | Emprise (repère du site) | Photos / vues | Dates | Zone de conflit visée |
|---|---|---|---|---|
| `meylan_auto_noeud_a41_n87` (f2 élargie) | x 374 → 657, y −172 → 238 | 13 / 52 | 23/06/2024 → 13/09/2026 | divergence de la N87 (musoir), pont de la N87 sur l'A41, raccord de la boucle, pied de l'hélice |
| `…_f4` | x −10 → 267, y −17 → 81 | 13 / 52 | 01/06/2025 → 28/06/2026 | sortie Sisteron (voie de décélération, musoir), fin de la voie d'insertion du sens Grenoble |
| `…_f5` | x 894 → 1 237, y 205 → 343 | 13 / 52 | 23/06/2024 → 13/09/2026 | divergence A41 → N87 sud (sens Grenoble), passage supérieur de desserte, portique |

Orthos : IGN 2024 (09/08/2024), 2021, 2018, 2015, IRC 2024, Pléiades 2025 ; lues en tuiles natives
(`orthos/tuiles_natives/site_ign2024_t00` à `t05` de f2 ; `t00`, `t01` de f4 et f5) et en zooms
(`zooms/nd_debut`, `nd_a41_x374`, `nd_a41_x510`, `nd_f5_est`, `a41sc_x300`, `a41sc_fin`). Vues de dessus : `f4/dessus/
planche_dessus_site_ign_t01`, `f5/dessus/planche_dessus_site_ign_t01`. Vues : citées ci-dessous.

## 2. La scène en une phrase

Échangeur sur trois niveaux : l'A41 (2 × 2 voies, TPC d'herbe à une glissière côté sud) passe sous le long pont de la
N87 ; vers Chambéry, la BAU devient 120 m avant le nœud la voie de décélération de la sortie Sisteron, qui quitte l'A41
par un long musoir à chevrons (nez au droit d'un portique) ; vers Grenoble, une 3e voie (insertion de la boucle puis de
la bretelle de Meylan, chacune par un musoir à chevrons) court sur 600 m et finit en biseau à l'entrée de la section
courante ; à l'est, les 3 voies du sens Grenoble se partagent sous un portique « Grenoble-Centre | Autres directions »
en 2 voies vers Grenoble et une branche vers la N87 sud, au droit d'un musoir à chevrons ; la TPC devient une GBA.

## 3. Ce qu'il y a où

### 3.1 Sortie Sisteron (sens Chambéry, f4)

- La **BAU devient voie de décélération** vers x ≈ 420 de la section courante (ligne T4 → tirets larges T2) :
  `zooms/a41sc_x300`, `a41sc_fin` ; entre les deux voies, tirets courts T3 (dissuasion).
- **Portique** au début du nœud : « A41 Turin-Milan Genève Albertville Chambéry » (2 flèches) | « N87 Sisteron
  St-Martin-d'H. / Gières Domaine universitaire » (1 flèche sur la voie de droite) : `vue_1575f4f9_-017` (14/06/2025).
- La voie quitte l'A41 vers x ≈ 30 ; **chevrons** de x ≈ 40 au **nez** vers x ≈ 190-195 (au droit d'un second portique),
  obliquité ≈ 1/31 : `zooms/nd_debut`, `f4/orthos/tuiles_natives/site_ign2024_t00` et `t01`.
- Modèle de l'itération 0 : bretelle posée sur la voie de droite et la BAU de l'A41 (axe OSM), pas de voie de
  décélération ni de musoir (`f4/dessus/planche_dessus_site_ign_t01`).

### 3.2 Sens Grenoble : voie d'insertion de 600 m (f2, f4)

- La **boucle** (N87 → A41 Grenoble) rejoint l'A41 par un musoir à chevrons étroit vers x ≈ 585-656 (`zooms/nd_a41_x510`) ;
  sa voie devient une 3e voie (tirets larges T2).
- La bretelle **Meylan → A41 La Tronche** arrive du nord-est et rejoint au droit d'un second musoir à chevrons vers
  x ≈ 380-420 (`zooms/nd_a41_x374`).
- La 3e voie continue jusqu'à un **biseau** vers x ≈ 10-20 (`f4/dessus/planche_dessus_site_ign_t01` : 3 voies de x 54 à
  202 ; `zooms/nd_debut`). Le modèle de l'itération 0 ne la portait qu'entre s = 420 et 559.

### 3.3 Pont de la N87, divergence de la N87, raccords (f2)

- Long pont à poutres béton sur piles (piles dans le TPC et les accotements), rive taguée : ortho `site_ign2024_t03`,
  relevé du lot B (7b271e3a, 949a4e59) ; non fabriqué (ND-1, ND-2).
- La N87 nord (3 voies) se partage au sud de l'A41 par un **musoir à chevrons central** (`site_ign2024_t04`) : à gauche la
  boucle, à droite 2 voies vers Chambéry (nouvel enrobé sombre) ; côté sud-est, entre l'A41 sens Chambéry et la branche
  vers Chambéry, une bande revêtue **hachurée** (x ≈ 520-650, `zooms/nd_a41_x510`).

### 3.4 Divergence A41 → N87 sud (sens Grenoble, f5)

- À l'est (x > 1 115) le sens Grenoble a **3 voies** (`zooms/nd_f5_est`) ; vers x ≈ 1 115 elles se partagent : 2 voies
  continuent vers Grenoble-Centre, la voie de droite (côté nord) devient la branche vers la N87 sud, qui gagne une voie ;
  **chevrons** de x ≈ 1 115 au **nez** x ≈ 1 004 (`f5/orthos/tuiles_natives/site_ign2024_t00`, `t01`) ; vues
  `vue_0ef894c3_-025` (23/06/2024 : chevrons, J14a au nez, passage supérieur), `vue_d3172e5e_-018` (01/06/2025 : portique
  « Grenoble-Centre / Meylan Mi-Plaine La Tronche Hôpital Nord » | « N87 E712 Autres directions / Gières Domaine
  universitaire », tirets de la voie de droite), `vue_5a4bbe0f_-159` (13/09/2026, depuis la branche N87 → Chambéry).
- **Passage supérieur de desserte** à x ≈ 1 007 (tablier mince, pile dans le TPC, garde-corps) : `vue_c45f498e_-153`,
  `vue_17f7f02c_-157` ; non fabriqué.
- TPC : **GBA béton** à partir de x ≈ 950 (`vue_d3172e5e_-018`) ; entre l'A41 sens Chambéry et la branche N87,
  **double glissière** sur une bande d'herbe (`vue_5a4bbe0f_-159`, `vue_17f7f02c_-157`).
- Modèle de l'itération 0 : la branche « A41 vers N87 sud » était posée sur l'axe OSM, qui court 60 m sur les voies du
  sens Grenoble ; pas de musoir (`f5/dessus/planche_dessus_site_ign_t01`).

## 4. Contradictions entre dates, résolues

- 2024, 2025 et 2026 : mêmes marquages et mêmes portiques ; la branche N87 → Chambéry a reçu un enrobé neuf (sombre sur
  l'ortho du 09/08/2024 au sud du pont) ; aucune contradiction avec les photos. État : 14/06/2025 (inchangé).
- Hélice : seules les photos du lot B (18/03/2023) la montrent ; non revue ici (hors fenêtres).

## 5. Ce qui reste incertain

- Position exacte des deux musoirs de convergence du sens Grenoble (± 10 m) et largeur de la voie d'insertion.
- Profil en long : non mesuré (trois niveaux, ND-1).

## 6. Écarts au modèle et suite donnée (itération 1)

| Élément | Itération 0 | Réalité | Suite |
|---|---|---|---|
| Sortie Sisteron | bretelle sur la chaussée de l'A41 | voie de décélération puis musoir de 160 m | voie de décélération dans le profil (ici et sur la section courante dès s = 431) et **`bretelles` type sortie** : obliquité 0,031, musoir peint de 372 m², S.5,00 à 166 m de la jonction (nez réel à ≈ 165 m) |
| 3e voie du sens Grenoble | s 420-559 | s ≈ 15-600 | voie d'accélération ← de s = 15 à 559 |
| Divergence vers la N87 sud | branche sur l'axe OSM, pas de musoir | partage à x ≈ 1 115, chevrons jusqu'au nez x ≈ 1 004 | 3 voies à l'est de s = 1 156, zone hachurée à la place de la BAU de s = 1 039 à 1 156, branche partant du point de partage ; chevrons côté ← : BESOINS ND-6 |
| Bandes hachurées et musoirs du sud, convergences du sens Grenoble | absents | présents | côté ← ou chaussées voisines : BESOINS ND-3, ND-6 |
