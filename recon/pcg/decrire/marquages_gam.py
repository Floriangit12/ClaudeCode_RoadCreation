"""Levé GAM des marquages (SOL_SIGNALISATION_HORIZONTALE, 409 lignes) : lectures communes de la famille
marquages.

- paires de bords : deux lignes ouvertes quasi parallèles (≤ 10°) à 0,06-0,25 m l'une de l'autre sur au
  moins la moitié de la plus courte = les deux bords levés d'une même marque -> axe = ligne médiane, largeur
  = écartement (paires()) ;
- axes_leves(refs) : axes des lignes référencées (médiane des paires, sinon la ligne elle-même) ;
- tirets_leves(P, ...) : lignes ouvertes droites de 0,3 à 6,5 m quasi parallèles à un axe P à moins de
  0,30 m = tirets levés un à un (bords appariés fusionnés), en abscisses σ de P ;
- orphelines(refs_v1, points_v2) : lignes ouvertes non rattachées au v1 et à plus de 0,5 m de toute marque.
"""
import functools
import math

import numpy as np

import marquages_commun as M
from commun import abscisses, densifier, point_a, projeter

ECART_PAIRE = (0.06, 0.25)
PARALLELE = math.cos(math.radians(10.0))


def ouverte(P):
    return not (len(P) > 3 and np.allclose(P[0], P[-1]))


@functools.lru_cache(maxsize=None)
def paires():
    """{k: (j, écartement médian, fraction recouverte)} : partenaire de bord de chaque ligne appariée."""
    G = M.gam_lin()
    ouv = [k for k, P in enumerate(G) if ouverte(P) and abscisses(P)[-1] > 0.3]
    bb = {k: (*G[k].min(axis=0) - 0.5, *G[k].max(axis=0) + 0.5) for k in ouv}
    cand = {}
    for a in ouv:
        Q, _ = densifier(G[a], 0.10)
        for b in ouv:
            if b == a:
                continue
            A, B = bb[a], bb[b]
            if A[2] < B[0] or B[2] < A[0] or A[3] < B[1] or B[3] < A[1]:
                continue
            sb, d, _ = projeter(G[b], Q)
            dedans = (sb > 0.01) & (sb < abscisses(G[b])[-1] - 0.01)
            if dedans.sum() < 3:
                continue
            dd = d[dedans]
            e = float(np.median(dd))
            if not (ECART_PAIRE[0] <= e <= ECART_PAIRE[1]) or float(np.percentile(dd, 90) - np.percentile(dd, 10)) > 0.04:
                continue
            ua = G[a][-1] - G[a][0]
            ub = G[b][-1] - G[b][0]
            if abs(ua @ ub) / max(np.hypot(*ua) * np.hypot(*ub), 1e-9) < PARALLELE:
                continue
            frac = float(dedans.mean())
            if frac < 0.5:
                continue
            if a not in cand or (frac, -e) > (cand[a][2], -cand[a][1]):
                cand[a] = (b, round(e, 3), round(frac, 3))
    return {k: v for k, v in cand.items() if v[0] in cand}


def mediane(a, b):
    """Ligne médiane de deux bords (échantillons de a au pas 0,10 m projetés sur b)."""
    G = M.gam_lin()
    Q, _ = densifier(G[a], 0.10)
    sb, d, _ = projeter(G[b], Q)
    dedans = (sb > 0.01) & (sb < abscisses(G[b])[-1] - 0.01)
    Pb, _ = point_a(G[b], sb[dedans])
    return M.dedoublonner(0.5 * (Q[dedans] + Pb))


def axes_leves(refs):
    """[(axe, largeur levée ou None, (k, ...))] des lignes GAM `refs` : médiane des paires de bords (largeur =
    écartement), sinon la ligne elle-même ; triés par indice."""
    G = M.gam_lin()
    pp = paires()
    out, vus = [], set()
    for k in sorted(set(refs)):
        if k in vus or not ouverte(G[k]):
            continue
        if k in pp:
            j, e, _ = pp[k]
            vus |= {k, j}
            a, b = (k, j) if abscisses(G[k])[-1] >= abscisses(G[j])[-1] else (j, k)
            C = mediane(a, b)
            if len(C) >= 2:
                out.append((C, e, (min(k, j), max(k, j))))
                continue
        vus.add(k)
        out.append((G[k], None, (k,)))
    return out


@functools.lru_cache(maxsize=None)
def morceaux_chaines():
    """Lignes ouvertes dont une extrémité prolonge (< 5 cm, déviation < 30°) une autre ligne ouverte : morceaux
    d'une polyligne plus longue (pas des tirets isolés)."""
    G = M.gam_lin()
    ouv = [k for k, P in enumerate(G) if ouverte(P) and abscisses(P)[-1] > 1e-3]
    bouts = []
    for k in ouv:
        P = G[k]
        for e, d in ((P[0], P[0] - P[1]), (P[-1], P[-1] - P[-2])):
            bouts.append((k, e, d / max(np.hypot(*d), 1e-12)))
    out = set()
    for i, (k, e, d) in enumerate(bouts):
        for j, (k2, e2, d2) in enumerate(bouts):
            if k2 == k or np.hypot(*(e - e2)) > 0.05:
                continue
            if float(d @ -d2) > math.cos(math.radians(30.0)):
                out |= {k, k2}
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def _contigues():
    """{k: {j}} : lignes ouvertes qui se prolongent bout à bout (< 5 cm, déviation < 30°)."""
    G = M.gam_lin()
    ouv = [k for k, P in enumerate(G) if ouverte(P) and abscisses(P)[-1] > 1e-3]
    bouts = []
    for k in ouv:
        P = G[k]
        for e, d in ((P[0], P[0] - P[1]), (P[-1], P[-1] - P[-2])):
            bouts.append((k, e, d / max(np.hypot(*d), 1e-12)))
    out = {k: set() for k in ouv}
    for k, e, d in bouts:
        for k2, e2, d2 in bouts:
            if k2 != k and np.hypot(*(e - e2)) <= 0.05 and float(d @ -d2) > math.cos(math.radians(30.0)):
                out[k].add(k2)
    return out


def chaine(refs, permises):
    """Lignes GAM jointives (bout à bout, partenaires de paire compris) atteintes depuis `refs` en ne traversant que
    des lignes de `permises` (non rattachées au v1) : frozenset."""
    cont = _contigues()
    pp = paires()
    vus = set(refs)
    pile = sorted(refs)
    while pile:
        k = pile.pop()
        voisins = set(cont.get(k, ())) | ({pp[k][0]} if k in pp else set())
        for j in sorted(voisins):
            if j not in vus and (j in permises or j in refs):
                vus.add(j)
                pile.append(j)
    return frozenset(vus)


def tirets_leves(P, exclure=(), lat_max=0.30, ang_max=12.0, inclure=()):
    """Tirets levés un à un le long de l'axe local P : [(σ0, σ1, t médian, (k, ...))] triés ; les deux bords
    d'un même tiret (paire) donnent un seul tiret (milieu) ; les morceaux de polylignes chaînées sont exclus, sauf
    ceux de `inclure` (ligne GAM courte qui porte à elle seule des tirets v1 synthétiques)."""
    G = M.gam_lin()
    exclure = set(exclure) | (morceaux_chaines() - set(inclure))
    L = float(abscisses(P)[-1])
    lo, hi = P.min(axis=0) - 7.0, P.max(axis=0) + 7.0
    pp = paires()
    vus, out = set(), []
    for k, g in enumerate(G):
        if k in exclure or k in vus or not ouverte(g):
            continue
        if g[:, 0].max() < lo[0] or g[:, 0].min() > hi[0] or g[:, 1].max() < lo[1] or g[:, 1].min() > hi[1]:
            continue
        Lg = float(abscisses(g)[-1])
        corde = float(np.hypot(*(g[-1] - g[0])))
        if not (0.3 <= Lg <= 6.5) or corde < 0.97 * Lg:
            continue
        s, d, cote = projeter(P, g)
        if d.max() > lat_max + 0.1:
            continue
        u = (g[-1] - g[0]) / corde
        _, tg = point_a(P, np.array([float(s.mean())]))
        if abs(u @ tg[0]) < math.cos(math.radians(ang_max)):
            continue
        a, b = float(s.min()), float(s.max())
        if b < 0.05 or a > L - 0.05:
            continue
        t = float(np.median(cote * d))
        ks = (k,)
        if k in pp and pp[k][0] not in exclure:
            j = pp[k][0]
            s2, d2, c2 = projeter(P, G[j])
            a, b = 0.5 * (a + float(s2.min())), 0.5 * (b + float(s2.max()))
            t = 0.5 * (t + float(np.median(c2 * d2)))
            ks = (min(k, j), max(k, j))
            vus.add(j)
        if abs(t) > lat_max:
            continue
        vus.add(k)
        out.append((a, b, t, ks))
    return sorted(out)


def orphelines(refs_v1, points_v2, dmin=0.5, part=0.8):
    """Lignes GAM ouvertes (≥ 0,3 m) non rattachées au v1 et à plus de dmin de toute marque v2 sur `part` de leur
    longueur : [k] triés."""
    G = M.gam_lin()
    out = []
    for k, P in enumerate(G):
        if k in refs_v1 or not ouverte(P) or abscisses(P)[-1] < 0.3:
            continue
        S, _ = densifier(P, 0.25)
        lo, hi = S.min(axis=0) - dmin, S.max(axis=0) + dmin
        Q = points_v2[(points_v2[:, 0] > lo[0]) & (points_v2[:, 0] < hi[0]) & (points_v2[:, 1] > lo[1]) & (points_v2[:, 1] < hi[1])]
        if len(Q) == 0:
            out.append(k)
            continue
        d = np.array([float(np.min(np.hypot(*(Q - s).T))) for s in S])
        if (d > dmin).mean() > part:
            out.append(k)
    return out
