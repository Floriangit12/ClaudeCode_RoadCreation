# Guide PC — carrefour Paquet Jardin (Meylan), état octobre 2026

Ce paquet contient la reconstruction 3D du carrefour (av. de Verdun RD1090 / ch. de la Revirée /
av. du Vercors) sur un carré de 300 m. Elle est faite à partir de données ouvertes (levés
topographiques de la Métropole, plan du projet 2025, ortho 5 cm 2022, LiDAR HD 2021, OSM 2026,
photos Panoramax) et vérifiée visuellement. Ce guide décrit la suite **sur ton PC** :
**Houdini 22** pour raffiner, **Unreal Engine 5.8** pour le simulateur, et ta **librairie
d'assets** (CARLA, Fab, fabrication maison).

## Version du paquet : v1 (9 octobre 2026)
| Élément | État dans la v1 |
|---|---|
| Surfaces (chaussée, trottoirs, îlots, pistes, espaces verts) | **État 2026** : terre-plein planté et refuge sur Verdun SO, îlot du Vercors, bretelle supprimée, quais de bus déplacés. Double vérification en cours. |
| Relief, bordures | **Vérifié** sur le LiDAR : pentes et dévers à ±2 cm, hauteurs de bordure mesurées |
| Objets (arbres, feux, panneaux, éclairage, mobilier, bâtiments) | **Vérifié deux fois puis corrigé**. Positions et hauteurs réelles, volumes provisoires. Les objets déduits faute de photo après travaux portent le statut « à vérifier ». |
| OpenDRIVE | **Vérifié deux fois**, aucune anomalie au contrôle ASAM QC (dernière correction en cours) |
| Marquages | **Provisoires** : version de travail, l'atelier est en cours de finalisation |
| Texture du sol | **Provisoire** : ortho 2022 brute, donc anciens marquages et voitures visibles sur les zones non refaites. Les zones refaites en 2025 sont en couleur unie. |

**Ce que contiendra la v2** (récupérable par `git pull`, puis réimport) : texture nettoyée et étalonnée sur les photos (marquages et véhicules retirés, zones 2025 recomposées), masques d'usure, fissures et rapiéçages, marquages finaux. Les noms de prims USD ne changent pas : ton travail dans Houdini (look-dev, matériaux) reste valable.

## 0. Récupérer le paquet
```
git clone https://github.com/floriangit12/claudecode_roadcreation.git
cd claudecode_roadcreation
git checkout claude/adas-simulator-meylan-i6fdvn
```
Le paquet est dans `recon/out/paquet_jardin/package/` :

| Fichier | Contenu |
|---|---|
| `paquet_jardin_2026.usda` | scène racine (à ouvrir) — mètres, Z vers le haut |
| `layers/*.usdc` | terrain, voirie (une mesh par classe : chaussée, trottoir, îlot, piste...), bordures, marquages (drapés à +1 cm, usure en attribut), végétation et mobilier (instances), bâtiments |
| `layers/materiaux.usda` | matériaux UsdPreviewSurface (macro-albédo de l'ortho nettoyée + couleurs par classe) |
| `textures/` | macro-albédo 8192 px de l'emprise et masques (rapiéçages, fissures, usure, ombres) |
| `paquet_jardin_2026.xodr` | réseau routier OpenDRIVE (voies, manœuvres autorisées, feux, passages) |
| `preview/paquet_jardin_2026.glb` | aperçu rapide (Visionneuse 3D de Windows, Blender, gltf-viewer.donmccurdy.com) |
| `houdini/charger_paquet_jardin.py` | chargement Houdini 22 |
| `unreal/importer_paquet_jardin.py` | import Unreal 5.8 |
| `substituer_assets.py` | remplace les volumes provisoires par tes assets |
| `rapport_assemblage.json` | comptes, sources utilisées, origine du repère |
| `donnees/` | couches sources en Lambert-93 : surfaces, marquages, bordures avec hauteur mesurée (pour des Sweep), heightmaps 16 bits avec leur JSON d'échelle (Landscape Unreal, heightfield Houdini), instances et voies OpenDRIVE |

**Repère** : origine O = Lambert-93 (917279.43, 6460289.98), altitude NGF-IGN69 216.30 m ;
X vers l'est, Y vers le nord, Z vers le haut. Toutes les coordonnées de la scène sont relatives à O.

## 1. Vérification rapide (2 minutes)
Ouvre `preview/paquet_jardin_2026.glb` dans la Visionneuse 3D de Windows ou dans Blender.
Tu dois voir le carrefour texturé par l'ortho, avec les marquages 2026, les bordures, les arbres
et le mobilier (en volumes provisoires).

## 2. Houdini 22
1. Ouvre Houdini 22, puis **File > Run Script…** et choisis `package/houdini/charger_paquet_jardin.py`.
2. Le script crée :
   - `/stage/paquet_jardin` : la scène USD complète dans **Solaris**, avec un soleil et un ciel.
     Un rendu Karma est possible tout de suite.
   - `/obj/paquet_jardin_sop` : la même géométrie dépaquetée en **SOP**, passée en Y-up. Les
     attributs USD sont conservés en attributs Houdini : `classe`, `etat`, `type` et `usure`
     des marquages, `couverture`.
3. Si la scène apparaît couchée dans Solaris, mets `ROTATION_SOLARIS = True` en tête du script
   et relance-le.
4. Raffinements conseillés (procéduraux, réversibles) :
   - **bordures** : remplace les faces verticales par un *Sweep* du profil réel le long des
     bordures. Les profils sont dans `assets/specs/bordures.json` ; les hauteurs mesurées sont
     dans `donnees/relief/bordures_hauteurs.geojson`.
   - **marquages** : *PolyExtrude* de 2 mm, et variation de couleur/rugosité pilotée par
     `usure` et `couverture`.
   - **espaces verts** : *Scatter* d'herbe et de massifs sur les classes `espace_vert` et
     `terre_plein_vegetal`.
   - **export** : *USD ROP* (ou *Houdini Engine* dans Unreal) vers un nouveau fichier.
     N'écrase pas le paquet : il est régénérable.

## 3. Unreal Engine 5.8
1. Crée un projet vide (ou ouvre ton projet simulateur).
2. Dans **Edit > Plugins**, active **USD Importer** et **Python Editor Script Plugin**, et
   éventuellement **Georeferencing**. Redémarre l'éditeur.
3. **Tools > Execute Python Script…** et choisis `package/unreal/importer_paquet_jardin.py`.
   - `MODE = "stage"` (par défaut) : un *UsdStageActor* lit directement le `.usda`. C'est idéal
     pour vérifier, car un rechargement suffit après une régénération du paquet.
   - `MODE = "import"` : conversion en Static Meshes, matériaux et textures dans
     `/Game/Meylan/PaquetJardin`. Ce mode convient pour Nanite, l'éclairage, le packaging et
     CARLA.
4. Matériaux : l'import crée des instances de matériaux à partir des UsdPreviewSurface. Pour
   le réalisme, remplace-les par tes matériaux Unreal :
   - enrobé, béton : matériaux CC0 de `assets/manifeste_cc0.json`, téléchargés par
     `python assets/telecharger_cc0.py` ;
   - garde le **macro-albédo** (`textures/albedo_macro_8192.jpg`, UV0 = coordonnées 0-1 sur
     l'emprise) multiplié par la texture de détail tuilable (UV1 = mètres) ;
   - peinture des marquages : couleur et usure d'après `assets/specs/peinture.json`.
5. Géoréférencement (optionnel) : avec le plugin Georeferencing, *GeoReferencingSystem* en
   projection **EPSG:2154**, origine du niveau = O (917279.43, 6460289.98, 216.30).

## 3 bis. Look-dev réaliste (à faire dans Houdini 22)
Le réalisme du sol se construit sur le PC, dans Houdini (Karma / MaterialX), avec un rendu réel sous les yeux :
- **Macro** : la couleur vient de `textures/albedo_macro_8192.jpg` (UV `st`, 0-1 sur l'emprise). Dans la v2, c'est l'ortho nettoyée.
- **Détail** : un enrobé CC0 tuilable en UV `st1` (en mètres). Le choix est fait et vérifié visuellement dans
  `assets/manifeste_cc0.json`, par exemple Asphalt031 pour l'enrobé ancien et Asphalt033 pour l'enrobé neuf de 2025, avec une taille de tuile de 2 à 2,5 m. Pour le télécharger : `python assets/telecharger_cc0.py`.
- **Mélange conseillé** : couleur = macro × (détail / moyenne floue du détail). Le détail apporte le grain sans changer la teinte réelle du site. Rugosité et normale viennent du détail. Les masques de la v2 (traces de roues polies, rapiéçages, fissures) modulent la rugosité et la couleur.
- **Peinture** : couleurs, réflectance et recette d'usure 0-3 dans `assets/specs/peinture.json`. Les primvars `usure`, `couverture` et `type` sont sur les meshes de marquages.

## 4. Librairie d'assets (static meshes, textures)
- La liste exacte des assets à obtenir ou fabriquer est dans `assets/CAHIER_DES_CHARGES.md` :
  nom, cotes, référence normative, photo réelle, source conseillée et priorité ADAS. Les faces
  officielles des panneaux sont dans `assets/specs/panneaux/faces/`, et les équivalents CARLA
  dans `assets/carla_correspondances.json`.
- Chaque objet de la scène est un prototype **nommé comme l'asset final** (ex. `feu_R11v`,
  `panneau_B14_50`, `arbre_platanus_acerifolia_grand`) avec un volume provisoire.
- Quand tu as des assets, exporte chacun en USD dans `assets/lib/<categorie>/<nom>/<nom>.usda` :
  pivot au pied, face avant vers +Y, en mètres ou en cm, Z-up ou Y-up. Lance ensuite :
  ```
  hython recon/out/paquet_jardin/package/substituer_assets.py --librairie assets/lib
  ```
  Recharge ensuite la scène (Houdini : Reload sur le Sublayer LOP ; Unreal : Reload sur le
  UsdStageActor). Pour revenir aux volumes provisoires, supprime `layers/substitutions.usda`.
- Pour les assets CARLA (fichiers .uasset, déjà dans Unreal), utilise
  `carla_correspondances.json`. En mode « import », remplace dans le niveau les Static Meshes
  provisoires par les meshes CARLA de même usage. Les feux et panneaux CARLA ne sont pas
  français : préfère les assets maison pour la perception ADAS.

## 5. OpenDRIVE et simulation
- Contrôle visuel rapide du `.xodr` avec **esmini** :
  `esmini --odr paquet_jardin_2026.xodr --window 60 60 1280 720`.
  L'outil est gratuit (github.com/esmini/esmini).
- **CARLA** : une carte personnalisée = un maillage (FBX, exportable depuis Houdini ou
  Unreal) + le `.xodr` du même nom. Voir la documentation CARLA « Ingest a map » / « Add a new
  map ». Vérifie que ta branche CARLA est compatible avec ta version d'Unreal.
- Le `.xodr` est dans le même repère local que la scène USD (header `geoReference` EPSG:2154 +
  offset O) : routes et maillages se superposent sans recalage.

## 6. Ce qui est fidèle, et ce qui ne l'est pas encore
Voir `rapport_assemblage.json` et `recon/out/paquet_jardin/*/` (rapports de chaque atelier).
- **Fidèle et vérifié** : géométrie 2026 de la chaussée, des îlots et des trottoirs au cœur ;
  marquages 2026 et leur usure ; topologie et manœuvres ; relief (pentes, dévers, hauteurs de
  bordure mesurées au LiDAR) ; positions des arbres et du mobilier.
- **Provisoire** : apparence du mobilier et des arbres (volumes en attendant tes assets) ;
  bâtiments en blocs LoD1 ; texture de chaussée issue de l'ortho 2022 (5 cm/px, donc floue de
  près, à combiner avec un matériau de détail).
