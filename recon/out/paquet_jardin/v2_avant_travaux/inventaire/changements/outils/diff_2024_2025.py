"""Différence IGN 2024 (09/08) -> Pléiades 2025 à 0,5 m, hors toits BD TOPO dilatés de 8 m (déversement
Pléiades ~5-6 m) et hors végétation (NDVI IRC 2024 > 0,2) ; blocs de 2 m ; rouge = écart > P95."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa
from pyproj import Transformer

RES = 0.5
b = OR.BBOX
a24 = np.asarray(lire("2024", b, RES, Image.BOX), float)
a25 = np.asarray(lire("2025", b, RES), float)
irc = np.asarray(lire("2024irc", b, RES, Image.BOX), float)
ndvi = (irc[..., 0] - irc[..., 1]) / (irc[..., 0] + irc[..., 1] + 1e-6)
a25n = (a25 - a25.mean((0, 1))) / a25.std((0, 1)) * a24.std((0, 1)) + a24.mean((0, 1))
d = np.sqrt(((a25n - a24) ** 2).sum(-1))
TR = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
mk = Image.new("L", (d.shape[1], d.shape[0]), 0)
dm = ImageDraw.Draw(mk)
for f in lire_json(RACINE / "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson")["features"]:
    g = f["geometry"]
    for p in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
        pts = [((TR.transform(c[0], c[1])[0] - b[0]) / RES, (b[3] - TR.transform(c[0], c[1])[1]) / RES) for c in p[0]]
        dm.polygon(pts, fill=1)
        dm.line(pts + [pts[0]], fill=1, width=int(16 / RES))
toit = np.asarray(mk, bool)
ok = ~toit & (ndvi < 0.2)
k = 4
H, W = d.shape[0] // k * k, d.shape[1] // k * k
bl = np.where(ok, d, np.nan)[:H, :W].reshape(H // k, k, W // k, k)
bm = np.nanmean(bl, axis=(1, 3))
s = np.nanpercentile(bm, 95)
g = Image.fromarray(a25.astype(np.uint8)).convert("L").convert("RGB")
m = np.kron(np.nan_to_num(bm) > s, np.ones((k, k)))
mm = np.zeros(d.shape); mm[:H, :W] = m
im = Image.composite(Image.new("RGB", g.size, (255, 0, 0)), g, Image.fromarray((mm * 140).astype(np.uint8)))
im = im.resize((900, 900), Image.LANCZOS)
v = Vue("2025", b, 900, titre="IGN 2024 -> Pléiades 2025 : rouge = écart > P95 (hors toits dilatés, hors végétation)", im=im)
v.grille(10, 50)
v.im.save(PLANCHES / "carte_auto_2024_2025.png")
print("seuil", s)
