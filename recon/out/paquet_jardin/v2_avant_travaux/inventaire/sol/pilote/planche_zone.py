"""Planche d'une zone : fonds (ortho 2022 5 cm, BD ORTHO 2024, Pléiades 2025, pente LiDAR 2021,
ombrage du sol nu 10 cm, plan projet 2025) et calques vectoriels (GAM bordure / limite de revêtement /
caniveau / chartières, PCRS 2019, bordures v2 2026, zones modifiées du relief v1).

Usage : python -I planche_zone.py x0 y0 x1 y1 res nom [fonds séparés par des virgules]
Sortie : ../planches/zone_<nom>_<fond>.jpg (un fichier par fond) et ../planches/zone_<nom>_mosaique.jpg
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw

import commun_sol as C

COUL = {
    "gam_bordure": (255, 0, 0), "pcrs": (0, 230, 255), "lrev": (255, 165, 0), "caniveau": (40, 90, 255),
    "v2": (255, 255, 0), "zones": (255, 0, 255), "chartiere": (255, 0, 255),
}


def ombrage(hm, X, Y, res):
    z = hm(X, Y)
    gy, gx = np.gradient(z, res)
    # soleil NO 45°
    nx, ny, nz = -gx, gy, np.ones_like(z)
    n = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    l = np.array([-1, 1, 1.4]) / np.linalg.norm([-1, 1, 1.4])
    s = np.clip((nx * l[0] + ny * l[1] + nz * l[2]) / n, 0, 1)
    s = (s - s.min()) / max(1e-9, s.max() - s.min())
    g = (s * 255).astype(np.uint8)
    return np.dstack([g, g, g])


def calques(bbox, marge=3.0):
    x0, y0, x1, y1 = bbox

    def dedans(P):
        return ((P[:, 0] > x0 - marge) & (P[:, 0] < x1 + marge) & (P[:, 1] > y0 - marge) & (P[:, 1] < y1 + marge)).any()
    L = {}
    L["lrev"] = [P for _, _, P, _ in C.charger_lignes(C.SITE / "vector/gam_topo_sol_limite_revetement_lin.geojson", wgs=True) if dedans(P)]
    L["caniveau"] = [P for _, _, P, _ in C.charger_lignes(C.SITE / "vector/gam_topo_sol_caniveau_lin.geojson", wgs=True) if dedans(P)]
    L["pcrs"] = [P for _, _, P, _ in C.charger_lignes(C.SITE / "vector/gam_limite_voirie_pcrs.geojson", wgs=True) if dedans(P)]
    L["gam_bordure"] = [P for _, _, P, _ in C.charger_lignes(C.SITE / "vector/gam_topo_sol_bordure_lin.geojson", wgs=True) if dedans(P)]
    L["v2"] = [P for _, _, P, _ in C.charger_lignes(C.V2 / "description/base/bordures.geojson") if dedans(P)]
    L["zones"] = [P for _, p, P, _ in C.charger_lignes(C.PAQUET / "relief/relief_zones_2026.geojson")
                  if dedans(P) and p.get("zone") != "chaussee_2026"]
    ch = []
    for f in C.lire_json(C.SITE / "vector/gam_topo_sol_bordure_pct.geojson")["features"]:
        b = f["properties"].get("bloc") or ""
        a = np.atleast_2d(np.asarray(f["geometry"]["coordinates"], float))[:, :2]
        P = C.wgs_vers_l93(a) - C.O
        if dedans(P):
            ch.append((P[0], b, f["properties"].get("rotation")))
    L["chartiere"] = ch
    return L


def dessiner(im, L, bbox, res, quoi):
    dr = ImageDraw.Draw(im)
    lw = 2 if res <= 0.05 else 1
    for k in ("zones", "lrev", "caniveau", "pcrs", "v2", "gam_bordure"):
        if k not in quoi:
            continue
        for P in L[k]:
            w = lw + (1 if k == "v2" else 0)
            if k == "v2":
                C.tracer(dr, P, bbox, res, COUL[k], w)
            else:
                C.tracer(dr, P, bbox, res, COUL[k], lw)
    if "chartiere" in quoi:
        for p, b, rot in L["chartiere"]:
            (u, v), = C.vers_px(p[None], bbox, res)
            dr.ellipse([u - 5, v - 5, u + 5, v + 5], outline=COUL["chartiere"], width=2)


def main():
    bbox = tuple(float(v) for v in sys.argv[1:5])
    res, nom = float(sys.argv[5]), sys.argv[6]
    fonds = sys.argv[7].split(",") if len(sys.argv) > 7 else ["ortho2022", "ortho2024", "pleiades2025", "pente2021", "ombrage", "plan2025"]
    R = C.sources_raster()
    X, Y = C.grille(bbox, res)
    L = calques(bbox)
    imgs = []
    for fond in fonds:
        if fond == "ombrage":
            a = ombrage(C.Heightmap(), X, Y, res)
            quoi = ("gam_bordure", "zones", "chartiere")
            leg = "ombrage sol nu heightmap v1 10 cm (=LiDAR 2021 hors zones magenta) | rouge GAM | magenta zones modifiees 2025"
        else:
            a = R[fond].echantillonner(X, Y)
            if fond == "ortho2022":
                quoi = ("lrev", "caniveau", "pcrs", "gam_bordure", "chartiere")
                leg = "ortho 2022 5 cm | rouge GAM bordure | cyan PCRS 2019 | orange GAM lim. revet. | bleu caniveau | o chartiere"
            elif fond == "plan2025":
                quoi = ("gam_bordure", "v2")
                leg = "plan projet 2025 | rouge GAM bordure | jaune bordures v2 2026"
            elif fond == "pente2021":
                quoi = ("gam_bordure", "pcrs")
                leg = "pente LiDAR 2021 15 cm | rouge GAM bordure | cyan PCRS 2019"
            else:
                quoi = ("gam_bordure", "v2")
                leg = f"{fond} | rouge GAM bordure | jaune bordures v2 2026"
        im = Image.fromarray(a.copy())
        dessiner(im, L, bbox, res, quoi)
        C.cartouche(im, f"{nom} : {leg}", 13)
        C.echelle(im, res, 2 if (bbox[2] - bbox[0]) < 40 else 5)
        im.save(C.SORTIE / "planches" / f"zone_{nom}_{fond}.jpg", quality=90)
        imgs.append(im)
    print("écrit", nom, len(imgs), imgs[0].size)


if __name__ == "__main__":
    main()
