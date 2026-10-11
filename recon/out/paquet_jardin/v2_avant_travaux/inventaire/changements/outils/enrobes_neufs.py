"""Reprises d'enrobé 2022 -> 2024 : surfaces de chaussée nettement plus sombres en 2024 (enrobé neuf,
tranchées refermées) qu'en 2022, hors ombres et végétation. Cellules de 0,5 m ; gris 2024 normalisé
sur 2022 par la médiane et l'écart interquartile des chaussées (pixels peu saturés, gris 70..200).
Sortie : planches/enrobes_neufs_2022_2024.png + donnees/enrobes_neufs_2022_2024.json (composantes)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa

RES = 0.5
b = boite_locale(-150, -150, 150, 150)
a22 = np.asarray(lire("2022", b, RES, Image.BOX), float)
a24 = np.asarray(lire("2024", b, RES, Image.BOX), float)
irc = np.asarray(lire("2024irc", b, RES, Image.BOX), float)
g22, g24 = a22.mean(2), a24.mean(2)
sat22, sat24 = a22.max(2) - a22.min(2), a24.max(2) - a24.min(2)
ndvi = (irc[..., 0] - irc[..., 1]) / (irc[..., 0] + irc[..., 1] + 1e-6)
route = (sat22 < 25) & (sat24 < 25) & (g22 > 70) & (g22 < 210) & (ndvi < 0.1)
q22 = np.percentile(g22[route], [25, 50, 75]); q24 = np.percentile(g24[route], [25, 50, 75])
g24n = (g24 - q24[1]) / (q24[2] - q24[0]) * (q22[2] - q22[0]) + q22[1]
d = g22 - g24n
neuf = route & (d > 28) & (g24 > 60)
# nettoyage : au moins 3 voisins sur 8
p = np.pad(neuf, 1)
vois = sum(p[1 + i:1 + i + neuf.shape[0], 1 + j:1 + j + neuf.shape[1]] for i in (-1, 0, 1) for j in (-1, 0, 1)) - neuf
neuf = neuf & (vois >= 3)
im = Image.fromarray((a24 * 0.55).astype(np.uint8))
arr = np.asarray(im).copy()
arr[neuf] = (255, 120, 0)
im = Image.fromarray(arr).resize((900, 900), Image.NEAREST)
v = Vue("2024", b, 900, titre="enrobés plus sombres en 2024 qu'en 2022 (orange) — reprises / tranchées", im=im)
v.grille(10, 50)
v.im.save(PLANCHES / "enrobes_neufs_2022_2024.png")
ecrire_json(DONNEES / "enrobes_neufs_2022_2024.json", {"methode": __doc__, "res_m": RES,
            "surface_m2": float(neuf.sum() * RES * RES), "quartiles_chaussee_2022": q22.tolist(), "quartiles_chaussee_2024": q24.tolist()})
np.save(DONNEES / "enrobes_neufs_masque.npy", neuf)
print("surface", neuf.sum() * RES * RES)
