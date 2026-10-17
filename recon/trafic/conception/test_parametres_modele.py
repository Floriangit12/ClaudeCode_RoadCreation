"""Contrôle de assets/specs/trafic/parametres_modele.json (volet 04, conception v0.1).

  T1 forme : chaque paramètre a {id, couche, role, grandeur, loi, parametres, unite, nature, source{doc, page,
     annee}, confiance, usage, origine} ; couche, nature et confiance dans les listes admises.
  T2 traçabilité : loi et paramètres identiques au fichier d'origine (volets 01, 02, 03) ; source identique
     (document, page, année).
  T3 fraîcheur : les empreintes sha256 des fichiers d'entrée enregistrées dans meta correspondent aux fichiers
     actuels (sinon : relancer construire_parametres_modele.py).
  T4 renvois : règles, cibles, correspondances réseau et SUMO ne citent que des identifiants existants ; les
     groupes de tirage existent dans facteurs_latents.
  T5 conception : chaque cible porte au moins une référence sourcée (sauf V-24, convention) et une priorité ;
     chaque hypothèse a un plan de calage.
Avertissements (non bloquants) : paramètres dont la page source est vide dans le volet d'origine.

  python recon/trafic/conception/test_parametres_modele.py      -> code 1 si un test échoue
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
F = DEPOT / "assets" / "specs" / "trafic" / "parametres_modele.json"
COUCHES = {"PER", "STR", "TAC", "LON", "LAT", "VEH", "POP", "CTX", "VAL", "REF"}
NATURES = {"norme", "mesure", "donnee_administrative", "donnee_constructeur", "derive", "estimation", "convention",
           "defaut_logiciel", "calage", "mesure_simulation", "hypothese"}
CONFIANCES = {"elevee", "moyenne", "faible"}
CHAMPS = ["id", "couche", "role", "grandeur", "loi", "parametres", "unite", "nature", "source", "confiance", "usage", "origine"]


def charger(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def origines(meta):
    """Index {(volet, id): paramètre d'origine}."""
    out = {}
    J01 = charger(meta["entrees"]["01"]["fichier"])

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and "loi" in o:
                out[("01_Vehicules", o["id"])] = o
                return
            for k, v in o.items():
                if k not in ("meta", "sources", "lacunes"):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(J01)
    for p in charger(meta["entrees"]["02"]["fichier"])["parametres"]:
        out[("02_Conducteurs", p["id"])] = p
    for p in charger(meta["entrees"]["03"]["fichier"])["entrees"]:
        out[("03_Modeles_Existants", p["id"])] = p
    return out


def main():
    D = charger(F)
    P = D["parametres"]
    idx = {p["id"]: p for p in P}
    err, avert = [], []

    # T1
    if len(idx) != len(P):
        err.append("T1 identifiants en double")
    for p in P:
        for c in CHAMPS:
            if c not in p or p[c] in (None, "") and c not in ("parametres",):
                if c == "parametres" and p.get("loi") == "non renseigné":
                    continue
                err.append(f"T1 {p.get('id')} : champ {c} absent ou vide")
        if p.get("couche") not in COUCHES:
            err.append(f"T1 {p['id']} : couche {p.get('couche')}")
        if p.get("nature") not in NATURES:
            err.append(f"T1 {p['id']} : nature {p.get('nature')}")
        if p.get("confiance") not in CONFIANCES:
            err.append(f"T1 {p['id']} : confiance {p.get('confiance')}")
        s = p.get("source") or {}
        if not s.get("doc"):
            err.append(f"T1 {p['id']} : source.doc vide")
        if not s.get("page"):
            avert.append(f"{p['id']} : page source vide dans le volet d'origine")
        if s.get("annee") is None:
            if p.get("origine", {}).get("volet") == "04_Conception":
                err.append(f"T1 {p['id']} : source.annee vide")
            else:
                avert.append(f"{p['id']} : année absente dans la source d'origine (document non daté)")
    # T2
    O = origines(D["meta"])
    n_trace = 0
    for p in P:
        o = p["origine"]
        if o["volet"] == "04_Conception":
            continue
        q = O.get((o["volet"], o["id"]))
        if q is None:
            err.append(f"T2 {p['id']} : origine introuvable")
            continue
        if q.get("loi") != p["loi"] or q.get("parametres") != p["parametres"]:
            err.append(f"T2 {p['id']} : loi ou paramètres différents de l'origine")
        if q.get("tirage") != p.get("tirage"):
            err.append(f"T2 {p['id']} : tirage différent de l'origine")
        sq = q.get("source") or {}
        for k in ("page", "annee"):
            if sq.get(k) != p["source"].get(k):
                err.append(f"T2 {p['id']} : source.{k} différente de l'origine")
        n_trace += 1
    # T3
    for nom, e in D["meta"]["entrees"].items():
        h = hashlib.sha256(Path(e["fichier"]).read_bytes()).hexdigest()
        if h != e["sha256"]:
            err.append(f"T3 {nom} : {e['fichier']} a changé depuis la construction")
    # T4
    for r in D["regles"]:
        for x in r["parametres"]:
            if x not in idx:
                err.append(f"T4 règle {r['id']} : {x} inconnu")
    for c in D["validation"]["cibles"]:
        for x in c["references"] + c["sumo_par_defaut"]:
            if x["id"] not in idx:
                err.append(f"T4 cible {c['id']} : {x['id']} inconnu")
            elif x.get("valeurs", x.get("resultats")) != idx[x["id"]]["parametres"]:
                err.append(f"T4 cible {c['id']} : valeurs de {x['id']} non recopiées à l'identique")
    for c in D["correspondance_reseaux"]:
        l = c.get("loi")
        if l and l.split(" ")[0] in idx:
            continue
        if l and ("*" in l or "," in l or " " in l):
            continue  # renvoi descriptif (plusieurs lois)
        if l:
            err.append(f"T4 réseau {c['id']} : loi {l} inconnue")
    groupes = set(D["facteurs_latents"]["charges_par_groupe"]) | set(D["facteurs_latents"]["groupe_ajoute_v04"])
    for p in P:
        g = (p.get("tirage") or {}).get("groupe")
        if g and g not in groupes:
            err.append(f"T4 {p['id']} : groupe de tirage {g} inconnu")
    for l in D["correspondance_sumo"]["lignes"]:
        base = l["parametre"].split(" ")[0]
        if "*" not in base and base not in idx:
            err.append(f"T4 SUMO : {base} inconnu")
    # T5
    for c in D["validation"]["cibles"]:
        if not c["references"] and c["id"] != "V-24":
            err.append(f"T5 cible {c['id']} sans référence")
        if c.get("priorite") not in ("P1", "P2", "P3"):
            err.append(f"T5 cible {c['id']} sans priorité")
    for h in D["hypotheses"]:
        if not h.get("a_caler_sur"):
            err.append(f"T5 {h['id']} sans plan de calage")

    res = {"parametres": len(P), "traces_vers_origine": n_trace, "regles": len(D["regles"]),
           "cibles": len(D["validation"]["cibles"]), "hypotheses": len(D["hypotheses"]),
           "erreurs": err, "avertissements": avert}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "avertissements"}, ensure_ascii=False, indent=1))
    print(f"avertissements : {len(avert)}")
    for a in avert:
        print("  -", a)
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
