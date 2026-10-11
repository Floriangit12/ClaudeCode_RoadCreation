"""Composantes connexes du masque des reprises d'enrobé 2022 -> 2024 (enrobes_neufs.py), >= 8 m²."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa
from detection_auto import enveloppe  # noqa: E402  (ré-exécute la détection : rapide)

m = np.load(DONNEES / "enrobes_neufs_masque.npy")
RES = 0.5
x0l, y1l = -150.0, 150.0
# dilatation 1 cellule pour relier les fragments d'une même bande
p = np.pad(m, 1)
md = np.max([p[i:i + m.shape[0], j:j + m.shape[1]] for i in range(3) for j in range(3)], axis=0)
lab = np.zeros(m.shape, int)
comps = []
for j0, i0 in zip(*np.nonzero(md)):
    if lab[j0, i0]:
        continue
    pile = [(j0, i0)]; lab[j0, i0] = len(comps) + 1; cel = []
    while pile:
        j, i = pile.pop(); cel.append((j, i))
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            jj, ii = j + dj, i + di
            if 0 <= jj < m.shape[0] and 0 <= ii < m.shape[1] and md[jj, ii] and not lab[jj, ii]:
                lab[jj, ii] = len(comps) + 1; pile.append((jj, ii))
    comps.append(cel)
out = []
for cel in comps:
    vrai = [(j, i) for j, i in cel if m[j, i]]
    s = len(vrai) * RES * RES
    if s < 8:
        continue
    pts = []
    for j, i in vrai:
        x, y = x0l + i * RES, y1l - j * RES
        pts += [(x, y), (x + RES, y), (x, y - RES), (x + RES, y - RES)]
    env = enveloppe(pts)
    js, is_ = np.array(vrai).T
    out.append({"surface_m2": s, "centre_local": [round(float(x0l + (is_.mean() + .5) * RES), 1), round(float(y1l - (js.mean() + .5) * RES), 1)],
                "enveloppe_local": [[round(a, 2), round(b, 2)] for a, b in env]})
out.sort(key=lambda o: -o["surface_m2"])
for k, o in enumerate(out):
    o["id"] = f"ENR-{k + 1:03d}"
ecrire_json(DONNEES / "enrobes_neufs_composantes.json", {"source": "enrobes_neufs_masque.npy", "n": len(out), "composantes": out})
for o in out[:40]:
    print(o["id"], o["surface_m2"], o["centre_local"])
