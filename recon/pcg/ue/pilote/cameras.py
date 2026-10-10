"""Cameras de controle du pilote (recon/pc/houdini/cameras_v2_pilote.usda, pj_rendu.py) -> parametres de
pj_tools.high_res_capture (Python pur : lecture du .usda texte, sans pxr).

Camera USD : matrice xformOp:transform (lignes = axes X droite, Y haut, Z arriere, puis translation), repere local
(m, Z haut), visee = -Z ; focale et ouverture en dixiemes d'unite (0,36 = 36 mm). Conversion :
- position locale = translation (high_res_capture la convertit : X = 100x, Y = -100y, Z = 100z, repere.py) ;
- cap local = atan2(vy, vx) de la visee, site = asin(vz) (high_res_capture : yaw_UE = -cap, repere.yaw_local_vers_ue) ;
- roulis = angle de l'axe X camera avec l'horizontale (doit etre nul : high_res_capture n'a pas de roulis) ;
- champ horizontal = 2 atan(ouverture_h / (2 focale)).
"""
from __future__ import annotations

import math
import os
import re

DEPOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
CAMERAS = os.path.join(DEPOT, 'recon', 'pc', 'houdini', 'cameras_v2_pilote.usda')
# noms courts des captures UE (consigne : ue_a..ue_f) -> camera USD
VUES = {'a': 'a_pieton_file_joints', 'b': 'b_abaisse_traversee_bev', 'c': 'c_entree_charretiere',
        'd': 'd_ilot_brf', 'e': 'e_ilot_gravier', 'f': 'f_vue_ensemble'}


def lire(chemin: str = CAMERAS) -> dict:
    """{nom: {matrice (4x4 lignes), focale, ouverture_h, ouverture_v}} des Camera du fichier."""
    txt = open(chemin, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'def Camera "(\w+)"(.*?)\n        \}', txt, re.S):
        corps = m.group(2)

        def f(nom):
            r = re.search(rf'float {nom} = ([-\d.e]+)', corps)
            return float(r.group(1)) if r else None
        mat = re.search(r'matrix4d xformOp:transform = \((.*?)\)\s*\n', corps, re.S).group(1)
        nums = [float(x) for x in re.findall(r'[-\d.]+(?:e[-+]?\d+)?', mat)]
        out[m.group(1)] = {'matrice': [nums[i:i + 4] for i in range(0, 16, 4)], 'focale': f('focalLength'),
                           'ouverture_h': f('horizontalAperture'), 'ouverture_v': f('verticalAperture')}
    return out


def pose_capture(cam: dict) -> dict:
    """Parametres de high_res_capture (m locaux, degres) d'une camera USD."""
    M = cam['matrice']
    x, z = M[0][:3], M[2][:3]
    v = [-z[0], -z[1], -z[2]]
    n = math.sqrt(sum(c * c for c in v))
    v = [c / n for c in v]
    cap = math.degrees(math.atan2(v[1], v[0]))
    site = math.degrees(math.asin(max(-1.0, min(1.0, v[2]))))
    roulis = math.degrees(math.asin(max(-1.0, min(1.0, x[2] / math.sqrt(sum(c * c for c in x))))))
    hfov = math.degrees(2.0 * math.atan(cam['ouverture_h'] / (2.0 * cam['focale'])))
    return {'cam_x_m': M[3][0], 'cam_y_m': M[3][1], 'cam_z_m': M[3][2], 'yaw_deg': cap, 'pitch_deg': site,
            'fov_deg': hfov, 'roulis_deg': roulis}


def pose_joint(points: dict, jid: str, recul_m: float = 0.75, decalage_m: float = 0.30, h_m: float = 0.55,
               fov_deg: float = 40.0) -> dict:
    """Gros plan d'un joint de bordure (points/bordures.json) : camera cote chaussee (-u), en biais de decalage_m le
    long de la bordure, a h_m au-dessus du dessous du bloc, visant le milieu de la face vue au droit du joint."""
    j = next(q for q in points['points'] if q['id'] == jid)
    x, y, z = j['p']
    a = math.radians(j['rpy_deg'][2])
    ex, ey = math.cos(a), math.sin(a)                  # +s le long de la bordure
    nx, ny = -ey, ex                                    # +u (arriere, cote haut) ; la chaussee est en -u
    cam = (x + decalage_m * ex - recul_m * nx, y + decalage_m * ey - recul_m * ny, z + h_m)
    cible = (x, y, z + 0.18)
    d = [cible[i] - cam[i] for i in range(3)]
    return {'cam_x_m': cam[0], 'cam_y_m': cam[1], 'cam_z_m': cam[2], 'yaw_deg': math.degrees(math.atan2(d[1], d[0])),
            'pitch_deg': math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))), 'fov_deg': fov_deg, 'roulis_deg': 0.0,
            'joint': jid}


def poses() -> dict:
    cams = lire()
    return {k: dict(pose_capture(cams[n]), camera=n) for k, n in VUES.items()}


if __name__ == '__main__':
    import json
    print(json.dumps(poses(), indent=1))
