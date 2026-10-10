"""[editeur] Essai 5 : remise a zero SANS suppression d'asset, puis graphe de la voie (a) en Python
(le noeud Python Data Processor n'est pas propose par PCGToolset.AddNode).

Regle : ne jamais supprimer un asset potentiellement reference (ForceDelete d'un asset en usage = paquet
corrompu en memoire). Les volumes PCG d'essai sont nettoyes (cleanup_local) puis detruits ; les graphes
PG_Points_Test* existants sont VIDES (noeuds retires, entree/sortie gardees) et reutilises ; le PCGDataAsset
est reecrit en place par pj_tools.charger_points.

ARGS : niveau, json, script_pdp (fichier .py ecrit pour le noeud), pda.
RESULT : retires, graphe_a, graphe_b (chemin si PG_Points_Test existe deja et a ete vide, sinon None), pda_existe.
"""
import unreal
from pj_tools import toolset as T
from pj_tools import charger_points as cp

A = ARGS  # noqa: F821
EAL = unreal.EditorAssetLibrary
ACT = T._acteurs()
res = {'retires': [], 'graphes_vides': {}}

if T._monde().get_path_name().split('.')[0] != A['niveau']:
    T._preparer_changement_niveau(True)
    T._niveaux().load_level(A['niveau'])

for a in ACT.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith('PJ_PCG_Points') or lab.startswith('PJ_Essai_Cuisson') or lab == cp.VOLUME_CUISSON:
        c = a.get_component_by_class(unreal.PCGComponent)
        if c:
            c.cleanup_local(True)
        res['retires'].append(lab)
        ACT.destroy_actor(a)


def graphe_vide(chemin):
    """Charge le graphe s'il existe et retire tous ses noeuds (entree/sortie conservees) ; sinon None."""
    if not EAL.does_asset_exist(chemin):
        return None
    g = unreal.load_asset(chemin)
    noeuds = list(g.get_editor_property('nodes'))
    for n in noeuds:
        g.remove_node(n)
    res['graphes_vides'][chemin] = len(noeuds)
    return g


gb = graphe_vide('/Game/PJ/PCG/PG_Points_Test')
if gb is not None:
    EAL.save_loaded_asset(gb, False)
res['graphe_b'] = gb.get_path_name() if gb is not None else None
res['pda_existe'] = EAL.does_asset_exist(A['pda'])

# ---- voie (a) : PG_Points_Test_PDP = Input -> Python Data Processor -> Static Mesh Spawner (attribut Mesh)
cp.script_pdp(A['json'], A['script_pdp'])
g = graphe_vide('/Game/PJ/PCG/PG_Points_Test_PDP')
if g is None:
    g = unreal.AssetToolsHelpers.get_asset_tools().create_asset('PG_Points_Test_PDP', '/Game/PJ/PCG',
                                                                unreal.PCGGraph, unreal.PCGGraphFactory())
n_py, s_py = g.add_node_of_type(unreal.PCGPythonDataProcessorSettings)
s_py.set_editor_property('script_input_method', unreal.PCGPythonScriptInputMethod.FILE)
s_py.set_editor_property('script_path', unreal.FilePath(file_path=A['script_pdp']))
s_py.set_editor_property('mute_editor_toast', True)
n_sm, s_sm = g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
s_sm.set_mesh_selector_type(unreal.PCGMeshSelectorByAttribute)
s_sm.get_editor_property('mesh_selector_parameters').set_editor_property('attribute_name', cp.ATTR_MESH)
n_py.set_node_position(0, 0)
n_sm.set_node_position(400, 0)
g.add_edge(g.get_input_node(), 'In', n_py, 'Input')
g.add_edge(n_py, 'Output', n_sm, 'In')
g.add_edge(n_sm, 'Out', g.get_output_node(), 'Out')
EAL.save_loaded_asset(g, False)
res['graphe_a'] = g.get_path_name()
res['noeuds_a'] = [n.get_path_name() for n in (n_py, n_sm)]
RESULT = res
