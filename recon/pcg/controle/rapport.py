"""Mise en forme du rapport du vérificateur de règles : raisons des règles non contrôlées et RAPPORT_REGLES.md
(synthèse par famille, 30 pires violations, règles en violation, règles non contrôlées). Texte déterministe."""

NON_IMPLEMENTEES = {
    "DET-KRB-014": "affinage par la marche LiDAR point à point : les dalles LAZ classées (classe 2) ne sont pas sur le "
                   "PC ; la vue décrite est comparée à la marche LiDAR agrégée par VAL-KRB-005 (b)",
    "TQ-VAL-001": "test de scintillement : exige 120 images TSR capturées dans l'éditeur UE (niveau PJ_2026)",
    "MQ-CYC-011": "neutralisation du stationnement avant une bande ou une piste : les places de stationnement ne sont "
                  "pas décrites comme entités",
    "TQ-SOL-011": "déplacement Nanite des matériaux d'enrobé : réglage des matériaux UE, absent des fichiers",
    "TQ-MQR-002": "WPO / PDO des matériaux maîtres : réglage des matériaux UE, absent des fichiers",
    "TQ-MQR-003": "Cast Shadow, distance fields, collisions des components de marquage : réglages de l'import UE",
    "TQ-MQR-004": "réglages Nanite (position_precision, keep_percent) : appliqués après import dans UE",
    "TQ-MQR-006": "choix décalques / géométrie : pas de décalque dans la fabrication v2 (aucune donnée à contrôler)",
    "TQ-OMB-001": "Nanite partout : réglage des StaticMesh importés dans UE",
    "TQ-BOR-001": "ISM vs HISM et data packer cd0..cd6 : graphe PCG PG_Bordures dans UE",
    "TQ-BOR-004": "ombres et cache des ISM de bordure : réglages UE",
    "TQ-PCG-002": "nœud PCG Houdini Digital Asset : réglages du graphe PCG dans UE",
    "TQ-PCG-003": "densité des instances Nanite dispersées : graphes PCG d'UE",
    "TQ-PCG-005": "retouches manuelles dans UE : aucune trace dans les fichiers",
    "TQ-REF-001": "choix d'outillage (Labs Road Generator) : décision documentaire, rien à mesurer",
}

SEV = ["bloquant", "majeur", "mineur", "info"]


def _f(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}".replace(".", ",")
    return str(v)


def _xy(v):
    xy = v.get("xy_local")
    return f"{_f(xy[0], 1)} ; {_f(xy[1], 1)}" if xy else "—"


def _cel(t, n=140):
    t = str(t or "").replace("|", "/").replace("\n", " ")
    return t if len(t) <= n else t[:n - 1] + "…"


def ecrire_md(r, chemin):
    s = r["synthese"]
    e = r["entrees"]
    L = []
    L.append("# Vérification des règles de conception : carrefour Paquet Jardin v2")
    L.append("")
    L.append("Rapport produit par `python recon/pcg/controle/verifier_regles.py` (détail complet : `rapport_regles.json`). "
             "Chaque règle « verifier » de `assets/specs/regles_conception.json`, et chaque règle « contraindre » "
             "mesurable dans les fichiers, est contrôlée sur la description v2 et sur la fabrication Houdini "
             "(`fabrique_hda`). Coordonnées : repère local (L93 − O), en mètres.")
    L.append("")
    L.append("## Entrées")
    L.append("")
    L.append(f"- Règles : `{e['regles']['fichier']}` version {e['regles']['version']}, {e['regles']['n']} règles.")
    L.append(f"- Description : `{e['description']['dossier']}`, schéma {e['description']['schema']}, hash "
             f"`{str(e['description']['hash_description'])[:12]}…`.")
    lu = str(e['fabrication']['hash_description_lu'])[:12]
    coh = "identique" if e['fabrication']['hash_description_lu'] == e['description']['hash_description'] else "DIFFÉRENT"
    L.append(f"- Fabrication : `{e['fabrication']['dossier']}`, description lue `{e['fabrication']['description_lue']}` "
             f"(hash `{lu}…`, {coh} de la description contrôlée).")
    L.append("")
    L.append("## Synthèse")
    L.append("")
    v, c, t = s["verifier"], s["contraindre"], s["toutes"]
    L.append(f"- Règles « verifier » (action principale ou secondaire) : {v['n']} ; contrôlées "
             f"{v['implementees'] + v['partielles']} ({_f(100 * v['taux_couverture'], 0)} %), dont {v['partielles']} "
             f"en partie ; non contrôlées {v['non_implementees']} ; en violation {v['avec_violation']}.")
    L.append(f"- Règles « contraindre » seules : {c['n']} ; contrôlées {c['implementees'] + c['partielles']} ; non "
             f"contrôlables dans les fichiers {c['non_implementees']} (réglages de l'éditeur UE).")
    L.append(f"- Toutes règles : {t['implementees'] + t['partielles']} contrôles exécutés, {t['erreurs']} en erreur.")
    vs = s["violations_par_severite"]
    L.append(f"- Cas en violation : {sum(vs.values())} (bloquant {vs['bloquant']}, majeur {vs['majeur']}, mineur "
             f"{vs['mineur']}, info {vs['info']}).")
    L.append("")
    L.append("### Par famille")
    L.append("")
    L.append("| Famille | Règles | Contrôlées | Cas testés | Violations | Règles en violation | Bloquant | Majeur | Mineur | Info |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for f, d in s["par_famille"].items():
        ps = d["par_severite"]
        L.append(f"| {f} | {d['regles']} | {d['controlees']} | {d['n_teste']} | {d['n_violations']} | "
                 f"{d['regles_en_violation']} | {ps['bloquant']} | {ps['majeur']} | {ps['mineur']} | {ps['info']} |")
    L.append("")
    L.append("## Les 30 pires violations")
    L.append("")
    L.append("Classement : sévérité, puis écart relatif au seuil ; au plus 3 cas par règle.")
    L.append("")
    L.append("| # | Règle | Sévérité | Entité | x ; y (local) | Valeur | Seuil | Détail |")
    L.append("|---:|---|---|---|---|---|---|---|")
    for k, x in enumerate(r["top_violations"], 1):
        L.append(f"| {k} | {x['regle']} | {x['severite']} | {_cel(x.get('entite'), 40)} | {_xy(x)} | "
                 f"{_cel(_f(x.get('valeur'), 3), 24)} | {_cel(x.get('seuil'), 40)} | {_cel(x.get('detail'))} |")
    L.append("")
    L.append("## Règles en violation")
    L.append("")
    L.append("| Règle | Sévérité | Cible | Statut | Testés | Violations | Conformité | Pire cas |")
    L.append("|---|---|---|---|---:|---:|---:|---|")
    lignes = []
    for rid, d in r["regles"].items():
        if d.get("statut") in ("implemente", "partiel") and d.get("n_violations"):
            p = d["pires_cas"][0] if d["pires_cas"] else {}
            lignes.append((SEV.index(d["severite"]), -d["n_violations"], rid,
                           f"| {rid} | {d['severite']} | {d['cible']} | {d['statut']} | {d['n_teste']} | "
                           f"{d['n_violations']} | {_f(100 * (d['taux_conformite'] or 0), 0)} % | "
                           f"{_cel(p.get('entite'), 30)} : {_cel(p.get('detail'), 90)} |"))
    for _, _, _, l_ in sorted(lignes):
        L.append(l_)
    L.append("")
    L.append("## Règles conformes")
    L.append("")
    ok = sorted(rid for rid, d in r["regles"].items() if d.get("statut") in ("implemente", "partiel")
                and not d.get("n_violations") and d.get("n_teste"))
    vides = sorted(rid for rid, d in r["regles"].items() if d.get("statut") in ("implemente", "partiel")
                   and not d.get("n_teste"))
    L.append(f"Sans violation ({len(ok)}) : {', '.join(ok)}.")
    L.append("")
    L.append(f"Sans objet sur le site (aucune entité concernée, {len(vides)}) : {', '.join(vides)}.")
    L.append("")
    L.append("## Règles non contrôlées")
    L.append("")
    L.append("| Règle | Catégorie | Raison |")
    L.append("|---|---|---|")
    for x in r["non_implementees"]:
        L.append(f"| {x['id']} | {x['categorie']} | {_cel(x['raison'], 200)} |")
    L.append("")
    L.append("Les règles « generer » et « deduire_si_absent » sans action secondaire « verifier » ne sont pas contrôlées "
             "en tant que telles : leur résultat est mesuré par les règles « verifier » associées.")
    L.append("")
    L.append("## Méthode")
    L.append("")
    L.append("- Les USD de `fabrique_hda` sont relus en hython (`extraire_fabrication.py`) et mis en cache numpy ; "
             "le sol fabriqué est échantillonné par requête verticale exacte sur ses triangles (grille de 0,10 m du "
             "nivellement pour les pentes, cuvettes, trous et recouvrements).")
    L.append("- Classes de surface : partition de la description rasterisée sur la même grille ; modèle de nivellement : "
             "`nivellement_requete.Nivellement` ; OpenDRIVE : `xodr_echantillonne` et `nivellement_xodr`.")
    L.append("- Unité testée, seuils et limites propres à chaque règle : champs `methode`, `limites` et `mesures` de "
             "`rapport_regles.json`.")
    L.append("- Déterminisme : tri fixe, arrondis fixes, aucun horodatage ; deux exécutions donnent des fichiers "
             "identiques à l'octet.")
    L.append("")
    chemin.write_text("\n".join(L) + "\n", encoding="utf-8")
