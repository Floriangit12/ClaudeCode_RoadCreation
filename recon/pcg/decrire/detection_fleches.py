"""Détection des flèches directionnelles rectifiée par voie (DET-FLE-003 ortho 2022, DET-FLE-004 plan 2025,
DET-FLE-005 a priori de réseau, DET-FLE-006 typage par parties, DET-FLE-008 glyphe hors bibliothèque).

Pour chaque voie « driving » des routes hors jonction : bande rééchantillonnée à 5 cm dans le repère de la voie
(lignes = sens de circulation, colonnes = écart latéral x ∈ [−1,6 ; 1,6] m, x > 0 à droite), top-hat (DET-PRE-002),
NCC axiale des 5 gabarits IISR (± 4°) et d'un gabarit concurrent « tiret » 3,00 x 0,12 m ; origine bornée à
|x| ≤ 0,5 m (± 1,5 m sur voie de plus de 4 m) ; suppression des non-maxima sur 5 m.
Acceptation : NCC ≥ 0,75 (ortho) / 0,80 (plan) ; candidat à 0,60 / 0,65 avec une marge ≥ 0,05 sur le tiret.
Typage (DET-FLE-006) : S0 = NCC(TD), SD = NCC(TD_TAD), SG = NCC(TD_TAG) ; (1) max(TAG, TAD) − S0 ≥ 0,15 -> flèche
tournante seule ; (2) SD et SG ≥ S0 − 0,05 et |SD − SG| < 0,07 -> trident / glyphe à revoir (jamais posé) ;
(3) |SD − SG| ≥ 0,07 -> combinée du côté du maximum ; (4) sinon TD.
Seules les rangées dont la zone admet la source sont retenues (FUS-SRC-001) ; option `toutes_zones` pour mesurer la
précision du détecteur contre le levé GAM.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_commun as D  # noqa: E402
import marquages_commun as M  # noqa: E402
import marquages_sources as S  # noqa: E402
import xodr_echantillonne as X  # noqa: E402

XW = 1.6
TYPES = ("TD", "TAD", "TAG", "TD_TAD", "TD_TAG")
SEUILS = {"ortho2022": (0.75, 0.60), "plan2025": (0.80, 0.65)}
DECALAGE_TIGE = {"TD": 0.0, "TAD": -0.425, "TAG": 0.425, "TD_TAD": -0.275, "TD_TAG": 0.275}   # MQ-FLE-006


def voies(reseau, pas=D.PX):
    """Axes des voies « driving » hors jonction dans le sens de circulation (local) : [{cle, route, voie, section_s,
    C (N, 2), D, Rt, s (N,), largeur_m}]."""
    out = []
    for rid in sorted(reseau, key=int):
        if int(rid) >= 100:
            continue
        r = reseau[rid]
        for sec in r.sections:
            for v in sorted(sec.voies):
                ln = sec.voies[v]
                if v == 0 or ln.type != "driving":
                    continue
                s = np.arange(sec.s, sec.s1, pas)
                if len(s) < 120:
                    continue
                tb = r.t_bords(s, sec)
                vi = v + 1 if v < 0 else v - 1
                tm = 0.5 * (tb[v] + tb[vi])
                x, y, h = X.point_st(r, s, tm)
                C = np.c_[x, y]
                if v > 0:
                    C, s = C[::-1], s[::-1]
                d = np.gradient(C, axis=0)
                d /= np.linalg.norm(d, axis=1, keepdims=True)
                out.append({"cle": f"R{rid}/s{sec.s:g}/v{v}", "route": rid, "voie": v, "section_s": sec.s, "C": C, "D": d,
                            "Rt": np.c_[d[:, 1], -d[:, 0]], "s": s, "largeur_m": float(np.median(np.abs(tb[v] - tb[vi])))})
    return out


def _bande(raster, ln):
    xs = np.arange(-XW, XW + 1e-9, D.PX)
    Q = ln["C"][:, None, :] + xs[None, :, None] * ln["Rt"][:, None, :]
    lum = D.RASTERS[raster](Q.reshape(-1, 2)).reshape(len(ln["C"]), len(xs))
    return lum, xs


def detecter(reseau, raster, toutes_zones=False):
    """Détections de flèches -> [{voie, s, x, origine (local), cap_deg, gabarit, ncc, ncc_tiret, scores, statut}]."""
    spec = M.spec()["gabarits"]
    tiret = [[np.array([[-0.06, 0.0], [0.06, 0.0], [0.06, 3.0], [-0.06, 3.0]])]]
    tau_sur, tau_cand = SEUILS[raster]
    out = []
    for ln in voies(reseau):
        lum, xs = _bande(raster, ln)
        ok = ~np.isnan(lum).any(axis=1)
        if not toutes_zones:
            src = "plan2025" if raster.startswith("plan") else raster
            ok &= np.array([S.admissible(src, e) for e in S.etat_zone(ln["C"])], bool)
        if ok.mean() < 0.05:
            continue
        lum = np.where(np.isnan(lum), np.nanmedian(lum), lum).astype(np.float32)
        img = D.tophat(lum)
        maps = {t: D.carte_origine(img, [[np.asarray(spec[t]["polygone"], float)]])[0] for t in TYPES}
        dm, _ = D.carte_origine(img, tiret)
        A = np.stack([maps[t] for t in TYPES])
        best = A.max(0)
        kbest = A.argmax(0)
        lim = 1.5 if ln["largeur_m"] > 4.0 else 0.5
        best[:, np.abs(xs) > lim] = -1
        best[~ok] = -1
        from numpy.lib.stride_tricks import sliding_window_view as swv
        pad = np.pad(dm, ((20, 20), (6, 6)), constant_values=-1)
        dloc = swv(pad, (41, 13)).max((-1, -2))
        rowbest, rowarg = best.max(1), best.argmax(1)
        ordre = np.argsort(-rowbest, kind="stable")
        pris = np.zeros(len(rowbest), bool)
        for i in ordre:
            if rowbest[i] < tau_cand:
                break
            if pris[max(0, i - 100):i + 100].any():
                continue
            pris[i] = True
            j = rowarg[i]
            sc = {t: float(maps[t][i, j]) for t in TYPES}
            ncc = float(rowbest[i])
            marge = ncc - float(dloc[i, j])
            if ncc < tau_sur and marge < 0.05:
                continue
            g, statut = typer(sc)
            o = ln["C"][i] + xs[j] * ln["Rt"][i]
            cap = math.degrees(math.atan2(ln["D"][i][1], ln["D"][i][0])) % 360.0
            out.append({"voie": ln["cle"], "route": ln["route"], "voie_id": ln["voie"], "section_s": ln["section_s"],
                        "s": round(float(ln["s"][i]), 3), "x": round(float(xs[j]), 3), "origine": o, "cap_deg": round(cap, 3),
                        "gabarit": g, "ncc": round(ncc, 3), "ncc_tiret": round(float(dloc[i, j]), 3),
                        "scores": {t: round(v, 3) for t, v in sc.items()}, "statut": statut,
                        "sur": ncc >= tau_sur, "largeur_voie_m": round(ln["largeur_m"], 2), "source": raster})
    return out


def typer(sc):
    """DET-FLE-006 : typage par parties -> (gabarit ou None, statut)."""
    S0, SD, SG = sc["TD"], sc["TD_TAD"], sc["TD_TAG"]
    tourn = max(sc["TAG"], sc["TAD"])
    if tourn - S0 >= 0.15:
        return ("TAG" if sc["TAG"] >= sc["TAD"] else "TAD"), "tournante"
    if SD >= S0 - 0.05 and SG >= S0 - 0.05 and abs(SD - SG) < 0.07:
        return None, "trident_ou_glyphe_a_revoir"          # DET-FLE-008 : jamais posé
    if abs(SD - SG) >= 0.07:
        return ("TD_TAD" if SD > SG else "TD_TAG"), "combinee"
    return "TD", "tout_droit"
