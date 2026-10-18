# -*- coding: utf-8 -*-
"""Épures de giration des véhicules de projet (lot L3a, PLAN_GENERATEUR § 3).

Le balayage est l'enveloppe de la caisse d'un véhicule dont un point (le « point guide ») suit un axe donné
(VU p. 143-144 : « courbes décrites par les roues et la caisse […] ; en carrefour urbain, encombrement total de la
caisse » ; RF-GV-TRJ-007). Modèle cinématique « bicyclette » sans glissement, une unité rigide par caisse :

- point guide = centre de l'essieu avant directeur de l'unité motrice (convention [G], écrite dans le JSON) ;
- l'essieu arrière équivalent de chaque unité suit son meneur (point guide, sellette ou articulation) en tractrice ;
  la tractrice est intégrée EXACTEMENT sur chaque pas rectiligne du meneur : tan(φ'/2) = tan(φ/2)·exp(−s/L) ;
- chaque caisse est un rectangle (largeur de balayage du JSON), chanfreiné par le rayon avant de la semi-remorque
  (96/53 § 4.4 : 2,04 m autour du pivot) ; l'articulation d'un autobus articulé porte un soufflet (disque de
  diamètre = largeur, convention [G]) ;
- enveloppe = réunion des enveloppes convexes de deux positions successives de chaque caisse, rendue exacte par une
  fonction de distance signée (zéro = bord exact de la réunion de polygones convexes) et contourée par « marching
  squares » (interpolation linéaire sur les arêtes de la grille) ; anneaux orientés : extérieur direct, trous
  indirects.

Dépendances : Python ≥ 3.9 et numpy (présents dans hython 22 ; shapely n'est PAS requis).

API (pour le solveur de carrefours, lots L3, L5) :

    from vehicules.balayage import vehicule, rayon_min, balayage, axe_virage
    v = vehicule("bus_standard_12m")
    rayon_min(v)                       # rayon minimal de la trajectoire du point guide (m), régime établi
    poly = balayage(v, axe)            # axe : [(x, y), …] en mètres -> Polygone(exterieur, trous)
    poly.exterieur                     # [(x, y), …] sens direct, fermé implicitement
    distance_signee(poly, (x, y))      # < 0 dedans ; « premier contact + 0,30 m » = distance ≥ 0,30
    d = balayage_detail(v, axe)        # + poses, braquage, faisabilité (rayon local de l'axe ≥ rayon_min)
    faisabilite(v, axe)                # sans enveloppe : rayon_axe_min, faisable

Aucune valeur de véhicule n'est écrite ici : tout vient de `vehicules_projet.json` (construit et sourcé par
`construire_vehicules.py`).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Iterable, NamedTuple, Sequence

import numpy as np

ICI = Path(__file__).resolve().parent
FICHIER = ICI / "vehicules_projet.json"

PAS_CINEMATIQUE = 0.05      # m : pas du point guide pour l'intégration (tractrice exacte par pas rectiligne)
PAS_ENVELOPPE = 0.25        # m : pas des positions réunies dans l'enveloppe (flèche ≤ 2 mm pour R ≥ 4 m)
RESOLUTION = 0.05           # m : maille de la fonction de distance contourée
TOLERANCE_SIMPLIFICATION = 0.003   # m : Douglas-Peucker sur les anneaux rendus
SEGMENTS_ARC = 8            # segments des arcs de chanfrein ; 24 pour le soufflet


# ----------------------------------------------------------------------------------------------------------------
# Véhicules
# ----------------------------------------------------------------------------------------------------------------
class Unite(NamedTuple):
    nom: str
    empattement: float          # unité motrice : essieu avant -> essieu arrière équivalent ; remorque : attelage -> essieu équivalent
    avant: float                # abscisse de l'avant de la caisse depuis l'essieu équivalent (> 0)
    arriere: float              # distance de l'arrière de la caisse derrière l'essieu équivalent (> 0)
    largeur: float              # largeur de balayage
    attelage: float | None      # abscisse (depuis l'essieu équivalent, + vers l'avant) du point d'attelage de l'unité suivante
    rayon_avant_pivot: float | None   # chanfrein : points en avant du pivot à ≤ r du pivot (semi-remorque)
    soufflet: bool              # disque de diamètre = largeur au point d'attelage de l'unité suivante


class Vehicule(NamedTuple):
    nom: str
    libelle: str
    unites: tuple
    rayon_guide_min: float      # rayon minimal du point guide (régime établi, braquage maximal)
    braquage_max: float         # angle « bicyclette » maximal (rad) = asin(empattement / rayon_guide_min)

    @property
    def longueur_totale(self) -> float:
        """Longueur hors tout, véhicule aligné (abscisses depuis l'essieu équivalent de l'unité motrice)."""
        x = 0.0
        avant, arriere = [], []
        for k, u in enumerate(self.unites):
            if k > 0:                       # essieu de l'unité k = attelage de l'unité k−1 − empattement de k
                x = x + self.unites[k - 1].attelage - u.empattement
            avant.append(x + u.avant)
            arriere.append(x - u.arriere)
        return max(avant) - min(arriere)


def _valeur(d, cle):
    x = d.get(cle)
    if x is None:
        return None
    return float(x["valeur"]) if isinstance(x, dict) else (float(x) if not isinstance(x, bool) else x)


def unites_depuis_json(entree: dict) -> tuple:
    """Unités cinématiques d'une entrée de `vehicules_projet.json` (champ `cinematique`)."""
    res = []
    for u in entree["cinematique"]["unites"]:
        att = _valeur(u, "attelage")
        res.append(Unite(
            nom=u["nom"],
            empattement=_valeur(u, "empattement"),
            avant=_valeur(u, "avant"),
            arriere=_valeur(u, "arriere"),
            largeur=_valeur(u, "largeur_balayage"),
            attelage=att,
            rayon_avant_pivot=_valeur(u, "rayon_avant_pivot"),
            soufflet=bool(u.get("soufflet", False)),
        ))
    return tuple(res)


@lru_cache(maxsize=4)
def _charger(chemin: str) -> dict:
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def catalogue(chemin: str | Path | None = None) -> dict:
    """Le JSON des véhicules de projet (dict)."""
    return _charger(str(chemin or FICHIER))


def noms(chemin=None) -> list:
    return sorted(catalogue(chemin)["vehicules"])


def vehicule(nom: str, chemin=None) -> Vehicule:
    """Véhicule par son nom (`noms()`) ou un alias du JSON (« VL », « bus », « semi », « car »…)."""
    cat = catalogue(chemin)
    nom = cat.get("alias", {}).get(nom, nom)
    e = cat["vehicules"][nom]
    unites = unites_depuis_json(e)
    rg = float(e["giration"]["rayon_point_guide_min"]["valeur"])
    return Vehicule(nom=nom, libelle=e.get("libelle", nom), unites=unites, rayon_guide_min=rg,
                    braquage_max=math.asin(min(1.0, unites[0].empattement / rg)))


def rayon_min(v: Vehicule | str) -> float:
    """Rayon minimal (m) de la trajectoire du point guide (centre de l'essieu avant) en régime établi."""
    if isinstance(v, str):
        v = vehicule(v)
    return v.rayon_guide_min


# ----------------------------------------------------------------------------------------------------------------
# Géométrie des caisses
# ----------------------------------------------------------------------------------------------------------------
def _arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n))
            for k in range(1, n)]


def contour_local(u: Unite) -> list:
    """Contour de la caisse dans le repère de l'unité (x vers l'avant depuis l'essieu équivalent, y à gauche),
    sens direct (convexe)."""
    w2 = u.largeur / 2.0
    xa, xr = u.avant, -u.arriere
    r = u.rayon_avant_pivot
    xh = u.empattement                      # pivot d'une remorque : à l'empattement en avant de son essieu
    f = xa - xh
    if r is None or f <= 0 or math.hypot(f, w2) <= r or r <= w2 or r <= f:
        return [(xr, -w2), (xa, -w2), (xa, w2), (xr, w2)]
    xs = xh + math.sqrt(r * r - w2 * w2)     # côté ∩ cercle
    yf = math.sqrt(r * r - f * f)            # face avant ∩ cercle
    a0, a1 = math.atan2(-w2, xs - xh), math.atan2(-yf, f)
    pts = [(xr, -w2), (xs, -w2)]
    pts += _arc(xh, 0.0, r, a0, a1, SEGMENTS_ARC)
    pts += [(xa, -yf), (xa, yf)]
    pts += _arc(xh, 0.0, r, -a1, -a0, SEGMENTS_ARC)
    pts += [(xs, w2), (xr, w2)]
    return pts


def _soufflet_local(u: Unite) -> list:
    r = u.largeur / 2.0
    return [(u.attelage + r * math.cos(2 * math.pi * k / 24), r * math.sin(2 * math.pi * k / 24)) for k in range(24)]


def caisses_locales(v: Vehicule) -> list:
    """[(indice d'unité, contour local), …] : caisses et soufflets."""
    res = []
    for k, u in enumerate(v.unites):
        res.append((k, contour_local(u)))
        if u.soufflet and u.attelage is not None:
            res.append((k, _soufflet_local(u)))
    return res


def _monde(contour, p, c, s):
    px, py = p
    return [(px + c * x - s * y, py + s * x + c * y) for (x, y) in contour]


def polygones_pose(v: Vehicule, pose, caisses=None) -> list:
    """Polygones monde (convexes, sens direct) d'une pose."""
    caisses = caisses or caisses_locales(v)
    return [_monde(cl, pose[k][0], pose[k][1][0], pose[k][1][1]) for (k, cl) in caisses]


# ----------------------------------------------------------------------------------------------------------------
# Cinématique
# ----------------------------------------------------------------------------------------------------------------
def _suivre(f, a, b, l):
    """Tractrice exacte : le suiveur f (à distance l du meneur a) quand le meneur va de a à b en ligne droite."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    s = math.hypot(dx, dy)
    vx, vy = a[0] - f[0], a[1] - f[1]
    if s < 1e-12:
        return f
    ux, uy = dx / s, dy / s
    phi = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t = math.tan(phi / 2.0) * math.exp(-s / l)
    phi2 = 2.0 * math.atan(t)
    c, sn = math.cos(phi2), math.sin(phi2)
    wx, wy = l * (c * ux - sn * uy), l * (sn * ux + c * uy)
    return (b[0] - wx, b[1] - wy)


def reechantillonner(axe: Sequence, pas: float) -> list:
    """Polyligne rééchantillonnée à abscisse curviligne constante (les sommets d'origine ne sont pas conservés)."""
    pts = [(float(x), float(y)) for (x, y) in axe]
    out = [pts[0]]
    reste = pas
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        lg = math.hypot(x1 - x0, y1 - y0)
        if lg == 0:
            continue
        s = reste
        while s <= lg + 1e-12:
            t = s / lg
            out.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))
            s += pas
        reste = s - lg
    if math.hypot(out[-1][0] - pts[-1][0], out[-1][1] - pts[-1][1]) > 1e-9:
        out.append(pts[-1])
    return out


def simuler(v: Vehicule, axe: Sequence, pas: float = PAS_CINEMATIQUE, amorce: float | None = None) -> dict:
    """Poses successives du véhicule dont le point guide parcourt `axe`.

    `amorce` : longueur d'approche rectiligne ajoutée avant le début de l'axe, le long de sa tangente initiale
    (défaut : longueur totale du véhicule), pour que le véhicule arrive aligné ; les poses de l'amorce ne sont pas
    retournées. Pose = ((point essieu équivalent, (cos θ, sin θ)) par unité).
    """
    u = v.unites
    pts = reechantillonner(axe, pas)
    if len(pts) < 2:
        raise ValueError("axe trop court")
    dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
    n0 = math.hypot(dx, dy)
    tx, ty = dx / n0, dy / n0
    if amorce is None:
        amorce = v.longueur_totale
    na = int(math.ceil(amorce / pas))
    chemin = [(pts[0][0] - tx * pas * k, pts[0][1] - ty * pas * k) for k in range(na, 0, -1)] + pts
    i0 = na
    # pose initiale alignée
    g = chemin[0]
    p = [(g[0] - u[0].empattement * tx, g[1] - u[0].empattement * ty)]
    hd = [(tx, ty)]
    for k in range(1, len(u)):
        a = u[k - 1].attelage
        hx, hy = p[k - 1][0] + a * tx, p[k - 1][1] + a * ty
        p.append((hx - u[k].empattement * tx, hy - u[k].empattement * ty))
        hd.append((tx, ty))
    poses, guides, braquages = [], [], []
    m_tan = max(1, int(round(0.25 / pas)))
    if i0 == 0:
        poses.append(tuple(zip(p, hd)))
        guides.append(g)
        braquages.append(0.0)
    for i in range(1, len(chemin)):
        gn = chemin[i]
        p_old, hd_old = list(p), list(hd)
        p[0] = _suivre(p_old[0], g, gn, u[0].empattement)
        hx, hy = (gn[0] - p[0][0]) / u[0].empattement, (gn[1] - p[0][1]) / u[0].empattement
        hd[0] = (hx, hy)
        for k in range(1, len(u)):
            a = u[k - 1].attelage
            h_old = (p_old[k - 1][0] + a * hd_old[k - 1][0], p_old[k - 1][1] + a * hd_old[k - 1][1])
            h_new = (p[k - 1][0] + a * hd[k - 1][0], p[k - 1][1] + a * hd[k - 1][1])
            p[k] = _suivre(p_old[k], h_old, h_new, u[k].empattement)
            lk = u[k].empattement
            hd[k] = ((h_new[0] - p[k][0]) / lk, (h_new[1] - p[k][1]) / lk)
        # braquage « bicyclette » (indicatif) = angle entre la tangente de l'axe au point guide (sécante centrée sur
        # ± 0,25 m, qui lisse les sommets d'un arc polygonal) et le cap de l'unité motrice
        gs, gp = chemin[min(i + m_tan, len(chemin) - 1)], chemin[max(i - m_tan, 0)]
        sx, sy = gs[0] - gp[0], gs[1] - gp[1]
        delta = math.atan2(hx * sy - hy * sx, hx * sx + hy * sy)
        g = gn
        if i >= i0:
            poses.append(tuple(zip(tuple(p), tuple(hd))))
            guides.append(gn)
            braquages.append(delta)
    return {"poses": poses, "guides": guides, "braquages": braquages, "pas": pas}


# ----------------------------------------------------------------------------------------------------------------
# Enveloppe : réunion de polygones convexes par distance signée + marching squares
# ----------------------------------------------------------------------------------------------------------------
class Polygone(NamedTuple):
    exterieur: list
    trous: list

    @property
    def aire(self) -> float:
        return _aire(self.exterieur) + sum(_aire(t) for t in self.trous)


def _aire(r) -> float:
    a = 0.0
    for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
        a += x0 * y1 - x1 * y0
    return 0.5 * a


def _enveloppe_convexe(pts) -> list:
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts

    def croix(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    bas, haut = [], []
    for q in pts:
        while len(bas) >= 2 and croix(bas[-2], bas[-1], q) <= 0:
            bas.pop()
        bas.append(q)
    for q in reversed(pts):
        while len(haut) >= 2 and croix(haut[-2], haut[-1], q) <= 0:
            haut.pop()
        haut.append(q)
    return bas[:-1] + haut[:-1]


def convexes_balayes(v: Vehicule, poses, pas_enveloppe: float = PAS_ENVELOPPE, pas: float = PAS_CINEMATIQUE,
                     troncon: float = PAS_ENVELOPPE) -> list:
    """Polygones convexes dont la réunion est le balayage : chaque caisse à chaque position retenue (pas
    `pas_enveloppe`), plus, entre deux positions successives, l'enveloppe convexe de chaque tronçon (≤ `troncon`)
    du contour aux deux positions. Découper le contour évite l'erreur de corde d'une enveloppe convexe de la caisse
    entière (une caisse de 12 m qui tourne de 0,03 rad déborde de ~0,1 m vers le centre) : l'écart résiduel est
    ≤ tronçon × rotation par pas / 4 (quelques millimètres)."""
    caisses = caisses_locales(v)
    k = max(1, int(round(pas_enveloppe / pas)))
    idx = list(range(0, len(poses), k))
    if idx[-1] != len(poses) - 1:
        idx.append(len(poses) - 1)
    polys = [polygones_pose(v, poses[i], caisses) for i in idx]
    res = [P for ps in polys for P in ps]
    # découpage des contours locaux (identique pour toutes les positions)
    decoupes = []
    for (_, cl) in caisses:
        pts = []
        n = len(cl)
        for e in range(n):
            (x0, y0), (x1, y1) = cl[e], cl[(e + 1) % n]
            m = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / troncon)))
            pts += [(x0 + (x1 - x0) * q / m, y0 + (y1 - y0) * q / m) for q in range(m)]
        decoupes.append(pts)
    mondes = [[_monde(dc, poses[i][kc][0], poses[i][kc][1][0], poses[i][kc][1][1])
               for dc, (kc, _) in zip(decoupes, caisses)] for i in idx]
    for a, b in zip(mondes, mondes[1:]):
        for pa, pb in zip(a, b):
            n = len(pa)
            for e in range(n):
                h = _enveloppe_convexe([pa[e], pa[(e + 1) % n], pb[e], pb[(e + 1) % n]])
                if len(h) >= 3 and abs(_aire(h)) > 1e-10:
                    res.append(h)
    return res


def _champ(convexes, h):
    xs = [p[0] for c in convexes for p in c]
    ys = [p[1] for c in convexes for p in c]
    x0 = math.floor(min(xs) / h) * h - 3 * h
    y0 = math.floor(min(ys) / h) * h - 3 * h
    nx = int(math.ceil((max(xs) - x0) / h)) + 4
    ny = int(math.ceil((max(ys) - y0) / h)) + 4
    gx = x0 + h * np.arange(nx)
    gy = y0 + h * np.arange(ny)
    f = np.full((ny, nx), np.inf)
    for c in convexes:
        cx = [p[0] for p in c]
        cy = [p[1] for p in c]
        i0 = max(0, int(math.floor((min(cx) - x0) / h)) - 1)
        i1 = min(nx, int(math.ceil((max(cx) - x0) / h)) + 2)
        j0 = max(0, int(math.floor((min(cy) - y0) / h)) - 1)
        j1 = min(ny, int(math.ceil((max(cy) - y0) / h)) + 2)
        X = gx[i0:i1][None, :]
        Y = gy[j0:j1][:, None]
        g = None
        n = len(c)
        for e in range(n):
            (ax, ay), (bx, by) = c[e], c[(e + 1) % n]
            dx, dy = bx - ax, by - ay
            lg = math.hypot(dx, dy)
            if lg < 1e-12:
                continue
            nxe, nye = dy / lg, -dx / lg                  # normale extérieure (polygone direct)
            val = nxe * (X - ax) + nye * (Y - ay)
            g = val if g is None else np.maximum(g, val)
        if g is not None:
            sub = f[j0:j1, i0:i1]
            np.minimum(sub, g, out=sub)
    return f, x0, y0


def _contours(f, x0, y0, h) -> list:
    """Marching squares sur f (< 0 dedans) ; anneaux orientés dedans à gauche."""
    ny, nx = f.shape
    dedans = f < 0
    b0 = dedans[:-1, :-1]
    b1 = dedans[:-1, 1:]
    b2 = dedans[1:, 1:]
    b3 = dedans[1:, :-1]
    cas = b0.astype(np.int8) | (b1.astype(np.int8) << 1) | (b2.astype(np.int8) << 2) | (b3.astype(np.int8) << 3)
    js, is_ = np.nonzero((cas != 0) & (cas != 15))
    suivant = {}

    def aretes(j, i):
        return (("h", j, i), ("v", j, i + 1), ("h", j + 1, i), ("v", j, i))

    for j, i in zip(js.tolist(), is_.tolist()):
        c = int(cas[j, i])
        e = aretes(j, i)
        b = [(c >> k) & 1 for k in range(4)]
        n = sum(b)
        segs = []
        if n == 1:
            k = b.index(1)
            segs.append((e[k], e[(k - 1) % 4]))
        elif n == 3:
            k = b.index(0)
            segs.append((e[(k - 1) % 4], e[k]))
        else:
            ks = [k for k in range(4) if b[k]]
            if ks[1] - ks[0] != 2:                      # deux coins voisins c_k, c_k+1 dedans
                k = 3 if ks == [0, 3] else ks[0]
                segs.append((e[(k + 1) % 4], e[(k - 1) % 4]))
            else:                                       # selle : valeur au centre
                centre = 0.25 * (f[j, i] + f[j, i + 1] + f[j + 1, i + 1] + f[j + 1, i])
                if centre < 0:
                    for k in range(4):
                        if not b[k]:
                            segs.append((e[(k - 1) % 4], e[k]))
                else:
                    for k in range(4):
                        if b[k]:
                            segs.append((e[k], e[(k - 1) % 4]))
        for a, z in segs:
            suivant[a] = z

    def point(cle):
        t, j, i = cle
        if t == "h":
            fa, fb = f[j, i], f[j, i + 1]
            s = float(fa / (fa - fb))
            return (x0 + h * (i + s), y0 + h * j)
        fa, fb = f[j, i], f[j + 1, i]
        s = float(fa / (fa - fb))
        return (x0 + h * i, y0 + h * (j + s))

    anneaux = []
    vus = set()
    for depart in sorted(suivant):
        if depart in vus:
            continue
        r = []
        cle = depart
        while cle not in vus:
            vus.add(cle)
            r.append(point(cle))
            cle = suivant.get(cle)
            if cle is None:
                break
        if len(r) >= 3:
            anneaux.append(r)
    return anneaux


def _simplifier(r, tol):
    """Douglas-Peucker sur un anneau fermé (déterministe)."""
    n = len(r)
    if n < 8 or tol <= 0:
        return r
    # coupure aux deux points les plus éloignés du premier
    p0 = r[0]
    k = max(range(n), key=lambda q: (r[q][0] - p0[0]) ** 2 + (r[q][1] - p0[1]) ** 2)
    garder = [False] * n
    garder[0] = garder[k] = True
    pile = [(0, k), (k, n)]
    while pile:
        a, b = pile.pop()
        pa, pb = r[a], r[b % n]
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        lg = math.hypot(dx, dy)
        dmax, imax = -1.0, -1
        for q in range(a + 1, b):
            px, py = r[q]
            if lg < 1e-12:
                d = math.hypot(px - pa[0], py - pa[1])
            else:
                d = abs(dx * (py - pa[1]) - dy * (px - pa[0])) / lg
            if d > dmax:
                dmax, imax = d, q
        if dmax > tol:
            garder[imax] = True
            pile.append((a, imax))
            pile.append((imax, b))
    return [p for p, g in zip(r, garder) if g]


def _dans_anneau(p, r) -> bool:
    x, y = p
    dedans = False
    for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if xi > x:
                dedans = not dedans
    return dedans


def reunion_convexes(convexes, resolution: float = RESOLUTION,
                     tolerance: float = TOLERANCE_SIMPLIFICATION) -> list:
    """Réunion de polygones convexes (sens direct) -> [Polygone], le plus grand en premier."""
    f, x0, y0 = _champ(convexes, resolution)
    anneaux = [_simplifier(r, tolerance) for r in _contours(f, x0, y0, resolution)]
    ext = [r for r in anneaux if _aire(r) > 0]
    trous = [r for r in anneaux if _aire(r) < 0]
    ext.sort(key=lambda r: -_aire(r))
    res = [Polygone(r, []) for r in ext]
    for t in trous:
        for P in res:
            if _dans_anneau(t[0], P.exterieur):
                P.trous.append(t)
                break
    return res


def enveloppe(v: Vehicule, poses, resolution: float = RESOLUTION, pas_enveloppe: float = PAS_ENVELOPPE,
              pas: float = PAS_CINEMATIQUE) -> list:
    return reunion_convexes(convexes_balayes(v, poses, pas_enveloppe, pas), resolution)


def balayage_detail(v: Vehicule | str, axe: Sequence, pas: float = PAS_CINEMATIQUE, amorce: float | None = None,
                    resolution: float = RESOLUTION, pas_enveloppe: float = PAS_ENVELOPPE) -> dict:
    """Balayage + diagnostic : polygones, poses, braquage maximal demandé et faisabilité."""
    if isinstance(v, str):
        v = vehicule(v)
    sim = simuler(v, axe, pas, amorce)
    polys = enveloppe(v, sim["poses"], resolution, pas_enveloppe, pas)
    fa = faisabilite(v, axe, sim=sim)
    return {
        "vehicule": v.nom,
        "polygones": polys,
        "polygone": polys[0] if polys else Polygone([], []),
        "poses": sim["poses"],
        "guides": sim["guides"],
        "braquages": sim["braquages"],
        **{k: fa[k] for k in ("rayon_axe_min", "rayon_min_vehicule", "braquage_max_demande_deg",
                              "braquage_max_vehicule_deg", "faisable")},
    }


def rayon_axe_min(axe: Sequence) -> float:
    """Plus petit rayon local de l'axe, aux sommets d'origine : min(l1, l2) / (2 sin(θ/2)) (θ : déviation au
    sommet, l1, l2 : côtés adjacents). Exact pour un arc échantillonné par des points de l'arc (L1) ; un angle vif
    donne le plus petit arc qui tiendrait entre les côtés."""
    pts = []
    for (x, y) in axe:
        if not pts or math.hypot(x - pts[-1][0], y - pts[-1][1]) > 1e-9:
            pts.append((float(x), float(y)))
    rmin = float("inf")
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = c[0] - b[0], c[1] - b[1]
        l1, l2 = math.hypot(ux, uy), math.hypot(vx, vy)
        th = abs(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy))
        if th > 1e-12:
            rmin = min(rmin, min(l1, l2) / (2.0 * math.sin(th / 2.0)))
    return rmin


def faisabilite(v: Vehicule | str, axe: Sequence, pas: float = PAS_CINEMATIQUE, amorce: float | None = None,
                sim: dict | None = None) -> dict:
    """Faisabilité d'un axe pour le véhicule : rayon local minimal de l'axe ≥ rayon_min(v) (critère officiel :
    en régime transitoire le braquage reste ≤ asin(empattement × courbure max), il n'y a pas de dépassement) ;
    braquage demandé par la simulation donné à titre indicatif."""
    if isinstance(v, str):
        v = vehicule(v)
    sim = sim or simuler(v, axe, pas, amorce)
    dmax = max((abs(d) for d in sim["braquages"]), default=0.0)
    r = rayon_axe_min(axe)
    return {"vehicule": v.nom, "rayon_axe_min": r, "rayon_min_vehicule": v.rayon_guide_min,
            "braquage_max_demande_deg": math.degrees(dmax),
            "braquage_max_vehicule_deg": math.degrees(v.braquage_max),
            "faisable": r >= v.rayon_guide_min * (1.0 - 1e-6)}


def balayage(v: Vehicule | str, axe: Sequence, **options) -> Polygone:
    """Enveloppe de la caisse quand le point guide du véhicule parcourt `axe` -> Polygone(exterieur, trous)."""
    return balayage_detail(v, axe, **options)["polygone"]


# ----------------------------------------------------------------------------------------------------------------
# Outils pour le solveur
# ----------------------------------------------------------------------------------------------------------------
def _dist_segments(p, r):
    a = np.asarray(r, dtype=float)
    b = np.roll(a, -1, axis=0)
    d = b - a
    q = np.asarray(p, dtype=float)
    ll = np.maximum((d * d).sum(1), 1e-24)
    t = np.clip(((q - a) * d).sum(1) / ll, 0.0, 1.0)
    proj = a + d * t[:, None]
    return float(np.sqrt(((proj - q) ** 2).sum(1)).min())


def distance_signee(poly: Polygone, p) -> float:
    """Distance (m) du point p au bord du balayage ; négative à l'intérieur."""
    d = min([_dist_segments(p, poly.exterieur)] + [_dist_segments(p, t) for t in poly.trous])
    dedans = _dans_anneau(p, poly.exterieur) and not any(_dans_anneau(p, t) for t in poly.trous)
    return -d if dedans else d


def contient(poly: Polygone, p) -> bool:
    return distance_signee(poly, p) < 0


def axe_virage(rayon: float, angle_deg: float, approche: float, sortie: float, depart=(0.0, 0.0),
               cap_deg: float = 0.0, gauche: bool = True, fleche: float = 0.0005) -> list:
    """Axe « droite – arc tangent – droite » (RF-GV-TRJ-006), arc échantillonné à flèche ≤ `fleche` (L1)."""
    c0, s0 = math.cos(math.radians(cap_deg)), math.sin(math.radians(cap_deg))
    x, y = depart
    pts = [(x, y)]
    x, y = x + approche * c0, y + approche * s0
    pts.append((x, y))
    sg = 1.0 if gauche else -1.0
    cx, cy = x - sg * rayon * s0, y + sg * rayon * c0                 # centre à gauche (ou à droite)
    a0 = math.atan2(y - cy, x - cx)
    pas_ang = 2.0 * math.acos(max(-1.0, 1.0 - fleche / rayon))
    tot = math.radians(angle_deg)
    n = max(1, int(math.ceil(tot / pas_ang)))
    for k in range(1, n + 1):
        a = a0 + sg * tot * k / n
        pts.append((cx + rayon * math.cos(a), cy + rayon * math.sin(a)))
    cap = math.radians(cap_deg) + sg * tot
    if sortie > 0:
        x, y = pts[-1]
        pts.append((x + sortie * math.cos(cap), y + sortie * math.sin(cap)))
    return pts


# ----------------------------------------------------------------------------------------------------------------
# Régime établi (analytique) : sert à caler le braquage minimal et aux contrôles
# ----------------------------------------------------------------------------------------------------------------
def _dist_point_poly(p, poly) -> float:
    if _dans_anneau(p, poly):
        return 0.0
    return _dist_segments(p, poly)


def pose_etablie(unites: Sequence[Unite], r0: float) -> tuple:
    """Pose en virage établi à gauche, centre à l'origine, essieu équivalent de l'unité motrice en (0, −r0),
    cap +x. Retourne la pose (même forme que `simuler`)."""
    p = [(0.0, -r0)]
    hd = [(1.0, 0.0)]
    for k in range(1, len(unites)):
        a = unites[k - 1].attelage
        hx, hy = p[k - 1][0] + a * hd[k - 1][0], p[k - 1][1] + a * hd[k - 1][1]
        rh = math.hypot(hx, hy)
        lk = unites[k].empattement
        rk = math.sqrt(max(rh * rh - lk * lk, 0.0))
        ang = math.atan2(hy, hx) - math.atan2(lk, rk)        # en retard (sens direct) sur l'attelage
        pk = (rk * math.cos(ang), rk * math.sin(ang))
        p.append(pk)
        hd.append(((hx - pk[0]) / lk, (hy - pk[1]) / lk))
    return tuple(zip(p, hd))


def rayons_etablis(unites: Sequence[Unite], r0: float) -> dict:
    """Rayons extérieur (caisse) et intérieur du balayage en régime établi pour un rayon r0 de l'essieu arrière
    équivalent de l'unité motrice ; rayon du point guide."""
    v = Vehicule("_", "_", tuple(unites), 1.0, 0.0)
    polys = polygones_pose(v, pose_etablie(unites, r0))
    rext = max(math.hypot(x, y) for P in polys for (x, y) in P)
    rint = min(_dist_point_poly((0.0, 0.0), P) for P in polys)
    return {"r0": r0, "Rext": rext, "Rint": rint, "R_guide": math.hypot(r0, unites[0].empattement)}


def r0_pour_rext(unites: Sequence[Unite], rext: float) -> float:
    """Rayon de l'essieu arrière équivalent de l'unité motrice donnant un rayon extérieur de caisse `rext`
    (dichotomie ; Rext croît avec r0)."""
    lo, hi = 0.0, rext
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if rayons_etablis(unites, m)["Rext"] < rext:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def rayons_poses(v: Vehicule, poses, centre=(0.0, 0.0)) -> dict:
    """Rayons extrêmes (m) des caisses de `poses` vus d'un centre : max des sommets, min des distances polygone."""
    caisses = caisses_locales(v)
    rext, rint = 0.0, float("inf")
    cx, cy = centre
    for pose in poses:
        for P in polygones_pose(v, pose, caisses):
            Q = [(x - cx, y - cy) for (x, y) in P]
            rext = max(rext, max(math.hypot(x, y) for (x, y) in Q))
            rint = min(rint, _dist_point_poly((0.0, 0.0), Q))
    return {"Rext": rext, "Rint": rint}


def rayons_polygone(poly: Polygone, centre=(0.0, 0.0)) -> dict:
    """Rayon extérieur (sommets de l'anneau extérieur) et intérieur (distance au trou le plus proche)."""
    cx, cy = centre
    rext = max(math.hypot(x - cx, y - cy) for (x, y) in poly.exterieur)
    rint = min((_dist_segments((cx, cy), t) for t in poly.trous), default=float("nan"))
    return {"Rext": rext, "Rint": rint}
