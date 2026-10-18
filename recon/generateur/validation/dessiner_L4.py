"""Plan de contrôle du lot L4 (sans Houdini, PIL) : zone de conflit, trajectoires, ligne de guidage, points de conflit,
marques du lot (flèches, figurines), lignes finales et morceaux retirés, autour du centre du carrefour.

    python recon/generateur/validation/dessiner_L4.py [<scene> ...] [--demi 40]

Écrit recon/out/generateur/<scene>/l4/plan_l4.png (1092 × 1092 px, regardé en entier sans réduction).
Couleurs : zone de conflit jaune, faces de bordure grises, lignes finales blanches (ajouts du lot en cyan), morceaux
retirés rouges, marques du lot blanches bordées de cyan, trajectoires TD bleu / TAG rouge / TAD vert (vélos en
pointillé violet), ligne de guidage magenta, conflits (croisement rond, convergence triangle, divergence losange),
voies à la limite de jonction (entrantes vert, sortantes orange).
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

DEPOT = Path(__file__).resolve().parents[3]
OUT = DEPOT / "recon" / "out" / "generateur"
SCENES = ("J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe")
COUL = {"TD": (60, 140, 255), "TAG": (235, 50, 50), "TAD": (50, 200, 70)}
N = 1092


def charger(d, nom):
    return json.loads((d / nom).read_text(encoding="utf-8"))


def dessiner(scene, demi):
    d4 = OUT / scene / "l4"
    tr = charger(d4, "trajectoires.json")
    zo = charger(d4, "zone_conflit.json")
    gu = charger(d4, "guidage.json")
    co = charger(d4, "conflits.json")
    mq = charger(d4, "marques_l4.json")
    re_ = charger(d4, "lignes_retirees.json")
    l3 = charger(OUT / scene / "l3", "carrefours.json")
    c = tr["branches"][0]["centre"] if tr["branches"] else [0, 0, 0]
    k = N / (2 * demi)

    def px(p):
        return ((p[0] - c[0] + demi) * k, (c[1] + demi - p[1]) * k)

    im = Image.new("RGB", (N, N), (58, 58, 58))
    dr = ImageDraw.Draw(im, "RGBA")
    for z in zo["zones"]:
        dr.polygon([px(p) for p in z["points"]], fill=(255, 215, 50, 45), outline=(255, 215, 50, 255))
    for f in l3["faces"]:
        dr.line([px(p) for p in f["points"]], fill=(185, 185, 185), width=2)
    for e in mq["lignes_finales"]:
        dr.polygon([px(p) for p in e["xy"]], fill=(0, 229, 255) if e.get("rg_l4") else (255, 255, 255))
    for e in re_["morceaux"]:
        dr.polygon([px(p) for p in e["xy"]], fill=(255, 48, 48))
    for e in mq["marques_l4"]:
        dr.polygon([px(p) for p in e["xy"]], fill=(255, 255, 255), outline=(0, 229, 255))
    for t in tr["trajectoires"]:
        col = (170, 90, 230) if t["tags"] == "velo" else COUL.get(t["mouvement"], (150, 100, 200))
        dr.line([px(p) for p in t["points"]], fill=col, width=4 if t["guide"] else 2)
    for g in gu["lignes"]:
        dr.line([px(p) for p in g["points"]], fill=(255, 0, 255), width=2)
    for q in co["conflits"]:
        x, y = px(q["xy"])
        col = (255, 255, 0) if q["famille"] == "vl_vl" else (255, 150, 0)
        if q["type"] == "croisement":
            dr.ellipse([x - 5, y - 5, x + 5, y + 5], outline=col, width=2)
        elif q["type"] == "convergence":
            dr.polygon([(x, y - 6), (x - 6, y + 5), (x + 6, y + 5)], outline=col)
        else:
            dr.polygon([(x, y - 6), (x - 6, y), (x, y + 6), (x + 6, y)], outline=col)
    for v in tr["voies"]:
        x, y = px(v["xy"])
        dr.rectangle([x - 3, y - 3, x + 3, y + 3], fill=(0, 255, 0) if v["entrante"] else (255, 136, 0))
    dr.text((8, 8), f"{scene} - lot L4 ; {2 * demi:.0f} m de côté", fill=(255, 255, 255))
    f = d4 / "plan_l4.png"
    im.save(f)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--demi", type=float, default=40.0)
    a = ap.parse_args()
    for s in a.scenes or SCENES:
        print(dessiner(s, a.demi))


if __name__ == "__main__":
    main()
