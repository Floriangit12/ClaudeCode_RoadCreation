"""Textures des sols, de la BEV, des grilles, des arbres et de la peinture usée du rendu de contrôle (correction après
contrôle du lot L2b) ; numpy + PIL, graines fixes : deux exécutions donnent les mêmes octets.

Ces textures ne servent qu'au rendu de contrôle (aucune donnée de la route ni de cote) : elles règlent l'ASPECT des
matériaux nommés par le modèle (materiau_id), à partir des textures CC0 de la bibliothèque (assets/lib), en ramenant
leur albédo moyen et leur teinte aux valeurs mesurées sur les photos de Meylan et dans la littérature (rapport
RAPPORT_correction.md § 3) :
  - détail recoloré : motif de luminance de la tuile de la bibliothèque (Y / moyenne), albédo cible × teinte cible ;
  - cartes « macro » (facteur multiplicatif linéaire, codé ×0,5 en PNG brut) : reprises et fissures pontées de
    l'enrobé ancien, plaques d'herbe sèche ou drue ; étendue 64 m, combinées au rendu à un bruit fractal 3D en
    coordonnées du monde (MaterialX, Karma XPU) : aucune répétition visible ;
  - dalles podotactiles jointées (BEV), grille de caniveau, écorce fissurée, grappes de feuilles, peinture salie.
"""
import hashlib
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DEPOT = Path(__file__).resolve().parents[3]
LIB_ROUTE = DEPOT / "assets" / "lib" / "route_fr" / "materiaux"
LIB_SITE = DEPOT / "assets" / "lib" / "materiaux"


def _lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def _srgb8(lin):
    lin = np.clip(lin, 0, 1)
    s = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    return (s * 255 + 0.5).astype(np.uint8)


def _ecrire(arr, dst, jpeg=False):
    """Écrit si le contenu a changé (octets identiques d'une exécution à l'autre : PIL déterministe)."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    mode = "RGBA" if arr.ndim == 3 and arr.shape[-1] == 4 else ("L" if arr.ndim == 2 else "RGB")
    tmp = dst.with_name(dst.stem + ".tmp" + dst.suffix)
    im = Image.fromarray(arr, mode)
    if jpeg:
        im.save(tmp, quality=93, subsampling=0, optimize=False)
    else:
        im.save(tmp, optimize=False)
    if dst.exists() and dst.read_bytes() == tmp.read_bytes():
        tmp.unlink()
    else:
        tmp.replace(dst)
    return dst


def _bruit(rng, n, octaves=5, persistance=0.55, base=4):
    """Bruit fractal 2D périodique dans [0, 1]."""
    out = np.zeros((n, n))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        f = base * 2 ** o
        g = rng.random((f, f))
        x = np.linspace(0, f, n, endpoint=False)
        i0 = np.floor(x).astype(int) % f
        i1 = (i0 + 1) % f
        t = x - np.floor(x)
        t = t * t * (3 - 2 * t)
        a = g[i0][:, i0] * (1 - t)[None, :] + g[i0][:, i1] * t[None, :]
        b = g[i1][:, i0] * (1 - t)[None, :] + g[i1][:, i1] * t[None, :]
        out += amp * (a * (1 - t)[:, None] + b * t[:, None])
        tot += amp
        amp *= persistance
    out /= tot
    return (out - out.min()) / max(out.max() - out.min(), 1e-9)


def _bruit_spectral(rng, n, lmin, lmax, beta=1.0):
    """Bruit 2D périodique isotrope (bruit blanc filtré dans le domaine fréquentiel : longueurs d'onde de lmin à lmax
    pixels, spectre d'amplitude en 1/f^beta), centré réduit ; pas d'alignement sur une grille (contrairement au bruit
    de valeurs interpolé de _bruit)."""
    w = rng.standard_normal((n, n))
    fx = np.fft.fftfreq(n)
    f = np.sqrt(fx[None, :] ** 2 + fx[:, None] ** 2)
    filtre = np.where((f >= 1.0 / lmax) & (f <= 1.0 / lmin), 1.0 / np.maximum(f, 1e-9) ** beta, 0.0)
    z = np.real(np.fft.ifft2(np.fft.fft2(w) * filtre))
    return (z - z.mean()) / z.std()


# ------------------------------------------------------------------------------------------- détail recoloré
def detail_recolore(src, dst, cible_lin, cote=2048, contraste=1.0, chroma=0.0):
    """Tuile de la bibliothèque (src, sRGB) -> même motif, albédo moyen et teinte cibles (cible_lin : RGB linéaire
    moyen visé). contraste : exposant du motif de luminance (1 : motif d'origine) ; chroma : part de la variation de
    teinte d'origine gardée (0 : teinte unie). Renvoie (dst, statistiques)."""
    im = Image.open(src).convert("RGB")
    if im.size[0] != cote:
        im = im.resize((cote, cote), Image.LANCZOS)
    a = _lin(np.asarray(im, dtype=np.float64) / 255.0)
    Y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    m = float(Y.mean())
    yn = np.power(np.maximum(Y / m, 1e-4), contraste)
    yn /= yn.mean()
    c = np.asarray(cible_lin, dtype=np.float64)
    out = yn[..., None] * c[None, None, :]
    if chroma > 0:
        ch = a / np.maximum(Y[..., None], 1e-4)              # chromaticité d'origine (rapport à la luminance)
        ch /= ch.reshape(-1, 3).mean(0)[None, None, :]
        out *= (1 - chroma) + chroma * ch
    _ecrire(_srgb8(out), dst, jpeg=True)
    Yo = 0.2126 * out[..., 0] + 0.7152 * out[..., 1] + 0.0722 * out[..., 2]
    return Path(dst), {"albedo_moyen_lin": [round(float(x), 4) for x in out.reshape(-1, 3).mean(0)],
                       "Y_moyen": round(float(Yo.mean()), 4), "sigmaY_rel": round(float(Yo.std() / Yo.mean()), 4)}


# ------------------------------------------------------------------------------------------- cartes macro
def _encoder_facteur(f):
    """Facteur multiplicatif linéaire -> PNG brut 8 bits (f × 0,5 ; 1,0 ↔ 128) ; le rendu multiplie par 2."""
    return np.clip(f * 0.5 * 255 + 0.5, 0, 255).astype(np.uint8)


def macro_enrobe(dst, etendue_m=64.0, cote=2048, graine=41, reprises=14, fissures=70, sobre=False):
    """Carte macro de l'enrobé ancien (facteur RGB) : nuances lentes (± 5 %), reprises (rapiéçages et tranchées
    rectangulaires plus sombres, joint de bord), fissures pontées au bitume (lignes sombres de 2 à 4 cm), taches.
    sobre (étape 1, route seule : « usure légère, reprises plausibles ») : reprises rectangulaires alignées sur les
    axes (les routes du catalogue suivent x) et à peine plus sombres (0,90-0,95, joint 0,80), tranchées transversales
    étroites (0,6-1,0 m), fissures pontées rares, fines et peu contrastées (0,72-0,82)."""
    rng = np.random.default_rng(graine)
    px = cote / etendue_m                                       # pixels par mètre (32 : 3,1 cm/px)
    f = 1.0 + (0.06 if sobre else 0.10) * (_bruit(rng, cote, 5, 0.5) - 0.5)   # nuances lentes ± 3 % (± 5 %)
    im = Image.fromarray(np.full((cote, cote), 128, np.uint8), "L")
    d = ImageDraw.Draw(im)
    for k in range(reprises):                                   # reprises : plus sombres (enrobé plus récent)
        if sobre and k % 3 == 2:                                # tranchée transversale (réseau) : 0,6-1,0 × 3-6 m
            w, h = rng.uniform(0.6, 1.0) * px, rng.uniform(3.0, 6.0) * px
        else:
            w, h = rng.uniform(1.2, 3.5) * px, rng.uniform(2.0, 9.0) * px
            if rng.random() < 0.5:
                w, h = h, w
        x, y = rng.uniform(0, cote - w), rng.uniform(0, cote - h)
        v = int(128 * (rng.uniform(0.90, 0.95) if sobre else rng.uniform(0.78, 0.90)))
        d.rectangle([x, y, x + w, y + h], fill=v, outline=int(128 * (0.80 if sobre else 0.62)),
                    width=max(1, int(0.03 * px)))
    for _ in range(fissures):                                   # fissures pontées : marches aléatoires
        x, y = rng.uniform(0, cote), rng.uniform(0, cote)
        ang = rng.uniform(0, 2 * math.pi)
        pts = [(x, y)]
        for _k in range(int(rng.uniform(6, 30))):
            ang += rng.normal(0, 0.45)
            pas = rng.uniform(0.15, 0.45) * px
            x, y = x + pas * math.cos(ang), y + pas * math.sin(ang)
            pts.append((x, y))
        if sobre:
            d.line(pts, fill=int(128 * rng.uniform(0.72, 0.82)), width=max(1, int(rng.uniform(0.015, 0.03) * px)))
        else:
            d.line(pts, fill=int(128 * rng.uniform(0.45, 0.62)), width=max(1, int(rng.uniform(0.02, 0.045) * px)))
    for _ in range(25):                                         # taches (huile, poussière) très douces
        r = rng.uniform(0.3, 1.2) * px
        x, y = rng.uniform(0, cote), rng.uniform(0, cote)
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=int(128 * rng.uniform(0.88, 0.96)))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    g = np.asarray(im, dtype=np.float64) / 128.0
    fac = f * g
    rgb = np.stack([fac * 1.0, fac * 1.0, fac * 1.0], axis=-1)
    _ecrire(_encoder_facteur(rgb), dst)
    return Path(dst), {"etendue_m": etendue_m, "facteur_moyen": round(float(fac.mean()), 4),
                       "reprises": reprises, "fissures": fissures}


def macro_herbe(dst, etendue_m=64.0, cote=2048, graine=43):
    """Carte macro de l'herbe (facteur RGB) : plaques d'herbe sèche (plus claires, jaunies), drue (plus sombre),
    petites zones de terre ; variations lentes de luminance (σ ≥ 0,10 visé sur le rendu, photos I10, I11 : 0,11-0,16)."""
    rng = np.random.default_rng(graine)
    b1 = _bruit(rng, cote, 5, 0.55, base=3)
    b2 = _bruit(np.random.default_rng(graine + 1), cote, 5, 0.6, base=6)
    b3 = _bruit(np.random.default_rng(graine + 2), cote, 4, 0.5, base=16)
    sec = np.clip((b1 - 0.55) * 4.0, 0, 1)                      # herbe sèche
    dru = np.clip((0.40 - b1) * 4.0, 0, 1)                      # herbe drue, plus sombre
    terre = np.clip((b2 - 0.82) * 8.0, 0, 1) * np.clip((b3 - 0.4) * 3, 0, 1)
    # variations lentes renforcées (correction après contrôle : σY de l'herbe 0,02-0,03 en vue de dessus contre
    # 0,11-0,16 sur les photos) : ± 30 % sur 4-10 m, plaques sèches plus claires, drues plus sombres
    lum = 1.0 + 0.60 * (b3 - 0.5) + 0.40 * (b2 - 0.5)
    R = lum * (1 + 0.70 * sec - 0.30 * dru + 0.6 * terre)
    G = lum * (1 + 0.40 * sec - 0.25 * dru - 0.1 * terre)
    B = lum * (1 - 0.05 * sec - 0.25 * dru + 0.3 * terre)
    rgb = np.stack([R, G, B], axis=-1)
    Y = 0.2126 * R + 0.7152 * G + 0.0722 * B
    rgb /= float(Y.mean())
    _ecrire(_encoder_facteur(rgb), dst)
    Y = Y / float(Y.mean())
    return Path(dst), {"etendue_m": etendue_m, "sigmaY_facteur": round(float(Y.std()), 4)}


def meso_herbe(dst, genre="touffes", cote=2048, graine=47, sigma_log=None):
    """Carte méso de l'herbe (facteur RGB de moyenne 1) ; deux genres, lus à des périodes incommensurables dans le
    matériau (MESO de rendu_l2b : touffes 4,7 m, plaques 11,3 m ; leur produit ne se répète pas) :
    - « touffes » : touffes et creux d'ombre entre les brins (7-30 cm), σ du logarithme 0,40 ;
    - « plaques » : plaques claires et sombres de 0,2 à 1,2 m (herbe drue, trèfle plus sombre et plus bleu, brins secs
      clairs et jaunis), σ du logarithme 0,44.
    Correction après contrôle : herbe 4 fois trop uniforme en vue de dessus (σY 0,02-0,03 contre 0,11-0,16 sur les
    photos I10, I11, M24). PNG brut : facteur × 0,25 (le matériau multiplie par 4 : facteurs jusqu'à 4 sans écrêtage)."""
    rng = np.random.default_rng(graine)
    if genre == "touffes":                                     # tuile de 4,7 m : 2,3 mm par pixel
        sigma_log = 0.40 if sigma_log is None else sigma_log
        z = _bruit_spectral(rng, cote, 30, 130, 0.8)           # touffes et creux, 7 à 30 cm
        trefle = sec = np.zeros_like(z)
    else:                                                      # tuile de 11,3 m : 5,5 mm par pixel
        sigma_log = 0.44 if sigma_log is None else sigma_log
        z = _bruit_spectral(rng, cote, 36, 220, 1.0)           # plaques de 0,2 à 1,2 m
        c = _bruit_spectral(np.random.default_rng(graine + 2), cote, 50, 200, 1.0)   # trèfle (0,3-1,1 m)
        s_ = _bruit_spectral(np.random.default_rng(graine + 3), cote, 60, 300, 1.0)  # brins secs (0,3-1,6 m)
        trefle = np.clip((c - 1.0) * 1.5, 0, 1)
        sec = np.clip((s_ - 1.0) * 1.5, 0, 1)
        z = z - 0.6 * trefle + 0.5 * sec
    z = (z - z.mean()) / z.std()
    L = np.exp(sigma_log * z)
    R = L * (1 - 0.12 * trefle + 0.22 * sec)
    G = L * (1 - 0.02 * trefle + 0.10 * sec)
    B = L * (1 + 0.08 * trefle - 0.10 * sec)
    rgb = np.stack([R, G, B], axis=-1)
    Y = 0.2126 * R + 0.7152 * G + 0.0722 * B
    rgb /= float(Y.mean())
    _ecrire(np.clip(rgb * 0.25 * 255 + 0.5, 0, 255).astype(np.uint8), dst)
    Y = Y / float(Y.mean())
    return Path(dst), {"genre": genre, "sigmaY_facteur": round(float(Y.std()), 4), "sigma_log": sigma_log,
                       "part_ecretee": round(float((rgb > 3.99).mean()), 5)}


# ------------------------------------------------------------------------------------------- BEV, grille
def bev_dalles(dst, cote=512, base=(0.40, 0.40, 0.38), joint_c=(0.10, 0.10, 0.095)):
    """BEV en dalles podotactiles jointées : une dalle de 0,40 m le long de la bordure (u) sur toute la profondeur de
    la BEV (v, 0 au nez, 1 au fond) ; joints de 4 mm, plots en quinconce (5 × 7). base : albédo linéaire de la dalle
    (correction après le second contrôle : teinte choisie en contraste avec le revêtement voisin, RF-MA-OBS-003 —
    anthracite sur un trottoir clair, gris clair sur un enrobé) ; joint_c : albédo du joint."""
    rng = np.random.default_rng(51)
    H, W = cote, int(cote * 0.40 / 0.5875 + 0.5)               # texture au rapport d'une dalle 0,40 × 0,5875
    b = _bruit(rng, cote, 5, 0.55)[:H, :W]
    base = np.array(base, dtype=np.float64)
    img = base[None, None, :] * (0.92 + 0.12 * b[..., None])
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = xx / W, yy / H
    for i in range(5):
        for j in range(7):
            cu = (i + 0.5 + (0.5 if j % 2 else 0.0)) / 5.0
            if cu > 1.0:
                continue
            cv = (j + 0.5) / 7.0
            d2 = ((u - cu) * 0.40) ** 2 + ((v - cv) * 0.5875) ** 2
            plot = d2 < 0.0125 ** 2
            img[plot] = img[plot] * 1.08 + 0.02
            ombre = (d2 >= 0.0125 ** 2) & (d2 < 0.0155 ** 2) & ((v - cv) > 0)
            img[ombre] *= 0.80
    jt = 0.004 / 0.40 * W
    joint = (xx < jt) | (xx >= W - jt) | (yy < 0.004 / 0.5875 * H) | (yy >= H - 0.004 / 0.5875 * H)
    img[joint] = list(joint_c)
    _ecrire(_srgb8(img), dst)
    return Path(dst), {"dalle_m": [0.40, 0.5875], "plots": [5, 7], "joint_mm": 4, "albedo_lin": [round(float(x), 4) for x in base]}


def grille(dst, cote=512):
    """Grille en fonte (caniveau à grille, avaloir) : barreaux de 25 mm, fentes de 15 mm (≤ 2 cm, A2007 pour les
    cheminements), cadre ; tuile de 0,50 m."""
    rng = np.random.default_rng(53)
    b = _bruit(rng, cote, 5, 0.6)
    fonte = np.array([0.055, 0.052, 0.050]) * (0.8 + 0.5 * b[..., None])
    fond = np.array([0.012, 0.011, 0.010])
    yy, xx = np.mgrid[0:cote, 0:cote]
    pas = cote / 20.0                                          # 20 barreaux sur 0,50 m : 25 mm
    fente = ((xx % pas) / pas > 0.62) & (yy % (cote / 2) > cote * 0.04) & (yy % (cote / 2) < cote * 0.46)
    img = np.where(fente[..., None], fond[None, None, :], fonte)
    _ecrire(_srgb8(img), dst)
    return Path(dst), {"tuile_m": 0.5, "fente_mm": 15}


# ------------------------------------------------------------------------------------------- arbres
def ecorce(dst, cote=512):
    """Écorce fissurée (crêtes verticales gris-brun, fissures sombres, lichens clairs), tuile 0,5 m ; sans
    « taches de camouflage » (relecture adverse)."""
    rng = np.random.default_rng(61)
    yy, xx = np.mgrid[0:cote, 0:cote] / cote
    warp = _bruit(rng, cote, 4, 0.5, base=3)
    crete = 0.5 + 0.5 * np.sin(2 * math.pi * (xx * 14 + 0.9 * warp))
    fis = np.clip((0.22 - crete) * 6, 0, 1)
    fin = _bruit(np.random.default_rng(62), cote, 6, 0.6, base=8)
    lichen = np.clip((_bruit(np.random.default_rng(63), cote, 4, 0.5, base=5) - 0.72) * 5, 0, 1)
    base = np.array([0.105, 0.092, 0.078])
    col = base[None, None, :] * (0.75 + 0.45 * crete[..., None]) * (0.85 + 0.3 * fin[..., None])
    col = col * (1 - 0.75 * fis[..., None]) + lichen[..., None] * np.array([0.10, 0.11, 0.09]) * 0.6
    _ecrire(_srgb8(col), dst)
    return Path(dst)


def feuilles(dst, couleur_srgb="#4C7A30", cote=256, graine=7):
    """Grappe de feuilles (RGBA) d'une carte de 0,08-0,15 m : un rameau et 6 à 8 feuilles elliptiques nervurées de
    teinte voisine de la couleur d'été de l'essence (assets/specs/vegetation.json), fond transparent."""
    rng = np.random.default_rng(graine)
    h = couleur_srgb.lstrip("#")
    c0 = _lin(np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0)
    img = np.zeros((cote, cote, 4))
    yy, xx = np.mgrid[0:cote, 0:cote] / cote
    # rameau
    tige = (np.abs(xx - 0.5 - 0.06 * (yy - 0.5)) < 0.012) & (yy > 0.1) & (yy < 0.95)
    img[tige, :3] = np.array([0.06, 0.045, 0.03])
    img[tige, 3] = 1.0
    for k in range(int(rng.integers(6, 9))):
        t = 0.15 + 0.75 * rng.random()
        cx, cy = 0.5 + 0.06 * (t - 0.5), t
        cote_f = 1 if k % 2 else -1
        ang = cote_f * rng.uniform(0.5, 1.1) + math.pi / 2
        L, Wd = rng.uniform(0.17, 0.24), rng.uniform(0.08, 0.11)
        ox, oy = cx + math.cos(ang) * L * 0.9, cy - math.sin(ang) * L * 0.4
        u = (xx - ox) * math.cos(ang) + (yy - oy) * math.sin(ang)
        v = -(xx - ox) * math.sin(ang) + (yy - oy) * math.cos(ang)
        forme = (u / L) ** 2 + (v / (Wd * (1 - 0.4 * (u / L)))) ** 2 <= 1.0
        teinte = c0 * rng.uniform(0.75, 1.25) * np.array([rng.uniform(0.9, 1.1), 1.0, rng.uniform(0.85, 1.1)])
        nerv = np.exp(-(v / 0.006) ** 2) * (np.abs(u) < L)
        ombre = 0.78 + 0.22 * (1 - np.clip(np.abs(v) / Wd, 0, 1))
        col = teinte[None, None, :] * ombre[..., None] * (1 + 0.5 * nerv[..., None])
        img[forme, :3] = col[forme]
        img[forme, 3] = 1.0
    rgb = _srgb8(img[..., :3])
    a = (img[..., 3] * 255).astype(np.uint8)
    _ecrire(np.dstack([rgb, a]), dst)
    return Path(dst)


# ------------------------------------------------------------------------------------------- peinture
def peinture_usee(dst, cote=1024, blanc=0.66, graine=23):
    """Albédo de la peinture blanche usée et salie : blanc 0,66 (peinture neuve 0,77, peinture_routiere u0) assombri
    par la salissure (marbrures ± 10 %), granulats de l'enrobé affleurants (points sombres, 6 %), traînées dans le
    sens de circulation (axe u). Calibré sur les photos M24 et M27 (rapport § 3 : écart peinture − enrobé)."""
    rng = np.random.default_rng(graine)
    b = _bruit(rng, cote, 6, 0.6)
    g = rng.random((cote, cote))
    tr = _bruit(np.random.default_rng(graine + 1), cote, 5, 0.5, base=8)
    tr = np.repeat(tr[::8, :], 8, axis=0)[:cote]               # traînées étirées
    v = blanc * (0.88 + 0.12 * b) * (0.94 + 0.06 * tr)
    v = np.where(g < 0.06, v * 0.35, v)
    col = np.stack([v, v, v * 0.97], axis=-1)
    _ecrire(_srgb8(col), dst)
    return Path(dst)


def empreintes(chemins):
    return {k: hashlib.sha256(Path(v).read_bytes()).hexdigest() for k, v in sorted(chemins.items())}


def montagne(dst, cote=1024, graine=71):
    """Fond de relief (décor) : u = azimut (tuile répétée), v = altitude relative (0 au pied, 1 vers 1 900 m) ; forêt
    sombre jusqu'à la limite des arbres (≈ 60 %, irrégulière), roche et pelouses au-dessus, sans stries ; perspective
    aérienne : couleurs mêlées à 35 % au bleu-gris de l'horizon (relief à 7 km)."""
    rng = np.random.default_rng(graine)
    b = _bruit(rng, cote, 6, 0.55, base=3)
    b2 = _bruit(np.random.default_rng(graine + 1), cote, 5, 0.5, base=4)
    v = np.linspace(1, 0, cote)[:, None] * np.ones((1, cote))      # ligne 0 = haut de l'image = v 1
    foret = np.array([0.018, 0.032, 0.016])
    roche = np.array([0.095, 0.094, 0.090])
    pelouse = np.array([0.060, 0.070, 0.045])
    limite = 0.60 + 0.20 * (b2 - 0.5)
    m = np.clip((v - limite) * 6, 0, 1)[..., None]
    haut = roche * (0.85 + 0.3 * b[..., None]) * (1 - 0.3 * b2[..., None]) + pelouse * 0.3 * b2[..., None]
    col = foret * (0.8 + 0.4 * b[..., None]) * (1 - m) + haut * m
    voile = np.array([0.20, 0.25, 0.33])                      # bleu-gris de l'horizon (perspective aérienne)
    col = col * 0.65 + voile * 0.35
    _ecrire(_srgb8(col), dst)
    return Path(dst)


COUVERTURE_USURE = {"0": 0.99, "1": 0.95, "2": 0.88, "3": 0.80, "F": 0.55}
BLANC_USURE = {"0": 0.72, "1": 0.66, "2": 0.58, "3": 0.52, "F": 0.48}


def masque_usure(dst, classe="1", cote=1024, graine=29):
    """Masque d'opacité de la peinture usée (tuile 4 m, st1 au 1/4) : granulats de l'enrobé affleurants (points de
    2 à 8 mm) et plages d'usure lentes (bandes de roulement), jusqu'à la couverture de la classe (u0 99 % … uF 55 %).
    Remplace au rendu les masques à cellules polygonales de la bibliothèque (taches de « camouflage » dans les bandes
    de passage de S_M24, relecture adverse : « usure légère » trop propre ou mal répartie)."""
    rng = np.random.default_rng(graine + ord(classe[0]))
    cible = COUVERTURE_USURE.get(classe, 0.95)
    lent = _bruit(rng, cote, 5, 0.55, base=4)
    fin = rng.random((cote, cote))
    im = Image.fromarray((fin * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    fin = np.asarray(im, dtype=np.float64) / 255.0
    # usure : petits points, un peu plus denses dans les plages usées (étape 1 : poids des plages 0,25 au lieu de
    # 0,35 : plus de « taches » sombres dans les bandes de passage en vue de dessus, usure légère et diffuse)
    score = 0.75 * fin + 0.25 * lent
    seuil = np.quantile(score, 1.0 - cible)
    m = (score >= seuil).astype(np.uint8) * 255
    _ecrire(m, dst)
    return Path(dst), {"classe": classe, "couverture": round(float((m > 0).mean()), 4)}


# ------------------------------------------------------------------------------------------- étape 1 : route seule
def sol_neutre(dst, albedo=(0.50, 0.485, 0.445), cote=256, graine=81):
    """Sol neutre autour de la route (étape 1, décision de l'utilisateur : rien en dehors de l'emprise de la route) :
    gris-beige clair, mat, uni (bruit de ± 1 % seulement, pour que le maillage reste « texturé » au sens du critère M1),
    tuile de 4 m. Ce n'est pas un matériau du modèle : c'est le fond de présentation (socle et sol plat)."""
    rng = np.random.default_rng(graine)
    b = _bruit(rng, cote, 4, 0.5, base=4)
    a = np.asarray(albedo, dtype=np.float64)[None, None, :] * (0.99 + 0.02 * b[..., None])
    _ecrire(_srgb8(a), dst)
    return Path(dst), {"albedo_lin": list(albedo), "variation": "± 1 %"}


def joints_beton(dst, pas_m=2.0, joint_mm=8.0, cote=1024, graine=83):
    """Joints sciés d'un trottoir en béton balayé (facteur RGB, PNG brut × 0,25 comme les cartes méso : le matériau
    multiplie par 4) : un trait transversal sombre (facteur 0,45, largeur joint_mm) par tuile de pas_m, légèrement
    irrégulier (épaufrures) ; tuile carrée pas_m × pas_m lue en coordonnées de la route (x le long de l'axe)."""
    rng = np.random.default_rng(graine)
    f = np.ones((cote, cote))
    w = max(1, int(round(joint_mm / 1000.0 / pas_m * cote)))
    bord = _bruit(rng, cote, 4, 0.5, base=8)[:, 0]               # épaufrures le long du joint
    for y in range(cote):
        e = w + int(bord[y] * 2.0)
        f[y, :e] = 0.45
        f[y, e:e + 2] = 0.80
    rgb = np.stack([f, f, f * 0.99], axis=-1)
    _ecrire(np.clip(rgb * 0.25 * 255 + 0.5, 0, 255).astype(np.uint8), dst)
    return Path(dst), {"pas_m": pas_m, "joint_mm": joint_mm}
