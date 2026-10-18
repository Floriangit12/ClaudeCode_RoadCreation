# -*- coding: utf-8 -*-
"""Tests du lot N1 (résolveur de la couche réseau) — CHAINE_CONSTRUCTION.md § 7.1, critère de fin du lot N1.

    python -B recon/generateur/reseau/tests/tester_reseau.py [--json SORTIE.json] [--sans-compositions]

T1  rétrocompatibilité : les 42 descriptions de référence de l'étape 2 (S01-S12, B01, J1-J6, G1-G4, A1-A4, exemples,
    M20/M24/M27) traversent le résolveur sans changer d'un octet ;
T2  exemples du format réseau (tests/exemples/R*.yaml) : résolus, compilés sans erreur ni non-conformité non admise ;
    l'exemple de l'utilisateur (R01) donne un terre-plein de 2 m entre 65 et 85 m avec ses têtes d'îlot de 19,5 m ;
T3  les 15 sites de Meylan : compilés par le chemin de la fabrication (description_vers_modele.compiler_fichier), 0
    erreur de validation ; contrôle CC-04 conforme à chaque nœud partagé portant un contrat de profil ;
T4  continuité entre sites : chaque nœud partagé de reseau_meylan.yaml est cité par les sites qu'il relie ;
    compositions (a41, rocade_sud, verdun_centre, helice, sept_laux) compilées sans erreur, raccords fusionnés CC-04 ;
T5  refus : vitesse approchée, nœud non déclaré, ancrages contradictoires, intervalle hors du tronçon, régime approché,
    dates d'état contradictoires ;
T6  déterminisme : deux résolutions (et deux compositions) donnent les mêmes octets ; relecture YAML identique.
Les sorties vont dans recon/out/generateur/reseau_n1/tests/ (non versionné).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RES = ICI.parent
GEN = RES.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(RES))
sys.path.insert(0, str(GEN))
import resoudre_reseau as RR  # noqa: E402
import composer as CO  # noqa: E402
from description import description_vers_modele as D  # noqa: E402
from description import yaml_simple  # noqa: E402

SORTIE = DEPOT / "recon" / "out" / "generateur" / "reseau_n1" / "tests"
REFERENCES = (sorted((GEN / "scenes_simples").glob("S*.yaml")) + sorted((GEN / "scenes_simples").glob("B*.yaml"))
              + sorted((GEN / "scenes_carrefours").glob("J*.yaml")) + sorted((GEN / "scenes_giratoires").glob("G*.yaml"))
              + sorted((GEN / "scenes_autoroutes").glob("A*.yaml")) + sorted((GEN / "description" / "exemples").glob("*.yaml"))
              + sorted((GEN / "scenes_meylan").glob("M*.yaml")))
SITES = sorted(p.name for p in (GEN / "meylan").iterdir() if (p / "description.yaml").exists())
COMPOSITIONS = ["a41", "rocade_sud", "verdun_centre", "helice", "sept_laux"]


def ok(nom, cond, detail=None):
    return {"test": nom, "statut": "ok" if cond else "ECHEC", "detail": detail}


def t1():
    out = []
    for f in REFERENCES:
        texte, d, rap, octets = RR.resoudre_fichier(f)
        out.append(ok(f"T1 {f.parent.name}/{f.name}", rap.get("inchangee") and texte.encode("utf-8") == octets))
    return out


def t2():
    out = []
    for f in sorted((ICI / "exemples").glob("R*.yaml")):
        if "reseau_commun" in f.name:
            continue
        try:
            rap, rc, sortie = RR.traiter(f, SORTIE / "exemples" / f.stem)
            out.append(ok(f"T2 {f.name}", rc["validation"]["nb_erreurs"] == 0 and not rc["non_conformites"],
                          {"approximations": len(rap.get("approximations") or []), "fusions": len(rap.get("fusions") or []),
                           "non_conformites": len(rc["non_conformites"])}))
            if f.stem.startswith("R01"):
                m = json.loads((sortie / "modele_voie.json").read_text(encoding="utf-8"))
                P = {p["id"]: p for p in m["profils"]}
                tp = [(s["s0"], s["s1"]) for s in m["routes"][0]["sections"]
                      if any(b["type"] == "terre_plein" for b in P[s["profil"]]["bandes"])]
                w = [b["largeur"] for s in m["routes"][0]["sections"] for b in P[s["profil"]]["bandes"]
                     if b["type"] == "terre_plein"]
                ins = rap["troncons"]["R1"]["insertions"][0]
                out.append(ok("T2 R01 terre-plein de 2 m de 65 à 85 m, têtes d'îlot de 19,5 m",
                              tp == [(65.0, 85.0)] and w == [2.0] and ins["tetes_ilot_m"] == [19.5, 19.5],
                              {"terre_plein": tp, "largeur": w, "tetes": ins["tetes_ilot_m"]}))
        except Exception as e:
            out.append(ok(f"T2 {f.name}", False, f"{type(e).__name__}: {e}"))
    return out


def t3():
    out = []
    for site in SITES:
        f = GEN / "meylan" / site / "description.yaml"
        try:
            m, rc, sortie = D.compiler_fichier(f, SORTIE / "sites" / site)
            rap = json.loads((sortie / "compilation_reseau.json").read_text(encoding="utf-8"))
            cc = rap.get("raccords") or []
            out.append(ok(f"T3 {site}", rc["validation"]["nb_erreurs"] == 0 and all(
                c["statut"] == "conforme" for c in cc if c.get("bloquant", True)),
                {"date": rc.get("scene") and m["meta"].get("date"), "routes": len(m["routes"]),
                 "non_conformites_non_admises": len(rc["non_conformites"]),
                 "cc04": [f"{c['noeud']}:{c['statut']}" for c in cc],
                 "fusions_internes": len(rap.get("fusions") or [])}))
        except Exception as e:
            out.append(ok(f"T3 {site}", False, f"{type(e).__name__}: {e}"))
    return out


def t4(compositions=True):
    out = []
    R = RR.charger_yaml(GEN / "meylan" / "reseau_meylan.yaml")
    cites = {}
    for site in SITES:
        texte = (GEN / "meylan" / site / "description.yaml").read_text(encoding="utf-8")
        for n in R["noeuds"]:
            if n in texte:
                cites.setdefault(n, set()).add(site)
    for n, spec in R["noeuds"].items():
        attendus = set(spec.get("sites") or [])
        out.append(ok(f"T4 nœud {n} cité par {sorted(attendus)}", attendus <= cites.get(n, set()),
                      {"cite_par": sorted(cites.get(n, set()))}))
    if compositions:
        for c in COMPOSITIONS:
            try:
                rap, rc, sortie = RR.traiter(None, SORTIE / "compositions" / c, composer_nom=c)
                cc = rap.get("raccords") or []
                out.append(ok(f"T4 composition {c}", rc["validation"]["nb_erreurs"] == 0 and all(
                    x["statut"] == "conforme" for x in cc),
                    {"routes": rap["resume"]["fusions"], "fusions": [f["noeud"] for f in rap.get("fusions") or []],
                     "non_fusionnes": [x["noeud"] for x in rap.get("noeuds_non_fusionnes") or []],
                     "cc04": [f"{x['noeud']}:{x['statut']}" for x in cc]}))
            except Exception as e:
                out.append(ok(f"T4 composition {c}", False, f"{type(e).__name__}: {e}"))
    return out


BASE = {"format": "description_reseau/0.1", "contexte": {"agglomeration": "oui", "vitesse": 50},
        "noeuds": {"A": {"position": [0, 0]}, "B": {"position": [100, 0]}},
        "troncons": [{"id": "R1", "de": "A", "vers": "B", "profil": "trottoir | voie ← | voie → | trottoir"}]}


def t5():
    cas = []
    d = copy.deepcopy(BASE)
    d["contexte"]["vitesse"] = "≈ 50"
    cas.append(("vitesse approchée", d))
    d = copy.deepcopy(BASE)
    d["troncons"][0]["vers"] = "Z"
    cas.append(("nœud non déclaré", d))
    d = copy.deepcopy(BASE)
    d["noeuds"]["B"] = {"position": [100, 0], "depuis": "A", "distance": 80, "cap": 0}
    cas.append(("ancrages contradictoires", d))
    d = copy.deepcopy(BASE)
    d["troncons"][0]["evenements"] = ["de ≈ 90 à ≈ 120 : terre-plein planté"]
    cas.append(("intervalle hors du tronçon", d))
    d = copy.deepcopy(BASE)
    d["carrefours"] = [{"id": "C", "noeud": "B", "regime": "≈ feux", "branches": [{"troncon": "R1"}]}]
    cas.append(("régime approché", d))
    d = copy.deepcopy(BASE)
    d["date"] = "2025-05-18"
    d["date_etat"] = "2026-07-28"
    cas.append(("dates d'état contradictoires", d))
    out = []
    for nom, d in cas:
        try:
            RR.resoudre_dict(d, "test")
            out.append(ok(f"T5 refus : {nom}", False, "accepté"))
        except (RR.ErreurReseau, D.ErreurDescription) as e:
            out.append(ok(f"T5 refus : {nom}", True, str(e)[:160]))
    return out


def t6():
    out = []
    for f in [ICI / "exemples" / "R01_terre_plein_20m.yaml", GEN / "meylan" / "axe_verdun_centre" / "description.yaml",
              GEN / "meylan" / "paquet_jardin" / "description.yaml"]:
        a = RR.resoudre_fichier(f)[0]
        b = RR.resoudre_fichier(f)[0]
        out.append(ok(f"T6 déterminisme {f.parent.name}/{f.name}", a == b, hashlib.sha256(a.encode()).hexdigest()[:16]))
    a = CO.composer("verdun_centre")[0]
    b = CO.composer("verdun_centre")[0]
    out.append(ok("T6 déterminisme composition verdun_centre", a == b, hashlib.sha256(a.encode()).hexdigest()[:16]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(SORTIE / "rapport_tests.json"))
    ap.add_argument("--sans-compositions", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    res = t1() + t2() + t3() + t4(not a.sans_compositions) + t5() + t6()
    for r in res:
        print(f"{r['statut']:6s} {r['test']}" + (f"  {json.dumps(r['detail'], ensure_ascii=False)[:220]}" if r["detail"]
                                                 and r["statut"] != "ok" else ""))
    n_ok = sum(1 for r in res if r["statut"] == "ok")
    print(f"{n_ok} / {len(res)} tests réussis")
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps({"resultats": res, "reussis": n_ok, "total": len(res)}, ensure_ascii=False,
                                       indent=1) + "\n", encoding="utf-8")
    return 0 if n_ok == len(res) else 1


if __name__ == "__main__":
    sys.exit(main())
