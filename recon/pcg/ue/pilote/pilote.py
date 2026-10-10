"""Pilote ZP-01 dans Unreal 5.8 (cote client, editeur ouvert, MCP) : niveau PJ_2026, imports USD, bibliotheque des
bordures, PCG, captures aux 6 poses de controle et planches Karma | UE.

    python recon/pcg/ue/pilote/pilote.py tout
    python recon/pcg/ue/pilote/pilote.py niveau | imports | bordures [--bibliotheque] | captures [a b ...] | joints |
                                         planche | inventaire

Entree : recon/out/paquet_jardin/v2/fabrique_ue_snapshot (instantane de fabrique/, regenerable :
hython recon/pcg/houdini/fabriquer.py --sortie ... --sans-cameras). Sorties : recon/out/paquet_jardin/v2/ue_pilote/
(rapports JSON, points/bordures_ue.json, captures ue_<v>_1920x1080 et ue_<v>_1000 en PNG + EXR, planche_*.png).
Scripts editeur : ue/*.py (pj_tools.run_python_file). Reference d'eclairage : pj_tools/eclairage.py (EV100 14).
"""
from __future__ import annotations

import json
import os
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))                              # recon/pcg/ue -> mcp_client
sys.path.insert(0, os.path.join(os.path.dirname(ICI), 'pj_tools'))    # eclairage
sys.path.insert(0, ICI)

from mcp_client import McpClient, McpErreur  # noqa: E402
from pj_tools import eclairage  # noqa: E402
import cameras  # noqa: E402
import points_ue  # noqa: E402

DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..')).replace('\\', '/')
V2 = f'{DEPOT}/recon/out/paquet_jardin/v2'
FABRIQUE = f'{V2}/fabrique_ue_snapshot'
OUT = f'{V2}/ue_pilote'
KARMA = f'{DEPOT}/recon/pc/rendus/v2_pilote'
UE = f'{ICI}/ue'.replace('\\', '/')
PDA = '/Game/PJ/PCG/Donnees/PDA_Bordures'
# couches importees (pj_tools.import_usd, contexte unreal, Nanite : remplissages deplaces, eclats instancies)
COUCHES = [('sol.usda', '/Game/PJ/Import/Sol'), ('decals_sol.usda', '/Game/PJ/Import/Decals'),
           ('ilots.usda', '/Game/PJ/Import/Ilots'), ('ilots_couverture.usdc', '/Game/PJ/Import/Ilots')]
# (largeur, hauteur, suffixe, exposition locale) : 1920 x 1080 = reference neutre (capteurs, mesures) ; 1000 = vignettes des
# planches, exposition locale (eclairage.EXPOSITION_LOCALE_PLANCHES ; revue UE du 10/10 : ombres bouchees a EV 14 fixe)
TAILLES = [(1920, 1080, '1920x1080', False), (1000, 1000, '1000', True)]
# gros plans des joints (6 mm) : joint sombre en retrait (bordure neuve K-0369), mortier clair a fleur (ceinture
# A2 de l'ilot BRF K-0417, T2 K-0386)
JOINTS = ['K-0369/J004', 'K-0417/J002', 'K-0386/J004']


def ecrire(nom: str, obj) -> str:
    os.makedirs(OUT, exist_ok=True)
    chemin = f'{OUT}/{nom}'
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return chemin


def ue(c: McpClient, script: str, args: dict | None = None, timeout: float = 1800.0):
    r = c.pj('run_python_file', {'path': f'{UE}/{script}', 'args_json': json.dumps(args or {})}, timeout=timeout)
    if not isinstance(r, dict) or not r.get('ok'):
        raise McpErreur(f'{script} : {json.dumps(r, ensure_ascii=False)[-4000:]}')
    return r['resultat']


def etape_niveau(c):
    t0 = time.time()
    # plan de contexte sous le terrain v1 et le sol lointain (comme contexte.py materiaux : -4,1 m, MI lointain)
    r = {'materiaux_maison': ue(c, 'materiaux_maison.py'),
         'niveau': ue(c, 'niveau_2026.py', {'contexte_z_m': -4.1, 'contexte_mi': '/Game/PJ/Materials/MI_PJ_Contexte_Lointain'})}
    r['duree_s'] = round(time.time() - t0, 1)
    return ecrire('niveau.json', r)


def etape_imports(c):
    # acteurs d'un import precedent retires d'abord (un reimport REPLACE double les entrees du niveau)
    rapport = {'retrait': ue(c, 'retirer_imports.py', {'racines': [f.split('.')[0] for f, _ in COUCHES]})}
    for fichier, dest in COUCHES:
        r = c.pj('import_usd', {'usd_path': f'{FABRIQUE}/{fichier}', 'dest_path': dest, 'render_context': 'unreal',
                                'nanite': True}, timeout=1800)
        if not r.get('ok'):
            raise McpErreur(f'import {fichier} : {r}')
        rapport[fichier] = {k: r.get(k) for k in ('nb', 'acceptation', 'journal', 'duree_s', 'options_refusees')}
        rapport[fichier]['meshes'] = [{k: m[k] for k in ('mesh', 'uv', 'nanite', 'recompute_normals', 'use_full_precision_u_vs',
                                                       'materiaux')} for m in r.get('meshes', [])]
    rapport['inventaire'] = ue(c, 'inventaire.py')
    rapport['collisions'] = ue(c, 'collisions.py', {'etape': 'appliquer'})     # revue UE du 10/10 : tout en NoCollision
    return ecrire('imports.json', rapport)


def etape_bordures(c, bibliotheque=None):
    """bibliotheque : None = importer les prototypes si /Game/PJ/Lib/Bordures n'a pas tous les SM (premier import
    ~1,5 min ; reimport force ~11 min : suppression puis remplacement des 253 assets)."""
    t0 = time.time()
    index = json.load(open(f'{FABRIQUE}/prototypes/index.json', encoding='utf-8'))['prototypes']
    if bibliotheque is None:
        n = c.pj('list_assets', {'path': '/Game/PJ/Lib/Bordures', 'recursive': False}).get('nb', 0)
        bibliotheque = n < len(index)
    r = {'bibliotheque': ue(c, 'bibliotheque_bordures.py', {'fabrique': FABRIQUE}) if bibliotheque else 'deja importee'}
    r['points'] = points_ue.principal(FABRIQUE, f'{OUT}/points/bordures_ue.json')
    pts = r['points']['sortie'].replace('\\', '/')
    c.pj('charger_points', {'json_path': pts, 'asset_path': PDA})
    for _ in range(120):
        e = c.pj('charger_points', {'json_path': pts, 'asset_path': PDA, 'etat_seulement': True})
        if e.get('fini'):
            break
        time.sleep(0.5)
    r['cuisson'] = e
    r['generation'] = ue(c, 'pg_bordures.py', {'etape': 'generer'})
    for _ in range(60):                                  # generation PCG asynchrone (quelques images)
        time.sleep(1.0)
        v = ue(c, 'pg_bordures.py', {'etape': 'verifier', 'points': pts}) if _ else None
        if v and v['instances'] == v['points']:
            break
    r['verification'] = v
    r['collisions'] = ue(c, 'collisions.py', {'etape': 'appliquer'})
    r['duree_s'] = round(time.time() - t0, 1)
    c.pj('save_all', {})
    return ecrire('bordures.json', r)


def capture(c, png: str, pose: dict, w: int, h: int, warmup: int = 48, max_s: float = 900.0,
            exposition_locale: bool = False) -> dict:
    r = c.pj('high_res_capture', {'out_png': png, **{k: pose[k] for k in ('cam_x_m', 'cam_y_m', 'cam_z_m', 'yaw_deg',
                                                                            'pitch_deg', 'fov_deg')},
                                  'width': w, 'height': h, 'warmup': warmup, 'ev100': eclairage.EV100,
                                  'exposition_locale': bool(exposition_locale)}, timeout=900)
    t0 = time.time()
    while isinstance(r, dict) and r.get('ok') and r.get('en_cours') and time.time() - t0 < max_s:
        time.sleep(0.5)
        r = c.pj('high_res_capture_etat', {'out_png': png}, timeout=300)
    if not isinstance(r, dict) or not r.get('ok') or not r.get('fini'):
        raise McpErreur(f'capture {png} : {r}')
    return r


def etape_captures(c, vues=None):
    poses = cameras.poses()
    rapport = {}
    for v in vues or sorted(poses):
        for w, h, suffixe, locale in TAILLES:
            png = f'{OUT}/ue_{v}_{suffixe}.png'
            r = capture(c, png, poses[v], w, h, exposition_locale=locale)
            rapport[f'ue_{v}_{suffixe}'] = {'pose': poses[v], 'png': png, 'exr': r.get('exr'), 'ev100': r.get('ev100'),
                                            'exposition_locale': locale, 'moyenne_srgb': r.get('moyenne'),
                                            'duree_s': r.get('duree_s')}
    chemin = f'{OUT}/captures.json'
    ancien = json.load(open(chemin, encoding='utf-8')) if os.path.exists(chemin) else {}
    ancien.update(rapport)
    return ecrire('captures.json', ancien)


def etape_joints(c):
    pts = json.load(open(f'{FABRIQUE}/points/bordures.json', encoding='utf-8'))
    rapport = {}
    for jid in JOINTS:
        pose = cameras.pose_joint(pts, jid)
        png = f"{OUT}/ue_joints_{jid.replace('/', '_')}.png"
        r = capture(c, png, pose, 1600, 1000)
        rapport[jid] = {'pose': pose, 'png': png, 'exr': r.get('exr'), 'moyenne_srgb': r.get('moyenne')}
    return ecrire('captures_joints.json', rapport)


def etape_planche():
    import planche
    return planche.principal()


def main(argv):
    etape = argv[0] if argv else 'tout'
    if etape == 'planche':
        print(etape_planche())
        return
    with McpClient() as c:
        if etape in ('niveau', 'tout'):
            print(etape_niveau(c))
        if etape in ('imports', 'tout'):
            print(etape_imports(c))
        if etape in ('bordures', 'tout'):
            print(etape_bordures(c, True if '--bibliotheque' in argv else None))
        if etape in ('captures', 'tout'):
            print(etape_captures(c, argv[1:] or None))
        if etape in ('joints', 'tout'):
            print(etape_joints(c))
        if etape == 'inventaire':
            print(json.dumps(ue(c, 'inventaire.py'), ensure_ascii=False, indent=1))
        c.pj('save_all', {})
    if etape == 'tout':
        print(etape_planche())


if __name__ == '__main__':
    main(sys.argv[1:])
