"""[editeur] Essai 6 : Houdini Engine (H22.0.459, licence Indie) dans UE 5.8.

ARGS : niveau, mode ('nettoyer' | 'lancer' | 'etat'), hda (fichier .hdalc/.hda), dossier, label, x, y (m locaux),
taille [x, y, z] (m, repere Houdini Y-haut), log (journal de l'editeur).
- lancer : importe l'HDA (UHoudiniAsset), ouvre la session HAPI si besoin, instancie l'actif (cuisson
  automatique asynchrone), regle les parametres ; le wrapper est garde vivant dans pj_tools._he.
- etat : sorties de la cuisson (types, objets, composants), bornes de l'acteur, lignes Houdini du journal.
"""
import os

import unreal
import pj_tools
from pj_tools import toolset as T
from pj_tools import repere

A = ARGS  # noqa: F821
ACT = T._acteurs()
api = unreal.HoudiniPublicAPIBlueprintLib.get_api()
res = {'mode': A['mode'], 'session_valide_avant': api.is_session_valid()}

if A['mode'] == 'nettoyer':
    # destruction de l'instance precedente (asynchrone cote HAPI) : appel separe, avant 'lancer'
    w = getattr(pj_tools, '_he', {}).pop(A['label'], None)
    res['wrapper_supprime'] = bool(w and w.delete_instantiated_asset())
    for a in ACT.get_all_level_actors():
        if a.get_actor_label() == A['label']:
            ACT.destroy_actor(a)
            res['acteur_detruit'] = True
elif A['mode'] == 'lancer':
    if T._monde().get_path_name().split('.')[0] != A['niveau']:
        T._preparer_changement_niveau(True)
        T._niveaux().load_level(A['niveau'])
    chemin = f"{A['dossier']}/{os.path.splitext(os.path.basename(A['hda']))[0]}"
    if not unreal.EditorAssetLibrary.does_asset_exist(chemin):     # pas de reimport sous une instance vivante
        t = unreal.AssetImportTask()
        T._set(t, filename=A['hda'], destination_path=A['dossier'], automated=True, replace_existing=True, save=True)
        res['import'] = T._taches_import([t])
    asset = unreal.load_asset(chemin)
    if not isinstance(asset, unreal.HoudiniAsset):
        raise RuntimeError(f'UHoudiniAsset absent : {chemin}')
    if not api.is_session_valid():
        api.create_session()
    res['session_valide'] = api.is_session_valid()
    X, Y, Z = repere.local_vers_ue(A['x'], A['y'], 0.0)
    reg = unreal.HoudiniPublicAPISettings()
    reg.set_editor_property('transform', unreal.Transform(unreal.Vector(X, Y, Z), unreal.Rotator(0, 0, 0),
                                                          unreal.Vector(1, 1, 1)))
    reg.set_editor_property('enable_auto_cook', True)
    # instantiate (API courante) attend la fin de l'instanciation : parametres reglables tout de suite
    w = api.instantiate(asset, unreal.HoudiniPublicAPIInstantiationType.HOUDINI_ASSET_COMPONENT, reg)
    if w is None:
        raise RuntimeError(f'instantiate a echoue : {api.get_last_error_message()}')
    pj_tools._he = getattr(pj_tools, '_he', {})
    pj_tools._he[A['label']] = w                     # empeche le ramasse-miettes du wrapper
    act = w.get_houdini_asset_actor()
    if act:
        act.set_actor_label(A['label'])
    regles = [w.set_float_parameter_value('taille', float(v), i) for i, v in enumerate(A['taille'])]
    pj_tools._he_params = getattr(pj_tools, '_he_params', {})
    pj_tools._he_params[A['label']] = all(regles)
    res['params_regles'] = regles
    res['acteur'] = act.get_path_name() if act else None
    res['erreur_api'] = api.get_last_error_message()
else:
    w = getattr(pj_tools, '_he', {}).get(A['label'])
    if w is None:
        raise RuntimeError('wrapper introuvable (lancer d abord)')
    res['session_valide'] = api.is_session_valid()
    if not pj_tools._he_params.get(A['label']):
        regles = [w.set_float_parameter_value('taille', float(v), i) for i, v in enumerate(A['taille'])]
        res['params_regles'] = regles
        if all(regles):
            pj_tools._he_params[A['label']] = True       # recuisson automatique
    res['params_appliques'] = pj_tools._he_params.get(A['label'])
    n = w.get_num_outputs()
    sorties = []
    for i in range(n):
        ids = w.get_output_identifiers_at(i)
        ids = ids[-1] if isinstance(ids, tuple) else ids
        objs = []
        for ident in (ids or []):
            o = w.get_output_object_at(i, ident)
            d = {'objet': o.get_path_name() if o else None, 'classe': o.get_class().get_name() if o else None,
                 'proxy': w.is_output_current_proxy_at(i, ident)}
            if isinstance(o, unreal.StaticMesh):
                b = o.get_bounding_box()
                d['bornes_cm'] = [[b.min.x, b.min.y, b.min.z], [b.max.x, b.max.y, b.max.z]]
                d['triangles_lod0'] = o.get_num_triangles(0) if hasattr(o, 'get_num_triangles') else None
            objs.append(d)
        sorties.append({'index': i, 'type': str(w.get_output_type_at(i)), 'objets': objs})
    res['sorties'] = sorties
    proxy = any(o.get('proxy') for s in sorties for o in s['objets'])
    if pj_tools._he_params.get(A['label']) and proxy:
        # le plugin garde un maillage « proxy » (HoudiniStaticMesh) puis l'affine en UStaticMesh
        # (minuterie ou sauvegarde) : on force l'affinage
        res['affinage'] = str(w.refine_all_current_proxy_outputs(True))
    act = w.get_houdini_asset_actor()
    if act:
        res['acteur_cm'] = [act.get_actor_location().x, act.get_actor_location().y, act.get_actor_location().z]
        res['composants'] = []
        for c in act.get_components_by_class(unreal.MeshComponent):
            o, e, _r = unreal.SystemLibrary.get_component_bounds(c)
            res['composants'].append({'classe': c.get_class().get_name(), 'nom': c.get_name(),
                                      'centre_cm': [o.x, o.y, o.z], 'demi_etendue_cm': [e.x, e.y, e.z],
                                      'visible': c.is_visible()})
    res['params_lus'] = [w.get_float_parameter_value('taille', i) for i in range(3)]
    res['erreur_api'] = api.get_last_error_message()
    lignes = []
    if os.path.isfile(A.get('log', '')):
        with open(A['log'], encoding='utf-8', errors='replace') as f:
            for ligne in f:
                if 'Houdini' in ligne and any(k in ligne.lower() for k in ('licen', 'indie', 'session', 'hapi',
                                                                            'error', 'cook', 'warning')):
                    lignes.append(ligne.rstrip()[:300])
    res['journal_houdini'] = lignes[-60:]
RESULT = res
