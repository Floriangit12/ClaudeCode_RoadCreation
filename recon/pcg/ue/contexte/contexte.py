"""Contexte du pilote dans Unreal 5.8 (cote client, editeur ouvert, MCP) : tout ce qui entoure et habille la zone
pilote ZP-01 dans /Game/PJ/Maps/PJ_2026 (carrefour de banlieue francaise, mi-octobre).

    python recon/pcg/ue/contexte/contexte.py tout
    python recon/pcg/ue/contexte/contexte.py usd | materiaux | imports | arbres | herbe | clotures | mobilier | feuilles |
                                             perf [vues...] | captures [vues...] | panoramax | revue [vues...] |
                                             planches | inventaire

Etapes :
- usd        lointain.py (cadastre et arbres publics hors du carre v1, pyproj) puis hython preparer_usd.py : contexte v1
             hors emprise (sol, bordures, marquages, batiments ; masque du pilote), batiments lointains, zones
             d'echantillonnage PCG, Z du sol sous les objets -> ue_pilote/usd/ (ignore par git) ; horizon.py (profil de
             l'horizon de montagnes releve sur les photos 360) puis hython relief_usd.py (relief.usdc : anneau de relief
             de 3 a 35 km, sol lointain raccorde au bord du terrain v1) ; contrat verifie
- materiaux  ue/materiaux_contexte.py (M_PJ_Facade + 6 MI, MI_bordure_v1, MI_PJ_Contexte_Lointain) ; plan de contexte
             du niveau abaisse sous le terrain v1 (niveau_2026.py, contexte_z_m = -4,1, MI_PJ_Contexte_Lointain)
- imports    pj_tools.import_usd contexte_v1.usdc, lointain.usdc et relief.usdc (kinds_to_collapse 2 : un SM par tuile /
             batiment / secteur, Nanite) et zones_pcg.usdc (assets seulement : acteurs retires) ; collisions
             (pilote/ue/collisions.py)
- arbres     vegetation/arbres.py -> points/arbres_ue.json + tuteurs_ue.json (+ arbres_lointains_ue.json, lointain.py) ->
             PDA -> PG_Arbres (volume PJ_PCG_Arbres)
- herbe      ue/pg_herbe.py : PG_Herbe (PCGMeshSampler sur les zones : gazon ras proche / lointain, herbe haute,
             massifs, feuilles CARLA eparses) ; controle_herbe.py (hython) : distance des touffes aux bordures v2 / v1
- clotures   clotures.py (lignes d'instances.json) -> points/clotures_ue.json -> PG_Clotures
- mobilier   mobilier.py : substituts CARLA des lampadaires, poteaux bois et potelets v1 -> PG_Mobilier
- feuilles   ue/feuilles.py : decalques de feuilles mortes sous les feuillus (DBuffer) ; arbres et buissons sans decalque
- perf       ue/perf.py : temps d'image et GPU (ProfileGPU) en rendu 1920 x 1080 aux poses de controle (PIE)
- captures   6 vues du pilote + 4 vues de controle v1 (recon/pc/houdini/cameras.usda) -> ue_pilote/ctx_<vue>_*.png|exr
- panoramax  poses Panoramax 360 (e5d79de9, 9834f494) -> vues UE + recadrages gnomoniques des photos -> planches
- revue      vues a hauteur de pieton (VUES_REVUE) -> ue_pilote/revue_<vue>.png|exr
- planches   planche_contexte_*.png
Sorties : recon/out/paquet_jardin/v2/ue_pilote/ (contexte_*.json, points/, captures, planches).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
UE_DIR = os.path.dirname(ICI)
sys.path.insert(0, UE_DIR)                                            # mcp_client
sys.path.insert(0, os.path.join(UE_DIR, 'pj_tools'))                   # eclairage
sys.path.insert(0, os.path.join(UE_DIR, 'pilote'))                     # cameras, pilote
sys.path.insert(0, os.path.join(UE_DIR, 'vegetation'))
sys.path.insert(0, ICI)

from mcp_client import McpClient, McpErreur  # noqa: E402
from pj_tools import eclairage  # noqa: E402
import cameras  # noqa: E402

DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..')).replace('\\', '/')
V2 = f'{DEPOT}/recon/out/paquet_jardin/v2'
OUT = f'{V2}/ue_pilote'
USD = f'{OUT}/usd'
PTS = f'{OUT}/points'
HYTHON = 'C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe'
UE = f'{ICI}/ue'.replace('\\', '/')
PILOTE_UE = f'{UE_DIR}/pilote/ue'.replace('\\', '/')
VEG_UE = f'{UE_DIR}/vegetation/ue'.replace('\\', '/')
SITE = [-150.0, -150.0, 150.0, 150.0]
CAMERAS_V1 = f'{DEPOT}/recon/pc/houdini/cameras.usda'
TAILLES = [(1920, 1080, '1920x1080', False), (1000, 1000, '1000', True)]     # comme pilote.TAILLES (1000 : planches)


def ecrire(nom: str, obj) -> str:
    os.makedirs(OUT, exist_ok=True)
    chemin = f'{OUT}/{nom}'
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return chemin


def ue(c: McpClient, script: str, args: dict | None = None, timeout: float = 3600.0):
    r = c.pj('run_python_file', {'path': script, 'args_json': json.dumps(args or {})}, timeout=timeout)
    if not isinstance(r, dict) or not r.get('ok'):
        raise McpErreur(f'{script} : {json.dumps(r, ensure_ascii=False)[-4000:]}')
    return r['resultat']


def cuire(c: McpClient, json_path: str, pda: str) -> dict:
    c.pj('charger_points', {'json_path': json_path, 'asset_path': pda})
    e = {}
    for _ in range(600):
        e = c.pj('charger_points', {'json_path': json_path, 'asset_path': pda, 'etat_seulement': True})
        if e.get('fini'):
            break
        time.sleep(0.5)
    return e


# ------------------------------------------------------------------ etapes
def etape_usd():
    t0 = time.time()
    import lointain
    loin = lointain.principal()                       # cadastre + arbres publics hors du carre v1 (pyproj)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([HYTHON, f'{ICI}/preparer_usd.py', '--sortie', USD], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, cwd=DEPOT)
    if r.returncode:
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
    rap = json.load(open(f'{USD}/preparation.json', encoding='utf-8'))
    rap['lointain_entrees'] = loin
    rap['duree_totale_s'] = round(time.time() - t0, 1)
    # horizon de montagnes (revue UE du 10/10) : profil releve sur les photos 360, anneau de relief et sol lointain
    import horizon
    rap['horizon'] = horizon.principal()
    r = subprocess.run([HYTHON, f'{ICI}/relief_usd.py', '--sortie', USD], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, cwd=DEPOT)
    if r.returncode:
        raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
    rap['relief'] = json.load(open(f'{USD}/relief.json', encoding='utf-8'))
    rap['relief'].pop('profil', None)
    rap['contrat'] = {}
    for nom in ('contexte_v1', 'lointain', 'zones_pcg', 'relief'):
        subprocess.run([HYTHON, f'{UE_DIR}/contrat/verifier_usd.py', f'{USD}/{nom}.usdc', '--json', f'{USD}/contrat_{nom}.json'],
                       capture_output=True, text=True, env=env, cwd=DEPOT)
        ver = json.load(open(f'{USD}/contrat_{nom}.json', encoding='utf-8'))
        rap['contrat'][nom] = {'ok': ver['ok'], 'erreurs': len(ver['erreurs']), 'avertissements': len(ver['avertissements'])}
    return ecrire('contexte_usd.json', rap)


def etape_materiaux(c):
    r = {'materiaux': ue(c, f'{UE}/materiaux_contexte.py'),
         'niveau': ue(c, f'{PILOTE_UE}/niveau_2026.py', {'contexte_z_m': -4.1,
                                                         'contexte_mi': '/Game/PJ/Materials/MI_PJ_Contexte_Lointain'})}
    return ecrire('contexte_materiaux.json', r)


def etape_imports(c):
    rapport = {'retrait': ue(c, f'{PILOTE_UE}/retirer_imports.py', {'racines': ['contexte_v1', 'lointain', 'zones_pcg',
                                                                                 'relief']})}
    for fichier, dest in (('contexte_v1.usdc', '/Game/PJ/Import/Contexte'), ('lointain.usdc', '/Game/PJ/Import/Lointain'),
                          ('zones_pcg.usdc', '/Game/PJ/Import/Zones'), ('relief.usdc', '/Game/PJ/Import/Relief')):
        r = c.pj('import_usd', {'usd_path': f'{USD}/{fichier}', 'dest_path': dest, 'render_context': 'unreal',
                                'kinds_to_collapse': 2, 'nanite': not fichier.startswith('zones')}, timeout=3600)
        if not r.get('ok'):
            raise McpErreur(f'import {fichier} : {json.dumps(r)[:3000]}')
        rapport[fichier] = {k: r.get(k) for k in ('nb', 'acceptation', 'duree_s', 'options', 'options_refusees')}
        rapport[fichier]['journal'] = (r.get('journal') or [])[:40] if isinstance(r.get('journal'), list) else r.get('journal')
        ms = r.get('meshes', [])
        rapport[fichier]['meshes'] = {'nb': len(ms), 'nanite': sum(bool(m.get('nanite')) for m in ms),
                                      'recompute_normals': sum(bool(m.get('recompute_normals')) for m in ms),
                                      'uv_min': min((m.get('uv') or 0 for m in ms), default=None)}
    rapport['zones_acteurs_retires'] = ue(c, f'{PILOTE_UE}/retirer_imports.py', {'racines': ['zones_pcg']})
    rapport['inventaire'] = ue(c, f'{PILOTE_UE}/inventaire.py')
    rapport['collisions'] = ue(c, f'{PILOTE_UE}/collisions.py', {'etape': 'appliquer'})
    c.pj('save_all', {})
    return ecrire('contexte_imports.json', rapport)


def etape_arbres(c):
    import arbres
    t0 = time.time()
    r = {'points': arbres.principal(PTS)}
    r['points'].pop('ignores_detail', None)
    pda = {'arbres': 'PDA_Arbres', 'tuteurs': 'PDA_Tuteurs', 'arbres_lointains': 'PDA_Arbres_Lointains'}
    r['cuisson'] = {nom: cuire(c, f'{PTS}/{nom}_ue.json', f'/Game/PJ/PCG/Donnees/{p}') for nom, p in pda.items()}
    # site (arbres + tuteurs) et lointain (arbres publics hors du carre v1, sans ombre portee : cout des ombres virtuelles
    # des feuillages non Nanite) dans deux volumes, donc dans des ISM distincts
    graphes = [
        ({'graphe': '/Game/PJ/PCG/PG_Arbres', 'volume': 'PJ_PCG_Arbres', 'zone': SITE,
          'branches': [{'pda': '/Game/PJ/PCG/Donnees/PDA_Arbres'}, {'pda': '/Game/PJ/PCG/Donnees/PDA_Tuteurs', 'materiau': True}],
          'description': 'Arbres du site : points pj_points (vegetation/arbres.py, correspondance_carla.json) -> '
                         'Static Mesh Spawner (Mesh) ; tuteurs (Materiau) ; recon/pcg/ue/contexte/ue/pg_points.py'},
         [f'{PTS}/arbres_ue.json', f'{PTS}/tuteurs_ue.json']),
        ({'graphe': '/Game/PJ/PCG/PG_Arbres_Lointains', 'volume': 'PJ_PCG_Arbres_Lointains', 'zone': [-700.0, -700.0, 700.0, 700.0],
          'branches': [{'pda': '/Game/PJ/PCG/Donnees/PDA_Arbres_Lointains'}], 'sans_ombre': True,
          'description': 'Arbres publics hors du carre v1 (contexte/lointain.py) : Static Mesh Spawner (Mesh), sans ombre portee'},
         [f'{PTS}/arbres_lointains_ue.json'])]
    r['generation'], r['verification'] = {}, {}
    for args, fichiers in graphes:
        r['generation'][args['volume']] = ue(c, f'{UE}/pg_points.py', dict(args, etape='generer'))
        v = None
        for _ in range(60):
            time.sleep(1.0)
            v = ue(c, f'{UE}/pg_points.py', dict(args, etape='verifier', points=fichiers))
            if v['egalite']:
                break
        r['verification'][args['volume']] = v
    r['duree_s'] = round(time.time() - t0, 1)
    c.pj('save_all', {})
    return ecrire('contexte_arbres.json', r)


def etape_herbe(c):
    r = ue(c, f'{UE}/pg_herbe.py', {'etape': 'generer'})
    v = {}
    for _ in range(120):                                  # generation PCG asynchrone
        time.sleep(2.0)
        v = ue(c, f'{UE}/pg_herbe.py', {'etape': 'verifier'})
        if v['instances'] and v['instances'] == r.get('_dernier'):
            break
        r['_dernier'] = v['instances']
    r.pop('_dernier', None)
    r['verification'] = v
    # controle d'exclusion : distance en plan des touffes et buissons aux bordures v2 et v1 (>= 0,15 m)
    pos = f'{USD}/positions_herbe.json'
    r['positions'] = ue(c, f'{UE}/positions_herbe.py', {'sortie': pos})
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([HYTHON, f'{ICI}/controle_herbe.py', pos, f'{OUT}/contexte_herbe_controle.json'], capture_output=True,
                   text=True, env=env, cwd=DEPOT)
    r['controle'] = json.load(open(f'{OUT}/contexte_herbe_controle.json', encoding='utf-8'))['total']
    c.pj('save_all', {})
    return ecrire('contexte_herbe.json', r)


def etape_clotures(c):
    import clotures
    r = {'points': clotures.principal(PTS)}
    r['cuisson'] = cuire(c, f'{PTS}/clotures_ue.json', '/Game/PJ/PCG/Donnees/PDA_Clotures')
    args = {'graphe': '/Game/PJ/PCG/PG_Clotures', 'volume': 'PJ_PCG_Clotures', 'zone': SITE,
            'branches': [{'pda': '/Game/PJ/PCG/Donnees/PDA_Clotures'}],
            'description': 'Clotures v1 (instances.json lignes) : panneaux CARLA le long des polylignes ; contexte/clotures.py'}
    r['generation'] = ue(c, f'{UE}/pg_points.py', dict(args, etape='generer'))
    time.sleep(2.0)
    r['verification'] = ue(c, f'{UE}/pg_points.py', dict(args, etape='verifier', points=[f'{PTS}/clotures_ue.json']))
    c.pj('save_all', {})
    return ecrire('contexte_clotures.json', r)


def etape_mobilier(c):
    import mobilier
    r = {'points': mobilier.principal(PTS)}
    r['cuisson'] = cuire(c, f'{PTS}/mobilier_ue.json', '/Game/PJ/PCG/Donnees/PDA_Mobilier')
    args = {'graphe': '/Game/PJ/PCG/PG_Mobilier', 'volume': 'PJ_PCG_Mobilier', 'zone': SITE,
            'branches': [{'pda': '/Game/PJ/PCG/Donnees/PDA_Mobilier'}],
            'description': 'Substituts CARLA du mobilier v1 (lampadaires, poteaux bois, potelets) ; contexte/mobilier.py'}
    r['generation'] = ue(c, f'{UE}/pg_points.py', dict(args, etape='generer'))
    time.sleep(2.0)
    r['verification'] = ue(c, f'{UE}/pg_points.py', dict(args, etape='verifier', points=[f'{PTS}/mobilier_ue.json']))
    c.pj('save_all', {})
    return ecrire('contexte_mobilier.json', r)


def etape_feuilles(c):
    r = ue(c, f'{UE}/feuilles.py', {'points': f'{PTS}/arbres_ue.json'})
    c.pj('save_all', {})
    return ecrire('contexte_feuilles.json', r)


def poses_controle() -> dict:
    """6 vues du pilote (cameras_v2_pilote.usda) + 4 vues de controle v1 (cameras.usda)."""
    p = cameras.poses()
    for n, cam in cameras.lire(CAMERAS_V1).items():
        p[n.split('_')[0]] = dict(cameras.pose_capture(cam), camera=n)
    return p


def capture(c, png: str, pose: dict, w: int, h: int, warmup: int = 48, exposition_locale: bool = False) -> dict:
    import pilote
    return pilote.capture(c, png, pose, w, h, warmup=warmup, exposition_locale=exposition_locale)


def etape_captures(c, vues=None):
    poses = poses_controle()
    rapport = {}
    for v in vues or list(poses):
        for w, h, suffixe, locale in TAILLES:
            png = f'{OUT}/ctx_{v}_{suffixe}.png'
            r = capture(c, png, poses[v], w, h, exposition_locale=locale)
            rapport[f'ctx_{v}_{suffixe}'] = {'pose': poses[v], 'png': png, 'exr': r.get('exr'), 'ev100': r.get('ev100'),
                                             'exposition_locale': locale, 'moyenne_srgb': r.get('moyenne'),
                                             'duree_s': r.get('duree_s')}
    chemin = f'{OUT}/contexte_captures.json'
    ancien = json.load(open(chemin, encoding='utf-8')) if os.path.exists(chemin) else {}
    ancien.update(rapport)
    return ecrire('contexte_captures.json', ancien)


# vues de revue a hauteur de pieton (test « photo a 10 m » de la revue UE du 10/10 ; horizon visible) : pose locale
# (x, y, z oeil, cap trigo depuis +x, site, champ)
VUES_REVUE = {
    'pieton_10m': dict(cam_x_m=33.0, cam_y_m=21.0, cam_z_m=1.75, yaw_deg=-127.6, pitch_deg=-4.0, fov_deg=60.0),
    'pieton_nord_est': dict(cam_x_m=20.0, cam_y_m=8.0, cam_z_m=1.75, yaw_deg=52.4, pitch_deg=-3.0, fov_deg=60.0),
    'pieton_ilot_gazon': dict(cam_x_m=44.6, cam_y_m=68.4, cam_z_m=1.65, yaw_deg=-42.8, pitch_deg=-8.0, fov_deg=60.0),
    'pieton_bev': dict(cam_x_m=13.6, cam_y_m=3.0, cam_z_m=1.6, yaw_deg=-10.0, pitch_deg=-38.0, fov_deg=55.0),
}


def etape_revue(c, vues=None):
    rapport = {}
    for v in vues or list(VUES_REVUE):
        png = f'{OUT}/revue_{v}.png'
        r = capture(c, png, VUES_REVUE[v], 1920, 1080)
        rapport[f'revue_{v}'] = {'pose': VUES_REVUE[v], 'png': png, 'exr': r.get('exr'), 'ev100': r.get('ev100'),
                                 'moyenne_srgb': r.get('moyenne'), 'duree_s': r.get('duree_s')}
    return ecrire('revue_captures.json', rapport)


LOG_UE = 'D:/ClaudeADAS/Saved/Logs/ClaudeADAS.log'


def profil_gpu(marque: str) -> dict:
    """Premier bloc ProfileGPU du journal apres la marque : temps d'image, GPU total (<root> inclusif), 12 premiers
    postes sous SceneRender (inclusif, ms) et resolution de la TSR."""
    import re
    txt = open(LOG_UE, encoding='utf-8', errors='replace').read()
    i = txt.rfind(f'PJ_PERF_MARQUE {marque}')
    if i < 0:
        return {'erreur': 'marque absente du journal'}
    j = txt.find('GPU Profile for Frame', i)
    k = txt.find('GPU Profile for Frame', j + 10)
    bloc = txt[j:k if k > 0 else len(txt)].splitlines()
    out = {'postes': {}}
    for l in bloc:
        m = re.search(r'Frame Time\s*:\s*([\d.]+)ms', l)
        if m:
            out['image_ms'] = float(m.group(1))
        cols = l.split('┃')
        if len(cols) >= 4:
            t = re.findall(r'([\d.]+) ms', cols[2])
            nom = cols[3].rstrip()
            ind = len(nom) - len(nom.lstrip())
            nom = nom.strip()
            if t and nom == '<root>':
                out['gpu_ms'] = float(t[0])
            elif t and ind == 16 and float(t[0]) >= 0.15:
                out['postes'][nom] = out['postes'].get(nom, 0.0) + float(t[0])
        m = re.search(r'TemporalSuperResolution\(.*?\) (\d+x\d+) -> (\d+x\d+)', l)
        if m:
            out['tsr'] = f'{m.group(1)} -> {m.group(2)}'
    out['postes'] = dict(sorted(((k_, round(v, 3)) for k_, v in out['postes'].items()), key=lambda kv: -kv[1])[:12])
    return out


def etape_perf(c, vues=('cam2', 'cam3', 'a', 'f', 'cam1', 'cam4')):
    poses = poses_controle()
    P = f'{UE}/perf.py'
    r = {'methode': 'PIE en fenetre flottante, rendu interne 1920 x 1080 (r.ScreenPercentage sur la fenetre PIE), VSync '
                    'coupe ; temps d image = moyenne de 300 intervalles apres 120 images de chauffe (editeur + PIE) ; '
                    'GPU = ProfileGPU (<root> inclusif) sur une image', 'preparer': ue(c, P, {'etape': 'preparer'}),
         'vues': {}}
    try:
        c.call_tool('EditorToolset.EditorAppToolset', 'StopPIE', {})
    except McpErreur:
        pass
    c.call_tool('EditorToolset.EditorAppToolset', 'StartPIE', {'options': {'playMode': 'PlayMode_InEditorFloating',
                                                                           'warmupSeconds': 3}})
    try:
        for v in vues:
            d = {'pose': ue(c, P, {'etape': 'poser', 'pose': poses[v]})}
            time.sleep(2.0)
            marque = f'{v}_{int(time.time())}'
            ue(c, P, {'etape': 'mesurer', 'chauffe': 120, 'n': 300, 'marque': marque})
            for _ in range(240):
                time.sleep(0.5)
                e = ue(c, P, {'etape': 'etat'})
                if e.get('fini'):
                    break
            d['images'] = e
            time.sleep(1.0)
            d['gpu'] = profil_gpu(marque)
            r['vues'][v] = d
    finally:
        try:
            c.call_tool('EditorToolset.EditorAppToolset', 'StopPIE', {})
        except McpErreur:
            pass
        r['restaurer'] = ue(c, P, {'etape': 'restaurer'})
    gms = [d['gpu'].get('gpu_ms') for d in r['vues'].values() if d['gpu'].get('gpu_ms')]
    ims = [d['images'].get('ips_moyen') for d in r['vues'].values() if d['images'].get('ips_moyen')]
    r['synthese'] = {'gpu_ms_max': max(gms) if gms else None, 'gpu_ms_moyen': round(sum(gms) / len(gms), 2) if gms else None,
                     'ips_min': min(ims) if ims else None, 'objectif_60ips': (min(ims) >= 60) if ims else None}
    return ecrire('contexte_perf.json', r)


def etape_panoramax(c):
    import panoramax
    return panoramax.principal(c)


def etape_planches():
    import planches
    return planches.principal()


def main(argv):
    etape = argv[0] if argv else 'tout'
    if etape in ('usd', 'tout'):
        print(etape_usd())
    if etape == 'planches':
        print(etape_planches())
        return
    with McpClient() as c:
        if etape in ('materiaux', 'tout'):
            print(etape_materiaux(c))
        if etape in ('imports', 'tout'):
            print(etape_imports(c))
        if etape in ('arbres', 'tout'):
            print(etape_arbres(c))
        if etape in ('herbe', 'tout'):
            print(etape_herbe(c))
        if etape in ('clotures', 'tout'):
            print(etape_clotures(c))
        if etape in ('mobilier', 'tout'):
            print(etape_mobilier(c))
        if etape in ('feuilles', 'tout'):
            print(etape_feuilles(c))
        if etape in ('perf', 'tout'):
            print(etape_perf(c, tuple(argv[1:]) or ('cam2', 'cam3', 'a', 'f', 'cam1', 'cam4')))
        if etape in ('captures', 'tout'):
            print(etape_captures(c, argv[1:] or None))
        if etape in ('panoramax', 'tout'):
            print(etape_panoramax(c))
        if etape in ('revue', 'tout'):
            print(etape_revue(c, argv[1:] or None))
        if etape == 'inventaire':
            print(ecrire('contexte_inventaire.json', ue(c, f'{PILOTE_UE}/inventaire.py')))
        c.pj('save_all', {})
    if etape == 'tout':
        print(etape_planches())


if __name__ == '__main__':
    main(sys.argv[1:])
