#!/usr/bin/env python3
"""Atelier « Surfaces au sol, état octobre 2026 » — carrefour Paquet Jardin (Meylan).

Produit un pavage SANS TROU NI CHEVAUCHEMENT de l'emprise de 300 m du site en polygones
classés (classes de recon/CONVENTIONS.md), dans l'état d'octobre 2026 (après les travaux C1
de 2025), avec les attributs classe, materiau, hauteur_bordure_m, source, etat.

Exécution (depuis la racine du dépôt) :  python3 recon/stages/surfaces.py [--cache DIR] [--no-qa]
Sorties : recon/out/paquet_jardin/surfaces/
  surfaces_2026.geojson        pavage classé (Lambert-93, EPSG:2154)
  surfaces_2026_stats.json     comptes / surfaces par classe, contrôles du pavage
  lignes_structurantes.geojson lignes utilisées comme limites (source de chaque ligne)
  qa/qa_<X>_<Y>.jpg            rendus 1000x1000 à 5 cm sur l'ortho 2022 (49 tuiles de 50 m)
  qa/plan_<X>_<Y>.jpg          rendus sur le plan projet 2025 géoréférencé (cœur)
  qa/o24_<X>_<Y>.jpg           rendus sur l'ortho IGN 2024 (Saules Blancs, construits après 2022)

Méthode « raster de régions » (grille 10 cm, puis vectorisation topologique) :
 1. Lignes de limite : levés GAM (bordures, limites de revêtement, caniveaux, clôtures, bâti,
    végétation ; au cœur postérieurs aux travaux 2025), PCRS vecteur 2019 HORS de la zone des
    travaux 2025 et hors des Saules Blancs (sans doublon des levés GAM), contours des bâtiments
    OSM 2026 / BD TOPO, lignes 2026 imposées (terre-plein central, queue d'îlot Vercors, quais,
    pistes du cœur ; tirées du plan projet géoréférencé et de la spécification etat_actuel.json),
    bord de l'emprise. Fermeture des lacunes (accrochage < 0,3 m, raccord d'extrémités en
    vis-à-vis, prolongement court) ; les lignes sont « brûlées » comme barrières.
 2. Occupation du sol par pixel : bâti (OSM/BD TOPO), végétation (indice de verdure de l'ortho
    5 cm 2022 ; sous les houppiers : intensité LiDAR du sol), sol nu, eau ; ortho 2024 sur les
    Saules Blancs ; aplats du plan projet 2025 dans la zone des travaux.
 3. Régions = composantes connexes de même occupation séparées par les barrières.
 4. Classement fonctionnel des régions revêtues (axes OSM 2026 des voies, pistes, trottoirs,
    parkings, accès ; hauteur LiDAR relative ; voisinage) ; partage par plus proche indice quand
    une région sans bordure mélange plusieurs fonctions.
 5. Géométrie 2026 imposée au cœur (terre-plein central planté et refuge de Verdun SW, îlot en
    goutte d'eau du Vercors, quais bus déplacés, suppression de la bretelle et de la voie bus SE,
    suppression de la contre-allée NW, noue et massifs).
 6. Lissage modal, suppression des éclats, vectorisation (arcs partagés simplifiés puis
    re-polygonisés : pavage exact), fusion par attributs, contrôle du pavage, rendus QA.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import rasterio
import shapely
from PIL import Image, ImageDraw, ImageFont
from rasterio import features
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.ops import linemerge, nearest_points, polygonize, unary_union
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common_recon import (BBOX, O, OUT, PLAN, REPO, RES, SITE_DATA, TILE,  # noqa: E402
                          l93_to_uv, load_site_vector, ortho_tile, read_layer, uv_to_l93,
                          write_layer)

OUTD = OUT / "surfaces"
QAD = OUTD / "qa"
GR = 0.10                                   # résolution de la grille de travail (m)
X0, Y0, X1, Y1 = BBOX
NG = int(round((X1 - X0) / GR))             # 3000
GT = from_origin(X0, Y1, GR, GR)
EMPRISE = box(*BBOX)
LIDAR = REPO / "data" / "raw" / "lidar" / "paquet_jardin"
O24 = REPO / "data" / "raw" / "ortho" / "paquet_jardin" / "ORTHOIMAGERY_ORTHOPHOTOS2024_20cm"

# --- classes (recon/CONVENTIONS.md) -------------------------------------------------------
CLASSES = ["autre", "chaussee", "piste_cyclable", "trottoir", "ilot", "terre_plein_vegetal",
           "espace_vert", "quai_bus", "parking", "acces_riverain", "chantier", "batiment"]
K = {c: i for i, c in enumerate(CLASSES)}
COLORS = {"chaussee": (70, 70, 255), "piste_cyclable": (0, 210, 255), "trottoir": (255, 165, 0),
          "ilot": (255, 0, 200), "terre_plein_vegetal": (0, 120, 0), "espace_vert": (120, 255, 60),
          "quai_bus": (255, 255, 0), "parking": (170, 80, 255), "acces_riverain": (255, 90, 90),
          "chantier": (255, 255, 255), "batiment": (200, 20, 20), "autre": (140, 140, 140)}

# occupation du sol (raster G)
G_PAV, G_VEG, G_NU, G_EAU, G_BAT = 1, 2, 3, 4, 5
# codes du raster « plan projet »
P_NONE, P_MASK, P_PHOTO, P_GREY, P_GLIGHT, P_GDARK, P_YGREEN, P_NOUE = range(8)


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# =========================================================================================
# Outils géométriques
# =========================================================================================
def explode_lines(g):
    """Géométrie quelconque -> liste de LineString 2D."""
    if g is None or g.is_empty:
        return []
    g = shapely.force_2d(g)
    t = g.geom_type
    if t == "LineString":
        return [g] if g.length > 0 else []
    if t == "LinearRing":
        return [LineString(g.coords)]
    if t == "Polygon":
        return [LineString(g.exterior.coords)] + [LineString(r.coords) for r in g.interiors]
    if hasattr(g, "geoms"):
        out = []
        for x in g.geoms:
            out += explode_lines(x)
        return out
    return []


def polys_of(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    if hasattr(g, "geoms"):
        out = []
        for x in g.geoms:
            out += polys_of(x)
        return out
    return []


def uv_poly(pts_uv):
    return Polygon([uv_to_l93(u, v) for u, v in pts_uv])


def uv_line(pts_uv):
    return LineString([uv_to_l93(u, v) for u, v in pts_uv])


def uv_band(u0, u1, v0_a, v1_a, v0_b=None, v1_b=None, n=2):
    """Quadrilatère (u0..u1) x (v0..v1) en repère d'axe, bords éventuellement inclinés."""
    v0_b = v0_a if v0_b is None else v0_b
    v1_b = v1_a if v1_b is None else v1_b
    return uv_poly([(u0, v0_a), (u1, v0_b), (u1, v1_b), (u0, v1_a)])


def rasterize(geoms, value=1, all_touched=False, out=None, dtype=np.uint8):
    shp = [(g, value) for g in geoms if g is not None and not g.is_empty]
    if out is None:
        out = np.zeros((NG, NG), dtype)
    if shp:
        features.rasterize(shp, out=out, transform=GT, all_touched=all_touched)
    return out


def mask_of(geoms, all_touched=False):
    return rasterize(geoms, 1, all_touched).astype(bool)


def px_xy(r, c):
    return X0 + (c + 0.5) * GR, Y1 - (r + 0.5) * GR


# =========================================================================================
# 1. Rasters d'indices
# =========================================================================================
def mosaic_ortho2022():
    """Ortho PCRS 5 cm 2022 ramenée à 10 cm sur la grille (NG x NG x 3)."""
    img = np.zeros((NG, NG, 3), np.uint8)
    for tx in range(int(np.floor(X0 / 50) * 50), int(X1), 50):
        for ty in range(int(np.floor(Y0 / 50) * 50), int(Y1), 50):
            t = np.asarray(ortho_tile(tx, ty)).astype(np.float32)
            src_t = from_origin(tx, ty + 50, 0.05, 0.05)
            for k in range(3):
                band = np.zeros((NG, NG), np.float32)
                reproject(t[..., k], band, src_transform=src_t, src_crs="EPSG:2154",
                          dst_transform=GT, dst_crs="EPSG:2154", resampling=Resampling.average,
                          src_nodata=-1, dst_nodata=-1, init_dest_nodata=False)
                m = band > 0
                img[..., k][m] = np.clip(band[m], 0, 255).astype(np.uint8)
    return img


def mosaic_ortho2024():
    """Ortho IGN 20 cm 2024 rééchantillonnée à 10 cm (bilinéaire)."""
    img = np.zeros((NG, NG, 3), np.uint8)
    for f in sorted(O24.glob("*.jpg")):
        a, d, b, e, c, fy = map(float, f.with_suffix(".jgw").read_text().split())
        src = np.asarray(Image.open(f).convert("RGB"))
        tr = rasterio.Affine(a, b, c - a / 2, d, e, fy - e / 2)
        for k in range(3):
            band = np.zeros((NG, NG), np.uint8)
            reproject(src[..., k], band, src_transform=tr, src_crs="EPSG:2154", dst_transform=GT,
                      dst_crs="EPSG:2154", resampling=Resampling.bilinear)
            m = band > 0
            img[..., k][m] = band[m]
    return img


def raster_lidar(name, rs=Resampling.bilinear):
    a = np.full((NG, NG), np.nan, np.float32)
    with rasterio.open(LIDAR / f"{name}.tif") as r:
        reproject(rasterio.band(r, 1), a, dst_transform=GT, dst_crs="EPSG:2154",
                  resampling=rs, src_nodata=np.nan, dst_nodata=np.nan)
    return a


def raster_mnh():
    """Modèle numérique de hauteur IGN LiDAR HD 50 cm (sursol : arbres, bâti), 2021."""
    a = np.full((NG, NG), np.nan, np.float32)
    for f in sorted((REPO / "data" / "raw" / "lidar" / "mnh").glob("*.tif")):
        with rasterio.open(f) as r:
            b = r.bounds
            if b.right < X0 or b.left > X1 or b.top < Y0 or b.bottom > Y1:
                continue
            t = np.full((NG, NG), np.nan, np.float32)
            reproject(rasterio.band(r, 1), t, dst_transform=GT, dst_crs="EPSG:2154",
                      resampling=Resampling.bilinear, src_nodata=r.nodata, dst_nodata=np.nan)
            m = ~np.isnan(t)
            a[m] = t[m]
    return np.nan_to_num(a, nan=0.0)


def nconv(a, size):
    """Moyenne glissante normalisée d'un raster creux (NaN = pas de mesure)."""
    m = ~np.isnan(a)
    num = ndi.uniform_filter(np.where(m, a, 0).astype(np.float32), size)
    den = ndi.uniform_filter(m.astype(np.float32), size)
    return num / np.maximum(den, 1e-6), den


def plan_rgb():
    rgb = np.zeros((3, NG, NG), np.uint8)
    inside = np.zeros((NG, NG), np.uint8)
    with rasterio.open(PLAN) as r:
        for b in range(3):
            reproject(rasterio.band(r, b + 1), rgb[b], dst_transform=GT, dst_crs="EPSG:2154",
                      resampling=Resampling.nearest)
        ones = np.ones((r.height, r.width), np.uint8)
        reproject(ones, inside, src_transform=r.transform, src_crs=r.crs, dst_transform=GT,
                  dst_crs="EPSG:2154", resampling=Resampling.nearest)
    return np.transpose(rgb, (1, 2, 0)), inside.astype(bool)


def plan_class_raster(rgb, inside):
    """Classe des aplats du plan projet 2025 (géoréférencé) sur la grille 10 cm."""
    im = rgb.astype(np.int16)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    mx, mn = im.max(2), im.min(2)
    val = im.mean(2)
    loc_std = np.sqrt(np.maximum(ndi.uniform_filter(val ** 2, 5) - ndi.uniform_filter(val, 5) ** 2, 0))
    grey = (mx - mn <= 6) & (mn >= 208) & (mx <= 232) & (loc_std < 3.0)
    glight = (R >= 140) & (R <= 180) & (G >= 240) & (B >= 95) & (B <= 140)
    gdark = (R <= 40) & (G >= 160) & (G <= 210) & (B <= 40)
    ygreen = (R >= 140) & (R <= 180) & (G >= 240) & (B <= 40)
    noue = (R >= 195) & (R <= 235) & (G >= 240) & (B >= 95) & (B <= 160)
    black = mx < 25
    white = mn >= 248
    pc = np.full((NG, NG), P_PHOTO, np.uint8)
    for code, m in ((P_GREY, grey), (P_GLIGHT, glight), (P_GDARK, gdark), (P_YGREEN, ygreen),
                    (P_NOUE, noue)):
        pc[m] = code
    for m in (black, white):            # masques « hors projet » : grandes plages uniformes
        lab, n = ndi.label(m)
        if n:
            sz = ndi.sum(m, lab, index=np.arange(1, n + 1))
            big = np.zeros(n + 1, bool)
            big[1:] = sz > 400
            pc[big[lab]] = P_MASK
    pc[~inside] = P_NONE
    # aplats : fermeture pour effacer textes, symboles, traits fins dessinés par-dessus
    out = pc.copy()
    for code in (P_GREY, P_GLIGHT, P_GDARK, P_YGREEN, P_NOUE):
        m = ndi.binary_closing(pc == code, structure=np.ones((3, 3)), iterations=3)
        m = ndi.binary_opening(m, iterations=1)
        out[m & (pc != P_MASK) & (pc != P_NONE)] = code
    return out


def load_rasters(cache: Path | None):
    """Rasters de travail (10 cm), avec cache optionnel (développement)."""
    names = ["o22", "o24", "ig", "mnh", "dtm", "plan", "pin", "pcls"]
    if cache and all((cache / f"{n}.npy").exists() for n in names):
        log("rasters : cache", cache)
        return {n: np.load(cache / f"{n}.npy") for n in names}
    log("rasters : ortho 2022")
    d = {"o22": mosaic_ortho2022()}
    log("rasters : ortho 2024")
    d["o24"] = mosaic_ortho2024()
    log("rasters : LiDAR")
    d["ig"] = raster_lidar("intensity_ground_15cm", Resampling.bilinear)
    d["dtm"] = raster_lidar("dtm_15cm", Resampling.bilinear)
    d["mnh"] = raster_mnh()
    log("rasters : plan projet")
    d["plan"], d["pin"] = plan_rgb()
    d["pcls"] = plan_class_raster(d["plan"], d["pin"])
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        for n in names:
            np.save(cache / f"{n}.npy", d[n])
    return d


# =========================================================================================
# 2. Zones et couches vectorielles
# =========================================================================================
def zone_travaux():
    """Zone des travaux C1 2025 (géométrie changée ; PCRS 2019 exclu, levés GAM font foi)."""
    sw = uv_poly([(-121, -26), (-121, 17.5), (-8, 17.5), (-8, -26)])
    centre = Point(uv_to_l93(0, -2)).buffer(36)
    # avenue du Vercors (phase 2 : trottoirs, végétalisation, îlot) jusqu'au bord S de l'emprise
    verc = load_site_vector("osm_roads")
    axes = [g for g, p in verc if p.get("name") == "Avenue du Vercors"]
    vc = unary_union(axes).buffer(16) if axes else Polygon()
    return unary_union([sw, centre, vc]).intersection(EMPRISE)


def zone_saules_blancs():
    """Domaine des Saules Blancs (chantier sur l'ortho 2022, construit sur l'ortho 2024)."""
    return Polygon([(917300.0, 6460272.0), uv_to_l93(5.0, -12.5), (917429.43, 6460422.3),
                    (917429.43, 6460139.98), (917312.0, 6460139.98), (917310.0, 6460200.0),
                    (917306.0, 6460235.0)]).intersection(EMPRISE)


def load_gam(name):
    """Couche GAM etat_2026 (L93) -> lignes 2D."""
    p = SITE_DATA / "etat_2026" / f"{name}_L93.geojson"
    if p.exists():
        return [l for g, _ in read_layer(p) for l in explode_lines(g)]
    return [l for g, _ in load_site_vector(f"gam_topo_sol_{name}") for l in explode_lines(g)]


def dedupe(lines, ref_lines, tol, min_len):
    """Parties de `lines` à plus de `tol` de toute ligne de référence (évite les doublons)."""
    if not ref_lines:
        return lines
    ref = unary_union(ref_lines).buffer(tol, cap_style="flat")
    out = []
    for l in lines:
        d = l.difference(ref)
        out += [x for x in explode_lines(d) if x.length >= min_len]
    return out


def load_vectors():
    v = {}
    v["gam_bord"] = load_gam("bordure_lin")
    v["gam_lim"] = load_gam("limite_revetement_lin")
    v["gam_can"] = load_gam("caniveau_lin")
    v["gam_clo"] = load_gam("clotures_lin")
    v["gam_bat"] = load_gam("batiment_lin")
    v["gam_veg"] = load_gam("vegetation_lin")
    v["pcrs"] = []
    for n in ("gam_limite_voirie_pcrs", "gam_changement_revetements_pcrs", "gam_accotement_pcrs",
              "gam_mur_pcrs"):
        v["pcrs"] += [(l, n) for g, p in load_site_vector(n) for l in explode_lines(g)]
    v["chartieres"] = [g for g, p in read_layer(SITE_DATA / "etat_2026" / "bordure_pct_L93.geojson")
                       if p.get("bloc")]
    # bâtiments : OSM 2026 (prioritaire) + BD TOPO (compléments)
    osmb = [g for g, p in load_site_vector("osm_buildings") if g.geom_type in ("Polygon", "MultiPolygon")]
    bdt = [g for g, p in load_site_vector("bdtopo_batiment") if g.geom_type in ("Polygon", "MultiPolygon")]
    osmu = unary_union(osmb) if osmb else Polygon()
    add = []
    for g in bdt:
        g = shapely.force_2d(g).buffer(0)
        if g.intersection(osmu).area < 0.3 * g.area:
            add.append(g)
    v["bat"] = [shapely.force_2d(g).buffer(0) for g in osmb] + add
    v["roads"] = load_site_vector("osm_roads")
    v["cyc"] = load_site_vector("osm_cycleways")
    v["foot"] = load_site_vector("osm_footways")
    v["park"] = [(g, p) for g, p in load_site_vector("osm_parking") if g.geom_type == "Polygon"]
    v["pt"] = load_site_vector("osm_public_transport")
    v["landuse"] = load_site_vector("osm_landuse")
    v["hydro"] = [g for g, p in load_site_vector("bdtopo_surface_hydrographique")]
    v["arbres"] = [g for g, p in read_layer(SITE_DATA / "etat_2026" / "arbre_pct_L93.geojson")]
    return v


# =========================================================================================
# 3. Occupation du sol par pixel (G) : revêtu / végétal / sol nu / eau / bâti
# =========================================================================================
def exg_of(rgb):
    o = rgb.astype(np.float32)
    R, G, B = o[..., 0], o[..., 1], o[..., 2]
    return (2 * G - R - B) / (R + G + B + 1.0), (R + G + B) / 3.0


def ground_cover(d, v, zt, ze):
    """Raster G (uint8) + masques utiles."""
    bat = mask_of(v["bat"])
    in_ze = mask_of([ze])
    exg22, br22 = exg_of(d["o22"])
    exg24, br24 = exg_of(d["o24"])
    exg = np.where(in_ze, exg24, exg22)
    br = np.where(in_ze, br24, br22)
    rgb = np.where(in_ze[..., None], d["o24"], d["o22"]).astype(np.float32)
    exg5 = ndi.uniform_filter(exg, 5)
    br5 = ndi.uniform_filter(br, 5)
    # houppiers (MNH 2021 > 2 m hors bâti) : le sol est jugé sur l'intensité LiDAR du sol
    canopy = (ndi.uniform_filter(d["mnh"], 3) > 2.0) & ~bat & ~in_ze
    igs, igc = nconv(d["ig"], 9)
    veg_open = exg5 > 0.075
    veg_under = (igs > 45500) & (igc > 0.03)
    paved_under = (igs < 43000) & (igc > 0.03)
    # sous houppier ou dans l'ombre portée, la verdure de l'ortho n'est pas fiable
    shadow = (br5 < 78) & ~in_ze
    unsure = canopy | shadow
    veg = np.where(unsure, np.where(veg_under, True, np.where(paved_under, False, veg_open)), veg_open)
    # au soleil : herbe claire très réfléchissante en proche IR même si peu verte (pelouse sèche)
    veg |= (~unsure) & (~in_ze) & (igs > 48500) & (igc > 0.03) & (exg5 > 0.02)
    # sol nu (terre, sable, gravier clair) : beige/brun, peu vert, saturé
    R, G_, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    sat = (np.maximum(np.maximum(R, G_), B) - np.minimum(np.minimum(R, G_), B)) / (np.maximum(np.maximum(R, G_), B) + 1)
    sat5 = ndi.uniform_filter(sat, 7)
    nu = (~veg) & (ndi.uniform_filter(R - B, 7) > 22) & (sat5 > 0.14) & (br5 > 95) & (exg5 < 0.05)
    G = np.full((NG, NG), G_PAV, np.uint8)
    G[veg] = G_VEG
    G[nu] = G_NU
    # plan projet (zone des travaux) : les aplats dessinés priment
    pc = d["pcls"]
    in_plan = mask_of([zt]) & np.isin(pc, (P_GREY, P_GLIGHT, P_GDARK, P_YGREEN, P_NOUE))
    G[in_plan & (pc == P_GREY)] = G_PAV
    G[in_plan & (pc != P_GREY)] = G_VEG
    # eau (bassin d'orage BD TOPO)
    G[mask_of(v["hydro"])] = G_EAU
    G[bat] = G_BAT
    return G, dict(bat=bat, canopy=canopy, in_ze=in_ze, exg=exg5, br=br5, in_plan=in_plan)


def modal_smooth(G, size=5, keep=None):
    """Filtre majoritaire (classes entières petites)."""
    vals = np.unique(G)
    best = np.zeros(G.shape, np.float32) - 1
    out = G.copy()
    for c in vals:
        f = ndi.uniform_filter((G == c).astype(np.float32), size)
        m = f > best
        out[m] = c
        best[m] = f[m]
    if keep is not None:
        out[keep] = G[keep]
    return out


# =========================================================================================
# 4. Lignes de limite (barrières) et faces
# =========================================================================================
def end_dir(line, at_start, back=0.8):
    L = line.length
    if at_start:
        p = np.array(line.coords[0]); q = np.array(line.interpolate(min(back, L)).coords[0])
    else:
        p = np.array(line.coords[-1]); q = np.array(line.interpolate(max(L - back, 0)).coords[0])
    d = p - q
    n = np.linalg.norm(d)
    return p, (d / n if n > 1e-9 else np.zeros(2))


def close_gaps(lines, snap=0.3, pair_max=6.0, ext_max=2.5, cos_pair=np.cos(np.radians(25))):
    """Fermeture des lacunes du réseau de lignes : renvoie la liste des connecteurs."""
    segs = explode_lines(unary_union(lines))
    kk = lambda c: (round(c[0], 3), round(c[1], 3))
    deg = defaultdict(int)
    for s in segs:
        deg[kk(s.coords[0])] += 1
        deg[kk(s.coords[-1])] += 1
    dang = []
    for i, s in enumerate(segs):
        if s.length < 0.05:
            continue
        for st in (True, False):
            c = s.coords[0] if st else s.coords[-1]
            if deg[kk(c)] == 1:
                p, d = end_dir(s, st)
                dang.append((i, p, d))
    tree = STRtree(segs)
    conns, done = [], set()
    # (a) accrochage < snap
    for j, (i, p, d) in enumerate(dang):
        P = Point(p)
        best = None
        for c in tree.query(P.buffer(snap)):
            if c == i:
                continue
            dd = segs[c].distance(P)
            if dd < snap and (best is None or dd < best[0]):
                best = (dd, c)
        if best:
            q = nearest_points(segs[best[1]], P)[0]
            if best[0] > 1e-6:
                conns.append(LineString([p, q.coords[0]]))
            done.add(j)
    # (b) raccord de deux extrémités en vis-à-vis (continuité de bordure interrompue)
    if dang:
        kd = cKDTree(np.array([p for _, p, _ in dang]))
        best_partner = {}
        for j, (i, p, d) in enumerate(dang):
            if j in done:
                continue
            for m in kd.query_ball_point(p, pair_max):
                if m == j or m in done or dang[m][0] == i:
                    continue
                vv = dang[m][1] - p
                n = np.linalg.norm(vv)
                if n < 1e-6:
                    continue
                vv = vv / n
                a1, a2 = np.dot(d, vv), np.dot(dang[m][2], -vv)
                if a1 > cos_pair and a2 > cos_pair:
                    score = n * (2.2 - a1 - a2)
                    if j not in best_partner or score < best_partner[j][0]:
                        best_partner[j] = (score, m)
        for j, (sc, m) in best_partner.items():
            if j in done or m in done:
                continue
            if best_partner.get(m, (None, None))[1] == j:
                seg = LineString([dang[j][1], dang[m][1]])
                if not any(segs[c].crosses(seg) for c in tree.query(seg)):
                    conns.append(seg)
                    done.update((j, m))
    # (c) prolongement court dans l'axe
    for j, (i, p, d) in enumerate(dang):
        if j in done:
            continue
        ray = LineString([p + d * 0.01, p + d * ext_max])
        best = None
        for c in tree.query(ray):
            if c == i:
                continue
            it = segs[c].intersection(ray)
            if it.is_empty:
                continue
            dd = Point(p).distance(it)
            if best is None or dd < best[0]:
                best = (dd, nearest_points(it, Point(p))[0])
        if best:
            conns.append(LineString([p, best[1].coords[0]]))
            done.add(j)
    return conns, len(dang), len(done)


def structure_lines(v, zt, ze, imposed):
    """Lignes de limite (geom, source) et connecteurs de fermeture."""
    out = []
    excl = unary_union([zt, ze])
    gam = v["gam_bord"] + v["gam_lim"] + v["gam_can"]
    # au cœur (zone des travaux) les lignes GAM de l'état ancien encore présentes dans le levé
    # et contredites par les lignes imposées 2026 sont retirées (liste imposed["retirer"])
    rm = unary_union(imposed.get("retirer", [])) if imposed.get("retirer") else None
    def keep(l):
        if rm is None:
            return [l]
        return [x for x in explode_lines(l.difference(rm)) if x.length > 0.2]
    for l in v["gam_bord"]:
        out += [(x, "gam_bordure") for x in keep(l)]
    for l in v["gam_lim"]:
        out += [(x, "gam_limite_revetement") for x in keep(l)]
    for l in v["gam_can"]:
        out += [(x, "gam_caniveau") for x in keep(l)]
    for l in v["gam_clo"]:
        out += [(x, "gam_cloture") for x in keep(l)]
    for l in v["gam_bat"]:
        out += [(x, "gam_batiment") for x in keep(l)]
    for l in v["gam_veg"]:
        out += [(x, "gam_vegetation") for x in keep(l)]
    # PCRS 2019 : hors zone des travaux et hors Saules Blancs, sans doublon des levés GAM
    pc = []
    for l, n in v["pcrs"]:
        d = l.difference(excl)
        pc += [(x, n) for x in explode_lines(d) if x.length > 0.3]
    ded = dedupe([x for x, _ in pc], gam + v["gam_clo"] + v["gam_bat"], 0.45, 0.6)
    out += [(x, "pcrs_2019") for x in ded]
    # bâtiments (OSM 2026 / BD TOPO)
    for g in v["bat"]:
        out += [(x, "osm_bdtopo_batiment") for x in explode_lines(g)]
    # lignes 2026 imposées (cœur)
    for l, src in imposed.get("lignes", []):
        out += [(x, src) for x in explode_lines(l)]
    out += [(LineString(EMPRISE.exterior.coords), "emprise")]
    lines = [l for l, _ in out]
    conns, nd, nf = close_gaps(lines)
    log(f"lignes : {len(out)}, extrémités pendantes {nd}, fermées {nf}, connecteurs {len(conns)}")
    out += [(c, "fermeture") for c in conns]
    return out


def faces_raster(lines):
    """Faces = composantes 4-connexes des pixels hors lignes (lignes brûlées 8-connexes)."""
    bar = mask_of([l.buffer(0.001) if l.length < 1e-6 else l for l, _ in lines], all_touched=True)
    lab, n = ndi.label(~bar, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    return lab, n, bar


# =========================================================================================
# 5. Classement fonctionnel par propagation contrainte
# =========================================================================================
PUBLIC = ("primary", "secondary", "tertiary", "residential", "unclassified", "living_street")


def road_halfwidth(p):
    """Demi-largeur de chaussée (m) d'après les attributs OSM 2026."""
    hw = p.get("highway")
    try:
        w = float(str(p.get("width")).replace(",", "."))
    except (TypeError, ValueError):
        w = None
    try:
        n = int(p.get("lanes"))
    except (TypeError, ValueError):
        n = None
    oneway = p.get("oneway") == "yes"
    if hw == "primary":
        return 3.2 * (n or 2) / 2
    if w:
        return w / 2
    if hw == "tertiary":
        return 3.0 * (n or 2) / 2 if oneway else 3.0
    if hw == "residential":
        return (3.5 * (n or 1) / 2) if oneway else 3.0
    if hw == "living_street":
        return 2.6
    return 2.5


def flood(seed, allowed):
    """Propagation 4-connexe des germes dans `allowed` (composantes connexes touchées)."""
    s = seed & allowed
    if not s.any():
        return s
    lab, n = ndi.label(allowed, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    keep = np.zeros(n + 1, bool)
    keep[np.unique(lab[s])] = True
    keep[0] = False
    return keep[lab]


def edt_to(mask):
    """Distance euclidienne (m) au masque."""
    if not mask.any():
        return np.full(mask.shape, 1e9, np.float32)
    return (ndi.distance_transform_edt(~mask) * GR).astype(np.float32)


def window(g, margin):
    """Fenêtre (r0, r1, c0, c1) de la grille couvrant g élargie de margin (m)."""
    x0, y0, x1, y1 = g.bounds
    c0 = max(int((x0 - margin - X0) / GR) - 1, 0)
    c1 = min(int((x1 + margin - X0) / GR) + 2, NG)
    r0 = max(int((Y1 - y1 - margin) / GR) - 1, 0)
    r1 = min(int((Y1 - y0 + margin) / GR) + 2, NG)
    return r0, r1, c0, c1


def axis_flood(g, cap, allowed_fn, all_touched=True):
    """Propagation depuis l'axe g, limitée à la distance cap (m), dans une fenêtre locale.
    allowed_fn(sl, dist) -> masque autorisé (sl = tranche de fenêtre)."""
    r0, r1, c0, c1 = window(g, cap + 1)
    sl = (slice(r0, r1), slice(c0, c1))
    tr = from_origin(X0 + c0 * GR, Y1 - r0 * GR, GR, GR)
    ax = np.zeros((r1 - r0, c1 - c0), np.uint8)
    features.rasterize([(g, 1)], out=ax, transform=tr, all_touched=all_touched)
    ax = ax.astype(bool)
    if not ax.any():
        return None, sl
    dist = (ndi.distance_transform_edt(~ax) * GR).astype(np.float32)
    allowed = allowed_fn(sl, dist) & (dist <= cap)
    return flood(ax, allowed), sl


def assign_classes(d, v, lines, G, aux, imposed):
    """Raster de classes C (uint8, codes K) avant imposition 2026 et nettoyage."""
    curb_src = {"gam_bordure", "gam_caniveau", "gam_cloture", "gam_batiment", "pcrs_2019",
                "osm_bdtopo_batiment", "emprise", "impose_bordure", "fermeture"}
    bar_curb = mask_of([l for l, s in lines if s in curb_src], all_touched=True)
    bar_all = mask_of([l for l, s in lines], all_touched=True)
    paved = (G == G_PAV) | (G == G_NU)
    notbat = G != G_BAT
    canopy = aux["canopy"]
    C = np.full((NG, NG), 255, np.uint8)          # 255 = non attribué
    nonch = mask_of([g for g, cl, src in imposed.get("polys", [])]) if imposed.get("polys") else None
    # --- chaussée : depuis les axes des voies publiques, arrêtée par les bordures -----------
    ch = np.zeros((NG, NG), bool)
    for g, p in v["roads"]:
        if p.get("highway") not in PUBLIC:
            continue
        hw = road_halfwidth(p)
        cap = hw + (3.0 if p.get("highway") in ("primary", "tertiary") else 1.6)
        corew = max(hw - 0.6, 1.0)
        def alw(sl, dist, corew=corew):
            return notbat[sl] & ~bar_curb[sl] & (paved[sl] | (dist <= corew) | canopy[sl])
        m, sl = axis_flood(g, cap, alw)
        if m is not None:
            ch[sl] |= m
    if nonch is not None:
        ch &= ~nonch
    C[ch] = K["chaussee"]
    free = (C == 255)
    # --- piste cyclable ------------------------------------------------------------------------
    cyc = [(g, p) for g, p in v["cyc"] if p.get("osm_id") not in imposed.get("cyc_ignores", ())]
    cyc += [(g, {"width": w}) for g, w in imposed.get("axes_piste", [])]
    for g, p in cyc:
        try:
            w = float(p.get("width") or p.get("cycleway:width") or 3)
        except ValueError:
            w = 3.0
        def alw(sl, dist, w=w):
            return free[sl] & notbat[sl] & ~bar_all[sl] & (paved[sl] | (dist <= w / 2 - 0.3))
        m, sl = axis_flood(g, w / 2 + 0.6, alw)
        if m is not None:
            C[sl][m] = K["piste_cyclable"]
    free = (C == 255)
    # --- parkings : polygones OSM (surface / street_side) + allées ------------------------------
    pk = np.zeros((NG, NG), bool)
    for g, p in v["park"]:
        if p.get("parking") in ("multi-storey", "underground"):
            continue
        pk |= mask_of([g])
    for g, p in v["roads"]:
        if p.get("highway") == "service" and p.get("service") == "parking_aisle":
            m, sl = axis_flood(g, 3.2, lambda sl, dist: free[sl] & notbat[sl] & ~bar_curb[sl] & paved[sl])
            if m is not None:
                pk[sl] |= m
    pk &= free & paved
    C[pk] = K["parking"]
    free = (C == 255)
    # --- accès riverains (voies de service hors allées de parking) -----------------------------
    for g, p in v["roads"]:
        if p.get("highway") == "service" and p.get("service") != "parking_aisle":
            m, sl = axis_flood(g, 2.8, lambda sl, dist: free[sl] & notbat[sl] & ~bar_curb[sl]
                               & (paved[sl] | (dist < 1.5)))
            if m is not None:
                C[sl][m] = K["acces_riverain"]
    free = (C == 255)
    # --- quai bus (OSM : quai de la ligne 42 sur la Revirée ; Verdun : imposés) ---------------
    for g, p in v["pt"]:
        if g.geom_type == "LineString" and p.get("public_transport") == "platform":
            if p.get("osm_id") in imposed.get("quais_osm_ignores", ()):
                continue
            m, sl = axis_flood(g, 1.6, lambda sl, dist: free[sl] & paved[sl] & ~bar_all[sl])
            if m is not None:
                C[sl][m] = K["quai_bus"]
    free = (C == 255)
    # --- trottoirs : chemins OSM + bande revêtue derrière une bordure de chaussée --------------
    fw = np.zeros((NG, NG), bool)
    for g, p in v["foot"]:
        if p.get("highway") not in ("footway", "path", "steps", "pedestrian"):
            continue
        if p.get("footway") == "crossing":
            continue
        m, sl = axis_flood(g, 2.0, lambda sl, dist: free[sl] & paved[sl] & ~bar_all[sl])
        if m is not None:
            fw[sl] |= m
    near_ch = edt_to(C == K["chaussee"])
    behind = free & paved & (near_ch <= 0.35) & ~bar_all
    tr = flood(fw | behind, free & paved & ~bar_all & (near_ch <= 7.0)) | fw
    C[tr] = K["trottoir"]
    free = (C == 255)
    # --- végétal, sol nu, eau, bâti -----------------------------------------------------------
    C[free & (G == G_VEG)] = K["espace_vert"]
    C[G == G_BAT] = K["batiment"]
    C[free & (G == G_EAU)] = K["autre"]
    # --- îlots : trous de la chaussée -----------------------------------------------------------
    holes = ndi.binary_fill_holes(C == K["chaussee"]) & (C != K["chaussee"])
    lab, n = ndi.label(holes)
    if n:
        idx = np.arange(1, n + 1)
        sz = ndi.sum(np.ones(lab.shape), lab, index=idx) * GR * GR
        vegf = ndi.mean((G == G_VEG).astype(float), lab, index=idx)
        small = np.zeros(n + 1, bool)
        small[1:] = sz <= 600
        isveg = np.zeros(n + 1, bool)
        isveg[1:] = vegf > 0.6
        m = small[lab] & (C != K["batiment"])
        C[m & isveg[lab]] = K["terre_plein_vegetal"]
        C[m & ~isveg[lab]] = K["ilot"]
    free = (C == 255)
    # --- revêtu restant : classe voisine (<= 3 m) sinon « autre » -------------------------------
    rest = free & paved
    assigned = np.isin(C, [K[c] for c in ("trottoir", "parking", "acces_riverain",
                                         "piste_cyclable", "quai_bus")])
    if rest.any() and assigned.any():
        dist, (ri, ci) = ndi.distance_transform_edt(~assigned, return_indices=True)
        near = rest & (dist * GR <= 3.0)
        C[near] = C[ri[near], ci[near]]
    free = (C == 255)
    C[free] = K["autre"]
    # --- géométrie 2026 imposée ------------------------------------------------------------------
    for g, cl, src in imposed.get("polys", []):
        C[mask_of([g])] = K[cl]
    soft_ok = np.isin(C, [K[c] for c in ("trottoir", "autre", "parking", "acces_riverain", "chaussee",
                                         "quai_bus")])
    for g, cl, src in imposed.get("soft", []):
        m = mask_of([g]) & soft_ok & paved
        if cl != "parking":
            m &= C != K["chaussee"]
        C[m] = K[cl]
    return C, bar_curb, bar_all


# =========================================================================================
# 6. Géométrie 2026 imposée au cœur (plan projet géoréférencé + spécification etat_actuel)
# =========================================================================================
def rounded_strip(u0, u1, se0, se1, nw0, nw1, round0=True, round1=True, step=0.5):
    """Bande en repère d'axe (u0..u1), bords SE et NW linéaires en u, extrémités arrondies."""
    def se(u):
        return se0 + (se1 - se0) * (u - u0) / (u1 - u0)
    def nw(u):
        return nw0 + (nw1 - nw0) * (u - u0) / (u1 - u0)
    pts = []
    r0 = (nw(u0) - se(u0)) / 2
    r1 = (nw(u1) - se(u1)) / 2
    a0 = u0 + (r0 if round0 else 0)
    a1 = u1 - (r1 if round1 else 0)
    for u in np.arange(a0, a1 + 1e-6, step):
        pts.append((u, se(u)))
    if round1:
        c = (se(a1) + nw(a1)) / 2
        for t in np.linspace(-np.pi / 2, np.pi / 2, 13)[1:-1]:
            pts.append((a1 + r1 * np.cos(t), c + r1 * np.sin(t)))
    else:
        pts.append((u1, se(u1)))
        pts.append((u1, nw(u1)))
    for u in np.arange(a1, a0 - 1e-6, -step):
        pts.append((u, nw(u)))
    if round0:
        c = (se(a0) + nw(a0)) / 2
        for t in np.linspace(np.pi / 2, 3 * np.pi / 2, 13)[1:-1]:
            pts.append((a0 + r0 * np.cos(t), c + r0 * np.sin(t)))
    else:
        pts.append((u0, nw(u0)))
        pts.append((u0, se(u0)))
    return uv_poly(pts).buffer(0)


def plan_aplat_lines(pcls, zt, ref_lines):
    """Limites des aplats du plan projet (revêtu / planté / reste) dans la zone des travaux,
    là où les levés GAM n'ont pas de ligne (terre-plein, queue d'îlot, massifs, noue)."""
    m = mask_of([zt.buffer(-1.0)])
    code = np.zeros((NG, NG), np.uint8)
    code[(pcls == P_GREY) & m] = 1
    code[np.isin(pcls, (P_GLIGHT, P_GDARK, P_YGREEN, P_NOUE)) & m] = 2
    code = modal_smooth(code, 5)
    polys = []
    for geom, val in features.shapes(code, mask=code > 0, transform=GT, connectivity=4):
        g = shape(geom)
        if g.area >= 1.0:
            polys.append(g.buffer(0.08, join_style="mitre").simplify(0.08))
    lines = []
    for g in polys:
        lines += explode_lines(g)
    lines = [l.intersection(zt.buffer(-1.2)) for l in lines]
    lines = [x for l in lines for x in explode_lines(l)]
    return dedupe(lines, ref_lines, 0.40, 1.0)


def imposed_2026(d, v):
    """Éléments 2026 imposés au cœur : lignes, polygones de classe forcée, axes corrigés."""
    imp = {"lignes": [], "polys": [], "soft": [], "axes_piste": [], "quais_osm_ignores": set(),
           "cyc_ignores": set()}
    # --- terre-plein central planté de Verdun SW (plan projet : aplat vert 2,0 m + bordures) ---
    # bords mesurés sur l'aplat du plan (v SE -4,37 à u -69,5 -> -3,74 à u -29,6 ; v NW -2,50 -> -1,86)
    # + 0,18 m de bordure ; refuge GAM (u -29,6 à -22,3, v -3,9 à -1,5) ; nez planté u -22,3 à -17
    tpc_a = rounded_strip(-69.6, -29.6, -4.55, -3.92, -2.32, -1.62, round0=True, round1=False)
    refuge = uv_band(-29.6, -22.3, -3.90, -1.50)
    nez = rounded_strip(-22.3, -17.0, -3.88, -3.80, -1.42, -1.45, round0=False, round1=True)
    imp["polys"] += [(tpc_a, "terre_plein_vegetal", "plan_projet_2025+etat_actuel"),
                     (nez, "terre_plein_vegetal", "plan_projet_2025+etat_actuel"),
                     (refuge, "ilot", "gam_2026+plan_projet_2025")]
    for g in (tpc_a, refuge, nez):
        imp["lignes"] += [(l, "impose_bordure") for l in explode_lines(g)]
    # --- quais bus déplacés (zigzags GAM ; bordures de quai GAM) : classe forcée sur le revêtu --
    quai_nw = uv_band(-65.6, -34.0, 4.2, 7.45, 4.5, 7.75)
    quai_se = uv_band(-101.7, -71.6, -13.25, -10.3, -13.15, -10.0)
    imp["soft"] += [(quai_nw, "quai_bus", "gam_2026+osm_2026"), (quai_se, "quai_bus", "gam_2026+osm_2026")]
    imp["quais_osm_ignores"] |= {"way/185326913", "way/185326915"}
    # --- encoche autopartage + 2 places PMR (côté NW, u -100 à -80) -------------------------------
    imp["soft"] += [(uv_band(-100.5, -80.5, 3.2, 9.9), "parking", "gam_2026+plan_projet_2025")]
    # --- pistes cyclables du cœur (axes corrigés : OSM 2026 décalé de 1,5 à 2 m au NW,
    #     ancienne traversée à u -15 non mise à jour) -----------------------------------------------
    imp["axes_piste"] += [
        (uv_line([(-125.0, 13.3), (-82.0, 13.2), (-40.0, 13.0), (-33.0, 12.6), (-29.0, 11.6),
                  (-26.0, 11.1), (-15.0, 11.1), (-5.3, 10.6), (0.0, 10.2)]), 3.6),
        # nouvelle piste bidirectionnelle vers le Vercors, dans l'axe de la traversée u -25,9/-22,3
        (uv_line([(-24.0, -10.9), (-24.0, -20.0), (-23.9, -30.0), (-23.8, -38.0), (-23.2, -42.0)]), 3.2),
    ]
    imp["cyc_ignores"] |= {"way/398052317", "way/385035086", "way/698843233", "way/54585242"}
    return imp


# =========================================================================================
# 7. Nettoyage raster, vectorisation topologique
# =========================================================================================
def remove_small(L, min_px, protect=None, max_iter=6):
    """Réaffecte les composantes connexes de moins de min_px pixels à l'étiquette voisine
    majoritaire (itératif)."""
    L = L.copy()
    for it in range(max_iter):
        changed = 0
        for val in np.unique(L):
            m = L == val
            lab, n = ndi.label(m, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
            if n == 0:
                continue
            sz = np.bincount(lab.ravel())
            small = np.where(sz < min_px)[0]
            small = small[small > 0]
            if len(small) == 0:
                continue
            sm = np.isin(lab, small)
            if protect is not None:
                sm &= ~protect
            if not sm.any():
                continue
            # étiquette voisine majoritaire : plus proche pixel hors composante
            lab_s, ns = ndi.label(sm, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
            ring = ndi.binary_dilation(sm, iterations=1) & ~sm
            # pour chaque petite composante, vote des pixels de l'anneau
            lab_ring = ndi.grey_dilation(lab_s, size=3) * ring
            idx = np.nonzero(lab_ring)
            if len(idx[0]) == 0:
                continue
            comp = lab_ring[idx]
            vals = L[idx]
            order = np.lexsort((vals, comp))
            comp, vals = comp[order], vals[order]
            best = {}
            # comptage par (comp, val)
            key = comp.astype(np.int64) * 1000 + vals.astype(np.int64)
            uk, cnt = np.unique(key, return_counts=True)
            for k_, c_ in zip(uk, cnt):
                ci, vi = divmod(int(k_), 1000)
                if ci not in best or c_ > best[ci][1]:
                    best[ci] = (vi, c_)
            newv = np.full(ns + 1, -1, np.int64)
            for ci, (vi, _) in best.items():
                newv[ci] = vi
            tgt = newv[lab_s]
            ok = sm & (tgt >= 0)
            L[ok] = tgt[ok]
            changed += int(ok.sum())
        if changed == 0:
            break
    return L


def chaikin(coords, n=2):
    c = np.asarray(coords, float)
    for _ in range(n):
        if len(c) < 3:
            break
        q = 0.75 * c[:-1] + 0.25 * c[1:]
        r = 0.25 * c[:-1] + 0.75 * c[1:]
        mid = np.empty((2 * len(q), 2))
        mid[0::2] = q
        mid[1::2] = r
        c = np.vstack([c[:1], mid, c[-1:]])
    return c


def vectorize_partition(L, tol=0.09, smooth=True):
    """Raster d'étiquettes -> pavage polygonal exact (arcs partagés simplifiés)."""
    polys = []
    for geom, val in features.shapes(L.astype(np.int32), transform=GT, connectivity=4):
        polys.append(shape(geom))
    log(f"vectorisation : {len(polys)} polygones bruts")
    bnd = shapely.union_all([shapely.boundary(p) for p in polys] + [EMPRISE.boundary])
    arcs = explode_lines(linemerge(bnd)) if bnd.geom_type != "LineString" else [bnd]
    log(f"vectorisation : {len(arcs)} arcs")
    out = []
    for a in arcs:
        s = a.simplify(tol, preserve_topology=False)
        if smooth and len(s.coords) >= 3 and s.length > 1.0:
            c = chaikin(s.coords, 2)
            if a.is_ring:
                c[-1] = c[0]
            s = LineString(c).simplify(0.02)
        out.append(s)
    noded = shapely.union_all(out)
    faces = list(polygonize(noded))
    log(f"vectorisation : {len(faces)} faces")
    # étiquette de chaque face : vote sur le raster (point représentatif + centre de masse)
    res = defaultdict(list)
    for f in faces:
        if f.area < 1e-6:
            continue
        p = f.representative_point()
        c = int((p.x - X0) / GR)
        r = int((Y1 - p.y) / GR)
        c = min(max(c, 0), NG - 1)
        r = min(max(r, 0), NG - 1)
        res[int(L[r, c])].append(f)
    return res


# =========================================================================================
# 8. Attributs
# =========================================================================================
ZONE_AUTRE, ZONE_TRAVAUX, ZONE_SB = 0, 1, 2
ETAT = {ZONE_AUTRE: "inchange_2022", ZONE_TRAVAUX: "modifie_2025", ZONE_SB: "construit_2023_2024"}
STD_H = {"trottoir": 0.14, "quai_bus": 0.20, "ilot": 0.15, "terre_plein_vegetal": 0.15,
         "espace_vert": 0.14, "piste_cyclable": 0.10, "parking": 0.12, "acces_riverain": 0.02}
RAISED = ("trottoir", "quai_bus", "ilot", "terre_plein_vegetal", "espace_vert", "piste_cyclable")


def material(cl, stats, zone, imposed_src=None):
    """Matériau de surface d'après la classe, la couleur moyenne (ortho) et la zone."""
    br, sat, exg, tex = stats
    if cl == "batiment":
        return "bati"
    if cl in ("espace_vert", "terre_plein_vegetal"):
        if zone == ZONE_TRAVAUX:
            return "massif_plante"
        return "herbe" if exg > 0.04 or br < 90 else "terre"
    if cl in ("chaussee", "parking", "acces_riverain", "piste_cyclable"):
        if cl in ("parking", "acces_riverain") and br > 165 and sat > 0.12:
            return "gravier"
        return "enrobe"
    if cl in ("trottoir", "quai_bus", "ilot"):
        if zone == ZONE_TRAVAUX:
            return "beton" if cl in ("quai_bus", "ilot") else "enrobe"
        if tex > 14 and br > 120:
            return "paves"
        return "beton" if br > 168 else "enrobe"
    if cl == "autre":
        if br > 165 and sat > 0.12:
            return "gravier"
        if exg > 0.05:
            return "herbe"
        return "beton" if br > 170 else "enrobe"
    return "enrobe"


def polygon_stats(geoms, rgb):
    """Statistiques image par polygone : luminance, saturation, verdure, texture (écart-type)."""
    o = rgb.astype(np.float32)
    br = o.mean(2)
    mx, mn = o.max(2), o.min(2)
    sat = (mx - mn) / (mx + 1)
    exg = (2 * o[..., 1] - o[..., 0] - o[..., 2]) / (o.sum(2) + 1)
    tex = np.sqrt(np.maximum(ndi.uniform_filter(br ** 2, 5) - ndi.uniform_filter(br, 5) ** 2, 0))
    lab = np.zeros((NG, NG), np.int32)
    features.rasterize([(g, i + 1) for i, g in enumerate(geoms)], out=lab, transform=GT)
    idx = np.arange(1, len(geoms) + 1)
    out = []
    for a in (br, sat, exg, tex):
        m = ndi.median(a, lab, index=idx) if len(idx) < 2000 else ndi.mean(a, lab, index=idx)
        out.append(np.nan_to_num(np.asarray(m, float)))
    return list(zip(*out)), lab


def curb_heights(lab, n, C, dtm):
    """Hauteur de bordure (m) par polygone : DTM LiDAR 2021, bande intérieure 0,3-0,8 m moins
    bande de chaussée 0,1-0,6 m (médianes), le long de la limite commune avec la chaussée."""
    ch = C == K["chaussee"]
    dch = ndi.distance_transform_edt(~ch) * GR
    out = {}
    if n == 0:
        return out
    inner = (dch >= 0.3) & (dch <= 0.8) & (lab > 0)
    idx = np.arange(1, n + 1)
    zin = ndi.median(np.nan_to_num(dtm, nan=0), lab * inner, index=idx)
    cnt = ndi.sum(inner, lab, index=idx)
    # bande de chaussée voisine de chaque polygone : étiquette du polygone le plus proche
    notch = (lab > 0) & ~ch
    dist, (ri, ci) = ndi.distance_transform_edt(~notch, return_indices=True)
    outer = ch & (dist * GR >= 0.1) & (dist * GR <= 0.6)
    lab_out = np.where(outer, lab[ri, ci], 0)
    zout = ndi.median(np.nan_to_num(dtm, nan=0), lab_out, index=idx)
    cnto = ndi.sum(outer, lab_out, index=idx)
    for i in range(n):
        if cnt[i] >= 15 and cnto[i] >= 15:
            out[i + 1] = float(zin[i] - zout[i])
    return out


def build_features(faces, Lmeta, d, aux, C, zt, ze, imposed, lines):
    """Fusion par étiquette, explosion, attributs."""
    geoms, props = [], []
    for lv, fl in faces.items():
        cl_code, zone = Lmeta(lv)
        u = unary_union(fl)
        for p in polys_of(u):
            if p.area < 0.05:
                continue
            geoms.append(p)
            props.append({"classe": CLASSES[cl_code], "_zone": zone})
    log(f"attributs : {len(geoms)} polygones")
    rgb = np.where(aux["in_ze"][..., None], d["o24"], d["o22"])
    stats, lab = polygon_stats(geoms, rgb)
    hts = curb_heights(lab, len(geoms), C, d["dtm"])
    # sources des limites : longueur de périmètre proche de chaque type de ligne
    src_lines = defaultdict(list)
    for l, s in lines:
        src_lines[s].append(l)
    src_buf = {s: unary_union(ls).buffer(0.15) for s, ls in src_lines.items()
               if s not in ("emprise", "fermeture")}
    tree_src = list(src_buf.items())
    imp_polys = [(g, cl, s) for g, cl, s in imposed.get("polys", [])] + list(imposed.get("soft", []))
    feats = []
    for i, (g, p) in enumerate(zip(geoms, props)):
        cl, zone = p["classe"], p["_zone"]
        st = stats[i]
        mat = material(cl, st, zone)
        # hauteur de bordure
        h, hsrc = None, None
        if cl in RAISED and (i + 1) in hts:
            hm = hts[i + 1]
            touches = True
        else:
            hm, touches = None, False
        if cl in RAISED and touches:
            if zone == ZONE_AUTRE and hm is not None and 0.03 <= hm <= 0.35:
                h, hsrc = round(hm, 2), "lidar_2021"
            else:
                h, hsrc = STD_H.get(cl), "standard_2025" if zone == ZONE_TRAVAUX else "standard"
        # sources
        per = g.exterior.length
        bsrc = []
        for s, b in tree_src:
            if not b.intersects(g):
                continue
            ln = g.exterior.intersection(b).length
            if ln > 0.2 * per:
                bsrc.append(s)
        csrc = {"chaussee": "osm_2026", "piste_cyclable": "osm_2026", "parking": "osm_2026",
                "acces_riverain": "osm_2026", "trottoir": "osm_2026+lidar_2021",
                "batiment": "osm_bdtopo"}.get(cl, "ortho_2022+lidar_2021")
        if zone == ZONE_SB:
            csrc = csrc.replace("ortho_2022+lidar_2021", "ortho_2024")
        if zone == ZONE_TRAVAUX:
            csrc = "plan_projet_2025+" + csrc
        for ig, icl, isrc in imp_polys:
            if icl == cl and g.intersection(ig).area > 0.5 * g.area:
                csrc = isrc
                break
        feats.append((g, {
            "classe": cl, "materiau": mat, "hauteur_bordure_m": h, "hauteur_source": hsrc,
            "source": "limites:" + ("+".join(sorted(set(bsrc))) or "raster_10cm") + " ; classe:" + csrc,
            "etat": ETAT[zone], "surface_m2": round(g.area, 2)}))
    return feats
