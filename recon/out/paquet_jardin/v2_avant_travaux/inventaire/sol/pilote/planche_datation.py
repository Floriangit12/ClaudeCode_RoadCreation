"""Planche de la datation des bordures (sortie de dater_gam.py) sur l'ortho 2022 et la BD ORTHO 2024.

Usage : python -I planche_datation.py x0 y0 x1 y1 res nom [source gam|pcrs2019|toutes]
Sortie : ../planches/datation_<nom>_<fond>.jpg
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C

COUL = {"relief_2021": (0, 255, 0), "arasee_visible": (0, 220, 255), "apparue_2022_2024": (255, 150, 0),
        "absente_avant": (255, 0, 0), "masquee": (170, 170, 170), "relief_seul": (255, 255, 0), "terrain_remanie_2021": (255, 0, 255)}


def main():
    bbox = tuple(float(v) for v in sys.argv[1:5])
    res, nom = float(sys.argv[5]), sys.argv[6]
    src = sys.argv[7] if len(sys.argv) > 7 else "gam"
    R = C.sources_raster()
    X, Y = C.grille(bbox, res)
    F = C.lire_json(C.SORTIE / "datation/gam_bordures_datation.geojson")["features"]
    for fond in ("ortho2022", "ortho2024"):
        im = Image.fromarray(R[fond].echantillonner(X, Y))
        dr = ImageDraw.Draw(im)
        for f in F:
            if (src != "toutes" and f["properties"]["source"] != src) or (src == "toutes" and f["properties"]["source"] not in ("gam", "pcrs2019")):
                continue
            P = np.asarray(f["geometry"]["coordinates"])[:, :2] - C.O
            C.tracer(dr, P, bbox, res, COUL[f["properties"]["classe"]], 3 if res < 0.1 else 2)
        C.cartouche(im, f"{nom} {fond} | {src} | vert relief 2021 | cyan arasee visible 2022 | orange apparue 2022-2024 | rouge absente avant 08/2024 | gris masquee | magenta terrain remanie | jaune relief sans arete", 12)
        C.echelle(im, res, 10 if res >= 0.1 else 2)
        im.save(C.SORTIE / "planches" / f"datation_{nom}_{fond}.jpg", quality=90)
    print("ok")


if __name__ == "__main__":
    main()
