# recon/pcg/enrichir : géométrie des photos Panoramax (poses calées, projection, triangulation)

Boîte à outils qui rend les photos Panoramax **mesurables** : chaque photo reçoit une pose calée
(position, cap, assiette) par points d'appui, ce qui permet ensuite de projeter n'importe quel
objet de la description v2 dans les photos, de pointer un objet dans plusieurs photos et de le
**trianguler**, donc de vérifier qu'un mât, un panneau ou un feu est bien là où le paquet le place
(ou de mesurer de combien il est déplacé). C'est la brique géométrique de l'enrichissement
(`description/enrichi/`) et du contrôle de placement (« cet objet devrait-il plutôt être là ? »).

Python 3.11 système (numpy, Pillow, pyproj ; ni OpenCV ni SciPy). Lancer depuis ce dossier.

## Repère et conventions

- Repère local unique : `local = L93 − O`, `z = NGF − 216,30` (conversion `decrire/commun.py: repere`).
- Pose `[x, y, z, lacet, tangage, roulis]` : lacet = azimut **grille** de l'axe avant (deg, de +Y
  vers +X) ; lacet brut = azimut Panoramax (nord vrai) + γ, γ = azimut grille du nord vrai
  (−2,0086° au centre, calculé par photo avec pyproj) ; tangage + = axe relevé ; roulis + = côté
  droit relevé. `R = matrice_rotation(lacet, tangage, roulis)`, `c = R·(P − C)` en (droite, avant, haut).
- Modèles : `equirect` (GoPro Max 5760×2880, u = W(0,5 + lon/2π), v = H(0,5 − lat/π)) ;
  `stenope` (f = (W/2)/tan(FOV/2), FOV horizontal Panoramax ; focale inconnue pour les séries
  2020 et 2023 : a priori 62–63°, calée). Pixels continus, pixel (i, j) = [i, i+1[.
- Z : MNT « sol nu octobre 2026 » du paquet ; hauteur de l'objectif a priori par séquence
  (`camera.SEQUENCES` : voiture 1,7 m, vélo 1,9 m, téléphone 1,3 m), calée ensuite.

## Fichiers

| fichier | rôle |
|---|---|
| `camera.py` | catalogue des photos, modèles de caméra, pose brute (GNSS + γ), images, poses calées |
| `projection.py` | `projeter`, `rayon`, `decoupe_perspective` (gnomonique), `fenetre_azel` (grille azimut/élévation où toute verticale est une colonne), rendu de l'ortho 2022 drapée, occultation par le bâti |
| `gcp.py` | catalogue des points d'appui datés, pointage automatique (mâts, sol), vignettes |
| `poses.py` | calage : hypothèses, vote en espace de pose, RANSAC + Levenberg-Marquardt robuste, qualité |
| `triangulation.py` | `trianguler`, `trianguler_verticale`, `pose_sans` (validation non circulaire), `verifier_mat` |
| `planche.py` | planches de contrôle de calage, `planche_preuve(entité, point)`, `planche_projection` |

## Points d'appui (GCP) et validité temporelle

| famille | source | observation | validité |
|---|---|---|---|
| `mat` | `objets/mobilier.geojson` (lampadaires, supports de feux, poteaux de panneaux, potelets, poteaux réseau, mâts) statut « existant », confiance haute (LiDAR 2021, σ 0,25 m) ou moyenne (σ 0,6 m) ; objets portés par un même mât fusionnés | axe du mât (résidu = angle au plan caméra-pied-sommet) | toujours ; « 2026 confirmé » : après travaux |
| `sol` coin_zebra | coins des bandes de passages piétons (`marquages_2026`, GAM ou ortho 2022) | pixel du coin | conservé : toujours ; refait 2025 : après travaux |
| `sol` coin_marquage | sommets vifs des tirets, lignes, flèches, damiers, symboles | pixel | idem ; **fantôme** (présent en 2022, effacé en 2025) : avant travaux |
| `sol` ligne_marquage | axe des lignes (échantillons tous les 1,5 m) | pixel sur l'axe (1D) | idem |
| `sol` texture_ortho | points texturés de l'ortho PCRS 5 cm 2022 sur revêtement dégagé (hors espaces verts, parkings, couronnes d'arbres) | pixel | jusqu'à la fin des travaux ; hors surfaces construites 2023-2024 pour les photos ≥ 2023 |
| `tronc` | troncs levés GAM | axe | désactivé par défaut (haies et voitures font accrocher un mât voisin) |

Une photo antérieure à un objet ne prouve rien sur lui, et réciproquement : chaque GCP porte
`[valide_de, valide_a]`. Aucune photo ne montre le cœur après les travaux (dernière : 31/08/2025).

## Pointage automatique

- **Mâts** : grille (azimut, élévation) du repère local autour de la projection ; réponse de barre
  par ligne `√max(0, −gx(c−k)·gx(c+k))` (deux bords de signes opposés à la largeur attendue,
  quelle que soit la polarité), normalisée par le fond de la ligne ; score = 35e centile sur la
  hauteur du mât (force) + cohérence (part des lignes qui répondent). Rejet si force < 4,
  cohérence < 0,65 ou hauteur angulaire < 3°.
- **Sol** : vue virtuelle native centrée sur le point ; gabarit = marquages vectoriels rendus dans
  la même vue (insensible aux couronnes et aux ombres de l'ortho) et ortho 2022 drapée sur le MNT
  (photo floutée à l'empreinte d'un pixel de 5 cm) ; NCC sur images passe-haut ; pic distinct.
- **Vote en espace de pose** : les cartes NCC de tous les points et les profils des mâts sont
  calculés une fois, puis on cherche (dx, dy, dlacet) puis (dz, tangage, roulis) qui les aligne
  ensemble (robuste aux zébras répétitifs), avec pénalité d'a priori.
- **Photos à plat** : orientation par le **paysage lointain** (montagnes, bâti, lignes d'arbres)
  corrélé avec la photo 360° calée la plus proche dans la grille azimut/élévation (le lacet n'y est
  qu'un décalage de colonnes) ; puis même chaîne.
- **A priori de séquence** (`--sequence`) : les photos non calées reprennent le biais de lacet, le
  décalage GNSS (le long / en travers de la marche) et l'assiette médians de leurs voisines
  acceptées de la même série.

## Calage et acceptation

Moindres carrés robustes (Huber) sur les erreurs **angulaires**, a priori GNSS/hauteur/assiette,
RANSAC sur les observations ; trois passes « pointer puis ajuster » à fenêtres décroissantes.
Inlier : résidu < 3σ borné à 0,25–0,6° (360°) ou 6–15 px (à plat). Acceptation (toutes requises) :

- résidu moyen ≤ 0,5° (360°) ou ≤ 8 px (à plat) ;
- contraintes indépendantes : points + mâts + **lignes distinctes** ≥ 6 (les échantillons d'une même
  ligne au sol comptent une fois), dont ≥ 3 points au sol ou ≥ 4 mâts, et points + mâts ≥ 4 ;
  ≥ 14 équations d'observation ;
- **validation croisée leave-one-out** : chaque GCP inlier est prédit par une pose calée sans lui ;
  moyenne ≤ 2 × seuil (rejette les solutions sur-ajustées : faux appariements cohérents sur une
  carrosserie, une seule ligne de marquage…) ;
- 360° : ≥ 2 secteurs de 45° ou ≥ 8 points de sol étagés en profondeur (rapport ≥ 1,8) ;
- écart au GNSS ≤ 3 × précision annoncée + 1 m.

## Vérification des objets : « devait-il être ici, ou plutôt là ? »

`triangulation.py --verifier-tout` traite chaque mât du mobilier (lampadaires, feux, panneaux,
potelets, poteaux) :

1. **règle de date** : seules les photos prises pendant la période de validité de l'objet comptent
   (un objet « déduit 2026 » ou « 2026 confirmé » n'est vérifiable par aucune photo actuelle :
   verdict « non vérifiable ») ;
2. sur chaque photo calée qui le voit, pose **réajustée sans cet objet** (pas d'auto-validation),
   3 meilleurs pics de barre dans ±2 m autour de la position du paquet (a priori gaussien) ;
3. RANSAC sur les visées (une par photo), score = photos cohérentes − pénalité d'éloignement ;
   triangulation de l'axe ; **fiable** si ≥ 3 photos, angle d'intersection des visées ≥ 20°
   (deux visées opposées sont parallèles), σ ≤ 0,25 m et position stable quand on retire une photo ;
4. verdict : confirmé (écart ≤ max(0,35 m ; 3σ)) | affinage (≤ 0,75 m) | déplacement (> 0,75 m) ;
   tout écart > 0,35 m produit une planche `triangulation_<objet>.jpg` (axe à la position du paquet
   en haut, triangulé en bas, mêmes photos) ;
5. **revue visuelle** (`revue_visuelle.json`, verdicts de Claude avec la planche citée) :
   `correction_confirmee | correction_rejetee | incertain` ; `decision` finale = garder | affiner |
   deplacer | revue_requise | non_conclu. Seules les décisions garder / affiner / deplacer amorcent
   les GCP (position triangulée, σ triangulé) pour la passe suivante.

Leçon intégrée : une première version annonçait le lampadaire du TPC déplacé de 2,07 m (deux visées
presque colinéaires + un mât voisin) ; les planches montraient l'inverse. D'où l'angle de droites,
la stabilité leave-one-out, les pics multiples et la revue visuelle obligatoire au-delà de 0,75 m.

## Commandes (depuis `recon/pcg/enrichir`)

```
python poses.py --photos <id8...>        # 1. 360° d'abord (références d'horizon des photos à plat)
python poses.py --cibles                 # 2. 360° à < 60 m du centre + série à plat du 2025-08-31
python poses.py --assembler              #    par_photo/*.json -> poses.json + gcp.json
python triangulation.py --verifier-tout  # 3. vérification des mâts -> amorçage des GCP triangulés
python poses.py --cibles --sequence      # 4. non acceptées (et calées avec a priori) : a priori de séquence
python poses.py --requalifier            #    recalcule l'acceptation des par_photo avec les critères courants
python poses.py --assembler
python planche.py --controle <id8...>    # planches de contrôle (vignettes de chaque GCP pointé)
python planche.py --entite MAT-feu_NE_TPC --point 12.0 9.0 0.31 --sommet 12.0 9.0 3.4
python triangulation.py --valider        # mâts levés : position triangulée vs levé (poses sans le mât)
python triangulation.py --verifier-tout  # tous les mâts du mobilier, y compris « à vérifier »
```

Parallélisable par `--part k/n` (une photo = un fichier `par_photo/<id8>.json`, déterministe).

## Sorties (`recon/out/paquet_jardin/v2/enrichi/poses/`)

- `poses.json` : par photo, pose brute et calée, intrinsèques, écarts types, qualité (n GCP,
  mâts / sol, résidus moyen et max en degrés et pixels, écart au GNSS, correction de lacet,
  hauteur de l'objectif), acceptation et raison, GCP utilisés ;
- `gcp.json` : catalogue daté des GCP et observations par photo (pixels, score, résidu, inlier) ;
- `triangulation.json` : validation sur mâts levés, vérification du mobilier ;
- `planches/` : `controle_<id8>.jpg`, `preuve_<entité>.jpg`, `validation_projection.jpg`,
  `triangulation_*.jpg`.

## Résultats au 10/10/2026 (65 photos traitées : 30 en 360° à < 60 m du centre + 35 à plat du 2025-08-31)

| série | acceptées | remarque |
|---|---|---|
| 2025-05-18 GoPro (GNSS 0,1–0,4 m) | 8 / 10 | 13 à 45 GCP, résidu moyen 0,08–0,35°, lacet −2,5° à +0,2°, objectif à 1,9–2,2 m |
| 2024-08-24 GoPro (GNSS ±4 m) | 5 / 6 | 11 à 38 GCP, décalage GNSS 1,0–2,4 m |
| 2024-05-01 GoPro | 0 / 11 | cœur en chantier (pelles, clôtures) : marquages 2022 absents, mâts masqués |
| 2025-01-12 GoPro (vélo) | 0 / 3 | 35–52 m, peu de GCP visibles |
| 2025-08-31 à plat (A52, ±5 m) | 0 / 35 | chantier au cœur, contre-jour, ±5 m ; les rares solutions trouvées (mâts sur une carrosserie, un feu rouge) sont rejetées par la validation croisée et l'étendue angulaire |

Les 13 poses acceptées : 24 GCP en moyenne, résidu moyen 0,17° (≈ 2,8 px), validation croisée
0,10–0,54°, écarts types de position 1–27 cm, de lacet 0,06–0,47°.
Une pose refusée garde sa meilleure solution dans `par_photo/` mais n'est jamais utilisée :
`camera_calee` ne renvoie une pose calée que si elle est acceptée (sinon la pose brute).

Validation (`triangulation.json`, `planches/`) :
- **6 mâts levés au LiDAR 2021** triangulés depuis 4 à 8 photos chacun, poses réajustées sans le
  mât : écart au levé 0,16 / 0,17 / 0,17 / 0,19 / 0,27 / 0,36 m (moyenne 0,22 m ; σ de
  triangulation 3–10 cm ; le LiDAR donne souvent la tête de feu, décalée du fût) ;
- **10 points levés** (5 mâts LiDAR, 5 coins de zébra GAM) projetés dans 5 photos calées
  (`validation_projection.jpg`, revue visuelle : axes sur les fûts, croix sur les coins de bandes ;
  la balise J5 du paquet tombe à ≈ 0,3 m du support réel) ;
- coins de zébra GAM retriangulés depuis 2 photos : 2–8 cm (non indépendant : ce sont aussi des GCP).

Vérification du mobilier (`triangulation.json` → `verification_mobilier`, 104 objets) : 9 positions
confirmées + C114 gardé après rejet visuel du déplacement proposé (la triangulation avait pris un
autre support) = 10 décisions `garder` ; 1 affinage confirmé visuellement (feu_NE_droite, 0,36 m) ;
3 cas incertains (feu_NE_SE_pietons, D21 ×2 : deux supports à 0,5 m) ; 34 objets « 2026 » non
vérifiables (aucune photo postérieure aux travaux) ; 48 non vus par les 13 photos calées.

Limites : aucune photo du cœur après travaux ; la série à plat du 2025-08-31 n'est pas calable
automatiquement avec ces GCP (chantier, ±5 m) — pistes : nouvelle prise de vue 2026 (même chaîne),
pointage manuel validé de 6 à 10 GCP par photo, ou GCP 2026 relevés sur place.

## API (import depuis un autre script)

```python
import sys; sys.path.insert(0, "recon/pcg/enrichir")
from projection import projeter, rayon, decoupe_perspective
from triangulation import trianguler, trianguler_verticale
from planche import planche_preuve
r = projeter([[12.0, 9.0, 0.31]], "119d9094")        # uv, visible, distance, pose 'calee'|'brute'
C, d = rayon("119d9094", (2900.5, 1500.0))            # rayon 3D local
img, cv = decoupe_perspective("119d9094", lacet=60, tangage=-5, fov=60, taille=800)
t = trianguler([("119d9094", (u1, v1)), ("e5d79de9", (u2, v2))])
```
