"""[editeur] Essai 1 : niveau /Game/PJ/Maps/PJ_Phase0 (sol neutre, ciel, soleil, exposition fixe).

Execute par pj_tools.run_python_file. ARGS : niveau, ev100, soleil_az_geo, soleil_elev, convergence, soleil_lux,
wb_temp, mie_scattering_scale, mie_absorption_scale ; valeurs par defaut : pj_tools/eclairage.py (reference unique).
Idempotent : les acteurs P0_* sont recrees ou mis a jour ; le niveau est enregistre.
"""
import importlib
import math

import unreal
from pj_tools import toolset as T
from pj_tools import repere
from pj_tools import eclairage as E

importlib.reload(E)
A = dict(niveau='/Game/PJ/Maps/PJ_Phase0', ev100=E.EV100, **E.SOLEIL, cote_sol_m=4000.0, wb_temp=E.BALANCE_BLANCS_K,
         **E.CIEL)
A.update(ARGS)  # noqa: F821 (fourni par run_python_file)
journal = {'refus': {}}

EAS = unreal.EditorAssetLibrary
ACT = T._acteurs()

# ---- niveau : creer (vierge, non partitionne) ou charger
if EAS.does_asset_exist(A['niveau']):
    T._preparer_changement_niveau(True)
    T._niveaux().load_level(A['niveau'])
    journal['niveau'] = 'charge'
else:
    T._preparer_changement_niveau(True)
    try:
        ok = T._niveaux().new_level(A['niveau'], False)       # is_partitioned_world=False
    except TypeError:
        ok = T._niveaux().new_level(A['niveau'])
    journal['niveau'] = f'cree ({ok})'


def acteur(label, classe, loc=unreal.Vector(0, 0, 0), rot=unreal.Rotator(0, 0, 0)):
    a = T._trouver_acteur(label)
    if a is not None and not isinstance(a, classe):
        ACT.destroy_actor(a)
        a = None
    if a is None:
        a = ACT.spawn_actor_from_class(classe, loc, rot)
        a.set_actor_label(label)
    a.set_actor_location_and_rotation(loc, rot, False, False)
    return a


# ---- materiau neutre : MI de BasicShapeMaterial (gris 18 %, rugosite 0,85) ; compatible Substrate
MI = '/Game/PJ/Materials/MI_PJ_Neutre'
if not EAS.does_asset_exist(MI):
    f = unreal.MaterialInstanceConstantFactoryNew()
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_PJ_Neutre', '/Game/PJ/Materials',
                                                                 unreal.MaterialInstanceConstant, f)
    mi.set_editor_property('parent', unreal.load_asset('/Engine/BasicShapes/BasicShapeMaterial'))
else:
    mi = unreal.load_asset(MI)
MEL = unreal.MaterialEditingLibrary
MEL.set_material_instance_vector_parameter_value(mi, 'Color', unreal.LinearColor(0.18, 0.18, 0.18, 1.0))
MEL.set_material_instance_scalar_parameter_value(mi, 'Roughness', 0.85)
MEL.update_material_instance(mi)
EAS.save_loaded_asset(mi, False)

# ---- sol : Plane moteur (1 m) mis a l'echelle, dessus a Z = 0
sol = acteur('P0_Sol', unreal.StaticMeshActor)
smc = sol.static_mesh_component
smc.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
smc.set_material(0, mi)
c = A['cote_sol_m']
sol.set_actor_scale3d(unreal.Vector(c, c, 1.0))
smc.set_mobility(unreal.ComponentMobility.STATIC)

# ---- soleil : azimut geographique -> azimut quadrillage L93 (convergence des meridiens)
az_grille = A['soleil_az_geo'] - A['convergence']
yaw_local = (270.0 - az_grille) % 360.0          # cap local du vecteur de propagation (vers l'oppose du soleil)
yaw_ue = repere.yaw_local_vers_ue(yaw_local)
rot_soleil = unreal.Rotator(roll=0.0, pitch=-A['soleil_elev'], yaw=yaw_ue)
sun = acteur('P0_Soleil', unreal.DirectionalLight, unreal.Vector(0, 0, 1000), rot_soleil)
lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
lc.set_mobility(unreal.ComponentMobility.MOVABLE)
journal['refus']['soleil'] = T._set(lc, intensity=float(A['soleil_lux']), light_source_angle=0.5357,
                                    atmosphere_sun_light=True, atmosphere_sun_light_index=0,
                                    cast_shadows=True, use_temperature=False,
                                    light_color=unreal.Color(255, 255, 255, 255))
fwd = rot_soleil.get_forward_vector()
journal['soleil'] = {'az_geo': A['soleil_az_geo'], 'az_grille': round(az_grille, 4), 'elev': A['soleil_elev'],
                     'rot_ue': [rot_soleil.roll, rot_soleil.pitch, rot_soleil.yaw],
                     'propagation_ue': [round(fwd.x, 4), round(fwd.y, 4), round(fwd.z, 4)],
                     'lux': A['soleil_lux']}

# ---- ciel (aerosols de la vallee : eclairage.CIEL), lumiere du ciel (capture temps reel), brouillard
atm = acteur('P0_Atmosphere', unreal.SkyAtmosphere)
ac = atm.get_component_by_class(unreal.SkyAtmosphereComponent)
journal['refus']['atmosphere'] = T._set(ac, mie_scattering_scale=float(A['mie_scattering_scale']),
                                        mie_absorption_scale=float(A['mie_absorption_scale']))
journal['ciel'] = {k: ac.get_editor_property(k) for k in ('mie_scattering_scale', 'mie_absorption_scale',
                                                          'mie_anisotropy', 'rayleigh_scattering_scale')}
sky = acteur('P0_SkyLight', unreal.SkyLight, unreal.Vector(0, 0, 500))
slc = sky.get_component_by_class(unreal.SkyLightComponent)
slc.set_mobility(unreal.ComponentMobility.MOVABLE)
journal['refus']['skylight'] = T._set(slc, real_time_capture=True,
                                      source_type=unreal.SkyLightSourceType.SLS_CAPTURED_SCENE, **E.LUMIERE_CIEL)
fog = acteur('P0_Brouillard', unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
journal['refus']['brouillard'] = T._set(fc, fog_density=0.005, fog_height_falloff=0.2,
                                        enable_volumetric_fog=False)

# ---- post-process global : exposition manuelle fixe (bias = -EV100, sans camera physique), sans vignettage ni grain
ppv = acteur('P0_PostProcess', unreal.PostProcessVolume)
ppv.set_editor_property('unbound', True)
pp = ppv.get_editor_property('settings')
journal['refus']['postprocess'] = T._set(
    pp, override_auto_exposure_method=True, auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
    override_auto_exposure_bias=True, auto_exposure_bias=-float(A['ev100']),
    override_auto_exposure_apply_physical_camera_exposure=True, auto_exposure_apply_physical_camera_exposure=False,
    override_white_temp=True, white_temp=float(A['wb_temp']), **E.POST_PROCESS_NEUTRE)
ppv.set_editor_property('settings', pp)
journal['exposition'] = {'ev100': float(A['ev100']), 'balance_blancs_k': float(A['wb_temp']), **E.POST_PROCESS_NEUTRE}

# ---- verification des reglages projet (Lumen)
SL = unreal.SystemLibrary
journal['cvars'] = {k: SL.get_console_variable_int_value(k) for k in (
    'r.DynamicGlobalIlluminationMethod', 'r.ReflectionMethod', 'r.Shadow.Virtual.Enable',
    'r.Lumen.HardwareRayTracing', 'r.Substrate')}

T._niveaux().save_current_level()
journal['acteurs'] = sorted(a.get_actor_label() for a in ACT.get_all_level_actors())
journal['monde'] = T._monde().get_path_name()
RESULT = journal
