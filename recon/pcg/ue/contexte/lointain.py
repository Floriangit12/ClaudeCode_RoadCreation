"""Lointain du site (Python pur + pyproj, deterministe) : batiments et arbres publics de Meylan hors du carre v1 (+-150 m)
et a moins de RAYON_M de l'origine, pour fermer l'horizon des vues (sans eux : plan de gazon jusqu'a l'horizon).

- Batiments : cadastre Etalab (data/context/cadastre-38229-batiments.json.gz, WGS84 -> L93 -> local) ; emprise sans
  hauteur : hauteur a priori par l'aire et le type (02 = construction legere : 3 m ; < 40 m2 : 3 m ; < 200 m2 : maison
  6,5 m ; < 500 m2 : 10 m ; < 1 500 m2 : 15 m ; au-dela 19 m ; +-15 % tire par graine) -> ue_pilote/usd/lointain_entrees.json,
  extrude par preparer_usd.py (couche lointain.usdc, base au plan de contexte Z_PLAN).
- Arbres : inventaire des arbres de la Metropole (data/context/arbres_metropole.geojson, etat « Present ») ; hauteur =
  classe d'inventaire (60 % de l'intervalle ; « 0 » ou absente : 8 m), couronne = 0,55 h ; essence -> modele par la meme
  table que le site (vegetation/correspondance_carla.json, vegetation/arbres.Choix) -> ue_pilote/points/arbres_lointains_ue.json.
Usage : python lointain.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..'))
CTX = os.path.join(DEPOT, 'data', 'context')
UE_PILOTE = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'v2', 'ue_pilote')
sys.path.insert(0, os.path.join(ICI, '..', 'vegetation'))
O = (917279.43, 6460289.98)
DEMI_COTE_V1 = 150.0
RAYON_M = 700.0
Z_PLAN = -0.9                       # sol lointain (relief_usd.sol_lointain) : mediane de l'altitude du bord du terrain v1
                                    # (revue UE du 10/10 : plan a -4,1 m, marche de 1 a 6 m au bord du carre v1)


def graine(*p) -> int:
    return int.from_bytes(hashlib.sha256('|'.join(map(str, p)).encode()).digest()[:4], 'little') & 0x7FFFFFFF


def hors_site(x, y):
    return (abs(x) > DEMI_COTE_V1 or abs(y) > DEMI_COTE_V1) and math.hypot(x, y) < RAYON_M


def aire(r):
    return 0.5 * abs(sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1)))


def batiments(t):
    g = json.load(gzip.open(os.path.join(CTX, 'cadastre-38229-batiments.json.gz'), 'rt', encoding='utf-8'))
    out = []
    for k, f in enumerate(g['features']):
        geo = f['geometry']
        polys = geo['coordinates'] if geo['type'] == 'MultiPolygon' else [geo['coordinates']]
        for j, poly in enumerate(polys):
            xs, ys = t.transform([c[0] for c in poly[0]], [c[1] for c in poly[0]])
            r = [(round(x - O[0], 3), round(y - O[1], 3)) for x, y in zip(xs, ys)]
            cx, cy = sum(p[0] for p in r[:-1]) / (len(r) - 1), sum(p[1] for p in r[:-1]) / (len(r) - 1)
            if not hors_site(cx, cy):
                continue
            a = aire(r)
            if a < 8.0:
                continue
            leg = f['properties'].get('type') == '02'
            h = 3.0 if (leg or a < 40) else 6.5 if a < 200 else 10.0 if a < 500 else 15.0 if a < 1500 else 19.0
            bid = f'cad_{k:05d}_{j}'
            h *= 0.85 + 0.30 * (graine(bid, 'h') % 1000) / 1000.0
            out.append({'id': bid, 'anneau': r, 'h': round(h, 2), 'aire_m2': round(a, 1), 'legere': leg})
    return out


def arbres(t):
    import arbres as A
    table = A.lire(os.path.join(ICI, '..', 'vegetation', 'correspondance_carla.json'))
    cat = A.lire(os.path.join(ICI, '..', 'vegetation', 'catalogue_carla.json'))['assets']
    ch = A.Choix(table, cat)
    feats = json.load(open(os.path.join(CTX, 'arbres_metropole.geojson'), encoding='utf-8'))['features']
    pts = []
    for f in feats:
        p = f['properties']
        if p.get('etat') != 'Présent':
            continue
        lon, lat = f['geometry']['coordinates'][0]
        x, y = t.transform(lon, lat)
        x, y = x - O[0], y - O[1]
        if not hors_site(x, y):
            continue
        cl = p.get('hauteur') or ''
        try:
            lo, hi = cl.strip('[').split(';')
            lo = float(lo)
            hi = float(hi.strip('m[').replace('+', '') or lo + 10) if hi.strip('m[+') else lo + 10
            h = lo + 0.6 * (hi - lo)
        except ValueError:
            h = 8.0
        h = max(h, 3.0)
        tid = f"metro_{p.get('arbre_id')}"
        typ = 'conifere' if str(p.get('type')).lower().startswith('conif') else 'feuillu'
        props = {'id': tid, 'type': typ, 'essence': p.get('essence'), 'genre': p.get('genre'), 'hauteur_m': h,
                 'diametre_couronne_m': round(0.55 * h, 2), 'etat_2026': 'existant (inventaire Metropole)'}
        c = ch.arbre(props)
        hq = math.radians(c['yaw']) / 2.0
        pts.append({'id': tid, 'asset': A.chemin_asset(c['modele']), 'p': [round(x, 3), round(y, 3), Z_PLAN - 0.03],
                    'q': [0.0, 0.0, round(math.sin(hq), 7), round(math.cos(hq), 7)], 'rpy_deg': [0.0, 0.0, round(c['yaw'], 4)],
                    's': [round(c['sxy'], 4), round(c['sxy'], 4), round(c['sz'], 4)], 'graine': graine(tid),
                    'x': {'essence': p.get('essence'), 'famille': c['famille'], 'h_data': h, 'h_posee': round(c['sz'] * c['h_asset'], 2)}})
    return sorted(pts, key=lambda q: q['id'])


def principal() -> dict:
    from pyproj import Transformer
    t = Transformer.from_crs('EPSG:4326', 'EPSG:2154', always_xy=True)
    b = batiments(t)
    os.makedirs(os.path.join(UE_PILOTE, 'usd'), exist_ok=True)
    with open(os.path.join(UE_PILOTE, 'usd', 'lointain_entrees.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'source': 'recon/pcg/ue/contexte/lointain.py (cadastre Etalab, hauteurs a priori)', 'z_base': Z_PLAN,
                   'batiments': b}, f, ensure_ascii=False, separators=(',', ':'))
    pts = arbres(t)
    tete = {'schema': 'pj_points/0.1', 'famille': 'arbres_lointains',
            'source_hash': hashlib.sha256(open(os.path.join(CTX, 'arbres_metropole.geojson'), 'rb').read()).hexdigest(),
            'repere': 'local (L93 - O, z = NGF - 216,30), m, Z haut', 'pivot': 'pied du tronc',
            'source': 'data/context/arbres_metropole.geojson ; recon/pcg/ue/contexte/lointain.py'}
    chemin = os.path.join(UE_PILOTE, 'points', 'arbres_lointains_ue.json')
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    lignes = [json.dumps(tete, ensure_ascii=False)[:-1] + ',\n"points": [']
    for i, q in enumerate(pts):
        lignes.append(json.dumps(q, ensure_ascii=False, separators=(',', ':')) + (',' if i < len(pts) - 1 else ''))
    lignes.append(']}')
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lignes) + '\n')
    from collections import Counter
    return {'batiments': len(b), 'aire_m2': round(sum(x['aire_m2'] for x in b)), 'hauteurs': dict(Counter(round(x['h']) for x in b).most_common(8)),
            'arbres': len(pts), 'familles': dict(Counter(q['x']['famille'] for q in pts)), 'sortie_arbres': chemin}


if __name__ == '__main__':
    print(json.dumps(principal(), ensure_ascii=False, indent=1))
