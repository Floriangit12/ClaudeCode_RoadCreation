"""Planches de comparaison du pilote (Pillow) : rendus Karma (recon/pc/rendus/v2_pilote/<vue>.png, 1000 x 1000) a cote
des captures UE aux memes poses (ue_pilote/ue_<v>_1000.png) -> ue_pilote/planche_karma_vs_ue.png ; gros plans des
joints de bordure -> ue_pilote/planche_joints_bordures.png (si les captures ue_joints_* existent).
Usage : python planche.py
"""
from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

import cameras

DEPOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')).replace('\\', '/')
OUT = f'{DEPOT}/recon/out/paquet_jardin/v2/ue_pilote'
KARMA = f'{DEPOT}/recon/pc/rendus/v2_pilote'
COTE = 480                     # planches versionnees (planche_*.png) : taille raisonnable
MARGE = 8
FOND = (24, 24, 24)
TEXTE = (235, 235, 235)


def police(t):
    for nom in ('arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(nom, t)
        except OSError:
            pass
    return ImageFont.load_default()


def vignette(chemin, cote=COTE):
    if not os.path.exists(chemin):
        im = Image.new('RGB', (cote, cote), (80, 0, 0))
        ImageDraw.Draw(im).text((10, 10), 'absent', fill=TEXTE, font=police(24))
        return im
    im = Image.open(chemin).convert('RGB')
    return im.resize((cote, int(round(cote * im.height / im.width))), Image.LANCZOS)


def planche_karma_ue(vues=None) -> str:
    vues = vues or sorted(cameras.VUES)
    f_t, f_s = police(26), police(18)
    entete = 60
    h_ligne = COTE + 34
    W = 2 * COTE + 3 * MARGE
    H = entete + len(vues) * (h_ligne + MARGE) + MARGE
    pl = Image.new('RGB', (W, H), FOND)
    d = ImageDraw.Draw(pl)
    d.text((MARGE, 10), 'Pilote ZP-01 : Karma XPU (Houdini, gauche) | Unreal 5.8 Lumen, EV100 14 (droite)', fill=TEXTE, font=f_t)
    y = entete
    for v in vues:
        cam = cameras.VUES[v]
        d.text((MARGE, y + 4), f'{v} : {cam}', fill=TEXTE, font=f_s)
        pl.paste(vignette(f'{KARMA}/{cam}.png'), (MARGE, y + 30))
        pl.paste(vignette(f'{OUT}/ue_{v}_1000.png'), (2 * MARGE + COTE, y + 30))
        y += h_ligne + MARGE
    chemin = f'{OUT}/planche_karma_vs_ue.png'
    pl.save(chemin, optimize=True)
    return chemin


def planche_joints() -> str | None:
    noms = sorted(f for f in os.listdir(OUT) if f.startswith('ue_joints_') and f.endswith('.png'))
    if not noms:
        return None
    f_s = police(18)
    ims = [vignette(f'{OUT}/{n}', 720) for n in noms]
    W = 720 + 2 * MARGE
    H = sum(i.height + 34 + MARGE for i in ims) + MARGE
    pl = Image.new('RGB', (W, H), FOND)
    d = ImageDraw.Draw(pl)
    y = MARGE
    for n, im in zip(noms, ims):
        d.text((MARGE, y + 4), n[:-4], fill=TEXTE, font=f_s)
        pl.paste(im, (MARGE, y + 30))
        y += im.height + 34 + MARGE
    chemin = f'{OUT}/planche_joints_bordures.png'
    pl.save(chemin, optimize=True)
    return chemin


def principal() -> str:
    return json.dumps({'karma_vs_ue': planche_karma_ue(), 'joints': planche_joints()}, ensure_ascii=False)


if __name__ == '__main__':
    print(principal())
