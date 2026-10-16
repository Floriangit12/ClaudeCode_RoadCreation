# -*- coding: utf-8 -*-
"""Vérifie que les identifiants RF-*, DEF-* et ARB-* cités dans des fichiers Markdown existent dans regles_route_fr.json.

Usage : python -I verifier_citations_md.py FICHIER.md [...]
Les formes abrégées « RF-MQ-PP-01, -02 » ne contrôlent que l'identifiant complet ; « RF-SV-X.* » contrôle le préfixe.
"""
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
BASE = ICI.parents[2] / "assets" / "specs" / "route" / "regles_route_fr.json"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.loads(BASE.read_text(encoding="utf-8"))
    ids = {r["id"] for r in d["regles"]}
    alias = d["index_alias"]
    defs = {p["id"] for p in d["parametres_par_defaut"]}
    arbs = {a["id"] for a in d["arbitrages"]}
    total, manquants = 0, []
    for f in sys.argv[1:]:
        texte = Path(f).read_text(encoding="utf-8")
        for m in re.finditer(r"\bRF-[A-Za-z0-9_.'\-*]+", texte):
            brut = m.group(0).rstrip(".,;:)'")
            tok = brut.rstrip("-")
            total += 1
            if brut.endswith("-") and re.fullmatch(r"RF-[A-Z]{2}-?", brut):  # préfixe de volet (« RF-MQ- »)
                if not any(i.startswith(brut) for i in ids):
                    manquants.append((f, brut))
                continue
            if tok.endswith(".*") or tok.endswith("*"):
                pre = tok.rstrip("*")
                if not any(i.startswith(pre) for i in ids):
                    manquants.append((f, tok))
                continue
            if tok not in ids and tok not in alias:
                manquants.append((f, tok))
        for m in re.finditer(r"\bDEF-\d{3}\b", texte):
            total += 1
            if m.group(0) not in defs:
                manquants.append((f, m.group(0)))
        for m in re.finditer(r"\bARB-\d{2}\b", texte):
            total += 1
            if m.group(0) not in arbs:
                manquants.append((f, m.group(0)))
    print(f"{total} citations contrôlées ; {len(manquants)} introuvable(s)")
    for f, t in manquants:
        print("INTROUVABLE", Path(f).name, t)
    return 1 if manquants else 0


if __name__ == "__main__":
    sys.exit(main())
