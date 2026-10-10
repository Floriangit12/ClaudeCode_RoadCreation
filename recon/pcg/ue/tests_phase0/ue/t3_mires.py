"""[editeur] Essai 3 : mires de georeferencement + acteur GeoReferencingSystem (EPSG:2154, origine O).

ARGS : niveau, mires=[[nom, x, y, z], ...] (m, repere local). Pose un cube de 0,30 m (centre au point),
une croix plate de 2 m et un texte ; relit les transforms ; regle GeoReferencingSystem (hors ligne :
PROJ embarque dans le plugin) et convertit chaque mire moteur -> L93 -> WGS84.
"""
import unreal
from pj_tools import toolset as T
from pj_tools import repere

A = ARGS  # noqa: F821
ACT = T._acteurs()
EAS = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
res = {'mires': [], 'georef': {}}

if T._monde().get_path_name().split('.')[0] != A['niveau']:
    T._preparer_changement_niveau(True)
    T._niveaux().load_level(A['niveau'])

for a in ACT.get_all_level_actors():
    if a.get_actor_label().startswith('P0_Mire_') or a.get_actor_label() == 'P0_GeoReferencing':
        ACT.destroy_actor(a)

# materiau rouge (MI de BasicShapeMaterial)
MI = '/Game/PJ/Materials/MI_PJ_Mire'
if not EAS.does_asset_exist(MI):
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'MI_PJ_Mire', '/Game/PJ/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', unreal.load_asset('/Engine/BasicShapes/BasicShapeMaterial'))
else:
    mi = unreal.load_asset(MI)
MEL.set_material_instance_vector_parameter_value(mi, 'Color', unreal.LinearColor(0.8, 0.02, 0.02, 1.0))
MEL.update_material_instance(mi)
EAS.save_loaded_asset(mi, False)

CUBE = unreal.load_asset('/Engine/BasicShapes/Cube')


def boite(label, loc, echelle, yaw=0.0):
    a = ACT.spawn_actor_from_object(CUBE, loc, unreal.Rotator(0, 0, yaw))
    a.set_actor_label(label)
    a.set_actor_scale3d(echelle)
    a.static_mesh_component.set_material(0, mi)
    return a


for nom, x, y, z in A['mires']:
    X, Y, Z = repere.local_vers_ue(x, y, z)
    cube = boite(f'P0_Mire_{nom}', unreal.Vector(X, Y, Z), unreal.Vector(0.3, 0.3, 0.3))
    # croix plate 2 m x 0,10 m posee au sol (repere visuel pour les captures)
    for k, yaw in enumerate((0.0, 90.0)):
        boite(f'P0_Mire_{nom}_croix{k}', unreal.Vector(X, Y, 1.0), unreal.Vector(2.0, 0.10, 0.02), yaw)
    txt = ACT.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(X + 60, Y, 2.0),
                                     unreal.Rotator(roll=0.0, pitch=90.0, yaw=0.0))
    txt.set_actor_label(f'P0_Mire_{nom}_texte')
    tc = txt.text_render
    T._set(tc, text=nom, world_size=80.0, text_render_color=unreal.Color(20, 20, 20, 255),
           horizontal_alignment=unreal.HorizTextAligment.EHTA_LEFT)
    L = cube.get_actor_location()
    xl, yl, zl = repere.ue_vers_local(L.x, L.y, L.z)
    res['mires'].append({'nom': nom, 'local_m': [x, y, z], 'attendu_ue_cm': [X, Y, Z],
                         'lu_ue_cm': [L.x, L.y, L.z],
                         'ecart_cm': [L.x - X, L.y - Y, L.z - Z],
                         'retour_local_m': [xl, yl, zl],
                         'l93': list(repere.local_vers_l93(xl, yl, zl)),
                         'acteur': cube.get_path_name()})

# ---- GeoReferencingSystem : planete plate, CRS projete EPSG:2154, origine O
geo = ACT.spawn_actor_from_class(unreal.GeoReferencingSystem, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
geo.set_actor_label('P0_GeoReferencing')
E0, N0, H0 = repere.O_L93
props = dict(planet_shape=unreal.PlanetShape.FLAT_PLANET, projected_crs='EPSG:2154', geographic_crs='EPSG:4326',
             origin_at_planet_center=False, origin_location_in_projected_crs=True,
             origin_projected_coordinates_easting=E0, origin_projected_coordinates_northing=N0,
             origin_projected_coordinates_up=H0)
res['georef']['refus'] = T._set(geo, **props)
try:
    geo.apply_settings()
    res['georef']['apply_settings'] = True
except Exception as e:  # noqa: BLE001
    res['georef']['apply_settings'] = repr(e)
res['georef']['proprietes'] = {k: str(geo.get_editor_property(k)) for k in props}


def _vec(v):
    try:
        return [v.x, v.y, v.z]
    except AttributeError:
        return str(v)


conv = []
for m in res['mires']:
    L = unreal.Vector(*m['lu_ue_cm'])
    d = {'nom': m['nom']}
    try:
        p = geo.k2_engine_to_projected(L)
        d['projete'] = _vec(p)
        d['ecart_vs_repere_cm'] = [round((a - b) * 100.0, 4) for a, b in zip(d['projete'], m['l93'])]
        g = geo.k2_projected_to_geographic(p)
        d['wgs84'] = [g.latitude, g.longitude, g.altitude]
    except Exception as e:  # noqa: BLE001
        d['erreur'] = repr(e)
    conv.append(d)
res['georef']['conversions'] = conv
# origine du niveau
try:
    g0 = geo.k2_projected_to_geographic(geo.k2_engine_to_projected(unreal.Vector(0, 0, 0)))
    res['georef']['origine_wgs84'] = [g0.latitude, g0.longitude, g0.altitude]
except Exception as e:  # noqa: BLE001
    res['georef']['origine_wgs84'] = repr(e)

T._niveaux().save_current_level()
RESULT = res
