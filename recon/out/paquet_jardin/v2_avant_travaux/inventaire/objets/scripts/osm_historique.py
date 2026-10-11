"""Instantanés OSM historiques (Overpass [date:...]) des objets ponctuels du site Paquet Jardin.

Usage : python -I osm_historique.py <dossier_sortie>
Sortie : <dossier>/osm_<date>.json (réponse Overpass brute, out meta) pour chaque date.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
BB = "45.20620,5.76600,45.20910,5.77035"   # s,w,n,e
DATES = ["2020-06-01T00:00:00Z", "2022-05-10T00:00:00Z", "2023-06-01T00:00:00Z", "2024-06-01T00:00:00Z",
         "2025-06-20T00:00:00Z", None]


def requete(date):
    entete = f'[out:json][timeout:180]{"[date:%s]" % chr(34) + date + chr(34) if date else ""};'
    entete = f'[out:json][timeout:180]' + (f'[date:"{date}"]' if date else "") + ";"
    corps = f"""
(
  node({BB})(if:count_tags()>0);
  way({BB})[barrier];
  way({BB})[natural=tree_row];
  way({BB})[amenity=shelter];
  way({BB})[amenity=bicycle_parking];
);
out meta geom;
"""
    return entete + corps


def get(q):
    data = urllib.parse.urlencode({"data": q}).encode()
    for k in range(6):
        url = URLS[k % len(URLS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "paquet-jardin-recon/0.1"})
            with urllib.request.urlopen(req, timeout=200) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print("essai", k, url, type(e).__name__, str(e)[:120])
            time.sleep(10 * (k + 1))
    raise RuntimeError("Overpass indisponible")


def main(sortie):
    sortie = Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    for d in DATES:
        nom = (d or "actuel")[:10]
        f = sortie / f"osm_{nom}.json"
        if f.exists():
            continue
        r = get(requete(d))
        r["_requete"] = {"date": d or time.strftime("%Y-%m-%dT%H:%M:%SZ"), "bbox_sw_ne": BB, "overpass": requete(d)}
        f.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        print(nom, len(r.get("elements", [])))
        time.sleep(5)


if __name__ == "__main__":
    main(sys.argv[1])
