"""Files de pavés (pavés jaunes Chronovélo 0,70 x 0,37, carrés blancs 0,50 de traversée cyclable, damier bus 1,00) :
dimensions par moments (rectangle équivalent sqrt(12 lambda)), regroupement en files (orientation de la file à 10°
près, pas < 1,6 m), pas régulier par moindres carrés, gabarit PAVE_CHRONOVELO / CARRE_TRAVERSEE_CYCLABLE /
DAMIER_BUS posé au centre de chaque pavé.
"""
from __future__ import annotations

import math

import numpy as np

import commun_pilote as C


def paves(det, classes):
    return [d for d in det["comps"] if d["classe"] in classes]


def files(items, pas_max=1.6):
    n = len(items)
    par = list(range(n))

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            a, b = items[i], items[j]
            if math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"]) <= pas_max:
                par[f(i)] = f(j)
    g = {}
    for i in range(n):
        g.setdefault(f(i), []).append(items[i])
    out = []
    for grp in g.values():
        if len(grp) < 3:
            continue
        P = np.array([[d["cx"], d["cy"]] for d in grp])
        c = P.mean(0)
        w, v = np.linalg.eigh(np.cov((P - c).T))
        ax = v[:, 1]
        t = (P - c) @ ax
        o = np.argsort(t)
        t = t[o]
        lat = ((P - c) @ np.array([-ax[1], ax[0]]))[o]
        dif = np.diff(t)
        p0 = float(np.median(dif))
        k = np.round((t - t[0]) / p0).astype(int)
        A = np.c_[k, np.ones_like(k)]
        sol, *_ = np.linalg.lstsq(A, t, rcond=None)
        res = t - A @ sol
        dims = np.array([[grp[i]["long_m"], grp[i]["larg_m"]] for i in o])
        angs = [grp[i]["angle_rad"] for i in o]
        out.append({"n": len(grp), "centre": c.tolist(), "axe_rad": float(math.atan2(ax[1], ax[0])), "pas_m": float(sol[0]),
                    "residu_pas_rms_m": float(np.sqrt(np.mean(res ** 2))), "ecart_lateral_rms_m": float(np.sqrt(np.mean((lat - lat.mean()) ** 2))),
                    "long_mediane_m": float(np.median(dims[:, 0])), "larg_mediane_m": float(np.median(dims[:, 1])),
                    "angle_pave_rel_file_deg": float(math.degrees(C.ecart_axial(C.angle_moyen_axial(angs), math.atan2(ax[1], ax[0])))),
                    "centres": [[grp[i]["cx"], grp[i]["cy"]] for i in o], "angles_rad": angs})
    return out


def polygones_file(fl, long_m, larg_m):
    """Rectangles normés (long_m le long de l'axe principal du pavé mesuré) posés aux centres mesurés."""
    out = []
    th = C.angle_moyen_axial(fl["angles_rad"])
    eu = np.array([math.cos(th), math.sin(th)])
    ev = np.array([-math.sin(th), math.cos(th)])
    for c in fl["centres"]:
        c = np.array(c)
        out.append([[c + su * long_m / 2 * eu + sv * larg_m / 2 * ev for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]])
    return out


def detecter_paves_jaunes(det_blanc, geo):
    """Pavés jaunes : la chrominance JPEG (sous-échantillonnée) fond les pavés d'une file en une bande continue ;
    on prend donc la bande jaune (p_jaune >= 0,3, dilatée de 0,15 m) comme zone et la LUMINANCE (contraste au
    fond, sans le filtre de saturation du blanc) pour séparer les pavés."""
    import detection as D
    c = det_blanc["cartes"]
    pj = D.probabilite_jaune(c)
    zone = C.max_filtre((pj >= 0.3).astype(np.float32) * 255, 7) > 0
    s = D.seuil_adaptatif(c["fond"])
    p = np.clip((c["TH"] - 0.5 * s) / s, 0, 1)
    m = D.nettoyer((p >= 0.5) & zone, 6)
    lab, n = C.etiqueter(m)
    out = []
    for i, (rr, cc) in enumerate(C.composantes(lab, n), start=1):
        d = D.mesurer(rr, cc, geo, c)
        d["id"] = i
        d["couleur"] = "jaune"
        d["classe"] = "pave_jaune" if (0.25 <= d["larg_m"] <= 0.55 and 0.45 <= d["long_m"] <= 0.95) else "autre_jaune"
        out.append(d)
    return out


def files_paves_jaunes(det_blanc, geo):
    """Files de pavés jaunes ajustées comme des « zébras » de petites bandes : germes = pavés isolés mesurés,
    profil le long de la file sur la carte de luminance limitée à la bande jaune, pas régulier, bords sous-pixel."""
    import detection as D
    import zebras as Z
    c = det_blanc["cartes"]
    pj = D.probabilite_jaune(c)
    zone = C.max_filtre((pj >= 0.3).astype(np.float32) * 255, 7) > 0
    s = D.seuil_adaptatif(c["fond"])
    P = np.where(zone, np.clip((c["TH"] - 0.5 * s) / s, 0, 1), 0.0).astype(np.float32)
    seeds = [d for d in detecter_paves_jaunes(det_blanc, geo) if d["classe"] == "pave_jaune"]
    out = []
    for g in Z.regrouper(seeds):
        out += Z.mesurer_passage(g, det_blanc, geo, P=P, larg_bornes=(0.25, 0.55), larg_profil=(0.2, 0.6),
                                 tranche=0.05, marge_ext=0.10)
    return out


def files_jaunes_periodiques(det_blanc, geo, long_min=1.5):
    """Files de pavés jaunes par périodicité (robuste à la fusion des pavés à 5 cm) : bande jaune (p_jaune >= 0,3)
    -> axe principal ; largeur de la bande (= longueur du pavé en travers de la file) au niveau 50 % de p_jaune ;
    profil de luminance le long de l'axe (pas 2 cm, moyenne sur +/- 0,15 m), tendance retirée (moyenne glissante
    1,2 m) ; pas = pic d'autocorrélation dans [0,4 ; 1,0] m (interpolation parabolique) ; phase et rapport plein/pas
    par ajustement d'un créneau (corrélation maximale) ; pavés = créneaux contenus dans l'étendue de la bande."""
    import detection as D
    c = det_blanc["cartes"]
    pj = D.probabilite_jaune(c)
    zone = D.nettoyer(pj >= 0.3, 40)
    lab, n = C.etiqueter(zone)
    out = []
    for i, (rr, cc) in enumerate(C.composantes(lab, n), start=1):
        d = D.mesurer(rr, cc, geo, c)
        if d["long_m"] < long_min or d["larg_m"] > 1.2:
            continue
        th = d["angle_rad"]
        eu = np.array([math.cos(th), math.sin(th)])
        ev = np.array([-math.sin(th), math.cos(th)])
        hl = d["long_m"] / 2 + 0.3
        uu = np.arange(-hl, hl, 0.02)
        vv = np.arange(-0.15, 0.151, 0.03)
        UU, VV = np.meshgrid(uu, vv)
        X = d["cx"] + UU * eu[0] + VV * ev[0]
        Y = d["cy"] + UU * eu[1] + VV * ev[1]
        prof = np.nanmean(C.echantillonner(c["L"], geo, X, Y), axis=0)
        pjp = np.nanmean(C.echantillonner(pj, geo, X, Y, defaut=0.0), axis=0)
        k = 61
        tend = np.convolve(np.pad(prof, k // 2, mode="edge"), np.ones(k) / k, mode="valid")
        osc = prof - tend
        dedans = pjp >= 0.3
        if dedans.sum() < 30:
            continue
        o = osc[dedans] - osc[dedans].mean()
        ac = np.correlate(o, o, mode="full")[len(o) - 1:]
        ac = ac / max(ac[0], 1e-9)
        lags = np.arange(len(ac)) * 0.02
        sel = np.flatnonzero((lags >= 0.4) & (lags <= 1.0))
        if not len(sel):
            continue
        j = sel[int(np.argmax(ac[sel]))]
        if 0 < j < len(ac) - 1:
            a_, b_, c_ = ac[j - 1], ac[j], ac[j + 1]
            dj = 0.5 * (a_ - c_) / (a_ - 2 * b_ + c_) if (a_ - 2 * b_ + c_) != 0 else 0.0
        else:
            dj = 0.0
        pas = (j + dj) * 0.02
        if not np.isfinite(pas) or pas < 0.3:
            continue
        ud = uu[dedans]
        best = None
        for duty in np.arange(0.40, 0.81, 0.02):
            for phi in np.arange(0, pas, 0.01):
                m = (((ud - phi) / pas) % 1.0) < duty
                if m.all() or not m.any():
                    continue
                r = np.corrcoef(m.astype(float), o)[0, 1]
                if best is None or r > best[0]:
                    best = (r, duty, phi)
        r, duty, phi = best
        u0, u1 = ud.min(), ud.max()
        kmin = int(math.floor((u0 - phi) / pas)) - 1
        centres = []
        for kk in range(kmin, kmin + int((u1 - u0) / pas) + 4):
            a = phi + kk * pas
            b = a + duty * pas
            if a >= u0 - 0.05 and b <= u1 + 0.05:
                cu = 0.5 * (a + b)
                centres.append([float(d["cx"] + cu * eu[0]), float(d["cy"] + cu * eu[1])])
        # largeur de la bande jaune (longueur des pavés en travers)
        vv2 = np.arange(-0.8, 0.801, 0.01)
        UU2, VV2 = np.meshgrid(np.linspace(-d["long_m"] / 3, d["long_m"] / 3, 15), vv2)
        cp = np.nanmean(C.echantillonner(pj, geo, d["cx"] + UU2 * eu[0] + VV2 * ev[0], d["cy"] + UU2 * eu[1] + VV2 * ev[1], defaut=0.0), axis=1)
        from zebras import _niveau50
        im = int(np.argmax(cp))
        niv = 0.5 * cp.max()
        g = _niveau50(vv2, cp, niv, im, -1)
        dd = _niveau50(vv2, cp, niv, im, +1)
        out.append({"centre": [d["cx"], d["cy"]], "axe_rad": float(th), "longueur_file_m": float(u1 - u0), "pas_m": float(pas),
                    "plein_m": float(duty * pas), "vide_m": float((1 - duty) * pas), "correlation_creneau": float(r),
                    "autocorrelation_pic": float(ac[j]), "n_paves": len(centres), "centres": centres,
                    "largeur_bande_m": float(dd - g) if (g is not None and dd is not None) else None,
                    "angles_rad": [float(th + math.pi / 2)] * len(centres)})
    return out
