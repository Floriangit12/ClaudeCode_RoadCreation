# Carrefour à feux Verdun × Chamrousse × Chaumetière (M08) — manques du générateur rencontrés à l'étape 3

*`recon/generateur/meylan/verdun_lycee_feux/BESOINS.md` — 18/10/2026, lot « carrefours » de l'étape 3. Le code partagé
n'a pas été modifié. Les besoins G2, G6, G7 et G8 sont communs aux quatre carrefours du lot ; leur diagnostic complet
est dans `../vieux_chene_taillefer_feux/BESOINS.md`.*

## G2 — Triangulate 2D de `rg::carrefours_sol` qui ne se termine pas (bloquant)

Premier passage : plantage `GU_Delaunay` (`recon/out/generateur/meylan_verdun_lycee_feux/_travail/fab_v1.log`). Rendus
obtenus avec le contournement déclaré `angle_min = 0` sur `rg::carrefours_sol` (enveloppe
`meylan_paquet_jardin/_travail/fabriquer_lot_a.py`).

## L1 — Petit îlot libre au cœur du carrefour

- **Élément** : îlot rond bordé d'environ 2 m de diamètre, au milieu de la zone de conflit, entre les passages (photo
  921c90d1 t004 du 28/07/2026 ; planches 551efb9c et 54c3c177 : îlot à potelet au centre).
- **Constat** : le format ne connaît que les îlots portés par le profil d'une branche et les îlots directionnels de
  tourne-à-droite (`FORMAT_DESCRIPTION.md` § 15.2) ; un îlot « libre » (polygone ou cercle dit, dans le cœur) ne peut pas
  être décrit. Le solveur sait pourtant fabriquer des « îlots du cœur » (README_RG § 9, `ilots[]` sans
  `porte_par_profil`).
- **Besoin** : `ilots: [{type: refuge | separateur, centre: [x, y], diametre: 2}]` ou `polygone:` dans un carrefour,
  avec ses contrôles (surface ≥ 5 m², RF-GV-CAR-008 ; balayages).

## L2 — Chaussées séparées qui se croisent (quatre nœuds de feux)

- **Élément** : le carrefour réel est le croisement de deux routes à chaussées séparées (quatre nœuds de feux OSM
  137649, 57599588, 1689337428, 1689337431, à 13-18 m les uns des autres) ; les sens de Chamrousse se séparent autour
  d'un îlot planté triangulaire à partir de ≈ 30 m (photos 208a1f46, cb597029).
- **Constat** : décrit comme un seul carrefour à 4 branches centré au milieu des nœuds ; l'îlot de Chamrousse est
  approché à l'itération 1 par un terre-plein de largeur constante (≈ 5 m) précédé de sa zone hachurée ; sa forme
  triangulaire et la sortie courbe bordée de potelets (cb597029) ne sont pas représentables.
- **Besoin** : carrefour de chaussées séparées (deux carrefours couplés ou un carrefour à branches doubles), îlot de
  branche de largeur variable (loi de largeur dite par points).

## L3 — Piste cyclable qui traverse un angle de carrefour hors chaussée

- **Élément** : la Chronovélo coupe l'angle nord-ouest entre Verdun nord-est et Chamrousse, entre des massifs
  (photo ab5960e2 du 09/05/2024 : piste courbe avec figurine vélo ; OSM 190080268, 1241042273).
- **Constat** : les pistes ne sont décrites que dans le profil des branches ; le coin d'un carrefour est un trottoir
  ou une bande plantée (coin `coin_droit`), sans piste.
- **Besoin** : objet « piste de liaison » dans un coin (polyligne, largeur, bordures), ou piste de coin suivant le
  congé.

## L4 — Tirets de guidage du cœur non conformes à l'IISR

- Photos 5922e7b4, 921c90d1, 551efb9c : tirets prolongeant les voies dans le carrefour (dossier 13 M08 : « différent »
  de l'IISR7). Non décrits volontairement (ARB-08 : guidage seulement en phase spéciale de TAG). À trancher par
  l'utilisateur : pratique locale photographiée à reproduire ou non (`PLAN_GENERATEUR.md` § 9, décision 3).

## G6 — Outil de comparaison : sélection vide avec la date d'état

- Avec `--depuis 2025-06-01`, l'outil n'a retenu que 6 photos à plat du 31/08/2025, toutes dans le même quadrant
  (« -x ») ; les 68 photos IGN du 28/07/2026, dont les trois photos du relevé (921c90d1, 5922e7b4, ef8cd80b), sont
  écartées parce que le modèle n'occupe que 1,4 à 2,8 % de la hauteur de leur vue (seuil `EMPRISE_MIN` 3,5 % de
  `selection.py` ; diagnostic `meylan_verdun_lycee_feux/_travail/debug_selection.py`) : ce sont des photos à plat
  prises en hauteur et en plongée lointaine. Comparaison refaite avec `--depuis 2024-05-01` (photos 2024-2025 d'une
  voirie inchangée, `date_etat` 28/07/2026 conservée), sans toucher aux seuils.

## G8 — Fissures pontées de l'enrobé (photos ce9382f5, 006df5af, 0c2f5716)

## Passe v2 (18/10/2026) : ce que le centre réel montre et que le PCG ne sait pas faire

Lecture du dossier de compréhension v2 (59 photos, 129 vues dont 52 du centre, orthos 2015-2025) : `COMPREHENSION.md`.
Coordonnées dans le repère du site (x vers l'est, y vers le nord, origine au point M08) ; lectures à grille dans
`recon/out/generateur/meylan_verdun_lycee_feux/_travail/v2/lecture/`.

### LY-1 — Îlot de branche qui avance dans la zone de conflit (nez à 9 m du centre, frontière à 15 m)

- **Élément** : nez revêtu de la médiane de Verdun nord-est vers (8,2 ; 4,5), à ≈ 9 m du centre ; celui de Verdun
  sud-ouest vers (−12,5 ; −7,5), à ≈ 14,5 m. Images : `gam_NE`, `gam_SO` (IGN 2024 + levé GAM) ; vues 54c3c177_-008,
  8892229b_-012 (18/05/2025).
- **Constat** : l'îlot porté par le profil s'arrête à la frontière calculée (15,1 m au nord-est, 16,4 m au sud-ouest) ;
  la frontière vient des bords prolongés de Chamrousse et de Chaumetière, très obliques. Le nez réel est 6 m plus près.
  Par ailleurs, l'îlot n'existe que si la dernière section du profil commence avant la frontière ; un refuge revêtu
  dans un terre-plein planté coupe la section (le refuge est en béton balayé) et renvoyait l'îlot dans la zone de
  conflit : l'itération v2-1 met donc la médiane en béton depuis ≈ 26 m (écart de matériau sur ≈ 6 m).
- **Règles** : RF-GV-ILO-008, RF-OBS-ILO-01. **Besoin** : avancée du nez d'un îlot de branche dite (`nez: 9`, distance
  au centre) avec le contrôle des balayages ; refuge revêtu qui ne coupe pas l'îlot porté par le profil.

### LY-2 — Long passage en biais le long du bord de Verdun (Chamrousse)

- **Élément** : passage piéton d'≈ 25 m, en biais, le long du bord nord-ouest de Verdun, de (−24 ; 4) à (−5 ; 19),
  coupé par de petits refuges ; il traverse l'embouchure très oblique de Chamrousse. Images : `gam_NO` ; vues e40f8d0c
  (28/07/2026), 674d46c6_+171.
- **Constat** : un passage de branche est perpendiculaire à la branche, en retrait de la frontière ; le modèle met deux
  demi-passages à ≈ 24 m du centre, loin à l'ouest. **Besoin** : passage de carrefour dit par ses deux extrémités
  (polyligne, refuges traversés), non rattaché à une seule branche.

### LY-3 — Traversées cyclables en carrés et petits refuges à balise J5 du cœur (précise L1 et L4)

- **Élément** : rangées de carrés blancs d'≈ 0,5 m (traversées cyclables) le long du long passage et en travers du
  cœur, de (−20 ; 0) vers (−5 ; 12) ; petits îlots bordés bas en gravillons (≈ 1,5-2 m) à balise J5 vers (−13 ; 13),
  (−5,5 ; 10,5) et (−18 ; 2). Images : `gam_NO` ; vues 208a1f46_-076, -158 ; a7bf442e_-122 ; 02b1aad4_-049, -014
  (2024) ; 674d46c6_+171.
- **Règles** : RF-OBS-CYC-03, RF-MQ-GUI-01 (ligne de guidage), RF-GV-CAR-008 (surface d'îlot). **Besoin** : objet
  « traversée cyclable » de cœur (polyligne, marquage `carrés`), îlot libre du cœur (L1) avec balise J5.

### LY-4 — Embouchure évasée de Chaumetière avec îlot

- **Élément** : la rue d'≈ 6 m s'évase à ≈ 13 m au débouché (zébra de (−3 ; −17) à (10 ; −9)), petit îlot allongé
  vers (0 ; −11,5) côté cœur. Images : `gam_SE` ; vues 6b04ee98 (28/07/2026), 80dcf3ae_-054.
- **Constat** : décrite en 2 voies de 3,1 m jusqu'au centre ; seul le retrait du passage est corrigé (0,6 m).
  **Besoin** : évasement de branche au débouché (ouverture dans la zone de conflit) et îlot de bout de branche dit.

### G2 étendu — triangulations de `rg::sol`

- Toutes les fabrications de la passe v2 sont faites avec `--angle-sol 0` en plus de `--angle-carrefour 0` (enveloppe
  `meylan_paquet_jardin/_travail/fabriquer_lot_a.py`), après le plantage de `rg::sol` observé sur Paquet Jardin
  (`../paquet_jardin/BESOINS.md` PJ-8) : TQ-SOL-002 n'est pas tenu sur les routes, la forme du sol n'est pas changée.
