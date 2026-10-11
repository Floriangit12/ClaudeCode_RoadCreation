"""Différence OSM entre deux instantanés Overpass ([date:...]) sur l'emprise du site.
python -I osm_diff.py <snapshot_avant.json> <snapshot_apres.json> <sortie.json>
Ne garde que les objets dont l'apparition, la disparition ou le changement de tags/géométrie
intéressent la scène (voirie, traversées, arrêts, bâtiments, arbres, mobilier, chantier)."""
import json
import math
import sys

from pyproj import Transformer

O = (917279.43, 6460289.98)
TR = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
CLES = ("highway", "crossing", "footway", "cycleway", "public_transport", "bus", "building", "natural",
        "barrier", "amenity", "landuse", "construction", "traffic_signals", "kerb", "leisure", "man_made",
        "parking", "surface", "lanes", "tactile_paving", "crossing:markings", "traffic_calming", "power", "entrance")


def charger(p):
    d = json.load(open(p, encoding="utf-8"))
    return {(e["type"], e["id"]): e for e in d["elements"]}


def centre(e):
    if e["type"] == "node":
        x, y = TR.transform(e["lon"], e["lat"])
    elif "geometry" in e and e["geometry"]:
        pts = [TR.transform(g["lon"], g["lat"]) for g in e["geometry"] if g]
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
    elif "bounds" in e:
        b = e["bounds"]
        x, y = TR.transform((b["minlon"] + b["maxlon"]) / 2, (b["minlat"] + b["maxlat"]) / 2)
    else:
        return None
    return [round(x - O[0], 1), round(y - O[1], 1)]


def geom_l93(e):
    if e["type"] == "node":
        return [list(TR.transform(e["lon"], e["lat"]))]
    if "geometry" in e and e["geometry"]:
        return [list(TR.transform(g["lon"], g["lat"])) for g in e["geometry"] if g]
    return []


def interessant(t):
    return any(k in t for k in CLES)


def resume(t):
    return {k: v for k, v in t.items() if k in CLES or k in ("name", "ref", "operator", "start_date", "check_date", "note", "fixme", "description", "route")}


A, B = charger(sys.argv[1]), charger(sys.argv[2])
out = []
for k in sorted(set(A) | set(B)):
    a, b = A.get(k), B.get(k)
    ta, tb = (a or {}).get("tags", {}), (b or {}).get("tags", {})
    if not (interessant(ta) or interessant(tb)):
        continue
    if a and b and a.get("version") == b.get("version"):
        continue
    if a is None:
        etat = "ajoute"
    elif b is None:
        etat = "supprime"
    else:
        etat = "modifie"
    diff = {}
    if a and b:
        for kk in sorted(set(ta) | set(tb)):
            if ta.get(kk) != tb.get(kk):
                diff[kk] = [ta.get(kk), tb.get(kk)]
        ga, gb = geom_l93(a), geom_l93(b)
        if len(ga) == len(gb) and ga:
            dmax = max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(ga, gb))
        else:
            dmax = None if not (ga and gb) else -1
        if not diff and (dmax is not None and 0 <= dmax < 0.05):
            continue
    else:
        dmax = None
    e = b or a
    c = centre(e)
    if c is None or abs(c[0]) > 170 or abs(c[1]) > 170:
        continue
    out.append({"osm": f"{k[0]}/{k[1]}", "etat": etat, "local": c,
                "tags_apres" if b else "tags_avant": resume(tb if b else ta),
                "diff_tags": diff, "deplacement_max_m": None if dmax is None else round(dmax, 2),
                "geometrie_l93": [[round(p[0], 2), round(p[1], 2)] for p in geom_l93(e)],
                "version_avant": (a or {}).get("version"), "version_apres": (b or {}).get("version"),
                "horodatage_apres": (b or {}).get("timestamp"), "auteur_apres": (b or {}).get("user"),
                "changeset_apres": (b or {}).get("changeset")})
json.dump({"avant": sys.argv[1], "apres": sys.argv[2], "n": len(out), "changements": out},
          open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
import collections
print(len(out), collections.Counter(o["etat"] for o in out))
