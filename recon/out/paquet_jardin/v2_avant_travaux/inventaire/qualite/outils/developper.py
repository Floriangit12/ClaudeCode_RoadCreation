import sys, math
from pathlib import Path
import numpy as np
import OpenImageIO as oiio
S = Path("C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q")
SOLEIL = {"hauteur_deg": 29.0, "exposition": 2.0, "couleur": (1.0, 0.95, 0.88)}
EV, EPAULE = 0.2, 0.6
def courbe(x):
    k = 1.0 - EPAULE
    return np.where(x <= EPAULE, x, EPAULE + k * (1.0 - np.exp(-(x - EPAULE) / k)))
def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
def gains_balance():
    zen, hor = np.array((0.30, 0.42, 0.70)), np.array((0.80, 0.86, 0.95))
    l, h = 256, 128
    el = (0.5 - (np.arange(h) + 0.5) / h) * np.pi
    t = np.clip(np.sin(np.maximum(el, 0.0)), 0, 1) ** 0.45
    ligne = np.where(el[:, None] >= 0, hor * (1 - t[:, None]) + zen * t[:, None], hor * 0.5)
    dw = (np.pi / h) * (2 * np.pi / l) * np.cos(el)
    E = float(np.sum((ligne.mean(axis=1) * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0]))
    E_s = 2.0 ** SOLEIL["exposition"] * math.sin(math.radians(SOLEIL["hauteur_deg"]))
    k = E_s / 3.5 / E
    Ec = np.array([float(np.sum((ligne[:, c] * np.sin(np.maximum(el, 0.0)) * dw * l)[el > 0])) for c in range(3)]) * k
    g = np.array((1.0, 1.0, 0.94)) / (np.array(SOLEIL["couleur"]) * E_s + Ec)
    return g / g[1]
g = gains_balance()
for exr in sorted(S.glob("rendu_*.exr")):
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * (2.0 ** EV) * g.astype(np.float32)
    y = (srgb(courbe(np.maximum(a, 0.0))) * 255 + 0.5).astype(np.uint8)
    b = oiio.ImageBuf(oiio.ImageSpec(y.shape[1], y.shape[0], 3, oiio.UINT8)); b.set_pixels(oiio.ROI(), y)
    b.write(str(exr.with_suffix(".png")))
    print(exr.name, y.mean())
