"""Outils communs de la famille « marquages » (schéma description_scene_v2/0.2).

Lecture des marquages v1 (paquet, lecture seule), géométrie plane (rectangle orienté minimal,
Douglas-Peucker, détection des contours raster en escalier, lissage), gabarits IISR
(assets/specs/marquages_geometrie.json) posés par (origine, cap), IoU par rastérisation, poses
OpenDRIVE (s, t) et conventions de pose.

Conventions :
- repère local (commun.repere) pour tous les calculs, Lambert-93 dans les fichiers ;
- cap (`cap_deg`) : angle trigonométrique (depuis l'est, sens anti-horaire) de l'axe +y du gabarit,
  c'est-à-dire du sens de circulation / de lecture ; un point (x, y) du gabarit (x à droite) va en
  origine + x·(sin h, −cos h) + y·(cos h, sin h) ;
- abscisse σ d'une ligne : longueur curviligne le long de sa géométrie (axe), depuis son 1er sommet.
"""
import functools
import math

import numpy as np

from commun import (DONNEES, SPECS, VECTEURS, aire_signee, anneaux, dedoublonner_sommets, lire_geojson,
                    lire_json, repere)

V1 = DONNEES / "marquages/marquages_2026.geojson"
GAM_LIN = VECTEURS / "etat_2026/signalisation_horizontale_lin_L93.geojson"
GAM_PCT = VECTEURS / "etat_2026/signalisation_horizontale_pct_L93.geojson"
SPEC = SPECS / "marquages_geometrie.json"
PEINTURE = SPECS / "peinture.json"


# --------------------------------------------------------------------------- données
@functools.lru_cache(maxsize=None)
def spec():
    return lire_json(SPEC)


@functools.lru_cache(maxsize=None)
def v1():
    """Marquages v1 : liste triée par id de dict {id, p (propriétés), polys (anneaux locaux), r (anneau
    extérieur principal), obb, raster}."""
    out = []
    for f in lire_geojson(V1):
        p = f["properties"]
        polys = [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
        polys = [orienter_poly(pp) for pp in polys]
        r = max((pp[0] for pp in polys), key=lambda a: abs(aire_signee(a)))
        out.append({"id": p["id"], "p": p, "polys": polys, "r": r, "obb": rect_min(np.vstack([pp[0] for pp in polys])),
                    "raster": contour_raster(r), "aire": sum(abs(aire_signee(pp[0])) - sum(abs(aire_signee(t)) for t in pp[1:])
                                                             for pp in polys)})
    out.sort(key=lambda m: m["id"])
    return out


@functools.lru_cache(maxsize=None)
def gam_lin():
    """Lignes du levé GAM (SOL_SIGNALISATION_HORIZONTALE) en local, indexées comme gam_ref."""
    return [repere(np.asarray(f["geometry"]["coordinates"], dtype=float)[:, :2]) for f in lire_geojson(GAM_LIN)]


@functools.lru_cache(maxsize=None)
def gam_pct():
    out = []
    for i, f in enumerate(lire_geojson(GAM_PCT)):
        g = f["geometry"]
        c = g["coordinates"] if g["type"] == "Point" else g["coordinates"][0]
        out.append({"i": i, "xy": repere(np.asarray(c[:2], float)[None])[0], "bloc": f["properties"].get("bloc"),
                    "rotation": f["properties"].get("rotation"), "libelle": f["properties"].get("libelle")})
    return out


def gam_refs(p):
    g = p.get("gam_ref")
    return [int(x) for x in g.split(",")] if g else []


# --------------------------------------------------------------------------- géométrie plane
def orienter_poly(poly):
    out = []
    for k, r in enumerate(poly):
        a = aire_signee(r)
        out.append(r[::-1] if (k == 0 and a < 0) or (k > 0 and a > 0) else r)
    return out


def enveloppe_convexe(P):
    P = np.unique(np.round(np.asarray(P, float), 9), axis=0)
    if len(P) < 3:
        return P
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def croix(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    bas, haut = [], []
    for p in P:
        while len(bas) >= 2 and croix(bas[-2], bas[-1], p) <= 0:
            bas.pop()
        bas.append(p)
    for p in P[::-1]:
        while len(haut) >= 2 and croix(haut[-2], haut[-1], p) <= 0:
            haut.pop()
        haut.append(p)
    return np.array(bas[:-1] + haut[:-1])


def rect_min(P):
    """Rectangle d'aire minimale (pieds à pieds de l'enveloppe convexe) :
    {c, u (grand axe, x ≥ 0), v (gauche de u), L, W, coins (4, 2) anti-horaires}."""
    H = enveloppe_convexe(P)
    if len(H) < 3:
        c = np.asarray(P, float).mean(axis=0)
        return {"c": c, "u": np.array([1.0, 0.0]), "v": np.array([0.0, 1.0]), "L": 0.0, "W": 0.0,
                "coins": np.repeat(c[None], 4, axis=0)}
    best = None
    for i in range(len(H)):
        e = H[(i + 1) % len(H)] - H[i]
        n = np.hypot(*e)
        if n < 1e-9:
            continue
        u = e / n
        v = np.array([-u[1], u[0]])
        pu, pv = H @ u, H @ v
        a = (pu.max() - pu.min()) * (pv.max() - pv.min())
        if best is None or a < best[0] - 1e-12:
            best = (a, u, v, pu.min(), pu.max(), pv.min(), pv.max())
    _, u, v, u0, u1, v0, v1_ = best
    if u1 - u0 < v1_ - v0:
        u, v, u0, u1, v0, v1_ = v, -u, v0, v1_, -u1, -u0
    if u[0] < -1e-12 or (abs(u[0]) <= 1e-12 and u[1] < 0):
        u, v, u0, u1, v0, v1_ = -u, -v, -u1, -u0, -v1_, -v0
    c = u * (u0 + u1) / 2 + v * (v0 + v1_) / 2
    L, W = u1 - u0, v1_ - v0
    coins = np.array([c + u * a * L / 2 + v * b * W / 2 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    return {"c": c, "u": u, "v": v, "L": float(L), "W": float(W), "coins": coins}


def douglas_peucker(P, tol, ferme=False):
    """Douglas-Peucker (itératif) ; anneau fermé : coupé aux deux sommets les plus éloignés."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    if ferme:
        i0 = 0
        i1 = int(np.argmax(np.hypot(*(P - P[0]).T)))
        a = douglas_peucker(np.vstack([P[i0:i1 + 1]]), tol)
        b = douglas_peucker(np.vstack([P[i1:], P[:1]]), tol)
        return np.vstack([a[:-1], b[:-1]])
    garde = np.zeros(len(P), bool)
    garde[[0, -1]] = True
    pile = [(0, len(P) - 1)]
    while pile:
        i, j = pile.pop()
        if j <= i + 1:
            continue
        a, b = P[i], P[j]
        ab = b - a
        n = np.hypot(*ab)
        Q = P[i + 1:j]
        if n < 1e-12:
            d = np.hypot(*(Q - a).T)
        else:
            d = np.abs(ab[0] * (Q[:, 1] - a[1]) - ab[1] * (Q[:, 0] - a[0])) / n
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            garde[m] = True
            pile += [(i, m), (m, j)]
    return P[garde]


def contour_raster(r):
    """Contour vectorisé depuis un raster (marches d'escalier) : soit ≥ 8 sommets, arête médiane 2-15 cm et au
    moins la moitié des arêtes à 0° / 45° / 90° / 135° (± 3°) de la grille Lambert-93 ; soit une marche
    d'escalier (escalier)."""
    r = np.asarray(r, float)
    if len(r) < 8:
        return False
    e = np.diff(np.vstack([r, r[:1]]), axis=0)
    L = np.hypot(*e.T)
    a = np.degrees(np.arctan2(e[:, 1], e[:, 0])) % 45.0
    grille = (a < 3.0) | (a > 42.0)
    return bool(0.02 <= np.median(L) <= 0.15 and grille.mean() >= 0.5) or bool(escalier(r))


def _sans_alignes(r, tol_deg=3.0):
    """Anneau sans sommets alignés (déviation < tol_deg) ni arêtes nulles."""
    r = np.asarray(r, float)[:, :2]
    if len(r) > 1 and np.allclose(r[0], r[-1]):
        r = r[:-1]
    while len(r) > 3:
        a, c = np.roll(r, 1, 0), np.roll(r, -1, 0)
        u, v = r - a, c - r
        ang = np.degrees(np.arctan2(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0], (u * v).sum(1)))
        rm = np.where((np.abs(ang) < tol_deg) | (np.hypot(*u.T) < 1e-6))[0]
        if len(rm) == 0:
            break
        garde = np.ones(len(r), bool)
        dernier = -10
        for i in rm:
            if i - dernier > 1:
                garde[i] = False
                dernier = i
        r = r[garde]
    return r


def escalier(r, lmin=0.03, lmax=0.25, amin=25.0, amax=120.0, kmin=4):
    """Marche d'escalier (détecteur élargi de la revue, validé sur les 78 contours raster v1) : au moins kmin
    arêtes consécutives de lmin à lmax avec des virages alternés de amin à amax degrés. -> nombre de séries."""
    r = _sans_alignes(r)
    n = len(r)
    if n < 5:
        return 0
    e = np.roll(r, -1, 0) - r
    L = np.hypot(*e.T)
    e2 = np.roll(e, -1, 0)
    ang = np.degrees(np.arctan2(e[:, 0] * e2[:, 1] - e[:, 1] * e2[:, 0], (e * e2).sum(1)))
    ok = (L >= lmin) & (L <= lmax)
    series = 0
    for s0 in range(n):
        if not ok[s0]:
            continue
        k, j = 1, s0
        while k < n:
            a = ang[j % n]
            if not (amin <= abs(a) <= amax):
                break
            if k >= 2 and np.sign(a) == np.sign(ang[(j - 1) % n]):
                break
            if not ok[(j + 1) % n]:
                break
            k += 1
            j += 1
        if k >= kmin:
            series += 1
    return series


def lisser_anneau(r, sigma_m=0.06, pas=0.02):
    """Anneau rééchantillonné au pas `pas` puis lissé (gaussienne périodique σ) : supprime les marches
    d'un contour raster sans déplacer les bords droits de plus de quelques mm."""
    r = np.asarray(r, float)
    rr = np.vstack([r, r[:1]])
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(rr, axis=0).T))]
    n = max(8, int(round(s[-1] / pas)))
    g = np.linspace(0.0, s[-1], n, endpoint=False)
    Q = np.c_[np.interp(g, s, rr[:, 0]), np.interp(g, s, rr[:, 1])]
    k = sigma_m / (s[-1] / n)
    h = int(math.ceil(3 * k))
    w = np.exp(-0.5 * (np.arange(-h, h + 1) / max(k, 1e-6)) ** 2)
    w /= w.sum()
    idx = (np.arange(n)[:, None] + np.arange(-h, h + 1)[None]) % n
    return Q[idx].transpose(0, 2, 1) @ w


# --------------------------------------------------------------------------- gabarits et poses
def axes_cap(cap_deg):
    h = math.radians(cap_deg)
    return np.array([math.sin(h), -math.cos(h)]), np.array([math.cos(h), math.sin(h)])


def poser(P, origine, cap_deg, echelle=1.0):
    """Points (x, y) d'un gabarit -> repère local (origine, cap de l'axe +y)."""
    ex, ey = axes_cap(cap_deg)
    P = np.asarray(P, float) * echelle
    return np.asarray(origine, float)[None] + P[:, :1] * ex[None] + P[:, 1:2] * ey[None]


def dans_repere(Q, origine, cap_deg):
    """Inverse de poser : local -> (x, y) du gabarit."""
    ex, ey = axes_cap(cap_deg)
    d = np.asarray(Q, float) - np.asarray(origine, float)[None]
    return np.c_[d @ ex, d @ ey]


@functools.lru_cache(maxsize=None)
def _velo():
    import marquages_glyphes as GL
    return GL.velo_d1(spec()["gabarits"]["VELO"])


def gabarit(nom, echelle_x=1.0):
    """Polygones du gabarit [[anneau, trous...], ...] en coordonnées gabarit (roues de VELO comprises) ; x multiplié
    par echelle_x (homothétie latérale d'une flèche conservée plus étroite que l'IISR). VELO : figurine D1
    reconstruite par primitives (marquages_glyphes.velo_d1 : corps redressé, tête et roues en ellipses exactes)."""
    if echelle_x != 1.0:
        return [[np.c_[r[:, 0] * echelle_x, r[:, 1]] for r in poly] for poly in gabarit(nom)]
    if nom == "VELO":
        return [[r.copy() for r in poly] for poly in _velo()]
    g = spec()["gabarits"][nom]
    polys = [[np.asarray(g["polygone"], float)] + [np.asarray(t, float) for t in g.get("trous", [])]]
    for _, part in sorted(g.get("parties", {}).items()):
        if isinstance(part, dict) and "polygone" in part:
            polys.append([np.asarray(part["polygone"], float)])
    return polys


def cap_de(u):
    return math.degrees(math.atan2(u[1], u[0])) % 360.0


def ecart_cap(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


# --------------------------------------------------------------------------- IoU par rastérisation
def raster_masque(polys, x0, y0, nx, ny, res):
    from PIL import Image, ImageDraw
    im = Image.new("L", (nx, ny), 0)
    d = ImageDraw.Draw(im)
    for poly in polys:
        for k, r in enumerate(poly):
            pts = [((x - x0) / res, (y0 + ny * res - y) / res) for x, y in r]
            if len(pts) >= 3:
                d.polygon(pts, fill=255 if k == 0 else 0)
    return np.asarray(im) > 0


def iou(polys_a, polys_b, res=0.01, marge=0.05):
    P = np.vstack([r for poly in list(polys_a) + list(polys_b) for r in poly])
    x0, y0 = P.min(axis=0) - marge
    x1, y1 = P.max(axis=0) + marge
    nx, ny = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
    a = raster_masque(polys_a, x0, y0, nx, ny, res)
    b = raster_masque(polys_b, x0, y0, nx, ny, res)
    u = np.count_nonzero(a | b)
    return float(np.count_nonzero(a & b) / u) if u else 0.0


# --------------------------------------------------------------------------- divers
def mediane_ou(v, defaut=None):
    v = [x for x in v if x is not None]
    return float(np.median(v)) if v else defaut


def dedoublonner(P, tol=1e-4):
    return dedoublonner_sommets(np.asarray(P, float), tol)


def ident(prefixe, ids_v1, suffixe=""):
    """Identifiant stable : préfixe + numéro du plus petit MQ lié (ex. ML-0503) + suffixe."""
    n = min(int(i[2:]) for i in ids_v1)
    return f"{prefixe}-{n:04d}{suffixe}"
