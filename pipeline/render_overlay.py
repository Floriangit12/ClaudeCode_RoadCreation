"""Superpose les couches vectorielles d'un site (OSM / BD TOPO) sur les tuiles
d'ortho 1000x1000 px, pour contrôler le calage et lire la géométrie.

Usage :
  python3 pipeline/render_overlay.py --tiles data/raw/ortho/paquet_jardin/<dossier> \
      --site paquet_jardin --out data/sites/paquet_jardin/overlay_20cm
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import shape

from common import DATA, to_l93

STYLE = {  # couche : (couleur, largeur)
    "osm_roads": ((255, 0, 0), 3),
    "osm_cycleways": ((0, 200, 0), 3),
    "osm_footways": ((255, 0, 255), 2),
    "osm_crossings": ((255, 255, 0), 7),
    "osm_traffic_signals": ((255, 120, 0), 9),
    "osm_kerbs": ((0, 255, 255), 6),
    "osm_public_transport": ((0, 120, 255), 6),
    "bdtopo_troncon_de_route": ((0, 0, 255), 2),
}


def iter_coords(g):
    if g.geom_type in ("Point",):
        yield [g.coords[0]]
    elif g.geom_type in ("LineString",):
        yield list(g.coords)
    elif g.geom_type == "Polygon":
        yield list(g.exterior.coords)
    elif hasattr(g, "geoms"):
        for p in g.geoms:
            yield from iter_coords(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--site", default="paquet_jardin")
    ap.add_argument("--out", required=True)
    ap.add_argument("--layers", nargs="*", default=list(STYLE))
    a = ap.parse_args()
    idx = json.loads((Path(a.tiles) / "index.json").read_text())
    vec = DATA / "sites" / a.site / "vector"
    layers = {}
    for name in a.layers:
        f = vec / f"{name}.geojson"
        if f.exists():
            layers[name] = [shape(ft["geometry"]) for ft in json.loads(f.read_text())["features"]]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for t in idx["tiles"]:
        x0, y0, x1, y1 = t["l93_bbox"]
        res = t["res_m"]
        im = Image.open(Path(a.tiles) / t["file"]).convert("RGB")
        dr = ImageDraw.Draw(im)

        def px(lon, lat, *_):
            x, y = to_l93(lon, lat)
            return ((x - x0) / res, (y1 - y) / res)
        for name, geoms in layers.items():
            col, w = STYLE[name]
            for g in geoms:
                for cs in iter_coords(g):
                    pts = [px(*c) for c in cs]
                    if len(pts) == 1:
                        x, y = pts[0]
                        dr.ellipse((x - w, y - w, x + w, y + w), outline=col, width=2)
                    else:
                        dr.line(pts, fill=col, width=w)
        im.save(out / t["file"], quality=90)
    print("ok", len(idx["tiles"]), "tuiles ->", out)


if __name__ == "__main__":
    main()
