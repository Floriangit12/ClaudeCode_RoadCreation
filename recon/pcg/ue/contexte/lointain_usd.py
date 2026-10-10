"""[hython] Couche lointain.usdc : batiments du cadastre hors du carre v1 (contexte/lointain.py -> lointain_entrees.json)
extrudes en LoD1 (murs + toit plat triangule par oreilles), base au plan de contexte ; une composante par tuile de 100 m,
un Mesh par materiau (facades M_PJ_Facade, toits CARLA). UV des murs : u = abscisse le long du contour, v = hauteur ;
st1 = (hauteur, alea du batiment) comme les batiments v1 (fenetres procedurales). Appele par preparer_usd.py.
"""
import hashlib
import json
import math

import numpy as np


def graine(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:4], 'little') & 0x7FFFFFFF


def trianguler(r):
    """Triangulation par oreilles d'un anneau simple (liste de (x, y), non ferme, sens trigo) -> [(a, b, c)]."""
    idx = list(range(len(r)))
    tris = []

    def aire2(a, b, c):
        return (r[b][0] - r[a][0]) * (r[c][1] - r[a][1]) - (r[c][0] - r[a][0]) * (r[b][1] - r[a][1])

    def dedans(p, a, b, c):
        return aire2(a, b, p) >= 0 and aire2(b, c, p) >= 0 and aire2(c, a, p) >= 0
    garde = 0
    while len(idx) > 3 and garde < 10000:
        garde += 1
        for k in range(len(idx)):
            a, b, c = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            if aire2(a, b, c) <= 1e-9:
                continue
            if any(dedans(q, a, b, c) for q in idx if q not in (a, b, c)):
                continue
            tris.append((a, b, c))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def construire(Couche, facades_enduit, entrees, chemin_sortie):
    """Couche (classe de preparer_usd.py), facades_enduit (liste des MI d'enduit) -> ecrit lointain.usdc ; rapport."""
    with open(entrees, encoding='utf-8') as f:
        d = json.load(f)
    z0 = float(d['z_base'])
    lo = Couche('Batiments lointains (cadastre Etalab, hauteurs a priori ; recon/pcg/ue/contexte/lointain.py, '
                'lointain_usd.py), base au plan de contexte.')
    lo.groupe('/World/Lointain')
    par_tuile = {}
    for b in d['batiments']:
        r = [tuple(p) for p in b['anneau']]
        if r[0] == r[-1]:
            r = r[:-1]
        if len(r) < 3:
            continue
        a2 = sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))
        if a2 < 0:
            r = r[::-1]                                   # sens trigo : normales des murs vers l'exterieur
        h, g = float(b['h']), graine('lointain', b['id'])
        if h < 4.0:
            fac, toit = 'PJ_Facade_annexe', 'toit_terrasse'
        elif b['aire_m2'] > 1500 and h < 12:
            fac, toit = 'PJ_Facade_commerce', 'toit_terrasse'
        else:
            fac = facades_enduit[g % len(facades_enduit)]
            toit = 'toit_pentes' if b['aire_m2'] < 200 else 'toit_terrasse'
        cx = sum(p[0] for p in r) / len(r)
        cy = sum(p[1] for p in r) / len(r)
        T_ = par_tuile.setdefault((int(math.floor(cx / 100.0)), int(math.floor(cy / 100.0))), {})
        P, Tr, UV = [], [], []
        s0 = 0.0
        for i in range(len(r)):
            (x0, y0), (x1, y1) = r[i], r[(i + 1) % len(r)]
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 1e-3:
                continue
            o = len(P)
            P += [(x0, y0, z0), (x1, y1, z0), (x1, y1, z0 + h), (x0, y0, z0 + h)]
            UV += [(s0, 0.0), (s0 + L, 0.0), (s0 + L, h), (s0, h)]
            Tr += [(o, o + 1, o + 2), (o, o + 2, o + 3)]
            s0 += L
        if Tr:
            T_.setdefault(fac, []).append((np.array(P), np.array(Tr), np.array(UV), (h, (g % 1000) / 1000.0)))
        tri = trianguler(r)
        if tri:
            Pr = np.array([(x, y, z0 + h) for x, y in r])
            T_.setdefault(toit, []).append((Pr, np.array(tri), Pr[:, :2], None))
    nb = 0
    for key in sorted(par_tuile):
        comp = f'/World/Lointain/Lointain_{key[0] + 10}_{key[1] + 10}'
        lo.composant(comp)
        for mat in sorted(par_tuile[key]):
            Pl, Tl, UVl, S1, o = [], [], [], [], 0
            for P, Tr, UV, st1 in par_tuile[key][mat]:
                Pl.append(P)
                Tl.append(Tr + o)
                UVl.append(UV[Tr].reshape(-1, 2))
                if st1 is not None:
                    S1.append(np.tile(st1, (len(Tr) * 3, 1)))
                o += len(P)
            P, Tr = np.concatenate(Pl), np.concatenate(Tl)
            a, b_, c = P[Tr[:, 0]], P[Tr[:, 1]], P[Tr[:, 2]]
            n = np.cross(b_ - a, c - a)
            n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
            lo.maillage(f'{comp}/{mat}', P, Tr, mat, np.concatenate(UVl), N=np.repeat(n, 3, axis=0),
                        st1=np.concatenate(S1) if S1 else None)
            nb += len(Tr)
    lo.enregistrer(chemin_sortie)
    return {'batiments': len(d['batiments']), 'tuiles': len(par_tuile), 'triangles': int(nb)}
