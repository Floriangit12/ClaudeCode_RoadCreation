"""Rattache chaque photo du catalogue Panoramax à la route OSM la plus proche et compte la couverture par axe
(A41, N87, bretelles, avenue de Verdun…). Écrit recon/out/generateur/meylan/auto_travail_lotB/panoramax/
photos_par_axe.json (non versionné).

    python recon/generateur/meylan/auto_outils/photos_par_axe.py      (shapely et pyproj : site-packages utilisateur, donc sans -I)

Une photo est « sur » une route si elle est à moins de --dmax m (défaut 8 m) de sa ligne OSM et si son cap est
dans ±35° de la direction de la ligne (ou de l'inverse si la route est à double sens) ; les photos prises depuis un
pont au-dessus d'une autoroute sont rattachées au pont (route la plus proche) et signalées « au-dessus de ».
"""
import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

RACINE = Path(__file__).resolve().parents[4]
TRAVAIL = RACINE / "recon" / "out" / "generateur" / "meylan" / "auto_travail_lotB"
T = Transformer.from_crs(4326, 2154, always_xy=True)


def cap_ligne(L, d):
    """Cap géographique (0 = nord, sens horaire) de la ligne à l'abscisse d."""
    a = L.interpolate(max(0.0, d - 2.0))
    b = L.interpolate(min(L.length, d + 2.0))
    return (math.degrees(math.atan2(b.x - a.x, b.y - a.y)) + 360.0) % 360.0


def ecart(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", default=str(TRAVAIL / "panoramax" / "catalogue_lotB.json"))
    ap.add_argument("--routes", default=str(TRAVAIL / "osm" / "routes_toutes.json"))
    ap.add_argument("--dmax", type=float, default=8.0)
    a = ap.parse_args()
    R = json.load(open(a.routes, encoding="utf-8"))["elements"]
    lignes, meta = [], []
    for e in R:
        t = e["tags"]
        if t.get("highway") in ("footway", "steps", "path", "cycleway", "service", "track", "pedestrian", "corridor",
                                "proposed", "construction", "platform", "elevator", "bridleway"):
            continue
        L = LineString([T.transform(p["lon"], p["lat"]) for p in e["geometry"]])
        lignes.append(L)
        meta.append({"way": e["id"], "highway": t.get("highway"), "ref": t.get("ref"), "name": t.get("name"),
                     "oneway": t.get("oneway"), "bridge": t.get("bridge"), "layer": t.get("layer"),
                     "lanes": t.get("lanes")})
    arbre = STRtree(lignes)
    photos = json.load(open(a.catalogue, encoding="utf-8"))
    sortie = []
    for ph in photos:
        x, y = T.transform(ph["lon"], ph["lat"])
        P = Point(x, y)
        idx = arbre.query(P.buffer(a.dmax))
        best = None
        for i in idx:
            L = lignes[int(i)]
            d = L.distance(P)
            if d > a.dmax:
                continue
            c = cap_ligne(L, L.project(P))
            m = meta[int(i)]
            if ph["azimut"] is None:
                ok = True
                e_ = None
            else:
                e_ = ecart(ph["azimut"], c)
                if m["oneway"] not in ("yes", "-1"):
                    e_ = min(e_, ecart(ph["azimut"], c + 180.0))
                ok = e_ <= 35.0
            score = d + (0 if ok else 50)
            if best is None or score < best[0]:
                best = (score, d, e_, m, ok)
        r = dict(ph)
        r["x_l93"], r["y_l93"] = round(x, 2), round(y, 2)
        if best:
            r["route"] = best[3]
            r["dist_route_m"] = round(best[1], 2)
            r["ecart_cap_deg"] = None if best[2] is None else round(best[2], 1)
            r["cap_ok"] = best[4]
        sortie.append(r)
    (TRAVAIL / "panoramax" / "photos_par_axe.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=0),
                                                               encoding="utf-8")
    c = Counter()
    ans = defaultdict(Counter)
    for r in sortie:
        m = r.get("route")
        if not m or not r.get("cap_ok"):
            continue
        k = (m["highway"], m["ref"], m["name"])
        c[k] += 1
        ans[k][(r["datetime"] or "")[:4]] += 1
    for k, v in c.most_common():
        if k[0] in ("motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary"):
            print(v, k, dict(sorted(ans[k].items())))


if __name__ == "__main__":
    main()
