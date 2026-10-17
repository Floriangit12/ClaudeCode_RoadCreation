"""Calculs de cohérence de la conception du modèle « conducteur + véhicule » (volet 04).

Ces calculs ne valident pas le modèle complet (il n'existe pas encore) : ils testent, avec les lois
sourcées des volets 01 (véhicules) et 02 (conducteurs), les CHOIX de conception décrits dans
D:/DocRoute/17_Modele_Vehicules_Conducteurs/04_Conception/MODELE_CONDUCTEUR_VEHICULE.md.

  C1  décharge d'une file au feu (IIDM) : quel temps intervéhiculaire désiré T reproduit le débit de
      saturation français (1 800 uvpd/h, soit 2,0 s ; Certu Feux 2010 p. 34) ? Comparaison avec le TIV
      moyen en suivi stable (Huang 2018, tab. V) et les TIV par rang (Salles 2020, fig. 10).
  C2  équilibre en suivi : IDM contre IIDM quand la vitesse désirée urbaine (ONISR) est proche de la
      vitesse de suivi.
  C3  vitesse en courbe : loi des deux tiers et accélération latérale par conducteur (Bosetti 2014)
      contre la V85 Sétra (Cerema 2018 p. 8) et les vitesses conventionnelles (VSA 90/110 p. 68).
  C4  couplage conducteur / véhicule : part des conducteurs dont l'accélération voulue dépasse la
      capacité du véhicule tiré (volet 01).
  C5  adhérence : part des conducteurs dont l'accélération latérale maximale dépasse 0,5 µg (domaine de
      la bicyclette cinématique, Polack 2018) et dont le freinage d'urgence dépasse µg sur mouillé.
  C6  feu jaune : décélérations demandées aux conducteurs qui s'arrêtent, et franchissements après la
      fin du jaune, avec la loi logistique de seuil (FHWA 2008) et un jaune français de 3 s.

Entrées : conducteurs_parametres.json (volet 02), vehicules_parametres.json (volet 01).
Sortie : D:/DocRoute/17_Modele_Vehicules_Conducteurs/04_Conception/verification/coherence.json

  python recon/trafic/conception/verifier_coherence.py [--n 20000] [--files 300]

Dépendances : numpy, scipy (déjà requises par le volet 02).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "conducteurs"))
sys.path.insert(0, str(ICI.parent / "vehicules"))
import modele_conducteurs as mc  # noqa: E402
from population import tirer_vp  # noqa: E402

DEPOT = ICI.parents[2]
F_VEH = DEPOT / "assets" / "specs" / "trafic" / "vehicules_parametres.json"
DOC17 = Path("D:/DocRoute/17_Modele_Vehicules_Conducteurs")
SORTIE = DOC17 / "04_Conception" / "verification" / "coherence.json"

G = 9.81
# Constantes reprises telles quelles des sources (aucune n'est inventée ici)
SAT_FR_S = 2.0              # 1 800 uvpd/h/voie -> 2,0 s (Certu Feux 2010 p. 34)
SALLES_RANG = {"2": 2.3, "3": 2.1, "4_et_plus": [1.8, 2.1], "1": 3.25}   # Salles 2020 fig. 10
EIDM_DEMARRAGE = {"taccmax": 1.2, "Mflatness": 2.0, "Mbegin": 0.7}       # défauts SUMO 1.27.1 (volet 03)
IDM_DELTA = 4.0             # Treiber 2000, tab. I (volet 03)
ARRET_LIGNE_M = 1.0         # distance du premier véhicule à la ligne : défaut SUMO jmStoplineGap (convention)
V_REF_SUIVI = 12.0          # m/s : vitesse de référence pour T = TIV - s0/v (Huang : suivi à v > 10 m/s ; convention)


def q(x, p):
    return float(np.quantile(np.asarray(x, dtype=float), p))


def resume(x, ps=(0.05, 0.15, 0.5, 0.85, 0.95)):
    x = np.asarray(x, dtype=float)
    return {"moyenne": round(float(x.mean()), 3), "ecart_type": round(float(x.std()), 3),
            **{f"p{int(round(p * 100))}": round(q(x, p), 3) for p in ps}}


# ----------------------------------------------------------------------------- IIDM
def acc_iidm(v, s, dv, v0, T, s0, a, b, delta=IDM_DELTA):
    """Accélération IIDM (Treiber & Kesting), forme du code SUMO MSCFModel_EIDM.cpp l. 1060-1075.
    v, s (écart net), dv = v - v_meneur ; tableaux numpy de même forme."""
    sstar = s0 + np.maximum(0.0, v * T + v * dv / (2.0 * np.sqrt(a * b)))
    z = sstar / np.maximum(s, 1e-3)
    vr = np.where(v0 > 0, v / v0, 0.0)
    a_free_inf = a * (1.0 - np.power(np.minimum(vr, 10.0), delta))
    # v <= v0
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        cas_z_ge = a * (1.0 - z * z)
        expo = np.where(a_free_inf > 1e-9, 2.0 * a / np.maximum(a_free_inf, 1e-9), 1.0)
        cas_z_lt = a_free_inf * (1.0 - np.power(np.minimum(z, 1.0), expo))
        acc_inf = np.where(z >= 1.0, cas_z_ge, cas_z_lt)
        # v > v0
        a_free_sup = -b * (1.0 - np.power(np.where(v > 0, v0 / np.maximum(v, 1e-6), 1.0), a * delta / b))
        acc_sup = np.where(z >= 1.0, a_free_sup + a * (1.0 - z * z), a_free_sup)
    return np.where(v <= v0, acc_inf, acc_sup)


def acc_idm(v, s, dv, v0, T, s0, a, b, delta=IDM_DELTA):
    sstar = s0 + np.maximum(0.0, v * T + v * dv / (2.0 * np.sqrt(a * b)))
    return a * (1.0 - np.power(v / v0, delta) - (sstar / np.maximum(s, 1e-3)) ** 2)


def simuler_decharge(T, a, b, s0, v0, L, d_dep, demarrage_eidm=True, dt=0.05, tmax=120.0, reaction="meneur"):
    """File arrêtée au rouge, vert à t = 0. Tableaux (Q files, n véhicules). Le véhicule i ne peut
    démarrer qu'après d_dep[i] secondes :
      reaction = "meneur" : depuis le vert pour le premier, depuis le démarrage de son meneur
                            (v > 0,1 m/s) pour les suivants (réaction en chaîne) ;
      reaction = "vert"   : tous depuis le vert (chacun voit le feu ; l'IIDM retient le suiveur tant
                            que l'écart ne s'ouvre pas) — borne « anticipation complète ».
    Intégration balistique. Renvoie les instants de passage de l'avant de chaque véhicule sur la
    ligne (x = 0)."""
    Q, n = T.shape
    x = np.zeros((Q, n))
    x[:, 0] = -ARRET_LIGNE_M
    for i in range(1, n):
        x[:, i] = x[:, i - 1] - L[:, i - 1] - s0[:, i]
    v = np.zeros((Q, n))
    t_dep = np.full((Q, n), np.inf)
    t_dep[:, 0] = d_dep[:, 0]
    if reaction == "vert":
        t_dep[:, :] = d_dep
    passage = np.full((Q, n), np.nan)
    t = 0.0
    p = EIDM_DEMARRAGE
    while t < tmax and np.isnan(passage).any():
        s = np.empty((Q, n))
        dv = np.empty((Q, n))
        s[:, 0] = 1e6
        dv[:, 0] = 0.0
        s[:, 1:] = x[:, :-1] - L[:, :-1] - x[:, 1:]
        dv[:, 1:] = v[:, 1:] - v[:, :-1]
        acc = acc_iidm(v, s, dv, v0, T, s0, a, b)
        autorise = t >= t_dep
        if demarrage_eidm:
            f = (np.tanh(((t - np.where(np.isfinite(t_dep), t_dep, t)) * 2.0 / p["taccmax"] - p["Mbegin"]) * p["Mflatness"]) + 1.0) / 2.0
            acc = np.where(acc > 0, acc * f, acc)
        acc = np.where(autorise | (v > 0.0), acc, np.minimum(acc, 0.0))
        acc = np.maximum(acc, -9.0)
        vn = np.maximum(v + acc * dt, 0.0)
        xn = x + 0.5 * (v + vn) * dt
        traverse = np.isnan(passage) & (x < 0.0) & (xn >= 0.0)
        frac = np.where(traverse, -x / np.maximum(xn - x, 1e-9), 0.0)
        passage = np.where(traverse, t + frac * dt, passage)
        # démarrage des suivants : leur meneur vient de dépasser 0,1 m/s
        part = (vn[:, :-1] > 0.1) & ~np.isfinite(t_dep[:, 1:])
        t_dep[:, 1:] = np.where(part, t + dt + d_dep[:, 1:], t_dep[:, 1:])
        x, v = xn, vn
        t += dt
    return passage


def c1_decharge(P, ix, L_med, n_files, rng):
    """Décharge au feu. Renvoie le T* homogène (conducteur médian) et le contrôle hétérogène."""
    med = {k: float(np.asarray(mc.valeur(ix[k], np.array([0.5]))).ravel()[0]) for k in
           ["acc.demarrage_pic", "dec.max_courante_urbain", "tiv.ecart_arret", "vit.artere_centre_ville_50",
            "tiv.moyen_conducteur_urbain", "tpr.anticipe"]}
    n = 15
    rangs = slice(3, 11)  # TIV des rangs 5 à 12 (écarts entre passages 4->5 ... 11->12)

    def homogene(T, delai, eidm):
        sh = (1, n)
        pas = simuler_decharge(np.full(sh, T), np.full(sh, med["acc.demarrage_pic"]),
                               np.full(sh, med["dec.max_courante_urbain"]), np.full(sh, med["tiv.ecart_arret"]),
                               np.full(sh, med["vit.artere_centre_ville_50"] / 3.6), np.full(sh, L_med),
                               np.full(sh, delai), demarrage_eidm=eidm)[0]
        h = np.diff(pas)
        return pas, h

    def t_etoile(delai, eidm):
        lo, hi = 0.2, 2.5
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            _, h = homogene(mid, delai, eidm)
            if np.nanmean(h[rangs]) > SAT_FR_S:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    res = {"conducteur_median": {k: round(v, 3) for k, v in med.items()}, "longueur_vehicule_m": L_med,
           "T_suivi_median_s": round(med["tiv.moyen_conducteur_urbain"] - med["tiv.ecart_arret"] / V_REF_SUIVI, 3)}
    # balayage de T pour la variante complète
    balayage = []
    for T in [0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]:
        pas, h = homogene(T, med["tpr.anticipe"], True)
        hm = float(np.nanmean(h[rangs]))
        balayage.append({"T_s": T, "TIV_rangs_5_12_s": round(hm, 3), "debit_veh_h": round(3600 / hm),
                         "TIV_rang2_3_4_s": [round(float(z), 2) for z in h[:3]], "premier_passage_s": round(float(pas[0]), 2)})
    res["balayage_T_variante_complete"] = balayage
    variantes = {}
    for nom, delai, eidm in [("IIDM_seul", 0.0, False), ("IIDM_demarrage_EIDM", 0.0, True),
                             ("IIDM_demarrage_EIDM_reaction_TPR_anticipe", med["tpr.anticipe"], True)]:
        Ts = t_etoile(delai, eidm)
        pas, h = homogene(Ts, delai, eidm)
        variantes[nom] = {"T_etoile_s": round(Ts, 3), "rapport_T_etoile_sur_T_suivi": round(Ts / res["T_suivi_median_s"], 3),
                          "TIV_rang2_3_4_s": [round(float(z), 2) for z in h[:3]],
                          "TIV_rangs_5_12_s": round(float(np.nanmean(h[rangs])), 3),
                          "premier_passage_s": round(float(pas[0]), 2)}
    res["variantes_homogenes"] = variantes
    # T pris égal au TIV de suivi (ce que ferait une correspondance naïve)
    pas, h = homogene(res["T_suivi_median_s"], med["tpr.anticipe"], True)
    res["T_egal_T_suivi"] = {"T_s": res["T_suivi_median_s"], "TIV_rangs_5_12_s": round(float(np.nanmean(h[rangs])), 3),
                             "debit_veh_h": round(3600 / float(np.nanmean(h[rangs])))}
    # contrôle hétérogène : T_i = r x T_suivi,i, conducteurs tirés par la copule du volet 02
    r_med = variantes["IIDM_demarrage_EIDM_reaction_TPR_anticipe"]["rapport_T_etoile_sur_T_suivi"]
    N = n_files * n
    vals, _ = mc.tirer_population(P, N, rng)
    shp = (n_files, n)
    s0 = vals["tiv.ecart_arret"].reshape(shp)
    T_suivi = (vals["tiv.moyen_conducteur_urbain"].reshape(shp) - s0 / V_REF_SUIVI)
    a = vals["acc.demarrage_pic"].reshape(shp)
    b = vals["dec.max_courante_urbain"].reshape(shp)
    v0 = vals["vit.artere_centre_ville_50"].reshape(shp) / 3.6
    v0 = np.maximum(v0, 3.0)
    d = vals["tpr.anticipe"].reshape(shp)
    Lm = np.full(shp, L_med)

    def population(r, reaction):
        pas = simuler_decharge(r * T_suivi, a, b, s0, v0, Lm, d, demarrage_eidm=True, reaction=reaction)
        h = np.diff(pas, axis=1)
        return pas, h, np.nanmean(h[:, rangs], axis=1)

    def bilan(r, reaction, regle):
        pas, h, hm = population(r, reaction)
        return {"regle": regle, "r": round(r, 3), "reaction_au_demarrage": reaction,
                "TIV_moyen_rangs_5_12_par_file_s": resume(hm),
                "debit_saturation_veh_h": round(3600.0 / float(np.nanmean(hm))),
                "TIV_moyen_par_rang_s": {str(k + 2): round(float(np.nanmean(h[:, k])), 3) for k in range(6)},
                "premier_passage_s": resume(pas[:, 0])}

    def r_pop(reaction):
        lo, hi = 0.2, 1.2
        for _ in range(18):
            mid = 0.5 * (lo + hi)
            if float(np.nanmean(population(mid, reaction)[2])) > SAT_FR_S:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    res["population_heterogene"] = {
        "n_files": n_files, "vehicules_par_file": n,
        "references": {"Certu_Feux_2010_p34_s": SAT_FR_S, "HCM_plage_veh_h": [1500, 2000],
                       "Salles_2020_fig10_s": SALLES_RANG},
        "r_du_conducteur_median": bilan(r_med, "meneur", "T_i = r x T_suivi,i avec r calé sur le conducteur médian"),
        "r_cale_population_reaction_meneur": bilan(r_pop("meneur"), "meneur",
                                                   "r calé pour que la population donne 2,0 s (rangs 5-12)"),
        "r_cale_population_reaction_vert": bilan(r_pop("vert"), "vert",
                                                 "idem, chaque conducteur réagissant au vert (anticipation complète)"),
        "r_1_T_suivi_reaction_meneur": bilan(1.0, "meneur", "T_i = T_suivi,i (correspondance naïve TIV de suivi -> T)")}
    return res


# ----------------------------------------------------------------------------- C2
def c2_equilibre(T_suivi, s0, v0_list_kmh):
    out = []
    for v0k in v0_list_kmh:
        v0 = v0k / 3.6
        for v in [6.0, 8.0, 10.0, 11.0, 12.0]:
            if v >= v0:
                continue
            sst = s0 + v * T_suivi
            s_idm = sst / math.sqrt(1.0 - (v / v0) ** IDM_DELTA)
            out.append({"v0_kmh": v0k, "v_ms": v, "TIV_net_IDM_s": round(s_idm / v, 2),
                        "TIV_net_IIDM_s": round(sst / v, 2)})
    return {"T_s": round(T_suivi, 3), "s0_m": s0, "delta": IDM_DELTA, "points": out}


# ----------------------------------------------------------------------------- C3
def v85_setra(R, vlim):
    return vlim / (1.0 + 346.0 / R ** 1.5)


def c3_courbes(vals, P_ix):
    alpha = vals["courbe.alpha_deux_tiers"]
    alat = vals["courbe.alat_max_conducteur"]
    v0_80 = vals["vit.route_2_3_voies_80"] / 3.6
    cfts = P_ix["courbe.vitesse_conventionnelle_cfts"]["parametres"]
    cfts_map = dict(zip(cfts["R_m"], cfts["V_kmh"]))
    lignes = []
    for R in [10, 15, 20, 30, 40, 57, 80, 100, 134, 200, 300, 500]:
        vb = np.minimum(alpha * R ** (1.0 / 3.0), np.sqrt(alat * R))
        v_rural = np.minimum(v0_80, vb)
        lignes.append({
            "R_m": R,
            "bosetti_frontiere_kmh": {"p50": round(q(vb, 0.5) * 3.6, 1), "p85": round(q(vb, 0.85) * 3.6, 1)},
            "regle_bosetti_reseau_80_kmh": {"p50": round(q(v_rural, 0.5) * 3.6, 1), "p85": round(q(v_rural, 0.85) * 3.6, 1)},
            "setra_V85_kmh": {"Vlim_92": round(v85_setra(R, 92), 1), "Vlim_102": round(v85_setra(R, 102), 1),
                              "Vlim_120": round(v85_setra(R, 120), 1)},
            "cfts_vitesse_conventionnelle_kmh": cfts_map.get(R),
            "SUMO_sqrt_5_5R_kmh": round(math.sqrt(5.5 * R) * 3.6, 1),
            "CARLA_sqrt_0_6gR_kmh": round(math.sqrt(0.6 * G * R) * 3.6, 1)})
    # rayon où la frontière P85 de Bosetti passe sous la V85 Sétra (Vlim 102) de plus de 5 km/h
    rb = None
    for R in np.arange(10, 400, 1.0):
        vb = np.minimum(alpha * R ** (1.0 / 3.0), np.sqrt(alat * R))
        if v85_setra(R, 102) - q(vb, 0.85) * 3.6 > 5.0:
            rb = float(R)
            break
    return {"lignes": lignes, "rayon_ecart_5kmh_bosetti_setra102_m": rb}


# ----------------------------------------------------------------------------- C4
def c4_couplage(vals, vehs):
    b_cond = vals["acc.max_conducteur_bosetti"]
    pic = vals["acc.demarrage_pic"]
    res = []
    for vk in [2, 10, 30, 50, 70, 90, 110]:
        av = np.array([vh.acceleration_max(vk / 3.6) for vh in vehs])
        res.append({"v_kmh": vk, "a_vehicule_max_ms2": resume(av, (0.05, 0.5, 0.95)),
                    "part_conducteurs_b_bosetti_sup_capacite": round(float(np.mean(b_cond > av)), 3),
                    "part_pic_demarrage_sup_capacite": round(float(np.mean(pic > av)), 3)})
    return {"n": int(len(vehs)), "points": res,
            "note": "conducteurs et véhicules tirés indépendamment (aucune donnée de corrélation style/puissance)"}


# ----------------------------------------------------------------------------- C5
def c5_adherence(vals, mu_list):
    alat = vals["courbe.alat_max_conducteur"]
    urg = vals["dec.urgence_max_markkula"]
    out = []
    for mu in mu_list:
        out.append({"mu": mu, "part_alat_sup_0_5_mu_g": round(float(np.mean(alat > 0.5 * mu * G)), 3),
                    "part_alat_sup_mu_g": round(float(np.mean(alat > mu * G)), 3),
                    "part_urgence_markkula_sup_mu_g": round(float(np.mean(urg > mu * G)), 3)})
    return {"points": out}


# ----------------------------------------------------------------------------- C6
def c6_jaune(vals, rng, jaune_s=3.0, ttl_max=8.0):
    n = len(vals["feu.seuil_arret_jaune"])
    seuil = vals["feu.seuil_arret_jaune"]
    tr = vals["feu.tpr_jaune"]
    v = np.maximum(vals["vit.artere_centre_ville_50"] / 3.6, 3.0)
    b_hab = vals["dec.max_courante_urbain"]
    b_urg = vals["dec.urgence_max_markkula"]
    ttl = rng.uniform(0.0, ttl_max, n)
    arret = ttl > seuil
    reste = ttl - tr
    possible = reste > 0
    dec = np.where(possible, v / (2.0 * np.maximum(reste, 1e-6)), np.inf)
    ar = arret & possible
    # conducteurs qui passent : franchissent la ligne après la fin du jaune si TTL > jaune (vitesse maintenue)
    passe = ~arret
    out = {"hypotheses": {"TTL_au_debut_du_jaune": f"uniforme 0-{ttl_max} s (arrivées uniformes)", "jaune_s": jaune_s,
                          "vitesse": "vitesse libre du réseau artère 50 (ONISR)", "decision": "arrêt si TTL > seuil_i"},
           "part_arrets": round(float(arret.mean()), 3),
           "part_arrets_impossibles_TTL_inf_TPR": round(float((arret & ~possible).mean()), 4),
           "deceleration_demandee_arrets_ms2": resume(dec[ar]),
           "part_arrets_dec_sup_3_05_ITE": round(float(np.mean(dec[ar] > 3.05)), 3),
           "part_arrets_dec_sup_4_5_SUMO": round(float(np.mean(dec[ar] > 4.5)), 3),
           "part_arrets_dec_sup_b_habituelle_conducteur": round(float(np.mean(dec[ar] > b_hab[ar])), 3),
           "part_arrets_dec_sup_urgence_conducteur": round(float(np.mean(dec[ar] > b_urg[ar])), 3),
           "part_passages_apres_fin_jaune": round(float(np.mean(passe & (ttl > jaune_s))), 3),
           "part_des_passages_qui_finissent_au_rouge": round(float(np.mean(ttl[passe] > jaune_s)), 3)}
    # variante : passage interdit si TTL > jaune (contrainte de faisabilité) et arrêt possible
    arret2 = arret | ((ttl > jaune_s) & possible)
    ar2 = arret2 & possible
    out["variante_faisabilite"] = {
        "regle": "le conducteur s'arrête aussi si TTL > durée du jaune et que l'arrêt est possible",
        "part_arrets": round(float(arret2.mean()), 3),
        "deceleration_demandee_arrets_ms2": resume(dec[ar2]),
        "part_arrets_dec_sup_b_habituelle_conducteur": round(float(np.mean(dec[ar2] > b_hab[ar2])), 3),
        "P_arret_TTL_2_5_3_5_5_5": [round(float(np.mean(arret2[(ttl > c - 0.25) & (ttl < c + 0.25)])), 3) for c in (2.5, 3.5, 5.5)]}
    out["P_arret_logistique_TTL_2_5_3_5_5_5"] = [round(float(np.mean(arret[(ttl > c - 0.25) & (ttl < c + 0.25)])), 3) for c in (2.5, 3.5, 5.5)]
    return out


# ----------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--files", type=int, default=300)
    ap.add_argument("--graine", type=int, default=20261017)
    a = ap.parse_args(argv)
    P, _prof = mc.charger()
    ix = mc.index(P)
    J = json.load(open(F_VEH, encoding="utf-8"))
    rng = np.random.default_rng(a.graine)
    # longueur médiane des 10 voitures de référence ADAC (volet 01)
    longueurs = []
    for c, d in J["classes"].items():
        for p in d.get("parametres", []):
            if p["id"].endswith("-EXEMPLES"):
                longueurs += [m["longueur_mm"] / 1000 for m in p["parametres"]["modeles"] if m.get("longueur_mm")]
    longueurs = sorted(set(longueurs))
    L_med = round(float(np.median(longueurs)), 3)

    vals, _ = mc.tirer_population(P, a.n, rng)
    rnd = random.Random(a.graine)
    vehs = [tirer_vp(J, rnd) for _ in range(a.n)]

    res = {"meta": {"script": "recon/trafic/conception/verifier_coherence.py", "graine": a.graine, "n_conducteurs": a.n,
                    "entrees": {"conducteurs": str(DOC17 / "02_Conducteurs" / "conducteurs_parametres.json"),
                                "vehicules": str(F_VEH)},
                    "longueurs_reference_m": longueurs,
                    "avertissement": "calculs de cohérence de la conception, pas une validation du modèle complet"}}
    res["C1_decharge_feu"] = c1_decharge(P, ix, L_med, a.files, rng)
    res["C2_equilibre_suivi"] = c2_equilibre(res["C1_decharge_feu"]["T_suivi_median_s"],
                                             res["C1_decharge_feu"]["conducteur_median"]["tiv.ecart_arret"], [41.2, 50.0])
    res["C3_courbes"] = c3_courbes(vals, ix)
    res["C4_couplage_conducteur_vehicule"] = c4_couplage(vals, vehs)
    res["C5_adherence"] = c5_adherence(vals, [1.0, 0.75, 0.49])
    res["C6_feu_jaune"] = c6_jaune(vals, rng)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
