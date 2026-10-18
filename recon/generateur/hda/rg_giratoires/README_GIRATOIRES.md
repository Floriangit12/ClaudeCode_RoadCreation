# hda/rg_giratoires : HDA du lot L5, partie giratoires (`rg::giratoires`, `rg::giratoires_sol`)

*18/10/2026. Plan : PLAN_GENERATEUR § 2.4 (étape 4, « giratoire ») et § 3 (L5). Rapport :
`validation/RAPPORT_giratoires.md`. Construction : `construire.py` (code VEX dans `vex_giratoires.py`,
`vex_giratoires_sol.py`, bibliothèque `vex/rg_giratoire.h` ; lecture Python `lecteur_giratoires.py`). Pilote :
`recon/generateur/fabriquer_giratoires.py` (importe fabriquer_carrefours, fabriquer_l2, fabriquer_l2b et
fabriquer_generateur sans les modifier). Contrôle : `validation/controler_giratoires.py`,
`validation/faire_rapport_giratoires.py`. Texte prévu pour un § 10 de `hda/README_RG.md` (à reporter par l'agent
d'intégration).*

Principe : le giratoire réutilise le cœur des carrefours plans. `rg::giratoires` traduit l'anneau en coins au contrat
de `rg::carrefours` ; `rg::carrefours_sol` (lot L3, inchangé) fabrique alors le sol de la chaussée annulaire, des
bouches et des trottoirs de coin, les bordures de coin (congés et anneau) et les lignes CÉDEZ. Les îlots (couronne,
îlot central, dôme, séparateurs) sont **posés** sur ce sol par `rg::giratoires_sol`. La route d'anneau du modèle n'est
plus déroulée par `rg::profils` / `rg::sol` : son profil sert seulement à poser les rayons des limites.

```
rg::lire_modele ─► rg::carrefours ─(1 routes, 2 profils, 3 SOLVEUR)─► rg::giratoires ─► 1 routes coupées, sans anneaux ─► rg::graphe …
                                                                                   ├► 2 profils (+ réduits) ─► rg::graphe, rg::profils,
                                                                                   │                          rg::nivellement, rg::vers_entites, rg::marquages
                                                                                   ├► 3 SOLVEUR fusionné ─► rg::carrefours_sol (cœur : anneau, bouches, coins)
                                                                                   └► 4 GIRATOIRES ─┐
                                    sol sans îlots (rg::sol + rg::carrefours_sol, sortie 1) ───────┴► rg::giratoires_sol
   sorties : 1 sol des îlots, 2 BEV, 3 ENTITÉS (bordures des îlots), 4 MARQUES (contour du dôme, lignes de l'anneau), 5 CONTRÔLES
pilote : sol total = rg::sol + cœur + îlots ; entités = rg::vers_entites + coins + îlots ; marques = rg::marquages + cœur + anneau
```

## `rg::giratoires::1.0` (« RG Giratoires (solveur) »)

Entrées : 1 routes, 2 profils, 3 SOLVEUR de `rg::carrefours` ; paramètre `fichier` (relié à `rg::lire_modele`).
Carrefours de type `giratoire` et `mini_giratoire`.

1. **Anneau** : bord intérieur de la chaussée annulaire `r_ci = Rg − la` (anneau du modèle) ; rayons des limites du
   profil de la route d'anneau posés depuis `r_ci` (bandes de l'intérieur vers l'extérieur) ; `R0` = bord extérieur des
   bandes « chaussee » (voie + bande dérasée éventuelle) : cercle des raccordements. Un écart entre `R0` et `Rg` ou entre
   les voies du profil et `la` est signalé (G2 : bande dérasée de 1 m hors de Rg → R0 = 26 m).
2. **Branches** : repère à la frontière (`s_front` = joint de frontière du modèle), bords de chaussée réels (lois de
   largeur : évasement de l'entrée et de la sortie), extérieurs. **Congés** : entrée `Re` à droite (voies entrantes), sortie
   `Rs` à gauche (raccordements du modèle, ACI tableau 1, RF-GV-GIR-003), tangents au bord réel (droite locale itérée) et
   extérieurement au cercle `R0` (`rgi_conge`). **Coupes** des trottoirs : `s_tan − amorce` (3 m, [G]), reculées avant les
   rampants d'un passage proche (`s − l/2 − 2,40 − 0,10`, DEF-031, [G]) : l'abaissé du passage est alors entier sur la
   bordure de coin.
3. **Coins** (contrat de `rg::carrefours`, de B vers A, côté haut à gauche) : amorce de B (partie 0), congé de sortie de B,
   arc horaire du cercle `R0`, congé d'entrée de A (partie 1), amorce de A (partie 2) ; pas angulaire ≤ 0,8°, flèche
   ≤ 0,5 mm. Attributs de L3 + `rayon_b` (sortie), `rayon_anneau`, `centre_arc_b`, `centre_anneau`, `u_Tb`, `u_Kb`, `u_Ka`,
   `u_Ta` (points de tangence), `giratoire = 1`. Frontière fermée, embouchures (code L3).
4. **Routes** : branches coupées en `s_end = s_front` (code L3 `VEX_COUPER_ROUTES`, profils réduits `~cG` / `~cD` / `~cGD`) ;
   routes d'anneau retirées.
5. **SOLVEUR fusionné** : SOLVEUR des carrefours plans (îlots des giratoires retirés : ils sont posés) + branches, coins,
   embouchures, frontières, passages des giratoires. Les lignes CÉDEZ des giratoires viennent du SOLVEUR L3.

Sortie 4 **GIRATOIRES** : points `giratoire` (`Rg`, `la`, `Ri`, `Ri_inf`, `slf`, `r_ci`, `R0`, `r_lim[]`, `b0`, `b1`,
bandes `a_*[]` et limites `l_*[]` du profil d'anneau, `l_mmod[]`, `l_mlu[]`, `l_mum[]`), `branche` (`T_g/d`, `C_g/d`,
`K_g/d`, `Rf_g/d`, `s_tan_g/d`, `s_cut_g/d` …), `passage`, primitives `ilot_g` (îlots du modèle), `coin`, `embouchure`,
`frontiere` ; détail `rg_anneaux`, `rg_giratoires_ids`, `rg_giratoires_avertissements`.

## `rg::giratoires_sol::1.0` (« RG Giratoires (îlots posés, marques de l'anneau) »)

Entrées : 1 GIRATOIRES, 2 sol sans îlots. Faces de bordure (polylignes fermées, sens trigonométrique, îlot à gauche,
contrat des faces de `rg::carrefours_sol`) :

| Îlot | Face | Bordure | Dessus |
|---|---|---|---|
| couronne franchissable (bande `terre_plein` du profil d'anneau contre la chaussée) | cercle `r_ci` | limite du profil (G1 : A2, 0,03 m) | tête − 4 mm à l'arrière de la bordure (TQ-SOL-013 (5)) puis **pente 5 %** vers le centre (RF-GV-GIR-006 : 4-6 %, milieu [G]) jusque sous la bordure centrale ; pavés du profil |
| îlot central infranchissable | cercle `Ri_inf` de l'anneau (contrôle : polygone du modèle) | ceinture du modèle (A2) | tête − 4 cm planté (TQ-SOL-013 (7)) ; pied sur la couronne |
| dôme du mini-giratoire (franchissable, `bombement_m`) | cercle `Ri` | aucune | z = sol + relief + (h − relief)(1 − (ρ/R)²) [G] ; relief 2 cm au bord (RF-GV-GIR-016 : 1-3 cm, milieu [G]) |
| îlots séparateurs | polygone du modèle (densifié 0,5 m ; < 0,5 m² : signalé, non fabriqué [G]) | ceinture du modèle (I2 ; A2 mini) ; abaissés des passages (DEF-031) | Triangulate 2D ; tête − retrait de la bordure la plus proche (refuge abaissé) |

Jupes (murs `z_type` 14, invisibles) du bord de chaque dessus jusqu'à 5 cm sous le sol posé ; au bord du dôme la jupe
est visible (relief). Pieds des bordures : sol posé (plus haute face visible sous le point) ; îlot central : couronne.
**BEV** : code de `rg::carrefours_sol` ; au refuge, profondeur réduite (0,40 m) quand la demi-largeur du refuge est
sous 1,90 m (DEF-031 par analogie, [G] : les deux BEV ne se chevauchent pas). **ENTITÉS** : code de
`rg::carrefours_sol` (identifiants `K-<îlot>`). **MARQUES** (contrat `pj::marquage_solide`) : contour du dôme
(`marquage_contour` du modèle, T'2 3u, RF-MQ-GIR-02 : cercle à `Ri + retrait + l/2`, motif fermé à période ajustée [G]) ;
lignes de l'anneau (limites du profil d'anneau qui portent un marquage, RF-OSM-MRQ-021, RF-MQ-GIR-04 ; rive intérieure
décalée d'une demi-largeur vers l'anneau [G] ; lignes intérieures interrompues au droit des bouches, entre les points de
tangence des congés sur `R0` [G]) ; pièces de 2 m au plus (drapé).

## Commandes

```
hython recon/generateur/fabriquer_giratoires.py recon/generateur/scenes_giratoires/G1_giratoire_urbain_D40.yaml [--rendus] [--verifier-determinisme]
python recon/generateur/validation/controler_giratoires.py [<scene> …] [--json SORTIE]
python recon/generateur/validation/faire_rapport_giratoires.py [--constats …] [--determinisme "…"]
```

Exports : `<scene>/l5/giratoires.json` (anneau, branches, congés, faces des îlots, coupes radiales des dessus, entités,
BEV, marques), `l5/mesures_l5.json` (bords libres des îlots posés), `l5/manifest_l5.json` ; plus ceux des lots L1, L2,
L2b, L3 (le cœur du giratoire est un carrefour au sens de L3 : `l3/carrefours.json`, `l3/mesures_l3.json`).

## Limites

- Branches tracées vers le centre (extrémité « fin »), axe droit près de l'anneau ; anneau à une voie, centre unique.
- Trottoir de l'anneau : largeur interpolée entre les trottoirs des deux branches le long du coin (code L3) ; il n'est
  donc égal au trottoir du profil d'anneau que si les branches ont la même largeur (G1-G3 : oui).
- Chaussée annulaire : interpolation harmonique de `rg::carrefours_sol` (le dévers de 2,5 % du profil d'anneau n'est pas
  appliqué tel quel ; RF-GV-GIR-005 : 1,5-2 % vers l'extérieur).
- Lignes CÉDEZ : celles du modèle (droites, à la frontière de la branche) ; elles ne suivent pas le cercle de l'anneau.
- Îlots posés : le sol des branches et du cœur continue sous les îlots (caché) ; les hachures de l'enveloppe peinte sous
  l'îlot restent peintes (cachées) ; `marquage_contour` des îlots séparateurs non peint (l'enveloppe hachurée du profil
  en tient lieu).
