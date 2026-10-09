# Travail sur le PC — carrefour Paquet Jardin

Ce dossier contient ce qui est produit sur le PC (Houdini 22, Unreal 5.8) à partir du paquet
`recon/out/paquet_jardin/package/`. Le paquet n'est jamais modifié : tout ici est une couche ou un
script à part, qui reste valable après une régénération du paquet (les noms de prims ne changent pas).

## Prompt 1 — chargement Houdini 22 et rendus Karma de contrôle (octobre 2026)
| Fichier | Rôle |
|---|---|
| `../package_src/houdini/charger_paquet_jardin.py` | chargeur corrigé pour Houdini 22.0.459 (noms de nœuds et paramètres vérifiés dans hython, soleil Z-up, import SOP complet) ; recopié dans le paquet au prochain assemblage |
| `houdini/creer_hip.py` | pilote hython : chargeur + caméras + Karma Render Settings + 4 USD Render ROP + export de `rendu_controle.usda`, puis sauvegarde du hip |
| `houdini/paquet_jardin.hip` | scène Solaris + SOP (licence Indie : contenu « HouLC » sous l'extension .hip) |
| `houdini/cameras.usda`, `cameras.md`, `generer_cameras.py` | 4 caméras de contrôle placées depuis les données (OpenDRIVE, marquages, maillage du sol) |
| `houdini/rendu_controle.usda` | racine husk non aplatie : `./cameras.usda` + paquet en sous-couches relatives, lumières, réglages Karma |
| `houdini/rendre_controle.py` | rendus husk des 4 caméras (Karma XPU par défaut), `--couche` pour empiler un look-dev |
| `rendus/v1/` | rendus 1000 × 1000 du paquet v1 tel quel (matériaux UsdPreviewSurface du paquet) |
| `rendus/v1_citysample/` | mêmes vues avec la couche optionnelle `houdini/lookdev_citysample.usda` |
| `citysample/` | export des textures City Sample (UE 5.7) et préparation du look-dev ; textures **non versionnées** (EULA Unreal), voir `citysample/README.md` |

Régénérer :
```
hython recon/pc/houdini/creer_hip.py
hython recon/pc/houdini/rendre_controle.py v1
hython recon/pc/houdini/rendre_controle.py v1_citysample --couche recon/pc/houdini/lookdev_citysample.usda
```
(`hython` = `C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe` ; ~10 s par image
sur RTX 5070. `KARMA_XPU_DISABLE_MIPMAPS=1` est posé pour que Karma XPU n'écrive pas de caches `.rat`
dans le paquet.)

Ces rendus sont un **contrôle du paquet v1**, pas une cible de réalisme : arbres et mobilier y sont des
volumes provisoires, les bâtiments des blocs LoD1, les marquages une version de travail. La suite vise
un jumeau réaliste fabriqué de façon procédurale (description vectorielle de la scène → Houdini →
PCG Unreal 5.8 avec la librairie d'assets) ; ces vues servent de référence « avant ».
