"""[hython] Controle de l'exclusion de l'herbe pres des bordures : distance en plan de chaque instance de PG_Herbe
(positions relevees dans l'editeur par ue/positions_herbe.py) aux bordures v2 posees (emprise des elements et caniveaux de
fabrique_ue_snapshot/points/bordures.json, joints exclus) et aux faces de bordure v1 hors emprise (paquet v1 + masque du
pilote). Critere de la consigne : centre de la touffe a 0,15 m au moins d'une ligne de bordure.

    hython recon/pcg/ue/contexte/controle_herbe.py POSITIONS.json SORTIE.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import preparer_usd as PU  # noqa: E402

SEUIL = 0.15


def segments_v2(snapshot):
    pts = PU.lire_json(snapshot / 'points/bordures.json')['points']
    index = PU.lire_json(snapshot / 'prototypes/index.json')['prototypes']
    segs, rects = [], []
    for p in pts:
        x_ = p.get('x') or {}
        if x_.get('type') == 'joint':
            continue
        L, W = index[p['asset']]['dims_m'][:2]
        L *= p['s'][0]
        y0, y1 = (-W, 0.0) if x_.get('type') == 'caniveau' else (0.0, W)
        loc = np.array([[-L / 2, y0], [L / 2, y0], [L / 2, y1], [-L / 2, y1]])
        a = math.radians(p['rpy_deg'][2])
        R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        q = loc @ R.T + np.array(p['p'][:2])
        rects.append(q)
        for k in range(4):
            segs.append((q[k], q[(k + 1) % 4]))
    return np.array(segs), rects


def segments_v1(snapshot):
    st = PU.stage_v1(snapshot)
    P, tri, _ = PU.triangles(st.GetPrimAtPath('/World/Bordures/faces_verticales'))
    V = P[tri][:, :, :2]
    d01 = np.linalg.norm(V[:, 0] - V[:, 1], axis=1)
    d02 = np.linalg.norm(V[:, 0] - V[:, 2], axis=1)
    d12 = np.linalg.norm(V[:, 1] - V[:, 2], axis=1)
    k = np.argmax(np.stack([d01, d02, d12], axis=1), axis=1)
    A = np.where(k[:, None] == 2, V[:, 1], V[:, 0])
    B = np.where(k[:, None] == 0, V[:, 1], V[:, 2])
    ok = np.linalg.norm(B - A, axis=1) > 1e-3
    return np.stack([A[ok], B[ok]], axis=1)


def distances(Q, S, cel=1.0, rayon=1.0):
    """Distance de chaque point Q (n,2) au segment le plus proche de S (m,2,2), plafonnee a rayon."""
    o = np.minimum(S.min(axis=(0, 1)), Q.min(axis=0)) - 2.0
    grille = {}
    lo = np.floor((S.min(axis=1) - o - rayon) / cel).astype(int)
    hi = np.floor((S.max(axis=1) - o + rayon) / cel).astype(int)
    for s in range(len(S)):
        for i in range(lo[s, 0], hi[s, 0] + 1):
            for j in range(lo[s, 1], hi[s, 1] + 1):
                grille.setdefault((i, j), []).append(s)
    cq = np.floor((Q - o) / cel).astype(int)
    d = np.full(len(Q), rayon)
    for n in range(len(Q)):
        c = grille.get((int(cq[n, 0]), int(cq[n, 1])))
        if not c:
            continue
        A, B = S[c, 0], S[c, 1]
        ab = B - A
        t = np.clip(((Q[n] - A) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-12), 0, 1)
        d[n] = min(rayon, float(np.min(np.linalg.norm(A + t[:, None] * ab - Q[n], axis=1))))
    return d


def principal(positions, sortie, snapshot=PU.V2 / 'fabrique_ue_snapshot'):
    pos = json.load(open(positions, encoding='utf-8'))
    s2, rects = segments_v2(Path(snapshot))
    s1 = segments_v1(Path(snapshot))
    S = np.concatenate([s2, s1])
    rapport = {'seuil_m': SEUIL, 'segments_v2': int(len(s2)), 'segments_v1': int(len(s1)), 'par_mesh': {}}
    for nom in sorted(pos):
        Q = np.array(pos[nom], dtype=np.float64)
        if not len(Q):
            continue
        d = distances(Q, S)
        dans = np.zeros(len(Q), dtype=bool)
        for r in rects:                                   # centre sous un element : distance 0
            x0, y0 = r.min(axis=0)
            x1, y1 = r.max(axis=0)
            m = (Q[:, 0] > x0) & (Q[:, 0] < x1) & (Q[:, 1] > y0) & (Q[:, 1] < y1)
            if m.any():                                   # quadrilatere convexe : meme signe des 4 produits vectoriels
                q = Q[m]
                cr = np.stack([(r[(k + 1) % 4, 0] - r[k, 0]) * (q[:, 1] - r[k, 1]) -
                               (r[(k + 1) % 4, 1] - r[k, 1]) * (q[:, 0] - r[k, 0]) for k in range(4)], axis=1)
                dans[np.where(m)[0][(cr >= 0).all(axis=1) | (cr <= 0).all(axis=1)]] = True
        d[dans] = 0.0
        rapport['par_mesh'][nom] = {'n': int(len(Q)), 'sous_015': int((d < SEUIL).sum()),
                                    'part_sous_015': round(float((d < SEUIL).mean()), 5),
                                    'd_min_m': round(float(d.min()), 3), 'd_p01_m': round(float(np.percentile(d, 1)), 3)}
    tot = sum(v['n'] for v in rapport['par_mesh'].values())
    sous = sum(v['sous_015'] for v in rapport['par_mesh'].values())
    rapport['total'] = {'n': tot, 'sous_015': sous, 'part_sous_015': round(sous / max(tot, 1), 5)}
    with open(sortie, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    return rapport


if __name__ == '__main__':
    print(json.dumps(principal(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=1))
