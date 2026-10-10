"""Primitives géométriques des marques non couvertes par un polygone IISR exact : traits (rubans de largeur
constante, bouts plats ou ronds), arcs, ellipses, pictogramme PMR (ISO 7001 stylisé), chiffres « 30 » /
« 50 » dans une ellipse, T de stationnement, figurine vélo D1 reconstruite par primitives, redressement des
contours d'origine raster (droites ajustées) et raccord des axes anguleux (congés).

Repère des gabarits (comme marquages_commun) : x à droite, y dans le sens de circulation / de lecture ;
polygones [[anneau, ...], ...] sans trou (les anneaux se recouvrent : la fabrication en fait la réunion).
Discrétisation des arcs : corde ≤ 1 mm. Toutes les fonctions sont déterministes.
"""
import math

import numpy as np

CORDE = 0.001


def n_arc(r, balayage=2 * math.pi, corde=CORDE):
    """Nombre de segments d'un arc de rayon r (corde ≤ `corde`)."""
    if r <= corde:
        return 8
    da = 2 * math.acos(max(-1.0, 1.0 - corde / r))
    return max(8, int(math.ceil(abs(balayage) / da)))


def ellipse(c, a, b, n=None, a0=0.0, a1=2 * math.pi, ferme=True):
    """Points d'une ellipse de centre c, demi-axes a (x) et b (y), de l'angle a0 à a1 (radians)."""
    n = n or n_arc(max(a, b), a1 - a0)
    t = np.linspace(a0, a1, n, endpoint=not ferme)
    return np.c_[c[0] + a * np.cos(t), c[1] + b * np.sin(t)]


def aire(r):
    r = np.asarray(r, float)
    return 0.5 * float(np.dot(r[:, 0], np.roll(r[:, 1], -1)) - np.dot(r[:, 1], np.roll(r[:, 0], -1)))


def trigo(r):
    r = np.asarray(r, float)
    return r if aire(r) >= 0 else r[::-1]


def trait(P, w, bouts="plat", onglet_max=3.0):
    """Contour (trigonométrique) d'un trait de largeur w le long de la polyligne P ; bouts « plat » ou « rond »."""
    P = np.asarray(P, float)
    keep = np.r_[True, np.hypot(*np.diff(P, axis=0).T) > 1e-9]
    P = P[keep]
    d = np.diff(P, axis=0)
    t = d / np.hypot(*d.T)[:, None]
    ns = np.c_[-t[:, 1], t[:, 0]]
    nv = np.vstack([ns[:1], ns[:-1] + ns[1:], ns[-1:]])
    nv /= np.maximum(np.hypot(*nv.T), 1e-12)[:, None]
    fac = np.ones(len(P))
    if len(P) > 2:
        c = np.einsum("ij,ij->i", nv[1:-1], ns[1:])
        fac[1:-1] = 1.0 / np.maximum(c, 1.0 / onglet_max)
    off = nv * (0.5 * w * fac)[:, None]
    g, dr = P + off, P - off
    if bouts == "rond":
        h = 0.5 * w
        n = n_arc(h, math.pi)
        a_fin = math.atan2(t[-1, 1], t[-1, 0])
        a_deb = math.atan2(t[0, 1], t[0, 0])
        cap_f = ellipse(P[-1], h, h, n + 1, a_fin - math.pi / 2, a_fin + math.pi / 2, ferme=False)[1:-1]
        cap_d = ellipse(P[0], h, h, n + 1, a_deb + math.pi / 2, a_deb + 3 * math.pi / 2, ferme=False)[1:-1]
        return trigo(np.vstack([dr, cap_f, g[::-1], cap_d]))
    return trigo(np.vstack([dr, g[::-1]]))


def arc_trait(c, r, a0, a1, w, bouts="plat"):
    """Trait de largeur w le long de l'arc de cercle (centre c, rayon r) de a0 à a1 (radians, sens quelconque)."""
    n = n_arc(r + w / 2, a1 - a0) + 1
    return trait(ellipse(c, r, r, n, a0, a1, ferme=False), w, bouts)


def arc_ellipse_trait(c, a, b, t0, t1, w, bouts="plat"):
    """Trait de largeur w le long d'un arc d'ellipse (paramètre t de t0 à t1)."""
    n = n_arc(max(a, b) + w / 2, t1 - t0) + 1
    return trait(ellipse(c, a, b, n, t0, t1, ferme=False), w, bouts)


def anneau_ellipse(c, a, b, w):
    """Anneau elliptique (demi-axes extérieurs a, b ; largeur w) en deux moitiés sans trou (droite, gauche)."""
    out = []
    for t0 in (-math.pi / 2, math.pi / 2):
        n = n_arc(max(a, b), math.pi) + 1
        ext = ellipse(c, a, b, n, t0, t0 + math.pi, ferme=False)
        intr = ellipse(c, a - w, b - w, n, t0, t0 + math.pi, ferme=False)
        out.append(trigo(np.vstack([ext, intr[::-1]])))
    return out


# --------------------------------------------------------------------------- PMR (ISO 7001 stylisé)
PMR_BOITE = (0.86, 0.95)        # emprise naturelle (x, y) du pictogramme unitaire


def pmr(hauteur, miroir=False):
    """Pictogramme « fauteuil roulant » (ISO 7001 stylisé, personne tournée vers +x) de hauteur `hauteur` (y),
    centré sur sa boîte : tête (disque), tronc, bras, cuisse, jambe (traits à bouts ronds), roue (anneau ouvert
    vers l'avant). -> polygones [[anneau]]."""
    k = hauteur / PMR_BOITE[1]
    elems = [ellipse((0.58, 0.88), 0.095, 0.095),
             trait([(0.45, 0.74), (0.42, 0.42)], 0.13, "rond"),
             trait([(0.44, 0.64), (0.66, 0.64)], 0.10, "rond"),
             trait([(0.42, 0.42), (0.72, 0.42)], 0.13, "rond"),
             trait([(0.72, 0.42), (0.86, 0.10)], 0.12, "rond"),
             arc_trait((0.40, 0.36), 0.29, math.radians(55.0), math.radians(335.0), 0.085, "rond")]
    c = np.array([0.067 + 0.86 / 2, 0.027 + 0.95 / 2])
    out = []
    for r in elems:
        q = (np.asarray(r) - c) * k
        if miroir:
            q[:, 0] = -q[:, 0]
            q = q[::-1]
        out.append([trigo(q)])
    return out


# --------------------------------------------------------------------------- chiffres
def _chiffre(ch, Wd, Hd, e):
    """Traits d'un chiffre (0, 3, 5) dans la boîte [0, Wd] x [0, Hd] (lignes médianes à e/2 du bord)."""
    xl, xr, yb, yt = e / 2, Wd - e / 2, e / 2, Hd - e / 2
    cx, rx = (xl + xr) / 2, (xr - xl) / 2
    out = []
    if ch == "0":
        a, b = rx + e / 2, (yt - yb) / 2 + e / 2
        out += anneau_ellipse((cx, Hd / 2), a, b, e)
    elif ch == "5":
        ym = 0.56 * Hd
        cy, ry = (ym + yb) / 2, (ym - yb) / 2
        t0 = math.radians(125.0)
        p0 = (cx + rx * math.cos(t0), cy + ry * math.sin(t0))
        out.append(trait([(xr, yt), (xl + 0.08 * rx, yt), (p0[0], p0[1])], e, "plat"))
        out.append(arc_ellipse_trait((cx, cy), rx, ry, t0, math.radians(-140.0), e, "plat"))
    elif ch == "3":
        ym = 0.52 * Hd
        ryu, cyu = (yt - ym) / 2, (yt + ym) / 2
        ryl, cyl = (ym - yb) / 2, (ym + yb) / 2
        out.append(arc_ellipse_trait((cx, cyu), rx, ryu, math.radians(150.0), math.radians(-90.0), e, "plat"))
        out.append(arc_ellipse_trait((cx, cyl), rx, ryl, math.radians(90.0), math.radians(-150.0), e, "plat"))
    else:
        raise ValueError(f"chiffre non construit : {ch}")
    return out


def texte_ellipse(texte, L, W, anneau=0.10, trait_chiffre=None):
    """Rappel de vitesse « 30 » / « 50 » : anneau elliptique L (y, sens de lecture) x W (x) de largeur `anneau`,
    chiffres côte à côte (de gauche à droite pour un conducteur roulant vers +y), anamorphosés le long de y,
    centrés sur l'origine. -> polygones [[anneau]]."""
    e = trait_chiffre or round(0.10 * W, 3)
    polys = [[r] for r in anneau_ellipse((0.0, 0.0), W / 2, L / 2, anneau)]
    Hd = 0.60 * L
    Wd = 0.27 * W
    gap = 0.07 * W
    x0 = -(len(texte) * Wd + (len(texte) - 1) * gap) / 2
    for i, ch in enumerate(texte):
        dx = x0 + i * (Wd + gap)
        for r in _chiffre(ch, Wd, Hd, e):
            polys.append([trigo(np.asarray(r) + np.array([dx, -Hd / 2]))])
    return polys


# --------------------------------------------------------------------------- T de stationnement
def t_stationnement(barre, jambe, w):
    """T de stationnement : barre de longueur `barre` le long de x en haut (y = 0), jambe de longueur `jambe`
    vers −y depuis le milieu ; traits de largeur w ; origine au milieu de la barre."""
    return [[trait([(-barre / 2, -w / 2), (barre / 2, -w / 2)], w)],
            [trait([(0.0, -w / 2), (0.0, -jambe)], w)]]


# --------------------------------------------------------------------------- redressement de contours
def redresser(r, tol=0.025, lmin=0.06, lisse=0.05):
    """Contour sans marche d'escalier : lissage gaussien (σ `lisse`), Douglas-Peucker `tol`, puis chaque arête
    plus courte que `lmin` est remplacée par l'intersection de ses deux voisines (coin vif d'un tracé raster
    chanfreiné) quand celle-ci reste à moins de 2·lmin des sommets ; enfin Douglas-Peucker `tol`."""
    import marquages_commun as M
    r = np.asarray(r, float)
    q = M.lisser_anneau(r, sigma_m=lisse) if lisse else r
    q = M.douglas_peucker(q, tol, ferme=True)
    for _ in range(len(q)):
        n = len(q)
        if n <= 4:
            break
        e = np.roll(q, -1, axis=0) - q
        L = np.hypot(*e.T)
        k = int(np.argmin(L))
        if L[k] >= lmin:
            break
        a0, a1 = q[k - 1], q[k]
        b0, b1 = q[(k + 1) % n], q[(k + 2) % n]
        da, db = a1 - a0, b1 - b0
        den = da[0] * db[1] - da[1] * db[0]
        if abs(den) < 1e-9:
            q = np.delete(q, (k + 1) % n, axis=0)
            continue
        t = ((b0 - a0)[0] * db[1] - (b0 - a0)[1] * db[0]) / den
        x = a0 + da * t
        if np.hypot(*(x - a1)) > 2 * lmin or np.hypot(*(x - b0)) > 2 * lmin:
            q = np.vstack([q[:k], [(a1 + b0) / 2], q[k + 2:]]) if k + 1 < n else np.vstack([[(a1 + b0) / 2], q[1:k]])
            continue
        if k + 1 < n:
            q = np.vstack([q[:k], [x], q[k + 2:]])
        else:
            q = np.vstack([[x], q[1:k]])
    q = M.douglas_peucker(q, tol, ferme=True)
    return trigo(q)


def adoucir(P, rayon=6.0, angle_min=10.0, part=0.45, ecart_max=0.03):
    """Congés circulaires aux sommets d'une polyligne dont la déviation dépasse `angle_min` : rayon `rayon`,
    réduit pour que la tangente ne dépasse pas `part` des segments voisins et que le congé reste à moins de
    `ecart_max` du sommet levé ; les extrémités ne bougent pas."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u, v = b - a, c - b
        lu, lv = float(np.hypot(*u)), float(np.hypot(*v))
        if lu < 1e-9 or lv < 1e-9:
            continue
        u, v = u / lu, v / lv
        dev = math.acos(max(-1.0, min(1.0, float(u @ v))))
        if math.degrees(dev) < angle_min:
            out.append(b)
            continue
        tmax = part * min(lu, lv)
        R = min(rayon, tmax / math.tan(dev / 2), ecart_max / max(1.0 / math.cos(dev / 2) - 1.0, 1e-9))
        t = R * math.tan(dev / 2)
        p0, p1 = b - u * t, b + v * t
        sgn = 1.0 if (u[0] * v[1] - u[1] * v[0]) > 0 else -1.0
        n0 = np.array([-u[1], u[0]]) * sgn
        cc = p0 + n0 * R
        a0 = math.atan2(*(p0 - cc)[::-1])
        a1 = math.atan2(*(p1 - cc)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        m = max(2, n_arc(R, da))
        ang = a0 + da * np.linspace(0.0, 1.0, m + 1)
        out += list(np.c_[cc[0] + R * np.cos(ang), cc[1] + R * np.sin(ang)])
    out.append(P[-1])
    Q = np.array(out)
    keep = np.r_[True, np.hypot(*np.diff(Q, axis=0).T) > 1e-6]
    return Q[keep]


# --------------------------------------------------------------------------- figurine vélo D1
def velo_d1(gabarit):
    """Figurine D1 reconstruite : corps du tracé de l'annexe redressé (droites ajustées, encoches des lignes de
    grille supprimées, coins vifs), tête = ellipse exacte (≥ 32 segments) ajustée sur la boîte de la tête du
    tracé, roues = ellipses exactes 0,30 x 0,55 de la spec. `gabarit` = entrée VELO de marquages_geometrie.json."""
    P = np.asarray(gabarit["polygone"], float)
    tete = P[:, 1] >= 1.09
    corps = redresser(P[~tete] if tete.sum() >= 3 else P, tol=0.004, lmin=0.03, lisse=0.0)
    xt, yt = P[tete, 0], P[tete, 1]
    cx, a = 0.5 * (xt.min() + xt.max()), 0.5 * (xt.max() - xt.min())
    y0, y1 = float(yt.min()) - 0.01, float(yt.max())
    tete_e = ellipse((cx, 0.5 * (y0 + y1)), a, 0.5 * (y1 - y0), n=max(32, n_arc(max(a, (y1 - y0) / 2))))
    polys = [[corps], [trigo(tete_e)]]
    for _, part in sorted(gabarit.get("parties", {}).items()):
        if isinstance(part, dict) and "polygone" in part:
            polys.append([trigo(np.asarray(part["polygone"], float))])
    return polys
