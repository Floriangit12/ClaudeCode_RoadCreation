"""[editeur] Nettoie (cleanup PCG) puis detruit un volume PCG. ARGS : volume (chemin d'objet)."""
import unreal
from pj_tools import toolset as T

v = unreal.find_object(None, ARGS['volume'])  # noqa: F821
lab = None
if v is not None:
    lab = v.get_actor_label()
    c = v.get_component_by_class(unreal.PCGComponent)
    if c:
        c.cleanup_local(True)
    T._acteurs().destroy_actor(v)
RESULT = {'retire': lab}
