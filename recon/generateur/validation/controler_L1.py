# -*- coding: utf-8 -*-
"""Contrôles indépendants des courbes de contrôle du lot L1 (PLAN_GENERATEUR § 3, critères L1).

    python recon/generateur/validation/controler_L1.py [DOSSIER_SCENE ...] [--json SORTIE.json]

Lit `<scene>/l1/courbes_controle.json` (écrit par fabriquer_generateur.py, HDA rg::*) et le modèle qu'il cite, puis
recalcule tout en double précision avec `analytique_L1.py` (aucun code commun avec le VEX) :

1. flèche : pour chaque corde de la référence et de chaque limite, écart maximal entre la courbe analytique et la
   corde (33 points par corde, puis raffinement) — seuil 0,5 mm ;
2. écart au milieu des cordes : distance du milieu de chaque corde à la courbe analytique décalée (droite, arc,
   clothoïde, séparément) — seuil 1 mm ; écart des sommets à leur position analytique ;
3. largeurs : aucune bande de largeur négative ; largeur nulle seulement à une extrémité de biseau (bande qui naît ou
   disparaît à la jonction) ;
4. chevauchement : réunion des rubans (shapely) = somme des aires ; aucun repli (1 − t κ > 0) ;
5. sections contiguës de 0 à L (modèle et sorties) ;
6. continuité aux jonctions de sections : bords d'une même bande ≤ 1 mm ; bande qui naît ou disparaît : largeur
   ≤ 1 mm ; jonctions « transition_entree : instantanee » déclarées par le modèle comptées à part ;
7. loi verticale (plateaux, dos-d'âne) : dz exporté contre dz analytique, flèche du profil en long ;
8. sommets obligatoires (raccords, sections, lois, évènements de limite, ralentisseurs) présents ;
9. aires des rubans (Houdini, quadrilatères) contre l'aire analytique ∫ [w − κ (t_g² − t_d²)/2] ds (information).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy import integrate
from shapely.geometry import Polygon
from shapely.ops import unary_union

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(ICI))
import analytique_L1 as A  # noqa: E402

SEUIL_FLECHE = 0.0005
SEUIL_MILIEU = 0.001
SEUIL_CONTINUITE = 0.001
SEUIL_DZ = 0.001
N_CORDE = 32
# abscisses et positions exportées par Houdini : flottants 32 bits (résolution ≤ 1,5e-5 m sous 256 m) ; les
# comparaisons d'abscisses entre sorties et modèle se font donc à 2e-5 m (0,02 mm, 50 fois sous les seuils du lot)
TOL_S = 2e-5


# ------------------------------------------------------------------------------------------------ référence vectorisée
class RefVect:
    """Ligne de référence évaluée en tableau : droites et arcs en forme fermée ; clothoïdes par table à 0,02 m
    (incréments par quadrature adaptative scipy.integrate.quad) et interpolation d'Hermite cubique avec la tangente
    exacte (erreur < 1e-10 m)."""

    def __init__(self, route: dict, origine):
        self.R = A.Reference(route, origine)
        self.poly = self.R.poly is not None
        self.L = self.R.L
        self.L_modele = float(route["ligne_reference"].get("longueur_m") or self.R.L)
        if self.poly:
            return
        self.p = self.R.prims
        self.s0 = np.array([p.s0 for p in self.p])
        self.tab = {}
        for i, p in enumerate(self.p):
            if p.type != "clothoide":
                continue
            n = max(2, int(math.ceil(p.L / 0.02)))
            u = np.linspace(0.0, p.L, n + 1)
            x = np.empty(n + 1)
            y = np.empty(n + 1)
            x[0], y[0] = p.x0, p.y0
            for j in range(n):
                dx = integrate.quad(lambda v: math.cos(p.theta(v)), u[j], u[j + 1], epsabs=1e-15, epsrel=1e-14)[0]
                dy = integrate.quad(lambda v: math.sin(p.theta(v)), u[j], u[j + 1], epsabs=1e-15, epsrel=1e-14)[0]
                x[j + 1], y[j + 1] = x[j] + dx, y[j] + dy
            self.tab[i] = (u, x, y)

    def eval(self, s):
        s = np.atleast_1d(np.asarray(s, float))
        if self.poly:
            out = [self.R.eval(float(v)) for v in s]
            return tuple(np.array(c) for c in zip(*out))
        g = np.clip(np.searchsorted(self.s0, s + 1e-9, side="right") - 1, 0, len(self.p) - 1)
        x = np.empty_like(s)
        y = np.empty_like(s)
        th = np.empty_like(s)
        k = np.empty_like(s)
        for i, p in enumerate(self.p):
            m = g == i
            if not m.any():
                continue
            u = np.clip(s[m] - p.s0, 0.0, p.L)
            th[m] = p.cap + p.k0 * u + 0.5 * p.c * u * u
            k[m] = p.k0 + p.c * u
            if p.type == "droite":
                x[m] = p.x0 + u * math.cos(p.cap)
                y[m] = p.y0 + u * math.sin(p.cap)
            elif p.type == "arc":
                x[m] = p.x0 + (np.sin(p.cap + p.k0 * u) - math.sin(p.cap)) / p.k0
                y[m] = p.y0 - (np.cos(p.cap + p.k0 * u) - math.cos(p.cap)) / p.k0
            else:
                tu, tx, ty = self.tab[i]
                j = np.clip(np.searchsorted(tu, u, side="right") - 1, 0, len(tu) - 2)
                h = tu[j + 1] - tu[j]
                a = (u - tu[j]) / h
                tha, thb = p.theta(tu[j]), p.theta(tu[j + 1])
                h00, h10, h01, h11 = 2 * a ** 3 - 3 * a ** 2 + 1, a ** 3 - 2 * a ** 2 + a, -2 * a ** 3 + 3 * a ** 2, a ** 3 - a ** 2
                x[m] = h00 * tx[j] + h10 * h * np.cos(tha) + h01 * tx[j + 1] + h11 * h * np.cos(thb)
                y[m] = h00 * ty[j] + h10 * h * np.sin(tha) + h01 * ty[j + 1] + h11 * h * np.sin(thb)
        return x, y, th, k

    def type_a(self, s):
        if self.poly:
            return "polyligne"
        g = int(np.clip(np.searchsorted(self.s0, s + 1e-9, side="right") - 1, 0, len(self.p) - 1))
        return self.p[g].type


# ------------------------------------------------------------------------------------------------ lois vectorisées
def loi_v(v, s):
    s = np.asarray(s, float)
    if isinstance(v, (int, float)):
        return np.full_like(s, float(v))
    if v["type"] == "points":
        S = np.array([p[0] for p in v["points"]], float)
        V = np.array([p[1] for p in v["points"]], float)
        if v.get("interpolation", "lineaire") == "palier":
            i = np.clip(np.searchsorted(S, s, side="right") - 1, 0, len(S) - 1)
            return V[i]
        return np.interp(s, S, V)
    return np.array([A.loi(v, float(x)) for x in s])


def t_limites_v(profil, s):
    """Tableau (n + 1, len(s)) des t des limites."""
    s = np.asarray(s, float)
    w = [loi_v(b["largeur"], s) for b in profil["bandes"]]
    r = int(profil["reference"]["limite"])
    t = [None] * (len(w) + 1)
    t[r] = np.full_like(s, -float(profil["reference"].get("decalage_m", 0.0)))
    for i in range(r - 1, -1, -1):
        t[i] = t[i + 1] + w[i]
    for i in range(r + 1, len(w) + 1):
        t[i] = t[i - 1] - w[i - 1]
    return np.array(t)


def profil_effectif(m, route, k):
    sec = route["sections"][k]
    P = {p["id"]: p for p in m["profils"]}
    base = sec["profil"] if isinstance(sec["profil"], dict) else P[sec["profil"]]
    if sec.get("surcharges"):
        base = copy.deepcopy(base)
        for chemin, v in sec["surcharges"].items():
            mt = re.fullmatch(r"(bandes|limites)\[(\d+)\]\.([a-z_]+)", chemin)
            base[mt.group(1)][int(mt.group(2))][mt.group(3)] = v
    return base


# ------------------------------------------------------------------------------------------------ mesures de cordes
def mesurer_courbe(ref: RefVect, tfun, S, X, Y):
    """Courbe décalée t(s) (tfun : s -> t) échantillonnée en (S, X, Y). Renvoie, par type de primitive :
    flèche max, écart max du milieu des cordes, écart max des sommets."""
    S, X, Y = (np.asarray(v, float) for v in (S, X, Y))
    res = {}

    def pos(s):
        x, y, th, _ = ref.eval(s)
        t = tfun(s)
        return np.array([x - t * np.sin(th), y + t * np.cos(th)])

    pv = pos(S)
    ecart_sommets = np.hypot(pv[0] - X, pv[1] - Y)
    for j in range(len(S) - 1):
        a, b = S[j], S[j + 1]
        if b - a < 1e-9:
            continue
        typ = ref.type_a(0.5 * (a + b))
        uu = np.linspace(a, b, N_CORDE + 1)
        q = pos(uu)
        A0 = np.array([X[j], Y[j]])
        B0 = np.array([X[j + 1], Y[j + 1]])
        ab = B0 - A0
        nab = float(ab @ ab)
        w = np.clip(((q.T - A0) @ ab) / max(nab, 1e-24), 0.0, 1.0)
        proj = A0 + np.outer(w, ab)
        d = np.hypot(*(q.T - proj).T)
        k = int(np.argmax(d))
        # raffinement autour du maximum
        lo, hi = uu[max(k - 1, 0)], uu[min(k + 1, N_CORDE)]
        uu2 = np.linspace(lo, hi, 33)
        q2 = pos(uu2)
        w2 = np.clip(((q2.T - A0) @ ab) / max(nab, 1e-24), 0.0, 1.0)
        d2 = np.hypot(*(q2.T - (A0 + np.outer(w2, ab))).T)
        fl = max(float(d.max()), float(d2.max()))
        # milieu de la corde -> courbe analytique
        M = 0.5 * (A0 + B0)
        dm = np.hypot(q[0] - M[0], q[1] - M[1])
        km = int(np.argmin(dm))
        lo, hi = uu[max(km - 1, 0)], uu[min(km + 1, N_CORDE)]
        for _ in range(3):
            uu3 = np.linspace(lo, hi, 33)
            q3 = pos(uu3)
            d3 = np.hypot(q3[0] - M[0], q3[1] - M[1])
            k3 = int(np.argmin(d3))
            lo, hi = uu3[max(k3 - 1, 0)], uu3[min(k3 + 1, 32)]
        mil = float(min(dm.min(), d3.min()))
        r = res.setdefault(typ, {"cordes": 0, "fleche_max_m": 0.0, "milieu_max_m": 0.0, "sommet_max_m": 0.0,
                                 "pire": None})
        r["cordes"] += 1
        if fl > r["fleche_max_m"]:
            r["pire"] = {"s0": round(float(a), 4), "s1": round(float(b), 4)}
        r["fleche_max_m"] = max(r["fleche_max_m"], fl)
        r["milieu_max_m"] = max(r["milieu_max_m"], mil)
        r["sommet_max_m"] = max(r["sommet_max_m"], float(ecart_sommets[j]), float(ecart_sommets[j + 1]))
    return res


def ecart_polyligne(rr, ref, tfun, S, X, Y, cle="polyligne_ecart_max_m"):
    """Route sans géométrie régulière (polyligne du modèle) : la limite analytique est la polyligne décalée en onglet
    (sommets : intersections des décalés des segments adjacents). L'abscisse n'en est pas un paramètre continu (le
    décalé saute aux sommets) : on mesure la distance de Hausdorff entre la polyligne exportée et la polyligne
    analytique (sommets du modèle décalés à leur t)."""
    from shapely.geometry import LineString
    e = ref.R.poly_s[-1] / ref.L_modele
    sv = ref.R.poly_s / e
    ana = [ref.R.offset_polyligne(float(v) * e, float(tfun(np.array([v]))[0])) for v in sv]
    la, lb = LineString(ana), LineString(list(zip(X, Y)))
    rr[cle] = max(rr[cle], float(la.hausdorff_distance(lb)))


def inversions(X, Y, S, refc):
    """Nombre de cordes d'une limite dont le sens s'oppose à celui de la référence (pli d'un décalé intérieur)."""
    X, Y = np.asarray(X), np.asarray(Y)
    Sr = np.asarray(refc["s"])
    cap = np.asarray(refc["cap_rad"])
    sm = 0.5 * (np.asarray(S)[1:] + np.asarray(S)[:-1])
    j = np.clip(np.searchsorted(Sr, sm) - 1, 0, len(Sr) - 1)
    tx, ty = np.cos(cap[j]), np.sin(cap[j])
    d = np.diff(X) * tx + np.diff(Y) * ty
    lg = np.hypot(np.diff(X), np.diff(Y))
    return int(np.sum((d <= 0.0) & (lg > 1e-9)))


def fusion(dst, src):
    for typ, r in src.items():
        d = dst.setdefault(typ, {"cordes": 0, "fleche_max_m": 0.0, "milieu_max_m": 0.0, "sommet_max_m": 0.0})
        d["cordes"] += r["cordes"]
        for k in ("fleche_max_m", "milieu_max_m", "sommet_max_m"):
            d[k] = max(d[k], r[k])


# ------------------------------------------------------------------------------------------------ contrôle d'une scène
def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def controler_scene(dossier: Path) -> dict:
    c = json.loads((dossier / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    fm = DEPOT / c["modele"]["fichier"]
    m = json.loads(fm.read_text(encoding="utf-8"))
    o = m["repere"]["origine_l93"]
    rampe = float(c["parametres"]["rampe_plateau_pct"])
    objets = m.get("objets", [])
    rr = {"scene": c["scene"], "modele_sha256_ok": sha256(fm) == c["modele"]["sha256"], "routes": [],
          "par_type": {}, "reference_par_type": {}, "largeurs_negatives": 0, "largeurs_nulles_hors_biseau": 0,
          "extremites_de_biseau": 0, "replis": 0, "chevauchement_m2": 0.0, "rubans_invalides": 0,
          "sections_contigues": True, "jonctions": [], "dz_ecart_max_m": 0.0, "dz_fleche_max_m": 0.0,
          "sommets_obligatoires_manquants": [], "aire_ecart_rel_max": 0.0, "quads_mal_orientes": 0,
          "extremites_ok": True, "noeuds_ok": True, "raccord_max_m": 0.0, "raccord_cap_max_deg": 0.0,
          "ecart_longueur_primitives_m": 0.0, "inversions": 0, "polyligne_ecart_max_m": 0.0,
          "reference_polyligne_ecart_max_m": 0.0}
    routes_m = {r["id"]: r for r in m["routes"]}
    for rc in c["routes"]:
        route = routes_m[rc["id"]]
        ref = RefVect(route, o)
        poly = ref.poly
        L = float(route["ligne_reference"].get("longueur_m") or ref.L)
        rinfo = {"id": rc["id"], "longueur_m": L, "sections": len(rc["sections"]), "echantillons": len(rc["reference"]["s"])}
        # raccords des primitives du modèle : fin de la primitive i (calculée sur elle-même) contre départ de i + 1
        if not poly:
            for pa, pb in zip(ref.p, ref.p[1:]):
                xa, ya = pa.point(pa.L)
                rr["raccord_max_m"] = max(rr["raccord_max_m"], math.hypot(xa - pb.x0, ya - pb.y0))
                d = (pa.theta(pa.L) - pb.cap + math.pi) % (2 * math.pi) - math.pi
                rr["raccord_cap_max_deg"] = max(rr["raccord_cap_max_deg"], abs(math.degrees(d)))
        # référence
        Sr = np.array(rc["reference"]["s"])
        if poly:
            ecart_polyligne(rr, ref, lambda s: np.zeros_like(np.asarray(s, float)), Sr, rc["reference"]["x"],
                            rc["reference"]["y"], cle="reference_polyligne_ecart_max_m")
        else:
            fusion(rr["reference_par_type"], mesurer_courbe(ref, lambda s: np.zeros_like(np.asarray(s, float)), Sr,
                                                             rc["reference"]["x"], rc["reference"]["y"]))
        # sommets obligatoires (calculés ici depuis le modèle)
        obl = {0.0, L}
        # raccords intérieurs des primitives (la fin de la dernière primitive n'est pas un sommet : la route finit à
        # longueur_m, arrondie à 0,1 mm par le compilateur ; l'écart est rapporté à part)
        obl |= set(ref.R.bornes_primitives()[1:-1]) if not poly else set()
        if not poly:
            rr["ecart_longueur_primitives_m"] = max(rr["ecart_longueur_primitives_m"],
                                                    abs(L - (ref.p[-1].s0 + ref.p[-1].L)))
        for k, sec in enumerate(route["sections"]):
            obl |= {float(sec["s0"]), float(sec["s1"])}
            p = profil_effectif(m, route, k)
            for b in p["bandes"]:
                obl |= {x for x in A.breakpoints_loi(b["largeur"]) if sec["s0"] < x < sec["s1"]}
            for lim in p["limites"]:
                ev = []
                for ab in (lim.get("bordure") or {}).get("abaisses", []) or []:
                    ev += [ab["s0"], ab["s1"]]
                for mq in lim.get("marquages", []) or []:
                    if mq.get("intervalle"):
                        ev += [mq["intervalle"]["s0"], mq["intervalle"]["s1"]]
                    for it in mq.get("interruptions", []) or []:
                        ev += [it["s0"], it["s1"]]
                obl |= {float(x) for x in ev if sec["s0"] < x < sec["s1"]}
        obl |= {x for x in A.bornes_verticales(objets, rc["id"], rampe) if 0 < x < L}
        manq = [round(x, 4) for x in sorted(obl) if np.min(np.abs(Sr - x)) > TOL_S]
        rr["sommets_obligatoires_manquants"] += [f"{rc['id']}@{x}" for x in manq]
        # sections contiguës (modèle et sorties)
        secs_m = route["sections"]
        ok = abs(secs_m[0]["s0"]) <= 1e-6 and abs(secs_m[-1]["s1"] - L) <= 1e-6 and all(
            abs(a["s1"] - b["s0"]) <= 1e-6 for a, b in zip(secs_m, secs_m[1:]))
        ok = ok and len(rc["sections"]) == len(secs_m) and all(
            abs(sc["s"][0] - sm["s0"]) <= TOL_S and abs(sc["s"][-1] - sm["s1"]) <= TOL_S for sc, sm in zip(rc["sections"], secs_m))
        rinfo["sections_contigues"] = ok
        rr["sections_contigues"] &= ok
        # sections : limites, largeurs, rubans
        polys = []
        aires = []
        prec = None
        for k, (sc, sm) in enumerate(zip(rc["sections"], secs_m)):
            p = profil_effectif(m, route, k)
            S = np.array(sc["s"])
            T = t_limites_v(p, S)
            nb = len(p["bandes"])
            ids = [b["id"] for b in p["bandes"]]
            # écarts au modèle analytique (chaque limite)
            for l, lim in enumerate(sc["limites"]):
                tf = (lambda pp, ll: (lambda s: t_limites_v(pp, s)[ll]))(p, l)
                if poly:
                    ecart_polyligne(rr, ref, tf, S, lim["x"], lim["y"])
                else:
                    fusion(rr["par_type"], mesurer_courbe(ref, tf, S, lim["x"], lim["y"]))
                    # repli : 1 − t κ > 0 (analytique)
                    _, _, _, kk = ref.eval(S)
                    rr["replis"] += int(np.sum(1.0 - T[l] * kk <= 0.0))
                # inversion de sens d'une limite (sorties) : corde opposée à la tangente de la référence
                rr["inversions"] += inversions(lim["x"], lim["y"], S, rc["reference"])
            # largeurs (sorties Houdini)
            Th = np.array([lim["t"] for lim in sc["limites"]])
            ids_prec = prec["ids"] if prec else []
            ids_suiv = [b["id"] for b in profil_effectif(m, route, k + 1)["bandes"]] if k + 1 < len(secs_m) else []
            for b in range(nb):
                w = Th[b] - Th[b + 1]
                rr["largeurs_negatives"] += int(np.sum(w < -1e-9))
                nulles = np.where(np.abs(w) <= 1e-6)[0]
                for q in nulles:
                    if (q == 0 and ids[b] not in ids_prec and k > 0) or (q == len(S) - 1 and ids[b] not in ids_suiv
                                                                            and k + 1 < len(secs_m)):
                        rr["extremites_de_biseau"] += 1
                    else:
                        rr["largeurs_nulles_hors_biseau"] += 1
                xl, yl = np.array(sc["limites"][b]["x"]), np.array(sc["limites"][b]["y"])
                xr, yr = np.array(sc["limites"][b + 1]["x"]), np.array(sc["limites"][b + 1]["y"])
                ring = list(zip(xl, yl)) + list(zip(xr[::-1], yr[::-1]))
                pg = Polygon(ring)
                if not pg.is_valid:
                    pg2 = pg.buffer(0)
                    if abs(pg2.area - abs(Polygon(ring).area)) > 1e-6:
                        rr["rubans_invalides"] += 1
                    pg = pg2
                polys.append(pg)
                # aire analytique ∫ [w − κ (tg² − td²)/2] ds
                ss = np.linspace(S[0], S[-1], max(200, 20 * len(S)))
                tt = t_limites_v(p, ss)
                kk = ref.eval(ss)[3] if not poly else np.zeros_like(ss)
                f = (tt[b] - tt[b + 1]) - kk * (tt[b] ** 2 - tt[b + 1] ** 2) / 2.0
                aire_a = float(integrate.simpson(f, x=ss))
                bh = next((x for x in sc["bandes"] if x["rang"] == b), None)
                if bh is not None:
                    rr["quads_mal_orientes"] += bh["quads_normale_y_negative"]
                    if aire_a > 1e-6:
                        rr["aire_ecart_rel_max"] = max(rr["aire_ecart_rel_max"], abs(bh["aire_m2"] - aire_a) / aire_a)
            # continuité à la jonction avec la section précédente (coordonnées exportées)
            if prec is not None:
                ec, det = 0.0, ""
                pts0 = [(sc["limites"][l]["x"][0], sc["limites"][l]["y"][0]) for l in range(nb + 1)]
                for b in range(nb):
                    if ids[b] in prec["ids"]:
                        i = prec["ids"].index(ids[b])
                        e = max(math.dist(prec["fin"][i], pts0[b]), math.dist(prec["fin"][i + 1], pts0[b + 1]))
                    else:
                        e = math.dist(pts0[b], pts0[b + 1])
                    if e > ec:
                        ec, det = e, ids[b]
                for i, bid in enumerate(prec["ids"]):
                    if bid not in ids:
                        e = math.dist(prec["fin"][i], prec["fin"][i + 1])
                        if e > ec:
                            ec, det = e, bid
                inst = (sm.get("transition_entree") or {}).get("type") == "instantanee"
                rr["jonctions"].append({"route": rc["id"], "s": sm["s0"], "ecart_m": ec, "bande": det, "instantanee": inst})
            prec = {"ids": ids, "fin": [(lim["x"][-1], lim["y"][-1]) for lim in sc["limites"]]}
        u = unary_union(polys)
        chev = max(0.0, sum(pg.area for pg in polys) - u.area)
        rr["chevauchement_m2"] = max(rr["chevauchement_m2"], chev)
        rinfo["chevauchement_m2"] = chev
        # loi verticale
        pl = rc["profil_long"]
        Sp = np.array(pl["s"])
        dz_a = np.array([A.dz_chaussee(objets, rc["id"], float(x), rampe) for x in Sp])
        rr["dz_ecart_max_m"] = max(rr["dz_ecart_max_m"], float(np.max(np.abs(dz_a - np.array(pl["dz"])))))
        for j in range(len(Sp) - 1):
            if Sp[j + 1] - Sp[j] < 1e-9:
                continue
            uu = np.linspace(Sp[j], Sp[j + 1], 17)
            za = np.array([A.dz_chaussee(objets, rc["id"], float(x), rampe) for x in uu])
            zl = np.interp(uu, [Sp[j], Sp[j + 1]], [pl["dz"][j], pl["dz"][j + 1]])
            rr["dz_fleche_max_m"] = max(rr["dz_fleche_max_m"], float(np.max(np.abs(za - zl))))
        # extrémités : coupe en s = 0 et s = L = points des limites de la première / dernière section
        e0 = rc["extremites"].get("debut")
        e1 = rc["extremites"].get("fin")
        s0, s1 = rc["sections"][0], rc["sections"][-1]
        ok_e = e0 is not None and e1 is not None and \
            all(abs(e0["x"][l] - s0["limites"][l]["x"][0]) < 1e-9 and abs(e0["y"][l] - s0["limites"][l]["y"][0]) < 1e-9
                for l in range(len(s0["limites"]))) and \
            all(abs(e1["x"][l] - s1["limites"][l]["x"][-1]) < 1e-9 and abs(e1["y"][l] - s1["limites"][l]["y"][-1]) < 1e-9
                for l in range(len(s1["limites"])))
        rr["extremites_ok"] &= bool(ok_e)
        rr["routes"].append(rinfo)
    # nœuds : branches triées, valence = nombre d'extrémités de routes au nœud
    for n in c["noeuds"]:
        attendu = sum((r["noeud_debut"] == n["id"]) + (r["noeud_fin"] == n["id"]) for r in m["routes"])
        if n["valence"] != attendu or n["azimuts_deg"] != sorted(n["azimuts_deg"]):
            rr["noeuds_ok"] = False
    return rr


def bilan(scenes: list[dict]) -> dict:
    out = {"scenes": len(scenes), "par_type": {}, "reference_par_type": {}}
    for s in scenes:
        fusion(out["par_type"], s["par_type"])
        fusion(out["reference_par_type"], s["reference_par_type"])
    for k in ("largeurs_negatives", "largeurs_nulles_hors_biseau", "extremites_de_biseau", "replis", "rubans_invalides",
              "quads_mal_orientes", "inversions"):
        out[k] = sum(s[k] for s in scenes)
    out["chevauchement_max_m2"] = max(s["chevauchement_m2"] for s in scenes)
    out["sections_contigues"] = sum(1 for s in scenes if s["sections_contigues"])
    js = [j for s in scenes for j in s["jonctions"]]
    out["jonctions"] = len(js)
    out["jonctions_continues"] = [j for j in js if not j["instantanee"]]
    out["jonctions_instantanees"] = [j for j in js if j["instantanee"]]
    out["jonction_ecart_max_m"] = max([j["ecart_m"] for j in out["jonctions_continues"]] or [0.0])
    out["dz_ecart_max_m"] = max(s["dz_ecart_max_m"] for s in scenes)
    out["dz_fleche_max_m"] = max(s["dz_fleche_max_m"] for s in scenes)
    out["sommets_obligatoires_manquants"] = sum(len(s["sommets_obligatoires_manquants"]) for s in scenes)
    out["aire_ecart_rel_max"] = max(s["aire_ecart_rel_max"] for s in scenes)
    out["raccord_max_m"] = max(s["raccord_max_m"] for s in scenes)
    out["raccord_cap_max_deg"] = max(s["raccord_cap_max_deg"] for s in scenes)
    out["ecart_longueur_primitives_max_m"] = max(s["ecart_longueur_primitives_m"] for s in scenes)
    out["polyligne_ecart_max_m"] = max(s["polyligne_ecart_max_m"] for s in scenes)
    out["reference_polyligne_ecart_max_m"] = max(s["reference_polyligne_ecart_max_m"] for s in scenes)
    out["modeles_sha_ok"] = sum(1 for s in scenes if s["modele_sha256_ok"])
    out["extremites_ok"] = sum(1 for s in scenes if s["extremites_ok"])
    out["noeuds_ok"] = sum(1 for s in scenes if s["noeuds_ok"])
    return out


def arrondir(v):
    if isinstance(v, float):
        return float(f"{v:.6g}")
    if isinstance(v, dict):
        return {k: arrondir(x) for k, x in v.items()}
    if isinstance(v, list):
        return [arrondir(x) for x in v]
    return v


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("dossiers", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    dossiers = [Path(d) for d in a.dossiers] or sorted(
        p.parent.parent for p in (DEPOT / "recon" / "out" / "generateur").glob("*/l1/courbes_controle.json"))
    scenes = []
    for d in dossiers:
        r = controler_scene(d)
        scenes.append(r)
        pt = r["par_type"]
        print(f"{r['scene']:45s} " + " ".join(f"{t}: flèche {v['fleche_max_m'] * 1000:.3f} mm, milieu "
                                                f"{v['milieu_max_m'] * 1000:.3f} mm, sommet {v['sommet_max_m'] * 1000:.4f} mm ;"
                                                for t, v in sorted(pt.items()))
              + f" nég {r['largeurs_negatives']} nulles {r['largeurs_nulles_hors_biseau']} biseaux "
                f"{r['extremites_de_biseau']} replis {r['replis']} chev {r['chevauchement_m2']:.2e} "
                f"jonctions {[(j['s'], round(j['ecart_m'] * 1000, 4), j['instantanee']) for j in r['jonctions']]} "
                f"dz {r['dz_ecart_max_m'] * 1000:.4f}/{r['dz_fleche_max_m'] * 1000:.3f} mm manquants "
                f"{len(r['sommets_obligatoires_manquants'])} aire {r['aire_ecart_rel_max']:.2e}")
    b = bilan(scenes)
    if a.json:
        Path(a.json).write_text(json.dumps(arrondir({"bilan": b, "scenes": scenes}), ensure_ascii=False, indent=1)
                                + "\n", encoding="utf-8")
    print(json.dumps(arrondir({k: v for k, v in b.items() if k not in ("jonctions_continues",)}), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
