"""Catalogue des photos Panoramax (métadonnées seulement) le long des axes du lot B (autoroute A41, N87,
grands axes de Meylan), avec la route OSM la plus proche de chaque photo.

Aucune image n'est téléchargée ici : seulement l'identifiant, la position, la date, le cap, l'auteur, la
licence et l'URL HD. Sortie (non versionnée) : recon/out/generateur/meylan/auto_travail_lotB/panoramax/.

    python -I recon/generateur/meylan/auto_outils/catalogue_panoramax.py --bbox 5.752 45.196 5.822 45.212 --nom a41

API publique : https://api.panoramax.xyz/api/search (STAC). Le bbox est découpé en cases pour rester sous la
limite de résultats de l'API.
"""
import argparse
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
TRAVAIL = RACINE / "recon" / "out" / "generateur" / "meylan" / "auto_travail_lotB"
UA = "ClaudeCode_RoadCreation/1.0 (recherche voirie Meylan)"
API = "https://api.panoramax.xyz/api/search"


def get_json(url):
    for essai in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # réseau : on réessaie
            if essai == 3:
                raise
            time.sleep(3 * (essai + 1))


def chercher(bbox, limite=1000):
    q = urllib.parse.urlencode({"bbox": ",".join("%.6f" % v for v in bbox), "limit": limite})
    d = get_json(API + "?" + q)
    return d.get("features", [])


def resume(f):
    p = f["properties"]
    io = p.get("pers:interior_orientation") or {}
    lon, lat = f["geometry"]["coordinates"]
    return {
        "id": f["id"],
        "collection": f.get("collection"),
        "lon": lon, "lat": lat,
        "datetime": p.get("datetime"),
        "azimut": p.get("view:azimuth"),
        "auteur": p.get("geovisio:producer"),
        "licence": p.get("license"),
        "camera": "%s %s" % (io.get("camera_manufacturer", ""), io.get("camera_model", "")),
        "fov": io.get("field_of_view"),
        "capteur": io.get("sensor_array_dimensions"),
        "hd": (f.get("assets", {}).get("hd") or {}).get("href"),
        "precision_m": p.get("quality:horizontal_accuracy"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, required=True, help="lon0 lat0 lon1 lat1")
    ap.add_argument("--nom", required=True)
    ap.add_argument("--pas", type=float, default=0.004, help="taille des cases en degrés")
    a = ap.parse_args()
    lon0, lat0, lon1, lat1 = a.bbox
    vus = {}
    nx = max(1, math.ceil((lon1 - lon0) / a.pas))
    ny = max(1, math.ceil((lat1 - lat0) / a.pas))
    for i in range(nx):
        for j in range(ny):
            b = (lon0 + i * a.pas, lat0 + j * a.pas, min(lon1, lon0 + (i + 1) * a.pas), min(lat1, lat0 + (j + 1) * a.pas))
            fs = chercher(b)
            if len(fs) >= 1000:
                print("case saturée", b)
            for f in fs:
                vus[f["id"]] = resume(f)
    out = TRAVAIL / "panoramax"
    out.mkdir(parents=True, exist_ok=True)
    liste = sorted(vus.values(), key=lambda r: (r["datetime"] or "", r["id"]))
    (out / ("catalogue_%s.json" % a.nom)).write_text(json.dumps(liste, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(liste), "photos ->", out / ("catalogue_%s.json" % a.nom))


if __name__ == "__main__":
    main()
