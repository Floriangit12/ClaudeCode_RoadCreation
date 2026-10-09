# -*- coding: utf-8 -*-
"""Caméras de contrôle du carrefour Paquet Jardin -> recon/pc/houdini/cameras.usda.

Couche USD séparée (le paquet n'est pas modifié) : `over "World"` + Scope Cameras + 4 caméras,
placées à partir des données réelles du paquet, dans le repère local (O = L93 917279.43 /
6460289.98, NGF 216.30 ; X est, Y nord, Z haut, mètres) :
  cam1_ensemble_sud          vue d'ensemble depuis le sud, 60 m au-dessus du sol, visée du centre
  cam2_conducteur_verdun_so  conducteur (1,3 m), voie de droite de Verdun SO entrante,
                             45 m avant la ligne d'effet des feux
  cam3_pieton_traversee_so   piéton (1,6 m) au bord du trottoir SE de la nouvelle traversée SO
                             (2025), regard vers le NO à travers zébras et refuge
  cam4_conducteur_vercors    conducteur (1,3 m), voie entrante du Vercors, 40 m avant la ligne
                             d'effet des feux
Sources : opendrive/lanes_2026.geojson (liaisons de jonction, lignes de référence, voies, lignes
de feux), marquages/marquages_2026.geojson (bandes neuves 2025 du zébra SO), surfaces_2026.geojson.
Altitudes du sol : maillages USD du paquet (layers/voirie.usdc, layers/terrain.usdc), recoupées
avec la heightmap 10 cm. Contrôles : scène composée, classes de surface sous chaque caméra,
écart angulaire de visée, dégagement de 2 m devant l'objectif (instances, bâtiments, clôtures).

Usage : hython recon/pc/houdini/generer_cameras.py [--controle-seul]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
PAQUET = DEPOT / "recon" / "out" / "paquet_jardin" / "package"
DONNEES = PAQUET / "donnees"
SORTIE = ICI / "cameras.usda"
O_L93 = np.array([917279.43, 6460289.98, 216.30])

APERTURE_MM = 36.0          # ouverture carrée (rendus 1000x1000)
CAM1_RECUL_M, CAM1_HAUTEUR_M, CAM1_HFOV = 95.0, 60.0, 55.0
CAM2_AVANT_FEUX_M, CAM4_AVANT_FEUX_M = 45.0, 40.0
OEIL_CONDUCTEUR_M, OEIL_PIETON_M = 1.3, 1.6
DECALAGE_CONDUCTEUR_M = 0.4  # conducteur à gauche du centre de voie (véhicule français)
PLONGEE_CONDUCTEUR, PLONGEE_PIETON = -2.5, -5.0
HFOV_CONDUCTEUR, HFOV_PIETON = 75.0, 70.0
RECUL_PIETON_M = 0.6         # piéton en attente derrière le nez de bordure


# ---------------------------------------------------------------- géométrie 2D (repère local)
def charger(rel):
    with open(DONNEES / rel, encoding="utf-8") as f:
        return json.load(f)


def polygones(g):
    """Liste de polygones (anneaux numpy en repère local) d'une géométrie GeoJSON L93."""
    if g["type"] == "Polygon":
        return [[np.asarray(r)[:, :2] - O_L93[:2] for r in g["coordinates"]]]
    if g["type"] == "MultiPolygon":
        return [[np.asarray(r)[:, :2] - O_L93[:2] for r in p] for p in g["coordinates"]]
    return []


def dans_anneau(pt, r):
    x, y = pt
    xa, ya, xb, yb = r[:, 0], r[:, 1], np.roll(r[:, 0], -1), np.roll(r[:, 1], -1)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = ((ya > y) != (yb > y)) & (x < (xb - xa) * (y - ya) / (yb - ya) + xa)
    return np.count_nonzero(c) % 2 == 1


def dans_polygone(pt, poly):
    return dans_anneau(pt, poly[0]) and not any(dans_anneau(pt, h) for h in poly[1:])


def ligne_reference(lanes, route):
    """Polyligne de la ligne de référence OpenDRIVE d'une route + abscisses curvilignes."""
    segs = [np.asarray(f["geometry"]["coordinates"])[:, :2] - O_L93[:2] for f in lanes
            if f["properties"].get("route") == route and f["properties"].get("type") == "reference"]
    pts = [segs[0]] + [s[1:] for s in segs[1:]]
    p = np.vstack(pts)
    return p, np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]


def point_ref(ref, s):
    """Point et cap unitaire de la ligne de référence à l'abscisse s."""
    p, d = ref
    i = int(np.clip(np.searchsorted(d, s) - 1, 0, len(p) - 2))
    t = (s - d[i]) / (d[i + 1] - d[i])
    h = p[i + 1] - p[i]
    return p[i] + t * (p[i + 1] - p[i]), h / np.linalg.norm(h)


def projeter_ref(ref, q):
    """Abscisse s et décalage t (positif à gauche) du point q sur la ligne de référence."""
    p, d = ref
    best = None
    for i in range(len(p) - 1):
        v = p[i + 1] - p[i]
        u = np.clip(np.dot(q - p[i], v) / np.dot(v, v), 0, 1)
        x = p[i] + u * v
        n = np.array([-v[1], v[0]]) / np.linalg.norm(v)
        cand = (np.linalg.norm(q - x), d[i] + u * np.linalg.norm(v), float(np.dot(q - x, n)))
        if best is None or cand[0] < best[0]:
            best = cand
    return best[1], best[2]


def coupe_voies(lanes, route, ref, s):
    """Intervalles [t0, t1] de chaque voie de la route sur la normale à l'abscisse s."""
    p, h = point_ref(ref, s)
    n = np.array([-h[1], h[0]])
    res = {}
    for f in lanes:
        pr = f["properties"]
        if pr.get("route") != route or "voie" not in pr or pr.get("type") == "reference":
            continue
        r = polygones(f["geometry"])[0][0]
        ts = []
        for a, b in zip(r[:-1], r[1:]):
            m = np.array([[n[0], a[0] - b[0]], [n[1], a[1] - b[1]]])
            if abs(np.linalg.det(m)) < 1e-12:
                continue
            t, u = np.linalg.solve(m, a - p)
            if 0 <= u <= 1 and abs(t) < 25:
                ts.append(t)
        if len(ts) >= 2:
            res[pr["voie"]] = (pr["type"], min(ts), max(ts))
    return p, h, n, res


# ---------------------------------------------------------------- sol (maillages USD du paquet)
class Sol:
    """Altitude du sol par lancer vertical sur les maillages USD (triangle le plus haut)."""

    def __init__(self):
        tris, noms = [], []
        for couche in ("voirie.usdc", "terrain.usdc"):
            st = Usd.Stage.Open(str(PAQUET / "layers" / couche))
            for prim in st.Traverse():
                if not prim.IsA(UsdGeom.Mesh):
                    continue
                m = UsdGeom.Mesh(prim)
                pts = np.asarray(m.GetPointsAttr().Get(), dtype=np.float64)
                mat = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
                    Usd.TimeCode.Default()))
                pts = (np.c_[pts, np.ones(len(pts))] @ mat)[:, :3]
                cnt = np.asarray(m.GetFaceVertexCountsAttr().Get())
                idx = np.asarray(m.GetFaceVertexIndicesAttr().Get())
                deb = np.r_[0, np.cumsum(cnt)[:-1]]
                for k in range(3, cnt.max() + 1):
                    sel = deb[cnt == k]
                    for j in range(1, k - 1):
                        t = np.c_[idx[sel], idx[sel + j], idx[sel + j + 1]]
                        tris.append(pts[t])
                        noms += [prim.GetPath().pathString] * len(t)
        self.t = np.vstack(tris)
        self.noms = np.asarray(noms)
        self.mn, self.mx = self.t[:, :, :2].min(1), self.t[:, :, :2].max(1)

    def z(self, x, y):
        sel = np.where((self.mn[:, 0] <= x) & (self.mx[:, 0] >= x)
                       & (self.mn[:, 1] <= y) & (self.mx[:, 1] >= y))[0]
        hits = []
        for i in sel:
            a, b, c = self.t[i]
            v0, v1, v2 = b[:2] - a[:2], c[:2] - a[:2], np.array([x, y]) - a[:2]
            det = v0[0] * v1[1] - v0[1] * v1[0]
            if abs(det) < 1e-12:
                continue
            u = (v2[0] * v1[1] - v2[1] * v1[0]) / det
            v = (v0[0] * v2[1] - v0[1] * v2[0]) / det
            if u >= -1e-9 and v >= -1e-9 and u + v <= 1 + 1e-9:
                hits.append((a[2] + u * (b[2] - a[2]) + v * (c[2] - a[2]), self.noms[i]))
        if not hits:
            raise ValueError(f"pas de sol sous ({x:.2f}, {y:.2f})")
        return max(hits)


def z_heightmap(x, y, _cache={}):
    """Recoupement : heightmap 16 bits 10 cm (valeur aux nœuds), interpolation bilinéaire."""
    if not _cache:
        from PIL import Image
        meta = json.load(open(DONNEES / "relief" / "heightmap_3025_10cm.json", encoding="utf-8"))
        img = np.asarray(Image.open(DONNEES / "relief" / meta["fichier"]), dtype=np.float64)
        _cache.update(img=img, meta=meta)
    img, meta = _cache["img"], _cache["meta"]
    e = meta["emprise_noeuds_L93"]
    c = (x + O_L93[0] - e["x_min"]) / meta["taille_pixel_m"]
    r = (e["y_max"] - (y + O_L93[1])) / meta["taille_pixel_m"]
    c0, r0 = int(c), int(r)
    fc, fr = c - c0, r - r0
    v = (img[r0, c0] * (1 - fc) * (1 - fr) + img[r0, c0 + 1] * fc * (1 - fr)
         + img[r0 + 1, c0] * (1 - fc) * fr + img[r0 + 1, c0 + 1] * fc * fr)
    return meta["z_min_local_m"] + v / 65535.0 * (meta["z_max_local_m"] - meta["z_min_local_m"])


# ---------------------------------------------------------------- caméras
def regard(oeil, avant):
    """Matrice USD (convention vecteur-ligne) : la caméra regarde selon -Z local, +Y local en haut,
    haut du monde = +Z."""
    f = np.asarray(avant, float) / np.linalg.norm(avant)
    r = np.cross(f, [0.0, 0.0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    lignes = [list(r) + [0.0], list(u) + [0.0], list(-f) + [0.0], list(oeil) + [1.0]]
    return Gf.Matrix4d(*[[round(float(v), 9) + 0.0 for v in ligne] for ligne in lignes])


def direction(cap_deg, plongee_deg):
    c, p = math.radians(cap_deg), math.radians(plongee_deg)
    return np.array([math.cos(p) * math.cos(c), math.cos(p) * math.sin(c), math.sin(p)])


def fr(x):
    """Nombre décimal à la française pour les textes (1,3 m)."""
    return f"{x:g}".replace(".", ",")


def cap(v):
    return math.degrees(math.atan2(v[1], v[0]))


def focale(hfov_deg):
    return APERTURE_MM / 2.0 / math.tan(math.radians(hfov_deg) / 2.0)


def calculer():
    lanes = charger("opendrive/lanes_2026.geojson")["features"]
    surfaces = charger("surfaces/surfaces_2026.geojson")["features"]
    marquages = charger("marquages/marquages_2026.geojson")["features"]
    sol = Sol()

    # Centre du carrefour : barycentre de l'union des liaisons de jonction (raster 10 cm).
    jn = [polygones(f["geometry"])[0][0] for f in lanes
          if f["properties"].get("jonction") is True and f["properties"].get("type") == "driving"]
    tout = np.vstack(jn)
    gx, gy = np.meshgrid(np.arange(tout[:, 0].min(), tout[:, 0].max(), 0.1),
                         np.arange(tout[:, 1].min(), tout[:, 1].max(), 0.1))
    masque = np.zeros(gx.shape, bool)
    for r in jn:
        dedans = np.zeros(gx.shape, bool)
        for (xa, ya), (xb, yb) in zip(r[:-1], r[1:]):
            if ya != yb:
                dedans ^= ((ya > gy) != (yb > gy)) & (gx < (xb - xa) * (gy - ya) / (yb - ya) + xa)
        masque |= dedans
    centre_xy = np.array([gx[masque].mean(), gy[masque].mean()])
    z_c, _ = sol.z(*centre_xy)
    centre = np.r_[centre_xy, z_c]
    feux = {f["properties"]["nom"]: polygones(f["geometry"])[0][0][:-1].mean(0) for f in lanes
            if f["properties"].get("sous_type") == "stopLine"}

    cams = []

    # cam1 : vue d'ensemble depuis le sud.
    xy = centre_xy + np.array([0.0, -CAM1_RECUL_M])
    zs, prim = sol.z(*xy)
    oeil = np.r_[xy, zs + CAM1_HAUTEUR_M]
    cams.append(dict(
        nom="cam1_ensemble_sud", oeil=oeil, avant=centre - oeil, cible=centre, z_sol=zs,
        prim_sol=prim, hfov=CAM1_HFOV, clip=(1.0, 5000.0),
        doc=f"Vue d'ensemble depuis le sud : {CAM1_HAUTEUR_M:.0f} m au-dessus du sol, "
            f"{CAM1_RECUL_M:.0f} m au sud du centre du carrefour (barycentre des liaisons de "
            f"jonction OpenDRIVE), visée de ce centre."))

    # cam2 : conducteur sur Verdun SO, chaussée sens NE (route 1), voie de droite (-2).
    ref = ligne_reference(lanes, 1)
    s_feux, _ = projeter_ref(ref, feux["ligne_effet_feux Verdun SW"])
    p, h, n, voies = coupe_voies(lanes, 1, ref, s_feux - CAM2_AVANT_FEUX_M)
    t = 0.5 * (voies[-2][1] + voies[-2][2]) + DECALAGE_CONDUCTEUR_M   # sens = sens de la référence
    xy = p + t * n
    zs, prim = sol.z(*xy)
    pf, _, nf, _ = coupe_voies(lanes, 1, ref, s_feux)
    vise = pf + t * nf
    cams.append(dict(
        nom="cam2_conducteur_verdun_so", oeil=np.r_[xy, zs + OEIL_CONDUCTEUR_M],
        avant=direction(cap(vise - xy), PLONGEE_CONDUCTEUR), cible=np.r_[vise, sol.z(*vise)[0]],
        z_sol=zs, prim_sol=prim, hfov=HFOV_CONDUCTEUR, clip=(0.05, 5000.0),
        doc=f"Conducteur (oeil à {fr(OEIL_CONDUCTEUR_M)} m) sur l'avenue de Verdun SO, chaussée "
            f"sens NE (entrante), voie de droite (voie OpenDRIVE -2 de la route 1), "
            f"{fr(DECALAGE_CONDUCTEUR_M)} m à gauche du centre de voie, "
            f"{CAM2_AVANT_FEUX_M:.0f} m avant la ligne d'effet des feux ; regard le long de la "
            f"voie vers le carrefour, plongée {fr(-PLONGEE_CONDUCTEUR)} deg."))

    # cam3 : piéton sur la nouvelle traversée SO (bandes neuves 2025, zébra reculé de 8,8 m).
    bandes = [f for f in marquages if f["properties"]["type"] == "passage_pieton_bande"
              and f["properties"]["branche"] == "verdun_sw"
              and f["properties"]["groupe"] == "passage_pieton"
              and f["properties"]["etat"] == "neuf_2025"]
    cb = np.array([polygones(f["geometry"])[0][0][:-1].mean(0) for f in bandes])
    ordre = np.argsort(cb[:, 0])
    groupes, g = [], [ordre[0]]
    for i, j in zip(ordre[:-1], ordre[1:]):        # regroupement : écart > 5 m = autre traversée
        if np.linalg.norm(cb[j] - cb[i]) > 5.0:
            groupes.append(g)
            g = []
        g.append(j)
    groupes.append(g)
    feu_so = feux["ligne_effet_feux Verdun SW"]
    g = min(groupes, key=lambda g: np.linalg.norm(cb[g].mean(0) - feu_so))
    c0 = cb[g].mean(0)
    axe = np.linalg.svd(cb[g] - c0)[2][0]
    axe = axe if axe[0] > 0 else -axe            # axe NO -> SE

    def classe(pt):
        return [f["properties"]["classe"] for f in surfaces
                for poly in polygones(f["geometry"]) if dans_polygone(pt, poly)]

    def bord(signe):
        """Distance du centre de la traversée au trottoir (fin de chaussée et de refuge)."""
        k = 0.0
        while {"chaussee", "ilot"} & set(classe(c0 + signe * k * axe)):
            k += 0.05
        return k
    k_se, k_no = bord(+1), bord(-1)
    xy = c0 + (k_se + RECUL_PIETON_M) * axe
    zs, prim = sol.z(*xy)
    vise = c0 - k_no * axe
    cams.append(dict(
        nom="cam3_pieton_traversee_so", oeil=np.r_[xy, zs + OEIL_PIETON_M],
        avant=direction(cap(vise - xy), PLONGEE_PIETON), cible=np.r_[vise, sol.z(*vise)[0]],
        z_sol=zs, prim_sol=prim, hfov=HFOV_PIETON, clip=(0.05, 5000.0),
        bandes=[bandes[i]["properties"]["id"] for i in g],
        cible_controle=np.r_[vise, sol.z(*vise)[0]],
        nom_cible_controle="l'extrémité NO de la traversée",
        doc=f"Piéton (oeil à {fr(OEIL_PIETON_M)} m) en attente sur le trottoir SE, "
            f"{fr(RECUL_PIETON_M)} m derrière la bordure, dans l'axe de la nouvelle traversée de "
            f"Verdun SO (zébra neuf 2025, reculé de 8,8 m vers le SO par les travaux ; refuge "
            f"central entre les deux chaussées). Regard vers le NO à travers les deux zébras et le "
            f"refuge (feux piétons R12 du refuge et de l'extrémité NO face à la caméra), plongée "
            f"{fr(-PLONGEE_PIETON)} deg."))

    # cam4 : conducteur sur l'avenue du Vercors, voie entrante (route 6, voies positives).
    ref = ligne_reference(lanes, 6)
    s_feux, _ = projeter_ref(ref, feux["ligne_effet_feux Vercors"])
    p, h, n, voies = coupe_voies(lanes, 6, ref, s_feux + CAM4_AVANT_FEUX_M)
    entrantes = [k for k, v in voies.items()
                 if k > 0 and v[0] == "driving" and v[2] - v[1] > 2.5]   # voies pleine largeur
    v_dr = max(entrantes)                         # voie entrante la plus à droite (seule ici)
    # sens de circulation opposé à la référence : la gauche du conducteur est vers -t
    t = 0.5 * (voies[v_dr][1] + voies[v_dr][2]) - DECALAGE_CONDUCTEUR_M
    xy = p + t * n
    zs, prim = sol.z(*xy)
    pf, _, nf, _ = coupe_voies(lanes, 6, ref, s_feux)
    vise = pf + t * nf
    cams.append(dict(
        nom="cam4_conducteur_vercors", oeil=np.r_[xy, zs + OEIL_CONDUCTEUR_M],
        avant=direction(cap(vise - xy), PLONGEE_CONDUCTEUR), cible=np.r_[vise, sol.z(*vise)[0]],
        z_sol=zs, prim_sol=prim, hfov=HFOV_CONDUCTEUR, clip=(0.05, 5000.0), voie=v_dr,
        doc=f"Conducteur (oeil à {fr(OEIL_CONDUCTEUR_M)} m) sur l'avenue du Vercors, voie entrante "
            f"(voie OpenDRIVE {v_dr} de la route 6, seule voie entrante à cet endroit), "
            f"{fr(DECALAGE_CONDUCTEUR_M)} m à gauche du centre de voie, "
            f"{CAM4_AVANT_FEUX_M:.0f} m avant la ligne d'effet des feux ; regard le long de la "
            f"voie vers le carrefour, plongée {fr(-PLONGEE_CONDUCTEUR)} deg."))

    for c in cams:
        c["z_heightmap"] = z_heightmap(*(c["oeil"][:2]))
        c["classes"] = classe(c["oeil"][:2])
    return centre, feux, cams, (c0, axe, k_no, k_se)


def ecrire(cams, centre):
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    st.SetDefaultPrim(st.OverridePrim("/World"))
    lay = st.GetRootLayer()
    lay.documentation = ("Caméras de contrôle du carrefour Paquet Jardin (repère local du paquet, "
                         "Z haut, mètres). Couche à part, à empiler au-dessus de "
                         "paquet_jardin_2026.usda ; générée par generer_cameras.py.")
    lay.customLayerData = {
        "origine_locale_L93_NGF": "917279.43 6460289.98 216.3",
        "centre_carrefour_local": Gf.Vec3d(*[round(float(v), 3) for v in centre]),
        "source": "recon/out/paquet_jardin/package (donnees/ + layers/voirie.usdc, terrain.usdc)",
    }
    UsdGeom.Scope.Define(st, "/World/Cameras")
    for c in cams:
        cam = UsdGeom.Camera.Define(st, f"/World/Cameras/{c['nom']}")
        cam.CreateProjectionAttr(UsdGeom.Tokens.perspective)
        cam.CreateFocalLengthAttr(round(focale(c["hfov"]), 4))
        cam.CreateHorizontalApertureAttr(APERTURE_MM)
        cam.CreateVerticalApertureAttr(APERTURE_MM)
        cam.CreateClippingRangeAttr(Gf.Vec2f(*c["clip"]))
        cam.CreateFStopAttr(0.0)
        cam.CreateFocusDistanceAttr(round(float(np.linalg.norm(c["cible"] - c["oeil"])), 2))
        cam.AddTransformOp().Set(regard(c["oeil"], c["avant"]))
        prim = cam.GetPrim()
        prim.SetDocumentation(c["doc"])
        l93 = c["oeil"] + O_L93
        av = c["avant"] / np.linalg.norm(c["avant"])
        couche = "voirie" if "Voirie" in c["prim_sol"] else "terrain"
        cd = {
            "position_locale_m": Gf.Vec3d(*[round(float(v), 3) for v in c["oeil"]]),
            "position_L93_NGF": Gf.Vec3d(*[round(float(v), 3) for v in l93]),
            "cible_locale_m": Gf.Vec3d(*[round(float(v), 3) for v in c["cible"]]),
            "z_sol_local_m": round(float(c["z_sol"]), 3),
            "z_sol_source": f"{c['prim_sol']} (layers/{couche}.usdc)",
            "z_sol_heightmap_local_m": round(float(c["z_heightmap"]), 3),
            "hfov_deg": float(c["hfov"]),
            "azimut_deg": round((90.0 - cap(c["avant"])) % 360.0, 2),   # depuis le nord, horaire
            "plongee_deg": round(math.degrees(math.asin(av[2])), 2),
        }
        if "bandes" in c:
            cd["bandes_zebra"] = ", ".join(c["bandes"])
        prim.SetCustomData(cd)
    lay.GetPrimAtPath("/World").specifier = Sdf.SpecifierOver   # Define() l'avait passé en def
    lay.Export(str(SORTIE))
    print(f"écrit : {SORTIE}")


# ---------------------------------------------------------------- contrôles
def controler(cams, centre):
    racine = Usd.Stage.Open(str(PAQUET / "paquet_jardin_2026.usda"))
    racine.GetSessionLayer().subLayerPaths.append(str(SORTIE).replace("\\", "/"))
    tc = Usd.TimeCode.Default()
    # boîtes orientées des instances (mobilier, végétation)
    bc = UsdGeom.BBoxCache(tc, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    boites = []
    for prim in racine.Traverse():
        if not prim.IsA(UsdGeom.PointInstancer):
            continue
        pi = UsdGeom.PointInstancer(prim)
        protos = pi.GetPrototypesRel().GetTargets()
        idx = pi.GetProtoIndicesAttr().Get()
        xf = pi.ComputeInstanceTransformsAtTime(tc, tc)
        l2w = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(tc)
        bornes = [bc.ComputeUntransformedBound(racine.GetPrimAtPath(p)) for p in protos]
        for k, (i, m) in enumerate(zip(idx, xf)):
            b = bornes[i]
            mat = b.GetMatrix() * m * l2w
            boites.append((f"{prim.GetName()}[{k}]:{protos[i].name}", np.asarray(mat.GetInverse()),
                           np.asarray(b.GetRange().GetMin()), np.asarray(b.GetRange().GetMax())))
    bat = charger("objets/batiments_local.geojson")["features"]
    clo = UsdGeom.Mesh(racine.GetPrimAtPath("/World/Mobilier/clotures"))
    cpts = np.asarray(clo.GetPointsAttr().Get())
    cnt = np.asarray(clo.GetFaceVertexCountsAttr().Get())
    cidx = np.asarray(clo.GetFaceVertexIndicesAttr().Get())
    deb = np.r_[0, np.cumsum(cnt)[:-1]]
    ctri = np.vstack([cpts[np.c_[cidx[deb[cnt == k]], cidx[deb[cnt == k] + j],
                                 cidx[deb[cnt == k] + j + 1]]]
                      for k in range(3, cnt.max() + 1) for j in range(1, k - 1)])
    cmn, cmx = ctri.min(1) - 0.05, ctri.max(1) + 0.05     # boîtes des triangles de clôture
    ok_global = True
    print(f"centre du carrefour (local) : {np.round(centre, 2)}")
    for c in cams:
        cible_ctl = c.get("cible_controle", centre)
        prim = racine.GetPrimAtPath(f"/World/Cameras/{c['nom']}")
        assert prim and prim.IsA(UsdGeom.Camera), c["nom"]
        m = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(tc)
        oeil = np.asarray(m.ExtractTranslation())
        av = np.asarray(m.TransformDir(Gf.Vec3d(0, 0, -1)).GetNormalized())
        haut = np.asarray(m.TransformDir(Gf.Vec3d(0, 1, 0)).GetNormalized())
        gcam = UsdGeom.Camera(prim).GetCamera(tc)
        hfov = gcam.GetFieldOfView(Gf.Camera.FOVHorizontal)
        vers_c = (centre - oeil) / np.linalg.norm(centre - oeil)
        ang_c = math.degrees(math.acos(np.clip(np.dot(av, vers_c), -1, 1)))
        # échantillons du champ jusqu'à 2 m devant l'objectif
        r = np.cross(av, [0, 0, 1.0])
        r /= np.linalg.norm(r)
        u = np.cross(r, av)
        tg = math.tan(math.radians(hfov) / 2)
        ech = np.array([oeil + d * (av + a * tg * r + b * tg * u)
                        for d in np.linspace(0.05, 2.0, 20)
                        for a in np.linspace(-1, 1, 21) for b in np.linspace(-1, 1, 21)])
        e4 = np.c_[ech, np.ones(len(ech))]
        obst, proche = [], (np.inf, "")
        for nom, inv, mn, mx in boites:
            q = (e4 @ inv)[:, :3]
            if np.any(np.all((q >= mn) & (q <= mx), axis=1)):
                obst.append(nom)
            centre_b = np.r_[0.5 * (mn + mx), 1.0] @ np.linalg.inv(inv)
            v = centre_b[:3] - oeil
            cos_v = np.dot(v, av) / np.linalg.norm(v)
            if cos_v > math.cos(math.radians(hfov / 2)):        # centre de boîte dans le champ
                proche = min(proche, (float(np.linalg.norm(v)), nom))
        for f in bat:
            p = f["properties"]
            for poly in f["geometry"]["coordinates"][:1]:
                ring = np.asarray(poly)[:, :2]
                z0 = p.get("z_sol_local", 0.0)
                z1 = z0 + (p.get("hauteur_faite_m") or 0.0)
                if any(dans_anneau(e[:2], ring) and z0 <= e[2] <= z1 for e in ech):
                    obst.append(f"batiment {p.get('id')}")
        dans_clo = np.all((ech[:, None, :] >= cmn[None]) & (ech[:, None, :] <= cmx[None]), axis=2)
        if dans_clo.any():
            obst.append(f"clôture ({int(dans_clo.any(0).sum())} triangles)")
        sol_ok = ("chaussee" in c["classes"]) if "conducteur" in c["nom"] else (
            any(k in c["classes"] for k in ("trottoir", "ilot")) if "pieton" in c["nom"] else True)
        ecart_hm = c["z_sol"] - c["z_heightmap"]
        print(f"\n{c['nom']}")
        e, n, alt = oeil + O_L93
        print(f"  oeil local {np.round(oeil, 3)}  L93 ({e:.2f}, {n:.2f})  NGF {alt:.2f}")
        attendu = c["avant"] / np.linalg.norm(c["avant"])
        print(f"  avant {np.round(av, 4)} (attendu {np.round(attendu, 4)})"
              f"  haut {np.round(haut, 3)}  hFOV {hfov:.2f} deg")
        print(f"  sol z={c['z_sol']:.3f} ({c['prim_sol']}) ; heightmap {c['z_heightmap']:.3f}"
              f" (écart {ecart_hm * 100:.1f} cm) ; classes surfaces_2026 : {c['classes']}")
        vc = (cible_ctl - oeil) / np.linalg.norm(cible_ctl - oeil)
        ang_ctl = math.degrees(math.acos(np.clip(np.dot(av, vc), -1, 1)))
        print(f"  écart de visée vers le centre du carrefour : {ang_c:.1f} deg")
        if "cible_controle" in c:
            print(f"  écart de visée vers {c['nom_cible_controle']} : {ang_ctl:.1f} deg "
                  f"(le centre du carrefour est volontairement hors champ)")
        print(f"  obstacles à moins de 2 m devant l'objectif : {obst or 'aucun'}")
        print(f"  instance la plus proche dans le champ : {proche[1]} à {proche[0]:.1f} m")
        ok = (np.allclose(av, attendu, atol=1e-6) and sol_ok
              and not obst and abs(ecart_hm) < 0.2 and ang_ctl < 10)
        print(f"  => {'OK' if ok else 'A VERIFIER'}")
        ok_global &= ok
    return ok_global


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    centre, _, cams, (c0, axe, k_no, k_se) = calculer()
    print(f"traversée SO 2025 : centre {np.round(c0, 2)}, axe NO->SE {np.round(axe, 4)}, "
          f"bordure NO à {k_no:.2f} m, bordure SE à {k_se:.2f} m du centre")
    if "--controle-seul" not in sys.argv:
        ecrire(cams, centre)
    ok = controler(cams, centre)
    print("\nCONTROLES : " + ("OK" if ok else "à vérifier"))


if __name__ == "__main__":
    main()
