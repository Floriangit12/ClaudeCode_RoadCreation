# Carrefour Paquet Jardin (M01, état avant travaux) — manques du générateur

*`recon/generateur/meylan/paquet_jardin/BESOINS.md` — 18/10/2026, étape 3 (passe 1, puis passe v2 « centre »). Le code
partagé n'a pas été modifié : chaque manque est décrit ici avec l'élément réel, les images qui le montrent et la règle.
Coordonnées : repère du site (x vers l'est, y vers le nord, origine O du dépôt). Les vues citées sont celles du dossier
de compréhension v2 (`recon/out/generateur/meylan_paquet_jardin/comparaison/meylan_paquet_jardin/comprehension/`,
vues natives sous `photos_non_versionnees/v2/vues/`, jamais versionnées).*

## A. Passe v2 : ce que le centre réel montre et que le PCG ne sait pas faire

### PJ-1 — Traversée de la Chronovélo en rectangles jaunes (centre, Verdun sud-ouest) — besoin A2 / G4 précisé

- **Élément** : bande cyclable bidirectionnelle de ≈ 2,7 m qui traverse les deux chaussées de Verdun sud-ouest entre
  le passage piéton et le cœur, bordée de **deux rangées de rectangles jaunes** (≈ 1,2 × 0,5 m, pas ≈ 0,9 m) avec
  logos vélo, de (−13 ; −5,5) à (−2,5 ; −15), interrompue par l'îlot rond de la médiane (≈ (−7,4 ; −10,9)) ; la même
  traversée coupe la bretelle au sud de l'angle sud (≈ (−5 ; −27)), orientée nord-sud.
- **Images** : PCRS 10/05/2022 (`_travail/v2/lecture/pcrs_SO.png`, `pcrs_coin_SO_vercors.png`) ; vue 31d16b8e_-113
  (18/05/2025) ; IGN 09/08/2024 (moitié nord-ouest).
- **Règles** : RF-MA-CHR-007 (Chronovélo, pratique locale), RF-OBS-MAR-01, DEF-008 / DEF-020 (pratiques locales
  seulement si dites).
- **Besoin** : un objet « traversée cyclable » de branche (position par retrait ou par abscisse, largeur, sens,
  marquage : `rectangles jaunes`, `damier vert`, `bande verte`, `logos`), posé à côté du passage piéton et coupé par
  les îlots qu'il traverse ; il doit aussi pouvoir traverser une voie directe d'îlot directionnel.

### PJ-2 — Traversées cyclables vertes à damier de la Revirée (centre)

- **Élément** : sur chaque demi-passage de la Revirée, côté cœur, une bande de ≈ 1,5 m peinte en vert avec damier
  blanc, de (−9,5 ; 9) à (−6 ; 6) et de (−6 ; 13,5) à (−2,5 ; 9,5).
- **Images** : PCRS (`pcrs_NO.png`) ; vues 119d9094_+114 et e5d79de9_+037 (18/05/2025).
- **Règles** : RF-OBS-CYC-03, RF-MA-CHR-007. **Besoin** : le même objet que PJ-1 avec le marquage `damier vert`.

### PJ-3 — Ligne axiale mixte et flèches dans le cœur (guidage sans phase spéciale)

- **Élément** : la ligne axiale de Verdun se prolonge à travers tout le cœur, de l'îlot sud-ouest à l'îlot nord-est
  (≈ 20 m) : en 2024-2025, ligne **mixte** (continue côté sud-est, discontinue côté nord-ouest, que franchissent les
  tourne-à-gauche de Verdun nord-est vers le Vercors) ; flèches de direction (tout droit) de part et d'autre, vers
  (5 ; 1) et (−6 ; −8).
- **Images** : IGN 09/08/2024 (zoom du centre) ; vues 119d9094_-045, -015, -134 (18/05/2025), 5c0d1d39_-057 et
  2ab4efbc_-099 (24/08/2024). PCRS 2022 : tirets courts (état antérieur, repeint en 2024).
- **Constat** : `guidage` n'est accepté qu'aux feux et pour des TAG opposés en phase spéciale (ARB-08, RF-MQ-GUI-01,
  RF-MQ-CAR-03) ; aucune clé pour une ligne de continuité ou une ligne axiale dans la zone de conflit, ni pour des
  flèches dans le cœur.
- **Besoin** : un marquage de cœur dit (`ligne: {de: <branche>, vers: <branche>, modulation: mixte|T'1|T3|continue,
  cote_continu: ...}`) posé le long de l'axe joignant les deux branches, et des flèches de cœur (position par fraction
  de cette ligne).

### PJ-4 — Passage qui coupe un îlot central au bord du cœur (Vercors) : l'îlot disparaît sous le refuge

- **Élément** : îlot central du Vercors en galets, en **triangle** au bord du cœur (sommets ≈ (2,9 ; −12,2), (6,2 ; −13,5),
  (4,2 ; −15,7), ≈ 6 m², B21), puis le passage (refuge à niveau), puis l'îlot long (≈ 2 m) jusqu'à ≈ 27 m.
- **Images** : `pcrs_coin_SO_vercors.png`, `pcrs_SE.png` ; vues 119d9094_-045 et -084 (18/05/2025), a1ffea74, 4d9fa65d.
- **Constat** : décrit par une ouverture du profil (terre-plein 2 m galets) ; le compilateur revêt le refuge sur la
  largeur du passage **et ses rampants de 2,40 m** (RF-OBS-ILO-01, DEF-031) ; entre la frontière et le refuge il ne reste
  que ≈ 2,2 m² d'îlot (contrôle RF-GV-CAR-008 « 5 m² », écart admis dans la description pour ne pas bloquer).
- **Besoin** : un refuge « coupure à niveau » sans rampants (l'îlot réel est coupé net à la largeur du passage), et
  une forme d'îlot de bout de branche dite (triangle, nez élargi au bord du cœur).

### PJ-5 — Bretelle de tourne-à-droite longue et grand îlot d'angle (angle sud) — besoin P1 précisé

- **Élément** : la bretelle SE quitte Verdun à ≈ 100 m, longe Verdun derrière une séparation peinte et une barrière
  (quais La Revirée), puis contourne le **grand îlot revêtu de l'angle sud** (≈ 8 × 8 m, sommets ≈ (−2,3 ; −14,7),
  (−6,5 ; −19), (1,1 ; −20,8), dos vers y ≈ −23,5 ; mâts R11, la Chronovélo le traverse) et rejoint la sortie du Vercors
  vers (5 ; −26). Sa traversée (zébra + rectangles jaunes) est orientée nord-sud, ≈ 4 m au sud du prolongement du
  passage de Verdun sud-ouest.
- **Images** : `pcrs_S_bretelle.png`, `pcrs_coin_SO_vercors.png`, tuiles t06-t07 du PCRS ; vues 0fe2656f, 034cb578,
  31d16b8e_-113.
- **Constat (itération 2)** : décrite en îlot directionnel (`rayon: 16, largeur_voie: 4, passage: oui`) ; l'îlot du
  modèle est la zone d'angle hors du disque R + W (forme imposée, RF-GV-ILO-015) et le passage de la voie directe est le
  prolongement en ligne droite de celui de la branche (refuge de 1,1 m à la pointe : DEF-022, écart admis).
- **Besoin** : (1) voie directe longue (quitte une branche à une abscisse dite, rejoint l'autre branche à une abscisse
  dite) ; (2) îlot directionnel de forme dite (polygone ou cotes) ; (3) passage de voie directe positionné et orienté
  séparément ; (4) régime de la voie directe au débouché (cédez, feux).

### PJ-6 — Îlot de branche en coin (Revirée) et îlots de largeur variable

- **Élément** : l'îlot de la Revirée est un **coin** : ≈ 2-3 m de large au bord du cœur (≈ (−4,3 ; 5,7)), il s'effile et
  passe entre les deux demi-passages décalés jusqu'à un nez étroit (poteau bois) ; il porte les D21.
- **Images** : `pcrs_NO.png` ; vues 119d9094_+114, e5d79de9_+037, 31d16b8e_+160, 2ab4efbc_+179.
- **Constat** : le profil fait un îlot rectangulaire (terre-plein 2,2 m). **Besoin** : largeur d'îlot de branche dite
  par points (déjà L2 de `verdun_lycee_feux`), demi-passages décalés d'une même branche.

### PJ-7 — Angles plantés en pointe (angle ouest)

- **Élément** : îlot d'angle planté (herbe haute, bordure granit) en pointe entre la Revirée et Verdun sud-ouest,
  hypoténuse ≈ (−8,5 ; 3) → (−13,5 ; −2) ; la Chronovélo passe derrière.
- **Images** : `pcrs_NO.png` ; vue 31d16b8e_+160 (18/05/2025).
- **Constat** : le coin du solveur prend le revêtement de la bande extérieure à la frontière (trottoir revêtu de la
  liaison du passage) : l'angle est rendu en trottoir (même manque que L3 de `verdun_lycee_feux`). **Besoin** : matériau
  et forme du coin dits (`coin: {rayon, sol: gazon, forme: pointe}`).

### PJ-8 — G2 étendu : la triangulation de `rg::sol` plante aussi (branche courbe à îlot)

- **Constat** : fabrication de l'itération 2 (description `description.yaml` du 18/10/2026, 21 h) : segfault dans
  `GU_Delaunay::RefinerT::splitEncroachedEdges` (journal `recon/out/generateur/meylan_paquet_jardin/_travail/v2/fab_iter2.log`)
  pendant la cuisson de `/obj/generateur_l1/sol/trianguler` (arête 0,25 m, angle 25°). Entrées enregistrées
  (`_travail/v2/diag_tri/tri00_entree.bgeo.sc`, `tri01_entree.bgeo.sc`) ; bissection par route
  (`_travail/v2/diag_tri/bissection_routes.log`) : R-1, R-2, R-3 seules passent en 0,2 à 1,9 s, **R-4 seule (Vercors :
  tracé droite + arc de 60 m + droite, ouverture d'un îlot central à 51 m) plante** ; angle 0° : 484 924 triangles en
  2,1 s.
- **Contournement déclaré** : `--angle-sol 0` de l'enveloppe `_travail/fabriquer_lot_a.py` (rien d'enregistré dans les
  HDA) ; TQ-SOL-002 n'est plus tenu sur les routes de ce site.
- **Besoin** : celui de G2 (nettoyer l'entrée, plafonner le raffinement avec un message), étendu à `rg::sol`, avec cette
  entrée en scène de non-régression.

## B. Besoins de la passe 1 (toujours ouverts)

- **G2** — Triangulate 2D de `rg::carrefours_sol` qui ne se termine pas (bloquant) : contournement `angle_min = 0` sur
  l'instance (enveloppe `_travail/fabriquer_lot_a.py`) ; diagnostic complet dans `../vieux_chene_taillefer_feux/BESOINS.md`.
- **P1** — Bretelle de tourne-à-droite séparée de 100 m : précisé en PJ-5.
- **G4** — Traversées de la Chronovélo et bandes vertes : précisé en PJ-1 et PJ-2.
- **G6** — Outil de comparaison : profil « visé » faux sur une scène de réseau (même constat que
  `../vieux_chene_taillefer_feux/BESOINS.md` § G6).
- **G7** — Vues économes des scènes de réseau (dessus + oblique) : enveloppe `fabriquer_lot_a.py`.
- **G8** — Fissures pontées et reprises de l'enrobé ancien : photos 119d9094, 9834f494, e86aa913, 034cb578, 734a0da6
  (enrobé ancien très fissuré, pontages noirs) ; le rendu « enrobé usé » est uniforme (RF-OBS-REV-01).
