# recon/pcg/houdini : fabrication v2 déterministe (hython Houdini 22.0.459 Indie)

« Claude décrit, Houdini fabrique, UE 5.8 place ». Ce dossier lit la description vectorielle
(`recon/out/paquet_jardin/v2/description`, schéma `description_scene_v2/0.1`) et les specs
(`assets/specs/bordures.json`, `bordures_elements.json`, `materiaux_sol.json`, et les surcharges de
rendu `materiaux_rendu_v2.json`). Il fabrique ensuite la géométrie de la zone pilote ZP-01 par des
verbes SOP Houdini appelés depuis Python, sans HDA ni interface. Chaque valeur vient d'un attribut de
la description ou d'une règle nommée. Aucune géométrie n'est tirée d'un raster, et aucun Z ne vient
des maillages v1.

## Commandes

Depuis la racine du dépôt :

```
hython recon/pcg/houdini/fabriquer.py                          # tout (≈ 90 s), dans recon/out/paquet_jardin/v2/fabrique
hython recon/pcg/houdini/fabriquer.py --verifier-determinisme  # + 2e exécution complète, comparaison sha256, résultat dans le manifeste
hython recon/pcg/houdini/fabriquer.py --strict                 # code de sortie 3 si un critère chiffré de la phase 1 échoue
hython recon/pcg/houdini/fabriquer.py --sortie DOSSIER --sans-cameras --comparer AUTRE/manifest_fabrication.json
hython recon/pcg/houdini/rendre_pilote.py                      # 6 vues Karma XPU -> recon/pc/rendus/v2_pilote (≈ 1 min par vue)
hython recon/pcg/houdini/rendre_pilote.py --vues d_ilot_brf --sur 1 --dossier DOSSIER   # essai rapide
```

`hython` se trouve dans `C:/Program Files/Side Effects Software/Houdini 22.0.459/bin`. Lancer avec
`PYTHONDONTWRITEBYTECODE=1` pour ne pas laisser de `__pycache__`.

`rendre_pilote.py` rend chaque vue en EXR linéaire à 2 x la résolution (husk, Karma XPU,
`KARMA_XPU_DISABLE_MIPMAPS=1` : aucun `.rat` à côté des textures), applique l'exposition de la vue, une
courbe d'épaule douce et l'encodage sRGB, réduit à 1000 x 1000 (lanczos3) et écrit le PNG. Le harnais
v1 `recon/pc/houdini/rendre_controle.py` fonctionne toujours sur `rendu_pilote.usda`, mais sans
exposition ni épaule.

## Modules

| Module | Rôle |
|---|---|
| `fabriquer.py` | CLI : enchaîne les étapes, écrit `manifest_fabrication.json` (hashes des entrées, des scripts et des sorties ; comptes ; contrôles mesurés sur la géométrie posée ; critères de la phase 1 ; déterminisme) |
| `pj_commun.py` | Chemins, graines `sha256(id \| pj_fabrique/0.1)`, specs (dont surcharges de rendu), description en repère local (`decrire/commun.py: repere`, seule conversion), MNT 2026, lissage des faces vues |
| `pj_bordure_pose.py` | Pose des éléments et des caniveaux le long des bordures, joints, points `pj_points/0.1`, `bordures.usda` |
| `pj_bordure_prototypes.py` | Prototypes d'éléments : balayage du contour, PolyBevel, Boolean (épaufrures), Normal, Divide |
| `pj_limites.py` | Régularisation topologique des limites de surfaces d'origine raster (arcs partagés) |
| `pj_sol.py` | Sol découpé sous les bordures (Triangulate 2D), classes, Z (MNT, bordures, rampes, décaissés, îlots), matériaux, contrôles |
| `pj_ilot.py` | Couverture 3D des remplissages (copeaux, gravillons ; Shrinkwrap), éclats épars, `ilots.usda`, `ilots_couverture.usdc`, `points/ilots_epars.json`, `zones/ilots.json` |
| `pj_decals.py` | Rubans drapés (pontages, joint de reprise, zébras provisoires) ; touffes d'herbe et dalles podotactiles 3D |
| `pj_materiaux.py` | `materiaux_v2.usda` : MaterialX (Karma) + UsdPreviewSurface, textures CC0, matériaux maison |
| `pj_contexte.py` | Masque du paquet v1 dans l'emprise pilote, instances v1 réassises sur le sol v2 (couche de surcharge, paquet intact) |
| `pj_controles.py` | Contrôles de conformité sur la géométrie posée (fidélité Z et plan, interstices denses, rampes marchables, faces arrière, remplissages, vues des traversées) |
| `pj_rendu.py` | Caméras `recon/pc/houdini/cameras_v2_pilote.usda`, ciel procédural, décor de rendu, racine `rendu_pilote.usda` |
| `rendre_pilote.py` | Rendus Karma XPU des 6 vues (EXR -> exposition -> épaule -> PNG) |
| `pj_usd.py` | Écriture USD déterministe (couches en mémoire exportées) |

## Sorties (`recon/out/paquet_jardin/v2/fabrique/`)

```
prototypes/<nom>.usda, prototypes/courbes/<nom>.usda, prototypes/eclats/<nom>.usda, prototypes/index.json
points/bordures.json          éléments, caniveaux et bouchons de joint (pj_points/0.1)
points/ilots_epars.json       éclats épars (débordement sur la chaussée, tête de bordure) (pj_points/0.1)
zones/ilots.json              polygones, remplissage et densités de couverture (PG_Ilots)
bordures.usda                 PointInstancers (béton gris, béton clair, caniveaux, joints sombres et clairs)
sol.usda                      un maillage par materiau_id (UV st1 en m, primvar salissure, unrealMaterial)
ilots.usda                    PointInstancers des éclats épars
ilots_couverture.usdc         couverture dense des remplissages et des massifs de BRF (binaire)
decals_sol.usda               pontages de fissures et joint de reprise (rubans à +1,5 mm), touffes d'herbe 3D, dalles podotactiles 3D
marquages_pilote.usda         zébras provisoires (rubans à +2 mm ; phase 2 : pj_marquages)
materiaux_v2.usda             matériaux /World/Looks_v2/<materiau_id>
ciel/ciel_clair.hdr           ciel clair procédural (latlong, Radiance) du dôme de rendu
contexte/masque_v1_pilote.usdc  surcharge du v1 (voir plus bas)
contexte/decor_rendu.usda     arbres v1 masqués, matériaux CC0 de décor (bâtiments, toits, espaces verts v1) pour les rendus de contrôle
rendu_pilote.usda             racine Karma : caméras + couches v2 + masque + décor + recon/pc/houdini/rendu_controle.usda
manifest_fabrication.json
```

Les chemins d'assets dans les USD sont relatifs à `fabrique/`, quel que soit `--sortie` : deux
exécutions donnent des fichiers identiques à l'octet.

## Conventions

- **Repère** : local = L93 − O (917279.43, 6460289.98), z = NGF − 216,30 ; mètres, Z haut.
- **Prototype de bordure** : X = s (le long de la bordure), Y = u (0 = face vue, + vers l'arrière,
  c'est-à-dire le côté haut), Z = v (0 = dessous du bloc). Pivot au milieu de l'élément, sur la face
  vue, sous le bloc. Chartières et raccords : pivot sous le bloc du profil haut, le profil bas posé au
  même fil d'eau. Pièces courbes : origine au milieu de la corde. Caniveaux : même repère que la
  bordure longée (u de −largeur à 0). Côté UE : X = 100 s, Y = −100 u, Z = 100 v.
- **Éclats** : taille unitaire, origine au centre de la boîte englobante.
- **Points** :
  - format `{id, asset, p, rpy_deg, s, graine, cd, x}` ;
  - `rpy_deg = [r, p, y]` en ZYX intrinsèques, R = Rz(y)·Ry(p)·Rx(r), p > 0 abaisse l'avant ;
    c'est la convention de `recon/pcg/ue/pj_tools/pj_tools/repere.py`, et côté UE
    `Rotator(roll = r, pitch = −p, yaw = −y)` ;
  - `s[0]` des éléments = longueur posée / longueur du prototype (coupes 0,80-1,00, pente 1/cos) ;
    `s[0]` des joints = largeur réelle du joint (bouchon de 10 mm mis à l'échelle) ;
  - `cd` des bordures et caniveaux : `[usure, salissure, mousse_joints, herbe_joints, teinte]`, et
    `x.couleur` = gain RVB de dérive de teinte ; joints : `x.mortier` (sombre en retrait, clair à fleur) ;
  - `x` : données de traçabilité (bordure, s0/s1, profil, vue, type, coupe, variante, matériau).
- **Caméras** : focale et ouverture en dixièmes d'unité de scène (convention USD : 0,36 = 36 mm), pour
  une profondeur de champ juste sous Karma.
- **Matériaux** : chaque maillage porte `primvars:materiau_id` et
  `unrealMaterial = /Game/PJ/Materials/MI_<id>.MI_<id>`. Aucun contenu City Sample côté Houdini ou Karma.

## Règles de fabrication

**Faces vues** (`pj_commun.Bordure`)
- Tracé levé : tous les sommets GAM (filtre des zigzags < 5 cm). Les grappes de sommets aux nez sont
  fusionnées (Douglas-Peucker 15 mm) pour la seule détection des coins ; les cordes longues que laisse
  ce Douglas-Peucker sont jalonnées (sur la corde tous les 0,5 m si le levé y est droit à 6 mm près,
  sinon par les sommets levés) : la spline ne bombe plus entre deux sommets éloignés (revue r2 : 13 à
  22 cm sur K-0369, K-0353).
- Lissage : Catmull-Rom centripète par ces points, coins de plus de 40° gardés vifs.
- Les coins convexes de plus de 45° deviennent des nez arrondis :
  - rayon de nez de l'îlot décrit (`ilots.nez.rayon_m`, ≥ 0,25) pour une bordure de ceinture, sinon
    R 0,5 pour T et A, R 0,25 pour P, TU et I ;
  - pointe effilée de plus de 120° : R 0,20 au plus, et assez petit pour que le sommet du nez ne
    recule pas de plus de 0,30 m (la pointe décrite garde sa longueur) ;
  - le rayon est réduit si les côtés sont courts.
- Un repli aller-retour (plus de 150°, à moins de 0,25 m) est réduit à une seule partie.
- Profil en long : fil d'eau décrit interpolé sur TOUS les sommets levés (revue r2 : le Douglas-Peucker
  plan perdait le profil, K-0341 posée 26 cm trop haut), puis lissage gaussien (σ 0,5 m, périodique sur
  un anneau) borné à ±3,5 mm du décrit : les coudes du MNT n'ouvrent plus les joints en coin vertical.
- Les abscisses de la description sont reportées par les sommets d'origine.

**Pose** (`pj_bordure_pose`)
- Éléments de 0,994 m au pas de 1,00, centrés dans leur case. Largeur de joint tirée par joint :
  5,5-7 mm (bordure neuve), 5-8 mm log-normale centrée sur 6,5 mm (ancienne).
- Pas : le plus long de 1,00 / 0,50 dont la flèche de corde reste ≤ 10,5 mm, le coin de joint en plan
  (base x déviation des tangentes) ≤ 6 mm et le coin vertical (H x changement de pente) ≤ 4 mm ; sinon
  pièce courbe sur mesure (abouts radiaux, arc ≤ 1 m et ≤ un quart de cercle, déviation mesurée) ;
  hystérésis à 60 % des seuils.
- Joints (revue r2 : jusqu'à 21 mm d'un côté et −8 mm de l'autre sur les courbes) :
  - entre deux éléments droits, joint centré à mi-base et mi-hauteur (déviation en plan, lacet de jitter
    et changement de pente compris), largeur tirée ramenée pour que les 4 coins restent dans 3,5-9,5 mm ;
  - coude du levé (coin > 6 mm) : l'élément dont la corde s'écarte le plus de la face devient une pièce
    sur mesure ; une pièce sur mesure prend la normale d'about de sa voisine droite (bissectrice si les
    deux sont sur mesure) : abouts parallèles ; angle vif : onglet des deux côtés ;
  - bouchon de mortier orienté sur la normale du joint, à la largeur du joint à mi-base.
- Chartières et raccords de profil (description : chartière dès 1 cm d'écart de vue) : loft du profil
  haut à sa vue vers le profil de l'intervalle voisin à l'extrémité basse ; sur une courbe ou un coude,
  le loft suit la face (pièce sur mesure).
- Points durs, par priorité décroissante : abaissé, angle vif, profil, extrémité. Une coupe de zone
  n'est jamais un point de départ.
- Coupe en fin de file, d'au moins 0,20 m. Une file multiple du pas à ±1 % est posée sans coupe.
- Le prototype et son échelle X sont choisis avant la pose ; sur une pente, échelle x 1/cos(pente).
- Caniveaux (`caniveau` de la description, CS2 : 25 x 11/13,5) : éléments alignés sur ceux de la
  bordure, devant la face, dessous = fil d'eau − 0,11 ; pièces courbes dès 2 mm de flèche ou devant une
  pièce sur mesure ; la chaussée s'arrête à leur bord, à fil d'eau + 2,5 cm.
- Z : dessous du bloc = fil d'eau au milieu de la CORDE + vue − H. Le tangage suit la corde.
- Jitter (`bordures_elements.json`) : hauteur ±2 mm (±3 mm sur une bordure ancienne), dont une part
  corrélée sur 3-5 m ; lacet ±0,3° (±0,5° ancienne), latéral ±1 mm, roulis ±0,15° ; ni hauteur ni
  roulis sur les bateaux et les chartières ; la variation de longueur est portée par les joints.
- Épaufrures v0-v3 selon l'âge. Teinte par élément 0,94-1,06 (neuve) ou 0,88-1,12 (ancienne), dérive
  chaude / froide, décalage d'UV par élément ; primvars `salissure`, `mousse_joints`, `demi_longueur`.

**Limites de surfaces** (`pj_limites`, la description n'est pas modifiée)
- Les anneaux sont découpés en arcs aux nœuds de la partition ; un arc partagé n'est traité qu'une fois.
- Par arc : dents supprimées, calage sur la face vue d'une bordure parallèle proche, Douglas-Peucker
  0,20 m (0,35 m pour une limite d'espace vert ou de massif), dents de 0,3 à 1 m retirées, Chaikin x 2.
- Limite chaussée neuve 2025 / ancienne : segments droits (reprise sciée), pontée sur toute sa longueur.
- Près d'une bordure (0,35 m), la classe d'un triangle vient de l'étiquette du côté, lissée le long de
  la bordure ; gazon côté chaussée d'une bordure de chaussée (vue ≥ 6 cm, à moins de 2 m) : revêtement
  de chaussée sondé plus loin du même côté.

**Sol** (`pj_sol`)
- Bande occupée par la bordure : de la face au niveau de la chaussée + 12 mm jusqu'à base − 12 mm. Le sol
  passe sous l'élément.
- Triangulation contrainte : bandes, lignes à 0,15 m de part et d'autre des bandes, limites
  régularisées (hors 0,30 m autour des bordures), contour des modules BEV, cadre. Raffinage ≤ 0,25 m²,
  angle ≥ 22°.
- Classe par triangle : îlot (polygone décrit ou intérieur de la ceinture fermée, côté haut de toutes
  les bordures de ceinture à moins de 2 m), BEV (modules entiers), puis surface.
- Z = MNT 2026, avec ces corrections :
  - surfaces à araser : plan ajusté autour ; chaussées : ouverture morphologique de 1,3 m ;
  - rampes derrière les bateaux (vue ≤ 0,04 ; revue r2) : rampe PLANE depuis la tête − 4 mm sur la
    profondeur marchable (arrêt à 0,25 m d'une autre bordure, au premier revêtement non marchable ou à
    4 m) : vers le niveau de la bordure qui arrête la rangée (≤ 4 %) ou pente moyenne du MNT (≤ 3,5 %) ;
    elle prime sur les corrections des autres bordures (plus de S à 8-10 % entre deux bordures) ;
  - côté chaussée d'une bordure : fil d'eau (ou bord du caniveau) sur 0,30 m, puis raccord ;
  - côté haut : dessus − 4 mm et dévers de 1,5 % (derrière un bateau : la rampe), raccord sur 30 x
    l'écart au MNT (0,6 à 4 m) ; pondération 1/d² entre bordures voisines ;
  - bornes : chaussée entre fil d'eau − 5 mm et tête − (vue − 5 mm) à moins de 0,15 m devant (vue réelle
    = vue décrite ± 5 mm), sol ≤ tête − 2 mm + 3,5 % à moins de 0,20 m derrière ;
  - massifs de BRF, gravier, paillage hors îlots : décaissés de 4 / 3 cm, talus dans le massif ;
  - îlots : tête de ceinture (pondération 1/d⁴) − retrait + bombement, borné à 3-5 cm sous la tête
    locale de chaque bordure de ceinture.
- Modules BEV (`modules_bev`) : modules entiers de 0,40 alignés sur l'abaissé, gardés si leurs 4 coins
  sont dans le contour décrit ; plus de fragment rogné.

**Îlots et massifs** (`pj_ilot`)
- Couverture dense : copeaux de 15 à 60 mm (5 % de copeaux longs de 80-120 mm, 15 % dressés à 50-70°),
  2 500 /m² sur 0,25 m de bord, 1 800 /m² à l'intérieur, 1 500 /m² sur les massifs ; couleurs : bois
  frais roux (48 %), écorce brun sombre (40 %), grisé chaud (12 %) ; concassé anguleux 10/20 des îlots
  du Vercors (Panoramax 2025-01-12) de 12 à 26 mm, 4 200 /m² à moins de 1,2 m de la ceinture, 3 000 /m²
  à l'intérieur, gris foncé majoritaire.
- Chaque éclat dépasse de 40 à 70 % de sa hauteur (calculée sur le prototype tourné).
- Débordement sur la chaussée devant la ceinture (altitude sur le maillage fabriqué ; hors sol :
  écarté) et quelques éclats sur la tête des éléments posés.

**Détails** (`pj_decals`)
- Pontages de fissures sur l'enrobé ancien : motif d'entretien (rive à 0,8-1,0 m de la face, bande de
  roulement intérieure, joint de voie ; transversales tous les 6 à 15 m), tronçons de 1,5 à 8 m, rubans
  de 4-8 cm à bavures, 0,10 m/m² ; joint de reprise neuf / ancien ponté.
- Touffes d'herbe 3D : joints des bordures anciennes (`herbe_joints`), limites gazon / revêtement dur.
- Dalles podotactiles 3D : 60 plots en calotte (Ø 25 mm, 5 mm, quinconce au pas de 50 mm) par module,
  dessus à +0,8 mm du sol, plan ajusté à leurs 4 coins, jamais enterrées.
- Zébras provisoires : bandes `passage_pieton_bande` du paquet v1 recalées en rectangles exacts (0,50 m),
  drapées à +2 mm. À remplacer par `pj_marquages` (phase 2).

**Contexte v1** (`pj_contexte`)
- Le paquet v1 n'est jamais modifié.
- Dans l'emprise pilote, les faces v1 du sol, des bordures, des marquages et des clôtures deviennent
  dégénérées ; les faces coupées par le bord sont recréées hors emprise.
- Le Z du sol v1 est fondu vers le sol v2 sur 3 m.
- Mobilier et végétation v1 de l'emprise (+ 3 m) posés au sol : posés sur leur appui v2 (max du sol et
  des têtes de bordure sous l'empreinte) ; têtes de feux et panneaux : suivent leur mât.
- Rendus de contrôle : arbres v1 masqués ; bâtiments sur un enduit CC0 d'albédo 0,47 légèrement chaud,
  toits et espaces verts v1 sur des matériaux CC0 en projection triplanaire (`contexte/decor_rendu.usda`).

**Matériaux** (`pj_materiaux`, `assets/specs/materiaux_rendu_v2.json`)
- Béton de bordure : Concrete037 à tuile 1,2 m, sans normale de texture ni AO (crépi sinon ; Karma XPU
  n'applique pas `strength` de ND_hextilednormalmap), rugosité ≥ 0,6, moucheté d'agrégats fins (cellnoise
  700 /m) ; vieillissement piloté par l'aspect décrit : assombrissement (1 − 0,3·salissure), crasse en
  dégradé sur la face, lichens sur la tête, mousse aux abouts.
- Peinture : macrotexture de l'enrobé à travers le film, usure qui fait réapparaître l'enrobé (6-8 %).
- Gazon désaturé (≈ 0,055 / 0,075 / 0,032), BRF à 0,05, concassé à 0,14 légèrement chaud, BEV en béton
  x 0,85, fondu hexagonal 0,12.

**Rendu** (`pj_rendu`, `rendre_pilote.py`)
- Ciel clair procédural (zénith désaturé 0,30 / 0,42 / 0,70), rapport d'éclairement horizontal
  soleil / ciel de 3,5:1 ; soleil à l'azimut 220° et 29° de hauteur (10 octobre, 45,2° N), exposition 2.
- Balance des blancs : gains calculés sur une carte grise horizontale (soleil + ciel) pour un blanc
  légèrement chaud (B/R 0,94), appliqués au développement ; exposition commune +0,65 EV.
- 128 chemins par pixel, rendu à 2 x la résolution, profondeur de champ f/8 sur les vues rapprochées ;
  vue b abaissée de 5°.

## Contrôles (manifest_fabrication.json)

- `controles.pose_reelle` : joints aux 4 coins de chaque about (abouts transformés par la pose réelle) et
  marches de tête ; tête − sol devant et derrière ; retraits des massifs ; recouvrements de bandes ; pas
  alternés ; longueurs posées des ceintures d'îlots.
- `controles.conformite` (`pj_controles`) : fil d'eau posé − décrit par élément ; écart en plan face
  posée − tracé levé (nez exclus) et écart de lissage par bordure ; interstices denses (sondes tous les
  2 cm à 3 mm devant et derrière chaque face) ; rampes sur profils marchables (pente sur 0,25 m) ; faces
  arrière à nu ; retraits des remplissages à 3, 6 et 10 cm du dos de la ceinture ; vue réelle des
  éléments de bateau de traversée.
- `controles.bordures`, `controles.sol` : contrôles de planification (joints, coupes, flèches, rampes
  sur triangles, dévers, retraits, écart au MNT par classe, limites régularisées).
- `controles.masque_v1.reassis_controle` : base des instances v1 posées au sol − appui v2.
- `phase1` : critères chiffrés de la phase 1, chacun sur la mesure brute avec son seuil d'origine
  (`conforme`, `mesure`) ; `--strict` échoue sinon.
- `determinisme`.

## Limites connues

- **Rampes** : là où la description met un revêtement non marchable ou une autre bordure juste derrière
  un bateau (A-0178-1 contre K-0182 à 0,75 m, A-0385-2 devant un massif de BRF), ou des niveaux décrits
  incompatibles avec 5 % (A-0341-1, A-0388-1), la pente dépasse 5 % ; il faut des cotes de rampe ou de
  trottoir et des surfaces marchables dans la description.
- **Traversées sur bordurette P1 affleurante** (A-0339-1, A-0341-1, A-0354-1) : vue décrite de 0,01, hors
  du critère 0,02 ± 0,005 mais conforme à l'arrêté (ressaut ≤ 2 cm) ; à trancher dans la description.
- **Bordures à deux faces vues** (K-0177, K-0178, accès S-0265) : la description (LiDAR 2021, MNT 2026)
  et Panoramax 2024-05-01 montrent une bordure basse entre deux enrobés au même niveau.
- **Zébras provisoires** : bandes du paquet v1 recalées ; les autres marquages attendent `pj_marquages`.
- **Limites de surfaces** : régularisées, mais les formes elles-mêmes (taches d'herbe d'origine raster
  sur les trottoirs) restent celles de la description 0.1.
- **Dalles podotactiles et touffes 3D** : Karma seulement ; côté UE, MI_bev_podotactile sur le sol et
  PG_Joints / PG_Ilots à étendre.
- **Remplissages et matériaux neufs a priori** : il n'existe aucune photo postérieure aux travaux de 2025.
