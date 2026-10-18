"""Géographie de la comparaison multivues : Lambert-93, convergence des méridiens, position du soleil, ancrage du
modèle fabriqué (repère local (s, t) du générateur) dans le Lambert-93, données OSM locales.

Conventions
- Azimut : degrés, compté depuis le nord dans le sens horaire. « vrai » = nord géographique (Panoramax
  `view:azimuth`), « grille » = nord du Lambert-93 ; azimut grille = azimut vrai + gamma, gamma = azimut grille du
  nord vrai (≈ − 2,0° à Meylan), calculé point par point.
- Repère du modèle : celui du générateur (x = s le long du tronçon droit, y = t vers la gauche, z haut, mètres).
  L'ancrage donne l'origine O (L93) et l'azimut grille alpha de l'axe +x : P_L93 = O + s·u + t·v, u = (sin a, cos a),
  v = (− cos a, sin a) (u tourné de + 90°).
- Lacet dans le modèle : angle depuis +x, sens trigonométrique ; une direction d'azimut grille A a le lacet
  alpha − A.
"""
import gzip
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyproj import Transformer

DEPOT = Path(__file__).resolve().parents[3]
OSM = DEPOT / "data" / "vector_gz" / "osm"

_VERS_L93 = Transformer.from_crs(4326, 2154, always_xy=True)
_VERS_WGS = Transformer.from_crs(2154, 4326, always_xy=True)


def l93(lon, lat):
    x, y = _VERS_L93.transform(lon, lat)
    return float(x), float(y)


def wgs(x, y):
    lon, lat = _VERS_WGS.transform(x, y)
    return float(lon), float(lat)


def gamma(lon, lat):
    """Azimut grille (Lambert-93) du nord vrai au point (degrés)."""
    x0, y0 = l93(lon, lat)
    x1, y1 = l93(lon, lat + 0.001)
    return math.degrees(math.atan2(x1 - x0, y1 - y0))


def az_vrai_vers_grille(az, lon, lat):
    return (az + gamma(lon, lat)) % 360.0


def ecart_angle(a, b):
    """a − b ramené dans ]− 180 ; 180]."""
    return (a - b + 180.0) % 360.0 - 180.0


# ------------------------------------------------------------------------------------------------ soleil
def lire_date(s):
    """Date ISO (Panoramax) -> datetime UTC."""
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def soleil(date_utc, lon, lat):
    """Hauteur et azimut vrai (degrés) du soleil (algorithme simplifié de l'almanach, précision ≈ 0,05°)."""
    d = date_utc if isinstance(date_utc, datetime) else lire_date(date_utc)
    jd = d.timestamp() / 86400.0 + 2440587.5
    n = jd - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360.0
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    gmst = (18.697374558 + 24.06570982441908 * n) % 24.0
    ha = math.radians((gmst + lon / 15.0) * 15.0) - ra
    phi = math.radians(lat)
    el = math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(ha))
    az = math.atan2(-math.sin(ha), math.tan(dec) * math.cos(phi) - math.sin(phi) * math.cos(ha))
    return math.degrees(el), math.degrees(az) % 360.0


# ------------------------------------------------------------------------------------------------ OSM local
def _lire_osm(nom):
    with gzip.open(OSM / f"{nom}.geojson.gz", "rt", encoding="utf-8") as f:
        return json.load(f)["features"]


_CACHE_OSM = {}


def osm(nom):
    if nom not in _CACHE_OSM:
        _CACHE_OSM[nom] = _lire_osm(nom)
    return _CACHE_OSM[nom]


def osm_par_id(nom, ids):
    ids = set(ids)
    return [f for f in osm(nom) if f["properties"].get("osm_id") in ids]


def lignes_l93(features):
    """Polylignes L93 (liste de tableaux (N, 2)) des LineString / MultiLineString."""
    out = []
    for f in features:
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for p in parts:
            out.append(np.array([l93(*c[:2]) for c in p]))
    return out


def densifier(poly, pas=1.0):
    pts = [poly[0]]
    for a, b in zip(poly[:-1], poly[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / pas)))
        for k in range(1, n + 1):
            pts.append(a + (b - a) * k / n)
    return np.array(pts)


# ------------------------------------------------------------------------------------------------ ancrage
class Ancrage:
    """Passage repère du modèle (s, t, z) <-> Lambert-93."""

    def __init__(self, ox, oy, alpha):
        self.O = np.array([ox, oy], dtype=np.float64)
        self.alpha = float(alpha) % 360.0
        a = math.radians(self.alpha)
        self.u = np.array([math.sin(a), math.cos(a)])
        self.v = np.array([-math.cos(a), math.sin(a)])

    def vers_l93(self, s, t):
        s, t = np.asarray(s, dtype=np.float64), np.asarray(t, dtype=np.float64)
        return self.O[0] + s * self.u[0] + t * self.v[0], self.O[1] + s * self.u[1] + t * self.v[1]

    def vers_modele(self, x, y):
        d = np.stack([np.asarray(x, dtype=np.float64) - self.O[0], np.asarray(y, dtype=np.float64) - self.O[1]], -1)
        return d @ self.u, d @ self.v

    def lacet(self, az_grille):
        """Azimut grille -> lacet dans le modèle (degrés, sens trigonométrique depuis +x)."""
        return (self.alpha - az_grille + 180.0) % 360.0 - 180.0

    def az_grille(self, lacet):
        return (self.alpha - lacet) % 360.0

    def dict(self):
        return {"origine_l93": [round(float(self.O[0]), 3), round(float(self.O[1]), 3)],
                "azimut_grille_axe_x_deg": round(self.alpha, 3)}


def calculer_ancrage(conf, longueur, photos_ref):
    """Ancrage du modèle d'après la configuration du site (sites_meylan.json) :
    - direction : droite ajustée (ACP) sur les voies OSM nommées dans `voie_osm`, échantillonnées tous les mètres sur
      l'étendue du tronçon (0 ≤ s ≤ L, |t| ≤ 15 m autour de l'ancrage provisoire) ; sens choisi d'après les photos de
      référence (vue « vise » + lacet relatif de rendu_l2b.VUES_PHOTO) ; sans voie OSM : moyenne des photos ;
    - position : centroïde des nœuds OSM du passage (`passage_osm`, point (s, t) du modèle) s'il est donné, sinon
      moyenne des positions GNSS des photos de référence moins leur position (s, t) dans le modèle ; dans ce dernier
      cas, si `lateral_osm` est vrai, le décalage latéral est pris sur l'axe OSM (t = 0 sur la ligne OSM).
    photos_ref : {id: {"lon", "lat", "azimut_vrai"}} ; renvoie (Ancrage, diagnostic)."""
    anc = conf["ancrage"]
    diag = {"methode": [], "photos_reference": []}
    # ---- direction a priori par les photos de référence
    alphas, positions = [], []
    for r in anc.get("photos_reference", []):
        m = photos_ref[r["id"]]
        az_vue_vrai = m["azimut_vrai"] + r.get("lacet_image_deg", 0.0)
        az_vue = az_vrai_vers_grille(az_vue_vrai, m["lon"], m["lat"])
        alphas.append((az_vue + r["lacet_relatif_deg"]) % 360.0)
        positions.append((l93(m["lon"], m["lat"]), (r["s"], r["t"])))
    if alphas:
        c = np.mean([[math.sin(math.radians(a)), math.cos(math.radians(a))] for a in alphas], axis=0)
        alpha0 = math.degrees(math.atan2(c[0], c[1])) % 360.0
    else:
        alpha0 = float(anc["azimut_grille_deg"])
    diag["azimut_photos_deg"] = [round(a, 2) for a in alphas]

    def origine(alpha):
        A = Ancrage(0.0, 0.0, alpha)
        if anc.get("passage_osm"):
            pts = [l93(*f["geometry"]["coordinates"][:2]) for f in osm_par_id("crossings", anc["passage_osm"]["noeuds"])]
            if not pts:
                raise RuntimeError("nœuds OSM du passage introuvables : %s" % anc["passage_osm"]["noeuds"])
            P = np.mean(np.array(pts), axis=0)
            s, t = anc["passage_osm"]["s"], anc["passage_osm"]["t"]
            return P - s * A.u - t * A.v, "passage OSM %s -> (s, t) = (%g, %g)" % (anc["passage_osm"]["noeuds"], s, t)
        if positions:
            O = np.mean([np.array(p) - st[0] * A.u - st[1] * A.v for p, st in positions], axis=0)
            return O, "photos de référence (GNSS) à leur position estimée dans le modèle"
        return np.array(anc["origine_l93"], dtype=np.float64), "origine donnée"

    O, meth_pos = origine(alpha0)
    alpha = alpha0
    meth_dir = "photos de référence"
    if anc.get("voie_osm"):
        lignes = [densifier(p, 1.0) for p in lignes_l93(osm_par_id("roads", anc["voie_osm"]))]
        if lignes:
            pts = np.concatenate(lignes)
            for _ in range(3):
                A = Ancrage(O[0], O[1], alpha)
                s, t = A.vers_modele(pts[:, 0], pts[:, 1])
                sel = (s >= 0) & (s <= longueur) & (np.abs(t) <= 15.0)
                if sel.sum() < 10:
                    break
                q = pts[sel]
                c0 = q.mean(axis=0)
                _, _, vt = np.linalg.svd(q - c0, full_matrices=False)
                d = vt[0]
                a_fit = math.degrees(math.atan2(d[0], d[1])) % 360.0
                if abs(ecart_angle(a_fit, alpha0)) > 90.0:
                    a_fit = (a_fit + 180.0) % 360.0
                alpha = a_fit
                O, meth_pos = origine(alpha)
                meth_dir = "droite ajustée sur %s (%d points OSM sur l'étendue du tronçon)" % (anc["voie_osm"], int(sel.sum()))
            if anc.get("lateral_osm") and not anc.get("passage_osm"):
                A = Ancrage(O[0], O[1], alpha)
                s, t = A.vers_modele(pts[:, 0], pts[:, 1])
                sel = (s >= 0) & (s <= longueur) & (np.abs(t) <= 15.0)
                if sel.sum() >= 10:
                    dt = float(np.median(t[sel])) - float(anc.get("t_osm", 0.0))
                    O = O + dt * A.v
                    meth_pos += " ; latéral sur l'axe OSM (décalage %.2f m)" % dt
    A = Ancrage(O[0], O[1], alpha)
    diag["methode"] = [meth_dir, meth_pos]
    diag["ecart_direction_photos_osm_deg"] = round(ecart_angle(alpha, alpha0), 2)
    for r in anc.get("photos_reference", []):
        m = photos_ref[r["id"]]
        s, t = A.vers_modele(*l93(m["lon"], m["lat"]))
        diag["photos_reference"].append({"id": r["id"], "st_decrit": [r["s"], r["t"]],
                                         "st_gnss": [round(float(s), 2), round(float(t), 2)],
                                         "ecart_m": round(float(math.hypot(s - r["s"], t - r["t"])), 2)})
    return A, diag


# ------------------------------------------------------------------------------------------------ bâtiments
class Batiments:
    """Emprises des bâtiments OSM (L93) autour d'un point, pour les tests de visibilité en plan."""

    def __init__(self, cx, cy, rayon):
        from shapely.geometry import shape
        from shapely.ops import transform
        from shapely.strtree import STRtree
        lon, lat = wgs(cx, cy)
        dlat = rayon / 111000.0
        dlon = dlat / math.cos(math.radians(lat))
        geoms = []
        for f in osm("buildings"):
            c = f["geometry"]["coordinates"]
            while isinstance(c[0][0], list):
                c = c[0]
            if abs(c[0][0] - lon) > dlon * 1.5 or abs(c[0][1] - lat) > dlat * 1.5:
                continue
            g = transform(lambda x, y, z=None: _VERS_L93.transform(x, y), shape(f["geometry"]))
            if g.is_valid and not g.is_empty:
                geoms.append(g)
        self.geoms = geoms
        self.arbre = STRtree(geoms) if geoms else None

    def contient(self, x, y):
        from shapely.geometry import Point
        if self.arbre is None:
            return False
        p = Point(x, y)
        return any(self.geoms[i].contains(p) for i in self.arbre.query(p))

    def visibles(self, cx, cy, pts):
        """Masque des points (N, 2) L93 visibles depuis (cx, cy) : le segment ne traverse aucun bâtiment."""
        import shapely
        out = np.ones(len(pts), dtype=bool)
        if self.arbre is None or not len(pts):
            return out
        pts = np.asarray(pts, dtype=np.float64)
        segs = shapely.linestrings(np.stack([np.broadcast_to([cx, cy], pts.shape), pts], axis=1))
        paires = self.arbre.query(segs, predicate="intersects")
        out[np.unique(paires[0])] = False
        return out
