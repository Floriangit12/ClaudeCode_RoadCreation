"""Profil de l'horizon de montagnes (azimut vrai -> site) releve sur les photos 360 Panoramax du site (revue UE du
10/10 : horizon plat et laiteux ; Saint-Eynard, Chartreuse, Belledonne et Vercors absents). Aucun MNT regional hors
ligne : le relief lointain est reconstruit depuis ce profil (lointain_usd.py, anneau de relief).

Methode (numpy, Pillow) :
- photos 360 equirectangulaires (colonne centrale = azimut de la photo, pers_pitch = pers_roll = 0), reduites a
  4 px/deg ; ciel = pixels clairs et bleutes ou nuages clairs peu satures, connexes au haut de l'image ;
- ligne de ciel de chaque colonne : premier pixel non-ciel en descendant depuis +45 deg ; site = (H/2 - ligne) / 4 ;
- les objets proches (arbres, batiments, mats) relevent la ligne de ciel d'une photo a l'autre, pas les montagnes
  (parallaxe < 2 deg a 3 km sur 150 m de deplacement) : par degre d'azimut vrai, quantile bas (Q) des photos qui voient
  cet azimut, puis filtre median sur 5 deg ; azimuts sans ciel visible : interpolation circulaire ;
- sorties : ue_pilote/horizon/profil.json (site par degre, nombre de photos, quantile) et planche de controle
  (bandes d'horizon des photos avec le profil retenu superpose).

    python recon/pcg/ue/contexte/horizon.py [--max 60] [--q 0.15]
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
from PIL import Image, ImageDraw

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..')).replace('\\', '/')
PHOTOS = f'{DEPOT}/data/raw/panoramax/paquet_jardin'
OUT = f'{DEPOT}/recon/out/paquet_jardin/v2/ue_pilote/horizon'
PX_DEG = 4
SITE_MAX = 45.0


def ciel(rgb):
    """Masque de couleur du ciel : bleu clair (B > R, lumineux) ou nuage / voile clair et peu sature."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    bleu = (b > r + 18) & (b > g - 4) & (lum > 95)
    nuage = (lum > 175) & (sat < 0.22)
    return bleu | nuage, lum


def ligne_de_ciel(nom):
    """Site de la ligne de ciel par colonne (nan si la colonne ne commence pas dans le ciel). En descendant depuis
    +SITE_MAX : la ligne est le premier pixel qui n'a plus la couleur du ciel OU qui est plus sombre que 0,88 x le ciel
    juste au-dessus (montagnes lointaines voilees : bleutees mais plus sombres que le ciel), suivi de 2 deg non-ciel."""
    im = Image.open(nom).convert('RGB')
    W, H = 360 * PX_DEG, 180 * PX_DEG
    a = np.asarray(im.resize((W, H), Image.BILINEAR)).astype(np.float32)
    h0 = H // 2 - int(SITE_MAX * PX_DEG)
    zone = a[h0:H // 2 + 4 * PX_DEG]
    coul, lum = ciel(zone)
    n = zone.shape[0]
    ref = np.full(W, np.nan)
    ligne = np.full(W, n)
    actif = coul[0] & coul[1]
    ref[actif] = lum[:2, actif].mean(axis=0)
    non = np.zeros((n, W), dtype=bool)
    for y in range(n):
        sombre = lum[y] < 0.88 * np.nan_to_num(ref, nan=0.0)
        non[y] = ~coul[y] | sombre
        ok = ~non[y] & np.isfinite(ref)
        ref[ok] = 0.8 * ref[ok] + 0.2 * lum[y, ok]                          # ciel juste au-dessus (degrade lent)
    run = 2 * PX_DEG
    cum = np.vstack([np.zeros((1, W)), np.cumsum(non, axis=0)])
    for y in range(n - run):
        plein = (cum[y + run] - cum[y]) >= run - 1                           # 2 deg non-ciel (1 pixel toléré)
        prend = plein & non[y] & (ligne == n)
        ligne[prend] = y
    site = (H // 2 - (h0 + ligne)) / PX_DEG
    return np.where(actif, site, np.nan)


def principal(n_max=60, q=0.15):
    os.makedirs(OUT, exist_ok=True)
    metas = []
    for f in sorted(glob.glob(f'{PHOTOS}/*_hd.json')):
        m = json.load(open(f, encoding='utf-8'))
        if m.get('is_360') and m.get('dist_center_m', 1e9) < 160 and (m.get('pers_pitch') in (None, 0, 0.0)):
            metas.append(m)
    metas.sort(key=lambda m: (m['datetime'][:10] < '2024-08', m['dist_center_m']))   # poses de cap fiables d'abord
    metas = metas[:n_max]
    pile = np.full((len(metas), 360), np.nan)
    for i, m in enumerate(metas):
        s = ligne_de_ciel(f"{PHOTOS}/{m['local_file']}")
        W = 360 * PX_DEG
        az = (m['azimuth'] + (np.arange(W) + 0.5 - W / 2) / PX_DEG) % 360.0      # colonne -> azimut vrai
        k = np.floor(az).astype(int) % 360
        for d in range(360):
            v = s[k == d]
            v = v[np.isfinite(v)]
            if len(v):
                pile[i, d] = np.median(v)
    n = np.isfinite(pile).sum(axis=0)
    prof = np.full(360, np.nan)
    for d in range(360):
        v = pile[np.isfinite(pile[:, d]), d]
        if len(v) >= 3:
            prof[d] = np.quantile(v, q)
    # filtre median circulaire sur 5 deg puis interpolation des trous
    ext = np.r_[prof[-2:], prof, prof[:2]]
    med = np.array([np.nanmedian(ext[d:d + 5]) if np.isfinite(ext[d:d + 5]).any() else np.nan for d in range(360)])
    ok = np.isfinite(med)
    az = np.arange(360)
    if ok.sum() >= 2:
        xs = np.r_[az[ok] - 360, az[ok], az[ok] + 360]
        ys = np.r_[med[ok], med[ok], med[ok]]
        med = np.interp(az, xs, ys)
    out = {'source': 'Panoramax 360 (CC-BY-SA 4.0, voir ATTRIBUTIONS.md), recon/pcg/ue/contexte/horizon.py',
           'methode': f'ligne de ciel par colonne, quantile {q} sur {len(metas)} photos, median 5 deg',
           'photos': [m['id'][:8] for m in metas], 'quantile': q,
           'site_deg': [round(float(x), 2) for x in med], 'n_photos': [int(x) for x in n],
           'interpole': [int(not x) for x in ok]}
    json.dump(out, open(f'{OUT}/profil.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    planche(metas[:6], med)
    return {'photos': len(metas), 'azimuts_interpoles': int((~ok).sum()), 'site_max': round(float(np.max(med)), 2),
            'az_site_max': int(np.argmax(med)), 'profil': f'{OUT}/profil.json'}


def planche(metas, prof):
    """Bandes d'horizon (+25 a -5 deg) de quelques photos, recalees en azimut vrai, avec le profil retenu (rouge)."""
    W = 360 * PX_DEG
    bandes = []
    for m in metas:
        im = Image.open(f"{PHOTOS}/{m['local_file']}").convert('RGB').resize((W, 180 * PX_DEG), Image.BILINEAR)
        a = np.asarray(im)
        dec = int(round((m['azimuth'] - 180.0) * PX_DEG))                   # colonne 0 = azimut 0
        a = np.roll(a, dec, axis=1)
        b = Image.fromarray(a[(90 - 25) * PX_DEG:(90 + 5) * PX_DEG])
        d = ImageDraw.Draw(b)
        pts = [(x, (25 - prof[int(x / PX_DEG) % 360]) * PX_DEG) for x in range(0, W, 2)]
        d.line(pts, fill=(255, 0, 0), width=2)
        for az in range(0, 360, 30):
            d.text((az * PX_DEG + 2, 2), f'{az}', fill=(255, 255, 0))
        d.text((4, 104), f"{m['id'][:8]} {m['datetime'][:10]} (CC-BY-SA 4.0 Panoramax)", fill=(255, 255, 255))
        bandes.append(b)
    p = Image.new('RGB', (W, sum(b.height for b in bandes)))
    y = 0
    for b in bandes:
        p.paste(b, (0, y))
        y += b.height
    p.save(f'{OUT}/controle_profil.png')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--max', type=int, default=60)
    ap.add_argument('--q', type=float, default=0.15)
    a = ap.parse_args()
    print(json.dumps(principal(a.max, a.q), ensure_ascii=False))
