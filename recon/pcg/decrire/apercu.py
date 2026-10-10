"""Planche de contrôle (PNG) de la description v2, vue de dessus sur l'ortho 2022 du paquet.

Usage :
    python recon/pcg/decrire/apercu.py SORTIE.png [--emprise x0 y0 x1 y1] [--res 0.05] [--etiquettes]
                                       [--base DOSSIER_BASE]
Emprise en repère local (m), défaut : zone pilote ; base : recon/out/paquet_jardin/v2/description/base.
Bordures colorées par profil (bateaux en rouge épais, chartières en magenta, trait vert = côté haut),
surfaces teintées par matériau, îlots par remplissage (contour magenta), BEV en cyan, blocs
CHARTIERE GAM en cercles verts. Fond : textures/albedo_macro_8192.jpg (8192 px pour 300 m centrés sur O).
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import contexte as ctx
from commun import PAQUET, SORTIE, abscisses, anneaux, lire_geojson, normale_gauche, point_a, repere, sous_polyligne

COUL_PROFIL = {"T2": (255, 255, 255), "T3": (255, 150, 40), "A2": (255, 230, 0), "P1": (150, 150, 150),
               "T2_bateau": (255, 40, 40), "QUAI_BUS": (0, 160, 255), "MURET_TALUS": (120, 60, 0)}
COUL_MAT = {"enrobe_trottoir": (210, 120, 40), "enrobe_bbsg_ancien": (90, 90, 150), "enrobe_bbsg_neuf_2025": (50, 50, 210),
            "enrobe_piste_cyclable": (0, 170, 220), "gazon_tondu": (40, 160, 40), "herbe_haute": (110, 200, 60),
            "brf_bois_concasse": (150, 75, 20), "gravier_concasse_6_10": (215, 215, 205), "beton_balaye": (200, 190, 170),
            "paves_beton": (230, 80, 160), "terre_nue": (120, 90, 60), "stabilise_beige": (220, 200, 140),
            "noue_plantee": (20, 110, 60)}
COUL_REMPL = {"brf_bois_concasse": (190, 95, 25), "gravier_concasse_6_10": (235, 235, 225),
              "beton_balaye": (200, 190, 170), "enrobe_trottoir": (60, 60, 60)}


def police(t):
    for nom in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except OSError:
            pass
    return ImageFont.load_default()


def fond_ortho(x0, y0, x1, y1, res):
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(PAQUET / "textures/albedo_macro_8192.jpg")
    px = 300.0 / im.width
    box = ((x0 + 150) / px, (150 - y1) / px, (x1 + 150) / px, (150 - y0) / px)
    W, H = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    return im.transform((W, H), Image.EXTENT, box, Image.BILINEAR).convert("RGB")


def lire(base, nom):
    f = Path(base) / f"{nom}.geojson"
    return lire_geojson(f) if f.exists() else []


def planche(sortie, base=SORTIE / "base", emprise=None, res=0.05, etiquettes=False):
    x0, y0, x1, y1 = emprise or ctx.zone_pilote()["emprise"]
    img = fond_ortho(x0, y0, x1, y1, res)
    img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.35)
    d = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    k = max(1, int(round(0.05 / res)))
    f_pt, f_gd = police(11 * k), police(14 * k)

    def tp(p):
        return [((x - x0) / res, (y1 - y) / res) for x, y in np.asarray(p)[:, :2]]

    surfs = lire(base, "surfaces")
    for f in surfs:
        col = COUL_MAT.get(f["properties"]["revetement"]["materiau_id"], (255, 255, 255))
        for poly in anneaux(f["geometry"]):
            d.polygon(tp(repere(poly[0])), fill=col + (60,), outline=col + (160,))
    for f in lire(base, "ilots"):
        m = f["properties"]["remplissage"]["materiau_id"]
        col = COUL_REMPL.get(m, (255, 0, 255))
        for poly in anneaux(f["geometry"]):
            r = tp(repere(poly[0]))
            d.polygon(r, fill=col + (150,))
            d.line(r + r[:1], fill=(255, 0, 255, 255), width=2 * k)
        if etiquettes:
            c = repere(anneaux(f["geometry"])[0][0]).mean(axis=0, keepdims=True)
            d.text(tp(c)[0], f"{f['properties']['id']}\n{m}", fill=(255, 255, 255), font=f_gd)
    for f in lire(base, "ponctuels_sol"):
        for poly in anneaux(f["geometry"]):
            d.polygon(tp(repere(poly[0])), fill=(0, 255, 255, 210), outline=(0, 120, 120, 255))
    for f in lire(base, "bordures"):
        p = f["properties"]
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        for it in p["intervalles"]:
            seg = sous_polyligne(P, it["s0"], it["s1"])
            col = (255, 0, 255) if it["role"] == "chartiere" else COUL_PROFIL.get(it["profil"], (255, 0, 255))
            d.line(tp(seg), fill=col + (255,), width=(4 if it["role"] != "courant" else 2) * k)
        q, tg = point_a(P, abscisses(P)[-1] / 2)
        n = normale_gauche(tg)[0]
        d.line(tp([q[0], q[0] + n * 0.6]), fill=(0, 255, 0, 255), width=k)
        if etiquettes:
            d.text(tp([q[0] + n * 0.8])[0], p["id"][2:], fill=(255, 255, 160), font=f_pt)
    for b in ctx.chartieres_gam():
        (u, v), = tp([b["xy"]])
        r = 0.35 / res
        d.ellipse((u - r, v - r, u + r, v + r), outline=(0, 255, 0, 255), width=2 * k)
    z = ctx.zone_pilote()["anneau"]
    d.line(tp(np.vstack([z, z[:1]])), fill=(255, 0, 0, 220), width=2 * k)
    for gx in range(int(math.ceil(x0 / 10) * 10), int(x1) + 1, 10):
        d.line(tp([(gx, y0), (gx, y1)]), fill=(255, 255, 255, 40))
        d.text(tp([(gx + 0.2, y1 - 0.2)])[0], str(gx), fill=(255, 255, 255), font=f_pt)
    for gy in range(int(math.ceil(y0 / 10) * 10), int(y1) + 1, 10):
        d.line(tp([(x0, gy), (x1, gy)]), fill=(255, 255, 255, 40))
        d.text(tp([(x0 + 0.2, gy)])[0], str(gy), fill=(255, 255, 255), font=f_pt)
    mats = sorted({f["properties"]["revetement"]["materiau_id"] for f in surfs})
    lg = [(f"bordure {p}", c) for p, c in COUL_PROFIL.items()] + [("chartière", (255, 0, 255)), ("BEV", (0, 255, 255)),
                                                                     ("côté haut (gauche)", (0, 255, 0))]
    lg += [(f"îlot {m}", c) for m, c in COUL_REMPL.items()] + [(f"sol {m}", COUL_MAT.get(m, (255, 255, 255))) for m in mats]
    hl, f_lg = 15, police(12)
    bx, by = W - 240, H - 10 - hl * len(lg)
    d.rectangle((bx - 6, by - 6, W - 4, H - 4), fill=(0, 0, 0, 170))
    for i, (t, c) in enumerate(lg):
        d.rectangle((bx, by + i * hl, bx + 12, by + i * hl + 10), fill=c + (255,))
        d.text((bx + 18, by - 2 + i * hl), t, fill=(255, 255, 255), font=f_lg)
    Path(sortie).parent.mkdir(parents=True, exist_ok=True)
    img.save(sortie)
    return W, H


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sortie")
    ap.add_argument("--emprise", nargs=4, type=float)
    ap.add_argument("--res", type=float, default=0.05)
    ap.add_argument("--etiquettes", action="store_true")
    ap.add_argument("--base", default=str(SORTIE / "base"))
    a = ap.parse_args()
    W, H = planche(a.sortie, a.base, a.emprise, a.res, a.etiquettes)
    print(f"{a.sortie} ({W}x{H} px, {a.res} m/px)")


if __name__ == "__main__":
    main()
