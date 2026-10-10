#!/usr/bin/env python
"""Contrôle automatique des marquages v2 sur l'ortho PCRS 5 cm 2022 (agent VISION-ORTHO-A).

Pour chaque marquage v2 dont le centre tombe dans une des dalles données : contraste de luminance
entre l'empreinte (polygone, ou axe épaissi à largeur_m) et un anneau de 0,15-0,45 m autour, à la
position décrite puis au meilleur décalage (dx, dy) dans ±0,6 m (corrélation FFT). Sert à trier les
entités à revoir à l'œil : il ne remplace pas la lecture des découpes.

  python contraste_marquages.py <sortie.json> [tuile ...]   (défaut : les 25 dalles A)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlay as ov  # noqa: E402

MARGE = 1.5
DMAX = 0.6


def anneaux(g):
    t = g["type"]
    if t == "Polygon":
        return [g["coordinates"]], True
    if t == "MultiPolygon":
        return g["coordinates"], True
    if t == "LineString":
        return [[g["coordinates"]]], False
    if t == "MultiLineString":
        return [[c] for c in g["coordinates"]], False
    return [], False


def masque(f, x0, yh, W, H):
    g = f["geometry"]
    polys, ferme = anneaux(g)
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    P = lambda c: ((c[0] - x0) / ov.PAS, (yh - c[1]) / ov.PAS)
    larg = f["properties"].get("largeur_m") or 0.12
    for p in polys:
        if ferme:
            d.polygon([P(c) for c in p[0]], fill=255)
            for h in p[1:]:
                d.polygon([P(c) for c in h], fill=0)
        else:
            d.line([P(c) for c in p[0]], fill=255, width=max(2, int(round(larg / ov.PAS))))
    return np.asarray(im) > 0


def corr(img, m):
    F = np.fft.rfft2(img)
    G = np.fft.rfft2(m.astype(float))
    return np.fft.irfft2(F * np.conj(G), s=img.shape)


def analyser(f):
    xs, ys = [], []
    polys, _ = anneaux(f["geometry"])
    for p in polys:
        for r in p:
            for c in r:
                xs.append(c[0]); ys.append(c[1])
    x0, x1 = min(xs) - MARGE, max(xs) + MARGE
    y0, y1 = min(ys) - MARGE, max(ys) + MARGE
    img, (xg, yh) = ov.mosaique(x0, y0, x1, y1)
    H, W = img.shape[:2]
    if img.max() == 0:
        return None
    a = img.astype(float)
    jaune = f["properties"].get("couleur") == "jaune"
    lum = (a[..., 0] + a[..., 1]) / 2 - 0.5 * a[..., 2] if jaune else a.mean(axis=2)
    m_in = masque(f, xg, yh, W, H)
    if m_in.sum() < 4:
        return None
    mi = Image.fromarray(m_in.astype(np.uint8) * 255)
    d1 = np.asarray(mi.filter(ImageFilter.MaxFilter(7))) > 0      # +0,15 m
    d2 = np.asarray(mi.filter(ImageFilter.MaxFilter(19))) > 0     # +0,45 m
    ring = d2 & ~d1
    n_in, n_r = m_in.sum(), max(ring.sum(), 1)
    c_in = corr(lum, m_in) / n_in
    c_r = corr(lum, ring) / n_r
    sc = c_in - c_r                       # sc[dy, dx] : décalage (en px, circulaire) de l'empreinte
    k = int(DMAX / ov.PAS)
    best, arg = -1e9, (0, 0)
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            v = sc[dy % H, dx % W] - 0.4 * (dx * dx + dy * dy) ** 0.5   # léger a priori vers 0
            if v > best:
                best, arg = v, (dx, dy)
    s0 = float(sc[0, 0])
    sb = float(sc[arg[1] % H, arg[0] % W])
    # part des pixels de l'empreinte plus clairs que l'anneau + 25
    med_r = float(np.median(lum[ring])) if ring.any() else float(lum.mean())
    frac = float((lum[m_in] > med_r + 25).mean())
    return {"contraste": round(s0, 1), "contraste_best": round(sb, 1),
            "dx_m": round(arg[0] * ov.PAS, 2), "dy_m": round(-arg[1] * ov.PAS, 2),
            "part_claire": round(frac, 2), "n_px": int(n_in)}


def main():
    sortie = sys.argv[1]
    tuiles = sys.argv[2:] or ov.TUILES_A
    boites = [(float(t.split("_")[0]), float(t.split("_")[1])) for t in tuiles]
    res = []
    for f in ov.couches()["marquages"]:
        p = f["properties"]
        polys, _ = anneaux(f["geometry"])
        pts = [c for pp in polys for r in pp for c in r]
        cx, cy = sum(c[0] for c in pts) / len(pts), sum(c[1] for c in pts) / len(pts)
        t = next((f"{int(x)}_{int(y)}" for x, y in boites if x <= cx < x + 50 and y <= cy < y + 50), None)
        if t is None:
            continue
        r = analyser(f)
        if r is None:
            continue
        b = ov.etat_travaux(cx, cy, 0.3)
        res.append({"id": p["id"], "tuile": t, "classe": p.get("classe"), "type": p.get("type"), "etat": p.get("etat"),
                    "couleur": p.get("couleur"), "centre_l93": [round(cx, 2), round(cy, 2)], "travaux_bits": b, **r})
    Path(sortie).write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(res))


if __name__ == "__main__":
    main()
