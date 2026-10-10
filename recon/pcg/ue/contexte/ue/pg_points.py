"""[editeur] Graphe PCG generique « points pj_points -> instances » et pose dans le niveau courant (PG_Arbres,
PG_Clotures...) : une branche par PCGDataAsset (cuit par pj_tools.charger_points) :
Load PCG Data Asset -> Static Mesh Spawner (PCGMeshSelectorByAttribute 'Mesh' ; surcharge du materiau par l'attribut
'Materiau' si la branche le demande) -> Output. Volume <volume> (dossier PJ_PCG) couvrant la zone ; generation locale.

ARGS : etape 'generer' | 'verifier' ; graphe ; volume ; zone [x0, y0, x1, y1] (m locaux) ;
branches [{pda, materiau (bool)}] ; points [json] (verifier) ; n_controle (10) ; graine (2154) ; description ;
collision (profil des ISM generes, BlockAll par defaut : arbres, tuteurs, clotures, mobilier ; revue UE du 10/10).
'verifier' : instances = points (par branche) ; n_controle points tires au hasard par fichier compares a l'instance la
plus proche (position <= 1 mm, orientation <= 0,05 deg via M.R.M contre q, echelle, mesh). sans_ombre : les ISM du volume ne
projettent pas d'ombre (fixe a la verification, la generation etant asynchrone).
"""
import json
import random

import unreal
from pj_tools import repere

A = dict(etape='generer', graphe=None, volume=None, zone=[-150.0, -150.0, 150.0, 150.0], branches=[], points=[],
         n_controle=10, graine=2154, description='', sans_ombre=False, collision='BlockAll')
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def volume():
    for a in ACT.get_all_level_actors():
        if a.get_actor_label() == A['volume']:
            return a
    return None


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


def graphe():
    if EAL.does_asset_exist(A['graphe']):
        g = unreal.load_asset(A['graphe'])
        for n in list(g.get_editor_property('nodes')):
            g.remove_node(n)
    else:
        d, n = A['graphe'].rsplit('/', 1)
        g = unreal.AssetToolsHelpers.get_asset_tools().create_asset(n, d, unreal.PCGGraph, unreal.PCGGraphFactory())
    for i, b in enumerate(A['branches']):
        n_ld, s_ld = g.add_node_of_type(unreal.PCGLoadDataAssetSettings)
        s_ld.set_editor_property('asset', unreal.load_asset(b['pda']))
        s_ld.set_editor_property('synchronous_load', True)
        n_sp, s_sp = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
        s_sp.set_editor_property('mesh_selector_type', unreal.PCGMeshSelectorByAttribute)
        sel = s_sp.get_editor_property('mesh_selector_parameters')
        sel.set_editor_property('attribute_name', 'Mesh')
        collision_ism(sel, A['collision'])
        if b.get('materiau'):
            sel.set_editor_property('use_attribute_material_overrides', True)
            sel.set_editor_property('material_override_attributes', ['Materiau'])
        s_sp.set_editor_property('synchronous_load', True)
        n_ld.set_node_position(0, 300 * i)
        n_sp.set_node_position(400, 300 * i)
        lab = n_ld.get_editor_property('output_pins')[0].get_editor_property('properties').get_editor_property('label')
        g.add_edge(n_ld, lab, n_sp, 'In')
        g.add_edge(n_sp, 'Out', g.get_output_node(), 'Out')
    try:
        g.set_editor_property('description', A['description'])
    except Exception:  # noqa: BLE001
        pass
    EAL.save_loaded_asset(g, False)
    return g


def isms(v):
    return list(v.get_components_by_class(unreal.InstancedStaticMeshComponent)) if v else []


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
    v.set_actor_scale3d(unreal.Vector((x1 - x0) / 2.0 + 2.0, (y1 - y0) / 2.0 + 2.0, 40.0))
    comp = v.get_component_by_class(unreal.PCGComponent)
    comp.cleanup_local(True)
    comp.set_graph(g)
    comp.generate_local(True)
    c = isms(v)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    RESULT = {'graphe': g.get_path_name(), 'volume': v.get_path_name(), 'ism': len(c),
              'instances': sum(x.get_instance_count() for x in c)}
else:
    v = volume()
    inst = []
    if A['sans_ombre']:                     # apres generation (asynchrone) : ISM du volume sans ombre portee
        for c in isms(v):
            c.set_editor_property('cast_shadow', False)
    for c in isms(v):
        sm = c.get_editor_property('static_mesh')
        for i in range(c.get_instance_count()):
            inst.append({'t': c.get_instance_transform(i, True), 'mesh': sm.get_path_name() if sm else None})
    rnd = random.Random(A['graine'])
    n_pts, controles = 0, []
    for chemin in A['points']:
        pts = json.load(open(chemin, encoding='utf-8'))['points']
        n_pts += len(pts)
        for j in rnd.sample(range(len(pts)), min(int(A['n_controle']), len(pts))):
            p = pts[j]
            X, Y, Z = repere.local_vers_ue(*p['p'])
            best = min(inst, key=lambda e: (e['t'].translation.x - X) ** 2 + (e['t'].translation.y - Y) ** 2 +
                       (e['t'].translation.z - Z) ** 2)
            t = best['t']
            d_mm = 10.0 * ((t.translation.x - X) ** 2 + (t.translation.y - Y) ** 2 + (t.translation.z - Z) ** 2) ** 0.5
            q = t.rotation
            ax = [q.get_axis_x(), q.get_axis_y(), q.get_axis_z()]
            R_ue = [[(ax[c].x, ax[c].y, ax[c].z)[r] for c in range(3)] for r in range(3)]
            M = (1.0, -1.0, 1.0)
            Mi = [[M[r] * R_ue[r][c] * M[c] for c in range(3)] for r in range(3)]
            ang = repere.ecart_rotations_deg(repere.matrice_quat(p['q']), Mi)
            sc, s = t.scale3d, p['s']
            controles.append({'id': p['id'], 'ecart_mm': round(d_mm, 3), 'ecart_deg': round(ang, 4),
                              'echelle_ecart': round(max(abs(sc.x - s[0]), abs(sc.y - s[1]), abs(sc.z - s[2])), 6),
                              'mesh_ok': best['mesh'] is not None and best['mesh'].split('.')[0] == p['asset'].split('.')[0]})
    RESULT = {'points': n_pts, 'instances': len(inst), 'egalite': n_pts == len(inst), 'controles': controles,
              'max_mm': max((c['ecart_mm'] for c in controles), default=None),
              'max_deg': max((c['ecart_deg'] for c in controles), default=None),
              'tous_ok': all(c['ecart_mm'] <= 1.0 and c['ecart_deg'] <= 0.05 and c['mesh_ok'] and c['echelle_ecart'] < 1e-4
                             for c in controles)}
