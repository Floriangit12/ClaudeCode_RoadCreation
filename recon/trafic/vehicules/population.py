"""Tirage d'une population de voitures particulières à partir de vehicules_parametres.json.

Prototype : seules les classes VP (citadine, compacte, berline, suv_b, suv_c, monospace_ludospace)
sont tirées ; les autres classes n'ont pas encore toutes leurs distributions (voir « lacunes »).

  python recon/trafic/vehicules/population.py --n 10000 --graine 1 [--parc neuf|circulation]

Règles de tirage (toutes tracées vers un paramètre du JSON ; version du 17/10/2026, relecture adverse) :
  classe          ~ part des immatriculations 2024 (<CLASSE>-PART-MARCHE), renormalisée
  famille, masse, P/m
                  tirage CONJOINT d'une combinaison (marque, modèle, version) dans <CLASSE>-MASSE-PM-CONJOINTE
                  (AEE 2024, pondérée par les immatriculations) : queues réelles, sans troncature ; familles
                  électrique (Ft = electric), thermique_auto_hybride (Fm = H ou P), thermique_manuelle (le reste).
                  parc = « circulation » (défaut) : poids des familles ramenés au parc en circulation
                  (PARC-VP-FAMILLE-2026, SDES) par des facteurs par famille ajustés (raking),
                  à l'intérieur de chaque classe (parts de classes : immatriculations 2024, faute de données de parc) ;
                  parc = « neuf » : immatriculations 2024 telles quelles.
                  (v0.1 : masse et P/m tirées indépendamment, tronquées à [P5 ; P95] ; hybrides comptés manuels)
  empattement     lognormale <CLASSE>-EMPATTEMENT tronquée à [P1 ; P99] de la lognormale ajustée
  k, a_lancement  VP-DYN-K / VP-DYN-A-LANCEMENT de la famille (normale moyenne +- écart-type des calages)
  d_max (sec)     parc « circulation » : VP-FREIN-DMAX-SEC-PARC (Greibe 2007, estimation) ;
                  parc « neuf » : VP-FREIN-DMAX-SEC (ADAC, pneus neufs, piste)
  CxS             facteur VP-DYN-CXS x largeur x hauteur (largeur, hauteur : uniforme entre les modèles
                  de référence de la classe, ou de toutes les VP de référence à défaut)
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dynamique import Vehicule  # noqa: E402

PARAMS_DEFAUT = Path(__file__).resolve().parents[3] / "assets" / "specs" / "trafic" / "vehicules_parametres.json"
CLASSES_VP = ["citadine", "compacte", "berline", "suv_b", "suv_c", "monospace_ludospace"]
FAMILLES = ["electrique", "thermique_auto_hybride", "thermique_manuelle"]
Z99 = 2.3263478740408408   # quantile 0,99 de la loi normale centrée réduite


def _par(J, classe, suffixe):
    for p in J["classes"][classe]["parametres"]:
        if p["id"] == f"{classe.upper()}-{suffixe}":
            return p["parametres"]
    return None


def _commun(J, pid):
    for p in J["classes"]["_dynamique_VP"]["parametres"]:
        if p["id"] == pid:
            return p["parametres"]
    raise KeyError(pid)


def _parc(J, pid):
    for p in J["parc_france"]:
        if p["id"] == pid:
            return p["parametres"]
    raise KeyError(pid)


def _lognorm_tronquee(rng, d):
    """Lognormale ajustée, tronquée à ses P1-P99 (v0.1 : P5-P95 empiriques, qui retiraient 10 % des véhicules)."""
    mu, sg = d["lognormale"]["mu_ln"], d["lognormale"]["sigma_ln"]
    lo, hi = math.exp(mu - Z99 * sg), math.exp(mu + Z99 * sg)
    for _ in range(1000):
        x = math.exp(rng.gauss(mu, sg))
        if lo <= x <= hi:
            return x
    return d["p50"]


def _normale_tronquee(rng, m, s, lo, hi):
    for _ in range(1000):
        x = rng.gauss(m, s)
        if lo <= x <= hi:
            return x
    return min(max(m, lo), hi)


def _tables(J, parc: str):
    """Tables cumulées (par classe) des combinaisons (masse, P/m, famille), pondérées selon le parc
    (mises en cache dans le dictionnaire J, clé privée « _tables_population »)."""
    cache = J.setdefault("_tables_population", {})
    if parc in cache:
        return cache[parc]
    poids_fam = {f: 1.0 for f in FAMILLES}
    if parc == "circulation":
        # ajustement proportionnel itératif (raking) : facteurs par famille tels que, avec les parts de classes
        # des immatriculations, les parts nationales des familles soient celles du parc en circulation (SDES)
        part_parc = _parc(J, "PARC-VP-FAMILLE-2026")
        part_cl = {c: _par(J, c, "PART-MARCHE")["part"] for c in CLASSES_VP}
        tot_cl = sum(part_cl.values())
        n_cf = {c: {f: 0.0 for f in FAMILLES} for c in CLASSES_VP}
        for c in CLASSES_VP:
            for m, pm, f, n in _par(J, c, "MASSE-PM-CONJOINTE")["lignes"]:
                n_cf[c][f] += n
        for _ in range(200):
            courant = {f: 0.0 for f in FAMILLES}
            for c in CLASSES_VP:
                den = sum(n_cf[c][f] * poids_fam[f] for f in FAMILLES)
                for f in FAMILLES:
                    courant[f] += part_cl[c] / tot_cl * n_cf[c][f] * poids_fam[f] / den
            poids_fam = {f: poids_fam[f] * part_parc[f] / courant[f] for f in FAMILLES}
    out = {}
    for c in CLASSES_VP:
        lignes = _par(J, c, "MASSE-PM-CONJOINTE")["lignes"]
        cum, acc = [], 0.0
        for m, pm, f, n in lignes:
            acc += n * poids_fam[f]
            cum.append(acc)
        out[c] = (lignes, cum)
    cache[parc] = out
    return out


def tirer_vp(J, rng, classe=None, parc="circulation"):
    if parc not in ("circulation", "neuf"):
        raise ValueError(parc)
    tab = _tables(J, parc)
    if classe is None:
        # parts de classes : immatriculations 2024 dans les deux cas (aucune répartition du parc par segment) ;
        # seules les familles sont ramenées au parc, à l'intérieur de chaque classe
        parts = {c: _par(J, c, "PART-MARCHE")["part"] for c in CLASSES_VP}
        tot = sum(parts.values())
        u, acc = rng.random() * tot, 0.0
        for c, p_ in parts.items():
            acc += p_
            if u <= acc:
                classe = c
                break
    lignes, cum = tab[classe]
    k_l = bisect.bisect_left(cum, rng.random() * cum[-1])
    masse, p_m, famille, _n = lignes[min(k_l, len(lignes) - 1)]
    W = _par(J, classe, "EMPATTEMENT")
    empattement = _lognorm_tronquee(rng, W) if W else None
    ex = _par(J, classe, "EXEMPLES")
    if not ex:
        ex = {"modeles": [m for c in CLASSES_VP for m in ((_par(J, c, "EXEMPLES") or {}).get("modeles", []))]}
    larg = rng.uniform(min(m["largeur_mm"] for m in ex["modeles"]), max(m["largeur_mm"] for m in ex["modeles"])) / 1000
    haut = rng.uniform(min(m["hauteur_mm"] for m in ex["modeles"]), max(m["hauteur_mm"] for m in ex["modeles"])) / 1000
    long_ = rng.uniform(min(m["longueur_mm"] for m in ex["modeles"]), max(m["longueur_mm"] for m in ex["modeles"])) / 1000
    K = _commun(J, "VP-DYN-K")[famille]
    AL = _commun(J, "VP-DYN-A-LANCEMENT")[famille]
    k_d = K["k_depart"]
    k = _normale_tronquee(rng, k_d["moyenne"], k_d["ecart_type"], k_d["min"], k_d["max"])
    a_l = AL["a_lancement"]["moyenne"] if AL["a_lancement"]["ecart_type"] == 0 else _normale_tronquee(
        rng, AL["a_lancement"]["moyenne"], AL["a_lancement"]["ecart_type"], AL["a_lancement"]["min"], AL["a_lancement"]["max"])
    D = _commun(J, "VP-FREIN-DMAX-SEC-PARC" if parc == "circulation" else "VP-FREIN-DMAX-SEC")
    d_max = _normale_tronquee(rng, D["moyenne"], D["ecart_type"], D["min"], D["max"])
    fcx = _commun(J, "VP-DYN-CXS")["facteur"]
    v = Vehicule(nom=f"{classe}_{famille}", masse_kg=float(masse), puissance_kW=p_m * masse / 1000.0, k_puissance=k,
                 a_lancement=a_l, cxs_m2=fcx * larg * haut, v_max_kmh=150.0 if famille == "electrique" else 180.0, d_max=d_max,
                 meta={"classe": classe, "famille": famille, "longueur_m": round(long_, 3), "largeur_m": round(larg, 3),
                       "hauteur_m": round(haut, 3), "empattement_mm": round(empattement) if empattement else None,
                       "puissance_masse_W_kg": round(p_m, 1), "parc": parc})
    return v


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parametres", default=str(PARAMS_DEFAUT))
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--parc", default="circulation", choices=["circulation", "neuf"])
    a = ap.parse_args(argv)
    J = json.load(open(a.parametres, encoding="utf-8"))
    rng = random.Random(a.graine)
    pop = [tirer_vp(J, rng, parc=a.parc) for _ in range(a.n)]
    t0100 = sorted(v.temps_acceleration(0, 100) for v in pop)
    t050 = sorted(v.temps_acceleration(0, 50) for v in pop)
    q = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))]
    res = {"n": a.n, "graine": a.graine, "parc": a.parc,
           "parts_classes": {c: round(sum(1 for v in pop if v.meta["classe"] == c) / a.n, 3) for c in CLASSES_VP},
           "parts_familles": {f: round(sum(1 for v in pop if v.meta["famille"] == f) / a.n, 3) for f in FAMILLES},
           "masse_kg": {"p1": round(q(sorted(v.masse_kg for v in pop), .01)), "p5": round(q(sorted(v.masse_kg for v in pop), .05)),
                        "p50": round(q(sorted(v.masse_kg for v in pop), .5)), "p95": round(q(sorted(v.masse_kg for v in pop), .95)),
                        "p99": round(q(sorted(v.masse_kg for v in pop), .99))},
           "t_0_50_s": {"p5": round(q(t050, .05), 2), "p50": round(q(t050, .5), 2), "p95": round(q(t050, .95), 2)},
           "t_0_100_s": {"p5": round(q(t0100, .05), 2), "p50": round(q(t0100, .5), 2), "p95": round(q(t0100, .95), 2)},
           "a_max_a_50_kmh": {"p5": round(q(sorted(v.acceleration_max(50 / 3.6) for v in pop), .05), 2), "p50": round(q(sorted(v.acceleration_max(50 / 3.6) for v in pop), .5), 2),
                              "p95": round(q(sorted(v.acceleration_max(50 / 3.6) for v in pop), .95), 2)},
           "d_100_0_m": {"p5": round(q(sorted(v.distance_freinage(100) for v in pop), .05), 1), "p50": round(q(sorted(v.distance_freinage(100) for v in pop), .5), 1),
                         "p95": round(q(sorted(v.distance_freinage(100) for v in pop), .95), 1)}}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
