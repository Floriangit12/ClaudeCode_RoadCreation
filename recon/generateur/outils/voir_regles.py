# -*- coding: utf-8 -*-
"""Affiche en entier des règles des volets : python -I voir_regles.py 08:SAS-01 11:MA-CAR-002 ..."""
import json
import sys
from pathlib import Path

RACINE = Path(r"D:\DocRoute")
FICHIERS = {
    "08": ("08_Marquages_Geometrie_IISR7/marquages_iisr7.json", ["regles", "pratiques_locales"]),
    "09S": ("09_Signalisation_Verticale_Feux/signalisation_implantation.json", ["regles"]),
    "09F": ("09_Signalisation_Verticale_Feux/feux.json", ["regles"]),
    "10": ("10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/regles_geometrie_voirie.json", ["regles"]),
    "11": ("11_Cycles_Pietons_Accessibilite_TC/regles_modes_actifs.json", ["regles"]),
    "12": ("12_Modele_Voie_OSM_Generateurs/inference_osm_profil.json", ["regles"]),
    "13": ("13_Observations_Panoramax_Isere/regles_pratiques_locales.json", ["regles"]),
    "14": ("14_Assets_Route_Statics/regles_assets_route.json", ["regles"]),
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cache = {}
    for arg in sys.argv[1:]:
        v, i = arg.split(":", 1)
        if v not in cache:
            rel, cles = FICHIERS[v]
            d = json.loads((RACINE / rel).read_text(encoding="utf-8"))
            cache[v] = {r["id"]: r for k in cles for r in d[k]}
        r = cache[v].get(i)
        print(f"--- {v}:{i}")
        print(json.dumps(r, ensure_ascii=False) if r else "INTROUVABLE")


if __name__ == "__main__":
    main()
