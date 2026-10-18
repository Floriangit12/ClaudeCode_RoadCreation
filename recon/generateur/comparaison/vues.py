"""Caméras et vues de comparaison.

Une « vue » est une image perspective (sténopé, pixels carrés, sans distorsion) tirée d'une photo Panoramax :
- photo 360° équirectangulaire : vue de TAILLE × TAILLE px (≤ 1092) tirée par `decoupe.vue_equirect` (recon/pcg/vision),
  au lacet (relatif au centre de l'image = cap de la photo) et au tangage choisis, champ réglé sur la résolution
  angulaire de la source (règle de decoupe.py equirect : TAILLE / (W / 360°), borné à [40° ; 90°]) ;
- photo plane : l'image entière ramenée à ≤ 1092 px de grand côté (champ horizontal des métadonnées).

Caméra dans le repère du modèle (geo.py) : centre C (x, y, z), lacet (depuis +x, sens trigonométrique), tangage
(positif vers le haut), roulis (positif : côté droit relevé), champ horizontal. Pixel (i, j) centré en (i + 0,5, j + 0,5) :
u = W/2 + f·x, v = H/2 − f·y, (x, y) = (droite, haut) / avant. C'est exactement la géométrie de vue_equirect
(lacet, tangage, roulis nul), donc une vue tirée d'une 360° est décrite sans approximation par la caméra nominale.
"""
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

DEPOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(DEPOT / "recon" / "pcg" / "vision"))
import decoupe  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
TAILLE = decoupe.TAILLE_NATIVE        # 1092

# Porteurs : hauteur de l'objectif (m) par défaut et élévation (°) sous laquelle le porteur occupe l'image
# (valeurs du dossier 13 et de recon/pcg/enrichir/camera.py SEQUENCES : GoPro Max sur voiture 2,1 m, capot sous − 21° ;
# GoPro portée ou sur casque 1,9 m, corps sous − 28 à − 30° ; téléphone derrière le pare-brise 1,3 m).
PORTEURS = {
    "voiture_360": dict(h=2.05, sh=0.35, el_min=-22.0, bas_masque=0.0),
    "velo_360": dict(h=1.90, sh=0.40, el_min=-30.0, bas_masque=0.0),
    "pieton_360": dict(h=1.90, sh=0.40, el_min=-28.0, bas_masque=0.0),
    "inconnu_360": dict(h=1.95, sh=0.45, el_min=-28.0, bas_masque=0.0),
    "voiture_plan": dict(h=1.35, sh=0.35, el_min=-90.0, bas_masque=0.14),
    "velo_plan": dict(h=1.50, sh=0.40, el_min=-90.0, bas_masque=0.0),
    "pieton_plan": dict(h=1.50, sh=0.40, el_min=-90.0, bas_masque=0.0),
    "inconnu_plan": dict(h=1.45, sh=0.45, el_min=-90.0, bas_masque=0.08),
}


def fov_equirect(W):
    return min(90.0, max(40.0, TAILLE / (W / 360.0)))


@dataclass
class Camera:
    W: int
    H: int
    fov: float                      # champ horizontal (°)
    C: np.ndarray                   # (3,)
    lacet: float                    # ° depuis +x, sens trigonométrique
    tangage: float = 0.0
    roulis: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def f(self):
        return (self.W / 2.0) / math.tan(math.radians(self.fov) / 2.0)

    def R(self):
        """Lignes : axes droite, avant, haut de la caméra dans le repère du modèle."""
        ps, th, ph = (math.radians(v) for v in (self.lacet, self.tangage, self.roulis))
        a = np.array([math.cos(th) * math.cos(ps), math.cos(th) * math.sin(ps), math.sin(th)])
        d = np.array([math.sin(ps), -math.cos(ps), 0.0])
        h = np.cross(d, a)
        d2 = d * math.cos(ph) + h * math.sin(ph)
        h2 = -d * math.sin(ph) + h * math.cos(ph)
        return np.vstack([d2, a, h2])

    def projeter(self, P):
        """Points (N, 3) -> pixels continus (N, 2), profondeur (N,), devant (N,)."""
        c = (np.asarray(P, dtype=np.float64) - self.C) @ self.R().T
        av = c[:, 1]
        ok = av > 0.3
        a = np.where(ok, av, 1.0)
        f = self.f
        u = self.W / 2.0 + f * c[:, 0] / a
        v = self.H / 2.0 - f * c[:, 2] / a
        return np.c_[u, v], av, ok

    def rayons(self, uv):
        """Pixels continus (N, 2) -> directions unitaires dans le repère du modèle."""
        uv = np.atleast_2d(uv)
        x = (uv[:, 0] - self.W / 2.0) / self.f
        y = -(uv[:, 1] - self.H / 2.0) / self.f
        c = np.c_[x, np.ones_like(x), y]
        c /= np.linalg.norm(c, axis=1, keepdims=True)
        return c @ self.R()

    def avec(self, ds=0.0, dt=0.0, dlacet=0.0, dtangage=0.0, droulis=0.0, dh=0.0):
        return Camera(self.W, self.H, self.fov, self.C + np.array([ds, dt, dh]), self.lacet + dlacet,
                      self.tangage + dtangage, self.roulis + droulis, self.meta)

    def matrice_usd(self):
        """Matrice 4 × 4 (convention USD, vecteurs lignes) : X = droite, Y = haut, Z = arrière, translation = C."""
        R = self.R()
        m = np.eye(4)
        m[0, :3], m[1, :3], m[2, :3], m[3, :3] = R[0], R[2], -R[1], self.C
        return m

    def usd(self):
        return {"focale_mm": 18.0 / math.tan(math.radians(self.fov) / 2.0), "ouverture_h_mm": 36.0,
                "ouverture_v_mm": 36.0 * self.H / self.W, "resolution": [self.W, self.H],
                "matrice": [[float(v) for v in r] for r in self.matrice_usd()]}

    def dict(self):
        return {"W": self.W, "H": self.H, "champ_h_deg": round(self.fov, 4),
                "C_modele": [round(float(v), 3) for v in self.C], "lacet_deg": round(self.lacet, 3),
                "tangage_deg": round(self.tangage, 3), "roulis_deg": round(self.roulis, 3)}


def masque_porteur(cam, porteur):
    """Masque (H, W) des pixels exploitables : hors porteur (élévation des rayons de la caméra nominale sous el_min,
    bas de l'image pour les photos à plat prises d'un véhicule)."""
    p = PORTEURS[porteur]
    jj, ii = np.mgrid[0:cam.H, 0:cam.W]
    uv = np.c_[ii.ravel() + 0.5, jj.ravel() + 0.5]
    r = cam.rayons(uv)
    el = np.degrees(np.arcsin(np.clip(r[:, 2], -1, 1))).reshape(cam.H, cam.W)
    m = el > p["el_min"]
    if p["bas_masque"] > 0:
        m[int(cam.H * (1 - p["bas_masque"])):, :] = False
    return m


def redresser_mapillary(im, mly):
    """Photo Mapillary perspective ou fisheye -> image sténopé sans distorsion (modèles d'OpenSfM, f normalisée par
    max(W, H), k1, k2) et son champ horizontal (°). Perspective : même focale ; fisheye : champ ramené à 100°."""
    import cv2
    a = np.asarray(im)
    h, w = a.shape[:2]
    cp = list(mly.get("camera_parameters") or [])
    f = float(cp[0]) * max(w, h) if cp else None
    k1, k2 = (float(cp[1]) if len(cp) > 1 else 0.0), (float(cp[2]) if len(cp) > 2 else 0.0)
    if not f:
        return im, None
    K = np.array([[f, 0, w / 2.0], [0, f, h / 2.0], [0, 0, 1.0]])
    if mly.get("camera_type") == "fisheye":
        fn = (w / 2.0) / math.tan(math.radians(50.0))
        Kn = np.array([[fn, 0, w / 2.0], [0, fn, h / 2.0], [0, 0, 1.0]])
        b = cv2.fisheye.undistortImage(a, K, np.array([k1, k2, 0.0, 0.0]), Knew=Kn)
        return Image.fromarray(b), 100.0
    b = cv2.undistort(a, K, np.array([k1, k2, 0.0, 0.0]))
    return Image.fromarray(b), math.degrees(2.0 * math.atan(w / (2.0 * f)))


def extraire_vue(photo_jpg, est360, lacet_image, tangage, fov_plan=None, mly=None):
    """Image de la vue (PIL RGB) et (W, H, champ) : 360° -> vue_equirect native ; plane -> image réduite à ≤ 1092
    (Mapillary perspective ou fisheye : redressée d'abord, `mly` = paramètres de la caméra)."""
    im = Image.open(photo_jpg).convert("RGB")
    if est360:
        W = im.size[0]
        fov = fov_equirect(W)
        vue = decoupe.vue_equirect(np.asarray(im), lacet_image, tangage, fov, TAILLE)
        return vue, (TAILLE, TAILLE, fov)
    if mly and mly.get("camera_type") in ("perspective", "fisheye"):
        im, fov_r = redresser_mapillary(im, mly)
        fov_plan = fov_r or fov_plan
    w, h = im.size
    k = min(1.0, TAILLE / max(w, h))
    W, H = int(round(w * k)), int(round(h * k))
    vue = im.resize((W, H), Image.LANCZOS) if k < 1.0 else im
    return vue, (W, H, float(fov_plan))


# ------------------------------------------------------------------------------------------------ redressement
def _rayons_vue(T, fov, lacet):
    """Fonction pixel (x, y) -> rayon unitaire dans le repère de la photo 360° (droite, avant, haut) pour une vue
    vue_equirect (lacet relatif au centre, tangage 0)."""
    f = (T / 2.0) / math.tan(math.radians(fov) / 2.0)
    L = math.radians(lacet)

    def r(x, y):
        cx = (np.asarray(x) + 0.5 - T / 2.0) / f
        cy = -(np.asarray(y) + 0.5 - T / 2.0) / f
        cz = np.ones_like(cx)
        d = np.stack([cx * math.cos(L) + cz * math.sin(L), -cx * math.sin(L) + cz * math.cos(L), cy], -1)
        return d / np.linalg.norm(d, axis=-1, keepdims=True)
    return r


def verticale_360(img, T=800, fov=90.0, el_min=-25.0, tilt_max=25.0):
    """Verticale vraie d'une photo 360° dans son propre repère (droite, avant, haut), estimée sur les segments
    quasi verticaux (poteaux, façades, troncs droits) de 8 vues de 90° : chaque segment définit un plan contenant la
    verticale ; la verticale est le vecteur le plus orthogonal aux normales de ces plans (moindres carrés pondérés par la
    longueur, 3 passes en écartant les segments à plus de 2° du plan). Renvoie (u, n_segments, résidu °) ou None."""
    import cv2
    a = np.asarray(img.convert("RGB")) if hasattr(img, "convert") else np.asarray(img)
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    N, W = [], []
    for lacet in range(-180, 180, 45):
        v = np.asarray(decoupe.vue_equirect(a, float(lacet), 0.0, fov, T))
        seg = lsd.detect(cv2.cvtColor(v, cv2.COLOR_RGB2GRAY))[0]
        if seg is None:
            continue
        seg = seg.reshape(-1, 4)
        L = np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])
        ang = np.degrees(np.arctan2(np.abs(seg[:, 2] - seg[:, 0]), np.abs(seg[:, 3] - seg[:, 1])))
        ok = (L >= 40) & (ang <= 25)
        if not ok.any():
            continue
        r = _rayons_vue(T, fov, lacet)
        r1, r2 = r(seg[ok, 0], seg[ok, 1]), r(seg[ok, 2], seg[ok, 3])
        el = np.degrees(np.arcsin(np.clip((r1[:, 2] + r2[:, 2]) / 2, -1, 1)))
        n = np.cross(r1, r2)
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        bon = el > el_min
        N.append(n[bon])
        W.append(L[ok][bon])
    if not N:
        return None
    N, W = np.concatenate(N), np.concatenate(W)
    u = np.array([0.0, 0.0, 1.0])
    garde = np.abs(N @ u) < math.sin(math.radians(tilt_max))
    for seuil in (6.0, 3.0, 2.0):
        if garde.sum() < 15:
            return None
        M = (N[garde] * W[garde, None]).T @ N[garde]
        _, vecs = np.linalg.eigh(M)
        u = vecs[:, 0] * (1 if vecs[2, 0] >= 0 else -1)
        garde = np.abs(N @ u) < math.sin(math.radians(seuil))
    if math.degrees(math.acos(min(1.0, u[2]))) > tilt_max:
        return None
    res = float(np.degrees(np.arcsin(np.sqrt(np.average((N[garde] @ u) ** 2, weights=W[garde])))))
    return u, int(garde.sum()), res


def orientation_redressee(lacet_centre, u, lacet_vue, tangage_vue):
    """Lacet, tangage, roulis (repère du modèle) de la vue (lacet_vue relatif au centre, positif à droite ;
    tangage_vue) d'une photo 360° dont la verticale vraie, dans le repère de la photo, est u ; lacet_centre : lacet
    (modèle) du centre de l'image."""
    z = np.array([0.0, 0.0, 1.0])
    ax = np.cross(u, z)
    s, c = np.linalg.norm(ax), float(u @ z)
    if s < 1e-9:
        Q = np.eye(3)
    else:
        k = ax / s
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        Q = np.eye(3) + s * K + (1 - c) * K @ K          # rotation qui amène u sur la verticale
    p0 = math.radians(lacet_centre)
    B = np.column_stack([[math.sin(p0), -math.cos(p0), 0.0], [math.cos(p0), math.sin(p0), 0.0], [0.0, 0.0, 1.0]])
    L, Tg = math.radians(lacet_vue), math.radians(tangage_vue)
    av = np.array([math.cos(Tg) * math.sin(L), math.cos(Tg) * math.cos(L), math.sin(Tg)])
    dr = np.array([math.cos(L), -math.sin(L), 0.0])
    a = B @ Q @ av
    d = B @ Q @ dr
    lacet = math.degrees(math.atan2(a[1], a[0]))
    tangage = math.degrees(math.asin(np.clip(a[2], -1, 1)))
    ps = math.radians(lacet)
    d0 = np.array([math.sin(ps), -math.cos(ps), 0.0])
    h0 = np.cross(d0, a)
    roulis = math.degrees(math.atan2(d @ h0, d @ d0))
    return lacet, tangage, roulis
