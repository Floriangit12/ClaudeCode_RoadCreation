"""Consolide les résultats des workflows d'analyse (observation -> 2 vérifications
indépendantes -> arbitrage) en une liste unique de constats avec leur statut :

  verifie_x2      les deux vérificateurs indépendants ont confirmé
  corrige         retenu après correction (arbitre), texte final = version corrigée
  retenu_arbitre  contesté par au moins un vérificateur, retenu par l'arbitre
  ajoute          oubli signalé par un vérificateur et validé par l'arbitre
  incertain       non tranché
  rejete          réfuté (conservé pour traçabilité, à ne pas utiliser)

Entrée : verification/*.json (valeur de retour brute de chaque workflow)
Sortie : constats_verifies.json + constats_verifies.md (tableaux par thème)
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent


def unit_items(doc):
    """Chaque workflow renvoie une liste d'unités (zone, séquence ou thème)."""
    for u in doc:
        key = u.get("zone") or u.get("sequence") or u.get("theme")
        v1 = u.get("verification_reobservation") or u.get("verification_1") or {}
        v2 = u.get("verification_recoupement") or u.get("verification_2") or {}
        yield key, u.get("label", key), u["observation"], v1 or {}, v2 or {}, u.get("arbitrage") or {}


def consolidate():
    out = []
    for f in sorted((HERE / "verification").glob("*.json")):
        for key, label, obs, v1, v2, arb in unit_items(json.loads(f.read_text())):
            vd1 = {v["id"]: v for v in v1.get("verdicts", [])}
            vd2 = {v["id"]: v for v in v2.get("verdicts", [])}
            ad = {a["id"]: a for a in arb.get("arbitrages", [])}
            for c in obs.get("constats", []):
                cid = c["id"]
                a, b, r = vd1.get(cid), vd2.get(cid), ad.get(cid)
                texte = c.get("description") or c.get("enonce")
                usure = c.get("usure")
                if a and b and a["verdict"] == "confirme" and b["verdict"] == "confirme" and not r:
                    statut = "verifie_x2"
                elif r:
                    statut = {"retenu": "retenu_arbitre", "retenu_corrige": "corrige",
                              "rejete": "rejete", "incertain": "incertain"}[r["decision"]]
                    texte = r.get("texte_final") or texte
                    usure = r.get("usure_finale") or usure
                else:
                    statut = "incertain"
                out.append({
                    "id": cid, "source_analyse": f.stem, "unite": key, "unite_label": label,
                    "categorie": c.get("categorie") or c.get("sujet"),
                    "statut": statut, "texte": texte, "texte_initial": c.get("description") or c.get("enonce"),
                    "localisation": c.get("localisation"), "preuve": c.get("preuve"),
                    "usure": usure, "cause_usure": c.get("cause_usure"),
                    "date_source": c.get("date_source"), "confiance_initiale": c.get("confiance"),
                    "verif_reobservation": a, "verif_recoupement": b, "arbitrage": r,
                })
            for i, o in enumerate(arb.get("oublis_valides", []), 1):
                out.append({"id": f"{key}-ajout-{i:02d}", "source_analyse": f.stem, "unite": key,
                            "unite_label": label, "categorie": "ajout_verification",
                            "statut": "ajoute", "texte": o.get("description"),
                            "localisation": o.get("localisation"), "preuve": o.get("preuve"),
                            "usure": o.get("usure")})
    return out


def main():
    rows = consolidate()
    (HERE / "constats_verifies.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    stats = Counter(r["statut"] for r in rows)
    lines = ["# Constats vérifiés — carrefour Paquet Jardin", "",
             "Chaque constat a été produit par un analyste, contrôlé par **deux vérificateurs "
             "indépendants** (re-observation des mêmes images ; recoupement avec d'autres sources), "
             "puis **arbitré** en cas de désaccord.", "",
             "| Statut | Nombre |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in stats.most_common()]
    by = {}
    for r in rows:
        by.setdefault((r["source_analyse"], r["unite_label"]), []).append(r)
    for (src, lab), rs in by.items():
        lines += ["", f"## {lab}  ·  `{src}`", "",
                  "| id | statut | catégorie | usure | constat | localisation |", "|---|---|---|---|---|---|"]
        for r in rs:
            t = (r["texte"] or "").replace("\n", " ").replace("|", "/")
            loc = (r.get("localisation") or "").replace("\n", " ").replace("|", "/")
            lines.append(f"| {r['id']} | {r['statut']} | {r['categorie']} | {r.get('usure') or ''} "
                         f"| {t} | {loc} |")
    (HERE / "constats_verifies.md").write_text("\n".join(lines) + "\n")
    print(len(rows), "constats ;", dict(stats))


if __name__ == "__main__":
    main()
