"""Télécharge des photos Panoramax (HD) d'un site du lot B et les découpe en tuiles natives (≤ 1092 px) avec
recon/pcg/vision/decoupe.py. Photos et tuiles vont UNIQUEMENT sous
recon/out/generateur/meylan/<site>/photos_non_versionnees/ (jamais versionnées, CC-BY-SA).

    python recon/generateur/meylan/auto_outils/photos_site.py --site auto_a41_section_courante \
        --ids 3e0e4893 28b78e21 --tangages -35,-10

Les identifiants peuvent être abrégés (8 premiers caractères) : ils sont résolus dans le catalogue
(auto_travail_lotB/panoramax/catalogue_lotB.json). Une photo 360° (2:1) est découpée en vues perspectives
(`decoupe.py equirect`, champ réglé sur la résolution de la source) ; une photo plane en tuiles (`decoupe.py image`).
Le manifeste photos_meta.json (non versionné) garde id, date, auteur, licence, position, cap et dossier de tuiles.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "recon" / "out" / "generateur" / "meylan"
CATALOGUE = OUT / "auto_travail_lotB" / "panoramax" / "photos_par_axe.json"
DECOUPE = RACINE / "recon" / "pcg" / "vision" / "decoupe.py"
UA = "ClaudeCode_RoadCreation/1.0 (recherche voirie Meylan)"


def telecharger(url, f):
    if f.exists() and f.stat().st_size > 0:
        return
    for essai in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                f.write_bytes(r.read())
            return
        except Exception:
            if essai == 3:
                raise
            time.sleep(4 * (essai + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--tangages", default="-35,-10")
    ap.add_argument("--recouvrement", default="0.2")
    a = ap.parse_args()
    cat = json.load(open(CATALOGUE, encoding="utf-8"))
    base = OUT / a.site / "photos_non_versionnees"
    brut = base / "brut"
    brut.mkdir(parents=True, exist_ok=True)
    meta_f = base / "photos_meta.json"
    meta = json.load(open(meta_f, encoding="utf-8")) if meta_f.exists() else {}
    for court in a.ids:
        cands = [p for p in cat if p["id"].startswith(court)]
        if len(cands) != 1:
            sys.exit("identifiant %s : %d correspondances" % (court, len(cands)))
        p = cands[0]
        nom = "%s_%s" % (p["datetime"][:10], p["id"][:8])
        f = brut / (nom + ".jpg")
        telecharger(p["hd"], f)
        w, h = Image.open(f).size
        tu = base / "tuiles" / nom
        if not (tu / "tuiles.json").exists():
            if abs(w - 2 * h) <= 2:
                cmd = [sys.executable, str(DECOUPE), "equirect", str(f), str(tu), "--tangages=" + a.tangages,
                       "--recouvrement", a.recouvrement]
            else:
                cmd = [sys.executable, str(DECOUPE), "image", str(f), str(tu), "--recouvrement", a.recouvrement]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        meta[p["id"]] = {"id": p["id"], "date": p["datetime"], "auteur": p["auteur"], "licence": p["licence"],
                         "lon": p["lon"], "lat": p["lat"], "x_l93": p["x_l93"], "y_l93": p["y_l93"],
                         "azimut": p["azimut"], "camera": p["camera"], "taille": [w, h],
                         "route_osm": p.get("route"), "fichier": f.name, "tuiles": str(tu.relative_to(base))}
        print(nom, w, h, "->", tu.relative_to(OUT))
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
