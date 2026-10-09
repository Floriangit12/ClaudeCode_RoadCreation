"""Outils communs de reconstruction (repère local, lecture des couches, rendus QA).

Toutes les couches de reconstruction sont stockées en Lambert-93 (EPSG:2154),
dans recon/out/<site>/ ; le passage au repère local (X, Y, Z relatifs à O) se
fait à l'export 3D (USD/OpenDRIVE).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

REPO = Path(__file__).resolve().parents[1]
SITE = "paquet_jardin"
O = (917279.43, 6460289.98, 216.30)              # origine locale (L93 + NGF-IGN69)
HALF = 150.0
BBOX = (O[0] - HALF, O[1] - HALF, O[0] + HALF, O[1] + HALF)
OUT = REPO / "recon" / "out" / SITE
SITE_DATA = REPO / "data" / "sites" / SITE
ORTHO5 = SITE_DATA / "ortho5cm_2022"             # tuiles pcrs5cm_<X>_<Y>.jpg (coin bas-gauche, 50 m)
PLAN = SITE_DATA / "plan_projet_2025" / "plan_L93.tif"
DTM15 = REPO / "data" / "raw" / "lidar" / SITE / "dtm_15cm.tif"
TILE = 1000
RES = 0.05

_wgs2l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
_l932wgs = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)


def uv_to_l93(u, v):
    """Repère d'axe de Verdun (u vers le NE, v vers le NW) -> Lambert-93."""
    return O[0] + 0.70710678 * (u - v), O[1] + 0.70710678 * (u + v)


def l93_to_uv(x, y):
    dx, dy = x - O[0], y - O[1]
    return 0.70710678 * (dx + dy), 0.70710678 * (dy - dx)


def to_local(x, y, z=None):
    return (x - O[0], y - O[1]) if z is None else (x - O[0], y - O[1], z - O[2])


def wgs_geom_to_l93(g):
    return transform(lambda x, y, z=None: _wgs2l93.transform(x, y), g)


def load_site_vector(name: str, l93=True):
    """Couche de data/sites/<site>/vector/<name>.geojson (WGS84) -> liste (geom, props)."""
    fc = json.loads((SITE_DATA / "vector" / f"{name}.geojson").read_text())
    out = []
    for f in fc["features"]:
        if not f.get("geometry"):
            continue
        g = shape(f["geometry"])
        out.append((wgs_geom_to_l93(g) if l93 else g, f["properties"]))
    return out


def write_layer(path: Path, feats, crs="EPSG:2154"):
    """feats : liste (geom_shapely_L93, props)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection",
          "crs": {"type": "name", "properties": {"name": f"urn:ogc:def:crs:{crs.replace(':', '::')}"}},
          "features": [{"type": "Feature", "properties": p, "geometry": mapping(g)} for g, p in feats]}
    path.write_text(json.dumps(fc, ensure_ascii=False))


def read_layer(path: Path):
    fc = json.loads(Path(path).read_text())
    return [(shape(f["geometry"]), f["properties"]) for f in fc["features"] if f.get("geometry")]


def sample_raster(path, xs, ys):
    with rasterio.open(path) as r:
        vals = np.array([v[0] for v in r.sample(zip(xs, ys))], dtype=float)
        if r.nodata is not None:
            vals[vals == r.nodata] = np.nan
    return vals


def ortho_tile(x0, y0):
    """Tuile ortho 5 cm dont le coin bas-gauche est (x0, y0) (multiples de 50 m)."""
    p = ORTHO5 / f"pcrs5cm_{int(x0)}_{int(y0)}.jpg"
    return Image.open(p).convert("RGB") if p.exists() else Image.new("RGB", (TILE, TILE), (40, 40, 40))


def tiles_covering(bbox):
    x0 = int(np.floor(bbox[0] / 50) * 50)
    y0 = int(np.floor(bbox[1] / 50) * 50)
    return [(x, y) for x in range(x0, int(bbox[2]), 50) for y in range(y0, int(bbox[3]), 50)]


def draw_geom(dr, g, x0, y1, style):
    """Dessine une géométrie L93 sur une image dont le coin haut-gauche est (x0, y1), 5 cm/px."""
    def px(c):
        return ((c[0] - x0) / RES, (y1 - c[1]) / RES)
    col = style.get("color", (255, 0, 255))
    w = style.get("width", 2)
    fill = style.get("fill")
    gt = g.geom_type
    if gt in ("Polygon", "MultiPolygon"):
        for p in getattr(g, "geoms", [g]):
            pts = [px(c) for c in p.exterior.coords]
            if fill is not None:
                dr.polygon(pts, fill=fill)
            dr.line(pts, fill=col, width=w)
            for h in p.interiors:
                dr.line([px(c) for c in h.coords], fill=col, width=w)
    elif gt in ("LineString", "MultiLineString", "LinearRing"):
        for ln in getattr(g, "geoms", [g]):
            dr.line([px(c) for c in ln.coords], fill=col, width=w)
    elif gt in ("Point", "MultiPoint"):
        r = style.get("radius", 6)
        for p in getattr(g, "geoms", [g]):
            x, y = px(p.coords[0])
            dr.ellipse((x - r, y - r, x + r, y + r), outline=col, width=w)


def qa_tiles(layers, out_dir: Path, bbox=None, tiles=None, base="ortho", alpha=110):
    """Rendus de contrôle 1000x1000 px (5 cm/px) : layers = [(feats, style_fn)] où
    style_fn(props) -> dict(color, width, fill). base = 'ortho' (PCRS 2022) ou 'none'."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tl = tiles or tiles_covering(bbox or BBOX)
    written = []
    for (tx, ty) in tl:
        img = ortho_tile(tx, ty) if base == "ortho" else Image.new("RGB", (TILE, TILE), (30, 30, 30))
        over = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(over)
        from shapely.geometry import box
        tb = box(tx, ty, tx + 50, ty + 50)
        for feats, style_fn in layers:
            for g, p in feats:
                if not g.intersects(tb):
                    continue
                st = dict(style_fn(p))
                if st.get("fill") is not None and len(st["fill"]) == 3:
                    st["fill"] = (*st["fill"], alpha)
                draw_geom(dr, g, tx, ty + 50, st)
        im = Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")
        f = out_dir / f"qa_{tx}_{ty}.jpg"
        im.save(f, quality=90)
        written.append(str(f))
    return written
