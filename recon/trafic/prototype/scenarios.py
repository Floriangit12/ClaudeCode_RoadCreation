"""Scénarios du prototype (même géométrie que les réseaux SUMO de sumo_scenarios.py).

  S1  file de 20 VL arrêtée au rouge, démarrage au vert (artère 50, CR-04) — V-08, V-10, V-14, V-24
  S1b arrivées libres au début du jaune (jaune 3 s), TTL uniforme 0-8 s — V-11, V-12, option H-11
  S2  peloton de 11 VL à 60 km/h derrière un meneur lent (route 80, CR-06) ; freinage d'urgence du meneur
  S3  approche d'un STOP et insertion en tourne-à-droite sur une artère à 50 km/h (600 véh/h) — V-16, V-17
  S4  courbe de rayon 60 m (90°) sur route à 80 km/h hors agglomération — V-15
  S5  dos-d'âne en zone 30 — V-19

Les conventions propres aux scénarios (longueurs, débits, profil du meneur de S2) sont dans CONVENTIONS ;
elles ne sont pas des données de comportement.
"""
from __future__ import annotations

import math

import numpy as np

from conducteurs import tirer_conducteurs
from parametres import Parametres
from route import Courbe, Feu, Jonction, Ralentisseur, Route, Stop
from simulateur import Simulation
from vehicules import tirer_vehicules

CONVENTIONS = {
    "S1": {"n_vehicules": 20, "ligne_s": 200.0, "longueur": 400.0, "duree_s": 70.0,
           "note": "file à l'arrêt, premier véhicule à 1 m de la ligne (jmStoplineGap SUMO), écarts s0_i"},
    "S1b": {"ligne_s": 300.0, "longueur": 400.0, "ttl_max_s": 8.0, "jaune_s": 3.0,
            "note": "jaune 3 s en agglomération (Certu Feux 2010 p. 68) ; TTL au début du jaune uniforme 0-8 s (hypothèse du calcul C6)"},
    "S2": {"n_vehicules": 11, "v_peloton_kmh": 60.0, "t_freinage_s": 40.0, "duree_s": 60.0,
           "decel_meneur_ms2": 6.68, "decel_meneur_variante_ms2": 4.0, "jerk_meneur_ms3": 12.65,
           "note": "meneur lent à 60 km/h (peloton derrière un véhicule lent, convention) ; freinage à la "
                   "décélération maximale moyenne de Markkula 2016 (6,68 m/s²), montée au jerk du modèle de "
                   "référence FSM de l'ONU R157 (12,65 m/s³, REF.r157.fsm) ; variante : 4,0 m/s² (décélération de confort du FSM, REF.r157.fsm)"},
    "S3": {"debit_prioritaire_veh_h": 600, "debit_secondaire_veh_h": 180, "duree_s": 2400.0,
           "note": "mêmes débits que le scénario S3 du volet 03 (convention) ; seul le flux prioritaire venant de la gauche est en conflit avec un tourne-à-droite"},
    "S4": {"R_m": 60.0, "angle_deg": 90.0, "droite_amont_m": 1000.0, "droite_aval_m": 600.0, "Vlim_setra_kmh": 102,
           "note": "route bidirectionnelle à 80 km/h, 2 voies de 6-7 m (Vlim Sétra 102) ; véhicules isolés"},
    "S5": {"ralentisseur_s": 300.0, "longueur_ralentisseur_m": 4.0, "longueur": 500.0,
           "note": "zone 30 (CR-01, loi belge H-13) ; longueur du dispositif 4 m (convention) ; véhicules isolés ; loi de franchissement belge nationale (Vias 2021), variante « bruxelles » (dispositifs efficaces)"},
}


def tirer_agents(P: Parametres, n: int, graine: int):
    rng = np.random.default_rng(graine)
    pop = tirer_conducteurs(P, n, rng)
    veh = tirer_vehicules(P, n, graine, rng)
    return pop, veh


# ----------------------------------------------------------------------------- S1
def s1_file_feu(P, n_files=200, graine=1, **opt):
    c = CONVENTIONS["S1"]
    nv = c["n_vehicules"]
    route = Route("artere_S1", voie=0, longueur=c["longueur"], reseau="artere_centre_ville_50",
                  feux=[Feu(s=c["ligne_s"], t_vert=0.0)], detecteurs=[c["ligne_s"]])
    N = n_files * nv
    pop, veh = tirer_agents(P, N, graine)
    s = np.zeros(N)
    arr = P.v("arret_ligne_feu_m")
    for q in range(n_files):
        k0 = q * nv
        s[k0] = c["ligne_s"] - arr
        for k in range(1, nv):
            s[k0 + k] = s[k0 + k - 1] - veh["longueur"][k0 + k - 1] - pop["LON.tiv.ecart_arret"][k0 + k]
    agents = {"route": np.zeros(N, int), "couloir": np.repeat(np.arange(n_files), nv), "t_insert": np.full(N, -1.0),
              "s_insert": s, "v_insert": np.zeros(N), "pop": pop, "veh": veh, "arret_en_file": np.ones(N, bool)}
    sim = Simulation(P, [route], agents, graine=graine, t0=-1.0, **opt)
    sim.executer(c["duree_s"])
    return sim, {"rang": np.tile(np.arange(1, nv + 1), n_files), "n_files": n_files, "n_vehicules": nv}


# ----------------------------------------------------------------------------- S1b
def s1b_jaune(P, n=3000, graine=2, **opt):
    c = CONVENTIONS["S1b"]
    pop, veh = tirer_agents(P, n, graine)
    rng = np.random.default_rng([graine, 7])
    from conducteurs import v0_reseau
    v0 = v0_reseau(P, pop, "artere_centre_ville_50")
    ttl = rng.uniform(0.0, c["ttl_max_s"], n)
    t_jaune = (c["ligne_s"] - ttl * v0) / v0
    route = Route("artere_S1b", voie=0, longueur=c["longueur"], reseau="artere_centre_ville_50",
                  feux=[Feu(s=c["ligne_s"], t_vert=-1e9, t_jaune=t_jaune, duree_jaune=c["jaune_s"])],
                  detecteurs=[c["ligne_s"]])
    agents = {"route": np.zeros(n, int), "couloir": np.arange(n), "t_insert": np.zeros(n), "s_insert": np.zeros(n),
              "v_insert": v0, "pop": pop, "veh": veh}
    opt.setdefault("enregistrer", False)
    sim = Simulation(P, [route], agents, graine=graine, **opt)
    sim.executer(float(np.max(t_jaune)) + 20.0)
    return sim, {"ttl_debut_jaune": ttl, "t_jaune": t_jaune, "v0": v0}


# ----------------------------------------------------------------------------- S2
def s2_freinage_urgence(P, n_pelotons=300, graine=3, decel_meneur=None, **opt):
    c = CONVENTIONS["S2"]
    nv = c["n_vehicules"]
    v_p = c["v_peloton_kmh"] / 3.6
    N = n_pelotons * nv
    pop, veh = tirer_agents(P, N, graine)
    route = Route("route80_S2", voie=0, longueur=4000.0, reseau="route_2_3_voies_80")
    from conducteurs import T_suivi
    Ts = np.maximum(T_suivi(P, pop, "route_2_3_voies_80"), 0.1)
    s0 = pop["LON.tiv.ecart_arret"]
    s = np.zeros(N)
    pil = np.zeros(N, bool)
    for q in range(n_pelotons):
        k0 = q * nv
        s[k0] = 800.0
        pil[k0] = True
        for k in range(1, nv):
            s[k0 + k] = s[k0 + k - 1] - veh["longueur"][k0 + k - 1] - (s0[k0 + k] + v_p * Ts[k0 + k])
    t_f, dmen, jmen = c["t_freinage_s"], decel_meneur or c["decel_meneur_ms2"], c["jerk_meneur_ms3"]

    def profil(t, idx, v):
        if t < t_f:
            return np.zeros(len(idx))
        a = -min(dmen, jmen * (t - t_f))
        return np.where(v > 0, a, 0.0)

    agents = {"route": np.zeros(N, int), "couloir": np.repeat(np.arange(n_pelotons), nv), "t_insert": np.zeros(N),
              "s_insert": s, "v_insert": np.full(N, v_p), "pop": pop, "veh": veh, "pilote": pil, "profil_pilote": profil}
    sim = Simulation(P, [route], agents, graine=graine, **opt)
    sim.executer(c["duree_s"])
    return sim, {"rang": np.tile(np.arange(0, nv), n_pelotons), "t_freinage": t_f, "n_pelotons": n_pelotons}


# ----------------------------------------------------------------------------- S3
def s3_stop(P, geo: dict, n_rep=6, graine=4, **opt):
    """geo : longueurs lues dans le réseau SUMO (sumo_scenarios.geometrie_s3)."""
    c = CONVENTIONS["S3"]
    L_W, L_int, L_E, L_S, L_turn, R_turn = (geo[k] for k in ("L_W", "L_int_maj", "L_E", "L_S", "L_virage", "R_virage"))
    s_merge = L_W + L_int
    L_maj = L_W + L_int + L_E
    maj = Route("principale_S3", voie=1, longueur=L_maj, reseau="artere_centre_ville_50", detecteurs=[L_W, s_merge])
    mino = Route("secondaire_S3", voie=0, longueur=L_S + L_turn + L_E, reseau="artere_centre_ville_50",
                 courbes=[Courbe(L_S, L_S + L_turn, R_turn, agglo=True)],
                 stops=[Stop(s=L_S, voie_prioritaire=1, s_conflit=s_merge, creneau_ref_s=P.v("creneau_TAD_50_s"))],
                 jonction=Jonction(s=L_S, voie=1, s_cible=s_merge - L_turn), detecteurs=[L_S - 30.0, L_S - 3.0, L_S, L_S + L_turn])
    rng = np.random.default_rng([graine, 11])
    t_ins, rte, cl = [], [], []
    for q in range(n_rep):
        for r_i, deb in ((0, c["debit_prioritaire_veh_h"]), (1, c["debit_secondaire_veh_h"])):
            t = rng.exponential(3600.0 / deb)
            while t < c["duree_s"]:
                t_ins.append(t), rte.append(r_i), cl.append(q)
                t += rng.exponential(3600.0 / deb)
    N = len(t_ins)
    pop, veh = tirer_agents(P, N, graine)
    from conducteurs import v0_reseau
    v0 = v0_reseau(P, pop, "artere_centre_ville_50")
    agents = {"route": np.array(rte), "couloir": np.array(cl), "t_insert": np.array(t_ins), "s_insert": np.zeros(N),
              "v_insert": v0, "force": np.zeros(N, bool), "pop": pop, "veh": veh}
    opt.setdefault("enregistrer", False)
    sim = Simulation(P, [maj, mino], agents, graine=graine, **opt)
    sim.executer(c["duree_s"] + 120.0)
    return sim, {"geo": geo, "s_merge": s_merge, "n_rep": n_rep}


# ----------------------------------------------------------------------------- S4
def s4_courbe(P, n=1000, graine=5, **opt):
    c = CONVENTIONS["S4"]
    L_c = c["R_m"] * math.radians(c["angle_deg"])
    s_a = c["droite_amont_m"]
    route = Route("route80_S4", voie=0, longueur=s_a + L_c + c["droite_aval_m"], reseau="route_2_3_voies_80",
                  vlim_setra_kmh=c["Vlim_setra_kmh"], courbes=[Courbe(s_a, s_a + L_c, c["R_m"])],
                  detecteurs=[s_a, s_a + L_c / 2, s_a + L_c])
    pop, veh = tirer_agents(P, n, graine)
    from conducteurs import v0_reseau
    v0 = v0_reseau(P, pop, "route_2_3_voies_80")
    agents = {"route": np.zeros(n, int), "couloir": np.arange(n), "t_insert": np.zeros(n), "s_insert": np.zeros(n),
              "v_insert": v0, "pop": pop, "veh": veh}
    sim = Simulation(P, [route], agents, graine=graine, **opt)
    sim.executer(route.longueur / 8.0, arret_si_vide=True)
    return sim, {"s_debut": s_a, "s_fin": s_a + L_c, "R": c["R_m"], "v0": v0}


# ----------------------------------------------------------------------------- S5
def s5_ralentisseur(P, n=1000, graine=6, **opt):
    c = CONVENTIONS["S5"]
    sh, lh = c["ralentisseur_s"], c["longueur_ralentisseur_m"]
    route = Route("zone30_S5", voie=0, longueur=c["longueur"], reseau="zone_30_be",
                  ralentisseurs=[Ralentisseur(sh, lh)],
                  detecteurs=[sh - 40.0, sh, sh + lh, sh + lh + 10.0, sh + lh + 15.0, sh + lh + 20.0])
    pop, veh = tirer_agents(P, n, graine)
    from conducteurs import v0_reseau
    v0 = v0_reseau(P, pop, "zone_30_be")
    agents = {"route": np.zeros(n, int), "couloir": np.arange(n), "t_insert": np.zeros(n), "s_insert": np.zeros(n),
              "v_insert": v0, "pop": pop, "veh": veh}
    sim = Simulation(P, [route], agents, graine=graine, **opt)
    sim.executer(c["longueur"] / 3.0, arret_si_vide=True)
    return sim, {"s_ralentisseur": sh, "longueur": lh, "v0": v0}
