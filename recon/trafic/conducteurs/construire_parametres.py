"""Construit conducteurs_parametres.json (volet « conducteurs » du modèle de trafic).

Chaque paramètre suit la forme machine demandée :
  {id, volet, grandeur, population, loi, parametres, unite, conditions,
   nature (norme | mesure | estimation | defaut_logiciel), source:{cle, doc, page, annee, fichier},
   confiance (elevee | moyenne | faible), statistiques_publiees, notes, role}

« statistiques_publiees » recopie les chiffres lus dans la source ; « parametres » donne la loi
utilisée par le modèle. Quand la loi est ajustée (par ex. lognormale reproduisant une moyenne et
un percentile publiés), la nature est « estimation » et la méthode est dite dans « notes ».

Usage : python construire_parametres.py [--sortie DOSSIER]
(par défaut D:/DocRoute/17_Modele_Vehicules_Conducteurs/02_Conducteurs)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lois  # noqa: E402
from sources_conducteurs import SOURCES  # noqa: E402

SORTIE_DEFAUT = "D:/DocRoute/17_Modele_Vehicules_Conducteurs/02_Conducteurs"
KMH = 1 / 3.6
G = 9.81

PARAMS = []


def src(cle, page):
    s = SOURCES[cle]
    return {"cle": cle, "doc": s["titre"], "auteurs": s["auteurs"], "annee": s["annee"], "page": page,
            "fichier": s["fichier"]}


def P(id, volet, grandeur, population, loi, parametres, unite, conditions, nature, source, confiance,
      stats=None, notes="", role="parametre_conducteur", tirage=None):
    rec = {"id": id, "volet": volet, "grandeur": grandeur, "population": population, "loi": loi,
           "parametres": parametres, "unite": unite, "conditions": conditions, "nature": nature,
           "source": source, "confiance": confiance}
    if stats:
        rec["statistiques_publiees"] = stats
    if notes:
        rec["notes"] = notes
    rec["role"] = role
    if tirage:
        rec["tirage"] = tirage
    PARAMS.append(rec)
    return rec


def r4(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


# =========================================================================================
# 1. TEMPS DE PERCEPTION-RÉACTION (TPR)
# =========================================================================================
V = "temps_perception_reaction"
ln_att = lois.lognormale_depuis_moyenne_ecart(0.73, 0.16)
P("tpr.anticipe", V, "Temps de perception-réaction au freinage, événement anticipé (le conducteur sait qu'il devra freiner)",
  "Conducteurs VL alertés, études « behind the wheel » : Olson & Sivak (n=49 jeunes, 15 âgés), Johansson & Rumar (n=321)",
  "lognormale", r4(ln_att), "s", "jour, route sèche, signal ou obstacle attendu ; temps jusqu'au début d'action sur le frein",
  "estimation", src("NCHRP400", "p. 24 (PDF 34), tableau 13, « Behind the Wheel » ; moyennes 0,72 / 0,73 / 0,75 s"), "elevee",
  stats={"moyenne": 0.73, "ecart_type": 0.16, "detail": {"Olson_Sivak_jeunes": [0.72, 0.11], "Olson_Sivak_ages": [0.73, 0.10],
                                                          "Johansson_Rumar": [0.75, 0.28]}},
  notes="Lognormale ajustée par la méthode des moments sur la moyenne pondérée publiée (0,73 ± 0,16 s). Cohérent avec Green (2000) : 0,70-0,75 s pour un événement pleinement anticipé (cité par Markkula 2016, p. 2 du manuscrit).",
  tirage={"facteur": "vigilance", "charge": -0.5, "groupe": "tpr"})

P("tpr.anticipe.age", V, "Temps de perception-réaction à un objet attendu selon l'âge et le sexe (moyennes)",
  "NCHRP 400 études 2 et 3 (Texas), conducteurs jeunes / âgés, hommes / femmes",
  "constante", {"jeunes": 0.52, "ages": 0.66, "hommes": 0.59, "femmes": 0.63, "ensemble": 0.55}, "s",
  "objet attendu (signal au pare-brise), pistes fermées", "mesure",
  src("NCHRP400", "p. 32-33 (PDF 42-43), texte et tableau 22"), "moyenne",
  notes="Utilisé pour décaler les profils « novice » (jeune) et « senior » sur l'événement anticipé ; aucune différence d'âge significative pour l'objet inattendu (Lerner, cité p. 24).",
  role="modulateur_profil")

ln_inatt = lois.lognormale_depuis_moyenne_ecart(1.27, 0.66)
P("tpr.inattendu_signal", V, "Temps de perception-réaction au freinage, signal inattendu (passage au jaune/rouge, feux stop)",
  "Conducteurs non informés observés à des feux (études « covert ») : Sivak et al. n=1644, Wortman n=839, Chang et al. n=579",
  "lognormale", r4(ln_inatt), "s", "conducteur ne sachant pas qu'il est observé ; réaction à un signal inattendu",
  "estimation", src("NCHRP400", "p. 24 (PDF 34), tableau 13, « Covert », moyenne des estimations 1,27 ± 0,66 s"), "elevee",
  stats={"moyenne": 1.27, "ecart_type": 0.66, "detail": {"Sivak": [1.21, 0.63, 1644], "Wortman": [1.30, 0.60, 839], "Chang": [1.30, 0.74, 579]}},
  notes="Lognormale (moments). Green (2000) : 1,25 s pour un événement inattendu courant (feux stop) - via Markkula 2016. Rapport inattendu / anticipé de jour = 1,75 (NCHRP 400 p. 24).",
  tirage={"facteur": "vigilance", "charge": -0.5, "groupe": "tpr"})

ln_surp = lois.lognormale_depuis_moyenne_quantile(1.10, 2.0, 0.95)
P("tpr.surprise_obstacle", V, "Temps de perception-réaction au freinage, obstacle surgissant (surprise)",
  "NCHRP 400 études 2-4 : 43 conducteurs (âgés et jeunes), véhicule d'essai ou personnel, piste et route ouverte",
  "lognormale", r4(ln_surp), "s", "objet apparaissant soudainement sur la voie, jour, conducteur non prévenu",
  "estimation", src("NCHRP400", "p. 36 (PDF 46) : moyenne ≈ 1,10 s, 95e centile 2,0 s ; p. 32 (PDF 42) tableau 21"), "elevee",
  stats={"moyenne": 1.10, "p95": 2.0, "tableau21": {"etude2_ages": [0.82, 0.159, 12], "etude2_jeunes": [0.82, 0.203, 10],
                                                     "etude3_ages": [1.14, 0.353, 7], "etude3_jeunes": [0.93, 0.191, 3],
                                                     "etude4_ages": [1.06, 0.222, 5], "etude4_jeunes": [1.14, 0.204, 6]},
         "semi_alerte_p90_p95": [2.0, 2.5], "Lerner": {"moyenne": 1.50, "ecart_type": 0.40, "p85": 1.9, "max": 2.54, "n": 56},
         "Green2000": 1.5},
  notes="Lognormale reproduisant moyenne 1,10 s et P95 2,0 s. Avec ces paramètres : P(TPR ≤ 1,8 s) ≈ 0,92 et P(≤ 2,5 s) ≈ 0,985, ce qui situe les valeurs normatives françaises (1,8 s Cerema 2018 ; 2 s ICTAVRU/ACI) vers le 92e-95e centile, comme l'AASHTO (2,5 s ≈ 90e-95e centile, NCHRP 400 p. 3).",
  tirage={"facteur": "vigilance", "charge": -0.5, "groupe": "tpr"})

P("tpr.norme_fr_route", V, "Temps de perception-réaction conventionnel (distance d'arrêt, ralentissement)",
  "Norme de conception, routes et autoroutes françaises", "constante", {"valeur": 1.8}, "s",
  "calcul de distance d'arrêt et de ralentissement (vitesse V85)", "norme",
  src("CEREMA_VIS2018", "p. 11 (PDF 13) et p. 20 (PDF 22) ; repris par ARP 2022 p. 30 (PDF 32)"), "elevee",
  notes="Valeur de conception, pas une moyenne de comportement : sert à la validation (le modèle doit couvrir ≈ 90-95 % des conducteurs).",
  role="norme_validation")
P("tpr.norme_fr_vru_aci", V, "Temps de perception-réaction conventionnel (anciens guides)", "Norme de conception",
  "constante", {"valeur": 2.0}, "s", "voies rapides urbaines (ICTAVRU) ; carrefours interurbains V ≤ 100 km/h (ACI) ; VSA 70/90/110",
  "norme", src("ICTAVRU2009", "p. 32 (PDF 34) ; ACI 1998 p. 37 (PDF 41) ; VSA 90/110 2014 p. PDF 17"), "elevee", role="norme_validation")
P("tpr.norme_fr_urbain", V, "Temps de perception-réaction retenu en milieu urbain (ouvrages, traversées piétonnes)",
  "Norme de conception urbaine", "constante", {"valeur": 1.0}, "s",
  "« caractérise mieux l'état de vigilance de l'usager circulant en milieu urbain » ; exemple piéton : freinage 15 m à 50 km/h sur sec + 1 s",
  "norme", src("CERTU_CU2010", "p. PDF 146 (ouvrages) et p. PDF 74 (piétons)"), "elevee", role="norme_validation")
P("tpr.pedagogique", V, "Temps de réaction et décélération de la fiche de sécurité routière", "Message de prévention",
  "constante", {"temps_reaction": 1.0, "deceleration": 7.0}, "s ; m/s²", "distances d'arrêt 28 / 70 / 129 m à 50 / 90 / 130 km/h",
  "norme", src("BISONFUTE", "p. 1 (schéma)"), "moyenne", role="norme_validation")

# Modèle cinématique de Markkula (urgence) : option avancée
P("tpr.markkula.alphaB_yeux_sur_menace", V, "Instant de début de freinage d'urgence, conducteur regardant la menace : αB = (tB - t0,2)/(tC - t0,2)",
  "SHRP2 + 100-Car (voitures), 94 événements réels (accidents et quasi-accidents)", "normale", {"moyenne": 0.22, "ecart_type": 0.29},
  "-", "t0,2 = premier instant où l'inverse du temps à collision (looming τ⁻¹) dépasse 0,2 s⁻¹ ; tC = instant de collision sans freinage",
  "mesure", src("MARKKULA2016", "fig. 10 p. 15 du manuscrit (PDF 16)"), "moyenne",
  notes="Remplace un « temps de réaction » fixe pour les urgences : le freinage dépend de l'urgence cinématique. Camions/bus : N(0,27 ; 0,40), n=11.",
  role="modele_avance")
P("tpr.markkula.alphaB_yeux_hors_route", V, "Instant de début de freinage d'urgence, conducteur distrait (regard hors route)",
  "SHRP2 + 100-Car (voitures), 115 événements", "lognormale", {"mu_log": -1.40, "sigma_log": 0.71}, "-",
  "même définition ; regard hors route au moment où la menace apparaît", "mesure",
  src("MARKKULA2016", "fig. 10 p. 15 du manuscrit (PDF 16)"), "moyenne",
  notes="Camions/bus : lognormale(-0,51 ; 0,85), n=6. Utilisé par le profil « distrait ».", role="modele_avance")

P("tpr.markkula.kB", V, "Coefficient de la rampe de freinage d'urgence : jB = kB·τ⁻¹ (τ⁻¹ looming au début du freinage)",
  "SHRP2 + 100-Car, voitures, 225 événements (accidents et quasi-accidents)", "lognormale", {"mu_log": 1.23, "sigma_log": 0.62},
  "m/s² (|kB|)", "valeur absolue de kB ; rampe jB = kB·τ⁻¹ jusqu'à la décélération maximale a1", "mesure",
  src("MARKKULA2016", "fig. 10 p. 15 du manuscrit (PDF 16)"), "moyenne",
  notes="Camions/bus : lognormale(0,84 ; 0,71). Ajouté le 17/10/2026 (la v0.1 recopiait la loi dans le code du prototype). Plafond proposé par les auteurs « par exemple jB ≤ 8 m/s³ » (annexe B.3).",
  role="modele_avance")

# =========================================================================================
# 2. DÉCÉLÉRATIONS
# =========================================================================================
V = "decelerations"
P("dec.norme_ralentissement", V, "Décélération de manœuvre de ralentissement (confort)", "Norme de conception",
  "constante", {"valeur": 1.5}, "m/s²", "ralentissement avant un giratoire, un arrêt TC", "norme",
  src("CEREMA_VIS2018", "p. 20 (PDF 22) ; ARP 2022 p. 30 (PDF 32)"), "elevee", role="norme_validation")
P("dec.norme_arret_mouille", V, "Décélération moyenne conventionnelle en manœuvre d'arrêt (chaussée mouillée)",
  "Norme de conception", "constante", {"30_kmh": 0.46 * G, "50_kmh": 0.46 * G, "70_kmh": 0.44 * G, "sup_70_kmh": 0.41 * G}, "m/s²",
  "fractions de g : 0,46 à 30 ET 50 km/h (cellule fusionnée), 0,44 à 70 km/h, 0,41 au-delà de 70 km/h ; + malus en courbe mc(R) = 0,2 si R ≤ Rdn", "norme",
  src("CEREMA_VIS2018", "p. 11 (PDF 13), tableau « Décélération moyenne γv » lu sur rendu natif (relecture du 17/10/2026)"), "elevee",
  stats={"gamma_v_g": {"30": 0.46, "50": 0.46, "70": 0.44, "sup_70": 0.41},
         "controle_VSA90_110_2014_p16": {"30": 0.46, "50": 0.46, "70": 0.44, "90": 0.40, "110": 0.36}},
  notes="Correction du 17/10/2026 : la v0.1 décalait d'une colonne (0,44 g à 50 km/h, 0,41 g à 70 km/h) ; distances normatives corrigées 46,4 m à 50 km/h et 78,8 m à 70 km/h (1,8 s ; palier). Les valeurs à 30-70 km/h sont identiques dans le guide officiel VSA 90/110 (Cerema 2014, p. 16) ; la copie locale du guide 2018 est un miroir de cours (voir SOURCES.md).",
  role="norme_validation")
P("dec.norme_bus_debout", V, "Décélération d'arrêt avec passagers debout (conducteur de bus/car)", "Norme de conception",
  "constante", {"valeur": 0.205 * G}, "m/s²", "0,205 g", "norme", src("CEREMA_VIS2018", "p. 31 (PDF 33)"), "elevee",
  role="modulateur_profil")
P("dec.norme_bus_vsa70", V, "Décélération de confort pour personnes debout (visibilité TC sur AU70)", "Norme de conception",
  "constante", {"valeur": 2.0, "temps_reaction_distance_m": 40}, "m/s²", "70 km/h : 100 m de freinage + 40 m de réaction",
  "norme", src("VSA70_2013", "p. 65 (PDF 65)"), "moyenne", role="norme_validation")
P("dec.ite_confortable", V, "Décélération « raisonnablement confortable » (manuel ITE cité par NCHRP 400)",
  "Norme de conception (États-Unis)", "constante", {"valeur": 10 * 0.3048}, "m/s²", "10 ft/s² ; AASHTO « confortable » plus faible",
  "norme", src("NCHRP400", "p. 25 (PDF 35)"), "moyenne", role="norme_validation")

P("dec.p10_inattendu", V, "Décélération d'arrêt face à un obstacle inattendu : valeur atteinte ou dépassée par 90 % des conducteurs",
  "NCHRP 400, essais de freinage (45 conducteurs, 3 000 manœuvres)", "constante", {"valeur": 3.4}, "m/s²",
  "freinage d'arrêt ; « peut être atteinte sans perte de contrôle »", "mesure",
  src("NCHRP400", "p. 3 (PDF 13)"), "elevee", role="reference_validation")

ecd = lois.lognormale_depuis_moyenne_quantile(0.55 * G, 0.37 * G, 0.10)
ecd = dict(r4(ecd), q_max=0.99)   # borne haute ≈ 1,0 g : au-delà, physiquement exclu (pic mesuré 0,74 ± 0,09 g ; µ ≤ 1,1)
P("dec.urgence_equivalente", V, "Décélération constante équivalente d'un arrêt d'urgence (obstacle inattendu)",
  "NCHRP 400 étude 3 : n = 7 conducteurs dans leur propre véhicule sans ABS, chaussée sèche", "lognormale",
  ecd, "m/s²",
  "chaussée sèche, vitesse initiale 55 mph ; décélération moyenne sur toute la manœuvre", "estimation",
  src("NCHRP400", "p. 34 (PDF 44), tableaux 24-25 (étude 3, sans ABS) ; tableau 25 lu sur rendu natif"), "faible",
  stats={"moyenne_g": 0.55, "ecart_type_g_tab24": 0.07, "n_conducteurs": 7,
         "percentiles_depassement_g_tab25": {"75": 0.43, "90": 0.37, "95": 0.32, "99": 0.24},
         "max_Gx_moyen_g": 0.74, "max_Gx_ecart_type_g": 0.09,
         "etude2_vehicule_essai_ABS": {"moyenne_g": 0.63, "max_Gx_g": 0.91, "p90_depassement_g": 0.42},
         "p3_dixieme_centile_ms2": 3.4},
  notes=("Correction du 17/10/2026 : la v0.1 utilisait N(0,55 ; 0,07 g), écart-type du tab. 24 qui contredit les centiles du tab. 25 "
         "de la même page (avec cette normale, 99,6 % des tirages dépassaient 0,37 g au lieu de 90 %). Loi retenue : lognormale de "
         "moyenne 0,55 g (tab. 24-25) dont le 10e centile vaut 0,37 g (seuil dépassé par 90 % des conducteurs, tab. 25). "
         "Troncature au 99e centile (≈ 1,0 g) : la lognormale n'est pas bornée, alors que le pic moyen mesuré vaut 0,74 ± 0,09 g et que µ ≤ 1,1. "
         "Contrôle des centiles 1/5/25 par valider.py (T2b). Les centiles du tab. 25 portent sur les manœuvres, pas sur des moyennes "
         "par conducteur. NCHRP 400 p. 3 : 3,4 m/s² au 10e centile (45 conducteurs, 3 000 manœuvres, toutes études). Le pic "
         "(0,74 g) n'est atteint qu'en fin de manœuvre (p. 36). Étude 1 (freinage attendu, piste) : 0,56 g à 40 mph, 0,60 g à 55 mph (p. 29)."),
  tirage={"facteur": "style", "charge": 0.2, "groupe": "dec_urgence"})

P("dec.urgence_max_markkula", V, "Décélération maximale en situation d'urgence réelle (accidents)",
  "SHRP2 + 100-Car, voitures, 31 accidents par l'arrière", "normale_tronquee", {"moyenne": 6.68, "ecart_type": 1.69, "min": 2.0, "max": 10.0}, "m/s² (valeur absolue)",
  "valeur maximale du freinage d'urgence (a1 = -6,68 m/s² dans la source, signe négatif = décélération) ; troncature 2-10 m/s² (hypothèse)", "mesure",
  src("MARKKULA2016", "fig. 10 p. 15 du manuscrit (PDF 16)"), "moyenne",
  stats={"moyenne": -6.68, "ecart_type": 1.69, "n": 31},
  notes="Camions/bus : N(-4,70 ; 1,44), n=17. Rampe de freinage : jB = kB·τB⁻¹ avec |kB| lognormale(1,23 ; 0,62) m/s² (voitures, n=225) ; camions/bus lognormale(0,84 ; 0,71).",
  role="parametre_conducteur", tirage={"facteur": "style", "charge": 0.2, "groupe": "dec_urgence"})

# GEV de type Fréchet (k > 0) : queue haute non bornée (b jusqu'à 12 m/s² sur 20 000 tirages en v0.1).
# Troncature explicite au 99e centile (correction du 17/10/2026) : Huang 2018 décrit des extrêmes habituels
# (2,5e / 97,5e centiles par conducteur) ; au-delà de P99, la loi ajustée sort du domaine observé et de la capacité
# des véhicules (a_max VP ≤ 5,9 m/s², volet 01). La coupure retire 1 % des tirages (documenté dans « notes »).
Q_MAX_GEV = 0.99
gev_dec_loc = {"k": 0.1649, "sigma": 0.3289, "mu": 2.3865, "q_max": Q_MAX_GEV}
gev_dec_aut = {"k": 0.1669, "sigma": 0.4722, "mu": 2.4461, "q_max": Q_MAX_GEV}
NOTE_TRONC = (" Troncature au 99e centile de la GEV publiée (q_max = 0,99, correction du 17/10/2026) : la GEV de type Fréchet "
              "n'est pas bornée et donnait des valeurs au-delà de la capacité physique ; moyenne contrôlée par T2.")
P("dec.max_courante_urbain", V, "Décélération « extrême » habituelle d'un conducteur en suivi (2,5e centile de ses freinages), routes locales",
  "SPMD Ann Arbor (Michigan), conducteurs particuliers, 85 656 événements de suivi sur routes locales", "gev", gev_dec_loc, "m/s²",
  "valeur absolue ; suivi de véhicule, vitesse > 10 m/s", "mesure", src("HUANG2018", "p. 3, tableau III ; moyenne 2,64 m/s² p. 4"), "moyenne",
  stats={"moyenne": 2.64}, notes="Convention GEV : k = forme (scipy c = -k). Contrôle : la moyenne recalculée vaut 2,64 m/s² sans troncature." + NOTE_TRONC,
  tirage={"facteur": "style", "charge": 0.4, "groupe": "dec_courante"})
P("dec.max_courante_autoroute", V, "Décélération « extrême » habituelle d'un conducteur en suivi, autoroutes",
  "SPMD Ann Arbor, 75 353 événements de suivi sur autoroutes", "gev", gev_dec_aut, "m/s²", "valeur absolue",
  "mesure", src("HUANG2018", "p. 3, tableau III ; moyenne 2,81 m/s² p. 4"), "moyenne", stats={"moyenne": 2.81},
  notes="GEV de Huang 2018." + NOTE_TRONC,
  role="parametre_conducteur", tirage={"facteur": "style", "charge": 0.4, "groupe": "dec_courante"})

P("dec.percentiles_bosetti", V, "Distribution des décélérations de freinage (toutes conduites)",
  "24 conducteurs italiens, 48 trajets, ~35 h (projet interactIVe, CRF)", "constante",
  {"tous": {"min": -8.87, "p5": -1.61, "p25": -0.44, "p50": -0.26, "p75": -0.09, "p95": -0.01},
   "moins_40kmh": {"min": -8.87, "p5": -2.22, "p25": -1.14, "p50": -0.47, "p75": -0.11, "p95": -0.02},
   "40_70kmh": {"min": -4.77, "p5": -1.72, "p25": -0.72, "p50": -0.32, "p75": -0.18, "p95": -0.03},
   "plus_70kmh": {"min": -4.90, "p5": -0.54, "p25": -0.32, "p50": -0.16, "p75": -0.06, "p95": -0.01}},
  "m/s²", "trajet mixte urbain / extra-urbain / autoroute", "mesure", src("BOSETTI2014", "p. 163, tableau 4 (PDF 7)"),
  "moyenne", notes="Sert à valider la distribution simulée des décélérations (forme, queue).", role="reference_validation")

ln_c = lois.lognormale_depuis_quantiles(3.09, 0.05, 5.27, 0.95)
P("dec.max_conducteur_bosetti", V, "Décélération maximale de freinage propre à un conducteur (sommet c du losange g-g)",
  "24 conducteurs italiens, 48 trajets", "lognormale", r4(ln_c), "m/s²", "valeur absolue", "estimation",
  src("BOSETTI2014", "p. 164, tableau 5 (PDF 8)"), "moyenne", stats={"p5": 3.09, "p50": 3.86, "p95": 5.27},
  notes="Lognormale ajustée sur P5 et P95 ; médiane recalculée 4,03 m/s² (publiée 3,86).", role="reference_validation")

# =========================================================================================
# 3. ACCÉLÉRATIONS, DÉMARRAGE
# =========================================================================================
V = "accelerations"
ln_b = lois.lognormale_depuis_quantiles(2.42, 0.05, 4.12, 0.95)
P("acc.max_conducteur_bosetti", V, "Accélération longitudinale maximale propre à un conducteur (sommet b du losange g-g)",
  "24 conducteurs italiens, 48 trajets", "lognormale", r4(ln_b), "m/s²", "accélérateur seul, toutes vitesses", "estimation",
  src("BOSETTI2014", "p. 164, tableau 5 (PDF 8)"), "moyenne", stats={"p5": 2.42, "p50": 3.10, "p95": 4.12},
  notes="Lognormale ajustée sur P5 et P95 (médiane recalculée 3,16). Le facteur « conducteur » et l'expérience sont significatifs (ANOVA, tableau 6) ; le sexe ne l'est pas.",
  tirage={"facteur": "style", "charge": 0.5, "groupe": "acc"})
P("acc.demarrage_pic", V, "Pic d'accélération au démarrage arrêté (feu vert, départ)",
  "FKFS Stuttgart : > 2 000 démarrages instrumentés (moteurs thermiques)", "normale_tronquee",
  {"moyenne": 2.1, "ecart_type": 0.5, "min": 1.0, "max": 4.0}, "m/s²",
  "démarrage après ≥ 2 s d'arrêt ; 1 m/s atteint en 0,8 s en moyenne, pic vers 2,3 s", "estimation",
  src("SALLES2020", "p. 14 (texte) et fig. 9 p. 15 (lecture graphique : pic moyen ≈ 2,1 m/s² boîte manuelle et automatique ; écart-type ≈ 0,5 m/s²)"),
  "moyenne", stats={"temps_1ms": 0.8, "temps_pic": 2.3, "ecart_type_courbes": 0.5},
  notes="Moyenne lue sur figure (± 0,1) ; l'écart-type entre véhicules (± 0,5 m/s²) est donné dans le texte pour les courbes d'accélération.",
  tirage={"facteur": "style", "charge": 0.5, "groupe": "acc"})
P("acc.demarrage_file", V, "Pic moyen d'accélération selon le rang dans la file au vert",
  "Mesures par drone, 2 carrefours à feux de Stuttgart, 3 h", "constante",
  {"rang1": 2.67, "rang2": 2.28, "rang3": 2.02, "rang4_9": 1.9, "ecart_type": [0.4, 0.65]}, "m/s²",
  "lecture de la fig. 8a (± 0,05)", "mesure", src("SALLES2020", "fig. 8 p. 15"), "moyenne",
  notes="Le pic décroît jusqu'au 4e véhicule puis se stabilise, comme les temps intervéhiculaires (fig. 10).",
  role="reference_validation")
gev_acc_loc = {"k": 0.1426, "sigma": 0.1930, "mu": 1.0457, "q_max": Q_MAX_GEV}
gev_acc_aut = {"k": 0.3711, "sigma": 0.1628, "mu": 0.5314, "q_max": Q_MAX_GEV}
P("acc.max_suivi_urbain", V, "Accélération « extrême » habituelle en suivi (97,5e centile du conducteur), routes locales",
  "SPMD Ann Arbor, routes locales", "gev", gev_acc_loc, "m/s²", "suivi de véhicule, vitesse > 10 m/s", "mesure",
  src("HUANG2018", "p. 3, tableau III ; moyenne 1,19 m/s² p. 4"), "moyenne", stats={"moyenne": 1.19},
  notes="GEV de Huang 2018." + NOTE_TRONC,
  tirage={"facteur": "style", "charge": 0.5, "groupe": "acc"})
P("acc.max_suivi_autoroute", V, "Accélération « extrême » habituelle en suivi, autoroutes", "SPMD Ann Arbor, autoroutes",
  "gev", gev_acc_aut, "m/s²", "suivi de véhicule", "mesure", src("HUANG2018", "p. 3, tableau III ; moyenne 0,72 m/s² p. 4"),
  "moyenne", stats={"moyenne": 0.72},
  notes="GEV de Huang 2018 (k = 0,37 : queue la plus lourde ; sans troncature, P99,9 = 5,2 m/s² et maximum 14,6 m/s² sur 20 000 tirages)." + NOTE_TRONC,
  tirage={"facteur": "style", "charge": 0.5, "groupe": "acc"})
P("acc.percentiles_bosetti", V, "Distribution des accélérations longitudinales selon la vitesse", "24 conducteurs italiens",
  "constante", {"0_40kmh": {"p5": -1.79, "p50": 0.04, "p95": 1.49, "max": 4.43},
                "40_70kmh": {"p5": -1.24, "p50": 0.11, "p95": 1.13, "max": 3.25},
                "plus_70kmh": {"p5": -0.38, "p50": 0.09, "p95": 0.55, "max": 2.06},
                "forte_courbure": {"p5": -1.63, "p95": 1.38}, "faible_courbure": {"p5": -0.38, "p95": 0.56}},
  "m/s²", "accélération positive et négative mêlées", "mesure", src("BOSETTI2014", "p. 163, tableau 4 (PDF 7)"), "moyenne",
  notes="L'accélération maximale observée baisse avec la vitesse : à utiliser comme enveloppe a_max(v).",
  role="reference_validation")
P("acc.jerk_confort", V, "Jerk (variation d'accélération) à ne pas dépasser pour une conduite confortable",
  "Recommandation de modélisation (Treiber & Kesting 2013, cité)", "constante", {"valeur": 1.5}, "m/s³",
  "conduite normale hors urgence", "estimation", src("SALLES2020", "p. 3"), "faible", role="contrainte_modele",
  notes="Recommandation d'auteur (Treiber et Kesting 2013, citée par Salles 2020 p. 3), pas une norme ni une mesure (requalifiée le 17/10/2026). Le prototype montre qu'elle est incompatible avec les démarrages mesurés (1 m/s en 0,8 s exige au moins 3 m/s³).")

# =========================================================================================
# 4. VITESSES PRATIQUÉES (vitesse désirée en circulation libre)
# =========================================================================================
V = "vitesses"


def onisr_fit(vma, moy, parts):
    return lois.normale_sigma_depuis_depassements(moy, [vma + 0.5 + 10 * i for i in range(len(parts))], parts)


reseaux = [
    # id, VMA, moyenne 2023 jour, parts 2023 jour [>VMA, >VMA+10], page 2023, moyenne 2019, parts 2019, nuit (moy 2023 si dispo), conf
    ("artere_centre_ville_50", 50, 41.2, [0.15, 0.01], 45.4, 43, [0.20, 0.04, 0.01], "artères de centre-ville d'agglomération moyenne"),
    ("traversee_petite_agglo_50", 50, 47.0, [0.37, 0.07], None, 49, [0.39, 0.13, 0.04], "routes en traversée de petite agglomération"),
    ("entree_sortie_agglo_50", 50, 50.5, [0.38, 0.21], None, 48, [0.38, 0.10, 0.02], "entrées et sorties d'agglomération moyenne"),
    ("route_2_3_voies_80", 80, 76.8, [0.32, 0.09], 79.6, 78, [0.34, 0.11, 0.04], "routes à 2 ou 3 voies hors agglomération (VMA 80, parfois 90)"),
    ("route_2x2_110", 110, 103.0, [0.26, 0.05], None, 104, [0.27, 0.07, 0.02], "routes à 2x2 voies (VMA 110)"),
    ("autoroute_degagement_110", 110, 100.0, [0.20, 0.06], None, 103, [0.27, 0.07, 0.02], "autoroutes de dégagement (VMA 110)"),
    ("autoroute_liaison_130", 130, 114.5, [0.14, 0.02], 114.9, 119, [0.20, 0.04, 0.01], "autoroutes de liaison (VMA 130)"),
]
nuit_2019 = {"artere_centre_ville_50": (43, 49), "traversee_petite_agglo_50": (49, 58), "entree_sortie_agglo_50": (48, 53),
             "route_2_3_voies_80": (79, 89), "autoroute_degagement_110": (106, 110), "autoroute_liaison_130": (114, 122)}
for rid, vma, m23, p23, n23, m19, p19, lib in reseaux:
    f23 = onisr_fit(vma, m23, p23)
    f19 = onisr_fit(vma, m19, p19)
    nature_note = ""
    if rid == "entree_sortie_agglo_50":
        # distribution 2023 bimodale (bosse 70-80 km/h) : ajustement normal 2019, moyenne 2023
        sig = f19["ecart_type"]
        par = {"moyenne": m23, "ecart_type": round(sig, 2)}
        nature_note = " La distribution 2023 est bimodale (bosse à 70-80 km/h, p. 31) : écart-type ajusté sur 2019 (unimodale) et moyenne 2023 ; résidu 2023 au seuil VMA = +12 points (loi normale inadaptée)."
    else:
        par = {"moyenne": m23, "ecart_type": round(f23["ecart_type"], 2)}
    stats_pub = {"2023_jour": {"moyenne": m23, "part_sup_VMA": p23[0], "part_sup_VMA+10": p23[1]},
                 "2019_jour": {"moyenne": m19, "parts_sup_VMA_+10_+20": p19}, "residus_ajustement_2023": f23["residus_parts"],
                 "ecart_type_ajuste_2019": round(f19["ecart_type"], 2)}
    if n23:
        stats_pub["2023_nuit"] = {"moyenne": n23}
    if rid in nuit_2019:
        stats_pub["2019_jour_nuit_meme_panel"] = nuit_2019[rid]
    P(f"vit.{rid}", V, f"Vitesse pratiquée en circulation libre, véhicules de tourisme, de jour - {lib}",
      "VT (longueur 2 à 6 m) en vitesse libre, panel ONISR métropole ; 2023 : radars automatiques 7 jours, 9h30-16h30",
      "normale", par, "km/h",
      f"VMA {vma} km/h ; section droite, plane, loin des carrefours, feux et radars ; hors pointe ; jour",
      "estimation", src("ONISR2023", "p. 5 et 7 (moyennes, taux de dépassement) ; ONISR 2019 p. 3-18 pour 2019"), "elevee",
      stats=stats_pub,
      notes=("Loi normale : moyenne publiée ; écart-type ajusté par moindres carrés sur les taux de dépassement de la VMA et de VMA+10 (2023)."
             + nature_note + f" Facteur de vitesse (vitesse / VMA) : moyenne {par['moyenne']/vma:.3f}, écart-type {par['ecart_type']/vma:.3f}."),
      tirage={"facteur": "style", "charge": 0.6, "groupe": "vitesse", "vma_kmh": vma})

# histogrammes lus sur les figures (contrôle de forme)
P("vit.histo.artere_centre_ville_50.2019", V, "Distribution des vitesses VT de jour, artères de centre-ville (VMA 50), 2019",
  "4 826 VT observés (2019)", "empirique_classes",
  {"bornes": [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85],
   "frequences": [9.84, 11.29, 16.30, 23.49, 18.69, 10.63, 5.31, 2.54, 1.03, 0.60, 0.18, 0.12]}, "km/h ; %",
  "classes de 5 km/h ; classes ouvertes « ≤ 30 » et « ≥ 81 » fermées à ± 5 km/h (hypothèse)", "mesure",
  src("ONISR2019", "p. 18, figure « Distribution des vitesses de jour sur les artères » (lecture des pixels, ± 0,3 point)"),
  "moyenne", notes="Valeurs extraites des pixels de la courbe VT (les deux premières classes, masquées par la courbe VU confondue, sont celles de VU). Contrôles : >50 km/h = 20,0 % (publié 20 %), >60 = 4,5 % (publié 4 %).",
  role="reference_validation")
P("vit.histo.artere_centre_ville_50.2023_jour", V, "Distribution des vitesses VT de jour, artères de centre-ville (VMA 50), 2023",
  "214 430 VT de jour (2023)", "empirique_classes",
  {"bornes": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
   "frequences": [0.0, 0.28, 2.0, 6.21, 12.03, 19.78, 24.19, 19.92, 10.18, 3.84, 1.0, 0.2]}, "km/h ; %", "classes de 5 km/h",
  "mesure", src("ONISR2023", "p. 35, figure de distribution (image native 1582 px, lecture des pixels ± 0,3 point ; classes 20-25, 60-65, 65-70 lues à l'œil)"),
  "moyenne", notes="Contrôle : >50 km/h = 15,2 % (publié 15 %).", role="reference_validation")
P("vit.histo.artere_centre_ville_50.2023_nuit", V, "Distribution des vitesses VT de nuit (23h-5h), artères de centre-ville (VMA 50), 2023",
  "14 552 VT de nuit (2023)", "empirique_classes",
  {"bornes": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
   "frequences": [0.0, 0.11, 0.81, 3.16, 6.79, 12.03, 20.26, 25.30, 17.94, 9.36, 3.30, 0.6]}, "km/h ; %", "classes de 5 km/h",
  "mesure", src("ONISR2023", "p. 35, figure de distribution (lecture des pixels ; dernière classe à l'œil)"), "moyenne",
  notes="Contrôle : >50 km/h = 31,2 % (publié 31 %).", role="reference_validation")
P("vit.histo.route_2_3_voies_80.2019", V, "Distribution des vitesses VT de jour, routes à 2 ou 3 voies (VMA 80), 2019",
  "9 013 VT (2019)", "empirique_classes",
  {"bornes": [45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125],
   "frequences": [1.10, 1.41, 2.58, 5.34, 12.03, 20.98, 22.30, 14.76, 7.73, 4.52, 2.83, 1.76, 1.13, 0.69, 0.31, 0.38]},
  "km/h ; %", "classes de 5 km/h", "mesure", src("ONISR2019", "p. 12 (lecture des pixels)"), "moyenne",
  notes="Contrôles : >80 = 33,9 % (publié 34 %), >90 = 11,6 % (11 %), >100 = 4,3 % (4 %). Pic marqué juste sous la VMA : une normale sous-estime le taux >VMA (résidu 2019 = 7,6 points).",
  role="reference_validation")
P("vit.histo.traversee_petite_agglo_50.2019", V, "Distribution des vitesses VT de jour, traversées de petite agglomération (VMA 50), 2019",
  "4 428 VT (2019)", "empirique_classes",
  {"bornes": [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85],
   "frequences": [1.05, 4.17, 10.56, 21.66, 23.47, 16.29, 9.11, 6.13, 3.45, 1.92, 1.1, 0.8]}, "km/h ; %", "classes de 5 km/h",
  "mesure", src("ONISR2019", "p. 14 (lecture des pixels ; 2 dernières classes à l'œil, confondues avec VU)"), "moyenne",
  notes="Contrôles : >50 = 38,8 % (publié 39 %), >60 = 13,4 % (13 %).", role="reference_validation")
P("vit.histo.entree_sortie_agglo_50.2019", V, "Distribution des vitesses VT de jour, entrées-sorties d'agglomération moyenne (VMA 50), 2019",
  "3 934 VT (2019)", "empirique_classes",
  {"bornes": [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85],
   "frequences": [4.02, 6.22, 10.75, 18.93, 21.44, 17.69, 10.33, 5.68, 2.63, 0.97, 0.51, 0.21]}, "km/h ; %", "classes de 5 km/h",
  "mesure", src("ONISR2019", "p. 16 (lecture des pixels ; 1re classe = VU confondue)"), "moyenne",
  notes="Contrôles : >50 = 38,0 % (publié 38 %), >60 = 10,0 % (10 %).", role="reference_validation")
P("vit.histo.autoroute_liaison_130.2019", V, "Distribution des vitesses VT de jour, autoroutes de liaison (VMA 130), 2019",
  "22 555 VT (2019)", "empirique_classes",
  {"bornes": [70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155],
   "frequences": [0.28, 0.42, 1.08, 1.68, 2.84, 3.90, 5.90, 8.92, 10.64, 12.65, 16.06, 15.56, 10.93, 4.80, 1.89, 1.28, 0.77]},
  "km/h ; %", "classes de 5 km/h", "mesure", src("ONISR2019", "p. 6 (lecture des pixels, recalage de l'axe sur la grille 5-40 %)"),
  "moyenne", notes="Contrôles : >130 = 19,7 % (publié 20 %), >140 = 3,9 % (4 %). Asymétrie à gauche (files lentes).",
  role="reference_validation")

P("vit.poids_lourds", V, "Vitesse pratiquée par les poids lourds (> 9 m), de jour et de nuit, 2023",
  "PL du panel ONISR (radars automatiques)", "constante",
  {"autoroute_liaison_VMA90": {"jour": 84.2, "nuit": 85.5, "respect_jour": 0.88, "respect_nuit": 0.83},
   "route_2_3_voies_VMA80": {"jour": 73.8, "nuit": 77.9, "respect_jour": 0.71, "respect_nuit": 0.54},
   "artere_centre_ville_VMA50": {"jour": 36.0, "respect_jour": 0.96}}, "km/h", "VMA des PL (90 sur autoroute, 80 hors agglomération)",
  "mesure", src("ONISR2023", "p. 7 (tableau des indicateurs clés PL) et p. 34"), "elevee",
  notes="Profil « conducteur PL » ; 2019 : PL 4 essieux et plus 88-89 km/h sur autoroutes de liaison, 33 % > 90 km/h (ONISR 2019 p. 5).",
  role="modulateur_profil")
P("vit.ecart_jour_nuit", V, "Écart de vitesse moyenne VT nuit - jour (même panel de points)", "VT, panel ONISR",
  "constante", {"2019": {"autoroute_liaison_130": 8, "autoroute_degagement_110": 4, "route_2_3_voies_80": 10,
                         "traversee_petite_agglo_50": 9, "entree_sortie_agglo_50": 5, "artere_centre_ville_50": 6},
                "2023": {"autoroute_liaison_130": 0.4, "route_2_3_voies_80": 2.8, "artere_centre_ville_50": 4.2}},
  "km/h", "nuit 22h-3h (2019, mesures visibles) ; 23h-5h (2023, radars automatiques)", "mesure",
  src("ONISR2019", "p. 19 (tableau jour/nuit) ; ONISR 2023 p. 7 (tableau des indicateurs clés)"), "elevee",
  notes="2023 : jour/nuit 114,5/114,9 (autoroutes de liaison), 76,8/79,6 (2-3 voies), 41,2/45,4 (artères). Le dispositif a changé en 2020 (radars discrets, panel 135 points) : les écarts 2023 sont plus fiables.",
  role="modulateur_contexte")
P("vit.week_end", V, "Écart de vitesse VT week-end - jours ouvrés, de jour, artères de centre-ville", "VT, ONISR 2023",
  "constante", {"valeur": 1.3}, "km/h", "jour ; la tendance s'inverse la nuit (-0,3 km/h)", "mesure",
  src("ONISR2023", "p. 34"), "moyenne", notes="Vias 2021 : vitesses plus élevées le week-end sur 30, 50 et 70 km/h (p. 10).",
  role="modulateur_contexte")

P("vit.route_bidirectionnelle_80_vl_24h", V, "Vitesse des véhicules légers, routes bidirectionnelles à 2 voies limitées à 80 km/h, 24 h/24",
  "Observatoire VMA80 du Cerema, 143 millions de passages (juin 2018 - déc. 2019), capteurs invisibles", "normale",
  {"moyenne": 83.5, "ecart_type": round(lois.normale_depuis_v15_v85(0, 20), 2)}, "km/h",
  "tous véhicules légers, jour et nuit, VMA 80 (après juillet 2018)", "estimation",
  src("CEREMA_V80_2020", "p. 32-35 (PDF 34-37)"), "elevee",
  stats={"moyenne_VL_apres": 83.5, "moyenne_VL_avant": 87.0, "V85_moins_V15_tous": [21, 20], "part_sup_80_dec2019": 0.58,
         "part_sup_90_dec2019": 0.23, "critere_vehicule_libre_TIV_s": 5},
  notes="Écart-type déduit de V85 - V15 = 20 km/h (loi assimilée normale par le Cerema, note 6 p. 32). Les capteurs invisibles et la nuit donnent des vitesses plus élevées que l'ONISR (p. 4 ONISR 2019).",
  role="reference_validation")

vias = [("zone_30_be", 30, 38.3, 47.2, 0.776, "zones 30 et abords d'école sans dispositif ralentisseur (Belgique)"),
        ("urbain_50_be", 50, 51.5, 59.7, 0.513, "routes limitées à 50 km/h, en agglomération (Belgique)"),
        ("route_70_be", 70, 69.2, 78.1, 0.416, "routes limitées à 70 km/h (Belgique)"),
        ("route_90_be", 90, 93.2, 106.1, 0.543, "routes limitées à 90 km/h (1x1 : 81,5 ; 2x2 : 97 km/h)"),
        ("autoroute_120_be", 120, 119.1, 130.9, 0.437, "autoroutes limitées à 120 km/h (Belgique)")]
for rid, vma, m, v85, ptrop, lib in vias:
    par = lois.normale_depuis_v85(m, v85)
    P(f"vit.{rid}", V, f"Vitesse en circulation libre des voitures - {lib}",
      "Voitures (2,5-8 m) en vitesse libre (TIV > 5 s à la vitesse limite), 215 sites, 3,8 millions de voitures, sept.-déc. 2021, 24 h/24",
      "normale", {"moyenne": m, "ecart_type": round(par["ecart_type"], 2)}, "km/h", f"VMA {vma} km/h ; pondéré par les véhicules-km",
      "estimation", src("VIAS2021", "p. 9 (tableau des indicateurs) et p. 21 (critère de vitesse libre)"), "elevee",
      stats={"moyenne": m, "V85": v85, "part_au_dessus_limite": ptrop},
      notes="Écart-type = (V85 - moyenne)/1,036 (hypothèse normale). Données belges : à utiliser pour les zones 30 faute de mesure française publiée équivalente.",
      tirage={"facteur": "style", "charge": 0.6, "groupe": "vitesse", "vma_kmh": vma} if rid == "zone_30_be" else None,
      role="parametre_conducteur" if rid == "zone_30_be" else "reference_validation")
P("vit.zone_30_bruxelles", V, "Vitesse en zone 30 à Bruxelles, sans et avec dispositif ralentisseur", "Voitures en vitesse libre, Région bruxelloise 2021",
  "normale", {"sans_dispositif": {"moyenne": 33.3, "ecart_type": round(lois.normale_depuis_v85(33.3, 40.8)["ecart_type"], 2)},
              "avec_dispositif": {"moyenne": 27.6, "ecart_type": round(lois.normale_depuis_v85(27.6, 34.3)["ecart_type"], 2)}},
  "km/h", "mesure à 10-20 m après le dispositif (chicane, coussin, plateau, casse-vitesse…)", "estimation",
  src("VIAS2021", "p. 39-40 (PDF 39-40) et p. 19 (position de mesure)"), "moyenne",
  stats={"sans": {"moyenne": 33.3, "V85": 40.8}, "avec": {"moyenne": 27.6, "V85": 34.3}},
  notes="En Flandre et en Wallonie, pas de différence significative avec / sans dispositif (p. 10).", role="reference_validation")
P("vit.contexte_grenoble", V, "Contexte local : « Métropole apaisée » (30 km/h par défaut)", "Grenoble-Alpes Métropole",
  "constante", {"communes_adherentes": 43, "part_lineaire_agglo_30": 0.82}, "-",
  "30 km/h règle et 50 km/h exception depuis 2016 ; rétablissement de la priorité à droite ; suppression de carrefours à feux",
  "mesure", src("GAM_JTR2018", "diapositives 5, 6, 13-15"), "moyenne",
  notes="Aucune mesure de vitesse chiffrée dans ce document ; évaluation Cerema « baisse limitée de la vitesse » (diapositive 15).",
  role="contexte")

# =========================================================================================
# 5. VITESSE EN COURBE ET ACCÉLÉRATION LATÉRALE
# =========================================================================================
V = "courbes"
P("courbe.v85_setra", V, "Vitesse V85 en courbe (routes bidirectionnelles et artères interurbaines) : V85 = Vlim / (1 + 346 / R^1,5)",
  "Relation géométrie-vitesse des guides Sétra/Cerema (usagers libres)", "fonction",
  {"expression": "V85_kmh = Vlim / (1 + 346 / R_m**1.5)", "Vlim_kmh": {"2x2_voies": 120, "2_voies_6_7m_ou_3_voies": 102, "2_voies_5m": 92},
   "rampe": "V85 = Vlim - 0,31 p² (p en %)"}, "km/h", "rayon R en m ; écrêtée à la VMA (sauf carrefours)", "norme",
  src("CEREMA_VIS2018", "p. 8 (PDF 10), figures 1 et 2 ; ACI 1998 PDF 127"), "elevee",
  notes="Attribution des trois courbes vérifiée sur la figure 1 rendue à taille native (bleu 2x2 = 120, orange 2 voies 6-7 m ou 3 voies = 102, vert 2 voies 5 m = 92). Relation empirique adoptée comme norme : sert à la validation et au mode « rase campagne ».",
  role="relation")
ln_a = lois.lognormale_depuis_quantiles(3.66, 0.05, 5.53, 0.95)
P("courbe.alat_max_conducteur", V, "Accélération latérale maximale propre à un conducteur (sommet a du losange g-g)",
  "24 conducteurs italiens, 48 trajets (urbain, extra-urbain, autoroute)", "lognormale", r4(ln_a), "m/s²",
  "valeur absolue, routes de forte courbure surtout", "estimation", src("BOSETTI2014", "p. 164, tableau 5 (PDF 8)"), "moyenne",
  stats={"p5": 3.66, "p50": 4.49, "p95": 5.53},
  notes="Lognormale ajustée sur P5/P95 (médiane recalculée 4,50). ANOVA : effet conducteur et expérience significatifs, sexe non (tableau 6).",
  tirage={"facteur": "style", "charge": 0.6, "groupe": "courbe"})
P("courbe.enveloppe_alat", V, "Enveloppe de l'accélération latérale acceptée selon la vitesse (critère de Levinson modifié)",
  "Mêmes données", "fonction", {"expression": "a_lat = a0 / sqrt((1 - v/v0)**2 + 2*(v/v0)**2)", "a0": 5.22, "v0": 14.84},
  "m/s² (v en m/s)", "enveloppe des observations ; Levinson : a = (k/v)², k = 36 m^1,5/s² (conducteur moyen), 42 (85e centile), plafond 0,4 g",
  "mesure", src("BOSETTI2014", "p. 159-160, éq. 1 (PDF 3-4)"), "moyenne",
  notes="Les données de Bosetti et Battelle plafonnent vers 4 m/s² à basse vitesse ; Reymond (7-8 m/s²) jugé non conforme (p. 161).",
  role="relation")
P("courbe.alpha_deux_tiers", V, "Loi des deux tiers : v = α ρ^(-1/3) (ρ courbure, 1/m) pour les manœuvres les plus rapides",
  "24 conducteurs italiens ; α par trajet = 0,999e quantile de v ρ^(1/3) en forte courbure", "normale",
  {"moyenne": round((3.06 + 3.60) / 2, 3), "ecart_type": round((3.60 - 3.06) / (2 * lois.Z(0.95)), 3)}, "m^(2/3)/s",
  "vitesse en m/s ; forte courbure (R < 300 m)", "estimation", src("BOSETTI2014", "p. 162 (α = 3,70 global) et tableau 5 p. 164 (P5 3,06 ; P50 3,34 ; P95 3,60)"),
  "moyenne", stats={"alpha_global_q999": 3.70, "p5": 3.06, "p50": 3.34, "p95": 3.60},
  notes="Normale ajustée sur P5/P95. Borne haute de la vitesse en courbe : v_max(R) = α R^(1/3). Ex. R = 50 m : 3,34·3,68 = 12,3 m/s (44 km/h).",
  tirage={"facteur": "style", "charge": 0.6, "groupe": "courbe"})
P("courbe.vitesse_conventionnelle_cfts", V, "Vitesse praticable conventionnelle selon le rayon (seuil de sécurité, dévers 5 %)",
  "Norme VSA 90/110", "constante", {"R_m": [40, 60], "V_kmh": [44, 51]}, "km/h",
  "VR = sqrt(R g (cfts + d)) ; d = 0,05 ; frottement transversal au seuil de sécurité", "norme",
  src("VSA90_2014", "p. 68 (PDF 70) ; formule VSA70 2013 p. 56"), "elevee",
  notes=("Limite de sécurité, au-dessus du comportement habituel : sert de garde-fou au modèle de courbe. Seules les deux valeurs "
         "utilisées par le modèle (R = 40 et 60 m) sont reprises : le document porte « Copie, reproduction et diffusion, même "
         "partielles, interdites sans l'accord explicite du Cerema » (correction du 17/10/2026 ; la v0.1 recopiait la table entière)."),
  role="norme_validation")
P("courbe.giratoire", V, "Vitesse de franchissement d'un giratoire urbain", "Guide Certu", "constante", {"valeur_max_typique": 30},
  "km/h", "« moins de 30 km/h en général »", "norme", src("CERTU_GIR1999", "p. PDF 9"), "moyenne", role="norme_validation")
P("courbe.bus_alat", V, "Accélération transversale maximale admissible pour personnes debout (bus)", "Norme VSA70",
  "constante", {"valeur": 1.0}, "m/s²", "confort et sécurité des passagers debout", "norme", src("VSA70_2013", "p. 65 (PDF 65)"),
  "moyenne", role="modulateur_profil")

# =========================================================================================
# 6. TEMPS INTERVÉHICULAIRES ET DISTANCES EN FILE
# =========================================================================================
V = "temps_intervehiculaires"
P("tiv.norme_fr", V, "Distance de sécurité réglementaire", "Code de la route art. R412-12", "constante",
  {"tiv_min_s": 2.0, "hors_agglo_PL_sup_3_5t_et_7m_m": 50, "autoroute_regle_pratique_m": 90}, "s ; m",
  "« au moins 2 secondes » ; 50 m entre PL > 3,5 t et > 7 m hors agglomération ; 2 traits de BAU ≈ 90 m",
  "norme", src("BISONFUTE", "p. 1 et 3"), "elevee", role="norme_validation")
P("tiv.critere_libre", V, "Seuil de véhicule « libre » (vitesse non contrainte)", "Convention d'observation", "constante",
  {"valeur": 5.0}, "s", "TIV > 5 s (Aron & Durrande 2000, OCDE 2018)", "norme",
  src("CEREMA_V80_2020", "p. 23 (PDF 25) ; Vias 2021 p. 21"), "elevee", role="contrainte_modele")
ln_tiv_loc = lois.lognormale_depuis_moyenne_ecart(2.07, math.sqrt(0.18))
ln_tiv_aut = lois.lognormale_depuis_moyenne_ecart(1.42, math.sqrt(0.08))
P("tiv.moyen_conducteur_urbain", V, "TIV moyen propre à un conducteur en suivi, routes locales",
  "SPMD Ann Arbor : distribution des TIV moyens par conducteur (85 656 événements de suivi locaux)", "lognormale",
  r4(ln_tiv_loc), "s", "suivi stable > 50 s, vitesse > 10 m/s, sans changement de voie", "mesure",
  src("HUANG2018", "p. 5, tableau V"), "moyenne", stats={"moyenne": 2.07, "variance": 0.18, "p25": 1.77, "p50": 2.03, "p75": 2.33},
  notes="Lognormale de l'article (moments) ; quartiles recalculés 1,77 / 2,03 / 2,33 = publiés.",
  tirage={"facteur": "style", "charge": -0.5, "groupe": "tiv_moyen"})
P("tiv.moyen_conducteur_autoroute", V, "TIV moyen propre à un conducteur en suivi, autoroutes",
  "SPMD Ann Arbor, 75 353 événements de suivi sur autoroutes", "lognormale", r4(ln_tiv_aut), "s", "suivi stable",
  "mesure", src("HUANG2018", "p. 5, tableau V"), "moyenne", stats={"moyenne": 1.42, "variance": 0.08, "p25": 1.21, "p50": 1.39, "p75": 1.60},
  notes="Quartiles recalculés 1,22 / 1,39 / 1,59. L'article rappelle 1,3-1,6 s dans la littérature.",
  tirage={"facteur": "style", "charge": -0.5, "groupe": "tiv_moyen"})
P("tiv.min_conducteur_urbain", V, "TIV minimal habituel d'un conducteur (2,5e centile de ses TIV), routes locales", "SPMD Ann Arbor",
  "gev", {"k": -0.0737, "sigma": 0.2267, "mu": 0.6880}, "s", "suivi", "mesure", src("HUANG2018", "p. 5, tableau VI ; p. 6"),
  "moyenne", stats={"moyenne": 0.80, "variance": 0.071},
  notes="Le texte parle d'« écart-type » 0,071 s : le recalcul GEV montre qu'il s'agit de la variance (écart-type 0,27 s).",
  tirage={"facteur": "style", "charge": -0.5, "groupe": "tiv_min"})
P("tiv.min_conducteur_autoroute", V, "TIV minimal habituel d'un conducteur, autoroutes", "SPMD Ann Arbor", "gev",
  {"k": 0.0415, "sigma": 0.1058, "mu": 0.3720}, "s", "suivi", "mesure", src("HUANG2018", "p. 5, tableau VI ; p. 6"), "moyenne",
  stats={"moyenne": 0.44, "variance": 0.021}, tirage={"facteur": "style", "charge": -0.5, "groupe": "tiv_min"})
P("tiv.population_highD", V, "TIV instantanés en suivi, autoroutes allemandes (highD)", "Toutes paires suiveur-meneur du jeu highD",
  "lognormale_decalee", {"decalage": 0.377, "mu_log": 0.233, "sigma_log": 0.899}, "s", "autoroute, flux ininterrompu", "mesure",
  src("LEUNGBOOTNAK2025", "p. 12-13, tableau 3 (ajustement MCMC « Shifted Log-normal »)"), "moyenne",
  notes="Médiane 1,64 s, moyenne 2,27 s, P10 0,78 s, P90 4,37 s. Jeu highD non téléchargé (licence non commerciale) : seule la loi publiée est reprise. NGSIM : décalage 0,528, μ 0,683, σ 0,594.",
  role="reference_validation")
P("tiv.population_NGSIM", V, "TIV en suivi, NGSIM (US-101 / I-80, Californie)", "1 341 événements de suivi", "lognormale",
  {"mu_log": 0.4226, "sigma_log": 0.4365}, "s", "autoroute urbaine congestionnée", "mesure", src("ZHU2019", "p. 4, éq. 4-5"), "moyenne",
  notes="Médiane 1,53 s, moyenne 1,68 s.", role="reference_validation")
P("tiv.udrive_suivi_rapproche", V, "TIV minimal moyen lors des épisodes de suivi rapproché (TIV < 1,5 s pendant ≥ 1,5 s), par pays",
  "UDRIVE, conducteurs de 5 pays européens", "constante", {"France": 1.13, "Pays_Bas": 1.13, "Allemagne": 1.18, "Pologne": 1.19, "Royaume_Uni": 1.16},
  "s", "épisodes de suivi rapproché ; 66 % d'entre eux sous des VMA de 31-50 km/h", "mesure",
  src("UDRIVE_D41", "p. 38-41 (PDF 39-42), fig. 3.6-3.8"), "moyenne",
  notes="Plus la VMA est élevée, moins les épisodes de suivi rapproché sont fréquents (p. 45).", role="reference_validation")
P("tiv.file_feu", V, "Temps intervéhiculaire au passage de la ligne de feux selon le rang (démarrage au vert)",
  "Mesures par drone, 2 carrefours de Stuttgart", "constante",
  {"rang1": 3.25, "rang2": 2.3, "rang3": 2.1, "rang4_plus": [1.8, 2.1], "ecart_type_rang1": 1.15, "ecart_type_rang4_plus": [0.5, 0.85]},
  "s", "lecture de la fig. 10a (± 0,05 s)", "mesure", src("SALLES2020", "fig. 10 p. 17"), "moyenne", role="reference_validation")
P("tiv.ecart_arret", V, "Distance de garde à l'arrêt (s0 des modèles de type IDM)", "Calages IDM publiés : Kesting & Treiber 2008 (3 jeux de trajectoires, Stuttgart) ; Zhu et al. 2018 (42 conducteurs, Shanghai)",
  "lognormale", r4(lois.lognormale_depuis_quantiles(1.04, 0.05, 3.40, 0.95)), "m", "véhicules à l'arrêt en file", "estimation",
  src("KESTING2008", "p. 7, tableau 1 (s0 = 2,41 / 2,33 / 2,56 ; 2,63 / 2,82 / 3,40 ; 1,61 / 1,52 / 1,04 m : 3 jeux × 3 mesures d'erreur)"), "faible",
  stats={"kesting_treiber_2008_tab1": [2.41, 2.33, 2.56, 2.63, 2.82, 3.40, 1.61, 1.52, 1.04],
         "kesting_treiber_2008_Fmix": [2.33, 2.82, 1.52],
         "zhu2018_tab2_42_conducteurs": {"moyenne": 1.56, "ecart_type": 0.96, "p5": 0.10, "p95": 3.42}},
  notes=("Correction du 17/10/2026 : la v0.1 utilisait U(1 ; 2,5) m attribué à un résumé secondaire (Salles 2020 tab. 4 : "
         "« 1-1,6 m Kesting & Treiber 2008 »), alors que la source primaire donne 1,04 à 3,40 m (6 calages sur 9 au-dessus de 2,3 m). "
         "Loi retenue : lognormale de P5 = 1,04 m (plus petit calage de Kesting & Treiber) et P95 = 3,40 m (plus grand calage, proche "
         "du P95 de Zhu 2018 : 3,42 m) ; médiane 1,88 m, moyenne 2,0 m. Le P5 de Zhu (0,10 m) est un artefact de calage en mouvement "
         "(s0 mal identifié) et n'est pas retenu. Aucune mesure directe de l'écart à l'arrêt trouvée. SUMO minGap par défaut 2,5 m."),
  tirage={"facteur": "style", "charge": -0.3, "groupe": "ecart_arret"})

# =========================================================================================
# 7. CARREFOURS À FEUX
# =========================================================================================
V = "feux"
P("feu.saturation_fr", V, "Débit de saturation par voie", "Norme de conception française", "constante",
  {"valeur_uvpd_h": 1800, "tiv_equivalent_s": 2.0}, "uvpd/h", "moyenne ; valeurs supérieures ou inférieures selon le contexte",
  "norme", src("CERTU_FEUX2010", "p. 34-35 et p. 23 (« de l'ordre de 1 800 véh/h par voie »)"), "elevee", role="norme_validation")
P("feu.saturation_hcm", V, "Débit de saturation idéal et plage observée", "Manuel FHWA (HCM)", "constante",
  {"ideal_uvp_h": 1900, "plage_uvp_h": [1500, 2000], "temps_perdu_demarrage_s": 2.0, "temps_perdu_total_par_phase_s": 4.0},
  "uvp/h ; s", "saturation atteinte après le 4e véhicule", "norme", src("FHWA_STM2008", "p. 3-5 à 3-7 (PDF 63-65)"), "elevee",
  role="norme_validation")
P("feu.demarrage_fr", V, "Temps nécessaire au démarrage (temps perdu)", "Fiche Cerema", "constante", {"valeur": 1.0}, "s",
  "« environ 1 seconde » + jaune 3 s + rouge de dégagement = temps neutralisé", "norme", src("CEREMA_SDB20", "p. 4"),
  "moyenne", role="norme_validation")
P("feu.duree_jaune_fr", V, "Durée du jaune fixe et vert minimal", "Réglementation française (via guide Certu)", "constante",
  {"jaune_agglo_s": 3, "jaune_rase_campagne_s": 5, "vert_min_s": 6, "vitesse_degagement_m_s": 10}, "s",
  "rouge de dégagement calculé à 10 m/s pour les véhicules", "norme", src("CERTU_FEUX2010", "p. 68 et p. 33"), "elevee",
  role="norme_validation")
P("feu.tpr_jaune", V, "Temps de perception-réaction au passage au jaune (observé à l'insu des conducteurs)",
  "Chang et al. (n = 579), cité par NCHRP 400", "lognormale", r4(lois.lognormale_depuis_moyenne_ecart(1.30, 0.74)), "s",
  "approche d'un feu, conducteurs non informés", "estimation", src("NCHRP400", "p. 24 (PDF 34), tableau 13"), "moyenne",
  stats={"moyenne": 1.30, "ecart_type": 0.74, "n": 579, "valeur_conception_ITE": 1.0},
  notes="Valeur de conception du jaune aux États-Unis : t = 1,0 s, a = 10 ft/s² (3,05 m/s²) (FHWA STM 2008 p. 5-13, PDF 138).",
  tirage={"facteur": "vigilance", "charge": -0.5, "groupe": "tpr"})
lg = lois.logistique_depuis_p10_p90(2.5, 5.5)
P("feu.seuil_arret_jaune", V, "Seuil individuel de temps à la ligne (TTL) au-delà duquel le conducteur s'arrête au jaune",
  "Synthèse FHWA : zone d'indécision entre 5,5 s (90 % s'arrêtent) et 2,5 s (10 %)", "logistique", r4(lg), "s",
  "approche à vitesse stabilisée ; P(arrêt | TTL) = P(seuil < TTL)", "estimation",
  src("FHWA_STM2008", "p. 4-24 et 4-25 (PDF 114-115), fig. 4-18 et 4-19"), "moyenne",
  stats={"TTL_90pc_arret": 5.5, "TTL_10pc_arret": 2.5, "Chang": "85 % s'arrêtent au-delà de 3 s ; presque tous passent en deçà de 2 s"},
  notes=("Si chaque conducteur a un seuil T et s'arrête quand TTL > T, la loi des seuils est la logistique P(arrêt|TTL). "
         "FHWA 2008 p. 4-25 ne donne que deux points (5,5 s ≈ 90 % d'arrêts, 2,5 s ≈ 10 %), établis sur des approches à plus de "
         "35 mph (p. 4-24) aux États-Unis ; toute autre valeur (ex. P = 0,32 à 3,5 s) est une interpolation du projet, pas une "
         "donnée FHWA. Transposition à une artère française à 50 km/h avec jaune de 3 s : hypothèse. Aucune donnée française de "
         "zone de dilemme trouvée (lacune)."),
  tirage={"facteur": "style", "charge": 0.4, "groupe": "jaune"})
P("feu.dec_jaune_conception", V, "Décélération de conception face au jaune", "Valeur citée par le FHWA (ITE)", "constante",
  {"valeur": 3.05}, "m/s²", "10 ft/s²", "norme", src("FHWA_STM2008", "p. 5-13 (PDF 138)"), "moyenne", role="norme_validation")

# =========================================================================================
# 8. CARREFOURS SANS FEUX : ACCEPTATION DE CRÉNEAUX
# =========================================================================================
V = "creneaux"
P("creneau.norme_fr", V, "Créneau critique de conception (méthode du créneau critique)", "Norme de conception urbaine française",
  "constante", {"traversee_1_file": 4, "traversee_2_files": 6,
                "insertion_sens_unique": {"30": 4, "50": 5, "70": 6},
                "insertion_double_sens_TAD": {"30": 4, "50": 5, "70": 6},
                "insertion_double_sens_TAG": {"30": 5, "50": 6, "70": 7}}, "s",
  "vitesse réglementaire de la voie principale en km/h ; bus et PL non majorés (calcul en uvp)", "norme",
  src("CERTU_CU2010", "p. 93 imprimée (PDF 92-93)"), "elevee", role="parametre_conducteur",
  notes="Valeurs de conception utilisées comme créneaux critiques MOYENS du modèle (contexte français) ; la dispersion entre conducteurs vient de creneau.dispersion.")
P("creneau.norme_fr_vsa70", V, "Créneau critique et créneau complémentaire (temps de suivi) sur artère 70 km/h",
  "Norme VSA70", "constante", {"T_avec_TAG": {"critique": 7, "complementaire": 4}, "X_avec_TAG": {"critique": 7, "complementaire": 4},
                                "demi_carrefour": {"critique": 6, "complementaire": 4}}, "s", "AU70", "norme",
  src("VSA70_2013", "annexe 1 p. 97 (PDF 97)"), "elevee", role="parametre_conducteur")
P("creneau.hcm_base", V, "Créneaux critiques et temps de suivi de base du HCM (carrefour à STOP, voie principale 2x2)",
  "HCM 6e éd. (valeurs reproduites par un rapport HCS7)", "constante",
  {"critique": {"TAG_secondaire": 7.5, "traversee_secondaire": 6.5, "TAD_secondaire": 6.9, "TAG_principale": 4.1},
   "suivi": {"TAG_secondaire": 3.5, "traversee_secondaire": 4.0, "TAD_secondaire": 3.3, "TAG_principale": 2.2}}, "s",
  "conditions de base (VL, pente nulle) ; voie principale à 2 voies par sens", "norme",
  src("QK4_HCS2021", "p. 2 (rapport HCS7 « KY 61 & Springfield Rd »)"), "moyenne",
  notes="Pour une voie principale à 1 voie par sens, le HCM donne 7,1 / 6,5 / 6,2 / 4,1 s (non vérifié sur un document téléchargé : à confirmer).",
  role="reference_validation")
P("creneau.giratoire_meta", V, "Créneau critique et temps de suivi à l'entrée des giratoires à une voie (méta-analyse, effets aléatoires)",
  "Études internationales (Allemagne, Pays-Bas, Italie, Danemark, Portugal, États-Unis, Canada, Australie, Chine)", "constante",
  {"critique_moyen": 4.27, "critique_erreur_type": 0.11, "suivi_moyen": 3.10, "suivi_erreur_type": 0.07,
   "deux_voies": {"critique_anneau_exterieur": 3.82, "critique_anneau_interieur": 4.16, "suivi_voie_droite": 2.72}}, "s",
  "giratoire à une voie ; synthèse de moyennes d'études", "mesure", src("GIUFFRE2016", "p. 9-10, tableaux 4-5 ; p. 11-13, tableaux 6-8"),
  "moyenne", notes="Plage des moyennes par étude : critique 2,2-5,9 s ; suivi 2,1-4,3 s (tableau 1). Aucune mesure française dans la méta-analyse.",
  role="parametre_conducteur")
P("creneau.dispersion", V, "Dispersion entre conducteurs du créneau critique (écart-type) et du temps de suivi",
  "Études à une voie ayant publié l'écart-type (tableau 1 de la méta-analyse)", "constante",
  {"ecart_type_critique": {"Gazzarri_Italie": [0.67, 0.95], "Rodegerdts_USA": [0.70, 1.80], "Xu_Tian_USA": [0.90, 1.10],
                           "Zheng_USA": [1.00, 2.00], "Nicolosi_Italie": 1.13, "Fortuijn_Pays_Bas": [0.19, 0.28]},
   "ecart_type_suivi": {"Gazzarri_Italie": [0.68, 0.90], "Rodegerdts_USA": [0.80, 1.50], "Qu_Australie": 0.62}}, "s",
  "", "mesure", src("GIUFFRE2016", "p. 5, tableau 1"), "moyenne", role="reference_validation")
ln_cr = lois.lognormale_depuis_moyenne_ecart(1.0, 0.20)
P("creneau.facteur_conducteur", V, "Facteur multiplicatif individuel appliqué au créneau critique de référence",
  "Population de conducteurs (VL)", "lognormale", r4(ln_cr), "-", "tc_conducteur = facteur × tc_référence(manœuvre, vitesse)",
  "estimation", src("GIUFFRE2016", "p. 5, tableau 1 (écart-type ≈ 0,67-0,95 s pour des moyennes de 3,5-4,1 s, Italie)"), "faible",
  notes="Coefficient de variation 0,20 choisi dans la plage européenne (Gazzarri : 0,19-0,23). À recaler sur des observations françaises (lacune).",
  tirage={"facteur": "style", "charge": -0.5, "groupe": "creneau"})
ln_tf = lois.lognormale_depuis_moyenne_ecart(1.0, 0.27)
P("creneau.facteur_suivi", V, "Facteur multiplicatif individuel appliqué au temps de suivi", "Population VL", "lognormale",
  r4(ln_tf), "-", "tf_conducteur = facteur × tf_référence", "estimation",
  src("GIUFFRE2016", "p. 5, tableau 1 (Gazzarri : écart-type 0,68-0,90 s pour 2,5-2,8 s)"), "faible",
  notes="Coefficient de variation 0,27 (Gazzarri, Italie).", tirage={"facteur": "style", "charge": -0.4, "groupe": "suivi"})
P("creneau.girabase_cetur", V, "Capacité d'une entrée de giratoire urbain à une voie (droite Cetur/Certu) : Ce = 1 500 - 5/6 Qg",
  "Méthode française ancienne (citée)", "fonction",
  {"expression": "Ce_uvp_h = 1500 - 5/6 * Qg", "Qg": "Qa + Ks Qs", "Ks": "(15 - La)/23 ; La largeur de l'îlot séparateur (m)",
   "intervalle_moyen_saturation_s": 2.4, "Qg_annulation": 1800}, "uvp/h",
  "angle d'attaque 40-60° ; temps d'attente (Tanner) = (2000 + 2 Qg)/(Ce - Qe)", "norme",
  src("MAIGA2006", "p. 18-21"), "faible",
  notes="Source secondaire citant le Certu ; la formule Girabase (Certu 1999) n'a pas été trouvée en accès libre (lacune). 2,4 s ≈ temps de suivi à saturation.",
  role="reference_validation")

# =========================================================================================
# 9. ARRÊT AU STOP
# =========================================================================================
V = "stop"
P("stop.comportement", V, "Comportement à un STOP : arrêt complet, arrêt glissé, pas d'arrêt",
  "Carrefour à STOP sur toutes les branches, Vaughan (Ontario), heures de pointe, 2006 (848 puis 808 véhicules)", "categorielle",
  {"modalites": {"arret_complet": 0.57, "arret_glisse": 0.39, "pas_d_arret": 0.04}}, "-",
  "moyenne des 4 relevés (pointes du matin et du soir, avant / après panneaux supplémentaires)", "estimation",
  src("VAUGHAN2006", "p. 2 (tableau)"), "faible",
  stats={"mars_2006": {"am": [0.52, 0.46, 0.02], "pm": [0.51, 0.42, 0.07]}, "nov_2006": {"am": [0.62, 0.36, 0.02], "pm": [0.64, 0.33, 0.03]}},
  notes="Aucune observation française publiée trouvée (lacune). Code de la route : marquer l'arrêt à la limite de la chaussée abordée. Le taux d'arrêt complet augmente fortement en présence de trafic transversal (synthèse québécoise citée en recherche, non vérifiée).",
  tirage={"facteur": "style", "charge": 0.4, "groupe": "stop"})
P("stop.vitesse_residuelle_glisse", V, "Vitesse minimale lors d'un arrêt glissé", "Lacune : proxy = vitesse minimale avant passage piéton avec interaction (inD)",
  "lognormale", r4(lois.lognormale_depuis_moyenne_ecart(1.3, 0.6)), "m/s", "proxy", "estimation",
  src("GANKHUYAG2023", "p. 4, tableau 1 (Vm = 1,29 m/s avec piéton)"), "faible",
  notes="Moyenne = proxy inD ; écart-type 0,6 m/s : hypothèse de travail, à mesurer. À remplacer dès qu'une mesure d'arrêt glissé existe.",
  tirage={"facteur": "style", "charge": 0.4, "groupe": "stop_vitesse"})

# =========================================================================================
# 10. RALENTISSEURS
# =========================================================================================
V = "ralentisseurs"
P("ralent.objectif_conception", V, "Vitesse visée au franchissement des coussins et plateaux", "Guide Certu", "constante",
  {"vitesse_kmh": 30, "zone_rencontre_kmh": 20, "distance_50_vers_30_m": 25, "hauteur_coussin_cm": [6, 7]}, "km/h ; m",
  "limitation ponctuelle à 30 km/h ; visibilité 25 m pour passer de 50 à 30 km/h", "norme",
  src("CERTU_COUSSINS2010", "p. 17-19 et 45 (PDF 18-19, 46)"), "elevee", role="norme_validation")
P("ralent.vitesse_franchissement", V, "Vitesse peu après un dispositif ralentisseur en zone 30 (proxy du franchissement)",
  "Voitures en vitesse libre, zones 30 avec dispositif ralentisseur, Belgique 2021 (moyenne nationale publiée ; 10-20 m après chicane, coussin, plateau, casse-vitesse)", "normale",
  {"moyenne": 34.0, "ecart_type": round(lois.normale_depuis_v85(34.0, 41.5)["ecart_type"], 2)}, "km/h",
  "zone 30 avec dispositif ; mesure en aval (le conducteur ré-accélère déjà) ; dispositifs non distingués (chicanes, coussins, plateaux, casse-vitesse, p. 19)", "estimation",
  src("VIAS2021", "p. 39-40 (PDF 39-40), fig. 23 (moyennes) et fig. 24 (V85) lues sur rendu natif ; p. 19 (position de mesure)"), "faible",
  stats={"moyenne": 34.0, "V85": 41.5,
         "bruxelles": {"moyenne": 27.6, "V85": 34.3, "sans_dispositif": [33.3, 40.8], "difference": "significative (p = 0,011)"},
         "flandre": {"moyenne": 34.9, "V85": 42.3, "sans_dispositif": [36.7, 46.4], "difference": "non significative"},
         "wallonie": {"moyenne": 34.5, "V85": 42.5, "sans_dispositif": "non mesuré"},
         "belgique_sans_dispositif": {"moyenne": 35.1, "V85": 43.7}},
  notes=("Correction du 17/10/2026 : la v0.1 ne retenait que la Région bruxelloise (27,6 km/h), seule région où l'effet du dispositif "
         "est significatif. Loi retenue : moyenne nationale publiée (34,0 ; V85 41,5) ; variantes régionales dans "
         "« statistiques_publiees » (Bruxelles : dispositifs efficaces). Le dos-d'âne n'est pas isolé dans la source. Aucune mesure "
         "française de vitesse au droit d'un coussin ou d'un plateau trouvée (lacune)."),
  tirage={"facteur": "style", "charge": 0.5, "groupe": "ralentisseur"})

# =========================================================================================
# 11. PIÉTONS
# =========================================================================================
V = "pietons"
P("pieton.taux_cede", V, "Part des piétons approchant un passage zébré non régulé auxquels le premier véhicule cède le passage (proxy de la cession par conducteur)",
  "Pologne, observations vidéo sur site (2018), près de 7 000 piétons, avant l'obligation polonaise de 2021", "bernoulli", {"p": 0.45}, "-",
  "passage piéton marqué sans feux, piéton arrivant au bord du trottoir quand un véhicule approche", "mesure",
  src("DABROWSKA2021", "p. 192 (PDF 8), § 3.1 (45 % des piétons « were given way by the first oncoming vehicle ») ; p. 191 (PDF 7) : près de 7 000 piétons"), "faible",
  notes="En France le conducteur doit céder au piéton « s'engageant ou manifestant clairement l'intention de le faire » (art. R415-11) : le taux français est probablement plus élevé, aucune mesure française publiée trouvée (lacune).",
  tirage={"facteur": "style", "charge": 0.4, "groupe": "pieton"})
P("pieton.approche", V, "Approche d'un passage piéton avec et sans interaction (début de freinage, vitesse minimale, décélération)",
  "inD (Aachen, carrefour Frankenburg, VMA 15 m/s), ~4 h d'enregistrement", "constante",
  {"sans_interaction": {"Vi": 8.53, "LVi": 39.81, "Vm": 5.26, "LVm": 8.79, "dav": 0.75, "SRT": 4.59},
   "avec_pieton": {"Vi": 7.96, "LVi": 42.97, "Vm": 1.29, "LVm": 7.61, "dav": 0.88, "SRT": 7.15},
   "avec_cycliste": {"Vi": 6.39, "LVi": 42.43, "Vm": 2.19, "LVm": 8.17, "dav": 0.48, "SRT": 8.00}},
  "m/s ; m ; m/s² ; s", "Vi vitesse au début du freinage à LVi m du passage ; Vm vitesse minimale à LVm m ; dav décélération moyenne ; SRT durée de réduction",
  "mesure", src("GANKHUYAG2023", "p. 4, tableau 1"), "moyenne", role="parametre_conducteur",
  notes="Jeu inD non téléchargé (licence non commerciale) : seules les moyennes publiées sont reprises.")
P("pieton.distance_regle_cu", V, "Distance minimale d'un véhicule pour qu'un piéton traverse (règle de conception)",
  "Guide Certu", "constante", {"50_kmh_m": 30, "zone_30_m": 15}, "m", "freinage ≈ 15 m à 50 km/h sur sec + 1 s de réaction",
  "norme", src("CERTU_CU2010", "p. PDF 74"), "moyenne", role="norme_validation")

# =========================================================================================
# 12. CHANGEMENTS DE VOIE
# =========================================================================================
V = "changements_de_voie"
P("vdv.duree_chevauchement", V, "Durée d'un changement de voie (temps où le véhicule occupe deux voies)",
  "NGSIM (US-101, I-80), 1 105 changements de voie", "lognormale", r4(lois.lognormale_depuis_moyenne_ecart(4.01, 2.31)), "s",
  "autoroute urbaine ; borne basse de la durée réelle", "estimation", src("THIEMANN2008", "p. 17-18, éq. 21, fig. 8"), "moyenne",
  stats={"moyenne": 4.01, "ecart_type": 2.31, "mode": 3.0, "duree_complete_estimee": [5, 6]},
  notes="Lognormale par les moments (moyenne et écart-type reproduits). Son mode vaut 2,6 s contre environ 3 s dans la source (fig. 8) : la forme n'est pas exacte. Durée complète (préparation incluse) estimée à 5-6 s par les auteurs.",
  tirage={"facteur": "style", "charge": -0.4, "groupe": "vdv"})
P("vdv.insertion_devant", V, "Changement de voie devant le conducteur (cut-in) : durée, vacance initiale, lacet maximal",
  "SPMD Ann Arbor : 422 249 cas (78,7 % routes locales)", "constante",
  {"duree_moyenne_s": {"autoroute": 4.3, "local": 2.0},
   "lacet_max_moyen_deg_s": {"autoroute": 0.6, "local": 1.4},
   "distance_initiale_moyenne_m": {"autoroute": 75.8, "local": 60.2},
   "distance_initiale_percentiles_m": {"autoroute": {"10": 96.2, "30": 82.3, "70": 44.8, "90": 17.0},
                                       "local": {"10": 85.7, "30": 66.5, "70": 36.8, "90": 21.8}},
   "gev_lacet_max": {"autoroute": {"k": -0.0083, "sigma": 0.2325, "mu": 0.5900}, "local": {"k": 0.1525, "sigma": 0.7381, "mu": 1.3953}}},
  "s ; deg/s ; m", "véhicule qui s'insère devant le véhicule instrumenté", "mesure",
  src("HUANG2018", "p. 4 (lacet, tableau IV), p. 7 (tableau VIII), p. 8 (durée)"), "moyenne",
  notes="Les percentiles de distance sont ceux de l'inverse 1/R (10 % = 1/96,2 m⁻¹…).", role="parametre_conducteur")

# =========================================================================================
# 13. HÉTÉROGÉNÉITÉ : ÂGE, NOVICES, DISTRACTION, SEXE
# =========================================================================================
V = "heterogeneite"
P("hetero.novice_vitesses_max", V, "Vitesses maximales des élèves conducteurs et conducteurs en période probatoire",
  "Conducteurs en permis probatoire (3 ans ; 2 ans après conduite accompagnée)", "constante",
  {"autoroute_130": 110, "autoroute_110_et_routes_2x2_avec_TPC": 100, "autres_routes": 80}, "km/h",
  "non concernés par le relèvement à 90 km/h", "norme", src("AN_QE8216", "p. 1-2 (cite l'art. R413-5 du code de la route)"),
  "elevee", role="modulateur_profil")
P("hetero.distraction_part_temps", V, "Part du temps de conduite consacrée à une tâche secondaire", "UDRIVE, 87 conducteurs VL, 653 trajets (~167 h)",
  "constante", {"France": 0.083, "Allemagne": 0.019, "Pologne": 0.194, "Royaume_Uni": 0.088, "ensemble": 0.102,
                "hommes": 0.108, "femmes": 0.095, "telephone_ensemble": 0.042}, "-",
  "tâches : téléphone, appareil électronique, manger/boire, fumer, lire/écrire, toilette, parler/chanter", "mesure",
  src("UDRIVE_D41", "p. 5 (fig. 0.3, PDF 6) et p. 46-47 (PDF 47-48)"), "moyenne",
  notes=("Répartition des usages du téléphone : interaction mains libres 38,4 %, conversation mains libres 22,6 %, interaction en main (SMS…) 22,0 %. "
         "ATTENTION (17/10/2026) : c'est une part du temps occupé par une tâche secondaire (parler, chanter et conversations mains "
         "libres compris), PAS une part de regards hors route au sens de Markkula 2016 ; son emploi comme probabilité d'avoir les "
         "yeux hors de la menace est une hypothèse du prototype."),
  role="parametre_conducteur")
P("hetero.cycliste_age", V, "Vitesse moyenne des cyclistes selon l'âge et le type de vélo",
  "Étude naturaliste allemande : 90 participants, 4 semaines, ~17 000 km", "constante",
  {"velo": {"<=40": 16.6, "41-64": 15.8, ">=65": 13.9, "ensemble": 15.3},
   "VAE_25": {"<=40": 20.5, "41-64": 17.5, ">=65": 14.8, "ensemble": 17.4},
   "speed_pedelec_45": {"<=40": 23.4, "41-64": 25.1, "ensemble": 24.5}}, "km/h", "trajets quotidiens", "mesure",
  src("SCHLEINITZ2017", "diapositive 5"), "moyenne", role="parametre_conducteur")
P("hetero.sexe_vitesse", V, "Différences hommes-femmes", "UDRIVE", "constante",
  {"tiv_moyen_s": {"hommes": 2.34, "femmes": 2.25}, "exces_legers_plus_frequents": "femmes", "exces_graves_plus_frequents": "hommes"},
  "s", "épisodes de suivi rapproché", "mesure", src("UDRIVE_D41", "p. 39-40 (PDF 40-41)"), "faible",
  notes="Le texte parle de TIV mais la figure 3.7 est titrée « durée moyenne des épisodes » : ambigu. Bosetti (2014) : sexe non significatif sur les accélérations.",
  role="contexte")
P("hetero.traits_exces", V, "Lien entre traits de personnalité déclarés et excès de vitesse", "UDRIVE", "constante",
  {"part_d_excedants": {"traits_negatifs_bas": 0.48, "traits_negatifs_hauts": 0.59, "vitesse_declaree_basse": 0.43,
                        "vitesse_declaree_haute": 0.62, "deviance_basse": 0.47, "deviance_haute": 0.58}}, "-",
  "excès = ≥ 11 % au-dessus de la limite pendant > 10 s", "mesure", src("UDRIVE_D41", "p. 40 (PDF 41), tableau 3.4"), "moyenne",
  notes="Justifie un facteur latent « style » commun à la vitesse et aux comportements à risque.", role="justification_correlation")
P("hetero.facteur_conducteur_bosetti", V, "Part de variance expliquée par l'identité du conducteur et l'expérience", "Bosetti 2014, ANOVA",
  "constante", {"alpha": {"experience_p": 8.6e-5, "conducteur_p": 4.6e-6}, "a_lateral": {"experience_p": 2.9e-5, "conducteur_p": 2.9e-6},
                "b_longitudinal": {"experience_p": 0.031, "conducteur_p": 0.023}, "c_freinage": {"experience_p": "ns"}}, "-",
  "le sexe, le système co-driver et l'état de la route ne sont pas significatifs", "mesure", src("BOSETTI2014", "p. 167, tableau 6 (PDF 11)"),
  "moyenne", notes="Le style est propre au conducteur et stable : justifie un tirage par conducteur et non par manœuvre.",
  role="justification_correlation")

# =========================================================================================
# 14. CYCLISTES ET DEUX-ROUES MOTORISÉS
# =========================================================================================
V = "deux_roues"
P("velo.vitesse_traversee", V, "Vitesse de traversée d'un carrefour à feux au vert, cycliste non gêné",
  "Munich, 4 carrefours, 466 cyclistes (groupe A)", "normale_tronquee", {"moyenne": 5.23, "ecart_type": 1.25, "min": 1.5, "max": 10.0},
  "m/s", "vert, intervalle > 2 s avec le cycliste précédent", "mesure", src("TWADDLE2016", "p. 16, tableau 2"), "moyenne",
  stats={"moyenne": 5.23, "ecart_type": 1.25, "fluctuation_moyenne": 1.82, "v_min_moy": 4.20, "v_max_moy": 6.02},
  notes="Plage de vitesse normale : 0,8 à 1,15 × vitesse désirée (p. 9). Revue : vitesses moyennes 3,2-6,9 m/s, accélérations moyennes 0,23-1,07 m/s² (p. 3).",
  tirage={"facteur": "style", "charge": 0.5, "groupe": "velo_vitesse", "population": "cycliste"})
P("velo.acceleration_revue", V, "Accélération moyenne des cyclistes au démarrage (revue)", "Études vidéo citées", "uniforme",
  {"min": 0.23, "max": 1.07}, "m/s²", "constante sur le démarrage (modèle simple) ; profil réel décroissant avec la vitesse", "mesure",
  src("TWADDLE2016", "p. 3"), "faible", notes="Faute de distribution publiée lisible, plage uniforme (hypothèse).",
  tirage={"facteur": "style", "charge": 0.5, "groupe": "velo_acc", "population": "cycliste"})
P("velo.defauts_sumo", V, "Valeurs par défaut SUMO (comparaison)", "Logiciel SUMO 1.27.1", "constante",
  {"bicycle": {"accel": 1.2, "decel": 3.0, "emergencyDecel": 7.0, "desiredMaxSpeed_kmh": 20, "minGap": 0.5},
   "moped": {"accel": 1.1, "decel": 7.0, "maxSpeed_kmh": 45, "minGap": 2.5},
   "motorcycle": {"accel": 6.0, "decel": 10.0, "minGap": 2.5}}, "m/s² ; km/h ; m", "valeurs de la page « Vehicle Type Parameter Defaults »",
  "defaut_logiciel", src("SUMO_DOC", "Vehicle_Type_Parameter_Defaults.html"), "faible", role="reference_validation",
  notes="Ce ne sont pas des mesures ; les comportements des deux-roues motorisés (remontée de file, vitesses) restent une lacune.")
P("drm.tiv_derriere", V, "TIV d'une voiture derrière un deux-roues motorisé", "UDRIVE, 140 conducteurs, ~650 000 km", "constante",
  {"constat": "pas plus court que derrière une voiture ; plutôt plus long"}, "-", "sections droites", "mesure",
  src("UDRIVE_D41", "p. 64-65 (PDF 65-66)"), "faible", role="contexte")

# =========================================================================================
# 15. CORRESPONDANCE SUMO (valeurs par défaut, pour comparaison)
# =========================================================================================
V = "sumo"
P("sumo.defauts_vtype", V, "Valeurs par défaut des paramètres SUMO de comportement (voiture)", "Logiciel SUMO 1.27.1", "constante",
  {"accel": 2.6, "decel": 4.5, "emergencyDecel": 9.0, "sigma": 0.5, "tau": 1.0, "minGap": 2.5, "speedFactor": 1.0, "speedDev": 0.1,
   "jmTimegapMinor": 1.0, "jmCrossingGap": 10.0, "jmStoplineGap": 1.0, "jmDriveAfterRedTime": -1, "jmIgnoreFoeProb": 0.0,
   "impatience": 0.0, "time_to_impatience_s": 180}, "SI", "Krauss par défaut", "defaut_logiciel",
  src("SUMO_DOC", "Definition_of_Vehicles,_Vehicle_Types,_and_Routes.html (tableaux vType et jm*)"), "elevee",
  role="reference_validation", notes="Voir profils_conducteurs.json → correspondance_sumo pour les valeurs proposées par profil.")


def meta():
    return {
        "titre": "Modèle de conducteurs - paramètres sourcés (volet 02_Conducteurs)",
        "version": "0.1.0",
        "date": dt.date.today().isoformat(),
        "generateur": "recon/trafic/conducteurs/construire_parametres.py",
        "unites": "SI sauf mention (vitesses publiées en km/h)",
        "natures": {"norme": "valeur réglementaire ou de conception (sert surtout à la validation)",
                    "mesure": "valeur publiée issue d'observations ou d'essais",
                    "estimation": "loi ajustée par nous sur des statistiques publiées, ou hypothèse explicitée",
                    "defaut_logiciel": "valeur par défaut d'un outil (pas une mesure)"},
        "confiance": {"elevee": "source officielle ou grand échantillon, contexte proche (France/Europe)",
                      "moyenne": "mesure fiable mais contexte différent (pays, véhicule, petit échantillon) ou lecture graphique",
                      "faible": "source secondaire, proxy ou hypothèse à recaler"},
        "roles": {"parametre_conducteur": "tiré par conducteur dans le prototype",
                  "modulateur_profil": "modifie un profil (âge, véhicule, permis)",
                  "modulateur_contexte": "dépend du contexte (nuit, week-end), pas du conducteur",
                  "relation": "relation déterministe utilisée par le modèle",
                  "modele_avance": "option (modèle cinématique d'urgence)",
                  "norme_validation": "norme de conception servant de contrôle",
                  "reference_validation": "mesure servant de contrôle",
                  "contrainte_modele": "contrainte numérique du modèle",
                  "justification_correlation": "appuie la structure de corrélation",
                  "contexte": "information de contexte"},
        "tirage": "Champ « tirage » : le paramètre est tiré par conducteur par copule gaussienne ; "
                  "charge = corrélation entre la variable latente normale du paramètre et le facteur latent (style ou vigilance). "
                  "Les charges sont des HYPOTHÈSES documentées dans profils_conducteurs.json.",
        "convention_gev": "GEV au sens MATLAB/Huang 2018 : f(x|k,σ,μ) ; scipy.stats.genextreme(c=-k, loc=μ, scale=σ)",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=SORTIE_DEFAUT)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    ids = [p["id"] for p in PARAMS]
    assert len(ids) == len(set(ids)), "identifiants en double"
    doc = {"meta": meta(), "sources": SOURCES, "parametres": PARAMS}
    chemin = os.path.join(a.sortie, "conducteurs_parametres.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"{len(PARAMS)} paramètres -> {chemin}")


if __name__ == "__main__":
    main()
