"""Rasters, filtres et géométrie communs du paquet marquages_ortho_gabarits (promu de
v2_avant_travaux/inventaire/marquages/pilote/commun_pilote.py).

Repères : L93 (EPSG:2154) ; local = L93 - O, O = (917279.43, 6460289.98).
Ortho PCRS 5 cm 2022 : dalles 50 m (data/sites/paquet_jardin/ortho5cm_2022), nom = coin bas-gauche, le .jgw donne le
centre du pixel haut-gauche. Le pixel (r, c) d'une mosaïque couvre x in [X0 + c*0,05 ; X0 + (c+1)*0,05[,
y in ]Y1 - (r+1)*0,05 ; Y1 - r*0,05].
BD ORTHO IGN 2024 (20 cm) : recalée sur le PCRS par le décalage de
recon/out/paquet_jardin/v2/enrichi/recensement/ortho_recentes/recalage.json (lecture seule ;
convention : position cadre PCRS 2022 = position lue sur la couche - (dx, dy)).
Aucune écriture : les sorties sont gérées par l'appelant. numpy + Pillow seulement.
"""
from __future__ import annotations

import functools
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RACINE = Path(__file__).resolve().parents[4]
SITE = RACINE / "data/sites/paquet_jardin"
PCRS = SITE / "ortho5cm_2022"
BDO24 = RACINE / "data/raw/ortho_recentes/ign_bdortho_2024_rvb_20cm"
RECALAGE = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/ortho_recentes/recalage.json"
SPEC = RACINE / "assets/specs/marquages_geometrie.json"
O = (917279.43, 6460289.98)
PX = 0.05
EMPRISE_SITE = (917129.0, 6460140.0, 917429.0, 6460440.0)


def lire_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def conv_json(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return o.as_posix()
    raise TypeError(type(o))


@functools.lru_cache(maxsize=None)
def spec():
    """Gabarits IISR (assets/specs/marquages_geometrie.json), en lecture seule."""
    return lire_json(SPEC)


def local(x, y):
    return x - O[0], y - O[1]


# --------------------------------------------------------------------------- rasters
@functools.lru_cache(maxsize=64)
def _dalle_pcrs(x0, y0):
    p = PCRS / f"pcrs5cm_{x0}_{y0}.jpg"
    if not p.exists():
        return None
    return np.asarray(Image.open(p).convert("RGB"))


def dalles_pcrs_utilisees(X0, Y0, X1, Y1):
    out = []
    for tx in range(int(math.floor(X0 / 50) * 50), int(math.ceil(X1 / 50) * 50), 50):
        for ty in range(int(math.floor(Y0 / 50) * 50), int(math.ceil(Y1 / 50) * 50), 50):
            p = PCRS / f"pcrs5cm_{tx}_{ty}.jpg"
            if p.exists():
                out.append(p)
    return out


def mosaique_2022(X0, Y0, X1, Y1):
    """RGB uint8 (H, W, 3) de l'ortho PCRS 2022 sur [X0, X1] x [Y0, Y1] (L93, bornes arrondies aux 5 cm).
    Retourne (img, (Xg, Yh)) avec Xg = bord gauche, Yh = bord haut."""
    X0 = math.floor(round(X0 / PX, 6)) * PX
    Y1 = math.ceil(round(Y1 / PX, 6)) * PX
    W = int(round((X1 - X0) / PX))
    H = int(round((Y1 - Y0) / PX))
    out = np.zeros((H, W, 3), np.uint8)
    for tx in range(int(math.floor(X0 / 50) * 50), int(math.ceil(X1 / 50) * 50), 50):
        for ty in range(int(math.floor(Y0 / 50) * 50), int(math.ceil(Y1 / 50) * 50), 50):
            im = _dalle_pcrs(tx, ty)
            if im is None:
                continue
            c0 = int(round((tx - X0) / PX))
            r0 = int(round((Y1 - (ty + 50)) / PX))
            a0, b0 = max(0, -r0), max(0, -c0)
            a1, b1 = min(1000, H - r0), min(1000, W - c0)
            if a1 <= a0 or b1 <= b0:
                continue
            out[r0 + a0:r0 + a1, c0 + b0:c0 + b1] = im[a0:a1, b0:b1]
    return out, (X0, Y1)


@functools.lru_cache(maxsize=None)
def decalage_2024():
    """(dx, dy) du recalage BD ORTHO 2024 -> PCRS 2022 et MAD (m)."""
    try:
        d = lire_json(RECALAGE)["couches"]["ign_bdortho_2024_rvb_20cm"]
        return float(d["dx_m"]), float(d["dy_m"]), [float(v) for v in d.get("mad_m", [None, None])]
    except (OSError, KeyError, ValueError):
        return 0.0, 0.0, [None, None]


@functools.lru_cache(maxsize=16)
def _dalle_2024(x0, y0):
    p = BDO24 / f"ign_bdortho_2024_rvb_20cm_{x0}_{y0}.jpg"
    if not p.exists():
        return None
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32)


def dalles_2024_utilisees(X0, Y0, X1, Y1):
    out = []
    for tx in range(int(math.floor(X0 / 200) * 200), int(math.ceil(X1 / 200) * 200), 200):
        for ty in range(int(math.floor(Y0 / 200) * 200), int(math.ceil(Y1 / 200) * 200), 200):
            p = BDO24 / f"ign_bdortho_2024_rvb_20cm_{tx}_{ty}.jpg"
            if p.exists():
                out.append(p)
    return out


def echantillonner_2024(X, Y):
    """RGB bilinéaire de la BD ORTHO 2024 (20 cm) aux points L93 exprimés dans le cadre PCRS 2022."""
    dx, dy, _ = decalage_2024()
    X = np.asarray(X, float) + dx
    Y = np.asarray(Y, float) + dy
    out = np.full(X.shape + (3,), np.nan, np.float32)
    tx = (np.floor(X / 200) * 200).astype(int)
    ty = (np.floor(Y / 200) * 200).astype(int)
    for k in sorted(set(zip(tx.ravel().tolist(), ty.ravel().tolist()))):
        im = _dalle_2024(*k)
        if im is None:
            continue
        m = (tx == k[0]) & (ty == k[1])
        c = (X[m] - k[0]) / 0.2 - 0.5
        r = (k[1] + 200 - Y[m]) / 0.2 - 0.5
        n = im.shape[0] - 2
        c0 = np.clip(np.floor(c).astype(int), 0, n)
        r0 = np.clip(np.floor(r).astype(int), 0, n)
        a = np.clip(c - c0, 0, 1)[:, None]
        b = np.clip(r - r0, 0, 1)[:, None]
        out[m] = (im[r0, c0] * (1 - a) + im[r0, c0 + 1] * a) * (1 - b) + (im[r0 + 1, c0] * (1 - a) + im[r0 + 1, c0 + 1] * a) * b
    return out


def mosaique_2024(X0, Y0, X1, Y1, res=PX):
    """BD ORTHO 2024 recalée, rééchantillonnée (bilinéaire) sur la grille de la mosaïque 2022."""
    X0 = math.floor(round(X0 / PX, 6)) * PX
    Y1 = math.ceil(round(Y1 / PX, 6)) * PX
    W = int(round((X1 - X0) / res))
    H = int(round((Y1 - Y0) / res))
    xs = X0 + (np.arange(W) + 0.5) * res
    ys = Y1 - (np.arange(H) + 0.5) * res
    XX, YY = np.meshgrid(xs, ys)
    v = echantillonner_2024(XX, YY)
    return np.nan_to_num(v, nan=0).clip(0, 255).astype(np.uint8), (X0, Y1)


def px_vers_l93(r, c, geo, res=PX):
    """Centre du pixel (r, c) (fractionnaire accepté) -> L93."""
    return geo[0] + (np.asarray(c) + 0.5) * res, geo[1] - (np.asarray(r) + 0.5) * res


def l93_vers_px(x, y, geo, res=PX):
    return (geo[1] - np.asarray(y)) / res - 0.5, (np.asarray(x) - geo[0]) / res - 0.5


# --------------------------------------------------------------------------- filtres (sans scipy)
def flou_boite(a, k):
    """Moyenne glissante k x k (k impair) par images intégrales, bords répliqués."""
    a = np.asarray(a, np.float64)
    p = k // 2
    b = np.pad(a, p, mode="edge")
    ii = np.pad(b, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    H, W = a.shape
    return (ii[k:k + H, k:k + W] - ii[:H, k:k + W] - ii[k:k + H, :W] + ii[:H, :W]) / (k * k)


def noyau_gauss(sigma, ordre=0):
    """Noyau gaussien 1D (ou dérivée d'ordre 1 / 2) échantillonné, rayon 3,5 sigma."""
    r = int(math.ceil(3.5 * sigma))
    x = np.arange(-r, r + 1, dtype=np.float64)
    g = np.exp(-0.5 * (x / sigma) ** 2)
    g /= g.sum()
    if ordre == 0:
        return g
    if ordre == 1:
        return -x / sigma ** 2 * g
    return (x ** 2 / sigma ** 4 - 1 / sigma ** 2) * g


def convoluer_sep(a, kr, kc):
    """Convolution séparable (lignes puis colonnes), bords répliqués."""
    a = np.asarray(a, np.float64)
    pr, pc = len(kr) // 2, len(kc) // 2
    b = np.pad(a, ((pr, pr), (0, 0)), mode="edge")
    out = np.zeros_like(a)
    for i, w in enumerate(kr):
        out += w * b[i:i + a.shape[0]]
    b = np.pad(out, ((0, 0), (pc, pc)), mode="edge")
    out2 = np.zeros_like(a)
    for j, w in enumerate(kc):
        out2 += w * b[:, j:j + a.shape[1]]
    return out2


def _filtre_rang(a, k, filtre):
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    steps, rem = divmod(k - 1, 8)
    for _ in range(steps):
        im = im.filter(filtre(9))
    if rem:
        im = im.filter(filtre(rem + 1 if (rem + 1) % 2 else rem + 2))
    return np.asarray(im, np.float32)


def min_filtre(a, k):
    return _filtre_rang(a, k, ImageFilter.MinFilter)


def max_filtre(a, k):
    return _filtre_rang(a, k, ImageFilter.MaxFilter)


def etiqueter(m):
    """Composantes 8-connexes d'un masque booléen (étiquetage par plages + union-find). -> (labels int32, n)."""
    H, W = m.shape
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    lab = np.zeros((H, W), np.int32)
    prev = []
    for r in range(H):
        row = m[r]
        if not row.any():
            prev = []
            continue
        d = np.diff(np.r_[0, row.view(np.int8), 0])
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1)
        cur = []
        j = 0
        for s, e in zip(starts.tolist(), ends.tolist()):
            lb = 0
            while j < len(prev) and prev[j][1] < s:
                j += 1
            k = j
            while k < len(prev) and prev[k][0] <= e:
                if prev[k][1] >= s:
                    a = find(prev[k][2])
                    if lb == 0:
                        lb = a
                    elif a != lb:
                        parent[max(a, lb)] = min(a, lb)
                        lb = min(a, lb)
                k += 1
            if lb == 0:
                lb = len(parent)
                parent.append(lb)
            lab[r, s:e] = lb
            cur.append((s, e, lb))
        prev = cur
    par = np.array([find(i) for i in range(len(parent))], np.int32)
    _, inv = np.unique(par, return_inverse=True)
    lab = inv.astype(np.int32)[lab]
    return lab, int(lab.max())


def composantes(lab, n):
    """Indices de pixels par composante : liste de (rows, cols)."""
    flat = lab.ravel()
    order = np.argsort(flat, kind="stable")
    counts = np.bincount(flat, minlength=n + 1)
    bounds = np.r_[0, np.cumsum(counts)]
    W = lab.shape[1]
    out = []
    for i in range(1, n + 1):
        idx = order[bounds[i]:bounds[i + 1]]
        out.append((idx // W, idx % W))
    return out


# --------------------------------------------------------------------------- géométrie
def poser(poly, x, y, cap_rad, sx=1.0, sy=1.0):
    """Gabarit (x latéral à droite, y longitudinal) -> L93 ; cap = azimut trigonométrique du sens y (rad)."""
    P = np.asarray(poly, float) * [sx, sy]
    d = np.array([math.cos(cap_rad), math.sin(cap_rad)])
    rgt = np.array([math.sin(cap_rad), -math.cos(cap_rad)])
    return np.c_[x + P[:, 0] * rgt[0] + P[:, 1] * d[0], y + P[:, 0] * rgt[1] + P[:, 1] * d[1]]


def rasteriser(polys, geo, shape, res=PX, ss=4):
    """Couverture 0-1 (H, W) de polygones L93 (liste d'anneaux [ext, trous...]) sur la grille geo."""
    H, W = shape
    cv = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(cv)
    for poly in polys:
        for k, ring in enumerate(poly):
            R = np.asarray(ring, float)
            cc = (R[:, 0] - geo[0]) / res * ss
            rr = (geo[1] - R[:, 1]) / res * ss
            d.polygon(list(zip(cc.tolist(), rr.tolist())), fill=255 if k == 0 else 0)
    return np.asarray(cv.resize((W, H), Image.BOX), np.float32) / 255.0


def rasteriser_tampon(polys, geo, shape, tampon_m, res=PX, ss=2):
    """Masque booléen (H, W) des polygones dilatés de `tampon_m` (contour tracé en trait épais)."""
    H, W = shape
    cv = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(cv)
    lw = max(1, int(round(2 * tampon_m / res * ss)))
    for poly in polys:
        R = np.asarray(poly[0], float)
        cc = (R[:, 0] - geo[0]) / res * ss
        rr = (geo[1] - R[:, 1]) / res * ss
        pts = list(zip(cc.tolist(), rr.tolist()))
        d.polygon(pts, fill=255)
        d.line(pts + [pts[0]], fill=255, width=lw, joint="curve")
        for q in pts:
            d.ellipse([q[0] - lw / 2, q[1] - lw / 2, q[0] + lw / 2, q[1] + lw / 2], fill=255)
    return np.asarray(cv.resize((W, H), Image.BOX)) > 0


def rasteriser_lignes(lignes, geo, shape, largeur_m, res=PX):
    """Masque booléen des polylignes L93 épaissies à `largeur_m`."""
    H, W = shape
    cv = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(cv)
    lw = max(1, int(round(largeur_m / res)))
    for P in lignes:
        P = np.asarray(P, float)
        pts = list(zip(((P[:, 0] - geo[0]) / res).tolist(), ((geo[1] - P[:, 1]) / res).tolist()))
        if len(pts) >= 2:
            d.line(pts, fill=255, width=lw, joint="curve")
    return np.asarray(cv) > 0


def dist_point_polyligne(Q, P):
    """Distance de points Q (N, 2) à une polyligne P (M, 2) ; renvoie aussi l'abscisse curviligne du projeté."""
    Q = np.atleast_2d(np.asarray(Q, float))
    P = np.asarray(P, float)
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    t = np.clip(((Q[:, None, :] - A[None]) * AB[None]).sum(-1) / L2[None], 0, 1)
    proj = A[None] + t[..., None] * AB[None]
    d2 = ((Q[:, None, :] - proj) ** 2).sum(-1)
    i = d2.argmin(1)
    s0 = np.r_[0, np.cumsum(np.sqrt(L2))]
    s = s0[i] + t[np.arange(len(Q)), i] * np.sqrt(L2[i])
    return np.sqrt(d2[np.arange(len(Q)), i]), s


def echantillonner(A, geo, X, Y, res=PX, defaut=np.nan):
    """Valeur bilinéaire d'un raster (H, W) de la grille geo aux points L93 (X, Y) (mêmes formes)."""
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    r, c = l93_vers_px(X, Y, geo, res)
    H, W = A.shape[:2]
    ok = (r >= 0) & (c >= 0) & (r <= H - 1) & (c <= W - 1)
    r0 = np.clip(np.floor(r).astype(int), 0, H - 2)
    c0 = np.clip(np.floor(c).astype(int), 0, W - 2)
    a = np.clip(c - c0, 0, 1)
    b = np.clip(r - r0, 0, 1)
    v = (A[r0, c0] * (1 - a) + A[r0, c0 + 1] * a) * (1 - b) + (A[r0 + 1, c0] * (1 - a) + A[r0 + 1, c0 + 1] * a) * b
    return np.where(ok, v, defaut)


def angle_moyen_axial(angles, poids=None):
    """Moyenne d'orientations définies modulo pi (moyenne circulaire de 2 theta)."""
    a = np.asarray(angles, float)
    w = np.ones_like(a) if poids is None else np.asarray(poids, float)
    s, c = (w * np.sin(2 * a)).sum(), (w * np.cos(2 * a)).sum()
    return 0.5 * math.atan2(s, c)


def ecart_axial(a, b):
    """Écart d'orientations modulo pi, dans [-pi/2, pi/2[."""
    return (a - b + math.pi / 2) % math.pi - math.pi / 2


def ferme(P, tol=1e-3):
    """Polyligne fermée (premier sommet = dernier à tol près). np.allclose a une tolérance RELATIVE (65 m en L93) :
    ne pas l'utiliser sur des coordonnées Lambert-93."""
    P = np.asarray(P)
    return len(P) >= 3 and float(np.hypot(*(P[0][:2] - P[-1][:2]))) < tol


def point_dans_polygone(x, y, R):
    """Test pair-impair d'un point dans un anneau (N, 2)."""
    R = np.asarray(R, float)
    inside = False
    j = len(R) - 1
    for i in range(len(R)):
        if ((R[i, 1] > y) != (R[j, 1] > y)) and (x < (R[j, 0] - R[i, 0]) * (y - R[i, 1]) / (R[j, 1] - R[i, 1] + 1e-12) + R[i, 0]):
            inside = not inside
        j = i
    return inside


def points_dans_polygone(X, Y, R):
    """Version vectorisée (tableaux de points) du test pair-impair."""
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    R = np.asarray(R, float)
    inside = np.zeros(X.shape, bool)
    j = len(R) - 1
    for i in range(len(R)):
        yi, yj, xi, xj = R[i, 1], R[j, 1], R[i, 0], R[j, 0]
        cond = ((yi > Y) != (yj > Y)) & (X < (xj - xi) * (Y - yi) / (yj - yi + 1e-12) + xi)
        inside ^= cond
        j = i
    return inside


def longueur(P):
    P = np.asarray(P, float)
    return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum()) if len(P) > 1 else 0.0


def reechantillonner(P, pas):
    """Polyligne rééchantillonnée à pas constant (extrémités conservées)."""
    P = np.asarray(P, float)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if s[-1] <= 0:
        return P[:1].copy(), np.zeros(1)
    n = max(2, int(math.ceil(s[-1] / pas)) + 1)
    t = np.linspace(0, s[-1], n)
    return np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], t


def douglas_peucker(P, tol):
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    garde = np.zeros(len(P), bool)
    garde[0] = garde[-1] = True
    pile = [(0, len(P) - 1)]
    while pile:
        a, b = pile.pop()
        if b <= a + 1:
            continue
        A, B = P[a], P[b]
        AB = B - A
        n = np.hypot(*AB)
        Q = P[a + 1:b]
        if n < 1e-12:
            d = np.hypot(*(Q - A).T)
        else:
            d = np.abs(AB[0] * (Q[:, 1] - A[1]) - AB[1] * (Q[:, 0] - A[0])) / n
        i = int(np.argmax(d))
        if d[i] > tol:
            garde[a + 1 + i] = True
            pile += [(a, a + 1 + i), (a + 1 + i, b)]
    return P[garde]
