# Simulateur ADAS — Meylan (Isère)

Objectif : construire un simulateur ADAS reproduisant la ville de **Meylan** (38229, agglomération
grenobloise), en priorité la **chaussée** : géométrie, voies, marquages (et leur usure), passages
piétons, aménagements cyclables, bordures, revêtement.

Étape 1 (ce dépôt, état actuel) : **collecte de toutes les données ouvertes utiles sur la commune**,
puis **analyse détaillée, vérifiée deux fois, du carrefour « Paquet Jardin »** (avenue de Verdun /
chemin de la Revirée / avenue du Vercors).

## Contenu

```
config/meylan.json          emprise de la commune, sites étudiés, taille des tuiles (1000 px)
pipeline/                   scripts de téléchargement / traitement (reproductibles)
  common.py                 HTTP robuste (reprise), Lambert-93 <-> WGS84, découpage 1000x1000
  osm.py                    OSM complet de la commune -> couches GeoJSON thématiques
  bdtopo.py                 BD TOPO v3 (IGN) par WFS
  gam_geoflux.py            levés topo 3D de la Métropole (marquages, bordures...), PCRS vecteur
  pcrs.py                   ortho PCRS 5 cm (CRAIG) -> tuiles 1000x1000 (50 m)
  ortho.py                  ortho IGN/CRAIG/Pléiades par WMS, directement en tuiles 1000x1000
  panoramax_enum.py         catalogue Panoramax de la commune (quadtree sur l'API STAC)
  panoramax.py              photos de rue HD autour d'un site + tuiles 1000x1000
  lidarhd_download.py       LiDAR HD IGN (nuages COPC + MNT/MNS/MNH 50 cm)
  lidar_raster.py           MNT, intensité (marquages), hauteurs de bordures, pentes d'un site
  site_extract.py           découpe de toutes les couches vectorielles autour d'un site
  render_overlay.py         superposition vecteurs / ortho pour contrôle
  tile_images.py            découpe de n'importe quelle image en 1000x1000
data/vector/                vecteurs de toute la commune (OSM, BD TOPO, GAM)
data/sites/paquet_jardin/   extraits du carrefour : vecteurs, LiDAR (tuiles), liste Panoramax
data/raw/                   données lourdes (non versionnées, re-téléchargeables)
analysis/paquet_jardin/     analyse du carrefour (rapport, constats vérifiés, carte d'assemblage)
docs/SOURCES.md             inventaire testé de toutes les sources, accès, dates, licences
```

## Reproduire

```bash
pip install -r requirements.txt
cd pipeline
python3 osm.py                                   # OSM commune
python3 bdtopo.py                                # BD TOPO commune
python3 gam_geoflux.py                           # levés topo Métropole
python3 pcrs.py --commune --roads-only           # ortho 5 cm (tuiles de voirie)
python3 ortho.py --source ign_year --layers ORTHOIMAGERY.ORTHOPHOTOS2024 --res 0.20 --commune
python3 -I panoramax_enum.py --boundary ../data/raw/meylan_contour.geojson --clip \
        --out ../data/raw/panoramax/meylan_panoramax.geojson
python3 lidarhd_download.py --aoi ../data/raw/meylan_l93.wkt --out ../data/raw/lidar
# site du carrefour
python3 site_extract.py --site paquet_jardin
python3 pcrs.py --site paquet_jardin
python3 panoramax.py --site paquet_jardin --radius 150
python3 lidar_raster.py --laz ../data/raw/lidar/npl/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz --res 0.15
```

Volumes (commune entière) : PCRS 5 cm 2,6 Go (427 dalles) + 0,9 Go de tuiles voirie ; LiDAR HD
4,6 Go ; ortho 20 cm 85 Mo ; Panoramax : catalogue 25 Mo (19 868 photos, 53,6 Go si tout en HD —
seules les 204 photos du carrefour sont téléchargées, 1,1 Go avec les tuiles).

## Règle de découpage des images
Toute image destinée à l'analyse visuelle est découpée en **carrés de 1000×1000 px sans
redimensionnement** : les orthos sont demandées/découpées directement à 1000 px par tuile (5 cm →
tuiles de 50 m ; 20 cm → 200 m), les photos 360° 5760×2880 donnent 6×3 tuiles (dernière
colonne/rangée recalée sur le bord), les rasters LiDAR 15 cm → tuiles de 150 m.
