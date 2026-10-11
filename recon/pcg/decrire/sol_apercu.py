"""Planches de contrôle des familles de sol v2 (site complet) sur l'ortho 2022 du paquet.

Usage :
    python recon/pcg/decrire/sol_apercu.py DOSSIER_SORTIE [--base DOSSIER_BASE]
Produit, dans DOSSIER_SORTIE : sol_site.png (site complet), sol_<zoom>.png (4 zooms) et nivellement_<…>.png
(ombrage + classes de pente des cheminements, même emprise). Légende en bas à droite.
- surfaces teintées par classe (partition vectorielle), emprises de bordure en blanc, rampes en cyan ;
- bordures colorées par profil, bateaux en rouge épais, chartières en magenta ;
- ponts entre bouts de bordure (K-95nn) en jaune, fermetures résiduelles (limite raster signalée) en rouge fin ;
- BEV en cyan plein, îlots cernés de magenta ;
- nivellement : ombrage du modèle, pentes de cheminement > 5 % jaune, > 8 % orange, > 12 % rouge.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from apercu import fond_ortho, police
from commun import SORTIE, abscisses, anneaux, lire_geojson, repere, sous_polyligne

COUL_CLASSE = {"chaussee": (70, 70, 210), "parking": (140, 140, 230), "acces_riverain": (160, 100, 200),
               "piste_cyclable": (0, 190, 230), "trottoir": (230, 150, 60), "quai_bus": (255, 60, 60),
               "ilot": (255, 230, 0), "terre_plein_vegetal": (30, 120, 30), "espace_vert": (50, 170, 50),
               "autre": (200, 200, 200), "emprise_bordure": (255, 255, 255)}
COUL_PROFIL = {"T2": (255, 255, 255), "T3": (255, 150, 40), "A2": (255, 230, 0), "P1": (170, 170, 170),
               "T2_bateau": (255, 40, 40), "QUAI_BUS": (0, 160, 255), "MURET_TALUS": (120, 60, 0)}
ZOOMS = {
    "ilots_verdun_so": (-32.0, -36.0, 2.0, -4.0),
    "trottoirs_ne": (18.0, 12.0, 62.0, 56.0),
    "coeur_carrefour": (-22.0, -22.0, 22.0, 22.0),
    "vercors_noue": (0.0, -62.0, 44.0, -18.0),
}


def planche(sortie, base, emprise, res, nom=""):
    x0, y0, x1, y1 = emprise
    img = fond_ortho(x0, y0, x1, y1, res)
    img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.30)
    d = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    k = max(1, int(round(0.04 / res)))
    tp = lambda P: [((x - x0) / res, (y1 - y) / res) for x, y in np.asarray(P)[:, :2]]
    for f in lire_geojson(base / "surfaces.geojson"):
        p = f["properties"]
        c = COUL_CLASSE.get(p["classe"], (255, 0, 255))
        a = 150 if p["classe"] == "emprise_bordure" else 85
        if "rampe" in p:
            c, a = (0, 255, 255), 140
        for poly in anneaux(f["geometry"]):
            r = tp(repere(poly[0]))
            d.polygon(r, fill=c + (a,), outline=c + (200,))
            for h in poly[1:]:
                d.polygon(tp(repere(h)), fill=(0, 0, 0, 0), outline=(255, 255, 255, 120))
        if p.get("limite_raster") and p["fermetures_m"] > 0.5:
            for poly in anneaux(f["geometry"]):
                d.line(tp(repere(np.vstack([poly[0], poly[0][:1]]))), fill=(255, 0, 0, 90), width=1)
    for f in lire_geojson(base / "ilots.geojson"):
        for poly in anneaux(f["geometry"]):
            r = tp(repere(poly[0]))
            d.line(r + r[:1], fill=(255, 0, 255, 255), width=2 * k)
    for f in lire_geojson(base / "ponctuels_sol.geojson"):
        for poly in anneaux(f["geometry"]):
            d.polygon(tp(repere(poly[0])), fill=(0, 255, 255, 220))
    for f in lire_geojson(base / "bordures.geojson"):
        p = f["properties"]
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        if P[:, 0].max() < x0 - 2 or P[:, 0].min() > x1 + 2 or P[:, 1].max() < y0 - 2 or P[:, 1].min() > y1 + 2:
            continue
        pont = (p["source"].get("pont") is not None)
        for it in p["intervalles"]:
            seg = sous_polyligne(P, it["s0"], it["s1"])
            col = (255, 0, 255) if it["role"] == "chartiere" else COUL_PROFIL.get(it["profil"], (255, 0, 255))
            if pont:
                col = (255, 255, 0)
            d.line(tp(seg), fill=col + (255,), width=(3 if it["role"] != "courant" or pont else 1) * k)
    fp = police(max(10, int(12 * k)))
    if (x1 - x0) <= 80:
        for f in lire_geojson(base / "bordures.geojson"):
            P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            q = P[len(P) // 2]
            if x0 <= q[0] <= x1 and y0 <= q[1] <= y1:
                d.text(tp([q])[0], f["properties"]["id"][2:], fill=(255, 255, 160), font=fp)
    pas = 10 if (x1 - x0) <= 100 else 50
    for gx in range(int(math.ceil(x0 / pas) * pas), int(x1) + 1, pas):
        d.line(tp([(gx, y0), (gx, y1)]), fill=(255, 255, 255, 40))
        d.text(tp([(gx + 0.2, y1 - 0.2)])[0], str(gx), fill=(255, 255, 255), font=fp)
    for gy in range(int(math.ceil(y0 / pas) * pas), int(y1) + 1, pas):
        d.line(tp([(x0, gy), (x1, gy)]), fill=(255, 255, 255, 40))
        d.text(tp([(x0 + 0.2, gy)])[0], str(gy), fill=(255, 255, 255), font=fp)
    lg = [(f"sol {c}", col) for c, col in COUL_CLASSE.items()] + [("rampe / palier", (0, 255, 255)), ("BEV", (0, 255, 255))]
    lg += [(f"bordure {p}", c) for p, c in COUL_PROFIL.items()] + [("chartière", (255, 0, 255)), ("pont (K-95nn)", (255, 255, 0)),
                                                                      ("limite résiduelle", (255, 0, 0))]
    fl = police(12)
    hl = 15
    bx, by = W - 210, H - 10 - hl * len(lg)
    d.rectangle((bx - 6, by - 6, W - 4, H - 4), fill=(0, 0, 0, 170))
    for i, (t, c) in enumerate(lg):
        d.rectangle((bx, by + i * hl, bx + 12, by + i * hl + 10), fill=c + (255,))
        d.text((bx + 18, by - 2 + i * hl), t, fill=(255, 255, 255), font=fl)
    if nom:
        d.text((8, 8), nom, fill=(255, 255, 255), font=police(16))
    img.save(sortie)
    return W, H


def planche_nivellement(sortie, base, emprise, k=1):
    """Ombrage du modèle + classes de pente (même région, base 2 m) des cheminements et du reste."""
    g = np.load(base / "nivellement_grille.npz")
    x0g, y0g, pas = float(g["x0"]), float(g["y0"]), float(g["pas"])
    z, reg = g["z0"].astype(np.float64), g["r0"].astype(np.int32)
    x0, y0, x1, y1 = emprise
    base_px = 20
    i0, i1 = int((x0 - x0g) / pas), int((x1 - x0g) / pas) + 1
    j0, j1 = int((y0 - y0g) / pas), int((y1 - y0g) / pas) + 1
    # pentes calculées sur une fenêtre élargie de la base (pas de bande vide au bord de l'image)
    e0, e1 = max(0, i0 - base_px), min(z.shape[1], i1 + base_px)
    f0, f1 = max(0, j0 - base_px), min(z.shape[0], j1 + base_px)
    ZE, RE = z[f0:f1, e0:e1], reg[f0:f1, e0:e1]
    Z, R = z[j0:j1, i0:i1], reg[j0:j1, i0:i1]
    gy, gx = np.gradient(np.nan_to_num(Z), pas)
    sl = np.arctan(np.hypot(gx, gy) * 4.0)
    asp = np.arctan2(-gx, gy)
    az, alt = np.radians(315.0), np.radians(35.0)
    hs = np.clip(np.sin(alt) * np.cos(sl) + np.cos(alt) * np.sin(sl) * np.cos(az - asp), 0, 1)
    rgb = np.dstack([hs * 235 + 20] * 3).astype(np.uint8)
    p = np.zeros(ZE.shape)
    for ax in (0, 1):
        a = [slice(None), slice(None)]
        b = [slice(None), slice(None)]
        a[ax] = slice(0, -base_px)
        b[ax] = slice(base_px, None)
        ok = (RE[tuple(a)] == RE[tuple(b)]) & (RE[tuple(a)] >= 0)
        dz = np.where(ok, np.abs(ZE[tuple(b)] - ZE[tuple(a)]), 0.0) / (base_px * pas)
        tmp = np.zeros(ZE.shape)
        tmp[tuple(a)] = np.nan_to_num(dz)
        p = np.maximum(p, tmp)
    p = p[j0 - f0:j0 - f0 + Z.shape[0], i0 - e0:i0 - e0 + Z.shape[1]]
    rgb[(p > 0.05) & (p <= 0.08)] = (255, 230, 0)
    rgb[(p > 0.08) & (p <= 0.12)] = (255, 140, 0)
    rgb[p > 0.12] = (255, 0, 0)
    rgb[np.isnan(Z)] = (0, 0, 70)
    img = Image.fromarray(rgb[::-1])
    if k != 1:
        img = img.resize((img.width * k, img.height * k), Image.NEAREST)
    img.save(sortie)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sortie")
    ap.add_argument("--base", default=str(SORTIE / "base"))
    a = ap.parse_args()
    out = Path(a.sortie)
    out.mkdir(parents=True, exist_ok=True)
    base = Path(a.base)
    planche(out / "sol_site.png", base, (-150.0, -150.0, 150.0, 150.0), 0.12, "site complet (300 m)")
    planche_nivellement(out / "nivellement_site.png", base, (-150.0, -150.0, 150.0, 150.0))
    for nom, e in ZOOMS.items():
        planche(out / f"sol_{nom}.png", base, e, 0.025, nom)
        planche_nivellement(out / f"nivellement_{nom}.png", base, e, k=3)
    print(f"planches écrites dans {out}")


if __name__ == "__main__":
    main()
