"""Comparaison à l'octet des sorties de deux processus du pilote (contrôle de déterminisme), sans Houdini.

Une seule normalisation, dite : dans un .usda, les références aux matériaux de la bibliothèque sont des chemins
relatifs au dossier de sortie (« @../../../../../assets/… ») ; leur nombre de « ../ » dépend de la profondeur de ce
dossier, qui n'est pas la même pour le second processus (recon/generateur/tmp/l1/determinisme/). Ils sont ramenés à
« @<depot>/assets/… » avant comparaison ; manifest_l2.json est comparé sans l'empreinte de route_l2.usda (comparé à
part, normalisé) ; de même manifest_l2b.json sans l'empreinte de route_l2b.usda (lot L2b). Tout le reste est
comparé octet par octet.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FICHIERS_L1 = ("courbes_controle.json", "manifest_l1.json")


def avertissement_stable(w: str) -> str:
    """Avertissement de cuisson de Houdini écrit dans un manifeste : la liste d'exemples d'attributs d'un Merge
    (« A mis-match of attributes … e.g.: s_dorsale, variant, courbure, … ») suit l'ordre de la table de hachage des
    attributs, propre au processus (constat de la relecture adverse : manifest_l2.json de S08 et S11 différents d'un
    processus à l'autre) ; elle est retirée, le reste du message est gardé tel quel."""
    return re.sub(r"e\.g\.:\s.*$", "e.g.: <liste d'attributs retirée : ordre propre au processus>", w)


def avertissements_stables(noeuds) -> list[str]:
    """Avertissements de cuisson des nœuds (et de leurs enfants), stables d'un processus à l'autre, triés, uniques."""
    return sorted({avertissement_stable(f"{c.path()}: {w}") for n in noeuds for c in (n,) + tuple(n.allSubChildren())
                   for w in c.warnings()})
SUFFIXES_L2 = (".npy", ".npz", ".json", ".usda")


def octets(f: Path) -> bytes:
    b = Path(f).read_bytes()
    if f.suffix == ".usda":
        return re.sub(rb"@(\.\./)+assets/", b"@<depot>/assets/", b)
    if f.name in ("manifest_l2.json", "manifest_l2b.json"):
        d = json.loads(b.decode("utf-8"))
        d.get("fichiers", {}).pop("route_l2.usda", None)
        d.get("fichiers", {}).pop("route_l2b.usda", None)
        return json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return b


def comparer(dossiers_l1, autre: Path, l2: bool, l2b: bool = False) -> tuple[list[str], int]:
    """dossiers_l1 : dossiers <sortie>/<scene>/l1 du premier processus ; autre : sortie du second.
    Renvoie (écarts, nombre de fichiers comparés)."""
    ecarts, n = [], 0
    for d in map(Path, dossiers_l1):
        for f in FICHIERS_L1:
            b = Path(autre) / d.parent.name / "l1" / f
            n += 1
            if not b.exists() or (d / f).read_bytes() != b.read_bytes():
                ecarts.append(f"{d.parent.name}/{f}")
        for lot, actif in (("l2", l2), ("l2b", l2b)):
            if not actif:
                continue
            for f in sorted((d.parent / lot).glob("*")):
                if f.is_file() and f.suffix in SUFFIXES_L2:
                    b = Path(autre) / d.parent.name / lot / f.name
                    n += 1
                    if not b.exists() or octets(f) != octets(b):
                        ecarts.append(f"{d.parent.name}/{lot}/{f.name}")
    return ecarts, n


SUFFIXES_ARBO = (".json", ".npy", ".npz", ".usda")


def _npz_egaux(a: Path, b: Path) -> bool:
    """Archives .npz comparées par contenu (noms, formes, types, valeurs) : l'horodatage des entrées de l'archive zip
    écrite par numpy change d'un processus à l'autre."""
    import numpy as np
    with np.load(a, allow_pickle=False) as A, np.load(b, allow_pickle=False) as B:
        if sorted(A.files) != sorted(B.files):
            return False
        for k in A.files:
            x, y = A[k], B[k]
            if x.shape != y.shape or x.dtype != y.dtype or not np.array_equal(x, y):
                return False
    return True


def comparer_arborescence(scene: Path, autre_scene: Path, lots, remplacer=()) -> tuple[list[str], int]:
    """Intégration de l'étape 4 : sorties des lots (sous-dossiers `lots` de la scène, récursivement : l3, l4, l5,
    autoroute, l6, ouvrages, couches/<couche>/l1…) comparées au second processus. .json, .npy, .usda à l'octet après la
    normalisation de octets() ; .npz par contenu ; manifestes (chemins de sortie) et rendus exclus. remplacer : paires
    (chemin de sortie du second processus, chemin de sortie du premier), en octets, ramenées l'une à l'autre (fichiers
    des couches d'une scène à ouvrages, qui citent le modèle de la couche écrit dans la sortie).
    Renvoie (écarts, nombre de fichiers comparés)."""
    ecarts, n = [], 0
    for lot in lots:
        d = Path(scene) / lot
        if not d.exists():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file() or f.suffix not in SUFFIXES_ARBO or f.name.startswith("manifest"):
                continue
            rel = f.relative_to(scene)
            if "rendus" in rel.parts or "tuiles" in rel.parts:
                continue
            g = Path(autre_scene) / rel
            n += 1
            if not g.exists():
                ecarts.append(f"{Path(scene).name}/{rel.as_posix()} (absent)")
            elif f.suffix == ".npz":
                if not _npz_egaux(f, g):
                    ecarts.append(f"{Path(scene).name}/{rel.as_posix()}")
            else:
                a, b = octets(f), octets(g)
                for x, y in remplacer:
                    b = b.replace(x, y)
                if a != b:
                    ecarts.append(f"{Path(scene).name}/{rel.as_posix()}")
    return ecarts, n
