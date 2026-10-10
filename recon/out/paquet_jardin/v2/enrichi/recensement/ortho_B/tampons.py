"""tampons.py : candidats tampons / regards / grilles sur les surfaces revêtues d'une dalle ortho 2022.

Taches sombres compactes (0,15 à 1,3 m²) sur chaussée, trottoir, parking, piste, accès, quai
(surfaces_2026 v1), contraste local > 15 niveaux sous la moyenne 2 m. Les candidats sont ensuite
revus sur planche (planches_b.py --couche pts:...) ; aucun n'est noté sans revue visuelle.

python tampons.py <tuile...>  -> controles/<tuile>_tampons.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from overlay import Dalle, charger  # noqa: E402
from controles import flou, masque, composantes  # noqa: E402

REVETU = {"chaussee", "trottoir", "parking", "piste_cyclable", "acces_riverain", "quai_bus"}


def candidats(t):
    D = Dalle(t)
    a = np.asarray(D.img, np.float32)
    L = a @ np.array([0.299, 0.587, 0.114], np.float32)
    fond = flou(L, 20)
    sat = a.max(-1) - a.min(-1)
    rev = np.zeros((1000, 1000), bool)
    for e in charger():
        if e["couche"] == "surfaces_v1" and e["props"].get("classe") in REVETU:
            x0, y0, x1, y1 = D.emprise()
            bx = e["bbox"]
            if bx[2] < x0 or bx[0] > x1 or bx[3] < y0 or bx[1] > y1:
                continue
            rev |= masque(D, e["anneaux"][:1], True)
    sombre = (L < fond - 15) & (L > 25) & (sat < 60) & rev
    out = []
    for c in composantes(sombre, 50):
        u0, v0, u1, v1 = c["bbox"]
        w, h = u1 - u0 + 1, v1 - v0 + 1
        if c["aire_px"] > 600 or max(w, h) > 32 or max(w, h) / max(1, min(w, h)) > 1.7:
            continue
        if c["aire_px"] / (w * h) < 0.45:
            continue
        out.append(c)
    with open(ICI / "controles" / f"{t}_tampons.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=0)
    return out


if __name__ == "__main__":
    for t in sys.argv[1:]:
        c = candidats(t)
        print(t, len(c), ";".join(f"{x['u']:.0f},{x['v']:.0f},c{i}" for i, x in enumerate(c)))
