# -*- coding: utf-8 -*-
"""Valide assets/specs/regles_conception.json (Python 3.11, bibliothèque standard seulement).

Contrôles :
  - schéma du document et de chaque règle (champs, types, énumérations) ;
  - identifiants uniques, au bon format, alias sans collision, table des fusions cohérente ;
  - unités : tout nombre de « parametres » a une unité dans le suffixe de sa clé ou d'une clé englobante ;
  - sources : chaque règle cite une source du catalogue ; fichiers locaux présents et tailles exactes ; une URL file:///
    du dépôt existe et désigne le même fichier que « fichier_local » ;
  - références : « regle:<fichier>.<chemin> » résolues dans assets/specs, identifiants de règles cités existants ;
  - conflits, familles (comptes et sous-familles), applicabilité, historique et section de fusion cohérents ;
  - résumé : REGLES_CONCEPTION.md, s'il est à côté du JSON, porte la même version, le même nombre de règles et tous
    les identifiants.

Usage : python valider_regles.py [chemin_json] [--strict]
Code de sortie : 0 si aucune erreur (avec --strict : ni erreur ni avertissement), 1 sinon.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import unquote

RACINE = Path(__file__).resolve().parents[3]
DEFAUT = RACINE / "assets" / "specs" / "regles_conception.json"
SPECS = RACINE / "assets" / "specs"

ACTIONS = {"generer", "contraindre", "verifier", "deduire_si_absent"}
CONFIANCES = {"haute", "moyenne", "faible"}
STATUTS = {"immediate", "partielle", "donnees_nouvelles"}
CHAMPS_REGLE = {"id": str, "famille": str, "sous_famille": str, "enonce": str, "parametres": dict, "condition": str,
                "action": str, "source": dict, "confiance": str, "applicabilite": dict}
CHAMPS_OPTION = {"actions_secondaires": list, "sources_secondaires": list, "alias": list, "conflits": list, "notes": str}
CLES_TETE = ["version", "date", "perimetre", "conventions", "familles", "regles", "sources", "fusion_detection_inference"]
CLES_FUSION = ["principe", "hierarchie_valeurs", "hierarchie_normative", "regle_arbitrage", "score", "ordre_application"]
SUFFIXES_DEFAUT = {"m", "mm", "cm", "m2", "m3", "km", "pct", "deg", "kmh", "s", "dn", "px", "kn", "ptv", "ratio", "n", "ncc",
                   "score", "id", "u"}
# famille : 2 à 4 caractères, une lettre puis des lettres ou des chiffres (MQ-FLE-003, MQ-Z30-001)
RE_ID = re.compile(r"^(MQ|INF|GA|FUS|DET|VAL|TQ)-[A-Z][A-Z0-9]{1,3}-\d{3}$")
RE_CITE = re.compile(r"\b(?:MQ|INF|GA|FUS|DET|VAL|TQ)-[A-Z][A-Z0-9]{1,3}-\d{3}\b")
NOM_RESUME = "REGLES_CONCEPTION.md"
RE_REGLE = re.compile(r"regle:([a-z_]+)\.([A-Za-z0-9_.\-]+)")
RE_CF = re.compile(r"^CF-\d{2}$")
SCHEMAS_URL = ("http://", "https://", "file:///", "interne:")


class Rapport:
    def __init__(self):
        self.erreurs, self.avertissements = [], []

    def err(self, ou, msg):
        self.erreurs.append(f"[ERREUR] {ou} : {msg}")

    def avert(self, ou, msg):
        self.avertissements.append(f"[AVERT.] {ou} : {msg}")


def unite_ok(cle, suffixes):
    if cle.startswith(("n_", "nb_")):
        return True
    return "_" in cle and cle.rsplit("_", 1)[1] in suffixes


def parcourir_nombres(obj, chemin, avec_unite, suffixes, sortie):
    """Ajoute à sortie les chemins des nombres sans unité dans leur chemin de clés."""
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return
    if isinstance(obj, (int, float)):
        if not avec_unite:
            sortie.append(chemin)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            parcourir_nombres(v, f"{chemin}.{k}", avec_unite or unite_ok(str(k), suffixes), suffixes, sortie)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            parcourir_nombres(v, f"{chemin}[{i}]", avec_unite, suffixes, sortie)


def chaines(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from chaines(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from chaines(v)


def meme_fichier(a, b):
    return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))


def dans_depot(p):
    try:
        Path(p).resolve().relative_to(RACINE)
        return True
    except ValueError:
        return False


_cache_specs = {}


def resoudre_regle(fichier, chemin):
    """Résout « regle:fichier.chemin » dans assets/specs/fichier.json ; renvoie un message d'erreur ou None."""
    if fichier not in _cache_specs:
        p = SPECS / f"{fichier}.json"
        try:
            _cache_specs[fichier] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        except json.JSONDecodeError as e:
            _cache_specs[fichier] = None
            return f"{p.name} illisible ({e})"
    noeud = _cache_specs[fichier]
    if noeud is None:
        return f"spec assets/specs/{fichier}.json introuvable"
    for part in chemin.rstrip(".").split("."):
        if isinstance(noeud, dict) and part in noeud:
            noeud = noeud[part]
        else:
            return f"clé « {part} » absente dans {fichier}.{chemin}"
    return None


def valider(doc, rap):
    # ------------------------------------------------------------- en-tête
    for k in CLES_TETE:
        if k not in doc:
            rap.err("document", f"clé de tête manquante : {k}")
    if not isinstance(doc.get("version"), str) or not doc.get("version"):
        rap.err("document", "version absente ou non textuelle")
    try:
        date.fromisoformat(str(doc.get("date")))
    except ValueError:
        rap.err("document", f"date non ISO : {doc.get('date')!r}")
    conv = doc.get("conventions", {})
    suffixes = set(conv.get("unites", {}).get("suffixes", {}) or SUFFIXES_DEFAUT)
    if not conv.get("unites", {}).get("suffixes"):
        rap.avert("conventions", "suffixes d'unité absents : liste par défaut utilisée")
    for k in ("reperes", "identifiants", "actions", "confiance"):
        if k not in conv:
            rap.err("conventions", f"rubrique manquante : {k}")

    # ------------------------------------------------------------- sources
    sources = {}
    for i, s in enumerate(doc.get("sources", [])):
        ou = f"sources[{i}]"
        sid = s.get("id")
        if not sid:
            rap.err(ou, "id manquant")
            continue
        if sid in sources:
            rap.err(ou, f"id de source en double : {sid}")
        sources[sid] = s
        for k in ("titre", "type", "url", "date"):
            if not s.get(k):
                rap.err(f"source {sid}", f"champ « {k} » vide")
        if s.get("url") and not str(s["url"]).startswith(SCHEMAS_URL):
            rap.err(f"source {sid}", f"URL de schéma inconnu : {s['url']}")
        if s.get("fichier_local"):
            p = RACINE / s["fichier_local"]
            if not p.exists():
                rap.err(f"source {sid}", f"fichier local absent : {s['fichier_local']}")
            elif s.get("taille_octets") is not None and p.is_file() and p.stat().st_size != s["taille_octets"]:
                rap.err(f"source {sid}", f"taille {p.stat().st_size} ≠ {s['taille_octets']} annoncée")
        elif s.get("taille_octets") is not None:
            rap.err(f"source {sid}", "taille annoncée sans fichier local")
        url = str(s.get("url", ""))
        if url.startswith("file:///"):
            p_url = Path(unquote(url[len("file:///"):]))
            if dans_depot(p_url):
                if not p_url.exists():
                    rap.err(f"source {sid}", f"URL locale introuvable : {url}")
                if s.get("fichier_local") and not meme_fichier(p_url, RACINE / s["fichier_local"]):
                    rap.err(f"source {sid}", f"URL locale ({url}) différente de fichier_local ({s['fichier_local']})")
            elif not p_url.exists():
                rap.avert(f"source {sid}", f"URL locale hors dépôt introuvable : {url}")
        if s.get("fichier_hors_depot") and not Path(s["fichier_hors_depot"]).exists():
            rap.avert(f"source {sid}", f"fichier hors dépôt introuvable : {s['fichier_hors_depot']}")
    # tout PDF de data/raw/normes doit figurer au catalogue
    normes = RACINE / "data" / "raw" / "normes"
    cites = {str(Path(s["fichier_local"]).as_posix()) for s in sources.values() if s.get("fichier_local")}
    if normes.exists():
        for f in sorted(normes.rglob("*")):
            if f.is_file() and f.relative_to(RACINE).as_posix() not in cites:
                rap.avert("sources", f"fichier téléchargé non catalogué : {f.relative_to(RACINE).as_posix()}")

    # ------------------------------------------------------------- familles
    familles = {}
    for i, f in enumerate(doc.get("familles", [])):
        for k in ("id", "titre", "description", "nb_regles"):
            if k not in f:
                rap.err(f"familles[{i}]", f"champ « {k} » manquant")
        if f.get("id") in familles:
            rap.err(f"familles[{i}]", f"famille en double : {f.get('id')}")
        familles[f.get("id")] = f

    # ------------------------------------------------------------- règles
    regles = doc.get("regles", [])
    ids = [r.get("id") for r in regles]
    for i, n in Counter(ids).items():
        if n > 1:
            rap.err("regles", f"identifiant en double : {i} ({n} fois)")
    ensemble_ids = set(ids)
    alias = {}
    conflits_doc = {c.get("id") for c in doc.get("conflits", [])}
    usage_src = Counter()
    for idx, r in enumerate(regles):
        rid = r.get("id", f"regles[{idx}]")
        for k, t in CHAMPS_REGLE.items():
            if k not in r:
                rap.err(rid, f"champ obligatoire manquant : {k}")
            elif not isinstance(r[k], t):
                rap.err(rid, f"champ « {k} » de type {type(r[k]).__name__}, attendu {t.__name__}")
        for k, t in CHAMPS_OPTION.items():
            if k in r and not isinstance(r[k], t):
                rap.err(rid, f"champ « {k} » de type {type(r[k]).__name__}, attendu {t.__name__}")
        inconnus = set(r) - set(CHAMPS_REGLE) - set(CHAMPS_OPTION)
        if inconnus:
            rap.avert(rid, f"champs non prévus : {sorted(inconnus)}")
        if not RE_ID.match(str(r.get("id", ""))):
            rap.err(rid, "identifiant hors format <DOMAINE>-<FAMILLE>-<NNN>")
        if r.get("famille") not in familles:
            rap.err(rid, f"famille inconnue : {r.get('famille')}")
        if len(str(r.get("enonce", ""))) < 20:
            rap.err(rid, "énoncé vide ou trop court")
        if not str(r.get("condition", "")).strip():
            rap.err(rid, "condition vide")
        if r.get("action") not in ACTIONS:
            rap.err(rid, f"action inconnue : {r.get('action')}")
        sec = r.get("actions_secondaires", [])
        if isinstance(sec, list):
            for a in sec:
                if a not in ACTIONS:
                    rap.err(rid, f"action secondaire inconnue : {a}")
                if a == r.get("action"):
                    rap.err(rid, f"action secondaire identique à l'action : {a}")
            if len(set(sec)) != len(sec):
                rap.err(rid, "actions secondaires en double")
        if r.get("confiance") not in CONFIANCES:
            rap.err(rid, f"confiance inconnue : {r.get('confiance')}")
        # sources de la règle
        for j, s in enumerate([r.get("source")] + list(r.get("sources_secondaires", []))):
            ou = f"{rid} source{'' if j == 0 else f' secondaire {j}'}"
            if not isinstance(s, dict):
                rap.err(ou, "source absente ou mal formée")
                continue
            for k in ("id", "doc", "ref", "url"):
                if not str(s.get(k, "")).strip():
                    rap.err(ou, f"champ « {k} » vide")
            if s.get("id") not in sources:
                rap.err(ou, f"source inconnue du catalogue : {s.get('id')}")
            else:
                usage_src[s["id"]] += 1
                if s.get("url") != sources[s["id"]].get("url"):
                    rap.err(ou, "URL différente de celle du catalogue")
                if s.get("doc") != sources[s["id"]].get("titre"):
                    rap.avert(ou, "titre différent de celui du catalogue")
            if s.get("url") and not str(s["url"]).startswith(SCHEMAS_URL):
                rap.err(ou, f"URL de schéma inconnu : {s['url']}")
        # applicabilité
        ap = r.get("applicabilite", {})
        if isinstance(ap, dict):
            if ap.get("statut") not in STATUTS:
                rap.err(rid, f"statut d'applicabilité inconnu : {ap.get('statut')}")
            elif ap["statut"] != "immediate" and not ap.get("donnees_requises"):
                rap.err(rid, "applicabilité non immédiate sans « donnees_requises »")
        # alias
        for a in r.get("alias", []):
            if not RE_ID.match(str(a)):
                rap.err(rid, f"alias hors format : {a}")
            if a in ensemble_ids:
                rap.err(rid, f"alias identique à l'identifiant d'une règle : {a}")
            if a in alias:
                rap.err(rid, f"alias déjà porté par {alias[a]} : {a}")
            alias[a] = rid
        # conflits
        for c in r.get("conflits", []):
            if not RE_CF.match(str(c)):
                rap.err(rid, f"code de conflit hors format : {c}")
            elif c not in conflits_doc:
                rap.err(rid, f"conflit inconnu : {c}")
        # unités
        sans = []
        parcourir_nombres(r.get("parametres", {}), "parametres", False, suffixes, sans)
        for ch in sans:
            rap.err(rid, f"nombre sans unité : {ch} (suffixe attendu parmi {sorted(suffixes)} ou préfixe n_/nb_)")
    # familles : comptes et sous-familles
    compte_fam = Counter(r.get("famille") for r in regles)
    sous_fam = defaultdict(set)
    for r in regles:
        sous_fam[r.get("famille")].add(r.get("sous_famille"))
    for fid, f in familles.items():
        if f.get("nb_regles") != compte_fam.get(fid, 0):
            rap.err(f"famille {fid}", f"nb_regles = {f.get('nb_regles')} mais {compte_fam.get(fid, 0)} règles")
        if compte_fam.get(fid, 0) == 0:
            rap.avert(f"famille {fid}", "famille vide")
        if "sous_familles" in f and sorted(f["sous_familles"]) != sorted(sous_fam.get(fid, set())):
            rap.err(f"famille {fid}", f"sous_familles {sorted(f['sous_familles'])} ≠ {sorted(sous_fam.get(fid, set()))} "
                                      "portées par les règles")
    # sources inutilisées ou comptes faux
    for sid, s in sources.items():
        if usage_src.get(sid, 0) == 0 and not s.get("non_exploitee"):
            rap.avert(f"source {sid}", "non citée par une règle (marquer non_exploitee si c'est voulu)")
        if "utilisee_par_n" in s and s["utilisee_par_n"] != usage_src.get(sid, 0):
            rap.err(f"source {sid}", f"utilisee_par_n = {s['utilisee_par_n']} mais {usage_src.get(sid, 0)} citations")

    # ------------------------------------------------------------- références croisées
    connus = ensemble_ids | set(alias)
    for r in regles:
        rid = r.get("id")
        for txt in chaines({k: r.get(k) for k in ("enonce", "condition", "notes", "parametres")}):
            for cite in RE_CITE.findall(txt):
                if cite not in connus:
                    rap.err(rid, f"cite une règle inexistante : {cite}")
                elif cite in alias and cite != rid:
                    rap.avert(rid, f"cite l'alias {cite} : préférer {alias[cite]}")
            for fichier, chemin in RE_REGLE.findall(txt):
                if fichier == "regles_conception":
                    if chemin.split(".")[0] not in connus and not chemin.startswith("<"):
                        rap.err(rid, f"référence regle:regles_conception.{chemin} inconnue")
                    continue
                msg = resoudre_regle(fichier, chemin)
                if msg:
                    rap.err(rid, f"référence regle:{fichier}.{chemin} non résolue ({msg})")

    # ------------------------------------------------------------- historique des versions
    hist = doc.get("historique")
    if hist is not None:
        if not isinstance(hist, list) or not hist:
            rap.err("historique", "liste vide ou mal formée")
        else:
            if hist[-1].get("version") != doc.get("version"):
                rap.err("historique", f"dernière version {hist[-1].get('version')} ≠ version du document {doc.get('version')}")
            for h in hist:
                for cle in ("ajouts", "corrections"):
                    for rr in h.get(cle, []):
                        if rr not in ensemble_ids:
                            rap.err("historique", f"v{h.get('version')} : {cle} cite une règle inexistante : {rr}")

    # ------------------------------------------------------------- fusions d'identifiants
    fus = doc.get("fusions_identifiants")
    if fus is not None and fus != dict(sorted(alias.items())):
        rap.err("fusions_identifiants", "table différente des alias portés par les règles")

    # ------------------------------------------------------------- conflits
    vus = set()
    for i, c in enumerate(doc.get("conflits", [])):
        cid = c.get("id", f"conflits[{i}]")
        if not RE_CF.match(str(cid)):
            rap.err(cid, "code de conflit hors format CF-NN")
        if cid in vus:
            rap.err(cid, "conflit en double")
        vus.add(cid)
        for k in ("sujet", "valeurs", "decision", "principe", "regles"):
            if not c.get(k):
                rap.err(cid, f"champ « {k} » vide")
        for rr in c.get("regles", []):
            if rr not in ensemble_ids:
                rap.err(cid, f"règle inexistante : {rr}")
            else:
                regle = next(x for x in regles if x["id"] == rr)
                if cid not in regle.get("conflits", []):
                    rap.avert(cid, f"{rr} ne renvoie pas à ce conflit")

    # ------------------------------------------------------------- fusion / détection / inférence
    fu = doc.get("fusion_detection_inference", {})
    for k in CLES_FUSION:
        if k not in fu:
            rap.err("fusion_detection_inference", f"rubrique manquante : {k}")
    for txt in chaines(fu):
        for cite in RE_CITE.findall(txt):
            if cite not in connus:
                rap.err("fusion_detection_inference", f"cite une règle inexistante : {cite}")

    # ------------------------------------------------------------- applicabilité ZP-01
    az = doc.get("applicabilite_zp01")
    if az:
        statuts = Counter(r["applicabilite"]["statut"] for r in regles if isinstance(r.get("applicabilite"), dict))
        if az.get("comptes") and az["comptes"] != dict(statuts):
            rap.err("applicabilite_zp01", f"comptes {az['comptes']} ≠ {dict(statuts)}")
        for p in az.get("priorites", []):
            for rr in p.get("regles", []):
                if rr not in ensemble_ids:
                    rap.err("applicabilite_zp01", f"priorité citant une règle inexistante : {rr}")
                elif next(x for x in regles if x["id"] == rr)["applicabilite"]["statut"] == "donnees_nouvelles":
                    rap.avert("applicabilite_zp01", f"{rr} est prioritaire mais attend des données nouvelles")
        for cle in ("partielle", "donnees_nouvelles"):
            attendu = sorted(r["id"] for r in regles if r.get("applicabilite", {}).get("statut") == cle)
            if sorted(az.get(cle, [])) != attendu:
                rap.err("applicabilite_zp01", f"liste « {cle} » incohérente avec les règles")
    return {"regles": len(regles), "familles": len(familles), "sources": len(sources), "alias": len(alias),
            "conflits": len(doc.get("conflits", [])), "actions": dict(Counter(r.get("action") for r in regles)),
            "confiance": dict(Counter(r.get("confiance") for r in regles))}


def valider_resume(chemin, doc, rap):
    """Contrôle que le résumé Markdown posé à côté du JSON suit le JSON (version, nombre de règles, identifiants)."""
    md = chemin.with_name(NOM_RESUME)
    if not md.exists():
        return
    txt = md.read_text(encoding="utf-8")
    titre = txt.splitlines()[0] if txt else ""
    if f"(v{doc.get('version')}," not in titre:
        rap.err(NOM_RESUME, f"titre sans la version v{doc.get('version')} du JSON : {titre!r}")
    n = len(doc.get("regles", []))
    if f"**{n} règles**" not in txt:
        rap.err(NOM_RESUME, f"nombre de règles différent du JSON ({n}) : régénérer le résumé")
    absents = [r.get("id") for r in doc.get("regles", []) if r.get("id") and r["id"] not in txt]
    if absents:
        rap.err(NOM_RESUME, f"{len(absents)} règle(s) absente(s) du résumé : {', '.join(absents[:8])}"
                            f"{' …' if len(absents) > 8 else ''}")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    strict = "--strict" in argv
    args = [a for a in argv if not a.startswith("--")]
    chemin = Path(args[0]) if args else DEFAUT
    rap = Rapport()
    try:
        doc = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[ERREUR] lecture de {chemin} : {e}")
        return 1
    bilan = valider(doc, rap)
    valider_resume(chemin, doc, rap)
    for m in rap.erreurs + rap.avertissements:
        print(m)
    print(f"\n{chemin.name} : {bilan['regles']} règles, {bilan['familles']} familles, {bilan['sources']} sources, "
          f"{bilan['alias']} alias, {bilan['conflits']} conflits")
    print(f"actions {bilan['actions']} ; confiance {bilan['confiance']}")
    print(f"{len(rap.erreurs)} erreur(s), {len(rap.avertissements)} avertissement(s)")
    return 1 if rap.erreurs or (strict and rap.avertissements) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
