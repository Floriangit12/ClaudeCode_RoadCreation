# -*- coding: utf-8 -*-
"""Entrées de provenance `prov[<chemin>] = {src, regle, conf, note}` (modele_voie.schema.json $defs/prov_entree).

Toute règle citée passe par `regles.existe` : une provenance ne peut pas citer une règle absente de
`regles_route_fr.json` (le contrôle C11 du validateur ne peut donc pas échouer sur une sortie du générateur).

    from commun.prov import defaut, inference, osm, description, table
    defaut("DEF-004")                         # {"src": "defaut:DEF-004", "regle": "DEF-004", "conf": "moyenne"}
    inference("RF-OSM-LAR-001", regle="RF-OSM-LAR-010")
    osm("tag/maxspeed", "RF-OSM-VIT-001")     # {"src": "osm:tag/maxspeed", "regle": "RF-OSM-VIT-001", "conf": "haute"}
    description("profil[2].largeur")          # {"src": "description:profil[2].largeur", "conf": "moyenne"}
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # recon/generateur (regles.py)
import regles  # noqa: E402

CONFIANCES = ("haute", "moyenne", "faible")

# tables du volet 12 qui ne sont pas des règles de la base fusionnée (genre « table_volet12 » du validateur)
TABLE_VOLET12 = "regle:inference_osm_profil.json"


def _verifier(regle: str | None) -> None:
    if regle is not None and not regles.existe(regle):
        raise ValueError(f"règle absente de regles_route_fr.json : {regle}")


def _conf(regle: str | None, conf: str | None) -> str:
    if conf is not None:
        if conf not in CONFIANCES:
            raise ValueError(f"confiance inconnue : {conf}")
        return conf
    return regles.confiance(regle) if regle else "moyenne"


def entree(src: str, regle: str | None = None, conf: str | None = None, note: str | None = None) -> dict:
    _verifier(regle)
    e = {"src": src}
    if regle:
        e["regle"] = regle
    e["conf"] = _conf(regle, conf)
    if note:
        e["note"] = note
    return e


def defaut(regle: str, conf: str | None = None, note: str | None = None, par: str | None = None) -> dict:
    """Valeur par défaut tirée de `regle` (src « defaut:<par ou regle> »)."""
    _verifier(par)
    return entree(f"defaut:{par or regle}", regle, conf, note)


def inference(regle: str, conf: str | None = None, note: str | None = None, src_regle: str | None = None) -> dict:
    """Valeur inférée (src « inference:<src_regle ou regle> »)."""
    _verifier(src_regle)
    return entree(f"inference:{src_regle or regle}", regle, conf, note)


def osm(chemin: str, regle: str | None = None, conf: str | None = None, note: str | None = None) -> dict:
    """Valeur lue dans OSM : chemin « tag/<clé> », « way/<id> », « node/<id> »."""
    return entree(f"osm:{chemin}", regle, conf or ("haute" if regle is None else None), note)


def description(champ: str, conf: str = "moyenne", regle: str | None = None, note: str | None = None) -> dict:
    """Valeur dite par la description simple (src « description:<champ> »)."""
    return entree(f"description:{champ}", regle, conf, note)


def table(nom: str, conf: str = "moyenne", note: str | None = None) -> dict:
    """Valeur tirée d'une table du volet 12 (inference_osm_profil.json, tables.<nom>)."""
    return entree(f"{TABLE_VOLET12}#tables.{nom}", None, conf, note)


def solveur(etape: str, regle: str | None = None, conf: str | None = None, note: str | None = None) -> dict:
    """Valeur calculée par le compilateur à partir d'autres valeurs (src « solveur:<étape> »)."""
    return entree(f"solveur:{etape}", regle, conf, note)
