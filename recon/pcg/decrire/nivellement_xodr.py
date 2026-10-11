"""Modèle de Z de la chaussée tiré d'OpenDRIVE (TQ-SOL-004) : elevation + superelevation + shape
(lateralProfile, ASAM OpenDRIVE 1.7), évalué en (s, t) par projection sur la ligne de référence.

z(s, t) = elevation(s) + t·tan(superelevation(s)) + shape(s, t)
- superelevation : angle de roulis (rad) autour de la ligne de référence, positif = chute vers la droite
  (t < 0) ;
- shape : pour chaque abscisse s_i, polynômes cubiques en dt = t − t_j valables de t_j au t suivant ;
  interpolation linéaire en s entre deux abscisses s_i (OpenDRIVE 1.7 § 8.4.3) ;
- routes de liaison de la jonction (junction ≠ -1) : non utilisées pour le Z du sol (TQ-SOL-014).
Repère : le .xodr est déjà en repère local (header offset = O) ; z local = NGF − 216,30.
"""
import bisect
import functools
import math

import numpy as np

import xodr_echantillonne as X


def _cubiques(elements):
    return sorted((float(e.get("s")), float(e.get("a")), float(e.get("b")), float(e.get("c")), float(e.get("d")))
                  for e in elements)


class Cubiques:
    """Fonction cubique par morceaux [(s_debut, a, b, c, d)], évaluation vectorisée."""

    def __init__(self, m):
        self.m = np.array(m, dtype=np.float64).reshape(-1, 5)

    def __call__(self, s, defaut=0.0):
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        if len(self.m) == 0:
            return np.full(len(s), defaut)
        k = np.clip(np.searchsorted(self.m[:, 0], s + 1e-9, side="right") - 1, 0, len(self.m) - 1)
        s0, a, b, c, d = self.m[k].T
        ds = s - s0
        return a + b * ds + c * ds * ds + d * ds ** 3


class ModeleRoute:
    """Profil en long et en travers d'une route OpenDRIVE (hors jonction)."""

    def __init__(self, route, pas=0.05):
        self.route = route
        self.id = route.id
        lp = route.xml.find("lateralProfile")
        self.sup = Cubiques(_cubiques(lp.findall("superelevation")) if lp is not None else [])
        self.elev = Cubiques(route.elevation_.m)
        formes = {}
        if lp is not None:
            for e in lp.findall("shape"):
                formes.setdefault(float(e.get("s")), []).append(
                    (float(e.get("t")), float(e.get("a")), float(e.get("b")), float(e.get("c")), float(e.get("d"))))
        self.formes_s = sorted(formes)
        self.formes = [sorted(formes[s]) for s in self.formes_s]
        n = max(2, int(math.ceil(route.longueur / pas)) + 1)
        self.s_ref = np.linspace(0.0, route.longueur, n)
        x, y, h = route.reference(self.s_ref)
        self.xy_ref = np.c_[x, y]
        self.hdg = h

    def _forme_a(self, k, t):
        polys = np.array(self.formes[k], dtype=np.float64)
        j = np.clip(np.searchsorted(polys[:, 0], t, side="right") - 1, 0, len(polys) - 1)
        t0, a, b, c, d = polys[j].T
        dt = t - t0
        return a + b * dt + c * dt * dt + d * dt ** 3

    def forme(self, s, t):
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        t = np.atleast_1d(np.asarray(t, dtype=np.float64))
        if not self.formes_s:
            return np.zeros(len(s))
        out = np.empty(len(s))
        fs = self.formes_s
        idx = np.clip(np.searchsorted(fs, s, side="right") - 1, 0, len(fs) - 1)
        for k in np.unique(idx):
            m = idx == k
            h0 = self._forme_a(k, t[m])
            if k + 1 < len(fs):
                h1 = self._forme_a(k + 1, t[m])
                w = np.clip((s[m] - fs[k]) / (fs[k + 1] - fs[k]), 0.0, 1.0)
                out[m] = h0 * (1 - w) + h1 * w
            else:
                out[m] = h0
        return out

    def z(self, s, t):
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        t = np.atleast_1d(np.asarray(t, dtype=np.float64))
        return self.elev(s) + t * np.tan(self.sup(s, 0.0)) + self.forme(s, t)

    def st(self, Q):
        """(s, t) des points locaux Q par projection sur la ligne de référence échantillonnée."""
        from commun import projeter
        s, d, c = projeter(self.xy_ref, Q)
        return s, d * c

    def z_xy(self, Q):
        s, t = self.st(Q)
        return self.z(s, t), s, t

    def z_xy_rapide(self, Q, pas=0.5):
        """Comme z_xy, mais (s, t) calculés sur une grille de `pas` m puis interpolés (bilinéaire) :
        (s, t) varient lentement loin du centre de courbure (écart < 1 mm pour les rayons du site)."""
        Q = np.asarray(Q, dtype=np.float64)
        x0, y0 = np.floor(Q.min(axis=0) / pas) * pas - pas
        x1, y1 = np.ceil(Q.max(axis=0) / pas) * pas + pas
        gx = np.arange(x0, x1 + pas / 2, pas)
        gy = np.arange(y0, y1 + pas / 2, pas)
        GX, GY = np.meshgrid(gx, gy)
        fi = (Q[:, 0] - x0) / pas
        fj = (Q[:, 1] - y0) / pas
        i0 = np.clip(np.floor(fi).astype(int), 0, len(gx) - 2)
        j0 = np.clip(np.floor(fj).astype(int), 0, len(gy) - 2)
        utile = np.zeros(GX.shape, bool)
        for dj in (0, 1):
            for di in (0, 1):
                utile[j0 + dj, i0 + di] = True
        sg = np.full(GX.shape, np.nan)
        tg = np.full(GX.shape, np.nan)
        s_, t_ = self.st(np.c_[GX[utile], GY[utile]])
        sg[utile], tg[utile] = s_, t_
        ti, tj = fi - i0, fj - j0
        def bil(g):
            return ((g[j0, i0] * (1 - ti) + g[j0, i0 + 1] * ti) * (1 - tj)
                    + (g[j0 + 1, i0] * (1 - ti) + g[j0 + 1, i0 + 1] * ti) * tj)
        s, t = bil(sg), bil(tg)
        return self.z(s, t), s, t


@functools.lru_cache(maxsize=None)
def modeles():
    """{id route: ModeleRoute} des routes hors jonction."""
    res = X.lire_xodr()
    return {rid: ModeleRoute(r) for rid, r in sorted(res.items(), key=lambda kv: int(kv[0])) if r.jonction == "-1"}


@functools.lru_cache(maxsize=None)
def modeles_liaisons():
    """{id route: ModeleRoute} des routes de liaison de la jonction (axe de Verdun : tout droit)."""
    res = X.lire_xodr()
    return {rid: ModeleRoute(r) for rid, r in sorted(res.items(), key=lambda kv: int(kv[0])) if r.jonction != "-1"}
