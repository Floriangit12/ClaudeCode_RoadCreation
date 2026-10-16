"""Exporte les règles « machine » de la bibliothèque d'assets route_fr (forme JSON commune à DocRoute).

    python recon/pcg/assets_route/exporter_regles_assets.py [--sortie D:/DocRoute/14_Assets_Route_Statics/regles_assets_route.json]

Chaque règle : {id, sujet, condition, valeurs, unite, tolerance, source: {doc, page, article|figure}, confiance}.
Les profils de bordures et de caniveaux sont repris de specs_assets_route.PROFILS (une règle par profil) ; les autres
règles sont écrites ci-dessous, chacune avec sa page (relue sur le document le 16/10/2026).
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import specs_assets_route as SP  # noqa: E402

DOCS = {
    "alkern2026": "Alkern, catalogue Voirie 2026",
    "celtys": "Celtys, catalogue Bordures TP",
    "fabemi_I2": "Fabemi, fiche Bordure I2 0,5 m (2012)",
    "sepa_T": "Sepa, fiches bordures T1-T3 (2017)",
    "arrete2007": "Arrêté du 15 janvier 2007 (accessibilité de la voirie), copie préfecture du Cantal",
    "certu_bev": "Certu/Cerema, fiche n° 03 BEV – Implantation (juillet 2010)",
    "iisr1": "IISR 1re partie (VC 04/09/2025)",
    "iisr6": "IISR 6e partie (VC 04/09/2025)",
    "setra_gc": "Setra, guide technique GC Garde-corps (1997)",
    "cerema_gc_cycles": "Cerema, Hauteurs de garde-corps en présence de cycles",
    "angers_cpu": "Ville d'Angers, Cahier de prescriptions urbaines (2018)",
    "trafic_feux": "Trafic, fiches feux D200 (2023)",
    "grandlyon_barriere": "Métropole de Lyon, fiche Réflexe Les barrières (2019)",
}


def S(doc, page=None, article=None, figure=None):
    d = {"doc": DOCS.get(doc, doc), "cle": doc}
    if page is not None:
        d["page"] = page
    if article:
        d["article"] = article
    if figure:
        d["figure"] = figure
    return d


def R(id_, sujet, condition, valeurs, unite, source, confiance="haute", tolerance=None, note=None):
    r = dict(id=id_, sujet=sujet, condition=condition, valeurs=valeurs, unite=unite, tolerance=tolerance, source=source,
             confiance=confiance)
    if note:
        r["note"] = note
    return r


def regles_profils():
    out = []
    for pid, p in SP.PROFILS.items():
        s0 = p["sources"][0]
        out.append(R(f"profil_{pid}", "bordures" if p["famille"] != "caniveau" else "caniveaux",
                     f"élément préfabriqué de profil {pid}",
                     dict(base_m=p["base"], H_m=p["H"], vue_nominale_m=p.get("vue"), contour_uv_m=p["pts"],
                          lecture=p.get("lecture"), masse_catalogue_kg_par_m=(SP.MASSES_KG.get(pid) or (None,))[0]),
                     "m", S(s0["doc"], s0.get("page"), figure=s0.get("figure")), p["confiance"],
                     tolerance="NF EN 1340 / NF P 98-340/CN : voir regle tolerances_bordures",
                     note="vue nominale : assets/specs/bordures.json (vue_courante) ou Celtys p. 3 (I1, I2) ; "
                          "u = 0 sur la face vue, v = 0 au dessous du bloc"))
    return out


REGLES = [
    R("liste_profils_nf", "bordures", "profils normalisés des bordures et caniveaux béton certifiés NF",
      {"A": ["A1", "A2"], "P": ["P1", "P2", "P4"], "T": ["T1", "T2", "T3", "T4"], "I": ["I1", "I2", "I3", "I4"],
       "CS": ["CS1", "CS2", "CS3", "CS4"], "CC": ["CC1", "CC2"],
       "usage": {"A": "accotements de routes, franchissables", "P": "parcs de stationnement, allées, terrains de sport",
                 "T": "trottoirs des voiries urbaines", "I": "îlots directionnels : posées (I1, I3) ou encastrées (I2, I4)",
                 "CS": "caniveaux simple pente (avec bordures A ou T)", "CC": "caniveaux double pente"}},
      None, S("alkern2026", 56), "haute",
      note="extrait du guide CERIB 206E reproduit par Alkern ; I5, I6 et P3 ne figurent pas dans la liste"),
    R("classes_resistance", "bordures", "classe de résistance en flexion (NF EN 1340)",
      {"U": {"MPa_min": 6.0, "emploi": "voiries urbaines à circulation intense"}, "T": {"MPa_min": 5.0, "emploi": "emplois courants"},
       "S": {"MPa_min": 3.5, "emploi": "efforts réduits"}}, "MPa", S("alkern2026", 56)),
    R("pas_element", "bordures", "pose en éléments de 1 m", {"pas_m": 1.0, "longueur_reelle_m": [0.992, 0.994], "joint_mm": [6, 8]},
      "m", S("sepa_T", 1), "haute", note="T1 994 mm, T2 992 mm (Sepa p. 1-2) ; éléments de 0,50 m pour les courbes serrées"),
    R("tolerances_bordures", "bordures", "tolérances dimensionnelles (béton, NF EN 1340 / NF P 98-340/CN)",
      SP.TOLERANCES, "mm ou %", S("fabemi_I2", 1)),
    R("raccord_bateau", "bordures", "élément de raccord (rampant) entre bordure courante et abaissé",
      {"longueur_m": 1.0, "variantes": ["droite", "gauche"], "exemples": ["T2 / T2 surbaissée", "T2 / T2 basse", "T3 / T3 surbaissée"]},
      "m", S("alkern2026", 11), "haute"),
    R("abaisse_ressaut", "accessibilite", "au droit de chaque traversée piétonne (abaissé de trottoir)",
      {"ressaut_max_m": 0.02, "ressaut_max_chanfrein_1_pour_3_m": 0.04, "largeur_min_abaisse_m": 1.20,
       "distance_min_entre_ressauts_m": 2.50}, "m", S("arrete2007", 2, article="art. 1er, 4° et 5°")),
    R("contraste_poteaux_bornes", "mobilier", "bornes et poteaux sur cheminement",
      {"bande_contrastee_hauteur_min_m": 0.10, "position_poteaux_m": [1.20, 1.40],
       "bornes_H_max_1_30": "partie contrastée en partie haute"}, "m", S("arrete2007", 2, article="art. 1er, 6° b")),
    R("element_bas_barrieres", "mobilier", "barrières et obstacles en saillie", {"element_bas_max_m": 0.40}, "m",
      S("arrete2007", 2, article="art. 1er, 6°")),
    R("bev_dimensions", "accessibilite", "bande d'éveil de vigilance (NF P 98-351 révisée)",
      {"largeur_standard_m": 0.5875, "distance_au_nez_de_bordure_m": 0.50}, "m", S("certu_bev", 3), "haute",
      note="0,50 m du nez de bordure : fiche p. 6 ; plots Ø 25 mm, h 5 mm, entraxe 75 mm : source secondaire (Hellopro), "
           "confiance faible ; formats fabricants 600 × 420 (Samse), 820 × 420 et 820 × 607 (Passage SAS)"),
    R("supports_accotement", "signalisation_verticale", "supports métalliques standards des panneaux d'accotement",
      {"rectangulaires_mm": ["40 × 27", "40 × 40", "80 × 40", "80 × 80"], "ronds_mm": [48.3, 60.3, 76.0],
       "moment_max_daNm": 570, "mats_directionnels_D_mm": [76, 89, 114, 140, 168]}, "mm", S("iisr1", 15, article="art. 6 B 1°")),
    R("hauteur_panneaux_agglo", "signalisation_verticale", "panneaux en agglomération éclairée",
      {"hauteur_sous_panneau_max_m": 2.30}, "m", S("iisr1", 19, article="art. 9 b")),
    R("hauteur_panneaux_dessus_chaussee", "signalisation_verticale", "panneaux sur portique, potence ou haut-mât",
      {"hauteur_min": "gabarit de la route + 0,10 m (entretien) + 0,50 m (protection)"}, "m", S("iisr1", 19, article="art. 9 c")),
    R("feux_diametres", "feux", "feux circulaires principaux pour véhicules",
      {"diametres_mm": [200, 300], "mixte": "rouge 300 + jaune et vert 200", "directionnels": "le plus souvent 300",
       "R19_mm": [90, 200], "R24_min_mm": 160}, "mm", S("iisr6", 10, article="art. 109-4")),
    R("feux_repetiteurs", "feux", "feux répétiteurs (R22, R23 ; répétition des R11)", {"diametre_mm": 90}, "mm",
      S("iisr6", 35), "haute", note="« généralement 90 mm » (p. 35 R22, p. 36 R23)"),
    R("feux_ordre_R11v", "feux", "signal tricolore circulaire R11v", {"ordre_bas_vers_haut": ["vert", "jaune", "rouge"]}, None,
      S("iisr6", 5, article="art. 109-3 A", figure="fig. 1")),
    R("feux_ordre_R12", "feux", "signal piéton R12 (et R12m)",
      {"horizontal": "vert à droite, rouge à gauche (vu par le piéton)", "vertical": "vert en bas"}, None,
      S("iisr6", 5, article="art. 109-3 A", figure="fig. 2")),
    R("feux_ordre_R13", "feux", "signaux tricolores modaux R13c (cycle), R13b (BUS)",
      {"ordre_bas_vers_haut": ["vert", "jaune", "rouge"], "pictogramme": "le même sur les trois feux"}, None,
      S("iisr6", 6, figure="fig. 3")),
    R("feux_implantation_trottoir", "feux", "signaux tricolores principaux sur trottoir, accotement ou îlot",
      {"gabarit_libre_m": 2.00, "axe_feu_superieur_max_m": 4.20}, "m", S("iisr6", 11, figure="fig. 16")),
    R("feux_aspect", "feux", "tous les feux principaux",
      {"visiere": "obligatoire (dispositif limitant l'éclairement par le soleil)", "fond": "surface sombre formant contraste",
       "monobloc": True, "ecran_contraste_noir": "obligatoire hors agglomération, recommandé sinon"}, None, S("iisr6", 11)),
    R("feux_module_D200", "feux", "module de feu D200 (ordre de grandeur fabricant)",
      {"module_h_mm": 240, "module_l_mm": 265, "visiere_mm": 200, "tricolore_h_mm": 865, "mat_D_mm": 90}, "mm",
      S("trafic_feux", 1), "moyenne", note="fiches de feux de chantier / accès privés ; boîtiers urbains à vérifier"),
    R("garde_corps_hauteur", "ponts", "garde-corps de pont",
      {"pietons_m": 1.00, "piste_cyclable_etroite_ou_familiale_m": 1.20, "cas_particuliers_m": 1.40}, "m",
      S("cerema_gc_cycles", 1)),
    R("garde_corps_barreaux", "ponts", "barreaudage vertical", {"vide_max_m": 0.15, "vide_batiment_m": 0.11}, "m",
      S("setra_gc", 13)),
    R("garde_corps_S8", "ponts", "modèle S8 (exemple du guide)",
      {"main_courante_mm": "120 × 55 × 4", "montants_mm": "80 × 40 × 4", "entraxe_montants_m": 1.50,
       "lisse_inferieure_mm": "60 × 30 × 2,7", "barreaux_mm": "30 × 30 × 1,5", "hauteur_montants_m": 1.0}, "mm",
      S("setra_gc", 68), note="hauteur des montants : p. 73"),
    R("potelet_gorge_angers", "mobilier", "potelet à gorge (prescription Ville d'Angers)",
      {"diametre_mm": 101.6, "tube_mm": 3.65, "H_hors_sol_m": 1.00, "H_traversees_m": 1.20, "couleurs": "RAL 7016 (+ tête RAL 9010)",
       "masse_kg": [11, 15]}, "mm / m", S("angers_cpu", 1), "haute", note="fiche potelet-a-gorge (27/06/2018) : prescription locale"),
    R("barriere_croix_angers", "mobilier", "barrière croix de Saint-André (Ville d'Angers)",
      {"H_m": 1.0, "L_m": [1.0, 1.5], "masse_kg": 23, "couleur": "RAL 7016 sablé-givré"}, "m", S("angers_cpu", 1)),
    R("regle_materiaux_elements", "materiaux", "élément unitaire (pavé, dalle, bordure) vs surface pavée",
      {"element_unitaire": "matériau de matière (beton_prefa_lisse, beton_bordure, granit_gris_flamme)",
       "sol_tuilable": "matériau d'appareillage (paves_*, dalles_*)"}, None, {"doc": "observation des rendus de contrôle du 16/10/2026"},
      "haute", note="un pavé portant une texture de pavage montre de faux joints"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="D:/DocRoute/14_Assets_Route_Statics/regles_assets_route.json")
    a = ap.parse_args()
    regles = regles_profils() + REGLES
    doc = dict(schema="docroute/regles/1.0", date=datetime.date.today().isoformat(),
               producteur="recon/pcg/assets_route/exporter_regles_assets.py",
               role="Règles de cotes et d'implantation des static meshes de la route (bibliothèque route_fr)",
               nb_regles=len(regles), regles=regles)
    Path(a.sortie).write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(a.sortie, len(regles), "règles")


if __name__ == "__main__":
    main()
