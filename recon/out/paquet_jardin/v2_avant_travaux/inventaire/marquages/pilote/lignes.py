"""Lignes longitudinales (tirets et continues) : mesure sous-pixel, regroupement en files, modulation IISR.

1. Chaque composante « trait » (largeur <= 0,38 m) est rééchantillonnée dans son repère principal (u le long,
   v en travers) au pas de 1 cm en v ; par tranches de 0,10 m en u, bords gauche et droit au niveau 50 % de la
   luminance (plateau = maximum lissé, fond = médiane à 0,15-0,40 m de l'axe) ; ajustement d'une droite (ou d'une
   parabole au-delà de 8 m) sur les centres -> axe, largeur médiane, rectitude (RMS) ; extrémités au niveau 50 %
   sur le profil axial.
2. Files : tirets colinéaires (orientation à 3° près, écart latéral < 0,12 m, vide < 14 m).
3. Modulation : (trait, vide) médians comparés à la table IISR (T1, T'1, T2, T'2, T3, T'3) ; écart relatif.
"""
from __future__ import annotations

import math

import numpy as np

import commun_pilote as C
from zebras import _niveau50

MODULATIONS = {"T1": (3.0, 10.0), "T'1": (1.5, 5.0), "T2": (3.0, 3.5), "T'2": (0.5, 0.5), "T3": (3.0, 1.33), "T'3": (20.0, 6.0)}


def mesurer_trait(d, det, geo):
    L = det["cartes"]["L"]
    th = d["angle_rad"]
    eu = np.array([math.cos(th), math.sin(th)])
    ev = np.array([-math.sin(th), math.cos(th)])
    hl = 0.5 * d["long_m"] + 0.4
    uu = np.arange(-hl, hl, 0.02)
    vv = np.arange(-0.45, 0.45 + 1e-9, 0.01)
    UU, VV = np.meshgrid(uu, vv)
    X = d["cx"] + UU * eu[0] + VV * ev[0]
    Y = d["cy"] + UU * eu[1] + VV * ev[1]
    Lr = C.echantillonner(L, geo, X, Y)
    Pr = C.echantillonner(det["p"], geo, X, Y, defaut=0.0)
    lab = C.echantillonner((det["lab"] == d["id"]).astype(np.float32), geo, X, Y, defaut=0.0)
    # tranches
    pts = []
    for t0 in np.arange(-hl, hl, 0.10):
        sel = (uu >= t0) & (uu < t0 + 0.10)
        if not sel.any() or lab[:, sel].max() < 0.5:
            continue
        col = np.nanmean(Lr[:, sel], axis=1)
        pc = np.nanmean(Pr[:, sel], axis=1)
        if pc.max() < 0.5:
            continue
        im = int(np.argmax(np.convolve(pc, np.ones(5) / 5, mode="same")))
        fond = np.nanmedian(col[(np.abs(vv - vv[im]) > 0.15) & (np.abs(vv - vv[im]) < 0.40)])
        pl = np.nanmax(np.convolve(col, np.ones(3) / 3, mode="same")[max(0, im - 8):im + 9])
        if not (np.isfinite(fond) and np.isfinite(pl)) or pl - fond < 15:
            continue
        niv = 0.5 * (pl + fond)
        g = _niveau50(vv, col, niv, im, -1)
        dr = _niveau50(vv, col, niv, im, +1)
        if g is None or dr is None or not (0.04 < dr - g < 0.45):
            continue
        pts.append((t0 + 0.05, g, dr))
    if len(pts) < 4:
        return None
    P = np.array(pts)
    u, g, dr = P[:, 0], P[:, 1], P[:, 2]
    c = 0.5 * (g + dr)
    deg = 2 if (u.max() - u.min()) > 8 else 1
    coef = np.polyfit(u, c, deg)
    resid = c - np.polyval(coef, u)
    # extrémités : profil axial sur la bande centrale
    vc = np.polyval(coef, uu)
    prof = np.array([C.echantillonner(L, geo, d["cx"] + uu * eu[0] + (vc + o) * ev[0], d["cy"] + uu * eu[1] + (vc + o) * ev[1]) for o in (-0.02, 0.0, 0.02)])
    prof = np.nanmean(prof, axis=0)
    ia = int(np.argmin(np.abs(uu - u.min())))
    ib = int(np.argmin(np.abs(uu - u.max())))
    fond_ax = np.nanmedian(np.r_[prof[:max(1, ia - 10)][-15:], prof[ib + 10:][:15]]) if (ia > 10 or ib < len(uu) - 10) else np.nanmin(prof)
    pl_ax = np.nanmedian(prof[ia:ib + 1])
    niv = 0.5 * (pl_ax + fond_ax) if np.isfinite(fond_ax) else None
    ua = _niveau50(uu, prof, niv, ia, -1) if niv is not None else None
    ub = _niveau50(uu, prof, niv, ib, +1) if niv is not None else None
    ua = u.min() - 0.05 if ua is None or ua < u.min() - 0.4 else ua
    ub = u.max() + 0.05 if ub is None or ub > u.max() + 0.4 else ub
    larg = dr - g
    sa = np.linspace(ua, ub, max(2, int((ub - ua) / 0.25) + 1))
    sv = np.polyval(coef, sa)
    axe = np.c_[d["cx"] + sa * eu[0] + sv * ev[0], d["cy"] + sa * eu[1] + sv * ev[1]]
    tang = np.polyval(np.polyder(coef), 0.5 * (ua + ub))
    return {"composante": d["id"], "axe_l93": axe.tolist(), "longueur_m": float(ub - ua), "largeur_m": float(np.median(larg)),
            "largeur_p10_p90_m": [float(np.percentile(larg, 10)), float(np.percentile(larg, 90))],
            "rms_axe_m": float(np.sqrt(np.mean(resid ** 2))), "degre": deg, "n_tranches": int(len(u)),
            "angle_rad": float(th + math.atan(tang)), "milieu": axe[len(axe) // 2].tolist(),
            "debut": axe[0].tolist(), "fin": axe[-1].tolist()}


def regrouper(traits):
    n = len(traits)
    par = list(range(n))

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            a, b = traits[i], traits[j]
            if abs(C.ecart_axial(a["angle_rad"], b["angle_rad"])) > math.radians(3):
                continue
            th = C.angle_moyen_axial([a["angle_rad"], b["angle_rad"]])
            eu = np.array([math.cos(th), math.sin(th)])
            ev = np.array([-math.sin(th), math.cos(th)])
            d = np.array(b["milieu"]) - np.array(a["milieu"])
            lat = abs(d @ ev)
            lon = abs(d @ eu) - 0.5 * (a["longueur_m"] + b["longueur_m"])
            if lat < 0.12 and lon < 14.0:
                par[f(i)] = f(j)
    g = {}
    for i in range(n):
        g.setdefault(f(i), []).append(traits[i])
    return list(g.values())


def modulation(file_):
    if len(file_) < 2:
        return None
    th = C.angle_moyen_axial([t["angle_rad"] for t in file_])
    eu = np.array([math.cos(th), math.sin(th)])
    iv = sorted([(min(np.array(t["debut"]) @ eu, np.array(t["fin"]) @ eu), max(np.array(t["debut"]) @ eu, np.array(t["fin"]) @ eu)) for t in file_])
    traits = [b - a for a, b in iv]
    vides = [iv[k + 1][0] - iv[k][1] for k in range(len(iv) - 1)]
    T, V = float(np.median(traits)), float(np.median(vides))
    best = min(MODULATIONS, key=lambda m: abs(MODULATIONS[m][0] - T) / MODULATIONS[m][0] + abs(MODULATIONS[m][1] - V) / MODULATIONS[m][1])
    tn, vn = MODULATIONS[best]
    return {"n_traits": len(iv), "trait_median_m": T, "vide_median_m": V, "traits_m": [round(x, 3) for x in traits],
            "vides_m": [round(x, 3) for x in vides], "modulation_proche": best,
            "ecart_trait_m": T - tn, "ecart_vide_m": V - vn, "periode_m": T + V}


def mesurer_ligne_courbe(d, det, geo, pas=0.5):
    """Ligne longue ou courbe : centres par tranches de `pas` le long de l'axe principal (moyenne pondérée par p
    des pixels de la composante), puis profil perpendiculaire local (luminance, 1 cm, moyenné sur +/- 5 cm le long
    de la tangente) -> bords 50 %, centre et largeur ; polynôme de degré 3 v(u) -> rectitude (RMS) ; symétrie du
    fond (une bordure a deux fonds différents : enrobé / trottoir ou végétation)."""
    L = det["cartes"]["L"]
    rr, cc = np.nonzero(det["lab"] == d["id"])
    x, y = C.px_vers_l93(rr, cc, geo)
    w = det["p"][rr, cc]
    th = d["angle_rad"]
    eu = np.array([math.cos(th), math.sin(th)])
    ev = np.array([-math.sin(th), math.cos(th)])
    u = (x - d["cx"]) * eu[0] + (y - d["cy"]) * eu[1]
    v = (x - d["cx"]) * ev[0] + (y - d["cy"]) * ev[1]
    bins = np.arange(u.min(), u.max() + pas, pas)
    cen = []
    for a in bins[:-1]:
        s = (u >= a) & (u < a + pas)
        if s.sum() < 6:
            continue
        vs = v[s]
        if vs.max() - vs.min() > 0.6:          # plusieurs branches ou boucle dans la tranche : pas un ruban simple
            continue
        cen.append((float(np.average(u[s], weights=w[s] + 1e-6)), float(np.average(vs, weights=w[s] + 1e-6))))
    if len(cen) < 4:
        return None
    cen = np.array(cen)
    pts = []
    vv = np.arange(-0.40, 0.40 + 1e-9, 0.01)
    for k in range(len(cen)):
        k0, k1 = max(0, k - 1), min(len(cen) - 1, k + 1)
        t = cen[k1] - cen[k0]
        t = t / max(np.linalg.norm(t), 1e-9)
        tang = t[0] * eu + t[1] * ev              # tangente en L93
        nrm = np.array([-tang[1], tang[0]])
        P0 = np.array([d["cx"], d["cy"]]) + cen[k, 0] * eu + cen[k, 1] * ev
        col = np.zeros_like(vv)
        for o in (-0.05, 0.0, 0.05):
            col += C.echantillonner(L, geo, P0[0] + o * tang[0] + vv * nrm[0], P0[1] + o * tang[1] + vv * nrm[1])
        col /= 3
        im = int(np.nanargmax(np.convolve(np.nan_to_num(col), np.ones(5) / 5, mode="same")[25:-25])) + 25
        fg = np.nanmedian(col[(vv < vv[im] - 0.15) & (vv > vv[im] - 0.40)])
        fd = np.nanmedian(col[(vv > vv[im] + 0.15) & (vv < vv[im] + 0.40)])
        fond = 0.5 * (fg + fd)
        pl = np.nanmax(np.convolve(col, np.ones(3) / 3, mode="same")[max(0, im - 8):im + 9])
        if not (np.isfinite(fond) and np.isfinite(pl)) or pl - fond < 15:
            continue
        niv = 0.5 * (pl + fond)
        g = _niveau50(vv, col, niv, im, -1)
        dr = _niveau50(vv, col, niv, im, +1)
        if g is None or dr is None or not (0.04 < dr - g < 0.45):
            continue
        c = P0 + 0.5 * (g + dr) * nrm
        pts.append((c[0], c[1], dr - g, abs(fg - fd), pl - fond))
    if len(pts) < 4:
        return None
    P = np.array(pts)
    uu = (P[:, 0] - d["cx"]) * eu[0] + (P[:, 1] - d["cy"]) * eu[1]
    vv2 = (P[:, 0] - d["cx"]) * ev[0] + (P[:, 1] - d["cy"]) * ev[1]
    deg = min(3, len(P) - 2)
    coef = np.polyfit(uu, vv2, deg)
    resid = vv2 - np.polyval(coef, uu)
    # bruit local : écart de chaque centre à la droite de ses 2 voisins de part et d'autre (fenêtre 2 m)
    loc = []
    for k in range(2, len(uu) - 2):
        cf = np.polyfit(np.r_[uu[k - 2:k], uu[k + 1:k + 3]], np.r_[vv2[k - 2:k], vv2[k + 1:k + 3]], 1)
        loc.append(vv2[k] - np.polyval(cf, uu[k]))
    bruit = float(np.sqrt(np.mean(np.square(loc)))) if loc else float("nan")
    sa = np.linspace(uu.min(), uu.max(), max(2, int((uu.max() - uu.min()) / 0.25) + 1))
    sv = np.polyval(coef, sa)
    axe = np.c_[d["cx"] + sa * eu[0] + sv * ev[0], d["cy"] + sa * eu[1] + sv * ev[1]]
    longueur = float(np.sum(np.linalg.norm(np.diff(axe, axis=0), axis=1)))
    return {"composante": d["id"], "axe_l93": axe.tolist(), "longueur_m": longueur, "largeur_m": float(np.median(P[:, 2])),
            "largeur_p10_p90_m": [float(np.percentile(P[:, 2], 10)), float(np.percentile(P[:, 2], 90))],
            "rms_axe_m": float(np.sqrt(np.mean(resid ** 2))), "bruit_local_m": bruit, "degre": deg, "n_tranches": int(len(P)),
            "dissymetrie_fond_DN": float(np.median(P[:, 3])), "contraste_DN": float(np.median(P[:, 4])),
            "angle_rad": float(th), "milieu": axe[len(axe) // 2].tolist(), "debut": axe[0].tolist(), "fin": axe[-1].tolist(),
            "courbe": True}
