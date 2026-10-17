# -*- coding: utf-8 -*-
"""Géométrie analytique de référence du lot L1 (contrôles indépendants des HDA rg::*).

Ce module ne partage aucun code avec les HDA (VEX) ni avec le compilateur de description : il relit le modèle
`modele_voie/0.1` et recalcule en double précision, par d'autres méthodes que le VEX :
- la ligne de référence (droite et arc en forme fermée ; clothoïde par quadrature adaptative de Gauss-Kronrod,
  `scipy.integrate.quad`, tolérance 1e-13 m, alors que le VEX intègre par Gauss-Legendre composite à 8 nœuds) ;
- les lois de largeur (`points` linéaire / palier, `poly3`, nombre) et la position t de chaque limite (cumul des
  largeurs depuis la limite de référence du profil, décalage `reference.decalage_m`) ;
- la loi verticale de la chaussée (plateau trapézoïdal, dos-d'âne circulaire).

Conventions du modèle (meta.conventions) : s absolu le long de la ligne de référence ; t positif à gauche ; cap
OpenDRIVE (0° = est, sens trigonométrique) ; coordonnées locales = Lambert-93 − repere.origine_l93.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import integrate

TOL_QUAD = 1e-12


# ------------------------------------------------------------------------------------------------ ligne de référence
class Primitive:
    def __init__(self, p: dict, origine):
        self.type = p["type"]
        if self.type not in ("droite", "arc", "clothoide"):
            raise ValueError(f"primitive {self.type} non prise en charge par le contrôle L1")
        self.s0 = float(p["s0"])
        self.L = float(p["longueur"])
        self.x0 = float(p["x0"]) - origine[0]
        self.y0 = float(p["y0"]) - origine[1]
        self.cap = math.radians(float(p["cap_deg"]))
        self.k0 = float(p.get("courbure0", 0.0))
        self.k1 = float(p.get("courbure1", self.k0))
        if self.type == "droite":
            self.k0 = self.k1 = 0.0
        if self.type == "arc":
            self.k1 = self.k0
        self.c = (self.k1 - self.k0) / self.L if self.L > 0 else 0.0

    def theta(self, u):
        return self.cap + self.k0 * u + 0.5 * self.c * u * u

    def kappa(self, u):
        return self.k0 + self.c * u

    def point(self, u: float):
        """(x, y) local à l'abscisse locale u (scalaire)."""
        if self.type == "droite":
            return self.x0 + u * math.cos(self.cap), self.y0 + u * math.sin(self.cap)
        if self.type == "arc":
            k = self.k0
            return (self.x0 + (math.sin(self.cap + k * u) - math.sin(self.cap)) / k,
                    self.y0 - (math.cos(self.cap + k * u) - math.cos(self.cap)) / k)
        if u == 0.0:
            return self.x0, self.y0
        ix = integrate.quad(lambda v: math.cos(self.theta(v)), 0.0, u, epsabs=TOL_QUAD, epsrel=1e-12, limit=200)[0]
        iy = integrate.quad(lambda v: math.sin(self.theta(v)), 0.0, u, epsabs=TOL_QUAD, epsrel=1e-12, limit=200)[0]
        return self.x0 + ix, self.y0 + iy


class Reference:
    """Ligne de référence d'une route : géométrie régulière, sinon polyligne (droites par sommets)."""

    def __init__(self, route: dict, origine):
        lr = route["ligne_reference"]
        self.L = float(lr.get("longueur_m") or 0.0)
        gr = lr.get("geometrie_reguliere") or []
        self.prims = [Primitive(p, origine) for p in gr]
        self.poly = None
        if not self.prims:
            pts = np.array([[q[0] - origine[0], q[1] - origine[1]] for q in lr["geometrie"]], float)
            d = np.hypot(*np.diff(pts, axis=0).T)
            keep = np.concatenate([[True], d > 1e-9])
            pts = pts[keep]
            self.poly = pts
            self.poly_s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
            if not self.L:
                self.L = float(self.poly_s[-1])
        elif not self.L:
            self.L = sum(p.L for p in self.prims)

    def _prim(self, s):
        """Primitive qui porte s : la dernière dont s0 ≤ s (à un raccord, la suivante, dont le départ est celui du
        modèle ; même convention que rg_indice_primitive en VEX)."""
        k = 0
        for i, p in enumerate(self.prims):
            if p.s0 <= s + 1e-9:
                k = i
        return self.prims[k]

    def eval(self, s: float):
        """(x, y, cap rad, courbure) à l'abscisse s."""
        if self.poly is not None:
            i = int(np.clip(np.searchsorted(self.poly_s, s, side="right") - 1, 0, len(self.poly) - 2))
            a, b = self.poly[i], self.poly[i + 1]
            u = (s - self.poly_s[i]) / (self.poly_s[i + 1] - self.poly_s[i])
            th = math.atan2(b[1] - a[1], b[0] - a[0])
            return a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]), th, 0.0
        p = self._prim(s)
        u = min(max(s - p.s0, 0.0), p.L)
        x, y = p.point(u)
        return x, y, p.theta(u), p.kappa(u)

    def point_st(self, s: float, t: float):
        x, y, th, _ = self.eval(s)
        return x - t * math.sin(th), y + t * math.cos(th)

    def bornes_primitives(self):
        if self.poly is not None:
            return [float(v) for v in self.poly_s]
        return sorted({p.s0 for p in self.prims} | {self.prims[-1].s0 + self.prims[-1].L})

    def offset_polyligne(self, s: float, t: float):
        """Polyligne : position décalée en onglet (intersection des décalés des deux segments) aux sommets."""
        if self.poly is None:
            return self.point_st(s, t)
        k = np.where(np.abs(self.poly_s - s) < 2e-5)[0]
        if len(k) and 0 < k[0] < len(self.poly) - 1:
            i = int(k[0])
            a, b, c = self.poly[i - 1], self.poly[i], self.poly[i + 1]
            d1 = (b - a) / np.linalg.norm(b - a)
            d2 = (c - b) / np.linalg.norm(c - b)
            n1 = np.array([-d1[1], d1[0]])
            n2 = np.array([-d2[1], d2[0]])
            m = n1 + n2
            m = m / np.linalg.norm(m)
            cos_half = float(np.dot(m, n1))
            q = b + t * m / cos_half
            return float(q[0]), float(q[1])
        x, y, th, _ = self.eval(s)
        return x - t * math.sin(th), y + t * math.cos(th)


# ------------------------------------------------------------------------------------------------ lois de s
def loi(v, s: float) -> float:
    """Loi de s du schéma (loi_s) : nombre, {type: points, interpolation: lineaire | palier}, {type: poly3}."""
    if isinstance(v, (int, float)):
        return float(v)
    if v["type"] == "points":
        pts = v["points"]
        interp = v.get("interpolation", "lineaire")
        if interp not in ("lineaire", "palier"):
            raise ValueError(f"interpolation {interp} non définie (contrôle L1)")
        if s <= pts[0][0]:
            return float(pts[0][1])
        if s >= pts[-1][0]:
            return float(pts[-1][1])
        for (sa, va), (sb, vb) in zip(pts, pts[1:]):
            if sa <= s <= sb:
                if interp == "palier":
                    return float(vb if s >= sb else va)
                return float(va + (vb - va) * (s - sa) / (sb - sa))
    if v["type"] == "poly3":
        m = [x for x in v["morceaux"] if x["s0"] <= s + 1e-12] or [v["morceaux"][0]]
        x = m[-1]
        ds = s - x["s0"]
        return x["a"] + x.get("b", 0.0) * ds + x.get("c", 0.0) * ds ** 2 + x.get("d", 0.0) * ds ** 3
    raise ValueError(f"loi inconnue {v}")


def breakpoints_loi(v):
    if isinstance(v, dict) and v.get("type") == "points":
        return [float(p[0]) for p in v["points"]]
    if isinstance(v, dict) and v.get("type") == "poly3":
        return [float(m["s0"]) for m in v["morceaux"]]
    return []


def t_limites(profil: dict, s: float):
    """t (m, + gauche) des n + 1 limites du profil à l'abscisse s."""
    w = [loi(b["largeur"], s) for b in profil["bandes"]]
    r = int(profil["reference"]["limite"])
    t = [0.0] * (len(w) + 1)
    t[r] = -float(profil["reference"].get("decalage_m", 0.0))
    for i in range(r - 1, -1, -1):
        t[i] = t[i + 1] + w[i]
    for i in range(r + 1, len(w) + 1):
        t[i] = t[i - 1] - w[i - 1]
    return t


# ------------------------------------------------------------------------------------------------ loi verticale
def dz_chaussee(objets: list, route_id: str, s: float, rampe_pct: float) -> float:
    """Surélévation de la chaussée (m) : plateau trapézoïdal (rampes à rampe_pct, DEF-034), dos-d'âne circulaire
    (segment de cercle de corde longueur_m et de flèche hauteur_m, RF-MA-RAL-001)."""
    dz = 0.0
    for o in objets:
        if (o.get("rattachement") or {}).get("route") != route_id or o.get("type") not in ("plateau", "dos_d_ane"):
            continue
        sc = float(o["rattachement"]["s"])
        lg = float(o["dimensions"]["longueur_m"])
        h = float(o["dimensions"]["hauteur_m"])
        u = s - sc
        if abs(u) >= lg / 2:
            continue
        if o["type"] == "plateau":
            rampe = h / (rampe_pct / 100.0)
            dz += h * min(1.0, (lg / 2 - abs(u)) / rampe)
        else:
            R = (lg * lg / 4.0 + h * h) / (2.0 * h)
            dz += math.sqrt(R * R - u * u) - (R - h)
    return dz


def bornes_verticales(objets: list, route_id: str, rampe_pct: float):
    out = []
    for o in objets:
        if (o.get("rattachement") or {}).get("route") != route_id or o.get("type") not in ("plateau", "dos_d_ane"):
            continue
        sc = float(o["rattachement"]["s"])
        lg = float(o["dimensions"]["longueur_m"])
        h = float(o["dimensions"]["hauteur_m"])
        out += [sc - lg / 2, sc + lg / 2]
        if o["type"] == "dos_d_ane":
            out.append(sc)
        if o["type"] == "plateau":
            rampe = h / (rampe_pct / 100.0)
            out += [sc - lg / 2 + rampe, sc + lg / 2 - rampe]
    return out


# ------------------------------------------------------------------------------------------------ distances
def distance_point_segment(p, a, b) -> float:
    p, a, b = np.asarray(p, float), np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    n = float(np.dot(ab, ab))
    if n < 1e-24:
        return float(np.linalg.norm(p - a))
    u = min(1.0, max(0.0, float(np.dot(p - a, ab)) / n))
    return float(np.linalg.norm(p - (a + u * ab)))


def distance_point_courbe(m, f, sa: float, sb: float, n0: int = 24) -> float:
    """Distance de m à la courbe analytique f(s), s ∈ [sa, sb] : grille puis section dorée autour du minimum."""
    ss = np.linspace(sa, sb, n0 + 1)
    d = [math.dist(m, f(x)) for x in ss]
    k = int(np.argmin(d))
    lo, hi = ss[max(k - 1, 0)], ss[min(k + 1, n0)]
    g = (math.sqrt(5) - 1) / 2
    c, e = hi - g * (hi - lo), lo + g * (hi - lo)
    fc, fe = math.dist(m, f(c)), math.dist(m, f(e))
    for _ in range(60):
        if fc < fe:
            hi, e, fe = e, c, fc
            c = hi - g * (hi - lo)
            fc = math.dist(m, f(c))
        else:
            lo, c, fc = c, e, fe
            e = lo + g * (hi - lo)
            fe = math.dist(m, f(e))
        if hi - lo < 1e-10:
            break
    return min(min(d), fc, fe)
