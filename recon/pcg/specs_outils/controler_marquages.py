# -*- coding: utf-8 -*-
"""Contrôle des gabarits de marquages_geometrie.json : simplicité, orientation, trous, dimensions, cotes, cordes."""
import json
import math
import sys

import numpy as np

doc = json.load(open(sys.argv[1], encoding="utf-8"))
G = doc["gabarits"]
erreurs = []


def aire(P):
    P = np.asarray(P, float)
    return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


def seg_inter(p, q, r, s):
    """Intersection stricte ou contact de deux segments [p,q] et [r,s]."""
    def o(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)
    def sur(a, b, c):
        return min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12 and min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12
    o1, o2, o3, o4 = o(p, q, r), o(p, q, s), o(r, s, p), o(r, s, q)
    if o1 != o2 and o3 != o4:
        return True
    return (o1 == 0 and sur(p, q, r)) or (o2 == 0 and sur(p, q, s)) or (o3 == 0 and sur(r, s, p)) or (o4 == 0 and sur(r, s, q))


def simple(P):
    n = len(P)
    if len({(round(x, 6), round(y, 6)) for x, y in P}) != n:
        return False, "sommets dupliqués"
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or j == (i + 1) % n:
                continue
            c, d = P[j], P[(j + 1) % n]
            if seg_inter(a, b, c, d):
                return False, f"arêtes {i} et {j} se coupent"
    return True, "ok"


def anneaux_se_coupent(A, B):
    for i in range(len(A)):
        for j in range(len(B)):
            if seg_inter(A[i], A[(i + 1) % len(A)], B[j], B[(j + 1) % len(B)]):
                return True
    return False


def dedans(pt, P):
    x, y = pt
    c = False
    for i in range(len(P)):
        x1, y1 = P[i]
        x2, y2 = P[(i + 1) % len(P)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def ok(cond, msg):
    if not cond:
        erreurs.append(msg)
    return "ok " if cond else "ERR"


print(f"{'gabarit':26s} {'L (m)':>7s} {'W (m)':>7s} {'n':>4s} {'aire':>7s}  simple  sens  dims  trous")
for k, g in G.items():
    P = g["polygone"]
    s, why = simple(P)
    sens = aire(P) > 0
    xs = [p[0] for p in P]
    ys = [p[1] for p in P]
    if k == "VELO":
        Q = P + g["parties"]["roue_arriere"]["polygone"] + g["parties"]["roue_avant"]["polygone"]
        xs = [p[0] for p in Q]
        ys = [p[1] for p in Q]
        tol = 0.012
    else:
        tol = 0.0006
    Lm, Wm = max(ys) - min(ys), max(xs) - min(xs)
    dims = abs(Lm - g["longueur_m"]) <= tol and abs(Wm - g["largeur_m"]) <= tol
    tr = "—"
    if g.get("trous"):
        good = True
        for t in g["trous"]:
            st, _ = simple(t)
            good &= st and aire(t) < 0 and all(dedans(p, P) for p in t) and not anneaux_se_coupent(P, t)
        tr = ok(good, f"{k} : trou invalide")
    parts = ""
    if g.get("parties"):
        for pn in ("roue_arriere", "roue_avant"):
            R = g["parties"][pn]["polygone"]
            st, _ = simple(R)
            parts += " " + pn + ":" + ok(st and aire(R) > 0 and not anneaux_se_coupent(P, R), f"{k}.{pn} invalide").strip()
    m1, m2, m3 = f"{k} non simple : {why}", f"{k} pas CCW", f"{k} dimensions {Lm:.4f} x {Wm:.4f} != {g['longueur_m']} x {g['largeur_m']}"
    print(f"{k:26s} {Lm:7.3f} {Wm:7.3f} {g['n_sommets']:4d} {g['aire_m2']:7.4f}  {ok(s, m1)}     {ok(sens, m2)}  {ok(dims, m3)}   {tr}{parts}")

# cotes particulières
def pres(P, pt, tol=1e-6):
    return any(abs(p[0] - pt[0]) <= tol and abs(p[1] - pt[1]) <= tol for p in P)


C = []
td = G["TD"]["polygone"]
C.append(("TD tige 0,15 / tête 0,70 à y = 2,00 / pointe (0 ; 4,00)", pres(td, [0.075, 2.0]) and pres(td, [0.35, 2.0]) and pres(td, [-0.35, 2.0]) and pres(td, [0, 4.0])))
tad = G["TAD"]["polygone"]
C.append(("TAD dos de tête à 0,50 de la tige (x = 0,575), profondeur 0,35, pointe y = 3,00, tête 2,00", pres(tad, [0.575, 2.0]) and pres(tad, [0.575, 4.0]) and pres(tad, [0.925, 3.0])))
d1 = math.hypot(0.575 - 0.075, 2.75 - 2.25)
C.append(("TAD branche à 45° (bords parallèles, largeur perp. 0,354)", abs(math.degrees(math.atan2(0.5, 0.5)) - 45) < 1e-9 and abs(0.5 / math.sqrt(2) - 0.3536) < 1e-4 and abs(d1 - math.hypot(0.65, 0.65) + math.hypot(0.15, 0.15)) < 1e-9))
tt = G["TD_TAD"]["polygone"]
C.append(("TD_TAD pointe droite (0,925 ; 1,50), tête 0,50-2,50, branche 0,75-1,25", pres(tt, [0.925, 1.5]) and pres(tt, [0.575, 0.5]) and pres(tt, [0.575, 2.5]) and pres(tt, [0.075, 0.75]) and pres(tt, [0.075, 1.25])))
C.append(("TAG = miroir exact de TAD", sorted(map(tuple, G["TAG"]["polygone"])) == sorted((-x, y) for x, y in tad)))
rb = G["RAB_D"]["polygone"]
cons = G["RAB_D"]["construction"]
C.append(("RAB pied 0,25 (x -0,36 / -0,11 à y = 0)", pres(rb, [-0.36, 0]) and pres(rb, [-0.11, 0])))
# erreur de corde des arcs
def corde_max(points, xmin, R, yt):
    e = 0.0
    for a, b in zip(points[:-1], points[1:]):
        for t in np.linspace(0, 1, 21):
            y = a[1] + (b[1] - a[1]) * t
            x_seg = a[0] + (b[0] - a[0]) * t
            x_arc = xmin + R - math.sqrt(R * R - (y - yt) ** 2)
            e = max(e, abs(x_arc - x_seg))
    return e
bd = cons["bord_droit"]
pts_d = rb[1:1 + bd["segments"] + 1]
bg = cons["bord_gauche"]
pts_g = sorted(rb[-(bg["segments"] + 1):], key=lambda p: p[1])
ed = corde_max(pts_d, bd["x_tangente"], bd["rayon"], bd["tangente_verticale_y"])
eg = corde_max(pts_g, bg["x"], bg["rayon"], bg["vertical_jusqu_a_y"])
C.append((f"RAB arcs : erreur de corde max droite {ed * 1000:.2f} mm, gauche {eg * 1000:.2f} mm (≤ 1 mm, exigence ≤ 5 cm)", ed <= 0.00105 and eg <= 0.00105))
xd0 = bd["x_tangente"] + bd["rayon"] - math.sqrt(bd["rayon"] ** 2 - bd["tangente_verticale_y"] ** 2)
C.append((f"RAB bord droit passe par x = -0,11 au pied ({xd0:.4f})", abs(xd0 + 0.11) < 1e-4))
C.append(("RAB encoche sur l'arc R 21 et cassure sur l'arc R 18,38", pres(rb, cons["tete"]["encoche"], 1e-4) and pres(rb, cons["tete"]["cassure"], 1e-4)))
for nm, b, Lg, tr_ in [("CEDEZ_V60", 1.0, 2.0, 0.10), ("CEDEZ_V60P", 2.0, 6.0, 0.15)]:
    g = G[nm]
    P, T = g["polygone"], g["trous"][0]
    k = (b / 2) / Lg
    # distance perpendiculaire entre le côté droit extérieur et le côté droit du trou
    n = np.array([1, -k]) / math.hypot(1, k)
    dd = abs(np.dot(np.array(T[2]) - np.array([0, 0]), n))
    band = Lg - T[2][1]
    C.append((f"{nm} trait perpendiculaire {dd:.4f} (attendu {tr_}) et bandeau {band:.3f}", abs(dd - tr_) < 1e-3 and abs(band - (0.5 if b == 1 else 1.0)) < 1e-9))
v = G["VELO"]["parties"]
C.append(("VELO roues 0,30 x 0,55 à x ±0,25", all(abs(v[r]["ellipse"]["demi_axes"][0] - 0.15) < 1e-9 for r in ("roue_arriere", "roue_avant"))))
for txt, c in C:
    print(ok(c, txt), txt)
print()
print("RÉSULTAT :", "aucune erreur" if not erreurs else f"{len(erreurs)} erreur(s)")
for e in erreurs:
    print("  -", e)
sys.exit(1 if erreurs else 0)
