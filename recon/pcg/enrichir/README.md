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
`[valide_de, valide_a]`. Aucune photo ne montre le cœur après les travaux (dernière photo du cœur : 31/08/2025 ;
les 7 photos Panoramax du 28/07/2026 sont sur la place, environ 135 m au sud, voir `calage_sequence.py`).

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

## Orthos récentes (`orthos_recentes.py`, agent ORTHOS-RECENTES)

Recherche des orthophotos ouvertes postérieures au PCRS 5 cm du 10/05/2022, téléchargement à la
résolution native, recalage sur le PCRS et mini-recensement (cœur ± 75 m et secteur construit
2023-2024 à l'est / sud-est). Réutilise `pipeline/ortho.py` (grille 1000 px, `fetch_tile`, fichier monde).

```
python orthos_recentes.py --decouvrir     # GetCapabilities IGN / CRAIG / GAM, WebDAV PCRS, couverture, dates
python orthos_recentes.py --telecharger   # -> data/raw/ortho_recentes/<couche>/ (jpg + jgw + index.json, git-ignoré)
python orthos_recentes.py --recaler       # décalage / PCRS 2022 -> ortho_recentes/recalage.json
python orthos_recentes.py --planches      # planches 2 x 2 (PCRS 2022 | IGN 2024 / + description | Pléiades 2025)
python orthos_recentes.py --controles     # contrôle auto bordures (2022 + 2024) et marquages (2024) + planches colorées
python orthos_recentes.py --decoupe XL0 YL0 XL1 YL1   # planche libre en coordonnées locales
python orthos_recentes.py --obs           # saisie/*.json + controles_2024.json -> obs_ortho_recentes.json
```

Couches trouvées sur l'emprise (consultation du 10/10/2026, `catalogue_orthos.json`) :

| couche | date sur Meylan | résolution | décision |
|---|---|---|---|
| IGN `ORTHOIMAGERY.ORTHOPHOTOS2024` (= `HR.`, `ORTHOPHOTOS`, `BDORTHO`) | **2024-08-09** (graphe de mosaïquage WFS : toute l'emprise) | 20 cm | téléchargée (référence) |
| IGN `ORTHOPHOTOS.IRC.2024` (= `IRC`) | 2024-08-09 | 20 cm | téléchargée |
| IGN `ORTHO-EXPRESS.2024`, `IRC-EXPRESS.2024` | même vol (NCC 0,84 / 0,80) | 20 cm | téléchargées |
| CRAIG `ortho_2024` (= `ortho`) | même vol (NCC 0,93) | 20 cm | téléchargée |
| IGN `ORTHO-ASP_PAC2025` | image 2024 recompressée (NCC 0,99) | — | doublon |
| IGN `ORTHO-SAT.PLEIADES.2025` | 2025, sans métadonnée ; avant le chantier du cœur (voir ci-dessous) | 50 cm | téléchargée |
| IGN `ORTHO-SAT.SPOT.2022` à `2025` | année seule | 1,5 m | téléchargées (peu utiles) |
| IGN `ORTHO-EXPRESS.2025`, `RVB-EXPRESS.2026`, `IRC-EXPRESS.2025/2026`, `PAC2026`, `PLEIADES.2026` (bord à 2 km au sud), `ORTHOPHOTOS2023`, `PCRS.LAMB93`, `THR` | — | — | vides sur Meylan |
| IGN `ORTHOPHOTOS2021-2023`, `OI.*`, `PAC2022`, GAM `ortho_gam2021`, `Ortho_gam` | 2021-08-13 | 20 cm | antérieures au PCRS |
| CRAIG PCRS 5 cm open data (WebDAV) | seule `2022/grenoble_alpes` couvre le site | 5 cm | déjà exploitée |
| CRAIG RTGE PCRS 5 cm 2025 (juin-juillet 2025) | — | 5 cm | **accès restreint (HTTP 401)** |

Recalage (`recalage.json`, corrélation de phase passe-haut, groupe de mesures le plus dense) : IGN 2024
(+0,04 ; +0,03) m ± 0,1 m par rapport au PCRS (négligeable) ; Pléiades 2025 (+0,47 ; +1,17) m ± (0,12 ; 0,32)
sur le sol, les toits d'immeubles étant déversés de 3 à 7 m. Les planches sont recalées (cadre PCRS).

Résultats :
- **aucune ortho ouverte ne montre le cœur pendant ni après les travaux** : l'IGN 2024 est antérieure (le cœur
  y montre des reprises d'enrobé de 2024) ; le Pléiades 2025 montre encore les zébras, îlots et kiosque de 2024
  sans emprise de chantier (date non publiée : feuillage complet, probablement avant le 23/06/2025) ;
- l'IGN 2024 est en revanche **la seule image aérienne du secteur est / sud-est achevé** (chantier en 2022) :
  bâtiments, parc, allées, stationnements et jeunes plantations ;
- arbres : les arbres du levé GAM plantés en 2023-2024 dans le parc est ont reçu la hauteur et la couronne du
  MNH LiDAR 2021, c'est-à-dire de l'ancienne végétation abattue (`arbre_160` : 10,6 m / 10,6 m pour un jeune
  arbre de 1–1,5 m de houppier en 2024) ; `arbre_175` (sommet MNH 2021) est abattu ; le contrôle NDVI
  `controle_ortho2024_vegetation` confond pelouse et houppier ;
- surfaces : allée stabilisée, trottoir et une place de stationnement absents de S-0352a ; bâtiment bas neuf
  rangé dans S-0352b (noue plantée) ; lits minéraux 2024 du parc est (enherbés sur Pléiades 2025) ;
- bordures : deux doublons géométriques (K-0470 = K-0469 inversée, K-0472 = K-0471) ;
- contrôles automatiques, revus sur planches-contacts (`planches/vignettes/`, verdicts dans
  `saisie/revue_controles.json`) : bordure vue au même endroit en 2022 et 2024, longueur >= 2 m, à plus de 12 m
  des immeubles neufs : 16 / 20 correctes à l'échantillon ; bordure vue en 2024 seule dans le secteur construit :
  23 / 53 (toits déversés et ombres portées) -> seules les 23 revues sont émises ; marquage « conservé » vu en
  2024 : 18 / 22 (erreurs : voiture blanche, feuillage) ; les « absents » automatiques sont presque tous des
  ombres ou des traits de 10 cm illisibles à 20 cm : aucune absence n'est émise sans revue.

`obs_ortho_recentes.json` : 203 observations (24 relevés visuels dont 2 doublons de bordures, 23 bordures revues visuellement, 54 bordures
confirmées sur deux dates, 102 marquages conservés vus en 2024 ; 182 valides 2026, 19 incertaines aux abords
de la zone de travaux 2025 ou de l'avenue du Vercors, 2 historiques). Licences : Etalab 2.0 (IGN, CRAIG) ;
Pléiades et SPOT attribués au CNES (couche WMS) ; images jamais versionnées.

## Images Mapillary (`mapillary.py`)

Inventaire Graph API v4 (bbox 5,7662–5,7702 E × 45,2063–45,2090 N, dallage 4×4) : **1 867 images, 23 séquences,
2017-06 → 2025-05** (`data/raw/mapillary/paquet_jardin/images.json`, sans jeton ; attribution par image).
Jeton lu dans `MAPILLARY_TOKEN` ou le fichier `MAPILLARY_TOKEN_FILE` / `--jeton-fichier`, passé en en-tête
`Authorization`, jamais écrit. Sélection déterministe de 400 images (`selection.json`) : 2022-2025 à ≤ 90 m du
centre ou à ≤ 15 m de l'emprise construite 2023-2024, puis 2022-2025 jusqu'à 170 m (éclaircies à 5 m), puis
2019-2020 et 2017-2018 à ≤ 90 m (4 m) ; vignettes `thumb_2048` (perspectives) et originaux 5760×2880
(sphériques) dans `img/` (CC-BY-SA 4.0, non versionnées).

Caméras : `CameraMly` (sous-classe de `camera.Camera`, sans modifier camera.py) applique les modèles OpenSfM
`perspective` / `fisheye` [f, k1, k2] normalisés par max(W, H) ; `spherical` = `equirect`. `computed_rotation`
(R_cw, monde ENU) -> repère local par la convergence γ ; décomposition en (lacet, tangage, roulis) de
`matrice_rotation` (contrôle : azimut reconstruit = `computed_compass_angle` à 0,01° près). z = MNT 2026 + hauteur
a priori (`computed_altitude` est relatif).

Poses (`recensement/mapillary/poses/poses_mapillary.json`, règle de priorité) :

| statut | n | méthode | σ position |
|---|---|---|---|
| calee_panoramax | 13 | même prise que Panoramax (± 0,5 s, < 4 m, < 5°) : pose calée de poses.json | 0,15 m |
| calee_gcp | 5 | `poses.py` (vote, RANSAC, LM, qualité) depuis le SfM Mapillary | 0,25 m |
| calee_bordures | 27 | sphériques : alignement des bordures GAM hors travaux (tenseur de structure, 2 échelles) | 0,30 m |
| a_priori | 355 | SfM Mapillary seul : jamais utilisé pour mesurer (sphériques : identification seulement) | 2–10 m |

Écarts SfM Mapillary / pose calée Panoramax (13 sphériques) : 0,2–1,9 m, lacet −2,8° à +0,3°. Les photos à plat
(téléphones 2017-2024) ont un retard GNSS jusqu'à ~10 m le long de la marche et peu de GCP lisibles en 2048 px :
le calage GCP n'aboutit pas, le recalage sur les bordures (séquence : τ·v + Δ ; image) converge mais la revue
visuelle (`validation/validation_2018-08-09_*.jpg`, planches bordures_03/04) montre des erreurs de 1–3 m ->
**toutes les perspectives sont rejetées** (pose recalée gardée dans `pose_bordures`). Validation
(`validation/validation.json`, 10 planches, mâts LiDAR pointés indépendamment) : poses Panoramax 0,22–0,28° (7–8
mâts), GCP 0,52° (1 mât) ; recalage bordures : contrôle visuel (bordures et emprises bâties à ≤ 0,3 m à 10–20 m).

Recensement : `--census` produit les cibles (39 conflits ouverts, entités sans preuve image : 369 bordures hors
travaux, 220 surfaces, 191 arbres, 76 mobiliers, 68 marquages, 6 îlots/BEV), la meilleure vue posée de chaque
cible (date valide, proximité, statut de pose ; au plus une image par séquence) et des planches brute | annotée
(`planches/*.jpg`, découpes `preuves/<groupe>/<entité>__<image>.jpg`). La revue visuelle (Claude, une ligne par
clé de planche) est dans `revue_mapillary.json` ; `--obs` en fait `recensement/obs_mapillary.json` (format OBS,
`source = mly:<id>`, attribution et pose dans `attributs.image`, valide_2026 par date et zones de travaux,
attributs alignés sur la table d'alias de la fusion). `triangulation_mixte.json` : axes de mâts pointés
(`gcp.detecter_mat`) sur toutes les vues sphériques calées Mapillary + Panoramax (RANSAC sur paires, revue
obligatoire au-delà de 0,75 m).

Résultat (10/10/2026) : **355 observations** sur 354 entités, dont **325 sans preuve image valable auparavant**
(87 bordures, 121 surfaces, 54 arbres, 36 mobiliers, 23 marquages) ; 173 confirmations, 72 attributs corrigés
(clôtures : barreaudages / grillages / palissades des résidences 2023-2024 ; surfaces : places en stabilisé,
parvis en pavés béton, prairies en herbe haute au lieu de gazon tondu, îlots enherbés classés chaussée),
25 absences (dont 8 marquages tombant sur des bandes plantées : faux positifs indépendants de la date ; arc de
bordures K-0078…K-0086 absent avant travaux, comme attendu), 2 positions (lamp_lidar_VERC_E triangulé à 0,45 m
de la description, la correction de 0,77 m proposée n'est pas retrouvée ; poteau_reseau_12888056356 = même
support bois que lamp_lidar_SW_NO), 83 incertaines ; 135 vues jugées non lisibles (sans observation).
Conflits tranchés ou éclairés : CF-ENR-001 (brun-rouille), -006 (arbre_224 : garder, la cible proposée est un
autre arbre), -009, -012, -023/-025 (sous-zones), -056…-062 (absences attendues), -063 (MZ-5002 hors chaussée),
-065…-067, -074 (barrière présente dès 2024), -076, -077, -079…-081 (pan_J5_1 : panneau B21 posé entre 06/2022 et
08/2024). Limites : aucune image Mapillary postérieure au 18/05/2025 (cœur du carrefour : rien de valable 2026) ;
la fusion 0.2 lit `obs_mapillary.json` (source `mly:`, photo classée selon sa date).

## Fusion du recensement (`fusion_recensement.py` 0.3) et contrôle automatique (`controle_auto.py`)

`python fusion_recensement.py [--sans-carte]` lit **tous** les `recensement/obs_*.json` (ordre alphabétique) et
`web/obs_web.json`, plus les arbitrages de revue `description/enrichi/arbitrages_fusion.json`, et écrit la couche
`description/enrichi/` (détail des règles FUS-* et des comptes dans son `RESUME.md`). Nouveautés de la 0.2 :

- sources `ortho_recente:<couche>` (IGN 2024 -> ortho_2024, Pléiades 2025 -> ortho_2025) et `mly:` (photos) ;
  catégorie **photo_2026** (photo ≥ 05/12/2025), prioritaire pour l'existence, les attributs et la position (FUS-DATE-01) ;
- confirmations automatiques de marquages sans masque véhicules / ombres requalifiées « incertain » sauf
  corroboration manuelle (FUS-AUTO-01) ; contrat des futurs contrôles automatiques (FUS-AUTO-02) :
  `attributs.controle_auto` calculé par `controle_auto.py` (masque des taches claires ou sombres ≥ 3 m² et ≥ 1,2 m de
  large et des ombres portées ; réponse de ligne fine 0,10-0,15 m sur ≥ 80 % de la longueur, PCRS 5 cm requis ;
  part peinte ≥ 0,3 pour les flèches et symboles) :
  `python controle_auto.py --entites ML-0294 MF-5042 [--ortho pcrs2022|<dossier de dalles jgw>] [--planche f.jpg]` ;
- ajouts : entité de même classe levée GAM à moins de 1,5 m -> conflit `ajout_contre_leve_gam` au lieu d'un ajout
  (FUS-ADD-04) ; arbitrages de revue par identifiant d'observation (FUS-ARB-01 : ne_pas_instancier,
  ancrer_bord_ilot, mesure_position) ;
- chronologie des présences / absences (FUS-EXI-03) ; couverture par tranche de date de la preuve concluante
  (2026, 2025, 2020-2024, ortho 2022 ; FUS-COUV-01) dans `couverture.json` et `couverture_preuves.png`.

Nouveautés de la 0.3 (critique de couverture du 10/10/2026) :

- deux couvertures : **large** (FUS-COUV-01, définition 0.2, comparaison) et **stricte** (FUS-COUV-02 : au moins une
  observation image manuelle, confiance moyenne ou haute, valide 2026, probante) ; le statut « confirmé »
  (FUS-STAT-01), l'application d'un déplacement, d'un attribut (FUS-ATT-06) ou d'un retrait (FUS-EXI-04) et la carte
  utilisent la stricte ;
- validité « incertaine » : jamais une preuve de présence ni d'absence (FUS-VAL-04) ; constat « indépendant de la
  date » limité aux projections à 15 m au plus (FUS-VAL-02) ; confiance plafonnée à « faible » au-delà de 20 m
  (FUS-CONF-02) ;
- classes de date relatives aux travaux (FUS-DATE-02) : après travaux, avant travaux hors emprise, avant travaux dans
  l'emprise (± 3 m, au point observé) — ces dernières ne valent qu'avec un appui de règle (FUS-SRC-001 : marquage
  conservé, bordure levée GAM hors périmètre refait, surface inchangée, objet attesté après les travaux) ; zone des
  travaux étendue aux surfaces vues refaites en 2026 (FUS-ZONE-01 : S-0268a, chaussée du Vercors) ;
- liens groupés sur une photo (≥ 3 entités) : seules les entités citées dans la preuve sont prouvées (FUS-LIEN-09) ;
- contrôles automatiques des bordures requalifiés comme ceux des marquages (FUS-AUTO-01/02 : masque et réponse de
  ligne fine ou d'arête) ;
- vote des attributs de bordure (vue, profil, abaissé) depuis les textes libres, par intervalle de la description,
  et contradictions de vue signalées sans jamais être appliquées (FUS-BOR-01..03) ;
- arbitrages `invalider_observation` et `constat_revue` (FUS-ARB-01).

