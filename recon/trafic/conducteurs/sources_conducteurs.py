"""Catalogue des sources du volet « conducteurs » (DocRoute/17_Modele_Vehicules_Conducteurs/02_Conducteurs).

Chaque entrée : clé -> {titre, auteurs, annee, editeur, url, fichier (relatif à 02_Conducteurs/sources
ou chemin DocRoute), licence, type}.
type : « norme » (texte réglementaire ou guide de conception), « mesure » (observation / essai),
« revue » (synthèse de mesures), « logiciel » (valeurs par défaut d'un outil).
"""

SRC_DOC10 = "DocRoute/10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/sources/"

SOURCES = {
    # ---------------- France : normes et guides (Cerema / Certu / Sétra)
    "CEREMA_VIS2018": {
        "titre": "Conception des routes et autoroutes - Révision des règles sur la visibilité et les rayons en angle saillant",
        "auteurs": "Cerema", "annee": 2018, "editeur": "Cerema",
        "url": "https://madoc.univ-nantes.fr/mod/resource/view.php?id=1663768",
        "fichier": SRC_DOC10 + "Cerema_Regles_Visibilite_madoc.pdf",
        "licence": ("COPIE NON OFFICIELLE : miroir d'un cours de l'Université de Nantes (Moodle). Guide Cerema, collection "
                    "Références, oct. 2018, auquel la note technique du 01/10/2018 (BO MTES-MCTRCT 2018/10 p. 134-135, NOR "
                    "TRAT1815980N) donne valeur d'instruction ; version officielle non trouvée en accès libre (17/10/2026). "
                    "Contrôles sur documents officiels : TPR 1,8 s et 1,5 m/s² (ARP 2022 p. 30) ; γv 0,46/0,46/0,44 à "
                    "30/50/70 km/h (VSA 90/110 2014 p. 16). Consultation locale, ne pas rediffuser."), "type": "norme"},
    "ARP2022": {
        "titre": "Aménagement des routes principales (ARP), édition août 2022", "auteurs": "Cerema",
        "annee": 2022, "editeur": "Cerema", "url": "https://doc.cerema.fr (SYRACUSE/592036)",
        "fichier": SRC_DOC10 + "Cerema_ARP_Amenagement_Routes_Principales_2022.pdf",
        "licence": "Accès libre doc.cerema.fr, droits réservés", "type": "norme"},
    "ICTAVRU2009": {
        "titre": "Instruction sur les conditions techniques d'aménagement des voies rapides urbaines (ICTAVRU), réédition 2009",
        "auteurs": "Certu", "annee": 2009, "editeur": "Certu", "url": "https://doc.cerema.fr (SYRACUSE/16469)",
        "fichier": SRC_DOC10 + "CERTU_ICTAVRU_2009.pdf", "licence": "Accès libre doc.cerema.fr", "type": "norme"},
    "ACI1998": {
        "titre": "Aménagement des carrefours interurbains sur les routes principales - Carrefours plans (ACI)",
        "auteurs": "Sétra", "annee": 1998, "editeur": "Sétra", "url": "https://doc.cerema.fr (SYRACUSE/15718)",
        "fichier": SRC_DOC10 + "SETRA_ACI_Amenagement_Carrefours_Interurbains_1998.pdf",
        "licence": "Accès libre doc.cerema.fr", "type": "norme"},
    "CERTU_CU2010": {
        "titre": "Carrefours urbains : guide (coll. Références n°103)", "auteurs": "Certu", "annee": 2010,
        "editeur": "Certu", "url": "https://doc.cerema.fr (SYRACUSE/13987)",
        "fichier": SRC_DOC10 + "CERTU_Carrefours_Urbains_Guide_2010.pdf", "licence": "Accès libre doc.cerema.fr",
        "type": "norme"},
    "CERTU_FEUX2010": {
        "titre": "Guide de conception des carrefours à feux", "auteurs": "Certu", "annee": 2010, "editeur": "Certu",
        "url": "https://doc.cerema.fr (SYRACUSE/14140)",
        "fichier": SRC_DOC10 + "CERTU_Guide_Conception_Carrefours_a_Feux_2010.pdf",
        "licence": "Accès libre doc.cerema.fr", "type": "norme"},
    "CEREMA_SDB20": {
        "titre": "Savoirs de base en sécurité routière, fiche n°20 : les carrefours à feux (2013, revue 2025)",
        "auteurs": "Cerema", "annee": 2025, "editeur": "Cerema", "url": "https://doc.cerema.fr (SYRACUSE/17581)",
        "fichier": SRC_DOC10 + "Cerema_SdB_Fiche20_Carrefours_a_Feux.pdf", "licence": "Accès libre doc.cerema.fr",
        "type": "norme"},
    "CERTU_COUSSINS2010": {
        "titre": "Guide des coussins et plateaux", "auteurs": "Certu", "annee": 2010, "editeur": "Certu",
        "url": "https://doc.cerema.fr (SYRACUSE/14144)",
        "fichier": SRC_DOC10 + "CERTU_Guide_Coussins_Plateaux_2010.pdf", "licence": "Accès libre doc.cerema.fr",
        "type": "norme"},
    "VSA70_2013": {
        "titre": "Voies structurantes d'agglomération : conception des artères urbaines à 70 km/h", "auteurs": "Certu",
        "annee": 2013, "editeur": "Certu", "url": "https://doc.cerema.fr (SYRACUSE/14599)",
        "fichier": SRC_DOC10 + "CERTU_VSA70_Arteres_Urbaines_2013.pdf",
        "licence": "Accès libre mais mention « Ne pas diffuser » : consultation locale", "type": "norme"},
    "VSA90_2014": {
        "titre": "Voies structurantes d'agglomération : conception des voies à 90 et 110 km/h", "auteurs": "Cerema",
        "annee": 2014, "editeur": "Cerema", "url": "https://doc.cerema.fr (SYRACUSE/14597)",
        "fichier": SRC_DOC10 + "Cerema_VSA_90_110_2014.pdf",
        "licence": "Copie et diffusion interdites sans accord : consultation locale", "type": "norme"},
    "CERTU_GIR1999": {
        "titre": "Giratoires en ville, mode d'emploi", "auteurs": "Certu", "annee": 1999, "editeur": "Certu",
        "url": "https://doc.cerema.fr (SYRACUSE/584931)",
        "fichier": SRC_DOC10 + "CERTU_Giratoires_en_Ville_Mode_Emploi_1999.pdf", "licence": "Accès libre",
        "type": "norme"},
    "BISONFUTE": {
        "titre": "Respecter limitations de vitesse et distances de sécurité (fiche Bison Futé)",
        "auteurs": "Bison Futé / ministère", "annee": None, "editeur": "bison-fute.gouv.fr",
        "url": "https://www.bison-fute.gouv.fr/IMG/pdf/Distances_et_vitesse.pdf",
        "fichier": "bisonfute/BisonFute_Distances_et_vitesse.pdf", "licence": "Document public de l'État",
        "type": "norme"},
    "AN_QE8216": {
        "titre": "Question écrite n° 8216 et réponse : limitation à 80 km/h et jeunes conducteurs (cite l'art. R413-5 du code de la route)",
        "auteurs": "Assemblée nationale / ministère de l'Intérieur", "annee": 2018, "editeur": "Assemblée nationale",
        "url": "https://www.assemblee-nationale.fr/dyn/15/questions/QANR5L15QE8216.pdf",
        "fichier": "reglementation/AN_QE8216_R413-5_jeunes_conducteurs.pdf", "licence": "Document parlementaire public",
        "type": "norme"},
    # ---------------- France : mesures
    "ONISR2019": {
        "titre": "Observatoire des vitesses (France métropolitaine) - Résultats de l'année 2019", "auteurs": "ONISR",
        "annee": 2020, "editeur": "ONISR",
        "url": "https://www.onisr.securite-routiere.gouv.fr/sites/default/files/2021-10/Observatoire%20des%20vitesses%202019.pdf",
        "fichier": "onisr/ONISR_Observatoire_vitesses_2019.pdf",
        "licence": "Droits réservés (mentions légales ONISR) : consultation locale, constats chiffrés seulement",
        "type": "mesure"},
    "ONISR2023": {
        "titre": "Observatoire des vitesses (France métropolitaine) - Résultats de l'année 2023", "auteurs": "ONISR, Cerema",
        "annee": 2026, "editeur": "ONISR",
        "url": "https://www.onisr.securite-routiere.gouv.fr/sites/default/files/2026-02/Obs_vitesses_2023_0.pdf",
        "fichier": "onisr/ONISR_Observatoire_vitesses_2023.pdf",
        "licence": "Droits réservés (mentions légales ONISR) : consultation locale", "type": "mesure"},
    "CEREMA_V80_2020": {
        "titre": "Abaissement de la vitesse maximale autorisée à 80 km/h - Rapport final d'évaluation", "auteurs": "Cerema",
        "annee": 2020, "editeur": "Cerema / ONISR",
        "url": "https://www.onisr.securite-routiere.gouv.fr/sites/default/files/2020-08/Cerema-EvaluationV80-Juillet2020-V2.pdf",
        "fichier": "cerema/Cerema_Evaluation_V80_rapport_final_2020.pdf", "licence": "Droits réservés : consultation locale",
        "type": "mesure"},
    "GAM_JTR2018": {
        "titre": "Métropole apaisée et aménagements modes actifs (présentation JTR 2018)", "auteurs": "L. Faure (Grenoble-Alpes Métropole)",
        "annee": 2018, "editeur": "Université Gustave Eiffel (JTR)",
        "url": "https://jtr.univ-gustave-eiffel.fr/fileadmin/contributeurs/JTR/Annee_2018/Presentations_2018/Session2/3_Faure_Grenoble.pdf",
        "fichier": "grenoble/UGE_JTR2018_Faure_Grenoble_ville30.pdf", "licence": "Présentation publique",
        "type": "contexte"},
    # ---------------- Europe : mesures
    "VIAS2021": {
        "titre": "Mesure nationale de comportement en matière de vitesse 2021 (rapport 2023-R-10-FR)",
        "auteurs": "Wardenier N., Vervoort M., Silverans P., Boets S., Ben Messaoud Y.", "annee": 2023,
        "editeur": "Vias institute (Belgique)",
        "url": "https://www.vias.be/publications/Nationale%20gedragsmeting%20snelheid%202021/Mesure_nationale_de_comportement_en_mati%C3%A8re_de_vitesse_2021.pdf",
        "fichier": "vias/Vias_Mesure_nationale_comportement_vitesse_2021.pdf",
        "licence": "Reproduction autorisée avec mention de la source (p. 2)", "type": "mesure"},
    "UDRIVE_D41": {
        "titre": "UDRIVE D41.1 - The UDrive dataset and key analysis results", "auteurs": "Bärgman J., van Nes N. et al.",
        "annee": 2017, "editeur": "Projet UE FP7 UDRIVE (GA 314050)",
        "url": "https://erticonetwork.com/wp-content/uploads/2017/12/UDRIVE-D41.1-UDrive-dataset-and-key-analysis-results-with-annotation-codebook.pdf",
        "fichier": "udrive/UDRIVE_D41.1_dataset_key_results_2017.pdf", "licence": "Livrable public (Dissemination level: Public)",
        "type": "mesure"},
    "BOSETTI2014": {
        "titre": "On the human control of vehicles: an experimental study of acceleration",
        "auteurs": "Bosetti P., Da Lio M., Saroldi A.", "annee": 2014,
        "editeur": "European Transport Research Review 6:157-170", "url": "https://doi.org/10.1007/s12544-013-0120-2",
        "fichier": "articles/Bosetti_2014_ETRR_acceleration_human_control.pdf", "licence": "Open access (SpringerOpen)",
        "type": "mesure"},
    "MARKKULA2016": {
        "titre": "A farewell to brake reaction times? Kinematics-dependent brake response in naturalistic rear-end emergencies",
        "auteurs": "Markkula G., Engström J., Lodin J., Bärgman J., Victor T.", "annee": 2016,
        "editeur": "Accident Analysis and Prevention 95:209-226 (version auteur White Rose)",
        "url": "https://eprints.whiterose.ac.uk/id/eprint/102162/",
        "fichier": "articles/Markkula_2016_AAP_farewell_brake_reaction_times_AAM.pdf",
        "licence": "Manuscrit accepté en dépôt ouvert", "type": "mesure"},
    "SALLES2020": {
        "titre": "Extending the Intelligent Driver Model in SUMO and Verifying the Drive Off Trajectories with Aerial Measurements",
        "auteurs": "Salles D., Kaufmann S., Reuss H.-C.", "annee": 2020, "editeur": "SUMO User Conference 2020 (SCP 1, 2022)",
        "url": "https://eclipse.dev/sumo/documents/2020/SUMO2020_paper_28.pdf",
        "fichier": "sumo/Salles_2020_SUMO2020_paper28_EIDM_drive_off.pdf",
        "licence": ("Fichier local : version eclipse.dev des actes SUMO 2020 (EasyChair), sans mention de licence. Même article "
                    "publié dans SUMO Conference Proceedings vol. 1 (TIB Open Publishing, 01/07/2022, doi:10.52825/scp.v1i.95) "
                    "sous CC BY 3.0 DE (page de l'éditeur consultée le 17/10/2026)."),
        "type": "mesure"},
    "GIUFFRE2016": {
        "titre": "Gap-acceptance parameters for roundabouts: a systematic review",
        "auteurs": "Giuffrè O., Granà A., Tumminello M. L.", "annee": 2016,
        "editeur": "European Transport Research Review 8:2", "url": "https://doi.org/10.1007/s12544-015-0190-4",
        "fichier": "giratoires/Giuffre_2015_ETRR_critical_headway_review.pdf", "licence": "Open access (SpringerOpen)",
        "type": "revue"},
    "MAIGA2006": {
        "titre": "L'utilité d'un carrefour giratoire dans la sécurité routière (séminaire AGEPAR/AIPCR, Lomé)",
        "auteurs": "Maiga O.", "annee": 2006, "editeur": "AIPCR",
        "url": "https://www.piarc.org/ressources/documents/899,Maiga-Commn-AGEPAR.pdf",
        "fichier": "giratoires/PIARC_AGEPAR_Maiga.pdf", "licence": "Document public AIPCR", "type": "revue"},
    "DABROWSKA2021": {
        "titre": "Road users' behaviour study in areas of zebra crosswalks",
        "auteurs": "Dąbrowska-Loranc M., Sicińska K., Zielińska A.", "annee": 2021,
        "editeur": "Transport Problems 16(3)", "url": "http://transportproblems.polsl.pl/pl/Archiwum/2021/zeszyt3/2021t16z3_16.pdf",
        "fichier": "pietons/Dabrowska_2021_TransportProblems_zebra.pdf",
        "licence": "CC BY 4.0 (fiche DOAJ de la revue Transport Problems, ISSN 1896-0596 ; consultée le 17/10/2026) ; doi:10.21307/tp-2021-052",
        "type": "mesure"},
    "GANKHUYAG2023": {
        "titre": "Naturalistic Yielding Behavior of Drivers at an Unsignalized Intersection based on Survival Analysis",
        "auteurs": "Gankhuyag D., Olaverri-Monreal C.", "annee": 2023, "editeur": "arXiv:2307.10879 (données inD, Aachen)",
        "url": "https://arxiv.org/abs/2307.10879", "fichier": "pietons/arXiv2307.10879_naturalistic_yielding_survival.pdf",
        "licence": "Licence arXiv (lecture)", "type": "mesure"},
    "SCHLEINITZ2017": {
        "titre": "The German Naturalistic Cycling Study - Comparing cycling speed of riders of different e-bikes and conventional bicycles (Safety Science 92:290-297) ; valeurs lues sur la diapositive 5 de K. Schleinitz (ETSC)",
        "auteurs": "Schleinitz K., Petzoldt T., Franke-Bartholdt L., Krems J., Gehlert T.", "annee": 2017,
        "editeur": "Safety Science / ETSC", "url": "https://etsc.eu/wp-content/uploads/Katja-Schleinitz.pdf",
        "fichier": "cyclistes/ETSC_Schleinitz_German_naturalistic_cycling_slides.pdf", "licence": "Présentation publique",
        "type": "mesure"},
    "TWADDLE2016": {
        "titre": "Modeling the speed, acceleration and deceleration of bicyclists for microscopic traffic simulation (preprint TRR 2587)",
        "auteurs": "Twaddle H., Grigoropoulos G.", "annee": 2016, "editeur": "Transportation Research Record 2587:8-16",
        "url": "https://radverkehr.uni-wuppertal.de/fileadmin/bauing/radverkehr/Publikationen/Preprints/Twaddle_Grigoropoulos_2016_Modeling_the_speed__acceleration_and_deceleration_of_bicyclists_for_microscopic_traffic_simulation.pdf",
        "fichier": "cyclistes/Twaddle_Grigoropoulos_2016_bicyclist_speed_accel_decel_preprint.pdf",
        "licence": "Preprint auteur", "type": "mesure"},
    # ---------------- International : mesures
    "NCHRP400": {
        "titre": "NCHRP Report 400 - Determination of Stopping Sight Distances", "auteurs": "Fambro D. B., Fitzpatrick K., Koppa R. J.",
        "annee": 1997, "editeur": "Transportation Research Board",
        "url": "https://onlinepubs.trb.org/onlinepubs/nchrp/nchrp_rpt_400.pdf", "fichier": "trb/nchrp_rpt_400.pdf",
        "licence": "Copyright NAS, téléchargement libre : consultation locale (PDF scanné, OCR local)", "type": "mesure"},
    "HUANG2018": {
        "titre": "Developing Robot Driver Etiquette Based on Naturalistic Human Driving Behavior",
        "auteurs": "Huang X., Zhang S., Peng H.", "annee": 2018, "editeur": "arXiv:1808.00869 (données SPMD, Ann Arbor)",
        "url": "https://arxiv.org/abs/1808.00869", "fichier": "articles/Huang_2018_arXiv1808.00869_robot_driver_etiquette_SPMD.pdf",
        "licence": "Licence arXiv (lecture)", "type": "mesure"},
    "ZHU2019": {
        "titre": "Safe, Efficient, and Comfortable Velocity Control based on Reinforcement Learning for Autonomous Driving",
        "auteurs": "Zhu M., Wang Y., Pu Z., Hu J., Wang X., Ke R.", "annee": 2019, "editeur": "arXiv:1902.00089 (données NGSIM)",
        "url": "https://arxiv.org/abs/1902.00089", "fichier": "articles/Zhu_2019_arXiv1902.00089_velocity_control_RL_NGSIM.pdf",
        "licence": "Licence arXiv (lecture)", "type": "mesure"},
    "LEUNGBOOTNAK2025": {
        "titre": "Modeling Headway in Heterogeneous and Mixed Traffic Flow: A Statistical Distribution Based on a General Exponential Function",
        "auteurs": "Leungbootnak N., Li Z., Wei Z., Lord D., Zhang Y.", "annee": 2025,
        "editeur": "arXiv:2511.03154 (données highD, exiD, NGSIM, Waymo, Lyft)", "url": "https://arxiv.org/abs/2511.03154",
        "fichier": "articles/Leungbootnak_2025_arXiv2511.03154_headway_highD_NGSIM.pdf", "licence": "Licence arXiv (lecture)",
        "type": "mesure"},
    "THIEMANN2008": {
        "titre": "Estimating Acceleration and Lane-Changing Dynamics Based on NGSIM Trajectory Data",
        "auteurs": "Thiemann C., Treiber M., Kesting A.", "annee": 2008, "editeur": "arXiv:0804.0108 (TRR 2088)",
        "url": "https://arxiv.org/abs/0804.0108", "fichier": "articles/Thiemann_2008_arXiv0804.0108_NGSIM_accel_lanechange.pdf",
        "licence": "Licence arXiv (lecture)", "type": "mesure"},
    "FHWA_STM2008": {
        "titre": "Traffic Signal Timing Manual (FHWA-HOP-08-024)", "auteurs": "Koonce P. et al.", "annee": 2008,
        "editeur": "FHWA", "url": "https://ops.fhwa.dot.gov/publications/fhwahop08024/fhwa_hop_08_024.pdf",
        "fichier": "fhwa/FHWA_HOP_08_024_Traffic_Signal_Timing_Manual_2008.pdf",
        "licence": "Œuvre du gouvernement fédéral US (domaine public)", "type": "revue"},
    "FHWA_ROUND2000": {
        "titre": "Roundabouts: An Informational Guide (FHWA-RD-00-067)", "auteurs": "Robinson B. W. et al.", "annee": 2000,
        "editeur": "FHWA", "url": "https://www.fhwa.dot.gov/publications/research/safety/00067/00067.pdf",
        "fichier": "fhwa/FHWA_RD_00_067_Roundabouts_Informational_Guide_2000.pdf",
        "licence": "Œuvre du gouvernement fédéral US (domaine public)", "type": "norme"},
    "FHWA_RRFB2016": {
        "titre": "Investigating Improvements to Pedestrian Crossings with an Emphasis on the RRFB (FHWA-HRT-15-043)",
        "auteurs": "Fitzpatrick K. et al.", "annee": 2016, "editeur": "FHWA",
        "url": "https://www.fhwa.dot.gov/publications/research/safety/15043/15043.pdf",
        "fichier": "fhwa/FHWA_HRT_15_043_Pedestrian_Crossings_RRFB_2016.pdf",
        "licence": "Œuvre du gouvernement fédéral US (domaine public)", "type": "mesure"},
    "QK4_HCS2021": {
        "titre": "E'town Planning Study - Appendix B Capacity Analysis (rapports HCS7 Two-Way Stop-Control, valeurs de base HCM)",
        "auteurs": "QK4 / KYTC", "annee": 2021, "editeur": "QK4",
        "url": "https://www.qk4.com/wp-content/uploads/2021/09/EECS-Appendix-B-Capacity-Analysis.pdf",
        "fichier": "creneaux/QK4_EECS_AppendixB_Capacity.pdf", "licence": "Document d'étude public", "type": "norme"},
    "VAUGHAN2006": {
        "titre": "Committee of the Whole - Medallion Boulevard and Morning Star Drive (étude de respect de l'arrêt au STOP)",
        "auteurs": "City of Vaughan (Ontario), Engineering", "annee": 2006, "editeur": "City of Vaughan",
        "url": "https://meetingarchives.vaughan.ca/committee_2006/pdf/CWA1211_22.pdf",
        "fichier": "stop/Vaughan_2006_CWA1211_22_stop_compliance.pdf", "licence": "Rapport municipal public", "type": "mesure"},
    "KESTING2008": {
        "titre": "Calibrating car-following models using trajectory data: Methodological study",
        "auteurs": "Kesting A., Treiber M.", "annee": 2008,
        "editeur": "Transportation Research Record 2088 (version arXiv 0803.4063)", "url": "https://arxiv.org/abs/0803.4063",
        "fichier": "DocRoute/17_Modele_Vehicules_Conducteurs/03_Modeles_Existants/sources/articles/Kesting_Treiber_2008_Calibration_arXiv_0803.4063.pdf",
        "licence": "Prépublication arXiv (licence arXiv par défaut) : citation des valeurs", "type": "mesure"},
    "ZHU2018": {
        "titre": "Modeling car-following behavior on urban expressways in Shanghai: A naturalistic driving study",
        "auteurs": "Zhu M., Wang X., Tarko A., Fang S.", "annee": 2018,
        "editeur": "Transportation Research Part C 93 (version arXiv 1811.06395)", "url": "https://arxiv.org/abs/1811.06395",
        "fichier": "DocRoute/17_Modele_Vehicules_Conducteurs/03_Modeles_Existants/sources/articles/Zhu_Wang_Tarko_Fang_2018_CF_Shanghai_NDS_arXiv_1811.06395.pdf",
        "licence": "Prépublication arXiv : citation des valeurs", "type": "mesure"},
    "SUMO_DOC": {
        "titre": "Documentation SUMO 1.27.1 (Definition of Vehicles, Vehicle Type Parameter Defaults, Car-Following Models)",
        "auteurs": "Eclipse SUMO / DLR", "annee": 2026, "editeur": "Eclipse Foundation",
        "url": "https://sumo.dlr.de/docs/", "fichier": "C:/Program Files (x86)/Eclipse/Sumo/doc/userdoc (installation locale, lecture seule)",
        "licence": "EPL-2.0 (logiciel) ; documentation consultée localement", "type": "logiciel"},
}
