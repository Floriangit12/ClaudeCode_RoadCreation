"""Scénario S1 — file de 10 véhicules sur route droite (50 km/h), meneur piloté.

Le meneur suit un profil imposé (TraCI, speedMode 0) : démarrage, croisière 50 km/h,
ralentissement à 30 km/h, reprise, freinage fort (4 m/s²) jusqu'à l'arrêt, redémarrage.
Les 9 suiveurs utilisent le modèle testé avec ses paramètres par défaut (sauf speedFactor
fixé à 1,2 sans dispersion pour qu'ils restent contraints par le meneur — choix de test).

Mesures : temps inter-véhiculaires en croisière, bruit de vitesse, accélérations et jerks,
décélération maximale par rang pendant le freinage fort (stabilité de file), retards de
démarrage, distances à l'arrêt.

Usage : python s1_file_route_droite.py [--graines 5]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C  # noqa: E402

import traci  # noqa: E402  (SUMO_HOME/tools ajouté par commun)

DOSSIER = C.RACINE_SORTIE / "S1_file_route_droite"
V_LIM = 13.89
N_SUIV = 9
X0_MENEUR = 300.0
PROFIL = [(0.0, 0.0, 0.0), (2.0, V_LIM, 1.5), (60.0, 8.33, 1.5), (90.0, V_LIM, 1.5), (130.0, 0.0, 4.0),
          (145.0, V_LIM, 1.5)]
T_FIN = 200.0
FENETRES_CROISIERE = [(45.0, 60.0), (115.0, 130.0)]
FENETRE_FREINAGE = (129.0, 150.0)


def construire():
    C.ecrire(DOSSIER / "s1.nod.xml", """<nodes>
  <node id="A" x="0" y="0" type="priority"/>
  <node id="B" x="4000" y="0" type="priority"/>
</nodes>
""")
    C.ecrire(DOSSIER / "s1.edg.xml", f"""<edges>
  <edge id="AB" from="A" to="B" numLanes="1" speed="{V_LIM}"/>
</edges>
""")
    C.netconvert(DOSSIER, "s1")


def routes(cfg_id: str) -> Path:
    cf = C.CONFIGS[cfg_id]["cf"]
    lignes = ['<routes>',
              '  <vType id="meneur" vClass="passenger" carFollowModel="Krauss" sigma="0" accel="5" decel="9" emergencyDecel="9" speedFactor="1" speedDev="0" color="0,0,0"/>',
              f'  <vType id="suiveur" vClass="passenger" carFollowModel="{cf}" speedFactor="1.2" speedDev="0"/>',
              '  <route id="r" edges="AB"/>',
              f'  <vehicle id="v00" type="meneur" route="r" depart="0" departPos="{X0_MENEUR}" departSpeed="0"/>']
    for k in range(1, N_SUIV + 1):
        lignes.append(f'  <vehicle id="v{k:02d}" type="suiveur" route="r" depart="0" departPos="{X0_MENEUR - 7.5 * k:.1f}" departSpeed="0"/>')
    lignes.append('</routes>')
    p = DOSSIER / f"s1_{cfg_id}.rou.xml"
    C.ecrire(p, "\n".join(lignes) + "\n")
    return p


def vitesse_cible(t: float, v: float, dt: float) -> float:
    cible, taux = 0.0, 0.0
    for (t0, vc, a) in PROFIL:
        if t >= t0:
            cible, taux = vc, a
    if v < cible:
        return min(cible, v + taux * dt)
    if v > cible:
        return max(cible, v - taux * dt)
    return v


def simuler(cfg_id: str, graine: int) -> dict:
    step = C.CONFIGS[cfg_id]["step"]
    rou = routes(cfg_id)
    cmd = ["sumo", "-n", str(DOSSIER / "s1.net.xml"), "-r", str(rou), "--step-length", str(step),
           "--seed", str(graine), "--no-step-log", "true", "--collision.action", "warn",
           "--collision.check-junctions", "true", "--end", str(T_FIN)]
    traci.start(cmd, label=f"s1_{cfg_id}_{graine}")
    con = traci.getConnection(f"s1_{cfg_id}_{graine}")
    ids = [f"v{k:02d}" for k in range(N_SUIV + 1)]
    rec = {i: {"t": [], "x": [], "v": [], "a": []} for i in ids}
    v_meneur = 0.0
    collisions = 0
    try:
        con.simulationStep()  # insertion
        con.vehicle.setSpeedMode("v00", 0)
        while con.simulation.getTime() < T_FIN:
            t = con.simulation.getTime()
            v_meneur = vitesse_cible(t, v_meneur, step)
            con.vehicle.setSpeed("v00", v_meneur)
            con.simulationStep()
            collisions += con.simulation.getCollidingVehiclesNumber()
            tt = con.simulation.getTime()
            presents = set(con.vehicle.getIDList())
            for i in ids:
                if i in presents:
                    rec[i]["t"].append(tt)
                    rec[i]["x"].append(con.vehicle.getLanePosition(i))
                    rec[i]["v"].append(con.vehicle.getSpeed(i))
                    rec[i]["a"].append(con.vehicle.getAcceleration(i))
    finally:
        con.close()
    out = {i: {k: np.asarray(vv) for k, vv in d.items()} for i, d in rec.items()}
    out["_collisions"] = collisions
    return out


def analyser(cfg_id: str, runs: list[dict]) -> dict:
    step = C.CONFIGS[cfg_id]["step"]
    tg, gaps_arret, sd_v, jerks, accs = [], [], [], [], []
    sd_rang = {k: [] for k in range(1, N_SUIV + 1)}
    dec_max_rang = {k: [] for k in range(N_SUIV + 1)}
    retard_rang = {k: [] for k in range(1, N_SUIV + 1)}
    retard_rang_initial = {k: [] for k in range(1, N_SUIV + 1)}
    n_urg = 0
    collisions = 0
    for run in runs:
        collisions += run["_collisions"]
        for k in range(1, N_SUIV + 1):
            me, pr = run[f"v{k:02d}"], run[f"v{k - 1:02d}"]
            n = min(len(me["t"]), len(pr["t"]))
            t, x, v, a = me["t"][:n], me["x"][:n], me["v"][:n], me["a"][:n]
            gap = pr["x"][:n] - 5.0 - x
            for (t0, t1) in FENETRES_CROISIERE:
                m = (t >= t0) & (t < t1) & (v > 1.0)
                tg += list(gap[m] / v[m])
                sd_v.append(float(np.std(v[(t >= t0) & (t < t1)])))
                sd_rang[k].append(sd_v[-1])
            m_arr = (t > 140.0) & (t < 144.5) & (v < 0.01)
            if m_arr.any():
                gaps_arret.append(float(np.median(gap[m_arr])))
            # jerk sur tout le parcours (hors première seconde)
            j = np.diff(a) / step
            jerks += list(np.abs(j[t[1:] > 1.0]))
            accs += list(a)
            mf = (t >= FENETRE_FREINAGE[0]) & (t <= FENETRE_FREINAGE[1])
            dec_max_rang[k].append(float(-a[mf].min()))
            n_urg += int(np.sum(a < -4.5 - 1e-6))
            # retards de démarrage : redémarrage après l'arrêt (t>=145) et départ initial (t>=2)
            # Un retard n'est compté que si le véhicule ET son prédécesseur se sont réellement
            # arrêtés (v < 0,1 m/s) dans la fenêtre ; sinon NaN (les derniers de file peuvent ne pas s'arrêter).
            for (tdeb, tfin_arret, dico) in ((145.0, 165.0, retard_rang), (0.0, 3.0, retard_rang_initial)):
                def t_dep(tt, vv):
                    arr = (tt >= FENETRE_FREINAGE[0] if tdeb > 0 else tt >= 0) & (tt <= tfin_arret) & (vv < 0.1)
                    if not arr.any():
                        return np.nan
                    t_arr = float(tt[arr][0])
                    mm = (tt >= max(t_arr, tdeb)) & (vv > 0.5)
                    return float(tt[mm][0]) if mm.any() else np.nan
                dico[k].append(t_dep(t, v) - t_dep(pr["t"][:n], pr["v"][:n]))
        mene = run["v00"]
        mf = (mene["t"] >= FENETRE_FREINAGE[0]) & (mene["t"] <= FENETRE_FREINAGE[1])
        dec_max_rang[0].append(float(-mene["a"][mf].min()))
    return {
        "config": C.CONFIGS[cfg_id],
        "graines": len(runs),
        "collisions": collisions,
        "temps_inter_net_croisiere_s": C.percentiles(tg),
        "ecart_type_vitesse_croisiere_ms": C.percentiles(sd_v),
        "ecart_type_vitesse_croisiere_par_rang_ms": {k: C.percentiles(v, ps=(50,)) for k, v in sd_rang.items()},
        "jerk_abs_ms3": C.percentiles(jerks, ps=(50, 90, 95, 99)),
        "part_pas_jerk_sup_1.5": round(float(np.mean(np.asarray(jerks) > 1.5)), 4) if jerks else None,
        "acceleration_ms2": C.percentiles(accs, ps=(1, 5, 50, 95, 99)),
        "pas_decel_sup_decel_4.5": n_urg,
        "decel_max_freinage_fort_par_rang": {k: C.percentiles(v, ps=(50,)) for k, v in dec_max_rang.items()},
        "retard_redemarrage_vs_predecesseur_s": {k: C.percentiles(v, ps=(50,)) for k, v in retard_rang.items()},
        "retard_depart_initial_vs_predecesseur_s": {k: C.percentiles(v, ps=(50,)) for k, v in retard_rang_initial.items()},
        "distance_arret_m": C.percentiles(gaps_arret),
    }


def graphes(runs0: dict, resume: dict):
    plt = C.style_graphes()
    cmap = plt.get_cmap("viridis")
    # Figure 1 : vitesses ; Figure 2 : accélérations (graine 0, 3 configurations)
    for grandeur, fic, ylab in (("v", "S1_vitesses.png", "vitesse (m/s)"), ("a", "S1_accelerations.png", "accélération (m/s²)")):
        fig, axes = plt.subplots(3, 1, figsize=(10, 9.5), sharex=True)
        for ax, cfg_id in zip(axes, C.CONFIGS):
            run = runs0[cfg_id]
            ax.plot(run["v00"]["t"], run["v00"][grandeur], color="black", lw=2.0, label="meneur (profil imposé)")
            for k in range(1, N_SUIV + 1):
                d = run[f"v{k:02d}"]
                ax.plot(d["t"], d[grandeur], color=cmap(k / (N_SUIV + 1)), lw=1.0, label=f"suiveur {k}" if k in (1, 5, 9) else None)
            ax.set_title(C.CONFIGS[cfg_id]["libelle"] + " — graine 0")
            ax.set_ylabel(ylab)
            if grandeur == "a":
                ax.axhline(-4.5, color="red", ls="--", lw=0.8)
                ax.text(1, -4.4, "decel = 4,5 (défaut)", color="red", fontsize=8)
                ax.set_ylim(-9.5, 4)
            ax.legend(loc="upper right", fontsize=8, ncol=4)
        axes[-1].set_xlabel("temps (s)")
        fig.tight_layout()
        fig.savefig(DOSSIER / "resultats" / fic)
        plt.close(fig)
    # Figure 3 : synthèse (4 panneaux)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8.5))
    rangs = list(range(1, N_SUIV + 1))
    ax = axes[0, 0]
    for cfg_id in C.CONFIGS:
        r = resume[cfg_id]["decel_max_freinage_fort_par_rang"]
        ax.plot([0] + rangs, [r[0]["p50"]] + [r[k]["p50"] for k in rangs], "o-", color=C.COULEURS[cfg_id], label=C.CONFIGS[cfg_id]["libelle"])
    ax.set_xlabel("rang dans la file (0 = meneur)")
    ax.set_ylabel("décélération max (m/s², médiane graines)")
    ax.set_title("Freinage fort du meneur (4 m/s²)")
    ax.legend(fontsize=7)
    ax = axes[0, 1]
    for cfg_id in C.CONFIGS:
        r = resume[cfg_id]["retard_redemarrage_vs_predecesseur_s"]
        ax.plot(rangs, [r[k]["p50"] for k in rangs], "o-", color=C.COULEURS[cfg_id])
    ax.set_xlabel("rang dans la file")
    ax.set_ylabel("retard de démarrage / prédécesseur (s)")
    ax.set_title("Redémarrage après arrêt (seuil v > 0,5 m/s)")
    ax = axes[1, 0]
    data = []
    labels = []
    for cfg_id in C.CONFIGS:
        data.append(np.asarray(resume[cfg_id]["_tg"]))
        labels.append(cfg_id)
    ax.boxplot(data, whis=(5, 95), showfliers=False)
    ax.set_xticks(range(1, len(labels) + 1), labels, fontsize=8)
    ref = C.REFERENCES["temps_inter_idm_shanghai"]["valeur"]
    ax.axhspan(ref["p5"], ref["p95"], color="grey", alpha=0.2, label="T IDM calé SH-NDS p5–p95 (Zhu 2018)")
    ax.axhspan(1.03, 1.51, color="tab:blue", alpha=0.12, label="T IDM calé Stuttgart (Kesting 2008)")
    ax.set_ylabel("temps inter-véhiculaire net (s)")
    ax.set_title("Croisière 50 km/h (boîtes p5–p95)")
    ax.legend(fontsize=7, loc="upper right")
    ax = axes[1, 1]
    for cfg_id in C.CONFIGS:
        j = np.sort(np.asarray(resume[cfg_id]["_jerk"]))
        if j.size:
            ax.plot(j, 1 - np.arange(j.size) / j.size, color=C.COULEURS[cfg_id], label=cfg_id)
    ax.set_xscale("symlog", linthresh=0.1)
    ax.set_yscale("log")
    ax.axvline(1.5, color="black", ls="--", lw=0.8)
    ax.text(1.6, 0.5, "1,5 m/s³", fontsize=8)
    ax.set_xlabel("|jerk| (m/s³)")
    ax.set_ylabel("fraction des pas > x")
    ax.set_title("Distribution des jerks (tous suiveurs)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(DOSSIER / "resultats" / "S1_synthese.png")
    plt.close(fig)
    # Figure 4 : croissance des fluctuations de vitesse le long de la file (comparaison Jiang et al. 2014)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for cfg_id in C.CONFIGS:
        r = resume[cfg_id]["ecart_type_vitesse_croisiere_par_rang_ms"]
        ax.plot(rangs, [r[k]["p50"] for k in rangs], "o-", color=C.COULEURS[cfg_id], label=C.CONFIGS[cfg_id]["libelle"] + " (meneur à vitesse parfaitement constante)")
    ref = C.REFERENCES["jiang_sv_50kmh"]["valeur"]
    ax.errorbar([1, 9, 22], [ref["rang_1"], ref["rang_9"], ref["rangs_20_25"]], yerr=0.1, fmt="s", color="black", capsize=4,
                label="mesure, file de 25 voitures à 50 km/h (Jiang et al. 2014, fig. 5D, lecture ±0,1)")
    ax.set_xlabel("rang du suiveur dans la file")
    ax.set_ylabel("écart-type de la vitesse en croisière (m/s)")
    ax.set_title("Croissance des fluctuations le long de la file (médiane des graines)")
    ax.set_xlim(0, 25)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(DOSSIER / "resultats" / "S1_fluctuations_par_rang.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graines", type=int, default=5)
    a = ap.parse_args()
    (DOSSIER / "resultats").mkdir(parents=True, exist_ok=True)
    construire()
    resume, runs0 = {}, {}
    for cfg_id in C.CONFIGS:
        runs = [simuler(cfg_id, g) for g in range(a.graines)]
        runs0[cfg_id] = runs[0]
        resume[cfg_id] = analyser(cfg_id, runs)
        # séries brutes pour graphes de synthèse
        step = C.CONFIGS[cfg_id]["step"]
        tg, jk = [], []
        for run in runs:
            for k in range(1, N_SUIV + 1):
                me, pr = run[f"v{k:02d}"], run[f"v{k - 1:02d}"]
                n = min(len(me["t"]), len(pr["t"]))
                t, x, v = me["t"][:n], me["x"][:n], me["v"][:n]
                gap = pr["x"][:n] - 5.0 - x
                for (t0, t1) in FENETRES_CROISIERE:
                    m = (t >= t0) & (t < t1) & (v > 1.0)
                    tg += list(gap[m] / v[m])
                j = np.abs(np.diff(me["a"][:n]) / step)
                jk += list(j[t[1:] > 1.0])
        resume[cfg_id]["_tg"] = tg
        resume[cfg_id]["_jerk"] = jk
        print(cfg_id, "ok", resume[cfg_id]["temps_inter_net_croisiere_s"])
    graphes(runs0, resume)
    for cfg_id in resume:
        resume[cfg_id].pop("_tg")
        resume[cfg_id].pop("_jerk")
    C.json_ecrire(DOSSIER / "resultats" / "S1_resume.json", {"scenario": __doc__.strip().splitlines()[0], "resultats": resume,
                                                            "references": {k: C.REFERENCES[k] for k in ("temps_inter_idm_shanghai", "temps_inter_idm_stuttgart", "demarrage_salles", "jiang_sv_50kmh")}})


if __name__ == "__main__":
    main()
