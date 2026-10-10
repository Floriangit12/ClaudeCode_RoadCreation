"""[editeur] Positions (m locaux) des instances de PG_Herbe par mesh, pour le controle d'exclusion des bordures
(contexte/controle_herbe.py). ARGS : sortie (JSON), meshes (prefixes retenus). RESULT : comptes."""
import json

import unreal
from pj_tools import repere

A = dict(sortie=None, volume='PJ_PCG_Herbe', meshes=['SM_Grass', 'SM_SmallGrass', 'SM_Bush'])
A.update(globals().get('ARGS') or {})
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
v = next(a for a in ACT.get_all_level_actors() if a.get_actor_label() == A['volume'])
out = {}
for c in v.get_components_by_class(unreal.InstancedStaticMeshComponent):
    sm = c.get_editor_property('static_mesh')
    nom = sm.get_name() if sm else ''
    if not nom.startswith(tuple(A['meshes'])):
        continue
    L = out.setdefault(nom, [])
    for i in range(c.get_instance_count()):
        t = c.get_instance_transform(i, True).translation
        x, y, z = repere.ue_vers_local(t.x, t.y, t.z)
        L.append([round(x, 3), round(y, 3)])
with open(A['sortie'], 'w', encoding='utf-8') as f:
    json.dump(out, f)
RESULT = {k: len(v_) for k, v_ in out.items()}
