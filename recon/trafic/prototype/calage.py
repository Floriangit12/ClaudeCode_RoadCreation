"""Calages du prototype (conception § 16, étape 1) : démarrage et décharge au feu.

1. Démarrage d'un véhicule seul (cible V-08, Salles 2020 p. 14) : taccmax et Mbegin du facteur de
   démarrage EIDM (Mflatness gardé au défaut SUMO 2,0) pour que la médiane de la population atteigne
   1 m/s en 0,8 s et son pic d'accélération à 2,3 s après le début du mouvement.
2. Décharge d'une file (cible V-10, Certu Feux 2010 p. 34 : 1 800 uvpd/h, 2,0 s) : rapport r = T_décharge /
   T_suivi, global, pour que le TIV moyen des rangs 5 à 12 de la population vaille 2,0 s (dichotomie),
   pour les deux variantes de réaction au départ (« meneur » : chaîne de réactions ; « vert » : chacun
   réagit au vert).
3. v0.2 (relecture adverse du 17/10/2026) : contrainte de stabilité. Le r retenu est le plus petit r ≥ r(2,0 s)
   qui donne zéro collision primaire sur 5 graines × 200 files (V-24) ; si ce r dépasse r(2,0 s), le débit
   obtenu est publié tel quel (il n'est plus de 1 800 uvpd/h). T_i ≥ Δ_a,i (H-17) est appliqué pendant le calage.
   L'horizon de prévisualisation (tpreview) n'est plus un défaut EIDM : il est lu dans TAC.pieton.approche
   (inD, LVi / Vi), voir parametres.py.

Écrit assets/specs/trafic/parametres_prototype.json et 05_Prototype/resultats/calage.json.
  python recon/trafic/prototype/calage.py [--rapide]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import optimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from parametres import DOC05, Parametres, ecrire_parametres_prototype  # noqa: E402
from route import Route  # noqa: E402
from simulateur import Simulation  # noqa: E402
import scenarios as SC  # noqa: E402

CIBLE_T1, CIBLE_TPIC = 0.8, 2.3          # Salles 2020 p. 14 (LON.eidm.demarrage_salles2020)
CIBLE_TIV = 2.0                          # VAL.feu.saturation_fr (Certu Feux 2010 p. 34)
CIBLE_PIC_RANG1 = 2.67                   # VAL.acc.demarrage_file rang 1 (Salles 2020 fig. 8, drone)


def mesures_demarrage(tr, idx):
    """Pour chaque agent : t(1 m/s) et instant du pic d'accélération depuis le début du mouvement, pic."""
    t, v, a = tr["t"], tr["v"][:, idx], tr["a"][:, idx]
    out = []
    for j in range(len(idx)):
        vv, aa = v[:, j], a[:, j]
        ok = np.isfinite(vv)
        if not ok.any() or not (vv[ok] > 0.01).any():
            out.append((np.nan, np.nan, np.nan))
            continue
        k0 = int(np.argmax(np.where(ok, vv, 0) > 0.01))
        t_dep = t[k0] - 0.1           # l'échantillon k0 est la fin du premier pas en mouvement
        k1 = int(np.argmax(np.where(ok, vv, 0) >= 1.0))
        # interpolation linéaire pour t(1 m/s)
        t1 = t[k1 - 1] + 0.1 * (1.0 - vv[k1 - 1]) / max(vv[k1] - vv[k1 - 1], 1e-9) if k1 > 0 else np.nan
        fen = slice(k0, min(k0 + 120, len(t)))
        kp = k0 + int(np.nanargmax(aa[fen]))
        out.append((t1 - t_dep, t[kp] - 0.05 - t_dep, float(aa[kp])))
    return np.array(out)


def demarrage_isole(P, n=2000, graine=101):
    """Véhicules seuls arrêtés sans contrainte devant eux : départ après le TPR anticipé."""
    route = Route("libre", voie=0, longueur=400.0, reseau="artere_centre_ville_50")
    pop, veh = SC.tirer_agents(P, n, graine)
    agents = {"route": np.zeros(n, int), "couloir": np.arange(n), "t_insert": np.zeros(n), "s_insert": np.zeros(n),
              "v_insert": np.zeros(n), "pop": pop, "veh": veh}
    sim = Simulation(P, [route], agents, graine=graine, hdm=False)
    sim.executer(12.0)
    return mesures_demarrage(sim.traces(), np.arange(n))


def caler_demarrage(P, n=2000):
    hist = []

    def cout(x):
        tacc, mb = x
        if tacc <= 0.2 or not (-1.0 <= mb <= 2.0):
            return 1e3
        P.proto["demarrage_taccmax"]["valeur"] = float(tacc)
        P.proto["demarrage_Mbegin"]["valeur"] = float(mb)
        m = demarrage_isole(P, n)
        t1, tp = np.nanmedian(m[:, 0]), np.nanmedian(m[:, 1])
        c = ((t1 - CIBLE_T1) / 0.2) ** 2 + ((tp - CIBLE_TPIC) / 0.3) ** 2
        hist.append((float(tacc), float(mb), float(t1), float(tp), float(c)))
        return c

    res = optimize.minimize(cout, x0=[3.0, 0.2], method="Nelder-Mead",
                            options={"xatol": 0.01, "fatol": 1e-3, "maxiter": 60})
    tacc, mb = res.x
    P.proto["demarrage_taccmax"]["valeur"] = round(float(tacc), 3)
    P.proto["demarrage_Mbegin"]["valeur"] = round(float(mb), 3)
    for k in ("demarrage_taccmax", "demarrage_Mbegin"):
        P.proto[k]["nature"] = "calage"
        P.proto[k]["source"] = "calé sur Salles 2020 p. 14 (1 m/s en 0,8 s ; pic à 2,3 s), calage.py"
    m = demarrage_isole(P, n)
    return {"taccmax": round(float(tacc), 3), "Mbegin": round(float(mb), 3), "Mflatness": P.v("demarrage_Mflatness"),
            "t_1ms_s": _q(m[:, 0]), "t_pic_s": _q(m[:, 1]), "pic_ms2": _q(m[:, 2]), "iterations": hist}


def _q(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return {"moyenne": round(float(x.mean()), 3), "ecart_type": round(float(x.std()), 3),
            **{f"p{p}": round(float(np.percentile(x, p)), 3) for p in (5, 25, 50, 75, 95)}, "n": int(x.size)}


def tiv_par_rang(sim, meta):
    det = sim.detections_tableau()
    tc = np.full(len(meta["rang"]), np.nan)
    for i, r, d, t, v in det:
        if d == 0:
            tc[int(i)] = t
    tc = tc.reshape(meta["n_files"], meta["n_vehicules"])
    h = np.diff(np.concatenate([np.zeros((tc.shape[0], 1)), tc], axis=1), axis=1)
    return tc, h


def pics_par_rang(sim, meta):
    a = sim.traces()["a"]
    nf, nv = meta["n_files"], meta["n_vehicules"]
    return np.array([np.nanmean(np.nanmax(a[:, np.arange(rk, nf * nv, nv)], axis=0)) for rk in range(nv)])


def caler_facteur_a(P, n_files=150, graine=1):
    """Facteur d'accélération en décharge (H-14) : pic moyen du rang 1 = 2,67 m/s² (point fixe)."""
    hist = []
    for _ in range(3):
        sim, meta = SC.s1_file_feu(P, n_files=n_files, graine=graine)
        p1 = float(pics_par_rang(sim, meta)[0])
        k = P.v("facteur_a_decharge")
        hist.append((round(k, 4), round(p1, 4)))
        if abs(p1 - CIBLE_PIC_RANG1) < 0.01:
            break
        P.proto["facteur_a_decharge"]["valeur"] = round(k * CIBLE_PIC_RANG1 / p1, 4)
    return P.v("facteur_a_decharge"), hist


def caler_r(P, reaction="meneur", n_files=150, graine=1):
    hist = []

    def tiv(r):
        P.proto["T_decharge_rapport"]["valeur"] = float(r)
        sim, meta = SC.s1_file_feu(P, n_files=n_files, graine=graine, reaction_depart=reaction, enregistrer=False)
        _, h = tiv_par_rang(sim, meta)
        x = float(np.nanmean(h[:, 4:12]))
        hist.append((round(r, 4), round(x, 4)))
        return x

    lo, hi = 0.2, 1.2
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        if tiv(mid) > CIBLE_TIV:
            hi = mid
        else:
            lo = mid
    return round(0.5 * (lo + hi), 3), hist


def collisions_s1(P, graines=(1, 2, 3, 4, 5), n_files=200, reaction="vert"):
    """Collisions primaires et secondaires de S1 sur plusieurs graines (contrainte de stabilité, V-24)."""
    out = []
    for g in graines:
        sim, meta = SC.s1_file_feu(P, n_files=n_files, graine=g, reaction_depart=reaction, enregistrer=False)
        _, h = tiv_par_rang(sim, meta)
        out.append({"graine": g, "primaires": len(sim.collisions), "secondaires": len(sim.collisions_secondaires),
                    "tiv_5_12_s": round(float(np.nanmean(h[:, 4:12])), 4)})
    return out


def caler_r_stable(P, r0, pas=0.01, max_iter=25):
    """Plus petit r ≥ r0 sans collision primaire sur 5 graines × 200 files."""
    hist = []
    r = r0
    for _ in range(max_iter):
        P.proto["T_decharge_rapport"]["valeur"] = float(r)
        c = collisions_s1(P)
        n = sum(x["primaires"] for x in c)
        hist.append({"r": round(r, 4), "collisions_primaires": n, "par_graine": c})
        if n == 0:
            return round(r, 4), hist
        r += pas
    return round(r, 4), hist


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapide", action="store_true")
    a = ap.parse_args(argv)
    P = Parametres(chemin_proto=None)
    t0 = time.time()
    res = {"cibles": {"t_1ms_s": CIBLE_T1, "t_pic_s": CIBLE_TPIC, "TIV_rangs_5_12_s": CIBLE_TIV,
                      "sources": ["LON.eidm.demarrage_salles2020 (Salles 2020 p. 14)", "VAL.feu.saturation_fr (Certu Feux 2010 p. 34)"]}}
    res["demarrage_defauts_EIDM"] = {"t_1ms_s": None}
    m0 = demarrage_isole(P, 1000)
    res["demarrage_defauts_EIDM"] = {"taccmax": 1.2, "Mbegin": 0.7, "Mflatness": 2.0, "t_1ms_s": _q(m0[:, 0]),
                                     "t_pic_s": _q(m0[:, 1]), "pic_ms2": _q(m0[:, 2])}
    res["demarrage"] = caler_demarrage(P, 1000 if a.rapide else 2000)
    nf = 60 if a.rapide else 150
    k_a, h_k = caler_facteur_a(P, nf)
    res["facteur_a_decharge"] = {"valeur": k_a, "iterations": h_k}
    r_men, h_men = caler_r(P, "meneur", nf)
    r_vert, h_vert = caler_r(P, "vert", nf)
    res["r_meneur"], res["r_vert"] = {"r": r_men, "iterations": h_men}, {"r": r_vert, "iterations": h_vert}
    tiv_men = [x[1] for x in h_men]
    if r_men <= 0.21:
        res["r_meneur"]["note"] = ("variante « meneur » : le TIV des rangs 5-12 plafonne vers %.2f s (chaîne de réactions), "
                                   "la dichotomie n'a pas de sens" % min(tiv_men))
    else:
        res["r_meneur"]["note"] = "variante « meneur » (réaction au départ du meneur) : r = %.3f ; non retenue par défaut" % r_men
    r_stable, h_stable = caler_r_stable(P, r_vert)
    res["r_stable"] = {"r": r_stable, "r_debit_2_0s": r_vert, "iterations": h_stable,
                       "regle": "plus petit r ≥ r(2,0 s) sans collision primaire sur 5 graines × 200 files (V-24, H-17 appliquée)"}
    P.proto["T_decharge_rapport"]["valeur"] = r_stable
    P.proto["T_decharge_rapport"]["nature"] = "calage"
    P.proto["T_decharge_rapport"]["source"] = ("calé : TIV moyen des rangs 5-12 = 2,0 s (Certu Feux 2010 p. 34), réaction au vert "
                                               "(reaction_depart_feu), facteur_a_decharge calé avant, T_i ≥ Δ_a,i (H-17), puis plus petit r "
                                               f"sans collision primaire sur 5 graines × 200 files (r(2,0 s) = {r_vert}) ; calage.py")
    res["duree_s"] = round(time.time() - t0, 1)
    calages = {
        "demarrage_taccmax": {"grandeur": "durée caractéristique du facteur de démarrage EIDM", "unite": "s",
                              "conditions": "Mflatness au défaut SUMO ; médiane de la population", "confiance": "faible"},
        "demarrage_Mbegin": {"grandeur": "décalage du facteur de démarrage EIDM", "unite": "-", "confiance": "faible"},
        "facteur_a_decharge": {"grandeur": "facteur sur a (IIDM) pendant la décharge d'une file ou d'une ligne", "unite": "-",
                               "conditions": "pic moyen du rang 1 au feu = 2,67 m/s² (Salles 2020 fig. 8)", "confiance": "faible"},
        "T_decharge_rapport": {"grandeur": "r = T_décharge / T_suivi (décharge d'une file)", "unite": "-",
                               "conditions": "IIDM + CAH ; départ après TPR anticipé au vert ; T_i ≥ Δ_a,i ; contrainte zéro collision (5 × 200 files)", "confiance": "faible"},
    }
    ecrire_parametres_prototype(P, calages)
    (DOC05 / "resultats").mkdir(parents=True, exist_ok=True)
    (DOC05 / "resultats" / "calage.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "demarrage"}, ensure_ascii=False)[:2000])
    print("demarrage", res["demarrage"]["taccmax"], res["demarrage"]["Mbegin"], res["demarrage"]["t_1ms_s"]["p50"],
          res["demarrage"]["t_pic_s"]["p50"], res["demarrage"]["pic_ms2"]["moyenne"])
    return res


if __name__ == "__main__":
    main()
