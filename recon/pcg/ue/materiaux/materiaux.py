"""Matériaux du sol V2 dans UE 5.8 : orchestration (côté client, éditeur ouvert, MCP pj_tools).

    python recon/pcg/ue/materiaux/materiaux.py preparer      textures dérivées + mesures, maillages USD (hors éditeur)
    python recon/pcg/ue/materiaux/materiaux.py construire    textures, maîtres et MI dans l'éditeur
    python recon/pcg/ue/materiaux/materiaux.py niveau        PJ_Materiaux : éclairage, import USD, plaques, maquettes
    python recon/pcg/ue/materiaux/materiaux.py mesurer       albédo moyen de chaque MI (GBuffer) contre la cible
    python recon/pcg/ue/materiaux/materiaux.py etalonner     corrige etalonnage.json, reconstruit les MI, remesure
    python recon/pcg/ue/materiaux/materiaux.py essai_cd      file de bordures posée par PCG avec données d'instance cd
    python recon/pcg/ue/materiaux/materiaux.py captures      vues à 1,60 m (photos 1 à 3) et vues de dessus de la grille
    python recon/pcg/ue/materiaux/materiaux.py tout
Sorties : recon/out/paquet_jardin/v2/ue_materiaux/ (construction.json, niveau.json, albedo.json, vues/*.png|exr).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(os.path.dirname(ICI), 'tests_phase0'))
import catalogue as C  # noqa: E402
import commun  # noqa: E402  (client MCP, capture asynchrone, lecture EXR)

NIVEAU = '/Game/PJ/Maps/PJ_Materiaux'
USD_UE = '/Game/PJ/Essais/Materiaux/USD'
# exposition manuelle unique du projet (pj_tools/eclairage.py : EV100 14, comme PJ_Phase0 et les capteurs)
EV100 = commun.EV100
VUES = f'{C.OUT}/vues'
CARLA_FACTEUR_MAX = 8.0     # au-delà, le MI CARLA n'est pas une surface uniforme (atlas de bordure ou de caniveau)


def ue(c, script, args=None, timeout=3600):
    r = c.pj('run_python_file', {'path': f'{ICI}/{script}'.replace('\\', '/'), 'args_json': json.dumps(args or {})},
             timeout=timeout)
    if not isinstance(r, dict) or not r.get('ok'):
        raise RuntimeError(f'{script} : {json.dumps(r, ensure_ascii=False)[-4000:]}')
    return r


def preparer():
    for s in ('preparer_textures.py', 'generer_meshes.py'):
        subprocess.run([sys.executable, os.path.join(ICI, s)], check=True)


def construire(c, etapes=('textures', 'maitres', 'instances')):
    r = ue(c, 'construire_materiaux.py', {'etapes': list(etapes)})
    print(json.dumps(r['resultat'], ensure_ascii=False)[:2000])
    if r['resultat']['erreurs']:
        raise RuntimeError(r['resultat']['erreurs'])


def niveau(c, ev100=EV100):
    r = commun.ue(c, 't1_niveau.py', {'niveau': NIVEAU, 'ev100': ev100})
    print('éclairage', json.dumps(r['resultat']['soleil'], ensure_ascii=False))
    import_usd = []
    for f in sorted(os.listdir(f'{C.OUT}/usd')):
        if f.endswith('.usda'):
            r = c.pj('import_usd', {'usd_path': f'{C.OUT}/usd/{f}', 'dest_path': f'{USD_UE}/{f[:-5]}',
                                    'kinds_to_collapse': 2, 'render_context': 'unreal', 'nanite': True}, timeout=900)
            if not r.get('ok'):
                raise RuntimeError(f'import {f} : {r}')
            import_usd.append({'usd': f, 'acceptation': r['acceptation'], 'meshes': [
                {k: m[k] for k in ('mesh', 'sommets', 'uv', 'recompute_normals', 'materiaux')} for m in r['meshes']]})
    with open(f'{C.OUT}/import_usd.json', 'w', encoding='utf-8') as f:
        json.dump(import_usd, f, ensure_ascii=False, indent=1)
    print('import USD :', [(x['usd'], x['acceptation']['ok']) for x in import_usd])
    r = ue(c, 'niveau_materiaux.py', {'ev100': ev100})
    print('plaques', len(r['resultat']['plaques']), 'retirés', r['resultat']['acteurs_retires'])
    c.pj('save_all', {})


def lire_moyennes(noms=None):
    import numpy as np
    d = f'{C.OUT}/albedo'
    out = {}
    for f in sorted(os.listdir(d)):
        if f.endswith('.exr') and (not noms or f[:-4] in noms):
            e = commun.lire_exr(f'{d}/{f}')
            out[f[:-4]] = [round(float(np.mean(e[k])), 4) for k in ('R', 'G', 'B')]
    return out


def facteur_tete_bordure(d):
    """Plaque plate (z local = 0 : salissure du pied partout) -> tête de bordure (salissure × SalissureHaut)."""
    s = d['scalaires'].get('Salissure', 0.0)
    t = C.TEINTE_SALISSURE_BORDURE

    def f(sv, k):
        return (1 - sv * (1 - t[k])) * (1 - C.K_SAL * sv)
    return [f(s * C.SALISSURE_HAUT, k) / f(s, k) for k in range(3)]


def mesurer(c, nom_sortie='albedo.json'):
    r = ue(c, 'mesurer_albedo.py', {})
    print('plaques mesurées', r['resultat']['nb'])
    moy = lire_moyennes()
    etal = C.charger_json(C.ETALONNAGE, {})
    mes = C.charger_json(C.MESURES)
    defs = {d['nom']: d for d in C.instances(mes, etal) + C.peintures(mes)}
    rap = {}
    for nom, m in moy.items():
        d = defs.get(nom)
        if d is None:
            continue
        e = {'maitre': d['maitre'], 'variante': d.get('variante'), 'mesure_plaque': m}
        cible = d.get('cible')
        if d['maitre'] == 'bordure':
            k = facteur_tete_bordure(d)
            e['mesure'] = [round(m[i] * k[i], 4) for i in range(3)]
            e['note'] = 'tête de bordure (salissure × SalissureHaut) déduite de la plaque'
        else:
            e['mesure'] = m
        if cible:
            e['cible'] = cible
            e['cible_source'] = d.get('cible_source')
            e['ecart_lum_pct'] = round(100 * (C.lum(e['mesure']) / C.lum(cible) - 1), 1)
            e['ecart_max_canal_pct'] = round(100 * max(abs(e['mesure'][i] / cible[i] - 1) for i in range(3)), 1)
        rap[nom] = e
    json.dump({'date': commun.horodatage(), 'methode': 'GBuffer base color, SceneCapture2D orthographique, 1,6 x 1,6 m centraux',
               'mi': rap}, open(f'{C.OUT}/{nom_sortie}', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    hors = [(k, v['ecart_lum_pct'], v['ecart_max_canal_pct']) for k, v in rap.items()
            if 'cible' in v and (abs(v['ecart_lum_pct']) > 10 or v['ecart_max_canal_pct'] > 10)]
    print(f'{len(rap)} MI mesurés ; hors ±10 % : {len(hors)}', hors[:40])
    return rap


def etalonner(c, rap):
    """facteur_nouveau = facteur × cible / mesure (CARLA : luminance seule), puis reconstruction des MI."""
    etal = C.charger_json(C.ETALONNAGE, {}) or {}
    etal.setdefault('mi', {})
    for nom, e in rap.items():
        if 'cible' not in e or e['maitre'] == 'peinture':
            continue
        f0 = etal['mi'].get(nom, {}).get('facteur', [1.0, 1.0, 1.0])
        if e['variante'] == 'carla' and e['maitre'] == 'carla':
            k = C.lum(e['cible']) / max(C.lum(e['mesure']), 1e-6)
            f = [round(min(max(x * k, 1 / CARLA_FACTEUR_MAX), CARLA_FACTEUR_MAX), 5) for x in f0]
        else:
            f = [round(f0[i] * e['cible'][i] / max(e['mesure'][i], 1e-6), 5) for i in range(3)]
        etal['mi'][nom] = {'facteur': f, 'mesure_avant': e['mesure'], 'cible': e['cible']}
    etal['methode'] = ('facteur = cible / mesure GBuffer (cumulé) ; MI CC0 et City Sample : Luminosite × Teinte ; '
                       'MI CARLA : paramètre de luminosité du MI parent × luminance du facteur')
    etal['date'] = commun.horodatage()
    with open(C.ETALONNAGE, 'w', encoding='utf-8') as f:
        json.dump(etal, f, ensure_ascii=False, indent=1)
    construire(c, ('instances',))


def captures(c, ev100=EV100, seulement=None):
    os.makedirs(VUES, exist_ok=True)
    niv = C.charger_json(f'{C.OUT}/niveau.json')
    g = niv['grille']
    cx = g['x0'] + g['pas'] * g['colonnes'] / 2
    vues = {
        # (cam x, y, z), cap, site, fov, largeur, hauteur
        'v1_file_bordures_photo1': ((3.4, -2.9, 1.6), 95.0, -32.0, 60.0, 1920, 1080),
        'v1b_file_bordures_rasante': ((-1.2, -0.9, 1.6), 12.0, -22.0, 55.0, 1920, 1080),
        'v2_ilot_brf_photo2': ((4.6, 5.25, 1.6), 172.0, -42.0, 60.0, 1920, 1080),
        'v3_ilot_gravier_photo3': ((9.0, 5.1, 1.6), 148.0, -45.0, 60.0, 1920, 1080),
        'v4_chaussee_trottoir_detail': ((3.0, -1.6, 1.6), 90.0, -55.0, 50.0, 1920, 1080),
        'v5_bordures_pcg_cd': ((3.0, 9.0, 1.6), 90.0, -32.0, 62.0, 1920, 1080),
        'grille_dessus': ((cx, (g['y0'] + g['y_fin']) / 2, 46.0), 90.0, -90.0, 46.0, 2160, 3240),
    }
    for nom, (cam, yaw, pitch, fov, w, h) in vues.items():
        if seulement and nom not in seulement:
            continue
        t0 = time.time()
        r = commun.capture(c, nom, cam, yaw, pitch, fov=fov, w=w, h=h, ev100=ev100, warmup=48, dossier=VUES)
        print(nom, r.get('moyenne'), round(time.time() - t0, 1), 's')
    # vues de dessus par bloc (une rangée de 8 plaques par image)
    if not seulement or 'blocs' in seulement:
        rangs = sorted({p['centre'][1] for p in niv['plaques']})
        for i, yr in enumerate(rangs):
            commun.capture(c, f'grille_rang_{i:02d}', (cx - 0.35, yr - 0.15, 11.8), 90.0, -90.0, fov=86.0, w=2560, h=820, ev100=ev100,
                           warmup=32, dossier=VUES)


def essai_cd(c):
    """File de 6 bordures posée par PCG depuis des points pj_points/0.1 porteurs de cd (essai_bordures_cd.py)."""
    imp = {x['usd']: x for x in C.charger_json(f'{C.OUT}/import_usd.json')}
    mesh = imp['PJ_Bordure_T2_L994_Droit.usda']['meshes'][0]['mesh']
    # cd = [usure, salissure, mousse_joints, herbe_joints, teinte] ; le 6e point n'en porte pas (valeurs du MI)
    cds = [[0, 0, 0, 0, -1], [0, 0, 0, 0, 1], [0, 0.2, 0, 0, 0], [0, 1.0, 0, 0, 0], [0.5, 0.45, 1.0, 0, 0], None]
    pts = []
    for k, cd in enumerate(cds):
        q = {'id': f'K_essai_cd_{k + 1}', 'asset': mesh, 'p': [k * 1.0, 11.0, 0.0], 'q': [0.0, 0.0, 0.0, 1.0],
             'rpy_deg': [0.0, 0.0, 0.0], 's': [1.0, 1.0, 1.0], 'graine': 1000 + k}
        if cd is not None:
            q['cd'] = cd
        pts.append(q)
    doc = {'schema': 'pj_points/0.1', 'famille': 'essai_bordures_cd', 'source_hash': 'essai',
           'convention_cd': 'cd = [usure, salissure, mousse_joints, herbe_joints, teinte] (bordures_elements.json)',
           'points': pts}
    js = f'{C.OUT}/points_essai_bordures_cd.json'
    with open(js, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    pda = '/Game/PJ/PCG/Donnees/PDA_Essai_Bordures_cd'
    r = c.pj('charger_points', {'json_path': js, 'asset_path': pda})
    t0 = time.time()
    while not r.get('fini') and time.time() - t0 < 120:
        time.sleep(0.5)
        r = c.pj('charger_points', {'json_path': js, 'asset_path': pda, 'etat_seulement': True})
    if not r.get('fini'):
        raise RuntimeError(f'cuisson {pda} : {r}')
    r = ue(c, 'essai_bordures_cd.py', {'etape': 'generer', 'pda': pda})
    print('graphe', r['resultat'])
    time.sleep(3.0)
    v = ue(c, 'essai_bordures_cd.py', {'etape': 'verifier'})['resultat']
    with open(f'{C.OUT}/essai_bordures_cd.json', 'w', encoding='utf-8') as f:
        json.dump({'points': js, 'pda': pda, **v}, f, ensure_ascii=False, indent=1)
    for i in v['ism']:
        print(i['mesh'], i['instances'], 'cd/instance', i['cd_par_instance'], [d['cd'] for d in i['detail']])
    c.pj('save_all', {})


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'tout'
    if cmd == 'preparer':
        return preparer()
    c = commun.client()
    if cmd in ('construire', 'tout'):
        if cmd == 'tout':
            preparer()
        construire(c)
    if cmd in ('niveau', 'tout'):
        niveau(c)
    if cmd in ('mesurer', 'tout'):
        mesurer(c)
    if cmd in ('etalonner', 'tout'):
        for _ in range(2):
            etalonner(c, mesurer(c))
        mesurer(c)
        c.pj('save_all', {})
    if cmd in ('essai_cd', 'tout'):
        essai_cd(c)
    if cmd in ('captures', 'tout'):
        captures(c, seulement=sys.argv[2:] or None)


if __name__ == '__main__':
    main()
