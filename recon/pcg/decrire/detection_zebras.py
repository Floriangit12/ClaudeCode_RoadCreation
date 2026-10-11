"""Détection des passages piétons par périodicité (DET-ZEB-009), sans indice : balayage des chaussées OpenDRIVE.

Pour chaque route hors jonction, tous les 0,25 m de s : profil en travers de la chaussée (t de la rive gauche à la
rive droite des voies roulables, pas 2 cm), moyenné sur ± 0,8 m en s (≈ 60 % d'une bande de 2,5-3,5 m), sur le
top-hat du raster admissible (DET-PRE-002) ; spectre (FFT, fenêtre de Hann) : pic du pas dans [0,8 ; 1,6] m ;
« pic sur fond » = amplitude du pic / médiane du spectre dans [0,2 ; 3] cycles/m. Candidat si pic/fond ≥ 8 ;
maxima locaux espacés de 4 m. Mesures au candidat : étendue en s des rangées périodiques (longueur de bande),
positions des bandes (plages claires du profil moyen), pas (médiane), nombre de bandes (≥ 3).
c_detection = clip((pic/fond − 4) / 12) (FUS-SCO-002).
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_commun as D  # noqa: E402
import marquages_sources as S  # noqa: E402
import xodr_echantillonne as X  # noqa: E402

PAS_S, PAS_T, DEMI_S = 0.25, 0.02, 0.8
ROULABLES = ("driving", "biking", "bus", "parking", "median", "border")
PIC_MIN = 8.0


def _etendue_t(route, sec, s):
    tb = route.t_bords(np.array([s]), sec)
    ts = [float(v[0]) for k, v in tb.items()]
    ids = sorted(sec.voies)
    lo, hi = None, None
    for v in ids:
        if v == 0 or sec.voies[v].type not in ROULABLES:
            continue
        vi = v + 1 if v < 0 else v - 1
        a, b = sorted((float(tb[v][0]), float(tb[vi][0])))
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    return lo, hi


def bande_section(raster, route, sec, toutes_zones):
    """Bande rectifiée d'une laneSection : s au pas de 0,1 m, t au pas de 2 cm sur l'étendue roulable (± 1 m) ;
    top-hat en travers (1,2 m) ; rangées hors zone admissible ou hors raster : NaN. -> (s, t, th, ext (t0, t1) par s)."""
    s = np.arange(sec.s + 0.2, sec.s1 - 0.2, 0.1)
    if len(s) < 20:
        return None
    ext = [_etendue_t(route, sec, x) for x in s]
    t0s = np.array([e[0] if e[0] is not None else np.nan for e in ext])
    t1s = np.array([e[1] if e[1] is not None else np.nan for e in ext])
    if np.isnan(t0s).all():
        return None
    t = np.arange(np.nanmin(t0s) - 1.0, np.nanmax(t1s) + 1.0 + 1e-9, PAS_T)
    x, y, h = X.point_st(route, np.repeat(s, len(t)), np.tile(t, len(s)))
    Q = np.c_[x, y]
    v = D.RASTERS[raster](Q).reshape(len(s), len(t))
    if not toutes_zones:
        src = "plan2025" if raster.startswith("plan") else raster
        xc, yc, _ = X.point_st(route, s, np.nan_to_num(0.5 * (t0s + t1s)))
        adm = np.array([S.admissible(src, e) for e in S.etat_zone(np.c_[xc, yc])], bool)
        v[~adm] = np.nan
    ok = ~np.isnan(v)
    if ok.mean() < 0.02:
        return None
    fond = float(np.nanmedian(v))
    im = np.where(ok, v, fond).astype(np.float32)
    th = D.tophat(im, se_m=1.2, px=PAS_T)
    th[~ok] = 0.0
    dehors = (t[None, :] < t0s[:, None] - 0.5) | (t[None, :] > t1s[:, None] + 0.5) | np.isnan(t0s)[:, None]
    th[dehors] = 0.0
    return s, t, th, t0s, t1s, ok.mean(axis=1) > 0.7


def spectre(p, pas=PAS_T):
    p = p - p.mean()
    n = 8192
    F = np.abs(np.fft.rfft(p * np.hanning(len(p)), n))
    fr = np.fft.rfftfreq(n, pas)
    bande = (fr > 1 / 1.6) & (fr < 1 / 0.8)
    if not bande.any():
        return None, 0.0
    k = int(np.argmax(np.where(bande, F, 0)))
    fond = float(np.median(F[(fr > 0.2) & (fr < 3)]))
    return 1.0 / fr[k], float(F[k] / max(fond, 1e-9))


def balayer(reseau, raster, toutes_zones=False):
    """Candidats zébras mesurés : [{route, section_s, s, s_min, s_max, t_bandes, pas_m, nb_bandes, pic_sur_fond, ...}]."""
    out = []
    k = int(round(DEMI_S / 0.1))
    for rid in sorted(reseau, key=int):
        if int(rid) >= 100:
            continue
        r = reseau[rid]
        for sec in r.sections:
            b = bande_section(raster, r, sec, toutes_zones)
            if b is None:
                continue
            s, t, th, t0s, t1s, okr = b
            cs = np.cumsum(np.vstack([np.zeros((1, th.shape[1])), th]), axis=0)
            pf = np.zeros(len(s))
            per = np.zeros(len(s))
            for i in range(0, len(s), int(round(PAS_S / 0.1))):
                i0, i1 = max(0, i - k), min(len(s), i + k + 1)
                if not okr[i] or np.isnan(t0s[i]):
                    continue
                prof = (cs[i1] - cs[i0]) / (i1 - i0)
                m = (t >= t0s[i] - 0.5) & (t <= t1s[i] + 0.5)
                if m.sum() < 60:
                    continue
                per[i], pf[i] = spectre(prof[m])
            for i in np.argsort(-pf, kind="stable"):
                if pf[i] < PIC_MIN:
                    break
                if any(o["route"] == rid and o["section_s"] == sec.s and abs(o["s"] - s[i]) < 4.0 for o in out):
                    continue
                ext = [j for j in range(len(s)) if abs(s[j] - s[i]) <= 4.0 and pf[j] >= 0.5 * pf[i]]
                j0, j1 = min(ext), max(ext)
                prof = th[max(0, j0 - k):j1 + k + 1].mean(axis=0)
                mes = _bandes(t, prof)
                if mes is None:
                    continue
                # longueur de bande : rangées où le top-hat moyen aux positions des bandes dépasse la moitié de son maximum
                tb_ = np.array(mes["t_bandes"])
                cols = np.zeros(len(t), bool)
                for tb1 in tb_:
                    cols |= np.abs(t - tb1) <= 0.12
                jj = np.arange(max(0, j0 - 40), min(len(s), j1 + 41))
                e_r = th[jj][:, cols].mean(axis=1)
                fort = e_r >= 0.5 * float(e_r.max())
                ic = int(np.argmax(e_r))
                a_, b_ = ic, ic
                while a_ - 1 >= 0 and fort[a_ - 1]:
                    a_ -= 1
                while b_ + 1 < len(jj) and fort[b_ + 1]:
                    b_ += 1
                j0, j1 = int(jj[a_]), int(jj[b_])
                sm = 0.5 * (s[j0] + s[j1])
                tc = float(np.mean(mes["t_bandes"]))
                x, y, h = X.point_st(r, np.array([sm]), np.array([tc]))
                out.append(dict(mes, route=rid, section_s=sec.s, s=round(float(s[i]), 2),
                                s_min=round(float(s[j0] - DEMI_S), 2), s_max=round(float(s[j1] + DEMI_S), 2),
                                pic_sur_fond=round(float(pf[i]), 1), xy=np.array([x[0], y[0]]),
                                cap_route_deg=round(math.degrees(h[0]) % 360.0, 3), source=raster,
                                longueur_bande_m=round(float(s[j1] - s[j0] + 0.1), 2)))
    return out


def _bandes(t, p):
    """Plages claires du profil moyen (largeur 0,30-0,75 m) -> positions, pas, nombre (≥ 3) ou None."""
    seuil = 0.5 * float(np.percentile(p, 98))
    if seuil <= 5.0:
        return None
    clair = p > seuil
    bandes = []
    i = 0
    while i < len(t):
        if clair[i]:
            j = i
            while j + 1 < len(t) and clair[j + 1]:
                j += 1
            w = (j - i + 1) * PAS_T
            if 0.3 <= w <= 0.75:
                bandes.append(0.5 * (t[i] + t[j]))
            i = j + 1
        else:
            i += 1
    if len(bandes) < 3:
        return None
    b = np.array(bandes)
    d = np.diff(b)
    pas = float(np.median(d))
    if not (0.8 <= pas <= 1.6):
        return None
    return {"t_bandes": [round(float(x), 3) for x in b], "pas_m": round(pas, 3), "nb_bandes": int(len(b))}


def c_detection(pf):
    return D.clip01((pf - 4.0) / 12.0)
