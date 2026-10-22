# -*- coding: utf-8 -*-
"""Non-régression de l'intégration de l'étape 4 : sorties d'une fabrication comparées à une référence (sans Houdini).

    python recon/generateur/validation/comparer_integration_etape4.py REFERENCE NOUVEAU [SCENE ...] [--json F]

REFERENCE : copie des sorties avant l'intégration (recon/generateur/tmp/integration_etape4/avant/<scene>/, rendus
exclus) ; NOUVEAU : sortie de fabriquer_generateur.py --complet (recon/out/generateur). Tous les fichiers des lots sont
comparés, récursivement : modele_voie.json, compilation.json, l1, l2, l2b, l3, l4, l5, autoroute, l6 (sans rendus),
ouvrages, couches (sans rendus). Une seule normalisation, celle de commun/determinisme.octets (chemins relatifs des
matériaux dans les .usda ; manifestes l2 / l2b sans l'empreinte du .usda) ; .npz comparés par contenu (l'archive zip
de numpy est horodatée) ; autres fichiers (.bgeo.sc, .usdc, .png) à l'octet. Aucune tolérance : chaque fichier différent
est décrit (validation/comparer_integration.decrire) puis classé à la main dans le rapport.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(ICI))
from commun import determinisme as DET  # noqa: E402
import comparer_integration as CI  # noqa: E402

RACINE = ("modele_voie.json", "compilation.json")
LOTS = ("l1", "l2", "l2b", "l3", "l4", "l5", "autoroute", "l6", "ouvrages", "couches")
EXCLUS = ("rendus", "tuiles", "photos_non_versionnees", "plans")


def _fichiers(base: Path) -> set[str]:
    out = {f for f in RACINE if (base / f).exists()}
    for lot in LOTS:
        d = base / lot
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(base)
            if any(p in EXCLUS for p in rel.parts) or f.suffix in (".png", ".exr", ".hiplc"):
                continue
            out.add(rel.as_posix())
    return out


def _egaux(fa: Path, fb: Path) -> bool:
    if fa.suffix == ".npz":
        return DET._npz_egaux(fa, fb)
    return DET.octets(fa) == DET.octets(fb)


def comparer_scene(ref: Path, neuf: Path) -> dict:
    res = {"identiques": 0, "differents": {}, "absents": [], "nouveaux": []}
    a, b = _fichiers(ref), _fichiers(neuf)
    for cle in sorted(a | b):
        fa, fb = ref / cle, neuf / cle
        if cle not in b:
            res["absents"].append(cle)
        elif cle not in a:
            res["nouveaux"].append(cle)
        elif _egaux(fa, fb):
            res["identiques"] += 1
        else:
            res["differents"][cle] = CI.decrire(fa, fb) if fa.suffix in (".json", ".npy") else \
                {"taille": [fa.stat().st_size, fb.stat().st_size]}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reference")
    ap.add_argument("nouveau")
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    ref, neuf = Path(a.reference), Path(a.nouveau)
    scenes = a.scenes or sorted(p.name for p in ref.iterdir() if p.is_dir())
    out = {}
    for s in scenes:
        out[s] = comparer_scene(ref / s, neuf / s)
        r = out[s]
        print(f"{s} : {r['identiques']} identiques, {len(r['differents'])} différents, {len(r['absents'])} absents, "
              f"{len(r['nouveaux'])} nouveaux")
        for k, v in r["differents"].items():
            print("   ", k, json.dumps(v, ensure_ascii=False)[:300])
        for k in r["absents"][:10]:
            print("    absent :", k)
        for k in r["nouveaux"][:10]:
            print("    nouveau :", k)
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
