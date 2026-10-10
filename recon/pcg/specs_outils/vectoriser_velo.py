# -*- coding: utf-8 -*-
"""Vectorisation unique de la figurine velo IISR (annexe D1, image native 0,80 x 1,28 m, grille 0,10 m).
Marching squares (numpy) sur l'image dont les lignes de grille sont effacees, puis Douglas-Peucker.
Sortie : velo_vecteur.json (anneaux en metres, origine coin bas gauche de la boite, x vers la droite, y vers le haut de la figure)."""
import json, math, sys
import numpy as np
from PIL import Image

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'velo_vecteur.json'
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 0.004   # m, Douglas-Peucker

im = np.asarray(Image.open(SRC).convert('L')).astype(float)
im = im[:720].copy()                         # sans la legende
GX = [60, 112, 164, 216, 268, 320, 372, 424, 476]          # lignes de grille verticales (px)
GY = [46 + 49.154 * k for k in range(14)]                   # 13 cases de 0,10 m
# effacement des lignes de grille : max des voisins a +-3 px
for gx in GX:
    for x in range(gx - 1, gx + 2):
        im[:, x] = np.maximum(im[:, gx - 3], im[:, gx + 3])
for gy in GY:
    g = int(round(gy))
    for y in range(g - 1, g + 2):
        im[y, :] = np.maximum(im[g - 3, :], im[g + 3, :])
im[:, :GX[0] - 4] = 192; im[:, GX[-1] + 5:] = 192          # hors boite
# lissage leger 3x3 pour stabiliser l'isovaleur
k = np.ones((3, 3)) / 9.0
p = np.pad(im, 1, mode='edge')
im = sum(p[i:i + im.shape[0], j:j + im.shape[1]] * k[i, j] for i in range(3) for j in range(3))
T = (192 + 255) / 2.0

# marching squares : segments entre points de passage identifies par arete
H, W = im.shape
b = im > T
def pt(e):
    kind, i, j = e
    if kind == 'h':   # entre (i,j) et (i,j+1)
        a, c = im[i, j], im[i, j + 1]; t = (T - a) / (c - a); return (j + t, i)
    a, c = im[i, j], im[i + 1, j]; t = (T - a) / (c - a); return (j, i + t)
nxt = {}
for i in range(H - 1):
    for j in range(W - 1):
        c = (b[i, j] << 3) | (b[i, j + 1] << 2) | (b[i + 1, j + 1] << 1) | b[i + 1, j]
        if c in (0, 15): continue
        top, right, bot, left = ('h', i, j), ('v', i, j + 1), ('h', i + 1, j), ('v', i, j)
        # orientation : blanc a gauche du segment (contour exterieur CCW une fois y retourne)
        table = {1: [(left, bot)], 2: [(bot, right)], 3: [(left, right)], 4: [(right, top)],
                 5: [(left, top), (right, bot)], 6: [(bot, top)], 7: [(left, top)], 8: [(top, left)],
                 9: [(top, bot)], 10: [(top, right), (bot, left)], 11: [(top, right)], 12: [(right, left)],
                 13: [(right, bot)], 14: [(bot, left)]}
        for a, z in table[c]:
            nxt[a] = z
loops = []
seen = set()
for s0 in list(nxt):
    if s0 in seen: continue
    L = []; e = s0
    while e not in seen and e in nxt:
        seen.add(e); L.append(pt(e)); e = nxt[e]
    if len(L) > 20: loops.append(np.array(L))
# pixels -> metres (x : 52 px / 0,10 m depuis x=60 ; y : 49,154 px / 0,10 m depuis y=685,0)
def to_m(P): return np.c_[(P[:, 0] - 60.0) / 520.0, (GY[-1] - P[:, 1]) / 491.54]
def area(P): return 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
def dp(P, tol):
    if len(P) < 3: return P
    a, z = P[0], P[-1]; d = z - a; n = np.hypot(*d)
    dist = np.abs(np.cross(d, P - a)) / n if n > 0 else np.hypot(*(P - a).T)
    i = int(np.argmax(dist))
    if dist[i] > tol: return np.vstack([dp(P[:i + 1], tol)[:-1], dp(P[i:], tol)])
    return np.vstack([a, z])
def dp_ferme(P, tol):
    # coupe l'anneau aux deux points les plus eloignes
    i = 0; j = int(np.argmax(np.hypot(*(P - P[0]).T)))
    A = dp(np.vstack([P[i:j + 1]]), tol); B = dp(np.vstack([P[j:], P[:1]]), tol)
    return np.vstack([A[:-1], B[:-1]])
res = []
for P in loops:
    M = to_m(P)
    ar = area(M)
    if abs(ar) < 1e-4: continue
    S = dp_ferme(M, TOL)
    if area(S) < 0: S = S[::-1]  # CCW (exterieurs)
    res.append(dict(aire_m2=round(abs(ar), 4), n_brut=len(M), n=len(S),
                    bbox=[round(float(v), 3) for v in (S[:, 0].min(), S[:, 1].min(), S[:, 0].max(), S[:, 1].max())],
                    signe_brut=1 if ar > 0 else -1, anneau=[[round(float(x), 4), round(float(y), 4)] for x, y in S]))
res.sort(key=lambda r: -r['aire_m2'])
for r in res: print(r['aire_m2'], r['n_brut'], '->', r['n'], r['bbox'], 'signe', r['signe_brut'])
json.dump(res, open(OUT, 'w'), indent=0)
