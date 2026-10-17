# -*- coding: utf-8 -*-
"""Contrôle indépendant du lot L2b (marquages de la section courante) sur la géométrie fabriquée.

    python recon/generateur/validation/controler_L2b.py [recon/out/generateur/<scene> ...] [--json SORTIE]

Lit les sorties de fabriquer_l2b.py (peinture_*.npy, mesures_l2b.npz, table_marques.json) et les compare aux marques
recalculées par `analytique_L2b` (modèle, règles, gabarits du dossier 08 ; aucun code commun avec le VEX) :
  - lignes : chaque tiret fabriqué (sommets du pied de la jupe, au ras de l'empreinte) projeté en (s, t) : début, fin,
    largeur, décalage à la limite ; modulation (période et trait, dérive cumulée sur le tronçon) ;
  - flèches, triangles, figurines, lettres : écart des sommets fabriqués au gabarit posé et des sommets du gabarit au
    maillage (≤ 1 mm), rotation (ICP, Kabsch itéré), position par le centre de surface des faces du dessus (biais du
    chanfrein ≤ 2 mm), centrage dans la voie (± 2 cm), positions et interdistances (RF-MQ-RAB-05, DEF-017) ;
  - passages : nombre de bandes, largeurs, intervalles et marges (DEF-011, RF-MQ-PP-05), longueur ;
  - zébras : angle des hachures avec la rive (côtés parallèles de l'enveloppe sans sommets alignés ; une hachure sans
    côtés mesurables est signalée), pas perpendiculaire, nombre de hachures et d'aplats (DEF-020) ;
  - épaisseur : dessus de peinture − sol fabriqué = e_top ± 0,3 mm (TQ-MQG-002, TQ-MQG-004) aux sommets et aux
    centres des faces du dessus ; aucune peinture sur une bordure ou un caniveau (TQ-MQG-014) ;
  - « attendus » de la description (catalogue) mesurés sur les sorties fabriquées (L1, L2, L2b).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent))
import analytique_L2b as AB  # noqa: E402
import regles  # noqa: E402

DEPOT = ICI.parents[2]
SORTIE = DEPOT / "recon" / "out" / "generateur"
SCENES = [f"S{k:02d}" for k in range(1, 13)]
TOL = {"tiret_m": 0.01, "largeur_m": 0.002, "gabarit_m": 0.001, "centrage_m": 0.02, "angle_deg": 0.5,
       "interdistance_m": 0.05, "hachure_angle_deg": 0.1, "hachure_pas_m": 0.01, "epaisseur_m": 0.0003,
       "passage_e_m": 0.01}


def _ent_nom(i):
    return re.sub(r"[^A-Za-z0-9]", "_", i)


# ------------------------------------------------------------------------------------------------ chargement
class Peinture:
    def __init__(self, d2b: Path):
        self.P = np.load(d2b / "peinture_points.npy")
        F = np.load(d2b / "peinture_faces.npy")
        C = np.load(d2b / "peinture_comptes.npy")
        self.A = np.load(d2b / "peinture_attributs.npy")
        self.voc = json.loads((d2b / "peinture_vocabulaire.json").read_text(encoding="utf-8"))
        m = np.load(d2b / "mesures_l2b.npz")
        self.au = m["au_dessus"]
        self.dessus = m["dessus"]
        self.au_c = m["au_dessus_centre"]
        self.dessus_f = m["dessus_face"]
        off = np.concatenate([[0], np.cumsum(C)])
        self.faces = [F[off[i]:off[i + 1]] for i in range(len(C))]
        self.ent = {}
        for i, f in enumerate(self.faces):
            nom = self.voc["pj_entite"][self.A[i, 0]]
            e = self.ent.setdefault(nom, {"faces": [], "classe": self.voc["classe"][self.A[i, 1]]})
            e["faces"].append(i)
        for nom, e in self.ent.items():
            e["points"] = np.unique(np.concatenate([self.faces[i] for i in e["faces"]]))
            e["pied"] = e["points"][self.au[e["points"]] < -0.001]          # pied de la jupe : empreinte exacte
        self.table = json.loads((d2b / "table_marques.json").read_text(encoding="utf-8"))

    def classe_point(self):
        cl = np.full(len(self.P), "", dtype=object)
        for i, f in enumerate(self.faces):
            cl[f] = self.voc["classe"][self.A[i, 1]]
        return cl


def _st(S, R, xy):
    return np.array([S.st_de_xy(R, float(x), float(y)) for x, y in xy])


# ------------------------------------------------------------------------------------------------ lignes
def ctl_lignes(S, PE, rid):
    R = S.routes[rid]
    att = S.lignes(rid)
    tab = {m["id"]: m for m in PE.table["marques"] if m["classe"] == "ligne"}
    fab = []
    for nom, e in PE.ent.items():
        if e["classe"] != "ligne":
            continue
        m = tab.get(nom)
        if m is None:
            fab.append({"nom": nom, "inconnu": True})
            continue
        st = _st(S, R, PE.P[e["pied"], :2])
        tl = np.array([S.t_cle(R, m["cle"], s) for s in st[:, 0]], float)
        d = st[:, 1] - tl
        fab.append({"nom": nom, "cle": m["cle"], "modulation": m["modulation"], "largeur": m["largeur"],
                    "s0": float(st[:, 0].min()), "s1": float(st[:, 0].max()), "dmin": float(d.min()),
                    "dmax": float(d.max())})
    def peint(cle, w, a, b):
        """Étendue en s de la partie peinte d'un tiret [a, b] : bande [t − w/2, t + w/2] moins les corps de bordure et
        les caniveaux (TQ-MQG-014) ; bornes affinées par bissection (1e-7 m)."""
        def ok(x):
            t = S.t_cle(R, cle, x)
            if t is None:
                return False
            lo, hi = t - w / 2, t + w / 2
            seg = [(lo, hi)]
            for z0, z1 in S.zones_interdites(R, x):
                seg = [q for a0, b0 in seg for q in ((a0, min(b0, z0)), (max(a0, z1), b0)) if q[1] - q[0] > 1e-7]
            return any(q[1] - q[0] > 1e-6 for q in seg)
        xs = np.linspace(a, b, max(2, int(math.ceil((b - a) / 0.02)) + 1))
        oks = [ok(x) for x in xs]
        if not any(oks):
            return None
        i0 = oks.index(True)
        i1 = len(oks) - 1 - oks[::-1].index(True)

        def bis(u, v):
            fu = ok(u)
            for _ in range(40):
                m = 0.5 * (u + v)
                if ok(m) == fu:
                    u = m
                else:
                    v = m
            return 0.5 * (u + v)
        a2 = a if i0 == 0 else bis(xs[i0 - 1], xs[i0])
        b2 = b if i1 == len(xs) - 1 else bis(xs[i1], xs[i1 + 1])
        return a2, b2

    ecarts = {"debut_fin_max_m": 0.0, "largeur_max_m": 0.0, "decentrage_max_m": 0.0}
    manquants, en_trop = [], []
    vus = set()
    runs_mes = []
    for r in att:
        cand = [f for f in fab if not f.get("inconnu") and f["cle"] == r["cle"] and f["modulation"] == r["modulation"]
                and abs(f["largeur"] - r["largeur"]) < 1e-6]
        mes = []
        for a0, b0 in r["tirets"]:
            ab = peint(r["cle"], r["largeur"], a0, b0)
            if ab is None:
                continue
            a, b = ab
            f = min(cand, key=lambda f: abs(f["s0"] - a) + abs(f["s1"] - b), default=None)
            if f is None or abs(f["s0"] - a) > 0.5:
                manquants.append(f"{r['cle']} {r['modulation']} [{a:.3f}, {b:.3f}]")
                continue
            vus.add(f["nom"])
            ecarts["debut_fin_max_m"] = max(ecarts["debut_fin_max_m"], abs(f["s0"] - a), abs(f["s1"] - b))
            ecarts["largeur_max_m"] = max(ecarts["largeur_max_m"], abs((f["dmax"] - f["dmin"]) - r["largeur"]))
            ecarts["decentrage_max_m"] = max(ecarts["decentrage_max_m"], abs(0.5 * (f["dmax"] + f["dmin"])))
            mes.append((f["s0"], f["s1"]))
        runs_mes.append((r, mes))
    en_trop = [f["nom"] for f in fab if f["nom"] not in vus]
    # modulation mesurée : période (débuts successifs), trait (tirets entiers), dérive cumulée par tronçon continu
    mods = AB.modulations()
    per_max = trait_max = derive_max = 0.0
    n_periodes = 0
    for r, mes in runs_mes:
        if r["modulation"] == "continue" or len(mes) < 2:
            continue
        tr, vi = mods[r["modulation"]]
        P = tr + vi
        mes = sorted(mes)
        # tronçons continus (une interruption remet la phase à zéro) : début de tronçon = début de tiret attendu
        # après une interruption
        debuts = [a for a, b in r["tirets"]]
        groupes = []
        for k, (a, b) in enumerate(mes):
            if k == 0 or abs((a - mes[k - 1][0]) - P) > 0.25 * P:
                groupes.append([])
            groupes[-1].append((a, b))
        for g in groupes:
            for k in range(1, len(g)):
                per_max = max(per_max, abs((g[k][0] - g[k - 1][0]) - P))
                n_periodes += 1
            for k, (a, b) in enumerate(g):
                derive_max = max(derive_max, abs(a - g[0][0] - k * P))
                if b - a > 0.99 * tr or k < len(g) - 1:
                    trait_max = max(trait_max, abs((b - a) - tr))
        del debuts
    traits = {}
    continues = {}
    for f in fab:
        if f.get("inconnu"):
            continue
        k = round(f["largeur"] / 0.05, 3)
        cle = f"{f['modulation']} {int(k) if k == int(k) else k}u"
        if f["modulation"] == "continue":
            continues[cle] = continues.get(cle, 0.0) + (f["s1"] - f["s0"])
        else:
            traits[cle] = traits.get(cle, 0) + 1
    return {"tirets_attendus": sum(len(r["tirets"]) for r in att), "tirets_fabriques": len(fab),
            "manquants": manquants, "en_trop": en_trop, **{k: round(v, 6) for k, v in ecarts.items()},
            "periode_max_m": round(per_max, 6), "trait_max_m": round(trait_max, 6), "derive_max_m": round(derive_max, 6),
            "periodes": n_periodes, "traits": traits, "continues_m": {k: round(v, 3) for k, v in continues.items()},
            "degagements": [(r["cle"], [(round(a, 3), round(b, 3)) for a, b in r["coupes"]]) for r in att if r["coupes"]]}


# ------------------------------------------------------------------------------------------------ gabarits
def _centre_aire_faces(PE, e):
    """Centre de surface (x, y) des faces du dessus de l'entité (triangulation de l'empreinte peinte)."""
    a_tot, c_tot = 0.0, np.zeros(2)
    for i in e["faces"]:
        if PE.dessus_f[i] != 1:
            continue
        q = PE.P[PE.faces[i], :2]
        for k in range(1, len(q) - 1):                       # éventail
            a = 0.5 * float(np.cross(q[k] - q[0], q[k + 1] - q[0]))
            a_tot += a
            c_tot += a * (q[0] + q[k] + q[k + 1]) / 3.0
    return c_tot / a_tot if abs(a_tot) > 1e-12 else None


def _centre_aire_gabarit(anneaux):
    """Centre de surface de la forme attendue (règle pair-impair : un anneau intérieur est un trou)."""
    from functools import reduce
    forme = reduce(lambda u, v: u.symmetric_difference(v), [Polygon(a).buffer(0) for a in anneaux])
    c = forme.centroid
    return np.array([c.x, c.y])


def _ecart_gabarit(anneaux, pts_xy, centre_fabrique=None):
    """(écart max des sommets fabriqués au contour attendu, écart max des sommets attendus au maillage, rotation
    Kabsch (degrés), translation (x, y)) ; contour attendu = réunion des anneaux extérieurs moins les trous.
    Translation : écart des centres de surface (fabriqué : faces du dessus ; attendu : anneaux) quand le centre fabriqué
    est donné, indépendant de la densité du maillage ; sinon ICP point à point."""
    polys = [Polygon(a) for a in anneaux]
    bord = unary_union([p.exterior for p in polys])
    d_out = max((bord.distance(Point(q)) for q in pts_xy), default=1e9)
    att = np.vstack(anneaux)
    tr = cKDTree(pts_xy)
    dd, ii = tr.query(att)
    d_in = float(dd.max())
    # rotation : ICP point à point (Kabsch sur les plus proches sommets fabriqués, itéré jusqu'à stabilité), partant de
    # la translation des centres de surface ; une seule passe sous-estime un déplacement plus grand que l'espacement
    # des sommets du maillage (fût d'une flèche)
    ca = att.mean(0)
    Rm, tv = np.eye(2), np.zeros(2)
    dc = None
    if centre_fabrique is not None:
        dc = np.asarray(centre_fabrique) - _centre_aire_gabarit(anneaux)
        tv = dc.copy()
    for _ in range(200):
        _d, ii = tr.query(att @ Rm.T + tv)
        Q = pts_xy[ii]
        cq = Q.mean(0)
        U, _, Vt = np.linalg.svd((att - ca).T @ (Q - cq))
        Dm = np.diag([1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
        Rn = Vt.T @ Dm @ U.T
        tn = cq - Rn @ ca
        fini = np.abs(Rn - Rm).max() < 1e-12 and np.abs(tn - tv).max() < 1e-10
        Rm, tv = Rn, tn
        if fini:
            break
    ang = math.degrees(math.atan2(Rm[1, 0], Rm[0, 0]))
    return float(d_out), d_in, ang, (dc if dc is not None else (Rm @ ca + tv) - ca)


def ctl_symboles(S, PE, rid):
    R = S.routes[rid]
    out = []
    for x in S.marques(rid):
        if x["type"] not in ("fleche", "symbole", "inscription"):
            continue
        nom = "MQ_" + _ent_nom(x["id"])
        e = PE.ent.get(nom)
        if e is None:
            out.append({"id": x["id"], "absent": True})
            continue
        if x["type"] == "inscription":
            anneaux, info = S.inscription(x, rid)
        else:
            anneaux, info = S.symbole(x, rid)
        d_out, d_in, ang, dxy = _ecart_gabarit(anneaux, PE.P[e["pied"], :2], _centre_aire_faces(PE, e))
        an = x["ancrage"]
        s_o, t_o = S.st_de_xy(R, *(info["o"] + dxy))
        # centrage : sur la limite si l'ancrage y est (flèche à cheval sur une ligne, RF-MQ-RAB-02), sinon milieu de la
        # bande d'ancrage ; triangle du dos-d'âne : milieu de voie ± 0,70 (RF-MQ-RAL-01, trois triangles centrés)
        k, p, T = S.bandes(R, float(an["s"]))
        ids = [b["id"] for b in p["bandes"]]
        sur_limite = min(T, key=lambda v: abs(v - float(an["t"])))
        if abs(sur_limite - float(an["t"])) < 0.01:
            t_ref, ref = sur_limite, "limite"
        else:
            b = ids.index(an["bande"]) if an.get("bande") in ids else None
            t_ref = 0.5 * (T[b] + T[b + 1]) if b is not None else float(an["t"])
            ref = "milieu de voie"
            if x.get("gabarit") == "TRIANGLE_DOS_ANE":
                pas = float(AB.dossier08()["gabarits"]["TRIANGLE_DOS_ANE"]["largeur_m"])
                t_ref = min((t_ref - pas, t_ref, t_ref + pas), key=lambda v: abs(v - float(an["t"])))
                ref = "milieu de voie ± 0,70"
        out.append({"id": x["id"], "type": x["type"], "gabarit": x.get("gabarit"), "s": float(an["s"]),
                    "s_mesure": round(s_o, 4), "t_mesure": round(t_o, 4), "t_attendu": round(t_ref, 4), "reference": ref,
                    "ecart_sommets_fabriques_m": round(d_out, 6), "ecart_sommets_gabarit_m": round(d_in, 6),
                    "rotation_deg": round(ang, 4), "centrage_m": round(abs(t_o - t_ref), 4),
                    "texte": info.get("texte")})
    # figurines
    for f in S.figurines(rid):
        nom = f"MF_{_ent_nom(rid)}_{_ent_nom(f['id'].rsplit('_', 1)[0])}_{f['id'].rsplit('_', 1)[1]}"
        e = PE.ent.get(nom)
        if e is None:
            out.append({"id": f["id"], "absent": True, "type": "figurine"})
            continue
        d_out, d_in, ang, dxy = _ecart_gabarit(f["anneaux"], PE.P[e["pied"], :2], _centre_aire_faces(PE, e))
        k, p, T = S.bandes(R, f["s"])
        b = [bb["id"] for bb in p["bandes"]].index(f["bande"])
        out.append({"id": f["id"], "type": "figurine", "gabarit": "VELO", "s": f["s"], "ecart_sommets_fabriques_m":
                    round(d_out, 6), "ecart_sommets_gabarit_m": round(d_in, 6), "rotation_deg": round(ang, 4),
                    "centrage_m": round(abs(f["t"] + 0.0 - 0.5 * (T[b] + T[b + 1])) + float(np.hypot(*dxy)), 4)})
    return out


def interdistances(S, rid, symb, lignes):
    """Positions des flèches contre les règles : directionnelles (DEF-017 : interdistance 20 m, 3 par voie) ;
    rabattement (RF-MQ-RAB-05 : flèches à L, L − i1, L − i1 − i2 en amont du point de référence : début de la ligne
    continue de la limite qui porte les flèches, sinon milieu de l'oblique continue qui ferme la voie ; L par
    RF-MQ-PS-03 depuis la vitesse de la route, V15 = vitesse limite)."""
    R = S.routes[rid]
    out = []
    par_voie = {}
    for x in S.marques(rid):
        if x["type"] != "fleche":
            continue
        an = x["ancrage"]
        m = next((q for q in symb if q["id"] == x["id"]), None)
        if m is None or m.get("absent"):
            continue
        par_voie.setdefault((x["gabarit"], an.get("bande")), []).append((m["s_mesure"], float(an["t"]), x))
    d17 = regles.valeur("DEF-017")
    tab = {r["L"]: r for r in regles.valeur("RF-MQ-RAB-05", "table")}
    v15 = float(R.route.get("vitesse_kmh") or 50)
    tL = regles.valeur("RF-MQ-PS-03", "V15_vers_L_m")
    L = next(float(tL[k]) for k in sorted(tL, key=int) if v15 <= int(k) + 1e-9)
    for (gab, bande), lst in sorted(par_voie.items(), key=lambda q: str(q[0])):
        lst.sort()
        ss = [q[0] for q in lst]
        if gab.startswith("RAB"):
            s0, t0 = lst[0][0], lst[0][1]
            ref, quoi = None, ""
            for r in lignes:                         # continue sur la limite qui porte la flèche (annonce)
                if r["modulation"] == "continue" and r["s0"] > s0:
                    tl = S.t_cle(R, r["cle"], s0)
                    if tl is not None and abs(tl - t0) < 0.01:
                        ref, quoi = r["s0"], f"début de la continue {r['cle']}"
            if ref is None:                          # oblique continue qui ferme la voie de la flèche
                for r in lignes:
                    if r["modulation"] == "continue" and bande in r["cle"].split("|") and r["s0"] > s0:
                        ref, quoi = 0.5 * (r["s0"] + r["s1"]), f"milieu de l'oblique {r['cle']}"
            if ref is None or int(L) not in tab:
                out.append({"gabarit": gab, "bande": bande, "s": ss, "conforme": False, "regle": "RF-MQ-RAB-05"})
                continue
            t = tab[int(L)]
            att = [ref - L, ref - L + t["i1"], ref - L + t["i1"] + t["i2"]][:len(ss)]
            out.append({"gabarit": gab, "bande": bande, "s": [round(v, 4) for v in ss], "L": L, "reference": quoi,
                        "s_reference": round(ref, 4), "s_attendus": [round(v, 4) for v in att],
                        "ecart_max_m": round(max(abs(a - b) for a, b in zip(att, ss)), 5), "regle": "RF-MQ-RAB-05"})
        else:
            ecarts = [abs((ss[k + 1] - ss[k]) - float(d17["interdistance"])) for k in range(len(ss) - 1)]
            out.append({"gabarit": gab, "bande": bande, "s": [round(v, 4) for v in ss],
                        "interdistances_attendues": [float(d17["interdistance"])] * (len(ss) - 1),
                        "ecart_max_m": round(max(ecarts, default=0.0), 5), "regle": "DEF-017",
                        "nombre": len(ss), "nombre_attendu": int(d17["nombre_par_voie"])})
    return out


# ------------------------------------------------------------------------------------------------ passages, zébras
def ctl_passages(S, PE, rid):
    R = S.routes[rid]
    out = []
    for x in S.marques(rid):
        if x["type"] != "passage_pieton":
            continue
        att = S.passage(x, rid)
        noms = sorted(n for n in PE.ent if n.startswith("MQ_" + _ent_nom(x["id"]) + "_b"))
        bandes = []
        for n in noms:
            st = _st(S, R, PE.P[PE.ent[n]["pied"], :2])
            bandes.append((st[:, 0].min(), st[:, 0].max(), st[:, 1].min(), st[:, 1].max()))
        bandes.sort(key=lambda b: -b[3])
        larg = [b[3] - b[2] for b in bandes]
        gaps = [att["t1"] - bandes[0][3]] + [bandes[k][2] - bandes[k + 1][3] for k in range(len(bandes) - 1)] + \
               [bandes[-1][2] - att["t0"]] if bandes else []
        out.append({"id": x["id"], "s": round(0.5 * (att["s0"] + att["s1"]), 4), "W": round(att["W"], 4),
                    "n_attendu": att["n"], "n_plage_iisr": list(att["n_plage"]), "n_mesure": len(bandes),
                    "e_attendu": round(att["e"], 4), "e_mesures": [round(g, 4) for g in gaps],
                    "e_ecart_max_m": round(max((abs(g - att["e"]) for g in gaps), default=9), 5),
                    "largeur_ecart_max_m": round(max((abs(w - att["bande"]) for w in larg), default=9), 5),
                    "longueur_mesuree": round(max((b[1] - b[0] for b in bandes), default=0), 4),
                    "longueur_attendue": round(att["s1"] - att["s0"], 4),
                    "longueur_ecart_max_m": round(max((max(abs(b[0] - att["s0"]), abs(b[1] - att["s1"]))
                                                       for b in bandes), default=9), 5)})
    return out


def ctl_zebras(S, PE, rid, lignes):
    R = S.routes[rid]
    out = []
    for z in S.zebras(rid, lignes):
        noms = sorted(n for n in PE.ent if n.startswith(f"MZ_{_ent_nom(rid)}_{_ent_nom(z['bande'])}"))
        hach, aplats = [], []
        for n in noms:
            st = _st(S, R, PE.P[PE.ent[n]["pied"], :2])
            (hach if "_hachure" in n else aplats).append((n, st))
        # hachure : arêtes longues de l'enveloppe convexe (s, t) ; angle avec la rive (axe s) ; pas perpendiculaire
        angles, cs = [], []
        sans_angle = []
        ang = math.radians(z["angle"])
        sgs = 1.0
        d = np.array([sgs * math.cos(ang), (1.0 if z["cote_ligne"] > 0 else -1.0) * math.sin(ang)])
        nrm = np.array([-d[1], d[0]])
        for n, st in hach:
            # enveloppe sans ses sommets alignés (le maillage coupe les côtés en segments de quelques centimètres)
            hull = MultiPoint([tuple(q) for q in st]).convex_hull.simplify(1e-5, preserve_topology=False)
            c = np.array(hull.exterior.coords)
            ar = [(a, b) for a, b in zip(c[:-1], c[1:]) if np.hypot(*(b - a)) > 0.3]
            n_avant = len(angles)
            # côtés de la bande : paire d'arêtes parallèles (± 1°) distantes de la largeur de bande (± 5 cm)
            for i in range(len(ar)):
                for j in range(i + 1, len(ar)):
                    (a1, b1), (a2, b2) = ar[i], ar[j]
                    d1, d2 = (b1 - a1) / np.hypot(*(b1 - a1)), (b2 - a2) / np.hypot(*(b2 - a2))
                    if abs(abs(float(d1 @ d2)) - 1.0) > 1.5e-4:
                        continue
                    ecart = abs(float(np.cross(d1, a2 - a1)))
                    if abs(ecart - z["bande_h"]) > 0.05:
                        continue
                    for dd in (d1, d2):
                        angles.append(abs(math.degrees(math.atan2(abs(dd[1]), abs(dd[0])))))
            if len(angles) == n_avant:
                sans_angle.append(n)               # aucune paire de côtés mesurable : hachure non contrôlée en angle
            proj = st @ nrm
            cs.append((proj.min(), proj.max()))
        cs.sort()
        pas = [cs[k + 1][0] - cs[k][0] for k in range(len(cs) - 1)]
        larg = [b - a for a, b in cs]
        out.append({"bande": z["bande"], "zone_s": [round(z["z0"], 3), round(z["z1"], 3)],
                    "aplat_s": [round(z["sa"], 3), round(z["sb"], 3)], "hachures": len(hach), "aplats": len(aplats),
                    "angle_attendu_deg": z["angle"],
                    "angles_mesures_deg": sorted({round(a, 4) for a in angles}),
                    "angle_ecart_max_deg": round(max((abs(a - z["angle"]) for a in angles), default=9), 4),
                    "hachures_sans_angle": sans_angle,
                    "pas_attendu_m": round(z["pas"], 4),
                    "pas_ecart_max_m": round(max((abs(p - z["pas"]) for p in pas[1:-1] or pas), default=0.0), 5),
                    "pas_mesures": [round(p, 4) for p in pas],
                    "largeur_bande_mesures": [round(w, 4) for w in larg]})
    return out


# ------------------------------------------------------------------------------------------------ épaisseur, bordures
def ctl_epaisseur(PE):
    cl = PE.classe_point()
    out = {}
    for nom, e_top, sel in (("lignes", 0.002, cl == "ligne"), ("autres", 0.003, (cl != "ligne") & (cl != ""))):
        m = (PE.dessus == 1) & sel
        v = PE.au[m]
        fsel = np.array([PE.voc["classe"][PE.A[i, 1]] == "ligne" for i in range(len(PE.faces))])
        fm = (PE.dessus_f == 1) & (fsel if nom == "lignes" else ~fsel)
        vc = PE.au_c[fm]
        out[nom] = {"e_top_m": e_top, "sommets": int(m.sum()),
                    "sommets_min_m": round(float(v.min()), 6) if len(v) else None,
                    "sommets_max_m": round(float(v.max()), 6) if len(v) else None,
                    "sommets_ecart_max_m": round(float(np.abs(v - e_top).max()), 6) if len(v) else 0.0,
                    "centres": int(fm.sum()),
                    "centres_ecart_max_m": round(float(np.abs(vc - e_top).max()), 6) if len(vc) else 0.0,
                    "sans_sol": int((v < -1e8).sum())}
    return out


def ctl_bordures(S, PE, rid):
    """Aire de peinture (faces du dessus) dont le centre tombe sur un corps de bordure ou un caniveau (TQ-MQG-014)."""
    R = S.routes[rid]
    aire = 0.0
    n = 0
    for i, f in enumerate(PE.faces):
        if PE.dessus_f[i] != 1:
            continue
        q = PE.P[f]
        c = q[:, :2].mean(0)
        s, t = S.st_de_xy(R, *c)
        if any(lo + 1e-6 < t < hi - 1e-6 for lo, hi in S.zones_interdites(R, s)):
            a = 0.5 * abs(np.cross(q[1, :2] - q[0, :2], q[2, :2] - q[0, :2])) if len(q) == 3 else 0.0
            aire += a
            n += 1
    return {"faces": n, "aire_m2": round(aire, 6)}


# ------------------------------------------------------------------------------------------------ attendus
def ctl_attendus(scene, S, PE, res, dossier):
    import importlib.util                       # lecteur YAML du catalogue (scenes_simples/yaml_simple.py)
    sp = importlib.util.spec_from_file_location("yaml_simple_catalogue",
                                                DEPOT / "recon" / "generateur" / "scenes_simples" / "yaml_simple.py")
    ys = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(ys)
    yaml = next((DEPOT / "recon" / "generateur" / "scenes_simples").glob(f"{scene}_*.yaml"))
    att = ys.charger(yaml).get("attendus") or {}
    rid = S.m["routes"][0]["id"]
    R = S.routes[rid]
    mes = {}
    T0 = AB.A1.t_limites(R.profil(0), 0.0)
    p0 = R.profil(0)
    mes["longueur"] = round(R.L, 3)
    mes["largeur_emprise"] = round(T0[0] - T0[-1], 3)
    chaussee = {"voie_circulation", "voie_bus", "bande_cyclable", "stationnement", "accotement_revetu",
                "bande_derasee"}

    def largeur_chaussee(p, T):
        bs_ = p["bandes"]
        iv = [i for i, b in enumerate(bs_) if b["type"] in ("voie_circulation", "voie_bus")]
        g = iv[0]
        while g - 1 >= 0 and bs_[g - 1]["type"] in chaussee and bs_[g - 1].get("materiau_id") not in AB.A2.VEGETAUX \
                and "bordure" not in p["limites"][g]:
            g -= 1
        d = iv[0]
        while d + 1 < len(bs_) and bs_[d + 1]["type"] in chaussee and bs_[d + 1].get("materiau_id") not in AB.A2.VEGETAUX \
                and "bordure" not in p["limites"][d + 1]:
            d += 1
        return round(T[g] - T[d + 1], 3)

    # largeur courante : celle qui couvre la plus grande longueur de route (milieu de chaque section) ; une avancée
    # de trottoir ou un ralentisseur ponctuel ne la change pas (S03 : 6,00 sur les avancées, 8,00 sur les places)
    cumul = {}
    for sc in R.secs:
        a_, b_ = float(sc["s0"]), float(sc["s1"])
        sm = 0.5 * (a_ + b_)
        w = largeur_chaussee(R.profil(R.section(sm)), AB.A1.t_limites(R.profil(R.section(sm)), sm))
        cumul[w] = cumul.get(w, 0.0) + (b_ - a_)
    mes["largeur_chaussee"] = max(sorted(cumul), key=lambda w: cumul[w])
    mes["largeur_chaussee_par_longueur"] = {str(w): round(x, 3) for w, x in sorted(cumul.items())}
    bs = p0["bandes"]
    v = {}
    for b in bs:
        if b["type"] in ("voie_circulation", "voie_bus"):
            v[b["sens"]] = v.get(b["sens"], 0) + 1
    mes["voies"] = v
    mes["traits"] = res["lignes"]["traits"]
    mes["continues_m"] = {k: round(x) for k, x in res["lignes"]["continues_m"].items()}
    fl = {}
    for q in res["symboles"]:
        if q.get("type") == "fleche" and not q.get("absent"):
            fl[q["gabarit"]] = fl.get(q["gabarit"], 0) + 1
    mes["fleches"] = fl
    mes["fleches_s"] = sorted(round(q["s_mesure"], 2) for q in res["symboles"] if q.get("type") == "fleche")
    mes["triangles"] = sum(1 for q in res["symboles"] if q.get("gabarit") == "TRIANGLE_DOS_ANE" and not q.get("absent"))
    mes["figurines"] = sum(1 for q in res["symboles"] if q.get("type") == "figurine" and not q.get("absent"))
    mes["inscriptions"] = {q["texte"]: 1 for q in res["symboles"] if q.get("type") == "inscription"}
    mes["passages"] = [{"s": p["s"], "W": round(p["W"], 3), "bandes": p["n_mesure"], "e": round(p["e_attendu"], 3),
                        "longueur_bandes": round(p["longueur_mesuree"], 3)} for p in res["passages"]]
    mes["hachures"] = sum(z["hachures"] for z in res["zebras"])
    mes["aplats"] = sum(z["aplats"] for z in res["zebras"])
    # sorties du lot L2 : bordures, arbres, BEV, abaissés
    ent = json.loads((dossier / "l2" / "entites.json").read_text(encoding="utf-8"))
    lb = sum(float(np.hypot(*np.diff(np.array(e["xy"]), axis=0).T).sum()) for e in ent)
    mes["bordures_m_total"] = round(lb, 2)
    v_ = json.loads((dossier / "l2" / "vegetation.json").read_text(encoding="utf-8"))
    mes["arbres"] = len(v_["arbres"] if isinstance(v_, dict) else v_)      # rg_vegetation/0.2 : arbres de l'étape 2
    mes["bev"] = len(json.loads((dossier / "l2" / "bev.json").read_text(encoding="utf-8")))
    # abaissés : tronçons de bordure où la vue mesurée sur la géométrie fabriquée (dessus de l'élément − sol devant la
    # face, mesures_l2.json) est <= 3 cm (abaissé : 2 cm, DEF-031 ; abaissé réalisé par un plateau compris) ; le sommet
    # d'un dos-d'âne de 10 cm sous une bordure de 14 cm laisse 4 cm de vue : ce n'est pas un abaissé (S08)
    ml = json.loads((dossier / "l2" / "mesures_l2.json").read_text(encoding="utf-8"))
    n_ab = 0
    for b in sorted({e["bordure"] for e in ml["elements"]}):
        el = sorted((e["s"], e["z_dessus"] - e["z_devant"]) for e in ml["elements"]
                    if e["bordure"] == b and e["z_dessus"] is not None and e["z_devant"] is not None)
        dedans = False
        for s_, v in el:
            if v <= 0.03 and not dedans:
                n_ab += 1
            dedans = v <= 0.03
    mes["abaisses"] = n_ab
    av = [sc for sc in R.secs if any(b.get("sous_type") == "avancee_trottoir" for b in R.prof[sc["profil"]]["bandes"])]
    pl = [sc for sc in R.secs if any(b["type"] == "stationnement" for b in R.prof[sc["profil"]]["bandes"])]
    mes["avancees"] = len(av)
    mes["places"] = len(pl)
    mes["rayons"] = [round(1 / abs(p.k0), 3) for p in R.ref.prims if p.type == "arc"]
    lig = res["lignes_def"]
    obl = [r for r in lig if r["modulation"] == "continue" and r["cle"].startswith("zh_")]
    if obl:
        o = obl[0]
        pci = min(float(sc["s0"]) for sc in R.secs if any(
            isinstance(b["largeur"], dict) for b in R.prof[sc["profil"]]["bandes"] if b["type"] == "trottoir")) \
            if any(isinstance(b["largeur"], dict) for sc in R.secs for b in R.prof[sc["profil"]]["bandes"]
                   if b["type"] == "trottoir") else None
        mes["oblique"] = {"L": round(o["s1"] - o["s0"], 3), "s0": round(o["s0"], 3), "s1": round(o["s1"], 3),
                          "PCI": pci, "Lp": round(o["s1"] - pci, 3) if pci is not None else None}
    ann = [r for r in lig if r["modulation"] == "T3" and r["cle"] == "v1|v2" and r["largeur"] == 0.1]
    cont = [r for r in lig if r["modulation"] == "continue" and r["cle"] == "v1|v2"]
    if ann and cont:
        mes["annonce"] = {"L": round(cont[0]["s0"] - ann[0]["tirets"][0][0], 3), "s0": round(ann[0]["tirets"][0][0], 3),
                          "s1": round(cont[0]["s0"], 3)}
    # comparaison clé par clé
    comp = {}
    for k, v in att.items():
        if k == "bordures_m":
            tot = sum(v.values()) + sum((att.get("bordures_avancees_m") or {}).values())
            comp[k] = {"attendu": tot, "mesure": mes["bordures_m_total"], "ok": abs(tot - mes["bordures_m_total"]) <= 0.05}
        elif k == "bordures_avancees_m":
            comp[k] = {"attendu": v, "mesure": "compté avec bordures_m (même file)", "ok": True}
        elif k == "passages":
            ok = len(v) == len(mes["passages"]) and all(
                abs(a["s"] - b["s"]) < 0.01 and abs(a["W"] - b["W"]) < 0.01 and a["bandes"] == b["bandes"]
                and abs(a["e"] - b["e"]) < 0.001 and abs(a["longueur_bandes"] - b["longueur_bandes"]) < 0.01
                for a, b in zip(v, mes["passages"]))
            comp[k] = {"attendu": v, "mesure": mes["passages"], "ok": ok}
        elif k == "fleches_s":
            ok = len(v) == len(mes["fleches_s"]) and all(abs(a - b) <= 0.05 for a, b in zip(sorted(v), mes["fleches_s"]))
            comp[k] = {"attendu": sorted(v), "mesure": mes["fleches_s"], "ok": ok}
        elif k in mes:
            m = mes[k]
            if isinstance(v, dict):
                ok = all((abs(float(m.get(kk, -1e9)) - float(vv)) <= 0.05 if isinstance(vv, (int, float)) else
                          m.get(kk) == vv) for kk, vv in v.items() if vv is not None) and \
                     (k not in ("traits", "fleches", "voies", "continues_m", "inscriptions") or set(m) == set(v))
            elif isinstance(v, list):
                ok = len(v) == len(m) and all(abs(float(a) - float(b)) <= 0.05 for a, b in zip(v, m))
            else:
                ok = abs(float(m) - float(v)) <= 0.05
            comp[k] = {"attendu": v, "mesure": m, "ok": bool(ok)}
        else:
            comp[k] = {"attendu": v, "mesure": None, "ok": False, "note": "non mesuré"}
    return comp


# ------------------------------------------------------------------------------------------------ scène
def controler_scene(dossier, peinture=None):
    dossier = Path(dossier)
    S = AB.Scene(dossier)
    PE = peinture or Peinture(dossier / "l2b")
    rid = S.m["routes"][0]["id"]
    lig = ctl_lignes(S, PE, rid)
    symb = ctl_symboles(S, PE, rid)
    res = {"scene": dossier.name, "lignes": lig, "lignes_def": S.lignes(rid), "symboles": symb,
           "passages": ctl_passages(S, PE, rid)}
    res["interdistances"] = interdistances(S, rid, symb, res["lignes_def"])
    res["zebras"] = ctl_zebras(S, PE, rid, res["lignes_def"])
    res["epaisseur"] = ctl_epaisseur(PE)
    res["bordures"] = ctl_bordures(S, PE, rid)
    res["attendus"] = ctl_attendus(dossier.name, S, PE, res, dossier)
    res.pop("lignes_def")
    return res


def bilan(resultats):
    b = {"scenes": len(resultats)}
    L = [r["lignes"] for r in resultats]
    b["tirets"] = {"attendus": sum(x["tirets_attendus"] for x in L), "fabriques": sum(x["tirets_fabriques"] for x in L),
                   "manquants": sum(len(x["manquants"]) for x in L), "en_trop": sum(len(x["en_trop"]) for x in L),
                   "debut_fin_max_m": max(x["debut_fin_max_m"] for x in L), "largeur_max_m": max(x["largeur_max_m"] for x in L),
                   "decentrage_max_m": max(x["decentrage_max_m"] for x in L), "periode_max_m": max(x["periode_max_m"] for x in L),
                   "trait_max_m": max(x["trait_max_m"] for x in L), "derive_max_m": max(x["derive_max_m"] for x in L),
                   "periodes": sum(x["periodes"] for x in L)}
    sy = [q for r in resultats for q in r["symboles"]]
    ok = [q for q in sy if not q.get("absent")]
    b["symboles"] = {"total": len(sy), "absents": len(sy) - len(ok),
                     "ecart_gabarit_max_m": max((max(q["ecart_sommets_fabriques_m"], q["ecart_sommets_gabarit_m"])
                                                 for q in ok), default=0.0),
                     "rotation_max_deg": max((abs(q["rotation_deg"]) for q in ok), default=0.0),
                     "centrage_max_m": max((q["centrage_m"] for q in ok), default=0.0),
                     "par_type": {}}
    for q in ok:
        t = b["symboles"]["par_type"].setdefault(q["type"], 0)
        b["symboles"]["par_type"][q["type"]] = t + 1
    it = [q for r in resultats for q in r["interdistances"]]
    b["interdistances"] = {"series": len(it), "ecart_max_m": max((q.get("ecart_max_m", 9) for q in it), default=0.0),
                           "non_conformes": sum(1 for q in it if q.get("conforme") is False)}
    pp = [q for r in resultats for q in r["passages"]]
    b["passages"] = {"passages": len(pp), "n_conformes": sum(1 for q in pp if q["n_mesure"] == q["n_attendu"]
                                                              and q["n_plage_iisr"][0] <= q["n_mesure"] <= q["n_plage_iisr"][1]),
                     "e_ecart_max_m": max((q["e_ecart_max_m"] for q in pp), default=0.0),
                     "largeur_ecart_max_m": max((q["largeur_ecart_max_m"] for q in pp), default=0.0),
                     "longueur_ecart_max_m": max((q["longueur_ecart_max_m"] for q in pp), default=0.0)}
    zz = [q for r in resultats for q in r["zebras"]]
    b["zebras"] = {"zebras": len(zz), "hachures": sum(q["hachures"] for q in zz), "aplats": sum(q["aplats"] for q in zz),
                   "angle_ecart_max_deg": max((q["angle_ecart_max_deg"] for q in zz), default=0.0),
                   "hachures_sans_angle": sum(len(q["hachures_sans_angle"]) for q in zz),
                   "pas_ecart_max_m": max((q["pas_ecart_max_m"] for q in zz), default=0.0)}
    ep = [r["epaisseur"] for r in resultats]
    b["epaisseur"] = {k: {"sommets": sum(e[k]["sommets"] for e in ep),
                          "sommets_ecart_max_m": max(e[k]["sommets_ecart_max_m"] for e in ep),
                          "centres": sum(e[k]["centres"] for e in ep),
                          "centres_ecart_max_m": max(e[k]["centres_ecart_max_m"] for e in ep),
                          "sans_sol": sum(e[k]["sans_sol"] for e in ep)} for k in ("lignes", "autres")}
    b["bordures"] = {"aire_m2": round(sum(r["bordures"]["aire_m2"] for r in resultats), 6),
                     "faces": sum(r["bordures"]["faces"] for r in resultats)}
    at = [(r["scene"], k, v) for r in resultats for k, v in r["attendus"].items()]
    b["attendus"] = {"cles": len(at), "ok": sum(1 for _, _, v in at if v["ok"]),
                     "scenes_ok": sum(1 for r in resultats if all(v["ok"] for v in r["attendus"].values())),
                     "echecs": [f"{s} {k} : attendu {v['attendu']} mesuré {v['mesure']}" for s, k, v in at if not v["ok"]]}
    return b


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dossiers", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    dossiers = [Path(x) for x in a.dossiers] or [SORTIE / s for s in SCENES]
    res = [controler_scene(d) for d in dossiers]
    b = bilan(res)
    print(json.dumps(b, ensure_ascii=False, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps({"bilan": b, "scenes": res}, ensure_ascii=False, indent=1, default=float) + "\n",
                                encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
