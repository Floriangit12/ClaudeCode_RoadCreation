"""Ciel physique du rendu de contrôle (lot L2b) : modèle analytique de Preetham, Shirley et Smits (« A Practical
Analytic Model for Daylight », SIGGRAPH 1999 : luminance et chromaticité du ciel clair selon la turbidité et la hauteur
du soleil), quelques nuages de beau temps (bruit fractal sur un plan à 1 500 m, graine fixe), sol lointain sombre.
Texture lat-long linéaire (EXR), Y haut (le dôme est tourné de 90° vers Z haut à la pose) ; numpy + OpenImageIO.

Le soleil n'est pas dans la texture : c'est la DistantLight (normalize = 1, ASSETS_ROUTE.md § 3). La texture est mise à
l'échelle pour que l'éclairement horizontal du ciel vaille `part_ciel` × celui du soleil (ciel clair : 0,15 à 0,25).
"""
import math

import numpy as np

XYZ_VERS_RGB = np.array([[3.2404542, -1.5371385, -0.4985314],
                         [-0.9692660, 1.8760108, 0.0415560],
                         [0.0556434, -0.2040259, 1.0572252]])


def _perez(theta, gamma, A, B, C, D, E):
    ct = np.maximum(np.cos(theta), 0.02)
    return (1 + A * np.exp(B / ct)) * (1 + C * np.exp(D * gamma) + E * np.cos(gamma) ** 2)


def preetham(dirs, sun, T):
    """Radiance relative (RGB linéaire) du ciel clair pour les directions dirs (N, 3, Y haut) ; sun : direction du
    soleil (Y haut) ; T : turbidité."""
    ts = math.acos(max(min(sun[1], 1.0), -1.0))
    chi = (4.0 / 9.0 - T / 120.0) * (math.pi - 2 * ts)
    Yz = (4.0453 * T - 4.9710) * math.tan(chi) - 0.2155 * T + 2.4192
    t3, t2 = ts ** 3, ts ** 2
    xz = (T * T * (0.00166 * t3 - 0.00375 * t2 + 0.00209 * ts) + T * (-0.02903 * t3 + 0.06377 * t2 - 0.03202 * ts + 0.00394)
          + (0.11693 * t3 - 0.21196 * t2 + 0.06052 * ts + 0.25886))
    yz = (T * T * (0.00275 * t3 - 0.00610 * t2 + 0.00317 * ts) + T * (-0.04214 * t3 + 0.08970 * t2 - 0.04153 * ts + 0.00516)
          + (0.15346 * t3 - 0.26756 * t2 + 0.06670 * ts + 0.26688))
    cY = (0.1787 * T - 1.4630, -0.3554 * T + 0.4275, -0.0227 * T + 5.3251, 0.1206 * T - 2.5771, -0.0670 * T + 0.3703)
    cx = (-0.0193 * T - 0.2592, -0.0665 * T + 0.0008, -0.0004 * T + 0.2125, -0.0641 * T - 0.8989, -0.0033 * T + 0.0452)
    cy = (-0.0167 * T - 0.2608, -0.0950 * T + 0.0092, -0.0079 * T + 0.2102, -0.0441 * T - 1.6537, -0.0109 * T + 0.0529)
    theta = np.arccos(np.clip(dirs[:, 1], -1, 1))
    gamma = np.arccos(np.clip(dirs @ np.asarray(sun), -1, 1))
    Y = Yz * _perez(theta, gamma, *cY) / _perez(np.zeros(1), np.array([ts]), *cY)
    x = xz * _perez(theta, gamma, *cx) / _perez(np.zeros(1), np.array([ts]), *cx)
    y = yz * _perez(theta, gamma, *cy) / _perez(np.zeros(1), np.array([ts]), *cy)
    X = x * Y / y
    Z = (1 - x - y) * Y / y
    rgb = np.column_stack([X, Y, Z]) @ XYZ_VERS_RGB.T
    return np.maximum(rgb, 0.0)


def _bruit_plan(u, v, graine, octaves=6):
    """Bruit fractal de valeur en (u, v) quelconques (interpolation lisse d'un réseau pseudo-aléatoire haché)."""
    tot = np.zeros_like(u)
    amp, somme = 1.0, 0.0
    for o in range(octaves):
        f = 2.0 ** o
        x, y = u * f, v * f
        xi, yi = np.floor(x), np.floor(y)
        tx, ty = x - xi, y - yi
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)

        def h(a, b):
            n = (a * 374761393 + b * 668265263 + (graine + o * 7919) * 1442695041).astype(np.int64)
            n = (n ^ (n >> 13)) * 1274126177
            return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
        xi, yi = xi.astype(np.int64), yi.astype(np.int64)
        a = h(xi, yi) * (1 - tx) + h(xi + 1, yi) * tx
        b = h(xi, yi + 1) * (1 - tx) + h(xi + 1, yi + 1) * tx
        tot += amp * (a * (1 - ty) + b * ty)
        somme += amp
        amp *= 0.5
    return tot / somme


def ciel_exr(chemin, elevation_deg, azimut_deg, turbidite=2.6, part_ciel=0.20, soleil=1.0, nuages=0.18,
             largeur=2048, graine=1789, sol_radiance=None, voile=0.75, teinte_voile=(0.93, 0.98, 1.06)):
    """Écrit le ciel lat-long ; azimut compté dans le repère de la scène (Z haut, sens trigonométrique depuis +x) ;
    renvoie le résumé (éclairement du ciel, radiance moyenne, part des nuages). nuages = 0 : ciel clair seul (étape 1,
    route seule). sol_radiance (RGB linéaire, unités de la scène) : radiance de l'hémisphère bas après mise à l'échelle
    (fond vu au ras de l'horizon : celle du sol neutre, pour qu'aucune bande ne sépare le sol du ciel) ; sinon sol
    lointain sombre (éclairage)."""
    import OpenImageIO as oiio
    W, H = largeur, largeur // 2
    v = (np.arange(H) + 0.5) / H
    u = (np.arange(W) + 0.5) / W
    el = (0.5 - v) * math.pi                                      # élévation
    EL, U = np.meshgrid(el, u, indexing="ij")
    # convention du DomeLight de Karma XPU 22 (dôme tourné de +90° autour de X, vérifiée par tmp/l2b/essai_dome.py) :
    # la direction de la scène d'azimut phi (depuis +x, sens trigonométrique, Z haut) est vue en u = 0,25 − phi / 2pi
    PHI = 2 * math.pi * (0.25 - U)
    # repère de calcul Y haut : (x, y, z) = (x scène, z scène, y scène)
    dirs = np.column_stack([(np.cos(EL) * np.cos(PHI)).ravel(), np.sin(EL).ravel(), (np.cos(EL) * np.sin(PHI)).ravel()])
    e, a = math.radians(elevation_deg), math.radians(azimut_deg)
    sun_tex = np.array([math.cos(e) * math.cos(a), math.sin(e), math.cos(e) * math.sin(a)])
    rad = preetham(dirs, sun_tex, turbidite)
    haut = dirs[:, 1] > 0
    # voile près de l'horizon : le modèle de Preetham y donne une teinte rosée (rouge > vert) ; un ciel réel est
    # blanchâtre à l'horizon (diffusion par les aérosols) : mélange vers un blanc bleuté de même luminance
    el_dir = np.arcsin(np.clip(dirs[:, 1], -1, 1))
    hz = np.exp(-np.maximum(el_dir, 0.0) / 0.13)[:, None]
    lum0 = (0.2126 * rad[:, 0] + 0.7152 * rad[:, 1] + 0.0722 * rad[:, 2])[:, None]
    rad = rad * (1 - voile * hz) + lum0 * np.array(teinte_voile)[None, :] * 1.05 * voile * hz
    # nuages : plan à 1 500 m, coordonnées en km
    cosz = np.maximum(dirs[:, 1], 0.02)
    pu, pv = dirs[:, 0] / cosz * 1.5, dirs[:, 2] / cosz * 1.5
    n = _bruit_plan(pu * 0.9 + 3.1, pv * 0.9 + 7.7, graine)
    seuil = float(np.percentile(n[haut], 100.0 * (1.0 - nuages))) if nuages > 0 else 2.0
    dens = np.clip((n - seuil) / 0.06, 0, 1) * np.clip((dirs[:, 1] - 0.02) / 0.15, 0, 1)
    lum = rad.mean(axis=1)
    blanc = np.percentile(lum[haut], 90) * 1.6
    cos_sun = np.clip(dirs @ sun_tex, -1, 1)
    eclaire = 0.75 + 0.25 * (0.5 + 0.5 * cos_sun)
    nuage = np.column_stack([blanc * eclaire * 0.98, blanc * eclaire * 0.98, blanc * eclaire])
    rad = rad * (1 - dens[:, None]) + nuage * dens[:, None]
    # sol lointain : sombre, légèrement vert
    sol = np.array([0.08, 0.09, 0.07]) * np.percentile(lum[haut], 50) * 0.35
    rad[~haut] = sol
    # éclairement horizontal du ciel (Z haut scène = Y texture) : somme L cos(theta) dΩ
    dA = (2 * math.pi / W) * (math.pi / H) * np.cos(EL).ravel()
    E = float((rad.mean(axis=1) * np.maximum(dirs[:, 1], 0) * dA).sum())
    E_sun_h = soleil * math.sin(e)
    k = part_ciel * E_sun_h / max(E, 1e-9)
    rad = rad * k
    if sol_radiance is not None:
        rad[~haut] = np.asarray(sol_radiance, dtype=np.float64)[None, :]
    img = rad.reshape(H, W, 3).astype(np.float32)
    spec = oiio.ImageSpec(W, H, 3, oiio.FLOAT)
    spec.attribute("compression", "zip")
    o = oiio.ImageOutput.create(str(chemin))
    o.open(str(chemin), spec)
    o.write_image(img)
    o.close()
    return {"modele": "Preetham 1999 (ciel clair)" + (" + nuages fractals (plan à 1 500 m)" if nuages > 0 else ", sans nuage"),
            "turbidite": turbidite, "hemisphere_bas": "sol neutre" if sol_radiance is not None else "sol lointain sombre",
            "elevation_soleil_deg": elevation_deg, "azimut_soleil_deg": azimut_deg, "part_ciel": part_ciel,
            "nuages_couverture": round(float((dens[haut] > 0.5).mean()), 4),
            "radiance_moyenne_ciel": round(float(rad[haut].mean()), 5), "resolution": [W, H]}
