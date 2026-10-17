"""Contrôle des descriptions du lot B (autoroute et grands axes) : chaque meylan/{auto_,axe_}*/description.yaml
est lu par le lecteur YAML du dépôt (description/yaml_simple.py), la clé `extensions_auto` (besoins notés dans
meylan/BESOINS_FORMAT_AUTO.md, pas encore lus par le compilateur) est retirée, puis la partie au format existant
est compilée par description/description_vers_modele.compiler, SANS rien écrire dans le dépôt.

    python recon/generateur/meylan/auto_outils/tester_descriptions_lotB.py [site ...]

Résumé écrit dans recon/out/generateur/meylan/auto_travail_lotB/tests_descriptions_lotB.json (non versionné) :
compilation réussie ou message d'erreur, nombre de sections, avertissements, non-conformités, règles utilisées,
et un contrôle de la clé extensions_auto (présence des rubriques attendues, provenance de chaque valeur).
Le compilateur appartient au lot « étape 2 » (autre workflow) : il est seulement importé, jamais modifié.
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # ne rien écrire (pas même __pycache__) dans les dossiers du compilateur de l'autre lot

RACINE = Path(__file__).resolve().parents[4]
GEN = RACINE / "recon" / "generateur"
sys.path.insert(0, str(GEN / "description"))
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(RACINE))

import yaml_simple as Y  # noqa: E402

try:
    import description_vers_modele as DVM  # noqa: E402
except Exception as e:  # le compilateur peut être en cours de modification par l'autre lot
    DVM = None
    ERREUR_IMPORT = repr(e)

MEYLAN = GEN / "meylan"
OUT = RACINE / "recon" / "out" / "generateur" / "meylan" / "auto_travail_lotB"
RUBRIQUES = ("etapes", "provenance")


def tester(site_dir):
    f = site_dir / "description.yaml"
    res = {"site": site_dir.name, "fichier": str(f.relative_to(RACINE)).replace("\\", "/")}
    texte = f.read_text(encoding="utf-8")
    try:
        d = Y.charger(texte)
    except Exception as e:
        res["yaml"] = "erreur : %s" % e
        return res
    res["yaml"] = "ok"
    ext = d.pop("extensions_auto", None)
    res["extensions_auto"] = {"presente": ext is not None,
                              "rubriques": sorted(ext.keys()) if isinstance(ext, dict) else [],
                              "manquantes": [r for r in RUBRIQUES if not (isinstance(ext, dict) and r in ext)]}
    if isinstance(ext, dict) and isinstance(ext.get("provenance"), dict):
        res["extensions_auto"]["n_provenances"] = len(ext["provenance"])
    if DVM is None:
        res["compilation"] = "compilateur non importable : %s" % ERREUR_IMPORT
        return res
    try:
        modele, rapport = DVM.compiler(d, source=res["fichier"])
    except Exception as e:
        res["compilation"] = "erreur : %s" % e
        return res
    res["compilation"] = "ok"
    res["routes"] = len(modele.get("routes", []))
    res["sections"] = sum(len(r.get("sections", [])) for r in modele.get("routes", []))
    res["profils"] = len(modele.get("profils", []))
    res["avertissements"] = rapport.get("avertissements", [])
    for t in rapport.get("troncons", []):
        res.setdefault("avertissements_troncons", []).extend(t.get("avertissements", []))
    res["non_conformites"] = rapport.get("non_conformites", [])
    res["regles_utilisees"] = len(rapport.get("regles_utilisees", []))
    val = rapport.get("validation") or rapport.get("validateur")
    if isinstance(val, dict):
        res["validation"] = {k: v for k, v in val.items() if k in ("erreurs", "n_erreurs", "ok", "prov_genres")}
    return res


def main():
    noms = sys.argv[1:]
    sites = sorted(p for p in MEYLAN.iterdir() if p.is_dir() and p.name.startswith(("auto_", "axe_"))
                   and (p / "description.yaml").exists() and (not noms or p.name in noms))
    tout = [tester(s) for s in sites]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tests_descriptions_lotB.json").write_text(json.dumps(tout, ensure_ascii=False, indent=1, default=str),
                                                      encoding="utf-8")
    for r in tout:
        print("%-34s yaml=%s compil=%s sections=%s nc=%s avert=%s ext=%s" % (
            r["site"], r.get("yaml"), str(r.get("compilation"))[:160], r.get("sections"),
            len(r.get("non_conformites") or []), len(r.get("avertissements") or []) + len(r.get("avertissements_troncons") or []),
            r.get("extensions_auto", {}).get("manquantes")))


if __name__ == "__main__":
    main()
