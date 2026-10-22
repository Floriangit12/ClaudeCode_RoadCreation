# -*- coding: utf-8 -*-
"""Planches d'ensemble de l'étape 4 (intégration) : scène vitrine, ponts (lot « ouvrages ») et scènes enrichies de leur
signalisation verticale et de leurs feux (lot L6) ; une rangée par scène : légende | vue de dessus | seconde vue.

    python recon/generateur/rendu/planches_etape4.py [--sortie recon/out/generateur]

Lit les rendus de fabriquer_generateur.py --complet :
  - scène vitrine et scènes à ouvrages : <scene>/rendus/dessus.png et la vue oblique 3/4 (oblique.png) ou la vue du
    conducteur du lot L6 (l6_conducteur.png) ;
  - scènes enrichies par le lot L6 : <scene>/l6/rendus/dessus.png (signalisation posée) et l6_conducteur.png ;
et écrit recon/out/generateur/catalogue_rendus/etape4_<k>.png (1092 px de large, ≤ 1092 px de haut, 4 scènes par
fichier), plus etape4_vitrine_V01.png (planche de la scène vitrine, 3 vues).
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
sys.path.insert(0, str(ICI))
import planches as PL  # noqa: E402

VITRINE = "V01_demi_echangeur_voie_rapide"
OUVRAGES = ["D1_passage_superieur_autoroute", "D2_passage_inferieur_voie_rapide", "D3_viaduc_vallee_seche",
            "D4_pont_urbain_piste_cyclable"]
L6 = ["E01_entree_agglomeration", "J1_T_cedez", "J2_croix_stop", "J3_croix_feux", "J4_ilots_directionnel_separateurs",
      "J5_carrefour_complexe", "J6_carrefour_complexe_2x2", "G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50",
      "G3_mini_giratoire_D20", "G4_giratoire_multivoie_D50", "A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres",
      "A3_bretelle_entree", "A4_bretelle_sortie", "S07", "S08", "S10"]


def _titre(sortie, s):
    try:
        return json.loads((Path(sortie) / s / "modele_voie.json").read_text(encoding="utf-8"))["meta"].get("titre", "")
    except (OSError, KeyError, ValueError):
        return ""


def _ensemble(d, nom="manifest_rendus_l6.json"):
    try:
        return json.loads((Path(d) / nom).read_text(encoding="utf-8"))["cameras"]["l6_conducteur"]["ensemble"]
    except (OSError, KeyError, ValueError):
        return ""


def entrees(sortie):
    out = []
    d = Path(sortie) / VITRINE / "rendus"
    out.append((VITRINE, "SCÈNE VITRINE imaginée — " + _titre(sortie, VITRINE), d / "dessus.png", d / "l6_conducteur.png",
                f"1,20 m, voie rapide face au portique de sortie ({_ensemble(d, 'manifest_rendus.json') or 'portique'})"))
    for s in OUVRAGES:
        d = Path(sortie) / s / "rendus"
        out.append((s, "pont — " + _titre(sortie, s), d / "dessus.png", d / "oblique.png", "vue oblique 3/4 de l'ouvrage"))
    for s in L6:
        d = Path(sortie) / s / "l6" / "rendus"
        out.append((s, "panneaux et feux — " + _titre(sortie, s), d / "dessus.png", d / "l6_conducteur.png",
                    f"1,20 m, face à {_ensemble(d)}"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sortie", default=str(DEPOT / "recon" / "out" / "generateur"))
    a = ap.parse_args()
    cat = Path(a.sortie) / "catalogue_rendus"
    for f in sorted(cat.glob("etape4_*.png")):
        f.unlink()
    fs = PL.planches_etape2(entrees(a.sortie), cat, prefixe="etape4",
                            titre="Générateur de routes — étape 4 : ponts, panneaux et feux (route seule)")
    pv = Path(a.sortie) / VITRINE / "rendus" / f"planche_{VITRINE}.png"
    if pv.exists():
        shutil.copyfile(pv, cat / "etape4_vitrine_V01.png")
        fs.append(cat / "etape4_vitrine_V01.png")
    for f in fs:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
