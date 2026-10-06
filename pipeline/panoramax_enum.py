#!/usr/bin/env python3
"""
Enumerate ALL Panoramax pictures inside an area (default: commune of Meylan, 38229)
and save them as a slim GeoJSON (one Point feature per picture).

Why a quadtree: the Panoramax STAC /search endpoint returns no 'next' link and is
capped by 'limit' only (results are sorted by distance to bbox centre). So we ask
for `limit` items per bbox, and when a bbox is "full" (== limit) we split it in 4
and recurse. Results are de-duplicated by picture id.

Usage (run with python3 -I):
  python3 -I panoramax_enum.py --out meylan_panoramax.geojson \
      [--api https://api.panoramax.xyz/api] [--bbox minlon,minlat,maxlon,maxlat] \
      [--boundary meylan_contour.geojson] [--limit 2000] [--raw raw.ndjson] \
      [--center 45.20765,5.76820] [--collections-out collections.json]

--api can be the federated meta-catalog (https://api.panoramax.xyz/api, default)
or a single instance (https://panoramax.ign.fr/api, https://panoramax.openstreetmap.fr/api).
"""
import argparse
import json
import math
import sys
import time

import requests

DEFAULT_API = "https://api.panoramax.xyz/api"
MEYLAN_BBOX = (5.752471, 45.186932, 5.820473, 45.242427)
PAQUET_JARDIN = (45.20765, 5.76820)  # lat, lon

S = requests.Session()
S.headers["User-Agent"] = "meylan-adas-sim/0.1 (research; panoramax enumeration)"


def get_json(url, params=None, tries=4, timeout=120):
    last = None
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # network flakiness
            last = repr(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET {url} {params} failed: {last}")


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def search_quadtree(api, bbox, limit, out, depth=0, log=None):
    params = {"bbox": ",".join(f"{v:.7f}" for v in bbox), "limit": limit}
    d = get_json(f"{api}/search", params)
    feats = d.get("features", [])
    if log:
        log(f"{'  ' * depth}bbox={params['bbox']} -> {len(feats)}")
    if len(feats) >= limit and depth < 14:
        x0, y0, x1, y1 = bbox
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        for sub in ((x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)):
            search_quadtree(api, sub, limit, out, depth + 1, log)
    else:
        for f in feats:
            out[f["id"]] = f


def slim(f, center=None, poly=None):
    p = f.get("properties", {})
    ex = p.get("exif", {}) or {}
    io = p.get("pers:interior_orientation", {}) or {}
    lon, lat = f["geometry"]["coordinates"][:2]
    assets = f.get("assets", {})
    via = [l for l in f.get("links", []) if l.get("rel") == "via"]
    instance = via[0].get("instance_name") if via else None
    instance_url = via[0].get("href") if via else None
    if not instance:
        # querying an instance directly: derive from the hd asset host
        hd = assets.get("hd", {}).get("href", "")
        instance_url = hd.split("/api/")[0] if "/api/" in hd else None
    fov = io.get("field_of_view")
    proj = ex.get("Xmp.GPano.ProjectionType")
    is360 = (fov == 360) or (proj == "equirectangular")
    sensor = io.get("sensor_array_dimensions")
    w = ex.get("Exif.Photo.PixelXDimension") or (sensor[0] if sensor else None)
    h = ex.get("Exif.Photo.PixelYDimension") or (sensor[1] if sensor else None)
    sem_coll = (p.get("collection") or {}).get("semantics") or []
    out = {
        "id": f["id"],
        "collection": f.get("collection"),
        "instance": instance,
        "instance_url": instance_url,
        "producer": p.get("geovisio:producer"),
        "license": p.get("license"),
        "datetime": p.get("datetime"),
        "datetimetz": p.get("datetimetz"),
        "azimuth": p.get("view:azimuth"),
        "pers_yaw": p.get("pers:yaw"),
        "pers_pitch": p.get("pers:pitch"),
        "pers_roll": p.get("pers:roll"),
        "camera_make": io.get("camera_manufacturer") or ex.get("Exif.Image.Make"),
        "camera_model": io.get("camera_model") or ex.get("Exif.Image.Model"),
        "focal_length_mm": io.get("focal_length"),
        "field_of_view": fov,
        "projection": proj or ("equirectangular" if fov == 360 else "flat"),
        "is_360": bool(is360),
        "width": int(w) if w not in (None, "") else None,
        "height": int(h) if h not in (None, "") else None,
        "original_file_size": p.get("original_file:size"),
        "original_file_name": p.get("original_file:name"),
        "horizontal_accuracy_m": p.get("quality:horizontal_accuracy"),
        "pixel_density": p.get("panoramax:horizontal_pixel_density"),
        "gps_altitude": ex.get("Exif.GPSInfo.GPSAltitude"),
        "transport": ";".join(s.get("value", "") for s in sem_coll if s.get("key") == "transport") or None,
        "n_annotations": len(p.get("annotations") or []),
        "annotation_tags": sorted({s["key"] + "=" + s["value"] for a in (p.get("annotations") or [])
                                   for s in a.get("semantics", []) if s.get("key", "").startswith("osm|")}),
        "rank_in_collection": p.get("geovisio:rank_in_collection"),
        "hd": assets.get("hd", {}).get("href"),
        "sd": assets.get("sd", {}).get("href"),
        "thumb": assets.get("thumb", {}).get("href"),
        "lat": lat,
        "lon": lon,
    }
    if center:
        out["dist_center_m"] = round(haversine_m(center[0], center[1], lat, lon), 1)
    if poly is not None:
        from shapely.geometry import Point
        out["in_boundary"] = bool(poly.contains(Point(lon, lat)))
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--bbox", default=",".join(map(str, MEYLAN_BBOX)))
    ap.add_argument("--boundary", default=None, help="GeoJSON polygon; adds in_boundary flag")
    ap.add_argument("--clip", action="store_true", help="keep only pictures inside --boundary")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--center", default=f"{PAQUET_JARDIN[0]},{PAQUET_JARDIN[1]}", help="lat,lon")
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw", default=None, help="optional NDJSON dump of the full STAC items")
    ap.add_argument("--collections-out", default=None, help="optional JSON of collections metadata")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    bbox = tuple(float(v) for v in a.bbox.split(","))
    center = tuple(float(v) for v in a.center.split(",")) if a.center else None
    poly = None
    if a.boundary:
        from shapely.geometry import shape
        from shapely.ops import unary_union
        gj = json.load(open(a.boundary))
        geoms = [shape(f["geometry"]) for f in gj["features"]] if "features" in gj else [shape(gj.get("geometry", gj))]
        poly = unary_union(geoms)

    log = None if a.quiet else (lambda m: print(m, file=sys.stderr))
    items = {}
    t0 = time.time()
    search_quadtree(a.api.rstrip("/"), bbox, a.limit, items, log=log)
    if log:
        log(f"{len(items)} unique pictures in bbox, {time.time() - t0:.1f}s")

    feats = [slim(f, center, poly) for f in items.values()]
    if a.clip and poly is not None:
        feats = [f for f in feats if f["properties"]["in_boundary"]]
    feats.sort(key=lambda f: (f["properties"]["collection"] or "", f["properties"]["datetime"] or ""))
    with open(a.out, "w") as fh:
        json.dump({"type": "FeatureCollection",
                   "properties": {"source_api": a.api, "bbox": bbox, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                  "count": len(feats)},
                   "features": feats}, fh)
    if a.raw:
        keep = {f["properties"]["id"] for f in feats}
        with open(a.raw, "w") as fh:
            for i, f in items.items():
                if i in keep:
                    fh.write(json.dumps(f) + "\n")
    if a.collections_out:
        d = get_json(f"{a.api.rstrip('/')}/collections", {"bbox": a.bbox, "limit": 1000})
        cols = {c["id"]: c for c in d.get("collections", [])}
        used = {f["properties"]["collection"] for f in feats}
        missing = [c for c in used if c not in cols]
        for cid in missing:
            try:
                cols[cid] = get_json(f"{a.api.rstrip('/')}/collections/{cid}")
            except Exception as e:
                print("collection fetch failed", cid, e, file=sys.stderr)
        json.dump({cid: cols[cid] for cid in used if cid in cols}, open(a.collections_out, "w"))
    print(f"wrote {len(feats)} features -> {a.out}")


if __name__ == "__main__":
    main()
