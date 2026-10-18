# Carrefour à feux chemin du Vieux Chêne × avenue du Taillefer × Hélice de Meylan

*Relevé Meylan, lot A, 17/10/2026. Site M07 du dossier `D:\DocRoute\13_Observations_Panoramax_Isere`. Point du site :
45,20752 N, 5,783466 E ; Lambert-93 (918 477,69 ; 6 460 317,67) ; z ≈ 219,0 m (RGE ALTI). Centre du carrefour :
(−1,4 ; −1,3) m de ce point.*

**État décrit : 28/07/2026** (campagne IGN : photo 360° de 08:26, photos planes de 10:31), le plus récent.

C'est le carrefour d'arrivée de l'**Hélice de Meylan**, la bretelle qui descend de l'A41 et de la rocade sud : le bout
d'autoroute lui-même est relevé par le lot B (`../auto_a41_echangeur_meylan_est/`, `../auto_noeud_a41_n87/`).

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** ; la branche Hélice finit sur `N_VCT_HELICE` ; les deux chaussées de l'hélice du nœud A41 / N87 sont coupées au droit de ce nœud (recouvrement de 44,5 m supprimé ; raccord « jumelé » d'une branche à double sens et de deux chaussées à sens unique, besoin B2). Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description simple

> Grand carrefour à feux à quatre branches au pied de l'Hélice de Meylan. Au nord l'avenue du Taillefer (2 voies
> d'environ 3,5 m qui arrivent, 1 qui repart, environ 11 m de chaussée), à l'est et à l'ouest le chemin du Vieux Chêne,
> au sud la bretelle qui monte vers l'autoroute (2 voies dans chaque sens séparées par un îlot). L'entrée est arrive
> en 3 voies, dont 2 pour tourner à gauche ; les autres entrées ont une voie de tourne-à-gauche. Deux tourne-à-droite
> passent derrière des îlots directionnels bordés, en cédez-le-passage : de la bretelle vers l'est (courbe d'environ
> 25 m de rayon) et de l'ouest vers la bretelle. Les îlots portent des sens interdits et des mâts de panneaux de
> direction (« A41 Chambéry Genève », « La Tronche / Grenoble »…). Passages piétons à feux à bandes épaisses avec une
> traversée cyclable peinte en vert, pistes mixtes en enrobé le long du Vieux Chêne derrière des bandes d'herbe.
> Grande zone de conflit en enrobé très rapiécé, candélabres doubles avec décors lumineux, haies et murs blancs.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | terrain plat (z ≈ 219 m) ; la bretelle monte vers le sud |
| E08 bordures | îlots directionnels revêtus (nez arrondis), îlot entre les sens de la bretelle, séparateur bordé du Vieux Chêne est, bordures des trottoirs |
| E10 chaussée | quatre branches, zone de conflit, voies de shunt courbes |
| E11 trottoirs, pistes | pistes mixtes du Vieux Chêne, trottoirs du Taillefer, bandes enherbées |
| E12 marquages | lignes de voies, flèches d'affectation (TAG / TD / TAD), lignes d'effet, passages, traversées vertes (pratique locale photographiée), cédez-le-passage des shunts |
| E14 signalisation et feux | R11 sur chaque entrée, R12 aux passages, B1 sur les îlots, D21 groupés sur mâts, panneau d'autoroute bleu, AB3a des shunts |
| E15 éclairage | candélabres doubles décorés |
| E17 végétation (plus tard) | haies, grands arbres |

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Branches | Taillefer 340°, Vieux Chêne est 88°, Hélice 165°, Vieux Chêne ouest 242° | OSM (azimuts depuis le centre) |
| Taillefer à 25 m | chaussée 11,1 m : 2 entrantes de 3,5 m, 1 sortante de 3,8 m ; trottoir est 3,0 m | coupe `n_25` |
| Vieux Chêne est à 30 m | 3 entrantes 9,7 m (3,0 / 3,2 / 3,5), séparateur 0,26 m, sortie + shunt 7,0 m | coupe `e_30` ; OSM left\|left\|through;right |
| Hélice à 30 m | sortie 2 voies + shunt ouest 12,2 m ; entrée 2 voies + shunt est 11,2 m | coupe `s_30` ; OSM 1341306742, 235030396 |
| Vieux Chêne ouest à 30 m | entrée 2 voies + sortie 1 voie 9,7 m ; piste mixte | coupe `w_30` ; OSM 857526259, 190600691, 1351825052 |
| Îlots directionnels | shunt Hélice → est (rayon d'axe ≈ 25 m), shunt ouest → Hélice (≈ 36 m), cédez | OSM 168365100, 190600689, give_way ; photo fccb6997 (l+0102.9) |
| Régime | feux sur les 4 entrées, passages à feux | OSM traffic_signals ×4, crossings ×2 ; photo ad0b728e |
| Traversées cyclables | peintes en vert | photo ad0b728e (l-0102.9) ; RF-OBS-CYC-03 |
| Revêtement | enrobé très rapiécé, bandes de passage faïencées | photos e8178560, ad0b728e |

## 4. Ce que la description simplifie

- Le plan de feux est une hypothèse à 2 phases (DEF-028) ; les voies de shunt sont reconstruites par le solveur à
  partir du rayon et de la largeur dits.
- Le Taillefer est décrit avec 2 voies entrantes (lignes du levé GAM à 25 m) alors qu'OSM en compte 3 à la ligne de
  feux : la troisième naît probablement plus près du carrefour (à vérifier sur photo de face).
- Les décors lumineux, le panneau bleu d'autoroute et les murs blancs n'ont pas de mot dans le format.

## 5. Étape 3 — reconstruction (18/10/2026)

- Séparateur du Vieux Chêne est écrit « terre-plein » (une bande « séparateur » n'est pas fabricable, BESOINS.md G1),
  puis élargi à environ 1,2 m garni de gravillons (itération 2 : photos 3eb5557e, efc67150, 12844b83, c02e39f5).
- Itération 1 : la branche est n'est pas droite : elle part vers l'est-nord-est puis tourne vers le sud-est (droite de
  36 m, arc de ≈ 24 m de rayon ; médiane des chaussées OSM ; photos efc67150, 3eb5557e, 4c3c6ec3) ; axe ouest recalé
  sur la médiane OSM ; passage ouest déplacé à ≈ 47 m du centre (levé GAM, photo 4289a952) ; îlot séparateur bordé
  d'environ 1,4 m sur les 20 derniers mètres de la branche ouest (levé GAM, photo e5c7653d).
- Rapport : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## 6. Étape 3, passe v2 — centre relu (18/10/2026)

Dossier de compréhension v2 lu en tuiles natives (60 photos, 169 vues dont 65 du centre ; IGN 2015 à 2025) :
`COMPREHENSION.md`. Description simple du centre, telle qu'on la dirait :

> Le cœur est un grand espace d'enrobé uni et très rapiécé, sans aucun marquage intérieur. Chaque branche y débouche
> avec un îlot : au nord, un petit îlot refuge bordé (environ 1,5 × 4 m, B21) entre la sortie et les deux entrées du
> Taillefer, coupé par le passage et sa bande verte cyclable, puis un séparateur étroit ; à l'ouest, un îlot étroit à
> balise ; au sud, l'îlot central de l'Hélice ; à l'est, le séparateur en gravillons. Les deux tourne-à-droite directs
> passent en cédez derrière un petit triangle revêtu (Hélice → est) et un grand triangle (ouest → Hélice).

| Itération | Changement | Preuve |
|---|---|---|
| v2-1 | îlot refuge du Taillefer (ouverture de 4 m, terre-plein bordé 1,5 m, écarts DEF-022 et RF-MA-REF-003 admis) | c02e39f5 -131 et -174, 3c82fa3f +013 (28/07/2026), 0190214f -170 (28/06/2026) ; IGN 2024 |
| v2-2 | axe du Taillefer déplacé de 2,5 m vers l'est : l'îlot du modèle tombait 3 m à l'ouest de l'îlot réel | IGN 2024 lu à la grille (`ign24_coeur`) ; bordure est du levé GAM ; 2a5175d2 +009 |

Hors format : `BESOINS.md` (VT-1 séparateur étroit, VT-2 traversées vertes et damier, VT-3 zébra du levé GAM d'un autre
état).
