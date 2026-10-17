"""Exécute le prototype (v0.2) : 5 scénarios (+ S1b) avec notre modèle et dans SUMO, métriques, figures, tableaux.

  python recon/trafic/prototype/executer.py [--rapide] [--sans-sumo]

Sorties (D:/DocRoute/17_Modele_Vehicules_Conducteurs/05_Prototype/) :
  resultats/resultats_prototype.json   toutes les métriques (modèle et SUMO) et les cibles citées
  figures/*.png                        une figure par scénario (1300 × 750 px au plus)
  tableaux/*.md, *.csv                 tableau des cibles et tableaux par scénario
  sumo/                                réseaux netconvert et fichiers de routes
Durée : environ 15 min (SUMO compris) ; --rapide : petits échantillons pour vérifier la chaîne.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
PYLIB = Path("D:/DocRoute/17_Modele_Vehicules_Conducteurs/tmp/03/pylib")   # matplotlib installé hors de C: (volet 03)
if PYLIB.exists() and str(PYLIB) not in sys.path:
    sys.path.append(str(PYLIB))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import analyse as A  # noqa: E402
import calage  # noqa: E402
import figures as F  # noqa: E402
import lateral  # noqa: E402
import modele as M  # noqa: E402
import scenarios as SC  # noqa: E402
import sumo_scenarios as SS  # noqa: E402
from parametres import DOC05, Parametres, ecrire_parametres_prototype  # noqa: E402

FIG, TAB, RES = DOC05 / "figures", DOC05 / "tableaux", DOC05 / "resultats"


def journal(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:7.1f} s] {msg}", flush=True)


def cibles(P):
    ix = P.par
    return {
        "salles_tiv": ix("VAL.tiv.file_feu"), "salles_pic": ix("VAL.acc.demarrage_file"),
        "saturation_fr": ix("VAL.feu.saturation_fr"), "saturation_hcm": ix("VAL.feu.saturation_hcm"),
        "demarrage_salles": ix("LON.eidm.demarrage_salles2020"), "pic_demarrage": ix("LON.acc.demarrage_pic"),
        "jerk_confort": ix("LON.acc.jerk_confort"), "logistique": ix("TAC.feu.seuil_arret_jaune"),
        "dec_jaune": ix("VAL.feu.dec_jaune_conception"), "tpr_signal": ix("PER.tpr.inattendu_signal"),
        "dec_urgence_markkula": ix("LON.dec.urgence_max_markkula"), "dec_p10_inattendu": ix("VAL.dec.p10_inattendu"),
        "creneau_fr": ix("TAC.creneau.norme_fr"), "creneau_dispersion": ix("VAL.creneau.dispersion"),
        "stop": ix("TAC.stop.comportement")["modalites"], "ralent": ix("TAC.ralent.vitesse_franchissement"),
        "ralent_objectif": ix("VAL.ralent.objectif_conception"), "setra": ix("LAT.courbe.v85_setra"),
        "cfts": ix("VAL.courbe.vitesse_conventionnelle_cfts"), "pieton_approche": ix("TAC.pieton.approche"),
        "vit_zone30": ix("LON.vit.zone_30_be"), "vit_80": ix("LON.vit.route_2_3_voies_80"),
        "vit_artere": ix("LON.vit.artere_centre_ville_50"),
    }


def profil(s_grid, trajs):
    """Médiane, P15, P85 de la vitesse (km/h) sur une grille d'abscisses à partir de trajectoires (s, v)."""
    M = np.full((len(trajs), s_grid.size), np.nan)
    for k, (s, v) in enumerate(trajs):
        ok = np.isfinite(s) & np.isfinite(v)
        s, v = s[ok], v[ok]
        if s.size < 2:
            continue
        o = np.argsort(s)
        s, v = s[o], v[o]
        m = (s_grid >= s[0]) & (s_grid <= s[-1])
        M[k, m] = np.interp(s_grid[m], s, v) * 3.6
    return np.nanmedian(M, axis=0), np.nanpercentile(M, 15, axis=0), np.nanpercentile(M, 85, axis=0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--sans-sumo", action="store_true")
    ap.add_argument("--scenarios", default="V08,S1,S1b,S2,S3,S4,S5",
                    help="sous-ensemble à recalculer ; les autres résultats sont repris du JSON existant")
    a = ap.parse_args(argv)
    voulus = set(a.scenarios.split(","))
    rap = a.rapide
    for d in (FIG, TAB, RES):
        d.mkdir(parents=True, exist_ok=True)
    P = Parametres()
    C = cibles(P)
    R = {"meta": {"date": time.strftime("%Y-%m-%d %H:%M"), "rapide": rap, "parametres_prototype": {k: v["valeur"] for k, v in P.proto.items()},
                  "pas_s": P.v("pas_s")}, "cibles": C}
    F_RES = RES / "resultats_prototype.json"
    if voulus != {"V08", "S1", "S1b", "S2", "S3", "S4", "S5"} and F_RES.exists():
        anc = json.loads(F_RES.read_text(encoding="utf-8"))
        R.update({k: v for k, v in anc.items() if k not in ("meta", "cibles")})
        R["meta"]["recalcules"] = sorted(voulus)

    # ------------------------------------------------------------------ V-08 démarrage isolé, V-23 véhicules
    if "V08" in voulus:
        journal("V-08 démarrage isolé")
        m = calage.demarrage_isole(P, 500 if rap else 2000)
        R["V08_demarrage_isole"] = {"t_1ms_s": calage._q(m[:, 0]), "t_pic_s": calage._q(m[:, 1]), "pic_ms2": calage._q(m[:, 2])}
        R["V23_vehicules"] = {}
        for parc in ("circulation", "neuf"):
            old = P.proto["parc_vehicules"]["valeur"]
            P.proto["parc_vehicules"]["valeur"] = parc
            pop, veh = SC.tirer_agents(P, 200 if rap else 1000, 77)
            P.proto["parc_vehicules"]["valeur"] = old
            objs = veh["objets"]
            R["V23_vehicules"][parc] = {"t_0_100_s": A.q([o.temps_acceleration(0, 100) for o in objs]),
                                        "t_60_100_s": A.q([o.temps_acceleration(60, 100) for o in objs]),
                                        "d_100_0_m": A.q([o.distance_freinage(100) for o in objs]),
                                        "a_max_50kmh_ms2": A.q([o.acceleration_max(50 / 3.6) for o in objs]),
                                        "masse_kg": A.q(veh["masse"], (1, 5, 50, 95, 99)),
                                        "parts_familles": {f: round(float(np.mean(veh["famille"] == f)), 3)
                                                           for f in ("electrique", "thermique_auto_hybride", "thermique_manuelle")},
                                        "mu_sec": A.q(veh["mu"])}
        journal("contrôles de population")
        R["population"] = A.controles_population(P, n=50000 if rap else 200000)

    # ------------------------------------------------------------------ S1
    if "S1" in voulus:
        journal("S1 modèle")
        nf = 40 if rap else 200
        sim1, meta1 = SC.s1_file_feu(P, n_files=nf, graine=1)
        R["S1"] = {"modele": A.s1_modele(sim1, meta1), "sumo": {}, "diagnostic_v0": A.s1_diagnostic_v0(sim1, meta1)}
        R["S1"]["part_T_decharge_fixe_par_H17"] = round(float(np.mean(P.v("T_decharge_rapport") * sim1.Ts < sim1.tpr_ant)), 4)
        journal("S1 5 graines")
        R["S1"]["graines"] = calage.collisions_s1(P, graines=(1, 2, 3, 4, 5), n_files=nf)
        sim1m, meta1m = SC.s1_file_feu(P, n_files=nf, graine=1, reaction_depart="meneur")
        R["S1"]["modele_variante_meneur"] = A.s1_modele(sim1m, meta1m)
        # sensibilités : sans H-17 (T < Δ_a permis) ; troncature de la loi ONISR (H-04)
        cles = ("debit_saturation_veh_h", "tiv_moyen_par_rang_s", "collisions", "collisions_secondaires")
        sens = {}
        simx, metax = SC.s1_file_feu(P, n_files=nf, graine=1, T_min_action=False)
        rx = A.s1_modele(simx, metax)
        sens["sans_H17"] = {k: rx[k] for k in cles}
        for q0 in (0.0, 0.10):
            old = P.proto["v0_quantile_min"]["valeur"]
            P.proto["v0_quantile_min"]["valeur"] = q0
            simx, metax = SC.s1_file_feu(P, n_files=nf, graine=1)
            P.proto["v0_quantile_min"]["valeur"] = old
            rx = A.s1_modele(simx, metax)
            sens[f"v0_quantile_min_{q0}"] = dict({k: rx[k] for k in cles}, diagnostic_v0=A.s1_diagnostic_v0(simx, metax))
        R["S1"]["sensibilites"] = sens
        del simx
        if not a.sans_sumo:
            R["S1"]["sumo_calage_tau"] = {}
            for cfg in SS.CONFIGS:
                fac = None
                if SS.CONFIGS[cfg]["nos_lois"]:
                    journal(f"S1 SUMO calage de tau {cfg}")
                    fac, hist = SS.caler_tau_s1(sim1, meta1, cfg, n_rep=6 if rap else 20)
                    R["S1"]["sumo_calage_tau"][cfg] = {"facteur_tau_sur_T_suivi": fac, "iterations": hist}
                journal(f"S1 SUMO {cfg}")
                res = SS.s1_sumo(sim1, meta1, cfg, n_rep=8 if rap else 30, facteur_tau=fac)
                R["S1"]["sumo"][cfg] = A.s1_sumo(res)
        F.fig_s1(R["S1"], C, FIG / "S1_file_feu.png")
        del sim1, sim1m

    # ------------------------------------------------------------------ S1b
    if "S1b" in voulus:
        journal("S1b jaune")
        R["S1b"] = {}
        for cle, h11 in (("sans_H11", False), ("avec_H11", True)):
            sim, meta = SC.s1b_jaune(P, n=800 if rap else 4000, option_h11=h11)
            R["S1b"][cle] = A.s1b_modele(sim, meta)
            R["S1b"][cle]["_decel"] = np.array([-sim.a_min[x["agent"]] for x in sim.journal["jaune"] if x["arret"]])
        R["S1b"]["sumo_volet03"] = {k: P.par(f"REF.sim.S2.{k}") for k in ("krauss_pas1s", "krauss_pas01s", "eidm_pas01s")}
        F.fig_s1b(R["S1b"], C, FIG / "S1b_jaune.png")

    # ------------------------------------------------------------------ S2
    if "S2" in voulus:
        journal("S2 modèle")
        npl = 60 if rap else 300
        R["S2"] = {"modele": {}, "sumo_6.68": {}, "sumo_4.0": {}, "_sumo_delais": {}}
        sim2 = None
        for mode in ("markkula", "tpr"):
            for dm in (6.68, 4.0):
                sim, meta = SC.s2_freinage_urgence(P, n_pelotons=npl, mode_urgence=mode, decel_meneur=dm)
                r = A.s2_modele(sim, meta)
                tr = sim.traces()
                apres = tr["t"] >= meta["t_freinage"]
                idx = np.arange(1, npl * 11, 11)
                r["_delais_rang1"] = (A._onset(tr["t"], tr["a"][:, idx], apres) - A._onset(tr["t"], tr["a"][:, idx - 1], apres))
                r["_delais_rang1"] = r["_delais_rang1"][np.isfinite(r["_delais_rang1"])]
                R["S2"]["modele"][f"{mode}_{dm}"] = r
                if mode == "markkula" and dm == 6.68:
                    sim2 = sim
        if not a.sans_sumo:
            meta2 = {"n_pelotons": npl}
            for dm in (6.68, 4.0):
                for cfg in SS.CONFIGS_S2:
                    journal(f"S2 SUMO {cfg} {dm}")
                    res = SS.s2_sumo(sim2, meta2, cfg, n_rep=8 if rap else 30, decel_meneur=dm)
                    R["S2"][f"sumo_{dm}"][cfg] = A.s2_sumo(res)
                    if dm == 6.68:
                        R["S2"]["_sumo_delais"][cfg] = [r_["rangs"][1]["delai_feux_stop"] for r_ in res if 1 in r_["rangs"]
                                                        and np.isfinite(r_["rangs"][1]["delai_feux_stop"])]
            # contrôle de la conclusion v0.1 : meneur SUMO avec decel = apparentDecel = 9 m/s² (Krauss sûr par construction)
            journal("S2 SUMO krauss_nos_lois, meneur decel 9")
            res = SS.s2_sumo(sim2, meta2, "krauss_nos_lois", n_rep=8 if rap else 30, decel_meneur=6.68, meneur_b=False)
            R["S2"]["sumo_6.68_meneur_decel9"] = {"krauss_nos_lois": A.s2_sumo(res)}
        F.fig_s2(R["S2"], C, FIG / "S2_freinage_urgence.png")
        del sim2

    # ------------------------------------------------------------------ S3
    if "S3" in voulus:
        journal("S3 modèle")
        geo = SS.geometrie_s3()
        sim3, meta3 = SC.s3_stop(P, geo, n_rep=2 if rap else 6)
        R["S3"] = {"geometrie": {k: v for k, v in geo.items() if not k.startswith("decalages")},
                   "modele": A.s3_modele(sim3, meta3), "sumo": {}}
        sim3b, meta3b = SC.s3_stop(P, geo, n_rep=2 if rap else 6, h10=False)
        R["S3"]["modele_sans_H10"] = A.s3_modele(sim3b, meta3b)
        del sim3b
        if not a.sans_sumo:
            for cfg in SS.CONFIGS:
                journal(f"S3 SUMO {cfg}")
                rows, amin = SS.s3_sumo(sim3, cfg, n_rep=1 if rap else 3)
                R["S3"]["sumo"][cfg] = A.s3_sumo(rows, amin)
            # « nos lois » sans transposition du créneau (impatience 0 par défaut) : transfert brut, non comparable
            R["S3"]["sumo_transfert_brut"] = {}
            for cfg in ("krauss_nos_lois", "eidm_nos_lois"):
                journal(f"S3 SUMO {cfg} transfert brut")
                rows, amin = SS.s3_sumo(sim3, cfg, n_rep=1 if rap else 3, impatience=None)
                R["S3"]["sumo_transfert_brut"][cfg] = A.s3_sumo(rows, amin)
        F.fig_s3(R["S3"], C, FIG / "S3_stop_creneaux.png")
        del sim3

    # ------------------------------------------------------------------ S4
    if "S4" in voulus:
        journal("S4 modèle")
        c4 = SC.CONVENTIONS["S4"]
        n4 = 300 if rap else 1000
        sim4, meta4 = SC.s4_courbe(P, n=n4)
        s_a, s_b, Rc = meta4["s_debut"], meta4["s_fin"], meta4["R"]
        pts = {"v_entree": s_a, "v_milieu": 0.5 * (s_a + s_b), "v_sortie": s_b}
        rows = A.libres_modele(sim4, pts, s_a, zone=(s_a, s_b))
        tr4 = sim4.traces()
        vmil = np.array([r["v_milieu"] for r in rows]) * 3.6
        alat = (np.array([r["v_milieu"] for r in rows])) ** 2 / Rc
        R["S4"] = {"modele": A.resume_libres(rows, ["v_entree", "v_milieu", "v_sortie", "v_min_zone", "debut_freinage_m",
                                                    "decel_max_approche_ms2", "decel_moy_approche_ms2", "jerk_p95"]),
                   "sumo": {}}
        R["S4"]["modele"]["v_milieu_kmh"] = A.q(vmil)
        R["S4"]["modele"]["a_lat_milieu_ms2"] = A.q(alat)
        R["S4"]["modele"]["part_a_lat_sup_a_lat_conducteur"] = round(float(np.mean(alat > sim4.alat)), 4)
        R["S4"]["modele"]["part_a_lat_sup_0_5_mu_g"] = round(float(np.mean(alat > 0.5 * sim4.mu * 9.81)), 4)
        R["S4"]["modele"]["v0_kmh"] = A.q(sim4.v0 * 3.6)
        R["S4"]["reference"] = {"V85_setra_Vlim102_kmh": round(float(M.v85_setra(Rc, 102)), 1),
                                "V85_setra_Vlim92_kmh": round(float(M.v85_setra(Rc, 92)), 1),
                                "vitesse_conventionnelle_cfts_kmh": dict(zip(C["cfts"]["R_m"], C["cfts"]["V_kmh"])).get(int(Rc)),
                                "SUMO_sqrt_5_5R_kmh": round(math.sqrt(5.5 * Rc) * 3.6, 1)}
        # contrôle latéral (pure pursuit + bicyclette cinématique), post-traitement
        ang = [m_["angle_bicyclette_deg"] for m_ in P.par("VEH.VP-BRAQUAGE-DERIVE")["modeles"]]
        dmax = math.radians(float(np.median(ang)))
        ch = lateral.chemin_courbe(s_a, Rc, math.radians(c4["angle_deg"]), c4["droite_aval_m"] + 50)
        lat = lateral.pure_pursuit(ch, tr4["v"].astype(float), P.v("pas_s"), sim4.veh["empattement"], np.full(sim4.N, dmax))
        R["S4"]["lateral"] = {"ecart_lateral_max_abs_m": A.q(np.nanmax(np.abs(lat["ecart"]), axis=0)),
                              "braquage_max_deg": A.q(np.degrees(np.nanmax(np.abs(lat["delta"]), axis=0))),
                              "lacet_max_deg_s": A.q(np.degrees(np.nanmax(np.abs(lat["lacet"]), axis=0))),
                              "a_y_max_ms2": A.q(np.nanmax(np.abs(lat["ay"]), axis=0)),
                              "delta_max_deg": round(math.degrees(dmax), 2),
                              "conventions": "l_v = 2 m + 1 s × v ; l_r = 0,6 L (H-12, non sourcées)"}
        s_grid = np.arange(s_a - 400, s_b + 200, 2.0)
        R["S4"]["_profil"] = (s_grid,) + profil(s_grid, [(tr4["s"][:, i].astype(float), tr4["v"][:, i].astype(float)) for i in range(sim4.N)])
        R["S4"]["_v_mes_sumo"], R["S4"]["_prof_sumo"] = {}, {}
        if not a.sans_sumo:
            for var in ("arete", "limitee"):
                d, net, aretes = SS.s4_reseau(var)
                off, _ = SS.decalages(net, aretes)
                s_cc = off["CC_0"]
                L_cc = net.getEdge("CC").getLane(0).getLength()
                for cfg in SS.CONFIGS:
                    journal(f"S4 SUMO {var} {cfg}")
                    trajs, off, Lt = SS.libre_sumo(sim4, cfg, f"S4_{var}", d, net, aretes, 80 / 3.6, n=150 if rap else 500, periode=45.0)
                    rr = A.libres_sumo(trajs, {"v_entree": s_cc, "v_milieu": s_cc + L_cc / 2, "v_sortie": s_cc + L_cc}, s_cc,
                                       zone=(s_cc, s_cc + L_cc))
                    key = f"{cfg}|{'arc 80 km/h' if var == 'arete' else 'arc limité à √(5,5 R)'}"
                    R["S4"]["sumo"][key] = A.resume_libres(rr, ["v_milieu", "v_min_zone", "debut_freinage_m", "decel_max_approche_ms2", "jerk_p95"])
                    vm = np.array([r_["v_milieu"] for r_ in rr]) * 3.6
                    R["S4"]["sumo"][key]["v_milieu_kmh"] = A.q(vm)
                    R["S4"]["sumo"][key]["a_lat_milieu_ms2"] = A.q((vm / 3.6) ** 2 / (L_cc / (math.pi / 2)))
                    R["S4"]["sumo"][key]["rayon_voie_m"] = round(L_cc / (math.pi / 2), 2)
                    if cfg in ("krauss_defaut", "eidm_nos_lois"):
                        R["S4"]["_v_mes_sumo"][key] = vm[np.isfinite(vm)]
                        sg = s_grid - s_a + s_cc
                        med, _, _ = profil(sg, [(dd["s"], dd["v"]) for dd in trajs.values()])
                        R["S4"]["_prof_sumo"][key] = (s_grid, med)
        F.fig_profils({"profil_modele": R["S4"]["_profil"], "profils_sumo": R["S4"]["_prof_sumo"], "v_mesure_modele": vmil,
                       "v_mesure_sumo": R["S4"]["_v_mes_sumo"]},
                      {"lignes": [(R["S4"]["reference"]["V85_setra_Vlim102_kmh"], "V85 Sétra (Vlim 102), R = 60 m")],
                       "verticales": [(R["S4"]["reference"]["V85_setra_Vlim102_kmh"], "V85 Sétra 58,5 km/h"),
                                      (R["S4"]["reference"]["vitesse_conventionnelle_cfts_kmh"] or 51, "vitesse conventionnelle VSA (cfts)")]},
                      FIG / "S4_courbe_R60.png", "S4 — courbe R = 60 m (90°) sur route à 80 km/h, véhicules isolés",
                      "abscisse (m) ; zone grise : la courbe", (s_a, s_b), (20, 120),
                      "vitesse au milieu de la courbe (km/h) ; trait gris : 85e centile")
        del sim4, tr4, lat

    # ------------------------------------------------------------------ S5
    if "S5" in voulus:
        journal("S5 modèle")
        c5 = SC.CONVENTIONS["S5"]
        sim5, meta5 = SC.s5_ralentisseur(P, n=300 if rap else 1000)
        sh, lh = meta5["s_ralentisseur"], meta5["longueur"]
        pts5 = {"v_amont_40m": sh - 40, "v_ralentisseur": sh + lh / 2, "v_aval_10m": sh + lh + 10, "v_aval_15m": sh + lh + 15,
                "v_aval_20m": sh + lh + 20}
        rows5 = A.libres_modele(sim5, pts5, sh, zone=(sh, sh + lh))
        tr5 = sim5.traces()
        v_aval = np.array([np.nanmean([r_["v_aval_10m"], r_["v_aval_15m"], r_["v_aval_20m"]]) for r_ in rows5]) * 3.6
        R["S5"] = {"modele": A.resume_libres(rows5, list(pts5) + ["v_min_zone", "debut_freinage_m", "decel_max_approche_ms2",
                                                                 "decel_moy_approche_ms2", "jerk_p95"]), "sumo": {}}
        R["S5"]["modele"]["v_aval_10_20m_kmh"] = A.q(v_aval)
        R["S5"]["modele"]["v_ralentisseur_kmh"] = A.q(np.array([r_["v_min_zone"] for r_ in rows5]) * 3.6)
        R["S5"]["modele"]["v0_kmh"] = A.q(sim5.v0 * 3.6)
        R["S5"]["modele"]["v_r_tiree_kmh"] = A.q(sim5.v_ralent * 3.6)
        sim5b, _ = SC.s5_ralentisseur(P, n=300 if rap else 1000, ralent_variante="bruxelles")
        rows5b = A.libres_modele(sim5b, pts5, sh, zone=(sh, sh + lh))
        v_aval_b = np.array([np.nanmean([r_["v_aval_10m"], r_["v_aval_15m"], r_["v_aval_20m"]]) for r_ in rows5b]) * 3.6
        R["S5"]["modele_variante_bruxelles"] = A.resume_libres(rows5b, ["debut_freinage_m", "decel_max_approche_ms2", "decel_moy_approche_ms2"])
        R["S5"]["modele_variante_bruxelles"]["v_aval_10_20m_kmh"] = A.q(v_aval_b)
        R["S5"]["modele_variante_bruxelles"]["v_ralentisseur_kmh"] = A.q(np.array([r_["v_min_zone"] for r_ in rows5b]) * 3.6)
        R["S5"]["modele_variante_bruxelles"]["v_r_tiree_kmh"] = A.q(sim5b.v_ralent * 3.6)
        R["S5"]["_v_aval_bruxelles"] = v_aval_b
        del sim5b
        s_grid5 = np.arange(0.0, c5["longueur"], 2.0)
        R["S5"]["_profil"] = (s_grid5,) + profil(s_grid5, [(tr5["s"][:, i].astype(float), tr5["v"][:, i].astype(float)) for i in range(sim5.N)])
        R["S5"]["_v_mes_sumo"], R["S5"]["_prof_sumo"] = {}, {}
        if not a.sans_sumo:
            for var, vh in (("sans_traitement", 30.0), ("limite_moyenne", C["ralent"]["moyenne"])):
                d, net, aretes = SS.s5_reseau(vh, var)
                off, _ = SS.decalages(net, aretes)
                s_h = off["HH_0"]
                for cfg in SS.CONFIGS:
                    journal(f"S5 SUMO {var} {cfg}")
                    trajs, off, Lt = SS.libre_sumo(sim5, cfg, f"S5_{var}", d, net, aretes, 30 / 3.6, n=150 if rap else 500, periode=35.0)
                    rr = A.libres_sumo(trajs, {"v_aval_10m": s_h + lh + 10, "v_aval_15m": s_h + lh + 15, "v_aval_20m": s_h + lh + 20,
                                               "v_amont_40m": s_h - 40}, s_h, zone=(s_h, s_h + lh))
                    lim = str(C["ralent"]["moyenne"]).replace(".", ",")
                    key = f"{cfg}|{'sans traitement' if var == 'sans_traitement' else 'tronçon limité à ' + lim + ' km/h'}"
                    va = np.array([np.nanmean([r_["v_aval_10m"], r_["v_aval_15m"], r_["v_aval_20m"]]) for r_ in rr]) * 3.6
                    R["S5"]["sumo"][key] = A.resume_libres(rr, ["v_min_zone", "debut_freinage_m", "decel_max_approche_ms2", "jerk_p95"])
                    R["S5"]["sumo"][key]["v_aval_10_20m_kmh"] = A.q(va)
                    R["S5"]["sumo"][key]["v_ralentisseur_kmh"] = A.q(np.array([r_["v_min_zone"] for r_ in rr]) * 3.6)
                    if cfg in ("krauss_defaut", "eidm_nos_lois"):
                        R["S5"]["_v_mes_sumo"][key] = va[np.isfinite(va)]
                        med, _, _ = profil(s_grid5, [(dd["s"], dd["v"]) for dd in trajs.values()])
                        R["S5"]["_prof_sumo"][key] = (s_grid5, med)
        F.fig_profils({"profil_modele": R["S5"]["_profil"], "profils_sumo": R["S5"]["_prof_sumo"], "v_mesure_modele": v_aval,
                       "v_mesure_sumo": R["S5"]["_v_mes_sumo"]},
                      {"lignes": [(30.0, "objectif de conception 30 km/h (Certu 2010)")],
                       "loi_cible": (C["ralent"]["moyenne"], C["ralent"]["ecart_type"], "Vias 2021, Belgique : N(34,0 ; 7,24) km/h, 10-20 m en aval"),
                       "loi_cible_2": (27.6, 6.46, "Vias 2021, Bruxelles : N(27,6 ; 6,46) km/h"),
                       "mesure_variante": (R["S5"]["_v_aval_bruxelles"], "notre modèle, loi bruxelloise")},
                      FIG / "S5_ralentisseur.png", "S5 — dos-d'âne en zone 30, véhicules isolés", "abscisse (m) ; zone grise : le dispositif",
                      (sh, sh + lh), (0, 70), "vitesse moyenne 10 à 20 m en aval du dispositif (km/h)")
        del sim5, tr5

    # ------------------------------------------------------------------ écriture
    def propre(o):
        if isinstance(o, dict):
            return {str(k): propre(v) for k, v in o.items() if not str(k).startswith("_")}
        if isinstance(o, (list, tuple)):
            return [propre(v) for v in o]
        if isinstance(o, np.ndarray):
            return [propre(v) for v in o.tolist()]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else round(float(o), 4)
        if isinstance(o, (np.integer,)):
            return int(o)
        return o
    (RES / "resultats_prototype.json").write_text(json.dumps(propre(R), ensure_ascii=False, indent=1), encoding="utf-8")
    journal("terminé")
    return R


if __name__ == "__main__":
    main()
