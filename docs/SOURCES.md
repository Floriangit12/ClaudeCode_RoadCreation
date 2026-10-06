# Sources de données — Meylan (38229)

Toutes les sources ci-dessous ont été **testées** (requête réelle, contrôle du contenu et de la
résolution) le 6 octobre 2026. Les scripts du dossier `pipeline/` les téléchargent de façon
reproductible ; les données lourdes vont dans `data/raw/` (non versionné), les données
vectorielles légères et les extraits du carrefour étudié dans `data/vector/` et `data/sites/`.

Règle commune à toutes les images : **découpage en tuiles carrées de 1000×1000 px, sans
redimensionnement** (`pipeline/common.py::cut_tiles`, la dernière tuile d'une rangée est recalée
sur le bord plutôt que complétée ou réduite).

## 1. Imagerie aérienne

| Source | Résolution native | Date | Couverture Meylan | Accès | Licence | Script |
|---|---|---|---|---|---|---|
| **PCRS 5 cm Grenoble-Alpes Métropole** (CRAIG) | **5 cm** (vraie, vérifiée) | PVA **10 mai 2022** (campagne `grenoble_alpes_2022`) ; quelques dalles est : `chartreuse_gresivaudan_2021` (15 juin 2021) | 100 % (427 dalles 200 m) | WebDAV `https://drive.opendata.craig.fr/public.php/webdav/ortho/PCRS_5cm/<année>/<campagne>/<XXXX>-<YYYYY>.tif`, utilisateur `opendata`, mot de passe vide ; nom = coin haut-gauche en hm ; tableau d'assemblage `dallage_pcrs_opendata.gpkg.zip` | Licence Ouverte (attribution « Partenariat PCRS sur Grenoble Alpes Métropole – CRAIG – 2022 ») | `pcrs.py` |
| Ortho IGN BD ORTHO HR | 20 cm | 2024 (Isère) | 100 % | WMS `https://data.geopf.fr/wms-r`, couche `HR.ORTHOIMAGERY.ORTHOPHOTOS` ou `ORTHOIMAGERY.ORTHOPHOTOS<année>` | Etalab 2.0 | `ortho.py` |
| Ortho IGN millésimes | 20 cm (2015→2024), 50 cm avant | 2015, 2018, 2021, 2024 | 100 % | idem, `ORTHOIMAGERY.ORTHOPHOTOS2015`… | Etalab 2.0 | `ortho.py --source ign_year --layers …` |
| CRAIG ortho régionale | 20–25 cm | 2024, 2021, 2018… | 100 % | WMS `https://wms.craig.fr/ortho` (`ortho_2024`…) | Licence Ouverte | `ortho.py --source craig` |
| Pléiades (satellite) | ≈ 0,5–0,6 m | 2025 | 100 % | WMS IGN `ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025`, **FORMAT=image/png** (4 bandes) et résolution ≥ 0,6 m (échelle mini) | Etalab 2.0 | `ortho.py --format image/png --res 0.6` |
| PCRS 5 cm GAM 2025 (RVB + IRC) | 5 cm | juin–juillet 2025 | 100 % | flux RTGE `tiles.rtge.craig.fr` | **Accès restreint (abonnement)** — non utilisé | — |
| IGN THR / PCRS.LAMB93 / ORTHO-EXPRESS 2025 / RVB-EXPRESS 2026 | — | — | **vide sur Meylan** | — | — | — |

## 2. Photos de rue

| Source | Contenu Meylan | Accès | Licence | Script |
|---|---|---|---|---|
| **Panoramax** (méta-catalogue `https://api.panoramax.xyz/api`, instances IGN et OSM-France) | **19 868 photos** dans la commune (10 179 en 360° GoPro Max 5760×2880, 9 689 à plat), 2009 → sept. 2026, ≈ 53,6 Go en HD ; **204 photos à ≤ 150 m du carrefour Paquet Jardin** (8 séquences 2020→2026) | STAC `/search?bbox=…&limit=…` (pas de pagination → découpage en quadtree) ; image HD `/api/pictures/<id>/hd.jpg` | CC-BY-SA 4.0 (OSM-France) / Etalab 2.0 (IGN) | `panoramax_enum.py` (catalogue), `panoramax.py` (téléchargement + tuiles) |
| Mapillary | inconnu | nécessite un jeton OAuth gratuit | CC-BY-SA | non utilisé (pas de jeton) |
| KartaView | 663 photos 2019–2021, aucune à < 573 m du carrefour | API v1 `nearby-photos` | CC-BY-SA | non utilisé |

## 3. Altimétrie / 3D

| Source | Détail | Date | Accès | Script |
|---|---|---|---|---|
| **LiDAR HD IGN** (nuage classé COPC) | ≈ 24 pts/m² (sol ≈ 12 pts/m²), classes 1-2-3-4-5-6-9, intensité (pas de RVB) ; 27 dalles 1 km, 4,6 Go, 740 M points | vol **12 août – 6 sept. 2021** (édition 2025-03-25) | index WFS `IGNF_LIDAR-HD_METADONNEE:metadata` ; `https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_PM_2025-03-25/LHD_FXX_<XXXX>_<YYYY>_PTS_LAMB93_IGN69.copc.laz` | `lidarhd_download.py`, `lidar_raster.py` |
| MNT / MNS / MNH LiDAR HD 50 cm | GeoTIFF float | 2021 | URL `url_mnt/url_mns/url_mnh` du même index | `lidarhd_download.py` |
| CRAIG LiDAR HD Isère (COG MNT/MNS 50 cm, LAZ 500 m) | mosaïque | 2021-2022 | WebDAV `altimetrie/lidar_hd/38_Isere/` (utilisateur `opendata`) | — |
| RGE ALTI 1 m | repli | 2024 | WMS `RGEALTI-MNT_PYR-ZIP_FXX_LAMB93_WMS` | — |
| BD TOPO bâtiments (hauteurs) | LoD1 | 2017–2026 | WFS (voir §4) | `bdtopo.py` |

## 4. Vecteurs

| Source | Contenu | Accès | Script |
|---|---|---|---|
| **OpenStreetMap** | 5 506 voies, 712 aménagements cyclables, 1 836 passages piétons, 452 feux, 556 bordures, 722 panneaux, 4 914 lampadaires, 18 708 bâtiments, 3 205 arbres, 360 lignes TC… ; autour du carrefour, **édité févr.–août 2026 (état après travaux)** | API OSM 0.6 `/map` par 16 dalles (Overpass indisponible depuis le proxy) | `osm.py` |
| **BD TOPO v3** (IGN) | 6 890 tronçons de route (largeur de chaussée, nb de voies, sens, vitesse moyenne, voies bus, gestionnaire…), bâtiments, végétation, haies, équipements de transport… (24 classes) | WFS `https://data.geopf.fr/wfs` `BDTOPO_V3:*` | `bdtopo.py` |
| **Levés topographiques Grenoble-Alpes Métropole** (« geoflux ») | **marquages au sol 3D** (lignes + symboles : vélo, piéton, flèches, « 30 », BUS…), bordures, caniveaux, limites de revêtement, seuils, glissières, arbres… issus des plans topo (`Meylan_Topo.dwg`) ; **PCRS vecteur** (limites de voirie, changements de revêtement…) ; graphe de voirie ; aménagements cyclables ; P+R ; ouvrages d'art ; secteurs d'éclairage | WFS `https://geoflux.grenoblealpesmetropole.fr/geoserver/wfs` (requêtes par dalles de 1 km, `/geoserver/ows` bloqué par le pare-feu) | `gam_geoflux.py` |
| Contour communal | polygone officiel | `https://geo.api.gouv.fr/communes/38229?format=geojson&geometry=contour` | — |

## 5. Documents (contexte du carrefour)

| Document | Contenu |
|---|---|
| Panneau « Aménagement carrefour Verdun/Vercors » (meylan.fr, PDF 1,18 × 0,9 m) | plan du réaménagement 2025 (ligne C1) superposé à l'ortho 5 cm : suppression du tourne-à-droite vers Vercors, quais de bus « La Revirée » mutualisés, traversées piétonnes et cycles sécurisées, îlots, plantations, entrée P+R déplacée |
| Pages meylan.fr « Travaux C1 : carrefour Verdun/Vercors », « avenue du Vercors », « point sur les chantiers » | calendrier des travaux 2025-2026 |
| Magazine « Meylan ma ville » n°163 (avril–mai 2025) | présentation du projet |

## 6. Limites connues
- **Aucune image aérienne ouverte postérieure aux travaux de 2025** : le PCRS 2022 et l'IGN 2024
  montrent l'état avant travaux ; le PCRS 2025 existe mais est en accès restreint.
- Pas de photo de rue Panoramax du carrefour après le 31 août 2025 (en plein chantier) ;
  l'avenue de Verdun n'est photographiée que dans le sens Montbonnot → Grenoble.
- Le LiDAR (2021) est antérieur aux nouveaux immeubles à l'est et aux travaux 2025.
- L'API `data.gouv.fr` et certains serveurs coupent souvent les connexions via le proxy :
  tous les scripts réessaient avec reprise.
