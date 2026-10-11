"""REPORT.md de la description résolue (français, déterministe)."""
import collections

import resoudre_regles as RR
import resoudre_revue as RV

LIBELLES = {
    "deplacement": "déplacements", "reorientation": "réorientations", "reorientation_tete": "réorientations de têtes de feux",
    "non_instancie_absent_2026": "objets non instanciés (absents en 2026)", "support_commun": "supports fusionnés (un seul fût)",
    "attribut": "attributs mis à jour", "ajout": "ajouts", "retrait": "marquages retirés (non fabriqués)",
    "recalage_fleche": "flèches recentrées dans leur voie", "arret_a_l_arete": "marques arrêtées à l'arête des bordures",
}


def _tab(entetes, lignes):
    out = ["| " + " | ".join(entetes) + " |", "|" + "---|" * len(entetes)]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in lignes]
    return out


def rapport(sortie, S, J, man, journal, val, planches):
    c = journal["comptes"]
    L = []
    L.append("# Description résolue du carrefour Paquet Jardin (état octobre 2026)")
    L.append("")
    L.append("Base de description 0.3 + seulement les décisions prouvées de la fusion 0.3 et de la cohérence v2, "
             "arbitrées par les revues adverses. Commande : `python recon/pcg/decrire/resoudre.py` "
             "(`--sans-planches`, `--sans-validation`, `--forcer`). Déterministe : deux exécutions donnent des fichiers "
             "identiques à l'octet. Ni `base/`, ni le paquet, ni `enrichi/`, ni `coherence/` ne sont modifiés.")
    L.append("")
    L.append("## Utiliser la description résolue")
    L.append("")
    L.append("- **Houdini** : dans `pj::lire_description`, régler le paramètre **Dossier de la description (`dossier`)** sur "
             "`<dépôt>/recon/out/paquet_jardin/v2/description/resolue/base` au lieu de `.../description/base` (dans la scène "
             "maîtresse : `PJ_DESCRIPTION=<dépôt>/recon/out/paquet_jardin/v2/description/resolue/base`). Le lecteur y trouve "
             "les cinq familles, `nivellement.json` et `nivellement_grille.npz`, et lit le manifeste "
             "`resolue/description_scene_v2.json` (dossier parent). Les marquages retirés portent "
             "`fabrication.statut = non_fabrique` : ils sont exclus par défaut (paramètre « Garder les marquages non fabriqués »).")
    L.append("- **Objets** (non lus par `pj::lire_description`) : `resolue/objets/mobilier.geojson` et `arbres.geojson` ont le "
             "schéma du paquet (`x_local`, `y_local`, `z_local`, `instancier`, `statut_2026`…) plus une propriété `resolution`. "
             "Pour les consommer, pointer la constante `OBJETS` de `recon/pcg/ue/vegetation/arbres.py` (et `PAQUET/donnees/objets` "
             "de `recon/pcg/ue/contexte/preparer_usd.py`) vers `resolue/objets` (modification à faire par leur propriétaire). "
             "Un objet porté (`porte_par`, `instancier_fut = false`) ne doit pas recevoir de fût propre. "
             "`vegetation_ajouts.geojson` (haies, massifs) et `ponctuels_sol_ajouts.geojson` (tampons, avaloirs) sont nouveaux.")
    L.append(f"- **Validation** : `python recon/pcg/decrire/valider.py recon/out/paquet_jardin/v2/description/resolue` : "
             f"{len(val['erreurs'])} erreur, {val['avertissements']} avertissements "
             f"({'identiques à ceux de la base' if val.get('memes_avertissements') else 'à comparer à la base'}). "
             f"Entités remises à l'état de base par la garde de validation : {', '.join(val['bloques']) or 'aucune'}.")
    L.append(f"- **Empreintes** : hash_description {man['hash_description']} (base : {man['statistiques']['resolution']['hash_description_base']}).")
    ch = journal["chaine"]["ecarts"]
    L.append(f"- **Chaîne** (RES-CHN-001) : {'cohérence et fusion ont lu la base courante' if not ch else 'ÉCARTS : ' + ' ; '.join(ch)}.")
    L.append("")
    L.append("## Règles de résolution")
    L.append("")
    for k, v in RR.REGLES.items():
        L.append(f"- **{k}** : {v}")
    L.append("")
    L.append("## Modifications appliquées")
    L.append("")
    L.append(f"{c['appliquees']} modifications appliquées ; {c['non_resolues']} entités ou propositions non résolues.")
    L.append("")
    par = collections.Counter()
    for e in J.appliquees:
        par[(e["famille"], e["nature"])] += 1
    lignes = []
    for (fam, nat), n in sorted(par.items()):
        lignes.append([fam, LIBELLES.get(nat, nat), n])
    L += _tab(["famille", "nature", "n"], lignes)
    L.append("")
    cl = collections.Counter()
    for e in J.appliquees:
        cl[(e.get("classe") or e["famille"], e["nature"])] += 1
    L.append("Par classe d'objet :")
    L.append("")
    L += _tab(["classe", "nature", "n"], [[k[0], LIBELLES.get(k[1], k[1]), n] for k, n in sorted(cl.items())])
    L.append("")
    L.append("### Déplacements et réorientations d'objets")
    L.append("")
    lig = []
    for e in J.appliquees:
        if e["nature"] in ("deplacement", "reorientation", "non_instancie_absent_2026", "support_commun"):
            d = (e["apres"] or {}).get("d_m")
            az = f"{(e['avant'] or {}).get('azimut_deg')} -> {(e['apres'] or {}).get('azimut_deg')}" if e["nature"] == "reorientation" else ""
            rev = (e.get("revue") or "").split(" — ")[0]
            lig.append([f"`{e['id']}`", e.get("classe") or "", e["nature"], f"{d:.2f}" if d is not None else az,
                        e["conf"], ", ".join(e["regles"]), rev])
    L += _tab(["objet", "classe", "décision", "d (m) / azimut", "conf.", "règles", "revue"], lig)
    L.append("")
    L.append("### Marquages")
    L.append("")
    lig = []
    for e in J.appliquees:
        if e["famille"] == "marquages" and e["nature"] != "attribut":
            lig.append([f"`{e['id']}`", e.get("classe") or "", LIBELLES.get(e["nature"], e["nature"]), e["motif"][:150]])
    L += _tab(["marquage", "classe", "décision", "preuve"], lig)
    L.append("")
    L.append("## Planches avant / après (15 changements les plus significatifs)")
    L.append("")
    L.append("Fond : ortho PCRS 5 cm du 2022-05-10 ; jaune : arêtes avant des bordures 2026 ; rouge : avant ; cyan : après. "
             "Mosaïque : `planches/00_index.jpg`. Les planches contiennent une imagerie tierce : elles restent locales.")
    L.append("")
    L += _tab(["#", "entité", "décision", "planche"], [[p["rang"], f"`{p['id']}`", p["nature"], f"`{p['fichier']}`"] for p in planches])
    L.append("")
    lect = getattr(RV, "LECTURE_PLANCHES", {})
    vues = [p for p in planches if p["id"] in lect]
    if vues:
        L.append("Lecture des planches (agent RÉSOLUTION) :")
        L.append("")
        for p in vues:
            L.append(f"- #{p['rang']:02d} `{p['id']}` : {lect[p['id']]}")
        manquantes = [p["id"] for p in planches if p["id"] not in lect]
        if manquantes:
            L.append(f"- planches non relues (sélection changée depuis la dernière lecture) : {', '.join(manquantes)}")
        L.append("")
    L.append("## Ce qui reste non résolu")
    L.append("")
    org = collections.Counter((e["famille"], e["origine"]) for e in J.non_resolues)
    L += _tab(["famille", "origine", "n"], [[k[0], k[1], n] for k, n in sorted(org.items())])
    L.append("")
    L.append("Origines : `conflit` (sources contradictoires), `incertain` (preuve insuffisante ou revue « incertain »), "
             "`proposition_rejetee` (proposition de la fusion ou de la cohérence refusée par une règle RES), `schema` "
             "(non représentable dans le schéma 0.3), `validation` (retirée par la garde de validation).")
    L.append("")
    L.append("### Par station terrain")
    L.append("")
    st = collections.defaultdict(list)
    for e in J.non_resolues:
        s = (e.get("station") or {}).get("station") or "sans position"
        st[s].append(e)
    lig = []
    for s, es in sorted(st.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        note = (es[0].get("station") or {}).get("note") or ""
        nat = collections.Counter(e["nature"].split(":")[0] for e in es)
        uniq = list(dict.fromkeys(e["id"] for e in es))
        ex = ", ".join(f"`{i}`" for i in uniq[:6]) + (" …" if len(uniq) > 6 else "")
        lig.append([s, note[:60], len(es), ", ".join(f"{k} {v}" for k, v in nat.most_common(4)), ex])
    L += _tab(["station", "lieu", "n", "natures principales", "exemples"], lig)
    L.append("")
    L.append("Les stations S1 à S15 sont celles de `recon/pcg/enrichir/PROTOCOLE_TERRAIN.md` (portée 30 m pour une station, "
             "15 m pour un parcours) ; N1, N2… sont des stations à créer (couverture gloutonne de 30 m des entités hors de portée).")
    L.append("")
    L.append("### Propositions rejetées (extrait)")
    L.append("")
    lig = []
    for e in J.non_resolues:
        if e["origine"] in ("proposition_rejetee", "conflit") and e["famille"] in ("mobilier", "arbres", "marquages") and \
                e["nature"].split(":")[0] in ("position", "position_fusion", "recalage_fleche", "violation_physique",
                                              "absence_anterieure_contre_2026", "attribut", "raccourcissement"):
            lig.append([f"`{e['id']}`", e["nature"], e["origine"], e["motif"][:170], (e.get("station") or {}).get("station") or ""])
    L += _tab(["entité", "nature", "origine", "motif", "station"], lig[:60])
    L.append("")
    L.append("## Fichiers")
    L.append("")
    L.append("- `description_scene_v2.json` : manifeste 0.3 (couches et sha256, `statistiques.resolution`, références des entrées).")
    L.append("- `base/` : familles du schéma 0.3 (copies identiques à l'octet quand aucune décision ne les touche).")
    L.append("- `objets/` : objets résolus et ajouts.")
    L.append("- `journal_resolution.json` : décisions appliquées (avant / après, observations, règles, revue, confiance) et "
             "entités non résolues (motif, origine, station).")
    L.append("- `modifications.geojson`, `non_resolus.geojson` : couches de contrôle (L93).")
    L.append("- `planches/` : planches avant / après (locales).")
    (sortie / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
