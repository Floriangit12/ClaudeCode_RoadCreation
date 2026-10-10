# -*- coding: utf-8 -*-
"""Planche PNG des gabarits de marquages_geometrie.json (numpy + PIL), même échelle pour tous."""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

doc = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]
G = doc["gabarits"]
S = 2            # suréchantillonnage
PXM = 130 * S    # px par mètre
try:
    F = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13 * S)
    FB = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15 * S)
except OSError:
    F = FB = ImageFont.load_default()

rangs = [["TD", "TAD", "TAG", "TD_TAD", "TD_TAG", "RAB_D", "RAB_G"],
         ["CEDEZ_V60", "CEDEZ_V60P", "VELO", "VELO@x3", "DAMIER_BUS", "PAVE_CHRONOVELO", "CARRE_TRAVERSEE_CYCLABLE"]]
MARGE = 40 * S
cases = []
y0 = MARGE
for rang in rangs:
    x0 = MARGE
    hmax = 0
    for nom in rang:
        k, f = (nom.split("@x")[0], float(nom.split("@x")[1])) if "@x" in nom else (nom, 1.0)
        g = G[k]
        bx, by = g["boite"]["x"], g["boite"]["y"]
        w = (bx[1] - bx[0]) * PXM * f + 2 * 60 * S
        h = (by[1] - by[0]) * PXM * f + 2 * 50 * S
        w = max(w, 190 * S)
        cases.append((nom, k, f, x0, y0, w, h))
        x0 += w
        hmax = max(hmax, h)
    y0 += hmax + 20 * S
W = int(max(c[3] + c[5] for c in cases) + MARGE)
H = int(y0 + MARGE)
im = Image.new("RGB", (W, H), (236, 236, 232))
d = ImageDraw.Draw(im)
for nom, k, f, x0, y0, w, h in cases:
    g = G[k]
    bx, by = g["boite"]["x"], g["boite"]["y"]
    ox = x0 + 60 * S - bx[0] * PXM * f
    oy = y0 + h - 50 * S + by[0] * PXM * f
    T = lambda p: (ox + p[0] * PXM * f, oy - p[1] * PXM * f)
    # grille 0,5 m (0,1 m pour les agrandissements)
    pas = 0.1 if f > 1 else 0.5
    import math
    for i in range(math.floor(bx[0] / pas) - 1, math.ceil(bx[1] / pas) + 2):
        X = ox + i * pas * PXM * f
        d.line([(X, y0 + 30 * S), (X, y0 + h - 20 * S)], fill=(212, 212, 206), width=S)
    for j in range(math.floor(by[0] / pas) - 1, math.ceil(by[1] / pas) + 2):
        Y = oy - j * pas * PXM * f
        if y0 + 30 * S <= Y <= y0 + h - 20 * S:
            d.line([(x0 + 10 * S, Y), (x0 + w - 10 * S, Y)], fill=(212, 212, 206), width=S)
    coul = (60, 60, 64) if g.get("couleur", "blanc") == "blanc" else (170, 140, 20)
    anneaux = [g["polygone"]]
    if g.get("parties"):
        anneaux += [g["parties"]["roue_arriere"]["polygone"], g["parties"]["roue_avant"]["polygone"]]
    for A in anneaux:
        d.polygon([T(p) for p in A], fill=coul, outline=(20, 20, 20))
    for t in g.get("trous") or []:
        d.polygon([T(p) for p in t], fill=(236, 236, 232), outline=(20, 20, 20))
    for A in anneaux + (g.get("trous") or []):
        for p in A:
            X, Y = T(p)
            r = 2.2 * S
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=(220, 40, 40))
    # origine
    X, Y = T((0, 0))
    d.line([(X - 9 * S, Y), (X + 9 * S, Y)], fill=(0, 110, 220), width=2 * S)
    d.line([(X, Y - 9 * S), (X, Y + 9 * S)], fill=(0, 110, 220), width=2 * S)
    titre = k + (f"  (x{f:g})" if f != 1 else "")
    d.text((x0 + 12 * S, y0 + 4 * S), titre, font=FB, fill=(0, 0, 0))
    d.text((x0 + 12 * S, y0 + 22 * S), f"{g['longueur_m']:.3f} x {g['largeur_m']:.3f} m · n {g['n_sommets']}", font=F, fill=(40, 40, 40))
d.text((MARGE, H - 30 * S), "Gabarits marquages_geometrie.json — même échelle (130 px/m), grille 0,5 m (0,1 m pour VELO x3) ; points rouges = sommets ; croix bleue = origine ; y = sens de circulation",
       font=F, fill=(0, 0, 0))
im = im.resize((W // S, H // S), Image.LANCZOS)
im.save(OUT)
print(OUT, im.size)
