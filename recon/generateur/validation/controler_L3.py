"""Contrôle indépendant du lot L3 (carrefours plans) : mesures sur la géométrie fabriquée (Python + numpy, sans Houdini).

    python recon/generateur/validation/controler_L3.py [recon/out/generateur/<scene> ...] [--json SORTIE]

Lit, pour chaque scène : l3/carrefours.json (solveur, faces de bordure, balayages), l3/mesures_l3.json (raccords),
l2/entites.json (toutes les files de bordure : branches et carrefour), l2/sol_*.npy (sol fabriqué), l2/elements.json,
l2/mesures_l2.json (sondes des éléments de bordure), l2b/peinture_*.npy (peinture fabriquée), l2b/table_marques.json
(passages), modele_voie.json ; balayages des véhicules dans recon/generateur/tmp/carrefours/<scene>/balayages.json.

Critères du plan (PLAN_GENERATEUR § 3, L3) :
  coins tangents (rupture ≤ 0,5°) et rayon = consigne ± 1 cm ; frontière fermée ; lignes CÉDEZ / STOP à 0 ± 0,05 m de la
  limite de la chaussée prioritaire ; passages à 2,0 ± 0,05 m de la ligne ; refuge ≥ 2,00 m au droit du passage ;
  aucune ligne CÉDEZ sur une branche à feux ; traversée ≤ 12 m hors refuge (bloquant) ; nez des îlots au premier
  contact des balayages des véhicules (lot L3a) + 0,30 m ;
et d'appui : sol étanche aux raccords (≤ 1 mm, aucun bord libre hors du bord extérieur), vue des bordures du carrefour
= modèle ± 5 mm, BEV derrière chaque abaissé, bordures jusque dans le carrefour (part de la frontière bordée).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
SCENES = ("J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe",
          "J6_carrefour_complexe_2x2")


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def lire(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------ géométrie
def ajuster_cercle(P):
    """Cercle des moindres carrés (Kasa) : centre, rayon, écart maximal des points."""
    P = np.asarray(P, float)
    A = np.column_stack([2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))])
    b = (P ** 2).sum(1)
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0], c[1]
    r = math.sqrt(c[2] + cx * cx + cy * cy)
    d = np.hypot(P[:, 0] - cx, P[:, 1] - cy) - r
    return (cx, cy), r, float(np.abs(d).max())


def angle(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    c = float(np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-12))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def inter_segments(p, r, q, s):
    """Intersection de [p, p + r] et [q, q + s] : (t, u) ou None."""
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    qp = (q[0] - p[0], q[1] - p[1])
    t = (qp[0] * s[1] - qp[1] * s[0]) / den
    u = (qp[0] * r[1] - qp[1] * r[0]) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return t, u
    return None


def simple(poly):
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for j in range(i + 2, n):
            if (j + 1) % n == i:
                continue
            c, d = poly[j], poly[(j + 1) % n]
            r = inter_segments(a, (b[0] - a[0], b[1] - a[1]), c, (d[0] - c[0], d[1] - c[1]))
            if r is not None and 1e-9 < r[0] < 1 - 1e-9 and 1e-9 < r[1] < 1 - 1e-9:
                return False
    return True


def aire(poly):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def dans(poly, p):
    c = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[i - 1]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            c = not c
    return c


class Sol:
    """Sol fabriqué (l2/sol_*.npy) : classe de la face visible sous un point (x, y)."""

    def __init__(self, d):
        self.P = np.load(d / "l2" / "sol_points.npy")
        F = np.load(d / "l2" / "sol_faces.npy")
        C = np.load(d / "l2" / "sol_comptes.npy")
        A = np.load(d / "l2" / "sol_attributs.npy")
        self.voc = lire(d / "l2" / "sol_vocabulaire.json")
        o = np.concatenate([[0], np.cumsum(C)])
        self.faces = [F[o[k]:o[k + 1]] for k in range(len(C))]
        self.A = A
        self.cent = np.array([self.P[f, :2].mean(0) for f in self.faces])

    def classe(self, x, y):
        idx = np.where(np.hypot(self.cent[:, 0] - x, self.cent[:, 1] - y) < 1.5)[0]
        best = None
        for k in idx:
            if self.A[k, 3] == 0:                       # face invisible (sous bordure, mur)
                continue
            q = [tuple(v) for v in self.P[self.faces[k], :2]]
            if dans(q, (x, y)):
                z = float(self.P[self.faces[k], 2].mean())
                if best is None or z > best[0]:
                    best = (z, self.voc["classe"][self.A[k, 4]], self.voc["materiau_id"][self.A[k, 5]])
        return best


def peinture(d):
    """Polygones de peinture par entité (dessus seulement : faces de normale verticale)."""
    P = np.load(d / "l2b" / "peinture_points.npy")
    F = np.load(d / "l2b" / "peinture_faces.npy")
    C = np.load(d / "l2b" / "peinture_comptes.npy")
    A = np.load(d / "l2b" / "peinture_attributs.npy")
    voc = lire(d / "l2b" / "peinture_vocabulaire.json")
    o = np.concatenate([[0], np.cumsum(C)])
    out = {}
    ent_col = voc["colonnes"].index("entite") if "colonnes" in voc and "entite" in voc["colonnes"] else 0
    noms = voc.get("entite") or voc.get("pj_entite") or []
    for k in range(len(C)):
        e = noms[A[k, ent_col]] if noms else str(A[k, ent_col])
        out.setdefault(e, []).append(P[F[o[k]:o[k + 1]], :])
    return out


# ------------------------------------------------------------------------------------------------ contrôle
def controler(d):
    d = Path(d)
    sc = d.name
    car = lire(d / "l3" / "carrefours.json")
    m3 = lire(d / "l3" / "mesures_l3.json")
    cc = lire(d / "l1" / "courbes_controle.json")
    fm = Path(cc["modele"]["fichier"])
    m = lire(fm if fm.is_absolute() else DEPOT / fm)
    o = m["repere"]["origine_l93"]
    ents = lire(d / "l2" / "entites.json")
    res = {"scene": sc}
    br = {b["route"]: b for b in car["branches"]}
    brid = {b["branche"]: b for b in car["branches"]}
    # ---------------------------------------------------------------- coins : tangence, rayon
    coins = []
    for c in car["solveur"].get("coin", []):
        Q = np.array(c["points"], float)
        parties = None
        if c.get("droit"):
            coins.append({"coin": c["coin"], "droit": True, "longueur_m": _r(c["longueur"], 3)})
            continue
        # sommets du congé (partie 1 du solveur) ; file fabriquée du coin (rg::carrefours_sol -> entités)
        par = c.get("parties") or []
        arc = Q[[i for i, k in enumerate(par) if k == 1]]
        (cx, cy), R, ecart = ajuster_cercle(arc)
        i_tb = par.index(1)
        i_ta = len(par) - 1 - par[::-1].index(1)
        # tangence : tangente du cercle ajusté aux points de tangence contre la direction locale de l'amorce
        def tang(i, j):
            a = Q[i]
            t = np.array([-(a[1] - cy), a[0] - cx])
            g = angle(t, Q[j] - Q[i])
            return min(g, 180 - g)
        tg = max(tang(i_tb, i_tb - 1), tang(i_ta, i_ta + 1))
        # rupture de la polyligne aux points de tangence (angle entre l'amorce et la première corde)
        def rupture(i):
            return angle(Q[i] - Q[i - 1], Q[i + 1] - Q[i])
        e = next((x for x in ents if x["id"] == "K-" + "".join(ch if ch.isalnum() or ch == "." else "_" for ch in c["coin"])), None)
        dev = None
        if e is not None:
            F = np.array(e["xy"], float)
            dev = 0.0
            for q in F:
                dmin = min(float(np.hypot(*(q - (a + np.clip(np.dot(q - a, b - a) / max(np.dot(b - a, b - a), 1e-12), 0, 1) * (b - a)))))
                           for a, b in zip(Q[:-1], Q[1:]))
                dev = max(dev, dmin)
        coins.append({"coin": c["coin"], "droit": False, "rayon_consigne_m": c["rayon"], "rayon_mesure_m": _r(R, 5),
                      "ecart_rayon_m": _r(abs(R - c["rayon"]), 5), "ecart_points_cercle_m": _r(ecart, 6),
                      "tangence_deg": _r(tg, 4), "rupture_polyligne_deg": _r(max(rupture(i_tb), rupture(i_ta)), 4),
                      "file_fabriquee_ecart_max_m": _r(dev, 5), "rayon_par_defaut": bool(c.get("rayon_defaut")),
                      "longueur_m": _r(c["longueur"], 3)})
    res["coins"] = coins
    # ---------------------------------------------------------------- frontière fermée
    fr = []
    for f in car["solveur"].get("frontiere", []):
        P = [tuple(p) for p in f["points"]]
        Pd = [p for i, p in enumerate(P) if i == 0 or math.dist(p, P[i - 1]) > 1e-6]
        fr.append({"carrefour": f.get("carrefour"), "sommets": len(Pd), "simple": simple(Pd),
                   "aire_m2": _r(abs(aire(Pd)), 2), "fermee": len(Pd) >= 3 and abs(aire(Pd)) > 1.0})
    res["frontiere"] = fr
    # ---------------------------------------------------------------- lignes transversales et passages
    pein = peinture(d)
    lignes = []
    for li in car["solveur"].get("ligne", []):
        gab = li.get("gabarit")
        if gab not in ("CEDEZ", "STOP", "EFFET_FEUX"):
            continue
        ent_prefix = "MQ_" + "".join(ch if ch.isalnum() else "_" for ch in li["id"]) + "_t"
        polys = [p for e, ps in pein.items() if e.startswith(ent_prefix) for p in ps]
        rid = li.get("route")
        b = br.get(rid)
        info = {"id": li["id"], "gabarit": gab, "route": rid, "pieces_peintes": len(polys)}
        if b and polys:
            P0 = np.array(b["Pf"][:2]); dd = np.array(b["dir"][:2])
            xs = np.concatenate([(p[:, :2] - P0) @ dd for p in polys])
            info.update({"bord_aval_m": _r(xs.max(), 4), "bord_amont_m": _r(xs.min(), 4),
                         "largeur_m": _r(xs.max() - xs.min(), 4), "regime_branche": b.get("regime")})
            # passages de la même route (table des marques de rg::marquages)
            tm = lire(d / "l2b" / "table_marques.json")["marques"]
            pas = [x for x in tm if x.get("classe") == "passage" and x.get("route") == rid]
            if pas:
                sf = b["s_front"]
                ecarts = []
                for x in pas:
                    s_proche = max(x["s0"], x["s1"])
                    ecarts.append(round((sf + xs.min()) - s_proche, 4))
                info["passages_retrait_m"] = ecarts
        lignes.append(info)
    res["lignes"] = lignes
    # ---------------------------------------------------------------- traversées et refuges
    sol = Sol(d)
    curbs = [np.array(e["xy"], float) for e in ents]
    trav = []
    passages = list(car["solveur"].get("passage_libre", []))
    pp_mod = []
    for c in m.get("carrefours", []):
        for p in c.get("passages_pieton", []):
            ax = p.get("axe")
            if ax:
                pp_mod.append((p["id"], [(ax[0][0] - o[0], ax[0][1] - o[1]), (ax[-1][0] - o[0], ax[-1][1] - o[1])]))
    for f in car["faces"]:
        pass
    for pid, ax in pp_mod + [(p["id"], None) for p in passages]:
        if ax is None:
            continue
        a, b = np.array(ax[0]), np.array(ax[1])
        u = (b - a) / np.linalg.norm(b - a)
        A0, A1 = a - 10 * u, b + 10 * u
        ts = []
        for Q in curbs:
            for q0, q1 in zip(Q[:-1], Q[1:]):
                r = inter_segments(A0, A1 - A0, q0, q1 - q0)
                if r is not None:
                    ts.append(r[0] * np.linalg.norm(A1 - A0))
        ts = sorted(set(round(t, 4) for t in ts))
        segs = []
        for t0, t1 in zip(ts, ts[1:]):
            if t1 - t0 < 0.05:
                continue
            mid = A0 + 0.5 * (t0 + t1) * u
            cl = sol.classe(*mid)
            segs.append((t0, t1, cl[1] if cl else None))
        # traversée : segments de chaussée consécutifs entre deux surfaces piétonnes (trottoir, refuge)
        pieton = lambda c: c is not None and any(k in c for k in ("trottoir", "terre_plein", "ilot", "refuge"))  # noqa: E731
        runs, cur, refuges = [], 0.0, []
        for t0, t1, cl in segs:
            if pieton(cl):
                if cur > 0:
                    runs.append(cur)
                cur = 0.0
                refuges.append((round(t1 - t0, 3), cl))
            else:
                cur += t1 - t0
        if cur > 0:
            runs.append(cur)
        # refuges intérieurs (entre deux parcours de chaussée)
        inner = []
        seen_ch = False
        for i, (t0, t1, cl) in enumerate(segs):
            if not pieton(cl):
                seen_ch = True
            elif seen_ch and any(not pieton(c2) for _, _, c2 in segs[i + 1:]):
                inner.append(round(t1 - t0, 3))
        trav.append({"passage": pid, "traversee_max_hors_refuge_m": _r(max(runs) if runs else 0.0, 3),
                     "parcours_chaussee_m": [_r(x, 3) for x in runs], "refuges_m": inner,
                     "segments": [[_r(t0, 3), _r(t1, 3), cl] for t0, t1, cl in segs]})
    res["traversees"] = trav
    # ---------------------------------------------------------------- nez des îlots / balayages (calcul indépendant)
    # balayages qui ont placé les nez : <scène>/l3/balayages.json (chaîne intégrée, trajectoires finales du lot L4,
    # correction après le contrôle de l'étape 2) ; à défaut, ceux du pilote du lot L3 (tmp/carrefours)
    fb = d / "l3" / "balayages.json"
    if not fb.exists():
        fb = GEN / "tmp" / "carrefours" / sc / "balayages.json"
    nez = []
    if fb.exists():
        bal = [x for x in lire(fb)["balayages"] if x["faisable"]]
        for f in car["solveur"].get("nez", []):
            b = br[f["route"]]
            P0 = np.array(b["Pf"][:2]); dd = np.array(b["dir"][:2]); nn = np.array(b["nrm"][:2])
            lo, hi = f["t_d"], f["t_g"]
            x_tip = -b["nez_retrait"]
            xout, qui = 1e9, ""
            for x in bal:
                if x["carrefour"] != b["carrefour"]:
                    continue
                E = np.array(x["exterieur"], float)
                X = (E - P0) @ dd
                Y = (E - P0) @ nn
                c = b["nez_c"]
                for i in range(len(E)):
                    j = (i + 1) % len(E)
                    cands = []
                    if lo <= Y[i] <= hi:
                        cands.append(X[i])
                    for yl in (lo, hi):
                        if (Y[i] - yl) * (Y[j] - yl) < 0:
                            w = (yl - Y[i]) / (Y[j] - Y[i])
                            cands.append(X[i] + w * (X[j] - X[i]))
                    for cx in cands:
                        if cx > -c - 5.0 and cx < xout:
                            xout, qui = cx, f"{x['trajectoire']} {x['vehicule']}"
            par_v = {}
            for x in bal:
                if x["carrefour"] != b["carrefour"]:
                    continue
                E = np.array(x["exterieur"], float)
                X = (E - P0) @ dd
                Y = (E - P0) @ nn
                xo = 1e9
                for i in range(len(E)):
                    j = (i + 1) % len(E)
                    if lo <= Y[i] <= hi and X[i] > -b["nez_c"] - 5.0:
                        xo = min(xo, X[i])
                    for yl in (lo, hi):
                        if (Y[i] - yl) * (Y[j] - yl) < 0:
                            w = (yl - Y[i]) / (Y[j] - Y[i])
                            cx_ = X[i] + w * (X[j] - X[i])
                            if cx_ > -b["nez_c"] - 5.0:
                                xo = min(xo, cx_)
                v = x["vehicule"]
                if xo < 1e8 and (v not in par_v or xo - x_tip < par_v[v][0]):
                    par_v[v] = (round(xo - x_tip, 3), x["trajectoire"])
            nez.append({"nez": f["coin"], "pointe_x_m": _r(x_tip, 3), "premier_contact_x_m": _r(xout, 3) if xout < 1e8 else None,
                        "marge_m": _r(xout - x_tip, 3) if xout < 1e8 else None, "balayage": qui,
                        "retrait_m": b["nez_retrait"], "retrait_requis_m": b.get("nez_retrait_requis"),
                        "limite_par_refuge": bool(b.get("nez_limite_refuge")),
                        "marge_par_vehicule_m": {k: v[0] for k, v in sorted(par_v.items())},
                        "trajectoire_par_vehicule": {k: v[1] for k, v in sorted(par_v.items())}})
        # îlots du cœur : distance des balayages faisables à la face de l'îlot (hors balayages qui la traversent)
        for fc in car["faces"]:
            if fc.get("kind") != "ilot":
                continue
            Q = [tuple(p) for p in fc["points"]]
            dmin, qui, coupe = 1e9, "", []
            for x in bal:
                E = [tuple(p) for p in x["exterieur"]]
                inter = any(dans(E, q) for q in Q) or any(dans(Q, e) for e in E)
                if inter:
                    coupe.append(f"{x['trajectoire']} {x['vehicule']}")
                    continue
                for q in Q[::2]:
                    for e0, e1 in zip(E, E[1:] + E[:1]):
                        vx, vy = e1[0] - e0[0], e1[1] - e0[1]
                        l2 = vx * vx + vy * vy
                        t = max(0.0, min(1.0, ((q[0] - e0[0]) * vx + (q[1] - e0[1]) * vy) / l2)) if l2 > 0 else 0.0
                        dd_ = math.hypot(q[0] - e0[0] - t * vx, q[1] - e0[1] - t * vy)
                        if dd_ < dmin:
                            dmin, qui = dd_, f"{x['trajectoire']} {x['vehicule']}"
            nez.append({"ilot": fc["ref"], "distance_min_balayage_m": _r(dmin, 3), "balayage": qui,
                        "balayages_qui_coupent": coupe})
        res["balayages"] = {"n": len(lire(fb)["balayages"]), "faisables": len(bal),
                            "infaisables": sorted({f"{x['trajectoire']} {x['vehicule']} (R axe {x['rayon_axe_min_m']} < {x['rayon_min_vehicule_m']})"
                                                   for x in lire(fb)["balayages"] if not x["faisable"]})}
    res["nez"] = nez
    # ---------------------------------------------------------------- vue des bordures du carrefour (sondes L2)
    ml2 = lire(d / "l2" / "mesures_l2.json")
    ent_c = {e["id"]: e for e in car["entites"]}
    # profils T2 (dessus plat sous la sonde à 7 cm) : vue mesurée contre la vue du modèle ; I2 (dessus chanfreiné :
    # la sonde à 7 cm ne lit pas la vue) : vue mesurée comparée à celle des bordures I2 posées par la chaîne (branches)
    ecarts, i2_car, i2_ch = [], [], []
    ent_all = {e["id"]: e for e in ents}
    for s in ml2["elements"]:
        if s.get("z_dessus") is None or s.get("z_devant") is None:
            continue
        v = s["z_dessus"] - s["z_devant"]
        e = ent_c.get(s["bordure"])
        if e is not None and str(s.get("profil", "")).startswith("T2"):
            S = e["niv_s"]
            V = [t - p for t, p in zip(e["niv_z_tete"], e["niv_z_pied"])]
            ecarts.append(abs(v - float(np.interp(s["s"], S, V))))
        elif s.get("profil") == "I2" and s.get("type") in ("droit", "courbe"):
            (i2_car if e is not None else i2_ch).append(round(v, 4))
    res["vue_bordures_carrefour"] = {"sondes_T2": len(ecarts), "ecart_max_T2_m": _r(max(ecarts) if ecarts else None, 4),
                                     "I2_carrefour_m": [min(i2_car), max(i2_car)] if i2_car else None,
                                     "I2_branches_m": [min(i2_ch), max(i2_ch)] if i2_ch else None}
    # ---------------------------------------------------------------- BEV des abaissés du carrefour
    bev = lire(d / "l2" / "bev.json")
    n_ab = sum(len(f.get("ab0") or []) for f in car["faces"])
    n_ab_bev = 0
    for f in car["faces"]:
        for k in range(len(f.get("ab0") or [])):
            if any(i.startswith(f"BEV-{f['ref']}-{k}") for i in bev):
                n_ab_bev += 1
    res["abaisses"] = {"abaisses": n_ab, "avec_bev": n_ab_bev}
    # ---------------------------------------------------------------- frontière bordée (urbain)
    L_c = sum(e["niv_s"][-1] for e in car["entites"] if not e["id"].startswith("K-") or True)
    res["bordures_carrefour_m"] = _r(L_c, 2)
    res["raccords"] = m3
    res["avertissements"] = car.get("avertissements", [])
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    dossiers = a.scenes or [str(DEPOT / "recon" / "out" / "generateur" / s) for s in SCENES]
    out = [controler(x) for x in dossiers]
    txt = json.dumps({"schema": "rg_controles_L3/0.1", "scenes": out}, ensure_ascii=False, indent=1)
    if a.json:
        Path(a.json).write_text(txt + "\n", encoding="utf-8")
    for r in out:
        print(r["scene"])
        for c in r["coins"]:
            print("  coin", c)
        for f in r["frontiere"]:
            print("  frontière", f)
        for li in r["lignes"]:
            print("  ligne", li)
        for t in r["traversees"]:
            print("  traversée", {k: v for k, v in t.items() if k != "segments"})
        for n in r["nez"]:
            print("  nez", n)
        print("  vue", r["vue_bordures_carrefour"], "abaissés", r["abaisses"], "raccords",
              {k: v for k, v in r["raccords"].items() if k in ("ecart_max_m", "bords_libres_hors_exterieur", "raccords_branches")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
