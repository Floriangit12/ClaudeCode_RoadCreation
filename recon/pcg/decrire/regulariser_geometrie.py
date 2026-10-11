"""Régularisation géométrique, cœur numérique (numpy seul) : ajustement d'une polyligne levée (bruitée,
cassée) par une suite de primitives droites / arcs de cercle (clothoïdes en option) continue en position et
en tangente (G1), dans la tolérance de sa source ; densification à flèche ≤ 2 mm ; mesures de cassures.

Règles (assets/specs/regles_qualite_geometrique.json) :
- GQ-PRI-001 / GQ-PRI-002 : primitives admises (droite, arc ; clothoïde pour les axes de marquage) ;
- GQ-CON-001 : continuité G1 partout sauf aux coins voulus (GQ-CON-002) ; la paramétrisation intrinsèque
  (départ x0, y0, cap h0 puis pièces (L, k0, k1)) garantit G1 par construction ;
- GQ-TOL-001 : écart à la source ≤ T (99 % des points) et ≤ 1,5 T (tous), T par source ;
- GQ-SEG-001 : pas de micro-pièce (longueur minimale par famille) ;
- GQ-RAY-003 : rayons arrondis à la série normalisée quand l'écart reste dans la tolérance ;
- GQ-DEN-001 : polyligne densifiée à flèche ≤ 2 mm, sommet à chaque raccord de primitives.

Méthode (déterministe) : nettoyage (sommets < 5 mm fusionnés) -> coins (déviation ≥ 30° portée par deux
alignements droits) -> pour chaque tronçon entre coins : découpage initial descendant (droite ou arc par
moindres carrés, coupe au point le plus éloigné), puis ajustement G1 global (Levenberg-Marquardt, résidus
normaux pondérés Huber, projection de Newton des points de mesure) avec contraintes de nœuds (position,
cap) ; boucle découpe (écart > T) / fusion (pièces voisines compatibles) / arrondi (droite, rayon normalisé).
"""
import math

import numpy as np

E_FLECHE = 0.002          # GQ-DEN-001 : flèche de corde maximale de la polyligne densifiée (m)
SEUIL_COIN_DEG = 30.0     # GQ-CON-002 : déviation minimale d'un coin voulu
LONG_COIN_M = 1.0         # longueur d'alignement examinée de part et d'autre d'un coin
SERIE_RAYONS = [0.25, 0.5, 1.2, 1.4, 1.6, 1.8, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0,
                30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 150.0, 200.0, 250.0, 300.0, 400.0, 500.0]   # GQ-RAY-003


def _sinc(a):
    """sin(a)/a (1 en 0), sans le détour de np.sinc."""
    a = np.asarray(a, dtype=np.float64)
    pt = np.abs(a) < 1e-4
    aa = np.where(pt, 1.0, a)
    return np.where(pt, 1.0 - a * a / 6.0, np.sin(aa) / aa)


def wrap(a):
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi


# --------------------------------------------------------------------------- chaîne de primitives
class Chaine:
    """Suite G1 de primitives à courbure affine en s : droite (k = 0), arc (k constant), clothoïde (k0 -> k1).
    Départ (x0, y0), cap h0 (rad, depuis l'axe x, sens trigonométrique), pièces [L, k0, k1] (k > 0 : à gauche)."""

    def __init__(self, x0, y0, h0, pieces):
        self.x0, self.y0, self.h0 = float(x0), float(y0), float(h0)
        self.pieces = [[float(L), float(k0), float(k1)] for L, k0, k1 in pieces]
        self._preparer()

    def _preparer(self):
        U, X, Y, H, K = [0.0], [self.x0], [self.y0], [self.h0], []
        self.debut_piece = []
        for L, k0, k1 in self.pieces:
            L = max(L, 0.0)
            self.debut_piece.append(len(K))
            if abs(k1 - k0) < 1e-12:
                subs = [(L, k0)]
            else:                                            # clothoïde : sous-arcs de 5 cm (courbure au milieu)
                m = max(1, int(math.ceil(L / 0.05)))
                subs = [(L / m, k0 + (k1 - k0) * (j + 0.5) / m) for j in range(m)]
            for d, k in subs:
                h = H[-1]
                a = k * d / 2.0
                c = d * (math.sin(a) / a if abs(a) > 1e-6 else 1.0 - a * a / 6.0)
                X.append(X[-1] + c * math.cos(h + a))
                Y.append(Y[-1] + c * math.sin(h + a))
                H.append(h + k * d)
                U.append(U[-1] + d)
                K.append(k)
        if not K:
            K = [0.0]
            U.append(U[-1])
            X.append(X[-1])
            Y.append(Y[-1])
            H.append(H[-1])
        self.U, self.X, self.Y = np.array(U), np.array(X), np.array(Y)
        self.H, self.K = np.array(H), np.array(K)
        self.L = float(self.U[-1])
        self.bornes = np.r_[0.0, np.cumsum([max(p[0], 0.0) for p in self.pieces])]

    def evaluer(self, u):
        """(points (n, 2), cap (n,), courbure (n,)) aux abscisses u (bornées à [0, L])."""
        u = np.clip(np.atleast_1d(np.asarray(u, dtype=np.float64)), 0.0, self.L)
        i = np.clip(np.searchsorted(self.U, u, side="right") - 1, 0, len(self.K) - 1)
        t = u - self.U[i]
        k = self.K[i]
        h = self.H[i]
        a = k * t / 2.0
        c = t * _sinc(a)
        return np.column_stack((self.X[i] + c * np.cos(h + a), self.Y[i] + c * np.sin(h + a))), h + k * t, k

    def fin(self):
        return np.array([self.X[-1], self.Y[-1]]), float(self.H[-1])

    def types(self):
        return [type_piece(k0, k1) for _, k0, k1 in self.pieces]

    def copie(self):
        return Chaine(self.x0, self.y0, self.h0, [list(p) for p in self.pieces])


def type_piece(k0, k1):
    if abs(k1 - k0) > 1e-9:
        return "clothoide"
    return "droite" if abs(k0) < 1e-9 else "arc"


# --------------------------------------------------------------------------- ajustements élémentaires
def droite_tls(Q):
    """Droite des moindres carrés totaux : (centre, direction unitaire, écart max)."""
    c = Q.mean(axis=0)
    M = Q - c
    _, _, vt = np.linalg.svd(M, full_matrices=False)
    d = vt[0]
    n = np.array([-d[1], d[0]])
    e = np.abs(M @ n)
    return c, d, float(e.max()) if len(e) else 0.0


def cercle(Q):
    """Cercle des moindres carrés (Kåsa puis 5 itérations géométriques) : (centre, rayon, écart max) ou None."""
    if len(Q) < 3:
        return None
    c0 = Q.mean(axis=0)
    M = Q - c0
    A = np.c_[2 * M, np.ones(len(M))]
    b = (M ** 2).sum(1)
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    a, bb, c = sol
    r2 = c + a * a + bb * bb
    if not np.isfinite(r2) or r2 <= 0:
        return None
    cx, cy, r = a, bb, math.sqrt(r2)
    for _ in range(5):                                     # Gauss-Newton géométrique
        dx, dy = M[:, 0] - cx, M[:, 1] - cy
        di = np.hypot(dx, dy)
        if np.any(di < 1e-12):
            break
        J = np.c_[-dx / di, -dy / di, -np.ones(len(di))]
        res = di - r
        try:
            st, *_ = np.linalg.lstsq(J, -res, rcond=None)
        except np.linalg.LinAlgError:
            break
        cx, cy, r = cx + st[0], cy + st[1], r + st[2]
        if np.abs(st).max() < 1e-10:
            break
    if not (np.isfinite(r) and r > 0 and r < 1e6):
        return None
    e = np.abs(np.hypot(M[:, 0] - cx, M[:, 1] - cy) - r)
    return np.array([cx, cy]) + c0, float(r), float(e.max())


def abscisse(P):
    if len(P) < 2:
        return np.zeros(len(P))
    return np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]


def nettoyer(P, tol=0.005):
    """Sommets successifs à moins de tol fusionnés ; allers-retours (pointes) retirés."""
    P = np.asarray(P, dtype=np.float64)[:, :2]
    if len(P) < 2:
        return P
    out = [P[0]]
    for q in P[1:-1]:
        if np.hypot(*(q - out[-1])) > tol:
            out.append(q)
    if np.hypot(*(P[-1] - out[-1])) > tol or len(out) == 1:
        out.append(P[-1])
    else:
        out[-1] = P[-1]
    Q = np.array(out)
    k = 1
    while len(Q) > 2 and k < len(Q) - 1:                   # pointe : demi-tour (> 170°) sur un sommet
        a, b = Q[k] - Q[k - 1], Q[k + 1] - Q[k]
        ca = float(a @ b) / max(np.hypot(*a) * np.hypot(*b), 1e-12)
        if ca < -0.985:
            Q = np.delete(Q, k, axis=0)
            k = max(1, k - 1)
        else:
            k += 1
    return Q


def reechantillonner(P, pas):
    """Points tous les ≤ pas m, sommets d'origine compris (données d'ajustement)."""
    S = abscisse(P)
    L = S[-1]
    n = max(1, int(math.ceil(L / pas)))
    s = np.unique(np.r_[S, np.linspace(0.0, L, n + 1)])
    s = s[np.r_[True, np.diff(s) > 1e-6]]
    i = np.clip(np.searchsorted(S, s, side="right") - 1, 0, len(P) - 2)
    t = ((s - S[i]) / np.maximum(S[i + 1] - S[i], 1e-12))[:, None]
    return P[i] * (1 - t) + P[i + 1] * t, s


# --------------------------------------------------------------------------- coins voulus (GQ-CON-002)
def coins(P, tol, seuil_deg=SEUIL_COIN_DEG, ferme=False, lmin=0.5, rmin=0.25):
    """Indices des sommets de P qui sont des coins voulus (GQ-CON-002) : un congé constructible (rayon
    ≥ rmin et longueur ≥ lmin) passerait à plus de tol du sommet, et le coin est porté par deux alignements
    droits (écart ≤ tol sur ≤ LONG_COIN_M de chaque côté) ou dévie de 45° au moins."""
    n = len(P)
    if n < 3:
        return []
    S = abscisse(P)
    cand = []
    for i in range(n):
        if not ferme and (i == 0 or i == n - 1):
            continue
        if ferme and i == n - 1:
            continue
        a = P[i] - P[i - 1] if i > 0 else P[0] - P[-2]
        b = P[i + 1] - P[i]
        ang = abs(math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a @ b)))
        if ang >= min(seuil_deg, 20.0):
            cand.append((i, ang))
    out = []
    for j, (i, ang) in enumerate(cand):
        al = math.radians(min(ang, 179.0))
        r_eff = max(rmin, lmin / al)
        if r_eff * (1.0 / math.cos(al / 2) - 1.0) <= tol:
            continue                                         # un congé constructible tient dans la tolérance
        s0 = S[cand[j - 1][0]] if j > 0 else S[0]
        s1 = S[cand[j + 1][0]] if j + 1 < len(cand) else S[-1]
        lo, hi = max(s0, S[i] - LONG_COIN_M), min(s1, S[i] + LONG_COIN_M)
        ok = True
        for a0, a1 in ((lo, S[i]), (S[i], hi)):
            m = (S >= a0 - 1e-9) & (S <= a1 + 1e-9)
            Q = P[m]
            if len(Q) >= 3 and droite_tls(Q)[2] > tol:
                ok = False
        if ok or ang >= 45.0:
            out.append(i)
    return out


# --------------------------------------------------------------------------- découpage initial
def _ajuster_morceau(Q, tol, rmin):
    """('droite', e) ou ('arc', e, centre, r) le meilleur dans la tolérance, sinon None."""
    _, _, el = droite_tls(Q)
    if el <= tol:
        return ("droite", el)
    c = cercle(Q)
    if c is not None and c[2] <= tol and c[1] >= rmin:
        # l'arc doit être parcouru dans un seul sens (angle < 2π, monotone)
        ang = np.unwrap(np.arctan2(Q[:, 1] - c[0][1], Q[:, 0] - c[0][0]))
        d = np.diff(ang)
        if np.all(d >= -1e-6) or np.all(d <= 1e-6):
            return ("arc", c[2], c[0], c[1])
    return None


def decoupage_initial(Q, s, tol, lmin, rmin):
    """Morceaux [(i0, i1)] (indices inclus) chacun ajustable par une droite ou un arc dans tol."""
    pile = [(0, len(Q) - 1)]
    out = []
    while pile:
        i0, i1 = pile.pop()
        seg = Q[i0:i1 + 1]
        if i1 - i0 < 2 or s[i1] - s[i0] < 2 * lmin or _ajuster_morceau(seg, tol, rmin) is not None:
            out.append((i0, i1))
            continue
        a, b = Q[i0], Q[i1]
        ab = b - a
        lab = max(np.hypot(*ab), 1e-12)
        d = np.abs((seg[:, 0] - a[0]) * ab[1] - (seg[:, 1] - a[1]) * ab[0]) / lab
        ok = (s[i0:i1 + 1] - s[i0] >= lmin) & (s[i1] - s[i0:i1 + 1] >= lmin)
        if not ok.any():
            out.append((i0, i1))
            continue
        d = np.where(ok, d, -1.0)
        k = i0 + int(np.argmax(d))
        if d.max() < 0.25 * tol:                           # arc presque centré : couper au milieu
            k = i0 + int(np.argmin(np.abs(s[i0:i1 + 1] - (s[i0] + s[i1]) / 2)))
        pile.append((k, i1))
        pile.append((i0, k))
    out.sort()
    # fusion gloutonne des voisins compatibles
    change = True
    while change and len(out) > 1:
        change = False
        for j in range(len(out) - 1):
            i0, i1 = out[j][0], out[j + 1][1]
            if _ajuster_morceau(Q[i0:i1 + 1], 0.9 * tol, rmin) is not None:
                out[j:j + 2] = [(i0, i1)]
                change = True
                break
    return out


def chaine_initiale(Q, s, morceaux, rmin, lmin=0.5):
    """Chaîne G1 initiale : primitive (droite ou arc) de chaque morceau ; aux raccords où les tangentes des
    primitives voisines diffèrent de plus de 1°, un congé (arc court) absorbe l'écart de cap, pris sur les
    longueurs voisines : la chaîne initiale suit déjà les données (convergence locale de l'ajustement)."""
    prims = []
    for i0, i1 in morceaux:
        seg = Q[i0:i1 + 1]
        L = float(s[i1] - s[i0])
        f = None
        if len(seg) >= 3:
            _, _, el = droite_tls(seg)
            c = cercle(seg)
            if c is not None and c[1] >= rmin and c[2] < 0.5 * el:
                ang = np.unwrap(np.arctan2(seg[:, 1] - c[0][1], seg[:, 0] - c[0][0]))
                if np.all(np.diff(ang) >= -1e-6) or np.all(np.diff(ang) <= 1e-6):
                    f = ("arc", c[2], c[0], c[1])
        if f is None:
            c, d, _ = droite_tls(seg) if len(seg) >= 2 else (seg[0], np.array([1.0, 0.0]), 0.0)
            if d @ (seg[-1] - seg[0]) < 0:
                d = -d
            k = 0.0
            hs = math.atan2(d[1], d[0])
            p0 = c + d * ((seg[0] - c) @ d)
        else:
            _, _, cen, r = f
            v0 = seg[0] - cen
            ang = np.unwrap(np.arctan2(seg[:, 1] - cen[1], seg[:, 0] - cen[0]))
            sens = 1.0 if ang[-1] >= ang[0] else -1.0          # sens de parcours (arcs > 180° compris)
            k = sens / r
            hs = math.atan2(v0[1], v0[0]) + sens * math.pi / 2
            p0 = cen + r * v0 / max(np.hypot(*v0), 1e-12)
            L = abs(float(ang[-1] - ang[0])) * r
        prims.append([L, k, hs, p0])
    pieces = []
    for j, (L, k, hs, p0) in enumerate(prims):
        if j > 0:
            Lp, kp, hp, _ = prims[j - 1]
            dlt = float(wrap(hs - (hp + kp * Lp)))
            if abs(dlt) > math.radians(1.0):
                ell = max(lmin, abs(dlt) * rmin)
                ell = min(ell, 0.45 * pieces[-1][0] + 0.45 * L)
                if ell > 1e-3:
                    pieces[-1][0] -= ell / 2
                    L -= ell / 2
                    kc = dlt / ell
                    pieces.append([ell, kc, kc])
        pieces.append([L, k, k])
    for p_ in pieces:
        p_[0] = max(p_[0], 1e-3)
    _, _, h0, P0 = prims[0][0], prims[0][1], prims[0][2], prims[0][3]
    return Chaine(P0[0], P0[1], h0, pieces)


# --------------------------------------------------------------------------- ajustement G1 (Levenberg-Marquardt)
class Contraintes:
    """Nœuds imposés : position et cap au début / à la fin ; chaîne fermée."""

    def __init__(self, debut=None, fin=None, cap_debut=None, cap_fin=None, ferme=False, poids_bout=3.0):
        self.debut = None if debut is None else np.asarray(debut, float)
        self.fin = None if fin is None else np.asarray(fin, float)
        self.cap_debut, self.cap_fin, self.ferme = cap_debut, cap_fin, ferme
        self.poids_bout = poids_bout


def projeter(ch, D, u):
    """Projection de Newton des points D sur la chaîne, à partir des abscisses u."""
    for _ in range(6):
        C, h, k = ch.evaluer(u)
        T = np.column_stack((np.cos(h), np.sin(h)))
        N = np.column_stack((-T[:, 1], T[:, 0]))
        e = D - C
        den = 1.0 - k * (e * N).sum(1)
        den = np.where(den > 0.2, den, 1.0)
        du = (e * T).sum(1) / den
        u = np.clip(u + du, 0.0, ch.L)
        if np.abs(du).max() < 1e-7:
            break
    C, h, k = ch.evaluer(u)
    N = np.column_stack((-np.sin(h), np.cos(h)))
    return u, C, N


def _vecteur(ch):
    m = len(ch.pieces)
    v = np.empty(3 + 2 * m)
    v[:3] = ch.x0, ch.y0, ch.h0
    for j, (L, k0, _) in enumerate(ch.pieces):
        v[3 + j], v[3 + m + j] = L, k0
    return v


def _depuis(v, m):
    return Chaine(v[0], v[1], v[2], [(v[3 + j], v[3 + m + j], v[3 + m + j]) for j in range(m)])


def _dF_dk(t, h, k):
    """Dérivée par rapport à la courbure du point d'un arc (départ fixe, cap h) à l'abscisse t."""
    t = np.asarray(t, dtype=np.float64)
    a = k * t / 2.0
    c = t * _sinc(a)
    small = np.abs(a) < 1e-3
    aa = np.where(small, 1.0, a)
    g = np.where(small, -a / 3.0 + a ** 3 / 30.0, (aa * np.cos(aa) - np.sin(aa)) / aa ** 2)
    dc = t * t / 2.0 * g
    ph = h + a
    return np.column_stack((dc * np.cos(ph) - c * t / 2.0 * np.sin(ph), dc * np.sin(ph) + c * t / 2.0 * np.cos(ph)))


def _jacobien_points(ch, u, bout=False):
    """dC/dp (n, 2, 3 + 2m) pour p = [x0, y0, h0, L_j, k_j] (chaîne de droites et d'arcs) aux abscisses u
    fixes ; bout=True : point final de la chaîne (suit l'allongement de la dernière pièce). Vectorisé."""
    m = len(ch.pieces)
    u = np.atleast_1d(np.asarray(u, dtype=np.float64))
    n = len(u)
    C, H, _ = ch.evaluer(u)
    idx = np.clip(np.searchsorted(ch.bornes, u, side="right") - 1, 0, m - 1)
    if bout:
        idx[:] = m - 1
    Lp = np.array([max(p[0], 0.0) for p in ch.pieces])
    kp = np.array([p[1] for p in ch.pieces])
    hs, he = ch.H[:m], ch.H[1:m + 1]
    Ex, Ey = ch.X[1:m + 1], ch.Y[1:m + 1]
    G = np.zeros((n, 2, 3 + 2 * m))
    G[:, 0, 0] = 1.0
    G[:, 1, 1] = 1.0
    G[:, 0, 2] = -(C[:, 1] - ch.y0)
    G[:, 1, 2] = C[:, 0] - ch.x0
    apres = idx[:, None] > np.arange(m)[None, :]
    dx = C[:, 0, None] - Ex[None, :]
    dy = C[:, 1, None] - Ey[None, :]
    if bout:
        t0 = np.cos(he)[None, :] - kp[None, :] * dy
        t1 = np.sin(he)[None, :] + kp[None, :] * dx
    else:
        t0 = np.cos(he)[None, :] - kp[None, :] * dy - np.cos(H)[:, None]
        t1 = np.sin(he)[None, :] + kp[None, :] * dx - np.sin(H)[:, None]
    G[:, 0, 3:3 + m] = np.where(apres, t0, 0.0)
    G[:, 1, 3:3 + m] = np.where(apres, t1, 0.0)
    dE = _dF_dk(Lp, hs, kp)
    G[:, 0, 3 + m:] = np.where(apres, dE[None, :, 0] - Lp[None, :] * dy, 0.0)
    G[:, 1, 3 + m:] = np.where(apres, dE[None, :, 1] + Lp[None, :] * dx, 0.0)
    r = np.arange(n)
    dF = _dF_dk(u - ch.bornes[idx], hs[idx], kp[idx])
    G[r, 0, 3 + m + idx] = dF[:, 0]
    G[r, 1, 3 + m + idx] = dF[:, 1]
    if bout:
        G[r, 0, 3 + idx] = np.cos(he[idx])
        G[r, 1, 3 + idx] = np.sin(he[idx])
    return G


def ajuster_lm(ch, D, cons, lmin, libres_k=None, maxit=60, huber=None, rmin=0.2):
    """Ajustement G1 de la chaîne (droites et arcs) aux points D (ordonnés) sous contraintes (Levenberg-
    Marquardt, jacobien analytique, résidus normaux à abscisses fixées puis reprojection) ; renvoie
    (chaîne, u, résidus normaux signés)."""
    m = len(ch.pieces)
    kmax = 1.0 / rmin
    v = _vecteur(ch)
    libres_k = libres_k if libres_k is not None else [True] * m
    libre = np.ones(len(v), bool)
    if cons.debut is not None:
        libre[0] = libre[1] = False
        v[0], v[1] = cons.debut
    if cons.cap_debut is not None:
        libre[2] = False
        v[2] = cons.cap_debut
    for j in range(m):
        libre[3 + m + j] = bool(libres_k[j])
    idx = np.nonzero(libre)[0]
    ch = _depuis(v, m)
    S = abscisse(D)
    u = S * (ch.L / max(S[-1], 1e-9))
    wb = cons.poids_bout
    W_DUR = 300.0
    npar = 3 + 2 * m

    def evaluer(w, u, N, poids, avec_j):
        c = _depuis(w, m)
        C, _, _ = c.evaluer(u)
        r = [poids * ((D - C) * N).sum(1)]
        Js = []
        if avec_j:
            G = _jacobien_points(c, u)
            Js.append(-(poids[:, None] * (G * N[:, :, None]).sum(1)))
            Gf = _jacobien_points(c, np.array([c.L]), bout=True)[0]
        pf, hf = c.fin()
        dHf = np.zeros(npar)
        dHf[2] = 1.0
        dHf[3:3 + m] = w[3 + m:3 + 2 * m]
        dHf[3 + m:] = w[3:3 + m]
        if cons.debut is None:
            r.append(wb * (np.array([c.x0, c.y0]) - D[0]))
            if avec_j:
                Z = np.zeros((2, npar))
                Z[0, 0] = Z[1, 1] = wb
                Js.append(Z)
        if cons.ferme:
            r.append(W_DUR * (pf - np.array([c.x0, c.y0])))
            tour = math.copysign(2 * math.pi, sum(p[0] * p[1] for p in c.pieces))
            r.append(W_DUR * np.atleast_1d(wrap(hf - c.h0 - tour)))
            if avec_j:
                Z = W_DUR * Gf.copy()
                Z[0, 0] -= W_DUR
                Z[1, 1] -= W_DUR
                Js.append(Z)
                dh = W_DUR * dHf.copy()
                dh[2] -= W_DUR
                Js.append(dh[None])
        elif cons.fin is not None:
            r.append(W_DUR * (pf - cons.fin))
            if avec_j:
                Js.append(W_DUR * Gf)
        else:
            r.append(wb * (pf - D[-1]))
            if avec_j:
                Js.append(wb * Gf)
        if cons.cap_fin is not None:
            r.append(W_DUR * np.atleast_1d(wrap(hf - cons.cap_fin)))
            if avec_j:
                Js.append(W_DUR * dHf[None])
        Ls = w[3:3 + m]
        ks = w[3 + m:3 + 2 * m]
        lmins = np.where(np.abs(ks) >= 1.0 / 1.2, min(lmin, 0.2), lmin)     # GQ-SEG-001 : arc serré ≥ 0,20 m
        r.append(W_DUR * np.minimum(Ls - lmins, 0.0))
        r.append(W_DUR * np.sign(ks) * np.maximum(np.abs(ks) - kmax, 0.0))
        if avec_j:
            Z = np.zeros((m, npar))
            Z[np.arange(m), 3 + np.arange(m)] = W_DUR * (Ls < lmins)
            Js.append(Z)
            Z = np.zeros((m, npar))
            Z[np.arange(m), 3 + m + np.arange(m)] = W_DUR * (np.abs(ks) > kmax)
            Js.append(Z)
            return np.concatenate(r), np.vstack(Js)
        return np.concatenate(r), None

    lam = 1e-3
    u, C, N = projeter(ch, D, u)
    poids = np.ones(len(D))
    for it in range(maxit):
        if huber:
            a_ = np.abs(((D - C) * N).sum(1))
            poids = np.where(a_ <= huber, 1.0, np.sqrt(huber / np.maximum(a_, 1e-12)))
        r0, J = evaluer(v, u, N, poids, True)
        J = J[:, idx]
        c0 = float(r0 @ r0)
        g = J.T @ r0
        A = J.T @ J
        ok = False
        c1 = c0
        st = np.zeros(len(idx))
        for _ in range(10):
            try:
                st = np.linalg.solve(A + lam * np.diag(np.maximum(np.diag(A), 1e-9)), -g)
            except np.linalg.LinAlgError:
                lam *= 10
                continue
            w = v.copy()
            w[idx] += st
            w[3:3 + m] = np.maximum(w[3:3 + m], 1e-4)
            r1, _ = evaluer(w, u, N, poids, False)
            c1 = float(r1 @ r1)
            if c1 < c0:
                v = w
                lam = max(lam / 3.0, 1e-9)
                ok = True
                break
            lam *= 4.0
        ch = _depuis(v, m)
        u, C, N = projeter(ch, D, u)
        if not ok or (c0 - c1) < 1e-8 * max(c0, 1e-12) or np.abs(st).max() < 1e-7:
            break
    rd = ((D - C) * N).sum(1)
    return ch, u, rd


# --------------------------------------------------------------------------- écarts
def distance_a_polyligne(Q, P):
    """Distance de chaque point Q à la polyligne P (segments)."""
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-18)
    out = np.empty(len(Q))
    pas = max(1, 1_500_000 // max(len(A), 1))
    for k0 in range(0, len(Q), pas):
        q = Q[k0:k0 + pas]
        AQ = q[:, None, :] - A[None]
        t = np.clip(np.einsum("qij,ij->qi", AQ, AB) / L2, 0, 1)
        d = np.hypot(*(AQ - t[..., None] * AB[None]).transpose(2, 0, 1))
        out[k0:k0 + pas] = d.min(axis=1)
    return out


def ecarts(ch, D, P_source):
    """Écarts symétriques (m) : points de la source -> chaîne, et chaîne -> polyligne source."""
    u = abscisse(D) * (ch.L / max(abscisse(D)[-1], 1e-9))
    u, C, N = projeter(ch, D, u)
    d1 = np.hypot(*(D - C).T)
    n = max(2, int(math.ceil(ch.L / 0.05)) + 1)
    Cc, _, _ = ch.evaluer(np.linspace(0.0, ch.L, n))
    d2 = distance_a_polyligne(Cc, P_source) if len(P_source) >= 2 else np.zeros(1)
    return d1, d2


def accepte(d1, d2, tol):
    """GQ-TOL-001 : 99 % des écarts ≤ T et aucun > 1,5 T ; GQ-TOL-002 (contrainte) : écart moyen des points de
    la source ≤ T / 2 (pas de biais systématique ; le contrôle signale au-delà de T / 3,23)."""
    d = np.r_[d1, d2]
    return bool(np.percentile(d, 99) <= tol + 1e-9 and d.max() <= 1.5 * tol + 1e-9
                and float(np.mean(d1)) <= tol / 2.0 + 1e-4)


# --------------------------------------------------------------------------- tronçon complet
def ajuster_troncon(P, tol, cons, lmin=0.5, rmin=0.2, serie=SERIE_RAYONS, max_tours=24, arrondir=True):
    """Ajuste un tronçon (sans coin) : chaîne G1 de droites / arcs dans la tolérance. Renvoie un dict."""
    P = np.asarray(P, float)
    L_src = float(abscisse(P)[-1])
    pas = min(0.10, max(0.01, L_src / 400.0))
    D, s = reechantillonner(P, pas)
    lmin_eff = min(lmin, max(L_src / 3.0, 0.02))
    if len(D) < 3 or L_src < 2 * lmin_eff:
        a, b = (cons.debut if cons.debut is not None else P[0]), (cons.fin if cons.fin is not None else P[-1])
        h = math.atan2(b[1] - a[1], b[0] - a[0])
        ch = Chaine(a[0], a[1], h, [[float(np.hypot(*(b - a))), 0.0, 0.0]])
        d1, d2 = ecarts(ch, D, P)
        return {"chaine": ch, "d1": d1, "d2": d2, "ok": accepte(d1, d2, tol), "tours": 0}
    morceaux = decoupage_initial(D, s, 0.8 * tol, lmin_eff, rmin)
    ch = chaine_initiale(D, s, morceaux, rmin, lmin_eff)
    hub = 0.5 * tol
    ch, u, rd = ajuster_lm(ch, D, cons, lmin_eff, huber=hub, rmin=rmin)
    tours = 0
    # boucle de découpe : tant que l'écart dépasse T, couper la pièce du pire point
    while tours < max_tours:
        d1, d2 = ecarts(ch, D, P)
        if accepte(d1, d2, tol):
            break
        tours += 1
        i = int(np.argmax(np.abs(rd)))
        uu = float(np.clip(u[i], 0, ch.L))
        j = int(np.clip(np.searchsorted(ch.bornes, uu, side="right") - 1, 0, len(ch.pieces) - 1))
        a, b = ch.bornes[j], ch.bornes[j + 1]
        if b - a < 2.2 * lmin_eff:
            # pièce trop courte pour être coupée : couper la plus longue voisine du pire point
            j = int(np.argmax([p[0] for p in ch.pieces]))
            a, b = ch.bornes[j], ch.bornes[j + 1]
            uu = (a + b) / 2
            if b - a < 2.2 * lmin_eff:
                break
        uu = float(np.clip(uu, a + 1.1 * lmin_eff, b - 1.1 * lmin_eff))
        L, k0, k1 = ch.pieces[j]
        km = k0 + (k1 - k0) * (uu - a) / max(L, 1e-9)
        pieces = ch.pieces[:j] + [[uu - a, k0, km], [b - uu, km, k1]] + ch.pieces[j + 1:]
        ch = Chaine(ch.x0, ch.y0, ch.h0, pieces)
        ch, u, rd = ajuster_lm(ch, D, cons, lmin_eff, huber=hub, rmin=rmin)
    d1, d2 = ecarts(ch, D, P)
    ok = accepte(d1, d2, tol)
    # fusions : supprimer les raccords inutiles (parcimonie, GQ-SEG-002)
    if ok and len(ch.pieces) > 1:
        ch, u, rd = _fusions(ch, D, P, cons, lmin_eff, tol, hub, rmin)
    # arrondis : droite si la flèche est négligeable, rayon de la série normalisée (GQ-RAY-003)
    if ok and arrondir:
        ch = _arrondis(ch, D, P, cons, lmin_eff, tol, hub, serie, rmin)
    ch2 = fermer_exactement(ch, cons)
    if ch2 is None:                                     # bout imposé hors d'atteinte : arc unique entre nœuds
        ch2 = arc_entre_noeuds(D, P, cons, rmin, depart=np.array([ch.x0, ch.y0]))
    ch = ch2
    d1, d2 = ecarts(ch, D, P)
    return {"chaine": ch, "d1": d1, "d2": d2, "ok": accepte(d1, d2, tol), "tours": tours}


def arc_entre_noeuds(D, P, cons, rmin, depart=None):
    """Arc (ou droite) unique passant exactement par les deux nœuds imposés, de courbure choisie pour
    minimiser l'écart maximal aux données (|k| ≤ 1/rmin) ; sans cap imposé au départ."""
    A = np.asarray(cons.debut if cons.debut is not None else depart, float)
    B = np.asarray(cons.fin, float)
    c = B - A
    d = float(np.hypot(*c))
    a0 = math.atan2(c[1], c[0])
    kmax = min(1.0 / rmin, 2.0 / max(d, 1e-9) * 0.999)

    def chaine(k):
        if abs(k) < 1e-9:
            return Chaine(A[0], A[1], a0, [[d, 0.0, 0.0]])
        phi = math.asin(max(-1.0, min(1.0, k * d / 2.0)))
        return Chaine(A[0], A[1], a0 - phi, [[2.0 * phi / k, k, k]])

    def cout(k):
        ch = chaine(k)
        d1, d2 = ecarts(ch, D, P)
        return max(float(d1.max()), float(d2.max()))

    ks = np.linspace(-kmax, kmax, 81)
    cs = [cout(k) for k in ks]
    i = int(np.argmin(cs))
    lo, hi = ks[max(i - 1, 0)], ks[min(i + 1, len(ks) - 1)]
    for _ in range(30):                                 # section dorée
        m1, m2 = lo + 0.382 * (hi - lo), lo + 0.618 * (hi - lo)
        if cout(m1) <= cout(m2):
            hi = m2
        else:
            lo = m1
    k = (lo + hi) / 2.0
    return chaine(0.0 if cout(0.0) <= cout(k) + 1e-4 else k)


def fermer_exactement(ch, cons):
    """Bout imposé atteint exactement (GQ-TOP-001) : le résidu de l'ajustement (≤ quelques mm en général) est
    absorbé par une similitude autour du départ (rotation δ, échelle f des longueurs, courbures / f) qui garde
    la chaîne G1 et ses types de primitives."""
    if cons.fin is None or cons.ferme:
        return ch
    p0 = np.array([ch.x0, ch.y0])
    pf, _ = ch.fin()
    v1, v2 = pf - p0, cons.fin - p0
    n1, n2 = float(np.hypot(*v1)), float(np.hypot(*v2))
    if n1 < 1e-9 or float(np.hypot(*(pf - cons.fin))) < 1e-6:
        return ch
    dlt = math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1 @ v2)
    f = n2 / n1
    if abs(f - 1.0) > 0.005 or abs(dlt) > math.radians(0.5):
        return None                                     # correction trop forte : la chaîne ne tient pas le nœud
    return Chaine(ch.x0, ch.y0, ch.h0 + dlt, [[L * f, k0 / f, k1 / f] for L, k0, k1 in ch.pieces])


def _fusions(ch, D, P, cons, lmin, tol, hub, rmin):
    u = rd = None
    essais = 0
    while len(ch.pieces) > 1 and essais < 3 * len(ch.pieces) + 4:
        # raccords triés par dissemblance de courbure pondérée par la longueur
        cand = []
        for j in range(len(ch.pieces) - 1):
            La, ka, _ = ch.pieces[j]
            Lb, kb, _ = ch.pieces[j + 1]
            cand.append((abs(ka - kb) * min(La, Lb) ** 2, j))
        cand.sort()
        fait = False
        for _, j in cand[:3]:
            essais += 1
            La, ka, _ = ch.pieces[j]
            Lb, kb, _ = ch.pieces[j + 1]
            k = (La * ka + Lb * kb) / max(La + Lb, 1e-9)
            pieces = ch.pieces[:j] + [[La + Lb, k, k]] + ch.pieces[j + 2:]
            c2, u2, rd2 = ajuster_lm(Chaine(ch.x0, ch.y0, ch.h0, pieces), D, cons, lmin, huber=hub, rmin=rmin, maxit=30)
            d1, d2 = ecarts(c2, D, P)
            if accepte(d1, d2, tol):
                ch, u, rd = c2, u2, rd2
                fait = True
                break
        if not fait:
            break
    return ch, u, rd


def _arrondis(ch, D, P, cons, lmin, tol, hub, serie, rmin):
    """GQ-RAY-003 : arc -> droite si sa flèche est < T/2 (ou R > 500 m : tolérance élargie de la flèche, l'arc
    n'étant alors qu'un bruit de dessin), sinon rayon de la série normalisée si l'écart de rayon ≤ 10 % ; les
    pièces déjà arrondies restent fixées pendant les essais suivants."""
    fixes = set()
    for j in range(len(ch.pieces)):
        L, k0, k1 = ch.pieces[j]
        if abs(k1 - k0) > 1e-12 or abs(k0) < 1e-12:
            continue
        R = 1.0 / abs(k0)
        fleche = L * L * abs(k0) / 8.0
        essais = []
        if R > serie[-1] and fleche <= tol / 4.0:
            essais.append((0.0, fleche))
        elif fleche < tol / 2.0:
            essais.append((0.0, 0.0))
        Rn = min(serie, key=lambda r: abs(r - R))
        if abs(Rn - R) / R <= 0.10 and R <= serie[-1]:
            essais.append((math.copysign(1.0 / Rn, k0), 0.0))
        for kn, marge in essais:
            pieces = [list(p) for p in ch.pieces]
            pieces[j] = [L, kn, kn]
            libres = [i != j and i not in fixes for i in range(len(pieces))]
            c2, _, _ = ajuster_lm(Chaine(ch.x0, ch.y0, ch.h0, pieces), D, cons, lmin, libres_k=libres, huber=hub, rmin=rmin, maxit=30)
            d1, d2 = ecarts(c2, D, P)
            if accepte(d1, d2, tol + marge):
                ch = c2
                fixes.add(j)
                break
    return ch


# --------------------------------------------------------------------------- polyligne complète
def densifier(chaines, e=E_FLECHE, pas_max=0.5):
    """Polyligne densifiée (flèche ≤ e, pas ≤ pas_max), sommet à chaque raccord ; abscisse cumulée."""
    pts, us = [], []
    base = 0.0
    for ci, ch in enumerate(chaines):
        u_list = []
        for j, (L, k0, k1) in enumerate(ch.pieces):
            a, b = ch.bornes[j], ch.bornes[j + 1]
            kmax = max(abs(k0), abs(k1))
            if kmax > 1e-12:
                R = 1.0 / kmax
                c = 2.0 * math.sqrt(max(2 * R * e - e * e, 1e-12))
                pas = min(pas_max or 1e9, c) if R > e else 0.01
            else:
                pas = pas_max or 1e9
            n = max(1, int(math.ceil((b - a) / pas - 1e-9)))
            u_list.append(np.linspace(a, b, n + 1)[:-1])
        u_list.append(np.array([ch.L]))
        u = np.concatenate(u_list)
        C, _, _ = ch.evaluer(u)
        if ci > 0:
            C, u = C[1:], u[1:]
        pts.append(C)
        us.append(u + base)
        base += ch.L
    return np.vstack(pts), np.concatenate(us)


def ajuster_polyligne(P, tol, debut=None, fin=None, cap_debut=None, cap_fin=None, ferme=False,
                      lmin=0.5, rmin=0.2, seuil_coin=SEUIL_COIN_DEG, serie=SERIE_RAYONS, max_coins_ajoutes=6):
    """Régularise une polyligne : coins voulus (G0) puis tronçons G1. Renvoie un dict :
    chaines (une par tronçon), coins (points), polyligne densifiée, écarts, statut. Si un tronçon reste hors
    tolérance, le sommet le plus cassé de ce tronçon devient un coin (au plus max_coins_ajoutes fois) ;
    en dernier recours la polyligne nettoyée est gardée telle quelle (statut « source_gardee »)."""
    P0 = nettoyer(P)
    if len(P0) < 2:
        return None
    if ferme and np.hypot(*(P0[0] - P0[-1])) > 1e-9:
        P0 = np.vstack([P0, P0[:1]])
    if ferme and len(P0) < 4:
        ferme = False
    ic = coins(P0, tol, seuil_coin, ferme=ferme, lmin=lmin)
    if ferme and ic:
        k = ic[0]
        P0 = np.vstack([P0[k:-1], P0[:k + 1]])               # l'anneau commence au premier coin
        ic = sorted({(i - k) % (len(P0) - 1) for i in ic} - {0})
    ajoutes = []
    for essai in range(max_coins_ajoutes + 1):
        r = _ajuster_entre_coins(P0, ic, tol, debut, fin, cap_debut, cap_fin, ferme, lmin, rmin, serie)
        if r["ok"] or essai == max_coins_ajoutes:
            break
        # tronçon le plus mauvais : son sommet le plus dévié devient un coin
        j = int(np.argmax([x["ecart"] for x in r["troncons"]]))
        i0, i1 = r["bornes"][j], r["bornes"][j + 1]
        if i1 - i0 < 2:
            break
        ang = []
        for i in range(i0 + 1, i1):
            u, v = P0[i] - P0[i - 1], P0[i + 1] - P0[i]
            ang.append(abs(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)))
        i = i0 + 1 + int(np.argmax(ang))
        ic = sorted(set(ic) | {i})
        ajoutes.append(i)
    statut = "regularise" if r["ok"] else "hors_tolerance"
    if not r["ok"] and r["ecart_max"] > 3 * tol:
        # dernier recours : polyligne source nettoyée (droites, coins à chaque sommet), signalée
        ch = []
        for q0, q1 in zip(P0[:-1], P0[1:]):
            h = math.atan2(q1[1] - q0[1], q1[0] - q0[0])
            ch.append(Chaine(q0[0], q0[1], h, [[float(np.hypot(*(q1 - q0))), 0.0, 0.0]]))
        poly, u = densifier(ch)
        r = {"chaines": ch, "coins": list(P0[1:-1]), "polyligne": poly, "u": u, "d1": np.zeros(1), "d2": np.zeros(1),
             "ok": False, "ecart_max": 0.0, "ecart_p99": 0.0, "tours": r["tours"], "bornes": list(range(len(P0)))}
        statut = "source_gardee"
    r.update(source=P0, ferme=ferme, statut=statut, coins_ajoutes=len(ajoutes))
    return r


def _ajuster_entre_coins(P0, ic, tol, debut, fin, cap_debut, cap_fin, ferme, lmin, rmin, serie):
    bornes = [0] + list(ic) + [len(P0) - 1]
    ferme_lisse = ferme and not ic
    noeuds = [None] * len(bornes)
    if ferme and not ferme_lisse:
        noeuds[0] = noeuds[-1] = _coin(P0, 0, tol, ferme=True,
                                       lo=bornes[-2] if len(bornes) > 2 else None,
                                       hi=bornes[1] if len(bornes) > 2 else None)
    if debut is not None and not ferme:
        noeuds[0] = np.asarray(debut, float)
    if fin is not None and not ferme:
        noeuds[-1] = np.asarray(fin, float)
    for j in range(1, len(bornes) - 1):
        noeuds[j] = _coin(P0, bornes[j], tol, lo=bornes[j - 1], hi=bornes[j + 1])
    chaines, res = [], []
    for j in range(len(bornes) - 1):
        seg = P0[bornes[j]:bornes[j + 1] + 1]
        cons = Contraintes(debut=noeuds[j], fin=noeuds[j + 1],
                           cap_debut=cap_debut if (j == 0 and not ferme) else None,
                           cap_fin=cap_fin if (j == len(bornes) - 2 and not ferme) else None,
                           ferme=ferme_lisse)
        r = ajuster_troncon(seg, tol, cons, lmin=lmin, rmin=rmin, serie=serie)
        r["ecart"] = float(max(r["d1"].max(), r["d2"].max()))
        chaines.append(r["chaine"])
        res.append(r)
    d1 = np.concatenate([r["d1"] for r in res])
    d2 = np.concatenate([r["d2"] for r in res])
    poly, u = densifier(chaines)
    if ferme:
        poly[-1] = poly[0]
    return {"chaines": chaines, "coins": [noeuds[i] if noeuds[i] is not None else P0[b] for i, b in enumerate(bornes)][1:-1],
            "polyligne": poly, "u": u, "d1": d1, "d2": d2, "ok": accepte(d1, d2, tol),
            "ecart_max": float(max(d1.max(), d2.max())), "ecart_p99": float(np.percentile(np.r_[d1, d2], 99)),
            "tours": sum(r["tours"] for r in res), "troncons": res, "bornes": bornes}


def _coin(P, i, tol, ferme=False, lo=None, hi=None):
    """Coin = intersection des droites ajustées de part et d'autre du sommet i, fenêtres de ≤ LONG_COIN_M
    bornées aux coins voisins (indices lo, hi) ; gardée si ≤ 1,5 T du sommet levé, sinon le sommet."""
    n = len(P)
    S = abscisse(P)
    if ferme:                                              # anneau : sommet 0 = sommet n-1
        L = S[-1]
        sa = S[(lo if lo is not None else n - 1)] if lo is not None else 0.0
        Qa = P[(S >= max(L - LONG_COIN_M, sa)) & (S <= L)]
        hb = S[hi] if hi is not None else L
        Qb = P[(S >= 0.0) & (S <= min(LONG_COIN_M, hb))]
    else:
        s_lo = S[lo] if lo is not None else S[0]
        s_hi = S[hi] if hi is not None else S[-1]
        Qa = P[(S >= max(S[i] - LONG_COIN_M, s_lo)) & (S <= S[i])]
        Qb = P[(S >= S[i]) & (S <= min(S[i] + LONG_COIN_M, s_hi))]
    if len(Qa) < 2 or len(Qb) < 2:
        return P[i].copy()
    ca, da, _ = droite_tls(Qa)
    cb, db, _ = droite_tls(Qb)
    den = da[0] * db[1] - da[1] * db[0]
    if abs(den) < 1e-6:
        return P[i].copy()
    t = ((cb - ca)[0] * db[1] - (cb - ca)[1] * db[0]) / den
    X = ca + t * da
    return X if np.hypot(*(X - P[i])) <= 1.5 * tol else P[i].copy()


# --------------------------------------------------------------------------- mesures
def cassures(P, d=0.5):
    """Cassure à chaque sommet intérieur : |2·T(d) − T(2d)| (degrés), T(x) = déviation entre les cordes
    [s−x, s] et [s, s+x]. Nulle sur une droite, un arc et un raccord G1 ; égale à l'angle d'un coin."""
    P = np.asarray(P, float)
    S = abscisse(P)
    if len(P) < 3 or S[-1] < 4 * d:
        return np.zeros(0), np.zeros(0)
    m = (S >= 2 * d) & (S <= S[-1] - 2 * d)
    s = S[m]

    def pt(x):
        i = np.clip(np.searchsorted(S, x, side="right") - 1, 0, len(P) - 2)
        t = ((x - S[i]) / np.maximum(S[i + 1] - S[i], 1e-12))[:, None]
        return P[i] * (1 - t) + P[i + 1] * t

    c = pt(s)

    def dev(x):
        a, b = c - pt(s - x), pt(s + x) - c
        return np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1))

    return s, np.degrees(np.abs(wrap(2 * dev(d) - dev(2 * d))))


def points_de_cassure(P, seuil=2.0, d=0.5):
    """Nombre de cassures distinctes > seuil (maxima locaux espacés d'au moins 1 m)."""
    s, k = cassures(P, d)
    if not len(s):
        return 0, []
    idx = np.nonzero(k > seuil)[0]
    out = []
    for i in idx:
        if out and s[i] - s[out[-1]] < 1.0:
            if k[i] > k[out[-1]]:
                out[-1] = i
            continue
        out.append(i)
    return len(out), [float(k[i]) for i in out]


def peigne(chaines, pas=0.25):
    """Peigne de courbure : (points, normales, courbure) échantillonnés le long des chaînes."""
    P, N, K = [], [], []
    for ch in chaines:
        u = np.linspace(0.0, ch.L, max(2, int(ch.L / pas) + 1))
        C, h, k = ch.evaluer(u)
        P.append(C)
        N.append(np.c_[-np.sin(h), np.cos(h)])
        K.append(k)
    return np.vstack(P), np.vstack(N), np.concatenate(K)


def sauts_de_cap(chaines):
    """Sauts de cap (degrés) aux raccords internes des chaînes (0 par construction) et entre chaînes (coins)."""
    internes, entre = [], []
    for ch in chaines:
        for j in range(1, len(ch.pieces)):
            internes.append(0.0)
    for a, b in zip(chaines[:-1], chaines[1:]):
        entre.append(abs(math.degrees(float(wrap(b.h0 - a.fin()[1])))))
    return internes, entre


def sauts_de_courbure(chaines):
    """Sauts de courbure (1/m) aux raccords internes (G2 non exigé : mesuré)."""
    out = []
    for ch in chaines:
        for (_, _, ka), (_, kb, _) in zip(ch.pieces[:-1], ch.pieces[1:]):
            out.append(abs(kb - ka))
    return out


def description_primitives(chaines, vers_l93, nd=4):
    """Liste sérialisable des primitives : type, s0, s1, départ (L93), cap, courbures, rayon."""
    out = []
    base = 0.0
    for ci, ch in enumerate(chaines):
        for j, (L, k0, k1) in enumerate(ch.pieces):
            a = ch.bornes[j]
            C, h, _ = ch.evaluer(np.array([a]))
            x, y = vers_l93(C)[0]
            t = type_piece(k0, k1)
            e = {"type": t, "s0": round(base + a, 6), "s1": round(base + a + L, 6),
                 "x0": round(float(x), nd), "y0": round(float(y), nd),
                 "cap0_rad": round(float(h[0]), 9), "k0": round(k0, 9)}
            if t == "clothoide":
                e["k1"] = round(k1, 9)
            if t == "arc":
                e["rayon_m"] = round(1.0 / abs(k0), 4)
            if j == 0 and ci > 0:
                e["coin"] = True
            out.append(e)
        base += ch.L
    return out
