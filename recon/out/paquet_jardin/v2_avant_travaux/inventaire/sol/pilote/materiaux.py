"""Signatures des matériaux de sol avant travaux sur l'ortho PCRS 2022 (5 cm) et l'intensité LiDAR 2021 (15 cm),
sur des placettes étiquetées à la main dans les zones pilotes (étiquettes confirmées sur la photo Panoramax du
2025-05-18 pour les galets des îlots du cœur). But : montrer quelles variables séparent enrobé, béton de bordure,
galets, terre / paillage, herbe sèche, gazon, et proposer des seuils.

Variables : luminance médiane L, écart-type de L sur la placette, grain (écart-type de L − moyenne 3×3 : texture
à l'échelle de 5-15 cm), ExG = 2G − R − B, R − B, intensité LiDAR sol (JPEG 8 bits, relative).
Sorties : ../materiaux_signatures.json, ../planches/materiaux_placettes_<zone>.jpg
Usage : python -I materiaux.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C

# (étiquette, x, y, rayon) en repère local ; placettes posées sur l'ortho 2022 (planches de contrôle)
PLACETTES = [
    ("enrobe_chaussee", -0.4, -11.4, 0.7), ("enrobe_chaussee", 12.8, -22.8, 0.5), ("enrobe_chaussee", 5.9, -24.6, 0.7),
    ("galets_ilot", 9.3, -22.3, 0.5), ("galets_ilot", 10.4, -25.0, 0.35), ("galets_ilot", 4.4, -13.6, 0.45),
    ("terre_paillage_massif", 20.5, 4.0, 0.8), ("terre_paillage_massif", 22.0, 5.8, 0.6),
    ("herbe_seche_ilot", 13.6, -3.0, 0.6), ("herbe_seche_ilot", 13.0, -6.0, 0.4),
    ("trottoir_enrobe", 19.0, 1.2, 0.4), ("trottoir_enrobe", 22.4, 0.6, 0.35),
    ("gazon", -18.0, 3.0, 0.8), ("gazon", -20.4, -0.9, 0.6),
]
ZONES = {"A": (-4.0, -34.0, 20.0, -6.0), "B": (8.0, -8.0, 28.0, 12.0), "O": (-36.0, -16.0, -12.0, 24.0)}


def stats(R, x, y, r):
    res = 0.05
    bb = (x - r - 0.1, y - r - 0.1, x + r + 0.1, y + r + 0.1)
    X, Y = C.grille(bb, res)
    rgb = R["ortho2022"].echantillonner(X, Y).astype(float)
    m = np.hypot(X - C.O[0] - x, Y - C.O[1] - y) <= r
    L = C.luminance(rgb)
    Lm = (L + np.roll(L, 1, 0) + np.roll(L, -1, 0) + np.roll(L, 1, 1) + np.roll(L, -1, 1)
          + np.roll(np.roll(L, 1, 0), 1, 1) + np.roll(np.roll(L, 1, 0), -1, 1) + np.roll(np.roll(L, -1, 0), 1, 1) + np.roll(np.roll(L, -1, 0), -1, 1)) / 9
    hp = (L - Lm)[m]
    it = C.luminance(R["intensite2021"].echantillonner(X, Y))[m]
    a = rgb[m]
    return {"L_med": round(float(np.median(L[m])), 1), "L_ecart_type": round(float(L[m].std()), 1),
            "grain": round(float(hp.std()), 1), "ExG_med": round(float(np.median(2 * a[:, 1] - a[:, 0] - a[:, 2])), 1),
            "R_moins_B_med": round(float(np.median(a[:, 0] - a[:, 2])), 1), "intensite21_med": round(float(np.median(it)), 1),
            "n_px": int(m.sum())}


def main():
    R = C.sources_raster()
    res = {"placettes": []}
    par = {}
    for lab, x, y, r in PLACETTES:
        s = stats(R, x, y, r)
        res["placettes"].append({"etiquette": lab, "centre_local": [x, y], "rayon_m": r} | s)
        par.setdefault(lab, []).append(s)
    res["par_etiquette"] = {k: {v: round(float(np.mean([s[v] for s in L])), 1) for v in ("L_med", "L_ecart_type", "grain", "ExG_med", "R_moins_B_med", "intensite21_med")}
                            for k, L in par.items()}
    C.ecrire_json(C.SORTIE / "materiaux_signatures.json", res)
    for nom, bb in ZONES.items():
        X, Y = C.grille(bb, 0.03)
        im = Image.fromarray(R["ortho2022"].echantillonner(X, Y))
        dr = ImageDraw.Draw(im)
        for lab, x, y, r in PLACETTES:
            if bb[0] < x < bb[2] and bb[1] < y < bb[3]:
                (u, v), = C.vers_px(np.array([[x, y]]), bb, 0.03)
                rp = r / 0.03
                dr.ellipse([u - rp, v - rp, u + rp, v + rp], outline=(255, 255, 0), width=3)
                dr.text((u + rp + 3, v - 8), lab, fill=(255, 255, 0), font=C.police(14))
        C.cartouche(im, f"placettes materiaux zone {nom} (ortho 2022)", 13)
        C.echelle(im, 0.03, 2)
        im.save(C.SORTIE / "planches" / f"materiaux_placettes_{nom}.jpg", quality=88)
    print(C.json.dumps(res["par_etiquette"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
