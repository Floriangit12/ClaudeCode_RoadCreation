#!/usr/bin/env python3
"""Résout sur le PC les chemins Unreal exacts des équivalents CARLA de la librairie.

assets/carla_correspondances.json ne contient que ce que la documentation officielle publie :
identifiants des props (static.prop.*) et dossiers de contenu (/Game/Carla/Static/...). Ce script
lit le contenu CARLA installé sur le PC et complète, pour chaque asset :
  - le chemin objet exact des props (Content/Carla/Config/*.Package.json : {name, path}) ;
  - la liste des .uasset candidats des dossiers documentés (végétation, feux, panneaux, poteaux,
    décals, matériaux...) qui contiennent les mots-clés indiqués.

Usage (Python 3.9+, aucune dépendance) :
    python assets/carla_resoudre_chemins.py --carla D:/carla
    python assets/carla_resoudre_chemins.py --content D:/carla/Unreal/CarlaUE4/Content --max 20
Sortie : assets/carla_correspondances_resolues.json (+ .csv) à côté du fichier d'entrée.
Le dépôt CARLA UE4 (Unreal/CarlaUE4/Content) et la branche UE5 (Unreal/CarlaUnreal/Content) sont
reconnus ; tout dossier « Content » contenant « Carla » convient.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent


def trouver_content(carla: Path | None, content: Path | None) -> Path:
    if content:
        if (content / "Carla").is_dir():
            return content
        sys.exit(f"pas de dossier Carla dans {content}")
    for rel in ("Unreal/CarlaUE4/Content", "Unreal/CarlaUnreal/Content", "Unreal/CarlaUE5/Content", "Content"):
        c = carla / rel
        if (c / "Carla").is_dir():
            return c
    for racine, dirs, _ in os.walk(carla):
        if Path(racine).name == "Content" and "Carla" in dirs:
            return Path(racine)
        if racine.count(os.sep) - str(carla).count(os.sep) > 4:
            dirs[:] = []
    sys.exit(f"dossier Content/Carla introuvable sous {carla}")


def lire_packages(content: Path) -> dict:
    props = {}
    cfg = content / "Carla" / "Config"
    for f in sorted(cfg.glob("*.Package.json")) if cfg.is_dir() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:                       # fichier mal formé : on continue
            print(f"  ! {f.name} illisible : {e}")
            continue
        for p in d.get("props", []):
            if p.get("name") and p.get("path"):
                props.setdefault(p["name"].lower(), {"path": p["path"], "fichier": f.name, "size": p.get("size")})
    return props


def objet_unreal(content: Path, fichier: Path) -> str:
    rel = fichier.relative_to(content).with_suffix("")
    return "/Game/" + rel.as_posix() + "." + rel.name


def inventaire(content: Path, dossier_game: str) -> list:
    rel = dossier_game.replace("/Game/", "", 1).strip("/")
    base = content / rel
    if not base.is_dir():
        return []
    return [p for p in base.rglob("*.uasset")]


def resoudre(entree: Path, sortie: Path, content: Path, nmax: int):
    data = json.loads(entree.read_text(encoding="utf-8"))
    props = lire_packages(content)
    print(f"{len(props)} props déclarés dans Content/Carla/Config/*.Package.json")
    cache = {}
    lignes = []
    for row in data["correspondances"]:
        for c in row.get("carla", []):
            if c.get("blueprint_id"):
                nom = c["blueprint_id"].split(".")[-1].lower()
                p = props.get(nom) or props.get(nom.replace("_", ""))
                c["chemin_resolu"] = p["path"] if p else None
                c["source_resolution"] = p["fichier"] if p else "introuvable dans les .Package.json"
            if c.get("mots_cles") and c.get("dossier_unreal"):
                d = c["dossier_unreal"]
                if d not in cache:
                    cache[d] = inventaire(content, d)
                mots = [m.lower() for m in c["mots_cles"]]
                trouves = []
                for f in cache[d]:
                    s = f.relative_to(content).as_posix().lower()
                    if any(m in s for m in mots):
                        trouves.append(objet_unreal(content, f))
                c["candidats_resolus"] = sorted(trouves)[:nmax]
                c["nb_candidats"] = len(trouves)
            lignes.append([row["asset"], row["adequation"], c.get("blueprint_id") or "", c.get("chemin_resolu") or "",
                           "; ".join(c.get("candidats_resolus", [])[:5])])
    data["meta"]["resolution"] = {"content": str(content), "props_declares": len(props),
                                  "dossiers_inventories": {k: len(v) for k, v in cache.items()}}
    sortie.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    with open(sortie.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["asset", "adequation", "blueprint_id", "chemin_resolu", "candidats (5 premiers)"])
        w.writerows(lignes)
    print(f"écrit : {sortie} et {sortie.with_suffix('.csv')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--carla", type=Path, help="racine du dépôt CARLA")
    ap.add_argument("--content", type=Path, help="dossier Content (si non standard)")
    ap.add_argument("--entree", type=Path, default=ICI / "carla_correspondances.json")
    ap.add_argument("--sortie", type=Path, default=ICI / "carla_correspondances_resolues.json")
    ap.add_argument("--max", type=int, default=15, help="nombre max de candidats par mot-clé")
    a = ap.parse_args()
    if not a.carla and not a.content:
        ap.error("--carla ou --content requis")
    content = trouver_content(a.carla, a.content)
    print("Content :", content)
    resoudre(a.entree, a.sortie, content, a.max)


if __name__ == "__main__":
    main()
