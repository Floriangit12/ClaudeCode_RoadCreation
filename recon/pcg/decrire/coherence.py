"""Solveur de cohérence des objets (mobilier, arbres, têtes de feux, hypothèses des specs).

Chaîne (déterministe) :
1. carte sémantique du site (coherence_carte) ;
2. objets, groupes rigides, preuves (coherence_objets) ;
3. évaluation des règles d'implantation et recherche du candidat admissible (coherence_regles) ;
4. arbitrage : corrigé, anomalie de surface (l'objet prouvé prime, la surface est fausse), photo,
   a priori, non-instanciation ; orientation recalculée ; z posé sur le sol 2026 ;
5. têtes de feux (FEU-03/05/06/07), déductions (R12, boutons d'appel, candélabres, îlots manquants),
   conflits avec feux.json / panneaux.json ;
6. preuves photo (coherence_preuves) : planches Panoramax + ortho des corrections > 0,3 m ou > 20°,
   lues par Claude (revue_coherence.json), triangulation des mâts en désaccord ;
7. sorties : coherence/rapport_coherence.json, corrections.geojson, propositions_ajouts.geojson, REPORT.md.

Usage (depuis la racine du dépôt) :
  python recon/pcg/decrire/coherence.py                 # tout, planches comprises
  python recon/pcg/decrire/coherence.py --sans-planches # évaluation seule
Ne modifie ni le paquet ni la description de base : couche séparée à fusionner par le composeur.
"""
import argparse
import collections
import re
import sys
import time

import numpy as np

from coherence_carte import COHERENCE, REGLES, Carte, azimut, ecart_angle
from coherence_objets import (FIN_TRAVAUX, azimut_grossier, charger, hypotheses_specs, tetes,
                              valide_pour_photo)
from coherence_regles import CIRC_BASE, Solveur
from commun import RACINE, lire_json

SCHEMA = "pj_coherence/0.1"
SEUIL_PLANCHE_M = 0.30
SEUIL_PLANCHE_DEG = 20.0
REVUE = COHERENCE / "revue_coherence.json"


# --------------------------------------------------------------------------- objets
def evaluer_groupes(S, objets):
    """Évalue chaque objet puis résout chaque groupe rigide comme un seul support."""
    groupes = collections.OrderedDict()
    for o in objets:
        if o["statut"].startswith("absent"):
            continue
        groupes.setdefault(o["groupe"], []).append(o)
    evals = {}
    for o in objets:
        if o["statut"].startswith("absent"):
            evals[o["id"]] = dict(V=[], ctx=None, regs=[])
            continue
        V, ctx, regs = S.evaluer(o)
        evals[o["id"]] = dict(V=V, ctx=ctx, regs=regs)
    resol = {}
    for g, membres in groupes.items():
        rep = sorted(membres, key=lambda o: (o["type"] == "panneau", -o["rayon"], o["id"]))[0]
        V = [v for m in membres for v in evals[m["id"]]["V"]]
        res = S.resoudre(rep, V, evals[rep["id"]]["ctx"])
        res["representant"] = rep["id"]
        res["membres"] = [m["id"] for m in membres]
        for m in membres:
            resol[m["id"]] = res
    return evals, resol


def arbitrer(S, o, ev, res, photos):
    """Statut de résolution, position et confiance finales (avant revue photo)."""
    V, ctx = ev["V"], ev["ctx"]
    par = S.par
    dures = [v for v in V if v["dure"]]
    surf = [v for v in V if v["nature"] == "surface" and v["gravite"] == "critique"]
    # σ de la preuve pour l'état 2026 : doublé si la preuve précède les travaux en zone de travaux
    sig = res["sigma_recherche"]
    fort = sig <= par["seuil_sigma_preuve_forte_m"]
    leve = sig <= 0.10                     # levé 2026 (GAM) ou équivalent : la surface v1 ne peut pas le contredire
    faible_surface = (ctx["faible"] and not ctx["arbitree_bordure"]) \
        or (ctx["zone"] in ("chaussee",) and (ctx["d_bordure"] or 99) > 2.0) \
        or any(v.get("zones_a_priori") for v in surf)
    out = dict(p=o["p0"].copy(), statut="conforme", conf=None, instancier=True, drapeaux=[], justification=[])
    if not V or all(v["nature"] in ("info",) for v in V):
        return out
    if not dures:
        if surf and o["sigma"] <= par["seuil_sigma_preuve_forte_m"]:
            out["statut"] = "anomalie_surface"
            out["justification"].append("objet bien prouvé sur une surface interdite de classe peu sûre : la surface est à corriger")
        elif any(v["nature"] not in ("z", "info", "orientation") and v["gravite"] in ("critique", "majeur") for v in V):
            out["statut"] = "conforme_signale"
        return out
    # objet prouvé seulement avant les travaux, à l'emplacement d'un marquage posé en 2025 : déposé ou déplacé
    from coherence_objets import anterieure_travaux
    if anterieure_travaux(o) and any(v["nature"] == "surface" and v["gravite"] == "critique" for v in dures):
        m25 = S.c.marquages_poses_2025(o["p0"], rayon=max(o["rayon"], 0.1) + 0.15)
        if m25:
            out["statut"], out["instancier"], out["conf"] = "non_resolu", False, "faible"
            out["drapeaux"] += ["obsolete_probable", "a_verifier_terrain2026"]
            out["justification"].append(
                f"preuve antérieure aux travaux 2025 ({o['preuve']}) ; le marquage posé en 2025 "
                f"{', '.join(m['id'] + ' (' + m['zone'] + ', ' + m['etat'] + ')' for m in m25)} passe à son emplacement "
                f"et la surface 2026 y est circulée : objet probablement déposé ou déplacé par les travaux, non instancié")
            return out
    # objet bien prouvé, seules des violations de surface sur une classe peu sûre : on garde l'objet
    if (leve or (fort and faible_surface)) and all(v["nature"] == "surface" for v in dures):
        out["statut"] = "anomalie_surface"
        cause = {"batiment": "emprise bâtie (BD TOPO / OSM) trop large ou arbre de cour",
                 "chaussee": "îlot, refuge, fosse ou bande plantée absents des surfaces",
                 "parking": "fosse ou terre-plein de parking absent des surfaces",
                 "acces_riverain": "bande plantée ou limite d'accès mal placée",
                 "piste_cyclable": "limite de piste mal placée"}.get(ctx["zone"], "limite de surface ou zone dérivée à corriger")
        out["justification"].append(f"preuve forte ({o['preuve']}, σ {o['sigma']} m) sur {ctx['zone']} de classe peu sûre "
                                    f"(d bordure {ctx['d_bordure']} m) : {cause}")
        return out
    if res.get("dans_dmax") and res.get("candidat") is not None and res.get("relaxation") \
            and float(np.hypot(*(np.asarray(res["candidat"]) - o["p0"]))) < 0.005:
        out["statut"] = "conforme_signale"
        out["justification"].append("aucune position ne satisfait les règles majeures sans quitter l'espace de l'objet : "
                                    f"{', '.join(res['relaxation'])} signalées, position gardée")
        return out
    if res.get("dans_dmax") and res.get("candidat") is not None:
        out["p"] = np.asarray(res["candidat"], float)
        out["statut"] = "corrige"
        out["conf"] = "moyenne" if o["sigma"] < 1.0 else "faible"
        out["justification"].append(f"candidat admissible le plus proche ({res['mode']}, Δt {res['dt']:+.2f} m, Δs {res['ds']:+.2f} m, "
                                    f"J {res['J']}) dans la limite de la preuve ({o['preuve']}, d_max {res['dmax']} m)")
        if res.get("relaxation"):
            out["justification"].append("aucune position ne satisfait toutes les règles : seules les règles critiques sont "
                                        f"imposées, {', '.join(res['relaxation'])} restent signalées")
        return out
    # aucun candidat dans d_max
    if fort and all(v["nature"] == "surface" for v in dures):
        out["statut"] = "anomalie_surface"
        out["justification"].append(f"preuve forte ({o['preuve']}) : aucune position admissible dans {res['dmax']} m ; la surface "
                                    f"({ctx['zone']}) est à revoir")
        return out
    circ = ctx["zone"] in CIRC_BASE or ctx["zone"] in ("passage_pietons", "traversee_cyclable", "voie_bus", "bande_cyclable")
    critique = any(v["gravite"] == "critique" for v in dures)
    if photos:
        out["statut"] = "a_arbitrer_photo"
        out["justification"].append(f"preuve faible, aucune position admissible dans {res['dmax']} m : arbitrage par {len(photos)} photo(s) calée(s)")
    elif res.get("candidat_hors_dmax") is not None:
        out["p"] = np.asarray(res["candidat_hors_dmax"], float)
        out["statut"] = "corrige"
        out["conf"] = "faible"
        out["drapeaux"].append("a_verifier_terrain2026")
        out["justification"].append(f"aucune preuve photo valide : candidat a priori à {res['d_hors']} m (au-delà de d_max), conf faible")
        return out
    else:
        out["statut"] = "non_resolu"
        out["justification"].append("aucune position admissible et aucune preuve pour trancher")
    sv = S.c.surface_v1(o["p0"])
    if sv and sv["etat"] == "modifie_2025" and anterieure_travaux(o):
        out["drapeaux"] = sorted(set(out["drapeaux"]) | {"surface_modifiee_2025", "a_verifier_terrain2026"})
        out["justification"].append(f"la surface {sv['id']} ({sv['classe']}) a été (re)construite en 2025 "
                                    f"({sv['source']}) et l'objet n'est prouvé qu'avant les travaux : objet peut-être supprimé")
    if critique and circ:
        out["instancier"] = False
        out["justification"].append("violation critique non résolue sur une surface circulée : objet non instancié (resolution.arbitrage.non_instanciation)")
    return out


ORIENTATION_PHOTO = re.compile(r"face à la caméra|de face|vue? de face|vues? depuis|dos (gris )?des? lames|"
                               r"relèvement|lisibles? de face", re.I)


def orienter(S, o, p, ctx, hyp_az):
    """Azimut final. La règle oriente un objet sans azimut ; elle affine un azimut grossier (multiple
    de 45°) ou faiblement prouvé seulement si elle reste à moins de 60° de lui ; un désaccord plus
    fort signale que la voie visée n'est pas celle du modèle (voie secondaire non décrite, carrefour) :
    l'azimut est gardé et signalé. Un azimut lu sur photo (source) n'est jamais remplacé par la règle ;
    l'azimut photo d'une spec, s'il s'accorde avec la règle (≤ 30°), remplace celui de la couche."""
    az0 = o.get("azimut0")
    cible = S.orientation_cible(o, p, ctx, az0=az0) if o["type"] in ("panneau", "lampadaire", "abri_bus", "poteau_incendie") else None
    out = dict(az=az0, statut=None, cible=None, conf=None, motif=None)
    if cible is None:
        return out
    out["cible"] = round(cible["az"], 1)
    tol = cible.get("tolerance", 15.0)
    out["motif"] = cible["motif"]
    if az0 is None:
        out.update(az=round(cible["az"], 1), statut="reoriente", conf="moyenne", raison="azimut absent : orienté par la règle")
        return out
    e = ecart_angle(az0, cible["az"])
    if cible.get("modulo_180"):
        e = min(e, 180.0 - e)
    if e <= tol:
        return out
    photo = bool(ORIENTATION_PHOTO.search(o["source"] or ""))
    if hyp_az is not None and ecart_angle(hyp_az, az0) > 5.0 and ecart_angle(hyp_az, cible["az"]) <= max(tol, 30.0):
        out.update(az=round(float(hyp_az), 1), statut="reoriente", conf="moyenne",
                   raison=f"azimut photo de la spec ({hyp_az:.0f}°) conforme à la règle ({cible['az']:.0f}°) ; couche à {az0:.0f}°")
        return out
    if photo:
        out.update(statut="orientation_signalee", raison=f"azimut lu sur photo (source) à {e:.0f}° de la règle : gardé")
        return out
    if (azimut_grossier(az0) or o["sigma"] >= S.par["seuil_sigma_normatif_m"]) and e <= 60.0:
        out.update(az=round(cible["az"], 1), statut="reoriente", conf="moyenne" if azimut_grossier(az0) else "faible",
                   raison=("azimut grossier (multiple de 45°)" if azimut_grossier(az0) else "azimut d'une preuve faible")
                   + f" à {e:.0f}° de la règle : affiné")
        return out
    out.update(statut="orientation_signalee",
               raison=f"azimut à {e:.0f}° de la règle ({cible['motif']}) : désaccord trop fort pour corriger sans photo, gardé")
    return out


# --------------------------------------------------------------------------- têtes de feux
def _visee_voie(ap, p_sup, recul, largeur_voie=3.2):
    """Point de visée sur l'axe de la voie la plus proche du support, `recul` m en amont de la ligne."""
    P = ap["P"]
    a, b = P[0], P[-1]
    proche, loin = (a, b) if np.hypot(*(a - p_sup)) <= np.hypot(*(b - p_sup)) else (b, a)
    L = float(np.hypot(*(loin - proche)))
    u = (loin - proche) / max(L, 1e-9)
    return proche + u * min(largeur_voie / 2, L / 2) - ap["h"] * recul


def _traversee_cyclable_proche(S, p, rayon=8.0):
    best = None
    for mid, zone, etat, anneau in S.c.marques:
        if zone != "traversee_cyclable":
            continue
        c = anneau.mean(axis=0)
        d = float(np.min(np.hypot(*(anneau - p).T)))
        if d <= rayon and (best is None or d < best[0]):
            best = (d, mid, c)
    return best


def evaluer_tetes(S, positions):
    """Orientation (FEU-05/06/07, R13c) et hauteurs (FEU-03, FEU-07) des têtes, au support résolu.
    Une tête d'azimut grossier (multiple de 45°), déduite ou copiée de la tête principale (répétiteur)
    est réorientée si la règle reste à moins de 60° ; au-delà, l'azimut est gardé et signalé."""
    out = []
    pieces = S.c.passages
    for t in S.tetes:
        sup = t["support"]
        p_sup = positions.get(sup["id"], sup["p0"])
        dp = p_sup - sup["p0"]
        p = t["p"] + dp
        tt = t["type_tete"]
        cible, motif, tol, regle = None, None, None, None
        ap = S._approche(sup)
        if ap is not None:
            ap = dict(ap, P=S.lignes_effet[[k for k, v in S.lignes_effet.items() if v["id"] == ap["ligne"]][0]]["P"])
        if tt == "R13c":
            tc = _traversee_cyclable_proche(S, p_sup)
            if tc is not None:
                cible, regle, tol = azimut(p - tc[2]), "FEU-09", 20.0
                motif = f"cyclistes en attente avant la traversée {tc[1]}"
        elif tt in ("R11v", "R11v_rep", "M12", "AB3a") and ap is not None:
            if tt == "R11v_rep":
                U = _visee_voie(ap, p_sup, S.regles["FEU-06"]["parametres"]["visee_amont_ligne_m"])
                regle, tol = "FEU-06", 10.0
                motif = f"premier véhicule arrêté à la ligne {ap['ligne']} (axe de la voie la plus proche)"
            else:
                U = _visee_voie(ap, p_sup, S.regles["FEU-05"]["parametres"]["distance_visee_amont_m"])
                regle, tol = ("FEU-05" if tt == "R11v" else "SIG-08"), 10.0
                motif = f"voie gérée à 40 m en amont de la ligne {ap['ligne']}"
            cible = azimut(U - p)
        elif tt == "R12":
            cands = []
            for q in pieces:
                for E2, F2 in ((q["a"], q["b"]), (q["b"], q["a"])):
                    if float(np.hypot(*(E2 - p_sup))) <= 4.5:
                        cands.append((ecart_angle(t["azimut0"], azimut(F2 - p)), q, F2))
            if cands:
                cands.sort(key=lambda c: (round(c[0], 3), c[1]["id"]))
                _, pp, F = cands[0]
                cible, regle, tol = azimut(F - p), "FEU-07", 15.0
                motif = f"extrémité opposée du passage {pp['id']}"
        e = None if cible is None else ecart_angle(t["azimut0"], cible)
        statut, az = "conforme", t["azimut0"]
        principal = [x for x in S.tetes_de.get(sup["id"], []) if x["type_tete"] == "R11v"]
        copie = tt == "R11v_rep" and principal and abs(principal[0]["azimut0"] - t["azimut0"]) < 0.5
        if cible is not None and e > tol:
            souple = azimut_grossier(t["azimut0"]) or t["statut"].startswith("déduit") or copie or sup["sigma"] >= 0.5
            if souple and e <= 60.0:
                statut, az = "reoriente", round(cible, 1)
            else:
                statut = "orientation_signalee"
        h = float(t["z"]) - float(S.c.z_sol(p_sup[None])[0])
        viol = []
        if cible is not None and e > tol:
            viol.append(dict(regle=regle, nature="orientation", valeur=round(t["azimut0"], 1), attendu=round(cible, 1),
                             residu=round(e, 1), message=f"face à {t['azimut0']:.0f}°, attendu {cible:.0f}° ({motif})"
                             + (" ; azimut copié de la tête principale" if copie else "")))
        if tt == "R11v" and h - 0.475 < 2.0 - 0.05:
            viol.append(dict(regle="FEU-03", nature="hauteur", valeur=round(h - 0.475, 2), attendu=">= 2.0",
                             message=f"bas de la tête à {h - 0.475:.2f} m du sol"))
        if tt == "R12":
            lo, hi = S.regles["FEU-07"]["parametres"]["hauteur_centre_mesuree_m"]
            if not (lo - 0.15 <= h <= hi + 0.15):
                viol.append(dict(regle="FEU-07", nature="hauteur", valeur=round(h, 2), attendu=f"{lo}-{hi}",
                                 message=f"centre R12 à {h:.2f} m (mesuré sur site {lo}-{hi} m)"))
        out.append(dict(id=t["id"], support=sup["id"], type_tete=tt, azimut_source=round(t["azimut0"], 1),
                        azimut_resolu=az, cible=None if cible is None else round(cible, 1), regle=regle,
                        ecart_deg=None if e is None else round(e, 1), statut=statut, hauteur_centre_m=round(h, 2),
                        violations=viol, motif=motif, statut_2026=t["statut"],
                        verdict="violation" if statut == "reoriente" or any(v["nature"] == "hauteur" for v in viol)
                        else ("a_verifier" if viol else "conforme")))
    return out


# --------------------------------------------------------------------------- déductions
def deduire(S, positions, tetes_res):
    """Objets obligatoires absents : R12 (FEU-07), boutons d'appel (FEU-08), candélabres (ECL-04)."""
    props = []
    supports = [o for o in S.objets if o["type"] == "support_feux"]
    r12 = [t for t in S.tetes if t["type_tete"] == "R12"]
    osm = __import__("contexte").osm_traversees()
    for pp in S.c.passages:
        m = (pp["a"] + pp["b"]) / 2
        sig = [x for x in osm if x["crossing"] == "traffic_signals" and _dans_rect(x["xy"], pp, 3.0)]
        non_sig = [x for x in osm if x["crossing"] in ("marked", "uncontrolled", "unmarked", "zebra")
                   and _dans_rect(x["xy"], pp, 1.0)]
        axe = azimut(pp["b"] - pp["a"])
        proches = [t for t in r12 if min(np.hypot(*(t["p"] - pp["a"])), np.hypot(*(t["p"] - pp["b"]))) <= 4.5
                   and min(ecart_angle(t["azimut0"], axe), ecart_angle(t["azimut0"], axe + 180.0)) <= 30.0]
        if non_sig or (not sig and (not proches or "piste" in str(pp.get("groupe") or ""))):
            continue
        for E, F, nom in ((pp["a"], pp["b"], "a"), (pp["b"], pp["a"], "b")):
            cible = azimut(F - E)
            ok = [t for t in r12 if np.hypot(*(positions.get(t["parent"], t["support"]["p0"]) - E)) <= 4.5
                  and ecart_angle(t["azimut0"], cible) <= 45.0]
            if ok:
                continue
            sup = sorted([s for s in supports if np.hypot(*(positions.get(s["id"], s["p0"]) - E)) <= 3.0],
                         key=lambda s: (float(np.hypot(*(s["p0"] - E))), s["id"]))
            if sup:
                q = positions.get(sup[0]["id"], sup[0]["p0"])
                props.append(dict(id=f"ADD-R12-{pp['id']}-{nom}", type="tete_feu", type_tete="R12", regle="FEU-07",
                                  p=q, azimut=round(azimut(F - q), 1), support=sup[0]["id"], conf="faible",
                                  justification=f"extrémité {nom} du passage à feux {pp['id']} sans R12 tourné vers l'extrémité "
                                                f"opposée ; tête ajoutée sur {sup[0]['id']} (≤ 3 m)",
                                  preuves=[f"osm:{x['osm']}" for x in sig]))
            else:
                q = E + pp["v"] * (pp["demi_largeur"] + 0.35) - pp["u"] * (0.0 if nom == "b" else 0.0)
                props.append(dict(id=f"ADD-R12-{pp['id']}-{nom}", type="support_feux", type_tete="R12", regle="FEU-07",
                                  p=q, azimut=round(azimut(F - q), 1), support=None, conf="faible", hauteur_m=2.6,
                                  justification=f"extrémité {nom} du passage à feux {pp['id']} sans R12 ni support à moins de 3 m : "
                                                "mât piéton de 2,6 m dans le prolongement du passage, à la limite de la BEV",
                                  preuves=[f"osm:{x['osm']}" for x in sig]))
        # FEU-08 : bouton d'appel aux traversées OSM button_operated=yes
        for x in osm:
            if x["crossing"] != "traffic_signals" or not _dans_rect(x["xy"], pp, 3.0):
                continue
            src_btn = _osm_tags(x["osm"]).get("button_operated")
            if src_btn != "yes":
                continue
            for E, nom in ((pp["a"], "a"), (pp["b"], "b")):
                sup = sorted([s for s in supports if np.hypot(*(positions.get(s["id"], s["p0"]) - E)) <= 4.5],
                             key=lambda s: (float(np.hypot(*(s["p0"] - E))), s["id"]))
                if not sup:
                    continue
                if any(t["type_tete"] == "boitier_bouton_appel" for t in S.tetes_de.get(sup[0]["id"], [])):
                    continue
                q = positions.get(sup[0]["id"], sup[0]["p0"])
                props.append(dict(id=f"ADD-BTN-{pp['id']}-{nom}", type="tete_feu", type_tete="boitier_bouton_appel",
                                  regle="FEU-08", p=q, azimut=round(azimut(m - q), 1), support=sup[0]["id"], conf="faible",
                                  hauteur_centre_m=1.0,
                                  justification=f"OSM {x['osm']} button_operated=yes sur le passage {pp['id']} : boîtier à 1,0 m "
                                                f"sur {sup[0]['id']}, face vers le passage", preuves=[f"osm:{x['osm']}"]))
    props += _candelabres_manquants(S, positions)
    props.sort(key=lambda d: d["id"])
    return props


def _osm_tags(oid):
    from commun import VECTEURS, lire_geojson
    for f in lire_geojson(VECTEURS / "vector/osm_crossings.geojson"):
        if f["properties"].get("osm_id") == oid:
            return f["properties"]
    return {}


def _dans_rect(q, pp, marge):
    d = q - pp["a"]
    L = float(np.hypot(*(pp["b"] - pp["a"])))
    u = float(d @ pp["u"])
    v = float(d @ pp["v"])
    return -marge <= u <= L + marge and abs(v) <= pp["demi_largeur"] + marge


def _candelabres_manquants(S, positions):
    """ECL-04 : trou égal à 2 intervalles médians (±20 %) dans une rangée régulière (≥ 4 candélabres)."""
    g = S.regles["ECL-04"]["parametres"]
    lamps = [o for o in S.objets if o["type"] == "lampadaire" and not o["statut"].startswith("absent")]
    rangées = collections.defaultdict(list)
    from commun import projeter
    for o in lamps:
        p = positions.get(o["id"], o["p0"])
        best = None
        for route, refs in S.c.refs.items():
            if route > 100:
                continue
            for k, R in enumerate(refs):
                s, d, c = projeter(R, p[None])
                if d[0] <= 25 and (best is None or d[0] < best[0]):
                    best = (float(d[0]), route, k, float(s[0]), float(c[0]) * float(d[0]))
        if best:
            d, route, k, s, v = best
            rangées[(route, k, int(np.sign(v)))].append((s, v, o["id"], p))
    out = []
    for cle, L in sorted(rangées.items()):
        L.sort()
        if len(L) < g["taille_rangee_min_n"]:
            continue
        s = np.array([x[0] for x in L])
        v = np.array([x[1] for x in L])
        if np.ptp(v) > 6.0:
            continue
        pas = np.diff(s)
        med = float(np.median(pas))
        if med < 8.0:
            continue
        tol = g["tolerance_trou_pct"] / 100.0
        for i, d in enumerate(pas):
            if abs(d - 2 * med) <= tol * 2 * med:
                sm = (s[i] + s[i + 1]) / 2
                R = S.c.refs[cle[0]][cle[1]]
                from commun import point_a, normale_gauche
                q, tg = point_a(R, [sm])
                n = normale_gauche(tg)[0]
                pt = q[0] + n * float(np.median(v))
                out.append(dict(id=f"ADD-LAMP-{L[i][2]}-{L[i + 1][2]}", type="lampadaire", regle="ECL-04", p=pt,
                                azimut=None, conf="faible", support=None,
                                justification=f"rangée de {len(L)} candélabres (route {cle[0]}, pas médian {med:.1f} m) : trou de "
                                              f"{d:.1f} m entre {L[i][2]} et {L[i + 1][2]} (≈ 2 pas) ; à confirmer par photo ou terrain",
                                preuves=[L[i][2], L[i + 1][2]]))
    return out


def ilots_manquants(S, objets, arbit):
    """Anomalies de surface sur chaussée loin des bordures, regroupées : îlot (ou refuge) absent des
    surfaces. Emprise approchée : MNT 2026 surélevé (≥ 4 cm) autour des objets, sinon disque de 1,5 m."""
    pts = [(o, arbit[o["id"]]) for o in objets if arbit.get(o["id"], {}).get("statut") == "anomalie_surface"]
    groupes = []
    for o, a in pts:
        ctx_d = a.get("_ctx") or {}
        if ctx_d.get("zone") not in ("chaussee", "traversee_cyclable", "passage_pietons") or (ctx_d.get("d_bordure") or 0) < 2.0:
            continue
        for gr in groupes:
            if min(np.hypot(*(o["p0"] - q["p0"])) for q in gr) <= 4.0:
                gr.append(o)
                break
        else:
            groupes.append([o])
    out = []
    for gr in groupes:
        c = np.mean([o["p0"] for o in gr], axis=0)
        relief = S.c.relief_local(c, r_in=0.6, r_out=(3.0, 5.0))
        X, Y = np.meshgrid(np.arange(-4, 4.01, 0.2), np.arange(-4, 4.01, 0.2))
        Q = c + np.c_[X.ravel(), Y.ravel()]
        zr = np.median(S.c.z_sol(c + 4.5 * np.c_[np.cos(np.linspace(0, 6.28, 24)), np.sin(np.linspace(0, 6.28, 24))]))
        haut = Q[S.c.z_sol(Q) > zr + 0.04]
        from coherence_carte import _enveloppe
        if len(haut) >= 6 and relief > 0.04:
            anneau = _enveloppe(haut)
            src = f"MNT 2026 surélevé de {relief:.2f} m"
        else:
            ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            anneau = c + 1.5 * np.c_[np.cos(ang), np.sin(ang)]
            src = f"emprise a priori (MNT 2026 : {relief:+.2f} m)"
        ids = sorted(o["id"] for o in gr)
        if all(o["type"] == "arbre" for o in gr) and relief <= 0.04:
            ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            out.append(dict(id=f"ADD-SURF-{ids[0]}", type="surface_a_corriger", regle="VEG-01", p=c,
                            anneau=c + 1.0 * np.c_[np.cos(ang), np.sin(ang)], conf="faible", preuves=ids,
                            relief_m=round(relief, 3),
                            justification=f"arbre levé ({', '.join(ids)}) sur une chaussée v1 d'origine raster, à plus de 2 m "
                                          f"de toute bordure ({src}) : fosse, bande plantée ou limite de surface à corriger"))
            continue
        out.append(dict(id=f"ADD-ILOT-{ids[0]}", type="ilot_manquant", regle="GEN-01", p=c, anneau=anneau,
                        conf="faible" if all(o["type"] == "arbre" for o in gr) else "moyenne",
                        justification=f"objets prouvés ({', '.join(ids)}) sur la chaussée à plus de 2 m de toute bordure : "
                                      f"îlot bordé absent des surfaces ; {src}", preuves=ids, relief_m=round(relief, 3)))
    return out


def supports_confondus(S, objets, positions, arbit):
    """Supports de groupes différents à moins de 0,30 m après résolution : un seul mât (GEN-06)."""
    mats = ("panneau", "lampadaire", "support_feux", "poteau_reseau", "mat_camera", "poteau_arret")
    reps = {}
    for o in objets:
        a = arbit.get(o["id"])
        if a is None or o["type"] not in mats or not a.get("instancier", True):
            continue
        reps.setdefault(o["groupe"], o)
    cles = sorted(reps)
    out = []
    for i in range(len(cles)):
        for j in range(i + 1, len(cles)):
            a, b = reps[cles[i]], reps[cles[j]]
            d = float(np.hypot(*(positions[a["id"]] - positions[b["id"]])))
            if d < 0.50:
                m = (positions[a["id"]] + positions[b["id"]]) / 2
                out.append(dict(id=f"FUS-{cles[i]}-{cles[j]}", type="fusion_supports", regle="GEN-06", p=m, conf="moyenne",
                                justification=f"supports {cles[i]} ({a['type']}) et {cles[j]} ({b['type']}) à {d:.2f} m l'un de "
                                              "l'autre après résolution : très probablement un seul mât (GEN-06) ; fusionner les "
                                              "éléments portés sur un support",
                                preuves=[a["id"], b["id"]]))
    return out


# --------------------------------------------------------------------------- hypothèses des specs
def conflits_specs(S, positions, azim):
    """Comparaison des positions / azimuts de feux.json et panneaux.json avec la couche objets."""
    out = []
    for h in S.hyps:
        o = S.par_id.get(h["objet"]) if h["objet"] else None
        if o is None:
            proches = sorted([x for x in S.actifs if x["couche"] == "mobilier" and np.hypot(*(x["p0"] - h["p"])) <= 1.0],
                             key=lambda x: (float(np.hypot(*(x["p0"] - h["p"]))), x["id"]))
            out.append(dict(id=h["id"], spec=h["spec"], ref=h["ref"], code=h["code"], p_spec=h["p"], az_spec=h.get("azimut"),
                            objet=None, nature="identite" if proches else "absent_couche",
                            objet_proche=proches[0]["id"] if proches else None,
                            d_m=round(float(np.hypot(*(proches[0]["p0"] - h["p"]))), 3) if proches else None,
                            statut_spec=h.get("statut"), confiance_spec=h.get("confiance"), source_spec=h.get("source"),
                            role=h.get("role")))
            continue
        d = float(np.hypot(*(o["p0"] - h["p"])))
        daz = None if h.get("azimut") is None or o.get("azimut0") is None else ecart_angle(h["azimut"], o["azimut0"])
        if d <= SEUIL_PLANCHE_M and (daz is None or daz <= SEUIL_PLANCHE_DEG):
            continue
        V, ctx, _ = S.evaluer(o, p=h["p"], az=h.get("azimut"))
        tri = (o.get("triangulation") or {}).get("decision") in ("garder", "affiner")
        out.append(dict(id=h["id"], spec=h["spec"], ref=h["ref"], code=h["code"], p_spec=h["p"], az_spec=h.get("azimut"),
                        position_couche_confirmee_photo=bool(tri and d > SEUIL_PLANCHE_M),
                        objet=o["id"], d_m=round(d, 3), daz_deg=None if daz is None else round(daz, 1),
                        nature="position" if d > SEUIL_PLANCHE_M else "orientation",
                        spec_legale=not any(v["dure"] for v in V),
                        violations_spec=sorted({v["regle"] for v in V if v["dure"]}),
                        statut_spec=h.get("statut"), confiance_spec=h.get("confiance"), source_spec=h.get("source"),
                        ecart_note=h.get("ecart_couche")))
    return out


# --------------------------------------------------------------------------- preuves
def preuves(S, objets, arbit, orient, conflits, revue, faire_planches=True):
    """Planches des corrections (> 0,3 m ou > 20°) et des conflits, triangulation, revue."""
    import coherence_preuves as CP
    jobs = []
    for o in objets:
        a = arbit.get(o["id"])
        if a is None or o["id"] != a["_rep"]:
            continue
        d = float(np.hypot(*(a["p"] - o["p0"])))
        orr = orient.get(o["id"]) or {}
        daz = None
        if orr.get("statut") == "reoriente" and o.get("azimut0") is not None:
            daz = ecart_angle(orr["az"], o["azimut0"])
        conf_s = [c for c in conflits if c.get("objet") == o["id"] and c["nature"] in ("position", "orientation")]
        if d > SEUIL_PLANCHE_M or (daz or 0) > SEUIL_PLANCHE_DEG or a["statut"] in ("a_arbitrer_photo", "anomalie_surface", "non_resolu") \
                or orr.get("statut") == "orientation_signalee" or conf_s:
            jobs.append((o, a, orr, conf_s))
    for c in conflits:
        if c["nature"] == "identite":
            o = S.par_id[c["objet_proche"]]
            j = [x for x in jobs if x[0]["id"] == o["id"]]
            if j:
                j[0][3].append(c)
            else:
                jobs.append((o, arbit[o["id"]], orient.get(o["id"]) or {}, [c]))
    res = {}
    if faire_planches and CP.PLANCHES.exists():
        for f in sorted(CP.PLANCHES.glob("*.jpg")):
            f.unlink()                       # planches d'une exécution précédente
    for o, a, orr, conf_s in jobs:
        hyps = [dict(cle="A", p=o["p0"], az=o.get("azimut0") if o["type"] != "arbre" else None)]
        if float(np.hypot(*(a["p"] - o["p0"]))) > 0.05 or orr.get("statut") == "reoriente":
            hyps.append(dict(cle="C", p=a["p"], az=orr.get("az")))
        for c in conf_s:
            hyps.append(dict(cle="S", p=c["p_spec"], az=c.get("az_spec")))
        if o.get("triangulation") and o["triangulation"].get("position_triangulee"):
            hyps.append(dict(cle="T", p=np.array(o["triangulation"]["position_triangulee"][:2]), az=None))
        h = float(o.get("hauteur") or 2.5) if o["type"] != "arbre" else 3.0
        h = min(max(h, 1.0), 6.0)
        valide = (lambda date, o=o: valide_pour_photo(o, date))
        regles_v = sorted({v["regle"] for v in a["_V"] if v["nature"] != "z"})
        titre = [f"{o['id']} ({o['type']}{' ' + o['code'] if o.get('code') else ''}) - {a['statut']} - preuve {o['preuve']} "
                 f"sigma {o['sigma']} m - statut 2026 : {o['statut']}",
                 "règles : " + ", ".join(regles_v) + f" | déplacement {np.hypot(*(a['p'] - o['p0'])):.2f} m"
                 + (f" | azimut {o.get('azimut0')} -> {orr.get('az')}" if orr.get("statut") else "")
                 + (" | spec : " + ", ".join(c["id"] for c in conf_s) if conf_s else "")]
        chemin = CP.PLANCHES / f"{o['id']}.jpg"
        entree = dict(planche=chemin.relative_to(RACINE).as_posix(), hypotheses=[q["cle"] for q in hyps], photos=[])
        notes = []
        for q in hyps:
            zq = S.zones(np.asarray(q["p"], float)[None])[0][0]
            rq = S.c.ref_bordure(np.asarray(q["p"], float)[None], rayon=10.0, circulee=True)[0]
            notes.append(f"{q['cle']} : ({q['p'][0]:.2f} ; {q['p'][1]:.2f}) zone {zq}"
                         + ("" if rq is None else f", t = {rq['t']:+.2f} m de {rq['id']}")
                         + ("" if q.get("az") is None else f", face {q['az']:.0f}°"))
        notes += [j[:150] for j in a.get("justification", [])[:2]]
        if faire_planches:
            _, photos = CP.planche(S.c, o["id"], titre, hyps, h, valide, chemin, azimuts=True, notes=notes)
            entree["photos"] = photos
        dpos = max([float(np.hypot(*(q["p"] - o["p0"]))) for q in hyps if q["cle"] in ("C", "S")] or [0.0])
        if faire_planches and o["type"] in ("lampadaire", "support_feux", "panneau", "poteau_reseau", "mat_camera",
                                            "potelet", "poteau_arret") and dpos > 0.75 and len(entree["photos"]) >= 2:
            alt = max([q for q in hyps if q["cle"] in ("C", "S")], key=lambda q: float(np.hypot(*(q["p"] - o["p0"]))))
            st = o["statut"]
            vd = FIN_TRAVAUX if (st.startswith("déduit 2026") or st.startswith("2026")) else "2000-01-01"
            try:
                entree["triangulation"] = CP.trianguler(o, o["p0"], alt["p"], vd)
            except Exception as e:  # noqa: BLE001 - indice seulement
                entree["triangulation"] = dict(conclusion=f"échec : {e}")
        entree["revue"] = revue.get(o["id"])
        res[o["id"]] = entree
    return res


def preuves_tetes(S, tetes_res, positions, revue, faire_planches=True):
    """Planches des têtes de feux réorientées (ou signalées) de plus de 20° : axe vertical du support
    et face attendue (A d'origine, C corrigée) dans chaque photo calée valide."""
    import coherence_preuves as CP
    res = {}
    for t in tetes_res:
        if t["statut"] not in ("reoriente", "orientation_signalee") or (t["ecart_deg"] or 0) <= SEUIL_PLANCHE_DEG:
            continue
        sup = S.par_id[t["support"]]
        p = positions.get(sup["id"], sup["p0"])
        hyps = [dict(cle="A", p=p, az=t["azimut_source"]), dict(cle="C", p=p, az=t["cible"])]
        h = min(max(float(sup.get("hauteur") or 3.0), 1.5), 5.0)
        valide = (lambda date, o=sup: valide_pour_photo(o, date))
        titre = [f"{t['id']} (tête {t['type_tete']} sur {sup['id']}) - {t['statut']} - azimut {t['azimut_source']} -> {t['cible']} "
                 f"({t['regle']})", f"{t['motif']} ; hauteur du centre {t['hauteur_centre_m']} m ; statut 2026 : {t['statut_2026']}"]
        chemin = CP.PLANCHES / f"{t['id']}.jpg"
        entree = dict(planche=chemin.relative_to(RACINE).as_posix(), photos=[])
        if faire_planches:
            notes = [f"A : face {t['azimut_source']}° (couche)", f"C : face {t['cible']}° (règle {t['regle']})"]
            _, photos = CP.planche(S.c, t["id"], titre, hyps, h, valide, chemin, azimuts=True, notes=notes)
            entree["photos"] = photos
        entree["revue"] = revue.get(t["id"])
        t["planche"], t["photos_planche"] = entree["planche"], entree["photos"]
        res[t["id"]] = entree
    return res


# --------------------------------------------------------------------------- principal
def main(argv=None):
    ap = argparse.ArgumentParser(description="Solveur de cohérence des objets (règles d'implantation + preuves)")
    ap.add_argument("--sans-planches", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    carte = Carte(verbeux=True)
    carte.ecrire()
    R = lire_json(REGLES)
    objets, clotures = charger(R)
    tt = tetes(objets)
    hy = hypotheses_specs(objets)
    S = Solveur(carte, R, objets, clotures, tt, hy)
    revue = lire_json(REVUE)["revues"] if REVUE.exists() else {}
    print(f"objets {len(objets)}, têtes {len(tt)}, hypothèses specs {len(hy)} ({time.time() - t0:.1f} s)")

    evals, resol = evaluer_groupes(S, objets)
    for o in objets:
        if o["id"] in resol:
            o["travaux"] = bool(resol[o["id"]].get("degradation_temporelle"))
    collis = S.collisions()
    import coherence_preuves as CP
    cams = np.array([[r["pose"]["x"], r["pose"]["y"]] for r in CP._poses().values() if r.get("accepte")])
    nphotos = {}
    for o in objets:
        if o["statut"].startswith("absent") or np.min(np.hypot(*(cams - o["p0"]).T)) > 30:
            nphotos[o["id"]] = []
            continue
        h = 2.5 if o["type"] != "arbre" else 3.0
        p3 = np.r_[o["p0"], float(carte.z_sol(o["p0"][None])[0])]
        sel = CP.photos_calees([p3], h, lambda d, o=o: valide_pour_photo(o, d), n=13, dmax=25.0)
        nphotos[o["id"]] = [pid for _, pid, _, _ in sel]
    arbit, orient = {}, {}
    for o in objets:
        if o["statut"].startswith("absent"):
            continue
        res = resol[o["id"]]
        rep = S.par_id[res["representant"]]
        if o["id"] != rep["id"]:
            continue
        membres = [S.par_id[m] for m in res["membres"]]
        V = [v for m in membres for v in evals[m["id"]]["V"]]
        ph = sorted({p for m in membres for p in nphotos[m["id"]]})
        ar = arbitrer(S, rep, dict(V=V, ctx=evals[rep["id"]]["ctx"]), res, ph)
        ar["_V"], ar["_ctx"], ar["_rep"] = V, evals[rep["id"]]["ctx"], rep["id"]
        for m in membres:
            arbit[m["id"]] = ar
    # îlots manquants : un objet faible voisin d'une anomalie forte partage l'anomalie
    ilots = ilots_manquants(S, [o for o in objets if o["id"] in arbit], arbit)
    for il in ilots:
        for o in objets:
            ar = arbit.get(o["id"])
            if ar is None or ar["statut"] not in ("a_arbitrer_photo", "non_resolu"):
                continue
            if np.hypot(*(o["p0"] - il["p"])) <= 4.0:
                ar2 = dict(ar, statut="anomalie_surface", instancier=True, conf="faible", p=o["p0"].copy(),
                           justification=ar["justification"] + [f"sur l'îlot manquant {il['id']}, étayé par des objets bien prouvés"])
                for m in resol[o["id"]]["membres"]:
                    arbit[m] = ar2
                il["preuves"] = sorted(set(il["preuves"]) | set(resol[o["id"]]["membres"]))
    obsoletes = [o for o in objets if "obsolete_probable" in (arbit.get(o["id"]) or {}).get("drapeaux", [])]
    for o in objets:
        ar = arbit.get(o["id"])
        if ar is None or ar["statut"] not in ("a_arbitrer_photo", "non_resolu") or "obsolete_probable" in ar["drapeaux"]:
            continue
        voisins = [x["id"] for x in obsoletes if np.hypot(*(x["p0"] - o["p0"])) <= 3.0]
        if voisins and ar["_ctx"]["zone"] in CIRC_BASE | {"traversee_cyclable", "passage_pietons"}:
            ar2 = dict(ar, statut="non_resolu", instancier=False, conf="faible",
                       drapeaux=sorted(set(ar["drapeaux"]) | {"obsolete_probable", "a_verifier_terrain2026"}),
                       justification=ar["justification"] + [f"sur le même îlot que {', '.join(voisins)} (probablement supprimé "
                                                            "par les travaux 2025)"])
            for m in resol[o["id"]]["membres"]:
                arbit[m] = ar2
    positions = {k: v["p"] for k, v in arbit.items()}
    fusions = supports_confondus(S, objets, positions, arbit)
    hyp_az = {}
    for h in hy:
        if h.get("objet") and h.get("azimut") is not None:
            hyp_az.setdefault(h["objet"], h["azimut"])
    for o in objets:
        if o["id"] not in arbit:
            continue
        p = positions[o["id"]]
        orient[o["id"]] = orienter(S, o, p, S.contexte(o, p), hyp_az.get(o["id"]))
    groupes = collections.defaultdict(list)
    for o in objets:
        if o["id"] in orient and o["type"] == "panneau":
            groupes[o["groupe"]].append(o)
    for g, membres in groupes.items():
        principaux = [m for m in membres if not str(m.get("code") or "").startswith("M")]
        if not principaux:
            continue
        ref = sorted(principaux, key=lambda m: m["id"])[0]
        for m in membres:
            if str(m.get("code") or "").startswith("M") and orient[ref["id"]].get("az") is not None:
                orr = dict(orient[ref["id"]])
                orr["raison"] = f"panonceau : même plan que {ref['id']} (SIG-08)"
                if m.get("azimut0") == orr["az"]:
                    orr["statut"] = None
                orient[m["id"]] = orr
    conflits = conflits_specs(S, positions, orient)
    tetes_res = evaluer_tetes(S, positions)
    deductions = deduire(S, positions, tetes_res) + ilots + fusions
    pr = preuves(S, objets, arbit, orient, conflits, revue, faire_planches=not a.sans_planches)
    pr.update(preuves_tetes(S, tetes_res, positions, revue, faire_planches=not a.sans_planches))
    print(f"évaluation et preuves : {time.time() - t0:.1f} s")
    import coherence_sorties as CS
    CS.ecrire_sorties(S, objets, clotures, evals, resol, arbit, orient, nphotos, collis, conflits, tetes_res,
                      deductions, pr, revue)
    print(f"terminé en {time.time() - t0:.1f} s")


if __name__ == "__main__":
    sys.exit(main())
