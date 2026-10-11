"""Planches d'aperçu : levé GAM SOL_BORDURE (= etat_2026) et PCRS 2019 sur l'ortho 2022, l'ortho 2024,
la pente LiDAR 2021 et le plan projet 2025, pour dater le levé et choisir les zones pilotes.

Usage : python -I planche_apercu.py [x0 y0 x1 y1 res nom]
Sorties : ../planches/apercu_<nom>_<fond>.jpg
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C


def main():
    if len(sys.argv) >= 7:
        bbox = tuple(float(v) for v in sys.argv[1:5])
        res, nom = float(sys.argv[5]), sys.argv[6]
    else:
        bbox, res, nom = (-150, -150, 150, 150), 0.3, "site"
    fonds = sys.argv[7].split(",") if len(sys.argv) >= 8 else ["ortho2022", "ortho2024", "pente2021", "plan2025"]
    R = C.sources_raster()
    X, Y = C.grille(bbox, res)
    gam = C.charger_lignes(C.SITE / "vector/gam_topo_sol_bordure_lin.geojson", wgs=True)
    pcrs = C.charger_lignes(C.SITE / "vector/gam_limite_voirie_pcrs.geojson", wgs=True)
    lrev = C.charger_lignes(C.SITE / "vector/gam_topo_sol_limite_revetement_lin.geojson", wgs=True)
    v2 = C.charger_lignes(C.V2 / "description/base/bordures.geojson")
    v2 = [(i, p, P - 0 if False else P, z) for i, p, P, z in v2]
    larg = max(1, int(round(0.06 / res))) if res < 0.06 else 1
    for fond in fonds:
        a = R[fond].echantillonner(X, Y)
        im = Image.fromarray(a)
        dr = ImageDraw.Draw(im)
        for _, _, P, _ in lrev:
            C.tracer(dr, P, bbox, res, (255, 160, 0), max(1, larg))
        for _, _, P, _ in pcrs:
            C.tracer(dr, P, bbox, res, (0, 220, 255), max(1, larg))
        for _, _, P, _ in gam:
            C.tracer(dr, P, bbox, res, (255, 0, 0), max(1, larg))
        C.cartouche(im, f"{fond} | rouge GAM SOL_BORDURE | cyan PCRS 2019 limite voirie | orange GAM limite revetement | {nom}")
        C.echelle(im, res, 10 if res >= 0.1 else 2)
        im.save(C.SORTIE / "planches" / f"apercu_{nom}_{fond}.jpg", quality=90)
        print("écrit", f"apercu_{nom}_{fond}.jpg", im.size)


if __name__ == "__main__":
    main()
