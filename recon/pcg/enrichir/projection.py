"""Projection, rayons, découpes perspective et rendu de l'ortho 2022 dans la vue d'une photo.

Fonctions publiques :
- projeter(points_local, photo_id) -> dict(uv, visible, devant, distance, occulte)
- rayon(photo_id, pixel) -> (origine (3,), direction unitaire (3,)) dans le repère local
- decoupe_perspective(photo_id, lacet, tangage, fov, taille) -> (image PIL, Camera virtuelle)
- rendu_ortho(cam, uv) : sol vu par la caméra (ortho PCRS 2022 5 cm drapée sur le MNT 2026)
- occulte_par_batiments(C, P) : occultation approchée par les emprises bâties (prismes)

La pose utilisée est celle de poses.json (calée) si elle existe, sinon la pose brute GNSS.
"""
import functools
import math

import numpy as np
from PIL import Image

from camera import (DONNEES, VECTEURS, Camera, camera_calee, echantillonner, image_rgb,
                    lire_json, matrice_rotation, mnt, O, photo)

ORTHO = VECTEURS / "ortho5cm_2022"
ORTHO_PAS = 0.05


# --------------------------------------------------------------------------- bâtiments
@functools.lru_cache(maxsize=1)
def batiments():
    """Emprises bâties locales : liste de (anneau (N, 2), z_haut local)."""
    out = []
    for f in lire_json(DONNEES / "objets/batiments_local.geojson")["features"]:
        p, g = f["properties"], f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        zs = (p.get("z_sol_local") or 0.0) + (p.get("hauteur_egout_m") or 3.0)
        for poly in polys:
            r = np.asarray(poly[0], dtype=np.float64)[:, :2]
            out.append((r, zs))
    return out


def occulte_par_batiments(C, P):
    """Vrai si le segment C -> P (3D) traverse une emprise bâtie sous son égout (approché)."""
    C = np.asarray(C, dtype=np.float64)
    P = np.atleast_2d(np.asarray(P, dtype=np.float64))
    occ = np.zeros(len(P), dtype=bool)
    for r, zh in batiments():
        A, B = r, np.roll(r, -1, axis=0)
        bmin, bmax = r.min(0), r.max(0)
        lo = np.minimum(P[:, :2], C[:2])
        hi = np.maximum(P[:, :2], C[:2])
        cand = np.all(hi >= bmin, axis=1) & np.all(lo <= bmax, axis=1) & ~occ
        if not cand.any():
            continue
        for k in np.nonzero(cand)[0]:
            q = P[k]
            d = q[:2] - C[:2]
            e = B - A
            den = d[0] * e[:, 1] - d[1] * e[:, 0]
            ok = np.abs(den) > 1e-12
            w = A - C[:2]
            t = np.where(ok, (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / np.where(ok, den, 1), -1)
            s = np.where(ok, (w[:, 0] * d[1] - w[:, 1] * d[0]) / np.where(ok, den, 1), -1)
            hit = ok & (t > 0.02) & (t < 0.98) & (s >= 0) & (s <= 1)
            if hit.any():
                z_ray = C[2] + t[hit] * (q[2] - C[2])
                if np.any(z_ray < zh):
                    occ[k] = True
    return occ


# --------------------------------------------------------------------------- API
def projeter(points_local, photo_id, cam=None, occlusion=True, dmax=None):
    """Projette des points locaux (N, 3) dans la photo.

    Renvoie dict : uv (N, 2) pixels HD, devant (dans le champ), distance (m), occulte (bâtiments),
    visible = devant & non occulté (& distance ≤ dmax), pose ('calee' | 'brute')."""
    P = np.atleast_2d(np.asarray(points_local, dtype=np.float64))
    statut = "fournie"
    if cam is None:
        cam, statut = camera_calee(photo_id)
    uv, devant, dist = cam.projeter(P)
    occ = occulte_par_batiments(cam.C, P) if occlusion else np.zeros(len(P), bool)
    vis = devant & ~occ
    if dmax is not None:
        vis &= dist <= dmax
    return dict(uv=uv, devant=devant, distance=dist, occulte=occ, visible=vis, pose=statut)


def rayon(photo_id, pixel, cam=None):
    """Rayon 3D (origine, direction unitaire) du pixel (u, v) de la photo, repère local."""
    if cam is None:
        cam, _ = camera_calee(photo_id)
    d = cam.rayons(np.asarray(pixel, dtype=np.float64)[None])[0]
    return cam.C.copy(), d


def camera_virtuelle(cam, lacet, tangage, fov, taille, roulis=0.0):
    """Caméra sténopé virtuelle de même centre que `cam` (fov horizontal en deg, taille (w, h))."""
    w, h = (taille, taille) if np.isscalar(taille) else taille
    f = (w / 2.0) / math.tan(math.radians(fov) / 2.0)
    return Camera("stenope", int(w), int(h), np.r_[cam.C, lacet, tangage, roulis], f=f,
                  cx=w / 2.0, cy=h / 2.0)


def reechantillonner(cam_src, img, cam_dst):
    """Image de la vue cam_dst (même centre) rééchantillonnée depuis img prise par cam_src."""
    w, h = cam_dst.W, cam_dst.H
    jj, ii = np.mgrid[0:h, 0:w]
    uv = np.c_[ii.ravel() + 0.5, jj.ravel() + 0.5]
    d = cam_dst.rayons(uv)
    c = d @ cam_src.R.T
    uvs, ok = cam_src.cam_vers_pixel(c)
    val = echantillonner(img, uvs[:, 0], uvs[:, 1], boucle=cam_src.modele == "equirect")
    if img.ndim == 3:
        val = val * ok[:, None]
        return val.reshape(h, w, img.shape[2])
    return (val * ok).reshape(h, w)


def decoupe_perspective(photo_id, lacet, tangage, fov, taille, cam=None, roulis=0.0):
    """Découpe perspective (gnomonique) de la photo : axe (lacet grille, tangage) en degrés,
    fov horizontal (deg), taille en pixels (entier ou (w, h)). Renvoie (PIL.Image, Camera virtuelle).
    Les points 3D se projettent dans la découpe avec `cam_virtuelle.projeter(P)`."""
    if cam is None:
        cam, _ = camera_calee(photo_id)
    cv = camera_virtuelle(cam, lacet, tangage, fov, taille, roulis)
    img = reechantillonner(cam, image_rgb(photo_id).astype(np.float32), cv)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), cv


def fenetre_azel(cam, img, az0, az1, el0, el1, pas):
    """Rééchantillonne la photo sur une grille (élévation, azimut) du repère LOCAL (pas en deg).
    Colonnes = azimut croissant de az0 à az1, lignes = élévation décroissante de el1 à el0 :
    une verticale du monde y est une colonne exactement (quelle que soit l'assiette de la caméra).
    Renvoie (valeurs (nl, nc[, 3]), az (nc,), el (nl,), masque valide (nl, nc))."""
    az = np.arange(az0, az1 + 1e-9, pas)
    el = np.arange(el1, el0 - 1e-9, -pas)
    A, E = np.meshgrid(np.radians(az), np.radians(el))
    d = np.stack([np.cos(E) * np.sin(A), np.cos(E) * np.cos(A), np.sin(E)], -1).reshape(-1, 3)
    c = d @ cam.R.T
    uv, ok = cam.cam_vers_pixel(c)
    val = echantillonner(img, uv[:, 0], uv[:, 1], boucle=cam.modele == "equirect")
    sh = (len(el), len(az))
    if img.ndim == 3:
        return val.reshape(sh + (img.shape[2],)), az, el, ok.reshape(sh)
    return val.reshape(sh), az, el, ok.reshape(sh)


def azel_vers_pixel(cam, az, el):
    """Directions (azimut, élévation) locales en degrés -> pixels de la photo (N, 2), validité."""
    A, E = np.radians(np.atleast_1d(az)), np.radians(np.atleast_1d(el))
    d = np.stack([np.cos(E) * np.sin(A), np.cos(E) * np.cos(A), np.sin(E)], -1)
    return cam.cam_vers_pixel(d @ cam.R.T)


def visee(cam, P):
    """Lacet et tangage (deg, repère local) de la direction C -> P."""
    d = np.asarray(P, dtype=np.float64) - cam.C
    return (math.degrees(math.atan2(d[0], d[1])) % 360.0,
            math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))))


# --------------------------------------------------------------------------- ortho 2022
@functools.lru_cache(maxsize=1)
def ortho_mosaique():
    """Mosaïque niveaux de gris (float32 0..1) des dalles PCRS 5 cm 2022 et son géoréférencement.
    Renvoie (img, x0_local, y1_local) : pixel (i, j) centré en (x0 + (i+0,5)·pas, y1 − (j+0,5)·pas)."""
    tuiles = sorted(ORTHO.glob("pcrs5cm_*.jpg"))
    xs = sorted({int(t.stem.split("_")[1]) for t in tuiles})
    ys = sorted({int(t.stem.split("_")[2]) for t in tuiles})
    n = int(round(50 / ORTHO_PAS))
    img = np.zeros((n * len(ys), n * len(xs)), dtype=np.float32)
    for t in tuiles:
        x, y = int(t.stem.split("_")[1]), int(t.stem.split("_")[2])
        a = np.asarray(Image.open(t).convert("L"), dtype=np.float32) / 255.0
        ci = xs.index(x)
        rj = len(ys) - 1 - ys.index(y)
        img[rj * n:(rj + 1) * n, ci * n:(ci + 1) * n] = a[:n, :n]
    x0 = xs[0] - O[0]
    y1 = ys[-1] + 50 - O[1]
    return img, x0, y1


def ortho_valeur(x, y):
    """Niveau de gris de l'ortho 2022 aux points locaux (bilinéaire) ; NaN hors emprise."""
    img, x0, y1 = ortho_mosaique()
    u = (np.asarray(x) - x0) / ORTHO_PAS
    v = (y1 - np.asarray(y)) / ORTHO_PAS
    H, W = img.shape
    ok = (u >= 0.5) & (u < W - 0.5) & (v >= 0.5) & (v < H - 0.5)
    val = echantillonner(img, u, v)
    return np.where(ok, val, np.nan)


def intersection_sol(C, d, n_iter=3):
    """Intersection des rayons C + t·d (d (N, 3)) avec le MNT 2026 ; t (N,) (NaN si vers le haut)."""
    C = np.asarray(C, dtype=np.float64)
    m = mnt()
    z0 = float(m(C[0] + O[0], C[1] + O[1])) - O[2]
    dz = np.where(d[:, 2] < -1e-3, d[:, 2], np.nan)
    t = (z0 - C[2]) / dz
    for _ in range(n_iter):
        X = C + t[:, None] * d
        zg = m(np.nan_to_num(X[:, 0]) + O[0], np.nan_to_num(X[:, 1]) + O[1]) - O[2]
        t = (zg - C[2]) / dz
    t[(t <= 0) | (t > 200)] = np.nan
    return t


def rendu_ortho(cam, uv):
    """Ortho 2022 vue depuis cam aux pixels uv (N, 2) : (valeur (N,), points sol (N, 3))."""
    d = cam.rayons(uv)
    t = intersection_sol(cam.C, d)
    X = cam.C + t[:, None] * d
    val = ortho_valeur(X[:, 0], X[:, 1])
    val[~np.isfinite(t)] = np.nan
    return val, X


__all__ = ["projeter", "rayon", "decoupe_perspective", "camera_virtuelle", "reechantillonner",
           "visee", "fenetre_azel", "azel_vers_pixel", "ortho_mosaique", "ortho_valeur", "rendu_ortho", "intersection_sol",
           "occulte_par_batiments", "batiments", "matrice_rotation"]
