"""Sorties du solveur de cohérence v2 : décisions finales (revue, mesures et porte géométrique comprises),
rapport par objet, couches de corrections, propositions d'ajouts, REPORT.md (français).

Décision finale d'une correction (revue_coherence.json 0.2, verdicts de Claude sur les planches) :
- « corrigee » : la position corrigée correspond aux photos ou à l'ortho -> appliquée (conf moyenne) SI la
  porte géométrique P2 de la paire A-C est « complet » (≥ 2 photos décisives discriminantes, ≥ 15°) ou si
  la revue s'appuie sur l'ortho (vue en plan) ; « lateral » : seule la composante perpendiculaire à la visée
  est validée (position A + composante latérale ; si elle viole une règle physique, C est gardée au titre
  de la règle, conf faible, drapeau profondeur_par_la_regle) ; « non_observable » : la revue ne prouve
  rien, correction par la règle (conf faible) ;
- « origine » : les photos montrent l'objet en A -> gardé (anomalie de surface si A viole une règle) ;
  exige aussi une porte non « non_observable » (sinon conf faible) ;
- « spec » / « triangulee » : position d'une spec ou triangulée retenue ;
- « ambigu » ou pas de revue : correction par la règle, conf faible, a_verifier_terrain2026.
Les mesures (P3) ont déjà remplacé p0 avant la résolution : la correction rapportée est comptée depuis
la POSITION SOURCE de la couche (p_source), le budget depuis la position source BRUTE (p_brut, P9).
"""
import collections
import math
import re

import numpy as np

from coherence_carte import CARTE, COHERENCE, REGLES, ecart_angle
from commun import (DONNEES, RACINE, SPECS, arrondi, coords_geojson, ecrire_geojson, ecrire_json, repere, sha256)

GRAVITE = {"critique": 3, "majeur": 2, "mineur": 1, "info": 0}
REGLE_ORIENT = {"panneau": "SIG-04", "lampadaire": "ECL-02", "abri_bus": "TC-01", "poteau_incendie": "RES-03"}
POIDS_TYPE = {"support_feux": 3.0, "panneau": 2.5, "balise_J11": 2.0, "lampadaire": 1.5, "poteau_reseau": 1.2,
              "mat_camera": 1.2, "potelet": 1.0, "abri_bus": 1.5, "poteau_arret": 1.2, "arbre": 0.8}


def l93(p):
    return [round(float(v), 3) for v in repere(np.asarray(p, float)[None], "l93")[0]]


def loc(p):
    return [round(float(v), 3) for v in np.asarray(p, float)[:2]]


def _verdict(V, statut, orr, dz):
    """violation : l'objet a été (ou doit être) déplacé, réorienté, retiré, ou est mal posé (> 0,10 m) ;
    a_verifier : objet gardé mais signalé (anomalie de surface, règle signalée, orientation contestée) ;
    conforme sinon."""
    dures = [v for v in V if v.get("dure")] if statut not in ("anomalie_surface", "conforme_signale") else []
    if dures or statut in ("corrige", "non_resolu", "a_arbitrer_photo", "mesure") or (orr or {}).get("statut") == "reoriente" \
            or (dz is not None and abs(dz) > 0.10):
        return "violation"
    if statut in ("anomalie_surface", "conforme_signale") or (orr or {}).get("statut") == "orientation_signalee" \
            or any(v["nature"] not in ("info",) and v.get("gravite") in ("critique", "majeur") for v in V) \
            or (dz is not None and abs(dz) > 0.03):
        return "a_verifier"
    return "conforme"


def decider(S, o, a, orr, preuve, conflits_o):
    """Applique la revue photo et la porte géométrique (P2) à la correction proposée."""
    rv = (preuve or {}).get("revue") or {}
    portes = (preuve or {}).get("portes") or {}
    inst = bool(a.get("instancier", True))
    p_src = np.asarray(o.get("p_source", o["p0"]), float)
    pA = np.asarray(o["p0"], float)                 # a priori de la résolution (mesure si elle existe)
    p = np.asarray(a["p"], float)
    statut, conf = a["statut"], a.get("conf")
    drap = list(a.get("drapeaux", []))
    just = list(a.get("justification", []))
    az = (orr or {}).get("az", o.get("azimut0"))
    st_az = (orr or {}).get("statut")
    conf_az = (orr or {}).get("conf")
    v = rv.get("verdict")
    gate = portes.get("C")
    porte_info = None
    if o.get("mesure") and float(np.hypot(*(pA - p_src))) > 0.005:
        m = o["mesure"]
        just.insert(0, f"mesure retenue comme nouvel a priori (P3) : {', '.join(m['sources'])}, σ {m['sigma_m']} m, "
                       f"{m['d_p0_m']:.2f} m de la position source" + (f" (héritée de {m['herite_de']})" if m.get("herite_de") else ""))
        if statut == "conforme":
            statut, conf = "mesure", "moyenne" if m["sigma_m"] <= 0.3 else "faible"
    d = float(np.hypot(*(p - pA)))
    if v == "corrigee":
        if rv.get("support") == "ortho" or gate is None:
            conf = "moyenne"
            just.append(f"revue ({'ortho' if rv.get('support') == 'ortho' else 'planche'}) : position corrigée confirmée "
                        f"({rv.get('note', '')})")
        elif gate["verdict"] == "complet":
            conf = "moyenne"
            just.append(f"revue photo : position corrigée confirmée, porte P2 complète ({gate['n_discriminantes']} photos "
                        f"discriminantes, {gate['angle_intersection_max_deg']}°) ({rv.get('note', '')})")
        elif gate["verdict"] == "lateral":
            lat = np.asarray(gate["direction_laterale"], float)
            q = pA + lat * float((p - pA) @ lat)
            Vq, _, _ = S.evaluer(o, p=q, dures_seulement=True)
            porte_info = f"porte P2 latérale : {gate['n_discriminantes']} photo(s), angle {gate['angle_intersection_max_deg']}° < 15° ; " \
                         f"composante validée {gate['composante_validee_m']:+.2f} m, profondeur {gate['composante_profondeur_m']:+.2f} m non observable"
            if Vq:
                conf = "faible"
                drap.append("profondeur_par_la_regle")
                just.append(f"revue photo : {porte_info} ; la seule composante latérale laisse une violation "
                            f"({', '.join(sorted({x['regle'] for x in Vq}))}) : la profondeur reste celle de la règle")
            else:
                p = q
                conf = "moyenne"
                just.append(f"revue photo : {porte_info} ; position = origine + composante latérale")
        else:
            conf = "faible"
            drap.append("revue_non_probante_geometrie")
            if rv.get("mesure"):
                just.append(f"revue : position = mesure de la revue ; la porte P2 est non observable (les photos voient le "
                            f"déplacement le long de leur visée) : seule la contrainte latérale est prouvée, confiance faible "
                            f"({rv.get('note', '')})")
            else:
                just.append(f"revue photo non probante (porte P2 : aucune photo décisive ne sépare A et C de plus de 3σ) : "
                            f"correction par la règle ({rv.get('note', '')})")
    elif v == "origine":
        observable = rv.get("support") == "ortho" or gate is None or gate["verdict"] != "non_observable"
        if statut in ("non_resolu", "a_arbitrer_photo"):
            statut = "anomalie_surface" if any(x["nature"] == "surface" and x.get("dure") for x in a["_V"]) else "conforme_signale"
            inst = True
            drap = [x for x in drap if x not in ("a_verifier_terrain2026",)]
        if d > 0.005:
            p = pA.copy()
            statut = "anomalie_surface" if any(x["nature"] == "surface" and x.get("dure") for x in a["_V"]) else "conforme_signale"
            just.append(f"revue : l'objet est à sa position (a priori) ({rv.get('note', '')}) ; correction annulée")
            drap = [x for x in drap if x != "a_verifier_terrain2026"]
        else:
            just.append(f"revue : position confirmée ({rv.get('note', '')})")
        conf = "moyenne" if observable else "faible"
        if not observable:
            drap.append("revue_non_probante_geometrie")
    elif v in ("spec", "triangulee"):
        q = rv.get("position_local")
        if q is not None:
            p = np.asarray(q, float)
            statut, conf = "corrige", "moyenne"
            just.append(f"revue : position {v} retenue ({rv.get('note', '')})")
    elif v == "ambigu" or (preuve and not rv and statut == "corrige" and d > 0.30):
        if statut == "corrige":
            conf = "faible"
            if "a_verifier_terrain2026" not in drap:
                drap.append("a_verifier_terrain2026")
            just.append("revue ambiguë ou impossible : correction par la règle, confiance faible" if v == "ambigu"
                        else "pas de revue : correction par la règle, confiance faible")
    if rv.get("instancier") is not None:
        inst = bool(rv["instancier"])
        just.append(f"revue : instanciation {'confirmée' if inst else 'refusée'} ({rv.get('note_instanciation', rv.get('note', ''))})")
    va = rv.get("verdict_azimut")
    if va == "corrigee" and st_az:
        conf_az = "moyenne"
    elif va == "origine" and st_az:
        az, st_az, conf_az = o.get("azimut0"), "orientation_photo", "moyenne"
        just.append(f"revue photo : orientation d'origine confirmée ({rv.get('note_azimut', '')})")
    elif va in ("spec", "valeur"):
        az = rv.get("azimut", az)
        st_az, conf_az = "reoriente", "moyenne"
        just.append(f"revue photo : orientation {'de la spec' if va == 'spec' else 'lue sur les photos'} retenue ({rv.get('note_azimut', '')})")
    for t in rv.get("tests_ordinaux") or []:
        just.append(f"test ordinal {t.get('test')} = {t.get('valeur')} ({', '.join(t.get('photos') or [])}, {t.get('date', '')}) : "
                    f"{t.get('note', '')}")
    return dict(p=p, statut=statut, conf=conf, drapeaux=sorted(set(drap)), justification=just, az=az, statut_az=st_az,
                conf_az=conf_az, revue=rv or None, instancier=inst, porte=gate, porte_info=porte_info)


def ecrire_sorties(S, objets, clotures, evals, resol, arbit, orient, nphotos, collis, conflits, tetes_res,
                   deductions, preuves, revue, ombres=None, journal_mesures=None, marquages=None):
    import coherence_politique as POL
    import coherence_poses as PO
    COHERENCE.mkdir(parents=True, exist_ok=True)
    par_id = {o["id"]: o for o in objets}
    coll_par = collections.defaultdict(list)
    for c in collis:
        coll_par[c["a"]].append(c)
        coll_par[c["b"]].append(c)
    conf_par = collections.defaultdict(list)
    for c in conflits:
        if c.get("objet"):
            conf_par[c["objet"]].append(c)
        if c.get("objet_proche"):
            conf_par[c["objet_proche"]].append(c)
    rap, corr = [], []
    for o in objets:
        ev = evals[o["id"]]
        if o["statut"].startswith("absent"):
            rap.append(dict(id=o["id"], couche=o["couche"], type=o["type"], statut_2026=o["statut"], verdict="conforme",
                            statut_resolution="non_instancie_absent_2026", instancier=False, violations=[]))
            continue
        a = arbit[o["id"]]
        rep = a["_rep"]
        orr = orient.get(o["id"]) or {}
        pr = preuves.get(rep)
        dec = decider(S, o, a, orr, pr, conf_par.get(o["id"], []))
        ctx = ev["ctx"]
        ref = ctx["ref"]
        p = dec["p"]
        p_src = np.asarray(o.get("p_source", o["p0"]), float)
        if float(np.hypot(*(p - p_src))) > 0.005 and not dec["justification"]:
            dec["justification"] = [f"GEN-05 : élément porté aligné sur son support {rep} (groupe rigide {o['groupe']})"]
            dec["conf"] = "haute"
        z_sol_f = float(S.c.z_sol(p[None])[0])
        dalle = "dalle" in str(o.get("z_source") or "")
        z_res = (float(o["z0"]) if dalle and o.get("z0") is not None else z_sol_f)
        dz = None if o.get("z0") is None or dalle else float(o["z0"]) - float(ctx["z_sol"])
        V = list(ev["V"])
        for c in coll_par.get(o["id"], []):
            autre = c["b"] if c["a"] == o["id"] else c["a"]
            V.append(dict(regle="GEN-06", nature=c["nature"], valeur=c["d"], attendu=f">= {c.get('min', 1.0)}",
                          gravite="majeur", action="verifier", dure=False,
                          message=f"{c['nature']} avec {autre} ({c['d']:.2f} m)"))
        statut = dec["statut"]
        if dec["statut_az"] == "reoriente" and statut in ("conforme", "conforme_signale"):
            statut = "reoriente"
        voies = S.c.voies(o["p0"], rayon=20.0, types=("driving", "bus", "biking"))
        v0 = voies[0] if voies else None
        pmr = o.get("_pmr")
        d = float(np.hypot(*(p - p_src)))
        dt = ds = None
        if ref is not None and d > 0.005:
            n = np.array([-ref["tg"][1], ref["tg"][0]])
            dt, ds = float((p - p_src) @ n), float((p - p_src) @ ref["tg"])
        verdict = _verdict(V, statut, {"statut": dec["statut_az"]}, dz)
        lidar = bool(re.search(r"LiDAR", o["source"]))
        pb = o.get("p_brut")
        d_brut = None if pb is None else round(float(np.hypot(*(p - np.asarray(pb, float)))), 3)
        rec = dict(
            id=o["id"], couche=o["couche"], type=o["type"], code=o.get("code"), groupe=o["groupe"],
            membres_groupe=resol[o["id"]]["membres"], statut_2026=o["statut"], confiance_source=o.get("confiance"),
            statut_objet=POL.statut_objet(o), verdict=verdict, statut_resolution=statut, instancier=bool(dec["instancier"]),
            preuve=dict(classe=o["preuve"], classe_propre=o["preuve_propre"], sigma_m=o["sigma"], deplacement_max_m=o["dmax"],
                        source=o["source"], lidar_2021=lidar,
                        photos_calees=dict(n=len(nphotos.get(o["id"], [])), ids=nphotos.get(o["id"], [])),
                        triangulation=o.get("triangulation"),
                        degradation_temporelle=resol[o["id"]].get("degradation_temporelle"),
                        mesure=None if not o.get("mesure") else {k: v for k, v in o["mesure"].items() if k not in ("cov", "xy")},
                        mesures_candidates=[dict(source=m["source"], methode=m["methode"], xy=loc(m["xy"]), sigma_m=m["sigma_m"],
                                                 date=m["date"], statut=m["statut"], valide=m["valide"], motif_rejet=m["motif_rejet"],
                                                 preuves=m["preuves"], note=m.get("note")) for m in o.get("mesures") or []]),
            contexte=dict(zone=ctx["zone"], classe_base=ctx["base"], classe_faible=ctx["faible"],
                          zone_a_priori=ctx["zone_defaut"], source_classe=ctx["source_classe"],
                          arbitree_par_bordure=ctx["arbitree_bordure"],
                          bordure_reference=None if ref is None else ref["id"],
                          s_m=None if ref is None else round(ref["s"], 3), t_m=None if ref is None else round(ref["t"], 3),
                          d_bordure_m=ctx["d_bordure"], emprise_travaux=bool(o.get("_emprise_travaux")),
                          voie=None if v0 is None else dict(route=v0["route"], voie=v0["voie"], type=v0["type"],
                                                           cap_deg=round(v0["cap_deg"], 1), d_m=round(v0["d"], 2)),
                          z_sol_local=round(ctx["z_sol"], 3), largeur_libre=pmr, fuseau_peint=ctx.get("fuseau"),
                          exception_P8=bool(ctx.get("exception_P8"))),
            regles_evaluees=ev["regs"],
            violations=[{k: (arrondi(x, 3) if k != "message" else x) for k, x in v.items()} for v in V],
            correction=dict(
                p_source_l93=l93(p_src), p_resolu_l93=l93(p), p_source_local=loc(p_src), p_resolu_local=loc(p),
                p_apriori_local=loc(o["p0"]), p_brut_local=None if pb is None else loc(pb), source_brute=o.get("source_brute"),
                dmax_brut_m=o.get("dmax_brut"), d_brut_m=d_brut,
                budget_respecte=None if d_brut is None else bool(d_brut <= float(o.get("dmax_brut") or 0) + 1e-6),
                d_m=round(d, 3), dt_m=None if dt is None else round(dt, 3), ds_m=None if ds is None else round(ds, 3),
                azimut_source_deg=o.get("azimut0"), azimut_resolu_deg=dec["az"], azimut_cible_deg=orr.get("cible"),
                orientation=dec["statut_az"], orientation_motif=orr.get("motif"), orientation_raison=orr.get("raison"),
                raccourci=orr.get("raccourci"),
                z_source_local=o.get("z0"), z_resolu_local=round(z_res, 3), z_resolu_ngf=round(z_res + 216.30, 3),
                dz_source_m=None if dz is None else round(dz, 3),
                conf=dec["conf"] or dec["conf_az"], drapeaux=dec["drapeaux"], justification=dec["justification"],
                planche=(pr or {}).get("planche"), photos_planche=(pr or {}).get("photos"),
                portes_geometriques=(pr or {}).get("portes"), revue=dec["revue"],
                regles_dures=resol[o["id"]].get("regles_dures"), passe=a.get("passe"),
                candidat_indicatif_local=None if a.get("candidat_indicatif") is None else loc(a["candidat_indicatif"]),
                prov=dict(src=("mesure:" + ",".join(o["mesure"]["sources"])) if o.get("mesure") and d > 0.005 and statut == "mesure"
                          else ("regle:implantation." + ",".join(resol[o["id"]].get("regles_dures") or [])) if d > 0.005 else o["preuve"],
                          ref=f"déplacement {d:.2f} m depuis la position source ; preuve {o['preuve']}", conf=dec["conf"] or "haute")),
            conflits_specs=[c["id"] for c in conf_par.get(o["id"], [])],
        )
        rap.append(rec)
        moved = d > 0.005
        reor = dec["statut_az"] == "reoriente" and o.get("azimut0") != dec["az"]
        retire = not rec["instancier"]
        base_props = dict(id=o["id"], couche=o["couche"], type=o["type"], code=o.get("code"), groupe=o["groupe"],
                          statut_resolution=statut, verdict=verdict, statut_objet=rec["statut_objet"],
                          conf=dec["conf"] or dec["conf_az"] or "faible", drapeaux=dec["drapeaux"], instancier=rec["instancier"],
                          preuve=o["preuve"], sigma_m=o["sigma"], planche=rec["correction"]["planche"],
                          revue=(dec["revue"] or {}).get("verdict") or (("azimut " + dec["revue"]["verdict_azimut"])
                                                                        if (dec["revue"] or {}).get("verdict_azimut") else None),
                          porte=(dec["porte"] or {}).get("verdict"),
                          p_source_local=loc(p_src), p_resolu_local=loc(p), p_brut_local=rec["correction"]["p_brut_local"],
                          d_brut_m=d_brut, dmax_brut_m=o.get("dmax_brut"), z_resolu_ngf=rec["correction"]["z_resolu_ngf"],
                          mesure=None if not o.get("mesure") else ", ".join(o["mesure"]["sources"]))
        if retire and not moved:
            corr.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": l93(p_src)}, "properties": dict(
                base_props, nature="non_instanciation", d_m=0.0, dt_m=None, ds_m=None,
                azimut_source_deg=o.get("azimut0"), azimut_resolu_deg=dec["az"], delta_azimut_deg=None,
                regles=sorted({v["regle"] for v in V if v.get("dure")}), justification=" ; ".join(dec["justification"]))})
        if moved or reor:
            daz = None if (o.get("azimut0") is None or dec["az"] is None) else round(ecart_angle(o["azimut0"], dec["az"]), 1)
            geom = {"type": "LineString", "coordinates": coords_geojson([l93(p_src), l93(p)])} if moved else \
                {"type": "Point", "coordinates": l93(p)}
            corr.append({"type": "Feature", "geometry": geom, "properties": dict(
                base_props, nature=("deplacement" if moved else "") + ("+" if moved and reor else "") + ("reorientation" if reor else ""),
                d_m=round(d, 3), dt_m=rec["correction"]["dt_m"], ds_m=rec["correction"]["ds_m"],
                azimut_source_deg=o.get("azimut0"), azimut_resolu_deg=dec["az"], delta_azimut_deg=daz,
                regles=sorted({v["regle"] for v in V if v.get("dure")} | ({REGLE_ORIENT.get(o["type"], "SIG-04")} if reor else set())),
                justification=" ; ".join(dec["justification"] + ([orr.get("raison")] if reor and orr.get("raison") else [])))})
    # têtes réorientées
    for t in tetes_res:
        rv = revue.get(t["id"]) or {}
        if t["statut"] == "reoriente":
            az = t["azimut_resolu"]
            if rv.get("verdict_azimut") == "origine":
                az, t["statut"] = t["azimut_source"], "orientation_photo"
            t["revue"] = rv or None
            if t["statut"] == "reoriente":
                sup = par_id[t["support"]]
                corr.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": l93(arbit[sup["id"]]["p"])},
                             "properties": dict(id=t["id"], couche="instances", type="tete_feu", code=t["type_tete"],
                                                groupe=sup["groupe"], nature="reorientation", statut_resolution="reoriente",
                                                verdict=t["verdict"], statut_objet="existant", d_m=0.0,
                                                azimut_source_deg=t["azimut_source"], azimut_resolu_deg=az,
                                                delta_azimut_deg=t["ecart_deg"], regles=[t["regle"]],
                                                conf="moyenne" if t["azimut_source"] % 45 == 0 else "faible",
                                                drapeaux=[], instancier=True,
                                                justification=f"{t['motif']} : azimut {t['azimut_source']}° -> {az}° "
                                                              f"({'grossier, multiple de 45°' if t['azimut_source'] % 45 == 0 else 'preuve faible'})",
                                                preuve=sup["preuve"], sigma_m=sup["sigma"], planche=None, revue=rv.get("verdict_azimut"),
                                                p_source_local=loc(sup.get("p_source", sup["p0"])), p_resolu_local=loc(arbit[sup["id"]]["p"]))})
    # propositions d'ajouts
    adds = []
    for dd in deductions:
        rv = revue.get(dd["id"]) or {}
        if rv.get("verdict") == "rejete":
            dd["statut"] = "rejete_revue"
        if "anneau" in dd:
            g = {"type": "Polygon", "coordinates": [coords_geojson(repere(np.vstack([dd["anneau"], dd["anneau"][:1]]), "l93"))]}
        else:
            g = {"type": "Point", "coordinates": l93(dd["p"])}
        adds.append({"type": "Feature", "geometry": g, "properties": dict(
            id=dd["id"], type=dd["type"], type_tete=dd.get("type_tete"), regle=dd["regle"], support=dd.get("support"),
            azimut_deg=dd.get("azimut"), hauteur_m=dd.get("hauteur_m"), conf=dd["conf"], statut=dd.get("statut", "proposition"),
            src=f"a_priori:regle:{dd['regle']}", justification=dd["justification"], preuves=dd.get("preuves"),
            relief_m=dd.get("relief_m"), p_local=loc(dd["p"]), revue=rv.get("note"), instancier=False)})
    for c in conflits:
        if c["nature"] in ("absent_couche", "identite"):
            rv = revue.get(c["id"]) or {}
            adds.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": l93(c["p_spec"])},
                         "properties": dict(id="ADD-" + c["id"], type="hypothese_spec", type_tete=None, regle="GEN-06",
                                            support=c.get("objet_proche"), azimut_deg=c.get("az_spec"), hauteur_m=None,
                                            conf="faible" if not rv else rv.get("conf", "moyenne"),
                                            statut=rv.get("verdict", "a_arbitrer"), src=f"spec:{c['spec']}:{c['ref']}",
                                            justification=(f"{c['spec']} place {c['ref']} ({c['code']}) à {c['d_m']} m de "
                                                           f"{c['objet_proche']} (même support ?)") if c["nature"] == "identite"
                                            else f"{c['spec']} décrit {c['ref']} ({c['code']}), absent de mobilier.geojson",
                                            preuves=[c.get("source_spec")], relief_m=None, p_local=loc(c["p_spec"]),
                                            revue=rv.get("note"), instancier=False)})
    adds.sort(key=lambda f: f["properties"]["id"])
    corr.sort(key=lambda f: f["properties"]["id"])
    for f in corr + adds:
        f["properties"] = arrondi(f["properties"], 3)
    entete = {"schema": "pj_coherence/0.2", "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98)",
              "role": "couche de corrections séparée, à fusionner par le composeur (ne modifie ni le paquet ni la description de base) ; "
                      "géométrie : position source de la couche -> position résolue"}
    ecrire_geojson(COHERENCE / "corrections.geojson", corr, "corrections", entete)
    ecrire_geojson(COHERENCE / "propositions_ajouts.geojson", adds, "propositions_ajouts", entete)
    # comptes
    comptes = dict(
        par_verdict=dict(sorted(collections.Counter(r["verdict"] for r in rap).items())),
        par_statut=dict(sorted(collections.Counter(r["statut_resolution"] for r in rap).items())),
        par_statut_objet=dict(sorted(collections.Counter(r.get("statut_objet", "absent") for r in rap).items())),
        par_type_verdict={k: dict(v) for k, v in sorted(_croise(rap, "type", "verdict").items())},
        par_couche_verdict={k: dict(v) for k, v in sorted(_croise(rap, "couche", "verdict").items())},
        par_zone_verdict={k: dict(v) for k, v in sorted(_croise(rap, lambda r: (r.get("contexte") or {}).get("zone") or "-", "verdict").items())},
        violations_par_regle=dict(sorted(collections.Counter(v["regle"] for r in rap for v in r["violations"]
                                                            if v.get("nature") not in ("info",)).items())),
        violations_dures_par_regle=dict(sorted(collections.Counter(v["regle"] for r in rap for v in r["violations"]
                                                                  if v.get("dure")).items())),
        violations_molles_signalees=dict(sorted(collections.Counter(v["regle"] for r in rap for v in r["violations"]
                                                                   if not v.get("dure") and v.get("nature") not in ("info", "z", "orientation")
                                                                   and v.get("motif_durete", "").startswith("objet existant")).items())),
        tetes=dict(sorted(collections.Counter(t["statut"] for t in tetes_res).items())),
        corrections=dict(sorted(collections.Counter(f["properties"]["nature"] for f in corr).items())),
        corrections_conf=dict(sorted(collections.Counter(f["properties"]["conf"] for f in corr).items())),
        portes=dict(sorted(collections.Counter((f["properties"].get("porte") or "sans_photo") for f in corr
                                               if f["properties"].get("couche") != "instances").items())),
        propositions=dict(sorted(collections.Counter(f["properties"]["type"] for f in adds).items())),
        non_instancies=sorted(r["id"] for r in rap if not r.get("instancier", True) and r["statut_resolution"] != "non_instancie_absent_2026"),
        mesures_appliquees=len(journal_mesures or []),
        budget_depasse=sorted(r["id"] for r in rap if (r.get("correction") or {}).get("budget_respecte") is False),
        photos_calees=PO.comptes(),
    )
    comptes["cheminement"] = coupes_cheminement(S, {r["id"]: dict(p=np.asarray(r["correction"]["p_resolu_local"], float),
                                                                  instancier=r["instancier"])
                                                    for r in rap if r.get("correction")})
    sources = {k: dict(chemin=v.relative_to(RACINE).as_posix(), sha256=sha256(v)) for k, v in {
        "mobilier": DONNEES / "objets/mobilier.geojson", "arbres": DONNEES / "objets/arbres.geojson",
        "instances": DONNEES / "objets/instances.json", "surfaces_2026": DONNEES / "surfaces/surfaces_2026.geojson",
        "lanes_2026": DONNEES / "opendrive/lanes_2026.geojson", "regles": REGLES, "feux": SPECS / "feux.json",
        "panneaux": SPECS / "panneaux.json", "bordures_v2": RACINE / "recon/out/paquet_jardin/v2/description/base/bordures.geojson",
        "surfaces_v2": RACINE / "recon/out/paquet_jardin/v2/description/base/surfaces.geojson",
        "marquages_v2": RACINE / "recon/out/paquet_jardin/v2/description/base/marquages.geojson",
        "poses": RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json",
        "fusion_corrections": RACINE / "recon/out/paquet_jardin/v2/description/enrichi/corrections_position.geojson"}.items()
        if v.exists()}
    audit = audit_bordures(S)
    ecrire_json(COHERENCE / "rapport_coherence.json", arrondi(dict(
        schema="pj_coherence/0.2", site="paquet_jardin", etat="octobre 2026",
        repere="local = L93 - (917279.43, 6460289.98), z = NGF - 216.30",
        methode="voir recon/pcg/decrire/coherence.py et REPORT.md", sources=sources,
        carte=dict(dossier=CARTE.relative_to(RACINE).as_posix(), bordures=len(S.c.bordures), voies=len(S.c.lanes),
                   passages=len(S.c.passages), audit_orientation_bordures=audit, abaisses=S.c.abaisses),
        politique=dict(P7=POL.SOURCES_P7, P8=POL.EXCEPTION_GEN02["source"], surfaces_physiques=sorted(POL.SURFACES_PHYSIQUES)),
        comptes=comptes, ombres=None if not ombres else {k: dict(soleil=v.get("soleil"), validation=v.get("validation"),
                                                                    sigma_preuve_m=v.get("sigma_preuve_m"))
                                                          for k, v in ombres["par_ortho"].items()},
        objets=rap, clotures=[dict(id=c["id"], statut_resolution="conforme", verdict="conforme",
                                   regle="BAR-02", note="limite dure, jamais déplacée") for c in clotures],
        tetes=tetes_res, conflits_specs=[{k: (loc(v) if k == "p_spec" else v) for k, v in c.items()} for c in conflits],
        doublons_collisions=collis, propositions=[f["properties"] for f in adds],
        marquages=None if not marquages else marquages["comptes"]), 3))
    apercu_corrections(S, rap, adds)
    ecrire_rapport_md(rap, corr, adds, comptes, tetes_res, conflits, preuves, ombres, marquages, audit, journal_mesures, revue)
    return rap, corr, adds


def audit_bordures(S):
    """P6 : contrôle de l'orientation des bordures v2 par les voies OpenDRIVE (driving / bus) : une voie du
    côté haut est une incohérence (journalisée, jamais corrigée ici)."""
    from commun import normale_gauche, point_a
    out = []
    for kb in S.c.bordures:
        s = np.linspace(0.2, max(kb["L"] - 0.2, 0.2), max(2, int(kb["L"] / 1.0)))
        q, tg = point_a(kb["P"], s)
        nv = normale_gauche(tg)
        haut, bas = 0, 0
        for x in q + nv * 0.6:
            vs = [v for v in S.c.voies(x, types=("driving", "bus"), rayon=0.0) if v["dedans"] and not v["jonction"]]
            haut += bool(vs)
        for x in q - nv * 0.6:
            vs = [v for v in S.c.voies(x, types=("driving", "bus"), rayon=0.0) if v["dedans"] and not v["jonction"]]
            bas += bool(vs)
        n = len(q)
        if haut / n >= 0.5 and haut > bas:
            out.append(dict(bordure=kb["id"], part_voie_cote_haut=round(haut / n, 2), part_voie_cote_bas=round(bas / n, 2),
                            orientation=kb.get("orientation"), conf=kb.get("orientation_conf")))
    return dict(n_bordures=len(S.c.bordures), n_orientation_forte=sum(1 for k in S.c.bordures if k.get("orientation_forte")),
                incoherences=out)


def coupes_cheminement(S, arbit, pas=1.0):
    """Largeur libre du cheminement piéton (PMR-01) tous les `pas` m le long des bordures dont le côté bas
    est circulé et le côté haut piéton ; carte/cheminement_coupes.geojson."""
    from coherence_carte import PIETONNES
    from commun import normale_gauche, point_a
    P = np.array([a["p"] for k, a in sorted(arbit.items()) if a.get("instancier", True)])
    ids = [k for k, a in sorted(arbit.items()) if a.get("instancier", True)]
    R = np.array([S.par_id[k]["rayon"] for k in ids])
    feats, n_etroit, n_obj, n_etroit_trottoir = [], 0, 0, 0
    for k, kb in enumerate(S.c.bordures):
        if not kb["circulee_bas"] or kb["classe_haut"] not in PIETONNES:
            continue
        for s0 in np.arange(pas / 2, kb["L"], pas):
            t, m, fin = S.c.coupe_pietonne(k, s0)
            if not m.any():
                continue
            q0, tg = point_a(kb["P"], [s0])
            n = normale_gauche(tg)[0]
            d = P - q0[0]
            lat = np.abs(d @ tg[0])
            tt = d @ n
            sel = (lat <= R + 0.25) & (tt > -0.5) & (tt < t[m].max() + 0.5)
            obs = [(float(tt[i]), float(R[i])) for i in np.nonzero(sel)[0]]
            sans = S.c.largeur_libre(t, m, [])
            avec = S.c.largeur_libre(t, m, obs)
            seuil = 1.40 if fin in ("batiment", "cloture") else 1.20
            if avec < seuil:
                n_etroit += 1
                if fin != "chaussee":
                    n_etroit_trottoir += 1
            if avec < sans - 0.01:
                n_obj += 1
            tm = t[m]
            a_, b_ = q0[0] + n * tm.min(), q0[0] + n * tm.max()
            feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords_geojson(
                repere(np.vstack([a_, b_]), "l93"))}, "properties": dict(
                id=f"{kb['id']}-s{s0:06.1f}", bordure=kb["id"], s_m=round(float(s0), 2), largeur_m=round(sans, 2),
                libre_m=round(avec, 2), seuil_m=seuil, limite=fin, conforme=bool(avec >= seuil),
                objets=[ids[i] for i in np.nonzero(sel)[0]])})
    ecrire_geojson(CARTE / "cheminement_coupes.geojson", feats, "cheminement_coupes",
                   {"regle": "PMR-01 : 1,40 m (1,20 m sans obstacle latéral)", "pas_m": pas})
    return dict(coupes=len(feats), sous_seuil=n_etroit, sous_seuil_hors_ilots=n_etroit_trottoir, reduites_par_objet=n_obj)


def apercu_corrections(S, rap, adds, emprise=(-60.0, -60.0, 70.0, 70.0)):
    """carte/apercu_corrections.png : carte sémantique du cœur avec déplacements (flèche source -> résolue),
    réorientations, objets non instanciés (croix), anomalies (losange), propositions (cercle vert)."""
    from PIL import Image, ImageDraw
    from coherence_preuves import POLICE_P
    chemin = CARTE / "apercu_corrections.png"
    S.c.apercu(chemin, emprise)
    im = Image.open(chemin).convert("RGB")
    x0, y0, x1, y1 = emprise
    k = 2
    im = im.resize((im.size[0] // k, im.size[1] // k))
    pas = 0.05 * k
    to = lambda p: ((p[0] - x0) / pas, (y1 - p[1]) / pas)
    dr = ImageDraw.Draw(im)
    for r in rap:
        c = r.get("correction")
        if not c or r["type"] == "arbre" and r["statut_resolution"] == "conforme":
            continue
        a, b = c["p_source_local"], c["p_resolu_local"]
        if not (x0 <= a[0] <= x1 and y0 <= a[1] <= y1):
            continue
        ua, va = to(a)
        ub, vb = to(b)
        if not r.get("instancier", True):
            dr.line([(ua - 6, va - 6), (ua + 6, va + 6)], fill=(255, 0, 0), width=3)
            dr.line([(ua - 6, va + 6), (ua + 6, va - 6)], fill=(255, 0, 0), width=3)
            dr.text((ua + 7, va - 7), r["id"], fill=(255, 0, 0), font=POLICE_P)
        elif r["statut_resolution"] == "anomalie_surface":
            dr.polygon([(ua, va - 7), (ua + 7, va), (ua, va + 7), (ua - 7, va)], outline=(255, 128, 0))
            dr.text((ua + 8, va - 7), r["id"], fill=(255, 128, 0), font=POLICE_P)
        elif c["d_m"] > 0.005:
            dr.line([(ua, va), (ub, vb)], fill=(255, 0, 255), width=3)
            dr.ellipse([ub - 4, vb - 4, ub + 4, vb + 4], outline=(0, 230, 255), width=2)
            dr.text((ub + 6, vb - 7), f"{r['id']} {c['d_m']:.2f} m", fill=(0, 230, 255), font=POLICE_P)
        if c.get("orientation") == "reoriente" and c.get("azimut_resolu_deg") is not None:
            for az, col in ((c.get("azimut_source_deg"), (255, 0, 255)), (c["azimut_resolu_deg"], (0, 230, 255))):
                if az is None:
                    continue
                t = math.radians(az)
                dr.line([(ub, vb), (ub + 14 * math.sin(t), vb - 14 * math.cos(t))], fill=col, width=2)
    for f in adds:
        p = f["properties"]
        q = p["p_local"]
        if not (x0 <= q[0] <= x1 and y0 <= q[1] <= y1):
            continue
        u, v = to(q)
        dr.ellipse([u - 6, v - 6, u + 6, v + 6], outline=(0, 200, 0), width=2)
        dr.text((u + 7, v + 2), p["id"], fill=(0, 160, 0), font=POLICE_P)
    dr.rectangle([0, 0, im.size[0], 16], fill=(0, 0, 0))
    dr.text((4, 1), "Solveur de cohérence v2 (cœur, 130 m) : magenta -> cyan = déplacement depuis la position source ; croix = non instancié ; "
                    "losange = anomalie de surface ; cercle vert = proposition", fill=(255, 255, 255), font=POLICE_P)
    im.save(chemin)
    return chemin


def _croise(rap, cle_a, cle_b):
    out = collections.defaultdict(collections.Counter)
    for r in rap:
        a = cle_a(r) if callable(cle_a) else r.get(cle_a)
        out[a][r.get(cle_b)] += 1
    return out


def importance(f):
    """Rang des décisions : type d'objet × (déplacement + réorientation / 30° + retrait), majoré si la
    décision est prouvée (revue confirmée avec porte complète, mesure), minoré si elle est a priori."""
    p = f["properties"]
    g = POIDS_TYPE.get(p["type"], 1.0)
    prouve = p.get("revue") in ("corrigee", "spec", "triangulee", "origine", "azimut corrigee", "azimut origine") or p.get("mesure")
    rev = 2.0 if prouve else (0.6 if p.get("conf") == "faible" else 1.0)
    retrait = 2.0 if p["nature"] == "non_instanciation" else 0.0
    return round(g * rev * ((p.get("d_m") or 0.0) + (p.get("delta_azimut_deg") or 0.0) / 30.0 + retrait), 3)


def _fmt_porte(g):
    if not g:
        return "-"
    if not g["n_photos"]:
        return "aucune photo calée valide (preuve ortho ou règle)"
    return (f"{g['verdict']} ({g['n_discriminantes']}/{g['n_photos']} photos > 3σ, {g['angle_intersection_max_deg']}°, "
            f"validé {g['composante_validee_m']:+.2f} m)")


def ecrire_rapport_md(rap, corr, adds, comptes, tetes_res, conflits, preuves, ombres, marquages, audit, journal_mesures, revue=None):
    L = []
    w = L.append
    w("# Solveur de cohérence v2 : « l'objet devait-il être ici, ou plutôt là ? »\n")
    w("Couche séparée, à fusionner par le composeur. Ni le paquet v1 ni la description de base v2 ne sont modifiés.")
    w("Commande : `python recon/pcg/decrire/coherence.py` (déterministe ; `--sans-planches` pour l'évaluation seule). "
      "Les planches `planches/*.jpg` contiennent des photos de tiers : locales, ignorées par git.\n")
    w("## Ce qui change par rapport à la v1 (revue adverse P1 à P10)\n")
    pc = comptes.get("photos_calees") or []
    n_ph = sum(x["n"] for x in pc)
    n_dec = sum(x["n"] for x in pc if x["decisive"])
    liste_ph = ", ".join(f"{x['plateforme']} {x['statut_pose']} {x['n']}" + (" décisives" if x["decisive"] else "") for x in pc)
    w(f"- **P1, photos** : {n_ph} poses calées utilisées ({liste_ph}), "
      f"dont {n_dec} décisives (LOO ≤ 0,5°). L'a priori de séquence est impossible pour 2025-08-31, 2025-01-12 et 2024-05-01 "
      "(aucune photo acceptée dans ces séries) : ces photos servent aux tests ordinaux de la revue (nombre de mâts, plaques, "
      "présence à une date), photo citée.")
    w(f"- **P2, géométrie** : chaque planche affiche, photo par photo, la séparation A↔C rapportée au σ de la pose, et la porte "
      f"de chaque paire (complète / latérale / non observable). Corrections par porte : {comptes.get('portes')}.")
    w(f"- **P3, mesures** : {comptes.get('mesures_appliquees')} objets reçoivent une mesure comme nouvel a priori (revue, fusion 0.3 "
      "« appliquer », triangulations fiables, ombres concordantes) avant la résolution.")
    w("- **P4, orientation** : azimut par raccourci des plaques sur ≥ 2 vues (w/h mesuré / w/h de face), plaques du mât "
      "identifiées avant tout transfert.")
    w("- **P5, fusions** : candidats exclus à moins de r1 + r2 + 0,10 m d'un objet de preuve au moins aussi bonne ; fusion seulement "
      f"si « même support » ou photo à un seul mât. Propositions : {comptes.get('propositions')}.")
    w(f"- **P6, bordures** : {audit['n_bordures']} bordures de la description régularisée (site complet), {audit['n_orientation_forte']} "
      f"d'orientation forte ; incohérences voie/côté haut restantes : {len(audit['incoherences'])}"
      + (f" ({', '.join(x['bordure'] for x in audit['incoherences'][:12])})" if audit["incoherences"] else "") + ".")
    w(f"- **P7, dureté** : pour un objet existant, seules les violations physiques (chaussée, voies, passages, îlot peint, bâti) "
      f"sont dures. Statuts d'objets : {comptes.get('par_statut_objet')}. Règles dures violées : {comptes.get('violations_dures_par_regle')}. "
      f"Règles signalées sans déplacement (objets existants) : {comptes.get('violations_molles_signalees')}.")
    w("- **P8, GEN-02** : supports de feux piétons et boutons d'appel admis à la limite arrière de la BEV dans le prolongement du "
      "passage (CEREMA fiche BEV 03) ; palier de 0,80 m majeur, dessiné seulement si le trottoir le permet (ARR2007 art. 1er 4°).")
    w(f"- **P9, budget** : déplacement compté depuis la position source brute (nœud OSM brut) ; dépassements : "
      f"{comptes.get('budget_depasse') or 'aucun'}.")
    if ombres:
        for k, v in ombres["par_ortho"].items():
            so, va = v.get("soleil") or {}, v.get("validation") or {}
            w(f"- **P10, ombres ({v.get('libelle', k)})** : ombres à {so.get('az_ombre_grille')}° (grille), soleil à {so.get('elevation_deg')}° "
              f"vers {so.get('heure_utc')} UTC, calé sur {so.get('n_refs')} mâts triangulés ; validation : {va.get('n')} détections "
              f"acceptées sur {va.get('n_essais')} essais ({va.get('n_objets')} mâts), biais le long de l'ombre {va.get('biais_long_m')} m, "
              f"σ long {va.get('sigma_long_m')} m, σ travers {va.get('sigma_travers_m')} m, p90 {va.get('p90_m')} m -> σ retenus "
              f"{v.get('sigma_preuve_m')} ; une détection seule est un indice, probante si les deux orthos concordent.")
    w("")
    w("## Comptes\n")
    w("| verdict | objets |\n|---|---|")
    for k, v in comptes["par_verdict"].items():
        w(f"| {k} | {v} |")
    w("\n| statut de résolution | objets |\n|---|---|")
    for k, v in comptes["par_statut"].items():
        w(f"| {k} | {v} |")
    w("\n| type | conforme | a_verifier | violation |\n|---|---|---|---|")
    for k, v in comptes["par_type_verdict"].items():
        w(f"| {k} | {v.get('conforme', 0)} | {v.get('a_verifier', 0)} | {v.get('violation', 0)} |")
    w(f"\nTêtes de feux : {comptes['tetes']}. Corrections : {comptes['corrections']} (confiance : {comptes['corrections_conf']}). "
      f"Propositions : {comptes['propositions']}.")
    if comptes["non_instancies"]:
        w(f"Objets non instanciés : {', '.join(comptes['non_instancies'])}.")
    w("\nViolations par règle (dures et signalées) : " + ", ".join(f"{k} {v}" for k, v in comptes["violations_par_regle"].items()) + ".\n")
    # ---- 20 décisions
    w("## Les 20 décisions les plus significatives\n")
    w("| # | objet | décision | preuve | revue | porte P2 | planche |\n|---|---|---|---|---|---|---|")
    vus, top = set(), []
    for f in sorted([f for f in corr if f["properties"]["couche"] != "instances"], key=lambda f: (-importance(f), f["properties"]["id"])):
        if f["properties"]["groupe"] in vus:
            continue
        vus.add(f["properties"]["groupe"])
        top.append(f)
        if len(top) == 20:
            break
    membres = collections.defaultdict(list)
    for f in corr:
        membres[f["properties"]["groupe"]].append(f["properties"]["id"])
    prep = {r["id"]: r for r in rap}
    for i, f in enumerate(top, 1):
        p = f["properties"]
        c = []
        if p.get("d_m"):
            c.append(f"{p['d_m']:.2f} m" + ("" if p.get("dt_m") is None else f" (Δt {p['dt_m']}, Δs {p['ds_m']})"))
        if p.get("delta_azimut_deg"):
            c.append(f"azimut {p['azimut_source_deg']} → {p['azimut_resolu_deg']}°")
        if p["nature"] == "non_instanciation":
            c.append("non instancié (" + ", ".join(p.get("drapeaux") or []) + ")")
        autres = [m for m in membres[p["groupe"]] if m != p["id"]]
        nom = f"`{p['id']}` ({p['type']}{' ' + p['code'] if p.get('code') else ''})" + (f" + {', '.join(autres)}" if autres else "")
        g = ((prep.get(p["id"]) or {}).get("correction") or {}).get("portes_geometriques") or {}
        w(f"| {i} | {nom} | {' ; '.join(c)} — {p['statut_resolution']} | {p['preuve']} σ {p['sigma_m']}"
          + (f" ; mesure {p['mesure']}" if p.get("mesure") else "") + f" | {p.get('revue') or '-'} ({p.get('conf')}) | "
          f"{_fmt_porte(g.get('C')) if (p.get('d_m') or 0) >= 0.3 else '-'} | `{p.get('planche') or '-'}` |")
    w("\nJustifications :\n")
    for i, f in enumerate(top, 1):
        w(f"{i}. `{f['properties']['id']}` : {f['properties']['justification']}")
    # ---- tests ordinaux et raccourcis (P1, P4)
    tests = [(oid, t) for oid, rv in sorted((revue or {}).items()) for t in rv.get("tests_ordinaux") or []]
    if tests:
        w("\n## Tests ordinaux sur photos non calées ou orthos (P1)\n")
        vus_t = set()
        for oid, t in tests:
            cle = (t.get("test"), str(t.get("valeur")), tuple(t.get("photos") or []))
            if cle in vus_t:
                continue
            vus_t.add(cle)
            w(f"- {t.get('test')} = {t.get('valeur')} — objets {', '.join(t.get('objets') or [oid])} — photos "
              f"{', '.join(t.get('photos') or [])} ({t.get('date', '')}) : {t.get('note', '')}")
    rac = [(oid, rv) for oid, rv in sorted((revue or {}).items()) if rv.get("raccourci")]
    for oid, rv in rac:
        r = next((x for x in rap if x["id"] == oid), None)
        sol = ((r or {}).get("correction") or {}).get("raccourci") or {}
        w(f"\n**Raccourci des plaques (P4), `{oid}`** : " + " ; ".join(
            f"{v['photo']} relèvement {v['releve_deg']}°, w/h {v['rapport_wh']} / {v['rapport_face']} ({v['cote']}, {v.get('plaque', '')})"
            for v in rv["raccourci"]["vues"]) + f" -> {sol.get('raison', '-')}.")
    # ---- mesures
    if journal_mesures:
        w(f"\n## Mesures appliquées comme a priori (P3, {len(journal_mesures)})\n")
        for j in sorted(journal_mesures, key=lambda j: (-j["d_m"], j["objet"]))[:40]:
            w(f"- `{j['objet']}` : {j['d_m']:.2f} m de la position source, σ {j['sigma_m']} m ({', '.join(j['sources'])})")
    # ---- marquages
    if marquages:
        w("\n## Marquages : flèches centrées dans leur voie, marques dans la chaussée\n")
        w(f"Comptes : {marquages['comptes']}. Détail : `marquages_controle.json` ; propositions : `corrections_marquages.geojson`.\n")
        w("| flèche | gabarit | état / source | bords de voie | décalage obs. / attendu | écart | statut |\n|---|---|---|---|---|---|---|")
        for r in marquages["fleches"]:
            w(f"| `{r['id']}` | {r.get('gabarit')} | {r.get('etat')} / {r.get('source')} | {(r.get('bords') or '-').replace(' | ', ' ; ')} | "
              f"{r.get('decalage_origine_m')} / {r.get('decalage_attendu_m')} | {r.get('ecart_m')} | {r['statut']} |")
        mh = [r for r in marquages["marques"] if r["statut"] != "exception"]
        w(f"\nMarques hors chaussée (hors exceptions : lignes jaunes, figurines, passages coupant un refuge) : {len(mh)}.\n")
        for r in mh[:40]:
            w(f"- `{r['id']}` ({r['classe']} {r['type']}, {r.get('source')}, {r.get('etat')}) : {r['part_hors_chaussee'] * 100:.0f} % "
              f"hors chaussée, débord max {r['debord_max_m']} m -> {r['statut']}"
              + (f" ({r.get('note')})" if r.get("note") else ""))
    # ---- têtes
    tr = [t for t in tetes_res if t["statut"] in ("reoriente", "orientation_signalee")]
    w(f"\n## Têtes de feux ({len(tr)} réorientées ou signalées sur {len(tetes_res)})\n")
    w("| tête | support | azimut | règle | motif | statut |\n|---|---|---|---|---|---|")
    for t in tr:
        w(f"| `{t['id']}` ({t['type_tete']}) | `{t['support']}` | {t['azimut_source']} → {t['azimut_resolu']}° (cible {t['cible']}°, "
          f"écart {t['ecart_deg']}°) | {t['regle']} | {t['motif']} | {t['statut']} |")
    pmr = [r for r in rap if any(v["regle"] == "PMR-01" and v["nature"] != "info" for v in r.get("violations", []))]
    ch = comptes.get("cheminement") or {}
    w(f"\n## Cheminement piéton (PMR-01, {len(pmr)} objets)\n")
    w(f"Coupes tous les 1 m derrière les bordures à côté bas circulé (`carte/cheminement_coupes.geojson`, classes des surfaces v2 "
      f"du site complet) : {ch.get('coupes')} coupes, {ch.get('sous_seuil')} sous le seuil, dont {ch.get('sous_seuil_hors_ilots')} hors "
      f"îlots et terre-pleins (coupe qui ne finit pas sur une autre chaussée) et {ch.get('reduites_par_objet')} réduites par un objet "
      "(positions résolues). La v1 (classes raster) en comptait 71 sur 1005 : les surfaces v2 bornent le cheminement aux bandes "
      "vertes et comptent les îlots ; seule la réduction due à un objet déclenche PMR-01.\n")
    an = [r for r in rap if r.get("statut_resolution") == "anomalie_surface"]
    w(f"\n## Anomalies de surface ({len(an)} objets : l'objet prouvé prime, la surface est à corriger)\n")
    for r in sorted(an, key=lambda r: r["id"])[:40]:
        cz = r["contexte"]
        rv = (r["correction"].get("revue") or {}).get("note")
        motif = ("revue : " + rv) if rv else "; ".join(r["correction"]["justification"])
        w(f"- `{r['id']}` ({r['type']}) sur {cz['zone']} (classe {cz['classe_base']}, d bordure {cz['d_bordure_m']} m), "
          f"preuve {r['preuve']['classe']} : {motif[:260]}")
    w("\n## Propositions d'ajouts et signalements\n")
    for f in adds:
        p = f["properties"]
        w(f"- `{p['id']}` ({p['type']}{' ' + p['type_tete'] if p.get('type_tete') else ''}, {p['statut']}, conf {p['conf']}) : {p['justification']}")
    cf = [c for c in conflits if c["nature"] in ("position", "orientation")]
    if cf:
        w("\n## Conflits avec feux.json / panneaux.json\n")
        for c in cf:
            w(f"- `{c['id']}` ↔ `{c['objet']}` : écart {c['d_m']} m" + (f", azimut {c['daz_deg']}°" if c.get("daz_deg") else "")
              + f" ; position de la spec {'légale' if c['spec_legale'] else 'illégale (' + ', '.join(c['violations_spec']) + ')'}")
    w("\n## Limites\n")
    w("- Aucune photo du cœur après les travaux 2025 (les 3 photos 2026 calées sont à 130 m au sud) : un objet posé ou déduit pour "
      "2026 au cœur n'est prouvable que par le terrain ; ses corrections restent à confiance faible (a_verifier_terrain2026).")
    w("- Les photos à plat du 2025-08-31 ne sont pas calables (aucune voisine acceptée) : elles ne servent qu'aux tests ordinaux.")
    w("- Détecteur d'ombres : fiable en travers de l'ombre ; le début de l'ombre est souvent masqué par l'image déversée du mât "
      "(lanterne claire) : σ le long de l'ombre ≥ 0,6 m ; erreurs grossières possibles (mât voisin), d'où la corroboration exigée.")
    w("- Les flèches levées GAM ne sont jamais déplacées : un écart à MQ-FLE-006 y signale des bords de voie à vérifier.")
    w("- P11 à P16 (rangées d'arbres, jalonnement relocalisé, masque du véhicule dans le calage, repère (s, t) hors étendue, statut "
      "temporel des arbres GAM, double lecture) ne font pas partie de ce lot ; voir open_issues.")
    (COHERENCE / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
