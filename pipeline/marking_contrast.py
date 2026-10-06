"""Indice objectif d'usure des marquages à partir de l'ortho 5 cm.

Principe : la peinture routière est une structure claire et fine posée sur un
enrobé plus sombre. Le chapeau haut-de-forme (« top-hat » morphologique) de la
luminance — luminance moins son ouverture par un élément structurant de
~2 m — isole ces structures et mesure leur contraste local avec l'enrobé
environnant. Un marquage neuf a un contraste élevé ; un marquage usé, grisé ou
partiellement arraché a un contraste faible et une couverture lacunaire.

Sorties (site) :
  data/sites/<site>/marquages/contraste_5cm/*.jpg   tuiles 1000x1000 colorées
      (vert = contraste fort/neuf, jaune = moyen, rouge = faible/usé), même
      nommage que les tuiles PCRS (coin bas-gauche L93)
  data/sites/<site>/marquages/contraste_par_tuile.json
  data/sites/<site>/marquages/contraste_marquages_gam.geojson  (si levés GAM
      disponibles : indice par objet de marquage levé)

Usage : python3 pipeline/marking_contrast.py --site paquet_jardin
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from shapely.geometry import box, mapping, shape
from shapely.ops import transform, unary_union

from common import DATA, RAW, TILE_PX, _to_l93, to_wgs84

RES = 0.05
SE_M = 2.0          # élément structurant (m) : > largeur des marquages (bandes de zébra 0,5 m)
T_PAINT = 25        # seuil top-hat (niveaux de luminance) pour « pixel peint »
MAX_BLOB_M2 = 3.0   # tache claire > 3 m² peu contrastée = réparation d'enrobé, pas de la peinture


def to_l93_geom(g):
    return transform(lambda x, y, z=None: _to_l93.transform(x, y), g)


def load_mosaic(tiles_dir: Path):
    idx = json.loads((tiles_dir / "index.json").read_text())["tiles"]
    x0 = min(t["l93_bbox"][0] for t in idx)
    y0 = min(t["l93_bbox"][1] for t in idx)
    x1 = max(t["l93_bbox"][2] for t in idx)
    y1 = max(t["l93_bbox"][3] for t in idx)
    w, h = int(round((x1 - x0) / RES)), int(round((y1 - y0) / RES))
    m = np.zeros((h, w, 3), np.uint8)
    for t in idx:
        a = np.asarray(Image.open(tiles_dir / t["file"]).convert("RGB"))
        c = int(round((t["l93_bbox"][0] - x0) / RES))
        r = int(round((y1 - t["l93_bbox"][3]) / RES))
        m[r:r + a.shape[0], c:c + a.shape[1]] = a
    return m, (x0, y0, x1, y1), idx


def road_mask(site: str, bbox, shape_hw):
    """Masque de chaussée : levés GAM (limite de voirie PCRS) si présents,
    sinon axes OSM tamponnés selon leur largeur/nb de voies."""
    vec = DATA / "sites" / site / "vector"
    polys = []
    f = vec / "osm_roads.geojson"
    for ft in json.loads(f.read_text())["features"]:
        p = ft["properties"]
        hw = p.get("highway")
        if hw in ("footway", "path", "steps", "pedestrian"):
            continue
        try:
            w = float(p.get("width", 0))
        except ValueError:
            w = 0
        if not w:
            lanes = int(p.get("lanes", 2 if p.get("oneway") != "yes" else 1) or 1)
            w = 3.5 * lanes
        polys.append(to_l93_geom(shape(ft["geometry"])).buffer(w / 2 + 1.0))
    for name in ("osm_cycleways.geojson",):
        g = vec / name
        if g.exists():
            for ft in json.loads(g.read_text())["features"]:
                polys.append(to_l93_geom(shape(ft["geometry"])).buffer(2.5))
    zone = unary_union(polys)
    x0, y0, x1, y1 = bbox
    mask = np.zeros(shape_hw, np.uint8)
    geoms = getattr(zone, "geoms", [zone])
    for g in geoms:
        if g.is_empty:
            continue
        pts = np.array([[(x - x0) / RES, (y1 - y) / RES] for x, y in g.exterior.coords], np.int32)
        cv2.fillPoly(mask, [pts], 1)
        for hole in g.interiors:
            pts = np.array([[(x - x0) / RES, (y1 - y) / RES] for x, y in hole.coords], np.int32)
            cv2.fillPoly(mask, [pts], 0)
    return mask.astype(bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="paquet_jardin")
    a = ap.parse_args()
    tiles_dir = RAW / "pcrs5cm" / "tiles" / a.site
    m, bbox, idx = load_mosaic(tiles_dir)
    lab = cv2.cvtColor(m, cv2.COLOR_RGB2LAB)
    L = lab[:, :, 0]
    k = int(SE_M / RES) | 1
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    tophat = cv2.morphologyEx(L, cv2.MORPH_TOPHAT, se)
    road = road_mask(a.site, bbox, L.shape)
    # chroma : la peinture blanche est peu saturée, la jaune a b* élevé ;
    # on écarte les objets très saturés (voitures colorées, végétation)
    chroma = np.hypot(lab[:, :, 1].astype(int) - 128, lab[:, :, 2].astype(int) - 128)
    yellow = (lab[:, :, 2].astype(int) - 128) > 18
    paint = road & (tophat > T_PAINT) & ((chroma < 22) | yellow)
    ref = float(np.percentile(tophat[paint], 95)) if paint.any() else 100.0
    idx_wear = np.clip(tophat.astype(float) / ref, 0, 1)   # 1 = aussi contrasté que le neuf du site
    # filtre de forme : les grandes taches claires mais peu contrastées sont des
    # reprises d'enrobé / zones décolorées, pas des marquages
    n, lab_cc, st, _ = cv2.connectedComponentsWithStats(paint.astype(np.uint8), connectivity=8)
    mean_idx = np.bincount(lab_cc.ravel(), weights=idx_wear.ravel(), minlength=n) / np.maximum(
        np.bincount(lab_cc.ravel(), minlength=n), 1)
    area_m2 = st[:, cv2.CC_STAT_AREA] * RES * RES
    bad = (area_m2 > MAX_BLOB_M2) & (mean_idx < 0.45)
    bad[0] = False
    paint &= ~bad[lab_cc]

    out = DATA / "sites" / a.site / "marquages"
    (out / "contraste_5cm").mkdir(parents=True, exist_ok=True)
    # rendu : fond = ortho assombrie, peinture colorée selon l'indice
    base = (m * 0.45).astype(np.uint8)
    col = np.zeros_like(m)
    v = idx_wear
    col[..., 0] = np.clip(255 * (1 - (v - 0.5) * 2), 0, 255).astype(np.uint8)   # rouge si faible
    col[..., 1] = np.clip(255 * (v * 2), 0, 255).astype(np.uint8)               # vert si fort
    rend = np.where(paint[..., None], col, base)
    x0, y0, x1, y1 = bbox
    stats = []
    for t in idx:
        c = int(round((t["l93_bbox"][0] - x0) / RES))
        r = int(round((y1 - t["l93_bbox"][3]) / RES))
        sl = (slice(r, r + TILE_PX), slice(c, c + TILE_PX))
        Image.fromarray(rend[sl]).save(out / "contraste_5cm" / t["file"].replace("pcrs5cm", "contraste"),
                                       quality=90)
        p, rd = paint[sl], road[sl]
        vals = idx_wear[sl][p]
        stats.append({"tuile": t["file"], "l93_bbox": t["l93_bbox"],
                      "part_chaussee": round(float(rd.mean()), 3),
                      "part_peinte_sur_chaussee": round(float(p.sum() / max(rd.sum(), 1)), 4),
                      "indice_contraste_median": round(float(np.median(vals)), 3) if vals.size else None,
                      "indice_contraste_p25": round(float(np.percentile(vals, 25)), 3) if vals.size else None})
    (out / "contraste_par_tuile.json").write_text(json.dumps(
        {"reference_neuf_tophat_p95": ref, "seuil_tophat": T_PAINT, "element_structurant_m": SE_M,
         "filtre_taches_m2": MAX_BLOB_M2,
         "tuiles": stats}, indent=1))

    # indice par objet de marquage levé (GAM), si disponible
    gam = DATA / "sites" / a.site / "vector" / "gam_topo_sol_signalisation_horizontale_lin.geojson"
    if gam.exists():
        feats = []
        for ft in json.loads(gam.read_text())["features"]:
            g = to_l93_geom(shape(ft["geometry"]))
            if g.is_empty or not g.intersects(box(*bbox)):
                continue
            zone = g.buffer(0.12)   # ±12 cm autour du trait levé
            mk = np.zeros(L.shape, np.uint8)
            for poly in getattr(zone, "geoms", [zone]):
                pts = np.array([[(x - x0) / RES, (y1 - y) / RES] for x, y in poly.exterior.coords],
                               np.int32)
                cv2.fillPoly(mk, [pts], 1)
            sel = mk.astype(bool)
            n = int(sel.sum())
            if n < 10:
                continue
            cover = float((sel & paint).sum() / n)
            vals = idx_wear[sel & paint]
            gw = transform(lambda x, y, z=None: to_wgs84(x, y), g)
            feats.append({"type": "Feature", "geometry": mapping(gw), "properties": {
                **{k: ft["properties"].get(k) for k in ("calque", "fichier", "couleur_objet")},
                "longueur_m": round(g.length, 2),
                "couverture_peinture": round(cover, 3),
                "indice_contraste": round(float(np.median(vals)), 3) if vals.size else 0.0}})
        (out / "contraste_marquages_gam.geojson").write_text(json.dumps(
            {"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
        print(len(feats), "objets de marquage GAM évalués")
    print("référence neuf (top-hat p95) =", ref, "; tuiles :", len(stats))


if __name__ == "__main__":
    main()
