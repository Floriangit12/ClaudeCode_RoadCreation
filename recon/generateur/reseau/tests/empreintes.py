# -*- coding: utf-8 -*-
"""Empreintes sha256 des modèles compilés, témoin de non-régression du lot N1 (CHAINE_CONSTRUCTION § 7.2).

    python -B recon/generateur/reseau/tests/empreintes.py SORTIE.json [--comparer AVANT.json] [--graine N]

Compile, avec le compilateur du dépôt importé tel quel (aucun bytecode écrit), les scènes de référence :
S01-S12 et B01 (`scenes_simples/`), J1-J6 (`scenes_carrefours/`), G1-G4 (`scenes_giratoires/`), A1-A4
(`scenes_autoroutes/`), les exemples (`description/exemples/`) et M20/M24/M27 (`scenes_meylan/`). Pour chacune :
sha256 du modèle et du rapport de compilation (JSON indenté comme `compiler_fichier`), nombre d'erreurs de validation
et de non-conformités non admises. `--comparer` liste les scènes dont une empreinte a changé (code de sortie 1).
Chaque scène est compilée dans un processus neuf : aucun état de module ne passe d'une scène à l'autre ; `--graine N`
fixe PYTHONHASHSEED (contrôle de déterminisme : l'ordre d'un ensemble ne doit jamais changer une sortie).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
DEPOT = GEN.parents[1]

GROUPES = {
    "simples": sorted((GEN / "scenes_simples").glob("S*.yaml")) + sorted((GEN / "scenes_simples").glob("B*.yaml")),
    "carrefours": sorted((GEN / "scenes_carrefours").glob("J*.yaml")),
    "giratoires": sorted((GEN / "scenes_giratoires").glob("G*.yaml")),
    "autoroutes": sorted((GEN / "scenes_autoroutes").glob("A*.yaml")),
    "exemples": sorted((GEN / "description" / "exemples").glob("*.yaml")),
    "meylan_etape1": sorted((GEN / "scenes_meylan").glob("M*.yaml")),
}

ENFANT = r'''
import copy, hashlib, json, sys
sys.dont_write_bytecode = True
from pathlib import Path
GEN = Path(sys.argv[1]); f = Path(sys.argv[2])
sys.path.insert(0, str(GEN)); sys.path.insert(0, str(GEN / "schema"))
from description import description_vers_modele as D
from description import yaml_simple
octets = f.read_bytes()
d = yaml_simple.charger(octets.decode("utf-8"))
src = str(f.resolve().relative_to(GEN.parents[1])).replace("\\", "/")
try:
    m, r = D.compiler(d, src, hashlib.sha256(octets).hexdigest())
except Exception as e:
    print(json.dumps({"exception": f"{type(e).__name__}: {e}"}, ensure_ascii=False)); sys.exit(0)
om = (json.dumps(m, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
orr = (json.dumps(r, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
print(json.dumps({"modele": hashlib.sha256(om).hexdigest(), "rapport": hashlib.sha256(orr).hexdigest(),
                  "erreurs": r["validation"]["nb_erreurs"], "non_conformites": len(r["non_conformites"])}))
'''


def empreinte(f: Path, graine=None) -> dict:
    env = dict(os.environ)
    if graine is not None:
        env["PYTHONHASHSEED"] = str(graine)
    p = subprocess.run([sys.executable, "-B", "-c", ENFANT, str(GEN), str(f)], capture_output=True, text=True,
                       encoding="utf-8", cwd=str(DEPOT), env=env)
    lignes = [x for x in p.stdout.splitlines() if x.startswith("{")]
    if not lignes:
        return {"exception": (p.stderr or p.stdout).strip()[-400:]}
    return json.loads(lignes[-1])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    cible = Path(args[0])
    avant = None
    graine = int(args[args.index("--graine") + 1]) if "--graine" in args else None
    if "--comparer" in args:
        avant = json.loads(Path(args[args.index("--comparer") + 1]).read_text(encoding="utf-8"))
    out = {}
    for g, fichiers in GROUPES.items():
        for f in fichiers:
            cle = f"{g}/{f.name}"
            out[cle] = empreinte(f, graine)
            print(cle, out[cle].get("modele", out[cle].get("exception"))[:16], out[cle].get("erreurs"))
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(out), "scènes ;", sum(1 for v in out.values() if v.get("erreurs") == 0), "sans erreur")
    if avant is not None:
        diff = sorted(k for k in set(avant) | set(out) if avant.get(k) != out.get(k))
        dm = sorted(k for k in set(avant) | set(out) if (avant.get(k) or {}).get("modele") != (out.get(k) or {}).get("modele"))
        print("modèles identiques :", len(out) - len(dm), "/", len(out), "; empreintes complètes (modèle et rapport) "
              "identiques :", len(out) - len(diff), "/", len(out))
        for k in diff:
            print("DIFFÉRENT", k, avant.get(k), "→", out.get(k))
        return 1 if diff else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
