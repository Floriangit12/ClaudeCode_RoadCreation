"""Clotures du paquet v1 -> points PCG (Python pur, deterministe) : lignes « cloture » de package/donnees/objets/instances.json
(51 polylignes, 926 m, hauteur 1,6 / 1,8 m) -> ue_pilote/points/clotures_ue.json (pj_points/0.1).

Panneau CARLA SM_fence_09_v<n> (grillage sur muret beton, 2,40 m le long de +Y UE, 1,60 m de haut, semelle enterree
jusqu'a -1 m : suit les pentes) : chaque segment de polyligne est decoupe en panneaux de longueur egale (<= 2,40 m),
mis a l'echelle le long du panneau (s[1]) et en hauteur (h / 1,60) ; pivot au debut du panneau ; lacet local =
direction du segment + 90 deg (l'axe +Y UE du modele est l'axe -y local) ; Z = sol rendu sous chaque sommet
(ue_pilote/usd/z_objets.json) interpole ; variante tiree par graine (sha256(id | k)).
Usage : python clotures.py [SORTIE_DIR]
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..'))
OBJETS = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'package', 'donnees', 'objets')
UE_PILOTE = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'v2', 'ue_pilote')
MODELE = '/Game/Carla/Static/Fence/SM_fence_09_v{v}'
VARIANTES = (1, 2, 3, 4)
L_PANNEAU = 2.40
H_MODELE = 1.60


def g(*parts) -> int:
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:4], 'little') & 0x7FFFFFFF


def principal(sortie_dir: str = os.path.join(UE_PILOTE, 'points')) -> dict:
    inst = json.load(open(os.path.join(OBJETS, 'instances.json'), encoding='utf-8'))
    zf = os.path.join(UE_PILOTE, 'usd', 'z_objets.json')
    zsol = json.load(open(zf, encoding='utf-8'))['z'] if os.path.exists(zf) else {}
    pts, longueur, sans_z = [], 0.0, 0
    for l in sorted(inst['lignes'], key=lambda q: q['id']):
        if l.get('prototype') != 'cloture':
            continue
        sz = float(l.get('hauteur_m') or H_MODELE) / H_MODELE
        P = l['points']
        Z = []
        for k in range(len(P)):
            z = zsol.get(f"{l['id']}/{k}")
            if z is None:
                sans_z += 1
            Z.append(z)
        zs = [z for z in Z if z is not None]
        Z = [z if z is not None else (sum(zs) / len(zs) if zs else 0.0) for z in Z]
        for k in range(len(P) - 1):
            (x0, y0), (x1, y1) = P[k], P[k + 1]
            d = math.hypot(x1 - x0, y1 - y0)
            if d < 0.05:
                continue
            longueur += d
            n = max(1, math.ceil(d / L_PANNEAU - 1e-6))
            th = math.degrees(math.atan2(y1 - y0, x1 - x0))
            yaw = th + 90.0
            h = math.radians(yaw) / 2.0
            for i in range(n):
                t = i / n
                pid = f"{l['id']}/{k:03d}/{i:02d}"
                v = VARIANTES[g(pid) % len(VARIANTES)]
                nom = MODELE.format(v=v)
                pts.append({'id': pid, 'asset': f'{nom}.{nom.rsplit("/", 1)[-1]}',
                            'p': [round(x0 + t * (x1 - x0), 3), round(y0 + t * (y1 - y0), 3),
                                  round(Z[k] + t * (Z[k + 1] - Z[k]), 3)],
                            'q': [0.0, 0.0, round(math.sin(h), 7), round(math.cos(h), 7)], 'rpy_deg': [0.0, 0.0, round(yaw, 4)],
                            's': [1.0, round(d / n / L_PANNEAU, 4), round(sz, 4)], 'graine': g(pid),
                            'x': {'ligne': l['id'], 'hauteur_m': l.get('hauteur_m'), 'statut': l.get('statut')}})
    tete = {'schema': 'pj_points/0.1', 'famille': 'clotures',
            'source_hash': hashlib.sha256(open(os.path.join(OBJETS, 'instances.json'), 'rb').read()).hexdigest(),
            'repere': 'local (L93 - O, z = NGF - 216,30), m, Z haut',
            'pivot': 'debut du panneau, au sol (modele CARLA : panneau le long de +Y UE = -y local)',
            'source': 'package/donnees/objets/instances.json (lignes cloture) ; recon/pcg/ue/contexte/clotures.py',
            'bibliotheque': 'asset = StaticMesh CARLA /Game/Carla/Static/Fence (CC-BY 4.0)'}
    os.makedirs(sortie_dir, exist_ok=True)
    lignes = [json.dumps(tete, ensure_ascii=False)[:-1] + ',\n"points": [']
    for i, q in enumerate(pts):
        lignes.append(json.dumps(q, ensure_ascii=False, separators=(',', ':')) + (',' if i < len(pts) - 1 else ''))
    lignes.append(']}')
    chemin = os.path.join(sortie_dir, 'clotures_ue.json')
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lignes) + '\n')
    return {'sortie': chemin, 'panneaux': len(pts), 'longueur_m': round(longueur, 1), 'sommets_sans_z': sans_z}


if __name__ == '__main__':
    print(json.dumps(principal(*sys.argv[1:2]), ensure_ascii=False, indent=1))
