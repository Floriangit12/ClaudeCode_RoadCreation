"""[editeur] Retire du niveau courant les hierarchies d'acteurs importees dont un StaticMesh est sous
ARGS['dossier'] (racine d'attache et descendants). Si ARGS['supprimer_assets'], supprime aussi le dossier
de contenu (contenu d'essai uniquement)."""
import unreal
from pj_tools import toolset as T

A = ARGS  # noqa: F821
ACT = T._acteurs()


def racine(a):
    while a.get_attach_parent_actor() is not None:
        a = a.get_attach_parent_actor()
    return a


def descendants(a, acc):
    acc.append(a)
    for e in a.get_attached_actors():
        descendants(e, acc)
    return acc


cibles = {}
for a in ACT.get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.static_mesh
        if sm and sm.get_path_name().startswith(A['dossier']):
            for d in descendants(racine(a), []):
                cibles[d.get_path_name()] = d
            break
labels = sorted(d.get_actor_label() for d in cibles.values())
for d in cibles.values():
    ACT.destroy_actor(d)
supp = None
if A.get('supprimer_assets') and unreal.EditorAssetLibrary.does_directory_exist(A['dossier']):
    T.pj_tools.save_all()
    supp = unreal.EditorAssetLibrary.delete_directory(A['dossier'])
RESULT = {'retires': labels, 'dossier_supprime': supp}
