"""[éditeur] Essai de la chaîne d'instance des bordures : points pj_points/0.1 avec cd -> PCGDataAsset
(pj_tools.charger_points, attributs cd0..cd4) -> graphe /Game/PJ/PCG/Essais/PG_Essai_Bordures_cd
(Load PCG Data Asset -> Static Mesh Spawner : MeshSelectorByAttribute 'Mesh', PCGInstanceDataPackerByAttribute
cd0..cd4) -> ISM dont les PerInstanceCustomData 0..4 alimentent M_PJ_Bordure
(cd = [usure, salissure, mousse_joints, herbe_joints, teinte], bordures_elements.json aspect.donnees_instance).

ARGS : etape = 'generer' (graphe + volume PJM_PCG_Bordures_cd + génération) | 'verifier' (lecture des ISM).
"""
import unreal

A = dict(etape='generer', pda='/Game/PJ/PCG/Donnees/PDA_Essai_Bordures_cd', graphe='/Game/PJ/PCG/Essais/PG_Essai_Bordures_cd',
         volume='PJM_PCG_Bordures_cd', centre_cm=[300.0, -1100.0, 0.0], n_cd=5)
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def volume():
    for a in ACT.get_all_level_actors():
        if a.get_actor_label() == A['volume']:
            return a
    return None


def graphe():
    if EAL.does_asset_exist(A['graphe']):
        g = unreal.load_asset(A['graphe'])
        for n in list(g.get_editor_property('nodes')):          # rejouable : graphe vidé puis reconstruit
            g.remove_node(n)
    else:
        d, n = A['graphe'].rsplit('/', 1)
        g = unreal.AssetToolsHelpers.get_asset_tools().create_asset(n, d, unreal.PCGGraph, unreal.PCGGraphFactory())
    n_ld, s_ld = g.add_node_of_type(unreal.PCGLoadDataAssetSettings)
    s_ld.set_editor_property('asset', unreal.load_asset(A['pda']))
    s_ld.set_editor_property('synchronous_load', True)
    n_sp, s_sp = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
    s_sp.set_editor_property('mesh_selector_type', unreal.PCGMeshSelectorByAttribute)
    s_sp.get_editor_property('mesh_selector_parameters').set_editor_property('attribute_name', 'Mesh')
    s_sp.set_editor_property('instance_data_packer_type', unreal.PCGInstanceDataPackerByAttribute)
    pk = s_sp.get_editor_property('instance_data_packer_parameters')
    sels = []
    for i in range(int(A['n_cd'])):
        s = unreal.PCGAttributePropertyInputSelector()      # pas d'accesseur Python : format texte du sélecteur
        if not s.import_text(f'PCGBegin(cd{i})PCGEnd'):
            raise RuntimeError(f'sélecteur cd{i} refusé')
        sels.append(s)
    pk.set_editor_property('attribute_selectors', sels)
    n_ld.set_node_position(0, 0)
    n_sp.set_node_position(400, 0)
    sortie_ld = n_ld.get_editor_property('output_pins')[0].get_editor_property('properties').get_editor_property('label')
    g.add_edge(n_ld, sortie_ld, n_sp, 'In')
    g.add_edge(n_sp, 'Out', g.get_output_node(), 'Out')
    EAL.save_loaded_asset(g, False)
    return g, pk


if A['etape'] == 'generer':
    g, pk = graphe()
    v = volume()
    if v is None:
        v = ACT.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(*A['centre_cm']), unreal.Rotator(0, 0, 0))
        v.set_actor_label(A['volume'])
        v.set_folder_path('PJM')
    v.set_actor_scale3d(unreal.Vector(8.0, 3.0, 2.0))
    comp = v.get_component_by_class(unreal.PCGComponent)
    comp.cleanup_local(True)
    comp.set_graph(g)
    comp.generate_local(True)
    RESULT = {'graphe': g.get_path_name(), 'selecteurs': [str(unreal.PCGAttributePropertySelectorBlueprintHelpers.get_name(s))
                                                         for s in pk.get_editor_property('attribute_selectors')]}
else:
    v = volume()
    out = []
    for c in (v.get_components_by_class(unreal.InstancedStaticMeshComponent) if v else []):
        n = c.get_instance_count()
        k = c.get_editor_property('num_custom_data_floats')
        cd = list(c.get_editor_property('per_instance_sm_custom_data'))
        inst = []
        for i in range(n):
            t = c.get_instance_transform(i, True)
            inst.append({'x_cm': round(t.translation.x, 2), 'y_cm': round(t.translation.y, 2),
                         'cd': [round(x, 3) for x in cd[i * k:(i + 1) * k]]})
        out.append({'composant': c.get_name(), 'mesh': c.static_mesh.get_path_name() if c.static_mesh else None,
                    'materiau': c.get_material(0).get_path_name() if c.get_material(0) else None,
                    'instances': n, 'cd_par_instance': k, 'detail': inst})
    RESULT = {'ism': out}
