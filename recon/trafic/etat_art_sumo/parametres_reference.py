"""Forme machine des paramètres du volet 03 (état de l'art des modèles).

Chaque entrée : {id, grandeur, population, loi, parametres, unite, conditions,
                 source:{doc, page, annee}, nature, confiance}
nature    : « norme » | « mesure » | « calage » (paramètre identifié sur données) |
            « défaut logiciel » | « mesure en simulation » (ce dépôt) | « estimation »
confiance : « élevée » (relu dans la source primaire) | « moyenne » (source secondaire ou
            lecture graphique) | « faible » (incohérence doc/code, à vérifier).

Écrit le même fichier à deux endroits (une seule source de vérité : ce script) :
  - D:\\ClaudeCode_RoadCreation\\assets\\specs\\trafic\\modeles_existants_reference.json
  - D:\\DocRoute\\17_Modele_Vehicules_Conducteurs\\03_Modeles_Existants\\parametres_modeles_existants.json
Les mesures en simulation sont relues dans les résumés JSON des scénarios S1-S3.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C  # noqa: E402

SORTIES = [Path(r"D:\ClaudeCode_RoadCreation\assets\specs\trafic\modeles_existants_reference.json"),
           Path(r"D:\DocRoute\17_Modele_Vehicules_Conducteurs\03_Modeles_Existants\parametres_modeles_existants.json")]

E = []


def P(id_, grandeur, population, loi, parametres, unite, conditions, doc, page, annee, nature, confiance="élevée"):
    E.append({"id": id_, "grandeur": grandeur, "population": population, "loi": loi, "parametres": parametres,
              "unite": unite, "conditions": conditions, "source": {"doc": doc, "page": page, "annee": annee},
              "nature": nature, "confiance": confiance})


# ------------------------------------------------------------------ SUMO 1.27.1 : défauts
DOC_VT = "SUMO 1.27.1 userdoc, Definition_of_Vehicles,_Vehicle_Types,_and_Routes.html (tableau « Available vType Attributes »)"
DOC_DEF = "SUMO 1.27.1 userdoc, Vehicle_Type_Parameter_Defaults.html"
POP = "SUMO vClass passenger (véhicule par défaut)"
for k, g, v, u, rem in [
    ("accel", "accélération max choisie par le conducteur (pas la capacité du véhicule)", 2.6, "m/s²", "doc : « not the car's maximum acceleration possibility but rather the maximum acceleration a driver chooses »"),
    ("decel", "décélération souhaitée (borne dure pour Krauss)", 4.5, "m/s²", ""),
    ("emergencyDecel", "décélération maximale physique (urgence)", 9.0, "m/s²", ""),
    ("tau", "temps inter-véhiculaire minimal désiré (Krauss : écart net arrière-meneur/avant+minGap)", 1.0, "s", ""),
    ("minGap", "distance à l'arrêt derrière le meneur", 2.5, "m", "valeur identique pour tous les véhicules (pas de dispersion)"),
    ("length", "longueur", 5.0, "m", ""), ("width", "largeur", 1.8, "m", ""), ("mass", "masse à vide", 1500, "kg", ""),
    ("maxSpeed", "vitesse max technique", 55.55, "m/s", "200 km/h"),
    ("startupDelay", "retard supplémentaire au démarrage après arrêt", 0.0, "s", ""),
]:
    P(f"sumo.passenger.{k}", g, POP, "constante", {"valeur": v}, u, rem or "valeur par défaut", DOC_VT + " ; " + DOC_DEF, "tableaux", 2026, "défaut logiciel")
P("sumo.passenger.sigma", "imperfection du conducteur Krauss (« dawdling »)", POP, "uniforme (tirage à chaque pas)",
  {"valeur": 0.5, "effet": "v <- v - sigma*accel*U(0,1)*dt (si v >= accel), MSCFModel_Krauss::dawdle2"}, "-",
  "tirage renouvelé à chaque pas de simulation sauf si sigmaStep est fixé", DOC_VT + " ; code cfmodels/MSCFModel_Krauss.cpp", "dawdle2()", 2026, "défaut logiciel")
P("sumo.passenger.speedFactor", "facteur multiplicatif de la limite de vitesse (vitesse désirée individuelle)", POP,
  "normale tronquée normc(moyenne, écart-type, min, max)", {"moyenne": 1.0, "ecart_type": 0.1, "min": 0.2, "max": 2.0}, "-",
  "tiré une fois par véhicule ; ~95 % entre 0,8 et 1,2 × limite (doc)", DOC_VT, "§ Speed Distributions", 2026, "défaut logiciel")
P("sumo.step_length", "pas de simulation par défaut (= temps de réaction implicite)", "SUMO (option --step-length)", "constante", {"valeur": 1.0}, "s",
  "actionStepLength = pas par défaut ; doc : le temps de réaction est égal au pas", "SUMO userdoc, Car-Following-Models/index.html § Reaction time", "§ Reaction time", 2026, "défaut logiciel")
P("sumo.integration", "schéma d'intégration par défaut", "SUMO", "catégorielle", {"valeur": "Euler semi-implicite (vitesse constante sur le pas)", "alternative": "ballistic (--step-method.ballistic)"}, "-",
  "doc : le ballistique est plus réaliste pour les grands pas (1 s)", "SUMO userdoc, Simulation/Basic_Definition.html § Defining the Integration Method", "§", 2026, "défaut logiciel")
for vc, a, d, ed, L, m in [("truck", 1.3, 4.0, 7.0, 7.1, 4500), ("trailer", 1.0, 4.0, 7.0, 16.5, 13000), ("bus", 1.2, 4.0, 7.0, 12.0, 12000),
                           ("motorcycle", 6.0, 10.0, 10.0, 2.2, 200), ("bicycle", 1.2, 3.0, 7.0, 1.6, 10)]:
    P(f"sumo.{vc}.dynamique", f"accel/decel/emergencyDecel/longueur/masse par défaut vClass {vc}", f"SUMO vClass {vc}", "constantes",
      {"accel": a, "decel": d, "emergencyDecel": ed, "length": L, "mass": m}, "m/s², m, kg", "valeurs par défaut (sources de la doc : wikis, colliseum…)", DOC_DEF, "tableaux", 2026, "défaut logiciel", "moyenne")

# Carrefours / feux
DOC_JM = DOC_VT + " (tableau « Junction Model Parameters »)"
for k, g, v, u, rem in [
    ("jmTimegapMinor", "marge temporelle minimale avant/après un prioritaire (non encore engagé)", 1.0, "s", "MSLink::blockedByFoe : lookAhead"),
    ("impatience", "impatience de base (volonté d'imposer un freinage au prioritaire)", 0.0, "-", "impatience = max(0, min(1, base + attente/time-to-impatience))"),
    ("jmStoplineGap", "distance d'arrêt avant une ligne de feu / prioritaire", 1.0, "m", ""),
    ("jmStoplineGapMinor", "distance d'arrêt avant une ligne non prioritaire", 0.0, "m", ""),
    ("jmCrossingGap", "distance minimale à un piéton se dirigeant vers le conflit", 10.0, "m", ""),
    ("jmDriveAfterYellowTime", "franchissement volontaire du jaune", -1, "s", "désactivé : seuls les véhicules incapables de s'arrêter passent"),
    ("jmDriveAfterRedTime", "franchissement volontaire du rouge", -1, "s", "désactivé"),
    ("jmIgnoreFoeProb", "probabilité d'ignorer un prioritaire", 0.0, "-", ""),
]:
    P(f"sumo.jm.{k}", g, "SUMO tous véhicules", "constante", {"valeur": v}, u, rem or "défaut", DOC_JM, "tableau", 2026, "défaut logiciel")
P("sumo.jm.jmStopSignWait", "durée d'arrêt minimale au STOP", "SUMO tous véhicules", "constante", {"valeur": "1 pas de simulation"}, "s",
  "mesuré : 0,1 s au pas 0,1 s (S3 variante STOP)", DOC_JM, "tableau", 2026, "défaut logiciel")
P("sumo.time_to_impatience", "temps pour que l'impatience passe de 0 à 1", "SUMO (option --time-to-impatience)", "constante", {"valeur": 180},
  "s", "la description de l'option dans MSFrame.cpp annonce 300 s mais la valeur codée est 180 s (doc userdoc : 180 s)", "code src/microsim/MSFrame.cpp l. 532-533 ; userdoc § Impatience", "l. 532", 2026, "défaut logiciel", "moyenne")
P("sumo.tls_yellow_min_decel", "décélération minimale admise pour s'arrêter au jaune/rouge", "SUMO (option --tls.yellow.min-decel)", "constante", {"valeur": 3.0,
  "regle": "stopDecel = max(min(3,0 ; emergencyDecel) ; decel) ; s'arrête si distance > brakeGap(v, decel)"}, "m/s²",
  "décision binaire déterministe", "code MSFrame.cpp l. 513 ; MSVehicle.cpp l. 2792-2797 et 3766-3773", "lignes citées", 2026, "défaut logiciel")
P("sumo.turn_speed_factor", "vitesse limite en virage dans le carrefour : sqrt(R × facteur)", "SUMO (netconvert --junctions.limit-turn-speed)", "constante", {"valeur": 5.5},
  "m/s² (accélération latérale implicite)", "v_virage = sqrt(5,5 R) ; plafonnée à la moyenne des vitesses amont/aval", "SUMO userdoc, Simulation/Intersections.html § Speed while passing the Intersection", "§", 2026, "défaut logiciel")
P("sumo.friction_device", "facteur de réduction de vitesse selon le frottement perçu", "SUMO device.friction", "fonction déterministe + bruit gaussien",
  {"formule": "facteur = -0,3491 f² + 0,8922 f + 0,4493", "stdDev_bruit": 1.0, "offset": 0.0}, "-", "f = coefficient de frottement de la voie (défaut 1)", "SUMO userdoc, Simulation/Friction.html", "§ Vehicle Behavior", 2026, "défaut logiciel")
P("sumo.driverstate", "erreurs de perception (processus d'Ornstein-Uhlenbeck) — device driverstate", "SUMO (Krauss, IDM, ACC, CACC)", "processus OU",
  {"initialAwareness": 1.0, "errorTimeScaleCoefficient": 100.0, "errorNoiseIntensityCoefficient": 0.2, "speedDifferenceErrorCoefficient": 0.15,
   "headwayErrorCoefficient": 0.75, "freeSpeedErrorCoefficient": 0.0, "minAwareness": 0.1}, "-", "aucun effet tant que awareness = 1 (défaut)",
  "SUMO userdoc, Driver_State.html", "tableau", 2026, "défaut logiciel")
# EIDM
EIDM = {"treaction": (0.5, "s"), "tpreview": (4.0, "s"), "tPersDrive": (3.0, "s"), "tPersEstimate": (10.0, "s"), "coolness": (0.99, "-"),
        "sigmaleader": (0.02, "-"), "sigmagap": (0.10, "-"), "jerkmax": (3.0, "m/s³"), "epsilonacc": (1.0, "m/s²"), "taccmax": (1.2, "s"),
        "Mflatness": (2.0, "-"), "Mbegin": (0.7, "-"), "delta": (4.0, "-"), "stepping": (0.25, "s")}
for k, (v, u) in EIDM.items():
    P(f"sumo.eidm.{k}", f"paramètre EIDM {k}", "SUMO carFollowModel=EIDM", "constante", {"valeur": v}, u, "défaut (identique doc et code)",
      "code cfmodels/MSCFModel_EIDM.cpp l. 56-71 ; userdoc tableau CF", "l. 56-71", 2026, "défaut logiciel")
P("sumo.eidm.sigmaerror", "amplitude de l'erreur de conduite EIDM", "SUMO carFollowModel=EIDM", "constante", {"valeur_code": 0.04, "valeur_doc": 0.10}, "-",
  "INCOHÉRENCE doc/code : le code 1.27.1 utilise 0,04", "code MSCFModel_EIDM.cpp l. 66 ; userdoc tableau CF", "l. 66", 2026, "défaut logiciel", "faible")
P("sumo.w99", "paramètres Wiedemann 99 (CC1-CC9) ; CC0 = minGap", "SUMO carFollowModel=W99", "constantes",
  {"cc1_s": 1.30, "cc2_m": 8.00, "cc3_s": -12.00, "cc4_ms": -0.25, "cc5_ms": 0.35, "cc6": 6.00, "cc7_ms2": 0.25, "cc8_ms2": 2.00, "cc9_ms2": 1.50}, "mixtes",
  "défauts SUMO (proches des défauts Vissim d'après la doc)", "code MSCFModel_W99.cpp l. 51-61 ; userdoc tableau CF", "l. 51-61", 2026, "défaut logiciel")
P("sumo.wiedemann74", "paramètres Wiedemann (2 paramètres)", "SUMO carFollowModel=Wiedemann", "constantes",
  {"security": 0.5, "estimation": 0.5, "AX": "length + 1 + 2·security", "CX": "25·(1 + security + estimation)", "D_MAX_m": 150}, "mixtes", "défauts",
  "code MSCFModel_Wiedemann.cpp l. 45-60", "l. 45-60", 2026, "défaut logiciel")
P("sumo.acc", "gains du modèle ACC (Milanés & Shladover 2014)", "SUMO carFollowModel=ACC", "constantes",
  {"speedControlGain": -0.4, "gapClosingControlGainSpeed": 0.8, "gapClosingControlGainSpace": 0.04, "gapControlGainSpeed": 0.07,
   "gapControlGainSpace": 0.23, "collisionAvoidanceGainSpace": 0.8, "collisionAvoidanceGainSpeed": 0.23, "collisionAvoidanceOverride_ms": 2.0}, "mixtes",
  "modes : vitesse (> 120 m), rapprochement (< 100 m), écart, anticollision", "SUMO userdoc, Car-Following-Models/ACC.html et tableau CF", "§", 2026, "défaut logiciel")
P("sumo.lc2013", "paramètres de changement de voie LC2013", "SUMO laneChangeModel=LC2013", "constantes",
  {"lcStrategic": 1.0, "lcCooperative": 1.0, "lcSpeedGain": 1.0, "lcKeepRight": 1.0, "lcSpeedGainRight": 0.1, "lcAssertive": 1.0,
   "lcStrategicLookahead_m": 3000, "lcSpeedGainRemainTime_s": 20, "lcOvertakeRight": 0.0, "lcSigma": 0.0,
   "seuil_gain_vitesse_gauche": "0,2/lcSpeedGain (gain relatif cumulé)", "seuil_droite": "(0,2/lcSpeedGainRight)/lcSpeedGain",
   "KEEP_RIGHT_TIME_s": 5.0, "CUT_IN_LEFT_SPEED_THRESHOLD_ms": 27.0, "facteur_urgence_strategique": {"gauche": 10, "droite": 20}}, "mixtes",
  "changement de voie instantané (sans sous-voies ni --lanechange.duration)",
  "userdoc tableau LC ; code lcmodels/MSLCM_LC2013.cpp l. 48-78, 145-149 ; Erdmann 2014 p. 4", "l. 48-149 ; p. 4", 2014, "défaut logiciel")
P("sumo.sl2015", "paramètres latéraux du modèle à sous-voies SL2015", "SUMO laneChangeModel=SL2015", "constantes",
  {"minGapLat_m": 0.6, "maxSpeedLat_ms": 1.0, "lcAccelLat_ms2": 1.0, "lcPushy": 0.0, "lcImpatience": 0.0, "lcSublane": 1.0, "latAlignment": "center"}, "mixtes",
  "activé par --lateral-resolution", "SUMO userdoc, SublaneModel.html et tableau LC", "§", 2026, "défaut logiciel")

# ------------------------------------------------------------------ Littérature : poursuite / changement de voie
P("idm.treiber2000", "paramètres IDM « typiques » (autoroute)", "trafic autoroutier allemand (calage sur états congestionnés observés)", "constantes",
  {"v0_kmh": 120, "T_s": 1.6, "a_ms2": 0.73, "b_ms2": 1.67, "delta": 4, "s0_m": 2.0, "s1_m": 0.0, "longueur_m": 5.0}, "mixtes",
  "a = 0,73 m/s² ⇔ 0-100 km/h en 45 s (« accélérations quotidiennes ») ; T = 1,6 s légèrement sous la recommandation allemande 1,8 s",
  "Treiber, Hennecke, Helbing, Phys. Rev. E 62 (2000), arXiv cond-mat/0002177", "tableau I p. 29 ; p. 9", 2000, "calage")
P("acc_idm.kesting2010", "paramètres IDM / ACC-IDM (CAH, coolness)", "voiture / poids lourd (simulation)", "constantes",
  {"voiture": {"v0_kmh": 120, "delta": 4, "T_s": 1.5, "s0_m": 2.0, "a_ms2": 1.4, "b_ms2": 2.0, "c": 0.99},
   "poids_lourd": {"v0_kmh": 85, "delta": 4, "T_s": 2.0, "s0_m": 4.0, "a_ms2": 0.7, "b_ms2": 2.0, "c": 0.99}}, "mixtes",
  "c réaliste dans [0,95 ; 1,00]", "Kesting, Treiber, Helbing, Phil. Trans. R. Soc. A 368 (2010), arXiv 0912.3613", "tableau 1 p. 4 ; p. 6", 2010, "estimation")
P("hdm.treiber2006", "extensions « conducteur humain » (HDM)", "simulations", "constantes / plages",
  {"temps_reaction_s": [0.0, 2.0], "vehicules_anticipes_na": [1, 7], "Vs_erreur_relative_distance": 0.05, "rc_erreur_inverse_TTC_par_s": 0.01, "tau_correlation_erreurs_s": 20,
   "IDM_sous_jacent": {"v0_kmh": 128, "T_s": 1.1, "a_ms2": 1.0, "b_ms2": 1.5, "s0_m": 2.0}}, "mixtes",
  "erreurs = processus de Wiener corrélés ; s_est = s·exp(Vs·w_s) ; Δv_est = Δv + s·rc·w_Δv", "Treiber, Kesting, Helbing, Physica A 360 (2006), arXiv cond-mat/0404736", "tableau 1 p. 9 ; éq. 3-7 p. 5-6", 2006, "estimation")
P("idm.calage_stuttgart2008", "IDM calé sur 3 trajectoires radar (ville, Stuttgart, 1995, heure de pointe)", "3 conducteurs, route urbaine à une voie", "plage (min-max sur 3 jeux × 3 critères)",
  {"T_s": [1.03, 1.51], "s0_m": [1.04, 3.40], "a_ms2": [0.956, 1.58], "b_ms2": [0.614, 3.73], "erreur_calage_pc": [11, 29]}, "mixtes",
  "ajouter un temps de réaction explicite n'améliore pas l'ajustement (anticipation) ; variabilité intra-conducteur dominante",
  "Kesting & Treiber, TRR 2088 (2008), arXiv 0803.4063", "tableau 1 p. 7 ; p. 1", 2008, "calage")
P("idm.calage_shanghai2018", "IDM calé par conducteur (SH-NDS, voies rapides urbaines)", "42 conducteurs chinois, 2 100 périodes de poursuite (161 055 km)", "empirique (moyenne, médiane, écart-type, p5, p95)",
  {"a_ms2": {"moyenne": 0.8418, "mediane": 0.8088, "ecart_type": 0.2775, "p5": 0.5024, "p95": 1.3222},
   "v0_kmh": {"moyenne": 105.63, "mediane": 101.93, "ecart_type": 24.74, "p5": 74.0, "p95": 150.0},
   "delta": {"moyenne": 3.52, "mediane": 1.5, "ecart_type": 3.62, "p5": 1.0, "p95": 10.0},
   "b_ms2": {"moyenne": 0.815, "mediane": 0.612, "ecart_type": 0.725, "p5": 0.118, "p95": 2.362},
   "s0_m": {"moyenne": 1.555, "mediane": 1.381, "ecart_type": 0.963, "p5": 0.10, "p95": 3.425},
   "T_s": {"moyenne": 0.878, "mediane": 0.946, "ecart_type": 0.334, "p5": 0.356, "p95": 1.432}}, "mixtes",
  "erreur de calage 19-25 % (5 modèles) ; erreur de validation inter-conducteurs 31 % vs intra 19 % ; IDM meilleur que W99",
  "Zhu, Wang, Tarko, Fang, Transp. Res. C 93 (2018), arXiv 1811.06395", "tableau 2 p. 14 ; p. 17-18", 2018, "calage")
P("gipps.reaction_shanghai2018", "temps de réaction du modèle de Gipps calé", "42 conducteurs (SH-NDS)", "empirique",
  {"moyenne": 1.2214, "mediane": 1.20, "ecart_type": 0.4831, "p5": 0.50, "p95": 2.04}, "s", "paramètre calé (pas une mesure directe de TR)",
  "Zhu et al. 2018, arXiv 1811.06395", "tableau 2 p. 14", 2018, "calage")
P("mobil.kesting2007", "paramètres MOBIL", "simulations IDM + MOBIL", "constantes",
  {"politesse_p": [0.0, 1.0], "seuil_delta_a_th_ms2": 0.1, "b_safe_ms2": 4.0, "biais_voie_droite_ms2": 0.3, "b_max_sec_ms2": 9.0}, "m/s²",
  "b_safe nettement inférieur à ~9 m/s² (décélération max sur sol sec)", "Kesting, Treiber, Helbing, TRR 1999 (2007), préprint", "tableau 1 p. 10 ; p. 6", 2007, "estimation")
P("eidm.demarrage_salles2020", "démarrage depuis l'arrêt (véhicules instrumentés)", ">2 000 démarrages, moteurs thermiques, véhicules d'essai (Stuttgart)", "moyennes",
  {"t_pour_1ms_s": 0.8, "t_pour_amax_s": 2.3, "ecart_type_accel_ms2": 0.5}, "s ; m/s²", "ces temps comptent depuis le début du mouvement",
  "Salles, Kaufmann, Reuss, SUMO User Conf. 2020", "p. 14", 2020, "mesure", "moyenne")
P("eidm.amax_salles2020", "accélération max IDM : EIDM vs littérature", "comparaison de jeux de paramètres", "plages",
  {"EIDM_ms2": [2.5, 3.5], "Kovacs2016_ms2": 1.6, "Kesting2008_ms2": [1.5, 1.6], "Treiber_Kesting2013b_ms2": 1.0, "Dallmeyer2014_ms2": 1.5, "Treiber_Kesting2013a_ms2": 1.4}, "m/s²",
  "le calage sur données autoroutières donne des a faibles (aérodynamique)", "Salles et al. 2020", "tableau 4 p. 19", 2020, "calage", "moyenne")
P("file.jiang2014", "écart-type de vitesse par rang dans une file de 25 voitures", "expérience sur route ouverte (Chine), meneur à 50 km/h", "lecture graphique",
  C.REFERENCES["jiang_sv_50kmh"]["valeur"], "m/s", "croissance linéaire à basse vitesse, concave à vitesse plus élevée (p. 6)",
  "Jiang et al., PLoS ONE 9(4) e94351 (2014)", "fig. 5D p. 7 ; p. 6", 2014, "mesure", "moyenne")
P("file.sugiyama2008", "formation spontanée d'un bouchon sans goulot", "22 véhicules sur un circuit de 230 m", "observation",
  {"n_vehicules": 22, "circonference_m": 230}, "-", "bouchon apparu puis se propageant sur le circuit", "Sugiyama et al., New J. Phys. 10, 033001 (2008)", "p. 3-4", 2008, "mesure")
# Réglementaire
P("r157.ccdm", "conducteur « compétent et prudent » CCDM (ONU R157, annexe 3) — coupure de trajectoire", "modèle de référence réglementaire", "constantes",
  {"zone_errance_m": 0.375, "temps_perception_s": 0.4, "delai_freinage_s": 0.75, "TTC_declenchement_s": 2.0, "decel_ms2": 7.6, "montee_s": 0.6, "jerk_ms3": 12.65}, "mixtes",
  "valeurs relevées par Olleja et al. dans R157 ; R157 non téléchargeable (HTTP 403 sur unece.org)", "Olleja, Markkula, Bärgman 2024, arXiv 2406.09493", "p. 5-6", 2024, "norme", "moyenne")
P("r157.fsm", "Fuzzy Safety Model (ONU R157)", "modèle de référence réglementaire", "constantes",
  {"decel_confort_ms2": 4.0, "decel_max_ms2": 6.0, "jerk_ms3": 12.65}, "m/s², m/s³", "freinage proportionnel au risque (métriques PFS/CFS)",
  "Olleja et al. 2024, arXiv 2406.09493", "p. 6", 2024, "norme", "moyenne")
P("r157.validation_olleja2024", "comparaison CCDM/FSM vs conducteurs réels (38 quasi-accidents SHRP2)", "38 quasi-accidents de coupure SHRP2", "résultats",
  {"CCDM": "freinage plus tardif que l'humain ; collisions dans 3 quasi-accidents", "FSM_reagit_avant_humain_pc": 74, "FSM_mediane_avance_s": 0.7}, "-",
  "les modèles réglementaires ne reproduisent pas le comportement humain", "Olleja et al. 2024, arXiv 2406.09493", "p. 1, 9", 2024, "mesure")
# Dynamique
P("vehicule.bicyclette_cinematique_validite", "domaine de validité du modèle bicyclette cinématique", "véhicule particulier", "seuil",
  {"a_lat_max": "0,5 µ g"}, "m/s²", "au-delà, utiliser un modèle dynamique (dérives des pneus)", "Polack et al. 2018, arXiv 1804.08290 (renvoie à Polack et al. IV 2017)", "p. 1-2", 2018, "estimation")
# Normes FR / références de comparaison
for k, ref in C.REFERENCES.items():
    if k in ("temps_inter_idm_shanghai", "temps_inter_idm_stuttgart", "demarrage_salles", "jiang_sv_50kmh"):
        continue
    P(f"reference.{k}", k.replace("_", " "), "voir conditions", "valeur(s)", {"valeur": ref["valeur"]}, ref["unite"], ref["nature"], ref["source"], "voir doc", None,
      "norme" if ("norme" in ref["nature"] or "dimensionnement" in ref["nature"]) else ("mesure" if "mesure" in ref["nature"] else "estimation"))
P("reference.cerema_TPR", "temps de perception-réaction de conception", "conception routière FR", "constante", {"valeur": 1.8}, "s",
  "distance d'arrêt d_a = (T_PR·v + (1+m_c)·v²/(2g(γv+p)))·K", "Cerema, Révision des règles sur la visibilité (oct. 2018)", "p. 13", 2018, "norme")

# ------------------------------------------------------------------ CARLA 0.9.15 / MassTraffic
P("carla_tm.constantes", "constantes du Traffic Manager CARLA 0.9.15", "PNJ CARLA en autopilot", "constantes",
  {"distance_marge_defaut_m": 2.0, "distance_suivi": "2,0 s × v + 2,0 m", "vitesse_approche_relative_kmh": 12, "marge_freinage_critique_m": 0.2,
   "ralentissement_max_par_trame": "8 % de v", "vitesse_virage": "sqrt(R × 0,6 × 9,81)", "vitesse_cible_feu_kmh": 15, "vitesse_cible_stop_kmh": 10,
   "attente_min_carrefour_non_signale_s": 2.0, "un_seul_vehicule_dans_carrefour_non_signale": True, "ecart_limite_vitesse_global_pc_code": 0.0, "ecart_limite_doc": "« 70 % de la limite » (doc) — incohérent avec le code (0 %)",
   "PID_long": [12.0, 0.05, 0.02], "PID_lat": [4.0, 0.02, 0.08], "throttle_max": 0.85, "frein_max": 0.7, "dt_PID_s": 0.05}, "mixtes",
  "carrefours non signalés : premier arrivé premier servi, attentes fixes (doc)", "CARLA 0.9.15 : Constants.h, Parameters.h l. 47 et 77, MotionPlanStage.cpp l. 308-388 et 405-421, TrafficLightStage.cpp l. 119-128, adv_traffic_manager.md",
  "lignes citées", 2023, "défaut logiciel")
P("masstraffic.reglages", "réglages par défaut MassTraffic (City Sample UE 5.7), convertis en SI", "PNJ MassTraffic", "uniforme par véhicule (RandomFraction) + bruit",
  {"accel_ms2": 3.0, "variance_accel_pc": 10, "decel_ms2": 20.0, "variance_decel_pc": 10, "variance_sous_limite_pc": 35, "bruit_vitesse_pc": 10,
   "temps_ideal_vehicule_suivant_s": [1.5, 2.0], "distance_min_vehicule_suivant_m": [0.8, 5.0], "distance_arret_feu_m": [0.5, 3.5],
   "temps_freinage_stop_s": 4.0, "duree_jaune_s": 2.0, "facteur_vitesse_virage": 0.5, "decision_changement_voie_s": [30, 60], "duree_changement_voie_s": 3.0}, "mixtes",
  "modèle cinématique de commande (cible de vitesse + PID), pas de modèle de conducteur", "Plugins/Traffic/Source/MassTraffic/Public/MassTrafficSettings.h (l. 96-400) et MassTrafficIntersections.h l. 321-323",
  "lignes citées", None, "défaut logiciel", "moyenne")

# ------------------------------------------------------------------ Mesures en simulation (ce dépôt)
def charge(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))["resultats"]
    except Exception:
        return None


R = C.RACINE_SORTIE
s1, s2, s3 = charge(R / "S1_file_route_droite/resultats/S1_resume.json"), charge(R / "S2_arret_feu/resultats/S2_resume.json"), charge(R / "S3_insertion_cedez/resultats/S3_resume.json")
sens = charge(R / "S3_insertion_cedez/resultats/S3_sensibilite_jm.json")
reana = charge(R / "S3_insertion_cedez/resultats/S3_reanalyse_creneaux.json")   # relecture adverse du 17/10/2026
DOCSIM = "Ce dépôt : recon/trafic/etat_art_sumo (SUMO 1.27.1), résultats dans DocRoute/17_.../03_Modeles_Existants/scenarios_sumo"
if s1:
    for cfg, r in s1.items():
        P(f"sim.S1.{cfg}", "file de 10 véhicules à 50 km/h (meneur piloté)", f"SUMO {r['config']['libelle']}, {r['graines']} graines", "empirique",
          {"temps_inter_net_s": r["temps_inter_net_croisiere_s"], "jerk_abs_ms3": r["jerk_abs_ms3"], "part_pas_jerk_sup_1.5": r["part_pas_jerk_sup_1.5"],
           "distance_arret_m": r["distance_arret_m"], "ecart_type_vitesse_par_rang_ms": {k: v["p50"] for k, v in r["ecart_type_vitesse_croisiere_par_rang_ms"].items()},
           "retard_redemarrage_par_rang_s": {k: v["p50"] for k, v in r["retard_redemarrage_vs_predecesseur_s"].items()}},
          "s, m/s³, m, m/s", "suiveurs speedFactor 1,2 sans dispersion", DOCSIM, "S1_resume.json", 2026, "mesure en simulation")
if s2:
    for cfg, r in s2.items():
        P(f"sim.S2.{cfg}", "feu isolé 50 km/h : jaune, freinage, écoulement", f"SUMO {r['config']['libelle']}, {r['graines']} graines", "empirique",
          {"TTS_max_passage_s": r["tts_max_passage_s"], "TTS_min_arret_s": r["tts_min_arret_s"], "decel_max_premier_arret_ms2": r["decel_max_premier_arret_ms2"],
           "intervalle_saturation_s": r["intervalle_saturation_rangs5_12_s"], "debit_saturation_veh_h": r["debit_saturation_veh_h"],
           "temps_perdu_demarrage_s": r["temps_perdu_demarrage_rangs1_4_s"], "franchissements_rouge": r["franchissements_au_rouge"]},
          "s, m/s², véh/h", "cycle 60 s, jaune 3 s, arrivées de Poisson 720 véh/h", DOCSIM, "S2_resume.json", 2026, "mesure en simulation")
if s3:
    for cle, r in s3.items():
        P(f"sim.S3.{cle.replace('/', '.')}", "insertion TAD depuis voie secondaire (créneau critique)", f"SUMO {r['config']['libelle']}, {r['variante']}, {r['graines']} graines", "log-normale (MLE Troutbeck) + empirique",
          {"creneau_critique_MLE_arretes": r["arretes_creneau_critique_mle_lognormal"], "creneau_accepte_arretes_s": r["arretes_creneau_accepte_s"],
           "plus_grand_refuse_arretes_s": r["arretes_plus_grand_refuse_s"], "attente_s": r["attente_s"], "duree_arret_ligne_s": r["duree_arret_ligne_s_si_arret"],
           "part_arret_complet": r["part_arret_complet"],
           "creneau_critique_MLE_depuis_arret_entree": ((reana or {}).get(cle, {}).get("B") or {}).get("mle"),
           "creneau_critique_MLE_depuis_arret_point_conflit": ((reana or {}).get(cle, {}).get("C") or {}).get("mle")},
          "s", "flux prioritaire 600 véh/h/sens, secondaire 180 véh/h", DOCSIM, "S3_resume.json", 2026, "mesure en simulation")
if sens:
    for nom, r in sens.items():
        P(f"sim.S3.sensibilite.{nom}", "créneau critique SUMO selon impatience / jmTimegapMinor", f"SUMO Krauss pas 0,1 s, cédez, {r['attributs_vType']}", "log-normale (MLE)",
          {"creneau_critique_MLE": r["arretes_creneau_critique_mle_lognormal"], "accel_min_prioritaire_suivant_ms2": r["accel_min_prioritaire_suivant_ms2"]},
          "s, m/s²", "3 graines", DOCSIM, "S3_sensibilite_jm.json", 2026, "mesure en simulation")


def main():
    doc = {"description": "Paramètres et valeurs de référence des modèles existants (volet 03, état de l'art). Généré par recon/trafic/etat_art_sumo/parametres_reference.py.",
           "format_entree": "{id, grandeur, population, loi, parametres, unite, conditions, source:{doc, page, annee}, nature, confiance}",
           "n_entrees": len(E), "entrees": E}
    for p in SORTIES:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(p, len(E))


if __name__ == "__main__":
    main()
