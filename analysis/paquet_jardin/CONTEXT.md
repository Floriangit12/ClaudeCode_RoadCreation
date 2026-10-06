# Carrefour « Paquet Jardin » (Meylan) — fiche de contexte pour l'analyse

## Localisation
- Carrefour à feux entre l'**avenue de Verdun** (RD1090, ex-RN90, axe structurant Grenoble ↔ Montbonnot,
  2×2 voies à chaussées séparées, gestionnaire Grenoble-Alpes Métropole), le **chemin de la Revirée**
  (branche nord-ouest : lycée Louis Terray, commerces de la Revirée) et l'**avenue du Vercors**
  (branche sud). La jardinerie « Paquet Jardin » (46 chemin de la Revirée) est à l'ouest, d'où le nom.
- Centre : WGS84 lat 45.20765, lon 5.76820 ; **Lambert-93 (EPSG:2154) x = 917279.43, y = 6460289.98**.
- Orientation : l'avenue de Verdun suit un axe **sud-ouest (Grenoble) → nord-est (Montbonnot)**,
  azimut ≈ 45°/225°. Revirée part vers le nord-nord-ouest, Vercors vers le sud. Altitude ≈ 214 m.
- Arrêts de bus « La Revirée » (réseau M réso / ligne Chrono C1 et ligne 21 etc.), parking relais P+R.
- Piste cyclable bidirectionnelle large le long de l'avenue de Verdun (côté nord-ouest).

## Chronologie essentielle (à garder en tête : quelle date montre chaque source ?)
- 2015/2018 : grand parking à l'est du carrefour ; 2021 : démolition/chantier ; 2024 : nouveaux immeubles.
- **LiDAR HD IGN : vol août–septembre 2021.**
- **Ortho PCRS 5 cm : prise de vue 10 mai 2022.**
- Ortho IGN 20 cm : 2015, 2018, 2021, 2024 (2024 = la plus récente aérienne ouverte).
- Panoramax (photos de rue) : 2020-05-21, 2023-03-18, 2024-05-01, 2024-08-24, 2025-01-12, 2025-05-18,
  **2025-08-31 (carrefour EN TRAVAUX, marquage provisoire jaune)**, 2026-07-28 (à ≥ 129 m au sud).
- **Travaux 2025 « amélioration de la ligne C1 »** (Grenoble-Alpes Métropole) : carrefour compacté,
  **suppression de la voie de tourne-à-droite Verdun → Vercors**, sécurisation des traversées piétonnes
  et cycles, déplacement/mutualisation des quais de bus « La Revirée », déplacement de l'entrée du P+R,
  plantations et gestion alternative des eaux pluviales, cheminement piéton le long des « Saules Blancs ».
  Phase 1 jusqu'au 5 oct. 2025, phase 2 (avenue du Vercors) 6 oct.–5 déc. 2025, finitions jusqu'au 30 janv. 2026.
  Panneau du projet : `data/raw/docs/panneau_amenagement_carrefour_verdun_vercors.pdf`
  (tuiles : `data/raw/docs/tiles/panneau_72dpi/` (vue d'ensemble) et `data/raw/docs/tiles/panneau_150dpi/` (détail)).
- **OSM** autour du carrefour : très nombreuses éditions févr.–août 2026 (après travaux) → OSM ≈ état actuel.
- BD TOPO (IGN) : modifications jusqu'en 2026.
- **Levés topographiques GAM** (`gam_topo_sol_*`, fichier Meylan_Topo.dwg) : au cœur du carrefour ils
  **ne coïncident pas** avec l'ortho de mai 2022 (zébras décalés, bordure nouvelle sur l'ancienne voie de
  tourne-à-droite vers Vercors) → probablement un récolement postérieur aux travaux 2025 (à vérifier).
  Ne pas s'en servir pour juger l'état de 2022 au cœur du carrefour ; une différence avec l'ortho 2022 n'est
  pas forcément une erreur.
=> Les images aériennes 5 cm (2022) et 20 cm (2024) montrent l'**état AVANT travaux**. L'état ACTUEL
   (oct. 2026) se déduit du plan projet + OSM 2026 + photos 2025-08 (travaux) + BD TOPO.

## Données disponibles (chemins relatifs à la racine du dépôt /home/user/ClaudeCode_RoadCreation)
Toutes les images sont en tuiles **1000×1000 px** : les ouvrir telles quelles (ne pas redimensionner).

| Source | Chemin | Détails |
|---|---|---|
| Ortho PCRS 5 cm (2022-05-10) | `data/raw/pcrs5cm/tiles/paquet_jardin/pcrs5cm_<X>_<Y>.jpg` | tuile 50 m × 50 m, nord en haut. `<X>,<Y>` = coin **bas-gauche** L93. Pixel (c, r) → x = X + 0.05·c, y = Y + 50 − 0.05·r |
| Ortho IGN 20 cm (2015/2018/2021/2024) | `data/raw/ortho/paquet_jardin/ORTHOIMAGERY_ORTHOPHOTOS<année>_20cm/` | tuiles 200 m (1000 px). Nom = coin bas-gauche |
| Recadrages 200 m centrés (1000 px) | `/tmp/claude-0/-home-user-ClaudeCode-RoadCreation/86d2357b-8d3a-5e9d-b8d8-a3aa44c66205/scratchpad/vintages/*.jpg` | même cadrage pour chaque millésime |
| Pléiades 2025 (≈ 0.6 m, satellite) | `data/raw/ortho/paquet_jardin/ORTHOIMAGERY_ORTHO-SAT_PLEIADES_2025_60cm/` | trop grossier pour les marquages |
| Photos Panoramax HD | `data/raw/panoramax/paquet_jardin/<date>_<id>_hd.jpg` + `.json` (azimut, caméra...) | tuiles 1000×1000 : `data/raw/panoramax/paquet_jardin/tiles/<date>_<id>_hd/..._rRR_cCC.jpg` (+ `index.json` avec les boîtes pixel) |
| Liste Panoramax (200 photos ≤ 150 m) | `data/sites/paquet_jardin/panoramax_pictures.geojson` | dist_site_m, dx_e_m, dy_n_m (position relative au centre), azimuth |
| LiDAR HD 2021 (rasters) | `data/sites/paquet_jardin/lidar/<produit>_<15cm|25cm>/` (tuiles) ; GeoTIFF float : `data/raw/lidar/paquet_jardin/*.tif` | produits : dtm (MNT sol), intensity_ground, intensity_enhanced (CLAHE, marquages), height_above_ground (0–50 cm : bordures/îlots), slope_pct. Emprise 300 m centrée (x 917129.43–917429.43, y 6460139.98–6460439.98) |
| Nuage LiDAR complet (COPC) | `data/raw/lidar/npl/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz` | ~24 pts/m², classes 1,2,3,4,5,6,9 ; lisible avec laspy |
| Vecteurs du site (WGS84) | `data/sites/paquet_jardin/vector/*.geojson` | `osm_*` (OSM 2026), `bdtopo_*` (IGN), `gam_*` (levés topo Métropole : marquages `topo_sol_signalisation_horizontale_*`, bordures, caniveaux ; PCRS vecteur) |
| Documents projet | `data/raw/docs/` | panneau du projet (PDF + tuiles), magazine « Meylan ma ville » avril-mai 2025 (PDF), pages web meylan.fr |

## Échelle d'usure des marquages (à utiliser partout)
- **0 – neuf** : blanc franc, bords nets, contraste maximal.
- **1 – légère usure** : quelques manques, contraste encore bon.
- **2 – usure marquée** : nettement grisé/transparent, manques importants dans les traces de roues, lisible.
- **3 – très effacé** : à peine visible, risque de non-détection par une caméra ADAS.
- **F – fantôme** : ancien marquage effacé/grenaillé encore visible (ligne fantôme pouvant tromper un détecteur).
Préciser toujours la **cause probable** (passage des roues, freinage/accélération, girations, âge, rabotage...).

## Conventions de réponse
- Rédiger en **français**. Donner des positions en L93 (au mètre) ou par rapport aux branches du carrefour.
- Distinguer **observé** (avec la tuile/photo qui le prouve) et **déduit**. Indiquer le niveau de confiance.
- Ne jamais inventer : si une chose n'est pas visible, le dire.
