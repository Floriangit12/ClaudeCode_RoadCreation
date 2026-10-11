"""Modèle de nivellement UNIQUE du site (TQ-SOL-013, CF-26) : une seule surface de sol, évaluée dans
l'ordre de la règle, partagée par la fabrication des bordures, du sol, des îlots et des marquages.

Ordre (TQ-SOL-013) :
 (1) chaussée hors jonction : modèle OpenDRIVE elevation + superelevation + shape (TQ-SOL-004,
     nivellement_xodr), imposé (Dirichlet) sur les nœuds des voies circulées des routes 1-6 ;
 (2) aire du carrefour (jonction 100) : membrane (TQ-SOL-014) entre les profils des branches, avec un
     terme faible vers l'axe de Verdun (liaisons tout droit) ; autres chaussées hors .xodr (rues des
     Saules Blancs, parkings, accès) : membrane + terme faible vers le MNT lissé ;
 (3) caniveaux : bord côté chaussée au Z de la chaussée, fil d'eau 2,5 cm plus bas (CS2) ;
 (4) pied de face de chaque bordure : fil d'eau du caniveau au contact, sinon Z de la chaussée (ou de
     la surface basse) au contact — le sol passe sous la bordure au niveau du pied ;
 (5) tête de bordure : pied + vue décrite (chartières linéaires) ;
 (6) trottoir, quai, refuge, piste : tête − 4 mm à l'arête arrière (TQ-SOL-013), dévers de 1,5 % vers la
     chaussée sur les 4 premiers mètres (GA-TRO-003 ; potentiel de dévers et terme fort vers tête − retrait
     de la bordure de chaussée la plus proche : le raccord au terrain se fait hors de la bande), rampes analytiques derrière
     les abaissés en plan incliné (GA-ABA-003/005, GA-CHR-002), puis membrane ;
 (7) îlots plantés et remplis : tête − retrait (3 à 5 cm, GA-ARB-003), bombement ; îlots revêtus : − 4 mm ;
 (8) espaces verts : MNT 2026 conditionné (lissage σ 0,3 m, TQ-SOL-007) raccordé aux arêtes arrière
     (tête − 2 cm) ; noue : talus à 1/3 au plus depuis la rive (GA-ASS-005).
Discontinuités : arêtes arrière et bouts de bordure, bâtiments, bord du site. Toutes les autres limites
(arête avant, limites de revêtement, fermetures, coupes) sont continues : chaque composante connexe de
faces est une RÉGION de nivellement, résolue par moindres carrés (gradient conjugué, grille de 0,10 m)
dans l'ordre des dépendances (une bordure dont la région basse est résolue fixe sa région haute).
Fins de file libres (même région des deux côtés, GA-BOR-005) : descente de la vue à 0 sur ≥ 1 m.

Sorties : base/nivellement.json (régions, modèles par surface, lignes de contrainte des bordures,
rampes, statistiques et contrôles), base/nivellement_grille.npz (couches z / région, voir
nivellement_requete.py), Z des bordures (fil d'eau = pied) réécrit dans la description.
"""
import collections
import math

import numpy as np

import sol_geometrie as G
import sol_partition as SP
import sol_site as ctx
from commun import abscisses, arrondi, coords_geojson, distance_segments, normale_gauche, point_a, repere

PAS = 0.10
N = 3001
X0 = Y0 = -150.0
Z_O = 216.30
RETRAIT_TROTTOIR = 0.004          # TQ-SOL-013 (6)
RETRAIT_VERT = 0.02               # espace vert raccordé sous la tête (TQ-SOL-007)
DEVERS_TROTTOIR = 0.015           # GA-TRO-003 : 1,5 % par défaut, vers la chaussée
DEVERS_SUR_M = 4.0
DENIVELE_CS2 = 0.025              # TQ-SOL-013 (3)
TALUS_NOUE = 1.0 / 3.0            # GA-ASS-005 / revue : talus à 1/3 au plus
LAMBDA_VERT = 0.002               # attache au MNT lissé des espaces verts : raccord sur ≈ 2 m (TQ-SOL-007 : 30·|Δz|, 0,6-4 m)
LAMBDA_DEVERS = 0.05              # bande de dévers des cheminements (GA-TRO-003) : raccord au terrain ≈ 0,5 m
COUTURE_XODR_M = 0.3              # nœuds laissés libres à la couture de deux routes (raccord des profils)
CLASSES_VEHICULES = {"chaussee", "parking", "acces_riverain"}
CLASSES_PIETONNES = {"trottoir", "quai_bus", "piste_cyclable", "autre"}
CLASSES_VERTES = {"espace_vert", "terre_plein_vegetal"}
REMPLIS = {"brf_bois_concasse", "gravier_concasse_6_10", "galets_20_40", "gazon_tondu", "herbe_haute", "terre_nue",
           "noue_plantee"}


# --------------------------------------------------------------------------- grille
def coord_noeuds(i, j):
    return X0 + np.asarray(i) * PAS, Y0 + np.asarray(j) * PAS


def masque_lignes(lignes, largeur_px):
    """Nœuds (tableau [j, i]) à moins de ~largeur_px/2 nœuds des polylignes locales."""
    from PIL import Image, ImageDraw
    img = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(img)
    for P in lignes:
        pts = [((x - X0) / PAS, (N - 1) - (y - Y0) / PAS) for x, y in np.asarray(P)[:, :2]]
        if len(pts) >= 2:
            d.line(pts, fill=1, width=largeur_px)
    return np.array(img, dtype=bool)[::-1]


def masque_noeuds(anneaux, i0, i1, j0, j1):
    """Masque [j0:j1, i0:i1] (ligne j = y croissant) des nœuds intérieurs à la face (pair-impair)."""
    nx, ny = i1 - i0, j1 - j0
    x0 = X0 + i0 * PAS - PAS / 2
    y_haut = Y0 + (j1 - 1) * PAS
    m = SP.masque_face(anneaux, x0, y_haut + PAS / 2, PAS, nx, ny)
    return m[::-1]


def boite(anneaux, marge=1):
    a = np.vstack(anneaux)
    i0 = max(0, int(math.floor((a[:, 0].min() - X0) / PAS)) - marge)
    i1 = min(N, int(math.ceil((a[:, 0].max() - X0) / PAS)) + 1 + marge)
    j0 = max(0, int(math.floor((a[:, 1].min() - Y0) / PAS)) - marge)
    j1 = min(N, int(math.ceil((a[:, 1].max() - Y0) / PAS)) + 1 + marge)
    return i0, i1, j0, j1


def flou(z, sigma_m, masque=None):
    """Lissage gaussien approché (3 passes de moyenne glissante, séparables) ; NaN ignorés."""
    r = max(1, int(round(sigma_m / PAS * math.sqrt(3.0) * 0.6)))
    v = np.where(np.isfinite(z), z, 0.0)
    w = np.isfinite(z).astype(np.float64)
    if masque is not None:
        v, w = v * masque, w * masque
    for _ in range(3):
        for ax in (0, 1):
            for arr in (v, w):
                c = np.cumsum(np.pad(arr, [(r + 1, r) if a == ax else (0, 0) for a in (0, 1)], mode="edge"), axis=ax)
                sl_hi = [slice(None)] * 2
                sl_lo = [slice(None)] * 2
                sl_hi[ax] = slice(2 * r + 1, None)
                sl_lo[ax] = slice(0, -(2 * r + 1))
                arr[...] = (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / (2 * r + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(w > 1e-6, v / np.maximum(w, 1e-12), np.nan)


# --------------------------------------------------------------------------- solveur
def resoudre(zone, fixe, z_fixe, lam, cible, x0=None, iters=4000, tol=2e-5):
    """Minimise Σ_arêtes (h_i − h_j)² + Σ λ_i (h_i − cible_i)² sur les nœuds de `zone` (4-voisinage),
    nœuds `fixe` imposés à z_fixe : gradient conjugué préconditionné (Jacobi) sur le vecteur des seules
    inconnues (voisinages indexés). Tableaux 2D (sous-grille) ; renvoie (z 2D, itérations)."""
    inc = zone & ~fixe
    out = np.where(fixe & zone, z_fixe, np.nan)
    if not inc.any():
        return out, 0
    H, W = zone.shape
    flat = np.flatnonzero(inc)
    n = len(flat)
    uidx = np.full(H * W, -1, dtype=np.int64)
    uidx[flat] = np.arange(n)
    zf = zone.ravel()
    fx = (fixe & zone).ravel()
    zfv = np.where(fx, z_fixe.ravel(), 0.0)
    r_, c_ = flat // W, flat % W
    deg = np.zeros(n)
    rhs = lam.ravel()[flat] * np.where(np.isfinite(cible.ravel()[flat]), cible.ravel()[flat], 0.0)
    voisins = []
    for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        rr, cc = r_ + dr, c_ + dc
        ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        nb = np.where(ok, rr * W + cc, 0)
        ok &= zf[nb]
        deg += ok
        vu = np.where(ok, uidx[nb], -1)
        rhs += np.where(ok & fx[nb], zfv[nb], 0.0)
        voisins.append(vu)
    lamv = lam.ravel()[flat].astype(np.float64)
    lamv = np.where(deg + lamv <= 0.0, 1e-3, lamv)          # nœud isolé : retenu par les données
    diag = deg + lamv
    V = np.stack(voisins)
    okV = V >= 0
    Vs = np.where(okV, V, 0)

    Vd = np.where(okV, V, n)                                   # voisin absent -> case nulle ajoutée

    def Av(v):
        ve = np.append(v, 0.0)
        return diag * v - (ve[Vd[0]] + ve[Vd[1]] + ve[Vd[2]] + ve[Vd[3]])
    x = np.zeros(n)
    if x0 is not None:
        x = np.nan_to_num(x0.ravel()[flat])
    r = rhs - Av(x)
    zv = r / diag
    p = zv.copy()
    rz = _dot(r, zv)
    nb_ = math.sqrt(_dot(rhs, rhs)) + 1e-12
    k = 0
    for k in range(iters):
        Ap = Av(p)
        a = rz / max(_dot(p, Ap), 1e-30)
        x += a * p
        r -= a * Ap
        if math.sqrt(_dot(r, r)) / nb_ < tol:
            break
        zv = r / diag
        rz2 = _dot(r, zv)
        p = zv + (rz2 / max(rz, 1e-30)) * p
        rz = rz2
    o = out.ravel()
    o[flat] = x
    return o.reshape(H, W), k + 1


def _dot(a, b):
    """Produit scalaire déterministe (somme par paires de numpy, sans BLAS multi-fil)."""
    return float(np.einsum("i,i->", a, b))


def _paires():
    return (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
            ((slice(0, -1), slice(None)), (slice(1, None), slice(None))))


# --------------------------------------------------------------------------- données
class Bord:
    """Bordure en repère local : arête avant, largeurs, vues, caniveau, régions basse et haute."""

    def __init__(self, f):
        self.f = f
        self.p = f["properties"]
        self.id = self.p["id"]
        self.P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        self.S = abscisses(self.P)
        self.L = float(self.S[-1])
        n = max(2, int(math.ceil(self.L / 0.25)) + 1)
        self.s = np.linspace(0.0, self.L, n)
        self.q, self.tg = point_a(self.P, self.s)
        self.nrm = normale_gauche(self.tg)
        self.w = G.largeur_le_long(self.p["intervalles"], self.s)

    def vue(self, s):
        out = np.empty(len(np.atleast_1d(s)))
        for k, x in enumerate(np.atleast_1d(s)):
            it = self.p["intervalles"][-1]
            for c in self.p["intervalles"]:
                if c["s0"] - 1e-9 <= x <= c["s1"] + 1e-9:
                    it = c
                    break
            if "vue_m_fin" in it and it["s1"] > it["s0"]:
                t = (x - it["s0"]) / (it["s1"] - it["s0"])
                out[k] = it["vue_m"] + (it["vue_m_fin"] - it["vue_m"]) * min(1.0, max(0.0, t))
            else:
                out[k] = it["vue_m"]
        return out

    def caniveau(self, s):
        cv = self.p.get("caniveau") or {}
        m = np.zeros(len(s), bool)
        for a, b in cv.get("intervalles", []):
            m |= (s >= a - 1e-6) & (s <= b + 1e-6)
        return m


def carte_xodr_chaussee():
    """Cellules des voies circulées des routes 1-6 contiguës à la chaussée : route (0 ailleurs)."""
    par = collections.defaultdict(dict)
    for r, v, t, s, j, polys in ctx.voies_xodr():
        if not j:
            par[(r, s)][v] = (t, polys)
    items = []
    for (r, s), voies in sorted(par.items()):
        for signe in (1, -1):
            k = signe
            ok = True
            while k in voies and ok:
                t, polys = voies[k]
                if t in ("driving", "bus", "biking", "stop", "parking", "entry", "exit"):
                    items.append((r, polys))
                else:
                    ok = False                            # au-delà d'une bordure, d'un TPC ou d'un trottoir
                k += signe
    return ctx.rasteriser(items, 0)


# --------------------------------------------------------------------------- construction
def construire(K, S, partition, I, mnt):
    """(K à Z réécrits, nivellement dict, grille dict, rapport)."""
    import nivellement_xodr as NX
    arr = partition["arrangement"]
    lignes = partition["lignes"]
    faces = arr["faces"]
    face_id = partition["face_id"]
    sprops = {f["properties"]["id"]: f["properties"] for f in S}
    ks = sorted(face_id)
    # ---- étiquettes des nœuds (face) et régions
    lab = np.full((N, N), -1, dtype=np.int32)
    for k in ks:
        i0, i1, j0, j1 = boite(faces[k]["anneaux"])
        m = masque_noeuds(faces[k]["anneaux"], i0, i1, j0, j1)
        sub = lab[j0:j1, i0:i1]
        sub[m] = k
    par = {k: k for k in ks}

    def rac(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    gauche = {}
    for k, f in enumerate(faces):
        for cyc in f["aretes"]:
            for u, v in cyc:
                gauche[(u, v)] = k
    disc = {"bordure_arriere", "bordure_bout", "batiment", "emprise"}
    for (a, b), ls in sorted(arr["aretes"].items()):
        if any(lignes[l][1]["src"] in disc for l in ls):
            continue
        fa, fb = gauche.get((a, b)), gauche.get((b, a))
        if fa in par and fb in par:
            ra, rb = rac(fa), rac(fb)
            if ra != rb:
                par[max(ra, rb)] = min(ra, rb)
    reg_face = {k: rac(k) for k in ks}
    regions = sorted(set(reg_face.values()))
    rid = {r: n for n, r in enumerate(regions)}
    reg_face = {k: rid[r] for k, r in reg_face.items()}
    lut = np.full(len(faces) + 1, -1, dtype=np.int32)
    for k, r in reg_face.items():
        lut[k] = r
    reg = np.where(lab >= 0, lut[np.where(lab >= 0, lab, len(faces))], -1)
    classe_face = {k: sprops[face_id[k]]["classe"] for k in ks}
    mat_face = {k: sprops[face_id[k]]["revetement"]["materiau_id"] for k in ks}
    # ---- MNT aux nœuds (repère local) et versions lissées
    ii, jj = np.meshgrid(np.arange(N), np.arange(N))
    xs, ys = coord_noeuds(ii, jj)
    z_mnt = (mnt(xs.ravel() + 917279.43, ys.ravel() + 6460289.98) - Z_O).reshape(N, N)
    z_lisse = flou(z_mnt, 0.3)            # TQ-SOL-007
    z_large = flou(z_mnt, 1.5)
    # ---- chaussée OpenDRIVE (TQ-SOL-004) : nœuds des voies circulées des routes 1-6
    cx = carte_xodr_chaussee()
    rr = np.clip(np.floor((150.0 - ys) / PAS).astype(int), 0, cx.shape[0] - 1)
    cc = np.clip(np.floor((xs + 150.0) / PAS).astype(int), 0, cx.shape[1] - 1)
    route_noeud = cx[rr, cc]
    lut_ch = np.zeros(len(faces) + 1, bool)
    for k in ks:
        lut_ch[k] = classe_face[k] == "chaussee"
    est_chaussee = lut_ch[np.where(lab >= 0, lab, len(faces))]
    z_xodr = np.full((N, N), np.nan)
    modeles = NX.modeles()
    nc = int(round(COUTURE_XODR_M / PAS))
    for r_id, M in modeles.items():
        m = est_chaussee & (route_noeud == int(r_id))
        autre = (route_noeud > 0) & (route_noeud != int(r_id))
        for _ in range(nc):                               # couture avec une autre route : libre (membrane)
            a2 = autre.copy()
            a2[1:, :] |= autre[:-1, :]
            a2[:-1, :] |= autre[1:, :]
            a2[:, 1:] |= autre[:, :-1]
            a2[:, :-1] |= autre[:, 1:]
            autre = a2
        m &= ~autre
        if not m.any():
            continue
        Q = np.c_[xs[m], ys[m]]
        z, s, t = M.z_xy_rapide(Q)
        z_xodr[m] = z
    # jonction : aire des voies des routes de liaison (jonction 100) élargie de 2 m, hors routes 1-6
    cj = ctx.rasteriser([(1, polys) for r_, v_, t_, s_, j_, polys in ctx.voies_xodr() if j_], 0)
    mj = cj[rr, cc] == 1
    for _ in range(20):
        m2 = mj.copy()
        m2[1:, :] |= mj[:-1, :]
        m2[:-1, :] |= mj[1:, :]
        m2[:, 1:] |= mj[:, :-1]
        m2[:, :-1] |= mj[:, 1:]
        mj = m2
    jonction = est_chaussee & (route_noeud == 0) & mj
    # axe de Verdun (liaisons tout droit 101, 102, 105, 106), terme faible (TQ-SOL-014)
    z_axe = np.full((N, N), np.nan)
    liaisons = NX.modeles_liaisons()
    for r_id in ("101", "102", "105", "106"):
        if r_id not in liaisons:
            continue
        M = liaisons[r_id]
        Q = np.c_[xs[jonction], ys[jonction]]
        z, s, t = M.z_xy_rapide(Q)
        ok = (np.abs(t) < 4.0) & (s > 0.0) & (s < M.route.longueur)
        tmp = z_axe[jonction]
        tmp[ok & np.isnan(tmp)] = z[ok & np.isnan(tmp)]
        z_axe[jonction] = tmp
    # ---- bordures : régions basse et haute (par extrémités et milieu)
    bords = [Bord(f) for f in K]
    par_k = {b.id: b for b in bords}

    def region_pt(Q):
        i = np.clip(np.rint((Q[:, 0] - X0) / PAS).astype(int), 0, N - 1)
        j = np.clip(np.rint((Q[:, 1] - Y0) / PAS).astype(int), 0, N - 1)
        return reg[j, i]
    for b in bords:
        rb = region_pt(b.q - b.nrm * 0.15)
        rh = region_pt(b.q + b.nrm * (b.w + 0.15)[:, None])
        b.r_bas = collections.Counter(int(x) for x in rb if x >= 0).most_common(1)[0][0] if (rb >= 0).any() else -1
        b.r_haut = collections.Counter(int(x) for x in rh if x >= 0).most_common(1)[0][0] if (rh >= 0).any() else -1
        b.rb, b.rh = rb, rh
        ib = np.clip(np.rint(((b.q - b.nrm * 0.15) - [X0, Y0]) / PAS).astype(int), 0, N - 1)
        ih = np.clip(np.rint(((b.q + b.nrm * (b.w + 0.15)[:, None]) - [X0, Y0]) / PAS).astype(int), 0, N - 1)
        b.lb_bas, b.lb_haut = lab[ib[:, 1], ib[:, 0]], lab[ih[:, 1], ih[:, 0]]
        cls = [classe_face.get(int(x), "") for x in b.lb_bas if x >= 0]
        b.bas_vehicule = bool(cls) and np.mean([c in CLASSES_VEHICULES for c in cls]) >= 0.5
    # ---- GA-BOR-005 : fins de file libres (même région des deux côtés près du bout) -> descente
    descentes = []
    ouverts = set(tuple(x) for x in partition.get("bouts_ouverts", []))
    for b in bords:
        its = b.p["intervalles"]
        for bout in (0, -1):
            sel = (b.s <= 1.0) if bout == 0 else (b.s >= b.L - 1.0)
            if not sel.any():
                continue
            meme = np.mean((b.lb_bas[sel] == b.lb_haut[sel]) & (b.lb_bas[sel] >= 0))
            if (b.id, bout) in ouverts:                   # bout de file ouvert (ni pont ni contact) : sol
                meme = 1.0                                # continu autour du bout -> descente
            v = its[0]["vue_m"] if bout == 0 else its[-1].get("vue_m_fin", its[-1]["vue_m"])
            it_bout = its[0] if bout == 0 else its[-1]
            if meme < 0.5 or v <= 0.025 or b.L < 2.0 or it_bout.get("role") != "courant":
                continue                                  # bout d'abaissé ou de chartière : inchangé
            if it_bout.get("profil") == "MURET_TALUS":
                continue                                  # muret : about vertical, pas de chartière (K-0098 « en tente »,
                                                          # revue réalisme du 11/10/2026 ; GA-ASS-005, TQ-SOL-013)
            ld = float(min(max(1.0, v / 0.10), 0.45 * b.L))   # ≤ 10 %/m sur la tête, ≥ 1 m
            nouv = []
            if bout == 0:
                a = {"s0": 0.0, "s1": ld, "profil": its[0]["profil"], "vue_m": 0.0, "vue_m_fin": round(v, 3),
                     "role": "chartiere"}
                for it in its:
                    if it["s1"] <= ld + 1e-9:
                        continue
                    it = dict(it)
                    if it["s0"] < ld:
                        if "vue_m_fin" in it and it["s1"] > it["s0"]:
                            t = (ld - it["s0"]) / (it["s1"] - it["s0"])
                            it["vue_m"] = round(it["vue_m"] + (it["vue_m_fin"] - it["vue_m"]) * t, 3)
                        it["s0"] = ld
                    nouv.append(it)
                nouv = [a] + nouv
            else:
                s_d = b.L - ld
                for it in its:
                    if it["s0"] >= s_d - 1e-9:
                        continue
                    it = dict(it)
                    if it["s1"] > s_d:
                        if "vue_m_fin" in it and it["s1"] > it["s0"]:
                            t = (s_d - it["s0"]) / (it["s1"] - it["s0"])
                            it["vue_m_fin"] = round(it["vue_m"] + (it["vue_m_fin"] - it["vue_m"]) * t, 3)
                        it["s1"] = s_d
                    nouv.append(it)
                nouv.append({"s0": s_d, "s1": b.L, "profil": its[-1]["profil"], "vue_m": round(v, 3), "vue_m_fin": 0.0,
                             "role": "chartiere"})
            if bout == 0:
                empiete = any(it.get("abaisse") and it["s0"] < ld + 1e-6 for it in its)
            else:
                empiete = any(it.get("abaisse") and it["s1"] > b.L - ld - 1e-6 for it in its)
            if empiete:
                continue                                  # la descente empiéterait sur un abaissé
            b.p["intervalles"] = nouv
            its = nouv
            descentes.append((b.id, bout, ld, v))
    # ---- GA-BOR-005 : raccords aux contacts bout à bout entre bordures de vues différentes (> 2 cm) :
    # la plus haute descend vers la vue de l'autre sur Δvue / 6 % (0,5 à 2 m), bout courant seulement
    raccords_contact = []
    A_ = np.vstack([b.P[:-1] for b in bords])
    B_ = np.vstack([b.P[1:] for b in bords])
    own = np.concatenate([np.full(len(b.P) - 1, k) for k, b in enumerate(bords)])
    vue_bout = lambda b, bout: (b.p["intervalles"][0]["vue_m"] if bout == 0 else
                                b.p["intervalles"][-1].get("vue_m_fin", b.p["intervalles"][-1]["vue_m"]))
    for k, b in enumerate(bords):
        for bout in (0, -1):
            sel = own != k
            d, j, pr = distance_segments(b.P[bout][None], A_[sel], B_[sel])
            if d[0] > 0.3:
                continue
            o = bords[own[sel][j[0]]]
            so, _ = G.projeter_sur(o.P, pr)
            if min(so[0], o.L - so[0]) > 0.3:
                continue                                  # contact en T : pas une continuité de file
            bo = 0 if so[0] <= o.L / 2 else -1
            va, vo = vue_bout(b, bout), vue_bout(o, bo)
            if va - vo <= 0.02 or b.r_bas != o.r_bas:
                continue
            its = b.p["intervalles"]
            it_b = its[0] if bout == 0 else its[-1]
            if it_b.get("role") != "courant" or b.L < 1.5:
                continue
            lr = float(min(2.0, max(0.5, (va - vo) / 0.06), 0.45 * b.L))
            if bout == 0:
                nouv = [{"s0": 0.0, "s1": lr, "profil": it_b["profil"], "vue_m": round(vo, 3), "vue_m_fin": round(va, 3),
                         "role": "chartiere"}] + [dict(it, s0=max(it["s0"], lr)) for it in its if it["s1"] > lr + 1e-6]
            else:
                nouv = [dict(it, s1=min(it["s1"], b.L - lr)) for it in its if it["s0"] < b.L - lr - 1e-6] +                        [{"s0": b.L - lr, "s1": b.L, "profil": it_b["profil"], "vue_m": round(va, 3), "vue_m_fin": round(vo, 3),
                         "role": "chartiere"}]
            if any(it.get("abaisse") for it in (nouv[1:2] if bout == 0 else nouv[-2:-1])):
                continue
            b.p["intervalles"] = nouv
            raccords_contact.append((b.id, bout, o.id, round(va, 3), round(vo, 3), lr))
    # ---- ordre de résolution
    surf_reg = collections.defaultdict(float)
    for k in ks:
        if classe_face[k] == "chaussee":
            surf_reg[reg_face[k]] += faces[k]["aire"]
    r_route = max(surf_reg.items(), key=lambda kv: (kv[1], -kv[0]))[0] if surf_reg else 0
    deps = collections.defaultdict(set)
    for b in bords:
        if b.r_bas >= 0 and b.r_haut >= 0 and b.r_bas != b.r_haut:
            deps[b.r_bas].add(b.r_haut)
    ordre, vu = [], set()
    file_ = [r_route]
    while file_:
        r = file_.pop(0)
        if r in vu:
            continue
        vu.add(r)
        ordre.append(r)
        file_ += sorted(deps.get(r, ()))
    ordre += [r for r in range(len(regions)) if r not in vu]
    # ---- résolution région par région
    z = np.full((N, N), np.nan)
    d_glob = np.full((N, N), np.inf)              # distance à l'arête arrière d'une bordure de chaussée
    iters_reg = {}
    pieds = {}
    modeles_surf = {}
    ilot_de_face = _ilots_faces(I, faces, ks)
    fenetres = {k: boite(faces[k]["anneaux"], marge=1) for k in ks}
    # tables par face (indexées par l'étiquette ; -1 -> dernière case)
    NF = len(faces) + 1
    code_cl = np.zeros(NF, dtype=np.int8)        # 1 vert, 2 parking/accès/autre, 3 chaussée, 4 piéton, 5 emprise, 6 îlot
    for k in ks:
        cl = classe_face[k]
        mat = mat_face[k]
        if ilot_de_face.get(k) is not None:
            code_cl[k] = 6
        elif cl in CLASSES_VERTES or (cl == "ilot" and mat in REMPLIS):
            code_cl[k] = 1
        elif cl in ("parking", "acces_riverain", "autre"):
            code_cl[k] = 2
        elif cl == "chaussee":
            code_cl[k] = 3
        elif cl in CLASSES_PIETONNES:
            code_cl[k] = 4
        elif cl == "emprise_bordure":
            code_cl[k] = 5
    retrait_face = np.full(NF, RETRAIT_TROTTOIR)
    for k in ks:
        retrait_face[k] = _retrait(classe_face[k], mat_face[k], ilot_de_face.get(k))
    rampes_faces = {k: sprops[face_id[k]]["rampe"] for k in ks if "rampe" in sprops[face_id[k]]}
    noues = [k for k in ks if mat_face[k] == "noue_plantee"]
    # nœuds du côté haut derrière l'arête arrière de chaque bordure (≤ 0,14 m) et distance au dos des
    # bordures de chaussée (≤ 4,2 m, dans la région haute) : fenêtres de 10 m le long de la bordure
    for b in bords:
        b.arriere = _noeuds_derriere(b, 0.14, reg, b.r_haut, xs, ys)
        # nœuds derrière une partie MURET_TALUS (vue ≥ 0,30) : pas de Dirichlet (terrain au MNT)
        mur = [(it["s0"], it["s1"]) for it in b.p["intervalles"] if it["profil"] == "MURET_TALUS"]
        b.muret = None
        if mur and len(b.arriere[1]):
            sv_ = b.arriere[1]
            b.muret = np.zeros(len(sv_), bool)
            for a0, a1 in mur:
                b.muret |= (sv_ >= a0 - 0.5) & (sv_ <= a1 + 0.5)
        b.devers = None
        if b.bas_vehicule and b.r_haut >= 0:
            fl_, s_, dd_ = _noeuds_derriere(b, DEVERS_SUR_M + 0.2, reg, b.r_haut, xs, ys, bouts=True)
            if len(fl_):
                v = d_glob.ravel()
                np.minimum.at(v, fl_, np.maximum(dd_, 0.0))
                b.devers = (fl_, s_, np.maximum(dd_, 0.0))
    # bande de dévers : chaque nœud suit la bordure de chaussée la plus proche (GA-TRO-003)
    for b in bords:
        if b.devers is not None:
            fl_, s_, dd_ = b.devers
            garde = dd_ <= d_glob.ravel()[fl_] + 1e-9
            b.devers = (fl_[garde], s_[garde], dd_[garde])
    for r in ordre:
        mreg = reg == r
        if not mreg.any():
            continue
        jx, ix = np.nonzero(mreg)
        j0, j1, i0, i1 = max(0, jx.min() - 1), min(N, jx.max() + 2), max(0, ix.min() - 1), min(N, ix.max() + 2)
        zone = mreg[j0:j1, i0:i1]
        sx, sy = xs[j0:j1, i0:i1], ys[j0:j1, i0:i1]
        lb = lab[j0:j1, i0:i1]
        lbi = np.where(lb >= 0, lb, NF - 1)
        cc_ = np.where(zone, code_cl[lbi], 0)
        faces_r = [k for k in ks if reg_face[k] == r]

        def fen(k):
            a0, a1, b0, b1 = fenetres[k]
            return (slice(max(b0, j0) - j0, min(b1, j1) - j0), slice(max(a0, i0) - i0, min(a1, i1) - i0))
        # deux passes si des bordures ont leurs deux côtés dans la région (accès, rampes, fermetures) :
        # la 2e passe impose leur arête arrière avec le pied tiré de la 1re (TQ-SOL-013 (4)-(6))
        memes = [bb for bb in bords if bb.r_bas == r and bb.r_haut == r]
        x_init = np.where(np.isfinite(z_lisse[j0:j1, i0:i1]), z_lisse[j0:j1, i0:i1], 0.0)
        for passe in range(2 if memes else 1):
            fixe = np.zeros(zone.shape, bool)
            zf = np.zeros(zone.shape)
            # (1) chaussée OpenDRIVE
            zx = z_xodr[j0:j1, i0:i1]
            mx = zone & np.isfinite(zx)
            fixe |= mx
            zf[mx] = zx[mx]
            # (6)/(7)/(8) arêtes arrière des bordures dont cette région est le côté haut et dont la région
            # basse est résolue : tête − retrait (nœuds précalculés derrière l'arête arrière)
            for b in bords:
                if b.r_haut != r or b.id not in pieds or b.arriere is None:
                    continue
                pied, tete = pieds[b.id]
                fl_, s_, _ = b.arriere
                if b.muret is not None:                   # muret / talus : terrain haut au MNT (GA-TRO-006)
                    keep = ~b.muret
                    fl_, s_ = fl_[keep], s_[keep]
                gj, gi = fl_ // N, fl_ % N
                ok = (gj >= j0) & (gj < j1) & (gi >= i0) & (gi < i1)
                rj, ri = gj[ok] - j0, gi[ok] - i0
                ok2 = zone[rj, ri]
                rj, ri, sv_ = rj[ok2], ri[ok2], s_[ok][ok2]
                if not len(rj):
                    continue
                t_ = np.interp(sv_, b.s, tete)
                v_ = np.interp(sv_, b.s, tete - pied)
                fixe[rj, ri] = True
                # retrait sous la tête, jamais sous le pied (bateau à 0 : sol affleurant, GA-ABA-010)
                zf[rj, ri] = t_ - np.minimum(retrait_face[lbi[rj, ri]], np.maximum(v_, 0.0))
            d_route = d_glob[j0:j1, i0:i1]
            # bande de dévers des cheminements (GA-TRO-003) : cible = tête − retrait de la bordure de chaussée
            # la plus proche, le potentiel phi ajoutant 1,5 % en s'éloignant ; terme fort sur 4 m
            cible_dev = np.full(zone.shape, np.nan)
            for b in bords:
                if b.r_haut != r or b.id not in pieds or b.devers is None:
                    continue
                pied, tete = pieds[b.id]
                fl_, s_, dd_ = b.devers
                gj, gi = fl_ // N, fl_ % N
                ok = (gj >= j0) & (gj < j1) & (gi >= i0) & (gi < i1)
                rj, ri = gj[ok] - j0, gi[ok] - i0
                ok2 = zone[rj, ri]
                rj, ri, sv_ = rj[ok2], ri[ok2], s_[ok][ok2]
                v_ = np.interp(sv_, b.s, tete - pied)
                cible_dev[rj, ri] = np.interp(sv_, b.s, tete) - np.minimum(retrait_face[lbi[rj, ri]], np.maximum(v_, 0.0))
            # rampes analytiques (GA-ABA-003/005, GA-CHR-002)
            for k in faces_r:
                if k not in rampes_faces:
                    continue
                rp = rampes_faces[k]
                b = par_k.get(rp["bordure"])
                if b is None or b.id not in pieds:
                    continue
                sl = fen(k)
                mf = zone[sl] & (lb[sl] == k)
                if not mf.any():
                    continue
                Q = np.c_[sx[sl][mf], sy[sl][mf]]
                zr_ = z_rampe(b, pieds[b.id], rp, Q)
                fx_ = fixe[sl]
                zf_ = zf[sl]
                fx_[mf] = True
                zf_[mf] = zr_
                modeles_surf[face_id[k]] = "rampe_plan_incline"
            # potentiel de dévers (GA-TRO-003) : +1,5 % en s'éloignant de la chaussée, sur 4 m ; continu
            # (saturé à 4 m, et au-delà de toute bordure : une constante n'altère pas la solution)
            phi = DEVERS_TROTTOIR * np.minimum(d_route, DEVERS_SUR_M)
            # données (MNT conditionné) et poids, par classe de face (tables)
            zl, zg = z_lisse[j0:j1, i0:i1], z_large[j0:j1, i0:i1]
            lam = np.zeros(zone.shape)
            cible = np.where(np.isfinite(zl), zl, 0.0)
            lam[cc_ == 1] = LAMBDA_VERT                                # espaces verts : MNT lissé (TQ-SOL-007)
            m2 = (cc_ == 2) | ((cc_ == 3) & (r != r_route))
            lam[m2] = 0.01                                             # parkings, accès, autres chaussées
            cible[m2] = np.where(np.isfinite(zg[m2]), zg[m2], 0.0)
            if r == r_route:
                # chaussées hors .xodr et hors carrefour (rues des Saules Blancs, contre-allées) : MNT large ;
                # carrefour : membrane + axe de Verdun (TQ-SOL-014)
                jn = jonction[j0:j1, i0:i1]
                mh = (cc_ == 3) & ~jn & ~fixe
                lam[mh] = 0.01
                cible[mh] = np.where(np.isfinite(zg[mh]), zg[mh], 0.0)
                za = z_axe[j0:j1, i0:i1]
                ma = (cc_ == 3) & jn & np.isfinite(za) & ~fixe
                lam[ma] = 0.02
                cible[ma] = za[ma]
            m4 = cc_ == 4
            dr = np.where(np.isfinite(d_route), d_route, 99.0)
            lam[m4] = 0.004 * np.clip((dr[m4] - 3.0) / 3.0, 0.0, 1.0)    # piéton : loin des bordures, MNT large
            cible[m4] = np.where(np.isfinite(zg[m4]), zg[m4], 0.0)
            md = m4 & np.isfinite(cible_dev) & (dr < DEVERS_SUR_M)
            lam_d = LAMBDA_DEVERS * np.clip(DEVERS_SUR_M - dr[md], 0.0, 1.0)     # atténué sur le dernier mètre
            w_far = lam[md]
            cible[md] = (lam_d * (cible_dev[md] + phi[md]) + w_far * cible[md]) / np.maximum(lam_d + w_far, 1e-12)
            lam[md] = lam_d + w_far
            if not fixe[zone].any() and not (lam[zone] > 0).any():
                lam[zone] = 0.01
                cible[zone] = np.where(np.isfinite(zg[zone]), zg[zone], 0.0)
            # îlots : bombement (potentiel), sans données
            for k in faces_r:
                il = ilot_de_face.get(k)
                if il is None:
                    continue
                sl = fen(k)
                mf = zone[sl] & (lb[sl] == k)
                bomb = float(il["remplissage"].get("bombement_m", 0.0) or 0.0)
                if bomb > 0 and mf.any():
                    db = _distance_bord(faces[k]["anneaux"], np.c_[sx[sl][mf], sy[sl][mf]])
                    ph_ = phi[sl]
                    ph_[mf] = bomb * np.minimum(1.0, db / 1.0)
                modeles_surf[face_id[k]] = "ilot_tete_moins_retrait"
            h, nit = resoudre(zone, fixe, zf - phi, lam, cible - phi, x0=x_init - phi)
            zr = h + phi
            x_init = np.where(np.isfinite(zr), zr, x_init)
            # noue : talus à 1/3 au plus depuis la rive (GA-ASS-005)
            for k in noues:
                if reg_face[k] != r:
                    continue
                sl = fen(k)
                mf = zone[sl] & (lb[sl] == k)
                if not mf.any():
                    continue
                zr_s = zr[sl]
                zr_s[mf] = _talus_noue(faces[k]["anneaux"], np.c_[sx[sl][mf], sy[sl][mf]], zr_s[mf], zr_s,
                                       zone[sl] & ~mf, sx[sl], sy[sl])
                modeles_surf[face_id[k]] = "noue_talus_1_3"
            sub = z[j0:j1, i0:i1]
            sub[zone] = zr[zone]
            iters_reg[r] = iters_reg.get(r, 0) + nit
            # pieds et têtes des bordures dont cette région est le côté bas (TQ-SOL-013 (3)-(5))
            for b in bords:
                if b.r_bas != r:
                    continue
                pieds[b.id] = pied_tete(b, z, reg, r)
    # bordures sans région basse résolue : MNT (contrôle seulement)
    for b in bords:
        if b.id not in pieds:
            zb = mnt(*(repere(b.q - b.nrm * 0.3, "l93").T)) - Z_O
            v = b.vue(b.s)
            pieds[b.id] = (zb, zb + v)
    # ---- surfaces : modèle et statistiques
    for k in ks:
        sid = face_id[k]
        if sid in modeles_surf:
            continue
        cl = classe_face[k]
        if cl == "chaussee" and reg_face[k] == r_route:
            modeles_surf[sid] = "xodr_et_jonction_membrane"
        elif cl == "emprise_bordure":
            modeles_surf[sid] = "sous_bordure_pied"
        elif cl in CLASSES_VERTES:
            modeles_surf[sid] = "mnt_conditionne_raccorde"
        elif cl in CLASSES_PIETONNES:
            modeles_surf[sid] = "tete_moins_4mm_devers"
        else:
            modeles_surf[sid] = "membrane_mnt_lisse"
    grille = couches(z, reg)
    return dict(lab=lab, reg=reg, z=z, z_mnt=z_mnt, reg_face=reg_face, ordre=ordre, iters=iters_reg, pieds=pieds,
                d_route=d_glob, ilot_de_face=ilot_de_face, raccords_contact=raccords_contact,
                bords=bords, descentes=descentes, modeles=modeles_surf, r_route=r_route, grille=grille,
                classe_face=classe_face, xs=xs, ys=ys, z_xodr=z_xodr, est_chaussee=est_chaussee,
                route_noeud=route_noeud)


def _noeuds_derriere(b, marge, reg, r_haut, xs, ys, pas_morceau=10.0, bouts=False):
    """Nœuds de la région r_haut du côté haut de la bordure, entre l'arête arrière (− 2 cm) et
    `marge` derrière : (indices plats, abscisse s, distance à l'arête arrière). Projection par
    morceaux de 10 m (fenêtres serrées autour de la bordure). `bouts` : garde aussi les nœuds au-delà
    des extrémités (distance radiale), pour un potentiel de dévers continu."""
    from commun import sous_polyligne
    fl, ss, dd = [], [], []
    k0 = 0.0
    while k0 < b.L - 1e-9:
        k1 = min(b.L, k0 + pas_morceau)
        a0, a1 = max(0.0, k0 - 0.5), min(b.L, k1 + 0.5)
        seg = sous_polyligne(b.P, a0, a1)
        m = 0.4 + marge
        x0, y0 = seg.min(axis=0) - m
        x1, y1 = seg.max(axis=0) + m
        i0, i1 = max(0, int((x0 - X0) / PAS)), min(N, int((x1 - X0) / PAS) + 2)
        j0, j1 = max(0, int((y0 - Y0) / PAS)), min(N, int((y1 - Y0) / PAS) + 2)
        if i1 > i0 and j1 > j0:
            win = reg[j0:j1, i0:i1] == r_haut
            if win.any():
                jj, ii = np.nonzero(win)
                Q = np.c_[xs[j0:j1, i0:i1][win], ys[j0:j1, i0:i1][win]]
                s_p, d_p = G.projeter_sur(seg, Q)
                s_p = s_p + a0
                w = G.largeur_le_long(b.p["intervalles"], s_p)
                d_ = d_p - w
                ok = (d_ > -0.02) & (d_ <= marge) & (s_p >= k0) & (s_p < k1 + (1e-9 if k1 >= b.L else 0.0))                     & (bouts | ((s_p > 0.02) & (s_p < b.L - 0.02)))
                fl.append((jj[ok] + j0) * N + (ii[ok] + i0))
                ss.append(s_p[ok])
                dd.append(d_[ok])
        k0 = k1
    if not fl:
        return np.zeros(0, int), np.zeros(0), np.zeros(0)
    return np.concatenate(fl), np.concatenate(ss), np.concatenate(dd)


def _retrait(classe, materiau, ilot):
    """Retrait sous la tête de bordure du sol du côté haut (TQ-SOL-013 (6)-(8), GA-ARB-003)."""
    if ilot is not None:
        return float(ilot["remplissage"].get("retrait_sous_bordure_m", 0.0) or 0.0) or RETRAIT_TROTTOIR
    if classe in CLASSES_VERTES:
        return 0.03 if materiau in ("brf_bois_concasse", "gravier_concasse_6_10") else RETRAIT_VERT
    return RETRAIT_TROTTOIR


def _ilots_faces(I, faces, ks):
    """{face: propriétés de l'îlot qui la contient} (faces intérieures des îlots)."""
    out = {}
    if not I:
        return out
    polys = []
    for f in I:
        g = f["geometry"]
        rs = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        polys.append((f["properties"], [[repere(np.asarray(r, float)[:-1, :2]) for r in p] for p in rs]))
    from commun import dans_polygone
    for k in ks:
        pi = SP.point_interieur(faces[k]["anneaux"])
        for props, pp in polys:
            if any(dans_polygone(pi[None], p)[0] for p in pp):
                out[k] = props
                break
    return out


def _distance_bord(anneaux, Q):
    A = np.vstack(anneaux)
    B = np.vstack([np.roll(r, -1, axis=0) for r in anneaux])
    d, _, _ = distance_segments(Q, A, B)
    return d


def _talus_noue(anneaux, Q, zq, z_sub, autour, sx, sy):
    """Enveloppe des talus à 1/3 depuis la rive de la noue (z rive − d/3) : le fond reste celui du MNT."""
    A = np.vstack(anneaux)
    B = np.vstack([np.roll(r, -1, axis=0) for r in anneaux])
    L = np.hypot(*(B - A).T)
    pts = []
    for a, b, l in zip(A, B, L):
        n = max(1, int(math.ceil(l / 0.5)))
        pts.append(a + (b - a) * (np.arange(n)[:, None] / n))
    R = np.vstack(pts)
    # Z de rive : nœud voisin hors noue le plus proche (dans la boîte de la noue + 0,5 m)
    x0, y0 = A.min(axis=0) - 0.5
    x1, y1 = A.max(axis=0) + 0.5
    pres = autour & np.isfinite(z_sub) & (sx >= x0) & (sx <= x1) & (sy >= y0) & (sy <= y1)
    if not pres.any():
        return zq
    C = np.c_[sx[pres], sy[pres]]
    zc = z_sub[pres]
    dmin, _, _ = distance_segments(C, A, B)
    C, zc = C[dmin <= 0.25], zc[dmin <= 0.25]
    if len(C) == 0:
        return zq
    zr = np.empty(len(R))
    for k0 in range(0, len(R), 256):
        d = np.hypot(R[k0:k0 + 256, None, 0] - C[None, :, 0], R[k0:k0 + 256, None, 1] - C[None, :, 1])
        zr[k0:k0 + 256] = zc[np.argmin(d, axis=1)]
    env = np.full(len(Q), -np.inf)
    for k0 in range(0, len(Q), 512):
        d = np.hypot(Q[k0:k0 + 512, None, 0] - R[None, :, 0], Q[k0:k0 + 512, None, 1] - R[None, :, 1])
        env[k0:k0 + 512] = np.max(zr[None, :] - d * TALUS_NOUE, axis=1)
    return np.maximum(zq, env)


def pied_tete(b, z, reg, r):
    """Pied (fil d'eau ou pied de face) et tête de la bordure aux abscisses b.s (TQ-SOL-013 (3)-(5)) :
    Z de la région basse à 0,05 m devant la face ; caniveau CS2 : Z à 0,25 m devant − 2,5 cm."""
    avant = b.q - b.nrm * 0.05
    zc = _bilin(z, reg, r, avant)
    can = b.caniveau(b.s)
    if can.any():
        z_bord = _bilin(z, reg, r, b.q - b.nrm * 0.27)
        zc = np.where(can & np.isfinite(z_bord), z_bord - DENIVELE_CS2, zc)
    if np.isnan(zc).any():
        ok = np.isfinite(zc)
        zc = np.interp(b.s, b.s[ok], zc[ok]) if ok.any() else np.zeros(len(b.s))
    # lissage léger du profil en long (éléments rigides de 1 m) : σ 0,5 m
    ws = np.exp(-0.5 * ((b.s[:, None] - b.s[None, :]) / 0.5) ** 2)
    zc = (ws @ zc) / ws.sum(axis=1)
    return zc, zc + b.vue(b.s)


def _bilin(z, reg, r, Q):
    fi = (Q[:, 0] - X0) / PAS
    fj = (Q[:, 1] - Y0) / PAS
    i0 = np.clip(np.floor(fi).astype(int), 0, N - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, N - 2)
    ti, tj = fi - i0, fj - j0
    num = np.zeros(len(Q))
    den = np.zeros(len(Q))
    for dj, di, w in ((0, 0, (1 - ti) * (1 - tj)), (0, 1, ti * (1 - tj)), (1, 0, (1 - ti) * tj), (1, 1, ti * tj)):
        v = z[j0 + dj, i0 + di]
        ok = (reg[j0 + dj, i0 + di] == r) & np.isfinite(v)
        num[ok] += w[ok] * v[ok]
        den[ok] += w[ok]
    return np.where(den > 1e-6, num / np.maximum(den, 1e-12), np.nan)


def z_rampe(b, pied_tete_, rp, Q):
    """Plan incliné derrière un abaissé (GA-ABA-003, GA-ABA-005, GA-CHR-002) : surface réglée entre
    l'arête arrière (tête − 4 mm, vue décrite le long de la file) et l'arête lointaine à la profondeur D
    (niveau courant du trottoir : pied + vue courante − 4 mm + dévers)."""
    pied, tete = pied_tete_
    s_p, d_p = G.projeter_sur(b.P, Q)
    w = G.largeur_le_long(b.p["intervalles"], s_p)
    D = max(0.3, float(rp["profondeur_m"]))
    t = np.clip((d_p - w) / D, 0.0, 1.0)
    z_proche = np.interp(s_p, b.s, tete) - RETRAIT_TROTTOIR
    v_cour = float(rp["denivele_m"]) + float(np.interp(0.5 * (rp["s0"] + rp["s1"]), b.s, tete - pied))
    v_cour = max(v_cour, float(np.max(np.interp(np.array([rp["s0"], rp["s1"]]), b.s, tete - pied))))
    z_loin = np.interp(s_p, b.s, pied) + v_cour - RETRAIT_TROTTOIR + DEVERS_TROTTOIR * D
    return z_proche + (z_loin - z_proche) * t


def couches(z, reg, n_ext=2):
    """Couches de la grille : propriétaire (z0, r0) et prolongements (z1, r1), (z2, r2) des régions
    voisines sur `n_ext` nœuds (moyenne des voisins connus, deux anneaux)."""
    z0 = np.where(np.isfinite(z), z, np.nan).astype(np.float32)
    r0 = reg.astype(np.int32)
    z1 = np.full(z.shape, np.nan, np.float32)
    r1 = np.full(z.shape, -1, np.int32)
    z2 = np.full(z.shape, np.nan, np.float32)
    r2 = np.full(z.shape, -1, np.int32)
    for r in sorted(set(np.unique(reg).tolist()) - {-1}):
        m = reg == r
        jx, ix = np.nonzero(m)
        j0, j1 = max(0, jx.min() - n_ext - 1), min(z.shape[0], jx.max() + n_ext + 2)
        i0, i1 = max(0, ix.min() - n_ext - 1), min(z.shape[1], ix.max() + n_ext + 2)
        connu = m[j0:j1, i0:i1].copy()
        val = np.where(connu, z[j0:j1, i0:i1], 0.0)
        for _ in range(n_ext):
            s = np.zeros(connu.shape)
            c = np.zeros(connu.shape)
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                sh_c = np.roll(np.roll(connu, dj, 0), di, 1)
                sh_v = np.roll(np.roll(val, dj, 0), di, 1)
                s += np.where(sh_c, sh_v, 0.0)
                c += sh_c
            nouv = ~connu & (c > 0)
            val = np.where(nouv, s / np.maximum(c, 1), val)
            connu = connu | nouv
        ext = connu & ~m[j0:j1, i0:i1]
        for zc, rc in ((z1, r1), (z2, r2)):
            libre = ext & (rc[j0:j1, i0:i1] < 0) & (r0[j0:j1, i0:i1] != r)
            zs, rs = zc[j0:j1, i0:i1], rc[j0:j1, i0:i1]
            zs[libre] = val[libre]
            rs[libre] = r
            ext = ext & ~libre
    return {"x0": X0, "y0": Y0, "pas": PAS, "z0": z0, "r0": r0, "z1": z1, "r1": r1, "z2": z2, "r2": r2}


# --------------------------------------------------------------------------- contrôles
def _pente_meme_region(z, reg, base):
    """Pentes |Δz| / base en x et en y sur une base de `base` nœuds, entre nœuds de même région."""
    out = np.zeros(z.shape)
    for ax in (0, 1):
        a = [slice(None), slice(None)]
        b = [slice(None), slice(None)]
        a[ax] = slice(0, -base)
        b[ax] = slice(base, None)
        ok = (reg[tuple(a)] == reg[tuple(b)]) & (reg[tuple(a)] >= 0)
        d = np.where(ok, np.abs(z[tuple(b)] - z[tuple(a)]), 0.0) / (base * PAS)
        tmp = np.zeros(z.shape)
        tmp[tuple(a)] = np.nan_to_num(d)
        out = np.maximum(out, tmp)
    return out


def _quantiles(v, qs=(50, 95, 99)):
    v = np.asarray(v, dtype=np.float64)
    v = v[np.isfinite(v)]
    if not len(v):
        return None
    out = {f"p{q}": float(np.percentile(v, q)) for q in qs}
    out.update(max=float(v.max()), n=int(len(v)))
    return out


def controles(R, K, S, partition):
    """Contrôles du nivellement (règles d'action « verifier ») mesurés sur la grille et les bordures."""
    z, reg, lab = R["z"], R["reg"], R["lab"]
    face_id = partition["face_id"]
    sprops = {f["properties"]["id"]: f["properties"] for f in S}
    NF = int(max(face_id) + 2) if face_id else 1
    l_cl = np.zeros(NF, dtype=np.int8)            # 1 chaussée, 2 marchable, 3 vert (talus naturels admis)
    l_ra, l_no, l_ba, l_tr = (np.zeros(NF, bool) for _ in range(4))
    for k, sid in face_id.items():
        p = sprops[sid]
        l_cl[k] = 1 if p["classe"] == "chaussee" else (2 if p["classe"] in ("trottoir", "quai_bus", "piste_cyclable") else
                                                       (3 if p["classe"] in CLASSES_VERTES else 0))
        l_ra[k] = "rampe" in p
        l_no[k] = p["revetement"]["materiau_id"] == "noue_plantee"
        l_ba[k] = p["classe"] == "emprise_bordure"
        l_tr[k] = p["classe"] == "trottoir"
    li = np.where(lab >= 0, lab, NF - 1)
    rampe, noue, bande = l_ra[li], l_no[li], l_ba[li]
    # les marches portées par une bordure (de part et d'autre de son emprise, plus étroite qu'un pas de
    # grille pour une P1) ne sont pas des défauts : emprise élargie d'un nœud pour le contrôle VAL-SOL-009
    lignes_k = []
    for b in R["bords"]:
        lignes_k.append(b.P)
        lignes_k.append(G.arete_arriere(b.P, b.p["intervalles"]))
    bande_ctrl = bande | masque_lignes(lignes_k, 3)
    marchable = (l_cl[li] == 2) | rampe
    est_ch = l_cl[li] == 1
    vert = l_cl[li] == 3
    out = {}
    # TQ-SOL-004 : modèle OpenDRIVE vs MNT 2026 (contrôle seulement)
    mx = np.isfinite(R["z_xodr"])
    e = np.abs(R["z_xodr"][mx] - R["z_mnt"][mx])
    q = _quantiles(e) or {}
    out["TQ-SOL-004_xodr_mnt_m"] = dict(q, seuil_p95_m=0.03, alerte_m=0.05, conforme=bool(q and q["p95"] <= 0.05))
    # TQ-SOL-013 : pied de bordure (modèle) vs fil d'eau MNT décrit avant nivellement (contrôle)
    ecarts = []
    for b in R["bords"]:
        if b.id not in R["pieds"]:
            continue
        C = np.asarray(b.f["geometry"]["coordinates"], dtype=np.float64)
        S0 = abscisses(C[:, :2])
        pied = np.interp(S0, b.s, R["pieds"][b.id][0])
        ecarts.append(np.abs(pied - (C[:, 2] - Z_O)))
    q = (_quantiles(np.concatenate(ecarts)) if ecarts else None) or {}
    out["TQ-SOL-013_pied_vs_fil_eau_mnt_m"] = dict(q, seuil_p95_m=0.03, alerte_m=0.05, conforme=bool(q and q["p95"] <= 0.05))
    # GA-TRO-003 : dévers des trottoirs (pente vers la chaussée), 4 premiers mètres, hors rampes
    gy, gx = np.gradient(np.where(np.isfinite(z), z, 0.0), PAS)
    dd_ = np.where(np.isfinite(R["d_route"]), np.minimum(R["d_route"], 50.0), 50.0)
    dy, dx = np.gradient(dd_, PAS)
    nd = np.hypot(dx, dy)
    sel = marchable & ~rampe & np.isfinite(R["d_route"]) & (R["d_route"] > 0.3) & (R["d_route"] < DEVERS_SUR_M) & (nd > 0.5)
    for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sel &= np.roll(np.roll(reg, dj, 0), di, 1) == reg
    dev = 100.0 * (gx * dx + gy * dy)[sel] / nd[sel]
    q = _quantiles(dev, (5, 50, 95)) or {}
    out["GA-TRO-003_devers_trottoirs_pct"] = dict(
        q, part_1_2=float(np.mean((dev >= 1.0) & (dev <= 2.0))) if len(dev) else None,
        part_sup_2=float(np.mean(dev > 2.0)) if len(dev) else None,
        part_negatif=float(np.mean(dev < 0.0)) if len(dev) else None, seuil_max_pct=2.0, seuil_min_pct=1.0)
    dtr = (100.0 * (gx * dx + gy * dy) / np.maximum(nd, 1e-9))[sel & l_tr[li]]
    if len(dtr):
        out["GA-TRO-003_devers_trottoirs_pct"]["classe_trottoir"] = dict(
            _quantiles(dtr, (5, 50, 95)), part_0_2=float(np.mean((dtr >= 0.0) & (dtr <= 2.0))),
            part_1_2=float(np.mean((dtr >= 1.0) & (dtr <= 2.0))), part_negatif=float(np.mean(dtr < 0.0)))
    # GA-TRO-004 : pentes des cheminements (fenêtres de 0,5 m et 2 m)
    p05 = _pente_meme_region(z, reg, 5)
    p20 = _pente_meme_region(z, reg, 20)
    m = marchable & np.isfinite(z)
    mr = rampe & np.isfinite(z)
    out["GA-TRO-004_pentes_cheminements"] = {
        "noeuds": int(m.sum()),
        "pente_2m_p95_pct": float(np.percentile(100 * p20[m], 95)) if m.any() else None,
        "pente_2m_max_pct": float(100 * p20[m].max()) if m.any() else None,
        "part_2m_sup_5pct": float(np.mean(p20[m] > 0.05)) if m.any() else None,
        "part_2m_sup_8pct": float(np.mean(p20[m] > 0.08)) if m.any() else None,
        "part_05m_sup_12pct": float(np.mean(p05[m] > 0.12)) if m.any() else None,
        "rampes_pente_2m_p95_pct": float(np.percentile(100 * p20[mr], 95)) if mr.any() else None,
        "rampes_pente_2m_max_pct": float(100 * p20[mr].max()) if mr.any() else None,
        "seuils_pct": {"courant": 5, "sur_2m": 8, "sur_0_5m": 12}}
    # VAL-SOL-009 (1) / E8 : marches dans une même région (|Δz| > 3 cm entre nœuds voisins), hors emprises de
    # bordure et noues
    marches = []
    for ax in (0, 1):
        a = [slice(None), slice(None)]
        b = [slice(None), slice(None)]
        a[ax] = slice(0, -1)
        b[ax] = slice(1, None)
        ok = (reg[tuple(a)] == reg[tuple(b)]) & (reg[tuple(a)] >= 0)
        ok &= ~(bande_ctrl[tuple(a)] | bande_ctrl[tuple(b)] | noue[tuple(a)] | noue[tuple(b)])
        ok &= ~(vert[tuple(a)] | vert[tuple(b)])           # E8 : talus des espaces verts exclus
        d = np.abs(z[tuple(b)] - z[tuple(a)])
        mm = ok & (d > 0.03)
        jj, ii = np.nonzero(mm)
        marches += [(float(v), int(j), int(i)) for v, j, i in zip(d[mm], jj, ii)]
    marches.sort(reverse=True)
    out["VAL-SOL-009_marches_meme_region"] = {
        "n_aretes_sup_3cm": len(marches),
        "n_aretes_sup_45deg": int(sum(1 for v, _, _ in marches if v > 0.10)),
        "pires": [{"dz_m": round(v, 3), "x": round(X0 + i * PAS, 1), "y": round(Y0 + j * PAS, 1)} for v, j, i in marches[:15]]}
    # VAL-SOL-009 (4), TQ-SOL-014 : pente résultante de la chaussée ≥ 0,5 % ; points bas (GA-CHA-004)
    ch = est_ch & np.isfinite(z)
    g = np.hypot(gx, gy)
    jct = ch & ~np.isfinite(R["z_xodr"])
    out["VAL-SOL-009_TQ-SOL-014_chaussee"] = {
        "part_pente_inf_0_5pct": float(np.mean(g[ch] < 0.005)) if ch.any() else None,
        "part_pente_inf_0_5pct_hors_xodr": float(np.mean(g[jct] < 0.005)) if jct.any() else None,
        "pente_p50_pct": float(100 * np.median(g[ch])) if ch.any() else None}
    zz = np.where(ch, z, np.inf)
    minima = ch.copy()
    minima[:5, :] = minima[-5:, :] = False                # bord du site (0,5 m) : hors contrôle
    minima[:, :5] = minima[:, -5:] = False
    for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        minima &= zz < np.roll(np.roll(zz, dj, 0), di, 1) - 1e-4
    jj, ii = np.nonzero(minima)
    out["GA-CHA-004_points_bas_chaussee"] = {
        "n": int(len(jj)), "avaloirs_decrits": 0,
        "exemples": [[round(X0 + i * PAS, 1), round(Y0 + j * PAS, 1)] for j, i in list(zip(jj, ii))[:10]]}
    # GA-ASS-005 : talus de la noue ≤ 1/3
    mn = noue & np.isfinite(z)
    out["GA-ASS-005_noue"] = {"pente_05m_max_pct": float(100 * p05[mn].max()) if mn.any() else None,
                              "pente_2m_max_pct": float(100 * p20[mn].max()) if mn.any() else None, "seuil_pct": 33.3}
    # GA-BOR-005 : compatibilité des niveaux aux contacts entre bordures (tête ≤ 2 cm, pied ≤ 1 cm)
    contacts = []
    bl = R["bords"]
    A = np.vstack([b.P[:-1] for b in bl])
    B = np.vstack([b.P[1:] for b in bl])
    own = np.concatenate([np.full(len(b.P) - 1, k) for k, b in enumerate(bl)])
    for k, b in enumerate(bl):
        if b.id not in R["pieds"]:
            continue
        for bout in (0, -1):
            qe = b.P[bout]
            sel = own != k
            d, j, pr = distance_segments(qe[None], A[sel], B[sel])
            if d[0] > 0.3:
                continue
            o = bl[own[sel][j[0]]]
            if o.id not in R["pieds"]:
                continue
            so, _ = G.projeter_sur(o.P, pr)
            te = R["pieds"][b.id][1][0 if bout == 0 else -1]
            pe = R["pieds"][b.id][0][0 if bout == 0 else -1]
            to = float(np.interp(so[0], o.s, R["pieds"][o.id][1]))
            po = float(np.interp(so[0], o.s, R["pieds"][o.id][0]))
            bout_a_bout = bool(min(so[0], o.L - so[0]) <= 0.3)
            contacts.append({"bordure": b.id, "bout": "debut" if bout == 0 else "fin", "contre": o.id,
                             "bout_a_bout": bout_a_bout,
                             "dtete_m": round(abs(te - to), 3), "dpied_m": round(abs(pe - po), 3)})
    en_t = [c for c in contacts if not c["bout_a_bout"]]
    contacts = [c for c in contacts if c["bout_a_bout"]]
    dt = np.array([c["dtete_m"] for c in contacts]) if contacts else np.zeros(0)
    dp = np.array([c["dpied_m"] for c in contacts]) if contacts else np.zeros(0)
    out["GA-BOR-005_contacts"] = {
        "n_contacts_en_t": len(en_t),
        "n_contacts": len(contacts), "n_tete_sup_2cm": int((dt > 0.02).sum()), "n_pied_sup_1cm": int((dp > 0.01).sum()),
        "dtete_max_m": float(dt.max()) if len(dt) else None, "dpied_max_m": float(dp.max()) if len(dp) else None,
        "pires": sorted(contacts, key=lambda c: (-c["dtete_m"], c["bordure"]))[:12],
        "fins_libres_descendues": len(R["descentes"])}
    return arrondi(out, 4)


# --------------------------------------------------------------------------- écriture
def _npz_deterministe(data):
    """Archive npz à dates de fichiers fixes (sortie identique à l'octet d'une exécution à l'autre)."""
    import io
    import zipfile
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for nom in sorted(src.namelist()):
            zi = zipfile.ZipInfo(nom, date_time=(2026, 10, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            dst.writestr(zi, src.read(nom))
    return out.getvalue()


def ecrire(dossier, R, K, S, partition, ctrl):
    """base/nivellement.json + base/nivellement_grille.npz ; renvoie (json, npz)."""
    import io
    import json
    from pathlib import Path
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    g = R["grille"]
    f_npz = dossier / "nivellement_grille.npz"
    buf = io.BytesIO()
    np.savez_compressed(buf, x0=np.float64(g["x0"]), y0=np.float64(g["y0"]), pas=np.float64(g["pas"]),
                        z0=g["z0"], r0=g["r0"].astype(np.int16), z1=g["z1"], r1=g["r1"].astype(np.int16),
                        z2=g["z2"], r2=g["r2"].astype(np.int16))
    f_npz.write_bytes(_npz_deterministe(buf.getvalue()))
    face_id = partition["face_id"]
    sprops = {f["properties"]["id"]: f["properties"] for f in S}
    z, lab = R["z"], R["lab"]
    surfs = []
    reg_surf = collections.defaultdict(list)
    fl = lab.ravel()
    zl = z.ravel()
    ordre_n = np.argsort(fl, kind="stable")
    fl_t = fl[ordre_n]
    debut = np.searchsorted(fl_t, np.arange(fl_t.max() + 2))
    for k in sorted(face_id, key=lambda k: face_id[k]):
        sid = face_id[k]
        r = int(R["reg_face"][k])
        reg_surf[r].append(sid)
        vals = zl[ordre_n[debut[k]:debut[k + 1]]] if k + 1 < len(debut) else np.zeros(0)
        vals = vals[np.isfinite(vals)]
        e = {"id": sid, "region": r, "modele": R["modeles"].get(sid, "membrane")}
        if len(vals):
            e.update(z_min=float(vals.min()), z_med=float(np.median(vals)), z_max=float(vals.max()))
        surfs.append(e)
    regions = []
    rang = {r: i for i, r in enumerate(R["ordre"])}
    for r in sorted(reg_surf):
        cl = collections.Counter(sprops[s]["classe"] for s in reg_surf[r])
        regions.append({"id": r, "rang": rang.get(r), "iterations": int(R["iters"].get(r, 0)),
                        "n_surfaces": len(reg_surf[r]), "classes": dict(sorted(cl.items())),
                        "route": bool(r == R["r_route"])})
    bords = []
    for b in R["bords"]:
        if b.id not in R["pieds"]:
            continue
        pied, tete = R["pieds"][b.id]
        s5 = np.unique(np.r_[np.arange(0.0, b.L, 0.5), b.L])
        bords.append({"id": b.id, "region_basse": int(b.r_bas), "region_haute": int(b.r_haut),
                      "s": s5.tolist(), "z_pied": np.interp(s5, b.s, pied).tolist(),
                      "z_tete": np.interp(s5, b.s, tete).tolist(),
                      "z_arriere": (np.interp(s5, b.s, tete) - RETRAIT_TROTTOIR).tolist(),
                      "caniveau": bool(b.caniveau(b.s).any())})
    doc = {
        "schema": "pj_nivellement/0.1",
        "regles": ["TQ-SOL-013", "CF-26", "TQ-SOL-004", "TQ-SOL-014", "TQ-SOL-007", "GA-CHA-001", "GA-TRO-003",
                   "GA-TRO-004", "GA-ABA-003", "GA-ABA-004", "GA-ABA-005", "GA-CHR-002", "GA-CHR-003", "GA-BOR-005",
                   "GA-ARB-003", "GA-ASS-005", "VAL-SOL-009"],
        "repere": "local = L93 − (917279.43, 6460289.98) ; z local = NGF − 216,30 ; m",
        "grille": {"fichier": f_npz.name, "x0": X0, "y0": Y0, "pas": PAS, "n": N,
                   "couches": "z0/r0 propriétaire du nœud ; z1/r1, z2/r2 prolongements (2 nœuds) des régions voisines ; NaN / -1 sinon",
                   "convention": "nœud (i, j) en (x0 + i·pas, y0 + j·pas), tableau [j, i]"},
        "requete": "recon/pcg/decrire/nivellement_requete.py : Nivellement(dossier_base).z(x, y, surface_id) ; z_bordure(id, s)",
        "constantes": {"retrait_trottoir_m": RETRAIT_TROTTOIR, "retrait_vert_m": RETRAIT_VERT,
                       "devers_trottoir_pct": 100 * DEVERS_TROTTOIR, "devers_sur_m": DEVERS_SUR_M,
                       "denivele_caniveau_cs2_m": DENIVELE_CS2, "talus_noue": "1/3"},
        "discontinuites": ["bordure_arriere", "bordure_bout", "batiment", "emprise"],
        "ordre_regions": [int(r) for r in R["ordre"]],
        "regions": regions,
        "surfaces": surfs,
        "bordures": bords,
        "descentes_fin_de_file": [{"bordure": k, "bout": "debut" if b == 0 else "fin", "longueur_m": l, "vue_m": v}
                                  for k, b, l, v in R["descentes"]],
        "raccords_contact": [{"bordure": k, "bout": "debut" if b == 0 else "fin", "contre": o, "vue_m": va,
                              "vue_contact_m": vo, "longueur_m": l} for k, b, o, va, vo, l in R["raccords_contact"]],
        "controles": ctrl,
    }
    f_json = dossier / "nivellement.json"
    f_json.write_text(json.dumps(arrondi(doc, 4), ensure_ascii=False, separators=(",", ":")) + "\n",
                      encoding="utf-8", newline="\n")
    return f_json, f_npz


def reecrire_bordures(K, R):
    """Z des sommets des bordures = pied du modèle (fil d'eau / pied de face, NGF) ; z_ref nivellement_2026."""
    par = {b.id: b for b in R["bords"]}
    for f in K:
        b = par.get(f["properties"]["id"])
        if b is None or b.id not in R["pieds"]:
            continue
        C = np.asarray(f["geometry"]["coordinates"], dtype=np.float64)
        S0 = abscisses(C[:, :2])
        pied = np.interp(S0, b.s, R["pieds"][b.id][0]) + Z_O
        f["geometry"]["coordinates"] = coords_geojson(np.c_[C[:, :2], pied])
        p = f["properties"]
        p["z_ref"] = "nivellement_2026"
        p["intervalles"] = arrondi(b.p["intervalles"])
        p["prov"]["z"] = {"src": "regle:regles_conception.TQ-SOL-013",
                          "ref": "modèle de nivellement unique : pied de face au contact de la chaussée (OpenDRIVE, jonction) "
                                 "ou de la surface basse, fil d'eau du caniveau CS2 (− 2,5 cm) ; MNT 2026 en contrôle",
                          "conf": "moyenne"}
