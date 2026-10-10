"""Prépare les textures du sol V2 pour Unreal (hors éditeur, numpy + PIL) et mesure leurs moyennes.

    python recon/pcg/ue/materiaux/preparer_textures.py [--forcer]

1. Mesure, pour chaque dossier CC0 utilisé par materiaux_sol.json (assets/lib/materiaux/<nom>/textures),
   l'albédo moyen LINÉAIRE (décodage sRGB exact), la rugosité et l'AO moyennes ; idem pour les PNG City Sample
   exportés (recon/pc/citysample/textures, réservés à Unreal).
2. Cartes de hauteur (16 bits, alignées sur les cartes 1024 px de la bibliothèque) :
   - ambientCG : *_Displacement.jpg du zip en cache (data/raw/assets_src/cc0/ambientcg/<id>/2K) ;
   - Poly Haven (pas de hauteur en cache) : intégration de la carte de normales OpenGL (Frankot-Chellappa),
     validée sur WoodChips003 contre son Displacement réel (corrélation affichée).
3. Textures maison : bruit macro tuilable (T_PJ_BruitMacro, RVB = 3 bruits fBm périodiques indépendants,
   graine 2154) et masque d'usure de la peinture (spec assets/specs/peinture.json, graine 1967, générateur
   de assets/telecharger_cc0.py).
Sorties images : data/raw/assets_src/cc0_derive/ (non versionné) ; mesures : materiaux/mesures_textures.json.
Déterministe : mêmes entrées -> mêmes octets (sha256 dans le JSON).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import sys
import zipfile

import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import catalogue as C  # noqa: E402

N_HAUTEUR = 1024
# passe-haut des hauteurs intégrées : sigma ~ 2 à 3 tailles d'élément (gravier 6/14 mm sur 2 m = 512 px/m)
SIGMA_PX = {'gravier_concasse_6_10': 10.0, 'paillage_mineral': 30.0}


def srgb_vers_lin(a):
    a = np.asarray(a, np.float64) / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def moyenne_albedo(p):
    a = srgb_vers_lin(np.asarray(Image.open(p).convert('RGB')))
    return [round(float(x), 4) for x in a.reshape(-1, 3).mean(0)]


def moyenne_scalaire(p, canal=0):
    im = Image.open(p)
    a = np.asarray(im, np.float64)
    if a.ndim == 3:
        a = a[..., canal]
    return round(float(a.mean() / (65535.0 if a.max() > 255 else 255.0)), 4)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def ecrire_png16(a01, p):
    Image.fromarray((np.clip(a01, 0, 1) * 65535 + 0.5).astype(np.uint16)).save(p)


def normaliser(h):
    """Hauteur -> [0, 1] par centiles 0,5-99,5 % (robuste aux pics)."""
    lo, hi = np.percentile(h, [0.5, 99.5])
    return np.clip((h - lo) / max(hi - lo, 1e-9), 0, 1)


def hauteur_depuis_normales(p_normale):
    """Frankot-Chellappa : normales OpenGL (+Y = haut de l'image) -> hauteur périodique (unités relatives)."""
    n = np.asarray(Image.open(p_normale).convert('RGB'), np.float64) / 255.0 * 2 - 1
    nz = np.maximum(n[..., 2], 0.2)
    gx = -n[..., 0] / nz                  # dh/dx (colonnes vers la droite)
    gy = n[..., 1] / nz                   # dh/d(ligne) : +Y OpenGL = vers le haut = lignes décroissantes
    h, w = gx.shape
    wx = np.fft.fftfreq(w)[None, :] * 2 * np.pi
    wy = np.fft.fftfreq(h)[:, None] * 2 * np.pi
    den = wx ** 2 + wy ** 2
    den[0, 0] = 1.0
    F = (-1j * wx * np.fft.fft2(gx) - 1j * wy * np.fft.fft2(gy)) / den
    F[0, 0] = 0
    return np.real(np.fft.ifft2(F))


def flou_periodique(a, sigma_px):
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.fftfreq(a.shape[1])[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * np.pi ** 2 * sigma_px ** 2 * (fx ** 2 + fy ** 2))))


def passe_haut(h, sigma_px=24.0, part_basse=0.25):
    """L'intégration des normales dérive aux basses fréquences (nuages sans rapport avec le relief) : on garde le
    relief à l'échelle des éléments et seulement part_basse (en écart-type) d'ondulation lente."""
    b = flou_periodique(h, sigma_px)
    hp = h - b
    lp = (b - b.mean()) / max(b.std(), 1e-12) * hp.std()
    return hp + part_basse * lp


def displacement_zip(source_id):
    d = os.path.join(C.CACHE_CC0, 'ambientcg', source_id, '2K')
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.endswith('.zip'):
            with zipfile.ZipFile(os.path.join(d, f)) as z:
                for nom in z.namelist():
                    if nom.endswith('_Displacement.jpg') or nom.endswith('_Displacement.png'):
                        im = Image.open(io.BytesIO(z.read(nom)))
                        a = np.asarray(im, np.float64)
                        if a.ndim == 3:
                            a = a[..., 0]
                        a = a / (65535.0 if a.max() > 255 else 255.0)
                        return a, nom
    return None


def redim_float(a, n):
    if a.shape[0] == n:
        return a
    im = Image.fromarray(a.astype(np.float32), 'F').resize((n, n), Image.LANCZOS)
    return np.asarray(im, np.float64)


def correlation(a, b):
    a = (a - a.mean()) / a.std()
    b = (b - b.mean()) / b.std()
    return float((a * b).mean())


def module_telecharger():
    spec = importlib.util.spec_from_file_location('telecharger_cc0', os.path.join(C.DEPOT, 'assets', 'telecharger_cc0.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--forcer', action='store_true', help='régénérer les images dérivées existantes')
    args = ap.parse_args()
    os.makedirs(C.DERIVE_DIR, exist_ok=True)
    out = {'schema': 'pj_mesures_textures/1', 'cc0': {}, 'citysample': {}, 'maison': {}}

    # ---- 1-2. dossiers CC0 utilisés + hauteurs
    validation = None
    for nom in C.dossiers_cc0():
        meta = json.load(open(os.path.join(C.CC0_DIR, nom, 'meta.json'), encoding='utf-8'))
        tx = {t['role']: os.path.join(C.CC0_DIR, nom, t['fichier']) for t in meta['textures']}
        e = {'source': f"{meta['source']} {meta['source_id']}", 'tile_m': meta.get('tile_m'),
             'roles': sorted(tx), 'albedo_moyen_lin': moyenne_albedo(tx['albedo'])}
        if 'rugosite' in tx:
            e['rugosite_moyenne'] = moyenne_scalaire(tx['rugosite'])
        if 'ao' in tx:
            e['ao_moyen'] = moyenne_scalaire(tx['ao'])
        dst = os.path.join(C.DERIVE_DIR, nom)
        os.makedirs(dst, exist_ok=True)
        ph = os.path.join(dst, f'{nom}_hauteur.png')
        dz = displacement_zip(meta['source_id']) if meta['source'] == 'ambientCG' else None
        if dz is not None:
            h, src = normaliser(redim_float(dz[0], N_HAUTEUR)), f'zip ambientCG : {dz[1]}'
            methode = 'displacement'
            if meta['source_id'] == 'WoodChips003':      # validation du sens de l'intégration
                fc = normaliser(redim_float(hauteur_depuis_normales(tx['normale']), N_HAUTEUR))
                hp = h - np.asarray(Image.fromarray(h.astype(np.float32), 'F').resize((64, 64), Image.BOX).resize(
                    (N_HAUTEUR, N_HAUTEUR), Image.BILINEAR), np.float64)
                fp = fc - np.asarray(Image.fromarray(fc.astype(np.float32), 'F').resize((64, 64), Image.BOX).resize(
                    (N_HAUTEUR, N_HAUTEUR), Image.BILINEAR), np.float64)
                validation = {'texture': 'WoodChips003', 'correlation_brute': round(correlation(h, fc), 3),
                              'correlation_hautes_frequences': round(correlation(hp, fp), 3)}
        elif 'normale' in tx:
            sig = SIGMA_PX.get(nom, 24.0)
            h = normaliser(passe_haut(redim_float(hauteur_depuis_normales(tx['normale']), N_HAUTEUR), sig))
            src = f'intégration des normales (Frankot-Chellappa), passe-haut sigma {sig:g} px + 25 % de basses fréquences'
            methode = 'normales_integrees'
        else:
            h = None
        if h is not None:
            if args.forcer or not os.path.exists(ph):
                ecrire_png16(h, ph)
            e['hauteur'] = {'fichier': os.path.relpath(ph, C.DEPOT).replace('\\', '/'), 'methode': methode, 'source': src,
                            'moyenne': round(float(h.mean()), 4), 'p10_p90': [round(float(x), 4) for x in np.percentile(h, [10, 90])],
                            'sha256': sha(ph)}
        out['cc0'][nom] = e
        print(f'{nom:28s} albedo {e["albedo_moyen_lin"]} rug {e.get("rugosite_moyenne")} haut {e.get("hauteur", {}).get("methode")}')
    out['validation_integration'] = validation
    print('validation intégration normales -> hauteur :', validation)

    # ---- City Sample (PNG exportés, Unreal seulement)
    for f in sorted(os.listdir(C.CS_DIR)):
        if not f.endswith('.png'):
            continue
        p = os.path.join(C.CS_DIR, f)
        im = Image.open(p)
        e = {'px': im.size[0], 'mode': im.mode}
        if f.endswith('_albedo.png'):
            e['albedo_moyen_lin'] = moyenne_albedo(p)
        elif 'rugosite' in f or 'roughness' in f:
            e['moyenne'] = moyenne_scalaire(p)
        out['citysample'][f] = e

    # ---- 3. textures maison
    tc = module_telecharger()
    p = os.path.join(C.DERIVE_DIR, 'pj', 'pj_bruit_macro.png')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if args.forcer or not os.path.exists(p):
        rng = np.random.default_rng(2154)
        n = 1024
        rgb = np.stack([tc.bruit_periodique(n, n / 4.0, 3, rng, 0.55),
                        tc.bruit_periodique(n, n / 8.0, 3, rng, 0.5),
                        tc.bruit_periodique(n, n / 24.0, 2, rng, 0.5)], -1)
        Image.fromarray(np.round(rgb * 255).astype(np.uint8), 'RGB').save(p)
    out['maison']['pj_bruit_macro.png'] = {'role': 'bruit macro tuilable (R : 1/4 de tuile, G : 1/8, B : 1/24), uniforme 0-1, linéaire',
                                           'graine': 2154, 'sha256': sha(p)}
    p = os.path.join(C.DERIVE_DIR, 'pj', 'masque_usure_peinture.png')
    spec = json.load(open(C.SPEC_PEINTURE, encoding='utf-8'))
    if args.forcer or not os.path.exists(p):
        M = np.round(tc.generer_masque(spec) * 255) / 255.0
        Image.fromarray(np.round(M * 255).astype(np.uint8), 'RGBA').save(p)
    out['maison']['masque_usure_peinture.png'] = {'role': 'masque d\'usure RGBA (peinture.json usure.masque)', 'graine': 1967,
                                                  'tile_m': spec['usure']['masque']['tile_m'], 'sha256': sha(p)}
    json.dump(out, open(C.MESURES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('écrit', C.MESURES)


if __name__ == '__main__':
    main()
