# Look-dev optionnel « City Sample » (Karma / MaterialX)

Grain réaliste du sol (enrobés, trottoirs, îlots, bordures, peinture usée) tiré des textures du
projet **City Sample** d'Epic Games (Unreal Engine 5.7). La teinte réelle du site reste celle de
l'ortho (`albedo_macro_8192.jpg`). Le détail City Sample n'ajoute que le grain, la rugosité et le relief.
Exceptions voulues : les classes sans ortho (bordures, enrobé neuf 2025) sont calées sur l'albédo
mesurée sur photos de `assets/manifeste_cc0.json`. Les bordures sont donc environ 40 % plus sombres que
dans le paquet v1, dont la couleur (0,66) est 1,8 fois trop claire. L'encrassement de la peinture
suit la classe d'usure (`salete` de `assets/specs/peinture.json` : peinture 2025 presque propre).

## Contenu
| Fichier | Versionné | Rôle |
|---|---|---|
| `exporter_textures_citysample.py` | oui | script Python **Unreal** : export des Texture2D choisies (PNG, données source) |
| `preparer_lookdev_citysample.py` | oui | script **hython** : hoiiotool (2048 px, normales OpenGL), statistiques numpy, JSON, couche USD |
| `correspondances_citysample.json` | oui | classe → assets UE, fichiers, tuile (m), albédo moyenne, rangement des canaux, réglages |
| `../houdini/lookdev_citysample.usda` | oui | couche de surcharges MaterialX (`outputs:mtlx:surface`) des `/World/Looks/*` du paquet |
| `textures/` (dont `brut/`) | **non** | textures exportées (≈ 2,2 Go en `brut/`, ≈ 105 Mo préparées, plus les caches `.rat` créés par Karma) |

**Pourquoi `textures/` n'est pas versionné :** le contenu City Sample et Megascans est couvert par
l'EULA Unreal Engine. On peut l'utiliser dans ses projets, mais pas le redistribuer comme fichiers
bruts. Le dossier est donc ignoré (`recon/pc/.gitignore`). Le dépôt ne contient que du code, des
chemins d'assets et la couche USD (chemins relatifs vers `textures/`).

## Ce qui a été exporté
45 textures, détail dans le JSON. Sources : `/Game/Megascans/Surfaces` (Asphalt_Road_2x2_M_01/02/03,
Coarse_Road, Asphalt_Dried01, Asphalt_Fresh, Dirty_Sidewalk, Concrete_Rough_2x2, Rough_Concrete_Floor…),
`/Game/Building/Texture/ConcreteDirty`, `/Game/Road/Textures/Sidewalks`, `/Game/Megascans/Atlases`
(peinture usée, poussière) et `Grunge_00`. Textures retenues :
- enrobé ancien (chaussée, parking, accès) : Asphalt_Road_2x2_M_03 ;
- piste cyclable : Asphalt_Road_2x2_M_02, l'enrobé de référence des routes City Sample ;
- trottoir : Asphalt_Dried01 ;
- îlots et quais : Concrete_Rough_2x2_M_00 ;
- enrobé neuf 2025 : Asphalt_Fresh_2x2_M_00. City Sample n'en fournit que l'albédo, le relief vient de M_02 ;
- bordures : T_ConcreteDirty, en projection triplanaire (faces verticales sans UV utiles) ;
- usure de la peinture : Grunge_00, égalisée, pour que l'opacité moyenne soit égale à la primvar `couverture`.

City Sample ne contient **ni herbe ni enrobé coloré**. Les espaces verts gardent donc
l'UsdPreviewSurface du paquet (voir le CC0 `Grass004` dans `assets/manifeste_cc0.json`).

Les normales Unreal marquées *Flip Green Channel* sont déjà en OpenGL dans les données source. Les
autres sont en DirectX, et leur vert est inversé. La règle a été vérifiée par corrélation
normale / hauteur.

## Régénérer (PC avec CitySample et Houdini 22)
```
"C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "C:/Users/flori/Documents/Unreal Projects/CitySample/CitySample.uproject" -run=pythonscript -script="<dépôt>/recon/pc/citysample/exporter_textures_citysample.py" -unattended -nop4 -nosplash -NullRHI -stdout -FullStdOutLogOutput
"C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe" <dépôt>/recon/pc/citysample/preparer_lookdev_citysample.py
```
L'export prend environ 4 minutes, la préparation environ 40 secondes. Le projet CitySample est
seulement lu : rien n'est sauvegardé, à part le cache Saved/DDC du moteur. La variable
`CITYSAMPLE_MODE=inventaire` liste les textures et les paramètres des matériaux de voirie, sans
rien exporter.

## Activer le look-dev
La couche doit être le sublayer **le plus fort**, au-dessus du paquet. Le paquet n'est jamais modifié.
- **Solaris** : un LOP *Sublayer* chargé avec `recon/pc/houdini/lookdev_citysample.usda`, placé
  au-dessus du paquet. Il suffit de le désactiver ou de le retirer pour revenir à l'UsdPreviewSurface.
- **husk** : une racine qui empile `@<dépôt>/recon/pc/houdini/lookdev_citysample.usda@`, puis les
  caméras et `paquet_jardin_2026.usda`.

Karma utilise le réseau MaterialX. Unreal et les autres outils continuent de lire l'UsdPreviewSurface.
Sans le dossier `textures/`, Karma affiche « Failed to load texture » et utilise les valeurs par défaut
(couleur moyenne, peinture pleine). Le rendu ressemble alors à celui de l'UsdPreviewSurface : il faut
d'abord régénérer les textures.
Pour régler l'intensité du grain, du relief ou de la rugosité de chaque look, modifier `LOOKS` dans
`preparer_lookdev_citysample.py`, puis relancer le script.
