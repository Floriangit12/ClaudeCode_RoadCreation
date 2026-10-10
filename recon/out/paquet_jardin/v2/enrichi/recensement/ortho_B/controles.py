"""controles.py : contrôles automatiques d'appui à la revue visuelle (agent VISION-ORTHO-B).

Pour chaque dalle ortho 2022 :
- marquages de la description : part de l'empreinte couverte par de la peinture (blanche ou jaune)
  détectée sur la dalle (seuil local : luminance > fond flou 2 m + 30, saturation faible, ou jaune) ;
- peinture non expliquée : composantes de peinture sur surfaces circulées (surfaces v1 chaussée,
  parking, piste, accès riverain, quai bus) hors de toute empreinte de marquage dilatée de 0,30 m ;
- arbres : indice de verdure (ExG) dans un disque de 1,5 m autour du point ;
- inventaire : entités présentes sur la dalle avec pixel (u, v).
Ce ne sont que des indices : chaque verdict est relu sur les vues (overlay.py) avant d'être noté.

python controles.py --toutes | --tuiles <t...>   -> controles/<tuile>.json, controles/<tuile>_peinture.jpg
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overlay import ICI, PAS, TUILES_B, Dalle, charger  # noqa: E402

CIRCULE = {"chaussee", "parking", "piste_cyclable", "acces_riverain", "quai_bus"}


def flou(a, r):
    """Moyenne glissante (2r+1)^2 par sommes cumulées."""
    p = np.pad(a, r + 1, mode="edge").astype(np.float64)
    c = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return (s / (k * k))[:a.shape[0], :a.shape[1]]


def peinture(img):
    a = np.asarray(img, np.float32)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    L = 0.299 * R + 0.587 * G + 0.114 * B
    fond = flou(L, 20)
    sat = a.max(-1) - a.min(-1)
    blanc = (L > fond + 30) & (L > 150) & (sat < 45)
    jaune = (R > 150) & (G > 120) & (B < 0.75 * G) & (R - B > 70) & (L > fond + 15)
    return blanc, jaune


def masque(D, anneaux, poly, largeur_px=3):
    m = Image.new("L", (1000, 1000), 0)
    dr = ImageDraw.Draw(m)
    for k, an in enumerate(anneaux):
        P = [tuple(p) for p in D.l93_vers_px(an)]
        if poly:
            dr.polygon(P, fill=0 if k > 0 and poly == "trous" else 255)
        elif len(P) > 1:
            dr.line(P, fill=255, width=max(1, int(round(largeur_px))))
        else:
            dr.ellipse([P[0][0] - largeur_px, P[0][1] - largeur_px, P[0][0] + largeur_px, P[0][1] + largeur_px],
                       fill=255)
    return np.asarray(m) > 0


def dilate(m, r):
    return flou(m.astype(np.float32), r) > 1e-6


def composantes(m, mini):
    """Étiquetage 8-connexe sur pixels actifs (liste), renvoie bbox, aire, centroïde."""
    ys, xs = np.nonzero(m)
    act = set(zip(ys.tolist(), xs.tolist()))
    out = []
    while act:
        p = act.pop()
        pile, comp = [p], [p]
        while pile:
            y, x = pile.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (y + dy, x + dx)
                    if q in act:
                        act.remove(q)
                        pile.append(q)
                        comp.append(q)
        if len(comp) >= mini:
            c = np.array(comp)
            out.append(dict(aire_px=len(comp), u=round(float(c[:, 1].mean()), 1), v=round(float(c[:, 0].mean()), 1),
                            bbox=[int(c[:, 1].min()), int(c[:, 0].min()), int(c[:, 1].max()), int(c[:, 0].max())]))
    return out


def controler(tuile):
    D = Dalle(tuile)
    x0, y0, x1, y1 = D.emprise()
    blanc, jaune = peinture(D.img)
    pein = blanc | jaune
    circ = np.zeros((1000, 1000), bool)
    toutes = np.zeros((1000, 1000), bool)
    res = dict(tuile=tuile, marquages=[], arbres=[], inventaire=[], peinture_non_expliquee=[])
    a = np.asarray(D.img, np.float32)
    exg = 2 * a[..., 1] - a[..., 0] - a[..., 2]
    for e in charger():
        bx = e["bbox"]
        if bx[2] < x0 or bx[0] > x1 or bx[3] < y0 or bx[1] > y1:
            continue
        uv = D.l93_vers_px(np.vstack(e["anneaux"]).mean(0))
        dedans = 0 <= uv[0] < 1000 and 0 <= uv[1] < 1000
        if e["couche"] == "surfaces_v1" and e["props"].get("classe") in CIRCULE:
            circ |= masque(D, e["anneaux"][:1], True)
        if e["couche"] == "marquages":
            p = e["props"]
            larg = (p.get("largeur_m") or 0.15) / PAS
            m = masque(D, e["anneaux"], e["poly"], larg)
            toutes |= m
            n = int(m.sum())
            if n == 0:
                continue
            res["marquages"].append(dict(id=e["id"], classe=p.get("classe"), type=p.get("type"),
                                         etat=p.get("etat"), couleur=p.get("couleur"), n_px=n,
                                         blanc=round(float((m & blanc).sum() / n), 3),
                                         jaune=round(float((m & jaune).sum() / n), 3),
                                         uv=[round(float(uv[0]), 1), round(float(uv[1]), 1)]))
        elif e["couche"] == "arbres" and dedans:
            yy, xx = np.mgrid[0:1000, 0:1000]
            d = np.hypot(xx - uv[0], yy - uv[1]) < 30
            res["arbres"].append(dict(id=e["id"], uv=[round(float(uv[0]), 1), round(float(uv[1]), 1)],
                                      exg=round(float(exg[d].mean()), 1), vert=round(float((exg[d] > 15).mean()), 2),
                                      h=e["props"].get("hauteur_m"), couronne=e["props"].get("diametre_couronne_m"),
                                      type=e["props"].get("type"), etat=e["props"].get("statut_2026")))
        if dedans or e["couche"] in ("marquages", "bordures", "bordures_site", "surfaces", "ilots"):
            res["inventaire"].append(dict(couche=e["couche"], id=e["id"], uv=[round(float(uv[0]), 1),
                                                                               round(float(uv[1]), 1)]))
    libre = pein & circ & ~dilate(toutes, 6)
    res["peinture_non_expliquee"] = sorted(composantes(libre, 40), key=lambda c: -c["aire_px"])
    vis = np.asarray(D.img).copy()
    vis[toutes] = (vis[toutes] * 0.5 + np.array([0, 90, 255]) * 0.5).astype(np.uint8)
    vis[libre] = (255, 0, 0)
    im = Image.fromarray(vis)
    dr = ImageDraw.Draw(im)
    for c in res["peinture_non_expliquee"]:
        b = c["bbox"]
        dr.rectangle([b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3], outline=(255, 255, 0))
    out = ICI / "controles"
    out.mkdir(exist_ok=True)
    im.save(out / f"{tuile}_peinture.jpg", quality=88)
    with open(out / f"{tuile}.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuiles", nargs="*", default=[])
    ap.add_argument("--toutes", action="store_true")
    a = ap.parse_args()
    for t in (TUILES_B if a.toutes else a.tuiles):
        r = controler(t)
        print(t, "marquages", len(r["marquages"]), "arbres", len(r["arbres"]),
              "peinture libre", len(r["peinture_non_expliquee"]))
