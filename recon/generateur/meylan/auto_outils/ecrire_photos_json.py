"""Écrit meylan/<site>/photos.json (versionné) : identifiants, date, auteur, licence, position, cap et constats des
photos Panoramax regardées pour le site. AUCUNE image ni chemin d'image versionné : seulement les noms des tuiles
regardées (elles restent dans recon/out/generateur/meylan/<site>/photos_non_versionnees/, ignoré par git).

    python recon/generateur/meylan/auto_outils/ecrire_photos_json.py --site auto_a41_section_courante \
        --constats recon/out/generateur/meylan/auto_a41_section_courante/constats_photos.json

constats_photos.json : {"<id8>": {"tuiles_regardees": ["l+0000.0_t-10.0", ...], "constats": ["...", ...],
                                  "role": "section courante, sens est"}, ...}
"""
import argparse
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "recon" / "out" / "generateur" / "meylan"
MEYLAN = RACINE / "recon" / "generateur" / "meylan"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--constats", required=True)
    ap.add_argument("--meta-site", nargs="*", default=[], help="autres dossiers de sortie où chercher les métadonnées")
    a = ap.parse_args()
    meta = {}
    for s in [a.site] + a.meta_site:
        f = OUT / s / "photos_non_versionnees" / "photos_meta.json"
        if f.exists():
            meta.update({k: dict(v, site=s) for k, v in json.load(open(f, encoding="utf-8")).items()})
    cons = json.load(open(a.constats, encoding="utf-8"))
    photos = []
    for court, c in cons.items():
        m = [v for k, v in meta.items() if k.startswith(court)]
        if len(m) != 1:
            raise SystemExit("photo %s : %d métadonnées" % (court, len(m)))
        m = m[0]
        r = m.get("route_osm") or {}
        photos.append({
            "id": m["id"], "date": m["date"], "auteur": m["auteur"], "licence": m["licence"],
            "source": "Panoramax (api.panoramax.xyz), photo de tiers non versionnée",
            "lon": round(m["lon"], 7), "lat": round(m["lat"], 7),
            "x_l93": m["x_l93"], "y_l93": m["y_l93"], "azimut_deg": m["azimut"], "camera": m["camera"].strip(),
            "taille_px": m["taille"], "route_osm": {k: r.get(k) for k in ("way", "highway", "ref", "name")},
            "role": c.get("role", ""),
            "tuiles_regardees": c.get("tuiles_regardees", []),
            "dossier_tuiles_non_versionne": "recon/out/generateur/meylan/%s/photos_non_versionnees/%s"
                                            % (m.get("site", a.site), m["tuiles"].replace("\\", "/")),
            "constats": c.get("constats", []),
        })
    photos.sort(key=lambda p: (p["date"], p["id"]))
    doc = {"site": a.site,
           "licence_photos": "CC-BY-SA 4.0 (auteurs ci-dessous) ; photos et tuiles jamais versionnées ni diffusées",
           "methode": "photos HD téléchargées par auto_outils/photos_site.py, découpées par recon/pcg/vision/decoupe.py "
                      "(équirectangulaire : vues perspectives de 1092 px, champ 68,25°, tangage −10° ou −35° ; plane : "
                      "tuiles de 1092 px, 20 % de recouvrement) ; seules les tuiles natives ont été regardées",
           "photos": photos}
    f = MEYLAN / a.site / "photos.json"
    f.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(len(photos), "photos ->", f)


if __name__ == "__main__":
    main()
