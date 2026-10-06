"""Plan du projet de réaménagement 2025 (ligne C1) du carrefour Verdun/Vercors :
extraction de l'image raster intégrée au PDF du panneau (meylan.fr), puis
géoréférencement automatique sur l'ortho PCRS 5 cm (SIFT + RANSAC, similitude),
et découpage en tuiles 1000x1000 px natives (aucun rééchantillonnage du plan).

Le fond du plan est l'ortho PCRS 2022 : l'appariement est donc très précis
(≈ 260 points homologues, RMSE ≈ 3 cm, ≈ 4,1 cm/px, rotation ≈ −46°).

Sorties : data/sites/<site>/plan_projet_2025/
  plan_L93.tif         GeoTIFF à géotransformation tournée (pixels du plan intacts)
  georef.json          affine pixel -> Lambert-93, nb de points, RMSE
  tuiles/*.jpg         tuiles 1000x1000 + index.json (affine de chaque tuile)

Usage : python3 pipeline/plan_projet.py
"""
from __future__ import annotations

import argparse
import json
import math

import cv2
import numpy as np
import pymupdf
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.merge import merge

from common import DATA, RAW, cut_tiles

PDF = RAW / "docs" / "panneau_amenagement_carrefour_verdun_vercors.pdf"


def extract_largest_image(pdf, out_png):
    doc = pymupdf.open(pdf)
    best = None
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            info = doc.extract_image(xref)
            n = info["width"] * info["height"]
            if best is None or n > best[0]:
                best = (n, xref, info)
    _, xref, info = best
    pix = pymupdf.Pixmap(doc, xref)
    if pix.n - pix.alpha > 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    pix.save(out_png)
    return xref, info["width"], info["height"]


def georef(plan_png, tiles, outdir):
    srcs = [rasterio.open(t) for t in tiles]
    mos, tr = merge(srcs, res=0.10, resampling=Resampling.average)
    mos = np.moveaxis(mos[:3], 0, -1).astype(np.uint8)
    g_m = cv2.cvtColor(mos, cv2.COLOR_RGB2GRAY)
    plan = cv2.cvtColor(cv2.imread(str(plan_png)), cv2.COLOR_BGR2RGB)
    sift = cv2.SIFT_create(nfeatures=30000)
    km, dm = sift.detectAndCompute(g_m, None)
    best = None
    for s in (0.35, 0.45, 0.5, 0.6):  # échelle du plan inconnue (4-6 cm/px)
        p = cv2.resize(plan, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        kp, dp = sift.detectAndCompute(cv2.cvtColor(p, cv2.COLOR_RGB2GRAY), None)
        if dp is None or len(kp) < 10:
            continue
        ms = cv2.BFMatcher(cv2.NORM_L2).knnMatch(dp, dm, k=2)
        good = [m for m, n in ms if m.distance < 0.75 * n.distance]
        if len(good) < 8:
            continue
        src = np.float32([kp[m.queryIdx].pt for m in good]) / s
        dst = np.float32([km[m.trainIdx].pt for m in good])
        M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                             ransacReprojThreshold=4.0, maxIters=20000)
        ni = int(inl.sum()) if inl is not None else 0
        if M is not None and (best is None or ni > best[0]):
            best = (ni, M, src[inl.ravel() == 1], dst[inl.ravel() == 1])
    ni, M, s_in, d_in = best
    A = np.vstack([M, [0, 0, 1]])
    T = np.array([[tr.a, tr.b, tr.c], [tr.d, tr.e, tr.f], [0, 0, 1]])
    half = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1]])
    G = T @ half @ A                     # centre de pixel du plan -> L93
    res = (np.c_[s_in, np.ones(len(s_in))] @ A.T)[:, :2] - d_in
    info = {"points_homologues": ni,
            "resolution_plan_m": math.hypot(M[0, 0], M[1, 0]) * 0.10,
            "rotation_deg": math.degrees(math.atan2(M[1, 0], M[0, 0])),
            "rmse_m": float(np.sqrt((res ** 2).sum(1).mean()) * 0.10),
            "affine_pixel_centre_vers_L93": G[:2].tolist(),
            "reference": [str(t) for t in tiles]}
    a, b, c = G[0]
    d, e, f = G[1]
    aff = Affine(a, b, c - 0.5 * a - 0.5 * b, d, e, f - 0.5 * d - 0.5 * e)
    with rasterio.open(outdir / "plan_L93.tif", "w", driver="GTiff", width=plan.shape[1],
                       height=plan.shape[0], count=3, dtype="uint8", crs="EPSG:2154",
                       transform=aff, compress="deflate") as o:
        o.write(np.moveaxis(plan, -1, 0))
    (outdir / "georef.json").write_text(json.dumps(info, indent=1))
    return info, aff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="paquet_jardin")
    a = ap.parse_args()
    out = DATA / "sites" / a.site / "plan_projet_2025"
    out.mkdir(parents=True, exist_ok=True)
    png = RAW / "docs" / "plan_projet_raster.png"
    xref, w, h = extract_largest_image(PDF, png)
    print("image intégrée xref", xref, w, "x", h)
    tiles = sorted((RAW / "pcrs5cm" / "dalles").rglob("*.tif"))
    # dalles 200 m autour du carrefour
    near = [t for t in tiles if t.stem in ("9170-64602", "9170-64604", "9172-64602", "9172-64604")]
    info, aff = georef(png, near, out)
    print(json.dumps({k: v for k, v in info.items() if k != "reference"}, indent=1))
    idx = cut_tiles(png, out / "tuiles", prefix="plan_projet")
    for e in idx:  # affine (coin) de chaque tuile en Lambert-93
        c0, r0 = e["px_box"][:2]
        t = aff * Affine.translation(c0, r0)
        e["affine_L93"] = [t.a, t.b, t.c, t.d, t.e, t.f]
    (out / "tuiles" / "index.json").write_text(json.dumps(idx, indent=1))
    print(len(idx), "tuiles 1000x1000 ->", out / "tuiles")


if __name__ == "__main__":
    main()
