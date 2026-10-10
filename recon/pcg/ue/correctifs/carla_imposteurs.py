"""[editeur] Correctif CARLA : desactive les LOD « imposteurs » des vegetaux (copie projet /Game/Carla).

Constat (phase 0, essai 5) : dans UE 5.8, le dernier LOD des arbres CARLA (carte de 9 sommets, materiau
derive de /Game/Carla/Static/GenericMaterials/Impostor/M_Impostor) s'affiche comme un bloc arrondi au
lieu d'une silhouette d'arbre (verifie en comparant avec r.ForceLOD 0). Correctif : la taille d'ecran
de ce LOD est mise a 0 (il n'est plus jamais choisi ; le LOD precedent reste affiche a distance).
La geometrie n'est pas modifiee ; D:/CARLA_Assets n'est pas touche (retour arriere : recopier l'asset).

Execution : pj_tools.run_python_file(path, args_json='{"dossier": "/Game/Carla/Static/Vegetation", "appliquer": true}')
"""
import unreal

A = {'dossier': '/Game/Carla/Static/Vegetation', 'appliquer': False, 'max_sommets': 64}
A.update(globals().get('ARGS') or {})

ss = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()
cls = unreal.TopLevelAssetPath('/Script/Engine', 'StaticMesh')
filtre = unreal.ARFilter(package_paths=[A['dossier']], recursive_paths=True, class_paths=[cls])
cibles, ignores = [], 0


def est_imposteur(mi) -> bool:
    m = mi
    while isinstance(m, unreal.MaterialInstance):
        m = m.get_editor_property('parent')
    return m is not None and 'Impostor' in m.get_path_name()


for ad in reg.get_assets(filtre):
    sm = unreal.load_asset(str(ad.package_name))
    if sm is None:
        continue
    n = ss.get_lod_count(sm)
    if n < 2:
        continue
    der = n - 1
    if ss.get_number_verts(sm, der) > A['max_sommets']:
        continue
    slots = sm.get_editor_property('static_materials')
    idx = {int(ss.get_lod_material_slot(sm, der, s)) for s in range(sm.get_num_sections(der))}
    if not idx or not all(0 <= i < len(slots) and est_imposteur(slots[i].get_editor_property('material_interface'))
                          for i in idx):
        ignores += 1
        continue
    tailles = list(ss.get_lod_screen_sizes(sm))
    cibles.append({'mesh': sm.get_path_name(), 'lod': der, 'tailles_avant': [round(t, 4) for t in tailles]})
    if A['appliquer'] and tailles[der] > 0.0:
        tailles[der] = 0.0
        ss.set_lod_screen_sizes(sm, tailles)
        unreal.EditorAssetLibrary.save_loaded_asset(sm, False)

RESULT = {'dossier': A['dossier'], 'applique': A['appliquer'], 'nb_corriges': len(cibles),
          'nb_lod_court_non_imposteur': ignores, 'meshes': cibles}
