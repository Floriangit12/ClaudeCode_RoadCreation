# -*- coding: utf-8 -*-
"""Recouvrements et raccords entre les sites de Meylan, mesurés sur les modèles compilés (lot N1).

    python -B recon/generateur/reseau/tests/recouvrements.py [DOSSIER_DES_COMPILATIONS]

Même mesure que la relecture de la préparation (RELECTURE_PREPARATION.md § 5.2, outils/recouvrements.py) : pour chaque
paire de routes de deux sites différents, longueur d'axe à moins de 6 m de l'autre (recouvrement) et distance entre
extrémités (raccord). Les axes viennent des modèles (Lambert-93, ligne de référence échantillonnée) : défaut
recon/out/generateur/reseau_n1/tests/sites/<site>/modele_voie.json (écrits par tester_reseau.py).
"""
import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Point

DEPOT = Path(__file__).resolve().parents[4]
base = Path(sys.argv[1]) if len(sys.argv) > 1 else DEPOT / "recon" / "out" / "generateur" / "reseau_n1" / "tests" / "sites"
axes = {}
for f in sorted(base.glob("*/modele_voie.json")):
    m = json.loads(f.read_text(encoding="utf-8"))
    axes[f.parent.name] = [(r["id"] + " " + (r.get("nom") or "")[:40], LineString([(p[0], p[1]) for p in
                            r["ligne_reference"]["geometrie"]])) for r in m["routes"] if r.get("categorie") != "anneau_giratoire"]
sys.stdout.reconfigure(encoding="utf-8")
lignes = []
sites = sorted(axes)
for i, s1 in enumerate(sites):
    for s2 in sites[i + 1:]:
        for n1, L1 in axes[s1]:
            for n2, L2 in axes[s2]:
                if L1.distance(L2) > 30:
                    continue
                lg = L1.intersection(L2.buffer(6.0)).length
                bouts = min(Point(a).distance(Point(b)) for a in (L1.coords[0], L1.coords[-1])
                            for b in (L2.coords[0], L2.coords[-1]))
                lignes.append((round(lg, 1), s1, n1, s2, n2, round(L1.distance(L2), 1), round(bouts, 2)))
print("commun_m | site 1 | route 1 | site 2 | route 2 | distance des axes | distance des bouts")
for x in sorted(lignes, reverse=True):
    print(" | ".join(map(str, x)))
