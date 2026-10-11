"""Géométrie dérivée des bordures pour la partition du sol (repère local, numpy) : arête arrière
(arête avant décalée de la largeur de base du profil, bordures.json), emprise (bande) de bordure,
abscisses et décalages. Une seule définition, partagée par surfaces, rampes et nivellement.
"""
import functools
import math

import numpy as np

from commun import SPECS, abscisses, dedoublonner_sommets, distance_segments, lire_json, normale_gauche, point_a

LARGEUR_DEFAUT = 0.15
TRANSITION_LARGEUR = 0.30      # passage d'une largeur de profil à l'autre (m)


@functools.lru_cache(maxsize=None)
def _spec():
    return lire_json(SPECS / "bordures.json")


def largeur_base(profil):
    """Largeur de base du profil (bordures.json : base, sinon largeur ; 0,15 m par défaut ;
    MURET_TALUS 0,20 m)."""
    if profil == "MURET_TALUS":
        return 0.20
    p = _spec()["profils"].get(profil, {})
    return float(p.get("base") or p.get("largeur") or LARGEUR_DEFAUT)


def largeur_le_long(intervalles, s):
    """Largeur de base aux abscisses s, transitions linéaires de 0,30 m centrées sur les changements."""
    s = np.atleast_1d(np.asarray(s, dtype=np.float64))
    bornes = [(it["s0"], it["s1"], largeur_base(it["profil"])) for it in intervalles]
    w = np.empty(len(s))
    for k, x in enumerate(s):
        w[k] = bornes[-1][2]
        for a, b, l in bornes:
            if a - 1e-9 <= x <= b + 1e-9:
                w[k] = l
                break
    # adoucissement des marches de largeur
    for (a0, b0, l0), (a1, b1, l1) in zip(bornes[:-1], bornes[1:]):
        if abs(l0 - l1) < 1e-6:
            continue
        c = b0
        m = np.abs(s - c) < TRANSITION_LARGEUR / 2
        t = (s[m] - (c - TRANSITION_LARGEUR / 2)) / TRANSITION_LARGEUR
        w[m] = l0 + (l1 - l0) * t
    return w


def decaler_variable(P, d, pas=0.25):
    """Polyligne décalée à gauche de d(s) (fonction des abscisses), sommets d'origine + pas régulier ;
    boucles locales (coins rentrants) supprimées."""
    P = dedoublonner_sommets(np.asarray(P, dtype=np.float64)[:, :2])
    S = abscisses(P)
    L = float(S[-1])
    n = max(1, int(math.ceil(L / pas)))
    s = np.unique(np.r_[S, np.linspace(0.0, L, n + 1)])
    s = s[np.r_[True, np.diff(s) > 1e-4]]
    q, _ = point_a(P, s)
    # tangente lissée aux sommets (bissectrice des segments voisins)
    seg = np.diff(q, axis=0)
    tg = seg / np.maximum(np.hypot(*seg.T), 1e-12)[:, None]
    tv = np.vstack([tg[:1], tg[:-1] + tg[1:], tg[-1:]])
    tv /= np.maximum(np.hypot(*tv.T), 1e-12)[:, None]
    nv = normale_gauche(tv)
    tt = np.vstack([tg[:1], tg, tg[-1:]])
    cosa = np.maximum(np.einsum("ij,ij->i", normale_gauche(tt[:-1]), nv), 0.5)
    dd = np.asarray(d(s), dtype=np.float64)
    Q = q + nv * (dd / cosa)[:, None]
    return sans_boucles(Q), s


def sans_boucles(Q, fenetre=60):
    """Supprime les petites boucles d'une polyligne (segments non voisins qui se coupent à moins de
    `fenetre` sommets d'écart) : la boucle est remplacée par le point d'intersection."""
    Q = np.asarray(Q, dtype=np.float64)
    i = 0
    while i < len(Q) - 3:
        p, r = Q[i], Q[i + 1] - Q[i]
        j1 = min(len(Q) - 1, i + fenetre)
        A, B = Q[i + 2:j1], Q[i + 3:j1 + 1]
        if len(A) == 0:
            i += 1
            continue
        s_ = B - A
        den = r[0] * s_[:, 1] - r[1] * s_[:, 0]
        ap = A - p
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (ap[:, 0] * s_[:, 1] - ap[:, 1] * s_[:, 0]) / den
            u = (ap[:, 0] * r[1] - ap[:, 1] * r[0]) / den
        m = (np.abs(den) > 1e-12) & (t > 0) & (t < 1) & (u >= 0) & (u <= 1)
        if m.any():
            k = int(np.nonzero(m)[0][-1])
            x = p + r * t[k]
            Q = np.vstack([Q[:i + 1], x[None], Q[i + 2 + k + 1:]])
        i += 1
    return Q


def arete_arriere(P, intervalles):
    """Arête arrière (côté haut, à gauche) : avant décalée de la largeur de base du profil."""
    Q, s = decaler_variable(P, lambda s: largeur_le_long(intervalles, s))
    return Q


def emprise(P, Q):
    """Anneau de l'emprise d'une bordure : arête avant + arête arrière renversée."""
    r = np.vstack([np.asarray(P)[:, :2], np.asarray(Q)[::-1, :2]])
    return r


def projeter_sur(P, Q):
    """(s, distance signée positive à gauche) des points Q sur la polyligne P."""
    from commun import projeter
    s, d, c = projeter(P, Q)
    return s, d * c


def contact(Q, lignes, dmax):
    """Distance de chaque point Q à l'ensemble de polylignes `lignes` ([(N, 2)])."""
    if not lignes:
        return np.full(len(Q), np.inf)
    A = np.vstack([l[:-1] for l in lignes])
    B = np.vstack([l[1:] for l in lignes])
    d, _, _ = distance_segments(Q, A, B)
    return d
