# Simulateur ADAS « Paquet Jardin » v2 : Claude décrit, Houdini fabrique, UE 5.8 place

## 0. Les constats qui fixent l'architecture

- **Le paquet v1 n'utilise pas ses propres données.** `assemble.py` fabrique les bordures en faces verticales (66 136 triangles) et vectorise les marquages depuis le raster. Il ne lit ni `bordures_hauteurs.geojson` (8 413 tronçons) ni `assets/specs/bordures.json` (18 profils NF). Les données sont riches, mais il n'existe aucune description *paramétrique*. C'est le premier chantier.
- **Houdini Engine est déjà disponible.** J'ai lu `HoudiniEngine.uplugin` dans `.../Houdini Engine/Unreal/21.0.700/5.8/` et dans `D:/ClaudeADAS/Plugins/HoudiniEngine/` (copié le 10/10 à 01:03). Les deux portent `Version 22000459`, `"3.0 - H22.0.459"`. Le plugin vise donc bien Houdini 22.0.459, et l'éditeur le charge. L'hypothèse « Houdini Engine seulement pour la 21.0.700 » est fausse. En revanche, le calcul d'un HDA en session Indie n'a pas encore été testé.
- **Le pilotage MCP de l'éditeur fonctionne déjà.** Le serveur répond sur `http://127.0.0.1:8000/mcp`. PCGToolset expose 30 outils, mais il n'y a ni import, ni pose d'acteurs, ni capture : il faut activer EditorToolset et écrire un toolset Python maison.
- **Les assets CARLA se chargent dans UE 5.8.3** (CC-BY 4.0, licence vérifiée dans `D:/CARLA_Assets/LICENSE`). Un test de 115 assets sur 115 s'est chargé sans erreur. Les StaticMesh et les matériaux n'ont aucune dépendance `/Script/Carla`.
- **Aucune bibliothèque ne contient d'assets français** : bordures en éléments de 1 m, flèches IISR, panneaux FR. Ils sont à fabriquer.
- **Aucune image ouverte ne montre le carrefour après les travaux.** La photo la plus récente du cœur date du 31/08/2025. Les HD Panoramax sont absentes du PC (seules 5 HD dans `C:/Users/flori/Documents/ChatGPT/ADAS/SAM3/data/raw`). Sans photo, 1 582 m de bordures, 70 surfaces et 424 marquages restent des a priori.

## 1. Architecture

### 1.1 Le principe en trois étages

```
 Données du dépôt (paquet v1, data/sites/*/vector, .xodr)  ─┐
 Normes (IISR 7e partie, NF bordures, pratique)            ─┤  [A] DÉCRIRE (Python, déterministe)
 Panoramax + nouvelle prise de vue + photos utilisateur    ─┤      base ⊕ enrichi ⊕ arbitré → description_scene_v2 (vectorielle, sourcée)
 Décisions de Claude (a priori justifiés)                  ─┘
                         │  validation JSON Schema + contrôles géométriques
                         ▼
 [B] FABRIQUER (hython Houdini 22, HDAs .hdalc, sans GUI, graine = hash(id))
     ├─ géométrie propre au site → USD : sol, trottoirs, caniveaux, remplissages d'îlots, lignes et zébras
     ├─ prototypes de bibliothèque → USD/FBX une seule fois : éléments de bordure, flèches IISR, figurines
     └─ semis de points → points/*.json, zones/*.json (asset_id, pose, échelle, graine, données d'instance)
                         ▼
 [C] PLACER ET SIMULER (UE 5.8.3, D:/ClaudeADAS, piloté par MCP)
     import USD → acteurs ; graphes PCG : points → Static Mesh Spawner (MeshSelectorByAttribute sur bibliotheque.json)
     zones → Create Polygon 2D → Surface Sampler (herbe, feuilles, gravillons épars) ; matériaux, Lumen, soleil, capteurs
                         ▼
 [D] VALIDER : vues aux poses Panoramax recalées, planches photo | rendu | superposition, revue indépendante
```

Partage des rôles :
- **Claude** n'écrit jamais de géométrie à la main. Il produit et enrichit les attributs, chacun avec sa provenance.
- **Houdini** n'invente rien. Chaque valeur vient d'un attribut ou d'une règle de spec nommée (`src: "regle:bordures.R3"`).
- **UE** ne fait que résoudre les `asset_id` dans la bibliothèque et disperser selon les règles.

### 1.2 Les composants

| Composant | Rôle | Entrée | Sortie |
|---|---|---|---|
| `decrire/` (Python + numpy) | Convertit le paquet en entités paramétriques | `package/donnees/*.geojson`, `.xodr`, `data/sites/paquet_jardin/vector/gam_*` | `description/base/*.geojson` |
| `enrichir/` | Pipeline Panoramax et terrain : pose, sélection, découpes, extraction par vision, double vérification | photos, poses, entités | `description/enrichi/*.json` (attributs + preuves) |
| `composer.py` + `valider.py` | Fusion par priorité (arbitré > enrichi vérifié deux fois > base) et contrôles | 3 couches | `description_scene_v2.json` (manifeste) + couches résolues |
| HDAs `pj_*` + `fabriquer.py` | Fabrication déterministe | description résolue + specs | `fabrique/*.usda`, `points/`, `zones/`, `manifest_fabrication.json` (hashes) |
| Toolset UE `pj_tools` | Outils MCP : import_usd, charger_points, lancer_pcg, poser_camera, capturer, run_python | fichiers `fabrique/` | niveau `PJ_2026`, rendus |
| Graphes PCG `PG_*` | Placement depuis la bibliothèque | points, zones, `DT_Bibliotheque` | instances ISM/HISM (Nanite) |
| `validation/` | Vues de contrôle, planches, mesures, grille de revue | poses, rendus, photos | `vues/`, `rapports/` |

### 1.3 Description sémantique v2

Choix de format :
- **Un FeatureCollection GeoJSON par famille**, en Lambert-93 (lisible dans QGIS), plus un manifeste `description_scene_v2.json` qui contient le site, l'origine O, la saison, les références, les règles PCG et l'index des preuves.
- **Version du schéma** : `description_scene_v2/0.1` (semver). Les identifiants sont stables (`K-`, `S-`, `I-`, `ML-`, `MF-`, `A-`, `SIG-`).
- **Provenance** : chaque entité porte `prov: {attribut: {src, ref, conf, date}}`. Les sources possibles sont `gam | pcrs2019 | lidar2021 | xodr | ortho2022 | plan2025 | panoramax:<id>/<tuile> | terrain2026 | photo_utilisateur | norme:<art> | a_priori:<règle>`, et la confiance vaut `haute | moyenne | faible`.

Familles et champs clés :

- **`bordures`.** LineString de l'arête avant haute, dédoublonnée (le GAM trace deux arêtes par bordure). Champs :
  - `face_vue` ;
  - intervalles `[{s0, s1, profil, vue_m}]`, tirés de `regles_affectation` puis compressés ;
  - `abaisses [{type: traversee|charretiere|quai, s0, s1, vue_m, raccords, bev}]` ;
  - `materiau` (beton_gris, beton_clair, granit, peint_blanc, brique/pavé) et `finition` ;
  - `element_m: auto|1.0|0.5`, `joint_mm` (6 par défaut), `phase_m` ;
  - `caniveau {profil: CS1|CS2|CS3, cote}` ;
  - `aspect {epaufrures, mousse_joints, herbe_joints, salissure}` ;
  - `z_ref: fil_eau_2021|modele_2026`.
- **`surfaces`.** Polygone, classe, et `revetement {materiau_id, appareillage, module_cm, joints_sciés_m, age, salissure}`. Aussi `niveau {ref, dz_m, devers_pct}` et `bords: [ids bordures]`. Les 209 limites d'origine raster sont recalées sur l'arête arrière des bordures.
- **`ilots`.** Champs :
  - `surface` ;
  - `remplissage {materiau_id: brf_bois_concasse|gravier_concasse_6_10|galets_20_40|gazon_tondu|herbe_haute|massif|paves|enrobe, epaisseur_m, retrait_sous_bordure_m (0,03–0,05), debordement}` ;
  - `ceinture` (liste d'identifiants de bordures), `nez {rayon_m, peint}`, `objets_portes`, `plantation`.
- **`marquages`.**
  - `lignes` : ancrées sur `road/lane/s0/s1/t_off`, avec `modulation`, `largeur_m`, `phase_m` et `usure`.
  - `transversales`, `passages` (axe, bande, intervalle, longueur, nombre de bandes, coupures).
  - `fleches` et `symboles` : `gabarit` IISR + pose.
  - `zones` (hachures, chevrons, damiers, zigzags) et `fantomes`.
  - `lien_v1: [MQxxxx]` pour la traçabilité des 996 marquages v1.
- **`vegetation`.**
  - `arbres` : essence, classe de silhouette, `asset_id`, h, couronne, fût, fosse, saison.
  - `massifs` : sol, palette `[{asset_id, part, h}]`, densité, marge, graine.
  - `haies` : axe, h, épaisseur.
  - `herbe` : type, hauteur, feuilles mortes.
- **`signaux` et `mobilier`.** Code FR, gamme, support, `h_bas_m`, azimut de la face, panonceaux, `xodr.signal`. Lien explicite entre têtes de feux et signaux.
- **`ponctuels_sol`.** Tampons, avaloirs, BEV 40×40, boucles de détection.
- **`regles_pcg`.** Herbe dans les joints, exclusions (triangles de visibilité aux traversées, h ≤ 0,6 m), dégagements sous panneaux et feux, feuilles mortes d'octobre.

Les specs (dans `assets/specs/`) sont la seule source de géométrie normative :
- `bordures.json` v2 : joint 6 mm et élément de 0,994 m (Sepa), chanfreins CS 15×15 mm, ajout de CS3, AC1, TU et du quart de rond R0,25, T4 signalé comme non vérifié ;
- `marquages_geometrie.json` (nouveau) : modulations, u = 5 ou 6 cm, polygones exacts des flèches de l'annexe B, rabattement, hachures 0,50/1,35/26,565°, zigzag, triangle, figurine vélo vectorisée une fois depuis l'image de l'annexe ;
- `materiaux_sol.json` (nouveau) ;
- `regles_pcg.json` (nouveau).

### 1.4 Fabrication dans Houdini (hython, 22.0.459 Indie)

- **`pj_bordure_prototypes`** (lancé une fois, versionné). Pour chaque profil de `bordures.json` :
  - un élément de 0,994 m, 0,494 m et 0,16 m, avec arêtes arrondies ou chanfreinées ;
  - 3 variantes d'épaufrures ;
  - chartières gauche et droite (biseau de la vue courante à 0,02 m), raccords T2/A2 et quarts de rond de nez d'îlot.

  Soit environ 50 meshes, exportés vers `/Game/PJ/Lib/Bordures/SM_<profil>_<L>_v<n>` (Nanite).
- **`pj_bordure_pose`.** Le pas suit le rayon de courbure : 1,00 m si R ≥ 12 m, 0,50 m si 3 ≤ R < 12 m, pièces courbes ou de 0,16 m en dessous. La pose part d'un point dur (chartière, angle, nez) et finit par un **élément de coupe**. Les joints sont phasés sur l'observé quand il existe. Le Z vient du fil d'eau plus la vue (ou de `h_modele_2026` en zone de travaux). Jitter de ±2 mm et ±0,3°. Les données d'instance portent usure, salissure, mousse et teinte. Sortie : `points/bordures.json` (environ 8 500 instances), plus les caniveaux en éléments CS de la même façon.
- **`pj_sol`.**
  - Chaussée : coupée à la face avant au fil d'eau.
  - Trottoirs : coupés à l'arête arrière de la bordure (axe décalé de la largeur de tête du profil), devers de 1 à 2 % vers la chaussée, rampes d'abaissé ≤ 5 % (8 % sur 2 m au plus).
  - Béton désactivé : joints sciés en géométrie tous les 3 à 4 m.
  - Dalles et pavés : UV alignées sur le module.
  - Terrain issu de la heightmap à 10 cm. Le tout est étanche et sans trou.

  Sortie : `fabrique/sol.usda`, avec matériaux nommés par `materiau_id` et couleur de sommet (R usure, G salissure, B graine).
- **`pj_ilot`.** Remplissage légèrement bombé, posé 3 à 5 cm sous le dessus de la ceinture, puis zone `zones/ilots.json` pour la dispersion des copeaux ou gravillons (débordement sur la chaussée) et des plantations.
- **`pj_marquages`.**
  - Lignes : générées depuis les bords de voie OpenDRIVE (échantillonneur paramPoly3 + laneOffset + width en Python, écart médian de 7 mm au levé), découpées selon la modulation et phasées sur les 155 tirets GAM.
  - Arrêt à 0,50 m des passages ; zébras, hachures et zigzags générés depuis leurs paramètres.
  - Rubans triangulés posés à +3 mm, UV en mètres → `fabrique/marquages.usda`.
  - Flèches, figurines vélo, PMR et triangles : **prototypes de bibliothèque** posés par `points/marquages_symboles.json`.
  - La géométrie relevée n'est gardée que pour les cas atypiques, simplifiée (Douglas-Peucker 1 cm, pas de marche d'escalier).
- **`pj_vegetation`.** Points discrets uniquement (453 arbres, massifs selon la palette, haies en coques d'extrusion, herbes de joints) → `points/vegetation.json`. Les dispersions denses (herbe, feuilles mortes) restent dans le PCG d'UE, à partir des zones.
- **Déterminisme.** Graine = hash(id + version de règle). `manifest_fabrication.json` enregistre le hash de la description, les versions des HDAs, la version de Houdini et le hash de chaque sortie. Deux exécutions donnent des sorties identiques à l'octet.

### 1.5 Pont vers UE et PCG

| Route | Rôle | Décision |
|---|---|---|
| **hython en batch → fichiers** | Chemin canonique, reproductible, versionné, testable sans éditeur | **Principal** |
| Houdini Engine 22 (nœud PCG « Houdini Digital Asset ») | Réglage interactif d'un HDA dans l'éditeur | Optionnel, après test du calcul en Indie |
| PointInstancer USD pour les assets de bibliothèque | À éviter : UE recrée les meshes au lieu de référencer les UAssets | Refusée |

- **USD → UE.** Pour le sol, les marquages et les îlots, UE 5.8 embarque USD 0.26.03 et Houdini 22 la 0.26.05 : les fichiers sont compatibles. Les matériaux sont remappés par `materiau_id` vers `/Game/PJ/Materials/MI_<id>`, soit par le contexte de rendu `unreal` (`info:unreal:sourceAsset`), soit par un script après import.
- **Points → PCG.** Il n'existe pas de lecteur CSV ou JSON natif. Un test en phase 0 départagera trois voies :
  - (a) PCG Python Data Processor (PCGPythonInterop) ;
  - (b) Load Alembic (PCGExternalDataInterop, preset CitySample, Houdini écrit l'`.abc` nativement) ;
  - (c) un outil `pj_tools.charger_points` qui écrit un PCGDataAsset, relu par « Load PCG Data Asset ».

  Le JSON reste le format de référence, lisible et comparable.
- **Format des points** :

  ```
  {schema:"pj_points/0.1", famille, source_hash,
   points:[{id, asset, p:[x,y,z] (m, local O, Z haut), rpy_deg:[r,p,y], s:[sx,sy,sz], graine, cd:[...]}]}
  ```

- **Repère unique.** Local = L93 − O (917279.43 / 6460289.98 / 216.30). Côté UE : X = x·100, Y = −y·100, Z = z·100, yaw_UE = −yaw. C'est la même convention que CARLA et OpenDRIVE. GeoReferencing porte EPSG:2154 et l'origine. La conversion vit dans une seule fonction, testée sur des mires.
- **Graphes PCG.** Ils sont décrits dans le dépôt (`ue/graphes/*.json`) et recréés par Claude via `PCGToolset.CreateGraph/AddNode/ConnectNodePins` :
  - `PG_Bordures` : points → MeshSelectorByAttribute ;
  - `PG_Symboles` ;
  - `PG_Arbres` ;
  - `PG_Massifs` ;
  - `PG_Herbe` : zones → Polygon2D → Surface Sampler, densité et hauteur par attribut, exclusions ;
  - `PG_Joints` : herbe et mousse aux joints ;
  - `PG_Ilots` : copeaux et gravillons de bord.
- **Bibliothèque.** `assets/bibliotheque.json` est importé dans UE en `DT_Bibliotheque`. Champs : `asset_id`, `ue_path`, `ue_path_secours`, source (carla, citysample, pve, cc0, maison), licence, attribution, dimensions, convention de pivot (base centrée, +X vers l'avant), `classe_semantique`, Nanite, saisons.
- **MCP.**
  - `.mcp.json` du dépôt : `{"mcpServers":{"unreal-mcp":{"type":"http","url":"http://127.0.0.1:8000/mcp"}}}`.
  - Plugins à activer dans `ClaudeADAS.uproject` : EditorToolset (dont CaptureViewport), PCGPrimitives, PCGPythonInterop, PCGExternalDataInterop, PCGGeometryScriptInterop, USDImporter, ProceduralVegetationEditor, GeoReferencing, MovieRenderPipeline, SunPosition.
  - Toolset Python `pj_tools` dans `Content/Python/init_unreal.py` (ToolsetDefinition + `@toolset_registry.tool_call`), dont la source est versionnée dans `recon/pcg/ue/`.
- **Runtime ADAS (UE 5.8 sans CARLA).**
  - Niveau `PJ_2026` : Lumen, soleil de Meylan à la mi-octobre 2026 avec heure paramétrable, exposition fixe pour les capteurs.
  - Véhicule ego Chaos, rig caméra physique, classes sémantiques par stencil (depuis `classe_semantique`).
  - Vérité terrain : voies depuis le `.xodr` (pas d'importeur xodr dans UE, il reste la référence logique, dans le même repère), boîtes 2D et 3D.

### 1.6 Arborescence

```
recon/pcg/
  README.md                       repère, conventions, commandes
  schema/  description_scene_v2.schema.json, pj_points.schema.json, extraction_photo.schema.json
  decrire/ xodr_echantillonne.py, bordures.py, surfaces.py, ilots.py, marquages.py, vegetation.py, signaux.py, composer.py, valider.py
  enrichir/ poses_pnp.py, selection.py, decoupes.py (bandes de bordure + FFT, patchs ortho), extraire.py, consolider.py
  houdini/ fabriquer.py (CLI hython), hda/pj_*.hdalc, sop/*.py
  ue/      pj_tools/init_unreal.py, charger_points.py, importer_usd.py, graphes/*.json, niveau.py
  validation/ vues_controle.py, planches.py, mesures.py, grille_revue.md
assets/specs/{bordures.json v2, marquages_geometrie.json, materiaux_sol.json, regles_pcg.json}
assets/bibliotheque.json ; assets/lib/<asset_id>/{meta.json, sources maison}   (aucun .uasset tiers dans git)
recon/out/paquet_jardin/v2/
  description/{base,enrichi,arbitre}/*.geojson, description_scene_v2.json
  fabrique/{sol,marquages,ilots}.usda, prototypes/*.usd, points/*.json, zones/*.json, manifest_fabrication.json
  vues/<photo_id>/{rendu.png, planche.png, mesures.json}, rapports/
D:/ClaudeADAS/Content/{PJ/{Lib,Materials,PCG,Maps}, Carla/... (chemins /Game/Carla conservés), CitySample/...}
```

Les photos et les tuiles restent hors git (`data/raw`). Le dépôt ne garde que les identifiants et les boîtes en pixels.

### 1.7 Validation

1. **Poses.** Pose a priori (L93, yaw = azimut − 2,0086°), puis PnP sur 5 à 10 points d'appui : pieds de mâts LiDAR, blocs CHARTIERE, coins de zébras. On accepte si l'erreur moyenne est ≤ 0,5° en 360° ou ≤ 8 px à plat. Le test sur e5d79de9 passe de 9,4° à 0,54° après ajustement.
2. **Vues de contrôle.** Une CineCamera UE par pose, avec les mêmes intrinsèques. Pour une photo 360°, on extrait des vues perspective à 90° aux azimuts utiles, côté photo et côté rendu.
3. **Planches.** Photo | rendu | superposition des arêtes vectorielles projetées (bordures, marquages).
4. **Mesures.** Erreur de reprojection des arêtes, IoU par classe entre les masques SAM 3.1 de la photo et le rendu sémantique UE. On ne compare que les entités valides à la date de la photo.
5. **Revue indépendante.** Un agent séparé, qui n'a vu ni le code ni la description, reçoit des paires dans un ordre aléatoire. Il note de 0 à 3 : joints et profil des bordures, abaissés, matériau du trottoir, remplissage des îlots, forme des marquages, végétation, lumière. Seuil : moyenne ≥ 2 et aucun 0. L'utilisateur valide ensuite.

## 2. Plan par phases (le sol réaliste arrive dès la phase 1)

**Phase 0 : socle et essais (3 à 5 jours)**
- Livrables :
  - plugins UE activés, `.mcp.json`, toolset `pj_tools` ;
  - copie CARLA (Vegetation, GenericMaterials, Decals/Road et Pavement, Static/Static, Fence, Pole et les 2 MPC CarlaParameters et WeatherMaterialParameters) dans `Content/Carla/`, puis ResavePackages ;
  - migration des matériaux City Sample utiles dans le projet UE ;
  - essai du transport des points (voies a, b, c) ;
  - essai d'import USD avec remappage des matériaux ;
  - 5 mires aux points L93 connus ;
  - essai Houdini Engine 22 (HDA trivial en Indie).
- Critères :
  - Claude, via MCP, importe un USD, place 3 assets depuis un JSON et récupère une capture ;
  - erreur de position des mires ≤ 1 cm ;
  - SM_Oak_M_v1 s'affiche correctement sous Lumen ;
  - la voie de transport retenue est documentée.

**Phase 1 : sol réaliste sur une zone pilote (1 à 2 semaines)**
- Zone proposée : refuge TPC NE + trottoir Verdun NE (60 m) + une traversée + une entrée charretière + un îlot BRF et un îlot gravier. Les HD locales e5d79de9 et ab4cfacd la couvrent, et les photos de référence de l'utilisateur s'y appliquent.
- Livrables :
  - schéma 0.1 (bordures, surfaces, îlots, ponctuels, preuves) et convertisseurs ;
  - `bordures.json` v2 et `materiaux_sol.json` ;
  - HDAs `pj_bordure_prototypes`, `pj_bordure_pose`, `pj_sol`, `pj_ilot` ;
  - matériaux : béton de bordure en 3 teintes, enrobé chaussée et trottoir, BEV, gazon, gravier, BRF ;
  - graphes `PG_Bordures`, `PG_Ilots`, `PG_Joints` ;
  - 6 vues et leurs planches.
- Critères :
  - joints visibles tous les 1,00 m (0,50 m si R < 12 m) et élément de coupe en fin de file ;
  - vue de 0,02 ± 0,005 m aux traversées, rampe ≤ 5 % ;
  - aucun interstice > 5 mm entre bordure et trottoir ;
  - remplissage 3 à 5 cm sous la bordure ;
  - sorties identiques à l'octet sur 2 exécutions ;
  - note de revue ≥ 2 sur bordures, trottoirs et îlots, et accord de l'utilisateur.

**Phase 2 : marquages IISR sur tout le site (environ 1 semaine)**
- Livrables :
  - `marquages_geometrie.json`, `xodr_echantillonne.py`, `pj_marquages` ;
  - prototypes : flèches TD, G, D, TD+G, TD+D et rabattement, figurine vélo, PMR, triangle ;
  - roadMarks des 10 voies cyclables dans la description ;
  - table de correspondance v1 → v2.
- Critères :
  - les 996 marquages v1 sont tous rattachés (générés, gardés simplifiés ou retirés avec justification) ;
  - 0 contour en escalier ;
  - phase des tirets par rapport au GAM : p95 < 0,10 m ; écart latéral p95 < 0,05 m ;
  - flèches identiques aux polygones IISR ;
  - largeurs T3 harmonisées (0,12 ou 0,15, documenté).

**Phase 3 : sol complet du site (1 à 2 semaines)**
- Livrables :
  - 8,4 km de bordures dédoublonnées, 656 lignes, abaissés en intervalles (192 drapeaux, 21 CHARTIERE, 13 zones, 15 accès riverains) ;
  - caniveaux GAM (138,8 m) et caniveaux par défaut ;
  - 471 surfaces recalées ;
  - BEV, tampons et avaloirs, décalques de reprises et de fissures (CARLA, CC-BY) ;
  - terrain et talus.
- Critères :
  - couverture ≥ 98 % des lignes de bordure GAM dédoublonnées ;
  - sol étanche (0 trou) ;
  - ≥ 60 i/s en 1080p sur la RTX 5070 avec Lumen ;
  - planches à au moins 6 poses Panoramax.

**Piste P : enrichissement Panoramax et terrain, en parallèle dès la phase 1 (accord requis, voir §3)**
- Livrables :
  - téléchargement HD (61 photos à partir de mai 2025, 183 Mo ; puis les séries 2024-05, 2024-08 et 2025-01) ;
  - poses PnP et sélection par score entité × photo ;
  - bandes de bordure dépliées avec FFT (période des joints) et patchs orthorectifiés ;
  - extraction par vision selon un schéma JSON, en deux passes indépendantes plus arbitrage ;
  - troisième vote SAM 3.1 + DINOv2 pour les matériaux ;
  - couche `enrichi/` ;
  - intégration de la nouvelle prise de vue de l'utilisateur dans le même pipeline (`src: terrain2026`).
- Critères :
  - ≥ 80 % des photos 360° retenues avec erreur moyenne ≤ 0,5° ;
  - chaque attribut enrichi cite sa photo et ses pixels ;
  - les zones de travaux 2025 passent de `a_priori` à `observé` après la prise de vue.

**Phase 4 : végétation et dispersion PCG (1 à 2 semaines)**
- Correspondances :
  - Quercus → SM_Oak, Fraxinus → SM_WhiteAsh, Acer → SM_Maple ;
  - Populus, Carpinus, Tilia et Corylus → PVE (Aspen, Beech, NorwayMaple, Hazel), plus un peuplier fastigié maison ;
  - feuillus non identifiés → mélange Oak/Maple choisi par la hauteur LiDAR ;
  - arbustes → SM_Bush_L/M ;
  - herbes et adventices CC0 (Poly Haven), si le téléchargement est accordé ;
  - haies (646 m) et palettes de massifs ;
  - saison d'automne : teinte des feuilles et feuilles mortes ;
  - graphes `PG_Arbres`, `PG_Massifs`, `PG_Herbe`.
- Critères :
  - 453 arbres posés ;
  - |h_asset − h_LiDAR| ≤ 15 % pour 90 % des arbres ;
  - aucune végétation > 0,6 m dans les triangles de visibilité, aucune sur la chaussée ;
  - note de revue ≥ 2.

**Phase 5 : signalisation, mobilier et éclairage français (environ 2 semaines)**
- Livrables :
  - assets maison : les 20 types de `panneaux.json` (faces PNG), feux R11v, R12 et R13c, mâts, 42 lampadaires, potelets, barrières, abri ;
  - signaux `country=FR` liés au `.xodr` ;
  - réconciliation des positions entre `instances.json` et `panneaux.json`.
- Critères : 28 panneaux sur 28 et 13 supports de feux sur 13 posés, conformes aux photos Panoramax (filtrées par date).

**Phase 6 : runtime ADAS et recette**
- Livrables : véhicule ego, rig caméra, rendu sémantique et profondeur, export de vérité terrain, toutes les vues de contrôle valides, rapport de revue indépendante.
- Critères : une séquence capteur reproductible, une vérité terrain cohérente avec le `.xodr` (p95 ≤ 5 cm) et l'accord final de l'utilisateur.

## 3. Décisions réservées à l'utilisateur

| # | Décision | Défaut recommandé |
|---|---|---|
| 1 | Zone pilote de la phase 1 et cible de performance | Refuge TPC NE + Verdun NE ; 60 i/s en 1080p sur la RTX 5070 |
| 2 | Télécharger les HD Panoramax (183 Mo, puis 567 Mo au total) | Oui, en commençant par les 183 Mo |
| 3 | Nouvelle prise de vue sur place (environ 30 min, 250 à 400 photos, protocole de l'inventaire Panoramax) | Oui. C'est la seule source de l'état 2026. |
| 4 | Télécharger des assets CC0 : ambientCG WoodChips001-003 et graviers, Poly Haven grass_medium_01/02, adventices, shrub_01-04, tree_stump | Oui, avec la liste précise soumise avant le téléchargement |
| 5 | Remplissage réel de chaque îlot et de la TPC (BRF, gravier, gazon, enrobé) et matériau des bordures neuves | Vercors en gravier (constat coeur-31), T2 béton clair en éléments de 1 m ; à confirmer sur un tableau à remplir |
| 6 | Route Houdini | Batch hython comme référence ; Houdini Engine 22 en interactif seulement |
| 7 | Conditions Houdini Indie (moins de 100 k$ de revenus, fichiers .hdalc) et installation de SideFX Labs pour H22 (outils tree_* et biome_*) | Garder Indie ; Labs H22 à installer seulement si PVE et CARLA ne suffisent pas |
| 8 | City Sample : garder les assets uniquement dans UE ; arrêter le look-dev Karma `recon/pc/houdini/lookdev_citysample.usda` | Oui ; remplacer par du CC0 côté Houdini |
| 9 | Versionnement : D:/ClaudeADAS hors git ; seuls les scripts, la description, les specs et les sources maison sont versionnés | Oui |
| 10 | Largeur d'unité u (5 ou 6 cm) et gabarits des flèches (IISR ou mesurés GAM, plus étroits) | Largeurs mesurées et u = 6 cm sur Verdun ; flèches IISR sauf preuve photo contraire |
| 11 | Périmètre « simulateur » : UE 5.8 seul (capteurs + vérité terrain) ou intégration CARLA 0.10 plus tard | UE 5.8 seul pour l'instant |
| 12 | Ajouter `.mcp.json` au dépôt et activer les plugins dans `ClaudeADAS.uproject` | Oui |

### Décisions prises (10 octobre 2026)
- **D2, téléchargements** : accordé. Les 204 photos HD Panoramax (518 Mo) et 3 131 tuiles sont dans `data/raw/panoramax/paquet_jardin/`, non versionnées.
- **D3, prise de vue sur place** : reportée, à faire seulement si l'absence de photos après travaux bloque vraiment. Les entités neuves restent marquées `a_priori`.
- **D4, CC0** : accordé pour les textures. Les 25 matériaux du manifeste sont dans `assets/lib/materiaux/` ; le BRF (WoodChips ambientCG) est ajouté au manifeste.
- **D6, Houdini → UE** : l'utilisateur reste sur Houdini 22. Le plugin officiel Houdini Engine for Unreal v4.0.2 (H22.0.459, UE 5.8 Win64) est installé dans `D:/ClaudeADAS/Plugins/HoudiniEngine`, et une session HAPI a été testée en Indie. La voie batch hython → fichiers reste la référence reproductible.
- **D8, City Sample** : uniquement dans Unreal. Les rendus Karma faits avec ses textures restent locaux (`recon/pc/rendus/*citysample*/`, ignoré par git) ; côté Houdini, on passe au CC0.
- **D12** : accordé. L'éditeur peut être fermé et relancé par Claude pour la configuration.

## 4. Risques

| Risque | Impact | Parade |
|---|---|---|
| Aucune image après les travaux ; 19 % des bordures et 70 surfaces en a priori | Matériaux ou remplissages faux | Prise de vue (D3), photos de l'utilisateur, `src: a_priori` visible dans les rapports |
| Poses Panoramax à ±4–5 m ; altitude GPS fausse | Comparaisons trompeuses | Recalage PnP obligatoire, seuil 0,5°, comparaison filtrée par date |
| Plugins UE expérimentaux (MCP, PCGToolset, PVE, PCGPythonInterop) | Casse d'API | Fichiers comme référence, UE figé en 5.8.3, graphes décrits en JSON et reconstructibles |
| Calcul Houdini Engine 22 en Indie non testé ; Labs absent pour H22 | Blocage de l'interactif | Hors du chemin critique (route batch) |
| Arbres CARLA anciens (low-poly, sans Nanite, feuilles masquées sous Lumen, UV NaN sur SM_Acer_02, 13 références cassées) | Végétation peu réaliste | Écarter les modèles low-poly ; utiliser PVE et le CC0 ; test visuel en phase 0 |
| Incohérences de specs : T3 à 0,12 ou 0,15 ; joints de 3–5 ou 6–8 mm ; chanfreins CS ; T4 et T3 non confirmés | Dimensions erronées | Specs v2 sourcées, paramètres exposés, contrôle par FFT des joints sur photo |
| Scripts `recon/stages` absents | Couches de base non régénérables | La v2 part des sorties du paquet et des vecteurs de `data/sites` |
| Erreur de repère (inversion de Y, convergence des méridiens) | Décalages invisibles | Une seule fonction de conversion, mires de la phase 0, test unitaire |
| Performance (millions de brins d'herbe, environ 8 500 éléments de bordure) | Moins de 60 i/s | HISM et Nanite, partitionnement PCG, densité ajustée à la distance |
| Licences : City Sample utilisé hors UE (Karma), attribution CC-BY CARLA, PVE réservé à UE | Non-conformité | D8, `meta.json` d'attribution, aucun .uasset tiers ni .hdanc CARLA dans git |
| État git : `charger_paquet_jardin.py` modifié et `recon/pc/` non suivi (pas de mon fait) | Conflits | À clarifier avant le premier commit v2 |
| Ampleur du projet (« très très complexe ») | Dérive | Phases livrables, zone pilote d'abord, critères chiffrés, revue à chaque phase |

Aucun fichier du dépôt n'a été modifié. J'ai seulement vérifié en lecture :
- `D:/ClaudeADAS/Plugins/HoudiniEngine/HoudiniEngine.uplugin` et `C:/Program Files/Side Effects Software/Houdini Engine/Unreal/21.0.700/5.8/HoudiniEngine/HoudiniEngine.uplugin` : `"Version": 22000459`, `"VersionName": "3.0 - H22.0.459"` ;
- le contenu de `D:/ClaudeCode_RoadCreation/recon/`.