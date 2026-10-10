"""Points des bordures pour UE (Python pur) : fabrique/points/bordures.json (pj_points/0.1, Houdini) ->
ue_pilote/points/bordures_ue.json (pj_points/0.1, assets UE resolus), relu par pj_tools.charger_points.

- asset : nom de prototype -> /Game/PJ/Lib/Bordures/SM_<nom>.SM_<nom> (bibliotheque_bordures.py) ;
- materiau (UE, attribut PCG 'Materiau' -> surcharge du Static Mesh Spawner) : x.materiau beton_gris ->
  MI_beton_bordure_gris, beton_clair -> MI_beton_bordure_clair, caniveau_beton -> MI_caniveau_beton ; joints :
  x.mortier sombre -> MI_mortier_joint, clair -> MI_mortier_clair ;
- cd : [usure, salissure, mousse_joints, herbe_joints, teinte] + cd5 = z_pied x 100 (cm : fil d'eau dans le repere
  de l'element, pivot des prototypes sous le bloc ; M_PJ_Bordure -> BasDecalageCm par instance) + cd6 = demi-longueur
  du prototype (cm, prototypes/index.json dims_m[0] / 2 ; M_PJ_Bordure : distance aux abouts) ; joints : [] ;
- p, q, rpy_deg, s, graine, id : inchanges (q prioritaire dans charger_points, rpy_deg controle a 0,05 deg).
Usage : python points_ue.py [FABRIQUE] [SORTIE]
"""
from __future__ import annotations

import json
import os
import sys

DEPOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
FABRIQUE = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'v2', 'fabrique_ue_snapshot')
SORTIE = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'v2', 'ue_pilote', 'points', 'bordures_ue.json')
LIB = '/Game/PJ/Lib/Bordures'
MAT = '/Game/PJ/Materials'
MATERIAU = {'beton_gris': 'beton_bordure_gris', 'beton_clair': 'beton_bordure_clair', 'caniveau_beton': 'caniveau_beton'}
MORTIER = {'sombre': 'mortier_joint', 'clair': 'mortier_clair'}


def mi(mid: str) -> str:
    return f'{MAT}/MI_{mid}.MI_{mid}'


def convertir(doc: dict, index: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != 'points'}
    out['famille'] = 'bordures_ue'
    out['source'] = 'fabrique/points/bordures.json (pj_bordure_pose.py) ; recon/pcg/ue/pilote/points_ue.py'
    out['bibliotheque'] = f'asset = {LIB}/SM_<prototype> (pilote/ue/bibliotheque_bordures.py)'
    out['cd'] = ('éléments et caniveaux : [usure, salissure, mousse_joints, herbe_joints, teinte, z_pied_cm, '
                 'demi_longueur_cm] (M_PJ_Bordure : PerInstanceCustomData 0-6) ; joints : []')
    pts = []
    for p in doc['points']:
        x = p.get('x') or {}
        q = dict(p)
        q['asset'] = f'{LIB}/SM_{p["asset"]}.SM_{p["asset"]}'
        if x.get('type') == 'joint':
            q['materiau'] = mi(MORTIER[x.get('mortier', 'sombre')])
        else:
            q['materiau'] = mi(MATERIAU[x['materiau']])
            q['cd'] = list(p.get('cd') or []) + [round(100.0 * float(x['z_pied']), 2),
                                                 round(50.0 * float(index[p['asset']]['dims_m'][0]), 2)]
        pts.append(q)
    out['points'] = pts
    return out


def ecrire(doc: dict, chemin: str):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tete = {k: v for k, v in doc.items() if k != 'points'}
    lignes = [json.dumps(tete, ensure_ascii=False)[:-1] + ',\n"points": [']
    for i, p in enumerate(doc['points']):
        lignes.append(json.dumps(p, ensure_ascii=False, separators=(',', ':')) + (',' if i < len(doc['points']) - 1 else ''))
    lignes.append(']}')
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lignes) + '\n')


def principal(fabrique: str = FABRIQUE, sortie: str = SORTIE) -> dict:
    with open(os.path.join(fabrique, 'points', 'bordures.json'), encoding='utf-8') as f:
        doc = json.load(f)
    with open(os.path.join(fabrique, 'prototypes', 'index.json'), encoding='utf-8') as f:
        index = json.load(f)['prototypes']
    out = convertir(doc, index)
    ecrire(out, sortie)
    from collections import Counter
    return {'sortie': sortie, 'points': len(out['points']), 'avec_q': sum('q' in p for p in out['points']),
            'materiaux': dict(Counter(p['materiau'].rsplit('.', 1)[-1] for p in out['points'])),
            'assets': len({p['asset'] for p in out['points']})}


if __name__ == '__main__':
    print(json.dumps(principal(*sys.argv[1:3]), ensure_ascii=False, indent=1))
