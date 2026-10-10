"""[editeur] Niveau /Game/PJ/Maps/PJ_2026 (non World Partition) : eclairage de reference, exposition fixe,
GeoReferencingSystem EPSG:2154 a l'origine O, sol de contexte autour de la zone pilote, nuages (eclairage.NUAGES).

Execute par pj_tools.run_python_file. ARGS (defauts : pj_tools/eclairage.py, reference unique) : niveau, ev100,
soleil_az_geo, soleil_elev, convergence, soleil_lux, wb_temp, mie_scattering_scale, mie_absorption_scale,
contexte_z_m (dessus du sol de contexte, m locaux), contexte_cote_m, contexte_mi.
Idempotent : les acteurs PJ_* sont recrees ou mis a jour ; le niveau est enregistre.
Memes reglages que tests_phase0/ue/t1_niveau.py (PJ_Phase0, PJ_Materiaux), etiquettes PJ_ au lieu de P0_.
"""
import importlib

import unreal
from pj_tools import toolset as T
from pj_tools import repere
from pj_tools import eclairage as E

importlib.reload(E)
A = dict(niveau='/Game/PJ/Maps/PJ_2026', ev100=E.EV100, **E.SOLEIL, wb_temp=E.BALANCE_BLANCS_K, **E.CIEL,
         contexte_z_m=-1.6, contexte_cote_m=3000.0, contexte_mi='/Game/PJ/Materials/MI_PJ_Contexte')
A.update(ARGS)  # noqa: F821 (fourni par run_python_file)
journal = {'refus': {}}
EAS = unreal.EditorAssetLibrary
ACT = T._acteurs()

# ---- niveau : creer (vierge, non partitionne) ou charger
if T._monde().get_path_name().split('.')[0] != A['niveau']:
    T._preparer_changement_niveau(True)
    if EAS.does_asset_exist(A['niveau']):
        T._niveaux().load_level(A['niveau'])
        journal['niveau'] = 'charge'
    else:
        try:
            ok = T._niveaux().new_level(A['niveau'], False)        # is_partitioned_world=False
        except TypeError:
            ok = T._niveaux().new_level(A['niveau'])
        journal['niveau'] = f'cree ({ok})'
else:
    journal['niveau'] = 'deja ouvert'


def acteur(label, classe, loc=unreal.Vector(0, 0, 0), rot=unreal.Rotator(0, 0, 0), dossier='PJ_Eclairage'):
    a = T._trouver_acteur(label)
    if a is not None and not isinstance(a, classe):
        ACT.destroy_actor(a)
        a = None
    if a is None:
        a = ACT.spawn_actor_from_class(classe, loc, rot)
        a.set_actor_label(label)
    a.set_actor_location_and_rotation(loc, rot, False, False)
    a.set_folder_path(dossier)
    return a


# ---- soleil : azimut geographique -> azimut quadrillage L93 (convergence des meridiens)
az_grille = A['soleil_az_geo'] - A['convergence']
yaw_local = (270.0 - az_grille) % 360.0          # cap local du vecteur de propagation (oppose du soleil)
rot_soleil = unreal.Rotator(roll=0.0, pitch=-A['soleil_elev'], yaw=repere.yaw_local_vers_ue(yaw_local))
sun = acteur('PJ_Soleil', unreal.DirectionalLight, unreal.Vector(0, 0, 1000), rot_soleil)
lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
lc.set_mobility(unreal.ComponentMobility.MOVABLE)
journal['refus']['soleil'] = T._set(lc, intensity=float(A['soleil_lux']), light_source_angle=0.5357,
                                    atmosphere_sun_light=True, atmosphere_sun_light_index=0,
                                    cast_shadows=True, use_temperature=False,
                                    light_color=unreal.Color(255, 255, 255, 255))
fwd = rot_soleil.get_forward_vector()
journal['soleil'] = {'az_geo': A['soleil_az_geo'], 'az_grille': round(az_grille, 4), 'elev': A['soleil_elev'],
                     'rot_ue': [rot_soleil.roll, rot_soleil.pitch, rot_soleil.yaw],
                     'propagation_ue': [round(fwd.x, 4), round(fwd.y, 4), round(fwd.z, 4)], 'lux': A['soleil_lux']}

# ---- ciel (aerosols de la vallee), lumiere du ciel (capture temps reel), brouillard
atm = acteur('PJ_Atmosphere', unreal.SkyAtmosphere)
ac = atm.get_component_by_class(unreal.SkyAtmosphereComponent)
journal['refus']['atmosphere'] = T._set(ac, mie_scattering_scale=float(A['mie_scattering_scale']),
                                        mie_absorption_scale=float(A['mie_absorption_scale']))
sky = acteur('PJ_SkyLight', unreal.SkyLight, unreal.Vector(0, 0, 500))
slc = sky.get_component_by_class(unreal.SkyLightComponent)
slc.set_mobility(unreal.ComponentMobility.MOVABLE)
journal['refus']['skylight'] = T._set(slc, real_time_capture=True,
                                      source_type=unreal.SkyLightSourceType.SLS_CAPTURED_SCENE, **E.LUMIERE_CIEL)
# ---- nuages (eclairage.NUAGES) : MI enfant du nuage simple du moteur, couverture et vent fixes
NU = E.NUAGES
mat = NU['materiau']
EAS_ = unreal.EditorAssetLibrary
mi_n = unreal.load_asset(mat) if EAS_.does_asset_exist(mat) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    mat.rsplit('/', 1)[1], mat.rsplit('/', 1)[0], unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
mi_n.set_editor_property('parent', unreal.load_asset(NU['parent']))
MEL_ = unreal.MaterialEditingLibrary
MEL_.clear_all_material_instance_parameters(mi_n)
# couverture : Cloud_GlobalCoverage du nuage simple (eclairage.NUAGES) ; vent nul
MEL_.set_material_instance_scalar_parameter_value(mi_n, 'Cloud_GlobalCoverage', float(NU['couverture']))
MEL_.set_material_instance_scalar_parameter_value(mi_n, 'Cloud_GlobalDensity', float(NU['densite']))
MEL_.set_material_instance_vector_parameter_value(mi_n, 'Layout_WindControls', unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
MEL_.update_material_instance(mi_n)
EAS_.save_loaded_asset(mi_n, False)
nua = acteur('PJ_Nuages', unreal.VolumetricCloud)
vc = nua.get_component_by_class(unreal.VolumetricCloudComponent)
vc.set_layer_bottom_altitude(float(NU['bas_km']))
vc.set_layer_height(float(NU['epaisseur_km']))
vc.set_material(mi_n)
journal['nuages'] = {k: NU[k] for k in ('bas_km', 'epaisseur_km', 'couverture', 'densite')}
fog = acteur('PJ_Brouillard', unreal.ExponentialHeightFog)
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
journal['refus']['brouillard'] = T._set(fc, fog_density=0.005, fog_height_falloff=0.2, enable_volumetric_fog=False)

# ---- post-process global : exposition manuelle fixe (biais = -EV100), balance 5500 K, post-process neutre
ppv = acteur('PJ_PostProcess', unreal.PostProcessVolume)
ppv.set_editor_property('unbound', True)
pp = ppv.get_editor_property('settings')
journal['refus']['postprocess'] = T._set(
    pp, override_auto_exposure_method=True, auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
    override_auto_exposure_bias=True, auto_exposure_bias=-float(A['ev100']),
    override_auto_exposure_apply_physical_camera_exposure=True, auto_exposure_apply_physical_camera_exposure=False,
    override_white_temp=True, white_temp=float(A['wb_temp']), **E.POST_PROCESS_NEUTRE)
ppv.set_editor_property('settings', pp)
journal['exposition'] = {'ev100': float(A['ev100']), 'balance_blancs_k': float(A['wb_temp'])}

# ---- GeoReferencingSystem : planete plate, EPSG:2154, origine O (PROJ embarque, hors ligne)
geo = acteur('PJ_GeoReferencing', unreal.GeoReferencingSystem, dossier='PJ_Repere')
E0, N0, H0 = repere.O_L93
journal['refus']['georef'] = T._set(geo, planet_shape=unreal.PlanetShape.FLAT_PLANET, projected_crs='EPSG:2154',
                                    geographic_crs='EPSG:4326', origin_at_planet_center=False,
                                    origin_location_in_projected_crs=True,
                                    origin_projected_coordinates_easting=E0, origin_projected_coordinates_northing=N0,
                                    origin_projected_coordinates_up=H0)
try:
    geo.apply_settings()
    g0 = geo.k2_projected_to_geographic(geo.k2_engine_to_projected(unreal.Vector(0, 0, 0)))
    p1 = geo.k2_engine_to_projected(unreal.Vector(1000.0, -2000.0, 300.0))   # local (10, 20, 3)
    journal['georef'] = {'origine_wgs84': [g0.latitude, g0.longitude, g0.altitude],
                         'controle_local_10_20_3': [p1.x - E0, p1.y - N0, p1.z - H0]}
except Exception as e:  # noqa: BLE001
    journal['georef'] = repr(e)

# ---- sol de contexte : plan de 3 km sous la zone pilote (dessus a contexte_z_m), gazon en UV monde
mi = None
if EAS.does_asset_exist(A['contexte_mi']):
    mi = unreal.load_asset(A['contexte_mi'])
ctx = acteur('PJ_Sol_Contexte', unreal.StaticMeshActor, unreal.Vector(0, 0, A['contexte_z_m'] * 100.0),
             dossier='PJ_Contexte')
smc = ctx.static_mesh_component
smc.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
if mi is not None:
    smc.set_material(0, mi)
c = float(A['contexte_cote_m'])
ctx.set_actor_scale3d(unreal.Vector(c, c, 1.0))
smc.set_mobility(unreal.ComponentMobility.STATIC)
journal['contexte'] = {'z_m': A['contexte_z_m'], 'cote_m': c, 'mi': mi.get_path_name() if mi else None}

SL = unreal.SystemLibrary
for k, v in E.CVARS.items():                                  # session courante (DefaultEngine.ini au demarrage)
    SL.execute_console_command(T._monde(), f'{k} {v}')
journal['cvars_projet'] = {k: SL.get_console_variable_int_value(k) for k in E.CVARS}
journal['cvars'] = {k: SL.get_console_variable_int_value(k) for k in (
    'r.DynamicGlobalIlluminationMethod', 'r.ReflectionMethod', 'r.Shadow.Virtual.Enable',
    'r.Lumen.HardwareRayTracing', 'r.Substrate', 'r.Nanite.Tessellation')}
T._niveaux().save_current_level()
journal['monde'] = T._monde().get_path_name()
try:
    journal['world_partition'] = T._monde().get_world_partition() is not None
except Exception as e:  # noqa: BLE001
    journal['world_partition'] = repr(e)
RESULT = journal
