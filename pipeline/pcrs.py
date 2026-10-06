"""Ortho PCRS 5 cm (Plan Corps de Rue Simplifié) de Grenoble-Alpes Métropole,
diffusé en open data par le CRAIG (drive WebDAV, utilisateur `opendata` sans
mot de passe). Campagne couvrant Meylan : grenoble_alpes_2022 (PVA 2022-05).

Dalles GeoTIFF 200 m x 200 m (4000 x 4000 px, EPSG:2154, JPEG interne).
Chaque dalle est découpée en 16 tuiles JPEG 1000 x 1000 px (50 m x 50 m) —
aucun redimensionnement. Option --roads-only : ne garder que les tuiles qui
touchent la voirie (OSM, tampon 12 m) pour se concentrer sur la chaussée.

Usage :
  python3 pipeline/pcrs.py --site paquet_jardin            # 300 m x 300 m
  python3 pipeline/pcrs.py --commune --roads-only          # toute la commune
"""
from __future__ import annotations

import argparse
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from PIL import Image
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union

from common import DATA, RAW, TILE_PX, download, site
from common import _to_l93  # noqa: PLC2701

DAV = "https://drive.opendata.craig.fr/public.php/webdav/ortho/PCRS_5cm"
AUTH = ("opendata", "")
OUT = RAW / "pcrs5cm"


def dallage() -> gpd.GeoDataFrame:
    z = OUT / "dallage_pcrs_opendata.gpkg.zip"
    if not z.exists():
        download(f"{DAV}/dallage_pcrs_opendata.gpkg.zip", z, auth=AUTH)
    gpkg = OUT / "dallage_pcrs_opendata.gpkg"
    if not gpkg.exists():
        zipfile.ZipFile(z).extractall(OUT)
    return gpd.read_file(gpkg).to_crs(2154)


def area(args):
    if args.commune:
        g = json.loads((RAW / "meylan_contour.geojson").read_text())
        return transform(lambda x, y, z=None: _to_l93.transform(x, y), shape(g["geometry"])), "meylan"
    s = site(args.site)
    cx, cy = s["center_l93"]
    h = args.half or s["half_size_m"]
    return box(cx - h, cy - h, cx + h, cy + h), args.site


def road_mask():
    fc = json.loads((DATA / "vector" / "osm" / "roads.geojson").read_text())
    lines = [transform(lambda x, y, z=None: _to_l93.transform(x, y), shape(f["geometry"]))
             for f in fc["features"]
             if f["properties"].get("highway") not in ("service", "track", "path")
             or f["properties"].get("service") in (None, "alley")]
    return unary_union([g.buffer(12) for g in lines])


def cut(tif: Path, out_dir: Path, keep=None):
    """Découpe une dalle 4000x4000 en tuiles 1000x1000 (+ fichier monde)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    with rasterio.open(tif) as src:
        res = src.res[0]
        arr = None
        for r in range(src.height // TILE_PX):
            for c in range(src.width // TILE_PX):
                x0 = src.bounds.left + c * TILE_PX * res
                y1 = src.bounds.top - r * TILE_PX * res
                b = (x0, y1 - TILE_PX * res, x0 + TILE_PX * res, y1)
                if keep is not None and not keep.intersects(box(*b)):
                    continue
                name = f"pcrs5cm_{int(b[0])}_{int(b[1])}.jpg"
                f = out_dir / name
                if not f.exists():
                    if arr is None:
                        arr = src.read([1, 2, 3])
                    t = arr[:, r * TILE_PX:(r + 1) * TILE_PX, c * TILE_PX:(c + 1) * TILE_PX]
                    Image.fromarray(np.moveaxis(t, 0, -1)).save(f, quality=92)
                    f.with_suffix(".jgw").write_text(
                        f"{res}\n0\n0\n{-res}\n{b[0] + res / 2}\n{b[3] - res / 2}\n")
                entries.append({"file": name, "l93_bbox": list(b), "res_m": res,
                                "dalle": tif.name})
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="paquet_jardin")
    ap.add_argument("--half", type=float, default=None)
    ap.add_argument("--commune", action="store_true")
    ap.add_argument("--roads-only", action="store_true")
    ap.add_argument("--no-tiles", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()

    zone, name = area(a)
    d = dallage()
    sel = d[d.intersects(zone)].sort_values("location")
    print(len(sel), "dalles PCRS ;", sel["campagne"].value_counts().to_dict(),
          "; dates PVA :", sorted(sel["date_pva"].astype(str).unique()))
    keep = zone.intersection(road_mask()) if a.roads_only else zone
    tiles_dir = OUT / "tiles" / name

    def job(row):
        tif = download(f"{DAV}/{row.location}", OUT / "dalles" / row.location, auth=AUTH)
        return [] if a.no_tiles else cut(tif, tiles_dir, keep)

    with ThreadPoolExecutor(a.workers) as ex:
        idx = [e for es in ex.map(job, sel.itertuples()) for e in es]
    meta = sel.drop(columns="geometry").astype(str).to_dict("records")
    if not a.no_tiles:
        (tiles_dir / "index.json").write_text(json.dumps(
            {"source": "PCRS 5cm Grenoble-Alpes Métropole (CRAIG open data)", "dalles": meta,
             "tiles": idx}, indent=1))
    print(len(idx), "tuiles 1000x1000 ->", tiles_dir)


if __name__ == "__main__":
    main()
