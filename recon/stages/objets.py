#!/usr/bin/env python3
"""Atelier « Objets : arbres, feux, panneaux, éclairage, mobilier, bâtiments » — carrefour
Paquet Jardin (Meylan), état modélisé : octobre 2026 (après les travaux C1 de 2025).

Exécution (depuis la racine du dépôt) :  python3 recon/stages/objets.py
Sorties : recon/out/paquet_jardin/objets/
  arbres.geojson          arbres de l'emprise (L93 EPSG:2154 ; attributs x/y/z locaux), hauteur et
                          diamètre de couronne mesurés sur le LiDAR HD 2021, essence si connue,
                          jeunes sujets plantés en 2025 (plan projet), arbres abattus (non instanciés)
  mobilier.geojson        feux (mâts + têtes), panneaux (code FR), lampadaires, abris/poteaux d'arrêt,
                          potelets/barrières, totems, armoires, poteaux, bornes... (points L93)
  batiments.geojson       emprises des bâtiments (BD TOPO, complétées OSM) avec hauteurs à l'égout et
                          au faîte mesurées sur le LiDAR (classe 6), nombre d'étages
  batiments_local.geojson mêmes polygones en repère local (X, Y en m, Z sol local en attribut)
  instances.json          liste d'instanciation (prototype, x, y, z locaux, yaw, échelle) Houdini/Unreal
  objets_resume.json      comptes par type, sources, écarts connus
  qa/qa_<X>_<Y>.jpg       rendus 1000x1000 à 5 cm sur l'ortho 2022 (toute l'emprise, 36 tuiles)
  qa/plan_<X>_<Y>.jpg     rendus sur le plan projet 2025 géoréférencé (cœur, zone des travaux)

Repère local (recon/CONVENTIONS.md) : X = E - 917279.43, Y = N - 6460289.98, Z = alt - 216.30 (Z up).
Repère d'axe de Verdun (u le long de Verdun vers le NE, v vers le NW) utilisé pour les positions
déduites : x = 917279.43 + 0.7071 (u - v), y = 6460289.98 + 0.7071 (u + v).

Principes (résumé ; détails dans les commentaires de chaque section) :
- ARBRES : positions = levés GAM (gam_topo_sol_arbre_pct, bloc feuillu/conifère/souche) + inventaire
  Métropole (essence, circonférence, année ; « Abattu » = absent) + OSM ; jeunes arbres du plan projet
  2025 (fosses rouges détectées sur plan_L93.tif : TPC, bande NO, angle NO, noue SE) ; arbres du LiDAR
  2021 hors levés (sommets du MNH des classes 3-5) contrôlés sur l'ortho 2024 (verdure).
  Hauteur = max du MNH (classes 3-5) dans la couronne ; couronne = segmentation par ligne de partage
  des eaux du MNH 0,5 m ensemencée par les troncs ; contrôle par le MNH IGN 50 cm.
- BÂTIMENTS : BD TOPO (+ OSM pour les constructions récentes absentes) ; hauteurs LiDAR classe 6 :
  faîte = p99 des points toit, égout = médiane des points de la bande de rive (1,2 m intérieure) ;
  sol = médiane du MNT 15 cm dans un anneau extérieur ; étages = BD TOPO > OSM > estimation.
  Bâtiments postérieurs au LiDAR 2021 (couverture classe 6 < 30 %) : hauteur BD TOPO/OSM.
- MOBILIER : lampadaires OSM (hauteur LiDAR) ; feux, panneaux, bus, totems : liste raisonnée
  (sources par objet) car les nœuds OSM des feux datent de 2022 et la branche SW a été reconstruite :
  les supports des branches inchangées (NE, Revirée, rive E du Vercors) sont repris de l'ortho 2022 /
  LiDAR 2021 / photos 2024-2025 ; ceux des zones refaites (Verdun SW, angle SE, îlot du Vercors) sont
  DÉDUITS de la géométrie 2026 (lignes d'arrêt, traversées, refuges) et marqués « à vérifier ».
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
from shapely.ops import unary_union
from shapely import affinity

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common_recon import (BBOX, O, OUT, PLAN, REPO, RES, SITE_DATA, TILE,  # noqa: E402
                          l93_to_uv, load_site_vector, ortho_tile, uv_to_l93, write_layer)

OUTD = OUT / "objets"
QAD = OUTD / "qa"
LIDAR_DIR = REPO / "data" / "raw" / "lidar"
COPC = LIDAR_DIR / "npl" / "LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz"
DTM15 = LIDAR_DIR / "paquet_jardin" / "dtm_15cm.tif"
MNH50 = LIDAR_DIR / "mnh" / "LHD_FXX_0917_6461_MNH_O_0M50_LAMB93_IGN69.tif"
MNT50 = LIDAR_DIR / "mnt"
O24 = REPO / "data" / "raw" / "ortho" / "paquet_jardin" / "ORTHOIMAGERY_ORTHOPHOTOS2024_20cm"
OSM_RAW = [REPO / "data" / "raw" / "osm" / f for f in ("map_0_1.osm", "map_1_1.osm")]
ARBRES_METRO = REPO / "data" / "context" / "arbres_metropole.geojson"
X0, Y0, X1, Y1 = BBOX
EMPRISE = box(*BBOX)
WGS2L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)


def log(*a):
    print(*a, flush=True)


def loc(x, y, z=None):
    """L93 -> repère local (arrondi au cm)."""
    if z is None:
        return round(x - O[0], 3), round(y - O[1], 3)
    return round(x - O[0], 3), round(y - O[1], 3), round(z - O[2], 3)


def uvp(u, v):
    return Point(*uv_to_l93(u, v))


def az_from_uvdir(du, dv):
    """Azimut (degrés, depuis le nord, sens horaire) d'une direction exprimée en (du, dv)."""
    dx, dy = 0.70710678 * (du - dv), 0.70710678 * (du + dv)
    return round(math.degrees(math.atan2(dx, dy)) % 360, 1)


def yaw_from_az(az):
    """Azimut (N, horaire) -> yaw local (degrés depuis +X/Est, anti-horaire, Z up)."""
    return round((90.0 - az) % 360, 1)


# =============================================================================================
# 0. Données de base : MNT 15 cm, nuage LiDAR 2021
# =============================================================================================
class Terrain:
    def __init__(self):
        self.r = rasterio.open(DTM15)
        self.a = self.r.read(1)
        self.fallback = []
        for f in sorted(MNT50.glob("*.tif")):
            rr = rasterio.open(f)
            b = rr.bounds
            if b.left < X1 and b.right > X0 and b.bottom < Y1 and b.top > Y0:
                self.fallback.append(rr)

    def z(self, x, y, r=0.3):
        """Altitude du sol (médiane du MNT 15 cm dans un rayon r) ; repli sur le MNT IGN 50 cm."""
        c = int((x - self.r.transform.c) / 0.15)
        w = int((self.r.transform.f - y) / 0.15)
        k = max(1, int(r / 0.15))
        if 0 <= c < self.a.shape[1] and 0 <= w < self.a.shape[0]:
            sub = self.a[max(0, w - k):w + k + 1, max(0, c - k):c + k + 1]
            v = sub[np.isfinite(sub)]
            if v.size:
                return float(np.median(v))
        for rr in self.fallback:
            b = rr.bounds
            if b.left <= x < b.right and b.bottom <= y < b.top:
                v = list(rr.sample([(x, y)]))[0][0]
                if v > -1000:
                    return float(v)
        return float("nan")

    def ring_median(self, poly, d0=0.6, d1=2.5):
        ring = poly.buffer(d1).difference(poly.buffer(d0))
        xs, ys = sample_polygon(ring, 0.5)
        zz = [self.z(x, y, 0.1) for x, y in zip(xs, ys)]
        zz = np.array([v for v in zz if np.isfinite(v)])
        return float(np.percentile(zz, 30)) if zz.size else float("nan")


def sample_polygon(poly, step):
    x0, y0, x1, y1 = poly.bounds
    xs, ys = np.meshgrid(np.arange(x0, x1, step) + step / 2, np.arange(y0, y1, step) + step / 2)
    xs, ys = xs.ravel(), ys.ravel()
    import shapely
    m = shapely.contains_xy(poly, xs, ys)
    return xs[m], ys[m]


class Lidar:
    """Points LiDAR HD 2021 (COPC) de l'emprise + 15 m ; hauteur sur sol par le MNT 15 cm."""

    def __init__(self, terrain: Terrain):
        import laspy
        log("lecture du nuage COPC ...")
        m = 15.0
        try:
            from laspy import CopcReader, Bounds
            with CopcReader.open(str(COPC)) as cr:
                pts = cr.query(Bounds(mins=np.array([X0 - m, Y0 - m]), maxs=np.array([X1 + m, Y1 + m])))
            x, y, z = np.asarray(pts.x), np.asarray(pts.y), np.asarray(pts.z)
            c = np.asarray(pts.classification)
        except Exception:  # repli : lecture complète
            las = laspy.read(str(COPC))
            x, y, z = np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)
            c = np.asarray(las.classification)
            k = (x >= X0 - m) & (x <= X1 + m) & (y >= Y0 - m) & (y <= Y1 + m)
            x, y, z, c = x[k], y[k], z[k], c[k]
        self.x, self.y, self.z, self.c = x, y, z.astype(np.float32), c.astype(np.uint8)
        a = terrain.a
        T = terrain.r.transform
        col = ((x - T.c) / 0.15).astype(int)
        row = ((T.f - y) / 0.15).astype(int)
        ok = (col >= 0) & (col < a.shape[1]) & (row >= 0) & (row < a.shape[0])
        h = np.full(len(x), np.nan, np.float32)
        h[ok] = z[ok] - a[row[ok], col[ok]]
        self.h = h
        log(f"  {len(x)} points, classes {dict(Counter(self.c.tolist()))}")
        # MNH végétation (classes 3-5) et bâti (classe 6) à 0,5 m sur l'emprise + 15 m
        self.res = 0.5
        self.gx0, self.gy1 = X0 - m, Y1 + m
        self.n = int(round((X1 - X0 + 2 * m) / self.res))
        self.chm = self._grid(np.isin(self.c, [3, 4, 5]) & np.isfinite(h) & (h > 0.3) & (h < 45))
        self.bld = self._grid((self.c == 6) & np.isfinite(h) & (h > 1.0))
        self.tree_veg = cKDTree(np.c_[x[np.isin(self.c, [3, 4, 5])], y[np.isin(self.c, [3, 4, 5])]])

    def _grid(self, m):
        col = ((self.x[m] - self.gx0) / self.res).astype(int)
        row = ((self.gy1 - self.y[m]) / self.res).astype(int)
        ok = (col >= 0) & (col < self.n) & (row >= 0) & (row < self.n)
        g = np.zeros((self.n, self.n), np.float32)
        np.maximum.at(g, (row[ok], col[ok]), self.h[m][ok])
        return g

    def rc(self, x, y):
        return int((self.gy1 - y) / self.res), int((x - self.gx0) / self.res)

    def xy(self, r, c):
        return self.gx0 + (c + 0.5) * self.res, self.gy1 - (r + 0.5) * self.res


class Ortho2024:
    """Ortho IGN 2024 20 cm (tuiles 200 m, fichiers .jgw) : contrôle de présence de la végétation."""

    def __init__(self):
        self.tiles = []
        for j in sorted(O24.glob("*.jgw")):
            v = [float(t) for t in j.read_text().split()]
            jp = j.with_suffix(".jpg")
            if jp.exists():
                self.tiles.append((v[4] - v[0] / 2, v[5] - v[3] / 2, v[0], jp))
        self.cache = {}

    def _img(self, p):
        if p not in self.cache:
            self.cache[p] = np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
        return self.cache[p]

    def green_frac(self, x, y, r):
        """Part de pixels « végétation » (vert ou sombre ombragé non gris) dans un disque."""
        for (xl, yt, res, p) in self.tiles:
            if xl <= x < xl + 200 and yt - 200 < y <= yt:
                a = self._img(p)
                c0, r0 = (x - xl) / res, (yt - y) / res
                k = int(r / res) + 1
                rr, cc = np.mgrid[-k:k + 1, -k:k + 1]
                m = (rr ** 2 + cc ** 2) <= (r / res) ** 2
                R = (r0 + rr[m]).astype(int).clip(0, a.shape[0] - 1)
                C = (c0 + cc[m]).astype(int).clip(0, a.shape[1] - 1)
                px = a[R, C]
                g = px[:, 1] - (px[:, 0] + px[:, 2]) / 2
                veg = (g > 6) | ((px.sum(1) < 180) & (px[:, 1] >= px[:, 0]))
                return float(veg.mean())
        return float("nan")


# =============================================================================================
# 1. ARBRES
# =============================================================================================
# Jeunes arbres plantés lors des travaux 2025 : fosses (carrés rouges barrés) du plan projet
# géoréférencé, détectées automatiquement ; codes d'essence lus sur le plan (zooms vérifiés),
# dans l'ordre SW -> NE de chaque alignement. Décodage des abréviations : HYPOTHÈSES (non publiées).
PLAN_CODES = {
    # (zone, rang SW->NE) : code
    "TPC": ["Alc", "As", "Ce", "Alc", "As"],
    "bande_NO": ["Gt", "Aca", "Ac", "Gt", "Ac"],
    "angle_NO": ["Ca"],
    "noue_SE": ["Ul", "Oc", "Oc", "Ul"],
}
CODE_HYP = {
    "Alc": "Alnus cordata (aulne de Corse) ?", "As": "Acer sp. (code As) ?",
    "Ce": "Celtis / Cercis (code Ce) ?", "Gt": "Gleditsia triacanthos (févier) ?",
    "Aca": "Acer campestre (érable champêtre, petit sujet) ?", "Ac": "Acer campestre ?",
    "Ca": "Celtis australis (micocoulier) / Carpinus ?", "Ul": "Ulmus (orme résistant) ?",
    "Oc": "Ostrya carpinifolia (charme-houblon) ?",
}


def plan_warp(xmin, ymin, size, npx):
    """Rééchantillonne le plan projet (géotransformation tournée) en image nord en haut."""
    import cv2
    r = rasterio.open(PLAN)
    img = np.transpose(r.read(), (1, 2, 0)).copy()
    T = r.transform
    inv = ~T
    res = size / npx
    A = np.array([[res, 0, xmin + res / 2], [0, -res, ymin + size - res / 2], [0, 0, 1]])
    Ti = np.array([[inv.a, inv.b, inv.c], [inv.d, inv.e, inv.f], [0, 0, 1]])
    M = (Ti @ A)[:2]
    M[:, 2] -= 0.5
    out = cv2.warpAffine(img, M, (npx, npx), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(40, 40, 40))
    return out


def plan_tree_pits():
    """Fosses d'arbres du plan : carrés rouge-orangé de 1,2-1,7 m, remplissage 0,25-0,65."""
    xmin, ymin, S, N = X0, Y0, 300.0, 6000
    img = plan_warp(xmin, ymin, S, N).astype(int)
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    m = (R > 170) & (G < 140) & (B < 80) & (R - G > 70) & (R - B > 140)
    mc = ndimage.binary_closing(m, iterations=3)
    lab, _ = ndimage.label(mc)
    pits = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        h = (sl[0].stop - sl[0].start) * 0.05
        w = (sl[1].stop - sl[1].start) * 0.05
        n = (lab[sl] == i + 1).sum()
        fill = n / ((h / 0.05) * (w / 0.05))
        if not (1.2 <= h <= 1.75 and 1.2 <= w <= 1.75 and 0.25 <= fill <= 0.65):
            continue
        cy, cx = ndimage.center_of_mass(lab[sl] == i + 1)
        x = xmin + (sl[1].start + cx + 0.5) * 0.05
        y = ymin + S - (sl[0].start + cy + 0.5) * 0.05
        pits.append((x, y))
    # l'« Aca » (petit sujet) est dessiné sans fosse rouge : position lue sur le plan (cercle orange)
    pits.append(uv_to_l93(-71.9, 9.3))
    out = []
    for x, y in pits:
        u, v = l93_to_uv(x, y)
        if -75 <= u <= -25 and -5 <= v <= -1:
            z = "TPC"
        elif -80 <= u <= -25 and 7 <= v <= 12:
            z = "bande_NO"
        elif -20 <= u <= -14 and 4 <= v <= 9:
            z = "angle_NO"
        elif -62 <= u <= -28 and -15 <= v <= -11:
            z = "noue_SE"
        else:
            log(f"  fosse du plan hors zone connue ignorée : u={u:.1f} v={v:.1f}")
            continue
        out.append(dict(x=x, y=y, u=u, v=v, zone=z))
    res = []
    for z, codes in PLAN_CODES.items():
        L = sorted([p for p in out if p["zone"] == z], key=lambda p: p["u"])
        if len(L) != len(codes):
            log(f"  ATTENTION zone {z} : {len(L)} fosses pour {len(codes)} codes")
        for p, c in zip(L, codes):
            p["code"] = c
            res.append(p)
    return res


def load_metro_trees():
    fc = json.loads(ARBRES_METRO.read_text())
    out = []
    for f in fc["features"]:
        lon, lat = f["geometry"]["coordinates"][0]
        x, y = WGS2L93.transform(lon, lat)
        if X0 - 5 <= x <= X1 + 5 and Y0 - 5 <= y <= Y1 + 5:
            out.append(dict(x=x, y=y, **f["properties"]))
    return out


def build_trees(lid: Lidar, ter: Terrain, o24: Ortho2024):
    log("== arbres")
    gam = []
    for g, p in load_site_vector("gam_topo_sol_arbre_pct"):
        pt = list(g.geoms)[0] if hasattr(g, "geoms") else g
        if EMPRISE.contains(pt):
            sc = p.get("echelle_bloc")
            gam.append(dict(x=pt.x, y=pt.y, bloc=p["bloc"], gam_echelle=float(sc.split(";")[0]) if sc else None))
    metro = load_metro_trees()
    osm = [(g, p) for g, p in load_site_vector("osm_trees") if EMPRISE.contains(g)]
    plan = plan_tree_pits()
    log(f"  GAM {len(gam)}, Métropole {len(metro)}, OSM {len(osm)}, plan 2025 {len(plan)}")

    trees = []
    for i, q in enumerate(gam):
        typ = {"ARBRE_FEUILLU": "feuillu", "ARBRE_CONIFERE": "conifere", "SOUCHE": "souche"}[q["bloc"]]
        trees.append(dict(x=q["x"], y=q["y"], type=typ, sources=["GAM levé topo (Meylan_Topo.dwg)"],
                          gam_bloc=q["bloc"], gam_echelle_bloc=q["gam_echelle"]))
    # inventaire Métropole : rattachement au plus proche arbre GAM (< 3 m), sinon nouvel arbre
    T = cKDTree([(t["x"], t["y"]) for t in trees])
    used = set()
    for m in sorted(metro, key=lambda m: m["etat"] != "Présent"):
        d, k = T.query([m["x"], m["y"]])
        info = dict(essence=m.get("essence"), genre=m.get("genre"), circonference_cm=m.get("circonference"),
                    hauteur_classe_inventaire=m.get("hauteur"), annee_plantation=m.get("annee_plantation") or None,
                    inventaire_etat=m.get("etat"), inventaire_id=m.get("arbre_id"),
                    alignement=m.get("alignement"))
        if d < 3.0 and k not in used:
            used.add(k)
            trees[k].update(info)
            trees[k]["sources"].append("inventaire arbres Métropole")
        else:
            t = dict(x=m["x"], y=m["y"], type="conifere" if m.get("type") == "Conifère" else "feuillu",
                     sources=["inventaire arbres Métropole"], **info)
            trees.append(t)
    for g, p in osm:
        T = cKDTree([(t["x"], t["y"]) for t in trees])
        d, k = T.query([g.x, g.y])
        if d < 3.0:
            trees[k]["sources"].append(f"OSM {p['osm_id']}")
            if p.get("leaf_type") == "needleleaved":
                trees[k]["type"] = "conifere"
        else:
            trees.append(dict(x=g.x, y=g.y, type="conifere" if p.get("leaf_type") == "needleleaved" else "feuillu",
                              sources=[f"OSM {p['osm_id']}"]))
    # jeunes arbres du plan projet 2025
    T = cKDTree([(t["x"], t["y"]) for t in trees])
    for p in plan:
        d, k = T.query([p["x"], p["y"]])
        t = dict(x=p["x"], y=p["y"], type="feuillu", sources=["plan projet 2025 (fosse d'arbre)"],
                 essence_code=p["code"], essence=CODE_HYP.get(p["code"]), zone_plantation=p["zone"],
                 jeune=True, annee_plantation=2025)
        if d < 2.0:
            # un arbre déjà levé au même endroit : on garde la position du levé, attributs du plan
            trees[k].update({kk: vv for kk, vv in t.items() if kk not in ("x", "y", "sources", "type")})
            trees[k]["sources"].append("plan projet 2025 (fosse d'arbre)")
        else:
            trees.append(t)

    # --- arbres du LiDAR 2021 absents des levés : sommets du MNH (classes 3-5) ---
    chm = lid.chm
    s = ndimage.gaussian_filter(chm, 1.0)
    tops = []
    for (hmin, hmax, rad) in [(4, 9, 2), (9, 16, 3), (16, 50, 4)]:
        mx = ndimage.maximum_filter(s, size=2 * rad + 1)
        pk = (s == mx) & (s >= hmin) & (s < hmax)
        for r, c in zip(*np.nonzero(pk)):
            tops.append((r, c, float(s[r, c])))
    tops.sort(key=lambda t: -t[2])
    kept = []
    for r, c, hh in tops:
        if all((r - r2) ** 2 + (c - c2) ** 2 >= (max(1.5, 0.22 * h2) / lid.res) ** 2 for r2, c2, h2 in kept):
            kept.append((r, c, hh))
    T = cKDTree([(t["x"], t["y"]) for t in trees])
    n_add = n_rej = 0
    for r, c, hh in kept:
        x, y = lid.xy(r, c)
        if not EMPRISE.contains(Point(x, y)):
            continue
        d, k = T.query([x, y])
        if d < max(3.0, 0.3 * hh):
            continue
        if lid.bld[max(0, r - 2):r + 3, max(0, c - 2):c + 3].max() > 2.0:
            continue                                   # toit / façade
        # crête de couronne d'un arbre levé voisin ? (sommet à moins de 0,45 h d'un arbre plus haut)
        dd, kk = T.query([x, y], k=3)
        near = any(di < 0.45 * hh and di < 6.0 for di in np.atleast_1d(dd))
        g24 = o24.green_frac(x, y, max(1.0, 0.15 * hh))
        if near:
            continue
        if not (g24 >= 0.35):
            n_rej += 1
            continue
        trees.append(dict(x=x, y=y, type="feuillu", sources=["LiDAR HD 2021 (sommet du MNH, hors levés)"],
                          controle_ortho2024_vegetation=round(g24, 2)))
        T = cKDTree([(t["x"], t["y"]) for t in trees])
        n_add += 1
    log(f"  sommets LiDAR ajoutés : {n_add} (rejetés car absents de l'ortho 2024 : {n_rej})")

    # --- mesures LiDAR : hauteur et couronne (ligne de partage des eaux ensemencée) ---
    from skimage.segmentation import watershed
    markers = np.zeros(chm.shape, np.int32)
    for i, t in enumerate(trees):
        r, c = lid.rc(t["x"], t["y"])
        if 0 <= r < chm.shape[0] and 0 <= c < chm.shape[1]:
            # graine = maximum local du MNH à moins de 1,5 m du tronc
            r0, r1, c0, c1 = max(0, r - 3), r + 4, max(0, c - 3), c + 4
            sub = s[r0:r1, c0:c1]
            rr, cc = np.unravel_index(np.argmax(sub), sub.shape)
            if sub.max() >= 2.0:
                markers[r0 + rr, c0 + cc] = i + 1
            else:
                markers[r, c] = i + 1
    mask = s >= 1.5
    lab = watershed(-s, markers, mask=mask)
    mnh = rasterio.open(MNH50)
    for i, t in enumerate(trees):
        r, c = lid.rc(t["x"], t["y"])
        seg = lab == (i + 1)
        # limiter la couronne à 9 m du tronc
        R0, R1, C0, C1 = max(0, r - 18), r + 19, max(0, c - 18), c + 19
        sub = seg[R0:R1, C0:C1].copy()
        yy, xx = np.mgrid[R0:R0 + sub.shape[0], C0:C0 + sub.shape[1]]
        sub &= ((yy - r) ** 2 + (xx - c) ** 2) * lid.res ** 2 <= 81
        area = float(sub.sum()) * lid.res ** 2
        hmax = float(chm[R0:R1, C0:C1][sub].max()) if sub.any() else 0.0
        # contrôle MNH IGN 50 cm (max dans 2 m)
        win = [(t["x"] + dx, t["y"] + dy) for dx in (-1.5, -0.5, 0.5, 1.5) for dy in (-1.5, -0.5, 0.5, 1.5)]
        vals = [v[0] for v in mnh.sample(win)]
        h_ign = float(max([v for v in vals if v > -100] or [0]))
        t["z_sol"] = round(ter.z(t["x"], t["y"]), 2)
        t["hauteur_lidar_m"] = round(hmax, 1)
        t["hauteur_mnh_ign_m"] = round(h_ign, 1)
        t["diam_couronne_lidar_m"] = round(2 * math.sqrt(area / math.pi), 1) if area > 0 else 0.0
    return trees


def finalize_trees(trees):
    """Règles d'état 2026, valeurs retenues et identifiants."""
    feats = []
    zone_travaux = Polygon([uv_to_l93(u, v) for u, v in [(-112, -30), (8, -30), (8, 22), (-112, 22)]])
    for t in trees:
        p = {}
        jeune = t.get("jeune", False)
        h, dc = t["hauteur_lidar_m"], t["diam_couronne_lidar_m"]
        etat, conf, note = "existant", "haute", []
        if t["type"] == "souche":
            etat, h, dc = "souche", 0.4, 0.0
        elif jeune:
            etat = "planté 2025 (projet C1, jeune sujet)"
            conf = "moyenne"
            h, dc = 4.5, 1.8      # baliveau / tige force 18-20 après une saison
            note.append("position et essence : plan projet 2025 ; non visible sur LiDAR 2021 / ortho 2022-2024")
        elif t.get("inventaire_etat") == "Abattu":
            etat, conf = "abattu (inventaire Métropole)", "moyenne"
        elif h < 2.5:
            # levé mais pas de couronne en 2021 : arbre planté après le vol LiDAR (ou arbuste)
            etat, conf = "existant (jeune ou planté après 2021)", "moyenne"
            note.append("hauteur LiDAR 2021 < 2,5 m : dimensions par défaut")
            h, dc = 5.0, 2.5
        if "LiDAR HD 2021 (sommet du MNH, hors levés)" in t["sources"]:
            conf = "moyenne"
            note.append("arbre non levé (domaine privé ou hors levé) : position = sommet de couronne")
            if zone_travaux.contains(Point(t["x"], t["y"])):
                etat, conf = "à vérifier (zone des travaux 2025)", "faible"
        if dc < 1.0 and etat == "existant":
            dc = max(dc, 0.35 * h)
        p.update(type=t["type"], essence=t.get("essence"), essence_code=t.get("essence_code"),
                 genre=t.get("genre"), hauteur_m=round(float(h), 1), diametre_couronne_m=round(float(dc), 1),
                 hauteur_lidar_2021_m=t["hauteur_lidar_m"], hauteur_mnh_ign_m=t["hauteur_mnh_ign_m"],
                 diametre_couronne_lidar_m=t["diam_couronne_lidar_m"],
                 circonference_cm=t.get("circonference_cm"), annee_plantation=t.get("annee_plantation"),
                 hauteur_classe_inventaire=t.get("hauteur_classe_inventaire"),
                 zone_plantation=t.get("zone_plantation"), etat_2026=etat,
                 instancier=etat not in ("abattu (inventaire Métropole)",),
                 source="; ".join(t["sources"]), confiance=conf, remarque="; ".join(note) or None,
                 gam_bloc=t.get("gam_bloc"), gam_echelle_bloc=t.get("gam_echelle_bloc"),
                 controle_ortho2024_vegetation=t.get("controle_ortho2024_vegetation"))
        X, Y, Z = loc(t["x"], t["y"], t["z_sol"])
        p.update(x_local=X, y_local=Y, z_local=Z, z_sol_ngf=t["z_sol"])
        feats.append((Point(t["x"], t["y"]), p))
    feats.sort(key=lambda f: (round(f[0].y, -1), f[0].x))
    for i, (g, p) in enumerate(feats):
        p["id"] = f"arbre_{i + 1:03d}"
    return feats


# =============================================================================================
# QA : rendus 1000 x 1000 px à 5 cm
# =============================================================================================
def _font(sz=14):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


TREE_COL = {"existant": (0, 255, 0), "existant (jeune ou planté après 2021)": (160, 255, 120),
            "planté 2025 (projet C1, jeune sujet)": (255, 255, 0), "abattu (inventaire Métropole)": (255, 60, 60),
            "à vérifier (zone des travaux 2025)": (255, 150, 0), "souche": (150, 90, 40)}
MOB_COL = {"feu": (255, 40, 40), "panneau": (40, 160, 255), "lampadaire": (255, 230, 0),
           "arret_bus": (255, 0, 255), "barriere": (255, 140, 0), "divers": (0, 255, 255)}


def draw_layers(img, tx, ty, trees, mob, bats, size=50.0, npx=1000, labels=True):
    res = size / npx
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(over)
    f12, f14 = _font(12), _font(14)

    def px(x, y):
        return ((x - tx) / res, (ty + size - y) / res)

    tb = box(tx - 15, ty - 15, tx + size + 15, ty + size + 15)
    for g, p in bats or []:
        if not g.intersects(tb):
            continue
        for poly in getattr(g, "geoms", [g]):
            dr.line([px(*c) for c in poly.exterior.coords], fill=(255, 0, 255, 255), width=3)
        if labels and g.centroid.intersects(box(tx, ty, tx + size, ty + size)):
            c = px(g.centroid.x, g.centroid.y)
            dr.text((c[0] - 40, c[1] - 8), f"F{p['hauteur_faite_m']:.1f} E{p['hauteur_egout_m']:.1f} N{p['nb_etages']}",
                    fill=(255, 0, 255, 255), font=f14, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for g, p in trees or []:
        if not g.intersects(tb):
            continue
        c = px(g.x, g.y)
        col = TREE_COL.get(p["etat_2026"], (200, 200, 200))
        r = max(p["diametre_couronne_m"] / 2 / res, 6)
        dr.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=(*col, 255), width=2)
        dr.ellipse((c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4), fill=(*col, 255))
        if labels:
            lab = f"{p['hauteur_m']:.0f}m"
            if p.get("essence_code"):
                lab += " " + p["essence_code"]
            dr.text((c[0] + 6, c[1] + 2), lab, fill=(*col, 255), font=f12, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for g, p in mob or []:
        if not g.intersects(tb):
            continue
        col = MOB_COL.get(p["categorie"], (255, 255, 255))
        if g.geom_type != "Point":
            for ln in getattr(g, "geoms", [g]):
                cs = ln.exterior.coords if ln.geom_type == "Polygon" else ln.coords
                dr.line([px(*cc[:2]) for cc in cs], fill=(*col, 255), width=3)
            continue
        c = px(g.x, g.y)
        k = 7
        if p["categorie"] == "feu":
            dr.rectangle((c[0] - k, c[1] - k, c[0] + k, c[1] + k), outline=(*col, 255), width=3)
            for hd in p.get("tetes", []):
                a = math.radians(hd["azimut_deg"])
                L = 26 if hd["type"].startswith("R11") else 18
                e = (c[0] + L * math.sin(a), c[1] - L * math.cos(a))
                hc = {"R11v": (255, 40, 40), "R12": (0, 255, 0), "R13c": (255, 160, 0)}.get(hd["type"][:4].rstrip(" _"), (255, 255, 255))
                dr.line([c, e], fill=(*hc, 255), width=3)
                dr.ellipse((e[0] - 3, e[1] - 3, e[0] + 3, e[1] + 3), fill=(*hc, 255))
        elif p["categorie"] == "panneau":
            dr.polygon([(c[0], c[1] - k - 2), (c[0] + k + 2, c[1]), (c[0], c[1] + k + 2), (c[0] - k - 2, c[1])],
                       outline=(*col, 255), width=3)
            if p.get("azimut_deg") is not None:
                a = math.radians(p["azimut_deg"])
                dr.line([c, (c[0] + 22 * math.sin(a), c[1] - 22 * math.cos(a))], fill=(*col, 255), width=2)
        elif p["categorie"] == "lampadaire":
            dr.ellipse((c[0] - k, c[1] - k, c[0] + k, c[1] + k), fill=(*col, 255), outline=(0, 0, 0, 255))
            if p.get("azimut_deg") is not None and p.get("porte_a_faux_m"):
                a = math.radians(p["azimut_deg"])
                L = p["porte_a_faux_m"] / res
                dr.line([c, (c[0] + L * math.sin(a), c[1] - L * math.cos(a))], fill=(*col, 255), width=2)
        else:
            dr.ellipse((c[0] - k + 2, c[1] - k + 2, c[0] + k - 2, c[1] + k - 2), outline=(*col, 255), width=3)
        if labels:
            lab = p.get("code") or p.get("sous_type") or p["type"]
            dr.text((c[0] + 9, c[1] - 16), str(lab)[:22], fill=(*col, 255), font=f14, stroke_width=2,
                    stroke_fill=(0, 0, 0, 255))
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


# =============================================================================================
# 2. BÂTIMENTS
# =============================================================================================
def build_buildings(lid: Lidar, ter: Terrain):
    log("== bâtiments")
    import shapely
    bd = [(g, p) for g, p in load_site_vector("bdtopo_batiment") if g.intersects(EMPRISE)]
    osm = [(g, p) for g, p in load_site_vector("osm_buildings") if g.intersects(EMPRISE)]
    m6 = (lid.c == 6) & np.isfinite(lid.h)
    X6, Y6, Z6 = lid.x[m6], lid.y[m6], lid.z[m6]
    mo = (lid.c == 1) & np.isfinite(lid.h) & (lid.h > 1.5)
    XO, YO, ZO = lid.x[mo], lid.y[mo], lid.z[mo]

    def pts_in(poly, X, Y, Z):
        x0, y0, x1, y1 = poly.bounds
        sel = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
        xs, ys, zs = X[sel], Y[sel], Z[sel]
        k = shapely.contains_xy(poly, xs, ys)
        return xs[k], ys[k], zs[k]

    def coverage(poly, xs, ys):
        if not len(xs):
            return 0.0
        occ = set(zip((xs // 1).astype(int), (ys // 1).astype(int)))
        cells = sum(1 for _ in zip(*sample_polygon(poly, 1.0)))
        return min(1.0, len(occ) / max(cells, 1))

    items = []
    replaced = set()
    # 1) constructions récentes (absentes du LiDAR 2021) : la BD TOPO les découpe en morceaux
    #    (créés le 2025-07-04) ; on prend l'emprise OSM 2026 (relevé plus complet) quand elle existe.
    for go, po in osm:
        if po.get("amenity") == "shelter":
            continue
        xs, ys, _ = pts_in(go.buffer(-0.3) if go.buffer(-0.3).area > 1 else go, X6, Y6, Z6)
        cov_l = coverage(go, xs, ys)
        hits = [i for i, (g, p) in enumerate(bd) if g.intersection(go).area > 0.3 * min(g.area, go.area)]
        cov_bd = sum(bd[i][0].intersection(go).area for i in hits) / go.area
        if cov_l < 0.3 and (hits or go.area > 8) and (p0 := (bd[hits[0]][1] if hits else {})) is not None:
            recent = all((bd[i][1].get("date_creation") or "") >= "2024" for i in hits) if hits else True
            if hits and not recent:
                continue
            for i in hits:
                replaced.add(i)
            items.append(dict(geom=go, bd=bd[hits[0]][1] if hits else None, osm=po,
                              source="OSM 2026" + (" (remplace %d morceau(x) BD TOPO récents)" % len(hits) if hits
                                                   else " (absent de la BD TOPO)")))
    for i, (g, p) in enumerate(bd):
        if i in replaced:
            continue
        best, bi = None, 0.0
        for go, po in osm:
            inter = go.intersection(g).area
            if inter > 0 and inter / min(g.area, go.area) > bi:
                best, bi = po, inter / min(g.area, go.area)
        items.append(dict(geom=g, bd=p, osm=best if bi > 0.5 and best.get("amenity") != "shelter" else None,
                          source="BD TOPO"))
    for go, po in osm:            # autres emprises OSM absentes de la BD TOPO (bâtiments anciens)
        if po.get("amenity") == "shelter" or any(it["osm"] is po and it["source"].startswith("OSM") for it in items):
            continue
        cov = sum(g.intersection(go).area for g, _ in bd) / go.area
        if cov < 0.3 and go.area > 8:
            items.append(dict(geom=go, bd=None, osm=po, source="OSM 2026 (absent de la BD TOPO)"))

    feats = []
    for it in items:
        g = it["geom"]
        p, po = it["bd"] or {}, it["osm"] or {}
        inner = g.buffer(-0.3) if g.buffer(-0.3).area > 1 else g
        xs, ys, zs = pts_in(inner, X6, Y6, Z6)
        cover = coverage(inner, xs, ys)
        src_h = "LiDAR HD 2021 (classe 6)"
        if cover < 0.3:
            xo, yo, zo = pts_in(inner, XO, YO, ZO)
            if coverage(inner, xo, yo) >= 0.5:
                xs, ys, zs, cover = xo, yo, zo, coverage(inner, xo, yo)
                src_h = "LiDAR HD 2021 (classe 1, toit non classé)"
        z_sol = ter.ring_median(g)
        if not np.isfinite(z_sol):
            z_sol = p.get("altitude_minimale_sol") or ter.z(g.centroid.x, g.centroid.y)
        lev_bd = p.get("nombre_d_etages")
        lev_osm = int(float(po["building:levels"])) if po.get("building:levels") else None
        roof_lev = int(float(po["roof:levels"])) if po.get("roof:levels") else 0
        usage = p.get("usage_1") if p.get("usage_1") not in (None, "Indifférencié") else (po.get("building") or p.get("usage_1"))
        commercial = (usage or "").lower().startswith(("commercial", "industriel", "retail", "sport", "office"))
        note = []
        if cover >= 0.3 and len(zs) >= 6:
            hf = float(np.percentile(zs, 99)) - z_sol
            band = inner.difference(g.buffer(-1.5)) if g.buffer(-1.5).area > 1 else inner
            ine = shapely.contains_xy(band, xs, ys)
            he = float(np.median(zs[ine])) - z_sol if ine.sum() >= 5 else float(np.percentile(zs, 10)) - z_sol
            he = min(he, hf)
            spread = float(np.percentile(zs, 95) - np.percentile(zs, 10))
            toit = "terrasse" if spread < 1.2 else "pentes"
        else:
            levels = lev_osm or lev_bd
            if levels:
                he = 3.0 * levels + 0.6
                src_h = "estimée (étages OSM/BD TOPO x 3 m + 0,6 m)"
            elif p.get("hauteur"):
                he, src_h = float(p["hauteur"]), "BD TOPO (hauteur)"
            else:
                he, src_h = 3.0, "valeur par défaut (annexe)"
            hf = he + (2.5 * roof_lev if roof_lev else (0.0 if po.get("roof:shape") == "flat" else 1.0))
            toit = "terrasse" if po.get("roof:shape") == "flat" else "inconnu"
            note.append(f"couverture LiDAR 2021 = {cover:.0%} : construit après août 2021 ou masqué")
        # nombre d'étages : source la plus cohérente avec la hauteur à l'égout
        per = 4.0 if commercial else 3.0
        est = max(1, int(round((he - 0.4) / per)))
        cands = [(lev_bd, "BD TOPO"), ((lev_osm + roof_lev) if lev_osm else None, "OSM")]
        cands = [(int(n), s_) for n, s_ in cands if n]
        if src_h.startswith("LiDAR"):
            ok = [(abs(n - est), n, s_) for n, s_ in cands
                  if abs(n - est) <= 1.5 or (commercial and 3 * n - 1 <= he <= 6 * n + 2)]
            if ok:
                _, n_et, src_n = min(ok)
            else:
                n_et, src_n = est, f"estimé LiDAR ({per:.0f} m/étage)"
                if cands:
                    note.append("étages " + ", ".join(f"{s_} {n}" for n, s_ in cands) + " incohérents avec la hauteur LiDAR")
        else:
            n_et, src_n = (cands[0][0], cands[0][1]) if cands else (est, "estimé")
            if lev_osm:
                n_et, src_n = lev_osm + roof_lev, "OSM"
        prop = dict(source_emprise=it["source"], cleabs=p.get("cleabs"), osm_id=po.get("osm_id"),
                    nature=p.get("nature"), usage=usage, nom=po.get("name"),
                    construction_legere=bool(p.get("construction_legere")) if p else False,
                    z_sol_ngf=round(float(z_sol), 2),
                    hauteur_egout_m=round(float(he), 1), hauteur_faite_m=round(float(hf), 1),
                    z_egout_ngf=round(float(z_sol + he), 2), z_faite_ngf=round(float(z_sol + hf), 2),
                    toit=toit, nb_etages=int(n_et), source_etages=src_n, source_hauteur=src_h,
                    couverture_lidar=round(cover, 2), hauteur_bdtopo_m=p.get("hauteur"),
                    etages_bdtopo=lev_bd, etages_osm=lev_osm,
                    date_creation_bdtopo=(p.get("date_creation") or "")[:10] or None,
                    partiel_emprise=g.intersection(EMPRISE).area / g.area < 0.99,
                    surface_m2=round(g.area, 1), remarque="; ".join(note) or None,
                    z_sol_local=round(float(z_sol) - O[2], 3))
        feats.append((g, prop))
    feats.sort(key=lambda f: (-f[0].area))
    for i, (g, p) in enumerate(feats):
        p["id"] = f"bat_{i + 1:03d}"
    log(f"  {len(feats)} bâtiments")
    return feats


# =============================================================================================
# 3. MOBILIER
# =============================================================================================
def D(dx, dy):
    """Point L93 à partir d'un décalage local (dx, dy) en m."""
    return Point(O[0] + dx, O[1] + dy)


def U(u, v):
    return Point(*uv_to_l93(u, v))


# Directions de face (azimut de la normale de la face visible, depuis le nord, sens horaire) :
AZ_SW_IN = 225.0      # face tournée vers le SW : vue par le trafic Verdun SW -> NE (sens entrant SW)
AZ_NE_IN = 45.0       # face vers le NE : vue par le trafic Verdun NE -> SW
AZ_REV_IN = 330.0     # face vers le NNO : vue par le trafic sortant de la Revirée (vers le SSE)
AZ_VERC_IN = 172.0    # face vers le S : vue par le trafic montant du Vercors (cap ~352°)


def head(t, az, h, **kw):
    """Tête de feu. t : R11v (véhicules, 3 feux), R11v_rep (répétiteur petit format), R12 (piétons),
    R13c (cycles) ; az = azimut de la face ; h = hauteur du centre de la tête (m)."""
    d = dict(type=t, azimut_deg=round(az % 360, 1), hauteur_centre_m=h)
    d.update(kw)
    return d


# ---- supports de feux (état 2026) ----------------------------------------------------------
# Repères 2021-2022 : têtes LiDAR (classe 1, sommet 3,3-3,5 m) et ombres de mâts (ortho 2022) ;
# photos Panoramax 2024-05 / 2025-05 / 2025-08 pour les types de têtes. Les supports des zones
# refaites en 2025 (Verdun SW, surface centrale sud, bretelle SE) sont supprimés ; ceux de la
# nouvelle traversée SW sont déduits (ligne d'arrêt u = -32,3 ; passage u -29,5..-26,0 ;
# traversée cyclable u -25,9..-22,3 ; refuge v -3,9..-1,5 ; bordure SE v -10,8 ; bordure NO v +5,0).
FEUX = [
    # --- Verdun NE (inchangé) : approche vers le SW, ligne d'arrêt u = 17,2, passage u 11,1-14,1
    dict(id="feu_NE_droite", geom=D(6.5, 15.3), branche="Verdun NE", hauteur_mat_m=3.4,
         role="approche Verdun NE -> SW, support droit (angle Revirée, fourreau jaune) + piétons",
         tetes=[head("R11v", AZ_NE_IN, 2.9), head("R11v_rep", AZ_NE_IN, 1.9), head("R12", 135, 2.4)],
         etat="existant (inchangé ; LiDAR 2021 + ortho 2022 + photos 2025-05)", confiance="haute",
         source="LiDAR 2021 (tête à 3,37 m en dx 6,6 dy 15,4) ; ortho 2022 (ombre) ; Panoramax 2025-05-18 9834f494"),
    dict(id="feu_NE_TPC", geom=D(12.0, 9.0), branche="Verdun NE", hauteur_mat_m=3.4,
         role="approche Verdun NE -> SW, support gauche sur le nez du TPC + piétons (refuge)",
         tetes=[head("R11v", AZ_NE_IN, 2.9), head("R12", 315, 2.4), head("R12", 135, 2.4)],
         etat="existant (inchangé ; LiDAR 2021 + photos 2025-05)", confiance="haute",
         source="LiDAR 2021 (tête 3,34 m) ; Panoramax 2025-05-18 9834f494 / e5d79de9"),
    dict(id="feu_NE_SE_pietons", geom=D(15.5, -0.1), branche="Verdun NE", hauteur_mat_m=2.6,
         role="traversée Verdun NE, extrémité SE (piétons)",
         tetes=[head("R12", 315, 2.2)],
         etat="existant (inchangé ; LiDAR 2021)", confiance="moyenne",
         source="LiDAR 2021 (amas classe 1, sommet 2,59 m) ; OSM crossing 1959022976 (bouton d'appel)"),
    # --- Revirée (inchangé) : approche vers le SSE (cap ~150°), ligne d'arrêt v ~ 16,6
    dict(id="feu_REV_droite", geom=D(-11.9, 8.8), branche="Revirée", hauteur_mat_m=3.4,
         role="approche Revirée, support droit (côté O) + piétons + cédez-le-passage cycliste au feu",
         tetes=[head("R11v", AZ_REV_IN, 2.9), head("R11v_rep", AZ_REV_IN, 1.9), head("R12", 60, 2.4),
                head("M12", AZ_REV_IN, 1.6, note="panonceau M12 (OSM red_turn:right:bicycle=yes)")],
         etat="existant (inchangé ; LiDAR 2021 + photos 2024-2025)", confiance="haute",
         source="LiDAR 2021 (tête 3,38 m) ; Panoramax 2024-05 3fc0ff2e, 2025-05 119d9094 ; OSM 1959022958"),
    dict(id="feu_REV_ilot_axial", geom=D(-8.5, 13.1), branche="Revirée", hauteur_mat_m=4.2,
         role="approche Revirée, support gauche sur l'îlot axial (mât haut à fourreau jaune)",
         tetes=[head("R11v", AZ_REV_IN, 3.6)],
         etat="existant (inchangé ; LiDAR 2021 : têtes à 4,0-4,1 m)", confiance="moyenne",
         source="LiDAR 2021 ; ortho 2022 (ombre longue) ; observations coeur-07"),
    dict(id="feu_REV_ilot_E", geom=D(-3.9, 5.9), branche="Revirée", hauteur_mat_m=2.6,
         role="traversées Revirée (piétons) et piste (cycles), îlot arrondi E",
         tetes=[head("R12", 245, 2.2), head("R13c", 335, 1.6)],
         etat="existant (inchangé ; LiDAR 2021)", confiance="moyenne",
         source="LiDAR 2021 (amas classe 1, sommet 2,61 m) ; observations coeur-30"),
    # --- Vercors : approche vers le N (cap ~352°), ligne d'effet ~ (dx 11, dy -18)
    dict(id="feu_VERC_droite", geom=D(13.8, -12.3), branche="Vercors", hauteur_mat_m=3.4,
         role="approche Vercors, support droit (rive E) + piétons",
         tetes=[head("R11v", AZ_VERC_IN, 2.9), head("R11v_rep", AZ_VERC_IN, 1.9), head("R12", 239, 2.4),
                head("AB3a", AZ_VERC_IN, 1.6, note="panonceau triangulaire pointe en bas sous un feu (photo 2025-01), "
                                                   "lecture incertaine (AB3a ou M12)")],
         etat="existant (rive E inchangée ; LiDAR 2021 + photo 2025-01)", confiance="haute",
         source="LiDAR 2021 (tête 3,39 m) ; Panoramax 2025-01-12 a1ffea74 ; OSM 1959022975"),
    dict(id="feu_VERC_ilot", geom=D(7.4, -17.4), branche="Vercors", hauteur_mat_m=3.4,
         role="approche Vercors, support gauche sur l'îlot en goutte d'eau + piétons (refuge)",
         tetes=[head("R11v", AZ_VERC_IN, 2.9), head("R12", 59, 2.4), head("R12", 222, 2.4)],
         etat="existant 2021 (pointe de l'ancien îlot effilé) dans l'emprise du nouvel îlot 2025 : à vérifier",
         confiance="moyenne", source="LiDAR 2021 (tête 3,50 m en dx 7,7 dy -17,3) ; plan projet 2025 (îlot)"),
    dict(id="feu_VERC_O_pietons", geom=D(-1.2, -25.4), branche="Vercors", hauteur_mat_m=2.6,
         role="traversée Vercors, extrémité O (angle SE du carrefour, piétons)",
         tetes=[head("R12", 42, 2.2)],
         etat="déduit 2026 (nouvel angle SE, à vérifier)", confiance="faible",
         source="géométrie 2026 (bordure GAM 2646533206, passage piéton prolongé vers l'O)"),
    # --- Verdun SW (reconstruit 2025) : approche vers le NE, ligne d'arrêt u = -32,3
    dict(id="feu_SW_droite", geom=U(-30.8, -11.5), branche="Verdun SW", hauteur_mat_m=3.4,
         role="approche Verdun SW -> NE, support droit (bordure SE) + piétons",
         tetes=[head("R11v", AZ_SW_IN, 2.9), head("R11v_rep", AZ_SW_IN, 1.9), head("R12", 315, 2.4)],
         etat="déduit 2026 (traversée SW reculée de 9 m en 2025, à vérifier)", confiance="faible",
         source="géométrie GAM/plan 2025 ; implantation type (support droit entre ligne d'arrêt et passage)"),
    dict(id="feu_SW_TPC", geom=U(-30.2, -2.7), branche="Verdun SW", hauteur_mat_m=3.4,
         role="approche Verdun SW -> NE, support gauche sur la pointe du TPC planté + piétons (refuge)",
         tetes=[head("R11v", AZ_SW_IN, 2.9), head("R12", 135, 2.4), head("R12", 315, 2.4)],
         etat="déduit 2026 (à vérifier)", confiance="faible",
         source="plan projet 2025 (TPC planté jusqu'à u -29,6, refuge u -29,6..-22,3)"),
    dict(id="feu_SW_NO_pietons", geom=U(-28.7, 5.7), branche="Verdun SW", hauteur_mat_m=2.6,
         role="traversée Verdun SW, extrémité NO (piétons)",
         tetes=[head("R12", 135, 2.2)],
         etat="déduit 2026 (à vérifier)", confiance="faible", source="géométrie GAM/plan 2025"),
    dict(id="feu_SW_cycles_SE", geom=U(-22.6, -11.4), branche="Verdun SW", hauteur_mat_m=2.2,
         role="traversée cyclable bidirectionnelle (Chronovélo 1), extrémité SE",
         tetes=[head("R13c", 135, 1.6)],
         etat="déduit 2026 (à vérifier)", confiance="faible",
         source="plan projet 2025 / GAM (traversée u -25,9..-22,3) ; pratique Chronovélo (feux cycles)"),
    dict(id="feu_SW_cycles_NO", geom=U(-22.6, 5.7), branche="Verdun SW", hauteur_mat_m=2.2,
         role="traversée cyclable bidirectionnelle (Chronovélo 1), extrémité NO",
         tetes=[head("R13c", 315, 1.6)],
         etat="déduit 2026 (à vérifier)", confiance="faible",
         source="plan projet 2025 / GAM ; pratique Chronovélo (feux cycles)"),
]

# ---- panneaux de police / direction (état 2026) -----------------------------------------------
PANNEAUX = [
    dict(code="B21a1", geom=U(16.2, -2.0), az=AZ_NE_IN, h=1.0, support="potelet bas (nez de TPC)",
         etat="existant (photos 2025-05)", confiance="haute",
         source="Panoramax 2025-05-18 119d9094 r01_c00 ; observations p2025_05_360-06/17"),
    dict(code="B21a1", geom=U(-17.3, -2.7), az=AZ_NE_IN, h=1.0, support="potelet bas (nez du TPC SW, côté carrefour)",
         etat="déduit 2026 (remplace le B21a1 de l'îlot rond SW de 2025)", confiance="faible",
         source="photo 2025-05 (B21a1 sur l'îlot rond SW) ; plan 2025 (nez planté u -21,9..-17)"),
    dict(code="B21a1", geom=U(-69.3, -2.7), az=AZ_SW_IN, h=1.0, support="potelet bas (début du TPC planté)",
         etat="déduit 2026 (à vérifier)", confiance="faible", source="plan 2025 (TPC dès u -69,5, nez hachuré amont)"),
    dict(code="B21a1", geom=D(4.4, -11.6), az=10.0, h=1.0, support="potelet bas (tête de l'îlot Vercors)",
         etat="déduit 2026 (B21 sur l'ancien îlot en 2025)", confiance="faible",
         source="photo 2025-05 e5d79de9 (annotation B21a1 vers le S) ; plan 2025 (îlot en goutte d'eau)"),
    dict(code="D21", geom=D(-3.6, 6.4), az=135.0, h=2.6, support="poteau (2 panneaux)",
         texte="LA REVIRÉE / Collège L. Terray ; Commerces de LA REVIRÉE", etat="existant (photos 2025-05 et 2025-08)",
         confiance="haute", source="Panoramax 2025-05-18 119d9094 r01_c04 ; 2025-08-31 ab4cfacd"),
    dict(code="C114", geom=D(-8.4, 24.0), az=250.0, h=2.3, support="poteau (C114 + AB3a + panonceau)",
         etat="existant (photos 2024-05 et 2025)", confiance="moyenne",
         source="observation p2024_05_360-24 ; Panoramax e5d79de9 / 10ec04d5 (annotations C114, AB3a) ; LiDAR 2021"),
    dict(code="AB3a", geom=D(-8.4, 24.0), az=250.0, h=1.6, support="même poteau que le C114",
         etat="existant (photos 2024-05 et 2025)", confiance="moyenne", source="idem C114"),
    dict(code="C113", geom=D(6.2, 19.9), az=225.0, h=2.2, support="poteau (début de la piste NE)",
         etat="existant (Panoramax 2025, 6 rayons concordants)", confiance="moyenne",
         source="annotations Panoramax 2025-05-18 et 2025-08-31 (FR:C113), triangulation"),
    dict(code="B2a", geom=D(46.4, 65.1), az=342.0, h=2.3, support="poteau (sortie riveraine NO de Verdun NE)",
         etat="existant (Panoramax 2025-08)", confiance="moyenne",
         source="annotations Panoramax 2025-08-31 (FR:B2a, FR:AB3a), triangulation ; OSM give_way 12184212277"),
    dict(code="AB3a", geom=D(46.4, 65.1), az=342.0, h=1.6, support="même poteau que le B2a",
         etat="existant (Panoramax 2025-08)", confiance="moyenne", source="idem B2a"),
    dict(code="A17", geom=D(109.5, 119.8), az=AZ_NE_IN, h=2.3, support="poteau (Verdun NE, côté NO)",
         etat="observé 2025-08 (Panoramax), permanent ou de chantier : à vérifier", confiance="faible",
         source="annotations Panoramax 2025-08-31 f6297e9f / 3a86ce25 / 430a2fa1 (FR:A17)"),
    dict(code="AB3a", geom=Point(917308.7, 6460154.3), az=270.0, h=1.6, support="poteau (îlot herbeux angle S)",
         etat="existant (Panoramax 2026-07)", confiance="moyenne",
         source="observation p2026_07_ign-14 ; poteau visible sur l'ortho 2022"),
    dict(code="AB4", geom=Point(917311.3, 6460156.7), az=270.0, h=1.6, support="poteau (sortie allée des Mitaillères)",
         etat="existant (Panoramax 2026-07)", confiance="moyenne",
         source="OSM highway=stop 12167664505 ; observation p2026_07_ign-15 (implantation exacte incertaine)"),
    dict(code="B6a1", geom=Point(917292.0, 6460149.7), az=0.0, h=2.4, support="sur le candélabre 0456 (avec C13a)",
         etat="existant (Panoramax 2026-07)", confiance="moyenne", source="observation p2026_07_ign-16"),
    dict(code="C13a", geom=Point(917292.0, 6460149.7), az=0.0, h=1.9, support="sur le candélabre 0456",
         etat="existant (Panoramax 2026-07)", confiance="moyenne", source="observation p2026_07_ign-16"),
    dict(code="B6a1", geom=Point(917263.3, 6460163.8), az=180.0, h=2.2, support="poteau (panonceau Parking privé L'Horloge)",
         etat="existant (Panoramax 2026-07)", confiance="faible",
         source="annotations Panoramax 2026-07-28 (FR:B6a1), triangulation à 2 rayons"),
    dict(code="B1", geom=Point(917244.0, 6460149.8), az=150.0, h=2.2, support="poteau",
         etat="existant (Panoramax 2026-07)", confiance="moyenne",
         source="annotations Panoramax 2026-07-28 fab53b58 / ffc2e8ac / 05089869 (FR:B1), triangulation"),
]

# Zone des travaux C1 2025 (approximative, repère u/v) : les objets OSM antérieurs à août 2025 qui
# s'y trouvent sont marqués « à vérifier ».
ZONE_TRAVAUX = unary_union([
    Polygon([uv_to_l93(u, v) for u, v in [(-112, -16), (-12, -16), (-12, 12), (-112, 12)]]),
    Polygon([uv_to_l93(u, v) for u, v in [(-12, -14), (8, -14), (8, 12), (-12, 12)]]),
    Polygon([uv_to_l93(u, v) for u, v in [(-40, -40), (2, -40), (2, -12), (-40, -12)]]),
])
DATE_TRAVAUX = "2025-08-01"


def read_osm_raw():
    """Nœuds et chemins OSM (extraction 2026-10) de l'emprise, avec date de dernière édition."""
    import xml.etree.ElementTree as ET
    nodes, tagged, ways = {}, {}, {}
    for f in OSM_RAW:
        for ev, el in ET.iterparse(f):
            if el.tag == "node":
                x, y = WGS2L93.transform(float(el.get("lon")), float(el.get("lat")))
                nodes[el.get("id")] = (x, y)
                tags = {c.get("k"): c.get("v") for c in el if c.tag == "tag"}
                if tags and X0 - 5 <= x <= X1 + 5 and Y0 - 5 <= y <= Y1 + 5:
                    tagged[el.get("id")] = dict(id="node/" + el.get("id"), x=x, y=y, tags=tags,
                                                date=el.get("timestamp", "")[:10])
                el.clear()
            elif el.tag == "way":
                tags = {c.get("k"): c.get("v") for c in el if c.tag == "tag"}
                nds = [c.get("ref") for c in el if c.tag == "nd"]
                ways[el.get("id")] = dict(id="way/" + el.get("id"), nds=nds, tags=tags,
                                          date=el.get("timestamp", "")[:10])
                el.clear()
    for w in ways.values():
        w["pts"] = [nodes[n] for n in w["nds"] if n in nodes]
    ways = {k: w for k, w in ways.items() if w["pts"] and any(X0 - 5 <= x <= X1 + 5 and Y0 - 5 <= y <= Y1 + 5
                                                            for x, y in w["pts"])}
    return tagged, ways


def etat_osm(pt, date):
    if date >= DATE_TRAVAUX:
        return f"2026 confirmé (OSM, édition {date})", "haute"
    if ZONE_TRAVAUX.contains(pt):
        return f"à vérifier (zone des travaux 2025 ; OSM du {date})", "faible"
    return f"existant (OSM du {date}, zone inchangée)", "moyenne"


def nearest_road_az(pt, roads):
    best, bd = None, 1e9
    for ln in roads:
        d = ln.distance(pt)
        if d < bd:
            bd, best = d, ln
    if best is None or bd > 25:
        return None, None
    q = best.interpolate(best.project(pt))
    return round(math.degrees(math.atan2(q.x - pt.x, q.y - pt.y)) % 360, 1), round(bd, 1)


def build_mobilier(lid: Lidar, ter: Terrain):
    log("== mobilier")
    tagged, ways = read_osm_raw()
    feats = []

    def add(g, categorie, typ, **p):
        p = {k: v for k, v in p.items()}
        p.update(categorie=categorie, type=typ)
        feats.append((g, p))

    # --- 3.1 feux ---
    for f in FEUX:
        g = f["geom"]
        tetes = f["tetes"]
        add(g, "feu", "support_feux", id=f["id"], branche=f["branche"], role=f["role"],
            hauteur_m=f["hauteur_mat_m"], tetes=tetes,
            nb_tetes_R11v=sum(1 for t in tetes if t["type"] == "R11v"),
            nb_repetiteurs=sum(1 for t in tetes if t["type"] == "R11v_rep"),
            nb_tetes_R12=sum(1 for t in tetes if t["type"] == "R12"),
            nb_tetes_R13c=sum(1 for t in tetes if t["type"] == "R13c"),
            azimut_deg=next((t["azimut_deg"] for t in tetes if t["type"].startswith("R11v")), tetes[0]["azimut_deg"]),
            etat_2026=f["etat"], confiance=f["confiance"], source=f["source"])
    # --- 3.2 panneaux ---
    n = Counter()
    for s in PANNEAUX:
        n[s["code"]] += 1
        add(s["geom"], "panneau", "panneau", id=f"pan_{s['code']}_{n[s['code']]}", code=s["code"],
            azimut_deg=s["az"], hauteur_m=s["h"], support=s["support"], texte=s.get("texte"),
            etat_2026=s["etat"], confiance=s["confiance"], source=s["source"])
    # --- 3.3 lampadaires (OSM) ---
    roads = [g for g, p in load_site_vector("osm_roads")
             if p.get("highway") in ("primary", "secondary", "tertiary", "residential", "unclassified",
                                     "living_street", "service")]
    gam_b = [shape(f["geometry"]) for f in json.loads((SITE_DATA / "etat_2026" / "bordure_lin_L93.geojson")
                                                       .read_text())["features"]]
    gam_bu = unary_union(gam_b)
    m1 = (lid.c == 1) & np.isfinite(lid.h) & (lid.h > 3.5)
    T1 = cKDTree(np.c_[lid.x[m1], lid.y[m1]])
    H1 = lid.h[m1]
    for g, p in load_site_vector("osm_street_lamps"):
        if not EMPRISE.contains(g):
            continue
        raw = tagged.get(p["osm_id"].split("/")[1], {})
        date = raw.get("date", "")
        idx = T1.query_ball_point([g.x, g.y], 2.5)
        h_l = float(np.max(H1[idx])) if idx else None
        mount = p.get("lamp_mount")
        h_def = {"bent_mast": 9.0, "straight_mast": 6.0}.get(mount, 7.0)
        h = round(h_l, 1) if h_l and 4.0 <= h_l <= 14.0 else h_def
        etat, conf = etat_osm(g, date)
        geom = g
        note = None
        u, v = l93_to_uv(g.x, g.y)
        ref = p.get("ref")
        # supports de la haie séparative de Verdun SW (refs 2352, 2354) : leur position de 2022 tombe
        # dans la chaussée sens SO déportée de ~2,8 m vers le NO en 2025 -> déplacés derrière la
        # nouvelle bordure NO (GAM), à 0,8 m.
        if ref in ("2352", "2354"):
            a, b = uv_to_l93(u, -10), uv_to_l93(u, 20)
            I = LineString([a, b]).intersection(gam_bu)
            vs = sorted(l93_to_uv(q.x, q.y)[1] for q in getattr(I, "geoms", [I]) if q.geom_type == "Point")
            vk = min([vv for vv in vs if 3.5 < vv < 7.0] or [4.8])
            geom = U(u, vk + 0.8)
            etat, conf = "déplacé (déduit) : position OSM 2022 dans la chaussée 2026", "faible"
            note = f"OSM 2022 en v = {v:.1f} ; bordure NO 2026 (GAM) en v = {vk:.2f}"
        az, dist = nearest_road_az(geom, roads)
        n_cr = 2 if (p.get("power") == "catenary_mast" or ref in ("2352", "2354", "2355", "2356", "2357", "2358")) else (
            1 if mount == "bent_mast" else 0)
        add(geom, "lampadaire", "lampadaire", id=f"lamp_{p['osm_id'].split('/')[1]}", osm_id=p["osm_id"], ref=ref,
            sous_type={"bent_mast": "mât à crosse", "straight_mast": "mât droit"}.get(mount, "mât (type inconnu)"),
            lamp_type=p.get("lamp_type"), nb_crosses=n_cr, porte_a_faux_m=1.5 if n_cr else 0.3,
            hauteur_m=h, hauteur_lidar_2021_m=round(h_l, 1) if h_l else None,
            azimut_deg=az, distance_axe_route_m=dist, etat_2026=etat, confiance=conf,
            source=f"OSM {p['osm_id']} ({date})" + ("; hauteur LiDAR 2021 (classe 1)" if h_l and 4 <= h_l <= 14 else
                                                     "; hauteur par défaut selon le type"),
            remarque=note)

    # --- 3.4 arrêts de bus ---
    # abris : SE = OSM 185326914 (déplacé le 2025-10-27, conforme au plan à ~2 m) ;
    #         NO = plan projet 2025 (OSM 185326911 resté latéralement sur l'ancienne bordure).
    for g, p in load_site_vector("osm_buildings"):
        if p.get("amenity") == "shelter" and p.get("osm_id") == "way/185326914":
            c = g.centroid
            add(c, "arret_bus", "abri_bus", id="abri_SE_ref21", nom="La Revirée (quai SE, réf. 21, sens Montbonnot)",
                operateur=p.get("operator"), longueur_m=4.0, largeur_m=1.5, hauteur_m=2.5,
                azimut_deg=az_from_uvdir(0, 1), etat_2026="2026 confirmé (OSM 2025-10-27 ; plan 2025 à ~2 m)",
                confiance="haute", source="OSM way/185326914 ; plan projet 2025", emprise_osm=g.wkt)
    nw = U(-61.6, 7.7)
    add(nw, "arret_bus", "abri_bus", id="abri_NO_ref396", nom="La Revirée (quai NO, réf. 396, sens Grenoble)",
        operateur="JCDecaux", longueur_m=4.0, largeur_m=1.5, hauteur_m=2.5, azimut_deg=az_from_uvdir(0, -1),
        etat_2026="2026 (plan projet 2025 ; OSM 185326911 déplacé le long de l'axe seulement)", confiance="moyenne",
        source="plan projet 2025 (symbole « Abri bus » détecté en u -63,6..-60,0, v 7,4-8,0) ; OSM way/185326911")
    add(U(-68.0, -11.9), "arret_bus", "poteau_arret", id="poteau_SE_ref21", hauteur_m=2.8, azimut_deg=AZ_SW_IN,
        etat_2026="déduit (poteau d'arrêt vu sur la photo 2025-08-31 ; position en tête de quai)", confiance="faible",
        source="hist-07 (Panoramax 2025-08-31) ; quai OSM 185326913 (u -101,4..-65,6)")
    add(U(-37.5, 5.4), "arret_bus", "poteau_arret", id="poteau_NO_ref396", hauteur_m=2.8, azimut_deg=AZ_NE_IN,
        etat_2026="déduit (tête de quai, zigzag GAM u -66,4..-36,5)", confiance="faible", source="GAM / plan 2025")
    pole = tagged.get("13261073976")
    if pole:
        add(Point(pole["x"], pole["y"]), "arret_bus", "poteau_arret", id="poteau_REV_ligne42",
            nom="La Revirée (Flexo 42, chemin de la Revirée)", hauteur_m=2.8,
            azimut_deg=nearest_road_az(Point(pole["x"], pole["y"]), roads)[0],
            etat_2026=f"2026 confirmé (OSM {pole['date']})", confiance="haute", source="OSM node/13261073976")

    # --- 3.5 autres nœuds OSM (mobilier, barrières, réseaux) ---
    TYPES = [
        (lambda t: t.get("amenity") == "bench", "divers", "banc", 0.9),
        (lambda t: t.get("amenity") == "waste_basket", "divers", "corbeille", 1.0),
        (lambda t: t.get("amenity") == "bicycle_parking", "divers", "stationnement_velos", 0.8),
        (lambda t: t.get("amenity") == "vending_machine", "divers", "distributeur", 1.8),
        (lambda t: t.get("amenity") == "recycling", "divers", "conteneur_verre", 1.8),
        (lambda t: t.get("amenity") == "drinking_water", "divers", "fontaine", 1.1),
        (lambda t: t.get("amenity") == "letter_box", "divers", "boite_aux_lettres", 1.3),
        (lambda t: t.get("tourism") == "information", "divers", "panneau_information", 2.2),
        (lambda t: t.get("advertising") == "poster_box", "divers", "mobilier_publicitaire", 2.6),
        (lambda t: t.get("man_made") == "street_cabinet", "divers", "armoire", 1.4),
        (lambda t: t.get("man_made") == "utility_pole", "divers", "poteau_reseau", 9.0),
        (lambda t: t.get("man_made") == "surveillance" and t.get("camera:mount") == "pole", "divers", "mat_camera", 6.0),
        (lambda t: t.get("emergency") == "fire_hydrant", "divers", "poteau_incendie", 0.9),
        (lambda t: t.get("barrier") == "bollard", "barriere", "potelet", 1.0),
        (lambda t: t.get("barrier") in ("gate", "wicket_gate", "sliding_gate"), "barriere", "portail", 1.6),
        (lambda t: t.get("barrier") == "lift_gate", "barriere", "barriere_levante", 1.1),
        (lambda t: t.get("barrier") == "cycle_barrier", "barriere", "chicane", 1.1),
    ]
    nw_shift = 0
    for nid, nd in tagged.items():
        t = nd["tags"]
        pt = Point(nd["x"], nd["y"])
        if not EMPRISE.contains(pt):
            continue
        for test, cat, typ, h in TYPES:
            if not test(t):
                continue
            geom, note = pt, None
            etat, conf = etat_osm(pt, nd["date"])
            u, v = l93_to_uv(pt.x, pt.y)
            # quai NO (édition OSM du 2026-03-14) : déplacé le long de l'axe seulement, resté sur l'ancienne
            # bordure (hist-21) -> décalage latéral de +2,9 m (déport de la bordure NO, GAM)
            if nd["date"] >= "2026-03-01" and -76 <= u <= -30 and -1 <= v <= 6.5:
                geom = U(u, v + 2.9)
                note = "position OSM décalée de +2,9 m vers le NO (bordure du quai NO déplacée en 2025)"
                conf = "moyenne"
                nw_shift += 1
            az = None
            if typ in ("banc", "panneau_information", "mobilier_publicitaire", "distributeur", "stationnement_velos"):
                az = nearest_road_az(geom, roads)[0]
            props = dict(id=f"{typ}_{nid}", osm_id=nd["id"], azimut_deg=az, hauteur_m=h, etat_2026=etat,
                         confiance=conf, source=f"OSM {nd['id']} ({nd['date']})", remarque=note)
            for k in ("capacity", "bicycle_parking", "vending", "operator", "ref", "utility", "material", "barrier",
                      "camera:type", "surveillance:zone", "information", "board_type", "fire_hydrant:type",
                      "backrest", "covered"):
                if k in t:
                    props["osm_" + k.replace(":", "_")] = t[k]
            add(geom, cat, typ, **props)
            break
    log(f"  objets du quai NO décalés : {nw_shift}")
    # clôtures OSM
    for w in ways.values():
        if w["tags"].get("barrier") in ("fence", "wall", "guard_rail") and len(w["pts"]) >= 2:
            g = LineString(w["pts"]).intersection(EMPRISE)
            if g.is_empty:
                continue
            etat, conf = etat_osm(g.centroid, w["date"])
            add(g, "barriere", "cloture" if w["tags"]["barrier"] == "fence" else w["tags"]["barrier"],
                id=f"cloture_{w['id'].split('/')[1]}", osm_id=w["id"], hauteur_m=1.8,
                materiau=w["tags"].get("material"), etat_2026=etat, confiance=conf, source=f"OSM {w['id']} ({w['date']})")

    # --- 3.6 objets relevés sur ortho / LiDAR / photos (absents d'OSM) ---
    add(D(19.2, 4.0), "divers", "poteau_reseau", id="poteau_bois_NE", hauteur_m=10.0, osm_material="wood",
        etat_2026="existant (LiDAR 2021 : 10,0 m ; photo 2025-05 : poteau bois avec lignes aériennes)",
        confiance="haute", source="LiDAR 2021 (classe 1) ; ortho 2022 (ombre) ; Panoramax 2025-05-18 119d9094 r01_c00")
    add(U(-20.6, -3.0), "divers", "mat_camera", id="mat_camera_SW_TPC", hauteur_m=6.0,
        etat_2026="2026 confirmé (OSM node/12288437339 édité le 2026-04-03, caméra trafic orientable)",
        confiance="moyenne", source="OSM node/12288437339 ; photo 2025-05 (mât à crosse avec caméra dôme)",
        remarque="doublon possible avec l'objet OSM du même nœud (conservé comme référence)")
    for i, (x, y) in enumerate([(917197.7, 6460412.2), (917199.7, 6460409.4)]):
        add(Point(x, y), "barriere", "balise_J11", id=f"balise_J11_REV_{i + 1}", code="J11", hauteur_m=1.0,
            etat_2026="existant (ortho 2022, zone inchangée)", confiance="moyenne", source="observation reviree_no-08")
    for i, (x, y) in enumerate([(917219.7, 6460385.3), (917221.4, 6460382.8), (917215.8, 6460379.3)]):
        add(Point(x, y), "barriere", "potelet", id=f"potelet_REV_{i + 1}", hauteur_m=1.0,
            etat_2026="existant (ortho 2022, zone inchangée)", confiance="moyenne", source="observation reviree_no-14")
    add(U(-76.0, 5.1), "divers", "totem_PR", id="totem_PR", code="P+R (SMMAG)", hauteur_m=2.8, azimut_deg=AZ_NE_IN,
        texte="P+R PARKING RELAIS → / M", etat_2026="déplacé (déduit) : îlot de 2022 supprimé ; symbole rouge "
        "du plan 2025 en bord de trottoir NO", confiance="faible",
        source="photos 2025-05 (totem en u -38,8 v 3,5, îlot supprimé) ; plan projet 2025 (symbole rouge)")
    add(D(7.6, -37.0), "divers", "armoire", id="armoire_feux_VERC", hauteur_m=1.5,
        etat_2026="existant (photo 2025-01 ; OSM node/12507622174)", confiance="moyenne",
        source="observation p2025_01_vercors-24 (armoire de commande des feux probable)",
        remarque="même objet que l'armoire OSM 12507622174")
    # dédoublonnage : objets OSM repris explicitement ci-dessus
    drop = {"armoire_12507622174", "mat_camera_12288437339"}
    feats = [(g, p) for g, p in feats if p.get("id") not in drop]
    for g, p in feats:
        if g.geom_type == "Point":
            z = ter.z(g.x, g.y)
            X, Y, Z = loc(g.x, g.y, z)
            p.update(x_local=X, y_local=Y, z_local=Z, z_sol_ngf=round(z, 2))
            p.setdefault("azimut_deg", None)
            p["yaw_deg"] = yaw_from_az(p["azimut_deg"]) if p.get("azimut_deg") is not None else None
    log(f"  {len(feats)} objets : {dict(Counter(p['type'] for g, p in feats))}")
    return feats
