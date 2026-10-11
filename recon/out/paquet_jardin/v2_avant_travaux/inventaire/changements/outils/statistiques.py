"""Chiffres de synthèse de l'inventaire : surfaces changées par effet et par couronne, part des vecteurs
(levé GAM, PCRS vecteur 2019, bordures de la description v2) dans les zones changées, et volume de photos
par période. Lecture seule. Sortie : donnees/statistiques.json."""
import collections
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import DONNEES, ICI, O, RACINE, ecrire_json, lire_json  # noqa: E402
from pyproj import Transformer  # noqa: E402

TR = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
RES = 0.5
X0, Y1, N = -150.0, 150.0, 600            # emprise locale -150..150 (300 m), cellules 0,5 m
CENTRE = (-1.57, -5.09)

GROUPES = {
    "geometrie_invalide": ["CHG-001", "CHG-002", "CHG-003", "CHG-004", "CHG-005", "CHG-006"],
    "marquages_invalides": ["CHG-008"],
    "texture_chaussee": ["CHG-009", "CHG-010", "CHG-011"],
    "apparence_batiment": ["CHG-012"],
    "paysager_incertain": ["CHG-018"],
    "paysager_2024_2025": ["CHG-021"],
    "risque_non_observe": ["CHG-019"],
}


def masque(feats):
    im = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(im)
    for f in feats:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else (g["coordinates"] if g["type"] == "MultiPolygon" else [])
        for p in polys:
            d.polygon([((x - O[0] - X0) / RES, (Y1 - (y - O[1])) / RES) for x, y in p[0]], fill=1)
    return np.asarray(im, bool)


def couronnes():
    j, i = np.mgrid[0:N, 0:N]
    x = X0 + (i + 0.5) * RES
    y = Y1 - (j + 0.5) * RES
    r = np.hypot(x - CENTRE[0], y - CENTRE[1])
    return {"r<=40": r <= 40, "40<r<=80": (r > 40) & (r <= 80), "80<r<=150": (r > 80) & (r <= 150), "emprise_300m": np.ones_like(r, bool)}


def longueur_dans(lignes, m):
    tot, dedans = 0.0, 0.0
    for l in lignes:
        for (xa, ya), (xb, yb) in zip(l[:-1], l[1:]):
            L = math.hypot(xb - xa, yb - ya)
            if L == 0:
                continue
            xm, ym = (xa + xb) / 2, (ya + yb) / 2
            i, j = int((xm - X0) / RES), int((Y1 - ym) / RES)
            if not (0 <= i < N and 0 <= j < N):
                continue
            tot += L
            dedans += L * m[j, i]
    return round(tot, 1), round(dedans, 1), round(dedans / tot, 3) if tot else None


def lignes_wgs(p):
    out = []
    for f in lire_json(p)["features"]:
        g = f["geometry"]
        if g is None:
            continue
        cs = [g["coordinates"]] if g["type"] == "LineString" else (g["coordinates"] if g["type"] == "MultiLineString" else [])
        for c in cs:
            out.append([(TR.transform(q[0], q[1])[0] - O[0], TR.transform(q[0], q[1])[1] - O[1]) for q in c])
    return out


def lignes_l93(p):
    out = []
    for f in lire_json(p)["features"]:
        g = f["geometry"]
        cs = [g["coordinates"]] if g["type"] == "LineString" else (g["coordinates"] if g["type"] == "MultiLineString" else [])
        for c in cs:
            out.append([(q[0] - O[0], q[1] - O[1]) for q in c])
    return out


def photos():
    """Photos du dépôt par période (Panoramax HD locales, Mapillary téléchargées) et poses calées."""
    V = RACINE / "data/raw"
    per = collections.Counter()
    for js in (V / "panoramax/paquet_jardin").glob("*_hd.json"):
        m = json.loads(js.read_text(encoding="utf-8"))
        per[("panoramax", m["datetime"][:10])] += 1
    inv = {im["id"]: im for im in lire_json(V / "mapillary/paquet_jardin/images.json")["images"]}
    for f in (V / "mapillary/paquet_jardin/img").glob("*.jpg"):
        im = inv.get(f.stem)
        if im:
            per[("mapillary", dt.datetime.utcfromtimestamp(im["captured_at"] / 1000).strftime("%Y-%m-%d"))] += 1
    cal = collections.Counter()
    for p in lire_json(RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json")["photos"]:
        if p["accepte"]:
            cal[("panoramax", p["date"])] += 1
    for im in lire_json(RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/poses/poses_mapillary.json")["images"]:
        if im["statut"] != "a_priori":
            cal[("mapillary", im["date"][:10])] += 1

    def fen(a, b):
        return {"photos": sum(v for (s, d), v in per.items() if a <= d <= b),
                "poses_calees": sum(v for (s, d), v in cal.items() if a <= d <= b),
                "seances": sorted({f"{d} {s}" for (s, d) in per if a <= d <= b})}
    return {"par_seance": {f"{d} {s}": {"photos": v, "poses_calees": cal.get((s, d), 0)} for (s, d), v in sorted(per.items(), key=lambda t: t[0][1])},
            "autour_mai_2022 (2022-01-01..2023-06-30)": fen("2022-01-01", "2023-06-30"),
            "fenetre_2022-05-10..2023-12-31": fen("2022-05-10", "2023-12-31"),
            "autour_printemps_2025 (2024-08-01..2025-06-22)": fen("2024-08-01", "2025-06-22"),
            "fenetre_2024-01-01..2025-06-22": fen("2024-01-01", "2025-06-22"),
            "pendant_travaux (2025-06-23..2026-01-30)": fen("2025-06-23", "2026-01-30"),
            "apres_travaux (> 2026-01-30)": fen("2026-01-31", "2100-01-01")}


def main():
    fc = lire_json(ICI / "changements_2022_2025.geojson")
    par_id = {f["properties"]["id"]: f for f in fc["features"]}
    C = couronnes()
    out = {"cellule_m": RES, "emprise_locale": [-150, -150, 150, 150], "centre_local": CENTRE, "surfaces_m2": {}, "parts_couronne": {}}
    M = {}
    for gname, ids in GROUPES.items():
        M[gname] = masque([par_id[i] for i in ids if i in par_id])
    M["tout_observe_hors_texture"] = M["geometrie_invalide"] | M["marquages_invalides"] | M["apparence_batiment"]
    M["tout_observe"] = M["tout_observe_hors_texture"] | M["texture_chaussee"] | M["paysager_incertain"]
    for gname, m in M.items():
        out["surfaces_m2"][gname] = {c: round(float((m & cm).sum() * RES * RES), 1) for c, cm in C.items()}
        out["parts_couronne"][gname] = {c: round(float((m & cm).sum() / cm.sum()), 4) for c, cm in C.items()}
    inv = M["geometrie_invalide"] | M["marquages_invalides"]
    V = RACINE / "data/sites/paquet_jardin/vector"
    out["vecteurs_dans_zones_geometrie_ou_marquage_invalides"] = {
        "gam_topo_bordure_lin": dict(zip(("longueur_m", "dans_zones_m", "part"), longueur_dans(lignes_wgs(V / "gam_topo_sol_bordure_lin.geojson"), inv))),
        "gam_topo_signalisation_horizontale_lin": dict(zip(("longueur_m", "dans_zones_m", "part"), longueur_dans(lignes_wgs(V / "gam_topo_sol_signalisation_horizontale_lin.geojson"), inv))),
        "pcrs_vecteur_2019_limite_voirie": dict(zip(("longueur_m", "dans_zones_m", "part"), longueur_dans(lignes_wgs(V / "gam_limite_voirie_pcrs.geojson"), inv))),
        "description_v2_base_bordures": dict(zip(("longueur_m", "dans_zones_m", "part"), longueur_dans(
            lignes_l93(RACINE / "recon/out/paquet_jardin/v2/description/base/bordures.geojson"), inv))),
    }
    out["photos"] = photos()
    ecrire_json(DONNEES / "statistiques.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "photos"}, ensure_ascii=False, indent=1))
    ph = out["photos"]
    for k, v in ph.items():
        if k != "par_seance":
            print(k, v["photos"], v["poses_calees"])
    for k, v in ph["par_seance"].items():
        print(k, v)


if __name__ == "__main__":
    main()
