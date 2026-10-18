# Rond-point de Didcot — reconstruction (étape 3)

*`recon/generateur/meylan/rp_didcot/RECONSTRUCTION.md`, 18/10/2026. Lot de sites « giratoires et rues ». Description :
`description.yaml` (format réseau) ; besoins du générateur : `BESOINS.md`. Sorties non versionnées :
`recon/out/generateur/meylan_rp_didcot/`.*

## État

**Passe 2 (18/10/2026, soir) : itération 4 finale**, avec la comparaison v2 (60 photos, 178 vues) : voir la section
« Passe 2 » ci-dessous et `COMPREHENSION.md`. L'état du premier passage suit.

**Premier passage : fabriqué, rendu et comparé (itération 2).** Date d'état : 28/07/2026. Giratoire de 47 m, anneau de 8,9 m,
couronne de 2 m ; quatre directions tracées vers l'anneau : Chamechaude (nord, passage à 5 m), Vieux Chêne est (sens
séparés par une bande boisée), bretelle de la rocade (sud, îlot enherbé), Vieux Chêne ouest (îlot planté, passage
piéton à ≈ 30 m de l'anneau). Pas de nœud partagé (sortie 26 de l'échangeur à ≈ 48 m, hors recouvrement).

| Fichier | Contenu |
|---|---|
| `rendus/dessus.png`, `rendus/oblique_carrefour.png`, `rendus/planche_meylan_rp_didcot.png` | rendu seul (route seule) de l'itération 2 ; oblique depuis le sud-ouest, 52 m du centre, 28 m de haut |
| `iterations/iter0/`, `iter1/`, `iter2/` | vues de dessus et obliques de chaque itération |
| `comparaison/meylan_rp_didcot/` | sélection, poses, rendus des vues photo, grille `ecarts.json` et `ecarts_iter{0,1,2}.json` ; planches dans `photos_non_versionnees/` |
| `comparaison/jugements/iter{0,1,2}.json` | jugements de l'agent versés dans la grille |
| `controle/` | ortho IGN 2024 des bouches (premier passage) |
| `journaux/`, `essais/` | fabrications, comparaisons, essai des rayons, copies de la description |

## Itérations

| Itération | Description | Comparaison | Constats |
|---|---|---|---|
| 0 (description du premier passage, fabriquée au premier passage, comparée à la reprise) | quatre directions vers l'anneau, rayons de raccordement par défaut (tableau ACI : Re 15, Rs 20) | 10 photos ; conformes 31, différents 13, absents 3 ; ressemblance moyenne 4, faible 4, inexploitable 2 ; recouvrement 3 px médian 0,09 → 0,10 | **trois coins sur quatre faisaient le tour de l'anneau** (180 à 186 m) : trottoir de coin en gazon en travers des bouches de Chamechaude, de la bretelle et du Vieux Chêne ouest (c4d60a47, 30b80a7b, ba5d0ba1) ; refuge du passage de Chamechaude absent ; passage de la branche ouest absent (265149e9) |
| 1 | rayons au bas des plages (Re 8 m RF-GV-GIR-011, Rs 15 m RF-GV-GIR-012) sur les quatre branches ; passage piéton de la branche ouest au nœud OSM 2213788508 | 10 photos ; conformes 34, différents 10, absents 2 ; bonne 1, moyenne 4, faible 3, inexploitable 2 ; recouvrement 0,06 → 0,10 | bouches libres (coins de 28 à 62 m) ; branche ouest : bandes latérales du mauvais côté loin de l'anneau, axe 4 à 6 m trop au sud-est (265149e9, bdce9363, f09ca37b) |
| 2 | branche ouest recalée sur OSM (tronc commun, cassure partagée) ; loin de l'anneau : bande enherbée + **chemin au sud-est**, profil de la coupe br_w_out seulement sur les 25 derniers mètres ; îlot planté précédé d'une ouverture de 10 m | 9 photos ; **conformes 37**, différents 8, absent 1 ; **bonne 3, moyenne 5**, inexploitable 1 ; recouvrement 0,10 → 0,15, écart moyen 19,9 → 18,3 px (4 poses affinées) | branche ouest ressemblante dans l'axe et en travers (bdce9363, 67619a0d, f09ca37b) |

## Ressemblance par photo (itération 2)

| Photo | Date | Prise | Ressemblance | Ce que la planche montre |
|---|---|---|---|---|
| f09ca37b | 01/05/2024 | branche ouest, en travers | **bonne** | passage, îlot au fond, bandes latérales justes (pose validée, confiance haute) |
| bdce9363 | 28/07/2026 | branche ouest, vers l'anneau | **bonne** | chemin et bande enherbée au sud-est, zébra au loin |
| 67619a0d | 28/07/2026 | branche ouest, loin | **bonne** | profil courant à double sens |
| c4d60a47 | 28/07/2026 | Chamechaude, vers l'anneau | moyenne | bouche libre ; zébra non visible sur la photo (ombre) |
| 30b80a7b | 28/07/2026 | anneau | moyenne | anneau juste ; couronne en pavés rouges et galets rendue grise (D2) |
| ba5d0ba1 | 01/05/2024 | bouche de Chamechaude | moyenne | passage juste ; refuge bordé au milieu absent (D4) ; traversée cyclable verte (D6) |
| 6c0347d0 | 23/11/2024 | bouche ouest | moyenne | îlot réel étroit et bas, celui du modèle large de 5 m et haut |
| 9d06b95b | 01/05/2024 | chemin sud-est | moyenne | coupe en travers semblable |
| ca8bf5b9 | 23/11/2024 | bois | inexploitable | — |

## Écarts restants

1. **Couronne** en pavés rouges avec deux rangs de galets (D2) et **îlot central en butte** (D3) : rendus en couronne
   grise et disque plat.
2. **Refuges** : bordé avec panneau au milieu du passage de Chamechaude (D4) ; à balise au passage de la branche ouest.
3. **Îlot de la branche ouest** trop large (5 m, plan coté) et à bordures hautes ; la photo le montre étroit et bas.
4. **Bande boisée du Vieux Chêne est** décrite à largeur constante de 12 m (6 à 24 m réels, D5).
5. Traversée cyclable verte et piste mixte à STOP cycliste (D6), panneaux, butte, mâts rouges : non décrits.
6. Rayons de raccordement pris au bas des plages pour contourner D1 (non mesurés).

## Passe 2 (18/10/2026) : compréhension par fusion des images, centre et îlots

**Dossier v2.** `comparer_multivues.py meylan_rp_didcot --v2 --depuis 2024-05-01` :

- 60 photos (56 Panoramax, 4 Mapillary), 178 vues ;
- 17 photos prises sur l'anneau ou à son bord ;
- 104 vues voient le centre ;
- aucune zone aveugle ;
- 9 photos au premier passage.

Orthos IGN 2015, 2018, 2021, 2024, IRC 2024 et Pléiades 2025.

**Lu moi-même en tuiles natives** (`COMPREHENSION.md` § 1) :

- les orthos datées ;
- les zooms de l'IGN 2024 avec les bordures et marquages GAM (`nord_gam`, `sud_gam`, `ouest_gam`) ;
- les vues côte à côte rendu | ortho ;
- 12 vues natives et 3 planches du centre (12 vues) ;
- après fabrication : `p2_centre`, `p2_ouest` et 8 planches photo | rendu.

| Itération | Description | Résultat |
|---|---|---|
| 3 (passe 2) | Bretelle : axe recalé sur l'îlot GAM, îlot séparateur triangulaire `{7.5, 17}` (au lieu du rectangle en gazon de 7 m, 4 m trop à l'est). Chamechaude : îlot en goutte d'eau `{6.5, 12}` coupé par le passage (absent avant). Ouest : petit îlot `{5.0, 9}` (au lieu de l'îlot planté de 20 m), refuge bordé de 1,2 m à balise | 0 erreur à la compilation ; écarts admis : refuge de Chamechaude 1,4 m (RF-GV-GIR-014), déflexion Chamechaude → ouest (RF-GV-GIR-008), axe de la bretelle (RF-GV-GIR-021). Fabrication en 638 s, 7,3 Go. Vues jugées : 6 ; moyenne 4, faible 2 (`comparaison/jugements/passe2_iter3.json`). Les trois îlots sont à 1 à 2 m de leur place (`p2_centre`). **Le passage ouest est ≈ 5 m trop près de l'anneau et le refuge posé dans le passage** (`p2_ouest`, planche `bdce9363_-013`) |
| 4 (passe 2, finale) | Passage ouest avancé à s = 65,5 (bandes du zébra GAM centrées vers (−54 ; −28)) ; deux lignes (zone hachurée de 1,2 m), puis refuge bordé de 1,2 m de s = 72 à 78, juste après le zébra | voir ci-dessous |

### Écarts restants après la passe 2

1. Couronne : pavés rouges en talus et deux rangs de galets, rendus en bande grise plate (D2 bis).
2. Îlot central : butte plantée de 1 à 1,5 m, rendue en disque plat (D3 bis).
3. Îlot de Chamechaude : forme de triangle ACI, au lieu d'un trapèze et d'un nez de part et d'autre du passage ; refuge de 1,4 m au lieu de ≈ 3 m (D7).
4. Hachures d'enveloppe trop longues avant les îlots de la bretelle et de la branche ouest. Le réel n'a qu'un contour peint (comme `../rp_lycee/BESOINS.md` G14).
5. Feux et ligne d'effet de l'entrée de la bretelle (D8).
6. Bande boisée du Vieux Chêne est à largeur constante (D5). Un double sens possible près de l'anneau, vu sur une seule photo (`COMPREHENSION.md` § 2.3), n'est pas tranché.
7. Voie de service et parking au nord de la branche ouest, non décrits.
