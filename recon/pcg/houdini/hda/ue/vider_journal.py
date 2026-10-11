"""FlushLog du journal de l'éditeur UE (exécuté dans Unreal par pj_tools.run_python_file)."""
import unreal

unreal.SystemLibrary.execute_console_command(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
                                             "FlushLog")
RESULT = "ok"
