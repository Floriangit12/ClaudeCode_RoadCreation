"""Socle du vérificateur de règles : chemins, contexte (données chargées à la demande), géométrie numpy,
requêtes exactes sur les maillages fabriqués, rasters de contrôle et objet Resultat.

Repère : local = L93 − O, z = NGF − 216,30 (decrire/commun.repere, seule conversion). Aucune écriture hors de
recon/out/paquet_jardin/v2/controle. Python 3.11 + numpy + Pillow ; les USD sont lus par extraire_fabrication.py
(hython) et relus ici en .npz.
"""
import functools
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
sys.path.insert(0, str(RACINE / "recon/pcg/decrire"))
import commun as C  # noqa: E402
from nivellement_requete import Nivellement  # noqa: E402
import xodr_echantillonne as X  # noqa: E402

V2 = RACINE / "recon/out/paquet_jardin/v2"
DESCRIPTION = V2 / "description"
FABRIQUE = V2 / "fabrique_hda"
SORTIE = V2 / "controle"
CACHE = SORTIE / "cache"
SPECS = RACINE / "assets/specs"
DONNEES = RACINE / "recon/out/paquet_jardin/package/donnees"
SITE = RACINE / "data/sites/paquet_jardin"
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")
O = C.O
PAS_GRILLE = 0.10
X0 = Y0 = -150.0
N_GRILLE = 3001
PIETON = ("trottoir", "quai_bus")
CIRCULE = ("chaussee", "parking", "piste_cyclable", "acces_riverain")
ND = 4


def r4(v, nd=ND):
    if v is None:
        return None
    if isinstance(v, (list, tuple, np.ndarray)):
        return [r4(x, nd) for x in v]
    v = float(v)
    if not math.isfinite(v):
        return None
    return round(v, nd)


def stats(v, pct=(50, 95), nd=ND):
    v = np.asarray([x for x in np.ravel(v) if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    out = {"n": int(len(v)), "min": r4(v.min(), nd), "max": r4(v.max(), nd)}
    for p in pct:
        out[f"p{p}"] = r4(np.percentile(v, p), nd)
    return out


def sha256(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def l93(xy):
    a = np.asarray(xy, float)
    return [round(float(a[0]) + O[0], 2), round(float(a[1]) + O[1], 2)]


# ============================================================================ résultat d'une règle
POIDS = {"bloquant": 4.0, "majeur": 3.0, "mineur": 2.0, "info": 1.0}


class Resultat:
    """Mesure d'une règle : n_teste, n_ok, violations (entité, coordonnées locales et L93, valeur, seuil)."""

    def __init__(self, regle, cible, severite, methode, statut="implemente", limites=None):
        self.regle = regle
        self.cible = cible
        self.severite = severite
        self.methode = methode
        self.statut = statut
        self.limites = limites
        self.n_teste = 0
        self.n_ok = 0
        self.violations = []
        self.mesures = {}

    def tester(self, ok, entite=None, xy=None, valeur=None, seuil=None, detail=None, ecart=None, severite=None):
        self.n_teste += 1
        if ok:
            self.n_ok += 1
            return True
        v = {"entite": entite, "valeur": r4(valeur) if isinstance(valeur, (int, float, np.floating, np.integer))
             else valeur, "seuil": seuil, "detail": detail}
        if xy is not None and np.all(np.isfinite(np.asarray(xy, float)[:2])):
            v["xy_local"] = [round(float(xy[0]), 2), round(float(xy[1]), 2)]
            v["xy_l93"] = l93(xy)
        v["ecart"] = r4(ecart if ecart is not None else 1.0, 3)
        v["severite"] = severite or self.severite
        self.violations.append(v)
        return False

    def mesure(self, cle, val):
        self.mesures[cle] = val

    def dict(self, n_pires=12):
        pires = sorted(self.violations, key=lambda v: (-POIDS[v["severite"]], -(v["ecart"] or 0.0),
                                                        str(v.get("entite")), json.dumps(v.get("xy_local"))))
        nv = self.n_teste - self.n_ok
        return {"statut": self.statut, "cible": self.cible, "severite": self.severite, "methode": self.methode,
                "limites": self.limites, "n_teste": self.n_teste, "n_ok": self.n_ok, "n_violations": nv,
                "taux_conformite": r4(self.n_ok / self.n_teste, 3) if self.n_teste else None,
                "mesures": self.mesures, "pires_cas": pires[:n_pires], "_toutes": pires}


# registre des contrôles : id -> (fonction, cible, severite, methode, statut, limites)
REGISTRE = {}


def regle(rid, cible, severite, methode, statut="implemente", limites=None):
    def deco(f):
        REGISTRE[rid] = (f, cible, severite, methode, statut, limites)
        return f
    return deco


# ============================================================================ géométrie
def poly_local(geom):
    """GeoJSON (L93) -> liste de polygones [[ext, trous...]] en local (N, 2)."""
    return [[C.repere(r) for r in p] for p in C.anneaux(geom)]


def ligne_local(geom, z=False):
    t = geom["type"]
    cs = [geom["coordinates"]] if t == "LineString" else geom["coordinates"] if t == "MultiLineString" else []
    out = []
    for c in cs:
        a = np.asarray(c, float)
        out.append(C.repere(a[:, :3] if (z and a.shape[1] > 2) else a[:, :2]))
    return out


def aire(r):
    return abs(C.aire_signee(r))


def aire_poly(p):
    return aire(p[0]) - sum(aire(h) for h in p[1:])


def dans(Q, poly):
    Q = np.atleast_2d(np.asarray(Q, float))
    if not len(Q):
        return np.zeros(0, bool)
    lo, hi = poly[0].min(0), poly[0].max(0)
    m = (Q[:, 0] >= lo[0]) & (Q[:, 0] <= hi[0]) & (Q[:, 1] >= lo[1]) & (Q[:, 1] <= hi[1])
    out = np.zeros(len(Q), bool)
    if m.any():
        out[m] = C.dans_polygone(Q[m], poly)
    return out


def dans_liste(Q, polys):
    out = np.zeros(len(np.atleast_2d(Q)), bool)
    for p in polys:
        out |= dans(Q, p)
    return out


def segments(polys):
    A = np.vstack([r for p in polys for r in p]) if polys else np.zeros((0, 2))
    B = np.vstack([np.roll(r, -1, 0) for p in polys for r in p]) if polys else np.zeros((0, 2))
    return A, B


def dist_polys(Q, polys):
    """Distance de Q aux contours des polygones (0 à l'intérieur non garanti : voir dans_liste)."""
    A, B = segments(polys)
    d, _, _ = C.distance_segments(Q, A, B)
    return d


def dist_polyligne(Q, P):
    P = np.asarray(P, float)[:, :2]
    if len(P) < 2:
        return np.hypot(*(np.atleast_2d(Q)[:, :2] - P[0]).T)
    d, _, _ = C.distance_segments(Q, P[:-1], P[1:])
    return d


def densifier(P, pas):
    return C.densifier(np.asarray(P, float), pas)[0]


def point(P, s):
    """Point (2D) de la polyligne P à l'abscisse s."""
    return C.point_a(np.asarray(P, float)[:, :2], s)[0][0]


def normale_gauche(P):
    P = np.asarray(P, float)[:, :2]
    tg = np.gradient(P, axis=0)
    tg /= np.maximum(np.hypot(*tg.T), 1e-12)[:, None]
    return np.c_[-tg[:, 1], tg[:, 0]], tg


def cap_deg(u):
    return math.degrees(math.atan2(u[1], u[0])) % 360.0


def ecart_angle(a, b, mod=360.0):
    d = abs((a - b) % mod)
    return min(d, mod - d)


def grappes(Q, rayon):
    """Regroupe des points (N, 2) proches (< rayon) : étiquettes 0..k-1 (union-find sur grille de hachage)."""
    Q = np.asarray(Q, float)
    n = len(Q)
    if not n:
        return np.zeros(0, int)
    parent = np.arange(n)

    def trouver(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    cle = np.floor(Q / rayon).astype(np.int64)
    cellules = {}
    for i, (a, b) in enumerate(map(tuple, cle)):
        cellules.setdefault((a, b), []).append(i)
    for (a, b), idx in cellules.items():
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                autres = cellules.get((a + da, b + db))
                if not autres:
                    continue
                P = Q[idx]
                R = Q[autres]
                d = np.hypot(P[:, None, 0] - R[None, :, 0], P[:, None, 1] - R[None, :, 1])
                ii, jj = np.nonzero(d < rayon)
                for i, j in zip(ii, jj):
                    ri, rj = trouver(idx[i]), trouver(autres[j])
                    if ri != rj:
                        parent[max(ri, rj)] = min(ri, rj)
    racines = np.array([trouver(i) for i in range(n)])
    _, lab = np.unique(racines, return_inverse=True)
    return lab


# ============================================================================ maillages fabriqués
class RequeteMaillage:
    """Requêtes verticales exactes sur un ensemble de triangles (index de seaux de `cellule` m)."""

    def __init__(self, T, cellule=0.5, ids=None):
        T = np.asarray(T, np.float64)
        self.T = T
        self.ids = ids
        self.c = cellule
        xy = T[..., :2]
        lo, hi = xy.min(1), xy.max(1)
        self.o = (lo.min(0) if len(T) else np.zeros(2)) - 1e-6
        i0 = np.floor((lo - self.o) / cellule).astype(np.int64)
        i1 = np.floor((hi - self.o) / cellule).astype(np.int64)
        self.nx = int(i1[:, 0].max() + 2) if len(T) else 1
        self.ny = int(i1[:, 1].max() + 2) if len(T) else 1
        w = i1[:, 0] - i0[:, 0] + 1
        h = i1[:, 1] - i0[:, 1] + 1
        cnt = w * h
        tri = np.repeat(np.arange(len(T)), cnt)
        k = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        cx = i0[tri, 0] + k % w[tri]
        cy = i0[tri, 1] + k // w[tri]
        cid = cy * self.nx + cx
        o = np.argsort(cid, kind="stable")
        self.tri = tri[o]
        self.start = np.searchsorted(cid[o], np.arange(self.nx * self.ny + 1))
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        self.a = a
        self.e1 = b - a
        self.e2 = c - a
        self.det = self.e1[:, 0] * self.e2[:, 1] - self.e1[:, 1] * self.e2[:, 0]

    def requete(self, Q, mode="max", eps=1e-9, toutes=False):
        """z (NaN sans triangle), indice du triangle retenu, nombre de triangles touchés. mode : max | min."""
        Q = np.atleast_2d(np.asarray(Q, float))[:, :2]
        n = len(Q)
        zout = np.full(n, np.nan)
        tout = np.full(n, -1, np.int64)
        nb = np.zeros(n, np.int32)
        zmin = np.full(n, np.nan)
        if not len(self.T):
            return (zout, tout, nb, zmin) if toutes else (zout, tout, nb)
        ij = np.floor((Q - self.o) / self.c).astype(np.int64)
        ok = (ij[:, 0] >= 0) & (ij[:, 0] < self.nx) & (ij[:, 1] >= 0) & (ij[:, 1] < self.ny)
        cid = np.where(ok, ij[:, 1] * self.nx + ij[:, 0], 0)
        s0 = self.start[cid]
        cnt = np.where(ok, self.start[cid + 1] - s0, 0)
        lot = 4_000_000
        bornes = [0]
        cum = np.cumsum(cnt)
        while bornes[-1] < n:
            base = cum[bornes[-1] - 1] if bornes[-1] > 0 else 0
            j = int(np.searchsorted(cum, base + lot, side="right"))
            bornes.append(max(j, bornes[-1] + 1))
        for p0, p1 in zip(bornes[:-1], bornes[1:]):
            c = cnt[p0:p1]
            if c.sum() == 0:
                continue
            pi = np.repeat(np.arange(p0, p1), c)
            k = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)
            ti = self.tri[s0[pi] + k]
            d = Q[pi] - self.a[ti, :2]
            det = self.det[ti]
            good = np.abs(det) > 1e-14
            with np.errstate(divide="ignore", invalid="ignore"):
                u = (d[:, 0] * self.e2[ti, 1] - d[:, 1] * self.e2[ti, 0]) / det
                v = (self.e1[ti, 0] * d[:, 1] - self.e1[ti, 1] * d[:, 0]) / det
            dedans = good & (u >= -eps) & (v >= -eps) & (u + v <= 1 + eps)
            pi, ti, u, v = pi[dedans], ti[dedans], u[dedans], v[dedans]
            z = self.a[ti, 2] + u * self.e1[ti, 2] + v * self.e2[ti, 2]
            np.add.at(nb, pi, 1)
            ordre = np.lexsort((z, pi))
            pi, ti, z = pi[ordre], ti[ordre], z[ordre]
            if len(pi):
                dernier = np.r_[pi[1:] != pi[:-1], True]
                premier = np.r_[True, pi[1:] != pi[:-1]]
                sel = dernier if mode == "max" else premier
                zout[pi[sel]] = z[sel]
                tout[pi[sel]] = ti[sel]
                zmin[pi[premier]] = z[premier]
        return (zout, tout, nb, zmin) if toutes else (zout, tout, nb)


def charger_couche(nom):
    f = CACHE / f"{nom}.npz"
    if not f.exists():
        return None
    d = np.load(f, allow_pickle=False)
    return {k: d[k] for k in d.files}


def assurer_cache(forcer=False):
    """Réextrait les USD (hython) si une source a changé depuis le cache."""
    fm = CACHE / "manifeste_cache.json"
    besoin = forcer or not fm.exists()
    if not besoin:
        man = json.loads(fm.read_text(encoding="utf-8"))
        for nom, m in man["couches"].items():
            if m.get("absente"):
                continue
            src = RACINE / m["source"]
            if not src.exists() or sha256(src) != m["sha256"]:
                besoin = True
                break
    if besoin:
        cmd = [str(HYTHON), str(ICI / "extraire_fabrication.py")] + (["--forcer"] if forcer else [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if r.returncode != 0:
            raise SystemExit("extraction des USD en échec :\n" + r.stdout[-3000:] + r.stderr[-3000:])
    return json.loads(fm.read_text(encoding="utf-8"))


# ============================================================================ rasters (grille du nivellement)
def grille_xy():
    g = X0 + PAS_GRILLE * np.arange(N_GRILLE)
    return g


def raster_polygones(items, fond=-1):
    """items : [(valeur, poly local [[ext, trous]])] dessinés dans l'ordre (un item plus tardif recouvre).
    Grille du nivellement : nœud (i, j) = (X0 + i·pas, Y0 + j·pas), tableau [j, i].
    Rastérisation EXACTE des nœuds par la règle pair-impair (balayage par ligne, demi-ouvert [x_entrée ; x_sortie[),
    trous compris : un nœud n'est attribué que s'il est strictement dans le polygone. Le remplissage PIL précédent
    incluait les bords (aire +1,8 %) et repeignait les trous en « fond » : faux trous de TQ-SOL-009 le long des
    bâtiments (revue conformité du 11/10/2026 : 70 m² signalés, 0,7 m² réels)."""
    im = np.full((N_GRILLE, N_GRILLE), int(fond), np.int32)
    for val, p in items:
        J, Xc = [], []
        for r in p:
            r = np.asarray(r, float)
            if len(r) < 3:
                continue
            a = r
            b = np.roll(r, -1, axis=0)
            for (x0, y0), (x1, y1) in zip(a, b):
                if y0 == y1:
                    continue
                lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
                j0 = int(np.ceil((lo - Y0) / PAS_GRILLE - 1e-9))
                j1 = int(np.ceil((hi - Y0) / PAS_GRILLE - 1e-9))        # exclusif : [lo ; hi[
                j0, j1 = max(j0, 0), min(j1, N_GRILLE)
                if j1 <= j0:
                    continue
                jj = np.arange(j0, j1)
                yy = Y0 + jj * PAS_GRILLE
                J.append(jj)
                Xc.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
        if not J:
            continue
        J = np.concatenate(J)
        Xc = np.concatenate(Xc)
        o = np.lexsort((Xc, J))
        J, Xc = J[o], Xc[o]
        debut = np.r_[True, J[1:] != J[:-1]]
        rang = np.arange(len(J)) - np.maximum.accumulate(np.where(debut, np.arange(len(J)), 0))
        ent = (rang % 2) == 0
        k = np.nonzero(ent)[0]
        k = k[k + 1 < len(J)]
        k = k[J[k + 1] == J[k]]
        i0 = np.ceil((Xc[k] - X0) / PAS_GRILLE - 1e-9).astype(np.int64)
        i1 = np.ceil((Xc[k + 1] - X0) / PAS_GRILLE - 1e-9).astype(np.int64)
        i0, i1 = np.clip(i0, 0, N_GRILLE), np.clip(i1, 0, N_GRILLE)
        for j, a_, b_ in zip(J[k].tolist(), i0.tolist(), i1.tolist()):
            if b_ > a_:
                im[j, a_:b_] = int(val)
    return im


def disque(r_px):
    o = []
    for di in range(-r_px, r_px + 1):
        for dj in range(-r_px, r_px + 1):
            if di * di + dj * dj <= r_px * r_px + 1e-9:
                o.append((di, dj))
    return o


def decaler(m, di, dj, rempl):
    out = np.full_like(m, rempl)
    n0, n1 = m.shape
    a0, b0 = max(0, dj), min(n0, n0 + dj)
    a1, b1 = max(0, di), min(n1, n1 + di)
    out[a0:b0, a1:b1] = m[a0 - dj:b0 - dj, a1 - di:b1 - di]
    return out


def eroder(m, r_px):
    out = m.copy()
    for di, dj in disque(r_px):
        if di or dj:
            out &= decaler(m, di, dj, False)
    return out


def dilater(m, r_px):
    out = m.copy()
    for di, dj in disque(r_px):
        if di or dj:
            out |= decaler(m, di, dj, False)
    return out


def composantes(m):
    """Composantes 8-connexes d'un masque booléen creux : liste de tableaux d'indices (j, i)."""
    jj, ii = np.nonzero(m)
    if not len(jj):
        return []
    Q = np.c_[ii, jj].astype(float)
    lab = grappes(Q, 1.5)
    out = []
    for k in range(lab.max() + 1):
        s = lab == k
        out.append((jj[s], ii[s]))
    out.sort(key=lambda c: (-len(c[0]), int(c[0].min()), int(c[1].min())))
    return out


# ============================================================================ contexte
class Contexte:
    """Toutes les entrées, chargées à la demande et mémorisées."""

    def __init__(self, description=DESCRIPTION / "base", fabrique=FABRIQUE):
        self.dbase = Path(description)
        self.fab = Path(fabrique)
        self._c = {}

    def _m(self, cle, f):
        if cle not in self._c:
            self._c[cle] = f()
        return self._c[cle]

    # ---------------------------------------------------------------- règles et specs
    @property
    def regles(self):
        return self._m("regles", lambda: json.loads((SPECS / "regles_conception.json").read_text(encoding="utf-8")))

    def spec(self, nom):
        return self._m("spec:" + nom, lambda: json.loads((SPECS / f"{nom}.json").read_text(encoding="utf-8")))

    # ---------------------------------------------------------------- description
    def couche(self, nom):
        return self._m("desc:" + nom, lambda: C.lire_geojson(self.dbase / f"{nom}.geojson"))

    @property
    def manifeste(self):
        return self._m("manifeste", lambda: json.loads((self.dbase.parent / "description_scene_v2.json")
                                                        .read_text(encoding="utf-8")))

    @property
    def bordures(self):
        """{id: dict(p=propriétés, P=(N,3) local, s=abscisses, n=normale gauche (côté haut), tg)}"""
        def f():
            out = {}
            for ft in self.couche("bordures"):
                p = ft["properties"]
                P = ligne_local(ft["geometry"], z=True)[0]
                S = C.abscisses(P[:, :2])
                n, tg = normale_gauche(P[:, :2])
                out[p["id"]] = {"p": p, "P": P, "s": S, "n": n, "tg": tg}
            return out
        return self._m("bordures", f)

    @property
    def surfaces(self):
        def f():
            out = {}
            for ft in self.couche("surfaces"):
                p = ft["properties"]
                out[p["id"]] = {"p": p, "poly": poly_local(ft["geometry"])}
            return out
        return self._m("surfaces", f)

    @property
    def ilots(self):
        return self._m("ilots", lambda: {ft["properties"]["id"]: {"p": ft["properties"], "poly": poly_local(ft["geometry"])}
                                         for ft in self.couche("ilots")})

    @property
    def ponctuels(self):
        return self._m("ponctuels", lambda: {ft["properties"]["id"]: {"p": ft["properties"],
                                                                      "poly": poly_local(ft["geometry"])}
                                             for ft in self.couche("ponctuels_sol")})

    @property
    def marquages(self):
        def f():
            out = {}
            for ft in self.couche("marquages"):
                p = ft["properties"]
                g = ft["geometry"]
                e = {"p": p, "type_geom": g["type"] if g else None}
                if g and g["type"] in ("Polygon", "MultiPolygon"):
                    e["poly"] = poly_local(g)
                elif g and g["type"] in ("LineString", "MultiLineString"):
                    e["lignes"] = ligne_local(g)
                out[p["id"]] = e
            return out
        return self._m("marquages", f)

    def fabrique_marquage(self, p):
        return (p.get("fabrication") or {}).get("statut") != "non_fabrique" and not p.get("virtuelle") \
            and p.get("peinte") is not False

    @property
    def niv(self):
        return self._m("niv", lambda: Nivellement(self.dbase))

    @property
    def niv_meta(self):
        return self.niv.meta

    @property
    def mnt(self):
        return self._m("mnt", lambda: C.MNT())

    @property
    def cote_bordures(self):
        """{bordure: {"avant": set(classes), "arriere": set(classes), "surf_avant": [...], ...}} depuis surfaces.bords"""
        def f():
            out = {}
            for sid, s in self.surfaces.items():
                for b in s["p"].get("bords") or []:
                    d = out.setdefault(b["bordure"], {"avant": {}, "arriere": {}})
                    d[b["cote"]][sid] = s["p"]["classe"]
            return out
        return self._m("cote_bordures", f)

    # ---------------------------------------------------------------- réseau OpenDRIVE
    @property
    def reseau(self):
        return self._m("reseau", lambda: X.lire_xodr(X.XODR))

    @property
    def xodr_objets(self):
        return self._m("xodr_objets", lambda: X.objets(self.reseau))

    @property
    def signaux(self):
        def f():
            out = []
            for rid in sorted(self.reseau, key=int):
                r = self.reseau[rid]
                for s in r.xml.iter("signal"):
                    ss, t = float(s.get("s")), float(s.get("t"))
                    x, y, h = X.point_st(r, np.array([ss]), np.array([t]))
                    out.append({"route": rid, "id": s.get("id"), "type": s.get("type"), "nom": s.get("name"),
                                "s": ss, "t": t, "xy": np.array([x[0], y[0]]), "hdg": float(h[0]),
                                "orientation": s.get("orientation"), "zOffset": float(s.get("zOffset", 0))})
            return out
        return self._m("signaux", f)

    @property
    def voies(self):
        """Polygones des voies (lanes_2026.geojson) : liste de dict(route, voie, type, jonction, poly)."""
        def f():
            out = []
            for ft in C.lire_geojson(DONNEES / "opendrive/lanes_2026.geojson"):
                p = ft["properties"]
                if p.get("type") in (None, "reference"):
                    continue
                for pol in poly_local(ft["geometry"]):
                    out.append({"route": str(p.get("route")), "voie": p.get("voie"), "type": p.get("type"),
                                "jonction": bool(p.get("jonction")) or int(p.get("route", 0) or 0) >= 100,
                                "section_s": p.get("section_s"), "poly": pol, "p": p})
            return out
        return self._m("voies", f)

    @property
    def jonction(self):
        return self._m("jonction", lambda: [v["poly"] for v in self.voies if v["jonction"]])

    @property
    def manoeuvres(self):
        return self._m("manoeuvres", lambda: json.loads((DONNEES / "opendrive/manoeuvres_2026.json")
                                                         .read_text(encoding="utf-8")))

    # ---------------------------------------------------------------- objets, levés
    @property
    def mobilier(self):
        return self._m("mobilier", lambda: C.lire_geojson(DONNEES / "objets/mobilier.geojson"))

    @property
    def arbres(self):
        return self._m("arbres", lambda: C.lire_geojson(DONNEES / "objets/arbres.geojson"))

    def gam(self, nom):
        return self._m("gam:" + nom, lambda: C.lire_geojson(SITE / f"etat_2026/{nom}_L93.geojson"))

    @property
    def bordures_hauteurs(self):
        return self._m("bh", lambda: C.lire_geojson(DONNEES / "relief/bordures_hauteurs.geojson"))

    # ---------------------------------------------------------------- fabrication
    @property
    def cache(self):
        return self._m("cache", lambda: assurer_cache())

    def fab_couche(self, nom):
        self.cache
        return self._m("fab:" + nom, lambda: charger_couche(nom))

    def requete(self, nom, cellule=0.5):
        def f():
            c = self.fab_couche(nom)
            return RequeteMaillage(c["T"], cellule) if c is not None else None
        return self._m(f"req:{nom}:{cellule}", f)

    def fab_entites(self, nom):
        """{entité: indices des triangles} d'une couche fabriquée."""
        def f():
            c = self.fab_couche(nom)
            if c is None:
                return {}
            o = np.argsort(c["ent"], kind="stable")
            e = c["ent"][o]
            b = np.searchsorted(e, np.arange(len(c["ents"]) + 1))
            return {str(c["ents"][k]): o[b[k]:b[k + 1]] for k in range(len(c["ents"]))}
        return self._m("fabent:" + nom, f)

    def points(self, famille):
        return self._m("pts:" + famille, lambda: json.loads((self.fab / f"points/{famille}.json")
                                                            .read_text(encoding="utf-8")))

    @property
    def manifeste_fab(self):
        return self._m("manfab", lambda: json.loads((self.fab / "manifest_fabrication_hda.json")
                                                    .read_text(encoding="utf-8")))

    # ---------------------------------------------------------------- rasters de contrôle
    @property
    def raster_surfaces(self):
        """Indice de surface (ordre de self.ids_surfaces) par nœud de la grille de 0,10 m ; −1 hors surfaces."""
        def f():
            ids = sorted(self.surfaces)
            idx = {s: k for k, s in enumerate(ids)}
            items = sorted(((idx[s], self.surfaces[s]["poly"][k]) for s in ids
                            for k in range(len(self.surfaces[s]["poly"]))),
                           key=lambda t: (-aire(t[1][0]), t[0]))
            return ids, raster_polygones(items)
        return self._m("rsurf", f)

    def classe_noeuds(self):
        def f():
            ids, R = self.raster_surfaces
            classes = np.array([self.surfaces[s]["p"]["classe"] for s in ids] + ["hors"])
            return classes[np.where(R >= 0, R, len(ids))]
        return self._m("rclasse", f)

    @property
    def sol_grille(self):
        """Hauteur du sol fabriqué (max, Z haut) aux nœuds de la grille de 0,10 m, nombre de couches touchées et
        z min ; mémorisé dans le cache (clé : sha256 de sol.usdc)."""
        def f():
            h = self.cache["couches"]["sol"]["sha256"]
            fc = CACHE / "sol_grille.npz"
            if fc.exists():
                d = np.load(fc)
                if str(d["sha"]) == h and "mat" in d.files and "nbs" in d.files:
                    self._c["solmat"] = d["mat"]
                    self._c["solnbs"] = d["nbs"]
                    return d["z"], d["nb"], d["zmin"]
            g = grille_xy()
            req = self.requete("sol", 0.5)
            mats = self.fab_couche("sol")["mat"]
            Z = np.full((N_GRILLE, N_GRILLE), np.nan, np.float32)
            NB = np.zeros((N_GRILLE, N_GRILLE), np.int8)
            ZM = np.full((N_GRILLE, N_GRILLE), np.nan, np.float32)
            MAT = np.full((N_GRILLE, N_GRILLE), -1, np.int16)
            # couches STRICTES (TQ-SOL-009, revue conformité du 11/10/2026) : triangles de sol hors BEV qui contiennent
            # le nœud strictement (pas sur une arête partagée) ; > 1 = sol en double couche, même coplanaire
            c_sol = self.fab_couche("sol")
            noms_m = [str(x) for x in c_sol["mats"]]
            hors_bev = c_sol["mat"] != (noms_m.index("bev_podotactile") if "bev_podotactile" in noms_m else -1)
            req_s = RequeteMaillage(c_sol["T"][hors_bev], 0.5)
            NBS = np.zeros((N_GRILLE, N_GRILLE), np.int8)
            for j0 in range(0, N_GRILLE, 200):
                jj = np.arange(j0, min(N_GRILLE, j0 + 200))
                XX, YY = np.meshgrid(g, g[jj])
                z, ti, nb, zm = req.requete(np.c_[XX.ravel(), YY.ravel()], "max", toutes=True)
                Z[jj] = z.reshape(len(jj), N_GRILLE)
                NB[jj] = np.minimum(nb, 100).reshape(len(jj), N_GRILLE)
                ZM[jj] = zm.reshape(len(jj), N_GRILLE)
                MAT[jj] = np.where(ti >= 0, mats[np.maximum(ti, 0)], -1).reshape(len(jj), N_GRILLE)
                _, _, nbs = req_s.requete(np.c_[XX.ravel(), YY.ravel()], "max", eps=-1e-7)
                NBS[jj] = np.minimum(nbs, 100).reshape(len(jj), N_GRILLE)
            np.savez(fc, z=Z, nb=NB, zmin=ZM, mat=MAT, nbs=NBS, sha=np.array(h))
            self._c["solmat"] = MAT
            self._c["solnbs"] = NBS
            return Z, NB, ZM
        return self._m("solgrille", f)

    @property
    def sol_couches_strictes(self):
        """Nombre de triangles de sol (hors BEV) contenant strictement chaque nœud (TQ-SOL-009 : > 1 = double couche)."""
        self.sol_grille
        return self._c["solnbs"]

    @property
    def sol_materiau(self):
        """Nom du matériau du sol fabriqué à chaque nœud ('' hors sol)."""
        def f():
            self.sol_grille
            noms = np.array([str(x) for x in self.fab_couche("sol")["mats"]] + [""])
            M = self._c["solmat"]
            return noms[np.where(M >= 0, M, len(noms) - 1)]
        return self._m("solmatnom", f)
