# -*- coding: utf-8 -*-
"""Accès en lecture seule aux règles fusionnées `assets/specs/route/regles_route_fr.json` (PLAN_GENERATEUR § 2.5).

Utilisé par l'inférence OSM → modèle (`inference/osm_vers_modele.py`), par le validateur (`schema/valider_modele.py`)
et par les scripts de construction des HDA (défauts des paramètres écrits depuis les `DEF-*`). Les HDA ne lisent
jamais ce JSON : les valeurs leur arrivent comme attributs du modèle (avec `prov`).

    from regles import regle, defaut, arbitrage, valeur, canonique, existe
    regle("RF-OSM-LAR-010")          # la règle (dict)
    regle("OSM-LAR-010")             # ancien identifiant, résolu par index_alias → RF-OSM-LAR-010
    regle("12:OSM-LAR-010")          # forme « volet:identifiant » de index_alias
    defaut("DEF-004")                # paramètre par défaut (dict)
    arbitrage("ARB-19")              # arbitrage (dict)
    valeur("DEF-004")                # 2.0 (champ « valeur » d'un DEF)
    valeur("RF-OSM-LAR-010", "defaut")          # 3.0 (champ « valeurs » d'une règle, chemin pointé)
    valeur("ARB-17", "GAM_m")                   # 2.2 (champ « valeur_retenue » d'un arbitrage)
    canonique("GA-RAY-001")          # None : identifiant des specs du dépôt, absent de index_alias

Fichier lu : variable d'environnement REGLES_ROUTE_FR, sinon <dépôt>/assets/specs/route/regles_route_fr.json.
Identifiants admis dans une instance `modele_voie` (contrôle C11) : MOTIF (RF-…, DEF-nnn, ARB-nn).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent          # recon/generateur
DEPOT = ICI.parents[1]                          # D:/ClaudeCode_RoadCreation
FICHIER_DEFAUT = DEPOT / "assets" / "specs" / "route" / "regles_route_fr.json"

# Identifiants de la base fusionnée : RF-OSM-CAR-040, RF-MQ-PP-02, RF-SV-GEN.HAUTEUR.AGGLO, RF-FEU.HAUTEUR.TROTTOIR,
# RF-AS-garde_corps_hauteur ; paramètres DEF-001 à DEF-034 ; arbitrages ARB-01 à ARB-20.
MOTIF = re.compile(r"^(?:RF-[A-Z]{2,4}[-.][A-Za-z0-9_.'\-]+|DEF-\d{3}|ARB-\d{2})$")   # « ' » : RF-MQ-MOD-T'1


def fichier() -> Path:
    return Path(os.environ.get("REGLES_ROUTE_FR", str(FICHIER_DEFAUT)))


@lru_cache(maxsize=4)
def _base(chemin: str) -> dict:
    octets = Path(chemin).read_bytes()
    d = json.loads(octets.decode("utf-8"))
    regles = {r["id"]: r for r in d.get("regles", [])}
    defs = {p["id"]: p for p in d.get("parametres_par_defaut", [])}
    arbs = {a["id"]: a for a in d.get("arbitrages", [])}
    alias = dict(d.get("index_alias", {}))
    # anciens identifiants nus (« OSM-LAR-020 ») : résolus seulement s'ils désignent une seule règle canonique
    nus: dict[str, set] = {}
    for cle, cible in alias.items():
        if ":" in cle:
            nus.setdefault(cle.split(":", 1)[1], set()).add(cible)
    return {"d": d, "regles": regles, "defs": defs, "arbs": arbs, "alias": alias, "nus": nus,
            "sha256": hashlib.sha256(octets).hexdigest(), "date": d.get("date"), "schema": d.get("schema")}


def base() -> dict:
    return _base(str(fichier()))


def empreinte() -> dict:
    """Traçabilité : chemin, schéma, date et SHA-256 de la base lue."""
    b = base()
    return {"fichier": str(fichier()).replace("\\", "/"), "schema": b["schema"], "date": b["date"],
            "sha256": b["sha256"], "regles": len(b["regles"]), "parametres": len(b["defs"]),
            "arbitrages": len(b["arbs"]), "alias": len(b["alias"])}


def canonique(ident: str) -> str | None:
    """Identifiant canonique (règle RF-*, DEF-nnn ou ARB-nn) d'un identifiant, ou None s'il est inconnu.

    Résout : identifiant canonique ; clé de index_alias (« RF-MA-CAR-001 » fusionné, « 12:OSM-LAR-020 ») ;
    ancien identifiant nu (« OSM-LAR-020 ») s'il ne désigne qu'une règle."""
    b = base()
    if ident in b["regles"] or ident in b["defs"] or ident in b["arbs"]:
        return ident
    if ident in b["alias"]:
        return b["alias"][ident]
    cibles = b["nus"].get(ident)
    if cibles and len(cibles) == 1:
        return next(iter(cibles))
    return None


def ambigu(ident: str) -> list[str]:
    """Règles candidates d'un ancien identifiant nu qui en désigne plusieurs (sinon liste vide)."""
    cibles = base()["nus"].get(ident) or set()
    return sorted(cibles) if len(cibles) > 1 else []


def existe(ident: str) -> bool:
    """Vrai si l'identifiant est de la forme admise (MOTIF) et se résout dans la base fusionnée."""
    return bool(MOTIF.match(ident or "")) and canonique(ident) is not None


def regle(ident: str) -> dict:
    """Règle RF-* (anciens identifiants résolus par index_alias). KeyError si inconnue."""
    c = canonique(ident)
    if c is None or c not in base()["regles"]:
        raise KeyError(f"règle inconnue de regles_route_fr.json : {ident}")
    return base()["regles"][c]


def defaut(ident: str) -> dict:
    """Paramètre par défaut DEF-nnn. KeyError si inconnu."""
    if ident not in base()["defs"]:
        raise KeyError(f"paramètre par défaut inconnu : {ident}")
    return base()["defs"][ident]


def arbitrage(ident: str) -> dict:
    """Arbitrage ARB-nn. KeyError si inconnu."""
    if ident not in base()["arbs"]:
        raise KeyError(f"arbitrage inconnu : {ident}")
    return base()["arbs"][ident]


def _suivre(v, chemin: str | None):
    if not chemin:
        return v
    for morceau in chemin.split("."):
        if isinstance(v, dict) and morceau in v:
            v = v[morceau]
        elif isinstance(v, list) and morceau.lstrip("-").isdigit():
            v = v[int(morceau)]
        else:
            raise KeyError(f"chemin « {chemin} » absent (bloqué à « {morceau} »)")
    return v


def valeur(ident: str, chemin: str | None = None):
    """Valeur d'une règle (« valeurs »), d'un DEF (« valeur ») ou d'un ARB (« valeur_retenue »), au chemin pointé."""
    if ident.startswith("DEF-"):
        return _suivre(defaut(ident)["valeur"], chemin)
    if ident.startswith("ARB-"):
        return _suivre(arbitrage(ident)["valeur_retenue"], chemin)
    return _suivre(regle(ident)["valeurs"], chemin)


def confiance(ident: str) -> str:
    """Confiance d'une règle RF-* (haute, moyenne, faible) ; « moyenne » pour un DEF ou un ARB (choix documentés)."""
    c = canonique(ident)
    if c and c in base()["regles"]:
        return base()["regles"][c].get("confiance", "moyenne")
    return "moyenne"
