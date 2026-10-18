# Rond-point de Didcot — compréhension de la scène (fusion des images dans le modèle)

*`recon/generateur/meylan/rp_didcot/COMPREHENSION.md`, 18/10/2026, passe 2 de l'étape 3.*

Ce texte est ma lecture des images. Je les ai croisées moi-même, sans algorithme de fusion. Sources :

- les orthos datées (2018, 2021, 2024, 2025) ;
- 60 photos de la comparaison v2 (56 Panoramax, 4 Mapillary ; 178 vues, dont 104 voient le centre) ;
- les bordures et les marquages du levé GAM.

Toutes les images ont été lues en tuiles natives (≤ 1 092 px). Les chemins sont relatifs à
`recon/out/generateur/meylan_rp_didcot/comparaison/meylan_rp_didcot/`. Les photos sont sous
`photos_non_versionnees/` et ne sont jamais versionnées.

## 1. Images lues

| Source | Images |
|---|---|
| Orthos datées, même emprise | `orthos/planche_dates_centre_p01.png` (IGN 2024-08-09, Pléiades 2025, IGN 2021-08-13, IGN 2018-08-21), `orthos/planche_dates_site_p01.png`, `orthos/site_ign2024.png` |
| Zooms d'ortho IGN 2024 (grille du repère du site ; bordures GAM en rouge, marquages GAM en cyan) | `comprehension/zooms/centre_ign2024.png`, `centre_gam.png`, `nord_gam.png` (pas de 2 m), `sud_gam.png`, `ouest_gam.png` |
| Rendu de dessus de l'itération 2 \| ortho, côte à côte | `comprehension/zooms/cote_centre.png`, `cote_nord.png`, `cote_sud.png`, `cote_sud_ouest.png`, `cote_est.png` |
| Coupes des bordures et marquages GAM | Chamechaude y = 24 à 60 ; bretelle y = −24 à −55 ; ouest, 4 coupes obliques ; est, 4 coupes |
| Vues natives (1 092 px) | `30b80a7b_-121`, `30b80a7b_-020`, `f5ca5dc3_-175`, `604d69ac_+005`, `604d69ac_+051`, `m993270770`, `7544b177_+116`, `33fe9c2f`, `c4d60a47_-151`, `71960487_+132`, `bdce9363_-013`, `91a54867_-036` |
| Rendu de l'itération 2 | `../../rendus/dessus.png` |

Fenêtre d'état : depuis le 01/05/2024. Les 60 photos de la v2 sont toutes dans cette fenêtre : 01/05/2024, 23/11/2024,
29/05/2026 (Mapillary) et 28/07/2026.

## 2. Ce que je comprends de la scène

### 2.1 Anneau, couronne, îlot central (le centre)

- **Anneau.** Environ 9 m, en enrobé gris, sans voie marquée.
  - Une ligne de rive continue longe le côté de la couronne (`30b80a7b_-020`, `f5ca5dc3_-175`). Le GAM la donne en cercle au rayon ≈ 20 m.
  - Le diamètre extérieur (47 m) et la largeur de l'anneau sont justes dans le modèle : `cote_centre`, cercle rouge GAM sur le bord de l'îlot.
- **Couronne franchissable.** Environ 2 m, **en pavés rouges (aspect brique) posés en talus nettement incliné** : elle monte d'≈ 0,3 à 0,5 m vers la butte (`30b80a7b_-121` et `30b80a7b_-096`, planche `centre_p10` ; `9f232d8a_-055`, planche `centre_p18`), avec **deux rangs de galets** gris scellés parallèles au bord, bordure basse côté anneau.
  - Vues : `30b80a7b_-121` (vue rapprochée, 28/07/2026), `30b80a7b_-020`, `604d69ac_+005`.
  - Sur l'ortho 2018, la couronne apparaît plus rouge (`planche_dates_centre_p01`, ign2018) ; en 2021, 2024 et 2025, elle est plus claire. C'est la même couronne, vue sous un autre éclairage et une autre usure : la géométrie est identique.
- **Îlot central.** **Butte plantée** qui monte d'environ 1 à 1,5 m au-dessus de la couronne : couvre-sol (lierre), arbustes et massifs fleuris, une dizaine d'arbres.
  - Vues : `30b80a7b_-121`, `c4d60a47_-151`, `m993270770`.
  - Ortho : couronne d'arbres dense au centre, à toutes les dates.
  - **B21** bleus face aux entrées, posés sur la butte (`30b80a7b_-121`, `m993270770`).

### 2.2 Zone de conflit et entrées

- **Pas de marquage dans l'anneau** en dehors des rives.
- Les **lignes cédez-le-passage** en tirets suivent le bord de l'anneau à chaque entrée (GAM, `centre_gam`).
- **Bretelle de la rocade** : une **seconde ligne transversale** ≈ 5 m en amont (y ≈ −31) est la ligne d'effet d'un **feu**. Ce sont deux feux tricolores sur poteau, chacun avec un cédez (`m993270770`, Mapillary du 29/05/2026 ; OSM 10577671775).
- **Entrée du Vieux Chêne est** : un petit îlot triangulaire bordé, en (21 → 27 ; 6 → 10), sépare l'entrée de la sortie au bord de l'anneau (`cote_est`).

### 2.3 Branches et îlots séparateurs

**Avenue de Chamechaude, au nord** (`nord_gam`, coupes GAM, `c4d60a47_-151`, `71960487_+132`, `30b80a7b_-020`)
- Deux voies larges d'environ 4,7 m.
- Bande médiane peinte d'environ 0,9 m (deux lignes) jusqu'à y ≈ 33.
- Elle devient un **îlot séparateur bordé en goutte d'eau**, coupé par le **passage piéton zébré** (y 26,3 → 30) :
  - partie côté anneau : trapèze bordé, y 23 → 26,3, de 5,5 m à 3 m de large, entouré d'un contour peint plus large (8 m à la base) ;
  - partie extérieure : nez bordé de ≈ 2 m, y 30 → 32,6, avec un mât rouge et blanc et un cédez.
- L'îlot sert de refuge au passage.

**Bretelle de la rocade, au sud** (`sud_gam`, coupes GAM, `m993270770`, `604d69ac_+051`)
- **Îlot triangulaire bordé, revêtu** (gris, un mât) :
  - base de ≈ 6,5 m au bord de l'anneau, x 0,5 → 7 ;
  - **pointe en (11 ; −40)**, à ≈ 17 m de l'anneau ;
  - contour peint ; deux lignes continues se rejoignent ensuite vers (14 ; −47).
- **Sortie** d'une voie d'environ 5 m à l'ouest.
- **Entrée en deux voies** de ≈ 4,2 m à l'est, lignes GAM à y = −28 : 8,4 / 12,6 / 16,7.
- Plus loin (y < −50), tronc à trois voies et ligne axiale.
- À l'ouest de la sortie, une grande pelouse plantée.

**Chemin du Vieux Chêne ouest** (`ouest_gam`, `cote_sud_ouest`, `bdce9363_-013`, `33fe9c2f`)
- Au bord de l'anneau, un **petit îlot triangulaire bordé** : base ≈ 5 m côté anneau, ≈ 8 m de long, pointe vers (−30 ; −14,5), contour peint.
- Ensuite, **deux lignes discontinues** espacées d'≈ 1 m jusqu'au passage.
- Au **passage zébré**, à x ≈ −50 (≈ 27 m de l'anneau), un **refuge bordé étroit** (≈ 1,2 m sur ≈ 6 m) porte une **balise J5** (`bdce9363_-013`).
- Au-delà, axe continu.
- Au nord de la branche, une **voie de service et parking** débouche en (−45 ; −23) (OSM 844616066), avec **zone 30** (`33fe9c2f` : panneau de zone 30, piste mixte, jalonnement). Elle n'est pas décrite.

**Chemin du Vieux Chêne est** (`cote_est`, `91a54867_-036`, `7544b177_+116`)
- L'entrée (y 14 → 19) et la sortie (sous les arbres, vers le sud-est) sont séparées par une bande boisée de 6 à 24 m.
- **Incertain** : sur `91a54867_-036` (28/07/2026, à (41 ; 16)), la chaussée d'entrée porte une **double ligne continue** au milieu et une ligne discontinue à droite. Une voiture y roule en s'éloignant de l'anneau. Cette section serait donc à double sens près de l'anneau, alors qu'OSM la donne à sens unique. Je n'ai pas tranché : une seule photo, à l'ombre.

## 3. Ce que le modèle de l'itération 2 montrait faux, et ce que la passe 2 corrige

| N° | Élément | Itération 2 | Réel | Passe 2 |
|---|---|---|---|---|
| 3.1 | Îlot de la bretelle | rectangle en gazon de 7 m, x 5 → 13, précédé de 25 m de zone hachurée | triangle bordé revêtu, base 6,5 m, pointe à 17 m, x 0,5 → 11 | axe recalé sur l'îlot GAM (bout (3,77 ; −23,43)) ; îlot séparateur de giratoire `ilot: {largeur: 7.5, longueur: 17}` dans une enveloppe hachurée ouverte sur 26 m ; sortie 4,5 → 5,0 m, entrée 2 × 4,2 m |
| 3.2 | Îlot de Chamechaude | absent : bande peinte de 1 m jusqu'à l'anneau, passage sans refuge | goutte d'eau bordée coupée par le passage | `ilot: {largeur: 6.5, longueur: 12}` dans une enveloppe de 7,5 m ouverte sur 11 m ; le passage la coupe (refuge de 1,4 m dans le modèle, écart admis) |
| 3.3 | Îlot du Vieux Chêne ouest | îlot planté de 5 m sur 10 m, précédé de 10 m hachurés, x −45 → −30 | petit triangle de 5 × 8 m au bord de l'anneau | `ilot: {largeur: 5.0, longueur: 9}` dans une enveloppe ouverte sur 12 m |
| 3.4 | Refuge du passage ouest | absent | refuge bordé de 1,2 m à balise | terre-plein bordé de 1,2 m sur 7 m (s 70 → 77), passage à s = 71 |
| 3.5 | Couronne | grise unie, 2 m | pavés rouges et deux rangs de galets | inchangé (pas de mot), besoin D2 |
| 3.6 | Îlot central | disque d'herbe plat | butte plantée d'environ 1 à 1,5 m | inchangé, besoin D3 |
| 3.7 | Feu de la bretelle | absent | deux feux et une ligne d'effet à ≈ 5 m de la ligne cédez | pas de mot pour un feu sur une entrée de giratoire (besoin D8) |

## 4. Contradictions entre dates

- **Ortho 2018 contre 2021, 2024 et 2025.** En 2018, l'anneau est sombre et la couronne rouge vif ; ensuite, ils sont plus clairs. C'est un renouvellement d'enrobé sans changement de géométrie : îlots, passages et lignes sont aux mêmes places sur les quatre dates.
- **Photos du 01/05/2024, du 23/11/2024 et du 28/07/2026.** Mêmes îlots, même refuge à balise, même couronne. Les vues du 23/11/2024 (`f5ca5dc3`, `71960487`) sont en automne, sans feuilles.
- L'état décrit (28/07/2026) vaut donc depuis au moins 2021.

## 5. Ce qui reste incertain

- Le double sens de la branche est près de l'anneau (§ 2.3).
- La hauteur de la butte centrale (1 à 1,5 m, estimée) et la largeur exacte de la couronne (≈ 2 m).
- La forme exacte des parties d'îlot de part et d'autre des passages. Le générateur fabrique un triangle ACI continu : la partie extérieure de Chamechaude (nez de 2 m, au-delà du passage) n'est pas représentée en tant que telle.
- Le tracé de la voie de service au nord du Vieux Chêne ouest, non décrite.
