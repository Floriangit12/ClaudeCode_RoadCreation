# -*- coding: utf-8 -*-
"""Validation d'une instance `modele_voie/0.1` : JSON Schema 2020-12 + contrôles structurels (lot L0).

Copie corrigée de D:/DocRoute/12_Modele_Voie_OSM_Generateurs/outils/valider_modele.py (lecture seule là-bas) :
- C11 n'admet plus que les identifiants de la base fusionnée `assets/specs/route/regles_route_fr.json` (motifs
  RF-…, DEF-nnn, ARB-nn, regles.MOTIF) et les résout par `index_alias` (une règle fusionnée dans une autre reste
  admise) ; un ancien identifiant (OSM-LAR-020, GA-RAY-001…) est une erreur qui donne sa cible s'il en a une ;
- la base est lue par `recon/generateur/regles.py` (plus de lecture des specs du dépôt ni d'inference_osm_profil.json) ;
- C12 (option --exiger-prov) : chaque valeur posée porte une provenance, dénombrée par genre (description, osm,
  regle, table_volet12, mesure, solveur, sans_regle) ;
- C13 : cohérence ARB-19 (branche « stop_a_verifier » : ni ligne STOP, ni continue d'approche, ni AB4).

Usage :
    python recon/generateur/schema/valider_modele.py INSTANCE.json [--schema S] [--exiger-prov] [--anciens-admis]
                                                     [--json RAPPORT.json]
(sans -I : jsonschema est installé dans le site utilisateur.)
Contrôles : C01 identifiants uniques par collection ; C02 len(limites) == len(bandes) + 1 ; C03 reference.limite
dans [0, n] ; C04 identifiants de bande uniques dans un profil ; C05 références nœud / profil / carrefour / îlot /
signal existantes ; C06 sections contiguës couvrant [0, longueur] ; C07 bandes des branches présentes dans le
profil d'extrémité ; C08 graphe (zones, voies, tags déclarés, ≤ 32 tags) ; C09 jamais de ligne STOP / CEDEZ sur une
branche à feux (RF-MQ-CED-03, RF-SV-AB4.POSITION) ; C10 une limite « marquage » porte une marque, « bordure » une
bordure ; C11 toute règle citée (champs regle, regles, src defaut:<id> / inference:<id>) est de la forme admise et
existe dans la base fusionnée ; C12 couverture de la provenance ; C13 ARB-19.
Sortie : une ligne par erreur (code, chemin, message) ; code retour 0 si aucune erreur.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))            # recon/generateur (regles.py)
import regles  # noqa: E402

SCHEMA_DEFAUT = ICI / "modele_voie.schema.json"


def charger(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def regles_citees(obj, chemin=""):
    """(chemin, identifiant) de chaque règle citée dans l'instance."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            c = f"{chemin}/{k}"
            if k == "regle" and isinstance(v, str):
                yield c, v
            elif k == "regles" and isinstance(v, list):
                for x in v:
                    if isinstance(x, str):
                        yield c, x
            elif k == "src" and isinstance(v, str) and v.split(":", 1)[0] in ("defaut", "inference"):
                yield c, v.split(":", 1)[1]
            else:
                yield from regles_citees(v, c)
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from regles_citees(x, f"{chemin}/{i}")


def genre_prov(e: dict) -> str:
    """Genre d'une entrée de provenance : description (valeur dite par la description simple), osm (tag lu),
    regle (complétée par une règle RF/DEF/ARB existante), table_volet12, mesure, solveur (calculée), catalogue (fiche
    d'un catalogue d'assets du dépôt : assets/specs/vegetation.json…), sans_regle."""
    rid = e.get("regle")
    src = e.get("src", "")
    pre = src.split(":", 1)[0]
    if pre == "description":
        return "description"
    if pre == "osm":
        return "osm"
    if rid and regles.existe(rid):
        return "regle"
    if pre in ("defaut", "inference") and regles.existe(src.split(":", 1)[1]):
        return "regle"
    if src.startswith("regle:inference_osm_profil.json"):
        return "table_volet12"
    if pre in ("pcrs", "lidar2021", "ortho2022", "panoramax", "terrain", "mesure", "photo", "bdtopo"):
        return "mesure"
    if pre == "solveur":
        return "solveur"
    if pre == "catalogue":
        return "catalogue"
    return "sans_regle"


def couverture(inst):
    """C12 : (manques, compte des genres). Une clé est couverte par prov[clé] ou prov['*']."""
    manques, genres = [], Counter()

    def tout_prov(o, chemin=""):
        if isinstance(o, dict):
            if isinstance(o.get("prov"), dict):
                for k, e in o["prov"].items():
                    genres[genre_prov(e)] += 1
                    if genre_prov(e) != "regle":
                        genres_detail[(genre_prov(e), k)] += 1
            for k, v in o.items():
                if k != "prov":
                    tout_prov(v, f"{chemin}/{k}")
        elif isinstance(o, list):
            for i, x in enumerate(o):
                tout_prov(x, f"{chemin}/{i}")

    genres_detail = Counter()
    tout_prov(inst)

    def exige(obj, cles, chemin):
        p = obj.get("prov") or {}
        for c in cles:
            if c not in p and "*" not in p:
                manques.append((chemin, c))

    for r in inst.get("routes", []):
        cles = ["categorie", "agglomeration", "vitesse_kmh", "sens_unique"]
        cles += [c for c in ("layer", "prioritaire") if c in r]
        if "placement" in r.get("ligne_reference", {}):
            cles.append("ligne_reference.placement")
        exige(r, cles, f"routes/{r.get('id')}")
    for p in inst.get("profils", []):
        exige(p, [c for c in ("u_m", "reference", "agglomeration") if c in p], f"profils/{p.get('id')}")
        for b in p.get("bandes", []):
            cles = ["*", "largeur"] + [c for c in ("niveau", "materiau_id", "stationnement", "vitesse_kmh",
                                                    "objets_le_long", "terre_plein", "cyclable") if c in b]
            pb = b.get("prov") or {}
            for c in cles:
                if c not in pb:
                    manques.append((f"profils/{p.get('id')}/bandes/{b.get('id')}", c))
        for i, l in enumerate(p.get("limites", [])):
            pl = l.get("prov") or {}
            if "*" in pl:
                continue
            cles = [c for c in ("marquages", "bordure", "separateur") if c in l] or ["nature"]
            for c in cles:
                if c not in pl:
                    manques.append((f"profils/{p.get('id')}/limites/{i}", c))
    for n in inst.get("noeuds", []):
        exige(n, ["type"], f"noeuds/{n.get('id')}")
    for c in inst.get("carrefours", []):
        cles = ["type", "regime"]
        for b in c.get("branches", []):
            cles.append(f"branches[{b.get('id')}].regime")
            for k in ("ligne_arret", "ligne_axiale_approche", "fleches", "coin_droit", "sas_velo"):
                if k in b:
                    cles.append(f"branches[{b.get('id')}].{k}")
        if c.get("trajectoires"):
            cles.append("trajectoires")
        if c.get("anneau"):
            cles.append("anneau")
        exige(c, cles, f"carrefours/{c.get('id')}")
        for pp in c.get("passages_pieton", []) + c.get("traversees_cyclables", []):
            exige(pp, ["*"], f"carrefours/{c.get('id')}/passages/{pp.get('id')}")
    for nom in ("signaux", "ouvrages", "objets", "marquages", "ilots", "zones"):
        for o in inst.get(nom, []):
            exige(o, ["*"], f"{nom}/{o.get('id')}")
    return manques, genres, genres_detail


def valider(inst, schema=None, exiger_prov=False, anciens_admis=False):
    """Liste des erreurs [(code, chemin, message)], avertissements [str] et statistiques {}."""
    err, avert, stats = [], [], {}
    schema = schema if schema is not None else charger(SCHEMA_DEFAUT)
    try:
        import jsonschema
        v = jsonschema.Draft202012Validator(schema)
        for e in sorted(v.iter_errors(inst), key=lambda e: [str(x) for x in e.path]):
            err.append(("SCHEMA", "/".join(map(str, e.path)), e.message[:200]))
    except ImportError:
        err.append(("SCHEMA", "", "module jsonschema absent : pip install --user jsonschema (et lancer sans -I)"))

    def uniques(nom):
        ids = [x.get("id") for x in inst.get(nom, [])]
        for i in sorted(set(map(str, ids))):
            if [str(x) for x in ids].count(i) > 1:
                err.append(("C01", nom, f"identifiant en double : {i}"))
        return {x.get("id"): x for x in inst.get(nom, [])}

    profils = uniques("profils"); noeuds = uniques("noeuds"); routes = uniques("routes")
    carrefours = uniques("carrefours"); ilots = uniques("ilots"); signaux = uniques("signaux")
    uniques("ouvrages"); uniques("objets"); uniques("marquages"); uniques("zones")

    def profil_de(sec):
        p = sec.get("profil")
        return profils.get(p) if isinstance(p, str) else p

    for pid, p in profils.items():
        nb, nl = len(p.get("bandes", [])), len(p.get("limites", []))
        if nl != nb + 1:
            err.append(("C02", f"profils/{pid}", f"{nl} limites pour {nb} bandes (attendu {nb + 1})"))
        k = p.get("reference", {}).get("limite", -1)
        if not (0 <= k <= nb):
            err.append(("C03", f"profils/{pid}", f"reference.limite = {k} hors de [0, {nb}]"))
        ids = [b.get("id") for b in p.get("bandes", [])]
        if len(ids) != len(set(ids)):
            err.append(("C04", f"profils/{pid}", "identifiants de bande en double"))
        for i, l in enumerate(p.get("limites", [])):
            if "marquage" in l.get("nature", []) and not l.get("marquages"):
                err.append(("C10", f"profils/{pid}/limites/{i}", "nature 'marquage' sans marque"))
            if "bordure" in l.get("nature", []) and not l.get("bordure"):
                err.append(("C10", f"profils/{pid}/limites/{i}", "nature 'bordure' sans bordure"))

    for rid, r in routes.items():
        for cle in ("noeud_debut", "noeud_fin"):
            if r.get(cle) not in noeuds:
                err.append(("C05", f"routes/{rid}", f"{cle} inconnu : {r.get(cle)}"))
        for cle in ("carrefour_debut", "carrefour_fin"):
            if cle in r and r[cle] not in carrefours:
                err.append(("C05", f"routes/{rid}", f"{cle} inconnu : {r[cle]}"))
        for s in r.get("signaux", []):
            if s not in signaux:
                err.append(("C05", f"routes/{rid}", f"signal inconnu : {s}"))
        secs = sorted(r.get("sections", []), key=lambda s: s["s0"])
        L = r.get("ligne_reference", {}).get("longueur_m")
        if secs:
            if abs(secs[0]["s0"]) > 1e-6:
                err.append(("C06", f"routes/{rid}", "la première section ne commence pas à s = 0"))
            for a, b in zip(secs, secs[1:]):
                if abs(a["s1"] - b["s0"]) > 1e-6:
                    err.append(("C06", f"routes/{rid}", f"sections non contiguës : {a['s1']} → {b['s0']}"))
            if L is not None and abs(secs[-1]["s1"] - L) > 0.01:
                err.append(("C06", f"routes/{rid}", f"dernière section jusqu'à {secs[-1]['s1']} pour une longueur de {L}"))
            for s in secs:
                if profil_de(s) is None:
                    err.append(("C05", f"routes/{rid}", f"profil inconnu : {s.get('profil')}"))

    for cid, c in carrefours.items():
        for b in c.get("branches", []):
            r = routes.get(b.get("route"))
            if r is None:
                err.append(("C05", f"carrefours/{cid}/{b.get('id')}", f"route inconnue : {b.get('route')}"))
                continue
            secs = sorted(r.get("sections", []), key=lambda s: s["s0"])
            p = profil_de(secs[-1] if b.get("extremite") == "fin" else secs[0]) if secs else None
            ids = {x.get("id") for x in (p or {}).get("bandes", [])}
            for cle in ("bandes_entrantes", "bandes_sortantes"):
                for bd in b.get(cle, []):
                    if bd not in ids:
                        err.append(("C07", f"carrefours/{cid}/{b.get('id')}", f"bande {bd} absente du profil d'extrémité"))
            la = b.get("ligne_arret", {}).get("type")
            if b.get("regime") == "feux" and la in ("STOP", "CEDEZ"):
                err.append(("C09", f"carrefours/{cid}/{b.get('id')}", "ligne STOP/CEDEZ sur une branche à feux (RF-MQ-CED-03)"))
            if b.get("regime") == "stop_a_verifier":
                if la in ("STOP", "CEDEZ"):
                    err.append(("C13", f"carrefours/{cid}/{b.get('id')}", f"ligne {la} sur une branche stop_a_verifier (ARB-19)"))
                if b.get("ligne_axiale_approche"):
                    err.append(("C13", f"carrefours/{cid}/{b.get('id')}", "continue d'approche sur une branche stop_a_verifier (ARB-19)"))
                for sid in b.get("signaux", []):
                    if signaux.get(sid, {}).get("code") == "AB4":
                        err.append(("C13", f"carrefours/{cid}/{b.get('id')}", f"AB4 {sid} sur une branche stop_a_verifier (ARB-19)"))
            for sid in b.get("signaux", []):
                if sid not in signaux:
                    err.append(("C05", f"carrefours/{cid}/{b.get('id')}", f"signal inconnu : {sid}"))
        for i in c.get("ilots", []):
            if i not in ilots:
                err.append(("C05", f"carrefours/{cid}", f"îlot inconnu : {i}"))
        for b in c.get("branches", []):
            if b.get("ilot_separateur") and b["ilot_separateur"] not in ilots:
                err.append(("C05", f"carrefours/{cid}/{b.get('id')}", f"îlot inconnu : {b['ilot_separateur']}"))
    for sid, s in signaux.items():
        a = s.get("applicabilite", {})
        if s.get("code") == "AB4" and a.get("carrefour") in carrefours:
            for b in carrefours[a["carrefour"]].get("branches", []):
                if b.get("id") == a.get("branche") and b.get("regime") == "stop_a_verifier":
                    err.append(("C13", f"signaux/{sid}", f"AB4 appliqué à la branche stop_a_verifier {b.get('id')} (ARB-19)"))

    g = inst.get("graphe_voies")
    if g:
        tags = {t["nom"] for t in g.get("tags", [])}
        if len(tags) > 32:
            err.append(("C08", "graphe_voies", f"{len(tags)} tags > 32 (limite ZoneGraph)"))
        zones = {z["id"] for z in g.get("zones", [])}
        voies = {v["id"] for v in g.get("voies", [])}
        for v in g.get("voies", []):
            if v["zone"] not in zones:
                err.append(("C08", f"graphe_voies/{v['id']}", f"zone inconnue {v['zone']}"))
            for t in v.get("tags", []):
                if t not in tags:
                    err.append(("C08", f"graphe_voies/{v['id']}", f"tag non déclaré {t}"))
        for l in g.get("liens", []):
            for cle in ("de", "vers"):
                if l[cle] not in voies:
                    err.append(("C08", "graphe_voies/liens", f"voie inconnue {l[cle]}"))

    try:
        stats["base_regles"] = regles.empreinte()
    except OSError as e:
        avert.append(f"C11 sauté : base des règles illisible ({e})")
    else:
        n_cit = 0
        for chemin, rid in regles_citees(inst):
            n_cit += 1
            if regles.MOTIF.match(rid):
                if regles.canonique(rid) is None:
                    err.append(("C11", chemin, f"règle inconnue de regles_route_fr.json : {rid}"))
                elif regles.canonique(rid) != rid:
                    avert.append(f"C11 {chemin} : {rid} est un alias de {regles.canonique(rid)} (index_alias)")
                continue
            cible = regles.canonique(rid)
            if anciens_admis and cible:
                avert.append(f"C11 {chemin} : ancien identifiant {rid} admis (→ {cible})")
            elif cible:
                err.append(("C11", chemin, f"ancien identifiant {rid} : citer {cible} (index_alias)"))
            elif regles.ambigu(rid):
                err.append(("C11", chemin, f"ancien identifiant ambigu {rid} : {', '.join(regles.ambigu(rid))}"))
            else:
                err.append(("C11", chemin, f"identifiant de règle mal formé ou absent de la base : {rid}"))
        stats["regles_citees"] = n_cit

    manques, genres, detail = couverture(inst)
    stats["prov_genres"] = dict(sorted(genres.items()))
    stats["prov_hors_regle"] = {f"{g}|{k}": n for (g, k), n in sorted(detail.items())}
    stats["prov_manquantes"] = len(manques)
    if exiger_prov:
        for chemin, cle in manques:
            err.append(("C12", chemin, f"valeur sans provenance : {cle}"))
    return err, avert, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("instance")
    ap.add_argument("schema_pos", nargs="?", help="schéma (forme héritée : 2e argument positionnel)")
    ap.add_argument("--schema")
    ap.add_argument("--exiger-prov", action="store_true", help="C12 : toute valeur posée porte une provenance")
    ap.add_argument("--anciens-admis", action="store_true", help="C11 : anciens identifiants résolus admis (avertissement)")
    ap.add_argument("--json", help="écrit erreurs, avertissements et statistiques dans ce fichier")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    schema = charger(a.schema or a.schema_pos or SCHEMA_DEFAUT)
    err, avert, stats = valider(charger(a.instance), schema, a.exiger_prov, a.anciens_admis)
    for m in avert:
        print(f"AVERTISSEMENT\t{m}")
    for code, chemin, msg in err:
        print(f"{code}\t{chemin}\t{msg}")
    print(f"{len(err)} erreur(s)")
    if a.json:
        Path(a.json).write_text(json.dumps({"instance": a.instance.replace("\\", "/"), "erreurs": [list(e) for e in err],
                                            "avertissements": avert, "statistiques": stats},
                                           ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
