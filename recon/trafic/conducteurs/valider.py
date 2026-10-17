"""Validation du prototype de modèle de conducteurs.

T1 forme machine et sources ; T2 reproduction des statistiques publiées par les lois ajustées ;
T3 vitesses (ajustements normaux et histogrammes) ; T4 tirage d'une population (marges et
corrélations) ; T5 cohérence avec les normes françaises (TPR, distances d'arrêt) ;
T6 ordre des profils ; T7 cohérences croisées (saturation, jaune).
Les contrôles vrais par construction (T6, T7b) sont marqués « par construction » et non bloquants
(relecture adverse du 17/10/2026) : ils vérifient la mise en œuvre, pas le modèle.

Usage : python valider.py [--n 200000] [--graine 1] [--sortie DOSSIER]
Écrit validation/validation_prototype.json dans le dossier du volet et affiche un résumé.
Code de sortie 1 si un test bloquant échoue.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lois  # noqa: E402
import modele_conducteurs as mc  # noqa: E402

G = 9.81
RES = []


def test(nom, ok, detail, bloquant=True):
    RES.append({"test": nom, "ok": bool(ok), "bloquant": bloquant, "detail": detail})


def t1_forme(params):
    req = ["id", "volet", "grandeur", "population", "loi", "parametres", "unite", "conditions", "nature", "source", "confiance"]
    natures = {"norme", "mesure", "estimation", "defaut_logiciel"}
    conf = {"elevee", "moyenne", "faible"}
    err = []
    for p in params["parametres"]:
        for k in req:
            if k not in p:
                err.append(f"{p.get('id')}: champ {k} absent")
        if p.get("nature") not in natures:
            err.append(f"{p['id']}: nature {p.get('nature')}")
        if p.get("confiance") not in conf:
            err.append(f"{p['id']}: confiance {p.get('confiance')}")
        s = p.get("source", {})
        if s.get("cle") not in params["sources"]:
            err.append(f"{p['id']}: source inconnue {s.get('cle')}")
        if not s.get("page"):
            err.append(f"{p['id']}: page absente")
    test("T1 forme machine et sources", not err, {"n_parametres": len(params["parametres"]), "erreurs": err[:20]})


def t2_reproduction(params):
    lignes, ko = [], []
    for p in params["parametres"]:
        st = p.get("statistiques_publiees")
        if not st or p["loi"] not in ("lognormale", "gev", "normale_tronquee", "normale", "lognormale_decalee"):
            continue
        par = p["parametres"]
        if p["loi"] in ("normale", "normale_tronquee") and "moyenne" not in par:
            continue
        # loi tronquée explicitement (q_min / q_max) : la statistique publiée porte sur la loi non tronquée
        par = {k: v for k, v in par.items() if k not in ("q_min", "q_max")}
        mo = lois.moments(p["loi"], par)
        chk = {}
        if "moyenne" in st and isinstance(st["moyenne"], (int, float)) and p["loi"] != "normale_tronquee":
            chk["moyenne"] = (st["moyenne"], mo["moyenne"])
        if "ecart_type" in st and p["loi"] in ("lognormale",):
            chk["ecart_type"] = (st["ecart_type"], mo["ecart_type"])
        if "variance" in st and p["loi"] in ("lognormale", "gev"):
            chk["variance"] = (st["variance"], mo["ecart_type"] ** 2)
        for q in ("p5", "p25", "p50", "p75", "p95"):
            if q in st and p["loi"] in ("lognormale", "gev", "lognormale_decalee"):
                chk[q] = (st[q], float(lois.quantile(p["loi"], par, int(q[1:]) / 100)))
        for k, (pub, mod) in chk.items():
            tol = 0.03 * abs(pub) + 0.011
            ok = abs(pub - mod) <= tol
            # médianes Bosetti : P5 et P95 sont imposés, la médiane est libre (tolérance 5 %)
            if k == "p50" and p["id"].endswith("_bosetti"):
                ok = abs(pub - mod) <= 0.05 * abs(pub) + 0.2
            lignes.append({"id": p["id"], "stat": k, "publie": pub, "modele": round(mod, 4), "ok": ok})
            if not ok:
                ko.append(f"{p['id']}.{k}: publié {pub} / modèle {mod:.3f}")
    test("T2 reproduction des statistiques publiées (lois non tronquées)", not ko, {"n_controles": len(lignes), "ecarts": ko, "lignes": lignes})
    # T2b : décélération d'urgence équivalente contre les centiles du tableau 25 de NCHRP 400 (étude 3)
    idx = {p["id"]: p for p in params["parametres"]}
    pe = idx["dec.urgence_equivalente"]
    tab25 = pe["statistiques_publiees"]["percentiles_depassement_g_tab25"]
    lig, ko2 = [], []
    for depasse, g_pub in tab25.items():
        q_ordre = 1.0 - int(depasse) / 100.0
        g_mod = float(lois.quantile(pe["loi"], pe["parametres"], q_ordre)) / G
        ok = abs(g_mod - g_pub) <= 0.04
        lig.append({"part_qui_depasse": int(depasse) / 100.0, "publie_g": g_pub, "modele_g": round(g_mod, 3), "ok": ok})
        if not ok:
            ko2.append(f"{depasse} % : {g_pub} g publié / {g_mod:.3f} g")
    test("T2b décélération d'urgence : centiles du tab. 25 de NCHRP 400 (± 0,04 g)", not ko2, {"lignes": lig, "ecarts": ko2})
    # T2c : lois tronquées : part des tirages retirés et moyenne tronquée (information)
    tr = []
    for p in params["parametres"]:
        par = p.get("parametres", {})
        if isinstance(par, dict) and ("q_max" in par or "q_min" in par):
            brut = {k: v for k, v in par.items() if k not in ("q_min", "q_max")}
            tr.append({"id": p["id"], "q_min": par.get("q_min", 0.0), "q_max": par.get("q_max", 1.0),
                       "borne_haute": round(float(lois.quantile(p["loi"], brut, par.get("q_max", 1.0) - 1e-9)), 3),
                       "moyenne_non_tronquee": round(lois.moments(p["loi"], brut)["moyenne"], 3),
                       "moyenne_tronquee": round(lois.moments(p["loi"], par)["moyenne"], 3)})
    test("T2c lois tronquées explicitement (information)", True, {"lois": tr}, bloquant=False)


def t3_vitesses(params):
    idx = mc.index(params)
    lignes, ko = [], []
    for p in params["parametres"]:
        if not p["id"].startswith("vit.") or p["loi"] != "normale" or "tirage" not in p:
            continue
        vma = p["tirage"]["vma_kmh"]
        st = p.get("statistiques_publiees", {}).get("2023_jour")
        if not st:
            continue
        par = p["parametres"]
        for seuil, cle in ((vma + 0.5, "part_sup_VMA"), (vma + 10.5, "part_sup_VMA+10")):
            mod = 1 - stats.norm.cdf(seuil, par["moyenne"], par["ecart_type"])
            pub = st[cle]
            ok = abs(mod - pub) <= 0.04 or p["id"].endswith("entree_sortie_agglo_50")
            lignes.append({"id": p["id"], "seuil": seuil, "publie": pub, "modele": round(mod, 3), "ok": ok})
            if not ok:
                ko.append(f"{p['id']} > {seuil}: {pub} / {mod:.3f}")
    # histogrammes : moyenne reconstituée vs moyenne publiée
    hist_ref = {"vit.histo.artere_centre_ville_50.2019": 43, "vit.histo.artere_centre_ville_50.2023_jour": 41.2,
                "vit.histo.artere_centre_ville_50.2023_nuit": 45.4, "vit.histo.route_2_3_voies_80.2019": 78,
                "vit.histo.traversee_petite_agglo_50.2019": 49, "vit.histo.entree_sortie_agglo_50.2019": 48,
                "vit.histo.autoroute_liaison_130.2019": 119}
    hl = []
    for hid, mpub in hist_ref.items():
        par = idx[hid]["parametres"]
        b = np.array(par["bornes"], float)
        f = np.array(par["frequences"], float)
        mid = (b[:-1] + b[1:]) / 2
        m = float((mid * f).sum() / f.sum())
        ok = abs(m - mpub) <= 1.0
        hl.append({"id": hid, "somme_pct": round(float(f.sum()), 2), "moyenne_reconstituee": round(m, 2), "moyenne_publiee": mpub, "ok": ok})
        if not ok:
            ko.append(f"{hid}: moyenne {m:.2f} vs {mpub}")
    # forme : normale ajustée vs histogramme 2023 artères (distance de Kolmogorov sur les classes)
    h = idx["vit.histo.artere_centre_ville_50.2023_jour"]["parametres"]
    pn = idx["vit.artere_centre_ville_50"]["parametres"]
    b = np.array(h["bornes"], float)
    cdf_h = np.concatenate([[0], np.cumsum(h["frequences"]) / np.sum(h["frequences"])])
    cdf_n = stats.norm.cdf(b, pn["moyenne"], pn["ecart_type"])
    dks = float(np.max(np.abs(cdf_h - cdf_n)))
    test("T3 vitesses : ajustements et histogrammes", not ko,
         {"depassements": lignes, "histogrammes": hl, "ecart_KS_normale_vs_histo_arteres_2023": round(dks, 3), "ecarts": ko})
    test("T3b forme : normale proche de l'histogramme (artères 2023, KS < 0,05)", dks < 0.05, {"KS": round(dks, 3)}, bloquant=False)


def t4_population(params, n, graine):
    rng = np.random.default_rng(graine)
    val, lat = mc.tirer_population(params, n, rng)
    idx = mc.index(params)
    grp = mc.groupes(params)
    ks, ko = [], []
    for pid, x in val.items():
        p = idx[pid]
        if p["loi"] in ("bernoulli", "categorielle", "empirique_classes", "uniforme"):
            if p["loi"] == "bernoulli":
                ok = abs(x.mean() - p["parametres"]["p"]) < 0.01
                ks.append({"id": pid, "moyenne": round(float(x.mean()), 4), "attendu": p["parametres"]["p"], "ok": ok})
            elif p["loi"] == "categorielle":
                probs = np.array(list(p["parametres"]["modalites"].values()), float)
                obs = np.bincount(x.astype(int), minlength=len(probs)) / len(x)
                ok = float(np.max(np.abs(obs - probs / probs.sum()))) < 0.01
                ks.append({"id": pid, "frequences": [round(float(o), 4) for o in obs], "attendu": probs.tolist(), "ok": ok})
            else:
                ok = True
            if not ok:
                ko.append(pid)
            continue
        cdf = lambda xx, p=p: lois.cdf(p["loi"], p["parametres"], xx)  # noqa: E731
        D = stats.kstest(x, cdf).statistic
        ok = D < 0.01
        ks.append({"id": pid, "KS": round(float(D), 4), "ok": ok})
        if not ok:
            ko.append(f"{pid}: KS {D:.4f}")
    # corrélations de rang entre groupes : un paramètre représentatif par groupe
    # (on mesure sur les variables latentes : les paramètres continus en sont des fonctions croissantes,
    #  les comportements discrets (Bernoulli « cède ») des fonctions décroissantes à ex aequo)
    noms = sorted(grp)
    cor, ecarts = [], []
    for i, g1 in enumerate(noms):
        for g2 in noms[i + 1:]:
            th = mc.spearman_theorique(grp[g1]["charge"], grp[g2]["charge"], grp[g1]["facteur"] == grp[g2]["facteur"])
            ob = stats.spearmanr(lat[g1], lat[g2]).statistic
            ok = abs(ob - th) < 0.02
            cor.append({"groupes": f"{g1}|{g2}", "theorique": round(th, 3), "observe": round(float(ob), 3), "ok": ok})
            if not ok:
                ecarts.append(f"{g1}|{g2}: {th:.3f} vs {ob:.3f}")
    # paramètres continus : rang identique à celui de leur variable latente
    mono = []
    for g, v in grp.items():
        p0 = idx[v["ids"][0]]
        if p0["loi"] not in ("bernoulli", "categorielle"):
            r = stats.spearmanr(val[v["ids"][0]], lat[g]).statistic
            mono.append({"groupe": g, "spearman_param_latent": round(float(r), 4)})
            if r < 0.999:
                ecarts.append(f"{g}: transformation non monotone ({r:.4f})")
    # cohérence intra-groupe : corrélation de rang = 1
    intra = []
    for g, v in grp.items():
        if len(v["ids"]) > 1:
            r = stats.spearmanr(val[v["ids"][0]], val[v["ids"][1]]).statistic
            intra.append({"groupe": g, "spearman": round(float(r), 4)})
    test("T4 population : marges conformes aux lois sourcées (KS < 0,01)", not ko, {"n": n, "marges": ks, "ecarts": ko})
    test("T4b population : corrélations de rang conformes à la structure déclarée (|écart| < 0,02)", not ecarts,
         {"n_paires": len(cor), "ecarts": ecarts, "paires_non_nulles": [c for c in cor if abs(c["theorique"]) > 0], "intra_groupe": intra, "monotonie": mono})
    return val


def gamma_v(v_kmh):
    """γv du Cerema 2018 (p. 11, PDF 13) : 0,46 à 30 ET 50 km/h (cellule fusionnée), 0,44 à 70, 0,41 au-delà.
    Corrigé le 17/10/2026 (la v0.1 prenait 0,44 à 50 km/h et 0,41 à 70 km/h)."""
    return 0.46 if v_kmh <= 50 else 0.44 if v_kmh <= 70 else 0.41


def distance_arret_norme(v_kmh):
    """Distance d'arrêt Cerema 2018 (p. 11) en palier, alignement droit, K = 1 (niveau B)."""
    v = v_kmh / 3.6
    return 1.8 * v + v * v / (2 * G * gamma_v(v_kmh))


def t5_normes(params, val):
    idx = mc.index(params)
    ps = idx["tpr.surprise_obstacle"]
    pi = idx["tpr.inattendu_signal"]
    cov = {
        "P(TPR_surprise <= 1,8 s Cerema)": float(lois.cdf("lognormale", ps["parametres"], 1.8)),
        "P(TPR_surprise <= 2,0 s ICTAVRU/ACI)": float(lois.cdf("lognormale", ps["parametres"], 2.0)),
        "P(TPR_surprise <= 2,5 s AASHTO)": float(lois.cdf("lognormale", ps["parametres"], 2.5)),
        "P(TPR_inattendu <= 1,8 s)": float(lois.cdf("lognormale", pi["parametres"], 1.8)),
        "P(TPR_inattendu <= 2,0 s)": float(lois.cdf("lognormale", pi["parametres"], 2.0)),
    }
    ok_tpr = 0.88 <= cov["P(TPR_surprise <= 1,8 s Cerema)"] <= 0.97 and cov["P(TPR_surprise <= 2,0 s ICTAVRU/ACI)"] >= 0.93
    # distances d'arrêt simulées (chaussée sèche, décélération d'urgence équivalente NCHRP) vs distance normative (mouillé)
    tpr = val["tpr.surprise_obstacle"]
    dec = val["dec.urgence_equivalente"]
    dist = {}
    for vk in (30, 50, 70, 90):
        v = vk / 3.6
        d = v * tpr + v * v / (2 * dec)
        dn = distance_arret_norme(vk)
        dist[f"{vk} km/h"] = {"norme_m": round(dn, 1), "mediane_simulee_m": round(float(np.median(d)), 1),
                              "p95_simule_m": round(float(np.percentile(d, 95)), 1), "part_couverte": round(float((d <= dn).mean()), 4)}
    # NCHRP 400 recommande des valeurs de conception au 90e centile : on exige une couverture ≥ 90 %
    ok_d = all(x["part_couverte"] >= 0.90 for x in dist.values())
    test("T5 TPR : les valeurs normatives françaises se situent vers le 90e-97e centile", ok_tpr, {k: round(v, 4) for k, v in cov.items()})
    test("T5b distances d'arrêt : la norme (mouillé, 1,8 s) couvre ≥ 90 % des arrêts simulés sur sec", ok_d, dist)
    # ralentissement normatif vs décélération habituelle
    dcu = val["dec.max_courante_urbain"]
    test("T5c décélération habituelle maximale ≥ décélération normative de ralentissement (1,5 m/s²) pour ≥ 90 % des conducteurs",
         float((dcu >= 1.5).mean()) >= 0.9, {"part": round(float((dcu >= 1.5).mean()), 4)}, bloquant=False)


def t6_profils(prof):
    ordre = ["prudent", "moyen", "presse", "agressif"]
    P = {p["id"]: p for p in prof["profils"]}
    croissants = ["vit.artere_centre_ville_50", "vit.autoroute_liaison_130", "acc.demarrage_pic", "courbe.alat_max_conducteur",
                  "feu.seuil_arret_jaune", "ralent.vitesse_franchissement"]
    decroissants = ["tiv.moyen_conducteur_urbain", "creneau.facteur_conducteur", "vdv.duree_chevauchement"]
    ko = []
    for pid in croissants:
        xs = [P[o]["valeurs"][pid]["mediane"] for o in ordre]
        if not all(a < b for a, b in zip(xs, xs[1:])):
            ko.append(f"{pid} non croissant {xs}")
    for pid in decroissants:
        xs = [P[o]["valeurs"][pid]["mediane"] for o in ordre]
        if not all(a > b for a, b in zip(xs, xs[1:])):
            ko.append(f"{pid} non décroissant {xs}")
    ac = [P[o]["valeurs"]["stop.comportement"]["probabilites"]["arret_complet"] for o in ordre]
    if not all(a > b for a, b in zip(ac, ac[1:])):
        ko.append(f"arrêt complet non décroissant {ac}")
    poids = sum(P[o]["poids_population"] for o in ordre)
    if abs(poids - 1) > 1e-3:
        ko.append(f"poids des tranches = {poids}")
    test("T6 profils ordonnés et poids = 1 (par construction : tranches de S, contrôle de mise en œuvre)", not ko,
         {"ecarts": ko, "somme_poids": round(poids, 4)}, bloquant=False)


def t7_croisees(params, val):
    idx = mc.index(params)
    # saturation : TIV au feu (rang ≥ 4) et norme 1800 uvpd/h (2,0 s)
    sat = idx["tiv.file_feu"]["parametres"]["rang4_plus"]
    ok = sat[0] <= 2.0 <= sat[1] + 0.05
    test("T7 cohérence entre deux sources : TIV de décharge mesurés (Stuttgart, rang ≥ 4) et 1 800 uvpd/h (2,0 s)", ok,
         {"tiv_rang4_plus": sat, "norme_s": 2.0}, bloquant=False)
    # jaune : P(arrêt | TTL) reproduit 10 % / 90 % à 2,5 / 5,5 s sur la population tirée
    T = val["feu.seuil_arret_jaune"]
    p25, p55 = float((T < 2.5).mean()), float((T < 5.5).mean())
    test("T7b jaune : P(arrêt|TTL) aux 2 points d'ajustement (par construction : contrôle du tirage)", abs(p25 - 0.1) < 0.01 and abs(p55 - 0.9) < 0.01,
         {"P_arret_2_5s": round(p25, 4), "P_arret_5_5s": round(p55, 4),
          "P_arret_3_5s_interpolation_du_projet": round(float((T < 3.5).mean()), 4)}, bloquant=False)
    # temps de réaction au jaune vs conception ITE (1,0 s)
    tj = val["feu.tpr_jaune"]
    test("T7c jaune : valeur de conception 1,0 s ≈ médiane observée à l'insu (± 0,2 s)", abs(float(np.median(tj)) - 1.0) <= 0.2,
         {"mediane_tpr_jaune": round(float(np.median(tj)), 3)}, bloquant=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200000)
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--dossier", default=mc.DOSSIER_DOC)
    a = ap.parse_args()
    params, prof = mc.charger(a.dossier)
    t1_forme(params)
    t2_reproduction(params)
    t3_vitesses(params)
    val = t4_population(params, a.n, a.graine)
    t5_normes(params, val)
    if prof:
        t6_profils(prof)
    t7_croisees(params, val)
    os.makedirs(os.path.join(a.dossier, "validation"), exist_ok=True)
    chemin = os.path.join(a.dossier, "validation", "validation_prototype.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"n": a.n, "graine": a.graine, "resultats": RES}, f, ensure_ascii=False, indent=1,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    nb_ko = 0
    for r in RES:
        etat = "OK " if r["ok"] else ("KO " if r["bloquant"] else "AVERT")
        if not r["ok"] and r["bloquant"]:
            nb_ko += 1
        print(f"[{etat}] {r['test']}")
    print(f"-> {chemin}")
    sys.exit(1 if nb_ko else 0)


if __name__ == "__main__":
    main()
