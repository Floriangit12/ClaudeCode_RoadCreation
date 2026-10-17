"""Lit le CSV HDV de l'AEE sur l'entrée standard et garde les lignes immatriculées en France
(colonnes utiles seulement). usage: curl URL | python -I hdv_filtre_fr.py sortie.csv compte_pays.json"""
import sys, csv, io, json, collections
csv.field_size_limit(10**8)
src = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig", errors="replace", newline="")
r = csv.reader(src)
hdr = next(r)
base = ["OEM_Make", "OEM_VehicleGroup", "OEM_VehicleSubgroup", "OEM_ZeroEmissionVehicle", "OEM_HybridElectricHDV",
        "OEM_VocationalVehicle", "OEM_Engine_FuelType", "OEM_GrossVehicleMass_t", "MS_RegistrationCountry",
        "MS_VehicleCategoryCode", "MS_BodyworkCode", "MS_TPMLM", "MS_RegistrationDateClean_YYYYMMDD", "LegislativeClass",
        "CurbMassChassis_kg", "AxleConfiguration", "SleeperCab", "MS_MaximumSpeed_kmh", "MS_NumberOfAxles",
        "MS_AveragePayload_t", "Engine_RatedPower_kw", "Engine_Displacement_ltr", "Gearbox_TransmissionType",
        "Gearbox_GearsCount", "Retarder_RetarderType", "AirDrag_CdxA_range"]
suff = ("_Mission", "_TotalVehicleMass_kg", "_Payload_kg", "_AverageSpeed_kmh", "_MaxAcceleration_ms2", "_MaxDeceleration_ms2")
keep = [c for c in base if c in hdr] + [c for c in hdr if c.endswith(suff) and c not in base]
idx = [hdr.index(c) for c in keep]
ic = hdr.index("MS_RegistrationCountry")
cnt = collections.Counter(); n = 0; nfr = 0
with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(keep)
    for row in r:
        n += 1
        if len(row) <= ic: continue
        c = row[ic]; cnt[c] += 1
        if c in ("FR", "France", "FRANCE"):
            nfr += 1; w.writerow([row[i] if i < len(row) else "" for i in idx])
json.dump({"lignes": n, "lignes_fr": nfr, "pays": cnt.most_common()}, open(sys.argv[2], "w"), indent=1)
print(n, nfr)
