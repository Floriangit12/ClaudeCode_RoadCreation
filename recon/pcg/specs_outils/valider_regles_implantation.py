"""Valide assets/specs/regles_implantation.json (format, unités, références) et l'essaie sur les données.

Usage (depuis la racine du dépôt, Python 3.11 sans dépendance) :
    python recon/pcg/specs_outils/valider_regles_implantation.py [SPEC]
    python recon/pcg/specs_outils/valider_regles_implantation.py --essai [MOBILIER_GEOJSON]
    python recon/pcg/specs_outils/valider_regles_implantation.py --index-md

Contrôles : identifiants uniques et bien formés, champs requis, vocabulaire (familles, types d'objets,
surfaces, relations, actions, gravités, confiances, sources), suffixe d'unité de chaque paramètre
numérique et plage plausible, intervalles [min, max] ordonnés, tables de même longueur, motifs
regex compilables, cohérence de la table de qualité des preuves.
--essai : applique les règles de surface (gravité critique ou majeure) aux points de mobilier.geojson
avec sa classe de surface v1 et sa distance à la bordure GAM (non signée) ; donne pour chaque
violation la classe de preuve, le déplacement autorisé et le statut de résolution probable. Indicatif :
la résolution complète demande les bordures orientées et les zones dérivées (voir la spec).
Code de sortie 1 si une erreur de format est trouvée.
"""
import json
import os
import re
import sys

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SPEC_DEFAUT = os.path.join(RACINE, "assets", "specs", "regles_implantation.json")
MOBILIER_DEFAUT = os.path.join(RACINE, "recon", "out", "paquet_jardin", "package", "donnees", "objets", "mobilier.geojson")

CHAMPS_REGLE = ["id", "famille", "objet_types", "enonce", "parametres", "surfaces_autorisees",
                "surfaces_interdites", "relations", "action", "gravite", "source", "confiance"]
CHAMPS_OPTIONNELS = {"filtre", "exceptions", "sources_complementaires", "note"}
CLES_TEXTE_RELATION = {"rel", "cible", "cote", "note"}
PLAGES = {  # plage plausible par suffixe d'unité
    "_mm": (0, 10000), "_m": (-50, 100), "_deg": (-360, 360), "_pct": (0, 100), "_m2": (0, 1e5),
    "_m3": (0, 1e4), "_s": (0, 4e9), "_px": (0, 1e5), "_n": (0, 1000), "_ratio": (0, 100), "_kmh": (0, 200),
}
MOTIF_ID = re.compile(r"^[A-Z]{2,3}-\d{2}$")


def rel(chemin):
    """Chemin relatif à la racine du dépôt si possible (sinon absolu : autre lecteur)."""
    try:
        return os.path.relpath(chemin, RACINE)
    except ValueError:
        return chemin


class Rapport:
    def __init__(self):
        self.erreurs, self.alertes = [], []

    def err(self, ou, msg):
        self.erreurs.append(f"{ou} : {msg}")

    def alerte(self, ou, msg):
        self.alertes.append(f"{ou} : {msg}")


def suffixe(cle, unites):
    """Suffixe d'unité de la clé (le plus long qui convient), ou None."""
    ok = [u for u in unites if cle.endswith(u)]
    return max(ok, key=len) if ok else None


def est_nombre(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def verifier_valeur(ou, cle, val, unites, r):
    suf = suffixe(cle, unites)
    if suf is None:
        r.err(ou, f"paramètre « {cle} » sans suffixe d'unité ({', '.join(sorted(unites))})")
        return
    lo, hi = PLAGES.get(suf, (-1e12, 1e12))

    def un(v, ici):
        if not est_nombre(v):
            r.err(ici, f"« {cle} » : valeur non numérique {v!r}")
            return
        if not lo <= v <= hi:
            r.err(ici, f"« {cle} » = {v} hors de la plage plausible [{lo}, {hi}] pour {suf}")
        if suf == "_n" and int(v) != v:
            r.err(ici, f"« {cle} » = {v} : un nombre _n doit être entier")

    if isinstance(val, dict):
        if not val:
            r.err(ou, f"« {cle} » : table par classe vide")
        for k, v in val.items():
            if isinstance(v, list):
                verifier_valeur(f"{ou}.{cle}[{k}]", cle, v, unites, r)
            else:
                un(v, f"{ou}.{cle}[{k}]")
    elif isinstance(val, list):
        for v in val:
            un(v, ou)
        if cle.startswith("table_"):
            if len(val) < 2:
                r.err(ou, f"« {cle} » : table de moins de 2 valeurs")
        elif len(val) != 2:
            r.err(ou, f"« {cle} » : un tableau est un intervalle [min, max] (ou préfixer la clé par table_)")
        elif all(est_nombre(v) for v in val) and val[0] > val[1]:
            r.err(ou, f"« {cle} » : intervalle décroissant {val}")
    else:
        un(val, ou)


def verifier_parametres(ou, params, unites, r):
    if not isinstance(params, dict):
        r.err(ou, "parametres doit être un objet")
        return
    for cle, val in params.items():
        verifier_valeur(ou, cle, val, unites, r)
    tables = {k: v for k, v in params.items() if k.startswith("table_")}
    longueurs = {len(v) for v in tables.values() if isinstance(v, list)}
    if len(longueurs) > 1:
        r.err(ou, f"tables de longueurs différentes : {sorted(tables)}")


def valider(spec, r):
    manque = [c for c in ["schema", "meta", "unites", "sources", "vocabulaire", "regles", "resolution"] if c not in spec]
    for cle in manque:
        r.err("racine", f"clé manquante « {cle} »")
    if manque:
        return
    if not str(spec["schema"]).startswith("regles_implantation/"):
        r.err("schema", f"version inattendue {spec['schema']!r}")
    unites = set(spec["unites"])
    voc = spec["vocabulaire"]
    manque = [c for c in ["familles", "objet_types", "classes_surface", "precedence_zones", "grandeurs", "relations",
                          "actions", "gravites", "confiances", "filtres"] if c not in voc]
    for cle in manque:
        r.err("vocabulaire", f"clé manquante « {cle} »")
    if manque:
        return
    familles, types, surfaces = set(voc["familles"]), set(voc["objet_types"]), set(voc["classes_surface"])
    relations, actions, gravites = set(voc["relations"]), set(voc["actions"]), set(voc["gravites"])
    confiances, sources = set(voc["confiances"]), spec["sources"]

    # sources
    for k, s in sources.items():
        ou = f"sources.{k}"
        for c in ["titre", "url", "local", "statut"]:
            if c not in s:
                r.err(ou, f"champ manquant « {c} »")
        if not s.get("url") and not s.get("local") and s.get("statut") != "a priori":
            r.err(ou, "ni url ni chemin local")
        loc = s.get("local")
        if loc and not os.path.exists(os.path.join(RACINE, loc)):
            r.alerte(ou, f"fichier local absent : {loc}")
    # types d'objets
    for t, d in voc["objet_types"].items():
        if d.get("famille") not in familles:
            r.err(f"objet_types.{t}", f"famille inconnue {d.get('famille')!r}")
        verifier_parametres(f"objet_types.{t}", {k: v for k, v in d.items() if k.startswith("emprise")}, unites, r)
    for z in voc["precedence_zones"]:
        if z not in surfaces:
            r.err("precedence_zones", f"zone inconnue {z!r}")
    for z, d in voc["classes_surface"].items():
        for parent in d.get("dans", []):
            if parent not in surfaces or parent == z:
                r.err(f"classes_surface.{z}", f"classe parente invalide {parent!r}")

    # règles
    vus = set()
    ids = [g.get("id") for g in spec["regles"]]
    for g in spec["regles"]:
        gid = g.get("id", "?")
        ou = f"regle {gid}"
        for c in CHAMPS_REGLE:
            if c not in g:
                r.err(ou, f"champ manquant « {c} »")
        for c in g:
            if c not in CHAMPS_REGLE and c not in CHAMPS_OPTIONNELS:
                r.err(ou, f"champ inconnu « {c} »")
        if not MOTIF_ID.match(str(gid)):
            r.err(ou, "identifiant mal formé (attendu AA-00 ou AAA-00)")
        if gid in vus:
            r.err(ou, "identifiant en double")
        vus.add(gid)
        if g.get("famille") not in familles:
            r.err(ou, f"famille inconnue {g.get('famille')!r}")
        for t in g.get("objet_types", []):
            if t != "*" and t not in types:
                r.err(ou, f"type d'objet inconnu {t!r}")
        if not g.get("objet_types"):
            r.err(ou, "objet_types vide")
        for c in ["surfaces_autorisees", "surfaces_interdites"]:
            for z in g.get(c, []):
                if z not in surfaces and z != "*":
                    r.err(ou, f"{c} : classe inconnue {z!r}")
        commun = set(g.get("surfaces_autorisees", [])) & set(g.get("surfaces_interdites", []))
        if commun:
            r.err(ou, f"classes à la fois autorisées et interdites : {sorted(commun)}")
        verifier_parametres(f"{ou}.parametres", g.get("parametres", {}), unites, r)
        for i, rel in enumerate(g.get("relations", [])):
            oui = f"{ou}.relations[{i}]"
            if rel.get("rel") not in relations:
                r.err(oui, f"relation inconnue {rel.get('rel')!r}")
            if "cible" not in rel:
                r.err(oui, "cible manquante")
            verifier_parametres(oui, {k: v for k, v in rel.items() if k not in CLES_TEXTE_RELATION}, unites, r)
        for i, ex in enumerate(g.get("exceptions", [])):
            oui = f"{ou}.exceptions[{i}]"
            for t in ex.get("objet_types", []):
                if t != "*" and t not in types:
                    r.err(oui, f"type d'objet inconnu {t!r}")
            for z in ex.get("zones_autorisees", []):
                if z not in surfaces:
                    r.err(oui, f"zone inconnue {z!r}")
            ref = ex.get("regle")
            if ref and not (ref in ids or ref.startswith("resolution.")):
                r.err(oui, f"règle référencée inconnue {ref!r}")
            if "filtre" in ex and not isinstance(ex["filtre"], dict):
                r.err(oui, "filtre doit être un objet")
        filtre = g.get("filtre", {})
        if not isinstance(filtre, dict) or any(not isinstance(v, list) for v in filtre.values()):
            r.err(ou, "filtre : objet {propriété: [valeurs]} attendu")
        if g.get("action") not in actions:
            r.err(ou, f"action inconnue {g.get('action')!r}")
        if g.get("gravite") not in gravites:
            r.err(ou, f"gravité inconnue {g.get('gravite')!r}")
        if g.get("confiance") not in confiances:
            r.err(ou, f"confiance inconnue {g.get('confiance')!r}")
        src = g.get("source", {})
        doc = src.get("doc")
        if doc not in sources:
            r.err(ou, f"source inconnue {doc!r}")
        else:
            if src.get("url") != sources[doc].get("url"):
                r.err(ou, f"url de la source différente du registre ({doc})")
            if not src.get("ref"):
                r.err(ou, "source sans référence (article, page)")
        for s2 in g.get("sources_complementaires", []):
            if s2.get("doc") not in sources:
                r.err(ou, f"source complémentaire inconnue {s2.get('doc')!r}")
        if g.get("source", {}).get("doc") == "PRATIQUE" and g.get("confiance") == "haute":
            r.alerte(ou, "règle de pratique (a priori) en confiance haute")

    # couverture
    utilises = {t for g in spec["regles"] for t in g.get("objet_types", [])}
    for t in sorted(types - utilises):
        if "*" not in utilises:
            r.alerte("couverture", f"type {t!r} sans règle propre")
    for f in sorted(familles - {g.get("famille") for g in spec["regles"]}):
        r.alerte("couverture", f"famille {f!r} sans règle")

    # résolution
    res = spec["resolution"]
    manque = [c for c in ["principe", "politique", "parametres", "qualite_preuve", "classes_mesurees", "sigma_confiance",
                          "algorithme", "arbitrage", "preuve_photo", "sortie", "determinisme"] if c not in res]
    for c in manque:
        r.err("resolution", f"clé manquante « {c} »")
    if manque:
        return
    verifier_parametres("resolution.parametres", res["parametres"], unites, r)
    dmax_abs = res["parametres"].get("deplacement_max_absolu_m", 5.0)
    for k, q in res["qualite_preuve"].items():
        ou = f"resolution.qualite_preuve.{k}"
        verifier_parametres(ou, {c: v for c, v in q.items() if c in ("sigma_m", "deplacement_max_m")}, unites, r)
        if q.get("sigma_m", 0) > q.get("deplacement_max_m", 0):
            r.err(ou, "sigma_m supérieur à deplacement_max_m")
        if q.get("deplacement_max_m", 0) > dmax_abs:
            r.err(ou, "deplacement_max_m supérieur au plafond absolu")
        for m in q.get("motifs_source", []):
            try:
                re.compile(m)
            except re.error as e:
                r.err(ou, f"motif invalide {m!r} : {e}")
    if "a_priori" not in res["qualite_preuve"]:
        r.err("resolution.qualite_preuve", "classe de repli « a_priori » manquante")
    for k in res["classes_mesurees"]:
        if k not in res["qualite_preuve"]:
            r.err("resolution.classes_mesurees", f"classe inconnue {k!r}")
    if set(res["sigma_confiance"]) != confiances:
        r.err("resolution.sigma_confiance", "les clés doivent être les confiances du vocabulaire")
    etapes = [e.get("etape") for e in res["algorithme"]]
    if etapes != list(range(1, len(etapes) + 1)):
        r.err("resolution.algorithme", f"étapes non numérotées 1..n : {etapes}")
    verifier_parametres("resolution.preuve_photo",
                        {k: v for k, v in res["preuve_photo"].items() if est_nombre(v)}, unites, r)


# --------------------------------------------------------------------------- essai sur les données
def classe_preuve(source, confiance, res):
    qp = res["qualite_preuve"]
    trouve = [k for k, q in qp.items() if any(re.search(m, source or "", re.I) for m in q["motifs_source"])]
    cle = min(trouve, key=lambda k: (qp[k]["sigma_m"], list(qp).index(k))) if trouve else "a_priori"
    sigma, dmax = qp[cle]["sigma_m"], qp[cle]["deplacement_max_m"]
    if cle not in res["classes_mesurees"]:
        sigma = max(sigma, res["sigma_confiance"].get(confiance, 0.0))
        dmax = min(max(dmax, 2 * sigma), res["parametres"]["deplacement_max_absolu_m"])
    return cle, sigma, dmax


def filtre_ok(filtre, p):
    for cle, vals in (filtre or {}).items():
        if cle == "zone":
            if p.get("classe_surface_2026") not in vals:
                return False
        elif cle == "type_tete":
            if not any(t.get("type") in vals for t in p.get("tetes") or []):
                return False
        elif cle.endswith("_exclus"):
            if p.get(cle[:-7]) in vals:
                return False
        elif cle.endswith("_contient"):
            if not any(v in str(p.get(cle[:-9]) or "") for v in vals):
                return False
        elif p.get(cle) not in vals:
            return False
    return True


def groupes_support(objets):
    """id d'objet -> clé de groupe rigide (GEN-05) : même champ poteau, ou support citant l'id d'un objet."""
    ids = {x["properties"]["id"] for x in objets}
    groupe = {}
    for x in objets:
        p = x["properties"]
        cle = p["id"]
        if p.get("poteau"):
            cle = "poteau:" + str(p["poteau"])
        else:
            cites = [i for i in re.findall(r"[A-Za-z_]+_\d+", str(p.get("support") or "")) if i in ids]
            if cites:
                cle = cites[0]
        groupe[p["id"]] = cle
    return groupe


def essai(spec, chemin):
    res, voc = spec["resolution"], spec["vocabulaire"]
    surf = voc["classes_surface"]
    circulees = {z for z, d in surf.items() if d.get("circulee")}
    seuil_fort = res["parametres"]["seuil_sigma_preuve_forte_m"]
    seuil_norme = res["parametres"]["seuil_sigma_normatif_m"]
    with open(chemin, encoding="utf-8") as f:
        objets = [x for x in json.load(f)["features"] if x["geometry"]["type"] == "Point"]
    objets.sort(key=lambda x: x["properties"]["id"])
    groupe = groupes_support(objets)
    preuve = {x["properties"]["id"]: classe_preuve(x["properties"].get("source"), x["properties"].get("confiance"), res)
              for x in objets}
    meilleure = {}  # clé de groupe -> meilleure preuve (sigma minimal) parmi les membres et le support
    for oid, pr in preuve.items():
        cle = groupe[oid]
        if cle not in meilleure or pr[1] < meilleure[cle][1]:
            meilleure[cle] = pr
    lignes, comptes, preuves = [], {}, {}
    for x in objets:
        p = x["properties"]
        cle, sigma, dmax = meilleure.get(groupe[p["id"]], preuve[p["id"]])
        preuves[cle] = preuves.get(cle, 0) + 1
        zone = p.get("classe_surface_2026")
        if zone is None:
            continue
        violees, a_verifier = [], []
        for g in spec["regles"]:
            if g["gravite"] not in ("critique", "majeur") or zone not in g["surfaces_interdites"]:
                continue
            if "*" not in g["objet_types"] and p["type"] not in g["objet_types"]:
                continue
            if not filtre_ok(g.get("filtre"), p):
                continue
            excuses = set()
            for ex in g.get("exceptions", []):
                concerne = "*" in ex.get("objet_types", []) or p["type"] in ex.get("objet_types", [])
                if concerne and filtre_ok(ex.get("filtre"), p):
                    excuses |= set(ex["zones_autorisees"])
            if zone in excuses:
                continue  # exception explicite pour cette classe
            permises = set(g["surfaces_autorisees"]) | excuses
            if any(zone in surf[z].get("dans", []) for z in permises):
                a_verifier.append(g["id"])  # une zone dérivée permise peut recouvrir la classe v1
            else:
                violees.append(g)
        if not violees and not a_verifier:
            continue
        d_bord = p.get("distance_bordure_gam_m") or 0.0
        besoin = round(d_bord + 0.3, 2)
        critique = any(g["gravite"] == "critique" for g in violees)
        if not violees:
            statut = "a_verifier_zone_derivee"
        elif not critique and sigma < seuil_norme:
            statut = "conforme_signale"
        elif besoin <= dmax:
            statut = "deplacable"
        elif critique and sigma <= seuil_fort:
            statut = "anomalie_surface"
        else:
            statut = "a_arbitrer_photo" + (" (non instancié d'ici là)" if critique and zone in circulees else "")
        comptes[statut.split(" ")[0]] = comptes.get(statut.split(" ")[0], 0) + 1
        ids = [g["id"] for g in violees] + a_verifier
        grp = "" if groupe[p["id"]] == p["id"] else f" groupe={groupe[p['id']]}"
        lignes.append(f"{p['id']:<30} {p['type']:<15} {zone:<15} d_bord={d_bord:5.2f} preuve={cle:<14} "
                      f"sigma={sigma:4.2f} d_max={dmax:4.2f} besoin>={besoin:5.2f} {statut} [{', '.join(ids)}]{grp}")
    print(f"Essai sur {rel(chemin)} : {len(objets)} objets ponctuels")
    print("classes de preuve (après groupes de support) : " + ", ".join(f"{k} {v}" for k, v in sorted(preuves.items())))
    print("\n".join(lignes))
    print("statuts : " + ", ".join(f"{k} {v}" for k, v in sorted(comptes.items())))
    pas = res["parametres"]["pas_azimut_grossier_deg"]
    orientes = [x["properties"] for x in objets if x["properties"].get("azimut_deg") is not None]
    grossiers = [q for q in orientes if float(q["azimut_deg"]) % pas == 0]
    par_type = {}
    for q in grossiers:
        par_type[q["type"]] = par_type.get(q["type"], 0) + 1
    print(f"azimuts multiples de {pas:g}° (grossiers si non mesurés sur photo : à recalculer par SIG-04, FEU-05, "
          f"ECL-02, TC-01) : {len(grossiers)} sur {len(orientes)} ("
          + ", ".join(f"{k} {v}" for k, v in sorted(par_type.items())) + ")")
    print("(besoin = distance non signée à la bordure GAM + 0,30 m : borne basse du déplacement pour quitter la surface "
          "interdite ; classe de surface v1 surfaces_2026, sans zones dérivées)")


def index_md(spec):
    print("| id | famille | objets | énoncé (début) | action | gravité | source | conf. |")
    print("|---|---|---|---|---|---|---|---|")
    for g in spec["regles"]:
        objets = ", ".join(g["objet_types"])
        if len(objets) > 40:
            objets = objets[:37] + "..."
        if g.get("filtre"):
            objets += " (" + "; ".join(f"{k}: {', '.join(map(str, v))}" for k, v in g["filtre"].items()) + ")"
        enonce = g["enonce"].split(" : ")[0].split(". ")[0]
        if len(enonce) > 70:
            enonce = enonce[:67] + "..."
        ref = re.split(r" \(| ;| :", g["source"]["ref"])[0]
        src = f"{g['source']['doc']} {ref[:40]}"
        print(f"| {g['id']} | {g['famille']} | {objets} | {enonce} | {g['action']} | {g['gravite']} | {src} | {g['confiance']} |")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    spec_chemin = SPEC_DEFAUT
    if args and args[0].endswith(".json"):
        spec_chemin = args.pop(0)
    with open(spec_chemin, encoding="utf-8") as f:
        spec = json.load(f)
    if "--index-md" in argv:
        index_md(spec)
        return 0
    r = Rapport()
    valider(spec, r)
    for a in r.alertes:
        print("ALERTE", a)
    for e in r.erreurs:
        print("ERREUR", e)
    n = len(spec.get("regles", []))
    print(f"{rel(spec_chemin)} : {n} règles, {len(r.erreurs)} erreur(s), {len(r.alertes)} alerte(s)")
    if "--essai" in argv and not r.erreurs:
        print()
        essai(spec, args[0] if args else MOBILIER_DEFAUT)
    return 1 if r.erreurs else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
