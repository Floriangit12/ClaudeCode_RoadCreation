# -*- coding: utf-8 -*-
"""Plan coté de contrôle (vue de dessus, SVG) d'un modèle compilé depuis une description de réseau (lot « scenes »).

Dessine, à partir du modèle `modele_voie` seul (géométrie régulière des routes, profils, sections, îlots, marquages,
signaux, carrefours) : bandes des routes (chaussée, trottoirs, terre-pleins, accotements, zones neutralisées),
bordures, lignes longitudinales, coupes des branches à la limite de la chaussée abordée, coins, îlots (en saillie et
peints), lignes transversales, passages, sas, flèches, lignes de guidage, chevrons, trajectoires (couleur par
mouvement), points de conflit, signaux ; puis les cotes du rapport de réseau (frontières, lignes, passages, refuges,
rayons) et un cartouche (attendus déclarés / valeurs mesurées). Deux vues : ensemble et zoom sur chaque carrefour.

    python recon/generateur/description/plan_reseau.py <dossier de sortie de la scène> [--plans DOSSIER]

Sorties : <plans>/<scene>_ensemble.svg, <scene>_<carrefour>.svg et leurs rendus PNG (PyMuPDF) pour la découpe en tuiles.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
sys.path.insert(0, str(GEN))
from commun import geometrie as G  # noqa: E402
from description import description_vers_modele as D  # noqa: E402

COUL = {"chaussee": "#55575a", "trottoir": "#c9c4b8", "terre_plein": "#7aa35a", "terre_plein_peint": "#6a6c70",
        "zone_neutralisee": "#6a6c70", "accotement": "#77797c", "bande_arret_urgence": "#68696c", "berme": "#9fb07a",
        "bande_plantee": "#7aa35a", "piste": "#7b4d4d", "fond": "#e9e7df", "bordure": "#1d1d1d", "blanc": "#ffffff",
        "jaune": "#f0c419", "ilot": "#a6c27f", "ilot_peint": "#808286", "TD": "#2e8b57", "TAG": "#d0312d",
        "TAD": "#1f6fd1", "anneau": "#8e44ad", "insertion": "#e67e22", "sortie": "#e67e22", "cote": "#b0006a"}


class TraceModele:
    """Ligne de référence reconstruite depuis geometrie_reguliere (mêmes primitives que le compilateur)."""

    def __init__(self, prims):
        self.prims = [G.Primitive(p["s0"], p["longueur"], p["x0"], p["y0"], math.radians(p["cap_deg"]),
                                  p.get("courbure0", 0.0), p.get("courbure1", p.get("courbure0", 0.0))) for p in prims]
        self.L = sum(p.longueur for p in self.prims)

    def _p(self, s):
        for p in self.prims:
            if s <= p.s0 + p.longueur + 1e-9:
                return p
        return self.prims[-1]

    def point(self, s):
        p = self._p(s)
        u = min(max(s - p.s0, 0.0), p.longueur)
        x, y = p.point_local(u)
        return x, y, p.cap_a(u)

    def point_st(self, s, t):
        x, y, c = self.point(s)
        return x - t * math.sin(c), y + t * math.cos(c)


class Plan:
    def __init__(self, modele, rapport, origine, cadre=None, echelle=None, titre="", attendus=None):
        self.m, self.r, self.o = modele, rapport, origine
        self.prof = {p["id"]: p for p in modele["profils"]}
        self.routes = {r["id"]: r for r in modele["routes"]}
        self.traces = {rid: TraceModele(r["ligne_reference"]["geometrie_reguliere"]) for rid, r in self.routes.items()}
        self.titre, self.attendus = titre, attendus
        # cadre en coordonnées locales (m)
        if cadre is None:
            xs, ys = [], []
            for r in modele["routes"]:
                for x, y in r["ligne_reference"]["geometrie"]:
                    xs.append(x - origine[0])
                    ys.append(y - origine[1])
            m = 18.0
            cadre = (min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)
        self.cadre = cadre
        W = cadre[2] - cadre[0]
        H = cadre[3] - cadre[1]
        self.k = echelle or min(1500.0 / W, 980.0 / H)
        self.cart = 300
        self.Wpx = int(W * self.k) + 20
        self.Hpx = int(H * self.k) + 20 + self.cart
        self.el = []
        self.coupe = self._coupes()

    # ---------------------------------------------------------------- outils
    def P(self, x, y):
        return ((x - self.o[0] - self.cadre[0]) * self.k + 10, (self.cadre[3] - (y - self.o[1])) * self.k + 10)

    def pts(self, lst):
        return " ".join(f"{a:.1f},{b:.1f}" for a, b in (self.P(x, y) for x, y in lst))

    def poly(self, lst, fill, stroke="none", sw=0.0, op=1.0, extra=""):
        self.el.append(f'<polygon points="{self.pts(lst)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:.2f}" '
                       f'fill-opacity="{op}" {extra}/>')

    def ligne(self, lst, stroke, sw, dash=None, op=1.0, cap="butt"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(f'<polyline points="{self.pts(lst)}" fill="none" stroke="{stroke}" stroke-width="{sw:.2f}" '
                       f'stroke-opacity="{op}" stroke-linecap="{cap}"{d}/>')

    def texte(self, x, y, t, taille=11, coul="#111", ancre="middle", gras=False, monde=True, fond=False):
        px, py = self.P(x, y) if monde else (x, y)
        t = str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        w = ' font-weight="bold"' if gras else ""
        if fond:
            lw = len(t) * taille * 0.55
            x0 = px - (lw / 2 if ancre == "middle" else (0 if ancre == "start" else lw))
            self.el.append(f'<rect x="{x0 - 2:.1f}" y="{py - taille:.1f}" width="{lw + 4:.1f}" height="{taille + 4:.1f}" '
                           f'fill="#ffffff" fill-opacity="0.85"/>')
        self.el.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="{taille}" fill="{coul}" text-anchor="{ancre}" '
                       f'font-family="DejaVu Sans, Arial, sans-serif"{w}>{t}</text>')

    # ---------------------------------------------------------------- coupes des branches (frontière / coins)
    def _coins_geo(self):
        """Coins exacts (même construction que le compilateur) : P, centre, points de tangence, arc."""
        out = []
        for c in self.m.get("carrefours", []):
            if c["type"] in ("giratoire", "mini_giratoire", "bifurcation"):
                continue
            br = c["branches"]
            n = len(br)
            for k, b in enumerate(br):
                co = b.get("coin_droit")
                nxt = br[(k + 1) % n]
                if not co:
                    continue
                a = (nxt["azimut_deg"] - b["azimut_deg"]) % 360
                if a > 179:
                    continue
                wb, wn = self._w_bords(b), self._w_bords(nxt)
                ub = (math.cos(math.radians(b["azimut_deg"])), math.sin(math.radians(b["azimut_deg"])))
                un = (math.cos(math.radians(nxt["azimut_deg"])), math.sin(math.radians(nxt["azimut_deg"])))
                nb, nn = (-ub[1], ub[0]), (-un[1], un[0])
                cx, cy = c["centre"]
                A = (cx + wb[0] * nb[0], cy + wb[0] * nb[1])
                B = (cx + wn[1] * nn[0], cy + wn[1] * nn[1])
                Pc = _inter(A, ub, B, un)
                R = co["rayon_m"]
                Cc = _inter((A[0] + R * nb[0], A[1] + R * nb[1]), ub, (B[0] - R * nn[0], B[1] - R * nn[1]), un)
                if Pc is None or Cc is None:
                    continue
                Ti = (Cc[0] - R * nb[0], Cc[1] - R * nb[1])
                Tk = (Cc[0] + R * nn[0], Cc[1] + R * nn[1])
                a_0 = math.degrees(math.atan2(Ti[1] - Cc[1], Ti[0] - Cc[0]))
                a_1 = math.degrees(math.atan2(Tk[1] - Cc[1], Tk[0] - Cc[0]))
                da = (a_1 - a_0 + 180) % 360 - 180
                arc = [(Cc[0] + R * math.cos(math.radians(a_0 + da * i / 40)), Cc[1] + R * math.sin(math.radians(a_0 + da * i / 40)))
                       for i in range(41)]
                xi = (Ti[0] - cx) * ub[0] + (Ti[1] - cy) * ub[1]
                xk = (Tk[0] - cx) * un[0] + (Tk[1] - cy) * un[1]
                out.append({"c": c, "b": b, "nxt": nxt, "P": Pc, "C": Cc, "R": R, "Ti": Ti, "Tk": Tk, "arc": arc,
                            "a0": a_0, "da": da, "xi": xi, "xk": xk})
        return out

    def _coupes(self):
        """{route: {"debut"|"fin": (x_chaussee, x_cote_gauche, x_cote_droit)}} : chaussée coupée à la frontière, bandes
        latérales aux points de tangence des coins (0 : pas de coin de ce côté, la bande va jusqu'au centre)."""
        out = {}
        self.coins_geo = self._coins_geo()
        for o in (self.r.get("reseau") or {}).get("objets", []):
            if o.get("genre") != "carrefour_plan":
                continue
            c = next(c for c in self.m.get("carrefours", []) if c["id"] == o["id"])
            for b in c["branches"]:
                xf = o["branches"][b["id"][2:]]["frontiere_m"]
                cg = next((g for g in self.coins_geo if g["c"] is c and g["b"] is b), None)
                cd = next((g for g in self.coins_geo if g["c"] is c and g["nxt"] is b), None)
                xg = cg["xi"] if cg else 0.0
                xd = cd["xk"] if cd else 0.0
                out.setdefault(b["route"], {})[b["extremite"]] = (xf, xg, xd)
        return out

    # ---------------------------------------------------------------- routes
    def _debouches(self):
        """Raccordements des branches de giratoire sur l'anneau (rayons Re / Rs du modèle) : arcs et intervalles
        angulaires où le bord extérieur de l'anneau est interrompu."""
        self.ouvertures = {}          # route d'anneau → [(a0, a1)] en degrés
        self.racc = []
        for c in self.m.get("carrefours", []):
            if c["type"] not in ("giratoire", "mini_giratoire"):
                continue
            a = c["anneau"]
            O = c["centre"]
            Rg = a["rayon_exterieur_m"]
            rid = a["construction"]["route_anneau"]
            for b in c["branches"]:
                rr = a["construction"].get("raccordements", {}).get(b["id"])
                if not rr:
                    continue
                wg, wd = self._w_bords(b)
                u = (math.cos(math.radians(b["azimut_deg"])), math.sin(math.radians(b["azimut_deg"])))
                n = (-u[1], u[0])
                r = self.routes[b["route"]]
                tr = self.traces[b["route"]]
                pe = tr.point(tr.L if b["extremite"] == "fin" else 0.0)[:2]
                angs = []
                for w, R, sgn in ((wg, rr["entree_m"], 1.0), (wd, rr["sortie_m"], -1.0)):
                    # centre à R du bord (côté extérieur) et à Rg + R de O
                    off = w + sgn * R
                    base = (pe[0] + off * n[0], pe[1] + off * n[1])
                    # |base + x u − O| = Rg + R
                    dx, dy = base[0] - O[0], base[1] - O[1]
                    bq = 2 * (dx * u[0] + dy * u[1])
                    cq = dx * dx + dy * dy - (Rg + R) ** 2
                    disc = bq * bq - 4 * cq
                    if disc < 0:
                        continue
                    xx = (-bq + math.sqrt(disc)) / 2
                    Cc = (base[0] + xx * u[0], base[1] + xx * u[1])
                    T1 = (pe[0] + xx * u[0] + w * n[0], pe[1] + xx * u[1] + w * n[1])
                    T2 = (O[0] + (Cc[0] - O[0]) * Rg / (Rg + R), O[1] + (Cc[1] - O[1]) * Rg / (Rg + R))
                    a1 = math.degrees(math.atan2(T1[1] - Cc[1], T1[0] - Cc[0]))
                    a2 = math.degrees(math.atan2(T2[1] - Cc[1], T2[0] - Cc[0]))
                    da = (a2 - a1 + 180) % 360 - 180
                    arc = [(Cc[0] + R * math.cos(math.radians(a1 + da * i / 30)), Cc[1] + R * math.sin(math.radians(a1 + da * i / 30)))
                           for i in range(31)]
                    self.racc.append({"arc": arc, "R": R, "T1": T1, "T2": T2, "pe": pe, "u": u, "n": n, "w": w, "C": Cc,
                                      "a1": a1, "da": da, "x": xx})
                    angs.append(math.degrees(math.atan2(T2[1] - O[1], T2[0] - O[0])))
                if len(angs) == 2:
                    lo, hi = sorted(angs)
                    if hi - lo > 180:
                        lo, hi = hi, lo + 360
                    self.ouvertures.setdefault(rid, []).append((lo, hi, O))

    def _dans_ouverture(self, rid, x, y):
        for lo, hi, O in self.ouvertures.get(rid, []):
            a = math.degrees(math.atan2(y - O[1], x - O[0]))
            for k in (a, a + 360, a - 360):
                if lo <= k <= hi:
                    return True
        return False

    def raccordements(self):
        for g in self.racc:
            # surface de chaussée entre le bord de la branche, l'arc de raccordement et l'anneau
            pts = [g["T1"]] + g["arc"] + [g["T2"]]
            pe, u, n = g["pe"], g["u"], g["n"]
            back = (pe[0] + n[0] * g["w"] * 0.0, pe[1] + n[1] * g["w"] * 0.0)
            self.poly(pts + [(pe[0] + g["w"] * n[0] * 0.0, pe[1]) if False else (g["pe"][0] + g["w"] * n[0], g["pe"][1] + g["w"] * n[1])],
                      COUL["chaussee"])
            self.ligne(g["arc"], COUL["bordure"], max(1.2, 0.18 * self.k))
            # trottoir derrière l'arc (2 m)
            Cc, R = g["C"], g["R"]
            arc2 = [(Cc[0] + (R - 2.0) * math.cos(math.radians(g["a1"] + g["da"] * i / 30)),
                     Cc[1] + (R - 2.0) * math.sin(math.radians(g["a1"] + g["da"] * i / 30))) for i in range(31)]
            self.poly(g["arc"] + arc2[::-1], COUL["trottoir"])
            self.texte(*_mil(g["arc"]), f"R {R:g}", 9, COUL["cote"], fond=True)

    def routes_bandes(self):
        self._debouches()
        for rid, r in self.routes.items():
            tr = self.traces[rid]
            cp = self.coupe.get(rid, {})
            for sec in r["sections"]:
                p = self.prof[sec["profil"]]
                s0, s1 = sec["s0"], sec["s1"]
                n = max(2, int((s1 - s0) / 1.0) + 1)
                if r["categorie"] == "anneau_giratoire":
                    n = max(n, int((s1 - s0) / 0.5) + 1)
                ss = [s0 + (s1 - s0) * i / (n - 1) for i in range(n)]
                for i, b in enumerate(p["bandes"]):
                    lim_s = self._lim_s(r, cp, b, p, i, tr.L)
                    sss = [s for s in ss if lim_s[0] - 1e-9 <= s <= lim_s[1] + 1e-9]
                    if len(sss) < 2:
                        continue
                    for morceau in self._morceaux(rid, r, p, i, sss, tr, b):
                        T = [D.t_limites(p, s) for s in morceau]
                        g = [tr.point_st(s, t[i]) for s, t in zip(morceau, T)]
                        d = [tr.point_st(s, t[i + 1]) for s, t in zip(morceau, T)]
                        self.poly(g + d[::-1], self._couleur(b))
        # lignes et bordures
        for rid, r in self.routes.items():
            tr = self.traces[rid]
            cp = self.coupe.get(rid, {})
            for sec in r["sections"]:
                p = self.prof[sec["profil"]]
                s0, s1 = sec["s0"], sec["s1"]
                n = max(2, int((s1 - s0) / 1.0) + 1)
                if r["categorie"] == "anneau_giratoire":
                    n = max(n, int((s1 - s0) / 0.5) + 1)
                ss = [s0 + (s1 - s0) * i / (n - 1) for i in range(n)]
                for i, lim in enumerate(p["limites"]):
                    a = p["bandes"][i - 1] if i > 0 else None
                    b = p["bandes"][i] if i < len(p["bandes"]) else None
                    ref = b if b is not None else a
                    if a is not None and b is not None and a["niveau"]["reference"] == "chaussee" and b["niveau"]["reference"] == "chaussee":
                        lim_s = self._lim_s(r, cp, a, p, i - 1, tr.L)
                    else:
                        lim_s = self._lim_s(r, cp, ref, p, i if b is not None else i - 1, tr.L, bordure=True)
                    sss = [s for s in ss if lim_s[0] - 1e-9 <= s <= lim_s[1] + 1e-9]
                    if len(sss) < 2:
                        continue
                    if "bordure" in lim["nature"]:
                        bext = b if (b is not None and b["niveau"]["reference"] != "chaussee") else a
                        for morceau in self._morceaux(rid, r, p, i, sss, tr, bext, limite=True):
                            pts = [tr.point_st(s, D.t_limites(p, s)[i]) for s in morceau]
                            self.ligne(pts, COUL["bordure"], max(1.2, 0.18 * self.k))
                    pts = [tr.point_st(s, D.t_limites(p, s)[i]) for s in sss]
                    if "separateur" in lim["nature"]:
                        sp = lim["separateur"]
                        self.ligne(pts, "#cfcfcf" if sp["type"] == "GBA" else "#9aa3ad",
                                   max(2.0, sp.get("largeur_m", 0.3) * self.k))
                        self.ligne(pts, "#444", max(0.6, 0.03 * self.k))
                    for mq in lim.get("marquages", []):
                        iv = mq.get("intervalle")
                        q = [x for x in sss if iv is None or iv["s0"] - 1e-9 <= x <= iv["s1"] + 1e-9]
                        if len(q) < 2:
                            continue
                        segs = self._decoupe_interruptions(q, mq.get("interruptions", []))
                        w = mq.get("largeur_m") or mq.get("largeur_u", 2) * mq.get("u_m", 0.05)
                        for seg in segs:
                            if len(seg) < 2:
                                continue
                            self.ligne([tr.point_st(s, D.t_limites(p, s)[i]) for s in seg],
                                       COUL["jaune"] if mq.get("couleur") == "jaune" else COUL["blanc"],
                                       max(0.9, w * self.k), dash=self._dash(mq["modulation"]))

    def _morceaux(self, rid, r, p, i, sss, tr, b, limite=False):
        """Échantillons découpés aux débouchés des branches pour les bandes extérieures de l'anneau d'un giratoire."""
        if r["categorie"] != "anneau_giratoire" or b is None or b["niveau"]["reference"] == "chaussee" and not limite:
            return [sss]
        if b["type"] == "terre_plein":
            return [sss]
        out, cur = [], []
        for s in sss:
            T = D.t_limites(p, s)
            x, y = tr.point_st(s, (T[i] + T[min(i + 1, len(T) - 1)]) / 2)
            if self._dans_ouverture(rid, x, y):
                if len(cur) >= 2:
                    out.append(cur)
                cur = []
            else:
                cur.append(s)
        if len(cur) >= 2:
            out.append(cur)
        return out

    @staticmethod
    def _decoupe_interruptions(ss, its):
        segs, cur = [], []
        for s in ss:
            if any(i["s0"] <= s <= i["s1"] for i in its):
                if cur:
                    segs.append(cur)
                cur = []
            else:
                cur.append(s)
        if cur:
            segs.append(cur)
        return segs

    def _dash(self, mod):
        k = self.k
        return {"T1": f"{3 * k:.1f},{10 * k:.1f}", "T'1": f"{1.5 * k:.1f},{5 * k:.1f}", "T2": f"{3 * k:.1f},{3.5 * k:.1f}",
                "T'2": f"{0.5 * k:.1f},{0.5 * k:.1f}", "T3": f"{3 * k:.1f},{1.33 * k:.1f}", "T'3": f"{20 * k:.1f},{6 * k:.1f}",
                "T4": f"{39 * k:.1f},{13 * k:.1f}"}.get(mod)

    def _lim_s(self, r, cp, b, p, i, L, bordure=False):
        """Intervalle de s dessiné pour la bande i : coupe à la frontière (chaussée) ou aux coins (bandes latérales)."""
        s0, s1 = 0.0, L
        for ex, (xf, xg, xd) in cp.items():
            if b is None:
                continue
            ch = b["niveau"]["reference"] == "chaussee" and not bordure
            # côté de la bande : t > 0 à gauche de la route ; branche sortante u = −route si « fin »
            T = D.t_limites(p, L if ex == "fin" else 0.0)
            tm = (T[min(i, len(T) - 1)] + T[min(i + 1, len(T) - 1)]) / 2
            sg = -1.0 if ex == "fin" else 1.0
            w = sg * tm
            if ch:
                x = xf
            else:
                x = xg if w > 0 else xd
            if ex == "fin":
                s1 = min(s1, L - x)
            else:
                s0 = max(s0, x)
        return s0, s1

    def _couleur(self, b):
        t = b["type"]
        if t == "terre_plein":
            tp = b.get("terre_plein") or {}
            if tp.get("franchissable") == "peint":
                return COUL["terre_plein_peint"]
            if (tp.get("remplissage") or {}).get("type") in ("beton", "enrobe", "paves"):
                return "#b9b4a6" if b["niveau"]["dz_m"] > 0.005 else "#8b8d90"
            return COUL["terre_plein"]
        if t in ("trottoir", "chemin_pieton", "quai_bus"):
            return COUL["trottoir"]
        if t == "zone_neutralisee":
            return COUL["zone_neutralisee"]
        if t == "bande_arret_urgence":
            return COUL["bande_arret_urgence"]
        if t in ("accotement_revetu", "bande_derasee"):
            return COUL["accotement"]
        if t in ("berme", "bande_plantee", "talus", "fosse", "noue"):
            return COUL["berme"]
        if t == "piste_cyclable":
            return COUL["piste"] if b["niveau"]["reference"] != "chaussee" else COUL["chaussee"]
        if t == "voie_insertion" or t == "voie_deceleration":
            return "#5e6064"
        return COUL["chaussee"]

    # ---------------------------------------------------------------- carrefours
    def carrefours(self):
        for c in self.m.get("carrefours", []):
            if c["type"] in ("giratoire", "mini_giratoire"):
                continue
            if c["type"] == "bifurcation":
                continue
            # zone de conflit (chaussée du carrefour) et coins
            zc = c["zone_conflit"]["exterieur"]
            self.poly(zc, COUL["chaussee"])
            for b in c["branches"]:
                co = b.get("coin_droit")
                if not co:
                    continue
        # coins : surfaces entre les bords de chaussée et l'arc (depuis le rapport : recalcul)
        for o in (self.r.get("reseau") or {}).get("objets", []):
            if o.get("genre") != "carrefour_plan":
                continue
            c = next(c for c in self.m["carrefours"] if c["id"] == o["id"])
            self._coins(c, o)

    def _coins(self, c, o):
        for g in self.coins_geo:
            if g["c"] is not c:
                continue
            Pc, Cc, R, arc = g["P"], g["C"], g["R"], g["arc"]
            self.poly([Pc] + arc, COUL["chaussee"])
            self.ligne(arc, COUL["bordure"], max(1.2, 0.18 * self.k))
            arc2 = [(Cc[0] + (R - 2.0) * math.cos(math.radians(g["a0"] + g["da"] * i / 40)),
                     Cc[1] + (R - 2.0) * math.sin(math.radians(g["a0"] + g["da"] * i / 40))) for i in range(41)] if R > 2.0 else [Cc]
            self.poly(arc + arc2[::-1], COUL["trottoir"])
            self.texte(*_mil(arc), f"R {R:g}", 10, COUL["cote"], fond=True)

    def _w_bords(self, b):
        r = self.routes[b["route"]]
        tr = self.traces[b["route"]]
        sec = r["sections"][-1] if b["extremite"] == "fin" else r["sections"][0]
        p = self.prof[sec["profil"]]
        s = tr.L - 1e-6 if b["extremite"] == "fin" else 1e-6
        T = D.t_limites(p, s)
        sg = -1.0 if b["extremite"] == "fin" else 1.0
        ws = []
        for i, bd in enumerate(p["bandes"]):
            if bd["niveau"]["reference"] == "chaussee":
                ws += [sg * T[i], sg * T[i + 1]]
        return max(ws), min(ws)

    def giratoires(self):
        for c in self.m.get("carrefours", []):
            if c["type"] not in ("giratoire", "mini_giratoire"):
                continue
            a = c["anneau"]
            cx, cy = c["centre"]
            # bouchage des branches jusqu'à l'anneau : déjà dessinées ; marquage cédez etc. via marquages
            Rg = a["rayon_exterieur_m"]
            self.texte(cx, cy - Rg - 4, f"Ø {2 * Rg:g} m ; anneau {a['largeur_anneau_m']:g} m ; couronne "
                                        f"{a['bande_franchissable_m']:g} m", 11, COUL["cote"], fond=True)

    def ilots(self):
        for il in self.m.get("ilots", []):
            ext = il["polygone"]["exterieur"]
            tp = il["terre_plein"]
            if tp.get("franchissable") == "peint":
                self.poly(ext, COUL["ilot_peint"], "#ffffff", max(0.8, 0.225 * self.k), 1.0)
                self._hachures(ext)
            else:
                rem = (tp.get("remplissage") or {}).get("type")
                f = COUL["ilot"] if rem in ("gazon", "plante", None) else ("#c2b8a3" if rem in ("paves",) else "#bdb8ab")
                if il["type"] == "central_giratoire" and tp.get("franchissable") == "vl_pl":
                    f = "#c9b48f"
                self.poly(ext, f, COUL["bordure"], max(1.0, 0.15 * self.k))
            for nz in il.get("nez", []):
                if nz.get("balise") == "J5":
                    x, y = self.P(*nz["position"])
                    self.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(2.5, 0.35 * self.k):.1f}" fill="#1f6fd1" '
                                   f'stroke="#fff" stroke-width="1"/>')
            if il.get("refuge"):
                cxy = _centroide(ext)
                self.texte(cxy[0], cxy[1], f"refuge {il['refuge']['largeur_m']:.2f}", 9, "#063", fond=True)

    def _rayures(self, ext, angle_deg, pas, larg, coul="#ffffff"):
        """Rayures découpées dans le polygone (shapely : pas de clipPath, rendu PNG fidèle)."""
        from shapely.geometry import LineString, Polygon
        poly = Polygon(ext).buffer(0)
        if poly.is_empty:
            return
        cx, cy = poly.centroid.x, poly.centroid.y
        R = math.hypot(poly.bounds[2] - poly.bounds[0], poly.bounds[3] - poly.bounds[1])
        u = (math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg)))
        n = (-u[1], u[0])
        k = -int(R / pas) - 1
        while k * pas <= R:
            o = k * pas
            seg = LineString([(cx + n[0] * o - u[0] * R, cy + n[1] * o - u[1] * R),
                              (cx + n[0] * o + u[0] * R, cy + n[1] * o + u[1] * R)]).intersection(poly)
            for g in getattr(seg, "geoms", [seg]):
                if g.geom_type == "LineString" and not g.is_empty:
                    self.ligne(list(g.coords), coul, max(0.8, larg * self.k))
            k += 1

    def _hachures(self, ext):
        # hachures 0,50 m au pas perpendiculaire 1,85 m (DEF-020), orientation indicative
        (ax, ay), (bx, by) = ext[0], ext[1]
        a = math.degrees(math.atan2(by - ay, bx - ax)) + 26.565
        self._rayures(ext, a, 1.85, 0.5)

    def marquages(self):
        for mq in self.m.get("marquages", []):
            t = mq["type"]
            g = mq.get("geometrie")
            if t == "ligne_transversale" and g:
                w = 0.5 if mq.get("gabarit") in ("CEDEZ", "STOP") else 0.15
                dash = None if mq.get("gabarit") == "STOP" else self._dash("T'2")
                self.ligne(g, COUL["blanc"], max(1.5, w * self.k), dash=dash)
            elif t == "passage_pieton" and g:
                ext = g["exterieur"]
                self.poly(ext, "none", "#ffffff", max(0.8, 0.12 * self.k))
                self._zebra(ext)
            elif t == "ligne_guidage" and g:
                self.ligne(g, COUL["blanc"], max(1.0, 0.10 * self.k), dash=self._dash("T'2"))
                self.ligne(g, "#ff00aa", 0.8, op=0.8)
            elif t == "sas_velo" and g:
                self.poly(g["exterieur"], "#3a7d3a", "none", 0, 0.35)
            elif t == "chevrons" and g:
                self.poly(g["exterieur"], "#8a8c90", "#fff", max(0.8, 0.225 * self.k))
                self._hachures(g["exterieur"])
            elif t in ("fleche", "figurine_velo") and mq.get("ancrage", {}).get("route") in self.traces:
                an = mq["ancrage"]
                tr = self.traces[an["route"]]
                x, y = tr.point_st(an["s"], an.get("t", 0.0))
                cap = math.radians(an.get("cap_deg", 0.0))
                if t == "figurine_velo":
                    px, py = self.P(x, y)
                    self.el.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{max(1.5, 0.5 * self.k):.1f}" fill="none" '
                                   f'stroke="#fff" stroke-width="1"/>')
                    continue
                Lf = 4.0 if "5,33" not in json.dumps(mq.get("prov", {})) else 5.333
                a = (x - Lf / 2 * math.cos(cap), y - Lf / 2 * math.sin(cap))
                b = (x + Lf / 2 * math.cos(cap), y + Lf / 2 * math.sin(cap))
                self.ligne([a, b], "#ffffff", max(1.2, 0.25 * self.k))
                gab = mq.get("gabarit", "")
                for sens, lab in ((90, "TAG"), (-90, "TAD")):
                    if lab in gab:
                        c2 = cap + math.radians(sens)
                        self.ligne([b, (b[0] + 1.2 * math.cos(c2), b[1] + 1.2 * math.sin(c2))], "#fff", max(1.0, 0.2 * self.k))
                self.ligne([b, (b[0] - 0.8 * math.cos(cap + 0.5), b[1] - 0.8 * math.sin(cap + 0.5))], "#fff", max(1.0, 0.2 * self.k))
                self.ligne([b, (b[0] - 0.8 * math.cos(cap - 0.5), b[1] - 0.8 * math.sin(cap - 0.5))], "#fff", max(1.0, 0.2 * self.k))

    def _zebra(self, ext):
        # bandes du passage : parallèles à l'axe de la chaussée (perpendiculaires au plus long côté de traversée)
        pts = ext[:-1] if ext[0] == ext[-1] else ext
        cotes = [(math.dist(pts[i], pts[(i + 1) % len(pts)]), i) for i in range(len(pts))]
        _, i = max(cotes)
        a, b = pts[i], pts[(i + 1) % len(pts)]
        ang_l = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        self._rayures(ext, ang_l + 90.0, 1.1, 0.5)

    def trajectoires(self):
        for c in self.m.get("carrefours", []):
            for t in c.get("trajectoires", []):
                g = t.get("geometrie")
                if not g:
                    continue
                coul = COUL.get(t["mouvement"], COUL["anneau"])
                self.ligne(g, coul, 1.4, op=0.85)
                if (t.get("guidage") or {}).get("materialise"):
                    self.ligne(g, coul, 3.0, op=0.35)
            for k in c.get("conflits", []):
                if k.get("type") == "croisement" and k.get("point"):
                    x, y = self.P(*k["point"])
                    self.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#ffd400" stroke="#000" stroke-width="0.6"/>')

    def signaux(self):
        for sg in self.m.get("signaux", []):
            xy = (sg.get("position") or {}).get("xyz")
            if not xy:
                continue
            x, y = self.P(*xy[:2])
            f = {"feu": "#111", "balise": "#1f6fd1"}.get(sg["famille"], "#c0392b")
            self.el.append(f'<rect x="{x - 3:.1f}" y="{y - 3:.1f}" width="6" height="6" fill="{f}" stroke="#fff" stroke-width="0.8"/>')
            self.el.append(f'<text x="{x + 4:.1f}" y="{y - 4:.1f}" font-size="9" fill="{f}" font-family="DejaVu Sans, Arial">{sg["code"]}</text>')

    def cotes(self):
        rap = (self.r.get("reseau") or {}).get("objets", [])
        for o in rap:
            if o.get("genre") != "carrefour_plan":
                continue
            c = next(c for c in self.m["carrefours"] if c["id"] == o["id"])
            cx, cy = c["centre"]
            for b in c["branches"]:
                info = o["branches"][b["id"][2:]]
                u = (math.cos(math.radians(b["azimut_deg"])), math.sin(math.radians(b["azimut_deg"])))
                n = (-u[1], u[0])
                xf = info["frontiere_m"]
                wb = self._w_bords(b)
                # frontière : trait magenta
                p0 = (cx + u[0] * xf + n[0] * (wb[1] - 1), cy + u[1] * xf + n[1] * (wb[1] - 1))
                p1 = (cx + u[0] * xf + n[0] * (wb[0] + 1), cy + u[1] * xf + n[1] * (wb[0] + 1))
                self.ligne([p0, p1], COUL["cote"], 1.0, dash="4,3")
                lab = f"{b['id'][2:]} : front. {xf:.2f}"
                if info.get("ligne") and info["ligne"]["type"] != "virtuelle":
                    lab += f" ; {info['ligne']['type']} {info['ligne']['x0_m']:.2f}"
                if info.get("passage"):
                    lab += f" ; pp {info['passage']['x0_m']:.2f}+{info['passage']['largeur_m']:g}"
                if info.get("sas"):
                    lab += f" ; sas {info['sas']['x_avant']:.2f}-{info['sas']['x_arriere']:.2f}"
                q = (cx + u[0] * (xf + 30) + n[0] * (wb[0] + 3), cy + u[1] * (xf + 30) + n[1] * (wb[0] + 3))
                self.texte(q[0], q[1], lab, 10, COUL["cote"], fond=True)

    def cartouche(self, lignes):
        y0 = self.Hpx - self.cart + 8
        self.el.append(f'<rect x="0" y="{self.Hpx - self.cart}" width="{self.Wpx}" height="{self.cart}" fill="#ffffff"/>')
        self.texte(10, y0 + 12, self.titre, 14, "#000", "start", True, monde=False)
        for i, l in enumerate(lignes[:24]):
            col = 10 + (i // 12) * (self.Wpx // 2)
            self.texte(col, y0 + 32 + (i % 12) * 21, l, 11, "#222", "start", monde=False)
        # échelle
        L10 = 10 * self.k
        self.el.append(f'<line x1="{self.Wpx - 20 - L10:.1f}" y1="{y0 + 4}" x2="{self.Wpx - 20:.1f}" y2="{y0 + 4}" stroke="#000" stroke-width="3"/>')
        self.texte(self.Wpx - 20 - L10 / 2, y0 + 18, "10 m", 10, "#000", monde=False)

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.Wpx}" height="{self.Hpx}" '
                f'viewBox="0 0 {self.Wpx} {self.Hpx}"><rect width="100%" height="100%" fill="{COUL["fond"]}"/>'
                + "".join(self.el) + "</svg>")

    def dessiner(self, lignes_cartouche):
        self.carrefours()
        self.routes_bandes()
        self.raccordements()
        self.giratoires()
        self.marquages()
        self.ilots()
        self.trajectoires()
        self.signaux()
        self.cotes()
        self.cartouche(lignes_cartouche)
        return self.svg()


def _inter(p, u, q, v):
    det = u[0] * (-v[1]) - u[1] * (-v[0])
    if abs(det) < 1e-9:
        return None
    rx, ry = q[0] - p[0], q[1] - p[1]
    a = (rx * (-v[1]) - ry * (-v[0])) / det
    return (p[0] + a * u[0], p[1] + a * u[1])


def _mil(pts):
    return pts[len(pts) // 2]


def _centroide(pts):
    n = len(pts) - 1 if pts[0] == pts[-1] else len(pts)
    return (sum(p[0] for p in pts[:n]) / n, sum(p[1] for p in pts[:n]) / n)


def lignes_cartouche(rapport, attendus):
    out = []
    for o in (rapport.get("reseau") or {}).get("objets", []):
        if o.get("genre") == "carrefour_plan":
            out.append(f"{o['id']} : zone de conflit {o['zone_conflit_m2']:.1f} m² ; trajectoires {o['trajectoires']} ; "
                       f"conflits {o['conflits']}")
            if o.get("feux"):
                out.append(f"feux : cycle {o['feux']['cycle_s']:.0f} s ; phases "
                           + " | ".join(f"{p['nom']} ({len(p['mouvements'])} mvts, vert {p['vert_s']:g} s)" for p in o["feux"]["phases"]))
            if o.get("croisements_par_phase"):
                out.append(f"croisements par phase : {o['croisements_par_phase']}")
            if o.get("guidage"):
                out.append(f"guidage : {o['guidage']['mouvements']} {o['guidage']['modulation']} {o['guidage']['largeur_m']} m")
            out.append(f"îlots : {', '.join(o['ilots']) or '—'} ; signaux : {', '.join(o['signaux'])} ({o['nb_signaux']})")
        elif o.get("genre") in ("giratoire", "mini_giratoire"):
            out.append(f"{o['id']} ({o['genre']}) : Ø {o['diametre_m']:g} m, anneau {o['anneau_m']:g}, couronne {o['couronne_m']:g}, "
                       f"Ri {o['Ri_m']:.2f} (infr. {o['Ri_infranchissable_m']:.2f})")
            out.append(f"déflexion (m) : {o['deflexion_m']} ; conflits {o['conflits']}")
            out.append(f"îlots : {', '.join(o['ilots'])} ; signaux : {', '.join(o['signaux'])} ({o['nb_signaux']})")
        elif o.get("genre", "").startswith("bretelle"):
            out.append(f"{o['id']} ({o['genre']}) : voie auxiliaire {o['voie_auxiliaire']} s = {o['voie_auxiliaire_s']} "
                       f"({o['voie_auxiliaire_longueur_m']:.1f} m) ; jonction s = {o['jonction_s_principale']}")
            out.append(f"point à 1 m : {o['point_1m_depuis_jonction_m']} m ; point à 5 m : {o['point_5m_depuis_jonction_m']} m ; "
                       f"obliquité {o['obliquite']:.4f} ; musoir peint {o['musoir_peint_m2']:.1f} m²")
    ctl = (rapport.get("reseau") or {}).get("controles", [])
    nc = [c for c in ctl if c["statut"] not in ("conforme",)]
    out.append(f"contrôles réseau : {len(ctl)} dont {len(nc)} non conformes / avertissements"
               + (" : " + "; ".join(f"{c['controle']}={c['valeur']}" for c in nc[:4]) if nc else ""))
    out.append(f"validation : {rapport['validation']['nb_erreurs']} erreur(s) ; non-conformités bloquantes : "
               f"{len(rapport['non_conformites'])}")
    if attendus:
        txt = json.dumps(attendus, ensure_ascii=False)
        for k in range(0, min(len(txt), 600), 150):
            out.append(("attendus : " if k == 0 else "   ") + txt[k:k + 150])
    return out


def ecrire_plans(sortie_scene: Path, plans: Path, nom: str, rendus: Path | None = None):
    m = json.loads((sortie_scene / "modele_voie.json").read_text(encoding="utf-8"))
    r = json.loads((sortie_scene / "compilation.json").read_text(encoding="utf-8"))
    o = m["repere"]["origine_l93"]
    titre = (m["meta"].get("titre") or nom)
    att = r.get("attendus_declares")
    plans.mkdir(parents=True, exist_ok=True)
    fichiers = []
    pl = Plan(m, r, o, titre=f"{nom} — {titre} (ensemble)", attendus=att)
    (plans / f"{nom}_ensemble.svg").write_text(pl.dessiner(lignes_cartouche(r, att)), encoding="utf-8")
    fichiers.append(plans / f"{nom}_ensemble.svg")
    if not m.get("carrefours"):
        # section courante seule : zoom sur 60 m autour du début de la première route (profil lisible)
        x0, y0 = m["routes"][0]["ligne_reference"]["geometrie"][0]
        cx, cy = x0 - o[0] + 30.0, y0 - o[1]
        pz = Plan(m, r, o, cadre=(cx - 30, cy - 20, cx + 30, cy + 20), echelle=25.0, titre=f"{nom} — section (zoom)",
                  attendus=att)
        f = plans / f"{nom}_section.svg"
        f.write_text(pz.dessiner(lignes_cartouche(r, att)), encoding="utf-8")
        fichiers.append(f)
    for c in m.get("carrefours", []):
        cx, cy = c["centre"][0] - o[0], c["centre"][1] - o[1]
        rr = 45.0 if c["type"] != "bifurcation" else 130.0
        if c["type"] in ("giratoire", "mini_giratoire"):
            rr = c["anneau"]["rayon_exterieur_m"] + 32
        cadre = (cx - rr, cy - rr * 0.62, cx + rr, cy + rr * 0.62)
        pz = Plan(m, r, o, cadre=cadre, echelle=min(1500.0 / (2 * rr), 1000.0 / (1.24 * rr)),
                  titre=f"{nom} — {c['id']} (zoom)", attendus=att)
        f = plans / f"{nom}_{c['id']}.svg"
        f.write_text(pz.dessiner(lignes_cartouche(r, att)), encoding="utf-8")
        fichiers.append(f)
    pngs = []
    try:
        import pymupdf
        for f in fichiers:
            doc = pymupdf.open(str(f))
            pix = doc[0].get_pixmap(dpi=72)
            png = (rendus or f.parent) / (f.stem + ".png")
            png.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(png))
            pngs.append(png)
    except Exception as e:  # noqa: BLE001
        print(f"rendu PNG impossible : {e}")
    return fichiers, pngs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie_scene")
    ap.add_argument("--plans", required=True)
    ap.add_argument("--nom")
    ap.add_argument("--rendus", help="dossier des PNG (défaut : <sortie_scene>/plans)")
    a = ap.parse_args()
    s = Path(a.sortie_scene)
    f, p = ecrire_plans(s, Path(a.plans), a.nom or s.name, Path(a.rendus) if a.rendus else s / "plans")
    for x in f + p:
        print(x)


if __name__ == "__main__":
    main()
