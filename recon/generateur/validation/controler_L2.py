# -*- coding: utf-8 -*-
"""Contrôles indépendants du lot L2 (Python système : numpy, scipy, shapely ; aucun code commun avec les HDA).

    python recon/generateur/validation/controler_L2.py [recon/out/generateur/<scene> ...] [--json SORTIE]

Lit les sorties du pilote (<scene>/l2/ : sol_*.npy, niveaux.json, entites.json, elements.json, bev.json,
mesures_l2.json) et le modèle (<scene>/modele_voie.json), recalcule les valeurs attendues par le nivellement
analytique (analytique_L2, analytique_L1) et mesure :
  - étanchéité du sol (TQ-SOL-009) : arêtes de bord hors contour, non-variétés, doublons, faces dégénérées,
    orientation, recouvrement en (s, t) (TQ-SOL-001), marches visibles hors éléments (jointure entre surfaces) ;
  - Z du sol visible contre le modèle (TQ-SOL-004, TQ-SOL-013), lignes de rupture traversées (TQ-SOL-003), angles ;
  - vue des bordures fabriquées (dessus de l'élément − surface devant la face) contre le modèle (± 5 mm) ; retrait
    du trottoir sous la tête (TQ-SOL-013 (6) : 4 ± 2 mm ; (7) bandes plantées : 3 à 5 cm) ;
  - dévers (≤ 2 %) et pente (< 5 % hors rampants) des trottoirs (ARR2007, RF-MA-TRO-002/003) ; rampants d'abaissé
    (≥ 1,50 m à 8 % ou ≥ 2,40 m à 5 %, RF-MA-ABA-004) ; BEV (DEF-031, RF-MA-BEV-002) ;
  - TQ-BOR-002 (éléments rigides, coupes), TQ-BOR-005 (joints non transparents), TQ-BOR-007 (sol sous l'élément,
    affleurement des caniveaux ± 3 mm).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import analytique_L1 as A1  # noqa: E402
import analytique_L2 as A2  # noqa: E402

DEPOT = ICI.parents[2]
SORTIE = DEPOT / "recon" / "out" / "generateur"
TOL_ST = 1e-4            # positions (s, t) stockées en flottants 32 bits (≈ 1e-5 m à 100 m)


def _r(x, n=6):
    if x is None:
        return None
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def stats(v):
    v = np.asarray([x for x in v if x is not None and math.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "min": _r(v.min()), "p50": _r(np.percentile(v, 50)), "p99": _r(np.percentile(v, 99)),
            "max": _r(v.max())}


# ------------------------------------------------------------------------------------------------ chargement
class Scene:
    def __init__(self, dossier: Path):
        self.d = Path(dossier)
        self.nom = self.d.name
        self.m = json.loads((self.d / "modele_voie.json").read_text(encoding="utf-8"))
        l2 = self.d / "l2"
        self.l2 = l2
        self.P = np.load(l2 / "sol_points.npy")                    # x, y, z, s, t
        self.faces = np.load(l2 / "sol_faces.npy")
        self.comptes = np.load(l2 / "sol_comptes.npy")
        self.attr = np.load(l2 / "sol_attributs.npy")              # z_type, section, bande, visible, classe, mat, bande_id
        self.voc = json.loads((l2 / "sol_vocabulaire.json").read_text(encoding="utf-8"))
        self.off = np.concatenate([[0], np.cumsum(self.comptes)])
        self.niv = json.loads((l2 / "niveaux.json").read_text(encoding="utf-8"))
        self.ent = {e["id"]: e for e in json.loads((l2 / "entites.json").read_text(encoding="utf-8"))}
        self.elements = json.loads((l2 / "elements.json").read_text(encoding="utf-8"))
        self.bev = json.loads((l2 / "bev.json").read_text(encoding="utf-8"))
        v_ = json.loads((l2 / "vegetation.json").read_text(encoding="utf-8"))
        # rg_vegetation/0.2 (étape 1) : arbres du modèle exportés pour l'étape 2, sous « arbres »
        self.veg = v_["arbres"] if isinstance(v_, dict) else v_
        self.mes = json.loads((l2 / "mesures_l2.json").read_text(encoding="utf-8"))
        self.rampe = float(self.niv.get("rampe_plateau_pct") or 7.0)
        self.routes = {r["id"]: A2.Route(self.m, r["id"], self.rampe) for r in self.m["routes"]}
        self.R = next(iter(self.routes.values()))

    def face(self, i):
        return self.faces[self.off[i]:self.off[i + 1]]

    def classe(self, i):
        return self.voc["classe"][self.attr[i, 4]]


# ------------------------------------------------------------------------------------------------ étanchéité
def etancheite(sc: Scene) -> dict:
    R = sc.R
    nf = len(sc.comptes)
    a_list, b_list, f_list = [], [], []
    for i in range(nf):
        f = sc.face(i)
        for k in range(len(f)):
            a_list.append(f[k])
            b_list.append(f[(k + 1) % len(f)])
            f_list.append(i)
    a = np.array(a_list)
    b = np.array(b_list)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    cle = lo.astype(np.int64) * (len(sc.P) + 1) + hi
    u, inv, cnt = np.unique(cle, return_inverse=True, return_counts=True)
    bord = np.where(cnt[inv] == 1)[0]
    nonvar = int((cnt > 2).sum())
    # orientation : une arête intérieure est parcourue une fois dans chaque sens
    sens = Counter()
    for k in np.where(cnt[inv] == 2)[0]:
        sens[(int(cle[k]), int(a[k] < b[k]))] += 1
    mal_orientees = sum(1 for (c, s_), n in sens.items() if n > 1)
    # arêtes de bord : sur le contour extérieur (s = 0, s = L ou t = bord extérieur du profil et des abords)
    S, T = sc.P[:, 3], sc.P[:, 4]
    cache = {}

    def sur_contour(p):
        s, t = float(S[p]), float(T[p])
        if abs(s) < TOL_ST or abs(s - R.L) < TOL_ST:
            return True
        k0 = R.section(s - 1e-6)
        k1 = R.section(s + 1e-6)
        for k in {k0, k1}:
            key = (k, round(s, 5))
            if key not in cache:
                cache[key] = R.contour_t(s, k)
            tmax, tmin = cache[key]
            if abs(t - tmax) < TOL_ST or abs(t - tmin) < TOL_ST:
                return True
        return False

    hors = [k for k in bord if not (sur_contour(int(a[k])) and sur_contour(int(b[k])))]
    # faces dégénérées et doublons
    deg, cles = 0, Counter()
    aires = []
    for i in range(nf):
        f = sc.face(i)
        p = sc.P[f, :3]
        ar = 0.0
        for k in range(1, len(f) - 1):
            ar += 0.5 * np.linalg.norm(np.cross(p[k] - p[0], p[k + 1] - p[0]))
        aires.append(ar)
        if ar < 1e-6:
            deg += 1
        cles[tuple(sorted(int(x) for x in f))] += 1
    doublons = sum(n - 1 for n in cles.values() if n > 1)
    # recouvrement en (s, t) (TQ-SOL-001) : faces non verticales ; aire signée = aire du contour, aucune inversée
    nonmur = np.where(sc.attr[:, 0] != 4)[0]
    sa = []
    for i in nonmur:
        f = sc.face(i)
        q = sc.P[f][:, 3:5]
        x, y = q[:, 0], q[:, 1]
        sa.append(0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)))
    sa = np.array(sa)
    signe = np.sign(np.median(sa))
    inversees = int((sa * signe < -1e-12).sum())
    ss = np.linspace(0.0, R.L, int(R.L / 0.05) + 1)
    larg = []
    for s in ss:
        k = R.section(s)
        tmax, tmin = R.contour_t(s, k)
        larg.append(tmax - tmin)
    aire_contour = float(np.trapezoid(larg, ss)) if hasattr(np, "trapezoid") else float(np.trapz(larg, ss))
    aire_faces = float(np.abs(sa).sum())
    # contrôle de TQ-SOL-001 : aire(union) = somme(aires) à 1e-6 m² près (0 recouvrement), en (s, t)
    from shapely import union_all
    from shapely.geometry import Polygon
    geoms = [Polygon(sc.P[sc.face(i)][:, 3:5]) for i, a_ in zip(nonmur, sa) if abs(a_) > 1e-14]
    aire_union = float(union_all(geoms).area) if geoms else 0.0
    # angles des triangles visibles (3D)
    vis = np.where(np.isin(sc.attr[:, 0], (0, 2)))[0]
    amin = []
    for i in vis:
        f = sc.face(i)
        if len(f) != 3:
            continue
        p = sc.P[f, :3]
        angs = []
        for k in range(3):
            u_ = p[(k + 1) % 3] - p[k]
            v_ = p[(k + 2) % 3] - p[k]
            c = np.dot(u_, v_) / max(np.linalg.norm(u_) * np.linalg.norm(v_), 1e-15)
            angs.append(math.degrees(math.acos(max(-1.0, min(1.0, c)))))
        amin.append(min(angs))
    amin = np.array(amin)
    return {"faces": nf, "faces_visibles": int(len(vis)), "murs": int((sc.attr[:, 0] == 4).sum()),
            "aretes": int(len(u)), "aretes_de_bord": int(len(bord)), "aretes_de_bord_hors_contour": len(hors),
            "exemples_hors_contour": [[_r(S[a[k]], 4), _r(T[a[k]], 4)] for k in hors[:5]],
            "non_varietes": nonvar, "aretes_mal_orientees": mal_orientees, "faces_degenerees_1e-6": deg,
            "faces_en_double": doublons, "faces_inversees_st": inversees,
            "aire_contour_st_m2": _r(aire_contour, 4), "aire_faces_st_m2": _r(aire_faces, 4),
            "ecart_aire_st_m2": _r(aire_faces - aire_contour, 6),
            "ecart_aire_st_relatif (contour intégré au pas de 5 cm, coordonnées float32)":
                _r((aire_faces - aire_contour) / max(aire_contour, 1e-9), 10),
            "aire_union_st_m2": _r(aire_union, 6),
            "recouvrement_st_m2 (somme des aires − aire de l'union, TQ-SOL-001)": float(f"{aire_faces - aire_union:.3e}"),
            "angle_min_triangles_visibles": stats(amin),
            "part_angle_min_ge_20": _r(float((amin >= 20.0).mean()) if len(amin) else 1.0, 5),
            "part_angle_min_ge_25": _r(float((amin >= 25.0 - 1e-6).mean()) if len(amin) else 1.0, 5)}


# ------------------------------------------------------------------------------------------------ empreintes
def empreintes(sc: Scene):
    """Empreintes des bordures (côté haut, base) et des caniveaux posés (côté bas, largeur) en (s, t), élargies de
    2 mm : une marche du sol située dedans est cachée par l'élément."""
    polys = []
    for c in sc.niv["bordures"]:
        q = [(p["s_ref"], p["t_ref"]) for p in c["points"]]
        qq = [q[0]] + [x for i, x in enumerate(q[1:], 1) if math.hypot(x[0] - q[i - 1][0], x[1] - q[i - 1][1]) > 1e-9]
        if len(qq) < 2:
            continue
        ls = LineString(qq)
        polys.append(ls.buffer(c["base"] + 0.002, single_sided=True, join_style=2))
        polys.append(ls.buffer(-0.002, single_sided=True, join_style=2))
        if c["wc"] > 0:
            pts = c["points"]
            run = []
            for i in range(len(pts)):
                if pts[i]["can"] == 1 and pts[i]["kind"] == 0:
                    run.append((pts[i]["s_ref"], pts[i]["t_ref"]))
                else:
                    if len(run) >= 2:
                        polys.append(LineString(run).buffer(-(c["wc"] + 0.002), single_sided=True, join_style=2))
                    run = []
            if len(run) >= 2:
                polys.append(LineString(run).buffer(-(c["wc"] + 0.002), single_sided=True, join_style=2))
    return unary_union(polys) if polys else None


def marches_visibles(sc: Scene, emp) -> dict:
    """Murs (faces verticales qui ferment une marche du sol) hors de l'empreinte des éléments : marches visibles."""
    murs = np.where(sc.attr[:, 0] == 4)[0]
    hors, hmax = 0, 0.0
    ex = []
    for i in murs:
        f = sc.face(i)
        st = sc.P[f][:, 3:5]
        z = sc.P[f][:, 2]
        m = st.mean(axis=0)
        h = float(z.max() - z.min())
        if emp is not None and emp.covers(Point(m[0], m[1])):
            continue
        hors += 1
        if h > hmax:
            hmax = h
        if len(ex) < 5:
            ex.append([_r(m[0], 3), _r(m[1], 3), _r(h, 4)])
    return {"murs": int(len(murs)), "murs_hors_elements": hors, "marche_visible_max_m": _r(hmax, 6), "exemples": ex}


# ------------------------------------------------------------------------------------------------ Z du sol
def z_sol(sc: Scene) -> dict:
    """Z des sommets des faces visibles contre le nivellement analytique (TQ-SOL-004, TQ-SOL-013)."""
    R = sc.R
    cache = {}

    def coupe(s, k):
        key = (k, round(float(s), 6))
        c = cache.get(key)
        if c is None:
            c = R.coupe(float(s), k)
            cache[key] = c
        return c

    ec = defaultdict(list)
    pire = (0.0, None)
    vis = np.where(np.isin(sc.attr[:, 0], (0, 2)))[0]
    vus = {}
    for i in vis:
        zt, k, b = int(sc.attr[i, 0]), int(sc.attr[i, 1]), int(sc.attr[i, 2])
        for p in sc.face(i):
            key = (int(p), zt, k, b)
            if key in vus:
                continue
            s, t, z = sc.P[p, 3], sc.P[p, 4], sc.P[p, 2]
            c = coupe(s, k)
            T = c["T"]
            if zt == 0:
                if b >= 0:
                    zm = R.z_bande(c, b, t)
                else:
                    zm = R.z_bande(c, 0, T[0]) if b == -1 else R.z_bande(c, len(T) - 2, T[-1])
                cat = "bandes" if b >= 0 else "abords"
            else:
                zm = None
                for l, bd in c["bords"].items():
                    u = bd["h"] * (t - T[l])
                    if bd["wc"] > 0 and -bd["wc"] - 1e-4 <= u <= 1e-4:
                        zm = bd["pied"] + c["dz"] + bd["dhc"] * min(1.0, max(0.0, -u / bd["wc"]))
                        break
                cat = "caniveau_releve"
            if zm is None:
                continue
            e = float(z - zm)
            vus[key] = e
            ec[cat].append(abs(e))
            if abs(e) > abs(pire[0]):
                pire = (e, [_r(s, 4), _r(t, 4), _r(z, 5), _r(zm, 5), cat])
    tous = [x for v in ec.values() for x in v]
    return {"sommets": len(tous), "ecart_max_m": _r(max(tous) if tous else 0.0, 7),
            "par_zone": {k: stats(v) for k, v in sorted(ec.items())}, "pire": pire[1]}


def ruptures(sc: Scene) -> dict:
    """Lignes de rupture traversées par une face visible (TQ-SOL-003, tolérance 1e-5 m, ici 1e-4 en float32) :
    limites sans bordure (dévers, revêtement, rives), lignes transversales (jonctions de sections, bords de
    rampe et de bateau, bornes des ralentisseurs)."""
    R = sc.R
    vis = np.where(np.isin(sc.attr[:, 0], (0, 2)))[0]
    trans = sorted({float(x["s0"]) for x in R.secs[1:]} | set(A1.bornes_verticales(R.objets, R.rid, R.rampe)))
    for k in range(len(R.secs)):
        for l, lim in enumerate(R.profil(k)["limites"]):
            for a in (lim.get("bordure") or {}).get("abaisses", []) or []:
                s0, s1, r = float(a["s0"]), float(a["s1"]), float(a.get("rampant_m", 0.0))
                cou = any(s1 > r0 and s0 < r1 for r0, r1 in R.ral)
                trans += [s0, s1] if cou else [s0 - r, s0, s1, s1 + r]
    trans = sorted({round(x, 6) for x in trans if 0 < x < R.L})
    n_long, n_trans = 0, 0
    ex = []
    cacheT = {}
    for i in vis:
        f = sc.face(i)
        st = sc.P[f][:, 3:5]
        k = int(sc.attr[i, 1])
        smin, smax = st[:, 0].min(), st[:, 0].max()
        for x in trans:
            if smin < x - TOL_ST and smax > x + TOL_ST:
                n_trans += 1
                if len(ex) < 4:
                    ex.append(["transversale", _r(x, 4), _r(st[:, 1].mean(), 3)])
                break
        p = R.profil(k)
        us = []
        for (s, t) in st:
            key = (k, round(float(s), 6))
            if key not in cacheT:
                cacheT[key] = A1.t_limites(p, float(s))
            us.append([t - x for x in cacheT[key]])
        us = np.array(us)
        for l, lim in enumerate(p["limites"]):
            bo, nat = R.bordure_effective(k, l)
            if nat == 1:
                continue
            if us[:, l].max() > TOL_ST and us[:, l].min() < -TOL_ST:
                n_long += 1
                if len(ex) < 8:
                    ex.append(["longitudinale", l, _r(st[:, 0].mean(), 3)])
                break
    return {"faces_visibles": int(len(vis)), "lignes_transversales": len(trans), "faces_traversant_longitudinale": n_long,
            "faces_traversant_transversale": n_trans, "exemples": ex}


# ------------------------------------------------------------------------------------------------ bordures
def _chaine_st(sc: Scene, kid: str, sc_abs: float):
    """(s_ref, t_ref, point de début du segment, point de fin) de la file kid à l'abscisse de courbe sc_abs."""
    e = sc.ent[kid]
    c = next(x for x in sc.niv["bordures"] if x["id"] == kid)
    ns = e["niv_s"]
    pts = c["points"]
    for i in range(len(ns) - 1):
        if ns[i + 1] - ns[i] < 1e-9:
            continue
        if ns[i] - 1e-9 <= sc_abs <= ns[i + 1] + 1e-9 or i == len(ns) - 2:
            a = (sc_abs - ns[i]) / (ns[i + 1] - ns[i])
            p, q = pts[i], pts[i + 1]
            return p["s_ref"] + a * (q["s_ref"] - p["s_ref"]), p["t_ref"] + a * (q["t_ref"] - p["t_ref"]), p, q, c
    raise ValueError(kid)


def attendu_bordure(sc: Scene, kid: str, sc_abs: float):
    """Vue visible attendue (dessus − surface devant la face), tête, Z attendu derrière (base + 3 cm) et retrait
    attendu, recalculés sur le modèle (longitudinale : coupe de la section ; retour : sections haute et basse)."""
    R = sc.R
    s, t, p, q, c = _chaine_st(sc, kid, sc_abs)
    if p["kind"] == 0 and q["kind"] == 0:
        k = p["section"]
        l = p["limite"]
        cp = R.coupe(s, k)
        bd = cp["bords"][l]
        tete = bd["tete"]
        lim = R.profil(k)["limites"][l]["bordure"]
        if bd["wc"] > 0:
            devant = bd["pied"] + (0.0 if R.caniveau_pose(s) else cp["dz"])
        else:
            devant = R.z_bande(cp, bd["bande_basse"], cp["T"][l])
        tb = cp["T"][l] + bd["h"] * (bd["base"] + 0.03)
        arriere = R.z_bande(cp, bd["bande_haute"], tb)
        return {"type": "longitudinale", "s": s, "t": t, "vue_visible": tete - devant, "tete": tete, "arriere": arriere,
                "vue_modele": R.vue(lim, s), "retrait": tete - arriere, "base": bd["base"],
                "plantee": cp["retraits"][bd["bande_haute"]] == A2.RETRAIT_PLANTE}
    # retour de bordure : section haute (k_haut) et basse (k_bas) à la jonction
    kb = (p if p["kind"] == 1 else q)["k_bas"]
    kh = (p if p["kind"] == 1 else q)["section"]
    cb = R.coupe(s, kb)
    ch = R.coupe(s, kh)
    Tb, Th = cb["T"], ch["T"]
    bb = next(i for i in range(len(Tb) - 1) if Tb[i + 1] - 1e-6 <= t <= Tb[i] + 1e-6 and cb["cls"][i] == 0)
    bh = next(i for i in range(len(Th) - 1) if Th[i + 1] - 1e-6 <= t <= Th[i] + 1e-6 and ch["cls"][i] == 1)
    ret = A2.RETRAIT_TROTTOIR
    zh = R.z_bande(ch, bh, t)
    pied = R.z_bande(cb, bb, t)
    # devant le retour, dans la bande d'un caniveau posé de la section basse : dessus du caniveau
    for l, bd in cb["bords"].items():
        u = bd["h"] * (t - Tb[l])
        if bd["wc"] > 0 and -bd["wc"] <= u <= 0 and R.caniveau_pose(s):
            pied = bd["pied"] + bd["dhc"] * (-u / bd["wc"])
            break
    return {"type": "retour", "s": s, "t": t, "vue_visible": zh + ret - pied, "tete": zh + ret, "arriere": zh,
            "vue_modele": None, "retrait": ret, "plantee": False}


def _normale_st(sc: Scene, kid: str, sc_abs: float):
    """Normale côté haut (gauche de la file) en (s, t) à l'abscisse de courbe sc_abs."""
    s, t, p, q, c = _chaine_st(sc, kid, sc_abs)
    ds, dt = q["s_ref"] - p["s_ref"], q["t_ref"] - p["t_ref"]
    nrm = math.hypot(ds, dt) or 1.0
    return -dt / nrm, ds / nrm


def emprises_autres(sc: Scene) -> dict:
    """Pour chaque file : empreinte (s, t) des corps de bordure autres que la pièce sondée : autres files, et pièces
    de la même file de part et d'autre d'un angle (retour de bordure)."""
    corps = {}
    for c in sc.niv["bordures"]:
        q = [(p["s_ref"], p["t_ref"]) for p in c["points"]]
        segs = []
        for i in range(len(q) - 1):
            if math.hypot(q[i + 1][0] - q[i][0], q[i + 1][1] - q[i][1]) > 1e-9:
                d = math.atan2(q[i + 1][1] - q[i][1], q[i + 1][0] - q[i][0])
                segs.append((d, LineString([q[i], q[i + 1]]).buffer(c["base"], single_sided=True, join_style=2)))
        corps[c["id"]] = segs
    out = {}
    for c in sc.niv["bordures"]:
        polys = [p for cc, segs in corps.items() if cc != c["id"] for _, p in segs]
        segs = corps[c["id"]]
        for (a1, p1), (a2, p2) in zip(segs, segs[1:]):
            if abs(math.remainder(a1 - a2, 2 * math.pi)) > math.radians(30):
                polys += [p1, p2]
        out[c["id"]] = unary_union(polys) if polys else Point(1e9, 1e9).buffer(0.1)
    return out


def bordures(sc: Scene, emp_bordures=None) -> dict:
    """Vue fabriquée (dessus de l'élément − surface 4 mm devant la face) contre la vue attendue ; retrait du trottoir
    3 cm derrière l'élément. Une sonde « devant » ou « derrière » qui tombe sous un autre corps de bordure (angle d'un
    retour) n'est pas comptée : elle ne mesure pas la pièce sondée (sondes écartées, comptées)."""
    vues, retr, retr_pl, ecarts_modele = [], [], [], []
    hors, sous_ko, n, ecartees, hors_emprise = [], 0, 0, 0, []
    par_type = defaultdict(list)
    for m in sc.mes["elements"]:
        if m["z_dessus"] is None or m["z_devant"] is None:
            # côté transversal d'une avancée posé sur la coupe d'un bout de scène (s = 0 ou s = L, L2b-13) : sa face
            # regarde hors de l'emprise, rien n'est modélisé devant elle (sonde hors emprise, comptée à part)
            if m["z_dessus"] is not None:
                s_, t_, *_ = _chaine_st(sc, m["bordure"], m["s"])
                ns_, nt_ = _normale_st(sc, m["bordure"], m["s"])
                sd = s_ - 0.004 * ns_
                if sd < 1e-4 or sd > sc.R.L - 1e-4:
                    hors_emprise.append(m["id"])
                    continue
            hors.append([m["id"], "sonde sans impact"])
            continue
        a = attendu_bordure(sc, m["bordure"], m["s"])
        if emp_bordures is not None:
            ns_, nt_ = _normale_st(sc, m["bordure"], m["s"])
            b_ = a.get("base", 0.15)
            e_ = emp_bordures[m["bordure"]]
            if e_.covers(Point(a["s"] - 0.004 * ns_, a["t"] - 0.004 * nt_)) or \
                    e_.covers(Point(a["s"] + (b_ + 0.03) * ns_, a["t"] + (b_ + 0.03) * nt_)):
                ecartees += 1
                continue
        n += 1
        vm = m["z_dessus"] - m["z_devant"]
        e = vm - a["vue_visible"]
        vues.append(abs(e))
        par_type[a["type"]].append(abs(e))
        if abs(e) > 0.005:
            hors.append([m["id"], _r(a["s"], 3), _r(vm, 4), _r(a["vue_visible"], 4)])
        if a["vue_modele"] is not None and abs(a["vue_visible"] - a["vue_modele"]) < 1e-9:
            ecarts_modele.append(abs(e))
        if m["z_arriere"] is not None:
            rmes = m["z_dessus"] - m["z_arriere"]
            if a["plantee"]:
                retr_pl.append(rmes)
            else:
                retr.append(rmes - a["retrait"])
        if any(z is None for z in m["sol_sous"]):
            sous_ko += 1
    ret_ok = list(retr)
    return {"sondes": n, "sondes_ecartees_angles": ecartees, "vue_ecart_abs": stats(vues), "vue_ecart_par_type": {k: stats(v) for k, v in par_type.items()},
            "vue_hors_5mm": len([h for h in hors if len(h) > 2]), "sondes_sans_impact": len([h for h in hors if len(h) == 2]),
            "sondes_hors_emprise_bout": len(hors_emprise), "elements_hors_emprise_bout": sorted(set(hors_emprise)),
            "exemples_hors": hors[:6],
            "vue_ecart_modele_abs (hors ralentisseur et retours)": stats(ecarts_modele),
            "retrait_trottoir_ecart_m (mesuré − attendu, TQ-SOL-013 (6) ± 2 mm)": stats(ret_ok),
            "retrait_plantee_m (TQ-SOL-013 (7) : 0,03 à 0,05)": stats(retr_pl),
            "sol_sous_element_absent (TQ-BOR-007)": sous_ko}


# ------------------------------------------------------------------------------------------------ trottoirs
def _rampants(R, sc):
    """Intervalles de rampant des abaissés non couverts : [(s_a, s_b, k, l), ...]."""
    out = []
    for k in range(len(R.secs)):
        for l, lim in enumerate(R.profil(k)["limites"]):
            for a in (lim.get("bordure") or {}).get("abaisses", []) or []:
                s0, s1, r = float(a["s0"]), float(a["s1"]), float(a.get("rampant_m", 0.0))
                if any(s1 > r0 and s0 < r1 for r0, r1 in R.ral):
                    continue
                out.append((s0 - r, s0, k, l, s1, s1 + r))
    return out


def trottoirs(sc: Scene) -> dict:
    """Dévers et pente des faces de trottoir (ARR2007 : dévers ≤ 2 %, pente ≤ 5 % hors rampants)."""
    R = sc.R
    ramp = _rampants(R, sc)
    dev, pente, pente_ramp = [], [], []
    for i in np.where(sc.attr[:, 0] == 0)[0]:
        if sc.classe(i) != "trottoir":
            continue
        f = sc.face(i)
        p = sc.P[f, :3]
        nrm = np.cross(p[1] - p[0], p[2] - p[0])
        if abs(nrm[2]) < 1e-12:
            continue
        gx, gy = -nrm[0] / nrm[2], -nrm[1] / nrm[2]
        s = float(sc.P[f, 3].mean())
        _, _, th, _ = R.ref.eval(s)
        lon = gx * math.cos(th) + gy * math.sin(th)
        tra = -gx * math.sin(th) + gy * math.cos(th)
        dev.append(abs(tra))
        dans = any((a - 0.02 <= s <= b + 0.02) or (c - 0.02 <= s <= d + 0.02) for a, b, k, l, c, d in ramp)
        (pente_ramp if dans else pente).append(abs(lon))
    return {"faces": len(dev), "devers_abs_pct": stats([100 * x for x in dev]),
            "pente_hors_rampants_abs_pct": stats([100 * x for x in pente]),
            "pente_rampants_abs_pct": stats([100 * x for x in pente_ramp])}


class _Locator:
    """Localisation de points (s, t) dans des triangles (grille de seaux) ; Z barycentrique."""

    def __init__(self, tri_st, tri_z, pas=0.5):
        self.st, self.z, self.pas = tri_st, tri_z, pas
        self.g = defaultdict(list)
        for i, q in enumerate(tri_st):
            lo, hi = q.min(axis=0), q.max(axis=0)
            for a in range(int(math.floor(lo[0] / pas)), int(math.floor(hi[0] / pas)) + 1):
                for b in range(int(math.floor(lo[1] / pas)), int(math.floor(hi[1] / pas)) + 1):
                    self.g[(a, b)].append(i)

    def z_en(self, s, t):
        for i in self.g.get((int(math.floor(s / self.pas)), int(math.floor(t / self.pas))), []):
            (x0, y0), (x1, y1), (x2, y2) = self.st[i]
            d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(d) < 1e-15:
                continue
            l0 = ((y1 - y2) * (s - x2) + (x2 - x1) * (t - y2)) / d
            l1 = ((y2 - y0) * (s - x2) + (x0 - x2) * (t - y2)) / d
            l2 = 1 - l0 - l1
            if min(l0, l1, l2) >= -1e-7:
                return float(l0 * self.z[i][0] + l1 * self.z[i][1] + l2 * self.z[i][2])
        return None


def rampants(sc: Scene) -> dict:
    """Rampants d'abaissé mesurés sur le sol fabriqué (trottoir, 10 cm derrière la bordure) : longueur et pente
    (RF-MA-ABA-004 : ≥ 1,50 m à 8 % au plus, ou ≥ 2,40 m à 5 % au plus ; comparaison au mm et au centième de % près,
    précision d'affichage, sans tolérance)."""
    R = sc.R
    tris = [i for i in np.where(sc.attr[:, 0] == 0)[0] if sc.classe(i) == "trottoir" and sc.comptes[i] == 3]
    loc = _Locator([sc.P[sc.face(i)][:, 3:5] for i in tris], [sc.P[sc.face(i)][:, 2] for i in tris])
    out = []
    for (a, b, k, l, c, d) in _rampants(R, sc):
        cp = R.coupe(0.5 * (b + c), k)
        bd = cp["bords"][l]
        res = {"limite": l, "abaisse": [_r(b, 3), _r(c, 3)], "rampant_modele_m": _r(b - a, 3), "rampes": []}
        ss = np.arange(a - 1.0, d + 1.0 + 1e-9, 0.02)
        zs = []
        for s in ss:
            T = A1.t_limites(R.profil(R.section(s)), s)
            t = T[l] + bd["h"] * (bd["base"] + 0.10)
            zs.append(loc.z_en(s, t))
        zs = np.array([np.nan if z is None else z for z in zs])
        pen = np.diff(zs) / np.diff(ss)
        actif = np.abs(pen) > 0.003
        i = 0
        while i < len(pen):
            if not actif[i] or not np.isfinite(pen[i]):
                i += 1
                continue
            j = i
            while j + 1 < len(pen) and actif[j + 1] and np.sign(pen[j + 1]) == np.sign(pen[i]):
                j += 1
            lg = float(ss[j + 1] - ss[i])
            # pente : intervalles entièrement dans la rampe (le premier et le dernier contiennent la cassure) ;
            # longueur exacte = dénivelé entre les deux paliers / pente (indépendante du pas d'échantillonnage)
            inter = np.abs(pen[i + 1:j]) if j - i >= 2 else np.abs(pen[i:j + 1])
            pm = float(np.nanmax(inter))
            pmed = float(np.nanmedian(inter))
            za = zs[i - 1] if i >= 1 else zs[i]
            zb = zs[j + 2] if j + 2 < len(zs) else zs[j + 1]
            dh = float(abs(zb - za))
            lx = dh / pmed if pmed > 0 else 0.0
            ok = (round(100 * pm, 2) <= 5.00 and round(lx, 3) >= 2.400) or (round(100 * pm, 2) <= 8.00 and round(lx, 3) >= 1.500)
            res["rampes"].append({"de": _r(ss[i], 3), "a": _r(ss[j + 1], 3), "longueur_echantillonnee_m": _r(lg, 3),
                                  "longueur_m": _r(lx, 4), "pente_max_pct": _r(100 * pm, 3), "denivele_m": _r(dh, 4),
                                  "conforme": ok})
            i = j + 1
        out.append(res)
    n = sum(len(x["rampes"]) for x in out)
    ko = sum(1 for x in out for r in x["rampes"] if not r["conforme"])
    return {"abaisses": len(out), "rampants_mesures": n, "rampants_non_conformes": ko, "detail": out}


# ------------------------------------------------------------------------------------------------ TQ-BOR
def joints(sc: Scene) -> dict:
    ray, ko = 0, 0
    ex = []
    for j in sc.mes["joints"]:
        for r in j["rayons"]:
            ray += 1
            if not r["impact"] or r.get("derriere_m", 1e9) > 0.30:
                ko += 1
                if len(ex) < 5:
                    ex.append([j["id"], r])
    larg = [j["largeur_mm"] for j in sc.mes["joints"]]
    return {"joints": len(sc.mes["joints"]), "rayons": ray, "echecs": ko, "exemples": ex,
            "largeur_joints_mm": stats(larg)}


def caniveaux(sc: Scene) -> dict:
    ec, ko = [], 0
    for c in sc.mes["caniveaux"]:
        if c["z_caniveau_2cm"] is None or c["z_enrobe_1cm"] is None:
            ko += 1
            continue
        arete = c["z_caniveau_2cm"] + 0.10 * 0.02 * (0.235 / 0.235)
        e = arete - c["z_enrobe_1cm"]
        ec.append(abs(e))
        if abs(e) > 0.003:
            ko += 1
    return {"sondes": len(sc.mes["caniveaux"]), "affleurement_abs_m": stats(ec), "hors_3mm": ko}


def elements(sc: Scene) -> dict:
    el = [e for e in sc.elements if e.get("kind") == "element"]
    jt = [e for e in sc.elements if e.get("kind") == "joint"]
    types = Counter((e["famille"], e.get("type")) for e in el)
    coupes_courtes = [e["id"] for e in el if e.get("coupe") and e.get("longueur", 1.0) < 0.20 - 1e-3]
    longs = [e for e in el if e.get("longueur", 0.0) > 1.0 + 1e-3]
    return {"elements": len(el), "joints": len(jt), "types": {f"{a}:{b}": n for (a, b), n in sorted(types.items())},
            "sur_mesure": sum(1 for e in el if e.get("sur_mesure")), "coupes_lt_0_20": len(coupes_courtes),
            "elements_gt_1_00": len(longs)}


def bev(sc: Scene) -> dict:
    """BEV : étendue (s0..s1 de l'abaissé, 0,50 m du nez, profondeur 0,5875 m) et dessus 3 mm au-dessus du trottoir."""
    R = sc.R
    out = []
    ss = np.linspace(0, R.L, int(R.L / 0.02) + 1)
    ref = np.array([R.ref.eval(s)[:3] for s in ss])

    def st(x, y):
        d = (ref[:, 0] - x) ** 2 + (ref[:, 1] - y) ** 2
        i = int(np.argmin(d))
        s = ss[i]
        for _ in range(4):
            x0, y0, th, _ = R.ref.eval(s)
            s += (x - x0) * math.cos(th) + (y - y0) * math.sin(th)
        x0, y0, th, _ = R.ref.eval(s)
        return s, -(x - x0) * math.sin(th) + (y - y0) * math.cos(th)

    attendus = []
    for k in range(len(R.secs)):
        for l, lim in enumerate(R.profil(k)["limites"]):
            for a in (lim.get("bordure") or {}).get("abaisses", []) or []:
                if a.get("bev"):
                    attendus.append((k, l, float(a["s0"]), float(a["s1"])))
    for bid, d in sorted(sc.bev.items()):
        pts = np.array([p for f in d["dalles"] for p in f])
        sts = np.array([st(x, y) for x, y in pts[:, :2]])
        smin, smax = sts[:, 0].min(), sts[:, 0].max()
        tm = float(sts[:, 1].mean())

        def cout(q):
            k, l, s0, s1 = q
            cp = R.coupe(0.5 * (s0 + s1), k)
            bd = cp["bords"].get(l)
            cote = 0.0 if bd is None or bd["h"] * (tm - cp["T"][l]) > 0 else 100.0
            return abs(s0 - smin) + abs(s1 - smax) + cote
        best = min(attendus, key=cout) if attendus else None
        if best is None:
            out.append({"id": bid, "attendu": None})
            continue
        k, l, s0, s1 = best
        cp = R.coupe(0.5 * (s0 + s1), k)
        bd = cp["bords"][l]
        # étendue attendue (RF-MA-BEV-002 : au droit de toute bordure de vue < 0,05 m, jamais au-delà du marquage) :
        # vue VISIBLE = tête − chaussée au droit de la face (fil d'eau + dz avec caniveau ; ralentisseur compris), au
        # pas de 1 mm sur l'abaissé (correction après contrôle : BEV de S10 devant 0,055 m aux bouts du marquage)
        vis_ok = []
        for sv in np.arange(s0, s1 + 1e-9, 0.001):
            c3 = R.coupe(float(sv), k)
            b3 = c3["bords"].get(l)
            if b3 is None:
                continue
            bb = l if b3["h"] > 0 else l - 1
            zb = b3["pied"] + c3["dz"] if b3["wc"] > 0 else c3["a"][bb] + c3["g"][bb] * c3["T"][l] + c3["dz"]
            if b3["tete"] - zb < 0.05 - 1e-9:
                vis_ok.append(float(sv))
        if vis_ok:
            s0, s1 = min(vis_ok), max(vis_ok)
        u = bd["h"] * (sts[:, 1] - cp["T"][l])
        zt = []
        for (s, t), z in zip(sts, pts[:, 2]):
            c2 = R.coupe(s, k)
            zt.append(z - R.z_bande(c2, c2["bords"][l]["bande_haute"], t))
        out.append({"id": bid, "s": [_r(smin, 4), _r(smax, 4)], "s_attendu": [s0, s1],
                    "u_nez_m": [_r(u.min(), 4), _r(u.max(), 4)], "u_attendu_m": [0.5, 0.5 + 0.5875],
                    "dessus_sur_trottoir_mm": [_r(1000 * min(zt), 3), _r(1000 * max(zt), 3)], "plots": d["plots"],
                    "ecart_max_m": _r(max(abs(smin - s0), abs(smax - s1), abs(u.min() - 0.5), abs(u.max() - 1.0875)), 5)})
    return {"bev": len(out), "attendues": len(attendus), "detail": out}


# ------------------------------------------------------------------------------------------------ normales
def normales(sc: Scene, pas_face: int = 5) -> dict:
    """TQ-SOL-008 : normales des faces de bande (z_type 0) contre le gradient analytique du modèle (analytique_L2) :
    dérivée en s du côté de la face (cassures des rampes), en t par le dévers de la bande ; une face sur pas_face."""
    f = sc.l2 / "sol_normales.npy"
    if not f.exists():
        return {"present": False}
    N = np.load(f)
    R = sc.R
    h = 0.005
    ang, n = [], 0
    cache = {}

    def coupe(s, k):
        cle = (round(s, 9), k)
        if cle not in cache:
            cache[cle] = R.coupe(s, k)
        return cache[cle]

    def pos(s, t):
        x, y, th, _ = R.ref.eval(s)
        return np.array([x - t * math.sin(th), y + t * math.cos(th)])

    faces = [i for i in np.where((sc.attr[:, 0] == 0) & (sc.attr[:, 2] >= 0))[0]][::pas_face]
    for i in faces:
        k, b = int(sc.attr[i, 1]), int(sc.attr[i, 2])
        idx = sc.face(i)
        sc_ = float(np.mean(sc.P[idx, 3]))
        for j, v in enumerate(idx):
            s, tt = float(sc.P[v, 3]), float(sc.P[v, 4])
            sa, sb = (s, min(s + h, R.L)) if sc_ >= s else (max(s - h, 0.0), s)
            if sb - sa < 1e-6:
                sa, sb = max(s - h, 0.0), min(s + h, R.L)
            ca, cb = coupe(sa, k), coupe(sb, k)
            dzs = (R.z_bande(cb, b, tt) - R.z_bande(ca, b, tt)) / (sb - sa)
            ps = (pos(sb, tt) - pos(sa, tt)) / (sb - sa)
            pt = (pos(s, tt + h) - pos(s, tt - h)) / (2 * h)
            a = np.cross([ps[0], ps[1], dzs], [pt[0], pt[1], cb["g"][b]])
            a /= np.linalg.norm(a)
            m = N[sc.off[i] + j].astype(np.float64)
            m /= max(np.linalg.norm(m), 1e-12)
            ang.append(math.degrees(math.acos(float(np.clip(np.dot(a, m), -1.0, 1.0)))))
            n += 1
    return {"present": True, "sommets_testes": n, "ecart_angle_deg": stats(ang)}


# ------------------------------------------------------------------------------------------------ végétation
def vegetation(sc: Scene) -> dict:
    """Arbres d'alignement recalculés sur le modèle (objets_le_long des bandes, famille vegetation : mode points ou
    pas depuis le début de l'intervalle, ancrage) contre vegetation.json ; distance de l'axe au bord de la chaussée
    (DEF-030 : ≥ 1,50 m)."""
    R = sc.R
    att = []
    for k, sec in enumerate(R.secs):
        p = R.profil(k)
        s_a, s_b = float(sec["s0"]), float(sec.get("s1", R.L))
        for b, bd in enumerate(p["bandes"]):
            for o in bd.get("objets_le_long", []) or []:
                if o.get("famille") != "vegetation":
                    continue
                if o.get("mode") == "points":
                    ss = [float(x) for x in o["s_points"]]
                else:
                    iv = o.get("intervalle") or {"s0": 0.0, "s1": R.L}
                    pas, ph = float(o["pas_m"]), float(o.get("phase_m", 0.0))
                    ss, m = [], 0
                    while True:
                        x = float(iv["s0"]) + ph + m * pas
                        if x > float(iv["s1"]) + 1e-9 or x > R.L + 1e-9:
                            break
                        ss.append(x)
                        m += 1
                an = o.get("ancrage") or {}
                ref, dec = an.get("reference", "centre"), float(an.get("decalage_m", 0.0))
                for x in ss:
                    if x < s_a - 1e-9 or x > s_b + 1e-9:
                        continue
                    T = R.coupe(x, k)["T"]
                    tt = T[b] + dec if ref == "rive_gauche" else (T[b + 1] + dec if ref == "rive_droite"
                                                                   else 0.5 * (T[b] + T[b + 1]) + dec)
                    att.append((x, tt, k))
    # doublons à une jonction de sections (même arbre porté par deux sections contiguës)
    uniq = []
    for a in sorted(att):
        if not uniq or math.hypot(a[0] - uniq[-1][0], a[1] - uniq[-1][1]) > 1e-6:
            uniq.append(a)
    fab = [(float(v["s"]), float(v["t"])) for v in sc.veg]
    ecarts = []
    for (s, tt, k) in uniq:
        d = min((math.hypot(s - a, tt - b) for a, b in fab), default=1e9)
        ecarts.append(d)
    # axe de l'arbre au bord de la chaussée (limite d'une bande basse la plus proche)
    dist = []
    for (s, tt, k) in uniq:
        c = R.coupe(s, k)
        T, cls = c["T"], c["cls"]
        bords = [T[l] for l in range(len(T)) if (l > 0 and cls[l - 1] == 0) or (l < len(cls) and cls[l] == 0)]
        if bords:
            dist.append(min(abs(tt - x) for x in bords))
    return {"arbres_fabriques": len(fab), "arbres_attendus": len(uniq),
            "position_ecart_max_m": _r(max(ecarts), 6) if ecarts else 0.0,
            "axe_bord_chaussee_min_m": _r(min(dist), 4) if dist else None}


def heightfield(sc: Scene) -> dict:
    """HeightField de nivellement (sortie 2 de rg::nivellement) : mesures de fabrication (pj_niv_z contre le sol) et
    descripteur (heightfield.json)."""
    h = sc.mes.get("heightfield") or {}
    f = sc.l2 / "heightfield.json"
    d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    c = d.get("couches", {})
    return {"present": bool(d), "couches": sorted(c), "resolution": c.get("height", {}).get("resolution"),
            "pas_m": d.get("descripteur", {}).get("niv_pas"), "mode": sorted({v.get("mode") for v in c.values()}),
            **h}


# ------------------------------------------------------------------------------------------------ scène
def controler_scene(dossier: Path) -> dict:
    sc = Scene(dossier)
    emp = empreintes(sc)
    res = {"scene": sc.nom, "routes": len(sc.routes), "longueur_m": _r(sc.R.L, 4)}
    res["etancheite"] = etancheite(sc)
    res["marches"] = marches_visibles(sc, emp)
    res["z_sol"] = z_sol(sc)
    res["ruptures"] = ruptures(sc)
    res["bordures"] = bordures(sc, emprises_autres(sc))
    res["trottoirs"] = trottoirs(sc)
    res["rampants"] = rampants(sc)
    res["joints"] = joints(sc)
    res["caniveaux"] = caniveaux(sc)
    res["elements"] = elements(sc)
    res["bev"] = bev(sc)
    res["vegetation"] = vegetation(sc)
    res["heightfield"] = heightfield(sc)
    res["normales"] = normales(sc)
    return res


K_RET = "retrait_trottoir_ecart_m (mesuré − attendu, TQ-SOL-013 (6) ± 2 mm)"
K_PL = "retrait_plantee_m (TQ-SOL-013 (7) : 0,03 à 0,05)"


def bilan(liste: list) -> dict:
    def mx(ch):
        v = [ch(r) for r in liste]
        v = [x for x in v if x is not None]
        return max(v) if v else None
    return {
        "scenes": len(liste),
        "aretes_hors_contour": sum(r["etancheite"]["aretes_de_bord_hors_contour"] for r in liste),
        "non_varietes": sum(r["etancheite"]["non_varietes"] for r in liste),
        "mal_orientees": sum(r["etancheite"]["aretes_mal_orientees"] for r in liste),
        "degenerees": sum(r["etancheite"]["faces_degenerees_1e-6"] for r in liste),
        "doublons": sum(r["etancheite"]["faces_en_double"] for r in liste),
        "inversees": sum(r["etancheite"]["faces_inversees_st"] for r in liste),
        "ecart_aire_st_max_m2": mx(lambda r: abs(r["etancheite"]["ecart_aire_st_m2"])),
        "ecart_aire_st_relatif_max": mx(lambda r: abs(r["etancheite"][
            "ecart_aire_st_relatif (contour intégré au pas de 5 cm, coordonnées float32)"])),
        "recouvrement_st_max_m2": mx(lambda r: abs(r["etancheite"][
            "recouvrement_st_m2 (somme des aires − aire de l'union, TQ-SOL-001)"])),
        "marche_visible_max_m": mx(lambda r: r["marches"]["marche_visible_max_m"]),
        "murs_hors_elements": sum(r["marches"]["murs_hors_elements"] for r in liste),
        "z_sol_ecart_max_m": mx(lambda r: r["z_sol"]["ecart_max_m"]),
        "ruptures_traversees": sum(r["ruptures"]["faces_traversant_longitudinale"] + r["ruptures"]["faces_traversant_transversale"]
                                   for r in liste),
        "vue_ecart_max_m": mx(lambda r: r["bordures"]["vue_ecart_abs"].get("max")),
        "vue_hors_5mm": sum(r["bordures"]["vue_hors_5mm"] for r in liste),
        "sondes_sans_impact": sum(r["bordures"]["sondes_sans_impact"] for r in liste),
        "devers_trottoir_max_pct": mx(lambda r: r["trottoirs"]["devers_abs_pct"].get("max")),
        "pente_trottoir_max_hors_rampants_pct": mx(lambda r: r["trottoirs"]["pente_hors_rampants_abs_pct"].get("max")),
        "rampants": sum(r["rampants"]["rampants_mesures"] for r in liste),
        "rampants_non_conformes": sum(r["rampants"]["rampants_non_conformes"] for r in liste),
        "joints_rayons": sum(r["joints"]["rayons"] for r in liste),
        "joints_echecs": sum(r["joints"]["echecs"] for r in liste),
        "caniveaux_hors_3mm": sum(r["caniveaux"]["hors_3mm"] for r in liste),
        "sol_sous_element_absent": sum(r["bordures"]["sol_sous_element_absent (TQ-BOR-007)"] for r in liste),
        "part_angle_min_ge_20_min": mx(lambda r: -r["etancheite"]["part_angle_min_ge_20"]),
        "retrait_trottoir_ecart_max_m": mx(lambda r: max(abs(r["bordures"][K_RET].get("min", 0.0)),
                                                         abs(r["bordures"][K_RET].get("max", 0.0)))
                                           if r["bordures"][K_RET].get("n") else None),
        "retrait_plantee_min_m": min((r["bordures"][K_PL]["min"] for r in liste if r["bordures"][K_PL].get("n")), default=None),
        "retrait_plantee_max_m": mx(lambda r: r["bordures"][K_PL].get("max")),
        "sondes_ecartees_angles": sum(r["bordures"].get("sondes_ecartees_angles", 0) for r in liste),
        "sondes_hors_emprise_bout": sum(r["bordures"].get("sondes_hors_emprise_bout", 0) for r in liste),
        "coupes_lt_0_20": sum(r["elements"]["coupes_lt_0_20"] for r in liste),
        "elements": sum(r["elements"]["elements"] for r in liste),
        "joints": sum(r["joints"]["joints"] for r in liste),
        "bev": sum(r["bev"]["bev"] for r in liste),
        "bev_attendues": sum(r["bev"]["attendues"] for r in liste),
        "bev_ecart_max_m": mx(lambda r: max([b["ecart_max_m"] for b in r["bev"]["detail"]] or [0.0])),
        "arbres": sum(r["vegetation"]["arbres_fabriques"] for r in liste),
        "arbres_attendus": sum(r["vegetation"]["arbres_attendus"] for r in liste),
        "arbres_ecart_max_m": mx(lambda r: r["vegetation"]["position_ecart_max_m"] if r["vegetation"]["arbres_attendus"]
                                 else None),
        "arbres_axe_bord_chaussee_min_m": min((r["vegetation"]["axe_bord_chaussee_min_m"] for r in liste
                                               if r["vegetation"]["axe_bord_chaussee_min_m"] is not None), default=None),
        "normales_sommets_testes": sum(r["normales"].get("sommets_testes", 0) for r in liste),
        "normales_ecart_max_deg": mx(lambda r: r["normales"].get("ecart_angle_deg", {}).get("max")),
        "heightfield_presents": sum(1 for r in liste if r["heightfield"]["present"]),
        "heightfield_ecart_max_m": mx(lambda r: r["heightfield"].get("ecart_max_m")),
        "heightfield_ecart_p99_max_m": mx(lambda r: r["heightfield"].get("ecart_p99_m")),
        "heightfield_absents": sum(r["heightfield"].get("absents", 0) for r in liste),
        "heightfield_points_testes": sum(r["heightfield"].get("points_testes", 0) for r in liste),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    dossiers = [Path(x) for x in a.scenes] or sorted(p.parent.parent for p in SORTIE.glob("*/l2/manifest_l2.json"))
    out = []
    for d in dossiers:
        r = controler_scene(d)
        out.append(r)
        b = r["bordures"]
        print(f"{r['scene']} : bord hors contour {r['etancheite']['aretes_de_bord_hors_contour']}, "
              f"non-variétés {r['etancheite']['non_varietes']}, Z max {r['z_sol']['ecart_max_m']}, "
              f"ruptures {r['ruptures']['faces_traversant_longitudinale']}+{r['ruptures']['faces_traversant_transversale']}, "
              f"vue max {b['vue_ecart_abs'].get('max')} (hors 5 mm {b['vue_hors_5mm']}), dévers max "
              f"{r['trottoirs']['devers_abs_pct'].get('max')} %, pente max {r['trottoirs']['pente_hors_rampants_abs_pct'].get('max')} %, "
              f"rampants {r['rampants']['rampants_mesures']} ({r['rampants']['rampants_non_conformes']} KO), "
              f"joints {r['joints']['echecs']}/{r['joints']['rayons']} KO, marches visibles {r['marches']['murs_hors_elements']}")
    res = {"scenes": out, "bilan": bilan(out)}
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res["bilan"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
