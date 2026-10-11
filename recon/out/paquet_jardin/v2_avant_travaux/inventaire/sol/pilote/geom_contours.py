"""Géométrie raster -> vecteur sans scipy : composantes connexes, remplissage des trous, suivi de contour
(Moore), anneaux fermés rééchantillonnés, lissage circulaire, Douglas-Peucker, contrôles G1."""
from collections import deque

import numpy as np


def composantes(m):
    """Étiquettes 4-connexes d'un masque booléen -> (lab, n)."""
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    n = 0
    for r0, c0 in zip(*np.nonzero(m)):
        if lab[r0, c0]:
            continue
        n += 1
        lab[r0, c0] = n
        dq = deque([(r0, c0)])
        while dq:
            r, c = dq.popleft()
            for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= rr < H and 0 <= cc < W and m[rr, cc] and not lab[rr, cc]:
                    lab[rr, cc] = n
                    dq.append((rr, cc))
    return lab, n


def remplir(m):
    """Bouche les trous (complément non relié au bord)."""
    H, W = m.shape
    ext = np.zeros((H + 2, W + 2), bool)
    lib = np.ones((H + 2, W + 2), bool)
    lib[1:-1, 1:-1] = ~m
    dq = deque([(0, 0)])
    ext[0, 0] = True
    while dq:
        r, c = dq.popleft()
        for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= rr < H + 2 and 0 <= cc < W + 2 and lib[rr, cc] and not ext[rr, cc]:
                ext[rr, cc] = True
                dq.append((rr, cc))
    return ~ext[1:-1, 1:-1]


def eroder(m, k=1):
    out = m.copy()
    for _ in range(k):
        out = out & np.roll(out, 1, 0) & np.roll(out, -1, 0) & np.roll(out, 1, 1) & np.roll(out, -1, 1)
    return out


def dilater(m, k=1):
    out = m.copy()
    for _ in range(k):
        out = out | np.roll(out, 1, 0) | np.roll(out, -1, 0) | np.roll(out, 1, 1) | np.roll(out, -1, 1)
    return out


def contour_moore(m):
    """Contour extérieur (centres de pixels) de la plus grande composante supposée unique, sens horaire image."""
    H, W = m.shape
    p = np.pad(m, 1)
    rs, cs = np.nonzero(p)
    i = np.lexsort((cs, rs))[0]
    start = (rs[i], cs[i])
    voisins = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    cont = [start]
    cur, back = start, 6          # on arrive par l'ouest
    for _ in range(4 * H * W):
        trouve = False
        for k in range(8):
            d = (back + 1 + k) % 8
            rr, cc = cur[0] + voisins[d][0], cur[1] + voisins[d][1]
            if p[rr, cc]:
                back = (d + 4) % 8
                cur = (rr, cc)
                trouve = True
                break
        if not trouve:
            break
        if cur == start:
            break
        cont.append(cur)
    a = np.asarray(cont, float) - 1.0
    return a                       # (r, c)


def aire(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def reechantillonner_ferme(P, pas):
    Q = np.r_[P, P[:1]]
    S = np.r_[0.0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
    n = max(8, int(round(S[-1] / pas)))
    s = np.linspace(0, S[-1], n, endpoint=False)
    x = np.interp(s, S, Q[:, 0])
    y = np.interp(s, S, Q[:, 1])
    return np.c_[x, y], S[-1]


def lisser_ferme(v, sigma_pts):
    if sigma_pts <= 0:
        return v
    k = int(np.ceil(3 * sigma_pts))
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma_pts) ** 2)
    w /= w.sum()
    out = np.zeros_like(v, dtype=float)
    for j, wj in zip(range(-k, k + 1), w):
        out += wj * np.roll(v, -j, axis=0)
    return out


def mediane_glissante_fermee(v, demi):
    n = len(v)
    idx = (np.arange(n)[:, None] + np.arange(-demi, demi + 1)[None]) % n
    return np.median(v[idx], 1)


def douglas_peucker(P, tol):
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    L = np.hypot(*ab)
    if L < 1e-12:
        d = np.hypot(*(P - a).T)
    else:
        d = np.abs(ab[0] * (P[:, 1] - a[1]) - ab[1] * (P[:, 0] - a[0])) / L
    i = int(np.argmax(d))
    if d[i] > tol:
        return np.r_[douglas_peucker(P[:i + 1], tol)[:-1], douglas_peucker(P[i:], tol)]
    return np.r_[[a], [b]]


def controles_g1(P, pas):
    """Anneau fermé rééchantillonné au pas `pas` : virage par sommet, rayon local, auto-intersections."""
    T = np.roll(P, -1, 0) - P
    ang = np.arctan2(T[:, 1], T[:, 0])
    dang = (np.diff(np.r_[ang, ang[:1]]) + np.pi) % (2 * np.pi) - np.pi
    deg = np.degrees(np.abs(dang))
    rayon = pas / np.maximum(np.abs(dang), 1e-9)
    # auto-intersections (segments non adjacents)
    A, B = P, np.roll(P, -1, 0)
    n = len(P)
    inter = 0
    for i in range(n):
        j = np.arange(i + 2, n if i > 0 else n - 1)
        if not len(j):
            continue
        p, r = A[i], B[i] - A[i]
        q, s = A[j], B[j] - A[j]
        den = r[0] * s[:, 1] - r[1] * s[:, 0]
        ok = np.abs(den) > 1e-12
        qp = q - p
        t = np.where(ok, (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / np.where(ok, den, 1), -1)
        u = np.where(ok, (qp[:, 0] * r[1] - qp[:, 1] * r[0]) / np.where(ok, den, 1), -1)
        inter += int(((t > 0) & (t < 1) & (u > 0) & (u < 1)).sum())
    return {"ferme": True, "n_sommets_pas": int(n), "virage_max_deg_par_pas": round(float(deg.max()), 1),
            "virages_sup_30deg": int((deg > 30).sum()), "rayon_min_m": round(float(rayon.min()), 3),
            "auto_intersections": inter, "somme_virages_deg": round(float(np.degrees(dang.sum())), 1)}


def remplir_scanline(anneaux, x0, y1, res, W, H):
    """Masque exact (règle pair-impair aux CENTRES de pixels) d'un polygone à trous, sur sa boîte englobante.
    Renvoie (r0, c0, masque) ; deux polygones qui partagent une arête ne partagent aucun pixel."""
    E = []
    for r in anneaux:
        r = np.asarray(r, float)
        if len(r) and np.hypot(*(r[0] - r[-1])) > 1e-9:
            r = np.r_[r, r[:1]]
        E.append(np.c_[r[:-1], r[1:]])
    E = np.vstack(E)
    ymin, ymax = E[:, [1, 3]].min(), E[:, [1, 3]].max()
    xmin, xmax = E[:, [0, 2]].min(), E[:, [0, 2]].max()
    r0 = max(0, int(np.floor((y1 - ymax) / res - 0.5)))
    r1 = min(H, int(np.ceil((y1 - ymin) / res + 0.5)))
    c0 = max(0, int(np.floor((xmin - x0) / res - 0.5)))
    c1 = min(W, int(np.ceil((xmax - x0) / res + 0.5)))
    if r1 <= r0 or c1 <= c0:
        return 0, 0, np.zeros((0, 0), bool)
    yc = y1 - (np.arange(r0, r1) + 0.5) * res
    xa, ya, xb, yb = E.T
    lo, hi = np.minimum(ya, yb), np.maximum(ya, yb)
    act = (yc[:, None] >= lo[None]) & (yc[:, None] < hi[None])
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = xa[None] + (yc[:, None] - ya[None]) * (xb - xa)[None] / (yb - ya)[None]
    xi = np.where(act, xi, np.inf)
    xi.sort(1)
    n = act.sum(1)
    xc = x0 + (np.arange(c0, c1) + 0.5) * res
    m = np.zeros((r1 - r0, c1 - c0), bool)
    for i in np.flatnonzero(n >= 2):
        xs = xi[i, :n[i] - (n[i] % 2)]
        a, b = xs[0::2], xs[1::2]
        ia = np.searchsorted(xc, a, side="left")
        ib = np.searchsorted(xc, b, side="left")
        for u, v in zip(ia, ib):
            m[i, u:v] = True
    return r0, c0, m
