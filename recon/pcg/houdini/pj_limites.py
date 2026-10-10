"""pj_limites : régularisation topologique des limites de surfaces d'origine raster.

Les surfaces de la description 0.1 sont les polygones v1 vectorisés depuis le raster : limites
ondulées, dents de scie, sommets partagés au millimètre entre voisines (partition). Règle de
fabrication regle:pj_limites.regularisation (la description n'est pas modifiée ; comptes dans le
manifeste, controles.sol.limites) :
1. arcs : chaque anneau est découpé aux nœuds (sommets de degré ≠ 2 du graphe des arêtes) ; un arc
   partagé par deux surfaces n'est traité qu'une fois, les voisines restent donc jointives ;
2. par arc, extrémités fixes : dents supprimées (tournant > 140°, base < 0,30 m, hauteur < 1 m) ;
   calage sur les bordures (tronçon de ≥ 1 m à moins de 2,5 m d'une face vue, à moins de 15° de son
   axe, d'écart régulier (p90 − p10 ≤ 0,25 m) : décalage constant = médiane, déplacement ≤ 0,25 m) ;
   Douglas-Peucker 0,20 m (0,35 m pour une limite d'espace vert ou de massif), dents de 0,3 à 1 m
   retirées (tournant > 105°, base < 1 m), segments ramenés à 0,50 m, puis Chaikin x 2 ; limite
   chaussée neuve 2025 / ancienne : Douglas-Peucker 0,30 m sans Chaikin (reprise sciée, segments droits) ;
3. un arc régularisé qui en croise un autre reprend sa géométrie d'origine.
Aucune décision au pixel : uniquement les sommets vectoriels de la description.
"""
import math

import numpy as np

import pj_commun as K

C = K.C
TOL_DP = 0.20
TOL_DP_SCIE = 0.30
CHAUSSEES = {"enrobe_bbsg_neuf_2025", "enrobe_bbsg_ancien"}
TOL_DP_VEGETAL = 0.35      # limite d'un espace vert ou d'un massif : tracé de projet, pas de festons raster
VEGETAUX = {"gazon_tondu", "herbe_haute", "gazon_sec", "terre_nue", "noue_plantee", "brf_bois_concasse",
            "gravier_concasse_6_10", "paillage_mineral"}


def _cle(p):
    return (int(round(float(p[0]) * 1000)), int(round(float(p[1]) * 1000)))


def _sans_pointes(Q, ang=140.0, base_max=0.30, h_max=1.0):
    """Retire itérativement les sommets intérieurs en pointe : tournant > ang, base (distance entre les
    deux voisins) < base_max et hauteur < h_max (dent de scie d'origine raster)."""
    Q = [np.asarray(q, float) for q in Q]
    change = True
    while change and len(Q) > 3:
        change = False
        for i in range(1, len(Q) - 1):
            u, v = Q[i] - Q[i - 1], Q[i + 1] - Q[i]
            lu, lv = math.hypot(*u), math.hypot(*v)
            if lu < 1e-9 or lv < 1e-9:
                del Q[i]
                change = True
                break
            t = abs(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)))
            if t > ang and math.hypot(*(Q[i + 1] - Q[i - 1])) < base_max and max(lu, lv) < h_max:
                del Q[i]
                change = True
                break
    return np.array(Q)


def _caler(Q, faces):
    """Tronçons parallèles à une face vue proche : décalage constant (médiane)."""
    if len(Q) < 4 or not faces:
        return Q, 0
    A = np.vstack([F[:-1] for _, F in faces])
    B = np.vstack([F[1:] for _, F in faces])
    qui = np.concatenate([np.full(len(F) - 1, k) for k, (_, F) in enumerate(faces)])
    d, j, pr = C.distance_segments(Q, A, B)
    tq = np.gradient(Q, axis=0)
    tq /= np.maximum(np.hypot(tq[:, 0], tq[:, 1]), 1e-12)[:, None]
    tb = (B[j] - A[j]) / np.maximum(np.hypot(*(B[j] - A[j]).T), 1e-12)[:, None]
    par = (d < 2.5) & (np.abs(np.einsum("ij,ij->i", tq, tb)) > math.cos(math.radians(15.0)))
    nl = np.c_[-tb[:, 1], tb[:, 0]]
    off = np.einsum("ij,ij->i", Q - pr, nl)
    Q = Q.copy()
    n_cal = 0
    i = 0
    while i < len(Q):
        if not par[i]:
            i += 1
            continue
        k = i
        while k + 1 < len(Q) and par[k + 1] and qui[j[k + 1]] == qui[j[i]]:
            k += 1
        L = float(np.sum(np.hypot(*np.diff(Q[i:k + 1], axis=0).T))) if k > i else 0.0
        etal = float(np.percentile(off[i:k + 1], 90) - np.percentile(off[i:k + 1], 10)) if k > i else 1.0
        if k - i >= 3 and L >= 1.0 and etal <= 0.25:          # limite parallèle ondulée (pas un biais)
            o = float(np.median(off[i:k + 1]))
            a, b = max(i, 1), min(k + 1, len(Q) - 1)       # extrémités de l'arc fixes
            for t_ in range(a, b):
                nouv = pr[t_] + nl[t_] * o
                # projection perpendiculaire seulement (pas au droit d'un sommet de bordure), 0,25 m au plus
                if np.hypot(*(Q[t_] - pr[t_] - nl[t_] * off[t_])) < 0.01 and np.hypot(*(nouv - Q[t_])) <= 0.25:
                    Q[t_] = nouv
                    n_cal += 1
        i = k + 1
    return Q, n_cal


def _densifier(Q, pas):
    """Segments de `pas` m au plus (Chaikin n'arrondit alors les coins que sur ~pas/4)."""
    out = [Q[0]]
    for a, b in zip(Q[:-1], Q[1:]):
        n = max(1, int(math.ceil(math.hypot(*(b - a)) / pas)))
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return np.array(out)


def _simplifier(Q, tol):
    if len(Q) < 3:
        return Q
    return Q[K.douglas_peucker(Q, tol)]


def _croisements(arcs):
    """Indices des arcs qui croisent un autre arc (segments non adjacents)."""
    segs, qui = [], []
    for k, Q in enumerate(arcs):
        for a, b in zip(Q[:-1], Q[1:]):
            segs.append((a, b))
            qui.append(k)
    if not segs:
        return set()
    S = np.array(segs)
    qui = np.array(qui)
    A, B = S[:, 0], S[:, 1]
    lo, hi = np.minimum(A, B), np.maximum(A, B)
    mauvais = set()

    def orient(p, q, r):
        return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])
    for i in range(len(S)):
        m = (lo[:, 0] <= hi[i, 0]) & (hi[:, 0] >= lo[i, 0]) & (lo[:, 1] <= hi[i, 1]) & (hi[:, 1] >= lo[i, 1])
        m[: i + 1] = False
        idx = np.where(m)[0]
        if len(idx) == 0:
            continue
        # extrémités communes (arcs jointifs) : pas un croisement
        commun = (np.hypot(*(A[idx] - A[i]).T) < 1e-6) | (np.hypot(*(A[idx] - B[i]).T) < 1e-6) | \
                 (np.hypot(*(B[idx] - A[i]).T) < 1e-6) | (np.hypot(*(B[idx] - B[i]).T) < 1e-6)
        idx = idx[~commun]
        if len(idx) == 0:
            continue
        d1, d2 = orient(A[i], B[i], A[idx]), orient(A[i], B[i], B[idx])
        d3, d4 = orient(A[idx], B[idx], A[i]), orient(A[idx], B[idx], B[i])
        x = (d1 * d2 < 0) & (d3 * d4 < 0)
        for k in idx[x]:
            mauvais |= {int(qui[i]), int(qui[k])}
    return mauvais


def regulariser(desc):
    """Pose srf['polys_fab'] (polygones régularisés, repère local) sur chaque surface ; renvoie les comptes."""
    anneaux = []                                   # (i_surface, i_poly, i_anneau, clés)
    for i, srf in enumerate(desc.surfaces):
        for j, poly in enumerate(srf["polys"]):
            for k, r in enumerate(poly):
                cl = [_cle(p) for p in r]
                cl = [c for n, c in enumerate(cl) if c != cl[n - 1]] if len(cl) > 1 else cl
                anneaux.append((i, j, k, cl))
    voisins = {}
    for _, _, _, cl in anneaux:
        for a, b in zip(cl, cl[1:] + cl[:1]):
            voisins.setdefault(a, set()).add(b)
            voisins.setdefault(b, set()).add(a)
    noeud = {c for c, v in voisins.items() if len(v) != 2}
    # arcs canoniques
    arcs, cotes = {}, {}
    decoupe = []
    for (i, j, k, cl) in anneaux:
        n = len(cl)
        pos = [t for t in range(n) if cl[t] in noeud]
        if not pos:                                # anneau sans nœud : arc fermé, départ sur la plus petite clé
            t0 = min(range(n), key=lambda t: cl[t])
            morceaux = [cl[t0:] + cl[:t0] + [cl[t0]]]
        else:
            morceaux = []
            for a, b in zip(pos, pos[1:] + [pos[0] + n]):
                morceaux.append([cl[t % n] for t in range(a, b + 1)])
        refs = []
        for m in morceaux:
            inv = m[::-1]
            can, sens = (tuple(m), 1) if tuple(m) <= tuple(inv) else (tuple(inv), -1)
            arcs.setdefault(can, None)
            cotes.setdefault(can, set()).add(desc.surfaces[i]["p"]["revetement"]["materiau_id"])
            refs.append((can, sens))
        decoupe.append(refs)
    faces = [(B.id, B.P) for B in desc.bordures]
    cles = sorted(arcs)
    orig = [np.array(c, dtype=np.float64) / 1000.0 for c in cles]
    lisses, n_cal, n_scie = [], 0, 0
    for c, Q in zip(cles, orig):
        scie = cotes[c] == CHAUSSEES
        R = _sans_pointes(Q)
        R, nc = _caler(R, faces)
        n_cal += nc
        if scie:
            R = _simplifier(R, TOL_DP_SCIE)
            n_scie += 1
        else:
            R = _simplifier(R, TOL_DP_VEGETAL if cotes[c] & VEGETAUX else TOL_DP)
            R = _sans_pointes(R, ang=105.0, base_max=1.0, h_max=1.2)      # dents de 0,3 à 1 m (raster)
            R = _simplifier(K.lisser_chaikin(_densifier(R, 0.5), 2), 0.005)
        lisses.append(R)
    mauvais = _croisements(lisses)
    for k in sorted(mauvais):
        lisses[k] = orig[k]
    par_cle = dict(zip(cles, lisses))
    ecart = 0.0
    for c, Q, R in zip(cles, orig, lisses):
        if len(R) >= 2 and len(Q) >= 2:
            d, _, _ = C.distance_segments(Q, R[:-1], R[1:])
            ecart = max(ecart, float(d.max()))
    # reconstruction des anneaux
    for srf in desc.surfaces:
        srf["polys_fab"] = [[None] * len(p) for p in srf["polys"]]
    for (i, j, k, cl), refs in zip(anneaux, decoupe):
        pts = []
        for can, sens in refs:
            R = par_cle[can] if sens > 0 else par_cle[can][::-1]
            pts += list(R[:-1])
        r = np.array(pts) if pts else desc.surfaces[i]["polys"][j][k]
        if len(r) < 3 or abs(C.aire_signee(r)) < 0.02:
            r = desc.surfaces[i]["polys"][j][k]
        desc.surfaces[i]["polys_fab"][j][k] = r
    n_av = sum(len(q) for q in orig)
    n_ap = sum(len(q) for q in lisses)
    return {"regle": "regle:pj_limites.regularisation", "arcs": len(cles), "noeuds": len(noeud),
            "sommets_avant": n_av, "sommets_apres": n_ap, "sommets_cales_sur_bordure": n_cal,
            "arcs_scies_neuf_ancien": n_scie, "arcs_rendus_a_l_origine": len(mauvais),
            "ecart_max_m": round(ecart, 3)}
