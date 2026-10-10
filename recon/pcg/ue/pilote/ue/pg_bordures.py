"""[editeur] Graphe PCG /Game/PJ/PCG/PG_Bordures et pose des bordures du pilote dans le niveau courant.

Load PCG Data Asset (PDA_Bordures, cuit par pj_tools.charger_points depuis ue_pilote/points/bordures_ue.json)
-> Static Mesh Spawner : PCGMeshSelectorByAttribute 'Mesh' (bibliotheque /Game/PJ/Lib/Bordures), surcharge du materiau
par l'attribut 'Materiau' (beton gris / clair, caniveau, mortiers), PCGInstanceDataPackerByAttribute cd0..cd6
(M_PJ_Bordure : PerInstanceCustomData 0-6 = usure, salissure, mousse_joints, herbe_joints, teinte, z_pied_cm,
demi_longueur_cm)
-> Output. Volume PJ_PCG_Bordures (dossier PJ_PCG) couvrant la zone pilote ; generation locale synchrone. Collision des
ISM : profil BlockAll dans le descripteur du spawner (ARGS collision ; maillages en collision complexe, collisions.py).

ARGS : etape = 'generer' | 'verifier' ; points (JSON pj_points, pour 'verifier') ; n_controle (10) ; graine (2154).
'verifier' : nombre d'instances = nombre de points ; n_controle instances tirees au hasard comparees au JSON
(position <= 1 mm, orientation <= 0,05 deg, echelle, mesh, materiau, donnees d'instance).
"""
import json
import math
import random

import unreal
from pj_tools import repere

A = dict(etape='generer', pda='/Game/PJ/PCG/Donnees/PDA_Bordures', graphe='/Game/PJ/PCG/PG_Bordures',
         volume='PJ_PCG_Bordures', n_cd=7, points=None, n_controle=10, graine=2154, collision='BlockAll',
         zone=[-11.0, -28.0, 60.0, 72.0])
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def collision_ism(sel, profil='BlockAll'):
    """Profil de collision des ISM generes, dans le descripteur du Static Mesh Spawner (revue UE du 10/10 : ISM du PCG
    en NoCollision, rayons des capteurs sans impact)."""
    td = sel.get_editor_property('template_descriptor')
    bi = td.get_editor_property('body_instance')
    actif = 'NoCollision' if profil == 'NoCollision' else 'QueryAndPhysics'
    if not bi.import_text(f'(CollisionProfileName="{profil}",CollisionEnabled={actif},ObjectType=ECC_WorldStatic)'):
        raise RuntimeError(f'profil de collision {profil} refuse')
    td.set_editor_property('body_instance', bi)
    sel.set_editor_property('template_descriptor', td)
    return str(sel.get_editor_property('template_descriptor').get_editor_property('body_instance').get_editor_property(
        'collision_profile_name'))


def volume():
    for a in ACT.get_all_level_actors():
        if a.get_actor_label() == A['volume']:
            return a
    return None


def graphe():
    if EAL.does_asset_exist(A['graphe']):
        g = unreal.load_asset(A['graphe'])
        for n in list(g.get_editor_property('nodes')):          # rejouable : graphe vide puis reconstruit
            g.remove_node(n)
    else:
        d, n = A['graphe'].rsplit('/', 1)
        g = unreal.AssetToolsHelpers.get_asset_tools().create_asset(n, d, unreal.PCGGraph, unreal.PCGGraphFactory())
    n_ld, s_ld = g.add_node_of_type(unreal.PCGLoadDataAssetSettings)
    s_ld.set_editor_property('asset', unreal.load_asset(A['pda']))
    s_ld.set_editor_property('synchronous_load', True)
    n_sp, s_sp = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
    s_sp.set_editor_property('mesh_selector_type', unreal.PCGMeshSelectorByAttribute)
    sel = s_sp.get_editor_property('mesh_selector_parameters')
    sel.set_editor_property('attribute_name', 'Mesh')
    sel.set_editor_property('use_attribute_material_overrides', True)
    sel.set_editor_property('material_override_attributes', ['Materiau'])
    collision_ism(sel, A['collision'])
    s_sp.set_editor_property('synchronous_load', True)
    s_sp.set_editor_property('instance_data_packer_type', unreal.PCGInstanceDataPackerByAttribute)
    pk = s_sp.get_editor_property('instance_data_packer_parameters')
    sels = []
    for i in range(int(A['n_cd'])):
        s = unreal.PCGAttributePropertyInputSelector()      # pas d'accesseur Python : format texte du selecteur
        if not s.import_text(f'PCGBegin(cd{i})PCGEnd'):
            raise RuntimeError(f'selecteur cd{i} refuse')
        sels.append(s)
    pk.set_editor_property('attribute_selectors', sels)
    n_ld.set_node_position(0, 0)
    n_sp.set_node_position(400, 0)
    sortie_ld = n_ld.get_editor_property('output_pins')[0].get_editor_property('properties').get_editor_property('label')
    g.add_edge(n_ld, sortie_ld, n_sp, 'In')
    g.add_edge(n_sp, 'Out', g.get_output_node(), 'Out')
    try:
        g.set_editor_property('description', "Bordures du pilote : points pj_points (PDA_Bordures) -> Static Mesh Spawner "
                                             "(Mesh, Materiau, cd0..cd6) ; recon/pcg/ue/pilote/ue/pg_bordures.py")
    except Exception:  # noqa: BLE001
        pass
    EAL.save_loaded_asset(g, False)
    return g


def ism_du_volume(v):
    return [c for c in v.get_components_by_class(unreal.InstancedStaticMeshComponent)] if v else []


if A['etape'] == 'generer':
    g = graphe()
    x0, y0, x1, y1 = A['zone']
    cx, cy, cz = repere.local_vers_ue(0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.0)
    v = volume()
    if v is None:
        v = ACT.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(cx, cy, cz), unreal.Rotator(0, 0, 0))
        v.set_actor_label(A['volume'])
    v.set_folder_path('PJ_PCG')
    v.set_actor_location(unreal.Vector(cx, cy, cz), False, False)
    v.set_actor_scale3d(unreal.Vector((x1 - x0) / 2.0 + 2.0, (y1 - y0) / 2.0 + 2.0, 10.0))   # brosse de 200 uu
    comp = v.get_component_by_class(unreal.PCGComponent)
    comp.cleanup_local(True)
    comp.set_graph(g)
    comp.generate_local(True)
    isms = ism_du_volume(v)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    RESULT = {'graphe': g.get_path_name(), 'volume': v.get_path_name(), 'ism': len(isms),
              'instances': sum(c.get_instance_count() for c in isms)}
else:
    doc = json.load(open(A['points'], encoding='utf-8'))
    pts = doc['points']
    v = volume()
    isms = ism_du_volume(v)
    # index des instances : position UE arrondie au 1/100 mm -> (composant, i)
    inst = []
    for c in isms:
        k = c.get_editor_property('num_custom_data_floats')
        cd = list(c.get_editor_property('per_instance_sm_custom_data'))
        sm = c.get_editor_property('static_mesh')
        mat = c.get_material(0)
        for i in range(c.get_instance_count()):
            t = c.get_instance_transform(i, True)
            inst.append({'t': t, 'mesh': sm.get_path_name() if sm else None, 'mat': mat.get_path_name() if mat else None,
                         'cd': cd[i * k:(i + 1) * k], 'comp': c.get_name()})
    rnd = random.Random(A['graine'])
    echantillon = rnd.sample(range(len(pts)), min(int(A['n_controle']), len(pts)))
    controles = []
    for j in echantillon:
        p = pts[j]
        X, Y, Z = repere.local_vers_ue(*p['p'])
        best = min(inst, key=lambda e: (e['t'].translation.x - X) ** 2 + (e['t'].translation.y - Y) ** 2 +
                   (e['t'].translation.z - Z) ** 2)
        t = best['t']
        d_mm = 10.0 * math.sqrt((t.translation.x - X) ** 2 + (t.translation.y - Y) ** 2 + (t.translation.z - Z) ** 2)
        # orientation : rotation de l'instance (UE) ramenee au repere local, R_local = M.R_ue.M (M = diag(1,-1,1),
        # repere.py), comparee a la matrice du quaternion q du JSON (independamment de charger_points)
        q_ue = t.rotation
        ax = [q_ue.get_axis_x(), q_ue.get_axis_y(), q_ue.get_axis_z()]  # colonnes de R_ue
        R_ue = [[(ax[c].x, ax[c].y, ax[c].z)[r] for c in range(3)] for r in range(3)]
        M = (1.0, -1.0, 1.0)
        Mi = [[M[r] * R_ue[r][c] * M[c] for c in range(3)] for r in range(3)]
        Mj = repere.matrice_quat(p['q']) if 'q' in p else repere.matrice_rpy(*p['rpy_deg'])
        ang = repere.ecart_rotations_deg(Mj, Mi)
        sc = t.scale3d
        s = p.get('s', [1, 1, 1])
        controles.append({'id': p['id'], 'ecart_mm': round(d_mm, 4), 'ecart_deg': round(ang, 5),
                          'echelle_ecart': round(max(abs(sc.x - s[0]), abs(sc.y - s[1]), abs(sc.z - s[2])), 6),
                          'mesh_ok': best['mesh'] is not None and best['mesh'].split('.')[0] == p['asset'].split('.')[0],
                          'materiau_ok': best['mat'] is not None and best['mat'].split('.')[0] == p['materiau'].split('.')[0],
                          'cd_json': p.get('cd'), 'cd_ism': [round(x, 3) for x in best['cd']]})
    RESULT = {'points': len(pts), 'instances': len(inst), 'ism': len(isms),
              'egalite': len(inst) == len(pts), 'controles': controles,
              'max_mm': max(c['ecart_mm'] for c in controles), 'max_deg': max(c['ecart_deg'] for c in controles),
              'tous_ok': all(c['ecart_mm'] <= 1.0 and c['ecart_deg'] <= 0.05 and c['mesh_ok'] and c['materiau_ok']
                             for c in controles)}
