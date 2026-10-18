# -*- coding: utf-8 -*-
"""Non-régression de l'intégration de l'étape 2 : sorties d'une fabrication comparées à une référence (sans Houdini).

    python recon/generateur/validation/comparer_integration.py REFERENCE NOUVEAU [SCENE ...] [--json F]

REFERENCE : copie des sorties avant l'intégration (recon/generateur/tmp/integration/avant/<scene>/ : l1, l2, l2b, l3,
l4, l5, autoroute, modele_voie.json, compilation.json) ; NOUVEAU : sortie de fabriquer_generateur.py
(recon/out/generateur). Chaque fichier est comparé à l'octet après la seule normalisation de commun/determinisme.py
(chemins relatifs des matériaux dans les .usda ; manifestes l2 / l2b sans l'empreinte du .usda). Les fichiers
différents sont décrits : tableaux numpy (forme, écart maximal), JSON (chemins des valeurs changées, 12 premiers),
manifestes (signatures d'HDA changées). Aucune tolérance : un écart est un écart, classé ensuite à la main en
« changement voulu » ou non dans le rapport d'intégration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
sys.path.insert(0, str(GEN))
from commun import determinisme as DET  # noqa: E402

LOTS = ("l1", "l2", "l2b", "l3", "l4", "l5", "autoroute")
RACINE = ("modele_voie.json", "compilation.json")
SUFFIXES = (".json", ".npy", ".npz", ".usda")


def _chemins_json(a, b, p="", out=None, n=12):
    out = [] if out is None else out
    if len(out) >= n:
        return out
    if type(a) is not type(b):
        out.append(p or "/")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(f"{p}/{k} ({'ajouté' if k not in a else 'retiré'})")
            else:
                _chemins_json(a[k], b[k], f"{p}/{k}", out, n)
            if len(out) >= n:
                break
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{p} (longueur {len(a)} -> {len(b)})")
        for i, (x, y) in enumerate(zip(a, b)):
            _chemins_json(x, y, f"{p}[{i}]", out, n)
            if len(out) >= n:
                break
    elif a != b:
        out.append(p)
    return out


def _cles_ajoutees(a, b, acc):
    """Clés ajoutées dans les objets de b (même structure que a) : {clé: compte}."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in b:
            if k not in a:
                acc[k] = acc.get(k, 0) + 1
            else:
                _cles_ajoutees(a[k], b[k], acc)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for x, y in zip(a, b):
            _cles_ajoutees(x, y, acc)
    return acc


def _ecart_numerique(a, b, acc):
    """Écart numérique maximal entre valeurs appariées (même chemin) et nombre de valeurs non numériques différentes."""
    if isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            acc[1] += 1
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        acc[0] = max(acc[0], abs(float(a) - float(b)))
    elif isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) & set(b):
            _ecart_numerique(a[k], b[k], acc)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for x, y in zip(a, b):
            _ecart_numerique(x, y, acc)
    elif a != b:
        acc[1] += 1
    return acc


def decrire(fa: Path, fb: Path) -> dict:
    if fa.suffix == ".npy":
        A, B = np.load(fa), np.load(fb)
        d = {"forme": [list(A.shape), list(B.shape)]}
        if A.shape == B.shape and A.dtype.kind in "fi":
            e = np.abs(A.astype(np.float64) - B.astype(np.float64))
            d["ecart_max"] = float(e.max()) if e.size else 0.0
            d["valeurs_differentes"] = int((e > 0).sum())
        return d
    if fa.suffix == ".json":
        A = json.loads(fa.read_text(encoding="utf-8"))
        B = json.loads(fb.read_text(encoding="utf-8"))
        ec = _ecart_numerique(A, B, [0.0, 0])
        d = {"chemins": _chemins_json(A, B), "ecart_numerique_max": ec[0], "autres_valeurs_differentes": ec[1]}
        if fa.name.startswith("manifest") and isinstance(A, dict):
            ha, hb = A.get("hda") or {}, B.get("hda") or {}
            d["hda_changees"] = sorted(k for k in set(ha) | set(hb) if ha.get(k) != hb.get(k))
        aj = _cles_ajoutees(A, B, {})
        if aj:
            d["cles_ajoutees"] = dict(sorted(aj.items()))
        return d
    return {"taille": [fa.stat().st_size, fb.stat().st_size]}


def comparer_scene(ref: Path, neuf: Path) -> dict:
    res = {"identiques": 0, "differents": {}, "absents": [], "nouveaux": []}
    paires = [(ref / f, neuf / f) for f in RACINE]
    for lot in LOTS:
        if (ref / lot).exists() or (neuf / lot).exists():
            noms = {p.name for d in (ref / lot, neuf / lot) if d.exists() for p in d.iterdir()
                    if p.is_file() and p.suffix in SUFFIXES}
            paires += [(ref / lot / n, neuf / lot / n) for n in sorted(noms)]
    for fa, fb in paires:
        cle = str(fa.relative_to(ref)).replace("\\", "/")
        if not fa.exists() and not fb.exists():
            continue
        if not fb.exists():
            res["absents"].append(cle)
            continue
        if not fa.exists():
            res["nouveaux"].append(cle)
            continue
        if DET.octets(fa) == DET.octets(fb):
            res["identiques"] += 1
        else:
            res["differents"][cle] = decrire(fa, fb)
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
        print(f"{s} : {r['identiques']} identiques, {len(r['differents'])} différents, absents {r['absents']}, "
              f"nouveaux {r['nouveaux']}")
        for k, v in r["differents"].items():
            print("   ", k, json.dumps(v, ensure_ascii=False)[:400])
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
