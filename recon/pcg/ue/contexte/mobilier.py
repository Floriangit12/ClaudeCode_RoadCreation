"""Mobilier v1 -> substituts CARLA (Python pur, deterministe) : instances.json du paquet v1 -> ue_pilote/points/mobilier_ue.json.

Les volumes provisoires du paquet v1 ne sont pas importes ; aux positions et hauteurs relevees, des modeles CARLA
(CC-BY 4.0) tiennent lieu de mobilier en attendant les assets francais de la phase 5 :
- lampadaire_crosse_double -> SM_Streetlight2_group3 (double crosse), sz = h / 8,2 ;
- lampadaire_crosse_simple -> SM_Streetlight1_group3 (crosse selon +X comme le prototype v1), sz = h / 5,24, sxy 1,2 ;
- lampadaire_mat_droit     -> SM_Streetlight4_group2 (lanterne en tete), sz = h / 3,95, sxy 1,1 ;
- poteau_reseau            -> SM_ElectricPole03 (poteau bois), sz = h / 7,61 ;
- potelet                  -> SM_Bollard01, sz = h / 0,683.
Non substitues (aucun equivalent francais) : feux, panneaux, abris, bornes... (phase 5).
Hauteur v1 = hauteur nominale du prototype x scale[2] ; Z = sol rendu (ue_pilote/usd/z_objets.json), a defaut z v1 ;
lacet = yaw_deg v1 (axe +X du prototype = axe +X du modele CARLA).
Usage : python mobilier.py [SORTIE_DIR]
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
P = '/Game/Carla/Static/Pole'
# prototype v1 -> (asset, hauteur nominale v1 (m), hauteur du modele (m), echelle horizontale)
TABLE = {
    'lampadaire_crosse_double': (f'{P}/StreetLights/Group3/SM_Streetlight2_group3', 10.0, 8.207, 1.0),
    'lampadaire_crosse_simple': (f'{P}/StreetLights/Group3/SM_Streetlight1_group3', 10.0, 5.24, 1.2),
    'lampadaire_mat_droit': (f'{P}/StreetLights/Group2/SM_Streetlight4_group2', 6.0, 3.946, 1.1),
    'poteau_reseau': (f'{P}/PoweLine/SM_ElectricPole03', 9.0, 7.609, 1.0),
    'potelet': (f'{P}/SM_Lights/SM_Bollard01', 1.0, 0.683, 1.0),
}


def principal(sortie_dir: str = os.path.join(UE_PILOTE, 'points')) -> dict:
    inst = json.load(open(os.path.join(OBJETS, 'instances.json'), encoding='utf-8'))
    zf = os.path.join(UE_PILOTE, 'usd', 'z_objets.json')
    zsol = json.load(open(zf, encoding='utf-8'))['z'] if os.path.exists(zf) else {}
    pts, ignores = [], {}
    for i in sorted(inst['instances'], key=lambda q: q['id']):
        t = TABLE.get(i['prototype'])
        if t is None:
            if not i['prototype'].startswith(('arbre', 'arbuste', 'souche')):
                ignores[i['prototype']] = ignores.get(i['prototype'], 0) + 1
            continue
        asset, h_nom, h_mod, sxy = t
        h = h_nom * float((i.get('scale') or [1, 1, 1])[2])
        sz = h / h_mod
        z = zsol.get(i['id'])
        z = z if z is not None else i['z']
        yaw = float(i.get('yaw_deg') or 0.0)
        hh = math.radians(yaw) / 2.0
        pts.append({'id': i['id'], 'asset': f'{asset}.{asset.rsplit("/", 1)[-1]}', 'p': [round(i['x'], 3), round(i['y'], 3), round(z, 3)],
                    'q': [0.0, 0.0, round(math.sin(hh), 7), round(math.cos(hh), 7)], 'rpy_deg': [0.0, 0.0, round(yaw, 4)],
                    's': [round(sxy, 4), round(sxy, 4), round(sz, 4)],
                    'graine': int.from_bytes(hashlib.sha256(i['id'].encode()).digest()[:4], 'little') & 0x7FFFFFFF,
                    'x': {'prototype_v1': i['prototype'], 'hauteur_m': round(h, 2), 'statut': i.get('statut')}})
    tete = {'schema': 'pj_points/0.1', 'famille': 'mobilier_substituts',
            'source_hash': hashlib.sha256(open(os.path.join(OBJETS, 'instances.json'), 'rb').read()).hexdigest(),
            'repere': 'local (L93 - O, z = NGF - 216,30), m, Z haut', 'pivot': 'pied du mat (modeles CARLA)',
            'source': 'package/donnees/objets/instances.json ; recon/pcg/ue/contexte/mobilier.py',
            'bibliotheque': 'asset = StaticMesh CARLA /Game/Carla/Static/Pole (CC-BY 4.0), substituts provisoires'}
    os.makedirs(sortie_dir, exist_ok=True)
    lignes = [json.dumps(tete, ensure_ascii=False)[:-1] + ',\n"points": [']
    for k, q in enumerate(pts):
        lignes.append(json.dumps(q, ensure_ascii=False, separators=(',', ':')) + (',' if k < len(pts) - 1 else ''))
    lignes.append(']}')
    chemin = os.path.join(sortie_dir, 'mobilier_ue.json')
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lignes) + '\n')
    from collections import Counter
    return {'sortie': chemin, 'poses': len(pts), 'par_prototype': dict(Counter(q['x']['prototype_v1'] for q in pts)),
            'non_substitues': dict(sorted(ignores.items()))}


if __name__ == '__main__':
    print(json.dumps(principal(*sys.argv[1:2]), ensure_ascii=False, indent=1))
