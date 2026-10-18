# -*- coding: utf-8 -*-
"""Test de permutation (lot correction de l'étape 2) : une scène fabriquée seule et la même scène fabriquée après une
autre scène dans le même processus doivent donner les mêmes octets, manifestes compris.

    python recon/generateur/validation/comparer_permutation.py DOSSIER_A DOSSIER_B SCENE [--json SORTIE]

Tous les fichiers de <dossier>/<scene>/{l1,l2,l2b,l3,l4,l5,autoroute} sont comparés à l'octet ; seule normalisation :
celle du contrôle de déterminisme (commun/determinisme.octets : chemins relatifs des matériaux dans les .usda, empreinte
du .usda dans manifest_l2 / manifest_l2b, comparé à part normalisé).
"""
import argparse
import json
import sys
from pathlib import Path

GEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEN))
from commun import determinisme as DET  # noqa: E402


def comparer(a, b, scene):
    a, b = Path(a) / scene, Path(b) / scene
    ecarts, n = [], 0
    for lot in ("l1", "l2", "l2b", "l3", "l4", "l5", "autoroute"):
        for f in sorted((a / lot).glob("*")):
            if not f.is_file() or f.suffix not in (".json", ".npy", ".npz", ".usda"):
                continue
            g = b / lot / f.name
            n += 1
            if not g.exists() or DET.octets(f) != DET.octets(g):
                ecarts.append(f"{lot}/{f.name}")
        for g in sorted((b / lot).glob("*")):
            if g.is_file() and not (a / lot / g.name).exists() and g.suffix in (".json", ".npy", ".npz", ".usda"):
                ecarts.append(f"{lot}/{g.name} (absent de A)")
    return {"scene": scene, "fichiers": n, "ecarts": ecarts, "identique": not ecarts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("scene")
    ap.add_argument("--json")
    x = ap.parse_args()
    r = comparer(x.a, x.b, x.scene)
    print(json.dumps(r, ensure_ascii=False))
    if x.json:
        Path(x.json).write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0 if r["identique"] else 1


if __name__ == "__main__":
    sys.exit(main())
