# -*- coding: utf-8 -*-
"""Rapport du lot L0 : rejoue tous les contrôles et écrit validation/rapport_L0.json (critères valeur / seuil / atteint).

    python recon/generateur/validation/faire_rapport_L0.py

Étapes : migration des 2 exemples du dossier 12 (relancée, sortie comparée à l'octet) ; tests de l'inférence
(cas de tags, réseaux, validateur) ; tests de la description (exemples, catalogue voisin, faits, erreurs) ;
inférence sur l'extrait OSM réel du site (deux fois, comparaison à l'octet) ; compilation de toutes les descriptions
vers recon/out/generateur/<scene>/ (non versionné). Aucune date d'exécution n'est écrite : deux exécutions donnent
le même rapport.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
PY = sys.executable
TMP = GEN / "tmp" / "l0" / "rapport"


def lancer(*args):
    r = subprocess.run([PY, *map(str, args)], cwd=DEPOT, capture_output=True, text=True, encoding="utf-8",
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout, r.stderr


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    TMP.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(GEN))
    import regles
    rapport = {"lot": "L0", "plan": "recon/generateur/PLAN_GENERATEUR.md § 3", "base_regles": regles.empreinte(), "etapes": {}}
    # 1. migration des exemples (relancée : doit redonner les mêmes octets)
    ex = GEN / "schema" / "exemples"
    avant = {p.name: sha(p) for p in sorted(ex.glob("*.json"))}
    code, out, err = lancer(GEN / "schema" / "migrer_exemples.py")
    apres = {p.name: sha(p) for p in sorted(ex.glob("*.json"))}
    mig = json.loads((ICI / "migration_exemples_L0.json").read_text(encoding="utf-8"))
    rapport["etapes"]["migration"] = {"code": code, "identiques_apres_relance": avant == apres, "sha256": apres,
                                      "sans_equivalent": {k: v["manques"] for k, v in mig["exemples"].items()},
                                      "citations_migrees": {k: v["migrees"] for k, v in mig["exemples"].items()}}
    # 2. tests de l'inférence
    code, out, err = lancer(GEN / "inference" / "tests" / "tester_inference.py", "--json", ICI / "tests_inference_L0.json")
    ti = json.loads((ICI / "tests_inference_L0.json").read_text(encoding="utf-8"))
    rapport["etapes"]["tests_inference"] = {"code": code, **ti["bilan"],
                                            "echecs": [x["id"] for x in ti["tags"] + ti["reseaux"] + ti["validateur"] if not x["ok"]]}
    # 3. tests de la description
    code, out, err = lancer(GEN / "description" / "tests" / "tester_descriptions.py", "--json", ICI / "tests_description_L0.json")
    td = json.loads((ICI / "tests_description_L0.json").read_text(encoding="utf-8"))
    rapport["etapes"]["tests_description"] = {"code": code, **td["bilan"],
                                              "echecs": [x.get("fichier", x.get("id", x.get("fait"))) for x in
                                                         td["exemples"] + td["catalogue_voisin"] + td.get("meylan", []) + td["faits"] + td["erreurs"] if not x["ok"]]}
    # 4. inférence sur l'extrait OSM réel du site (routes + traversées), deux fois
    v = DEPOT / "data" / "sites" / "paquet_jardin" / "vector"
    shas, infos = [], None
    for k in (1, 2):
        code, out, err = lancer(GEN / "inference" / "osm_vers_modele.py", v / "osm_roads.geojson", v / "osm_crossings.geojson",
                                "--sortie", TMP / f"osm_pj{k}", "--agglomeration", "oui", "--nom", "osm_paquet_jardin")
        shas.append(sha(TMP / f"osm_pj{k}" / "modele_voie.json"))
        infos = json.loads((TMP / f"osm_pj{k}" / "inference.json").read_text(encoding="utf-8"))
    rapport["etapes"]["inference_osm_site"] = {"entrees": ["data/sites/paquet_jardin/vector/osm_roads.geojson",
                                                           "data/sites/paquet_jardin/vector/osm_crossings.geojson"],
                                               "routes": infos["routes"], "profils": infos["profils"], "carrefours": infos["carrefours"],
                                               "carrefours_a_verifier": len(infos["a_verifier"]),
                                               "erreurs_validation": infos["validation"]["nb_erreurs"],
                                               "prov_genres": infos["validation"]["prov_genres"],
                                               "deterministe": shas[0] == shas[1], "sha256": shas[0],
                                               "avertissements": len(infos["avertissements"])}
    # 5. compilation des descriptions vers recon/out/generateur/<scene>/
    sorties = []
    for f in (sorted((GEN / "description" / "exemples").glob("*.yaml")) + sorted((GEN / "scenes_simples").glob("S*.yaml"))
              + sorted((GEN / "scenes_meylan").glob("*.yaml"))):
        code, out, err = lancer(GEN / "description" / "description_vers_modele.py", f)
        ligne = [l for l in out.splitlines() if " → " in l]
        sorties.append({"description": str(f.relative_to(GEN)).replace("\\", "/"), "code": code,
                        "sortie": ligne[-1].split(" → ")[-1].replace("\\", "/") if ligne else None})
    rapport["etapes"]["compilation_sorties"] = sorties
    # critères du lot (PLAN § 3 et commande du lot)
    tinf, tdes, osm = rapport["etapes"]["tests_inference"], rapport["etapes"]["tests_description"], rapport["etapes"]["inference_osm_site"]
    sorties_ok = sum(1 for s in sorties if s["code"] == 0)
    crit = [
        {"id": "L0-1 cas de test de tags", "valeur": f"{tinf['cas_tags']} cas", "seuil": "≥ 32", "atteint": tinf["cas_tags"] >= 32},
        {"id": "L0-2 cas de test donnant le profil attendu", "valeur": f"{tinf['reussis']} / {tinf['cas']} (tags, réseaux, validateur)",
         "seuil": "100 %", "atteint": tinf["reussis"] == tinf["cas"]},
        {"id": "L0-3 highway=stop seul → stop_a_verifier, ni AB4 ni ligne ; + FR:AB4 → stop (ARB-19)",
         "valeur": "R03 et R14 : stop_a_verifier sans ligne ni AB4 ; R04 : stop, ligne STOP, AB4" if not {"R03", "R04", "R14"} & set(tinf["echecs"]) else "échec",
         "seuil": "conforme", "atteint": not {"R03", "R04", "R14"} & set(tinf["echecs"])},
        {"id": "L0-4 valider_modele : 0 erreur sur les 2 exemples migrés", "valeur": "0 erreur" if not {"V-exemple_rue_carrefour.json", "V-exemple_rue_residentielle.json"} & set(tinf["echecs"]) else "erreurs",
         "seuil": "0 erreur", "atteint": not {"V-exemple_rue_carrefour.json", "V-exemple_rue_residentielle.json"} & set(tinf["echecs"])},
        {"id": "L0-5 valider_modele (provenance exigée, C01-C13) : 0 erreur sur les sorties",
         "valeur": f"inférence : {tinf['cas_reseaux']} réseaux de test + extrait réel ({osm['erreurs_validation']} erreur) ; description : "
                   f"{tdes['compilent_valides']} / {tdes['descriptions']} sans erreur",
         "seuil": "0 erreur", "atteint": osm["erreurs_validation"] == 0 and tdes["compilent_valides"] == tdes["descriptions"]
         and not [x for x in tinf["echecs"] if x.startswith("R")]},
        {"id": "L0-6 C11 rejette un identifiant inconnu (RF-OSM-LAR-999)", "valeur": "rejeté" if "V-C11" not in tinf["echecs"] else "accepté",
         "seuil": "rejeté", "atteint": "V-C11" not in tinf["echecs"]},
        {"id": "L0-7 déterminisme (deux exécutions identiques à l'octet)",
         "valeur": f"descriptions {tdes['deterministes']} / {tdes['descriptions']} ; réseaux de test {tinf['cas_reseaux']} ; extrait OSM réel : "
                   f"{'identique' if osm['deterministe'] else 'différent'} ; migration : {'identique' if rapport['etapes']['migration']['identiques_apres_relance'] else 'différente'}",
         "seuil": "100 % identiques", "atteint": tdes["deterministes"] == tdes["descriptions"] and osm["deterministe"]
         and rapport["etapes"]["migration"]["identiques_apres_relance"]},
        {"id": "L0-8 exemples de description compilant en modèle valide",
         "valeur": f"{tdes['compilent_valides']} / {tdes['descriptions']} ({tdes['exemples']} exemples + {tdes['catalogue_voisin']} scènes du catalogue voisin)",
         "seuil": "100 %", "atteint": tdes["compilent_valides"] == tdes["descriptions"]},
        {"id": "L0-9 scènes du catalogue voisin écrites dans le format (attendus vérifiables au niveau du modèle)",
         "valeur": f"{tdes['catalogue_attendus_ok']} / {tdes['catalogue_voisin']}", "seuil": "100 %",
         "atteint": tdes["catalogue_attendus_ok"] == tdes["catalogue_voisin"]},
        {"id": "L0-10 faits attendus sur les exemples (règles appliquées)", "valeur": f"{tdes['faits_ok']} / {tdes['faits']}", "seuil": "100 %",
         "atteint": tdes["faits_ok"] == tdes["faits"]},
        {"id": "L0-11 refus attendus (valeur sans règle, interdits réglementaires, clés inconnues)",
         "valeur": f"{tdes['erreurs_ok']} / {tdes['erreurs_attendues']}", "seuil": "100 %", "atteint": tdes["erreurs_ok"] == tdes["erreurs_attendues"]},
        {"id": "L0-12 sorties écrites dans recon/out/generateur/<scene>/", "valeur": f"{sorties_ok} / {len(sorties)}", "seuil": "100 %",
         "atteint": sorties_ok == len(sorties)},
    ]
    # critères ajoutés par la correction après contrôle (relecture adverse de l'étape 1)
    faits = {x["id"]: x for x in td["erreurs"]}
    def ok(*ids):
        return all(faits.get(i, {}).get("ok") for i in ids)
    crit += [
        {"id": "L0-13 dévers des accotements hors agglomération (RF-GV-DEV-001 : bande dérasée 4 %, berme 8 %, provenance "
               "de chaque dévers) ; S01 sortait à 2,5 % (RF-OSM-NIV-010)",
         "valeur": "test F4 " + ("conforme" if ok("F4") else "échec") + f" ; {faits.get('F4', {}).get('detail')}",
         "seuil": "4 % et 8 %, règle citée", "atteint": ok("F4")},
        {"id": "L0-14 chevauchements refusés (deux passages, plateau + dos-d'âne) et interdits réglementaires bloquants "
               "(dos-d'âne ou plateau hors agglomération ou à plus de 30 km/h), sauf écart admis explicite (motif)",
         "valeur": "E10 " + str(ok("E10")) + ", E11 " + str(ok("E11")) + ", E12 " + str(ok("E12")) + ", E13 " + str(ok("E13"))
                   + ", E14 " + str(ok("E14")) + ", E15 " + str(ok("E15")) + ", F3 " + str(ok("F3")),
         "seuil": "100 %", "atteint": ok("E10", "E11", "E12", "E13", "E14", "E15", "F3")},
        {"id": "L0-15 fabrication refusée sur un contrôle non conforme ou hors plage non admis (fabriquer_generateur."
               "preparer_entree lit compilation.json, plus seulement « 0 erreur(s) »)",
         "valeur": "test F5 " + ("conforme" if ok("F5") else "échec"), "seuil": "refus", "atteint": ok("F5")},
        {"id": "L0-16 arbres : dimensions portées dans le modèle (essence, hauteur, houppier, fût au gabarit RF-OSM-VEG-001)",
         "valeur": "tests F6, E16 : " + ("conformes" if ok("F6", "E16") else "échec"), "seuil": "100 %", "atteint": ok("F6", "E16")},
        {"id": "L0-17 lecteur YAML minimal contrôlé par PyYAML (Python du système)", "valeur": str(faits.get("Y1", {}).get("titre")),
         "seuil": "identique (saut de ligne final, dates nues)", "atteint": ok("Y1")},
        {"id": "L0-18 rues réelles de Meylan décrites d'après photo (scenes_meylan) : compilent, 0 non-conformité non admise",
         "valeur": f"{sum(1 for x in td.get('meylan', []) if x.get('ok'))} / {len(td.get('meylan', []))}", "seuil": "3 / 3",
         "atteint": len(td.get("meylan", [])) >= 3 and all(x.get("ok") for x in td.get("meylan", []))},
    ]
    rapport["criteres"] = crit
    rapport["statut"] = "ok" if all(c["atteint"] for c in crit) else "partiel"
    (ICI / "rapport_L0.json").write_bytes((json.dumps(rapport, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    for c in crit:
        print(f"{'ATTEINT' if c['atteint'] else 'NON ATTEINT'}\t{c['id']}\t{c['valeur']}\t(seuil {c['seuil']})")
    print(f"statut : {rapport['statut']}")
    return 0 if rapport["statut"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
