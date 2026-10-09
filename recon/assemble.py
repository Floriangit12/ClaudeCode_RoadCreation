"""Assemblage du paquet 3D « Paquet Jardin, état octobre 2026 » pour Houdini 22 et Unreal 5.8.

Lit les couches produites par les ateliers (recon/out/paquet_jardin/<atelier>/) et écrit
recon/out/paquet_jardin/package/ (structure décrite dans recon/CONVENTIONS.md) :

  paquet_jardin_2026.usda      scène racine (sous-couches), upAxis Z, metersPerUnit 1, repère local O
  layers/materiaux.usda        matériaux UsdPreviewSurface (macro-albédo + couleurs par classe)
  layers/terrain.usdc          espaces verts, terre-pleins, divers + jupe de bord d'emprise
  layers/voirie.usdc           chaussée, pistes, trottoirs, îlots, quais, parkings (un Mesh par classe)
  layers/bordures.usdc         faces verticales des bordures (hauteur = différence de niveau mesurée)
  layers/marquages.usdc        peinture drapée à +1 cm (un Mesh par couleur x usure, type par face)
  layers/vegetation.usdc       arbres (PointInstancer)
  layers/mobilier.usdc         feux, panneaux, lampadaires, abris... (PointInstancer)
  layers/batiments.usdc        bâtiments LoD1
  textures/                    macro-albédo 8192 px + masques
  paquet_jardin_2026.xodr      OpenDRIVE (copie)
  preview/paquet_jardin_2026.glb   aperçu glTF (Y-up)
  houdini/, unreal/, GUIDE_PC.md  (fichiers maintenus dans recon/package_src/, copiés ici)

Altitudes : surface composite à 10 cm construite à partir du MNT sol LiDAR (atelier relief),
de la surface de roulement lissée sur la chaussée, et des hauteurs de bordure pour les
zones surélevées créées en 2025. Chaque sommet de bord de polygone est échantillonné à 0,2 m
à l'intérieur de son polygone (pas de mélange de niveaux de part et d'autre d'une bordure) ;
une face verticale est créée là où le polygone domine son voisin.

Usage : python3 recon/assemble.py [--no-glb] [--albedo-px 8192]
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio
import shapely
import triangle as tr
import trimesh
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import reproject
from scipy import ndimage
from shapely.geometry import MultiPolygon, Polygon, box, shape
from shapely.geometry.polygon import orient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_recon import BBOX, DTM15, O, OUT, ORTHO5, REPO, read_layer  # noqa: E402

PKG = OUT / "package"
SRC = Path(__file__).resolve().parent / "package_src"
GRID = 0.10                                   # pas de la surface composite (m)
NX = NY = int(round((BBOX[2] - BBOX[0]) / GRID))
GT = from_origin(BBOX[0], BBOX[3], GRID, GRID)
EMPRISE = box(*BBOX)
EMPRISE_IN = EMPRISE.buffer(-0.05, join_style="mitre")
shapely.prepare(EMPRISE_IN)

# --- classes -------------------------------------------------------------------------------
VOIRIE = ["chaussee", "piste_cyclable", "trottoir", "ilot", "quai_bus", "parking", "acces_riverain"]
TERRAIN = ["terre_plein_vegetal", "espace_vert", "chantier", "batiment", "autre"]
CLASSES = VOIRIE + TERRAIN
CODE = {c: i + 1 for i, c in enumerate(CLASSES)}
ROAD_LEVEL = {"chaussee"}                                     # surface de roulement lissée
RAISED = {"trottoir", "ilot", "quai_bus", "terre_plein_vegetal", "espace_vert"}
H_DEFAUT = {"trottoir": 0.14, "ilot": 0.15, "quai_bus": 0.20, "terre_plein_vegetal": 0.15,
            "espace_vert": 0.14}
COULEUR = {  # couleur d'affichage (sRGB 0-1) : matériaux sans texture + aperçu glTF
    "chaussee": (0.20, 0.20, 0.21), "chaussee_2025": (0.13, 0.13, 0.14),
    "piste_cyclable": (0.30, 0.24, 0.22), "trottoir": (0.52, 0.51, 0.48), "ilot": (0.58, 0.57, 0.54),
    "quai_bus": (0.62, 0.61, 0.58), "parking": (0.27, 0.27, 0.27), "acces_riverain": (0.33, 0.32, 0.30),
    "terre_plein_vegetal": (0.24, 0.36, 0.14), "espace_vert": (0.22, 0.34, 0.13),
    "chantier": (0.45, 0.40, 0.33), "batiment": (0.45, 0.43, 0.40), "autre": (0.40, 0.38, 0.34),
    "bordure": (0.66, 0.65, 0.62), "bati": (0.78, 0.74, 0.66), "toit": (0.42, 0.33, 0.30),
    "tronc": (0.30, 0.22, 0.15), "feuillage": (0.18, 0.32, 0.12), "metal": (0.35, 0.37, 0.38),
    "signal": (0.10, 0.10, 0.10), "panneau": (0.85, 0.85, 0.85), "verre": (0.55, 0.65, 0.70),
}
PEINTURE = {"blanc": (0.88, 0.88, 0.86), "jaune": (0.90, 0.75, 0.10), "ocre": (0.80, 0.55, 0.25),
            "vert": (0.25, 0.55, 0.30), "rouge": (0.70, 0.15, 0.12), "bleu": (0.15, 0.30, 0.65)}
OPACITE_USURE = {"0": 0.97, "1": 0.88, "2": 0.68, "3": 0.42, "F": 0.15}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def getp(p, keys, default=None):
    for k in keys:
        v = p.get(k)
        if v not in (None, "", "nan"):
            return v
    return default


def fnum(v, default=None):
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def classe_of(p):
    c = str(getp(p, ["classe", "class"], "autre")).strip().lower()
    return c if c in CODE else "autre"


def modifie_2025(p):
    return "2025" in str(getp(p, ["etat", "state"], "")) or "modif" in str(getp(p, ["etat"], ""))


# --- rasters -------------------------------------------------------------------------------
def load_grid(path, fill=True):
    """Raster quelconque (L93) -> grille 10 cm de l'emprise (float32, NaN = absent)."""
    dst = np.full((NY, NX), np.nan, np.float32)
    with rasterio.open(path) as r:
        reproject(rasterio.band(r, 1), dst, src_transform=r.transform, src_crs=r.crs or "EPSG:2154",
                  src_nodata=r.nodata, dst_transform=GT, dst_crs="EPSG:2154", dst_nodata=np.nan,
                  resampling=Resampling.bilinear)
    dst[(dst < 100) | (dst > 1000)] = np.nan                   # altitudes NGF plausibles
    if fill and np.isnan(dst).any() and not np.isnan(dst).all():
        idx = ndimage.distance_transform_edt(np.isnan(dst), return_distances=False, return_indices=True)
        dst = dst[tuple(idx)]
    return dst


class Surface:
    """Surface composite (altitude finale de chaque classe) + échantillonnage bilinéaire."""

    def __init__(self, surfs, dtm_path, road_path):
        log("surface composite : MNT", dtm_path.relative_to(REPO))
        self.dtm = load_grid(dtm_path)
        road = load_grid(road_path, fill=False) if road_path else np.full_like(self.dtm, np.nan)
        cls = np.zeros((NY, NX), np.uint8)
        shapes = [(g, CODE[classe_of(p)]) for g, p in surfs if not g.is_empty]
        if shapes:
            cls = rasterize(shapes, out_shape=(NY, NX), transform=GT, fill=0, dtype="uint8")
        self.cls = cls
        z = self.dtm.copy()
        has_road = ~np.isnan(road)
        m = (cls == CODE["chaussee"]) & has_road
        z[m] = road[m]
        # niveau de chaussée de référence partout (plus proche voisin) pour les zones créées en 2025
        ref = road if has_road.any() else self.dtm.copy()
        if np.isnan(ref).any() and not np.isnan(ref).all():
            idx = ndimage.distance_transform_edt(np.isnan(ref), return_distances=False, return_indices=True)
            ref = ref[tuple(idx)]
        raised = [(g, float(fnum(getp(p, ["hauteur_bordure_m"]), H_DEFAUT[classe_of(p)])))
                  for g, p in surfs if classe_of(p) in RAISED and modifie_2025(p)]
        if raised:
            h = rasterize([(g, max(0.02, min(0.30, hv))) for g, hv in raised], out_shape=(NY, NX),
                          transform=GT, fill=0.0, dtype="float32")
            mm = h > 0
            # ancien sol au niveau chaussée (bretelle supprimée...) : on remonte au niveau bordure
            low = mm & (self.dtm < ref + 0.5 * h)
            z[low] = ref[low] + h[low]
            log(f"  zones 2025 surélevées : {low.sum() * GRID * GRID:.0f} m²")
        # zones devenues chaussée en 2025 sans surface lissée : niveau de chaussée voisin
        m2 = (cls == CODE["chaussee"]) & ~has_road & (self.dtm > ref + 0.06)
        z[m2] = ref[m2]
        self.z = z.astype(np.float32)

    def sample(self, x, y, arr=None):
        a = self.z if arr is None else arr
        col = (np.asarray(x) - BBOX[0]) / GRID - 0.5
        row = (BBOX[3] - np.asarray(y)) / GRID - 0.5
        return ndimage.map_coordinates(a, [row, col], order=1, mode="nearest")

    def sample_min(self, x, y, r=0.10):
        """Minimum local (évite de prendre le haut d'une bordure voisine pour la peinture)."""
        zs = [self.sample(x + dx, y + dy) for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r))]
        return np.min(zs, axis=0)


class GroundZ:
    """Altitude exacte du maillage de sol final (interpolation barycentrique dans ses triangles) :
    les marquages et objets sont posés sur le maillage, pas sur le raster (pas d'enfoncement)."""

    def __init__(self, meshes):
        Vs, Fs, n = [], [], 0
        for V, F in meshes:
            Vs.append(V)
            Fs.append(F + n)
            n += len(V)
        self.V = np.vstack(Vs)
        self.F = np.vstack(Fs)
        tri = self.V[self.F][:, :, :2]
        self.tree = shapely.STRtree(shapely.polygons(np.concatenate([tri, tri[:, :1]], axis=1)))

    def __call__(self, x, y, fallback):
        x, y = np.asarray(x, float), np.asarray(y, float)
        z = np.array(fallback, float, copy=True)
        ip, it = self.tree.query(shapely.points(np.c_[x, y]), predicate="intersects")
        if len(ip):
            _, first = np.unique(ip, return_index=True)
            ip, it = ip[first], it[first]
            A, B, C = (self.V[self.F[it, k]] for k in range(3))
            v0, v1 = B[:, :2] - A[:, :2], C[:, :2] - A[:, :2]
            v2 = np.c_[x[ip], y[ip]] - A[:, :2]
            den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
            den[np.abs(den) < 1e-12] = 1e-12
            b = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
            c = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
            z[ip] = A[:, 2] + b * (B[:, 2] - A[:, 2]) + c * (C[:, 2] - A[:, 2])
        return z


# --- géométrie -------------------------------------------------------------------------------
def densify_ring(coords, step):
    c = np.asarray(coords, float)[:, :2]
    if len(c) > 1 and np.allclose(c[0], c[-1]):
        c = c[:-1]
    out = []
    n = len(c)
    for i in range(n):
        a, b = c[i], c[(i + 1) % n]
        L = float(np.hypot(*(b - a)))
        k = max(1, int(math.ceil(L / step - 1e-9)))
        for j in range(k):
            out.append(a + (b - a) * (j / k))
    out = np.array(out)
    keep = np.ones(len(out), bool)
    keep[1:] = np.hypot(*(np.diff(out, axis=0).T)) > 1e-4
    return out[keep]


def polys_of(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    if g.geom_type == "MultiPolygon":
        return list(g.geoms)
    if g.geom_type == "GeometryCollection":
        return [p for gg in g.geoms for p in polys_of(gg)]
    return []


def clean_poly(g):
    g = shapely.set_precision(g, 0.001)
    if not g.is_valid:
        g = shapely.make_valid(g)
    return [orient(p, 1.0) for p in polys_of(g) if p.area > 0.01]


def triangulate(poly, step=1.0, max_area=1.0):
    """Triangulation contrainte (triangle) d'un polygone en coordonnées L93.
    Renvoie (V[n,2], F[m,3], rings) ; les sommets de bord densifiés sont les premiers de V,
    dans l'ordre des anneaux (rings = liste de (début, fin) dans V)."""
    rings, verts, segs, holes = [], [], [], []
    for k, ring in enumerate([poly.exterior, *poly.interiors]):
        pts = densify_ring(ring.coords, step)
        if len(pts) < 3:
            continue
        n0 = len(verts)
        verts.extend(pts.tolist())
        segs.extend([(n0 + i, n0 + (i + 1) % len(pts)) for i in range(len(pts))])
        rings.append((n0, n0 + len(pts)))
        if k > 0:
            holes.append(Polygon(ring).representative_point().coords[0])
    if len(verts) < 3:
        return None
    V0 = np.array(verts) - np.array(O[:2])                     # repère local : précision
    A = {"vertices": V0, "segments": np.array(segs)}
    if holes:
        A["holes"] = np.array(holes) - np.array(O[:2])
    B = None
    for opts in (f"pq20a{max_area}Y", "pY", "p"):
        try:
            B = tr.triangulate(A, opts)
            if "triangles" in B and len(B["triangles"]):
                break
        except Exception:
            B = None
    if B is None or "triangles" not in B:
        return None
    V = B["vertices"] + np.array(O[:2])
    F = B["triangles"].astype(np.int64)
    # orientation CCW (normale +Z)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    F[cross < 0] = F[cross < 0][:, ::-1]
    return V, F, rings


def ring_normals(P):
    """Normales sortantes aux sommets d'un anneau CCW (extérieur) ou CW (trou), après orient()."""
    nxt = np.roll(P, -1, axis=0)
    e = nxt - P
    L = np.hypot(e[:, 0], e[:, 1])[:, None] + 1e-12
    n_edge = np.c_[e[:, 1], -e[:, 0]] / L                       # normale sortante de l'arête i
    n_v = n_edge + np.roll(n_edge, 1, axis=0)
    n_v /= np.hypot(n_v[:, 0], n_v[:, 1])[:, None] + 1e-12
    return n_v, n_edge


class Mesh:
    """Accumulateur de triangles (L93 + z absolu) avec attributs par face."""

    def __init__(self):
        self.V, self.F, self.face_attrs = [], [], defaultdict(list)
        self.n = 0

    def add(self, V3, F, **face_attr):
        if F is None or len(F) == 0:
            return
        self.V.append(np.asarray(V3, float))
        self.F.append(np.asarray(F, np.int64) + self.n)
        self.n += len(V3)
        for k, v in face_attr.items():
            self.face_attrs[k].extend([v] * len(F))

    def arrays(self):
        if not self.V:
            return None, None
        return np.vstack(self.V), np.vstack(self.F)


def sample_vertices(surf, poly, V, rings, nb_bound):
    """Altitude des sommets : bord -> 0,2 m à l'intérieur du polygone (ou point exact si le voisin
    est au même niveau) ; intérieur -> point exact (éloigné du bord) ou ramené à 0,2 m."""
    x, y = V[:, 0].copy(), V[:, 1].copy()
    z = np.empty(len(V))
    walls = []                                       # (P_top[n,3], z_bas[n]) par anneau
    inner = poly.buffer(-0.2)
    for (a, b) in rings:
        P = V[a:b]
        n_v, _ = ring_normals(P)
        pin = P - 0.2 * n_v
        pout = P + 0.2 * n_v
        zin = surf.sample(pin[:, 0], pin[:, 1])
        zout = surf.sample(pout[:, 0], pout[:, 1])
        zp = surf.sample(P[:, 0], P[:, 1])
        outside = ~shapely.contains_xy(EMPRISE_IN, pout[:, 0], pout[:, 1])
        d = zin - zout
        smooth = (np.abs(d) < 0.02) & ~outside
        zr = np.where(smooth, zp, zin)
        z[a:b] = zr
        bottom = np.where(outside, zr - 1.0, zout - 0.03)
        wall = (d > 0.01) | outside
        walls.append((np.c_[P, zr], bottom, wall))
    # sommets intérieurs (points de Steiner)
    if nb_bound < len(V):
        I = np.arange(nb_bound, len(V))
        pts = shapely.points(V[I])
        dist = shapely.distance(pts, poly.boundary)
        near = dist < 0.2
        if near.any() and not inner.is_empty:
            bnd = inner.boundary
            pr = shapely.line_interpolate_point(bnd, shapely.line_locate_point(bnd, pts[near]))
            c = shapely.get_coordinates(pr)
            far = np.hypot(c[:, 0] - V[I[near], 0], c[:, 1] - V[I[near], 1]) > 1.0
            c[far] = V[I[near]][far]
            x[I[near]], y[I[near]] = c[:, 0], c[:, 1]
        z[I] = surf.sample(x[I], y[I])
    return z, walls


def wall_mesh(walls, mesh, **attr):
    for P3, bottom, flag in walls:
        n = len(P3)
        for i in range(n):
            j = (i + 1) % n
            if not (flag[i] or flag[j]):
                continue
            t0, t1 = P3[i], P3[j]
            b0 = np.array([t0[0], t0[1], min(bottom[i], t0[2] - 0.005)])
            b1 = np.array([t1[0], t1[1], min(bottom[j], t1[2] - 0.005)])
            # face tournée vers l'extérieur (anneau CCW, normale sortante à droite de l'arête)
            mesh.add(np.array([t0, t1, b1, b0]), np.array([[0, 2, 1], [0, 3, 2]]), **attr)


# --- USD ---------------------------------------------------------------------------------------
def usd():
    from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt  # noqa: F401
    return Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt


def new_layer(path):
    Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt = usd()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    w = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(w.GetPrim())
    return st


def local(V):
    V = np.asarray(V, float)
    return np.c_[V[:, 0] - O[0], V[:, 1] - O[1], V[:, 2] - O[2]].astype(np.float32)


def define_mesh(st, path, V, F, material=None, uv_macro=True, uv_metre=True, smooth=True,
                constant=None, uniform=None):
    """Mesh USD depuis des sommets L93 absolus. Primvars : st (UV macro 0-1 sur l'emprise),
    st1 (UV en mètres), attributs constants / par face."""
    Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt = usd()
    if V is None or len(F) == 0:
        return None
    VL = local(V)
    m = UsdGeom.Mesh.Define(st, path)
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(VL))
    m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(F), 3, np.int32)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.ascontiguousarray(F, np.int32).ravel()))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    m.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, VL.min(0))), Gf.Vec3f(*map(float, VL.max(0)))]))
    m.CreateDoubleSidedAttr(False)
    if smooth:
        tm = trimesh.Trimesh(VL, F, process=False)
        nrm = np.asarray(tm.vertex_normals, np.float32)
        m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(nrm))
        m.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    pv = UsdGeom.PrimvarsAPI(m)
    if uv_macro:
        st_ = np.c_[(V[:, 0] - BBOX[0]) / (BBOX[2] - BBOX[0]), (V[:, 1] - BBOX[1]) / (BBOX[3] - BBOX[1])]
        pv.CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
            Vt.Vec2fArray.FromNumpy(st_.astype(np.float32)))
    if uv_metre:
        pv.CreatePrimvar("st1", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
            Vt.Vec2fArray.FromNumpy(VL[:, :2].copy()))
    for k, v in (constant or {}).items():
        if isinstance(v, str):
            pv.CreatePrimvar(k, Sdf.ValueTypeNames.String, UsdGeom.Tokens.constant).Set(v)
        else:
            pv.CreatePrimvar(k, Sdf.ValueTypeNames.Float, UsdGeom.Tokens.constant).Set(float(v))
    for k, vals in (uniform or {}).items():
        if vals and isinstance(vals[0], str):
            pv.CreatePrimvar(k, Sdf.ValueTypeNames.StringArray, UsdGeom.Tokens.uniform).Set(Vt.StringArray(list(vals)))
        else:
            pv.CreatePrimvar(k, Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.uniform).Set(
                Vt.FloatArray.FromNumpy(np.asarray(vals, np.float32)))
    if material:
        bind(m.GetPrim(), material)
    return m


def bind(prim, material):
    """Liaison de matériau vers /World/Looks/... (défini dans layers/materiaux.usda)."""
    Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt = usd()
    UsdShade.MaterialBindingAPI.Apply(prim).GetDirectBindingRel().SetTargets([Sdf.Path(material)])


def write_materials(path, albedo_rel, masks):
    """Matériaux UsdPreviewSurface (lisibles par Houdini/Karma et l'import USD d'Unreal)."""
    Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt = usd()
    st = new_layer(path)
    UsdGeom.Scope.Define(st, "/World/Looks")

    def mat(name, color, rough=0.85, opacity=1.0, tex=None, metal=0.0):
        m = UsdShade.Material.Define(st, f"/World/Looks/{name}")
        sh = UsdShade.Shader.Define(st, f"/World/Looks/{name}/Surface")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rough)
        sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metal)
        if opacity < 1:
            sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
        if tex:
            rd = UsdShade.Shader.Define(st, f"/World/Looks/{name}/stReader")
            rd.CreateIdAttr("UsdPrimvarReader_float2")
            rd.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
            tx = UsdShade.Shader.Define(st, f"/World/Looks/{name}/Albedo")
            tx.CreateIdAttr("UsdUVTexture")
            tx.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(tex)
            tx.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
            tx.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
            tx.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
            tx.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), "result")
            tx.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tx.ConnectableAPI(), "rgb")
        else:
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        return m

    for c in CLASSES + ["chaussee_2025"]:
        mat(f"sol_{c}", COULEUR[c])                                   # sans texture (zones 2025)
        if albedo_rel and c != "chaussee_2025":
            mat(f"sol_{c}_macro", COULEUR[c], tex=albedo_rel)          # ortho nettoyée
    for k in ("bordure", "bati", "toit", "tronc", "feuillage", "metal", "signal", "panneau", "verre"):
        mat(k, COULEUR[k], rough=0.4 if k in ("metal", "verre") else 0.85,
            metal=0.6 if k == "metal" else 0.0)
    for coul, rgb in PEINTURE.items():
        for u, op in OPACITE_USURE.items():
            mat(f"peinture_{coul}_u{u}", rgb, rough=0.6, opacity=op)
    lay = st.GetRootLayer()
    lay.customLayerData = {"masques": ";".join(masks)}
    st.GetRootLayer().Save()


# --- prototypes d'instances ------------------------------------------------------------------
def proto_meshes():
    """Prototypes génériques (repère local du prototype, Z vers le haut, face avant vers +Y)."""
    P = {}

    def cyl(r, h, z0=0.0, sections=12):
        m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
        m.apply_translation([0, 0, z0 + h / 2])
        return m

    def boxm(sx, sy, sz, c):
        m = trimesh.creation.box([sx, sy, sz])
        m.apply_translation(c)
        return m

    crown = trimesh.creation.icosphere(subdivisions=2, radius=0.5)
    crown.apply_scale([1, 1, 0.75])
    crown.apply_translation([0, 0, 0.62])
    P["arbre_feuillu"] = [("tronc", cyl(0.035, 0.40)), ("feuillage", crown)]
    cone = trimesh.creation.cone(radius=0.5, height=0.8, sections=12)
    cone.apply_translation([0, 0, 0.2])
    P["arbre_conifere"] = [("tronc", cyl(0.035, 0.25)), ("feuillage", cone)]
    young = trimesh.creation.icosphere(subdivisions=1, radius=0.5)
    young.apply_scale([1, 1, 1.2])
    young.apply_translation([0, 0, 0.62])
    P["arbre_jeune"] = [("tronc", cyl(0.05, 0.45)), ("feuillage", young)]
    P["feu_tricolore"] = [("metal", cyl(0.06, 3.2)), ("signal", boxm(0.32, 0.25, 0.95, [0, 0.18, 2.75]))]
    P["feu_pieton"] = [("metal", cyl(0.06, 2.6)), ("signal", boxm(0.25, 0.22, 0.60, [0, 0.16, 2.25]))]
    P["feu_velo"] = [("metal", cyl(0.06, 2.6)), ("signal", boxm(0.22, 0.20, 0.55, [0, 0.15, 1.7]))]
    P["panneau"] = [("metal", cyl(0.03, 2.6)), ("panneau", boxm(0.70, 0.03, 0.70, [0, 0.05, 2.25]))]
    P["lampadaire"] = [("metal", cyl(0.08, 8.0)), ("metal", boxm(0.12, 1.6, 0.10, [0, 0.8, 7.95])),
                       ("verre", boxm(0.35, 0.6, 0.12, [0, 1.5, 7.85]))]
    P["abri_bus"] = [("verre", boxm(4.0, 0.04, 2.3, [0, -0.7, 1.15])), ("metal", boxm(4.2, 1.6, 0.08, [0, 0, 2.4])),
                     ("verre", boxm(0.04, 1.4, 2.3, [-2.0, 0, 1.15])), ("verre", boxm(0.04, 1.4, 2.3, [2.0, 0, 1.15]))]
    P["poteau_arret"] = [("metal", cyl(0.04, 2.8)), ("panneau", boxm(0.45, 0.04, 0.6, [0, 0, 2.4]))]
    P["potelet"] = [("metal", cyl(0.07, 1.0))]
    P["barriere"] = [("metal", boxm(1.5, 0.05, 1.0, [0, 0, 0.5]))]
    P["borne"] = [("metal", boxm(0.4, 0.3, 1.2, [0, 0, 0.6]))]
    P["autre"] = [("metal", cyl(0.05, 1.5))]
    return P


def proto_for(t):
    t = str(t or "").lower()
    rules = [("pieton", "feu_pieton"), ("velo", "feu_velo"), ("cycl", "feu_velo"), ("feu", "feu_tricolore"),
             ("signal", "feu_tricolore"), ("lamp", "lampadaire"), ("eclair", "lampadaire"),
             ("abri", "abri_bus"), ("arret", "poteau_arret"), ("bus", "poteau_arret"), ("panneau", "panneau"),
             ("sign", "panneau"), ("potelet", "potelet"), ("bollard", "potelet"), ("borne", "borne"),
             ("barri", "barriere"), ("garde", "barriere")]
    for k, v in rules:
        if k in t:
            return v
    return "autre"


# --- librairie graphique (assets/lib) ------------------------------------------------------------
LIB = Path(__import__("os").environ.get("ASSETS_LIB", REPO / "assets" / "lib"))


class Librairie:
    """Index des assets de la librairie (assets/lib/<categorie>/<nom>/<nom>.usda) ; les assets
    utilisés sont copiés dans le paquet (package/assets/...) et référencés par les PointInstancers."""

    def __init__(self, pkg):
        self.pkg = pkg
        self.idx = {}
        if LIB.exists():
            for f in LIB.glob("*/*/*.usda"):
                if f.stem == f.parent.name:
                    self.idx[f.stem] = f
        self.copied = {}
        self._h = {}

    def resolve(self, candidats):
        for c in candidats or []:
            if c in self.idx:
                return c
        return None

    def height(self, name):
        if name not in self._h:
            from pxr import Usd, UsdGeom
            h = None
            meta = self.idx[name].parent / "meta.json"
            if meta.exists():
                try:
                    h = fnum(json.loads(meta.read_text()).get("hauteur_m"))
                except Exception:
                    h = None
            if not h:
                stg = Usd.Stage.Open(str(self.idx[name]))
                bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
                    stg.GetPseudoRoot()).ComputeAlignedRange()
                h = float(bb.GetMax()[2] - bb.GetMin()[2]) if not bb.IsEmpty() else 1.0
            self._h[name] = max(h, 0.01)
        return self._h[name]

    def ref_path(self, name):
        """Copie l'asset dans le paquet ; chemin relatif depuis package/layers/."""
        src = self.idx[name].parent
        rel = src.relative_to(LIB)
        if name not in self.copied:
            dst = self.pkg / "assets" / rel
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            self.copied[name] = str(rel)
        return f"../assets/{rel}/{name}.usda"

    def glb(self, name):
        g = self.idx[name].parent / f"{name}.glb"
        return g if g.exists() else None


def resolve_items(items, lib):
    """Remplace le prototype générique par un asset de la librairie quand il existe
    (attrs['_candidats'] ; arbres : échelle = hauteur mesurée / hauteur de l'asset)."""
    out = []
    for proto, x, y, z, yaw, sc, attrs in items:
        name = lib.resolve(attrs.get("_candidats")) if lib else None
        if name:
            h = attrs.get("_h")
            k = (h / lib.height(name)) if h else 1.0
            out.append((name, x, y, z, yaw, (k, k, k), {**attrs, "_lib": True}))
        else:
            # volume générique, mais prototype nommé comme l'asset définitif attendu (remplaçable
            # sur le PC par un asset du même nom : voir recon/package_src/substituer_assets.py)
            nom = (attrs.get("_candidats") or [proto])[0]
            out.append((nom, x, y, z, yaw, sc, {**attrs, "_generique": proto}))
    return out


def point_instancer(st, path, protos, items, lib=None):
    """items : liste (proto, x, y, z_abs, yaw_deg, (sx, sy, sz), attrs)."""
    Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt = usd()
    used = sorted({it[0] for it in items})
    if not used:
        return
    pi = UsdGeom.PointInstancer.Define(st, path)
    UsdGeom.Scope.Define(st, f"{path}/Prototypes")
    rel = []
    lib_names = {it[0] for it in items if it[6].get("_lib")}
    for name in used:
        x = UsdGeom.Xform.Define(st, f"{path}/Prototypes/{name}")
        rel.append(x.GetPath())
        if name in lib_names:                                    # asset de la librairie
            x.GetPrim().GetReferences().AddReference(lib.ref_path(name))
            continue
        gen = next((it[6].get("_generique") for it in items if it[0] == name and it[6].get("_generique")), name)
        x.GetPrim().SetCustomDataByKey("volume_provisoire", gen)
        for k, (matname, tm) in enumerate(protos[gen]):
            V = np.asarray(tm.vertices, np.float32)
            F = np.asarray(tm.faces, np.int32)
            m = UsdGeom.Mesh.Define(st, f"{path}/Prototypes/{name}/part{k}_{matname}")
            m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(V))
            m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(F), 3, np.int32)))
            m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(F.ravel()))
            m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            m.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, V.min(0))), Gf.Vec3f(*map(float, V.max(0)))]))
            bind(m.GetPrim(), f"/World/Looks/{matname}")
    pi.CreatePrototypesRel().SetTargets(rel)
    idx = np.array([used.index(it[0]) for it in items], np.int32)
    pos = local(np.array([[it[1], it[2], it[3]] for it in items]))
    ori = []
    for it in items:
        a = math.radians(it[4]) / 2
        ori.append(Gf.Quath(math.cos(a), Gf.Vec3h(0, 0, math.sin(a))))
    sc = np.array([it[5] for it in items], np.float32)
    pi.CreateProtoIndicesAttr(Vt.IntArray.FromNumpy(idx))
    pi.CreatePositionsAttr(Vt.Vec3fArray.FromNumpy(pos))
    pi.CreateOrientationsAttr(Vt.QuathArray(ori))
    pi.CreateScalesAttr(Vt.Vec3fArray.FromNumpy(sc))
    pv = UsdGeom.PrimvarsAPI(pi)
    keys = sorted({k for it in items for k in it[6] if not k.startswith("_")})
    for k in keys:
        vals = [it[6].get(k) for it in items]
        if all(isinstance(v, (int, float)) or v is None for v in vals):
            pv.CreatePrimvar(k, Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex).Set(
                Vt.FloatArray([float(v) if v is not None else -1.0 for v in vals]))
        else:
            pv.CreatePrimvar(k, Sdf.ValueTypeNames.StringArray, UsdGeom.Tokens.vertex).Set(
                Vt.StringArray(["" if v is None else str(v) for v in vals]))
    return pi


# --- couches -----------------------------------------------------------------------------------
def build_ground(surfs, surf, albedo):
    """Pavage -> maillages par classe (voirie / terrain) + bordures."""
    groups = defaultdict(Mesh)                       # (couche, nom_mesh, materiau) -> Mesh
    kerbs = Mesh()
    skirt = Mesh()
    stats = defaultdict(float)
    for g, p in surfs:
        c = classe_of(p)
        mod = modifie_2025(p)
        for poly in clean_poly(g.intersection(EMPRISE)):
            big = c in ("espace_vert", "batiment", "autre", "chantier")
            T = triangulate(poly, step=0.5 if not big else 1.0, max_area=1.0 if not big else 4.0)
            if T is None:
                stats["echecs_triangulation"] += 1
                continue
            V, F, rings = T
            nb = rings[-1][1]
            z, walls = sample_vertices(surf, poly, V, rings, nb)
            layer = "voirie" if c in VOIRIE else "terrain"
            if c == "chaussee" and mod:
                name, mat = "chaussee_2025", "sol_chaussee_2025"
            elif mod or not albedo:
                name, mat = (f"{c}_2025" if mod else c), f"sol_{c}"
            else:
                name, mat = c, f"sol_{c}_macro"
            groups[(layer, name, mat, c)].add(np.c_[V, z], F)
            stats[f"aire_{c}"] += poly.area
            for P3, bottom, flag in walls:
                inside_emprise = ~(bottom < P3[:, 2] - 0.9)
                wall_mesh([(P3, bottom, flag & inside_emprise)], kerbs, classe=c)
                wall_mesh([(P3, bottom, flag & ~inside_emprise)], skirt, classe=c)
    return groups, kerbs, skirt, stats


def build_markings(marks, surf, ground):
    groups = defaultdict(Mesh)
    n = 0
    for g, p in marks:
        typ = str(getp(p, ["type"], "autre"))
        coul = str(getp(p, ["couleur"], "blanc")).lower()
        coul = coul if coul in PEINTURE else "blanc"
        us = str(getp(p, ["usure"], "1")).upper().replace(".0", "")
        if typ == "fantome":
            us = "F"
        us = us if us in OPACITE_USURE else "1"
        cov = fnum(getp(p, ["couverture"]), OPACITE_USURE[us])
        for poly in clean_poly(g.intersection(EMPRISE)):
            T = triangulate(poly, step=0.25, max_area=0.25)
            if T is None:
                continue
            V, F, _ = T
            z = ground(V[:, 0], V[:, 1], surf.sample_min(V[:, 0], V[:, 1])) + 0.01
            groups[(coul, us)].add(np.c_[V, z], F, type=typ, couverture=float(cov),
                                   ident=str(getp(p, ["id", "ident"], "")))
            n += 1
    return groups, n


def build_buildings(bats, surf):
    mesh_w, mesh_r = Mesh(), Mesh()
    n = 0
    for g, p in bats:
        h_eg = fnum(getp(p, ["hauteur_egout_m", "h_egout", "hauteur_egout"]))
        h_f = fnum(getp(p, ["hauteur_faite_m", "h_faite", "hauteur_faite", "hauteur_m", "hauteur"]))
        h = h_eg or h_f or 3.0 * (fnum(getp(p, ["nb_etages", "etages"]), 2) or 2)
        for poly in clean_poly(g):
            if not poly.intersects(EMPRISE):
                continue
            T = triangulate(poly, step=5.0, max_area=50.0)
            if T is None:
                continue
            V, F, rings = T
            ex = V[: rings[0][1]]
            zb = float(np.nanmin(surf.sample(ex[:, 0], ex[:, 1]))) - 0.2
            ztop = zb + 0.2 + h
            mesh_r.add(np.c_[V, np.full(len(V), ztop)], F)
            for (a, b) in rings:
                P = V[a:b]
                k = len(P)
                for i in range(k):
                    j = (i + 1) % k
                    q = np.array([[*P[i], ztop], [*P[j], ztop], [*P[j], zb], [*P[i], zb]])
                    mesh_w.add(q, np.array([[0, 2, 1], [0, 3, 2]]))
            n += 1
    return mesh_w, mesh_r, n


def items_trees(trees, surf, ground):
    items = []
    for g, p in trees:
        pt = g.centroid if g.geom_type != "Point" else g
        if not EMPRISE.contains(pt):
            continue
        h = fnum(getp(p, ["hauteur_m", "hauteur", "h"]), 8.0) or 8.0
        d = fnum(getp(p, ["diametre_couronne_m", "couronne_m", "diametre_m", "couronne"]), max(2.0, h * 0.6)) or 4.0
        ess = str(getp(p, ["essence", "espece", "genre"], "")).lower()
        jeune = str(getp(p, ["jeune", "plante_2025", "statut", "etat"], "")).lower()
        proto = "arbre_conifere" if any(k in ess for k in ("pin", "cèdre", "cedre", "sapin", "épicéa", "if ")) \
            else "arbre_jeune" if ("jeune" in jeune or "2025" in jeune or "true" in jeune) else "arbre_feuillu"
        z = float(ground([pt.x], [pt.y], surf.sample([pt.x], [pt.y]))[0])
        sp = "_".join(ess.replace("'", " ").replace("×", " ").split()[:2]) if ess else ""
        taille = "jeune" if proto == "arbre_jeune" else "petit" if h < 8 else "moyen" if h < 15 else "grand"
        ordre = {"jeune": ["jeune", "petit", "moyen", "grand"], "petit": ["petit", "moyen", "jeune", "grand"],
                 "moyen": ["moyen", "grand", "petit", "jeune"], "grand": ["grand", "moyen", "petit", "jeune"]}[taille]
        cands = [f"arbre_{sp}_{t}" for t in ordre] + [f"arbre_{sp.split('_')[0]}_{t}" for t in ordre] if sp else []
        items.append((proto, pt.x, pt.y, z, (hash((pt.x, pt.y)) % 360), (d, d, h),
                      {"hauteur_m": h, "couronne_m": d, "essence": ess or None, "_candidats": cands, "_h": h}))
    return items


def items_furniture(mob, inst_json, surf, ground):
    items = []
    src = []
    if inst_json:
        for e in inst_json:
            x = fnum(e.get("x")); y = fnum(e.get("y"))
            if x is None or y is None:
                continue
            if abs(x) < 1000 and abs(y) < 1000:                    # repère local
                x, y = x + O[0], y + O[1]
            src.append((e.get("type"), x, y, fnum(e.get("yaw"), 0.0), fnum(e.get("echelle") or e.get("scale"), 1.0), e))
    else:
        for g, p in mob:
            pt = g.centroid if g.geom_type != "Point" else g
            az = fnum(getp(p, ["orientation", "azimut", "orientation_deg", "azimut_deg"]), 0.0)
            src.append((getp(p, ["type", "categorie"]), pt.x, pt.y, -az, 1.0, p))
    for t, x, y, yaw, s, p in src:
        if not EMPRISE.contains(shapely.Point(x, y)) or str(t).lower().startswith("arbre"):
            continue
        proto = proto_for(t)
        z = float(ground([x], [y], surf.sample([x], [y]))[0])
        s = s if isinstance(s, (int, float)) and s > 0 else 1.0
        attrs = {"type": str(t)}
        code = getp(p, ["code_panneau", "code", "panneau"]) if isinstance(p, dict) else None
        asset = getp(p, ["asset", "prototype", "modele"]) if isinstance(p, dict) else None
        cands = [str(asset)] if asset else []
        if code:
            attrs["code_panneau"] = str(code)
            c = str(code).replace(" ", "").replace("-", "")
            cands += [f"panneau_{c}", f"panneau_{c.split('_')[0]}"]
        cands.append(proto)
        attrs["_candidats"] = cands
        items.append((proto, x, y, z, yaw, (s, s, s), attrs))
    return items


# --- textures ------------------------------------------------------------------------------------
def make_albedo(out_px, tex_dir, T):
    """Macro-albédo de l'emprise (8192 px par défaut) depuis l'atelier textures (sinon ortho 2022)."""
    cands = sorted([p for p in T.rglob("*.tif") if "albedo" in p.name.lower()]) if T.exists() else []
    res = (BBOX[2] - BBOX[0]) / out_px
    dst_t = from_origin(BBOX[0], BBOX[3], res, res)
    img = np.zeros((3, out_px, out_px), np.uint8)
    source = None
    if cands:
        source = [str(p.relative_to(REPO)) for p in cands]
        for p in cands:
            with rasterio.open(p) as r:
                tmp = np.zeros((3, out_px, out_px), np.uint8)
                for b in range(3):
                    reproject(rasterio.band(r, b + 1), tmp[b], src_transform=r.transform, src_crs=r.crs or "EPSG:2154",
                              dst_transform=dst_t, dst_crs="EPSG:2154", resampling=Resampling.bilinear)
                m = tmp.sum(0) > 0
                img[:, m] = tmp[:, m]
    else:
        source = ["ortho PCRS 2022 brute (repli : marquages et véhicules NON retirés)"]
        mos = Image.new("RGB", (6000, 6000))
        for x0 in range(int(BBOX[0] // 50 * 50), int(BBOX[2]), 50):
            for y0 in range(int(BBOX[1] // 50 * 50), int(BBOX[3]), 50):
                f = ORTHO5 / f"pcrs5cm_{x0}_{y0}.jpg"
                if f.exists():
                    px = int(round((x0 - BBOX[0]) / 0.05)); py = int(round((BBOX[3] - (y0 + 50)) / 0.05))
                    mos.paste(Image.open(f).convert("RGB"), (px, py))
        img = np.moveaxis(np.asarray(mos.resize((out_px, out_px), Image.BICUBIC)), -1, 0)
    tex_dir.mkdir(parents=True, exist_ok=True)
    f = tex_dir / f"albedo_macro_{out_px}.jpg"
    Image.fromarray(np.moveaxis(img, 0, -1)).save(f, quality=90, optimize=True)
    masks = []
    if T.exists():
        for p in sorted(T.rglob("*.tif")):
            n = p.name.lower()
            if n.startswith("masque") or "mask" in n:
                with rasterio.open(p) as r:
                    a = np.zeros((4096, 4096), np.float32)
                    reproject(rasterio.band(r, 1), a, src_transform=r.transform, src_crs=r.crs or "EPSG:2154",
                              dst_transform=from_origin(BBOX[0], BBOX[3], 300 / 4096, 300 / 4096),
                              dst_crs="EPSG:2154", resampling=Resampling.average)
                    mx = float(np.nanmax(a)) or 1.0
                    q = np.clip(a / mx * 255 if mx > 1 else a * 255, 0, 255).astype(np.uint8)
                    g = tex_dir / f"{p.stem}_4096.png"
                    Image.fromarray(q).save(g, optimize=True)
                    masks.append(f"../textures/{g.name}")
    return f, source, masks


# --- aperçu glTF -----------------------------------------------------------------------------------
def to_trimesh(V, F, rgb, alpha=1.0):
    """Maillage glTF (Y-up) ; la couleur est portée par un matériau PBR non métallique."""
    VL = local(V)
    VL = np.c_[VL[:, 0], VL[:, 2], -VL[:, 1]]                         # Z-up -> Y-up glTF
    t = trimesh.Trimesh(VL, F, process=False)
    t.metadata["rgba"] = (*[float(c) for c in rgb], float(alpha))
    return t


def glb_scene(parts, tex_part):
    scene = trimesh.Scene()
    by = defaultdict(list)
    for t in parts:
        by[t.metadata["rgba"]].append(t)
    for i, (rgba, ts) in enumerate(sorted(by.items())):
        m = trimesh.util.concatenate(ts) if len(ts) > 1 else ts[0]
        mat = trimesh.visual.material.PBRMaterial(
            baseColorFactor=[int(round(c * 255)) for c in rgba], metallicFactor=0.0, roughnessFactor=0.85,
            alphaMode="BLEND" if rgba[3] < 1 else "OPAQUE", doubleSided=False)
        m.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(m, node_name=f"groupe_{i:02d}")
    if tex_part is not None:
        scene.add_geometry(tex_part, node_name="sol_texture")
    return scene


def to_trimesh_tex(V, F, image):
    """Sol texturé par le macro-albédo (UV = position dans l'emprise)."""
    VL = local(V)
    uv = np.c_[(V[:, 0] - BBOX[0]) / (BBOX[2] - BBOX[0]), (V[:, 1] - BBOX[1]) / (BBOX[3] - BBOX[1])]
    VL = np.c_[VL[:, 0], VL[:, 2], -VL[:, 1]]
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=image, metallicFactor=0.0, roughnessFactor=0.9)
    return trimesh.Trimesh(VL, F, visual=trimesh.visual.TextureVisuals(uv=uv, material=mat), process=False)


def preview_instances(items, protos, lib, glb, glb_inst):
    """Aperçu : prototypes génériques fusionnés ; assets de la librairie instanciés (glb)."""
    for proto, x, y, z, yaw, s, at in items:
        if not at.get("_lib"):
            for matname, tm in protos[at.get("_generique", proto)]:
                t = tm.copy()
                t.apply_scale(s)
                t.apply_transform(trimesh.transformations.rotation_matrix(math.radians(yaw), [0, 0, 1]))
                t.apply_translation([x, y, z])
                glb.append(to_trimesh(np.asarray(t.vertices), np.asarray(t.faces), COULEUR[matname]))
        elif lib and lib.glb(proto):
            glb_inst.append((lib.glb(proto), x, y, z, yaw, s))


def add_instances(scene, inst):
    """Ajoute les assets glb (Y-up) en instances : translation (x, z, -y) locale, rotation autour de +Y."""
    cache = {}
    for k, (f, x, y, z, yaw, s) in enumerate(inst):
        if f not in cache:
            cache[f] = trimesh.load(f, force="scene")
        sub = cache[f]
        T = trimesh.transformations.rotation_matrix(math.radians(yaw), [0, 1, 0])
        T = T @ np.diag([s[0], s[2], s[1], 1.0])
        T[:3, 3] = [x - O[0], z - O[2], -(y - O[1])]
        for node in sub.graph.nodes_geometry:
            M, gname = sub.graph[node]
            scene.add_geometry(sub.geometry[gname], node_name=f"inst{k}_{node}", geom_name=f"{f.stem}_{gname}",
                               transform=T @ M)


# --- main ----------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-glb", action="store_true")
    ap.add_argument("--albedo-px", type=int, default=8192)
    ap.add_argument("--out", default=str(PKG))
    ap.add_argument("--entrees", default=str(OUT), help="dossier des sorties d'ateliers")
    a = ap.parse_args()
    pkg = Path(a.out)
    IN = Path(a.entrees)
    (pkg / "layers").mkdir(parents=True, exist_ok=True)
    rep = {"date_etat": "2026-10", "origine_L93_NGF": O, "emprise_L93": BBOX, "entrees": {}, "comptes": {}}

    def need(rel):
        p = IN / rel
        rep["entrees"][rel] = p.exists()
        return p if p.exists() else None

    f_surf = need("surfaces/surfaces_2026.geojson")
    f_marq = need("marquages/marquages_2026.geojson")
    f_dtm = need("relief/dtm_sol_10cm.tif") or DTM15
    f_road = need("relief/chaussee_lisse_10cm.tif")
    f_arb = need("objets/arbres.geojson")
    f_mob = need("objets/mobilier.geojson")
    f_bat = need("objets/batiments.geojson")
    f_inst = need("objets/instances.json")
    f_xodr = need("opendrive/paquet_jardin_2026.xodr")
    if f_surf is None:
        sys.exit("surfaces_2026.geojson manquant : lancer d'abord recon/stages/surfaces.py")

    surfs = read_layer(f_surf)
    log(len(surfs), "polygones de surface")
    surf = Surface(surfs, f_dtm, f_road)

    tex_dir = pkg / "textures"
    alb, alb_src, masks = make_albedo(a.albedo_px, tex_dir, IN / "textures")
    rep["albedo"] = {"fichier": str(alb.relative_to(pkg)), "sources": alb_src}
    log("albédo :", alb.name, alb_src[0][:60])
    write_materials(pkg / "layers" / "materiaux.usda", f"../textures/{alb.name}", masks)

    glb, glb_tex, glb_inst = [], [], []
    # sol
    groups, kerbs, skirt, stats = build_ground(surfs, surf, albedo=True)
    ground = GroundZ([m.arrays() for m in groups.values() if m.V])
    for layer in ("terrain", "voirie"):
        st = new_layer(pkg / "layers" / f"{layer}.usdc")
        Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt = usd()
        UsdGeom.Scope.Define(st, f"/World/{layer.capitalize()}")
        for (ly, name, mat, c), m in sorted(groups.items()):
            if ly != layer:
                continue
            V, F = m.arrays()
            define_mesh(st, f"/World/{layer.capitalize()}/{name}", V, F, material=f"/World/Looks/{mat}",
                        constant={"classe": c, "etat": "modifie_2025" if name.endswith("2025") else "inchange_2022"})
            rep["comptes"][f"{layer}/{name}"] = int(len(F))
            if mat.endswith("_macro"):
                glb_tex.append((V, F))
            else:
                glb.append(to_trimesh(V, F, COULEUR.get(name, COULEUR[c])))
        if layer == "terrain":
            V, F = skirt.arrays()
            if V is not None:
                define_mesh(st, "/World/Terrain/jupe_emprise", V, F, material="/World/Looks/sol_autre", smooth=False)
                glb.append(to_trimesh(V, F, COULEUR["autre"]))
        st.GetRootLayer().Save()
    st = new_layer(pkg / "layers" / "bordures.usdc")
    V, F = kerbs.arrays()
    if V is not None:
        define_mesh(st, "/World/Bordures/faces_verticales", V, F, material="/World/Looks/bordure", smooth=False,
                    uv_macro=False, uniform={"classe_haute": kerbs.face_attrs["classe"]})
        rep["comptes"]["bordures"] = int(len(F))
        glb.append(to_trimesh(V, F, COULEUR["bordure"]))
    st.GetRootLayer().Save()
    log("sol :", {k: v for k, v in rep["comptes"].items()})

    # marquages
    st = new_layer(pkg / "layers" / "marquages.usdc")
    if f_marq:
        mg, nm = build_markings(read_layer(f_marq), surf, ground)
        for (coul, us), m in sorted(mg.items()):
            V, F = m.arrays()
            define_mesh(st, f"/World/Marquages/{coul}_usure_{us}", V, F, material=f"/World/Looks/peinture_{coul}_u{us}",
                        uv_macro=False, smooth=False, constant={"couleur": coul, "usure": us},
                        uniform={"type": m.face_attrs["type"], "couverture": m.face_attrs["couverture"]})
            rep["comptes"][f"marquages/{coul}_usure_{us}"] = int(len(F))
            glb.append(to_trimesh(V, F, PEINTURE[coul], OPACITE_USURE[us]))
        rep["comptes"]["marquages_polygones"] = nm
    st.GetRootLayer().Save()

    protos = proto_meshes()
    lib = Librairie(pkg)
    rep["librairie_assets_disponibles"] = len(lib.idx)
    # végétation
    st = new_layer(pkg / "layers" / "vegetation.usdc")
    if f_arb:
        it = items_trees(read_layer(f_arb), surf, ground)
        it = resolve_items(it, lib)
        point_instancer(st, "/World/Vegetation/arbres", protos, it, lib)
        rep["comptes"]["arbres"] = len(it)
        preview_instances(it, protos, lib, glb, glb_inst)
    st.GetRootLayer().Save()
    # mobilier
    st = new_layer(pkg / "layers" / "mobilier.usdc")
    if f_mob or f_inst:
        inst = json.loads(f_inst.read_text()) if f_inst else None
        if isinstance(inst, dict):
            inst = inst.get("instances") or next((v for v in inst.values() if isinstance(v, list)), None)
        it = items_furniture(read_layer(f_mob) if f_mob else [], inst, surf, ground)
        it = resolve_items(it, lib)
        point_instancer(st, "/World/Mobilier/objets", protos, it, lib)
        rep["comptes"]["mobilier"] = len(it)
        preview_instances(it, protos, lib, glb, glb_inst)
    st.GetRootLayer().Save()
    # bâtiments
    st = new_layer(pkg / "layers" / "batiments.usdc")
    if f_bat:
        mw, mr, nb = build_buildings(read_layer(f_bat), surf)
        for nm_, m, mat in (("murs", mw, "bati"), ("toits", mr, "toit")):
            V, F = m.arrays()
            if V is not None:
                define_mesh(st, f"/World/Batiments/{nm_}", V, F, material=f"/World/Looks/{mat}", smooth=False, uv_macro=False)
                glb.append(to_trimesh(V, F, COULEUR[mat]))
        rep["comptes"]["batiments"] = nb
    st.GetRootLayer().Save()

    # racine
    from pxr import Sdf, Usd, UsdGeom, Kind
    root = pkg / "paquet_jardin_2026.usda"
    if root.exists():
        root.unlink()
    st = Usd.Stage.CreateNew(str(root))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    w = UsdGeom.Xform.Define(st, "/World")
    Usd.ModelAPI(w.GetPrim()).SetKind(Kind.Tokens.assembly)
    st.SetDefaultPrim(w.GetPrim())
    st.GetRootLayer().subLayerPaths = [f"layers/{n}" for n in (
        "materiaux.usda", "marquages.usdc", "bordures.usdc", "voirie.usdc", "terrain.usdc",
        "vegetation.usdc", "mobilier.usdc", "batiments.usdc")]
    st.GetRootLayer().customLayerData = {
        "site": "Meylan (38) — carrefour Paquet Jardin (av. de Verdun / ch. de la Revirée / av. du Vercors)",
        "etat_modelise": "octobre 2026 (après travaux ligne C1 2025)",
        "crs": "EPSG:2154 (Lambert-93), altitudes NGF-IGN69",
        "origine_locale_L93_NGF": f"{O[0]} {O[1]} {O[2]}",
        "unites": "mètres, Z vers le haut",
        "opendrive": "paquet_jardin_2026.xodr",
    }
    st.GetRootLayer().Save()
    if f_xodr:
        shutil.copy2(f_xodr, pkg / "paquet_jardin_2026.xodr")
    # fichiers maintenus à la main (scripts Houdini/Unreal, guide)
    if SRC.exists():
        for p in SRC.rglob("*"):
            if p.is_file():
                d = pkg / p.relative_to(SRC)
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, d)
    if not a.no_glb and (glb or glb_tex):
        (pkg / "preview").mkdir(exist_ok=True)
        tex_part = None
        if glb_tex:
            nV = np.cumsum([0] + [len(v) for v, _ in glb_tex])
            V = np.vstack([v for v, _ in glb_tex])
            F = np.vstack([f + nV[i] for i, (_, f) in enumerate(glb_tex)])
            img = Image.open(alb).convert("RGB")
            if img.size[0] > 4096:
                img = img.resize((4096, 4096), Image.LANCZOS)
            import io
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=88)
            img = Image.open(io.BytesIO(buf.getvalue()))                 # format JPEG conservé dans le glb
            tex_part = to_trimesh_tex(V, F, img)
        scene = glb_scene(glb, tex_part)
        add_instances(scene, glb_inst)
        scene.export(pkg / "preview" / "paquet_jardin_2026.glb")
        rep["comptes"]["glb_triangles"] = int(sum(len(g.faces) for g in scene.geometry.values()))
    rep["stats_sol"] = {k: round(v, 1) for k, v in stats.items()}
    (pkg / "rapport_assemblage.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    log("paquet écrit :", pkg)
    print(json.dumps(rep["comptes"], indent=1))


if __name__ == "__main__":
    main()
