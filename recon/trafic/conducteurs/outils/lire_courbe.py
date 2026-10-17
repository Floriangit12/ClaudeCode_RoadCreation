"""Lit une courbe colorée d'un graphique (image) : valeurs aux nœuds équidistants.
python -I lire_courbe.py image.png R G B tol n_classes val_haut [x_premier x_dernier]
- calibre l'axe Y avec les lignes horizontales grises (quadrillage) : la plus basse = 0, la plus haute = val_haut
- repère les pixels de la couleur (R,G,B) à tol près, prend x_min..x_max et n_classes nœuds équidistants."""
import sys, json
import numpy as np
from PIL import Image
f = sys.argv[1]; col = np.array(list(map(int, sys.argv[2:5]))); tol = int(sys.argv[5])
n = int(sys.argv[6]); vhaut = float(sys.argv[7])
a = np.asarray(Image.open(f).convert('RGB')).astype(int)
H, W, _ = a.shape
# quadrillage : lignes ou >40 % des pixels sont gris (r=g=b, 120..235)
g = (np.abs(a[:,:,0]-a[:,:,1]) < 12) & (np.abs(a[:,:,1]-a[:,:,2]) < 12) & (a[:,:,0] > 100) & (a[:,:,0] < 235)
rows = np.where(g.mean(axis=1) > 0.4)[0]
# regroupe les lignes contigues
grp = []
for r in rows:
    if grp and r - grp[-1][-1] <= 2: grp[-1].append(r)
    else: grp.append([r])
ys = [float(np.mean(x)) for x in grp]
y0, ytop = max(ys), min(ys)
m = (np.abs(a - col).sum(axis=2) < tol)
yy, xx = np.nonzero(m)
x_min, x_max = xx.min(), xx.max()
if len(sys.argv) > 9:
    x_min, x_max = float(sys.argv[8]), float(sys.argv[9])
cent = np.linspace(x_min, x_max, n)
vals = []
for c in cent:
    sel = np.abs(xx - c) <= 1.5
    if not sel.any():
        vals.append(None); continue
    y = float(np.median(yy[sel]))
    vals.append(round((y0 - y) / (y0 - ytop) * vhaut, 2))
print(json.dumps({"grilles_y": [round(v,1) for v in ys], "x": [int(x_min), int(x_max)], "valeurs": vals, "somme": round(sum(v for v in vals if v is not None), 2)}))
