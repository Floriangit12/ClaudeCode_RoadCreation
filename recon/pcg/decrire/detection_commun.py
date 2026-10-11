"""Détection image des marquages : rasters, prétraitement et corrélation (outils communs des détecteurs
detection_fleches / detection_zebras / detection_lignes).

Rasters (repère local, échantillonnage bilinéaire aux points Q (N, 2)) :
- ortho PCRS 5 cm 2022 (marquages_ortho.luminance) : marques blanches sur enrobé ;
- plan projet 2025 (data/sites/paquet_jardin/plan_projet_2025, 4,09 cm/px, affine pixel -> L93 de georef.json,
  RMSE 3 cm, DET-REG-001 : déjà calé) : glyphes CAO noirs (zébras, flèches, tirets) ou orange (pavés Chronovélo)
  sur la photo de fond ; canal « noir » = 255 − L, mis au fond là où la saturation dépasse 0,35 (calques colorés,
  DET-PRE-002) ; canal « orange » = R − B des pixels saturés orangés ; hors du raster (noir pur de
  la mosaïque, voisinage sans gris) : NaN.
Prétraitement (DET-PRE-002) : top-hat blanc (ouverture par un carré plus large que la plus large marque :
1,55 m pour TD_TAD de 1,275 m), seuil de vraisemblance 25 DN.
Corrélation : NCC par FFT d'un gabarit polygonal rastérisé (sur-échantillonné x4, couverture 0-1) avec marge de
contexte de 0,30 m (DET-FLE-003), maximum sur de petites rotations, carte ré-indexée à l'ORIGINE du gabarit.
Tout est déterministe (aucun aléa, FFT numpy).
"""
import functools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_ortho as MO  # noqa: E402
from commun import O, VECTEURS  # noqa: E402

PLAN = VECTEURS / "plan_projet_2025"
PX = 0.05                      # pas des bandes rectifiées (m), DET-FLE-003
SS = 4                         # sur-échantillonnage des gabarits
SEUIL_TOPHAT = 25.0            # DET-PRE-002 (DN)
SE_TOPHAT_M = 1.55             # DET-PRE-002 : > 1,275 m (TD_TAD)


# --------------------------------------------------------------------------- rasters
def ortho(Q):
    """Luminance ortho 2022 (0-255) aux points locaux Q ; NaN hors dalles."""
    return MO.luminance(Q)


@functools.lru_cache(maxsize=None)
def _plan():
    from PIL import Image, ImageFilter
    idx = json.loads((PLAN / "tuiles/index.json").read_text(encoding="utf-8"))
    W = max(t["px_box"][2] for t in idx)
    H = max(t["px_box"][3] for t in idx)
    rgb = np.zeros((H, W, 3), np.uint8)
    for t in sorted(idx, key=lambda t: t["file"]):
        im = np.asarray(Image.open(PLAN / "tuiles" / t["file"]).convert("RGB"))
        x0, y0 = t["px_box"][0], t["px_box"][1]
        rgb[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im
    g = json.loads((PLAN / "georef.json").read_text(encoding="utf-8"))
    A = np.vstack([np.array(g["affine_pixel_centre_vers_L93"]), [0, 0, 1]])
    f = rgb.astype(np.float32)
    L = f.mean(axis=2)
    mx, mn = f.max(axis=2), f.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    # validité : voisinage (≈ 1,6 m) contenant du gris de photo (le noir pur de la mosaïque est hors raster)
    gris = Image.fromarray(((L > 50) * 255).astype(np.uint8))
    for _ in range(4):
        gris = gris.filter(ImageFilter.MaxFilter(9))
    valide = np.asarray(gris) > 0
    noir = 255.0 - L
    fond = float(np.median(noir[valide]))
    noir = np.where(sat > 0.35, fond, noir)                     # calques colorés masqués (DET-PRE-002)
    orange = np.where((sat > 0.45) & (f[..., 0] > 150) & (f[..., 0] > f[..., 2] + 60) & (f[..., 1] > 60),
                      f[..., 0] - f[..., 2], 0.0)
    cad = (sat > 0.6) & (mx > 120)
    return {"noir": noir.astype(np.float32), "orange": orange.astype(np.float32), "valide": valide,
            "cad": cad, "Ai": np.linalg.inv(A), "W": W, "H": H, "georef": g}


def _plan_ech(canal, Q):
    p = _plan()
    Q = np.atleast_2d(np.asarray(Q, float))
    X, Y = Q[:, 0] + O[0], Q[:, 1] + O[1]
    Ai = p["Ai"]
    c = Ai[0, 0] * X + Ai[0, 1] * Y + Ai[0, 2]
    r = Ai[1, 0] * X + Ai[1, 1] * Y + Ai[1, 2]
    out = np.full(len(Q), np.nan)
    ok = (c >= 0) & (r >= 0) & (c < p["W"] - 1) & (r < p["H"] - 1)
    c0, r0 = np.floor(c[ok]).astype(int), np.floor(r[ok]).astype(int)
    a, b = c[ok] - c0, r[ok] - r0
    M = p[canal]
    if canal in ("valide", "cad"):
        out[ok] = M[np.round(r[ok]).astype(int), np.round(c[ok]).astype(int)]
        return out
    v = (M[r0, c0] * (1 - a) + M[r0, c0 + 1] * a) * (1 - b) + (M[r0 + 1, c0] * (1 - a) + M[r0 + 1, c0 + 1] * a) * b
    vv = p["valide"][r0, c0] & p["valide"][r0 + 1, c0 + 1]
    out[np.where(ok)[0][vv]] = v[vv]
    return out


def plan_noir(Q):
    """Plan 2025, canal des glyphes CAO noirs (255 − L, calques colorés masqués) ; NaN hors raster."""
    return _plan_ech("noir", Q)


def plan_orange(Q):
    """Plan 2025, canal des aplats orange (pavés Chronovélo) R − B (0-255) ; NaN hors raster."""
    return _plan_ech("orange", Q)


def plan_cad(Q):
    """Pixels de calques CAO colorés (saturation > 0,6) : 1/0 ; NaN hors raster."""
    return _plan_ech("cad", Q)


RASTERS = {"ortho2022": ortho, "plan2025": plan_noir, "plan2025_orange": plan_orange}


def grille(x0, y0, x1, y1, res):
    """Centres de pixels d'une fenêtre (lignes du nord au sud) : (Q (H*W, 2), H, W)."""
    W, H = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    xs = x0 + (np.arange(W) + 0.5) * res
    ys = y1 - (np.arange(H) + 0.5) * res
    X, Y = np.meshgrid(xs, ys)
    return np.c_[X.ravel(), Y.ravel()], H, W


def image(source, Q, H, W):
    """Image (H, W) d'une source aux points Q, NaN remplacés par la médiane (fond)."""
    v = RASTERS[source](Q).reshape(H, W)
    if np.isnan(v).all():
        return None, np.zeros((H, W), bool)
    ok = ~np.isnan(v)
    return np.where(ok, v, np.nanmedian(v)).astype(np.float32), ok


# --------------------------------------------------------------------------- prétraitement
def _filtre_rep(im, filt, k):
    steps, rem = divmod(k - 1, 8)
    for _ in range(steps):
        im = im.filter(filt(9))
    if rem:
        im = im.filter(filt(rem + 1 if (rem + 1) % 2 else rem + 2))
    return im


def tophat(img, se_m=SE_TOPHAT_M, px=PX):
    """Top-hat blanc (img − ouverture par un carré de se_m), DET-PRE-002 ; img float 0-255."""
    from PIL import Image, ImageFilter
    k = int(round(se_m / px)) | 1
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    op = _filtre_rep(_filtre_rep(pil, ImageFilter.MinFilter, k), ImageFilter.MaxFilter, k)
    return np.asarray(pil, np.float32) - np.asarray(op, np.float32)


# --------------------------------------------------------------------------- gabarits et NCC
def gabarit_raster(polys, rot_deg=0.0, marge=0.30, px=PX, echelle=1.0):
    """Gabarit (anneaux [[ext, trous...], ...] en coordonnées gabarit x, y) -> image de couverture 0-1 (lignes = y
    croissant, colonnes = x croissant) et position (ligne, colonne) fractionnaire de l'origine."""
    from PIL import Image, ImageDraw
    a = math.radians(rot_deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    rs = [[(np.asarray(r, float) * echelle) @ R.T for r in poly] for poly in polys]
    P = np.vstack([r for poly in rs for r in poly])
    cols, rows = P[:, 0] / px, P[:, 1] / px
    m = marge / px
    cmin, rmin = cols.min() - m, rows.min() - m
    w = int(math.ceil(cols.max() + m - cmin))
    h = int(math.ceil(rows.max() + m - rmin))
    cv = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(cv)
    for poly in rs:
        for k, r in enumerate(poly):
            d.polygon([((x / px - cmin) * SS, (y / px - rmin) * SS) for x, y in r], fill=255 if k == 0 else 0)
    return np.asarray(cv.resize((w, h), Image.BOX), np.float32) / 255.0, (-rmin - 0.5, -cmin - 0.5)


def ncc(img, tpl):
    """NCC « valide » de tpl sur img (FFT) : carte (H − h + 1, W − w + 1) ou None."""
    H, W = img.shape
    h, w = tpl.shape
    if h >= H or w >= W:
        return None
    t = tpl - tpl.mean()
    tn = math.sqrt(float((t * t).sum()))
    if tn < 1e-9:
        return None
    sh = (H + h, W + w)
    corr = np.fft.irfft2(np.fft.rfft2(img, sh) * np.fft.rfft2(t[::-1, ::-1], sh), sh)[h - 1:H, w - 1:W]
    ii = np.pad(img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ii2 = np.pad(img * img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)

    def bs(a):
        return a[h:, w:] - a[:-h, w:] - a[h:, :-w] + a[:-h, :-w]
    s1, s2 = bs(ii), bs(ii2)
    return corr / (tn * np.sqrt(np.maximum(s2 - s1 * s1 / (h * w), 1e-6)))


def carte_origine(img, polys, rots=(-4, -2, 0, 2, 4), echelle=1.0, px=PX):
    """Maximum de la NCC sur les rotations, ré-indexé à la position de l'ORIGINE du gabarit :
    (carte (H, W) -1 hors domaine, rotation retenue (H, W))."""
    H, W = img.shape
    out = np.full((H, W), -1.0, np.float32)
    arg = np.zeros((H, W), np.float32)
    for rd in rots:
        tpl, (ro, co) = gabarit_raster(polys, rd, echelle=echelle, px=px)
        Mp = ncc(img, tpl)
        if Mp is None:
            continue
        r0, c0 = int(round(ro)), int(round(co))
        if r0 < 0 or c0 < 0:
            continue
        sub = out[r0:r0 + Mp.shape[0], c0:c0 + Mp.shape[1]]
        hh, ww = sub.shape
        upd = Mp[:hh, :ww] > sub
        sub[upd] = Mp[:hh, :ww][upd]
        arg[r0:r0 + hh, c0:c0 + ww][upd] = rd
    return out, arg


def couverture_masque(polys, Q):
    """Masque booléen des points Q dans les polygones (gabarit posé) — rasterisation exacte au point."""
    from commun import dans_polygones
    return dans_polygones(Q, polys)


def clip01(v):
    return float(min(1.0, max(0.0, v)))
