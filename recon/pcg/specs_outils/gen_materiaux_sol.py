# -*- coding: utf-8 -*-
"""Génère assets/specs/materiaux_sol.json : catalogue des materiau_id V2 (fabrication Houdini, rendu Karma, UE)."""
import json
import os
import sys

import numpy as np
from PIL import Image

SORTIE = sys.argv[1]
DEP = "D:/ClaudeCode_RoadCreation"
MAN = {e["nom"]: e for e in json.load(open(f"{DEP}/assets/manifeste_cc0.json", encoding="utf-8"))["materiaux"]}
LIB = f"{DEP}/assets/lib/materiaux"


def mesure(nom):
    """Albédo moyen linéaire (meta.json) et rugosité moyenne de la texture téléchargée."""
    m = os.path.join(LIB, nom, "meta.json")
    if not os.path.exists(m):
        return None
    mt = json.load(open(m, encoding="utf-8"))
    r = os.path.join(LIB, nom, "textures", f"{nom}_rugosite.jpg")
    rg = float(np.asarray(Image.open(r).convert("L"), float).mean() / 255) if os.path.exists(r) else None
    return {"albedo_moyen_lineaire": mt.get("albedo_moyen_lineaire"), "rugosite_moyenne": None if rg is None else round(rg, 3),
            "resolution": mt.get("resolution"), "usd": f"assets/lib/materiaux/{nom}/{nom}.usda"}


CARLA = "/Game/Carla/Static/GenericMaterials/"
CS = "projet City Sample (UE 5.7, contenu réservé à Unreal) : "


def mat(mid, description, source_nom, *, cible=None, cible_src=None, facteur=None, rugosite=None, carla=None, citysample=None,
        appareillage=None, statut="ok", candidats=None, notes=None, couche=None, src_conf="moyenne"):
    e = {"description": description}
    if source_nom:
        m = MAN[source_nom]
        e["source_cc0"] = {"nom": source_nom, "dossier": f"assets/lib/materiaux/{source_nom}/", "origine": f"{m['source']} {m['id']}",
                           "licence": "CC0-1.0", "statut": statut}
        e["tile_m"] = m["tile_m"]
        c = (m.get("cible") or {}).get("albedo_lineaire")
        if cible is None and c is not None:
            cible, cible_src = c, f"manifeste_cc0.json {source_nom}.cible ({(m.get('cible') or {}).get('mesure', '')[:140]})"
        mes = mesure(source_nom)
        if mes:
            e["texture_mesuree"] = mes
    else:
        e["source_cc0"] = {"nom": None, "statut": statut}
        e["tile_m"] = None
    if candidats:
        e["source_cc0"]["candidats"] = candidats
    e["albedo_cible_lineaire"] = cible
    e["albedo_cible_source"] = cible_src
    if facteur:
        e["facteur_albedo"] = facteur
    e["rugosite"] = rugosite
    if appareillage:
        e["appareillage"] = appareillage
    if couche:
        e["couche"] = couche
    e["ue"] = {"ue_cc0": f"/Game/PJ/Materials/MI_{mid}", "ue_carla": carla, "ue_citysample": citysample}
    e["confiance"] = src_conf
    if notes:
        e["notes"] = notes
    return e


def fac(cible, source_nom):
    """Facteur par canal pour ramener la cible de la source vers la cible voulue (multiplicateur d'albédo)."""
    c0 = MAN[source_nom]["cible"]["albedo_lineaire"]
    return [round(a / b, 3) for a, b in zip(cible, c0)]


M = {}
M["enrobe_bbsg_ancien"] = mat("enrobe_bbsg_ancien", "Enrobé BBSG 0/10 ancien, gris clair oxydé, fissures pontées (chaussées inchangées depuis 2022, parkings, accès riverains)",
                              "enrobe_bbsg_ancien", rugosite={"valeur": 0.85, "plage": [0.75, 0.95]},
                              carla=[CARLA + "Asphalt/MI_Asphalt08", CARLA + "WetPavement/MI_WetRoad_1 (variante mouillée)"],
                              citysample=[CS + "/Game/Road/Material/MI/M_Asphalt_Master_Inst", "/Game/Megascans/Surfaces/Asphalt_Dried01_2x2 (textures)"],
                              src_conf="haute")
M["enrobe_bbsg_neuf_2025"] = mat("enrobe_bbsg_neuf_2025", "Enrobé neuf 2025 (réfection C1 : centre du carrefour, Vercors), sombre et homogène",
                                 "enrobe_bbsg_neuf", rugosite={"valeur": 0.80, "plage": [0.7, 0.9]},
                                 carla=[CARLA + "Asphalt/MI_Asphalt08 (assombri)"],
                                 citysample=[CS + "/Game/Megascans/Surfaces/Asphalt_Fresh_2x2_M_00 (textures)", "/Game/Road/Material/MI/MI_FreewayAsphalt_RoadDark"],
                                 notes="id manifeste : enrobe_bbsg_neuf", src_conf="moyenne")
M["enrobe_reprise_tranchee"] = mat("enrobe_reprise_tranchee", "Reprises d'enrobé (tranchées, rapiéçages), plus sombres et plus lisses, joints nets",
                                   "enrobe_reprise_tranchee", rugosite={"valeur": 0.75, "plage": [0.65, 0.85]},
                                   carla=["/Game/Carla/Static/Decals/Road/RoadPatch (décalques, CC-BY)"],
                                   citysample=[CS + "/Game/Megascans/Surfaces/Cracked_Asphalt_2x2_M_00 (textures)", "Megascans/Atlases Tar_Patch_00, Asphalt_Patch_01"])
M["enrobe_piste_cyclable"] = mat("enrobe_piste_cyclable", "Enrobé de la piste bidirectionnelle Chronovélo, plus récent et plus sombre",
                                 "enrobe_piste_cyclable", rugosite={"valeur": 0.8, "plage": [0.7, 0.9]}, carla=[CARLA + "Asphalt/MI_Asphalt08"],
                                 citysample=[CS + "/Game/Road/Material/MI/M_Asphalt_Master_Inst"])
M["enrobe_trottoir"] = mat("enrobe_trottoir", "Enrobé de trottoir BB 0/6 (3-5 cm), gris plus sombre et plus rugueux que la chaussée (photo utilisateur 1)",
                           "enrobe_trottoir", rugosite={"valeur": 0.9, "plage": [0.8, 0.95]},
                           carla=[CARLA + "Sidewalk/MI_Sidewalk_02 (à vérifier visuellement)", CARLA + "Asphalt/MI_Asphalt08"],
                           citysample=[CS + "/Game/Megascans/Surfaces/Dirty_Sidewalk_2x2_M_00 (textures)"],
                           appareillage={"type": "continu", "devers_pct": [1, 2], "note": "pente vers la chaussée"})
M["enrobe_clair_granulats"] = mat("enrobe_clair_granulats", "Enrobé clair grenaillé / surface à granulats apparents (surface centrale, refuges)",
                                  "enrobe_clair_granulats", rugosite={"valeur": 0.85, "plage": [0.75, 0.95]},
                                  carla=[CARLA + "Concrete/MI_Concrete_03 (à vérifier)"],
                                  citysample=[CS + "/Game/Megascans/Surfaces/Gravel_Pebbledash_ugzmbcrn_2K_surface_ms (textures)"])
M["enrobe_colore_ocre"] = mat("enrobe_colore_ocre", "Enrobé ou résine ocre-orangé délavé (îlots à niveau de la Revirée)", "enrobe_colore_ocre",
                              rugosite={"valeur": 0.85, "plage": [0.75, 0.95]}, carla=None, citysample=None)
M["resine_verte"] = mat("resine_verte", "Résine verte délavée des traversées cyclables de la Revirée", "resine_verte",
                        rugosite={"valeur": 0.6, "plage": [0.5, 0.75]}, carla=None, citysample=None,
                        notes="résine gravillonnée : rugosité plus faible que l'enrobé, usure par masque (peinture.json)")
M["resine_cyan"] = mat("resine_cyan", "Résine / peinture cyan pâle (rectangles de traversée de piste NO)", "resine_cyan",
                       rugosite={"valeur": 0.6, "plage": [0.5, 0.75]})
M["beton_balaye"] = mat("beton_balaye", "Béton coulé en place, finition balayée (stries transversales), joints sciés", "beton_bordure",
                        statut="proxy (texture beton_bordure, stries de balai à ajouter en normale procédurale)",
                        candidats=["Poly Haven anti_slip_concrete (2,50 m, CC0) : à ajouter au manifeste si une surface balayée est observée"],
                        rugosite={"valeur": 0.85, "plage": [0.75, 0.95]}, carla=[CARLA + "Concrete/MI_Concrete_01"],
                        citysample=[CS + "/Game/Megascans/Surfaces/Rough_Concrete_Floor_2x2 (textures)"],
                        appareillage={"type": "coulé", "joints_scies_m": [3.0, 4.0], "largeur_joint_mm": 5, "stries": "pas 3-6 mm perpendiculaires au cheminement"},
                        src_conf="faible", notes="aucune surface balayée confirmée sur le site (catalogue_besoins) : id réservé")
M["beton_desactive"] = mat("beton_desactive", "Béton désactivé à granulats apparents 4/10 ou 6/10 (12 cm), joints sciés tous les 3-4 m", "beton_galets",
                           statut="proxy (texture beton_galets : granulats apparents plus gros que 6/10)",
                           candidats=["ambientCG Gravel043 (1,60 m) ou Poly Haven gravel_embedded_concrete (2,00 m) : granulats plus fins, à évaluer"],
                           rugosite={"valeur": 0.9, "plage": [0.8, 0.95]}, carla=[CARLA + "Concrete/MI_Concrete_05 (à vérifier)"],
                           citysample=[CS + "/Game/Megascans/Surfaces/Gravel_Pebbledash_ugzmbcrn_2K_surface_ms (textures)"],
                           appareillage={"type": "coulé", "joints_scies_m": [3.0, 4.0], "largeur_joint_mm": 5,
                                         "fabrication": "joints sciés en géométrie (rainure 5 mm x 10 mm) dans pj_sol"},
                           src_conf="faible")
M["dalles_beton"] = mat("dalles_beton", "Dalles béton NF EN 1339 30x30 / 40x40 / 50x50 (4-8 cm) sur lit de pose, joints 3-5 mm", "beton_bordure",
                        statut="proxy (texture beton_bordure sur chaque dalle, joints en géométrie)",
                        candidats=["Poly Haven concrete_pavement_03 (2,10 m) ; checkered_pavement_tiles (2,00 m)"],
                        rugosite={"valeur": 0.8, "plage": [0.7, 0.9]},
                        carla=[CARLA + "Sidewalk/MI_Sidewalk_Residential", "/Game/Carla/Static/GenericMaterials/LargeMap_materials/largeM_sidewalk/tile01/MI_largeM_tile02"],
                        citysample=[CS + "/Game/Road/Material/MI/MI_Sidewalk", "/Game/Megascans/Surfaces/Tile_Sidewalk_ug4kbdus (textures)"],
                        appareillage={"module_cm": [30, 40, 50], "defaut_cm": 40, "joint_mm": [3, 5],
                                      "fabrication": "UV alignées sur le module ; dalles en géométrie (léger chanfrein 2 mm, décalage de hauteur ±1 mm) ou masque de joints"},
                        src_conf="faible")
M["paves_beton"] = mat("paves_beton", "Pavés béton NF EN 1338 20x10 (6-8 cm), joints sablés 5-10 mm (photos utilisateur 3 et 4 : pavés clairs)", "beton_bordure",
                       statut="proxy (texture beton_bordure par pavé, appareillage en géométrie ou masque)",
                       candidats=["ambientCG PavingStones (série) : choisir un 20x10 en chevrons ou en panneresse, à ajouter au manifeste"],
                       rugosite={"valeur": 0.8, "plage": [0.7, 0.9]}, carla=[CARLA + "Brick/MI_Brick03 (à vérifier)", CARLA + "Sidewalk/MI_Sidewalk_11"],
                       citysample=[CS + "/Game/Megascans/Surfaces/Patterned_Stone_Tiles_2x2_M_00 (textures)"],
                       appareillage={"module_cm": [20, 10], "joint_mm": [5, 10], "motifs": ["panneresse", "chevrons 45°", "chevrons 90°"]},
                       src_conf="faible", notes="trottoirs en pavés : 3 polygones (10,4 m²) sur le site")
M["paves_granit"] = mat("paves_granit", "Pavés de granit gris clair 10x10 / 14x20 (anneaux d'îlots, rangée affleurante de l'allée sud), joints 10-15 mm",
                        "paves_granit", rugosite={"valeur": 0.7, "plage": [0.6, 0.8]}, carla=[CARLA + "Brick/MI_Brick05 (à vérifier)"],
                        citysample=[CS + "/Game/Road/Textures/Plaza/Tile_Pavestone_ugfnfifo (textures)"],
                        appareillage={"module_cm": [[10, 10], [14, 20], [14, 14]], "joint_mm": [10, 15]}, src_conf="haute")
M["beton_bordure_gris"] = mat("beton_bordure_gris", "Béton gris des bordures et caniveaux (vieilli : épaufrures, mousses, salissures au fil d'eau)", "beton_bordure",
                              rugosite={"valeur": 0.75, "plage": [0.6, 0.85]},
                              carla=[CARLA + "Gutters_Curbs/Curb/MI_dirtyCurb", CARLA + "LargeMap_materials/largeM_curb/MI_largeM_curb01",
                                     CARLA + "Gutters_Curbs/Gutter/MI_dirtyGutter (caniveaux)"],
                              citysample=[CS + "/Game/Road/Kit_Small_Curb_A/Material/M_Concrete_Curb"],
                              notes="la v1 utilisait un albédo de 0,66 : 1,8 x trop clair ; teinte par élément ±4 % (bordures_elements.json)", src_conf="haute")
M["beton_bordure_clair"] = mat("beton_bordure_clair", "Béton de bordure très clair, presque blanc (îlots du Vercors, éléments neufs ; photo utilisateur 2)", "beton_bordure",
                               cible=[0.45, 0.455, 0.43],
                               cible_src="a priori : constat p2025_01_vercors-26 « bordures claires, presque blanches » ; photo utilisateur 2 (rapport tête de bordure / enrobé 1,94 x 0,24 = 0,47)",
                               facteur=fac([0.45, 0.455, 0.43], "beton_bordure"), rugosite={"valeur": 0.75, "plage": [0.6, 0.85]},
                               carla=[CARLA + "LargeMap_materials/largeM_curb/MI_largeM_curb01_2 (à vérifier)"],
                               citysample=[CS + "/Game/Road/Kit_Small_Curb_A/Material/M_Concrete_Curb (éclairci)"], src_conf="faible",
                               notes="même texture que beton_bordure_gris, albédo multiplié par facteur_albedo (UsdUVTexture inputs:scale côté Karma, paramètre de MI côté UE)")
M["granit_bordure"] = mat("granit_bordure", "Bordure en granit gris bouchardé ou flammé (option ; aucune relevée sur le site)", "paves_granit",
                          statut="proxy (texture de pavés : à remplacer par un granit bouchardé CC0 si une bordure granit est observée)",
                          candidats=["ambientCG Granite00x (plans de travail polis : non adaptés) ; Poly Haven granite_tile_03 (dalles)"],
                          rugosite={"valeur": 0.7, "plage": [0.6, 0.8]}, carla=None, citysample=None, src_conf="faible")
M["calcaire_bordure"] = mat("calcaire_bordure", "Bordure en pierre calcaire claire sciée (photo utilisateur 4), beige pâle à fins lits", "calcaire_bordure",
                            rugosite={"valeur": 0.7, "plage": [0.6, 0.8]}, carla=None, citysample=None, src_conf="faible",
                            notes="lits orientés le long de l'élément (U = s) ; aucune bordure calcaire relevée sur le site (option d'aspect)")
M["caniveau_beton"] = mat("caniveau_beton", "Caniveaux CS1/CS2/CS3 en béton, plus sales que la bordure (dépôts au fil d'eau)", "beton_bordure",
                          rugosite={"valeur": 0.75, "plage": [0.6, 0.85]}, carla=[CARLA + "Gutters_Curbs/Gutter/MI_dirtyGutter", CARLA + "LargeMap_materials/largeM_gutter/MI_largeM_gutter01"],
                          citysample=None, notes="salissure 0,5-0,8 (bordures_elements.json, aspect)", src_conf="moyenne")
M["bev_podotactile"] = mat("bev_podotactile", "Dalles podotactiles 40x40 à plots (BEV), gris clair ou blanches", "bev_podotactile",
                           rugosite={"valeur": 0.7, "plage": [0.6, 0.8]}, carla=None, citysample=None,
                           appareillage={"module_cm": [40, 40], "joint_mm": 3, "plots": "Ø 25 mm, h 5 mm, entraxe 75 mm en quinconce (mobilier.json)"},
                           src_conf="haute")
M["brf_bois_concasse"] = mat("brf_bois_concasse", "BRF / bois concassé brun en couche de 7-10 cm (îlots, massifs, pieds d'arbres) ; photo utilisateur 2", "brf_bois_concasse",
                             cible=[0.138, 0.12, 0.108],
                             cible_src="photo utilisateur 2 (Heinrich & Bock, hors site, lumière diffuse), revue UE du 2026-10-10 : rapport BRF / enrobé "
                                       "voisin 0,70-0,75 par moyennes linéaires et 0,30-0,35 par médianes (copeaux clairs très contrastés) ; cible = lit vu "
                                       "(copeaux bruns + ~25 % de brf_bois_gris) = 0,47 x enrobe_bbsg_ancien, chromie de la photo (R/G 1,15, B/G 0,90). "
                                       "L'ancienne cible du manifeste (0,062/0,047/0,038, médianes : 0,206) rendait le lit 3 à 4 fois trop sombre une fois "
                                       "enfoncé et ombré ; la texture de assets/lib (corrigée vers l'ancienne cible) reste à recaler pour Karma",
                             rugosite={"valeur": 0.9, "plage": [0.8, 1.0]}, carla=[CARLA + "Ground/MI_Dirt (secours, sans copeaux)"],
                             citysample=[CS + "/Game/Prop/Kit_Dirt_A (maillages de terre, secours)"],
                             couche={"epaisseur_m": [0.07, 0.10], "elements_m": [0.02, 0.05], "retrait_sous_bordure_m": [0.03, 0.05], "bombement_m": [0.01, 0.03],
                                     "debordement": "copeaux épars sur la tête de bordure et la chaussée (PG_Ilots), 0-3 par mètre de bordure",
                                     "vieillissement": "mélange avec brf_bois_gris par masque de bruit (îlots plantés avant 2025)"},
                             src_conf="faible")
M["brf_bois_gris"] = mat("brf_bois_gris", "BRF vieilli grisé (gris argent après environ 1 an)", "brf_bois_gris",
                         cible_src="pas de cible : couleur propre de la texture (WoodChips001)", rugosite={"valeur": 0.9, "plage": [0.8, 1.0]},
                         carla=None, citysample=None, couche={"epaisseur_m": [0.05, 0.08], "retrait_sous_bordure_m": [0.03, 0.05]}, src_conf="faible")
M["gravier_concasse_6_10"] = mat("gravier_concasse_6_10", "Gravier concassé anguleux 6/10 à 10/14 gris (îlots gravillonnés du Vercors, pieds de mâts) ; photos utilisateur 3 et 4",
                                 "gravier_concasse_6_10", rugosite={"valeur": 0.85, "plage": [0.75, 0.95]},
                                 carla=["/Game/Carla/Static/GenericMaterials/Ground/Textures/HD/T_Pebbles_01_dh (textures seules, sans MI)"],
                                 citysample=[CS + "/Game/Megascans/Surfaces/Gravel_Pavement_2x2 (textures)"],
                                 couche={"epaisseur_m": [0.05, 0.10], "elements_m": [0.006, 0.014], "sous_couche": "géotextile 100-300 g/m²",
                                         "retrait_sous_bordure_m": [0.03, 0.05], "bombement_m": [0.0, 0.02],
                                         "debordement": "gravillons épars sur la chaussée au pied de la bordure (PG_Ilots), 2-10 par mètre"},
                                 src_conf="moyenne", notes="remplace gravillons_ilot (gravier roulé) pour les îlots concassés ; cible identique (ortho du Vercors)")
M["gravillons_ilot"] = mat("gravillons_ilot", "Gravillons roulés clairs 6-20 mm (variante roulée, rivière)", "gravillons_ilot",
                           rugosite={"valeur": 0.8, "plage": [0.7, 0.9]}, carla=["/Game/Carla/Static/GenericMaterials/Ground/Textures/HD/T_Pebbles_02_dh (textures seules)"],
                           citysample=None, couche={"epaisseur_m": [0.05, 0.10], "retrait_sous_bordure_m": [0.03, 0.05]}, src_conf="moyenne")
M["galets_20_40"] = mat("galets_20_40", "Galets roulés 20/40 (25/40) en paillage minéral, couche d'environ 6 cm", "paillage_mineral",
                        rugosite={"valeur": 0.75, "plage": [0.65, 0.85]}, carla=["/Game/Carla/Static/GenericMaterials/Ground/Textures/HD/T_Pebbles_01_dh (textures seules)"],
                        citysample=None, couche={"epaisseur_m": [0.05, 0.07], "elements_m": [0.02, 0.04], "retrait_sous_bordure_m": [0.03, 0.05]},
                        notes="même source que paillage_mineral (clean_pebbles, galets 2-4 cm à 2,00 m)", src_conf="moyenne")
M["paillage_mineral"] = mat("paillage_mineral", "Paillage minéral (galets / gravier) au pied des jeunes arbres", "paillage_mineral",
                            rugosite={"valeur": 0.75, "plage": [0.65, 0.85]}, carla=None, citysample=None, src_conf="moyenne")
M["beton_galets"] = mat("beton_galets", "Galets sertis dans le béton (îlots du raccordement SE de Verdun)", "beton_galets",
                        rugosite={"valeur": 0.85, "plage": [0.75, 0.95]}, carla=None, citysample=None, src_conf="moyenne")
M["stabilise_beige"] = mat("stabilise_beige", "Sable stabilisé / grave fine 0/6 beige (cheminements, 8-10 cm)", "stabilise_beige",
                           rugosite={"valeur": 0.9, "plage": [0.85, 1.0]}, carla=[CARLA + "Ground/MI_Dirt"],
                           citysample=[CS + "/Game/Megascans/Surfaces/sand_sand_pjuuP0/M_sand"], src_conf="moyenne")
M["gazon_tondu"] = mat("gazon_tondu", "Gazon tondu 4-8 cm (sol sous les cartes d'herbe PCG)", "gazon_tondu",
                       rugosite={"valeur": 0.9, "plage": [0.8, 1.0]}, carla=[CARLA + "Ground/MI_Grass_Cutted_2", CARLA + "Ground/MI_Grass_Cutted_Yard"],
                       citysample=None, couche={"hauteur_herbe_m": [0.04, 0.08], "pcg": "PG_Herbe (densité et hauteur par attribut)"},
                       src_conf="haute", notes="City Sample n'a ni gazon ni haies")
M["herbe_haute"] = mat("herbe_haute", "Herbe haute non tondue 20-60 cm (accotements NE, bandes piste/chaussée)", "herbe_haute",
                       rugosite={"valeur": 0.95, "plage": [0.85, 1.0]}, carla=[CARLA + "Ground/MI_Grass_Park"], citysample=None,
                       couche={"hauteur_herbe_m": [0.2, 0.6], "pcg": "PG_Herbe, débordement sur la bordure (constat p2025_05_360-32)"}, src_conf="moyenne")
M["gazon_sec"] = mat("gazon_sec", "Gazon grillé d'été avec feuilles mortes (variante saisonnière)", "gazon_sec",
                     rugosite={"valeur": 0.95, "plage": [0.85, 1.0]}, carla=[CARLA + "Ground/MI_LargeLandscape_Grass_2 (à vérifier)"], citysample=None)
M["noue_plantee"] = mat("noue_plantee", "Noue / bande plantée (terre, prairie, jeunes arbres)", "noue_plantee",
                        rugosite={"valeur": 0.95, "plage": [0.85, 1.0]}, carla=[CARLA + "Ground/MI_Grass_Park_2"], citysample=None)
M["terre_nue"] = mat("terre_nue", "Terre nue remaniée (bandes en attente de plantation, massifs)", "terre_nue",
                     rugosite={"valeur": 0.9, "plage": [0.8, 1.0]}, carla=[CARLA + "Ground/MI_Dirt"],
                     citysample=[CS + "/Game/Prop/Kit_Dirt_A (maillages Dirt_200x200_A-D)"], src_conf="moyenne")
M["feuilles_mortes"] = mat("feuilles_mortes", "Couche de feuilles mortes d'octobre (mélange par hauteur sur gazon, BRF, pieds de bordure)", "overlay_feuilles_mortes",
                           cible_src="couleur propre de la texture (pas de cible)", rugosite={"valeur": 0.8, "plage": [0.7, 0.9]},
                           carla=["/Game/Carla/Static/Decals/Road/RoadDirt (décalques, CC-BY)"], citysample=None,
                           notes="couche : mélange HeightLerp (UE) / masque (Karma), pas une surface autonome")

doc = {
    "schema": "pj_specs/materiaux_sol/1.0",
    "version": 1,
    "date": "2026-10-10",
    "role": "Catalogue des materiau_id du sol V2 (surfaces, remplissages d'îlots, bordures, caniveaux, BEV) : description, texture CC0 locale, taille de tuile, albédo cible, rugosité, appareillage ou couche, et chemins Unreal (matériau maison, candidats CARLA et City Sample). pj_sol / pj_ilot écrivent materiau_id sur les primitives USD ; Karma lit les .usda CC0 ; UE remappe vers /Game/PJ/Materials/MI_<id>.",
    "conventions": {
        "albedo": "albédo diffus linéaire (RGB, 0-1) ; la cible vient de manifeste_cc0.json (mesure ortho 2022 étalonnée ou rapport photo) quand elle existe ; texture_mesuree = moyenne linéaire de la texture corrigée (meta.json). La cible est la conversion linéaire de la moyenne Lab visée : la moyenne linéaire de la texture, tirée par les grains clairs, est un peu plus haute (ex. paves_granit 0,45 contre 0,36) ; c'est normal",
        "facteur_albedo": "multiplicateur par canal appliqué à la texture source quand un materiau_id réutilise la texture d'un autre (ex. beton_bordure_clair)",
        "rugosite": "rugosité PBR (0 lisse - 1 mat) visée en moyenne ; la carte de la texture module autour de cette valeur",
        "tile_m": "taille réelle d'une répétition de texture ; UV st1 en mètres, UsdTransform2d scale = 1/tile_m",
        "normales": "OpenGL (+Y) ; Unreal : Flip Green Channel à l'import",
        "ue_cc0": "matériau maison à créer dans D:/ClaudeADAS (MI_<id> sur M_PJ_Sol, textures CC0 importées) ; chemin de référence du remappage USD",
        "ue_carla": "candidats CARLA (CC-BY 4.0, attribution ; chemins /Game/Carla conservés) : secours ou décalques, à vérifier visuellement",
        "ue_citysample": "candidats City Sample : contenu réservé à Unreal (jamais dans Houdini/Karma) ; chemins du projet City Sample, à confirmer après migration",
        "statut_source": "ok = texture dédiée téléchargée ; proxy = texture d'un autre matériau en attendant une source dédiée ; candidats = sources CC0 à évaluer (non téléchargées)",
        "licences": "CC0 (assets/lib/materiaux) seul utilisable dans Houdini/Karma ; City Sample et PVE réservés à UE",
    },
    "materiaux": M,
    "remplissages_ilots": {
        "ids": ["brf_bois_concasse", "brf_bois_gris", "gravier_concasse_6_10", "gravillons_ilot", "galets_20_40", "gazon_tondu", "herbe_haute", "terre_nue", "paves_beton", "paves_granit", "enrobe_bbsg_ancien"],
        "surface": "3 à 5 cm sous le dessus de la ceinture de bordures (retrait_sous_bordure_m), légèrement bombée (bombement_m), raccord étanche sur l'arête arrière des bordures",
        "geometrie": "pj_ilot : maillage du remplissage + zone zones/ilots.json pour la dispersion PCG (copeaux, gravillons, plantations)",
        "src_par_defaut": "a_priori:materiaux_sol.remplissages_ilots ; Vercors = gravier_concasse_6_10 (constat coeur-31, décision utilisateur n° 5)",
        "source": "pratique (ADEME, fiches fabricants ; non normatif) ; inventaire normes V2",
        "confiance": "moyenne (épaisseurs), faible (affectation par îlot sans photo 2026)",
    },
    "correspondances_v1": {
        "enrobe": "enrobe_bbsg_ancien (chaussée inchangée), enrobe_bbsg_neuf_2025 (modifie_2025), enrobe_trottoir (trottoir)",
        "beton": "beton_balaye / beton_desactive / dalles_beton selon l'observation ; défaut dalles_beton pour trottoir/beton (a priori)",
        "paves": "paves_beton (trottoir) ou paves_granit (anneaux d'îlots)",
        "herbe": "gazon_tondu (défaut) ou herbe_haute (accotements NE)",
        "terre": "terre_nue", "massif_plante": "terre_nue + brf_bois_concasse (pieds) + palette PCG",
        "stabilise": "stabilise_beige", "ilot (beton en v1)": "gravier_concasse_6_10 pour les îlots du Vercors (constat coeur-31), sinon à décider (décision n° 5)",
    },
    "historique": [{"version": 1, "date": "2026-10-10", "contenu": "création V2 : 36 materiau_id, textures CC0 mesurées, 4 nouveaux matériaux CC0 (BRF brun et gris, gravier concassé, calcaire), candidats CARLA et City Sample"},
                   {"version": 1, "date": "2026-10-10", "contenu": "révision (revue UE) : albédo cible de brf_bois_concasse relevé de 0,049 à 0,123 en luminance (lit vu, photo 2)"}],
}
doc["historique"][0]["contenu"] = doc["historique"][0]["contenu"].replace("36", str(len(M)))
json.dump(doc, open(SORTIE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("écrit", SORTIE, len(M), "materiau_id")
for k, v in M.items():
    s = v["source_cc0"]
    print(f"{k:24s} {str(s.get('nom')):24s} {s['statut'][:10]:10s} tile {v['tile_m']}  cible {v['albedo_cible_lineaire']}  tex {(v.get('texture_mesuree') or {}).get('albedo_moyen_lineaire')} rug {(v.get('texture_mesuree') or {}).get('rugosite_moyenne')}")
