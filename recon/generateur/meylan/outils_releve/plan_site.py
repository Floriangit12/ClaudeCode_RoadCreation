#!/usr/bin/env python
"""Relevé Meylan (lot A) : données vectorielles locales d'un site, plan annoté et coupes en travers.

Sources locales du dépôt (aucune requête réseau) :
  - OSM, extrait de Meylan du 09/10/2026 : data/vector_gz/osm/*.geojson.gz (ODbL © contributeurs OpenStreetMap) ;
  - levé topographique de Grenoble-Alpes Métropole (Meylan_Topo.dwg, « PLAN_GLOBAL », non daté, compilation de
    plans de géomètres : bordures, marquages, arbres) : data/vector_gz/gam/topo_sol_*.geojson.gz ;
  - PCRS vecteur GAM (limites de voirie, 2019-2022) : data/vector_gz/gam/limite_voirie_pcrs.geojson.gz.

Repère du site : celui de mesures.json (« repere », écrit par ortho_osm_site.py preparer) : x est, y nord, m.

Commandes :
  python -I plan_site.py extraire SITE [--rayon 110]
        résumé OSM versionné dans mesures.json (« osm » : voies, nœuds feux / passages / panneaux / arbres) ;
        entités GAM découpées au rayon dans recon/out/generateur/meylan/<site>/vecteurs/ (non versionné).
  python -I plan_site.py plan SITE [--cote 120] [--cx 0 --cy 0] [--echelle 2]
        plan annoté : ortho IGN 2024 + bordures GAM (cyan) + marquages GAM (jaune) + axes OSM (magenta)
        + arbres GAM (vert) + grille de 10 m ; découpé en tuiles natives (decoupe.py image).
  python -I plan_site.py coupe SITE X0 Y0 X1 Y1 [--nom c1]
        intersections du segment avec les bordures, marquages, limites PCRS et axes OSM, triées le long du
        segment, et largeurs entre intersections successives (mesure « gam: » ou « pcrs: »).
"""
import argparse
import gzip
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, Point, shape
from shapely.ops import transform as stransform

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "recon/out/generateur/meylan"
VERS = RACINE / "recon/generateur/meylan"
VG = RACINE / "data/vector_gz"
DECOUPE = RACINE / "recon/pcg/vision/decoupe.py"
T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
PAS = 0.20

COUCHES_GAM = {
    "bordure": "gam/topo_sol_bordure_lin.geojson.gz",
    "marquage": "gam/topo_sol_signalisation_horizontale_lin.geojson.gz",
    "marquage_pct": "gam/topo_sol_signalisation_horizontale_pct.geojson.gz",
    "arbre": "gam/topo_sol_arbre_pct.geojson.gz",
    "caniveau": "gam/topo_sol_caniveau_lin.geojson.gz",
    "revetement": "gam/topo_sol_limite_revetement_lin.geojson.gz",
    "vegetation": "gam/topo_sol_vegetation_lin.geojson.gz",
    "glissiere": "gam/topo_sol_glissiere_lin.geojson.gz",
    "pcrs_voirie": "gam/limite_voirie_pcrs.geojson.gz",
    "cyclable_gam": "gam/v_amenagements_cyclables_grand_public.geojson.gz",
}
COUCHES_OSM = ["roads", "cycleways", "footways", "crossings", "traffic_signals", "road_signs", "kerbs",
               "traffic_calming", "trees", "street_lamps", "road_areas", "public_transport", "barriers", "parking"]


def mesures(site):
    return json.loads((VERS / site / "mesures.json").read_text(encoding="utf-8"))


def ecrire(site, doc):
    (VERS / site / "mesures.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def vers_local(origine):
    x0, y0 = origine[0], origine[1]

    def f(lon, lat, z=None):
        X, Y = T.transform(lon, lat)
        return (np.asarray(X) - x0, np.asarray(Y) - y0)
    return f


def lire(rel):
    return json.load(gzip.open(VG / rel, "rt", encoding="utf-8"))["features"]


def cmd_extraire(a):
    doc = mesures(a.site)
    o = doc["repere"]["origine_l93"]
    f = vers_local(o)
    disque = Point(0, 0).buffer(a.rayon)
    vd = OUT / a.site / "vecteurs"
    vd.mkdir(parents=True, exist_ok=True)
    gam = {}
    for nom, rel in COUCHES_GAM.items():
        out = []
        for ft in lire(rel):
            try:
                g = stransform(f, shape(ft["geometry"]))
            except Exception:
                continue
            if g.is_empty or not g.intersects(disque):
                continue
            p = ft["properties"]
            out.append({"type": "Feature", "properties": {k: p.get(k) for k in ("calque", "bloc", "rotation", "echelle_bloc",
                                                                                "libelle", "id_objet", "calque",
                                                                                "type_amenagement", "date_leve")},
                        "geometry": json.loads(json.dumps(g.__geo_interface__))})
        gam[nom] = out
        (vd / ("gam_%s.json" % nom)).write_text(json.dumps({"type": "FeatureCollection", "features": out}), encoding="utf-8")
    osm_v, osm_n = [], []
    for nom in COUCHES_OSM:
        for ft in lire("osm/%s.geojson.gz" % nom):
            try:
                g = stransform(f, shape(ft["geometry"]))
            except Exception:
                continue
            if g.is_empty or not g.intersects(disque):
                continue
            p = {k: v for k, v in ft["properties"].items() if v not in (None, "")}
            if g.geom_type == "Point":
                osm_n.append({"couche": nom, "id": p.pop("osm_id", None), "tags": p, "local": [round(g.x, 2), round(g.y, 2)]})
            else:
                if g.geom_type == "LineString":
                    pts = [[round(x, 2), round(y, 2)] for x, y in g.coords]
                elif g.geom_type == "Polygon":
                    pts = [[round(x, 2), round(y, 2)] for x, y in g.exterior.coords]
                else:
                    pts = [[round(x, 2), round(y, 2)] for gg in getattr(g, "geoms", []) for x, y in
                           (gg.coords if gg.geom_type == "LineString" else gg.exterior.coords)]
                osm_v.append({"couche": nom, "id": p.pop("osm_id", None), "tags": p, "local": pts})
    (vd / "osm.json").write_text(json.dumps({"voies": osm_v, "noeuds": osm_n}, ensure_ascii=False), encoding="utf-8")
    garder = ("highway", "name", "ref", "lanes", "lanes:forward", "lanes:backward", "oneway", "maxspeed", "width",
              "turn:lanes", "turn:lanes:forward", "turn:lanes:backward", "cycleway", "cycleway:left", "cycleway:right",
              "cycleway:both", "sidewalk", "sidewalk:both", "sidewalk:left", "sidewalk:right", "surface", "junction",
              "segregated", "bicycle", "foot", "crossing", "crossing:island", "crossing:markings", "traffic_signals",
              "traffic_signals:direction", "direction", "traffic_sign", "traffic_calming", "kerb", "tactile_paving",
              "button_operated", "natural", "species", "genus", "height", "leaf_type", "parking:both", "parking:left",
              "parking:right", "lit", "dual_carriageway", "placement", "bus", "psv", "area:highway", "amenity",
              "public_transport", "shelter", "barrier", "lane_markings", "smoothness", "maxspeed:type", "zone:maxspeed",
              "cycle_network", "network", "layer", "bridge")
    doc["osm"] = {
        "source": "OpenStreetMap, extrait local de Meylan du 09/10/2026 (data/vector_gz/osm), ODbL © contributeurs OpenStreetMap",
        "rayon_m": a.rayon,
        "voies": [{"couche": v["couche"], "id": v["id"], "tags": {k: t for k, t in v["tags"].items() if k in garder},
                   "de": v["local"][0], "a": v["local"][-1], "n_points": len(v["local"])}
                  for v in osm_v if v["couche"] in ("roads", "cycleways", "footways", "road_areas")],
        "noeuds": [{"couche": n["couche"], "id": n["id"], "tags": {k: t for k, t in n["tags"].items() if k in garder},
                    "local": n["local"]} for n in osm_n if n["couche"] in
                   ("crossings", "traffic_signals", "road_signs", "kerbs", "traffic_calming", "trees", "public_transport")],
        "decompte": {c: sum(1 for v in osm_v + osm_n if v["couche"] == c) for c in COUCHES_OSM},
    }
    doc["gam"] = {"source": "Grenoble-Alpes Métropole, levé topographique Meylan_Topo.dwg (PLAN_GLOBAL, non daté) et PCRS "
                            "vecteur (data/vector_gz/gam) ; « ces données ne sont pas nécessairement à jour » (métadonnée GAM)",
                  "rayon_m": a.rayon, "decompte": {k: len(v) for k, v in gam.items()}}
    ecrire(a.site, doc)
    print(a.site, doc["osm"]["decompte"], doc["gam"]["decompte"])


def lignes(geom):
    g = shape(geom)
    if g.geom_type in ("LineString", "MultiLineString"):
        return list(getattr(g, "geoms", [g]))
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return [LineString(p.exterior.coords) for p in getattr(g, "geoms", [g])]
    return []


def police(t):
    for nom in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except Exception:
            pass
    return ImageFont.load_default()


def cmd_plan(a):
    doc = mesures(a.site)
    oj = json.loads((OUT / a.site / "ortho" / "ortho.json").read_text(encoding="utf-8"))
    im = np.asarray(Image.open(OUT / a.site / "ortho" / oj["fichier"]).convert("RGB"))
    b = oj["bbox_l93"]
    xc, yc = oj["centre_l93"]
    e = a.echelle
    c = a.cote
    x0, y1 = a.cx - c / 2, a.cy + c / 2
    npx = int(round(c / PAS))
    i0 = int(round((xc + x0 - b[0]) / PAS))
    j0 = int(round((b[3] - (yc + y1)) / PAS))
    H, W = im.shape[:2]
    fen = np.zeros((npx, npx, 3), np.uint8)
    si0, sj0, si1, sj1 = max(0, i0), max(0, j0), min(W, i0 + npx), min(H, j0 + npx)
    if si1 > si0 and sj1 > sj0:
        fen[sj0 - j0:sj1 - j0, si0 - i0:si1 - i0] = im[sj0:sj1, si0:si1]
    big = Image.fromarray((fen * 0.75).astype(np.uint8)).resize((npx * e, npx * e), Image.NEAREST)
    dr = ImageDraw.Draw(big)

    def px(x, y):
        return ((x - x0) / PAS * e, (y1 - y) / PAS * e)
    vd = OUT / a.site / "vecteurs"
    styles = [("pcrs_voirie", (255, 140, 0), 1), ("revetement", (150, 150, 255), 1), ("vegetation", (60, 200, 60), 1),
              ("caniveau", (0, 120, 255), 1), ("bordure", (0, 255, 255), 2), ("glissiere", (255, 0, 0), 2),
              ("marquage", (255, 255, 0), 1)]
    for nom, col, w in styles:
        fj = vd / ("gam_%s.json" % nom)
        if not fj.exists():
            continue
        for ft in json.loads(fj.read_text(encoding="utf-8"))["features"]:
            for l in lignes(ft["geometry"]):
                pts = [px(x, y) for x, y, *_ in l.coords]
                if len(pts) > 1:
                    dr.line(pts, fill=col, width=w)
    osm = json.loads((vd / "osm.json").read_text(encoding="utf-8"))
    for v in osm["voies"]:
        if v["couche"] in ("roads", "cycleways"):
            pts = [px(x, y) for x, y in v["local"]]
            dr.line(pts, fill=(255, 0, 255) if v["couche"] == "roads" else (0, 255, 0), width=1)
    fa = vd / "gam_arbre.json"
    if fa.exists():
        for ft in json.loads(fa.read_text(encoding="utf-8"))["features"]:
            g = shape(ft["geometry"])
            for p in getattr(g, "geoms", [g]):
                u, v = px(p.x, p.y)
                dr.ellipse([u - 4, v - 4, u + 4, v + 4], outline=(0, 255, 0), width=2)
    for n in osm["noeuds"]:
        u, v = px(*n["local"])
        if n["couche"] == "traffic_signals":
            dr.rectangle([u - 4, v - 4, u + 4, v + 4], outline=(255, 0, 0), width=2)
        elif n["couche"] == "crossings":
            dr.ellipse([u - 3, v - 3, u + 3, v + 3], fill=(255, 255, 255))
    fo = police(13)
    k = math.ceil(x0 / 10)
    while k * 10 <= x0 + c:
        u = (k * 10 - x0) / PAS * e
        dr.line([(u, 0), (u, npx * e)], fill=(255, 255, 255), width=1)
        dr.text((u + 2, 2), "x%+d" % (k * 10), fill=(255, 255, 255), font=fo)
        k += 1
    k = math.ceil((y1 - c) / 10)
    while k * 10 <= y1:
        v = (y1 - k * 10) / PAS * e
        dr.line([(0, v), (npx * e, v)], fill=(255, 255, 255), width=1)
        dr.text((2, v + 2), "y%+d" % (k * 10), fill=(255, 255, 255), font=fo)
        k += 1
    d = OUT / a.site / "plan"
    d.mkdir(parents=True, exist_ok=True)
    nom = "plan_%s_cx%+04d_cy%+04d_c%d_e%d" % (a.site, round(a.cx), round(a.cy), round(c), e)
    big.save(d / (nom + ".png"))
    if big.width > 1092 or big.height > 1092:
        subprocess.run([sys.executable, "-I", str(DECOUPE), "image", str(d / (nom + ".png")), str(d / ("tuiles_" + nom))],
                       check=True)
    print(d / (nom + ".png"), big.size)


def cmd_coupe(a):
    vd = OUT / a.site / "vecteurs"
    seg = LineString([(a.x0, a.y0), (a.x1, a.y1)])
    L = seg.length
    res = []
    for nom in ("bordure", "marquage", "caniveau", "revetement", "vegetation", "pcrs_voirie", "glissiere"):
        fj = vd / ("gam_%s.json" % nom)
        if not fj.exists():
            continue
        for ft in json.loads(fj.read_text(encoding="utf-8"))["features"]:
            for l in lignes(ft["geometry"]):
                l2 = LineString([(x, y) for x, y, *_ in l.coords])
                inter = seg.intersection(l2)
                for p in getattr(inter, "geoms", [inter]):
                    if p.is_empty or p.geom_type != "Point":
                        continue
                    res.append((round(seg.project(p), 2), nom, ft["properties"].get("bloc") or ft["properties"].get("calque")))
    osm = json.loads((vd / "osm.json").read_text(encoding="utf-8"))
    for v in osm["voies"]:
        if v["couche"] not in ("roads", "cycleways", "footways") or len(v["local"]) < 2:
            continue
        inter = seg.intersection(LineString(v["local"]))
        for p in getattr(inter, "geoms", [inter]):
            if not p.is_empty and p.geom_type == "Point":
                t = v["tags"]
                res.append((round(seg.project(p), 2), "osm_" + v["couche"],
                            "%s %s %s lanes=%s" % (v["id"], t.get("highway"), t.get("name", ""), t.get("lanes", ""))))
    res.sort()
    print("coupe %s (%.1f m) de (%.1f ; %.1f) à (%.1f ; %.1f)" % (a.nom, L, a.x0, a.y0, a.x1, a.y1))
    prec = None
    for s, nom, det in res:
        ecart = "" if prec is None else "  (+%.2f)" % (s - prec)
        print("  %6.2f  %-12s %s%s" % (s, nom, det, ecart))
        if not nom.startswith("osm"):
            prec = s
    d = OUT / a.site / "coupes"
    d.mkdir(parents=True, exist_ok=True)
    (d / ("coupe_%s.json" % a.nom)).write_text(json.dumps({"segment": [a.x0, a.y0, a.x1, a.y1], "intersections": res},
                                                         ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    e = s.add_parser("extraire"); e.add_argument("site"); e.add_argument("--rayon", type=float, default=110)
    pl = s.add_parser("plan"); pl.add_argument("site"); pl.add_argument("--cote", type=float, default=120)
    pl.add_argument("--cx", type=float, default=0); pl.add_argument("--cy", type=float, default=0)
    pl.add_argument("--echelle", type=int, default=2)
    c = s.add_parser("coupe"); c.add_argument("site")
    for k in ("x0", "y0", "x1", "y1"):
        c.add_argument(k, type=float)
    c.add_argument("--nom", default="c1")
    a = p.parse_args()
    {"extraire": cmd_extraire, "plan": cmd_plan, "coupe": cmd_coupe}[a.cmd](a)


if __name__ == "__main__":
    main()
