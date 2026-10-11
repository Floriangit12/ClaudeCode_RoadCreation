"""Verdicts des revues adverses utilisés par la résolution (données, aucune logique).

Sources :
- revue adverse de la cohérence v3 (11/10/2026, agent REVUE, 41 éléments relus ; preuves dans
  scratchpad/v2_tmp/revue_adverse_coherence_v3/) : texte transmis par l'orchestrateur du flux, recopié ici
  sans interprétation (verdict, objet, motif court, fichiers de preuve, position relue) ; c'est la revue de
  référence : elle porte sur les décisions de la cohérence v3 lue par la résolution ;
- revue adverse de la cohérence v2 (11/10/2026, 35 éléments relus ; preuves dans
  scratchpad/v2_tmp/revue_adverse_coherence_v2/) : un verdict v2 ne vaut que pour la décision qu'il a relue
  (position relue P_RELU_V2, RES-SRC-002) ;
- revue adverse de la cohérence v1 (tâche wdbpt58qa, result.revue.verdicts) : seulement les verdicts qui
  portent encore sur une décision (arbre_396) ;
- secondes lectures faites par l'agent RÉSOLUTION (11/10/2026) sur les vignettes des revues v2 et v3 :
  double lecture (P16) des absences, des rejets et des positions reprises contre la cohérence.

Chaque entrée : verdict ∈ {juste, faux, incertain} ; portee ∈ {position, azimut, existence, conforme, fleche,
non_instanciation} ; groupe : identifiants couverts par le même verdict (membres d'un même support) ;
decision_relue : la décision de la cohérence que le verdict juge ; p_relu_local : position relue (repère local).
"""

REVUE_V3_ID = "revue_adverse_coherence_v3"
REVUE_V3_DOSSIER = "scratchpad/v2_tmp/revue_adverse_coherence_v3"
REVUE_V2_ID = "revue_adverse_coherence_v2"
REVUE_V2_DOSSIER = "scratchpad/v2_tmp/revue_adverse_coherence_v2"
REVUE_V1_ID = "revue_adverse_coherence_v1"
RELECTURE_ID = "seconde_lecture_resolution"
TOLERANCE_LIEN_M = 0.05      # RES-SRC-002 : un verdict de position ne vaut que pour une position à ≤ 5 cm de la position relue

REVUE_V2 = [
    {"n": 1, "objet": "pan_C113_1", "portee": "azimut", "verdict": "juste",
     "motif": "face bleue vue depuis 9834f494, 6e97bb8c, e86aa913 (obliquité 1-9°) ; poteau sur C dans les 4 vues",
     "preuves": ["planches/pan_C113_1.jpg"]},
    {"n": 2, "objet": "pan_AB3a_3", "portee": "position", "verdict": "juste",
     "motif": "3 photos 2026 calées (f8d91bb1, ded07efa, 00c1ba9a) : triangle AB3a et poteau sur C, porte complète 23,3° ; "
              "réserve : statut « existant (inchangé) » faux pour un panneau déplacé de 4 m en 2025 (Q8)",
     "reserve_statut": "déplacé lors des travaux 2025 (mesuré sur photos 2026)", "preuves": ["planches/pan_AB3a_3.jpg"]},
    {"n": 3, "objet": "pan_AB3a_2", "groupe": ["pan_AB3a_2", "pan_B2a_1", "pan_M9_2"], "portee": "position",
     "verdict": "incertain", "azimut": "plausible",
     "motif": "azimut plausible (15-25° selon le relèvement de 9ef861d4) ; position non prouvée : fût à +0,37 / 0 / −1,0 m "
              "de C sur eeb2f8f1 / 79a18815 / mly:1207034570953803, pose Mapillary fausse de 2-3° (Q2), σ 0,06 m intenable (Q6)",
     "preuves": ["ab3a_large_pnx_79a18815.jpg", "ab3a_large_pnx_eeb2f8f1.jpg", "ab3a_large_mly_1207034570953803.jpg",
                 "gcp_mly_vs_pnx.jpg"]},
    {"n": 4, "objet": "lamp_12668620636", "portee": "position", "verdict": "juste",
     "motif": "ortho 2022 : mât au centre de la jardinière ronde, ombre à 334° depuis C, détecteur O à 0,2 m",
     "preuves": ["planches/lamp_12668620636.jpg"]},
    {"n": 5, "objet": "lamp_12668578865", "portee": "position", "verdict": "juste",
     "motif": "ombre fine de ≈ 2,6 m depuis le disque clair en C ; aucune ombre depuis A ; cohérent avec la mesure v1 à 0,3 m",
     "preuves": ["planches/lamp_12668578865.jpg"]},
    {"n": 6, "objet": "pan_J5_1", "portee": "position", "verdict": "juste",
     "motif": "pied de la balise sur C dans 4 vues calées (9834f494, e86aa913, 6e97bb8c, e5d79de9), porte complète 84°",
     "preuves": ["planches/pan_J5_1.jpg"]},
    {"n": 7, "objet": "pan_AB4_2", "portee": "position", "verdict": "juste",
     "motif": "poteau du STOP sur C à 3 px près sur f8d91bb1, ded07efa, 00c1ba9a (2026), porte complète 17,4°",
     "preuves": ["planches/pan_AB4_2.jpg"]},
    {"n": 8, "objet": "lamp_9514825221", "portee": "position", "verdict": "juste",
     "motif": "ortho 2022 graduée : une seule ombre de mât à 338°, pied au bout SSE en (19,0 ; −62,07)",
     "preuves": ["og_matcam.jpg"]},
    {"n": 9, "objet": "pan_B6a1_1", "groupe": ["pan_B6a1_1", "lamp_9514828517", "pan_C13a_1"], "portee": "position",
     "verdict": "juste", "reserve_sigma": "σ 0,05 m isotrope injustifié : une seule photo discriminante (ded07efa), "
                                        "profondeur tirée de l'ombre 2022 (Q6)",
     "motif": "ded07efa (2026, 7,5 m) : mât porteur sur C, A à 28 px ; ombre 2022 finissant en C",
     "preuves": ["planches/lamp_9514828517.jpg"]},
    {"n": 10, "objet": "pan_D21_1", "groupe": ["pan_D21_1", "pan_D21_2"], "portee": "non_instanciation",
     "verdict": "incertain",
     "motif": "D21 présent le 2025-08-31 en plein chantier (a83dae90, 81882270) ; silence du levé GAM non probant ; P12 non traité",
     "preuves": []},
    {"n": 11, "objet": "pan_J5_2", "portee": "non_instanciation", "verdict": "incertain",
     "motif": "même îlot et même preuve que le D21 ; aucune image après les travaux", "preuves": []},
    {"n": 12, "objet": "mat_camera_9831317323", "portee": "position", "verdict": "juste",
     "motif": "une seule ombre portant lanterne et caméra, pied en (19,0 ; −62,07) ; fusion P5 fondée sur l'image",
     "fusion_avec": "lamp_9514825221", "preuves": ["og_matcam.jpg"]},
    {"n": 13, "objet": "lamp_9665416717", "portee": "position", "verdict": "faux",
     "motif": "5 photos Panoramax décisives placent le fût à ≈ 0,10 ± 0,08 m de A (C à ≈ 4σ) ; la mesure pixel_ortho "
              "ORTHO_A-0167 lit la lanterne, pas le pied (Q1, Q7)",
     "preuves": ["l717k_all.jpg", "l717t_all.jpg", "hag_l717.jpg", "og_l717.jpg"]},
    {"n": 14, "objet": "feu_NE_droite", "portee": "position", "verdict": "juste",
     "motif": "mât sur T = C sur 5c0d1d39, 9834f494, 119d9094, 6e97bb8c ; ombre 2022 au même point", "preuves": []},
    {"n": 15, "objet": "lamp_9665416817", "portee": "position", "verdict": "juste",
     "motif": "fût à bannière sur C sur 6e97bb8c, e540bf1d, 7651c539, e5d79de9 ; porte complète 18°", "preuves": []},
    {"n": 16, "objet": "feu_VERC_droite", "portee": "position", "verdict": "juste",
     "motif": "mât et modules sur T et C (119d9094, 5c0d1d39, 9834f494, e5d79de9) ; cohérent avec l'ombre 2022", "preuves": []},
    {"n": 17, "objet": "pan_AB3a_1", "groupe": ["pan_AB3a_1", "lamp_12894130974", "pan_C114_1", "pan_M9_1"],
     "portee": "position", "verdict": "juste",
     "motif": "mât portant AB3a, C114 et M9 sur C dans 4 vues ; départ d'ombre 2022 en C", "preuves": []},
    {"n": 18, "objet": "pan_B21a1_4", "portee": "azimut", "verdict": "incertain",
     "motif": "aucune image ; cible tirée de la voie OpenDRIVE la plus proche, non vérifiée", "preuves": []},
    {"n": 19, "objet": "lamp_lidar_VERC_E", "portee": "position", "verdict": "incertain",
     "motif": "deux poteaux bois proches ; identité du « lampadaire » non établie", "preuves": ["lve_all.jpg"]},
    {"n": 20, "objet": "potelet_13827066658", "portee": "position", "verdict": "incertain",
     "motif": "repère (s, t) hors étendue (P14) ; potelet fonctionnel sur la voie piétonne d'une zone de rencontre", "preuves": []},
    # objets « conformes » tirés au hasard (graine 20261011)
    {"n": 21, "objet": "portail_12462947807", "portee": "conforme", "verdict": "incertain", "motif": "aucun portail identifiable sur l'ortho 2022", "preuves": []},
    {"n": 22, "objet": "lamp_lidar_SW_NO", "portee": "conforme", "verdict": "juste",
     "motif": "position triangulée à 0,07 m ; type douteux : poteau bois à câble, probablement poteau de réseau (CF-ENR-024)",
     "reserve_type": "poteau_reseau probable", "preuves": ["lsw_all.jpg"]},
    {"n": 23, "objet": "portail_12976463291", "portee": "conforme", "verdict": "incertain", "motif": "invérifiable (OSM 2026-04, ortho 2022 antérieure)", "preuves": []},
    {"n": 24, "objet": "lamp_9665416617", "portee": "conforme", "verdict": "juste", "motif": "ombre 2022 finissant sur P", "preuves": []},
    {"n": 25, "objet": "lamp_9514795817", "portee": "conforme", "verdict": "incertain",
     "motif": "pied d'ombre 2022 à 0,51 m le long de la bordure ; objet déduit 2026, ombre seule non probante", "preuves": []},
    {"n": 26, "objet": "barriere_levante_12462947804", "portee": "conforme", "verdict": "incertain", "motif": "aucun fût ni coffret sur l'ortho 2022", "preuves": []},
    {"n": 27, "objet": "arbre_028", "portee": "existence", "verdict": "faux",
     "motif": "absent en juillet 2026 : pelouse sèche nue sur ded07efa (7,6 m), f8d91bb1 (10,4 m), 00c1ba9a (13,7 m) ; "
              "poses validées par arbre_026 voisin", "preuves": ["arb1_all.jpg", "arbn_all.jpg"]},
    {"n": 28, "objet": "arbre_236", "portee": "conforme", "verdict": "incertain", "motif": "ni tronc ni couronne lisibles", "preuves": []},
    {"n": 29, "objet": "arbre_312", "portee": "conforme", "verdict": "juste", "motif": "bord de couronne d'un arbre pourpre ; levé GAM", "preuves": []},
    {"n": 30, "objet": "arbre_027", "portee": "existence", "verdict": "faux",
     "motif": "absent en juillet 2026 : sur f8d91bb1 (11,5 m), ded07efa (10,2 m), 00c1ba9a (11,7 m) la projection traverse "
              "des voitures puis la façade, sans houppier ni tronc", "preuves": ["arb1_all.jpg", "arbn_all.jpg"]},
    # flèches
    {"n": 31, "objet": "MF-0286", "portee": "fleche", "verdict": "faux",
     "motif": "tiret rectiligne de la ligne axiale (0,15 × 3 m, sans pointe), ancrage t = 0,038 m ; la fusion le déclare « retirer »",
     "preuves": ["fl_MF-0286.jpg", "fl_MF-0286_brut.jpg"]},
    {"n": 32, "objet": "MF-0774", "portee": "fleche", "verdict": "faux",
     "motif": "flèche et recalage à 100 % sur la classe trottoir : conflit surface / marquage, pas un recalage", "preuves": ["fl_MF-0774.jpg"]},
    {"n": 33, "objet": "MF-6013", "portee": "fleche", "verdict": "juste",
     "motif": "voie bornée par K-0627 et ML-5297 (3,16 m), marges 0,61 / 1,28 m égalisées ; recalage dans la chaussée (MQ-FLE-006)",
     "preuves": ["fl_MF-6013.jpg"]},
    {"n": 34, "objet": "MF-8000", "portee": "fleche", "verdict": "faux",
     "motif": "la bordure K-0415 traverse la boîte à −0,05 m du centre : fausse voie de 3,59 m ; recalage 32 % hors chaussée",
     "preuves": ["fl_MF-8000.jpg"]},
    {"n": 35, "objet": "MF-5525", "portee": "fleche", "verdict": "juste",
     "motif": "levée GAM 2026 coïncidant avec la flèche TAG de l'ortho 2022 : gardée avec son écart", "preuves": ["fl_MF-5525.jpg"]},
]

# positions relues par la revue v2 (n° -> position locale de la décision jugée) : décisions de la cohérence v2,
# telles qu'appliquées par la première résolution (historique/journal_resolution_r1.json, xy_apres_local) ;
# pour le n° 13 (faux), position C de la mesure rejetée (ORTHO_A-0167)
P_RELU_V2 = {1: [6.873, 16.84], 2: [25.72, -138.95], 4: [-147.64, 107.55], 5: [-124.33, 119.38], 6: [17.606, 14.805],
             7: [32.22, -137.57], 8: [19.0, -62.07], 9: [13.25, -140.34], 12: [19.0, -62.07], 13: [45.57, 51.94],
             14: [6.278, 15.018], 15: [16.052, 24.127], 16: [13.941, -12.512], 17: [-8.487, 23.779]}

# revue adverse de la cohérence v3 (référence). Fichiers de preuve relatifs à REVUE_V3_DOSSIER (vignettes graduées
# en pixels, photos Panoramax 2026-07-28 et 2025-05-18, orthos PCRS 2022 / IGN 2024 / CRAIG 2024 / Pléiades 2025).
REVUE_V3 = [
    # ------------------------------------------------------------------ top 20 du rapport de cohérence v3
    {"n": 1, "objet": "pan_C113_1", "portee": "position", "decision_relue": "reorientation", "verdict": "juste",
     "p_relu_local": [6.873, 16.84], "azimut": "juste", "azimut_relu_deg": 65.0, "photos": ["pnx:9834f494", "pnx:e86aa913"],
     "motif": "face bleue vue depuis 9834f494 et e86aa913 (obliquité 1° et 5°), poteau sur C dans les 4 vues ; Q1 en "
              "accord (Σr² 1,74 contre 13,7 pour A)", "preuves": ["coherence/planches/pan_C113_1.jpg"]},
    {"n": 2, "objet": "pan_AB3a_3", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [25.72, -138.95], "reserve_statut": "déplacé lors des travaux 2025 (mesuré sur photos 2026)",
     "motif": "ded07efa, f8d91bb1, 00c1ba9a (2026) : triangle et poteau sur C, A ne porte rien ; statut 2026 et drapeaux "
              "budget_source_depasse / deplace_par_travaux (10,7σ) posés", "preuves": ["coherence/planches/pan_AB3a_3.jpg"]},
    {"n": 3, "objet": "pan_AB3a_2", "groupe": ["pan_AB3a_2", "pan_B2a_1", "pan_M9_2"], "portee": "position",
     "decision_relue": "deplacement_par_la_regle", "verdict": "incertain", "p_relu_local": [52.67, 61.758],
     "azimut": "plausible (revue v2 n° 3, non contesté par la revue v3)",
     "motif": "position non prouvée : fût au-delà de C dans le sens A→C de 0,33° (≈ 0,17 m) sur 79a18815 et 0,75° "
              "(≈ 0,45 m) sur eeb2f8f1 : direction juste, ampleur latérale sous-estimée de 0,2 à 0,45 m, profondeur non "
              "observée ; mly:1207034570953803 encore affichée décisive alors que sa pose est fausse de 2-3°",
     "preuves": ["ab3a2_pnx_79a18815.jpg", "ab3a2_pnx_eeb2f8f1.jpg"]},
    {"n": 4, "objet": "lamp_12668620636", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [-147.64, 107.55],
     "motif": "ortho PCRS 2022 : mât au centre de la jardinière ronde, ombre (334°) partant de C ; détecteur d'ombres à 0,2 m ; "
              "lecture pixel_ortho admise par Q7 (corroborée)", "preuves": []},
    {"n": 5, "objet": "lamp_12668578865", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [-124.33, 119.38],
     "motif": "ombre fine partant du disque clair en C jusqu'à l'ombre de la lanterne au NNO ; aucune ombre depuis A "
              "(coin d'une voiture garée)", "preuves": []},
    {"n": 6, "objet": "pan_J5_1", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [17.606, 14.805],
     "motif": "9834f494 : balise à u ≈ 152, C à 158, A à 197 ; sur C aussi sur e86aa913, e5d79de9, 7651c539 ; Q1 : 5 votes "
              "pour la mesure, 0 pour A", "preuves": []},
    {"n": 7, "objet": "pan_AB4_2", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [32.253, -137.709],
     "reserve_surface": "sur ab42_pnx_ded07efa.jpg le poteau est sur M (u ≈ 4325, M 4325,1) et C à 5,6 px (≈ 0,12 m) : la "
                        "poussée de −0,25 m par la règle (M en classe « chaussée ») éloigne l'objet de la ligne observée (R8)",
     "motif": "ded07efa, f8d91bb1, 00c1ba9a (2026) : STOP à la pointe de l'îlot herbeux ; le « vote A » de 00c1ba9a vient "
              "du poteau AB3a_3 voisin", "preuves": ["ab42_pnx_ded07efa.jpg", "ab42_pnx_f8d91bb1.jpg", "ab42_pnx_00c1ba9a.jpg"]},
    {"n": 8, "objet": "lamp_9514825221", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [19.0, -62.07],
     "motif": "ortho 2022 : une seule ombre porte la lanterne et la caméra, pied en (19,0 ; −62,07) ; deux lectures "
              "indépendantes (Q7)", "preuves": []},
    {"n": 9, "objet": "lamp_12887274329", "portee": "non_instanciation", "decision_relue": "non_instanciation",
     "verdict": "incertain", "existence": "deplacement_probable", "p_probable_local": [-14.7, -127.4],
     "motif": "pas de mât au point OSM sur 00c1ba9a (15,9 m), mais un mât gris haut (≥ 4 m visibles) est à 0,1° de la "
              "projection sur ded07efa (plus loin sur la visée) et une tête de mât sur f8d91bb1 ; triangulés en "
              "(−14,7 ; −127,4), ≈ 7,6 m à l'ouest du nœud OSM (intersection 8°, profondeur peu sûre) ; tag OSM "
              "lamp_mount=straight_mast : « déplacement probable, à vérifier sur le terrain », pas « absent »",
     "preuves": ["c_ded_l1288.jpg", "c_00c_l1288.jpg", "c_f8d_l1288.jpg"]},
    {"n": 10, "objet": "pan_D21_1", "groupe": ["pan_D21_1", "pan_D21_2"], "portee": "non_instanciation",
     "decision_relue": "non_instanciation", "verdict": "incertain",
     "motif": "inchangé (Q9 hors lot) : seule preuve visuelle du 2025-08-31 en plein chantier, aucune hypothèse relocalisée",
     "preuves": []},
    {"n": 11, "objet": "pan_J5_2", "portee": "non_instanciation", "decision_relue": "non_instanciation",
     "verdict": "incertain", "motif": "même îlot et même absence de preuve postérieure aux travaux que le D21", "preuves": []},
    {"n": 12, "objet": "mat_camera_9831317323", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [19.0, -62.07], "fusion_avec": "lamp_9514825221",
     "motif": "une seule ombre porte la lanterne et le boîtier, pied en (19,0 ; −62,07) ; fusion "
              "FUS-lamp_9514825221-mat_camera_9831317323 fondée sur l'image", "preuves": []},
    {"n": 13, "objet": "feu_NE_droite", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [6.278, 15.018],
     "motif": "Q1 en accord (Σr² 12,9 contre 24,8 pour A) ; mât sur la position mesurée sur 5c0d1d39, 9834f494, 119d9094",
     "preuves": []},
    {"n": 14, "objet": "lamp_9665416817", "portee": "position", "decision_relue": "deplacement", "verdict": "juste",
     "p_relu_local": [16.052, 24.127],
     "motif": "Q1 : 5 votes pour la mesure, 0 pour A (Σr² 7,3 contre 53,7) ; fût à bannière sur C sur 6e97bb8c, e540bf1d, "
              "7651c539, e5d79de9", "preuves": []},
    {"n": 15, "objet": "arbre_013", "portee": "non_instanciation", "decision_relue": "non_instanciation", "verdict": "juste",
     "existence": "absent",
     "motif": "00c1ba9a (5,0 m), ded07efa, f8d91bb1 : pelouse sèche nue devant la façade et la rampe, aucun tronc "
              "(concorde avec PANO2026-026)", "preuves": []},
    {"n": 16, "objet": "arbre_015", "portee": "non_instanciation", "decision_relue": "non_instanciation", "verdict": "juste",
     "existence": "absent", "motif": "3 vues 2026 (5,9 à 10,2 m) : sol nu entre la haie et le candélabre lamp_9514828517 "
                                     "(concorde avec PANO2026-027)", "preuves": []},
    {"n": 17, "objet": "arbre_027", "portee": "non_instanciation", "decision_relue": "non_instanciation", "verdict": "juste",
     "existence": "absent", "motif": "les 3 visées 2026 traversent des voitures garées puis la façade, sans houppier ni "
                                     "tronc ; revue de présence saisie et datée", "preuves": []},
    {"n": 18, "objet": "arbre_028", "portee": "non_instanciation", "decision_relue": "non_instanciation", "verdict": "juste",
     "existence": "absent", "motif": "pelouse nue de 7,5 à 13,7 m ; arbre_026 voisin tombe exactement dans son tronc sur "
                                     "les mêmes vues (poses validées)", "preuves": []},
    {"n": 19, "objet": "arbre_029", "portee": "non_instanciation", "decision_relue": "non_instanciation", "verdict": "juste",
     "existence": "souche_presente",
     "motif": "souche coupée visible dans la boîte sur ded07efa (6,6 m) et f8d91bb1 (10,5 m) : arbre abattu ; réserve : "
              "l'entité de la fusion est typée « souche », existence « present » (PANO2026-031), la fusion a constaté la "
              "même souche ; reste à décider si la souche est instanciée (R7)", "preuves": []},
    {"n": 20, "objet": "arbre_175", "portee": "non_instanciation", "decision_relue": "non_instanciation", "verdict": "juste",
     "existence": "absent", "motif": "BD ORTHO 2024, CRAIG 2024 et Pléiades 2025 : espace vert réaménagé, aucun houppier au "
                                     "point alors que les jeunes arbres GAM voisins sont visibles ; abattu avant 2024",
     "preuves": ["ortho_a175_large.jpg"]},
    # ------------------------------------------------------------------ objets « conformes » (graine 20261012)
    {"n": 21, "objet": "pan_B1_1", "portee": "conforme", "decision_relue": "conforme", "verdict": "incertain",
     "orientation_ambigue": "115° / 347° (une seule vue oblique, bb9c05ff)",
     "motif": "position plausible (vu devant le mât 2 depuis le NE sur bb9c05ff) ; azimut 125° tiré d'une seule vue oblique "
              "à plat (w/h 0,44), ambiguïté miroir 115° / 347° ; SIG-04 (41° attendu) « à vérifier » ; la planche de "
              "cohérence imprime « face 65° » (R10)", "preuves": ["bb9c_small.jpg"]},
    {"n": 22, "objet": "armoire_1313238971", "portee": "conforme", "decision_relue": "conforme", "verdict": "incertain",
     "motif": "PCRS 2022 : A tombe sur la bande claire de la bordure, sans coffret ; rangée de boîtes claires (ombre au NNO) "
              "1,3 à 2,5 m plus à l'ouest ; l'hypothèse pixel_ortho de la fusion (1,04 m) ne tombe sur rien ; aucune photo calée",
     "preuves": ["og_armoire.jpg"]},
    {"n": 23, "objet": "banc_8360664518", "portee": "conforme", "decision_relue": "conforme", "verdict": "incertain",
     "p_probable_local": [-73.0, -49.0],
     "motif": "banc rouge visible en 2022 et 2024 en (−73,0 ; −49,0), à 4,0 m du nœud OSM 2026 (bord d'allée dans l'emprise "
              "des travaux) ; classe « parking » sur une pelouse (R8)", "preuves": ["og_banc836.jpg", "ort_banc836.jpg"]},
    {"n": 24, "objet": "abri_SE_0396", "portee": "conforme", "decision_relue": "conforme", "verdict": "juste",
     "motif": "centroïde du polygone OSM way/185326914 remis à jour après les travaux ; concorde avec le quai bus du plan 2025 "
              "et GTFS 2026 (arrêt 0396)", "preuves": ["plan_quai_SE_z.jpg"]},
    {"n": 25, "objet": "banc_12321340512", "portee": "conforme", "decision_relue": "conforme", "verdict": "incertain",
     "motif": "sur le nouveau quai, à 5,2 m du centre de l'abri ; une seule source, aucune image postérieure aux travaux",
     "preuves": []},
    {"n": 26, "objet": "portail_13827066656", "portee": "conforme", "decision_relue": "conforme", "verdict": "incertain",
     "motif": "BD ORTHO 2024 : entrée d'allée au pied d'un nouveau bâtiment ; portillon illisible à 20 cm", "preuves": []},
    {"n": 27, "objet": "arbre_462", "portee": "conforme", "decision_relue": "conforme", "verdict": "incertain",
     "motif": "mai 2022 : pelouse visible au point, branches claires couchées autour de (−49,5 ; 150,5) : indice d'abattage "
              "après le LiDAR 2021 ; orthos 2024 ambiguës, aucune photo", "preuves": ["og_a462.jpg"]},
    {"n": 28, "objet": "arbre_325", "portee": "conforme", "decision_relue": "conforme", "verdict": "juste",
     "motif": "dans la rangée de houppiers le long du bâtiment en 2022 et 2024 (GAM σ 0,05 m)", "preuves": []},
    {"n": 29, "objet": "arbre_411", "portee": "conforme", "decision_relue": "conforme", "verdict": "juste",
     "reserve_surface": "point = sommet de couronne LiDAR (σ 1 m), classe « trottoir » à 7 m de K-0666 au milieu d'un "
                        "boisement : erreur de surface (R8)",
     "motif": "houppier présent en 2022, 2024 et sur Pléiades 2025", "preuves": ["ort_arbre_411.jpg"]},
    {"n": 30, "objet": "arbre_052", "portee": "conforme", "decision_relue": "conforme", "verdict": "juste",
     "motif": "PCRS 2022 (sans feuilles) : centre de couronne et branches rayonnant depuis le point (< 0,3 m)", "preuves": []},
    # ------------------------------------------------------------------ flèches
    {"n": 31, "objet": "MF-0769", "portee": "fleche", "decision_relue": "recalage", "verdict": "juste",
     "motif": "voie bornée par K-0402 et ML-0799 (3,03 m), résultat entièrement roulable, confiance faible affichée ; "
              "proposition normative sans image, acceptable", "preuves": ["fl_MF-0769.jpg"]},
    {"n": 32, "objet": "MF-6020", "portee": "fleche", "decision_relue": "recalage", "verdict": "juste",
     "bords_mesures": "ligne GAM (orange) à 1,20 m et ML-0785 à 1,61 m de la flèche : 0,21 m hors du centre",
     "motif": "le recalage OpenDRIVE la recentre à ≈ 0,05 m près entre les lignes réellement décrites (mesure sur "
              "fl_MF-6020.jpg) : le résultat est le bon malgré la référence faible", "preuves": ["fl_MF-6020.jpg"]},
    {"n": 33, "objet": "MF-6000", "portee": "fleche", "decision_relue": "garde_par_ortho", "verdict": "juste",
     "motif": "balayage latéral du polygone sur la PCRS 2022 : luminance maximale au décalage 0 (189,8), 174 à la position "
              "recalée (+0,22 m) ; présente en 2024 (pano_0-38)", "preuves": ["fl_MF-6000.jpg", "fl6000_zoom.jpg"]},
    {"n": 34, "objet": "MF-5527", "portee": "fleche", "decision_relue": "voie_coupee", "verdict": "juste",
     "mettre_en_cause": "ML-8000",
     "motif": "flèche GAM gardée à juste titre ; la « limite » qui coupe la boîte est ML-8000, ligne générée par MQ-DET-002 "
              "(« sans ligne de délimitation ») qui traverse en biais la voie de gauche alors que ML-5228 (GAM) délimite "
              "déjà les voies : c'est ML-8000 qu'il faut remettre en cause", "preuves": ["fl_MF-5527.jpg"]},
    {"n": 35, "objet": "MF-6018", "portee": "fleche", "decision_relue": "recalage", "verdict": "incertain",
     "motif": "le bord K-0381 est un court tronçon de bordure (nez d'îlot), pas un bord de voie le long de la flèche : "
              "largeur 3,29 m et décalage tirés d'une coupe peu représentative ; aucune image après les travaux",
     "preuves": ["fl_MF-6018.jpg"]},
    # ------------------------------------------------------------------ faux de la revue v2 recontrôlés
    {"n": 36, "objet": "lamp_9665416717", "portee": "position", "decision_relue": "reste_en_A", "verdict": "juste",
     "motif": "fût au pied à u ≈ 5698,7 pour A à 5699,3 (F 5673,9, O 5648,5) sur 79a18815 ; à 5715,0 pour A à 5718,1 "
              "(F 5699,1) sur eeb2f8f1 : composante latérale A confirmée ; profondeur non observable (vues du SO, 41-44°)",
     "preuves": ["l717_pnx_79a18815.jpg", "l717_pnx_eeb2f8f1.jpg"]},
    {"n": 37, "objet": "MF-0286", "portee": "fleche", "decision_relue": "retrait", "verdict": "juste",
     "motif": "a_retirer (ORTHO-B-102), jugée aussi douteuse par Q5 (tige à 0,03 m de l'axe de ML-6232)", "preuves": []},
    {"n": 38, "objet": "MF-0774", "portee": "fleche", "decision_relue": "conflit_surface_marquage", "verdict": "juste",
     "motif": "aucun recalage émis ; sortie conflit_surface_marquage (0 % roulable avant comme après)", "preuves": ["fl_MF-0774.jpg"]},
    {"n": 39, "objet": "MF-8000", "portee": "fleche", "decision_relue": "glissement_s", "verdict": "faux",
     "conclusion": "supprimer",
     "motif": "la flèche glissée de −11 m tombe dans un tronçon couvert par le levé GAM 2026 (lignes de voie à 1,4 m) sans "
              "aucune flèche ; ce levé contient la répétition MF-5525 dans la voie de gauche et seulement MF-5524 dans la "
              "voie de droite ; l'ancienne flèche peinte en 2022 à l'emplacement de MF-8000 est traversée par la nouvelle "
              "bordure K-0415 : supprimée par les travaux ; le levé soutient « supprimer »",
     "preuves": ["fl_MF-8000.jpg", "zn_MF8000.jpg"]},
    # ------------------------------------------------------------------ régressions v2 -> v3 cherchées hors du top 20
    {"n": 40, "objet": "pan_B6a1_1", "groupe": ["pan_B6a1_1", "pan_C13a_1", "lamp_9514828517"], "portee": "position",
     "decision_relue": "retour_source", "verdict": "faux", "p_relu_local": [12.554, -140.281],
     "position_prouvee": {"p_local": [13.25, -140.34], "source": "fusion_recensement_0.3 (PANO2026-018, triangulation)",
                          "photos": ["pnx:f8d91bb1", "pnx:ded07efa"]},
     "motif": "f8d91bb1 (2026, 3,8 m) : mât « 0456 » portant B6a1 et C13a sur F à ≈ 5 px, A à 171 px (10,7°) ; photo source "
              "de la mesure écartée par le filtre « pied visible » ; ded07efa (7,4 m) : mât à 10 px de F (≈ 0,08 m), 77 px de "
              "A ; contraste Q1 66,7 en X contre 0,7 en A ; l'ombre PCRS 2022 finit en F : la correction de 0,70 m était juste",
     "preuves": ["b6a1_pnx_f8d91bb1.jpg", "b6a1_pnx_ded07efa.jpg"]},
    {"n": 41, "objet": "feu_NE_TPC", "portee": "position", "decision_relue": "retour_source", "verdict": "faux",
     "p_relu_local": [12.0, 9.0],
     "position_prouvee": {"p_local": [11.886, 8.849], "source": "triangulation_mixte (axe triangulé, 9 vues, 75,6°)",
                          "photos": ["pnx:e5d79de9", "pnx:5c0d1d39"]},
     "motif": "e5d79de9 (5,9 m) : poteau à u ≈ 1505, T à 1500,8, A à 1471,6 (A contredit de 2°, rA = +3,0σ ; photo exclue "
              "par Q2) ; 5c0d1d39 (7,8 m) : poteau à u ≈ 782-784, T à 776,9, A à 759,4, où Q1 a enregistré un faux vote A "
              "qui pèse 6,6 sur 12,2 de Σr²(X) et renverse le verdict",
     "preuves": ["tpc_pnx_e5d79de9.jpg", "tpc_pnx_119d9094.jpg"]},
]

# observations de la revue v3 hors verdicts (problèmes systémiques R4) : non appliquées, listées pour le terrain
OBSERVATIONS_V3 = [
    {"objet": "pan_B6a1_2", "nature": "position_douteuse", "p_probable_local": [-3.28, -129.29],
     "motif": "R4 : disque B6a1 non apparié (revue de présence) triangulé sur 3 photos en (−3,28 ; −129,29), résidus "
              "< 0,09 m, ≈ 13 m de la position à 2 rayons ; identité et pose non relues"},
]

# revue v1 : verdicts encore pertinents pour une décision v2 (tâche wdbpt58qa, result.revue.verdicts)
REVUE_V1 = [
    {"objet": "arbre_396", "portee": "position", "verdict": "juste",
     "motif": "direction et position légale justes (360° 7a182db7 du 2025-05-18 : troncs de peupliers plusieurs mètres en "
              "retrait de la piste) ; 1,85 m est probablement un minimum"},
]

# seconde lecture par l'agent RÉSOLUTION des vignettes de la revue v2 (double lecture, P16)
RELECTURE = [
    {"objet": "arbre_027", "verdict": "absent_2026", "fichier": "arb1_all.jpg (rangée du haut)",
     "lecture": "les trois rayons (f8d91bb1, ded07efa, 00c1ba9a) passent sur des voitures garées puis sur la façade, "
                "aucun tronc ni houppier au pied projeté ; concordant avec la revue"},
    {"objet": "arbre_028", "verdict": "absent_2026", "fichier": "arb1_all.jpg (rangée du bas)",
     "lecture": "pied projeté sur une pelouse sèche nue à 7,6 m (ded07efa) et 10,4 m (f8d91bb1) ; les arbres visibles sur "
                "00c1ba9a sont loin derrière la haie ; concordant avec la revue"},
    {"objet": "lamp_9665416717", "verdict": "mesure_rejetee", "fichier": "l717k_all.jpg",
     "lecture": "sur les 6 vignettes le fût gris est contre A (magenta) ou au-delà, jamais sur C (cyan) : la mesure de la "
                "fusion n'est pas appliquée ; concordant avec la revue"},
    # secondes lectures sur les vignettes de la revue v3 (11/10/2026)
    {"objet": "pan_B6a1_1", "verdict": "position_F", "fichier": "b6a1_pnx_f8d91bb1.jpg, b6a1_pnx_ded07efa.jpg",
     "lecture": "f8d91bb1 : le repère F (jaune) touche le bord gauche du mât « 0456 » portant le disque B6a1 et le panonceau "
                "C13a, le repère A (magenta) tombe sur la palissade, 180 px plus à droite, sans aucun mât ; ded07efa : F au "
                "bord gauche du même mât, A sur la haie grimpante, vide : le mât est en F ; concordant avec la revue"},
    {"objet": "feu_NE_TPC", "verdict": "position_T", "fichier": "tpc_pnx_e5d79de9.jpg, tpc_pnx_119d9094.jpg",
     "lecture": "e5d79de9 : le repère T (vert) est sur le fût du support et les modules, A (magenta) sur la haie à gauche, "
                "≈ 30 px du fût ; 119d9094 : T sur le module du support, A dans le feuillage à gauche du fût : le support est "
                "en T, pas en A ; concordant avec la revue"},
    {"objet": "arbre_029", "verdict": "souche_presente", "fichier": "coherence/planches/presence/arbre_029.jpg",
     "lecture": "ded07efa (6,6 m) et f8d91bb1 (10,5 m) : une souche d'environ 0,3-0,4 m de haut, coupée net, remplit la "
                "boîte projetée ; c'est l'objet décrit (type souche, levé GAM, 0,4 m) : présent"},
    {"objet": "lamp_12887274329", "verdict": "incertain", "fichier": "c_ded_l1288.jpg",
     "lecture": "ded07efa : un mât gris clair portant un disque et une plaque se dresse derrière les voitures à u ≈ 1385-1395, "
                "juste au-dessus de la projection L1288 ; sa profondeur n'est pas lisible : ni l'absence ni le déplacement ne "
                "sont prouvés"},
    {"objet": "pan_C113_1", "verdict": "orientation_a_preciser", "fichier": "resolution_v2/c113_vues.jpg (scratch)",
     "photos": ["pnx:e5d79de9", "pnx:9834f494", "pnx:e86aa913"],
     "lecture": "face bleue (vélo) de face sur 9834f494 (caméra au 64°) et e86aa913 (60°) : la face est bien vers le NE, "
                "pas vers le SO (225° est faux) ; mais e5d79de9 (3,9 m, caméra au 167°) voit aussi la face bleue, de biais "
                "(largeur ≈ 0,45 fois la hauteur) : une face à 65° y serait vue de dos (102° de la normale) ; avec le dos vu "
                "depuis 5c0d1d39 (199°), la face est plutôt entre 77° et 109° (≈ 95°) : 65° est appliqué (revue juste, bien "
                "meilleur que 225°) et l'azimut fin est listé à préciser"},
    {"objet": "MF-8000", "verdict": "a_retirer", "fichier": "fl_MF-8000.jpg, zn_MF8000.jpg",
     "lecture": "la flèche décrite (magenta) est posée sur l'ancienne flèche peinte de 2022 que la bordure K-0415 de 2026 "
                "(rouge) coupe en deux ; sur la carte des classes sa queue est dans l'espace vert ; la position glissée (cyan) "
                "tombe sous les arbres sans aucune flèche levée : ni la position décrite ni la glissée ne sont possibles"},
    {"objet": "ML-8000", "verdict": "a_retirer", "fichier": "fl_MF-5527.jpg",
     "lecture": "ML-8000 (vert fin) part du nez d'îlot et traverse en biais la flèche GAM MF-5527 de la voie de tourne-à-gauche "
                "puis court au milieu de cette voie, à ≈ 1,6 m de ML-5228 (GAM) et ≈ 1,7 m de ML-0408 : aucun trait n'existe "
                "sur ce tracé ; la voie est déjà délimitée par ML-0408 et ML-5228"},
]


def index_revue_v2():
    """{objet: entrée} pour tous les identifiants couverts (groupes compris), avec la position relue (RES-SRC-002)."""
    out = {}
    for e in REVUE_V2:
        e2 = dict(e)
        if e["n"] in P_RELU_V2:
            e2["p_relu_local"] = P_RELU_V2[e["n"]]
        for i in e.get("groupe", [e["objet"]]):
            out[i] = e2
    return out


def index_revue_v3():
    """{objet: entrée} de la revue v3 (groupes compris)."""
    out = {}
    for e in REVUE_V3:
        for i in e.get("groupe", [e["objet"]]):
            out[i] = e
    return out


def txt(rv, src):
    if not rv:
        return None
    n = f" n° {rv['n']}" if "n" in rv else ""
    return f"{src}{n} : {rv['verdict']} — {rv['motif']}"


def verdict_position(ident, p_local, R3, R2):
    """Verdict de revue applicable à la décision de position de la cohérence v3 pour ident (RES-SRC-002) :
    (entrée, identifiant de revue, lien) ou (None, None, motif). La revue v3 juge les décisions v3 (position relue
    = position v3 décidée, vérifiée à TOLERANCE_LIEN_M) ; un verdict v2 ne vaut que si la décision v3 est celle que la
    revue v2 a relue. Un verdict non « juste » vaut toujours pour refuser (prudence)."""
    import math
    for rv, src in ((R3.get(ident), REVUE_V3_ID), (R2.get(ident), REVUE_V2_ID)):
        if not rv or rv["portee"] not in ("position",):
            continue
        p = rv.get("p_relu_local")
        if rv["verdict"] != "juste" or p is None or p_local is None:
            return rv, src, "verdict de refus ou sans position relue"
        d = math.hypot(p[0] - p_local[0], p[1] - p_local[1])
        if d <= TOLERANCE_LIEN_M:
            return rv, src, f"position relue à {d:.3f} m"
        return None, None, f"{src} n° {rv['n']} « {rv['verdict']} » non transposable : position relue à {d:.2f} m de la " \
                           f"décision courante"
    return None, None, None


def index_revue_v1():
    return {e["objet"]: e for e in REVUE_V1}


def index_relecture():
    return {e["objet"]: e for e in RELECTURE}


def entree_v3(ident):
    """Entrée de la revue v3 qui nomme ident (objet, groupe ou marque mise en cause)."""
    for e in REVUE_V3:
        if ident in e.get("groupe", [e["objet"]]) or e.get("mettre_en_cause") == ident:
            return e
    return None

# lecture des planches avant / après de la résolution (agent RÉSOLUTION, 11/10/2026), par entité
LECTURE_PLANCHES = {
    "pan_AB3a_3": "2022 : un poteau et son ombre au point avant (A) ; le point après (C) tombe dans le contour 2026 du refuge "
                  "I-0658 (jaune), comme sur les photos 2026 : déplacement cohérent avec les travaux.",
    "pan_C113_1": "poteau inchangé (0,09 m) ; la face passe de 225° (vers le SO) à 65° (vers le NE), sens confirmé par la revue.",
    "arbre_013": "fond 2022 antérieur : seule la photo 2026 (PANO2026-026) prouve l'absence ; la croix tombe sur la pelouse "
                 "au bord d'une ombre d'arbre voisin.",
    "arbre_015": "fond 2022 antérieur : l'absence vient de PANO2026-027 ; le point est sur la bande enherbée.",
    "arbre_027": "un petit arbre est visible en 2022 au point levé ; absent sur les trois photos 2026 calées (revue et relecture) : "
                 "abattu après 2022.",
    "MF-6013": "la flèche glisse de 0,33 m vers sa droite et reste entre K-0627 et ML-5297 ; le marquage visible en 2022 est "
               "l'ancien (non probant pour une flèche neuve 2025).",
    "ML-0121": "le « trait » suit exactement l'arête du toit du bâtiment : artefact de détection, retrait justifié.",
    "lamp_12668620636": "le point après est au centre de la jardinière ronde où part l'ombre du mât ; le point avant (OSM) est dans "
                        "les places de stationnement.",
    "ML-0113": "la marque est arrêtée à l'arête de K-0233 (1,24 m non peints, en rouge) ; elle court dans l'ombre portée du "
               "bâtiment : son existence n'est pas jugée ici.",
    "lamp_12668578865": "le point après est sur le disque clair de la lanterne d'où part l'ombre fine vers le NNO ; le point avant "
                        "tombe sur une voiture garée.",
    "arbre_396": "déplacement de 1,6 m sous la couronne : la position du tronc n'est pas lisible sur l'ortho ; sens jugé juste "
                 "par la revue v1 (ampleur minimale).",
    "MF-0769": "recentrage de 0,19 m dans la voie bornée par K-0402 et ML-0799, empreinte entièrement sur la chaussée.",
    "lamp_9514795519": "objet déduit 2026 : le fond 2022 (avant travaux) ne le montre pas ; sortie de 1,2 m de la bande cyclable "
                       "décrite, confiance faible, à vérifier sur place.",
    "lamp_9514825221": "le point après est au pied SSE de l'unique ombre de mât, contre les images claires de la lanterne et du "
                       "boîtier caméra ; le point avant est 1,2 m plus au NNO sur l'ombre.",
    "pan_J5_1": "le point après est sur le nez du TPC (contour jaune), 0,93 m plus loin que le point avant.",
}

# lecture des planches avant / après de la résolution r2 (agent RÉSOLUTION, 11/10/2026), par entité ; remplie après
# avoir regardé chaque planche (REPORT : « Lecture des planches »)
LECTURE_PLANCHES_R2 = {
    "ML-8000": "le trait retiré (rouge) part du nez de l'îlot, traverse la flèche de tourne-à-gauche peinte en 2022 puis court "
               "au milieu de la voie, entre ML-5402 / ML-0408 (vert, côté îlot) et ML-5228 (vert, tirets visibles en 2022) ; "
               "aucune peinture sur son tracé : il couperait une voie de 3,3 m en deux : retrait justifié.",
    "MF-8000": "le contour rouge est posé sur l'ancienne flèche TD_TAD peinte en 2022 ; la bordure 2026 K-0415 (jaune) la "
               "coupe dans sa longueur, sa moitié droite est hors de la chaussée 2026 : la flèche ne peut pas exister telle que "
               "décrite ; le levé GAM 2026 n'en montre aucune : retrait justifié.",
    "lamp_9514828517": "ortho 2022 : l'ombre fine du mât (vers le NNO) part de C (cyan), pas de A (rouge, 0,7 m à l'ouest) ; "
                       "f8d91bb1 (4,5 m) et ded07efa (7,8 m), 2026 : l'axe C suit le mât jusqu'à la lanterne, l'axe A tombe "
                       "sur la palissade et le ciel : position F reprise à juste titre (groupe B6a1 / C13a).",
    "feu_NE_TPC": "e5d79de9 (5,9 m) et 5c0d1d39 (7,9 m) : l'axe C (cyan) est sur le fût du support, l'axe A (rouge) à côté, à "
                  "gauche, sans fût ; sur l'ortho l'ombre du support part de C : déplacement de 0,19 m cohérent.",
    "arbre_027": "2022 : pelouse au point levé ; ded07efa (11,2 m) et f8d91bb1 (12,4 m), 2026 : l'axe projeté tombe sur une "
                 "voiture garée puis sur la façade, sans tronc ni houppier ; la traînée grise verticale voisine est une "
                 "salissure de l'objectif (même colonne de l'image, côté gauche, sur les 3 photos, vérifié sur les images "
                 "brutes) : absence confirmée.",
    "MF-6020": "la flèche recentrée (cyan) est à mi-distance de ML-0785 (au NO) et de la ligne au SE (≈ 1,45 m et 1,54 m mesurés "
               "sur la planche agrandie), l'ancienne (rouge) était plus près de la ligne SE ; flèche neuve 2025 : le fond 2022 "
               "montre l'ancien marquage.",
    "pan_AB4_2": "ded07efa (18,8 m) et f8d91bb1 (19,9 m), 2026 : le poteau du STOP est sur C, A tombe dans le vide à sa droite ; "
                 "l'écart de 0,12 m signalé par la revue (poussée par la règle, R8) n'est pas lisible à cette échelle (listé).",
    "feu_REV_droite": "0,17 m : sur 5c0d1d39 (15,9 m) et e5d79de9 (20,1 m) les deux axes touchent le fût, C au centre, A sur son "
                      "bord gauche : écart sous ce que ces vues séparent ; appliqué comme triangulation en accord Q1, sans plus.",
    "pan_AB3a_3": "ded07efa (14,3 m) et f8d91bb1 (15,2 m), 2026 : le triangle AB3a et son poteau sont sur C, dans le refuge 2026 "
                  "(contour jaune) ; A tombe sur le poteau du STOP voisin (pan_AB4_2), sans triangle : déplacement de 4,15 m "
                  "confirmé.",
    "pan_C113_1": "9834f494 (caméra au 64°) voit la face bleue de face : la face est vers le NE, 225° est faux ; mais e5d79de9 "
                  "(caméra au 167°) voit aussi la face, de biais : à 65° elle y serait de dos ; azimut fin probablement ≈ 95° "
                  "(77-109°), listé à mesurer sur place.",
}
