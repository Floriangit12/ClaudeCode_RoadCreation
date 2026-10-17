# -*- coding: utf-8 -*-
"""Migration des identifiants de règles des 2 exemples du dossier 12 vers la base fusionnée (lot L0).

Entrée (lecture seule) : D:/DocRoute/12_Modele_Voie_OSM_Generateurs/exemples/{exemple_rue_carrefour,
exemple_rue_residentielle}.json. Sortie (versionnée) : recon/generateur/schema/exemples/ (mêmes noms) et le relevé
recon/generateur/validation/migration_exemples_L0.json.

Règle de migration, dans cet ordre :
1. ancien identifiant du volet 12 (OSM-LAR-020…) → cible de `index_alias` (« 12:OSM-LAR-020 » → RF-OSM-LAR-020) ;
2. identifiant des specs du dépôt (regles_conception GA-*, MQ-* ; regles_implantation SIG-*, VEG-*, GEN-*, ECL-* ;
   regles_locales_meylan LOC-*), absent de index_alias → table MIGRATION_DEPOT ci-dessous, établie à la main en
   relisant l'énoncé de l'ancienne règle et la règle fusionnée (sources_secondaires « DEPOT_RC / DEPOT_RI / DEPOT_RL »
   de la base quand elles existent). Un ancien identifiant peut donner plusieurs règles (listes `regles`) ou aucune :
   ces cas sont relevés dans `manques` (règle absente de regles_route_fr.json, à signaler, jamais inventée).
Seuls les identifiants changent : les valeurs des exemples (fictives) ne sont pas modifiées ; les incohérences
de valeur vues pendant la migration sont relevées dans `remarques`.

Usage : python recon/generateur/schema/migrer_exemples.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
import regles  # noqa: E402

SOURCE = Path("D:/DocRoute/12_Modele_Voie_OSM_Generateurs/exemples")
SORTIE = ICI / "exemples"
RELEVE = ICI.parent / "validation" / "migration_exemples_L0.json"
EXEMPLES = ("exemple_rue_carrefour.json", "exemple_rue_residentielle.json")

# ancien identifiant des specs du dépôt → (règles de la base fusionnée, justification)
MIGRATION_DEPOT = {
    "GA-RAY-001": (["RF-OSM-CAR-030"], "rayon des coins de bordure (Lyon p. 10) : RF-OSM-CAR-030 a GA-RAY-001 pour source ; 6,0 m est dans la classe « urbain dense VL » [5 ; 6]"),
    "GA-BOR-002": (["RF-OSM-NIV-010"], "vue de bordure de trottoir 0,14 m (Lyon p. 16) : source de RF-OSM-NIV-010 ; DEF-005 / ARB-18 retiennent la même valeur"),
    "GA-ILO-001": (["RF-OSM-LAR-051"], "largeur d'îlot refuge (BEV03 p. 6) : source de RF-OSM-LAR-051 (≥ 1,50 ; 2,00 recommandé)"),
    "GA-ILO-003": (["RF-MA-REF-003"], "refuge bordé (vue ≥ 0,12), ressaut 0,02 au droit de la traversée, BEV de chaque côté : même contenu que RF-MA-REF-003"),
    "MQ-LIG-008": (["RF-OSM-MRQ-010"], "axe 1 + 1 en agglomération et seuil de 5,20 m (Paris § II.1 p. 9) : repris par RF-OSM-MRQ-010"),
    "MQ-LIG-001": (["RF-OSM-MRQ-041"], "aucune ligne longitudinale dans un carrefour à feux ou à priorité à droite (IISR7 art. 117-1) : RF-OSM-MRQ-041"),
    "MQ-TRV-002": (["RF-MQ-CED-01"], "ligne cédez T'2 0,50 m à la limite de la chaussée prioritaire avec AB3a (IISR7 art. 117-4 B) : RF-MQ-CED-01"),
    "MQ-TRV-003": (["RF-MQ-STOP-03"], "continue axiale d'approche 2u sur 10-20 m, double sens sans îlot (IISR7 art. 117-4 A-B) : RF-MQ-STOP-03"),
    "MQ-PP-009": (["DEF-012"], "passage en retrait d'environ 2,00 m de la ligne cédez (audit P.2 p. 26) : DEF-012 (ARB-02), qui cite RF-OSM-CAR-040"),
    "MQ-CYC-003": (["DEF-018"], "figurines vélo répétées tous les 50 m environ : DEF-018 (ARB-12), règle RF-MA-CYC-012"),
    "VEG-02": (["RF-OSM-VEG-001"], "recul de l'arbre au bord de chaussée : RF-OSM-VEG-001 (axe ≥ 1,50 m) ; les reculs 0,75 / 1,00 m de VEG-02 (Montpellier) ne sont pas dans la base"),
    "VEG-03": (["RF-GV-TPC-010"], "distances arbre-façade et arbre-arbre : RF-GV-TPC-010 (distance façade 1/2 hauteur adulte, espacement ≥ hauteur adulte)"),
    "VEG-05": (["RF-GV-TPC-011"], "végétation basse ≤ 0,60 m et dégagement 0,60-2,30 m aux abords de carrefour : RF-GV-TPC-011"),
    "GEN-08": (["RF-GV-VIS-001"], "triangles de visibilité urbains sans masque 0,60-2,30 m : RF-GV-VIS-001 (DEF-029, ARB-10)"),
    "ECL-01": ([], "recul du fût de candélabre ≥ 0,50 m derrière l'arête de bordure : AUCUNE règle équivalente dans regles_route_fr.json"),
    "ECL-04": ([], "pas des candélabres = 3 à 5 fois la hauteur de feu : AUCUNE règle équivalente dans regles_route_fr.json"),
    "ECL-05": ([], "distance candélabre-arbre (2 m ; 5 / 8 / 10 m) : AUCUNE règle équivalente dans regles_route_fr.json"),
    "SIG-02": (["RF-SV-GEN.DISTANCE_RIVE"], "bord du panneau à ≥ 0,70 m de la rive (IISR1 art. 8 i) : RF-SV-GEN.DISTANCE_RIVE (ARB-20)"),
    "SIG-03": (["RF-SV-GEN.HAUTEUR.AGGLO"], "hauteur sous panneau (IISR1 art. 9 a-b) ; 2,30 m en agglomération éclairée : RF-SV-GEN.HAUTEUR.AGGLO"),
    "SIG-06": (["RF-SV-AB3A.POSITION", "RF-SV-GEN.SUPPORT_EXCLUSIF_AB3A_AB4"], "AB3a / AB4 au droit de la ligne, support exclusif (IISR3 art. 42-2 C et E ; IISR1 art. 8) : deux règles de la base"),
    "SIG-11": (["RF-SV-B21.EMPLOI"], "panneaux de contournement d'îlot (IISR1 art. 8 b) : RF-SV-B21.EMPLOI"),
    "LOC-TRV-004": (["RF-OBS-SIG-01"], "tête d'îlot séparateur à Meylan (B21-1 au nez) : observation RF-OBS-SIG-01 (B21a1, B21-1 ou J5 au nez d'îlot)"),
}


def cible(ident: str):
    """(nouvelles règles, origine) d'un identifiant cité dans un exemple."""
    if regles.MOTIF.match(ident) and regles.canonique(ident):
        return [regles.canonique(ident)], "déjà conforme"
    if ident in MIGRATION_DEPOT:
        return MIGRATION_DEPOT[ident][0], "table MIGRATION_DEPOT"
    c = regles.canonique(ident)
    if c:
        return [c], "index_alias"
    raise KeyError(f"identifiant sans migration : {ident}")


def migrer(obj, journal, chemin=""):
    """Remplace les identifiants des champs regle, regles et src (defaut:/inference:). Retourne l'objet migré."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            c = f"{chemin}/{k}"
            if k == "regle" and isinstance(v, str):
                nv, orig = cible(v)
                journal.append({"chemin": c, "ancien": v, "nouveau": nv, "par": orig})
                if nv:
                    out[k] = nv[0]
                    if len(nv) > 1:
                        journal[-1]["note"] = "champ 'regle' unique : première règle gardée"
                # sans cible : le champ 'regle' est retiré (relevé dans « manques »)
            elif k == "regles" and isinstance(v, list):
                nouv = []
                for x in v:
                    nv, orig = cible(x)
                    journal.append({"chemin": c, "ancien": x, "nouveau": nv, "par": orig})
                    nouv += [y for y in nv if y not in nouv]
                out[k] = nouv
            elif k == "src" and isinstance(v, str) and v.split(":", 1)[0] in ("defaut", "inference"):
                pre, ident = v.split(":", 1)
                nv, orig = cible(ident)
                journal.append({"chemin": c, "ancien": v, "nouveau": [f"{pre}:{nv[0]}"] if nv else [], "par": orig})
                out[k] = f"{pre}:{nv[0]}" if nv else v
            else:
                out[k] = migrer(v, journal, c)
        return out
    if isinstance(obj, list):
        return [migrer(x, journal, f"{chemin}/{i}") for i, x in enumerate(obj)]
    return obj


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    SORTIE.mkdir(parents=True, exist_ok=True)
    releve = {"date": regles.empreinte()["date"], "base_regles": regles.empreinte(), "table_depot": {
        k: {"regles": v[0], "justification": v[1]} for k, v in MIGRATION_DEPOT.items()}, "exemples": {}}
    for nom in EXEMPLES:
        src = SOURCE / nom
        d = json.loads(src.read_text(encoding="utf-8"))
        journal = []
        m = migrer(d, journal)
        m["meta"]["sources"] = ["assets/specs/route/regles_route_fr.json" if s.startswith("assets/specs/regles_")
                                or s == "inference_osm_profil.json" else s for s in m["meta"].get("sources", [])]
        m["meta"]["sources"] = list(dict.fromkeys(m["meta"]["sources"]))
        m["meta"]["migration"] = ("identifiants de règles migrés vers regles_route_fr.json par "
                                  "recon/generateur/schema/migrer_exemples.py (lot L0) ; valeurs inchangées ; "
                                  "relevé : recon/generateur/validation/migration_exemples_L0.json")
        (SORTIE / nom).write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        manques = sorted({j["ancien"] for j in journal if not j["nouveau"]})
        changes = [j for j in journal if j["par"] != "déjà conforme"]
        releve["exemples"][nom] = {
            "source": str(src).replace("\\", "/"), "sortie": f"recon/generateur/schema/exemples/{nom}",
            "citations": len(journal), "migrees": len(changes),
            "par_origine": {o: sum(1 for j in changes if j["par"] == o) for o in ("index_alias", "table MIGRATION_DEPOT")},
            "anciens_identifiants": sorted({j["ancien"] for j in changes}),
            "manques": manques, "journal": journal}
        print(f"{nom} : {len(journal)} citations, {len(changes)} migrées, sans équivalent : {manques or 'aucun'}")
    releve["remarques"] = [
        "exemple_rue_carrefour.json, signal SG-2 (B21-1 au nez de l'îlot I-1, agglomération) : hauteur_bas_m = 1,00 ; "
        "DEF-026 / ARB-04 retiennent 0,60 m [G] (confiance faible) pour une prescription en agglomération. Valeur "
        "conservée (migration des identifiants seulement), signalée.",
        "exemple_rue_carrefour.json, objets_le_long « candelabres » : recul 0,60 m et pas de 30 m reposaient sur "
        "ECL-01 / ECL-04 (et ECL-05), sans équivalent dans regles_route_fr.json : l'objet ne cite plus aucune règle "
        "après migration ; l'observation RF-OBS-ECL-01 (candélabres de 8 à 11 m) couvrirait la hauteur seulement. "
        "Règles manquantes à ajouter à la base (recul du fût, pas, distance aux arbres).",
        "exemple_rue_carrefour.json, profil P-URB-2V-BC-ST : reference.limite = 3 sans decalage_m alors que la chaussée "
        "(bandes cyclables, tampon et stationnement compris) n'est pas symétrique autour de l'axe ; RF-OSM-PRF-010 "
        "place la ligne OSM au centre de la chaussée. Valeur conservée, signalée.",
    ]
    RELEVE.parent.mkdir(parents=True, exist_ok=True)
    RELEVE.write_text(json.dumps(releve, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"relevé : {RELEVE}")


if __name__ == "__main__":
    main()
