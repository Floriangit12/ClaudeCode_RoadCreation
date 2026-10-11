"""Accord image automatique d'une mesure ou d'un candidat (correctif Q1 de la revue adverse v2), cohérence
multi-vues des axes (complément Q2), composante latérale observée et covariance photo anisotrope (Q6).

Vote d'une photo entre l'origine A et l'hypothèse X (mesure ou candidat) — la photo doit être décisive POUR
L'OBJET (LOO ≤ 0,5° et validation locale Q2) et discriminante (|az(X) − az(A)| ≥ 2σ) :
- une hypothèse est « observée » si un axe vertical soutenu, qui descend jusqu'à son pied et non ambigu, est
  à moins de 2σ de son azimut (résidu r, coherence_photos.detecter_axes) ;
- vote X si seul X est observé, vote A si seul A l'est ; si les deux le sont (deux structures), le plus fort
  contraste l'emporte s'il vaut 1,5 fois l'autre, sinon le plus petit résidu (écart > 0,5σ), sinon pas de vote.
Cohérence multi-vues : l'axe observé de chaque photo est comparé au point ajusté sur les axes des AUTRES
photos (moindres carrés, a priori faible de 5 m sur A) ; une photo à plus de 3σ est écartée pour l'objet
(cas de mly:1207034570953803 à l'accès NE : décalée de 2 à 3°).
Verdict (Q1) : « accord » si ≥ 2 photos votent X, plus que pour A, et Σ r(X)² < Σ r(A)² ; sinon la mesure
devient un INDICE : « desaccord » (votes A seulement), « contradictoire » (votes des deux côtés),
« accord_insuffisant » (une seule photo pour X), « non_concluant » (photos discriminantes sans axe net),
« non_testable » (aucune photo décisive discriminante : la mesure relève de Q6/Q7).
Hors accord, l'objet reste en A, ou seule la composante latérale OBSERVÉE (axes détectés, visées à moins
de 15° l'une de l'autre) s'applique si elle dépasse 2σ et 0,10 m ; une géométrie complète (≥ 15°) donne un
axe triangulé, gardé comme indice (hypothèse Q de la planche), jamais appliqué.

Q6 : covariance d'une mesure photo = dispersion réelle des résidus des axes (m) avec le plancher géométrique
d·σ_pose (latéral) et d·σ_pose / sin(angle d'intersection) (profondeur, infinie sous 15°).
"""
import math

import numpy as np

SEUIL_VOTE = 2.0
SEP_MIN = 2.0
LOO_MAX = 3.0
ANGLE_MIN = 15.0
SIGMA_INFINI = 100.0           # m : profondeur non observable


def _rad(x):
    return math.radians(x)


def observee(h):
    return bool(h and h.get("support") and h.get("pied_ok") and not h.get("ambigu") and h.get("residu") is not None
                and abs(h["residu"]) < SEUIL_VOTE)


def vote_photo(par_hyp, cle_a="A", cle_x="C"):
    a, x = par_hyp.get(cle_a), par_hyp.get(cle_x)
    if not a or not x:
        return dict(vote=None, discriminante=False, motif="hypothèse hors fenêtre")
    sig = (a["sigma"] + x["sigma"]) / 2.0
    sep = abs(x["az"] - a["az"]) / sig
    oa, ox = observee(a), observee(x)
    vote = None
    if sep >= SEP_MIN:
        if ox and not oa:
            vote = cle_x
        elif oa and not ox:
            vote = cle_a
        elif oa and ox:
            if x["valeur"] >= 1.5 * a["valeur"]:
                vote = cle_x
            elif a["valeur"] >= 1.5 * x["valeur"]:
                vote = cle_a
            elif abs(x["residu"]) + 0.5 < abs(a["residu"]):
                vote = cle_x
            elif abs(a["residu"]) + 0.5 < abs(x["residu"]):
                vote = cle_a
    axe = None
    if vote is not None:
        axe = (x if vote == cle_x else a)["axe_az"]
    elif ox and not oa:
        axe = x["axe_az"]
    elif oa and not ox:
        axe = a["axe_az"]
    elif oa and ox and sep < SEP_MIN:
        axe = (x if abs(x["residu"]) <= abs(a["residu"]) else a)["axe_az"]      # même structure vue des deux
    return dict(vote=vote, discriminante=bool(sep >= SEP_MIN), separation_sigma=round(sep, 2), axe_az=axe,
                axe_X=x["axe_az"] if ox else None,
                r_A=None if a.get("residu") is None else round(a["residu"], 2),
                r_X=None if x.get("residu") is None else round(x["residu"], 2),
                obs_A=oa, obs_X=ox, v_A=a.get("valeur"), v_X=x.get("valeur"), pied_A=a.get("pied"), pied_X=x.get("pied"),
                sigma_deg=round(sig, 3), d_m=round(a["d"], 1))


def _rayon(cam_c, az_deg):
    u = np.array([math.sin(_rad(az_deg)), math.cos(_rad(az_deg))])
    return np.asarray(cam_c[:2], float), u, np.array([u[1], -u[0]])


def ajuster(rayons, prior=None, sigma_prior=5.0):
    """Point le plus proche d'un faisceau de rayons [(C, u, n, s_m)] (moindres carrés pondérés par 1/s²)."""
    Mt = np.zeros((2, 2))
    b = np.zeros(2)
    for C, u, n, s in rayons:
        w = 1.0 / max(s, 1e-3) ** 2
        Mt += w * np.outer(n, n)
        b += w * np.outer(n, n) @ C
    if prior is not None:
        Mt += np.eye(2) / sigma_prior ** 2
        b += np.asarray(prior, float) / sigma_prior ** 2
    return np.linalg.solve(Mt, b), Mt


def angle_max(az_list):
    a = 0.0
    for i in range(len(az_list)):
        for j in range(i + 1, len(az_list)):
            e = abs((az_list[i] - az_list[j]) % 180.0)
            a = max(a, min(e, 180.0 - e))
    return a


def accord(A, X, photos, cle_x="C"):
    """photos : [dict(pid, cam_c (3,), decisive (bool, Q2 compris), par_hyp)] (ordre déterministe).
    Renvoie le verdict Q1, les lignes par photo, les exclusions multi-vues et la position observée."""
    A, X = np.asarray(A, float), np.asarray(X, float)
    lignes = []
    for ph in photos:
        v = vote_photo(ph["par_hyp"], "A", cle_x)
        v.update(photo=ph["pid"], decisive=bool(ph["decisive"]), motif_q2=ph.get("motif_q2"),
                 cam_c=[round(float(c), 3) for c in np.asarray(ph["cam_c"], float)[:3]])
        if not ph["decisive"]:
            v["vote"] = None
        lignes.append(v)
    # cohérence multi-vues des axes observés (photos décisives) : consensus du meilleur couple de visées
    # (≥ 15°) ; les photos hors consensus (> 3σ) sont écartées si le consensus réunit ≥ 3 photos et ≥ 60 %
    obs = [(i, l) for i, l in enumerate(lignes) if l["decisive"] and l["axe_az"] is not None]
    exclues = []
    if len(obs) >= 3:
        R = []
        for i, l in obs:
            C, u, n = _rayon(photos[i]["cam_c"], l["axe_az"])
            R.append((l["photo"], C, u, n, max(l["d_m"] * _rad(l["sigma_deg"]), 0.02), l["axe_az"]))
        best = None
        for a_ in range(len(R)):
            for b_ in range(a_ + 1, len(R)):
                e = abs((R[a_][5] - R[b_][5]) % 180.0)
                if min(e, 180.0 - e) < ANGLE_MIN:
                    continue
                P, _ = ajuster([R[a_][1:5], R[b_][1:5]])
                res = [float((P - r[1]) @ r[3]) / r[4] for r in R]
                inl = [k for k, v in enumerate(res) if abs(v) <= LOO_MAX]
                cle = (-len(inl), round(sum(res[k] ** 2 for k in inl), 6), a_, b_)
                if best is None or cle < best[0]:
                    best = (cle, res, inl)
        if best is not None and len(best[2]) >= 3 and len(best[2]) >= 0.6 * len(R):
            for k, r in enumerate(R):
                lignes[obs[k][0]]["consensus_sigma"] = round(best[1][k], 2)
                if k not in best[2]:
                    exclues.append(r[0])
        for l in lignes:
            if l["photo"] in exclues:
                l["vote"], l["exclue_multivues"] = None, True
    vX = [l for l in lignes if l["vote"] == cle_x]
    vA = [l for l in lignes if l["vote"] == "A"]
    util = [l for l in lignes if l["decisive"] and l["photo"] not in exclues and (l["obs_A"] or l["obs_X"])]
    nX = [l for l in util if l["obs_X"]]
    nA = [l for l in util if l["obs_A"]]
    SX = sum(min((l["r_X"] if l["obs_X"] else 3.0) ** 2, 9.0) for l in util)
    SA = sum(min((l["r_A"] if l["obs_A"] else 3.0) ** 2, 9.0) for l in util)
    disc = [l for l in lignes if l["decisive"] and l["discriminante"] and l["photo"] not in exclues]
    if not any(l["decisive"] for l in lignes):
        verdict = "non_testable"
    elif len(nX) >= 2 and SX < SA and len(vX) >= len(vA) and (not vA or len(vX) >= 2 * len(vA)):
        verdict = "accord"
    elif vX and vA:
        verdict = "contradictoire"
    elif vA or (len(nA) >= 2 and SA < SX):
        verdict = "desaccord"
    elif len(nX) == 1 and SX < SA:
        verdict = "accord_insuffisant"
    else:
        verdict = "non_concluant"
    out = dict(verdict=verdict, n_photos=len(lignes), n_decisives=sum(1 for l in lignes if l["decisive"]),
               n_discriminantes=len(disc), n_observee_X=len(nX), n_observee_A=len(nA),
               photos_X_observee=[l["photo"] for l in nX], votes_X=[l["photo"] for l in vX], votes_A=[l["photo"] for l in vA],
               somme_r2_X=round(SX, 2), somme_r2_A=round(SA, 2), exclues_multivues=exclues, photos=lignes)
    # axes observés (photos décisives, cohérentes) de l'hypothèse retenue par le verdict : X (accord, accord
    # insuffisant), A (désaccord) ; aucun si contradictoire ou non concluant -> composante latérale ou triangulation
    cote = {"accord": "X", "accord_insuffisant": "X", "desaccord": "A"}.get(verdict)
    rays = []
    for ph, l in zip(photos, lignes):
        if cote is None or not l["decisive"] or l["photo"] in exclues:
            continue
        h = ph["par_hyp"].get(cle_x if cote == "X" else "A") or {}
        if not observee(h):
            continue
        C, u, n = _rayon(ph["cam_c"], h["axe_az"])
        rays.append((C, u, n, max(l["d_m"] * _rad(l["sigma_deg"]), 0.02), h["axe_az"]))
    if rays:
        th = angle_max([r[4] for r in rays])
        out["angle_axes_deg"] = round(th, 1)
        if th >= ANGLE_MIN and len(rays) >= 2:
            P, Mt = ajuster([r[:4] for r in rays])
            cov = np.linalg.inv(Mt)
            out["axe_triangule"] = dict(xy=[round(float(v), 3) for v in P],
                                        sigma_m=round(float(math.sqrt(max(np.linalg.eigvalsh(cov)))), 3),
                                        d_A_m=round(float(np.hypot(*(P - A))), 3), d_X_m=round(float(np.hypot(*(P - X))), 3))
        else:
            ang = math.degrees(math.atan2(sum(math.sin(_rad(r[4])) for r in rays), sum(math.cos(_rad(r[4])) for r in rays)))
            u = np.array([math.sin(_rad(ang)), math.cos(_rad(ang))])
            ell = np.array([u[1], -u[0]])
            vals, ws = [], []
            for C, ui, ni, s, _ in rays:
                # décalage latéral de l'axe observé par rapport à A, compté le long de ell
                vals.append(-float((A - C) @ ni) * float(ni @ ell))
                ws.append(1.0 / s ** 2)
            vals, ws = np.array(vals), np.array(ws)
            L = float((vals * ws).sum() / ws.sum())
            sL = max(1.0 / math.sqrt(ws.sum()), float(np.sqrt(np.mean((vals - L) ** 2))) if len(vals) > 1 else 0.0)
            out["laterale_observee"] = dict(direction=[round(float(v), 4) for v in ell], decalage_m=round(L, 3),
                                            sigma_m=round(sL, 3), n=len(rays),
                                            significative=bool(abs(L) > 2 * sL and abs(L) >= 0.10),
                                            position=[round(float(v), 3) for v in (A + L * ell)])
    return out


def covariance_photo(M, photos_votes, sig_declare=None):
    """Q6 : covariance anisotrope de la mesure M à partir des axes des photos qui l'observent :
    [(cam_c, axe_az, d_m, sigma_deg)]. Renvoie dict(cov, sigma_lat, sigma_prof, angle, direction, rms)."""
    M = np.asarray(M, float)
    if not photos_votes:
        return None
    res, plancher, azs = [], [], []
    for cam_c, az, d, sg in photos_votes:
        C, u, n = _rayon(cam_c, az)
        res.append(float((M - C) @ n))
        plancher.append(d * _rad(sg))
        azs.append(az)
    th = angle_max(azs)
    rms = float(np.sqrt(np.mean(np.square(res))))
    base = float(np.median(plancher))
    s_lat = max(rms, base)
    s_prof = SIGMA_INFINI if th < ANGLE_MIN else max(rms, base) / math.sin(_rad(th))
    ang = math.degrees(math.atan2(sum(math.sin(_rad(a)) for a in azs), sum(math.cos(_rad(a)) for a in azs)))
    return dict(cov=cov_axes(s_prof, s_lat, ang), sigma_lat=round(s_lat, 3), sigma_prof=round(s_prof, 3),
                angle_deg=round(th, 1), direction_deg=round(ang % 360, 1), rms_m=round(rms, 3), plancher_m=round(base, 3))


def cov_axes(s_prof, s_lat, az_prof_deg):
    u = np.array([math.sin(_rad(az_prof_deg)), math.cos(_rad(az_prof_deg))])
    e = np.array([u[1], -u[0]])
    return s_prof ** 2 * np.outer(u, u) + s_lat ** 2 * np.outer(e, e)


def plancher_geometrique(M, cams, sigmas_deg):
    """Q6 : plancher d'une mesure photo à partir des photos citées : [(cam_c)], [σ_deg] -> dict ou None."""
    if not cams:
        return None
    M = np.asarray(M, float)
    d, azs, pl = [], [], []
    for c, sg in zip(cams, sigmas_deg):
        v = M - np.asarray(c[:2], float)
        dd = float(np.hypot(*v))
        d.append(dd)
        azs.append(math.degrees(math.atan2(v[0], v[1])))
        pl.append(dd * _rad(sg))
    th = angle_max(azs) if len(azs) > 1 else 0.0
    base = float(np.median(pl))
    ang = math.degrees(math.atan2(sum(math.sin(_rad(a)) for a in azs), sum(math.cos(_rad(a)) for a in azs)))
    s_prof = SIGMA_INFINI if th < ANGLE_MIN else base / math.sin(_rad(th))
    return dict(sigma_lat=round(base, 3), sigma_prof=round(s_prof, 3), angle_deg=round(th, 1), direction_deg=round(ang % 360, 1),
                n=len(cams), cov=cov_axes(s_prof, base, ang))
