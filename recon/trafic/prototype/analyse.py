"""Métriques des scénarios, calculées de la même façon pour notre modèle et pour SUMO.

Les valeurs cibles viennent de parametres_modele.json (ids cités) ; aucune cible n'est saisie ici.
v0.2 : collisions primaires / secondaires et taux par rang sachant le meneur intact (S2) ; écart-type du pic
d'accélération par rang (S1) ; jerk maximal hors démarrage, hors urgence et hors capture d'attention P-08 ;
passages au rouge par classe de TTL (S1b) ; créneaux mesurés depuis l'arrêt en tête de ligne et au point de
conflit (S3).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize, stats

import sumo_scenarios as SS

PAS = 0.1


def q(x, ps=(5, 15, 25, 50, 75, 85, 95)):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0}
    d = {"n": int(x.size), "moyenne": round(float(x.mean()), 3), "ecart_type": round(float(x.std(ddof=1)) if x.size > 1 else 0.0, 3)}
    d.update({f"p{p}": round(float(np.percentile(x, p)), 3) for p in ps})
    return d


def mle_lognormale(acc, rej):
    """Créneau critique par maximum de vraisemblance (Troutbeck), loi lognormale (méthode du volet 03).
    acc : créneau accepté ; rej : plus grand créneau refusé (0 si aucun)."""
    a, r = np.asarray(acc, float), np.asarray(rej, float)
    m = np.isfinite(a) & np.isfinite(r) & (a > r + 1e-6)
    a, r = a[m], r[m]
    if a.size < 10:
        return None

    def nll(p):
        mu, ls = p
        sg = math.exp(ls)
        Fa = stats.norm.cdf((np.log(a) - mu) / sg)
        Fr = np.where(r > 0, stats.norm.cdf((np.log(np.maximum(r, 1e-9)) - mu) / sg), 0.0)
        return -np.sum(np.log(np.maximum(Fa - Fr, 1e-300)))

    res = optimize.minimize(nll, [math.log(np.median(a)), math.log(0.3)], method="Nelder-Mead",
                            options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
    mu, sg = res.x[0], math.exp(res.x[1])
    moy = math.exp(mu + sg * sg / 2)
    return {"moyenne_s": round(moy, 3), "ecart_type_s": round(moy * math.sqrt(math.exp(sg * sg) - 1), 3),
            "mu_log": round(float(mu), 4), "sigma_log": round(float(sg), 4), "n_conducteurs": int(a.size)}


# ----------------------------------------------------------------------------- S1
def s1_modele(sim, meta):
    nf, nv = meta["n_files"], meta["n_vehicules"]
    det = sim.detections_tableau()
    tc = np.full(nf * nv, np.nan)
    vc = np.full(nf * nv, np.nan)
    for i, r, d, t, v in det:
        tc[int(i)], vc[int(i)] = t, v
    tc, vc = tc.reshape(nf, nv), vc.reshape(nf, nv)
    tr = sim.traces()
    t = tr["t"]
    a, v = tr["a"], tr["v"]
    pics, t1, tpk = np.full(nf * nv, np.nan), np.full(nf * nv, np.nan), np.full(nf * nv, np.nan)
    for i in range(nf * nv):
        vv, aa = v[:, i], a[:, i]
        k0 = np.flatnonzero(np.nan_to_num(vv) > 0.01)
        if not k0.size:
            continue
        k0 = k0[0]
        fen = slice(k0, min(k0 + 150, len(t)))
        pics[i] = np.nanmax(aa[fen])
        kp = k0 + int(np.nanargmax(aa[fen]))
        tpk[i] = t[kp] - 0.05 - (t[k0] - PAS)
        k1 = np.flatnonzero(np.nan_to_num(vv[k0:]) >= 1.0)
        if k1.size:
            k1 = k0 + k1[0]
            t1[i] = t[k1 - 1] + PAS * (1 - vv[k1 - 1]) / max(vv[k1] - vv[k1 - 1], 1e-9) - (t[k0] - PAS)
    jerk, jerk_hd, jerk_nominal = jerks(sim, tr)
    r = resume_s1(tc, vc, pics.reshape(nf, nv), t1.reshape(nf, nv), tpk.reshape(nf, nv), jerk, jerk_hd,
                  len(sim.collisions))
    r["jerk_abs_nominal_ms3"] = q(jerk_nominal, (50, 95, 99, 100))
    r["collisions_secondaires"] = len(sim.collisions_secondaires)
    r["collisions_detail"] = sim.collisions + sim.collisions_secondaires
    return r


def jerks(sim, tr):
    """|jerk| sur les pas où le véhicule roule (v > 0,1 m/s aux deux pas) ; hors phase de démarrage (P-02) ;
    « nominal » : hors démarrage, hors urgence, hors capture d'attention P-08 et hors véhicules accidentés."""
    a, v, t = tr["a"], tr["v"], tr["t"]
    j = np.abs(np.diff(a, axis=0)) / PAS
    ok = (np.nan_to_num(v[1:]) > 0.1) & (np.nan_to_num(v[:-1]) > 0.1) & np.isfinite(j)
    tt = t[1:, None] - np.where(np.isfinite(sim.t_start), sim.t_start, -1e9)[None, :]
    hd = ok & (tt > sim.P.v("duree_demarrage_s") + 2 * PAS)     # marge d'alignement des traces (t + Δ)
    exclu = np.zeros_like(hd)
    for cle in ("urg", "p08", "acc"):
        if cle in tr:
            x = np.nan_to_num(tr[cle]) > 0.5
            exclu |= x[1:] | x[:-1]
    nominal = hd & ~exclu
    return j[ok], j[hd], j[nominal]


def resume_s1(tc, vc, pics, t1, tpk, jerk, jerk_hd, n_col):
    h = np.diff(np.concatenate([np.zeros((tc.shape[0], 1)), tc], axis=1), axis=1)
    hm = np.nanmean(h[:, 4:12], axis=1)
    h_sat = float(np.nanmean(hm))
    return {"tiv_rangs_5_12_par_file_s": q(hm), "tiv_rangs_5_12_moyen_s": round(h_sat, 3),
            "debit_saturation_veh_h": round(3600.0 / h_sat) if h_sat > 0 else None,
            "temps_perdu_4_premiers_s": round(float(np.nanmean(tc[:, 3]) - 4 * h_sat), 3),
            "tiv_moyen_par_rang_s": [round(float(x), 3) for x in np.nanmean(h, axis=0)],
            "passage_moyen_par_rang_s": [round(float(x), 3) for x in np.nanmean(tc, axis=0)],
            "vitesse_ligne_par_rang_ms": [round(float(x), 2) for x in np.nanmean(vc, axis=0)],
            "pic_acc_moyen_par_rang_ms2": [round(float(x), 3) for x in np.nanmean(pics, axis=0)],
            "pic_acc_ecart_type_par_rang_ms2": [round(float(x), 3) for x in np.nanstd(pics, axis=0, ddof=1)],
            "rang1_t_1ms_s": q(t1[:, 0]), "rang1_t_pic_s": q(tpk[:, 0]), "rang1_pic_ms2": q(pics[:, 0]),
            "jerk_abs_ms3": q(jerk, (50, 90, 95, 99)), "jerk_abs_hors_demarrage_ms3": q(jerk_hd, (50, 90, 95, 99)),
            "collisions": n_col}


def s1_sumo(res, nv=20):
    n = len(res)
    g = lambda key: np.array([[res[q_].get(k, {}).get(key, np.nan) for k in range(1, nv + 1)] for q_ in range(n)], float)
    tc, vc, pics, t1, tpk = g("t_passage"), g("v_passage"), g("pic"), g("t_1ms"), g("t_pic")
    jerk = np.concatenate([res[q_][k]["jerk"] for q_ in range(n) for k in res[q_]]) if n else np.array([])
    return resume_s1(tc, vc, pics, t1, tpk, jerk, np.array([]), int(sum(r.get("_collisions", 0) for r in res)) if n else None)


# ----------------------------------------------------------------------------- S1b
def s1b_modele(sim, meta, ligne_s=300.0):
    j = sim.journal["jaune"]
    ttl = np.array([x["ttl"] for x in j])
    ar = np.array([x["arret"] for x in j])
    dec = np.array([x["decel_necessaire"] for x in j])
    det = sim.detections_tableau()
    jaune = meta["t_jaune"]
    rouge = np.zeros(sim.N, bool)
    passe = np.zeros(sim.N, bool)
    for i, r, d, t, v in det:
        passe[int(i)] = t > jaune[int(i)]
        rouge[int(i)] = t > jaune[int(i)] + 3.0
    presents = np.array([x["agent"] for x in j])
    bins = np.arange(0.0, 8.01, 0.5)
    c = 0.5 * (bins[1:] + bins[:-1])
    p = [float(np.mean(ar[(ttl >= lo) & (ttl < hi)])) if ((ttl >= lo) & (ttl < hi)).any() else np.nan
         for lo, hi in zip(bins[:-1], bins[1:])]
    dec_eff = np.array([-sim.a_min[x["agent"]] for x in j if x["arret"]])
    par_classe = {}
    for lo, hi in ((0.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0), (5.0, 8.0)):
        m = (ttl >= lo) & (ttl < hi)
        if m.any():
            par_classe[f"{lo:g}-{hi:g} s"] = {"n": int(m.sum()), "part_au_rouge": round(float(np.mean(rouge[presents[m]])), 4),
                                              "part_arret": round(float(np.mean(ar[m])), 4)}
    return {"P_arret_par_TTL": {"centres_s": c.tolist(), "P": [round(x, 3) for x in p]},
            "passage_au_rouge_par_classe_TTL": par_classe,
            "part_au_rouge_TTL_0_5": round(float(np.mean(rouge[presents[ttl <= 5.0]])), 4),
            "part_au_rouge_TTL_0_4": round(float(np.mean(rouge[presents[ttl <= 4.0]])), 4),
            "P_arret_2_5_3_5_5_5": [round(float(np.mean(ar[np.abs(ttl - x) < 0.25])), 3) for x in (2.5, 3.5, 5.5)],
            "part_arrets": round(float(ar.mean()), 3), "decel_necessaire_arrets_ms2": q(dec[ar]),
            "decel_max_appliquee_arrets_ms2": q(dec_eff),
            "part_au_rouge_parmi_presents": round(float(np.mean(rouge[presents])), 4),
            "part_au_rouge_parmi_passants": round(float(rouge[presents].sum() / max(passe[presents].sum(), 1)), 4),
            "collisions": len(sim.collisions), "n": int(len(j))}


# ----------------------------------------------------------------------------- S2
def s2_modele(sim, meta):
    tr = sim.traces()
    t, a, gap = tr["t"], tr["a"], tr["gap"]
    nv = 11
    npl = meta["n_pelotons"]
    t_f = meta["t_freinage"]
    apres = t >= t_f
    seuil = sim.P.v("feux_stop_seuil_ms2")
    # instant de la collision de chaque agent comme suiveur (primaire ou secondaire)
    t_col = np.full(sim.N, np.inf)
    prim = np.zeros(sim.N, bool)
    for c in sim.collisions:
        t_col[c["agent"]], prim[c["agent"]] = c["t"], True
    for c in sim.collisions_secondaires:
        t_col[c["agent"]] = c["t"]
    rangs = {}
    for k in range(1, nv):
        idx = np.arange(k, npl * nv, nv)
        idl = idx - 1
        on_f = _onset(t, a[:, idx], apres, seuil)
        on_l = _onset(t, a[:, idl], apres, seuil)
        # meneur intact : le meneur n'a heurté personne avant le choc de ce suiveur (ou pas du tout)
        intact = ~(t_col[idl] < t_col[idx])
        if k == 1:
            intact = np.ones(idx.size, bool)          # le meneur de tête ne heurte personne
        # décélération maximale AVANT tout choc (après un choc, le véhicule accidenté freine à d_max)
        a_av = np.where(np.nan_to_num(tr["acc"][:, idx]) > 0.5, np.nan, a[:, idx]) if "acc" in tr else a[:, idx]
        rangs[k] = {"delai_feux_stop_s": q(on_f - on_l), "decel_max_avant_choc_ms2": q(-np.nanmin(a_av[apres], axis=0)),
                    "gap_min_m": q(np.nanmin(gap[apres][:, idx], axis=0)),
                    "taux_collision_brut": round(float(np.mean(np.isfinite(t_col[idx]))), 4),
                    "n_meneur_intact": int(intact.sum()),
                    "taux_collision_primaire_meneur_intact": round(float(np.mean(prim[idx][intact])), 4) if intact.any() else None,
                    "collisions_primaires": int(prim[idx].sum()),
                    "collisions_secondaires": int((np.isfinite(t_col[idx]) & ~prim[idx]).sum())}
    rep = sim.journal["reponse"]
    r1 = [r for r in rep if r["agent"] % nv == 1]
    suiv = np.arange(npl * nv) % nv != 0
    return {"rangs": rangs, "collisions_primaires": len(sim.collisions), "collisions_secondaires": len(sim.collisions_secondaires),
            "taux_collision_brut_rangs_1_10": round(float(np.mean(sim.collision_agent[suiv])), 4),
            "taux_collision_primaire_rangs_1_10": round(float(np.mean(prim[suiv])), 4),
            "reponse_rang1": {"delai_evenement_s": q([r["delai"] for r in r1]), "alphaB": q([r["alphaB"] for r in r1]),
                              "part_distraits": round(float(np.mean([r["distrait"] for r in r1])), 3) if r1 else None,
                              "looming_au_debut_s-1": q([r["looming"] for r in r1])}}


def _onset(t, a, apres, seuil=1.3):
    """Instant d'allumage des feux stop (décélération > seuil de détection, convention feux_stop_seuil_ms2)."""
    out = np.full(a.shape[1], np.nan)
    for j in range(a.shape[1]):
        k = np.flatnonzero(apres & (np.nan_to_num(a[:, j]) < -seuil))
        if k.size:
            out[j] = t[k[0]]
    return out


def s2_sumo(res):
    rangs = {}
    for k in range(1, 11):
        rr = [r["rangs"][k] for r in res if k in r["rangs"]]
        rangs[k] = {"delai_feux_stop_s": q([x["delai_feux_stop"] for x in rr]), "decel_max_ms2": q([x["decel_max"] for x in rr]),
                    "gap_min_m": q([x["gap_min"] for x in rr]),
                    "taux_collision_brut": round(float(np.mean([x["gap_min"] < 0 for x in rr])), 4) if rr else None}
    return {"rangs": rangs, "collisions": int(sum(r["collisions"] for r in res)), "n_rep": len(res),
            "pelotons_avec_collision": int(sum(r["collisions"] > 0 for r in res))}


# ----------------------------------------------------------------------------- S3
def s3_modele(sim, meta):
    det = sim.detections_tableau()
    g = meta["geo"]
    rows = []
    for qc in range(meta["n_rep"]):
        mc = sim.couloir[det[:, 0].astype(int)] == qc
        Pm = np.sort(det[mc & (det[:, 1] == 0) & (det[:, 2] == 0), 3])
        Pc = np.sort(det[mc & (det[:, 1] == 0) & (det[:, 2] == 1), 3])       # prioritaires au point de conflit
        dm = det[mc & (det[:, 1] == 1)]
        t30, t3, td, tv = {}, {}, {}, {}
        for i, r, d, t, v in dm:
            {0: t30, 1: t3, 2: td, 3: tv}.get(int(d), {})[int(i)] = t
        for i in td:
            if i not in t3:
                continue
            arret = bool(sim.stop_vmin_zone[i] < 0.1)
            c = SS.creneaux(t3[i], td[i], Pm, arret, np.nan)
            if c is None:
                continue
            # mesures v0.2 : depuis l'arrêt en tête de ligne (v < 0,1 m/s), à l'entrée puis au point de conflit
            if arret and np.isfinite(sim.stop_t_v01[i]):
                cb = SS.creneaux(float(sim.stop_t_v01[i]), td[i], Pm, arret, np.nan)
                t_conf = tv.get(i, np.nan)
                cc = SS.creneaux(float(sim.stop_t_v01[i]), t_conf, Pc, arret, np.nan) if t_conf == t_conf else None
                if cb:
                    c["accepte_B"], c["max_rejete_B"] = cb["accepte"], cb["max_rejete"]
                if cc:
                    c["accepte_C"], c["max_rejete_C"] = cc["accepte"], cc["max_rejete"]
            c["vmin_3m"] = float(sim.stop_vmin_zone[i])
            c["libre"] = bool(i in t30 and not any(j != i and t30.get(j, np.inf) < t30[i] < td.get(j, np.inf) for j in td))
            c["modalite_tiree"] = int(sim.stop_modalite_tiree[i])
            rows.append(c)
    maj = np.flatnonzero((sim.route == 0) & sim.insere)
    a_min = sim.a_min[maj]
    return resume_s3(rows, a_min, -sim.b[maj], len(sim.collisions),
                     extra={"franchissements_sans_engagement": len(sim.journal["stop_franchi_sans_engagement"]),
                            "non_inseres_secondaire": int(np.sum((sim.route == 1) & ~sim.insere)),
                            "motifs_refus": _compte([c.get("motif", "") for c in sim.journal["creneau"] if not c["accepte"]])})


def _compte(x):
    from collections import Counter
    return dict(Counter(x))


def resume_s3(rows, a_min_maj, moins_b_maj, n_col, extra=None):
    acc = [r["accepte"] for r in rows]
    rej = [r["max_rejete"] for r in rows]
    arr = [r for r in rows if r["arret_complet"]]
    libres = [r for r in rows if r.get("libre", True)]
    vmin = np.array([r.get("vmin_3m", np.nan) for r in libres])
    out = {"n_conducteurs": len(rows),
           "creneau_critique_mle_tous": mle_lognormale(acc, rej),
           "creneau_critique_mle_arretes": mle_lognormale([r["accepte"] for r in arr], [r["max_rejete"] for r in arr]),
           "creneau_critique_mle_creneaux_seuls": mle_lognormale([r["accepte"] for r in rows if r["type"] == "gap"],
                                                                 [r["max_rejete_creneaux"] for r in rows if r["type"] == "gap"]),
           "creneau_critique_mle_arretes_depuis_arret": mle_lognormale([r["accepte_B"] for r in arr if "accepte_B" in r],
                                                                       [r["max_rejete_B"] for r in arr if "accepte_B" in r]),
           "creneau_critique_mle_arretes_depuis_arret_point_conflit": mle_lognormale([r["accepte_C"] for r in arr if "accepte_C" in r],
                                                                                     [r["max_rejete_C"] for r in arr if "accepte_C" in r]),
           "creneau_accepte_arretes_s": q([r["accepte"] for r in arr]),
           "attente_s": q([r["attente"] for r in rows]),
           "part_arret_complet_tous": round(float(np.mean([r["arret_complet"] for r in rows])), 3) if rows else None,
           "a_min_prioritaires_ms2": q(a_min_maj, (1, 5, 50)),
           "part_prioritaires_freinage_sup_b": round(float(np.mean(a_min_maj < moins_b_maj)), 4) if np.size(a_min_maj) and moins_b_maj is not None else None,
           "collisions": n_col}
    if np.isfinite(vmin).any():
        out["arrivees_libres"] = {"n": int(np.isfinite(vmin).sum()),
                                  "part_arret_complet_v_inf_0_1": round(float(np.nanmean(vmin < 0.1)), 3),
                                  "part_glisse_0_1_a_3": round(float(np.nanmean((vmin >= 0.1) & (vmin < 3.0))), 3),
                                  "part_sans_arret_sup_3": round(float(np.nanmean(vmin >= 3.0)), 3),
                                  "vmin_3m_ms": q(vmin)}
    if extra:
        out.update(extra)
    return out


def s3_sumo(rows, a_min_maj=None):
    return resume_s3(rows, np.asarray(a_min_maj if a_min_maj is not None else [], float), None, None)


# ----------------------------------------------------------------------------- S4 / S5 (véhicules isolés)
def profil_libre(t, s, v, a, s_ref_points: dict, s_debut_zone: float, horizon_m: float = 400.0):
    """Mesures d'un véhicule isolé le long de s : vitesses aux points, début du freinage d'approche."""
    ok = np.isfinite(s)
    s, v, a, t = s[ok], v[ok], a[ok], t[ok]
    out = {}
    for nom, x in s_ref_points.items():
        out[nom] = float(np.interp(x, s, v)) if s.size and s[0] <= x <= s[-1] else np.nan
    m = (s > s_debut_zone - horizon_m) & (s < s_debut_zone)
    k = np.flatnonzero(m & (a < -0.3))
    out["debut_freinage_m"] = float(s_debut_zone - s[k[0]]) if k.size else np.nan
    out["decel_max_approche_ms2"] = float(-a[m].min()) if m.any() else np.nan
    if k.size:
        mm = m & (s >= s[k[0]])
        out["decel_moy_approche_ms2"] = float(-a[mm][a[mm] < 0].mean()) if (a[mm] < 0).any() else np.nan
    else:
        out["decel_moy_approche_ms2"] = np.nan
    j = np.abs(np.diff(a)) / PAS
    out["jerk_p95"] = float(np.percentile(j, 95)) if j.size else np.nan
    return out


def libres_modele(sim, points: dict, s_zone: float, zone=None):
    tr = sim.traces()
    rows = []
    for i in range(sim.N):
        r = profil_libre(tr["t"], tr["s"][:, i].astype(float), tr["v"][:, i].astype(float), tr["a"][:, i].astype(float),
                         points, s_zone)
        if zone:
            s = tr["s"][:, i]
            m = (s >= zone[0]) & (s <= zone[1])
            r["v_min_zone"] = float(np.nanmin(tr["v"][:, i][m])) if m.any() else np.nan
        rows.append(r)
    return rows


def libres_sumo(trajs: dict, points: dict, s_zone: float, zone=None):
    rows = []
    for vid, d in trajs.items():
        r = profil_libre(d["t"], d["s"], d["v"], d["a"], points, s_zone)
        if zone:
            m = (d["s"] >= zone[0]) & (d["s"] <= zone[1])
            r["v_min_zone"] = float(d["v"][m].min()) if m.any() else np.nan
        rows.append(r)
    return rows


def resume_libres(rows, cles):
    return {k: q([r.get(k, np.nan) for r in rows]) for k in cles}


def s1_diagnostic_v0(sim, meta, seuil_kmh=34.0):
    """Lien entre le TIV des rangs profonds et la vitesse désirée la plus faible devant (effet du plus lent)."""
    nf, nv = meta["n_files"], meta["n_vehicules"]
    det = sim.detections_tableau()
    tc = np.full(nf * nv, np.nan)
    for i, r, d, t, v in det:
        tc[int(i)] = t
    tc = tc.reshape(nf, nv)
    h = np.diff(np.concatenate([np.zeros((nf, 1)), tc], axis=1), axis=1)
    v0 = sim.v0.reshape(nf, nv) * 3.6
    vmin = np.minimum.accumulate(v0, axis=1)
    out = {"v0_min_devant_par_rang_kmh": [round(float(x), 1) for x in vmin.mean(axis=0)]}
    for nom, sl in (("rangs_5_12", slice(4, 12)), ("rangs_13_20", slice(12, 20))):
        x, y = vmin[:, sl].ravel(), h[:, sl].ravel()
        ok = np.isfinite(y)
        lent = x < seuil_kmh
        out[nom] = {"spearman_TIV_v0min": round(float(stats.spearmanr(x[ok], y[ok])[0]), 3),
                    "TIV_moyen_sans_conducteur_lent_s": round(float(np.nanmean(y[~lent])), 3),
                    "TIV_moyen_avec_conducteur_lent_s": round(float(np.nanmean(y[lent])), 3),
                    "part_avec_conducteur_lent": round(float(np.mean(lent)), 3), "seuil_kmh": seuil_kmh}
    return out


# ----------------------------------------------------------------------------- population (contrôles v0.2)
def controles_population(P, n=200000, graine=123):
    """Contrôles de la population tirée : ordres (TPR, a1 ≥ b, TIV min ≤ moyen), maxima des lois tronquées,
    marges des TPR construits par incrément, part de T de décharge fixée par le plancher H-17, distraction."""
    from conducteurs import T_suivi, distrait_a_l_evenement, tirer_conducteurs
    import lois
    rng = np.random.default_rng(graine)
    pop = tirer_conducteurs(P, n, rng)
    out = {"n": n}
    ant = pop["PER.tpr.anticipe"]
    out["ordres"] = {
        "P(TPR_anticipe > TPR_inattendu)": float(np.mean(ant > pop["PER.tpr.inattendu_signal"])),
        "P(TPR_anticipe > TPR_jaune)": float(np.mean(ant > pop["PER.feu.tpr_jaune"])),
        "P(TPR_anticipe > TPR_surprise)": float(np.mean(ant > pop["PER.tpr.surprise_obstacle"])),
        "P(a1 < b)": float(np.mean(pop["LON.dec.urgence_max_markkula"] < pop["LON.dec.max_courante_urbain"])),
        "P(dec_equivalente < b)": float(np.mean(pop["LON.dec.urgence_equivalente"] < pop["LON.dec.max_courante_urbain"])),
        "P(TIV_min > TIV_moyen)": float(np.mean(pop["LON.tiv.min_conducteur_urbain"] > pop["LON.tiv.moyen_conducteur_urbain"])),
        "part_relevee_par_plancher_a1": pop["_plancher:LON.dec.urgence_max_markkula"],
        "part_relevee_par_plancher_dec_equivalente": pop["_plancher:LON.dec.urgence_equivalente"],
        "part_abaissee_TIV_min_urbain": pop["_plafond:LON.tiv.min_conducteur_urbain"]}
    marges = {}
    for pid in ("PER.tpr.inattendu_signal", "PER.feu.tpr_jaune", "PER.tpr.surprise_obstacle"):
        x = pop[pid]
        ref = lois.moments(P.p(pid)["loi"], P.par(pid))
        marges[pid] = {"moyenne": round(float(x.mean()), 3), "ecart_type": round(float(x.std()), 3),
                       "moyenne_publiee": round(ref["moyenne"], 3), "ecart_type_publie": round(ref["ecart_type"], 3),
                       "p50": round(float(np.median(x)), 3), "p50_loi_publiee": round(float(P.quantile(pid, [0.5])[0]), 3),
                       "p95": round(float(np.percentile(x, 95)), 3), "p95_loi_publiee": round(float(P.quantile(pid, [0.95])[0]), 3),
                       "increment_lognormal": {k: round(v, 4) for k, v in pop[f"_increment:{pid}"].items()}}
    out["tpr_par_increment"] = marges
    out["maxima"] = {pid: round(float(pop[pid].max()), 3) for pid in
                     ("LON.dec.max_courante_urbain", "LON.dec.max_courante_autoroute", "LON.acc.max_suivi_urbain",
                      "LON.acc.max_suivi_autoroute", "LON.dec.urgence_equivalente", "LON.dec.urgence_max_markkula")}
    out["v0_artere_min_kmh"] = round(float(pop["LON.vit.artere_centre_ville_50"].min()), 2)
    out["correlations_intra_groupe_spearman"] = {
        "tpr_anticipe_vs_inattendu": round(float(stats.spearmanr(ant, pop["PER.tpr.inattendu_signal"])[0]), 3),
        "alpha_vs_alat": round(float(stats.spearmanr(pop["LAT.courbe.alpha_deux_tiers"], pop["LAT.courbe.alat_max_conducteur"])[0]), 3),
        "acc_demarrage_vs_bosetti": round(float(stats.spearmanr(pop["LON.acc.demarrage_pic"], pop["LON.acc.max_conducteur_bosetti"])[0]), 3)}
    Ts = T_suivi(P, pop, "artere_centre_ville_50")
    r = P.v("T_decharge_rapport")
    out["decharge"] = {"r": r, "part_T_decharge_fixe_par_H17": round(float(np.mean(r * Ts < ant)), 4),
                       "T_decharge_effectif_p5_p50_p95_s": [round(float(np.percentile(np.maximum(r * Ts, ant), p)), 3) for p in (5, 50, 95)]}
    rng2 = np.random.default_rng(7)
    V = pop["V"][:20000]
    d = np.array([distrait_a_l_evenement(P, float(v), rng2) for v in V])
    out["distraction"] = {"part_moyenne": round(float(d.mean()), 4), "cible": P.v("distraction_part_temps_FR"),
                          "part_vigilance_basse_V_inf_-1_28": round(float(d[V < -1.2816].mean()), 4),
                          "part_vigilance_haute_V_sup_1_28": round(float(d[V > 1.2816].mean()), 4)}
    return out
