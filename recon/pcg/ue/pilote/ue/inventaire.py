"""[editeur] Inventaire du niveau courant : acteurs par racine USD / dossier, StaticMesh poses, instances (ISM/HISM)
par mesh et par materiau. RESULT : {acteurs, composants_sm, instances_par_mesh, total_instances, materiaux}."""
import collections

import unreal

ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# dedoublonne : apres un reimport USD (REPLACE), le tableau des acteurs du niveau peut lister deux fois le meme acteur
acteurs = list({a.get_path_name(): a for a in ACT.get_all_level_actors()}.values())
par_dossier = collections.Counter(str(a.get_folder_path()) or '-' for a in acteurs)
inst, mats, n_sm = collections.Counter(), collections.Counter(), 0
for a in acteurs:
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property('static_mesh')
        if sm is None:
            continue
        nom = sm.get_name()
        if isinstance(c, unreal.InstancedStaticMeshComponent):
            inst[nom] += c.get_instance_count()
        else:
            n_sm += 1
            inst[nom] += 1
        for i in range(c.get_num_materials()):
            m = c.get_material(i)
            mats[m.get_name() if m else None] += 1
RESULT = {'nb_acteurs': len(acteurs), 'acteurs_par_dossier': dict(par_dossier), 'composants_sm_simples': n_sm,
          'total_instances': sum(inst.values()), 'instances_par_mesh': dict(inst.most_common(60)),
          'materiaux': dict(mats.most_common(60))}
