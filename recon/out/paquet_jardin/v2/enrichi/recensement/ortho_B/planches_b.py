"""planches_b.py : planches de vignettes (brut 2x, repère au point de la description) pour vérifier
rapidement chaque objet ponctuel d'une dalle (mobilier, arbres, corrections, candidats de peinture).

python planches_b.py <tuile> [--couche mobilier|arbres|peinture|marquages] [--taille 100] [--echelle 2]
-> planches/<tuile>_<couche>_<k>.jpg (20 vignettes par planche, légende = id et pixel de dalle)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from overlay import Dalle, charger, police  # noqa: E402


def points(tuile, couche):
    D = Dalle(tuile)
    if couche.startswith("pts:"):
        out = []
        for k in couche[4:].split(";"):
            u, v, *n = k.split(",")
            out.append((n[0] if n else f"{u},{v}", float(u), float(v), None))
        return out
    if couche == "peinture":
        r = json.load(open(ICI / "controles" / f"{tuile}.json", encoding="utf-8"))
        return [(f"p{i}:{c['aire_px']}", c["u"], c["v"], None) for i, c in enumerate(r["peinture_non_expliquee"])]
    out = []
    for e in charger():
        if e["couche"] != couche:
            continue
        for an in e["anneaux"][:1]:
            if couche == "marquages":
                c = np.vstack(e["anneaux"]).mean(0)
            elif len(an) == 1:
                c = an[0]
            elif couche == "corrections":
                c = an[-1]
            else:
                continue
            u, v = D.l93_vers_px(c)
            if 0 <= u < 1000 and 0 <= v < 1000:
                extra = None
                if couche == "corrections":
                    extra = D.l93_vers_px(an[0])
                out.append((e["id"], float(u), float(v), extra))
    return out


def planche(tuile, couche, taille=100, echelle=2.0, par=20):
    D = Dalle(tuile)
    P = points(tuile, couche)
    s = int(taille * echelle)
    out = []
    for k in range(0, len(P), par):
        lot = P[k:k + par]
        ncol = 5
        nl = (len(lot) + ncol - 1) // ncol
        can = Image.new("RGB", (ncol * (s + 4), nl * (s + 20)), (25, 25, 25))
        dr = ImageDraw.Draw(can)
        for i, (nom, u, v, extra) in enumerate(lot):
            u0, v0 = int(round(u - taille / 2)), int(round(v - taille / 2))
            im = D.img.crop((u0, v0, u0 + taille, v0 + taille)).resize((s, s), Image.BICUBIC)
            x, y = (i % ncol) * (s + 4), (i // ncol) * (s + 20)
            can.paste(im, (x, y + 18))
            cx, cy = x + (u - u0) * echelle, y + 18 + (v - v0) * echelle
            dr.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], outline=(0, 255, 255), width=1)
            dr.line([cx - 3, cy, cx + 3, cy], fill=(0, 255, 255))
            if extra is not None:
                ex, ey = x + (extra[0] - u0) * echelle, y + 18 + (extra[1] - v0) * echelle
                dr.line([ex, ey, cx, cy], fill=(255, 60, 60), width=1)
                dr.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], outline=(255, 60, 60))
            dr.text((x + 2, y + 2), f"{nom[:22]} {u:.0f},{v:.0f}", font=police(11), fill=(255, 255, 0))
        nomc = "points" if couche.startswith("pts:") else couche
        f = ICI / "planches" / f"{tuile}_{nomc}_{k // par}.jpg"
        f.parent.mkdir(exist_ok=True)
        can.save(f, quality=88)
        out.append(f)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tuiles", nargs="+")
    ap.add_argument("--couche", default="mobilier")
    ap.add_argument("--taille", type=int, default=100)
    ap.add_argument("--echelle", type=float, default=2.0)
    a = ap.parse_args()
    for t in a.tuiles:
        for f in planche(t, a.couche, a.taille, a.echelle):
            print(f)
