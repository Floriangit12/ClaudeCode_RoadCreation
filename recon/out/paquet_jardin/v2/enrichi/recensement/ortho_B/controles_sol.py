"""controles_sol.py : contrôle radiométrique des surfaces de la description (materiau_id) sur l'ortho 2022.

Pour chaque surface (hors emprises de bordure) dont le centroïde est dans la dalle :
part verte (ExG > 15) hors couronnes d'arbres décrites, part sous couronnes, teinte moyenne.
Drapeaux : végétal décrit mais minéral sur l'image, minéral décrit mais vert, etc. Indices seulement :
chaque drapeau est relu sur les vues avant d'être noté (zones de travaux 2025 et secteurs
construits 2023-2024 : l'image ne prouve rien).

python controles_sol.py --toutes | --tuiles <t...>  -> controles/<tuile>_sol.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from overlay import PAS, TUILES_B, Dalle, charger  # noqa: E402

VEGETAL = {"gazon_tondu", "herbe_haute", "noue_plantee", "massif"}
MINERAL = {"enrobe_trottoir", "enrobe_bbsg_ancien", "enrobe_bbsg_neuf_2025", "enrobe_piste_cyclable", "beton_balaye",
           "stabilise_beige", "paves_beton"}


def controler(t):
    D = Dalle(t)
    a = np.asarray(D.img, np.float32)
    exg = 2 * a[..., 1] - a[..., 0] - a[..., 2]
    vert = exg > 15
    couronnes = Image.new("L", (1000, 1000), 0)
    dc = ImageDraw.Draw(couronnes)
    x0, y0, x1, y1 = D.emprise()
    E = charger()
    for e in E:
        if e["couche"] == "arbres" and e.get("rayon_m"):
            u, v = D.l93_vers_px(e["anneaux"][0][0])
            r = e["rayon_m"] / PAS
            dc.ellipse([u - r, v - r, u + r, v + r], fill=255)
    cour = np.asarray(couronnes) > 0
    out = []
    for e in E:
        if e["couche"] not in ("surfaces", "ilots"):
            continue
        bx = e["bbox"]
        if bx[2] < x0 or bx[0] > x1 or bx[3] < y0 or bx[1] > y1:
            continue
        m = Image.new("L", (1000, 1000), 0)
        dm = ImageDraw.Draw(m)
        for k, an in enumerate(e["anneaux"]):
            dm.polygon([tuple(p) for p in D.l93_vers_px(an)], fill=255 if k == 0 else 0)
        mk = np.asarray(m) > 0
        n = int(mk.sum())
        if n < 400:
            continue
        p = e["props"]
        mat = (p.get("revetement") or p.get("remplissage") or {}).get("materiau_id")
        libre = mk & ~cour
        nl = int(libre.sum())
        pv = float(vert[libre].mean()) if nl > 50 else None
        col = a[mk].mean(0)
        drap = None
        if pv is not None and nl > 0.3 * n:
            if mat in VEGETAL and pv < 0.25:
                drap = "vegetal_decrit_mineral_vu"
            elif mat in MINERAL and pv > 0.5:
                drap = "mineral_decrit_vert_vu"
            elif mat in ("brf_bois_concasse", "terre_nue") and pv > 0.6:
                drap = "brf_ou_terre_decrit_vert_vu"
        uv = D.l93_vers_px(np.vstack(e["anneaux"][:1]).mean(0))
        out.append(dict(id=e["id"], couche=e["couche"], classe=p.get("classe") or p.get("type"), materiau=mat,
                        n_px_dalle=n, part_sous_couronnes=round(1 - nl / n, 2),
                        part_verte=None if pv is None else round(pv, 2), rgb=[round(float(c)) for c in col],
                        drapeau=drap, uv=[round(float(uv[0]), 1), round(float(uv[1]), 1)]))
    with open(ICI / "controles" / f"{t}_sol.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuiles", nargs="*", default=[])
    ap.add_argument("--toutes", action="store_true")
    a = ap.parse_args()
    for t in (TUILES_B if a.toutes else a.tuiles):
        r = controler(t)
        print(t, len(r), "surfaces", sum(1 for x in r if x["drapeau"]), "drapeaux")
