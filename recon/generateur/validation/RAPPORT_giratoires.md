# Rapport du lot L5, partie giratoires : `rg::giratoires`, `rg::giratoires_sol`

*`recon/generateur/validation/RAPPORT_giratoires.md` — 18/10/2026. Critères : `validation/rapport_giratoires.json` ;
mesures détaillées : `validation/controles_giratoires.json` ; constats visuels : `validation/constats_visuels_giratoires.json`.
Documentation des HDA : `hda/rg_giratoires/README_GIRATOIRES.md` (texte prêt pour un § 10 de `hda/README_RG.md`).*

Demande : « le PCG doit reproduire des autoroutes, des ronds-points, plusieurs types de bordures… ». Ce lot fabrique dans
Houdini les **giratoires** décrits par le lot scenes (G1 urbain Ø 40 m à couronne franchissable, G2 périurbain Ø 50 m à
gouttes d'eau ACI, G3 mini-giratoire Ø 20 m à dôme franchissable). Route seule : sol neutre plat, ciel et soleil.

## 1. Ce qui a été fait

Le giratoire réutilise le cœur des carrefours plans du lot L3 au lieu de le refaire :

1. **`rg::giratoires::1.0`** (solveur, branché après `rg::carrefours`) lit l'anneau du modèle, pose les rayons des limites
   du profil d'anneau depuis `Rg − la`, calcule pour chaque branche les **congés d'entrée Re et de sortie Rs** (raccordements
   du modèle, ACI tableau 1) tangents au bord réel de la branche (évasement de l'entrée suivi par itération) et au bord
   extérieur de la chaussée annulaire, et en fait des **coins au contrat de `rg::carrefours`** : amorce, congé de sortie,
   arc de l'anneau, congé d'entrée, amorce. Il coupe les branches à la frontière (code L3), retire les routes d'anneau et
   fusionne son SOLVEUR avec celui des carrefours plans.
2. **`rg::carrefours_sol`** (lot L3, inchangé) fabrique alors, à partir de ce SOLVEUR, le sol de la chaussée annulaire, des
   bouches et des trottoirs de l'anneau, les bordures T2 des raccordements et de l'anneau (avec les abaissés et les BEV des
   passages proches) et les lignes CÉDEZ.
3. **`rg::giratoires_sol::1.0`** pose sur ce sol les îlots : couronne franchissable (bordure A2 de 3 cm, pavés, pente de
   5 % vers l'anneau), îlot central (cercle de l'anneau, A2, gazon, pied sur la couronne), dôme franchissable du
   mini-giratoire (10 cm, relief de 2 cm au bord) et îlots séparateurs (polygones du modèle, I2, béton balayé, refuges
   abaissés au droit des passages avec BEV). Il peint le contour T'2 3u du dôme et les lignes de l'anneau du profil (rive
   T2 3u de G2, interrompue aux bouches). Sorties au contrat de `rg::sol`, `pj::bordure` et `pj::marquage_solide`.
4. **Pilote `fabriquer_giratoires.py`** : réseau de `fabriquer_carrefours.reseau()` avec `rg::giratoires` inséré après
   `rg::carrefours` et `rg::giratoires_sol` branché sur le sol sans îlots ; exports `l5/` ; caméra conducteur recalculée
   (voir § 4). Aucun fichier partagé ni aucune HDA d'un autre lot n'est modifié.
5. **Contrôle indépendant** `validation/controler_giratoires.py` (Python sans Houdini, sur les exports), rapport
   `validation/faire_rapport_giratoires.py`.

Trois scènes fabriquées et rendues (G1 : dessus, conducteur, oblique ; G2, G3 : dessus, conducteur), planches regardées en
entier (≤ 1092 px), vues lues en tuiles natives, détails des îlots de G1 agrandis depuis le rendu natif. Durée : environ
6 min par scène avec les rendus.

## 2. Critères (mesurés sur la géométrie fabriquée)

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| GI-01 anneau de largeur uniforme, égale à la chaussée annulaire du modèle | G1 7,000 ; G2 9,000 (voies 8 + bande dérasée 1) ; G3 8,000 m ; écart 0,0 mm | ± 1 cm | oui |
| GI-02 déflexion de chaque traversée (cercle à 1,50 m de l'îlot fabriqué et 2,00 m des bordures) | G1 25,39 m ; G2 31,45 m (4 traversées chacun) | < 100 m | oui |
| GI-03 îlots séparateurs = ACI tableau 2 (H, B, d, r ; retrait 1 m) ; mini : 0,85-2,00 m | G1 4 îlots, écart max 2,8 mm (H 20, B 5, d 0,45, r 0,40) ; G2 4 îlots, 3,5 mm (H 25, B 6,25, d 0,50, r 0,50) ; **G3 0 / 4** | ± 1 cm ; 4 îlots | **non (G3)** |
| GI-04 refuges au droit des passages | G1 min 2,117 m (4) | ≥ 2,00 m | oui |
| GI-05 couronne franchissable | vue 0,030 m ; pente 5,00 % ; pavés contre enrobé | ≤ 0,03 m ; 4-6 % ; contrasté | oui |
| GI-06 îlot central hors agglomération sans obstacle (G2) | 0 arbre, gazon | 0 | oui |
| GI-07 passages en retrait de la ligne CÉDEZ | G1 5,00 m ; G3 2,00 m | 2-5 m | oui |
| GI-08 entrées / sorties tangentes, rayons | rupture max 0,400° (48 points) ; rayon − consigne max 0,04 mm (Re, Rs, anneau) | ≤ 0,5° ; ± 1 cm | oui |
| GI-09 ligne CÉDEZ sur chaque entrée | 4 / 4 sur G1, G2, G3 | toutes | oui |
| GI-10 mini-giratoire franchissable | dôme 10,0 cm ; relief 2,0 cm ; contour T'2 0,15 m (13 traits) | 10-15 cm (bus ≤ 12) ; 1-3 cm ; T'2 3u | oui |
| GI-11 sol étanche | écarts 0,13 / 1,00 / **1,72** mm ; bords libres hors extérieur **8** / 0 / 0 ; îlots posés : 0 bord libre visible | ≤ 1 mm ; 0 ; 0 | **non (G1, G3)** |
| GI-12 abaissés des refuges avec BEV | 8 abaissés, 8 BEV (G1) | 8 / 8 | oui |
| GI-13 planches regardées en tuiles natives | 3 planches, 7 vues | 3 ; 7 | oui |
| GI-14 déterminisme (G1 et G3, deux processus, une fois en fin de lot) | identique (64 fichiers L1, L2, L2b, L3, L5) | identique | oui |

## 3. Critères non atteints : causes

- **GI-03, G3** : les quatre îlots séparateurs du modèle du mini-giratoire sont dégénérés (0,12 m², 0,24 m de large
  sur 1 m) : le compilateur du lot scenes (`description/carrefours.py`, `_ilot_separateur`) applique au mini-giratoire la
  saillie de 0,50 m et le retrait de 1 m de l'ACI à une enveloppe de 1,50 × 6 m. `rg::giratoires_sol` les signale et ne
  les fabrique pas (seuil 0,5 m², [G]) ; l'enveloppe hachurée du profil reste peinte. À corriger dans le lot scenes : îlot
  du mini-giratoire = enveloppe entière (1,50 × 6 m, franchissable A2 3 cm), sans saillie ni retrait (RF-GV-GIR-016).
- **GI-11, G1** : 8 bords libres (2 par branche), à la coupe du trottoir des branches, sous la bordure : à l'abscisse de
  coupe, `rg::sol` fait monter le trottoir de la branche jusqu'à la face de bordure sur 2 cm quand le bord est évasé
  (loi de largeur), tandis que le coin de `rg::carrefours_sol` y pose le dessous de bordure bas. Le décalage est enfermé
  dans le volume de la bordure (invisible au rendu) ; même cas que le bord libre de J1 au lot L3.
- **GI-11, G3** : marche de 1,72 mm à la coupe des trottoirs (4 points, sous la bordure). Cause trouvée dans
  `rg::carrefours_sol` (lot L3, `vex_sol.py`, `VEX_DOMAINE`, pied des coins) : la pente du dessous de bordure `gl` est
  cherchée dans la coupe du profil en `s_tan` avec le `t` du bord **en `s_end`** ; sur un bord évasé ce `t` ne correspond
  à aucune limite en `s_tan`, `gl` reste nul et le dessous de bordure du coin est plat alors que celui de la branche suit
  le dévers de 2,5 %. C'est aussi l'écart de 1,74 mm de J4 (« dans l'ouverture à 1/15 »). Correction proposée au
  propriétaire de L3 : prendre `t` du bord en `s` (`rg_t_limites` en `s`) ; non faite ici (fichier hors lot).

## 4. Corrections et choix faits en cours de lot

- Première version : les jupes des îlots séparateurs avaient des points bas propres à chaque arête (bords verticaux
  comptés libres) : points bas partagés.
- Caméra conducteur : `fabriquer_carrefours.voie_entrante` prend 3,00 m pour toute largeur en loi ; sur l'évasement d'une
  entrée de giratoire la caméra tombait sur le trottoir. `fabriquer_giratoires.vues_giratoire` évalue les lois de largeur
  et place l'œil sur la voie entrante, 30 m avant la frontière.
- Choix [G] déclarés (paramètres d'HDA) : amorce 3 m ; coupe du trottoir reculée avant les rampants d'un passage proche
  (garde 0,10 m) pour que l'abaissé soit entier sur la bordure de coin ; pente de couronne 5 % (milieu de 4-6 %) ; relief
  du dôme 2 cm (milieu de 1-3 cm) et profil parabolique ; BEV de refuge à 0,40 m quand la demi-largeur du refuge est sous
  1,90 m (les deux BEV ne se chevauchent plus) ; îlot de moins de 0,5 m² non fabriqué ; rive intérieure de l'anneau
  décalée d'une demi-largeur sur la chaussée ; lignes de l'anneau interrompues entre les points de tangence des congés ;
  motif fermé du contour du dôme à période ajustée ; ouverture des files circulaires au sud.

## 5. Écarts du modèle signalés au lot scenes (hors lot)

- **G2** : le profil de la route d'anneau (voie 8 m + bande dérasée 1 m, référence décalée de 4,50 m) contredit l'anneau
  (Rg 25, la 8, Ri 17) de 0,50 m. Les rayons sont posés depuis `Rg − la` : le bord de chaussée est à 26 m, la bande
  dérasée hors de Rg, et la base des îlots séparateurs (Rg + 1 m) touche le bord de la bande dérasée.
- **G1, G2** : l'îlot séparateur est décalé de `d` vers la sortie (ACI) mais la zone hachurée du profil reste symétrique ;
  la marge hachurée n'existe que d'un côté de l'îlot.
- **Lignes CÉDEZ** : droites, à la frontière de la branche (sur l'axe : bord de l'anneau) ; elles s'écartent du cercle de
  l'anneau vers l'extérieur de l'entrée (bord de ligne à 1,09 m du cercle pour G1, 0,73 m pour G3). Les déplacer sur le cercle repousserait les passages
  au-delà de 5 m : laissé tel quel.
- **G3** (`rg::marquages`, lot L2b) : sans îlot, les hachures de l'enveloppe traversent les bandes du passage.
- `marquage_contour` des îlots séparateurs (continue 3u à 2u) non peint : l'enveloppe hachurée du profil en tient lieu.

## 6. Interface pour les autres lots

- **HDA `rg::giratoires::1.0`** (`hda/rg_giratoires/rg_giratoires.hdalc`) : entrées 1 routes, 2 profils, 3 SOLVEUR de
  `rg::carrefours` ; paramètres `fichier` (relié à `rg::lire_modele`), `amorce` 3 m, `rampant_passage` 2,40 (DEF-031),
  `garde_passage` 0,10, `fleche` 0,5 mm, `pas_angulaire_max` 0,8°. Sorties : 1 routes coupées sans anneaux, 2 profils
  (+ réduits ~cG / ~cD / ~cGD), 3 **SOLVEUR fusionné** (contrat L3 : branches, coins, embouchures, frontières, passages ;
  îlots des giratoires retirés), 4 **GIRATOIRES** (points `giratoire` : Rg, la, Ri, Ri_inf, slf, r_ci, R0, r_lim[], b0, b1,
  bandes `a_*[]` et limites `l_*[]` du profil d'anneau ; points `branche` : T_g/d, C_g/d, K_g/d, Rf_g/d, s_tan_g/d,
  s_cut_g/d ; `passage` ; primitives `ilot_g`, `coin` (u_Tb, u_Kb, u_Ka, u_Ta, rayon, rayon_b, rayon_anneau), `embouchure`,
  `frontiere`).
- **HDA `rg::giratoires_sol::1.0`** (`hda/rg_giratoires/rg_giratoires_sol.hdalc`) : entrées 1 GIRATOIRES, 2 sol sans îlots
  (rg::sol + rg::carrefours_sol) ; sorties 1 sol des îlots (classes `giratoire_ilot`, murs z_type 14), 2 BEV (groupe
  `dalles`), 3 ENTITÉS (`K-<îlot>`, contrat pj::bordure), 4 MARQUES (contrat pj::marquage_solide), 5 CONTRÔLES (faces).
- **Pilote** : `hython recon/generateur/fabriquer_giratoires.py SCENE.yaml… [--rendus] [--vues …] [--construire-hda]
  [--verifier-determinisme]` ; exports `<scene>/l5/giratoires.json`, `mesures_l5.json`, `manifest_l5.json` (plus L1, L2,
  L2b, L3). À intégrer : option `--giratoires` de `fabriquer_generateur.py` reprenant `reseau()` et `fabriquer()` de
  `fabriquer_giratoires.py` (le réseau est celui de L3 + deux nœuds ; une scène sans giratoire passe à l'identique).
- **Contrôle** : `python recon/generateur/validation/controler_giratoires.py [<scene>…] [--json …]` ;
  `python recon/generateur/validation/faire_rapport_giratoires.py --constats … --determinisme "…"`.

## 7. Limites

Branches droites tracées vers le centre ; anneau à une voie ; trottoir de l'anneau interpolé entre ceux des branches ;
chaussée annulaire par l'interpolation harmonique de L3 (pas le dévers du profil d'anneau) ; îlots posés sur un sol qui
continue dessous (caché, jupes jusqu'à 5 cm sous le sol) ; signalisation (AB25, B21-1, AB3a, J5) au lot L6 ; triangles
CÉDEZ absents du modèle ; terre-pleins (`rg::terre_pleins`) : autre partie du lot L5.
