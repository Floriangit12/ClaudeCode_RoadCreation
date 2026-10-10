"""Vues aux poses Panoramax (photos 360 du 18/05/2025 dans l'emprise pilote, AVANT les travaux 2025) : rendu UE a la pose
de la photo et recadrage perspective (gnomonique, numpy) de la photo equirectangulaire, cote a cote.

Pose : lat/lon de la photo -> Lambert-93 (pyproj) -> repere local (L93 - O) ; Z = MNT 2026 (decrire/commun.MNT) +
HAUTEUR_M (GoPro Max sur le toit d'une voiture, visible dans le bas de la photo ; altitude GPS non fiable) ;
cap : azimut de la photo (colonne centrale de l'equirectangulaire, pers_yaw = 0) + decalage de vue, ramene au
quadrillage L93 par la convergence des meridiens (2,0086 deg : az_grille = az_vrai - 2,0086) ; cap local = 90 - az_grille ;
site 0 ; champ horizontal 90 deg.
Recadrage : rayon (x/f, -y/f, 1) -> longitude relative atan2(x, 1), latitude atan2(y, sqrt(1 + x^2)) ; colonne
equirect = W (1/2 + lon / 2 pi), ligne = H (1/2 - lat / pi) ; interpolation bilineaire.
Sorties : ue_pilote/panoramax/<id>_<vue>_photo.png, ctx_pano_<id>_<vue>.png|exr, planche_panoramax_<id>.png (photo | UE).
A comparer : elements inchanges (arbres, batiments, aspect general), pas les bordures refaites en 2025.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..')).replace('\\', '/')
PHOTOS = f'{DEPOT}/data/raw/panoramax/paquet_jardin'
OUT = f'{DEPOT}/recon/out/paquet_jardin/v2/ue_pilote'
O_L93 = (917279.43, 6460289.98, 216.30)
CONVERGENCE = 2.0086
HAUTEUR_M = 2.0
FOV = 90.0
W, H = 1200, 900
# (photo, nom de vue, decalage de cap depuis l'azimut de la photo) : vers l'avant (sud-ouest, le carrefour) pour les deux
# photos demandees ; vers l'arriere (nord-est, la zone pilote) en complement
VUES = [('2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5', 'avant', 0.0),
        ('2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433', 'avant', 0.0),
        ('2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5', 'arriere', 180.0),
        ('2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433', 'arriere', 180.0)]


def meta(nom):
    return json.load(open(f'{PHOTOS}/{nom}_hd.json', encoding='utf-8'))


def pose(nom, dcap):
    from pyproj import Transformer
    sys.path.insert(0, f'{DEPOT}/recon/pcg/decrire')
    import commun as C
    m = meta(nom)
    e, n = Transformer.from_crs('EPSG:4326', 'EPSG:2154', always_xy=True).transform(m['lon'], m['lat'])
    zsol = float(C.MNT()(np.array([e]), np.array([n]))[0])
    az_grille = (m['azimuth'] + dcap - CONVERGENCE) % 360.0
    return {'cam_x_m': e - O_L93[0], 'cam_y_m': n - O_L93[1], 'cam_z_m': zsol - O_L93[2] + HAUTEUR_M,
            'yaw_deg': (90.0 - az_grille + 540.0) % 360.0 - 180.0, 'pitch_deg': 0.0, 'fov_deg': FOV,
            'az_vrai_deg': (m['azimuth'] + dcap) % 360.0, 'az_grille_deg': az_grille, 'sol_ngf_m': round(zsol, 3),
            'l93': [round(e, 3), round(n, 3)], 'date': m['datetimetz'], 'precision_m': m.get('horizontal_accuracy_m')}


def recadrer(nom, dcap, w=W, h=H, fov=FOV):
    """Vue perspective (gnomonique) de la photo equirectangulaire, cap = azimut de la photo + dcap, site 0."""
    eq = np.asarray(Image.open(f'{PHOTOS}/{nom}_hd.jpg').convert('RGB')).astype(np.float32)
    He, We = eq.shape[:2]
    f = (w / 2.0) / math.tan(math.radians(fov) / 2.0)
    u, v = np.meshgrid(np.arange(w) + 0.5 - w / 2.0, np.arange(h) + 0.5 - h / 2.0)
    x, y = u / f, -v / f
    lon = np.arctan2(x, 1.0) + math.radians(dcap)
    lat = np.arctan2(y, np.sqrt(1.0 + x * x))
    px = (We * (0.5 + lon / (2 * math.pi)) - 0.5) % We
    py = np.clip(He * (0.5 - lat / math.pi) - 0.5, 0, He - 1.001)
    x0, y0 = np.floor(px).astype(int), np.floor(py).astype(int)
    tx, ty = (px - x0)[..., None], (py - y0)[..., None]
    x1 = (x0 + 1) % We
    out = (eq[y0, x0] * (1 - tx) + eq[y0, x1] * tx) * (1 - ty) + (eq[y0 + 1, x0] * (1 - tx) + eq[y0 + 1, x1] * tx) * ty
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def police(t):
    for n in ('arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(n, t)
        except OSError:
            pass
    return ImageFont.load_default()


def planche(court, lignes, chemin, auteur='', instance='', licence=''):
    """lignes : [(titre, photo PIL, rendu PIL)] -> planche photo | UE (credit de la photo en tete)."""
    c = 640
    hh = int(c * H / W)
    pl = Image.new('RGB', (2 * c + 24, 70 + len(lignes) * (hh + 40)), (24, 24, 24))
    d = ImageDraw.Draw(pl)
    d.text((8, 10), f'Panoramax {court} (18/05/2025, avant travaux) | Unreal 5.8 PJ_2026 (oct. 2026), meme pose, champ 90 deg',
           fill=(235, 235, 235), font=police(20))
    d.text((8, 38), f'Comparer les elements inchanges (arbres, batiments, ambiance) ; bordures, marquages et ilots refaits en 2025. '
           f'Photo : {auteur} / Panoramax ({instance}), {licence}.', fill=(200, 200, 200), font=police(15))
    y = 70
    for titre, ph, ue in lignes:
        d.text((8, y + 6), titre, fill=(235, 235, 235), font=police(16))
        pl.paste(ph.resize((c, hh), Image.LANCZOS), (8, y + 30))
        pl.paste(ue.resize((c, hh), Image.LANCZOS), (16 + c, y + 30))
        y += hh + 40
    pl.save(chemin, optimize=True)
    return chemin


def principal(c=None) -> str:
    """c : McpClient (captures UE) ; sans client, seulement les recadrages et les poses."""
    os.makedirs(f'{OUT}/panoramax', exist_ok=True)
    rapport, par_photo = {}, {}
    for nom, vue, dcap in VUES:
        court = nom.split('_')[1][:8]
        p = pose(nom, dcap)
        ph = recadrer(nom, dcap)
        f_ph = f'{OUT}/panoramax/{court}_{vue}_photo.png'
        ph.save(f_ph)
        png = f'{OUT}/ctx_pano_{court}_{vue}.png'
        r = {}
        if c is not None:
            sys.path.insert(0, os.path.join(ICI, '..', 'pilote'))
            import pilote
            r = pilote.capture(c, png, p, W, H)
        rapport[f'{court}_{vue}'] = {'photo': nom, 'pose': p, 'recadrage': f_ph, 'ue_png': png, 'ue_exr': r.get('exr'),
                                     'moyenne_srgb': r.get('moyenne')}
        if os.path.exists(png):
            par_photo.setdefault(court, []).append((f"{vue} : cap vrai {p['az_vrai_deg']:.0f} deg (grille {p['az_grille_deg']:.1f}), "
                                                    f"camera ({p['cam_x_m']:.1f} ; {p['cam_y_m']:.1f} ; {p['cam_z_m']:.2f}) m, "
                                                    f"{HAUTEUR_M:.1f} m au-dessus du MNT 2026", ph, Image.open(png).convert('RGB')))
    for court, lignes in par_photo.items():
        m = meta(next(n for n, _, _ in VUES if court in n))
        rapport[f'planche_{court}'] = planche(court, lignes, f'{OUT}/planche_panoramax_{court}.png', m.get('producer', ''),
                                              m.get('instance', ''), m.get('license', ''))
    chemin = f'{OUT}/contexte_panoramax.json'
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    return chemin


if __name__ == '__main__':
    print(principal())
