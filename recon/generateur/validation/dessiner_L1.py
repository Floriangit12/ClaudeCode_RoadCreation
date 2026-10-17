# -*- coding: utf-8 -*-
"""Plans de contrôle du lot L1 : courbes de contrôle (sorties des HDA rg::*) dessinées en SVG puis PNG (PyMuPDF).

    python recon/generateur/validation/dessiner_L1.py [SCENE ...] [--tuiles]

Pour chaque scène (`recon/out/generateur/<scene>/l1/courbes_controle.json`) :
    l1/plan_l1.svg|png        rubans des bandes (couleur par type), limites (bordure, marquage, virtuelle…),
                              ligne de référence, cartouche (comptes, mesures Houdini)
    l1/detail_<nom>.png       agrandissements (transitions, courbes : sommets d'échantillonnage visibles)
    l1/profil_long.png        loi verticale de la chaussée (plateaux, dos-d'âne), exagération × 20
    l1/tuiles/<image>/        tuiles natives (recon/pcg/vision/decoupe.py image), avec --tuiles
Les dessins ne lisent que les sorties de Houdini : rien n'est recalculé ici (contrôle visuel de ce qui est fabriqué).
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
OUT = DEPOT / "recon" / "out" / "generateur"
DECOUPE = DEPOT / "recon" / "pcg" / "vision" / "decoupe.py"

COUL_BANDE = {
    "voie_circulation": "#5f6062", "voie_tourne_gauche": "#55575a", "voie_tourne_droite": "#55575a",
    "voie_bus": "#8e4a3b", "bande_cyclable": "#4f7d57", "piste_cyclable": "#a8563f", "voie_verte": "#b07a55",
    "stationnement": "#7d7f82", "livraison": "#7d7f82", "trottoir": "#d8ceb6", "quai_bus": "#c9bc9a",
    "chemin_pieton": "#d8ceb6", "terre_plein": "#6f9e4c", "bande_plantee": "#7aa857", "berme": "#86ad5f",
    "bande_derasee": "#8aa86a", "accotement_revetu": "#6c6d70", "zone_neutralisee": "#8d8f93", "separateur": "#3c3c3c",
    "talus": "#86ad5f", "fosse": "#5f7d4f", "noue": "#5f7d4f", "chaussee_partagee": "#66686c",
    "voie_centrale_banalisee": "#5a5c60", "rive_cyclable_cvcb": "#56795c", "voie_stockage": "#55575a",
    "voie_insertion": "#55575a", "voie_deceleration": "#55575a", "bande_arret_urgence": "#6c6d70", "voie_tram": "#7a6f62",
    "autre": "#ff00ff"}
COUL_BANDE_HERBE = {"herbe_haute", "gazon_tondu", "gazon_sec", "noue_plantee", "terre_nue", "terre_vegetale"}


def couleur_bande(b):
    if b["type"] in ("bande_derasee", "berme", "accotement_revetu") and b.get("materiau_id") in COUL_BANDE_HERBE:
        return "#86ad5f"
    return COUL_BANDE.get(b["type"], "#ff00ff")


def style_limite(nature):
    n = set(nature.split("+"))
    if "separateur" in n:
        return "#111111", 3.0, None
    if "bordure" in n:
        return "#1e1e1e", 2.4, None
    if "marquage" in n:
        return "#ffffff", 1.6, None
    if "changement_revetement" in n:
        return "#5a4632", 1.0, None
    return "#9a9a9a", 0.8, "4 3"


class Vue:
    def __init__(self, xmin, ymin, xmax, ymax, k, marge=24, entete=70):
        self.xmin, self.ymin, self.xmax, self.ymax, self.k = xmin, ymin, xmax, ymax, k
        self.m, self.h0 = marge, entete
        self.larg = int(math.ceil((xmax - xmin) * k + 2 * marge))
        self.haut = int(math.ceil((ymax - ymin) * k + 2 * marge + entete))
        self.out = []

    def px(self, x, y):
        return (x - self.xmin) * self.k + self.m, (self.ymax - y) * self.k + self.m + self.h0

    def chemin(self, xs, ys, ferme=False):
        pts = [self.px(x, y) for x, y in zip(xs, ys)]
        d = "M" + " L".join(f"{a:.2f},{b:.2f}" for a, b in pts)
        return d + (" Z" if ferme else "")

    def poly(self, xs, ys, fill, op=1.0):
        self.out.append(f'<path d="{self.chemin(xs, ys, True)}" fill="{fill}" fill-opacity="{op}" stroke="{fill}" '
                        f'stroke-width="0.6"/>')

    def ligne(self, xs, ys, coul, ep, tirets=None):
        da = f' stroke-dasharray="{tirets}"' if tirets else ""
        self.out.append(f'<path d="{self.chemin(xs, ys)}" fill="none" stroke="{coul}" stroke-width="{ep}"'
                        f' stroke-linejoin="round"{da}/>')

    def point(self, x, y, r, coul):
        a, b = self.px(x, y)
        self.out.append(f'<circle cx="{a:.2f}" cy="{b:.2f}" r="{r}" fill="{coul}"/>')

    def texte(self, x, y, txt, taille=13, coul="#1b1b1b", gras=False):
        g = ' font-weight="bold"' if gras else ""
        txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.out.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans, Arial" font-size="{taille}" fill="{coul}"'
                        f'{g}>{txt}</text>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.larg}" height="{self.haut}" '
                f'viewBox="0 0 {self.larg} {self.haut}">\n<rect x="0" y="0" width="{self.larg}" height="{self.haut}" '
                f'fill="#f4f2ec"/>\n' + "\n".join(self.out) + "\n</svg>\n")


def emprise(c, s_min=None, s_max=None):
    xs, ys = [], []
    for r in c["routes"]:
        for sec in r["sections"]:
            for lim in sec["limites"]:
                for s, x, y in zip(sec["s"], lim["x"], lim["y"]):
                    if (s_min is None or s >= s_min) and (s_max is None or s <= s_max):
                        xs.append(x)
                        ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def dessiner(c, vue, titre, sous_titre, points=False, s_min=None, s_max=None):
    def coupe(sec, vals):
        return [v for s, v in zip(sec["s"], vals) if (s_min is None or s >= s_min - 1e-9) and
                (s_max is None or s <= s_max + 1e-9)]
    for r in c["routes"]:
        for sec in r["sections"]:
            lims = sec["limites"]
            for b in sec["bandes"]:
                g, d = lims[b["rang"]], lims[b["rang"] + 1]
                xg, yg, xd, yd = coupe(sec, g["x"]), coupe(sec, g["y"]), coupe(sec, d["x"]), coupe(sec, d["y"])
                if len(xg) < 2:
                    continue
                vue.poly(xg + xd[::-1], yg + yd[::-1], couleur_bande(b))
        for sec in r["sections"]:
            for lim in sec["limites"]:
                xs, ys = coupe(sec, lim["x"]), coupe(sec, lim["y"])
                if len(xs) < 2:
                    continue
                coul, ep, da = style_limite(lim["nature"])
                if coul == "#ffffff":
                    vue.ligne(xs, ys, "#3a3a3a", ep + 1.2)
                vue.ligne(xs, ys, coul, ep, da)
                if points:
                    for x, y in zip(xs, ys):
                        vue.point(x, y, 1.6, "#d62828")
        rf = r["reference"]
        keep = [i for i, s in enumerate(rf["s"]) if (s_min is None or s >= s_min) and (s_max is None or s <= s_max)]
        vue.ligne([rf["x"][i] for i in keep], [rf["y"][i] for i in keep], "#c1121f", 1.0, "8 4")
        for i in keep:
            if rf["obligatoire"][i]:
                vue.point(rf["x"][i], rf["y"][i], 2.4, "#1d3557")
        for nom in ("debut", "fin"):
            e = r["extremites"].get(nom)
            if e:
                vue.ligne(e["x"], e["y"], "#e76f51", 1.4)
    vue.texte(vue.m, 24, titre, 16, gras=True)
    vue.texte(vue.m, 46, sous_titre, 12, "#333333")
    vue.texte(vue.m, 63, "rubans : couleur par type de bande ; limites : bordure (noir épais), marquage (blanc), "
                         "virtuelle (gris tireté) ; référence (rouge tireté) ; sommets obligatoires (points bleus)"
              + ("; sommets d'échantillonnage (points rouges)" if points else ""), 11, "#555555")


def png(svg_path, png_path, zoom=1.0):
    import pymupdf
    doc = pymupdf.open(str(svg_path))
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    pix.save(str(png_path))
    return pix.width, pix.height


def ecrire(vue, base: Path):
    svg = base.with_suffix(".svg")
    svg.write_text(vue.svg(), encoding="utf-8")
    return png(svg, base.with_suffix(".png"))


DETAILS = {          # scène -> [(nom, s_min, s_max, px/m, sommets)]
    "S03": [("avancees", 0.0, 32.5, 30, False)],
    "S09": [("rabattement", 35.0, 95.0, 22, True)],
    "S10": [("plateau", 40.0, 60.0, 40, True)],
    "S11": [("arc", 15.0, 45.0, 30, True)],
    "ex06_rabattement_2_vers_1": [("biseau", 80.0, 160.0, 14, True)],
    "ex09_elargissement_tourne_a_gauche": [("elargissement", 100.0, 150.0, 18, True)],
    "ex10_changement_de_profil": [("transition_80", 70.0, 105.0, 26, True), ("instantane_140", 130.0, 150.0, 40, True)],
    "E1_rue_clothoides": [("clothoide", 20.0, 60.0, 22, True)],
    "E2_rue_s_rabattement_ralentisseurs": [("s_rabattement", 60.0, 120.0, 16, True)],
    "E3_avenue_courbe_serree": [("interieur", 15.0, 45.0, 26, True)],
}


def profil_long(c, d: Path):
    """Une image par ralentisseur (plage où dz > 0, prolongée de 2 m) : dz(s) exagéré × 25, sommets en rouge."""
    r = c["routes"][0]
    pl = r["profil_long"]
    if not pl:
        return []
    S, Z = pl["s"], pl["dz"]
    plages, cur = [], None
    for s, z in zip(S, Z):
        if z > 1e-9:
            cur = [cur[0], s] if cur else [s, s]
        elif cur:
            plages.append(cur)
            cur = None
    out = []
    ex = 25.0
    for k, (sa, sb) in enumerate(plages):
        sa, sb = sa - 2.0, sb + 2.0
        idx = [i for i, s in enumerate(S) if sa <= s <= sb]
        Ss, Zs = [S[i] for i in idx], [Z[i] for i in idx]
        vue = Vue(sa, -0.01 * ex, sb, max(Zs) * ex + 0.01 * ex, 1000.0 / (sb - sa), entete=70)
        vue.ligne([sa, sb], [0, 0], "#9a9a9a", 0.8, "4 3")
        vue.ligne(Ss, [z * ex for z in Zs], "#1d3557", 1.6)
        for s, z in zip(Ss, Zs):
            vue.point(s, z * ex, 2.0, "#d62828")
        vue.texte(vue.m, 24, f"{c['scene']} : profil en long de la chaussée, s de {sa:.2f} à {sb:.2f} m "
                             "(rg::profils, sortie 4)", 16, gras=True)
        vue.texte(vue.m, 46, f"dz(s) exagéré × {ex:g} ; hauteur maximale {max(Zs):.3f} m ; {len(Ss)} sommets (rouges)",
                  12, "#333333")
        nom = f"profil_long_{k + 1}"
        out.append((nom, ecrire(vue, d / nom)))
    return out


def scene(nom, tuiles=False):
    d = OUT / nom / "l1"
    c = json.loads((d / "courbes_controle.json").read_text(encoding="utf-8"))
    ch = c["controles_houdini"]
    prod = []
    x0, y0, x1, y1 = emprise(c)
    k = min(12.0, 1450.0 / max(x1 - x0, 1.0), 1300.0 / max(y1 - y0, 1.0))
    vue = Vue(x0, y0, x1, y1, k)
    rs = c["routes"]
    lg = sum(r["longueur_m"] for r in rs)
    sous = (f"{len(rs)} route(s), {ch['n_sections']} section(s), {ch['n_limites']} limites, "
            f"{ch['n_rubans']} rubans ; L = {lg:.3f} m ; {sum(r['n_echantillons'] for r in rs)} sommets (pas min "
            f"{min(r['pas_min_m'] for r in rs):.3f} m) ; flèche majorée "
            f"{max(r['fleche_majorant_m'] for r in rs) * 1000:.3f} mm ; largeur min "
            f"{ch['largeur_min_m']:.3f} m ; jonctions discontinues {ch['jonctions_discontinues']}")
    dessiner(c, vue, f"{c['scene']} : courbes de contrôle du lot L1 (rg::lire_modele → rg::graphe → rg::profils)", sous)
    prod.append(("plan_l1", ecrire(vue, d / "plan_l1")))
    for (nd, sa, sb, kk, pts) in DETAILS.get(nom, []):
        x0, y0, x1, y1 = emprise(c, sa, sb)
        v = Vue(x0 - 1, y0 - 1, x1 + 1, y1 + 1, kk)
        dessiner(c, v, f"{c['scene']} : détail « {nd} » (s de {sa:g} à {sb:g} m)", sous, points=pts, s_min=sa, s_max=sb)
        prod.append((f"detail_{nd}", ecrire(v, d / f"detail_{nd}")))
    prod += profil_long(c, d)
    if tuiles:
        for nomi, _ in prod:
            subprocess.run([sys.executable, str(DECOUPE), "image", str(d / f"{nomi}.png"), str(d / "tuiles" / nomi)],
                           check=True, capture_output=True)
    return prod


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--tuiles", action="store_true")
    a = ap.parse_args()
    noms = a.scenes or sorted(p.parent.parent.name for p in OUT.glob("*/l1/courbes_controle.json"))
    for n in noms:
        prod = scene(n, a.tuiles)
        print(n, ", ".join(f"{p} {w}×{h}" for p, (w, h) in prod))


if __name__ == "__main__":
    main()
