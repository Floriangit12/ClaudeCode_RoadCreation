"""Contrôle latéral du prototype (conception § 7.3, § 8.3) : suivi de trajectoire à point de visée (pure
pursuit) et bicyclette cinématique, appliqués après coup aux trajectoires longitudinales du scénario de la
courbe (la vitesse en courbe ne dépend pas de la commande latérale dans le prototype).

  β = atan(l_r tan δ / L) ; ẋ = v cos(ψ + β) ; ẏ = v sin(ψ + β) ; ψ̇ = v cos β tan δ / L   (Samak 2020, volet 03)
  δ = atan(2 L sin α / l_v), borné à δ_max (angle « bicyclette » des VP de référence, volet 01 § 3.3)

Conventions non sourcées (hypothèse H-12) : distance de visée l_v = 2 m + 1 s × v ; l_r = 0,6 L (conception
§ 8.3). Ces valeurs donnent un suivi stable ; elles ne prétendent pas reproduire la commande humaine.
"""
from __future__ import annotations

import math

import numpy as np


def chemin_courbe(s_debut: float, R: float, angle_rad: float, longueur_aval: float, pas: float = 0.25):
    """Polyligne droite (axe x) - arc de rayon R à gauche - droite, échantillonnée tous les `pas` mètres."""
    s1 = np.arange(0.0, s_debut, pas)
    p1 = np.c_[s1, np.zeros_like(s1)]
    th = np.arange(0.0, angle_rad, pas / R)
    p2 = np.c_[s_debut + R * np.sin(th), R - R * np.cos(th)]
    x_e, y_e = s_debut + R * math.sin(angle_rad), R - R * math.cos(angle_rad)
    s3 = np.arange(0.0, longueur_aval, pas)
    p3 = np.c_[x_e + s3 * math.cos(angle_rad), y_e + s3 * math.sin(angle_rad)]
    return np.vstack([p1, p2, p3])


def pure_pursuit(chemin: np.ndarray, v_t: np.ndarray, dt: float, L: np.ndarray, delta_max: np.ndarray,
                 l_v0: float = 2.0, t_v: float = 1.0, part_lr: float = 0.6):
    """v_t : vitesses (n_pas, n_vehicules) le long de la trajectoire (NaN hors réseau).
    Renvoie un dictionnaire de séries (n_pas, n) : écart latéral, braquage, vitesse de lacet, a_y."""
    n_pas, n = v_t.shape
    x = np.zeros(n)
    y = np.zeros(n)
    psi = np.zeros(n)
    idx = np.zeros(n, int)
    lr = part_lr * L
    seg = np.diff(chemin, axis=0)
    out = {k: np.full((n_pas, n), np.nan, np.float32) for k in ("ecart", "delta", "lacet", "ay")}
    fen = np.arange(-8, 40)
    for k in range(n_pas):
        v = v_t[k]
        ok = np.isfinite(v)
        if not ok.any():
            continue
        v = np.where(ok, v, 0.0)
        cand = np.clip(idx[:, None] + fen[None, :], 0, len(chemin) - 1)
        d2 = (chemin[cand, 0] - x[:, None]) ** 2 + (chemin[cand, 1] - y[:, None]) ** 2
        idx = cand[np.arange(n), np.argmin(d2, axis=1)]
        # écart latéral signé (gauche positif) par rapport au segment le plus proche
        j = np.minimum(idx, len(seg) - 1)
        t_hat = seg[j] / np.linalg.norm(seg[j], axis=1)[:, None]
        rel = np.c_[x - chemin[j, 0], y - chemin[j, 1]]
        ecart = t_hat[:, 0] * rel[:, 1] - t_hat[:, 1] * rel[:, 0]
        l_v = l_v0 + t_v * v
        cible = np.minimum(idx + np.round(l_v / 0.25).astype(int), len(chemin) - 1)
        ang = np.arctan2(chemin[cible, 1] - y, chemin[cible, 0] - x) - psi
        ang = (ang + np.pi) % (2 * np.pi) - np.pi
        delta = np.clip(np.arctan(2.0 * L * np.sin(ang) / np.maximum(l_v, 0.5)), -delta_max, delta_max)
        beta = np.arctan(lr * np.tan(delta) / L)
        lacet = v * np.cos(beta) * np.tan(delta) / L
        x = x + np.where(ok, v * np.cos(psi + beta) * dt, 0.0)
        y = y + np.where(ok, v * np.sin(psi + beta) * dt, 0.0)
        psi = psi + np.where(ok, lacet * dt, 0.0)
        for nom, val in (("ecart", ecart), ("delta", delta), ("lacet", lacet), ("ay", v * lacet)):
            out[nom][k] = np.where(ok, val, np.nan)
    return out
