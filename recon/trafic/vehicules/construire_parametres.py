"""Construit vehicules_parametres.json (volet « véhicules » du modèle de trafic).

Entrées (toutes produites et documentées dans D:/DocRoute/17_Modele_Vehicules_Conducteurs/01_Vehicules/) :
  donnees/sdes_parc_2026.json              parc au 1er janvier 2026 (SDES, converti depuis les xlsx)
  donnees/adac_mesures.json                10 voitures, mesures ADAC + données constructeur
  donnees/validation_dynamique.json        sortie de valider_vehicules.py (calage k, a_lancement)
  donnees/hdv_france_2019_2023_stats.json  poids lourds neufs France (AEE, règlement 2018/956)
  sources/eea_co2_cars_fr/*.json           réponses Discodata AEE (voitures 2024, 2021 ; VUL 2021)
Sorties :
  01_Vehicules/vehicules_parametres.json
  D:/ClaudeCode_RoadCreation/assets/specs/trafic/vehicules_parametres.json (copie identique)

Chaque paramètre suit la forme machine demandée :
  {id, grandeur, population, loi, parametres, unite, conditions, source:{doc, page, annee}, confiance, nature}
nature : norme | mesure | donnee_administrative | derive | estimation | convention.
Usage : python -I recon/trafic/vehicules/construire_parametres.py
"""
from __future__ import annotations

import json
import math
import re
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path

VOLET = Path(r"D:\DocRoute\17_Modele_Vehicules_Conducteurs\01_Vehicules")
DON = VOLET / "donnees"
SRC = VOLET / "sources"
COPIE = Path(r"D:\ClaudeCode_RoadCreation\assets\specs\trafic\vehicules_parametres.json")
DOCROUTE10 = "D:/DocRoute/10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/sources/"

# ----------------------------------------------------------------------------- sources
SOURCES = {
    "SDES2026": {"titre": "SDES, Données sur le parc automobile français au 1er janvier 2026 (VP, VUL, PL, autobus et autocars ; RSVERO, données provisoires)", "annee": 2026, "url": "https://www.statistiques.developpement-durable.gouv.fr/donnees-sur-le-parc-automobile-francais-au-1er-janvier-2026", "licence": "licence ouverte (décret n° 2017-638)", "fichier": "sources/sdes_parc_2026/", "type": "donnee_administrative"},
    "ONISR2024": {"titre": "ONISR, La sécurité routière en France, bilan de l'année 2024 (publié en 2025), chapitre « La circulation routière » (d'après SDES, bilan de la circulation 2024)", "annee": 2025, "url": "https://www.onisr.securite-routiere.gouv.fr/sites/default/files/2025-09/Bilan%20SR%202024%20version%20site%20internet%2012%20septembre.pdf", "licence": "site public de l'État (réutilisation avec mention de la source)", "fichier": "sources/onisr/ONISR_Bilan_SR_2024.pdf", "type": "donnee_administrative"},
    "AEE_VP": {"titre": "AEE, Monitoring of CO2 emissions from passenger cars, règlement (UE) 2019/631 : immatriculations France 2024 (table co2cars_2024Fv30, finale) et 2021 (co2cars, Year=2021, Status=F)", "annee": 2025, "url": "https://discodata.eea.europa.eu/sql", "licence": "CC BY 4.0 (avis juridique AEE)", "fichier": "sources/eea_co2_cars_fr/", "type": "donnee_administrative"},
    "AEE_VUL": {"titre": "AEE, Monitoring of CO2 emissions from vans : immatriculations France 2021 (table co2vans, Status=P)", "annee": 2023, "url": "https://discodata.eea.europa.eu/sql", "licence": "CC BY 4.0", "fichier": "sources/eea_co2_cars_fr/fr2021_vans_*.json", "type": "donnee_administrative"},
    "AEE_HDV": {"titre": "AEE, Monitoring of CO2 emissions from heavy-duty vehicles, période 2019-2023 (extrait du 24/04/2025), lignes immatriculées en France et appariées aux données constructeur (VECTO)", "annee": 2025, "url": "https://discomap.eea.europa.eu/App/CO2HDV/HDV_CO2Emission_VehicleExtract_24042025.csv", "licence": "CC BY 4.0", "fichier": "sources/eea_co2_hdv/HDV_extrait_France_2019_2023.csv", "type": "donnee_administrative"},
    "ADAC": {"titre": "ADAC e.V., Autotests (10 PDF, 2020-2026) : Clio V TCe 90, 208 PureTech 100, Sandero III TCe 90, Captur II MH 160, 2008 PureTech 130, e-208 156, Kangoo III E-Tech EV45, 3008 III Hybrid 136, ë-C3, Model Y (2025)", "annee": 2026, "url": "https://assets.adac.de/image/upload/Autodatenbank/Autotest/", "licence": "tous droits réservés ; copie locale interne, valeurs factuelles seulement", "fichier": "sources/adac_autotests/", "type": "mesure"},
    "ADAC_CAT": {"titre": "ADAC Autokatalog (pages techniques constructeur des mêmes modèles : empattement, diamètre de braquage)", "annee": 2026, "url": "https://www.adac.de/rund-ums-fahrzeug/autokatalog/", "licence": "tous droits réservés ; consultation", "fichier": None, "type": "donnee_constructeur"},
    "R13H": {"titre": "Règlement ONU n° 13-H (freinage des voitures particulières), version consolidée 02 série, JO UE L 2026/502 du 13/04/2026", "annee": 2026, "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202600502", "licence": "EUR-Lex, réutilisation autorisée (décision 2011/833/UE)", "fichier": "sources/reglementation/ONU_R13H_UE_2026_502.pdf", "type": "norme"},
    "R13": {"titre": "Règlement ONU n° 13 (freinage des véhicules M, N, O), 11e série, suppl. 13, JO UE L 42 du 18/02/2016 [2016/194]", "annee": 2016, "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:42016X0218(01)", "licence": "EUR-Lex, réutilisation autorisée", "fichier": "sources/reglementation/ONU_R13_UE_2016_194.pdf", "type": "norme"},
    "R78": {"titre": "Règlement ONU n° 78 (freinage des véhicules L1 à L5), 03 série, JO UE L 24 du 30/01/2015 [2015/145]", "annee": 2015, "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:42015X0130(01)", "licence": "EUR-Lex, réutilisation autorisée", "fichier": "sources/reglementation/ONU_R78_UE_2015_145.pdf", "type": "norme"},
    "D9653": {"titre": "Directive 96/53/CE (poids et dimensions maximaux), version consolidée du 14/08/2019", "annee": 2019, "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:01996L0053-20190814", "licence": "EUR-Lex, réutilisation autorisée", "fichier": "sources/reglementation/UE_Directive_96_53_consolidee_20190814_FR.pdf", "type": "norme"},
    "D200285": {"titre": "Directive 2002/85/CE modifiant la directive 92/6/CEE (limiteurs de vitesse)", "annee": 2002, "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32002L0085", "licence": "EUR-Lex, réutilisation autorisée", "fichier": "sources/reglementation/UE_Directive_2002_85_limiteurs_vitesse_FR.pdf", "type": "norme"},
    "R1230": {"titre": "Règlement (UE) n° 1230/2012 (masses et dimensions des véhicules à moteur)", "annee": 2012, "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R1230", "licence": "EUR-Lex, réutilisation autorisée", "fichier": "sources/reglementation/UE_Reglement_1230_2012_masses_dimensions_FR.pdf", "type": "norme"},
    "R168": {"titre": "Règlement (UE) n° 168/2013 (réception des véhicules à deux ou trois roues et quadricycles), annexe I", "annee": 2013, "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32013R0168", "licence": "EUR-Lex, réutilisation autorisée", "fichier": "sources/reglementation/UE_Reglement_168_2013_categories_L_FR.pdf", "type": "norme"},
    "R2020_740": {"titre": "Règlement (UE) 2020/740 (étiquetage des pneumatiques), annexe I", "annee": 2020, "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32020R0740", "licence": "EUR-Lex, réutilisation autorisée", "fichier": "sources/reglementation/UE_Reglement_2020_740_etiquetage_pneus_FR.pdf", "type": "norme"},
    "D2019_1082": {"titre": "Décret n° 2019-1082 du 23/10/2019 (engins de déplacement personnel), JORFTEXT000039272656 (lu sur Légifrance le 17/10/2026, version d'origine)", "annee": 2019, "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000039272656", "licence": "texte officiel", "fichier": None, "type": "norme"},
    "VSA90110": {"titre": "Cerema, Guide VSA 90/110 (voies structurantes d'agglomération), nov. 2014 (page imprimée = PDF - 2)", "annee": 2014, "url": None, "licence": "© Cerema, diffusion interdite sans accord (mention du PDF) ; source déjà présente dans DocRoute", "fichier": DOCROUTE10 + "Cerema_VSA_90_110_2014.pdf", "type": "norme"},
    "VISI2018": {"titre": "Cerema, Conception des routes et autoroutes – Révision des règles sur la visibilité et sur les rayons en angle saillant du profil en long, note technique du 1er octobre 2018 (page imprimée = PDF - 2)", "annee": 2018, "url": None, "licence": "source déjà présente dans DocRoute", "fichier": DOCROUTE10 + "Cerema_Regles_Visibilite_madoc.pdf", "type": "norme"},
    "ICTAVRU": {"titre": "Certu, ICTAVRU (instruction voies rapides urbaines), réédition 2009 (page imprimée = PDF - 2)", "annee": 2009, "url": None, "licence": "source déjà présente dans DocRoute", "fichier": DOCROUTE10 + "CERTU_ICTAVRU_2009.pdf", "type": "norme"},
    "VSA70": {"titre": "Certu, Guide VSA 70 – artères urbaines, janvier 2013", "annee": 2013, "url": None, "licence": "© Certu, « ne pas diffuser » ; source déjà présente dans DocRoute", "fichier": DOCROUTE10 + "CERTU_VSA70_Arteres_Urbaines_2013.pdf", "type": "norme"},
    "ARP2022": {"titre": "Cerema, Aménagement des routes principales (ARP), 2022 (page imprimée = PDF - 2)", "annee": 2022, "url": None, "licence": "source déjà présente dans DocRoute", "fichier": DOCROUTE10 + "Cerema_ARP_Amenagement_Routes_Principales_2022.pdf", "type": "norme"},
    "DOCROUTE10": {"titre": "DocRoute, dossier 10 (CONCEPTION_CARREFOURS.md § 6, PROFILS_EN_TRAVERS.md § 4.2) : véhicules de référence de CU p. 78, VU p. 142-144, CF p. 22, N05 p. 4", "annee": 2026, "url": None, "licence": "documentation interne", "fichier": "D:/DocRoute/10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/", "type": "norme"},
    "RVC": {"titre": "Cerema, Rendre sa voirie cyclable (2022), p. 17 et 45, d'après DocRoute 11_Cycles_Pietons_Accessibilite_TC/CYCLES.md § 2.2 (figure lue sur tuiles)", "annee": 2022, "url": None, "licence": "documentation interne", "fichier": "D:/DocRoute/11_Cycles_Pietons_Accessibilite_TC/CYCLES.md", "type": "norme"},
    "GREIBE2007": {"titre": "P. Greibe (Trafitec), Braking distance, friction and behaviour, Danish Road Directorate, juillet 2007 : 22 conducteurs (dont 6 professionnels), 2 voitures ABS (Fiat Punto, Opel Vectra), 3 pistes, 172 freinages d'urgence", "annee": 2007, "url": "https://trafitec.dk/wp-content/uploads/2024/02/Braking-distance-friction-and-driver-behaviour.pdf", "licence": "rapport public, tous droits réservés", "fichier": "sources/essais_freinage/Greibe_2007_Braking_distance_friction_behaviour.pdf", "type": "mesure"},
    "LI2023": {"titre": "T. Li, J. Kovaceva, M. Dozza, Modeling collision avoidance maneuvers for micromobility vehicles, Journal of Safety Research 87 (2023), doi:10.1016/j.jsr.2023.09.019 : 36 participants (13 F, 23 H, 31,5 ± 7,5 ans), vélo, VAE, 2 trottinettes, piste d essai (Suède)", "annee": 2023, "url": "https://research.chalmers.se/publication/537916/file/537916_Fulltext.pdf", "licence": "CC BY 4.0", "fichier": "sources/deux_roues_micromobilite/Chalmers_537916_bike_escooter_braking_steering.pdf", "type": "mesure"},
    "SIEBERT2021": {"titre": "F. W. Siebert et al., Braking bad – Ergonomic design and implications for the safe use of shared E-scooters, Safety Science 140 (2021) 105294 (manuscrit accepté)", "annee": 2021, "url": "https://depositonce.tu-berlin.de/bitstream/11303/13900/1/siebert_etal_2021.pdf", "licence": "CC BY-NC-ND 4.0", "fichier": "sources/deux_roues_micromobilite/Siebert_2021_escooter_braking.pdf", "type": "mesure"},
    "CITARO": {"titre": "Mercedes-Benz, The Citaro – technical data and equipment at a glance (GB, PDF 13 p.) et The eCitaro (int.)", "annee": 2025, "url": "https://www.mercedes-benz-bus.com/gb/en/models/citaro/facts-citaro.pdf ; https://www.mercedes-benz-bus.com/int/en/models/ecitaro/facts-ecitaro.pdf", "licence": "© Daimler Buses, document public ; valeurs factuelles", "fichier": "sources/constructeurs/", "type": "donnee_constructeur"},
    "TRANSBUS": {"titre": "transbus.org, fiches Iveco Bus Urbanway 12 et Urbanway 18 (base documentaire d'amateurs, données d'origine constructeur non citées)", "annee": 2026, "url": "https://www.transbus.org/construc/iveco_urbanway18.html", "licence": "© transbus.org ; consultation seulement (non téléchargé)", "fichier": None, "type": "donnee_constructeur"},
    "SUMO1271": {"titre": "Eclipse SUMO 1.27.1, documentation « Vehicle Type Parameter Defaults » (installée localement, page éditée le 05/04/2026)", "annee": 2026, "url": "https://sumo.dlr.de/docs/Vehicle_Type_Parameter_Defaults.html", "licence": "dépôt SUMO sous EPL-2.0 (non revérifié pour la documentation)", "fichier": "C:/Program Files (x86)/Eclipse/Sumo/doc/userdoc/Vehicle_Type_Parameter_Defaults.html", "type": "convention"},
}


def S(doc, page=None, annee=None):
    return {"doc": doc, "page": page, "annee": annee if annee is not None else SOURCES.get(doc, {}).get("annee")}


def P(id_, grandeur, population, loi, parametres, unite, conditions, source, confiance, nature):
    return {"id": id_, "grandeur": grandeur, "population": population, "loi": loi, "parametres": parametres,
            "unite": unite, "conditions": conditions, "source": source, "confiance": confiance, "nature": nature}


# ----------------------------------------------------------------------------- outils statistiques
def quantiles_ponderes(paires, qs=(0.05, 0.15, 0.25, 0.5, 0.75, 0.85, 0.95)):
    """paires = [(valeur, poids)] -> dict n, moyenne, écart-type, quantiles, lognormale ajustée."""
    p = sorted((float(v), float(w)) for v, w in paires if v is not None and w and float(v) > 0)
    W = sum(w for _, w in p)
    if W == 0:
        return None
    m = sum(v * w for v, w in p) / W
    sd = math.sqrt(sum(w * (v - m) ** 2 for v, w in p) / W)
    ml = sum(w * math.log(v) for v, w in p) / W
    sl = math.sqrt(sum(w * (math.log(v) - ml) ** 2 for v, w in p) / W)
    out = {"n": int(round(W)), "moyenne": round(m, 3), "ecart_type": round(sd, 3)}
    cum, i = 0.0, 0
    for q in qs:
        cible = q * W
        while i < len(p) and cum + p[i][1] < cible:
            cum += p[i][1]; i += 1
        out[f"p{int(q * 100)}"] = round(p[min(i, len(p) - 1)][0], 3)
    out["lognormale"] = {"mu_ln": round(ml, 4), "sigma_ln": round(sl, 4)}
    return out


def charger(p):
    return json.load(open(p, encoding="utf-8"))


# ----------------------------------------------------------------------------- SDES
def sdes_val(sdes, fichier, feuille, libelle, occurrence=0, annee="2026"):
    L = sdes["fichiers"][fichier][feuille]["lignes"]
    lignes = [l for l in L if l["libelle"].strip() == libelle] or [l for l in L if l["libelle"].strip().startswith(libelle)]
    return lignes[occurrence]["annees"].get(annee)


# ----------------------------------------------------------------------------- segments VP
SEGMENTS_VP = [  # (motif sur « MARQUE MODELE », segment) — convention [G] de ce volet, d'après la carrosserie ; ordre = priorité
    (r"MODEL 3|\b508\b|PASSAT|CLASSE C|\bA[4-7]\b|SERIE [3-5]|\b3[0-9]{2}[IDE]\b|\b5[0-9]{2}[IDE]\b|\bI[45]\b|CLASSE E|SUPERB|\bS60\b|\bS90\b|\bV60\b|\bV90\b|\bEQE\b|\bSEAL\b(?! U)|TAYCAN|CAMRY|INSIGNIA|ARTEON", "berline"),
    (r"MODEL Y|\b3008\b|\b5008\b|AUSTRAL|TIGUAN|C-HR|TUCSON|SPORTAGE|C5 AIRCROSS|QASHQAI|KUGA|ESPACE|RAV4|SCENIC|IX1|\bX1\b|DS ?7|RAFALE|ARKANA|SYMBIOZ|NIRO|KADJAR|KAROQ|ATECA|FORMENTOR|ENYAQ|ID\.4|ID\.5|\bQ3\b|\bGLA\b|XC60|XC40|\bGLC\b|KODIAQ|\bX[3-7]\b|RANGE ROVER|DEFENDER|DISCOVERY|COUNTRYMAN|GRANDLAND|\bEV[69]\b|IONIQ 5|BZ4X|\bQ[4-8]\b|\bEQA\b|\bEQB\b|\bGLB\b|\bGLE\b|\bZS\b|\bHS\b|SEAL U|ATTO|ELROQ|TERRAMAR|TAVASCAN|SORENTO|SANTA FE|X-TRAIL|ARIYA|OUTLANDER|COMPASS|RENEGADE|TONALE|\bEX40\b|\bEC40\b|\bIX3\b|MACAN|CAYENNE", "suv_c"),
    (r"\b2008\b|CAPTUR|DUSTER|YARIS CROSS|PUMA|T-ROC|C3 AIRCROSS|T-CROSS|KONA|JUKE|\b600\b|MOKKA|KAMIQ|TAIGO|AVENGER|ARONA|STONIC|VITARA|\bQ2\b|BAYON|DS ?3|EX30|\b500X\b|COMBO LIFE|CROSSLAND|S-CROSS|XCEED|\bASX\b|\bX2\b|JUNIOR|FRONTERA|C4 X|\bEV3\b|URBAN CRUISER|AYGO X", "suv_b"),
    (r"JOGGER|BERLINGO|RIFTER|TRAFIC|KANGOO|TOURAN|SHARAN|PROACE|SPACETOURER|TRAVELLER|MULTIVAN", "monospace_ludospace"),
    (r"\b308\b|GOLF|COROLLA|\bC4\b|E-C4|OCTAVIA|ID\.3|\b408\b|FOCUS|MEGANE|\bA3\b|DS ?4|MG4|\bI30\b|CEED|LEON|ASTRA|CIVIC|SERIE 1|CLASSE A|\b1[1-4][0-9][ID]\b|\bA ?1[0-9]{2}\b|BORN|\bMG5\b|PRIUS|\bLEAF\b|DOLPHIN(?! SURF)|\bSCALA\b", "compacte"),
    (r"CLIO|\b208\b|SANDERO|\bC3\b|E-C3|YARIS|POLO|CORSA|TWINGO|AYGO|\b500\b|FABIA|SWIFT|IBIZA|RENAULT 5|MG3|PICANTO|\bA1\b|\bI20\b|\bI10\b|SPRING|\b108\b|ZOE|\bUP\b|PANDA|\bC1\b|MICRA|\bRIO\b|\bJAZZ\b|IGNIS|\bMINI\b|COOPER|CITIGO|RENAULT 4|INSTER|DOLPHIN SURF|\bT03\b", "citadine"),
]


def segment_vp(mk, cn):
    nom = f"{mk} {cn}".upper()
    for motif, seg in SEGMENTS_VP:
        if re.search(motif, nom):
            return seg
    return None


SEGMENTS_VUL = [
    (r"KANGOO|PARTNER|BERLINGO|EXPRESS|DOBLO|PROACE CITY|TRANSIT CONNECT|COMBO|CADDY|CITAN|TOWNSTAR|RIFTER", "vul_petit"),
    (r"TRAFIC|EXPERT|JUMPY|TRANSIT CUSTOM|VITO|TRANSPORTER|VIVARO|TALENTO|PROACE|NV300|PRIMASTAR|SCUDO", "vul_moyen"),
    (r"MASTER|BOXER|JUMPER|SPRINTER|DUCATO|CRAFTER|MOVANO|TRANSIT|DAILY|NV400|INTERSTAR", "vul_grand"),
    (r"RANGER|HILUX|NAVARA|L200|D-MAX|AMAROK", "vul_pickup"),
]


def segment_vul(mk, cn):
    nom = f"{mk} {cn}".upper()
    for motif, seg in SEGMENTS_VUL:
        if re.search(motif, nom):
            return seg
    return None


# ----------------------------------------------------------------------------- construction
def construire():
    sdes = charger(DON / "sdes_parc_2026.json")
    adac = charger(DON / "adac_mesures.json")
    val = charger(DON / "validation_dynamique.json")
    hdv = charger(DON / "hdv_france_2019_2023_stats.json")
    vp24 = charger(SRC / "eea_co2_cars_fr/fr2024_combinaisons_modele_masse_puissance.json")["resultats"]
    # même requête avec le mode de carburant « Fm » (H hybride non rechargeable, P rechargeable, E électrique, M mono...)
    vp24m = charger(SRC / "eea_co2_cars_fr/fr2024_combinaisons_modele_masse_puissance_mode.json")["resultats"]
    vp21 = charger(SRC / "eea_co2_cars_fr/fr2021_combinaisons_modele_empattement.json")["resultats"]
    vul21 = charger(SRC / "eea_co2_cars_fr/fr2021_vans_combinaisons.json")["resultats"]

    J = {"meta": {
        "titre": "Modèle de véhicules – paramètres sourcés (volet 01, véhicules)",
        "version": "0.1", "date": str(date.today()),
        "auteur": "volet 01 Véhicules, D:/DocRoute/17_Modele_Vehicules_Conducteurs/01_Vehicules",
        "unites": "SI sauf mention (km/h pour les vitesses de référence, kW pour les puissances, kg pour les masses)",
        "forme_parametre": "{id, grandeur, population, loi, parametres, unite, conditions, source:{doc, page, annee}, confiance, nature}",
        "nature": {"norme": "valeur réglementaire ou de conception (seuil, convention de calcul)",
                   "mesure": "valeur mesurée (essai, enquête instrumentée)",
                   "donnee_administrative": "statistique officielle (parc, immatriculations, déclarations réglementaires)",
                   "donnee_constructeur": "fiche technique constructeur",
                   "derive": "calculée ici à partir de sources citées (calcul indiqué)",
                   "estimation": "hypothèse de ce volet, à remplacer par une mesure",
                   "convention": "choix de modélisation ou valeur par défaut d'un autre outil"},
        "confiance": "haute | moyenne | faible",
        "construit_par": "recon/trafic/vehicules/construire_parametres.py",
    }, "sources": SOURCES}

    # ====================================================================== parc et trafic
    f = "vp_national.xlsx"
    vp_tot = sdes_val(sdes, f, "Carburant détaillé", "Ensemble")
    vp_energie = {k: sdes_val(sdes, f, "Carburant détaillé", k) for k in
                  ["Diesel", "Essence", "Electrique", "Essence HNR", "Essence HR", "Diesel HNR", "Diesel HR", "Gaz", "Hydrogène et autre ZE"]}
    vp_age = {k: sdes_val(sdes, f, "Âge", k) for k in ["0 à 4 ans", "5 à 9 ans", "10 à 14 ans", "15 à 19 ans", "20 à 24 ans", "25 ans et plus"]}
    vul_tot = sdes_val(sdes, "vul_national.xlsx", "Carburant détaillé", "Véhicule utilitaire leger (ensemble)")
    pl_tot = sdes_val(sdes, "pl_national.xlsx", "Carburant détaillé", "Poids lourd (ensemble)")
    tcp_tot = sdes_val(sdes, "tcp_national.xlsx", "Carburant détaillé", "Transport en commun de personne (ensemble)")
    parc = []
    parc.append(P("PARC-CAT-2026", "parc en circulation par catégorie au 1er janvier 2026", "véhicules immatriculés en France (SIV), en circulation",
                  "effectifs", {"VP": round(vp_tot), "VUL": round(vul_tot), "PL": round(pl_tot), "autobus_autocars": round(tcp_tot),
                                "dont_PL_camion": round(sdes_val(sdes, "pl_national.xlsx", "Carburant détaillé", "Camion")),
                                "dont_PL_tracteur_routier": round(sdes_val(sdes, "pl_national.xlsx", "Carburant détaillé", "Tracteur routier")),
                                "dont_autobus": round(sdes_val(sdes, "tcp_national.xlsx", "Carburant détaillé", "Autobus")),
                                "dont_autocars": round(sdes_val(sdes, "tcp_national.xlsx", "Carburant détaillé", "Autocar"))},
                  "véhicules", "parc au 1er janvier, données provisoires", S("SDES2026", "xlsx nationaux, feuille « Carburant détaillé »"), "haute", "donnee_administrative"))
    parc.append(P("PARC-VP-ENERGIE-2026", "répartition du parc VP par énergie", "voitures particulières en circulation, 1/1/2026", "catégorielle",
                  {k: round(v / vp_tot, 4) for k, v in vp_energie.items()}, "part", "HNR = hybride non rechargeable, HR = hybride rechargeable",
                  S("SDES2026", "vp_national.xlsx, « Carburant détaillé »"), "haute", "donnee_administrative"))
    fam_parc = {"electrique": round(vp_energie["Electrique"] / vp_tot, 4),
                "thermique_auto_hybride": round(sum(vp_energie[k] for k in ["Essence HNR", "Essence HR", "Diesel HNR", "Diesel HR"]) / vp_tot, 4)}
    fam_parc["thermique_manuelle"] = round(1.0 - fam_parc["electrique"] - fam_parc["thermique_auto_hybride"], 4)
    parc.append(P("PARC-VP-FAMILLE-2026", "répartition du parc VP en circulation par famille de motorisation du modèle dynamique",
                  "voitures particulières en circulation, 1/1/2026", "catégorielle", fam_parc, "part",
                  "électrique = « Electrique » ; thermique_auto_hybride = hybrides essence et diesel, rechargeables ou non ; thermique_manuelle = le reste "
                  "(la boîte de vitesses n'est pas connue : les thermiques automatiques non hybrides y sont comptés)",
                  S("SDES2026", "vp_national.xlsx, « Carburant détaillé » (regroupement du volet)"), "haute", "derive"))
    parc.append(P("PARC-VP-AGE-2026", "répartition du parc VP par classe d'âge", "voitures particulières en circulation, 1/1/2026", "histogramme",
                  {"classes": {k: round(v / vp_tot, 4) for k, v in vp_age.items()},
                   "age_moyen_ans": sdes_val(sdes, f, "Âge moyen", "Ensemble"),
                   "age_moyen_electriques_ans": sdes_val(sdes, f, "Âge moyen", "Electrique et hydrogène")},
                  "part / an", None, S("SDES2026", "vp_national.xlsx, « Âge », « Âge moyen »"), "haute", "donnee_administrative"))
    parc.append(P("PARC-VUL-PTAC-2026", "répartition du parc VUL par PTAC et sous-catégorie", "VUL en circulation, 1/1/2026", "catégorielle",
                  {"PTAC": {k: round(sdes_val(sdes, "vul_national.xlsx", "PTAC", k) / vul_tot, 4) for k in ["Moins de 1,5 t", "1,5 à moins de 2,5 t", "2,5 à moins de 3,5 t", "3,5 t"]},
                   "sous_categorie": {k: round(sdes_val(sdes, "vul_national.xlsx", "Crit'Air", k + " (ensemble)") / vul_tot, 4) for k in ["Camionnette", "Camping-car", "Dérivé VP", "Autre VASP"]},
                   "part_electrique": round(sdes_val(sdes, "vul_national.xlsx", "Carburant détaillé", "Electrique") / vul_tot, 4),
                   "age_moyen_ans": sdes_val(sdes, "vul_national.xlsx", "Âge moyen", "Véhicule utilitaire leger (ensemble)")},
                  "part / an", None, S("SDES2026", "vul_national.xlsx, « PTAC », « Crit'Air », « Âge moyen »"), "haute", "donnee_administrative"))
    parc.append(P("PARC-PL-PTAC-2026", "répartition du parc PL par PTAC", "poids lourds en circulation, 1/1/2026 (camions, tracteurs, VASP lourds)", "catégorielle",
                  {"PTAC": {k: round(sdes_val(sdes, "pl_national.xlsx", "PTAC", k) / pl_tot, 4) for k in ["Moins de 7,5 t", "7,5 à moins de 12 t", "12 à moins de 19 t", "19 à moins de 26 t", "26 à moins de 32 t", "32 t et plus"]},
                   "age_moyen_ans": {"ensemble": sdes_val(sdes, "pl_national.xlsx", "Âge Moyen", "Poids lourd (ensemble)"), "camion": sdes_val(sdes, "pl_national.xlsx", "Âge Moyen", "Camion"), "tracteur": sdes_val(sdes, "pl_national.xlsx", "Âge Moyen", "Tracteur routier")},
                   "part_electrique": round(sdes_val(sdes, "pl_national.xlsx", "Carburant détaillé", "Electrique") / pl_tot, 4)},
                  "part / an", "PTAC du véhicule moteur (le tracteur seul pour un ensemble articulé)", S("SDES2026", "pl_national.xlsx"), "haute", "donnee_administrative"))
    bus_tot = sdes_val(sdes, "tcp_national.xlsx", "Carburant détaillé", "Autobus")
    parc.append(P("PARC-BUS-ENERGIE-2026", "répartition des autobus par énergie", "autobus en circulation, 1/1/2026", "catégorielle",
                  {k: round(sdes_val(sdes, "tcp_national.xlsx", "Carburant détaillé", k, occurrence=1) / bus_tot, 4) for k in ["Diesel", "Gaz", "Diesel HNR", "Electrique", "Gaz HNR"]}
                  | {"age_moyen_autobus_ans": sdes_val(sdes, "tcp_national.xlsx", "Âge moyen", "Autobus"), "age_moyen_autocars_ans": sdes_val(sdes, "tcp_national.xlsx", "Âge moyen", "Autocar")},
                  "part / an", "2e occurrence des libellés = bloc « Autobus » de la feuille", S("SDES2026", "tcp_national.xlsx"), "haute", "donnee_administrative"))
    parc.append(P("PARC-2RM-2025", "parc de deux-roues motorisés (estimation ONISR)", "2RM en France, 1/1/2025", "effectifs",
                  {"total": 3440000, "cyclomoteurs": 516000, "motos_legeres": 860000, "motos_lourdes": 2064000,
                   "part_electrique": {"ensemble": 0.040, "cyclomoteurs": 0.177, "motos_legeres": 0.046, "motos_lourdes": 0.003}},
                  "véhicules / part", "estimation ONISR (enquête ministère 2012, Kantar Parc Auto, SIV)", S("ONISR2024", "p. 92 (PDF 94), tableau « Estimation du parc 2RM »", 2025), "moyenne", "donnee_administrative"))
    km = {"VP": sdes_val(sdes, f, "Distance", "Ensemble", annee="2025"),
          "VUL": sdes_val(sdes, "vul_national.xlsx", "Distance", "Véhicule utilitaire leger (ensemble)", annee="2025"),
          "PL": sdes_val(sdes, "pl_national.xlsx", "Distance", "Poids lourd (ensemble)", annee="2025"),
          "autobus_autocars": sdes_val(sdes, "tcp_national.xlsx", "Distance", "Transport en commun de personne (ensemble)", annee="2025")}
    km_tot = sum(km.values())
    trafic = []
    trafic.append(P("TRAF-VKM-SDES-2025", "kilomètres parcourus par les véhicules immatriculés en France, par catégorie", "parc français, toutes routes, année 2025",
                    "catégorielle", {"milliards_km": {k: round(v / 1e9, 2) for k, v in km.items()}, "parts": {k: round(v / km_tot, 4) for k, v in km.items()},
                                     "parcours_annuel_moyen_km": {"VP": round(sdes_val(sdes, f, "Parcours moyen", "Ensemble", annee="2025")),
                                                                 "PL_camion": round(sdes_val(sdes, "pl_national.xlsx", "parcours moyen", "Camion", annee="2025")),
                                                                 "PL_tracteur": round(sdes_val(sdes, "pl_national.xlsx", "parcours moyen", "Tracteur routier", annee="2025")),
                                                                 "autobus": round(sdes_val(sdes, "tcp_national.xlsx", "Parcours moyen", "Autobus", annee="2025")),
                                                                 "autocar": round(sdes_val(sdes, "tcp_national.xlsx", "Parcours moyen", "Autocar", annee="2025"))}},
                    "part", "hors 2RM et hors véhicules étrangers ; ATTENTION : dans pl_national.xlsx, la feuille « Distance » a des libellés décalés d'une ligne dans le bloc « Tracteur routier » (le total PL reste juste) — utiliser « parcours moyen » x parc",
                    S("SDES2026", "feuilles « Distance » et « Parcours moyen » (année 2025)"), "haute", "donnee_administrative"))
    trafic.append(P("TRAF-VKM-ONISR-2024", "répartition de la circulation par type de véhicule (France métropolitaine, véhicules français et étrangers)", "toutes routes, 2024",
                    "catégorielle", {"milliards_vehicules_km": {"vehicules_tourisme": 473.3, "dont_VT_VU_etrangers": 33.2, "vehicules_utilitaires": 83.3, "vehicules_lourds": 39.6, "dont_poids_lourds": 36.4, "dont_bus_cars": 3.2, "dont_lourds_etrangers": 14.7, "deux_roues_motorises": 11.7, "ensemble": 607.9},
                                     "parts": {"vehicules_tourisme": round(473.3 / 607.9, 4), "vehicules_utilitaires": round(83.3 / 607.9, 4), "poids_lourds": round(36.4 / 607.9, 4), "bus_cars": round(3.2 / 607.9, 4), "deux_roues_motorises": round(11.7 / 607.9, 4)},
                                     "reseau_routier_national_part_km": 0.36, "autoroutes_part_km": 0.27},
                    "part", "moyenne nationale ; la composition locale (rue de Meylan) diffère : à recaler par comptage", S("ONISR2024", "p. 92 (PDF 94), tableau « Estimation annuelle de la circulation par réseau »", 2025), "haute", "donnee_administrative"))
    J["parc_france"] = parc
    J["composition_trafic"] = trafic

    # ====================================================================== AEE : voitures par segment
    seg_masse, seg_pui, seg_pm, seg_n, seg_bev = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(float), defaultdict(float)
    tot24, non_classe = 0, defaultdict(int)
    for r in vp24:
        n = r["n"]; tot24 += n
        seg = segment_vp(r["Mk"], r["Cn"])
        if seg is None:
            non_classe[f"{r['Mk']} {r['Cn']}"] += n; continue
        seg_n[seg] += n
        if r["Ft"] == "electric": seg_bev[seg] += n
        if r["m"]:
            seg_masse[seg].append((r["m"], n))
        if r["p"] and r["p"] > 20:  # quelques valeurs « Ep » de 4 à 12 kW = moteur électrique d'hybrides : écartées
            seg_pui[seg].append((r["p"], n))
            if r["m"]:
                seg_pm[seg].append((1000.0 * r["p"] / r["m"], n))
    seg_w, seg_v = defaultdict(list), defaultdict(list)
    for r in vp21:
        seg = segment_vp(r["Mk"], r["Cn"])
        if seg and r["w"]:
            seg_w[seg].append((r["w"], r["n"]))
            if r["v1"]:
                seg_v[seg].append((r["v1"], r["n"]))
    classes_vp_stats = {}
    for seg in ["citadine", "compacte", "berline", "suv_b", "suv_c", "monospace_ludospace"]:
        classes_vp_stats[seg] = {"immatriculations_2024": int(seg_n[seg]), "part_immatriculations_2024": round(seg_n[seg] / tot24, 4),
                                 "part_electrique_2024": round(seg_bev[seg] / seg_n[seg], 4) if seg_n[seg] else None,
                                 "masse_UE_kg": quantiles_ponderes(seg_masse[seg]), "puissance_kW": quantiles_ponderes(seg_pui[seg]),
                                 "puissance_masse_W_kg": quantiles_ponderes(seg_pm[seg]),
                                 "empattement_mm_2021": quantiles_ponderes(seg_w[seg]), "voie_avant_mm_2021": quantiles_ponderes(seg_v[seg])}
    # loi conjointe (masse, P/m, famille de motorisation) par segment : combinaisons AEE pondérées par les
    # immatriculations (correction du 17/10/2026 : la v0.1 tirait masse et P/m indépendamment, tronquées à [P5 ; P95])
    def famille_aee(ft, fm):
        if ft == "electric":
            return "electrique"
        if fm in ("H", "P"):
            return "thermique_auto_hybride"
        return "thermique_manuelle"
    seg_conj, fam_new = defaultdict(lambda: defaultdict(float)), defaultdict(float)
    for r in vp24m:
        seg = segment_vp(r["Mk"], r["Cn"])
        if seg is None or not r["m"] or not r["p"] or r["p"] <= 20:
            continue
        fam = famille_aee(r["Ft"], r["Fm"])
        seg_conj[seg][(int(r["m"]), round(1000.0 * r["p"] / r["m"], 1), fam)] += r["n"]
        fam_new[fam] += r["n"]
    couverture = sum(seg_n.values()) / tot24
    J["_diagnostic_segmentation"] = {"immatriculations_2024_FR": tot24, "part_classee": round(couverture, 4),
                                     "principaux_non_classes": sorted(non_classe.items(), key=lambda x: -x[1])[:25]}
    # ensemble du marché 2024
    tout_m = [(r["m"], r["n"]) for r in vp24 if r["m"]]
    tout_pm = [(1000.0 * r["p"] / r["m"], r["n"]) for r in vp24 if r["m"] and r["p"] and r["p"] > 20]

    # ====================================================================== AEE : VUL par segment
    vs = defaultdict(lambda: defaultdict(list)); vn = defaultdict(float); vtot = 0
    for r in vul21:
        n = r["n"]; vtot += n
        seg = segment_vul(r["Mk"], r["Cn"])
        if seg is None:
            continue
        vn[seg] += n
        for cle, val_ in [("masse_UE_kg", r["m"]), ("ptac_kg", r["ptac"]), ("puissance_kW", r["p"]), ("empattement_mm", r["w"])]:
            if val_:
                vs[seg][cle].append((val_, n))
        if r["m"] and r["p"]:
            vs[seg]["puissance_masse_W_kg_vide"].append((1000.0 * r["p"] / r["m"], n))
            if r["ptac"]:
                vs[seg]["puissance_masse_W_kg_ptac"].append((1000.0 * r["p"] / r["ptac"], n))
    classes_vul_stats = {seg: {"immatriculations_2021": int(vn[seg]), "part_immatriculations_2021": round(vn[seg] / vtot, 4),
                               **{k: quantiles_ponderes(v) for k, v in vs[seg].items()}} for seg in ["vul_petit", "vul_moyen", "vul_grand", "vul_pickup"]}

    # ====================================================================== calage dynamique (validation)
    syn = val["synthese"]
    dyn = {
        "modele": "a(v) = min(a_lancement, k P / (m v), mu g part_essieu) - (m g C_r + 1/2 rho CxS v^2 + m g sin(atan p)) / m ; voir recon/trafic/vehicules/dynamique.py",
        "familles": {
            fam: {"k_reprise": syn[fam]["k_reprise_cale_60_100"], "k_depart": syn[fam]["k_depart_cale_0_100"],
                  "a_lancement_ms2": syn[fam]["a_lancement_ms2"], "a_reprise_bas_regime_15_30_ms2": syn[fam]["a_reprise_bas_regime_15_30_ms2"],
                  "erreurs_validation_croisee": {"t_60_100": syn[fam]["erreur_60_100_un_exclu"], "t_80_120": syn[fam]["erreur_80_120_un_exclu"], "t_0_100": syn[fam]["erreur_0_100_un_exclu"]}}
            for fam in ["thermique_manuelle", "thermique_auto_hybride", "electrique"]},
        "toutes": {"erreurs_validation_croisee": {"t_60_100": syn["toutes"]["erreur_60_100_un_exclu"], "t_80_120": syn["toutes"]["erreur_80_120_un_exclu"], "t_0_100": syn["toutes"]["erreur_0_100_un_exclu"]}},
        "hypotheses": val["hypotheses"], "facteur_cxs_largeur_hauteur": val["facteur_cxs"],
        "source": S("ADAC", "PDF des 10 tests ; calage par recon/trafic/vehicules/valider_vehicules.py"),
        "fichier_detail": "donnees/validation_dynamique.json",
    }
    J["calage_dynamique"] = dyn
    fam_par = {f_: dyn["familles"][f_] for f_ in dyn["familles"]}

    # ====================================================================== adhérence et freinage (communs)
    vsa_vr = [(40, 44), (50, 48), (57, 50), (60, 51), (70, 54), (80, 57), (90, 60), (100, 63), (110, 65), (120, 67), (130, 69), (134, 70)]
    cfts = [{"R_m": R, "V_kmh": V, "cfts": round(V * V / (127.0 * R) - 0.05, 3)} for R, V in vsa_vr]
    ict = {40: (15, 35), 60: (35, 55), 80: (60, 75), 100: (105, 110), 110: (135, 125)}
    ict_der = {V: {"d0_mouille_m": d0, "ds_sec_m_avec_2s": ds, "decel_mouille_ms2": round((V / 3.6) ** 2 / (2 * d0), 2),
                   "decel_sec_ms2": round((V / 3.6) ** 2 / (2 * (ds - 2 * V / 3.6)), 2)} for V, (d0, ds) in ict.items()}
    adac_mfdd = syn["toutes"]["mfdd_equivalent_100_0"]
    adh = [
        P("ADH-NORME-VSA90110", "décélération moyenne conventionnelle de freinage d'arrêt gamma(V)", "véhicule léger de projet, chaussée mouillée « conditions conventionnelles »",
          "table", {"V_kmh": [30, 50, 70, 90, 110], "gamma_g": [0.46, 0.46, 0.44, 0.40, 0.36], "temps_perception_reaction_s": 2.0},
          "fraction de g", "distance d'arrêt = 2 v + v²/(2 g (gamma + p)) ; majorée de 25 % en courbe R < 5V", S("VSA90110", "p. 16 (PDF 18), tableau des distances", 2014), "haute", "norme"),
        P("ADH-NORME-VISI2018", "décélération moyenne en manœuvre d'arrêt gamma_v (règles de visibilité 2018)", "véhicule léger de projet", "table",
          {"V_kmh": ["30", "50", "70", ">70"], "gamma_g": [0.46, 0.46, 0.44, 0.41], "temps_perception_reaction_s": 1.8, "deceleration_manoeuvre_ralentissement_ms2": 1.5},
          "fraction de g / m/s²", "d_a = (T_PR v + (1 + m_c(R)) v²/(2 g (gamma_v + p))) K(N_PV) ; table lue sur tuile (cellule 0,46 fusionnée sur 30 et 50 km/h) ; 1,5 m/s² = décélération de confort en approche de giratoire",
          S("VISI2018", "p. 11 (PDF 13) et p. 20 (PDF 22)", 2018), "haute", "norme"),
        P("ADH-NORME-ICTAVRU", "distances de freinage conventionnelles mouillé (d0) et distances d'arrêt sur sol sec (ds)", "véhicule de projet VRU ; d0 : roue bloquée, pneu Europe, 1 mm d'eau",
          "table", ict_der, "m ; m/s²", "décélérations dérivées ici : v²/(2 d0) et v²/(2 (ds - 2 v)) ; les distances sont arrondies à 5 m (incertitude forte à 40-60 km/h sur le sec)",
          S("ICTAVRU", "p. 32 (PDF 34)", 2009), "moyenne", "derive"),
        P("ADH-CFL-REVETEMENT", "coefficient de frottement longitudinal (CFL) selon le revêtement", "chaussées urbaines rapides, mesure CFL (mouillé)",
          "uniforme par revêtement (plage lue)", {"enrobes_fins": [0.12, 0.36], "beton_balaye": [0.25, 0.36], "BB_normal": [0.26, 0.51], "BB_cloute": [0.27, 0.53], "enduits": [0.27, 0.56]},
          "sans dimension", "lecture graphique sur tuile native, incertitude +-0,01 ; plage selon nature et âge", S("ICTAVRU", "p. 204 (PDF 206), graphique", 2009), "moyenne", "norme"),
        P("ADH-CFTS-VSA90110", "coefficient de frottement transversal au seuil de sécurité (cfts) déduit de la vitesse conventionnelle en courbe", "branches et bretelles, dévers 5 %",
          "table", {"points": cfts, "formule": "cfts = V²/(127 R) - d (V en km/h, R en m, d = 0,05)"}, "sans dimension",
          "dérivé ici du tableau V(R) du guide ; décroît de 0,33 (44 km/h) à 0,24 (70 km/h)", S("VSA90110", "§ 11.4, p. 68 (PDF 70)", 2014), "moyenne", "derive"),
        P("ADH-BUS-CONFORT", "accélérations admissibles pour un bus avec voyageurs debout", "autobus urbain, voyageurs debout", "valeurs seuils",
          {"acceleration_transversale_max_ms2": 1.0, "deceleration_visibilite_ms2": 2.0}, "m/s²", "règle de conception des sites propres TC sur artère à 70 km/h",
          S("VSA70", "p. 65 (texte § 4.2.2-4.2.3)", 2013), "haute", "norme"),
        P("ADH-MESURE-GREIBE-FROTTEMENT", "frottement mesuré des 3 pistes (60 km/h, 20 % de glissement, méthode standard mouillée)", "routes danoises en service", "plage",
          {"min": 0.49, "max": 0.75}, "sans dimension", None, S("GREIBE2007", "p. 18-19, tableau 2.7", 2007), "haute", "mesure"),
        P("ADH-MESURE-GREIBE-DECEL", "décélération moyenne de freinage d'urgence (de la pédale à l'arrêt) avec ABS", "2 voitures ABS 2006 (Punto, Vectra) ; 80, 110, 130 km/h",
          "moyennes par groupe", {"professionnels_sec": 8.4, "professionnels_mouille": 7.9, "non_professionnels_sec": 7.4, "non_professionnels_mouille": 7.0,
                                  "professionnels_sec_50_30_kmh": 9.5, "professionnels_sec_100_70_kmh": 9.1, "plage_professionnels_par_piste": [8.1, 8.7]},
          "m/s²", "Dec inclut la phase de mise en pression ; ratio non-pro/pro ~ 0,90", S("GREIBE2007", "p. 41-43, tableaux 4.5 et 4.6, figure 4.10", 2007), "haute", "mesure"),
        P("ADH-MESURE-GREIBE-MODELE", "décélération d'urgence en fonction du frottement mesuré (mouillé)", "conducteurs professionnels, voitures ABS",
          "régression", {"formule": "Dec = 8,79 sqrt(mu) + 0,028 V0", "a": 8.79, "b": 0.028, "R2": 0.97, "domaine_mu": [0.49, 0.75]},
          "m/s² (V0 en m/s)", "mu mesuré à 60 km/h, 20 % de glissement", S("GREIBE2007", "p. 50", 2007), "moyenne", "mesure"),
        P("ADH-MESURE-ADAC-100-0", "décélération moyenne équivalente v²/(2 d) des freinages 100-0 km/h", "10 voitures récentes (2019-2026), pneus d'essai neufs, piste sèche",
          "normale", {"moyenne": adac_mfdd["moyenne"], "ecart_type": adac_mfdd["ecart_type"], "min": adac_mfdd["min"], "max": adac_mfdd["max"], "n": adac_mfdd["n"],
                      "distances_m": {x["id"]: x["freinage"]["d_100_0_mesure_m"] for x in val["vehicules"]}},
          "m/s²", "moyenne de 10 freinages par véhicule ; inclut la montée en décélération ; borne haute « véhicule neuf, pneus neufs, piste »", S("ADAC", "page « ADAC Messwerte » de chaque PDF"), "haute", "mesure"),
        P("ADH-PNEU-ETIQUETTE", "classes d'adhérence sur sol mouillé (indice G) et de résistance au roulement (RRC) des pneus", "pneus C1 (VP), C2 (VUL), C3 (PL)",
          "classes", {"adherence_mouille_G": {"C1": {"A": ">=1,55", "B": "1,40-1,54", "C": "1,25-1,39", "D": "1,10-1,24", "E": "<=1,09"},
                                              "C2": {"A": ">=1,40", "B": "1,25-1,39", "C": "1,10-1,24", "D": "0,95-1,09", "E": "<=0,94"},
                                              "C3": {"A": ">=1,25", "B": "1,10-1,24", "C": "0,95-1,09", "D": "0,80-0,94", "E": "<=0,79"}},
                      "RRC_N_par_kN": {"C1": {"A": "<=6,5", "B": "6,6-7,7", "C": "7,8-9,0", "D": "9,1-10,5", "E": ">=10,6"},
                                       "C3": {"A": "<=4,0", "B": "4,1-5,0", "C": "5,1-6,0", "D": "6,1-7,0", "E": ">=7,1"}}},
          "sans dimension / N/kN", "G relatif au pneu de référence (essai ONU R117 annexe 5) ; RRC = coefficient de résistance au roulement x 1000", S("R2020_740", "annexe I, parties A et B (JO L 177, p. 13-14)", 2020), "haute", "norme"),
    ]
    J["adherence"] = adh

    frein = [
        P("REG-R13H-TYPE0", "exigence de freinage des voitures particulières (essai type 0)", "M1 et N1 réceptionnés R13-H", "seuils",
          {"moteur_debraye": {"v_kmh": 100, "s_max": "0,1 v + 0,0060 v² (70,0 m à 100 km/h)", "mfdd_min_ms2": 6.43},
           "moteur_embraye": {"v": "80 % vmax <= 160 km/h", "s_max": "0,1 v + 0,0067 v²", "mfdd_min_ms2": 5.76},
           "frein_secours": {"s_max": "0,1 v + 0,0158 v²", "mfdd_min_ms2": 2.44}, "effort_pedale_daN": [6.5, 50]},
          "m ; m/s²", "le terme 0,1 v (v en km/h) équivaut à 0,36 s x v (m/s) de temps mort admis", S("R13H", "annexe 3, § 2.1.1 et 2.2.2 (JO p. 41-42)", 2026), "haute", "norme"),
        P("REG-R13H-SIGNAL", "seuils des feux stop et du signal de freinage d'urgence", "M1, N1", "seuils",
          {"regeneratif_ou_automatique_peut_allumer_si_inferieur_ms2": 1.3, "doit_allumer_si_superieur_ms2": 1.3, "signal_urgence_activation_min_ms2": 6.0, "signal_urgence_desactivation_ms2": 2.5},
          "m/s²", "utile pour le rendu des feux stop des véhicules simulés", S("R13H", "§ 5.2.22-5.2.23 (JO p. 21)", 2026), "haute", "norme"),
        P("REG-R13-TYPE0", "exigence de freinage des véhicules lourds (essai type 0)", "M2, M3, N1-N3 réceptionnés R13", "seuils",
          {"moteur_debraye": {"v_kmh": {"M2": 60, "M3": 60, "N1": 80, "N2": 60, "N3": 60}, "s_max": "0,15 v + v²/130", "mfdd_min_ms2": 5.0},
           "moteur_embraye": {"v": "0,80 vmax plafonné (M2 100, M3 90, N1 120, N2 100, N3 90 km/h)", "s_max": "0,15 v + v²/103,5", "mfdd_min_ms2": 4.0},
           "effort_pedale_max_daN": 70},
          "m ; m/s²", "le terme 0,15 v équivaut à 0,54 s x v (m/s) de temps mort admis", S("R13", "annexe 4, § 2.1.1 (JO L 42/56)", 2016), "haute", "norme"),
        P("REG-R13-TEMPS-REPONSE", "temps de réponse du freinage de service assisté", "M, N à freinage dépendant d'une énergie autre que musculaire", "borne",
          {"t_max_s": 0.6, "definition": "de l'action sur la commande à la force de freinage prescrite sur l'essieu le plus défavorisé ; air comprimé : 75 % de la pression asymptotique au cylindre le plus défavorisé, actionnement en 0,2 s"},
          "s", None, S("R13", "annexe 4 § 4.1 (JO L 42/60) ; annexe 6 § 2.3-2.4", 2016), "haute", "norme"),
        P("REG-R78", "exigence de freinage des deux et trois-roues (essai à sec)", "L1 à L5 réceptionnés R78", "seuils",
          {"frein_avant_seul": {"L1": 3.4, "L2": 2.7, "L3": 4.4, "L4": 3.6}, "frein_arriere_seul": {"L1": 2.7, "L2": 2.7, "L3": 2.9, "L4": 3.6},
           "freinage_combine_ou_double": {"L1_L2": 4.4, "L3": 5.1, "L5": 5.0, "L4": 5.4}, "formes_distance": "S <= 0,1 V + k V² (k = 0,0071 à 0,0154)"},
          "m/s² (MFDD minimale)", None, S("R78", "annexe 3, § 3.3 (JO L 24/46-47)", 2015), "haute", "norme"),
        P("REG-LIMITEURS", "vitesse plafonnée par limiteur obligatoire", "M2, M3 ; N2, N3", "seuils", {"M2_M3_kmh": 100, "N2_N3_kmh": 90},
          "km/h", None, S("D200285", "art. 2 et 3 (JO L 327, p. 9)", 2002), "haute", "norme"),
        P("REG-DIMENSIONS-UE", "dimensions maximales et inscription en giration", "véhicules M2, M3, N2, N3, O3, O4 en trafic", "seuils",
          {"longueur_max_m": {"vehicule_moteur": 12.0, "vehicule_articule": 16.5, "train_routier": 18.75, "autobus_articule": 18.75, "autobus_2_essieux": 13.5, "autobus_plus_2_essieux": 15.0},
           "largeur_max_m": 2.55, "largeur_caisse_conditionnee_m": 2.60, "hauteur_max_m": 4.0, "pivot_arriere_semi_max_m": 12.0,
           "couronne_giration_m": {"rayon_exterieur": 12.5, "rayon_interieur": 5.3}, "debord_autobus_entree_couronne_max_m": 0.60,
           "masse_max_ensemble_5_6_essieux_t": 40, "masse_max_transport_combine_t": 44},
          "m / t", None, S("D9653", "annexe I, § 1.1-1.8 et 2.2 (version consolidée, p. 15-17)", 2019), "haute", "norme"),
        P("REG-MASSE-ORDRE-MARCHE", "définition de la masse en ordre de marche", "véhicules à moteur réceptionnés UE", "définition",
          {"inclut": "carburant >= 90 %, liquides, équipement standard, conducteur 75 kg", "masse_conducteur_kg": 75, "masse_passager_kg": 75},
          "kg", "toutes les masses « UE » de ce fichier (AEE, ADAC) suivent cette définition", S("R1230", "art. 2, points 4 et 20", 2012), "haute", "norme"),
        P("REG-CATEGORIES-L", "critères des catégories de deux-roues", "L1e, L3e ; cycles à pédalage assisté exclus", "seuils",
          {"L_commun": {"longueur_max_mm": 4000, "largeur_max_mm": 2000, "largeur_max_L1e_mm": 1000, "hauteur_max_mm": 2500},
           "L1e": {"vmax_kmh": 45, "puissance_max_W": 4000, "cylindree_max_cm3": 50},
           "L1e_A_velo_a_moteur": {"coupure_assistance_kmh": 25, "puissance_max_W": 1000},
           "L3e_A1": {"cylindree_max_cm3": 125, "puissance_max_kW": 11, "puissance_masse_max_kW_kg": 0.1},
           "L3e_A2": {"puissance_max_kW": 35, "puissance_masse_max_kW_kg": 0.2},
           "cycle_pedalage_assiste_exclu": {"puissance_nominale_max_W": 250, "coupure_kmh": 25}},
          "mm / km/h / W", None, S("R168", "art. 2 § 2 h) (p. 5) ; annexe I (JO L 60/94-96)", 2013), "haute", "norme"),
        P("REG-EDPM", "définition de l'engin de déplacement personnel motorisé (trottinette électrique)", "EDPM en France", "seuils",
          {"vmax_construction_kmh": [6, 25], "places": 1, "freinage": "dispositif de freinage efficace (art. R. 315-7), caractéristiques fixées par arrêté"},
          "km/h", None, S("D2019_1082", "art. R. 311-1 6.15 et R. 315-7 du code de la route créés par le décret", 2019), "haute", "norme"),
    ]
    J["reglementation"] = frein

    sys_frein = [
        P("FREIN-TEMPS-MORT-REGLEMENTAIRE", "temps mort + établissement admis implicitement par les formules d'essai", "véhicules réceptionnés", "valeurs dérivées",
          {"VP_R13H_s": 0.36, "deux_roues_R78_s": 0.36, "lourds_R13_s": 0.54}, "s",
          "0,1 V (km/h) = 0,36 s x v (m/s) ; 0,15 V = 0,54 s x v ; ce sont des bornes d'homologation, pas des mesures", S("R13H", "annexe 3 § 2.1.1", 2026), "haute", "derive"),
        P("FREIN-PEDALE-PRO-VS-NONPRO", "délai entre contact de la pédale et 10 kg d'effort", "freinage d'urgence, 2 voitures ABS", "moyennes",
          {"professionnels_s": 0.05, "non_professionnels_s": 0.83, "non_pro_par_condition_s": {"sec_80": 0.70, "sec_110": 0.80, "mouille_80": 0.81, "mouille_110": 1.07}},
          "s", "grandeur de comportement (voir volet 02) ; indique que la montée en décélération dépend surtout du conducteur", S("GREIBE2007", "p. 45, tableau 4.7", 2007), "haute", "mesure"),
        P("FREIN-ETABLISSEMENT-VP", "durée de montée de la décélération (système seul) pour une voiture", "VP récentes", "à caler",
          {"valeur_par_defaut_s": None, "borne_reglementaire_equivalente_s": 0.36},
          "s", "aucune mesure publique ouverte trouvée dans ce lot ; le modèle utilise par défaut la borne réglementaire R13-H interprétée comme t_mort + t_etab/2 <= 0,36 s",
          S("R13H", "annexe 3 § 2.1.1", 2026), "faible", "estimation"),
    ]
    J["freinage_systeme"] = sys_frein

    # ====================================================================== classes
    C = {}

    def ex_adac(ids):
        out = []
        for r in adac["vehicules"]:
            if r["id"] in ids:
                c, m = r["constructeur"], r["mesures"]
                out.append({"id": r["id"], "modele": r["modele"], "longueur_mm": c["longueur_mm"], "largeur_mm": c["largeur_mm"], "hauteur_mm": c["hauteur_mm"],
                            "empattement_mm": c.get("empattement_mm"), "masse_UE_kg": c["masse_UE_kg"], "puissance_kW": c["puissance_kW"],
                            "diametre_braquage_constructeur_m": c.get("diametre_braquage_m"), "diametre_braquage_mesure_ADAC_m": m.get("diametre_braquage_m"),
                            "v_max_kmh": c["v_max_kmh"], "t_0_100_s": c["t_0_100_s"], "d_100_0_m": m["d_100_0_m"]})
        return out

    def classe_vp(seg, nom, ids_adac):
        st_ = classes_vp_stats[seg]
        ex = ex_adac(ids_adac)
        params = [
            P(f"{seg.upper()}-MASSE", "masse en ordre de marche (conducteur inclus)", f"VP neuves 2024 France, segment {seg}", "empirique pondérée ; lognormale ajustée",
              st_["masse_UE_kg"], "kg", "à vide + conducteur ; ajouter passagers et bagages (75 kg par personne, R1230)", S("AEE_VP", "co2cars_2024Fv30, MS=FR, champ « M (kg) »", 2025), "haute", "donnee_administrative"),
            P(f"{seg.upper()}-PUISSANCE", "puissance maximale déclarée", f"VP neuves 2024 France, segment {seg}", "empirique pondérée ; lognormale ajustée",
              st_["puissance_kW"], "kW", "champ « Ep » : puissance du moteur thermique pour les hybrides (sous-estime la puissance système)", S("AEE_VP", "champ « Ep (KW) »", 2025), "haute", "donnee_administrative"),
            P(f"{seg.upper()}-PUISSANCE-MASSE", "rapport puissance / masse en ordre de marche", f"VP neuves 2024 France, segment {seg}", "empirique pondérée ; lognormale ajustée",
              st_["puissance_masse_W_kg"], "W/kg", None, S("AEE_VP", "Ep / M, calcul ligne à ligne", 2025), "haute", "derive"),
            P(f"{seg.upper()}-EMPATTEMENT", "empattement", f"VP neuves 2021 France, segment {seg}", "empirique pondérée",
              st_["empattement_mm_2021"], "mm", "donnée publiée par l'AEE jusqu'en 2021 seulement", S("AEE_VP", "co2cars, Year=2021, champ « W (mm) »", 2023), "haute", "donnee_administrative"),
            P(f"{seg.upper()}-VOIE", "voie avant", f"VP neuves 2021 France, segment {seg}", "empirique pondérée",
              st_["voie_avant_mm_2021"], "mm", None, S("AEE_VP", "champ « At1 (mm) »", 2023), "haute", "donnee_administrative"),
            P(f"{seg.upper()}-PART-MARCHE", "part du segment dans les immatriculations VP 2024 et part électrique", "France 2024", "catégorielle",
              {"part": st_["part_immatriculations_2024"], "part_electrique_dans_segment": st_["part_electrique_2024"], "n": st_["immatriculations_2024"]},
              "part", "segmentation par nom de modèle (convention du volet, voir SEGMENTS_VP)", S("AEE_VP", "co2cars_2024Fv30", 2025), "moyenne", "derive"),
            P(f"{seg.upper()}-MASSE-PM-CONJOINTE", "loi conjointe masse / rapport puissance-masse / famille de motorisation", f"VP neuves 2024 France, segment {seg}",
              "empirique_conjointe",
              {"colonnes": ["masse_kg", "puissance_masse_W_kg", "famille", "immatriculations"],
               "lignes": [[m_, pm_, f_, int(n_)] for (m_, pm_, f_), n_ in sorted(seg_conj[seg].items())],
               "familles": {"electrique": "Ft = electric", "thermique_auto_hybride": "Fm = H (hybride non rechargeable, hybrides légers compris) ou P (rechargeable)",
                            "thermique_manuelle": "autres (essence, diesel, GPL, E85 mono-carburant) ; boîte non renseignée par l'AEE"}},
              "kg ; W/kg", "tirage d'une combinaison (marque, modèle, version) pondérée par les immatriculations : queues réelles, sans troncature ; "
              "P/m = Ep / M (moteur thermique seul pour les hybrides) ; les thermiques automatiques non hybrides restent dans la famille manuelle",
              S("AEE_VP", "co2cars_2024Fv30, MS=FR, champs Mk, Cn, Ft, Fm, « M (kg) », « Ep (KW) » (requête du 17/10/2026)", 2025), "haute", "donnee_administrative"),
        ]
        if ex:
            params.append(P(f"{seg.upper()}-EXEMPLES", "dimensions, braquage et performances des modèles de référence testés", f"modèles {', '.join(e['modele'] for e in ex)}",
                            "valeurs individuelles", {"modeles": ex}, "mm, kg, kW, m, km/h, s",
                            "diamètre de braquage : constructeur (catalogue ADAC) et mesuré ADAC (définition entre murs/trottoirs non précisée ; mesuré > constructeur de 0,4 à 0,9 m)",
                            S("ADAC", "fiches techniques et « ADAC Messwerte »"), "haute", "mesure"))
        C[seg] = {"nom": nom, "categorie_UE": "M1", "parametres": params}

    classe_vp("citadine", "Citadine (segments A-B : Clio, 208, Sandero, C3, Yaris, Polo...)", ["clio5_tce90", "p208_pt100", "sandero3_tce90", "e208_156", "ec3_you"])
    classe_vp("compacte", "Compacte (segment C : 308, Golf, Corolla, C4, Mégane...)", [])
    classe_vp("berline", "Berline (segment D : Model 3, 508...) — effectif faible", [])
    classe_vp("suv_b", "SUV urbain (2008, Captur, Duster, Yaris Cross, Puma...)", ["captur2_mh160", "p2008_pt130"])
    classe_vp("suv_c", "SUV compact et familial (3008, Model Y, Austral, Tiguan...)", ["p3008_3_hyb136", "modely_rwd_2025"])
    classe_vp("monospace_ludospace", "Monospace et ludospace VP (Jogger, Berlingo, Kangoo, Trafic VP...)", ["kangoo3_ev45"])

    # dynamique commune aux VP
    C["_dynamique_VP"] = {"nom": "Paramètres dynamiques communs aux VP (par famille de motorisation)", "parametres": [
        P("VP-DYN-K", "part de puissance utile k", "voitures testées ADAC 2020-2026 (n = 10)", "par famille (moyenne +- écart-type des valeurs calées)",
          {f_: {"k_reprise": fam_par[f_]["k_reprise"], "k_depart": fam_par[f_]["k_depart"]} for f_ in fam_par}, "sans dimension",
          "calé sur 60-100 km/h mesuré (reprise) et 0-100 constructeur (départ, thermiques manuels) ; validé en croisé (erreurs ci-dessous)",
          S("ADAC", "calage valider_vehicules.py"), "moyenne", "derive"),
        P("VP-DYN-A-LANCEMENT", "plafond d'accélération à basse vitesse a_lancement", "voitures testées ADAC", "par famille",
          {f_: {"a_lancement": fam_par[f_]["a_lancement_ms2"], "a_reprise_bas_regime_15_30": fam_par[f_]["a_reprise_bas_regime_15_30_ms2"]} for f_ in fam_par}, "m/s²",
          "électriques et hybrides : 15-30 km/h mesuré ; thermiques manuels : plafond d'adhérence 5,89 m/s² (mu 1,0 x 60 % sur l'essieu moteur, estimation) pour le départ arrêté, et 15-30 km/h en 2e à bas régime mesuré (~1,8 m/s²) pour une reprise sans rétrograder",
          S("ADAC", "texte des tests (15 auf 30 km/h)"), "moyenne", "mesure"),
        P("VP-DYN-ERREURS", "erreurs de prédiction en validation croisée (un exclu)", "10 voitures", "erreur relative",
          dyn["toutes"]["erreurs_validation_croisee"] | {"par_famille": {f_: fam_par[f_]["erreurs_validation_croisee"] for f_ in fam_par}}, "sans dimension",
          "erreur = (prédit - mesuré) / mesuré", S("ADAC", "validation_dynamique.json"), "moyenne", "derive"),
        P("VP-DYN-CXS", "coefficient de traînée x aire frontale", "VP", "proportionnel à largeur x hauteur",
          {"facteur": dyn["facteur_cxs_largeur_hauteur"], "point_d_appui": "208 II : S 2,1 m², Cx 0,295 (ADAC AT5958, fiche)"}, "m²",
          "estimation ; +-20 % de CxS change le 80-120 de +-3 à 6 %", S("ADAC", "AT5958 p. fiche technique"), "faible", "estimation"),
        P("VP-DYN-CR", "coefficient de résistance au roulement", "pneus C1", "uniforme", {"min": 0.0065, "mode": 0.0085, "max": 0.0106}, "N/N",
          "bornes = classes A à E de l'étiquette ; mode = classe C (estimation)", S("R2020_740", "annexe I partie A"), "moyenne", "estimation"),
        P("VP-FREIN-DMAX-SEC", "décélération établie maximale sur sec (ABS)", "VP récentes, pneus en bon état", "normale tronquée",
          {"moyenne": adac_mfdd["moyenne"], "ecart_type": adac_mfdd["ecart_type"], "min": 8.4, "max": adac_mfdd["max"]},
          "m/s²", "moyenne/écart-type = ADAC (piste, pneus neufs, n = 10) ; borne basse = Greibe 2007 professionnels sur routes en service (8,4) ; pour le parc âgé (11,8 ans) et la route réelle, préférer la moitié basse", S("ADAC", "Messwerte"), "moyenne", "mesure"),
        P("VP-FREIN-DMAX-SEC-PARC", "décélération établie maximale sur sec, parc en circulation (ABS)", "VP en circulation (âge moyen 11,8 ans), routes en service",
          "normale tronquée", {"moyenne": 9.3, "ecart_type": round(adac_mfdd["ecart_type"], 4), "min": 8.4, "max": round(adac_mfdd["moyenne"], 2)}, "m/s²",
          "moyenne = milieu des décélérations établies mesurées par Greibe sur routes sèches en service (≈ 9,1 m/s² entre 100 et 70 km/h, ≈ 9,5 entre 50 et 30 km/h ; "
          "2 voitures ABS de 2006, conducteurs professionnels) ; écart-type = dispersion entre modèles de l'ADAC ; bornes = freinage complet de Greibe (8,4) et moyenne ADAC "
          "(véhicules neufs, pneus neufs, piste : borne haute). Ajouté le 17/10/2026 : la v0.1 tirait tout le parc dans la loi ADAC",
          S("GREIBE2007", "p. 42-43 (PDF 42-43), tableau 4.5 et fig. 4.10 (pros, sec)", 2007), "faible", "estimation"),
        P("VP-FREIN-DMAX-MOUILLE", "décélération établie maximale sur mouillé (ABS)", "VP, chaussée mouillée", "modèle",
          {"formule_Greibe": "8,79 sqrt(mu) + 0,028 V0", "valeur_professionnels_ms2": 7.9, "valeur_conventionnelle_projet_g": "0,46 (30-50 km/h) à 0,36 (110 km/h)"},
          "m/s²", "mu = frottement mesuré de la chaussée (0,49-0,75 sur les pistes de Greibe ; CFL 0,12-0,56 selon le revêtement, ICTAVRU)", S("GREIBE2007", "p. 50 ; tableau 4.5", 2007), "moyenne", "mesure"),
        P("VP-VMAX", "vitesse maximale par construction", "modèles de référence ADAC", "plage", {"thermiques_hybrides": [174, 201], "electriques": [132, 201]}, "km/h",
          "les électriques citadins et utilitaires sont bridés (132-150 km/h)", S("ADAC", "fiches constructeur"), "haute", "donnee_constructeur"),
    ]}

    # VUL
    def classe_vul(seg, nom, ids, extra=None):
        st_ = classes_vul_stats[seg]
        params = [P(f"{seg.upper()}-{k.upper()}", k.replace("_", " "), f"VUL (N1) neufs 2021 France, {seg}", "empirique pondérée ; lognormale ajustée",
                    v, {"masse_UE_kg": "kg", "ptac_kg": "kg", "puissance_kW": "kW", "empattement_mm": "mm"}.get(k, "W/kg"),
                    "masse UE = ordre de marche ; puissance_masse_W_kg_ptac = à pleine charge", S("AEE_VUL", "co2vans Year=2021 MS=FR", 2023), "haute",
                    "donnee_administrative" if "puissance_masse" not in k else "derive")
                  for k, v in st_.items() if isinstance(v, dict)]
        params.append(P(f"{seg.upper()}-PART", "part dans les immatriculations VUL 2021", "France 2021", "part", {"part": st_["part_immatriculations_2021"], "n": st_["immatriculations_2021"]},
                        "part", "segmentation par nom de modèle (convention du volet)", S("AEE_VUL", None, 2023), "moyenne", "derive"))
        if ids:
            params.append(P(f"{seg.upper()}-EXEMPLES", "modèle de référence testé", "ADAC", "valeurs individuelles", {"modeles": ex_adac(ids)}, "divers", None, S("ADAC", "fiche + Messwerte"), "haute", "mesure"))
        if extra:
            params += extra
        C[seg] = {"nom": nom, "categorie_UE": "N1", "parametres": params}

    classe_vul("vul_petit", "Utilitaire léger compact (Kangoo, Partner, Berlingo, Express...)", ["kangoo3_ev45"])
    classe_vul("vul_moyen", "Fourgon moyen (Trafic, Expert, Jumpy, Transit Custom, Vito...)", [])
    classe_vul("vul_grand", "Grand fourgon et châssis-cabine <= 3,5 t (Master, Boxer, Jumper, Sprinter, Ducato...)", [])

    # Bus
    C["bus_12m"] = {"nom": "Autobus urbain standard 12 m", "categorie_UE": "M3 classe I", "parametres": [
        P("BUS12-DIM-CITARO", "dimensions et géométrie (Mercedes Citaro / eCitaro 12 m)", "modèle de référence", "valeurs constructeur",
          {"longueur_mm": 12135, "largeur_mm": 2550, "largeur_retros_mm": 2950, "hauteur_mm": {"Citaro": 3095, "eCitaro": 3400}, "empattement_mm": 5900,
           "porte_a_faux_avant_mm": 2805, "porte_a_faux_arriere_mm": 3430, "diametre_giration_entre_murs_mm": {"Citaro": 22970, "eCitaro": 21214},
           "diametre_cercle_des_roues_mm": {"Citaro": 19160, "eCitaro": 17058}, "angle_braquage_roue_avant_max_deg": "53 / 46 (deux roues)",
           "largeur_couronne_min_mm": {"Citaro": 7478, "eCitaro": 6803}, "pneus": "275/70 R 22,5", "plancher_mm": 370},
          "mm / degrés", "« turning circle » = cercle enveloppe (entre murs) ; « track circle » = cercle des roues (entre trottoirs)", S("CITARO", "p. 3-4 (Citaro), p. 4 (eCitaro)"), "haute", "donnee_constructeur"),
        P("BUS12-MASSE-PUISSANCE-CITARO", "PTAC et puissance", "Citaro / eCitaro 12 m", "valeurs constructeur",
          {"PTAC_kg": {"Citaro": 19500, "eCitaro": 20000}, "puissance_kW": {"Citaro_OM936": 220, "Citaro_option": 260, "eCitaro_crete_continue": [440, 360]},
           "boite": "Voith DIWA.6, 4 rapports (thermique) ; ZF AxTrax 2 LF (électrique)", "masse_a_vide_kg": None},
          "kg / kW", "masse à vide non publiée dans ces fiches (lacune)", S("CITARO", "p. 5 et p. 8 (Citaro) ; p. 4-5 et 7 (eCitaro)"), "haute", "donnee_constructeur"),
        P("BUS12-DIM-URBANWAY", "dimensions (Iveco Urbanway 12)", "modèle de référence", "valeurs",
          {"longueur_mm": 12000, "largeur_mm": 2500, "hauteur_mm": [2875, 3066], "empattement_mm": 6120, "porte_a_faux_avant_mm": 2710, "porte_a_faux_arriere_mm": 3170},
          "mm", "source secondaire (base documentaire d'amateurs), à confirmer par la fiche Iveco", S("TRANSBUS", "fiche Urbanway 12"), "moyenne", "donnee_constructeur"),
        P("BUS-PARC", "parc d'autobus et énergie", "autobus en circulation, 1/1/2026", "voir PARC-BUS-ENERGIE-2026", {"effectif": round(bus_tot)}, "véhicules", None, S("SDES2026", "tcp_national.xlsx"), "haute", "donnee_administrative"),
        P("BUS-CONFORT", "limites liées aux voyageurs debout", "autobus urbain", "seuils", {"acceleration_transversale_max_ms2": 1.0, "deceleration_visibilite_ms2": 2.0},
          "m/s²", None, S("VSA70", "p. 65", 2013), "haute", "norme"),
        P("BUS-VMAX", "vitesse maximale (limiteur)", "M3", "seuil", {"kmh": 100}, "km/h", None, S("D200285", "art. 2", 2002), "haute", "norme"),
        P("BUS-FREIN-REG", "freinage minimal", "M3", "seuil", {"mfdd_min_ms2": 5.0, "temps_reponse_max_s": 0.6}, "m/s² / s", None, S("R13", "annexe 4", 2016), "haute", "norme"),
    ]}
    C["bus_articule_18m"] = {"nom": "Autobus articulé 18 m", "categorie_UE": "M3 classe I", "parametres": [
        P("BUS18-DIM-CITARO-G", "dimensions et géométrie (Citaro G / eCitaro G)", "modèle de référence", "valeurs constructeur",
          {"longueur_mm": 18125, "largeur_mm": 2550, "hauteur_mm": {"Citaro_G": 3095, "eCitaro_G": 3400}, "empattement_avant_milieu_mm": 5900, "empattement_milieu_moteur_mm": 5990,
           "porte_a_faux_avant_mm": 2805, "porte_a_faux_arriere_mm": 3430, "diametre_giration_entre_murs_mm": 22970, "diametre_cercle_des_roues_mm": 19160,
           "largeur_couronne_min_mm": {"Citaro_G": 7478, "eCitaro_G_4_portes": 7178}, "angle_braquage_roue_avant_max_deg": "53 / 46"},
          "mm / degrés", None, S("CITARO", "p. 3-4"), "haute", "donnee_constructeur"),
        P("BUS18-MASSE-PUISSANCE", "PTAC et puissance", "Citaro G / eCitaro G", "valeurs constructeur",
          {"PTAC_kg": {"Citaro_G": 28000, "eCitaro_G_3_portes": 30000, "eCitaro_G_4_portes": 29000}, "puissance_kW": {"Citaro_G_OM470": 265, "Citaro_G_OM936": 220, "eCitaro_G_crete_continue": [440, 360]}},
          "kg / kW", None, S("CITARO", "p. 5, 8 ; eCitaro p. 4-7"), "haute", "donnee_constructeur"),
        P("BUS18-DIM-URBANWAY", "dimensions (Iveco Urbanway 18)", "modèle de référence", "valeurs",
          {"longueur_mm": 17910, "largeur_mm": 2500, "hauteur_mm": 3066, "empattement_avant_mm": 5355, "porte_a_faux_avant_mm": 2710, "porte_a_faux_arriere_mm": 3170, "rayon_braquage_m": 10.247,
           "puissance_kW": [265, 294]},
          "mm / m / kW", "source secondaire ; définition du rayon non précisée", S("TRANSBUS", "fiche Urbanway 18"), "moyenne", "donnee_constructeur"),
        P("BUS18-REF-DOCROUTE", "giration de référence des guides français", "bus articulé", "valeurs", {"rayon_interieur_m": 5.30, "rayon_balayage_m": 12.0, "longueur_max_m": 18.75},
          "m", None, S("DOCROUTE10", "CF p. 22 ; VU p. 301"), "haute", "norme"),
    ]}

    # Poids lourds (AEE HDV)
    def hdv_params(g, prefixe, pop):
        r = hdv["groupes"][g]
        out = [P(f"{prefixe}-PUISSANCE", "puissance moteur nominale", pop, "empirique (quantiles)", r["puissance_moteur_kW"], "kW", None,
                 S("AEE_HDV", "champ Engine_RatedPower_kw", 2025), "haute", "donnee_administrative"),
               P(f"{prefixe}-MASSE-CHASSIS", "masse du châssis-cabine en ordre de marche (« corrected actual mass » sans carrosserie)", pop, "empirique (quantiles)", r["masse_chassis_cabine_kg"], "kg",
                 "sans carrosserie ni semi-remorque", S("AEE_HDV", "champ CurbMassChassis_kg", 2025), "haute", "donnee_administrative"),
               P(f"{prefixe}-PTAC", "PTAC du véhicule moteur (déclaration État membre)", pop, "empirique (quantiles)", r["PTAC_kg_MS"], "kg", None,
                 S("AEE_HDV", "champ MS_TPMLM", 2025), "haute", "donnee_administrative"),
               P(f"{prefixe}-ENERGIE-BOITE", "énergie et type de boîte", pop, "catégorielle", {"energie": r["energie"], "boite": r["boite"], "n": r["n"]}, "véhicules", None,
                 S("AEE_HDV", None, 2025), "haute", "donnee_administrative")]
        miss = {m: {"nom": v["nom"], "masse_totale_kg": v["masse_totale_kg"], "puissance_masse_kW_t": v["puissance_masse_kW_t"]} for m, v in r["missions"].items()}
        out.append(P(f"{prefixe}-MASSE-MISSION", "masse totale et rapport puissance/masse aux charges de référence VECTO (L = faible, R = représentative)", pop,
                     "empirique (quantiles) par mission", miss, "kg ; kW/t",
                     "charges utiles normalisées par le règlement (UE) 2017/2400 (pas des charges observées) ; LH/RD/UD/RE/CO/MU = longue distance, régional, urbain, régional EMS, construction, municipal",
                     S("AEE_HDV", "champs *_TotalVehicleMass_kg", 2025), "moyenne", "derive"))
        return out

    C["pl_porteur"] = {"nom": "Porteur 4x2 > 16 t (groupe VECTO 4) et 6x2 (groupe 9)", "categorie_UE": "N3", "parametres":
        hdv_params("4", "PL4", "porteurs 4x2 > 16 t neufs France 2019-2023") + hdv_params("9", "PL9", "porteurs 6x2 neufs France 2019-2023") + [
        P("PL-PORTEUR-GIRATION-REF", "giration de référence des guides français", "camion", "valeurs", {"longueur_m": 11, "rayon_interieur_m": 6.50, "rayon_exterieur_m": 12.50},
          "m", None, S("DOCROUTE10", "VU p. 144"), "haute", "norme"),
        P("PL-VMAX", "vitesse maximale (limiteur)", "N2, N3", "seuil", {"kmh": 90, "AEE_HDV_vmax_p50_kmh": hdv["groupes"]["4"]["vitesse_max_kmh"]["p50"]}, "km/h",
          "la vitesse déclarée AEE vaut 0 pour une partie des lignes (non renseignée)", S("D200285", "art. 3", 2002), "haute", "norme")]}
    C["pl_semi_remorque"] = {"nom": "Tracteur 4x2 + semi-remorque 3 essieux (groupe VECTO 5)", "categorie_UE": "N3 + O4", "parametres":
        hdv_params("5", "PL5", "tracteurs 4x2 neufs France 2019-2023 (n = %d)" % hdv["groupes"]["5"]["n"]) + [
        P("PL5-DIM-REF", "dimensions de l'ensemble de vérification interurbain", "semi-remorque", "valeurs",
          {"tracteur_m": [6.08, 2.50], "semi_remorque_m": [13.67, 2.55], "longueur_max_m": 16.5, "pivot_arriere_max_m": 12.0}, "m", None,
          S("DOCROUTE10", "N05 p. 4 ; directive 96/53"), "haute", "norme"),
        P("PL5-MASSE-MAX", "masse maximale de l'ensemble", "5-6 essieux", "seuils", {"general_t": 40, "transport_combine_t": 44}, "t", None, S("D9653", "annexe I § 2.2.2", 2019), "haute", "norme")]}
    C["autocar"] = {"nom": "Autocar (interurbain, tourisme)", "categorie_UE": "M3 classe II-III", "parametres": [
        P("CAR-DIM-REF", "autocar de vérification interurbain", "autocar 15 m", "valeurs", {"longueur_m": 15.0, "largeur_m": 2.55, "essieux_arriere": "directionnels"}, "m", None, S("DOCROUTE10", "N05 p. 4"), "haute", "norme"),
        P("CAR-PARC", "parc d'autocars", "autocars en circulation 1/1/2026", "effectif", {"effectif": round(sdes_val(sdes, "tcp_national.xlsx", "Carburant détaillé", "Autocar"))}, "véhicules", None, S("SDES2026"), "haute", "donnee_administrative"),
    ]}

    # 2RM et micromobilité
    C["deux_roues_motorises"] = {"nom": "Deux-roues motorisés (cyclomoteur L1e, moto légère L3e-A1, moto lourde)", "categorie_UE": "L1e, L3e", "parametres": [
        P("2RM-PARC", "parc par sous-catégorie", "France 1/1/2025", "voir PARC-2RM-2025", {"cyclomoteurs": 516000, "motos_legeres": 860000, "motos_lourdes": 2064000}, "véhicules", None, S("ONISR2024", "p. 92 (PDF 94)", 2025), "moyenne", "donnee_administrative"),
        P("2RM-BORNES", "bornes réglementaires (vitesse, puissance, rapport puissance/masse)", "L1e, L3e-A1, L3e-A2", "seuils", "voir REG-CATEGORIES-L", "-", None, S("R168", "annexe I", 2013), "haute", "norme"),
        P("2RM-FREIN-REG", "décélération minimale homologuée", "L1, L3", "seuils", {"L1_combine": 4.4, "L3_combine": 5.1}, "m/s²", None, S("R78", "annexe 3 § 3.3", 2015), "haute", "norme"),
        P("2RM-DYN", "accélération, freinage réel, dimensions", "2RM", "non renseigné", None, "-", "lacune : aucune mesure ouverte exploitable retrouvée dans ce lot (sources candidates en accès restreint)", S("ONISR2024"), "faible", "estimation"),
    ]}
    C["velo_vae"] = {"nom": "Vélo et vélo à assistance électrique (VAE)", "categorie_UE": "hors réception (VAE <= 250 W, coupure 25 km/h)", "parametres": [
        P("VELO-GABARIT", "gabarit du cycliste", "vélo classique", "valeurs", {"largeur_cycliste_guidon_m": 0.75, "gabarit_dynamique_m": 1.00, "degagement_confort_m": 1.50, "hauteur_m": 2.50,
          "velos_speciaux_m": {"biporteur": [2.60, 0.70], "triporteur": [2.30, 0.90], "velo_allonge": [2.00, 0.50]}}, "m", None, S("RVC", "p. 17 et 45", 2022), "haute", "norme"),
        P("VELO-MASSE", "masse des vélos d'essai", "vélo et VAE instrumentés", "valeurs", {"velo_kg": 17.8, "vae_kg": 21.8}, "kg", "véhicules instrumentés (enregistreur inclus)", S("LI2023", "tableau 1"), "moyenne", "mesure"),
        P("VELO-FREIN", "décélération moyenne (modèle arctangente) en freinage", "36 participants, départ ~19-21 km/h", "normale (moyenne +- écart-type)",
          {"confort": {"velo": [1.66, 0.68], "vae": [1.69, 0.55]}, "brusque": {"velo": [3.93, 1.55], "vae": [4.24, 1.69]}}, "m/s²", "n = 28 à 36 essais par cas", S("LI2023", "tableau 4"), "haute", "mesure"),
        P("VELO-JERK", "jerk de freinage", "idem", "normale", {"confort": {"velo": [1.19, 1.64], "vae": [0.99, 0.80]}, "brusque": {"velo": [6.22, 4.74], "vae": [6.83, 5.60]}}, "m/s³", None, S("LI2023", "tableau 4"), "haute", "mesure"),
        P("VAE-ASSISTANCE", "coupure de l'assistance", "VAE (cycle à pédalage assisté)", "seuil", {"vitesse_kmh": 25, "puissance_nominale_W": 250}, "km/h / W", None, S("R168", "art. 2 § 2 h)", 2013), "haute", "norme"),
    ]}
    C["trottinette"] = {"nom": "Trottinette électrique (EDPM)", "categorie_UE": "hors réception", "parametres": [
        P("TROT-VMAX", "vitesse maximale par construction", "EDPM", "borne", {"kmh": 25}, "km/h", None, S("D2019_1082", "art. R. 311-1 6.15", 2019), "haute", "norme"),
        P("TROT-MASSE", "masse des trottinettes d'essai", "petite (Segway Ninebot ES2, usage personnel) et grande (Segway Max Plus X, modèle de libre-service)", "valeurs", {"petite_kg": 11.3, "grande_kg": 31.5}, "kg", None, S("LI2023", "tableau 1"), "moyenne", "mesure"),
        P("TROT-FREIN", "décélération moyenne en freinage", "36 participants, départ 20-24 km/h", "normale", {"confort": {"petite": [1.65, 0.56], "grande": [1.98, 0.59]}, "brusque": {"petite": [2.92, 1.00], "grande": [4.04, 1.24]}},
          "m/s²", None, S("LI2023", "tableau 4"), "haute", "mesure"),
        P("TROT-JERK", "jerk de freinage", "idem", "normale", {"confort": {"petite": [0.98, 0.91], "grande": [1.15, 0.84]}, "brusque": {"petite": [3.17, 2.69], "grande": [4.97, 3.30]}}, "m/s³", None, S("LI2023", "tableau 4"), "haute", "mesure"),
        P("TROT-FREIN-AUTRES", "décélérations maximales citées (source secondaire)", "trottinette Egret One V3, vélo, Segway", "valeurs", {"trottinette": 3.1, "velo": 6.5, "segway": 4.5, "exigence_allemande_eKFV_min": 3.5},
          "m/s²", "cité par Siebert et al. d'après Bierbach et al. (BASt, 2018) ; eKFV § 4 (Allemagne)", S("SIEBERT2021", "p. 6-7 (manuscrit)"), "faible", "mesure"),
    ]}
    # braquage dérivé (géométrie d'Ackermann) pour les voitures dont empattement, diamètre et voie sont connus
    voies = defaultdict(list)
    for r in vp21:
        if r["v1"]:
            voies[r["Cn"].upper()].append((r["v1"], r["n"]))
    nom_aee = {"clio5_tce90": "CLIO", "p208_pt100": "208", "sandero3_tce90": "SANDERO", "captur2_mh160": "CAPTUR", "p2008_pt130": "2008", "e208_156": "208"}
    braq = []
    for r in adac["vehicules"]:
        c = r["constructeur"]
        if r["id"] in nom_aee and c.get("empattement_mm") and c.get("diametre_braquage_m") and voies.get(nom_aee[r["id"]]):
            L_ = c["empattement_mm"] / 1000; R_ = c["diametre_braquage_m"] / 2
            t_ = quantiles_ponderes(voies[nom_aee[r["id"]]])["p50"] / 1000
            d_ext = math.degrees(math.asin(L_ / R_))
            x = R_ * math.cos(math.radians(d_ext))            # distance centre de virage - roue avant extérieure, projetée
            d_int = math.degrees(math.atan(L_ / (x - t_)))
            r_arr = x - t_ / 2
            braq.append({"id": r["id"], "empattement_m": L_, "rayon_braquage_m": R_, "voie_m": t_, "angle_roue_ext_deg": round(d_ext, 1),
                         "angle_roue_int_deg": round(d_int, 1), "angle_bicyclette_deg": round(math.degrees(math.atan(L_ / r_arr)), 1),
                         "rayon_min_centre_essieu_arriere_m": round(r_arr, 2)})
    C["_dynamique_VP"]["parametres"].append(P(
        "VP-BRAQUAGE-DERIVE", "angles de braquage maximaux et rayon minimal du centre de l'essieu arrière", "6 voitures de référence",
        "valeurs dérivées", {"modeles": braq, "methode": "rayon R = diamètre constructeur / 2 rapporté à la roue avant extérieure ; delta_ext = asin(L/R) ; delta_int = atan(L / (R cos delta_ext - voie)) ; rayon arrière = R cos delta_ext - voie/2 ; modèle bicyclette delta = atan(L / rayon arrière)"},
        "degrés / m", "approximation : la convention du diamètre constructeur (bord du pneu ou centre de roue) n'est pas précisée ; erreur de l'ordre du demi-pneu (~0,1 m)",
        S("ADAC_CAT", "empattement et diamètre de braquage ; voie : AEE 2021"), "moyenne", "derive"))
    J["classes"] = C

    # ====================================================================== statistiques globales et comparaison SUMO
    J["marche_VP_2024_ensemble"] = {"masse_UE_kg": quantiles_ponderes(tout_m), "puissance_masse_W_kg": quantiles_ponderes(tout_pm),
                                    "source": S("AEE_VP", "co2cars_2024Fv30, MS=FR", 2025)}
    J["comparaison_sumo_1_27_1"] = {
        "source": S("SUMO1271", "tableaux « Passenger Cars and Light Delivery », « Trucks and Busses », vélos et 2RM"),
        "valeurs_par_defaut": {
            "passenger": {"longueur_m": 5.0, "largeur_m": 1.8, "masse_kg": 1500, "accel_ms2": 2.6, "decel_ms2": 4.5, "emergencyDecel_ms2": 9.0, "maxSpeed_kmh": 200},
            "delivery": {"longueur_m": 6.5, "largeur_m": 2.16, "masse_kg": 5000, "accel_ms2": 2.6, "decel_ms2": 4.5, "emergencyDecel_ms2": 9.0},
            "truck": {"longueur_m": 7.1, "largeur_m": 2.4, "masse_kg": 4500, "accel_ms2": 1.3, "decel_ms2": 4.0, "emergencyDecel_ms2": 7.0, "maxSpeed_kmh": 130},
            "trailer": {"longueur_m": 16.5, "largeur_m": 2.55, "masse_kg": 13000, "accel_ms2": 1.0, "decel_ms2": 4.0, "emergencyDecel_ms2": 7.0},
            "bus": {"longueur_m": 12.0, "largeur_m": 2.5, "masse_kg": 12000, "accel_ms2": 1.2, "decel_ms2": 4.0, "emergencyDecel_ms2": 7.0, "maxSpeed_kmh": 85},
            "motorcycle": {"longueur_m": 2.2, "largeur_m": 0.9, "masse_kg": 200, "accel_ms2": 6.0, "decel_ms2": 10.0, "emergencyDecel_ms2": 10.0},
            "moped": {"longueur_m": 2.1, "largeur_m": 0.8, "masse_kg": 80, "accel_ms2": 1.1, "decel_ms2": 7.0, "emergencyDecel_ms2": 10.0, "maxSpeed_kmh": 45},
            "bicycle": {"longueur_m": 1.6, "largeur_m": 0.65, "masse_kg": 10, "accel_ms2": 1.2, "decel_ms2": 3.0, "emergencyDecel_ms2": 7.0, "maxSpeed_kmh": 50, "desiredMaxSpeed_kmh": 20},
            "scooter": {"longueur_m": 1.2, "largeur_m": 0.5, "masse_kg": 10, "accel_ms2": 1.2, "decel_ms2": 3.0, "emergencyDecel_ms2": 7.0, "maxSpeed_kmh": 25}},
        "ecarts_notables": [
            "SUMO : une accélération constante par type (passenger 2,6 m/s²) ; mesures ADAC : de 4,1 m/s² au démarrage (électriques) à ~1,8 m/s² en reprise thermique à bas régime, décroissante avec la vitesse (moyenne 60-100 km/h : 1,4 à 3,5 m/s² ; 80-120 km/h : 1,0 à 3,1 m/s²)",
            "SUMO : longueur passenger 5,0 m ; citadines testées 4,02-4,09 m, SUV C 4,54-4,80 m",
            "SUMO : emergencyDecel passenger 9 m/s² ; ADAC 100-0 km/h : 10,0-11,6 m/s² équivalents (pneus neufs, piste) ; Greibe 2007 sur route : 8,4 (pros) et 7,4 (non-pros)",
            "SUMO : bicycle decel 3 m/s², emergencyDecel 7 m/s² ; mesures LI2023 freinage brusque : 3,9 +- 1,6 (vélo), 4,2 +- 1,7 (VAE), 2,9 +- 1,0 (petite trottinette)",
            "SUMO : bus 12 000 kg, accel 1,2 ; fiches Citaro : PTAC 19 500-20 000 kg, 220-440 kW"]}

    J["lacunes"] = [
        "Dimensions (longueur, largeur, hauteur, porte-à-faux) des VUL moyens et grands, des porteurs et des tracteurs : non publiées par l'AEE ; fiches constructeurs à collecter (Master, Trafic, Renault Trucks T et D, semi-remorque standard).",
        "Masse à vide des autobus 12 m et 18 m : absente des fiches Citaro ; à collecter (fiches techniques détaillées ou registres d'exploitants).",
        "Montée en pression des freins des VP (temps d'établissement, jerk d'urgence) : aucune mesure ouverte trouvée ; borne réglementaire seulement.",
        "Accélération réelle des PL et bus (départ arrêté, rampes) : pas de mesure ouverte retrouvée ; le modèle physique utilise P/m (AEE) et un k non calé pour ces classes.",
        "Deux-roues motorisés : dimensions, puissances, accélérations et freinages mesurés absents (articles d'essais en accès restreint) ; seules les bornes R78 et 168/2013 et le parc ONISR sont fournis.",
        "Distribution des CxS des VP : une seule valeur publiée (208) ; l'estimation largeur x hauteur est faiblement validée (sensibilité 80-120 de 3 à 6 %).",
        "Adhérence transversale mesurée (dérapage) : seuls les coefficients de projet (cfts) sont disponibles.",
        "Charges réelles des PL (taux de chargement observé) : les masses de mission VECTO sont normalisées ; données de pesage en marche (Cerema) non collectées.",
        "Parc roulant ancien : les distributions de masse et de puissance décrivent les véhicules neufs (2021, 2024) ; l'âge moyen du parc VP est de 11,8 ans (SDES). Seule la part des familles de motorisation est ramenée au parc (PARC-VP-FAMILLE-2026).",
        "Accélération des thermiques à boîte manuelle sous 30 km/h : le plafond a_lancement = µ g × 0,6 = 5,89 m/s² est une estimation (adhérence), pas une mesure ; l'ADAC mesure un « Anfahrverhalten » 15-30 km/h de 1,5 à 2,0 m/s² (rapport engagé non précisé), alors que Salles 2020 mesure des pics de démarrage de 2,1 ± 0,5 m/s² (> 2 000 démarrages de véhicules thermiques) : profil a(v) à bas régime non établi.",
        "Boîte automatique non hybride : non identifiable dans les données AEE (rangée dans la famille manuelle).",
        "Segmentation VP : faite sur le nom des modèles (convention), couvre la part indiquée dans _diagnostic_segmentation.",
    ]
    return J


def main():
    J = construire()
    sortie = VOLET / "vehicules_parametres.json"
    json.dump(J, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    COPIE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(sortie, COPIE)
    n_par = sum(len(v.get("parametres", [])) for v in J["classes"].values()) + sum(len(J[k]) for k in ["parc_france", "composition_trafic", "adherence", "reglementation", "freinage_systeme"])
    print("écrit", sortie, "et", COPIE, "-", n_par, "paramètres ; couverture segmentation VP 2024 :", J["_diagnostic_segmentation"]["part_classee"])
    for seg in ["citadine", "compacte", "berline", "suv_b", "suv_c", "monospace_ludospace"]:
        p = {x["id"]: x["parametres"] for x in J["classes"][seg]["parametres"]}
        m = p[f"{seg.upper()}-MASSE"]; pm = p[f"{seg.upper()}-PUISSANCE-MASSE"]; w = p[f"{seg.upper()}-EMPATTEMENT"]; pa = p[f"{seg.upper()}-PART-MARCHE"]
        print(f"{seg:20s} part {pa['part']:.3f} BEV {pa['part_electrique_dans_segment']} masse p50 {m['p50']} [{m['p5']}-{m['p95']}] P/m p50 {pm['p50']} [{pm['p5']}-{pm['p95']}] W p50 {w['p50'] if w else None}")
    for seg in ["vul_petit", "vul_moyen", "vul_grand"]:
        p = {x["id"]: x["parametres"] for x in J["classes"][seg]["parametres"]}
        print(seg, {k.split('-', 1)[1]: (v.get('p50'), v.get('p5'), v.get('p95')) for k, v in p.items() if isinstance(v, dict) and 'p50' in v})
    print("non classés principaux :", J["_diagnostic_segmentation"]["principaux_non_classes"][:12])


if __name__ == "__main__":
    main()
