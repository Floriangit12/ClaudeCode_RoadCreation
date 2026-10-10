"""pj_decals : détails sur le sol fabriqué (rubans vectoriels drapés, instances 3D ; jamais d'image plaquée).

- pontages (regle:pj_decals.pontage, revue réalisme r2) : motif d'entretien sur l'enrobé ancien,
  fissures longitudinales (rive à 0,8-1,0 m de la face, bande de roulement intérieure, joint de voie) et
  transversales tous les 6 à 15 m, tronçons de 1,5-8 m, rubans de 4-8 cm à bavures de raclette, densité
  0,10 m/m² ; joint de reprise neuf 2025 / ancien ponté sur toute sa longueur (3 cm) ;
- touffes d'herbe 3D (regle:pj_decals.touffes) : joints des bordures anciennes (aspect herbe_joints) et
  limites gazon / revêtement dur ;
- dalles podotactiles 3D (regle:pj_decals.bev) : modules entiers de pj_sol.modules_bev, 60 plots en
  calotte (NF P98-351) ;
- zébras provisoires (en attendant pj_marquages, phase 2) : bandes `passage_pieton_bande` du paquet v1
  (donnees/marquages/marquages_2026.geojson) dans l'emprise, recalées en rectangles exacts (axes
  principaux des sommets, largeur ramenée à 0,50 m si elle est entre 0,40 et 0,60), drapées sur le sol
  v2 à +2 mm, maillées tous les 0,25 m ; peinture blanche usée (pj_materiaux.PEINTURES) ;
- graines = hash(bordure | type | joint) ; sorties decals_sol.usda, marquages_pilote.usda.
"""
import json
import math

import numpy as np

import pj_commun as K
import pj_usd as U
from pxr import Sdf

C = K.C
T = Sdf.ValueTypeNames
DENSITE_PONTAGE = 0.10       # m de fissure pontée par m² d'enrobé ancien (revue réalisme r2 : 0,25 = gribouillis)
DZ_PONTAGE = 0.0015
DZ_PEINTURE = 0.002


class Localisateur:
    """Triangle du sol sous des points (grille de 0,5 m) et altitude barycentrique."""

    def __init__(self, P3, T_, classes=None, cellule=0.5):
        self.P3, self.T, self.cl = P3, T_, classes
        self.c = cellule
        A = P3[T_][:, :, :2]
        lo, hi = A.min(axis=1), A.max(axis=1)
        self.o = lo.min(axis=0) - 1.0
        i0 = np.floor((lo - self.o) / cellule).astype(int)
        i1 = np.floor((hi - self.o) / cellule).astype(int)
        self.g = {}
        for t in range(len(T_)):
            for ix in range(i0[t, 0], i1[t, 0] + 1):
                for iy in range(i0[t, 1], i1[t, 1] + 1):
                    self.g.setdefault((ix, iy), []).append(t)

    def trouver(self, Q):
        """(indice de triangle ou −1, z) pour chaque point Q (n, 2)."""
        Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))[:, :2]
        tri = np.full(len(Q), -1)
        z = np.full(len(Q), np.nan)
        cel = np.floor((Q - self.o) / self.c).astype(int)
        for i, q in enumerate(Q):
            cand = self.g.get((int(cel[i, 0]), int(cel[i, 1])))
            if not cand:
                continue
            cand = np.array(cand)
            a, b, c = self.P3[self.T[cand, 0]], self.P3[self.T[cand, 1]], self.P3[self.T[cand, 2]]
            v0, v1, v2 = (b - a)[:, :2], (c - a)[:, :2], q - a[:, :2]
            d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
            d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
            den = d00 * d11 - d01 * d01
            den = np.where(np.abs(den) < 1e-18, 1e-18, den)
            v = (d11 * d20 - d01 * d21) / den
            w = (d00 * d21 - d01 * d20) / den
            u = 1 - v - w
            ok = np.where((u >= -1e-9) & (v >= -1e-9) & (w >= -1e-9))[0]
            if len(ok):
                k = ok[0]
                tri[i] = cand[k]
                z[i] = u[k] * a[k, 2] + v[k] * b[k, 2] + w[k] * c[k, 2]
        return tri, z


def ruban(Q, larg, z, dz):
    """Maillage d'un ruban centré sur la polyligne Q (n, 2), largeur par sommet, z par sommet (2n)."""
    nl = K.normales_gauches(Q)
    g = Q + nl * (larg[:, None] / 2)
    d = Q - nl * (larg[:, None] / 2)
    P = np.empty((2 * len(Q), 3))
    P[0::2, :2], P[1::2, :2] = g, d
    P[0::2, 2] = z + dz
    P[1::2, 2] = z + dz
    faces = []
    for i in range(len(Q) - 1):
        a, b, c, e = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
        faces += [(a, b, c), (a, c, e)]
    return P, faces


def _assembler(morceaux):
    P, F, o = [], [], 0
    for p, f in morceaux:
        P.append(p)
        F += [tuple(i + o for i in t) for t in f]
        o += len(p)
    if not P:
        return None, None
    return np.vstack(P), np.array(F, dtype=np.int64)


class Decals:
    def __init__(self, desc, sol, log=print):
        self.desc, self.sol, self.log = desc, sol, log
        self.loc = Localisateur(sol.P3, sol.T, sol.cl)
        self.comptes = {}

    # ---------------------------------------------------------------- pontages
    def pontages(self):
        """Pontages de fissures sur l'enrobé ancien (regle:pj_decals.pontage, revue réalisme r2 : « vers »
        aléatoires de largeur constante, sans logique de fissuration). Motif d'entretien :
        - fissures longitudinales parallèles aux bordures : rive (bande de roulement extérieure, 0,8-1,0 m
          de la face), bande de roulement intérieure (2,5-2,9 m), joint de voie (3,2-3,5 m) ;
        - fissures transversales tous les 6 à 15 m, de la rive vers l'intérieur (2 à 5 m) ;
        - tronçons de 1,5 à 8 m séparés de 0,5 à 4 m, légère ondulation (±4 cm), uniquement sur l'enrobé
          ancien et à plus de 0,4 m d'une autre bordure ;
        - largeur 4 à 8 cm variable le long du ruban, bavures de raclette (élargissements x 1,4-1,8 sur
          10-25 cm) ; densité visée 0,10 m/m²."""
        sol = self.sol
        P3, T_, cl = sol.P3, sol.T, sol.cl
        anc = np.where(cl == "enrobe_bbsg_ancien")[0]
        morceaux = []
        long_tot = 0.0
        par_type = {}
        if len(anc):
            a, b, c = P3[T_[anc, 0]], P3[T_[anc, 1]], P3[T_[anc, 2]]
            A_tot = float((0.5 * np.abs(np.cross((b - a)[:, :2], (c - a)[:, :2]))).sum())
            cible = DENSITE_PONTAGE * A_tot
            faces = {B.id: B.P for B in self.desc.bordures}

            def loin_des_autres(Q, bid):
                ids = [k for k in sorted(faces) if k != bid]
                FA = np.vstack([faces[k][:-1] for k in ids])
                FB = np.vstack([faces[k][1:] for k in ids])
                d, _, _ = C.distance_segments(Q, FA, FB)
                return d > 0.4

            parts = {"rive": 0.35, "joint_voie": 0.25, "roulement_int": 0.15, "transversale": 0.25}

            def rubans(Q, r, typ):
                """Tronçons sur l'enrobé ancien d'une polyligne candidate, découpés et ajoutés (budget par type)."""
                nonlocal long_tot
                tri, z = self.loc.trouver(Q)
                ok = (tri >= 0) & (np.where(tri >= 0, cl[np.maximum(tri, 0)], "") == "enrobe_bbsg_ancien")
                budget = parts[typ] * cible
                i = 0
                while i < len(Q) and par_type.get(typ, 0.0) < budget:
                    if not ok[i]:
                        i += 1
                        continue
                    j = i
                    while j + 1 < len(Q) and ok[j + 1]:
                        j += 1
                    k = i
                    while k < j and par_type.get(typ, 0.0) < budget:   # tronçons de 1,5-8 m, trous de 0,5-4 m
                        n = int(r.uniform(1.5, 8.0) / 0.05)
                        e = min(j, k + n)
                        if e - k >= 12:
                            q, zz = Q[k:e + 1], z[k:e + 1]
                            t = np.linspace(0, 1, len(q))
                            w = r.uniform(0.04, 0.065) * (1.0 + 0.25 * np.sin(2 * np.pi * (t * r.uniform(1, 4) + r.uniform())))
                            for _ in range(int(r.integers(0, 3))):          # bavures de raclette
                                c0 = r.uniform(0, 1)
                                w *= 1.0 + r.uniform(0.4, 0.8) * np.exp(-0.5 * ((t - c0) * len(q) * 0.05 / r.uniform(0.05, 0.12)) ** 2)
                            w *= np.clip(np.minimum(t, 1 - t) * len(q) * 0.05 / 0.06, 0.45, 1.0)   # bouts effilés
                            morceaux.append(ruban(q, w, zz, DZ_PONTAGE))
                            L_ = 0.05 * (len(q) - 1)
                            long_tot += L_
                            par_type[typ] = par_type.get(typ, 0.0) + L_
                        k = e + int(r.uniform(0.5, 4.0) / 0.05)
                    i = j + 1
            for typ, (o0, o1), proba in (("rive", (0.8, 1.0), 0.8), ("joint_voie", (3.2, 3.5), 0.6),
                                         ("roulement_int", (2.5, 2.9), 0.35)):
                for B in self.desc.bordures:
                    r = K.rng("pontage", typ, B.id)
                    if r.uniform() > proba or B.L < 6.0:
                        continue
                    ss = np.arange(0.0, B.L, 0.05)
                    q, tg = C.point_a(B.P, ss)
                    nl = np.c_[-tg[:, 1], tg[:, 0]]
                    # tracé de fissure : ondulation lente (±4 cm) + marche aléatoire bornée (±6 cm)
                    mar = np.clip(np.cumsum(r.normal(0, 0.004, len(ss))), -0.06, 0.06)
                    off = r.uniform(o0, o1) + 0.04 * np.sin(2 * np.pi * ss / r.uniform(3, 7) + r.uniform(0, 6.3)) + mar
                    Q = q - nl * off[:, None]                          # côté chaussée (droite de la face vue)
                    Q = Q[loin_des_autres(Q, B.id)] if len(Q) else Q
                    if len(Q) > 12:
                        rubans(Q, r, typ)
            for B in self.desc.bordures:                              # transversales
                r = K.rng("pontage", "transversale", B.id)
                s_ = r.uniform(2.0, 8.0)
                while s_ < B.L - 1.0 and par_type.get("transversale", 0.0) < parts["transversale"] * cible:
                    q, tg = C.point_a(B.P, np.array([s_]))
                    nl = np.array([-tg[0, 1], tg[0, 0]])
                    L_ = r.uniform(2.0, 5.0)
                    d_ = np.arange(0.3, 0.3 + L_, 0.05)
                    dev = np.cumsum(r.normal(0, 0.006, len(d_)))
                    Q = q[0] - np.outer(d_, nl) + np.outer(dev, tg[0])
                    rubans(Q, r, "transversale")
                    s_ += r.uniform(6.0, 15.0)
        # joint de reprise neuf / ancien : arêtes du sol entre les deux classes
        jr = self._joint_reprise()
        long_j = 0.0
        for Q in jr:
            tri, z = self.loc.trouver(Q)
            ok = tri >= 0
            if ok.sum() < 2:
                continue
            Q, z = Q[ok], z[ok]
            morceaux.append(ruban(Q, np.full(len(Q), 0.03), z, DZ_PONTAGE + 0.0003))
            long_j += float(np.sum(np.hypot(*np.diff(Q, axis=0).T)))
        self.comptes["pontages"] = {"regle": "regle:pj_decals.pontage", "longueur_fissures_m": round(long_tot, 1),
                                    "par_type_m": {k: round(v, 1) for k, v in sorted(par_type.items())},
                                    "densite_m_par_m2": DENSITE_PONTAGE, "joint_reprise_neuf_ancien_m": round(long_j, 1),
                                    "rubans": len(morceaux)}
        return _assembler(morceaux)

    def _joint_reprise(self):
        """Polylignes des arêtes du sol séparant enrobé neuf 2025 et enrobé ancien (densifiées à 0,1 m)."""
        T_, cl, P3 = self.sol.T, self.sol.cl, self.sol.P3
        aretes = {}
        for t, tri in enumerate(T_):
            for i in range(3):
                a, b = int(tri[i]), int(tri[(i + 1) % 3])
                aretes.setdefault((min(a, b), max(a, b)), []).append(cl[t])
        bord = [e for e, cs in aretes.items() if len(cs) == 2 and set(cs) == {"enrobe_bbsg_neuf_2025", "enrobe_bbsg_ancien"}]
        vois = {}
        for a, b in bord:
            vois.setdefault(a, []).append(b)
            vois.setdefault(b, []).append(a)
        vu, out = set(), []
        for depart in sorted(v for v in vois if len(vois[v]) != 2) + sorted(vois):
            for nxt in sorted(vois[depart]):
                e = (min(depart, nxt), max(depart, nxt))
                if e in vu:
                    continue
                ch = [depart, nxt]
                vu.add(e)
                while len(vois[ch[-1]]) == 2:
                    s = [x for x in vois[ch[-1]] if (min(x, ch[-1]), max(x, ch[-1])) not in vu]
                    if not s:
                        break
                    vu.add((min(s[0], ch[-1]), max(s[0], ch[-1])))
                    ch.append(s[0])
                Q = P3[ch, :2]
                out.append(np.vstack([Q[0]] + [np.linspace(p, q, max(2, int(math.ceil(np.hypot(*(q - p)) / 0.1)) + 1))[1:]
                                               for p, q in zip(Q[:-1], Q[1:])]))
        return out

    # ---------------------------------------------------------------- zébras
    def zebras(self):
        R = self.desc.zone
        f = K.PAQUET_V1 / "donnees/marquages/marquages_2026.geojson"
        d = K.lire_json(f)
        morceaux, ids = [], []
        for feat in sorted(d["features"], key=lambda x: x["properties"]["id"]):
            p = feat["properties"]
            if p.get("type") != "passage_pieton_bande" or feat["geometry"]["type"] != "Polygon":
                continue
            r = K.repere(np.asarray(feat["geometry"]["coordinates"][0], dtype=np.float64)[:, :2], "local")
            if not ((r[:, 0] > R[0]).all() and (r[:, 0] < R[2]).all() and (r[:, 1] > R[1]).all() and (r[:, 1] < R[3]).all()):
                continue
            c = r.mean(axis=0)
            w, V = np.linalg.eigh(np.cov((r - c).T))
            ax = V[:, np.argmax(w)]
            ay = np.array([-ax[1], ax[0]])
            x, y = (r - c) @ ax, (r - c) @ ay
            L, l = float(x.max() - x.min()), float(y.max() - y.min())
            if 0.40 <= l <= 0.60:
                l = 0.50
            if L < 0.5:
                continue
            c = c + ax * 0.5 * (x.max() + x.min()) + ay * 0.5 * (y.max() + y.min())
            nx, ny = max(2, int(math.ceil(L / 0.25)) + 1), 3
            gx, gy = np.meshgrid(np.linspace(-L / 2, L / 2, nx), np.linspace(-l / 2, l / 2, ny), indexing="ij")
            Q = c + gx.reshape(-1, 1) * ax + gy.reshape(-1, 1) * ay
            tri, z = self.loc.trouver(Q)
            if (tri < 0).any():
                continue
            Pm = np.c_[Q, z + DZ_PEINTURE]
            faces = []
            for i in range(nx - 1):
                for j in range(ny - 1):
                    a, b, cc, e = i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1
                    faces += [(a, b, cc), (a, cc, e)]
            morceaux.append((Pm, faces))
            ids.append(p["id"])
        self.comptes["zebras"] = {"source": K.rel(f), "regle": "regle:pj_decals.zebra_provisoire (phase 2 : pj_marquages)",
                                  "bandes": len(ids), "ids_v1": ids}
        return _assembler(morceaux)

    # ---------------------------------------------------------------- touffes d'herbe
    def touffes(self, elements=(), joints=()):
        """Touffes d'herbe 3D (regle:pj_decals.touffes, revue réalisme r2) :
        - dans les joints des bordures dont l'aspect décrit `herbe_joints` > 0 : une touffe de 2 à 4 cm au
          pied de la face vue (fil d'eau) pour une part herbe_joints des joints, et derrière (tête) pour
          la moitié de cette part ;
        - le long des limites gazon / revêtement dur : une touffe de 4 à 8 cm tous les 6 cm environ,
          débordant de 0 à 4 cm sur le revêtement (le gazon ne s'arrête pas net à la limite).
        Renvoie {position, lacet, hauteur, variante, couleur}."""
        sol = self.sol
        pos, lac, ht, var, coul = [], [], [], [], []
        par_id = {B.id: B for B in self.desc.bordures}
        for j in sorted(joints, key=lambda x: x["id"]):
            B = par_id[j["bordure"]]
            herbe = float((B.p.get("aspect") or {}).get("herbe_joints", 0.0))
            if herbe <= 0:
                continue
            r = K.rng(j["id"], "touffe")
            q, tg = B.point(j["s"])
            nl = np.array([-tg[0, 1], tg[0, 0]])
            zfe = float(B.z_fe(j["s"]))
            b = self.sol.bandes[B.id]
            tete = float(b.interp(b.ztop, j["s"]))
            base = float(b.interp(b.base, j["s"]))
            for u, z, proba in ((-0.012, zfe - 0.002, herbe), (base + 0.012, tete - 0.006, 0.5 * herbe)):
                if r.uniform() >= proba:
                    continue
                for _ in range(int(r.integers(1, 3))):
                    pos.append([*(q[0] + nl * (u + r.uniform(-0.006, 0.006)) + tg[0] * r.uniform(-0.01, 0.01)), z])
                    lac.append(r.uniform(-180, 180))
                    ht.append(r.uniform(0.02, 0.04))
                    var.append(int(r.integers(0, 4)))
                    coul.append(r.uniform(0.8, 1.2) * np.array([1.0, r.uniform(0.9, 1.1), r.uniform(0.8, 1.0)]))
        n_joints = len(pos)
        # limites gazon / dur (arêtes du sol fabriqué)
        herbes = {"gazon_tondu", "herbe_haute", "gazon_sec", "noue_plantee"}
        durs = {"enrobe_trottoir", "enrobe_piste_cyclable", "enrobe_bbsg_ancien", "enrobe_bbsg_neuf_2025", "beton_balaye",
                "paves_beton", "dalles_beton", "stabilise_beige", "bev_podotactile"}
        T_, cl, P3 = sol.T, sol.cl, sol.P3
        aretes = {}
        for t, tri in enumerate(T_):
            for i in range(3):
                a, b2 = int(tri[i]), int(tri[(i + 1) % 3])
                aretes.setdefault((min(a, b2), max(a, b2)), []).append(t)
        G = P3[T_].mean(axis=1)
        r = K.rng("touffes", "limites_gazon")
        for (a, b2), ts in sorted(aretes.items()):
            if len(ts) != 2:
                continue
            c0, c1 = cl[ts[0]], cl[ts[1]]
            if c0 in herbes and c1 in durs:
                tg_, td = ts[0], ts[1]
            elif c1 in herbes and c0 in durs:
                tg_, td = ts[1], ts[0]
            else:
                continue
            A, Bq = P3[a], P3[b2]
            L = float(np.hypot(*(Bq[:2] - A[:2])))
            if L < 1e-3:
                continue
            e = (Bq[:2] - A[:2]) / L
            nrm = np.array([-e[1], e[0]])
            if (G[td, :2] - A[:2]) @ nrm < 0:
                nrm = -nrm                                   # vers le revêtement dur
            for _ in range(int(r.poisson(L / 0.06))):
                t = r.uniform()
                xy = A[:2] + (Bq[:2] - A[:2]) * t + nrm * r.uniform(-0.02, 0.04)
                pos.append([*xy, A[2] + (Bq[2] - A[2]) * t])
                lac.append(r.uniform(-180, 180))
                ht.append(r.uniform(0.04, 0.08))
                var.append(int(r.integers(0, 4)))
                coul.append(r.uniform(0.75, 1.15) * np.array([1.0, r.uniform(0.85, 1.05), r.uniform(0.7, 1.0)]))
        if pos:
            P = np.array(pos)
            tri, z = self.loc.trouver(P[:, :2])
            dedans = tri >= 0                                # z sur le maillage (bord de bordure : z du fil d'eau)
            P[n_joints:, 2] = np.where(dedans[n_joints:], z[n_joints:], P[n_joints:, 2])
            pos = P
        self.comptes["touffes"] = {"regle": "regle:pj_decals.touffes", "joints": n_joints,
                                   "limites_gazon": len(pos) - n_joints}
        return {"p": np.asarray(pos, dtype=np.float64).reshape(-1, 3), "lacet": np.array(lac), "h": np.array(ht),
                "var": np.array(var, dtype=int), "couleur": np.asarray(coul, dtype=np.float64).reshape(-1, 3)}

    # ---------------------------------------------------------------- dalles BEV
    def dalles_bev(self):
        """Dalles podotactiles 3D (regle:pj_decals.bev, revue réalisme r2 : plots en texture plate) : un
        prototype de dalle chanfreinée à 60 plots (calotte Ø 25 mm, 5 mm, quinconce au pas de 50 mm, NF P98-351)
        par module posé (pj_sol.modules_bev, joints de 3 mm) ; dessus à 0,8 mm au-dessus du sol (le sol, sous
        les dalles, n'apparaît que dans les joints, en mortier sombre) ; chaque dalle épouse le plan du sol à ses
        4 coins (rampes, chartières)."""
        sol = self.sol
        pos, rpy, ids = [], [], []
        for pc, mods in sol.modules_bev():
            for m in mods:
                coins = m["centre"] + (m["coins"] - m["centre"]) * ((m["demi"] - 0.0015) / m["demi"])
                tri, z = self.loc.trouver(np.vstack([m["centre"][None], coins]))
                if (tri < 0).any():
                    continue
                z = z + 0.0008                                 # dessus à +0,8 mm du sol (pas de z-fighting)
                t, nl = m["tangente"], np.array([-m["tangente"][1], m["tangente"][0]])
                X = coins - m["centre"]
                A = np.c_[X @ t, X @ nl, np.ones(4)]
                gx, gy, z0 = np.linalg.lstsq(A, z[1:], rcond=None)[0]
                # sol non plan sous la dalle (rampe, chartière) : dalle relevée du plus grand résidu sur une grille
                # de 5 x 5 points (jamais enterrée)
                g5 = np.linspace(-1.0, 1.0, 5) * (m["demi"] - 0.002)
                Gx, Gy = np.meshgrid(g5, g5)
                Gq = m["centre"] + np.outer(Gx.ravel(), t) + np.outer(Gy.ravel(), nl)
                tg5, zg5 = self.loc.trouver(Gq)
                okg = tg5 >= 0
                plan = gx * Gx.ravel() + gy * Gy.ravel() + z0
                if okg.any():
                    z0 += max(float((zg5[okg] + 0.0008 - plan[okg]).max()), 0.0)
                yaw = math.degrees(math.atan2(t[1], t[0]))
                rpy.append([math.degrees(math.atan(gy)), -math.degrees(math.atan(gx)), yaw])
                pos.append([*m["centre"], z0 - 0.012])
                ids.append(m["id"])
        self.comptes["bev_dalles"] = {"regle": "regle:pj_decals.bev", "dalles": len(pos), "plots_par_dalle": 60,
                                      "modules_par_bev": {pc["id"]: len(mods) for pc, mods in sol.modules_bev()}}
        return {"p": np.asarray(pos, dtype=np.float64).reshape(-1, 3), "rpy": np.asarray(rpy).reshape(-1, 3), "ids": ids}

    # ---------------------------------------------------------------- sorties
    def ecrire(self, chemin_decals, chemin_marquages, elements=(), joints=()):
        for chemin, (P, F), mat, doc, nom in (
                (chemin_decals, self.pontages(), "bitume_pontage",
                 "Pontages de fissures et joint de reprise neuf / ancien (pj_decals.py) : rubans drapés à +1,5 mm ; "
                 "touffes d'herbe 3D (joints de bordures anciennes, limites gazon / dur) ; dalles podotactiles 3D.",
                 "pontages"),
                (chemin_marquages, self.zebras(), "peinture_blanche",
                 "Zébras provisoires de la zone pilote (pj_decals.py) : bandes du paquet v1 recalées en rectangles, "
                 "drapées sur le sol v2 à +2 mm ; remplacés par pj_marquages en phase 2.", "zebras")):
            st = U.scene(doc, data={"version": K.VERSION, "description": self.desc.hash})
            U.xform(st, "/World/PJ_Decals")
            if P is not None:
                Nz = np.tile([0.0, 0.0, 1.0], (len(P), 1))
                m = U.maillage(st, f"/World/PJ_Decals/{nom}", P, np.full(len(F), 3), F.ravel(), normales=Nz,
                               st1=P[:, :2], st1_interp="vertex", materiau_id=mat)
                m.GetPrim().CreateAttribute("unrealMaterial", T.String).Set(f"/Game/PJ/Materials/MI_{mat}.MI_{mat}")
                U.lier_chemin(m.GetPrim(), f"/World/Looks_v2/{mat}")
            if nom == "pontages":
                self._ecrire_touffes(st, self.touffes(elements, joints))
                self._ecrire_dalles(st, self.dalles_bev())
            U.enregistrer(st, chemin)
        return self.comptes

    def _ecrire_touffes(self, st, tf):
        if len(tf["p"]) == 0:
            return
        path = "/World/PJ_Decals/touffes_herbe"
        protos = [(f"touffe_v{k}", None, None) for k in range(4)]
        q = np.array([K.quat_de_matrice(K.rotation_rpy([0.0, 0.0, float(a)])) for a in tf["lacet"]])
        pi = U.instancer(st, path, protos, tf["var"], tf["p"], q, echelles=np.repeat(tf["h"][:, None], 3, axis=1),
                         primvars={"couleur": (U.vt(tf["couleur"], T.Color3fArray), T.Color3fArray)})
        for k in range(4):
            P, F = prototype_touffe(k)
            m = U.maillage(st, f"{path}/Prototypes/touffe_v{k}/maillage", P, np.full(len(F), 3), F.ravel(),
                           double_face=True, materiau_id="herbe_touffe")
            m.GetPrim().CreateAttribute("unrealMaterial", T.String).Set("/Game/PJ/Materials/MI_herbe_touffe.MI_herbe_touffe")
        U.lier_chemin(pi.GetPrim(), "/World/Looks_v2/herbe_touffe")

    def _ecrire_dalles(self, st, dl):
        if len(dl["p"]) == 0:
            return
        path = "/World/PJ_Decals/bev_dalles"
        q = np.array([K.quat_de_matrice(K.rotation_rpy(list(map(float, a)))) for a in dl["rpy"]])
        pi = U.instancer(st, path, [("dalle_bev_40", None, None)], np.zeros(len(dl["p"]), dtype=int), dl["p"], q)
        P, counts, idx, st1 = prototype_dalle_bev()
        m = U.maillage(st, f"{path}/Prototypes/dalle_bev_40/maillage", P, counts, idx, st1=st1, materiau_id="bev_podotactile")
        m.GetPrim().CreateAttribute("unrealMaterial", T.String).Set("/Game/PJ/Materials/MI_bev_podotactile.MI_bev_podotactile")
        U.lier_chemin(pi.GetPrim(), "/World/Looks_v2/bev_podotactile")


def prototype_touffe(k):
    """Touffe d'herbe k (hauteur unitaire) : 8 à 14 brins triangulaires (base 3 % de la hauteur), inclinés
    de 0 à 35°, pieds sur un disque de rayon 0,25."""
    r = K.rng("touffe", k)
    n = int(r.integers(8, 15))
    P, F = [], []
    for i in range(n):
        a = r.uniform(0, 2 * math.pi)
        c = r.uniform(0, 0.25) * np.array([math.cos(a), math.sin(a)])
        inc = math.radians(r.uniform(0, 35))
        d = np.array([math.cos(a), math.sin(a)]) * math.sin(inc)
        h = r.uniform(0.6, 1.0)
        w = np.array([-math.sin(a), math.cos(a)]) * 0.015 * r.uniform(0.7, 1.3)
        o = len(P)
        P += [[*(c - w), 0.0], [*(c + w), 0.0], [*(c + d * h), math.cos(inc) * h]]
        F.append((o, o + 1, o + 2))
    return np.array(P), np.array(F)


def prototype_dalle_bev(L=0.397, e=0.012, ch=0.002, rplot=0.0125, hplot=0.005, pas=0.05):
    """Dalle podotactile (repère : centre du dessus en (0, 0, e), dessous en z = 0) : pavé chanfreiné de
    L x L x e et 60 plots en calotte (rayon de base 12,5 mm, 5 mm de haut) en quinconce au pas de 50 mm."""
    P, counts, idx = [], [], []

    def face(pts):
        o = len(P)
        P.extend(pts)
        counts.append(len(pts))
        idx.extend(range(o, o + len(pts)))
    h = L / 2
    hi = h - ch
    top = [[-hi, -hi, e], [hi, -hi, e], [hi, hi, e], [-hi, hi, e]]
    face(top)
    bas = [[-h, -h, 0.0], [h, -h, 0.0], [h, h, 0.0], [-h, h, 0.0]]
    mid = [[-h, -h, e - ch], [h, -h, e - ch], [h, h, e - ch], [-h, h, e - ch]]
    for i in range(4):
        j = (i + 1) % 4
        face([bas[i], bas[j], mid[j], mid[i]])
        face([mid[i], mid[j], top[j], top[i]])
    face([bas[3], bas[2], bas[1], bas[0]])
    seg, an = 12, 3
    for iy, y in enumerate(np.arange(-0.175, 0.176, pas)):
        xs = np.arange(-0.175, 0.176, pas) if iy % 2 == 0 else np.arange(-0.15, 0.151, pas)
        for x in xs:
            prev = None
            for k in range(1, an + 1):
                t = k / an
                rr = rplot * math.sqrt(max(1 - t * t, 0.0)) if k < an else 0.0
                zz = e + hplot * t
                ring = [[x + rplot * math.cos(2 * math.pi * m / seg), y + rplot * math.sin(2 * math.pi * m / seg), e]
                        for m in range(seg)] if prev is None else prev
                if k < an:
                    nxt = [[x + rr * math.cos(2 * math.pi * m / seg), y + rr * math.sin(2 * math.pi * m / seg), zz] for m in range(seg)]
                    for m in range(seg):
                        face([ring[m], ring[(m + 1) % seg], nxt[(m + 1) % seg], nxt[m]])
                    prev = nxt
                else:
                    for m in range(seg):
                        face([ring[m], ring[(m + 1) % seg], [x, y, zz]])
    P = np.array(P)
    st1 = P[np.array(idx)][:, :2] + 0.5
    return P, np.array(counts), np.array(idx), st1


