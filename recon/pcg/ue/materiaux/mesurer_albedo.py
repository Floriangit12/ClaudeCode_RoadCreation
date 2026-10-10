"""[éditeur] Mesure de l'albédo moyen des MI sur les plaques de PJ_Materiaux : capture « base color » du GBuffer
(SceneCapture2D, SCS_BASE_COLOR, orthographique, vue de dessus, cible RGBA32F) de la zone centrale de 1,6 x 1,6 m
de chaque plaque PJM_Plaque_<MI>, exportée en EXR (C.OUT/albedo/<MI>.exr) ; la moyenne est calculée hors éditeur
(materiaux.py mesurer). Contrôle : le sol neutre MI_PJ_Neutre (0,18) donne 0,1816 (quantification du GBuffer).
ARGS : noms (liste de MI, défaut : toutes les plaques), px (128).
"""
import os

import unreal

A = dict(noms=None, px=128, dossier=None)
A.update(globals().get('ARGS') or {})
OUT = A['dossier'] or 'D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/ue_materiaux/albedo'
os.makedirs(OUT, exist_ok=True)
monde = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
streaming = unreal.SystemLibrary.get_console_variable_int_value('r.TextureStreaming')
if streaming:                                                        # toutes les mips (comme pj_tools.capture)
    unreal.SystemLibrary.execute_console_command(monde, 'r.TextureStreaming 0')
try:
    unreal.AutomationLibrary.finish_loading_before_screenshot()      # shaders compilés, chargements finis
except Exception:  # noqa: BLE001
    pass
cap = ACT.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 500), unreal.Rotator(roll=0, pitch=-90, yaw=0))
c = cap.capture_component2d
rt = unreal.RenderingLibrary.create_render_target2d(monde, int(A['px']), int(A['px']), unreal.TextureRenderTargetFormat.RTF_RGBA32F)
for k, v in dict(texture_target=rt, capture_source=unreal.SceneCaptureSource.SCS_BASE_COLOR,
                 projection_type=unreal.CameraProjectionMode.ORTHOGRAPHIC, ortho_width=160.0,
                 capture_every_frame=False, capture_on_movement=False).items():
    c.set_editor_property(k, v)
faits = []
try:
    for a in ACT.get_all_level_actors():
        lab = a.get_actor_label()
        if not lab.startswith('PJM_Plaque_'):
            continue
        nom = lab[len('PJM_Plaque_'):]
        if A['noms'] and nom not in A['noms']:
            continue
        p = a.get_actor_location()
        cap.set_actor_location_and_rotation(unreal.Vector(p.x, p.y, p.z + 300.0), unreal.Rotator(roll=0, pitch=-90, yaw=0), False, False)
        c.capture_scene()
        unreal.RenderingLibrary.export_render_target(monde, rt, OUT, f'{nom}.exr')
        faits.append(nom)
finally:
    ACT.destroy_actor(cap)
    if streaming:
        unreal.SystemLibrary.execute_console_command(monde, f'r.TextureStreaming {streaming}')
RESULT = {'dossier': OUT, 'nb': len(faits), 'plaques': faits}
