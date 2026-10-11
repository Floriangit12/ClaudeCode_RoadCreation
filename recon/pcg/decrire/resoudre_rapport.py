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
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in l) + " |" for l in lignes]
    return out


def _val(v):
    if isinstance(v, dict):
        if "xy_local" in v:
            return f"({v['xy_local'][0]:.3f} ; {v['xy_local'][1]:.3f}), {v.get('d_m', 0):.2f} m"
        if "azimut_deg" in v:
            return f"azimut {v['azimut_deg']}°"
        if "statut_2026" in v:
            return f"instancier {v.get('instancier')} ; statut « {v['statut_2026']} »"
        if "d_m" in v:
            return f"{v['d_m']:.3f} m"
        return ", ".join(f"{k} {x}" for k, x in v.items())[:80]
    return str(v)


def _comparaison(L, cmp_):
    L.append("## Comparaison avec la résolution précédente")
    L.append("")
    if not cmp_:
        L.append("Référence `historique/journal_resolution_r1.json` absente : pas de comparaison.")
        L.append("")
        return
    L.append(f"Référence figée : `{cmp_['reference']}` (résolution r1 : cohérence v2, revue v2). Une modification est "
             "identifiée par (famille, entité, nature, attribut).")
    L.append("")
    L += _tab(["", "résolution r1", "cette résolution"],
              [["modifications appliquées", cmp_["appliquees_r1"], cmp_["appliquees"]],
               ["entités ou propositions non résolues", cmp_["non_resolues_r1"], cmp_["non_resolues"]]])
    L.append("")
    L.append(f"Modifications : {cmp_['inchangees']} inchangées, {len(cmp_['modifiees'])} modifiées, "
             f"{len(cmp_['nouvelles'])} nouvelles, {len(cmp_['retirees'])} retirées (retours à la base). Non résolues : "
             f"{cmp_['non_resolues_sorties']} sorties de la liste (résolues, confirmées ou devenues sans objet), "
             f"{cmp_['non_resolues_entrees']} entrées.")
    L.append("")
    if cmp_["nouvelles"]:
        L.append("Nouvelles :")
        L.append("")
        L += _tab(["entité", "nature", "après", "règles", "motif"],
                  [[f"`{e['id']}`", e["nature"], _val(e["apres"]), ", ".join(e["regles"]), e["motif"][:160]]
                   for e in cmp_["nouvelles"]])
        L.append("")
    if cmp_["modifiees"]:
        L.append("Modifiées :")
        L.append("")
        L += _tab(["entité", "nature", "r1", "maintenant", "motif"],
                  [[f"`{e['id']}`", e["nature"] + (f" ({e['attribut']})" if e.get("attribut") else ""), _val(e["apres_r1"]),
                    _val(e["apres"]), e["motif"][:150]] for e in cmp_["modifiees"]])
        L.append("")
    if cmp_["retirees"]:
        L.append("Retirées (la base est rétablie ; raison actuelle) :")
        L.append("")
        L += _tab(["entité", "nature", "r1", "raison"],
                  [[f"`{e['id']}`", e["nature"], _val(e["apres_r1"]), e["raison"][:200]] for e in cmp_["retirees"]])
        L.append("")


def rapport(sortie, S, J, man, journal, val, planches):
    c = journal["comptes"]
    cmp_ = journal.get("comparaison_r1")
    L = []
    L.append("# Description résolue du carrefour Paquet Jardin (état octobre 2026)")
    L.append("")
    L.append("Base de description 0.3 + seulement les décisions prouvées de la fusion 0.3 et de la cohérence v3, arbitrées "
             "par la revue adverse v3 (et par la revue v2 pour les décisions qu'elle a relues et qui n'ont pas changé, "
             "RES-SRC-002). Une décision jugée « faux » n'est jamais appliquée ; deux retours à la source de la cohérence v3 "
             "jugés « faux » sont corrigés par la position que la revue prouve sur photos (RES-POS-007). Commande : "
             "`python recon/pcg/decrire/resoudre.py` (`--sans-planches`, `--sans-validation`, `--forcer`). Déterministe : "
             "deux exécutions donnent des fichiers identiques à l'octet. Ni `base/`, ni le paquet, ni `enrichi/`, ni "
             "`coherence/` ne sont modifiés.")
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
    L.append(f"- **Empreintes** : hash_description {man['hash_description']} (base : {man['statistiques']['resolution']['hash_description_base']}) ; "
             f"hash_marquages {man['hash_marquages']}.")
    ch = journal["chaine"]["ecarts"]
    L.append(f"- **Chaîne** (RES-CHN-001) : {'cohérence v3 et fusion 0.3 ont lu la base courante' if not ch else 'ÉCARTS : ' + ' ; '.join(ch)}.")
    L.append("")
    _comparaison(L, cmp_)
    # ------------------------------------------------------------------ décisions contre la cohérence
    contre = [e for e in J.appliquees if any(r in e["regles"] for r in ("RES-POS-007", "RES-MQ-004"))]
    if contre:
        L.append("## Décisions prises contre la cohérence v3")
        L.append("")
        L.append("La cohérence v3 a ramené deux mâts à leur source et gardé deux marques générées que la revue adverse v3 "
                 "met en cause ; chaque reprise s'appuie sur la preuve photo de la revue et sur ma seconde lecture des "
                 "vignettes (P16).")
        L.append("")
        L += _tab(["entité", "décision", "preuve (revue v3)", "seconde lecture"],
                  [[f"`{e['id']}`", f"{e['nature']} {_val(e['apres'])}", (e.get("revue") or "")[:230],
                    (e.get("seconde_lecture") or "")[:230]] for e in contre])
        L.append("")
    # ------------------------------------------------------------------ règles
    L.append("## Règles de résolution")
    L.append("")
    for k, v in RR.REGLES.items():
        L.append(f"- **{k}** : {v}")
    L.append("")
    L.append("## Modifications appliquées")
    L.append("")
    L.append(f"{c['appliquees']} modifications appliquées ; {c['non_resolues']} entités ou propositions non résolues ; "
             f"{c['confirmees']} décisions de garder la base confirmées par une revue.")
    L.append("")
    par = collections.Counter()
    for e in J.appliquees:
        par[(e["famille"], e["nature"])] += 1
    L += _tab(["famille", "nature", "n"], [[fam, LIBELLES.get(nat, nat), n] for (fam, nat), n in sorted(par.items())])
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
                        e["conf"], ", ".join(e["regles"]), rev, e.get("comparaison_r1") or ""])
    L += _tab(["objet", "classe", "décision", "d (m) / azimut", "conf.", "règles", "revue", "vs r1"], lig)
    L.append("")
    L.append("### Marquages")
    L.append("")
    lig = []
    for e in J.appliquees:
        if e["famille"] == "marquages" and e["nature"] != "attribut":
            lig.append([f"`{e['id']}`", e.get("classe") or "", LIBELLES.get(e["nature"], e["nature"]), e["motif"][:150],
                        e.get("comparaison_r1") or ""])
    L += _tab(["marquage", "classe", "décision", "preuve", "vs r1"], lig)
    L.append("")
    if J.confirmees:
        L.append("### Base gardée et confirmée par une revue")
        L.append("")
        L += _tab(["entité", "nature", "motif", "revue"],
                  [[f"`{e['id']}`", e["nature"], e["motif"][:170], (e.get("revue") or "").split(" — ")[0]] for e in J.confirmees])
        L.append("")
    # ------------------------------------------------------------------ planches
    L.append(f"## Planches avant / après ({len(planches)} changements)")
    L.append("")
    L.append("À gauche, ortho PCRS 5 cm du 2022-05-10 (antérieure aux travaux) ; jaune : arêtes avant des bordures 2026 ; "
             "rouge : avant ; cyan : après (échelle 1 m pour les déplacements de moins de 0,5 m). À droite, pour un objet, "
             "jusqu'à deux vues perspectives des photos Panoramax calées : axe du mât à la position avant (rouge, A) et "
             "après (cyan, C). Sélection : décisions contre la cohérence, puis nouvelles ou modifiées depuis r1, puis "
             "portée. Mosaïque : `planches/av_ap_00_index.jpg`. Les planches contiennent une imagerie tierce : elles restent "
             "locales (ignorées par git).")
    L.append("")
    L += _tab(["#", "entité", "décision", "vs r1", "photos", "planche"],
              [[p["rang"], f"`{p['id']}`", p["nature"], p.get("comparaison_r1") or "", ", ".join(p.get("photos") or []) or "-",
                f"`{p['fichier']}`"] for p in planches])
    L.append("")
    lect = getattr(RV, "LECTURE_PLANCHES_R2", {})
    vues = [p for p in planches if p["id"] in lect]
    if vues:
        L.append("Lecture des planches (agent RÉSOLUTION, après les avoir regardées) :")
        L.append("")
        for p in vues:
            L.append(f"- #{p['rang']:02d} `{p['id']}` : {lect[p['id']]}")
        L.append("")
    manquantes = [p["id"] for p in planches if p["id"] not in lect]
    if manquantes:
        L.append(f"Planches non relues (sélection changée depuis la dernière lecture) : {', '.join(manquantes)}")
        L.append("")
    # ------------------------------------------------------------------ non résolus
    L.append("## Ce qui reste non résolu")
    L.append("")
    org = collections.Counter((e["famille"], e["origine"]) for e in J.non_resolues)
    L += _tab(["famille", "origine", "n"], [[k[0], k[1], n] for k, n in sorted(org.items())])
    L.append("")
    L.append("Origines : `conflit` (sources contradictoires), `incertain` (preuve insuffisante ou revue « incertain »), "
             "`proposition_rejetee` (proposition de la fusion ou de la cohérence refusée par une règle RES), `schema` "
             "(non représentable dans le schéma 0.3), `validation` (retirée par la garde de validation).")
    L.append("")
    st = collections.defaultdict(list)
    for e in J.non_resolues:
        s = (e.get("station") or {}).get("station") or "sans position"
        st[s].append(e)
    ordre = sorted(st.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    L.append("### Par station terrain")
    L.append("")
    lig = []
    for s, es in ordre:
        note = (es[0].get("station") or {}).get("note") or ""
        nat = collections.Counter(e["nature"].split(":")[0] for e in es)
        lig.append([s, note[:60], len(es), ", ".join(f"{k} {v}" for k, v in nat.most_common(4))])
    L += _tab(["station", "lieu", "n", "natures principales"], lig)
    L.append("")
    L.append("Les stations S1 à S15 sont celles de `recon/pcg/enrichir/PROTOCOLE_TERRAIN.md` (portée 30 m pour une station, "
             "15 m pour un parcours) ; N1, N2… sont des stations à créer (couverture gloutonne de 30 m des entités hors de "
             "portée ; leur numérotation dépend de l'ensemble des entités et change d'une résolution à l'autre).")
    L.append("")
    L.append("### Liste complète par station")
    L.append("")
    L.append("Pour chaque station : entité (nature, origine) — ce qu'il faut regarder sur place. Le détail (motif complet, "
             "proposition, observations, revue) est dans `journal_resolution.json` (`non_resolues`) et `non_resolus.geojson`.")
    L.append("")
    for s, es in ordre:
        note = (es[0].get("station") or {}).get("note") or ""
        L.append(f"**{s}** — {note} ({len(es)})")
        L.append("")
        for e in sorted(es, key=lambda e: (e["famille"], e["id"], e["nature"])):
            L.append(f"- `{e['id']}` ({e['nature']}, {e['origine']}) : {e['motif'][:180]}")
        L.append("")
    L.append("### Propositions rejetées (extrait)")
    L.append("")
    lig = []
    for e in J.non_resolues:
        if e["origine"] in ("proposition_rejetee", "conflit") and e["famille"] in ("mobilier", "arbres", "marquages") and \
                e["nature"].split(":")[0] in ("position", "position_fusion", "recalage_fleche", "glissement_fleche",
                                              "violation_physique", "absence_anterieure_contre_2026", "attribut",
                                              "raccourcissement", "marque_generee_contredite", "conflit_surface_marquage"):
            lig.append([f"`{e['id']}`", e["nature"], e["origine"], e["motif"][:170], (e.get("station") or {}).get("station") or ""])
    L += _tab(["entité", "nature", "origine", "motif", "station"], lig[:60])
    L.append("")
    L.append("## Fichiers")
    L.append("")
    L.append("- `description_scene_v2.json` : manifeste 0.3 (couches et sha256, `statistiques.resolution`, références des entrées).")
    L.append("- `base/` : familles du schéma 0.3 (copies identiques à l'octet quand aucune décision ne les touche).")
    L.append("- `objets/` : objets résolus et ajouts.")
    L.append("- `journal_resolution.json` : décisions appliquées (avant / après, observations, règles, revue, seconde lecture, "
             "confiance, comparaison avec r1), entités non résolues (motif, origine, station), décisions confirmées, "
             "comparaison avec la résolution r1 (`comparaison_r1`), verdicts des revues v3, v2, v1 et secondes lectures.")
    L.append("- `modifications.geojson`, `non_resolus.geojson` : couches de contrôle (L93).")
    L.append("- `historique/journal_resolution_r1.json` : journal figé de la résolution précédente (référence de comparaison).")
    L.append("- `planches/` : planches avant / après (locales, ignorées par git).")
    (sortie / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
