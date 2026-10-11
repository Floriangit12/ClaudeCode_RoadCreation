"""Vérificateur automatique des règles de conception (assets/specs/regles_conception.json) sur la description v2
et sur la fabrication Houdini (fabrique_hda).

    python recon/pcg/controle/verifier_regles.py [--description DIR] [--fabrique DIR] [--sortie DIR]
                                                 [--regles ID,ID...] [--forcer-extraction]

Pour chaque règle d'action « verifier » (principale ou secondaire) et pour les règles « contraindre » mesurables, un
contrôle (modules ctl_*.py, décorateur @regle) mesure la scène et rend : n_teste, n_ok, n_violations, pires cas
(entité, coordonnées locales et Lambert-93, valeur, seuil), sévérité. Les règles sans contrôle sont listées avec
la raison. Sorties dans <sortie> (défaut recon/out/paquet_jardin/v2/controle) :
    rapport_regles.json    tout le détail (déterministe : tri fixe, arrondis fixes, aucun horodatage)
    RAPPORT_REGLES.md      synthèse par famille et 30 pires violations
Les USD sont lus via un cache numpy (extraire_fabrication.py, lancé dans hython si une source a changé).
"""
import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import ctl_commun as K  # noqa: E402
import ctl_sol  # noqa: E402,F401
import ctl_marquages  # noqa: E402,F401
import ctl_reseau  # noqa: E402,F401
import ctl_detection  # noqa: E402,F401
import ctl_tq  # noqa: E402,F401
from rapport import ecrire_md, NON_IMPLEMENTEES  # noqa: E402

SEV_ORDRE = ["bloquant", "majeur", "mineur", "info"]


def est_verifier(r):
    return r["action"] == "verifier" or "verifier" in (r.get("actions_secondaires") or [])


def principal():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--description", default=str(K.DESCRIPTION / "base"))
    ap.add_argument("--fabrique", default=str(K.FABRIQUE))
    ap.add_argument("--sortie", default=str(K.SORTIE))
    ap.add_argument("--regles", default="")
    ap.add_argument("--forcer-extraction", action="store_true")
    ap.add_argument("--chrono", action="store_true", help="affiche la durée de chaque contrôle (non écrite)")
    a = ap.parse_args()
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    ctx = K.Contexte(a.description, a.fabrique)
    if a.forcer_extraction:
        K.assurer_cache(True)
    base = ctx.regles
    regles = base["regles"]
    choix = set(x for x in a.regles.split(",") if x)
    resultats = {}
    for r in regles:
        rid = r["id"]
        if choix and rid not in choix:
            continue
        if rid not in K.REGISTRE:
            continue
        f, cible, sev, methode, statut, limites = K.REGISTRE[rid]
        res = K.Resultat(rid, cible, sev, methode, statut, limites)
        t0 = time.time()
        try:
            f(ctx, res)
        except Exception as e:      # un contrôle en échec est rapporté, les autres continuent
            res.statut = "erreur_execution"
            res.limites = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        d = res.dict()
        if a.chrono:
            print(f"  {rid:<12} {time.time() - t0:6.1f} s  testés {d['n_teste']:>6}  violations {d['n_violations']:>5}")
        resultats[rid] = d
    if choix:
        for rid in sorted(resultats):
            d = resultats[rid]
            print(f"== {rid} [{d['statut']}] testés {d['n_teste']} ok {d['n_ok']} violations {d['n_violations']}"
                  + (f" ({d['limites']})" if d["statut"] == "erreur_execution" else ""))
            print("   mesures :", json.dumps(d["mesures"], ensure_ascii=False)[:1500])
            for v in d["pires_cas"][:6]:
                print("   -", v.get("entite"), v.get("xy_local"), v.get("valeur"), "|", v.get("detail"))
        return 0
    rapport = construire_rapport(ctx, base, resultats)
    (sortie / "rapport_regles.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8")
    ecrire_md(rapport, sortie / "RAPPORT_REGLES.md")
    s = rapport["synthese"]
    print(json.dumps({k: s[k] for k in ("verifier", "contraindre", "toutes")}, ensure_ascii=False))
    return 0


def construire_rapport(ctx, base, resultats):
    regles = base["regles"]
    cache = ctx.cache
    entree = {
        "regles": {"fichier": "assets/specs/regles_conception.json", "version": base.get("version"),
                   "sha256": K.sha256(K.SPECS / "regles_conception.json"), "n": len(regles)},
        "description": {"dossier": K.Path(ctx.dbase).resolve().relative_to(K.RACINE).as_posix(),
                        "hash_description": ctx.manifeste.get("hash_description"),
                        "schema": ctx.manifeste.get("schema")},
        "fabrication": {"dossier": K.Path(ctx.fab).resolve().relative_to(K.RACINE).as_posix(),
                        "description_lue": ctx.manifeste_fab.get("description"),
                        "hash_description_lu": ctx.manifeste_fab["fabrication"]["lecteur"].get("hash_description"),
                        "couches": {k: {"sha256": v.get("sha256"), "triangles": v.get("triangles")}
                                    for k, v in sorted(cache["couches"].items())}},
    }
    par_regle = {}
    toutes_v = []
    for r in regles:
        rid = r["id"]
        verif = est_verifier(r)
        cat = "verifier" if verif else ("contraindre" if r["action"] == "contraindre" else r["action"])
        info = {"famille": r["famille"], "sous_famille": r.get("sous_famille"), "action": r["action"],
                "actions_secondaires": r.get("actions_secondaires") or [], "categorie": cat,
                "confiance": r.get("confiance"), "enonce": r["enonce"]}
        if rid in resultats:
            d = dict(resultats[rid])
            toutes = d.pop("_toutes")
            for v in toutes:
                toutes_v.append(dict(v, regle=rid, famille=r["famille"]))
            info.update(d)
        else:
            raison = NON_IMPLEMENTEES.get(rid)
            if raison is None:
                raison = ("règle de génération ou d'inférence : sa conformité est mesurée par les règles « verifier » "
                          "associées" if r["action"] in ("generer", "deduire_si_absent") and not verif
                          else "non mesurable dans les fichiers (réglage ou pratique hors description et fabrication)")
            info.update({"statut": "non_implemente", "raison": raison})
        par_regle[rid] = info
    # synthèse
    def bilan(sel):
        ids = [r["id"] for r in regles if sel(r)]
        st = [par_regle[i]["statut"] for i in ids]
        n_impl = sum(1 for x in st if x in ("implemente", "partiel"))
        return {"n": len(ids), "implementees": sum(1 for x in st if x == "implemente"),
                "partielles": sum(1 for x in st if x == "partiel"),
                "non_implementees": sum(1 for x in st if x == "non_implemente"),
                "erreurs": sum(1 for x in st if x == "erreur_execution"),
                "taux_couverture": K.r4(n_impl / len(ids), 3) if ids else None,
                "avec_violation": sum(1 for i in ids if (par_regle[i].get("n_violations") or 0) > 0)}
    familles = {}
    for r in regles:
        f = r["famille"]
        d = familles.setdefault(f, {"regles": 0, "controlees": 0, "n_teste": 0, "n_violations": 0,
                                    "regles_en_violation": 0, "par_severite": {s: 0 for s in SEV_ORDRE}})
        d["regles"] += 1
        pr = par_regle[r["id"]]
        if pr["statut"] in ("implemente", "partiel"):
            d["controlees"] += 1
            d["n_teste"] += pr["n_teste"]
            d["n_violations"] += pr["n_violations"]
            if pr["n_violations"]:
                d["regles_en_violation"] += 1
                d["par_severite"][pr["severite"]] += pr["n_violations"]
    top = sorted(toutes_v, key=lambda v: (-K.POIDS[v["severite"]], -(v["ecart"] or 0), v["regle"], str(v["entite"])))
    vus, top30 = {}, []
    for v in top:                       # au plus 3 cas par règle dans les 30 pires (diversité)
        if vus.get(v["regle"], 0) >= 3:
            continue
        vus[v["regle"]] = vus.get(v["regle"], 0) + 1
        top30.append(v)
        if len(top30) == 30:
            break
    synthese = {
        "verifier": bilan(est_verifier),
        "contraindre": bilan(lambda r: r["action"] == "contraindre" and not est_verifier(r)),
        "contraindre_controlees": sum(1 for r in regles if r["action"] == "contraindre" and not est_verifier(r)
                                      and par_regle[r["id"]]["statut"] in ("implemente", "partiel")),
        "toutes": bilan(lambda r: True),
        "par_famille": familles,
        "violations_par_severite": {s: sum(1 for v in toutes_v if v["severite"] == s) for s in SEV_ORDRE},
    }
    return {"schema": "pj_rapport_regles/0.1", "entrees": entree, "synthese": synthese, "top_violations": top30,
            "regles": par_regle,
            "non_implementees": [{"id": r["id"], "categorie": par_regle[r["id"]]["categorie"],
                                  "raison": par_regle[r["id"]]["raison"]} for r in regles
                                 if par_regle[r["id"]]["statut"] == "non_implemente"
                                 and par_regle[r["id"]]["categorie"] in ("verifier", "contraindre")]}


if __name__ == "__main__":
    sys.exit(principal())
