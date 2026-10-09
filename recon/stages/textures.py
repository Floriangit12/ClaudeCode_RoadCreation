#!/usr/bin/env python3
"""Atelier « Textures et masques » — carrefour Paquet Jardin (Meylan), état modélisé oct. 2026.

Produit, à 5 cm sur l'emprise de 300 m du site (6000 x 6000 px, grille EXACTEMENT calée sur
l'emprise BBOX de recon/common_recon.py, coin haut-gauche L93 (917129.43, 6460439.98)) :

  albedo_chaussee_5cm   ortho PCRS 5 cm du 10/05/2022 nettoyée : marquages retirés (inpainting
                        basse fréquence + grain d'enrobé cloné), véhicules / piétons / objets
                        mobiles retirés, mâts et ombres fines retirés, houppiers au-dessus de la
                        chaussée retirés, ombres portées fortes atténuées (gain par canal).
  masque_marquages_2022 peinture détectée sur l'ortho 2022 (ce qui a été retiré) : 255 blanc,
                        200 jaune, 150 vert/bleu (aplats colorés).
  masque_vehicules      véhicules et objets mobiles retirés (avec leur ombre portée).
  masque_ombres         ombres portées (0-255 = fraction d'ombre) : arbres, bâtiments, mâts...
  masque_occultations   objets retirés autres que véhicules : mâts, ombres fines, houppiers.
  masque_rapiecages     reprises d'enrobé / tranchées refermées (0-255 = intensité de l'écart).
  masque_fissures       fissures, joints et pontages (0-255 = intensité du black-hat filtré).
  masque_usure_roues    bandes de polissage dans les traces de roues (16 bits).
  masque_enrobe_2022    domaine revêtu utilisé (1 chaussée, 2 parking, 3 piste/trottoir).
  masque_zones_modifiees_2025  zones où la surface 2022 n'est PAS représentative d'oct. 2026
                        (travaux C1 2025, chantier des Saules Blancs) : 255.

Sorties (recon/out/paquet_jardin/textures/) : GeoTIFF L93 (EPSG:2154) pleine emprise +
tuiles PNG 1000x1000 (6 x 6) + index JSON (emprises L93 / repère local / UV macro) +
rapiecages.geojson + LISEZMOI_TEXTURES.md (branchement Unreal 5.8 / Houdini 22) + qa/.

Exécution (depuis la racine du dépôt) :  python3 recon/stages/textures.py
Options : --qa-only (refait seulement les rendus QA à partir des GeoTIFF), --tiles r,c;r,c
(sous-ensemble, pour la mise au point), --no-qa.

Méthode (résumé ; détails dans LISEZMOI_TEXTURES.md) :
  passe 1 (par tuile + marge 10 m) : domaine revêtu (croissance de région depuis les axes OSM,
     arrêtée sur les bordures PCRS 2019), peinture (top-hat blanc + chroma Lab), candidats
     véhicules (écart colorimétrique à l'enrobé local + densité de contours), ombres (sombre et
     bleuté), objets fins sombres (black-hat fort : mâts et leurs ombres).
  global : composantes véhicules (forme, taille) + corrections manuelles vérifiées tuile par
     tuile ; champs grossiers à 0,25 m (fond d'enrobé, gains d'ombre).
  passe 2 (par tuile + marge) : inpainting multi-échelle (convolution normalisée) + grain
     d'enrobé cloné par décalage ; atténuation des ombres.
  passe 3 (par tuile + marge) : rapiéçages (écart au fond lissé, contours nets, taille),
     fissures (black-hat + filtre de linéarité + filtrage des faux positifs), usure des roues
     (bandes claires longitudinales mesurées le long des voies, modèle sur voies 2026 dans
     les zones modifiées).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from rasterio import features
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import Window
from scipy import ndimage as ndi
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common_recon import (BBOX, O, OUT, REPO, RES, SITE_DATA, load_site_vector,  # noqa: E402
                          l93_to_uv, read_layer, uv_to_l93)

cv2.setNumThreads(4)

OUTD = OUT / "textures"
QAD = OUTD / "qa"
TILES_D = OUTD / "tuiles"
X0, Y0, X1, Y1 = BBOX
N = 6000                                   # pixels sur l'emprise (300 m / 5 cm)
T = 1000                                   # taille des tuiles produites
NT = N // T                                # 6 x 6 tuiles
MARG = 200                                 # marge de calcul autour d'une tuile (10 m)
GT = from_origin(X0, Y1, RES, RES)
CRS = "EPSG:2154"
DALLES = REPO / "data" / "raw" / "pcrs5cm" / "dalles" / "2022" / "grenoble_alpes"
ORTHO_JPG = SITE_DATA / "ortho5cm_2022"
LIDAR = REPO / "data" / "raw" / "lidar" / "paquet_jardin"
PLAN = SITE_DATA / "plan_projet_2025" / "plan_L93.tif"
CRES = 0.25                                # grille grossière globale (= LiDAR 25 cm)
NC = int(round((X1 - X0) / CRES))          # 1200
F = int(round(CRES / RES))                 # 5

SUN_AZ, SUN_EL = 150.0, 57.0               # soleil du 10/05/2022 ~10h30 UTC (ajusté sur le MNS)
ASPH_AB = (-1.3, 2.5)                      # chroma Lab (a*, b*) médiane de l'enrobé (mesurée)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# =========================================================================================
# Lecture des sources sur la grille de sortie
# =========================================================================================
class OrthoSource:
    """Mosaïque PCRS 5 cm 2022 (dalles GeoTIFF 200 m, sinon tuiles JPEG 50 m) rééchantillonnée
    sur la grille exacte de l'emprise (décalage sous-pixel constant, interpolation bicubique)."""

    def __init__(self):
        self.items = []                         # (path, left, top, w, h) en m
        if DALLES.exists():
            for p in sorted(DALLES.glob("*.tif")):
                with rasterio.open(p) as r:
                    b = r.bounds
                    if b.right < X0 - 20 or b.left > X1 + 20 or b.top < Y0 - 20 or b.bottom > Y1 + 20:
                        continue
                    self.items.append((p, b.left, b.top, r.width, r.height))
        if not self.items:
            for p in sorted(ORTHO_JPG.glob("pcrs5cm_*.jpg")):
                _, xs, ys = p.stem.split("_")
                self.items.append((p, float(xs), float(ys) + 50.0, 1000, 1000))
        self.sx0 = min(i[1] for i in self.items)
        self.sy1 = max(i[2] for i in self.items)
        self.fx = (X0 - self.sx0) / RES          # col source = fx + col sortie
        self.fy = (self.sy1 - Y1) / RES
        self._cache = {}

    def _read_src(self, sr0, sc0, h, w):
        out = np.full((h, w, 3), 128, np.uint8)
        for p, left, top, pw, ph in self.items:
            pc0 = int(round((left - self.sx0) / RES))
            pr0 = int(round((self.sy1 - top) / RES))
            r0, r1 = max(sr0, pr0), min(sr0 + h, pr0 + ph)
            c0, c1 = max(sc0, pc0), min(sc0 + w, pc0 + pw)
            if r0 >= r1 or c0 >= c1:
                continue
            if p.suffix == ".tif":
                with rasterio.open(p) as r:
                    a = r.read(window=Window(c0 - pc0, r0 - pr0, c1 - c0, r1 - r0)).transpose(1, 2, 0)
            else:
                a = np.asarray(Image.open(p).convert("RGB"))[r0 - pr0:r1 - pr0, c0 - pc0:c1 - pc0]
            out[r0 - sr0:r1 - sr0, c0 - sc0:c1 - sc0] = a
        return out

    def read(self, r0, c0, h, w):
        """Fenêtre (lignes r0..r0+h, colonnes c0..c0+w) de la grille de sortie -> uint8 RGB."""
        sr = self.fy + r0
        sc = self.fx + c0
        sr0, sc0 = int(math.floor(sr)) - 3, int(math.floor(sc)) - 3
        src = self._read_src(sr0, sc0, h + 8, w + 8)
        M = np.float32([[1, 0, sc - sc0], [0, 1, sr - sr0]])
        dst = cv2.warpAffine(src, M, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_REFLECT)
        return dst


class LidarSource:
    """Rasters LiDAR 2021 (15 cm, calés sur l'emprise) échantillonnés sur la grille 5 cm."""

    def __init__(self, name):
        with rasterio.open(LIDAR / f"{name}.tif") as r:
            self.a = r.read(1).astype(np.float32)
            self.res = r.res[0]
            assert abs(r.bounds.left - X0) < 1e-3 and abs(r.bounds.top - Y1) < 1e-3
        self.k = self.res / RES

    def read(self, r0, c0, h, w, fill=np.nan):
        k = self.k
        cols = (np.arange(c0, c0 + w, dtype=np.float32) + 0.5) / k - 0.5
        rows = (np.arange(r0, r0 + h, dtype=np.float32) + 0.5) / k - 0.5
        mx, my = np.meshgrid(cols, rows)
        a = np.nan_to_num(self.a, nan=-999.0)
        out = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-999.0)
        out[out < -500] = fill
        return out


def win_transform(r0, c0):
    return from_origin(X0 + c0 * RES, Y1 - r0 * RES, RES, RES)


def rasterize(geoms, r0, c0, h, w, value=1, dtype=np.uint8, all_touched=False):
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return np.zeros((h, w), dtype)
    wb = box(X0 + c0 * RES, Y1 - (r0 + h) * RES, X0 + (c0 + w) * RES, Y1 - r0 * RES)
    gg = [g for g in geoms if g.intersects(wb)]
    if not gg:
        return np.zeros((h, w), dtype)
    if isinstance(value, (list, tuple)):
        shapes = list(zip(gg, value))
    else:
        shapes = [(g, value) for g in gg]
    return features.rasterize(shapes, out_shape=(h, w), transform=win_transform(r0, c0),
                              fill=0, dtype=dtype, all_touched=all_touched)


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def gblur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s, borderType=cv2.BORDER_REFLECT)


def nconv(img, w, s):
    """Convolution normalisée : moyenne gaussienne (sigma s px) des pixels de poids w."""
    if img.ndim == 3:
        num = np.stack([gblur(img[..., k] * w, s) for k in range(img.shape[2])], -1)
        den = gblur(w, s)
        return num / np.maximum(den, 1e-6)[..., None], den
    num = gblur(img * w, s)
    den = gblur(w, s)
    return num / np.maximum(den, 1e-6), den


def to_lab(rgb_u8):
    return cv2.cvtColor(rgb_u8.astype(np.float32) / 255.0, cv2.COLOR_RGB2Lab)


def luma(rgb):
    rgb = rgb.astype(np.float32)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


# =========================================================================================
# Vecteurs
# =========================================================================================
def uvpoly(pts):
    return Polygon([uv_to_l93(u, v) for u, v in pts])


class Vectors:
    def __init__(self):
        roads = load_site_vector("osm_roads")
        self.car_axes = []           # (geom, demi-largeur de recherche m)
        for g, p in roads:
            hw = p.get("highway")
            if hw in ("primary", "secondary", "tertiary"):
                d = 8.5
            elif hw in ("residential", "unclassified"):
                d = 6.5
            elif hw in ("living_street", "service"):
                d = 4.5
            else:
                continue
            self.car_axes.append((g, d))
        self.primary_axes = [g for g, p in roads if p.get("highway") in ("primary", "tertiary", "residential")]
        self.parkings = [g.buffer(0.3) for g, p in load_site_vector("osm_parking")
                         if g.geom_type in ("Polygon", "MultiPolygon") and p.get("parking") != "multi-storey"]
        self.cycle = [g for g, p in load_site_vector("osm_cycleways")]
        self.foot = [g for g, p in load_site_vector("osm_footways") if p.get("highway") != "steps"]
        gam_cyc = load_site_vector("gam_v_amenagements_cyclables_grand_public")
        self.cycle += [g for g, p in gam_cyc if g.geom_type in ("LineString", "MultiLineString")]
        self.curbs_pcrs = [g for g, p in load_site_vector("gam_limite_voirie_pcrs")]
        self.revet_pcrs = [g for g, p in load_site_vector("gam_changement_revetements_pcrs")]
        bld = [g for g, p in load_site_vector("osm_buildings") if p.get("building") not in ("roof", "shelter")]
        bld += [g for g, p in load_site_vector("bdtopo_batiment")]
        self.buildings = [g for g in bld if g.geom_type in ("Polygon", "MultiPolygon")]
        # zones où l'état 2022 n'est pas représentatif d'octobre 2026
        self.zones_2025 = zones_modifiees()

    def lanes_2026(self):
        """Axes de voies 2026 (analyse etat_actuel_agent.geojson, repère L93)."""
        p = REPO / "analysis" / "paquet_jardin" / "etat_actuel_agent.geojson"
        out = []
        if not p.exists():
            return out
        fc = json.loads(p.read_text())
        from common_recon import wgs_geom_to_l93
        for f in fc["features"]:
            pr = f["properties"]
            if pr.get("categorie") == "voie" and f["geometry"]["type"] == "LineString":
                out.append((wgs_geom_to_l93(shape(f["geometry"])), pr))
        return out


def zones_modifiees():
    """Emprises modifiées après mai 2022 (repère u/v de Verdun ; analyse etat_actuel.json,
    lidar_historique.json hist-09..13) : la texture 2022 y montre l'ancien état."""
    z = []
    # Verdun SO : TPC planté, voies sens SO déportées (+2,7..2,9 m vers le NO), quai NO avancé,
    # ancienne contre-allée supprimée, quai SE unique, zébra et traversée cyclable reculés.
    z.append(("travaux_C1_verdun_SO", uvpoly([(-112, -12.5), (-8, -12.5), (-8, 9.8), (-112, 9.8)])))
    # angle SE : ancienne bretelle TAD -> noue plantée, cheminement, nouvelle bordure r ~13 m
    z.append(("travaux_C1_angle_SE", uvpoly([(-45, -12.5), (-8, -12.5), (2, -22), (-4, -34),
                                             (-30, -24)])))
    # Vercors : îlot en goutte d'eau, zébra prolongé vers l'O, surlargeur E plantée (phase 2)
    z.append(("travaux_C1_vercors", uvpoly([(-4, -34), (2, -22), (-8, -12.5), (6, -6), (14, -14),
                                            (8, -30)])))
    # chantier des Saules Blancs (2022 : terrain nu / grues ; 2024 : immeubles livrés)
    sb = Polygon([(917296, 6460120), (917440, 6460120), (917440, 6460300), (917345, 6460300),
                  (917318, 6460262), (917306, 6460236)])
    z.append(("chantier_saules_blancs_2022", sb))
    return z


# =========================================================================================
# Corrections manuelles (vérification visuelle tuile par tuile, voir qa/)
# =========================================================================================
# Véhicules / objets mobiles ajoutés : (x, y, longueur, largeur, azimut_deg depuis le nord)
VEH_AJOUTS: list = []
# Faux positifs véhicules à retirer : points L93 (toute composante qui contient le point)
VEH_RETRAITS: list = []
# Zones où aucun véhicule n'est cherché (mobilier fixe, matériaux de chantier...)
VEH_EXCLUSIONS: list = []
# Rapiéçages : faux positifs (points L93) et ajouts (polygones L93)
RAP_RETRAITS: list = []


def rect_l93(x, y, L, W, az):
    a = math.radians(az)
    ux, uy = math.sin(a), math.cos(a)
    vx, vy = -uy, ux
    pts = [(x + s * ux * L / 2 + t * vx * W / 2, y + s * uy * L / 2 + t * vy * W / 2)
           for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    return Polygon(pts)


# =========================================================================================
# Passe 1 : domaine revêtu, peinture, candidats véhicules, ombres, objets fins
# =========================================================================================
def vegetation(rgb):
    r, g_, b = [rgb[..., k].astype(np.float32) for k in range(3)]
    exg = 2 * g_ - r - b
    veg = (exg > 16) & (g_ - r > 5) & (g_ - b > 10) & (g_ > 45)
    return cv2.morphologyEx(veg.astype(np.uint8), cv2.MORPH_OPEN, disk(2)) > 0


def domain_masks(V, r0, c0, h, w, rgb, hag, chantier):
    """Codes : 1 chaussée 2022 (croissance depuis les axes OSM, arrêtée aux bordures PCRS 2019),
    2 parking (OSM), 3 piste / trottoir (OSM + 2 m), 4 autre sol revêtu probable ; 0 sinon."""
    barrier = rasterize([g.buffer(0.08) for g in V.curbs_pcrs], r0, c0, h, w)
    bld = rasterize([g.buffer(0.3) for g in V.buildings], r0, c0, h, w)
    seeds = np.zeros((h, w), np.uint8)
    dist_ok = np.zeros((h, w), bool)
    for d in (8.5, 6.5, 4.5):
        axes = [g for g, dd in V.car_axes if dd == d]
        if not axes:
            continue
        s = rasterize([g.buffer(0.3) for g in axes], r0, c0, h, w)
        seeds |= s
        dt = cv2.distanceTransform((1 - s).astype(np.uint8), cv2.DIST_L2, 5) * RES
        dist_ok |= dt <= d
    free = (barrier == 0) & (bld == 0) & dist_ok
    n, lab = cv2.connectedComponents(free.astype(np.uint8), connectivity=4)
    keep = np.unique(lab[(seeds > 0) & free])
    keep = keep[keep > 0]
    ch = np.isin(lab, keep)
    ch = cv2.morphologyEx(ch.astype(np.uint8), cv2.MORPH_CLOSE, disk(3)) > 0   # rend les traits
    veg = vegetation(rgb)
    vegd = cv2.dilate(veg.astype(np.uint8), disk(2)) > 0
    ch &= ~(vegd & ~(hag > 2.0))
    park = rasterize(V.parkings, r0, c0, h, w) > 0
    cyc = rasterize([g.buffer(2.0) for g in V.cycle] + [g.buffer(1.4) for g in V.foot], r0, c0, h, w) > 0
    sat = (rgb.max(2).astype(np.float32) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    pav_like = (sat < 0.25) & ~vegd
    nb = (bld == 0) & ~chantier
    dom = np.zeros((h, w), np.uint8)
    # sol non végétal, hors bâti : les véhicules (colorés) y restent inclus
    vegb = cv2.morphologyEx(veg.astype(np.uint8), cv2.MORPH_CLOSE, disk(4))
    vegb = cv2.morphologyEx(vegb, cv2.MORPH_OPEN, disk(6)) > 0
    other = ~vegb & nb & ~(hag > 3.0)
    other = cv2.morphologyEx(other.astype(np.uint8), cv2.MORPH_OPEN, disk(4)) > 0
    dom[other] = 4
    dom[cyc & pav_like & nb] = 3
    dom[park & ~vegd & nb] = 2
    dom[ch & ~chantier] = 1
    return dom, barrier > 0, veg


def background_bright(Y):
    """Fond d'enrobé pour le top-hat blanc : fermeture fine (bouche fissures et joints sombres)
    puis ouverture large (0,75 m) et lissage."""
    cl = cv2.morphologyEx(Y, cv2.MORPH_CLOSE, disk(3))
    op = cv2.morphologyEx(cl, cv2.MORPH_OPEN, disk(15))
    return gblur(op, 2)


def geodesic_grow(seed, allowed, steps):
    m = seed & allowed
    k = np.ones((3, 3), np.uint8)
    for _ in range(steps):
        m2 = (cv2.dilate(m.astype(np.uint8), k) > 0) & allowed
        if (m2 == m).all():
            break
        m = m2
    return m


def paint_mask(rgb, lab, Y, dom, curb, hag):
    """Peinture : 1 blanc, 2 jaune, 3 aplat coloré (vert/bleu/rouge)."""
    h, w = Y.shape
    inside = dom > 0
    bg = background_bright(Y)
    th = Y - bg
    sat = (rgb.max(2).astype(np.float32) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    A, Bc = gblur(lab[..., 1], 2.5), gblur(lab[..., 2], 2.5)
    dA, dB = A - ASPH_AB[0], Bc - ASPH_AB[1]
    veg = vegetation(rgb)
    hi = hag > 2.5
    ok = inside & ~hi
    white_s = (th > 36) & (sat < 0.2) & ok
    white_w = (th > 15) & (sat < 0.26) & ok
    ok &= ~veg
    yel_s = (dB > 9) & (dA > -4) & (Y > 95) & ok
    yel_w = (dB > 4.5) & (dA > -5) & (Y > 85) & ok
    col_s = ((dA < -3.8) | (dB < -4.5) | (dA > 7)) & ok & (Y > 95) & (th > -20)
    out = np.zeros((h, w), np.uint8)
    for code, s, wk in ((1, white_s, white_w), (2, yel_s, yel_w)):
        m = geodesic_grow(s, wk, 4)
        out[m & (out == 0)] = code
    col = cv2.morphologyEx(col_s.astype(np.uint8), cv2.MORPH_OPEN, disk(4)) > 0
    n, lb, st, _ = cv2.connectedComponentsWithStats(col.astype(np.uint8), connectivity=8)
    big = st[:, cv2.CC_STAT_AREA] >= 300
    big[0] = False
    col = big[lb]
    out[col & (out == 0)] = 3
    # filtrage des composantes : taille, contraste moyen, bordures (pierres claires)
    n, lb, st, _ = cv2.connectedComponentsWithStats((out > 0).astype(np.uint8), connectivity=8)
    if n > 1:
        idx = np.arange(n)
        area = st[:, cv2.CC_STAT_AREA].astype(np.float32)
        cnt_curb = ndi.sum(curb.astype(np.float32), lb, idx)
        mth = ndi.mean(th, lb, idx)
        isw = ndi.mean((out == 1).astype(np.float32), lb, idx) > 0.5
        bad = (area < 20) | (cnt_curb / np.maximum(area, 1) > 0.4) | (isw & (mth < 24))
        bad[0] = False
        out[bad[lb]] = 0
    return out, th


def shadow_and_dark(rgb, lab, Y, dom, hag):
    """Ombres portées (binaire) et objets fins très sombres (mâts, ombres de mâts, câbles)."""
    L, Bc = lab[..., 0], lab[..., 2]
    sat = (rgb.max(2).astype(np.float32) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    blue = rgb[..., 2].astype(np.float32) / np.maximum(rgb.sum(2).astype(np.float32), 1)
    sh_s = (L < 32) & (blue > 0.355)
    sh_w = (L < 45) & (blue > 0.34)
    n, lb = cv2.connectedComponents(sh_w.astype(np.uint8), connectivity=8)
    ids = np.unique(lb[sh_s])
    sh = np.isin(lb, ids[ids > 0])
    sh = cv2.morphologyEx(sh.astype(np.uint8), cv2.MORPH_CLOSE, disk(1)) > 0
    sh &= ~(hag > 2.5)                           # houppiers et toits : pas des ombres au sol
    # objets fins sombres : black-hat fort et étroit (calculé sans la peinture)
    Yc = np.minimum(Y, background_bright(Y) + 10)
    cl = cv2.morphologyEx(Yc, cv2.MORPH_CLOSE, disk(6))
    bh = cl - Yc
    dark = (bh > 48) & (dom > 0)
    return sh, dark, bh


def vehicle_candidates(rgb, lab, Y, dom, paint, sh, shgeo, hag):
    """Pixels candidats « véhicule / objet mobile » : écart colorimétrique à l'enrobé local ou
    forte densité de contours, hors ombres portées prévues par le MNS (arbres, bâtiments)."""
    h, w = Y.shape
    L, A, Bc = lab[..., 0], lab[..., 1], lab[..., 2]
    sat = (rgb.max(2).astype(np.float32) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    asph = (sat < 0.1) & (L > 45) & (L < 85) & (paint == 0) & (dom > 0)
    st = np.dstack([L, A, Bc, np.ones_like(L)]) * asph[..., None].astype(np.float32)
    small = cv2.resize(st, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sm = np.dstack([gblur(small[..., k], 10) for k in range(4)])
    sm = cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)
    den = np.maximum(sm[..., 3], 1e-3)
    Lb, Ab, Bb = sm[..., 0] / den, sm[..., 1] / den, sm[..., 2] / den
    Lb = np.where(den > 0.02, Lb, 66.0)
    Ab = np.where(den > 0.02, Ab, ASPH_AB[0])
    Bb = np.where(den > 0.02, Bb, ASPH_AB[1])
    dE = np.sqrt(0.6 * (L - Lb) ** 2 + (A - Ab) ** 2 + (Bc - Bb) ** 2)
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)
    gm = np.sqrt(gx * gx + gy * gy)
    edens = gblur((gm > 40).astype(np.float32) * ~(paint > 0), 6)
    cand = ((dE > 15) | (edens > 0.25)) & (dom > 0) & ~(hag > 3.0)
    g_ratio = rgb[..., 1].astype(np.float32) / np.maximum(rgb.sum(2).astype(np.float32), 1)
    cand &= ~((g_ratio > 0.365) & (sat > 0.12))   # feuillage (même sombre)
    cand &= ~((paint > 0) & (dE < 32))            # peinture seule : pas un véhicule
    cand &= ~(sh & shgeo)                         # ombre portée prévue (arbre, bâtiment, mât)
    return cand, dE


def pass1_tile(src, lid, V, G, tr, tc):
    r0, c0 = tr * T - MARG, tc * T - MARG
    h = w = T + 2 * MARG
    rgb = src.read(r0, c0, h, w)
    hag = lid["hag"].read(r0, c0, h, w, fill=0.0)
    lab = to_lab(rgb)
    Y = luma(rgb)
    chantier = rasterize([g for n_, g in V.zones_2025 if n_.startswith("chantier")], r0, c0, h, w) > 0
    shgeo = coarse_to_fine(G["shgeo25"], r0, c0, h, w) > 0.5
    dom, curb, veg = domain_masks(V, r0, c0, h, w, rgb, hag, chantier)
    paint, th = paint_mask(rgb, lab, Y, dom, curb, hag)
    sh, dark, bh = shadow_and_dark(rgb, lab, Y, dom, hag)
    cand, dE = vehicle_candidates(rgb, lab, Y, dom, paint, sh, shgeo, hag)
    canopy = (hag > 2.5) & (dom == 1)
    sat = (rgb.max(2).astype(np.float32) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    green = ((rgb[..., 1].astype(np.float32) / np.maximum(rgb.sum(2).astype(np.float32), 1) > 0.36)
             & (sat > 0.1)) | veg
    cr = (slice(MARG, MARG + T), slice(MARG, MARG + T))
    R = dict(dom=dom[cr], paint=paint[cr], sh=sh[cr], dark=dark[cr], cand=cand[cr],
             canopy=canopy[cr], dE=np.clip(dE[cr] * 4, 0, 255).astype(np.uint8),
             hi=(hag[cr] > 1.2), green=green[cr])
    R["rgb25"] = cv2.resize(rgb[cr].astype(np.float32), (T // F, T // F), interpolation=cv2.INTER_AREA)
    return R, dict(rgb=rgb, th=th, dE=dE, bh=bh, hag=hag)


# =========================================================================================
# Passe 0 : ombres géométriques (MNS LiDAR 2021, objets > 2,5 m) sur la grille 0,25 m
# =========================================================================================
def coarse_to_fine(a25, r0, c0, h, w, interp=cv2.INTER_LINEAR):
    """Champ global 0,25 m (1200x1200, calé sur l'emprise) -> fenêtre 5 cm."""
    cols = (np.arange(c0, c0 + w, dtype=np.float32) + 0.5) / F - 0.5
    rows = (np.arange(r0, r0 + h, dtype=np.float32) + 0.5) / F - 0.5
    mx, my = np.meshgrid(cols, rows)
    a = a25.astype(np.float32)
    if a.ndim == 3:
        return np.dstack([cv2.remap(np.ascontiguousarray(a[..., k]), mx, my, interp,
                                    borderMode=cv2.BORDER_REPLICATE) for k in range(a.shape[2])])
    return cv2.remap(a, mx, my, interp, borderMode=cv2.BORDER_REPLICATE)


def cast_shadow(dsm, az, el, res, maxd=60.0, eps=0.3):
    """Ombre portée d'un MNS (lancer de rayons vers le soleil, pas = 1 pixel)."""
    dx, dy = math.sin(math.radians(az)), math.cos(math.radians(az))
    tg = math.tan(math.radians(el))
    H, W = dsm.shape
    sh = np.zeros((H, W), bool)
    for k in range(1, int(maxd / res) + 1):
        d = k * res
        ix, iy = int(round(dx * d / res)), int(round(-dy * d / res))
        s = np.full((H, W), -1e9, np.float32)
        rs = slice(max(0, -iy), min(H, H - iy)); cs = slice(max(0, -ix), min(W, W - ix))
        rd = slice(max(0, iy), min(H, H + iy)); cd = slice(max(0, ix), min(W, W + ix))
        s[rs, cs] = dsm[rd, cd]
        sh |= (s - d * tg) > dsm + eps
    return sh


def pass0_geo_shadow():
    with rasterio.open(LIDAR / "dsm_25cm.tif") as r:
        dsm = r.read(1)
    with rasterio.open(LIDAR / "dtm_25cm.tif") as r:
        dtm = r.read(1)
    dtm = np.where(np.isnan(dtm), np.nanmedian(dtm), dtm)
    dsm = np.where(np.isnan(dsm), dtm, dsm)
    tall = np.where(dsm - dtm > 2.5, dsm, dtm).astype(np.float32)
    sh = cast_shadow(tall, SUN_AZ, SUN_EL, CRES)
    sh = cv2.dilate(sh.astype(np.uint8), disk(2))      # +0,5 m (contours, croissance des arbres)
    return sh


# =========================================================================================
# Étape globale : véhicules et objets mobiles
# =========================================================================================
def directional_kernel(az_deg, length_px, width_px=3):
    """Noyau linéaire qui étend un masque vers l'azimut az (sens de l'ombre)."""
    n = 2 * length_px + 1
    k = np.zeros((n, n), np.uint8)
    dx, dy = math.sin(math.radians(az_deg)), -math.cos(math.radians(az_deg))
    c = length_px
    # la dilatation OpenCV utilise le noyau tel quel : on trace le segment opposé
    cv2.line(k, (c, c), (int(round(c - dx * length_px)), int(round(c - dy * length_px))), 1, width_px)
    return k


def vehicles_global(G, V, report):
    """Composantes véhicules : forme et taille + corrections manuelles. Remplit G['veh']."""
    cand = G["cand"] > 0
    dom = G["dom"]
    m = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_CLOSE, disk(8))
    m = ndi.binary_fill_holes(m).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(5))
    n, lb, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros(n, bool)
    feats = []
    dEf = G["dE"].astype(np.float32) / 4
    idx = np.arange(n)
    mean_dE = ndi.mean(dEf, lb, idx)
    frac_hi = ndi.mean(G["hi"].astype(np.float32), lb, idx)
    frac_sh = ndi.mean(G["sh"].astype(np.float32), lb, idx)
    frac_gr = ndi.mean(G["green"].astype(np.float32), lb, idx)
    dom_mode = ndi.median(dom.astype(np.float32), lb, idx)
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA] * RES * RES
        if a < 0.25 or a > 400:
            continue
        x, y, ww, hh = st[i, :4]
        sub = (lb[y:y + hh, x:x + ww] == i).astype(np.uint8)
        cnts, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cmax = max(cnts, key=cv2.contourArea)
        (cx, cy), (rw, rh), ang = cv2.minAreaRect(cmax)
        wid, lng = sorted((rw * RES, rh * RES))
        hull = cv2.convexHull(cmax)
        solid = st[i, cv2.CC_STAT_AREA] / max(cv2.contourArea(hull), 1)
        X = X0 + (x + cx + 0.5) * RES
        Yl = Y1 - (y + cy + 0.5) * RES
        f = dict(id=int(i), x=round(X, 2), y=round(Yl, 2), aire_m2=round(a, 2), largeur_m=round(wid, 2),
                 longueur_m=round(lng, 2), solidite=round(solid, 2), dE=round(float(mean_dE[i]), 1),
                 frac_lidar_haut=round(float(frac_hi[i]), 2), frac_ombre=round(float(frac_sh[i]), 2),
                 frac_vert=round(float(frac_gr[i]), 2),
                 domaine=int(dom_mode[i]))
        ok = False
        if a >= 2.5 and wid >= 1.2 and lng >= 2.4 and solid > 0.5 and a <= 400:
            ok = True                   # voiture (+ ombre), camionnette, bus, rangée stationnée
        elif 0.25 <= a < 2.5 and wid >= 0.4 and lng <= 2.6 and f["dE"] > 22 and solid > 0.55:
            ok = f["domaine"] in (1, 3) and frac_hi[i] < 0.3   # piéton, cycliste, deux-roues
        if ok and frac_hi[i] > 0.6 and a < 6:
            ok = False                  # mobilier fixe vu par le LiDAR 2021 (borne, poteau)
        if ok and frac_sh[i] > 0.8:
            ok = False                  # ombre seule
        if ok and frac_gr[i] > 0.25:
            ok = False                  # végétation
        f["retenu"] = bool(ok)
        keep[i] = ok
        feats.append(f)
    veh = keep[lb]
    # exclusions et retraits manuels
    if VEH_EXCLUSIONS:
        ex = rasterize([Polygon(p) for p in VEH_EXCLUSIONS], 0, 0, N, N) > 0
        veh &= ~ex
    for (xr, yr) in VEH_RETRAITS:
        c = int((xr - X0) / RES); r = int((Y1 - yr) / RES)
        if 0 <= r < N and 0 <= c < N and lb[r, c] > 0:
            veh[lb == lb[r, c]] = False
            for f in feats:
                if f["id"] == lb[r, c]:
                    f["retenu"] = False
                    f["retrait_manuel"] = True
    if VEH_AJOUTS:
        add = rasterize([rect_l93(*v) for v in VEH_AJOUTS], 0, 0, N, N) > 0
        veh |= add
    # ombre propre des véhicules (vers l'azimut opposé au soleil) + liseré
    shk = directional_kernel((SUN_AZ + 180) % 360, int(2.8 / RES), 5)
    vd = cv2.dilate(veh.astype(np.uint8), shk) > 0
    vshadow = vd & (G["sh"] > 0)
    vshadow |= vd & (G["cand"] > 0) & (G["dE"] > 4 * 18)
    veh = veh | vshadow
    veh = cv2.dilate(veh.astype(np.uint8), disk(3))
    G["veh"] = veh
    report["vehicules_composantes"] = feats
    report["vehicules_retenus"] = int(sum(f["retenu"] for f in feats))
    return feats


# =========================================================================================
# Outils QA (tuiles 1000 x 1000 à 5 cm sur la grille L93 de 50 m, comme les autres ateliers)
# =========================================================================================
QA_TILES_ALL = [(x, y) for y in range(6460400, 6460099, -50) for x in range(917100, 917401, 50)]


def l93_tile_rc(X, Y):
    return int(round((Y1 - (Y + 50)) / RES)), int(round((X - X0) / RES))


def crop_global(arr, r, c, size=T, fill=0):
    out = np.full((size, size) + arr.shape[2:], fill, arr.dtype)
    r0, c0 = max(r, 0), max(c, 0)
    r1, c1 = min(r + size, arr.shape[0]), min(c + size, arr.shape[1])
    if r0 < r1 and c0 < c1:
        out[r0 - r:r1 - r, c0 - c:c1 - c] = arr[r0:r1, c0:c1]
    return out


def outline(mask, k=3):
    m = mask.astype(np.uint8)
    return (cv2.dilate(m, np.ones((k, k), np.uint8)) > 0) & ~(cv2.erode(m, np.ones((k, k), np.uint8)) > 0)


_FONT = None


def font(sz=16):
    global _FONT
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()
