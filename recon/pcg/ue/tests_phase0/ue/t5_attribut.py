"""[editeur] Essai 5 : controle (et repli) du reglage MeshSelectorByAttribute du Static Mesh Spawner ;
renvoie aussi les broches de sortie des noeuds (celles du Load PCG Data Asset viennent de l'asset).

ARGS : graphe. Si UpdateNode (MCP) n'a pas pu regler l'attribut, il est fixe ici a 'Mesh' (repli Python).
"""
import unreal

g = unreal.load_asset(ARGS['graphe'])  # noqa: F821
out = []
for n in g.get_editor_property('nodes'):
    s = n.get_settings()
    if isinstance(s, unreal.PCGStaticMeshSpawnerSettings):
        sel = s.get_editor_property('mesh_selector_parameters')
        avant = str(sel.get_editor_property('attribute_name')) if isinstance(sel, unreal.PCGMeshSelectorByAttribute) else None
        if not isinstance(sel, unreal.PCGMeshSelectorByAttribute):
            s.set_mesh_selector_type(unreal.PCGMeshSelectorByAttribute)
            sel = s.get_editor_property('mesh_selector_parameters')
        repli = str(sel.get_editor_property('attribute_name')) != 'Mesh'
        if repli:
            sel.set_editor_property('attribute_name', 'Mesh')
        out.append({'noeud': n.get_name(), 'selecteur': sel.get_class().get_name(), 'attribut_avant': avant,
                    'attribut': str(sel.get_editor_property('attribute_name')), 'repli_python': repli})
unreal.EditorAssetLibrary.save_loaded_asset(g, False)
pins = {n.get_name(): [str(p.get_editor_property('properties').get_editor_property('label'))
                       for p in n.get_editor_property('output_pins')] for n in g.get_editor_property('nodes')}
RESULT = {'spawners': out, 'pins_sortie': pins}
