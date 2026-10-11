"""Détection automatique des changements PCRS 2022 (10/05) -> IGN 2024 (09/08), recalés au cm près.

Méthode (numpy seul) :
- les deux images sont lues à 0,25 m (filtre boîte) sur l'emprise du site, cadre PCRS ;
- normalisation radiométrique par canal (moyenne / écart type) de 2024 sur 2022 ;
- par cellule de 1 m : écart de couleur moyen (norme RVB des moyennes) et écart de texture
  (écart type des niveaux de gris) ;
- masques : végétation (indice vert 2022 > 0,06 ou NDVI IRC 2024 > 0,2 — les houppiers changent
  de forme et d'ombre sans que la scène change), ombres (gris < 55 à une seule date : soleil différent),
  toits BD TOPO (déversement en visée oblique) ;
- cellule « changée » : écart couleur > seuil_c ou écart texture > seuil_t ; fermeture morphologique
  3 x 3 ; composantes connexes de surface >= 12 m² ; contour = enveloppe convexe (L93).
Sorties : donnees/detection_auto_2022_2024.json (composantes), planches/carte_auto_2022_2024.png.
Ce n'est qu'un détecteur de candidats : chaque changement retenu dans changements_2022_2025.geojson
a été revu à l'œil sur les planches et les photos.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa

from pyproj import Transformer

RES = 0.25
CELL = 4                       # 4 x 0,25 m = 1 m
b = OR.BBOX
a22 = np.asarray(lire("2022", b, RES, Image.BOX), float)
a24 = np.asarray(lire("2024", b, RES, Image.BOX), float)
irc = np.asarray(lire("2024irc", b, RES, Image.BOX), float)
H, W = a22.shape[:2]
a24n = (a24 - a24.mean((0, 1))) / a24.std((0, 1)) * a22.std((0, 1)) + a22.mean((0, 1))
g22, g24 = a22.mean(2), a24n.mean(2)


def blocs(a, f=np.mean):
    h, w = a.shape[0] // CELL * CELL, a.shape[1] // CELL * CELL
    r = a[:h, :w].reshape(h // CELL, CELL, w // CELL, CELL, *a.shape[2:])
    return f(r, axis=(1, 3))


m22, m24 = blocs(a22), blocs(a24n)
dc = np.sqrt(((m22 - m24) ** 2).sum(-1))
dt = np.abs(blocs(g22, np.std) - blocs(g24, np.std))
vert22 = (a22[..., 1] - a22[..., 0]) / (a22[..., 1] + a22[..., 0] + 1e-6)
ndvi24 = (irc[..., 0] - irc[..., 1]) / (irc[..., 0] + irc[..., 1] + 1e-6)
veg = blocs(((vert22 > 0.06) | (ndvi24 > 0.2)).astype(float)) > 0.5
omb = blocs((((g22 < 55) ^ (g24 < 55))).astype(float)) > 0.5

# toits BD TOPO (emprises actuelles, y compris immeubles neufs) : exclus de la détection fine,
# traités à part comme « bâtiment construit » quand l'emprise est postérieure à 2022.
TR = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
toit = np.zeros(dc.shape, bool)
from PIL import ImageDraw as _D
mk = Image.new("L", (dc.shape[1], dc.shape[0]), 0)
dm = _D.Draw(mk)
for f in lire_json(RACINE / "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson")["features"]:
    g = f["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for p in polys:
        pts = [TR.transform(c[0], c[1]) for c in p[0]]
        dm.polygon([((x - b[0]) / (RES * CELL), (b[3] - y) / (RES * CELL)) for x, y in pts], fill=1)
toit = np.asarray(mk, bool)

seuil_c = float(np.percentile(dc[~veg & ~toit], 90))
seuil_t = float(np.percentile(dt[~veg & ~toit], 92))
chg = ((dc > seuil_c) | (dt > seuil_t)) & ~veg & ~omb & ~toit


def dilate(m):
    p = np.pad(m, 1)
    return np.max([p[i:i + m.shape[0], j:j + m.shape[1]] for i in range(3) for j in range(3)], axis=0)


def erode(m):
    p = np.pad(m, 1, constant_values=True)
    return np.min([p[i:i + m.shape[0], j:j + m.shape[1]] for i in range(3) for j in range(3)], axis=0)


chg_f = erode(dilate(chg))

# composantes connexes (4-connexité), BFS
lab = np.zeros(chg_f.shape, int)
n = 0
comps = []
for j0, i0 in zip(*np.nonzero(chg_f)):
    if lab[j0, i0]:
        continue
    n += 1
    pile = [(j0, i0)]
    lab[j0, i0] = n
    cel = []
    while pile:
        j, i = pile.pop()
        cel.append((j, i))
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            jj, ii = j + dj, i + di
            if 0 <= jj < lab.shape[0] and 0 <= ii < lab.shape[1] and chg_f[jj, ii] and not lab[jj, ii]:
                lab[jj, ii] = n
                pile.append((jj, ii))
    comps.append(cel)


def enveloppe(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cr(o, a, b_):
        return (a[0] - o[0]) * (b_[1] - o[1]) - (a[1] - o[1]) * (b_[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


c_m = RES * CELL
out = []
for k, cel in enumerate(comps):
    if len(cel) < 12:
        continue
    coins = []
    for j, i in cel:
        x0, y1 = b[0] + i * c_m, b[3] - j * c_m
        coins += [(x0, y1), (x0 + c_m, y1), (x0, y1 - c_m), (x0 + c_m, y1 - c_m)]
    env = enveloppe(coins)
    js, is_ = np.array(cel).T
    out.append({"id": f"AUTO-{len(out) + 1:03d}", "surface_m2": len(cel) * c_m * c_m,
                "centre_local": [round(float(b[0] + (is_.mean() + 0.5) * c_m - O[0]), 1), round(float(b[3] - (js.mean() + 0.5) * c_m - O[1]), 1)],
                "ecart_couleur_moyen": round(float(dc[js, is_].mean()), 1), "ecart_texture_moyen": round(float(dt[js, is_].mean()), 1),
                "enveloppe_l93": [[round(x, 2), round(y, 2)] for x, y in env]})
out.sort(key=lambda o: -o["surface_m2"])
ecrire_json(DONNEES / "detection_auto_2022_2024.json", {
    "methode": __doc__, "res_lecture_m": RES, "cellule_m": c_m, "seuil_couleur": round(seuil_c, 1), "seuil_texture": round(seuil_t, 1),
    "part_cellules_changees_hors_masques": round(float(chg_f[~veg & ~toit].mean()), 3),
    "part_vegetation": round(float(veg.mean()), 3), "part_toits": round(float(toit.mean()), 3),
    "n_composantes": len(out), "composantes": out})
# carte
g = Image.fromarray(a24.astype(np.uint8)).convert("L").convert("RGB")
big = lambda m: Image.fromarray((np.kron(m, np.ones((CELL, CELL))) * 255).astype(np.uint8)).resize(g.size, Image.NEAREST)
rouge = Image.new("RGB", g.size, (255, 0, 0))
bleu = Image.new("RGB", g.size, (60, 120, 255))
im = Image.composite(bleu, g, big(toit).point(lambda v: 70 if v else 0))
im = Image.composite(rouge, im, big(chg_f).point(lambda v: 150 if v else 0))
im = im.resize((900, 900), Image.LANCZOS)
v = Vue("2024", b, 900, titre="auto 2022->2024 : rouge changé (hors végétation/ombres), bleu toits BD TOPO", im=im)
v.grille(10, 50)
for o in out[:40]:
    v.poly([(x - O[0], y - O[1]) for x, y in o["enveloppe_l93"]], (255, 255, 0, 200), 1, etiquette=o["id"][5:] if o["surface_m2"] > 40 else None)
v.im.save(PLANCHES / "carte_auto_2022_2024.png")
print(len(out), "composantes ; seuils", round(seuil_c, 1), round(seuil_t, 1))
for o in out[:40]:
    print(o["id"], o["surface_m2"], o["centre_local"], o["ecart_couleur_moyen"], o["ecart_texture_moyen"])
