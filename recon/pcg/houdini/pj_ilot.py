"""pj_ilot : remplissages d'îlots (le maillage est fabriqué par pj_sol, côté haut de la ceinture,
dessus de bordure − retrait + bombement, 3-5 cm sous la tête locale) et éclats 3D qui leur donnent leur relief :
- copeaux de BRF (15-60 mm, plats et allongés ; 5 % de copeaux longs et fins de 80-120 mm) et pierres
  concassées 10/20 (anguleuses : enveloppe de 9-12 points tirés dans une boîte), prototypes procéduraux
  (Houdini Shrinkwrap), normales à facettes, UV boîte en mètres ; origine au centre de la boîte ;
- couverture dense (regle:pj_ilot.couverture) : BRF 1 800 /m² (2 500 sur 0,25 m de bord), concassé
  3 000 /m² (4 200 à moins de 1,2 m de la ceinture), massifs de BRF hors îlots 1 500 /m² ; chaque éclat
  dépasse de 40 à 70 % de sa hauteur (calculée sur le prototype tourné) ; copeaux inclinés (σ 20°, 15 %
  dressés à 50-70°) ;
  couleurs du BRF (revue réalisme r2) : bois frais roux (albédo 0,26-0,40, 48 %), écorce brun sombre
  (0,045-0,085, 40 %), grisé chaud (0,18-0,28, 12 %) ; concassé (îlots du Vercors, Panoramax 2025-01-12
  a1ff r01_c00) : gris foncé 0,14-0,21 (55 %), gris 0,22-0,30 (32 %), clair 0,32-0,40 (13 %), légèrement chaud ;
- éclats épars hors remplissage : débordement sur la chaussée devant la ceinture (remplissage.
  debordement, altitude sur le maillage fabriqué) et quelques éclats sur la tête des éléments posés ;
- semis déterministe (graine = hash(îlot)) ;
- sorties : ilots.usda (éclats épars), ilots_couverture.usdc (couverture dense, binaire), points/
  ilots_epars.json (éclats épars seulement, pj_points/0.1 ; la couverture dense est reproduite côté UE
  par PG_Ilots depuis zones/ilots.json), zones/ilots.json (polygones, densités).
"""
import math

import hou
import numpy as np

import pj_commun as K
import pj_usd as U
from pxr import Sdf, UsdGeom, Vt

C = K.C
T = Sdf.ValueTypeNames
CAT = hou.sopNodeTypeCategory()
N_VARIANTES = 12
N_LONGS = 4                # copeaux longs et fins (variantes 12-15 du BRF)

# éclats par matériau de remplissage : prototype, taille (m, grande dimension), densités (/m²), bord
# (revue réalisme r2 : BRF trop gris, trop clair, trop à plat ; gravier des îlots du Vercors en galets
# roulés clairs au lieu d'un concassé sombre et anguleux : granulométrie décrite 10/20, teinte gris foncé)
ECLATS = {
    "brf_bois_concasse": {"famille": "copeau_brf", "materiau": "eclat_brf", "source": "brf_bois_gris",
                          "taille": (0.015, 0.060), "forme": (1.0, 1.0, 1.0), "bord_m": 0.25,
                          "densite_bord": 2500.0, "densite_int": 1800.0, "emergence": (0.4, 0.7),
                          "inclinaison_deg": 40.0, "part_dresses": 0.15, "dresses_deg": (50.0, 70.0),
                          "part_longs": 0.05, "taille_longs": (0.08, 0.12),
                          "debord_par_m2": 6.0, "tete_par_m": 0.8},
    "gravier_concasse_6_10": {"famille": "gravier_6_10", "materiau": "eclat_gravier", "source": "gravier_concasse_6_10",
                              "taille": (0.012, 0.026), "forme": (1.0, 0.8, 0.6), "bord_m": 1.2,
                              "densite_bord": 4200.0, "densite_int": 3000.0, "emergence": (0.4, 0.7),
                              "inclinaison_deg": 180.0, "debord_par_m2": 30.0, "tete_par_m": 0.0},
}
DENSITE_MASSIF = 1500.0    # copeaux /m² sur les massifs de BRF hors îlots
# couleurs du BRF (albédo linéaire visé, gain RVB) et parts : bois frais roux, écorce brun sombre, grisé chaud
BRF_COULEURS = [("frais", 0.48, (0.26, 0.40), (1.0, 0.80, 0.58)),
                ("ecorce", 0.40, (0.045, 0.085), (1.0, 0.70, 0.50)),
                ("grise", 0.12, (0.18, 0.28), (1.0, 0.88, 0.74))]
# couleurs du concassé (albédo linéaire visé) et parts : gris foncé majoritaire, quelques pierres claires
GRAVIER_COULEURS = [(0.55, (0.14, 0.21)), (0.32, (0.22, 0.30)), (0.13, (0.32, 0.40))]
GRAVIER_GAIN = (1.0, 0.98, 0.93)


def n_variantes(famille):
    return N_VARIANTES + (N_LONGS if famille.startswith("copeau") else 0)


def prototype_eclat(famille, k):
    """Éclat k, taille unitaire (1 = grande dimension), origine au centre de la boîte englobante :
    enveloppe convexe (Shrinkwrap) d'un nuage de points ; copeau : boîte aplatie et allongée, tordue
    (variantes ≥ 12 : copeau long et fin, largeur / longueur 0,1) ; concassé : 9 à 12 points tirés dans
    une boîte (facettes et arêtes vives, pas d'ellipsoïde arrondi)."""
    r = K.rng(famille, k)
    if famille.startswith("copeau"):
        n = 22
        L = 1.0
        if k >= N_VARIANTES:
            W, Tz = r.uniform(0.08, 0.12), r.uniform(0.05, 0.09)
        else:
            W, Tz = r.uniform(0.25, 0.55), r.uniform(0.15, 0.30)
        p = np.c_[r.uniform(-L / 2, L / 2, n), r.uniform(-W / 2, W / 2, n) * (1 - 0.6 * np.abs(np.linspace(-1, 1, n))),
                  r.uniform(0, Tz, n)]
        p[:, 1] += 0.15 * W * np.sin(p[:, 0] * r.uniform(2, 6))          # copeau tordu
    else:
        n = int(r.integers(9, 13))
        ax = np.array([1.0, r.uniform(0.55, 0.9), r.uniform(0.4, 0.75)]) / 2
        p = r.uniform(-1.0, 1.0, (n, 3)) * ax
        p[:2] = [[-ax[0], 0.0, 0.0], [ax[0], r.uniform(-0.3, 0.3) * ax[1], 0.0]]    # grande dimension assurée
    g = hou.Geometry()
    g.createPoints([hou.Vector3(*map(float, q)) for q in p])
    out = hou.Geometry()
    v = CAT.nodeVerb("shrinkwrap::2.0")
    v.execute(out, [g])
    out2 = hou.Geometry()
    v = CAT.nodeVerb("normal")
    v.setParms({"type": 1, "cuspangle": 20.0})
    v.execute(out2, [out])
    import pj_bordure_prototypes as BP
    P, counts, idx, N = BP.depuis_hou(out2)
    P -= 0.5 * (P.min(axis=0) + P.max(axis=0))
    P /= max(float(np.ptp(P, axis=0).max()), 1e-6)
    st1 = BP.uv_boite(P, counts, idx)
    return P, counts, idx, N, st1


def _rotations(roulis, tangage, lacet):
    """Matrices (n, 3, 3) R = Rz(y)·Ry(p)·Rx(r) (convention de K.rotation_rpy), degrés."""
    r, p, y = np.radians(roulis), np.radians(tangage), np.radians(lacet)
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    R = np.empty((len(r), 3, 3))
    R[:, 0, 0] = cy * cp
    R[:, 0, 1] = cy * sp * sr - sy * cr
    R[:, 0, 2] = cy * sp * cr + sy * sr
    R[:, 1, 0] = sy * cp
    R[:, 1, 1] = sy * sp * sr + cy * cr
    R[:, 1, 2] = sy * sp * cr - cy * sr
    R[:, 2, 0] = -sp
    R[:, 2, 1] = cp * sr
    R[:, 2, 2] = cp * cr
    return R


def _quats(R):
    """Quaternions (w, x, y, z) de matrices (n, 3, 3) (branche trace > 0 ou axe dominant)."""
    out = np.empty((len(R), 4))
    for k in range(len(R)):
        out[k] = K.quat_de_matrice(R[k])
    return out


class Semis:
    def __init__(self, desc, specs, sol, log=print, elements=()):
        self.desc, self.specs, self.sol, self.log = desc, specs, sol, log
        self.points = []
        self.couverture = []                     # (materiau, dict de tableaux)
        self.sommets_protos = {}
        import pj_decals as DC
        self.loc = getattr(sol, "_loc", None) or DC.Localisateur(sol.P3, sol.T)
        sol._loc = self.loc
        self.cases = {}                          # bordure -> [(s0, s1)] des éléments posés
        for e in elements:
            self.cases.setdefault(e["bordure"], []).append((e["s0"], e["s1"]))

    def _distance_bord(self, il, Q):
        """Distance au bord du remplissage (arête arrière de la ceinture)."""
        din = np.full(len(Q), np.inf)
        for bid in il["p"].get("ceinture", []):
            b = self.sol.bandes.get(bid)
            if b is None:
                continue
            s, dl, d, ex = b.projeter(Q)
            ub = b.interp(b.ub, s)
            din = np.minimum(din, np.where(ex < 0.3, np.maximum(dl - ub, 0.0), np.inf))
        return np.where(np.isfinite(din), din, 1.0)

    def _sommets(self, cfg):
        """Sommets des variantes (mises à la forme) : pour la hauteur de chaque éclat tourné."""
        fam = cfg["famille"]
        if fam not in self.sommets_protos:
            self.sommets_protos[fam] = [prototype_eclat(fam, k)[0] * np.array(cfg["forme"]) for k in range(n_variantes(fam))]
        return self.sommets_protos[fam]

    def _tirage(self, cfg, Q, zs, r):
        """Tailles, variantes, rotations, positions (émergence 40-70 %), couleurs d'un lot d'éclats posés
        sur la surface z = zs aux points Q."""
        n = len(Q)
        t0, t1 = cfg["taille"]
        taille = np.exp(r.uniform(math.log(t0), math.log(t1), n))
        var = r.integers(0, N_VARIANTES, n)
        if cfg.get("part_longs"):                     # copeaux longs et fins
            lg = r.uniform(size=n) < cfg["part_longs"]
            var[lg] = r.integers(N_VARIANTES, N_VARIANTES + N_LONGS, int(lg.sum()))
            taille[lg] = r.uniform(*cfg["taille_longs"], int(lg.sum()))
        lacet = r.uniform(-180, 180, n)
        inc = cfg["inclinaison_deg"]
        if inc >= 180:
            roulis, tangage = r.uniform(-180, 180, n), r.uniform(-90, 90, n)
        else:
            roulis, tangage = r.normal(0, inc / 2, n), r.normal(0, inc / 2, n)
            if cfg.get("part_dresses"):               # copeaux dressés : interstices sombres (photo 2)
                dr = r.uniform(size=n) < cfg["part_dresses"]
                a, b = cfg["dresses_deg"]
                roulis[dr] = r.uniform(a, b, int(dr.sum())) * np.where(r.uniform(size=int(dr.sum())) < 0.5, -1, 1)
        R = _rotations(roulis, tangage, lacet)
        zmin, zmax = np.zeros(n), np.zeros(n)
        V = self._sommets(cfg)
        for k in range(len(V)):
            m = var == k
            if m.any():
                Z = R[m, 2, :] @ V[k].T
                zmin[m], zmax[m] = Z.min(axis=1) * taille[m], Z.max(axis=1) * taille[m]
        e = r.uniform(*cfg["emergence"], n)
        zc = zs + e * (zmax - zmin) - zmax              # le haut dépasse de e x la hauteur
        teinte = r.uniform(0.85, 1.12, n)
        if cfg["famille"].startswith("copeau"):
            moy = np.array((self.specs.materiau(cfg["source"]).get("texture_mesuree") or {})
                           .get("albedo_moyen_lineaire") or [0.26, 0.235, 0.205])
            u = r.uniform(size=n)
            coul = np.empty((n, 3))
            acc = 0.0
            for _, part, (a0, a1), rgb in BRF_COULEURS:
                m = (u >= acc) & (u < acc + part)
                acc += part
                coul[m] = r.uniform(a0, a1, (int(m.sum()), 1)) * np.array(rgb) / moy
            m = u >= acc
            coul[m] = 1.0
        else:                                         # concassé : albédo visé par pierre, gris foncé majoritaire
            moy = float(np.mean((self.specs.materiau(cfg["source"]).get("texture_mesuree") or {})
                                .get("albedo_moyen_lineaire") or [0.33, 0.33, 0.32]))
            u = r.uniform(size=n)
            a = np.empty(n)
            acc = 0.0
            for part, (a0, a1) in GRAVIER_COULEURS:
                m = (u >= acc) & (u < acc + part)
                acc += part
                a[m] = r.uniform(a0, a1, int(m.sum()))
            a[u >= acc] = 0.13
            coul = (a / moy)[:, None] * np.array(GRAVIER_GAIN) * (1.0 + r.uniform(-0.03, 0.03, (n, 3)))
        return {"p": np.c_[Q[:, :2], zc], "R": R, "rpy": np.c_[roulis, tangage, lacet], "taille": taille,
                "var": var, "teinte": teinte, "couleur": coul}

    def semer(self):
        sol = self.sol
        P3, Tt = sol.P3, sol.T
        for il in self.desc.ilots:
            rem = il["p"]["remplissage"]
            cfg = ECLATS.get(rem["materiau_id"])
            if cfg is None:
                continue
            r = K.rng(il["id"], "semis")
            sel = np.where(sol.ilot_tri == il["id"])[0]
            if len(sel) == 0:
                continue
            tri = Tt[sel]
            a, b, c = P3[tri[:, 0]], P3[tri[:, 1]], P3[tri[:, 2]]
            aire = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
            G = (a + b + c) / 3
            dbord = self._distance_bord(il, G[:, :2])
            dens = np.where(dbord < cfg["bord_m"], cfg["densite_bord"], cfg["densite_int"])
            nb = r.poisson(aire * dens)
            k = np.repeat(np.arange(len(sel)), nb)
            u, v = r.uniform(size=len(k)), r.uniform(size=len(k))
            f = u + v > 1
            u[f], v[f] = 1 - u[f], 1 - v[f]
            Q = a[k] + (b[k] - a[k]) * u[:, None] + (c[k] - a[k]) * v[:, None]
            lot = self._tirage(cfg, Q, Q[:, 2], r)
            lot["ilot"] = il["id"]
            self.couverture.append((cfg["materiau"], cfg["famille"], lot))
            # débordement sur la chaussée devant la ceinture, éclats sur la tête de bordure
            deb = rem.get("debordement") or {}
            larg = float(deb.get("largeur_m", 0.2))
            for bid in il["p"].get("ceinture", []):
                bd = sol.bandes.get(bid)
                if bd is None:
                    continue
                # seulement le long de l'îlot : abscisses où le côté haut (0,3 m derrière) est dans l'îlot
                sg = np.arange(0.0, bd.B.L, 0.25)
                pg, tg = C.point_a(bd.B.P, sg)
                q = pg + np.c_[-tg[:, 1], tg[:, 0]] * 0.3
                ok = C.dans_polygones(q, il["polys"])
                if not ok.any():
                    continue
                L = 0.25 * float(ok.sum())
                n = r.poisson(L * larg * cfg["debord_par_m2"])
                s = np.clip(r.choice(sg[ok], n) + r.uniform(0, 0.25, n), 0.05, bd.B.L - 0.05) if n else np.zeros(0)
                off = bd.interp(bd.uf, s) - 0.02 - larg * r.uniform(0, 1, n) ** 1.8   # plus dense contre la face
                pts, tg = C.point_a(bd.B.P, s)
                nl = np.c_[-tg[:, 1], tg[:, 0]]
                xy = pts + nl * off[:, None]
                # altitude sur le maillage fabriqué (revue conformité r2 : éclats flottants de 2 à 14 cm avec
                # l'altitude recalculée hors maillage) ; hors du sol : éclat écarté
                tri, z = self.loc.trouver(xy) if n else (np.zeros(0, int), np.zeros(0))
                okz = tri >= 0
                self._ajouter(il, cfg, np.c_[xy, z][okz], r, "chaussee")
                n = r.poisson(L * cfg["tete_par_m"])
                if n:
                    s = np.clip(r.choice(sg[ok], n) + r.uniform(0, 0.25, n), 0.05, bd.B.L - 0.05)
                    # seulement sur un élément posé (ni joint, ni au-delà d'un bout de file)
                    sur = np.array([any(e0 + 0.03 <= x <= e1 - 0.03 for e0, e1 in self.cases.get(bid, ())) for x in s],
                                   dtype=bool)
                    s = s[sur]
                    pts, tg = C.point_a(bd.B.P, s)
                    nl = np.c_[-tg[:, 1], tg[:, 0]]
                    u_ = r.uniform(0.04, bd.interp(bd.base, s) - 0.02)
                    xy = pts + nl * u_[:, None]
                    z = bd.interp(bd.ztop, s) - 0.003           # tête posée : jitter de hauteur ±2-3 mm
                    self._ajouter(il, cfg, np.c_[xy, z], r, "tete")
        self._massifs()
        self.points.sort(key=lambda p: p["id"])
        n_c = sum(len(l["taille"]) for _, _, l in self.couverture)
        self.log(f"   éclats : {n_c} en couverture, {len(self.points)} épars")
        return self.points

    def _massifs(self):
        """Massifs de BRF hors îlots (surfaces de la description) : même couverture de copeaux, à
        DENSITE_MASSIF /m² (graine = hash(surface))."""
        sol = self.sol
        cfg = ECLATS["brf_bois_concasse"]
        P3, Tt = sol.P3, sol.T
        sel_all = np.where((sol.cl == "brf_bois_concasse") & (sol.ilot_tri == ""))[0]
        for sid in sorted(set(sol.surf_tri[sel_all].tolist())):
            sel = sel_all[sol.surf_tri[sel_all] == sid]
            r = K.rng(sid, "semis_massif")
            tri = Tt[sel]
            a, b, c = P3[tri[:, 0]], P3[tri[:, 1]], P3[tri[:, 2]]
            aire = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
            nb = r.poisson(aire * DENSITE_MASSIF)
            k = np.repeat(np.arange(len(sel)), nb)
            u, v = r.uniform(size=len(k)), r.uniform(size=len(k))
            f = u + v > 1
            u[f], v[f] = 1 - u[f], 1 - v[f]
            Q = a[k] + (b[k] - a[k]) * u[:, None] + (c[k] - a[k]) * v[:, None]
            if len(Q) == 0:
                continue
            lot = self._tirage(cfg, Q, Q[:, 2], r)
            lot["ilot"] = sid
            self.couverture.append((cfg["materiau"], cfg["famille"], lot))

    def _ajouter(self, il, cfg, Q, r, ou):
        n = len(Q)
        if n == 0:
            return
        lot = self._tirage(cfg, Q, Q[:, 2], r)
        base = len([p for p in self.points if p["id"].startswith(f"{il['id']}/{ou}/")])
        for i in range(n):
            pid = f"{il['id']}/{ou}/{base + i:05d}"
            self.points.append({
                "id": pid, "asset": f"{cfg['famille']}_v{int(lot['var'][i]):02d}",
                "p": [float(x) for x in lot["p"][i]],
                "rpy_deg": [float(x) for x in lot["rpy"][i]],
                "s": [float(lot["taille"][i])] * 3, "graine": K.graine(pid),
                "cd": [float(lot["teinte"][i])] + [float(x) for x in lot["couleur"][i]],
                "_materiau": cfg["materiau"]})

    def prototypes(self, dossier, ref):
        """Prototypes d'éclats (prototypes/eclats/<nom>.usda) ; renvoie {nom: (chemin, matériau)}."""
        out = {}
        for cfg in ECLATS.values():
            for k in range(n_variantes(cfg["famille"])):
                nom = f"{cfg['famille']}_v{k:02d}"
                P, counts, idx, N, st1 = prototype_eclat(cfg["famille"], k)
                P = P * np.array(cfg["forme"])
                st = U.scene(f"Éclat {nom} (pj_ilot.py) : taille unitaire (grande dimension = 1), origine au centre "
                             "de la boîte englobante, mis à l'échelle par instance.", racine=nom)
                echelle_uv = math.sqrt(cfg["taille"][0] * cfg["taille"][1])     # UV ~ mètres à la taille typique
                U.maillage(st, f"/{nom}/maillage", P, counts, idx, normales=N, st1=st1 * echelle_uv,
                           materiau_id=cfg["materiau"])
                f = dossier / "eclats" / f"{nom}.usda"
                U.enregistrer(st, f)
                out[nom] = (f, cfg["materiau"])
        return out

    def ecrire_usd(self, chemin, protos, ref_fichier, chemin_couverture=None, ref_couverture=None):
        """ilots.usda (éclats épars) et ilots_couverture.usdc (couverture dense)."""
        st = U.scene("Éclats épars des îlots (pj_ilot.py) : débordement sur la chaussée et tête de bordure "
                     "(graine = hash(îlot)) ; le remplissage est dans sol.usda, sa couverture dense dans "
                     "ilots_couverture.usdc.", data={"version": K.VERSION, "description": self.desc.hash})
        U.xform(st, "/World/PJ_Ilots")
        mats = sorted(set(p["_materiau"] for p in self.points))
        for mat in mats:
            pts = [p for p in self.points if p["_materiau"] == mat]
            sous = sorted(set(p["asset"] for p in pts))
            si = {n: i for i, n in enumerate(sous)}
            proto_list = [(n, U.chemin_relatif(protos[n][0], ref_fichier), None) for n in sous]
            q = np.array([K.quat_de_matrice(K.rotation_rpy(p["rpy_deg"])) for p in pts])
            pi = U.instancer(st, f"/World/PJ_Ilots/{mat}", proto_list, [si[p["asset"]] for p in pts],
                             [p["p"] for p in pts], q, echelles=[p["s"] for p in pts],
                             primvars={"teinte": (U.vt([p["cd"][0] for p in pts], T.FloatArray), T.FloatArray),
                                       "couleur": (U.vt([p["cd"][1:4] for p in pts], T.Color3fArray), T.Color3fArray),
                                       "uv_decalage": (U.vt([[(p["graine"] % 997) / 97.0, (p["graine"] // 997 % 991) / 97.0]
                                                             for p in pts], T.Float2Array), T.Float2Array)})
            U.lier_chemin(pi.GetPrim(), f"/World/Looks_v2/{mat}")
        U.enregistrer(st, chemin)
        if chemin_couverture is None:
            return
        st = U.scene("Couverture dense des remplissages d'îlots (pj_ilot.py, regle:pj_ilot.couverture) : copeaux de "
                     "BRF et gravillons instanciés, 40-70 % de chaque éclat au-dessus du remplissage.",
                     data={"version": K.VERSION, "description": self.desc.hash})
        U.xform(st, "/World/PJ_Ilots_couverture")
        for mat, fam, lot in self.couverture:
            sous = [f"{fam}_v{k:02d}" for k in range(n_variantes(fam))]
            proto_list = [(n, U.chemin_relatif(protos[n][0], ref_couverture), None) for n in sous]
            n = len(lot["taille"])
            r = K.rng(lot["ilot"], "uv_couverture")
            pi = U.instancer(st, f"/World/PJ_Ilots_couverture/{lot['ilot'].replace('-', '_')}", proto_list, lot["var"],
                             lot["p"], _quats(lot["R"]), echelles=np.repeat(lot["taille"][:, None], 3, axis=1),
                             primvars={"teinte": (U.vt(lot["teinte"], T.FloatArray), T.FloatArray),
                                       "couleur": (U.vt(lot["couleur"], T.Color3fArray), T.Color3fArray),
                                       "uv_decalage": (U.vt(r.uniform(0, 10, (n, 2)), T.Float2Array), T.Float2Array)})
            U.lier_chemin(pi.GetPrim(), f"/World/Looks_v2/{mat}")
        U.enregistrer(st, chemin_couverture)

    def zones(self):
        """Zones de dispersion pour PG_Ilots (UE) : polygone de l'îlot (repère local) et paramètres."""
        out = []
        for il in self.desc.ilots:
            rem = il["p"]["remplissage"]
            zs = self.sol.z_ilots.get(il["id"])
            cfg = ECLATS.get(rem["materiau_id"], {})
            out.append({"id": il["id"], "type": il["p"].get("type"), "materiau_id": rem["materiau_id"],
                        "polygone_local": [K.r3(r, 3) for r in il["polys"][0]],
                        "remplissage": rem, "ceinture": il["p"].get("ceinture", []),
                        "z_dessus_ceinture_local": K.r3([float(zs[1].min()), float(zs[1].max())], 3) if zs else None,
                        "eclats": cfg.get("famille"),
                        "couverture": {k: cfg[k] for k in ("taille", "densite_bord", "densite_int", "bord_m", "emergence")}
                        if cfg else None})
        return out
