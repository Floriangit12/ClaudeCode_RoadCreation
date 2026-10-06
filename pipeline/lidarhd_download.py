#!/usr/bin/env python3
"""Download IGN LiDAR HD (COPC point clouds + MNT/MNS/MNH 50 cm) for an area.

Tile discovery: Géoplateforme WFS layer IGNF_LIDAR-HD_METADONNEE:metadata
(one feature per 1 km tile, with ready-made download URLs url_npl / url_mnt / url_mns / url_mnh).

usage:
  python3 pipeline/lidarhd_download.py --aoi meylan_l93.wkt --out DIR [--products npl,mnt,mns,mnh] [--min-area 100] [--dry-run]
AOI is a WKT polygon in EPSG:2154.
"""
import argparse, json, os, sys, time
import requests

from common import download
from shapely import wkt
from shapely.geometry import shape

WFS = ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
       "&TYPENAMES=IGNF_LIDAR-HD_METADONNEE:metadata&OUTPUTFORMAT=application/json"
       "&SRSNAME=EPSG:2154&BBOX={x0},{y0},{x1},{y1},EPSG:2154&COUNT=1000")


def get(url, stream=False, tries=5, timeout=300):
    for i in range(tries):
        try:
            r = requests.get(url, stream=stream, timeout=timeout)
            if r.status_code == 200:
                return r
            print(f"  HTTP {r.status_code} try {i+1}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  {type(e).__name__} try {i+1}", file=sys.stderr)
        time.sleep(3 * (i + 1))
    raise RuntimeError("failed: " + url)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoi", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--products", default="npl,mnt,mns,mnh")
    ap.add_argument("--min-area", type=float, default=100.0, help="skip tiles overlapping AOI by less than this many m2")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    aoi = wkt.loads(open(a.aoi).read())
    x0, y0, x1, y1 = aoi.bounds
    fc = get(WFS.format(x0=int(x0) - 1, y0=int(y0) - 1, x1=int(x1) + 1, y1=int(y1) + 1)).json()
    tiles = []
    for f in fc["features"]:
        g = shape(f["geometry"])
        ov = g.intersection(aoi).area
        if ov >= a.min_area:
            tiles.append((f["properties"], ov))
    tiles.sort(key=lambda t: t[0]["coordonnees_nw"])
    os.makedirs(a.out, exist_ok=True)
    json.dump([dict(t[0], overlap_m2=t[1]) for t in tiles], open(os.path.join(a.out, "tiles.json"), "w"), indent=1)
    print(f"{len(tiles)} tiles; total points {sum(t[0]['nombre_points'] for t in tiles):,}")
    for p, ov in tiles:
        for prod in a.products.split(","):
            url = p["url_" + prod]
            name = url.split("FILENAME=")[-1] if "FILENAME=" in url else url.rsplit("/", 1)[-1]
            dst = os.path.join(a.out, prod, name)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                continue
            print(p["coordonnees_nw"], prod, name, "(dry)" if a.dry_run else "")
            if a.dry_run:
                continue
            download(url, dst)  # reprise HTTP Range + contrôle de taille
            time.sleep(1.1)  # data.geopf.fr download API advertises x-ratelimit-limit-second: 1


if __name__ == "__main__":
    main()
