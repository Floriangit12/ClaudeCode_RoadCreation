"""[editeur] Graphe PCG /Game/PJ/PCG/PG_Herbe : herbe, massifs et feuilles mortes d'octobre sur les zones fabriquees par
contexte/preparer_usd.py (maillages /Game/PJ/Import/Zones/zones_pcg/StaticMeshes/SM_<zone>, non poses ; densite = couleur
de sommet R : 0 a moins de 0,15 m d'une surface dure ou d'une bordure v1 / v2, rampe jusqu'a 0,35 m ; feuilles :
degressif depuis le tronc des feuillus, plus rare sur la chaussee).

Par zone : Mesh Sampler (Poisson, rayon r, densite = R du sommet, modele source) -> [Attribute Noise : densite x alea]
-> Density Filter (seuil) -> Transform Points (lacet aleatoire, echelle uniforme [s0, s1], inclinaison) ->
Static Mesh Spawner (selecteur pondere : StaticMesh CARLA, distances de disparition, ombres) -> Output.
Volume PJ_PCG_Herbe (dossier PJ_PCG) sur tout le site ; generation locale synchrone.
Revue UE du 10/10 : seuil de densite des zones d'herbe releve a 0,6 (touffes a moins de 0,15 m des bordures, frange sur
les limites) ; herbe CARLA sur des MI du projet (MI_PJ_Herbe_*, variation de teinte de M_FoliageMaster ramenee de 15-25
a 6 ; SM_Grass_01 couleur paille -> vert gris : plaques d'herbe seche quasi blanches) ; feuilles 3D CARLA (atlas de dechets, « confettis jaunes ») raréfiees
(seuil 0,75, plus petites) : les feuilles mortes viennent surtout des decalques (feuilles.py).
ARGS : etape 'generer' | 'verifier'. RESULT : instances par maillage.
"""
import unreal

A = dict(etape='generer', graphe='/Game/PJ/PCG/PG_Herbe', volume='PJ_PCG_Herbe', zone=[-150.0, -150.0, 150.0, 150.0],
         zones='/Game/PJ/Import/Zones/zones_pcg/StaticMeshes')
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
G = '/Game/Carla/Static/Vegetation/Grass'
B = '/Game/Carla/Static/Vegetation/Bushes'
L = '/Game/Carla/Static/Vegetation/Leaves'

# zone -> reglages : rayon Poisson (cm), seuil de densite, bruit (densite x alea), echelle, inclinaison max (deg),
# entrees (asset, poids, ombre ; les meshes a ombre - buissons - ne recoivent pas les decalques de feuilles),
# distances de disparition (cm)
ZONES = {
    'herbe_tondu': dict(rayon=19.0, seuil=0.6, bruit=False, echelle=(0.5, 0.85), incl=5.0, cull=(3500, 5000),
                        entrees=[(f'{G}/SM_Grass_01', 3, False), (f'{G}/SM_SmallGrassv2', 2, False)]),
    'herbe_tondu_loin': dict(rayon=30.0, seuil=0.6, bruit=False, echelle=(0.5, 0.8), incl=4.0, cull=(3000, 4500),
                             entrees=[(f'{G}/SM_Grass_01', 3, False), (f'{G}/SM_SmallGrassv2', 2, False)]),
    'herbe_haute': dict(rayon=20.0, seuil=0.6, bruit=False, echelle=(1.4, 2.4), incl=8.0, cull=(4000, 6000),
                        entrees=[(f'{G}/SM_Grass_01', 3, False), (f'{G}/SM_SmallGrassv2', 2, False)]),
    'massifs': dict(rayon=55.0, seuil=0.5, bruit=False, echelle=(0.55, 0.95), incl=3.0, cull=(0, 0),
                    entrees=[(f'{B}/SM_Bush_M_v1', 3, True), (f'{B}/SM_Bush_M_v2', 2, True), (f'{B}/SM_Bush_M_v4', 2, True),
                             (f'{B}/SM_Bush_M_v3', 1, True), (f'{B}/SM_Bush_M_v5', 1, True)]),
    'feuilles': dict(rayon=30.0, seuil=0.75, bruit=True, echelle=(0.8, 1.3), incl=12.0, cull=(2500, 4000),
                     entrees=[(f'{L}/SM_Leaf03_v{i}', 1, False) for i in range(1, 7)] +
                             [(f'{L}/SM_Leaf04_v{i}', 1, False) for i in range(1, 7)] +
                             [(f'{L}/SM_Leaf05_v{i}', 1, False) for i in range(1, 7)]),
}


# herbe CARLA : MI du projet (enfants des MI CARLA, copie projet) ; parametres de M_FoliageMaster (SM_Grass_01 : touffes
# couleur paille a Hue 0,8 / Brightness 0,8, ramenees a un vert gris d'octobre, verifie en gros plan)
MI_HERBE = {'SM_Grass_01': ('/Game/Carla/Static/Vegetation/Grass/Materials/MI_Grass01', '/Game/PJ/Materials/MI_PJ_Herbe_Grass01',
                            {'Color Variation': 6.0, 'Saturation': 0.5, 'Brightness': 0.4, 'Hue': 0.92}),
            'SM_SmallGrassv2': ('/Game/Carla/Static/Vegetation/Grass/MI_Grass01__v1', '/Game/PJ/Materials/MI_PJ_Herbe_SmallGrass',
                                {'Color Variation': 6.0, 'Saturation': 0.45, 'Brightness': 0.5})}


def mi_herbe():
    MEL = unreal.MaterialEditingLibrary
    out = {}
    for sm, (parent, chemin, sc) in MI_HERBE.items():
        d, n = chemin.rsplit('/', 1)
        m = unreal.load_asset(chemin) if EAL.does_asset_exist(chemin) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        m.set_editor_property('parent', unreal.load_asset(parent))
        MEL.clear_all_material_instance_parameters(m)
        for k, v in sc.items():
            MEL.set_material_instance_scalar_parameter_value(m, k, float(v))
        MEL.update_material_instance(m)
        EAL.save_loaded_asset(m, False)
        out[sm] = chemin
    return out


def selecteur(txt):
    s = unreal.PCGAttributePropertyInputSelector()
    if not s.import_text(f'PCGBegin({txt})PCGEnd'):
        raise RuntimeError(f'selecteur {txt} refuse')
    return s


def entree(chemin, poids, ombre, cull):
    e = unreal.PCGMeshSelectorWeightedEntry()
    nom = chemin.rsplit('/', 1)[-1]
    mi = MI_HERBE.get(nom)
    surcharge = f'OverrideMaterials=("{mi[1]}.{mi[1].rsplit("/", 1)[-1]}"),' if mi else ''
    txt = (f'(Descriptor=(StaticMesh="{chemin}.{nom}",{surcharge}InstanceStartCullDistance={int(cull[0])},'
           f'InstanceEndCullDistance={int(cull[1])},bCastShadow={ombre},bCastDynamicShadow={ombre},'
           f'bCastContactShadow={ombre},bReceivesDecals={not ombre}),Weight={int(poids)})')
    if not e.import_text(txt):
        raise RuntimeError(f'entree {txt} refusee')
    return e


def graphe():
    if EAL.does_asset_exist(A['graphe']):
        g = unreal.load_asset(A['graphe'])
        for n in list(g.get_editor_property('nodes')):
            g.remove_node(n)
    else:
        d, n = A['graphe'].rsplit('/', 1)
        g = unreal.AssetToolsHelpers.get_asset_tools().create_asset(n, d, unreal.PCGGraph, unreal.PCGGraphFactory())
    for i, (zone, z) in enumerate(ZONES.items()):
        y = 320 * i
        n_ms, s_ms = g.add_node_of_type(unreal.PCGMeshSamplerSettings)
        s_ms.set_editor_property('static_mesh', unreal.load_asset(f"{A['zones']}/SM_{zone}"))
        s_ms.set_editor_property('sampling_method', unreal.PCGMeshSamplingMethod.POISSON_SAMPLING)
        so = s_ms.get_editor_property('sampling_options')
        so.set_editor_property('sampling_radius', float(z['rayon']))
        so.set_editor_property('random_seed', 2154 + i)
        s_ms.set_editor_property('sampling_options', so)
        s_ms.set_editor_property('use_color_channel_as_density', True)
        s_ms.set_editor_property('color_channel_as_density', unreal.PCGColorChannel.RED)
        s_ms.set_editor_property('requested_lod_type', unreal.GeometryScriptLODType.SOURCE_MODEL)
        s_ms.set_editor_property('synchronous_load', True)
        prev, sortie = n_ms, 'Out'
        n_ms.set_node_position(0, y)
        if z['bruit']:
            n_bn, s_bn = g.add_node_of_type(unreal.PCGAttributeNoiseSettings)
            s_bn.set_editor_property('mode', unreal.PCGAttributeNoiseMode.MULTIPLY)
            s_bn.set_editor_property('input_source', selecteur('$Density'))
            s_bn.set_editor_property('noise_min', 0.0)
            s_bn.set_editor_property('noise_max', 1.0)
            n_bn.set_node_position(250, y)
            g.add_edge(prev, sortie, n_bn, 'In')
            prev = n_bn
        n_df, s_df = g.add_node_of_type(unreal.PCGDensityFilterSettings)
        s_df.set_editor_property('lower_bound', float(z['seuil']))
        s_df.set_editor_property('upper_bound', 1.0)
        n_df.set_node_position(500, y)
        g.add_edge(prev, sortie, n_df, 'In')
        n_tp, s_tp = g.add_node_of_type(unreal.PCGTransformPointsSettings)
        s_tp.set_editor_property('rotation_min', unreal.Rotator(roll=-z['incl'], pitch=-z['incl'], yaw=0.0))
        s_tp.set_editor_property('rotation_max', unreal.Rotator(roll=z['incl'], pitch=z['incl'], yaw=360.0))
        s_tp.set_editor_property('absolute_rotation', True)
        s_tp.set_editor_property('scale_min', unreal.Vector(z['echelle'][0], z['echelle'][0], z['echelle'][0]))
        s_tp.set_editor_property('scale_max', unreal.Vector(z['echelle'][1], z['echelle'][1], z['echelle'][1]))
        s_tp.set_editor_property('uniform_scale', True)
        s_tp.set_editor_property('absolute_scale', True)
        n_tp.set_node_position(750, y)
        g.add_edge(n_df, 'Out', n_tp, 'In')
        n_sp, s_sp = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
        s_sp.set_editor_property('mesh_selector_type', unreal.PCGMeshSelectorWeighted)
        sel = s_sp.get_editor_property('mesh_selector_parameters')
        sel.set_editor_property('mesh_entries', [entree(c, p, o, z['cull']) for c, p, o in z['entrees']])
        s_sp.set_editor_property('synchronous_load', True)
        n_sp.set_node_position(1000, y)
        g.add_edge(n_tp, 'Out', n_sp, 'In')
        g.add_edge(n_sp, 'Out', g.get_output_node(), 'Out')
    try:
        g.set_editor_property('description', 'Herbe (gazon ras, herbe haute), massifs, feuilles mortes : zones de '
                                             'preparer_usd.py, densite = couleur de sommet ; contexte/ue/pg_herbe.py')
    except Exception:  # noqa: BLE001
        pass
    EAL.save_loaded_asset(g, False)
    return g


def volume():
    for a in ACT.get_all_level_actors():
        if a.get_actor_label() == A['volume']:
            return a
    return None


def bilan(v):
    par = {}
    for c in (v.get_components_by_class(unreal.InstancedStaticMeshComponent) if v else []):
        sm = c.get_editor_property('static_mesh')
        par[sm.get_name() if sm else None] = par.get(sm.get_name() if sm else None, 0) + c.get_instance_count()
    return par


if A['etape'] == 'generer':
    import time
    t0 = time.time()
    mi_herbe()
    g = graphe()
    v = volume()
    if v is None:
        v = ACT.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        v.set_actor_label(A['volume'])
    v.set_folder_path('PJ_PCG')
    x0, y0, x1, y1 = A['zone']
    v.set_actor_location(unreal.Vector(50.0 * (x0 + x1), -50.0 * (y0 + y1), 0.0), False, False)
    v.set_actor_scale3d(unreal.Vector((x1 - x0) / 2.0 + 2.0, (y1 - y0) / 2.0 + 2.0, 40.0))
    comp = v.get_component_by_class(unreal.PCGComponent)
    comp.cleanup_local(True)
    comp.set_graph(g)
    comp.generate_local(True)
    p = bilan(v)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    RESULT = {'graphe': g.get_path_name(), 'volume': v.get_path_name(), 'instances': sum(p.values()), 'par_mesh': p,
              'duree_s': round(time.time() - t0, 1), 'zones': {k: {kk: vv for kk, vv in z.items() if kk != 'entrees'}
                                                               for k, z in ZONES.items()}}
else:
    p = bilan(volume())
    RESULT = {'instances': sum(p.values()), 'par_mesh': p}
