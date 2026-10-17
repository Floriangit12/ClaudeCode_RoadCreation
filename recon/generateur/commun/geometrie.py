# -*- coding: utf-8 -*-
"""Ligne de référence d'une route : primitives régulières (droite, arc, clothoïde), point et cap à l'abscisse s,
point décalé (s, t), échantillonnage. Calcul en Python pur (math seulement) : résultat identique à l'octet d'une
exécution à l'autre.

Conventions (MODELE_VOIE_ROUTE_CARREFOUR.md § 1, OpenDRIVE 1.8.1 § 8.3 et § 9) :
- coordonnées Lambert-93 (m) ; cap_deg = cap OpenDRIVE (0° = est, 90° = nord, sens trigonométrique) ;
- t positif à gauche du sens de la ligne de référence ;
- courbure positive = virage à gauche ; clothoïde : courbure linéaire de courbure0 à courbure1 sur la longueur.
"""
from __future__ import annotations

import math

PAS_CLOTHOIDE = 0.05          # pas d'intégration (m) de la clothoïde (Simpson composite)
FLECHE_ECHANTILLON = 0.005    # flèche maximale (m) de la polyligne d'échantillonnage écrite dans le modèle


class Primitive:
    """Primitive régulière : droite (k0 = k1 = 0), arc (k0 = k1 ≠ 0) ou clothoïde (k0 ≠ k1)."""

    def __init__(self, s0: float, longueur: float, x0: float, y0: float, cap: float, k0: float = 0.0,
                 k1: float | None = None):
        self.s0, self.longueur, self.x0, self.y0, self.cap = s0, longueur, x0, y0, cap
        self.k0 = k0
        self.k1 = k0 if k1 is None else k1

    @property
    def type(self) -> str:
        if abs(self.k0) < 1e-12 and abs(self.k1) < 1e-12:
            return "droite"
        if abs(self.k1 - self.k0) < 1e-12:
            return "arc"
        return "clothoide"

    def cap_a(self, u: float) -> float:
        """Cap (rad) à l'abscisse locale u."""
        return self.cap + self.k0 * u + (self.k1 - self.k0) * u * u / (2.0 * self.longueur)

    def point_local(self, u: float) -> tuple[float, float]:
        if self.type == "droite":
            return self.x0 + u * math.cos(self.cap), self.y0 + u * math.sin(self.cap)
        if self.type == "arc":
            k = self.k0
            return (self.x0 + (math.sin(self.cap + k * u) - math.sin(self.cap)) / k,
                    self.y0 - (math.cos(self.cap + k * u) - math.cos(self.cap)) / k)
        # clothoïde : intégration de Simpson à pas fixe (n pair)
        n = max(2, 2 * int(math.ceil(u / (2 * PAS_CLOTHOIDE))))
        h = u / n
        sx = sy = 0.0
        for i in range(n + 1):
            w = 1 if i in (0, n) else (4 if i % 2 else 2)
            th = self.cap_a(i * h)
            sx += w * math.cos(th)
            sy += w * math.sin(th)
        return self.x0 + sx * h / 3.0, self.y0 + sy * h / 3.0

    def courbure_max(self) -> float:
        return max(abs(self.k0), abs(self.k1))

    def vers_schema(self) -> dict:
        d = {"type": self.type, "s0": self.s0, "longueur": self.longueur, "x0": self.x0, "y0": self.y0,
             "cap_deg": math.degrees(self.cap)}
        if self.type != "droite":
            d["courbure0"] = self.k0
            d["courbure1"] = self.k1
        return d


class Trace:
    """Suite de primitives raccordées (position et cap continus)."""

    def __init__(self, x0: float, y0: float, cap_deg: float):
        self.x, self.y, self.cap = x0, y0, math.radians(cap_deg)
        self.primitives: list[Primitive] = []
        self.longueur = 0.0

    def _ajouter(self, longueur: float, k0: float, k1: float) -> None:
        if longueur <= 0:
            raise ValueError("longueur de primitive nulle ou négative")
        p = Primitive(self.longueur, longueur, self.x, self.y, self.cap, k0, k1)
        self.primitives.append(p)
        self.x, self.y = p.point_local(longueur)
        self.cap = p.cap_a(longueur)
        self.longueur += longueur

    def droite(self, longueur: float) -> "Trace":
        self._ajouter(longueur, 0.0, 0.0)
        return self

    def arc(self, rayon: float, longueur: float, gauche: bool) -> "Trace":
        k = (1.0 if gauche else -1.0) / rayon
        self._ajouter(longueur, k, k)
        return self

    def clothoide(self, longueur: float, k0: float, k1: float) -> "Trace":
        self._ajouter(longueur, k0, k1)
        return self

    def courbure_fin(self) -> float:
        return self.primitives[-1].k1 if self.primitives else 0.0

    # ------------------------------------------------------------------ requêtes
    def _primitive(self, s: float) -> Primitive:
        for p in self.primitives:
            if s <= p.s0 + p.longueur + 1e-9:
                return p
        return self.primitives[-1]

    def point(self, s: float) -> tuple[float, float, float]:
        """(x, y, cap rad) à l'abscisse s ∈ [0, L]."""
        s = min(max(s, 0.0), self.longueur)
        p = self._primitive(s)
        u = s - p.s0
        x, y = p.point_local(u)
        return x, y, p.cap_a(u)

    def point_st(self, s: float, t: float) -> tuple[float, float]:
        x, y, c = self.point(s)
        return x - t * math.sin(c), y + t * math.cos(c)

    def abscisses(self, fleche: float = FLECHE_ECHANTILLON, pas_max: float = 5.0) -> list[float]:
        """Abscisses d'échantillonnage : flèche ≤ `fleche` sur les courbes, pas ≤ pas_max, bornes des primitives."""
        out = []
        for p in self.primitives:
            k = p.courbure_max()
            pas = pas_max if k < 1e-12 else min(pas_max, math.sqrt(8.0 * fleche / k))
            n = max(1, int(math.ceil(p.longueur / pas - 1e-9)))
            out += [p.s0 + p.longueur * i / n for i in range(n)]
        out.append(self.longueur)
        return out

    def polyligne(self, t: float = 0.0, fleche: float = FLECHE_ECHANTILLON) -> list[tuple[float, float]]:
        return [self.point_st(s, t) for s in self.abscisses(fleche)]


def trace_polyligne(points: list[tuple[float, float]]) -> Trace:
    """Trace en droites successives par des sommets donnés (cassures non raccordées : à éviter si la route tourne)."""
    if len(points) < 2:
        raise ValueError("une polyligne a au moins deux sommets")
    (xa, ya), (xb, yb) = points[0], points[1]
    tr = Trace(xa, ya, math.degrees(math.atan2(yb - ya, xb - xa)))
    for (xa, ya), (xb, yb) in zip(points, points[1:]):
        lg = math.hypot(xb - xa, yb - ya)
        if lg < 1e-6:
            continue
        tr.cap = math.atan2(yb - ya, xb - xa)
        tr.x, tr.y = xa, ya
        tr.droite(lg)
    return tr


def angle_cassure_max_deg(points: list[tuple[float, float]]) -> float:
    """Plus grande déviation angulaire (°) aux sommets intérieurs d'une polyligne."""
    m = 0.0
    for a, b, c in zip(points, points[1:], points[2:]):
        c1 = math.atan2(b[1] - a[1], b[0] - a[0])
        c2 = math.atan2(c[1] - b[1], c[0] - b[0])
        d = (c2 - c1 + math.pi) % (2 * math.pi) - math.pi
        m = max(m, abs(math.degrees(d)))
    return m
