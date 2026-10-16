# -*- coding: utf-8 -*-
"""Liste compacte (id | sujet | condition | source) des règles des volets 08 à 14, pour la revue des doublons."""
import json
import sys
from pathlib import Path

RACINE = Path(r"D:\DocRoute")
VOLETS = [
    ("08", "08_Marquages_Geometrie_IISR7/marquages_iisr7.json", "regles"),
    ("08P", "08_Marquages_Geometrie_IISR7/marquages_iisr7.json", "pratiques_locales"),
    ("09S", "09_Signalisation_Verticale_Feux/signalisation_implantation.json", "regles"),
    ("09F", "09_Signalisation_Verticale_Feux/feux.json", "regles"),
    ("10", "10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/regles_geometrie_voirie.json", "regles"),
    ("11", "11_Cycles_Pietons_Accessibilite_TC/regles_modes_actifs.json", "regles"),
    ("12", "12_Modele_Voie_OSM_Generateurs/inference_osm_profil.json", "regles"),
    ("13", "13_Observations_Panoramax_Isere/regles_pratiques_locales.json", "regles"),
    ("14", "14_Assets_Route_Statics/regles_assets_route.json", "regles"),
]


def src(s):
    if isinstance(s, dict):
        return f"{s.get('doc')} p.{s.get('page')} {s.get('article') or s.get('figure') or ''}".strip()
    return str(s)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    filtre = sys.argv[1:] or None
    for code, rel, cle in VOLETS:
        if filtre and code not in filtre:
            continue
        d = json.loads((RACINE / rel).read_text(encoding="utf-8"))
        for r in d[cle]:
            vals = json.dumps(r.get("valeurs"), ensure_ascii=False)
            print(f"{code}|{r['id']}|{r.get('sujet')}|{str(r.get('condition'))[:70]}|{vals[:110]}|{src(r.get('source'))[:70]}")


if __name__ == "__main__":
    main()
