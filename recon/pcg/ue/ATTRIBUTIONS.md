# Attributions des contenus tiers du projet Unreal (D:/ClaudeADAS)

Aucun `.uasset` tiers n'est versionné. Ce fichier recense les licences des contenus que le projet UE utilise ou copie.

## CARLA (CC-BY 4.0)

- Contenu : sous-ensemble de `D:/CARLA_Assets/Content/Carla` copié dans `D:/ClaudeADAS/Content/Carla/` (chemins
  `/Game/Carla/...` conservés), puis réenregistré en 5.8 : végétation, GenericMaterials, Decals/Road et Pavement,
  Static/Static, Fence, Pole, MPC CarlaParameters et WeatherMaterialParameters (README.md, § Contenu CARLA).
- Licence : Creative Commons Attribution 4.0 International (`D:/CARLA_Assets/LICENSE`), https://creativecommons.org/licenses/by/4.0/.
- Attribution : « CARLA Simulator assets © CARLA Team, Computer Vision Center (CVC), Universitat Autònoma de
  Barcelona, sous licence CC-BY 4.0 ». Modifications : réenregistrement en UE 5.8.3 ; taille d'écran des LOD imposteurs
  de 77 végétaux mise à 0 (`correctifs/carla_imposteurs.py`) ; MI enfants `MI_<id>__carla` (luminosité étalonnée) ;
  teinte d'automne par instance ajoutée au maître de feuillage `M_treeLeaves_master` de la copie projet
  (`correctifs/carla_feuillage_automne.py`) ; Nanite (préservation de l'aire) sur les 37 arbres et buissons posés
  (`correctifs/carla_arbres_nanite.py`) ; MI enfants `MI_PJ_Herbe_*` des herbes (teinte d'octobre, `contexte/ue/pg_herbe.py`).
- `D:/CARLA_Assets` n'est jamais modifié.
- Pilote ZP-01 (`pilote/`, niveau `/Game/PJ/Maps/PJ_2026`) : aucun asset CARLA posé (sol, bordures, îlots et détails
  viennent de la fabrication Houdini et des matériaux CC0).
- Contexte du pilote (`contexte/`, `vegetation/`, même niveau) : assets CARLA posés par PCG, non modifiés (sauf la taille
  d'écran des imposteurs ci-dessus) : arbres et buissons (`Static/Vegetation/Trees`, `Bushes`), herbes et feuilles
  (`Grass`, `Leaves`), clôtures (`Static/Fence/SM_fence_09_v*`), lampadaires, poteaux et potelets (`Static/Pole`), toits
  (`GenericMaterials/RoofBitumen`), bois des tuteurs (`Fence/Materials/FenceWood`). Table : `vegetation/correspondance_carla.json`.

## Données ouvertes (contexte)

- Cadastre Etalab (bâtiments de Meylan, `data/context/cadastre-38229-batiments.json.gz`) : Licence Ouverte 2.0 (Etalab),
  « Source : DGFiP / Etalab, cadastre ». Emprises extrudées avec des hauteurs a priori (`contexte/lointain.py`).
- Inventaire des arbres de Grenoble-Alpes Métropole (`data/context/arbres_metropole.geojson`, data.metropolegrenoble.fr) :
  positions, genres et classes de hauteur reprises dans `ue_pilote/points/arbres_lointains_ue.json` ; citer « Grenoble-Alpes
  Métropole, données ouvertes » (licence du jeu à confirmer sur le portail : Licence Ouverte ou ODbL).

## Photos Panoramax (CC-BY-SA 4.0)

Profil de l'horizon de montagnes (`ue_pilote/horizon/profil.json`, `contexte/horizon.py`) : ligne de ciel relevée sur 60
photos 360° du site (2024-2025, producteurs « Eric S », « motocultrice » et autres de panoramax.openstreetmap.fr), données
dérivées de photos CC-BY-SA 4.0, donc sous CC-BY-SA 4.0 (crédit « Panoramax, contributeurs, CC-BY-SA 4.0 ») ; le relief
lointain `relief.usdc` (non versionné) en est construit, avec un a priori de sommets pour les secteurs masqués.

Les planches `recon/out/paquet_jardin/v2/ue_pilote/planche_panoramax_<id>.png` contiennent des recadrages des photos 360°
e5d79de9 et 9834f494 (18/05/2025, producteur « Eric S », instance panoramax.openstreetmap.fr), sous licence CC-BY-SA 4.0 :
le crédit est inscrit sur chaque planche ; ces planches (œuvres dérivées) sont elles-mêmes sous CC-BY-SA 4.0. Les photos
et les recadrages bruts restent hors git (`data/raw`, `ue_pilote/panoramax/*.png`).

## City Sample (licence Epic / Unreal Engine)

Textures City Sample (`/Game/PJ/Textures/CitySample`, MI `MI_<id>__citysample` ; béton `concrete_rough_2x2` des MI
`MI_beton_bordure_gris` et `MI_beton_bordure_clair` depuis la revue UE du 10/10, `materiaux/catalogue.BETON_BORDURE_UE`) :
utilisation **uniquement dans Unreal Engine** (décision D8, ARCHITECTURE.md) ; pas d'usage dans Houdini / Karma (Karma
garde Concrete037 CC0), rien de versionné.

## Textures CC0 (ambientCG, Poly Haven)

Matériaux du sol (`assets/lib/materiaux/<id>/meta.json`, `/Game/PJ/Textures/CC0`) : CC0 1.0 Universal
(domaine public, attribution non requise). Sources citées par matériau dans `meta.json` ; dérivés (hauteurs, bruit,
masque de peinture) dans `data/raw/assets_src/cc0_derive` (non versionné).

## Contenu maison

Géométrie fabriquée par Houdini 22 (Indie) à partir de la description du dépôt (`recon/pcg/houdini`), matériaux
`M_PJ_*` / `MI_*` construits par script (`materiaux/`, `pilote/ue/materiaux_maison.py`).
