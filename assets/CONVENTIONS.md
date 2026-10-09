# Librairie graphique (static meshes, matériaux, textures) — conventions

But : fournir à la scène du carrefour (puis de Meylan) des assets **réalistes et conformes au
réel français** : mobilier de voirie aux cotes réglementaires, panneaux aux codes officiels,
matériaux de sol PBR, arbres par essence. La scène USD ne contient que des **références** vers ces
assets : on peut remplacer un asset (par une version CARLA, Fab/Megascans ou une version maison
améliorée dans Houdini) sans rien reconstruire.

## Répartition du travail (décision du 9 octobre 2026)
- **Cloud (ce dépôt)** : inventaire des besoins vérifié sur photos, cahier des charges
  (`assets/CAHIER_DES_CHARGES.md`), spécifications normatives (`assets/specs/*.json` : panneaux,
  feux, mobilier, profils de bordures, végétation, peinture), faces officielles des panneaux
  (PNG depuis les SVG Wikimedia), manifeste et script de téléchargement des matériaux CC0,
  table de correspondance CARLA. Dans la scène, chaque objet est déjà un prototype **nommé comme
  l'asset définitif** avec un volume provisoire.
- **PC de l'utilisateur** : fabrication / obtention des static meshes et matériaux finaux
  (Houdini 22, Unreal 5.8, contenu CARLA, Fab/Megascans, SpeedTree), export USD dans
  `assets/lib/<categorie>/<nom>/<nom>.usda`, puis `package/substituer_assets.py --librairie
  assets/lib` qui remplace les volumes provisoires par ces assets (couche `layers/substitutions.usda`).

## Sources (par ordre de préférence selon le cas)
1. **Fabrication maison** (Houdini 22 sur le PC, d'après `assets/specs/`) : tout ce qui est spécifique
   à la France et normé (panneaux et leurs faces, feux R11v/R12/R13, mâts, potelets, bordures,
   abris, poteaux d'arrêt). Les dimensions suivent l'IISR et les normes (NF EN 1340 pour les bordures)
   et sont recoupées sur les photos Panoramax du site.
2. **Téléchargements libres CC0** : ambientCG, Poly Haven (matériaux PBR : enrobés, bétons, pavés,
   herbe, gravier ; quelques modèles). Le script `assets/telecharger_cc0.py` les récupère : les
   fichiers volumineux ne sont pas versionnés, seul le manifeste (source, licence, empreinte) l'est.
   Wikimedia Commons fournit les SVG officiels des panneaux français (domaine public).
3. **CARLA** (dépôt et contenu présents sur le PC de l'utilisateur) : la table
   `assets/carla_correspondances.json` associe chaque asset de la librairie à son équivalent dans
   le contenu CARLA (chemin Unreal), avec une note d'adéquation (un feu américain n'est pas un R11v).
   Le script Unreal peut substituer ces assets.
4. **Fab / Quixel Megascans, SpeedTree** (sur le PC, compte de l'utilisateur) : surtout pour la
   végétation et les matériaux haut de gamme. Ils sont indiqués comme options dans le catalogue.

## Arborescence
```
assets/
  CONVENTIONS.md
  catalogue_besoins.json      ce dont la scène a besoin (types, codes, quantités, photos de référence)
  catalogue.json              ce que la librairie fournit (un enregistrement par asset)
  carla_correspondances.json  équivalences CARLA
  telecharger_cc0.py          téléchargement reproductible des sources CC0 (manifeste versionné)
  CAHIER_DES_CHARGES.md       liste des assets à obtenir/fabriquer sur le PC (nom, cotes, priorité ADAS)
  specs/                      spécifications (JSON) + faces de panneaux (specs/panneaux/faces/*.png)
  manifeste_cc0.json          matériaux CC0 retenus (source, URL, licence, tile_m, correction de teinte)
  lib/<categorie>/<nom>/      un dossier par asset :
      <nom>.usda              asset USD (Z-up, mètres), matériaux UsdPreviewSurface
      <nom>.glb               même asset en glTF (Y-up), pour aperçu et import Unreal (Interchange)
      textures/               PNG/JPG (PBR : albedo, normal, roughness, ao, opacity)
      meta.json               source, licence, auteur, dimensions, référence normative, photos de
                              référence, équivalents CARLA, LOD, nombre de triangles
  qa/                         rendus de contrôle 1000x1000 (asset seul et à côté de la photo réelle)
```
Catégories : `signalisation_verticale` (panneaux, feux, mâts), `eclairage`, `transport` (abris,
poteaux d'arrêt), `mobilier` (potelets, barrières, bancs, corbeilles), `bordures` (profils
extrudables), `vegetation`, `materiaux` (sols PBR, peinture routière).

## Règles des assets
- **Unités et axes** : mètres, Z vers le haut, **pivot au pied de l'objet sur le sol** (z = 0),
  **face avant vers +Y** (la face d'un panneau regarde +Y : dans la scène, l'orientation
  `yaw` fait tourner +Y vers l'usager concerné).
- **Noms** : snake_case ASCII. Panneaux : `panneau_<code>` (ex. `panneau_B14_50`,
  `panneau_AB3a`, `panneau_C20a`) ; feux : `feu_R11v`, `feu_R12`, `feu_R13c`... ; arbres :
  `arbre_<genre>_<espece>_<classe_taille>` (ex. `arbre_platanus_acerifolia_grand`).
- **Matériaux** : UsdPreviewSurface (diffuseColor/normal/roughness/metallic/occlusion/opacity),
  textures en chemins relatifs. Peinture rétroréfléchissante et faces de panneaux : texture
  d'albédo + rugosité ; les codes couleur suivent l'arrêté de 1967 / IISR (rouge, bleu, jaune).
- **Budget** : mobilier < 5 000 triangles, arbres < 30 000 (LOD0) ; textures 2K maximum
  dans le dépôt (4K téléchargeables via le manifeste).
- **Matériaux de sol** : texture tuilable (taille réelle en mètres indiquée dans `meta.json`,
  `tile_m`) ; le macro-albédo de l'ortho se combine par-dessus dans Unreal (voir le guide PC).
- **Licence** : chaque `meta.json` indique la licence (CC0, domaine public, maison = même
  licence que le dépôt). Rien de propriétaire n'est versionné (CARLA et Fab restent sur le PC).
- **Contrôle qualité** : chaque asset est rendu (outil `recon/tools/render3d`) en tuiles
  1000x1000 et comparé visuellement aux photos réelles du site (tuiles Panoramax 1000x1000).

## Lien avec la scène
Chaque prototype d'instance de la scène porte le nom de l'asset attendu (ex. `feu_R11v`,
`panneau_B14_50`, `arbre_platanus_acerifolia_grand`).
- Dans le cloud, `recon/assemble.py` référence `assets/lib/*/<nom>/<nom>.usda` s'il existe, sinon
  crée un volume provisoire (attribut `customData.volume_provisoire`).
- Sur le PC, `package/substituer_assets.py --librairie <dossier>` fait la même substitution sans
  rien reconstruire (assets Y-up ou en centimètres convertis automatiquement ; arbres mis à
  l'échelle de la hauteur mesurée au LiDAR).
