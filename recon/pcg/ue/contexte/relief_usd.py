"""[hython] Couche relief.usdc : anneau de relief lointain (montagnes) autour du site (revue UE du 10/10 : horizon plat et
laiteux, Saint-Eynard, Chartreuse, Belledonne et Vercors absents ; aucun MNT regional hors ligne).

Profil de crete site(azimut vrai) :
- secteur 200-352 deg (Vercors, Bastille, Rachais, Neron, Saint-Eynard : visibles au-dessus des toits) : releve sur les
  photos 360 Panoramax (horizon.py -> ue_pilote/horizon/profil.json) ;
- secteur 10-190 deg (Chartreuse, Gresivaudan, Belledonne, Taillefer : masques par les arbres et les immeubles sur
  toutes les photos) : a priori de sommets connus (CRETES : azimut, site, distance ; sites calcules depuis les
  altitudes et les distances au site, approximatifs) ;
- raccords lineaires sur 190-200 et 352-370 deg.
Distance de la crete par azimut (DISTANCES, km) : perspective aerienne de SkyAtmosphere selon l'eloignement.
Maillage : 720 colonnes (0,5 deg) x 7 rangees, de la crete (d, h = d tan(site) - courbure) vers le pied (0,45 d, -20 m),
profil concave (pentes moyennes plus douces au pied) ; distance de crete lissee sur 10 deg (pas de pli entre secteurs) ;
hauteurs des rangees intermediaires modulees par un bruit de valeur deterministe (ravines) ; normales a cusp 30 deg ;
UV boite en m ; materiau PJ_Relief (M_PJ_Relief : foret, prairies et rochers selon la pente, contexte/ue/
materiaux_contexte.py). Une composante par secteur de 30 deg (culling).
Sol lointain (sol_lointain) : raccord du bord du terrain v1 (carre de 300 m) vers Z_PLAN sur 25 m, puis plan a Z_PLAN
jusqu'a 60 km (remplace le plan de contexte a -4,1 m qui laissait une marche de 1 a 6 m au bord du terrain v1).

    hython recon/pcg/ue/contexte/relief_usd.py [--sortie DOSSIER]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.dont_write_bytecode = True
import preparer_usd as PU  # noqa: E402

DEPOT = ICI.parents[3]
PROFIL = DEPOT / 'recon/out/paquet_jardin/v2/ue_pilote/horizon/profil.json'
# a priori (azimut vrai deg, site deg, distance km) : Chamechaude, Dent de Crolles, Gresivaudan, Grand Charnier,
# Croix de Belledonne, Grand Colon, Chamrousse, Taillefer, Trieves
CRETES = [(5, 15.0, 4.5), (10, 11.7, 9.0), (20, 10.0, 10.0), (31, 8.1, 13.0), (38, 6.5, 14.0), (45, 4.0, 20.0),
          (52, 3.0, 28.0), (60, 4.9, 27.0), (70, 5.5, 22.0), (80, 6.5, 19.0), (90, 7.5, 18.0), (100, 8.4, 18.0),
          (108, 7.6, 17.0), (115, 7.3, 17.0), (125, 8.0, 15.0), (133, 8.6, 13.4), (142, 7.2, 15.0), (155, 7.6, 19.7),
          (165, 5.0, 22.0), (175, 3.5, 25.0), (185, 2.8, 30.0), (195, 2.9, 35.0), (205, 3.2, 38.0)]
DISTANCES = [(0, 4.0), (5, 4.5), (10, 9.0), (31, 13.0), (52, 28.0), (100, 18.0), (133, 13.4), (155, 19.7), (195, 35.0),
             (212, 30.0), (220, 13.0), (250, 5.0), (300, 4.5), (330, 3.6), (353, 3.3), (360, 4.0)]
SECTEUR_PHOTO = (200.0, 352.0)
RACCORD = 10.0
RANGEES = [(1.00, 1.00), (0.93, 0.82), (0.85, 0.65), (0.76, 0.48), (0.66, 0.32), (0.56, 0.17), (0.45, None)]
LISSAGE_DISTANCE_DEG = 10.0       # moyenne glissante de la distance de crete (pas de pli entre secteurs)
Z_PIED = -20.0
R_TERRE = 6371000.0
K_REFRACTION = 0.13


def interp_circ(az, pts):
    a = np.array([p[0] for p in pts], dtype=float)
    v = np.array([p[1] for p in pts], dtype=float)
    return np.interp(az % 360.0, np.r_[a - 360, a, a + 360], np.r_[v, v, v])


def bruit(u, v, graine=2154):
    """Bruit de valeur 2D deterministe (grille entiere, interpolation lisse), dans [-1, 1]."""
    def h(i, j):
        x = (i * 374761393 + j * 668265263 + graine * 2147483647) & 0xFFFFFFFF
        x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
        return (x / 0xFFFFFFFF) * 2.0 - 1.0
    i0, j0 = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fu, fv = u - i0, v - j0
    su, sv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    hv = np.vectorize(h)
    a, b, c, d = hv(i0, j0), hv(i0 + 1, j0), hv(i0, j0 + 1), hv(i0 + 1, j0 + 1)
    return (a * (1 - su) + b * su) * (1 - sv) + (c * (1 - su) + d * su) * sv


def profil():
    """(azimuts, site de crete deg, distance m) par pas de 0,5 deg."""
    az = np.arange(0.0, 360.0, 0.5)
    photo = np.array(json.load(open(PROFIL, encoding='utf-8'))['site_deg'], dtype=float)
    e_ph = np.interp(az, np.r_[np.arange(360) - 360, np.arange(360), np.arange(360) + 360] + 0.5, np.r_[photo, photo, photo])
    e_pr = interp_circ(az, [(a, e) for a, e, _ in CRETES])
    e_pr = e_pr + 0.35 * bruit(az / 3.0, np.zeros_like(az), 7) + 0.2 * bruit(az / 0.8, np.ones_like(az), 11) +         0.1 * bruit(az / 0.3, np.full_like(az, 2.0), 13)
    a0, a1 = SECTEUR_PHOTO
    w = np.clip(np.minimum((az - (a0 - RACCORD)) / RACCORD, ((a1 + RACCORD) - az) / RACCORD), 0.0, 1.0)
    w = np.where((az >= a0) & (az <= a1), 1.0, w)
    w = np.maximum(w, np.clip(((a1 + RACCORD) - (az + 360.0)) / RACCORD, 0.0, 1.0))      # raccord au-dela de 360
    e = w * e_ph + (1 - w) * e_pr
    d = interp_circ(az, DISTANCES) * 1000.0
    k = int(round(LISSAGE_DISTANCE_DEG / 0.5))
    d = np.convolve(np.r_[d[-k:], d, d[:k]], np.ones(2 * k + 1) / (2 * k + 1), mode='valid')
    return az, e, d, w


def sol_lointain(co, sortie, cote=150.0, raccord=25.0, rayon=60000.0, pas=2.0):
    """Sol au-dela du carre v1 (revue UE du 10/10 : plan de contexte a -4,1 m, marche de 1 a 6 m au bord du terrain v1) :
    raccord de RACCORD m depuis l'altitude du bord du terrain v1 (contexte_v1.usdc, sommets a |x| ou |y| = 150 m) vers
    Z_PLAN (lointain.Z_PLAN, mediane du bord), puis plan a Z_PLAN jusqu'a RAYON (60 km, au-dela des pieds du relief). Materiau
    PJ_Contexte_Lointain (UV monde)."""
    import lointain
    from pxr import Usd, UsdGeom
    z_plan = float(lointain.Z_PLAN)
    st = Usd.Stage.Open(str(sortie / 'contexte_v1.usdc'))
    B = []
    for p in st.Traverse():
        if p.IsA(UsdGeom.Mesh) and '/Sol_' in str(p.GetPath()):
            Q = np.array(UsdGeom.Mesh(p).GetPointsAttr().Get(), dtype=float)
            B.append(Q[(np.abs(Q[:, 0]) > cote - 0.05) | (np.abs(Q[:, 1]) > cote - 0.05)])
    B = np.vstack(B)

    def t_perim(x, y):
        """Abscisse sur le perimetre du carre (sens trigo depuis (cote, -cote))."""
        c = cote
        return np.where(np.isclose(x, c, atol=0.06), y + c,
               np.where(np.isclose(y, c, atol=0.06), 2 * c + (c - x),
               np.where(np.isclose(x, -c, atol=0.06), 4 * c + (c - y), 6 * c + (x + c))))
    tb = t_perim(B[:, 0], B[:, 1])
    o = np.argsort(tb)
    tb, zb = tb[o], B[o, 2]
    L = 8 * cote
    t = np.arange(0.0, L, pas)
    z_in = np.interp(t, np.r_[tb - L, tb, tb + L], np.r_[zb, zb, zb])

    def point(tt, c):
        tt = tt % L
        q, r = np.floor_divide(tt, 2 * cote), np.mod(tt, 2 * cote) / (2 * cote)
        f = cote / c
        x = np.select([q == 0, q == 1, q == 2, q == 3], [cote, cote - 2 * cote * r, -cote, -cote + 2 * cote * r]) / f
        y = np.select([q == 0, q == 1, q == 2, q == 3], [-cote + 2 * cote * r, cote, cote - 2 * cote * r, -cote]) / f
        return x, y
    xi, yi = point(t, cote)
    xo, yo = point(t, cote + raccord)
    xf, yf = point(t, rayon)
    n = len(t)
    P = np.vstack([np.c_[xi, yi, z_in], np.c_[xo, yo, np.full(n, z_plan)], np.c_[xf, yf, np.full(n, z_plan)]])
    T = []
    for k in range(2):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            c_, d_ = (k + 1) * n + j, (k + 1) * n + (j + 1) % n
            T += [(a, b, c_), (b, d_, c_)]
    T = np.array(T)
    co.groupe('/World/Sol_Lointain')
    co.composant('/World/Sol_Lointain/Sol_Lointain')
    co.maillage('/World/Sol_Lointain/Sol_Lointain/sol', P, T, 'PJ_Contexte_Lointain', P[:, :2])
    return {'z_plan': z_plan, 'bord_v1_z': [round(float(np.percentile(zb, q)), 2) for q in (5, 50, 95)],
            'raccord_m': raccord, 'rayon_m': rayon, 'triangles': int(len(T))}


def normales_lisses(P, T):
    """Normales par sommet, moyenne des faces ponderee par l'aire (relief vu a 3-35 km : pas d'arete vive ; la couche
    declare pj:cusp_deg = 180)."""
    n = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, T[:, k], n)
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    # par sommet de face ; face tres inclinee par rapport a la normale moyenne (repli entre deux colonnes dont la
    # distance de crete change vite) : normale de la face
    nf = n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    Nf = N[T]                                                  # (m, 3, 3)
    ok = np.einsum('mkj,mj->mk', Nf, nf) > 0.3
    Nf = np.where(ok[..., None], Nf, nf[:, None, :])
    return Nf.reshape(-1, 3)


def construire(sortie):
    az, e, d, w = profil()
    n, nr = len(az), len(RANGEES)
    P = np.zeros((nr, n, 3))
    ar = np.radians(az)
    for k, (fd, fh) in enumerate(RANGEES):
        dk = d * fd * (1.0 + 0.03 * bruit(az / 1.5, np.full(n, 3.0 * k), 23) * (0 < k < nr - 1))
        if fh is None:
            z = np.full(n, Z_PIED)
        else:
            h = d * np.tan(np.radians(e))
            m = 1.0 + (0.10 * bruit(az / 1.2, np.full(n, 5.0 * k), 31) if 0 < k < nr - 1 else 0.0)
            z = h * fh * m - dk * dk / (2.0 * R_TERRE) * (1.0 - K_REFRACTION)
        P[k, :, 0] = dk * np.sin(ar)                        # azimut vrai depuis le nord, sens horaire (repere L93 local)
        P[k, :, 1] = dk * np.cos(ar)
        P[k, :, 2] = z
    # azimut vrai -> quadrillage L93 : rotation de la convergence des meridiens (az_grille = az_vrai - 2,0086)
    c = math.radians(2.0086)
    x, y = P[..., 0].copy(), P[..., 1].copy()
    P[..., 0] = x * math.cos(c) - y * math.sin(c)
    P[..., 1] = x * math.sin(c) + y * math.cos(c)
    co = PU.Couche('Relief lointain (recon/pcg/ue/contexte/relief_usd.py) : anneau de cretes releve sur les photos 360 '
                   'Panoramax (200-352 deg) et a priori de sommets (Chartreuse, Belledonne), 3 a 35 km.')
    co.st.GetRootLayer().customLayerData = dict(co.st.GetRootLayer().customLayerData, **{'pj:cusp_deg': 180.0})
    co.groupe('/World/Relief')
    tri_total = 0
    for s in range(12):
        cols = [i % n for i in range(s * n // 12, (s + 1) * n // 12 + 1)]
        Pc = P[:, cols, :].reshape(-1, 3)
        m = len(cols)
        T = []
        for k in range(nr - 1):
            for j in range(m - 1):
                a, b = k * m + j, k * m + j + 1
                c_, d_ = (k + 1) * m + j, (k + 1) * m + j + 1
                T += [(a, c_, b), (b, c_, d_)]                # normales vers le site (face vue de l'interieur)
        T = np.array(T)
        comp = f'/World/Relief/Relief_{s * 30:03d}'
        co.composant(comp)
        co.maillage(f'{comp}/relief', Pc, T, 'PJ_Relief', PU.uv_boite(Pc, T), N=normales_lisses(Pc, T))
        tri_total += len(T)
    rap_sol = sol_lointain(co, sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    co.enregistrer(sortie / 'relief.usdc')
    rap = {'colonnes': n, 'rangees': nr, 'triangles': int(tri_total), 'sol_lointain': rap_sol, 'site_max_deg': round(float(e.max()), 2),
           'az_site_max': float(az[int(np.argmax(e))]), 'part_photo': round(float(w.mean()), 3),
           'distance_km': [round(float(d.min()) / 1000, 1), round(float(d.max()) / 1000, 1)],
           'profil': [[float(a), round(float(x), 2), round(float(y) / 1000, 2)] for a, x, y in zip(az[::10], e[::10], d[::10])]}
    json.dump(rap, open(sortie / 'relief.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return rap


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sortie', default=str(DEPOT / 'recon/out/paquet_jardin/v2/ue_pilote/usd'))
    a = ap.parse_args()
    r = construire(Path(a.sortie))
    print(json.dumps({k: v for k, v in r.items() if k != 'profil'}, ensure_ascii=False))
