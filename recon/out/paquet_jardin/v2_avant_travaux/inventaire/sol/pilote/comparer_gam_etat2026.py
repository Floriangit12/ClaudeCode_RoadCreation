"""Compare les calques SOL_* du levé GAM (vector/gam_topo_sol_*, WGS84) à etat_2026/*_L93.

Question : le levé « ancien » (vector/) et etat_2026 sont-ils deux extractions différentes
(avant / après travaux) ou la même donnée reprojetée ? Mesure : appariement des entités par
indice puis par plus proche voisin, écarts des sommets en L93 (cm), entités présentes dans
une seule des deux couches.

Lecture seule. Sortie : ../comparaison_gam_etat2026.json
Usage : python -I comparer_gam_etat2026.py
"""
import json
import math
from pathlib import Path

import numpy as np
from pyproj import Transformer

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[6]
VEC = RACINE / "data/sites/paquet_jardin/vector"
E26 = RACINE / "data/sites/paquet_jardin/etat_2026"
O = np.array([917279.43, 6460289.98])
T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)

PAIRES = [
    ("gam_topo_sol_bordure_lin", "bordure_lin_L93"),
    ("gam_topo_sol_bordure_pct", "bordure_pct_L93"),
    ("gam_topo_sol_caniveau_lin", "caniveau_lin_L93"),
    ("gam_topo_sol_limite_revetement_lin", "limite_revetement_lin_L93"),
    ("gam_topo_sol_signalisation_horizontale_lin", "signalisation_horizontale_lin_L93"),
    ("gam_topo_sol_signalisation_horizontale_pct", "signalisation_horizontale_pct_L93"),
    ("gam_topo_sol_arbre_pct", "arbre_pct_L93"),
]


def lire(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)["features"]


def coords(g, wgs):
    t = g["type"]
    cs = []
    if t in ("LineString", "MultiPoint"):
        cs = [g["coordinates"]]
    elif t == "MultiLineString":
        cs = g["coordinates"]
    elif t == "Point":
        cs = [[g["coordinates"]]]
    out = []
    for c in cs:
        a = np.asarray(c, dtype=float)[:, :2]
        if wgs:
            x, y = T.transform(a[:, 0], a[:, 1])
            a = np.c_[x, y]
        out.append(a)
    return np.vstack(out) if out else np.zeros((0, 2))


def main():
    res = {}
    for a, b in PAIRES:
        fa, fb = lire(VEC / f"{a}.geojson"), lire(E26 / f"{b}.geojson")
        A = [coords(f["geometry"], True) for f in fa]
        B = [coords(f["geometry"], False) for f in fb]
        # appariement par indice
        n = min(len(A), len(B))
        ec_idx, nb_diff_nsom, props_diff = [], 0, 0
        for i in range(n):
            if len(A[i]) != len(B[i]):
                nb_diff_nsom += 1
                continue
            ec_idx.append(np.hypot(*(A[i] - B[i]).T))
            pa = {k: v for k, v in fa[i]["properties"].items()}
            pb = {k: v for k, v in fb[i]["properties"].items()}
            if pa != pb:
                props_diff += 1
        e = np.concatenate(ec_idx) if ec_idx else np.zeros(0)
        # nuage complet : distance de chaque sommet A au sommet B le plus proche (et inverse)
        PA, PB = np.vstack(A), np.vstack(B)

        def ppv(P, Q):
            d = np.empty(len(P))
            for k in range(0, len(P), 2000):
                blk = P[k:k + 2000]
                d[k:k + 2000] = np.sqrt(((blk[:, None, :] - Q[None, :, :]) ** 2).sum(-1)).min(1)
            return d
        dab, dba = ppv(PA, PB), ppv(PB, PA)
        # emprise
        ea = (PA - O).min(0).round(1).tolist() + (PA - O).max(0).round(1).tolist()
        res[a] = {
            "n_entites_vector": len(fa), "n_entites_etat_2026": len(fb),
            "n_sommets_vector": int(len(PA)), "n_sommets_etat_2026": int(len(PB)),
            "appariement_par_indice": {
                "paires_meme_nb_sommets": len(ec_idx), "paires_nb_sommets_differents": nb_diff_nsom,
                "paires_attributs_differents": props_diff,
                "ecart_sommets_cm": {"p50": round(float(np.median(e)) * 100, 2) if len(e) else None,
                                     "p95": round(float(np.percentile(e, 95)) * 100, 2) if len(e) else None,
                                     "max": round(float(e.max()) * 100, 2) if len(e) else None},
            },
            "plus_proche_sommet_cm": {
                "vector_vers_2026_p50": round(float(np.median(dab)) * 100, 2),
                "vector_vers_2026_p99": round(float(np.percentile(dab, 99)) * 100, 2),
                "vector_vers_2026_max": round(float(dab.max()) * 100, 2),
                "sommets_vector_a_plus_de_10cm": int((dab > 0.10).sum()),
                "sommets_2026_a_plus_de_10cm": int((dba > 0.10).sum()),
            },
            "emprise_locale_vector_m": ea,
        }
    out = ICI.parent / "comparaison_gam_etat2026.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
