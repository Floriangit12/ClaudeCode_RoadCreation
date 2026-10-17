# -*- coding: utf-8 -*-
"""Inférence OSM → modèle `modele_voie/0.1` (lot L0 ; PLAN_GENERATEUR § 2.1, étape [0]).

    python recon/generateur/inference/osm_vers_modele.py ENTREE.(osm|osm.pbf|geojson) [--sortie DOSSIER]
           [--agglomeration oui|non|auto] [--emprise X0 Y0 X1 Y1] [--nom NOM]

Chaîne (INFERENCE_OSM_VERS_PROFIL.md § 1, ordre d'osm2streets) : lecture et Lambert-93 (`osm_lecture.py`) ;
découpe des ways aux nœuds partagés (RF-OSM-CAR-001) ; contexte (RF-OSM-AGG-001, table highway_vers_categorie,
RF-OSM-MRQ-001, RF-OSM-VIT-001 à -004) ; profil (RF-OSM-VOI-*, -CYC-*, -STA-001, -TRO-*, -LAR-*, -NIV-*, -PRF-*,
construit par `commun/profil.py`, le même constructeur que la description simple) ; carrefours et régimes
(RF-OSM-CAR-002, -010, -011 + ARB-19, -012, -020) ; passages (RF-OSM-CAR-040, -041) ; signaux (RF-OSM-PAN-001) ;
modération (RF-OSM-TC-001) ; ouvrages (RF-OSM-OUV-001). Chaque valeur porte sa provenance : `osm:tag/<clé>`,
`osm:node/<id>`, `defaut:<règle>`, `inference:<règle>`, ou la table du volet 12.

Hors périmètre du lot L0 (lots suivants) : géométrie des carrefours (frontière, coins, trajectoires), rattachement
des ways séparés (RF-OSM-CYC-003, RF-OSM-PRF-011), BD TOPO (RF-OSM-BDT-001).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(GEN / "schema"))
sys.path.insert(0, str(ICI))
import regles  # noqa: E402
from commun import profil as PF  # noqa: E402
from commun import prov as P  # noqa: E402
import osm_lecture  # noqa: E402

DEPOT = GEN.parents[1]
VERSION = "osm_vers_modele/1.0"
ORIGINE_DEPOT = [917279.43, 6460289.98, 216.3]

ROUTIERS = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
            "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "service", "road", "cycleway"}
RANG = {"motorway": 0, "trunk": 1, "primary": 2, "secondary": 3, "tertiary": 4, "unclassified": 5, "residential": 6,
        "living_street": 7, "service": 8, "road": 6, "cycleway": 9}
DEUX_VOIES_SANS_TAG = {"motorway", "trunk", "primary", "secondary", "tertiary", "motorway_link", "trunk_link",
                       "primary_link", "secondary_link", "tertiary_link", "residential", "road"}
TROTTOIRS_AGGLO = {"primary", "secondary", "tertiary", "unclassified", "residential", "primary_link", "secondary_link",
                   "tertiary_link", "road"}
SURFACES = {  # table surface_vers_materiau (volet 12) : surface → (chaussée, trottoir, piste)
    "asphalt": ("enrobe_bbsg_ancien", "enrobe_trottoir", "enrobe_piste_cyclable"),
    "concrete": ("beton_balaye",) * 3, "concrete:plates": ("dalles_beton",) * 3, "paving_stones": ("paves_beton",) * 3,
    "sett": ("paves_granit",) * 3, "compacted": ("stabilise_beige",) * 3, "fine_gravel": ("stabilise_beige",) * 3,
    "gravel": ("gravier_concasse_6_10",) * 3, "pebblestone": ("gravier_concasse_6_10",) * 3, "grass": ("gazon_tondu",) * 3,
    "dirt": ("terre_nue",) * 3, "ground": ("terre_nue",) * 3, "earth": ("terre_nue",) * 3}
TURN_FLECHE = {"through": "TD", "left": "TAG", "slight_left": "TAG", "sharp_left": "TAG", "right": "TAD",
               "slight_right": "TAD", "sharp_right": "TAD", "merge_to_left": "RABATTEMENT_G", "merge_to_right": "RABATTEMENT_D"}


class ErreurInference(ValueError):
    pass


def _r(x, nd=4):
    v = round(float(x), nd)
    return 0.0 if v == 0 else v


def arrondir(o, nd=4):
    if isinstance(o, float):
        return _r(o, nd)
    if isinstance(o, dict):
        return {k: arrondir(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [arrondir(v, nd) for v in o]
    return o


def oui(v) -> bool:
    return str(v).lower() in ("yes", "true", "1")


def nombre_osm(v):
    """« 3.5 », « 3,5 », « 3.5 m » → 3.5 ; None si illisible."""
    if v is None:
        return None
    m = re.match(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*(m)?\s*$", str(v))
    return float(m.group(1).replace(",", ".")) if m else None


def cote_tag(tags, base, cote):
    """Valeur de base:<cote>, sinon base:both, sinon base (clés OSM « côté »)."""
    for k in (f"{base}:{cote}", f"{base}:both", base):
        if k in tags:
            return tags[k], k
    return None, None


# ================================================================================================ contexte d'un way
def contexte_way(tags: dict, agglomeration, contexte_scene: dict | None = None):
    """(ctx de construction, infos route) : catégorie, agglomération, vitesse, u, matériaux, avec provenances."""
    hw = tags.get("highway", "")
    info = {"prov": {}}
    # agglomération (RF-OSM-AGG-001)
    if agglomeration is None:
        v = nombre_osm(tags.get("maxspeed"))
        if v is not None:
            agglomeration = v <= 50
            info["prov"]["agglomeration"] = P.inference("RF-OSM-AGG-001", conf="faible", note="indice : maxspeed ≤ 50")
        else:
            agglomeration = hw in ("residential", "living_street", "service")
            info["prov"]["agglomeration"] = P.inference("RF-OSM-AGG-001", conf="faible",
                                                        note="aucune limite d'agglomération fournie : déduite de la classe")
    else:
        info["prov"]["agglomeration"] = P.entree("contexte:agglomeration", "RF-OSM-AGG-001", "haute",
                                                 note="agglomération fournie par le contexte de la scène")
    info["agglomeration"] = bool(agglomeration)
    # catégorie (table highway_vers_categorie)
    ref = tags.get("ref", "")
    base = hw.replace("_link", "") if hw.endswith("_link") and hw not in ("motorway_link", "trunk_link") else hw
    if hw in ("motorway_link", "trunk_link"):
        cat = "bretelle"
    elif base == "motorway":
        cat = "autoroute"
    elif base == "trunk":
        cat = "voie_express"
    elif tags.get("junction") in ("roundabout", "circular"):
        cat = "anneau_giratoire"
    elif base in ("primary", "secondary", "tertiary"):
        if agglomeration:
            cat = "rue"
        elif ref.startswith("N"):
            cat = "route_nationale"
        elif ref.startswith("D") or base in ("primary", "secondary"):
            cat = "route_departementale"
        else:
            cat = "route_communale"
    else:
        cat = {"unclassified": "route_communale", "residential": "rue", "living_street": "zone_rencontre",
               "service": "voie_service", "cycleway": "piste_cyclable_independante", "road": "rue"}.get(base, "rue")
    info["categorie"] = cat
    info["prov"]["categorie"] = P.table("highway_vers_categorie", note=f"highway={hw}" + (f", ref={ref}" if ref else ""))
    # vitesse (RF-OSM-VIT-001 à -004)
    ms = tags.get("maxspeed", "")
    v = nombre_osm(ms)
    if v is not None:
        vit, pv = (int(v) if v == int(v) else v), P.osm("tag/maxspeed", "RF-OSM-VIT-001")
    elif ms == "FR:walk":
        vit, pv = 6, P.osm("tag/maxspeed", "RF-OSM-VIT-001", note="allure du pas, 6 km/h pour la simulation")
    elif "FR:30" in (tags.get("zone:maxspeed", ""), tags.get("source:maxspeed", "").replace("zone", "")) or ms == "FR:zone30":
        vit, pv = regles.valeur("RF-OSM-VIT-004", "zone30"), P.osm("tag/zone:maxspeed", "RF-OSM-VIT-004")
    elif hw == "living_street":
        vit, pv = regles.valeur("RF-OSM-VIT-004", "zone_rencontre"), P.defaut("RF-OSM-VIT-004", note="zone de rencontre")
    elif agglomeration:
        vit, pv = regles.valeur("RF-OSM-VIT-002", "defaut"), P.defaut("RF-OSM-VIT-002")
    elif cat == "autoroute":
        vit, pv = regles.valeur("RF-OSM-VIT-003", "autoroute"), P.defaut("RF-OSM-VIT-003", note="autoroute")
    else:
        vit, pv = regles.valeur("RF-OSM-VIT-003", "route_bidirectionnelle_sans_separateur"), P.defaut("RF-OSM-VIT-003")
    info["vitesse_kmh"], info["prov"]["vitesse_kmh"] = vit, pv
    # matériaux (table surface_vers_materiau)
    mats = {}
    for cle, cl, k in (("surface", "chaussee", 0), ("sidewalk:surface", "trottoirs", 1), ("cycleway:surface", "pistes", 2)):
        if tags.get(cle) in SURFACES:
            mats[cl] = (SURFACES[tags[cle]][k], P.osm(f"tag/{cle}", note="table surface_vers_materiau du volet 12"))
    u = (contexte_scene or {}).get("u_itineraires", {}).get(ref) if ref else None
    ctx = PF.contexte(agglomeration, vit, cat, prov_agglomeration=info["prov"]["agglomeration"], prov_vitesse=pv,
                      materiaux=mats, u=u, prov_u=P.entree("contexte:u_itineraires", "RF-OSM-MRQ-001", "haute") if u else None)
    info["u_m"] = ctx["u"]
    return ctx, info


# ================================================================================================ profil
def _bande(typ, sens, largeur=None, prov_l=None, src="", regle=None, **attrs):
    b = {"type": typ, "sous_type": attrs.pop("sous_type", None), "sens": sens, "largeur": largeur,
         "prov": {"*": P.osm(src, regle) if src else P.inference(regle or "RF-OSM-PRF-001")}, "attributs": attrs.pop("attributs", {})}
    if largeur is not None:
        b["prov"]["largeur"] = prov_l
    b.update({k: v for k, v in attrs.items() if v is not None})
    return b


def profil_depuis_tags(tags: dict, agglomeration=None, contexte_scene: dict | None = None, pid: str = "P-1"):
    """Profil d'un way OSM. Retourne (profil, infos route, avertissements, contrôles)."""
    tags = dict(tags)
    hw = tags.get("highway", "")
    av = []
    if tags.get("oneway") == "-1":            # sens inverse : on raisonne comme un oneway=yes retourné
        tags = inverser_tags(tags)
        av.append("oneway=-1 : way retourné (géométrie et clés :left/:right échangées)")
    ctx, info = contexte_way(tags, agglomeration, contexte_scene)
    agglo = info["agglomeration"]
    rond = tags.get("junction") in ("roundabout", "circular")
    oneway = oui(tags.get("oneway")) or rond or hw in ("motorway",) and tags.get("oneway") != "no"
    info["sens_unique"] = "oui" if oneway else "non"
    info["prov"]["sens_unique"] = P.osm("tag/oneway", "RF-OSM-VOI-001") if "oneway" in tags else P.inference(
        "RF-OSM-VOI-002", note="giratoire ou autoroute : sens unique implicite" if oneway else "oneway absent : double sens")
    if hw == "cycleway":
        return profil_piste(tags, ctx, info, pid, av)
    # ---------------------------------------------------------------- voies (RF-OSM-VOI-001 à -004)
    lanes = nombre_osm(tags.get("lanes"))
    both = int(nombre_osm(tags.get("lanes:both_ways")) or 0)
    fwd = bwd = None
    partagee = False
    if lanes is not None:
        n = int(lanes)
        pvo = P.osm("tag/lanes", "RF-OSM-VOI-001")
        if oneway:
            fwd, bwd = n, 0
        else:
            f, b_ = nombre_osm(tags.get("lanes:forward")), nombre_osm(tags.get("lanes:backward"))
            reste = n - both
            if f is not None and b_ is not None:
                fwd, bwd = int(f), int(b_)
            elif f is not None:
                fwd, bwd = int(f), reste - int(f)
            elif b_ is not None:
                fwd, bwd = reste - int(b_), int(b_)
            else:
                bwd = reste // 2
                fwd = reste - bwd
                pvo = P.osm("tag/lanes", "RF-OSM-VOI-001", note="répartition : arrière = ⌊n/2⌋, avant = n − arrière")
    else:
        if oneway:
            fwd, bwd = 1, 0
            pvo = P.defaut("RF-OSM-VOI-002", note="oneway sans lanes : 1 voie")
        elif hw in DEUX_VOIES_SANS_TAG:
            fwd, bwd = 1, 1
            pvo = P.defaut("RF-OSM-VOI-002", note=f"{hw} sans lanes : 1 + 1")
        else:
            w = nombre_osm(tags.get("width"))
            if w is not None and w >= regles.valeur("RF-OSM-MRQ-010", "largeur_circulable_min_pour_axe"):
                fwd, bwd = 1, 1
                pvo = P.defaut("RF-OSM-VOI-002", note=f"{hw} sans lanes, width ≥ 5,20 : 1 + 1 sans axe")
                ctx["marquages"] = {"axe": ("aucune", P.defaut("RF-OSM-VOI-002", note="1 + 1 sans axe"))}
            else:
                partagee = True
                pvo = P.defaut("RF-OSM-VOI-002", note=f"{hw} sans lanes : chaussée partagée")
    # voies bus (RF-OSM-VOI-003)
    bus = {"avant": 0, "arriere": 0}
    bw = tags.get("busway")
    if bw == "lane":
        bus = {"avant": 1, "arriere": 0 if oneway else 1}
    elif bw == "opposite_lane":
        bus["arriere"] = 1
    for cote, sens in (("right", "avant"), ("left", "arriere")):
        v = tags.get(f"busway:{cote}") or tags.get("busway:both")
        if v == "lane":
            bus["avant" if oneway else sens] = 1       # voie la plus à droite du sens (RF-OSM-VOI-003)
        elif v == "opposite_lane":
            bus["arriere"] = 1
    lb = nombre_osm(tags.get("lanes:bus")) or nombre_osm(tags.get("lanes:psv"))
    if lb and not any(bus.values()):
        bus["avant"] = int(lb) if oneway else 1
        if not oneway and int(lb) >= 2:
            bus["arriere"] = 1
    # largeurs par voie (width:lanes) et turn:lanes
    tl = {"avant": _liste(tags.get("turn:lanes:forward") or (tags.get("turn:lanes") if oneway else None)),
          "arriere": _liste(tags.get("turn:lanes:backward"))}
    wl = {"avant": _liste(tags.get("width:lanes:forward") or (tags.get("width:lanes") if oneway else None)),
          "arriere": _liste(tags.get("width:lanes:backward"))}
    voies = {"avant": [], "arriere": []}
    if partagee:
        voies_centre = [_bande("chaussee_partagee", "double", None, None, "tag/highway", "RF-OSM-VOI-002")]
    else:
        voies_centre = []
        for sens, n in (("avant", fwd or 0), ("arriere", bwd or 0)):
            nb_bus = min(bus[sens], n) if lanes is not None else bus[sens]
            n_gen = n - nb_bus if lanes is not None else n
            for k in range(n_gen + nb_bus):
                est_bus = k >= n_gen
                typ = "voie_bus" if est_bus else "voie_circulation"
                t = tl[sens][k] if k < len(tl[sens]) else None
                if t and not est_bus and "through" not in t and t not in ("none", ""):
                    if "left" in t and "right" not in t:
                        typ = "voie_tourne_gauche"
                    elif "right" in t and "left" not in t:
                        typ = "voie_tourne_droite"
                w = nombre_osm(wl[sens][k]) if k < len(wl[sens]) else None
                b = _bande(typ, sens, w, P.osm("tag/width:lanes", "RF-OSM-LAR-001") if w else None,
                           "tag/lanes" if lanes is not None else "", "RF-OSM-VOI-003" if est_bus else "RF-OSM-VOI-001")
                b["prov"]["*"] = P.osm("tag/busway", "RF-OSM-VOI-003") if est_bus else pvo
                if t:
                    b["attributs"]["turn"] = t
                if est_bus and _cyc(tags, "right" if sens == "avant" else "left") == "share_busway":
                    b["usagers"] = ["bus", "velo"]
                voies[sens].append(b)
        # ordre de gauche à droite : voies arrière (la plus à gauche d'abord : pour les usagers arrière, leur voie de
        # droite est la plus à gauche du profil), puis voies avant (de la plus à gauche à la plus à droite)
        arr = list(reversed(voies["arriere"]))       # turn:lanes:backward se lit de la gauche des usagers arrière
        if both:
            voies_centre = arr + [_bande("voie_centrale_banalisee", "double", None, None, "tag/lanes:both_ways", "RF-OSM-VOI-001")] + voies["avant"]
        else:
            voies_centre = arr + voies["avant"]
    # ---------------------------------------------------------------- côtés (RF-OSM-PRF-001 : du centre vers l'extérieur)
    cotes = {}
    for cote in ("left", "right"):
        sens = ("arriere" if cote == "left" else "avant") if not (oneway or partagee) else ("avant" if oneway else "double")
        if oneway and cote == "left":
            sens = "avant"
        seq, lims = cote_profil(tags, cote, sens, oneway, agglo, hw, info, av)
        cotes[cote] = (seq, lims)
    gauche, lg = cotes["left"]
    droite, ld = cotes["right"]
    bandes = list(reversed(gauche)) + voies_centre + droite
    # limites explicites (séparation cyclable) : clés (bande_gauche_idx, bande_droite_idx) locales
    limites = [None] * (len(bandes) + 1)
    off_c = len(gauche)
    for (i_loc, lim) in lg:     # i_loc compté depuis le centre vers l'extérieur, limite côté centre de la bande i_loc
        limites[off_c - i_loc] = lim
    off_d = len(gauche) + len(voies_centre)
    for (i_loc, lim) in ld:
        limites[off_d + i_loc] = lim
    # ---------------------------------------------------------------- largeur de chaussée connue (RF-OSM-LAR-001)
    repartir_largeur(tags, bandes, ctx, av)
    try:
        profil, w2, ctrl = PF.construire_profil(pid, bandes, limites, ctx, nom=f"highway={hw}")
    except PF.ErreurProfil as e:
        raise ErreurInference(f"profil impossible pour {hw} : {e}")
    av += w2
    if "placement" in tags:
        info["placement"] = placement(tags["placement"])
    return profil, info, av, ctrl


def _liste(v):
    return [x.strip() for x in v.split("|")] if v else []


def _cyc(tags, cote):
    v, _ = cote_tag(tags, "cycleway", cote)
    return v


def inverser_tags(tags: dict) -> dict:
    out = {}
    for k, v in tags.items():
        k2 = k.replace(":left", ":__G").replace(":right", ":left").replace(":__G", ":right")
        k2 = k2.replace(":forward", ":__F").replace(":backward", ":forward").replace(":__F", ":backward")
        out[k2] = v
    out["oneway"] = "yes"
    out["_inverse"] = "yes"
    return out


def cote_profil(tags, cote, sens_voie, oneway, agglo, hw, info, av):
    """Bandes d'un côté, du centre vers l'extérieur : voie bus (déjà dans les voies), bande cyclable, tampon,
    stationnement, séparateur + piste, trottoir ; et limites explicites [(i_loc, limite)]."""
    seq, lims = [], []
    # cyclable (RF-OSM-CYC-001 à -006)
    cyc, kc = cote_tag(tags, "cycleway", cote)
    if cyc in ("opposite_lane", "opposite") and kc == "cycleway" and cote == "right":
        cyc = None                                   # contresens : bande à gauche seulement (RF-OSM-CYC-004)
    if cyc is None and oneway and cote == "left" and tags.get("oneway:bicycle") == "no" and tags.get("cycleway") in ("opposite_lane", "opposite"):
        cyc, kc = tags["cycleway"], "cycleway"
    piste = None
    if cyc in ("lane", "opposite_lane"):
        s = sens_voie
        if cyc == "opposite_lane" or tags.get(f"cycleway:{cote}:oneway") == "-1":
            s = "arriere" if sens_voie == "avant" else "avant"
        if sens_voie == "double":
            s = "arriere" if cote == "left" else "avant"
        w = nombre_osm(tags.get(f"cycleway:{cote}:width") or tags.get("cycleway:both:width") or tags.get("cycleway:width"))
        b = _bande("bande_cyclable", s, w, P.osm(f"tag/cycleway:{cote}:width", "RF-OSM-LAR-001") if w else None,
                   f"tag/{kc}", "RF-OSM-CYC-004" if s != sens_voie else "RF-OSM-CYC-001")
        b["cyclable"] = {"double_sens": s != sens_voie}
        b["prov"]["cyclable"] = P.osm(f"tag/{kc}", "RF-OSM-CYC-004" if s != sens_voie else "RF-OSM-CYC-001")
        seq.append(b)
        sep = tags.get(f"cycleway:{cote}:separation") or tags.get("cycleway:both:separation") or tags.get("cycleway:separation")
        if sep and sep != "no":
            typ = {"bollard": "potelets", "flex_post": "balises_J11", "bump": "plots", "planter": "jardinieres",
                   "kerb": "bordure_separatrice", "vertical_panel": "potelets"}.get(sep)
            if typ:
                lims.append((0, {"raffiner": True, "separateur": {"type": typ, "regle": "RF-OSM-CYC-006"},
                                 "prov": P.osm(f"tag/cycleway:{cote}:separation", "RF-OSM-CYC-006")}))
    elif cyc == "track":
        w = nombre_osm(tags.get(f"cycleway:{cote}:width") or tags.get("cycleway:width"))
        s = sens_voie if sens_voie != "double" else ("arriere" if cote == "left" else "avant")
        piste = _bande("piste_cyclable", s, w, P.osm(f"tag/cycleway:{cote}:width", "RF-OSM-LAR-001") if w else None,
                       f"tag/{kc}", "RF-OSM-CYC-002")
        piste["cyclable"] = {"double_sens": False}
        piste["prov"]["cyclable"] = P.osm(f"tag/{kc}", "RF-OSM-CYC-002")
        piste["prov"]["niveau"] = P.defaut("RF-OSM-NIV-013", conf="faible")
    elif cyc == "shared_lane":
        av.append(f"cycleway:{cote}=shared_lane : vélos dans la voie (figurines ou doubles chevrons, RF-OSM-CYC-005), pas de bande")
    elif cyc == "separate":
        av.append(f"cycleway:{cote}=separate : piste cartographiée à part, à rattacher (RF-OSM-CYC-003, hors lot L0)")
    # stationnement (RF-OSM-STA-001), schéma 2022 puis ancien schéma parking:lane
    pk, kp = cote_tag(tags, "parking", cote)
    ori = tags.get(f"parking:{cote}:orientation") or tags.get("parking:both:orientation")
    if pk is None:
        old, ko = cote_tag(tags, "parking:lane", cote)
        if old in ("parallel", "diagonal", "perpendicular"):
            pos = tags.get(f"parking:lane:{cote}:{old}") or tags.get(f"parking:lane:both:{old}") or "on_street"
            pk = {"on_street": "lane", "half_on_kerb": "half_on_kerb", "on_kerb": "on_kerb", "street_side": "street_side"}.get(pos, "lane")
            ori = old
            kp = ko
            av.append(f"{ko}={old} : ancien schéma traduit en parking:{cote}={pk} + orientation={old} (RF-OSM-STA-001)")
    stat = None
    if pk in ("lane", "street_side", "half_on_kerb", "on_kerb"):
        o = {"parallel": "longitudinal", "diagonal": "epi", "perpendicular": "bataille"}.get(ori or "parallel", "longitudinal")
        pos = {"lane": "chaussee", "street_side": "encoche", "half_on_kerb": "mi_trottoir", "on_kerb": "trottoir"}[pk]
        w = nombre_osm(tags.get(f"parking:{cote}:width") or tags.get("parking:both:width"))
        stat = _bande("stationnement", sens_voie if sens_voie != "double" else ("arriere" if cote == "left" else "avant"),
                      w, P.osm(f"tag/parking:{cote}:width", "RF-OSM-LAR-001") if w else None, f"tag/{kp}", "RF-OSM-STA-001")
        stat["stationnement"] = {"orientation": o, "position": pos}
        if o == "longitudinal":
            stat["stationnement"]["longueur_place_m"] = regles.valeur("RF-OSM-LAR-040", "longueur_place")
        stat["prov"]["stationnement"] = P.osm(f"tag/{kp}", "RF-OSM-STA-001")
        if seq and seq[-1]["type"] == "bande_cyclable" and pos == "chaussee" and o == "longitudinal":
            t = _bande("zone_neutralisee", "aucun", None, None, "", "RF-OSM-LAR-032", sous_type="tampon_emportierage")
            seq.append(t)
        seq.append(stat)
    # piste derrière le stationnement, avec son séparateur (RF-OSM-CYC-002, RF-OSM-LAR-033)
    if piste is not None:
        seq.append(_bande("separateur", "aucun", None, None, "", "RF-OSM-LAR-033"))
        seq.append(piste)
    # trottoir (RF-OSM-TRO-001, -002)
    sw = tags.get(f"sidewalk:{cote}") or tags.get("sidewalk:both")
    swg = tags.get("sidewalk")
    present = None
    if sw is not None:
        present, kt = sw == "yes", f"sidewalk:{cote}"
    elif swg is not None:
        present = swg in ("both", "yes") or swg == cote
        kt = "sidewalk"
        if swg == "separate":
            av.append("sidewalk=separate : trottoirs cartographiés à part, à rattacher (RF-OSM-CYC-003, hors lot L0)")
    if present is None:
        present = info["agglomeration"] and hw in TROTTOIRS_AGGLO and tags.get("junction") not in ("roundabout", "circular", "intersection")
        pt = P.defaut("RF-OSM-TRO-002", note="trottoir implicite" if present else "pas de trottoir implicite")
    else:
        pt = P.osm(f"tag/{kt}", "RF-OSM-TRO-001")
    if present:
        w = nombre_osm(tags.get(f"sidewalk:{cote}:width") or tags.get("sidewalk:both:width") or tags.get("sidewalk:width"))
        t = _bande("trottoir", "double", w, P.osm(f"tag/sidewalk:{cote}:width", "RF-OSM-LAR-001") if w else None, "", "RF-OSM-TRO-001")
        t["prov"]["*"] = pt
        if stat is not None and stat["stationnement"]["position"] in ("trottoir", "mi_trottoir"):
            t["attributs"]["niveau"] = "trottoir"
        seq.append(t)
    elif not info["agglomeration"] and info["categorie"] not in ("autoroute", "voie_express", "bretelle", "piste_cyclable_independante"):
        # rase campagne : bande dérasée (RF-OSM-LAR-014, RF-OSM-TRO-001 « accotement »)
        seq.append(_bande("bande_derasee", sens_voie if sens_voie != "double" else ("arriere" if cote == "left" else "avant"),
                          None, None, "", "RF-OSM-LAR-014"))
    elif info["categorie"] == "autoroute" and cote == "right":
        seq.append(_bande("bande_arret_urgence", "avant", None, None, "", "RF-OSM-LAR-014"))
    return seq, lims


def profil_piste(tags, ctx, info, pid, av):
    """highway=cycleway : piste indépendante, bidirectionnelle sauf oneway (table highway_vers_categorie)."""
    ctx = dict(ctx)
    w = nombre_osm(tags.get("width"))
    if oui(tags.get("oneway")):
        b = [_bande("piste_cyclable", "avant", w, P.osm("tag/width", "RF-OSM-LAR-001") if w else None, "tag/highway", "RF-OSM-LAR-031")]
    else:
        b = []
        for s in ("arriere", "avant"):
            x = _bande("piste_cyclable", s, w / 2 if w else None, P.osm("tag/width", "RF-OSM-LAR-001", note="moitié de la largeur") if w else None,
                       "tag/highway", "RF-OSM-LAR-031")
            x["attributs"]["demi_piste"] = True
            x["attributs"]["niveau"] = "chaussee"
            x["cyclable"] = {"double_sens": True}
            x["prov"]["cyclable"] = P.inference("RF-OSM-CYC-002")
            b.append(x)
    for x in b:
        x["attributs"]["niveau"] = "chaussee"
    profil, w2, ctrl = PF.construire_profil(pid, b, None, ctx, nom="highway=cycleway")
    return profil, info, av + w2, ctrl


def repartir_largeur(tags, bandes, ctx, av):
    """width:carriageway / width / est_width : chaussée bordure à bordure (stationnement sur chaussée compris) →
    largeur des voies = (W − Σ bandes connues) / nombre de voies (RF-OSM-LAR-001), bornée par la plage, sinon
    signalée (conf faible) au lieu d'être forcée (INFERENCE § 2.3)."""
    for cle, conf in (("width:carriageway", "moyenne"), ("width", "faible"), ("est_width", "faible")):
        W = nombre_osm(tags.get(cle))
        if W is not None:
            break
    else:
        return
    ch = [b for b in bandes if PF.cle_niveau(b) == "chaussee"]
    voies = [b for b in ch if b["type"] in ("voie_circulation", "chaussee_partagee") and b.get("largeur") is None]
    if not voies:
        return
    connu = 0.0
    for b in ch:
        if b in voies:
            continue
        w = b["largeur"] if b.get("largeur") is not None else PF.largeur_defaut(b, bandes, ctx)[0]
        connu += w
    w = (W - connu) / len(voies)
    ref = "RF-OSM-LAR-011" if all(b["sens"] == "avant" for b in voies) and len(voies) == 1 else (
        "RF-OSM-LAR-012" if any(sum(1 for x in voies if x["sens"] == s) >= 2 for s in ("avant", "arriere")) else "RF-OSM-LAR-010")
    lo = regles.valeur(ref, "meme_sens_min" if ref == "RF-OSM-LAR-012" else "min")
    hi = regles.valeur(ref, "meme_sens_max" if ref == "RF-OSM-LAR-012" else "max")
    if voies[0]["type"] == "chaussee_partagee":
        lo, hi = 0.0, 99.0
    hors = not (lo - 1e-9 <= w <= hi + 1e-9) and ctx["agglomeration"]
    if hors:
        av.append(f"{cle}={W} : voies de {w:.2f} m hors de la plage [{lo} ; {hi}] de {ref} : valeur gardée, confiance faible")
    for b in voies:
        b["largeur"] = round(w, 4)
        b["prov"]["largeur"] = P.inference(ref, conf="faible" if hors else conf, src_regle="RF-OSM-LAR-001",
                                           note=f"({cle} {W} − {connu:.2f}) / {len(voies)}")


def placement(v: str) -> dict:
    if v == "transition":
        return {"type": "transition"}
    m = re.match(r"^(left_of|right_of|middle_of):(\d+)$", v)
    if m:
        return {"type": {"left_of": "bord_gauche_voie", "right_of": "bord_droit_voie", "middle_of": "milieu_voie"}[m.group(1)],
                "voie": int(m.group(2))}
    return {"type": "centre_chaussee"}


# ================================================================================================ graphe
def longueur(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def abscisse(pts, k):
    return longueur(pts[:k + 1])


def azimut(a, b):
    return (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360.0) % 360.0


def construire(donnees: dict, agglomeration=None, contexte_scene: dict | None = None, nom: str = "osm", source: str = ""):
    """DonneesOSM (osm_lecture) → (modele, rapport)."""
    nd, ways = donnees["noeuds"], donnees["ways"]
    av_glob = []
    routiers = {wid: w for wid, w in sorted(ways.items()) if w["tags"].get("highway") in ROUTIERS
                and w["tags"].get("area") != "yes" and len(w["noeuds"]) >= 2}
    usage = {}
    for wid, w in routiers.items():
        for k, n in enumerate(w["noeuds"]):
            usage[n] = usage.get(n, 0) + (1 if 0 < k < len(w["noeuds"]) - 1 else 1)
    graphe = {n for n, c in usage.items() if c >= 2}
    for w in routiers.values():
        graphe |= {w["noeuds"][0], w["noeuds"][-1]}
    # découpe (RF-OSM-CAR-001)
    routes, profils, cles_profils = [], [], {}
    ctrl_glob = []
    for wid, w in routiers.items():
        tags = dict(w["tags"])
        ids = list(w["noeuds"])
        if tags.get("oneway") == "-1":
            ids = ids[::-1]
        coupe = [k for k, n in enumerate(ids) if n in graphe or k in (0, len(ids) - 1)]
        for a, b in zip(coupe, coupe[1:]):
            seg = ids[a:b + 1]
            routes.append({"way": wid, "noeuds_osm": seg, "tags": tags})
    modele_routes, modele_noeuds = [], {}
    ecartes = []
    gardes = []
    for r in routes:      # un way dont le profil ne peut pas être construit sans inventer est écarté et signalé
        try:
            r["_profil"] = profil_depuis_tags(r["tags"], agglomeration, contexte_scene, "P-tmp")
            gardes.append(r)
        except ErreurInference as e:
            ecartes.append({"way": int(r["way"]), "raison": str(e)})
    routes[:] = gardes
    av_glob += [f"way {x['way']} écarté : {x['raison']}" for x in ecartes]
    for k, r in enumerate(routes, start=1):
        rid = f"R-{k}"
        r["id"] = rid
        profil, info, av, ctrl = r.pop("_profil")
        cle = json.dumps(profil, sort_keys=True, ensure_ascii=False)
        if cle not in cles_profils:
            pid = f"P-{len(profils) + 1}"
            profil["id"] = pid
            cles_profils[cle] = pid
            profils.append(profil)
        r["profil"] = next(p for p in profils if p["id"] == cles_profils[cle])
        r["info"] = info
        av_glob += [f"{rid} (way {r['way']}) : {x}" for x in av]
        ctrl_glob += [dict(c, route=rid) for c in ctrl if c.get("statut") != "conforme"]
        pts = [nd[n]["xy"] for n in r["noeuds_osm"]]
        r["pts"] = pts
        L = longueur(pts)
        r["L"] = L
    # nœuds et carrefours
    fins = {}
    for r in routes:
        fins.setdefault(r["noeuds_osm"][0], []).append((r, "debut"))
        fins.setdefault(r["noeuds_osm"][-1], []).append((r, "fin"))
    anneaux = giratoires(routes)
    carrefours, signaux, marquages, objets, ouvrages = [], [], [], [], []
    for n in sorted(fins):
        bouts = fins[n]
        deg = len(bouts)
        nid = f"N-{n}"
        typ = "carrefour" if deg >= 3 or n in anneaux else ("connexion" if deg == 2 else "extremite")
        modele_noeuds[n] = {"id": nid, "osm_node": int(n), "position": [_r(nd[n]["xy"][0]), _r(nd[n]["xy"][1])], "type": typ,
                            "routes": sorted({r["id"] for r, _ in bouts}, key=lambda x: int(x[2:])),
                            "prov": {"type": P.inference("RF-OSM-CAR-001", note=f"{deg} extrémité(s) de route")}}
    # carrefours : un par nœud de degré ≥ 3 hors giratoire ; un par anneau de giratoire
    for gid, noeuds_anneau in sorted(anneaux_groupes(routes).items()):
        c = carrefour_giratoire(gid, noeuds_anneau, fins, nd, routes)
        carrefours.append(c)
        for n in noeuds_anneau:
            if n in modele_noeuds:
                modele_noeuds[n]["carrefour"] = c["id"]
    for n in sorted(fins):
        if modele_noeuds[n]["type"] != "carrefour" or n in anneaux:
            continue
        c, sigs = carrefour_plan(n, fins[n], nd, routes, len(carrefours) + 1)
        carrefours.append(c)
        signaux += sigs
        modele_noeuds[n]["carrefour"] = c["id"]
    # éléments ponctuels le long des routes : passages, modération, signaux isolés ; ouvrages
    for r in routes:
        for k, n in enumerate(r["noeuds_osm"]):
            t = nd[n]["tags"]
            s = abscisse(r["pts"], k)
            if t.get("highway") == "crossing" and k not in (0, len(r["noeuds_osm"]) - 1):
                passage(r, n, s, t, nd, carrefours, marquages, fins)
            if t.get("traffic_calming") and 0 < k < len(r["noeuds_osm"]) - 1:
                o = moderation(r, n, s, t, nd, len(objets) + 1)
                if o:
                    objets.append(o)
        if r["tags"].get("bridge") and r["tags"]["bridge"] != "no":
            ouvrages.append(ouvrage(r, len(ouvrages) + 1, av_glob))
    # routes du modèle
    for r in routes:
        info, prof = r["info"], r["profil"]
        n0, n1 = r["noeuds_osm"][0], r["noeuds_osm"][-1]
        lr = {"geometrie": [[_r(x), _r(y)] for x, y in r["pts"]], "longueur_m": _r(r["L"])}
        route = {"id": r["id"], "osm": {"ways": [int(r["way"])], "tags": {k: v for k, v in sorted(r["tags"].items()) if not k.startswith("_")}},
                 "noeud_debut": f"N-{n0}", "noeud_fin": f"N-{n1}"}
        if r["tags"].get("name"):
            route["nom"] = r["tags"]["name"]
        if r["tags"].get("ref"):
            route["ref"] = r["tags"]["ref"]
        route.update({"classe_osm": r["tags"].get("highway"), "categorie": info["categorie"], "agglomeration": info["agglomeration"],
                      "vitesse_kmh": info["vitesse_kmh"], "sens_unique": info["sens_unique"]})
        if r["tags"].get("layer") is not None:
            route["layer"] = int(nombre_osm(r["tags"]["layer"]) or 0)
        if info.get("placement"):
            lr["placement"] = info["placement"]
        route["ligne_reference"] = lr
        route["sections"] = [{"s0": 0.0, "s1": _r(r["L"]), "profil": prof["id"]}]
        for cle, extr in (("carrefour_debut", n0), ("carrefour_fin", n1)):
            if modele_noeuds.get(extr, {}).get("carrefour"):
                route[cle] = modele_noeuds[extr]["carrefour"]
        for cle, lst in (("ouvrages", ouvrages), ("objets", objets), ("marquages", marquages)):
            ids = [o["id"] for o in lst if _concerne(o, r["id"])]
            if ids:
                route[cle] = ids
        pv = dict(info["prov"])
        if "layer" in route:
            pv["layer"] = P.osm("tag/layer", "RF-OSM-OUV-001")
        if "placement" in lr:
            pv["ligne_reference.placement"] = P.osm("tag/placement", "RF-OSM-PRF-010")
        route["prov"] = {k: pv[k] for k in ("categorie", "agglomeration", "vitesse_kmh", "sens_unique", "layer", "ligne_reference.placement") if k in pv}
        modele_routes.append(route)
    modele = {"schema": "modele_voie/0.1",
              "meta": {"auteur": "inférence OSM → modèle (recon/generateur/inference/osm_vers_modele.py)", "zone": nom,
                       "sources": [source or donnees.get("source", {}).get("fichier", "(objet)"), "assets/specs/route/regles_route_fr.json"],
                       "compilateur": VERSION, "base_regles": {k: regles.empreinte()[k] for k in ("schema", "date", "sha256")},
                       "osm": {k: v for k, v in donnees.get("source", {}).items() if k in ("format", "sha256", "octets")}},
              "repere": {"crs": "EPSG:2154", "origine_l93": ORIGINE_DEPOT, "z_ref": "NGF-IGN69", "convention_t": "positif_a_gauche"},
              "contexte": {"pays": "FR", "sens_circulation": "droite"},
              "profils": profils, "noeuds": [modele_noeuds[n] for n in sorted(modele_noeuds)], "routes": modele_routes}
    for cle, lst in (("carrefours", carrefours), ("ouvrages", ouvrages), ("signaux", signaux), ("objets", objets), ("marquages", marquages)):
        if lst:
            modele[cle] = lst
    modele = arrondir(modele)
    import valider_modele as VM
    err, av_v, stats = VM.valider(modele, exiger_prov=True)
    rapport = {"zone": nom, "version": VERSION, "routes": len(modele_routes), "profils": len(profils), "carrefours": len(carrefours),
               "ways_ecartes": ecartes,
               "avertissements": av_glob, "controles_hors_plage": ctrl_glob,
               "a_verifier": [c["id"] for c in carrefours if any("à vérifier" in (e.get("note") or "") for e in c["prov"].values())],
               "validation": {"nb_erreurs": len(err), "erreurs": [list(e) for e in err], "avertissements": av_v,
                              "prov_genres": stats.get("prov_genres"), "regles_citees": stats.get("regles_citees")}}
    return modele, rapport


def _concerne(o, rid):
    if o.get("ancrage", {}).get("route") == rid or o.get("rattachement", {}).get("route") == rid:
        return True
    return any(x.get("route") == rid for x in o.get("routes_portees", []))


# ================================================================================================ carrefours
def giratoires(routes):
    out = set()
    for r in routes:
        if r["tags"].get("junction") in ("roundabout", "circular"):
            out |= set(r["noeuds_osm"])
    return out


def anneaux_groupes(routes):
    """Composantes connexes des routes d'anneau → {G-k: nœuds de l'anneau}."""
    ann = [r for r in routes if r["tags"].get("junction") in ("roundabout", "circular")]
    groupes = []
    for r in ann:
        s = set(r["noeuds_osm"])
        fus = [g for g in groupes if g & s]
        for g in fus:
            groupes.remove(g)
            s |= g
        groupes.append(s)
    groupes.sort(key=lambda g: min(g))
    return {f"G{k + 1}": g for k, g in enumerate(groupes)}


def _bandes_branche(r, extremite):
    """(entrantes, sortantes) d'une route vers le carrefour à son extrémité."""
    entr, sort = [], []
    for b in r["profil"]["bandes"]:
        if b["type"] not in PF.VOIES_MOTORISEES:
            continue
        vers = (b["sens"] == "avant") == (extremite == "fin")
        if b["sens"] == "double":
            entr.append(b["id"]); sort.append(b["id"])
        elif vers:
            entr.append(b["id"])
        else:
            sort.append(b["id"])
    return entr, sort


def _noeuds_regime(r, extremite, nd, dmax=None):
    """Nœuds de signalisation de la route qui s'appliquent à cette extrémité : direction explicite, sinon le sens
    qui mène au carrefour le plus proche (RF-OSM-CAR-010, -011)."""
    out = []
    pts, ids = r["pts"], r["noeuds_osm"]
    L = r["L"]
    for k, n in enumerate(ids[1:-1], start=1):
        t = nd[n]["tags"]
        if t.get("highway") not in ("stop", "give_way", "traffic_signals") and not str(t.get("traffic_sign", "")).startswith("FR:A"):
            continue
        s = abscisse(pts, k)
        d = s if extremite == "debut" else L - s
        dirn = t.get("direction") or t.get("traffic_signals:direction")
        if dirn in ("forward", "backward"):
            vers_fin = dirn == "forward"
            if r["tags"].get("_inverse"):
                vers_fin = not vers_fin
            if vers_fin != (extremite == "fin"):
                continue
        elif d > L - d + 1e-9:
            continue
        if dmax is not None and d > dmax:
            continue
        out.append((n, t, d))
    return out


def codes_panneaux(v: str):
    """traffic_sign=FR:AB4 / FR:B0,M9v2 / FR:B14[50] → [(code, valeur)] (RF-OSM-PAN-001)."""
    out = []
    for morceau in re.split(r"[,;]", v or ""):
        m = re.match(r"^\s*(?:FR:)?([A-Za-z]+[0-9]*[a-z0-9.\-]*)(?:\[([^\]]*)\])?\s*$", morceau)
        if m and morceau.strip():
            out.append((m.group(1), m.group(2)))
    return out


def carrefour_plan(n, bouts, nd, routes, k):
    cid = f"C-{n}"
    tn = nd[n]["tags"]
    rangs = {r["id"]: RANG.get(r["tags"].get("highway", "").replace("_link", ""), 6) for r, _ in bouts}
    rmin = min(rangs.values())
    branches, prov, sigs = [], {}, []
    for j, (r, ex) in enumerate(sorted(bouts, key=lambda x: (x[0]["id"], x[1]))):
        bid = f"B{j + 1}"
        pts = r["pts"]
        az = azimut(pts[0], pts[1]) if ex == "debut" else azimut(pts[-1], pts[-2])
        entr, sort = _bandes_branche(r, ex)
        br = {"id": bid, "route": r["id"], "extremite": ex, "azimut_deg": _r(az, 2), "bandes_entrantes": entr,
              "bandes_sortantes": sort}
        regime, pr, ligne, signaux_b = None, None, None, []
        noeuds_b = _noeuds_regime(r, ex, nd)
        # feux : sur le nœud du carrefour, ou sur la branche à moins de 30 m (RF-OSM-CAR-010)
        feux = tn.get("highway") == "traffic_signals" or any(t.get("highway") == "traffic_signals" and d <= 30 for _, t, d in noeuds_b)
        stop_n = [(m, t) for m, t, _ in noeuds_b if t.get("highway") == "stop"]
        cedez_n = [(m, t) for m, t, _ in noeuds_b if t.get("highway") == "give_way" or "FR:AB3a" in t.get("traffic_sign", "")]
        ab4 = [(m, t) for m, t, _ in noeuds_b if "AB4" in t.get("traffic_sign", "")]
        non_prio = rangs[r["id"]] > rmin or len(set(rangs.values())) == 1
        if tn.get("highway") == "stop" and non_prio:      # STOP posé sur le nœud du carrefour (RF-OSM-CAR-011)
            stop_n.append((n, tn))
            if "AB4" in tn.get("traffic_sign", ""):
                ab4.append((n, tn))
        if tn.get("highway") == "give_way" and non_prio:
            cedez_n.append((n, tn))
        if not entr:
            regime, pr = "sortie_seule", P.inference("RF-OSM-CAR-001", note="aucune voie entrante")
        elif feux:
            regime, pr = "feux", P.osm(f"node/{n}" if tn.get("highway") == "traffic_signals" else "tag/highway=traffic_signals", "RF-OSM-CAR-010")
        elif ab4 or (stop_n and any("AB4" in t.get("traffic_sign", "") for _, t in stop_n)):
            regime, pr = "stop", P.osm(f"node/{(ab4 or stop_n)[0][0]}", "RF-OSM-CAR-011", note="traffic_sign=FR:AB4 : STOP confirmé (ARB-19)")
            ligne = {"type": "STOP", "distance_m": regles.valeur("DEF-012", "ligne"), "bandes": entr, "largeur_m": 0.5,
                     "modulation": "continue", "regle": "RF-OSM-CAR-020"}
        elif stop_n:
            regime = "stop_a_verifier"
            pr = P.osm(f"node/{stop_n[0][0]}", "ARB-19", conf="faible",
                       note="highway=stop seul : régime à vérifier, ni AB4 ni ligne ni continue d'approche (ARB-19, RF-OSM-CAR-011) ; à vérifier")
        elif cedez_n:
            regime, pr = "cedez", P.osm(f"node/{cedez_n[0][0]}", "RF-OSM-CAR-011")
            ligne = {"type": "CEDEZ", "distance_m": regles.valeur("DEF-012", "ligne"), "bandes": entr, "largeur_m": 0.5,
                     "modulation": "T'2", "regle": "RF-OSM-CAR-020"}
        elif any(rr["tags"].get("priority_road") == "designated" for rr, _ in bouts):
            if r["tags"].get("priority_road") == "designated":
                regime, pr = "prioritaire", P.osm("tag/priority_road", "RF-OSM-CAR-012")
            else:
                regime, pr = "cedez", P.inference("RF-OSM-CAR-012", conf="faible", note="route à caractère prioritaire sur une autre branche : régime inféré, à vérifier")
                ligne = None
        else:
            regime = "priorite_droite"
            note = "aucun signal ni tag de priorité : priorité à droite"
            conf = None
            if max(rangs.values()) - rmin >= 2 and rmin <= RANG["tertiary"]:
                note += " ; rangs de voies différents : à vérifier (STOP ou cédez non cartographié probable), rien n'est peint"
                conf = "faible"
            pr = P.inference("RF-OSM-CAR-012", conf=conf, note=note)
        br["regime"] = regime
        prov[f"branches[{bid}].regime"] = pr
        if ligne:
            br["ligne_arret"] = ligne
            prov[f"branches[{bid}].ligne_arret"] = P.inference("RF-OSM-CAR-020", note="ligne à la limite de la chaussée prioritaire (DEF-012, ARB-02)")
            dbl = r["profil"]["bandes"] and any(b["sens"] == "arriere" for b in r["profil"]["bandes"] if b["type"] in PF.VOIES_MOTORISEES) \
                and any(b["sens"] == "avant" for b in r["profil"]["bandes"] if b["type"] in PF.VOIES_MOTORISEES)
            if dbl:
                br["ligne_axiale_approche"] = {"modulation": "continue", "largeur_u": 2, "longueur_m": regles.valeur("DEF-013"),
                                               "regle": "RF-MQ-STOP-03"}
                prov[f"branches[{bid}].ligne_axiale_approche"] = P.defaut("DEF-013", note="double sens sans îlot : continue 2u sur 15 m")
        # flèches issues de turn:lanes (RF-OSM-MRQ-050, table turn_vers_fleche)
        fl = []
        turn = _turn_entrantes(r, ex)
        if turn:
            br["turn_lanes_osm"] = turn["brut"]
            for bid_b, val in turn["voies"]:
                types = types_fleche(val)
                if types:
                    fl.append({"bande": bid_b, "types": types, "nombre": regles.valeur("DEF-017", "nombre_par_voie"),
                               "intervalle_m": regles.valeur("DEF-017", "interdistance"),
                               "recul_derniere_m": regles.valeur("DEF-017", "pointe_derniere"), "regle": "RF-OSM-MRQ-050"})
            if fl:
                br["fleches"] = fl
                prov[f"branches[{bid}].fleches"] = P.osm("tag/turn:lanes", "RF-OSM-MRQ-050", note="table turn_vers_fleche ; 3 flèches, 20 m, pointe à 1,50 m (DEF-017)")
        # signaux des nœuds de la branche (RF-OSM-PAN-001) ; jamais d'AB4 sur une branche stop_a_verifier
        for m, t, d in noeuds_b:
            for code, val in codes_panneaux(t.get("traffic_sign", "")):
                if code == "AB4" and regime == "stop_a_verifier":
                    continue
                sid = f"SG-{m}" + (f".{code}" if len(codes_panneaux(t.get("traffic_sign", ""))) > 1 else "")
                sg = {"id": sid, "famille": "panneau", "code": code}
                if val:
                    sg["valeur"] = val
                sg.update({"position": {"route": r["id"], "s": _r(r["L"] - d if ex == "fin" else d), "xyz": [_r(nd[m]["xy"][0]), _r(nd[m]["xy"][1])]},
                           "applicabilite": {"carrefour": cid, "branche": bid, "route": r["id"]},
                           "regles": ["RF-OSM-PAN-001", "RF-OSM-PAN-010"],
                           "prov": {"*": P.osm(f"node/{m}", "RF-OSM-PAN-001"),
                                    "position": P.osm(f"node/{m}", "RF-OSM-PAN-010", note="nœud sur le way : position à recalculer au lot L6")}})
                sigs.append(sg)
                signaux_b.append(sid)
        if signaux_b:
            br["signaux"] = signaux_b
        branches.append(br)
    # une branche en STOP ou cédez confirmés : les autres branches sans signal sont prioritaires (régime de priorité,
    # IISR3 art. 42-2) ; un STOP non confirmé (stop_a_verifier) ne change rien (ARB-19)
    if any(b["regime"] in ("stop", "cedez") for b in branches):
        for b in branches:
            if b["regime"] == "priorite_droite":
                b["regime"] = "prioritaire"
                prov[f"branches[{b['id']}].regime"] = P.inference("RF-OSM-CAR-011", note="une autre branche cède ou s'arrête : branche prioritaire")
    regs = {b["regime"] for b in branches} - {"prioritaire", "sortie_seule"}
    if "feux" in regs:
        creg, ctype = "feux", "plan_feux"
    elif regs == {"priorite_droite"}:
        creg, ctype = "priorite_droite", "plan_simple"
    elif len(regs) == 1 and regs <= {"stop", "cedez"}:
        creg, ctype = regs.pop(), "plan_simple"
    else:
        creg, ctype = "mixte", "plan_simple"
    note_c = "; ".join(sorted({e.get("note", "") for e in prov.values() if "à vérifier" in (e.get("note") or "")}))
    prov["type"] = P.inference("RF-OSM-CAR-001", note=f"nœud partagé par {len(bouts)} extrémités de route")
    prov["regime"] = P.inference("RF-OSM-CAR-012" if creg in ("priorite_droite", "mixte") else "RF-OSM-CAR-011" if creg in ("stop", "cedez") else "RF-OSM-CAR-010",
                                 conf="faible" if note_c else None, note=("à vérifier : " + note_c) if note_c else "régime déduit des branches")
    c = {"id": cid, "type": ctype, "regime": creg, "noeuds": [f"N-{n}"], "centre": [_r(nd[n]["xy"][0]), _r(nd[n]["xy"][1])],
         "branches": branches, "regles": ["RF-OSM-CAR-001", "RF-OSM-CAR-010", "RF-OSM-CAR-011", "RF-OSM-CAR-012", "ARB-19"],
         "prov": {k: prov[k] for k in sorted(prov, key=lambda x: (not x.startswith(("type", "regime")), x))}}
    return c, sigs


def _turn_entrantes(r, ex):
    tags = r["tags"]
    entr, _ = _bandes_branche(r, ex)
    vers_fin = ex == "fin"
    oneway = oui(tags.get("oneway")) or tags.get("junction") in ("roundabout", "circular")
    cle = "turn:lanes" if oneway else ("turn:lanes:forward" if vers_fin else "turn:lanes:backward")
    if cle not in tags or (oneway and not vers_fin):
        return None
    vals = _liste(tags[cle])
    voies = [b for b in r["profil"]["bandes"] if b["id"] in entr]
    if not vers_fin:
        voies = list(reversed(voies))     # de la gauche des usagers qui roulent vers le début
    return {"brut": tags[cle], "voies": [(b["id"], v) for b, v in zip(voies, vals)]}


def types_fleche(val: str):
    parts = sorted(set(x for x in val.split(";") if x and x != "none"))
    if not parts:
        return []
    f = sorted({TURN_FLECHE.get(p) for p in parts if TURN_FLECHE.get(p)})
    if f == ["TD"]:
        return ["TD"]
    if f == ["TAG"]:
        return ["TAG"]
    if f == ["TAD"]:
        return ["TAD"]
    if f == ["TAG", "TD"]:
        return ["TD_TAG"]
    if f == ["TAD", "TD"]:
        return ["TD_TAD"]
    if f in (["RABATTEMENT_G"], ["RABATTEMENT_D"]):
        return f
    return []        # gauche + droite, demi-tour : pas de flèche IISR (RF-MQ-DIR-02), signalé par turn_lanes_osm


def carrefour_giratoire(gid, noeuds_anneau, fins, nd, routes):
    cid = f"C-{gid}"
    branches, prov = [], {}
    j = 0
    for n in sorted(noeuds_anneau):
        for r, ex in sorted(fins.get(n, []), key=lambda x: (x[0]["id"], x[1])):
            if r["tags"].get("junction") in ("roundabout", "circular"):
                continue
            j += 1
            bid = f"B{j}"
            entr, sort = _bandes_branche(r, ex)
            pts = r["pts"]
            az = azimut(pts[0], pts[1]) if ex == "debut" else azimut(pts[-1], pts[-2])
            br = {"id": bid, "route": r["id"], "extremite": ex, "azimut_deg": _r(az, 2), "bandes_entrantes": entr,
                  "bandes_sortantes": sort}
            if entr:
                br["regime"] = "entree_giratoire"
                br["ligne_arret"] = {"type": "CEDEZ", "distance_m": regles.valeur("DEF-012", "ligne"), "bandes": entr,
                                     "largeur_m": 0.5, "modulation": "T'2", "regle": "RF-OSM-CAR-002"}
                prov[f"branches[{bid}].regime"] = P.inference("RF-OSM-CAR-002", note="entrée de giratoire : cédez obligatoire")
                prov[f"branches[{bid}].ligne_arret"] = P.inference("RF-OSM-CAR-002", note="ligne T'2 50 cm obligatoire")
            else:
                br["regime"] = "sortie_seule"
                prov[f"branches[{bid}].regime"] = P.inference("RF-OSM-CAR-002", note="sortie de giratoire")
            branches.append(br)
    if not branches:
        branches.append({"id": "B0", "route": next(r["id"] for r in routes if r["tags"].get("junction")), "extremite": "debut",
                         "regime": "sortie_seule"})
        prov["branches[B0].regime"] = P.inference("RF-OSM-CAR-002", note="anneau sans branche")
    prov["type"] = P.osm("tag/junction", "RF-OSM-CAR-002")
    prov["regime"] = P.inference("RF-OSM-CAR-002")
    pts = [nd[n]["xy"] for n in sorted(noeuds_anneau)]
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return {"id": cid, "type": "giratoire", "regime": "giratoire", "noeuds": [f"N-{n}" for n in sorted(noeuds_anneau)
                                                                              if any(not rr["tags"].get("junction") for rr, _ in fins.get(n, []))] or [f"N-{min(noeuds_anneau)}"],
            "centre": [_r(cx), _r(cy)], "branches": branches, "regles": ["RF-OSM-CAR-002"],
            "prov": {k: prov[k] for k in sorted(prov, key=lambda x: (not x.startswith(("type", "regime")), x))}}


# ================================================================================================ ponctuels
def passage(r, n, s, t, nd, carrefours, marquages, fins):
    """highway=crossing (RF-OSM-CAR-040, -041) : passage du carrefour voisin, ou marquage isolé."""
    if t.get("crossing") == "no":
        return
    marque = t.get("crossing:markings", "yes" if t.get("crossing") in ("zebra", "marked", "traffic_signals", "uncontrolled") else "no") not in ("no",)
    if t.get("crossing") == "unmarked":
        marque = False
    regime = "feux" if t.get("crossing") == "traffic_signals" else "non_gere"
    larg = regles.valeur("DEF-011", "longueur_bandes_ville")
    # rattachement au carrefour de l'extrémité la plus proche si elle est à moins de la demi-largeur des branches + 5 m
    proche = None
    for ex, d in (("debut", s), ("fin", r["L"] - s)):
        n_ex = r["noeuds_osm"][0] if ex == "debut" else r["noeuds_osm"][-1]
        c = next((c for c in carrefours if f"N-{n_ex}" in c.get("noeuds", [])), None)
        if c:
            demi = max(sum(PF.nombre(b["largeur"]) for b in rr["profil"]["bandes"] if b["niveau"]["reference"] == "chaussee") / 2
                       for rr, _ in fins[n_ex])
            if d <= demi + 5.0 and (proche is None or d < proche[1]):
                proche = (c, d)
    pp = {"id": f"PP-{n}", "route": r["id"], "s": _r(s)}
    if marque:
        pp["largeur_m"] = larg
        pp["bandes"] = {"largeur_m": regles.valeur("DEF-011", "bande"), "intervalle_m": regles.valeur("RF-MQ-PP-01", "interdistance")[0]}
    pp["regime"] = regime
    pp["abaisses"] = True
    pp["bev"] = t.get("tactile_paving", "yes") != "no"
    pp["osm"] = {k: v for k, v in sorted(t.items()) if k.startswith(("crossing", "highway", "kerb", "tactile"))}
    pp["prov"] = {"*": P.osm(f"node/{n}", "RF-OSM-CAR-040"),
                  "abaisses": P.defaut("RF-OSM-CAR-041", note="abaissés ≥ 1,20 m en vue 0,02 ; BEV à 0,50 m du nez")}
    if marque:
        pp["prov"]["largeur_m"] = P.defaut("DEF-011", note="longueur des bandes")
    if proche:
        proche[0].setdefault("passages_pieton", []).append(pp)
        return
    if not marque:
        return
    marquages.append({"id": f"M-{n}", "type": "passage_pieton", "ancrage": {"route": r["id"], "s": _r(s)}, "couleur": "blanc",
                      "regles": ["RF-OSM-CAR-040", "RF-MQ-PP-01", "RF-MQ-PP-02", "DEF-011"],
                      "x-opendrive": {"object_type": "crosswalk"},
                      "prov": {"*": P.osm(f"node/{n}", "RF-OSM-CAR-040", note=f"passage isolé {t.get('crossing', '')} ; abaissés et BEV (RF-OSM-CAR-041) au lot L2")}})


def moderation(r, n, s, t, nd, k):
    """traffic_calming (RF-OSM-TC-001)."""
    v = t["traffic_calming"].split(";")[0]
    ch = sum(PF.nombre(b["largeur"]) for b in r["profil"]["bandes"] if b["niveau"]["reference"] == "chaussee")
    if v == "hump":
        typ, dims, reg = "dos_d_ane", {"longueur_m": regles.valeur("RF-MA-RAL-001", "dos_d_ane.longueur"), "largeur_m": ch,
                                       "hauteur_m": regles.valeur("RF-MA-RAL-001", "dos_d_ane.hauteur")}, ["RF-OSM-TC-001", "RF-MA-RAL-001", "RF-MQ-RAL-01"]
    elif v in ("table", "raised_table"):
        h = regles.valeur("DEF-034", "hauteur")
        typ, dims, reg = "plateau", {"hauteur_m": h, "largeur_m": ch}, ["RF-OSM-TC-001", "DEF-034", "RF-MQ-RAL-03"]
    elif v == "cushion":
        typ, dims, reg = "coussin", {"longueur_m": regles.valeur("RF-GV-RAL-001", "longueur")[0],
                                     "largeur_m": regles.valeur("RF-GV-RAL-001", "largeur_PL_bus")[0],
                                     "hauteur_m": regles.valeur("RF-GV-RAL-001", "hauteur_cm")[0] / 100.0}, ["RF-OSM-TC-001", "RF-GV-RAL-001", "RF-MQ-RAL-02"]
    else:
        return None
    x, y = nd[n]["xy"]
    return {"id": f"O-{n}", "famille": "securite", "type": typ, "position": [_r(x), _r(y)],
            "dimensions": {kk: _r(vv) for kk, vv in dims.items()}, "rattachement": {"route": r["id"], "s": _r(s)},
            "regles": reg, "prov": {"*": P.osm(f"node/{n}", "RF-OSM-TC-001"),
                                    "dimensions": P.defaut(reg[1], conf="faible" if v == "cushion" else None)}}


def ouvrage(r, k, av):
    t = r["tags"]
    typ = {"viaduct": "viaduc", "yes": "pont_route", "boardwalk": "passerelle"}.get(t["bridge"], "pont_route")
    o = {"id": f"OA-{k}", "type": typ, "routes_portees": [{"route": r["id"], "s0": 0.0, "s1": _r(r["L"])}]}
    if t.get("layer") is not None:
        o["layer"] = int(nombre_osm(t["layer"]) or 0)
        pl = P.osm("tag/layer", "RF-OSM-OUV-001")
    else:
        o["layer"] = 1
        pl = P.defaut("RF-OSM-OUV-001", conf="faible", note="pont sans layer : 1 supposé, signalé")
        av.append(f"{r['id']} : pont sans layer → layer = 1 supposé (RF-OSM-OUV-001)")
    o["osm"] = {"bridge": t["bridge"]}
    o["x-opendrive"] = {"object_type": "bridge"}
    o["prov"] = {"*": P.osm("tag/bridge", "RF-OSM-OUV-001"), "layer": pl}
    return o


# ================================================================================================ entrée / sortie
def ecrire_json(o, chemin: Path):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes((json.dumps(o, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entree", nargs="+", help="un fichier .osm / .pbf, ou un ou plusieurs GeoJSON (réunis : routes, traversées…)")
    ap.add_argument("--sortie")
    ap.add_argument("--agglomeration", choices=("oui", "non", "auto"), default="auto")
    ap.add_argument("--emprise", nargs=4, type=float)
    ap.add_argument("--nom")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if len(a.entree) == 1:
        d = osm_lecture.lire(a.entree[0])
    else:
        feats, empreintes = [], []
        for f in a.entree:
            if not f.lower().endswith((".geojson", ".json")):
                raise SystemExit("plusieurs entrées : GeoJSON seulement")
            octets = Path(f).read_bytes()
            feats += json.loads(octets.decode("utf-8"))["features"]
            empreintes.append(hashlib.sha256(octets).hexdigest())
        d = osm_lecture.lire_geojson(objet={"type": "FeatureCollection", "features": feats})
        d["source"] = {"fichier": " + ".join(x.replace("\\", "/") for x in a.entree), "format": "geojson",
                       "sha256": hashlib.sha256("".join(empreintes).encode()).hexdigest(), "octets": len(feats)}
    agg = {"oui": True, "non": False, "auto": None}[a.agglomeration]
    nom = a.nom or Path(a.entree[0]).stem
    modele, rapport = construire(d, agg, None, nom, d["source"]["fichier"])
    sortie = Path(a.sortie) if a.sortie else DEPOT / "recon" / "out" / "generateur" / nom
    ecrire_json(modele, sortie / "modele_voie.json")
    ecrire_json(rapport, sortie / "inference.json")
    for w in rapport["avertissements"]:
        print(f"AVERTISSEMENT\t{w}")
    print(f"{nom} : {rapport['routes']} route(s), {rapport['profils']} profil(s), {rapport['carrefours']} carrefour(s), "
          f"{rapport['validation']['nb_erreurs']} erreur(s) de validation → {sortie}")
    return 1 if rapport["validation"]["nb_erreurs"] else 0


if __name__ == "__main__":
    sys.exit(main())
