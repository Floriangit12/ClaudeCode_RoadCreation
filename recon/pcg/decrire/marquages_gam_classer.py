"""Classement du levé GAM 2026 des marquages (SOL_SIGNALISATION_HORIZONTALE : 409 polylignes, 28 blocs) en
primitives paramétriques (source de rang 1, FUS-SRC-001).

1. Assemblage : les polylignes ouvertes dont les extrémités se touchent (≤ 3 cm) sont chaînées (graphe des
   extrémités ; un nœud de degré ≠ 2 coupe la chaîne) ; un cycle donne un anneau (contour levé en morceaux :
   flèches et bandes dessinées segment par segment).
2. Anneaux (contours fermés) : rectangle (remplissage du rectangle minimal ≥ 0,93, 4 sommets) -> bande de zébra
   (largeur 0,40-0,62, longueur ≥ 1,5), carré (0,40-0,62 x 0,40-0,62), tiret ou barre (largeur 0,08-0,35) ;
   triangle -> dent ; flèche -> gabarit IISR ajusté (pose et sens, IoU ≥ 0,55 ; FUS-SNP-004 : la forme posée
   est TOUJOURS le gabarit IISR, décision n° 10) à l'homothétie 1 ou 1/2 (voies cyclables) ; parallélogramme de
   0,5 m -> bande de hachure ; sinon atypique.
3. Chaînes ouvertes : paires de bords (parallèles à ≤ 10°, 0,06-0,25 m, recouvrement ≥ 50 %) -> axe médian +
   largeur levée ; V à 3 sommets (branches 0,4-1,0 m, 60-120°) -> chevron ; ≥ 5 sommets alternés -> zigzag ;
   segment droit de 0,3 à 6,5 m -> segment court (tiret, place de stationnement, bord de hachure) ; plus long ->
   axe de ligne.
4. Petits morceaux groupés (étendue < 1,6 m) : pictogramme dessiné (vélo, flèche cyclable) -> boîte et cap.
5. Blocs : SYMBOLE_VELO (point = centre de la figurine, cap = rotation + 90°), SYMBOLE_PMR (centre, cap =
   rotation + 200° : convention mesurée sur les 10 pictogrammes du site, hauteur 0,79 x échelle),
   SYMBOLE_FLECHE_<DIR> (point = pied de tige, cap = rotation + 90° ; DROIT -> TD, GAUCHE -> TAG, DROITE -> TAD,
   DROIT_GAUCHE -> TD_TAG, DROIT_DROITE -> TD_TAD) ; textes (fme_text) ignorés (noms de rues).
Sortie : classer() -> dict de listes de primitives (repère local), chacune avec ses indices GAM (`gam`).
Tout est déterministe (indices triés, aucun aléa).
"""
import functools
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_commun as M  # noqa: E402
from commun import abscisses, aire_signee, densifier, projeter  # noqa: E402

TOL_NOEUD = 0.03
FLECHES = ("TD", "TAD", "TAG", "TD_TAD", "TD_TAG", "RAB_D", "RAB_G")
BLOC_FLECHE = {"SYMBOLE_FLECHE_DROIT": "TD", "SYMBOLE_FLECHE_GAUCHE": "TAG", "SYMBOLE_FLECHE_DROITE": "TAD",
               "SYMBOLE_FLECHE_DROIT_GAUCHE": "TD_TAG", "SYMBOLE_FLECHE_DROIT_DROITE": "TD_TAD"}
PMR_HAUTEUR_ECHELLE_1 = 0.79      # m (pictogrammes PMR du site à l'échelle 1 du bloc)
PMR_CAP_DECALAGE = 200.0          # cap = rotation + 200° (convention du bloc SYMBOLE_PMR, mesurée)


def ouverte(P):
    return not (len(P) > 3 and float(np.hypot(*(P[0] - P[-1]))) < 0.02)


# --------------------------------------------------------------------------- 1. assemblage
ANGLE_COUPE = 35.0            # déviation au raccord au-delà de laquelle deux polylignes ne sont pas chaînées


def triangles_ouverts():
    """Dents dessinées en traits (plateau, MQ-RAL-001) : paires de polylignes GAM à 2 sommets de 1,5 à 2,6 m qui
    partagent une extrémité (≤ 3 cm) sous un angle de 10 à 40° -> [{gam, sommet, base: (A, B)}]."""
    G = M.gam_lin()
    segs = [k for k, P in enumerate(G) if len(M.dedoublonner(P)) == 2 and 1.5 <= abscisses(P)[-1] <= 2.6]
    # extrémités des autres polylignes (≥ 0,2 m) : une base de dent est libre (une tête de flèche ne l'est pas)
    bouts = np.array([P[i] for k, P in enumerate(G) if abscisses(P)[-1] >= 0.2 for i in (0, -1)])
    proprio = [k for k, P in enumerate(G) if abscisses(P)[-1] >= 0.2 for _ in (0, 1)]

    def libre(X, a, b):
        d = np.hypot(*(bouts - X).T)
        return not any(proprio[i] not in (a, b) for i in np.where(d <= TOL_NOEUD)[0])
    out, pris = [], set()
    for i, a in enumerate(segs):
        if a in pris:
            continue
        Pa = M.dedoublonner(G[a])
        for b in segs[i + 1:]:
            if b in pris:
                continue
            Pb = M.dedoublonner(G[b])
            for ea in (0, -1):
                for eb in (0, -1):
                    if a in pris or b in pris or float(np.hypot(*(Pa[ea] - Pb[eb]))) > TOL_NOEUD:
                        continue
                    s = 0.5 * (Pa[ea] + Pb[eb])
                    A, B = Pa[-1 - ea], Pb[-1 - eb]
                    ua, ub = (A - s) / np.hypot(*(A - s)), (B - s) / np.hypot(*(B - s))
                    ang = math.degrees(math.acos(max(-1.0, min(1.0, float(ua @ ub)))))
                    if 10.0 <= ang <= 40.0 and 0.4 <= float(np.hypot(*(A - B))) <= 1.1 and libre(A, a, b) and libre(B, a, b):
                        out.append({"gam": [a, b], "sommet": s, "base": (A, B)})
                        pris |= {a, b}
    return out


def _deviation(P, Q):
    """Déviation (degrés) au raccord de P (fin) et Q (début)."""
    u = P[-1] - P[-2]
    v = Q[1] - Q[0]
    c = float(u @ v) / max(float(np.hypot(*u) * np.hypot(*v)), 1e-12)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


@functools.lru_cache(maxsize=None)
def assembler():
    """-> (anneaux [(ks, anneau)], chaines [(ks, polyligne)]) en repère local, triés par plus petit indice.
    Cycles purs (tous les nœuds de degré 2) -> anneaux quel que soit l'angle ; ailleurs, chaînage arrêté aux nœuds
    de degré ≠ 2 et aux raccords de plus de ANGLE_COUPE degrés."""
    G = M.gam_lin()
    exclus = {k for t in triangles_ouverts() for k in t["gam"]}
    anneaux, chaines = [], []
    ouv = []
    for k, P in enumerate(G):
        P = M.dedoublonner(P)
        if k in exclus or len(P) < 2 or abscisses(P)[-1] < 1e-3:
            continue
        if not ouverte(P):
            anneaux.append(((k,), P[:-1] if np.allclose(P[0], P[-1]) else P))
        else:
            ouv.append(k)
    bouts = [(k, e, (M.dedoublonner(G[k])[0] if e == 0 else M.dedoublonner(G[k])[-1])) for k in ouv for e in (0, 1)]
    parent = list(range(len(bouts)))

    def f(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    XY = np.array([b[2] for b in bouts]) if bouts else np.zeros((0, 2))
    for i in range(len(bouts)):
        d = np.hypot(*(XY[i + 1:] - XY[i]).T)
        for j in np.where(d <= TOL_NOEUD)[0] + i + 1:
            a, b = f(i), f(int(j))
            if a != b:
                parent[max(a, b)] = min(a, b)
    noeud = {(b[0], b[1]): f(i) for i, b in enumerate(bouts)}
    adj = {}
    for k in ouv:
        for e in (0, 1):
            adj.setdefault(noeud[(k, e)], []).append((k, e))
    deg = {n: len(v) for n, v in adj.items()}

    def poly(k, depuis_e):
        P = M.dedoublonner(G[k])
        return P if depuis_e == 0 else P[::-1]
    # composantes connexes ; cycles purs -> anneaux
    voisins = {k: set() for k in ouv}
    for n, lst in adj.items():
        for k, _ in lst:
            for k2, _ in lst:
                if k2 != k:
                    voisins[k].add(k2)
    vus = set()
    for k0 in ouv:
        if k0 in vus:
            continue
        cc, pile = {k0}, [k0]
        while pile:
            k = pile.pop()
            for k2 in sorted(voisins[k]):
                if k2 not in cc:
                    cc.add(k2)
                    pile.append(k2)
        noeuds = {noeud[(k, e)] for k in cc for e in (0, 1)}
        if len(cc) >= 2 and all(deg[n] == 2 for n in noeuds):
            ks = sorted(cc)
            ordre, morceaux = [ks[0]], [poly(ks[0], 0)]
            n = noeud[(ks[0], 1)]
            while len(ordre) < len(ks):
                k2, e2 = next((k2, e2) for k2, e2 in adj[n] if k2 not in ordre)
                ordre.append(k2)
                morceaux.append(poly(k2, e2))
                n = noeud[(k2, 1 - e2)]
            P = morceaux[0]
            for Q in morceaux[1:]:
                P = np.vstack([P[:-1], 0.5 * (P[-1] + Q[0])[None], Q[1:]])
            P[0] = 0.5 * (P[0] + P[-1])
            anneaux.append((tuple(ks), M.dedoublonner(P[:-1])))
            vus |= cc
    # contours ouverts en U (bande dessinée sur trois côtés) : chemin simple dont les deux bouts sont à moins de 0,7 m
    for k0 in ouv:
        if k0 in vus:
            continue
        cc, pile = {k0}, [k0]
        while pile:
            k = pile.pop()
            for k2 in sorted(voisins[k]):
                if k2 not in cc:
                    cc.add(k2)
                    pile.append(k2)
        if k0 != min(cc) or any(k in vus for k in cc):
            continue
        noeuds = [noeud[(k, e)] for k in cc for e in (0, 1)]
        bouts_c = [n for n in set(noeuds) if deg[n] == 1]
        if len(bouts_c) != 2 or any(deg[n] > 2 for n in set(noeuds)):
            continue
        # parcours du chemin depuis un bout
        n = min(bouts_c)
        k, e = next((k, e) for k, e in adj[n])
        ordre, morceaux = [k], [poly(k, e)]
        n = noeud[(k, 1 - e)]
        while deg[n] == 2:
            k2, e2 = next((k2, e2) for k2, e2 in adj[n] if k2 not in ordre)
            ordre.append(k2)
            morceaux.append(poly(k2, e2))
            n = noeud[(k2, 1 - e2)]
        P = morceaux[0]
        for Q in morceaux[1:]:
            P = np.vstack([P[:-1], 0.5 * (P[-1] + Q[0])[None], Q[1:]])
        if float(np.hypot(*(P[0] - P[-1]))) <= 0.7 and abscisses(P)[-1] >= 2.0:
            r = M.dedoublonner(P)
            o = M.rect_min(r)
            if 0.35 <= o["W"] <= 0.7 and abs(aire_signee(r)) / max(o["L"] * o["W"], 1e-9) >= 0.85:
                anneaux.append((tuple(sorted(cc)), r))
                vus |= cc
    # chaînes : arrêt aux nœuds de degré ≠ 2 et aux raccords anguleux
    def suivant(k, e_fin):
        n = noeud[(k, e_fin)]
        if deg[n] != 2:
            return None
        k2, e2 = next((k2, e2) for k2, e2 in adj[n] if not (k2 == k and e2 == e_fin))
        return (k2, e2) if k2 not in vus else None
    for k0 in ouv:
        if k0 in vus:
            continue
        # remonter au début de la chaîne (côté e = 0)
        k, e = k0, 0
        deja = {k0}
        while True:
            pr = suivant(k, e)
            if pr is None or pr[0] in deja:
                break
            k2, e2 = pr
            if _deviation(poly(k2, 1 - e2), poly(k, e)) > ANGLE_COUPE:
                break
            deja.add(k2)
            k, e = k2, 1 - e2
        ks, morceaux = [k], [poly(k, e)]
        vus.add(k)
        fin = 1 - e
        while True:
            pr = suivant(ks[-1], fin)
            if pr is None:
                break
            k2, e2 = pr
            Q = poly(k2, e2)
            if _deviation(morceaux[-1], Q) > ANGLE_COUPE:
                break
            vus.add(k2)
            ks.append(k2)
            morceaux.append(Q)
            fin = 1 - e2
        P = morceaux[0]
        for Q in morceaux[1:]:
            P = np.vstack([P[:-1], 0.5 * (P[-1] + Q[0])[None], Q[1:]])
        chaines.append((tuple(sorted(ks)), P))
    anneaux.sort(key=lambda a: a[0])
    chaines.sort(key=lambda a: a[0])
    return anneaux, chaines


# --------------------------------------------------------------------------- 2. anneaux
def centroide(polys):
    """Centroïde d'aire de polygones [[ext, trous...], ...]."""
    A, C = 0.0, np.zeros(2)
    for poly in polys:
        for k, r in enumerate(poly):
            r = np.asarray(r, float)
            x, y = r[:, 0], r[:, 1]
            x2, y2 = np.roll(x, -1), np.roll(y, -1)
            cr = x * y2 - x2 * y
            a = 0.5 * cr.sum()
            c = np.array([((x + x2) * cr).sum(), ((y + y2) * cr).sum()]) / 6.0
            sg = 1.0 if k == 0 else -1.0
            A += sg * abs(a)
            C += sg * (c if a >= 0 else -c)
    return C / max(A, 1e-12)


def ajuster_fleche(r, noms=FLECHES, echelles=(1.0, 0.5)):
    """Meilleur gabarit IISR pour le contour r (FUS-SNP-004) : balayage du cap (± 12° autour du grand axe du
    rectangle minimal, pas de 1°, deux sens) avec centroïdes d'aire alignés, puis descente (translations 4 / 2 / 1 cm,
    rotations 0,5 / 0,25°). -> dict {gabarit, echelle, origine, cap_deg, iou} ou None."""
    o = M.rect_min(r)
    polys_r = [[r]]
    c_r = centroide(polys_r)
    resultats = []

    def iou_pose(g, org, cap, e):
        return M.iou(polys_r, [[M.poser(rr, org, cap, e) for rr in poly] for poly in g], res=0.02)
    for nom in noms:
        g = M.gabarit(nom)
        P = np.vstack([rr for poly in g for rr in poly])
        Lg = float(P[:, 1].max() - P[:, 1].min())
        c_t = centroide(g)
        for e in echelles:
            if abs(o["L"] - Lg * e) > 0.35 * Lg * e:
                continue
            cand = None
            for sens in (1.0, -1.0):
                c0 = M.cap_de(o["u"] * sens)
                for dc in range(-12, 13):
                    cap = (c0 + dc) % 360.0
                    ex, ey = M.axes_cap(cap)
                    org = c_r - (c_t[0] * ex + c_t[1] * ey) * e
                    i = iou_pose(g, org, cap, e)
                    if cand is None or i > cand[0] + 1e-9:
                        cand = (i, org, cap)
            iou, org, cap = cand
            for p, da in ((0.04, 0.5), (0.02, 0.25), (0.01, 0.25)):
                amelio = True
                while amelio:
                    amelio = False
                    ex, ey = M.axes_cap(cap)
                    for dx, dy, dd in ((p, 0, 0), (-p, 0, 0), (0, p, 0), (0, -p, 0), (0, 0, da), (0, 0, -da)):
                        o2, c2 = org + dx * ex + dy * ey, (cap + dd) % 360.0
                        i2 = iou_pose(g, o2, c2, e)
                        if i2 > iou + 1e-4:
                            iou, org, cap, amelio = i2, o2, c2, True
                            break
            resultats.append({"gabarit": nom, "echelle": e, "origine": org, "cap_deg": cap % 360.0, "iou": iou})
    if not resultats:
        return None
    resultats.sort(key=lambda x: (-x["iou"], FLECHES.index(x["gabarit"]), -x["echelle"]))
    best = dict(resultats[0])
    autre = next((x for x in resultats[1:] if x["gabarit"] != best["gabarit"]), None)
    best["second"] = (autre["gabarit"], round(autre["iou"], 3)) if autre else None
    return best


def classer_anneau(ks, r):
    r = M.dedoublonner(r)
    A = abs(aire_signee(r))
    o = M.rect_min(r)
    rempl = A / max(o["L"] * o["W"], 1e-9)
    s = M.douglas_peucker(np.vstack([r, r[:1]]), 0.02)[:-1]
    n = len(s)
    base = {"gam": list(ks), "anneau": r, "obb": o, "aire_m2": A, "remplissage": rempl, "n_sommets": n}
    L, W = o["L"], o["W"]
    if n == 4 and rempl >= 0.93:
        if 0.40 <= W <= 0.62 and L >= 1.5:
            return dict(base, nature="bande")
        if 0.40 <= W <= 0.62 and 0.40 <= L <= 0.62:
            return dict(base, nature="carre")
        if 0.08 <= W <= 0.35 and 0.3 <= L <= 6.5:
            return dict(base, nature="tiret")
    if n == 3 and 0.4 <= rempl <= 0.6 and L >= 0.3:
        return dict(base, nature="triangle")
    if n <= 6 and 0.40 <= W <= 0.62 and L >= 1.0 and rempl >= 0.60:
        # parallélogramme (bande de hachure) ou bande de zébra tronquée (au droit d'une bordure ou d'un îlot)
        return dict(base, nature="bande_oblique")
    if 1.5 <= L <= 7.0 and 0.25 <= W <= 1.5 and n >= 6:
        fl = ajuster_fleche(r)
        if fl and fl["iou"] >= 0.55:
            return dict(base, nature="fleche", fleche=fl)
    return dict(base, nature="atypique")


# --------------------------------------------------------------------------- 3. chaînes
def _droite(P, tol=0.03):
    o = M.rect_min(P) if len(P) > 2 else {"W": 0.0}
    return o["W"] <= tol


def classer_chaine(ks, P):
    L = float(abscisses(P)[-1])
    s = M.douglas_peucker(P, 0.02)
    base = {"gam": list(ks), "P": P, "longueur_m": L, "n_sommets": len(s)}
    if L < 0.2:
        return dict(base, nature="debris")
    if len(s) == 3:
        l1, l2 = float(np.hypot(*(s[1] - s[0]))), float(np.hypot(*(s[2] - s[1])))
        u1, u2 = (s[0] - s[1]) / max(l1, 1e-9), (s[2] - s[1]) / max(l2, 1e-9)
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(u1 @ u2)))))
        if 0.4 <= l1 <= 1.0 and 0.4 <= l2 <= 1.0 and 60.0 <= ang <= 120.0:
            return dict(base, nature="chevron", pointe=s[1], branche_m=0.5 * (l1 + l2), ouverture_deg=ang,
                        cap_deg=M.cap_de(-(u1 + u2)))
    if len(s) >= 6:
        seg = np.hypot(*np.diff(s, axis=0).T)
        d = np.diff(s, axis=0)
        tour = np.sign(d[:-1, 0] * d[1:, 1] - d[:-1, 1] * d[1:, 0])
        if (tour[1:] != tour[:-1]).mean() >= 0.7 and 2.0 <= np.median(seg) <= 4.5 and len(seg) >= 5:
            return dict(base, nature="zigzag")
    if _droite(P) and 0.3 <= L <= 6.5:
        return dict(base, nature="segment")
    return dict(base, nature="axe")


def paires_chaines(ch):
    """Paires de bords parmi les chaînes ouvertes (axe, segment) : {i: (j, écartement médian)} réciproques."""
    idx = [i for i, c in enumerate(ch) if c["nature"] in ("axe", "segment")]
    bb = {i: (*ch[i]["P"].min(axis=0) - 0.3, *ch[i]["P"].max(axis=0) + 0.3) for i in idx}
    cand = {}
    for a in idx:
        Q, _ = densifier(ch[a]["P"], 0.10)
        for b in idx:
            if b == a:
                continue
            A, B = bb[a], bb[b]
            if A[2] < B[0] or B[2] < A[0] or A[3] < B[1] or B[3] < A[1]:
                continue
            Pb = ch[b]["P"]
            sb, d, _ = projeter(Pb, Q)
            dedans = (sb > 0.01) & (sb < abscisses(Pb)[-1] - 0.01)
            if dedans.sum() < 3 or dedans.mean() < 0.5:
                continue
            e = float(np.median(d[dedans]))
            if not (0.06 <= e <= 0.25) or float(np.percentile(d[dedans], 90) - np.percentile(d[dedans], 10)) > 0.04:
                continue
            fr = float(dedans.mean())
            if a not in cand or (fr, -e) > (cand[a][2], -cand[a][1]):
                cand[a] = (b, round(e, 3), round(fr, 3))
    return {k: v for k, v in cand.items() if v[0] in cand and cand[v[0]][0] == k}


def mediane(P, Q):
    """Ligne médiane de deux bords (échantillons de P au pas 0,05 m projetés sur Q)."""
    from commun import point_a
    S, _ = densifier(P, 0.05)
    sq, _, _ = projeter(Q, S)
    dedans = (sq > 0.005) & (sq < abscisses(Q)[-1] - 0.005)
    Pq, _ = point_a(Q, sq[dedans])
    return M.dedoublonner(0.5 * (S[dedans] + Pq))


# --------------------------------------------------------------------------- 5. blocs
def blocs():
    out = []
    for b in M.gam_pct():
        nom = b["bloc"]
        if not nom:
            out.append({"gam_pct": b["i"], "nature": "texte_ignore", "libelle": b["libelle"], "xy": b["xy"]})
            continue
        rot = float(b["rotation"] or 0.0)
        e = 1.0
        from commun import lire_geojson
        out.append({"gam_pct": b["i"], "bloc": nom, "xy": b["xy"], "rotation": rot})
        if nom == "SYMBOLE_VELO":
            out[-1].update(nature="velo", cap_deg=(rot + 90.0) % 360.0)
        elif nom == "SYMBOLE_PMR":
            out[-1].update(nature="pmr", cap_deg=(rot + PMR_CAP_DECALAGE) % 360.0)
        elif nom in BLOC_FLECHE:
            out[-1].update(nature="fleche", gabarit=BLOC_FLECHE[nom], cap_deg=(rot + 90.0) % 360.0)
        else:
            out[-1].update(nature="bloc_inconnu")
    ech = _echelles_blocs()
    for o in out:
        if "bloc" in o:
            o["echelle"] = ech.get(o["gam_pct"], 1.0)
    return out


@functools.lru_cache(maxsize=None)
def _echelles_blocs():
    from commun import lire_geojson
    out = {}
    for i, f in enumerate(lire_geojson(M.GAM_PCT)):
        e = f["properties"].get("echelle_bloc")
        if e:
            out[i] = float(str(e).split(";")[0])
    return out


# --------------------------------------------------------------------------- classement complet
@functools.lru_cache(maxsize=None)
def classer():
    """-> {anneaux: [...], chaines: [...], paires: {...}, blocs: [...], pictos: [...]}."""
    an, ch = assembler()
    A = [classer_anneau(ks, r) for ks, r in an]
    C = [classer_chaine(ks, P) for ks, P in ch]
    pp = paires_chaines(C)
    for i, (j, e, fr) in sorted(pp.items()):
        C[i]["paire"] = (j, e, fr)
    # 4. pictogrammes dessinés : petits anneaux (atypiques, tirets) et petites chaînes voisins (< 0,15 m)
    petits = [("a", i) for i, x in enumerate(A) if x["nature"] in ("atypique", "tiret") and x["obb"]["L"] < 1.45]
    petits += [("c", i) for i, x in enumerate(C) if x["nature"] in ("debris", "axe", "segment") and x["longueur_m"] < 1.6
               and "paire" not in x and float(np.ptp(x["P"], axis=0).max()) < 1.45]
    pts = {p: (A[p[1]]["anneau"] if p[0] == "a" else C[p[1]]["P"]) for p in petits}
    groupes, vus = [], set()
    for p in petits:
        if p in vus:
            continue
        g, pile = [p], [p]
        vus.add(p)
        while pile:
            q = pile.pop()
            for r in petits:
                if r in vus:
                    continue
                dmin = float(np.min(np.hypot(*(pts[q][:, None, :] - pts[r][None, :, :]).transpose(2, 0, 1))))
                if dmin < 0.15:
                    vus.add(r)
                    g.append(r)
                    pile.append(r)
        groupes.append(sorted(g))
    pictos = []
    for g in groupes:
        P = np.vstack([pts[p] for p in g])
        o = M.rect_min(P)
        if len(g) < 2 or not (0.45 <= o["L"] <= 1.6):
            continue
        ks = sorted(k for p in g for k in (A[p[1]]["gam"] if p[0] == "a" else C[p[1]]["gam"]))
        # figurine vélo dessinée par le levé : trait en Z (1,1-1,4 x 0,25-0,45) + barre (0,3-0,5 x 0,1-0,2)
        anns = [A[p[1]] for p in g if p[0] == "a"]
        z = [x for x in anns if 1.1 <= x["obb"]["L"] <= 1.45 and 0.25 <= x["obb"]["W"] <= 0.45]
        barre = [x for x in anns if 0.3 <= x["obb"]["L"] <= 0.5 and 0.1 <= x["obb"]["W"] <= 0.2]
        k_ = [x for x in anns if 1.1 <= x["obb"]["L"] <= 1.45 and 0.5 <= x["obb"]["W"] <= 0.7 and x["remplissage"] < 0.35]
        if len(z) == 1 and len(barre) == 1 and len(anns) == 2:
            nature = "velo"
        elif len(k_) == 1:
            nature = "pieton"          # silhouette en K (jambes en V, bras en barres) : pictogramme piéton dessiné
        else:
            nature = "inconnu"
        for p in g:
            (A if p[0] == "a" else C)[p[1]]["nature"] = "picto"
        pictos.append({"gam": ks, "obb": o, "n_morceaux": len(g), "nature": nature,
                       "anneaux": [x["anneau"] for x in anns], "axe_u": (z[0]["obb"]["u"] if z else o["u"])})
    pictos.sort(key=lambda p: p["gam"])
    return {"anneaux": A, "chaines": C, "blocs": blocs(), "pictos": pictos, "triangles": triangles_ouverts()}


def resume():
    import collections
    c = classer()
    return {"anneaux": dict(sorted(collections.Counter(a["nature"] for a in c["anneaux"]).items())),
            "chaines": dict(sorted(collections.Counter(x["nature"] for x in c["chaines"]).items())),
            "paires": sum(1 for x in c["chaines"] if "paire" in x) // 2,
            "blocs": dict(sorted(collections.Counter(b["nature"] for b in c["blocs"]).items())),
            "pictos": dict(sorted(collections.Counter(p["nature"] for p in c["pictos"]).items())),
            "triangles": len(c["triangles"])}


if __name__ == "__main__":
    import json
    print(json.dumps(resume(), ensure_ascii=False, indent=1))
