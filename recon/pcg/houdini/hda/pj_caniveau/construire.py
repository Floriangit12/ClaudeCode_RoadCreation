"""Construit l'HDA pj::caniveau::1.0 (caniveaux préfabriqués CS1-CS3 devant les bordures) ; hython Houdini 22.

    hython recon/pcg/houdini/hda/pj_caniveau/construire.py            # construit et enregistre pj_caniveau.hdalc/
    hython recon/pcg/houdini/hda/pj_caniveau/construire.py --essai [pilote|site]

Même réseau que pj::bordure (hda/pj_bordure/construire.py, mode « caniveau ») : le nœud disposer est remplacé par
disposer_caniveau (VEX) qui reprend la disposition des éléments de la bordure (joints alignés, bordures_elements.json
caniveaux) et la coupe aux intervalles du caniveau ; sections CS posées devant la face vue (u de −largeur à 0),
dessous = fil d'eau − h côté bordure (TQ-SOL-013 (3) : fil d'eau = pied de la bordure).
"""
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "pj_bordure"))
import construire as B  # noqa: E402

if __name__ == "__main__":
    if "--essai" in sys.argv:
        a = sys.argv[sys.argv.index("--essai") + 1:]
        B.essai(a[0] if a else "site", mode="caniveau")
    else:
        print(B.construire(ICI, mode="caniveau"))
