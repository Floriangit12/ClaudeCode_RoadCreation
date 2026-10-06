"""Utilitaires partagés du pipeline de données Meylan.

- chargement de la configuration (config/meylan.json)
- HTTP avec reprises (le proxy sortant coupe parfois les connexions)
- transformations WGS84 <-> Lambert-93
- découpage d'images en tuiles carrées 1000x1000 px (sans redimensionnement)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from PIL import Image
from pyproj import Transformer

REPO = Path(__file__).resolve().parents[1]
CONFIG = json.loads((REPO / "config" / "meylan.json").read_text())
DATA = REPO / "data"
RAW = DATA / "raw"
TILE_PX = CONFIG["tiling"]["tile_px"]

USER_AGENT = "meylan-adas-sim/0.1 (research; contact via github floriangit12)"

_to_l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
_to_wgs = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)


def to_l93(lon: float, lat: float) -> tuple[float, float]:
    return _to_l93.transform(lon, lat)


def to_wgs84(x: float, y: float) -> tuple[float, float]:
    return _to_wgs.transform(x, y)


def site(name: str = "paquet_jardin") -> dict:
    return CONFIG["sites"][name]


def http_get(url: str, *, params=None, retries: int = 5, timeout=(30, 120),
             stream: bool = False, **kw) -> requests.Response:
    """GET avec reprises exponentielles (2, 4, 8, 16 s...)."""
    headers = {"User-Agent": USER_AGENT, **kw.pop("headers", {})}
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=headers,
                             stream=stream, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r
        except (requests.RequestException,) as e:  # noqa: PERF203
            last = e
            if i < retries - 1:
                time.sleep(2 ** (i + 1))
    raise RuntimeError(f"échec GET {url} après {retries} essais: {last}")


def download(url: str, dest: Path, *, params=None, retries: int = 8,
             chunk: int = 1 << 20, overwrite: bool = False, auth=None) -> Path:
    """Téléchargement robuste : reprise (HTTP Range) après coupure, délai de
    lecture court (une connexion figée par le proxy est abandonnée au bout de
    60 s) et contrôle de la taille finale annoncée par le serveur."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0 and not overwrite:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    total, last = None, None
    for i in range(retries):
        have = tmp.stat().st_size if tmp.exists() else 0
        headers = {"User-Agent": USER_AGENT}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with requests.get(url, params=params, headers=headers, auth=auth, stream=True,
                              timeout=(30, 60)) as r:
                if r.status_code == 416 and total and have >= total:
                    break
                r.raise_for_status()
                if r.status_code == 200:  # pas de reprise possible : on repart de zéro
                    have = 0
                    total = int(r.headers.get("content-length", 0)) or None
                elif r.status_code == 206:
                    cr = r.headers.get("content-range", "")
                    total = int(cr.rsplit("/", 1)[-1]) if "/" in cr else None
                with open(tmp, "ab" if have else "wb") as f:
                    for b in r.iter_content(chunk):
                        f.write(b)
            if total is None or tmp.stat().st_size >= total:
                break
        except (requests.RequestException, OSError) as e:
            last = e
        time.sleep(min(2 ** (i + 1), 30))
    else:
        raise RuntimeError(f"échec téléchargement {url}: {last}")
    if total is not None and tmp.stat().st_size != total:
        raise RuntimeError(f"taille incorrecte pour {dest.name}: {tmp.stat().st_size} != {total}")
    tmp.replace(dest)
    return dest


def tile_origins(length: int, tile: int = TILE_PX) -> list[int]:
    """Origines des tuiles sur un axe : pas de `tile`, la dernière tuile est
    recalée sur le bord (léger recouvrement) pour que toutes les tuiles soient
    exactement carrées sans padding ni redimensionnement."""
    if length <= tile:
        return [0]
    origins = list(range(0, length - tile + 1, tile))
    if origins[-1] + tile < length:
        origins.append(length - tile)
    return origins


def cut_tiles(img_path: Path, out_dir: Path, *, tile: int = TILE_PX,
              prefix: str | None = None, quality: int = 92,
              georef: dict | None = None) -> list[dict]:
    """Découpe une image en tuiles tile x tile px (aucun redimensionnement).

    georef (optionnel) = {"x0": ..., "y0": ..., "res": ...} : coin haut-gauche
    en Lambert-93 et résolution (m/px) ; l'emprise de chaque tuile est alors
    ajoutée à l'index.
    Retourne l'index des tuiles (écrit aussi dans out_dir/index.json).
    """
    img_path, out_dir = Path(img_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = prefix or img_path.stem
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(img_path)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    w, h = im.size
    index = []
    for r, oy in enumerate(tile_origins(h, tile)):
        for c, ox in enumerate(tile_origins(w, tile)):
            box = (ox, oy, min(ox + tile, w), min(oy + tile, h))
            name = f"{prefix}_r{r:02d}_c{c:02d}.jpg"
            im.crop(box).save(out_dir / name, quality=quality)
            entry = {"file": name, "px_box": box, "source": img_path.name}
            if georef:
                x0, y0, res = georef["x0"], georef["y0"], georef["res"]
                entry["l93_bbox"] = [x0 + box[0] * res, y0 - box[3] * res,
                                     x0 + box[2] * res, y0 - box[1] * res]
            index.append(entry)
    idx_path = out_dir / "index.json"
    old = json.loads(idx_path.read_text()) if idx_path.exists() else []
    old = [e for e in old if e.get("source") != img_path.name]
    idx_path.write_text(json.dumps(old + index, indent=1))
    return index
