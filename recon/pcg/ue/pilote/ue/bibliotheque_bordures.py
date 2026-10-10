"""[editeur] Bibliotheque des bordures : prototypes Houdini (prototypes/index.json, pj_bordure_prototypes) importes en
StaticMesh Nanite /Game/PJ/Lib/Bordures/SM_<nom> (sans acteur), un asset par prototype.

Une couche USD de bibliotheque (Saved/PJ/usd/bibliotheque_bordures.usda) reference chaque prototype sous
/World/Bordures/<nom> (kind component du prototype) ; import en contexte unreal (Material /<nom>/Looks/<id> lie en
material:binding:preview -> MI_<id>), fusion par component (kinds_to_collapse = 2), import_actors = faux.
Pivot conserve (CONTRAT_EXPORT.md : X = s, Y = -u, Z = v, origine au milieu de l'element, sur la face vue, sous le
bloc) : le fil d'eau est a z_pied au-dessus du pivot (M_PJ_Bordure : donnee d'instance cd5, pilote/points_ue.py).
ARGS : fabrique (dossier), dest, noms (liste facultative, essai), nanite (vrai).
RESULT : nb, assets, absents, reglages (normales, UV, Nanite), journal LogStaticMesh / LogUsd, acceptation.
"""
import json
import os
import time

import unreal
from pj_tools import toolset as T

A = dict(fabrique='D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/fabrique_ue_snapshot',
         dest='/Game/PJ/Lib/Bordures', noms=None, nanite=True)
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary

index = json.load(open(os.path.join(A['fabrique'], 'prototypes', 'index.json'), encoding='utf-8'))['prototypes']
noms = sorted(A['noms'] or index)
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
couche = os.path.join(saved, 'PJ', 'usd', 'bibliotheque_bordures.usda').replace('\\', '/')
os.makedirs(os.path.dirname(couche), exist_ok=True)
lignes = ['#usda 1.0', '(', '    defaultPrim = "World"', '    metersPerUnit = 1', '    upAxis = "Z"', ')', '',
          'def Xform "World" (kind = "assembly")', '{', '    def Xform "Bordures" (kind = "group")', '    {']
for n in noms:
    f = os.path.join(A['fabrique'], index[n]['fichier']).replace('\\', '/')
    lignes.append(f'        def Xform "{n}" (prepend references = @{f}@) {{}}')
lignes += ['    }', '}', '']
with open(couche, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('\n'.join(lignes))

opts = unreal.UsdStageImportOptions()
refus = T._set(opts, import_actors=False, import_geometry=True, import_materials=True,
               import_skeletal_animations=False, import_level_sequences=False, import_groom_assets=False,
               import_sounds=False, import_sparse_volume_textures=False, prims_to_import=['/'], purposes_to_import=7,
               material_purpose='preview', render_context_to_import='unreal', use_prim_kinds_for_collapsing=True,
               kinds_to_collapse=2, merge_identical_material_slots=True, share_assets_for_identical_prims=False,
               override_stage_options=False, prim_path_folder_structure=False,
               nanite_triangle_threshold=0 if A['nanite'] else 2147483647,
               existing_actor_policy=unreal.ReplaceActorPolicy.REPLACE,
               existing_asset_policy=unreal.ReplaceAssetPolicy.REPLACE)
# l'importeur range les assets dans <dest>/<couche>/StaticMeshes : import en zone de transit puis deplacement vers
# <dest>/SM_<nom> (convention de prototypes/index.json). Rejeu : instances PCG des bordures nettoyees (plus aucune
# reference) puis anciens assets supprimes avant le deplacement.
ACT = T._acteurs()
for a in ACT.get_all_level_actors():
    if a.get_actor_label() == A.get('volume_pcg', 'PJ_PCG_Bordures'):
        a.get_component_by_class(unreal.PCGComponent).cleanup_local(True)
t = unreal.AssetImportTask()
T._set(t, filename=couche, destination_path=A['dest'], automated=True, replace_existing=True, save=True, options=opts)
t0 = time.time()
pos = T._journal_position()
objs = T._taches_import([t])
deplaces, refus_dep = [], []
for i, p in enumerate(list(objs)):
    paquet = p.split('.')[0]
    nom = paquet.rsplit('/', 1)[-1]
    cible = f"{A['dest']}/{nom}"
    if paquet == cible or not isinstance(unreal.load_asset(p), unreal.StaticMesh):
        continue
    if EAL.does_asset_exist(cible):
        EAL.delete_asset(cible)
    if EAL.rename_asset(paquet, cible):
        objs[i] = f'{cible}.{nom}'
        deplaces.append(nom)
    else:
        refus_dep.append(nom)
transit = f"{A['dest']}/{os.path.splitext(os.path.basename(couche))[0]}"
if not refus_dep and EAL.does_directory_exist(transit):
    EAL.delete_directory(transit)
sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
assets, reglages = {}, []
for p in objs:
    sm = unreal.load_asset(p)
    if not isinstance(sm, unreal.StaticMesh):
        continue
    bs = sub.get_lod_build_settings(sm, 0)
    modifie = False
    if not bs.get_editor_property('use_full_precision_u_vs'):
        bs.set_editor_property('use_full_precision_u_vs', True)
        sub.set_lod_build_settings(sm, 0, bs)
        modifie = True
    ns = sm.get_editor_property('nanite_settings')
    if A['nanite'] and not ns.get_editor_property('enabled'):
        ns.set_editor_property('enabled', True)
        sm.set_editor_property('nanite_settings', ns)
        modifie = True
    if modifie:
        EAL.save_loaded_asset(sm, False)
    assets[sm.get_name()] = p
    reglages.append({'mesh': sm.get_name(), 'triangles': sub.get_number_triangles(sm, 0) if hasattr(sub, 'get_number_triangles') else None,
                     'uv': sub.get_num_uv_channels(sm, 0),
                     'nanite': bool(sm.get_editor_property('nanite_settings').get_editor_property('enabled')),
                     'recompute_normals': bool(bs.get_editor_property('recompute_normals')),
                     'materiaux': [m.material_interface.get_name() if m.material_interface else None
                                   for m in sm.get_editor_property('static_materials')]})
try:
    unreal.AutomationLibrary.finish_loading_before_screenshot()
except Exception:  # noqa: BLE001
    pass
journal = T._journal_depuis(pos, ('LogStaticMesh', 'LogUsd', 'LogUsdStage', 'LogMeshDescription'))
absents = [n for n in noms if f'SM_{n}' not in assets]
n_sm = len(journal.get('LogStaticMesh', []))
mats = {}
for r in reglages:
    for m in r['materiaux']:
        mats[m] = mats.get(m, 0) + 1
RESULT = {'nb': len(assets), 'demandes': len(noms), 'absents': absents[:50], 'couche': couche,
          'deplaces': len(deplaces), 'deplacements_refuses': refus_dep[:20],
          'chemin_exemple': next(iter(assets.values()), None),
          'options_refusees': refus, 'materiaux': mats,
          'recompute_normals': sum(r['recompute_normals'] for r in reglages),
          'sans_uv': [r['mesh'] for r in reglages if r['uv'] < 1][:20],
          'sans_nanite': [r['mesh'] for r in reglages if not r['nanite']][:20],
          'exemples': reglages[:5], 'journal': journal,
          'acceptation': {'avertissements_logstaticmesh': n_sm, 'ok': n_sm == 0}, 'duree_s': round(time.time() - t0, 1)}
