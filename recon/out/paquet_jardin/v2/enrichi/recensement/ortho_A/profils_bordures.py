#!/usr/bin/env python
"""Contrôle automatique de la position des bordures sur l'ortho PCRS 5 cm 2022 (agent VISION-ORTHO-A).

Pour chaque bordure (v2 en zone pilote, carte de cohérence ailleurs) qui traverse une dalle donnée :
profils de luminance perpendiculaires tous les 0,5 m (t de −1,2 à +1,2 m, t > 0 côté haut = gauche),
moyennés par fenêtres de 4 m ; on y cherche le saut le plus net (|dL/dt| maximal, lissé) et la
bande claire (tête de bordure). Sortie par fenêtre : t du saut, signe (chaussée sombre côté t < 0 ?),
contraste. Le saut d'une bordure béton sur enrobé tombe normalement à |t| ≤ 0,15 m de l'arête avant
levée. C'est un tri : les fenêtres hors tolérance sont revues à l'œil.

  python profils_bordures.py <sortie.json> [tuile ...]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlay as ov  # noqa: E402

T = np.arange(-1.2, 1.2001, 0.05)
PAS_S = 0.5
FEN = 4.0


def echant(img, xg, yh, x, y):
    c = (x - xg) / ov.PAS - 0.5
    r = (yh - y) / ov.PAS - 0.5
    H, W = img.shape
    c0 = np.clip(np.floor(c).astype(int), 0, W - 2)
    r0 = np.clip(np.floor(r).astype(int), 0, H - 2)
    fc, fr = np.clip(c - c0, 0, 1), np.clip(r - r0, 0, 1)
    return (img[r0, c0] * (1 - fc) * (1 - fr) + img[r0, c0 + 1] * fc * (1 - fr)
            + img[r0 + 1, c0] * (1 - fc) * fr + img[r0 + 1, c0 + 1] * fc * fr)


def analyser(co, boite):
    co = np.asarray([c[:2] for c in co], float)
    if len(co) < 2:
        return []
    seg = np.hypot(*np.diff(co, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    if L < 1.0:
        return []
    xs, ys = co[:, 0], co[:, 1]
    img, (xg, yh) = ov.mosaique(xs.min() - 2, ys.min() - 2, xs.max() + 2, ys.max() + 2)
    lum = img.astype(float).mean(axis=2)
    out = []
    ss = np.arange(PAS_S / 2, L, PAS_S)
    prof, pts = [], []
    for sv in ss:
        i = min(int(np.searchsorted(s, sv)) - 1, len(co) - 2)
        i = max(i, 0)
        d = co[i + 1] - co[i]
        n = np.hypot(*d) or 1
        u = d / n
        nrm = np.array([-u[1], u[0]])     # gauche = côté haut
        p = co[i] + u * (sv - s[i])
        X, Y = p[0] + nrm[0] * T, p[1] + nrm[1] * T
        prof.append(echant(lum, xg, yh, X, Y))
        pts.append(p)
    prof = np.array(prof)
    pts = np.array(pts)
    nf = max(1, int(round(FEN / PAS_S)))
    for k in range(0, len(ss), nf):
        P = prof[k:k + nf]
        if len(P) < 3:
            continue
        cx, cy = pts[k:k + nf].mean(axis=0)
        if not (boite[0] <= cx < boite[2] and boite[1] <= cy < boite[3]):
            continue
        m = np.median(P, axis=0)
        if m.max() == 0:
            continue
        g = np.gradient(np.convolve(m, np.ones(3) / 3, mode="same"))
        g[:2] = g[-2:] = 0
        j = int(np.argmax(np.abs(g)))
        bas = float(np.median(m[:10]))      # t de −1,2 à −0,75
        haut = float(np.median(m[-10:]))
        jj = int(np.argmax(m[12:37])) + 12  # bande claire entre −0,6 et +0,6
        out.append({"s0": round(float(ss[k] - PAS_S / 2), 1), "s1": round(float(ss[min(k + nf, len(ss)) - 1] + PAS_S / 2), 1),
                    "centre_l93": [round(float(cx), 2), round(float(cy), 2)],
                    "t_saut_m": round(float(T[j]), 2), "grad": round(float(g[j]), 1),
                    "t_clair_m": round(float(T[jj]), 2), "lum_clair": round(float(m[jj]), 0),
                    "lum_bas": round(bas, 0), "lum_haut": round(haut, 0)})
    return out


def main():
    sortie = sys.argv[1]
    tuiles = sys.argv[2:] or ov.TUILES_A
    C = ov.couches()
    res = []
    for t in tuiles:
        x0, y0 = (float(v) for v in t.split("_"))
        boite = (x0, y0, x0 + 50, y0 + 50)
        for fam, fs in (("v2", C["bordures"]), ("site", C["bordures_site"])):
            for f in fs:
                co = f["geometry"]["coordinates"]
                if not any(boite[0] - 1 <= c[0] < boite[2] + 1 and boite[1] - 1 <= c[1] < boite[3] + 1 for c in co):
                    continue
                w = analyser(co, boite)
                if w:
                    p = f["properties"]
                    res.append({"id": p["id"], "tuile": t, "famille": fam, "source": p.get("source", "v2"),
                                "modifiee_2025": p.get("modifiee_2025", p.get("zone_travaux_2025")), "fenetres": w})
    Path(sortie).write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(res), sum(len(r["fenetres"]) for r in res))


if __name__ == "__main__":
    main()
