# Relief du carrefour Paquet Jardin (Meylan) — sorties de `recon/stages/relief.py`

Régénération : `python3 recon/stages/relief.py` depuis la racine du dépôt (≈ 10 min, sans cache).
Altitudes NGF-IGN69 (m), planimétrie Lambert-93 (EPSG:2154). Repère local : O = (917279.43,
6460289.98, 216.30) ; X = E − 917279.43, Y = N − 6460289.98, Z = alt − 216.30.

## Grille
Tous les rasters : 3025 × 3025 nœuds au pas de 0,10 m, centrés sur O (le nœud central est O).
Emprise des nœuds : x 917128.23 → 917430.63, y 6460138.78 → 6460441.18 (302,4 m) ; GeoTIFF en
convention « pixel = surface » (bords à ± 0,05 m des nœuds). 3025 = 63 × 2 × 24 + 1 : taille de
Landscape Unreal valide (63 quads/section, 2×2 sections/composant, 24×24 composants).

## Fichiers
| fichier | contenu |
|---|---|
| `dtm_sol_10cm.tif` | sol nu **2021** (LiDAR HD, classe 2, vols du 12/08 et 06/09/2021), float32 |
| `chaussee_lisse_10cm.tif` | surface de roulement lissée, **chaussée 2026**, NaN ailleurs, float32 |
| `dtm_2026_10cm.tif` | sol nu **octobre 2026** (source des heightmaps), float32 |
| `heightmap_3025_10cm.png/.json` | heightmap 16 bits 3025² (10 cm) + échelle, Unreal / Houdini |
| `heightmap_2017_15cm.png/.json` | heightmap 16 bits 2017² (15 cm) + échelle (63 quads, 2×2, 16×16) |
| `heightmap_*_zlocal.tif` | mêmes grilles en float32, Z local (m) : chargement direct dans Houdini |
| `bordures_hauteurs.geojson` | hauteur de vue des bordures par tronçon de 1 m (L93) |
| `relief_zones_2026.geojson` | chaussée 2026, zones rehaussées en 2025, traversées, chantier régalé |
| `relief_stats.json` | chiffres de contrôle (bruit, pentes, dévers, bordures, quantification) |
| `qa/` | rendus 1000×1000 à 5 cm (ombrages 2021 / 2026, hauteur sur chaussée, bordures, plan projet) et profils |

## Méthode
1. **Points sol** : classe 2, lignes de vol 2021 seules (les points de remplissage 2011/2019
   sont écartés), décalages verticaux entre bandes corrigés (référence 7209 : 7020 -2.5 cm, 7208 -0.5 cm, 7210 +0.2 cm, 7211 +1.3 cm),
   rejet des points isolés (10820 points), débruitage bilatéral (σ 0,25 m / 3 cm : le bruit
   de ±2 cm est atténué mais les ressauts > 8 cm sont conservés), TIN linéaire → `dtm_sol`.
   Trous (bâtiments, véhicules) : triangles du TIN ; 11.17 % des nœuds sont à plus de 2 m d'un point.
2. **Chaussée 2026** : propagation depuis les axes OSM 2026 dans des couloirs, arrêtée par les
   bordures GAM (levé postérieur aux travaux au cœur), les aplats et la géométrie 2026 du plan
   projet (terre-plein, refuges, îlot Vercors), les ressauts LiDAR 2021 hors zone des travaux,
   les talus, la végétation au sol (ortho 2022 + intensité LiDAR) et les pistes OSM.
3. **Lissage** : régression locale linéaire pondérée (convolution normalisée d'ordre 1, σ 0,5 /
   1,2 / 3 / 8 m, l'échelle la plus fine disposant de points l'emporte), robuste (bisquare 7 cm).
   Passe A sur la chaussée 2021 seule, passe B sur la chaussée 2026 en excluant les reliefs
   (> 5 cm) des anciens îlots / quais / séparateurs : ces surfaces sont **arasées au niveau de la
   chaussée prolongée**. Résidu des points retenus : écart-type 1,76 cm (bruit LiDAR).
4. **Sol 2026** : `dtm_sol` + chaussée lissée ; anciennes chaussées devenues trottoir / massif /
   refuge / terre-plein en 2025 = chaussée prolongée + hauteur standard ; chantier 2021 des
   Saules Blancs (quartier livré en 2024) régalé par interpolation harmonique depuis son pourtour.
5. **Bordures** : dessus (0,25–0,8 m derrière la ligne) − fil d'eau (0,1–0,6 m devant), médianes des
   points sol, par tronçon de 1 m ; tronçons sans mesure interpolés le long de la bordure (≤ 5 m) ;
   bordures créées après 2021 → hauteur standard, `statut = estimee`.

## Hauteurs standard (bordures créées en 2025, zones rehaussées)
- refuge, terre-plein central, îlot : **0,15 m** — valeurs mesurées en 2021 sur les refuges et le
  TPC du même carrefour (15–18 cm, vérification lidar-11), vue courante d'une bordure T2 (14–16 cm) ;
- trottoir, cheminement, massif « au niveau trottoir » : **0,14 m** — vue usuelle d'une T2 ; les
  bordures 2021 du site mesurent 10–15 cm sur Verdun / Revirée ;
- quai bus : **0,20 m** — ancien quai mesuré 19–22 cm (lidar-10), quais accessibles 18–21 cm ;
- traversées : **0,02 m** — bordure abaissée, ressaut maximal PMR (lidar-19).

## Statuts de `bordures_hauteurs.geojson`
`mesuree` (LiDAR 2021, ressaut ≥ 3 cm), `sans_ressaut_mesuree` (< 3 cm : bord à niveau, bateau,
limite de revêtement), `abaissee_mesuree` (traversée, ≤ 6 cm), `interpolee`, `modifiee_2025`
(un côté rehaussé en 2025 : hauteur du modèle 2026), `estimee` (créée après 2021 ou sans mesure).
Champs : `h_vue_m` (valeur à utiliser), `h_lidar_2021_m`, `h_modele_2026_m`, `z_dessus_2021_m`,
`z_fil_eau_2021_m`, `cote_haut` (gauche/droite du sens de numérisation), `traversee`,
`creee_apres_2021`, `zone_travaux_2025`, `contexte`, `confiance`, `source`, `u_m`, `v_m`.

## Unreal Engine 5.8 (Landscape)
Landscape Mode › Manage › New › Import from File : `heightmap_2017_15cm.png` (recommandé ; route en
maillages USD par-dessus) ou `heightmap_3025_10cm.png` (fin). Reprendre **exactement** la
résolution, les sections, l'échelle et la position du JSON (`unreal_5_8_landscape`) ; ne pas
laisser Unreal redimensionner. Échelle Z : `scale_z = (z_max − z_min) × 100 × 128 / 65535`
(quantification ≈ 0,1038 mm). Repère Unreal = repère local en cm avec Y inversé (comme l'import USD).

## Houdini 22 (heightfield)
HeightField File sur `heightmap_*_zlocal.tif` (Z local en mètres, aucune mise à l'échelle), taille
de voxel = pas de la grille, centré sur (0, 0). Avec le PNG : HeightField Remap 0..1 →
z_min_local..z_max_local du JSON. Houdini est Y-up : X = Est, Z = −Y local, la ligne 0 (nord) est
du côté −Z. Pour un maillage : HeightField Convert ou Volume → Polygons, puis découpe par les
polygones de `relief_zones_2026.geojson` / `surfaces_2026.geojson`.

## Limites connues
- Aucune altimétrie postérieure aux travaux 2025 n'existe : le relief des zones refaites est
  déduit (profils de chaussée conservés, hauteurs standard). Le régalage du quartier des Saules
  Blancs est une interpolation (le LiDAR 2021 montre le chantier).
- Les levés GAM ont Z = 0 : aucune altitude n'en est tirée.
- Nœuds sans point sol à moins de 2 m (bâtiments, couverts denses) : interpolés (TIN).
