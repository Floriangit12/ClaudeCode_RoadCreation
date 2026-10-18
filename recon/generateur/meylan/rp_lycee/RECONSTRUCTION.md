# Rond-point du Lycée — reconstruction (étape 3)

*`recon/generateur/meylan/rp_lycee/RECONSTRUCTION.md`, 18/10/2026. Lot de sites « giratoires et rues ». Description :
`description.yaml` (format réseau, résolue par `recon/generateur/reseau/`) ; besoins du générateur : `BESOINS.md`.
Sorties non versionnées : `recon/out/generateur/meylan_rp_lycee/`.*

## État

**Passe 2 (18/10/2026, soir) : itération 4 finale**, fabriquée, rendue et comparée avec l'outil v2 (60 photos, 243
vues). Voir la section « Passe 2 » ci-dessous et `COMPREHENSION.md`. L'état du premier passage est décrit ci-après.

**Premier passage : fabriqué, rendu et comparé (itération 2).** Date d'état : 28/07/2026. Giratoire de 66 m, anneau de 8 m,
couronne de 1,5 m, cinq branches (Verdun, Ancienne Mairie, 7 Laux jusqu'au nœud partagé `N_7LAUX_SO`, accès de
service est, Taillefer). Continuité avec `avenue_7_laux_separateur` par le contrat de profil du nœud (raccord de
≈ 30 m généré par le résolveur).

| Fichier | Contenu |
|---|---|
| `rendus/dessus.png`, `rendus/oblique_carrefour.png`, `rendus/planche_meylan_rp_lycee.png` | rendu seul (route seule, sans photo) de l'itération 2 ; oblique 3/4 depuis le sud-ouest, 62 m du centre, 34 m de haut |
| `iterations/iter0/`, `iter1/`, `iter2/` | vues de dessus et obliques de chaque itération |
| `comparaison/meylan_rp_lycee/` | sélection, poses, rendus des vues photo, grille `ecarts.json` (itération 2) et `ecarts_iter{0,1,2}.json` ; planches dans `photos_non_versionnees/` |
| `comparaison/jugements/iter{0,1,2}.json` | jugements de l'agent versés dans la grille (`outils_lot_c/remplir_grille.py`) |
| `journaux/` | fabrication, comparaison, essais, copies de la description de chaque itération |

Commandes : celles de `../avenue_7_laux_separateur/RECONSTRUCTION.md` (enveloppes `outils_lot_c/`, garde mémoire),
avec `--oblique 225,62,34,24` pour la fabrication.

## Itérations

La sélection des photos dépend du modèle (arêtes vues) : les photos changent un peu d'une itération à l'autre ; les
décomptes ne portent donc pas exactement sur les mêmes vues.

| Itération | Description | Comparaison (9 photos, 4 quadrants) | Constats |
|---|---|---|---|
| 0 (premier passage du lot) | relevé du 17/10 + harmonisation N1 ; branches droites et radiales | conformes 21, différents 21, non visibles 21 ; ressemblance bonne 1, moyenne 2, faible 3, inexploitable 3 | branche du Taillefer orientée 20° trop à l'est, entrée décrite « voie + hachures » au lieu d'une voie large, îlot planté et non en enrobé ; axe de Verdun 11 m trop au nord à 50 m ; séparateur des 7 Laux = muret plein |
| 1 (préparée au premier passage, fabriquée à la reprise) | Verdun recalé entre les deux sens OSM ; Ancienne Mairie recalée ; Taillefer en polyligne, tronc commun puis îlot planté de 4,6 m après une ouverture ; accès est raccourci à 18 m | — | **fabrication impossible** telle quelle : raffinement sans fin de Triangulate 2D dans `rg::sol` (hython à 52 Go, « Segmentation fault », journal `fab_iter1.log`). Cause trouvée par essai sous garde mémoire : le coin du giratoire atteignait le bout de la branche de 18 m (BESOINS G8). Accès est prolongé en ligne droite à ≈ 31 m : fabrication normale (3,9 Go). Comparaison : conformes 20, différents 9, en trop 2 ; bonne 1, moyenne 3, faible 1, inexploitable 4 ; recouvrement 3 px médian 0,03 → 0,13 |
| 2 (reprise) | Ancienne Mairie : séparation peinte de 0,6 m seulement sur les ≈ 20 derniers mètres (planche a56828f1 de l'itération 1 : pas de séparation loin de l'anneau) | conformes 17, différents 17, non visibles 29 ; **moyenne 4**, faible 2, inexploitable 3 ; recouvrement 3 px médian 0,01 → 0,13, écart moyen médian 28,1 → 17,7 px (4 poses affinées sur 9) | les écarts restants sont surtout des manques du générateur (murets) |

## Ressemblance par photo (itération 2)

| Photo | Date | Prise | Ressemblance | Ce que la planche montre |
|---|---|---|---|---|
| eea7ffb5 | 18/05/2025 | Ancienne Mairie, au passage | moyenne | deux voies et passage à la bonne place ; au passage, petit îlot bordé (panneaux) au lieu de la séparation peinte |
| 3d7dd376 | 28/07/2026 | anneau, vers Verdun | moyenne | orientation de Verdun juste (itération 1) ; muret et garde-corps du passage inférieur rendus en bordure |
| 5b9befe0 | 18/05/2025 | entrée des 7 Laux | moyenne | chaussée juste ; séparateur = muret béton plein ≈ 1 m, absent |
| bd7d48ad | 28/07/2026 | 7 Laux, à la ligne cédez | moyenne | nez du séparateur et ligne cédez à la bonne place ; muret absent |
| fcfac79c | 28/06/2026 | Taillefer, loin de l'anneau | faible | rendu au bout du modèle ; la photo montre un séparateur étroit bordé au-delà de la jonction décrite |
| f4bb6fc5 | 28/07/2026 | 7 Laux, vue latérale | faible | haie ; bordure basse au lieu du trottoir béton du modèle |
| 812f8985, 73c90e30, c965e640 | 2024 | piste et chemins dans les haies | inexploitable | 812f8985 montre le défaut du raccord de profil près du coin (G5) |

Sur l'itération 1 (autres photos) : a56828f1 (Ancienne Mairie loin de l'anneau) a motivé la correction de l'itération 2 ;
7486b798 confirme les deux voies d'entrée des 7 Laux et le muret.

## Écarts restants

1. **Murets** : séparateur des 7 Laux (muret plein ≈ 0,8-1 m, `../avenue_7_laux_separateur/BESOINS.md` S1) ; murets
   et garde-corps des passages inférieurs au bord de l'anneau (G3, F6) ; îlot central surélevé derrière un muret
   (rendu en disque de gazon plat, G3).
2. **Couronne** : béton balayé et rang de pavés non rendus (couronne grise unie, G4).
3. **Taillefer** : le séparateur étroit bordé se prolonge au-delà de la jonction décrite (fcfac79c) ; non corrigé
   (itérations épuisées).
4. **Ancienne Mairie** : petit îlot bordé au droit du passage, décrit en séparation peinte.
5. **Raccord des 7 Laux** près du coin du giratoire : facettes noires à ≈ 35 m de l'anneau (vue de dessus, G5).
6. **Accès est** prolongé en ligne droite jusqu'à 31 m alors que le vrai tracé tourne vers le nord à ≈ 20 m (contournement
   de G8).
7. Verdun : arrêts de bus et quais non décrits, sortie de 6,3 m décrite à 4,5 m ; enrobé fissuré et faïencé, joints de
   bordure peints en blanc non rendus.

## Passe 2 (18/10/2026) : compréhension par fusion des images, centre et îlots

Remarque de l'utilisateur, prise en compte ici : 6 à 10 photos ne suffisent pas pour comprendre la scène, et surtout
pas le centre et la zone de conflit. C'est l'agent qui fusionne les images dans son modèle : orthos de plusieurs dates
et 40 à 60 photos.

**Dossier v2.** `comparer_multivues.py meylan_rp_lycee --v2 --depuis 2024-05-01` :

- **60 photos, 243 vues** ; 32 photos prises sur l'anneau ou à son bord ; 186 vues voient le centre ;
- **aucune zone aveugle** : chaque secteur d'anneau est vu par 22 à 66 vues, l'îlot central par 34 ;
- orthos IGN 2015, 2018, 2021, 2024, IRC 2024 et Pléiades 2025 ; pas de PCRS ici.

**Ce que j'ai regardé moi-même, en tuiles natives** (détail dans `COMPREHENSION.md` § 1) :

- les orthos datées ;
- les zooms de l'IGN 2024 avec les bordures GAM ;
- 11 planches du centre (44 vues) et 7 vues natives ;
- après fabrication, les vues de dessus rendu | ortho côte à côte (`comprehension/zooms/iter4_*.png`) et 9 planches photo | rendu.

| Itération | Description | Résultat |
|---|---|---|
| 3 (passe 2) | Verdun recentré sur le séparateur GAM ; séparateur bordé de 0,9 m, puis terre-plein élargi de 0,9 à 7,3 m ; Mairie : séparateur bordé de 0,8 m sur 15 m ; Taillefer : axe GAM, tronc de 2 × 5 m, terre-plein revêtu de 0,6 à 6,8 m | 0 erreur à la compilation. Fabrication en 1 008 s, 7,1 Go. **Vue de dessus : les terre-pleins élargis par une loi de largeur ne sont pas fabriqués** : il ne reste que deux lignes sur l'enrobé (G13). Le terre-plein « enrobé » est en outre compilé en gazon. Pas de comparaison, l'itération 4 a été faite aussitôt |
| 4 (passe 2, finale) | îlots de Verdun et du Taillefer en **îlots séparateurs de giratoire** (`ilot: {largeur: 7.8, longueur: 35}` et `{7.2, 37}`), dans des enveloppes hachurées de 36 et 38 m | 0 erreur, 0 non-conformité non admise. Fabrication en 713 s, 7,3 Go. **Les îlots triangulaires sont à 1 à 1,5 m de leur place** sur l'ortho (`iter4_ouest`, `iter4_sud`), plus courts que le réel (20 à 25 m contre 26 à 33 m), et précédés de hachures absentes du réel (G14). Vues jugées : 9 ; moyenne 5, faible 3, inexploitable 1 (`comparaison/jugements/passe2_iter4.json`, grille `ecarts_iterp2_4.json`) |

**Ressemblance (itération 4)**

- **Branches et entrées : moyenne à bonne.** Les cinq entrées sont à leur place. Les îlots de Verdun et du Taillefer ont maintenant la bonne forme : planches `ed15dd0e_-146`, `23d3f6ff_-068`, `3c5f3ca7_-140`, `3df599ec_-146`. Le passage de la Mairie est juste.
- **Centre : moyenne, inchangée.** La géométrie de l'anneau est juste. Le cœur réel est hors de portée du PCG : muret, massif boisé, couronne en béton avec fil d'eau, passages inférieurs (`161a60d1_-134`).

Rendus seuls (route seule) de l'itération 4 :

- `recon/out/generateur/meylan_rp_lycee/rendus/dessus.png` et `oblique_carrefour.png` ;
- copies dans `iterations/iter4/` ;
- itération 3 : `iterations/iter3/`.

### Écarts restants après la passe 2

1. Îlot central : muret, massif boisé et sentier (G3 bis) ; couronne en béton incliné avec fil d'eau en pavés ou en grille fendue (G4 bis).
2. Passages inférieurs : parapets et garde-corps au bord de l'anneau, escaliers (G9).
3. Hachures d'enveloppe avant les îlots de Verdun et du Taillefer, absentes du réel (G14). Les îlots sont aussi plus courts de 6 à 8 m.
4. Accès du parking nord-ouest non décrit (G11, même cause que G8).
5. B1 aux nez des îlots et B21 sur le muret (G12).
6. Matériau des îlots : enrobé gravillonné clair au réel, béton balayé au rendu (G10).
7. Écarts du premier passage toujours valables : muret des 7 Laux (S1), accès est droit à 31 m (G8), raccord des 7 Laux (G5).
