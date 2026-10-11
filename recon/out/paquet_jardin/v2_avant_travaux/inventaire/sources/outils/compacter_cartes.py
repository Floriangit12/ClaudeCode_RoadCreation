#!/usr/bin/env python
"""Réduit la taille des cartes PNG : palette fixe = 224 niveaux de gris (fond d'ortho désaturé) + couleurs des séries
et du texte, sans tramage. Usage : python -I compacter_cartes.py <dossier_cartes> [planche_synthese:oui|non]"""
import glob
import os
import sys

from PIL import Image

COUL = [(42, 120, 214), (235, 104, 52), (27, 175, 122), (74, 58, 167), (11, 11, 11), (82, 81, 78), (125, 124, 120),
        (252, 252, 251), (255, 255, 255), (230, 229, 225), (238, 236, 230), (150, 149, 145)]
pal = []
for g in range(224):
    v = round(g * 255 / 223)
    pal += [v, v, v]
for c in COUL:
    pal += list(c)
pal += [0, 0, 0] * (256 - len(pal) // 3)
P = Image.new("P", (1, 1))
P.putpalette(pal)
d = sys.argv[1]
if len(sys.argv) < 3 or sys.argv[2] != "non":
    noms = ["2017-2021", "2022", "2023", "2024", "2025-S1", "apres_debut_travaux"]
    ims = [Image.open(os.path.join(d, f"couverture_photos_{n}.png")).convert("RGB") for n in noms]
    w, h = ims[0].size
    W, H = w // 2, h // 2
    out = Image.new("RGB", (W * 3, H * 2), (252, 252, 251))
    for i, im in enumerate(ims):
        out.paste(im.resize((W, H), Image.LANCZOS), ((i % 3) * W, (i // 3) * H))
    out.save(os.path.join(d, "couverture_photos_synthese.png"))
for f in glob.glob(os.path.join(d, "*.png")):
    im = Image.open(f).convert("RGB")
    im.quantize(palette=P, dither=Image.Dither.NONE).save(f, optimize=True)
    print(os.path.basename(f), os.path.getsize(f))
