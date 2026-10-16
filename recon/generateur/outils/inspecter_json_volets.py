# -*- coding: utf-8 -*-
"""Inspecte la structure des JSON de règles des volets 08 à 14 de D:\\DocRoute (lecture seule)."""
import json
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(r"D:\DocRoute")
FICHIERS = [
    "08_Marquages_Geometrie_IISR7/marquages_iisr7.json",
    "09_Signalisation_Verticale_Feux/signalisation_implantation.json",
    "09_Signalisation_Verticale_Feux/feux.json",
    "10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/regles_geometrie_voirie.json",
    "11_Cycles_Pietons_Accessibilite_TC/regles_modes_actifs.json",
    "12_Modele_Voie_OSM_Generateurs/inference_osm_profil.json",
    "13_Observations_Panoramax_Isere/regles_pratiques_locales.json",
    "14_Assets_Route_Statics/regles_assets_route.json",
]


def court(v, n=300):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "..."


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    seulement = sys.argv[1:]
    for rel in FICHIERS:
        if seulement and not any(s in rel for s in seulement):
            continue
        p = RACINE / rel
        d = json.loads(p.read_text(encoding="utf-8"))
        print("=" * 100)
        print(rel, p.stat().st_size)
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, list):
                    print(f"  [{k}] liste de {len(v)}")
                elif isinstance(v, dict):
                    print(f"  [{k}] dict de {len(v)} clés : {list(v)[:12]}")
                else:
                    print(f"  [{k}] = {court(v, 150)}")
        else:
            print("  liste de", len(d))
        # trouver la liste des règles
        cands = []
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
                    cands.append(k)
        for k in cands:
            regles = d[k]
            champs = Counter()
            for r in regles:
                champs.update(r.keys())
            print(f"  >> {k}: {len(regles)} éléments ; champs : {dict(champs)}")
            print("     exemple :", court(regles[0], 900))
            ids = [r.get("id") for r in regles]
            print("     doublons d'id :", [i for i, c in Counter(ids).items() if c > 1][:10])
            prefixes = Counter(str(i).rsplit("-", 1)[0] for i in ids)
            print("     préfixes :", dict(prefixes))


if __name__ == "__main__":
    sys.exit(main())
