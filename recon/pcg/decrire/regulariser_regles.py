"""Génère assets/specs/REGLES_QUALITE_GEOMETRIQUE.md depuis regles_qualite_geometrique.json (source unique).

Usage : python recon/pcg/decrire/regulariser_regles.py
"""
from commun import SPECS, lire_json

ACTIONS = {"generer": "générer", "contraindre": "contraindre", "verifier": "vérifier", "deduire_si_absent": "déduire si absent"}


def rendu(d):
    L = []
    L.append("# Règles de qualité géométrique (régularisation « plan de VRD professionnel »)\n")
    L.append(f"Version {d['version']} du {d['date']} — format `{d['schema']}` (même format que `regles_conception.json`). "
             "Source unique : `regles_qualite_geometrique.json` ; ce fichier est généré par "
             "`recon/pcg/decrire/regulariser_regles.py`.\n")
    L.append("## Objet\n")
    L.append(d["perimetre"]["objet"] + "\n")
    L.append(f"Chaîne : {d['perimetre']['pipeline']}.\n")
    L.append("Repère et conventions : " + d["conventions"]["repere"] + ".\n")
    L.append("## Synthèse\n")
    L.append("| Id | Action | Énoncé (résumé) | Source principale |")
    L.append("|---|---|---|---|")
    for r in d["regles"]:
        en = r["enonce"].split(". ")[0].rstrip(".")
        L.append(f"| {r['id']} | {ACTIONS.get(r['action'], r['action'])} | {en} | {r['source']['id']} ({r['source']['ref'][:60]}) |")
    L.append("")
    fam = None
    for r in d["regles"]:
        if r["famille"] != fam:
            fam = r["famille"]
            titre = next((f["titre"] for f in d["familles"] if f["id"] == fam), fam)
            L.append(f"## {titre}\n")
        L.append(f"### {r['id']} ({ACTIONS.get(r['action'], r['action'])})\n")
        L.append(r["enonce"] + "\n")
        if r.get("parametres"):
            L.append("Paramètres : " + ", ".join(f"`{k}` = {v}" for k, v in r["parametres"].items()) + ".\n")
        L.append(f"Condition : {r['condition']}.\n")
        s = r["source"]
        L.append(f"Source : **{s['id']}**, {s['doc']}, {s['ref']} — <{s['url']}>.")
        for s2 in r.get("sources_secondaires", []):
            L.append(f"Source secondaire : **{s2['id']}**, {s2['doc']}, {s2['ref']}.")
        L.append("")
        L.append(f"Confiance : {r['confiance']} ; applicabilité : {r['applicabilite']['statut']}"
                 + (f" ; conflits : {', '.join(r['conflits'])}" if r.get("conflits") else "") + ".\n")
        if r.get("implementation"):
            L.append(f"Implémentation : {r['implementation']}.\n")
        if r.get("notes"):
            L.append(f"Notes : {r['notes']}\n")
    L.append("## Conflits\n")
    for c in d["conflits"]:
        L.append(f"- **{c['id']}** ({c['sujet']}) : {c['decision']} — principe : {c['principe']} ; règles {', '.join(c['regles'])}.")
    L.append("\n## Sources\n")
    for s in d["sources"]:
        loc = f" ; copie locale `{s['fichier_local']}`" if s.get("fichier_local") else ""
        url = f" <{s['url']}>" if s.get("url") else ""
        L.append(f"- **{s['id']}** : {s['titre']}{url}{loc}.")
    return "\n".join(L) + "\n"


def main():
    d = lire_json(SPECS / "regles_qualite_geometrique.json")
    (SPECS / "REGLES_QUALITE_GEOMETRIQUE.md").write_text(rendu(d), encoding="utf-8", newline="\n")
    print(SPECS / "REGLES_QUALITE_GEOMETRIQUE.md", len(d["regles"]), "règles")


if __name__ == "__main__":
    main()
