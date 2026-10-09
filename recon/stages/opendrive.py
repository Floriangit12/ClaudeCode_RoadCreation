#!/usr/bin/env python3
"""Atelier « Réseau routier OpenDRIVE état 2026 » — carrefour Paquet Jardin (Meylan).

Produit le réseau routier ASAM OpenDRIVE 1.7 du carrefour avenue de Verdun (RD1090) /
chemin de la Revirée / avenue du Vercors, dans l'état d'octobre 2026 (après les travaux C1
de 2025), en repère local (origine O de recon/CONVENTIONS.md), avec :
  - 4 routes à sens unique pour l'avenue de Verdun (chaussées séparées, ligne de référence sur
    le bord intérieur = faîte du toit à deux pans), 1 route à double sens pour la Revirée (1+1),
    1 route à double sens pour l'avenue du Vercors (2 entrantes + 1 sortante, îlot en goutte d'eau),
  - une jonction avec une route de liaison par manœuvre autorisée (flèches du plan projet 2025,
    levés GAM, OSM 2026 ; le tourne-à-droite Verdun -> Vercors se fait depuis la voie droite),
  - types de voies driving / median / curb / sidewalk / biking (piste bidirectionnelle) / border,
  - largeurs mesurées sur les levés GAM (marquages et bordures) / PCRS / ortho 2022,
  - roadMark (continu / discontinu T1-T3, couleur, largeur),
  - élévation et dévers (superelevation) mesurés sur le MNT LiDAR HD 2021 (contrôlés contre
    analysis/paquet_jardin/verification/lidar_historique.json), profil en travers à deux pans
    (lateralProfile/shape) sur la Revirée et le Vercors,
  - objets crosswalk (passages piétons et traversées cyclables), lignes d'effet des feux,
    îlots, arrêts de bus « La Revirée », signaux (feux tricolores par approche, feux piétons,
    feux cyclistes, panneaux d'arrêt de bus), contrôleurs.

Exécution (depuis la racine du dépôt) :  python3 recon/stages/opendrive.py
Sorties : recon/out/paquet_jardin/opendrive/
  paquet_jardin_2026.xodr        réseau OpenDRIVE (repère local, geoReference EPSG:2154 + offset)
  manoeuvres_2026.json           résumé lisible des manœuvres (voies d'entrée/sortie, routes de liaison)
  validation_2026.json           contrôles : écarts bords de voies / levés, connectivité, continuité,
                                 auto-intersections, élévation, dévers, validation ASAM QC (si dispo)
  lanes_2026.geojson             géométrie des voies reconstruite depuis le .xodr (L93, contrôle)
  bordures_mesurees_2026.geojson bordures de voies mesurées (L93) servant à l'ajustement
  qa/qa_<X>_<Y>.jpg              rendus 1000x1000 à 5 cm sur l'ortho 2022 (toute l'emprise routière)
  qa/plan_<X>_<Y>.jpg            rendus sur le plan projet 2025 géoréférencé (cœur)
Options : --variante-traversee-sw-2022  (traversées SW à u=-18,6 / -16, état OSM/2022)
          --variante-vercors-trident   (voie droite du Vercors : gauche + tout droit + droite)
          --no-qc                      (ne lance pas le contrôleur ASAM QC)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.interpolate import make_smoothing_spline
from shapely import STRtree
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box, mapping
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common_recon import (O, OUT, PLAN, REPO, SITE_DATA, TILE, l93_to_uv,  # noqa: E402
                          load_site_vector, ortho_tile, read_layer, uv_to_l93, write_layer)

OUTD = OUT / "opendrive"
QAD = OUTD / "qa"
E26 = SITE_DATA / "etat_2026"
DTM = REPO / "data" / "raw" / "lidar" / "paquet_jardin" / "dtm_15cm.tif"
VERIF = REPO / "analysis" / "paquet_jardin" / "verification" / "lidar_historique.json"
XODR_NAME = "paquet_jardin_2026.xodr"
HALF = 150.0
EMPRISE = box(O[0] - HALF, O[1] - HALF, O[0] + HALF, O[1] + HALF)
EPSG2154_PROJ = ("+proj=lcc +lat_0=46.5 +lon_0=3 +lat_1=49 +lat_2=44 +x_0=700000 +y_0=6600000 "
                 "+ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +type=crs")


def log(*a):
    print("[opendrive]", *a, flush=True)


# =============================================================================================
# 1. Repères de mesure et données sources
# =============================================================================================
class Frame:
    """Repère plan (a le long de l'axe d'angle ang depuis l'Est, b à gauche)."""

    def __init__(self, name, origin, ang_deg):
        self.name = name
        self.ox, self.oy = origin
        self.ang = math.radians(ang_deg)
        self.c, self.s = math.cos(self.ang), math.sin(self.ang)

    def ab2xy(self, a, b):
        a = np.asarray(a, float); b = np.asarray(b, float)
        return self.ox + a * self.c - b * self.s, self.oy + a * self.s + b * self.c

    def xy2ab(self, x, y):
        dx = np.asarray(x, float) - self.ox; dy = np.asarray(y, float) - self.oy
        return dx * self.c + dy * self.s, -dx * self.s + dy * self.c


# Verdun : repère u/v de l'analyse (x = 917279.43 + 0.7071(u - v), y = 6460289.98 + 0.7071(u + v))
FV = Frame("verdun_uv", (O[0], O[1]), 45.0)
FR = Frame("reviree", tuple(uv_to_l93(3.0, 6.0)), 124.7)      # a vers le NNW, b vers l'WSW
FC = Frame("vercors", tuple(uv_to_l93(-3.0, -10.0)), -76.0)   # a vers le SSE, b vers l'ENE


class Sources:
    """Levés GAM 2026 (marquages M, bordures B), PCRS 2019 (bordures P), ortho 2022, MNT."""

    def __init__(self):
        self.M = [g for g, p in read_layer(E26 / "signalisation_horizontale_lin_L93.geojson")]
        self.B = [g for g, p in read_layer(E26 / "bordure_lin_L93.geojson")]
        self.P = [g for g, p in load_site_vector("gam_limite_voirie_pcrs")]
        self.trees = {k: STRtree(getattr(self, k)) for k in "MBP"}
        with rasterio.open(DTM) as r:
            self.dtm = r.read(1).astype(np.float64)
            self.dtm_tr = r.transform
            nd = r.nodata
        if nd is not None:
            self.dtm[self.dtm == nd] = np.nan
        self._ortho_cache = {}

    # ---- intersections d'un segment transversal avec les levés -----------------------------
    def cut(self, srcs, p0, p1):
        L = LineString([p0, p1])
        out = []
        for k in srcs:
            geoms = getattr(self, k)
            for i in self.trees[k].query(L):
                x = geoms[i].intersection(L)
                for pt in getattr(x, "geoms", [x]):
                    if pt.geom_type == "Point":
                        out.append((pt.x, pt.y, k, int(i)))
        return out

    # ---- MNT ------------------------------------------------------------------------------
    def z(self, x, y, win=0.45):
        """Médiane du MNT 15 cm dans un carré de ±win m (robuste aux petits objets)."""
        x = np.atleast_1d(np.asarray(x, float)); y = np.atleast_1d(np.asarray(y, float))
        offs = np.arange(-win, win + 1e-9, 0.15)
        dx, dy = np.meshgrid(offs, offs)
        X = x[:, None] + dx.ravel()[None, :]; Y = y[:, None] + dy.ravel()[None, :]
        tr = self.dtm_tr
        c = (X - tr.c) / tr.a - 0.5; r = (Y - tr.f) / tr.e - 0.5
        v = ndi.map_coordinates(np.nan_to_num(self.dtm, nan=-9999.0), [r.ravel(), c.ravel()],
                                order=1, cval=-9999.0).reshape(X.shape)
        v[v < 0] = np.nan
        return np.nanmedian(v, axis=1)

    # ---- ortho 2022 (détection de lignes hors zone de travaux) ------------------------------
    def ortho_gray(self, tx, ty):
        key = (tx, ty)
        if key not in self._ortho_cache:
            im = ortho_tile(tx, ty).convert("L")
            self._ortho_cache[key] = np.asarray(im, np.float32)
        return self._ortho_cache[key]

    def ortho_sample(self, X, Y):
        out = np.full(X.shape, np.nan, np.float32)
        tx = (np.floor(X / 50) * 50).astype(int); ty = (np.floor(Y / 50) * 50).astype(int)
        for (a, b) in set(zip(tx.ravel().tolist(), ty.ravel().tolist())):
            m = (tx == a) & (ty == b)
            g = self.ortho_gray(a, b)
            cc = (X[m] - a) / 0.05 - 0.5; rr = (b + 50 - Y[m]) / 0.05 - 0.5
            out[m] = ndi.map_coordinates(g, [rr, cc], order=1, cval=np.nan)
        return out

    def ortho_line(self, frame, a, b_prior, tol=0.6, half_len=4.0, min_peak=16.0):
        """Position b du marquage blanc le plus contrasté près de b_prior (fenêtre ±half_len)."""
        aa = np.arange(a - half_len, a + half_len, 0.1)
        bb = np.arange(b_prior - tol - 0.5, b_prior + tol + 0.5, 0.05)
        A, Bm = np.meshgrid(aa, bb)
        X, Y = frame.ab2xy(A, Bm)
        g = self.ortho_sample(X, Y)
        bg = ndi.median_filter(np.nan_to_num(g, nan=0), size=(15, 1))
        th = g - bg
        prof = np.nanpercentile(th, 85, axis=1)
        prof = ndi.uniform_filter1d(np.nan_to_num(prof, nan=0), 3)
        inside = np.abs(bb - b_prior) <= tol
        if not inside.any():
            return np.nan
        i = np.argmax(np.where(inside, prof, -1e9))
        return float(bb[i]) if prof[i] >= min_peak else np.nan


# =============================================================================================
# 2. Mesure des bordures de voies (bord, axe, ligne de voie, bordure de trottoir)
# =============================================================================================
def _interp_prior(knots, a):
    k = np.asarray(knots, float)
    return np.interp(a, k[:, 0], k[:, 1])


def measure_boundary(S, frame, a_grid, pieces, name=""):
    """pieces : [(a0, a1, src, knots, tol)] ; src ∈ {'M','B','P','MB','BP','MBP','O','C', callable}.
    Retourne (b_lisse, b_mesure, source_par_station)."""
    b_meas = np.full(len(a_grid), np.nan)
    b_prior = np.full(len(a_grid), np.nan)
    srcs = np.array([""] * len(a_grid), dtype=object)
    piece_id = np.full(len(a_grid), -1)
    for j, a in enumerate(a_grid):
        for k, pc in enumerate(pieces):
            a0, a1, src, knots, tol = pc
            if a0 - 1e-9 <= a <= a1 + 1e-9:
                piece_id[j] = k
                if callable(src):
                    b_prior[j] = src(a); b_meas[j] = b_prior[j]; srcs[j] = "F"
                    break
                bp = float(_interp_prior(knots, a))
                b_prior[j] = bp
                if src == "C":
                    b_meas[j] = bp; srcs[j] = "C"
                elif src == "O":
                    b_meas[j] = S.ortho_line(frame, a, bp, tol); srcs[j] = "O" if np.isfinite(b_meas[j]) else ""
                else:
                    p0 = frame.ab2xy(a, bp - tol - 0.01); p1 = frame.ab2xy(a, bp + tol + 0.01)
                    best = None
                    for (x, y, kk, i) in S.cut(list(src), (float(p0[0]), float(p0[1])),
                                              (float(p1[0]), float(p1[1]))):
                        _, bb = frame.xy2ab(x, y)
                        d = abs(float(bb) - bp)
                        if d <= tol and (best is None or d < best[0]):
                            best = (d, float(bb), kk)
                    if best is not None:
                        b_meas[j] = best[1]; srcs[j] = best[2]
                break
    # nettoyage : médiane glissante (pics), comblement par interpolation dans chaque morceau,
    # sinon a priori ; lissage léger (Savitzky-Golay ordre 2, ~5 m).
    b = b_meas.copy()
    for k in range(len(pieces)):
        m = piece_id == k
        if not m.any():
            continue
        idx = np.where(m)[0]
        seg = b[idx]
        ok = np.isfinite(seg)
        if ok.sum() >= 5:
            med = ndi.median_filter(np.where(ok, seg, np.nanmedian(seg[ok])), size=5, mode="nearest")
            bad = ok & (np.abs(seg - med) > 0.25)
            seg[bad] = np.nan; srcs[idx[bad]] = ""
            ok = np.isfinite(seg)
        if ok.sum() >= 2:
            seg[~ok] = np.interp(idx[~ok], idx[ok], seg[ok])
        elif ok.sum() == 1:
            seg[~ok] = seg[ok][0] + (b_prior[idx[~ok]] - b_prior[idx[ok]][0])
        else:
            seg[:] = b_prior[idx]
        b[idx] = seg
    still = ~np.isfinite(b)
    b[still] = b_prior[still]
    bs = _savgol(b, a_grid, 5.0)
    return bs, b_meas, srcs


def _savgol(b, a, win_m):
    from scipy.signal import savgol_filter
    if len(b) < 7:
        return b
    da = np.median(np.diff(a))
    w = int(round(win_m / da)) | 1
    w = max(5, min(w, (len(b) // 2) * 2 - 1))
    return savgol_filter(b, w, 2, mode="interp")
