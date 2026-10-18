# -*- coding: utf-8 -*-
"""Planches d'ensemble de l'étape 2 (intégration) : une vignette « dessus » et une « conducteur » par scène.

    python recon/generateur/rendu/planches_etape2.py [--sortie recon/out/generateur]

Lit les rendus de fabriquer_generateur.py --complet (<scene>/rendus/dessus.png et la vue conducteur de la scène) et
écrit recon/out/generateur/catalogue_rendus/etape2_<k>.png (1092 px de large, ≤ 1092 px de haut, 4 scènes par fichier).
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
sys.path.insert(0, str(ICI))
import planches as PL  # noqa: E402

SCENES = [f"S{k:02d}" for k in range(1, 13)] + [
    "B01", "J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe",
    "J6_carrefour_complexe_2x2",
    "G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50", "G3_mini_giratoire_D20", "G4_giratoire_multivoie_D50",
    "A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres", "A3_bretelle_entree", "A4_bretelle_sortie"]
# J6 et G4 : scènes ajoutées par le lot « correction de l'étape 2 » (second carrefour complexe, giratoire multivoie)
CONDUCTEUR = (("conducteur_ouest_tag", "1,20 m, voie de tourne-à-gauche de l'artère ouest"),
              ("conducteur_carrefour", "1,20 m, voie entrante d'une branche"),
              ("conducteur_autoroute", "1,20 m, bretelle ou voie de droite"),
              ("conducteur", "1,20 m, voie de droite"))


def entrees(sortie):
    out = []
    for s in SCENES:
        d = Path(sortie) / s / "rendus"
        try:
            titre = json.loads((Path(sortie) / s / "modele_voie.json").read_text(encoding="utf-8"))["meta"].get("titre", "")
        except (OSError, KeyError, ValueError):
            titre = ""
        cond = next(((d / f"{n}.png", leg) for n, leg in CONDUCTEUR if (d / f"{n}.png").exists()), (None, ""))
        out.append((s, titre, d / "dessus.png", cond[0], cond[1]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sortie", default=str(DEPOT / "recon" / "out" / "generateur"))
    a = ap.parse_args()
    for f in sorted((Path(a.sortie) / "catalogue_rendus").glob("etape2_*.png")):
        f.unlink()
    fs = PL.planches_etape2(entrees(a.sortie), Path(a.sortie) / "catalogue_rendus")
    for f in fs:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
