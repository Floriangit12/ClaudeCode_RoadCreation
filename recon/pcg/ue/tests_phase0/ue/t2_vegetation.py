"""[editeur] Essai 2 : vegetation CARLA sous Lumen dans PJ_Phase0.

Pose une rangee (pas de 8 m le long de +x local, y = 0) et un petit massif d'herbe,
puis inventorie les materiaux de chaque mesh (parent, domaine, mode de melange, MPC references,
materiau par defaut ou manquant). ARGS : rangee=[[label, asset, x], ...], herbe={asset, x0, n, pas}.
"""
import unreal
from pj_tools import toolset as T

A = ARGS  # noqa: F821
ACT = T._acteurs()
res = {'acteurs': [], 'meshes': {}}

if T._monde().get_path_name().split('.')[0] != A['niveau']:
    T._preparer_changement_niveau(True)
    T._niveaux().load_level(A['niveau'])

# nettoyage des poses precedentes de cet essai
for a in ACT.get_all_level_actors():
    if a.get_actor_label().startswith('P0_Veg_'):
        ACT.destroy_actor(a)


def poser(label, asset, x, y, yaw=0.0, s=1.0):
    r = T.pj_tools.spawn_static_mesh(asset, x, y, 0.0, yaw, label, s)
    import json
    r = json.loads(r)
    if not r.get('ok'):
        raise RuntimeError(r)
    a = T._trouver_acteur(label)
    o, e = a.get_actor_bounds(False)
    res['acteurs'].append({'label': label, 'asset': asset, 'x': x, 'y': y,
                           'ue_cm': r['ue_cm'], 'h_m': round((o.z + e.z) / 100.0, 2),
                           'larg_m': round(2 * max(e.x, e.y) / 100.0, 2)})
    return a


def parents(mi):
    ch = []
    m = mi
    while isinstance(m, unreal.MaterialInstance):
        ch.append(m.get_path_name())
        m = m.get_editor_property('parent')
    if m is not None:
        ch.append(m.get_path_name())
    return ch, m


def inventaire(asset_path):
    sm = unreal.load_asset(asset_path)
    info = {'lods': sm.get_num_lods(), 'nanite': None, 'materiaux': []}
    try:
        info['nanite'] = bool(sm.get_editor_property('nanite_settings').get_editor_property('enabled'))
    except Exception:  # noqa: BLE001
        pass
    for i, sl in enumerate(sm.get_editor_property('static_materials')):
        mi = sl.get_editor_property('material_interface')
        d = {'slot': str(sl.get_editor_property('material_slot_name'))}
        if mi is None:
            d['probleme'] = 'materiau absent'
        else:
            ch, base = parents(mi)
            d['chaine'] = ch
            if base is not None:
                d['blend'] = str(base.get_editor_property('blend_mode'))
                d['two_sided'] = bool(base.get_editor_property('two_sided'))
                d['shading'] = str(base.get_editor_property('shading_model'))
                deps = unreal.AssetRegistryHelpers.get_asset_registry().get_dependencies(
                    base.get_outermost().get_name(), unreal.AssetRegistryDependencyOptions())
                d['deps_base'] = sorted(str(x) for x in (deps or []) if not str(x).startswith('/Script'))
            if 'WorldGridMaterial' in ' '.join(ch) or 'DefaultMaterial' in ' '.join(ch):
                d['probleme'] = 'materiau par defaut'
        info['materiaux'].append(d)
    return info


for label, asset, x in A['rangee']:
    poser(label, asset, x, 0.0)
    res['meshes'][asset] = inventaire(asset)

h = A['herbe']
k = 0
for i in range(h['n']):
    for j in range(h['n']):
        k += 1
        poser(f'P0_Veg_Herbe_{k:02d}', h['asset'], h['x0'] + i * h['pas'], (j - (h['n'] - 1) / 2) * h['pas'],
              yaw=37.0 * k)
res['meshes'][h['asset']] = inventaire(h['asset'])

# MPC presentes
res['mpc'] = {p: unreal.EditorAssetLibrary.does_asset_exist(p) for p in (
    '/Game/Carla/Blueprints/Game/CarlaParameters', '/Game/Carla/Blueprints/Weather/Materials/WeatherMaterialParameters', '/Game/Carla/Static/GenericMaterials/WetPavement/WeatherMaterialParameters',
    '/Game/Carla/Static/Vegetation/VegetationParamCollection')}
T._niveaux().save_current_level()
RESULT = res
