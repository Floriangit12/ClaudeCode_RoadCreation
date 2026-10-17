"""Statistiques des poids lourds neufs immatriculés en France 2019-2023 (extrait AEE, règlement (UE) 2018/956).
usage: python -E -P hdv_stats.py extrait.csv sortie.json"""
import sys, json
import pandas as pd, numpy as np
d = pd.read_csv(sys.argv[1], low_memory=False)
d = d[d["OEM_VehicleGroup"].notna()].copy()
d["groupe"] = d["OEM_VehicleGroup"].astype(int)
Q = [0.05, 0.15, 0.25, 0.5, 0.75, 0.85, 0.95]
def stats(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0: return None
    return {"n": int(len(s)), "moyenne": round(float(s.mean()), 3), "ecart_type": round(float(s.std()), 3),
            **{f"p{int(q*100)}": round(float(s.quantile(q)), 3) for q in Q}}
out = {"source": "AEE, Monitoring of CO2 emissions from heavy-duty vehicles 2019-2023 (extrait du 24/04/2025), lignes MS_RegistrationCountry=FR appariées OEM",
       "n_total_fr_apparies": int(len(d)), "groupes": {}}
for g, x in d.groupby("groupe"):
    r = {"n": int(len(x)),
         "configuration_essieux": x["AxleConfiguration"].value_counts().to_dict(),
         "energie": x["OEM_Engine_FuelType"].value_counts().to_dict(),
         "zero_emission": int((x["OEM_ZeroEmissionVehicle"].astype(str).isin(["1", "True", "true"])).sum()),
         "puissance_moteur_kW": stats(x["Engine_RatedPower_kw"]),
         "masse_chassis_cabine_kg": stats(x["CurbMassChassis_kg"]),
         "PTAC_kg_MS": stats(x["MS_TPMLM"]),
         "masse_brute_constructeur_t": stats(x["OEM_GrossVehicleMass_t"]),
         "vitesse_max_kmh": stats(x["MS_MaximumSpeed_kmh"]),
         "CdxA_classe": x["AirDrag_CdxA_range"].value_counts().head(12).to_dict(),
         "boite": x["Gearbox_TransmissionType"].value_counts().to_dict(),
         "missions": {}}
    for m in ["LHL", "LHR", "RDL", "RDR", "UDL", "UDR", "REL", "RER", "COL", "COR", "MUL", "MUR"]:
        col = f"{m}_TotalVehicleMass_kg"
        if col in x and pd.to_numeric(x[col], errors="coerce").notna().sum() > 0:
            mt = pd.to_numeric(x[col], errors="coerce"); p = pd.to_numeric(x["Engine_RatedPower_kw"], errors="coerce")
            r["missions"][m] = {"nom": str(x[f"{m}_Mission"].dropna().iloc[0]) if x[f"{m}_Mission"].notna().any() else None,
                                "masse_totale_kg": stats(mt), "charge_utile_kg": stats(x[f"{m}_Payload_kg"]),
                                "puissance_masse_kW_t": stats(p / (mt / 1000.0)),
                                "acc_max_sim_ms2": stats(x[f"{m}_MaxAcceleration_ms2"]),
                                "dec_max_sim_ms2": stats(x[f"{m}_MaxDeceleration_ms2"])}
    out["groupes"][str(g)] = r
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for g, r in out["groupes"].items():
    print(g, r["n"], r["configuration_essieux"], "P50 kW", r["puissance_moteur_kW"]["p50"] if r["puissance_moteur_kW"] else None,
          "masse châssis p50", r["masse_chassis_cabine_kg"]["p50"] if r["masse_chassis_cabine_kg"] else None, list(r["missions"].keys()))
