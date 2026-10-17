# -*- coding: utf-8 -*-
"""Marquages analytiques de référence du lot L2b (contrôle indépendant de rg::marquages et de pj::marquage_solide).

Aucun code commun avec les HDA (VEX) : ce module relit le modèle `modele_voie/0.1`, les règles fusionnées
(`regles_route_fr.json` : RF-MQ-MOD-* modulations, DEF-011 / RF-MQ-PP-05 passages, DEF-020 hachures, RF-MQ-MUS-01,
RF-MQ-RAB-05, DEF-017) et les gabarits du dossier 08 directement (`D:/DocRoute/08_…/marquages_iisr7.json`, et non le
fichier dérivé lu par l'HDA), puis recalcule, avec la géométrie analytique des lots L1 et L2 (`analytique_L1`,
`analytique_L2` : référence, limites, bordures et caniveaux) :
  - les tirets attendus de chaque ligne (intervalles et interruptions du modèle, tronçons d'une section à l'autre,
    dégagement de 2u entre lignes qui convergent, phase « chaque tronçon commence par un trait, trait tronqué gardé
    s'il fait au moins la moitié d'un trait » : choix [G] du catalogue) ;
  - les bandes des passages (n maximal, e = (W − 0,5 n)/(n + 1)) ;
  - les gabarits posés (flèches, triangles, figurines, lettres) et la zone et les hachures des zébras ;
  - les zones interdites à la peinture (corps des bordures, caniveaux posés : MQ-DET-010, TQ-MQG-014).
Conventions : s abscisse de la ligne de référence, t positif à gauche, (x, y) locaux.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent))
import analytique_L1 as A1  # noqa: E402
import analytique_L2 as A2  # noqa: E402
import regles  # noqa: E402

DOSSIER_08 = Path(r"D:\DocRoute\08_Marquages_Geometrie_IISR7\marquages_iisr7.json")
FRACTION = 0.5            # [G] catalogue (scenes_simples/description.py, FRACTION_TRAIT_TRONQUE)
DEG_U = 2.0               # RF-MQ-MUS-01
E_MIN_PP = 0.5            # RF-MQ-PP-05


def modulations():
    out = {}
    for m in ("T1", "T'1", "T2", "T'2", "T3", "T'3", "T4"):
        v = regles.valeur(f"RF-MQ-MOD-{m}")
        out[m] = (float(v["trait"]), float(v["intervalle"]))
    return out


_D08 = {}


def dossier08():
    if "d" not in _D08:
        _D08["d"] = json.loads(DOSSIER_08.read_text(encoding="utf-8"))
    return _D08["d"]


def gabarit_anneaux(nom):
    """Anneaux (liste de polygones (N, 2)) d'un gabarit du dossier 08 : extérieur, trous, parties."""
    g = dossier08()["gabarits"][nom]
    out = [np.array(g["polygone"], float)]
    out += [np.array(t, float) for t in g.get("trous", []) or []]
    parts = g.get("parties")
    if isinstance(parts, list):
        out += [np.array(p, float) for p in parts]
    return out, g


def glyphe(car, serie="V<=70"):
    return dossier08()["glyphes"]["series"][serie][car]


def soustraire(iv, c0, c1):
    out = []
    for a, b in iv:
        if b <= c0 + 1e-9 or a >= c1 - 1e-9:
            out.append((a, b))
            continue
        if c0 - a > 1e-6:
            out.append((a, c0))
        if b - c1 > 1e-6:
            out.append((c1, b))
    return out


class Scene:
    def __init__(self, dossier_scene):
        self.dossier = Path(dossier_scene)
        self.m = A2.charger(self.dossier)
        self.routes = {r["id"]: A2.Route(self.m, r["id"]) for r in self.m["routes"]}
        self.mods = modulations()

    # ------------------------------------------------------------------------------------ géométrie
    def bandes(self, R, s):
        k = R.section(s)
        p = R.profil(k)
        return k, p, A1.t_limites(p, s)

    def cle(self, p, l):
        ids = [b["id"] for b in p["bandes"]]
        return (ids[l - 1] if l > 0 else "^") + "|" + (ids[l] if l < len(ids) else "$")

    def t_cle(self, R, cle, s):
        """t de la limite de clé « bande gauche|bande droite » en s (None si absente)."""
        k, p, T = self.bandes(R, s)
        for l in range(len(T)):
            if self.cle(p, l) == cle:
                return T[l]
        return None

    def largeur_bande(self, R, bande, s):
        k, p, T = self.bandes(R, s)
        ids = [b["id"] for b in p["bandes"]]
        if bande not in ids:
            return None
        i = ids.index(bande)
        return T[i] - T[i + 1]

    def zones_interdites(self, R, s):
        """Intervalles de t [lo, hi] interdits à la peinture en s : corps des bordures réelles (côté haut, base du
        profil), caniveaux posés (côté bas, largeur du profil)."""
        k = R.section(s)
        p = R.profil(k)
        T = A1.t_limites(p, s)
        out = []
        for l, lim in enumerate(p["limites"]):
            bo = lim.get("bordure")
            if not bo or l == 0 or l == len(p["bandes"]):
                continue
            base, H, dh = R.pb[bo["profil"]]
            can = (bo.get("caniveau") or {}).get("profil")
            wc = R.pb[can][0] if can and can != "aucun" and R.caniveau_pose(s) else 0.0
            if bo["cote_haut"] == "gauche":
                out.append((T[l] - wc, T[l] + base))
            else:
                out.append((T[l] - base, T[l] + wc))
        return out

    # ------------------------------------------------------------------------------------ lignes
    def lignes(self, rid):
        """Tronçons attendus : [{cle, modulation, largeur, u, continue, s0, s1, tirets: [(a, b)]}]."""
        R = self.routes[rid]
        morceaux = []
        for k, sc in enumerate(R.secs):
            p = R.prof[sc["profil"]]
            for l, lim in enumerate(p["limites"]):
                if "bordure" in lim or not lim.get("marquages"):
                    continue
                cle = self.cle(p, l)
                for e in lim["marquages"]:
                    a, b = float(sc["s0"]), float(sc["s1"])
                    if e.get("intervalle"):
                        a, b = max(a, float(e["intervalle"]["s0"])), min(b, float(e["intervalle"]["s1"]))
                    if b - a <= 1e-6:
                        continue
                    ivs = [(a, b)]
                    for it in e.get("interruptions", []) or []:
                        ivs = soustraire(ivs, float(it["s0"]), float(it["s1"]))
                    u = float(e.get("u_m", 0.05))
                    w = float(e["largeur_u"]) * u
                    for x0, x1 in ivs:
                        morceaux.append({"cle": cle, "modulation": e["modulation"], "largeur": w, "u": u,
                                         "couleur": e.get("couleur", "blanc"), "s0": x0, "s1": x1})
        morceaux.sort(key=lambda m: (m["cle"], m["modulation"], round(m["largeur"], 6), m["couleur"], m["s0"]))
        runs = []
        for m in morceaux:
            r = runs[-1] if runs else None
            if r and (r["cle"], r["modulation"], round(r["largeur"], 6), r["couleur"]) == \
                    (m["cle"], m["modulation"], round(m["largeur"], 6), m["couleur"]) and m["s0"] <= r["s1"] + 1e-6:
                r["s1"] = max(r["s1"], m["s1"])
            else:
                runs.append(dict(m))
        # dégagement entre lignes qui convergent ([G], RF-MQ-MUS-01 par analogie)
        coupes = {i: [] for i in range(len(runs))}
        for i, ri in enumerate(runs):
            gi, di = ri["cle"].split("|")
            for j, rj in enumerate(runs):
                if i == j:
                    continue
                a, b = max(ri["s0"], rj["s0"]), min(ri["s1"], rj["s1"])
                if b - a <= 1e-6:
                    continue
                gj, dj = rj["cle"].split("|")
                bande = di if gj == di else (gi if dj == gi else None)
                if bande in (None, "^", "$"):
                    continue
                ci, cj = ri["modulation"] == "continue", rj["modulation"] == "continue"
                if not ((not ci and cj) or (ci == cj and ri["largeur"] <= rj["largeur"] + 1e-9)):
                    continue
                marge = 0.5 * (ri["largeur"] + rj["largeur"]) + DEG_U * ri["u"]

                def c(x):
                    wb = self.largeur_bande(self.routes[rid], bande, x)
                    return 1e9 if wb is None else wb - marge
                xs = np.linspace(a, b, max(2, int(math.ceil((b - a) / 0.01)) + 1))
                cs = np.array([c(x) for x in xs])
                neg = cs < 0
                if not neg.any():
                    continue
                k = 0
                while k < len(xs):
                    if not neg[k]:
                        k += 1
                        continue
                    k0 = k
                    while k < len(xs) and neg[k]:
                        k += 1
                    lo = a if k0 == 0 else self._zero(c, xs[k0 - 1], xs[k0])
                    hi = b if k >= len(xs) else self._zero(c, xs[k - 1], xs[k])
                    coupes[i].append((lo, hi))
        out = []
        for i, r in enumerate(runs):
            ivs = [(r["s0"], r["s1"])]
            for c0, c1 in coupes[i]:
                ivs = soustraire(ivs, c0, c1)
            tir = []
            if r["modulation"] == "continue":
                tir = list(ivs)
            else:
                tr, vi = self.mods[r["modulation"]]
                for a, b in ivs:
                    x = a
                    while x < b - 1e-9:
                        fin = min(x + tr, b)
                        if fin - x >= FRACTION * tr - 1e-6:
                            tir.append((x, fin))
                        x += tr + vi
            out.append(dict(r, tirets=tir, coupes=coupes[i]))
        return out

    @staticmethod
    def _zero(f, a, b):
        fa = f(a)
        for _ in range(60):
            m = 0.5 * (a + b)
            fm = f(m)
            if (fm < 0) == (fa < 0):
                a, fa = m, fm
            else:
                b = m
        return 0.5 * (a + b)

    # ------------------------------------------------------------------------------------ ponctuels
    def marques(self, rid):
        return [x for x in self.m.get("marquages", []) if (x.get("ancrage") or {}).get("route") == rid]

    def passage(self, x, rid):
        """Zone du passage (s, t), W, n, e et bandes attendues [(s0, s1, t_bas, t_haut)]."""
        R = self.routes[rid]
        o = R.origine
        ext = x["geometrie"]["exterieur"]
        st = [self.st_de_xy(R, q[0] - o[0], q[1] - o[1]) for q in ext]
        s0, s1 = min(p[0] for p in st), max(p[0] for p in st)
        t0, t1 = min(p[1] for p in st), max(p[1] for p in st)
        d11 = regles.valeur("DEF-011")
        bande = float(d11["bande"])
        W = t1 - t0
        n = int(math.floor((W - E_MIN_PP) / (bande + E_MIN_PP) + 1e-9))
        e = (W - bande * n) / (n + 1)
        bandes = [(s0, s1, t1 - e - q * (bande + e) - bande, t1 - e - q * (bande + e)) for q in range(n)]
        nmin = math.ceil((W - 0.80) / 1.30)
        nmax = math.floor((W - 0.50) / 1.00)
        return {"s0": s0, "s1": s1, "t0": t0, "t1": t1, "W": W, "n": n, "e": e, "bande": bande, "bandes": bandes,
                "n_plage": (nmin, nmax)}

    def pose(self, R, s, t, cap_deg):
        x, y = R.ref.point_st(s, t)
        c = math.radians(cap_deg)
        ey = np.array([math.cos(c), math.sin(c)])
        ex = np.array([ey[1], -ey[0]])
        return np.array([x, y]), ex, ey

    def symbole(self, x, rid):
        """Anneaux attendus (x, y) d'une flèche ou d'un symbole (gabarit du dossier 08 posé à l'ancrage et au cap)."""
        R = self.routes[rid]
        an = x["ancrage"]
        o, ex, ey = self.pose(R, float(an["s"]), float(an["t"]), float(an["cap_deg"]))
        anneaux, g = gabarit_anneaux(x["gabarit"])
        return [o + a[:, :1] * ex + a[:, 1:2] * ey for a in anneaux], {"o": o, "ex": ex, "ey": ey, "gabarit": g}

    def inscription(self, x, rid):
        R = self.routes[rid]
        an = x["ancrage"]
        xo = x.get("x-opendrive") or {}
        texte = xo.get("texte") or x["gabarit"].replace("TEXTE_", "")
        h = float(xo.get("hauteur_lettres_m", 1.5))
        serie = "V<=70" if h <= 1.5 + 1e-9 else "V>70"
        esp = 0.15                                                  # IISR7 annexe D.2 (dossier 08, glyphes.repere)
        larg = [float(glyphe(c, serie)["largeur_m"]) for c in texte]
        tot = sum(larg) + esp * (len(texte) - 1)
        o, ex, ey = self.pose(R, float(an["s"]), float(an["t"]), float(an["cap_deg"]))
        anneaux = []
        xg = -tot / 2
        for c, lw in zip(texte, larg):
            for part in glyphe(c, serie)["parties"]:
                for a in [part["exterieur"]] + list(part.get("trous", []) or []):
                    a = np.array(a, float)
                    anneaux.append(o + (a[:, :1] + xg) * ex + a[:, 1:2] * ey)
            xg += lw + esp
        return anneaux, {"texte": texte, "largeur_totale": tot, "o": o}

    def figurines(self, rid):
        """[(id, s, t, cap, anneaux)] des figurines des objets le long des bandes (ancrage au milieu)."""
        R = self.routes[rid]
        out = []
        for k, sc in enumerate(R.secs):
            p = R.prof[sc["profil"]]
            for b, bd in enumerate(p["bandes"]):
                for ob in bd.get("objets_le_long", []) or []:
                    if ob.get("famille") != "symbole_sol":
                        continue
                    if ob.get("mode") == "points":
                        ss = [float(v) for v in ob["s_points"]]
                    else:
                        ss = [float(ob.get("phase_m", 0.0)) + j * float(ob["pas_m"]) for j in range(100000)
                              if float(ob.get("phase_m", 0.0)) + j * float(ob["pas_m"]) <= R.L]
                    dernier = k == len(R.secs) - 1
                    for j, s in enumerate(ss):
                        if s < sc["s0"] - 1e-9 or s > sc["s1"] + 1e-9 or (not dernier and s >= sc["s1"] - 1e-9):
                            continue
                        T = A1.t_limites(p, s)
                        t = 0.5 * (T[b] + T[b + 1]) + float((ob.get("ancrage") or {}).get("decalage_m", 0.0))
                        _, _, th, _ = R.ref.eval(s)
                        cap = math.degrees(th) + (180.0 if bd.get("sens") == "arriere" else 0.0)
                        anneaux, g = gabarit_anneaux(ob.get("gabarit", "VELO"))
                        o, ex, ey = self.pose(R, s, t, cap)
                        o = o - 0.5 * float(g["longueur_m"]) * ey
                        out.append({"id": f"{ob.get('id', 'fig')}_{j:03d}", "s": s, "t": t, "cap": cap,
                                    "anneaux": [o + a[:, :1] * ex + a[:, 1:2] * ey for a in anneaux], "bande": bd["id"]})
        return out

    # ------------------------------------------------------------------------------------ zébras
    def zebras(self, rid, lignes):
        """Zone hachurable, aplats et hachures attendus des bandes zone_neutralisee / hachures (DEF-020)."""
        R = self.routes[rid]
        d20 = regles.valeur("DEF-020")
        bande_h, esp, ang, aplat = (float(d20["bande"]), float(d20["espacement"]), float(d20["angle_rive_deg"]),
                                    float(d20["aplat_si_largeur_inf"]))
        out = []
        zb = sorted({b["id"] for sc in R.secs for b in R.prof[sc["profil"]]["bandes"]
                     if b["type"] == "zone_neutralisee" and b.get("sous_type") == "hachures"})
        for z in zb:
            secs = [k for k, sc in enumerate(R.secs) if z in [b["id"] for b in R.prof[sc["profil"]]["bandes"]]]
            S0, S1 = float(R.secs[secs[0]]["s0"]), float(R.secs[secs[-1]]["s1"])

            def bornes(s):
                k = R.section(min(max(s, S0 + 1e-7), S1 - 1e-7))
                p = R.profil(k)
                T = A1.t_limites(p, s)
                ids = [b["id"] for b in p["bandes"]]
                b = ids.index(z)
                m = []
                cote_ligne = 0
                for cote, l in ((0, b), (1, b + 1)):
                    lim = p["limites"][l]
                    bo = lim.get("bordure")
                    h = 1e-3
                    pente = (A1.t_limites(p, s + h)[l] - A1.t_limites(p, s - h)[l]) / (2 * h)
                    if bo:
                        base, H, dh = R.pb[bo["profil"]]
                        can = (bo.get("caniveau") or {}).get("profil")
                        wc = R.pb[can][0] if can and R.caniveau_pose(s) else 0.0
                        bas_vers_zone = (bo["cote_haut"] == "gauche") if cote == 0 else (bo["cote_haut"] == "droite")
                        m.append((wc if bas_vers_zone else base) + DEG_U * 0.05)
                    else:
                        cle = self.cle(p, l)
                        r = next((r for r in lignes if r["cle"] == cle and r["s0"] - 1e-6 <= s <= r["s1"] + 1e-6), None)
                        if r:
                            m.append((0.5 * r["largeur"] + DEG_U * r["u"]) * math.sqrt(1 + pente * pente))
                            cote_ligne = 1 if cote == 0 else -1
                        else:
                            m.append(0.0)
                return T[b] - m[0], T[b + 1] + m[1], cote_ligne
            ss = np.linspace(S0, S1, int(round((S1 - S0) / 0.01)) + 1)
            HI, LO, CL = zip(*[bornes(s) for s in ss])
            HI, LO = np.array(HI), np.array(LO)
            w = HI - LO
            ok = np.where(w >= 0)[0]
            z0, z1 = float(ss[ok[0]]), float(ss[ok[-1]])
            okap = np.where(w >= aplat)[0]
            sa, sb = float(ss[okap[0]]), float(ss[okap[-1]])
            cote_ligne = next((c for c in CL if c), -1)
            out.append({"bande": z, "z0": z0, "z1": z1, "sa": sa, "sb": sb, "s": ss, "hi": HI, "lo": LO,
                        "angle": ang, "bande_h": bande_h, "pas": bande_h + esp, "cote_ligne": cote_ligne,
                        "aplat": aplat})
        return out

    # ------------------------------------------------------------------------------------ (x, y) -> (s, t)
    def st_de_xy(self, R, x, y):
        """Inverse de la référence : projection sur l'échantillonnage (pas 0,5 m) puis Newton sur l'expression
        analytique (droite, arc en forme fermée ; clothoïde par quadrature)."""
        ref = R.ref
        if not hasattr(R, "_ech"):
            ss = np.linspace(0.0, ref.L, max(2, int(math.ceil(ref.L / 0.5)) + 1))
            R._ech = (ss, np.array([ref.eval(s)[:2] for s in ss]))
        ss, P = R._ech
        i = int(np.argmin(np.hypot(P[:, 0] - x, P[:, 1] - y)))
        s = float(ss[i])
        for _ in range(8):
            px, py, th, k = ref.eval(min(max(s, 0.0), ref.L))
            dx, dy = x - px, y - py
            ds = dx * math.cos(th) + dy * math.sin(th)
            s += ds
            if abs(ds) < 1e-11:
                break
        s = min(max(s, 0.0), ref.L)
        px, py, th, k = ref.eval(s)
        t = -(x - px) * math.sin(th) + (y - py) * math.cos(th)
        if s <= 0.0 or s >= ref.L:                  # au-delà des bouts : prolongement de la tangente
            ds = (x - px) * math.cos(th) + (y - py) * math.sin(th)
            s += ds
        return s, t
