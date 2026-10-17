#!/usr/bin/env python
"""Relevé Meylan (lot A) : reporte les constats rédigés à la main dans photos.json et mesures.json d'un site.

  python -I annoter.py SITE SPEC.json

SPEC.json (écrit pendant l'analyse, hors dépôt) :
  {"etat_decrit": "...",                         → photos.json
   "photos": {"<id 8 car.>": {"tuiles": [...], "constats": [...]}},
   "coupes": [{"nom": ..., "segment": [x0, y0, x1, y1], "ou": ..., "bandes": [[nom, largeur, source], ...],
               "note": ...}],                    → mesures.json « coupes » (lecture des intersections plan_site.py coupe)
   "mesures_ortho": [...], "constats": [...], "sources_complementaires": [...]}   → mesures.json
Les identifiants de photo sont complétés depuis photos.json ; aucune image n'est écrite.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
VERS = RACINE / "recon/generateur/meylan"


def main():
    site, spec = sys.argv[1], json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    fp = VERS / site / "photos.json"
    ph = json.loads(fp.read_text(encoding="utf-8"))
    if "etat_decrit" in spec:
        ph["etat_decrit"] = spec["etat_decrit"]
    for court, c in spec.get("photos", {}).items():
        cible = [p for p in ph["photos"] if p["id"].startswith(court)]
        if not cible:
            sys.exit("photo %s absente de photos.json (pnx_site.py retenir)" % court)
        cible[0].update(c)
    fp.write_text(json.dumps(ph, ensure_ascii=False, indent=1), encoding="utf-8")
    fm = VERS / site / "mesures.json"
    me = json.loads(fm.read_text(encoding="utf-8"))
    for k in ("coupes", "mesures_ortho", "constats", "sources_complementaires", "giratoire", "notes"):
        if k in spec:
            me[k] = spec[k]
    fm.write_text(json.dumps(me, ensure_ascii=False, indent=1), encoding="utf-8")
    print(site, "photos.json et mesures.json mis à jour")


if __name__ == "__main__":
    main()
