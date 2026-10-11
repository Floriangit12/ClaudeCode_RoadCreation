"""Outils communs du pilote « sol avant travaux » (lecture seule des données du dépôt).

Repère : local = L93 − O(917279.43, 6460289.98), z = NGF − 216,30.
Rasters lus :
  - ortho PCRS 5 cm du 10/05/2022 (data/sites/paquet_jardin/ortho5cm_2022, .jgw) ;
  - BD ORTHO IGN 2024 20 cm (09/08/2024) et Pléiades 2025 50 cm (data/raw/ortho_recentes), recalées
    sur le PCRS 2022 par recalage.json (position PCRS = position lue − (dx, dy)) ;
  - LiDAR HD 2021 dérivés 15 cm (pente, intensité sol ; JPEG, lecture visuelle seulement) ;
  - heightmap 16 bits 10 cm du paquet v1 (sol nu « 2026 » = sol nu LiDAR 2021 débruité hors zones
    modifiées ; zones modifiées dans relief_zones_2026.geojson) ;
  - plan projet 2025 (raster géoréférencé, affine par tuile).
Aucune dépendance hors numpy / Pillow / pyproj.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[6]
SITE = RACINE / "data/sites/paquet_jardin"
O = np.array([917279.43, 6460289.98])
ZO = 216.30
SORTIE = ICI.parent
V2 = RACINE / "recon/out/paquet_jardin/v2"
PAQUET = RACINE / "recon/out/paquet_jardin/package/donnees"


def lire_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def ecrire_json(p, d):
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


_T = None


def wgs_vers_l93(a):
    global _T
    if _T is None:
        from pyproj import Transformer
        _T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    x, y = _T.transform(a[:, 0], a[:, 1])
    return np.c_[x, y]


def lignes(geom):
    t = geom["type"]
    if t == "LineString":
        return [geom["coordinates"]]
    if t == "MultiLineString":
        return geom["coordinates"]
    if t == "Polygon":
        return geom["coordinates"]
    if t == "MultiPolygon":
        return [r for p in geom["coordinates"] for r in p]
    return []


def charger_lignes(chemin, wgs=False, filtre=None):
    """[(indice, propriétés, polyligne locale (N,2), z (N,) ou None)]"""
    out = []
    for i, f in enumerate(lire_json(chemin)["features"]):
        if filtre and not filtre(f["properties"]):
            continue
        for c in lignes(f["geometry"]):
            a = np.asarray(c, dtype=float)
            xy = a[:, :2]
            if wgs:
                xy = wgs_vers_l93(xy)
            z = a[:, 2] if a.shape[1] > 2 else None
            out.append((i, f["properties"], xy - O, z))
    return out


# ------------------------------------------------------------------ rasters géoréférencés
class Mosaique:
    """Tuiles (jpg + .jgw ou index.json) échantillonnées sur une grille locale."""

    def __init__(self, tuiles):
        # tuiles : [(chemin, a, c, e, f)] avec x = c + a·col, y = f + e·ligne (centre de pixel)
        self.tuiles = tuiles
        self._cache = {}

    def _img(self, p):
        if p not in self._cache:
            self._cache[p] = np.asarray(Image.open(p).convert("RGB"))
        return self._cache[p]

    def echantillonner(self, X, Y):
        """X, Y : L93 (tableaux de même forme) -> RGB uint8, plus proche voisin."""
        out = np.zeros(X.shape + (3,), np.uint8)
        for p, a, c, e, f in self.tuiles:
            im = self._img(p)
            h, w = im.shape[:2]
            col = np.floor((X - c) / a + 0.5).astype(int)
            lig = np.floor((Y - f) / e + 0.5).astype(int)
            m = (col >= 0) & (col < w) & (lig >= 0) & (lig < h)
            out[m] = im[lig[m], col[m]]
        return out


def mosaique_jgw(dossier, motif="*.jpg", dx=0.0, dy=0.0):
    t = []
    for p in sorted(Path(dossier).glob(motif)):
        j = p.with_suffix(".jgw")
        if not j.exists():
            continue
        a, _, _, e, c, f = [float(v) for v in j.read_text().split()]
        t.append((p, a, c - dx, e, f - dy))
    return Mosaique(t)


def mosaique_index(dossier, res):
    """Rasters LiDAR (index.json : l93_bbox de chaque tuile, coin haut-gauche = (x0, y1))."""
    t = []
    for it in lire_json(Path(dossier) / "index.json"):
        x0, y0, x1, y1 = it["l93_bbox"]
        t.append((Path(dossier) / it["file"], res, x0 + res / 2, -res, y1 - res / 2))
    return Mosaique(t)


class MosaiquePlan(Mosaique):
    """Plan projet 2025 : affine pixel -> L93 par tuile (rotation)."""

    def echantillonner(self, X, Y):
        out = np.full(X.shape + (3,), 255, np.uint8)
        for p, A in self.tuiles:
            im = self._img(p)
            h, w = im.shape[:2]
            a, b, c, d, e, f = A
            M = np.array([[a, b], [d, e]])
            Mi = np.linalg.inv(M)
            u = Mi[0, 0] * (X - c) + Mi[0, 1] * (Y - f)
            v = Mi[1, 0] * (X - c) + Mi[1, 1] * (Y - f)
            col, lig = np.floor(u + 0.5).astype(int), np.floor(v + 0.5).astype(int)
            m = (col >= 0) & (col < w) & (lig >= 0) & (lig < h)
            out[m] = im[lig[m], col[m]]
        return out


def mosaique_plan():
    d = SITE / "plan_projet_2025/tuiles"
    return MosaiquePlan([(d / it["file"], it["affine_L93"]) for it in lire_json(d / "index.json")])


def recalage(couche):
    r = lire_json(V2 / "enrichi/recensement/ortho_recentes/recalage.json")["couches"][couche]
    return r["dx_m"], r["dy_m"]


def sources_raster():
    raw = RACINE / "data/raw/ortho_recentes"
    dx24, dy24 = recalage("ign_bdortho_2024_rvb_20cm")
    dxp, dyp = recalage("ign_pleiades_2025_50cm")
    return {
        "ortho2022": mosaique_jgw(SITE / "ortho5cm_2022"),
        "ortho2024": mosaique_jgw(raw / "ign_bdortho_2024_rvb_20cm", dx=dx24, dy=dy24),
        "pleiades2025": mosaique_jgw(raw / "ign_pleiades_2025_50cm", dx=dxp, dy=dyp),
        "pente2021": mosaique_index(SITE / "lidar/slope_pct_15cm", 0.15),
        "intensite2021": mosaique_index(SITE / "lidar/intensity_ground_15cm", 0.15),
        "hauteur2021": mosaique_index(SITE / "lidar/height_above_ground_15cm", 0.15),
        "plan2025": mosaique_plan(),
    }


def grille(bbox_local, res):
    """bbox locale (x0, y0, x1, y1) -> X, Y L93 des centres de pixels (ligne 0 = nord)."""
    x0, y0, x1, y1 = bbox_local
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    xs = x0 + (np.arange(w) + 0.5) * res + O[0]
    ys = y1 - (np.arange(h) + 0.5) * res + O[1]
    return np.meshgrid(xs, ys)


# ------------------------------------------------------------------ heightmap 16 bits (paquet v1)
class Heightmap:
    def __init__(self, chemin_json=PAQUET / "relief/heightmap_3025_10cm.json"):
        self.meta = lire_json(chemin_json)
        a = np.asarray(Image.open(Path(chemin_json).with_name(self.meta["fichier"]))).astype(np.float64)
        z0, z1 = self.meta["z_min_m_NGF"], self.meta["z_max_m_NGF"]
        self.z = z0 + a / 65535.0 * (z1 - z0)
        e = self.meta["emprise_noeuds_L93"]
        self.x0, self.y1, self.pas = e["x_min"], e["y_max"], self.meta["taille_pixel_m"]
        self.n = self.z.shape[0]

    def __call__(self, x, y):
        """x, y : L93 -> z NGF (bilinéaire)."""
        x, y = np.asarray(x, float), np.asarray(y, float)
        fc = np.clip((x - self.x0) / self.pas, 0, self.n - 1.000001)
        fr = np.clip((self.y1 - y) / self.pas, 0, self.n - 1.000001)
        c, r = np.floor(fc).astype(int), np.floor(fr).astype(int)
        tc, tr = fc - c, fr - r
        z = self.z
        return ((z[r, c] * (1 - tc) + z[r, c + 1] * tc) * (1 - tr)
                + (z[r + 1, c] * (1 - tc) + z[r + 1, c + 1] * tc) * tr)


# ------------------------------------------------------------------ géométrie
def abscisses(P):
    return np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]


def reechantillonner(P, pas):
    S = abscisses(P)
    if S[-1] <= 0:
        return P[:1], np.zeros(1), np.array([[1.0, 0.0]])
    s = np.arange(pas / 2, S[-1], pas) if S[-1] > pas else np.array([S[-1] / 2])
    i = np.clip(np.searchsorted(S, s, side="right") - 1, 0, len(P) - 2)
    L = np.maximum(S[i + 1] - S[i], 1e-12)
    t = ((s - S[i]) / L)[:, None]
    pts = P[i] * (1 - t) + P[i + 1] * t
    tg = (P[i + 1] - P[i]) / L[:, None]
    return pts, s, tg


def dist_point_segments(Q, P):
    """Distance de chaque point Q (M,2) à la polyligne P (N,2)."""
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    d = np.full(len(Q), np.inf)
    for k in range(0, len(Q), 4000):
        q = Q[k:k + 4000]
        t = np.clip(((q[:, None, :] - A[None]) * AB[None]).sum(-1) / L2[None], 0, 1)
        proj = A[None] + t[..., None] * AB[None]
        d[k:k + 4000] = np.sqrt(((q[:, None, :] - proj) ** 2).sum(-1)).min(1)
    return d


def aire_polygone(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def rasteriser_polygones(anneaux_par_poly, bbox_local, res):
    """[[anneau ext, trous...], ...] (local) -> carte de comptage (uint16) : nb de polygones couvrant
    chaque pixel (parité par polygone, trous compris)."""
    x0, y0, x1, y1 = bbox_local
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    cpt = np.zeros((h, w), np.uint16)
    for anneaux in anneaux_par_poly:
        im = Image.new("1", (w, h), 0)
        dr = ImageDraw.Draw(im)
        masque = np.zeros((h, w), bool)
        for r in anneaux:
            u = (r[:, 0] - x0) / res
            v = (y1 - r[:, 1]) / res
            im2 = Image.new("1", (w, h), 0)
            ImageDraw.Draw(im2).polygon(list(zip(u.tolist(), v.tolist())), fill=1)
            masque ^= np.asarray(im2, bool)
        cpt += masque
    return cpt


# ------------------------------------------------------------------ dessin
def police(t=14):
    for nom in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except OSError:
            pass
    return ImageFont.load_default()


def vers_px(P, bbox_local, res):
    x0, y0, x1, y1 = bbox_local
    return list(zip(((P[:, 0] - x0) / res).tolist(), ((y1 - P[:, 1]) / res).tolist()))


def tracer(dr, P, bbox_local, res, coul, larg=2):
    if len(P) >= 2:
        dr.line(vers_px(P, bbox_local, res), fill=coul, width=larg)


def cartouche(im, texte, t=16):
    dr = ImageDraw.Draw(im)
    f = police(t)
    dr.rectangle([0, 0, im.width, t + 8], fill=(0, 0, 0))
    dr.text((4, 3), texte, fill=(255, 255, 255), font=f)
    return im


def echelle(im, res, longueur_m=5, t=13):
    dr = ImageDraw.Draw(im)
    L = longueur_m / res
    x, y = 10, im.height - 18
    dr.rectangle([x - 3, y - 14, x + L + 30, y + 8], fill=(0, 0, 0))
    dr.line([(x, y), (x + L, y)], fill=(255, 255, 255), width=3)
    dr.text((x + L + 4, y - 9), f"{longueur_m} m", fill=(255, 255, 255), font=police(t))


# ------------------------------------------------------------------ zones modifiées du relief v1 (heightmap)
class ZonesModifiees:
    """Carte (pas 0,10 m, repère local) : 0 = heightmap v1 = sol nu LiDAR 2021 débruité ; 1 = chaussée 2026
    (lissée, anciens îlots arasés) ; 2 = autre zone modifiée (rehaussée 2025, traversée abaissée, trottoir
    par défaut, chantier régalé)."""

    def __init__(self, res=0.10):
        self.res, self.x0, self.y1 = res, -151.0, 151.0
        n = int(round(302 / res))
        cpt = np.zeros((n, n), np.uint8)
        for f in lire_json(PAQUET / "relief/relief_zones_2026.geojson")["features"]:
            code = 1 if f["properties"].get("zone") == "chaussee_2026" else 2
            g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for p in polys:
                m = np.zeros((n, n), bool)
                for r in p:
                    r = np.asarray(r, float)[:, :2] - O
                    im = Image.new("1", (n, n), 0)
                    ImageDraw.Draw(im).polygon(list(zip(((r[:, 0] - self.x0) / res).tolist(),
                                                        ((self.y1 - r[:, 1]) / res).tolist())), fill=1)
                    m ^= np.asarray(im, bool)
                cpt[m] = np.maximum(cpt[m], code)
        self.c = cpt

    def __call__(self, x, y):
        """x, y locaux -> code (0, 1, 2)."""
        n = self.c.shape[0]
        c = np.clip(np.floor((np.asarray(x) - self.x0) / self.res).astype(int), 0, n - 1)
        r = np.clip(np.floor((self.y1 - np.asarray(y)) / self.res).astype(int), 0, n - 1)
        return self.c[r, c]


def luminance(rgb):
    rgb = rgb.astype(np.float64)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def pente_norm(rgb):
    """Palette de type « jet » de la pente LiDAR 2021 : bleu (0) -> cyan -> jaune -> rouge (1)."""
    a = rgb.astype(np.float64) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = np.maximum(mx - mn, 1e-9)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    h = np.where(h > 300, 0, h)          # magenta éventuel -> rouge
    return np.clip((240.0 - h) / 240.0, 0, 1)
