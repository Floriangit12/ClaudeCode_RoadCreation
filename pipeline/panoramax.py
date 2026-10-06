"""Photos de rue Panoramax : sélection autour d'un site, téléchargement HD et
découpage en tuiles 1000x1000 px (sans redimensionnement).

Le catalogue de toute la commune est produit par panoramax_enum.py :
  python3 -I pipeline/panoramax_enum.py --boundary <contour.geojson> --clip \
      --out data/raw/panoramax/meylan_panoramax.geojson

Puis :
  python3 pipeline/panoramax.py --site paquet_jardin --radius 150 [--asset hd]

Sorties :
  data/raw/panoramax/<site>/<date>_<id>_hd.jpg (+ .json : azimut, caméra...)
  data/raw/panoramax/<site>/tiles/<photo>/..._rRR_cCC.jpg (+ index.json)
  data/sites/<site>/panoramax_pictures.geojson (liste + métadonnées)
"""
from __future__ import annotations

import argparse
import json
import math
from concurrent.futures import ThreadPoolExecutor

from common import DATA, RAW, cut_tiles, download, site, to_l93


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=str(RAW / "panoramax" / "meylan_panoramax.geojson"))
    ap.add_argument("--site", default="paquet_jardin")
    ap.add_argument("--radius", type=float, default=150)
    ap.add_argument("--asset", default="hd", choices=["hd", "sd", "thumb"])
    ap.add_argument("--since", default=None)
    ap.add_argument("--no-tiles", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    cx, cy = site(a.site)["center_l93"]
    feats = json.load(open(a.catalog))["features"]
    sel = []
    for f in feats:
        p = f["properties"]
        x, y = to_l93(p["lon"], p["lat"])
        d = math.hypot(x - cx, y - cy)
        if d <= a.radius and (not a.since or (p["datetime"] or "") >= a.since):
            p["dist_site_m"] = round(d, 1)
            p["dx_e_m"], p["dy_n_m"] = round(x - cx, 1), round(y - cy, 1)
            sel.append(f)
    sel.sort(key=lambda f: f["properties"]["dist_site_m"])
    print(len(sel), "photos à moins de", a.radius, "m")

    out = RAW / "panoramax" / a.site
    out.mkdir(parents=True, exist_ok=True)

    def job(f):
        p = f["properties"]
        name = f"{(p['datetime'] or '')[:10]}_{p['id']}_{a.asset}"
        img = download(p[a.asset], out / f"{name}.jpg")
        (out / f"{name}.json").write_text(json.dumps(p, indent=1, ensure_ascii=False))
        p["local_file"] = img.name
        if not a.no_tiles:
            idx = cut_tiles(img, out / "tiles" / name, prefix=name)
            p["n_tiles"] = len(idx)
        return p

    with ThreadPoolExecutor(a.workers) as ex:
        for p in ex.map(job, sel):
            print(f"{p['dist_site_m']:6.1f} m  {p['datetime'][:10]}  {p['projection']:15s} "
                  f"{p.get('n_tiles', 0):3d} tuiles  {p['local_file']}")
    dest = DATA / "sites" / a.site / "panoramax_pictures.geojson"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"type": "FeatureCollection", "features": sel},
                               ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
