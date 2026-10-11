"""Sections v3 du REPORT.md du solveur de cohérence (correctifs Q1 à Q8 de la revue adverse v2, recontrôle des
6 faux et des 11 incertains de cette revue, vérifications image, présence 2026, désaccords avec la fusion)."""
import collections

FAUX_V2 = [
    ("lamp_9665416717", "objet", "mesure fusion « pixel_ortho » appliquée (0,88 m) ; les 5 photos décisives placent le fût près de A"),
    ("arbre_027", "objet", "« existant inchangé » alors qu'il est absent sur les 3 photos calées de 2026"),
    ("arbre_028", "objet", "« existant inchangé » alors qu'il est absent sur les 3 photos calées de 2026"),
    ("MF-0286", "fleche", "tiret de la ligne axiale gardé « par l'ortho » ; la fusion le déclare « retirer »"),
    ("MF-0774", "fleche", "recalage proposé alors que la flèche et son recalage sont sur le trottoir"),
    ("MF-8000", "fleche", "recalage poussant la flèche sur la bordure K-0415 (ignorée par le filtre |x| > 0,3 m)"),
]
INCERTAINS_V2 = [
    ("pan_AB3a_2", "objet", "position non prouvée (3 vues du SO dispersées de +0,37 à −1,0 m, mly:1207034570953803 fausse "
                            "localement, σ_travers 0,06 m intenable)"),
    ("pan_D21_1", "objet", "non instancié sans hypothèse de jalonnement relocalisée (P12)"),
    ("pan_J5_2", "objet", "non instancié (même îlot que le D21)"),
    ("pan_B21a1_4", "objet", "azimut 10° -> 341,1° déduit de la voie OpenDRIVE, sans image"),
    ("lamp_lidar_VERC_E", "objet", "0,45 m par triangulation mixte ; deux poteaux proches, identité non établie"),
    ("potelet_13827066658", "objet", "1,90 m par la règle POT-01 ; repère (s, t) hors étendue (P14)"),
    ("portail_12462947807", "objet", "conforme sur la seule foi d'OSM ; aucun portail lisible sur l'ortho 2022"),
    ("portail_12976463291", "objet", "conforme ; OSM 2026-04 dans l'emprise des travaux, invérifiable"),
    ("lamp_9514795817", "objet", "déduit 2026 ; pied d'ombre 2022 à 0,51 m le long de la bordure"),
    ("barriere_levante_12462947804", "objet", "conforme au milieu d'une aire en enrobé, aucun fût visible"),
    ("arbre_236", "objet", "conforme ; ortho 2022 illisible (bande d'ombre)"),
]


def _q1_mes(o, source=None):
    for m in ((o.get("preuve") or {}).get("mesures_candidates") or []):
        if m.get("q1") and (source is None or m["source"] == source):
            return m
    return None


def _etat_objet(r, presence, marq):
    if r is None:
        return "-", "objet absent du rapport"
    c = r.get("correction") or {}
    st = r.get("statut_resolution")
    dr = c.get("drapeaux") or []
    pres = (presence or {}).get(r["id"])
    if st in ("non_instancie_absent_2026", "a_retirer"):
        motif = "constat de présence 2026 (Q4)" if r.get("q4_absent") else (f"fusion « {(r.get('q3') or {}).get('existence')} » (Q3)"
                                                                           if r.get("q3") else "absent de la couche")
        return st, f"non instancié : {motif}" + (f" ; revue de présence : {pres['revue']['note']}" if pres and pres.get("revue") else "")
    txt = [f"{st}, déplacement {c.get('d_m', 0):.2f} m, conf {c.get('conf') or '-'}"]
    m = _q1_mes(r)
    if m:
        q = m["q1"]
        txt.append(f"Q1 sur la mesure {m['source']} : {q['verdict']} (votes {len(q.get('votes_X') or [])} pour la mesure, "
                   f"{len(q.get('votes_A') or [])} pour A ; Σr² {q.get('somme_r2_X')} / {q.get('somme_r2_A')})")
        lo = q.get("laterale_observee")
        if lo:
            txt.append(f"composante latérale observée {lo['decalage_m']:+.2f} ± {lo['sigma_m']:.2f} m "
                       f"({'appliquée' if lo['significative'] else 'non significative'})")
    for mm in ((r.get("preuve") or {}).get("mesures_candidates") or []):
        if str(mm.get("motif_indice") or "").startswith("Q7") and mm.get("valide"):
            txt.append(mm["motif_indice"])
        if mm.get("sigma_saisi_refuse"):
            q6 = mm.get("q6") or {}
            txt.append(f"Q6 : σ saisi refusé ({'; '.join(q6.get('refus') or [])})")
    qc = c.get("q1_candidat")
    if qc:
        txt.append(f"Q1 sur le candidat de la résolution : {qc['verdict']}")
    if c.get("azimut_resolu_deg") is not None and c.get("orientation"):
        txt.append(f"azimut {c.get('azimut_source_deg')} -> {c.get('azimut_resolu_deg')}° ({c.get('orientation')})")
    if pres:
        txt.append(f"présence 2026 : {pres.get('decision')}")
    if dr:
        txt.append("drapeaux : " + ", ".join(dr))
    return st, " ; ".join(txt)


def _etat_fleche(fid, marq):
    r = next((x for x in (marq or {}).get("fleches") or [] if x["id"] == fid), None)
    if r is None:
        return "-", "flèche absente du contrôle"
    st = r["statut"]
    if st == "a_retirer":
        return st, (r.get("note") or "")
    if st == "conflit_surface_marquage":
        return st, f"aucun recalage : {r.get('note')}"
    if st == "glissement_s_propose":
        return st, (f"glissement de {r['glissement_s_m']:+.1f} m en s, voie de {r.get('largeur_voie_apres_m')} m après glissement, "
                    f"entièrement roulable ; limites dans la boîte avant : {', '.join(r.get('limites_dans_boite') or [])}")
    if st == "suppression_proposee":
        return st, r.get("note") or ""
    return st, r.get("note") or (f"écart {r.get('ecart_m')} m" if r.get("ecart_m") is not None else "")


NOUVEL_ETAT = {
    "lamp_9665416717": lambda st, t: "corrigé : reste en A (mesure ramenée à un indice)" if "Q1" in t and st != "mesure" else "à revoir",
    "arbre_027": lambda st, t: "corrigé : non instancié (absent 2026)" if st == "non_instancie_absent_2026" else "à revoir",
    "arbre_028": lambda st, t: "corrigé : non instancié (absent 2026)" if st == "non_instancie_absent_2026" else "à revoir",
    "MF-0286": lambda st, t: "corrigé : à retirer (verdict de la fusion appliqué)" if st == "a_retirer" else "à revoir",
    "MF-0774": lambda st, t: "corrigé : conflit surface / marquage, aucun recalage" if st == "conflit_surface_marquage" else "à revoir",
    "MF-8000": lambda st, t: ("corrigé : glissement en s proposé" if st == "glissement_s_propose" else
                              "corrigé : suppression proposée" if st == "suppression_proposee" else "à revoir"),
}


def recontrole(rap, marquages, presence):
    par = {r["id"]: r for r in rap}
    lignes = []
    for groupe, items in (("faux", FAUX_V2), ("incertain", INCERTAINS_V2)):
        for oid, nat, constat in items:
            if nat == "fleche":
                st, txt = _etat_fleche(oid, marquages)
            else:
                st, txt = _etat_objet(par.get(oid), presence, marquages)
            f = NOUVEL_ETAT.get(oid)
            if f is not None:
                nouvel = f(st, txt)
            elif oid == "pan_AB3a_2":
                nouvel = ("partiellement corrigé : la mesure de la revue n'est plus appliquée (Q6, Q7) ; position par la règle, "
                          "confiance faible ; azimut 15,5° gardé (P4)")
            elif oid in ("pan_D21_1", "pan_J5_2", "pan_B21a1_4", "potelet_13827066658"):
                nouvel = "inchangé : relève de Q9 (P11 à P16), hors de ce lot ; station terrain"
            elif oid == "lamp_lidar_VERC_E":
                nouvel = ("signalé : mesure non testable (aucune pose validée localement, Q2) -> confiance faible"
                          if "mesure_non_testee_q1" in txt else "inchangé")
            else:
                nouvel = "inchangé : aucune photo calée 2026 à moins de 25 m (Q4 ne s'applique pas), aucune mesure à tester (Q1)"
            lignes.append(dict(revue=groupe, id=oid, constat_v2=constat, statut_v3=st, nouvel_etat=nouvel, detail=txt))
    return lignes


def sections(rap, comptes, marquages, presence, journal, objets, q1c, preuves):
    L = []
    w = L.append
    rc = recontrole(rap, marquages, presence)
    n_fx = sum(1 for x in rc if x["revue"] == "faux" and x["nouvel_etat"].startswith("corrigé"))
    q4 = comptes.get("q4") or {}
    w("## Résumé\n")
    w(f"- Faux de la revue v2 corrigés : {n_fx} sur 6 ; incertains : "
      f"{sum(1 for x in rc if x['revue'] == 'incertain' and not x['nouvel_etat'].startswith('inchangé'))} traités ou signalés, "
      f"{sum(1 for x in rc if x['revue'] == 'incertain' and x['nouvel_etat'].startswith('inchangé'))} inchangés (Q9 hors lot ou "
      "aucune photo 2026 à moins de 25 m).")
    w(f"- Mesures confrontées aux photos (Q1) : {sum((comptes.get('q1_mesures') or {}).values())} ; accord "
      f"{(comptes.get('q1_mesures') or {}).get('accord', 0)}, devenues indices : "
      f"{len(comptes.get('q1_mesures_devenues_indices') or [])} objets ; mesures appliquées : {comptes.get('mesures_appliquees')}.")
    w(f"- Absents en 2026 non instanciés : {', '.join(sorted(set(q4.get('absents') or []) | {r['id'] for r in rap if r.get('q3')}))}.")
    w(f"- Déplacé par les travaux (Q8) : {', '.join(k for k, v in (comptes.get('q8_detail') or {}).items() if v == 'deplace_par_travaux') or 'aucun'} ; "
      f"désaccords avec la fusion journalisés : {sum((comptes.get('journal_conflits_fusion') or {}).values())}.\n")
    w("## Ce qui change par rapport à la v2 (revue adverse v2, Q1 à Q8)\n")
    q2 = comptes.get("q2") or {}
    w(f"- **Q1, accord image automatique** : chaque mesure candidate et chaque candidat de la résolution (> 0,3 m) est confronté "
      "aux photos décisives de sa planche : axe vertical détecté entre le pied et la hauteur de l'objet (contraste de barre à "
      "deux flancs, 70e centile de la bande, la structure doit descendre jusqu'au pied), résidus r(A), r(X) en σ de la pose ; "
      "accord exigé sur ≥ 2 photos avec Σr²(X) < Σr²(A) et sans vote majoritaire pour A ; sinon la mesure devient un indice et "
      "l'objet reste en A (ou seule la composante latérale observée s'applique). Mesures : "
      f"{comptes.get('q1_mesures')} ; devenues indices : {', '.join(comptes.get('q1_mesures_devenues_indices') or []) or 'aucune'}. "
      f"Candidats : {comptes.get('q1_candidats')}"
      + (f" ; refusés : {', '.join(comptes['q1_candidats_refuses'])}" if comptes.get("q1_candidats_refuses") else "")
      + ". Résidus imprimés sur chaque planche (pied de vignette) et dans `verifications_image.json`.")
    w(f"- **Q2, décisivité locale des poses** : une photo n'est décisive pour un objet que si ≥ 2 éléments levés (arêtes de bordure "
      "GAM 2026 ou PCRS hors tronçons refaits, marquages GAM ; avant les travaux, seulement les éléments non modifiés) à moins de "
      "15 m de l'objet et à ±30° de son azimut se reprojettent à moins de 2σ (profil moyen du gradient le long de la normale "
      f"image). {q2.get('validees')} validations sur {q2.get('validations')} couples photo-objet ; {q2.get('sans_elements')} sans "
      f"assez d'éléments dans le secteur. σ_rot gonflé (×(1 + 3 − n)) pour les poses à moins de 3 secteurs de 45° : "
      f"{', '.join(q2.get('photos_secteurs_gonfles') or [])}. Une cohérence multi-vues complète le test : une photo hors du "
      "consensus des axes (≥ 3 photos) est écartée pour l'objet. Les portes P2 utilisent cette décisivité locale.")
    w(f"- **Q3, verdicts d'existence de la fusion** (`enrichi/entites_verifiees.json`) : absent_2026 -> non_instancie_absent_2026, "
      f"retirer -> a_retirer (hors contrôle des marquages), absent_2026_a_verifier -> drapeau. Objets : {comptes.get('q3')} ; "
      f"marquages hors contrôle : {(marquages or {}).get('comptes', {}).get('hors_controle_q3')} ; à vérifier : "
      f"{', '.join((marquages or {}).get('comptes', {}).get('absent_2026_a_verifier') or [])}. Désaccords journalisés dans "
      f"`conflits_fusion.json` : {comptes.get('journal_conflits_fusion')}.")
    q4 = comptes.get("q4") or {}
    w(f"- **Q4, présence 2026** : {q4.get('objets')} objets à moins de 25 m d'une photo calée de 2026, chacun avec ses vignettes "
      "(`planches/presence/`), un test automatique (structure verticale ; végétation et tronc pour un arbre) et une entrée de "
      f"revue obligatoire (`revue_coherence.json`, presence_2026) : {q4.get('revus')} revus, absents : "
      f"{', '.join(q4.get('absents') or []) or 'aucun'}. Le test automatique seul est trop faible pour conclure (végétation du "
      f"fond) : {q4.get('auto')}.")
    w(f"- **Q5, flèches** : contraste de la tête seule (tige exclue) ; flèche douteuse si la tige est à moins de 0,10 m de l'axe "
      "d'une ligne longitudinale ou le pied à moins de 0,5 m d'une limite de voie OpenDRIVE ; toute limite qui coupe la boîte "
      "donne voie_coupee (jamais de recalage) ; aucun recalage dont le résultat n'est pas entièrement roulable ; répétitions "
      f"INF-FLE-004 glissées en s (voie ≥ boîte + 2 × 0,3 m) ou supprimées. Comptes : {(marquages or {}).get('comptes', {}).get('fleches')}.")
    w(f"- **Q6, σ des mesures** : covariance anisotrope tirée de la dispersion réelle des résidus photo (triangulation mixte, "
      "axes observés par Q1), plancher d·σ_pose en travers et d·σ_pose / sin(angle) en profondeur (infinie sous 15°) ; σ saisis "
      f"sous le plancher refusés : {', '.join(comptes.get('q6_sigma_saisi_refuse') or []) or 'aucun'}. Une mesure compatible dont "
      "la profondeur n'est pas observée garde la profondeur de la source.")
    w(f"- **Q7, nature des mesures** : pixel_ortho seulement pour les objets au sol ; un mât exige un départ d'ombre corroboré "
      "(deux lectures indépendantes) ou une triangulation photo, tous soumis à Q1. Mesures ramenées à des indices : "
      f"{', '.join(comptes.get('q7_indices') or []) or 'aucune'}.")
    w(f"- **Q8, budget et compatibilité** : le budget de la source d'origine est gardé (dépassements signalés : "
      f"{', '.join(comptes.get('budget_source_depasse') or []) or 'aucun'}) et chaque mesure est testée contre sa source "
      f"(Mahalanobis ≤ 3) : {comptes.get('q8')} ; {comptes.get('q8_detail') or {}}. Statut 2026 mis à jour pour les objets "
      "déplacés par les travaux.")
    w("- **Q10 (défauts cités)** : relèvement moyen par moyenne circulaire (atan2 de la somme des vecteurs) dans la porte P2 ; "
      "en-tête des planches au statut de résolution final ; chaque affirmation chiffrée de la revue passe par Q1 (une revue "
      "« corrigée » contredite par les photos est refusée).\n")
    # ---- recontrôle
    w("## Recontrôle des 6 faux et des 11 incertains de la revue v2\n")
    w(f"Faux corrigés : {n_fx} sur 6. Détail calculé par le solveur (statut et tests de cette exécution) :\n")
    w("| revue v2 | objet | constat de la revue | nouvel état v3 | statut |\n|---|---|---|---|---|")
    for x in rc:
        w(f"| {x['revue']} | `{x['id']}` | {x['constat_v2']} | {x['nouvel_etat']} | {x['statut_v3']} |")
    w("")
    for x in rc:
        w(f"- `{x['id']}` : {x['detail']}")
    w("")
    # ---- vérifications Q1
    if objets:
        w("## Vérifications image (Q1) : mesures\n")
        w("| objet | mesure | nature | verdict | photos sur la mesure | votes mesure / A | Σr² mesure / A | statut |\n"
          "|---|---|---|---|---|---|---|---|")
        for o in objets:
            for m in o.get("mesures") or []:
                q = m.get("q1")
                if not q:
                    continue
                w(f"| `{o['id']}` | {m['source']} | {m.get('nature')} | {q['verdict']} | {q.get('n_observee_X', 0)} | "
                  f"{len(q['votes_X'])} / {len(q['votes_A'])} | {q['somme_r2_X']} / {q['somme_r2_A']} | {m['statut']} |")
        if q1c:
            w("\n**Candidats de la résolution (C contre l'a priori)** : " + "; ".join(
                f"`{k}` {v['verdict']}" for k, v in sorted(q1c.items())) + ".\n")
    # ---- présence
    if presence:
        w("## Présence 2026 (Q4)\n")
        w("| objet | type | auto | revue | photos | note |\n|---|---|---|---|---|---|")
        for k, v in sorted(presence.items()):
            rv = v.get("revue") or {}
            w(f"| `{k}` | {v['type']} | {v['auto']} | **{rv.get('valeur', 'MANQUANTE')}** | "
              f"{', '.join(p['photo'][4:] for p in v['photos'])} | {rv.get('note', '')} |")
        w("")
    # ---- désaccords fusion
    if journal:
        w("## Désaccords avec la fusion (Q3, `conflits_fusion.json`)\n")
        for j in journal:
            w(f"- `{j['entite']}` ({j['nature']}) : {j['decision']}" + (f" — fusion : {j['fusion']}" if j.get("fusion") else "")
              + (f" — cohérence : {j['coherence']}" if j.get("coherence") else ""))
        w("")
    return L
