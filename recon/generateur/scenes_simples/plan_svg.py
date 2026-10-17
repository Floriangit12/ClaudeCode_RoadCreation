# -*- coding: utf-8 -*-
"""Plan coté de contrôle (vue de dessus) d'une description simple, en SVG déterministe.

Dessine la géométrie calculée par `description.py` (bandes, bordures et caniveaux, abaissés, BEV, marquages exacts,
arbres), puis les cotes : chaînes transversales au début et à la fin du tronçon (largeur de chaque bande entre axes
des limites), chaîne longitudinale des points singuliers, chaînage tous les 10 m, cartouche (titre, contexte,
attendus, règles). Le SVG ne dépend d'aucune police ni d'aucun fichier externe ; les tirets sont des polygones (pas de
`stroke-dasharray`), si bien que le rendu PNG (PyMuPDF) montre la géométrie exacte.

    from plan_svg import ecrire_svg
    infos = ecrire_svg(scene, "plans/S02_rue_1x1_bordures_trottoirs.svg")
"""
from __future__ import annotations

import math
from pathlib import Path

from description import Scene, _r, lire_abord

ECHELLE = 20.0                       # px par mètre (0,10 m = 2 px)
ABORDS_M = 6.0                       # largeur des abords dessinés de part et d'autre du profil
CARTOUCHE_PX = 150
BAS_PX = 10

COULEURS = {
    # sols (materiaux_sol.json) : teintes moyennes des matériaux CC0 du dépôt, assombries pour la lisibilité
    "enrobe_bbsg_ancien": "#6f6f6c", "enrobe_bbsg_neuf_2025": "#4f4f50", "enrobe_reprise_tranchee": "#5d5d5c",
    "enrobe_piste_cyclable": "#4a4a4d", "enrobe_trottoir": "#8d8c87", "enrobe_clair_granulats": "#a19d94",
    "beton_balaye": "#bdb9ae", "beton_desactive": "#a8a293", "dalles_beton": "#c4c0b6", "paves_beton": "#a9a49b",
    "paves_granit": "#9b9a96", "gazon_tondu": "#6b8e47", "herbe_haute": "#7c8f4f", "gazon_sec": "#9a9a5a",
    "terre_nue": "#7d6a52", "paillage_mineral": "#a79f90", "brf_bois_concasse": "#7a5a3c",
    "gravier_concasse_6_10": "#9d9a92", "galets_20_40": "#aaa395", "stabilise_beige": "#c2b392",
    # éléments
    "bordure": "#dcd8cf", "caniveau": "#b6b1a6", "abaisse": "#e0b84c", "abaisse_rampant": "#ead08a",
    "abaisse_sol": "#000000", "rampant": "#000000", "bev": "#eeeae0", "rampe": "#000000", "plateau": "#ffffff",
    "blanc": "#f5f5f0", "jaune": "#f0c419",
}
OPACITE = {"rampant": 0.10, "abaisse_sol": 0.05, "rampe": 0.22, "plateau": 0.10}
ORDRE_CALQUES = ["abords", "sol", "relief", "bordure", "marquage", "vegetation"]


def _fmt(x: float) -> str:
    s = f"{x:.2f}"
    return "0.00" if s == "-0.00" else s


def _num_fr(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def _esc(t: str) -> str:
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


class Plan:
    def __init__(self, sc: Scene, echelle: float = ECHELLE):
        self.sc = sc
        self.k = float((sc.d.get("plan") or {}).get("echelle", echelle))
        # emprise en XY : profil + abords + cotes
        pts = []
        n = 60
        for q in range(n + 1):
            s = sc.L * q / n
            pts.append(sc.trace.point(s, sc.t_limite(0, s) + ABORDS_M + 5.0))                 # chaîne et étiquettes
            pts.append(sc.trace.point(s, sc.t_limite(len(sc.limites) - 1, s) - ABORDS_M - 2.5))  # chaînage
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        self.xmin, self.xmax = min(xs) - 9.0, max(xs) + 9.0
        self.ymin, self.ymax = min(ys), max(ys)
        self.larg = int(math.ceil((self.xmax - self.xmin) * self.k))
        self.haut = int(math.ceil((self.ymax - self.ymin) * self.k)) + CARTOUCHE_PX + BAS_PX
        self.out: list[str] = []

    # ------------------------------------------------------------------ repères
    def px(self, s: float, t: float):
        x, y = self.sc.trace.point(s, t)
        return (x - self.xmin) * self.k, (self.ymax - y) * self.k + CARTOUCHE_PX

    def px_hors(self, s: float, t: float):
        """Point (s, t) prolongé hors du tracé (s < 0 ou s > L) le long de la tangente."""
        sc = self.sc
        if 0.0 <= s <= sc.L:
            return self.px(s, t)
        s_b = 0.0 if s < 0 else sc.L
        x0, y0 = sc.trace.point(s_b, t)
        x1, y1 = sc.trace.point(s_b + (0.01 if s_b == 0.0 else -0.01), t)
        dx, dy = (x1 - x0) / 0.01, (y1 - y0) / 0.01
        if s_b != 0.0:
            dx, dy = -dx, -dy
        x, y = x0 + dx * (s - s_b), y0 + dy * (s - s_b)
        return (x - self.xmin) * self.k, (self.ymax - y) * self.k + CARTOUCHE_PX

    def chemin(self, st, densifier=True) -> str:
        pts = list(st)
        if densifier and self.sc.trace.courbe():
            dens = []
            for a, b in zip(pts, pts[1:] + pts[:1]):
                dens.append(a)
                n = int(abs(b[0] - a[0]) / 0.5)
                for q in range(1, n):
                    u = q / n
                    dens.append((a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])))
            pts = dens
        xy = [self.px(s, t) for s, t in pts]
        return "M " + " L ".join(f"{_fmt(x)} {_fmt(y)}" for x, y in xy) + " Z"

    # ------------------------------------------------------------------ dessin
    def poly(self, st, couleur, opacite=None, trait=None):
        fill = COULEURS.get(couleur, couleur if couleur.startswith("#") else "#ff00ff")
        op = f' fill-opacity="{opacite}"' if opacite is not None else ""
        if trait == "meme":                      # liseré de la couleur du fond : masque les joints d'anticrénelage
            trait = fill
        tr = f' stroke="{trait}" stroke-width="0.6"' if trait else ""
        self.out.append(f'<path d="{self.chemin(st)}" fill="{fill}"{op}{tr}/>')

    def poly_trous(self, anneaux, couleur):
        fill = COULEURS.get(couleur, couleur)
        d = " ".join(self.chemin(a, densifier=False) for a in anneaux)
        self.out.append(f'<path d="{d}" fill="{fill}" fill-rule="evenodd"/>')

    def texte(self, x, y, txt, taille=13, ancre="start", couleur="#1b1b1b", gras=False, rot=None, fond=False):
        poids = ' font-weight="bold"' if gras else ""
        tr = f' transform="rotate({_fmt(rot)} {_fmt(x)} {_fmt(y)})"' if rot is not None else ""
        if fond:
            w = 0.56 * taille * len(txt)
            x0 = x - (w if ancre == "end" else w / 2 if ancre == "middle" else 0)
            self.out.append(f'<rect x="{_fmt(x0 - 2)}" y="{_fmt(y - taille)}" width="{_fmt(w + 4)}" '
                            f'height="{_fmt(taille * 1.3)}" fill="#ffffff" fill-opacity="0.8"{tr}/>')
        self.out.append(f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-family="Helvetica" font-size="{taille}" '
                        f'fill="{couleur}" text-anchor="{ancre}"{poids}{tr}>{_esc(txt)}</text>')

    def ligne(self, a, b, couleur="#1b1b1b", ep=1.0):
        self.out.append(f'<line x1="{_fmt(a[0])}" y1="{_fmt(a[1])}" x2="{_fmt(b[0])}" y2="{_fmt(b[1])}" '
                        f'stroke="{couleur}" stroke-width="{ep}"/>')

    # ------------------------------------------------------------------ couches
    def abords(self):
        sc = self.sc
        ab = sc.d.get("abords") or {}
        for cote, i, sg in (("gauche", 0, 1.0), ("droite", len(sc.limites) - 1, -1.0)):
            lu = lire_abord(ab.get(cote), f"abords.{cote}")
            if not lu:
                continue
            mat, larg = lu
            larg = min(larg or ABORDS_M, ABORDS_M)        # le plan montre au plus ABORDS_M m d'abords
            ss = sc.s_points()
            haut = [(s, sc.t_limite(i, s)) for s in ss]
            bas = [(s, sc.t_limite(i, s) + sg * larg) for s in reversed(ss)]
            self.poly(haut + bas, mat, 0.55)     # abords plus clairs que le profil

    def couches(self):
        sc = self.sc
        prims = sorted(enumerate(sc.primitives),
                       key=lambda ip: (ORDRE_CALQUES.index(ip[1]["calque"]), 0 if ip[1].get("fond") else 1, ip[0]))
        for _, p in prims:
            if p["forme"] == "poly":
                self.poly(p["st"], p["couleur"], OPACITE.get(p["couleur"]), "meme" if p.get("fond") else None)
                if p.get("role") == "BEV":
                    self.plots_bev(p["st"])
            elif p["forme"] == "poly_trous":
                self.poly_trous(p["anneaux"], p["couleur"])
            elif p["forme"] == "arbre":
                self.arbre(p["s"], p["t"], p["rayon"])

    def plots_bev(self, st):
        """Plots de la BEV (entraxe 75 mm, catalogue bev_dalle_beton_600x420x60) : dessinés à 150 mm (lisibilité)."""
        s0, s1 = min(p[0] for p in st), max(p[0] for p in st)
        t0, t1 = min(p[1] for p in st), max(p[1] for p in st)
        pas = 0.15
        ns, nt = int((s1 - s0) / pas), int((t1 - t0) / pas)
        r = max(0.6, 0.025 * self.k)
        for i in range(ns):
            for j in range(nt):
                x, y = self.px(s0 + (i + 0.5) * pas, t0 + (j + 0.5) * pas)
                self.out.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="{_fmt(r)}" fill="#9c978b"/>')

    def arbre(self, s, t, rayon):
        x, y = self.px(s, t)
        self.out.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="{_fmt(rayon * self.k)}" fill="#2f5d2b" '
                        f'fill-opacity="0.45" stroke="#244a21" stroke-width="1"/>')
        self.out.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="{_fmt(0.18 * self.k)}" fill="#5b4330"/>')

    # ------------------------------------------------------------------ cotes
    def chaine_transversale(self, s_ref: float, s_trace: float, cote_texte: str):
        """Chaîne de cotes perpendiculaire à l'axe, tracée à l'abscisse s_trace (hors tronçon)."""
        sc = self.sc
        ts = [sc.t_limite(i, s_ref) for i in range(len(sc.limites))]
        pts = [self.px_hors(s_trace, t) for t in ts]
        self.ligne(pts[0], pts[-1], "#333333", 0.8)
        for (x, y) in pts:
            self.out.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="2" fill="#333333"/>')
        dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
        ang = math.degrees(math.atan2(dy, dx))
        rot = ang + (180 if (ang > 90 or ang < -90) else 0)
        petit = 0
        for j, b in enumerate(sc.bandes):
            w = ts[j] - ts[j + 1]
            if w < 0.05:
                continue
            xm, ym = 0.5 * (pts[j][0] + pts[j + 1][0]), 0.5 * (pts[j][1] + pts[j + 1][1])
            off = 12
            if w * self.k < 26:                  # bande étroite : étiquette décalée en quinconce
                petit += 1
                off = 12 + 22 * (petit % 2 + 1)
            off = -off if cote_texte == "avant" else off
            # décalage du texte le long de la tangente (hors de la chaîne)
            tx, ty = self.px_hors(s_trace + (0.5 if off > 0 else -0.5), ts[j] * 0 + 0.5 * (ts[j] + ts[j + 1]))
            vx, vy = tx - xm, ty - ym
            nrm = math.hypot(vx, vy) or 1.0
            ux, uy = vx / nrm, vy / nrm
            xt, yt = xm + ux * abs(off) * (1 if off > 0 else -1), ym + uy * abs(off) * (1 if off > 0 else -1)
            self.texte(xt, yt + 4, _num_fr(w), 12, "middle", rot=rot)
        tot = ts[0] - ts[-1]
        xe, ye = pts[0]
        self.texte(xe, ye - 8, f"emprise {_num_fr(tot)} m", 12, "middle", gras=True)

    def chaine_longitudinale(self):
        sc = self.sc
        t_haut = max(sc.t_limite(0, s) for s in sc.s_points()) + ABORDS_M + 1.0
        pts = sorted({_r(c["s"], 3) for c in sc.cotes_s if -EPS_S <= c["s"] <= sc.L + EPS_S} | {0.0, _r(sc.L, 3)})
        noms = {}
        for c in sc.cotes_s:
            noms.setdefault(_r(c["s"], 3), [])
            if c["texte"] and c["texte"] not in noms[_r(c["s"], 3)]:
                noms[_r(c["s"], 3)].append(c["texte"])
        n = 80
        base = [self.px(sc.L * q / n, t_haut) for q in range(n + 1)]
        self.out.append('<path d="M ' + " L ".join(f"{_fmt(x)} {_fmt(y)}" for x, y in base) +
                        '" fill="none" stroke="#333333" stroke-width="0.8"/>')
        dernier_x = -1e9
        rang = 0
        for s in pts:
            x, y = self.px(s, t_haut)
            x2, y2 = self.px(s, t_haut - 0.6)
            self.ligne((x, y - 6), (x2, y2 + 2), "#333333", 0.8)
            lab = " / ".join(noms.get(s, []))
            rang = rang + 1 if x - dernier_x < 70 else 0
            dernier_x = x
            self.texte(x, y - 10 - 26 * (rang % 3), f"{_num_fr(s, 2)}" + (f" {lab}" if lab else ""), 11, "middle",
                       couleur="#123a6b", fond=True)
        # distances entre repères consécutifs (sous la ligne)
        for a, b in zip(pts, pts[1:]):
            if b - a < 0.5:
                continue
            xa, ya = self.px(0.5 * (a + b), t_haut)
            if (b - a) * self.k < 34:
                continue
            self.texte(xa, ya + 13, _num_fr(b - a, 2), 10, "middle", couleur="#333333")

    def chainage(self):
        sc = self.sc
        t_bas = min(sc.t_limite(len(sc.limites) - 1, s) for s in sc.s_points()) - ABORDS_M - 0.8
        s = 0.0
        while s <= sc.L + 1e-6:
            x, y = self.px(s, t_bas)
            x2, y2 = self.px(s, t_bas + 0.5)
            self.ligne((x, y), (x2, y2), "#222222", 1.0)
            self.texte(x, y + 14, f"{int(round(s))} m", 11, "middle", couleur="#222222")
            s += 10.0

    def cartouche(self):
        sc = self.sc
        m = sc.mesures
        self.out.append(f'<rect x="0" y="0" width="{self.larg}" height="{CARTOUCHE_PX - 4}" fill="#f7f6f2"/>')
        self.texte(14, 26, f"{sc.id} — {sc.titre}", 20, gras=True)
        ctx = (f"longueur {_num_fr(sc.L, 2)} m · {'agglomération' if sc.agglo else 'hors agglomération'} · "
               f"{int(sc.vitesse)} km/h (V15 {int(sc.v15)}) · u = {_num_fr(sc.u, 3)} m · "
               f"échelle {int(self.k)} px/m · s croissant vers la droite, t > 0 à gauche · fichier {sc.chemin.name}")
        self.texte(14, 48, ctx, 12)
        lims = []
        for lim in sc.limites:
            if lim["nature"] == "ligne":
                lims.append(f"{lim['id']} : {lim['modulation']} {int(lim['k'])}u ({_num_fr(lim['k'] * sc.u)})")
            elif lim["nature"] == "bordure":
                lims.append(f"{lim['id']} : {lim['profil']} vue {_num_fr(lim['vue'])}" +
                            (f" + {lim['caniveau']}" if lim.get("caniveau") else ""))
        self._texte_long(14, 68, "Limites : " + " ; ".join(lims), 11, 2)
        att = sc.d["attendus"]
        txt = "Attendus : " + " ; ".join(f"{k} = {_court(v)}" for k, v in att.items())
        self._texte_long(14, 100, txt, 11, 3, couleur="#123a6b")

    def _texte_long(self, x, y, txt, taille, lignes_max, couleur="#1b1b1b"):
        par_ligne = max(40, int((self.larg - 2 * x) / (0.53 * taille)))
        morceaux, cur = [], ""
        for mot in txt.split(" "):
            if len(cur) + len(mot) + 1 > par_ligne:
                morceaux.append(cur)
                cur = mot
            else:
                cur = (cur + " " + mot).strip()
        morceaux.append(cur)
        if len(morceaux) > lignes_max:
            morceaux = morceaux[:lignes_max]
            morceaux[-1] = morceaux[-1][:-2] + " …"
        for q, l in enumerate(morceaux):
            self.texte(x, y + q * (taille + 4), l, taille, couleur=couleur)

    def svg(self) -> str:
        self.out = []
        self.abords()
        self.couches()
        self.chaine_transversale(0.0, -4.5, "arriere")
        self.chaine_transversale(self.sc.L, self.sc.L + 4.5, "avant")
        self.chaine_longitudinale()
        self.chainage()
        self.cartouche()
        tete = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.larg}" height="{self.haut}" '
                f'viewBox="0 0 {self.larg} {self.haut}">\n'
                f'<title>{_esc(self.sc.id)} — plan coté de contrôle</title>\n'
                f'<rect x="0" y="0" width="{self.larg}" height="{self.haut}" fill="#ffffff"/>\n')
        return tete + "\n".join(self.out) + "\n</svg>\n"


EPS_S = 1e-6


def _court(v) -> str:
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_court(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_court(x) for x in v) + "]"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def ecrire_svg(sc: Scene, chemin) -> dict:
    p = Plan(sc)
    texte = p.svg()
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    Path(chemin).write_bytes(texte.encode("utf-8"))
    return {"svg": str(chemin), "largeur_px": p.larg, "hauteur_px": p.haut, "echelle_px_m": p.k,
            "repere": {"xmin": p.xmin, "ymax": p.ymax, "cartouche_px": CARTOUCHE_PX}}
