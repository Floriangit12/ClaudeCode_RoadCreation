"""Arbres du site -> points PCG (Python pur, deterministe) : arbres.geojson du paquet v1 (+ instances.json pour le
controle des prototypes) -> ue_pilote/points/arbres_ue.json et tuteurs_ue.json (pj_points/0.1), controle des hauteurs.

- Table : vegetation/correspondance_carla.json (essence -> famille -> modele CARLA, variantes d'octobre, echelles) ;
  dimensions des modeles : vegetation/catalogue_carla.json (mesurees dans UE, ue/catalogue.py).
- Z : sol rendu sous le tronc (ue_pilote/usd/z_objets.json, contexte/preparer_usd.py : v1 fondu + sol v2 du pilote),
  moins enfoncement_m ; a defaut z_local du paquet.
- Choix : regle (ordre de la table) -> famille ; feuillu non identifie : melange Erable / Chene tire par classe de
  hauteur LiDAR ; variante S/M/L ou candidat qui minimise l'ecart de hauteur apres bornage de l'echelle ; variante
  de feuillage tiree selon les poids de la famille ; lacet aleatoire ; graine = sha256(id | pj_vegetation/0.1).
- Controle : |h_posee - hauteur_m| / hauteur_m <= 15 % pour au moins 90 % des arbres poses (hauteur_m > 0).
Usage : python arbres.py [SORTIE_DIR]   -> imprime le rapport (aussi ecrit dans SORTIE_DIR/arbres_controle.json)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..'))
OBJETS = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'package', 'donnees', 'objets')
UE_PILOTE = os.path.join(DEPOT, 'recon', 'out', 'paquet_jardin', 'v2', 'ue_pilote')
VEG = '/Game/Carla/Static/Vegetation'
VERSION = 'pj_vegetation/0.1'
TOL = 0.15


def lire(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def rng(*parts) -> random.Random:
    g = int.from_bytes(hashlib.sha256(('|'.join(map(str, parts)) + '|' + VERSION).encode('utf-8')).digest()[:8], 'little')
    return random.Random(g)


def tirer(r: random.Random, poids: dict):
    cles = sorted(poids)
    t = r.random() * sum(poids[k] for k in cles)
    for k in cles:
        t -= poids[k]
        if t <= 0:
            return k
    return cles[-1]


def chemin_asset(nom: str) -> str:
    sous = 'Bushes' if nom.startswith('SM_Bush') else 'Trees'
    return f'{VEG}/{sous}/{nom}.{nom}'


def quat_yaw(yaw_deg: float):
    h = math.radians(yaw_deg) / 2.0
    return [0.0, 0.0, round(math.sin(h), 7), round(math.cos(h), 7)]


class Choix:
    def __init__(self, table, catalogue):
        self.t, self.cat = table, catalogue
        self.e = table['echelle']

    def regle(self, p):
        ess = (p.get('essence') or '').lower()
        genre = (p.get('genre') or '').strip()
        for r in self.t['regles']:
            si = r['si']
            if 'etat_contient' in si and si['etat_contient'] not in (p.get('etat_2026') or ''):
                continue
            if 'type' in si and p.get('type') != si['type']:
                continue
            if 'essence_contient' in si and not any(m in ess for m in si['essence_contient']):
                continue
            if 'genre' in si and not (genre == si['genre'] or genre.startswith(si['genre'] + ' ')):
                continue
            return r
        return None

    def ecart(self, nom, h):
        ha = self.cat[nom]['hauteur_m']
        s = min(max(h / ha, self.e['min']), self.e['max'])
        return abs(s * ha - h) / h, s

    def meilleur(self, noms, h):
        """(nom, sz) du modele dont la hauteur bornee approche le mieux h (ordre de la liste en cas d'egalite)."""
        return min(((self.ecart(n, h)[0], i, n) for i, n in enumerate(noms)))[2]

    def arbre(self, p):
        r = rng(p['id'])
        regle = self.regle(p)
        fam = regle['famille']
        h = float(p.get('hauteur_m') or 0.0) or 5.0
        if fam == 'feuillu' or (regle.get('repli') and not self._atteint(fam, h)):
            for c in self.t['feuillu']['classes_hauteur_m']:
                if h <= c['max']:
                    fam_eff = tirer(r, c['melange'])
                    break
            src = 'melange'
        else:
            fam_eff, src = fam, 'regle'
        F = self.t['familles'][fam_eff if fam_eff in self.t['familles'] else fam]
        v = tirer(r, F['variantes'])
        if fam_eff == 'Jeune':
            g = (p.get('essence') or '').split(' ')[0]
            modeles = [regle['genre'][g]] if g in regle.get('genre', {}) else [tirer(r, regle['melange'])]
        else:
            modeles = F['modeles']
        noms = [m.format(v=v) for m in modeles]
        noms = [n for n in noms if n in self.cat] or [m.format(v='1') for m in modeles]
        nom = self.meilleur(noms, h)
        a = self.cat[nom]
        _, sz = self.ecart(nom, h)
        c = float(p.get('diametre_couronne_m') or 0.0)
        sxy = sz if c <= 0.3 else min(max(c / a['couronne_m'], self.t['echelle']['couronne_relative'][0] * sz),
                                       self.t['echelle']['couronne_relative'][1] * sz)
        sxy = min(max(sxy, self.e['min']), self.e['max'])
        return {'famille': fam_eff, 'source': src, 'modele': nom, 'sz': sz, 'sxy': sxy, 'yaw': r.uniform(0.0, 360.0),
                'h_asset': a['hauteur_m'], 'regle': regle['si']}

    def _atteint(self, fam, h):
        F = self.t['familles'][fam]
        noms = [m.format(v='1') for m in F['modeles']]
        return min(self.ecart(n, h)[0] for n in noms if n in self.cat) <= TOL


def principal(sortie_dir: str = os.path.join(UE_PILOTE, 'points')) -> dict:
    table = lire(os.path.join(ICI, 'correspondance_carla.json'))
    cat = lire(os.path.join(ICI, 'catalogue_carla.json'))['assets']
    arbres = lire(os.path.join(OBJETS, 'arbres.geojson'))['features']
    zf = os.path.join(UE_PILOTE, 'usd', 'z_objets.json')
    zsol = lire(zf)['z'] if os.path.exists(zf) else {}
    ch = Choix(table, cat)
    ign = table['ignores']
    pts, tut, ctrl, ignores = [], [], [], []
    for f in sorted(arbres, key=lambda f: f['properties']['id']):
        p = f['properties']
        if p['type'] in ign['types'] or (ign['instancier_faux'] and not p.get('instancier')) \
                or any(s in str(p.get('statut_2026')) for s in ign['statut_contient']):
            ignores.append({'id': p['id'], 'type': p['type'], 'statut': p.get('statut_2026'), 'etat': p.get('etat_2026')})
            continue
        c = ch.arbre(p)
        z = zsol.get(p['id'])
        z = (z if z is not None else p['z_local']) - table['enfoncement_m']
        x, y = p['x_local'], p['y_local']
        q = quat_yaw(c['yaw'])
        pts.append({'id': p['id'], 'asset': chemin_asset(c['modele']), 'p': [round(x, 3), round(y, 3), round(z, 3)],
                    'q': q, 'rpy_deg': [0.0, 0.0, round(c['yaw'], 4)],
                    's': [round(c['sxy'], 4), round(c['sxy'], 4), round(c['sz'], 4)],
                    'graine': int.from_bytes(hashlib.sha256(p['id'].encode()).digest()[:4], 'little') & 0x7FFFFFFF,
                    'x': {'essence': p.get('essence'), 'type': p['type'], 'famille': c['famille'], 'choix': c['source'],
                          'h_data': p.get('hauteur_m'), 'couronne_data': p.get('diametre_couronne_m'),
                          'h_posee': round(c['sz'] * c['h_asset'], 2), 'etat': p.get('etat_2026')}})
        h = float(p.get('hauteur_m') or 0.0)
        if h > 0:
            e = (c['sz'] * c['h_asset'] - h) / h
            ctrl.append({'id': p['id'], 'modele': c['modele'], 'h_data': h, 'h_posee': round(c['sz'] * c['h_asset'], 2),
                         'ecart_rel': round(e, 4), 'ok': abs(e) <= TOL + 1e-9})
        if table['familles'].get(c['famille'], {}).get('tuteurs'):
            T = table['tuteurs']
            r = rng(p['id'], 'tuteurs')
            a0 = r.uniform(0, 120)
            for k in range(T['nombre']):
                a = math.radians(a0 + 360.0 * k / T['nombre'])
                hz = T['hauteur_hors_sol_m'] + T['enfoui_m']
                tut.append({'id': f"{p['id']}/T{k}", 'asset': T['asset'], 'materiau': T['materiau'],
                            'p': [round(x + T['rayon_m'] * math.cos(a), 3), round(y + T['rayon_m'] * math.sin(a), 3),
                                  round(z + table['enfoncement_m'] - T['enfoui_m'] + hz / 2.0, 3)],
                            'q': [0.0, 0.0, 0.0, 1.0], 's': [T['diametre_m'], T['diametre_m'], hz], 'graine': k})
    ok = sum(c['ok'] for c in ctrl)
    entete = {'repere': 'local (L93 - O, z = NGF - 216,30), m, Z haut',
              'pivot': 'pied du tronc (modeles CARLA : origine au sol)',
              'source': 'package/donnees/objets/arbres.geojson ; vegetation/correspondance_carla.json ; '
                        'recon/pcg/ue/vegetation/arbres.py',
              'bibliotheque': 'asset = StaticMesh CARLA (/Game/Carla/Static/Vegetation, CC-BY 4.0)'}
    sh = hashlib.sha256(open(os.path.join(OBJETS, 'arbres.geojson'), 'rb').read()).hexdigest()
    os.makedirs(sortie_dir, exist_ok=True)
    for nom, fam, L in (('arbres_ue.json', 'arbres', pts), ('tuteurs_ue.json', 'tuteurs', tut)):
        tete = {'schema': 'pj_points/0.1', 'famille': fam, 'source_hash': sh, **entete}
        lignes = [json.dumps(tete, ensure_ascii=False)[:-1] + ',\n"points": [']
        for i, q in enumerate(L):
            lignes.append(json.dumps(q, ensure_ascii=False, separators=(',', ':')) + (',' if i < len(L) - 1 else ''))
        lignes.append(']}')
        with open(os.path.join(sortie_dir, nom), 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lignes) + '\n')
    from collections import Counter
    rapport = {'arbres_poses': len(pts), 'tuteurs': len(tut), 'ignores': len(ignores),
               'ignores_detail': ignores,
               'controle_hauteur': {'tolerance': TOL, 'n': len(ctrl), 'ok': ok, 'part_ok': round(ok / max(len(ctrl), 1), 4),
                                    'critere_90pct': ok / max(len(ctrl), 1) >= 0.9,
                                    'hors_tolerance': [c for c in ctrl if not c['ok']]},
               'familles': dict(Counter(q['x']['famille'] for q in pts)),
               'modeles': dict(Counter(q['asset'].rsplit('.', 1)[-1] for q in pts).most_common()),
               'z_sol_rendu': sum(1 for f in arbres if zsol.get(f['properties']['id']) is not None)}
    with open(os.path.join(sortie_dir, 'arbres_controle.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    return rapport


if __name__ == '__main__':
    r = principal(*sys.argv[1:2])
    print(json.dumps({k: v for k, v in r.items() if k not in ('ignores_detail',)}, ensure_ascii=False, indent=1)[:6000])
