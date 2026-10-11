"""Cartes de contrôle de l'inventaire avant travaux sur l'ortho PCRS 5 cm du 10/05/2022 (données GAM ouvertes).

Usage : python -I carte.py
Sorties : cartes/carte_site.png (300 m, 0,25 m/px), cartes/carte_coeur.png (± 60 m, 0,08 m/px),
          cartes/carte_arret_reviree.png (arrêts La Revirée, état avant / après).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_at import O, RACINE, SORTIE, lire  # noqa: E402

ORTHO = RACINE / "data/sites/paquet_jardin/ortho5cm_2022"
COUL = {"arbre": (40, 200, 60), "lampadaire": (255, 220, 0), "feu": (255, 40, 40), "panneau": (30, 120, 255),
        "potelet": (255, 140, 0), "barriere": (200, 200, 200), "banc": (160, 90, 40), "abri_bus": (0, 220, 220),
        "poteau_arret": (0, 160, 160), "borne": (255, 0, 160), "armoire": (150, 0, 200), "poteau": (120, 70, 20),
        "corbeille": (90, 90, 90), "arceaux_velos": (0, 255, 160), "autre_mobilier": (255, 255, 255)}


def mosaique(x0, y0, x1, y1, res):
    W, H = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    im = Image.new("RGB", (W, H), (30, 30, 30))
    for jpg in sorted(ORTHO.glob("pcrs5cm_*.jpg")):
        jgw = [float(v) for v in jpg.with_suffix(".jgw").read_text().split()]
        tx0, ty1 = jgw[4] - jgw[0] / 2, jgw[5] - jgw[3] / 2
        t = Image.open(jpg)
        tw, th = t.size
        tx1, ty0 = tx0 + tw * jgw[0], ty1 + th * jgw[3]
        if tx1 < x0 or tx0 > x1 or ty1 < y0 or ty0 > y1:
            continue
        sw, sh = int(round(tw * jgw[0] / res)), int(round(th * -jgw[3] / res))
        t = t.resize((sw, sh), Image.LANCZOS)
        im.paste(t, (int(round((tx0 - x0) / res)), int(round((y1 - ty1) / res))))
    return im


def dessiner(nom, x0, y0, x1, y1, res, feats, exclus, titre, etiquettes=False, extra=None):
    im = mosaique(x0, y0, x1, y1, res).convert("RGB")
    im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), 0.35)
    dr = ImageDraw.Draw(im)
    try:
        ft = ImageFont.truetype("arial.ttf", 13)
        fb = ImageFont.truetype("arialbd.ttf", 18)
    except OSError:
        ft = fb = ImageFont.load_default()

    def px(x, y):
        return ((x - x0) / res, (y1 - y) / res)

    r = max(3, int(0.6 / res)) if res < 0.15 else 4
    for f in exclus:
        p, g = f["properties"], f["geometry"]
        if g["type"] != "Point":
            continue
        u, v = px(*g["coordinates"][:2])
        dr.line([u - r, v - r, u + r, v + r], fill=(255, 0, 0), width=2)
        dr.line([u - r, v + r, u + r, v - r], fill=(255, 0, 0), width=2)
    for f in feats:
        p, g = f["properties"], f["geometry"]
        c = COUL.get(p["type"], (255, 255, 255))
        if g["type"] == "LineString":
            dr.line([px(*q[:2]) for q in g["coordinates"]], fill=c, width=2)
            continue
        u, v = px(*g["coordinates"][:2])
        etat = p["etat_avant_travaux"]
        if etat == "present":
            dr.ellipse([u - r, v - r, u + r, v + r], fill=c, outline=(0, 0, 0))
        elif etat == "present_presume":
            dr.ellipse([u - r, v - r, u + r, v + r], outline=c, width=2)
        else:
            dr.rectangle([u - r, v - r, u + r, v + r], outline=c, width=1)
        if p.get("position_2026_l93"):
            a, b = px(*p["position_2026_l93"])
            dr.line([u, v, a, b], fill=(255, 0, 255), width=1)
            dr.ellipse([a - 2, b - 2, a + 2, b + 2], outline=(255, 0, 255))
        if etiquettes and p["type"] != "arbre":
            lab = (p.get("code") or p["type"][:4]) + ("" if etat == "present" else "?")
            dr.text((u + r + 1, v - 7), lab, fill=c, font=ft)
    if extra:
        extra(dr, px, ft)
    # légende
    y = 8
    dr.rectangle([6, 4, 330, 26 + 17 * (len(COUL) + 4)], fill=(0, 0, 0))
    dr.text((10, y), titre, fill=(255, 255, 255), font=fb)
    y += 24
    for k, c in COUL.items():
        dr.ellipse([12, y + 3, 22, y + 13], fill=c)
        dr.text((28, y), k, fill=(255, 255, 255), font=ft)
        y += 17
    dr.text((12, y), "plein = présent, cercle = présumé, carré = incertain", fill=(255, 255, 255), font=ft)
    dr.text((12, y + 17), "croix rouge = exclu ; magenta = position 2026", fill=(255, 255, 255), font=ft)
    dr.text((12, y + 34), "fond : ortho PCRS 5 cm GAM 10/05/2022", fill=(200, 200, 200), font=ft)
    out = SORTIE / "cartes" / nom
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)
    print(out, im.size)


def main():
    feats = lire(SORTIE / "objets_avant_travaux.geojson")["features"]
    exclus = lire(SORTIE / "objets_exclus.geojson")["features"]
    X, Y = O[0], O[1]
    dessiner("carte_site.png", X - 150, Y - 150, X + 150, Y + 150, 0.25, feats, exclus,
             "Objets avant travaux (site 300 m)")
    dessiner("carte_coeur.png", X - 50, Y - 45, X + 50, Y + 55, 0.08, feats, exclus,
             "Objets avant travaux (coeur)", etiquettes=True)
    dessiner("carte_arret_reviree.png", X - 75, Y - 70, X + 5, Y - 20, 0.06, feats, exclus,
             "Arrêts La Revirée : avant / 2026", etiquettes=True)


if __name__ == "__main__":
    main()
