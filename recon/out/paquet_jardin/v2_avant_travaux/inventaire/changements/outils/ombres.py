"""Ombres portées des bâtiments (emprise BD TOPO) sur PCRS 2022, IGN 2024 et Pléiades 2025, pour dater
la prise Pléiades 2025 (azimut et élévation du soleil). Planches avec emprises au sol en magenta."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa
from pyproj import Transformer

TR = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
BAT = []
for f in lire_json(RACINE / "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson")["features"]:
    g = f["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for p in polys:
        BAT.append((f["properties"], [(TR.transform(c[0], c[1])[0] - O[0], TR.transform(c[0], c[1])[1] - O[1]) for c in p[0]]))


def planche(nom, x0, y0, x1, y1, px=650, pas=5.0):
    b = boite_locale(x0, y0, x1, y1)
    pans = []
    for k in ("2022", "2024", "2025"):
        v = Vue(k, b, px)
        for p, pts in BAT:
            v.poly(pts, (255, 0, 255, 220), 1)
        pans.append(v.grille(pas, 10).im)
    s = PLANCHES / "ombres" / f"{nom}.jpg"
    s.parent.mkdir(parents=True, exist_ok=True)
    assembler(pans, f"{nom} : emprises BD TOPO (magenta) ; ombres 2022 | 2024 | 2025").save(s, quality=90)
    print(s)


if __name__ == "__main__":
    a = sys.argv[1:]
    planche(a[0], *[float(v) for v in a[1:5]])
    for p, pts in BAT:
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        if max(xs) > float(a[1]) and min(xs) < float(a[3]) and max(ys) > float(a[2]) and min(ys) < float(a[4]):
            print(p.get("cleabs"), p.get("hauteur"), p.get("nombre_d_etages"), [(round(x, 1), round(y, 1)) for x, y in pts])
