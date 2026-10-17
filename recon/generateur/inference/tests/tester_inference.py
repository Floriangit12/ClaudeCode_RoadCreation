# -*- coding: utf-8 -*-
"""Tests du lot L0 : inférence OSM → modèle, validateur corrigé, déterminisme.

    python recon/generateur/inference/tests/tester_inference.py [--json FICHIER]   (défaut : recon/generateur/tmp/tests/tests_inference_L0.json ;
    seul validation/faire_rapport_L0.py écrit la version versionnée validation/tests_inference_L0.json)

- cas_tags.json : tags d'un way → profil attendu (bandes, limites, catégorie, vitesse…) ;
- cas_carrefours.json : petits réseaux → régimes de branche (dont ARB-19), giratoire, passages, modération, ouvrage ;
  chaque modèle produit passe le validateur avec provenance exigée (C01-C13) et sort identique à l'octet deux fois ;
- validateur : C11 rejette un identifiant inconnu (RF-OSM-LAR-999) ; C13 rejette un AB4 sur une branche
  stop_a_verifier ; les 2 exemples migrés du dossier 12 donnent 0 erreur.
Code retour 0 si tous les cas passent.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(GEN / "inference"))
sys.path.insert(0, str(GEN / "schema"))
import osm_vers_modele as I  # noqa: E402
import valider_modele as VM  # noqa: E402
from commun import profil as PF  # noqa: E402

O = (917279.43, 6460289.98)


def comparer_profil(cas):
    p, info, av, ctrl = I.profil_depuis_tags(cas["tags"], cas.get("agglomeration"))
    a = cas["attendu"]
    rs = PF.resume(p)
    ecarts = []
    if "bandes" in a and rs["bandes"] != a["bandes"]:
        ecarts.append({"champ": "bandes", "attendu": a["bandes"], "obtenu": rs["bandes"]})
    if "limites" in a and rs["limites"] != a["limites"]:
        ecarts.append({"champ": "limites", "attendu": a["limites"], "obtenu": rs["limites"]})
    for k in ("categorie", "vitesse_kmh", "sens_unique", "u_m"):
        if k in a and info.get(k) != a[k]:
            ecarts.append({"champ": k, "attendu": a[k], "obtenu": info.get(k)})
    if "reference" in a and p["reference"] != a["reference"]:
        ecarts.append({"champ": "reference", "attendu": a["reference"], "obtenu": p["reference"]})
    if "avertissement_contient" in a and not any(a["avertissement_contient"] in w for w in av):
        ecarts.append({"champ": "avertissements", "attendu": f"contient « {a['avertissement_contient']} »", "obtenu": av})
    if "materiau_voies" in a:
        m = sorted({b.get("materiau_id") for b in p["bandes"] if b["type"] == "voie_circulation"})
        if m != [a["materiau_voies"]]:
            ecarts.append({"champ": "materiau_voies", "attendu": a["materiau_voies"], "obtenu": m})
    for k, nat in a.get("limite_natures", {}).items():
        obt = p["limites"][int(k)]["nature"]
        if sorted(obt) != sorted(nat):
            ecarts.append({"champ": f"limites[{k}].nature", "attendu": nat, "obtenu": obt})
    if "separateur_type" in a:
        st = [l["separateur"]["type"] for l in p["limites"] if "separateur" in l]
        if a["separateur_type"] not in st:
            ecarts.append({"champ": "separateur", "attendu": a["separateur_type"], "obtenu": st})
    # la provenance de chaque bande cite une règle existante ou un tag OSM
    err, _, _ = VM.valider({"schema": "modele_voie/0.1", "repere": {"crs": "EPSG:2154", "origine_l93": [0, 0, 0]},
                            "profils": [p], "noeuds": [], "routes": []}, exiger_prov=True)
    if err:
        ecarts.append({"champ": "validation", "attendu": "0 erreur", "obtenu": [list(e) for e in err][:5]})
    return ecarts, rs


def reseau(cas):
    nd = {int(k): {"xy": (O[0] + v[0], O[1] + v[1]), "tags": dict(cas.get("tags_noeuds", {}).get(k, {}))} for k, v in cas["noeuds"].items()}
    ways = {w["id"]: {"noeuds": list(w["noeuds"]), "tags": dict(w["tags"])} for w in cas["ways"]}
    return {"noeuds": nd, "ways": ways, "relations": {}, "bornes_l93": None,
            "source": {"fichier": f"(test {cas['id']})", "format": "test", "sha256": "", "octets": 0}}


def _branches(modele, way, extremite=None):
    rids = {r["id"] for r in modele["routes"] if way in r["osm"]["ways"]}
    out = []
    for c in modele.get("carrefours", []):
        for b in c["branches"]:
            if b["route"] in rids and (extremite is None or b["extremite"] == extremite):
                out.append((c, b))
    return out


def comparer_reseau(cas):
    d = reseau(cas)
    m1, r1 = I.construire(copy.deepcopy(d), cas.get("agglomeration", True), None, cas["id"])
    m2, _ = I.construire(copy.deepcopy(d), cas.get("agglomeration", True), None, cas["id"])
    o1 = json.dumps(m1, ensure_ascii=False, indent=1).encode("utf-8")
    o2 = json.dumps(m2, ensure_ascii=False, indent=1).encode("utf-8")
    a = cas["attendu"]
    ecarts = []
    if o1 != o2:
        ecarts.append({"champ": "determinisme", "attendu": "identique", "obtenu": "différent"})
    if r1["validation"]["nb_erreurs"]:
        ecarts.append({"champ": "validation", "attendu": "0 erreur", "obtenu": r1["validation"]["erreurs"][:5]})
    sigs = {s["id"]: s for s in m1.get("signaux", [])}
    if "carrefour" in a:
        ac = a["carrefour"]
        cs = [c for c in m1.get("carrefours", []) if "noeud" not in ac or f"N-{ac['noeud']}" in c["noeuds"]]
        if not cs:
            ecarts.append({"champ": "carrefour", "attendu": ac, "obtenu": "absent"})
        else:
            c = cs[0]
            for k, champ in (("type", "type"), ("regime", "regime")):
                if k in ac and c[champ] != ac[k]:
                    ecarts.append({"champ": f"carrefour.{k}", "attendu": ac[k], "obtenu": c[champ]})
            if "branches" in ac and len(c["branches"]) != ac["branches"]:
                ecarts.append({"champ": "carrefour.branches", "attendu": ac["branches"], "obtenu": len(c["branches"])})
            if "a_verifier" in ac:
                av = c["id"] in r1["a_verifier"]
                if av != ac["a_verifier"]:
                    ecarts.append({"champ": "carrefour.a_verifier", "attendu": ac["a_verifier"], "obtenu": av})
            if "passages" in ac and len(c.get("passages_pieton", [])) != ac["passages"]:
                ecarts.append({"champ": "carrefour.passages", "attendu": ac["passages"], "obtenu": len(c.get("passages_pieton", []))})
    if "giratoire" in a:
        g = [c for c in m1.get("carrefours", []) if c["type"] == "giratoire"]
        if len(g) != 1:
            ecarts.append({"champ": "giratoire", "attendu": 1, "obtenu": len(g)})
        else:
            for k in ("type", "regime"):
                if g[0][k] != a["giratoire"][k]:
                    ecarts.append({"champ": f"giratoire.{k}", "attendu": a["giratoire"][k], "obtenu": g[0][k]})
            if len(g[0]["branches"]) != a["giratoire"]["branches"]:
                ecarts.append({"champ": "giratoire.branches", "attendu": a["giratoire"]["branches"], "obtenu": len(g[0]["branches"])})
    for ab in a.get("branches", []):
        bs = _branches(m1, ab["way"], ab.get("extremite"))
        if not bs:
            ecarts.append({"champ": f"branche way {ab['way']}", "attendu": ab, "obtenu": "absente"})
            continue
        c, b = bs[0]
        if "regime" in ab and b["regime"] != ab["regime"]:
            ecarts.append({"champ": f"way {ab['way']}.regime", "attendu": ab["regime"], "obtenu": b["regime"]})
        for k in ("ligne_arret", "ligne_axiale_approche"):
            if k in ab:
                if ab[k] is None and k in b:
                    ecarts.append({"champ": f"way {ab['way']}.{k}", "attendu": None, "obtenu": b[k]})
                elif ab[k] is not None:
                    for kk, vv in ab[k].items():
                        if b.get(k, {}).get(kk) != vv:
                            ecarts.append({"champ": f"way {ab['way']}.{k}.{kk}", "attendu": vv, "obtenu": b.get(k, {}).get(kk)})
        if "signaux_codes" in ab:
            codes = sorted(sigs[s]["code"] for s in b.get("signaux", []))
            if codes != sorted(ab["signaux_codes"]):
                ecarts.append({"champ": f"way {ab['way']}.signaux", "attendu": ab["signaux_codes"], "obtenu": codes})
        if "fleches_types" in ab:
            ft = [f["types"] for f in b.get("fleches", [])]
            if ft != ab["fleches_types"]:
                ecarts.append({"champ": f"way {ab['way']}.fleches", "attendu": ab["fleches_types"], "obtenu": ft})
    if "toutes_branches" in a:
        t = a["toutes_branches"]
        for c in m1.get("carrefours", []):
            for b in c["branches"]:
                if b["regime"] == "sortie_seule":
                    continue
                if b["regime"] != t["regime"]:
                    ecarts.append({"champ": f"{c['id']}/{b['id']}.regime", "attendu": t["regime"], "obtenu": b["regime"]})
                if "ligne_arret" in t and t["ligne_arret"] is None and "ligne_arret" in b:
                    ecarts.append({"champ": f"{c['id']}/{b['id']}.ligne_arret", "attendu": None, "obtenu": b["ligne_arret"]})
                if "ligne_arret_type" in t and b.get("ligne_arret", {}).get("type") != t["ligne_arret_type"]:
                    ecarts.append({"champ": f"{c['id']}/{b['id']}.ligne_arret", "attendu": t["ligne_arret_type"], "obtenu": b.get("ligne_arret")})
    if "aucun_signal_code" in a and any(s["code"] == a["aucun_signal_code"] for s in m1.get("signaux", [])):
        ecarts.append({"champ": "signaux", "attendu": f"aucun {a['aucun_signal_code']}", "obtenu": [s["code"] for s in m1["signaux"]]})
    if "marquage_passage" in a:
        mq = [x for x in m1.get("marquages", []) if x["type"] == "passage_pieton"]
        if len(mq) != 1 or abs(mq[0]["ancrage"]["s"] - a["marquage_passage"]["s"]) > 1e-6:
            ecarts.append({"champ": "marquage_passage", "attendu": a["marquage_passage"], "obtenu": [x["ancrage"] for x in mq]})
    if "objet" in a:
        ob = [o for o in m1.get("objets", []) if o["type"] == a["objet"]["type"]]
        if len(ob) != 1:
            ecarts.append({"champ": "objet", "attendu": a["objet"], "obtenu": len(ob)})
        else:
            for k in ("longueur_m", "hauteur_m"):
                if ob[0]["dimensions"].get(k) != a["objet"][k]:
                    ecarts.append({"champ": f"objet.{k}", "attendu": a["objet"][k], "obtenu": ob[0]["dimensions"].get(k)})
            if abs(ob[0]["rattachement"]["s"] - a["objet"]["s"]) > 1e-6:
                ecarts.append({"champ": "objet.s", "attendu": a["objet"]["s"], "obtenu": ob[0]["rattachement"]["s"]})
    if "ouvrage" in a:
        ov = m1.get("ouvrages", [])
        rid = {r["id"] for r in m1["routes"] if a["ouvrage"]["way"] in r["osm"]["ways"]}
        ok = [o for o in ov if o["type"] == a["ouvrage"]["type"] and o.get("layer") == a["ouvrage"]["layer"]
              and o["routes_portees"][0]["route"] in rid]
        if len(ok) != 1:
            ecarts.append({"champ": "ouvrage", "attendu": a["ouvrage"], "obtenu": ov})
    return ecarts, {"sha256": hashlib.sha256(o1).hexdigest(), "carrefours": [(c["id"], c["regime"]) for c in m1.get("carrefours", [])]}


def tests_validateur():
    out = []
    ex = GEN / "schema" / "exemples"
    for nom in ("exemple_rue_carrefour.json", "exemple_rue_residentielle.json"):
        inst = json.loads((ex / nom).read_text(encoding="utf-8"))
        err, _, _ = VM.valider(inst)
        out.append({"id": f"V-{nom}", "titre": f"exemple migré {nom} : 0 erreur", "ok": not err,
                    "detail": [list(e) for e in err][:5]})
    inst = json.loads((ex / "exemple_rue_residentielle.json").read_text(encoding="utf-8"))
    inst["profils"][0]["bandes"][0]["prov"]["largeur"]["regle"] = "RF-OSM-LAR-999"
    err, _, _ = VM.valider(inst)
    c11 = [e for e in err if e[0] == "C11" and "RF-OSM-LAR-999" in e[2]]
    out.append({"id": "V-C11", "titre": "C11 rejette l'identifiant inconnu RF-OSM-LAR-999", "ok": bool(c11), "detail": [list(e) for e in c11]})
    inst = json.loads((ex / "exemple_rue_residentielle.json").read_text(encoding="utf-8"))
    inst["profils"][0]["bandes"][0]["prov"]["largeur"]["src"] = "defaut:OSM-LAR-020"
    err, _, _ = VM.valider(inst)
    c11b = [e for e in err if e[0] == "C11" and "OSM-LAR-020" in e[2]]
    out.append({"id": "V-C11-ancien", "titre": "C11 refuse un ancien identifiant et donne sa cible (OSM-LAR-020 → RF-OSM-LAR-020)",
                "ok": bool(c11b) and "RF-OSM-LAR-020" in c11b[0][2], "detail": [list(e) for e in c11b]})
    # C13 : AB4 sur une branche stop_a_verifier
    d = reseau(json.loads((ICI / "cas_carrefours.json").read_text(encoding="utf-8"))["cas"][2])
    m, _ = I.construire(d, True, None, "V-C13")
    br = next(b for c in m["carrefours"] for b in c["branches"] if b["regime"] == "stop_a_verifier")
    c = next(c for c in m["carrefours"] if br in c["branches"])
    m.setdefault("signaux", []).append({"id": "SG-TEST", "famille": "panneau", "code": "AB4", "position": {"route": br["route"], "s": 1.0},
                                        "applicabilite": {"carrefour": c["id"], "branche": br["id"]},
                                        "prov": {"*": {"src": "manuel", "conf": "faible"}}})
    br.setdefault("signaux", []).append("SG-TEST")
    err, _, _ = VM.valider(m)
    c13 = [e for e in err if e[0] == "C13"]
    out.append({"id": "V-C13", "titre": "C13 rejette un AB4 sur une branche stop_a_verifier (ARB-19)", "ok": len(c13) >= 1,
                "detail": [list(e) for e in c13]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=str(GEN / "tmp" / "tests" / "tests_inference_L0.json"),
                    help="sortie JSON (défaut dans tmp/ ; validation/ seulement par faire_rapport_L0.py)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    res = {"tags": [], "reseaux": [], "validateur": []}
    for cas in json.loads((ICI / "cas_tags.json").read_text(encoding="utf-8"))["cas"]:
        try:
            ec, rs = comparer_profil(cas)
        except Exception as e:  # noqa: BLE001 - un cas qui plante est un échec rapporté
            ec, rs = [{"champ": "exception", "obtenu": f"{type(e).__name__}: {e}"}], None
        res["tags"].append({"id": cas["id"], "titre": cas["titre"], "regles": cas["regles"], "ok": not ec, "ecarts": ec})
    for cas in json.loads((ICI / "cas_carrefours.json").read_text(encoding="utf-8"))["cas"]:
        try:
            ec, info = comparer_reseau(cas)
        except Exception as e:  # noqa: BLE001
            ec, info = [{"champ": "exception", "obtenu": f"{type(e).__name__}: {e}"}], {}
        res["reseaux"].append({"id": cas["id"], "titre": cas["titre"], "regles": cas["regles"], "ok": not ec, "ecarts": ec, **info})
    res["validateur"] = tests_validateur()
    tous = res["tags"] + res["reseaux"] + res["validateur"]
    res["bilan"] = {"cas": len(tous), "reussis": sum(1 for x in tous if x["ok"]),
                    "cas_tags": len(res["tags"]), "cas_reseaux": len(res["reseaux"]), "cas_validateur": len(res["validateur"])}
    for x in tous:
        print(f"{'OK ' if x['ok'] else 'ÉCHEC'}\t{x['id']}\t{x['titre']}")
        if not x["ok"]:
            for e in x.get("ecarts", x.get("detail", [])):
                print(f"\t\t{json.dumps(e, ensure_ascii=False)[:400]}")
    print(f"{res['bilan']['reussis']} / {res['bilan']['cas']} cas réussis")
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_bytes((json.dumps(res, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return 0 if res["bilan"]["reussis"] == res["bilan"]["cas"] else 1


if __name__ == "__main__":
    sys.exit(main())
