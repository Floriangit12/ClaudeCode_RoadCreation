"""Prépare les données versionnables :
- compresse les vecteurs de la commune (data/vector/<source>/*.geojson, lourds)
  en data/vector_gz/<source>/*.geojson.gz (lisibles par GDAL/QGIS via
  /vsigzip/ ou geopandas.read_file) ;
- copie les tuiles ortho 5 cm du site (1000x1000, 50 m) dans data/sites/<site>/
  pour qu'elles accompagnent l'analyse.

Usage : python3 pipeline/pack_data.py [--site paquet_jardin]
"""
from __future__ import annotations

import argparse
import gzip
import shutil

from common import DATA, RAW


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="paquet_jardin")
    a = ap.parse_args()
    for f in sorted((DATA / "vector").rglob("*.geojson")):
        dst = DATA / "vector_gz" / f.relative_to(DATA / "vector")
        dst = dst.with_suffix(".geojson.gz")
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "rb") as i, gzip.open(dst, "wb", compresslevel=9) as o:
            shutil.copyfileobj(i, o)
        print(f"{dst.relative_to(DATA)} {dst.stat().st_size // 1024} ko")
    for f in (DATA / "vector" / "osm").glob("*.json"):
        shutil.copy(f, DATA / "vector_gz" / "osm" / f.name)
    src = RAW / "pcrs5cm" / "tiles" / a.site
    if src.exists():
        dst = DATA / "sites" / a.site / "ortho5cm_2022"
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            shutil.copy(f, dst / f.name)
        print("tuiles 5 cm copiées ->", dst)


if __name__ == "__main__":
    main()
