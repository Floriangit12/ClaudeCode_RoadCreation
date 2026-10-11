"""Panoramax : recherche des photos 2022-2025 du site (méta-catalogue) et annotations sémantiques.

Usage : python -I pnx_semantique.py <index_panoramax_geojson> <dossier_sortie>
Sorties : recherche_2022_2025.json (items de /api/search, sans les images),
          annotations.json (par photo annotée de l'index : annotations {forme, sémantique}).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

META = "https://api.panoramax.xyz/api"
BBOX = "5.76600,45.20620,5.77035,45.20910"


def get(url):
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paquet-jardin-recon/0.1", "Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print("essai", k, url[:90], type(e).__name__, str(e)[:100])
            time.sleep(5 * (k + 1))
    return None


def main(index, sortie):
    sortie = Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    # 1. recherche fédérée 2022-01-01 .. 2025-06-22
    items = []
    url = f"{META}/search?" + urllib.parse.urlencode({"bbox": BBOX, "limit": 500, "datetime": "2022-01-01T00:00:00Z/2025-06-22T23:59:59Z"})
    while url:
        d = get(url)
        if not d:
            break
        for f in d.get("features", []):
            p = f.get("properties", {})
            items.append({"id": f.get("id"), "collection": f.get("collection"), "datetime": p.get("datetime"),
                          "geometry": f.get("geometry"), "azimuth": p.get("view:azimuth"),
                          "instance": (f.get("providers") or [{}])[0].get("name") if f.get("providers") else None,
                          "semantics": p.get("semantics"), "annotations": p.get("annotations"),
                          "links_self": [l.get("href") for l in f.get("links", []) if l.get("rel") == "self"]})
        nxt = [l.get("href") for l in d.get("links", []) if l.get("rel") == "next"]
        url = nxt[0] if nxt else None
    (sortie / "recherche_2022_2025.json").write_text(json.dumps(
        {"source": f"{META}/search bbox={BBOX} datetime=2022-01-01/2025-06-22", "date_requete": time.strftime("%Y-%m-%d"),
         "n": len(items), "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("recherche :", len(items))
    # 2. annotations des photos annotées de l'index du site
    idx = json.loads(Path(index).read_text(encoding="utf-8"))
    ann = {}
    for f in idx["features"]:
        p = f["properties"]
        if not p.get("n_annotations"):
            continue
        u = f"{p['instance_url']}/api/collections/{p['collection']}/items/{p['id']}"
        d = get(u)
        if not d:
            continue
        q = d.get("properties", {})
        ann[p["id"]] = {"datetime": p["datetime"], "instance": p["instance_url"], "semantics": q.get("semantics"),
                        "annotations": q.get("annotations"), "width": p.get("width"), "height": p.get("height")}
        time.sleep(0.3)
    (sortie / "annotations.json").write_text(json.dumps(
        {"source": "Panoramax /api/collections/{c}/items/{id} (properties.annotations, semantics)",
         "licence": "CC-BY-SA 4.0 (Panoramax, contributeurs)", "date_requete": time.strftime("%Y-%m-%d"),
         "n": len(ann), "photos": ann}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("photos annotées :", len(ann))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
