# recon/pcg : description sémantique v2 (« Claude décrit, Houdini fabrique, UE 5.8 place »)

La v2 remplace la scène v1 (faces de bordure verticales, marquages vectorisés depuis le raster,
couleurs à plat) par une **description vectorielle paramétrique** : chaque bordure, surface, îlot ou
ponctuel est décrit par des attributs sourcés, et la géométrie n'est fabriquée qu'ensuite, de façon
déterministe, par Houdini (HDA `pj_*`), puis placée dans Unreal 5.8 par PCG. Ce dossier contient le
schéma, les convertisseurs et la zone pilote de la phase 1 (architecture : `architecture_v2.md`).

```
recon/pcg/
  README.md                       ce fichier
  zone_pilote.geojson             emprise de la zone pilote ZP-01 (L93) + justification
  schema/
    description_scene_v2.schema.json   JSON Schema 2020-12, version description_scene_v2/0.1
    materiaux_description.json         materiau_id autorisés -> librairie CC0 (assets/lib/materiaux)
  decrire/                        convertisseurs (Python 3.11 + numpy + Pillow + pyproj, sans shapely)
    commun.py      repère (fonction unique `repere`), GeoJSON déterministe, MNT 2026, géométrie
    contexte.py    lecture des données du dépôt (paquet v1, GAM, OSM, constats) en repère local
    bordures.py    famille bordures (+ candidats BEV)
    surfaces.py    famille surfaces
    ilots.py       famille ilots (+ bordures synthétiques de fermeture)
    composer.py    enchaîne tout, écrit les couches et le manifeste, lance la validation
    valider.py     validateur JSON Schema minimal + contrôles géométriques et de cohérence
    apercu.py      planche PNG de contrôle sur l'ortho 2022
recon/out/paquet_jardin/v2/description/
  description_scene_v2.json       manifeste (site, O, date 2026-10, saison, références sha256,
                                  couches, comptes, statistiques, preuves, a priori, règles PCG)
  base/bordures.geojson  base/surfaces.geojson  base/ilots.geojson  base/ponctuels_sol.geojson
```

Les couches `enrichi/` (Panoramax, vérifiées deux fois) et `arbitre/` viendront s'empiler sur
`base/` (priorité arbitré > enrichi > base) sans changer le schéma.

## Repère et conventions

- **Fichiers** : Lambert-93 (EPSG:2154), altitudes NGF-IGN69, mètres. Coordonnées arrondies au mm.
- **Repère local** (Houdini, USD, points PCG) : `local = L93 − O`, `O = (917279.43, 6460289.98)`,
  `z = NGF − 216.30` ; X est, Y nord, Z haut. Unreal : `X = x·100, Y = −y·100, Z = z·100`, `yaw_UE = −yaw`.
  Une seule conversion : `decrire/commun.py: repere(pts, "local" | "l93")`.
- **Z** : toujours le MNT « sol nu octobre 2026 » (`donnees/relief/heightmap_3025_10cm.png` + `.json`)
  ou les mesures de bordure, **jamais les maillages v1** (jusqu'à +1,77 m au-dessus du MNT sur les
  classes 2025).
- **Identifiants stables** : `K-<ligne GAM>[a-z]` (bordures ; `K-…z` et `K-9…` = bordures ajoutées),
  `S-<surface v1>[a-z]`, `I-<anneau ou surface v1>`, `A-<bordure>-<n>` (abaissés), `BEV-<abaissé>`.
- **Provenance** : chaque entité porte `prov {attribut: {src, ref, conf}}` ;
  `src` ∈ `gam | pcrs2019 | lidar2021 | xodr | ortho2022 | plan2025 | terrain2026 | photo_utilisateur |
  panoramax:<id8>/<tuile> | constat:<id> | norme:<réf> | a_priori:<règle> | osm[:node/<n>] | regle:<spec>`,
  `conf` ∈ `haute | moyenne | faible`. Le manifeste indexe les preuves citées et liste chaque règle
  a priori avec les entités concernées : ce qui n'est pas observé reste visible comme tel.
- **Déterminisme** : pas d'horodatage, entités triées par id, une entité par ligne ; deux exécutions
  donnent des fichiers identiques à l'octet (`hash_description` = sha256 des quatre couches).

## Familles (schéma 0.1)

**bordures** : `LineString` 3D de l'**arête avant** (u = 0 des contours de `assets/specs/bordures.json`),
Z des sommets = **fil d'eau** NGF (MNT 2026 à 0,30 m devant la face). Toutes les bordures sont orientées
**côté haut à gauche, face vue à droite**.
- double arête GAM dédoublonnée (traits parallèles à 0,10 m, 0,15 m aux Saules Blancs ; on garde le côté bas) ;
- `intervalles [{s0, s1, profil, vue_m, vue_m_fin?, role}]` : partition exacte de `[0, longueur_m]` ;
  `role` = `courant | bateau | chartiere` (vue linéaire de `vue_m` à `vue_m_fin`) ; profils NF par
  `regles_affectation` (h_vue lissée sur 7 m, changements de moins de 5 m fusionnés) ;
- `abaisses [{id, type: traversee|charretiere, s0, s1, vue_m, profil, raccords, bev, sources}]` :
  traversée à 0,02 m (arrêté du 15/01/2007), charretière 0,02-0,04 m, chartières de 1 m, largeur ≥ 1,20 m,
  extrémités recalées sur les blocs CHARTIERE GAM ; une bordure n'est abaissée que si elle coupe la marche ;
- `materiau` (`beton_gris` existant, `beton_clair` posé après 2021 ou constat), `aspect`
  (épaufrures, mousse et herbe des joints, salissure), `element_m: auto` (1,00 m si R ≥ 12 m,
  0,50 m sinon, pièces courbes sous 3 m : voir `courbes`), `joint_mm: 6`, `caniveau` (CS2 si ligne GAM).

**surfaces** : polygones v1 découpés par la zone, `classe`, `revetement {materiau_id, age, salissure,
appareillage…}`, `niveau {z_med_ngf, devers_pct, dz_bordure_m, dz_fil_eau_m, arasement}` (MNT 2026),
`bords [{bordure, cote: arriere|avant}]`, `ilots`, `limite_raster` (limite v1 issue d'un raster : à
recaler sur l'arête arrière des bordures à la fabrication). Les îlots priment sur les surfaces qu'ils
recouvrent.

**ilots** : polygone = anneau de l'arête avant de la ceinture (anneau GAM fermé, ou polygone v1 recalé
sur les bordures). `remplissage {materiau_id, epaisseur_m, retrait_sous_bordure_m, retrait_bordure_m,
granulometrie_mm, bombement_m, debordement}` : le remplissage commence à `retrait_bordure_m` (largeur
du profil) à l'intérieur et affleure `retrait_sous_bordure_m` sous le dessus de bordure (BRF 0,04 m,
gravier 0,03 m). `ceinture` (bordures), `nez {rayon_m, position, peint}`, `objets_portes`, `plantation`.

**ponctuels_sol** : BEV (dalles 0,40 × 0,40, profondeur 0,40 m, à 0,50 m du nez) derrière les bateaux
de traversée qui donnent sur la chaussée, sauf OSM `tactile_paving=no` ; tampons et avaloirs absents
des vecteurs GAM (à enrichir).

Matériaux : `schema/materiaux_description.json` résout chaque `materiau_id` vers la librairie CC0
(`disponible`, `substitut`, `derive`, `a_telecharger` : BRF à télécharger, gravier → `gravillons_ilot`).
Pas de matériau City Sample côté Houdini / Karma.

## Zone pilote ZP-01

Rectangle local x ∈ [−11, 60], y ∈ [−28, 72] (71 × 100 m ; L93 917268.43-917339.43 / 6460261.98-6460361.98) :
refuge et TPC NE, traversée NE (blocs CHARTIERE, BEV), trottoir + piste + accotement de Verdun NE sur
≈ 65 m, entrée charretière de l'accès riverain (K-0182), îlot BRF (goutte NE, I-0297), îlots gravier du
Vercors (I-0390, I-0629), traversée du Vercors. 50 photos Panoramax dans l'emprise, dont 9 en 360° du
18/05/2025 (précision 0,1-0,4 m). Justification détaillée dans `zone_pilote.geojson`.

## Commandes

Depuis la racine du dépôt, avec l'interpréteur système (Python 3.11, numpy, Pillow, pyproj) :

```
python recon/pcg/decrire/composer.py                       # description + validation
python recon/pcg/decrire/composer.py --png planche.png     # + planche de contrôle
python recon/pcg/decrire/valider.py [DOSSIER]              # validation seule
python recon/pcg/decrire/apercu.py SORTIE.png --etiquettes [--emprise x0 y0 x1 y1] [--res 0.025]
```

`composer.py --sortie DOSSIER` écrit ailleurs (essais) ; le code de sortie est 1 si la validation échoue.

## Limites connues (0.1)

- Aucune photo après les travaux 2025 : matériaux, remplissages et bordures neuves sont `a_priori`
  (listés dans `description_scene_v2.json: a_priori`) ; les îlots du Vercors reprennent le gravier
  observé avant travaux (constats coeur-31, p2025_01_vercors-26), le BRF de la goutte NE suit la photo
  de référence de l'utilisateur.
- Les limites de surfaces v1 d'origine raster ne sont pas encore recalées (drapeau `limite_raster`).
- Les refuges à niveau (TPC NE coupé par la traversée) n'ont pas de BEV décrite (pas de bordure où l'ancrer).
- Le MNT 2026 garde par endroits un relief 2021 disparu (prolongement de l'ancien TPC NE : S-0344,
  `niveau.arasement`) : la fabrication doit araser ces surfaces au niveau indiqué.
