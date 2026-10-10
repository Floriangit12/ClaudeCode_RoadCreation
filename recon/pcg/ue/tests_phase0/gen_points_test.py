"""Genere le jeu d'essai pj_points/0.1 de la phase 0 (200 arbres) depuis le paquet v1.

Source : recon/out/paquet_jardin/package/donnees/objets/instances.json (prototypes arbre_*).
Selection : les 200 arbres les plus proches du centre du carrefour (-1.569, -5.089).
Correspondance (essai seulement) : arbre_feuillu -> Oak_M ou Maple_M selon la parite du hash de l'id,
arbre_jeune_tuteure -> Maple_M, arbre_conifere -> Oak_M (aucun conifere dans le couple impose).
Echelle : s = (couronne/couronne_asset, idem, hauteur/hauteur_asset) a partir des dimensions nominales
du prototype x scale de l'instance ; dimensions des assets mesurees dans UE (bounding box).
Orientation : q (quaternion local xyzw, prioritaire pour charger_points) et rpy_deg (lisible), cf. CONTRAT_EXPORT.md.
Sorties : <OUT>/points_test_arbres.json (+ .csv, meme contenu a plat, pour la voie Data Table).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os

import commun as C
from pj_tools import repere

SRC = os.path.join(C.DEPOT, 'recon', 'out', 'paquet_jardin', 'package', 'donnees', 'objets', 'instances.json')
CENTRE = (-1.569, -5.089)
N = 200
TREES = '/Game/Carla/Static/Vegetation/Trees'
ASSETS = {  # hauteur, couronne moyenne (m) mesurees sur la bounding box UE
    'oak': (f'{TREES}/SM_Oak_M_v1.SM_Oak_M_v1', 9.325, 8.35),
    'maple': (f'{TREES}/SM_Maple_M_v1.SM_Maple_M_v1', 8.776, 7.84),
}
PROTO = {'arbre_feuillu': (10.0, 6.0), 'arbre_conifere': (12.0, 5.0), 'arbre_jeune_tuteure': (4.5, 1.8)}


def graine(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16) & 0x7FFFFFFF


def main() -> str:
    brut = open(SRC, 'rb').read()
    doc = json.loads(brut.decode('utf-8'))
    arbres = [i for i in doc['instances'] if str(i.get('prototype', '')).startswith('arbre_')]
    arbres.sort(key=lambda i: (math.hypot(i['x'] - CENTRE[0], i['y'] - CENTRE[1]), i['id']))
    pts = []
    for i in arbres[:N]:
        proto = i['prototype']
        g = graine(i['id'])
        cle = {'arbre_jeune_tuteure': 'maple', 'arbre_conifere': 'oak'}.get(proto, 'oak' if g % 2 == 0 else 'maple')
        asset, h_a, c_a = ASSETS[cle]
        h_n, c_n = PROTO[proto]
        sx, sy, sz = i.get('scale', [1, 1, 1])
        sh = round(h_n * sz / h_a, 4)
        sc = round(c_n * sx / c_a, 4)
        rpy = [0.0, 0.0, float(i.get('yaw_deg', 0.0))]
        pts.append({'id': i['id'], 'asset': asset, 'p': [i['x'], i['y'], i['z']],
                    'q': [round(v, 9) for v in repere.quat_depuis_rpy(*rpy)], 'rpy_deg': rpy, 's': [sc, sc, sh],
                    'graine': g, 'prototype': proto})
    sortie = {'schema': 'pj_points/0.1', 'famille': 'arbres_test_phase0',
              'source': os.path.relpath(SRC, C.DEPOT).replace('\\', '/'),
              'source_hash': 'sha256:' + hashlib.sha256(brut).hexdigest(),
              'repere': 'local m (L93 - O), Z haut ; UE : X=100x, Y=-100y, Z=100z ; '
                        'q local xyzw -> Quat(-x,y,-z,w) ; rpy -> Rotator(roll=r, pitch=-p, yaw=-y)',
              'points': pts}
    p = os.path.join(C.OUT, 'points_test_arbres.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(sortie, f, ensure_ascii=False, indent=1)
    with open(os.path.join(C.OUT, 'points_test_arbres.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Name', 'Id', 'Mesh', 'X_cm', 'Y_cm', 'Z_cm', 'Yaw_ue', 'SX', 'SY', 'SZ', 'Graine'])
        for q in pts:
            w.writerow([q['id'], q['id'], q['asset'], round(q['p'][0] * 100, 3), round(-q['p'][1] * 100, 3),
                        round(q['p'][2] * 100, 3), -q['rpy_deg'][2], *q['s'], q['graine']])
    return p


if __name__ == '__main__':
    chemin = main()
    d = json.load(open(chemin, encoding='utf-8'))
    from collections import Counter
    print(chemin, len(d['points']), Counter(q['asset'].rsplit('/', 1)[-1] for q in d['points']))
