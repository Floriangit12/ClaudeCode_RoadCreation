"""[editeur] Retire du niveau courant les acteurs d'un import USD precedent (racines etiquetees comme les couches :
sol, decals_sol, ilots, ilots_couverture, et leurs descendants) avant un nouvel import : un reimport en mode REPLACE
laisse chaque acteur deux fois dans le tableau des acteurs du niveau (constat UE 5.8.3, persistant a l'enregistrement).
ARGS : racines (liste d'etiquettes). RESULT : {detruits, restants, doublons}."""
import unreal

A = dict(racines=['sol', 'decals_sol', 'ilots', 'ilots_couverture'])
A.update(globals().get('ARGS') or {})
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def racine(a):
    while a.get_attach_parent_actor() is not None:
        a = a.get_attach_parent_actor()
    return a


uniques = {a.get_path_name(): a for a in ACT.get_all_level_actors()}
cibles = [a for a in uniques.values() if racine(a).get_actor_label() in A['racines']]
prof = {a.get_path_name(): 0 for a in cibles}
for a in cibles:                                   # descendants d'abord
    p, n = a, 0
    while p.get_attach_parent_actor() is not None:
        p, n = p.get_attach_parent_actor(), n + 1
    prof[a.get_path_name()] = n
detruits = 0
for a in sorted(cibles, key=lambda x: -prof[x.get_path_name()]):
    if ACT.destroy_actor(a):
        detruits += 1
unreal.SystemLibrary.collect_garbage()
reste = [a.get_path_name() for a in ACT.get_all_level_actors()]
RESULT = {'detruits': detruits, 'restants': len(reste), 'doublons': len(reste) - len(set(reste))}
