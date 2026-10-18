# -*- coding: utf-8 -*-
"""Écriture YAML relue à l'identique par `description/yaml_simple.py` (sous-ensemble du format de description).

Dictionnaires et listes en blocs ; listes de scalaires et petits dictionnaires de scalaires en ligne ; chaînes entre
guillemets doubles dès qu'elles ne sont pas un mot simple ; nombres en notation Python. `ecrire(o)` puis
`yaml_simple.charger()` redonne `o` (contrôlé par `verifier_aller_retour`).
"""
from __future__ import annotations

import re

SIMPLE = re.compile(r"^[A-Za-z_À-ÖØ-öø-ÿ][A-Za-z0-9_À-ÖØ-öø-ÿ.\-]*$")
MOTS_RESERVES = {"true", "false", "null", "yes", "no", "on", "off", "~"}


def scalaire(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("nombre non fini")
        return repr(v + 0.0)
    s = str(v)
    if "\\" in s:
        raise ValueError(f"barre oblique inverse non prise en charge : {s!r}")
    if SIMPLE.match(s) and s.lower() not in MOTS_RESERVES and not re.match(r"^[-+]?[\d.]", s):
        return s
    return '"' + s.replace('"', '\\"').replace("\n", "\\n") + '"'


def _en_ligne(o) -> str | None:
    if isinstance(o, list) and all(not isinstance(x, (list, dict)) for x in o):
        return "[" + ", ".join(scalaire(x) for x in o) + "]"
    if isinstance(o, list) and all(isinstance(x, list) and all(not isinstance(y, (list, dict)) for y in x) for x in o):
        return "[" + ", ".join(_en_ligne(x) for x in o) + "]"
    if isinstance(o, dict) and o and all(not isinstance(x, (list, dict)) for x in o.values()):
        return "{" + ", ".join(f"{_cle(k)}: {scalaire(v)}" for k, v in o.items()) + "}"
    return None


def _cle(k) -> str:
    s = str(k)
    if SIMPLE.match(s) and s.lower() not in MOTS_RESERVES:
        return s
    return '"' + s.replace('"', '\\"') + '"'


def _lignes(o, ind: int, out: list):
    pad = " " * ind
    if isinstance(o, dict):
        for k, v in o.items():
            el = _en_ligne(v) if isinstance(v, (list, dict)) else None
            if isinstance(v, (list, dict)) and v and (el is None or len(el) + ind + len(str(k)) > 118):
                out.append(f"{pad}{_cle(k)}:")
                _lignes(v, ind + 2, out)
            elif isinstance(v, (list, dict)):
                out.append(f"{pad}{_cle(k)}: {el if el is not None else ('[]' if isinstance(v, list) else '{}')}")
            else:
                out.append(f"{pad}{_cle(k)}: {scalaire(v)}")
    elif isinstance(o, list):
        for v in o:
            if isinstance(v, dict) and v:
                el = _en_ligne(v)
                if el is not None and len(el) + ind < 118:
                    out.append(f"{pad}- {el}")
                    continue
                sous = []
                _lignes(v, ind + 2, sous)
                sous[0] = f"{pad}- " + sous[0][ind + 2:]
                out.extend(sous)
            elif isinstance(v, list):
                el = _en_ligne(v)
                if el is not None:
                    out.append(f"{pad}- {el}")
                else:
                    out.append(f"{pad}-")
                    _lignes(v, ind + 2, out)
            else:
                out.append(f"{pad}- {scalaire(v)}")
    else:
        out.append(pad + scalaire(o))


def ecrire(o, entete: str = "") -> str:
    out = [f"# {l}" if l else "#" for l in entete.splitlines()] if entete else []
    _lignes(o, 0, out)
    return "\n".join(out) + "\n"


def verifier_aller_retour(o, texte: str):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from description import yaml_simple
    relu = yaml_simple.charger(texte)
    if relu != o:
        raise ValueError("écriture YAML : relecture différente de l'objet écrit")
