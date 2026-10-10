#!/usr/bin/env python
"""Candidats d'affleurants (tampons, avaloirs, regards, grilles) sur l'ortho PCRS 5 cm 2022.

Détecteur de taches isolées (moyenne d'une boîte centrale contre l'anneau carré qui l'entoure, à
3 échelles : côté 0,45 / 0,65 / 0,95 m), normalisé par la dispersion de l'anneau, limité aux
surfaces circulées ou piétonnes de la carte de cohérence (chaussée, trottoir, piste, quai, parking,
accès, îlot) et hors marquages. Ce n'est qu'un tri : chaque candidat est revu à l'œil sur une
découpe numérotée (aucun candidat n'est une observation par lui-même).

  python candidats_affleurants.py <tuile> <sortie.json>
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlay as ov  # noqa: E402

CARTE = ov.DESC / "coherence/carte"
CLASSES_OK = {1, 2, 3, 4, 5, 8, 9}     # chaussée, trottoir, îlot, piste, quai, parking, accès
ECHELLES = [(4, 9), (6, 13), (9, 19)]    # demi-côtés (px) : centre, extérieur


def integrale(a):
    s = np.zeros((a.shape[0] + 1, a.shape[1] + 1))
    s[1:, 1:] = a.cumsum(0).cumsum(1)
    return s


def boite(S, r):
    """Somme sur la boîte (2r+1)² centrée en chaque pixel (bords répliqués par repli)."""
    H, W = S.shape[0] - 1, S.shape[1] - 1
    y = np.arange(H)[:, None]
    x = np.arange(W)[None, :]
    y0, y1 = np.clip(y - r, 0, H), np.clip(y + r + 1, 0, H)
    x0, x1 = np.clip(x - r, 0, W), np.clip(x + r + 1, 0, W)
    return S[y1, x1] - S[y0, x1] - S[y1, x0] + S[y0, x0], (y1 - y0) * (x1 - x0)


def masque_classes(xg, yh, W, H):
    try:
        cl = np.asarray(Image.open(CARTE / "classes_5cm.png"))
        g = json.loads((CARTE / "carte.json").read_text(encoding="utf-8"))["georef"]
    except Exception:
        return np.ones((H, W), bool)
    x0l, y1l = g["x0_local"] + ov.O[0], g["y1_local"] + ov.O[1]
    c0 = int(round((xg - x0l) / ov.PAS))
    r0 = int(round((y1l - yh) / ov.PAS))
    out = np.ones((H, W), bool)       # hors carte : pas de restriction
    rr0, rr1 = max(r0, 0), min(r0 + H, cl.shape[0])
    cc0, cc1 = max(c0, 0), min(c0 + W, cl.shape[1])
    if rr0 < rr1 and cc0 < cc1:
        sub = cl[rr0:rr1, cc0:cc1]
        out[rr0 - r0:rr1 - r0, cc0 - c0:cc1 - c0] = np.isin(sub, list(CLASSES_OK))
    return out


def masque_marquages(xg, yh, W, H):
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    P = lambda c: ((c[0] - xg) / ov.PAS, (yh - c[1]) / ov.PAS)
    for f in ov.couches()["marquages"] + ov._feats(ov.DONNEES / "marquages/marquages_2026.geojson"):
        g = f["geometry"]
        if g["type"] in ("Polygon", "MultiPolygon"):
            for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
                d.polygon([P(c) for c in p[0]], fill=255)
        elif g["type"] in ("LineString", "MultiLineString"):
            for l in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
                d.line([P(c) for c in l], fill=255, width=6)
    return np.asarray(im.filter(ImageFilter.MaxFilter(5))) > 0


def detecter(x0, y0, x1, y1, seuil=4.5, nmax=80):
    img, (xg, yh) = ov.mosaique(x0, y0, x1, y1)
    H, W = img.shape[:2]
    L = img.astype(float).mean(axis=2)
    S, S2 = integrale(L), integrale(L * L)
    ok = masque_classes(xg, yh, W, H) & ~masque_marquages(xg, yh, W, H)
    best = np.zeros((H, W))
    sgn = np.zeros((H, W))
    ech = np.zeros((H, W), int)
    for k, (ri, ro) in enumerate(ECHELLES):
        si, ni = boite(S, ri)
        so, no = boite(S, ro)
        q2, _ = boite(S2, ro)
        qi2, _ = boite(S2, ri)
        mi = si / ni
        nr = np.maximum(no - ni, 1)
        mr = (so - si) / nr
        vr = np.maximum((q2 - qi2) / nr - mr * mr, 1.0)
        z = (mi - mr) / np.sqrt(vr + 25.0)
        z = np.where(np.abs(mi - mr) > 12, z, 0)
        m = np.abs(z) > np.abs(best)
        best = np.where(m, z, best)
        sgn = np.where(m, np.sign(z), sgn)
        ech = np.where(m, k, ech)
    best = np.where(ok, np.abs(best), 0)
    # maxima locaux (fenêtre 0,8 m)
    im = Image.fromarray(np.clip(best * 20, 0, 255).astype(np.uint8))
    mx = np.asarray(im.filter(ImageFilter.MaxFilter(17))).astype(float) / 20
    pics = np.argwhere((best >= seuil) & (best >= mx - 1e-6))
    cands = []
    for r, c in pics:
        cands.append((best[r, c], r, c))
    cands.sort(reverse=True)
    out = []
    pris = []
    for v, r, c in cands:
        if any((r - a) ** 2 + (c - b) ** 2 < 16 ** 2 for a, b in pris):
            continue
        pris.append((r, c))
        x, y = xg + (c + 0.5) * ov.PAS, yh - (r + 0.5) * ov.PAS
        k = int(ech[r, c])
        out.append({"x": round(x, 2), "y": round(y, 2), "score": round(float(v), 1),
                    "polarite": "sombre" if sgn[r, c] < 0 else "clair", "cote_m": round((2 * ECHELLES[k][0] + 1) * ov.PAS, 2)})
        if len(out) >= nmax:
            break
    return out


def main():
    t, sortie = sys.argv[1], sys.argv[2]
    x0, y0 = (float(v) for v in t.split("_"))
    c = detecter(x0, y0, x0 + 50, y0 + 50)
    Path(sortie).write_text(json.dumps(c, indent=0), encoding="utf-8")
    print(len(c))


if __name__ == "__main__":
    main()
