"""Scénario S3 — insertion en tourne-à-droite depuis une voie secondaire (carrefour en T, 50 km/h).

Voie principale O-E à double sens (1 voie/sens), arrivées de Poisson 600 véh/h par sens.
Voie secondaire S (cédez-le-passage, noeud « priority » ; variante STOP, noeud « priority_stop »),
arrivées de Poisson 180 véh/h, toutes en tourne-à-droite vers E (fusion dans le flux venant d'O).

Mesures : créneaux (intervalles entre passages successifs des véhicules prioritaires à l'entrée
du carrefour) refusés et acceptés par chaque conducteur non prioritaire ; estimation du créneau
critique par maximum de vraisemblance (loi log-normale, méthode de Troutbeck) ; effet de
l'attente (impatience) ; temps d'arrêt au STOP ; freinage imposé au prioritaire après fusion.

Usage : python s3_insertion_cedez.py [--graines 6]
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

DOSSIER = C.RACINE_SORTIE / "S3_insertion_cedez"
V_LIM = 13.89
DUREE = 2400.0
VARIANTES = {"cedez": "priority", "stop": "priority_stop"}
REUTILISER = False  # --reutiliser : relit les sorties FCD existantes (régénère analyses et graphes)


def construire(variante: str):
    nom = f"s3_{variante}"
    C.ecrire(DOSSIER / f"{nom}.nod.xml", f"""<nodes>
  <node id="W" x="-400" y="0" type="priority"/>
  <node id="J" x="0" y="0" type="{VARIANTES[variante]}"/>
  <node id="E" x="400" y="0" type="priority"/>
  <node id="S" x="0" y="-200" type="priority"/>
</nodes>
""")
    C.ecrire(DOSSIER / f"{nom}.edg.xml", f"""<edges>
  <edge id="WJ" from="W" to="J" numLanes="1" speed="{V_LIM}" priority="2"/>
  <edge id="JE" from="J" to="E" numLanes="1" speed="{V_LIM}" priority="2"/>
  <edge id="EJ" from="E" to="J" numLanes="1" speed="{V_LIM}" priority="2"/>
  <edge id="JW" from="J" to="W" numLanes="1" speed="{V_LIM}" priority="2"/>
  <edge id="SJ" from="S" to="J" numLanes="1" speed="{V_LIM}" priority="1"/>
</edges>
""")
    C.netconvert(DOSSIER, nom)
    C.ecrire(DOSSIER / "s3_filtre_fcd.txt", "edge:WJ\nedge:SJ\nedge:JE\n")


def routes(cfg_id: str) -> Path:
    cf = C.CONFIGS[cfg_id]["cf"]
    p = DOSSIER / f"s3_{cfg_id}.rou.xml"
    C.ecrire(p, f"""<routes>
  <vType id="vp" vClass="passenger" carFollowModel="{cf}"/>
  <flow id="maj_OE" type="vp" begin="0" end="{DUREE:.0f}" period="exp({600/3600:.6f})" from="WJ" to="JE" departSpeed="max"/>
  <flow id="maj_EO" type="vp" begin="0" end="{DUREE:.0f}" period="exp({600/3600:.6f})" from="EJ" to="JW" departSpeed="max"/>
  <flow id="min_SE" type="vp" begin="0" end="{DUREE:.0f}" period="exp({180/3600:.6f})" from="SJ" to="JE" departSpeed="max"/>
</routes>
""")
    return p


def simuler(variante: str, cfg_id: str, graine: int) -> Path:
    step = C.CONFIGS[cfg_id]["step"]
    fcd = C.RACINE_BRUT / DOSSIER.name / f"fcd_{variante}_{cfg_id}_g{graine}.xml.gz"
    fcd.parent.mkdir(parents=True, exist_ok=True)
    if REUTILISER and fcd.exists():
        return fcd
    C.lancer_sumo(["-n", str(DOSSIER / f"s3_{variante}.net.xml"), "-r", str(routes(cfg_id)),
                   "--step-length", str(step), "--seed", str(graine), "--no-step-log", "true",
                   "--end", str(DUREE + 300), "--fcd-output", str(fcd),
                   "--fcd-output.attributes", "lane,pos,speed,acceleration",
                   "--fcd-output.filter-edges.input-file", str(DOSSIER / "s3_filtre_fcd.txt"),
                   "--collision.action", "warn", "--collision.check-junctions", "true"],
                  C.RACINE_BRUT / DOSSIER.name / f"log_{variante}_{cfg_id}_g{graine}.txt")
    return fcd


def lire(fcd: Path, step: float):
    tr = defaultdict(lambda: defaultdict(lambda: {"t": [], "s": [], "v": [], "a": []}))
    for (t, vid, lane, pos, v, a) in C.lire_fcd(fcd):
        e = lane.rsplit("_", 1)[0]
        d = tr[vid][e]
        d["t"].append(t + step); d["s"].append(pos); d["v"].append(v); d["a"].append(a)  # recalage SUMO t+Δ
    return {k: {e: {kk: np.asarray(vv) for kk, vv in d.items()} for e, d in ed.items()} for k, ed in tr.items()}


def t_fin_voie(d, L):
    """Instant (interpolé/extrapolé) où l'avant du véhicule atteint la fin de voie s = L."""
    s, t, v = d["s"], d["t"], d["v"]
    i = np.searchsorted(s, L)
    if 0 < i < len(s):
        return float(t[i - 1] + (t[i] - t[i - 1]) * (L - s[i - 1]) / max(s[i] - s[i - 1], 1e-9))
    if i >= len(s) and len(s):
        return float(t[-1] + max(L - s[-1], 0.0) / max(v[-1], 0.5))
    return np.nan


def mle_lognormale(acc, rej):
    """Créneau critique : maximum de vraisemblance (Troutbeck 1992) avec loi log-normale.
    acc[i] = créneau accepté, rej[i] = plus grand créneau refusé (0 si aucun). Retourne (moyenne, écart-type)."""
    from scipy import optimize, stats
    a = np.asarray(acc); r = np.asarray(rej)
    m = a > r + 1e-6
    a, r = a[m], r[m]
    if a.size < 10:
        return None

    def nll(p):
        mu, ls = p
        sg = np.exp(ls)
        Fa = stats.norm.cdf((np.log(a) - mu) / sg)
        Fr = np.where(r > 0, stats.norm.cdf((np.log(np.maximum(r, 1e-9)) - mu) / sg), 0.0)
        return -np.sum(np.log(np.maximum(Fa - Fr, 1e-300)))

    x0 = [np.log(np.median(a)), np.log(0.3)]
    res = optimize.minimize(nll, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
    mu, sg = res.x[0], np.exp(res.x[1])
    moy = float(np.exp(mu + sg ** 2 / 2)); et = float(moy * np.sqrt(np.exp(sg ** 2) - 1))
    return {"moyenne_s": round(moy, 3), "ecart_type_s": round(et, 3), "mu_log": round(float(mu), 4), "sigma_log": round(float(sg), 4), "n_conducteurs": int(a.size)}


def analyser(tr, L_maj, L_min):
    passages = []
    for vid, ed in tr.items():
        if vid.startswith("maj_OE") and "WJ" in ed:
            tc = t_fin_voie(ed["WJ"], L_maj)
            if tc == tc:
                passages.append((tc, vid))
    passages.sort()
    P = np.array([p[0] for p in passages])
    ids_P = [p[1] for p in passages]
    out = []
    for vid, ed in tr.items():
        if not vid.startswith("min_SE") or "SJ" not in ed:
            continue
        d = ed["SJ"]
        m3 = (L_min - d["s"]) <= 3.0
        if not m3.any():
            continue
        t_a = float(d["t"][m3][0])
        t_d = t_fin_voie(d, L_min)
        if not (t_d == t_d) or P.size < 2:
            continue
        # arrêt au voisinage de la ligne
        mstop = m3 & (d["v"] < 0.1)
        duree_arret = float(mstop.sum()) * (d["t"][1] - d["t"][0] if len(d["t"]) > 1 else 0.0)
        k = int(np.searchsorted(P, t_a))  # premier prioritaire arrivant après t_a
        if k >= P.size:
            continue
        rejetes = []
        if t_d < P[k]:
            accepte = P[k] - t_a  # décalage (lag) accepté
            type_acc = "lag"
            j_suiv = k
        else:
            rejetes.append(P[k] - t_a)  # lag refusé
            j = k
            while j + 1 < P.size and P[j + 1] <= t_d:
                rejetes.append(P[j + 1] - P[j])
                j += 1
            if j + 1 >= P.size:
                continue
            accepte = P[j + 1] - P[j]
            type_acc = "gap"
            j_suiv = j + 1
        # avance prise sur le prioritaire suivant et freinage imposé à celui-ci
        avance = P[j_suiv] - t_d
        vj = ids_P[j_suiv]
        dec_imp = np.nan
        for e in ("WJ", "JE"):
            if e in tr[vj]:
                dd = tr[vj][e]
                mm = (dd["t"] >= t_d) & (dd["t"] <= t_d + 8.0)
                if mm.any():
                    dec_imp = np.nanmin([dec_imp, float(dd["a"][mm].min())]) if dec_imp == dec_imp else float(dd["a"][mm].min())
        out.append({"t_a": t_a, "attente": t_d - t_a, "accepte": float(accepte), "type": type_acc,
                    "max_rejete": float(max(rejetes)) if rejetes else 0.0, "n_rejetes": len(rejetes),
                    "avance_sur_prioritaire": float(avance), "accel_min_prioritaire_suivant": dec_imp,
                    "duree_arret_ligne": duree_arret, "arret_complet": bool(mstop.any())})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graines", type=int, default=6)
    ap.add_argument("--reutiliser", action="store_true")
    a = ap.parse_args()
    global REUTILISER
    REUTILISER = a.reutiliser
    (DOSSIER / "resultats").mkdir(parents=True, exist_ok=True)
    resume, brut = {}, {}
    for variante in VARIANTES:
        construire(variante)
        net = sumolib.net.readNet(str(DOSSIER / f"s3_{variante}.net.xml"))
        L_maj = net.getLane("WJ_0").getLength(); L_min = net.getLane("SJ_0").getLength()
        for cfg_id in C.CONFIGS:
            rows = []
            for g in range(a.graines):
                fcd = simuler(variante, cfg_id, g)
                rows += analyser(lire(fcd, C.CONFIGS[cfg_id]["step"]), L_maj, L_min)
            acc = [r["accepte"] for r in rows]; rej = [r["max_rejete"] for r in rows]
            gaps_acc = [r["accepte"] for r in rows if r["type"] == "gap"]
            rej_all = [r["max_rejete"] for r in rows if r["n_rejetes"] > 0]
            cle = f"{variante}/{cfg_id}"
            resume[cle] = {
                "config": C.CONFIGS[cfg_id], "variante": variante, "graines": a.graines, "n_conducteurs": len(rows),
                "creneau_accepte_s": C.percentiles(acc), "creneau_accepte_type_gap_s": C.percentiles(gaps_acc),
                "plus_grand_refuse_s": C.percentiles(rej_all),
                "creneau_critique_mle_lognormal": mle_lognormale(acc, rej),
                "arretes_creneau_accepte_s": C.percentiles([r["accepte"] for r in rows if r["arret_complet"]]),
                "arretes_plus_grand_refuse_s": C.percentiles([r["max_rejete"] for r in rows if r["arret_complet"] and r["n_rejetes"] > 0]),
                "arretes_creneau_critique_mle_lognormal": mle_lognormale([r["accepte"] for r in rows if r["arret_complet"]], [r["max_rejete"] for r in rows if r["arret_complet"]]),
                "roulants_lag_accepte_s": C.percentiles([r["accepte"] for r in rows if not r["arret_complet"]]),
                "attente_s": C.percentiles([r["attente"] for r in rows]),
                "avance_sur_prioritaire_s": C.percentiles([r["avance_sur_prioritaire"] for r in rows]),
                "accel_min_prioritaire_suivant_ms2": C.percentiles([r["accel_min_prioritaire_suivant"] for r in rows], ps=(1, 5, 50)),
                "part_prioritaire_freine_sup_2ms2": round(float(np.mean(np.array([r["accel_min_prioritaire_suivant"] for r in rows]) < -2.0)), 3) if rows else None,
                "part_arret_complet": round(float(np.mean([r["arret_complet"] for r in rows])), 3) if rows else None,
                "duree_arret_ligne_s_si_arret": C.percentiles([r["duree_arret_ligne"] for r in rows if r["arret_complet"]]),
            }
            brut[cle] = rows
            import csv
            with open(DOSSIER / "resultats" / f"S3_conducteurs_{variante}_{cfg_id}.csv", "w", newline="", encoding="utf-8") as fcsv:
                w = csv.DictWriter(fcsv, fieldnames=list(rows[0].keys()) if rows else ["vide"])
                w.writeheader(); w.writerows(rows)
            print(cle, len(rows), resume[cle]["creneau_critique_mle_lognormal"])
    graphes(resume, brut)
    C.json_ecrire(DOSSIER / "resultats" / "S3_resume.json", {"scenario": __doc__.strip().splitlines()[0], "resultats": resume,
                                                            "references": {k: C.REFERENCES[k] for k in ("creneau_critique_fr",)}})


def graphes(resume, brut):
    plt = C.style_graphes()
    from scipy import stats
    fig, axes = plt.subplots(2, 1, figsize=(10, 9.5))
    ax = axes[0]
    for cfg_id in C.CONFIGS:
        cle = f"cedez/{cfg_id}"
        rows = brut[cle]
        acc = np.sort([r["accepte"] for r in rows if r["arret_complet"]]); rej = np.sort([r["max_rejete"] for r in rows if r["n_rejetes"] > 0 and r["arret_complet"]])
        col = C.COULEURS[cfg_id]
        if acc.size:
            ax.plot(acc, np.arange(1, acc.size + 1) / acc.size, color=col, lw=1.8, label=f"{C.CONFIGS[cfg_id]['libelle']} : accepté après arrêt (n={acc.size})")
        if rej.size:
            ax.plot(rej, np.arange(1, rej.size + 1) / rej.size, color=col, lw=1.2, ls="--", label="  … plus grand refusé")
        mle = resume[cle]["arretes_creneau_critique_mle_lognormal"]
        if mle:
            x = np.linspace(0.5, 30, 400)
            ax.plot(x, stats.norm.cdf((np.log(x) - mle["mu_log"]) / mle["sigma_log"]), color=col, lw=0.8, ls=":",
                    label=f"  … créneau critique MLE (arrêtés) : {mle['moyenne_s']:.1f} ± {mle['ecart_type_s']:.1f} s")
    ax.axvline(5.0, color="black", lw=1.5, label="créneau critique norme FR, insertion à 50 km/h : 5 s (CERTU 2010 p. 93)")
    ax.set_xlim(0, 30)
    ax.set_xlabel("créneau (s) : lag depuis l'arrivée en ligne ou intervalle entre deux prioritaires")
    ax.set_ylabel("fonction de répartition")
    ax.set_title("Cédez-le-passage, tourne-à-droite, flux prioritaire 600 véh/h — conducteurs arrêtés à la ligne")
    ax.legend(fontsize=7, loc="lower right")
    ax = axes[1]
    for cfg_id in C.CONFIGS:
        rows = brut[f"cedez/{cfg_id}"]
        ax.scatter([r["attente"] for r in rows], [r["accepte"] for r in rows], s=8, alpha=0.5, color=C.COULEURS[cfg_id], label=C.CONFIGS[cfg_id]["libelle"])
    ax.axhline(5.0, color="black", lw=1)
    ax.set_xscale("log")
    ax.set_xlim(0.1, 150)
    ax.set_xlabel("attente à la ligne avant insertion (s, échelle log ; < 1 s = véhicules non arrêtés)")
    ax.set_ylabel("créneau accepté (s)")
    ax.set_title("Créneau accepté selon l'attente (impatience SUMO : croît de 0 à 1 en 180 s)")
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(DOSSIER / "resultats" / "S3_creneaux_cedez.png"); plt.close(fig)
    # Figure 2 : STOP et effets sur le prioritaire
    fig, axes = plt.subplots(2, 1, figsize=(10, 9.5))
    ax = axes[0]
    for cfg_id in C.CONFIGS:
        for var, ls in (("cedez", "-"), ("stop", "--")):
            rows = brut[f"{var}/{cfg_id}"]
            av = np.sort([r["avance_sur_prioritaire"] for r in rows])
            if av.size:
                ax.plot(av, np.arange(1, av.size + 1) / av.size, color=C.COULEURS[cfg_id], ls=ls, label=f"{var} — {C.CONFIGS[cfg_id]['libelle']}")
    ax.set_xlim(0, 15)
    ax.set_xlabel("avance de l'inséré sur le prioritaire suivant à la ligne (s)")
    ax.set_ylabel("fonction de répartition")
    ax.set_title("Temps laissé au prioritaire suivant après insertion")
    ax.legend(fontsize=7, ncol=2)
    ax = axes[1]
    data, labels = [], []
    for cfg_id in C.CONFIGS:
        rows = brut[f"stop/{cfg_id}"]
        data.append([r["duree_arret_ligne"] for r in rows if r["arret_complet"]] or [0.0])
        labels.append(cfg_id)
    ax.boxplot(data, whis=(5, 95), showfliers=True)
    ax.set_xticks(range(1, len(labels) + 1), labels, fontsize=8)
    ax.set_yscale("log")
    ax.set_ylim(0.05, 200)
    ax.set_ylabel("durée d'arrêt à la ligne STOP (s, échelle log)")
    txt = " ; ".join(f"{c} : arrêt complet {100 * resume[f'stop/{c}']['part_arret_complet']:.0f} %" for c in C.CONFIGS)
    ax.set_title("STOP (priority_stop, jmStopSignWait = 1 pas par défaut)\n" + txt, fontsize=9)
    fig.tight_layout(); fig.savefig(DOSSIER / "resultats" / "S3_stop_et_prioritaire.png"); plt.close(fig)


if __name__ == "__main__":
    main()
