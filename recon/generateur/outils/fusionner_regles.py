# -*- coding: utf-8 -*-
"""Fusionne les règles machine des volets 08 à 14 de D:\\DocRoute en une base unique pour le générateur.

Entrée  : les JSON des volets (lecture seule) et les tables de tables_fusion.py.
Sortie  : D:\\ClaudeCode_RoadCreation\\assets\\specs\\route\\regles_route_fr.json

Usage   : python -I recon/generateur/outils/fusionner_regles.py [--sortie CHEMIN]

Principes :
- chaque règle garde un identifiant stable dérivé de son identifiant d'origine (préfixe par volet) ;
- les doublons (même fait, même texte source) sont fusionnés dans une règle canonique qui garde la liste
  des alias et les sources secondaires ; tout ancien identifiant se résout par `index_alias` ;
- les recoupements (même sujet, sources ou contenus différents) restent séparés et sont liés par `voir_aussi` ;
- les valeurs contradictoires entre volets sont tranchées dans `arbitrages`, et `parametres_par_defaut`
  donne la valeur que le générateur doit prendre quand rien n'est relevé.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import tables_fusion as T  # noqa: E402

DEPOT = ICI.parents[2]
SORTIE_DEFAUT = DEPOT / "assets" / "specs" / "route" / "regles_route_fr.json"
RACINE = Path(T.DOCROUTE)

CONFIANCE = {"haute": "haute", "moyenne": "moyenne", "faible": "faible", "basse": "faible",
             "forte": "haute", "estimation": "faible",
             "haute (texte) / faible (formes non cotées)": "moyenne"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def nouvel_id(volet, ident):
    v = next(x for x in T.VOLETS if x["code"] == volet)
    return v["prefixe"] + ident


def prefixe_id(ident):
    """Préfixe d'un identifiant d'origine : 'INS-TXT-01' -> 'INS-TXT', 'MA-PIS-001' -> 'PIS', 'GEN.HAUTEUR' -> 'GEN'."""
    if ident.startswith("INS-TXT"):
        return "INS-TXT"
    if ident.startswith("MA-"):
        return ident.split("-")[1]
    if "." in ident and "-" not in ident.split(".")[0]:
        return ident.split(".")[0]
    return ident.split("-")[0] if "-" in ident else ident


# ------------------------------------------------------------------ sources
def canon_cle(volet, cle):
    cle = (cle or "").strip()
    if (volet, cle) in T.CLE_PAR_VOLET:
        return T.CLE_PAR_VOLET[(volet, cle)]
    if cle.startswith("W_"):
        return "OSM_WIKI"
    return T.CLE_COMMUNE.get(cle, cle)


def jeton_12(jeton):
    """'RC GA-CHA-005' -> ('DEPOT_RC', 'GA-CHA-005') ; 'W_LANES' -> ('OSM_WIKI', 'W_LANES')."""
    jeton = jeton.strip()
    mot = jeton.split(" ")[0]
    if mot.startswith("W_"):
        return "OSM_WIKI", jeton
    if mot == "INDEX_DOCUMENTATION.md":
        return "INDEX_DOCROUTE", jeton
    if mot in T.JETONS_12:
        cle = T.JETONS_12[mot]
        reste = jeton[len(mot):].strip()
        return cle, (reste or None)
    return mot, None


def source_canonique(volet, regle):
    s = regle.get("source") or {}
    sec = []
    if volet == "13":
        src = {"doc": "OBS_ISERE2026", "page": None, "article": None,
               "sites": regle.get("exemples_sites"), "doc_volet": s.get("doc")}
        if regle.get("norme"):
            n = regle["norme"]
            m = re.match(r"^IISR (\d)", n.get("doc") or "")
            sec.append({"doc": f"IISR{m.group(1)}" if m else n.get("doc"),
                        "page": n.get("page"), "article": n.get("article"), "role": "norme comparée"})
        return src, sec
    if volet == "14":
        cle = T.SOURCES_14.get(s.get("doc"), s.get("doc"))
        src = {"doc": cle, "page": s.get("page"), "article": s.get("article") or s.get("figure")}
        if cle != s.get("doc"):
            src["doc_volet"] = s.get("doc")
        return src, sec
    if volet == "12":
        jetons = [j for j in (s.get("doc") or "").split(" ; ") if j.strip()]
        cle, precision = jeton_12(jetons[0]) if jetons else (None, None)
        src = {"doc": cle, "page": s.get("page"), "article": s.get("article")}
        if precision:
            src["precision"] = precision
        if s.get("doc") and s.get("doc") != cle:
            src["doc_volet"] = s.get("doc")
        for j in jetons[1:]:
            c, p = jeton_12(j)
            e = {"doc": c}
            if p:
                e["precision"] = p
            sec.append(e)
        return src, sec
    cle = canon_cle(volet[:2], s.get("doc"))
    src = {"doc": cle, "page": s.get("page"), "article": s.get("article")}
    for k in ("figure", "note"):
        if s.get(k):
            src[k] = s[k]
    if cle != s.get("doc"):
        src["doc_volet"] = s.get("doc")
    for e in regle.get("sources_secondaires") or []:
        c = canon_cle(volet[:2], e.get("doc"))
        x = {"doc": c, "page": e.get("page"), "article": e.get("article")}
        if c == "DEPOT_RC" and e.get("article"):
            x["precision"] = e.get("article")
        sec.append(x)
    return src, sec


def dossier_docroute(nn):
    for d in RACINE.iterdir():
        if d.is_dir() and d.name.startswith(nn + "_"):
            return d.name
    return nn


def normaliser_chemin(volet, f):
    """Ramène les chemins des catalogues des volets à des chemins absolus (premier fichier seulement)."""
    if not f:
        return None
    f = f.replace("\\", "/").split(" ; ")[0].strip()
    m = re.match(r"^DocRoute/(\d\d)/(.*)$", f)
    if m:
        f = f"{T.DOCROUTE}/{dossier_docroute(m.group(1))}/{m.group(2)}"
    if f.startswith("ClaudeCode_RoadCreation/") or f.startswith("DocRoute/"):
        f = "D:/" + f
    if f.startswith("sources/"):
        dossier = {"10": "10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts", "12": "12_Modele_Voie_OSM_Generateurs"}.get(volet)
        if dossier:
            f = f"{T.DOCROUTE}/{dossier}/{f}"
    m = re.match(r"^(.*?\.pdf)", f)
    if m:
        f = m.group(1)
    return f


def catalogue_sources(donnees):
    cat = OrderedDict()

    def ajouter(cle, titre=None, fichier=None, url=None, volet=None, extra=None, surcharge=False):
        e = cat.setdefault(cle, {"titre": None, "fichier": None, "url": None, "cles_volets": [], "_fichiers": []})
        if titre and (surcharge or not e["titre"]):
            e["titre"] = titre
        if fichier:
            if surcharge:
                e["_fichiers"].insert(0, fichier)
            else:
                e["_fichiers"].append(fichier)
        if url and (surcharge or not e["url"]):
            e["url"] = url
        if volet:
            e["cles_volets"].append(volet)
        for k, v in (extra or {}).items():
            e.setdefault(k, v)

    d = donnees["08"]
    for k, v in d["sources"].items():
        ajouter(canon_cle("08", k), v.get("titre"), normaliser_chemin("08", v.get("fichier")),
                v.get("url"), f"08:{k}", {"sha256": v.get("sha256")} if v.get("sha256") else None)
    for code in ("09S", "09F"):
        for k, v in donnees[code]["meta"]["documents"].items():
            titre, _, fich = v.partition(" — ")
            ajouter(canon_cle("09", k), titre.strip(), normaliser_chemin("09", fich.strip()), None, f"{code}:{k}")
    for k, v in donnees["10"]["documents"].items():
        ajouter(canon_cle("10", k), v.get("titre"), normaliser_chemin("10", v.get("fichier")), v.get("url"), f"10:{k}",
                {"decalage_pages": v.get("decalage")} if v.get("decalage") else None)
    for k, v in donnees["11"]["sources"].items():
        ajouter(canon_cle("11", k), v.get("titre"), normaliser_chemin("11", v.get("fichier")),
                v.get("url"), f"11:{k}", {"licence": v.get("licence")} if v.get("licence") else None)
    for k, v in donnees["12"]["sources"].items():
        cle = canon_cle("12", k) if k not in T.JETONS_12 else T.JETONS_12[k]
        ajouter(cle, v.get("doc") or v.get("titre"), normaliser_chemin("12", v.get("fichier")), v.get("url"), f"12:{k}")
    for k, v in T.SOURCES_COMPLEMENTAIRES.items():
        ajouter(k, v.get("titre"), v.get("fichier"), v.get("url"), surcharge=True)
    ajouter("INDEX_DOCROUTE", "D:/DocRoute/INDEX_DOCUMENTATION.md (index du dossier)", T.DOCROUTE + "/INDEX_DOCUMENTATION.md")
    for k, v in T.NOTES_SOURCES.items():
        if k in cat:
            cat[k].update(v)
    for e in cat.values():
        fichiers = e.pop("_fichiers")
        existants = sorted((f for f in fichiers if Path(f.rstrip("/")).exists()),
                           key=lambda f: 0 if Path(f).is_file() else 1)
        e["fichier"] = (existants or fichiers or [None])[0]
        e["fichier_existe"] = bool(existants)
    return cat


# ------------------------------------------------------------------ règles
def famille(volet, ident):
    if (volet, ident) in T.FAMILLE_SPECIFIQUE:
        return T.FAMILLE_SPECIFIQUE[(volet, ident)]
    p = prefixe_id(ident)
    if volet in ("08",):
        return T.FAMILLE_08.get(p, "generalites")
    if volet == "08P":
        return "pratiques_locales"
    if volet == "09S":
        return "signalisation_verticale"
    if volet == "09F":
        return "feux"
    if volet == "10":
        return T.FAMILLE_10[p]
    if volet == "11":
        return T.FAMILLE_11[p]
    if volet == "12":
        return "inference_osm"
    if volet == "13":
        return "pratiques_locales"
    if volet == "14":
        return "assets"
    raise KeyError(volet)


def nature(volet, regle, src_cle):
    if volet == "08":
        if regle.get("normatif"):
            return "reglementaire"
        return "pratique_locale" if src_cle in ("PARIS_SH2015", "NANTES2022", "LYON_CF2023") else "choix_generateur"
    if volet == "08P":
        return "pratique_locale"
    if volet in ("09S", "09F"):
        t = regle.get("type")
        return {"obligation": "reglementaire", "interdiction": "reglementaire", "definition": "reglementaire",
                "faculte": "reglementaire", "valeur_derivee": "choix_generateur",
                "recommandation": "recommandation", "observation_figure": "observation"}.get(t, "reglementaire")
    if volet == "10":
        if src_cle in ("IISR7", "IISR3"):
            return "reglementaire"
        if src_cle == "EPURE_DOSSIER10":
            return "choix_generateur"
        if src_cle in ("LYON_CF2023", "ISERE_ARSENAL") or src_cle.startswith("GAM"):
            return "pratique_locale"
        return "recommandation"
    if volet == "11":
        return {"obligation": "reglementaire", "recommandation": "recommandation", "pratique_locale": "pratique_locale",
                "observation": "observation", "hypothese": "choix_generateur", "calcul": "calcul"}[regle["nature"]]
    if volet == "12":
        return "inference"
    if volet == "13":
        return "observation"
    if volet == "14":
        if src_cle.startswith("IISR") or src_cle == "ARR2007":
            return "reglementaire"
        if src_cle in ("CEREMA_BEV03", "SETRA_GC1997", "CEREMA_GC_CYCLES"):
            return "recommandation"
        if src_cle == "RENDUS_DOSSIER14":
            return "choix_generateur"
        return "donnee_fabricant"
    raise KeyError(volet)


def doc_md(volet, ident):
    v = next(x for x in T.VOLETS if x["code"] == volet)
    if volet == "10":
        nom = T.DOC_MD_10[prefixe_id(ident)]
    elif volet == "11":
        nom = T.DOC_MD_11[prefixe_id(ident)]
    else:
        nom = v["doc_md"]
    return f"{v['dossier']}/{nom}"


CHAMPS_DETAILS = ("normatif", "type", "nature", "sortie", "osm", "surcharges_locales", "usage_generateur", "statut",
                  "n_exemples", "exemples_sites", "statistiques_mesures", "n_contre_exemples",
                  "contre_exemples_sites", "norme", "ecart_norme", "correction", "confiance_usage", "confiance_plafond")


def convertir(volet, regle):
    src, sec = source_canonique(volet, regle)
    conf_orig = regle.get("confiance")
    r = OrderedDict()
    r["id"] = nouvel_id(volet, regle["id"])
    r["famille"] = famille(volet, regle["id"])
    r["sujet"] = regle.get("sujet")
    r["condition"] = regle.get("condition")
    r["valeurs"] = regle.get("valeurs")
    r["unite"] = regle.get("unite")
    r["tolerance"] = regle.get("tolerance")
    r["source"] = src
    if sec:
        r["sources_secondaires"] = sec
    r["nature"] = nature(volet, regle, src.get("doc") or "")
    r["confiance"] = CONFIANCE.get(conf_orig, conf_orig)
    if conf_orig not in ("haute", "moyenne", "faible"):
        r["confiance_origine"] = conf_orig
    if regle.get("note"):
        r["note"] = regle["note"]
    details = {k: regle[k] for k in CHAMPS_DETAILS if k in regle and k != "nature"}
    if details:
        r["details"] = details
    r["origine"] = {"volet": volet[:2], "fichier": f"{next(x for x in T.VOLETS if x['code'] == volet)['dossier']}/"
                    f"{next(x for x in T.VOLETS if x['code'] == volet)['fichier']}", "id": regle["id"]}
    r["renvoi"] = doc_md(volet, regle["id"])
    return r


# ------------------------------------------------------------------ programme
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    a = ap.parse_args()

    donnees, empreintes, brutes = {}, {}, OrderedDict()
    for v in T.VOLETS:
        p = RACINE / v["dossier"] / v["fichier"]
        if v["code"] not in donnees:
            pass
        d = json.loads(p.read_text(encoding="utf-8"))
        donnees[v["code"]] = d
        empreintes[f"{v['dossier']}/{v['fichier']}"] = {"sha256": sha256(p), "octets": p.stat().st_size}
        for r in d[v["cle"]]:
            brutes[(v["code"], r["id"])] = r

    regles = OrderedDict()
    for (volet, ident), r in brutes.items():
        nr = convertir(volet, r)
        if nr["id"] in regles:
            raise SystemExit(f"identifiant en double après préfixage : {nr['id']}")
        regles[nr["id"]] = nr

    # index des anciens identifiants
    index_alias = OrderedDict()
    for (volet, ident) in brutes:
        index_alias[f"{volet[:2]}:{ident}"] = nouvel_id(volet, ident)

    # doublons
    nb_alias = 0
    for (cv, ci), alias in T.DOUBLONS.items():
        can = regles[nouvel_id(cv, ci)]
        can.setdefault("alias", [])
        for (av, ai) in alias:
            aid = nouvel_id(av, ai)
            ar = regles.pop(aid)
            can["alias"].append({"id_fusionne": aid, "volet": av[:2], "id_origine": ai,
                                 "fichier": ar["origine"]["fichier"], "source": ar["source"]})
            # sources secondaires : la source de l'alias si elle diffère
            sa = ar["source"]
            if sa.get("doc") != can["source"].get("doc"):
                can.setdefault("sources_secondaires", []).append(
                    {"doc": sa.get("doc"), "page": sa.get("page"), "article": sa.get("article"), "via": aid})
            for e in ar.get("sources_secondaires", []):
                if e not in can.get("sources_secondaires", []):
                    can.setdefault("sources_secondaires", []).append(e)
            index_alias[f"{av[:2]}:{ai}"] = can["id"]
            index_alias[aid] = can["id"]
            nb_alias += 1

    def resoudre(volet, ident):
        nid = nouvel_id(volet, ident)
        nid = index_alias.get(nid, nid)
        if nid not in regles:
            raise SystemExit(f"référence inconnue : {volet}:{ident}")
        return nid

    # recoupements
    for groupe in T.RECOUPEMENTS:
        ids = []
        for (v, i) in groupe:
            nid = resoudre(v, i)
            if nid not in ids:
                ids.append(nid)
        for nid in ids:
            va = regles[nid].setdefault("voir_aussi", [])
            for autre in ids:
                if autre != nid and autre not in va:
                    va.append(autre)

    # arbitrages
    for arb in T.ARBITRAGES:
        res = []
        for rid in arb["regles"]:
            rid2 = index_alias.get(rid, rid)
            if rid2 not in regles:
                raise SystemExit(f"{arb['id']} : règle inconnue {rid}")
            res.append(rid2)
            regles[rid2].setdefault("arbitrages", [])
            if arb["id"] not in regles[rid2]["arbitrages"]:
                regles[rid2]["arbitrages"].append(arb["id"])
        arb["regles"] = res

    # paramètres par défaut
    parametres = []
    for (pid, nom, valeur, unite, plage, refs, arb) in T.PARAMETRES:
        refs2 = []
        for rid in refs:
            rid2 = index_alias.get(rid, rid)
            if rid2 not in regles:
                raise SystemExit(f"{pid} : règle inconnue {rid}")
            refs2.append(rid2)
        if arb and arb not in {x["id"] for x in T.ARBITRAGES}:
            raise SystemExit(f"{pid} : arbitrage inconnu {arb}")
        parametres.append(OrderedDict([("id", pid), ("parametre", nom), ("valeur", valeur), ("unite", unite),
                                       ("plage_ou_variantes", plage), ("regles", refs2), ("arbitrage", arb)]))

    # ordre de sortie : par famille puis par id d'origine (stable)
    ordre_fam = list(T.FAMILLES)
    liste = sorted(regles.values(), key=lambda r: (ordre_fam.index(r["famille"]), r["origine"]["volet"], r["id"]))

    cat = catalogue_sources(donnees)
    utilisees = Counter()
    for r in liste:
        utilisees[r["source"].get("doc")] += 1
        for e in r.get("sources_secondaires", []):
            utilisees[e.get("doc")] += 1
        for al in r.get("alias", []):
            utilisees[al["source"].get("doc")] += 1
    sources = OrderedDict()
    for cle in sorted(utilisees, key=lambda c: str(c)):
        e = cat.get(cle)
        if e is None:
            e = {"titre": None, "fichier": None, "url": None, "cles_volets": [], "a_completer": True}
        e = dict(e)
        e["utilisee_par_n"] = utilisees[cle]
        sources[cle] = e

    sortie = OrderedDict()
    sortie["schema"] = "regles_route_fr/1.0"
    sortie["date"] = "2026-10-17"
    sortie["revision"] = ("17/10/2026 : corrections de la relecture adverse (dossier 15 de DocRoute) appliquées aux JSON des volets et aux tables ; ARB-19 et ARB-20 ajoutés ; détail dans D:/DocRoute/00_ERRATA_DOCUMENTS_EXISTANTS.md § 10")
    sortie["role"] = ("Base unique des règles de conception routière française pour le générateur procédural "
                      "(Houdini 22 → USD / OpenDRIVE / graphe de voies). Fusion dédoublonnée des règles machine des "
                      "volets 08 à 14 de D:/DocRoute, avec identifiants stables, sources canoniques, arbitrages entre "
                      "volets et paramètres par défaut.")
    sortie["lecture"] = ("Voir assets/specs/route/README.md et D:/DocRoute/00_SYNTHESE_CONCEPTION_ROUTES_FR.md. "
                         "Une règle = {id, famille, sujet, condition, valeurs, unite, tolerance, source{doc, page, "
                         "article}, nature, confiance} + sources_secondaires, alias, voir_aussi, arbitrages, details, "
                         "origine, renvoi. Pages = pages du fichier PDF sauf mention de décalage dans `sources`.")
    sortie["priorite_d_application"] = [
        "1. mesure ou relevé du site (PCRS, levé GAM, LiDAR, ortho 5 cm, photo recalée)",
        "2. règle de nature « reglementaire » (IISR, arrêtés, code) : ne jamais l'enfreindre",
        "3. pratique locale du territoire de la scène (Grenoble-Alpes Métropole, observations de l'Isère)",
        "4. recommandation nationale (Cerema, Certu, Setra)",
        "5. paramètre par défaut du générateur (`parametres_par_defaut`, arbitrages)",
    ]
    sortie["natures"] = {
        "reglementaire": "texte réglementaire (IISR, arrêtés, code de la route, code de la voirie routière)",
        "recommandation": "guide national (Cerema, Certu, Setra)",
        "pratique_locale": "guide ou usage d'une collectivité (Grenoble-Alpes Métropole, Lyon, Paris, Nantes, Isère)",
        "observation": "constat sur photos Panoramax / ortho IGN ou relevé du site (estimation)",
        "inference": "règle de lecture des tags OSM vers le modèle de voie",
        "donnee_fabricant": "cote lue sur un catalogue de fabricant",
        "calcul": "valeur calculée à partir d'une règle",
        "choix_generateur": "valeur retenue quand les textes ne chiffrent pas (à surcharger par la scène)",
    }
    sortie["familles"] = OrderedDict((f, {"titre": t, "nb_regles": sum(1 for r in liste if r["famille"] == f)})
                                     for f, t in T.FAMILLES.items())
    sortie["volets"] = empreintes
    sortie["statistiques"] = {
        "regles_lues": len(brutes),
        "doublons_fusionnes": nb_alias,
        "regles": len(liste),
        "par_volet": dict(Counter(r["origine"]["volet"] for r in liste)),
        "par_nature": dict(Counter(r["nature"] for r in liste)),
        "par_confiance": dict(Counter(r["confiance"] for r in liste)),
        "recoupements": len(T.RECOUPEMENTS),
        "arbitrages": len(T.ARBITRAGES),
        "parametres_par_defaut": len(parametres),
        "sources": len(sources),
    }
    sortie["arbitrages"] = T.ARBITRAGES
    sortie["parametres_par_defaut"] = parametres
    sortie["regles"] = liste
    sortie["index_alias"] = index_alias
    sortie["sources"] = sources

    Path(a.sortie).parent.mkdir(parents=True, exist_ok=True)
    Path(a.sortie).write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(sortie["statistiques"], ensure_ascii=False, indent=1))
    manquantes = [k for k, v in sources.items() if v.get("a_completer") or not v.get("titre")]
    print("sources sans titre :", manquantes)


if __name__ == "__main__":
    main()
