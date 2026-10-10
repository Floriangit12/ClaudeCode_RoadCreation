"""Essai d'acceptation du contrat d'export (editeur UE ouvert, pj_tools publie) : python contrat/test_contrat.py

1. ecrit l'echantillon de reference (echantillon_contrat.py, pxr de l'editeur) et le verifie (verifier_usd.py) ;
2. controle negatif : la couche bordures v1 (sans normales ni UV) doit etre refusee par le verificateur ;
3. importe l'echantillon par pj_tools.import_usd (kinds_to_collapse = 2 : un StaticMesh par component)
   dans /Game/PJ/Test_Contrat : critere 0 avertissement LogStaticMesh, normales importees (pas de recalcul),
   1 canal UV en pleine precision, 2 meshes (SM_K_essai_0001, SM_S_essai_0001), 2 slots sur la dalle ;
4. controle negatif de l'import : la couche bordures v1 doit produire des avertissements LogStaticMesh.
Rapport : recon/out/paquet_jardin/v2/ue_phase0/contrat_export.json.
"""
from __future__ import annotations

import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'tests_phase0'))
import commun as C  # noqa: E402

ECH = f'{ICI}/echantillon_contrat.usda'.replace('\\', '/')
V1 = f'{C.DEPOT}/recon/out/paquet_jardin/package/layers/bordures.usdc'.replace('\\', '/')


def py(c, script, args):
    r = c.pj('run_python_file', {'path': f'{ICI}/{script}'.replace('\\', '/'), 'args_json': json.dumps(args)},
             timeout=1800)
    if not r.get('ok'):
        raise C.McpErreur(json.dumps(r, ensure_ascii=False)[-4000:])
    return r['resultat']


def main():
    c = C.client()
    res = {'date': C.horodatage()}
    try:
        c.pj('load_level', {'path': C.NIVEAU, 'discard_untitled': True})
        res['echantillon'] = py(c, 'echantillon_contrat.py', {'sortie': ECH})
        res['verif_echantillon'] = py(c, 'verifier_usd.py', {'usd': ECH})
        v1 = py(c, 'verifier_usd.py', {'usd': V1})
        res['verif_v1'] = {k: v for k, v in v1.items() if k != 'meshes'}
        imp = c.pj('import_usd', {'usd_path': ECH, 'dest_path': '/Game/PJ/Test_Contrat/Echantillon',
                                  'kinds_to_collapse': 2}, timeout=1800)
        res['import'] = {k: imp.get(k) for k in ('ok', 'nb', 'objets', 'meshes', 'journal', 'acceptation', 'duree_s')}
        res['import']['options'] = {k: imp.get('options', {}).get(k) for k in (
            'kinds_to_collapse', 'use_prim_kinds_for_collapsing', 'render_context_to_import')}
        neg = c.pj('import_usd', {'usd_path': V1, 'dest_path': '/Game/PJ/Test_Contrat/V1'}, timeout=1800)
        res['import_v1'] = {k: neg.get(k) for k in ('ok', 'nb', 'meshes', 'journal', 'acceptation', 'duree_s')}
        # les acteurs v1 font doublon avec t4 : retires du niveau (les assets restent)
        res['retrait_v1'] = C.ue(c, 't4_retirer.py', {'dossier': '/Game/PJ/Test_Contrat/V1'})['resultat']
        c.pj('save_all')
        sm = {os.path.basename(m['mesh']).split('.')[0]: m for m in res['import']['meshes']}
        res['controles'] = {
            'verificateur_echantillon_ok': res['verif_echantillon']['ok'],
            'verificateur_refuse_v1': not v1['ok'],
            'zero_avertissement_logstaticmesh': res['import']['acceptation']['ok'],
            'meshes_par_component': sorted(sm) == ['SM_K_essai_0001', 'SM_S_essai_0001'],
            'normales_importees': all(not m['recompute_normals'] for m in sm.values()),
            'uv_pleine_precision_1_canal': all(m['use_full_precision_u_vs'] and m['uv'] == 1 for m in sm.values()),
            'dalle_2_slots': len(sm.get('SM_S_essai_0001', {}).get('materiaux', [])) == 2,
            'detecteur_avertissements_v1': not res['import_v1']['acceptation']['ok'],
        }
        res['ok'] = all(res['controles'].values())
        res['capture'] = C.capture(c, 'contrat_echantillon', (-96.0, -123.0, 1.2), 125.5, -13.7, 60)
    finally:
        c.fermer()
    C.ecrire_json('contrat_export.json', res)
    print(json.dumps({'controles': res.get('controles'), 'ok': res.get('ok'),
                      'journal_echantillon': res.get('import', {}).get('journal'),
                      'erreurs_v1': res.get('verif_v1', {}).get('erreurs', [])[:8],
                      'journal_v1': res.get('import_v1', {}).get('journal')}, ensure_ascii=False, indent=1)[:8000])
    return 0 if res.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
