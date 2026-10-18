# -*- coding: utf-8 -*-
"""Contrôles ajoutés par le lot « correction de l'étape 2 » (18/10/2026), sur la géométrie FABRIQUÉE (sol l2/sol_*.npy,
peinture l2b/peinture_*.npy, table des marques, courbes L1), indépendants des HDA :

  CE-1  non-superposition des peintures : aire de recouvrement entre deux entités peintes différentes (faces du dessus)
        ≤ 1e-4 m² par paire ; rapporté par paire de classes et par scène ;
  CE-2  sol sous chaque passage et chaque refuge : aucun point de la traversée (de la première à la dernière bande, refuges
        compris) sur un sol meuble (gazon, herbe, terre, BRF) ;
  CE-3  passages : écart entre la dernière bande de chaque groupe et le bord de la chaussée (face de bordure, bord
        d'îlot ou rive), mesuré sur 5 génératrices le long des bandes : sur l'axe du passage (W « au droit du
        passage ») ≤ e max = 0,80 m (RF-MQ-PP-05) ; sur toutes les génératrices (bords évasés, congés) < 1,50 m = place
        d'une bande de plus (0,50 + 2 × e min, DEF-011) ;
  CE-4  rives peintes continues : sur chaque limite peinte d'une route (autoroutes, route S01), aucun tronçon sans
        peinture plus long que l'intervalle de sa modulation (bouts compris : de la naissance de la limite au premier
        trait, du dernier trait à la fin de la limite).

    python recon/generateur/validation/controler_correction_etape2.py [SCENE ...] [--json SORTIE]
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
OUT = GEN.parents[1] / "recon" / "out" / "generateur"
sys.path.insert(0, str(GEN))
import regles  # noqa: E402

SCENES = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11", "S12", "B01",
          "J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe",
          "G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50", "G3_mini_giratoire_D20",
          "A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres", "A3_bretelle_entree", "A4_bretelle_sortie"]
SEUIL_RECOUVREMENT = 1e-4
MEUBLES = ("gazon", "herbe", "terre", "brf", "paillage")
CHAUSSEE = {"voie_circulation", "bande_cyclable", "zone_neutralisee", "voie_tourne_gauche", "voie_tourne_droite",
            "carrefour_chaussee", "voie_bus", "voie_insertion", "voie_deceleration", "bande_derasee",
            "bande_arret_urgence", "stationnement", "carrefour_accotement", "accotement", "musoir"}
E_MAX = float(regles.valeur("RF-MQ-PP-05", "formule") and 0.80)    # e dans [0,50 ; 0,80] (RF-MQ-PP-05, DEF-011)


def _r(x, n=4):
    return None if x is None else round(float(x), n)


# ------------------------------------------------------------------------------------------------ maillages
class Maillage:
    """Sol ou peinture fabriqués (npy) : triangles en éventail, index par grille pour les sondes verticales."""

    def __init__(self, scene, quoi="sol", pas=2.0):
        d = OUT / scene / ("l2" if quoi == "sol" else "l2b")
        p = "sol" if quoi == "sol" else "peinture"
        self.P = np.load(d / f"{p}_points.npy")
        F = np.load(d / f"{p}_faces.npy")
        C = np.load(d / f"{p}_comptes.npy")
        self.A = np.load(d / f"{p}_attributs.npy")
        self.voc = json.loads((d / f"{p}_vocabulaire.json").read_text(encoding="utf-8"))
        self.off = np.concatenate([[0], np.cumsum(C)])
        self.F, self.C = F, C
        tris, fid = [], []
        for k in range(3, int(C.max()) + 1):
            sel = np.where(C == k)[0]
            for j in range(1, k - 1):
                tris.append(np.stack([F[self.off[sel]], F[self.off[sel] + j], F[self.off[sel] + j + 1]], 1))
                fid.append(sel)
        self.T = np.concatenate(tris)
        self.fid = np.concatenate(fid)
        self.tx = self.P[:, :2][self.T]
        self.bmin = self.tx.min(1)
        self.bmax = self.tx.max(1)
        self.pas = pas
        self.o = self.bmin.min(0)
        i0 = np.floor((self.bmin - self.o) / pas).astype(int)
        i1 = np.floor((self.bmax - self.o) / pas).astype(int)
        # index par grille (vectorisé) : chaque triangle inscrit dans toutes les cases de sa boîte
        ts, ks = [], []
        dx = i1[:, 0] - i0[:, 0]
        dy = i1[:, 1] - i0[:, 1]
        for a in range(int(dx.max()) + 1):
            for b in range(int(dy.max()) + 1):
                sel = np.where((dx >= a) & (dy >= b))[0]
                ts.append(sel)
                ks.append((i0[sel, 0] + a) * 1000003 + (i0[sel, 1] + b))
        ts = np.concatenate(ts)
        ks = np.concatenate(ks)
        o = np.argsort(ks, kind="stable")
        ts, ks = ts[o], ks[o]
        u, st = np.unique(ks, return_index=True)
        en = np.append(st[1:], len(ks))
        self.grille = {int(k): ts[a:b] for k, a, b in zip(u, st, en)}

    def attr(self, f, col):
        i = self.voc["colonnes"].index(col)
        v = self.A[f, i]
        lst = self.voc.get(col)
        return lst[v] if isinstance(lst, list) and 0 <= v < len(lst) else int(v)

    def sonde(self, x, y):
        """Face la plus haute sous (x, y) : (z, face) ou None."""
        k = int(math.floor((x - self.o[0]) / self.pas)) * 1000003 + int(math.floor((y - self.o[1]) / self.pas))
        cand = self.grille.get(k)
        if cand is None:
            return None
        best = None
        for t in cand:
            a, b, c = self.tx[t]
            v0, v1, v2 = b - a, c - a, np.array([x, y]) - a
            den = v0[0] * v1[1] - v1[0] * v0[1]
            if abs(den) < 1e-14:
                continue
            u = (v2[0] * v1[1] - v1[0] * v2[1]) / den
            w = (v0[0] * v2[1] - v2[0] * v0[1]) / den
            if u >= -1e-9 and w >= -1e-9 and u + w <= 1 + 1e-9:
                z = self.P[self.T[t][0], 2] * (1 - u - w) + self.P[self.T[t][1], 2] * u + self.P[self.T[t][2], 2] * w
                if best is None or z > best[0]:
                    best = (z, int(self.fid[t]))
        return best


def peinture_dessus(scene):
    """Polygones du dessus de chaque entité peinte : {(entité, classe): MultiPolygon}."""
    d = OUT / scene / "l2b"
    P = np.load(d / "peinture_points.npy")
    F = np.load(d / "peinture_faces.npy")
    C = np.load(d / "peinture_comptes.npy")
    A = np.load(d / "peinture_attributs.npy")
    voc = json.loads((d / "peinture_vocabulaire.json").read_text(encoding="utf-8"))
    off = np.concatenate([[0], np.cumsum(C)])
    ent = np.array(voc["pj_entite"])[A[:, 0]]
    cl = np.array(voc["classe"])[A[:, 1]]
    g = collections.defaultdict(list)
    for i in range(len(C)):
        q = P[F[off[i]:off[i + 1]]]
        n = np.cross(q[1] - q[0], q[2] - q[0])
        if abs(n[2]) <= 0.9 * np.linalg.norm(n):
            continue
        pg = Polygon(q[:, :2])
        if pg.is_valid and pg.area > 1e-8:
            g[(str(ent[i]), str(cl[i]))].append(pg)
    return {k: unary_union(v) for k, v in g.items()}


# ------------------------------------------------------------------------------------------------ CE-1
def jonction_prevue(a, b, gab, bifurcation=False):
    """Superpositions prévues (exclues de CE-1, rapportées à part) : flèche de rabattement « à cheval sur la ligne
    d'annonce » (IISR7 115-3 B p. 21, dossier 08 § flèches de rabattement) ; à une bifurcation d'autoroute, bouts de deux
    lignes de rive de deux routes différentes qui se prolongent l'une l'autre au point de jonction (rive de la bretelle →
    rive de la voie d'insertion)."""
    (ea, ca), (eb, cb) = a, b
    if bifurcation and ca == cb == "ligne" and ea.startswith("ML_R_") and eb.startswith("ML_R_") and             ea.split("_")[2] != eb.split("_")[2]:
        return "raccord des rives de deux routes au point de jonction d'une bifurcation"
    for (e1, c1), (e2, c2) in (((ea, ca), (eb, cb)), ((eb, cb), (ea, ca))):
        if c1 == "fleche" and c2 == "ligne" and str(gab.get(e1, "")).startswith("RAB"):
            return "flèche de rabattement à cheval sur la ligne d'annonce (IISR7 115-3 B)"
    return None


def ce1_recouvrements(G, gab=None, bifurcation=False):
    gab = gab or {}
    keys = list(G)
    geoms = [G[k] for k in keys]
    tree = STRtree(geoms)
    par = collections.Counter()
    ex = collections.defaultdict(list)
    prevues = []
    for i, k in enumerate(keys):
        for j in tree.query(geoms[i]):
            if j <= i:
                continue
            a = geoms[i].intersection(geoms[j]).area
            if a > SEUIL_RECOUVREMENT:
                jp = jonction_prevue(k, keys[j], gab, bifurcation)
                if jp:
                    prevues.append([k[0], keys[j][0], _r(a, 4), jp])
                    continue
                p = " / ".join(sorted((k[1], keys[j][1])))
                par[p] += a
                ex[p].append([k[0], keys[j][0], _r(a, 4)])
    return {"paires_au_dessus_du_seuil": sum(len(v) for v in ex.values()),
            "aire_totale_m2": _r(sum(par.values()), 4),
            "par_classes": {p: {"aire_m2": _r(a, 4), "paires": len(ex[p]), "exemples": ex[p][:4]}
                            for p, a in par.most_common()},
            "jonctions_prevues": prevues}


# ------------------------------------------------------------------------------------------------ passages
def groupes_passages(G):
    """Bandes de passage regroupées par passage (entité MQ_<id>_bNN) : {passage: [polygones]}."""
    out = collections.defaultdict(list)
    for (e, c), g in G.items():
        if c != "passage":
            continue
        base = re.sub(r"_(b\d+|x[gd]\d+)$", "", e)      # bandes de rg::marquages (bNN) et prolongements (xgNN, xdNN)
        for p in getattr(g, "geoms", [g]):
            out[base].append(p)
    return out


def repere_bandes(polys):
    """Repère du passage : u le long des bandes (sens de la route), v en travers (sens de la traversée)."""
    pts = np.concatenate([np.array(p.exterior.coords) for p in polys])
    rr = [p.minimum_rotated_rectangle for p in polys]
    angs = []
    for r in rr:
        c = np.array(r.exterior.coords)
        e1, e2 = c[1] - c[0], c[2] - c[1]
        e = e1 if np.linalg.norm(e1) >= np.linalg.norm(e2) else e2
        a = math.atan2(e[1], e[0]) % math.pi
        angs.append(a)
    a = float(np.median(angs))
    u = np.array([math.cos(a), math.sin(a)])
    v = np.array([-u[1], u[0]])
    c0 = pts.mean(0)
    return c0, u, v


def ce2_ce3(scene, G, sol):
    """CE-2 et CE-3 sur chaque passage : génératrices le long des bandes (5 positions) ; sur chacune, intervalles peints
    réels (bandes découpées comprises) ; groupes séparés par plus de 1,0 m (refuge, îlot)."""
    gp = groupes_passages(G)
    res = []
    i_cl = sol.voc["colonnes"].index("classe")
    i_mat = sol.voc["colonnes"].index("materiau_id")

    def classe_mat(x, y):
        s_ = sol.sonde(x, y)
        if s_ is None:
            return None, None
        f = s_[1]
        return sol.voc["classe"][sol.A[f, i_cl]], sol.voc["materiau_id"][sol.A[f, i_mat]]
    for pid, polys in sorted(gp.items()):
        c0, u, v = repere_bandes(polys)
        U = [np.array(p.exterior.coords) @ u for p in polys]
        u0 = float(np.median([x.min() for x in U]))
        u1 = float(np.median([x.max() for x in U]))
        union = unary_union(polys)
        gens = [u0 + (u1 - u0) * f for f in (0.05, 0.275, 0.5, 0.725, 0.95)]
        meubles, ecarts, ecarts_axe = [], [], []
        ngr = 0
        for ig, uu in enumerate(gens):
            ligne = LineString([tuple(uu * u - 60.0 * v), tuple(uu * u + 60.0 * v)])
            inter = ligne.intersection(union)
            segs = [g for g in getattr(inter, "geoms", [inter]) if g.length > 1e-6]
            iv = sorted((min(float(np.dot(c, v)) for c in g.coords), max(float(np.dot(c, v)) for c in g.coords)) for g in segs)
            if not iv:
                continue
            grp = [[iv[0]]]
            for b in iv[1:]:
                if b[0] - grp[-1][-1][1] > 1.0:
                    grp.append([b])
                else:
                    grp[-1].append(b)
            ngr = max(ngr, len(grp))
            vmin, vmax = iv[0][0], iv[-1][1]
            # CE-2 : sol sous toute la traversée (bandes et refuges)
            nv = max(2, int((vmax - vmin) / 0.10))
            for k in range(nv + 1):
                vv = vmin + (vmax - vmin) * k / nv
                p = uu * u + vv * v
                cl, mat = classe_mat(p[0], p[1])
                if mat is not None and any(m in mat for m in MEUBLES):
                    meubles.append([_r(p[0], 2), _r(p[1], 2), cl, mat])
            # CE-3 : écart de chaque bout de groupe au bord de la chaussée
            for g in grp:
                for bout, sens in ((g[0][0], -1.0), (g[-1][1], 1.0)):
                    d = 0.0
                    bord = None
                    while d < 6.0:
                        d += 0.02
                        p = uu * u + (bout + sens * d) * v
                        cl, mat = classe_mat(p[0], p[1])
                        if cl is None or cl not in CHAUSSEE:
                            bord = d
                            break
                    e_ = bord if bord is not None else 6.0
                    ecarts.append(e_)
                    if ig == 2:
                        ecarts_axe.append(e_)
        res.append({"passage": pid, "groupes": ngr, "bandes": len(polys),
                    "points_meubles": len(meubles), "exemples_meubles": meubles[:3],
                    "ecart_max_m": _r(max(ecarts), 3) if ecarts else None,
                    "ecart_min_m": _r(min(ecarts), 3) if ecarts else None,
                    "ecart_axe_max_m": _r(max(ecarts_axe), 3) if ecarts_axe else None})
    return res


# ------------------------------------------------------------------------------------------------ CE-4
def intervalles_modulation():
    out = {"continue": 0.0}
    for m in ("T1", "T'1", "T2", "T'2", "T3", "T'3", "T4"):
        out[m] = float(regles.regle("RF-MQ-MOD-" + m)["valeurs"]["intervalle"])
    return out


def ce4_rives(scene):
    INT = intervalles_modulation()
    cc = json.loads((OUT / scene / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    tab = json.loads((OUT / scene / "l2b" / "table_marques.json").read_text(encoding="utf-8"))["marques"]
    norm = lambda k: k.replace("^|", "|").replace("|$", "|")  # noqa: E731
    exist = collections.defaultdict(list)
    for r in cc["routes"]:
        for sec in r["sections"]:
            for lim in sec["limites"]:
                if "marquage" in lim["nature"]:
                    exist[(r["id"], norm(lim["cle"]))].append((sec["s0"], sec["s1"]))
    pieces = collections.defaultdict(list)
    mods = collections.defaultdict(set)
    for m in tab:
        if m["classe"] != "ligne":
            continue
        k = (m["route"], norm(m["cle"]))
        pieces[k].append((m["s0"], m["s1"]))
        mods[k].add(m["modulation"])
    pire, cas = 0.0, []
    for k, ivs in exist.items():
        ivs.sort()
        runs = [list(ivs[0])]
        for a, b in ivs[1:]:
            if a - runs[-1][1] < 1e-6:
                runs[-1][1] = b
            else:
                runs.append([a, b])
        pc = sorted(pieces.get(k, []))
        tol = max(INT.get(m, 0.0) for m in mods.get(k, {"continue"}))
        for a, b in runs:
            pp = [(max(x, a), min(y, b)) for x, y in pc if y > a + 1e-6 and x < b - 1e-6]
            trous = []
            cur = a
            for x, y in pp:
                if x - cur > 1e-6:
                    trous.append((cur, x))
                cur = max(cur, y)
            if b - cur > 1e-6:
                trous.append((cur, b))
            for x, y in trous:
                ecart = (y - x) - tol
                if ecart > 0.01:
                    cas.append({"route": k[0], "limite": k[1], "de": _r(x, 2), "a": _r(y, 2), "longueur_m": _r(y - x, 2),
                                "intervalle_m": tol, "modulations": sorted(mods.get(k, []))})
                    pire = max(pire, y - x - tol)
    return {"limites": len(exist), "trous_au_dela_de_l_intervalle": len(cas), "exces_max_m": _r(pire, 2), "cas": cas[:10]}


# ------------------------------------------------------------------------------------------------ CE-5
def ce5_tag_meme_phase(scene):
    """Carrefours à feux (lot L4) : croisements entre deux TAG servis dans une même phase (trajectoires finales)."""
    f = OUT / scene / "l4" / "conflits.json"
    if not f.exists():
        return None
    conf = json.loads(f.read_text(encoding="utf-8"))["conflits"]
    tr = {t["id"]: t for t in json.loads((OUT / scene / "l4" / "trajectoires.json").read_text(encoding="utf-8"))["trajectoires"]}
    cas = [[k["a"], k["b"]] for k in conf if k["type"] == "croisement" and k.get("meme_phase")
           and tr.get(k["a"], {}).get("mouvement") == "TAG" and tr.get(k["b"], {}).get("mouvement") == "TAG"]
    phases = sorted({p for t in tr.values() for p in (t.get("phases") or [])})
    return {"phases": phases, "croisements_TAG_meme_phase": len(cas), "cas": cas}


# ------------------------------------------------------------------------------------------------ principal
def controler(scene, rives=False):
    G = peinture_dessus(scene)
    tab = json.loads((OUT / scene / "l2b" / "table_marques.json").read_text(encoding="utf-8"))["marques"]
    gab = {m["id"]: m.get("gabarit", "") for m in tab}
    gab.update({"MQ_" + re.sub("[^A-Za-z0-9]", "_", m["id"]): m.get("gabarit", "") for m in tab})
    bif = (OUT / scene / "autoroute" / "musoirs.json").exists() and bool(
        json.loads((OUT / scene / "autoroute" / "musoirs.json").read_text(encoding="utf-8")).get("musoirs"))
    r = {"scene": scene, "CE-1": ce1_recouvrements(G, gab, bif)}
    c5 = ce5_tag_meme_phase(scene)
    if c5 is not None:
        r["CE-5"] = c5
    if any(c == "passage" for _, c in G):
        sol = Maillage(scene, "sol")
        r["passages"] = ce2_ce3(scene, G, sol)
    else:
        r["passages"] = []
    if rives:
        r["CE-4"] = ce4_rives(scene)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    ap.add_argument("--sortie", help="dossier des scènes (défaut recon/out/generateur)")
    a = ap.parse_args()
    global OUT
    if a.sortie:
        OUT = Path(a.sortie)
    scenes = a.scenes or SCENES
    out = []
    for s in scenes:
        if not (OUT / s / "l2b").exists():
            print(s, ": absente")
            continue
        rv = s.startswith("A") or s == "S01"
        r = controler(s, rives=rv)
        out.append(r)
        c1 = r["CE-1"]
        pm = sum(p["points_meubles"] for p in r["passages"])
        em = max((p["ecart_max_m"] for p in r["passages"] if p["ecart_max_m"] is not None), default=None)
        ea = max((p["ecart_axe_max_m"] for p in r["passages"] if p["ecart_axe_max_m"] is not None), default=None)
        print(f"{s} : CE-1 {c1['paires_au_dessus_du_seuil']} paires, {c1['aire_totale_m2']} m² "
              f"{list(c1['par_classes'])[:3]} ; passages {len(r['passages'])}, CE-2 points meubles {pm}, CE-3 écart axe {ea} / toutes génératrices {em}"
              + (f" ; CE-4 trous {r['CE-4']['trous_au_dela_de_l_intervalle']}" if "CE-4" in r else "")
              + (f" ; CE-5 TAG croisés même phase {r['CE-5']['croisements_TAG_meme_phase']}" if "CE-5" in r else ""))
    if a.json:
        Path(a.json).write_text(json.dumps({"schema": "controles_correction_etape2/0.1", "scenes": out},
                                           ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
