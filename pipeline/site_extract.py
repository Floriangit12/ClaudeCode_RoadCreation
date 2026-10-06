"""Découpe toutes les couches vectorielles (OSM, BD TOPO, ...) sur l'emprise
d'un site (carré autour du centre) et les reprojette en Lambert-93 local.

Sortie : data/sites/<site>/vector/<source>_<couche>.geojson (WGS84) + un
résumé JSON des objets présents.

Usage : python3 pipeline/site_extract.py --site paquet_jardin [--half 200]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from shapely.geometry import box, mapping, shape

from common import DATA, site, to_wgs84


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="paquet_jardin")
    ap.add_argument("--half", type=float, default=None)
    a = ap.parse_args()
    s = site(a.site)
    cx, cy = s["center_l93"]
    h = a.half or s["half_size_m"]
    (x0, y0), (x1, y1) = to_wgs84(cx - h, cy - h), to_wgs84(cx + h, cy + h)
    clip = box(x0, y0, x1, y1)
    out = DATA / "sites" / a.site / "vector"
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for src_dir in sorted((DATA / "vector").iterdir()):
        if not src_dir.is_dir():
            continue
        for f in sorted(src_dir.glob("*.geojson")):
            fc = json.loads(f.read_text())
            kept = []
            for feat in fc["features"]:
                if not feat.get("geometry"):
                    continue
                g = shape(feat["geometry"])
                if g.intersects(clip):
                    kept.append({**feat, "geometry": mapping(g.intersection(clip))
                                 if g.geom_type not in ("Point", "MultiPoint") else feat["geometry"]})
            if kept:
                name = f"{src_dir.name}_{f.stem}"
                (out / f"{name}.geojson").write_text(json.dumps(
                    {"type": "FeatureCollection", "features": kept}, ensure_ascii=False, indent=0))
                summary[name] = len(kept)
    (out.parent / "vector_summary.json").write_text(json.dumps(
        {"site": a.site, "half_size_m": h, "bbox_wgs84": [x0, y0, x1, y1], "layers": summary},
        indent=1))
    for k, v in summary.items():
        print(f"{k:45s} {v}")


if __name__ == "__main__":
    main()
