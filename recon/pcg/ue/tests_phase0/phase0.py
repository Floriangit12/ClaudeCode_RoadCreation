"""Essais de phase 0 pilotes par MCP (editeur UE ouvert, pj_tools publie).

Usage : python phase0.py <essai> [...] [ev=<EV100>]   essais : t1 t2 t3 t4 t5 t6 t7 (ou 'tout')
  t1 niveau /Game/PJ/Maps/PJ_Phase0 (sol neutre, ciel physique, soleil, exposition manuelle)
  t2 vegetation CARLA sous Lumen (pose + inventaire des materiaux + vues)
  t3 mires de georeferencement + GeoReferencingSystem EPSG:2154
  t4 import USD (couche bordures v1) : echelle, axes, remappage de materiau (contexte 'unreal')
  t5 points pj_points/0.1 -> PCG : voie (b) PCGDataAsset (retenue) et voie (a) Python Data Processor
  t6 Houdini Engine : HDA .hdalc (hda/creer_hda_boite.py) cuit dans UE
  t7 non-regression de high_res_capture (Lumen) et lumiere du ciel : ombre d'une boite haute, rapport ombre/soleil
     dans [0,18 ; 0,32], canal R >= 0,10 (pj_tools/eclairage.py) et a moins de 20 % du viewport
Les scripts executes dans l'editeur sont dans ./ue (via pj_tools.run_python_file).
Chaque essai ecrit <OUT>/t<n>_*.json (+ PNG) ; OUT = recon/out/paquet_jardin/v2/ue_phase0.
"""
from __future__ import annotations

import json
import os
import sys
import time

import commun as C

E = C.eclairage            # reference d'eclairage (pj_tools/eclairage.py) : soleil, ciel, EV100, post-process neutre


def t1(c, **_):
    """Niveau PJ_Phase0 : sol neutre, SkyAtmosphere, soleil, SkyLight temps reel, brouillard, PPV manuel."""
    r = C.ue(c, 't1_niveau.py', dict(niveau=C.NIVEAU, ev100=C.EV100, wb_temp=E.BALANCE_BLANCS_K, **E.SOLEIL, **E.CIEL))
    res = {'essai': 't1', 'date': C.horodatage(), 'ev100': C.EV100, **r['resultat']}
    # vue de controle du niveau vide : auto (EV de reference) puis manuel (EV fige)
    res['capture_auto'] = C.capture(c, 't1_niveau_auto', (-30, 0, 1.6), 0, -5, ev100=-100)
    res['capture'] = C.capture(c, 't1_niveau', (-30, 0, 1.6), 0, -5)
    C.ecrire_json('t1_niveau.json', res)
    return res


VEG = 'Game/Carla/Static/Vegetation'
X0 = 300.0   # rangee d'essai a l'ecart (x = 300 m) : hors des 200 arbres de t5 et des bordures (+-150 m)
RANGEE = [['P0_Veg_Chene_M', f'/{VEG}/Trees/SM_Oak_M_v1', X0 + 0.0],
          ['P0_Veg_Erable_L', f'/{VEG}/Trees/SM_Maple_L_v1', X0 + 8.0],
          ['P0_Veg_FreneBlanc', f'/{VEG}/Trees/SM_WhiteAsh_01_v1', X0 + 16.0],
          ['P0_Veg_Buisson_M', f'/{VEG}/Bushes/SM_Bush_M_v1', X0 + 24.0],
          ['P0_Veg_Buisson_L', f'/{VEG}/Bushes/SM_Bush_L_v1', X0 + 32.0]]
HERBE = {'asset': f'/{VEG}/Grass/SM_Grass_01', 'x0': X0 + 39.0, 'n': 3, 'pas': 1.0}
VUES_VEG = {  # nom: (camera m, yaw, pitch, fov)
    't2_veg_oeil_1m60': ((X0 + 20, -30, 1.6), 90, 8, 75),
    't2_veg_haut_20m': ((X0 + 20, -32, 20), 90, -20, 75),
    't2_veg_detail_chene': ((X0 + 0, -9, 1.6), 90, 25, 60),
    't2_veg_detail_tronc_chene': ((X0 + 0.5, -3.5, 1.6), 95, 5, 50),
    't2_veg_detail_frene_blanc': ((X0 + 16, -12, 1.6), 90, 22, 60),
    't2_veg_detail_buissons_herbe': ((X0 + 32, -7, 1.6), 75, -12, 70),
    't2_veg_detail_herbe': ((X0 + 40, -2.5, 1.0), 90, -30, 60),
}


def t2(c, ev=None):
    """Vegetation CARLA sous Lumen : pose, inventaire des materiaux, 4 vues 1920x1080."""
    r = C.ue(c, 't2_vegetation.py', dict(niveau=C.NIVEAU, rangee=RANGEE, herbe=HERBE))
    res = {'essai': 't2', 'date': C.horodatage(), **r['resultat'], 'captures': {}}
    for nom, (cam, yaw, pitch, fov) in VUES_VEG.items():
        res['captures'][nom] = C.capture(c, nom, cam, yaw, pitch, fov, ev100=C.EV100 if ev is None else ev)
    C.ecrire_json('t2_vegetation.json', res)
    return res


MIRES = [['Centre_carrefour', -1.569, -5.089, 0.02],
         ['Arret_Verdun_SO', -17.78, -27.90, 0.0],
         ['Arret_Verdun_NE', 10.59, 13.74, 0.0],
         ['Arret_Reviree', -10.62, 12.85, 0.0],
         ['Arret_Vercors', 11.84, -17.29, 0.0]]


def t3(c, **_):
    """Mires : pose, relecture par 2 voies (Python editeur + ActorTools MCP), GeoReferencing EPSG:2154."""
    from pyproj import Transformer
    r = C.ue(c, 't3_mires.py', dict(niveau=C.NIVEAU, mires=MIRES))['resultat']
    l93_wgs = Transformer.from_crs(2154, 4326, always_xy=True)
    pire = 0.0
    for m in r['mires']:
        tr = c.call_tool('editor_toolset.toolsets.actor.ActorTools', 'get_actor_transform',
                         {'actor': {'refPath': m['acteur']}})
        tr = tr.get('returnValue', tr) if isinstance(tr, dict) else tr
        loc = tr.get('location', {}) if isinstance(tr, dict) else {}
        lu = [loc.get('x'), loc.get('y'), loc.get('z')]
        m['actortools_ue_cm'] = lu
        m['actortools_ecart_cm'] = [a - b for a, b in zip(lu, m['attendu_ue_cm'])] if None not in lu else None
        ecarts = [abs(v) for v in m['ecart_cm'] + (m['actortools_ecart_cm'] or [1e9])]
        m['ecart_max_cm'] = max(ecarts)
        pire = max(pire, m['ecart_max_cm'])
        lon, lat = l93_wgs.transform(m['l93'][0], m['l93'][1])
        m['wgs84_pyproj'] = [lat, lon]
    for d in r['georef'].get('conversions', []):
        ref = next(m for m in r['mires'] if m['nom'] == d['nom'])
        if 'wgs84' in d:
            dlat = (d['wgs84'][0] - ref['wgs84_pyproj'][0]) * 111132.0
            dlon = (d['wgs84'][1] - ref['wgs84_pyproj'][1]) * 111320.0 * 0.7049
            d['ecart_vs_pyproj_cm'] = round(100.0 * (dlat ** 2 + dlon ** 2) ** 0.5, 3)
    res = {'essai': 't3', 'date': C.horodatage(), 'critere_cm': 1.0, 'ecart_max_cm': pire,
           'ok': pire <= 1.0, **r}
    # vues : verticale (nord en haut) et oblique depuis le SO
    res['captures'] = {
        't3_mires_verticale': C.capture(c, 't3_mires_verticale', (-3.0, -7.0, 70.0), 90, -89.9, 70),
        't3_mires_oblique': C.capture(c, 't3_mires_oblique', (-40.0, -50.0, 18.0), 45, -18, 70),
    }
    C.ecrire_json('t3_mires.json', res)
    return res


USD_BORDURES = f'{C.DEPOT}/recon/out/paquet_jardin/package/layers/bordures.usdc'.replace('\\', '/')
USD_REMAP = f'{C.ICI}/usd/bordures_remap.usda'.replace('\\', '/')


def t4(c, **_):
    """Import USD : (a) couche bordures v1 telle quelle ; (b) meme couche + materiau remappe (contexte 'unreal')."""
    c.pj('load_level', {'path': C.NIVEAU, 'discard_untitled': True})
    res = {'essai': 't4', 'date': C.horodatage()}
    # reprise propre : acteurs et assets d'essai d'un passage precedent
    res['nettoyage'] = C.ue(c, 't4_retirer.py', {'dossier': '/Game/PJ/Test_USD', 'supprimer_assets': True})['resultat']
    # (a) import brut, contexte universel
    ia = c.pj('import_usd', {'usd_path': USD_BORDURES, 'dest_path': '/Game/PJ/Test_USD/Bordures'}, timeout=1800)
    res['import_a'] = ia
    va = C.ue(c, 't4_usd_verif.py', {'usd': USD_BORDURES, 'dossier': '/Game/PJ/Test_USD/Bordures',
                                     'prims': ['/World/Bordures/faces_verticales']})['resultat']
    res['verif_a'] = va
    # les acteurs de (a) font doublon avec (b) : retires du niveau (les assets restent)
    res['retrait_a'] = C.ue(c, 't4_retirer.py', {'dossier': '/Game/PJ/Test_USD/Bordures'})['resultat']
    # (b) remappage du materiau 'bordure' -> MI_Concrete_01 (CARLA) + boite asymetrique
    ib = c.pj('import_usd', {'usd_path': USD_REMAP, 'dest_path': '/Game/PJ/Test_USD/Remap',
                             'render_context': 'unreal'}, timeout=1800)
    res['import_b'] = ib
    vb = C.ue(c, 't4_usd_verif.py', {'usd': USD_REMAP, 'dossier': '/Game/PJ/Test_USD/Remap',
                                     'prims': ['/World/Bordures/faces_verticales', '/World/Essai/Boite_asym']})['resultat']
    res['verif_b'] = vb
    ecarts = [p.get('ecart_boite_cm', 1e9) for p in va['prims'] + vb['prims']]
    ecarts += [p.get('ecart_extremes_max_cm', 1e9) for p in va['prims'] + vb['prims']]
    res['ecart_max_cm'] = max(ecarts)
    mats = [m for p in vb['prims'] for m in p.get('ue', {}).get('materiaux', [])]
    res['remap_ok'] = bool(mats) and all(m and 'MI_Concrete_01' in m for m in mats)
    c.pj('save_all')
    res['captures'] = {
        't4_usd_bordures': C.capture(c, 't4_usd_bordures', (-1.5, -26.0, 4.0), 90, -8, 70),
        't4_usd_boite': C.capture(c, 't4_usd_boite', (3.5, -2.2, 1.0), 90, -22, 60),
    }
    C.ecrire_json('t4_usd.json', res)
    return res


PDA = '/Game/PJ/PCG/Donnees/PDA_Points_Test'
GRAPHES = os.path.join(os.path.dirname(C.ICI), 'graphes').replace('\\', '/')
PCGT = 'PCGToolset.PCGToolset'
ECHANTILLON = ['arbre_215', 'arbre_164']     # complete par 3 ids pris dans le JSON


def _ref(x):
    """refPath d'une reponse PCGToolset (objet, {'returnValue':...}, {'actor':...}, {'node':...})."""
    if isinstance(x, dict):
        for k in ('refPath', 'returnValue', 'actor', 'node', 'graph'):
            if k in x:
                return _ref(x[k])
    return x


def _executer(c, vol_ref, json_path, echantillon, max_s=180):
    t0 = time.time()
    issues = c.call_tool(PCGT, 'ExecuteGraphInstance', {'pCGVolume': {'refPath': vol_ref}}, timeout=900)
    v = None
    while time.time() - t0 < max_s:
        v = C.ue(c, 't5_verif.py', {'volume': vol_ref, 'json': json_path, 'echantillon': echantillon})['resultat']
        if v['nb_instances'] >= v['nb_points']:
            break
        time.sleep(1.0)
    return {'issues': issues, 'duree_s': round(time.time() - t0, 2), 'verif': v}


def _volume(c, graphe, nom):
    r = c.call_tool(PCGT, 'SpawnGraphInstance', {
        'graph': {'refPath': graphe}, 'name': nom, 'jsonParams': '',
        'transform': {'location': {'x': 0, 'y': 0, 'z': 0}, 'rotation': {'pitch': 0, 'yaw': 0, 'roll': 0},
                      'scale': {'x': 25, 'y': 25, 'z': 10}}})
    return _ref(r)


def t5(c, **_):
    """Transport des points -> PCG : voie (b) PCGDataAsset (retenue) et voie (a) Python Data Processor."""
    import gen_points_test
    js = gen_points_test.main().replace('\\', '/')
    doc = json.load(open(js, encoding='utf-8'))
    ech = ECHANTILLON + [p['id'] for p in doc['points'][50:200:50]]
    res = {'essai': 't5', 'date': C.horodatage(), 'json': js, 'nb_points': len(doc['points']), 'echantillon': ech}
    res['preparation'] = C.ue(c, 't5_preparer.py', {
        'niveau': C.NIVEAU, 'json': js, 'pda': PDA,
        'script_pdp': f'{GRAPHES}/PG_Points_Test_PDP_lire.py'})['resultat']

    # ---- voie (b) : cuisson JSON -> PCGDataAsset (outil pj_tools.charger_points)
    t0 = time.time()
    c.pj('charger_points', {'json_path': js, 'asset_path': PDA})
    e = {}
    while time.time() - t0 < 120:
        e = c.pj('charger_points', {'json_path': js, 'asset_path': PDA, 'etat_seulement': True})
        if e.get('fini') and e.get('asset_existe'):
            break
        time.sleep(0.5)
    res['b_cuisson'] = {**e, 'duree_s': round(time.time() - t0, 2)}

    # ---- voie (b) : graphe d'execution construit par PCGToolset (MCP) ; un graphe existant est reutilise
    # (vide par t5_preparer : aucun asset n'est supprime, cf. ForceDelete d'un asset en usage)
    g = res['preparation'].get('graphe_b') or _ref(c.call_tool(PCGT, 'CreateGraph', {'name': 'PG_Points_Test',
                                                                                     'path': '/Game/PJ/PCG'}))
    res['b_graphe'] = g
    n_load = _ref(c.call_tool(PCGT, 'AddNode', {
        'graph': {'refPath': g}, 'nativeNodeType': 'Load PCG Data Asset', 'nodeName': 'Charger_Points',
        'nodeTitle': 'Charger points (PCGDataAsset)', 'nodeComment': 'voie b : asset cuit par pj_tools.charger_points',
        'xPositionIdx': 0, 'yPositionIdx': 0,
        'jsonParams': json.dumps({'asset': {'refPath': f'{PDA}.{PDA.rsplit("/", 1)[-1]}'}, 'bSynchronousLoad': True})}))
    n_sms = _ref(c.call_tool(PCGT, 'AddNode', {
        'graph': {'refPath': g}, 'nativeNodeType': 'Static Mesh Spawner', 'nodeName': 'Poser_Meshes',
        'nodeTitle': 'Poser meshes (attribut Mesh)', 'nodeComment': 'MeshSelectorByAttribute sur Mesh',
        'xPositionIdx': 400, 'yPositionIdx': 0,
        'jsonParams': json.dumps({'meshSelectorType': {'refPath': '/Script/PCG.PCGMeshSelectorByAttribute'}})}))
    res['b_noeuds'] = [n_load, n_sms]
    try:
        res['b_maj_attribut'] = c.call_tool(PCGT, 'UpdateNode', {
            'node': {'refPath': n_sms}, 'nodeTitle': '',
            'jsonParams': json.dumps({'meshSelectorParameters': {'attributeName': 'Mesh'}})})
    except Exception as ex:  # noqa: BLE001
        res['b_maj_attribut'] = f'echec : {ex}'[:500]
    struct = c.call_tool(PCGT, 'GetGraphStructure', {'graph': {'refPath': g}})
    sortie = next(n['path'] for n in struct['nodes'] if n['nodeType'] == 'Output Node')
    res['b_attribut_lu'] = C.ue(c, 't5_attribut.py', {'graphe': g})['resultat']
    # la broche de sortie du Load PCG Data Asset porte le libelle stocke dans l'asset ('In' : broche du Save)
    broche = res['b_attribut_lu']['pins_sortie']['Charger_Points'][0]
    res['b_broche_load'] = broche
    c.call_tool(PCGT, 'ConnectNodePins', {'fromNode': {'refPath': n_load}, 'fromPinLabel': broche,
                                         'toNode': {'refPath': n_sms}, 'toPinLabel': 'In'})
    c.call_tool(PCGT, 'ConnectNodePins', {'fromNode': {'refPath': n_sms}, 'fromPinLabel': 'Out',
                                         'toNode': {'refPath': sortie}, 'toPinLabel': 'Out'})
    c.call_tool(PCGT, 'SetGraphDescription', {'graph': {'refPath': g}, 'description':
                'Phase 0, voie (b) : PCGDataAsset (cuit depuis pj_points/0.1 par pj_tools.charger_points) '
                '-> Load PCG Data Asset -> Static Mesh Spawner (MeshSelectorByAttribute, attribut Mesh).'})
    c.pj('save_all')
    vb = _volume(c, g, 'PJ_PCG_Points_Test')
    res['b_volume'] = vb
    res['b_execution'] = _executer(c, vb, js, ech)

    # ---- voie (a) : Python Data Processor dans le graphe d'execution (construit en Python)
    ga = res['preparation']['graphe_a']
    va = _volume(c, ga, 'PJ_PCG_Points_Test_PDP')
    res['a_volume'] = va
    res['a_execution'] = _executer(c, va, js, ech)
    res['a_graphe_structure'] = c.call_tool(PCGT, 'GetGraphStructure', {'graph': {'refPath': ga}})
    # (a) et (b) posent les memes arbres : on retire (a) du niveau, (b) reste
    res['a_retrait'] = C.ue(c, 't5_retirer_volume.py', {'volume': va})['resultat']

    # ---- description du graphe retenu (versionnee)
    res['b_graphe_structure'] = c.call_tool(PCGT, 'GetGraphStructure', {'graph': {'refPath': g}})
    desc = {
        'graphe': 'PG_Points_Test', 'asset': g, 'route_retenue': 'b',
        'description': 'pj_points/0.1 (JSON) -> pj_tools.charger_points (cuisson par le graphe outil '
                       '/Game/PJ/PCG/Outils/PG_Cuisson_Points : Python Data Processor -> Save PCG Data Asset) -> '
                       f'{PDA} -> Load PCG Data Asset -> Static Mesh Spawner (PCGMeshSelectorByAttribute, Mesh)',
        'construction_mcp': [
            {'outil': 'CreateGraph', 'args': {'name': 'PG_Points_Test', 'path': '/Game/PJ/PCG'},
             'note': 'seulement si le graphe n existe pas ; sinon vide par t5_preparer et reutilise'},
            {'outil': 'AddNode', 'args': {'nativeNodeType': 'Load PCG Data Asset', 'nodeName': 'Charger_Points',
                                          'jsonParams': {'asset': {'refPath': f'{PDA}.PDA_Points_Test'},
                                                         'bSynchronousLoad': True}}},
            {'outil': 'AddNode', 'args': {'nativeNodeType': 'Static Mesh Spawner', 'nodeName': 'Poser_Meshes',
                                          'jsonParams': {'meshSelectorType': {
                                              'refPath': '/Script/PCG.PCGMeshSelectorByAttribute'}}}},
            {'outil': 'UpdateNode', 'args': {'node': 'Poser_Meshes',
                                             'jsonParams': {'meshSelectorParameters': {'attributeName': 'Mesh'}}},
             'resultat': 'refuse par PCGToolset (sous-objet instancie) ; repli Python : '
                         'settings.mesh_selector_parameters.attribute_name = Mesh (tests_phase0/ue/t5_attribut.py)'},
            {'outil': 'ConnectNodePins', 'args': ['Charger_Points.In (libelle de broche stocke dans l asset)', 'Poser_Meshes.In']},
            {'outil': 'ConnectNodePins', 'args': ['Poser_Meshes.Out', 'Output.Out']},
            {'outil': 'SpawnGraphInstance', 'args': {'name': 'PJ_PCG_Points_Test', 'scale': [25, 25, 10]}},
            {'outil': 'ExecuteGraphInstance'}],
        'reglage_attribut': res['b_attribut_lu'],
        'mesures': {k: res['b_execution']['verif'][k] for k in ('nb_instances', 'manquants', 'd_pos_max_cm',
                                                               'd_yaw_max_deg', 'd_rot_max_deg', 'd_s_max',
                                                               'mesh_faux')},
        'structure': res['b_graphe_structure'],
        'variante_a': {'graphe': ga, 'structure': res['a_graphe_structure'],
                       'script': f'{GRAPHES}/PG_Points_Test_PDP_lire.py'},
        'cuisson': {'graphe_outil': '/Game/PJ/PCG/Outils/PG_Cuisson_Points', 'outil_mcp': 'pj_tools.charger_points'},
    }
    with open(f'{GRAPHES}/PG_Points_Test.json', 'w', encoding='utf-8') as f:
        json.dump(desc, f, ensure_ascii=False, indent=1)
    c.pj('save_all')
    res['captures'] = {
        't5_pcg_vue_haute': C.capture(c, 't5_pcg_vue_haute', (-1.5, -95.0, 60.0), 90, -35, 80),
        't5_pcg_vue_rue': C.capture(c, 't5_pcg_vue_rue', (-25.0, -22.0, 1.6), 50, 3, 75),
    }
    C.ecrire_json('t5_points_pcg.json', res)
    return res


HDA = f'{C.ICI}/hda/pj_test_boite.hdalc'.replace('\\', '/')
JOURNAL_UE = 'D:/ClaudeADAS/Saved/Logs/ClaudeADAS.log'


def t6(c, **_):
    """Houdini Engine : HDA trivial (boite, .hdalc cree par hython) cuit dans UE en licence Indie."""
    args = {'niveau': C.NIVEAU, 'hda': HDA, 'dossier': '/Game/PJ/Houdini', 'label': 'PJ_HDA_Boite',
            'x': -30.0, 'y': 10.0, 'taille': [3.0, 1.2, 0.6], 'log': JOURNAL_UE}
    res = {'essai': 't6', 'date': C.horodatage(), 'hda': HDA}
    res['nettoyer'] = C.ue(c, 't6_houdini.py', {**args, 'mode': 'nettoyer'})['resultat']
    time.sleep(3.0)                                   # destruction HAPI asynchrone de l'instance precedente
    t0 = time.time()
    res['lancer'] = C.ue(c, 't6_houdini.py', {**args, 'mode': 'lancer'})['resultat']
    e = {}
    while time.time() - t0 < 120:
        e = C.ue(c, 't6_houdini.py', {**args, 'mode': 'etat'})['resultat']
        meshes = [o for s in e.get('sorties', []) for o in s['objets'] if o.get('classe') == 'StaticMesh']
        sm = [k for k in e.get('composants', []) if k['classe'] == 'StaticMeshComponent' and k['visible']]
        if e.get('params_appliques') and meshes and sm and abs(sm[0]['demi_etendue_cm'][0] - 50 * args['taille'][0]) < 1.0:
            break
        time.sleep(2.0)
    res['etat'] = e
    res['duree_s'] = round(time.time() - t0, 1)
    # licence : le serveur de licences local liste le processus HARS (session Houdini Engine hors processus)
    import subprocess
    hs = 'C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hserver.exe'
    try:
        res['hserver_l'] = subprocess.run([hs, '-l'], capture_output=True, text=True, timeout=60).stdout.splitlines()
    except Exception as ex:  # noqa: BLE001
        res['hserver_l'] = repr(ex)
    # attendu (UE, cm) : X = 100 tx, Y = 100 tz, Z = 100 ty (Houdini Y-haut -> UE Z-haut), base a z = 0
    tx, ty, tz = args['taille']
    res['attendu_demi_etendue_cm'] = [50 * tx, 50 * tz, 50 * ty]
    res['attendu_centre_cm'] = [args['x'] * 100, -args['y'] * 100, 50 * ty]
    sm = [k for k in e.get('composants', []) if k['classe'] == 'StaticMeshComponent' and k['visible']]
    if sm:
        res['ecart_cm'] = max(max(abs(a - b) for a, b in zip(sm[0]['demi_etendue_cm'], res['attendu_demi_etendue_cm'])),
                              max(abs(a - b) for a, b in zip(sm[0]['centre_cm'], res['attendu_centre_cm'])))
    c.pj('save_all')
    res['capture'] = C.capture(c, 't6_houdini_boite', (-30.0, 4.0, 1.8), 90, -8, 60)
    C.ecrire_json('t6_houdini.json', res)
    return res


def _mesure(img, pts, r=8):
    """Moyenne lineaire de fenetres (2r+1)^2 centrees sur les pixels pts (image 8 bits sRGB decodee,
    tableau flottant suppose deja lineaire)."""
    import numpy as np
    a = np.asarray(img)
    if a.dtype == np.uint8:
        a = a.astype(np.float64) / 255.0
        a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    vals = []
    for u, v in pts:
        u, v = int(round(u)), int(round(v))
        if not (r <= u < a.shape[1] - r and r <= v < a.shape[0] - r):
            raise ValueError(f'point hors image : {u},{v}')
        vals.append(a[v - r:v + r + 1, u - r:u + r + 1, :3].mean(axis=(0, 1)))
    return np.array(vals)


def t7(c, ev=None, **_):
    """Non-regression de high_res_capture (Lumen) et controle de la lumiere du ciel : boite haute sur le sol neutre ;
    a la meme pose, rapport ombre/soleil (luminance lineaire apres courbe de ton, sol 18 %) dans
    [eclairage.OMBRE_SOLEIL_MIN ; OMBRE_SOLEIL_MAX] (0,18-0,32 : ciel clair de vallee), canal R >= OMBRE_SOLEIL_R_MIN
    (ombres gris-bleu, pas bleu marine), et a moins de 20 % de celui de EditorAppToolset.CaptureViewport."""
    import numpy as np
    from PIL import Image
    r = C.ue(c, 't7_boite_ombre.py', {'niveau': C.NIVEAU})['resultat']
    cam, yaw, pitch = r['camera']['p'], r['camera']['yaw_deg'], r['camera']['pitch_deg']
    res = {'essai': 't7', 'date': C.horodatage(), 'scene': r, 'ev100': C.EV100 if ev is None else ev,
           'critere': {'rapport_min': E.OMBRE_SOLEIL_MIN, 'rapport_max': E.OMBRE_SOLEIL_MAX,
                       'rapport_r_min': E.OMBRE_SOLEIL_R_MIN, 'ecart_rel_max': 0.20}}
    vp = C.capture_viewport(c, 't7_viewport', cam, yaw, pitch)
    hrc = C.capture(c, 't7_capture', cam, yaw, pitch, vp['fov'], w=vp['largeur'], h=vp['hauteur'],
                    ev100=C.EV100 if ev is None else ev)
    res['viewport'], res['capture'] = vp, hrc
    po = C.projeter(r['points_ombre'], cam, yaw, pitch, vp['fov'], vp['largeur'], vp['hauteur'])
    ps = C.projeter(r['points_soleil'], cam, yaw, pitch, vp['fov'], vp['largeur'], vp['hauteur'])
    res['pixels'] = {'ombre': po, 'soleil': ps}
    exr = C.lire_exr(hrc['exr'])
    images = {'viewport': Image.open(vp['png']).convert('RGB'), 'capture_png': Image.open(hrc['png']).convert('RGB'),
              'capture_exr': np.stack([exr['R'], exr['G'], exr['B']], -1)}
    m = {}
    for nom, im in images.items():
        o, s_ = _mesure(im, po), _mesure(im, ps)
        lum = lambda x: x @ np.array([0.2126, 0.7152, 0.0722])  # noqa: E731
        m[nom] = {'ombre_rgb': o.mean(0).round(5).tolist(), 'soleil_rgb': s_.mean(0).round(5).tolist(),
                  'rapport': float(lum(o).mean() / lum(s_).mean()),
                  'rapport_rgb': (o.mean(0) / s_.mean(0)).round(4).tolist()}
    res['mesures'] = m
    rv, rc = m['viewport']['rapport'], m['capture_png']['rapport']
    res['ecart_rel'] = abs(rc - rv) / rv
    rr = m['capture_png']['rapport_rgb'][0]
    res['controles'] = {'capture_vs_viewport': res['ecart_rel'] <= 0.20,
                        'ombre_soleil': E.OMBRE_SOLEIL_MIN <= rc <= E.OMBRE_SOLEIL_MAX,
                        'ombre_canal_r': rr >= E.OMBRE_SOLEIL_R_MIN}
    res['ok'] = all(res['controles'].values())
    C.ecrire_json('t7_capture_lumen.json', res)
    return res


ESSAIS = {'t1': t1, 't2': t2, 't3': t3, 't4': t4, 't5': t5, 't6': t6, 't7': t7}


def main(argv):
    kw = dict(a.split('=', 1) for a in argv if '=' in a)
    argv = [a for a in argv if '=' not in a]
    noms = list(ESSAIS) if not argv or argv[0] == 'tout' else argv
    c = C.client()
    try:
        for n in noms:
            r = ESSAIS[n](c, **{k: float(v) for k, v in kw.items()})
            print(json.dumps(r, ensure_ascii=False, indent=1, default=str)[:8000])
    finally:
        c.fermer()


if __name__ == '__main__':
    main(sys.argv[1:])
