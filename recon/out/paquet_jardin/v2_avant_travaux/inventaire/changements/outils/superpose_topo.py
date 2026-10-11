"""Superposition du levé topo GAM (gam_topo_sol = etat_2026) et du PCRS vecteur 2019 sur les orthos 2022 / 2024."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa
from pyproj import Transformer

TR = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
V = RACINE / "data/sites/paquet_jardin/vector"


def lignes(f, wgs=True):
    out = []
    for ft in lire_json(f)["features"]:
        g = ft["geometry"]
        if g is None:
            continue
        cs = [g["coordinates"]] if g["type"] == "LineString" else (g["coordinates"] if g["type"] == "MultiLineString" else [])
        for c in cs:
            pts = [TR.transform(p[0], p[1]) if wgs else (p[0], p[1]) for p in c]
            out.append([(x - O[0], y - O[1]) for x, y in pts])
    return out


bord = lignes(V / "gam_topo_sol_bordure_lin.geojson")
sig = lignes(V / "gam_topo_sol_signalisation_horizontale_lin.geojson")
pcrs = lignes(V / "gam_limite_voirie_pcrs.geojson")


def planche(nom, x0, y0, x1, y1, px=700):
    b = boite_locale(x0, y0, x1, y1)
    pans = []
    for k in ("2022", "2024"):
        v = Vue(k, b, px, titre=LIB[k] + " + topo GAM (blanc bordures, cyan marquages) + PCRS vect. 2019 (orange)")
        for l in pcrs:
            v.poly(l, (255, 150, 0, 230), 1, ferme=False)
        for l in bord:
            v.poly(l, (255, 255, 255, 230), 1, ferme=False)
        for l in sig:
            v.poly(l, (0, 255, 255, 230), 1, ferme=False)
        pans.append(v.grille(10 if x1 - x0 > 80 else 5, 50 if x1 - x0 > 80 else 10).im)
    s = PLANCHES / "topo_gam" / f"{nom}.jpg"
    s.parent.mkdir(parents=True, exist_ok=True)
    assembler(pans, f"{nom} : levé topo GAM Meylan_Topo.dwg (= etat_2026) sur PCRS 2022 et IGN 2024").save(s, quality=88)
    print(s)


planche("site", -150, -150, 150, 150, 900)
planche("coeur", -30, -30, 30, 30, 800)
planche("est", 20, -100, 120, 0, 800)
planche("verdun_ne", 0, 0, 100, 100, 800)
