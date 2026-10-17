# -*- coding: utf-8 -*-
"""Valeurs du rendu lues hors de Houdini (rendu/rendu_l2b.py importe hou) : tables du module lues par ast (SOLS,
ECHELLE_ALBEDO, LOOKS, SOL_NEUTRE, SOLEIL_ELEVATION, GRIS_PASSAGE) et albédos moyens de la bibliothèque
(assets/lib/*/meta.json, albedo_moyen_lineaire) : luminance linéaire Rec. 709 des bordures, caniveaux, trottoirs,
enrobé, piste et sol neutre (critère C-18 du rapport de correction)."""
import ast
import json
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[3]
RENDU = DEPOT / "recon" / "generateur" / "rendu" / "rendu_l2b.py"
LIB = {"route": DEPOT / "assets" / "lib" / "route_fr" / "materiaux", "site": DEPOT / "assets" / "lib" / "materiaux"}
NOMS = ("SOLS", "ECHELLE_ALBEDO", "LOOKS", "SOL_NEUTRE", "SOLEIL_ELEVATION", "GRIS_PASSAGE")


def _y(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def tables():
    arbre = ast.parse(RENDU.read_text(encoding="utf-8"))
    out = {}
    for n in arbre.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and n.targets[0].id in NOMS:
            out[n.targets[0].id] = ast.literal_eval(n.value)
    return out


def albedo_bib(lib, nom, echelle=1.0):
    """Luminance de l'albédo moyen de la bibliothèque × échelle (nombre, ou triplet par canal depuis le second contrôle :
    bordures et caniveaux en gris chaud)."""
    m = json.loads((LIB[lib] / nom / "meta.json").read_text(encoding="utf-8"))
    a = m["albedo_moyen_lineaire"]
    k = echelle if isinstance(echelle, (tuple, list)) else (echelle, echelle, echelle)
    return _y([a[i] * k[i] for i in range(3)])


def valeurs():
    t = tables()
    lb, nb = t["LOOKS"]["beton_bordure_gris"]
    lc, nc = t["LOOKS"]["caniveau_beton"]
    bordure = albedo_bib(lb, nb, t["ECHELLE_ALBEDO"]["beton_bordure_gris"])
    caniveau = albedo_bib(lc, nc, t["ECHELLE_ALBEDO"]["caniveau_beton"])
    trot = {k: _y(t["SOLS"][k][2]) for k in ("enrobe_trottoir", "beton_balaye", "dalles_beton")}
    return {"bordure": round(bordure, 4), "caniveau": round(caniveau, 4),
            "trottoirs": {k: round(v, 4) for k, v in trot.items()},
            "rapports": [round(bordure / v, 4) for v in trot.values()],
            "enrobe": round(_y(t["SOLS"]["enrobe_bbsg_ancien"][2]), 4),
            "piste": round(_y(t["SOLS"]["enrobe_piste_cyclable"][2]), 4),
            "sol_neutre": round(_y(t["SOL_NEUTRE"]), 4), "soleil_deg": t["SOLEIL_ELEVATION"],
            "gris_passage": t["GRIS_PASSAGE"],
            "bibliotheque_bordure": f"{lb}:{nb}", "bibliotheque_caniveau": f"{lc}:{nc}"}


if __name__ == "__main__":
    print(json.dumps(valeurs(), ensure_ascii=False, indent=1))
