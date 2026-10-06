"""Rasterisation des nuages LiDAR HD (IGN) sur un site :
  - MNT (sol, classe 2) : altitude moyenne par cellule + comblement des trous
  - intensité du sol : fait ressortir les marquages (peinture rétro-réfléchissante)
  - MNS (max toutes classes sauf bruit) et hauteur au-dessus du sol (bordures,
    îlots, mobilier, véhicules)
  - pente (%), et rendu PNG en tuiles 1000x1000 px

Usage :
  python3 pipeline/lidar_raster.py --laz data/raw/lidar/*.laz --site paquet_jardin --res 0.10
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import laspy
import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_origin
from scipy import ndimage

from common import DATA, cut_tiles, site


def load_points(paths, bbox):
    x0, y0, x1, y1 = bbox
    chunks = []
    for p in paths:
        with laspy.open(p) as f:
            for pts in f.chunk_iterator(5_000_000):
                x, y = pts.x, pts.y
                m = (x >= x0) & (x < x1) & (y >= y0) & (y < y1)
                if not m.any():
                    continue
                c = np.asarray(pts.classification)[m]
                chunks.append(np.column_stack([
                    np.asarray(x)[m], np.asarray(y)[m], np.asarray(pts.z)[m],
                    np.asarray(pts.intensity)[m].astype(float), c.astype(float),
                ]))
    return np.vstack(chunks) if chunks else np.empty((0, 5))


def grid_stat(pts, bbox, res, val_col, how="mean"):
    x0, y0, x1, y1 = bbox
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    ix = np.clip(((pts[:, 0] - x0) / res).astype(int), 0, w - 1)
    iy = np.clip(((y1 - pts[:, 1]) / res).astype(int), 0, h - 1)
    flat = iy * w + ix
    v = pts[:, val_col]
    if how == "mean":
        s = np.bincount(flat, weights=v, minlength=w * h)
        n = np.bincount(flat, minlength=w * h)
        out = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    elif how == "max":
        out = np.full(w * h, -np.inf)
        np.maximum.at(out, flat, v)
        out[np.isinf(out)] = np.nan
    else:
        raise ValueError(how)
    return out.reshape(h, w), np.bincount(flat, minlength=w * h).reshape(h, w)


def fill_nan(a, max_iter=50):
    """Comblement des trous par moyenne des voisins (itératif)."""
    a = a.copy()
    for _ in range(max_iter):
        m = np.isnan(a)
        if not m.any():
            break
        v = np.where(m, 0, a)
        k = np.ones((3, 3))
        s = ndimage.convolve(v, k, mode="nearest")
        n = ndimage.convolve((~m).astype(float), k, mode="nearest")
        a[m & (n > 0)] = (s / np.maximum(n, 1))[m & (n > 0)]
    return a


def to_png(a, lo, hi, path, cmap=None):
    v = np.clip((a - lo) / (hi - lo), 0, 1)
    v = np.nan_to_num(v, nan=0)
    if cmap == "terrain":
        r = np.clip(1.5 * v, 0, 1)
        g = np.clip(1.5 - np.abs(2 * v - 1) * 1.5, 0, 1)
        b = np.clip(1.5 * (1 - v), 0, 1)
        img = (np.dstack([r, g, b]) * 255).astype(np.uint8)
    else:
        img = (v * 255).astype(np.uint8)
    Image.fromarray(img).save(path)


def write_tif(a, bbox, res, path):
    with rasterio.open(path, "w", driver="GTiff", width=a.shape[1], height=a.shape[0],
                       count=1, dtype="float32", crs="EPSG:2154",
                       transform=from_origin(bbox[0], bbox[3], res, res),
                       nodata=np.nan, compress="deflate") as d:
        d.write(a.astype("float32"), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laz", nargs="+", required=True)
    ap.add_argument("--site", default="paquet_jardin")
    ap.add_argument("--half", type=float, default=None)
    ap.add_argument("--res", type=float, default=0.10)
    a = ap.parse_args()
    s = site(a.site)
    cx, cy = s["center_l93"]
    h = a.half or s["half_size_m"]
    bbox = (cx - h, cy - h, cx + h, cy + h)
    out = DATA / "sites" / a.site / "lidar"
    out.mkdir(parents=True, exist_ok=True)
    raw = DATA / "raw" / "lidar" / a.site
    raw.mkdir(parents=True, exist_ok=True)

    pts = load_points(a.laz, bbox)
    cls = pts[:, 4].astype(int)
    stats = {"n_points": int(len(pts)), "area_m2": (2 * h) ** 2,
             "density_pts_m2": round(len(pts) / (2 * h) ** 2, 1),
             "classes": {int(k): int(v) for k, v in zip(*np.unique(cls, return_counts=True))}}
    ground = pts[cls == 2]
    keep = pts[~np.isin(cls, (7, 18, 65, 66))]

    dtm, n_g = grid_stat(ground, bbox, a.res, 2, "mean")
    inten, _ = grid_stat(ground, bbox, a.res, 3, "mean")
    dsm, _ = grid_stat(keep, bbox, a.res, 2, "max")
    dtm_f = fill_nan(dtm)
    hag = dsm - dtm_f
    gy, gx = np.gradient(ndimage.gaussian_filter(dtm_f, 2), a.res)
    slope = np.hypot(gx, gy) * 100

    for name, arr in (("dtm", dtm_f), ("intensity_ground", inten), ("dsm", dsm),
                      ("height_above_ground", hag), ("slope_pct", slope)):
        write_tif(arr, bbox, a.res, raw / f"{name}_{int(a.res * 100)}cm.tif")

    zlo, zhi = np.nanpercentile(dtm_f, [1, 99])
    ilo, ihi = np.nanpercentile(inten, [2, 99.5])
    tag = f"{int(a.res * 100)}cm"
    pngs = {
        "dtm": (dtm_f, zlo, zhi, "terrain"),
        "intensity_ground": (fill_nan(inten, 3), ilo, ihi, None),
        "height_above_ground": (hag, 0, 0.5, None),  # 0..50 cm : bordures/îlots
        "slope_pct": (slope, 0, 10, "terrain"),
    }
    # intensité rehaussée (CLAHE) : rend lisibles les marquages au sol
    import cv2
    i8 = (np.clip((fill_nan(inten, 3) - ilo) / (ihi - ilo), 0, 1) * 255).astype(np.uint8)
    enh = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16)).apply(i8)
    Image.fromarray(enh).save(raw / f"intensity_enhanced_{tag}.png")
    georef = {"x0": bbox[0], "y0": bbox[3], "res": a.res}
    cut_tiles(raw / f"intensity_enhanced_{tag}.png", out / f"intensity_enhanced_{tag}",
              prefix=f"intensity_enhanced_{tag}", georef=georef)
    for name, (arr, lo, hi, cm) in pngs.items():
        p = raw / f"{name}_{tag}.png"
        to_png(arr, lo, hi, p, cm)
        cut_tiles(p, out / f"{name}_{tag}", prefix=f"{name}_{tag}", georef=georef)
    stats.update({"dtm_min": float(np.nanmin(dtm_f)), "dtm_max": float(np.nanmax(dtm_f)),
                  "ground_cells_with_points_pct": round(100 * float((n_g > 0).mean()), 1),
                  "res_m": a.res, "bbox_l93": bbox,
                  "intensity_p2_p99_5": [float(ilo), float(ihi)]})
    (out / f"stats_{tag}.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
