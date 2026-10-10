"""Sorties du solveur de cohérence : décisions finales (revue photo comprise), rapport par objet,
couche de corrections, propositions d'ajouts et REPORT.md (français).

Décision finale d'une correction (revue_coherence.json, verdicts de Claude sur les planches) :
- « corrigee » : la position / l'orientation corrigée correspond aux photos ou à l'ortho -> appliquée (conf moyenne) ;
- « origine » : les photos montrent l'objet à sa position d'origine -> gardée ; si elle viole une
  règle de surface, c'est la surface qui est fausse (anomalie_surface) ;
- « spec » / « triangulee » : la position d'une spec ou triangulée est la bonne -> appliquée ;
- « ambigu » ou pas de revue : position d'origine si elle est légale, sinon correction par la règle,
  conf faible et drapeau a_verifier_terrain2026.
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
    a_verifier : objet gardé mais signalé (anomalie de surface, règle majeure signalée, orientation contestée) ;
    conforme sinon. Une anomalie de surface n'est pas une faute de l'objet : c'est la surface qui est fausse."""
    dures = [v for v in V if v.get("dure")] if statut not in ("anomalie_surface", "conforme_signale") else []
    if dures or statut in ("corrige", "non_resolu", "a_arbitrer_photo") or (orr or {}).get("statut") == "reoriente" \
            or (dz is not None and abs(dz) > 0.10):
        return "violation"
    if statut in ("anomalie_surface", "conforme_signale") or (orr or {}).get("statut") == "orientation_signalee" \
            or any(v["nature"] not in ("info",) and v.get("gravite") in ("critique", "majeur") for v in V) \
            or (dz is not None and abs(dz) > 0.03):
        return "a_verifier"
    return "conforme"


def decider(o, a, orr, preuve, conflits_o):
    """Applique la revue photo à la correction proposée."""
    rv = (preuve or {}).get("revue") or {}
    inst = bool(a.get("instancier", True))
    p0 = o["p0"]
    p = np.asarray(a["p"], float)
    statut, conf = a["statut"], a.get("conf")
    drap = list(a.get("drapeaux", []))
    just = list(a.get("justification", []))
    az = (orr or {}).get("az", o.get("azimut0"))
    st_az = (orr or {}).get("statut")
    conf_az = (orr or {}).get("conf")
    v = rv.get("verdict")
    d = float(np.hypot(*(p - p0)))
    if v == "corrigee":
        conf = "moyenne"
        just.append(f"revue photo : position corrigée confirmée ({rv.get('note', '')})")
    elif v == "origine":
        if statut in ("non_resolu", "a_arbitrer_photo"):
            statut = "anomalie_surface" if any(x["nature"] == "surface" and x.get("dure") for x in a["_V"]) else "conforme_signale"
            inst = True
            drap = [x for x in drap if x not in ("a_verifier_terrain2026",)]
        if d > 0.005:
            p = p0.copy()
            statut = "anomalie_surface" if any(x["nature"] == "surface" and x.get("dure") for x in a["_V"]) else "conforme_signale"
            just.append(f"revue photo : l'objet est à sa position d'origine ({rv.get('note', '')}) ; correction annulée")
            drap = [x for x in drap if x != "a_verifier_terrain2026"]
        else:
            just.append(f"revue photo : position d'origine confirmée ({rv.get('note', '')})")
        conf = "moyenne"
    elif v in ("spec", "triangulee"):
        q = rv.get("position_local")
        if q is not None:
            p = np.asarray(q, float)
            statut, conf = "corrige", "moyenne"
            just.append(f"revue photo : position {v} retenue ({rv.get('note', '')})")
    elif v == "ambigu" or (preuve and not rv and statut == "corrige" and d > 0.30):
        if statut == "corrige":
            conf = "faible"
            if "a_verifier_terrain2026" not in drap:
                drap.append("a_verifier_terrain2026")
            just.append("revue photo ambiguë ou impossible : correction par la règle, confiance faible" if v == "ambigu"
                        else "pas de photo calée valide : correction par la règle, confiance faible")
    va = rv.get("verdict_azimut")
    if va == "corrigee" and st_az:
        conf_az = "moyenne"
    elif va == "origine" and st_az:
        az, st_az, conf_az = o.get("azimut0"), "orientation_photo", "moyenne"
        just.append(f"revue photo : orientation d'origine confirmée ({rv.get('note_azimut', '')})")
    elif va == "spec":
        az = rv.get("azimut", az)
        st_az, conf_az = "reoriente", "moyenne"
        just.append(f"revue photo : orientation de la spec retenue ({rv.get('note_azimut', '')})")
    elif va == "valeur":
        az = rv.get("azimut", az)
        st_az, conf_az = "reoriente", "moyenne"
        just.append(f"revue photo : orientation lue sur les photos ({rv.get('note_azimut', '')})")
    return dict(p=p, statut=statut, conf=conf, drapeaux=drap, justification=just, az=az, statut_az=st_az, conf_az=conf_az,
                revue=rv or None, instancier=inst)


def ecrire_sorties(S, objets, clotures, evals, resol, arbit, orient, nphotos, collis, conflits, tetes_res,
                   deductions, preuves, revue):
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
        dec = decider(o, a, orr, pr, conf_par.get(o["id"], []))
        ctx = ev["ctx"]
        ref = ctx["ref"]
        p = dec["p"]
        if float(np.hypot(*(p - o["p0"]))) > 0.005 and not dec["justification"]:
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
        d = float(np.hypot(*(p - o["p0"])))
        dt = ds = None
        if ref is not None and d > 0.005:
            n = np.array([-ref["tg"][1], ref["tg"][0]])
            dt, ds = float((p - o["p0"]) @ n), float((p - o["p0"]) @ ref["tg"])
        verdict = _verdict(V, statut, {"statut": dec["statut_az"]}, dz)
        lidar = bool(re.search(r"LiDAR", o["source"]))
        rec = dict(
            id=o["id"], couche=o["couche"], type=o["type"], code=o.get("code"), groupe=o["groupe"],
            membres_groupe=resol[o["id"]]["membres"], statut_2026=o["statut"], confiance_source=o.get("confiance"),
            verdict=verdict, statut_resolution=statut, instancier=bool(dec["instancier"]),
            preuve=dict(classe=o["preuve"], classe_propre=o["preuve_propre"], sigma_m=o["sigma"], deplacement_max_m=o["dmax"],
                        source=o["source"], lidar_2021=lidar,
                        photos_calees=dict(n=len(nphotos.get(o["id"], [])), ids=nphotos.get(o["id"], [])),
                        triangulation=o.get("triangulation"),
                        degradation_temporelle=resol[o["id"]].get("degradation_temporelle")),
            contexte=dict(zone=ctx["zone"], classe_base=ctx["base"], classe_faible=ctx["faible"],
                          zone_a_priori=ctx["zone_defaut"], source_classe=ctx["source_classe"],
                          arbitree_par_bordure=ctx["arbitree_bordure"],
                          bordure_reference=None if ref is None else ref["id"],
                          s_m=None if ref is None else round(ref["s"], 3), t_m=None if ref is None else round(ref["t"], 3),
                          d_bordure_m=ctx["d_bordure"],
                          voie=None if v0 is None else dict(route=v0["route"], voie=v0["voie"], type=v0["type"],
                                                           cap_deg=round(v0["cap_deg"], 1), d_m=round(v0["d"], 2)),
                          z_sol_local=round(ctx["z_sol"], 3), largeur_libre=pmr, fuseau_peint=ctx.get("fuseau")),
            regles_evaluees=ev["regs"],
            violations=[{k: (arrondi(x, 3) if k != "message" else x) for k, x in v.items()} for v in V],
            correction=dict(
                p_source_l93=l93(o["p0"]), p_resolu_l93=l93(p), p_source_local=loc(o["p0"]), p_resolu_local=loc(p),
                d_m=round(d, 3), dt_m=None if dt is None else round(dt, 3), ds_m=None if ds is None else round(ds, 3),
                azimut_source_deg=o.get("azimut0"), azimut_resolu_deg=dec["az"], azimut_cible_deg=orr.get("cible"),
                orientation=dec["statut_az"], orientation_motif=orr.get("motif"), orientation_raison=orr.get("raison"),
                z_source_local=o.get("z0"), z_resolu_local=round(z_res, 3), z_resolu_ngf=round(z_res + 216.30, 3),
                dz_source_m=None if dz is None else round(dz, 3),
                conf=dec["conf"] or dec["conf_az"], drapeaux=dec["drapeaux"], justification=dec["justification"],
                planche=(pr or {}).get("planche"), photos_planche=(pr or {}).get("photos"),
                triangulation_coherence=(pr or {}).get("triangulation"), revue=dec["revue"],
                regles_dures=resol[o["id"]].get("regles_dures"),
                prov=dict(src=("regle:implantation." + ",".join(resol[o["id"]].get("regles_dures") or [])) if d > 0.005 else o["preuve"],
                          ref=f"déplacement {d:.2f} m ; preuve initiale {o['preuve']}", conf=dec["conf"] or "haute")),
            conflits_specs=[c["id"] for c in conf_par.get(o["id"], [])],
        )
        rap.append(rec)
        moved = d > 0.005
        reor = dec["statut_az"] == "reoriente" and o.get("azimut0") != dec["az"]
        retire = not rec["instancier"]
        if retire and not moved:
            corr.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": l93(o["p0"])}, "properties": dict(
                id=o["id"], couche=o["couche"], type=o["type"], code=o.get("code"), groupe=o["groupe"],
                nature="non_instanciation", statut_resolution=statut, verdict=verdict, d_m=0.0, dt_m=None, ds_m=None,
                azimut_source_deg=o.get("azimut0"), azimut_resolu_deg=dec["az"], delta_azimut_deg=None,
                regles=sorted({v["regle"] for v in V if v.get("dure")}), conf=dec["conf"] or "faible",
                drapeaux=dec["drapeaux"], instancier=False, justification=" ; ".join(dec["justification"]),
                preuve=o["preuve"], sigma_m=o["sigma"], planche=rec["correction"]["planche"],
                revue=(dec["revue"] or {}).get("verdict"), p_source_local=loc(o["p0"]), p_resolu_local=loc(o["p0"]),
                z_resolu_ngf=rec["correction"]["z_resolu_ngf"])})
        if moved or reor:
            daz = None if (o.get("azimut0") is None or dec["az"] is None) else round(ecart_angle(o["azimut0"], dec["az"]), 1)
            geom = {"type": "LineString", "coordinates": coords_geojson([l93(o["p0"]), l93(p)])} if moved else \
                {"type": "Point", "coordinates": l93(p)}
            corr.append({"type": "Feature", "geometry": geom, "properties": dict(
                id=o["id"], couche=o["couche"], type=o["type"], code=o.get("code"), groupe=o["groupe"],
                nature=("deplacement" if moved else "") + ("+" if moved and reor else "") + ("reorientation" if reor else ""),
                statut_resolution=statut, verdict=verdict, d_m=round(d, 3), dt_m=rec["correction"]["dt_m"],
                ds_m=rec["correction"]["ds_m"], azimut_source_deg=o.get("azimut0"), azimut_resolu_deg=dec["az"],
                delta_azimut_deg=daz, regles=sorted({v["regle"] for v in V if v.get("dure")}
                                                    | ({REGLE_ORIENT.get(o["type"], "SIG-04")} if reor else set())),
                conf=dec["conf"] or dec["conf_az"], drapeaux=dec["drapeaux"], instancier=rec["instancier"],
                justification=" ; ".join(dec["justification"] + ([orr.get("raison")] if reor and orr.get("raison") else [])),
                preuve=o["preuve"], sigma_m=o["sigma"], planche=rec["correction"]["planche"],
                revue=(dec["revue"] or {}).get("verdict"),
                p_source_local=loc(o["p0"]), p_resolu_local=loc(p), z_resolu_ngf=rec["correction"]["z_resolu_ngf"]),
            })
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
                                                verdict=t["verdict"], d_m=0.0, azimut_source_deg=t["azimut_source"],
                                                azimut_resolu_deg=az, delta_azimut_deg=t["ecart_deg"], regles=[t["regle"]],
                                                conf="moyenne" if t["azimut_source"] % 45 == 0 else "faible",
                                                drapeaux=[], instancier=True,
                                                justification=f"{t['motif']} : azimut {t['azimut_source']}° -> {az}° "
                                                              f"({'grossier, multiple de 45°' if t['azimut_source'] % 45 == 0 else 'preuve faible'})",
                                                preuve=sup["preuve"], sigma_m=sup["sigma"], planche=None, revue=rv.get("verdict_azimut"),
                                                p_source_local=loc(sup["p0"]), p_resolu_local=loc(arbit[sup["id"]]["p"]))})
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
    entete = {"schema": "pj_coherence/0.1", "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98)",
              "role": "couche de corrections séparée, à fusionner par le composeur (ne modifie ni le paquet ni la description de base)"}
    ecrire_geojson(COHERENCE / "corrections.geojson", corr, "corrections", entete)
    ecrire_geojson(COHERENCE / "propositions_ajouts.geojson", adds, "propositions_ajouts", entete)
    # comptes
    comptes = dict(
        par_verdict=dict(collections.Counter(r["verdict"] for r in rap)),
        par_statut=dict(collections.Counter(r["statut_resolution"] for r in rap)),
        par_type_verdict={k: dict(v) for k, v in sorted(_croise(rap, "type", "verdict").items())},
        par_couche_verdict={k: dict(v) for k, v in sorted(_croise(rap, "couche", "verdict").items())},
        par_zone_verdict={k: dict(v) for k, v in sorted(_croise(rap, lambda r: (r.get("contexte") or {}).get("zone") or "-", "verdict").items())},
        violations_par_regle=dict(sorted(collections.Counter(v["regle"] for r in rap for v in r["violations"]
                                                            if v.get("nature") not in ("info",)).items())),
        tetes=dict(collections.Counter(t["statut"] for t in tetes_res)),
        corrections=dict(collections.Counter(f["properties"]["nature"] for f in corr)),
        propositions=dict(collections.Counter(f["properties"]["type"] for f in adds)),
        non_instancies=sorted(r["id"] for r in rap if not r.get("instancier", True) and r["statut_resolution"] != "non_instancie_absent_2026"),
    )
    # largeur libre le long des trottoirs, avec les positions finales (revue comprise)
    comptes["cheminement"] = coupes_cheminement(S, {r["id"]: dict(p=np.asarray(r["correction"]["p_resolu_local"], float),
                                                                  instancier=r["instancier"])
                                                    for r in rap if r.get("correction")})
    sources = {k: dict(chemin=v.relative_to(RACINE).as_posix(), sha256=sha256(v)) for k, v in {
        "mobilier": DONNEES / "objets/mobilier.geojson", "arbres": DONNEES / "objets/arbres.geojson",
        "instances": DONNEES / "objets/instances.json", "surfaces_2026": DONNEES / "surfaces/surfaces_2026.geojson",
        "lanes_2026": DONNEES / "opendrive/lanes_2026.geojson", "regles": REGLES, "feux": SPECS / "feux.json",
        "panneaux": SPECS / "panneaux.json",
        "poses": RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json"}.items()}
    ecrire_json(COHERENCE / "rapport_coherence.json", arrondi(dict(
        schema="pj_coherence/0.1", site="paquet_jardin", etat="octobre 2026",
        repere="local = L93 - (917279.43, 6460289.98), z = NGF - 216.30",
        methode="voir recon/pcg/decrire/coherence.py et REPORT.md", sources=sources,
        carte=dict(dossier=CARTE.relative_to(RACINE).as_posix(), bordures=len(S.c.bordures), voies=len(S.c.lanes),
                   passages=len(S.c.passages)),
        comptes=comptes, objets=rap, clotures=[dict(id=c["id"], statut_resolution="conforme", verdict="conforme",
                                                     regle="BAR-02", note="limite dure, jamais déplacée") for c in clotures],
        tetes=tetes_res, conflits_specs=[{k: (loc(v) if k == "p_spec" else v) for k, v in c.items()} for c in conflits],
        doublons_collisions=collis, propositions=[f["properties"] for f in adds]), 3))
    apercu_corrections(S, rap, adds)
    ecrire_rapport_md(rap, corr, adds, comptes, tetes_res, conflits, preuves)
    return rap, corr, adds


def coupes_cheminement(S, arbit, pas=1.0):
    """Largeur libre du cheminement piéton (PMR-01) tous les `pas` m le long des bordures dont le côté bas
    est circulé et le côté haut piéton : coupe perpendiculaire, largeur du trottoir et largeur libre
    entre les emprises des objets (positions résolues) ; carte/cheminement_coupes.geojson."""
    from coherence_carte import PIETONNES
    from commun import normale_gauche, point_a
    P = np.array([a["p"] for k, a in sorted(arbit.items()) if a.get("instancier", True)])
    ids = [k for k, a in sorted(arbit.items()) if a.get("instancier", True)]
    R = np.array([S.par_id[k]["rayon"] for k in ids])
    feats, n_etroit, n_obj = [], 0, 0
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
    return dict(coupes=len(feats), sous_seuil=n_etroit, reduites_par_objet=n_obj)


def apercu_corrections(S, rap, adds, emprise=(-60.0, -60.0, 70.0, 70.0)):
    """carte/apercu_corrections.png : carte sémantique du cœur avec déplacements (flèche A -> C),
    réorientations (trait de face), objets non instanciés (croix), anomalies de surface (losange),
    propositions d'ajouts (cercle vert)."""
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
            import math
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
    dr.text((4, 1), "Corrections du solveur de cohérence (cœur, 130 m) : magenta -> cyan = déplacement ; croix rouge = non instancié ; "
                    "losange orange = anomalie de surface ; cercle vert = proposition", fill=(255, 255, 255), font=POLICE_P)
    im.save(chemin)
    return chemin


def _croise(rap, cle_a, cle_b):
    out = collections.defaultdict(collections.Counter)
    for r in rap:
        a = cle_a(r) if callable(cle_a) else r.get(cle_a)
        out[a][r.get(cle_b)] += 1
    return out


def importance(f):
    """Rang des corrections : type d'objet × (déplacement + réorientation / 30° + retrait), bonus si la
    revue photo a confirmé la correction, malus si elle est seulement a priori."""
    p = f["properties"]
    g = POIDS_TYPE.get(p["type"], 1.0)
    rev = 2.0 if p.get("revue") in ("corrigee", "spec", "triangulee") else (0.6 if p.get("conf") == "faible" else 1.0)
    retrait = 2.0 if p["nature"] == "non_instanciation" else 0.0
    return round(g * rev * ((p.get("d_m") or 0.0) + (p.get("delta_azimut_deg") or 0.0) / 30.0 + retrait), 3)


def ecrire_rapport_md(rap, corr, adds, comptes, tetes_res, conflits, preuves):
    L = []
    w = L.append
    w("# Solveur de cohérence des objets : « l'objet devait-il être ici, ou plutôt là ? »\n")
    w("Couche séparée, à fusionner par le composeur. Ni le paquet v1 ni la description de base v2 ne sont modifiés.")
    w("Commande : `python recon/pcg/decrire/coherence.py` (déterministe ; `--sans-planches` pour l'évaluation seule).\n")
    w("## Méthode\n")
    w("1. **Carte sémantique du site** (raster 5 cm, `carte/`) : classes îlots v2 > surfaces v2 > bâtiments > surfaces_2026 ; "
      "zones dérivées (passages, traversées cyclables, îlots peints, voies bus et bandes cyclables, abaissés, paliers, BEV, clôtures) "
      "selon `precedence_zones` ; bordures orientées sur tout le site (v2 en zone pilote, GAM/PCRS/plan 2025 dédoublonnées ailleurs) ; "
      "voies OpenDRIVE et sens ; largeur libre par coupe perpendiculaire à la bordure. Près d'une bordure (|t| < 1 m), la "
      "classe est arbitrée par la bordure levée (côté haut / côté chaussée).")
    w("2. **Règles** (`assets/specs/regles_implantation.json`, 66 règles) : surfaces, reculs, relations (ligne d'effet, extrémités "
      "de passage, nez d'îlot, fuseau peint), orientation (usagers visés, chaussée éclairée, extrémité opposée du passage), z, "
      "cheminement de 1,40 m, collisions et doublons. Politique : critique toujours dure ; majeur dure si σ ≥ 0,5 m ; une règle "
      "« vérifier » contraint un objet a priori ; une borne a priori ou une zone dérivée a priori ne s'oppose pas à un objet bien prouvé.")
    w("3. **Résolution** : normale à la bordure en s0 puis grille (Δs, Δt), coût J = (Δt/σ)² + 4(Δs/σ)² + termes mous, sans "
      "dépasser le déplacement autorisé par la preuve (GAM 0,5 m ; LiDAR 0,75 ; ortho 1,0 ; OSM 2,0 ; a priori 5,0). Sinon arbitrage : "
      "anomalie de surface (objet bien prouvé, la surface est fausse), photo, candidat a priori (conf faible), non-instanciation.")
    w("4. **Preuves** : planche Panoramax (poses calées, photos valides à la date de l'objet) + ortho 2022 pour chaque correction "
      "> 0,3 m ou > 20°, lue par Claude (`revue_coherence.json`) ; triangulation des mâts en désaccord > 0,75 m.\n")
    w("Vue d'ensemble : `carte/apercu_corrections.png` (carte sémantique du cœur, déplacements, retraits, anomalies, ajouts).\n")
    w("## Comptes\n")
    w("| verdict | objets |\n|---|---|")
    for k, v in sorted(comptes["par_verdict"].items()):
        w(f"| {k} | {v} |")
    w("\n| statut de résolution | objets |\n|---|---|")
    for k, v in sorted(comptes["par_statut"].items()):
        w(f"| {k} | {v} |")
    w("\n| type | conforme | a_verifier | violation |\n|---|---|---|---|")
    for k, v in comptes["par_type_verdict"].items():
        w(f"| {k} | {v.get('conforme', 0)} | {v.get('a_verifier', 0)} | {v.get('violation', 0)} |")
    w("\n| zone au point | conforme | a_verifier | violation |\n|---|---|---|---|")
    for k, v in comptes["par_zone_verdict"].items():
        w(f"| {k} | {v.get('conforme', 0)} | {v.get('a_verifier', 0)} | {v.get('violation', 0)} |")
    w(f"\nTêtes de feux : {dict(comptes['tetes'])}. Corrections : {dict(comptes['corrections'])}. "
      f"Propositions d'ajouts : {dict(comptes['propositions'])}.")
    if comptes["non_instancies"]:
        w(f"Objets non instanciés (violation critique non résolue sur surface circulée) : {', '.join(comptes['non_instancies'])}.")
    w("\nViolations par règle : " + ", ".join(f"{k} {v}" for k, v in comptes["violations_par_regle"].items()) + ".\n")
    w("## Les 15 corrections les plus significatives\n")
    w("| # | objet | correction | règles | preuve | revue | planche |\n|---|---|---|---|---|---|---|")
    vus, top = set(), []
    for f in sorted([f for f in corr if f["properties"]["couche"] != "instances"], key=lambda f: (-importance(f), f["properties"]["id"])):
        if f["properties"]["groupe"] in vus:
            continue
        vus.add(f["properties"]["groupe"])
        top.append(f)
        if len(top) == 15:
            break
    membres = collections.defaultdict(list)
    for f in corr:
        membres[f["properties"]["groupe"]].append(f["properties"]["id"])
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
        w(f"| {i} | {nom} | {' ; '.join(c)} | "
          f"{', '.join(r for r in p['regles'] if r)} | {p['preuve']} σ {p['sigma_m']} | {p.get('revue') or '-'} ({p.get('conf')}) | "
          f"`{p.get('planche') or '-'}` |")
    w("\nJustifications :\n")
    for i, f in enumerate(top, 1):
        w(f"{i}. `{f['properties']['id']}` : {f['properties']['justification']}")
    tr = [t for t in tetes_res if t["statut"] in ("reoriente", "orientation_signalee")]
    w(f"\n## Têtes de feux ({len(tr)} réorientées ou signalées sur {len(tetes_res)})\n")
    w("| tête | support | azimut | règle | motif | statut |\n|---|---|---|---|---|---|")
    for t in tr:
        w(f"| `{t['id']}` ({t['type_tete']}) | `{t['support']}` | {t['azimut_source']} → {t['azimut_resolu']}° (cible {t['cible']}°, "
          f"écart {t['ecart_deg']}°) | {t['regle']} | {t['motif']} | {t['statut']} |")
    pmr = [r for r in rap if any(v["regle"] == "PMR-01" for v in r.get("violations", []))]
    ch = comptes.get("cheminement") or {}
    w(f"\n## Cheminement piéton de 1,40 m (PMR-01, {len(pmr)} objets)\n")
    w(f"Coupes tous les 1 m le long des trottoirs (`carte/cheminement_coupes.geojson`) : {ch.get('coupes')} coupes, "
      f"{ch.get('sous_seuil')} sous le seuil (1,40 m contre un mur ou une clôture, 1,20 m sinon), dont {ch.get('reduites_par_objet')} "
      "réduites par un objet (positions résolues).\n")
    for r in pmr:
        ll = (r.get("contexte") or {}).get("largeur_libre") or {}
        v = [x for x in r["violations"] if x["regle"] == "PMR-01"][0]
        w(f"- `{r['id']}` ({r['type']}) : {v['message']} ; trottoir {ll.get('largeur_trottoir')} m, objet à t = {ll.get('t_objet')} m "
          f"-> {r['statut_resolution']} (déplacement {r['correction']['d_m']} m)")
    an = [r for r in rap if r.get("statut_resolution") == "anomalie_surface"]
    w(f"\n## Anomalies de surface ({len(an)} objets : l'objet prouvé prime, la surface est à corriger)\n")
    for r in sorted(an, key=lambda r: r["id"])[:40]:
        cz = r["contexte"]
        rv = (r["correction"].get("revue") or {}).get("note")
        motif = ("revue photo : " + rv) if rv else "; ".join(r["correction"]["justification"])
        w(f"- `{r['id']}` ({r['type']}) sur {cz['zone']} (classe {cz['classe_base']}, d bordure {cz['d_bordure_m']} m), "
          f"preuve {r['preuve']['classe']} : {motif[:260]}")
    w("\n## Propositions d'ajouts\n")
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
    w("- Aucune photo du cœur après les travaux 2025 : un objet posé ou déduit pour 2026 ne peut être prouvé par photo ; ses "
      "corrections restent à confiance faible (drapeau a_verifier_terrain2026).")
    w("- 13 photos calées (2024-08 et 2025-05), toutes le long de l'avenue de Verdun : au-delà de 25-30 m de cet axe, seule l'ortho 2022 "
      "sert de preuve visuelle.")
    w("- Zones dérivées a priori (profondeur de rampe 1,20 m, BEV 0,50-0,90 m hors zone pilote) : elles ne s'opposent pas aux objets bien prouvés.")
    w("- Les classes de surface v1 d'origine raster sont peu sûres ; la bordure levée les arbitre à moins de 1 m.")
    (COHERENCE / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
