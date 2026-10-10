"""Test unitaire des orientations local -> UE (repere.rpy_local_vers_ue / quat_local_vers_ue, charger_points).

Reference : la rotation locale R (rpy ZYX intrinseques ou quaternion, repere direct Z haut) conjuguee par le
miroir Y, M.R.M avec M = diag(1,-1,1), doit donner les axes du rotator UE (X avant, Y droite, Z haut,
exprimes en coordonnees UE). Cas tous non nuls (roulis, tangage et lacet), plus un controle negatif
(roulis de signe oppose = ancienne erreur de charger_points) qui doit echouer.

Hors editeur (partie mathematique, formule FRotationMatrix d'UE recopiee) :
    python recon/pcg/ue/tests/test_rotations.py
Dans l'editeur (pj_tools installe) : MCP pj_tools.run_python_file(path) ; compare en plus aux axes de
unreal.Rotator / unreal.Quat, a charger_points.transform_ue (rpy et q) et aux points d'un PCGPointData
construit par charger_points.point_data. RESULT = {ok, ecart_max, ...}.
"""
from __future__ import annotations

import math
import os
import random
import sys

try:
    import unreal  # noqa: F401
    EDITEUR = True
except ImportError:
    EDITEUR = False
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pj_tools'))

from pj_tools import repere  # noqa: E402

TOL = 1e-6
M = (1.0, -1.0, 1.0)
CAS = [(20.0, 10.0, 30.0), (-35.0, 50.0, 170.0), (5.0, -80.0, -120.0), (12.5, 3.0, 44.2),
       (-0.3, 0.15, 271.0), (88.0, -45.0, 10.0), (-170.0, 25.0, -60.0)]
_alea = random.Random(2154)
CAS += [(_alea.uniform(-180, 180), _alea.uniform(-89, 89), _alea.uniform(-180, 180)) for _ in range(40)]


def conj_miroir(R):
    """M.R.M : la meme rotation exprimee dans le repere UE (Y inverse)."""
    return [[M[i] * R[i][j] * M[j] for j in range(3)] for i in range(3)]


def axes_rotator_ue(roll, pitch, yaw):
    """Axes (X, Y, Z) d'un FRotator en coordonnees UE : formule de FRotationMatrix (Engine/Core, lignes = axes)."""
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    return [(cp * cy, cp * sy, sp),
            (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
            (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)]


def colonnes(R):
    return [tuple(R[i][j] for i in range(3)) for j in range(3)]


def ecart_axes(a, b):
    return max(abs(u - v) for x, y in zip(a, b) for u, v in zip(x, y))


def maths() -> dict:
    """Partie Python pur : rpy et q convertis par repere.py contre M.R.M."""
    pire_rpy = pire_q = pire_qr = 0.0
    neg = []
    for r, p, y in CAS:
        attendu = colonnes(conj_miroir(repere.matrice_rpy(r, p, y)))
        pire_rpy = max(pire_rpy, ecart_axes(axes_rotator_ue(*repere.rpy_local_vers_ue(r, p, y)), attendu))
        q = repere.quat_depuis_rpy(r, p, y)
        pire_qr = max(pire_qr, repere.ecart_rotations_deg(repere.matrice_quat(q), repere.matrice_rpy(r, p, y)))
        pire_q = max(pire_q, ecart_axes(colonnes(repere.matrice_quat(repere.quat_local_vers_ue(q))), attendu))
        neg.append(ecart_axes(axes_rotator_ue(-r, -p, -y), attendu))       # ancienne conversion (roulis -r)
    res = {'nb_cas': len(CAS), 'ecart_rpy_max': pire_rpy, 'ecart_q_max': pire_q, 'q_vs_rpy_deg_max': pire_qr,
           'controle_negatif_roulis_moins_r_min': min(n for n, (r, p, _) in zip(neg, CAS)
                                                      if abs(math.sin(math.radians(r))) > 0.05)}
    res['ok'] = (pire_rpy < TOL and pire_q < TOL and pire_qr < 1e-6
                 and res['controle_negatif_roulis_moins_r_min'] > 1e-2)
    return res


def editeur() -> dict:
    """Dans UE : axes des unreal.Rotator / unreal.Quat, de charger_points.transform_ue et d'un PCGPointData."""
    import unreal
    from pj_tools import charger_points as cp

    def axes_quat(qu):
        return [(a.x, a.y, a.z) for a in (qu.get_axis_x(), qu.get_axis_y(), qu.get_axis_z())]

    def vec(v):
        return (v.x, v.y, v.z)

    pire = {'formule_vs_unreal_rotator': 0.0, 'rotator_rpy': 0.0, 'transform_rpy': 0.0, 'transform_q': 0.0,
            'pcg_rpy': 0.0, 'pcg_q': 0.0}
    neg = 1e9
    pts = []
    for k, (r, p, y) in enumerate(CAS):
        attendu = colonnes(conj_miroir(repere.matrice_rpy(r, p, y)))
        roll, pitch, yaw = repere.rpy_local_vers_ue(r, p, y)
        rot = unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)
        ax = [vec(a) for a in (rot.get_forward_vector(), rot.get_right_vector(), rot.get_up_vector())]
        pire['formule_vs_unreal_rotator'] = max(pire['formule_vs_unreal_rotator'],
                                                ecart_axes(ax, axes_rotator_ue(roll, pitch, yaw)))
        pire['rotator_rpy'] = max(pire['rotator_rpy'], ecart_axes(ax, attendu))
        rneg = unreal.Rotator(roll=-r, pitch=pitch, yaw=yaw)
        if abs(math.sin(math.radians(r))) > 0.05:
            neg = min(neg, ecart_axes([vec(a) for a in (rneg.get_forward_vector(), rneg.get_right_vector(),
                                                         rneg.get_up_vector())], attendu))
        q = repere.quat_depuis_rpy(r, p, y)
        p_rpy = {'id': f'rpy_{k}', 'asset': '/Engine/BasicShapes/Cube.Cube', 'p': [k * 1.5, -2.0, 0.5],
                 'rpy_deg': [r, p, y], 's': [1.0, 1.0, 1.0], 'graine': k}
        p_q = {**p_rpy, 'id': f'q_{k}', 'q': list(q)}
        p_q.pop('rpy_deg')
        for nom, pt in (('transform_rpy', p_rpy), ('transform_q', p_q)):
            t = cp.transform_ue(pt)
            pire[nom] = max(pire[nom], ecart_axes(axes_quat(t.rotation), attendu))
        pts += [p_rpy, p_q]
    # chaine PCG : point_data -> PCGPoint.transform
    doc = {'schema': cp.SCHEMA, 'famille': 'test_rotations', 'points': pts}
    cp.verifier_orientations(doc)
    pd = cp.point_data(doc)
    for pt_pcg, pt in zip(pd.get_points(), pts):
        r, p, y = pt['rpy_deg'] if 'rpy_deg' in pt else CAS[int(pt['id'].split('_')[1])]
        attendu = colonnes(conj_miroir(repere.matrice_rpy(r, p, y)))
        nom = 'pcg_q' if 'q' in pt else 'pcg_rpy'
        pire[nom] = max(pire[nom], ecart_axes(axes_quat(pt_pcg.transform.rotation), attendu))
    # concordance q / rpy : un point incoherent doit etre refuse
    refus = False
    try:
        cp.verifier_orientations({'points': [{'id': 'x', 'q': list(repere.quat_depuis_rpy(20, 10, 30)),
                                              'rpy_deg': [-20, 10, 30]}]})
    except ValueError:
        refus = True
    ok = all(v < 1e-5 for v in pire.values()) and neg > 1e-2 and refus and pd.get_num_points() == len(pts)
    return {'ok': ok, 'ecarts_max': pire, 'controle_negatif_roulis_moins_r_min': neg,
            'incoherence_q_rpy_refusee': refus, 'nb_points_pcg': pd.get_num_points()}


def principal() -> dict:
    res = {'maths': maths()}
    if EDITEUR:
        res['editeur'] = editeur()
    res['ok'] = all(v['ok'] for v in res.values() if isinstance(v, dict))
    return res


RESULT = principal()
if __name__ == '__main__':
    import json
    print(json.dumps(RESULT, indent=1))
    if not EDITEUR and not RESULT['ok']:
        sys.exit(1)
