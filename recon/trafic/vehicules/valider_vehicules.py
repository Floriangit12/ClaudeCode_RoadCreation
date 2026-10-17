"""Calage et validation du modèle longitudinal (dynamique.py) sur les mesures ADAC.

Usage :
  python recon/trafic/vehicules/valider_vehicules.py [--mesures CHEMIN] [--sortie CHEMIN]

Étapes (reproductibles ; les seules valeurs fixées ici sont les HYPOTHESES listées) :
 1. chaque voiture testée par l'ADAC devient un Vehicule (masse UE, puissance, v_max constructeur ;
    CxS estimé) ;
 2. plafond basse vitesse a_lancement :
      - électriques et hybrides : = 15-30 km/h mesuré (couple quasi constant au démarrage) ;
      - thermiques à boîte manuelle : calé sur le 0-100 km/h constructeur (départ arrêté, régime
        élevé) ; le 15-30 km/h mesuré (reprise en 2e à bas régime) est rapporté à part
        (« a_reprise_bas_regime ») ;
 3. k_puissance calé voiture par voiture sur la reprise 60-100 km/h mesurée (plafond inactif à ces
    vitesses), puis contrôlé sur la reprise 80-120 km/h (mesure NON utilisée pour le calage) ;
 4. validation croisée « un exclu » : pour chaque voiture, paramètres = médianes des autres voitures
    de la même famille ; prédiction de 60-100, 80-120 et 0-100 ; erreurs relatives ;
 5. freinage : décélération moyenne équivalente des 100-0 km/h mesurés ; contrôle ONU R13-H.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dynamique import (Vehicule, a_lancement_pour_temps, k_pour_temps,  # noqa: E402
                       mfdd_depuis_distance, distance_reglementaire_R13H)

DOC = Path(r"D:\DocRoute\17_Modele_Vehicules_Conducteurs\01_Vehicules\donnees")

HYPOTHESES = {
    "masse": "masse d'essai = masse UE en ordre de marche (conducteur 75 kg inclus) ; l'équipement de mesure n'est pas ajouté (absorbé par k)",
    "cxs": "CxS = 0,248 x largeur x hauteur : facteur calé sur la seule valeur publiée dans les PDF ADAC (208 : S = 2,1 m², Cx = 0,295, soit 0,62 m² pour 1,745 x 1,430 m) ; estimation, sensibilité +-20 % rapportée",
    "c_roulement": "0,0085 : milieu de la classe C de l'étiquette pneus UE (règlement (UE) 2020/740, annexe I, C1 : 7,8 à 9,0 N/kN) ; estimation",
    "a_lancement_sans_mesure": "médiane de la famille quand le 15-30 km/h n'est pas publié (Model Y)",
}
FACTEUR_CXS = 0.62 / (1.745 * 1.430)
CAP_LIBRE = 50.0  # m/s^2 : plafond désactivé


def vehicule_depuis_mesure(r: dict, facteur_cxs: float = FACTEUR_CXS) -> Vehicule:
    c = r["constructeur"]
    return Vehicule(nom=r["id"], masse_kg=c["masse_UE_kg"], puissance_kW=c["puissance_kW"],
                    a_lancement=CAP_LIBRE, cxs_m2=facteur_cxs * c["largeur_mm"] / 1000 * c["hauteur_mm"] / 1000,
                    v_max_kmh=c["v_max_kmh"], meta={"famille": r["motorisation"]})


def a_15_30(r):
    t = r["mesures"].get("t_15_30_s")
    return (30 - 15) / 3.6 / t if t else None


def erreur(pred, mes):
    return None if pred is None or mes is None else (pred - mes) / mes


def resume(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not xs:
        return None
    return {"n": len(xs), "moyenne": round(st.mean(xs), 4), "ecart_type": round(st.pstdev(xs), 4),
            "abs_moyenne": round(st.mean(abs(x) for x in xs), 4), "min": round(min(xs), 4), "max": round(max(xs), 4)}


A_ADHERENCE_TRACTION = 1.0 * 9.81 * 0.6  # mu_sec = 1,0 x g x 60 % de la masse sur l'essieu moteur (estimation)


def calage_individuel(r):
    """Renvoie un dict de paramètres calés pour une voiture.
    - k_reprise : calé sur 60-100 km/h mesuré (rapport imposé ou position D) ;
    - thermique manuelle : k_depart calé sur 0-100 constructeur avec plafond = adhérence (départ
      arrêté, rapports optimaux) ; a_lancement = plafond d'adhérence ;
    - électrique / hybride : a_lancement = 15-30 mesuré, k_depart = k_reprise (un seul k)."""
    v = vehicule_depuis_mesure(r)
    m, c = r["mesures"], r["constructeur"]
    k_rep = k_pour_temps(v, 60, 100, m["t_60_100_s"])          # plafond libre à 60-100 km/h
    if r["motorisation"] == "thermique_manuelle":
        v.a_lancement = A_ADHERENCE_TRACTION
        k_dep = k_pour_temps(v, 0, 100, c["t_0_100_s"])
        return {"k_reprise": k_rep, "k_depart": k_dep, "a_lancement": A_ADHERENCE_TRACTION}
    return {"k_reprise": k_rep, "k_depart": k_rep, "a_lancement": a_15_30(r)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesures", default=str(DOC / "adac_mesures.json"))
    ap.add_argument("--sortie", default=str(DOC / "validation_dynamique.json"))
    a = ap.parse_args(argv)
    data = json.load(open(a.mesures, encoding="utf-8"))["vehicules"]

    cal = {r["id"]: calage_individuel(r) for r in data}
    for r in data:  # véhicules sans 15-30 publié : médiane de la famille
        if cal[r["id"]]["a_lancement"] is None:
            autres = [cal[x["id"]]["a_lancement"] for x in data
                      if x["motorisation"] == r["motorisation"] and cal[x["id"]]["a_lancement"] is not None]
            cal[r["id"]]["a_lancement"] = st.median(autres)
            cal[r["id"]]["a_lancement_origine"] = "médiane famille"

    res = []
    for r in data:
        fam = r["motorisation"]
        m, c = r["mesures"], r["constructeur"]
        ci = cal[r["id"]]
        autres = [cal[x["id"]] for x in data if x["motorisation"] == fam and x["id"] != r["id"]]
        med = (lambda key: st.median([x[key] for x in autres])) if autres else (lambda key: ci[key])
        kr_f, kd_f = med("k_reprise"), med("k_depart")
        a_f = ci["a_lancement"] if fam != "thermique_manuelle" else A_ADHERENCE_TRACTION
        v = vehicule_depuis_mesure(r)
        # --- contrôle : k calé sur 60-100 reproduit-il 80-120 ? (mesure non utilisée au calage)
        k80 = k_pour_temps(vehicule_depuis_mesure(r), 80, 120, m["t_80_120_s"]) if m.get("t_80_120_s") else None
        v.k_puissance, v.a_lancement = ci["k_reprise"], ci["a_lancement"]
        p80_i = v.temps_acceleration(80, 120) if m.get("t_80_120_s") else None
        sens = None
        if m.get("t_80_120_s"):
            cx0 = v.cxs_m2
            v.cxs_m2 = cx0 * 1.2; t_hi = v.temps_acceleration(80, 120)
            v.cxs_m2 = cx0 * 0.8; t_lo = v.temps_acceleration(80, 120)
            v.cxs_m2 = cx0
            sens = {"t_80_120_cxs_plus20": round(t_hi, 2), "t_80_120_cxs_moins20": round(t_lo, 2)}
        # --- validation croisée un exclu
        v.k_puissance, v.a_lancement = kr_f, a_f
        p60 = v.temps_acceleration(60, 100)
        p80 = v.temps_acceleration(80, 120) if m.get("t_80_120_s") else None
        v.k_puissance = kd_f
        p0 = v.temps_acceleration(0, 100)
        p50 = v.temps_acceleration(0, 50)
        mfdd = mfdd_depuis_distance(100, m["d_100_0_m"])
        res.append({
            "id": r["id"], "famille": fam, "masse_kg": v.masse_kg, "puissance_kW": v.puissance_kW,
            "puissance_masse_W_kg": round(1000 * v.puissance_kW / v.masse_kg, 1),
            "cxs_m2_estime": round(v.cxs_m2, 3),
            "k_reprise_cale_60_100": round(ci["k_reprise"], 3), "k_cale_80_120": round(k80, 3) if k80 else None,
            "k_depart_cale_0_100": round(ci["k_depart"], 3),
            "a_lancement_ms2": round(ci["a_lancement"], 2),
            "a_lancement_origine": ci.get("a_lancement_origine", "plafond d'adhérence (estimation)" if fam == "thermique_manuelle" else "15-30 km/h mesuré"),
            "a_reprise_bas_regime_15_30_ms2": round(a_15_30(r), 2) if a_15_30(r) else None,
            "parametres_un_exclu": {"k_reprise": round(kr_f, 3), "k_depart": round(kd_f, 3), "a_lancement": round(a_f, 2)},
            "t_60_100": {"mesure": m["t_60_100_s"], "predit_un_exclu": round(p60, 2), "erreur_rel": round(erreur(p60, m["t_60_100_s"]), 3)},
            "t_80_120": None if not m.get("t_80_120_s") else {
                "mesure": m["t_80_120_s"], "predit_un_exclu": round(p80, 2), "erreur_rel": round(erreur(p80, m["t_80_120_s"]), 3),
                "predit_k_individuel": round(p80_i, 2), "erreur_rel_k_individuel": round(erreur(p80_i, m["t_80_120_s"]), 3),
                "sensibilite_cxs": sens},
            "t_0_100": {"constructeur": c["t_0_100_s"], "predit_un_exclu": round(p0, 2), "erreur_rel": round(erreur(p0, c["t_0_100_s"]), 3)},
            "t_0_50_predit_un_exclu": round(p50, 2),
            "freinage": {"d_100_0_mesure_m": m["d_100_0_m"], "mfdd_equivalent_ms2": round(mfdd, 2),
                         "limite_R13H_m": round(distance_reglementaire_R13H(100), 1),
                         "conforme_R13H": m["d_100_0_m"] <= distance_reglementaire_R13H(100)},
        })

    familles = sorted({x["famille"] for x in res})
    synthese = {}
    for f in familles + ["toutes"]:
        R = [x for x in res if f == "toutes" or x["famille"] == f]
        synthese[f] = {
            "n": len(R),
            "k_reprise_cale_60_100": resume([x["k_reprise_cale_60_100"] for x in R]),
            "k_depart_cale_0_100": resume([x["k_depart_cale_0_100"] for x in R]),
            "k_cale_80_120": resume([x["k_cale_80_120"] for x in R]),
            "a_lancement_ms2": resume([x["a_lancement_ms2"] for x in R]),
            "a_reprise_bas_regime_15_30_ms2": resume([x["a_reprise_bas_regime_15_30_ms2"] for x in R]),
            "erreur_60_100_un_exclu": resume([x["t_60_100"]["erreur_rel"] for x in R]),
            "erreur_80_120_un_exclu": resume([x["t_80_120"]["erreur_rel"] for x in R if x["t_80_120"]]),
            "erreur_80_120_k_individuel": resume([x["t_80_120"]["erreur_rel_k_individuel"] for x in R if x["t_80_120"]]),
            "erreur_0_100_un_exclu": resume([x["t_0_100"]["erreur_rel"] for x in R]),
            "mfdd_equivalent_100_0": resume([x["freinage"]["mfdd_equivalent_ms2"] for x in R]),
        }
    out = {"hypotheses": HYPOTHESES, "facteur_cxs": round(FACTEUR_CXS, 4), "vehicules": res, "synthese": synthese}
    Path(a.sortie).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"{'id':16s} {'famille':23s} {'P/m':>5s} {'kRep':>6s} {'k80':>6s} {'kDep':>5s} {'60-100 mes/pred':>16s} {'80-120 mes/pred':>16s} {'0-100 cons/pred':>16s} {'mfdd':>6s}")
    for x in res:
        t8 = x["t_80_120"]
        f8 = f"{t8['mesure']:5.1f}/{t8['predit_un_exclu']:5.2f}" if t8 else "      -     "
        k8 = f"{x['k_cale_80_120']:6.3f}" if x['k_cale_80_120'] else "     -"
        print(f"{x['id']:16s} {x['famille']:23s} {x['puissance_masse_W_kg']:5.1f} {x['k_reprise_cale_60_100']:6.3f} {k8} {x['k_depart_cale_0_100']:5.2f} "
              f"     {x['t_60_100']['mesure']:5.1f}/{x['t_60_100']['predit_un_exclu']:5.2f}      {f8}      {x['t_0_100']['constructeur']:5.1f}/{x['t_0_100']['predit_un_exclu']:5.2f} {x['freinage']['mfdd_equivalent_ms2']:6.2f}")
    for f, s in synthese.items():
        print(f, {k: ((v["moyenne"], v["abs_moyenne"]) if isinstance(v, dict) else v) for k, v in s.items()})
    return out


if __name__ == "__main__":
    main()
