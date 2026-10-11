"""Niveau ouvert dans l'éditeur UE (exécuté dans Unreal par pj_tools.run_python_file)."""
import unreal

_m = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
RESULT = {"niveau": _m.get_path_name() if _m else None}
