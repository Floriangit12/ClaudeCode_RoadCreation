"""Téléchargement OSM complet de Meylan via l'API OSM 0.6 (/map par dalles)
puis export de couches GeoJSON thématiques utiles à la reconstruction de la
chaussée (voies, passages piétons, feux, aménagements cyclables, bordures,
surfaces de voirie, bâtiments, arbres, mobilier...).

Usage : python3 pipeline/osm.py [--margin 0.003]
"""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, mapping

from common import CONFIG, DATA, RAW, http_get

API = "https://api.openstreetmap.org/api/0.6/map"


def fetch_tiles(bbox, n=4, out=RAW / "osm"):
    out.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = bbox
    dx, dy = (x1 - x0) / n, (y1 - y0) / n
    files = []
    for i in range(n):
        for j in range(n):
            b = (x0 + i * dx, y0 + j * dy, x0 + (i + 1) * dx, y0 + (j + 1) * dy)
            f = out / f"map_{i}_{j}.osm"
            if not (f.exists() and f.stat().st_size > 0):
                r = http_get(API, params={"bbox": ",".join(f"{v:.6f}" for v in b)},
                             timeout=300)
                f.write_bytes(r.content)
            files.append(f)
            print("dalle", f.name, f.stat().st_size // 1024, "ko")
    return files


def merge(files):
    nodes, ways, rels = {}, {}, {}
    for f in files:
        root = ET.parse(f).getroot()
        for n in root.findall("node"):
            tags = {t.get("k"): t.get("v") for t in n.findall("tag")}
            nodes[n.get("id")] = (float(n.get("lon")), float(n.get("lat")), tags)
        for w in root.findall("way"):
            tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
            ways[w.get("id")] = ([nd.get("ref") for nd in w.findall("nd")], tags)
        for r in root.findall("relation"):
            tags = {t.get("k"): t.get("v") for t in r.findall("tag")}
            mem = [(m.get("type"), m.get("ref"), m.get("role")) for m in r.findall("member")]
            rels[r.get("id")] = (mem, tags)
    return nodes, ways, rels


AREA_KEYS = ("building", "area:highway", "landuse", "leisure", "natural", "amenity")


def way_geom(refs, tags, nodes):
    pts = [nodes[r][:2] for r in refs if r in nodes]
    if len(pts) < 2:
        return None
    closed = refs[0] == refs[-1] and len(pts) >= 4
    # une voie fermée (rond-point...) reste linéaire sauf area=yes
    linear_hw = "highway" in tags and tags.get("area") != "yes"
    is_area = closed and not linear_hw and (
        tags.get("area") == "yes" or any(k in tags for k in AREA_KEYS))
    if is_area:
        return Polygon(pts)
    return LineString(pts)


LAYERS = {
    # nom de couche : (prédicat sur tags, type d'objet)
    "roads": (lambda t: "highway" in t and t["highway"] not in (
        "footway", "path", "steps", "cycleway", "pedestrian", "bridleway", "track",
        "crossing", "traffic_signals", "street_lamp", "bus_stop", "give_way", "stop",
        "platform", "elevator", "corridor", "proposed", "construction"), "way"),
    # pistes dédiées + voies portant une bande/piste cyclable réelle
    # (cycleway:both=no / separate ne comptent pas)
    "cycleways": (lambda t: t.get("highway") == "cycleway" or t.get("bicycle") == "designated"
                  or any(k.startswith("cycleway") and k.count(":") <= 1
                         and v not in ("no", "none", "separate") for k, v in t.items()), "way"),
    "footways": (lambda t: t.get("highway") in ("footway", "path", "pedestrian", "steps"), "way"),
    "road_areas": (lambda t: "area:highway" in t or (t.get("highway") and t.get("area") == "yes"), "way"),
    "crossings": (lambda t: t.get("highway") == "crossing" or "crossing" in t, "node"),
    "traffic_signals": (lambda t: t.get("highway") == "traffic_signals" or
                        t.get("crossing") == "traffic_signals", "node"),
    "traffic_calming": (lambda t: "traffic_calming" in t, "any"),
    "kerbs": (lambda t: "kerb" in t or t.get("barrier") == "kerb", "any"),
    "road_signs": (lambda t: "traffic_sign" in t or t.get("highway") in ("stop", "give_way"), "node"),
    "street_lamps": (lambda t: t.get("highway") == "street_lamp", "node"),
    "public_transport": (lambda t: "public_transport" in t or t.get("highway") == "bus_stop", "any"),
    "parking": (lambda t: t.get("amenity") == "parking" or any(k.startswith("parking:") for k in t), "any"),
    "buildings": (lambda t: "building" in t, "way"),
    "trees": (lambda t: t.get("natural") in ("tree", "tree_row"), "any"),
    "barriers": (lambda t: "barrier" in t and t.get("barrier") != "kerb", "any"),
    "landuse": (lambda t: any(k in t for k in ("landuse", "leisure")) or
                t.get("natural") in ("wood", "grassland", "scrub", "water"), "way"),
    "railways_tram": (lambda t: "railway" in t, "any"),
}


def export(nodes, ways, out=DATA / "vector" / "osm"):
    out.mkdir(parents=True, exist_ok=True)
    feats = {k: [] for k in LAYERS}
    for nid, (lon, lat, tags) in nodes.items():
        if not tags:
            continue
        for name, (pred, kind) in LAYERS.items():
            if kind in ("node", "any") and pred(tags):
                feats[name].append({"type": "Feature", "id": f"n{nid}",
                                    "properties": {"osm_id": f"node/{nid}", **tags},
                                    "geometry": mapping(Point(lon, lat))})
    for wid, (refs, tags) in ways.items():
        if not tags:
            continue
        g = None
        for name, (pred, kind) in LAYERS.items():
            if kind in ("way", "any") and pred(tags):
                g = g or way_geom(refs, tags, nodes)
                if g is None:
                    break
                feats[name].append({"type": "Feature", "id": f"w{wid}",
                                    "properties": {"osm_id": f"way/{wid}", **tags},
                                    "geometry": mapping(g)})
    for name, fs in feats.items():
        (out / f"{name}.geojson").write_text(json.dumps(
            {"type": "FeatureCollection", "features": fs}, ensure_ascii=False))
        print(f"{name:18s} {len(fs):6d} objets")
    return feats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margin", type=float, default=0.003)
    ap.add_argument("--grid", type=int, default=4)
    a = ap.parse_args()
    x0, y0, x1, y1 = CONFIG["commune"]["bbox_wgs84"]
    m = a.margin
    files = fetch_tiles((x0 - m, y0 - m, x1 + m, y1 + m), n=a.grid)
    nodes, ways, rels = merge(files)
    print(len(nodes), "noeuds", len(ways), "ways", len(rels), "relations")
    export(nodes, ways)
    # relations de lignes de transport (bus/tram) : liste simple
    routes = [{"id": rid, **tags, "n_members": len(mem)} for rid, (mem, tags) in rels.items()
              if tags.get("type") == "route"]
    (DATA / "vector" / "osm" / "routes.json").write_text(json.dumps(routes, ensure_ascii=False, indent=1))
    print(len(routes), "relations route")


if __name__ == "__main__":
    main()
