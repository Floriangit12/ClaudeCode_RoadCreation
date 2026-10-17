"""Tableaux du rapport de prototype à partir de 05_Prototype/resultats/resultats_prototype.json.

  python recon/trafic/prototype/tableaux.py
Écrit 05_Prototype/tableaux/*.md et *.csv.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from parametres import DOC05  # noqa: E402

CFG = ["krauss_defaut", "eidm_defaut", "krauss_nos_lois", "eidm_nos_lois"]
CFG_S2 = CFG + ["krauss_nos_lois_asl", "krauss_nos_lois_ds"]
LIB = {"modele": "Notre modèle", "krauss_defaut": "Krauss défaut", "eidm_defaut": "EIDM défaut",
       "krauss_nos_lois": "Krauss nos lois", "eidm_nos_lois": "EIDM nos lois",
       "krauss_nos_lois_asl": "Krauss nos lois, actionStepLength = TPR", "krauss_nos_lois_ds": "Krauss nos lois, driverstate"}


def f(x, n=2):
    if x is None:
        return "—"
    if isinstance(x, (int, float)):
        return f"{x:.{n}f}".replace(".", ",")
    return str(x)


def g(d, *ks):
    for k in ks:
        if d is None:
            return None
        d = d.get(k) if isinstance(d, dict) else None
    return d


def ecrire(nom, entete, lignes):
    T = DOC05 / "tableaux"
    T.mkdir(parents=True, exist_ok=True)
    md = ["| " + " | ".join(entete) + " |", "|" + "---|" * len(entete)] + ["| " + " | ".join(l) + " |" for l in lignes]
    (T / f"{nom}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with open(T / f"{nom}.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.writer(fc, delimiter=";")
        w.writerow(entete)
        w.writerows(lignes)
    return "\n".join(md)


def main():
    R = json.load(open(DOC05 / "resultats" / "resultats_prototype.json", encoding="utf-8"))
    out = []
    # ---------------- S1
    s1 = R["S1"]
    cols = [("modele", s1["modele"])] + [(c, s1["sumo"].get(c)) for c in CFG if c in s1["sumo"]]
    lignes = []
    for lab, fn in [("TIV moyen rangs 5-12 (s)", lambda r: f(r["tiv_rangs_5_12_moyen_s"])),
                    ("débit de saturation (véh/h)", lambda r: f(r["debit_saturation_veh_h"], 0)),
                    ("TIV rangs 5-12 par file P5-P95 (s)", lambda r: f(g(r, "tiv_rangs_5_12_par_file_s", "p5")) + " - " + f(g(r, "tiv_rangs_5_12_par_file_s", "p95"))),
                    ("temps perdu, 4 premiers (s)", lambda r: f(r["temps_perdu_4_premiers_s"])),
                    ("passage rangs 1 / 2 / 3 / 4 (s depuis le vert)", lambda r: " / ".join(f(x, 1) for x in r["passage_moyen_par_rang_s"][:4])),
                    ("TIV rangs 2 / 3 / 4 (s)", lambda r: " / ".join(f(x) for x in r["tiv_moyen_par_rang_s"][1:4])),
                    ("pic d'acc. rangs 1 / 2 / 3 / 4-9 (m/s²)", lambda r: " / ".join(f(x) for x in r["pic_acc_moyen_par_rang_ms2"][:3]) + " / " + f(sum(r["pic_acc_moyen_par_rang_ms2"][3:9]) / 6)),
                    ("écart-type du pic, rangs 1 / 2 / 3 / 4-9 (m/s²)", lambda r: " / ".join(f(x) for x in r["pic_acc_ecart_type_par_rang_ms2"][:3]) + " / " + f(sum(r["pic_acc_ecart_type_par_rang_ms2"][3:9]) / 6) if r.get("pic_acc_ecart_type_par_rang_ms2") else "—"),
                    ("rang 1 : t(1 m/s) médiane (s)", lambda r: f(g(r, "rang1_t_1ms_s", "p50"))),
                    ("rang 1 : instant du pic médian (s)", lambda r: f(g(r, "rang1_t_pic_s", "p50"))),
                    ("jerk P95 (m/s³)", lambda r: f(g(r, "jerk_abs_ms3", "p95"))),
                    ("jerk P95 hors démarrage (m/s³)", lambda r: f(g(r, "jerk_abs_hors_demarrage_ms3", "p95"))),
                    ("jerk max nominal (hors démarrage, urgence, P-08) (m/s³)", lambda r: f(g(r, "jerk_abs_nominal_ms3", "p100"))),
                    ("collisions primaires / secondaires (graine 1)", lambda r: f(r.get("collisions"), 0) + " / " + f(r.get("collisions_secondaires"), 0) if r.get("collisions_secondaires") is not None else f(r.get("collisions"), 0))]:
        lignes.append([lab] + [fn(r) if r else "—" for _, r in cols])
    out.append(ecrire("S1_file_feu", ["Métrique"] + [LIB[c] for c, _ in cols], lignes))
    gr = s1.get("graines", [])
    if gr:
        out.append(ecrire("S1_graines", ["Graine", "TIV rangs 5-12 (s)", "collisions primaires", "collisions secondaires"],
                          [[str(x["graine"]), f(x["tiv_5_12_s"], 3), str(x["primaires"]), str(x["secondaires"])] for x in gr]))
    # ---------------- S1b
    s1b = R["S1b"]
    lignes = []
    for k in ("sans_H11", "avec_H11"):
        r = s1b[k]
        p = r["P_arret_2_5_3_5_5_5"]
        lignes.append([k.replace("_", " "), " / ".join(f(x) for x in p), f(r["part_arrets"]), f(g(r, "decel_necessaire_arrets_ms2", "p50")),
                       f(g(r, "decel_max_appliquee_arrets_ms2", "p50")) + " / " + f(g(r, "decel_max_appliquee_arrets_ms2", "p95")),
                       f(100 * r["part_au_rouge_parmi_presents"], 1), f(100 * r["part_au_rouge_parmi_passants"], 1), f(r["collisions"], 0)])
    out.append(ecrire("S1b_jaune", ["Variante", "P(arrêt) à TTL 2,5 / 3,5 / 5,5 s", "part d'arrêts", "décél. nécessaire médiane",
                                    "décél. max médiane / P95", "% au rouge (présents)", "% au rouge (passants)", "collisions"], lignes))
    cl = list(s1b["sans_H11"]["passage_au_rouge_par_classe_TTL"])
    lignes = [[k.replace("_", " ")] + [f(100 * s1b[k]["passage_au_rouge_par_classe_TTL"][c]["part_au_rouge"], 1) for c in cl]
              + [f(100 * s1b[k]["part_au_rouge_TTL_0_4"], 1), f(100 * s1b[k]["part_au_rouge_TTL_0_5"], 1), f(100 * s1b[k]["part_au_rouge_parmi_presents"], 1)]
              for k in ("sans_H11", "avec_H11")]
    out.append(ecrire("S1b_rouge_par_TTL", ["Variante"] + [f"% au rouge, TTL {c}" for c in cl] + ["TTL ≤ 4 s", "TTL ≤ 5 s", "TTL ≤ 8 s"], lignes))
    # ---------------- S2
    s2 = R["S2"]
    lignes = []
    for k, r in s2["modele"].items():
        rg = r["rangs"]
        cond = lambda i: rg[str(i)]["taux_collision_primaire_meneur_intact"]  # noqa: E731
        lignes.append([f"Notre modèle — {k.replace('_', ', meneur ')} m/s²",
                       f(100 * r["taux_collision_primaire_rangs_1_10"], 1) + " (brut " + f(100 * r["taux_collision_brut_rangs_1_10"], 1) + ")",
                       " / ".join(f(100 * cond(i), 1) if cond(i) is not None else "—" for i in (1, 2, 3, 5))
                       + " (n meneur intact rang 2 : " + str(rg["2"]["n_meneur_intact"]) + ")",
                       " / ".join(f(100 * rg[str(i)]["taux_collision_brut"], 0) for i in (1, 2, 3, 5)),
                       f(g(rg, "1", "delai_feux_stop_s", "p50")), f(g(rg, "1", "decel_max_avant_choc_ms2", "p50")), f(g(rg, "1", "gap_min_m", "p50"))])
    variantes = [(dm, c, s2.get(f"sumo_{dm}", {}).get(c)) for dm in ("6.68", "4.0") for c in CFG_S2]
    variantes += [("6.68", "krauss_nos_lois (meneur decel = 9, réglage v0.1)", (s2.get("sumo_6.68_meneur_decel9") or {}).get("krauss_nos_lois"))]
    for dm, c, r in variantes:
        if not r:
            continue
        rg = r["rangs"]
        lignes.append([f"{LIB.get(c, 'SUMO ' + c)} — meneur {dm} m/s²", f(r["collisions"], 0) + " collisions (" + str(r["pelotons_avec_collision"]) + " pelotons / " + str(r["n_rep"]) + ")",
                       "—", " / ".join(f(100 * (rg[str(i)]["taux_collision_brut"] or 0), 0) for i in (1, 2, 3, 5)),
                       f(g(rg, "1", "delai_feux_stop_s", "p50")), f(g(rg, "1", "decel_max_ms2", "p50")), f(g(rg, "1", "gap_min_m", "p50"))])
    out.append(ecrire("S2_freinage", ["Configuration", "% collisions primaires rangs 1-10 (brut)", "% primaires, meneur intact : rangs 1 / 2 / 3 / 5",
                                      "% bruts rangs 1 / 2 / 3 / 5", "délai feux stop rang 1, médiane (s)",
                                      "décél. max rang 1 avant choc, médiane (m/s²)", "écart min rang 1, médiane (m)"], lignes))
    # ---------------- S3
    s3 = R["S3"]
    cols = [("modele", s3["modele"]), ("modele_sans_H10", s3.get("modele_sans_H10"))] + [(c, s3["sumo"].get(c)) for c in CFG if c in s3["sumo"]]
    cols += [(c + "_brut", (s3.get("sumo_transfert_brut") or {}).get(c)) for c in ("krauss_nos_lois", "eidm_nos_lois") if (s3.get("sumo_transfert_brut") or {}).get(c)]
    lib3 = dict(LIB, modele_sans_H10="Notre modèle sans H-10", krauss_nos_lois="Krauss nos lois (impatience 0,5)",
                eidm_nos_lois="EIDM nos lois (impatience 0,5)", krauss_nos_lois_brut="Krauss nos lois, transfert brut",
                eidm_nos_lois_brut="EIDM nos lois, transfert brut")
    lignes = []
    for lab, fn in [("conducteurs analysés", lambda r: f(r["n_conducteurs"], 0)),
                    ("t_c MLE, arrêtés : moyenne ± é.-t. (s)", lambda r: (f(g(r, "creneau_critique_mle_arretes", "moyenne_s"), 1) + " ± " + f(g(r, "creneau_critique_mle_arretes", "ecart_type_s"), 1)) if r.get("creneau_critique_mle_arretes") else "—"),
                    ("t_c MLE, créneaux seuls (s)", lambda r: (f(g(r, "creneau_critique_mle_creneaux_seuls", "moyenne_s"), 1) + " ± " + f(g(r, "creneau_critique_mle_creneaux_seuls", "ecart_type_s"), 1)) if r.get("creneau_critique_mle_creneaux_seuls") else "—"),
                    ("t_c MLE, arrêtés, depuis l'arrêt, entrée (s)", lambda r: (f(g(r, "creneau_critique_mle_arretes_depuis_arret", "moyenne_s"), 1) + " ± " + f(g(r, "creneau_critique_mle_arretes_depuis_arret", "ecart_type_s"), 1)) if r.get("creneau_critique_mle_arretes_depuis_arret") else "—"),
                    ("t_c MLE, arrêtés, depuis l'arrêt, point de conflit (s)", lambda r: (f(g(r, "creneau_critique_mle_arretes_depuis_arret_point_conflit", "moyenne_s"), 1) + " ± " + f(g(r, "creneau_critique_mle_arretes_depuis_arret_point_conflit", "ecart_type_s"), 1)) if r.get("creneau_critique_mle_arretes_depuis_arret_point_conflit") else "—"),
                    ("attente à la ligne P50 / P95 (s)", lambda r: f(g(r, "attente_s", "p50"), 1) + " / " + f(g(r, "attente_s", "p95"), 1)),
                    ("arrivées libres : n", lambda r: f(g(r, "arrivees_libres", "n"), 0)),
                    ("arrivées libres : arrêt / glissé / sans (%)", lambda r: " / ".join(f(100 * (g(r, "arrivees_libres", k) or 0), 0) for k in ("part_arret_complet_v_inf_0_1", "part_glisse_0_1_a_3", "part_sans_arret_sup_3")) if r.get("arrivees_libres") else "—"),
                    ("décél. min des prioritaires P1 / P5 (m/s²)", lambda r: f(g(r, "a_min_prioritaires_ms2", "p1")) + " / " + f(g(r, "a_min_prioritaires_ms2", "p5"))),
                    ("prioritaires freinant > leur b (%)", lambda r: f(100 * r["part_prioritaires_freinage_sup_b"], 2) if r.get("part_prioritaires_freinage_sup_b") is not None else "—"),
                    ("collisions", lambda r: f(r.get("collisions"), 0))]:
        lignes.append([lab] + [fn(r) if r else "—" for _, r in cols])
    out.append(ecrire("S3_stop", ["Métrique"] + [lib3[c] for c, _ in cols], lignes))
    # ---------------- S4 / S5
    for nom, cle, mets in (("S4_courbe", "S4", [("v au milieu P15 / P50 / P85 (km/h)", "v_milieu_kmh", ("p15", "p50", "p85"), 1),
                                                  ("a_lat au milieu P50 / P95 (m/s²)", "a_lat_milieu_ms2", ("p50", "p95"), 2),
                                                  ("début du freinage avant la courbe, P50 (m)", "debut_freinage_m", ("p50",), 0),
                                                  ("décél. max d'approche P50 / P95 (m/s²)", "decel_max_approche_ms2", ("p50", "p95"), 2),
                                                  ("jerk P95 par véhicule, médiane (m/s³)", "jerk_p95", ("p50",), 2)]),
                           ("S5_ralentisseur", "S5", [("v au dispositif, moyenne ± é.-t. (km/h)", "v_ralentisseur_kmh", ("moyenne", "ecart_type"), 1),
                                                      ("v 10-20 m en aval : moyenne ± é.-t. ; V85 (km/h)", "v_aval_10_20m_kmh", ("moyenne", "ecart_type", "p85"), 1),
                                                      ("début du freinage avant le dispositif, P50 (m)", "debut_freinage_m", ("p50",), 0),
                                                      ("décél. max d'approche P50 / P95 (m/s²)", "decel_max_approche_ms2", ("p50", "p95"), 2)])):
        S = R[cle]
        cols = [("modele", S["modele"])] + ([("modele_variante_bruxelles", S["modele_variante_bruxelles"])] if "modele_variante_bruxelles" in S else []) + list(S["sumo"].items())
        lignes = []
        for lab, k, ps, n in mets:
            lignes.append([lab] + [" / ".join(f(g(r, k, p), n) for p in ps) if r and r.get(k) else "—" for _, r in cols])
        noms = [("Notre modèle, loi bruxelloise" if c == "modele_variante_bruxelles" else "Notre modèle") if "|" not in c
                else LIB[c.split("|")[0]] + " — " + c.split("|")[1] for c, _ in cols]
        out.append(ecrire(nom, ["Métrique"] + noms, lignes))
    print("\n\n".join(out))


if __name__ == "__main__":
    main()
