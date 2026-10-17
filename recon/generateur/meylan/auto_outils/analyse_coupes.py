"""Statistiques des coupes ortho (coupe_ortho.py) : position médiane des lignes attendues et des bords revêtus.

    python recon/generateur/meylan/auto_outils/analyse_coupes.py --site auto_a41_section_courante --nom a41_sc \
        --lignes "rive_tpc_N:3.4" "voie_N:7.0" "bau_N:10.5" --fenetre 0.6 --bords 14:16 -14:-16 --stations 30 80

Pour chaque ligne attendue (nom:t_nominal), on prend le pic de luminance le plus proche dans ± fenetre ; pour chaque
bord revêtu (t_interieur:t_exterieur), on cherche le premier t, en partant de l'intérieur, où l'indice de
végétation 2G − R − B dépasse --seuil-vert (herbe) ou la luminance chute de plus de --saut-lum (ombre, terre).
Écrit <site>/coupes/<nom>_stats.json et l'affiche.
"""
import argparse
import json
import statistics
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "recon" / "out" / "generateur" / "meylan"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--nom", required=True)
    ap.add_argument("--lignes", nargs="*", default=[])
    ap.add_argument("--fenetre", type=float, default=0.6)
    ap.add_argument("--bords", nargs="*", default=[])
    ap.add_argument("--seuil-vert", type=float, default=8.0)
    ap.add_argument("--stations", nargs="*", type=float, default=None)
    a = ap.parse_args()
    d = json.load(open(OUT / a.site / "coupes" / ("%s.json" % a.nom), encoding="utf-8"))
    coupes = [c for c in d["coupes"] if a.stations is None or c["station_m"] in a.stations]
    res = {"site": a.site, "coupes": a.nom, "stations": [c["station_m"] for c in coupes], "lignes": {}, "bords": {}}
    for spec in a.lignes:
        nom, t0 = spec.rsplit(":", 1)
        t0 = float(t0)
        vals = []
        for c in coupes:
            pk = [p for p in c["pics_lum"] if abs(p["t"] - t0) <= a.fenetre]
            if pk:
                vals.append(min(pk, key=lambda p: abs(p["t"] - t0))["t"])
        res["lignes"][nom] = {"t_nominal": t0, "n": len(vals), "valeurs": vals,
                              "mediane": round(statistics.median(vals), 2) if vals else None,
                              "ecart_type": round(statistics.pstdev(vals), 2) if len(vals) > 1 else None}
    for spec in a.bords:
        ti, te = [float(v) for v in spec.split(":")]
        vals = []
        for c in coupes:
            prof = c["profil_t_lum_vert_sat_pas05"]
            pts = sorted(prof, key=lambda r: abs(r[0] - ti))
            sens = 1 if te > ti else -1
            ligne = [r for r in prof if (r[0] - ti) * sens >= 0 and (te - r[0]) * sens >= 0]
            ligne.sort(key=lambda r: abs(r[0] - ti))
            for r in ligne:
                if r[2] > a.seuil_vert:
                    vals.append(r[0])
                    break
        res["bords"]["%s:%s" % (ti, te)] = {"n": len(vals), "valeurs": vals,
                                            "mediane": round(statistics.median(vals), 2) if vals else None,
                                            "ecart_type": round(statistics.pstdev(vals), 2) if len(vals) > 1 else None}
    f = OUT / a.site / "coupes" / ("%s_stats.json" % a.nom)
    f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in res["lignes"].items():
        print("%-14s t=%s ± %s (n=%d)" % (k, v["mediane"], v["ecart_type"], v["n"]))
    for k, v in res["bords"].items():
        print("bord %-12s t=%s ± %s (n=%d)" % (k, v["mediane"], v["ecart_type"], v["n"]))


if __name__ == "__main__":
    main()
