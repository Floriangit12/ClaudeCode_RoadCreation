# Comparaison multivues d'un tronçon fabriqué avec des photos Panoramax

*`recon/generateur/comparaison/` — 17/10/2026 ; v2 (dossier de compréhension) le 18/10/2026.*

Principe voulu par l'utilisateur : Claude décrit une scène réelle de Meylan à partir de photos (description
grossière, « environ 20 m »), le générateur la reconstruit en gérant le détail par les règles, et on juge la
**ressemblance** en comparant le rendu à **plusieurs** photos Panoramax prises sous **différents angles et depuis
différentes positions** (pas une seule vue, pas de précision au centimètre). Cet outil prépare tout ce qu'il faut
pour ce jugement ; le jugement lui-même (grille d'écarts) est rempli par l'agent qui regarde les planches.

```
python recon/generateur/comparaison/comparer_multivues.py S_M20 S_M24 S_M27
       [--etapes selection,pose,rendu,planches] [--rafraichir] [--depuis 2019-01-01] [--echantillons 128]
```

Python système (numpy, scipy, OpenCV, pyproj, shapely, Pillow) ; le rendu passe par hython
(`rendu_hython.py`, Houdini 22.0.459, Karma XPU). Aucune écriture hors de `D:` : les fichiers temporaires de
Houdini vont dans `recon/out/generateur/comparaison/_tmp/`.

La **v2** (18/10/2026, section suivante) prépare un *dossier de compréhension* pour les carrefours et les giratoires
(`--v2`) ; sans `--v2`, l'appel est celui de la v1, inchangé (sections « Entrées » et suivantes).

## v2 : dossier de compréhension, lu par le modèle (18/10/2026)

Remarques de l'utilisateur : « avec 6-10 photos tu ne peux pas comprendre toute la scène, et surtout le CENTRE avec la
ZONE DE CONFLIT » ; « l'outil de comparaison, c'est directement toi qui passes les images dans ton modèle et essaies
de comprendre la scène ; il peut aussi intégrer plusieurs orthos pour comprendre la scène de manière générale : c'est
de la fusion, mais directement dans ton modèle ». La v2 ne remplace donc pas la lecture par des algorithmes : elle
**choisit, découpe, date et indexe** les images (orthos de plusieurs dates, 40 à 60 photos sous toutes les directions,
rendu) que l'agent lit ensuite lui-même, dans l'ordre donné par `comprehension/LISEZMOI.md`. La pose reste celle de
la v1 (métadonnées, redressement, affinage validé) : approximative, elle suffit pour comparer à l'œil.

```
python recon/generateur/comparaison/comparer_multivues.py meylan_paquet_jardin --v2
       --sites-conf recon/generateur/meylan/paquet_jardin/comparaison_site.json
       --sortie recon/out/generateur/meylan_paquet_jardin/comparaison
       [--depuis 2024-08-24] [--jusqu-au 2025-06-22] [--complement-depuis 2019-01-01 | non]
       [--etapes selection,orthos,pose,rendu,dessus,planches,dossier] [--processus 4] [--sans-mapillary]
       [--couches-orthos pcrs2022,ign2024,...] [--echantillons 128] [--rafraichir]
```

| Étape | Module | Ce qu'elle fait |
|---|---|---|
| `selection` | `zones.py`, `selection_v2.py`, `api_panoramax.py`, `api_mapillary.py` | **zones d'intérêt** tirées du modèle (`modele_voie.json`) : zone centrale de conflit (ou anneau découpé par branche et îlot central d'un giratoire), îlots, passages, 45 m d'approche de chaque branche ; recherche Panoramax (repli sur les instances IGN et OSM-FR si le méta-catalogue ne répond pas) puis **Mapillary en complément** (jeton lu dans `%USERPROFILE%\.config\meylan_adas\mapillary_token.txt`, jamais écrit ; doublons d'une même prise publiée sur les deux écartés) ; filtres de la v1 ; **plusieurs vues par photo 360°** (vers le centre de chaque zone et les 8 azimuts, fusionnées à 25°) ; choix glouton qui **maximise la couverture** (zone × secteur d'observation × distance ≤ 20 m / au-delà), primes pour une photo prise **dans le cœur ou à son bord** et pour chaque **mouvement** nouveau (passage d'une séquence dans le cœur, branche d'entrée → branche de sortie) ; toute 360° garde une vue vers le centre et **vers chaque branche** visible (6 au plus si elle est prise dans le cœur, 4 ailleurs), et une 360° restée à une seule vue reçoit après le choix un contrechamp (vue à 90° ou plus qui montre le cœur ou une approche : sur une approche, la branche derrière la caméra) ; photo prise dans l'îlot central d'un giratoire écartée, îlot central supposé opaque ; doublons quasi identiques écartés ; périodes de travaux déclarées écartées (`--exclure-periodes`) ; **40 à 60 photos** pour un carrefour ou un giratoire (240 vues au plus), 12 à 20 pour une section ; **fenêtre d'état** `--depuis`/`--jusqu-au` d'abord, puis, en complément seulement (malus), photos antérieures depuis `--complement-depuis`, marquées « HORS FENÊTRE » partout → `selection.json`, `zones.json`, `couverture.json` (avant v1 / après v2, mêmes zones, même visibilité), `plan_couverture.png`, `plan_couverture_centre.png` |
| `orthos` | `orthos.py` | **kit multi-orthos** : PCRS 5 cm 2022 (si ≥ 50 % de l'emprise), IGN BD ORTHO 20 cm 2024, 2021, 2018, 2015, Pléiades 50 cm 2025, IRC 2024 (végétation en rouge), Plan IGN en plan de contexte ; même emprise L93 et même cadrage pour toutes les couches, **date de prise de vue sur chaque image** (graphe de mosaïquage WFS), zoom du **centre** par couche, tuiles natives des couches plus fines que le pas commun, planches 2 × 2 de quatre dates → `orthos/` (`kit.json`) |
| `pose` | `pose_lot.py` → `comparer_multivues.poser_vue` | pose de chaque vue comme en v1, en parallèle (`--processus`) |
| `rendu` | `rendu_hython.py` (mode par lots) | un appel husk par lot de 40 vues de même résolution (≈ 5 à 6 s par vue au lieu de 14 à 30 s) ; une vue déjà rendue est reprise si sa caméra, son soleil, les échantillons et l'empreinte de la scène (scene_rendu.usda, couches L2 / L2b) sont identiques → `rendus_v2/` |
| `dessus` | `dessus.py` | rendu de dessus du modèle (Karma, caméra quasi orthographique) **\|** ortho (PCRS 5 cm si elle couvre l'emprise, sinon IGN 20 cm) à la même échelle, contours du modèle sur l'ortho (bordures rouges, limites de matériau jaunes, marquages cyan), en tuiles de 740 px, site entier et **centre** → `dessus/` (`dessus.json`) |
| `planches` | `etapes_v2.py` | planche par vue (photo \| rendu \| contours \| arêtes, comme la v1), synthèses de 15 paires, plan des poses, grille `ecarts.json` avec la section **`centre_zone_conflit`** (îlots, guidage, traversées cyclables, pavés, zébras, passages, refuges, autres marquages : ce que dit le modèle, rempli automatiquement ; constat et détail à remplir par l'agent ; sources : zooms du centre des orthos, tuiles de dessus du centre, vues du centre) |
| `dossier` | `dossier.py` | **dossier de compréhension** : `comprehension/LISEZMOI.md` (ordre de lecture et, pour chaque vue, numéro sur le plan, date DANS / HORS fenêtre, position, visée, zones vues, fichiers), `index.json`, `plan_vues_centre.png` et `plan_vues_site.png` (meilleure ortho + zones du modèle + position et visée de chaque photo, numérotées P01…), planches 2 × 2 des vues du centre en tour d'horizon (`photos_non_versionnees/v2/comprehension/centre_pNN.png`) |

Ordre de lecture (LISEZMOI) : orthos datées (dates côte à côte, puis zoom du centre de chaque couche, tuiles
natives) → plans d'index → vue de dessus rendu | ortho → vues du centre par direction d'observation → vues de chaque
branche, îlot et passage → mouvements → remplir `centre_zone_conflit` et la grille des vues. Un élément vu seulement
sur une photo hors fenêtre se confirme sur une photo de la fenêtre ou sur l'ortho la plus proche de la date d'état.

Sorties v2 sous `<sortie>/<site>/` : `selection.json`, `zones.json`, `couverture.json`, `poses.json`,
`ecarts.json`, `rapport.json`, plans (`plan_site.png`, `plan_couverture*.png`), `orthos/`, `dessus/`, `rendus_v2/`,
`comprehension/` (diffusables : rendus, orthos sous licence ouverte, plans sans photo) ; photos de tiers et planches
qui en contiennent sous `photos_non_versionnees/{brut, v2/vues, v2/planches, v2/comprehension}` (jamais versionnées
ni diffusées). Une sélection v1 présente est d'abord copiée dans `v1/` (rien n'est effacé). Le cache des orthos
(réponses WMS, dates des graphes) est sous `<sortie>/_orthos/`.

### Essai v2 sur Paquet Jardin et le Rond-point du Lycée (18/10/2026)

```
python recon/generateur/comparaison/comparer_multivues.py meylan_paquet_jardin --v2 --sites-conf recon/generateur/meylan/paquet_jardin/comparaison_site.json --sortie recon/out/generateur/meylan_paquet_jardin/comparaison --depuis 2024-08-24 --jusqu-au 2025-06-22
python recon/generateur/comparaison/comparer_multivues.py meylan_rp_lycee --v2 --sites-conf recon/generateur/meylan/rp_lycee/comparaison_site.json --sortie recon/out/generateur/meylan_rp_lycee/comparaison --depuis 2024-05-01
```

| | Paquet Jardin (carrefour à feux) | Rond-point du Lycée (giratoire, 5 branches) |
|---|---|---|
| Photos v1 → v2 | 7 → **60** (38 Panoramax, 22 Mapillary ; 30 dans la fenêtre d'état 24/08/2024-22/06/2025, 30 antérieures 2019-2024 en complément : la fenêtre n'a que 32 photos candidates) | 9 → **60** (Panoramax ; toutes dans la fenêtre ≥ 01/05/2024 ; 21 photos prises dans l'îlot central écartées) |
| Vues | 123 (40 photos 360°, 1 à 6 vues chacune ; 16 n'ont qu'une vue : prises 20 à 60 m en dehors du cœur, les autres directions ne montrent aucune zone du site) | 243 (56 photos 360°, 2 à 6 vues chacune) |
| Photos dans le cœur ou à son bord | 9 | 32 (anneau) |
| Mouvements couverts | 3 (Revirée → Vercors, Verdun NE → SO, SO → NE ; les 3 disponibles) | 5 sur 7 disponibles |
| **Centre v1 → v2** (vues qui voient ≥ 20 % de la zone / photos / secteurs d'observation) | zone de conflit : 2 / 2 / 1 (SO) → **54 / 29 / 6** ; approche Verdun SO aveugle → 38 / 26 / 6 | anneau : 4 secteurs sur 5 aveugles, 1 vue → **22 à 66 vues, 13 à 35 photos, 4 à 8 secteurs par secteur d'anneau** ; îlot central aveugle → 34 / 26 / 8 ; approche de l'accès est aveugle → 12 / 7 / 4 |
| Zones aveugles v2 | aucune | aucune |
| Kit d'orthos | PCRS 2022-05-10 (5 cm), IGN 2024-08-09, 2021-08-13, 2018-08-21, 2015-07-03, IRC 2024, Pléiades 2025, Plan IGN de contexte | mêmes couches sans PCRS (hors emprise) |
| Vue de dessus | PCRS 5 cm : centre 4 tuiles, site 16 tuiles ; IGN 20 cm | IGN agrandie à 10 cm : centre 2 tuiles, site 4 tuiles |
| Temps, premier passage à froid | ≈ 22 min (sélection 124 s, orthos 192 s, poses 245 s, rendus 647 s pour 112 vues, dessus 79 s, planches 47 s, dossier 4 s) | ≈ 32 min (sélection 218 s, orthos 216 s, poses 272 s, rendus 1 099 s pour 243 vues, dessus 40 s, planches 95 s, dossier 12 s) |
| Temps, relance (caches, rendus repris) | ≈ 5 min (poses 218 s, rendus repris en 0,2 s, planches 52 s) | — |

Lecture faite par l'agent (kit d'orthos, tuiles de dessus du centre, toutes les vues du centre de Paquet Jardin et 28
vues du centre du Lycée sur les 8 directions, planches photo | rendu), consignée dans `ecarts.json` →
`centre_zone_conflit` de chaque site :
- **Paquet Jardin : ressemblance du centre FAIBLE.** Le cœur du modèle est un enrobé uni bordé de 4 passages et 4
  refuges rectangulaires ; le cœur réel porte des lignes de guidage du tourne-à-gauche Verdun NE → Vercors, la
  traversée de la Chronovélo en rectangles jaunes et logos vélo (côté cœur du passage SO), une traversée cyclable
  verte sur la Revirée, des îlots en pointe à balise J5 et deux îlots d'angle plantés ; les passages du modèle sont
  décalés de 2 à 6 m (le passage SO est posé sur la traversée Chronovélo réelle, `contours_centre_pcrs2022_t00`).
  Les photos du 01/05/2024 (hors fenêtre) montrent le chantier de l'angle ouest : la fenêtre d'état est justifiée.
- **Rond-point du Lycée : ressemblance du centre MOYENNE.** Rayon de l'îlot, largeur de l'anneau, entrées et lignes
  de cédez-le-passage justes (contours du modèle sur l'IGN 2024 à ≈ 1 m) ; habillage faux : le réel est un îlot-parc
  boisé et surélevé ceint d'un muret de 0,6 à 0,8 m, couronne en béton coulé avec caniveau à fentes, B21 face aux
  entrées, passages inférieurs piétons sous l'anneau ; le modèle est un disque de gazon plat bordé de pavés.

Limites connues de la v2 :
- Les positions GNSS restent approximatives (± 4 m annoncés ; Mapillary : `computed_geometry`) : une vue « prise dans
  le cœur » peut montrer la branche qui suit (m323711951, Paquet Jardin). Le plan d'index et la vue elle-même le
  disent ; la pose n'est pas raffinée davantage (principe de l'utilisateur).
- La visibilité d'une zone est géométrique (champ, distance, bâtiments OSM, îlot central d'un giratoire supposé
  opaque) : la végétation, les véhicules et les murets ailleurs ne sont pas modélisés ; « voir » une zone veut dire
  « l'avoir dans le champ, sans bâtiment devant ».
- Les photos hors fenêtre d'état montrent d'autres états : à Paquet Jardin, celles du 01/05/2024 montrent le chantier
  de l'angle ouest. `--exclure-periodes` écarte une période connue de travaux.
- Le Pléiades 2025 n'a pas de date d'image publiée ; le Plan IGN n'est lisible qu'en plan de contexte (0,6 m/px).
- Le temps est surtout celui des rendus (≈ 5 à 6 s par vue sur la RTX 5070, partagée avec les autres lots).

## Entrées (lecture seule)

| Entrée | Rôle |
|---|---|
| `recon/out/generateur/<scène>/` | modèle fabriqué : `l2/sol_*.npy`, `l2/niveaux.json` (bordures), `l2b/peinture_*.npy` (marquages), `rendus/scene_rendu.usda` (scène de rendu : route L2 + L2b, matériaux, socle, lumières) |
| `sites_meylan.json` (versionné) | ancrage de chaque tronçon dans le Lambert-93, point d'intérêt, porteurs connus des séquences |
| `data/vector_gz/osm/` | voies, passages piétons et bâtiments OSM (ancrage, visibilité) |
| API publique Panoramax | recherche par emprise, métadonnées, images SD (netteté) et HD (vues) |
| `recon/pcg/vision/decoupe.py` | vues perspectives des 360° (`vue_equirect`), tuiles natives, contrôle `photos_non_versionnees/` |

## Les quatre étapes

1. **Choix des photos** (`selection.py`) — emprise du modèle ancré + 60 m ; filtres : distance à l'emprise ≤ 60 m,
   date ≥ `--depuis`, soleil ≥ 3° (nuit, crépuscule), statut, précision annoncée ≤ 15 m, photo à plat sans champ,
   position dans un bâtiment OSM ; vues candidates (360° : 8 directions autour de l'axe + la direction du point
   d'intérêt ; à plat : sa direction) notées sur les arêtes du modèle vues (3-40 m, pondérées par la distance, sans
   bâtiment OSM entre la caméra et l'arête) ; netteté (laplacien / contraste) et luminance sur l'image SD des 30
   meilleures (floues < 45 % de la médiane et sombres écartées) ; choix glouton de 6 à 12 photos avec primes de
   diversité : nouveau **quadrant de visée** (dans le sens du tronçon, à contre-sens, vers la gauche, vers la
   droite), nouvelle **position le long** du tronçon (cases de 20 m), nouvelle **position en travers** (chaussée,
   trottoir, piste, accotement, hors modèle), pénalités pour un même point de prise de vue et une même séquence.
   → `selection.json` (id, date, lon/lat, L93, cap, type 360°/plan, porteur, vue, raison du choix ; liste des écartées
   avec le motif). La recherche est en cache (`cache/recherche.json`) : sans `--rafraichir`, tout est déterministe.
2. **Pose** (`pose.py`, `vues.py`) — départ : métadonnées (GNSS, cap Panoramax converti en azimut grille, hauteur par
   défaut du porteur : voiture 2,05 m, vélo ou piéton 1,90 m, téléphone derrière le pare-brise 1,35 m). Porteur :
   table des séquences de `sites_meylan.json` (capot ou sac à dos vus sur les photos, `recon/pcg/enrichir/camera.py`),
   sinon sémantique « transport », sinon vitesse médiane de la séquence. Pour une 360°, **redressement par les
   verticales** (`vues.verticale_360` : segments quasi verticaux de 8 vues de 90°, verticale par moindres carrés),
   appliqué seulement si l'inclinaison dépasse 3°, avec ≥ 30 segments, un résidu ≤ 1° et la même verticale (à 4°
   près) qu'au moins la moitié des autres photos de la séquence (même support de caméra) : la séquence au casque du
   12/01/2025 est inclinée de 16 à 20°, les scènes boisées donnent des verticales fausses. Puis affinage par
   **chanfrein orienté** des arêtes du modèle (bordures, limites de matériau, contours des marquages) sur les
   **segments rectilignes** de la photo (LSD, ≥ 25 px, sous l'horizon, hors porteur, hors bords d'ombre portée), en
   trois niveaux (redressement seul, orientation seule, pose complète), chacun **validé** sur une moitié des segments
   non utilisée pour l'affinage, contre la pose des métadonnées. Garde-fous : déplacement ≤ 5 m, lacet ≤ 10°,
   tangage ≤ 4° (8° caméra portée), roulis ≤ 3° (5°), hauteur ≤ 0,4 m ; une voiture reste sur la chaussée du modèle.
   L'a priori de position est **volontairement serré** (σ = 1,5 m) et la pose complète doit valider nettement mieux
   (+ 0,05) que l'orientation seule, que celle-ci ait franchi le seuil ou non : déplacer la caméra peut « absorber »
   une erreur de description (largeurs, position d'un passage) et la masquer, alors que c'est ce que la comparaison
   doit montrer. Rejet si la validation n'améliore pas le score de plus de 3 % (6 % pour le redressement seul), si un
   garde-fou est atteint ou si l'image du modèle s'écrase (étalement vertical < 50 %) : on garde alors la pose des
   métadonnées. La solution validée est ensuite affinée **localement** sur tous les segments ; la solution finale
   n'est gardée que si elle reste à moins de 1 m et 1,5° de la solution validée (sinon : la solution validée). Indice
   de confiance (validation, recouvrement, nombre de points, stabilité, emprise du modèle dans l'image). → `poses.json`.
3. **Rendu** (`rendu_hython.py`) — couche USD superposée à `rendus/scene_rendu.usda` (rien n'est modifié) : caméra de
   la pose retenue, même champ et même cadrage que la vue photo (1092 px), soleil et ciel physique à la date et à
   l'heure de la photo, exposition fixe pour cette hauteur de soleil ; husk (Karma XPU, 128 échantillons).
   → `rendus/rendu_<id8>.png`.
4. **Planches** (`planches.py`) — par photo, `planche_<id8>.png` (1056 × 1116 px, 4 panneaux réduits de moitié :
   photo | rendu / contours photo cyan, rendu magenta, communs blanc | arêtes du modèle projetées, pose initiale
   jaune, retenue verte, segments de la photo cyan) et les panneaux natifs 1092 px (`vue_`, `superposition_`,
   `aretes_`) ; `planche_synthese.png` (vignettes appariées) ; `plan_site.png` (modèle vu de dessus, positions GNSS et
   retenues, cônes de vue) ; **gabarit** `ecarts.json` (mesures automatiques, profil du modèle à l'endroit regardé,
   rubriques à remplir : géométrie — nombre de voies, largeurs relatives, terre-plein, îlots, bordures —, marquages,
   matériaux, éléments manquants ou en trop). Un nouveau passage garde ce que l'agent a rempli.

## Sorties (non versionnées) : `recon/out/generateur/comparaison/<scène>/`

| Fichier | Contenu |
|---|---|
| `selection.json`, `poses.json`, `ecarts.json`, `rapport.json` | choix, poses, grille d'écarts, mesures et durées ; aucune image |
| `plan_site.png`, `rendus/` | sans photo de tiers |
| `cache/` | réponses de l'API (métadonnées seulement) |
| `photos_non_versionnees/{brut,vues,planches,tuiles}/` | photos (CC-BY-SA, etalab…), vues, planches et tuiles qui en contiennent : **jamais versionnées ni diffusées** |
| `../bilan.json` | résumé par site |

## Ancrage d'un tronçon (`sites_meylan.json`)

Les tronçons de `scenes_meylan/` sont décrits dans un repère local (tronçon droit de 0 à L m). L'ancrage le pose dans
le Lambert-93 : **direction** = droite ajustée sur les voies OSM nommées (sur l'étendue du tronçon), sens donné par
les photos de référence ; **position** = nœuds OSM du passage piéton décrit (`passage_osm`, M24, M27) ou, à défaut,
position GNSS des photos de référence à leur place estimée dans le modèle (`rendu/rendu_l2b.py` `VUES_PHOTO`, M20).
Le diagnostic (écart entre la position GNSS de la photo de référence et sa place décrite, écart de direction photos /
OSM) est écrit dans `selection.json` et `rapport.json`.

## Essai sur les tronçons de l'étape 1 (18/10/2026, après le contrôle indépendant : `CONTROLE.md`)

| Site | Photos (séquences) | Quadrants de visée (*) | Positions | Poses retenues (validées) | Recouvrement 3 px médian | Écart moyen médian | Durée (recherche en cache) |
|---|---|---|---|---|---|---|---|
| S_M20 | 12 (5) | 4 | chaussée, trottoir, accotement, hors modèle | 5 / 12 (orientation 5) | 0,05 → 0,09 | 25,3 → 22,3 px | 270 s |
| S_M24 | 11 (3) | 4 | chaussée, trottoir, piste, accotement, hors modèle | 6 / 11 (redressement 1, orientation 4, complète 1) | 0,14 → 0,25 | 20,5 → 14,1 px | 249 s |
| S_M27 | 12 (4) | 4 | chaussée, trottoir, accotement, hors modèle | 6 / 12 (orientation 4, complète 2) | 0,14 → 0,19 | 17,8 → 14,5 px | 279 s |

(*) 15 vues sur 35 sont des diagonales exactes (± 45°, ± 135°) dont le quadrant est décidé par l'arrondi du calcul
(voir `CONTROLE.md`) ; la couverture « gauche » et « droite » repose surtout sur elles et sur des vues prises hors du
modèle.

Durée : sélection 3-4 s, poses 56-77 s, rendus Karma 179-185 s (≈ 16 s par vue), planches 12-14 s ; un premier
passage ajoute la recherche et les téléchargements (20 à 85 s pour la sélection, ≈ 4 Mo par photo HD). Deux passages
successifs donnent des `selection.json` et `poses.json` identiques (hors durées ; vérifié avant et après la
correction du 18/10/2026).

Le critère « pose affinée améliorant le score de contours sur ≥ 80 % des photos » **n'est pas atteint** (17 / 35,
49 % ; 19 / 35 avant la correction du contrôle, qui acceptait deux poses complètes sans la marge annoncée et
retenait des solutions finales non validées) : mesurée sur des segments non utilisés pour l'affinage, l'amélioration
n'existe que là où le modèle ressemble à la photo ; à l'œil, une partie des 17 poses retenues reste fausse
(`CONTROLE.md`). Dans les autres cas (passage décrit 10 à 20 m trop loin sur M20, piste plus large, carrefours
d'extrémité, rue courbe), l'affinage est rejeté et la pose des métadonnées est gardée : c'est voulu, l'écart vient de la
description et doit rester visible. Sur les segments qui servent à l'affinage, le score s'améliore toujours, par
construction : ce n'est pas une preuve, d'où la validation. Les écarts relevés par photo sont dans `ecarts.json` ;
les principaux :
- M20 : passage piéton réel vers 10-20 m du début du tronçon (et non 30 m), îlot peint central et marquages « 30 » /
  « 50 » non décrits, piste cyclable bidirectionnelle sombre de ≈ 3 m avec axe en tirets à la place d'un « chemin »
  clair de 1,8 m, accotement droit ≈ 4 m (2,5 m décrits), rue courbe au-delà de 50 m ;
- M24 : autres passages à îlot vers 16 et 63 m non décrits, carrefour à l'extrémité s = 0, hors des abords du passage
  le profil réel est bordure | herbe | piste (et non bordure | trottoir béton | piste), BEV en dalles claires
  (sombres dans le rendu), trottoir en grandes dalles ; caméra au casque inclinée de 16 à 20° (redressement) ;
- M27 : très ressemblant au passage (chevrons, refuge, rive en tirets, enrobé fissuré) ; zone hachurée limitée aux
  abords du refuge, rue transversale à gauche vers 65 m, carrefour avec voies de présélection vers 85-100 m,
  trottoir accolé à la piste côté droit absent, accotements ≈ 3 m (2 m décrits).

## Limites connues

- L'indice de confiance n'est qu'un indicateur : une pose « haute » peut rester fausse à l'œil (S_M27, 938c8e8c :
  caméra déplacée de 3 m pour recaler une rive ; S_M24, 9badc00e : caméra éloignée de 2 m de la bordure) ; la
  lecture des planches reste nécessaire.
- Contrôle indépendant du 18/10/2026 (`CONTROLE.md`) : la validation par rangs alternés de segments n'est pas
  indépendante (mêmes lignes physiques dans les deux moitiés) ; la pose complète absorbe encore des écarts de
  description (elle éloigne la caméra de la chaussée de 1,7 à 2,7 m sur les trois cas restants) ; sur les tronçons
  courbes, la position GNSS projetée sur l'axe droit tombe dans une autre bande (photo prise sur la piste, rendu
  depuis la chaussée) ; les vues diagonales ont un quadrant arbitraire.

- Le modèle est un **cas semblable simplifié** (tronçon droit) : l'affinage ne peut aligner que ce qui existe des deux
  côtés ; quand la photo montre autre chose (rue courbe, giratoire, piste plus large), il est rejeté par la validation
  et la pose des métadonnées est gardée — c'est voulu (ne pas « absorber » une erreur de description dans la pose).
- Les arêtes du modèle sont celles du sol, des bordures et des marquages : aucune occlusion par les objets réels
  (voitures, végétation) n'est modélisée ; le chanfrein tronqué et la validation limitent leur effet.
- Le filtre d'ombres (teinte de part et d'autre d'un segment) écarte aussi certaines faces de bordure à l'ombre.
- Le rendu (étape 1 du générateur : route seule) ne montre ni arbres ni bâtiments ; la superposition des contours ne
  doit être lue que sur la route.
