# -*- coding: utf-8 -*-
"""Compilateur : description simple d'une route (YAML lisible, en français) → instance `modele_voie/0.1` valide.

    python recon/generateur/description/description_vers_modele.py DESCRIPTION.yaml [--sortie DOSSIER]
                                                                 [--verifier-determinisme]

Sorties (par défaut `recon/out/generateur/<scene>/`) : `modele_voie.json` (le modèle, lu par le générateur Houdini)
et `compilation.json` (avertissements, contrôles de conformité aux règles, décompte des provenances, résultat du
validateur). Le format est documenté dans `FORMAT_DESCRIPTION.md` (même dossier).

Principe : ce que la description dit est repris tel quel (prov « description:<champ> ») ; ce qu'elle ne dit pas est
complété par la règle de `regles_route_fr.json` qui le fixe (prov « defaut:<DEF/RF> » ou « inference:<RF> ») ;
si aucune règle ne fixe une valeur non dite, la compilation s'arrête avec un message (Houdini n'invente rien).
Déterministe : aucune date d'exécution, ordre fixe, flottants arrondis au 1/10 de mm.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(GEN / "schema"))
import regles  # noqa: E402
from commun import geometrie as G  # noqa: E402
from commun import profil as PF  # noqa: E402
from commun import prov as P  # noqa: E402
from description import format_profil as FP  # noqa: E402
from description import vocabulaire as V  # noqa: E402
from description import yaml_simple  # noqa: E402

DEPOT = GEN.parents[1]
SORTIE_DEFAUT = DEPOT / "recon" / "out" / "generateur"
ORIGINE_DEPOT = [917279.43, 6460289.98, 216.3]      # O du dépôt (README_HDA § 2) : repère local des scènes
VERSION = "description_vers_modele/1.0"
CONVENTIONS = {
    "s": "abscisse curviligne absolue (m) le long de la ligne de référence de la route, pour toutes les lois de "
         "largeur (points), intervalles, interruptions, abaissés et ancrages",
    "t": "décalage latéral (m), positif à gauche du sens de la ligne de référence",
    "cap_deg": "cap OpenDRIVE : 0° = est, 90° = nord, sens trigonométrique",
    "ligne_reference": "axe de la chaussée décrite : séparation des sens (milieu du terre-plein s'il y en a un), "
                       "ou milieu de la chaussée d'une route à sens unique",
}


class ErreurDescription(ValueError):
    pass


def _r(x, nd=4):
    return round(float(x), nd) + 0.0


def arrondir(o, nd=4):
    if isinstance(o, float):
        v = round(o, nd)
        return 0.0 if v == 0 else v
    if isinstance(o, dict):
        return {k: arrondir(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [arrondir(v, nd) for v in o]
    return o


CLES_RACINE = {"scene", "nom", "titre", "description", "format", "date", "confiance", "origine", "contexte", "troncon",
               "troncons", "trace", "polyligne", "longueur", "depart", "cap", "de", "vers", "repere", "profil", "materiaux",
               "marquages", "evenements", "vegetation", "abords", "signalisation", "objets", "attendus",
               "ecarts_admis",
               # lot « scenes » (17/10/2026) : réseau de tronçons reliés (carrefours plans, giratoires, bretelles),
               # compilé par description/carrefours.py ; « plan » : options du plan coté SVG
               "carrefours", "giratoires", "bretelles", "plan"}
CLES_RESEAU = ("carrefours", "giratoires", "bretelles")
CLES_CONTEXTE = {"agglomeration", "vitesse", "vitesse_kmh", "categorie", "u", "u_m", "sens_unique", "usure_marquages",
                 "v15", "v15_kmh"}
CLES_TRONCON = {"trace", "polyligne", "longueur", "depart", "cap", "de", "vers", "repere", "profil", "evenements",
                "vegetation", "abords", "signalisation", "objets", "nom", "contexte", "id",
                # lot N1 (réseau, 18/10/2026) : matériaux, marquages et confiance propres à un tronçon (scènes composées
                # de plusieurs sites) ; absents, ceux de la description valent pour le tronçon (sortie inchangée)
                "materiaux", "marquages", "confiance"}
PARAMS = {  # paramètres admis par évènement (en plus de a, type, chemin, texte)
    "passage_pieton": {"largeur", "abaisses", "bev", "panneau", "pente_rampants_pct", "regime"},
    "dos_d_ane": {"longueur", "hauteur", "triangles"},
    "plateau": {"longueur", "hauteur", "rampe_pct", "passage_pieton", "bev", "abaisses", "triangles", "panneau"},
    "plateau_pieton": {"longueur", "hauteur", "rampe_pct", "passage_pieton", "bev", "abaisses", "triangles", "panneau"},
    "coussin": {"largeur", "longueur", "hauteur", "triangles"},
    "rabattement": {"sens", "voie", "biseau", "fleches", "nombre_fleches", "zebra", "elargit", "de", "vers"},
    "elargissement": {"sens", "voie", "cote", "largeur", "type_voie", "biseau"},
    "arret_bus": {"cote", "quai", "articule", "abri", "zigzag", "panneau"},
    "entree_charretiere": {"cote", "largeur"},
    "abaisse": {"cote", "largeur", "bev"},
    "panneau": {"code", "cote", "valeur"},
    "profil": {"nouveau", "transition"},
    "zone_depassement_interdit": {"sens", "fin", "annonce", "fleches"},
    "fleches": {"type_fleche", "voies", "nombre", "interdistance", "sens"},
    "inscription": {"texte_sol", "voie", "hauteur"},
    "ouverture": {"longueur", "nouveau", "sens", "raccord"},
    "fermeture": {"longueur", "nouveau", "raccord"},
}


def verifier_cles(d: dict, admises: set, chemin: str):
    inconnues = sorted(k for k in d if k not in admises)
    if inconnues:
        raise ErreurDescription(f"{chemin} : clé(s) inconnue(s) {', '.join(inconnues)} (admises : {', '.join(sorted(admises))})")


def normaliser_cles(o):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            nk = V.norm_cle(k)
            nk = V.SYNONYMES_CLES.get(nk, nk)
            if nk in out:
                raise ErreurDescription(f"clé « {k} » en double (après normalisation : {nk})")
            out[nk] = normaliser_cles(v)
        return out
    if isinstance(o, list):
        return [normaliser_cles(x) for x in o]
    return o


# ================================================================================================ contexte
def lire_contexte(d: dict, bandes_brutes: list[dict]) -> dict:
    c = dict(d.get("contexte") or {})
    if c.get("vitesse") is None and c.get("vitesse_kmh") is not None:
        c["vitesse"] = c["vitesse_kmh"]
    if c.get("u") is None and c.get("u_m") is not None:
        c["u"] = c["u_m"]
    conf = d.get("confiance", "moyenne")
    out = {"conf": conf}
    # catégorie
    if c.get("categorie") is not None:
        k = V.norm(c["categorie"])
        if k not in V.CATEGORIES:
            raise ErreurDescription(f"contexte.categorie : « {c['categorie']} » inconnue ({', '.join(sorted(V.CATEGORIES))})")
        out["categorie"], out["prov_categorie"] = V.CATEGORIES[k], P.description("contexte.categorie", conf)
    # agglomération
    if c.get("agglomeration") is not None:
        out["agglomeration"] = V.booleen(c["agglomeration"], "contexte.agglomeration")
        out["prov_agglomeration"] = P.description("contexte.agglomeration", conf)
    elif out.get("categorie"):
        out["agglomeration"] = out["categorie"] in ("rue", "desserte", "zone_rencontre", "aire_pietonne", "voie_service")
        out["prov_agglomeration"] = P.inference("RF-OSM-AGG-001", conf="faible", note=f"déduite de la catégorie {out['categorie']}")
    elif c.get("vitesse") is not None:
        out["agglomeration"] = V.nombre(c["vitesse"], "contexte.vitesse") <= 50
        out["prov_agglomeration"] = P.inference("RF-OSM-AGG-001", conf="faible", note="indice : vitesse ≤ 50 km/h")
    else:
        raise ErreurDescription("contexte : dire au moins « agglomeration: oui/non », la catégorie (rue, route…) ou la vitesse")
    if "categorie" not in out:
        out["categorie"] = "rue" if out["agglomeration"] else "route_departementale"
        out["prov_categorie"] = P.table("highway_vers_categorie", conf="faible",
                                        note="catégorie non dite : rue en agglomération, route départementale hors agglomération")
    # vitesse
    sep = any(b["type"] in ("terre_plein", "separateur") for b in bandes_brutes)
    voies = [b for b in bandes_brutes if b["type"] in PF.VOIES_MOTORISEES]
    if c.get("vitesse") is not None:
        out["vitesse"], out["prov_vitesse"] = V.nombre(c["vitesse"], "contexte.vitesse"), P.description("contexte.vitesse", conf)
    elif out["categorie"] == "zone_rencontre":
        out["vitesse"], out["prov_vitesse"] = regles.valeur("RF-OSM-VIT-004", "zone_rencontre"), P.defaut("RF-OSM-VIT-004")
    elif out["agglomeration"]:
        out["vitesse"], out["prov_vitesse"] = regles.valeur("RF-OSM-VIT-002", "defaut"), P.defaut("RF-OSM-VIT-002")
    else:
        if out["categorie"] == "autoroute":
            v, note = regles.valeur("RF-OSM-VIT-003", "autoroute"), "autoroute"
        elif sep:
            v, note = regles.valeur("RF-OSM-VIT-003", "chaussees_separees"), "chaussées séparées"
        elif max([sum(1 for b in voies if b.get("sens") == s) for s in ("avant", "arriere")] or [0]) >= 2:
            v = int(str(regles.valeur("RF-OSM-VIT-003", "plusieurs_voies_meme_sens")).split()[0])
            note = "plusieurs voies de même sens"
        else:
            v, note = regles.valeur("RF-OSM-VIT-003", "route_bidirectionnelle_sans_separateur"), "route bidirectionnelle sans séparateur"
        out["vitesse"], out["prov_vitesse"] = v, P.defaut("RF-OSM-VIT-003", note=note)
    # u
    if c.get("u") is not None:
        u = c["u"] if isinstance(c["u"], (int, float)) and c["u"] < 0.2 else V.nombre(c["u"], "contexte.u", "cm")
        if u not in (0.03, 0.05, 0.06, 0.075):
            raise ErreurDescription(f"contexte.u : {u} m n'est pas une valeur IISR (3, 5, 6 ou 7,5 cm)")
        out["u"], out["prov_u"] = u, P.description("contexte.u", conf, regle="DEF-001")
    return out


# ================================================================================================ géométrie
def lire_trace(t: dict, origine: list, chemin: str) -> G.Trace:
    local = V.norm(t.get("repere", "local")) != "l93"
    ox, oy = (origine[0], origine[1]) if local else (0.0, 0.0)

    def pt(v, c):
        if not (isinstance(v, list) and len(v) >= 2):
            raise ErreurDescription(f"{c} : point [x, y] attendu")
        return ox + V.nombre(v[0], c), oy + V.nombre(v[1], c)

    if "polyligne" in t:
        pts = [pt(p, f"{chemin}.polyligne[{i}]") for i, p in enumerate(t["polyligne"])]
        tr = G.trace_polyligne(pts)
        tr._cassure = G.angle_cassure_max_deg(pts)
        return tr
    if "de" in t and "vers" in t:
        (xa, ya), (xb, yb) = pt(t["de"], f"{chemin}.de"), pt(t["vers"], f"{chemin}.vers")
        return G.Trace(xa, ya, math.degrees(math.atan2(yb - ya, xb - xa))).droite(math.hypot(xb - xa, yb - ya))
    x0, y0 = pt(t.get("depart", [0, 0]), f"{chemin}.depart")
    tr = G.Trace(x0, y0, V.nombre(t.get("cap", 0), f"{chemin}.cap"))
    if "longueur" in t and "trace" not in t:
        return tr.droite(V.nombre(t["longueur"], f"{chemin}.longueur"))
    elems = t.get("trace")
    if not elems:
        raise ErreurDescription(f"{chemin} : donner « de / vers », « longueur » (+ cap), « trace » ou « polyligne »")
    for i, e in enumerate(elems):
        c = f"{chemin}.trace[{i}]"
        if not isinstance(e, dict) or len(e) != 1:
            raise ErreurDescription(f"{c} : un élément « droite: L », « arc: {{…}} » ou « clothoide: {{…}} » par ligne")
        (k, v), = e.items()
        if k == "droite":
            tr.droite(V.nombre(v, c))
        elif k in ("arc", "courbe", "virage"):
            r = V.nombre(v["rayon"], c + ".rayon")
            g = V.norm(v.get("sens", "gauche")) == "gauche"
            lg = V.nombre(v["longueur"], c) if "longueur" in v else math.radians(V.nombre(v["angle"], c + ".angle")) * r
            tr.arc(r, lg, g)
        elif k == "clothoide":
            lg = V.nombre(v["longueur"], c + ".longueur")
            sg = 1.0 if V.norm(v.get("sens", "gauche")) == "gauche" else -1.0
            k0 = tr.courbure_fin() if "rayon_debut" not in v else sg / V.nombre(v["rayon_debut"], c)
            k1 = sg / V.nombre(v["rayon_fin"], c) if v.get("rayon_fin") not in (None, "infini", "droite") else 0.0
            tr.clothoide(lg, k0, k1)
        else:
            raise ErreurDescription(f"{c} : élément de tracé inconnu « {k} »")
    return tr


# ================================================================================================ bandes
def resoudre_bandes(bandes: list[dict], limites: list, d: dict, chemin: str, ctxd: dict):
    """Sens, pistes bidirectionnelles, attributs → champs du modèle, vues de bordure, matériaux."""
    conf = ctxd["conf"]
    mot = [b for b in bandes if b["type"] in PF.VOIES_MOTORISEES]
    sans = [b for b in mot if b["sens"] is None]
    su = (d.get("contexte") or {}).get("sens_unique")
    if sans:
        if len(sans) != len(mot):
            raise ErreurDescription(f"{chemin} : donner le sens (→ ou ←) de toutes les voies, ou d'aucune")
        if su is not None and V.booleen(su, "contexte.sens_unique"):
            for b in mot:
                b["sens"] = "avant"
                b["prov"]["sens"] = P.description("contexte.sens_unique", conf)
        elif len(mot) == 1 and mot[0]["type"] == "chaussee_partagee":
            mot[0]["sens"] = "double"
        elif len(mot) % 2 == 0:
            for k, b in enumerate(mot):
                b["sens"] = "arriere" if k < len(mot) // 2 else "avant"
                b["prov"]["sens"] = P.inference("RF-OSM-PRF-002", note="voies sans flèche : moitié gauche ←, moitié droite →")
        else:
            raise ErreurDescription(f"{chemin} : {len(mot)} voies sans sens : écrire → ou ← sur chaque voie "
                                    "(ou « sens_unique: oui » dans le contexte)")
    # sens des autres bandes
    for i, b in enumerate(bandes):
        if b["sens"] is not None:
            continue
        if b["type"] in ("trottoir", "chemin_pieton", "quai_bus", "voie_verte"):
            b["sens"] = "double"
        elif b["type"] in ("bande_cyclable", "piste_cyclable", "stationnement", "livraison", "voie_bus",
                           "rive_cyclable_cvcb", "bande_derasee", "accotement_revetu", "bande_arret_urgence"):
            if b["type"] == "piste_cyclable" and b["attributs"].get("bidirectionnelle"):
                b["sens"] = "double"
                continue
            proches = sorted((abs(j - i), j) for j, x in enumerate(bandes) if x["type"] in PF.VOIES_MOTORISEES)
            b["sens"] = bandes[proches[0][1]]["sens"] if proches else "double"
            if b["sens"] == "double" and b["type"] != "piste_cyclable":
                b["sens"] = "aucun" if b["type"] in ("stationnement", "livraison", "bande_derasee", "accotement_revetu") else "double"
            b["prov"]["sens"] = P.inference("RF-OSM-PRF-002", note="sens de la voie la plus proche")
        else:
            b["sens"] = "aucun"
    # pistes bidirectionnelles → deux demi-pistes (axe T'1 2u entre elles, RF-OSM-CYC-002)
    nb, nl = [], [limites[0]]
    for i, b in enumerate(bandes):
        if b["type"] == "piste_cyclable" and b["attributs"].get("bidirectionnelle"):
            w = b["largeur"]
            g, dr = copy.deepcopy(b), copy.deepcopy(b)
            for x, s in ((g, "arriere"), (dr, "avant")):
                x["sens"] = s
                x["attributs"]["demi_piste"] = True
                x.setdefault("cyclable", {})["double_sens"] = True
                if w is not None:
                    x["largeur"] = w / 2.0
                    x["prov"]["largeur"] = P.description(f"{chemin}.largeur", conf, note=f"moitié de la piste bidirectionnelle de {w} m")
            nb += [g, dr]
            nl += [None, limites[i + 1]]
        else:
            nb.append(b)
            nl.append(limites[i + 1])
    bandes[:], limites[:] = nb, nl
    # attributs → champs ; un matériau dit pour une bande vaut pour les bandes suivantes du même type
    dernier_mat = {}
    for i, b in enumerate(bandes):
        a = b["attributs"]
        t = b["type"]
        if t == "stationnement":
            st = {"orientation": a.get("orientation", "longitudinal"), "position": a.get("position", "chaussee")}
            if st["orientation"] == "longitudinal":
                st["longueur_place_m"] = regles.valeur("RF-OSM-LAR-040", "longueur_place")
            if "places_marquees" in a:
                st["marquage_places"] = a["places_marquees"]
            b["stationnement"] = st
            b["prov"]["stationnement"] = P.description(b["prov"]["*"]["src"].split(":", 1)[1], conf,
                                                       regle="RF-OSM-LAR-040" if st["orientation"] == "longitudinal" else "RF-OSM-LAR-041",
                                                       note="longueur de place : RF-OSM-LAR-040" if "longueur_place_m" in st else None)
        if t in ("bande_cyclable", "piste_cyclable"):
            cy = b.get("cyclable") or {}
            if t == "piste_cyclable":
                cy.setdefault("double_sens", bool(a.get("bidirectionnelle")))
            if cy:
                b["cyclable"] = cy
                b["prov"]["cyclable"] = P.description(b["prov"]["*"]["src"].split(":", 1)[1], conf)
        if t == "voie_bus":
            b["usagers"] = ["bus"] + (["velo"] if a.get("velos_admis") else [])
        if t == "terre_plein":
            b["terre_plein"], b["prov_terre_plein"] = terre_plein(b, a, conf)
            b["prov"]["terre_plein"] = b["prov_terre_plein"]
        if t == "bande_plantee" and a.get("arbres"):
            a["_arbres_demandes"] = True
        # matériau dit sur la bande
        mats = a.get("materiaux") or []
        if a.get("materiau"):
            mats = [None] + mats
        mid = None
        for m in mats:
            if m is None:
                mid = a["materiau"]
                continue
            v = V.MATERIAUX[m]
            if isinstance(v, dict):
                cl = "piste" if t == "piste_cyclable" else ("trottoir" if t in PF.TYPES_PIETONS else "chaussee")
                v = v[cl]
                if cl == "chaussee" and a.get("usure") in V.USURE_ENROBE:
                    v = V.USURE_ENROBE[a["usure"]]
            mid = v
        if mid is None and a.get("usure") in V.USURE_ENROBE and t in PF.TYPES_CHAUSSEE:
            mid = V.USURE_ENROBE[a["usure"]]
        if mid:
            b["materiau_id"] = mid
            b["prov"]["materiau_id"] = P.description(b["prov"]["*"]["src"].split(":", 1)[1] + ".materiau", conf)
            dernier_mat[(t, b.get("sous_type"))] = (mid, b["prov"]["*"]["src"].split(":", 1)[1])
        elif (t, b.get("sous_type")) in dernier_mat and t not in ("terre_plein",):
            mid, de = dernier_mat[(t, b.get("sous_type"))]
            b["materiau_id"] = mid
            b["prov"]["materiau_id"] = P.description(de + ".materiau", conf, note="matériau dit pour la bande précédente du même type")
    # vues de bordure dites → niveau de la bande haute
    for i, lim in enumerate(limites):
        if not lim or "bordure" not in lim or "vue_m" not in lim["bordure"]:
            continue
        a = bandes[i - 1] if i > 0 else None
        b = bandes[i] if i < len(bandes) else None
        for x in (a, b):
            if x is not None and PF.cle_niveau(x) in ("trottoir", "terre_plein", "quai"):
                x["attributs"]["dz_m"] = lim["bordure"]["vue_m"]
                x["attributs"]["prov_dz"] = lim["prov"]
    return bandes, limites


def terre_plein(b: dict, a: dict, conf: str):
    """Objet terre_plein d'une bande « terre-plein » selon ses attributs (cinq genres, MODELE_VOIE § 5)."""
    mats = [V.MATERIAUX[m] for m in a.get("materiaux", []) if not isinstance(V.MATERIAUX[m], dict)]
    f = a.get("franchissable", "non")
    tp = {"franchissable": f}
    src = b["prov"]["*"]["src"].split(":", 1)[1]
    if f == "peint":
        h = regles.valeur("DEF-020")
        tp["remplissage"] = {"type": "hachures_peintes"}
        tp["marquage_contour"] = {"modulation": "continue", "largeur_u": 3, "retrait_u": 2}
        tp["hachures"] = {"angle_deg": h["angle_rive_deg"], "bande_m": h["bande"], "espacement_m": h["espacement"],
                          "aplat_sous_m": h["aplat_si_largeur_inf"]}
        return tp, P.description(src, conf, regle="DEF-020", note="terre-plein peint : contour et hachures DEF-020")
    mid = mats[0] if mats else None
    typ = {"gazon_tondu": "gazon", "herbe_haute": "gazon", "brf_bois_concasse": "brf", "gravier_concasse_6_10": "gravier",
           "gravillons_ilot": "gravier", "galets_20_40": "galets", "paves_beton": "paves", "paves_granit": "paves",
           "beton_balaye": "beton", "beton_desactive": "beton", "terre_nue": "terre", "stabilise_beige": "stabilise",
           "enrobe_bbsg_ancien": "enrobe"}.get(mid)
    note = None
    if typ is None:
        if a.get("plante") or a.get("arbres") or not mats:
            typ, mid = "gazon", "gazon_tondu"
            note = "remplissage non dit : gazon (RF-OSM-VEG-002, terre-plein planté)"
    tp["remplissage"] = {"type": typ, "materiau_id": mid}
    if a.get("plante") or a.get("arbres") or typ == "gazon":
        strates = [{"type": "gazon"}]
        if a.get("arbres"):
            strates.append({"type": "arbre", "pas_m": regles.valeur("DEF-030", "entraxe")})
        tp["plantation"] = {"strates": strates,
                            "hauteur_max_visibilite_m": regles.valeur("RF-GV-TPC-011", "zone_hauteur")[0]}
    return tp, P.description(src, conf, regle="RF-OSM-VEG-002", note=note or "terre-plein décrit ; arbres au pas DEF-030, "
                                                                            "plafond de visibilité RF-GV-TPC-011")


# ================================================================================================ sections
def largeur_a(w, s):
    if isinstance(w, dict) and w.get("type") == "points":
        pts = w["points"]
        if s <= pts[0][0]:
            return pts[0][1]
        for (s0, w0), (s1, w1) in zip(pts, pts[1:]):
            if s <= s1:
                return w0 + (w1 - w0) * (s - s0) / (s1 - s0) if s1 > s0 else w1
        return pts[-1][1]
    return PF.nombre(w)


def t_limites(p: dict, s: float) -> list[float]:
    ws = [largeur_a(b["largeur"], s) for b in p["bandes"]]
    n = len(ws)
    k, dec = p["reference"]["limite"], p["reference"].get("decalage_m", 0.0)
    t = [0.0] * (n + 1)
    t[k] = -dec
    for i in range(k - 1, -1, -1):
        t[i] = t[i + 1] + ws[i]
    for i in range(k + 1, n + 1):
        t[i] = t[i - 1] - ws[i - 1]
    return t


class Troncon:
    """Un tronçon décrit : tracé, profil de base, modifications le long de s, décorations, objets."""

    def __init__(self, rid: str, trace: G.Trace, bandes, limites, ctx, chemin, conf):
        self.rid, self.trace, self.ctx, self.chemin, self.conf = rid, trace, ctx, chemin, conf
        self.L = trace.longueur
        PF.ids_bandes(bandes)
        self.base = bandes
        self.lim_base = {self._cle(bandes, i): l for i, l in enumerate(limites) if l is not None}
        self.mods: list[dict] = []
        self.decos: list[dict] = []
        self.marquages: list[dict] = []
        self.objets: list[dict] = []
        self.signaux: list[dict] = []
        self.zones: list[dict] = []
        self.av: list[str] = []
        self.ctrl: list[dict] = []
        self._apres: list = []
        self.abords_sans_largeur: dict = {}
        self.ilots: list[dict] = []
        self.non_portes: list[str] = []
        self.admis: dict = {}             # écarts aux règles admis par la description (ecarts_admis : règle -> motif)
        # largeur de chaussée de base (axe d'une route à sens unique : reste fixe le long du tronçon)
        p0, _, _ = PF.construire_profil("P-tmp", bandes, limites, ctx)
        self.profil_base = p0
        sens = {b["sens"] for b in bandes if b["type"] in PF.VOIES_MOTORISEES}
        self.sens_unique = not ({"avant", "arriere"} <= sens)
        self.dec_su = p0["reference"].get("decalage_m", 0.0) if self.sens_unique else None
        self.bord_ref = "gauche"          # bord de chaussée fixe d'une route à sens unique (RF-OSM-PRF-010)

    @staticmethod
    def _cle(bandes, i):
        a = bandes[i - 1]["id"] if i > 0 else None
        b = bandes[i]["id"] if i < len(bandes) else None
        return (a, b)

    # ------------------------------------------------------------------ variantes
    def _variante(self, a: float, b: float):
        act = [m for m in self.mods if m["s0"] <= a + 1e-9 and m["s1"] >= b - 1e-9]
        rempl = [m for m in act if m["op"] == "profil"]
        if rempl:
            m = max(rempl, key=lambda m: m["s0"])
            bl, limd = copy.deepcopy(m["bandes"]), m["lim"]
        else:
            bl, limd = copy.deepcopy(self.base), self.lim_base
        ordre = {"inserer": 0, "absente": 1, "remplacer": 2, "remplacer_largeur": 3, "loi": 4, "revetir": 5}
        for m in sorted((m for m in act if m["op"] != "profil"), key=lambda m: (ordre[m["op"]], m["s0"], m.get("bande", ""))):
            ids = [x["id"] for x in bl]
            if m["op"] == "inserer":
                if m["bande"]["id"] in ids:
                    continue
                if m.get("apres") in ids:
                    bl.insert(ids.index(m["apres"]) + 1, copy.deepcopy(m["bande"]))
                elif m.get("avant") in ids:
                    bl.insert(ids.index(m["avant"]), copy.deepcopy(m["bande"]))
                else:
                    raise ErreurDescription(f"{m['chemin']} : position d'insertion introuvable")
            elif m["op"] == "absente":
                if m["bande"] in ids:
                    bl.pop(ids.index(m["bande"]))
            elif m["op"] == "remplacer":
                if m["bande"] in ids:
                    x = bl[ids.index(m["bande"])]
                    for k in ("stationnement", "terre_plein", "cyclable", "objets_le_long", "materiau_id", "usagers"):
                        x.pop(k, None)
                    x["prov"] = {k: v for k, v in x["prov"].items() if k in ("*", "largeur", "sens")}
                    x["attributs"] = {}
                    x.update(copy.deepcopy(m["par"]))
            elif m["op"] == "remplacer_largeur":
                if m["bande"] in ids:
                    x = bl[ids.index(m["bande"])]
                    x["largeur"] = m["largeur"]
                    x["prov"]["largeur"] = m["prov"]
            elif m["op"] == "revetir":
                # refuge revêtu au droit d'un passage (correction après le contrôle de l'étape 2) : seul le revêtement
                # d'un terre-plein planté traversé change (largeur, niveau, bordures gardés) ; plantation retirée
                if m["bande"] in ids:
                    x = bl[ids.index(m["bande"])]
                    if x.get("type") == "terre_plein" and _plante(x):
                        x["materiau_id"] = m["materiau_id"]
                        tp = dict(x.get("terre_plein") or {})
                        tp.pop("plantation", None)
                        tp["remplissage"] = dict(m["remplissage"])
                        x["terre_plein"] = tp
                        x.pop("objets_le_long", None)
                        x["prov"] = dict(x.get("prov") or {}, materiau_id=m["prov"], terre_plein=m["prov"])
            elif m["op"] == "loi":
                if m["bande"] in ids:
                    x = bl[ids.index(m["bande"])]
                    f = lambda s: m["w0"] + (m["w1"] - m["w0"]) * (s - m["s0"]) / (m["s1"] - m["s0"])  # noqa: E731
                    x["largeur"] = {"type": "points", "interpolation": "lineaire",
                                    "points": [[_r(a), _r(f(a))], [_r(b), _r(f(b))]]}
                    x["prov"]["largeur"] = m["prov"]
        lims = [limd.get(self._cle(bl, i)) for i in range(len(bl) + 1)]
        # bordure décrite reportée sur la nouvelle paire de bandes quand une bande est insérée ou retirée contre elle
        # (rabattement : zébra inséré contre la bordure, voie supprimée) : la bordure reste attachée à sa bande haute
        # (côté haut), avec son caniveau et ses abaissés ; sans cela la limite était inférée de nouveau et perdait le
        # caniveau dit (constat du lot L2 sur S09 : caniveau de gauche absent de P-2 à P-4).
        par_id = {x["id"]: x for x in bl}
        par_id.update({x["id"]: x for x in self.base if x["id"] not in par_id})
        haute = lambda bid: bid in par_id and PF.cle_niveau(par_id[bid]) != "chaussee"  # noqa: E731
        for i, l in enumerate(lims):
            if l is not None:
                continue
            a, b = self._cle(bl, i)
            if a is None or b is None:
                continue
            for (ka, kb), lb in sorted(limd.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
                if not (lb or {}).get("bordure") or (ka, kb) == (a, b):
                    continue
                if (ka == a and kb != b and haute(ka) and not haute(kb)) or \
                   (kb == b and ka != a and haute(kb) and not haute(ka)):
                    lims[i] = copy.deepcopy(lb)
                    break
        # bordure décrite pour le profil de base : tolérée là où une bande voisine est remplacée (avancée, quai…)
        remplacees = {m["bande"] for m in act if m["op"] == "remplacer"}
        for i, l in enumerate(lims):
            if l is not None and "bordure" in l:
                k = self._cle(bl, i)
                if k[0] in remplacees or k[1] in remplacees:
                    lims[i] = dict(l, tolerante=True)
        return bl, lims

    def sections(self):
        pts = sorted({0.0, self.L} | {min(max(m[k], 0.0), self.L) for m in self.mods for k in ("s0", "s1")})
        pts = [p for i, p in enumerate(pts) if i == 0 or p - pts[i - 1] > 1e-6]
        brut = []
        for a, b in zip(pts, pts[1:]):
            bl, lims = self._variante(a, b)
            cle = json.dumps([bl, lims], sort_keys=True, ensure_ascii=False, default=str)
            loi = any(isinstance(x["largeur"], dict) for x in bl)
            if brut and brut[-1]["cle"] == cle and not loi:
                brut[-1]["s1"] = b
            else:
                brut.append({"s0": a, "s1": b, "bandes": bl, "lims": lims, "cle": cle})
        return brut

    # ------------------------------------------------------------------ construction
    def construire(self, num_profil: list[int]):
        """Profils et sections. num_profil : compteur partagé entre tronçons (identifiants P-n uniques)."""
        self.profils, self.secs = [], []
        connus = {}
        for sec in self.sections():
            p, av, ctrl = PF.construire_profil("P-tmp", sec["bandes"], sec["lims"], self.ctx,
                                               decalage_sens_unique=self.dec_su if self.bord_ref == "gauche" else -self.dec_su,
                                               bord_reference=self.bord_ref)
            ids_p = [b["id"] for b in p["bandes"]]
            k_axe = next((k for k, b in enumerate(ids_p) if b.endswith(AXE_G) and k + 1 < len(ids_p)
                          and ids_p[k + 1] == b[:-len(AXE_G)] + AXE_D), None)
            if k_axe is not None:
                # ouverture d'une bande centrale (lot « scenes ») : séparation des sens entre les deux demi-bandes
                p["reference"] = {"limite": k_axe + 1}
                p["prov"]["reference"] = P.inference("RF-OSM-PRF-010", note="séparation des sens au milieu de la bande "
                                                                            "centrale qui s'ouvre (deux demi-bandes)")
            for w in av:
                if w not in self.av:
                    self.av.append(w)
            if getattr(self, "raccords", None) and _dans_raccord(self, sec["s0"], sec["s1"]):
                ctrl = [dict(c, statut=c["statut"] + "_raccord", note_raccord="profil de transition d'un raccord de "
                             "réseau (lot N1) : non bloquant") if c.get("statut") in ("non_conforme", "hors_plage") else c
                        for c in ctrl]
            for c in ctrl:
                if c not in self.ctrl:
                    self.ctrl.append(c)
            cle = json.dumps(p, sort_keys=True, ensure_ascii=False)
            if cle not in connus:
                num_profil[0] += 1
                p["id"] = f"P-{num_profil[0]}"
                p["nom"] = f"{self.rid} : {resume_profil(p)}"
                connus[cle] = p
                self.profils.append(p)
            sortie = {"s0": sec["s0"], "s1": sec["s1"], "profil": connus[cle]["id"]}
            if self.secs and any(m["op"] == "profil" and m.get("instantane") and abs(m["s0"] - sec["s0"]) < 1e-6
                                 for m in self.mods):
                sortie["transition_entree"] = {"type": "instantanee"}
            self.secs.append(sortie)
        self._decorer()

    def profil_a(self, s: float) -> dict:
        for sec in self.secs:
            if s <= sec["s1"] + 1e-9:
                return next(p for p in self.profils if p["id"] == sec["profil"])
        return self.profils[-1]

    def _intervalles(self, pid):
        return [(s["s0"], s["s1"]) for s in self.secs if s["profil"] == pid]

    def _decorer(self):
        # deux passes : marques (lignes de remplacement : annonce, axe T3 du dos-d'âne...) puis interruptions, pour qu'une
        # interruption d'obstacle (passage piéton, RF-MQ-PP-03 : « les lignes » à 0,50 m) coupe aussi une marque de
        # remplacement qui le chevauche, quel que soit l'ordre des évènements (lot L2b : l'axe T3 du dos-d'âne de S08
        # traversait le passage) ; une interruption « autre » (remplacement de modulation) ne vise que la ligne de base
        for p in self.profils:
            iv = self._intervalles(p["id"])
            for passe in ("abaisse_marque", "interruption"):
                for d in self.decos:
                    if not any(d["s0"] < b + 1e-9 and d["s1"] > a - 1e-9 for a, b in iv):
                        continue
                    if (d["type"] == "interruption") != (passe == "interruption"):
                        continue
                    if d["type"] == "abaisse" and d.get("passage") is not None:
                        # passage piéton : abaissés sur les seules bordures de sa traversée (aboutissements, refuges,
                        # bordures franchies) ; BEV à l'aboutissement et sur le refuge (correction après second contrôle)
                        for i, bev in self._limites_passage(p, iv, d):
                            lim = p["limites"][i]
                            ab = dict(d["abaisse"], bev=bool(d["abaisse"].get("bev")) and bev,
                                      s0=_r(max(d["s0"], 0.0)), s1=_r(min(d["s1"], self.L)))
                            lst = lim["bordure"].setdefault("abaisses", [])
                            if ab not in lst:
                                lst.append(ab)
                        continue
                    for i in cibles(p, d["cible"]):
                        lim = p["limites"][i]
                        if d["type"] == "abaisse" and "bordure" in lim["nature"]:
                            ab = dict(d["abaisse"], s0=_r(max(d["s0"], 0.0)), s1=_r(min(d["s1"], self.L)))
                            lst = lim["bordure"].setdefault("abaisses", [])
                            if ab not in lst:
                                lst.append(ab)
                        elif d["type"] == "interruption" and "marquage" in lim["nature"]:
                            for m in lim["marquages"]:
                                ivm = m.get("intervalle")
                                if ivm is not None and (d["motif"] == "autre" or not (
                                        d["s0"] < ivm["s1"] - 1e-9 and d["s1"] > ivm["s0"] + 1e-9)):
                                    continue
                                it = {"s0": _r(max(d["s0"], 0.0)), "s1": _r(min(d["s1"], self.L)), "motif": d["motif"]}
                                lst = m.setdefault("interruptions", [])
                                if it not in lst:
                                    lst.append(it)
                        elif d["type"] == "marque" and "marquage" in lim["nature"]:
                            m = dict(d["marque"], intervalle={"s0": _r(max(d["s0"], 0.0)), "s1": _r(min(d["s1"], self.L))})
                            if m not in lim["marquages"]:
                                lim["marquages"].append(m)
            for lim in p["limites"]:
                if lim.get("bordure", {}).get("abaisses"):
                    lim["bordure"]["abaisses"].sort(key=lambda x: (x["s0"], x["type"]))
                for m in lim.get("marquages", []):
                    if m.get("interruptions"):
                        m["interruptions"].sort(key=lambda x: (x["s0"], x["motif"]))

    def _limites_passage(self, p, iv, d):
        """[(limite, bev)] des bordures du profil p qui reçoivent l'abaissé du passage d (évènement « passage »).
        Profil qui recouvre le passage sur une longueur non nulle : traversée calculée dans ce profil (traversee_passage).
        Profil qui le touche seulement (jonction de section au bord du passage) : mêmes bordures retrouvées par leur
        position t à la jonction, sans BEV (seuls les rampants de l'abaissé s'y prolongent)."""
        s0, s1 = d["s0"], d["s1"]
        ov = [(min(b, s1) - max(a, s0), a, b) for a, b in iv]
        lg, a, b = max(ov)
        if lg > 1e-6:
            tp = traversee_passage(p, 0.5 * (max(a, s0) + min(b, s1)))
            if tp is None:
                return []
            vus, out = set(), []
            for lim, bev, _role in tp["abaisses"]:
                if lim not in vus:
                    vus.add(lim)
                    out.append((lim, bev))
            return out
        # jonction : profil voisin qui porte le passage
        sj = b if abs(b - s0) < 1e-6 else a
        q = self.profil_a(0.5 * (s0 + s1))
        if q is p:
            return []
        tq = traversee_passage(q, 0.5 * (s0 + s1))
        if tq is None:
            return []
        Tq, Tp = t_limites(q, sj), t_limites(p, sj)
        out = []
        for lim, _bev, _role in tq["abaisses"]:
            for i in range(1, len(p["bandes"])):
                if "bordure" in p["limites"][i]["nature"] and abs(Tp[i] - Tq[lim]) < 0.01 and (i, False) not in out:
                    out.append((i, False))
        return out

    # ------------------------------------------------------------------ outils géométriques
    def xy(self, s, t):
        x, y = self.trace.point_st(s, t)
        return [_r(x), _r(y)]

    def cap_deg(self, s, sens="avant"):
        c = math.degrees(self.trace.point(s)[2])
        return _r((c + (180.0 if sens == "arriere" else 0.0)) % 360.0)

    def chaussees(self, s):
        """[(t_gauche, t_droite, [indices des bandes])] des groupes de chaussée au droit de s (profil construit)."""
        p = self.profil_a(s)
        t = t_limites(p, s)
        out, cur = [], []
        for i, b in enumerate(p["bandes"]):
            if b["niveau"]["reference"] == "chaussee":
                cur.append(i)
            elif cur:
                out.append(cur)
                cur = []
        if cur:
            out.append(cur)
        return [(t[g[0]], t[g[-1] + 1], g) for g in out], p, t


def cibles(p: dict, cible) -> list[int]:
    """Indices des limites visées par une décoration. Les côtés se jugent sur la position t de chaque limite
    (largeurs courantes) : à droite t < 0, à gauche t > 0, de l'axe vers l'extérieur."""
    lims, bandes = p["limites"], p["bandes"]
    n = len(bandes)
    k = p["reference"]["limite"]
    if cible == "bordures":
        return [i for i in range(1, n) if "bordure" in lims[i]["nature"]]
    if cible == "lignes":
        return [i for i in range(1, n) if "marquage" in lims[i]["nature"]]
    if cible == "axe":
        return [k] if 0 < k < n and "marquage" in lims[k]["nature"] and {bandes[k - 1]["sens"], bandes[k]["sens"]} == {"avant", "arriere"} else []
    kind, cote = cible
    if kind == "limite_bande":
        ids = [b["id"] for b in bandes]
        if cote not in ids:
            return []
        j = ids.index(cote)
        tt = t_limites(p, -1e9)
        i = j if abs(tt[j]) < abs(tt[j + 1]) else j + 1          # limite la plus proche de l'axe
        return [i] if "marquage" in lims[i]["nature"] else []
    if kind == "limite_bande_ext":
        # limite de la bande la plus éloignée de l'axe (bord extérieur d'une demi-bande centrale)
        ids = [b["id"] for b in bandes]
        if cote not in ids:
            return []
        j = ids.index(cote)
        tt = t_limites(p, -1e9)
        i = j + 1 if abs(tt[j + 1]) >= abs(tt[j]) else j
        return [i] if 0 < i < n and "marquage" in lims[i]["nature"] else []
    t = t_limites(p, -1e9)              # largeurs au début de chaque loi
    if cote == "droite":
        rng = sorted((i for i in range(n + 1) if t[i] < -1e-9), key=lambda i: -t[i])
    else:
        rng = sorted((i for i in range(n + 1) if t[i] > 1e-9), key=lambda i: t[i])
    if kind == "bordure":
        return [i for i in rng if 0 < i < n and "bordure" in lims[i]["nature"]][:1]
    if kind == "cyclable":
        return [i for i in rng if 0 < i < n and "marquage" in lims[i]["nature"]
                and "bande_cyclable" in (bandes[i - 1]["type"], bandes[i]["type"])][:1]
    if kind == "rive":
        return [i for i in rng if "marquage" in lims[i]["nature"]
                and lims[i]["marquages"][0].get("regle") in ("RF-OSM-MRQ-021", "RF-OSM-MRQ-022")][:1]
    return []


# bandes traversées par un passage piéton (peintes : chaussée, zone neutralisée, stationnement neutralisé, accotement
# revêtu, piste), surfaces piétonnes où il aboutit, éléments franchis sans peinture
PASSAGE_TRAVERSEES = PF.TYPES_CHAUSSEE | {"piste_cyclable"}
PASSAGE_ABOUTISSEMENTS = PF.TYPES_PIETONS | {"voie_verte"}
PASSAGE_FRANCHIS = {"separateur"}


def traversee_passage(p: dict, s: float) -> dict | None:
    """Traversée d'un passage piéton dans le profil p au droit de s (correction après le second contrôle de l'étape 1 :
    les abaissés étaient posés sur toutes les bordures du profil, d'où des BEV dans les bandes plantées de S_M20 et S_M27,
    et les bandes peintes jusque sur le trottoir de S_M27). Des voies motorisées vers l'extérieur, de chaque côté :
    bandes traversées (chaussée, zone neutralisée, stationnement neutralisé, accotement revêtu, piste) jusqu'à la
    première surface piétonne (trottoir, chemin, quai, voie verte) = aboutissement ; entre les voies, un terre-plein est
    un refuge. Abaissés : bordure de l'aboutissement (BEV côté piéton, DEF-031, RF-MA-BEV-002), bordures du refuge (BEV,
    RF-MA-REF-003), bordure franchie entre deux bandes traversées (piste haute : sans BEV). Une berme, une bande plantée,
    un terre-plein extérieur ou le bord du profil avant toute surface piétonne : obstacle (passage refusé par
    _passage_controles). Renvoie None sans voie motorisée."""
    bandes, lims = p["bandes"], p["limites"]
    n = len(bandes)
    mot = [i for i, b in enumerate(bandes) if b["type"] in PF.VOIES_MOTORISEES]
    if not mot:
        return None
    i0, i1 = min(mot), max(mot)

    def bord(i):
        return 0 < i < n and "bordure" in lims[i]["nature"]
    ab, peintes, refuges, milieu = [], [], [], []
    for i in range(i0, i1 + 1):
        t = bandes[i]["type"]
        if t == "terre_plein":
            refuges.append(i)
            for lim in (i, i + 1):
                if bord(lim):
                    ab.append((lim, True, "refuge"))
        elif t in PASSAGE_TRAVERSEES:
            peintes.append(i)
        elif t not in PASSAGE_FRANCHIS:
            milieu.append((i, t))
    cotes = {}
    for cote, rng, lim_de in (("gauche", range(i0 - 1, -1, -1), lambda j: j + 1), ("droite", range(i1 + 1, n), lambda j: j)):
        c = {"traversees": [], "aboutissement": None, "type": None, "limite": None, "bordure": False, "obstacle": None}
        for j in rng:
            t, lj = bandes[j]["type"], lim_de(j)
            if t in PASSAGE_ABOUTISSEMENTS:
                c.update(aboutissement=j, type=t, limite=lj, bordure=bord(lj))
                if bord(lj):
                    ab.append((lj, True, "aboutissement"))
                break
            if t in PASSAGE_TRAVERSEES or t in PASSAGE_FRANCHIS:
                if bord(lj):
                    ab.append((lj, False, "franchie"))
                if t in PASSAGE_TRAVERSEES:
                    c["traversees"].append(j)
                    peintes.append(j)
                continue
            c["obstacle"] = (j, t)
            break
        else:
            c["obstacle"] = (None, "bord du profil")
        cotes[cote] = c
    peintes.sort()
    groupes = []
    for j in peintes:                       # bandes peintes contiguës, sans bordure entre elles
        if groupes and groupes[-1][-1] == j - 1 and not bord(j):
            groupes[-1].append(j)
        else:
            groupes.append([j])
    return {"cotes": cotes, "refuges": refuges, "abaisses": ab, "peintes": peintes, "groupes_peints": groupes,
            "milieu": milieu}


def resume_profil(p: dict) -> str:
    morceaux = []
    for b in p["bandes"]:
        s = {"avant": " →", "arriere": " ←"}.get(b["sens"], "")
        w = b["largeur"]
        ws = f"{PF.nombre(w):.2f}" if not isinstance(w, dict) else f"{w['points'][0][1]:.2f}→{w['points'][-1][1]:.2f}"
        morceaux.append(f"{b['type']} {ws}{s}")
    return " | ".join(morceaux)


# ================================================================================================ évènements
def lire_evenements(liste, chemin: str) -> list[dict]:
    out = []
    for i, e in enumerate(liste or []):
        c = f"{chemin}[{i}]"
        if isinstance(e, str):
            out.append(evenement_texte(e, c))
            continue
        if not isinstance(e, dict):
            raise ErreurDescription(f"{c} : évènement illisible")
        if len(e) == 1:
            (k, v), = e.items()
            if k.startswith("a_") and k[2:].replace("_", "").isdigit():      # « - à 45: passage piéton » sans guillemets
                out.append(evenement_texte(f"à {k[2:].replace('_', '.')} : {v}", c))
                continue
            if k in V.CLES_EVENEMENTS:
                params = dict(v) if isinstance(v, dict) else ({} if v in (None, True) else {"a": v})
                if k == "fleches" and "type" in params:
                    params["type_fleche"] = params.pop("type")
                if k == "inscription" and "texte" in params:
                    params["texte_sol"] = params.pop("texte")
                verifier_cles(params, PARAMS[k] | {"a"}, c)
                out.append(dict(params, type=k, chemin=c))
                continue
        typ = e.get("type")
        if typ is not None and V.norm_cle(typ) in V.CLES_EVENEMENTS:
            out.append(dict(e, type=V.norm_cle(typ), chemin=e.get("_chemin") or c))
            continue
        raise ErreurDescription(f"{c} : type d'évènement inconnu ({', '.join(sorted(V.CLES_EVENEMENTS))})")
    for e in out:
        if "a" not in e:
            raise ErreurDescription(f"{e['chemin']} : abscisse « à: S » manquante")
        e["a"] = V.nombre(e["a"], e["chemin"] + ".a")
    return sorted(out, key=lambda e: (e["a"], e["type"], e["chemin"]))


def evenement_texte(txt: str, c: str) -> dict:
    """« à 45 : passage piéton 4 m », « 80 : dos-d'âne », « à 200 : rabattement → voie gauche biseau 60 »."""
    import re
    s = V.norm(txt)
    m = re.match(r"^(?:a\s+)?(\d+(?:\.\d+)?)\s*m?\s*:\s*(.+)$", s)
    if not m:
        raise ErreurDescription(f"{c} : forme « à S : évènement » attendue, lu « {txt} »")
    toks = m.group(2).split(" ")
    cle, n = V.correspondance(toks, 0, V.EVENEMENTS)
    if not cle:
        raise ErreurDescription(f"{c} : évènement inconnu dans « {txt} »")
    e = {"type": V.EVENEMENTS[cle], "a": float(m.group(1)), "chemin": c, "texte": txt}
    reste, i = toks[n:], 0
    while i < len(reste):
        t = reste[i]
        if t in V.SENS:
            e["sens"] = t
        elif t in ("gauche", "droite"):
            e["cote" if e["type"] not in ("rabattement", "elargissement") else "voie"] = t
        elif t in ("biseau", "largeur", "longueur", "quai", "pas") and i + 1 < len(reste):
            e[t] = reste[i + 1]
            i += 1
        elif V.NOMBRE.match(t):
            e.setdefault("largeur" if e["type"] in ("passage_pieton", "entree_charretiere", "abaisse") else "longueur", t)
        elif t in ("avec", "passage", "pieton", "pietons") and e["type"] == "plateau":
            e["passage_pieton"] = True
        elif t in ("abri",):
            e["abri"] = True
        elif t in ("articule",):
            e["articule"] = True
        elif t in V.MOTS_VIDES or t in ("m", "voie", "voies", "cote"):
            pass
        elif e["type"] == "panneau" and "code" not in e:
            mm = re.match(r"^([a-z]+)(.*)$", t)               # c20a → C20a, ab3a → AB3a, m9v2 → M9v2
            e["code"] = (mm.group(1).upper() + mm.group(2)) if mm else t.upper()
        else:
            raise ErreurDescription(f"{c} : mot inconnu « {t} » dans « {txt} »")
        i += 1
    return e


def _cote(e, defaut="droite"):
    c = V.norm(e.get("cote", defaut)) if e.get("cote") is not None else defaut
    if c not in ("gauche", "droite", "deux", "les deux"):
        raise ErreurDescription(f"{e['chemin']} : côté « gauche » ou « droite » attendu")
    return c


def appliquer_evenements(tr: Troncon, evs: list[dict], d: dict):
    ctx = tr.ctx
    for e in evs:
        f = {"passage_pieton": ev_passage, "plateau_pieton": ev_plateau, "plateau": ev_plateau, "dos_d_ane": ev_dos_d_ane,
             "coussin": ev_coussin, "rabattement": ev_rabattement, "elargissement": ev_elargissement,
             "arret_bus": ev_arret_bus, "entree_charretiere": ev_charretiere, "abaisse": ev_abaisse,
             "panneau": ev_panneau, "profil": ev_profil, "zone_depassement_interdit": ev_zone_continue,
             "fleches": ev_fleches, "inscription": ev_inscription, "ouverture": ev_ouverture,
             "fermeture": ev_fermeture}[e["type"]]
        if e["type"] == "plateau_pieton":
            e["passage_pieton"] = True
        if not (0 <= e["a"] <= tr.L + 1e-6):
            raise ErreurDescription(f"{e['chemin']} : à = {e['a']} hors du tronçon [0 ; {tr.L:.2f}]")
        f(tr, e)
    chevauchements(evs)
    # contrôles croisés : passage piéton sur un dos-d'âne
    dos = [e for e in evs if e["type"] == "dos_d_ane"]
    for e in evs:
        if e["type"] == "passage_pieton":
            for x in dos:
                if abs(x["a"] - e["a"]) < regles.valeur("RF-MA-RAL-001", "dos_d_ane.longueur") / 2 + 2.0:
                    raise ErreurDescription(f"{e['chemin']} : passage piéton sur un dos-d'âne ({x['chemin']}), interdit "
                                            "(RF-MA-RAL-001 : passage obligatoire sur un ralentisseur trapézoïdal, interdit "
                                            "sur un dos-d'âne) : décrire un plateau avec passage piéton")


RALENTISSEURS = ("dos_d_ane", "plateau", "plateau_pieton", "coussin")


def chevauchements(evs: list[dict]):
    """Deux évènements de même nature dont les emprises se chevauchent, ou deux ralentisseurs qui se chevauchent : la
    description est incohérente (le second effacerait ou doublerait le premier) ; erreur, jamais une fusion muette.
    Emprises : passage (bandes, DEF-011), dos-d'âne (longueur), plateau (plateau + rampes), coussin (longueur),
    quai d'arrêt de bus, entrée charretière et abaissé (largeur). Un plateau avec passage compte aussi comme passage."""
    def nature(e):
        return "ralentisseur" if e["type"] in RALENTISSEURS else e["type"]

    def emprises(e):
        out = []
        if e.get("_s0") is not None:
            out.append((nature(e), e["_s0"], e["_s1"]))
        if e.get("_pp_s0") is not None:
            out.append(("passage_pieton", e["_pp_s0"], e["_pp_s1"]))
        return out
    vus = []
    for e in evs:
        for nat, a, b in emprises(e):
            for (n2, a2, b2, e2) in vus:
                if nat == n2 and min(b, b2) - max(a, a2) > 1e-6:
                    quoi = "deux ralentisseurs" if nat == "ralentisseur" else f"deux évènements « {nat} »"
                    raise ErreurDescription(f"{e['chemin']} [{a:.2f} ; {b:.2f}] chevauche {e2['chemin']} [{a2:.2f} ; "
                                            f"{b2:.2f}] : {quoi} ne peuvent pas se superposer")
            vus.append((nat, a, b, e))


def _bande_cote(bl, cote, types):
    """Indices des bandes de `types` du côté `cote` de la séparation des sens / de l'axe, de la chaussée vers l'extérieur."""
    mot = [i for i, b in enumerate(bl) if b["type"] in PF.VOIES_MOTORISEES]
    if not mot:
        return []
    if cote == "droite":
        return [i for i in range(max(mot) + 1, len(bl)) if bl[i]["type"] in types]
    return [i for i in range(min(mot) - 1, -1, -1) if bl[i]["type"] in types]


def _prov_ev(e, champ=None, regle=None, note=None, conf=None):
    return P.description(e["chemin"] + (f".{champ}" if champ else ""), conf or "moyenne", regle=regle, note=note)


def _largeur_resolue(tr: Troncon, b: dict):
    if b["largeur"] is not None:
        return b["largeur"], b["prov"]["largeur"]
    return PF.largeur_defaut(b, tr.base, tr.ctx)


REMPLISSAGES_PLANTES = {"plante", "gazon", "brf", "terre", "paillage_mineral", "galets", "gravier"}


def _plante(b) -> bool:
    """Terre-plein meuble ou planté (gazon, massif, paillage, terre, galets, gravier) : ni béton, ni enrobé, ni pavés."""
    r = ((b.get("terre_plein") or {}).get("remplissage") or {}).get("type")
    return r in REMPLISSAGES_PLANTES or str(b.get("materiau_id", "")).startswith(("gazon", "herbe", "terre", "brf"))


def _revetir_refuges(tr: Troncon, s0, s1, e):
    """Refuge revêtu au droit d'un passage qui traverse un terre-plein planté (correction après le contrôle de l'étape 2 :
    les refuges des TPC plantés de J5 restaient en gazon, BEV posées sur l'herbe). Le passage coupe l'îlot à niveau et
    l'îlot est revêtu au droit de la traversée (RF-OBS-ILO-01, observations d'Isère M24, M29, I10 ; cheminement non
    meuble) : chaque terre-plein planté situé entre les voies motorisées (refuge) prend sur [s0, s1] (passage, rampants
    compris) le revêtement des îlots revêtus du générateur (béton balayé, comme les îlots du cœur des carrefours)."""
    bl, _ = tr._variante(max(s0, 0.0), min(s1, tr.L))
    mot = [i for i, b in enumerate(bl) if b["type"] in PF.VOIES_MOTORISEES]
    if not mot:
        return []
    faits = []
    for i in range(min(mot) + 1, max(mot)):
        b = bl[i]
        if b["type"] != "terre_plein" or not _plante(b):
            continue
        tr.mods.append({"op": "revetir", "s0": max(s0, 0.0), "s1": min(s1, tr.L), "bande": b["id"], "chemin": e["chemin"],
                        "materiau_id": "beton_balaye", "remplissage": {"type": "beton", "materiau_id": "beton_balaye"},
                        "prov": P.inference("RF-OBS-ILO-01", note=f"refuge revêtu au droit du passage {e['chemin']} "
                                                                  f"(s = {s0:.2f} à {s1:.2f}, rampants compris) : le "
                                                                  "passage coupe l'îlot à niveau, surface revêtue")})
        faits.append(b["id"])
    return faits


def _neutraliser(tr: Troncon, s0, s1, cote, e, regle):
    """Stationnement du côté `cote` → zone neutralisée sur [s0, s1]."""
    for i in _bande_cote(tr.base, cote, ("stationnement", "livraison")):
        b = tr.base[i]
        w, pw = _largeur_resolue(tr, b)
        tr.mods.append({"op": "remplacer", "s0": max(s0, 0.0), "s1": min(s1, tr.L), "bande": b["id"], "chemin": e["chemin"],
                        "par": {"type": "zone_neutralisee", "sous_type": "neutralisation_stationnement", "sens": "aucun",
                                "largeur": w, "prov": {"largeur": pw, "*": P.defaut(regle, note=f"stationnement neutralisé ({e['chemin']})")}}})


def ev_passage(tr: Troncon, e):
    ctx, s = tr.ctx, e["a"]
    if e.get("_prov_largeur") is not None:
        w, pw = e["largeur"], e["_prov_largeur"]
    elif e.get("largeur") is not None:
        w, pw = V.nombre(e["largeur"], e["chemin"]), _prov_ev(e, "largeur", regle="RF-MQ-PP-01")
    else:
        w, pw = regles.valeur("DEF-011", "longueur_bandes_ville"), P.defaut("DEF-011", note="longueur des bandes du passage")
    if w < regles.valeur("RF-MQ-PP-01", "longueur_ville_min") - 1e-9:
        tr.av.append(f"{e['chemin']} : passage de {w} m < {regles.valeur('RF-MQ-PP-01', 'longueur_ville_min')} m (RF-MQ-PP-01)")
    s0, s1 = s - w / 2, s + w / 2
    e["_s0"], e["_s1"] = s0, s1
    if e.get("_plateau") is not None:            # passage porté par un plateau : emprise notée aussi sur le plateau
        e["_plateau"]["_pp_s0"], e["_plateau"]["_pp_s1"] = s0, s1
    # neutralisation du stationnement en amont (5 m, RF-OSM-STA-002 / DEF-009) et au droit du passage
    neut = regles.valeur("DEF-009", "neutralisation_avant_passage")
    _neutraliser(tr, s0 - neut, s1, "droite", e, "RF-OSM-STA-002")
    _neutraliser(tr, s0, s1 + neut, "gauche", e, "RF-OSM-STA-002")
    # abaissés + BEV sur les bordures de la traversée (DEF-031) : aboutissements sur la première surface piétonne de
    # chaque côté, refuges, bordures franchies (traversee_passage ; avant le second contrôle : toutes les bordures du
    # profil, d'où des BEV dans les bandes plantées)
    e["_bev"] = V.booleen(e.get("bev", "oui"), e["chemin"] + ".bev")
    if V.booleen(e.get("abaisses", "oui"), e["chemin"] + ".abaisses"):
        pr = V.nombre(e.get("pente_rampants_pct", 5), e["chemin"] + ".pente_rampants_pct")
        if pr not in (5.0, 8.0):
            raise ErreurDescription(f"{e['chemin']}.pente_rampants_pct : 5 ou 8 % (DEF-031, RF-MA-ABA-004)")
        ab = {"type": "traversee", "vue_m": regles.valeur("DEF-031", "vue"),
              "rampant_m": regles.valeur("DEF-031", "rampant_5pct" if pr == 5.0 else "rampant_8pct"),
              "bev": e["_bev"], "regle": "DEF-031"}
        tr.decos.append({"type": "abaisse", "s0": s0, "s1": s1, "cible": "bordures", "abaisse": ab, "passage": s})
        e["_refuges_revetus"] = _revetir_refuges(tr, s0 - ab["rampant_m"], s1 + ab["rampant_m"], e)
    else:
        e["_refuges_revetus"] = _revetir_refuges(tr, s0, s1, e)
    tr._apres.append(lambda: _passage_controles(tr, e))
    # interruption des lignes longitudinales à 0,50 m (RF-MQ-PP-03)
    dg = regles.valeur("RF-MQ-PP-03", "distance")
    tr.decos.append({"type": "interruption", "s0": s0 - dg, "s1": s1 + dg, "cible": "lignes", "motif": "passage_pieton"})
    e["_marque"] = {"largeur": w, "prov_largeur": pw}
    tr._apres.append(lambda: _passage_marquage(tr, e))
    if e.get("panneau") is not None and V.booleen(e["panneau"], e["chemin"] + ".panneau"):
        for cote in ("droite", "gauche"):
            ev_panneau(tr, {"a": s0 if cote == "droite" else s1, "code": "C20a", "cote": cote, "chemin": e["chemin"],
                            "_regle": "RF-MA-PP-008"})


def _passage_controles(tr: Troncon, e):
    """Cohérence de la traversée (correction après le second contrôle) dans chaque profil qui recouvre le passage : de
    chaque côté, la traversée doit aboutir sur une surface piétonne (trottoir, chemin, quai, voie verte) par des bandes
    revêtues ; une berme, une bande plantée, un terre-plein extérieur ou le bord du profil avant toute surface piétonne
    refusent la description (décrire la traversée revêtue au droit du passage par un évènement « profil », ou déplacer le
    passage). Un aboutissement de plain-pied (sans bordure) ne peut pas recevoir la BEV (le schéma 0.1 la porte par
    l'abaissé d'une bordure) : interdit RF-MA-BEV-001 (BEV obligatoire aux traversées matérialisées), admissible."""
    s0, s1 = e["_s0"], e["_s1"]
    vus = set()
    for sec in tr.secs:
        a, b = max(sec["s0"], s0), min(sec["s1"], s1)
        if b - a <= 1e-6:
            continue
        p = next(x for x in tr.profils if x["id"] == sec["profil"])
        tp = traversee_passage(p, 0.5 * (a + b))
        if tp is None:
            continue
        for i, t in tp["milieu"]:
            raise ErreurDescription(f"{e['chemin']} : le passage traverse « {t} » ({p['bandes'][i]['id']}) entre les voies "
                                    f"(profil {p['id']}, s = {a:.2f} à {b:.2f}) : ni chaussée ni refuge")
        for cote, c in tp["cotes"].items():
            if c["obstacle"] is not None:
                j, t = c["obstacle"]
                quoi = f"« {t} » ({p['bandes'][j]['id']})" if j is not None else "le bord du profil"
                raise ErreurDescription(
                    f"{e['chemin']} : côté {cote}, le passage aboutit sur {quoi} avant toute surface piétonne (profil "
                    f"{p['id']}, s = {a:.2f} à {b:.2f}) ; décrire la traversée revêtue au droit du passage (évènement "
                    f"« profil » : chemin ou trottoir à la place de la bande) ou déplacer le passage")
            if e.get("_bev") and not c["bordure"] and (cote, p["id"]) not in vus:
                vus.add((cote, p["id"]))
                interdit(tr, e, "RF-MA-BEV-001", "bev_aboutissement_de_plain_pied",
                         f"côté {cote}, le passage aboutit de plain-pied sur « {c['type']} » "
                         f"({p['bandes'][c['aboutissement']]['id']}, sans bordure) : pas de BEV possible (le schéma 0.1 "
                         "porte la BEV par l'abaissé d'une bordure)",
                         {"cote": cote, "profil": p["id"], "aboutissement": c["type"]})
        tr.ctrl.append({"controle": "passage_traversee", "evenement": e["chemin"], "profil": p["id"],
                        "valeur": {cote: {"aboutissement": c["type"], "bordure": c["bordure"],
                                          "traversees": [p["bandes"][j]["id"] for j in c["traversees"]]}
                                   for cote, c in tp["cotes"].items()},
                        "regle": "DEF-031", "statut": "conforme"})


def _passage_marquage(tr: Troncon, e):
    s, s0, s1 = e["a"], e["_s0"], e["_s1"]
    p = tr.profil_a(s)
    t = t_limites(p, s)
    tp = traversee_passage(p, s)
    # bandes peintes : groupes contigus de bandes traversées (chaussée, zone neutralisée, accotement revêtu, piste),
    # jamais sur un trottoir, un chemin, une berme ou une bande plantée (correction après le second contrôle ; avant :
    # groupes au niveau de la chaussée, trottoir « niveau chaussée » de S_M27 compris)
    if tp is not None:
        groupes = [(t[g[0]], t[g[-1] + 1], g) for g in tp["groupes_peints"]]
    else:
        groupes, p, t = tr.chaussees(s)
    # un terre-plein traversé est un refuge : largeur ≥ DEF-022 (RF-MA-REF-001), bordure ≥ DEF-005 refuge_min (RF-MA-REF-003)
    for j, bd in enumerate(p["bandes"]):
        if bd["type"] != "terre_plein" or not (j in (tp or {}).get("refuges", []) or (
                tp is None and t[j] > min(tg for tg, _, _ in groupes[-1:]) and t[j + 1] < max(tg for tg, _, _ in groupes[:1]))):
            continue
        lr = largeur_a(bd["largeur"], s)
        vue = bd["niveau"]["dz_m"]
        for ctl, val, seuil, regle in (("refuge_largeur", lr, regles.valeur("DEF-022", "largeur"), "DEF-022"),
                                       ("refuge_vue_bordure", vue, regles.valeur("DEF-005", "refuge_min"), "RF-MA-REF-003")):
            ok = val >= seuil - 1e-9
            tr.ctrl.append({"controle": ctl, "evenement": e["chemin"], "bande": bd["id"], "valeur": _r(val, 3), "plage": [seuil, None],
                            "regle": regle, "statut": "conforme" if ok else "non_conforme"})
            if not ok:
                tr.av.append(f"{e['chemin']} : le terre-plein {bd['id']} traversé sert de refuge : {ctl} = {val:.2f} < {seuil} ({regle})")
    for k, (tg, td, g) in enumerate(groupes):
        ext = [tr.xy(x, tg) for x in (s0, s, s1)] + [tr.xy(x, td) for x in (s1, s, s0)]
        ext.append(ext[0])
        mid = f"M-{tr.rid[2:]}.{len(tr.marquages) + 1}"
        tr.marquages.append({
            "id": mid, "type": "passage_pieton", "ancrage": {"route": tr.rid, "s": _r(s), "t": _r((tg + td) / 2)},
            "geometrie": {"exterieur": ext}, "couleur": "blanc",
            "regles": ["RF-MQ-PP-01", "RF-MQ-PP-02", "RF-MQ-PP-05", "DEF-011"],
            "x-opendrive": {"object_type": "crosswalk"},
            "prov": {"*": _prov_ev(e), "largeur": e["_marque"]["prov_largeur"],
                     "geometrie": P.solveur("passage", regle="RF-MQ-PP-05",
                                            note=f"largeur roulable {tg - td:.2f} m ; bandes de 0,50 m, n = floor(W − 0,5) au lot L4")}})


def interdit(tr: Troncon, e, regle: str, controle: str, message: str, valeur=None):
    """Interdit réglementaire : la compilation s'arrête, sauf si la description l'admet explicitement pour décrire un
    cas réel non conforme (« ecarts_admis: {<règle>: <motif>} ») ; le contrôle est alors noté non_conforme_admis."""
    c = {"controle": controle, "evenement": e["chemin"], "regle": regle, "statut": "non_conforme"}
    if valeur is not None:
        c["valeur"] = valeur
    if regle not in tr.admis:
        raise ErreurDescription(f"{e['chemin']} : {message} ; interdit ({regle}). Pour décrire un cas réel non "
                                f"conforme, l'admettre explicitement : « ecarts_admis: {{{regle}: <motif>}} »")
    tr.av.append(f"{e['chemin']} : {message} ; écart admis par la description ({regle} : {tr.admis[regle]})")
    tr.ctrl.append(c)


def _chaussee_largeur(tr, s):
    groupes, _, _ = tr.chaussees(s)
    return max((tg - td for tg, td, _ in groupes), default=0.0)


def ev_dos_d_ane(tr: Troncon, e):
    ctx, s = tr.ctx, e["a"]
    lg = regles.valeur("RF-MA-RAL-001", "dos_d_ane.longueur")
    h = regles.valeur("RF-MA-RAL-001", "dos_d_ane.hauteur")
    pdim = P.defaut("RF-MA-RAL-001", note="dos-d'âne circulaire 4,00 × 0,10 (NF P98-300)")
    if e.get("longueur") is not None or e.get("hauteur") is not None:
        lg = V.nombre(e.get("longueur", lg), e["chemin"] + ".longueur")
        h = V.nombre(e.get("hauteur", h), e["chemin"] + ".hauteur")
        pdim = _prov_ev(e, regle="RF-MA-RAL-001", note=f"cotes dites {lg} × {h}")
        if abs(lg - regles.valeur("RF-MA-RAL-001", "dos_d_ane.longueur")) > 1e-6 or abs(h - regles.valeur("RF-MA-RAL-001", "dos_d_ane.hauteur")) > 1e-6:
            tr.av.append(f"{e['chemin']} : dos-d'âne {lg} × {h} différent du profil normalisé 4,00 × 0,10 (RF-MA-RAL-001)")
    if not ctx["agglomeration"] or ctx["vitesse_kmh"] > 30:
        interdit(tr, e, "RF-MA-RAL-001", "dos_d_ane_contexte",
                 "dos-d'âne hors agglomération ou à plus de 30 km/h (décret 94-447 : agglomération, zone 30 ou section "
                 "à 30 km/h)", {"agglomeration": ctx["agglomeration"], "vitesse_kmh": ctx["vitesse_kmh"]})
    e["_s0"], e["_s1"] = s - lg / 2, s + lg / 2

    def apres():
        groupes, p, t = tr.chaussees(s)
        for tg, td, g in groupes:
            tr.objets.append(objet(tr, "securite", "dos_d_ane", s, (tg + td) / 2,
                                   {"longueur_m": lg, "largeur_m": _r(tg - td), "hauteur_m": h},
                                   ["RF-MA-RAL-001", "RF-OSM-TC-001"], _prov_ev(e), {"dimensions": pdim}))
            if V.booleen(e.get("triangles", "oui"), e["chemin"] + ".triangles"):
                for i in g:
                    b = p["bandes"][i]
                    if b["type"] not in PF.VOIES_MOTORISEES:
                        continue
                    tax = (t[i] + t[i + 1]) / 2
                    sb = s - lg / 2 if b["sens"] != "arriere" else s + lg / 2
                    for dx in (-0.7, 0.0, 0.7):
                        triangle(tr, "TRIANGLE_DOS_ANE", b, sb, tax, dx, ["RF-MQ-RAL-01", "RF-MA-RAL-003"], e)
        if _chaussee_largeur(tr, s) >= 5.0 - 1e-9 and cibles(tr.profil_a(s), "axe"):
            ext = 10.0
            tr.decos.append({"type": "interruption", "s0": s - lg / 2 - ext, "s1": s + lg / 2 + ext, "cible": "axe", "motif": "autre"})
            tr.decos.append({"type": "marque", "s0": s - lg / 2 - ext, "s1": s + lg / 2 + ext, "cible": "axe",
                             "marque": PF.marque("T3", 2, ctx, "RF-MQ-RAL-01")})
            tr._redecorer = True
    tr._apres.append(apres)


def triangle(tr, gabarit, b, s, tax, dx, regles_l, e):
    sens = b["sens"]
    sg = -1.0 if sens == "arriere" else 1.0
    tr.marquages.append({
        "id": f"M-{tr.rid[2:]}.{len(tr.marquages) + 1}", "type": "symbole", "gabarit": gabarit,
        "ancrage": {"route": tr.rid, "bande": b["id"], "s": _r(s), "t": _r(tax - sg * dx), "cap_deg": tr.cap_deg(s, sens)},
        "couleur": "blanc", "regles": regles_l, "prov": {"*": P.defaut(regles_l[0], note=f"marquage de {e['chemin']}")}})


def objet(tr, famille, typ, s, t, dims, regles_l, prov_e, prov_sup=None, bande=None):
    oid = f"O-{tr.rid[2:]}.{len(tr.objets) + 1}"
    o = {"id": oid, "famille": famille, "type": typ, "position": tr.xy(s, t), "orientation_deg": tr.cap_deg(s),
         "dimensions": {k: _r(v) for k, v in dims.items()}, "rattachement": {"route": tr.rid, "s": _r(s), "t": _r(t)},
         "regles": regles_l, "prov": dict({"*": prov_e}, **(prov_sup or {}))}
    if bande:
        o["rattachement"]["bande"] = bande
    return o


def ev_plateau(tr: Troncon, e):
    ctx, s = tr.ctx, e["a"]
    h = V.nombre(e["hauteur"], e["chemin"] + ".hauteur") if e.get("hauteur") is not None else regles.valeur("DEF-034", "hauteur")
    rp = V.nombre(e["rampe_pct"], e["chemin"] + ".rampe_pct") if e.get("rampe_pct") is not None else regles.valeur("DEF-034", "rampe_pct")
    hmax = regles.valeur("RF-GV-RAL-002", "hauteur_max_cm") / 100.0
    if h > hmax + 1e-9 or not (regles.valeur("RF-GV-RAL-002", "rampe_min_pct") <= rp <= regles.valeur("RF-GV-RAL-002", "rampe_max_pct")):
        tr.av.append(f"{e['chemin']} : plateau h = {h} m, rampe {rp} % hors des limites de RF-GV-RAL-002 (h ≤ {hmax}, rampe 5-10 %)")
    rampe = h / (rp / 100.0)
    pp = bool(e.get("passage_pieton")) and V.booleen(e.get("passage_pieton"), e["chemin"])
    if e.get("longueur") is not None:
        lp, plp = V.nombre(e["longueur"], e["chemin"]), _prov_ev(e, "longueur", regle="RF-MA-RAL-001")
    else:
        lp = regles.valeur("RF-MA-RAL-001", "trapezoidal.plateau")[1]
        plp = P.defaut("RF-MA-RAL-001", conf="faible", note="longueur de plateau non dite : borne haute de [2,50 ; 4,00]")
    lo_, hi_ = regles.valeur("RF-MA-RAL-001", "trapezoidal.plateau")
    trapezoidal = lo_ - 1e-9 <= lp <= hi_ + 1e-9
    if not trapezoidal:
        tr.av.append(f"{e['chemin']} : plateau de {lp} m hors de [{lo_} ; {hi_}] (ralentisseur trapézoïdal, RF-MA-RAL-001)")
    # contexte : un plateau de 2,50 à 4,00 m est un ralentisseur trapézoïdal du décret 94-447 (agglomération, zone 30 ou
    # section à 30 km/h, RF-MA-RAL-001) ; tout plateau est un aménagement d'agglomération (RF-GV-RAL-002, CP p. 44)
    val = {"agglomeration": ctx["agglomeration"], "vitesse_kmh": ctx["vitesse_kmh"], "plateau_m": lp}
    if trapezoidal and (not ctx["agglomeration"] or ctx["vitesse_kmh"] > 30):
        interdit(tr, e, "RF-MA-RAL-001", "plateau_contexte",
                 "ralentisseur trapézoïdal (plateau de 2,50 à 4,00 m) hors agglomération ou à plus de 30 km/h "
                 "(décret 94-447)", val)
    elif not ctx["agglomeration"]:
        interdit(tr, e, "RF-GV-RAL-002", "plateau_contexte", "plateau hors agglomération (condition : agglomération)", val)
    e["_s0"], e["_s1"] = s - lp / 2 - rampe, s + lp / 2 + rampe
    if pp:
        pro = regles.valeur("RF-MQ-PP-04", "prolongement")
        ev_passage(tr, dict(e, type="passage_pieton", largeur=lp + 2 * pro, chemin=e["chemin"], _plateau=e,
                            _prov_largeur=P.defaut("RF-MQ-PP-04", note=f"bandes = plateau {lp} m + 2 × {pro} m")))

    def apres():
        groupes, p, t = tr.chaussees(s)
        for tg, td, g in groupes:
            tr.objets.append(objet(tr, "securite", "plateau", s, (tg + td) / 2,
                                   {"longueur_m": lp + 2 * rampe, "largeur_m": tg - td, "hauteur_m": h},
                                   ["DEF-034", "RF-MA-RAL-001", "RF-GV-RAL-002"], _prov_ev(e),
                                   {"dimensions": P.defaut("DEF-034", note=f"plateau {lp:.2f} m + 2 rampes de {rampe:.2f} m à {rp} %, h = {h}"),
                                    "longueur": plp}))
            if not pp and V.booleen(e.get("triangles", "oui"), e["chemin"] + ".triangles"):
                for i in g:
                    b = p["bandes"][i]
                    if b["type"] not in PF.VOIES_MOTORISEES:
                        continue
                    tax = (t[i] + t[i + 1]) / 2
                    w = largeur_a(b["largeur"], s)
                    nb = int(math.floor(w / 0.7 + 1e-9))
                    pied = s - lp / 2 - rampe if b["sens"] != "arriere" else s + lp / 2 + rampe
                    sb = pied - 2.0 if b["sens"] != "arriere" else pied + 2.0      # rampe claire : pointes au pied du rampant
                    for k in range(nb):
                        triangle(tr, "TRIANGLE_PLATEAU", b, sb, tax, (k - (nb - 1) / 2) * 0.7, ["RF-MQ-RAL-03", "DEF-034"], e)
    tr._apres.append(apres)


def ev_coussin(tr: Troncon, e):
    s = e["a"]
    lo = V.nombre(e["largeur"], e["chemin"]) if e.get("largeur") is not None else regles.valeur("RF-GV-RAL-001", "largeur_PL_bus")[0]
    lg = V.nombre(e["longueur"], e["chemin"]) if e.get("longueur") is not None else regles.valeur("RF-GV-RAL-001", "longueur")[0]
    h = V.nombre(e["hauteur"], e["chemin"]) if e.get("hauteur") is not None else regles.valeur("RF-GV-RAL-001", "hauteur_cm")[0] / 100.0
    e["_s0"], e["_s1"] = e["a"] - lg / 2, e["a"] + lg / 2

    def apres():
        groupes, p, t = tr.chaussees(s)
        for tg, td, g in groupes:
            for i in g:
                b = p["bandes"][i]
                if b["type"] not in PF.VOIES_MOTORISEES:
                    continue
                tax = (t[i] + t[i + 1]) / 2
                tr.objets.append(objet(tr, "securite", "coussin", s, tax, {"longueur_m": lg, "largeur_m": lo, "hauteur_m": h},
                                       ["RF-GV-RAL-001", "RF-MA-RAL-002"], _prov_ev(e),
                                       {"dimensions": P.defaut("RF-GV-RAL-001", conf="faible",
                                                               note="bornes basses des plages : largeur 1,75 (bus), longueur 3, hauteur 6 cm")},
                                       bande=b["id"]))
                marge = (largeur_a(b["largeur"], s) - lo) / 2
                if marge < 0.5:
                    tr.av.append(f"{e['chemin']} : marge latérale du coussin {marge:.2f} m dans la voie {b['id']} (≥ 0,70 m, 0,50 en zone 30 : "
                                 "CP p. 20-26 d'après PROFILS_EN_TRAVERS.md § 6 ; règle absente de regles_route_fr.json)")
                pied = s - lg / 2 if b["sens"] != "arriere" else s + lg / 2
                sb = pied - 1.2 if b["sens"] != "arriere" else pied + 1.2
                if V.booleen(e.get("triangles", "oui"), e["chemin"] + ".triangles"):
                    for dx in (-0.5, 0.0, 0.5):
                        triangle(tr, "TRIANGLE_COUSSIN", b, sb, tax, dx, ["RF-MQ-RAL-02", "RF-MA-RAL-003"], e)
    tr._apres.append(apres)


def biseau_defaut(tr, w):
    """Longueur du biseau physique non dite : hors agglomération 37 × d (RF-GV-PT-014, ARP) ; en agglomération aucune
    règle ne la chiffre : prise égale à l'oblique de marquage L (RF-MQ-OBL-02), confiance faible."""
    if not tr.ctx["agglomeration"]:
        return 37.0 * w, P.defaut("RF-GV-PT-014", note=f"biseau 37 × d = 37 × {w:.2f} m (route interurbaine)")
    L, v15 = _V15_L(tr)
    return float(L), P.defaut("RF-MQ-OBL-02", conf="faible",
                              note=f"agglomération : biseau physique non chiffré, pris égal à l'oblique L = {L} m (V15 = {v15} km/h)")


def _V15_L(tr):
    v = tr.ctx.get("v15") or tr.ctx["vitesse_kmh"]
    v = min(v, regles.valeur("RF-MQ-PS-02", "double_sens")) if not tr.sens_unique else v
    tab = regles.valeur("RF-MQ-PS-03", "V15_vers_L_m")
    cles = sorted(int(k) for k in tab)
    k = next((c for c in cles if c >= v), cles[-1])
    return tab[str(k)], k


def _voie_cible(tr, e, defaut_voie="gauche"):
    """(indice dans la base, bande, sens des usagers) de la voie supprimée / ajoutée à côté."""
    mot = [(i, b) for i, b in enumerate(tr.base) if b["type"] in PF.VOIES_MOTORISEES]
    if e.get("sens") is not None:
        sens = V.SENS.get(V.norm(e["sens"]))
    else:
        cand = [s for s in ("avant", "arriere") if sum(1 for _, b in mot if b["sens"] == s) >= (2 if e["type"] == "rabattement" else 1)]
        if len(cand) != 1:
            raise ErreurDescription(f"{e['chemin']} : préciser le sens concerné (sens: → ou ←)")
        sens = cand[0]
    voies = [(i, b) for i, b in mot if b["sens"] == sens]
    if not voies:
        raise ErreurDescription(f"{e['chemin']} : aucune voie dans le sens {sens}")
    voie = V.norm(e.get("voie", defaut_voie))
    # « gauche » pour les usagers = la plus proche de l'axe
    if sens == "avant":
        i, b = voies[0] if voie == "gauche" else voies[-1]
    else:
        i, b = voies[-1] if voie == "gauche" else voies[0]
    return i, b, sens, voie, voies


def ev_rabattement(tr: Troncon, e):
    """Suppression d'une voie (N → N−1). Biseau physique Lp (dit, sinon 37 × d, RF-GV-PT-014) ; avec « zebra », oblique
    peinte continue 3u de longueur max(Lp, L) à l'amont du point de fin et zone hachurée entre l'oblique et la bordure
    (RF-MQ-OBL-02, RF-MQ-RET-01, RF-OSM-CAR-051, DEF-020) ; avec « elargit: <bande> », la bande nommée (trottoir) absorbe
    la largeur perdue (le bord extérieur ne bouge pas) ; flèches de rabattement depuis le milieu de l'oblique ou du
    biseau (RF-MQ-RAB-02 à -07)."""
    s = e["a"]
    i, b, sens, voie, voies = _voie_cible(tr, e)
    if len(voies) < 2:
        raise ErreurDescription(f"{e['chemin']} : rabattement d'une voie dans un sens qui n'en a qu'une")
    w = PF.nombre(b["largeur"]) if b["largeur"] is not None else PF.largeur_defaut(b, tr.base, tr.ctx)[0]
    if e.get("biseau") is not None:
        lb, plb = V.nombre(e["biseau"], e["chemin"]), _prov_ev(e, "biseau", regle="RF-MQ-OBL-02")
    else:
        lb, plb = biseau_defaut(tr, w)
    L, v15 = _V15_L(tr)
    zebra = e.get("zebra") is not None and V.booleen(e["zebra"], e["chemin"] + ".zebra")
    lo = max(lb, L) if zebra else lb
    if lb < L - 1e-9 and not zebra:
        tr.av.append(f"{e['chemin']} : biseau de {lb:.1f} m < L = {L} m (V15 = {v15} km/h) : l'oblique doit être portée à L "
                     "(RF-MQ-RET-01) ; écrire « zebra: oui » pour la peindre")
    sg = 1 if sens == "avant" else -1

    def iv(d0, d1):             # intervalle [a − d0, a − d1] dans le sens des usagers
        x0, x1 = s - sg * d0, s - sg * d1
        return min(x0, x1), max(x0, x1)

    o0, o1 = iv(lo, 0.0)        # oblique / disparition de la voie
    p0, p1 = iv(lb, 0.0)        # biseau physique
    if o0 < -1e-6 or o1 > tr.L + 1e-6:
        raise ErreurDescription(f"{e['chemin']} : l'oblique de {lo:.1f} m sort du tronçon")
    w0, w1 = (w, 0.0) if sens == "avant" else (0.0, w)
    tr.mods.append({"op": "loi", "s0": o0, "s1": o1, "bande": b["id"], "w0": w0, "w1": w1, "chemin": e["chemin"], "prov": plb})
    tr.mods.append({"op": "absente", "s0": o1 if sens == "avant" else 0.0, "s1": tr.L if sens == "avant" else o0,
                    "bande": b["id"], "chemin": e["chemin"]})
    cote_ext = "gauche" if (voie == "gauche") == (sens == "avant") else "droite"     # côté profil où disparaît la voie
    if tr.sens_unique and cote_ext == "gauche":
        tr.bord_ref = "droite"
    if zebra and lo > lb + 1e-9:
        # zone hachurée entre la bordure (côté de la voie supprimée) et l'oblique : largeur = w·(x − début)/Lo − rétrécissement
        z = {"id": f"zh_{b['id']}", "type": "zone_neutralisee", "sous_type": "hachures", "sens": "aucun", "largeur": None,
             "attributs": {}, "prov": {"*": _prov_ev(e, "zebra", regle="DEF-020", note="zébra entre l'oblique et la bordure")}}
        zm = w * (lo - lb) / lo
        pos = {"avant": b["id"]} if cote_ext == "gauche" else {"apres": b["id"]}
        tr.mods.append(dict({"op": "inserer", "s0": o0, "s1": o1, "bande": z, "chemin": e["chemin"]}, **pos))
        a_, b_ = iv(lo, lb)
        pz = P.solveur("rabattement", regle="RF-MQ-OBL-02", note=f"zébra : oblique L = {lo:.1f} m, biseau physique {lb:.1f} m")
        tr.mods.append({"op": "loi", "s0": a_, "s1": b_, "bande": z["id"], "w0": 0.0 if sens == "avant" else zm,
                        "w1": zm if sens == "avant" else 0.0, "chemin": e["chemin"], "prov": pz})
        tr.mods.append({"op": "loi", "s0": p0, "s1": p1, "bande": z["id"], "w0": zm if sens == "avant" else 0.0,
                        "w1": 0.0 if sens == "avant" else zm, "chemin": e["chemin"], "prov": pz})
    if e.get("elargit") is not None:
        cible = trouver_bande(str(e["elargit"]), tr.base, e["chemin"] + ".elargit")
        wt, pwt = _largeur_resolue(tr, cible)
        wt = PF.nombre(wt)
        pe = _prov_ev(e, "elargit", note=f"{cible['id']} absorbe la largeur de la voie supprimée")
        tr.mods.append({"op": "loi", "s0": p0, "s1": p1, "bande": cible["id"], "w0": wt if sens == "avant" else wt + w,
                        "w1": wt + w if sens == "avant" else wt, "chemin": e["chemin"], "prov": pe})
        tr.mods.append({"op": "remplacer_largeur", "s0": p1 if sens == "avant" else 0.0, "s1": tr.L if sens == "avant" else p0,
                        "bande": cible["id"], "largeur": wt + w, "prov": pe, "chemin": e["chemin"]})
    # flèches de rabattement (RF-MQ-RAB-03 à -07) : référence = milieu de l'oblique (ou du biseau)
    if V.booleen(e.get("fleches", "oui"), e["chemin"] + ".fleches"):
        tab = {r["L"]: r for r in regles.valeur("RF-MQ-RAB-05", "table")}
        r = tab[L]
        dists = [L, L - r["i1"], L - r["i1"] - r["i2"]]
        nb = int(V.nombre(e["nombre_fleches"], e["chemin"])) if e.get("nombre_fleches") is not None else 3
        if nb < 3 and not tr.ctx["agglomeration"]:
            tr.av.append(f"{e['chemin']} : {nb} flèches hors agglomération : 3 exigées (RF-MQ-RAB-03)")
        dists = dists[:nb]
        mil = (o0 + o1) / 2
        pos = [mil - d if sens == "avant" else mil + d for d in dists]
        pos_ok = [x for x in pos if 0 <= x <= tr.L]
        if len(pos_ok) < len(pos):
            tr.av.append(f"{e['chemin']} : longueur insuffisante avant l'oblique pour {len(pos)} flèches (RF-MQ-RAB-04)")
        gab = "RAB_D" if voie == "gauche" else "RAB_G"
        e["_fleches"] = pos_ok

        def apres():
            for x in pos_ok:
                p = tr.profil_a(x)
                ids = [bb["id"] for bb in p["bandes"]]
                if b["id"] not in ids:
                    continue
                k = ids.index(b["id"])
                t = t_limites(p, x)
                tr.marquages.append({
                    "id": f"M-{tr.rid[2:]}.{len(tr.marquages) + 1}", "type": "fleche", "gabarit": gab,
                    "ancrage": {"route": tr.rid, "bande": b["id"], "s": _r(x), "t": _r((t[k] + t[k + 1]) / 2),
                                "cap_deg": tr.cap_deg(x, sens)},
                    "couleur": "blanc", "regles": ["RF-MQ-RAB-02", "RF-MQ-RAB-03", "RF-MQ-RAB-04", "RF-MQ-RAB-05", "RF-MQ-RAB-07"],
                    "prov": {"*": P.defaut("RF-MQ-RAB-05", note=f"L = {L} m (V15 = {v15} km/h, RF-MQ-PS-03) ; i1 = {r['i1']}, i2 = {r['i2']} ; "
                                                                  f"référence : milieu {'de l oblique' if zebra else 'du biseau'}")}})
        tr._apres.append(apres)
        # rive T'3 3u à partir de la 1re flèche si la rive est marquée (RF-MQ-SC-11, RF-OSM-MRQ-021)
        if pos_ok:
            a0, a1 = (min(pos_ok), o1) if sens == "avant" else (o0, max(pos_ok))
            cote = "droite" if sens == "avant" else "gauche"
            tr.decos.append({"type": "interruption", "s0": a0, "s1": a1, "cible": ("rive", cote), "motif": "autre"})
            tr.decos.append({"type": "marque", "s0": a0, "s1": a1, "cible": ("rive", cote),
                             "marque": PF.marque("T'3", 3, tr.ctx, "RF-MQ-SC-11")})


def ev_zone_continue(tr: Troncon, e):
    """Zone de dépassement interdit : continue 2u sur l'axe à partir de « a » (dans le sens des usagers concernés)
    jusqu'à « fin », précédée d'une ligne d'annonce T3 2u de longueur L et de 3 flèches de rabattement à cheval sur
    l'annonce (RF-MQ-PS-03 à -05, RF-MQ-LAR-A3a, RF-MQ-LAR-A1a, RF-MQ-RAB-02 « 2 voies », RF-MQ-RAB-05, -07)."""
    s = e["a"]
    sens = V.SENS.get(V.norm(e.get("sens", "avant")))
    if sens not in ("avant", "arriere"):
        raise ErreurDescription(f"{e['chemin']}.sens : avant (→) ou arriere (←)")
    if not cibles(tr.profil_base, "axe"):
        raise ErreurDescription(f"{e['chemin']} : pas de ligne axiale (route à double sens marquée) où poser la continue")
    L, v15 = _V15_L(tr)
    fin = V.nombre(e["fin"], e["chemin"] + ".fin") if e.get("fin") is not None else (tr.L if sens == "avant" else 0.0)
    annonce = V.booleen(e.get("annonce", "oui"), e["chemin"] + ".annonce")
    regle_ann = "RF-MQ-PS-05" if tr.ctx["agglomeration"] else "RF-MQ-PS-04"
    c0, c1 = (s, fin) if sens == "avant" else (fin, s)
    a0, a1 = (s - L, s) if sens == "avant" else (s, s + L)
    if annonce and (a0 < -1e-6 or a1 > tr.L + 1e-6):
        raise ErreurDescription(f"{e['chemin']} : l'annonce de L = {L} m sort du tronçon")
    tot0, tot1 = (a0 if annonce else c0), (c1 if not annonce else max(c1, a1)) if sens == "avant" else (min(c0, a0), a1 if annonce else c1)
    tr.decos.append({"type": "interruption", "s0": min(a0, c0) if annonce else c0, "s1": max(a1, c1) if annonce else c1,
                     "cible": "axe", "motif": "autre"})
    tr.decos.append({"type": "marque", "s0": c0, "s1": c1, "cible": "axe", "marque": PF.marque("continue", 2, tr.ctx, "RF-MQ-LAR-A1a")})
    if annonce:
        tr.decos.append({"type": "marque", "s0": a0, "s1": a1, "cible": "axe", "marque": PF.marque("T3", 2, tr.ctx, "RF-MQ-LAR-A3a")})
    fl = V.booleen(e.get("fleches", "oui" if not tr.ctx["agglomeration"] else "non"), e["chemin"] + ".fleches")
    if annonce and fl:
        tab = {r["L"]: r for r in regles.valeur("RF-MQ-RAB-05", "table")}
        r = tab[L]
        dists = [L, L - r["i1"], L - r["i1"] - r["i2"]]
        pos = [s - d if sens == "avant" else s + d for d in dists]

        def apres():
            for x in pos:
                p = tr.profil_a(x)
                k = p["reference"]["limite"]
                t = t_limites(p, x)[k]
                bid = p["bandes"][k if sens == "avant" else k - 1]["id"]
                tr.marquages.append({
                    "id": f"M-{tr.rid[2:]}.{len(tr.marquages) + 1}", "type": "fleche", "gabarit": "RAB_D",
                    "ancrage": {"route": tr.rid, "bande": bid, "s": _r(x), "t": _r(t), "cap_deg": tr.cap_deg(x, sens)},
                    "couleur": "blanc", "regles": ["RF-MQ-RAB-01", "RF-MQ-RAB-02", "RF-MQ-RAB-05", "RF-MQ-RAB-07", regle_ann],
                    "prov": {"*": P.defaut("RF-MQ-RAB-05", note=f"à cheval sur l'annonce ; L = {L} m (V15 = {v15}) ; distances "
                                                                  f"{', '.join(str(d) for d in dists)} m au début de la continue")}})
        tr._apres.append(apres)
    tr._redecorer = True


def ev_fleches(tr: Troncon, e):
    """Flèches directionnelles (RF-MQ-DIR-02 à -09, DEF-017) : gabarits TD, TAD, TAG, TD_TAD, TD_TAG seulement."""
    typ = str(e.get("type_fleche", "")).upper().replace("-", "_")
    autorises = regles.valeur("RF-MQ-DIR-02", "types")
    if typ not in autorises:
        raise ErreurDescription(f"{e['chemin']} : flèche « {typ} » interdite ; types autorisés : {', '.join(autorises)} (RF-MQ-DIR-02)")
    nb = int(V.nombre(e.get("nombre", regles.valeur("DEF-017", "nombre_par_voie")), e["chemin"] + ".nombre"))
    pas = V.nombre(e.get("interdistance", regles.valeur("DEF-017", "interdistance")), e["chemin"] + ".interdistance")
    voies = e.get("voies", "toutes")
    if isinstance(voies, str) and V.norm(voies) == "toutes":
        cibles_b = [b for b in tr.base if b["type"] in PF.VOIES_MOTORISEES]
        if e.get("sens"):
            sf = V.SENS.get(V.norm(e["sens"]))
            cibles_b = [b for b in cibles_b if b["sens"] == sf]
    else:
        cibles_b = [trouver_bande(str(v), tr.base, e["chemin"] + ".voies") for v in (voies if isinstance(voies, list) else [voies])]
    if typ in ("TAG", "TAD", "TD_TAG", "TD_TAD"):
        tr.av.append(f"{e['chemin']} : flèches d'affectation {typ} : panneau C24a/b (ou Da30) obligatoire (RF-MQ-DIR-01), à poser au lot L6")
    pos = [e["a"] + k * pas for k in range(nb)]
    if pos[-1] > tr.L + 1e-6:
        raise ErreurDescription(f"{e['chemin']} : la dernière flèche (s = {pos[-1]}) sort du tronçon")

    def apres():
        for b in cibles_b:
            for x in pos:
                p = tr.profil_a(x)
                ids = [bb["id"] for bb in p["bandes"]]
                if b["id"] not in ids:
                    continue
                k = ids.index(b["id"])
                t = t_limites(p, x)
                tr.marquages.append({
                    "id": f"M-{tr.rid[2:]}.{len(tr.marquages) + 1}", "type": "fleche", "gabarit": typ,
                    "ancrage": {"route": tr.rid, "bande": b["id"], "s": _r(x), "t": _r((t[k] + t[k + 1]) / 2), "cap_deg": tr.cap_deg(x, b["sens"])},
                    "couleur": "blanc", "regles": ["RF-MQ-DIR-02", "RF-MQ-DIR-03", "RF-MQ-DIR-04", "RF-MQ-DIR-09", "DEF-017"],
                    "prov": {"*": _prov_ev(e, regle="RF-MQ-DIR-03", note=f"{nb} flèches, interdistance {pas} m (DEF-017 si non dit)")}})
    tr._apres.append(apres)


def ev_inscription(tr: Troncon, e):
    """Inscription au sol (BUS, TAXI…) : RF-MQ-TC-03, RF-MA-CTC-002 (lettres ≥ 1,50 m si V ≤ 50)."""
    txt = str(e.get("texte_sol") or "").strip().upper()
    if not txt:
        raise ErreurDescription(f"{e['chemin']} : texte de l'inscription manquant")
    b = trouver_bande(str(e.get("voie", "")), tr.base, e["chemin"] + ".voie")
    if e.get("hauteur") is not None:
        h, ph = V.nombre(e["hauteur"], e["chemin"] + ".hauteur"), _prov_ev(e, "hauteur", regle="RF-MA-CTC-002")
    elif tr.ctx["vitesse_kmh"] <= 50:
        h, ph = regles.valeur("RF-MA-CTC-002", "lettres_min_si_V_le_50"), P.defaut("RF-MA-CTC-002", note="lettres de 1,50 m (V ≤ 50)")
    else:
        raise ErreurDescription(f"{e['chemin']} : hauteur des lettres à dire (V > 50 km/h, aucune règle de la base ne la fixe)")
    s = e["a"]

    def apres():
        p = tr.profil_a(s)
        ids = [bb["id"] for bb in p["bandes"]]
        k = ids.index(b["id"])
        t = t_limites(p, s)
        tr.marquages.append({
            "id": f"M-{tr.rid[2:]}.{len(tr.marquages) + 1}", "type": "inscription", "gabarit": f"TEXTE_{txt}",
            "ancrage": {"route": tr.rid, "bande": b["id"], "s": _r(s), "t": _r((t[k] + t[k + 1]) / 2), "cap_deg": tr.cap_deg(s, b["sens"])},
            "couleur": "blanc", "regles": ["RF-MQ-TC-03" if txt in ("BUS", "TRAM") else "RF-MQ-STA-08", "RF-MA-CTC-002"],
            "x-opendrive": {"object_type": "roadMark", "texte": txt, "hauteur_lettres_m": h},
            "prov": {"*": _prov_ev(e), "hauteur": ph}})
    tr._apres.append(apres)


def ev_elargissement(tr: Troncon, e):
    s = e["a"]
    mot = [b for b in tr.base if b["type"] in PF.VOIES_MOTORISEES]
    sens = V.SENS.get(V.norm(e["sens"])) if e.get("sens") else None
    if sens is None:
        ss = {b["sens"] for b in mot}
        if len(ss) != 1:
            raise ErreurDescription(f"{e['chemin']} : préciser le sens (→ ou ←) de la voie ajoutée")
        sens = ss.pop()
    voies = [b for b in tr.base if b["type"] in PF.VOIES_MOTORISEES and b["sens"] == sens]
    voie = V.norm(e.get("voie", e.get("cote", "gauche")))
    typ = {"voie": "voie_circulation", "tourne-a-gauche": "voie_tourne_gauche", "tag": "voie_tourne_gauche",
           "tourne-a-droite": "voie_tourne_droite", "tad": "voie_tourne_droite", "bus": "voie_bus",
           "voie bus": "voie_bus", "insertion": "voie_insertion", "acceleration": "voie_insertion",
           "voie d'insertion": "voie_insertion", "deceleration": "voie_deceleration",
           "voie de deceleration": "voie_deceleration"}.get(V.norm(e.get("type_voie", "voie")), None)
    if typ is None:
        raise ErreurDescription(f"{e['chemin']} : type_voie inconnu (voie, tourne-à-gauche, tourne-à-droite, bus, "
                                "insertion, décélération)")
    nb = {"id": f"{PF.ABREVIATIONS[typ]}_e{e['chemin'].split('[')[-1].rstrip(']')}", "type": typ, "sous_type": None,
          "sens": sens, "largeur": None, "attributs": {}, "prov": {"*": _prov_ev(e)}}
    if e.get("largeur") is not None:
        w = V.nombre(e["largeur"], e["chemin"])
        nb["prov"]["largeur"] = _prov_ev(e, "largeur")
    else:
        w, nb["prov"]["largeur"] = PF.largeur_defaut(dict(nb), tr.base + [nb], tr.ctx)
    nb["largeur"] = w
    if e.get("biseau") is not None:
        lb, plb = V.nombre(e["biseau"], e["chemin"]), _prov_ev(e, "biseau", regle="RF-MQ-RET-01")
    else:
        lb, plb = biseau_defaut(tr, w)
    s0, s1 = (s - lb, s) if sens == "avant" else (s, s + lb)
    if s0 < -1e-6 or s1 > tr.L + 1e-6:
        raise ErreurDescription(f"{e['chemin']} : le biseau de {lb:.1f} m sort du tronçon")
    # position : gauche des usagers = côté de l'axe
    if sens == "avant":
        pos = {"avant": voies[0]["id"]} if voie == "gauche" else {"apres": voies[-1]["id"]}
    else:
        pos = {"apres": voies[-1]["id"]} if voie == "gauche" else {"avant": voies[0]["id"]}
    pres = (s0, tr.L) if sens == "avant" else (0.0, s1)
    if tr.sens_unique and ((sens == "avant") == (voie == "gauche")):
        tr.bord_ref = "droite"
    tr.mods.append(dict({"op": "inserer", "s0": pres[0], "s1": pres[1], "bande": nb, "chemin": e["chemin"]}, **pos))
    if typ in ("voie_insertion", "voie_deceleration"):
        _lignes_voie_auxiliaire(tr, e, nb, typ, pos)
    w0, w1 = (0.0, w) if sens == "avant" else (w, 0.0)
    tr.mods.append({"op": "loi", "s0": s0, "s1": s1, "bande": nb["id"], "w0": w0, "w1": w1, "chemin": e["chemin"], "prov": plb})


def _lignes_voie_auxiliaire(tr: Troncon, e, nb: dict, typ: str, pos: dict):
    """Voie d'insertion ou de décélération (lot « scenes ») : délimitation T2 5u avec la voie voisine (RF-MQ-INS-01,
    RF-MQ-DEC-01 ; IISR7 tableau 113-2 B1b, RF-MQ-LAR-B1b) au lieu du T1 2u des voies de même sens, et rive T'3 3u
    du côté extérieur (RF-MQ-LAR-B2d : rive aux approches et dans les bretelles). Posées comme limites décrites ; le
    compilateur de réseau retire l'avertissement d'écart de règle qui en résulte (règle spéciale citée)."""
    ids = [b["id"] for b in tr.base]
    regle = "RF-MQ-INS-01" if typ == "voie_insertion" else "RF-MQ-DEC-01"
    voisine = pos.get("apres") or pos.get("avant")
    k = ids.index(voisine)
    paire_voie = (voisine, nb["id"]) if "apres" in pos else (nb["id"], voisine)
    tr.lim_base[paire_voie] = {"raffiner": True, "_voie_auxiliaire": regle,
                               "marquages": {"modulation": "T2", "largeur_u": 5.0, "couleur": "blanc", "regle": regle},
                               "prov": P.defaut(regle, note=f"délimitation de la {typ.replace('_', ' ')} : T2 5u")}
    ext = ids[k + 1] if "apres" in pos and k + 1 < len(ids) else (ids[k - 1] if "avant" in pos and k > 0 else None)
    if ext is not None:
        paire_ext = (nb["id"], ext) if "apres" in pos else (ext, nb["id"])
        tr.lim_base[paire_ext] = {"raffiner": True, "_voie_auxiliaire": "RF-MQ-LAR-B2d",
                                  "marquages": {"modulation": "T'3", "largeur_u": 3.0, "couleur": "blanc",
                                                "regle": "RF-MQ-LAR-B2d"},
                                  "prov": P.defaut("RF-MQ-LAR-B2d", note="rive de voie auxiliaire T'3 3u")}


def ev_arret_bus(tr: Troncon, e):
    ctx, s = tr.ctx, e["a"]
    cote = _cote(e)
    sens = "avant" if cote == "droite" else "arriere"
    art = bool(e.get("articule")) and V.booleen(e.get("articule"), e["chemin"])
    if e.get("quai") is not None:
        lq, plq = V.nombre(e["quai"], e["chemin"]), _prov_ev(e, "quai")
    else:
        lq = 20.0 if art else 14.0
        plq = P.defaut("DEF-032", note=f"quai = bus + 2 × 1 m ({lq:.0f} m)")
    q1 = s + 1.0 if sens == "avant" else s - 1.0 + lq
    q0 = q1 - lq
    if q0 < 0 or q1 > tr.L:
        raise ErreurDescription(f"{e['chemin']} : le quai [{q0:.1f} ; {q1:.1f}] sort du tronçon")
    # bandes converties en quai : contiguës depuis la chaussée (stationnement, bande plantée, trottoir…), jusqu'au
    # premier trottoir ou à la première bande d'un autre type (une piste passe derrière le quai, RF-MA-PIS-012)
    convertibles = ("stationnement", "livraison", "bande_plantee", "zone_neutralisee", "trottoir")
    pq = P.defaut("DEF-032", note=f"quai bus ({e['chemin']})")
    convertis = []
    for i in _bande_cote(tr.base, cote, tuple(PF.ABREVIATIONS)):
        b = tr.base[i]
        if b["type"] in PF.VOIES_MOTORISEES:
            continue
        if b["type"] == "bande_cyclable" and not convertis:
            tr.av.append(f"{e['chemin']} : bande cyclable entre la voie et le quai : interrompue au droit de l'arrêt (RF-MA-BAN-007)")
            continue
        if b["type"] not in convertibles:
            break
        convertis.append(b["id"])
        w, pw = _largeur_resolue(tr, b)
        tr.mods.append({"op": "remplacer", "s0": q0, "s1": q1, "bande": b["id"], "chemin": e["chemin"],
                        "par": {"type": "quai_bus", "sous_type": None, "sens": "double", "largeur": w,
                                "prov": {"largeur": pw, "*": pq}}})
        if b["type"] == "trottoir":
            break
    if not convertis:
        raise ErreurDescription(f"{e['chemin']} : aucune bande pour porter le quai côté {cote} (trottoir, stationnement…)")
    neut = regles.valeur("RF-MA-BUS-015", "stationnement_interdit_amont")
    _neutraliser(tr, q0 - neut, q0, cote, e, "RF-MA-BUS-015")
    _neutraliser(tr, q1, q1 + regles.valeur("RF-MA-BUS-015", "stationnement_interdit_aval"), cote, e, "RF-MA-BUS-015")
    ib = regles.valeur("RF-MA-BAN-007", "interruption_avant_arret")
    tr.decos.append({"type": "interruption", "s0": q0 - ib if sens == "avant" else q0, "s1": q1 if sens == "avant" else q1 + ib,
                     "cible": ("cyclable", cote), "motif": "arret_bus"})
    zz = V.booleen(e.get("zigzag", "oui"), e["chemin"] + ".zigzag")

    def apres():
        p = tr.profil_a((q0 + q1) / 2)
        i = cibles(p, ("bordure", cote))
        if not i:
            return
        if zz:
            z = regles.valeur("DEF-019")
            z0, z1 = (s - z["amont"], s + z["aval"]) if sens == "avant" else (s - z["aval"], s + z["amont"])
            z0, z1 = max(z0, 0.0), min(z1, tr.L)
            n = max(2, int(math.ceil((z1 - z0) / 1.0)) + 1)
            geo = []
            for k in range(n):
                x = z0 + (z1 - z0) * k / (n - 1)
                geo.append(tr.xy(x, t_limites(tr.profil_a(x), x)[cibles(tr.profil_a(x), ("bordure", cote))[0]]
                                 if cibles(tr.profil_a(x), ("bordure", cote)) else t_limites(p, x)[i[0]]))
            tr.marquages.append({"id": f"M-{tr.rid[2:]}.{len(tr.marquages) + 1}", "type": "zigzag", "gabarit": "ZIGZAG_BUS_10M_U5",
                                 "ancrage": {"route": tr.rid, "s": _r(z0)}, "geometrie": geo, "couleur": "jaune",
                                 "regles": ["DEF-019", "RF-MQ-TC-01", "ARB-03"],
                                 "prov": {"*": P.defaut("DEF-019", note="zigzag 30 m : 20 m en amont du poteau, 10 m en aval (ARB-03)")}})
        t = t_limites(p, s)
        ids = [bb["id"] for bb in p["bandes"]]
        k = ids.index(convertis[-1]) if convertis[-1] in ids else None
        if k is not None:
            tc = (t[k] + t[k + 1]) / 2
            tr.objets.append(objet(tr, "transport", "poteau_arret_bus", s, tc, {"hauteur_m": regles.valeur("RF-MA-BUS-012", "poteau_affichage_h")},
                                   ["RF-MA-BUS-012", "RF-MA-BUS-001"], _prov_ev(e), {"position": P.solveur("arret_bus", note="poteau au milieu de la bande du quai la plus éloignée de la chaussée, au droit de la tête de l'arrêt")},
                                   bande=convertis[-1]))
            if e.get("abri") is not None and V.booleen(e["abri"], e["chemin"] + ".abri"):
                la, lo = regles.valeur("RF-MA-BUS-012", "abri_exemple")
                nez = regles.valeur("DEF-032", "passage_nez_abri")
                tb = t[i[0]]
                sg = -1.0 if cote == "droite" else 1.0
                ta = tb + sg * (nez + la / 2)
                larg_quai = sum(abs(t[ids.index(c)] - t[ids.index(c) + 1]) for c in convertis if c in ids)
                if larg_quai < nez + la - 1e-9:
                    tr.av.append(f"{e['chemin']} : quai de {larg_quai:.2f} m trop étroit pour un abri de {la} m et un passage "
                                 f"de {nez} m devant (RF-MA-BUS-007, DEF-032)")
                sa = s - lo / 2 if sens == "avant" else s + lo / 2
                tr.objets.append(objet(tr, "transport", "abri_bus", sa, ta, {"largeur_m": la, "longueur_m": lo},
                                       ["RF-MA-BUS-012", "DEF-032"], _prov_ev(e, "abri"),
                                       {"position": P.defaut("DEF-032", note=f"abri en tête de quai, passage de {nez} m devant")}))
        if e.get("panneau") is not None and V.booleen(e["panneau"], e["chemin"] + ".panneau"):
            ev_panneau(tr, {"a": q0 if sens == "avant" else q1, "code": "C6", "cote": cote, "chemin": e["chemin"], "_regle": "RF-MA-BUS-014"})
    tr._apres.append(apres)


def _vue_charretiere_defaut() -> float:
    """Vue par défaut d'une entrée charretière : assets/specs/bordures_elements.json (autre équipe, lecture seule),
    abaisses.entree_charretiere.vue_m.defaut."""
    f = DEPOT / "assets" / "specs" / "bordures_elements.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    return float(d["abaisses"]["entree_charretiere"]["vue_m"]["defaut"])


def ev_charretiere(tr: Troncon, e):
    s = e["a"]
    if e.get("largeur") is None:
        raise ErreurDescription(f"{e['chemin']} : largeur de l'entrée charretière à dire (aucune règle ne la fixe)")
    w = V.nombre(e["largeur"], e["chemin"])
    cote = _cote(e)
    # vue de l'entrée : défaut de bordures_elements.json (abaisses.entree_charretiere : 0,02-0,04, défaut 0,03 ; pièce
    # T2_bateau, vue nominale 0,02-0,04), bornée par le maximum de RF-MA-TRO-015 (0,05) ; intégration de l'étape 2
    # (lot bordures : 0,05 posait la pièce 1 cm au-dessus de sa vue nominale)
    ab = {"type": "charretiere", "vue_m": min(regles.valeur("RF-MA-TRO-015", "entree_charretiere_max"),
                                              _vue_charretiere_defaut()), "bev": False,
          "regle": "RF-MA-TRO-016"}
    tro = [tr.base[i] for i in _bande_cote(tr.base, cote, ("trottoir",))]
    if tro and tro[0]["largeur"] is not None and PF.nombre(tro[0]["largeur"]) < 2.5:
        ab["rampant_m"] = 2.0
    tr.decos.append({"type": "abaisse", "s0": s - w / 2, "s1": s + w / 2, "cible": ("bordure", cote), "abaisse": ab})


def ev_abaisse(tr: Troncon, e):
    s = e["a"]
    w = V.nombre(e["largeur"], e["chemin"]) if e.get("largeur") is not None else regles.valeur("DEF-031", "largeur_min")
    ab = {"type": "traversee", "vue_m": regles.valeur("DEF-031", "vue"), "rampant_m": regles.valeur("DEF-031", "rampant_5pct"),
          "bev": V.booleen(e.get("bev", "oui"), e["chemin"] + ".bev"), "regle": "DEF-031"}
    cotes = ("droite", "gauche") if _cote(e, "deux") in ("deux", "les deux") else (_cote(e),)
    for c in cotes:
        tr.decos.append({"type": "abaisse", "s0": s - w / 2, "s1": s + w / 2, "cible": ("bordure", c), "abaisse": ab})


def ev_panneau(tr: Troncon, e):
    code = str(e.get("code") or "").strip()
    if not code:
        raise ErreurDescription(f"{e['chemin']} : code IISR du panneau manquant (ex. C20a, AB4, B14)")
    cote = _cote(e)
    agglo = tr.ctx["agglomeration"]
    h = regles.valeur("DEF-025", "hauteur_trottoir_agglo" if agglo else "hauteur_rase_campagne")
    sid = f"SG-{tr.rid[2:]}.{len(tr.signaux) + 1}"
    sg = {"id": sid, "famille": "panneau", "code": code}
    if e.get("valeur") is not None:
        sg["valeur"] = str(e["valeur"])
    sg.update({"position": {"route": tr.rid, "s": _r(e["a"]), "cote": cote},
               "orientation": {"vise": {"route": tr.rid, "sens": "avant" if cote == "droite" else "arriere"},
                               "rotation_exterieure_deg": regles.valeur("DEF-025", "lacet_vers_exterieur_deg")},
               "hauteur_bas_m": h,
               "regles": [r for r in (e.get("_regle"), "DEF-025", "ARB-20", "RF-SV-GEN.DISTANCE_RIVE") if r],
               "prov": {"*": _prov_ev(e), "hauteur_bas_m": P.defaut("DEF-025", note="hauteur sous panneau"),
                        "position": P.solveur("panneau", regle="ARB-20", note="décalage t calculé au lot L6 (règle de placement ARB-20)")}})
    tr.signaux.append(sg)


def ev_profil(tr: Troncon, e):
    nouveau = e.get("nouveau") or e.get("profil")
    if not nouveau:
        raise ErreurDescription(f"{e['chemin']} : « nouveau: \"trottoir 2 | voie 3 ← | …\" » attendu")
    try:
        bl, lims = FP.analyser(nouveau, e["chemin"] + ".nouveau")
        bl, lims = resoudre_bandes(bl, lims, {"contexte": {}}, e["chemin"], {"conf": "moyenne"})
    except FP.ErreurFormat as x:
        raise ErreurDescription(str(x))
    # identités : même suite de types que la base → mêmes identifiants (continuité des voies)
    if [b["type"] for b in bl] == [b["type"] for b in tr.base]:
        for x, y in zip(bl, tr.base):
            x["id"] = y["id"]
    else:
        PF.ids_bandes(bl)
    limd = {Troncon._cle(bl, i): l for i, l in enumerate(lims) if l is not None}
    a = e["a"]
    trans = V.nombre(e.get("transition", 0), e["chemin"] + ".transition")
    meme_suite = [b["type"] for b in bl] == [b["type"] for b in tr.base]
    # changement dit sans transition (ou transition impossible : bandes différentes) : déclaré « instantanee » dans la
    # section qui commence en a (modele_voie section_profil.transition_entree), pour que le générateur distingue un
    # décroché voulu d'une discontinuité (lot L1)
    tr.mods.append({"op": "profil", "s0": a, "s1": tr.L, "bandes": bl, "lim": limd, "chemin": e["chemin"],
                    "instantane": not (trans > 0 and meme_suite)})
    if trans > 0 and meme_suite:
        for x, y in zip(bl, tr.base):
            wx = x["largeur"] if x["largeur"] is not None else PF.largeur_defaut(x, bl, tr.ctx)[0]
            wy = y["largeur"] if y["largeur"] is not None else PF.largeur_defaut(y, tr.base, tr.ctx)[0]
            if abs(wx - wy) > 1e-9:
                tr.mods.append({"op": "loi", "s0": a, "s1": min(a + trans, tr.L), "bande": x["id"], "w0": wy, "w1": wx,
                                "chemin": e["chemin"], "prov": _prov_ev(e, "transition")})
    elif trans > 0:
        tr.av.append(f"{e['chemin']} : transition ignorée (le nombre ou l'ordre des bandes change) : changement instantané")


def ev_ouverture(tr: Troncon, e):
    """Ouverture progressive (lot « scenes », 17/10/2026) : sur « longueur » m, le profil passe de la base au profil
    « nouveau ». Les bandes du nouveau profil absentes de la base (sous-suite de même type et même sens, dans l'ordre)
    y entrent avec une largeur qui croît de 0 à leur largeur ; les bandes communes passent linéairement de leur largeur
    de base à la nouvelle. « sens: → » (défaut) : base avant a − longueur, nouveau profil après a (jusqu'au prochain
    changement de profil) ; « sens: ← » : nouveau profil de 0 à a, retour à la base en a + longueur. Sert aux
    évasements d'approche de carrefour (voie de stockage, îlot séparateur précédé de sa zone hachurée)."""
    nouveau = e.get("nouveau")
    if not nouveau:
        raise ErreurDescription(f"{e['chemin']} : « nouveau: \"trottoir 2 | voie 3 ← | …\" » attendu")
    if e.get("longueur") is None:
        raise ErreurDescription(f"{e['chemin']} : longueur de l'ouverture (m) à dire (aucune règle ne la fixe seule : "
                                "déport 1/15 RF-GV-CAR-010, 1/10 si route ≤ 5 m)")
    lg = V.nombre(e["longueur"], e["chemin"] + ".longueur")
    sens = V.SENS.get(V.norm(e.get("sens", "→")))
    if sens not in ("avant", "arriere") or lg <= 0:
        raise ErreurDescription(f"{e['chemin']} : sens → ou ← et longueur > 0 attendus")
    try:
        bl, lims = FP.analyser(nouveau, e["chemin"] + ".nouveau")
        bl, lims = resoudre_bandes(bl, lims, {"contexte": {}}, e["chemin"], {"conf": tr.conf})
    except FP.ErreurFormat as x:
        raise ErreurDescription(str(x))
    a0 = e["a"] - lg if sens == "avant" else e["a"] + lg
    base, lim_courant = _profil_en_vigueur(tr, a0)
    cle = lambda b: (b["type"], b.get("sous_type"), b.get("sens"))  # noqa: E731
    j, assoc = 0, {}
    for i, b in enumerate(bl):
        if j < len(base) and cle(base[j]) == cle(b):
            assoc[i] = j
            j += 1
    if j != len(base):
        raise ErreurDescription(f"{e['chemin']} : l'ouverture ajoute des bandes à la base, elle n'en retire pas "
                                f"(bande de base non retrouvée : {base[j]['id']})")
    pris = {b["id"] for b in base}
    for i, b in enumerate(bl):
        if i in assoc:
            b["id"] = base[assoc[i]]["id"]
            continue
        ab = PF.ABREVIATIONS.get(b["type"], "b")
        k = 1
        while f"{ab}{k}" in pris:
            k += 1
        b["id"] = b.get("id") or f"{ab}{k}"
        pris.add(b["id"])
    for b in bl:
        if b["largeur"] is None:
            b["largeur"], b["prov"]["largeur"] = PF.largeur_defaut(b, bl, tr.ctx)
    # bande centrale qui s'ouvre entre les deux sens (îlot, enveloppe d'îlot) : coupée en deux demi-bandes de part et
    # d'autre de la séparation des sens, pour que celle-ci reste sur la ligne de référence pendant l'ouverture
    # (déport symétrique, RF-GV-CAR-010) — sinon la référence, constante par profil, resterait au bord de la bande
    arr = [i for i, b in enumerate(bl) if b["type"] in PF.VOIES_MOTORISEES and b["sens"] == "arriere"]
    ava = [i for i, b in enumerate(bl) if b["type"] in PF.VOIES_MOTORISEES and b["sens"] == "avant"]
    if arr and ava and max(arr) < min(ava):
        centre = list(range(max(arr) + 1, min(ava)))
        neuves = [i for i in centre if i not in assoc]
        if len(centre) == 1 and neuves == centre:
            i = centre[0]
            b = bl[i]
            g, d_ = copy.deepcopy(b), copy.deepcopy(b)
            g["id"], d_["id"] = f"{b['id']}{AXE_G}", f"{b['id']}{AXE_D}"
            g["largeur"] = d_["largeur"] = PF.nombre(b["largeur"]) / 2.0
            for x in (g, d_):
                x["prov"]["largeur"] = _prov_ev(e, "nouveau", note=f"moitié de la bande centrale de {PF.nombre(b['largeur'])} m")
            lims = lims[:i + 1] + [None] + lims[i + 1:]
            bl = bl[:i] + [g, d_] + bl[i + 1:]
            assoc = {(k if k < i else k + 1): v for k, v in assoc.items()}
    limd = {Troncon._cle(bl, i): l for i, l in enumerate(lims) if l is not None}
    # limites décrites du profil en vigueur (bordures, caniveaux, lignes) conservées entre les mêmes bandes
    for i in range(len(bl) + 1):
        k = Troncon._cle(bl, i)
        if k not in limd and k in lim_courant:
            limd[k] = lim_courant[k]
    a = e["a"]
    t0, t1 = (a - lg, a) if sens == "avant" else (a, a + lg)
    if t0 < -1e-6 or t1 > tr.L + 1e-6:
        raise ErreurDescription(f"{e['chemin']} : l'ouverture [{t0:.1f} ; {t1:.1f}] sort du tronçon [0 ; {tr.L:.2f}]")
    e["_s0"], e["_s1"] = t0, t1
    if e.get("raccord") is not None and V.booleen(e["raccord"], e["chemin"] + ".raccord"):
        _noter_raccord(tr, t0, t1)
    if arr and ava and max(arr) < min(ava) and any(b["id"].endswith(AXE_D) for b in bl):
        # lignes de bord de la bande centrale qui naît de largeur nulle : elles partent du même point et se recouvrent
        # sur la longueur où leur écart est inférieur à leur largeur (pointes de 0,04-0,08 m² de J4, J5, G1, G2,
        # contrôle de l'étape 2) ; la ligne du bord droit commence là où les deux lignes se touchent (largeur 3u, celle
        # que le profil leur donne) ; la ligne du bord gauche reste continue jusqu'à la pointe [G]
        bd = next(b for b in bl if b["id"].endswith(AXE_D))
        wc = 2.0 * PF.nombre(bd["largeur"])
        w = 3.0 * float(tr.ctx.get("u", 0.05) or 0.05)
        if wc > w:
            dlt = lg * w / wc
            i0, i1 = (t0, t0 + dlt) if sens == "avant" else (t1 - dlt, t1)
            tr.decos.append({"type": "interruption", "s0": i0, "s1": i1, "cible": ("limite_bande_ext", bd["id"]),
                             "motif": "autre"})
    zone = (t0, tr.L) if sens == "avant" else (0.0, t1)
    tr.mods.append({"op": "profil", "s0": zone[0], "s1": zone[1], "bandes": bl, "lim": limd, "chemin": e["chemin"],
                    "instantane": False})
    po = _prov_ev(e, "longueur", note=f"ouverture progressive sur {lg:.1f} m")
    for i, b in enumerate(bl):
        wn = PF.nombre(b["largeur"])
        wb = 0.0 if i not in assoc else PF.nombre(_largeur_resolue(tr, base[assoc[i]])[0])
        if abs(wn - wb) > 1e-9:
            w0, w1 = (wb, wn) if sens == "avant" else (wn, wb)
            tr.mods.append({"op": "loi", "s0": t0, "s1": t1, "bande": b["id"], "w0": w0, "w1": w1,
                            "chemin": e["chemin"], "prov": po})


def _noter_raccord(tr: Troncon, s0: float, s1: float):
    """Lot N1 (réseau, 18/10/2026) : intervalle d'un raccord de profil généré par le résolveur au bout d'un tronçon qui
    rejoint un nœud partagé (ouverture puis fermeture « raccord: oui ») ; les profils de transition qui y tombent ne
    sont pas des profils de conception : leurs contrôles de largeur sont rapportés « …_raccord », non bloquants."""
    if not hasattr(tr, "raccords"):
        tr.raccords = []
    tr.raccords.append((s0, s1))


def _dans_raccord(tr, s0: float, s1: float) -> bool:
    iv = sorted(getattr(tr, "raccords", []))
    fus = []
    for a, b in iv:
        if fus and a <= fus[-1][1] + 0.1:
            fus[-1] = (fus[-1][0], max(fus[-1][1], b))
        else:
            fus.append((a, b))
    return any(a - 1e-6 <= s0 and s1 <= b + 1e-6 for a, b in fus)


def _profil_en_vigueur(tr: Troncon, s: float):
    """(bandes, limites décrites) du profil en vigueur à l'abscisse s : dernier changement de profil (évènement
    « profil », « ouverture », « fermeture ») actif en s, sinon la base."""
    act = [m for m in tr.mods if m["op"] == "profil" and m["s0"] <= s + 1e-9 and m["s1"] >= s - 1e-9]
    if not act:
        return tr.base, tr.lim_base
    m = max(act, key=lambda m: m["s0"])
    return m["bandes"], m["lim"]


AXE_G, AXE_D = "_axe_g", "_axe_d"      # demi-bandes centrales d'une ouverture (référence entre elles)


def ev_fermeture(tr: Troncon, e):
    """Fermeture progressive (lot « scenes ») : inverse de l'ouverture. Sur « longueur » m avant a, les bandes du
    profil en vigueur absentes du profil « nouveau » voient leur largeur décroître jusqu'à 0 (voie d'insertion qui se
    termine en biseau, îlot qui se referme) et disparaissent en a ; les bandes communes passent linéairement à leur
    nouvelle largeur ; le nouveau profil s'applique après a."""
    nouveau = e.get("nouveau")
    if not nouveau or e.get("longueur") is None:
        raise ErreurDescription(f"{e['chemin']} : « nouveau » (profil après la fermeture) et « longueur » attendus")
    lg = V.nombre(e["longueur"], e["chemin"] + ".longueur")
    a = e["a"]
    t0 = a - lg
    if t0 < -1e-6 or a > tr.L + 1e-6 or lg <= 0:
        raise ErreurDescription(f"{e['chemin']} : la fermeture [{t0:.1f} ; {a:.1f}] sort du tronçon [0 ; {tr.L:.2f}]")
    try:
        bl, lims = FP.analyser(nouveau, e["chemin"] + ".nouveau")
        bl, lims = resoudre_bandes(bl, lims, {"contexte": {}}, e["chemin"], {"conf": tr.conf})
    except FP.ErreurFormat as x:
        raise ErreurDescription(str(x))
    cour, lim_courant = _profil_en_vigueur(tr, t0)
    cle = lambda b: (b["type"], b.get("sous_type"), b.get("sens"))  # noqa: E731
    j, assoc = 0, {}                       # indice dans le profil en vigueur → indice dans le nouveau
    for i, b in enumerate(cour):
        if j < len(bl) and cle(bl[j]) == cle(b):
            assoc[i] = j
            j += 1
    if j != len(bl):
        raise ErreurDescription(f"{e['chemin']} : la fermeture retire des bandes, elle n'en ajoute pas (bande nouvelle "
                                f"non retrouvée : {bl[j]['type']})")
    for i, k in assoc.items():
        bl[k]["id"] = cour[i]["id"]
    for b in bl:
        if b["largeur"] is None:
            b["largeur"], b["prov"]["largeur"] = PF.largeur_defaut(b, bl, tr.ctx)
    # profil de transition : bandes en vigueur, largeurs selon des lois ; puis le nouveau profil après a
    trans = copy.deepcopy(cour)
    for b in trans:
        if b["largeur"] is None:
            b["largeur"], b["prov"]["largeur"] = PF.largeur_defaut(b, trans, tr.ctx)
    tr.mods.append({"op": "profil", "s0": t0, "s1": a, "bandes": trans, "lim": lim_courant, "chemin": e["chemin"],
                    "instantane": False})
    limd = {Troncon._cle(bl, i): l for i, l in enumerate(lims) if l is not None}
    for i in range(len(bl) + 1):
        k = Troncon._cle(bl, i)
        if k not in limd and k in lim_courant:
            limd[k] = lim_courant[k]
    tr.mods.append({"op": "profil", "s0": a, "s1": tr.L, "bandes": bl, "lim": limd, "chemin": e["chemin"],
                    "instantane": False})
    e["_s0"], e["_s1"] = t0, a
    if e.get("raccord") is not None and V.booleen(e["raccord"], e["chemin"] + ".raccord"):
        _noter_raccord(tr, t0, a)
    po = _prov_ev(e, "longueur", note=f"fermeture progressive sur {lg:.1f} m")
    for i, b in enumerate(trans):
        wb = PF.nombre(b["largeur"])
        wn = 0.0 if i not in assoc else PF.nombre(bl[assoc[i]]["largeur"])
        if abs(wn - wb) > 1e-9:
            tr.mods.append({"op": "loi", "s0": t0, "s1": a, "bande": b["id"], "w0": wb, "w1": wn,
                            "chemin": e["chemin"], "prov": po})


# ================================================================================================ végétation
def trouver_bande(phrase: str, bandes: list[dict], chemin: str) -> dict:
    for b in bandes:
        if b.get("id") == str(phrase).strip():
            return b
    toks = V.jetons(phrase)
    cle, n = V.correspondance(toks, 0, V.BANDES)
    if not cle:
        raise ErreurDescription(f"{chemin} : bande « {phrase} » non reconnue")
    typ = V.BANDES[cle][0]
    cand = [b for b in bandes if b["type"] == typ]
    reste = [t for t in toks[n:] if t not in V.MOTS_VIDES]
    if not cand:
        raise ErreurDescription(f"{chemin} : aucune bande « {cle} » dans le profil")
    if reste and reste[0] in ("gauche", "droite", "droit", "centre", "centrale"):
        return cand[0] if reste[0] == "gauche" else (cand[-1] if reste[0] in ("droite", "droit") else cand[len(cand) // 2])
    if len(cand) > 1:
        raise ErreurDescription(f"{chemin} : « {phrase} » désigne {len(cand)} bandes : ajouter gauche ou droite")
    return cand[0]


def appliquer_vegetation(tr: Troncon, liste, chemin: str):
    for k, v in enumerate(liste or []):
        c = f"{chemin}[{k}]"
        if not isinstance(v, dict) or len(v) != 1:
            raise ErreurDescription(f"{c} : « - arbres: {{bande: …, pas: …}} » attendu")
        (cle, val), = v.items()
        if cle not in ("arbres", "alignement", "alignement_arbres", "alignement_d_arbres"):
            raise ErreurDescription(f"{c} : élément de végétation inconnu « {cle} » (arbres)")
        if isinstance(val, str):
            val = {"bande": val}
        ajouter_arbres(tr, trouver_bande(val.get("bande", ""), tr.base, c), val, c)
    # « bande plantée … arbres » / « trottoir … avec arbres » écrit dans le profil
    for b in tr.base:
        if b["attributs"].get("arbres") and b["type"] != "terre_plein" and not b.get("objets_le_long"):
            ajouter_arbres(tr, b, {}, b["prov"]["*"]["src"].split(":", 1)[1])


VEGETATION_JSON = DEPOT / "assets" / "specs" / "vegetation.json"      # catalogue de l'autre équipe (lecture seule)
_ESSENCES = None


def essences() -> list[dict]:
    global _ESSENCES
    if _ESSENCES is None:
        _ESSENCES = [e for e in json.loads(VEGETATION_JSON.read_text(encoding="utf-8"))["essences"]
                     if str(e.get("asset", "")).startswith("arbre_")]
    return _ESSENCES


def trouver_essence(nom: str, c: str) -> dict:
    """Essence du catalogue de végétation (assets/specs/vegetation.json) : nom d'asset, nom français ou latin, avec
    une classe de taille facultative (jeune, petit, moyen, grand ; « moyen » si plusieurs)."""
    n = V.norm(str(nom)).replace("_", " ")
    toks = n.split()
    taille = next((t for t in toks if t in ("jeune", "petit", "moyen", "grand")), None)
    cle = " ".join(t for t in toks if t not in ("jeune", "petit", "moyen", "grand"))
    cands = []
    for e in essences():
        noms = {V.norm(e["asset"]).replace("_", " "), V.norm(e.get("nom_francais", "")), V.norm(e.get("nom_latin", ""))}
        if n in noms or cle in noms or any(cle and x.startswith(cle) for x in noms):
            cands.append(e)
    if taille:
        cands = [e for e in cands if e["asset"].endswith("_" + taille)] or cands
    if len(cands) > 1:
        moy = [e for e in cands if e["asset"].endswith("_moyen")]
        cands = moy if len(moy) == 1 else cands
    if len(cands) != 1:
        raise ErreurDescription(f"{c}.essence : « {nom} » {'ambigu' if cands else 'inconnu'} dans assets/specs/vegetation.json "
                                f"({', '.join(sorted(e['asset'] for e in (cands or essences())))})")
    return cands[0]


def _nombre_cat(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def gabarit_arbre(tr: Troncon, idx: int, anc: dict, val: dict, c: str) -> tuple[dict, dict]:
    """Dimensions d'un arbre d'alignement portées dans le modèle (correction après contrôle : le rendu dessinait un
    gabarit fixe, fût 3,4 m, sans lire le modèle) : essence (asset_id), hauteur_m, houppier_rayon_m, fut_m (hauteur des
    premières branches). Dit par la description, sinon fiche de l'essence du catalogue de végétation ; fût relevé au
    gabarit de RF-OSM-VEG-001 (≥ 3,80 m si le houppier surplombe la chaussée, cible 2,50 m au-dessus d'un trottoir)."""
    import re
    if val.get("essence"):
        ess = trouver_essence(val["essence"], c)
        pess = P.description(c + ".essence", note=f"{ess['asset']} (assets/specs/vegetation.json)")
    else:
        ess = next(e for e in essences() if e["asset"] == "arbre_feuillu_generique_moyen")
        pess = P.entree("catalogue:assets/specs/vegetation.json#arbre_feuillu_generique_moyen", conf="faible",
                        note="essence non dite : feuillu générique du catalogue de végétation")
    gab = ess.get("gabarit") or {}
    out, prov = {"asset_id": ess["asset"]}, {"asset_id": pess}
    src_cat = f"catalogue:assets/specs/vegetation.json#{ess['asset']}"
    for champ, cle_d, cle_c, fac in (("hauteur_m", "hauteur", "hauteur", 1.0),
                                     ("houppier_rayon_m", "houppier_rayon", "couronne_diametre", 0.5)):
        if val.get(cle_d) is not None:
            out[champ] = V.nombre(val[cle_d], f"{c}.{cle_d}")
            prov[champ] = P.description(f"{c}.{cle_d}")
        elif _nombre_cat(gab.get(cle_c)) is not None:
            out[champ] = round(_nombre_cat(gab[cle_c]) * fac, 4)
            prov[champ] = P.entree(src_cat, conf="faible", note=f"{cle_c} de la fiche {ess['asset']}")
        else:
            raise ErreurDescription(f"{c} : {cle_d} non dit et absent de la fiche {ess['asset']} (aucune règle ne le fixe)")
    # gabarit des branches (RF-OSM-VEG-001) : bandes surplombées par le houppier dans le profil de base
    txt = str(regles.valeur("RF-OSM-VEG-001", "gabarit_branches"))
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+,\d+", txt)]
    g_ch, g_tr = nums[0], (nums[2] if len(nums) > 2 else nums[1])          # 3,80 chaussée ; 2,50 (cible) trottoir
    p0 = tr.profil_base
    t = t_limites(p0, 0.0)
    ta = {"rive_gauche": t[idx], "rive_droite": t[idx + 1]}.get(anc["reference"], 0.5 * (t[idx] + t[idx + 1])) \
        + anc.get("decalage_m", 0.0)
    R = out["houppier_rayon_m"]
    sous = set()
    for j, bd in enumerate(p0["bandes"]):
        if min(t[j], ta + R) - max(t[j + 1], ta - R) > 1e-6:
            k = PF.cle_niveau(bd)
            sous.add("chaussee" if k == "chaussee" else ("trottoir" if k in ("trottoir", "intermediaire") else "autre"))
    besoin = g_ch if "chaussee" in sous else (g_tr if "trottoir" in sous else 0.0)
    fut_ess = _nombre_cat(gab.get("fut_nu")) or 0.0
    if val.get("fut") is not None:
        out["fut_m"] = V.nombre(val["fut"], c + ".fut")
        prov["fut_m"] = P.description(c + ".fut", regle="RF-OSM-VEG-001")
        if out["fut_m"] < besoin - 1e-9:
            tr.av.append(f"{c} : fût de {out['fut_m']} m sous le gabarit de {besoin} m (houppier au-dessus de "
                         f"{', '.join(sorted(sous))}, RF-OSM-VEG-001)")
            tr.ctrl.append({"controle": "gabarit_branches", "objet": c, "valeur": out["fut_m"], "plage": [besoin, None],
                            "regle": "RF-OSM-VEG-001", "statut": "non_conforme"})
    else:
        out["fut_m"] = round(max(fut_ess, besoin), 4)
        prov["fut_m"] = P.defaut("RF-OSM-VEG-001", note=f"premières branches à max(fût de la fiche {fut_ess} m, gabarit "
                                 f"{besoin} m : houppier de {R} m au-dessus de {', '.join(sorted(sous)) or 'rien'})")
    if out["fut_m"] >= out["hauteur_m"] - 0.5:
        raise ErreurDescription(f"{c} : fût de {out['fut_m']} m pour un arbre de {out['hauteur_m']} m : préciser la hauteur")
    return out, prov


def ajouter_arbres(tr: Troncon, b: dict, val: dict, c: str):
    pas = V.nombre(val["pas"], c + ".pas") if val.get("pas") is not None else regles.valeur("DEF-030", "entraxe")
    ppas = "description" if val.get("pas") is not None else "DEF-030 (entraxe 7,50 m)"
    axe_min = regles.valeur("DEF-030", "axe_depuis_bord_chaussee_min")
    idx = tr.base.index(b)
    ref = tr.profil_base["reference"]["limite"]
    a_droite = idx >= ref
    w = PF.nombre(tr.profil_base["bandes"][idx]["largeur"])
    if b["type"] in ("trottoir", "quai_bus"):
        anc = {"reference": "rive_gauche" if a_droite else "rive_droite", "decalage_m": -axe_min if a_droite else axe_min}
        if w - axe_min < regles.valeur("RF-MA-TRO-001", "min") - 1e-9:
            tr.av.append(f"{c} : arbres dans un trottoir de {w:.2f} m : il reste {w - axe_min:.2f} m < 1,40 m de "
                         "cheminement derrière l'axe des arbres (RF-MA-TRO-001, DEF-030)")
            tr.ctrl.append({"controle": "cheminement_arbres", "bande": b["id"], "valeur": _r(w - axe_min, 3),
                            "plage": [regles.valeur("RF-MA-TRO-001", "min"), None], "regle": "RF-MA-TRO-001", "statut": "non_conforme"})
    else:
        anc = {"reference": "centre", "decalage_m": 0.0}
    o = {"id": f"arbres_{b['id']}", "famille": "vegetation", "type": "arbre_alignement"}
    dims, pdims = gabarit_arbre(tr, idx, anc, val, c)
    o.update({"asset_id": dims.pop("asset_id")})
    o.update({"mode": "pas", "pas_m": pas, "phase_m": pas / 2.0, "ancrage": anc, "orientation": {"mode": "aleatoire"},
              "exclusions": [{"type": t} for t in ("passage_pieton", "abaisse", "entree_charretiere", "arret_bus",
                                                   "triangle_visibilite", "cheminement_pmr")],
              "regles": ["DEF-030", "RF-OSM-VEG-001", "RF-GV-TPC-010"]})
    if val.get("de") is not None or val.get("a") is not None:
        o["intervalle"] = {"s0": V.nombre(val.get("de", 0), c + ".de"), "s1": V.nombre(val.get("a", tr.L), c + ".a")}
        if val.get("de") is not None:
            # « de » : premier arbre (comme « de » des avancées plantées) ; phase_m comptée depuis le début de
            # l'intervalle, comme la phase d'une ligne (constat du lot L2 : S06 donnait 12 arbres au lieu de 13)
            o["phase_m"] = 0.0
    o.update(dims)
    o["prov"] = pdims
    b.setdefault("objets_le_long", []).append(o)
    b["prov"]["objets_le_long"] = P.description(c, regle="DEF-030", note=f"alignement d'arbres, pas {pas} m ({ppas})")


def appliquer_objets(tr: Troncon, liste, chemin: str):
    for k, v in enumerate(liste or []):
        c = f"{chemin}[{k}]"
        if not isinstance(v, dict) or len(v) != 1:
            raise ErreurDescription(f"{c} : « - figurines: {{…}} », « - arbres: {{…}} » ou « - avancees_plantees: {{…}} » attendu")
        (cle, val), = v.items()
        if cle == "figurines":
            verifier_cles(val, {"gabarit", "bandes", "a", "pas", "de"}, c)
            gab = str(val.get("gabarit", "VELO")).upper()
            noms = val.get("bandes") if isinstance(val.get("bandes"), list) else [val.get("bandes")]
            for nom in noms:
                b = trouver_bande(str(nom), tr.base, c + ".bandes")
                o = {"id": f"fig_{b['id']}", "famille": "symbole_sol", "type": "figurine_velo", "gabarit": gab}
                if isinstance(val.get("a"), list):
                    o.update({"mode": "points", "s_points": [V.nombre(x, c + ".a") for x in val["a"]]})
                else:
                    o.update({"mode": "pas", "pas_m": V.nombre(val.get("pas", regles.valeur("DEF-018")), c + ".pas")})
                    if val.get("de") is not None:
                        o["phase_m"] = V.nombre(val["de"], c + ".de")
                o.update({"ancrage": {"reference": "centre", "decalage_m": 0.0}, "orientation": {"mode": "tangent"},
                          "regles": ["RF-MA-CYC-012", "DEF-018"]})
                b.setdefault("objets_le_long", []).append(o)
                b["prov"]["objets_le_long"] = P.description(c, regle="RF-MA-CYC-012")
        elif cle in ("arbres", "alignement", "alignement_arbres"):
            if isinstance(val, str):
                val = {"bande": val}
            verifier_cles(val, {"bande", "pas", "de", "a", "essence", "houppier_rayon", "hauteur", "fut"}, c)
            b = trouver_bande(str(val.get("bande", "")), tr.base, c)
            if b["type"] == "terre_plein":
                tp = b.get("terre_plein") or {"franchissable": "non"}
                b["terre_plein"] = tp
                st = tp.setdefault("plantation", {}).setdefault("strates", [])
                pas = V.nombre(val["pas"], c + ".pas") if val.get("pas") is not None else regles.valeur("DEF-030", "entraxe")
                st[:] = [x for x in st if x.get("type") != "arbre"] + [{"type": "arbre", "pas_m": pas}]
            ajouter_arbres(tr, b, val, c)
        elif cle == "avancees_plantees":
            avancees(tr, val, c)
        else:
            raise ErreurDescription(f"{c} : objet inconnu « {cle} » (figurines, arbres, avancees_plantees)")


def avancees(tr: Troncon, val: dict, c: str):
    """Avancées de trottoir plantées dans une file de stationnement, au pas (DEF-030 : arbre « entre places ») : sur
    chaque avancée, la bande de stationnement devient une bande plantée au niveau du trottoir (sous-type
    avancee_trottoir) ; la bordure suit alors l'avancée et la ligne de stationnement s'interrompt d'elle-même."""
    verifier_cles(val, {"bande", "de", "a", "pas", "longueur", "bordure", "sol", "arbre"}, c)
    b = trouver_bande(str(val.get("bande", "")), tr.base, c + ".bande")
    if b["type"] not in ("stationnement", "livraison", "zone_neutralisee"):
        raise ErreurDescription(f"{c}.bande : une avancée se place dans une file de stationnement")
    for k in ("de", "a", "pas", "longueur"):
        if val.get(k) is None:
            raise ErreurDescription(f"{c}.{k} manquant (aucune règle ne fixe la position des avancées)")
    de, a, pas, lg = (V.nombre(val[k], f"{c}.{k}") for k in ("de", "a", "pas", "longueur"))
    if V.PROFILS_BORDURE.get(V.norm(val.get("bordure", "t2"))) != "T2":
        tr.av.append(f"{c}.bordure : seule la bordure T2 de trottoir (RF-OSM-NIV-010) est posée autour des avancées au lot L0")
    sol = str(val.get("sol", "terre_nue"))
    if sol not in FP.ids_materiaux():
        raise ErreurDescription(f"{c}.sol : {sol} n'est pas un materiau_id de materiaux_sol.json")
    centres, x = [], de
    while x <= a + 1e-6:
        centres.append(round(x, 6))
        x += pas
    w, pw = _largeur_resolue(tr, b)
    idx = tr.base.index(b)
    a_droite = idx >= tr.profil_base["reference"]["limite"]
    par = {"type": "bande_plantee", "sous_type": "avancee_trottoir", "sens": "aucun", "largeur": w, "materiau_id": sol,
           "attributs": {"niveau": "trottoir"},
           "prov": {"largeur": pw, "*": P.description(c, regle="DEF-030", note=f"avancée de {lg} m au pas de {pas} m"),
                    "materiau_id": P.description(c + ".sol")}}
    arbre = val.get("arbre")
    if arbre:
        tv = V.nombre(arbre.get("t_depuis_voie", regles.valeur("DEF-030", "axe_depuis_bord_chaussee_min")), c + ".arbre.t_depuis_voie") \
            if isinstance(arbre, dict) else regles.valeur("DEF-030", "axe_depuis_bord_chaussee_min")
        if tv < regles.valeur("DEF-030", "axe_depuis_bord_chaussee_min") - 1e-9:
            tr.av.append(f"{c} : arbre à {tv} m de la voie < 1,50 m (DEF-030)")
        anc = {"reference": "rive_gauche" if a_droite else "rive_droite", "decalage_m": -tv if a_droite else tv}
        va = arbre if isinstance(arbre, dict) else {}
        verifier_cles(va, {"t_depuis_voie", "houppier_rayon", "hauteur", "fut", "essence"}, c + ".arbre")
        dims, pdims = gabarit_arbre(tr, idx, anc, va, c + ".arbre")
        o = {"id": f"arbres_{b['id']}", "famille": "vegetation", "type": "arbre_alignement",
             "asset_id": dims.pop("asset_id"), "mode": "points", "s_points": centres, "ancrage": anc,
             "orientation": {"mode": "aleatoire"}, "regles": ["DEF-030", "RF-OSM-VEG-001"]}
        o.update(dims)
        o["prov"] = pdims
        par["objets_le_long"] = [o]
        par["prov"]["objets_le_long"] = P.description(c + ".arbre", regle="DEF-030")
    for x in centres:
        s0, s1 = max(x - lg / 2, 0.0), min(x + lg / 2, tr.L)
        tr.mods.append({"op": "remplacer", "s0": s0, "s1": s1, "bande": b["id"], "chemin": c, "par": copy.deepcopy(par)})


TYPES_ABORDS = {"pelouse": ("espace_vert", "gazon_tondu"), "gazon": ("espace_vert", "gazon_tondu"),
                "herbe": ("espace_vert", "gazon_tondu"), "herbe haute": ("friche", "herbe_haute"),
                "prairie": ("friche", "herbe_haute"), "friche": ("friche", "herbe_haute"), "champ": ("champ", "terre_nue"),
                "foret": ("foret", None), "bois": ("foret", None), "massif": ("massif", "brf_bois_concasse"),
                "parking": ("parking", "enrobe_bbsg_ancien"), "haie": ("haie", None), "bati": ("bati", None)}


def appliquer_abords(tr: Troncon, ab: dict, chemin: str):
    for cote in ("gauche", "droite"):
        v = (ab or {}).get(cote)
        if v is None:
            continue
        c = f"{chemin}.{cote}"
        if isinstance(v, str) and v in FP.ids_materiaux():
            tr.av.append(f"{c} : abord « {v} » sans largeur : aucune zone créée (aucune règle ne fixe sa largeur), "
                         "noté dans meta.abords")
            tr.abords_sans_largeur[cote] = v
            continue
        if isinstance(v, str):
            toks = V.jetons(v)
            d = {}
            cle, n = V.correspondance(toks, 0, TYPES_ABORDS, 2)
            if not cle:
                raise ErreurDescription(f"{c} : type d'abord inconnu ({', '.join(sorted(TYPES_ABORDS))})")
            d["type"] = cle
            for t in toks[n:]:
                if V.NOMBRE.match(t):
                    d["largeur"] = float(t)
                elif t in ("epars", "eparses", "isoles"):
                    d["arbres"] = "epars"
                elif t in ("arbres", "avec", "m", "d", "de"):
                    pass
                else:
                    raise ErreurDescription(f"{c} : mot inconnu « {t} »")
            v = d
        typ = V.norm(v.get("type", ""))
        if typ not in TYPES_ABORDS:
            raise ErreurDescription(f"{c} : type d'abord inconnu « {v.get('type')} »")
        if v.get("largeur") is None:
            raise ErreurDescription(f"{c} : largeur de l'abord à dire (aucune règle ne la fixe)")
        larg = V.nombre(v["largeur"], c + ".largeur")
        zt, mat = TYPES_ABORDS[typ]
        ss = tr.trace.abscisses(fleche=0.01, pas_max=5.0)
        bord, ext = [], []
        for s in ss:
            p = tr.profil_a(s)
            t = t_limites(p, s)
            tb = t[0] if cote == "gauche" else t[-1]
            te = tb + larg if cote == "gauche" else tb - larg
            bord.append(tr.xy(s, tb))
            ext.append(tr.xy(s, te))
        anneau = bord + ext[::-1] + [bord[0]]
        z = {"id": f"Z-{tr.rid[2:]}.{len(tr.zones) + 1}", "type": zt, "polygone": {"exterieur": anneau},
             "attributs": {"cote": cote, "largeur_m": larg}}
        if mat:
            z["attributs"]["materiau_id"] = mat
        if v.get("arbres"):
            z["attributs"]["arbres"] = V.norm(v["arbres"])
        z["prov"] = {"*": P.description(c)}
        tr.zones.append(z)


# ================================================================================================ compilation
def materiaux_globaux(d: dict, conf: str) -> tuple[dict, str | None]:
    m = d.get("materiaux") or {}
    out, bord = {}, None
    cles = {"chaussee": "chaussee", "trottoirs": "trottoirs", "trottoir": "trottoirs", "pistes": "pistes",
            "piste": "pistes", "accotements": "accotements", "terre_plein": "vegetal", "vegetal": "vegetal",
            "quais": "quais", "bordures": "bordures"}
    for k, v in m.items():
        if k not in cles:
            raise ErreurDescription(f"materiaux.{k} : clé inconnue ({', '.join(sorted(set(cles)))})")
        cl = cles[k]
        toks = V.jetons(v)
        if cl == "bordures":
            cle, _ = V.correspondance(toks, 0, V.MATERIAUX_BORDURE, 2)
            if not cle:
                raise ErreurDescription(f"materiaux.bordures : « {v} » inconnu ({', '.join(V.MATERIAUX_BORDURE)})")
            bord = V.MATERIAUX_BORDURE[cle]
            continue
        cle, n = V.correspondance(toks, 0, V.MATERIAUX)
        reste = [t for t in toks[n:] if t not in V.MOTS_VIDES]
        if not cle:
            raise ErreurDescription(f"materiaux.{k} : « {v} » inconnu")
        mid = V.MATERIAUX[cle]
        if isinstance(mid, dict):
            mid = mid["piste" if cl == "pistes" else ("trottoir" if cl in ("trottoirs", "quais") else "chaussee")]
        for t in reste:
            if t in V.USURE_ENROBE and cl in ("chaussee", "accotements"):
                mid = V.USURE_ENROBE[t]
            elif t not in V.USURE_ENROBE:
                raise ErreurDescription(f"materiaux.{k} : mot inconnu « {t} »")
        out[cl] = (mid, P.description(f"materiaux.{k}", conf, note=str(v)))
    return out, bord


def marquages_globaux(d: dict, ctx: dict, conf: str):
    us = (d.get("contexte") or {}).get("usure_marquages")
    if us is not None:
        if not isinstance(us, (int, float)) or not 0 <= us <= 1:
            raise ErreurDescription("contexte.usure_marquages : nombre entre 0 (neuf) et 1 (effacé)")
        r, u2 = marquages_globaux(dict(d, contexte={}), ctx, conf)
        return r, (u2 if u2 is not None else float(us))
    m = d.get("marquages")
    if m is None or (isinstance(m, str) and V.norm(m) in ("auto", "automatique", "selon les regles")):
        return {}, None
    if not isinstance(m, dict):
        raise ErreurDescription("marquages : « auto » ou dictionnaire {axe, rives, entre_voies, cyclable, usure}")
    out, usure = {}, None
    for k, v in m.items():
        c = f"marquages.{k}"
        if k == "usure":
            s = V.norm(v)
            if s not in V.USURE_MARQUAGES:
                raise ErreurDescription(f"{c} : {', '.join(V.USURE_MARQUAGES)}")
            usure = V.USURE_MARQUAGES[s]
            continue
        if k not in ("axe", "rives", "entre_voies", "cyclable"):
            raise ErreurDescription(f"{c} : clé inconnue (axe, rives, entre_voies, cyclable, usure)")
        if V.norm(v) in ("auto",):
            continue
        r = FP.analyser_ligne(V.jetons("ligne " + str(v)), c)
        if r == "aucune":
            out[k] = ("aucune", P.description(c, conf))
        else:
            if "largeur_u" in r:
                r["u_m"] = ctx["u"]
            out[k] = (r, P.description(c, conf, note=str(v)))
    return out, usure


def compiler(d_brut: dict, source: str = "(objet)", sha: str | None = None, _reseau=None):
    """(modele, rapport). ErreurDescription si la description est incomplète ou incohérente.

    Réseau (lot « scenes ») : une description qui porte « carrefours », « giratoires » ou « bretelles » est compilée par
    `description/carrefours.py` (deux passes : tronçons seuls, puis tronçons + évènements posés aux branches + objets
    du réseau, construits par `_reseau(modele, rapport, contexte)` avant la validation)."""
    d = normaliser_cles(d_brut)
    if _reseau is None and any(d.get(k) for k in CLES_RESEAU):
        from description import carrefours as CR
        return CR.compiler_reseau(d, source, sha)
    verifier_cles(d, CLES_RACINE, "description")
    verifier_cles(d.get("contexte") or {}, CLES_CONTEXTE, "contexte")
    for i, t in enumerate(d.get("troncons") or []):
        verifier_cles(t, CLES_TRONCON, f"troncons[{i}]")
    if isinstance(d.get("troncon"), dict):
        verifier_cles(d["troncon"], CLES_TRONCON, "troncon")
    scene = str(d.get("scene") or Path(source).stem)
    conf = d.get("confiance", "moyenne")
    if conf not in P.CONFIANCES:
        raise ErreurDescription("confiance : haute, moyenne ou faible")
    admis = lire_ecarts_admis(d.get("ecarts_admis"))
    origine = [float(x) for x in d.get("origine", ORIGINE_DEPOT)]
    if len(origine) == 2:
        origine.append(ORIGINE_DEPOT[2])
    if d.get("troncon") is None and not d.get("troncons") and (d.get("trace") or d.get("polyligne") or d.get("longueur")):
        d["troncon"] = {k: d[k] for k in ("trace", "polyligne", "longueur", "depart", "cap", "de", "vers", "repere") if k in d}
    troncons = d.get("troncons") or ([dict(d.get("troncon") or {}, profil=d.get("profil"), evenements=d.get("evenements"),
                                           vegetation=d.get("vegetation"), abords=d.get("abords"),
                                           signalisation=d.get("signalisation"), nom=d.get("nom"))] if d.get("troncon") is not None else [])
    if not troncons:
        raise ErreurDescription("aucun tronçon : « troncon: {…} » et « profil: … » attendus")
    modele = {"schema": "modele_voie/0.1", "meta": {}, "repere": {"crs": "EPSG:2154", "origine_l93": origine,
                                                                   "z_ref": "NGF-IGN69", "convention_t": "positif_a_gauche"},
              "contexte": {"pays": "FR", "sens_circulation": "droite"}, "profils": [], "noeuds": [], "routes": []}
    rapport = {"scene": scene, "entree": source, "sha256_entree": sha, "version": VERSION, "troncons": []}
    num_p = [0]
    tous = {"marquages": [], "objets": [], "signaux": [], "zones": [], "ilots": []}
    av_glob = []
    trs = []                    # tronçons construits (compilateur de réseau)
    for k, tdesc in enumerate(troncons, start=1):
        ch = "troncon" if len(troncons) == 1 and d.get("troncon") is not None else f"troncons[{k - 1}]"
        rid = f"R-{k}"
        prof = tdesc.get("profil") if tdesc.get("profil") is not None else d.get("profil")
        if prof is None:
            raise ErreurDescription(f"{ch} : profil manquant")
        cprof = "profil" if tdesc.get("profil") is d.get("profil") else f"{ch}.profil"
        try:
            bandes, limites = FP.analyser(prof, cprof)
        except FP.ErreurFormat as e:
            raise ErreurDescription(str(e))
        dt, conf_t = d, conf                # lot N1 : matériaux, marquages et confiance propres au tronçon
        if any(tdesc.get(k) is not None for k in ("materiaux", "marquages", "confiance")):
            dt = dict(d, **{k: tdesc[k] for k in ("materiaux", "marquages", "confiance") if tdesc.get(k) is not None})
            conf_t = dt.get("confiance", "moyenne")
            if conf_t not in P.CONFIANCES:
                raise ErreurDescription(f"{ch}.confiance : haute, moyenne ou faible")
        ctxd = lire_contexte(dict(dt, contexte=dict(d.get("contexte") or {}, **(tdesc.get("contexte") or {}))), bandes)
        bandes, limites = resoudre_bandes(bandes, limites, dt, cprof, ctxd)
        mats, mat_bord = materiaux_globaux(dt, conf_t)
        ctx = PF.contexte(ctxd["agglomeration"], ctxd["vitesse"], ctxd["categorie"], u=ctxd.get("u"), prov_u=ctxd.get("prov_u"),
                          prov_agglomeration=ctxd["prov_agglomeration"], prov_vitesse=ctxd["prov_vitesse"], materiaux=mats)
        cx = dict(d.get("contexte") or {}, **(tdesc.get("contexte") or {}))
        if cx.get("v15") is not None or cx.get("v15_kmh") is not None:
            ctx["v15"] = V.nombre(cx.get("v15") if cx.get("v15") is not None else cx["v15_kmh"], "contexte.v15")
        ctx["marquages"], ctx["usure_marquages"] = marquages_globaux(dt, ctx, conf_t)
        trace = lire_trace(tdesc, origine, ch)
        if getattr(trace, "_cassure", 0) > 1.0:
            av_glob.append(f"{ch}.polyligne : cassure de {trace._cassure:.1f}° non raccordée (préférer « trace » avec arcs)")
        try:
            tr = Troncon(rid, trace, bandes, limites, ctx, ch, conf_t)
        except PF.ErreurProfil as e:
            raise ErreurDescription(f"{cprof} : {e}")
        tr.admis = admis
        appliquer_vegetation(tr, tdesc.get("vegetation") if tdesc.get("vegetation") is not None else d.get("vegetation"), "vegetation")
        appliquer_objets(tr, tdesc.get("objets") if tdesc.get("objets") is not None else d.get("objets"), "objets")
        evs = lire_evenements(tdesc.get("evenements") if tdesc.get("evenements") is not None else d.get("evenements"), "evenements")
        evs += [dict(e, type="panneau", chemin=f"signalisation[{i}]") for i, e in
                enumerate((tdesc.get("signalisation") if tdesc.get("signalisation") is not None else d.get("signalisation")) or [])]
        for e in evs:
            if e["type"] == "panneau" and not isinstance(e.get("a"), float):
                e["a"] = V.nombre(e["a"], e["chemin"] + ".a")
        evs.sort(key=lambda e: (e["a"], e["type"], e["chemin"]))
        appliquer_evenements(tr, evs, d)
        try:
            tr.construire(num_p)
        except PF.ErreurProfil as e:
            raise ErreurDescription(f"{cprof} : {e}")
        for f in tr._apres:
            f()
        if getattr(tr, "_redecorer", False):
            tr._decorer()
        appliquer_abords(tr, tdesc.get("abords") if tdesc.get("abords") is not None else d.get("abords"), "abords")
        if mat_bord:
            for p in tr.profils:
                for lim in p["limites"]:
                    if "bordure" in lim["nature"] and "materiau_id" not in lim["bordure"]:
                        lim["bordure"]["materiau_id"] = mat_bord
        # nœuds, route
        x0, y0, _ = trace.point(0.0)
        x1, y1, _ = trace.point(trace.longueur)
        n0, n1 = f"N-{2 * k - 1}", f"N-{2 * k}"
        for nid, x, y in ((n0, x0, y0), (n1, x1, y1)):
            modele["noeuds"].append({"id": nid, "position": [_r(x), _r(y)], "type": "limite_carte", "routes": [rid],
                                     "prov": {"type": P.solveur("troncon", note="extrémité d'un tronçon décrit seul (pas de carrefour au lot L0)")}})
        sens_u = tr.sens_unique and not any(b["sens"] == "double" and b["type"] in PF.VOIES_MOTORISEES for b in tr.base)
        route = {"id": rid, "noeud_debut": n0, "noeud_fin": n1}
        if tdesc.get("nom") or d.get("nom"):
            route["nom"] = str(tdesc.get("nom") or d.get("nom"))
        route.update({"categorie": ctx["categorie"], "agglomeration": ctx["agglomeration"], "vitesse_kmh": ctx["vitesse_kmh"],
                      "sens_unique": "oui" if sens_u else "non",
                      "ligne_reference": {"geometrie": [tr.xy(s, 0.0) for s in trace.abscisses()],
                                          "geometrie_reguliere": [p.vers_schema() for p in trace.primitives],
                                          "longueur_m": _r(trace.longueur)},
                      "sections": [dict({"s0": _r(s["s0"]), "s1": _r(s["s1"]), "profil": s["profil"]},
                                        **({"transition_entree": s["transition_entree"]} if "transition_entree" in s else {}))
                                   for s in tr.secs]})
        for cle, lst in (("objets", tr.objets), ("marquages", tr.marquages), ("signaux", tr.signaux)):
            if lst:
                route[cle] = [o["id"] for o in lst]
        route["prov"] = {"categorie": ctxd["prov_categorie"], "agglomeration": ctxd["prov_agglomeration"],
                         "vitesse_kmh": ctxd["prov_vitesse"],
                         "sens_unique": P.inference("RF-OSM-PRF-002", note="déduit du sens des voies décrites"),
                         "ligne_reference": P.description(ch, conf_t, note="tracé décrit")}
        modele["profils"] += tr.profils
        modele["routes"].append(route)
        if ctx.get("prov_u") and ctx["prov_u"]["src"].startswith("description"):
            modele["contexte"].setdefault("u_itineraires", {})[rid] = ctx["u"]
        for cle, lst in (("marquages", tr.marquages), ("objets", tr.objets), ("signaux", tr.signaux), ("zones", tr.zones),
                         ("ilots", tr.ilots)):
            tous[cle] += lst
        trs.append({"rid": rid, "tr": tr, "desc": tdesc, "ctx": ctx, "ctxd": ctxd, "chemin": ch, "route": route})
        rapport["troncons"].append({"route": rid, "longueur_m": _r(trace.longueur, 3), "sections": len(tr.secs),
                                    "profils": [p["id"] for p in tr.profils], "evenements": len(evs),
                                    "avertissements": tr.av, "controles": tr.ctrl,
                                    "non_portes_par_le_schema": tr.non_portes,
                                    "_abords": {f"{rid}.{k}": v for k, v in tr.abords_sans_largeur.items()}})
    if _reseau is not None:
        _reseau(modele, rapport, {"tous": tous, "num_p": num_p, "trs": trs, "conf": conf, "admis": admis,
                                  "origine": origine, "d": d, "av_glob": av_glob})
    for cle in ("ilots", "marquages", "objets", "signaux", "zones"):
        if tous[cle]:
            modele[cle] = tous[cle]
    # écarts admis : un contrôle non conforme ou hors plage dont la règle est admise par la description devient
    # « <statut>_admis » (motif recopié) ; les autres restent bloquants pour la fabrication (fabriquer_generateur)
    utilises = set()
    for t in rapport["troncons"] + ([{"controles": rapport["reseau"]["controles"]}] if "reseau" in rapport else []):
        for c in t["controles"]:
            if c.get("statut") in ("non_conforme", "hors_plage") and c.get("regle") in admis:
                c["statut"] += "_admis"
                c["motif"] = admis[c["regle"]]
                utilises.add(c["regle"])
    for r in sorted(set(admis) - utilises):
        av_glob.append(f"ecarts_admis : {r} admis sans aucun contrôle non conforme correspondant (à retirer)")
    rapport["ecarts_admis"] = admis
    rapport["non_conformites"] = [dict(c, route=t["route"]) for t in rapport["troncons"] for c in t["controles"]
                                  if c.get("statut") in STATUTS_BLOQUANTS]
    if "reseau" in rapport:
        rapport["non_conformites"] += [dict(c, route="reseau") for c in rapport["reseau"]["controles"]
                                       if c.get("statut") in STATUTS_BLOQUANTS]
    meta = {"auteur": "description simple compilée par recon/generateur/description/description_vers_modele.py",
            "zone": scene}
    if d.get("date"):
        meta["date"] = str(d["date"])
    if d.get("description"):
        meta["description"] = str(d["description"]).strip()
    meta["sources"] = [source, "assets/specs/route/regles_route_fr.json"]
    meta["compilateur"] = VERSION
    meta["base_regles"] = {k: regles.empreinte()[k] for k in ("schema", "date", "sha256")}
    meta["conventions"] = CONVENTIONS
    if sha:
        meta["sha256_description"] = sha
    if d.get("titre"):
        meta["titre"] = str(d["titre"])
    abs_ = {}
    for t in rapport["troncons"]:
        abs_.update(t.pop("_abords", {}))
    if abs_:
        meta["abords"] = abs_
    modele["meta"] = meta
    regulieres = [copy.deepcopy(r["ligne_reference"].get("geometrie_reguliere")) for r in modele["routes"]]
    modele = arrondir(modele)
    # géométrie régulière : l'arrondi général à 0,1 mm ne vaut pas pour les courbures et les caps (courbure 1/60
    # arrondie à 0,0167 : arc de 59,88 m, raccord suivant décalé de 6 cm, relevé par le lot L1) ; positions et
    # longueurs au µm, cap au 1e-9 degré, courbures à 1e-12 m⁻¹
    PREC = {"x0": 6, "y0": 6, "s0": 6, "longueur": 6, "cap_deg": 9, "courbure0": 12, "courbure1": 12}
    for r, g in zip(modele["routes"], regulieres):
        if g:
            r["ligne_reference"]["geometrie_reguliere"] = [
                {k: (round(float(v), PREC[k]) + 0.0 if k in PREC else v) for k, v in pr.items()} for pr in g]
    # validation
    import valider_modele as VM
    err, av_v, stats = VM.valider(modele, exiger_prov=True)
    rapport["avertissements"] = av_glob
    rapport["validation"] = {"erreurs": [list(e) for e in err], "nb_erreurs": len(err), "avertissements": av_v,
                             "prov_genres": stats.get("prov_genres"), "regles_citees": stats.get("regles_citees"),
                             "prov_manquantes": stats.get("prov_manquantes")}
    rapport["regles_utilisees"] = regles_utilisees(modele)
    if d.get("attendus") is not None:
        rapport["attendus_declares"] = d["attendus"]
    return modele, rapport


STATUTS_BLOQUANTS = ("non_conforme", "hors_plage")


def lire_ecarts_admis(v) -> dict:
    """« ecarts_admis: {RF-MA-RAL-001: "dos-d'âne existant relevé sur photo"} » : règle de la base -> motif (texte non
    vide). Une règle inconnue est une erreur ; un écart admis sert à décrire un cas réel non conforme, jamais un défaut."""
    if v is None:
        return {}
    if not isinstance(v, dict):
        raise ErreurDescription("ecarts_admis : dictionnaire « règle: motif » attendu")
    out = {}
    for k, m in v.items():
        rid = str(k).strip().upper().replace("_", "-")
        try:
            regles.defaut(rid) if rid.startswith("DEF-") else regles.regle(rid)
        except KeyError:
            raise ErreurDescription(f"ecarts_admis : règle inconnue de regles_route_fr.json : {k}")
        if not str(m or "").strip():
            raise ErreurDescription(f"ecarts_admis.{k} : motif à dire (cas réel, preuve)")
        out[rid] = str(m).strip()
    return dict(sorted(out.items()))


def regles_utilisees(modele) -> dict:
    out = {}

    def parcours(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "regle" and isinstance(v, str):
                    out[v] = out.get(v, 0) + 1
                elif k == "regles" and isinstance(v, list):
                    for x in v:
                        out[x] = out.get(x, 0) + 1
                else:
                    parcours(v)
        elif isinstance(o, list):
            for x in o:
                parcours(x)
    parcours(modele)
    return dict(sorted(out.items()))


def ecrire_json(o, chemin: Path):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes((json.dumps(o, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def _reseau():
    """Résolveur de la couche réseau (lot N1, recon/generateur/reseau/resoudre_reseau.py), importé à la demande."""
    if str(GEN / "reseau") not in sys.path:
        sys.path.insert(0, str(GEN / "reseau"))
    import resoudre_reseau
    return resoudre_reseau


def compiler_fichier(entree: Path, sortie: Path | None = None):
    octets = entree.read_bytes()
    texte = octets.decode("utf-8")
    d = json.loads(texte) if entree.suffix.lower() == ".json" else yaml_simple.charger(texte)
    try:
        src = str(entree.resolve().relative_to(DEPOT)).replace("\\", "/")
    except ValueError:
        src = str(entree).replace("\\", "/")
    # lot N1 (18/10/2026) : une description qui utilise la couche réseau (nœuds nommés ou partagés, valeurs approchées,
    # état décrit, positions en mots…, FORMAT_DESCRIPTION_RESEAU.md) est d'abord résolue en description exacte ; une
    # description au format de l'étape 2 n'est pas touchée (même chemin qu'avant)
    rap_reseau = None
    if entree.suffix.lower() != ".json":
        RR = _reseau()
        if RR.est_reseau(d):
            d, rap_reseau = RR.resoudre_dict(d, src, entree.resolve().parent)
    modele, rapport = compiler(d, src, hashlib.sha256(octets).hexdigest())
    if rap_reseau is not None:
        RR.apres_compilation(rap_reseau, d, modele, rapport)
    if sortie is None:
        sortie = SORTIE_DEFAUT / rapport["scene"]
    ecrire_json(modele, sortie / "modele_voie.json")
    ecrire_json(rapport, sortie / "compilation.json")
    if rap_reseau is not None:
        RR.ecrire_sorties(rap_reseau, d, sortie, hashlib.sha256(octets).hexdigest())
    return modele, rapport, sortie


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("description")
    ap.add_argument("--sortie", help="dossier de sortie (défaut recon/out/generateur/<scene>/)")
    ap.add_argument("--verifier-determinisme", action="store_true", help="compile deux fois et compare à l'octet")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    from description import description_vers_modele as _paquet      # même module importé par le réseau (carrefours.py)
    try:
        modele, rapport, sortie = compiler_fichier(Path(a.description), Path(a.sortie) if a.sortie else None)
    except (ErreurDescription, _paquet.ErreurDescription, yaml_simple.ErreurYaml) as e:
        print(f"ERREUR\t{e}")
        return 2
    for t in rapport["troncons"]:
        for w in t["avertissements"]:
            print(f"AVERTISSEMENT\t{t['route']}\t{w}")
    for w in rapport["avertissements"]:
        print(f"AVERTISSEMENT\t{w}")
    for e in rapport["validation"]["erreurs"]:
        print("VALIDATION\t" + "\t".join(e))
    for c in rapport["non_conformites"]:
        print(f"NON CONFORME\t{c['route']}\t{c.get('controle')}\t{c.get('regle')}\t{c.get('statut')}\t"
              f"{json.dumps(c.get('valeur'), ensure_ascii=False)}")
    print(f"{rapport['scene']} : {sum(t['sections'] for t in rapport['troncons'])} section(s), "
          f"{len(modele['profils'])} profil(s), {rapport['validation']['nb_erreurs']} erreur(s) de validation, "
          f"{len(rapport['non_conformites'])} non-conformité(s) non admise(s) → {sortie}")
    if a.verifier_determinisme:
        o1 = (sortie / "modele_voie.json").read_bytes()
        m2, _, _ = compiler_fichier(Path(a.description), sortie / "_bis")
        o2 = (sortie / "_bis" / "modele_voie.json").read_bytes()
        same = o1 == o2
        print(f"déterminisme : {'identique' if same else 'DIFFÉRENT'} (sha256 {hashlib.sha256(o1).hexdigest()[:16]})")
        for f in (sortie / "_bis").iterdir():
            f.unlink()
        (sortie / "_bis").rmdir()
        if not same:
            return 3
    return 1 if rapport["validation"]["nb_erreurs"] else 0


if __name__ == "__main__":
    sys.exit(main())
