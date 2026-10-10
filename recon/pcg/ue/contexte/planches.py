"""Planches de comparaison du contexte (Pillow) -> recon/out/paquet_jardin/v2/ue_pilote/planche_*.png :
- planche_contexte_pilote.png : 6 vues du pilote avec le contexte, reference neutre (ctx_<v>_1920x1080.png, EV100 14 fixe,
  capteurs ; carre central) | vignette des planches (ctx_<v>_1000.png, exposition locale) ;
- planche_contexte_v1.png : 4 vues de controle v1 (recon/pc/houdini/cameras.usda), rendu Karma du paquet v1
  (recon/pc/rendus/v1/<camera>.png, volumes provisoires) | UE avec le contexte (ctx_<cam>_1000.png).
- planche_revue_pieton.png : vues de revue a hauteur de pieton (contexte.py revue) ;
- planche_corrections_revue.png (option --avant DIR : captures d'avant les corrections de la revue UE du 10/10, memes noms) :
  avant | apres sur les vues qui portent les defauts revus (pointes de sol et BEV, enrobes, gazon, feuilles, BRF, gravier,
  joints, horizon).
Les planches Panoramax sont faites par panoramax.py (planche_panoramax_<id>.png).
Usage : python planches.py [--avant DIR]
"""
from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..')).replace('\\', '/')
OUT = f'{DEPOT}/recon/out/paquet_jardin/v2/ue_pilote'
KARMA_V1 = f'{DEPOT}/recon/pc/rendus/v1'
PILOTE = {'a': 'a_pieton_file_joints', 'b': 'b_abaisse_traversee_bev', 'c': 'c_entree_charretiere', 'd': 'd_ilot_brf',
          'e': 'e_ilot_gravier', 'f': 'f_vue_ensemble'}
V1 = {'cam1': 'cam1_ensemble_sud', 'cam2': 'cam2_conducteur_verdun_so', 'cam3': 'cam3_pieton_traversee_so',
      'cam4': 'cam4_conducteur_vercors'}
COTE, MARGE = 480, 8


def police(t):
    for n in ('arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(n, t)
        except OSError:
            pass
    return ImageFont.load_default()


def vignette(chemin, carre=False):
    if not os.path.exists(chemin):
        im = Image.new('RGB', (COTE, COTE), (80, 0, 0))
        ImageDraw.Draw(im).text((10, 10), 'absent', fill=(235, 235, 235), font=police(24))
        return im
    im = Image.open(chemin).convert('RGB')
    if carre and im.width > im.height:                    # carre central (memes cadrages que les vignettes 1000 x 1000)
        x0 = (im.width - im.height) // 2
        im = im.crop((x0, 0, x0 + im.height, im.height))
    return im.resize((COTE, int(round(COTE * im.height / im.width))), Image.LANCZOS)


def planche(titre, lignes, chemin, carre_gauche=False):
    """lignes : [(legende, image gauche, image droite)] ; carre_gauche : carre central de l'image de gauche ; hauteur de
    ligne = plus haute des deux vignettes."""
    vg = [(leg, vignette(g, carre=carre_gauche), vignette(dr)) for leg, g, dr in lignes]
    hs = [max(a.height, b.height) + 34 for _, a, b in vg]
    pl = Image.new('RGB', (2 * COTE + 3 * MARGE, 60 + sum(h + MARGE for h in hs) + MARGE), (24, 24, 24))
    d = ImageDraw.Draw(pl)
    d.text((MARGE, 10), titre, fill=(235, 235, 235), font=police(22))
    y = 60
    for (leg, a, b), h in zip(vg, hs):
        d.text((MARGE, y + 4), leg, fill=(235, 235, 235), font=police(17))
        pl.paste(a, (MARGE, y + 30))
        pl.paste(b, (2 * MARGE + COTE, y + 30))
        y += h + MARGE
    pl.save(chemin, optimize=True)
    return chemin


# vues des defauts de la revue UE du 10/10 : (legende, fichier avant, fichier apres)
CORRECTIONS = [
    ('b : pointe de sol en fin de bordurette K-9297a, dalles BEV en saillie', 'ue_b_1000.png', 'ue_b_1000.png'),
    ('a : enrobe ancien (0,26 -> 0,18), trottoir, gazon, horizon', 'ctx_a_1000.png', 'ctx_a_1000.png'),
    ('cam2 : horizon (relief Vercors / Bastille), ciel, contexte', 'ctx_cam2_1000.png', 'ctx_cam2_1000.png'),
    ('c : feuilles mortes (decalques), ombres des arbres', 'ctx_c_1000.png', 'ctx_c_1000.png'),
    ('d : eclats de BRF (M_PJ_Eclat), beton de bordure', 'ctx_d_1000.png', 'ctx_d_1000.png'),
    ('e : concasse anguleux (prototypes biseautes), fond a 0,14', 'ctx_e_1000.png', 'ctx_e_1000.png'),
    ('joint K-0369/J004 : beton fin, joint et mortier', 'ue_joints_K-0369_J004.png', 'ue_joints_K-0369_J004.png'),
    ('Panoramax e5d79de9 avant (SO) : horizon de montagnes', 'ctx_pano_e5d79de9_avant.png', 'ctx_pano_e5d79de9_avant.png'),
]


def principal(avant=None) -> str:
    r = {'pilote': planche('Pilote ZP-01 : reference neutre EV 14 (gauche) | exposition locale (droite)',
                           [(f'{v} : {n}', f'{OUT}/ctx_{v}_1920x1080.png', f'{OUT}/ctx_{v}_1000.png') for v, n in PILOTE.items()],
                           f'{OUT}/planche_contexte_pilote.png', carre_gauche=True),
         'v1': planche('Vues de controle v1 : Karma, paquet v1 a volumes provisoires (gauche) | Unreal 5.8 PJ_2026 (droite)',
                       [(f'{v} : {n}', f'{KARMA_V1}/{n}.png', f'{OUT}/ctx_{v}_1000.png') for v, n in V1.items()],
                       f'{OUT}/planche_contexte_v1.png')}
    rv = [f'{OUT}/revue_{v}.png' for v in ('pieton_10m', 'pieton_nord_est', 'pieton_ilot_gazon', 'pieton_bev')]
    if all(os.path.exists(f) for f in rv):
        r['revue'] = planche('Vues de revue a hauteur de pieton (EV 14 fixe)',
                             [('pieton_10m (SO, contre-jour) | pieton_nord_est', rv[0], rv[1]),
                              ('pieton_ilot_gazon | pieton_bev', rv[2], rv[3])], f'{OUT}/planche_revue_pieton.png')
    if avant:
        r['corrections'] = planche('Revue UE 10/10 : avant (gauche, EV 14 fixe) | apres (droite, expo. locale)',
                                   [(leg, f'{avant}/{a}', f'{OUT}/{b}') for leg, a, b in CORRECTIONS],
                                   f'{OUT}/planche_corrections_revue.png')
    return json.dumps(r, ensure_ascii=False)


if __name__ == '__main__':
    import sys
    print(principal(sys.argv[sys.argv.index('--avant') + 1] if '--avant' in sys.argv else None))
