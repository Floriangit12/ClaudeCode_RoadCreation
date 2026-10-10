# -*- coding: utf-8 -*-
"""Construit assets/specs/regles_locales_meylan.json (agent DOC-LOCALE)."""
import json, os, hashlib

R = "D:/ClaudeCode_RoadCreation/"
DW = "data/raw/docs_web/"
WEB = "recon/out/paquet_jardin/v2/enrichi/recensement/web/"
GUIDE = DW + "grenoblealpesmetropole/guide_espaces_publics/"
WB = "copie Wayback Machine (web.archive.org) car le fichier a été retiré du site de la Métropole en 2024-2025"
LIC_COLL = "document public d'une collectivité, téléchargé pour analyse interne ; droits réservés à l'auteur, non redistribué"


def taille(p):
    try:
        return os.path.getsize(R + p)
    except OSError:
        return None


def sha(p):
    try:
        h = hashlib.sha256()
        with open(R + p, "rb") as f:
            h.update(f.read())
        return h.hexdigest()[:16]
    except OSError:
        return None


S = {}


def src(i, titre, typ, url, date, fichier=None, lecture="texte intégral", licence=LIC_COLL, note=None):
    d = {"id": i, "titre": titre, "type": typ, "url": url, "date": date, "lecture": lecture,
         "fichier_local": fichier, "taille_octets": taille(fichier) if fichier else None,
         "sha256_16": sha(fichier) if fichier else None, "licence": licence}
    if note:
        d["note"] = note
    S[i] = d


GAMF = "https://www.grenoblealpesmetropole.fr/cms_viewFile.php?idtf=%d&path=%s"
src("GAM_GUIDE", "Guide métropolitain des espaces publics et de la voirie — « Cinq principes globaux pour des aménagements locaux » (livret, 28 p.)",
    "guide_collectivite", GAMF % (1916, "Guide-metropolitain-des-espaces-public-et-de-la-voirie.pdf"), "2017 (annexé à la délibération-cadre de février 2017)",
    GUIDE + "Guide-metropolitain-des-espaces-public-et-de-la-voirie.pdf", note=WB + " (capture 2021-11-02)")
fiches = {1: (2408, "Donner envie de marcher"), 2: (2409, "Pourquoi pas à vélo ?"), 3: (2411, "Des transports en commun intégrés dans leur environnement"),
          4: (2410, "Vivre et se déplacer serein dans la ville à 30"), 5: (2495, "La voiture bien utilisée"), 6: (2412, "Je prends en compte l'accessibilité"),
          7: (2413, "Usages d'aujourd'hui et de demain"), 8: (2414, "Un espace fonctionnel agréable à vivre au quotidien"), 9: (2415, "Pendant le chantier, la vie continue"),
          10: (2416, "Nature : une valeur ajoutée au projet"), 11: (2417, "L'eau de pluie, une richesse locale"), 12: (2418, "Paysage : différents plans à préserver"),
          13: (2419, "Je participe à la protection de la santé"), 14: (2420, "Concerter"), 15: (2421, "Un patrimoine vivant"),
          16: (2422, "Pour un meilleur partage de l'espace public : les nouveaux réflexes"), 17: (2423, "Grille d'analyse et d'évaluation"),
          18: (2496, "De la demande à la réponse : co-construction Métropole/commune"), 19: (2424, "Faire mieux avec moins")}
for n, (idtf, t) in fiches.items():
    f = "Espaces-publics-Fiche-%d.pdf" % n
    src("GAM_F%02d" % n, "Guide métropolitain des espaces publics et de la voirie, fiche n°%d « %s »" % (n, t), "guide_collectivite",
        GAMF % (idtf, f), "2017-2018", GUIDE + f, note=WB)
src("GAM_RGV", "Règlement général de voirie métropolitaine — dispositions administratives (Grenoble-Alpes Métropole, 06/07/2018)", "reglement_collectivite",
    GAMF % (195, "Reglement-general-de-voirie-metropolitaine.pdf"), "2018-07-06", DW + "grenoblealpesmetropole/Reglement-general-de-voirie-metropolitaine.pdf",
    note="le volume « dispositions techniques » n'a pas été trouvé")
src("GAM_CHARTE_ARBRE", "Charte de l'arbre — guide technique en faveur de la protection et du développement du patrimoine arboré (Grenoble-Alpes Métropole, 2019)", "charte_collectivite",
    "https://www.biodiversite-auvergne-rhone-alpes.fr/wp-content/uploads/2023/11/Charte-de-l-Arbre-Grenoble-Alpes-Metropole-1-1.pdf", "2019",
    DW + "biodiversite_aura/Charte-de-l-Arbre-Grenoble-Alpes-Metropole.pdf", note="original : " + GAMF % (2920, "charte-de-l-arbre.pdf"))
src("GAM_REX_CHRONO", "« Chronovélo et tramway à Grenoble : quelles solutions retenues » — Grenoble-Alpes Métropole et SMMAG, webinaire Cerema « Tramway et aménagements cyclables » du 29/11/2022",
    "presentation_collectivite", "https://www.cerema.fr/system/files/documents/2022/12/5_rdvmob_velos_tramway_rex_grenoblealpesmetropole.pdf", "2022-11-29",
    DW + "cerema/5_rdvmob_velos_tramway_rex_grenoblealpesmetropole.pdf", note="seule source publique trouvée de la charte graphique Chronovélo (p. 7 et 9)")
src("GAM_CHRONO_2018", "Projet Chronovélo, réunion publique du 4 décembre 2018 (Grenoble-Alpes Métropole)", "presentation_collectivite",
    "https://cluq-grenoble.org/WordPress/wp-content/uploads/2018/11/Projet-Chronov%C3%A9lo-Grenoble-Alpe-M%C3%A9tropole-r%C3%A9union-publique-04122018-V2.pdf", "2018-12-04",
    DW + "cluq/Projet-Chronovelo-GAM-reunion-publique-04122018-V2.pdf", note="hébergé par le CLUQ Grenoble")
src("GAM_CARTE_CHRONO_2026", "Carte « Axes Chronovélo » (janvier 2026), Grenoble-Alpes Métropole", "carte_collectivite",
    GAMF % (1507, "Carte-Chronovelo-janvier-2026.pdf"), "2026-01", DW + "grenoblealpesmetropole/Carte-Chronovelo-janvier-2026.pdf",
    lecture="carte vectorielle (zoom Meylan)", note="copie Wayback du 2026-03-08")
src("GAM_JTR_2018", "L. Faure (Grenoble-Alpes Métropole), « Métropole apaisée et aménagements modes actifs », Journées techniques de la route 2018", "presentation_collectivite",
    "https://jtr.univ-gustave-eiffel.fr/fileadmin/contributeurs/JTR/Annee_2018/Presentations_2018/Session2/3_Faure_Grenoble.pdf", "2018",
    DW + "univ_eiffel_jtr/3_Faure_Grenoble_JTR2018.pdf")
src("GAM_ABECEDAIRE", "Abécédaire de la Métropole apaisée (Grenoble-Alpes Métropole)", "plaquette_collectivite",
    "https://www.saint-egreve.fr/fileadmin/Prevention_securite/Metropole_apaisee/Abecedaire-Metropole-apaisee.pdf", "2016-2017", DW + "saint_egreve/Abecedaire-Metropole-apaisee.pdf")
src("GRENOBLE_DP_MA", "Dossier de presse « Métropole apaisée » (Ville de Grenoble)", "presse_collectivite",
    "https://www.grenoble.fr/uploads/Presse/pse_fichier/1e/53_136_dossier-de-presse-metropole-apaisee.pdf", "2015-12", DW + "grenoble_fr/dossier-de-presse-metropole-apaisee.pdf")
src("CEREMA_MA_2020", "Cerema Centre-Est, « Grenoble Métropole apaisée — évaluation du dispositif villes et villages à 30 km/h » (juillet 2020)", "rapport_etat",
    "https://www.cerema.fr/system/files/documents/2020/07/cerema_ce_grenoble_rapport_ma_3a_vfinale.pdf", "2020-07", DW + "cerema/cerema_ce_grenoble_rapport_ma_3a_vfinale.pdf")
src("CEREMA_Z30_2023", "Cerema, « Principes d'aménagement des zones 30 », Club sécurité routière du 27/06/2023 (diffusé par la préfecture de l'Aude)", "presentation_etat",
    "https://www.aude.gouv.fr/contenu/telechargement/25951/178929/file/Cerema_principes_amenagements_zone_30_23-06-27.pdf", "2023-06-27",
    DW + "aude_gouv/Cerema_principes_amenagements_zone_30_23-06-27.pdf", note="p. 18 : gabarit de l'ellipse « 30 » adopté par Grenoble")
MEY = "https://www.meylan.fr/include/viewfilesecure.php?idtf=%d&path=%s"
MEYC = "https://www.meylan.fr/cms_viewFile.php?idtf=%d&path=%s"
src("MEY_PANNEAU_CARREFOUR", "Panneau « Aménagement carrefour Verdun/Vercors » (Ville de Meylan, Métropole, SMMAG)", "panneau_projet",
    MEY % (9331, "Panneau-Amenagement-carrefour-Verdun-Vercors.pdf"), "2025-04-03", DW + "meylan_fr/Panneau-Amenagement-carrefour-Verdun-Vercors.pdf",
    note="même image que le plan projet 2025 déjà géoréférencé dans data/sites/paquet_jardin/plan_projet_2025")
src("MEY_PANNEAU_VERCORS", "Panneau « Aménagement avenue du Vercors » (définition d'une traversée sécurisée ; exemple de la traversée piscine des Buclos)", "panneau_projet",
    MEY % (9330, "panneau-amenagement-avenue-du-vercors.pdf"), "2025-04-03", DW + "meylan_fr/panneau-amenagement-avenue-du-vercors.pdf")
src("MEY_PANNEAU_GRANIER", "Panneau « Aménagement avenue du Granier »", "panneau_projet", MEY % (9332, "panneau-amenagement-avenue-du-granier.pdf"), "2025-04-03",
    DW + "meylan_fr/panneau-amenagement-avenue-du-granier.pdf")
src("MEY_PANNEAU_C1", "Panneau générique « Travaux d'amélioration de la ligne C1 »", "panneau_projet", MEY % (9333, "Panneau-generique-travaux-d-amelioration-ligne-C1.pdf"),
    "2025-04-03", DW + "meylan_fr/Panneau-generique-travaux-d-amelioration-ligne-C1.pdf")
src("MEY_PRES_2024", "Réunion publique du 14/05/2024, 1re phase du réaménagement Vercors-Granier (Métropole, Meylan, SMMAG)", "presentation_projet",
    MEY % (8054, "Presentation-reunion-publique-14-05-24.pdf"), "2024-05-14", DW + "meylan_fr/Presentation-reunion-publique-14-05-24.pdf")
src("MEY_PRES_2025", "Réunion publique du 03/04/2025, seconde phase du réaménagement des avenues Vercors et Granier", "presentation_projet",
    MEY % (9329, "presentation-reunion-C1-03-04-25.pdf"), "2025-04-03", DW + "meylan_fr/presentation-reunion-C1-03-04-25.pdf")
for n, idtf, f, d in [(164, 9680, "MMV-164-etet-2025.pdf", "2025-06"), (165, 10115, "MMV-165.pdf", "2025-10"), (166, 10404, "MMV-166-decembre25-janvier26.pdf", "2025-12"),
                      (167, 10722, "MMV-167-fevrier-mars-2026.pdf", "2026-02"), (168, 11277, "MMV-168-juin-ete-26.pdf", "2026-06")]:
    src("MEY_MMV%d" % n, "Meylan ma ville n°%d (journal municipal)" % n, "magazine_municipal", MEYC % (idtf, f), d, DW + "meylan_fr/" + f)
src("MEY_PAGE_C1", "Page « Ligne C1+ » (meylan.fr/311-ligne-c1.htm) et pages travaux (actualités 1108, 1129, 1227 expirées)", "page_web",
    "https://www.meylan.fr/311-ligne-c1.htm", "2025-2026", None, lecture="page web lue en ligne (non téléchargée)")
src("MEY_CHARTE_URBA", "Charte communale d'urbanisme de Meylan (septembre 2026)", "charte_commune", MEYC % (11733, "Charte-urba-2026.pdf"), "2026-09",
    DW + "meylan_fr/Charte-urba-2026.pdf")
src("MEY_LIVRET_HAIES", "« Quelle haie, quelle clôture pour mon jardin ? » — cahier pédagogique (Ville de Meylan, CEM ; extraits du PLUi métropolitain et de l'OAP Paysage et biodiversité)",
    "guide_commune", MEYC % (10109, "Livret-haies-et-clotures.pdf"), "2024-01", DW + "meylan_fr/Livret-haies-et-clotures.pdf")
src("DATAGOUV_ARBRES", "Patrimoine arboré du territoire métropolitain (Grenoble-Alpes Métropole), jeu archivé", "donnees_ouvertes",
    "https://www.data.gouv.fr/datasets/patrimoine-arbore-du-territoire-metropolitain", "2023-09-11", DW + "data_gouv_arbres/patrimoine_arbore.geojson",
    lecture="données (filtrées à 160 m du site)", licence="ODbL 1.0 (Grenoble-Alpes Métropole)", note="CSV : " + DW + "data_gouv_arbres/patrimoine_arbore.csv")
src("OSM_2026", "OpenStreetMap, extrait Overpass (base du 2026-05-31) autour du carrefour", "donnees_ouvertes", "https://overpass.kumi.systems/api/interpreter",
    "2026-05-31", WEB + "preuves/osm_extrait_site_2026-05-31.json", lecture="données ; éditions postérieures à septembre 2025",
    licence="ODbL 1.0 — © contributeurs OpenStreetMap")
src("BOAMP_C1", "Avis BOAMP 24-127427 « Travaux de réaménagement des avenues du Vercors et du Granier – Meylan » (marché 2024-TX-ACP-0331, 3 lots)", "avis_marche",
    "https://lacentraledesmarches.com/marches-publics/Meylan-Grenoble-Alpes-Metropole-Travaux-de-reamenagement-des-avenues-du-Vercors-et-du-Granier--Meylan/319899",
    "2024-11-08", None, lecture="page web ; DCE non consulté (consultation close, accès par formulaire)")
src("GAM_PANNEAUX_VELO", "Affiche « À vélo : les panneaux de signalisation à connaître » (Grenoble-Alpes Métropole)", "affiche_collectivite",
    GAMF % (1792, "Panneaux-de-signalisation-velo.pdf"), "2025", GUIDE + "Panneaux-de-signalisation-velo.pdf", lecture="image", note=WB)

LIENS_DOC = {}

regles = []


def r(i, famille, sous, enonce, parametres, condition, action, source, ref, confiance, statut="immediate", second=None,
      sec=None, liens=None, conflits=None, notes=None):
    s = S[source]
    d = {"id": i, "famille": famille, "sous_famille": sous, "enonce": enonce, "parametres": parametres,
         "condition": condition, "action": action}
    if second:
        d["actions_secondaires"] = second
    d["source"] = {"id": source, "doc": s["titre"], "ref": ref, "url": s["url"], "fichier_local": s["fichier_local"]}
    if sec:
        d["sources_secondaires"] = [{"id": a, "doc": S[a]["titre"], "ref": b, "url": S[a]["url"]} for a, b in sec]
    d["confiance"] = confiance
    d["applicabilite"] = {"statut": statut}
    if liens:
        d["liens"] = liens
    if conflits:
        d["conflits"] = conflits
    if notes:
        d["notes"] = notes
    regles.append(d)


# ------------------------------------------------------------------ contexte et gestion
r("LOC-CTX-001", "contexte", "gestionnaire",
  "Les trois voies du site (avenue de Verdun RD 1090, avenue du Vercors, chemin de la Revirée) sont des voies métropolitaines : la Métropole exerce la compétence voirie depuis le 1er janvier 2015 et les routes départementales de son territoire lui ont été transférées le 1er janvier 2017. Les règles locales applicables sont donc celles de Grenoble-Alpes Métropole (guide des espaces publics et de la voirie, règlement de voirie, charte de l'arbre, charte Chronovélo). Aucune règle du Département de l'Isère ne s'applique au marquage ni aux équipements de la RD 1090 dans le site ; le numéro « D 1090 » n'est qu'un repère.",
  {"gestionnaire_voirie": "Grenoble-Alpes Métropole", "transfert_routes_departementales": "2017-01-01", "competence_voirie_metropole": "2015-01-01",
   "autorite_mobilite": "SMMAG (depuis 2020), réseau M réso exploité par M TAG", "urbanisme": "PLUi de Grenoble-Alpes Métropole et OAP Paysage et biodiversité (ambiances de Meylan)"},
  "toujours", "contraindre", "GAM_CHARTE_ARBRE", "édito, p. imprimée 3 (PDF p. 2)", "haute",
  sec=[("GAM_F18", "chap. I, compétences voirie et espaces publics (bordures, îlots, potelets, arbres, mobilier standard)")],
  notes="Conséquence pour la recherche documentaire : l'absence de règles départementales n'est pas une lacune.")

r("LOC-CTX-002", "contexte", "etat_ouvrages_2026",
  "Âge des ouvrages en octobre 2026. Le carrefour a été refait du 23 juin au 5 décembre 2025 (fin annoncée en décembre 2025) ; les trottoirs et la végétalisation de l'avenue du Vercors ont duré jusqu'au 30 janvier 2026. En octobre 2026, les ouvrages de 2025 ont environ 10 mois : enrobés neufs et sombres, marquages neufs (blanc franc, jaune vif, sans usure), bordures et joints propres, sans mousse ni herbe, plantations dans leur première saison de végétation. Hors des zones de travaux, l'usure observée avant 2025 reste valable.",
  {"travaux_carrefour": ["2025-06-23", "2025-12-05"], "fin_annoncee": "2025-12", "vercors_trottoirs_vegetalisation_jusqu_au": "2026-01-30",
   "age_ouvrages_mois": 10, "usure_marquage_zone_travaux": 0, "mousse_joints_zone_travaux": 0, "herbe_joints_zone_travaux": 0,
   "marche": {"avis": "BOAMP 24-127427", "reference": "2024-TX-ACP-0331",
              "lots": ["1 voirie et réseaux divers", "2 espaces verts, revêtements qualitatifs, mobilier spécifique et serrurerie", "3 signalisation lumineuse tricolore et éclairage public"]}},
  "entité dont l'état est « neuf 2025 » ou située dans une zone de travaux 2025 (relief_zones_2026)", "generer", "MEY_MMV166", "p. 7 (« Fin des travaux en décembre 2025 »)", "moyenne",
  second=["contraindre"], sec=[("MEY_MMV165", "p. 12"), ("MEY_PAGE_C1", "calendrier du chantier ; actualité « Travaux C1 : carrefour Verdun/Vercors »"), ("BOAMP_C1", "lots et durées")],
  liens=["regles_pcg:R-joints-herbe", "regles_pcg:R-joints-mousse", "peinture.json (usure)"])

r("LOC-CTX-003", "contexte", "bilan_projet",
  "Bilan annoncé de la phase 2 (Vercors, Granier et carrefour Verdun/Vercors) : surfaces végétalisées de 1 700 à 2 400 m², trottoirs de 1 800 à 2 300 m², chaussée et îlots bitumés de 7 350 à 6 130 m², 94 arbres à planter, 11 traversées piétonnes réaménagées. Sert de contrôle de tendance : la description 2026 du carrefour doit avoir moins d'enrobé circulé et plus de surfaces plantées et piétonnes que l'état 2022, jamais l'inverse.",
  {"surface_vegetalisee_m2": [1700, 2400], "trottoir_m2": [1800, 2300], "chaussee_ilots_bitumes_m2": [7350, 6130], "arbres_objectif_n": 94,
   "traversees_reamenagees_n": 11, "reduction_chaussee_annoncee_pct": 11, "reduction_chaussee_calculee_pct": 16.6},
  "comparaison des surfaces 2022 et 2026 sur l'emprise du projet", "verifier", "MEY_PRES_2025", "p. 7", "moyenne",
  notes="Le document annonce -11 % mais ses chiffres donnent -16,6 % ; périmètre plus large que le site.")

# ------------------------------------------------------------------ vitesses (Métropole apaisée)
r("LOC-VIT-001", "vitesse", "metropole_apaisee",
  "Meylan applique depuis 2022 la « Métropole apaisée » : en agglomération, 30 km/h est la règle et 50 km/h l'exception, réservée aux axes signalés par un marquage « 50 ». En l'absence de ce marquage, la vitesse limite est de 30 km/h. Dans le site, l'avenue de Verdun reste à 50 km/h (ellipses « 50 » relevées) ; l'avenue du Vercors et le chemin de la Revirée sont à 30 km/h (ellipses « 30 » de rappel relevées en 2022 à leur entrée). Le maxspeed=50 d'OSM sur ces deux voies (source:maxspeed=FR:urban) est une valeur par défaut erronée et ne doit pas alimenter le .xodr ni les scénarios ADAS.",
  {"vitesse_defaut_agglomeration_kmh": 30, "axes_50": ["avenue de Verdun (RD 1090)"], "axes_30": ["avenue du Vercors", "chemin de la Revirée", "voies de desserte"],
   "adhesion_meylan": 2022, "osm_maxspeed_a_ignorer": True},
  "attribut de vitesse des routes .xodr, des panneaux et des scénarios", "contraindre", "GAM_F04", "p. 7, « Connaître les règles élémentaires du code de la rue »", "haute",
  second=["verifier"], sec=[("MEY_MMV164", "p. 10 (« Meylan a intégré en 2022 le dispositif Métropole apaisée »)"), ("CEREMA_MA_2020", "p. 11"), ("GAM_ABECEDAIRE", "entrées « panneau » et « vitesse »")],
  liens=["MQ-Z30-001", "MQ-V50-001"],
  notes="Application au site : confiance moyenne tant qu'aucune photo de 2026 ne montre les ellipses « 30 » reposées après la réfection du Vercors.")

r("LOC-VIT-002", "vitesse", "signalisation_vitesse",
  "Signalisation des vitesses dans la Métropole apaisée. Aucun panneau B14 « 30 » ou « 50 », ni B30/B51 de zone 30, à l'intérieur de la commune : le panneau B30 n'existe qu'en entrée d'agglomération, sur le mât du panneau d'entrée. Sur un axe à 50, une ellipse « 50 » est peinte juste après l'entrée d'agglomération et après les intersections. À chaque intersection avec une rue à 30, la limitation est rappelée par une ellipse « 30 », plus grande que l'ellipse « 50 », peinte au début de la rue à 30, dans chaque voie et dans le sens de circulation.",
  {"panneaux_vitesse_dans_le_site": 0, "ellipse_50": "après chaque intersection sur Verdun, dans chaque voie", "ellipse_30": "début de chaque rue à 30 issue du carrefour (Vercors sortant, Revirée sortante), une par voie",
   "rapport_tailles": "ellipse 30 plus grande que ellipse 50"},
  "génération de la signalisation verticale et des inscriptions de vitesse", "contraindre", "CEREMA_MA_2020", "p. 11", "haute",
  second=["deduire_si_absent"], sec=[("GAM_JTR_2018", "p. 6"), ("GAM_F16", "p. 5, « Supprimer tous les panneaux zone 30, limitation à 30 et 50 km/h »"), ("GRENOBLE_DP_MA", "p. 2")],
  liens=["MQ-Z30-001", "MQ-V50-001", "SIG-01"],
  conflits=["CF-LOC-01"],
  notes="Déduction admise seulement pour reposer à l'identique une ellipse relevée en 2022 sur une chaussée refaite en 2025 (même voie, même position longitudinale) ; sinon la règle MQ-Z30-001 (jamais déduit) s'applique.")

r("LOC-VIT-003", "vitesse", "gabarit_ellipse_30",
  "Gabarit grenoblois de l'ellipse « 30 » : 1,20 m de large sur 2,40 m de long, chiffres de 1,30 m de haut, centrée dans la voie et lisible dans le sens de circulation ; dimensions homogènes dans toute l'agglomération. Le gabarit mesuré sur le site (2,45 × 1,28 m) en est la réalisation : il est conservé.",
  {"ellipse_m": {"largeur": 1.2, "longueur": 2.4}, "hauteur_chiffres_m": 1.3, "cote_superieure_m": 0.6, "position": "milieu de chaque voie", "site_mesure_m": {"longueur": 2.45, "largeur": 1.28}},
  "fabrication du glyphe RAPPEL_30", "generer", "CEREMA_Z30_2023", "p. 18 (« Exemples de marquages adoptés par Grenoble »)", "haute",
  liens=["MQ-Z30-001", "TQ-MQG-013"],
  notes="Confirme et source le gabarit du site retenu par MQ-Z30-001 (écart de 2 à 7 %). La cote de 60 cm portée en haut du schéma est vraisemblablement la largeur d'un chiffre (lecture du dessin, confiance moyenne).")

r("LOC-VIT-004", "vitesse", "gabarit_ellipse_50",
  "L'ellipse « 50 » des axes maintenus à 50 km/h est plus petite que l'ellipse « 30 » (marquage expérimental de 2016, arrêté du 17/01/2016). Le gabarit du site (1,90 × 1,00 m, anneau 0,10 m) est conservé ; à défaut, le gabarit E.3 de l'IISR (1,80 × 0,90 m).",
  {"site_m": {"longueur": 1.9, "largeur": 1.0, "anneau": 0.1}, "repli_iisr_m": {"longueur": 1.8, "largeur": 0.9}},
  "fabrication du glyphe VITESSE_50", "contraindre", "CEREMA_MA_2020", "p. 11", "haute", liens=["MQ-V50-001", "CF-28"])

# ------------------------------------------------------------------ Chronovélo
CH = "Grenoble-Alpes Métropole et SMMAG, charte graphique Chronovélo (non publiée), reproduite dans GAM_REX_CHRONO p. 9 et GAM_F02 p. 3"
r("LOC-CHR-001", "chronovelo", "section_courante",
  "Section courante d'une Chronovélo : piste bidirectionnelle de 4 m conseillés (3 m au minimum entre bordures), en enrobé noir lisse. Une ligne de rive jaune continue longe chaque bordure, à l'intérieur de la piste. L'axe est un motif répété « point jaune, point jaune, tiret turquoise, point jaune » ; pas de ligne axiale continue.",
  {"largeur_m": {"conseillee": 4.0, "min_entre_bordures": 3.0}, "revetement": "enrobé noir lisse", "rive": "continue jaune des deux côtés",
   "axe_motif": ["point jaune", "point jaune", "tiret turquoise", "point jaune"], "axe_dimensions_site": {"point_diametre_m": 0.2, "tiret_m": [1.0, 0.17]},
   "rive_largeur_site_m": 0.09, "couleurs": {"jaune": "jaune Chronovélo (ocre pâle si usé)", "turquoise": "bleu turquoise clair"}},
  "piste de l'itinéraire Chronovélo (LOC-CHR-008)", "generer", "GAM_F02", "p. 3, § II « Aménager sur un axe Chronovélo »", "haute",
  second=["verifier"], sec=[("GAM_REX_CHRONO", "p. 7 et p. 9"), ("GAM_CHRONO_2018", "p. 19-20")],
  liens=["MQ-CHR-001", "MQ-CYC-012", "MQ-LAR-003"],
  notes="Dimensions des points et tirets : relevé du site (MQ-CHR-001, constat vercors_s-32). Sur le Vercors, la rive jaune n'existe que d'un côté sur une partie du tracé : l'observé prime. " + CH)

r("LOC-CHR-002", "chronovelo", "interface_pietonne",
  "Interface piétonne (passage piéton qui traverse la piste) : les rives jaunes s'interrompent ; une bande turquoise couvre la largeur de la piste sur la largeur du passage, et les bandes blanches du zébra la traversent sans interruption ; en amont, dans chaque sens, trois barrettes jaunes transversales « Cyclistes, ralentissez ! » sont peintes dans la moitié de piste du sens concerné ; BEV sur les trottoirs de part et d'autre.",
  {"fond": "turquoise, largeur de piste × largeur du passage", "zebra": "bandes blanches continues sur le fond", "barrettes_n_par_sens": 3, "barrettes_couleur": "jaune",
   "barrettes_position": "amont du passage, dans la demi-piste du sens", "rives": "interrompues au droit du passage"},
  "passage piéton coupant une piste Chronovélo (branche SO : traversée vers le quai NO ; angle N ; Vercors)", "generer", "GAM_REX_CHRONO", "p. 9, « Les interfaces piétonnes »", "haute",
  sec=[("GAM_F02", "p. 3"), ("MEY_PANNEAU_CARREFOUR", "bandes bleues sous les zébras sur la piste")],
  liens=["MQ-CYC-009", "MQ-CYC-013"], conflits=["CF-LOC-02"],
  notes="Le plan 2025 du carrefour dessine ces bandes turquoise (constats hist-19, historique_projet-ajout-12). Nombre de barrettes : 3 dans la charte ; le levé GAM du site montre des paires (MQ-CHR-001) ; l'observé prime.")

r("LOC-CHR-003", "chronovelo", "interface_routiere",
  "Interface routière (traversée de chaussée par la Chronovélo) : la traversée est bordée de part et d'autre par une file de pavés jaunes transversaux ; le motif d'axe « • • — • » se poursuit entre les deux files ; les rives s'arrêtent aux files de pavés ; trois barrettes jaunes « Cyclistes, ralentissez ! » en amont de chaque sens, sur la piste. Le site ajoute des logos vélo blancs tête-bêche entre les files.",
  {"files_paves_n": 2, "pave_site_m": [0.7, 0.37], "pave_pas_site_m": 0.6, "axe_dans_traversee": True, "barrettes_n_par_sens": 3, "logos_velo": "blancs, tête-bêche (pratique du site)"},
  "traversée cyclable de l'itinéraire Chronovélo (branche SO de Verdun ; traversées de rues adjacentes du Vercors)", "generer", "GAM_REX_CHRONO", "p. 9, « Les interfaces routières »", "haute",
  sec=[("GAM_F02", "p. 3"), ("MEY_PANNEAU_CARREFOUR", "carrés orange de part et d'autre de la traversée cyclable SO")],
  liens=["MQ-CHR-001", "MQ-CYC-007"], conflits=["CF-LOC-02"],
  notes="Le motif d'axe dans la traversée est visible sur la charte mais non vérifié sur le site (aucune photo après travaux).")

r("LOC-CHR-004", "chronovelo", "separateur_bordures",
  "Profil d'une Chronovélo le long d'une chaussée : séparateur d'au moins 0,30 m entre la piste et la chaussée ; séparateur haut chanfreiné si sa hauteur dépasse 7 cm ; bordure de chaussée en vue de 0,15 m ; bordures « qui pardonnent » (chanfreinées) côté piste ; bande tampon plantée de plus de 1 m quand la place le permet ; revêtement lisse, sans ressaut ni seuil.",
  {"separateur_largeur_min_m": 0.3, "seuil_chanfrein_m": 0.07, "vue_bordure_chaussee_m": 0.15, "tampon_vegetal_min_m": 1.0, "ressauts": "aucun"},
  "génération du profil en travers d'une piste Chronovélo sans relevé", "deduire_si_absent", "GAM_REX_CHRONO", "p. 7 (coupe « Chronovélo avec séparateur haut chanfreiné si hauteur > 7 cm »)", "moyenne",
  liens=["GA-CYC-002", "GA-CYC-003", "GA-CYC-004"],
  notes="Sur le Vercors, la piste est séparée de la chaussée par une bande enherbée bordée de bordures béton claires (constat vercors_s-31) : l'observé prime.")

r("LOC-CHR-005", "chronovelo", "mobilier_eclairage",
  "Sobriété du mobilier sur une Chronovélo : aucun potelet ni chicane aux entrées et sorties de piste ni sur les traversées (strict minimum de potelets, obstacles dangereux) ; carrefours avec îlots en amande et conflits orthogonalisés ; éclairage ou balisage lumineux de la piste ; rayons de giration adaptés.",
  {"potelets_entree_piste_n": 0, "eclairage": "obligatoire (mâts existants ou balisage)", "ilots": "en amande"},
  "pose de mobilier sur ou en bord de piste Chronovélo", "contraindre", "GAM_REX_CHRONO", "p. 7", "haute",
  sec=[("GAM_F16", "p. 4, « entrées/sorties de piste cyclable sans potelet »")], liens=["POT-01", "GA-OBS-002"])

r("LOC-CHR-006", "chronovelo", "indications_directionnelles",
  "Indications directionnelles peintes sur la piste : grand numéro d'axe blanc (« 1 » pour la Chronovélo 1), flèche blanche et nom de destination, dans chaque sens, avant les bifurcations. Posées seulement si elles sont levées ou visibles sur photo : jamais déduites.",
  {"glyphes": ["numéro d'axe", "flèche", "texte de destination"], "couleur": "blanc", "inference_hors_observation": False},
  "piste Chronovélo à l'approche d'une bifurcation d'itinéraires (carrefour Verdun/Vercors)", "verifier", "GAM_REX_CHRONO", "p. 9, « Les indications directionnelles »", "moyenne",
  sec=[("GAM_F02", "p. 3, photo de l'axe Saint-Égrève - Saint-Martin-d'Hères")])

r("LOC-CHR-007", "chronovelo", "station",
  "Station Chronovélo : totem, plan, banc et pompe, avec un marquage au sol multicolore en losanges (jaune, turquoise, rouge, noir) dans une encoche de la piste. La carte de janvier 2026 figure une station sur Verdun SO en amont du carrefour, sans position précise : à vérifier sur photo avant toute pose.",
  {"composants": ["totem", "plan", "banc", "pompe"], "marquage": "losanges multicolores", "inference_hors_observation": False},
  "objet « station » levé ou photographié", "verifier", "GAM_CHRONO_2018", "p. 20-22 (« Stations Chronovélo : totem + plan + banc + pompe »)", "moyenne",
  sec=[("GAM_REX_CHRONO", "p. 9-10"), ("GAM_CARTE_CHRONO_2026", "légende « Stations Chronovélo »")])

r("LOC-CHR-008", "chronovelo", "domaine_application",
  "Domaine d'application de l'identité Chronovélo en 2026 : la Chronovélo 1 « existante » arrive de Grenoble par la piste NO de Verdun SO, traverse la branche SO et repart par la piste du Vercors (baïonnette) ; la piste de 4 m de Verdun NE est un tronçon « planifié » de la Chronovélo 1 vers Montbonnot. L'identité (LOC-CHR-001 à 003) s'applique de droit aux premiers ; sur Verdun NE, seul le marquage observé est posé.",
  {"existant": ["piste NO de Verdun SO", "traversée cyclable de la branche SO", "piste du Vercors"], "planifie": ["piste de Verdun NE vers Montbonnot"]},
  "choix des tronçons recevant l'identité Chronovélo", "contraindre", "GAM_CARTE_CHRONO_2026", "zoom Meylan et légende", "moyenne",
  sec=[("GAM_CHRONO_2018", "p. 28, itinéraire Chronovélo Meylan - La Tronche")], liens=["MQ-CHR-001"])

r("LOC-CHR-009", "chronovelo", "couleurs_traversees",
  "Couleur des traversées cyclables : vert (résine) jusqu'en 2018-2021, puis jaune Chronovélo (pavés) depuis 2021-2022 sur l'itinéraire ; le plan 2025 dessine en orange (= jaune) la nouvelle traversée SO et la bordure de la traversée de la Revirée. Sans photo de 2026, une traversée cyclable refaite en 2025 sur l'itinéraire est jaune, jamais verte ; une traversée non refaite garde sa couleur relevée.",
  {"historique": [{"periode": "avant 2018-2021", "couleur": "vert résine"}, {"periode": "2021-2025", "couleur": "jaune Chronovélo (pavés)"}, {"periode": "2025-2026", "couleur": "jaune (orange au plan)"}],
   "couleur_defaut_2026": "jaune Chronovélo"},
  "traversée cyclable en zone de travaux 2025 sans observation postérieure", "deduire_si_absent", "MEY_PANNEAU_CARREFOUR", "plan (carrés orange)", "moyenne",
  sec=[("GAM_REX_CHRONO", "p. 9")], liens=["MQ-CHR-001", "MQ-CYC-007"],
  notes="Chronologie issue des constats hist-02, hist-03 et hist-19 (orthos 2015-2022, Panoramax).")

# ------------------------------------------------------------------ traversées piétonnes
r("LOC-TRV-001", "traversees", "securisation_c1",
  "Traversée piétonne « sécurisée » au sens du projet C1 de Meylan : îlot central avec signalisation adaptée ; voie rétrécie pour inciter au ralentissement ; zébra d'au moins 2,50 m de large, perpendiculaire à l'axe de la voie et si possible aux bordures ; bandes podotactiles et bordures abaissées ; ni stationnement ni masque à la visibilité sur 5 m en amont (et si possible en aval) ; éclairage renforcé.",
  {"zebra_largeur_min_m": 2.5, "orientation": "perpendiculaire à l'axe, si possible aux bordures", "degagement_visibilite_amont_m": 5.0, "ilot_central": True, "bev": True, "eclairage": "renforcé"},
  "traversées réaménagées par le projet C1 (branche SO de Verdun, Vercors, Revirée)", "verifier", "MEY_PANNEAU_VERCORS", "encadré « C'est quoi une sécurisation de traversée piétonne ? »", "haute",
  second=["contraindre"], sec=[("MEY_PRES_2024", "diapositive 32, PDF p. 30, « Sécurisation traversées »"), ("GAM_F08", "p. 7, zone dégagée visuellement de 5 m")],
  liens=["MQ-PP-003", "MQ-PP-005", "MQ-PP-013", "GA-ILO-001", "GA-ILO-002", "MQ-STA-001"])

r("LOC-TRV-002", "traversees", "bandes_resine",
  "Traversée type du Vercors (exemple de la piscine des Buclos, hors site) : passage de 3 m, îlot central planté à nez arrondi, refuge minéral avec deux BEV, et bandes de résine colorée (orange) le long des deux côtés du zébra, de bordure à bordure, « pour marquer visuellement la traversée ». Le plan 2025 du carrefour ne dessine pas ces bandes : ne pas les poser au carrefour sans observation.",
  {"passage_m": 3.0, "bandes_resine": {"couleur": "orange", "position": "de part et d'autre du zébra, sur toute la traversée", "largeur_m_estimee": 0.5}, "inference_hors_observation": False},
  "traversées du Vercors hors carrefour ; au carrefour seulement si observé", "verifier", "MEY_PANNEAU_VERCORS", "« Exemple de la future traversée piscine des Buclos » (photomontage et plan)", "moyenne",
  notes="Largeur des bandes estimée sur le plan (environ un sixième du zébra de 3 m) : confiance faible pour la cote.")

r("LOC-TRV-003", "traversees", "marquage_et_ilot",
  "Le passage piéton marqué (bandes blanches) s'impose dans les carrefours à feux, sur les axes à 50 km/h et dans les secteurs sensibles (écoles) ; ailleurs en zone 30, il n'est pas systématique. Une traversée qui coupe deux voies de circulation reçoit un îlot central (refuge).",
  {"marquage_obligatoire": ["carrefour à feux", "axe à 50 km/h", "abords d'école ou d'EHPAD"], "ilot_si_voies_traversees_n": 2},
  "toutes les traversées du site (carrefour à feux) ; traversées de desserte en zone 30", "verifier", "GAM_F16", "p. 5, § c) et « Je prends en compte l'accessibilité »", "haute",
  sec=[("GAM_F04", "p. 7"), ("GAM_F01", "p. 3, îlot central sur les axes à 50 km/h")], liens=["MQ-PP-001", "GA-ILO-002"])

r("LOC-TRV-004", "traversees", "tete_ilot",
  "Tête d'îlot séparateur à Meylan : panneau d'obligation de contourner (flèche blanche oblique sur fond bleu, B21-1) et deux balises cylindriques grises réfléchissantes (J11) sur le nez de l'îlot, surface d'îlot minérale claire. Sur les îlots plantés du projet 2025, poser le panneau seul en pointe si le plan ou une photo l'attestent.",
  {"panneau": "B21-1", "balises_J11_n": 2, "couleur_balises": "gris métallisé à bandes réfléchissantes"},
  "nez d'îlot séparateur en chaussée", "verifier", "MEY_PRES_2024", "diapositive 32, PDF p. 30 (photo « Exemple d'aménagement sécurisé »)", "moyenne",
  sec=[("GAM_CHRONO_2018", "p. 26 (îlot avec panneau à flèche, Meylan 2018)")], liens=["SIG-01", "GA-ILO-005"])

# ------------------------------------------------------------------ transports en commun
r("LOC-TC-001", "transport_commun", "quai_accessible",
  "Règles d'or d'un arrêt de bus accessible du réseau grenoblois : hauteur de quai de 18 à 21 cm selon le matériel (bus ou car), pour sortir la palette sans agenouillement ; revêtement de couleur contrastée distinguant la zone d'attente de la zone de sécurité ; dalle de repérage au droit de la porte centrale ; bande d'interception et dalles podotactiles au droit de la porte avant ; mobilier confortable avec une zone de manœuvre d'au moins 1,50 m. Les quais de La Revirée sont aussi desservis par des lignes périurbaines (80, 82, 164), probablement en cars : 0,18 m par défaut, la mesure prime.",
  {"hauteur_quai_m": {"bus": 0.21, "cars": 0.18}, "hauteur_defaut_la_reviree_m": 0.18, "zone_attente": "revêtement contrasté", "dalle_porte_centrale": True,
   "bande_interception_porte_avant": True, "zone_manoeuvre_min_m": 1.5},
  "quais La Revirée (SE et NO) et tout quai bus créé en 2025", "generer", "GAM_F03", "p. 3, « Je prends en compte l'accessibilité »", "haute",
  second=["verifier"], liens=["GA-QBU-001", "GA-QBU-005", "GA-QBU-006", "TC-01", "TC-02"],
  notes="Concorde avec GA-QBU-001 (Cerema). Vues mesurées du site : p50 0,20 m (QUAI_BUS).")

r("LOC-TC-002", "transport_commun", "traversee_arret",
  "Implantation d'un arrêt : passage piéton en amont de l'arrêt (au moins 4 m), à l'arrière du bus, pour la covisibilité ; arrêts sur chaussée (en ligne), en vis-à-vis avec îlot central ou décalés avec passage central pour empêcher le dépassement du bus.",
  {"distance_passage_amont_min_m": 4.0, "type_arret": "en ligne sur chaussée"},
  "quais de La Revirée", "verifier", "GAM_F03", "p. 3, « Arrêts »", "moyenne", liens=["GA-QBU-004", "GA-QBU-007"],
  notes="Quai NO : en aval de la traversée SO (conforme) ; quai SE : 45 à 75 m en amont de la traversée (constat ctx-08), sans passage propre.")

r("LOC-TC-003", "transport_commun", "gabarits_bus",
  "Gabarits pour les bus : voie bus d'au moins 3,05 m ; chaussée bidirectionnelle d'au moins 6,40 m pour le croisement de deux bus sur un axe à 50 km/h (6,20 à 6,40 m hors caniveau sur un axe à 30, y compris en courbe ; 5,50 à 6,20 m : croisement à très basse vitesse en ligne droite seulement).",
  {"voie_bus_min_m": 3.05, "croisement_bus_m": {"axe_50": 6.4, "axe_30": [6.2, 6.4], "lent_ligne_droite": [5.5, 6.2]}},
  "contrôle des largeurs de chaussée parcourues par les lignes C1, 42, 80, 82, 162, 164", "verifier", "GAM_F03", "p. 4, « Concilier les enjeux TC et la vie locale »", "haute",
  liens=["MQ-LAR-002", "GA-CHA-005", "GA-RAY-002"])

r("LOC-TC-004", "transport_commun", "equipement_arret",
  "Équipement d'un arrêt de ligne Chrono (C1) après travaux : abri, banc, corbeille, poteau d'arrêt, afficheur d'attente en temps réel, éclairage, bandes podotactiles ; à proximité : distributeur de titres M réso, plan de quartier, arceaux vélos. Un arrêt de ligne Flexo (42, chemin de la Revirée) n'a qu'un poteau avec horaires, sans abri ni banc.",
  {"chrono": ["abri", "banc", "corbeille", "poteau", "afficheur temps réel", "éclairage", "BEV"], "abords_chrono": ["distributeur de titres", "plan", "arceaux vélos"],
   "flexo": ["poteau avec horaires"]},
  "quai sans relevé d'équipement 2026", "deduire_si_absent", "OSM_2026", "way/185326915 (2026-04-01), way/185326913 (2025-09-21), way/1445374292 (2026-04-13)", "moyenne",
  sec=[("GAM_F03", "p. 5, « Qualité de l'attente à l'arrêt »")], liens=["TC-01", "TC-02", "MOB-01"])

# ------------------------------------------------------------------ vélos
r("LOC-VEL-001", "velo", "arceaux",
  "Arceaux vélos de la Métropole : modèle tube acier gris RAL 7024 ; au moins 4 arceaux par emplacement (3 si peu fréquenté ou contraint) ; 1 m entre arceaux ; 0,50 m de dégagement à la bordure ; de préférence sur la chaussée, sur une place de stationnement longitudinal juste en amont d'un passage piéton, protégés par un potelet à mémoire de forme. Les arceaux relevés sur trottoir ou sur quai (La Revirée) gardent leur position.",
  {"modele": "arceau tube acier", "couleur_ral": "7024", "arceaux_par_emplacement_min_n": 4, "arceaux_min_contraint_n": 3, "entraxe_m": 1.0, "degagement_bordure_m": 0.5,
   "position_preferee": "chaussée, place longitudinale, amont du passage piéton", "protection": "potelet à mémoire de forme"},
  "stationnement vélos déduit ou sans position fine", "generer", "GAM_F02", "p. 6-7, § IV « Proposer des solutions de stationnement »", "haute",
  second=["contraindre"], liens=["MOB-01", "PMR-01"])

r("LOC-VEL-002", "velo", "separation_et_carrefours",
  "Aménagements cyclables hors Chronovélo : à 30 km/h, mixité sur chaussée ; à 50 km/h, séparation (bande d'au moins 1,50 m, 2 m recommandés, ou piste) ; aux carrefours à feux, sas vélos et cédez-le-passage cycliste au feu (panonceau M12) sur les mouvements peu conflictuels ; jamais de vélos sur les espaces piétons.",
  {"bande_min_m": 1.5, "bande_recommandee_m": 2.0, "sas_velo": "préconisé", "m12": "mouvements peu conflictuels"},
  "contrôle des aménagements cyclables observés ; pose de M12 seulement si observé", "verifier", "GAM_F02", "p. 4-6", "haute",
  sec=[("GAM_F16", "p. 3"), ("GAM_PANNEAUX_VELO", "affiche (M12 tout droit / tourne-à-droite)")],
  liens=["MQ-LAR-003", "MQ-CYC-005", "MQ-TRV-004"],
  notes="OSM (2022) porte un cédez-le-passage cycliste au feu de la Revirée (red_turn:right:bicycle=yes), à revérifier après travaux.")

r("LOC-FEU-001", "feux", "repetiteurs",
  "Pratique métropolitaine : intégrer des sas vélos et supprimer les répétiteurs bas des feux tricolores. Les répétiteurs observés restent ; sur un support de feux créé en 2025 sans observation (branche SO), ne pas poser de répétiteur bas par défaut.",
  {"repetiteur_bas_defaut_support_neuf": False},
  "supports de feux déduits du plan 2025 (feu_SW_*)", "deduire_si_absent", "GAM_F02", "p. 6, § 2 « La gestion des carrefours »", "faible",
  liens=["FEU-01", "FEU-03"], notes="Recommandation générale, non vérifiée sur les feux neufs du site.")

r("LOC-FEU-002", "feux", "boutons_appel",
  "Les traversées à feux du carrefour n'ont ni bouton d'appel ni répéteur sonore ou vibrant (OSM : button_operated=no, traffic_signals:sound=no, vérifiés en 2023 puis en février-mars 2026 sur le Vercors). Ne pas poser de boîtier de bouton d'appel ni de module sonore sur les supports de feux piétons, sauf observation contraire.",
  {"bouton_appel": False, "signal_sonore": False, "vibreur": False},
  "supports de feux piétons du site", "contraindre", "OSM_2026", "node/1959022964 (2026-02-27), node/1959022961 (2026-03-07), nodes 1959022973/76 (2023-08-26), 6569623985/86 (2023-10-22)", "moyenne",
  liens=["FEU-01"])

# ------------------------------------------------------------------ mobilier
r("LOC-MOB-001", "mobilier", "potelets_bornes",
  "Gamme métropolitaine de mobilier de contention, posée en dernier recours et jamais à titre préventif : potelet acier monobloc Ø 88,9 mm, RAL 7024, hauteur 1,20 m ou 1,40 m, avec bande de peinture blanche non réfléchissante en tête ; borne bois de mélèze de section carrée 150 × 150 mm, chanfreinée, hauteur 1,30 m ; potelet à mémoire de forme Ø 90 mm, RAL 7024, hauteur hors sol 0,90 m.",
  {"potelet_acier": {"diametre_mm": 88.9, "couleur_ral": "7024", "hauteur_m": [1.2, 1.4], "bande_tete": "blanche, non réfléchissante"},
   "borne_bois": {"section_mm": [150, 150], "essence": "mélèze", "hauteur_m": 1.3, "chanfrein": True},
   "potelet_memoire_forme": {"diametre_mm": 90, "couleur_ral": "7024", "hauteur_m": 0.9},
   "pose_preventive": False},
  "fabrication et pose des potelets et bornes (assets)", "generer", "GAM_F16", "p. 4, « Harmoniser : tendre vers une gamme métropolitaine »", "haute",
  second=["contraindre"], liens=["POT-01", "POT-02", "GA-OBS-002"],
  notes="La bande blanche en tête satisfait le contraste de GA-OBS-002 ; Ø 88,9 mm à 1,20 m respecte l'abaque (≥ 0,06 m).")

r("LOC-MOB-002", "mobilier", "barrieres",
  "Barrière métropolitaine : croix de Saint-André, RAL 7024, hauteur 1,20 m, longueurs de 0,80, 1,20 ou 1,50 m ; à n'employer qu'en dernier recours.",
  {"motif": "croix de Saint-André", "couleur_ral": "7024", "hauteur_m": 1.2, "longueurs_m": [0.8, 1.2, 1.5]},
  "barrière déduite ou sans modèle relevé", "generer", "GAM_F16", "p. 4, « Les barrières métropolitaines »", "haute",
  liens=["BAR-01", "GA-OBS-003"], conflits=["CF-LOC-03"])

r("LOC-MOB-003", "mobilier", "couleur",
  "Couleur par défaut du mobilier métallique métropolitain non relevé (potelets, arceaux, barrières) : gris graphite RAL 7024, finition mate. Le mobilier relevé garde sa couleur (supports de feux, candélabres, abris de l'exploitant).",
  {"couleur_ral": "7024", "nom": "gris graphite", "rgb_approx": [71, 74, 80]},
  "matériau des assets de mobilier sans observation de couleur", "deduire_si_absent", "GAM_F16", "p. 4", "moyenne",
  sec=[("GAM_F02", "p. 7 (arceau RAL 7024)")],
  notes="Valeur RVB approchée de la teinte RAL 7024 (référence couleur courante, non tirée des documents).")

r("LOC-MOB-004", "mobilier", "zone_fonctionnelle",
  "Rangement du mobilier : une bande « fonctionnelle » le long de la chaussée regroupe mobilier, signalisation, stationnements vélos et arbres ; le cheminement piéton reste libre, continu et prioritaire, 2 m visés (1,50 m au moins laissés libres par toute occupation autorisée, 1,40 m au minimum réglementaire) ; obstacles au-dessus de 2,20 m ou signalés au sol ; aucun masque à la visibilité sur 5 m en amont d'un passage piéton.",
  {"cheminement_vise_m": 2.0, "cheminement_libre_occupation_min_m": 1.5, "cheminement_reglementaire_min_m": 1.4, "hauteur_libre_min_m": 2.2, "degagement_amont_passage_m": 5.0},
  "placement et recalage du mobilier sur trottoir", "contraindre", "GAM_F08", "p. 1, 6 et 7, « Organiser : zone fonctionnelle »", "haute",
  sec=[("GAM_RGV", "chap. mobilier urbain, « Cheminement piéton » (1,50 m libres)"), ("GAM_F16", "p. 3 (obstacles > 2,2 m)")],
  liens=["PMR-01", "MOB-01", "GA-TRO-001", "GA-CHA-006", "MQ-PP-013"], conflits=["CF-LOC-04"])

r("LOC-MOB-005", "mobilier", "sobriete",
  "Sobriété de l'aménagement métropolitain : limiter le nombre de matériaux, de couleurs et de styles de mobilier ; supprimer le marquage non obligatoire en zone 30 (ligne axiale, passages hors carrefour à feux) ; pas de potelets ni de croix de Saint-André pour les accès privés. Dans le PCG, ne jamais compléter la scène par du mobilier « de remplissage » non observé.",
  {"marquage_non_obligatoire_zone_30": "absent", "mobilier_de_remplissage": False},
  "génération procédurale du mobilier et des marquages en zone 30", "contraindre", "GAM_F16", "p. 4-5", "haute",
  sec=[("GAM_F19", "p. 3-4, « Éviter la confusion »"), ("GAM_F04", "p. 4")], liens=["GA-CHR-004"])

r("LOC-ECL-001", "eclairage", "teinte_lanternes",
  "Teinte des lanternes pour le rendu de nuit : lanternes au sodium haute pression (OSM lamp_type=high_pressure_sodium : Revirée, Verdun NE) en lumière orangée (environ 2 000 K) ; lanternes LED (lamp_type=led : Vercors S) en blanc chaud (environ 3 000 K, a priori).",
  {"shp_k": 2000, "led_k_a_priori": 3000},
  "rendu nocturne des candélabres (mobilier.lamp_type)", "generer", "OSM_2026", "nodes 12894130974, 12894141026, 9530354220, 9530354517 (SHP) ; 9514828418, 9514828517, 9514828717, 12887274329 (LED)", "faible",
  notes="Températures de couleur : valeurs typiques des technologies, non sourcées localement.")

# ------------------------------------------------------------------ matériaux
r("LOC-MAT-001", "materiaux", "revetements",
  "Revêtements des espaces publics métropolitains : chaussée et piste en enrobé ; trottoirs en enrobé (observé sur Verdun SO après travaux) ou en béton clair ; cheminements le long des espaces plantés en béton clair ou en stabilisé compacté (observés en 2026 le long des Saules Blancs et sur la rive E du Vercors) ; préférence pour des sols clairs à fort albédo ; béton désactivé possible (avec environ 10 % de gros granulats noirs) ; stabilisé jamais sur le cheminement principal ni sur les quais ; stationnement perméable possible (pavés à joints enherbés, evergreen). Limiter le nombre de matériaux.",
  {"chaussee": "enrobé", "piste": "enrobé noir lisse", "trottoir_defaut_2025": "enrobé", "cheminement_bord_espace_vert": ["béton clair", "stabilisé compacté"],
   "beton_desactive_granulats_noirs_pct": 10, "stabilise_interdit": ["cheminement principal", "quai bus", "abaissés"]},
  "surfaces créées en 2025 sans observation de matériau", "deduire_si_absent", "GAM_F19", "p. 3, 4 et 7", "moyenne",
  sec=[("GAM_F16", "p. 6, revêtements clairs à fort albédo"), ("GAM_F11", "p. 5, pavés à la place des caniveaux, parkings perméables"),
       ("OSM_2026", "way/1412130596 (béton), way/1488785305 (stabilisé), ways Verdun SO (enrobé neuf)")],
  liens=["materiaux_sol.json", "TQ-SOL-*", "GA-TRO-007"])

r("LOC-MAT-002", "materiaux", "couleurs_sol_reglementees",
  "Palette des couleurs de sol à usage codifié dans le site : jaune Chronovélo (rives, pavés, barrettes, points) ; turquoise (tirets d'axe Chronovélo, fond des interfaces piétonnes sur piste) ; blanc (marquage réglementaire) ; jaune réglementaire des zigzags d'arrêt. Pas de résine verte en zone de travaux 2025 ; résine orange des traversées du Vercors seulement si observée.",
  {"jaune_chronovelo": True, "turquoise": True, "vert_resine_2026": False, "orange_resine": "si observé"},
  "matériaux de marquage", "contraindre", "GAM_REX_CHRONO", "p. 9", "moyenne",
  sec=[("MEY_PANNEAU_VERCORS", "bandes de résine")], liens=["peinture.json", "MQ-CHR-001", "MQ-BUS-005"])

# ------------------------------------------------------------------ végétation
r("LOC-VEG-001", "vegetation", "entraxe_alignement",
  "Entraxe des arbres d'alignement de la Métropole selon le développement : grand (plus de 25 m) 10 à 12 m ; moyen (15 à 25 m) 7 à 8 m ; petit (moins de 15 m) 7 m ; en zone de stationnement 7 m au moins quel que soit l'arbre. Règle de contrôle équivalente : entraxe au moins égal au rayon du houppier adulte plus 1 m. Un alignement de 8 à 15 m d'entraxe est le cas général.",
  {"entraxe_m": {"grand": [10, 12], "moyen": [7, 8], "petit": 7, "stationnement_min": 7}, "regle_houppier": "rayon adulte + 1 m", "plage_generale_m": [8, 15]},
  "arbres déduits ou issus du plan 2025", "contraindre", "GAM_CHARTE_ARBRE", "p. imprimées 38-43, PDF p. 20-22 (schéma de synthèse ; « Distances en alignement »)", "haute",
  liens=["VEG-03"], conflits=["CF-LOC-05"])

r("LOC-VEG-002", "vegetation", "distances",
  "Distances de plantation de la Métropole : axe de l'arbre à 1,50 m au moins du bord d'une chaussée, d'une piste cyclable ou d'un cheminement, avec un dégagement de 1,50 m de large sur 2,50 m de haut pour piétons et cyclistes (essences à couronne facile à remonter) ; 2 m au moins entre l'axe de l'arbre et une façade ; près d'une émergence (façade, candélabre), rayon du houppier adulte plus 2 m, et au moins 2 m entre l'extrémité du houppier adulte et l'axe d'un candélabre ; 2 m entre l'arbre et les réseaux (aériens et souterrains). Les arbres ne masquent pas la visibilité aux passages piétons.",
  {"axe_arbre_bord_voie_min_m": 1.5, "degagement_circulation_m": {"largeur": 1.5, "hauteur": 2.5}, "axe_facade_min_m": 2.0, "emergence": "rayon houppier adulte + 2 m",
   "houppier_candelabre_min_m": 2.0, "reseaux_min_m": 2.0},
  "arbres déduits ou issus du plan 2025 ; contrôle des arbres observés", "contraindre", "GAM_CHARTE_ARBRE", "p. imprimées 38-39 et 46-47, PDF p. 20 et 24 (« Distances aux voies de circulation », « Distances aux réseaux aériens »)", "haute",
  second=["verifier"], liens=["VEG-02", "VEG-03", "ECL-01", "MQ-PP-013"], conflits=["CF-LOC-05"])

r("LOC-VEG-003", "vegetation", "plantation_type",
  "Plantation type d'un arbre métropolitain : fosse de 15 m³ (12 à 18 m³) en mélange terre-pierre et terre végétale ; arbre d'environ 3 m à la plantation ; tuteurage tripode ou quadripode d'environ 2 m hors sol (1,20 m dans le sol) ; cuvette d'arrosage en andains autour du collet (environ 20 cm de haut sur 80 cm) ; pied d'arbre végétalisé (vivaces, graminées, arbustes) ou revêtement perméable ; protection du tronc. Pour les arbres plantés à la fin de 2025 : en octobre 2026, tige de 3 à 4 m, couronne réduite, tuteurs en bois clair encore en place.",
  {"fosse_m3": {"defaut": 15, "plage": [12, 18]}, "hauteur_plantation_m": 3.0, "tuteurage": {"type": ["tripode", "quadripode"], "hauteur_hors_sol_m": 2.0, "ancrage_m": 1.2},
   "cuvette_m": {"hauteur": 0.2, "largeur": 0.8}, "pied": "végétalisé ou perméable", "etat_octobre_2026": {"hauteur_m": [3, 4], "tuteurs": True}},
  "arbres « plantés 2025 » (plan 2025 : TPC SO, bande NO, angle NO, noue SE)", "generer", "GAM_CHARTE_ARBRE", "p. imprimées 38-39, PDF p. 20 (schéma « Le bon arbre au bon endroit »)", "haute",
  sec=[("GAM_F18", "p. 16 (la Métropole plante, finance grilles et protections ; la commune gère les massifs fleuris)"), ("MEY_MMV165", "p. 12 (plantations à l'automne)")],
  liens=["GA-ARB-001", "GA-ARB-002", "GA-ARB-003", "vegetation.json"])

r("LOC-VEG-004", "vegetation", "terre_plein_central",
  "Un terre-plein central planté d'arbres mesure 2 à 6 m de large. Le TPC de Verdun SO (environ 2,4 m entre bordures) est en bas de plage : arbres à petit ou moyen développement, à couronne remontée au-dessus du gabarit des bus (hauteur libre de 3,80 m sur chaussée), pied engazonné ou planté.",
  {"largeur_tpc_m": [2.0, 6.0], "tpc_site_m": 2.4, "hauteur_libre_chaussee_m": 3.8},
  "TPC planté de Verdun SO", "contraindre", "GAM_CHARTE_ARBRE", "p. imprimées 42-43, PDF p. 22 (« Pour un terre-plein central : prévoir 2 à 6 m de large »)", "haute",
  sec=[("GAM_F03", "p. 4 (hauteur des bus et taille des arbres)")], liens=["GA-CHA-006", "VEG-02"])

r("LOC-VEG-005", "vegetation", "palette_meylan",
  "Palette végétale de Meylan (OAP Paysage et biodiversité, ambiance « Ville parc » de la plaine) : essences locales et diversifiées, résistantes à la chaleur, caduques en majorité. Petits arbres conseillés en ville parc (extrait) : tilleul à petites feuilles, érable champêtre, érable de Montpellier, cormier, cerisier à grappes, saule blanc, aulne blanc, faux ébénier, lilas. Haies : jamais monospécifiques ni majoritairement persistantes (thuya, laurier palme, cyprès de Leyland interdits). Espèces invasives proscrites : robinier faux-acacia, ailante, érable négondo, mimosa, buddleia, bambou traçant, herbe de la pampa.",
  {"ambiance_site": "Ville parc (plaine urbaine de Meylan, probable)", "arbres_petits_ville_parc": ["Tilia cordata", "Acer campestre", "Acer monspessulanum", "Sorbus domestica", "Prunus padus", "Salix alba", "Alnus incana", "Laburnum anagyroides", "Syringa vulgaris"],
   "haie_min_essences_n": 3, "haie_part_persistantes_max_pct": 50,
   "interdits": ["Thuja", "Prunus laurocerasus", "Cupressocyparis leylandii", "Robinia pseudoacacia", "Ailanthus altissima", "Acer negundo", "Acacia dealbata", "Buddleja davidii", "Phyllostachys", "Cortaderia selloana"]},
  "choix des essences pour les plantations déduites et pour les haies dispersées par le PCG", "contraindre", "MEY_LIVRET_HAIES", "p. 8-14 (règles du PLUi, tableaux d'essences)", "moyenne",
  sec=[("GAM_F10", "p. 6 (haies vives d'espèces locales, pas de murs végétaux monospécifiques)"), ("GAM_CHARTE_ARBRE", "« Quelles essences peu adaptées », p. 58")],
  liens=["vegetation.json"],
  notes="Les codes d'essences du plan 2025 (Alc, As, Ce, Gt, Aca, Ac, Ca, Ul, Oc) restent à décoder ; « Ac » = Acer campestre est compatible avec la palette. La part maximale de persistants est une lecture de « majoritairement persistantes » (seuil 50 %).")

r("LOC-VEG-006", "vegetation", "pleine_terre_noues",
  "Gestion de l'eau et pleine terre : chaque projet métropolitain réserve au moins 10 % de surfaces perméables en pleine terre (cap de 25 % à l'horizon 2030) ; les noues sont dimensionnées pour infiltrer la pluie courante en moins de 24 h (pas d'eau stagnante). Dans la scène d'octobre, la noue SE et les espaces plantés en creux sont secs hors épisode pluvieux, sans miroir d'eau.",
  {"pleine_terre_min_pct": 10, "pleine_terre_cap_2030_pct": 25, "infiltration_max_h": 24, "eau_stagnante_rendu": False},
  "espaces plantés « gestion alternative des eaux pluviales » du projet 2025", "contraindre", "GAM_F11", "p. 1 et 4", "haute",
  sec=[("GAM_GUIDE", "p. 20, objectifs chiffrés"), ("MEY_PANNEAU_CARREFOUR", "« gestion alternative des eaux pluviales »")], liens=["GA-ASS-005"])

r("LOC-VEG-007", "vegetation", "peupliers_verdun_ne",
  "Les grands arbres d'alignement de Verdun NE (rive SE, environ 36 à 156 m du centre) sont des peupliers noirs (Populus nigra, port fastigié probable, 20 à 29 m d'après le LiDAR 2021) selon l'inventaire de la Métropole (2023) : essence à porter par les arbres de la description appariés à moins de 5 m ; au-delà, confiance faible.",
  {"essence": "Populus nigra", "port": "fastigié (peuplier d'Italie) probable", "hauteur_m": [20, 29], "appariement_max_m": 5.0},
  "arbres de la description sans essence dans cette rangée", "deduire_si_absent", "DATAGOUV_ARBRES", "ids MEY00085 à MEY00100", "moyenne",
  liens=["obs_web DOC-LOCALE-018 à 033"])

# ------------------------------------------------------------------ clôtures et soutènements (riverains)
r("LOC-CLO-001", "clotures", "regles_plui_meylan",
  "Clôtures riveraines à Meylan (PLUi) : en limite du domaine public, hauteur totale de 1,80 m au plus ; muret de 1,00 m au plus, surmonté d'un dispositif à claire-voie ; portails et portillons de 1,80 m au plus, en harmonie avec la clôture ; en limite séparative, 2 m au plus et clôture perméable à la base (passage de la petite faune). Interdits : murs pleins de plus de 1 m (sauf prolongement d'un mur existant), palissades et brise-vues opaques, matériaux hétéroclites, haies d'une seule espèce ou majoritairement persistantes. Les murs et murets anciens sont préservés.",
  {"hauteur_max_limite_publique_m": 1.8, "muret_max_m": 1.0, "portail_max_m": 1.8, "hauteur_max_limite_separative_m": 2.0, "permeable_base": True,
   "interdits": ["mur plein > 1 m", "palissade opaque", "brise-vue", "matériaux hétéroclites", "haie monospécifique", "haie majoritairement persistante"]},
  "clôtures et haies riveraines déduites ou dispersées (PCG)", "contraindre", "MEY_LIVRET_HAIES", "p. 9-10 (« Règles générales », « Concernant la clôture »)", "haute",
  second=["verifier"], sec=[("MEY_CHARTE_URBA", "p. 4 et 9 (préserver murs, murets et clôtures ; limiter les clôtures)")],
  liens=["BAR-*", "vegetation.json"],
  notes="S'applique aux clôtures privées de 2026 ; une clôture relevée antérieure au PLUi (2019) garde sa forme.")

r("LOC-CLO-002", "clotures", "soutenements",
  "Murs de soutènement riverains : maçonnerie enduite, petit appareil de pierres sèches ou béton structuré à motifs ; enrochements interdits ; gabions seulement en soutènement et remplis de pierres appareillées (pas de galets en vrac) ; pas de parpaings ni de briques creuses laissés bruts ; clôture sur soutènement de 1,50 m au plus côté domaine public.",
  {"autorises": ["maçonnerie enduite", "pierres sèches", "béton structuré"], "interdits": ["enrochement", "galets en vrac", "parpaing brut"], "cloture_sur_soutenement_max_m": 1.5},
  "murs riverains déduits", "contraindre", "MEY_LIVRET_HAIES", "p. 10", "haute")

# ------------------------------------------------------------------ accessibilité
r("LOC-ACC-001", "accessibilite", "reperes_et_guidage",
  "Repères pour les déficients visuels : un espace partagé piétons/vélos est contrasté et séparé par un ressaut ou une bordure de 0,5 à 2 cm ; la bande de guidage podotactile n'est pas préconisée (seulement en rattrapage d'un aménagement qui n'a pas intégré de repérage) : ne pas en générer sans observation ; tout guidage visuel est doublé d'un relief (bordure, ressaut).",
  {"ressaut_espace_partage_m": [0.005, 0.02], "bande_guidage": "seulement si observée"},
  "génération des repères tactiles hors BEV", "contraindre", "GAM_F02", "p. 3, « Je prends en compte l'accessibilité »", "haute",
  sec=[("GAM_F01", "p. 3"), ("GAM_F12", "« Je veille à traduire par un guidage physique tout guidage visuel »")],
  liens=["GA-CYC-003", "PMR-02"],
  notes="Ne concerne pas la séparation piste/trottoir à niveaux différents (GA-CYC-003).")

# ------------------------------------------------------------------ conflits et métadonnées
conflits = [
    {"id": "CF-LOC-01", "sujet": "Ellipses « 30 » sur chaussée refaite", "valeurs": "MQ-Z30-001 : marquage facultatif, jamais déduit ; pratique métropolitaine : rappel à chaque intersection avec une rue à 30 (LOC-VIT-002)",
     "decision": "repose à l'identique seulement d'une ellipse relevée en 2022 sur une chaussée refaite en 2025 ; aucune création ailleurs", "regles": ["LOC-VIT-002", "MQ-Z30-001"]},
    {"id": "CF-LOC-02", "sujet": "Barrettes Chronovélo", "valeurs": "charte : 3 barrettes par sens ; levé GAM du site : paires au pas de 0,80 m (MQ-CHR-001)",
     "decision": "l'observé prime ; 3 barrettes seulement pour une interface Chronovélo déduite sans relevé", "regles": ["LOC-CHR-002", "LOC-CHR-003", "MQ-CHR-001"]},
    {"id": "CF-LOC-03", "sujet": "Hauteur des barrières", "valeurs": "BAR-01 : 1,00 m ; gamme métropolitaine : 1,20 m (LOC-MOB-002)",
     "decision": "1,20 m pour une barrière métropolitaine sans relevé ; hauteur relevée sinon", "regles": ["LOC-MOB-002", "BAR-01"], "spec_a_modifier": "regles_implantation.json : BAR-01.parametres.hauteur_m (signalé, non modifié)"},
    {"id": "CF-LOC-04", "sujet": "Largeur du cheminement piéton", "valeurs": "PMR-01 / GA-TRO-001 : 1,40 m minimum légal ; guide métropolitain : 2 m visés ; règlement de voirie : 1,50 m libres pour une occupation",
     "decision": "1,40 m reste le seuil de violation ; 2 m est la cible pour placer un objet déduit ; 1,50 m pour les objets autorisés (terrasses, mobilier commercial)", "regles": ["LOC-MOB-004", "PMR-01", "GA-TRO-001"]},
    {"id": "CF-LOC-05", "sujet": "Distances des arbres", "valeurs": "VEG-02 : recul du tronc 0,75 / 1,00 / 1,50 m ; VEG-03 : entraxe 5 / 8 / 10 m ; charte de l'arbre : axe à 1,50 m du bord de voie, entraxe 7 / 7-8 / 10-12 m",
     "decision": "pour un arbre déduit ou issu du plan 2025 (projet métropolitain), appliquer la charte (plus contraignante) ; un arbre observé n'est jamais déplacé pour ces seules règles", "regles": ["LOC-VEG-001", "LOC-VEG-002", "VEG-02", "VEG-03"], "spec_a_modifier": "regles_implantation.json : VEG-02, VEG-03 (signalé, non modifié)"},
]

documents_non_trouves = [
    "Charte graphique Chronovélo officielle (cotes des pavés, barrettes, points, teintes RAL) : non publiée ; reconstituée depuis GAM_REX_CHRONO p. 9 et GAM_F02 p. 3, cotes du site (MQ-CHR-001).",
    "Guide de conception cyclable et catalogue des aménagements cyclables de la Métropole (cités dans la bibliographie de la fiche 2) : introuvables en ligne.",
    "Volume « dispositions techniques » du règlement de voirie métropolitain et cahier des prescriptions générales assainissement : non trouvés.",
    "Référentiel des espaces publics de la Ville de Grenoble (2014), cité par la charte de l'arbre : non trouvé.",
    "SMMAG : aucun schéma directeur d'accessibilité (SDA-Ad'AP) ni guide des quais publié ; règles de quai tirées de la fiche 3 du guide métropolitain.",
    "DCE du marché 2024-TX-ACP-0331 (CCTP : matériaux, bordures, mobilier « spécifique », essences) : consultation close, accès par formulaire sur marches-publics.info ; non consulté.",
    "Département de l'Isère : sans objet (routes départementales transférées à la Métropole le 1er janvier 2017).",
    "Photos du carrefour après travaux (sept. 2025 - oct. 2026) : aucune trouvée (meylan.fr, grenoblealpesmetropole.fr, Place Gre'net, Le Dauphiné Libéré non accessible, Panoramax : seules les photos IGN du 2026-07-28 à 129-212 m au sud) ; OSM cite une photo Mapillary 4411579125519625 du quai NO (API à jeton, non consultée).",
    "OAP Paysage et biodiversité (carnet « Vallée de l'Isère amont ») et règlement écrit du PLUi : non téléchargés (extraits repris par le livret de Meylan).",
]

out = {
    "version": "1.0", "date": "2026-10-10", "schema": "regles_locales/1.0 (champs de regles_conception/1.0)",
    "agent": "DOC-LOCALE",
    "perimetre": {
        "site": "Carrefour « Paquet Jardin », Meylan (38) : avenue de Verdun RD 1090, avenue du Vercors, chemin de la Revirée ; état d'octobre 2026 après les travaux C1+ de 2025",
        "objet": "Règles et pratiques LOCALES (Grenoble-Alpes Métropole, SMMAG, Ville de Meylan, Métropole apaisée, charte Chronovélo) qui complètent ou précisent les règles nationales de regles_conception.json et regles_implantation.json.",
        "preseance": "observation 2026 > règle locale sourcée > règle nationale (regles_conception) > pratique d'une autre collectivité > a priori. Une règle locale ne déplace jamais un objet observé ; elle fixe les valeurs par défaut des objets déduits, les gabarits des assets et les contrôles.",
        "liens": "« liens » renvoie aux identifiants de regles_conception.json (MQ-, GA-, TQ-...) et regles_implantation.json (GEN-, PMR-, SIG-, FEU-, ECL-, POT-, TC-, MOB-, BAR-, VEG-, RES-)."
    },
    "conventions": {"unites": "suffixes de regles_conception.json (m, mm, pct, kmh, m2, m3, n, k = kelvin)", "actions": ["generer", "contraindre", "verifier", "deduire_si_absent"],
                     "references_spec": "« regle:<fichier>.<chemin> » comme dans regles_conception.json", "repere": "local = L93 - O(917279.43, 6460289.98) ; z = NGF - 216.30"},
    "familles": [],
    "regles": regles,
    "conflits": conflits,
    "sources": list(S.values()),
    "observations_web": {"fichier": WEB + "obs_web.json", "construction": WEB + "construire_obs_web.py", "preuves": WEB + "preuves/"},
    "documents_non_trouves": documents_non_trouves,
}
PV = WEB + "preuves/"
PREUVES = {"LOC-VIT-002": ["cerema_ma_2020_p11_ellipses.png"], "LOC-VIT-003": ["cerema_zone30_ellipse_grenoble_p18.png"], "LOC-VIT-004": ["cerema_ma_2020_p11_ellipses.png"],
           "LOC-VIT-001": ["gam_fiche4_p7_code_rue.png"],
           "LOC-CHR-001": ["cerema_rex_chronovelo_identite_p9.png", "gam_fiche2_p3_chronovelo.png"], "LOC-CHR-002": ["cerema_rex_chronovelo_identite_p9.png"],
           "LOC-CHR-003": ["cerema_rex_chronovelo_identite_p9.png", "panneau_carrefour_zoom_centre.png"], "LOC-CHR-004": ["cerema_rex_chronovelo_profil_p7.png"],
           "LOC-CHR-006": ["cerema_rex_chronovelo_identite_p9.png", "gam_fiche2_p3_chronovelo.png"], "LOC-CHR-008": ["carte_chronovelo_2026_meylan.png", "carte_chronovelo_2026_legende.png"],
           "LOC-CHR-009": ["panneau_carrefour_zoom_centre.png", "chronovelo2018_p26_photo_b.jpg"],
           "LOC-TRV-001": ["panneau_vercors_securisation_traversee.jpg"], "LOC-TRV-002": ["panneau_vercors_exemple_traversee.jpg"], "LOC-TRV-004": ["presentation_2024-05-14_p30_exemple_ilot.png"],
           "LOC-TC-001": ["gam_fiche3_p3_quais.png"], "LOC-TC-002": ["gam_fiche3_p3_quais.png"], "LOC-VEL-001": ["gam_fiche2_p6_arceaux.png"],
           "LOC-MOB-001": ["gam_fiche16_p4_potelets.png"], "LOC-MOB-002": ["gam_fiche16_p4_potelets.png"],
           "LOC-VEG-001": ["charte_arbre_p22_distances.png"], "LOC-VEG-002": ["charte_arbre_p20_schema.png", "charte_arbre_p24_voies.png"], "LOC-VEG-003": ["charte_arbre_p20_schema.png"],
           "LOC-VEG-004": ["charte_arbre_p22_distances.png"], "LOC-VEG-005": ["livret_haies_p8_ambiances.png"], "LOC-CTX-002": ["mmv166_p7_travaux.png", "mmv165_p12_c1_ou_en_est_on.png"],
           "LOC-CTX-003": ["presentation_2025-04-03_p7_bilan.png"]}
for x in regles:
    if x["id"] in PREUVES:
        x["preuves"] = [PV + f for f in PREUVES[x["id"]]]
        for f in x["preuves"]:
            assert os.path.exists(R + f), f
fam = {}
for x in regles:
    fam.setdefault(x["famille"], []).append(x["id"])
TIT = {"contexte": "Contexte, gestion et état des ouvrages", "vitesse": "Vitesses et Métropole apaisée", "chronovelo": "Identité et aménagement Chronovélo",
       "traversees": "Traversées piétonnes du projet C1", "transport_commun": "Arrêts et gabarits des bus", "velo": "Vélos hors Chronovélo", "feux": "Feux",
       "mobilier": "Mobilier métropolitain", "eclairage": "Éclairage", "materiaux": "Matériaux et couleurs de sol", "vegetation": "Arbres, plantations et eau",
       "clotures": "Clôtures et soutènements riverains", "accessibilite": "Accessibilité"}
out["familles"] = [{"id": k, "titre": TIT[k], "nb_regles": len(v), "regles": v} for k, v in fam.items()]
utilise = {}
for x in regles:
    utilise[x["source"]["id"]] = utilise.get(x["source"]["id"], 0) + 1
    for s in x.get("sources_secondaires", []):
        utilise[s["id"]] = utilise.get(s["id"], 0) + 1
for s in out["sources"]:
    s["utilisee_par_n"] = utilise.get(s["id"], 0)
with open(R + "assets/specs/regles_locales_meylan.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(len(regles), "règles ;", len(S), "sources ;", {k: len(v) for k, v in fam.items()})
print("sources non utilisées :", [s["id"] for s in out["sources"] if not s["utilisee_par_n"]])
print("fichiers manquants :", [s["id"] for s in out["sources"] if s["fichier_local"] and s["taille_octets"] is None])
