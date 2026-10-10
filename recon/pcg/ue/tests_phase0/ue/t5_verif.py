"""[editeur] Essai 5 : instances produites par un volume PCG comparees au JSON pj_points.

ARGS : volume (chemin d'objet de l'acteur), json, echantillon=[ids]. Apparie chaque point au plus proche
instance (meme mesh) et mesure les ecarts de position (cm), de lacet (deg), d'orientation complete (deg,
angle entre quaternions) et d'echelle.
"""
import math

import unreal
from pj_tools import charger_points as cp

A = ARGS  # noqa: F821
vol = unreal.find_object(None, A['volume'])
if vol is None:
    raise RuntimeError(f'volume introuvable : {A["volume"]}')
inst = []
comps = vol.get_components_by_class(unreal.InstancedStaticMeshComponent)
for c in comps:
    sm = c.static_mesh.get_path_name() if c.static_mesh else None
    for i in range(c.get_instance_count()):
        t = c.get_instance_transform(i, True)
        if isinstance(t, tuple):
            t = t[-1]
        L, R, S, Q = t.translation, t.rotation.rotator(), t.scale3d, t.rotation
        inst.append({'mesh': sm, 'loc': (L.x, L.y, L.z), 'yaw': R.yaw, 'pitch': R.pitch, 'roll': R.roll,
                     'q': (Q.x, Q.y, Q.z, Q.w), 'scale': (S.x, S.y, S.z), 'comp': c.get_name()})

doc = cp.lire(A['json'])
libres = list(range(len(inst)))
ecarts = []
for q in doc['points']:
    t = cp.transform_ue(q)
    L = t.translation
    best, bd = None, 1e18
    for k in libres:
        d = math.dist(inst[k]['loc'], (L.x, L.y, L.z))
        if d < bd:
            best, bd = k, d
    if best is None:
        ecarts.append({'id': q['id'], 'manquant': True})
        continue
    libres.remove(best)
    e = inst[best]
    dyaw = (e['yaw'] - t.rotation.rotator().yaw + 180.0) % 360.0 - 180.0
    qa = t.rotation
    sg = 1.0 if sum(u * v for u, v in zip(e['q'], (qa.x, qa.y, qa.z, qa.w))) >= 0.0 else -1.0
    dif = math.sqrt(sum((u - sg * v) ** 2 for u, v in zip(e['q'], (qa.x, qa.y, qa.z, qa.w))))
    som = math.sqrt(sum((u + sg * v) ** 2 for u, v in zip(e['q'], (qa.x, qa.y, qa.z, qa.w))))
    drot = math.degrees(4.0 * math.atan2(dif, som))       # angle entre quaternions, precis aux petits angles
    ecarts.append({'id': q['id'], 'attendu_cm': [L.x, L.y, L.z], 'instance_cm': list(e['loc']),
                   'd_pos_cm': bd, 'attendu_yaw_ue': t.rotation.rotator().yaw, 'instance_yaw_ue': e['yaw'],
                   'd_yaw_deg': dyaw, 'd_rot_deg': drot, 'attendu_s': list(q['s']), 'instance_s': list(e['scale']),
                   'd_s': max(abs(a - b) for a, b in zip(e['scale'], q['s'])),
                   'mesh_ok': (e['mesh'] or '').split('.')[0] == q['asset'].split('.')[0]})
ok = [x for x in ecarts if not x.get('manquant')]
RESULT = {
    'nb_instances': len(inst), 'nb_points': len(doc['points']), 'nb_composants': len(comps),
    'composants': sorted({(c.get_name(), c.get_class().get_name(), c.static_mesh.get_name() if c.static_mesh else None,
                           c.get_instance_count()) for c in comps}),
    'manquants': sum(1 for x in ecarts if x.get('manquant')), 'instances_en_trop': len(libres),
    'd_pos_max_cm': max((x['d_pos_cm'] for x in ok), default=None),
    'd_yaw_max_deg': max((abs(x['d_yaw_deg']) for x in ok), default=None),
    'd_rot_max_deg': max((x['d_rot_deg'] for x in ok), default=None),
    'd_s_max': max((x['d_s'] for x in ok), default=None),
    'mesh_faux': sum(1 for x in ok if not x['mesh_ok']),
    'echantillon': [x for x in ecarts if x['id'] in A.get('echantillon', [])],
}
