"""Partition plane vectorielle du site (numpy seul, sans shapely) : arrangement de polylignes ->
faces (polygones avec trous) et arêtes étiquetées (source de chaque limite).

Règles appliquées (regles_conception.json) :
- TQ-SOL-001 : topologie préparée avant Houdini : coordonnées calées sur une grille de 1 mm, arcs
  partagés identiques (une arête n'existe qu'une fois), sommets à moins de 5 mm fusionnés, contraintes
  quasi parallèles à moins de 6 cm de priorité inférieure retirées (`filtrer_paralleles`), aucune
  face d'aire nulle ; contrôle aire(union) = somme des aires (faces disjointes par construction).
- TQ-SOL-003 : les lignes de rupture (arêtes avant et arrière des bordures, limites de revêtement,
  coupes de jonction, bords de rampe) sont des arêtes de la partition.

Méthode : segments -> recollement des extrémités pendantes (accrochage ≤ 5 cm sur un segment,
prolongement ≤ `prolonger` m dans l'axe jusqu'au premier segment rencontré) -> intersections
(grille de hachage) -> découpe -> nœuds fusionnés à 5 mm -> élagage des arêtes pendantes ->
demi-arêtes triées par angle -> faces (cycles à gauche, anti-horaires) -> rattachement des
composantes isolées comme trous de la plus petite face qui les contient.
"""
import math
from collections import defaultdict

import numpy as np

from commun import abscisses, aire_signee, dans_polygone, distance_segments, point_a

GRILLE = 0.001        # calage des coordonnées (m)
RUPTURES = {"bordure_arriere", "bordure_bout", "batiment", "emprise"}   # = surfaces.DISCONTINUES
FUSION = 0.005        # sommets fusionnés (m)


def _segments(lignes):
    """lignes : [(polyligne (N, 2), etiquette)] -> A, B (M, 2), indice de ligne (M,)."""
    A, B, L = [], [], []
    for k, (P, _) in enumerate(lignes):
        P = np.asarray(P, dtype=np.float64)[:, :2]
        if len(P) < 2:
            continue
        a, b = P[:-1], P[1:]
        ok = np.hypot(*(b - a).T) > 1e-6
        A.append(a[ok])
        B.append(b[ok])
        L.append(np.full(int(ok.sum()), k))
    if not A:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0, int)
    return np.vstack(A), np.vstack(B), np.concatenate(L)


def _hachage(A, B, cell):
    """Paires candidates (i < j) de segments dont les boîtes partagent une cellule de grille."""
    x0 = np.minimum(A[:, 0], B[:, 0]); x1 = np.maximum(A[:, 0], B[:, 0])
    y0 = np.minimum(A[:, 1], B[:, 1]); y1 = np.maximum(A[:, 1], B[:, 1])
    cx0, cx1 = np.floor(x0 / cell).astype(int), np.floor(x1 / cell).astype(int)
    cy0, cy1 = np.floor(y0 / cell).astype(int), np.floor(y1 / cell).astype(int)
    ids, cles = [], []
    for i in range(len(A)):
        for cx in range(cx0[i], cx1[i] + 1):
            for cy in range(cy0[i], cy1[i] + 1):
                ids.append(i)
                cles.append(cx * 1000003 + cy)
    ids = np.array(ids)
    cles = np.array(cles, dtype=np.int64)
    o = np.lexsort((ids, cles))
    ids, cles = ids[o], cles[o]
    paires = set()
    debut = 0
    for k in range(1, len(cles) + 1):
        if k == len(cles) or cles[k] != cles[debut]:
            g = ids[debut:k]
            if len(g) > 1:
                for a in range(len(g)):
                    for b in range(a + 1, len(g)):
                        paires.add((int(g[a]), int(g[b])) if g[a] < g[b] else (int(g[b]), int(g[a])))
            debut = k
    if not paires:
        return np.zeros(0, int), np.zeros(0, int)
    p = np.array(sorted(paires))
    return p[:, 0], p[:, 1]


def _intersections(A, B, I, J, tol=1e-9):
    """Paramètres d'intersection (t sur I, u sur J) des paires de segments qui se coupent ou se
    touchent (extrémités comprises) ; segments colinéaires : recouvrement projeté."""
    p, r = A[I], B[I] - A[I]
    q, s = A[J], B[J] - A[J]
    den = r[:, 0] * s[:, 1] - r[:, 1] * s[:, 0]
    qp = q - p
    out_i, out_t, out_j, out_u = [], [], [], []
    ok = np.abs(den) > 1e-12
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / den
        u = (qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]) / den
    lr = np.hypot(*r.T)
    ls = np.hypot(*s.T)
    et = 1e-4 / np.maximum(lr, 1e-9)
    eu = 1e-4 / np.maximum(ls, 1e-9)
    m = ok & (t >= -et) & (t <= 1 + et) & (u >= -eu) & (u <= 1 + eu)
    out_i.append(I[m]); out_t.append(np.clip(t[m], 0, 1)); out_j.append(J[m]); out_u.append(np.clip(u[m], 0, 1))
    # colinéaires (recouvrements) : extrémités de l'un projetées sur l'autre
    col = ~ok
    if col.any():
        ic, jc = I[col], J[col]
        for (a_i, a_j) in ((ic, jc), (jc, ic)):
            pa, ra = A[a_i], B[a_i] - A[a_i]
            la2 = np.maximum(np.einsum("ij,ij->i", ra, ra), 1e-18)
            for ext in (A[a_j], B[a_j]):
                w = ext - pa
                tt = np.einsum("ij,ij->i", w, ra) / la2
                d = np.abs(w[:, 0] * ra[:, 1] - w[:, 1] * ra[:, 0]) / np.sqrt(la2)
                mm = (d < 1e-4) & (tt > 0) & (tt < 1)
                out_i.append(a_i[mm]); out_t.append(tt[mm])
                out_j.append(np.zeros(0, int)); out_u.append(np.zeros(0))
    return (np.concatenate(out_i), np.concatenate(out_t), np.concatenate(out_j), np.concatenate(out_u))


def filtrer_paralleles(P, references, dmax=0.06, cos_min=0.95, pas=0.05, zones=(), lmin=0.10):
    """Morceaux de la polyligne P qui ne doublent pas une ligne de priorité supérieure (à moins de
    dmax et parallèle) et ne sont pas dans une zone d'exclusion (emprises de bordure) :
    [polyligne]. TQ-SOL-001 : pas de contraintes quasi confondues (aiguilles)."""
    P = np.asarray(P, dtype=np.float64)
    L = float(abscisses(P)[-1])
    if L < 1e-6:
        return []
    n = max(2, int(math.ceil(L / pas)) + 1)
    s = np.linspace(0.0, L, n)
    q, tg = point_a(P, s)
    garde = np.ones(n, bool)
    if references is not None and len(references[0]):
        RA, RB = references
        x0, y0 = q.min(axis=0) - dmax - 0.01
        x1, y1 = q.max(axis=0) + dmax + 0.01
        sel = ~((np.maximum(RA[:, 0], RB[:, 0]) < x0) | (np.minimum(RA[:, 0], RB[:, 0]) > x1)
                | (np.maximum(RA[:, 1], RB[:, 1]) < y0) | (np.minimum(RA[:, 1], RB[:, 1]) > y1))
        if sel.any():
            ra, rb = RA[sel], RB[sel]
            d, j, _ = distance_segments(q, ra, rb)
            dr = (rb[j] - ra[j]) / np.maximum(np.hypot(*(rb[j] - ra[j]).T), 1e-12)[:, None]
            par = np.abs(np.einsum("ij,ij->i", tg, dr)) >= cos_min
            garde &= ~((d <= dmax) & par)
            garde &= ~(d <= 0.004)              # sur la ligne de référence (même arc levé deux fois)
    for z in zones:
        bx0, by0 = z.min(axis=0)
        bx1, by1 = z.max(axis=0)
        m = (q[:, 0] >= bx0) & (q[:, 0] <= bx1) & (q[:, 1] >= by0) & (q[:, 1] <= by1)
        if m.any():
            dd = np.zeros(n, bool)
            dd[m] = dans_polygone(q[m], [z])
            garde &= ~dd
    out = []
    i = 0
    while i < n:
        if garde[i]:
            j = i
            while j + 1 < n and garde[j + 1]:
                j += 1
            if s[j] - s[i] >= lmin:
                a, _ = point_a(P, s[i])
                b, _ = point_a(P, s[j])
                mid = P[(abscisses(P) > s[i] + 1e-6) & (abscisses(P) < s[j] - 1e-6)]
                out.append(np.vstack([a, mid, b]))
            i = j + 1
        else:
            i += 1
    return out


def _recoller(lignes, A, B, L, accroche=0.05, prolonger=1.5):
    """Extrémités pendantes : accrochage sur le segment le plus proche (≤ accroche) ou prolongement
    dans l'axe (≤ prolonger) jusqu'au premier segment rencontré ; renvoie les lignes modifiées et le
    nombre d'opérations."""
    out = [(np.asarray(P, dtype=np.float64).copy(), e) for P, e in lignes]
    n_acc, n_pro = 0, 0
    codes = {}
    gl = np.array([codes.setdefault(e.get("groupe"), len(codes)) if e.get("groupe") is not None else -1
                   for _, e in lignes], dtype=np.int64)
    gseg = gl[L] if len(L) else np.zeros(0, np.int64)
    r = max(accroche, prolonger) + 0.01
    bx0, bx1 = np.minimum(A[:, 0], B[:, 0]) - r, np.maximum(A[:, 0], B[:, 0]) + r
    by0, by1 = np.minimum(A[:, 1], B[:, 1]) - r, np.maximum(A[:, 1], B[:, 1]) + r
    for k, (P, e) in enumerate(out):
        if len(P) < 2 or e.get("ferme") or e.get("fixe"):
            continue
        for bout in (0, -1):
            q = P[bout]
            voisin = P[1] if bout == 0 else P[-2]
            # les lignes du même groupe (arêtes avant, arrière et bouts d'une même bordure) ne
            # raccordent pas une extrémité : une bordure qui s'arrête à 0,3 m d'un bâtiment laisse
            # sinon passer la chaussée vers le trottoir autour de son bout
            g = gl[k]
            pres = (bx0 <= q[0]) & (q[0] <= bx1) & (by0 <= q[1]) & (q[1] <= by1)   # boîtes voisines seulement
            autres = pres & ((L != k) if g < 0 else ((L != k) & (gseg != g)))
            if not autres.any():
                continue
            d, j, pr = distance_segments(q[None], A[autres], B[autres])
            if d[0] <= 1e-6:
                continue                                    # déjà raccordée
            if d[0] <= accroche:
                # segment de raccord ajouté (l'extrémité d'origine reste : elle peut porter d'autres
                # lignes du même groupe, ex. le bout d'une emprise de bordure)
                P = np.vstack([pr[:1], P]) if bout == 0 else np.vstack([P, pr[:1]])
                out[k] = (P, e)
                n_acc += 1
                continue
            if not e.get("prolonger", True) or prolonger <= 0:
                continue
            u = q - voisin
            nu = math.hypot(*u)
            if nu < 1e-9:
                continue
            u /= nu
            # rayon q -> q + u·prolonger contre les segments des autres lignes
            aa, bb = A[autres], B[autres]
            s_ = bb - aa
            den = u[0] * s_[:, 1] - u[1] * s_[:, 0]
            ok = np.abs(den) > 1e-12
            ap = aa - q
            with np.errstate(divide="ignore", invalid="ignore"):
                t = (ap[:, 0] * s_[:, 1] - ap[:, 1] * s_[:, 0]) / den
                w = (ap[:, 0] * u[1] - ap[:, 1] * u[0]) / den
            m = ok & (t > 1e-6) & (t <= prolonger) & (w >= 0) & (w <= 1)
            if m.any():
                tmin = float(t[m].min())
                p_new = q + u * tmin
                P = np.vstack([p_new[None], P]) if bout == 0 else np.vstack([P, p_new[None]])
                out[k] = (P, e)
                n_pro += 1
    return out, n_acc, n_pro


def arrangement(lignes, prolonger=1.5, accroche=0.05, cell=4.0):
    """Arrangement plan des polylignes. lignes : [(polyligne (N, 2) locale, etiquette dict)] ; une
    étiquette peut porter `prolonger: False` (bords d'emprise) et `ferme: True` (anneau).
    Renvoie {"noeuds" (K, 2), "aretes" [(u, v, {indices de lignes})], "faces" [{anneaux, aretes}],
    "stats"}. Faces : anneau extérieur anti-horaire + trous horaires (tableaux sans fermeture)."""
    lignes = [(np.round(np.asarray(P, dtype=np.float64)[:, :2] / GRILLE) * GRILLE, e) for P, e in lignes]
    A, B, L = _segments(lignes)
    lignes, n_acc, n_pro = _recoller(lignes, A, B, L, accroche, prolonger)
    lignes = [(np.round(P / GRILLE) * GRILLE, e) for P, e in lignes]
    A, B, L = _segments(lignes)
    I, J = _hachage(A, B, cell)
    ii, tt, jj, uu = _intersections(A, B, I, J)
    coupes = defaultdict(list)
    for i, t in zip(ii.tolist(), tt.tolist()):
        coupes[i].append(t)
    for j, u in zip(jj.tolist(), uu.tolist()):
        coupes[j].append(u)
    # jonctions en T : une extrémité de segment à moins de 1,5 mm d'un autre segment le coupe
    # (le calage à 1 mm peut laisser l'extrémité prolongée à quelques dixièmes de mm de la ligne)
    for (a_, b_) in ((I, J), (J, I)):
        for ext in (A[a_], B[a_]):
            ab = B[b_] - A[b_]
            l2 = np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-18)
            w = ext - A[b_]
            u = np.einsum("ij,ij->i", w, ab) / l2
            d = np.abs(w[:, 0] * ab[:, 1] - w[:, 1] * ab[:, 0]) / np.sqrt(l2)
            m = (d <= 1.5e-3) & (u > 1e-6) & (u < 1 - 1e-6)
            for j, uu_ in zip(b_[m].tolist(), u[m].tolist()):
                coupes[j].append(uu_)
    # découpe des segments
    pts, aretes_l = [], []
    for k in range(len(A)):
        ts = sorted(set([0.0, 1.0] + [min(1.0, max(0.0, t)) for t in coupes.get(k, [])]))
        a, b = A[k], B[k]
        prev = a
        for t in ts[1:]:
            q = a + (b - a) * t
            pts.append((prev, q, int(L[k])))
            prev = q
    P0 = np.array([p[0] for p in pts])
    P1 = np.array([p[1] for p in pts])
    lig = np.array([p[2] for p in pts])
    # nœuds : grille de 1 mm puis fusion à 5 mm (union-find sur grille de hachage)
    tous = np.vstack([P0, P1])
    cles = np.round(tous / GRILLE).astype(np.int64)
    uniq, inv = np.unique(cles, axis=0, return_inverse=True)
    inv = inv.ravel()
    coords = uniq.astype(np.float64) * GRILLE
    parent = np.arange(len(coords))

    def rac(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    cel = np.floor(coords / FUSION).astype(np.int64)
    par_cel = defaultdict(list)
    for i, (cx, cy) in enumerate(cel.tolist()):
        par_cel[(cx, cy)].append(i)
    for (cx, cy), membres in sorted(par_cel.items()):
        voisins = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                voisins += par_cel.get((cx + dx, cy + dy), [])
        for i in membres:
            for j in voisins:
                if j > i and np.hypot(*(coords[i] - coords[j])) < FUSION:
                    ri, rj = rac(i), rac(j)
                    if ri != rj:
                        parent[max(ri, rj)] = min(ri, rj)
    racines = np.array([rac(i) for i in range(len(coords))])
    nouv, idx = np.unique(racines, return_inverse=True)
    idx = idx.ravel()
    noeuds = coords[nouv]
    n0 = idx[inv[:len(P0)]]
    n1 = idx[inv[len(P0):]]
    ar = {}
    for a, b, l in zip(n0.tolist(), n1.tolist(), lig.tolist()):
        if a == b:
            continue
        c = (a, b) if a < b else (b, a)
        ar.setdefault(c, set()).add(l)
    # élagage des arêtes pendantes
    adj = defaultdict(set)
    for (a, b) in ar:
        adj[a].add(b)
        adj[b].add(a)
    pile = [v for v in adj if len(adj[v]) == 1]
    n_elague = 0
    while pile:
        v = pile.pop()
        if len(adj[v]) != 1:
            continue
        w = next(iter(adj[v]))
        adj[v].discard(w)
        adj[w].discard(v)
        ar.pop((v, w) if v < w else (w, v), None)
        n_elague += 1
        if len(adj[w]) == 1:
            pile.append(w)
    faces = _faces(noeuds, ar)
    faces, n_ecl = _fusionner_eclats(noeuds, ar, faces, lignes, adj)
    return {"noeuds": noeuds, "aretes": ar, "faces": faces, "lignes": lignes,
            "stats": {"segments": int(len(A)), "accroches": n_acc, "prolongements": n_pro,
                      "aretes": len(ar), "aretes_elaguees": n_elague, "eclats_fusionnes": n_ecl,
                      "faces": len(faces)}}


def _elaguer(ar, adj, pile):
    while pile:
        v = pile.pop()
        if len(adj[v]) != 1:
            continue
        w = next(iter(adj[v]))
        adj[v].discard(w)
        adj[w].discard(v)
        ar.pop((v, w) if v < w else (w, v), None)
        if len(adj[w]) == 1:
            pile.append(w)


def _fusionner_eclats(noeuds, ar, faces, lignes, adj, aire_min=0.01, largeur_min=0.004):
    """TQ-SOL-001 (aucune face d'aire nulle) : chaque éclat (aire < 0,01 m² ou largeur moyenne
    2·aire/périmètre < 4 mm) est fusionné avec sa voisine en retirant l'arête commune la plus longue,
    de préférence une limite continue (jamais une rupture de niveau si une limite continue existe :
    les régions de nivellement ne sont pas modifiées) ; les arêtes devenues internes sont retirées."""
    n = 0
    for _ in range(6):
        gauche = {he: k for k, f in enumerate(faces) for cyc in f["aretes"] for he in cyc}
        retirer, touches = [], set()
        # arêtes bordées par la même face des deux côtés (antennes) : retirées
        for (u, v) in sorted(ar):
            if gauche.get((u, v)) is not None and gauche.get((u, v)) == gauche.get((v, u)):
                retirer.append((u, v))
        for k, f in enumerate(faces):
            r = f["anneaux"][0]
            per = float(np.hypot(*(np.roll(r, -1, axis=0) - r).T).sum())
            if f["aire"] >= aire_min and 2.0 * f["aire"] / max(per, 1e-12) >= largeur_min:
                continue
            if k in touches:
                continue
            best = None
            for (u, v) in f["aretes"][0]:
                o = gauche.get((v, u))
                if o is None or o == k or o in touches:
                    continue
                c = (u, v) if u < v else (v, u)
                rupture = any(lignes[l][1].get("src") in RUPTURES for l in ar.get(c, ()))
                cle = (rupture, -float(np.hypot(*(noeuds[u] - noeuds[v]))), c, o)
                if best is None or cle < best:
                    best = cle
            if best is not None:
                retirer.append(best[2])
                touches |= {k, best[3]}
                n += 1
        if not retirer:
            break
        pile = []
        for c in sorted(set(retirer)):
            if ar.pop(c, None) is not None:
                adj[c[0]].discard(c[1])
                adj[c[1]].discard(c[0])
                pile += [x for x in c if len(adj[x]) == 1]
        _elaguer(ar, adj, pile)
        faces = _faces(noeuds, ar)
    return faces, n


def _faces(noeuds, ar):
    """Faces (cycles à gauche) de la carte plane : [{anneaux, aretes, aire}]."""
    sortants = defaultdict(list)
    for (a, b) in ar:
        sortants[a].append(b)
        sortants[b].append(a)
    ordre = {}
    for v, ws in sortants.items():
        d = noeuds[ws] - noeuds[v]
        ang = np.arctan2(d[:, 1], d[:, 0])
        o = np.argsort(ang, kind="stable")
        ordre[v] = [ws[i] for i in o]
    pos = {}
    for v, ws in ordre.items():
        for k, w in enumerate(ws):
            pos[(v, w)] = k
    vu = set()
    cycles = []
    for (a, b) in sorted(ar):
        for he in ((a, b), (b, a)):
            if he in vu:
                continue
            cyc = []
            u, v = he
            while (u, v) not in vu:
                vu.add((u, v))
                cyc.append((u, v))
                ws = ordre[v]
                k = pos[(v, u)]
                w = ws[(k - 1) % len(ws)]
                u, v = v, w
            cycles.append(cyc)
    pos_faces, neg = [], []
    for cyc in cycles:
        r = noeuds[[u for u, _ in cyc]]
        a = aire_signee(r)
        (pos_faces if a > 1e-9 else neg).append((a, r, cyc))
    # composantes connexes (pour rattacher les cycles extérieurs comme trous)
    comp = {}
    cid = 0
    for v0 in sorted(sortants):
        if v0 in comp:
            continue
        pile = [v0]
        comp[v0] = cid
        while pile:
            v = pile.pop()
            for w in sortants[v]:
                if w not in comp:
                    comp[w] = cid
                    pile.append(w)
        cid += 1
    faces = [{"anneaux": [r], "aretes": [cyc], "aire": a, "comp": comp[cyc[0][0]]} for a, r, cyc in pos_faces]
    faces.sort(key=lambda f: -f["aire"])
    # cycle extérieur de chaque composante : rattaché comme trou à la plus petite face d'une AUTRE
    # composante qui le contient (sinon : contour extérieur du site)
    for a, r, cyc in sorted(neg, key=lambda x: x[0]):
        c = comp[cyc[0][0]]
        q = r[:1]
        hote = None
        for f in sorted(faces, key=lambda f: f["aire"]):
            if f["comp"] == c:
                continue
            ext = f["anneaux"][0]
            if q[0, 0] < ext[:, 0].min() or q[0, 0] > ext[:, 0].max() or q[0, 1] < ext[:, 1].min() or q[0, 1] > ext[:, 1].max():
                continue
            if dans_polygone(q, [ext])[0] and not any(dans_polygone(q, [t])[0] for t in f["anneaux"][1:]):
                hote = f
                break
        if hote is not None:
            hote["anneaux"].append(r)
            hote["aretes"].append(cyc)
            hote["aire"] += a
    for f in faces:
        f["aire"] = abs(aire_signee(f["anneaux"][0])) - sum(abs(aire_signee(t)) for t in f["anneaux"][1:])
    return faces


def point_interieur(anneaux, pas=0.05):
    """Point intérieur garanti (hors trous) : centre de la plus longue corde horizontale intérieure,
    balayée sur plusieurs ordonnées."""
    ext = anneaux[0]
    y0, y1 = ext[:, 1].min(), ext[:, 1].max()
    meilleur, best_l = None, -1.0
    for f in np.linspace(0.1, 0.9, 9):
        y = y0 + (y1 - y0) * f
        xs = []
        for r in anneaux:
            a, b = r, np.roll(r, -1, axis=0)
            m = (a[:, 1] > y) != (b[:, 1] > y)
            with np.errstate(divide="ignore", invalid="ignore"):
                x = a[m, 0] + (y - a[m, 1]) * (b[m, 0] - a[m, 0]) / (b[m, 1] - a[m, 1])
            xs += x.tolist()
        xs = sorted(xs)
        for k in range(0, len(xs) - 1, 2):
            l = xs[k + 1] - xs[k]
            if l > best_l:
                best_l, meilleur = l, np.array([0.5 * (xs[k] + xs[k + 1]), y])
    return meilleur if meilleur is not None else ext.mean(axis=0)


def echantillons(anneaux, pas, n_max=4000):
    """Points intérieurs d'une face (grille régulière, au moins un point intérieur)."""
    ext = anneaux[0]
    x0, y0 = ext.min(axis=0)
    x1, y1 = ext.max(axis=0)
    aire = abs(aire_signee(ext))
    pas = max(pas, math.sqrt(max(aire, 1e-6) / n_max))
    xs = np.arange(math.floor(x0 / pas) * pas + pas / 2, x1, pas)
    ys = np.arange(math.floor(y0 / pas) * pas + pas / 2, y1, pas)
    if len(xs) and len(ys):
        X, Y = np.meshgrid(xs, ys)
        Q = np.c_[X.ravel(), Y.ravel()]
        Q = Q[dans_polygone(Q, anneaux)]
        if len(Q):
            return Q
    return point_interieur(anneaux)[None]


def masque_face(anneaux, x0, y1, pas, nx, ny):
    """Masque exact (règle pair-impair, centres de cellule) d'une face sur une grille de nx × ny
    cellules : cellule (r, c) de centre (x0 + (c + ½)·pas, y1 − (r + ½)·pas). Balayage par lignes,
    robuste aux anneaux pincés (sommets répétés, arêtes parcourues deux fois)."""
    A = np.vstack([r for r in anneaux])
    B = np.vstack([np.roll(r, -1, axis=0) for r in anneaux])
    m = np.zeros((ny, nx), dtype=bool)
    ymin, ymax = min(A[:, 1].min(), B[:, 1].min()), max(A[:, 1].max(), B[:, 1].max())
    r0 = max(0, int(math.floor((y1 - ymax) / pas - 0.5)))
    r1 = min(ny - 1, int(math.ceil((y1 - ymin) / pas)))
    lo, hi = np.minimum(A[:, 1], B[:, 1]), np.maximum(A[:, 1], B[:, 1])
    o = np.argsort(lo, kind="stable")
    A, B, lo, hi = A[o], B[o], lo[o], hi[o]
    for r in range(r0, r1 + 1):
        y = y1 - (r + 0.5) * pas
        k = np.searchsorted(lo, y, side="right")
        sel = (hi[:k] > y)
        if not sel.any():
            continue
        a, b = A[:k][sel], B[:k][sel]
        x = a[:, 0] + (y - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1])
        x.sort()
        for xa, xb in zip(x[0::2], x[1::2]):
            c0 = max(0, int(math.ceil((xa - x0) / pas - 0.5)))
            c1 = min(nx - 1, int(math.floor((xb - x0) / pas - 0.5)))
            if c1 >= c0:
                m[r, c0:c1 + 1] ^= True
    return m
