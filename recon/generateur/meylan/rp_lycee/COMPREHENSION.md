# Rond-point du Lycée — compréhension de la scène (fusion des images dans le modèle)

*`recon/generateur/meylan/rp_lycee/COMPREHENSION.md`, 18/10/2026, passe 2 de l'étape 3. Ce texte est ma lecture des
images, croisées entre elles. Aucun algorithme n'a fusionné quoi que ce soit : les orthos datées, les 60 photos
Panoramax de la comparaison v2 et les bordures du levé GAM ont été regardées une à une, en tuiles natives (≤ 1 092 px).
Les chemins sont relatifs à `recon/out/generateur/meylan_rp_lycee/comparaison/meylan_rp_lycee/`. Les photos sont sous
`photos_non_versionnees/`, elles ne sont jamais versionnées. Les vues sont citées par leur clé (`<id8>_<lacet>`) et,
quand elle existe, leur planche 2 × 2 (`centre_pNN`).*

## 1. Images lues

| Source | Images | Ce qu'elles apportent |
|---|---|---|
| Orthos datées, même emprise | `orthos/planche_dates_centre_p01.png` (IGN 2024-08-09, Pléiades 2025, IGN 2021-08-13, IGN 2018-08-21), `orthos/centre_ign2024.png`, `orthos/site_ign2024.png`, `orthos/planche_dates_site_p01.png`, `orthos/contexte_planign.png` | forme générale, îlots, état stable de 2018 à 2025 |
| Zooms d'ortho que j'ai faits (IGN 2024 agrandie, grille de 5 m du repère du site) | `comprehension/zooms/ouest_ign2024.png`, `ouest_gam.png` (bordures GAM en rouge, marquages en cyan), `nord_ign2024.png`, `sud_ign2024.png`, `est_ign2024.png` | îlots séparateurs, passages, accès |
| Coupes des bordures GAM | Verdun x = −105, −95, −80, −70, −60, −50, −42, −38, −34 ; Taillefer y = −100 à −33 ; Mairie y = 34 à 80 ; 7 Laux, 3 coupes obliques. Outil : `coupes_gam.py`, non versionné. | largeurs des voies et des îlots |
| Vue de dessus rendu \| ortho (itération 2) | `dessus/planche_dessus_centre_ign_t00.png`, `dessus/contours_centre_ign_t00.png`, `t01`, `dessus/contours_site_ign.png`, `dessus/rendu_site_ign.png` | ce que le modèle montre faux |
| Plans d'index | `comprehension/plan_vues_centre.png` | position et visée des 60 photos |
| Vues du centre (planches 2 × 2) | `centre_p01`, `p02`, `p03`, `p05`, `p08`, `p12`, `p16`, `p20`, `p24`, `p28`, `p36`, soit 44 vues sur les 8 directions | anneau, couronne, muret, îlots, entrées |
| Vues natives (1 092 px) | `ed15dd0e_-146`, `3611ffa6_+003`, `67834681_+164`, `23d3f6ff_+166`, `307cecd9_+005`, `3c5f3ca7_-140`, `3df599ec_-146` | nez des îlots, panneaux, accès nord-ouest |

En tout, 51 vues photo différentes ont été regardées, prises du 01/05/2024 au 28/07/2026 : 23 du 28/07/2026, 8 du
28/06/2026, 6 du 18/05/2025, les autres de mai 2024. Elles sont toutes dans la fenêtre d'état (≥ 01/05/2024).

## 2. Ce qui est sûr, croisé sur plusieurs images

### 2.1 Anneau

- Anneau d'environ **8 m**, en enrobé gris fissuré, sans voie marquée, sans rive peinte côté îlot.
  - Images : toutes les vues prises sur l'anneau, par exemple `ee3d887b_-170`, `161a60d1_-134`, `48975772_-139`, `bd7d48ad_-077`, `1a3fbc1d_-176`.
  - Le modèle de l'itération 2 a l'anneau juste à ≈ 1 m près : les contours tombent sur la bordure dans `contours_centre_ign_t00` et `t01`.
- L'**enrobé a été refait entre 2018 et 2021** : en 2018 il était sombre, en 2021 et 2024 il est clair (`planche_dates_centre_p01`). Rien d'autre n'a changé dans la géométrie de 2015 à 2025.
- Une **bordure basse** court le long du bord extérieur.
  - Au droit des quatre passages inférieurs, elle porte un **parapet en béton surmonté d'un garde-corps** métallique : nord-ouest sous la sortie de Verdun, sud-ouest, nord et est.
  - Images : `3611ffa6_+003`, `307cecd9_+005`, `ed70374e_+147`, `161a60d1_+153`, `3b6c677b_+017`, `5a7cee9c_-002`.
  - Escaliers vers les passages : `23d3f6ff_+166`. OSM : chemins `layer=-1` 190080264, 190080265, 398052235, 398052236.

### 2.2 Couronne et îlot central (le « centre »)

L'ordre est le suivant, de l'anneau vers le centre.

1. **Rang de pavés** gris-beige au fil d'eau, ou bien **caniveau à grille fendue**.
   - Pavés côté est et sud : `361048f7_-131`, `361048f7_-161`, `a23479c9_-129`, `3c5f3ca7_-140`.
   - Grille fendue côté nord-ouest et ouest : `ee3d887b_-170`, `ee3d887b_-135`, `161a60d1_-134`, `3611ffa6_-032`, `bd7d48ad_-077`.
2. **Couronne en béton coulé, inclinée vers l'anneau**, d'environ 1,5 à 2 m, fissurée et tachée.
   - Sur les orthos, c'est la bande claire au bord de l'îlot (`centre_ign2024`).
3. **Muret vertical en béton** d'environ **0,6 à 0,8 m**, avec un chaperon.
   - Il est continu tout autour : on le voit sur toutes les vues de l'anneau.
4. Derrière le muret, un **massif boisé** : arbustes, ronces, grands arbres de 10 à 15 m, un **sentier circulaire** au rayon ≈ 15 m (OSM 118543290) et des placettes revêtues aux débouchés des passages inférieurs.
   - Le sentier et les placettes se lisent mieux sur `centre_ign2018`, avant que la végétation ne pousse. Ils sont encore visibles en 2024.
   - La photo `d6305338_-081` (p12) et `d6305338_-113` (p16), prises en vélo dans l'îlot le 01/05/2024, montrent l'intérieur : allée revêtue, bordure de rondins, murs de soutènement tagués des débouchés.
   - Les cheminements piétons et cyclables sont donc **en contrebas, sous l'anneau**. L'îlot n'est pas un simple disque planté.
5. **Panneaux B21** (flèche blanche sur fond bleu) posés sur le muret, face aux entrées :
   - face aux 7 Laux : `361048f7_-131`, `3667caac_-022`, `e15979c5_+002` ;
   - face au Taillefer : `3c5f3ca7_-140`.
6. Rayon de l'îlot : le cercle intérieur du modèle tombe sur le bord de la couronne (`contours_centre_ign_t00`). Le diamètre (66 m), l'anneau (8 m) et la couronne (1,5 m) sont gardés.

### 2.3 Branches, îlots séparateurs, entrées et sorties

L'ordre est trigonométrique, en partant de l'ouest. Les entrées ont toutes une **ligne cédez-le-passage** en tirets et
un AB3a. Il n'y a **aucun feu**.

**Verdun ouest** (`ouest_gam.png`, coupes GAM, `ed15dd0e_-146`, `33c 23d3f6ff_-068` (p36), `307cecd9_+005`, `3611ffa6_+003`)
- Profil :
  - sortie au nord d'**une voie de 5,9 à 7,1 m**, élargie au droit d'un **arrêt de bus** : zigzag GAM et quai vers x = −65 à −50 ;
  - entrée au sud de **deux voies (8,2 à 9,3 m)**.
- Les deux sens sont séparés par un **séparateur bordé d'≈ 0,9 m** jusqu'à x ≈ −60.
- Ce séparateur s'ouvre ensuite en un **îlot triangulaire** :
  - largeurs : 2,9 m à x = −50, 4,7 m à −42, 5,8 m à −38, **7,3 m au bord de l'anneau** ;
  - surface en enrobé gris gravillonné, bordures aux joints repeints en blanc ;
  - au nez : un mât d'éclairage avec caméras, des panneaux de jalonnement, un AB3a, un B21 et un **B1** tourné vers l'anneau (`33c`, `25f c60ba812_+051`).

**Accès nord-ouest du parking** (OSM 1316393621, service)
- Petite entrée et sortie entre Verdun et la Mairie, vers le parking de l'ancienne mairie.
- On y voit une ligne cédez en tirets, un AB3a et un panonceau « cédez le passage » à droite de l'anneau (`307cecd9_+005`, `3611ffa6_+003`) et un passage piéton (`nord_ign2024`, vers (−29 ; 28)).

**Chemin de l'Ancienne Mairie, au nord** (`nord_ign2024`, coupes GAM, `67834681_+164`, `f0587cd3_+010` (p28), `b215fc54_-008` (p28))
- Entrée d'≈ 3,6 m à l'ouest et sortie d'≈ 4,9 m à l'est.
- Elles sont séparées sur les **≈ 15 derniers mètres** par un **séparateur bordé étroit** : 0,6 m à y = 42 et 1,2 m à y = 38. Il porte un mât et des panneaux.
- Un **passage zébré** traverse l'entrée près de l'anneau.
- Plus au nord, la rue est à double sens sans séparation.

**Avenue des 7 Laux, au nord-est** (coupes GAM, `5171922c_-168` (p20), `3667caac_-022` (p16), `bd7d48ad_-136`)
- Entrée de **deux voies (8,2 m)**, ligne de voie GAM.
- **Séparateur en muret de béton** d'≈ 1,55 m, avec une grille fendue le long de son pied.
- Sortie d'une voie (4,95 m).
- Le nez du séparateur est bas et bordé à l'entrée.
- La piste et la contre-allée sont au nord-ouest. Les coupes GAM confirment les cotes de l'itération 2.

**Accès de service est** (`est_ign2024`, `36769511_-014`, `1a3fbc1d_+033`)
- Une voie d'environ 4 m, **en entrée seule**, avec sa ligne cédez en (35 ; −1 à −6).

**Avenue du Taillefer, au sud** (`sud_ign2024`, coupes GAM, `3c5f3ca7_-140`, `3df599ec_-146`, `48975772_-056` (p36), `313e52cb_-032` (p36))
- Tronc commun de **10,2 à 10,9 m** en deux voies, à ligne axiale et inscriptions « 50 ».
- Il s'ouvre ensuite en un **îlot triangulaire bordé, revêtu (enrobé gris gravillonné, herbes folles)** :
  - largeurs : 0,9 m à y = −60, 2,6 m à −50, 4,95 m à −40, ≈ 6,8 m au bord de l'anneau ; pointe vers y = −62 ;
  - lignes blanches continues le long des deux bordures ;
  - **caniveau à grille côté sortie** ;
  - au nez : jalonnement « Chambéry / Inovallée / Hôtel de ville », AB3a, B21 et **B1** tourné vers l'anneau.
- Sortie de 4,8 m à l'ouest, **entrée large d'une voie de 7 m** à l'est.

## 3. Ce que le modèle de l'itération 2 montrait faux, et ce que la passe 2 corrige

| N° | Élément | Itération 2 | Réel (images) | Passe 2 (description) |
|---|---|---|---|---|
| 3.1 | Verdun : position et îlot | axe au milieu des deux sens OSM, terre-plein constant de 4,3 m en enrobé : à l'anneau, îlot, sortie et entrée étaient décalés de 1,5 à 4 m vers le sud | séparateur de 0,9 m qui s'ouvre en îlot triangulaire de 7,3 m (§ 2.3) | axe sur le séparateur GAM, bout (−30,38 ; −0,85) ; séparateur de 0,9 m, sortie élargie au droit du bus, îlot élargi linéairement de 0,9 à 7,3 m sur 31 m |
| 3.2 | Mairie : séparation | zone hachurée peinte de 0,6 m sur ≈ 20 m | séparateur bordé de 0,6 à 1,2 m sur ≈ 15 m | terre-plein bordé de 0,8 m sur les 15 derniers mètres, précédé de sa zone hachurée de 3 m |
| 3.3 | Mairie : passage | passage à 5 m de l'anneau (règle) | zébra près de l'anneau | inchangé ; le passage traverse le séparateur (refuge de 0,8 m admis, DEF-022) |
| 3.4 | Taillefer : îlot et axe | îlot **planté** rectangulaire de 4,6 m sur 26 m après une ouverture hachurée de 10 m ; bout 7 m trop à l'est ; tronc de 2 × 3,5 m | îlot triangulaire revêtu, 0 → 6,8 m sur ≈ 33 m ; tronc de 10,2 m | axe GAM, bout (3,84 ; −32,0) ; tronc de 2 × 5,0 m ; pointe hachurée de 3 m, puis terre-plein en enrobé de 0,6 → 6,8 m sur 32 m |
| 3.5 | Îlot central | disque d'herbe haute plat, couronne grise | muret, massif boisé, sentier et passages en contrebas | inchangé (pas de mot) : besoins G3 et G9 |
| 3.6 | Couronne | 1,5 m, gris uni | béton incliné, rang de pavés ou grille fendue | inchangé (pas de mot) : besoin G4 |
| 3.7 | Accès nord-ouest | absent | entrée et sortie du parking, ligne cédez | non décrit : une branche aussi courte (≈ 15 m jusqu'au parking) fait retomber dans G8 ; écart restant |

## 4. Contradictions entre dates, et comment je les tranche

- **2018 → 2021** : enrobé de l'anneau sombre, puis clair. C'est une réfection de la couche de roulement, sans changement de géométrie. L'état décrit est celui de 2021 à 2026.
- **Photos de mai 2024 et de juillet 2026** : mêmes îlots, mêmes panneaux, même muret. Exemple : nez de l'îlot de Verdun sur `ed15dd0e_-146` (18/05/2025) et `23d3f6ff_-068` (09/05/2024). Il n'y a pas de travaux visibles.
- **« Îlot planté » du Taillefer** (premier passage) contre **îlot revêtu** (passe 2) : l'ortho 2024 (`sud_ign2024`) et deux photos du 28/07/2026 (`3c5f3ca7_-140`, `3df599ec_-146`) montrent un îlot gris revêtu. La végétation vue dans le premier passage est celle des talus de part et d'autre. **Revêtu** l'emporte.
- **OSM contre GAM** pour l'axe du Taillefer au sud (jonction OSM en (20,3 ; −66,2), ligne axiale GAM en (23,8 ; −70)) : le **levé GAM** l'emporte, car il recoupe l'ortho.

## 5. Ce qui reste incertain

- La hauteur exacte du muret (0,6 à 0,8 m) et celle du massif derrière : estimées sur photo, sans mesure. On ne sait pas si l'intérieur est surélevé ou si seuls les cheminements sont en contrebas : les deux se voient (talus boisé au-dessus du muret, allées en contrebas aux débouchés).
- La largeur exacte de la couronne (1,5 à 2 m) : bande claire sur l'ortho de 20 cm, sans levé GAM.
- Le tracé exact de l'accès nord-ouest et le sens de ses voies : aucune photo prise dedans.
- Le matériau des îlots de Verdun et du Taillefer : enrobé gravillonné clair ou béton désactivé usé. Il apparaît plus clair que la chaussée sur l'ortho et gris moyen sur les photos. Il est décrit en « enrobé », car le terre-plein « enrobé clair » n'existe pas au format.
- La position du passage zébré de la Mairie : il est en biais sur l'ortho, et le modèle le pose droit à 5 m de l'anneau.
