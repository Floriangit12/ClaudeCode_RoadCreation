"""[editeur] Catalogue mesure des vegetaux CARLA du projet (/Game/Carla/Static/Vegetation/{Trees,Bushes,Grass,Leaves}) :
bornes (m, repere de l'asset, Z haut), hauteur au-dessus du pivot, diametre de couronne (moyenne des emprises X et Y),
nombre de LOD, sommets du LOD0, materiaux. Sert a la table de correspondance (vegetation/correspondance_carla.json)
et au controle des hauteurs posees (arbres.py). ARGS : dossiers (liste), sortie (JSON, facultatif). RESULT : catalogue.
"""
import json

import unreal

A = dict(dossiers=['/Game/Carla/Static/Vegetation/Trees', '/Game/Carla/Static/Vegetation/Bushes',
                   '/Game/Carla/Static/Vegetation/Grass', '/Game/Carla/Static/Vegetation/Leaves'], sortie=None)
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary
SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
out = {}
for d in A['dossiers']:
    for chemin in sorted(EAL.list_assets(d, recursive=False, include_folder=False)):
        donnees = unreal.EditorAssetLibrary.find_asset_data(chemin)
        if str(donnees.asset_class_path.asset_name) != 'StaticMesh':
            continue
        sm = unreal.load_asset(chemin)
        b = sm.get_bounding_box()
        mats = [m.material_interface.get_name() if m.material_interface else None for m in sm.static_materials]
        nom = sm.get_name()
        out[nom] = {'chemin': sm.get_path_name(),
                    'min_m': [round(b.min.x / 100, 3), round(-b.max.y / 100, 3), round(b.min.z / 100, 3)],
                    'max_m': [round(b.max.x / 100, 3), round(-b.min.y / 100, 3), round(b.max.z / 100, 3)],
                    'hauteur_m': round(b.max.z / 100, 3),
                    'couronne_m': round(((b.max.x - b.min.x) + (b.max.y - b.min.y)) / 200, 3),
                    'lods': sm.get_num_lods(), 'sommets_lod0': SMS.get_number_verts(sm, 0), 'materiaux': mats}
if A['sortie']:
    with open(A['sortie'], 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'source': 'recon/pcg/ue/vegetation/ue/catalogue.py (bornes des StaticMesh CARLA, UE 5.8.3)',
                   'repere': 'm, repere local de l asset (Y local = -Y UE), Z haut, pivot = origine',
                   'assets': out}, f, ensure_ascii=False, indent=1, sort_keys=True)
RESULT = {'nb': len(out), 'sortie': A['sortie']}
