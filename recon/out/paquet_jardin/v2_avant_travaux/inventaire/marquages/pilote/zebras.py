"""Passages piétons (zébras) : regroupement des bandes, mesure sous-pixel et ajustement au gabarit IISR.

1. Germes : composantes « bande_zebra » (detection.classer) ; regroupement en passages par union-find
   (orientation à 8° près, |du| < 1,5 m le long des bandes, |dv| < 2,6 m en travers, soit une bande manquante).
2. Repère du passage : u le long des bandes (theta = moyenne axiale des germes), v en travers.
   Rééchantillonnage bilinéaire de la luminance L et de la probabilité de peinture p au pas de 2 cm.
3. Profil en travers (moyenne de p sur le tiers central des bandes) -> intervalles peints ; bords sous-pixel
   au niveau 50 % entre le fond (médiane des vides voisins) et le plateau (médiane du cœur de la bande) sur la
   LUMINANCE, tranche par tranche (0,10 m) : droite des bords gauche et droit -> largeur, axe, rectitude (RMS).
   Extrémités : profil le long de u au cœur de la bande, même règle des 50 %.
4. Régularisation : pas régulier c_k = c0 + k p (moindres carrés, bandes manquantes autorisées), orientation
   commune, largeur mesurée comparée à 0,50 (IISR art. 118), lignes de début et de fin ajustées sur les
   extrémités (passage biais possible).
"""
from __future__ import annotations

import math

import numpy as np

import commun_pilote as C

DS = 0.02


def regrouper(seeds):
    n = len(seeds)
    par = list(range(n))

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            a, b = seeds[i], seeds[j]
            if abs(C.ecart_axial(a["angle_rad"], b["angle_rad"])) > math.radians(8):
                continue
            th = C.angle_moyen_axial([a["angle_rad"], b["angle_rad"]])
            dx, dy = b["cx"] - a["cx"], b["cy"] - a["cy"]
            du = dx * math.cos(th) + dy * math.sin(th)
            dv = -dx * math.sin(th) + dy * math.cos(th)
            if abs(du) < 1.5 and abs(dv) < 2.6:
                par[f(i)] = f(j)
    groupes = {}
    for i in range(n):
        groupes.setdefault(f(i), []).append(seeds[i])
    return [g for g in groupes.values() if len(g) >= 2]


def _niveau50(x, y, niveau, depuis, sens):
    """Première abscisse (interpolée) où y franchit `niveau` en partant de l'indice `depuis` dans le sens `sens`."""
    i = depuis
    n = len(y)
    while 0 <= i + sens < n:
        a, b = y[i], y[i + sens]
        if (a - niveau) * (b - niveau) <= 0 and a != b:
            t = (a - niveau) / (a - b)
            return x[i] + t * (x[i + sens] - x[i])
        i += sens
    return None


def mesurer_passage(groupe, det, geo, P=None, larg_bornes=(0.38, 0.66), larg_profil=(0.25, 0.9), tranche=0.10, marge_ext=0.25):
    """P : carte de probabilité à utiliser (défaut : peinture blanche) ; larg_bornes : largeurs de bande admises
    (zébra 0,38-0,66 ; pavés jaunes 0,25-0,55)."""
    c = det["cartes"]
    L = c["L"]
    P = det["p"] if P is None else P
    th = C.angle_moyen_axial([d["angle_rad"] for d in groupe], [d["aire_m2"] for d in groupe])
    eu = np.array([math.cos(th), math.sin(th)])
    ev = np.array([-math.sin(th), math.cos(th)])
    cx = np.mean([d["cx"] for d in groupe])
    cy = np.mean([d["cy"] for d in groupe])
    us = [(d["cx"] - cx) * eu[0] + (d["cy"] - cy) * eu[1] for d in groupe]
    vs = [(d["cx"] - cx) * ev[0] + (d["cy"] - cy) * ev[1] for d in groupe]
    Lm = float(np.median([d["long_m"] for d in groupe]))
    u0, u1 = min(us) - Lm / 2 - 1.0, max(us) + Lm / 2 + 1.0
    v0, v1 = min(vs) - 1.6, max(vs) + 1.6
    uu = np.arange(u0, u1, DS)
    vv = np.arange(v0, v1, DS)
    UU, VV = np.meshgrid(uu, vv)                      # lignes = v, colonnes = u
    X = cx + UU * eu[0] + VV * ev[0]
    Y = cy + UU * eu[1] + VV * ev[1]
    Lr = C.echantillonner(L, geo, X, Y)
    Pr = C.echantillonner(P, geo, X, Y, defaut=0.0)
    # profil en travers sur le tiers central (en u) des germes
    uc = float(np.median(us))
    cen = np.abs(uu - uc) <= max(0.3, Lm / 3)
    prof = np.nanmean(Pr[:, cen], axis=1)
    # intervalles peints
    on = prof >= 0.5
    d_ = np.diff(np.r_[0, on.astype(np.int8), 0])
    st, en = np.flatnonzero(d_ == 1), np.flatnonzero(d_ == -1)
    bandes = []
    for a, b in zip(st, en):
        larg = (b - a) * DS
        if larg < larg_profil[0] or larg > larg_profil[1]:
            continue
        bandes.append((a, b))
    res = []
    for k, (a, b) in enumerate(bandes):
        vcen = vv[(a + b - 1) // 2]
        # niveaux : plateau = médiane L au coeur ; fond = médiane L dans 0,15-0,35 m de part et d'autre
        coeur = (vv >= vv[a] + 0.1) & (vv <= vv[b - 1] - 0.1)
        if coeur.sum() < 2:
            coeur = (vv >= vv[a]) & (vv <= vv[b - 1])
        gauche = (vv < vv[a] - 0.12) & (vv > vv[a] - 0.35)
        droite = (vv > vv[b - 1] + 0.12) & (vv < vv[b - 1] + 0.35)
        # extrémités le long de u (profil au coeur de la bande)
        pu = np.nanmean(Pr[coeur, :], axis=0)
        ic = int(np.argmin(np.abs(uu - uc)))
        if pu[ic] < 0.5:
            cand = np.flatnonzero(pu >= 0.5)
            if not len(cand):
                continue
            ic = int(cand[np.argmin(np.abs(cand - ic))])
        # lissage léger (0,10 m) pour franchir les manques d'usure courts
        ker = np.ones(5) / 5
        pus = np.convolve(pu, ker, mode="same")
        ua = _niveau50(uu, pus, 0.5, ic, -1)
        ub = _niveau50(uu, pus, 0.5, ic, +1)
        if ua is None or ub is None:
            continue
        # affinage des extrémités sur la luminance
        Lu = np.nanmean(Lr[coeur, :], axis=0)
        plateau_u = np.nanmedian(Lu[(uu > ua + 0.2) & (uu < ub - 0.2)]) if (ub - ua) > 0.6 else np.nanmax(Lu)
        fond_u = np.nanmedian(np.r_[Lu[(uu < ua - 0.15) & (uu > ua - 0.5)], Lu[(uu > ub + 0.15) & (uu < ub + 0.5)]])
        n50 = 0.5 * (plateau_u + fond_u)
        ia = int(np.argmin(np.abs(uu - (ua + 0.15))))
        ib = int(np.argmin(np.abs(uu - (ub - 0.15))))
        ua2 = _niveau50(uu, Lu, n50, ia, -1)
        ub2 = _niveau50(uu, Lu, n50, ib, +1)
        if ua2 is not None and abs(ua2 - ua) < 0.15:
            ua = ua2
        if ub2 is not None and abs(ub2 - ub) < 0.15:
            ub = ub2
        # bords gauche/droit tranche par tranche (0,10 m) sur la luminance, hors 0,25 m des extrémités
        tr = np.arange(ua + marge_ext, ub - marge_ext, tranche)
        bg, bd, ut = [], [], []
        for t0 in tr:
            sel = (uu >= t0) & (uu < t0 + tranche)
            if not sel.any():
                continue
            col = np.nanmean(Lr[:, sel], axis=1)
            pl = np.nanmedian(col[coeur])
            fo = np.nanmedian(np.r_[col[gauche], col[droite]]) if (gauche.any() or droite.any()) else np.nanmin(col)
            if not np.isfinite(pl) or not np.isfinite(fo) or pl - fo < 12:
                continue
            niv = 0.5 * (pl + fo)
            imid = int(np.argmin(np.abs(vv - vcen)))
            g = _niveau50(vv, col, niv, imid, -1)
            d = _niveau50(vv, col, niv, imid, +1)
            if g is None or d is None or not (larg_profil[0] * 0.8 < d - g < larg_profil[1]):
                continue
            bg.append(g)
            bd.append(d)
            ut.append(t0 + tranche / 2)
        if len(ut) < 4:
            continue
        ut, bg, bd = np.array(ut), np.array(bg), np.array(bd)
        Ag = np.c_[ut, np.ones_like(ut)]
        pg, *_ = np.linalg.lstsq(Ag, bg, rcond=None)
        pd, *_ = np.linalg.lstsq(Ag, bd, rcond=None)
        rg = bg - Ag @ pg
        rd = bd - Ag @ pd
        um = 0.5 * (ua + ub)
        vg, vd = pg[0] * um + pg[1], pd[0] * um + pd[1]
        res.append({"k": k, "u_debut": float(ua), "u_fin": float(ub), "longueur_m": float(ub - ua),
                    "v_gauche": float(vg), "v_droite": float(vd), "largeur_m": float(vd - vg),
                    "v_centre": float(0.5 * (vg + vd)), "u_centre": float(um),
                    "pente_bords": [float(pg[0]), float(pd[0])],
                    "angle_bande_rel_deg": float(math.degrees(math.atan(0.5 * (pg[0] + pd[0])))),
                    "rms_bords_m": float(np.sqrt(np.mean(np.r_[rg, rd] ** 2))),
                    "n_tranches": int(len(ut)),
                    "contraste_DN": float(np.nanmedian(Lr[coeur][:, (uu > ua) & (uu < ub)]) - np.nanmedian(np.r_[Lr[gauche].ravel(), Lr[droite].ravel()]))})
    # rejet des intervalles qui ne sont pas des bandes : largeur hors [0,38 ; 0,66] ou longueur < 60 % de la
    # médiane du groupe (carrés de traversée cyclable, tirets, bordures qui tombent dans le profil)
    ok = [b for b in res if larg_bornes[0] <= b["largeur_m"] <= larg_bornes[1]]
    if ok:
        lmed = float(np.median([b["longueur_m"] for b in ok]))
        res = [b for b in ok if b["longueur_m"] >= 0.6 * lmed]
    if len(res) < 2:
        return []
    # tri en travers, puis découpe en tronçons (un vide > 1,6 pas ou des longueurs incompatibles : autre passage
    # ou coupure au droit d'un refuge) ; chaque tronçon est ajusté séparément
    res.sort(key=lambda b: b["v_centre"])
    vcs = np.array([b["v_centre"] for b in res])
    dif = np.diff(vcs)
    p0 = float(np.median(dif[(dif > 0.7) & (dif < 1.6)])) if ((dif > 0.7) & (dif < 1.6)).any() else 1.0
    troncons, cur = [], [res[0]]
    for b_prev, b in zip(res[:-1], res[1:]):
        recouv = min(b_prev["u_fin"], b["u_fin"]) - max(b_prev["u_debut"], b["u_debut"])
        if b["v_centre"] - b_prev["v_centre"] > 1.6 * p0 or recouv < 0.5 * min(b_prev["longueur_m"], b["longueur_m"]):
            troncons.append(cur)
            cur = [b]
        else:
            cur.append(b)
    troncons.append(cur)
    sorties = []
    for tr in troncons:
        if len(tr) < 2:
            continue
        o = _ajuster(tr, th, eu, ev, cx, cy)
        if o is not None:
            sorties.append(o)
    return sorties


def _ajuster(res, th, eu, ev, cx, cy):
    vcs = np.array([b["v_centre"] for b in res])
    dif = np.diff(vcs)
    p0 = float(np.median(dif[dif < 1.6])) if (dif < 1.6).any() else float(np.median(dif))
    kk = np.round((vcs - vcs[0]) / p0).astype(int)
    A = np.c_[kk, np.ones_like(kk)]
    sol, *_ = np.linalg.lstsq(A, vcs, rcond=None)
    pas, c0 = float(sol[0]), float(sol[1])
    resid = vcs - A @ sol
    for b, r_, k_ in zip(res, resid, kk):
        b["indice"] = int(k_)
        b["residu_pas_m"] = float(r_)
    # lignes de début / fin (u en fonction de v)
    va = np.array([b["v_centre"] for b in res])
    ua_ = np.array([b["u_debut"] for b in res])
    ub_ = np.array([b["u_fin"] for b in res])
    Av = np.c_[va, np.ones_like(va)]
    la, *_ = np.linalg.lstsq(Av, ua_, rcond=None)
    lb, *_ = np.linalg.lstsq(Av, ub_, rcond=None)
    larg = np.array([b["largeur_m"] for b in res])
    longs = np.array([b["longueur_m"] for b in res])
    rel = np.array([b["angle_bande_rel_deg"] for b in res])
    th_c = th + math.radians(float(np.median(rel)))          # orientation corrigée par les bords mesurés
    out = {"theta_rad": float(th_c), "azimut_bandes_deg": float((90 - math.degrees(th_c)) % 180),
           "centre_ref": [float(cx), float(cy)], "eu": eu.tolist(), "ev": ev.tolist(), "theta_germes_rad": float(th),
           "n_bandes": len(res), "indices": [b["indice"] for b in res], "pas_m": pas, "c0_m": c0,
           "largeur_mediane_m": float(np.median(larg)), "largeur_p10_p90_m": [float(np.percentile(larg, 10)), float(np.percentile(larg, 90))],
           "intervalle_m": pas - float(np.median(larg)),
           "longueur_mediane_m": float(np.median(longs)), "longueur_min_max_m": [float(longs.min()), float(longs.max())],
           "rms_bords_median_m": float(np.median([b["rms_bords_m"] for b in res])),
           "residu_pas_rms_m": float(np.sqrt(np.mean(resid ** 2))),
           "ligne_debut": [float(la[0]), float(la[1])], "ligne_fin": [float(lb[0]), float(lb[1])],
           "residu_extremites_rms_m": float(np.sqrt(np.mean(np.r_[ua_ - Av @ la, ub_ - Av @ lb] ** 2))),
           "bandes": res}
    return out


def polygones_passage(p, regularise=True, largeur=None):
    """Rectangles L93 des bandes ; régularisé : orientation commune, centres sur la grille du pas, largeur commune
    (mesurée ou imposée), extrémités sur les lignes de début et de fin."""
    th0 = p["theta_germes_rad"]
    eu = np.array(p["eu"])
    ev = np.array(p["ev"])
    cx, cy = p["centre_ref"]
    out = []
    for b in p["bandes"]:
        if regularise:
            vc = p["c0_m"] + p["pas_m"] * b["indice"]
            w = largeur if largeur is not None else p["largeur_mediane_m"]
            ua = p["ligne_debut"][0] * vc + p["ligne_debut"][1]
            ub = p["ligne_fin"][0] * vc + p["ligne_fin"][1]
            dth = p["theta_rad"] - th0
        else:
            vc, w, ua, ub = b["v_centre"], b["largeur_m"], b["u_debut"], b["u_fin"]
            dth = math.radians(b["angle_bande_rel_deg"])
        # rectangle dans (u, v) tourné de dth autour de son centre
        um = 0.5 * (ua + ub)
        hl, hw = 0.5 * (ub - ua), 0.5 * w
        cs, sn = math.cos(dth), math.sin(dth)
        pts = []
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            du, dv = su * hl, sv * hw
            u = um + du * cs - dv * sn
            v = vc + du * sn + dv * cs
            pts.append([cx + u * eu[0] + v * ev[0], cy + u * eu[1] + v * ev[1]])
        out.append({"indice": b["indice"], "anneau": pts, "centre": [cx + um * eu[0] + vc * ev[0], cy + um * eu[1] + vc * ev[1]]})
    return out
