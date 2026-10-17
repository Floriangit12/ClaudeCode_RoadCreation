"""Textures procédurales du décor de rendu (lot L2b) : écorce, grappes de feuilles (avec alpha), mortier des joints,
albédo de la peinture routière, brins d'herbe. numpy + PIL, graines fixes : deux exécutions donnent les mêmes octets.

Ces textures ne servent qu'au rendu de contrôle (aucune donnée de la route) : elles donnent aux matériaux qui n'en ont
pas dans la bibliothèque (arbres du décor, mortier, peinture) une carte d'albédo, pour que 100 % des maillages visibles
soient texturés (critère M1). Sortie : <dossier>/<nom>.png ; renvoie {nom: chemin}.
"""
import hashlib
from pathlib import Path

import numpy as np


def _bruit(rng, n, octaves=5, persistance=0.55, periodique=True):
    """Bruit fractal 2D périodique (somme d'octaves de bruit de valeur interpolé), valeurs dans [0, 1]."""
    out = np.zeros((n, n))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        f = 4 * 2 ** o
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


def _srgb8(lin):
    lin = np.clip(lin, 0, 1)
    s = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    return (s * 255 + 0.5).astype(np.uint8)


def ecorce(n=512):
    rng = np.random.default_rng(101)
    b = _bruit(rng, n, 6)
    # fissures verticales : bruit étiré en y
    rng2 = np.random.default_rng(102)
    f = _bruit(rng2, n, 5)
    f = np.repeat(f[::4, :], 4, axis=0)[:n]
    fis = np.clip((f - 0.35) * 3.0, 0, 1)
    base = np.array([0.10, 0.085, 0.07])
    col = base[None, None, :] * (0.55 + 0.6 * b[:, :, None]) * (0.35 + 0.65 * fis[:, :, None])
    return _srgb8(col)


def feuilles(n=512):
    """Grappe de feuilles (RGBA) : 7 à 9 feuilles elliptiques nervurées, teintes variées, fond transparent."""
    rng = np.random.default_rng(7)
    img = np.zeros((n, n, 4))
    yy, xx = np.mgrid[0:n, 0:n] / n
    for k in range(9):
        cx, cy = 0.2 + 0.6 * rng.random(), 0.2 + 0.6 * rng.random()
        ang = rng.random() * np.pi
        L, W = 0.20 + 0.10 * rng.random(), 0.09 + 0.04 * rng.random()
        u = (xx - cx) * np.cos(ang) + (yy - cy) * np.sin(ang)
        v = -(xx - cx) * np.sin(ang) + (yy - cy) * np.cos(ang)
        forme = (u / L) ** 2 + (v / (W * (1 - 0.45 * (u / L)))) ** 2 <= 1.0
        teinte = np.array([0.045, 0.11, 0.025]) * (0.75 + 0.6 * rng.random()) + np.array([0.02, 0.01, 0.0]) * rng.random()
        nerv = np.exp(-(v / 0.006) ** 2) * (np.abs(u) < L)
        ombre = 0.75 + 0.25 * (1 - np.clip(np.abs(v) / W, 0, 1))
        col = teinte[None, None, :] * ombre[:, :, None] * (1 + 0.6 * nerv[:, :, None])
        img[forme, :3] = col[forme]
        img[forme, 3] = 1.0
    rgb = _srgb8(img[:, :, :3])
    a = (img[:, :, 3] * 255).astype(np.uint8)
    return np.dstack([rgb, a])


def mortier(n=256):
    rng = np.random.default_rng(11)
    b = _bruit(rng, n, 5)
    col = np.array([0.20, 0.195, 0.18])[None, None, :] * (0.7 + 0.5 * b[:, :, None])
    return _srgb8(col)


def peinture(n=512):
    """Albédo de la peinture blanche : blanc cassé (0,77, peinture_routiere u0) avec salissure légère et grain."""
    rng = np.random.default_rng(23)
    b = _bruit(rng, n, 6)
    g = rng.random((n, n))
    col = np.array([0.77, 0.77, 0.75])[None, None, :] * (0.90 + 0.10 * b[:, :, None]) * (0.97 + 0.03 * g[:, :, None])
    return _srgb8(col)


def herbe_brin(n=256):
    """Brins d'herbe : dégradé vert du pied (sombre) à la pointe (clair, légèrement jauni), en v."""
    v = np.linspace(0, 1, n)[:, None] * np.ones((1, n))
    rng = np.random.default_rng(31)
    b = _bruit(rng, n, 4)
    pied = np.array([0.025, 0.055, 0.012])
    pointe = np.array([0.09, 0.15, 0.035])
    col = pied[None, None, :] * (1 - v[:, :, None]) + pointe[None, None, :] * v[:, :, None]
    col *= (0.8 + 0.4 * b[:, :, None])
    return _srgb8(col[::-1])


GENERATEURS = {"ecorce": ecorce, "feuilles": feuilles, "mortier": mortier, "peinture_albedo": peinture,
               "herbe_brin": herbe_brin}


def generer(dossier):
    from PIL import Image
    d = Path(dossier)
    d.mkdir(parents=True, exist_ok=True)
    out = {}
    for nom, fn in GENERATEURS.items():
        f = d / f"{nom}.png"
        arr = fn()
        im = Image.fromarray(arr, "RGBA" if arr.shape[-1] == 4 else "RGB")
        tmp = d / f"{nom}.tmp.png"
        im.save(tmp, optimize=False)
        if f.exists() and f.read_bytes() == tmp.read_bytes():
            tmp.unlink()
        else:
            tmp.replace(f)
        out[nom] = f
    return out


def empreintes(chemins):
    return {k: hashlib.sha256(Path(v).read_bytes()).hexdigest() for k, v in chemins.items()}


def macro_variation(src, dst, n=4, amplitude=0.13, graine=5, cote=1024):
    """Texture « macro » sans répétition visible : la tuile de la bibliothèque (src) répétée n × n (raccords d'origine
    gardés : aucune couture) et modulée par un bruit lisse périodique de période n tuiles (luminance ± amplitude,
    légère variation de teinte) ; écrite en JPEG (dst) si elle a changé. Renvoie dst."""
    from PIL import Image
    im = Image.open(src).convert("RGB").resize((cote, cote), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    big = np.tile(lin, (n, n, 1))
    N = big.shape[0]
    rng = np.random.default_rng(graine)
    b1 = _bruit(rng, N // 4, 3, 0.5)
    b2 = _bruit(np.random.default_rng(graine + 1), N // 4, 3, 0.5)
    from PIL import Image as I2
    up = lambda b: np.asarray(I2.fromarray((b * 255).astype(np.uint8)).resize((N, N), I2.BICUBIC), float) / 255.0
    m1, m2 = up(b1), up(b2)
    gain = 1.0 + amplitude * (2 * m1 - 1)
    teinte = np.stack([1.0 + 0.06 * (2 * m2 - 1), np.ones_like(m2), 1.0 - 0.06 * (2 * m2 - 1)], axis=-1)
    out = _srgb8(big * gain[:, :, None] * teinte)
    tmp = Path(dst).with_suffix(".tmp.jpg")
    Image.fromarray(out).save(tmp, quality=92, subsampling=0)
    if Path(dst).exists() and Path(dst).read_bytes() == tmp.read_bytes():
        tmp.unlink()
    else:
        tmp.replace(dst)
    return Path(dst)
