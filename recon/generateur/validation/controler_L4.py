"""Contrôle indépendant du lot L4 (marquages, trajectoires, conflits, zone de conflit des carrefours plans) : mesures sur
la géométrie fabriquée (Python, numpy, shapely ; sans Houdini).

    python recon/generateur/validation/controler_L4.py [<scene> ...] [--json SORTIE]

Lit, pour chaque scène (recon/out/generateur/<scene>/) : l4/*.json (trajectoires, conflits, zone, guidage, marques,
graphe, mesures de peinture), l1/courbes_controle.json (limites de rg::profils : axes des voies, indépendants de l'HDA
du lot), l2b/peinture_*.npy (peinture fabriquée : lignes transversales et passages), l3/carrefours.json (faces de
bordure), modele_voie.json ; gabarits du dossier 08 (hda/rg_marquages/gabarits_iisr7_pj.json) ; véhicules du lot L3a
(vehicules/balayage.py : rayon minimal, balayage du VL).

Critères (PLAN_GENERATEUR § 3, L4, carrefours J1-J5) : flèches (sommets = gabarit ± 1 mm, centrées ± 2 cm, orientées
± 0,5°, pointe de la dernière à 1,50 ± 0,02 m de la ligne, interdistance 20 ± 0,05 m, 3 par voie ou 2 si voie courte),
figurines des sas, trajectoires de rayon ≥ véhicule de projet et tangentes aux voies, guidage T'2 0,10 seulement là où
il est décrit (traits et intervalles ± 1 cm, largeur ± 2 mm), TAG à l'indonésienne sans croisement, 0 ligne
longitudinale dans la zone de conflit hors guidage (et hors discontinue prioritaire, RF-MQ-CAR-01), conflits comptés
(géométrie = topologie ; croix complète : 16 croisements, 32 conflits, CU p. 120-122), graphe (≥ 1 successeur par
voie entrante, ≤ 32 étiquettes), peinture à +2 / +3 mm ± 0,3 mm du sol fabriqué (TQ-MQG-005).
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
OUT = DEPOT / "recon" / "out" / "generateur"
SCENES = ("J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe",
          "J6_carrefour_complexe_2x2")
sys.path.insert(0, str(GEN))
from vehicules import balayage as B  # noqa: E402

GAB = json.loads((GEN / "hda" / "rg_marquages" / "gabarits_iisr7_pj.json").read_text(encoding="utf-8"))["gabarits"]
R_VL = B.rayon_min("vl")
W_VL = 1.80


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def lire(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def ang(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    c = float(np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-12))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def nettoyer(P, tol=1e-9):
    out = []
    for p in P:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append((float(p[0]), float(p[1])))
    return out


# ------------------------------------------------------------------------------------------------ axes des voies (L1)
def axes_voies(cc):
    """{(route, bande): [(s, x, y, largeur)]} : axe de chaque bande, milieu de ses deux limites (courbes de contrôle de
    rg::profils, lot L1 ; sections bout à bout)."""
    out = {}
    for r in cc["routes"]:
        for sec in r["sections"]:
            lims = {l["cle"]: l for l in sec["limites"]}
            for b in sec.get("bandes", []):
                g = next((l for c, l in lims.items() if c.endswith("|" + b["id"])), None)
                d = next((l for c, l in lims.items() if c.startswith(b["id"] + "|")), None)
                if g is None or d is None:
                    continue
                for k, s in enumerate(sec["s"]):
                    x = 0.5 * (g["x"][k] + d["x"][k])
                    y = 0.5 * (g["y"][k] + d["y"][k])
                    w = math.hypot(g["x"][k] - d["x"][k], g["y"][k] - d["y"][k])
                    out.setdefault((r["id"], b["id"]), []).append((s, x, y, w))
    for k in out:
        out[k].sort()
    return out


def reference(cc, rid):
    r = next(x for x in cc["routes"] if x["id"] == rid)
    ref = r["reference"]
    return np.array(ref["s"]), np.array(ref["x"]), np.array(ref["y"])


def s_de(cc_ref, x, y):
    S, X, Y = cc_ref
    i = int(np.argmin((X - x) ** 2 + (Y - y) ** 2))
    j = min(max(i, 1), len(S) - 1)
    a = np.array([X[j - 1], Y[j - 1]])
    b = np.array([X[j], Y[j]])
    v = b - a
    u = float(np.clip(np.dot([x - a[0], y - a[1]], v) / max(np.dot(v, v), 1e-18), -0.5, 1.5))
    return float(S[j - 1] + u * (S[j] - S[j - 1]))


def axe_proche(A, p):
    """Point de l'axe A (liste (s, x, y, w)) le plus proche de p : (distance, s, tangente unitaire, largeur)."""
    P = np.array([[a[1], a[2]] for a in A])
    best = None
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        v = b - a
        L2 = float(np.dot(v, v))
        if L2 < 1e-14:
            continue
        u = float(np.clip(np.dot(np.asarray(p) - a, v) / L2, 0.0, 1.0))
        q = a + u * v
        d = float(np.linalg.norm(np.asarray(p) - q))
        if best is None or d < best[0]:
            best = (d, A[i][0] + u * (A[i + 1][0] - A[i][0]), v / math.sqrt(L2), A[i][3] + u * (A[i + 1][3] - A[i][3]))
    return best


# ------------------------------------------------------------------------------------------------ peinture (L2b)
def peinture(d):
    P = np.load(d / "l2b" / "peinture_points.npy")
    F = np.load(d / "l2b" / "peinture_faces.npy")
    C = np.load(d / "l2b" / "peinture_comptes.npy")
    A = np.load(d / "l2b" / "peinture_attributs.npy")
    voc = lire(d / "l2b" / "peinture_vocabulaire.json")
    ents = voc["pj_entite"]
    polys = {}
    k = 0
    for i, n in enumerate(C):
        idx = F[k:k + n]
        k += n
        if A[i, 2] != 1:
            continue
        pg = Polygon([(P[j, 0], P[j, 1]) for j in idx])
        if pg.is_valid and pg.area > 1e-8:
            polys.setdefault(ents[A[i, 0]], []).append(pg)
    return {e: unary_union(v) for e, v in polys.items()}


def distance_couloir(trans, p, ey, demi=1.2, longueur=8.0):
    """Distance de p, le long de ey, au premier point de la peinture transversale dans un couloir de ± demi (m) : les
    lignes T'2 ont des vides, un rayon unique peut passer entre deux traits."""
    if trans is None:
        return None
    ex = np.array([ey[1], -ey[0]])
    p = np.asarray(p, float)
    cor = Polygon([tuple(p - demi * ex), tuple(p - demi * ex + longueur * ey), tuple(p + demi * ex + longueur * ey),
                   tuple(p + demi * ex)])
    it = trans.intersection(cor)
    if it.is_empty:
        return None
    best = None
    for g in getattr(it, "geoms", [it]):
        cs = list(g.exterior.coords) if hasattr(g, "exterior") else list(g.coords)
        for q in cs:
            d = float(np.dot(np.asarray(q) - p, ey))
            best = d if best is None else min(best, d)
    return best


def transversales(paint):
    """Empreintes peintes des lignes transversales (CÉDEZ, STOP, effet des feux, sas : lot L3) et des passages."""
    out = [g for e, g in paint.items() if re.search(r"ligne|sas_|cedez|stop|_PP_|passage|_pp", e, re.I)
           and not e.startswith(("MQ_L4_", "ML_L4_"))]
    return unary_union(out) if out else None


# ------------------------------------------------------------------------------------------------ contrôles
def ctl_fleches(d, l4, cc, axes, paint):
    tab = [t for t in l4["marques"]["table"] if t["m_classe"] == "fleche"]
    emp = {}
    for e in l4["marques"]["marques_l4"]:
        emp.setdefault(e["pj_entite"], []).append(e)
    trans = transversales(paint)
    res = {"fleches": len(tab), "ecart_gabarit_max_mm": 0.0, "centrage_max_m": 0.0, "orientation_max_deg": 0.0,
           "pointe_ligne": [], "interdistances": [], "comptes": [], "details": []}
    par_voie = {}
    for t in tab:
        g = GAB[t["m_gabarit"]]
        o = np.array(t["xy"])
        cap = math.radians(t["m_cap_deg"])
        ey = np.array([math.cos(cap), math.sin(cap)])
        ex = np.array([ey[1], -ey[0]])
        tpl = [o + x * ex + y * ey for x, y in g["polygone"]]
        ent = "MQ_L4_" + re.sub(r"[^A-Za-z0-9]", "_", t["m_id"])
        pts = [np.array(p) for e in emp.get(ent, []) for p in e["xy"]]
        if not pts:
            res["details"].append({"id": t["m_id"], "erreur": "empreinte absente"})
            continue
        P = np.array(pts)
        e1 = max(float(np.min(np.linalg.norm(P - q, axis=1))) for q in tpl)
        bord = LineString(list(map(tuple, tpl)) + [tuple(tpl[0])])
        e2 = max(bord.distance(Point(p)) for p in P)
        eg = 1000.0 * max(e1, e2)
        res["ecart_gabarit_max_mm"] = max(res["ecart_gabarit_max_mm"], eg)
        L = float(g["longueur_m"])
        pointe = o + L * ey
        A = axes.get((t["m_route"], t["m_bande"]))
        dc, so, tg, w = axe_proche(A, o)
        dt, st_, tg2, w2 = axe_proche(A, pointe)
        cen = max(dc, dt)
        ori = ang(ey, (tg + tg2) / 2.0)
        res["centrage_max_m"] = max(res["centrage_max_m"], cen)
        res["orientation_max_deg"] = max(res["orientation_max_deg"], ori)
        dl = distance_couloir(trans, pointe, ey)
        par_voie.setdefault((t["m_branche"], t["m_bande"]), []).append((t["m_rang"], pointe, dl, t, so, w))
        res["details"].append({"id": t["m_id"], "gabarit": t["m_gabarit"], "ecart_gabarit_mm": _r(eg, 3),
                               "centrage_m": _r(cen, 4), "orientation_deg": _r(ori, 3),
                               "pointe_a_la_ligne_m": _r(dl, 4)})
    ref_cache = {}
    for (br, bande), L_ in sorted(par_voie.items()):
        L_.sort(key=lambda x: x[0])
        der = L_[0]
        res["pointe_ligne"].append({"voie": f"{br}/{bande}", "distance_m": _r(der[2], 4)})
        for a, b in zip(L_, L_[1:]):
            res["interdistances"].append({"voie": f"{br}/{bande}", "m": _r(float(np.linalg.norm(a[1] - b[1])), 4)})
        t = der[3]
        # nombre attendu : voie formée (≥ 99 % de sa largeur à la ligne) sous chaque flèche (ARB-11 : 2 si courte)
        rid = t["m_route"]
        if rid not in ref_cache:
            ref_cache[rid] = axes
        A = axes[(rid, bande)]
        w_end = A[-1][3]
        s_tip0 = t["m_s1"]
        n_fit = 0
        for k in range(int(t["m_n_demande"])):
            s1 = s_tip0 - 20.0 * k
            s0 = s1 - 4.0
            ws = [a[3] for a in A if s0 - 1e-6 <= a[0] <= s1 + 1e-6]
            if s0 <= 0 or not ws or min(ws) < 0.99 * w_end:
                break
            sous = [a for a in A if s0 - 1e-6 <= a[0] <= s1 + 1e-6]
            P0, Pm, P1 = (np.array(sous[0][1:3]), np.array(sous[len(sous) // 2][1:3]), np.array(sous[-1][1:3]))
            if len(sous) >= 3 and ang(Pm - P0, P1 - Pm) > 0.5:
                break
            n_fit += 1
        res["comptes"].append({"voie": f"{br}/{bande}", "posees": len(L_), "demandees": int(t["m_n_demande"]),
                               "tenant_dans_la_voie": n_fit})
    return res


def ctl_sas(l4, axes, paint):
    tab = [t for t in l4["marques"]["table"] if t["m_classe"] == "figurine_sas"]
    trans = transversales(paint)
    out = []
    for t in tab:
        c = np.array(t["xy"])
        A = axes[(t["m_route"], t["m_bande"])]
        dc, s, tg, w = axe_proche(A, c)
        cap = math.radians(t["m_cap_deg"])
        ey = np.array([math.cos(cap), math.sin(cap)])
        dav = distance_couloir(trans, c, ey, demi=1.2, longueur=6.0)
        dam = distance_couloir(trans, c, -ey, demi=1.2, longueur=6.0)
        out.append({"id": t["m_id"], "axe_m": _r(dc, 4),
                    "vers_ligne_avant_m": _r(dav, 4), "vers_ligne_arriere_m": _r(dam, 4),
                    "profondeur_sas_m": _r((dav or 0) + (dam or 0), 4),
                    "centrage_m": _r(abs((dav or 0) - (dam or 0)) / 2.0, 4)})
    return out


def rayon_arc(P, R_attendu):
    """Rayon de l'arc d'une trajectoire : cercle des moindres carrés (Kasa) sur la plus longue suite de sommets qui
    tournent dans le même sens (déviation > 0,05°) ; robuste au bruit des positions (flottants 32 bits), contrairement
    au rayon à trois points. Renvoie (rayon, écart maximal des sommets au cercle)."""
    P = np.asarray(P, float)
    dev = []
    for i in range(1, len(P) - 1):
        u, v = P[i] - P[i - 1], P[i + 1] - P[i]
        dev.append(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], float(np.dot(u, v)))))
    best, cur = (0, -1, -1), None
    for i, dv in enumerate(dev, start=1):
        sg = 1 if dv > 0.05 else (-1 if dv < -0.05 else 0)
        if sg and cur and cur[0] == sg:
            cur = (sg, cur[1], i)
        else:
            cur = (sg, i, i) if sg else None
        if cur and cur[2] - cur[1] > best[2] - best[1]:
            best = cur
    if best[1] < 0 or best[2] - best[1] < 2:
        return None, None
    Q = P[best[1] - 1:best[2] + 2]
    A = np.column_stack([2 * Q[:, 0], 2 * Q[:, 1], np.ones(len(Q))])
    bb = (Q ** 2).sum(1)
    cc, *_ = np.linalg.lstsq(A, bb, rcond=None)
    r = math.sqrt(cc[2] + cc[0] ** 2 + cc[1] ** 2)
    d = np.abs(np.hypot(Q[:, 0] - cc[0], Q[:, 1] - cc[1]) - r)
    return r, float(d.max())


def ctl_trajectoires(l4, axes, br):
    tr = l4["traj"]["trajectoires"]
    voies = {(v["branche"], v["bande"], v["entrante"]): v for v in l4["traj"]["voies"]}
    route = {b["branche"]: b["route"] for b in br}
    out = {"vehicule": [], "velo": 0, "rayon_min_m": None, "rupture_max_deg": 0.0, "tangence_bouts_max_deg": 0.0,
           "decalage_bouts_max_m": 0.0, "non_faisables": []}
    rmin = math.inf
    for t in tr:
        P = nettoyer(t["points"])
        if t["tags"] == "velo":
            out["velo"] += 1
        else:
            r, res_ = rayon_arc(P, t["rayon"]) if t["rayon"] > 0 else (None, None)
            r = math.inf if r is None else r
            rmin = min(rmin, r)
            if r < R_VL - 1e-3:
                out["non_faisables"].append({"id": t["id"], "rayon_mesure_m": _r(r, 4)})
            out["vehicule"].append({"id": t["id"], "mouvement": t["mouvement"], "rayon_m": _r(t["rayon"], 3),
                                    "rayon_mesure_m": _r(r, 4) if r < math.inf else None,
                                    "longueur_m": _r(t["longueur"], 2), "phases": t["phases"]})
        # rupture des polylignes dans la jonction : sommets hors des axes de voie du lot L1 (les plis d'un axe de voie
        # — biseaux des lois de largeur du profil — appartiennent au profil, ils sont rapportés à part)
        Ain = axes.get((route[t["de_branche"]], t["de_bande"]))
        Aout = axes.get((route[t["vers_branche"]], t["vers_bande"]))

        def sur_axe(q):
            return any(A_ is not None and axe_proche(A_, q)[0] < 0.002 for A_ in (Ain, Aout))
        for i in range(1, len(P) - 1):
            a_ = ang(np.subtract(P[i], P[i - 1]), np.subtract(P[i + 1], P[i]))
            if sur_axe(P[i - 1]) and sur_axe(P[i]) and sur_axe(P[i + 1]):
                out["plis_axes_voies_max_deg"] = max(out.get("plis_axes_voies_max_deg", 0.0), a_)
                continue
            out["rupture_max_deg"] = max(out["rupture_max_deg"], a_)
        # bouts : sur l'axe de la voie (L1) et tangents à elle
        for bout, (br_, bande, ent) in ((0, (t["de_branche"], t["de_bande"], 1)), (-1, (t["vers_branche"], t["vers_bande"], 0))):
            A = axes.get((route[br_], bande))
            if A is None:
                continue
            p = np.array(P[bout])
            dd, s, tg, w = axe_proche(A, p)
            seg = np.subtract(P[1], P[0]) if bout == 0 else np.subtract(P[-1], P[-2])
            a1 = min(ang(seg, tg), ang(seg, -tg))
            out["decalage_bouts_max_m"] = max(out["decalage_bouts_max_m"], dd)
            out["tangence_bouts_max_deg"] = max(out["tangence_bouts_max_deg"], a1)
    out["rayon_min_m"] = _r(rmin, 4)
    out["rayon_min_vehicule_m"] = _r(R_VL, 4)
    return out


def ctl_guidage(d, l4, m, paint):
    desc = [t["id"] for c in m.get("carrefours", []) for t in c.get("trajectoires", [])
            if (t.get("guidage") or {}).get("materialise")]
    gu = l4["guidage"]["lignes"]
    res = {"trajectoires_guidees_decrites": desc, "lignes": len(gu), "traits": [], "intervalles": [],
           "largeurs": [], "tag_croisements": None, "garde_caisse_min_m": None, "balayages": None}
    if not gu:
        return res
    for g in gu:
        C = LineString(nettoyer(g["points"]))
        dash = [e for e in l4["marques"]["lignes_finales"] if e.get("cle") == "guidage"]
        par = {}
        for e in dash:
            par.setdefault(e["pj_entite"], []).append(e)
        iv = []
        for ent, es in par.items():
            us = [C.project(Point(p)) for e in es for p in e["xy"]]
            a = sum(Polygon(e["xy"]).area for e in es)
            u0, u1 = min(us), max(us)
            iv.append((u0, u1))
            res["traits"].append(u1 - u0)
            res["largeurs"].append(a / max(u1 - u0, 1e-9))
        iv.sort()
        res["intervalles"] = [b[0] - a[1] for a, b in zip(iv, iv[1:])]
        ids = g["mouvements"].split()
        T = {t["id"]: t for t in l4["traj"]["trajectoires"]}
        a, b = LineString(nettoyer(T[ids[0]]["points"])), LineString(nettoyer(T[ids[1]]["points"]))
        res["tag_croisements"] = 0 if a.intersection(b).is_empty else len(getattr(a.intersection(b), "geoms", [1]))
        res["garde_caisse_min_m"] = _r(min(a.distance(C), b.distance(C)) - W_VL / 2.0, 4)
        # balayages du VL (lot L3a) sur les deux trajectoires, avec 15 m d'approche et de sortie dans l'axe
        env = []
        for tid in ids:
            P = nettoyer(T[tid]["points"])
            u = np.subtract(P[1], P[0]); u = u / np.linalg.norm(u)
            v = np.subtract(P[-1], P[-2]); v = v / np.linalg.norm(v)
            axe = [tuple(np.array(P[0]) - 15.0 * u)] + P + [tuple(np.array(P[-1]) + 15.0 * v)]
            pg = B.balayage_detail("vl", axe)["polygone"]
            env.append(Polygon(pg.exterieur).buffer(0))
        l3 = lire(d / "l3" / "carrefours.json")
        faces = [LineString(nettoyer(f["points"])) for f in l3["faces"] if len(f["points"]) >= 2]
        bord = unary_union(faces) if faces else None
        res["balayages"] = {"recouvrement_m2": _r(env[0].intersection(env[1]).area, 4),
                            "distance_m": _r(env[0].distance(env[1]), 4),
                            "sur_la_ligne_m": [_r(e.intersection(C).length, 4) for e in env],
                            "contre_bordures_m": [_r(e.intersection(bord).length, 4) if bord is not None else None
                                                  for e in env],
                            "distance_bordures_m": [_r(e.exterior.distance(bord), 4) if bord is not None else None
                                                    for e in env]}
    return res


def ctl_zone(l4, m):
    zones = [Polygon(z["points"]).buffer(0) for z in l4["zone"]["zones"]]
    Z = unary_union(zones) if zones else None
    dedans = []
    autorise = 0
    for e in l4["marques"]["lignes_finales"]:
        c = Polygon(e["xy"]).centroid if len(e["xy"]) >= 3 else None
        if c is None or Z is None or not Z.contains(c):
            continue
        cle = e.get("cle") or ""
        if e.get("rg_l4") and (cle == "guidage" or cle.startswith("axe_prioritaire")):
            autorise += 1
            continue
        dedans.append({"entite": e["pj_entite"], "route": e["route"], "cle": cle})
    ret = l4["retirees"]["morceaux"]
    return {"zones": len(zones), "aire_m2": _r(Z.area if Z is not None else 0.0, 2), "valides": all(z.is_valid for z in zones),
            "lignes_dans_la_zone": len(dedans), "exemples": dedans[:10], "marques_autorisees_dans_la_zone": autorise,
            "retires": sum(1 for r in ret if not r["rg_l4_raison"].startswith("coupé")),
            "coupes": sum(1 for r in ret if r["rg_l4_raison"].startswith("coupé")),
            "raisons": sorted({r["rg_l4_raison"] for r in ret})}


def ctl_conflits(l4, br):
    tr = [t for t in l4["traj"]["trajectoires"] if t["tags"] != "velo"]
    c = br[0]["centre"] if br else [0, 0, 0]
    geo = {(k["a"], k["b"]): k["type"] for k in l4["conflits"]["conflits"] if k["famille"] == "vl_vl"}
    geo.update({(b, a): v for (a, b), v in list(geo.items())})

    def az(p):
        return math.atan2(p[1] - c[1], p[0] - c[0])

    def entre(a, x, b):
        """x strictement sur l'arc trigonométrique de a à b"""
        da = (x - a) % (2 * math.pi)
        db = (b - a) % (2 * math.pi)
        return 1e-9 < da < db - 1e-9

    topo = {}
    for i, a in enumerate(tr):
        for b in tr[i + 1:]:
            mE = (a["de_branche"], a["de_bande"]) == (b["de_branche"], b["de_bande"])
            mS = (a["vers_branche"], a["vers_bande"]) == (b["vers_branche"], b["vers_bande"])
            if mE and mS:
                continue
            if mE:
                topo[(a["id"], b["id"])] = "divergence"
                continue
            if mS:
                topo[(a["id"], b["id"])] = "convergence"
                continue
            a1, a2, b1, b2 = az(a["points"][0]), az(a["points"][-1]), az(b["points"][0]), az(b["points"][-1])
            if entre(a1, b1, a2) != entre(a1, b2, a2):
                topo[(a["id"], b["id"])] = "croisement"
    nb = {k: sum(1 for v in topo.values() if v == k) for k in ("croisement", "convergence", "divergence")}
    ng = {k: sum(1 for (a, b), v in geo.items() if v == k and a < b) for k in ("croisement", "convergence", "divergence")}
    diff = [f"{a} / {b} : géométrie {geo.get((a, b), '-')}, topologie {v}" for (a, b), v in topo.items()
            if geo.get((a, b)) != v]
    diff += [f"{a} / {b} : géométrie {v}, topologie -" for (a, b), v in geo.items() if a < b
             and (a, b) not in topo and (b, a) not in topo]
    meme = sum(1 for k in l4["conflits"]["conflits"] if k["famille"] == "vl_vl" and k["type"] == "croisement"
               and k["meme_phase"])
    ent, sor = {}, {}
    for t in tr:
        ent[(t["de_branche"], t["de_bande"])] = ent.get((t["de_branche"], t["de_bande"]), 0) + 1
        sor[(t["vers_branche"], t["vers_bande"])] = sor.get((t["vers_branche"], t["vers_bande"]), 0) + 1
    points = {"croisement": ng["croisement"], "divergence": sum(k - 1 for k in ent.values()),
              "convergence": sum(k - 1 for k in sor.values())}
    points["total"] = sum(points.values())
    return {"geometrie": ng, "topologie": nb, "points_CU": points, "ecarts": diff, "croisements_meme_phase": meme,
            "mouvements": sorted(t["id"] for t in tr)}


def ctl_graphe(l4):
    g = l4["graphe"]
    voies = {v["id"]: v for v in g["voies"]}
    dmax, amax = 0.0, 0.0
    for c in g["connecteurs"]:
        if not c["de"] or not c["vers"]:
            continue
        a, b = voies[c["de"]], voies[c["vers"]]
        P = nettoyer(c["polyligne"])
        A = nettoyer(a["polyligne"])
        Bv = nettoyer(b["polyligne"])
        dmax = max(dmax, math.dist(P[0], A[-1]), math.dist(P[-1], Bv[0]))
        amax = max(amax, ang(np.subtract(P[1], P[0]), np.subtract(A[-1], A[-2])),
                   ang(np.subtract(Bv[1], Bv[0]), np.subtract(P[-1], P[-2])))
    return {**g["comptes"], "raccord_max_m": _r(dmax, 5), "raccord_angle_max_deg": _r(amax, 3),
            "etiquettes_liste": g["etiquettes"]}


def ctl_axe_rives(l4, br, cc):
    """Discontinue prioritaire prolongée (RF-MQ-CAR-01) et rives interrompues au droit des affluentes (RF-MQ-SC-11)."""
    ax = [e for e in l4["marques"]["lignes_finales"] if (e.get("cle") or "").startswith("axe_prioritaire")]
    prio = [b for b in br if b["regime"] == "prioritaire"]
    rives = 0
    for b in prio:
        ref = reference(cc, b["route"])
        for cote, sg in (("g", 1), ("d", -1)):
            if b[f"rayon_coin_{cote}"] <= 0 or b[f"droit_{cote}"]:
                continue
            for e in l4["marques"]["lignes_finales"]:
                if e.get("route") != b["route"] or e.get("rg_l4"):
                    continue
                c = Polygon(e["xy"]).centroid
                s = s_de(ref, c.x, c.y)
                if s < b[f"s_tan_{cote}"] - 1e-3:
                    continue
                # côté : au-delà de l'axe de la voie extrême (t le plus grand à gauche, le plus petit à droite)
                vs = [v for v in l4["traj"]["voies"] if v["branche"] == b["branche"] and v["type"].startswith("voie")]
                if not vs:
                    continue
                tax = max(v["t_axe"] for v in vs) if cote == "g" else min(v["t_axe"] for v in vs)
                Sx, X, Y = ref
                i = int(np.argmin(np.abs(Sx - s)))
                j = min(max(i, 1), len(Sx) - 1)
                tgt = np.array([X[j] - X[j - 1], Y[j] - Y[j - 1]])
                tgt /= np.linalg.norm(tgt)
                nrm = np.array([-tgt[1], tgt[0]])
                t = float(np.dot([c.x - X[i], c.y - Y[i]], nrm))
                if (cote == "g" and t > tax) or (cote == "d" and t < tax):
                    rives += 1
    return {"branches_prioritaires": len(prio), "tirets_axe_ajoutes": len({e["pj_entite"] for e in ax}),
            "axe": l4["marques"].get("axe_prioritaire") or [], "rives_restantes_au_droit_des_affluentes": rives}


def controler(scene):
    d = OUT / scene
    l4 = {"traj": lire(d / "l4" / "trajectoires.json"), "conflits": lire(d / "l4" / "conflits.json"),
          "zone": lire(d / "l4" / "zone_conflit.json"), "guidage": lire(d / "l4" / "guidage.json"),
          "marques": lire(d / "l4" / "marques_l4.json"), "graphe": lire(d / "l4" / "graphe_voies.json"),
          "retirees": lire(d / "l4" / "lignes_retirees.json"), "mesures": lire(d / "l4" / "mesures_l4.json")}
    cc = lire(d / "l1" / "courbes_controle.json")
    m = lire(d / "modele_voie.json")
    axes = axes_voies(cc)
    paint = peinture(d)
    br = l4["traj"]["branches"]
    return {"scene": scene,
            "fleches": ctl_fleches(d, l4, cc, axes, paint),
            "sas": ctl_sas(l4, axes, paint),
            "trajectoires": ctl_trajectoires(l4, axes, br),
            "guidage": ctl_guidage(d, l4, m, paint),
            "zone": ctl_zone(l4, m),
            "conflits": ctl_conflits(l4, br),
            "graphe": ctl_graphe(l4),
            "axe_rives": ctl_axe_rives(l4, br, cc),
            "peinture": l4["mesures"]["peinture"],
            "avertissements": l4["traj"]["details"].get("avertissements")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = [controler(Path(s).name) for s in (a.scenes or SCENES)]
    txt = json.dumps(res, ensure_ascii=False, indent=1, default=float)
    if a.json:
        Path(a.json).write_text(txt + "\n", encoding="utf-8")
    else:
        print(txt)


if __name__ == "__main__":
    main()
