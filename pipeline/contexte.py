"""Données de contexte (mobilité, sécurité, foncier) pour Meylan, avec les URL
testées le 2026-10-06 :

- accidents corporels BAAC 2015-2024 (ONISR, data.gouv.fr) filtrés sur Meylan ;
- réseau TC M réso (GTFS SEM, tracés des lignes, Chronovélo) — API Mobilités M ;
- aménagements cyclables Métropole + schéma directeur SMMAG ;
- comptages routiers/vélos/piétons Métropole ; trafic D38 (Département) ;
- arrêtés de travaux de voirie (Métropole) : dates de réfection de chaussée ;
- cadastre Etalab (parcelles, bâtiments...), Base Adresse Nationale, écoles.

Sortie : data/context/ (fichiers filtrés sur Meylan, légers, versionnés).
Usage : python3 pipeline/contexte.py
"""
from __future__ import annotations

import csv
import io
import json
import math
import re

from shapely.geometry import shape

from common import CONFIG, DATA, RAW, download, http_get, site, to_l93

OUT = DATA / "context"
CACHE = RAW / "context"
GAM = "https://data.metropolegrenoble.fr/sites/default/files/dataset"
FILES = {
    "pistes_cyclables_metropole.json": f"{GAM}/2023/08/08/06510ff6-e703-434b-967e-7095d454d453/pistes_cyclables_metropole.json",
    "sdic_smmag.geojson": f"{GAM}/2024/07/25/a364b46f-a73d-483d-8177-da82fb8ce3a7/sdic_smmag_16_11_2023.geojson",
    "arbres_metropole.geojson": f"{GAM}/2023/02/22/cf47c651-fce0-4773-8883-68957560514b/arbre.geojson",
    "sens_uniques_metropole.geojson": f"{GAM}/2023/11/17/38d61415-834a-4126-89dc-ae42e6fa4e87/open_data1gam_voiries_sens_uniques_j5c99h.geojson.geojson",
    "comptages_directionnels.csv": f"{GAM}/2023/08/01/0ecc47f5-b960-4ee6-93ba-6159cd22f5d5/comptages_directionnels.csv",
    "comptages_velos_permanents.csv": f"{GAM}/2023/08/01/0ecc47f5-b960-4ee6-93ba-6159cd22f5d5/comptages_velos_permanents.csv",
    "comptages_vlpl_permanents_tmja2022.csv": f"{GAM}/2023/08/01/0ecc47f5-b960-4ee6-93ba-6159cd22f5d5/comptages_vlpl_permanents_tmja2022.csv",
    "radars_pedagogiques.csv": f"{GAM}/2023/08/01/0ecc47f5-b960-4ee6-93ba-6159cd22f5d5/radars_pedagogiques.csv",
    "arretes_travaux_metropole.csv": f"{GAM}/11d/76884-08e9-4d54-a049-a2aa5d308463/arretes_de_travaux_metropole_epsg4326.csv",
    "gtfs_SEM.zip": "https://data.mobilites-m.fr/api/gtfs/SEM",
    "lignes_SEM.geojson": "https://data.mobilites-m.fr/api/lines/json?types=ligne&reseaux=SEM",
    "chronovelo.geojson": "https://data.mobilites-m.fr/api/lines/json?types=chronovelo",
    "trafic_d38.geojson": "https://opendata.isere.fr/api/explore/v2.1/catalog/datasets/d38_reseau_routier_trafic/exports/geojson",
    "ecoles_meylan.json": "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-annuaire-education/records?where=code_commune%3D%2238229%22&limit=100",
    "ban_meylan.csv": "https://plateforme.adresse.data.gouv.fr/ban/communes/38229/download/csv-bal/adresses",
}
CADASTRE = ("https://cadastre.s3.rbx.io.cloud.ovh.net/etalab-cadastre/2026-09-01/geojson/"
            "communes/38/38229/cadastre-38229-{}.json.gz")
BAAC_DATASET = "https://www.data.gouv.fr/api/1/datasets/53698f4ca3a729239d2036df/"


def in_meylan_bbox(lon, lat, margin=0.01):
    x0, y0, x1, y1 = CONFIG["commune"]["bbox_wgs84"]
    return x0 - margin <= lon <= x1 + margin and y0 - margin <= lat <= y1 + margin


def clip_geojson(src, dst, margin=0.01):
    fc = json.loads(src.read_text())
    keep = []
    for f in fc.get("features", []):
        if not f.get("geometry"):
            continue
        g = shape(f["geometry"])
        if g.is_empty:
            continue
        c = g.representative_point()
        if in_meylan_bbox(c.x, c.y, margin):
            keep.append(f)
    dst.write_text(json.dumps({"type": "FeatureCollection", "features": keep}, ensure_ascii=False))
    return len(keep)


def clip_csv_latlon(src, dst):
    txt = src.read_bytes().decode("utf-8", "replace")
    sep = max([";", ","], key=txt.split("\n", 1)[0].count)
    rows = list(csv.reader(io.StringIO(txt), delimiter=sep))
    head, keep = rows[0], [rows[0]]
    for r in rows[1:]:
        nums = [float(v) for v in re.findall(r"-?\d+\.\d+", " ".join(r))]
        pairs = [(a, b) for a, b in zip(nums, nums[1:])]
        if any(in_meylan_bbox(b, a) or in_meylan_bbox(a, b) for a, b in pairs) or \
                any("meylan" in v.lower() for v in r):
            keep.append(r)
    with open(dst, "w", newline="") as f:
        csv.writer(f, delimiter=sep).writerows(keep)
    return len(keep) - 1


def baac():
    """Accidents corporels 2015-2024 sur Meylan (com 38229)."""
    meta = http_get(BAAC_DATASET, retries=8).json()
    res = {}
    for r in meta["resources"]:
        t = r["title"].lower()
        m = re.search(r"(20\d\d)", t)
        if not m or not (2015 <= int(m.group(1)) <= 2024):
            continue
        y = int(m.group(1))
        for kind, pat in (("caract", r"^(caract|carcteristiques)"), ("lieux", r"^lieux"),
                          ("usagers", r"^usagers"), ("vehicules", r"^vehicules-\d|^vehicules_\d")):
            if re.search(pat, t.replace("_", "-")) and "immatric" not in t:
                res.setdefault(y, {})[kind] = r["url"]
    cx, cy = site()["center_l93"]
    out_rows = []
    for y, kinds in sorted(res.items()):
        if "caract" not in kinds:
            continue
        # seul le fichier « caractéristiques » (lieu, date, conditions) est nécessaire ici ;
        # réutilise une copie déjà présente quel que soit son nom d'origine
        cached = [f for f in (CACHE / "baac").glob(f"*{y}.csv")
                  if re.match(r"(caract|carcteristiques|caracteristiques)", f.name)]
        fcar = cached[0] if cached else download(kinds["caract"], CACHE / "baac" / f"caract-{y}.csv")
        raw = fcar.read_bytes()
        try:
            txt = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            txt = raw.decode("latin-1")
        sep = max([";", ","], key=txt.split("\n", 1)[0].count)
        rd = csv.DictReader(io.StringIO(txt), delimiter=sep)
        for r in rd:
            r = {k.strip().strip('"').lower(): (v or "").strip() for k, v in r.items() if k}
            r["num_acc"] = r.get("num_acc") or r.get("accident_id")
            com, dep = r.get("com", ""), r.get("dep", "")
            if not (com == "38229" or (dep in ("38", "380") and com.zfill(3) == "229")):
                continue
            lat, lon = r.get("lat", ""), r.get("long", "")
            try:
                if y >= 2019:
                    lat, lon = float(lat.replace(",", ".")), float(lon.replace(",", "."))
                else:
                    lat, lon = float(lat) / 1e5, float(lon) / 1e5
                x, yy = to_l93(lon, lat)
                d = round(math.hypot(x - cx, yy - cy), 1)
            except ValueError:
                lat = lon = d = None
            out_rows.append({"annee": y, "num_acc": r["num_acc"], "jour": r.get("jour"),
                             "mois": r.get("mois"), "hrmn": r.get("hrmn"), "lum": r.get("lum"),
                             "int": r.get("int"), "atm": r.get("atm"), "col": r.get("col"),
                             "adr": r.get("adr"), "lat": lat, "lon": lon,
                             "dist_paquet_jardin_m": d})
    with open(OUT / "baac_meylan_2015_2024.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    print("BAAC :", len(out_rows), "accidents à Meylan ;",
          sum(1 for r in out_rows if r["dist_paquet_jardin_m"] is not None
              and r["dist_paquet_jardin_m"] <= 150), "à ≤ 150 m du carrefour")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        try:
            f = download(url, CACHE / name)
        except Exception as e:  # noqa: BLE001
            print(f"{name:40s} ERREUR {str(e)[:100]}")
            continue
        dst = OUT / name
        if name.endswith((".geojson",)) or name in ("pistes_cyclables_metropole.json",):
            n = clip_geojson(f, dst)
        elif name.endswith(".csv") and name not in ("ban_meylan.csv",):
            n = clip_csv_latlon(f, dst)
        else:
            dst.write_bytes(f.read_bytes())
            n = "copié"
        print(f"{name:40s} {n}")
    for layer in ("parcelles", "batiments", "sections", "lieux_dits"):
        try:
            download(CADASTRE.format(layer), OUT / f"cadastre-38229-{layer}.json.gz")
            print(f"cadastre {layer:30s} ok")
        except Exception as e:  # noqa: BLE001
            print(f"cadastre {layer:30s} ERREUR {str(e)[:100]}")
    try:
        baac()
    except Exception as e:  # noqa: BLE001
        print("BAAC ERREUR", str(e)[:200])


if __name__ == "__main__":
    main()
