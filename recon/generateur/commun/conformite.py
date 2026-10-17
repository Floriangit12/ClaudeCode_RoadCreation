"""Conformité d'une compilation (description -> modèle) avant fabrication : contrôles bloquants.

Un contrôle du compilateur (compilation.json, troncons[].controles[]) dont le statut est « non_conforme » ou
« hors_plage » bloque la fabrication (fabriquer_generateur.preparer_entree), sauf s'il est admis explicitement par la
description (« ecarts_admis: {<règle>: <motif>} », statut « non_conforme_admis » ou « hors_plage_admis ») pour
décrire un cas réel non conforme. Les erreurs de validation du modèle (valider_modele.py) bloquent toujours.
"""
STATUTS_BLOQUANTS = ("non_conforme", "hors_plage")


def bloquants(compilation: dict) -> list[dict]:
    """Contrôles bloquants d'une compilation (rapport du compilateur ou contenu de compilation.json)."""
    out = []
    for t in compilation.get("troncons", []):
        for c in t.get("controles", []):
            if c.get("statut") in STATUTS_BLOQUANTS:
                out.append(dict(c, route=t.get("route")))
    return out


def erreurs(compilation: dict) -> list:
    """Erreurs de validation du modèle (C01-C13)."""
    return list((compilation.get("validation") or {}).get("erreurs") or [])


def resume(compilation: dict) -> str:
    b, e = bloquants(compilation), erreurs(compilation)
    lignes = [f"{len(e)} erreur(s) de validation, {len(b)} contrôle(s) non conforme(s) non admis"]
    lignes += ["  validation : " + " | ".join(map(str, x)) for x in e[:10]]
    lignes += [f"  {c.get('route')} {c.get('controle')} ({c.get('regle')}) : {c.get('statut')} {c.get('valeur')}"
               for c in b[:20]]
    if b:
        lignes.append("  -> corriger la description, ou admettre l'écart pour un cas réel : « ecarts_admis: "
                      "{<règle>: <motif>} »")
    return "\n".join(lignes)
