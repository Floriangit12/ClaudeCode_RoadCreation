"""Détection des lignes longitudinales sur image le long d'un guide (DET-LIG-010, DET-LIG-011, DET-PLN-016, TQ-DED-002).

Guide : bord de voie OpenDRIVE (chaîne de bords marquages_lignes.ChaineBord, routes hors jonction, bords dont les
deux voies voisines sont roulables : driving, biking, bus, parking) ou axe d'un indice v1 (marque v1 linéaire hors des
bords de voie, couloir élargi).
Méthode (repère du guide : σ le long, t à gauche) :
- bande rectifiée (σ au pas de 5 cm, t de −0,6 à +0,6 m au pas de 2,5 cm) sur le raster admissible de la zone (ortho
  2022 en zone conservée, plan 2025 inversé dans la zone des travaux) ;
- top-hat 1D en travers (ouverture de 0,50 m : marques de 0,10 à 0,30 m, DET-LIG-010) ; rangée « peinte » si le
  maximum dans le couloir (|t| ≤ 0,40 m) dépasse le seuil de vraisemblance (DET-PRE-002 : 25 DN sur l'ortho ; 60 sur
  le plan inversé, traits CAO) et si moins de 60 % de la rangée est claire (bande de zébra ou aplat traversant) ;
- plages peintes (trous ≤ 0,15 m comblés, plages < 0,30 m écartées), décalage t médian et contraste par plage ;
- modulation (DET-LIG-011) : plage ≥ 8 m -> trait continu ; suites de tirets (0,3-6,5 m) -> modèle IISR ajusté
  (marquages_lignes.ajuster : T1, T'1, T2, T3, T'3, T'2 à ± 10 % ; sinon modulation mesurée « _site ») ; la suite
  modélisée comble les tirets masqués (TQ-DED-002) entre le premier et le dernier tiret observés ; phase mesurée sur
  l'image (DET-PLN-016 : sur le plan, présence, type et position seulement ; la phase n'y est pas fiable).
c_detection (FUS-SCO-002) = fraction de la longueur modélisée effectivement vue peinte.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_commun as D  # noqa: E402
import marquages_lignes as LG  # noqa: E402
import marquages_sources as S  # noqa: E402
from commun import abscisses, densifier, point_a  # noqa: E402

PAS_S, PAS_T, DEMI = 0.05, 0.025, 0.6
COULOIR = 0.40
SEUILS = {"ortho2022": 25.0, "plan2025": 60.0, "plan2025_orange": 60.0}
ROULABLES = ("driving", "biking", "bus", "parking")
LONG_CONTINU = 8.0
CODES_ESSAI = ("T3", "T'1", "T2", "T1", "T'3", "T'2")


def bande(raster, P, demi=DEMI):
    """Bande rectifiée le long de la polyligne P : (σ (N,), t (M,), image (N, M) NaN hors raster, points (N, 2),
    tangentes (N, 2))."""
    P = np.asarray(P, float)
    L = float(abscisses(P)[-1])
    sig = np.arange(0.0, L + 1e-9, PAS_S)
    Q, tg = point_a(P, sig)
    n = np.c_[-tg[:, 1], tg[:, 0]]
    t = np.arange(-demi, demi + 1e-9, PAS_T)
    G = Q[:, None, :] + t[None, :, None] * n[:, None, :]
    img = D.RASTERS[raster](G.reshape(-1, 2)).reshape(len(sig), len(t))
    return sig, t, img, Q, tg


def tophat_travers(img, largeur_m=0.50):
    """Top-hat 1D en travers (ouverture min puis max sur largeur_m)."""
    from numpy.lib.stride_tricks import sliding_window_view as swv
    k = int(round(largeur_m / PAS_T)) | 1
    h = k // 2
    a = np.pad(img, ((0, 0), (h, h)), mode="edge")
    mn = swv(a, k, axis=1).min(axis=2)
    b = np.pad(mn, ((0, 0), (h, h)), mode="edge")
    op = swv(b, k, axis=1).max(axis=2)
    return img - op


def detecter(raster, P, couloir=COULOIR, seuil=None, masque_zone=None):
    """Plages peintes le long de P : dict {sig, peint (N,), t_crete (N,), contraste (N,), plages [(σ0, σ1, t, c)],
    valide (N,)} ; masque_zone (N,) : rangées admissibles (zone)."""
    seuil = SEUILS[raster] if seuil is None else seuil
    sig, t, img, Q, tg = bande(raster, P)
    valide = ~np.isnan(img).any(axis=1)
    if masque_zone is not None:
        valide &= masque_zone(Q)
    if not valide.any():
        return {"sig": sig, "peint": np.zeros(len(sig), bool), "plages": [], "valide": valide, "Q": Q}
    fond = np.nanmedian(img)
    im = np.where(np.isnan(img), fond, img)
    th = tophat_travers(im)
    dans = np.abs(t) <= couloir
    sub = th[:, dans]
    j = np.argmax(sub, axis=1)
    v = sub[np.arange(len(sig)), j]
    tc = t[dans][j]
    clair = (th > seuil).mean(axis=1)
    peint = valide & (v >= seuil) & (clair < 0.6)
    plages = _plages(sig, peint)
    out = []
    for a, b in plages:
        m = (sig >= a - 1e-9) & (sig <= b + 1e-9) & peint
        out.append((round(a, 3), round(b, 3), float(np.median(tc[m])), float(np.median(v[m]))))
    return {"sig": sig, "peint": peint, "t_crete": tc, "contraste": v, "plages": out, "valide": valide, "Q": Q}


def _plages(sig, m, trou=0.15, lmin=0.30):
    iv = []
    i = 0
    n = len(m)
    while i < n:
        if not m[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and m[j + 1]:
            j += 1
        iv.append([sig[i], sig[j] + PAS_S])
        i = j + 1
    out = []
    for a, b in iv:
        if out and a - out[-1][1] <= trou:
            out[-1][1] = b
        else:
            out.append([a, b])
    return [(a, b) for a, b in out if b - a >= lmin]


def _suite(grp, i, code):
    """Tirets de grp (triés) qui suivent le motif IISR `code` à partir du tiret i : indices retenus et phase (début
    du tiret i) ; tolérances : début ou fin à ± 0,20 m du motif, longueur 0,4-1,3 trait, trou ≤ 3 périodes."""
    tab = LG.modulations()
    T, P = tab[code]["trait_m"], tab[code]["periode_m"]
    a_i, b_i = grp[i][0], grp[i][1]
    if not (0.6 * T <= b_i - a_i <= 1.3 * T + 0.1):
        return [i], a_i
    phi = a_i
    pris = [i]
    for k in range(i + 1, len(grp)):
        a, b = grp[k][0], grp[k][1]
        if a - grp[pris[-1]][1] > 3 * P:
            break
        n = round((a - phi) / P)
        ra, rb = a - (phi + n * P), b - (phi + n * P + T)
        if (abs(ra) <= 0.20 or abs(rb) <= 0.20) and 0.4 * T <= b - a <= 1.3 * T + 0.1:
            pris.append(k)
    return pris, phi


def modeliser(plages, longueur, ecart_max=14.0):
    """Plages peintes -> morceaux de ligne [{type, sigma0, sigma1, code, trait_m, vide_m, phase_m, n_vus, couverture, t}].
    1. plages ≥ LONG_CONTINU : traits continus ;
    2. tirets : suites gloutonnes qui suivent un motif IISR (DET-LIG-011, T3 / T'1 / T2 / T1 / T'3 / T'2, tolérance
       ± 0,20 m sur les débuts ou fins, au plus 2 tirets manquants consécutifs) ; le motif qui enchaîne le plus de tirets
       l'emporte ; au moins 3 tirets vus -> ligne discontinue modélisée du premier au dernier tiret vu, phase par
       moyenne des écarts (TQ-DED-002 : tirets masqués reconstruits) ;
    3. plages restantes ≥ 1 m : segments isolés (c_detection 0,5)."""
    out = []
    pl = sorted(plages)
    for g in pl:
        if g[1] - g[0] >= LONG_CONTINU:
            out.append({"type": "continue", "sigma0": g[0], "sigma1": g[1], "n_vus": 1, "couverture": 1.0, "t": g[2]})
    grp = [g for g in pl if g[1] - g[0] < LONG_CONTINU]
    tab = LG.modulations()
    libres = set(range(len(grp)))
    while True:
        best = None
        for i in sorted(libres):
            sous = [grp[k] for k in sorted(libres) if k >= i]
            for code in CODES_ESSAI:
                idx, phi = _suite(sous, 0, code)
                if len(idx) >= 3 and (best is None or len(idx) > len(best[0])):
                    best = ([sorted(k for k in libres if k >= i)[j] for j in idx], phi, code)
        if best is None:
            break
        idx, phi, code = best
        T, P = tab[code]["trait_m"], tab[code]["periode_m"]
        ecarts = [grp[k][0] - (phi + round((grp[k][0] - phi) / P) * P) for k in idx if grp[k][1] - grp[k][0] >= 0.85 * T]
        phi += float(np.median(ecarts)) if ecarts else 0.0
        deb = phi + math.floor((grp[idx[0]][0] - phi) / P + 0.5) * P
        fin_dernier = phi + math.floor((grp[idx[-1]][0] - phi) / P + 0.5) * P + T
        n = int(round((fin_dernier - T - deb) / P)) + 1
        vus = sum(grp[k][1] - grp[k][0] for k in idx)
        out.append({"type": "discontinue", "sigma0": deb, "sigma1": fin_dernier, "code": code, "modulation_source": "IISR",
                    "trait_m": T, "vide_m": round(P - T, 3), "phase_m": 0.0, "n_vus": len(idx), "n_tirets": n,
                    "couverture": round(min(1.0, vus / max(n * T, 1e-6)), 3),
                    "t": float(np.median([grp[k][2] for k in idx]))})
        libres -= set(idx)
        # les plages restantes recouvertes par la suite modélisée sont absorbées
        libres -= {k for k in libres if grp[k][0] >= deb - 0.1 and grp[k][1] <= fin_dernier + 0.1}
    for k in sorted(libres):
        g = grp[k]
        if g[1] - g[0] >= 1.0:
            out.append({"type": "segment", "sigma0": g[0], "sigma1": g[1], "n_vus": 1, "couverture": 0.5, "t": g[2]})
    return sorted(out, key=lambda m: m["sigma0"])


def guides_detectables(reseau):
    """Guides de détection : morceaux de chaînes de bords (routes hors jonction) formés de bords consécutifs dont les
    deux voies voisines sont roulables -> [(chaîne, s0, s1)]."""
    out = []
    for ch in LG.chaines_reseau(reseau):
        if int(ch.route) >= 100:
            continue
        r = reseau[ch.route]
        cur = None
        for b in ch.bords:
            sec = next(x for x in r.sections if abs(x.s - b.section_s) < 1e-6)
            if b.voie == 0:
                cotes = [sec.voies.get(1), sec.voies.get(-1)]
            else:
                sg = 1 if b.voie > 0 else -1
                cotes = [sec.voies.get(b.voie), sec.voies.get(b.voie + sg)]
            ok = all(c is not None and c.type in ROULABLES for c in cotes)
            if ok:
                cur = [cur[0], b.s1] if cur else [b.s0, b.s1]
            elif cur:
                out.append((ch, cur[0], cur[1]))
                cur = None
        if cur:
            out.append((ch, cur[0], cur[1]))
    return [(ch, a, b) for ch, a, b in out if b - a >= 5.0]


def masque_admissible(raster):
    src = "plan2025" if raster.startswith("plan") else raster

    def f(Q):
        e = S.etat_zone(Q)
        return np.array([S.admissible(src, x) for x in e], bool)
    return f


def lignes_bords(reseau, raster, admissible_seul=True):
    """Hypothèses de lignes détectées le long des bords de voie : [{chaine, route, s0, s1, t_off, type, ...}]."""
    out = []
    for ch, sa, sb in guides_detectables(reseau):
        G = ch.axe(0.0, sa, sb)
        det = detecter(raster, G, masque_zone=masque_admissible(raster) if admissible_seul else None)
        L = float(abscisses(G)[-1])
        sigG = abscisses(G)
        sG = np.interp(sigG, [0.0, L], [sa, sb]) if len(G) < 3 else None
        _, ss = ch.axe(0.0, sa, sb, avec_s=True)
        for m in modeliser(det["plages"], L):
            s0 = float(np.interp(max(0.0, m["sigma0"]), sigG, ss))
            s1 = float(np.interp(min(L, m["sigma1"]), sigG, ss))
            if s1 - s0 < 0.3:
                continue
            out.append(dict(m, chaine=ch.cle, route=ch.route, s0=s0, s1=s1, t_off=round(m["t"], 3), source=raster,
                            c_detection=m["couverture"]))
    return out
