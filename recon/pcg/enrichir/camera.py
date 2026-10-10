"""Modèles de caméra et catalogue des photos Panoramax du site (enrichissement v2).

Repère : local = Lambert-93 − O, z = NGF − 216,30 (une seule conversion : decrire/commun.py `repere`).
X est, Y nord, Z haut. Angles en degrés dans les fichiers, en radians dans les calculs.

Pose d'une photo : p = [x, y, z, lacet, tangage, roulis]
- lacet : azimut GRILLE (Lambert-93) de l'axe avant, compté de +Y (nord grille) vers +X (est) ;
  lacet brut = azimut Panoramax (nord vrai) + gamma, gamma = azimut grille du nord vrai
  (≈ −2,0086° au site, calculé par photo avec pyproj) ;
- tangage : rotation autour de l'axe droit, positif = axe avant relevé ;
- roulis : rotation autour de l'axe avant, positif = côté droit relevé.
Repère caméra (d, a, h) = (droite, avant, haut) ; R (3×3) a pour lignes ces axes exprimés dans le
repère local, de sorte que c = R · (P − C).

Modèles :
- `equirect` (GoPro Max 360°, 5760×2880) : u = W·(0,5 + lon/2π), v = H·(0,5 − lat/π),
  lon = atan2(d, a) (positif à droite), lat = atan2(h, √(d²+a²)) ;
- `stenope` (photos à plat) : u = cx + f·x·(1 + k1·r²), v = cy − f·y·(1 + k1·r²), x = d/a, y = h/a.
Coordonnées pixel continues : le pixel (i, j) couvre [i, i+1[ × [j, j+1[ (centre en i + 0,5).
"""
import functools
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

ICI = Path(__file__).resolve().parent
if str(ICI.parent) not in sys.path:
    sys.path.insert(0, str(ICI.parent))
from decrire.commun import (DONNEES, MNT, O, RACINE, VECTEURS, arrondi,  # noqa: E402
                            ecrire_json, lire_json, repere)

Image.MAX_IMAGE_PIXELS = None

PHOTOS = RACINE / "data/raw/panoramax/paquet_jardin"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/enrichi/poses"
CENTRE = np.array([-1.57, -5.09])          # centre du carrefour (local)

# A priori par séquence (clé = date de prise de vue). h : hauteur de l'objectif au-dessus du sol
# (m) et son écart type (voitures GoPro : 2,1 m, valeur calée sur 2024-08 et 2025-05) ; lat_min : élévation (deg) sous laquelle l'image montre le porteur
# (capot, vélo, corps) ; hfov : champ horizontal a priori des photos à plat sans métadonnée.
SEQUENCES = {
    "2020-05-21": dict(porteur="voiture, téléphone Symphony i10", h=1.3, sh=0.4, hfov=62.0, sfov=10.0),
    "2023-03-18": dict(porteur="voiture, Galaxy J7 derrière le pare-brise", h=1.3, sh=0.4, hfov=63.0, sfov=10.0),
    "2024-05-01": dict(porteur="GoPro Max portée (piéton ou deux-roues)", h=1.9, sh=0.6, lat_min=-28.0),
    "2024-08-24": dict(porteur="GoPro Max sur voiture (capot visible)", h=2.1, sh=0.4, lat_min=-21.0),
    "2025-01-12": dict(porteur="GoPro Max sur vélo (casque)", h=1.9, sh=0.5, lat_min=-30.0),
    "2025-05-18": dict(porteur="GoPro Max sur voiture (capot visible)", h=2.1, sh=0.4, lat_min=-21.0),
    "2025-08-31": dict(porteur="voiture, Galaxy A52 par la vitre", h=1.3, sh=0.4),
    "2026-07-28": dict(porteur="GoPro Max sur voiture", h=1.8, sh=0.5, lat_min=-25.0),
}
SEQ_DEFAUT = dict(porteur="inconnu", h=1.6, sh=0.6, lat_min=-30.0, hfov=65.0, sfov=10.0)


# --------------------------------------------------------------------------- rotations
def matrice_rotation(lacet, tangage=0.0, roulis=0.0):
    """R (3×3, lignes = axes droite, avant, haut dans le repère local) ; angles en degrés."""
    ps, th, ph = (math.radians(a) for a in (lacet, tangage, roulis))
    a0 = np.array([math.sin(ps), math.cos(ps), 0.0])
    d0 = np.array([math.cos(ps), -math.sin(ps), 0.0])
    h0 = np.array([0.0, 0.0, 1.0])
    a1 = a0 * math.cos(th) + h0 * math.sin(th)
    h1 = -a0 * math.sin(th) + h0 * math.cos(th)
    d2 = d0 * math.cos(ph) + h1 * math.sin(ph)
    h2 = -d0 * math.sin(ph) + h1 * math.cos(ph)
    return np.vstack([d2, a1, h2])


# --------------------------------------------------------------------------- caméra
@dataclass
class Camera:
    """Caméra posée : modèle (`equirect` | `stenope`), intrinsèques et pose [x, y, z, lacet, tangage, roulis]."""
    modele: str
    W: int
    H: int
    pose: np.ndarray
    f: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    k1: float = 0.0

    def __post_init__(self):
        self.pose = np.asarray(self.pose, dtype=np.float64)
        if self.modele == "stenope":
            self.cx = self.cx or self.W / 2.0
            self.cy = self.cy or self.H / 2.0

    @property
    def C(self):
        return self.pose[:3]

    @property
    def R(self):
        return matrice_rotation(*self.pose[3:6])

    @property
    def px_par_rad(self):
        return self.W / (2 * math.pi) if self.modele == "equirect" else self.f

    # ---- directions repère caméra <-> pixels (indépendant de la pose)
    def cam_vers_pixel(self, c):
        """Directions caméra (N, 3) (d, a, h) -> pixels (N, 2) et masque de validité."""
        c = np.atleast_2d(c)
        d, a, h = c[:, 0], c[:, 1], c[:, 2]
        if self.modele == "equirect":
            lon = np.arctan2(d, a)
            lat = np.arctan2(h, np.hypot(d, a))
            uv = np.c_[self.W * (0.5 + lon / (2 * np.pi)), self.H * (0.5 - lat / np.pi)]
            return uv, np.ones(len(c), dtype=bool)
        ok = a > 1e-6
        a_ = np.where(ok, a, 1.0)
        x, y = d / a_, h / a_
        g = 1.0 + self.k1 * (x * x + y * y)
        uv = np.c_[self.cx + self.f * x * g, self.cy - self.f * y * g]
        ok &= (uv[:, 0] >= 0) & (uv[:, 0] < self.W) & (uv[:, 1] >= 0) & (uv[:, 1] < self.H)
        return uv, ok

    def pixel_vers_cam(self, uv):
        """Pixels (N, 2) -> directions unitaires caméra (N, 3)."""
        uv = np.atleast_2d(np.asarray(uv, dtype=np.float64))
        if self.modele == "equirect":
            lon = (uv[:, 0] / self.W - 0.5) * 2 * np.pi
            lat = (0.5 - uv[:, 1] / self.H) * np.pi
            return np.c_[np.cos(lat) * np.sin(lon), np.cos(lat) * np.cos(lon), np.sin(lat)]
        xd = (uv[:, 0] - self.cx) / self.f
        yd = -(uv[:, 1] - self.cy) / self.f
        x, y = xd.copy(), yd.copy()
        for _ in range(6):
            g = 1.0 + self.k1 * (x * x + y * y)
            x, y = xd / g, yd / g
        c = np.c_[x, np.ones_like(x), y]
        return c / np.linalg.norm(c, axis=1, keepdims=True)

    # ---- monde <-> pixels
    def monde_vers_cam(self, P):
        P = np.atleast_2d(np.asarray(P, dtype=np.float64))
        return (P - self.C) @ self.R.T

    def projeter(self, P):
        """Points locaux (N, 3) -> (pixels (N, 2), devant/dans l'image (N,), distance (N,))."""
        c = self.monde_vers_cam(P)
        uv, ok = self.cam_vers_pixel(c)
        return uv, ok, np.linalg.norm(c, axis=1)

    def rayons(self, uv):
        """Pixels (N, 2) -> directions unitaires dans le repère local (N, 3)."""
        return self.pixel_vers_cam(uv) @ self.R


# --------------------------------------------------------------------------- catalogue
@dataclass
class Photo:
    id: str
    id8: str
    date: str
    datetime: str
    jpg: Path
    meta: dict = field(repr=False)

    @property
    def is360(self):
        return self.meta.get("projection") == "equirectangular"

    @property
    def W(self):
        return int(self.meta["width"])

    @property
    def H(self):
        return int(self.meta["height"])

    @property
    def seq(self):
        return {**SEQ_DEFAUT, **SEQUENCES.get(self.date, {})}


@functools.lru_cache(maxsize=1)
def catalogue():
    """Toutes les photos du dossier data/raw/panoramax/paquet_jardin : {id8: Photo}."""
    out = {}
    for js in sorted(PHOTOS.glob("*_hd.json")):
        m = lire_json(js)
        jpg = js.with_suffix(".jpg")
        if not jpg.exists():
            continue
        p = Photo(m["id"], m["id"][:8], m["datetime"][:10], m["datetime"], jpg, m)
        out[p.id8] = p
    return out


def photo(pid):
    """Photo par identifiant (8 premiers caractères ou uuid complet)."""
    return catalogue()[str(pid)[:8]]


@functools.lru_cache(maxsize=1)
def _wgs_l93():
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)


def gps_local(lon, lat):
    """lon/lat WGS84 -> (x, y) local et gamma = azimut grille du nord vrai (deg)."""
    t = _wgs_l93()
    a = np.array(t.transform(lon, lat))
    b = np.array(t.transform(lon, lat + 1e-4))
    gamma = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))
    xy = repere(a[None], "local")[0]
    return xy, gamma


@functools.lru_cache(maxsize=1)
def mnt():
    return MNT()


def z_sol(x, y):
    """Sol nu 2026 (MNT du paquet) en z local."""
    return float(mnt()(x + O[0], y + O[1])) - O[2]


def intrinseques(ph):
    """Intrinsèques a priori : dict(modele, W, H, f, cx, cy, k1, source)."""
    m = ph.meta
    if ph.is360:
        return dict(modele="equirect", W=ph.W, H=ph.H, f=0.0, cx=0.0, cy=0.0, k1=0.0,
                    source="equirectangulaire 360°")
    if m.get("field_of_view"):
        hfov, src = float(m["field_of_view"]), "field_of_view Panoramax (horizontal)"
    else:
        hfov, src = ph.seq["hfov"], "a priori (focale inconnue), à caler"
    f = (ph.W / 2.0) / math.tan(math.radians(hfov) / 2.0)
    return dict(modele="stenope", W=ph.W, H=ph.H, f=f, cx=ph.W / 2.0, cy=ph.H / 2.0, k1=0.0,
                source=src, hfov=hfov)


def pose_brute(ph):
    """Pose a priori (GNSS + azimut) et écarts types : dict(pose, sigma, gamma, ...)."""
    m = ph.meta
    xy, gamma = gps_local(m["lon"], m["lat"])
    s = ph.seq
    z = z_sol(*xy) + s["h"]
    lacet = (float(m["azimuth"]) + gamma) % 360.0
    tang = float(m.get("pers_pitch") or 0.0)
    roul = float(m.get("pers_roll") or 0.0)
    acc = float(m.get("horizontal_accuracy_m") or 5.0)
    sig_xy = max(acc, 0.5) if ph.is360 else max(acc, 3.0)
    sig = dict(xy=sig_xy, z=s["sh"], lacet=8.0 if ph.is360 else 25.0,
               tangage=2.0 if ph.is360 else 8.0, roulis=2.0 if ph.is360 else 5.0)
    return dict(pose=np.array([xy[0], xy[1], z, lacet, tang, roul]), sigma=sig, gamma=gamma,
                h_a_priori=s["h"])


def camera(ph, pose=None, intr=None):
    """Camera de la photo, à la pose donnée (sinon pose brute)."""
    intr = intr or intrinseques(ph)
    if pose is None:
        pose = pose_brute(ph)["pose"]
    return Camera(intr["modele"], intr["W"], intr["H"], np.asarray(pose, float),
                  f=intr["f"], cx=intr["cx"], cy=intr["cy"], k1=intr.get("k1", 0.0))


# --------------------------------------------------------------------------- images
@functools.lru_cache(maxsize=2)
def image_rgb(pid):
    """Image HD (H, W, 3) uint8."""
    return np.asarray(Image.open(photo(pid).jpg).convert("RGB"))


@functools.lru_cache(maxsize=2)
def image_gris(pid):
    """Image HD en niveaux de gris float32 (0..1)."""
    a = image_rgb(pid).astype(np.float32)
    return (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) / 255.0


def echantillonner(img, u, v, boucle=False):
    """Interpolation bilinéaire de img (H, W[, C]) aux coordonnées pixel continues (u, v).
    `boucle` : raccord horizontal à 360° (équirectangulaire). Hors image -> 0 (ou bord)."""
    H, W = img.shape[:2]
    x = np.nan_to_num(np.asarray(u, dtype=np.float64), nan=-1e6) - 0.5
    y = np.clip(np.nan_to_num(np.asarray(v, dtype=np.float64), nan=-1e6) - 0.5, 0, H - 1.000001)
    if boucle:
        x = np.mod(x, W)
    else:
        x = np.clip(x, 0, W - 1.000001)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    tx, ty = x - x0, y - y0
    x1 = (x0 + 1) % W if boucle else np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    if img.ndim == 3:
        tx, ty = tx[..., None], ty[..., None]
    a = img[y0, x0] * (1 - tx) + img[y0, x1] * tx
    b = img[y1, x0] * (1 - tx) + img[y1, x1] * tx
    return a * (1 - ty) + b * ty


# --------------------------------------------------------------------------- poses calées
def charger_poses(chemin=None):
    """poses.json -> {id8: dict} (vide s'il n'existe pas encore)."""
    chemin = Path(chemin or SORTIE / "poses.json")
    if not chemin.exists():
        return {}
    d = lire_json(chemin)
    return {p["id8"]: p for p in d.get("photos", [])}


def camera_calee(pid, poses=None, accepte_seulement=True):
    """Camera à la pose calée de poses.json si elle existe (et acceptée si demandé), sinon brute.
    Renvoie (camera, statut) avec statut 'calee' | 'calee_refusee' | 'brute'."""
    ph = photo(pid)
    poses = charger_poses() if poses is None else poses
    p = poses.get(ph.id8)
    if p and p.get("pose") and (p.get("accepte") or not accepte_seulement):
        q = p["pose"]
        intr = {**intrinseques(ph), **(p.get("intrinseques") or {})}
        pose = [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]]
        return camera(ph, pose, intr), ("calee" if p.get("accepte") else "calee_refusee")
    return camera(ph), "brute"


__all__ = ["Camera", "Photo", "catalogue", "photo", "camera", "camera_calee", "pose_brute",
           "intrinseques", "image_rgb", "image_gris", "echantillonner", "matrice_rotation",
           "z_sol", "gps_local", "charger_poses", "SORTIE", "CENTRE", "RACINE", "DONNEES",
           "VECTEURS", "O", "repere", "lire_json", "ecrire_json", "arrondi"]
