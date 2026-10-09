#!/usr/bin/env python3
"""Atelier « Relief » — carrefour Paquet Jardin (Meylan) : sol nu, chaussée lissée, bordures,
heightmaps pour Houdini 22 / Unreal 5.8.

Exécution (depuis la racine du dépôt) :  python3 recon/stages/relief.py [--cache DIR]
Sorties : recon/out/paquet_jardin/relief/   (voir README_relief.md produit dans ce dossier)

Grille commune (toutes les sorties raster) : 3025 x 3025 nœuds au pas de 0,10 m CENTRÉS sur
l'origine locale O = (917279.43, 6460289.98) : x = 917279.43 + 0.1 k, y = 6460289.98 + 0.1 k,
k = -1512..1512 (emprise 917128.18..917430.68 x 6460138.73..6460441.23, soit l'emprise de 300 m
+ 1,25 m de marge). Le nœud central est exactement O ; 3025 = 63 x 2 x 24 + 1 est une taille
de Landscape Unreal valide (63 quads/section, 2x2 sections/composant, 24x24 composants).

Méthode (résumé ; détails et chiffres dans relief_stats.json) :
 1. Points sol : nuage COPC LiDAR HD 2021 (classe 2), lignes de vol 2021 seules (psid 7020,
    7208-7211 ; points de remplissage 2011/2019 écartés), correction des décalages verticaux
    entre bandes (référence 7209), rejet des points isolés (> 5 cm au-delà du 2e voisin le plus
    bas / haut sur 10 voisins), débruitage bilatéral (σ 0,25 m / 3 cm) qui conserve les
    ressauts de bordure, puis interpolation TIN linéaire -> dtm_sol_10cm.tif (état 2021).
 2. Masques 2026 : chaussée 2026 par propagation depuis les axes OSM, barrières = bordures GAM
    (levé postérieur aux travaux au cœur), îlots/terre-plein 2026 (plan projet + géométrie
    d'analyse), ressauts LiDAR hors zone des travaux ; zone des travaux C1 2025.
 3. Chaussée lissée : régression locale linéaire pondérée (convolution normalisée d'ordre 1,
    multi-échelle 0,6 / 1,5 / 4 m) sur les points de chaussée conservée, robuste (rejet
    asymétrique des points au-dessus de la surface : bordures, îlots 2021 supprimés) ->
    chaussee_lisse_10cm.tif (NaN hors chaussée 2026).
 4. Sol 2026 : MNT 2021 + chaussée lissée + zones refaites en 2025 (anciens îlots arasés au
    niveau chaussée, nouvelles zones vertes / refuges / trottoirs au niveau trottoir) ->
    dtm_2026_10cm.tif, puis heightmaps PNG 16 bits (3025 px @ 10 cm, 2017 px @ 15 cm) + JSON.
 5. Bordures : hauteur de vue (dessus - fil d'eau) par tronçon de 1 m sur les profils LiDAR,
    abaissés aux traversées, hauteurs standard 'estimee' pour les bordures créées en 2025.
 6. Contrôles : profils en long / en travers comparés aux valeurs vérifiées
    (analysis/paquet_jardin/verification/lidar_historique.json), ombrages, tuiles QA 5 cm.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy import ndimage as ndi
from scipy.spatial import Delaunay, cKDTree
from scipy.interpolate import LinearNDInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common_recon import (BBOX, O, OUT, REPO, SITE_DATA, l93_to_uv, load_site_vector,  # noqa: E402
                          ortho_tile, read_layer, uv_to_l93, write_layer)

OUTD = OUT / "relief"
QAD = OUTD / "qa"
COPC = REPO / "data" / "raw" / "lidar" / "npl" / "LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz"
VERIF = REPO / "analysis" / "paquet_jardin" / "verification" / "lidar_historique.json"
ETAT = SITE_DATA / "etat_2026"
AGENT = REPO / "analysis" / "paquet_jardin" / "etat_actuel_agent.geojson"
PLAN = SITE_DATA / "plan_projet_2025" / "plan_L93.tif"

RES = 0.10
K = 1512                       # demi-taille de la grille en nœuds
N = 2 * K + 1                  # 3025
HALF = K * RES + RES / 2       # 151.25 m (bord des pixels)
GT = from_origin(O[0] - HALF, O[1] + HALF, RES, RES)
MARGIN = 8.0                   # marge de lecture des points autour de la grille (m)
PSID_2021 = (7020, 7208, 7209, 7210, 7211)
PSID_REF = 7209

STATS: dict = {}
CACHE: Path | None = None


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def node_xy():
    """Coordonnées locales (m) des nœuds : X croissant vers l'E (colonnes), Y décroissant (lignes)."""
    v = (np.arange(N) - K) * RES
    return v, v[::-1]


def cached(name, fn):
    """Cache npz optionnel (--cache) pour itérer vite ; sans cache tout est recalculé."""
    if CACHE is not None:
        p = CACHE / f"{name}.npz"
        if p.exists():
            d = np.load(p, allow_pickle=False)
            return {k: d[k] for k in d.files}
    out = fn()
    if CACHE is not None:
        np.savez(CACHE / f"{name}.npz", **out)
    return out


def write_tif(path, arr, nodata=np.nan, desc=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", width=N, height=N, count=1, dtype="float32",
                       crs="EPSG:2154", transform=GT, nodata=nodata, compress="deflate",
                       predictor=3, tiled=True, blockxsize=256, blockysize=256) as w:
        w.write(arr.astype(np.float32), 1)
        w.update_tags(VERTICAL_CRS="NGF-IGN69 (EPSG:5720)", UNITS="m",
                      GRID="noeuds centres sur O=(917279.43,6460289.98), pas 0.1 m",
                      DESCRIPTION=desc or "")


# =========================================================================================
# 1. Points sol LiDAR 2021
# =========================================================================================
def load_ground_points():
    import laspy
    from laspy import Bounds, CopcReader
    h = HALF + MARGIN
    with CopcReader.open(COPC) as r:
        pts = r.query(bounds=Bounds(mins=np.array([O[0] - h, O[1] - h]),
                                    maxs=np.array([O[0] + h, O[1] + h])))
    cls = np.asarray(pts.classification)
    ps = np.asarray(pts.point_source_id)
    g = cls == 2
    n_all, n_g = len(cls), int(g.sum())
    keep = g & np.isin(ps, PSID_2021)
    x = np.asarray(pts.x)[keep] - O[0]
    y = np.asarray(pts.y)[keep] - O[1]
    z = np.asarray(pts.z)[keep].astype(np.float64)
    ps = ps[keep]
    it = np.asarray(pts.intensity)[keep]
    STATS["points"] = {"lus": n_all, "classe2": n_g, "classe2_vols2021": int(keep.sum()),
                       "ecartes_hors_2021": int(n_g - keep.sum())}
    # ---- décalages verticaux entre bandes (réf. 7209), sur mailles de 1 m planes
    res = 1.0
    ix = np.floor((x + h) / res).astype(np.int64)
    iy = np.floor((y + h) / res).astype(np.int64)
    W = int(ix.max()) + 1
    key = iy * W + ix
    sel = ps == PSID_REF
    kk, zz = key[sel], z[sel]
    o = np.lexsort((zz, kk))
    kk, zz = kk[o], zz[o]
    u, st, cnt = np.unique(kk, return_index=True, return_counts=True)
    med = zz[st + cnt // 2]
    q1, q3 = zz[st + cnt // 4], zz[st + (3 * cnt) // 4]
    ok = (cnt >= 6) & ((q3 - q1) <= 0.02)
    medmap = np.full(int(key.max()) + 1, np.nan)
    medmap[u[ok]] = med[ok]
    offs = {PSID_REF: 0.0}
    from scipy import stats as sst
    for s in PSID_2021:
        if s == PSID_REF:
            continue
        m = ps == s
        dd = z[m] - medmap[key[m]]
        dd = dd[np.isfinite(dd)]
        offs[s] = float(sst.trim_mean(dd, 0.2)) if len(dd) > 1000 else 0.0
    for s, off in offs.items():
        z[ps == s] -= off
    STATS["decalages_bandes_cm"] = {str(k): round(v * 100, 2) for k, v in offs.items()}
    log("décalages de bande (cm, réf 7209) :", STATS["decalages_bandes_cm"])
    # ---- rejet des points isolés (bruit, objets bas mal classés), bords de bordure conservés
    P = np.c_[x, y]
    tr = cKDTree(P)
    dist, idx = tr.query(P, k=11)
    nz = np.sort(z[idx[:, 1:]], axis=1)
    lo = z < nz[:, 1] - 0.05
    hi = z > nz[:, -2] + 0.05
    far = dist[:, 3] > 1.5                          # point quasi seul dans 1,5 m : douteux
    bad = lo | hi
    STATS["points"]["rejet_isoles_bas"] = int(lo.sum())
    STATS["points"]["rejet_isoles_hauts"] = int(hi.sum())
    STATS["points"]["isoles_conserves_loin"] = int((far & ~bad).sum())
    k = ~bad
    x, y, z, ps, it = x[k], y[k], z[k], ps[k], it[k]
    # ---- bruit résiduel (plans locaux de 1 m) pour les statistiques
    log(f"points sol 2021 retenus : {len(x)} (rejets {int(bad.sum())})")
    return {"x": x, "y": y, "z": z, "ps": ps.astype(np.uint16), "it": it.astype(np.uint16)}


def bilateral_points(x, y, z, sig_s=0.25, sig_r=0.03, rad=0.6, k=16, iters=2):
    """Débruitage bilatéral des points (préserve les ressauts > ~8 cm)."""
    P = np.c_[x, y]
    tr = cKDTree(P)
    dist, idx = tr.query(P, k=k, distance_upper_bound=rad)
    valid = np.isfinite(dist)
    idx = np.where(valid, idx, 0)
    dist = np.where(valid, dist, 0)
    zz = z.copy()
    for _ in range(iters):
        nz = zz[idx]
        w = np.exp(-dist ** 2 / (2 * sig_s ** 2)) * np.exp(-(nz - zz[:, None]) ** 2 / (2 * sig_r ** 2)) * valid
        zz = (w * nz).sum(1) / w.sum(1)
    return zz


def tin_grid(x, y, z):
    tri = Delaunay(np.c_[x, y])
    f = LinearNDInterpolator(tri, z)
    X, Y = node_xy()
    out = np.empty((N, N), np.float32)
    for r0 in range(0, N, 500):                      # par bandes (mémoire)
        XX, YY = np.meshgrid(X, Y[r0:r0 + 500])
        out[r0:r0 + 500] = f(XX, YY)
    return out


def support_distance(x, y):
    """Distance (m) de chaque nœud au point sol le plus proche (trous : bâtiments, véhicules)."""
    tr = cKDTree(np.c_[x, y])
    X, Y = node_xy()
    out = np.empty((N, N), np.float32)
    for r0 in range(0, N, 500):
        XX, YY = np.meshgrid(X, Y[r0:r0 + 500])
        d, _ = tr.query(np.c_[XX.ravel(), YY.ravel()], k=1)
        out[r0:r0 + 500] = d.reshape(XX.shape)
    return out


def step_dtm_sol():
    g = cached("ground", load_ground_points)
    x, y, z = g["x"], g["y"], g["z"]

    def _f():
        zb = bilateral_points(x, y, z)
        log("débruitage bilatéral : écart-type de la correction %.1f cm" % (np.std(zb - z) * 100))
        dtm = tin_grid(x, y, zb)
        sd = support_distance(x, y)
        return {"zb": zb, "dtm": dtm, "sd": sd}
    d = cached("dtm_sol", _f)
    STATS["dtm_sol"] = {"correction_bilaterale_ecart_type_cm": round(float(np.std(d["zb"] - z)) * 100, 2),
                        "noeuds_sans_point_a_moins_de_0p5m_pct": round(float((d["sd"] > 0.5).mean()) * 100, 2),
                        "noeuds_sans_point_a_moins_de_2m_pct": round(float((d["sd"] > 2.0).mean()) * 100, 2),
                        "nan": int(np.isnan(d["dtm"]).sum())}
    return g, d



# =========================================================================================
# 2. Masques : plan projet 2025, chaussée 2026, zone des travaux
# =========================================================================================
P_NONE, P_MASK, P_PHOTO, P_GREY, P_GREEN, P_GDARK, P_NOUE = range(7)


def plan_classes():
    """Aplats du plan projet 2025 géoréférencé (plan_L93.tif) rééchantillonnés sur la grille.
    P_GREY : aplat minéral (trottoir, cheminement, quai, refuge) ; P_GREEN / P_GDARK / P_NOUE :
    massifs plantés, terre-plein planté, noue ; P_PHOTO : fond de plan = ortho 2022 (inchangé ou
    chaussée) ; P_MASK : hors projet (aplats noirs / blancs du panneau)."""
    from rasterio.warp import Resampling, reproject
    rgb = np.zeros((3, N, N), np.uint8)
    inside = np.zeros((N, N), np.uint8)
    with rasterio.open(PLAN) as r:
        for b in range(3):
            reproject(rasterio.band(r, b + 1), rgb[b], dst_transform=GT, dst_crs="EPSG:2154",
                      resampling=Resampling.nearest)
        reproject(np.ones((r.height, r.width), np.uint8), inside, src_transform=r.transform,
                  src_crs=r.crs, dst_transform=GT, dst_crs="EPSG:2154", resampling=Resampling.nearest)
    im = np.transpose(rgb, (1, 2, 0)).astype(np.int16)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    mx, mn = im.max(2), im.min(2)
    val = im.mean(2)
    loc_std = np.sqrt(np.maximum(ndi.uniform_filter(val ** 2, 5) - ndi.uniform_filter(val, 5) ** 2, 0))
    grey = (mx - mn <= 8) & (mn >= 205) & (mx <= 235) & (loc_std < 3.5)
    glight = (G >= 225) & (R >= 120) & (R <= 200) & (B <= 150) & (G - R >= 45)
    ygreen = (G >= 225) & (R >= 195) & (R <= 235) & (B >= 90) & (B <= 150)
    gdark = (R <= 50) & (G >= 140) & (G <= 215) & (B <= 50)
    black = mx < 25
    white = mn >= 248
    pc = np.full((N, N), P_PHOTO, np.uint8)
    for code, m in ((P_GREY, grey), (P_GREEN, glight), (P_GDARK, gdark), (P_NOUE, ygreen)):
        pc[m] = code
    for m in (black, white):
        lab, n = ndi.label(m)
        if n:
            sz = ndi.sum(m, lab, index=np.arange(1, n + 1))
            big = np.zeros(n + 1, bool)
            big[1:] = sz > 400
            pc[big[lab]] = P_MASK
    pc[inside == 0] = P_NONE
    out = pc.copy()
    drawn = pc >= P_GREY
    for code in (P_GREY, P_GREEN, P_GDARK, P_NOUE):     # efface textes / symboles / traits fins
        m = ndi.binary_closing(pc == code, structure=np.ones((3, 3)), iterations=3)
        m = ndi.binary_opening(m, iterations=2)
        out[m & ((pc == P_PHOTO) | (pc == code) | drawn)] = code
    # petites taches isolées (< 1 m²) : bruit de couleur du fond photo
    for code in (P_GREY, P_GREEN, P_GDARK, P_NOUE):
        m = out == code
        lab, n = ndi.label(m)
        if n:
            sz = ndi.sum(m, lab, index=np.arange(1, n + 1))
            small = np.zeros(n + 1, bool)
            small[1:] = sz < 100
            out[small[lab] & m] = P_PHOTO
    return out


def rasterize_geoms(geoms, width=0.0, all_touched=True):
    from rasterio.features import rasterize
    shp = []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        gg = g.buffer(width / 2, cap_style="flat") if width > 0 else g
        if not gg.is_empty:
            shp.append((gg, 1))
    if not shp:
        return np.zeros((N, N), bool)
    return rasterize(shp, out_shape=(N, N), transform=GT, dtype="uint8", all_touched=all_touched).astype(bool)


def load_agent_polys(ids):
    from shapely.geometry import shape
    from common_recon import wgs_geom_to_l93
    fc = json.loads(AGENT.read_text())
    out = {}
    for f in fc["features"]:
        if f["properties"]["id"] in ids:
            out[f["properties"]["id"]] = (wgs_geom_to_l93(shape(f["geometry"])), f["properties"])
    return out


def lidar_edges(dtm):
    """Ressauts LiDAR 2021 : amplitude locale > 7 cm sur 0,5 m et pente locale > 15 %."""
    zs = ndi.uniform_filter(dtm.astype(np.float64), 3)
    gy, gx = np.gradient(zs, RES)
    slope = np.hypot(gx, gy)
    rng = ndi.maximum_filter(dtm, 5) - ndi.minimum_filter(dtm, 5)
    return (rng > 0.07) & (slope > 0.15)


ROAD_HW = {"primary": 10.0, "secondary": 10.0, "tertiary": 9.0, "residential": 7.0,
           "unclassified": 7.0, "primary_link": 7.0, "tertiary_link": 7.0}
U_MAX_TRAVAUX = 12.0   # au-delà (Verdun NE, branche inchangée) on garde les îlots du LiDAR 2021


def uv_grid():
    X, Y = node_xy()
    XX, YY = np.meshgrid(X, Y)
    return 0.70710678 * (XX + YY), 0.70710678 * (YY - XX)


def load_lines(name):
    """Couche linéaire GAM (etat_2026 en L93 si présente, sinon vecteur du site)."""
    p = ETAT / f"{name}_L93.geojson"
    if p.exists():
        return [g for g, _ in read_layer(p)]
    return [g for g, _ in load_site_vector(f"gam_topo_sol_{name}")]


def step_masks(dtm):
    """Chaussée 2026, zone des travaux, zones surélevées 2026, barrières."""
    def _f():
        pc = plan_classes()
        edges = lidar_edges(dtm)
        kerbs = load_lines("bordure_lin")
        lrev = load_lines("limite_revetement_lin")
        other = [g for n in ("gam_topo_sol_talus_haut_lin", "gam_topo_sol_talus_bas_lin",
                             "gam_topo_sol_escalier_rampe_lin", "gam_topo_sol_clotures_lin")
                 for g, _ in load_site_vector(n)]
        ag = load_agent_polys(["etat-08", "etat-09", "etat-26"])
        kb = rasterize_geoms(kerbs, 0.2)
        agp = rasterize_geoms([g for g, _ in ag.values()])
        agb = rasterize_geoms([g.boundary for g, _ in ag.values()], 0.2)
        # zone des travaux C1 2025 : emprise utile du plan projet (hors masques du panneau)
        W = ndi.binary_opening(pc >= P_PHOTO, iterations=3)
        U, V = uv_grid()
        RZ = W & (U < U_MAX_TRAVAUX)          # zone où des îlots 2021 ont pu disparaître
        raised_plan = pc >= P_GREY
        raised26 = raised_plan | agp
        lines26 = kb | agb | rasterize_geoms(other, 0.2) | (raised_plan ^ ndi.binary_erosion(raised_plan))
        dist26 = ndi.distance_transform_edt(~lines26) * RES
        removed_edges = edges & RZ & (dist26 > 0.7)
        edges_keep = edges & ~removed_edges
        lrev_out = rasterize_geoms(lrev, 0.2) & ~W
        bar = kb | agb | raised26 | edges_keep | lrev_out
        # propagation depuis les axes OSM des voies circulées publiques
        from shapely.geometry import box
        bb = box(*BBOX).buffer(25)
        seedg, corr = [], []
        for g, p in load_site_vector("osm_roads"):
            h = p.get("highway")
            if h in ROAD_HW and g.intersects(bb):
                seedg.append(g)
                corr.append(g.buffer(ROAD_HW[h]))
        seed = rasterize_geoms(seedg, 0.3) & ~bar
        cor = rasterize_geoms(corr)
        free = cor & ~bar
        lab, n = ndi.label(free)
        ids = np.unique(lab[seed])
        ids = ids[ids > 0]
        road = np.isin(lab, ids)
        # trous < 4 m² (regards, bruit) rebouchés ; la chaussée rejoint l'axe des bordures (1 px)
        holes = ndi.binary_fill_holes(road) & ~road
        lab2, n2 = ndi.label(holes)
        if n2:
            sz = ndi.sum(holes, lab2, np.arange(1, n2 + 1))
            small = np.zeros(n2 + 1, bool)
            small[1:] = sz < 400
            road |= small[lab2]
        road |= ndi.binary_dilation(road) & (kb | agb) & ~agp
        return {"pc": pc, "edges": edges, "removed_edges": removed_edges, "W": W, "RZ": RZ,
                "raised26": raised26, "road": road, "bar": bar}
    m = cached("masks", _f)
    STATS["masques"] = {"chaussee_2026_m2": round(float(m["road"].sum()) * RES * RES, 1),
                        "zone_travaux_m2": round(float(m["W"].sum()) * RES * RES, 1),
                        "zones_surelevees_plan_m2": round(float(m["raised26"].sum()) * RES * RES, 1),
                        "ressauts_2021_supprimes_px": int(m["removed_edges"].sum())}
    return m


# =========================================================================================
# 3. Chaussée lissée : régression locale linéaire robuste, multi-échelle
# =========================================================================================
SCALES = ((0.5, 1), (1.2, 2), (3.0, 5), (8.0, 10))     # (sigma m, décimation)


def _blocksum(A, s):
    if s == 1:
        return A
    n = int(np.ceil(N / s)) * s
    P = np.zeros((n, n), A.dtype)
    P[:N, :N] = A
    return P.reshape(n // s, s, n // s, s).sum(axis=(1, 3))


def _upsample(A, s):
    if s == 1:
        return A
    r = (np.arange(N) - (s - 1) / 2) / s
    R, C = np.meshgrid(r, r, indexing="ij")
    return ndi.map_coordinates(A, [R, C], order=1, mode="nearest")


def lin_fit(Wt, WZ, sigma, s):
    """Ajustement local z = a + b dx + c dy pondéré par une gaussienne (σ en m) ; renvoie
    (a, n_eff, conditionnement) sur la grille complète. Décimation s pour les grandes échelles."""
    from scipy.ndimage import correlate1d
    w, wz = _blocksum(Wt, s), _blocksum(WZ, s)
    step = RES * s
    r = int(np.ceil(3 * sigma / step))
    d = np.arange(-r, r + 1) * step
    g0 = np.exp(-0.5 * (d / sigma) ** 2)
    g1, g2 = g0 * d, g0 * d * d

    def C(A, kx, ky):
        return correlate1d(correlate1d(A, kx, axis=1, mode="constant"), ky, axis=0, mode="constant")
    S0, Sx, Sy = C(w, g0, g0), C(w, g1, g0), C(w, g0, -g1)
    Sxx, Syy, Sxy = C(w, g2, g0), C(w, g0, g2), C(w, g1, -g1)
    Sz, Sxz, Syz = C(wz, g0, g0), C(wz, g1, g0), C(wz, g0, -g1)
    det = S0 * (Sxx * Syy - Sxy ** 2) - Sx * (Sx * Syy - Sxy * Sy) + Sy * (Sx * Sxy - Sxx * Sy)
    deta = Sz * (Sxx * Syy - Sxy ** 2) - Sx * (Sxz * Syy - Sxy * Syz) + Sy * (Sxz * Sxy - Sxx * Syz)
    with np.errstate(invalid="ignore", divide="ignore"):
        cond = det / np.maximum(S0 * Sxx * Syy, 1e-30)
        a1 = deta / det
        a0 = Sz / S0
    a1 = np.where(np.isfinite(a1), a1, a0)
    # repli sur l'ordre 0 (moyenne pondérée) quand la configuration est mal conditionnée
    t = np.clip((cond - 0.02) / 0.08, 0, 1)
    t = np.where(np.isfinite(t), t, 0.0)
    a = t * a1 + (1 - t) * a0
    a = np.where(S0 > 1e-6, a, np.nan)
    return _upsample(np.nan_to_num(a, nan=0.0), s), _upsample(S0, s), _upsample(cond, s)


def multiscale_fit(Wt, WZ):
    """Fusion des échelles : la plus fine qui a assez de points (n_eff) l'emporte."""
    Z = None
    for sigma, s in reversed(SCALES):
        a, n, cond = lin_fit(Wt, WZ, sigma, s)
        if Z is None:
            Z = np.where(n > 0.5, a, np.nan)
            continue
        alpha = np.clip((n - 6.0) / 10.0, 0, 1) * np.clip((cond - 0.02) / 0.08, 0, 1)
        Z = np.where(np.isnan(Z), np.where(n > 0.5, a, np.nan), alpha * a + (1 - alpha) * Z)
    return Z


def points_to_nodes(x, y):
    c = np.rint(x / RES).astype(np.int64) + K
    r = K - np.rint(y / RES).astype(np.int64)
    ok = (c >= 0) & (c < N) & (r >= 0) & (r < N)
    return r, c, ok


def step_chaussee(g, masks, dtm):
    """Surface de roulement lissée sur la chaussée 2026 (+ prolongement sous les zones refaites,
    utilisé pour poser les nouveaux îlots / trottoirs).
    Passe 1 : ajustement robuste sur tous les points du masque de chaussée provisoire.
    Ensuite : les reliefs > 5 cm au-dessus de la surface (anciens îlots 2021, bordures, débords
    du masque sur un trottoir) sont exclus avec une marge de 0,4 m ; hors zone des travaux, ces
    reliefs sont aussi retirés du masque de chaussée (ce sont des trottoirs / îlots existants)."""
    road0, RZ = masks["road"], masks["RZ"]

    def _f():
        x, y, z = g["x"], g["y"], g["z"]
        r, c, ok = points_to_nodes(x, y)
        inroad = np.zeros(len(x), bool)
        inroad[ok] = road0[r[ok], c[ok]]
        idx = np.where(inroad)[0]
        rr, cc, zz = r[idx], c[idx], z[idx]
        w = np.ones(len(idx))
        excl = np.zeros(len(idx), bool)
        hist = []
        inner = ndi.binary_erosion(road0, iterations=3)
        for it in range(5):
            Wt = np.zeros((N, N))
            WZ = np.zeros((N, N))
            ww = np.where(excl, 0.0, w)
            np.add.at(Wt, (rr, cc), ww)
            np.add.at(WZ, (rr, cc), ww * zz)
            Z = multiscale_fit(Wt, WZ)
            res = zz - Z[rr, cc]
            # pondération robuste (bisquare, c = 7 cm ≈ 3 σ du bruit)
            u = np.abs(res) / 0.07
            w = np.where(u < 1, (1 - u ** 2) ** 2, 0.0)
            if it == 0:
                H = dtm - Z
                raised = ndi.binary_dilation((H > 0.05) & inner, iterations=4)
                excl = raised[rr, cc]
            hist.append({"iter": it, "points": int(len(idx)), "exclus_reliefs": int(excl.sum()),
                         "poids_nuls": int((w == 0).sum()),
                         "residu_mediane_abs_cm": round(float(np.median(np.abs(res[~excl]))) * 100, 2)})
            log(f"chaussée itération {it} : {hist[-1]}")
        H = dtm - Z
        stay_raised = (H > 0.06) & ~RZ & road0
        stay_raised = ndi.binary_opening(stay_raised, iterations=2)
        stay_raised = ndi.binary_dilation(stay_raised, iterations=1) & road0
        road = road0 & ~stay_raised
        lab, n = ndi.label(road)
        if n > 1:
            sz = ndi.sum(road, lab, np.arange(1, n + 1))
            road = np.isin(lab, np.where(sz >= 2000)[0] + 1)     # îlots de chaussée < 20 m² : supprimés
        good = (w > 0.5) & ~excl
        return {"Z": Z.astype(np.float32), "road": road, "res": res.astype(np.float32), "good": good,
                "rr": rr.astype(np.int32), "cc": cc.astype(np.int32), "hist": json.dumps(hist)}
    d = cached("chaussee", _f)
    res, good = d["res"], d["good"]
    STATS["chaussee_lisse"] = {
        "iterations": json.loads(str(d["hist"])),
        "chaussee_2026_m2": round(float(d["road"].sum()) * RES * RES, 1),
        "points_chaussee_retenus": int(good.sum()),
        "residus_points_retenus_cm": {"ecart_type": round(float(np.std(res[good])) * 100, 2),
                                      "mediane": round(float(np.median(res[good])) * 100, 2),
                                      "p05": round(float(np.percentile(res[good], 5)) * 100, 2),
                                      "p95": round(float(np.percentile(res[good], 95)) * 100, 2)}}
    return d


# =========================================================================================
# Outils de rendu QA (tuiles 1000 x 1000 px à 5 cm, coin bas-gauche (tx, ty))
# =========================================================================================
def to_tile(A, tx, ty, order=1):
    """Échantillonne une grille (N x N, nœuds O + 0,1 k) aux centres des pixels 5 cm de la tuile."""
    i = np.arange(1000)
    xs = tx + 0.025 + 0.05 * i - O[0]
    ys = ty + 50 - 0.025 - 0.05 * i - O[1]
    cc = xs / RES + K
    rr = K - ys / RES
    R, C = np.meshgrid(rr, cc, indexing="ij")
    return ndi.map_coordinates(A, [R, C], order=order, mode="nearest")


def hillshade(Z, res=0.05, ex=4.0):
    gy, gx = np.gradient(Z * ex, res)
    dzdx, dzdy = gx, -gy
    out = 0
    for az, alt, w in ((315, 45, 0.55), (45, 50, 0.25), (200, 40, 0.20)):
        a, b = np.radians(az), np.radians(alt)
        L = np.array([np.sin(a) * np.cos(b), np.cos(a) * np.cos(b), np.sin(b)])
        out = out + w * np.clip((-dzdx * L[0] - dzdy * L[1] + L[2]) / np.sqrt(dzdx ** 2 + dzdy ** 2 + 1), 0, 1)
    return out


# =========================================================================================
def main():
    global CACHE
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", help="dossier de cache npz (facultatif)")
    ap.add_argument("--steps", default="all")
    a = ap.parse_args()
    if a.cache:
        CACHE = Path(a.cache)
        CACHE.mkdir(parents=True, exist_ok=True)
    OUTD.mkdir(parents=True, exist_ok=True)
    QAD.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    g, d = step_dtm_sol()
    write_tif(OUTD / "dtm_sol_10cm.tif", d["dtm"],
              desc="Sol nu 2021 (LiDAR HD classe 2, vols 2021, TIN sur points debruites)")
    log("dtm_sol écrit", time.time() - t0)
    m = step_masks(d["dtm"])
    log("masques", STATS["masques"])
    ch = step_chaussee(g, m, d["dtm"])
    log("chaussée", STATS["chaussee_lisse"])


if __name__ == "__main__":
    main()
