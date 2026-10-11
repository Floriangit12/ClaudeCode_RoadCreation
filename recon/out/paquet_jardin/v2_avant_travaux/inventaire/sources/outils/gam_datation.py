#!/usr/bin/env python
"""Datation et nature des couches GAM du dépôt (levé topo « Meylan_Topo.dwg » et PCRS vecteur).

1. Identité entre data/sites/paquet_jardin/vector/gam_topo_sol_* (WGS84) et data/sites/paquet_jardin/etat_2026/* (L93).
2. Marquages du levé topo : part de longueur présente sur l'ortho PCRS du 10/05/2022 (couverture de peinture
   calculée par pipeline/marking_contrast.py : data/sites/paquet_jardin/marquages/contraste_marquages_gam.geojson),
   par zone (travaux 2025 / hors travaux) et par distance au centre.
3. Bordures du levé topo comparées au PCRS vecteur (date_leve 2019, producteur Geofit) : part de longueur à ≤ 0,30 m
   d'une ligne PCRS, et réciproquement, par zone.
4. Cartes : levé topo / PCRS 2019 sur l'ortho 2022 (cœur ± 90 m et site ± 150 m).

Usage : python -I gam_datation.py <racine_depot>
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

RACINE = Path(sys.argv[1]).resolve()
SORTIE = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources"
V = RACINE / "data/sites/paquet_jardin/vector"
E26 = RACINE / "data/sites/paquet_jardin/etat_2026"
O = (917279.43, 6460289.98)
T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
EU = np.array([math.sin(math.radians(44.0)), math.cos(math.radians(44.0))])   # axe de Verdun (u > 0 vers le NE)
EV = np.array([-EU[1], EU[0]])                                                 # v > 0 vers le NO


def plat(c):
    if isinstance(c[0], (int, float)):
        return [c]
    return [q for s in c for q in plat(s)]


def lignes(geom, wgs=True):
    """Liste de polylignes (np.array N x 2, repère local) d'une géométrie GeoJSON."""
    t = geom["type"]
    cs = geom["coordinates"]
    if t == "LineString":
        parts = [cs]
    elif t in ("MultiLineString", "Polygon"):
        parts = cs
    elif t == "MultiPolygon":
        parts = [r for p in cs for r in p]
    else:
        parts = [[cs]] if t == "Point" else []
    out = []
    for p in parts:
        if wgs:
            xy = [T.transform(q[0], q[1]) for q in p]
        else:
            xy = [(q[0], q[1]) for q in p]
        out.append(np.array([(x - O[0], y - O[1]) for x, y in xy]))
    return out


def charger(p: Path, wgs=True):
    fs = json.loads(p.read_text(encoding="utf-8"))["features"]
    return [(f, lignes(f["geometry"], wgs)) for f in fs if f.get("geometry")]


# --------------------------------------------------------------------------- zone des travaux 2025
VERCORS = []


def axe_vercors():
    d = json.loads((V / "osm_roads.geojson").read_text(encoding="utf-8"))
    for f in d["features"]:
        if f["properties"].get("name") == "Avenue du Vercors":
            VERCORS.extend(lignes(f["geometry"]))


def d_poly(p, L):
    best = 1e9
    for a, b in zip(L[:-1], L[1:]):
        ab = b - a
        l2 = float(ab @ ab)
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, float((p - a) @ ab) / l2))
        best = min(best, float(np.hypot(*(p - a - t * ab))))
    return best


def zone(p):
    """travaux : disque r ≤ 40 m ∪ Verdun SO (u ∈ [-115, 0], |v| ≤ 22 m : terre-plein, arrêts, encoche)
    ∪ avenue du Vercors (≤ 14 m de l'axe OSM ; trottoirs refaits jusqu'au 30/01/2026). Sinon hors_travaux."""
    if math.hypot(*p) <= 40:
        return "travaux"
    u, v = float(p @ EU), float(p @ EV)
    if -115 <= u <= 0 and abs(v) <= 22:
        return "travaux"
    if any(d_poly(p, L) <= 14 for L in VERCORS):
        return "travaux"
    return "hors_travaux"


def bande_r(p):
    r = math.hypot(*p)
    return "r<=35" if r <= 35 else "35<r<=80" if r <= 80 else "80<r<=150" if max(abs(p[0]), abs(p[1])) <= 150 else "hors_site"


def echantillons(L, pas=0.25):
    out = []
    for a, b in zip(L[:-1], L[1:]):
        n = max(1, int(np.hypot(*(b - a)) / pas))
        for k in range(n):
            out.append(a + (b - a) * (k + 0.5) / n)
    return out


class Grille:
    def __init__(self, polys, c=1.0):
        self.c = c
        self.seg = []
        self.g = defaultdict(list)
        for L in polys:
            for a, b in zip(L[:-1], L[1:]):
                i = len(self.seg)
                self.seg.append((a, b))
                x0, x1 = sorted((a[0], b[0]))
                y0, y1 = sorted((a[1], b[1]))
                for ix in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
                    for iy in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
                        self.g[(ix, iy)].append(i)

    def dist(self, p, rmax=1.0):
        best = 1e9
        k = int(math.ceil(rmax / self.c))
        ix, iy = int(math.floor(p[0] / self.c)), int(math.floor(p[1] / self.c))
        vus = set()
        for a in range(-k, k + 1):
            for b in range(-k, k + 1):
                for i in self.g.get((ix + a, iy + b), ()):
                    if i in vus:
                        continue
                    vus.add(i)
                    s0, s1 = self.seg[i]
                    ab = s1 - s0
                    l2 = float(ab @ ab)
                    t = 0.0 if l2 == 0 else max(0.0, min(1.0, float((p - s0) @ ab) / l2))
                    best = min(best, float(np.hypot(*(p - s0 - t * ab))))
        return best


def couverture(src_polys, ref_polys, tol=0.30):
    """Longueur (m) des sources par (zone, bande) et part à ≤ tol d'une référence."""
    g = Grille(ref_polys)
    acc = defaultdict(lambda: [0.0, 0.0])
    for L in src_polys:
        for p in echantillons(L):
            z, b = zone(p), bande_r(p)
            if b == "hors_site":
                continue
            ok = g.dist(p) <= tol
            for k in ((z, b), (z, "tout"), ("site", b), ("site", "tout")):
                acc[k][0] += 0.25
                acc[k][1] += 0.25 * ok
    return {f"{z}|{b}": dict(longueur_m=round(v[0], 1), part_retrouvee=round(v[1] / v[0], 3) if v[0] else None)
            for (z, b), v in sorted(acc.items())}


def concordance(src_polys, ref_polys, tol=0.30, voisinage=3.0):
    """Là où les deux couches se recouvrent (référence à ≤ voisinage m), part de la longueur source à ≤ tol m de la
    référence ; distance médiane. Mesure la coïncidence géométrique indépendamment des lacunes de couverture."""
    g = Grille(ref_polys, c=1.0)
    acc = defaultdict(lambda: [0.0, 0.0, []])
    for L in src_polys:
        for p in echantillons(L):
            b = bande_r(p)
            if b == "hors_site":
                continue
            dd = g.dist(p, rmax=voisinage)
            if dd > voisinage:
                continue
            z = zone(p)
            for k in ((z, b), (z, "tout"), ("site", "tout")):
                acc[k][0] += 0.25
                acc[k][1] += 0.25 * (dd <= tol)
                acc[k][2].append(dd)
    return {f"{z}|{b}": dict(longueur_m=round(v[0], 1), part_a_moins_de_tol=round(v[1] / v[0], 3) if v[0] else None,
                             ecart_median_m=round(float(np.median(v[2])), 3) if v[2] else None)
            for (z, b), v in sorted(acc.items())}


# --------------------------------------------------------------------------- cartes
BLEU, ORANGE, AQUA, VIOLET = (42, 120, 214), (235, 104, 52), (27, 175, 122), (74, 58, 167)
ENCRE, ENCRE2 = (11, 11, 11), (82, 81, 78)


def police(t, gras=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if gras else "C:/Windows/Fonts/arial.ttf", t)
    except OSError:
        return ImageFont.load_default()


def fond(demi, res):
    n = int(2 * demi / res)
    base = Image.new("RGB", (n, n), (240, 240, 238))
    x0, y1 = O[0] - demi, O[1] + demi
    for jgw in sorted((RACINE / "data/sites/paquet_jardin/ortho5cm_2022").glob("*.jgw")):
        a = [float(v) for v in jgw.read_text().split()]
        X0, Y0 = a[4] - a[0] / 2, a[5] - a[3] / 2
        if X0 > x0 + 2 * demi or X0 + 50 < x0 or Y0 < y1 - 2 * demi or Y0 - 50 > y1:
            continue
        im = Image.open(jgw.with_suffix(".jpg"))
        k = res / a[0]
        im = im.resize((round(im.size[0] / k), round(im.size[1] / k)), Image.LANCZOS)
        base.paste(im, (round((X0 - x0) / res), round((y1 - Y0) / res)))
    g = base.convert("L").convert("RGB")
    return Image.blend(g, Image.new("RGB", g.size, (252, 252, 251)), 0.35)


def carte(chemin, demi, res, couches_, titre, sous_titre, zone_travaux=True):
    base = fond(demi, res)
    d = ImageDraw.Draw(base)

    def px(p):
        return ((p[0] + demi) / res, (demi - p[1]) / res)
    if zone_travaux:                                   # contour de la zone « travaux » (raster de la fonction zone)
        n = base.size[0]
        pas = 1.0
        m = {}
        for i in range(int(2 * demi / pas)):
            for j in range(int(2 * demi / pas)):
                p = np.array([-demi + (i + 0.5) * pas, demi - (j + 0.5) * pas])
                m[(i, j)] = zone(p) == "travaux"
        for (i, j), v in m.items():
            if v and (not m.get((i + 1, j), False) or not m.get((i - 1, j), False) or not m.get((i, j + 1), False) or not m.get((i, j - 1), False)):
                u, w = (i + 0.5) * pas / res, (j + 0.5) * pas / res
                d.ellipse([u - 1.5, w - 1.5, u + 1.5, w + 1.5], fill=VIOLET)
    for polys, col, w in couches_:
        for L in polys:
            pts = [px(q) for q in L]
            if len(pts) >= 2:
                d.line(pts, fill=col, width=w)
    n = base.size[0]
    H0 = 128
    img = Image.new("RGB", (n, n + H0 + 64), (252, 252, 251))
    img.paste(base, (0, H0))
    d = ImageDraw.Draw(img)
    d.text((16, 10), titre, fill=ENCRE, font=police(26, True))
    d.text((16, 46), sous_titre, fill=ENCRE2, font=police(15))
    y = 72
    x = 16
    for lab, col in (("levé topo GAM « Meylan_Topo.dwg » (bordures)", BLEU), ("levé topo GAM (marquages)", AQUA),
                     ("PCRS vecteur GAM, date_leve 2019 (bordures)", ORANGE)):
        d.line([(x, y + 9), (x + 28, y + 9)], fill=col, width=5)
        d.text((x + 36, y), lab, fill=ENCRE, font=police(15))
        x += 60 + d.textlength(lab, font=police(15))
        if x > n - 380:
            x, y = 16, y + 24
    if zone_travaux:
        d.ellipse([x + 8, y + 5, x + 16, y + 13], fill=VIOLET)
        d.text((x + 24, y), "limite de la zone des travaux 2025 (approchée)", fill=ENCRE, font=police(15))
    yb = n + H0 + 14
    L = 25 / res
    d.rectangle([16, yb, 16 + L, yb + 8], fill=ENCRE)
    d.text((24 + L, yb - 6), "25 m", fill=ENCRE, font=police(15))
    d.text((80 + L, yb - 6), "Nord en haut. Fond : ortho PCRS 5 cm du 10/05/2022 (CRAIG / GAM, Licence Ouverte).", fill=ENCRE2, font=police(14))
    d.text((80 + L, yb + 12), "Vecteurs : Grenoble-Alpes Métropole, WFS geoflux (extraction du 06/10/2026).", fill=ENCRE2, font=police(14))
    img.save(chemin, optimize=True)


def main():
    axe_vercors()
    res = dict(genere="outils/gam_datation.py", date="2026-10-11",
               zone_travaux=("disque r ≤ 40 m ∪ Verdun SO (u ∈ [-115, 0] m, |v| ≤ 22 m) ∪ avenue du Vercors (≤ 14 m de l'axe OSM) ; "
                             "u selon l'axe de Verdun (44°), v vers le NO"))
    # 1. identité vector/gam_topo_sol_* et etat_2026
    pairs = [("bordure_lin", "bordure_lin_L93"), ("bordure_pct", "bordure_pct_L93"), ("arbre_pct", "arbre_pct_L93"),
             ("caniveau_lin", "caniveau_lin_L93"), ("limite_revetement_lin", "limite_revetement_lin_L93"),
             ("signalisation_horizontale_lin", "signalisation_horizontale_lin_L93"),
             ("signalisation_horizontale_pct", "signalisation_horizontale_pct_L93")]
    ident = {}
    for a, b in pairs:
        A = charger(V / f"gam_topo_sol_{a}.geojson")
        B = charger(E26 / f"{b}.geojson", wgs=False)
        ecart = 0.0
        props = 0
        for (fa, la), (fb, lb) in zip(A, B):
            props += fa["properties"] == fb["properties"]
            for pa, pb in zip(la, lb):
                if len(pa) == len(pb):
                    ecart = max(ecart, float(np.max(np.hypot(*(pa - pb).T))))
                else:
                    ecart = float("inf")
        ident[a] = dict(n_vector=len(A), n_etat_2026=len(B), proprietes_identiques=props, ecart_max_m=round(ecart, 4))
    res["identite_vector_etat2026"] = ident
    # 2. marquages : couverture de peinture sur l'ortho 2022
    mq = json.loads((RACINE / "data/sites/paquet_jardin/marquages/contraste_marquages_gam.geojson").read_text(encoding="utf-8"))["features"]
    acc = defaultdict(lambda: [0.0, 0.0, 0, 0])
    for f in mq:
        for L in lignes(f["geometry"]):
            c = np.mean(L, axis=0)
            z, b = zone(c), bande_r(c)
            Lm = f["properties"].get("longueur_m") or 0.0
            vu = (f["properties"].get("couverture_peinture") or 0) >= 0.15
            for k in ((z, b), (z, "tout"), ("site", "tout")):
                acc[k][0] += Lm
                acc[k][1] += Lm * vu
                acc[k][2] += 1
                acc[k][3] += vu
    res["marquages_topo_vs_ortho2022"] = {
        "regle": "objet présent en 2022 si couverture_peinture ≥ 0,15 sur l'ortho PCRS 5 cm du 10/05/2022 (seuil de constats_verifies actuel-01)",
        "par_zone": {f"{z}|{b}": dict(n=v[2], n_presents_2022=v[3], longueur_m=round(v[0], 1),
                                      part_longueur_presente_2022=round(v[1] / v[0], 3) if v[0] else None)
                     for (z, b), v in sorted(acc.items())}}
    # 3. bordures topo vs PCRS 2019
    topo_b = [L for _, ls in charger(V / "gam_topo_sol_bordure_lin.geojson") for L in ls]
    pcrs = [L for _, ls in charger(V / "gam_limite_voirie_pcrs.geojson") for L in ls]
    res["bordures_topo_vs_pcrs2019"] = dict(
        tolerance_m=0.30,
        topo_retrouvees_dans_pcrs=couverture(topo_b, pcrs),
        pcrs_retrouvees_dans_topo=couverture(pcrs, topo_b),
        concordance_pcrs_vers_topo=concordance(pcrs, topo_b),
        concordance_topo_vers_pcrs=concordance(topo_b, pcrs))
    # 4. métadonnées
    res["metadonnees"] = dict(
        topo_sol=dict(fichier="Meylan_Topo.dwg", repertoire="/sigdata/Planotheque/esp_publics/MEYLAN/PLAN_GLOBAL/",
                      attributs_date=None, z="0 partout", resume_wfs=("« Issu des relevés de géomètres, ces données ne sont pas "
                      "nécessairement à jour… » (GetCapabilities geoflux)")),
        pcrs_vecteur=dict(date_leve="2019-01-01", producteur="geofit", precision_planimetrique_cm=10, precision_altimetrique_cm=20))
    (SORTIE / "gam_datation.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    # cartes
    topo_m = [L for _, ls in charger(V / "gam_topo_sol_signalisation_horizontale_lin.geojson") for L in ls]
    couches_ = [(topo_m, AQUA, 2), (pcrs, ORANGE, 4), (topo_b, BLEU, 2)]
    carte(SORTIE / "cartes/gam_topo_vs_pcrs2019_coeur.png", 75.0, 0.12, couches_,
          "Levé topo GAM et PCRS vecteur 2019 sur l'ortho du 10/05/2022",
          "Cœur ± 75 m. Bordures du levé (bleu) absentes du PCRS 2019 et de l'ortho 2022 = géométrie du projet C1 (2025).")
    carte(SORTIE / "cartes/gam_topo_vs_pcrs2019_site.png", 150.0, 0.25, couches_,
          "Levé topo GAM et PCRS vecteur 2019 – site ± 150 m",
          "Hors zone des travaux, le levé topo coïncide avec le PCRS 2019 et l'ortho 2022 ; dans la zone, il porte le projet C1.")
    print(json.dumps(res["identite_vector_etat2026"], ensure_ascii=False))
    print(json.dumps(res["marquages_topo_vs_ortho2022"]["par_zone"], ensure_ascii=False, indent=0))
    print(json.dumps(res["bordures_topo_vs_pcrs2019"], ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
