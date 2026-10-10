"""Points pj_points/0.1 (JSON) -> donnees PCG (editeur UE).

Format : {schema:"pj_points/0.1", famille, source_hash, points:[{id, asset, p:[x,y,z] (m, local, Z haut),
q:[x,y,z,w] (quaternion local, prioritaire) et/ou rpy_deg:[r,p,y], s:[sx,sy,sz], graine, ...}]}
(contrat : CONTRAT_EXPORT.md). Si q et rpy_deg sont presents, ils doivent concorder a TOL_Q_RPY_DEG pres.
Conversion (repere.py, seule implementation) : X = 100x, Y = -100y, Z = 100z ; rotation conjuguee par le
miroir Y : Rotator(roll=+r, pitch=-p, yaw=-y) (repere.rpy_local_vers_ue), Quat(-x, y, -z, w)
(repere.quat_local_vers_ue). Test : tests/test_rotations.py.
Attributs PCG crees : Mesh (SoftObjectPath, pour MeshSelectorByAttribute), Id (String), Graine (Integer64) et,
si les points portent des donnees d'instance cd:[...], cd0..cdN-1 (Float) : le Static Mesh Spawner les ecrit dans
les PerInstanceCustomData de l'ISM avec un packer PCGInstanceDataPackerByAttribute (selecteurs cd0..cdN-1, dans
l'ordre) ; un point sans cd recoit CD_ABSENT (valeur que les maitres M_PJ_* traitent comme « parametre du MI »).

Utilisations :
- voie (a) noeud PCG « Python Data Processor » : script = fichier qui appelle pdp(data_in, data_out, chemin_json) ;
- voie (b) cuisson en PCGDataAsset (noeud « Save PCG Data Asset ») puis relecture par « Load PCG Data Asset ».
"""
from __future__ import annotations

import json
import os

import unreal

from pj_tools import repere

SCHEMA = 'pj_points/0.1'
ATTR_MESH = 'Mesh'
CD_ABSENT = -9.0            # donnee d'instance absente (M_PJ_Bordure : valeur du MI ou alea)
TOL_Q_RPY_DEG = 0.05        # concordance exigee entre q et rpy_deg quand les deux sont fournis


def verifier_orientations(doc: dict) -> int:
    """Controle q (norme ~1) et sa concordance avec rpy_deg ; renvoie le nombre de points portant q."""
    n = 0
    for pt in doc['points']:
        q = pt.get('q')
        if q is None:
            continue
        n += 1
        if len(q) != 4 or abs(sum(v * v for v in q) - 1.0) > 1e-3:
            raise ValueError(f'point {pt.get("id")} : q doit etre un quaternion unitaire [x,y,z,w], recu {q}')
        if 'rpy_deg' in pt:
            e = repere.ecart_rotations_deg(repere.matrice_quat(q), repere.matrice_rpy(*pt['rpy_deg']))
            if e > TOL_Q_RPY_DEG:
                raise ValueError(f'point {pt.get("id")} : q et rpy_deg divergent de {e:.4f} deg')
    return n


def lire(chemin: str) -> dict:
    with open(chemin, encoding='utf-8') as f:
        doc = json.load(f)
    if doc.get('schema') != SCHEMA:
        raise ValueError(f'{chemin} : schema {doc.get("schema")!r} != {SCHEMA}')
    verifier_orientations(doc)
    return doc


def rotation_ue(pt: dict) -> unreal.Quat:
    """Orientation UE d'un point : q (prioritaire) sinon rpy_deg, convertis par repere.py."""
    if pt.get('q') is not None:
        return unreal.Quat(*repere.quat_local_vers_ue(pt['q']))
    roll, pitch, yaw = repere.rpy_local_vers_ue(*pt.get('rpy_deg', (0.0, 0.0, 0.0)))
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw).quaternion()


def transform_ue(pt: dict) -> unreal.Transform:
    X, Y, Z = repere.local_vers_ue(*pt['p'])
    s = pt.get('s', (1.0, 1.0, 1.0))
    if isinstance(s, (int, float)):
        s = (s, s, s)
    t = unreal.Transform(unreal.Vector(X, Y, Z), unreal.Rotator(0.0, 0.0, 0.0), unreal.Vector(*[float(v) for v in s]))
    t.rotation = rotation_ue(pt)
    return t


def point_data(doc: dict) -> unreal.PCGPointData:
    """Construit un PCGPointData (transform, graine, attributs Mesh/Id/Graine) depuis un document pj_points."""
    pd = unreal.PCGPointData()
    md = pd.mutable_metadata()
    md.create_soft_object_path_attribute(ATTR_MESH, unreal.SoftObjectPath(''), False, True)
    md.create_string_attribute('Id', '', False, True)
    md.create_integer64_attribute('Graine', 0, False, True)
    n_cd = max((len(q.get('cd') or []) for q in doc['points']), default=0)
    for i in range(n_cd):
        md.create_float_attribute(f'cd{i}', CD_ABSENT, False, True)
    pts = []
    for q in doc['points']:
        pt = unreal.PCGPoint()
        pt.transform = transform_ue(q)
        g = int(q.get('graine', 0))
        pt.seed = g & 0x7FFFFFFF
        pt.density = 1.0
        # metadata_entry est en lecture seule : les accesseurs du point creent l'entree au premier set
        pt.set_soft_object_path_attribute(md, ATTR_MESH, unreal.SoftObjectPath(q['asset']))
        pt.set_string_attribute(md, 'Id', str(q['id']))
        pt.set_integer64_attribute(md, 'Graine', g)
        cd = list(q.get('cd') or [])
        for i in range(n_cd):
            pt.set_float_attribute(md, f'cd{i}', float(cd[i]) if i < len(cd) else CD_ABSENT)
        pts.append(pt)
    pd.set_points(pts)
    return pd


def pdp(data_in, data_out, chemin_json: str, pin: str = 'Output') -> int:
    """Corps du noeud Python Data Processor : lit le JSON et emet les points sur 'pin'."""
    pd = point_data(lire(chemin_json))
    data_out.add_to_collection(pd, pin, [])
    unreal.log(f'pj_tools.charger_points : {pd.get_num_points()} points depuis {chemin_json}')
    return pd.get_num_points()


def script_pdp(chemin_json: str, chemin_py: str) -> str:
    """Ecrit le petit script appele par le noeud Python Data Processor (chemin du JSON fige dedans)."""
    os.makedirs(os.path.dirname(chemin_py), exist_ok=True)
    src = ('# Genere par pj_tools.charger_points.script_pdp : ne pas editer.\n'
           '# Variables injectees par le noeud : data_in, data_out.\n'
           'from pj_tools import charger_points\n'
           f'charger_points.pdp(data_in, data_out, r"{chemin_json}")  # noqa: F821\n')
    with open(chemin_py, 'w', encoding='utf-8') as f:
        f.write(src)
    return chemin_py


# ---------------------------------------------------------------- voie (b) : cuisson en PCGDataAsset
GRAPHE_CUISSON = '/Game/PJ/PCG/Outils/PG_Cuisson_Points'
VOLUME_CUISSON = 'PJ_Cuisson_Points'
_cuissons = {}          # references vivantes (delegues) des cuissons en cours


def _noeud(graphe, classe):
    for n in graphe.get_editor_property('nodes'):
        if isinstance(n.get_settings(), classe):
            return n
    n, _ = graphe.add_node_of_type(classe)
    return n


def graphe_cuisson():
    """Graphe outil /Game/PJ/PCG/Outils/PG_Cuisson_Points : Python Data Processor -> Save PCG Data Asset."""
    EAL = unreal.EditorAssetLibrary
    if EAL.does_asset_exist(GRAPHE_CUISSON):
        g = unreal.load_asset(GRAPHE_CUISSON)
    else:
        dossier, nom = GRAPHE_CUISSON.rsplit('/', 1)
        g = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nom, dossier, unreal.PCGGraph,
                                                                    unreal.PCGGraphFactory())
    n_py = _noeud(g, unreal.PCGPythonDataProcessorSettings)
    n_sv = _noeud(g, unreal.PCGSaveDataAssetSettings)
    n_py.set_node_position(0, 0)
    n_sv.set_node_position(400, 0)
    if not g.get_all_edges():
        # le Python Data Processor ne s'execute que si son entree 'Input' est alimentee (ici par les
        # donnees du volume, ignorees) ; la sortie du Save est cablee vers Output pour ne pas etre elaguee
        g.add_edge(g.get_input_node(), 'In', n_py, 'Input')
        g.add_edge(n_py, 'Output', n_sv, 'In')
        g.add_edge(n_sv, 'AssetPath', g.get_output_node(), 'Out')
    return g, n_py.get_settings(), n_sv.get_settings()


def lancer_cuisson(chemin_json: str, asset_path: str) -> dict:
    """Ecrit le PCGDataAsset 'asset_path' depuis le JSON (generation PCG asynchrone, quelques ticks).

    Un volume PCG temporaire est pose dans le niveau courant puis detruit apres la generation.
    """
    doc = lire(chemin_json)
    dossier, nom = asset_path.rsplit('/', 1)
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    script = script_pdp(chemin_json, os.path.join(saved, 'PJ', 'pdp', f'{nom}.py'))
    g, s_py, s_sv = graphe_cuisson()
    s_py.set_editor_property('script_input_method', unreal.PCGPythonScriptInputMethod.FILE)
    s_py.set_editor_property('script_path', unreal.FilePath(file_path=script.replace(os.sep, '/')))
    s_py.set_editor_property('mute_editor_toast', True)
    s_sv.set_editor_property('params', unreal.PCGAssetExporterParameters(
        open_save_dialog=False, asset_name=nom, asset_path=dossier, save_on_export_ended=True))
    unreal.EditorAssetLibrary.save_loaded_asset(g, False)
    act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    vol = None
    for a in act.get_all_level_actors():
        if a.get_actor_label() == VOLUME_CUISSON:
            vol = a
    if vol is None:
        vol = act.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        vol.set_actor_label(VOLUME_CUISSON)
    comp = vol.get_component_by_class(unreal.PCGComponent)
    comp.set_graph(g)
    etat = {'asset': asset_path, 'nb_points': len(doc['points']), 'script': script, 'fini': False}

    def _fin(_comp=None):
        etat['fini'] = True

        def _detruire(_dt):
            unreal.unregister_slate_post_tick_callback(h[0])
            try:
                act.destroy_actor(vol)
            except Exception:  # noqa: BLE001
                pass
        h = [None]
        h[0] = unreal.register_slate_post_tick_callback(_detruire)

    comp.on_pcg_graph_generated_external.add_callable(_fin)
    _cuissons[asset_path] = (comp, _fin, etat)
    comp.generate_local(True)
    return etat
