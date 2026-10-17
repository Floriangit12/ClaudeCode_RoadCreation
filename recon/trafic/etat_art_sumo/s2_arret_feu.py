"""Scénario S2 — approche d'un feu tricolore isolé (1 voie, 50 km/h), cycle fixe 60 s.

Plan de feux : vert 30 s, jaune 3 s (valeur réglementaire en agglomération, CERTU 2010 p. 68),
rouge 27 s. Demande : arrivées de Poisson 720 véh/h (période exp(0,2)) pendant 30 min.

Mesures : (a) décision arrêt/passage à l'apparition du jaune en fonction du temps jusqu'à la
ligne (TTS) ; (b) décélérations utilisées pour s'arrêter ; (c) écoulement de la file au vert
(intervalles par rang, intervalle de saturation, temps perdu au démarrage) ; (d) franchissements
au rouge.

Usage : python s2_arret_feu.py [--graines 8]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C  # noqa: E402
import sumolib  # noqa: E402

DOSSIER = C.RACINE_SORTIE / "S2_arret_feu"
V_LIM = 13.89
CYCLE, VERT, JAUNE = 60.0, 30.0, 3.0
DUREE = 1800.0


def construire():
    C.ecrire(DOSSIER / "s2.nod.xml", """<nodes>
  <node id="A" x="0" y="0" type="priority"/>
  <node id="J" x="600" y="0" type="traffic_light" tl="J"/>
  <node id="B" x="900" y="0" type="priority"/>
</nodes>
""")
    C.ecrire(DOSSIER / "s2.edg.xml", f"""<edges>
  <edge id="AJ" from="A" to="J" numLanes="1" speed="{V_LIM}"/>
  <edge id="JB" from="J" to="B" numLanes="1" speed="{V_LIM}"/>
</edges>
""")
    C.netconvert(DOSSIER, "s2", ["--tls.discard-simple", "false"])
    C.ecrire(DOSSIER / "s2_feux.add.xml", f"""<additional>
  <tlLogic id="J" type="static" programID="fixe60" offset="0">
    <phase duration="{VERT:.0f}" state="G"/>
    <phase duration="{JAUNE:.0f}" state="y"/>
    <phase duration="{CYCLE - VERT - JAUNE:.0f}" state="r"/>
  </tlLogic>
</additional>
""")


def routes(cfg_id: str) -> Path:
    cf = C.CONFIGS[cfg_id]["cf"]
    p = DOSSIER / f"s2_{cfg_id}.rou.xml"
    C.ecrire(p, f"""<routes>
  <vType id="vp" vClass="passenger" carFollowModel="{cf}"/>
  <flow id="f" type="vp" begin="0" end="{DUREE:.0f}" period="exp(0.2)" from="AJ" to="JB" departSpeed="max" departLane="best"/>
</routes>
""")
    return p


def simuler(cfg_id: str, graine: int) -> Path:
    step = C.CONFIGS[cfg_id]["step"]
    fcd = C.RACINE_BRUT / DOSSIER.name / f"fcd_{cfg_id}_g{graine}.xml.gz"
    fcd.parent.mkdir(parents=True, exist_ok=True)
    C.lancer_sumo(["-n", str(DOSSIER / "s2.net.xml"), "-r", str(routes(cfg_id)), "-a", str(DOSSIER / "s2_feux.add.xml"),
                   "--step-length", str(step), "--seed", str(graine), "--no-step-log", "true",
                   "--end", str(DUREE + 180), "--fcd-output", str(fcd),
                   "--fcd-output.attributes", "lane,pos,speed,acceleration",
                   "--collision.action", "warn", "--tls.all-off", "false"],
                  C.RACINE_BRUT / DOSSIER.name / f"log_{cfg_id}_g{graine}.txt")
    return fcd


def trajectoires(fcd: Path, L_app: float, L_int: float, step: float):
    """Retourne {id: dict(t, s, v, a)} avec s = abscisse depuis le début de l'approche ; ligne d'arrêt en s = L_app.

    Convention SUMO : l'état écrit au pas étiqueté t est celui APRÈS le mouvement du pas [t, t+Δ]
    (le feu lu pendant ce mouvement est celui de l'instant t). On recale donc t_phys = t + Δ.
    """
    tr = defaultdict(lambda: {"t": [], "s": [], "v": [], "a": []})
    for (t, vid, lane, pos, v, a) in C.lire_fcd(fcd):
        if lane.startswith("AJ_"):
            s = pos
        elif lane.startswith(":J"):
            s = L_app + pos
        elif lane.startswith("JB_"):
            s = L_app + L_int + pos
        else:
            continue
        d = tr[vid]
        d["t"].append(t + step); d["s"].append(s); d["v"].append(v); d["a"].append(a)
    return {k: {kk: np.asarray(vv) for kk, vv in d.items()} for k, d in tr.items()}


def t_franchissement(d, s_ligne):
    i = np.searchsorted(d["s"], s_ligne)  # s croissant
    if i == 0 or i >= len(d["s"]):
        return np.nan
    s0, s1, t0, t1 = d["s"][i - 1], d["s"][i], d["t"][i - 1], d["t"][i]
    return float(t0 + (t1 - t0) * (s_ligne - s0) / max(s1 - s0, 1e-9))


def etat_a(d, t):
    i = np.searchsorted(d["t"], t)
    if i >= len(d["t"]) or i == 0 and d["t"][0] > t:
        return None
    return d["s"][i], d["v"][i], d["a"][i]


def analyser_run(tr, L_app):
    dec, decel_arret, profils, h_par_rang, rouge = [], [], [], defaultdict(list), 0
    tc = {k: t_franchissement(d, L_app) for k, d in tr.items()}
    n_cycles = int(DUREE // CYCLE) + 2
    for kc in range(n_cycles):
        ty = kc * CYCLE + VERT
        tr_ = ty + JAUNE
        tg_suiv = (kc + 1) * CYCLE
        # --- (a) décisions au jaune : véhicules sur l'approche, triés du plus proche au plus loin
        cand = []
        for vid, d in tr.items():
            if d["t"][0] > ty or d["t"][-1] < ty:
                continue
            e = etat_a(d, ty)
            if e is None:
                continue
            s, v, a = e
            dist = L_app - s
            if 0 < dist <= 150 and v > 5.0:
                cand.append((dist, v, vid))
        cand.sort()
        for dist, v, vid in cand:
            t_c = tc[vid]
            d = tr[vid]
            # arrêt = le véhicule s'est immobilisé (v < 0,1 m/s) avant la ligne entre le jaune et son franchissement
            # (critère robuste au décalage d'un pas entre changement de feu et sortie FCD)
            fin = t_c if t_c == t_c else d["t"][-1]
            m_av = (d["t"] >= ty) & (d["t"] <= fin) & (d["s"] < L_app)
            arret = bool((d["v"][m_av] < 0.1).any()) or not (t_c == t_c)
            if not arret and t_c > tr_ + 1e-6:
                rouge += 1
            dec.append({"dist": dist, "v": v, "tts": dist / v, "arret": arret})
            if arret:
                m = (d["t"] >= ty) & (d["t"] <= ty + 25)
                if m.any():
                    decel_arret.append(float(-d["a"][m].min()))
                    if len(profils) < 40:
                        profils.append((d["t"][m] - ty, d["a"][m], d["v"][m]))
                break  # les suivants sont contraints par celui qui s'arrête
        # --- (c) écoulement de la file au vert suivant
        file_ = []
        for vid, d in tr.items():
            t_c = tc[vid]
            if not (tg_suiv - 1e-6 <= t_c < tg_suiv + VERT):
                continue
            m = (d["t"] >= tr_) & (d["t"] <= tg_suiv) & (d["v"] < 0.5)
            if m.any():
                file_.append(t_c)
        file_.sort()
        prev = tg_suiv
        for rang, t_c in enumerate(file_, start=1):
            h_par_rang[rang].append(t_c - prev)
            prev = t_c
    return dec, decel_arret, profils, h_par_rang, rouge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graines", type=int, default=8)
    a = ap.parse_args()
    (DOSSIER / "resultats").mkdir(parents=True, exist_ok=True)
    construire()
    net = sumolib.net.readNet(str(DOSSIER / "s2.net.xml"), withInternal=True)
    L_app = net.getLane("AJ_0").getLength()
    L_int = net.getLane(":J_0_0").getLength()
    resume, brut = {}, {}
    for cfg_id in C.CONFIGS:
        decs, decels, profs, h_all, rouge = [], [], [], defaultdict(list), 0
        for g in range(a.graines):
            fcd = simuler(cfg_id, g)
            tr = trajectoires(fcd, L_app, L_int, C.CONFIGS[cfg_id]["step"])
            d1, d2, p, h, r = analyser_run(tr, L_app)
            decs += d1; decels += d2; rouge += r
            if g == 0:
                profs = p
            for k, v in h.items():
                h_all[k] += v
        h_moy = {k: C.percentiles(v, ps=(50,)) for k, v in sorted(h_all.items()) if k <= 12}
        h_sat = [x for k, v in h_all.items() if 5 <= k <= 12 for x in v]
        h_sat_m = float(np.mean(h_sat)) if h_sat else np.nan
        perdu = sum((np.mean(h_all[k]) - h_sat_m) for k in range(1, 5) if h_all.get(k))
        tts = np.array([x["tts"] for x in decs]); arr = np.array([x["arret"] for x in decs])
        bins = np.arange(0, 11.5, 0.5)
        p_arret = []
        for b0, b1 in zip(bins[:-1], bins[1:]):
            m = (tts >= b0) & (tts < b1)
            p_arret.append({"tts_min": float(b0), "tts_max": float(b1), "n": int(m.sum()), "p_arret": round(float(arr[m].mean()), 3) if m.sum() else None})
        # seuil de bascule observé
        go_max = float(tts[~arr].max()) if (~arr).any() else None
        stop_min = float(tts[arr].min()) if arr.any() else None
        resume[cfg_id] = {
            "config": C.CONFIGS[cfg_id], "graines": a.graines,
            "decisions_jaune_n": len(decs), "franchissements_au_rouge": rouge,
            "p_arret_par_tts": p_arret,
            "tts_max_passage_s": go_max, "tts_min_arret_s": stop_min,
            "decel_max_premier_arret_ms2": C.percentiles(decels),
            "intervalle_decharge_par_rang_s": h_moy,
            "intervalle_saturation_rangs5_12_s": round(h_sat_m, 3),
            "debit_saturation_veh_h": round(3600.0 / h_sat_m, 0) if h_sat_m == h_sat_m else None,
            "temps_perdu_demarrage_rangs1_4_s": round(float(perdu), 2),
        }
        brut[cfg_id] = {"decs": decs, "profils": profs, "h": h_all}
        print(cfg_id, "decisions", len(decs), "hsat", round(h_sat_m, 2), "perdu", round(float(perdu), 2), "rouge", rouge)
    graphes(resume, brut)
    C.json_ecrire(DOSSIER / "resultats" / "S2_resume.json", {
        "scenario": __doc__.strip().splitlines()[0], "resultats": resume,
        "references": {k: C.REFERENCES[k] for k in ("saturation_fr", "jaune_fr", "temps_perdu_demarrage", "zone_indecision", "chang_85pc", "decel_ite_jaune", "decel_cerema_arret")}})


def graphes(resume, brut):
    plt = C.style_graphes()
    # --- Figure jaune : P(arrêt) vs TTS + nuage (v, d)
    fig, axes = plt.subplots(2, 1, figsize=(10, 9.5))
    ax = axes[0]
    ax.axvspan(2.5, 5.5, color="grey", alpha=0.18, label="zone d'indécision réelle 10 %→90 % d'arrêt (FHWA 2008 p. 4-25)")
    ax.plot([2.5, 5.5], [0.1, 0.9], "s", color="black", ms=7, label="repères 10 % / 90 % (FHWA 2008)")
    ax.plot([3.0], [0.85], "D", color="black", ms=7, mfc="white", label="Chang et al. : 85 % d'arrêt si TTS > 3 s (cité FHWA)")
    for cfg_id, r in resume.items():
        x = [(b["tts_min"] + b["tts_max"]) / 2 for b in r["p_arret_par_tts"] if b["n"] >= 3]
        y = [b["p_arret"] for b in r["p_arret_par_tts"] if b["n"] >= 3]
        ax.plot(x, y, "o-", color=C.COULEURS[cfg_id], label=C.CONFIGS[cfg_id]["libelle"])
    ax.set_xlabel("temps jusqu'à la ligne d'arrêt à l'apparition du jaune, TTS = d / v (s)")
    ax.set_ylabel("probabilité d'arrêt")
    ax.set_title("Décision au jaune (premier véhicule libre de décider), jaune = 3 s")
    ax.set_xlim(0, 11)
    ax.legend(fontsize=7, loc="lower right")
    ax = axes[1]
    vv = np.linspace(5, 17, 50)
    for cfg_id, b in brut.items():
        d = b["decs"]
        st = [x for x in d if x["arret"]]; go = [x for x in d if not x["arret"]]
        ax.scatter([x["v"] for x in st], [x["dist"] for x in st], s=10, marker="o", color=C.COULEURS[cfg_id], alpha=0.5, label=f"{cfg_id} : arrêt")
        ax.scatter([x["v"] for x in go], [x["dist"] for x in go], s=14, marker="x", color=C.COULEURS[cfg_id], alpha=0.7, label=f"{cfg_id} : passage")
    ax.plot(vv, vv ** 2 / (2 * 4.5), "k--", lw=1, label="d = v²/(2·4,5) : seuil SUMO (decel défaut)")
    ax.plot(vv, vv * 1.0 + vv ** 2 / (2 * 3.05), "k:", lw=1, label="d = v·1 s + v²/(2·3,05) : critère ITE (FHWA p. 5-13)")
    ax.set_xlabel("vitesse à l'apparition du jaune (m/s)")
    ax.set_ylabel("distance à la ligne (m)")
    ax.set_ylim(0, 80)
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    fig.tight_layout(); fig.savefig(DOSSIER / "resultats" / "S2_decision_jaune.png"); plt.close(fig)
    # --- Figure écoulement + freinage
    fig, axes = plt.subplots(2, 1, figsize=(10, 9.5))
    ax = axes[0]
    for cfg_id, r in resume.items():
        h = r["intervalle_decharge_par_rang_s"]
        ks = [int(k) for k in h if h[k]["n"] >= 5]
        ax.plot(ks, [h[k]["moyenne"] for k in ks], "o-", color=C.COULEURS[cfg_id], label=f"{C.CONFIGS[cfg_id]['libelle']} : h_sat = {r['intervalle_saturation_rangs5_12_s']:.2f} s, perdu = {r['temps_perdu_demarrage_rangs1_4_s']:.1f} s")
    ax.axhline(2.0, color="black", ls="--", lw=1, label="1 800 uvpd/h/voie ⇒ 2,0 s (CERTU feux 2010 p. 34)")
    ax.set_xlabel("rang dans la file au début du vert")
    ax.set_ylabel("intervalle de passage à la ligne (s)")
    ax.set_title("Écoulement de la file au vert (rang 1 : temps depuis le début du vert)\ntemps perdu au démarrage usuel ≈ 2 s (FHWA 2008 p. 3-5)", fontsize=10)
    ax.legend(fontsize=7)
    ax = axes[1]
    for cfg_id, b in brut.items():
        for i, (t, acc, v) in enumerate(b["profils"][:15]):
            ax.plot(t, acc, color=C.COULEURS[cfg_id], lw=0.8, alpha=0.7, label=C.CONFIGS[cfg_id]["libelle"] if i == 0 else None)
    ax.axhline(-3.05, color="black", ls=":", lw=1, label="10 ft/s² = 3,05 m/s² (ITE, cité FHWA p. 5-13)")
    ax.axhline(-4.5, color="red", ls="--", lw=0.8, label="decel SUMO par défaut 4,5 m/s²")
    ax.set_xlim(0, 15)
    ax.set_xlabel("temps depuis l'apparition du jaune (s)")
    ax.set_ylabel("accélération (m/s²)")
    ax.set_title("Profils de freinage des premiers véhicules qui s'arrêtent (graine 0)")
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(DOSSIER / "resultats" / "S2_decharge_freinage.png"); plt.close(fig)


if __name__ == "__main__":
    main()
