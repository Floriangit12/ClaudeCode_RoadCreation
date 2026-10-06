"""Téléchargement d'orthophotos par requêtes WMS GetMap, directement en tuiles
carrées de 1000x1000 px (aucun redimensionnement côté analyse).

Chaque tuile couvre 1000*res mètres de côté en Lambert-93 et est nommée par
son coin bas-gauche : <prefix>_<x>_<y>.jpg + fichier monde .jgw + index.json.

Exemples :
  # 5 cm sur le carrefour Paquet Jardin (300 m x 300 m -> 36 tuiles)
  python3 pipeline/ortho.py --source ign_hr --res 0.05 --site paquet_jardin
  # 20 cm sur toute la commune
  python3 pipeline/ortho.py --source ign_hr --res 0.20 --commune
"""
from __future__ import annotations

import argparse
import io
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from common import CONFIG, DATA, RAW, TILE_PX, http_get, site, to_l93

# Sources WMS testées (voir docs/SOURCES.md). Les paramètres propres à chaque
# service sont ici ; `layers` peut être surchargé en ligne de commande.
SOURCES = {
    "ign_hr": {  # BD ORTHO HR IGN (~20 cm natif), Géoplateforme
        "url": "https://data.geopf.fr/wms-r",
        "layers": "HR.ORTHOIMAGERY.ORTHOPHOTOS",
        "version": "1.3.0", "crs": "EPSG:2154", "format": "image/jpeg",
    },
    "ign_year": {  # millésimes IGN : --layers ORTHOIMAGERY.ORTHOPHOTOS2021 ...
        "url": "https://data.geopf.fr/wms-r",
        "layers": "ORTHOIMAGERY.ORTHOPHOTOS2021",
        "version": "1.3.0", "crs": "EPSG:2154", "format": "image/jpeg",
    },
    "craig": {  # CRAIG Auvergne-Rhône-Alpes : --layers ortho_2024 ...
        "url": "https://wms.craig.fr/ortho",
        "layers": "ortho_2024",
        "version": "1.3.0", "crs": "EPSG:2154", "format": "image/jpeg",
    },
}


def bbox_l93_for_site(name: str, half: float | None = None):
    s = site(name)
    cx, cy = s["center_l93"]
    h = half or s["half_size_m"]
    return cx - h, cy - h, cx + h, cy + h


def bbox_l93_for_commune():
    x0, y0, x1, y1 = CONFIG["commune"]["bbox_wgs84"]
    xs, ys = zip(*(to_l93(x, y) for x, y in ((x0, y0), (x0, y1), (x1, y0), (x1, y1))))
    return min(xs), min(ys), max(xs), max(ys)


def grid(bbox, res, tile=TILE_PX):
    """Grille de tuiles alignée sur un multiple de la taille de tuile au sol."""
    step = tile * res
    x0 = math.floor(bbox[0] / step) * step
    y0 = math.floor(bbox[1] / step) * step
    nx = math.ceil((bbox[2] - x0) / step)
    ny = math.ceil((bbox[3] - y0) / step)
    for j in range(ny):
        for i in range(nx):
            yield (round(x0 + i * step, 3), round(y0 + j * step, 3),
                   round(x0 + (i + 1) * step, 3), round(y0 + (j + 1) * step, 3))


def fetch_tile(src, b, out: Path, prefix: str, res: float):
    name = f"{prefix}_{int(b[0])}_{int(b[1])}.jpg"
    f = out / name
    if not (f.exists() and f.stat().st_size > 0):
        params = {
            "SERVICE": "WMS", "VERSION": src["version"], "REQUEST": "GetMap",
            "LAYERS": src["layers"], "STYLES": "", "FORMAT": src["format"],
            "WIDTH": TILE_PX, "HEIGHT": TILE_PX,
            ("CRS" if src["version"] == "1.3.0" else "SRS"): src["crs"],
            "BBOX": ",".join(str(v) for v in b),
        }
        r = http_get(src["url"], params=params, timeout=180)
        if not r.headers.get("content-type", "").startswith("image"):
            raise RuntimeError(f"réponse non image pour {name}: {r.text[:300]}")
        if src["format"] == "image/jpeg":
            f.write_bytes(r.content)
        else:  # PNG 4 bandes (ex. Pléiades) -> RVB JPEG
            Image.open(io.BytesIO(r.content)).convert("RGB").save(f, quality=93)
        # fichier monde (centre du pixel haut-gauche)
        f.with_suffix(".jgw").write_text(
            f"{res}\n0\n0\n{-res}\n{b[0] + res / 2}\n{b[3] - res / 2}\n")
    return {"file": name, "l93_bbox": list(b), "res_m": res, "layer": src["layers"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="ign_hr", choices=sorted(SOURCES))
    ap.add_argument("--layers", help="surcharge du nom de couche WMS")
    ap.add_argument("--url", help="surcharge de l'URL WMS")
    ap.add_argument("--format", help="surcharge du format (image/png pour les couches 4 bandes)")
    ap.add_argument("--res", type=float, default=0.05, help="m/pixel")
    ap.add_argument("--site", default=None)
    ap.add_argument("--half", type=float, default=None, help="demi-côté (m) autour du site")
    ap.add_argument("--commune", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    src = dict(SOURCES[a.source])
    if a.layers:
        src["layers"] = a.layers
    if a.url:
        src["url"] = a.url
    if a.format:
        src["format"] = a.format
    if a.commune:
        bbox, zone = bbox_l93_for_commune(), "meylan"
    else:
        bbox, zone = bbox_l93_for_site(a.site or "paquet_jardin", a.half), a.site or "paquet_jardin"
    tag = f"{src['layers'].replace('.', '_')}_{int(round(a.res * 100))}cm"
    out = Path(a.out) if a.out else RAW / "ortho" / zone / tag
    out.mkdir(parents=True, exist_ok=True)
    tiles = list(grid(bbox, a.res))
    print(f"{len(tiles)} tuiles {TILE_PX}px à {a.res} m/px -> {out}")
    with ThreadPoolExecutor(a.workers) as ex:
        index = list(ex.map(lambda b: fetch_tile(src, b, out, tag, a.res), tiles))
    (out / "index.json").write_text(json.dumps(
        {"source": src, "res_m": a.res, "bbox_l93": bbox, "tiles": index}, indent=1))
    print("ok", len(index), "tuiles")


if __name__ == "__main__":
    main()
