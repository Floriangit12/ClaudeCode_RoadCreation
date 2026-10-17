"""Dalles de l'ortho IGN 20 cm (WMS Géoplateforme, couche HR.ORTHOIMAGERY.ORTHOPHOTOS, licence Etalab 2.0) le
long des axes du lot B, avec leur fichier monde (.jgw, Lambert-93). Seules les dalles de 200 m qui touchent
l'axe (ligne OSM tamponnée de --tampon m) sont demandées.

    python recon/generateur/meylan/auto_outils/ortho_ign.py --ways 759037980 4247774 --tampon 80 --nom a41_ouest

Sorties (non versionnées) : recon/out/generateur/meylan/auto_travail_lotB/ortho/ign_hr/*.jpg + .jgw, que
recon/pcg/vision/decoupe.py ortho lit avec --source "<motif>" --pas 0.2.
"""
import argparse
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, box
from shapely.ops import unary_union

RACINE = Path(__file__).resolve().parents[4]
TRAVAIL = RACINE / "recon" / "out" / "generateur" / "meylan" / "auto_travail_lotB"
UA = "ClaudeCode_RoadCreation/1.0 (recherche voirie Meylan)"
WMS = "https://data.geopf.fr/wms-r"
COUCHE = "HR.ORTHOIMAGERY.ORTHOPHOTOS"
PX = 1000
PAS = 0.2
T = Transformer.from_crs(4326, 2154, always_xy=True)


def dalle(x0, y0, out):
    x1, y1 = x0 + PX * PAS, y0 + PX * PAS
    f = out / ("ign_hr_%d_%d.jpg" % (x0, y0))
    if not (f.exists() and f.stat().st_size > 0):
        q = urllib.parse.urlencode({"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": COUCHE,
                                    "STYLES": "", "FORMAT": "image/jpeg", "WIDTH": PX, "HEIGHT": PX,
                                    "CRS": "EPSG:2154", "BBOX": "%d,%d,%d,%d" % (x0, y0, x1, y1)})
        for essai in range(4):
            try:
                req = urllib.request.Request(WMS + "?" + q, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=180) as r:
                    if not r.headers.get("content-type", "").startswith("image"):
                        raise RuntimeError(r.read()[:300])
                    f.write_bytes(r.read())
                break
            except Exception:
                if essai == 3:
                    raise
                time.sleep(3 * (essai + 1))
        f.with_suffix(".jgw").write_text("%s\n0\n0\n%s\n%s\n%s\n" % (PAS, -PAS, x0 + PAS / 2, y1 - PAS / 2))
    return f.name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ways", nargs="*", type=int, default=[])
    ap.add_argument("--emprise", nargs=4, type=float, help="x0 y0 x1 y1 L93")
    ap.add_argument("--tampon", type=float, default=80.0)
    ap.add_argument("--routes", default=str(TRAVAIL / "osm" / "routes_toutes.json"))
    a = ap.parse_args()
    out = TRAVAIL / "ortho" / "ign_hr"
    out.mkdir(parents=True, exist_ok=True)
    zones = []
    if a.ways:
        R = {e["id"]: e for e in json.load(open(a.routes, encoding="utf-8"))["elements"]}
        for w in a.ways:
            L = LineString([T.transform(p["lon"], p["lat"]) for p in R[w]["geometry"]])
            zones.append(L.buffer(a.tampon))
    if a.emprise:
        zones.append(box(*a.emprise))
    Z = unary_union(zones)
    step = PX * PAS
    x0, y0, x1, y1 = Z.bounds
    n = 0
    for i in range(math.floor(x0 / step), math.ceil(x1 / step)):
        for j in range(math.floor(y0 / step), math.ceil(y1 / step)):
            b = box(i * step, j * step, (i + 1) * step, (j + 1) * step)
            if b.intersects(Z):
                dalle(int(i * step), int(j * step), out)
                n += 1
    print(n, "dalles ->", out)


if __name__ == "__main__":
    main()
