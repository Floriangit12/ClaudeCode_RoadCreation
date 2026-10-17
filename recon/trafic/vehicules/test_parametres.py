"""Contrôle de forme de vehicules_parametres.json. Lancer : python recon/trafic/vehicules/test_parametres.py [chemin]"""
import json
import sys
from pathlib import Path

CHEMIN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3] / "assets" / "specs" / "trafic" / "vehicules_parametres.json"
CLES = {"id", "grandeur", "population", "loi", "parametres", "unite", "conditions", "source", "confiance", "nature"}
NATURES = {"norme", "mesure", "donnee_administrative", "donnee_constructeur", "derive", "estimation", "convention"}


def tous_les_parametres(J):
    for sec in ["parc_france", "composition_trafic", "adherence", "reglementation", "freinage_systeme"]:
        yield from J[sec]
    for c in J["classes"].values():
        yield from c["parametres"]


def main():
    J = json.load(open(CHEMIN, encoding="utf-8"))
    ids, n, erreurs = set(), 0, []
    for p in tous_les_parametres(J):
        n += 1
        if set(p) != CLES:
            erreurs.append(f"{p.get('id')}: clés {sorted(set(p) ^ CLES)}")
        if p["id"] in ids:
            erreurs.append(f"id en double {p['id']}")
        ids.add(p["id"])
        if p["nature"] not in NATURES:
            erreurs.append(f"{p['id']}: nature {p['nature']}")
        if p["confiance"] not in {"haute", "moyenne", "faible"}:
            erreurs.append(f"{p['id']}: confiance {p['confiance']}")
        s = p["source"]
        if not isinstance(s, dict) or set(s) != {"doc", "page", "annee"} or s["doc"] not in J["sources"]:
            erreurs.append(f"{p['id']}: source {s}")
        q = p["parametres"]
        if isinstance(q, dict) and "p5" in q and not (q["p5"] <= q["p50"] <= q["p95"]):
            erreurs.append(f"{p['id']}: quantiles non ordonnés")
    for e in erreurs:
        print("ERREUR", e)
    print(n, "paramètres contrôlés,", len(erreurs), "erreur(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
