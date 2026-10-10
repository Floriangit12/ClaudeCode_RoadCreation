# recon/pcg/ue/materiaux : matériaux du sol V2 dans UE 5.8 (D:/ClaudeADAS)

Chaque `materiau_id` de `assets/specs/materiaux_sol.json` (34) a son `/Game/PJ/Materials/MI_<id>`, cible du
remappage USD (`info:unreal:sourceAsset`, CONTRAT_EXPORT.md § 5). S'y ajoutent les variantes `MI_<id>__citysample`
(10, textures City Sample, Unreal seulement), `MI_<id>__carla` (23, CC-BY 4.0) et la peinture `MI_PJ_Peinture_<blanc|jaune>_u<0|1|2|3|F>` (10).
Matériaux maison du pilote (ids hors spec, `pilote/ue/materiaux_maison.py`, dérivés de ces MI) : `MI_mortier_joint`,
`MI_mortier_clair`, `MI_bitume_pontage`, `MI_herbe_touffe` (M_PJ_Touffe), `MI_eclat_brf`, `MI_eclat_gravier` (M_PJ_Eclat),
`MI_PJ_Contexte`.

Revue UE du 10/10 (`catalogue.py`) :
- `RENDU_UE` : les surcharges de rendu de la revue de réalisme Karma (`assets/specs/materiaux_rendu_v2.json`) sont
  reportées, avec le même calcul que `pj_commun.materiau_rendu` (source, tuile, albédo = moyenne de la texture source x
  facteur ou albedo_cible / moyenne, x gain_rvb) : enrobé ancien 0,181/0,187/0,172 (0,26 avant), trottoir Asphalt015 à
  1,6 m 0,151/0,160/0,140, gazon 0,055/0,075/0,031, BRF (fond sous les copeaux) 0,061/0,049/0,040 à 1,6 m, concassé
  0,143/0,140/0,125 à 1,0 m, BEV en Concrete037 x 0,85 à 1,2 m ; étalonnage GBuffer refait (écart 0,0 %) ;
- `BETON_BORDURE_UE` : béton des bordures sur `concrete_rough_2x2` City Sample (moucheté fin, Unreal seulement) à 1,0 m,
  normale 0,25 (Concrete037 à 0,7 m = béton désactivé à gros granulats en gros plan) ; joints : `JointLargeurCm` 0,5 (1,2),
  `MI_mortier_joint` 0,28 (0,20) ;
- `ECLATS` + maître `M_PJ_Eclat` : couleur par éclat tirée par PerInstanceRandom dans la palette de
  `recon/pcg/houdini/pj_ilot.py` (BRF : bois frais roux 48 %, écorce 40 %, grisé 12 % ; concassé : gris foncé 55 %, gris 32 %,
  clair 13 %), détail de luminance de la texture du lit, fibres du bois (bruit étiré), normale ; remplace `M_PJ_Bordure` à
  tuile de 30 m (une tache de texture par éclat : copeaux bleutés ou blancs, BRF presque noir à 10 m) ;
- maître `M_PJ_Touffe` (feuillage deux faces, transmission ; pied sombre, 12 % de touffes sèches à albédo <= 0,21).

```
python recon/pcg/ue/materiaux/materiaux.py tout          # éditeur ouvert ; ~4 min ; ou étape par étape :
  preparer   hauteurs, bruit, masque, mesures (hors éditeur)  -> mesures_textures.json, data/raw/assets_src/cc0_derive/
             + maillages d'essai USD (generer_meshes.py)      -> recon/out/paquet_jardin/v2/ue_materiaux/usd/
  construire textures, maîtres, MI (construire_materiaux.py, rejouable, graphes reconstruits nœud par nœud)
  niveau     /Game/PJ/Maps/PJ_Materiaux (t1_niveau.py + import USD + niveau_materiaux.py)
  mesurer    albédo moyen de chaque MI (mesurer_albedo.py)    -> ue_materiaux/albedo.json
  etalonner  facteur = cible / mesure, cumulé                 -> etalonnage.json, MI reconstruits, remesure
  essai_cd   bordures posées par PCG avec données d'instance  -> ue_materiaux/essai_bordures_cd.json
  captures   vues à 1,60 m (photos utilisateur 1 à 3), dessus  -> ue_materiaux/vues/
```

| Fichier | Rôle |
|---|---|
| `catalogue.py` | source unique : maître par id, réglages (famille, id), sources UE remplacées, variantes CARLA et City Sample, recette de peinture, calage de l'albédo |
| `preparer_textures.py` | moyennes linéaires des textures ; hauteurs 16 bits : `Displacement` des zips ambientCG du cache, sinon intégration des normales (Frankot-Chellappa, passe-haut ; validée sur WoodChips003 : corrélation 0,85 en hautes fréquences) ; bruit macro (graine 2154) ; masque d'usure de peinture (peinture.json, graine 1967) |
| `generer_meshes.py` | plaques (UV `st` en mètres, pas de 5 cm pour le déplacement) et éléments de bordure T2 0,994 m (profil `pose_exemple` de bordures.json, chanfreins de 3 mm aux abouts, onglets à 45°) ; USDA conformes au contrat (vérifiés par `contrat/verifier_usd.py`) |
| `construire_materiaux.py` | import des textures, 4 maîtres, 77 MI |
| `niveau_materiaux.py`, `mesurer_albedo.py`, `essai_bordures_cd.py` | scripts éditeur du niveau d'essai, de la mesure, de l'essai PCG |
| `mesures_textures.json`, `etalonnage.json` | mesures hors éditeur et facteurs d'étalonnage (versionnés) |

## Textures (`/Game/PJ/Textures/{CC0/<dossier>, CitySample, PJ}`)
146 textures : albédo `Default` sRGB ; normales `Normalmap` + Flip Green Channel (sources OpenGL, City Sample
comprise) ; rugosité et AO `Masks` linéaires ; hauteur `Grayscale` 16 bits linéaire ; bruit `Masks` ; masque de
peinture `VectorDisplacementmap` (RGBA 8 bits exact, seuils de peinture.json). Virtual texturing désactivé.

## Maîtres (`/Game/PJ/Materials/Maitres`, attributs de matériau, Substrate converti, 2 échantillonneurs partagés)
- **M_PJ_Sol** : UV0 = `st` en mètres / `TileM` (repli `UV_Monde` : position monde XY) ; anti-répétition (second
  échantillonnage tourné de 37° et mis à l'échelle `EchelleB`, normale ramenée dans le repère, mélange par bruit
  lent, `AntiRepetition`) ; variation macro de luminance à deux échelles (`MacroForce`, `MacroEchelleM`) ;
  `Contraste` autour de `MoyenneTexture` ; `Teinte`, `Luminosite`, `RugositeMul`/`RugositeAjout`, `NormalForce`,
  `AOForce`, `Salissure` (plaques, concentrée dans les creux, `TeinteSalissure`) ; `CouleurSommet` (désactivé par
  défaut) : R usure, G salissure, B graine.
- **M_PJ_Remplissage** : M_PJ_Sol + déplacement **Nanite (tessellation)** : `Enable Tessellation`, sortie
  Displacement, `Displacement Scaling` 10 cm / centre 0,5 ; `DeplacementCm` (crête à crête : BRF 2,5, BRF gris 3,5,
  gravier 2,5, gravillons 1,8, galets 2,5), `HauteurCentre` = moyenne de la carte ; `HauteurCanalA` (hauteur dans
  l'alpha de l'albédo, textures CARLA `_dh`). Switch statique `Melange` (catalogue.MELANGE) : second lit
  (`T_*2`, `TileM2`, `Contraste2`, `HauteurCentre2`) mêlé par un bruit lent uniforme (`MelangeTaux` = part de surface,
  `MelangeEchelleM`, `MelangeTransition`) décalé par la hauteur du lit 2 (`MelangeHauteur`) ; albédo, normale,
  rugosité et hauteur mêlés ; `Teinte` ne teinte que le lit 1, le lit 2 vaut `Luminosite` × `Melange2Rapport` × sa
  texture (calage_melange : lit 2 à sa couleur propre × gain, lit 1 complète la cible du lit vu). En 5.8, `r.Nanite.Tessellation=1` par défaut (`r.Nanite.AllowTessellation`
  n'existe plus) ; le maillage doit être Nanite (`import_usd(..., nanite=True)`).
- **M_PJ_Bordure** : aléa par élément (PerInstanceRandom + hachage de la position de l'objet) : décalage d'UV,
  teinte ±`VariationTeinte` (4 %) ; données d'instance `PerInstanceCustomData` 0-6 =
  `cd = [usure, salissure, mousse_joints, herbe_joints, teinte, z_pied_cm, demi_longueur_cm]` (bordures_elements.json,
  `pilote/points_ue.py` ; absent = -9 -> valeur du MI) ; `teinte` (cd4) est le gain par élément des points
  (0,88-1,12), à défaut ±`VariationTeinte` aléatoire ; salissure ×(1 − 0,35·s·w), w = 1 au pied (z local entre le fil
  d'eau et `BasHauteurCm` au-dessus) et `SalissureHaut` sur la tête ; fil d'eau = cd5 (pivot des prototypes Houdini
  sous le bloc : z_pied = H − vue), à défaut `BasDecalageCm` (pivot au fil d'eau) ; abouts plus sales et `Mousse` à
  moins de `JointLargeurCm` des abouts : distance = cd6 − |x| (pivot au milieu de l'élément), à défaut bornes
  `ObjectLocalBounds` (exactes pour un acteur isolé seulement : sur un ISM ce sont celles du composant, d'où une mousse
  et une salissure sur toute la face des pièces uniques, constaté sur les pièces courbes du pilote).
- **M_PJ_Peinture** (masqué) : recette de peinture.json (score RGA du masque, seuils, faïençage, salissure,
  transparence vers le grain de l'enrobé, décoloration `Chroma`, normale de l'enrobé atténuée) ; les manques laissent
  voir l'enrobé réel sous la marque (+3 mm).

## Étalonnage de l'albédo
Calage analytique (Luminosite = Y(cible)/Y(moyenne texture), Teinte = chromie), puis mesure dans UE : capture
« base color » du GBuffer (SceneCapture2D orthographique, 1,6 × 1,6 m centraux de chaque plaque ; contrôle :
gris 0,18 lu 0,1816) et facteur cumulé `cible / mesure`. Bordures : la plaque plate (z local = 0) porte la salissure
du pied ; la mesure est ramenée à la tête (s × SalissureHaut). Résultat (albedo.json) : 34 MI CC0 et 10 City Sample
à moins de 1,1 % en luminance et 2,2 % par canal. CARLA : luminance seule (aspect CARLA conservé, facteur ≤ 8).

## Choix visuels (captures comparées aux photos utilisateur et aux tuiles Panoramax)
- Bordures : Concrete037 (béton à gros granulats roulés) resserré (`TileM` 0,7), `Contraste` 0,6, normale 0,55
  -> béton fin de bordure préfabriquée ; granit : moucheté de Concrete037 à 0,4 m (PavingStones119 dessinait des pavés).
- Trottoir : grain d'Asphalt031 à 1,3 m (tarred_gravel = brai lisse à paillettes blanches).
- BRF (revue UE du 10/10) : cible relevée à 0,138/0,120/0,108 (lit vu, photo 2 ; l'ancienne, 0,062/0,047/0,038, rendait
  le lit 3 à 4 fois trop sombre), tuile 4,0 m (copeaux allongés de 3 à 8 cm), `Contraste` 1,4, 20 % de BRF gris
  (WoodChips001 à 0,7 × sa couleur, tuile 2,8 m) par bruit de 2 m, déplacement 2,5 cm (4 cm étirait la texture sur les
  flancs), îlots 3 cm sous les bordures au pourtour et bombés de 1,5 cm. Rendu (v2) : BRF / enrobé 0,44 (photo 2 : 0,50),
  R/G 1,16 (1,22). Gravier : tuile 3,6 m (~2 cm, photo 3), 1,35.
  Ces tuiles (et les sources remplacées) ne valent que pour UE : à reporter dans materiaux_sol.json si validées.
- Éclairage et exposition : référence `pj_tools/eclairage.py` (EV100 14, soleil 128 klux hors atmosphère, Mie 0,12,
  post-process neutre), appliquée par `tests_phase0/ue/t1_niveau.py` ; plus de doublons `_ev13`.

## Points faibles connus
- MI CARLA de bordure et de caniveau (MI_dirtyCurb, largeM_curb, dirtyGutter) : atlas dépliés pour les maillages
  CARLA, rayures sur des UV en mètres ; MI_Brick05 rouge pour paves_granit ; échelle UV CARLA non recalée.
- Hauteurs des textures Poly Haven (gravier concassé, galets) intégrées depuis les normales : relief approché.
- Ombres : gris-bleu depuis la correction du ciel (pied de bordure / enrobé au soleil 0,25 sur v2, contre 0,11) ; reste
  bleuté (B/G 1,3). Joints de 6 mm : bouchons de mortier des prototypes Houdini posés par PG_Bordures (pilote,
  `MI_mortier_joint` 0,20 en retrait de 4 mm, `MI_mortier_clair` 0,30 à fleur) ; les maquettes `generer_meshes.py` du
  niveau d'essai n'en ont toujours pas.
- Cibles d'albédo UE = materiaux_sol.json + surcharges de rendu Karma (`RENDU_UE`, revue UE du 10/10) ; les autres
  materiau_id gardent la spec (pas de surcharge Karma).
