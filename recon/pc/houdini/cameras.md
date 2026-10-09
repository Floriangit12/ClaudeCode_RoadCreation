# Caméras de contrôle — `cameras.usda`

Couche USD à part (le paquet n'est pas modifié) : `over "World"` + `def Scope "Cameras"` + 4 caméras,
en Z vers le haut, mètres, `defaultPrim = World`. Comme elles sont sous `/World`, elles suivent la
rotation `ROTATION_SOLARIS` éventuelle. Pour s'en servir, empiler la couche **au-dessus** de
`recon/out/paquet_jardin/package/paquet_jardin_2026.usda` (Sublayer LOP, ou sous-couche d'une racine
de rendu). Elle est générée et contrôlée par :

```
hython recon/pc/houdini/generer_cameras.py      # option --controle-seul : contrôle sans réécrire
```

Repère local : O = Lambert-93 (917279.43, 6460289.98), NGF 216.30 m ; X est, Y nord, Z haut.
Centre du carrefour = barycentre de l'union des 14 liaisons de jonction OpenDRIVE
(`lanes_2026.geojson`, `jonction = true`) : local (-1.57, -5.09, 0.02), L93 (917277.86, 6460284.89),
NGF 216.32. La moyenne des 4 lignes d'effet des feux donne (-1.49, -4.65), soit 0,45 m d'écart.

| caméra | œil local (m) | œil L93 / NGF (m) | cible locale (m) | hauteur | focale / FOV | z sol local (prim USD) | dérivation |
|---|---|---|---|---|---|---|---|
| `cam1_ensemble_sud` | (-1.569, -100.089, 59.197) | 917277.86, 6460189.89 / 275.50 | centre du carrefour (-1.569, -5.089, 0.020) | 60 m au-dessus du sol | 34,58 mm, 55° | -0.803 (`Terrain/batiment`, emprise d'un bâtiment) | 95 m plein sud du centre, visée du centre, plongée 31,9° ; clipping 1 à 5000 m |
| `cam2_conducteur_verdun_so` | (-48.091, -61.200, 0.909) | 917231.34, 6460228.78 / 217.21 | (-16.795, -28.850, -0.188) | œil à 1,3 m | 23,46 mm, 75° | -0.391 (`Voirie/chaussee_2025`) | route 1 (Verdun SO, sens NE entrante), voie de droite (-2), 0,4 m à gauche du centre de voie, 45 m avant la ligne d'effet des feux ; visée de la même voie à la ligne de feux (azimut 44,1°), plongée 2,5° |
| `cam3_pieton_traversee_so` | (-11.677, -27.463, 1.631) | 917267.75, 6460262.52 / 217.93 | extrémité NO du zébra (-23.144, -16.232, -0.102) | œil à 1,6 m | 25,71 mm, 70° | 0.031 (`Voirie/trottoir_2025`) | trottoir SE, 0,6 m derrière la bordure, dans l'axe de la nouvelle traversée ; regard vers le NO (azimut 314,4°) à travers les 2 zébras et le refuge, plongée 5° |
| `cam4_conducteur_vercors` | (22.568, -56.315, 0.158) | 917302.00, 6460233.67 / 216.46 | (8.241, -18.913, -0.275) | œil à 1,3 m | 23,46 mm, 75° | -1.142 (`Voirie/chaussee_2025`) | route 6 (Vercors), voie entrante 1 (seule voie entrante à cet endroit), 0,4 m à gauche du centre de voie, 40 m avant la ligne d'effet des feux ; visée de la ligne de feux (azimut 339,0°), plongée 2,5° |

Commun : ouverture carrée 36 × 36 (rendus 1000 × 1000, hFOV = vFOV), `fStop = 0` (pas de profondeur
de champ), projection perspective, clipping de 0,05 à 5000 m pour les caméras au sol. Chaque caméra
porte un `doc` en français et un `customData` : position locale et L93/NGF, cible, z du sol et
prim source, z de la heightmap, hFOV, azimut (depuis le nord), plongée. Transformation : une seule `xformOp:transform`,
matrice « regarder vers » (axe -Z local = visée, +Y local = haut, haut du monde = +Z).

## Choix de la nouvelle traversée SO (cam3)
Ce sont les bandes `passage_pieton_bande` de `verdun_sw`, groupe `passage_pieton`, `etat = neuf_2025`
(MQ0863 à MQ0868 sur la chaussée sens SO, MQ0869 à MQ0874 sur la chaussée sens NE), au contact de
la ligne d'effet des feux SO. Le refuge central est la surface `ilot` surf_0339 (modifiée 2025).
L'ancien zébra effacé est noté `fantome_ancien_passage_pieton_SW`, 8,8 m plus près du carrefour
(constats : « zébra −18,6 → −27,4 »). Le long de l'axe, en partant du NO : trottoir, puis chaussée
sur 6,4 m, puis refuge sur 2,4 m, puis chaussée sur 6,6 m, puis trottoir SE. Les feux piétons R12
du refuge (`feu_SW_TPC`) et de l'extrémité NO (`feu_SW_NO_pietons`, azimut 135°) font face à la
caméra.

## Contrôles (sortie de `generer_cameras.py`)
- **Scène composée** (paquet + `cameras.usda` en sous-couche de session) : les 4 caméras existent.
  En repassant l'axe -Z local dans la matrice monde, on retrouve la visée prévue à 1e-6 près ;
  le hFOV mesuré par `Gf.Camera` est bien 55, 75, 70 et 75°. `usdchecker cameras.usda` : Success.
- **Surface sous la caméra** (`surfaces_2026.geojson`) : cam2 et cam4 sur `chaussee`, cam3 sur
  `trottoir`, cam1 au-dessus d'une emprise `batiment`, à 60 m de haut.
- **Visée** : écart avec le centre du carrefour de 0,0° (cam1), 4,7° (cam2) et 4,9° (cam4).
  Pour cam3, l'écart avec l'extrémité NO de la traversée est de 1,2°. Le centre du carrefour est
  à 69,7° : il est hors champ, et c'est voulu, car la caméra regarde à travers la traversée.
- **Dégagement** : aucune instance (mobilier, feux, végétation), aucun bâtiment ni aucune clôture
  à moins de 2 m devant l'objectif. Le contrôle échantillonne le champ par 20 × 21 × 21 points
  (de 0,05 à 2 m) dans les boîtes orientées des instances. Instance la plus proche dans le champ :
  arbre à 67,6 m (cam1), mobilier publicitaire à 8,8 m (cam2), tête R12 du refuge à 8,6 m (cam3),
  armoire à 24,4 m (cam4).
- **Sol** : la heightmap 10 cm donne le même résultat à 0,2 cm près pour cam1, cam2 et cam4. Pour
  cam3, l'écart est de 8,3 cm : le maillage `trottoir_2025` est à +0,03 m avec une bordure de
  15 à 17 cm au bord du zébra, alors que la heightmap n'a qu'un ressaut de 6 cm (bordure abaissée).
  C'est le maillage USD rendu qui fait foi pour la hauteur de l'œil.
- **Aperçus husk** (Karma XPU, 400 × 400, hors dépôt) : ils sont conformes. cam1 cadre tout le
  carrefour et le départ des 4 branches ; cam2 et cam4 montrent la voie et le carrefour au point
  de fuite ; cam3 montre le zébra au premier plan, le refuge, le second zébra et les feux piétons.
