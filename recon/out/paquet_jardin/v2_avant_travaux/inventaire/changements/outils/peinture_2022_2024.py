"""Peinture au sol 2022 vs 2024 : carte de présence des marquages blancs/jaunes aux deux dates.

Les deux orthos sont lues à 0,20 m (PCRS 5 cm moyenné en boîte : même flou que l'IGN 20 cm).
Réponse « chapeau haut-de-forme » : gris − moyenne locale (boîte 2,2 m), normalisée par le
percentile 99,5 de chaque image ; pixel peint si réponse > 0,35 et saturation faible (blanc) ou
teinte jaune. Couleurs : blanc = peint aux deux dates, rouge = 2022 seulement (effacé / recouvert /
voiture en 2024), vert = 2024 seulement (nouveau / repeint décalé / voiture en 2022).
Planches par quart de site (150 m) et zooms des carrefours. Revue visuelle obligatoire (voitures,
ombres, toits).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa

RES = 0.2


def boite_moy(a, k):
    p = k // 2
    c = np.cumsum(np.cumsum(np.pad(a, ((p + 1, p), (p + 1, p)), mode="edge"), 0), 1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def peinture(a):
    g = a.mean(2)
    th = g - boite_moy(g, 11)
    th = th / max(np.percentile(th, 99.5), 1.0)
    sat = a.max(2) - a.min(2)
    jaune = (a[..., 0] > a[..., 2] + 35) & (a[..., 1] > a[..., 2] + 25)
    return (th > 0.35) & ((sat < 45) | jaune), jaune


def carte(nom, x0, y0, x1, y1, px=None):
    b = boite_locale(x0, y0, x1, y1)
    a22 = np.asarray(lire("2022", b, RES, Image.BOX), float)
    a24 = np.asarray(lire("2024", b, RES), float)
    p22, j22 = peinture(a22)
    p24, j24 = peinture(a24)
    fond = (a24.mean(2) * 0.45).astype(np.uint8)
    rgb = np.stack([fond] * 3, -1)
    rgb[p22 & p24] = (255, 255, 255)
    rgb[p22 & ~p24] = (255, 40, 40)
    rgb[~p22 & p24] = (40, 255, 40)
    im = Image.fromarray(rgb)
    if px:
        im = im.resize((px, round(px * im.height / im.width)), Image.NEAREST)
    v = Vue("2024", b, im.width, titre=f"{nom} : peinture blanc=2022+2024, rouge=2022 seul, vert=2024 seul", im=im)
    L = x1 - x0
    v.grille(5 if L <= 80 else 10, 10 if L <= 80 else 50)
    s = PLANCHES / "peinture" / f"peinture_{nom}.png"
    s.parent.mkdir(parents=True, exist_ok=True)
    v.im.save(s)
    n22, n24, nb = int(p22.sum()), int(p24.sum()), int((p22 & p24).sum())
    print(s.name, "px peints 2022", n22, "2024", n24, "communs", nb)
    return dict(n22=n22, n24=n24, communs=nb)


if __name__ == "__main__":
    st = {}
    for nom, bb in {"NO": (-150, 0, 0, 150), "NE": (0, 0, 150, 150), "SO": (-150, -150, 0, 0), "SE": (0, -150, 150, 0),
                    "coeur": (-35, -35, 35, 35)}.items():
        st[nom] = carte(nom, *bb)
    ecrire_json(DONNEES / "peinture_2022_2024_stats.json", {"methode": __doc__, "quarts": st})
