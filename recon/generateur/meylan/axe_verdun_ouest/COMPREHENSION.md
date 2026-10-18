# Compréhension de la scène — `axe_verdun_ouest` (avenue de Verdun côté La Tronche)

*18/10/2026, lot SITES, comparaison v2. Compréhension faite par le modèle en regardant lui-même, en tuiles natives
(≤ 1 092 px), les orthos de plusieurs dates, 50 vues tirées de 13 photos Panoramax 360° et les rendus du modèle.
Aucune image ici : chemins relatifs à `recon/out/generateur/meylan_axe_verdun_ouest/comparaison/meylan_axe_verdun_ouest/`
(photos et planches sous `photos_non_versionnees/`, jamais versionnées).*

## 1. Images regardées

- Fenêtre d'état 01/05/2024 → 22/06/2025 (état décrit : 18/05/2025, avant le chantier de Paquet Jardin) : 13 photos
  360° (3 séquences de voiture des 24/08/2024 et 18/05/2025, une séquence vélo du 01/05/2024), 50 vues ; zones :
  cases de 20 m du tronçon, passages peints (aucune zone aveugle).
- Orthos : IGN 2024 (09/08/2024) en tuiles natives `orthos/tuiles_natives/site_ign2024_t04` (carrefour M15 et
  traversée), vue générale `orthos/site_ign2024`, planches de dates `orthos/planche_dates_site_p01`, `p02` (2015, 2018,
  2021, 2024, Pléiades 2025, IRC 2024) ; Plan IGN `orthos/contexte_planign`.
- Vue de dessus : `dessus/planche_dessus_site_ign_t06` (traversée, rendu | ortho).
- Vues et planches citées ci-dessous (`photos_non_versionnees/v2/vues/vue_<clé>.png`,
  `photos_non_versionnees/v2/planches/planche_<clé>.png`).

## 2. La scène en une phrase

Boulevard d'entrée de ville à chaussées séparées : près de l'A41, 3 + 3 voies (voie de droite réservée aux bus) de
part et d'autre d'un terre-plein d'herbe bordé qui porte des candélabres décoratifs ; après le carrefour à feux de la
Plaine Fleurie (M15), 2 + 2 voies de part et d'autre d'un terre-plein bordé planté d'une haie taillée ; la « zone de
conflit » du site est la **traversée à feux de k ≈ 406** (x ≈ 245, y ≈ 293), où un passage piéton, une **traversée
cyclable en damier jaune posée en biais**, un refuge à barrières et le débouché d'une rue latérale se superposent.

## 3. Ce qu'il y a où

### 3.1 Tronçon 1 (k 30-225, x 0-128)

- 3 voies par sens, voie de droite **bus** séparée par des tirets larges ; **flèches directionnelles** dans les voies
  du sens sud-ouest vers x ≈ 100 (voie de gauche : tourne-à-gauche ; voie du milieu : tout droit et droite) à
  l'approche du carrefour terminal de l'A41 : `planche_0394d4c2_-010` (18/05/2025).
- Terre-plein d'herbe d'environ 3 m entre deux bordures basses, avec des **candélabres décoratifs (lanterne en
  filet)** plantés dans le terre-plein : `vue_225508c7_-167` (24/08/2024), `planche_0394d4c2_-010`.
- À gauche du sens sud-ouest : arrêt de bus, STOP d'une rue latérale (`vue_225508c7_-167`) ; enrobé rapiécé.

### 3.2 Tronçon 2 (k 280-625, x 164-401)

- 2 voies par sens (≈ 2,6-3,2 m), rive continue et étroite bande revêtue à droite, puis herbe et arbres ;
  terre-plein bordé planté d'une **haie taillée continue** (≈ 1,2 m) : `planche_93212a7b_-007` (24/08/2024 ; le rendu a
  la bonne structure, sans la haie), `vue_8c267a4e_-009` (près de la traversée, la haie fait place à des plantations
  basses sur gravillons).
- Enrobé très rapiécé et fissuré (`planche_8c267a4e_-009`, `planche_93212a7b_-007`).

### 3.3 Traversée de k ≈ 406 (zone de conflit)

- **Passage piéton** à bandes sur les deux chaussées, **feux** sur mâts et potences des deux côtés, boutons d'appel :
  `vue_1d9018fd_-034` (24/08/2024), `planche_8c267a4e_-009` (18/05/2025), `vue_0af315d8_-085` (01/05/2024, vélo).
- **Refuge** dans le terre-plein, revêtu, bordé, avec **barrières** (croix de Saint-André rouge-brun) des deux côtés et
  un poteau de feux : `vue_1d9018fd_-034`, `vue_0af315d8_-085`.
- **Traversée cyclable en damier jaune** (Chronovélo) : longue bande en damier qui traverse la chaussée sud-est **en
  biais** depuis x ≈ 190 vers le passage, puis le longe côté nord-est sur la chaussée nord-ouest : `planche_61a21d0a_-173`
  (18/05/2025 : le damier part sous la voiture et file vers le terre-plein), `vue_1d9018fd_-034` (damier contre le
  passage, à droite), ortho IGN 2024 `site_ign2024_t04` (bande claire en biais vers x ≈ 185, y ≈ 228).
- **Débouché d'une rue latérale** au nord-ouest au droit de la traversée (`site_ign2024_t04`, `planche_dessus_site_ign_t06`) ;
  flèche de rabattement blanche dans la voie de gauche avant le passage (`vue_1d9018fd_-034`).
- Position : le passage du modèle (itération 1 du lot B) tombe sur le passage réel à ≈ 4 m près
  (`planche_dessus_site_ign_t06`).

## 4. Contradictions entre dates, résolues

- 01/05/2024 (vélo) et 24/08/2024 / 18/05/2025 (voiture) : même traversée, même damier, mêmes barrières ; la haie
  du terre-plein est taillée en 2024 et 2025. Orthos 2015-2024 : même géométrie. Aucune contradiction ; l'état du
  18/05/2025 est retenu (le chantier de Paquet Jardin, plus à l'est, commence le 23/06/2025).

## 5. Ce qui reste incertain

- Tracé exact du damier en biais (largeur ≈ 3 m, angle ≈ 30-40° avec l'axe) : lu sur une ortho de 20 cm et deux photos.
- Affectation exacte des voies du tronçon 1 (flèches vues sur une seule photo).
- Haie : hauteur ≈ 1,2 m estimée.

## 6. Écarts au modèle et suite donnée

| Élément | Modèle (itération 1 du lot B) | Réalité | Suite |
|---|---|---|---|
| Profils des deux tronçons | justes (voies, terre-pleins bordés, bermes) | idem | inchangés |
| Traversée de k ≈ 406 | passage + refuge bordé, ≈ 4 m près | passage, refuge à barrières, feux, damier en biais, rue latérale | damier, feux, barrières : BESOINS V-O1, V-O2, V-O6 ; rue latérale : hors format de section (carrefour), non décrite |
| Candélabres et haie | non rendus (route seule) | dans le terre-plein | BESOINS V-O3 |
| Flèches du tronçon 1 | absentes | TAG / TD+TAD vers x ≈ 100 | non ajoutées (une seule photo, affectation incertaine) |
