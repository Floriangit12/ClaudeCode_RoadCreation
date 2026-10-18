# -*- coding: utf-8 -*-
"""Construit `vehicules_projet.json` (lot L3a) : véhicules de projet sourcés + cinématique dérivée.

    python recon/generateur/vehicules/construire_vehicules.py            # écrit vehicules_projet.json
    python recon/generateur/vehicules/construire_vehicules.py --verifier # reconstruit en mémoire et compare à l'octet

Chaque cote porte {valeur, unite, source, nature, confiance} et, si elle est dérivée, le calcul. Natures :
`norme` (règlement ou valeur de conception d'un guide), `donnee_constructeur` (fiche du constructeur),
`annonce` (fiche de véhicule d'occasion ou source secondaire : confiance moyenne), `derive` (calculé ici depuis des
cotes citées), `convention` (choix de génération [G], écrit). Aucune cote « estimée » sans source.

Les cotes manquantes des guides (empattements, porte-à-faux : lacune signalée par DocRoute 10, PROFILS_EN_TRAVERS
§ 4.2) viennent des fiches constructeurs ; celles qu'aucune fiche lue ne donne sont DÉRIVÉES des gabarits de giration
des guides (VU p. 144, CF p. 22) ou de la couronne d'homologation (96/53, annexe I § 1.5), et le rapport L3a dit quels
contrôles en deviennent « par construction ».
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import balayage as B  # noqa: E402

SORTIE = ICI / "vehicules_projet.json"
DATE = "2026-10-17"

DR10 = "D:/DocRoute/10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/sources/"
DR17 = "D:/DocRoute/17_Modele_Vehicules_Conducteurs/01_Vehicules/"

SOURCES = {
    "VU": {"titre": "Cerema, Voirie urbaine - guide d'aménagement, 2016",
           "chemin": DR10 + "Cerema_Voirie_Urbaine_Guide_Amenagement_2016.pdf",
           "pages": "p. 142 (gabarits : VL 1,80 x 5 m ; berline 2,10 m avec rétroviseurs) ; p. 143-144 (épure, "
                    "tableau « Exemple de rayons de braquage de véhicules standard » : rayon intérieur / extérieur (caisse))"},
    "CU": {"titre": "Certu, Carrefours urbains - guide, 2010",
           "chemin": DR10 + "CERTU_Carrefours_Urbains_Guide_2010.pdf",
           "pages": "p. 78 (directive 97/27 : couronne de 12,50 m / 5,30 m)"},
    "CF": {"titre": "Certu, Guide de conception des carrefours à feux, 2010",
           "chemin": DR10 + "CERTU_Guide_Conception_Carrefours_a_Feux_2010.pdf",
           "pages": "p. 22, § 3.8 (autobus articulé : rayon intérieur 5,30 m, balayage extérieur 12 m)"},
    "N05": {"titre": "Cerema, note d'information n° 05, Le giratoire à terre-plein central franchissable en "
                     "milieu interurbain, novembre 2018",
            "chemin": "D:/DocRoute/02_Cerema_Guides_Voirie_Carrefours_Cyclable/"
                      "Cerema_Giratoire_Terre_Plein_Franchissable_Interurbain.pdf",
            "pages": "p. 4, note 1 (autocar 15,00 x 2,55 m à essieux arrière directionnels ; tracteur 6,08 x 2,50 m "
                     "+ semi-remorque 13,67 x 2,55 m)"},
    "D9653": {"titre": "Directive 96/53/CE consolidée au 14/08/2019 (poids et dimensions)",
              "chemin": DR17 + "sources/reglementation/UE_Directive_96_53_consolidee_20190814_FR.pdf",
              "pages": "annexe I § 1.1 (longueurs : véhicule articulé 16,50 m), § 1.2 (largeur 2,55 m), § 1.5 "
                       "(couronne 12,50 / 5,30 m), § 1.5 bis (débord ≤ 0,60 m des autobus), § 1.6 (pivot - arrière "
                       "≤ 12,00 m), § 4.4 (pivot - avant ≤ 2,04 m) ; PDF p. 15-16 et 20"},
    "CITARO": {"titre": "Mercedes-Benz, Citaro - technical data and equipment at a glance (facts-citaro.pdf, GB)",
               "chemin": DR17 + "sources/constructeurs/MB_Citaro_facts_gb_en.pdf",
               "pages": "p. 3 (longueurs, largeur, empattements, porte-à-faux, turning circle) ; p. 4 (track circle, "
                        "braquage 53°/46°)"},
    "TRANSBUS": {"titre": "transbus.org, fiche Iveco Bus Urbanway 12 (base documentaire d'amateurs ; données "
                          "d'origine constructeur non citées), reprise par DocRoute 17",
                 "chemin": DR17 + "vehicules_parametres.json",
                 "pages": "paramètre BUS12-DIM-URBANWAY (confiance moyenne)"},
    "AEE_VP": {"titre": "AEE, CO2 voitures neuves 2021, France, segment berline (via DocRoute 17)",
               "chemin": DR17 + "vehicules_parametres.json",
               "pages": "paramètre BERLINE-EMPATTEMENT (médiane 2 875 mm, n = 55 649)"},
    "SETRA": {"titre": "Setra, fiche « ComfortClass 500 HD » (setra-bus.com, éditions cs_CZ, pl_PL, sk_SK), "
                       "S 519 HD ; Bus & Coach Buyer, essai ComfortClass 500 du 02/01/2015",
              "chemin": "https://www.setra-bus.com/pl_PL/models/cc-hd-models/models/facts-ComfortClass-500-HD-Modelle.html ; "
                        "https://www.busandcoachbuyer.com/?p=11001",
              "pages": "S 519 HD : longueur 14 945, largeur 2 550, empattement essieu avant - essieu moteur 7 140, "
                       "porte-à-faux avant 2 890 et arrière 3 315, cercle de braquage minimal 24 090 mm (tableau lu par "
                       "moteur de recherche le 17/10/2026, non téléchargé) ; « main wheelbase of 7.14m », « steered third "
                       "axle » (B&CB, lu le 17/10/2026)"},
    "SCHMITZ": {"titre": "Annonce truckscout24 A222-13-422 : Schmitz Cargobull S.CS 24/L-13.62 (2023)",
                "chemin": "https://www.truckscout24.com/tsp/ts-222-13-422",
                "pages": "« Wheelbase 7700 mm » ; « Axle distance 1310/1310 mm » ; « kingpin position 1690mm » "
                         "(lu le 17/10/2026)"},
    "TRACTEURS": {"titre": "Annonces de tracteurs routiers 4x2 : Mercedes-Benz Actros 1845 LS (truckscout24 "
                           "ts-206-07-670, ts-205-97-170 : empattement 3 700 mm) ; Renault Trucks T 480 4x2 "
                           "(used-renault-trucks.com : 3 700 mm)",
                  "chemin": "https://www.truckscout24.de/tsp/ts-206-07-670 ; https://www.used-renault-trucks.com",
                  "pages": "relevé par moteur de recherche le 17/10/2026 (d'autres annonces : 3 710 à 3 850 mm)"},
    "G": {"titre": "Choix de génération du lot L3a (convention écrite, PLAN_GENERATEUR § 2.4 et RF-GV-TRJ-006)",
          "chemin": "recon/generateur/vehicules/balayage.py", "pages": "docstring"},
}


def cote(valeur, source, nature, confiance, calcul=None, note=None, unite="m"):
    d = {"valeur": round(float(valeur), 4), "unite": unite, "source": source, "nature": nature,
         "confiance": confiance}
    if calcul:
        d["calcul"] = calcul
    if note:
        d["note"] = note
    return d


def unite_cin(nom, empattement, avant, arriere, largeur, attelage=None, rayon_avant_pivot=None, soufflet=False):
    """Unité cinématique (valeurs arrondies au micromètre : la giration est recalculée sur ces valeurs)."""
    r6 = lambda x: round(float(x), 6)  # noqa: E731
    u = {"nom": nom, "empattement": r6(empattement), "avant": r6(avant), "arriere": r6(arriere),
         "largeur_balayage": r6(largeur)}
    if attelage is not None:
        u["attelage"] = r6(attelage)
    if rayon_avant_pivot is not None:
        u["rayon_avant_pivot"] = r6(rayon_avant_pivot)
    if soufflet:
        u["soufflet"] = True
    return u


def _u(d):
    """Unités cinématiques (balayage.Unite) depuis la forme JSON."""
    return B.unites_depuis_json({"cinematique": {"unites": d}})


def giration(unites_json, rext_ref, src_rext, nature_rext, conf_rext, rint_ref=None, src_rint=None, note=None):
    """Braquage minimal calé sur un rayon extérieur de caisse publié ; rayons établis recalculés."""
    un = _u(unites_json)
    r0 = B.r0_pour_rext(un, rext_ref)
    re_ = B.rayons_etablis(un, r0)
    wb = un[0].empattement
    g = {
        "rayon_exterieur_caisse_min": cote(rext_ref, src_rext, nature_rext, conf_rext,
                                           note="rayon extérieur de la caisse au braquage maximal : donnée d'entrée du calage"),
        "rayon_essieu_arriere_min": cote(r0, "G", "derive", conf_rext,
                                         calcul="r0 tel que le rayon extérieur de caisse en régime établi = "
                                                "rayon_exterieur_caisse_min (balayage.r0_pour_rext)"),
        "rayon_point_guide_min": cote(re_["R_guide"], "G", "derive", conf_rext,
                                      calcul="sqrt(r0² + empattement²) : rayon minimal du centre de l'essieu avant"),
        "angle_braquage_bicyclette_max": cote(math.degrees(math.asin(wb / re_["R_guide"])), "G", "derive", conf_rext,
                                              calcul="asin(empattement / rayon_point_guide_min)", unite="°"),
        "rayon_interieur_calcule": cote(re_["Rint"], "G", "derive", conf_rext,
                                        calcul="balayage.rayons_etablis(r0) : distance minimale centre - caisses"),
    }
    if rint_ref is not None:
        g["rayon_interieur_reference"] = cote(rint_ref, src_rint, "norme", "haute",
                                              note="valeur publiée, comparée au rayon intérieur calculé (contrôle L3a)")
    if note:
        g["note"] = note
    # conformité à la couronne d'homologation (96/53 § 1.5) : rayon intérieur quand l'extérieur vaut 12,50 m
    r0h = B.r0_pour_rext(un, 12.50)
    rint_h = B.rayons_etablis(un, r0h)["Rint"]
    g["couronne_96_53"] = {"Rext": 12.50, "Rint": round(rint_h, 4),
                           "conforme": rint_h >= 5.30 - 5e-4,
                           "tolerance": "0,5 mm (arrondi des cotes au micromètre)",
                           "source": "D9653 annexe I § 1.5 ; CU p. 78"}
    return g


def dichotomie(f, lo, hi, n=200):
    """Racine de f croissante ou décroissante sur [lo, hi]."""
    flo = f(lo)
    for _ in range(n):
        m = 0.5 * (lo + hi)
        fm = f(m)
        if (fm > 0) == (flo > 0):
            lo, flo = m, fm
        else:
            hi = m
    return 0.5 * (lo + hi)


# ----------------------------------------------------------------------------------------------------------------
def vl():
    L, w_caisse, w_bal = 5.00, 1.80, 2.10
    wb = 2.875
    rint, rext = 3.60, 6.90
    d = math.sqrt(rext ** 2 - (rint + w_bal) ** 2)          # empattement + porte-à-faux avant
    pav = d - wb
    par = L - wb - pav
    dims = {
        "longueur": cote(L, "VU p. 142, 144", "norme", "haute"),
        "largeur_caisse": cote(w_caisse, "VU p. 142", "norme", "haute",
                               note="« largeur d'une berline : environ 2,10 m avec rétroviseurs (1,80 m sans) »"),
        "largeur_retroviseurs": cote(w_bal, "VU p. 142", "norme", "haute"),
        "empattement": cote(wb, "AEE_VP (DocRoute 17, BERLINE-EMPATTEMENT, médiane)", "donnee_administrative", "haute"),
        "porte_a_faux_avant": cote(pav, "VU p. 144 ; VU p. 142 ; AEE_VP", "derive", "moyenne",
                                   calcul="sqrt(Rext² − (Rint + l)²) − empattement, Rext 6,90, Rint 3,60 (VU p. 144), "
                                          "l = 2,10 m (encombrement rétroviseurs compris, VU p. 142)"),
        "porte_a_faux_arriere": cote(par, "VU p. 144 ; AEE_VP", "derive", "moyenne",
                                     calcul="longueur − empattement − porte-à-faux avant"),
    }
    cin = [unite_cin("caisse", wb, wb + pav, par, w_bal)]
    return {
        "libelle": "Voiture particulière (berline de référence, VU p. 144)",
        "categorie": "M1", "role": "véhicule léger de vérification (urbain)",
        "dimensions": dims,
        "cinematique": {"unites": cin,
                        "note": "balayage à la largeur rétroviseurs compris (2,10 m) : « encombrement total » (VU p. 144)"},
        "giration": giration(cin, rext, "VU p. 144", "norme", "haute", rint, "VU p. 144",
                             note="porte-à-faux avant dérivé des deux rayons de VU p. 144 : rayon intérieur reproduit "
                                  "PAR CONSTRUCTION (pas un contrôle)"),
    }


def bus_standard():
    L, w, wb, pav, par = 12.00, 2.50, 6.12, 2.71, 3.17
    src = "TRANSBUS (DocRoute 17, BUS12-DIM-URBANWAY)"
    dims = {
        "longueur": cote(L, src, "annonce", "moyenne", note="VU p. 144 : bus 12 m"),
        "largeur_caisse": cote(w, src, "annonce", "moyenne"),
        "empattement": cote(wb, src, "annonce", "moyenne"),
        "porte_a_faux_avant": cote(pav, src, "annonce", "moyenne"),
        "porte_a_faux_arriere": cote(par, src, "annonce", "moyenne"),
    }
    cin = [unite_cin("caisse", wb, wb + pav, par, w)]
    return {
        "libelle": "Autobus urbain standard 12 m (Iveco Urbanway 12, successeur des Agora / Citelis)",
        "categorie": "M3 classe I", "role": "bus standard de VU p. 144 (urbain)",
        "dimensions": dims,
        "cinematique": {"unites": cin},
        "giration": giration(cin, 11.50, "VU p. 144", "norme", "haute", 4.80, "VU p. 144",
                             note="seul le rayon extérieur (11,50 m) sert au calage ; le rayon intérieur calculé est "
                                  "comparé à 4,80 m (VU p. 144) : contrôle indépendant des cotes du véhicule"),
    }


def bus_citaro():
    L, w, wb, pav, par = 12.135, 2.55, 5.90, 2.805, 3.43
    dims = {
        "longueur": cote(L, "CITARO p. 3", "donnee_constructeur", "haute"),
        "largeur_caisse": cote(w, "CITARO p. 3", "donnee_constructeur", "haute"),
        "largeur_retroviseurs": cote(2.95, "CITARO p. 3", "donnee_constructeur", "haute"),
        "empattement": cote(wb, "CITARO p. 3", "donnee_constructeur", "haute"),
        "porte_a_faux_avant": cote(pav, "CITARO p. 3", "donnee_constructeur", "haute"),
        "porte_a_faux_arriere": cote(par, "CITARO p. 3", "donnee_constructeur", "haute"),
    }
    cin = [unite_cin("caisse", wb, wb + pav, par, w)]
    return {
        "libelle": "Autobus Mercedes-Benz Citaro 12 m (variante constructeur)",
        "categorie": "M3 classe I", "role": "variante du bus standard (contrôle de sensibilité)",
        "dimensions": dims,
        "cinematique": {"unites": cin},
        "giration": giration(cin, 22.970 / 2, "CITARO p. 3 (turning circle 22 970 mm)", "donnee_constructeur",
                             "haute", 4.80, "VU p. 144",
                             note="cercle de braquage du constructeur ; les autres cotes de giration de la fiche (ring "
                                  "width 7 478 mm, track circle 19 160 mm) ne sont pas cohérentes avec un modèle rigide "
                                  "sans glissement (DocRoute 17, VEHICULES § 3.3) : non utilisées"),
    }


def bus_articule():
    L, w, wb1, wb2, pav, par = 18.125, 2.55, 5.90, 5.99, 2.805, 3.43
    rext_cf, rint_cf = 12.0, 5.30

    def unites(e):
        return [unite_cin("caisse_avant", wb1, wb1 + pav, e, w, attelage=-e, soufflet=True),
                unite_cin("caisse_arriere", wb2 - e, wb2 - e, par, w)]

    def ecart(e):
        un = _u(unites(e))
        return B.rayons_etablis(un, B.r0_pour_rext(un, rext_cf))["Rint"] - rint_cf
    e = dichotomie(ecart, 0.5, 4.0)
    dims = {
        "longueur": cote(L, "CITARO p. 3 (Citaro G)", "donnee_constructeur", "haute"),
        "largeur_caisse": cote(w, "CITARO p. 3", "donnee_constructeur", "haute"),
        "empattement_avant_milieu": cote(wb1, "CITARO p. 3", "donnee_constructeur", "haute"),
        "empattement_milieu_moteur": cote(wb2, "CITARO p. 3", "donnee_constructeur", "haute"),
        "porte_a_faux_avant": cote(pav, "CITARO p. 3", "donnee_constructeur", "haute"),
        "porte_a_faux_arriere": cote(par, "CITARO p. 3", "donnee_constructeur", "haute"),
        "articulation_derriere_essieu_milieu": cote(
            e, "CF p. 22 ; CITARO p. 3", "derive", "faible",
            calcul="e tel que, au braquage donnant un balayage extérieur de 12 m, le rayon intérieur vaille 5,30 m "
                   "(CF p. 22) ; dichotomie sur le modèle établi",
            note="position de l'articulation absente des fiches lues ; caisse avant = 2,805 + 5,90 + e"),
    }
    cin = unites(e)
    return {
        "libelle": "Autobus articulé 18 m (Mercedes-Benz Citaro G, pousseur)",
        "categorie": "M3 classe I", "role": "bus articulé de CF p. 22 (lignes fortes)",
        "dimensions": dims,
        "cinematique": {"unites": cin,
                        "note": "soufflet = disque de diamètre 2,55 m à l'articulation (convention [G]) ; caisse "
                                "arrière de l'articulation à l'arrière"},
        "giration": giration(cin, rext_cf, "CF p. 22", "norme", "haute", rint_cf, "CF p. 22",
                             note="articulation dérivée de CF p. 22 : rayon intérieur reproduit PAR CONSTRUCTION ; le "
                                  "constructeur annonce un cercle de braquage de 22 970 mm (Rext 11,485 m)"),
    }


def semi_remorque():
    Lt, wt = 6.08, 2.50
    Ls_tot, ws = 13.67, 2.55
    wb_t = 3.70
    a = 16.50 - 12.00                    # avant du tracteur -> pivot, ensemble de longueur maximale
    b = 12.00                            # pivot -> arrière de la semi-remorque
    l_s = 7.70                           # pivot -> milieu du groupe de 3 essieux
    entraxe = 1.31
    r_av = 2.04
    av_pivot = Ls_tot - b

    def unites(c):
        pav = a - wb_t + c
        return [unite_cin("tracteur", wb_t, wb_t + pav, Lt - wb_t - pav, wt, attelage=c),
                unite_cin("semi_remorque", l_s, l_s + av_pivot, b - l_s, ws, rayon_avant_pivot=r_av)]

    def ecart(c):
        un = _u(unites(c))
        return B.rayons_etablis(un, B.r0_pour_rext(un, 12.50))["Rint"] - 5.30
    c = dichotomie(ecart, 0.0, 1.5)
    pav = a - wb_t + c
    dims = {
        "tracteur_longueur": cote(Lt, "N05 p. 4", "norme", "haute"),
        "tracteur_largeur": cote(wt, "N05 p. 4", "norme", "haute"),
        "tracteur_empattement": cote(wb_t, "TRACTEURS", "annonce", "moyenne"),
        "tracteur_avant_pivot": cote(a, "D9653 annexe I § 1.1 et 1.6", "derive", "haute",
                                     calcul="16,50 (véhicule articulé) − 12,00 (pivot - arrière) : ensemble de longueur "
                                            "maximale"),
        "avance_sellette": cote(c, "D9653 annexe I § 1.5 ; CU p. 78 ; SCHMITZ ; TRACTEURS", "derive", "faible",
                                calcul="c tel que l'ensemble s'inscrive au plus juste dans la couronne 12,50 / 5,30 m "
                                       "(véhicule de vérification limite) ; dichotomie sur le modèle établi",
                                note="cote de sellette absente des fiches lues ; ordre de grandeur courant 0,5-0,8 m"),
        "tracteur_porte_a_faux_avant": cote(pav, "D9653 ; TRACTEURS", "derive", "faible",
                                            calcul="avant_pivot − empattement + avance_sellette"),
        "tracteur_porte_a_faux_arriere": cote(Lt - wb_t - pav, "N05 p. 4", "derive", "faible",
                                              calcul="longueur − empattement − porte-à-faux avant"),
        "semi_longueur": cote(Ls_tot, "N05 p. 4", "norme", "haute"),
        "semi_largeur": cote(ws, "N05 p. 4 ; D9653 annexe I § 1.2", "norme", "haute"),
        "semi_pivot_arriere": cote(b, "D9653 annexe I § 1.6", "norme", "haute",
                                   note="maximum réglementaire, retenu pour le véhicule de vérification"),
        "semi_pivot_avant": cote(av_pivot, "N05 p. 4 ; D9653 § 1.6", "derive", "haute",
                                 calcul="13,67 − 12,00 ; l'annonce SCHMITZ donne 1,69 m"),
        "semi_rayon_avant_pivot": cote(r_av, "D9653 annexe I § 4.4", "norme", "haute",
                                       note="coins avant chanfreinés au rayon de 2,04 m autour du pivot"),
        "semi_empattement": cote(l_s, "SCHMITZ", "annonce", "moyenne",
                                 note="pivot - milieu du groupe de trois essieux"),
        "semi_entraxe_essieux": cote(entraxe, "SCHMITZ", "annonce", "moyenne"),
        "semi_porte_a_faux_arriere_dernier_essieu": cote(b - l_s - entraxe, "D9653 ; SCHMITZ", "derive", "moyenne",
                                                         calcul="12,00 − 7,70 − 1,31"),
    }
    cin = unites(c)
    return {
        "libelle": "Tracteur 4x2 + semi-remorque 3 essieux (ensemble de vérification N05, 16,50 m)",
        "categorie": "N3 + O4", "role": "poids lourd de vérification interurbain (ACI, N05) et couronne 96/53",
        "dimensions": dims,
        "cinematique": {"unites": cin,
                        "note": "essieu équivalent de la semi-remorque = milieu du groupe de trois essieux fixes "
                                "(convention [G]) ; attelage = sellette, en avant de l'essieu moteur"},
        "giration": giration(cin, 12.50, "D9653 annexe I § 1.5 ; CU p. 78", "norme", "haute", 5.30,
                             "D9653 annexe I § 1.5 ; CU p. 78",
                             note="braquage minimal = couronne d'homologation ; avance de sellette dérivée de cette "
                                  "couronne : rayon intérieur reproduit PAR CONSTRUCTION en régime établi"),
    }


def pl_porteur(pav_cabine):
    L, w = 11.00, 2.55
    rint, rext = 6.50, 12.50
    d = math.sqrt(rext ** 2 - (rint + w) ** 2)
    wb = d - pav_cabine
    dims = {
        "longueur": cote(L, "VU p. 144", "norme", "haute"),
        "largeur_caisse": cote(w, "D9653 annexe I § 1.2 a)", "norme", "haute",
                               note="2,60 m pour une caisse frigorifique (D9653 § 1.2 b ; VU p. 142)"),
        "porte_a_faux_avant": cote(pav_cabine, "semi_remorque.tracteur_porte_a_faux_avant", "derive", "faible",
                                   note="même cabine avancée que le tracteur de vérification"),
        "empattement": cote(wb, "VU p. 144 ; D9653 § 1.2", "derive", "faible",
                            calcul="sqrt(Rext² − (Rint + l)²) − porte-à-faux avant ; Rext 12,50, Rint 6,50 (VU p. 144), "
                                   "l = 2,55 m",
                            note="empattement équivalent (milieu du groupe arrière pour un 6x2/6x4)"),
        "porte_a_faux_arriere": cote(L - d, "VU p. 144", "derive", "faible",
                                     calcul="longueur − (empattement + porte-à-faux avant)"),
    }
    cin = [unite_cin("caisse", wb, d, L - d, w)]
    return {
        "libelle": "Camion porteur 11 m (camion de VU p. 144)",
        "categorie": "N3", "role": "poids lourd urbain (livraison, collecte)",
        "dimensions": dims,
        "cinematique": {"unites": cin},
        "giration": giration(cin, rext, "VU p. 144", "norme", "haute", rint, "VU p. 144",
                             note="empattement dérivé des deux rayons de VU p. 144 : rayon intérieur reproduit PAR "
                                  "CONSTRUCTION"),
    }


def autocar():
    L, w = 15.00, 2.55
    wb, pav = 7.14, 2.89
    tag = 14.945 - 2.890 - 7.140 - 3.315
    par_tag = L - pav - wb - tag
    dims = {
        "longueur": cote(L, "N05 p. 4", "norme", "haute", note="Setra S 519 HD : 14,945 m"),
        "largeur_caisse": cote(w, "N05 p. 4 ; SETRA", "norme", "haute"),
        "empattement_avant_moteur": cote(wb, "SETRA", "donnee_constructeur", "moyenne"),
        "porte_a_faux_avant": cote(pav, "SETRA", "donnee_constructeur", "moyenne"),
        "entraxe_moteur_suiveur": cote(tag, "SETRA", "derive", "moyenne",
                                       calcul="14,945 − 2,890 − 7,140 − 3,315 (S 519 HD)"),
        "porte_a_faux_arriere_suiveur": cote(par_tag, "N05 p. 4 ; SETRA", "derive", "moyenne",
                                             calcul="15,00 − porte-à-faux avant − empattement − entraxe"),
    }
    cin = [unite_cin("caisse", wb, wb + pav, tag + par_tag, w)]
    return {
        "libelle": "Autocar 15 m à essieu arrière directionnel (autocar de vérification N05 ; Setra S 519 HD)",
        "categorie": "M3 classe III", "role": "car interurbain de vérification (N05)",
        "dimensions": dims,
        "cinematique": {"unites": cin,
                        "note": "essieu suiveur directionnel idéal : centre instantané sur l'essieu moteur "
                                "(empattement équivalent = avant - moteur, convention [G])"},
        "giration": giration(cin, 24.090 / 2, "SETRA (cercle de braquage 24 090 mm)", "donnee_constructeur",
                             "moyenne",
                             note="aucun rayon publié par N05 ; cercle de braquage du constructeur pris comme diamètre "
                                  "extérieur de caisse"),
    }


def construire() -> dict:
    semi = semi_remorque()
    pav_tracteur = semi["dimensions"]["tracteur_porte_a_faux_avant"]["valeur"]
    vehicules = {
        "vl": vl(),
        "bus_standard_12m": bus_standard(),
        "bus_12m_citaro": bus_citaro(),
        "bus_articule_18m": bus_articule(),
        "pl_porteur": pl_porteur(pav_tracteur),
        "semi_remorque": semi,
        "autocar_15m": autocar(),
    }
    return {
        "schema": "vehicules_projet/1.0",
        "lot": "L3a",
        "date": DATE,
        "construit_par": "recon/generateur/vehicules/construire_vehicules.py",
        "conventions": {
            "repere": "unités en mètres ; repère de chaque unité : x vers l'avant depuis son essieu équivalent, y à gauche",
            "point_guide": "centre de l'essieu avant directeur de l'unité motrice ; l'axe donné au balayage est la "
                           "trajectoire de ce point (RF-GV-TRJ-006 : axe de voie, arc tangent, axe de voie)",
            "modele": "bicyclette sans glissement ; tractrice exacte par pas rectiligne ; caisses rectangulaires "
                      "(chanfrein de 2,04 m de la semi-remorque, soufflet du bus articulé)",
            "unite_cinematique": "empattement : essieu avant -> essieu équivalent (unité motrice), attelage -> essieu "
                                 "équivalent (remorque) ; avant / arriere : extrémités de la caisse depuis l'essieu "
                                 "équivalent ; attelage : abscisse du point d'attelage de l'unité suivante",
            "giration": "rayon_point_guide_min = rayon minimal de l'axe suivi (régime établi, braquage maximal), "
                        "calé sur un rayon extérieur de caisse publié",
            "natures": "norme | donnee_constructeur | donnee_administrative | annonce | derive | convention",
        },
        "sources": SOURCES,
        "alias": {"VL": "vl", "berline": "vl", "bus": "bus_standard_12m", "bus_12m": "bus_standard_12m",
                  "citaro": "bus_12m_citaro", "bus_articule": "bus_articule_18m", "articule": "bus_articule_18m",
                  "PL": "pl_porteur", "camion": "pl_porteur", "porteur": "pl_porteur", "semi": "semi_remorque",
                  "SR": "semi_remorque", "car": "autocar_15m", "autocar": "autocar_15m"},
        "vehicules": vehicules,
    }


def serialiser(d) -> bytes:
    return (json.dumps(d, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def main(argv):
    octets = serialiser(construire())
    if "--verifier" in argv:
        ok = SORTIE.exists() and SORTIE.read_bytes() == octets
        print("identique" if ok else "DIFFÉRENT")
        return 0 if ok else 1
    SORTIE.write_bytes(octets)
    B._charger.cache_clear()
    print(f"{SORTIE} ({len(octets)} octets)")
    for nom, e in construire()["vehicules"].items():
        g = e["giration"]
        print(f"  {nom:18s} R_guide_min {g['rayon_point_guide_min']['valeur']:7.3f}  Rext {g['rayon_exterieur_caisse_min']['valeur']:6.3f}"
              f"  Rint calc {g['rayon_interieur_calcule']['valeur']:6.3f}"
              f"  ref {g.get('rayon_interieur_reference', {}).get('valeur', '-')}"
              f"  couronne 96/53 Rint {g['couronne_96_53']['Rint']:.3f} {'ok' if g['couronne_96_53']['conforme'] else 'NON'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
