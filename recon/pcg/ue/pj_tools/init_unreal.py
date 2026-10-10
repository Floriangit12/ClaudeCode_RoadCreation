"""Demarrage Python du projet ClaudeADAS : enregistre le toolset MCP 'pj_tools'.

Installe dans D:/ClaudeADAS/Content/Python/ par recon/pcg/ue/pj_tools/installer.py (ne pas editer la copie).
"""
import unreal

try:
    from toolset_registry.registration import Registration
    from pj_tools import toolset as _pj_toolset

    _pj_registration = Registration([_pj_toolset.pj_tools])
    if _pj_registration.register():
        unreal.log('pj_tools: toolset enregistre')
    else:
        unreal.log_warning('pj_tools: ToolsetRegistry indisponible (commandlet ?) - non enregistre')
except Exception as _e:  # noqa: BLE001
    unreal.log_warning(f'pj_tools: enregistrement impossible : {_e}')
