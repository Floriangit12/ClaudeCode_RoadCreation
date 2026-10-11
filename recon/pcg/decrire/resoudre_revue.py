"""Verdicts des revues adverses utilisés par la résolution (données, aucune logique).

Sources :
- revue adverse de la cohérence v2 (11/10/2026, agent REVUE, 35 éléments relus ; preuves dans
  scratchpad/v2_tmp/revue_adverse_coherence_v2/) : texte transmis par l'orchestrateur du flux, recopié ici
  sans interprétation (verdict, objet, motif court, fichiers de preuve) ;
- revue adverse de la cohérence v1 (tâche wdbpt58qa, result.revue.verdicts) : seulement les verdicts qui
  portent encore sur une décision v2 (arbre_396) ;
- seconde lecture faite par l'agent RÉSOLUTION (11/10/2026) sur les vignettes de la revue v2
  (arb1_all.jpg, l717k_all.jpg) : sert de double lecture (P16) pour les absences et les rejets.

Chaque entrée : verdict ∈ {juste, faux, incertain} ; portee ∈ {position, azimut, existence, conforme, fleche,
non_instanciation} ; groupe : identifiants couverts par le même verdict (membres d'un même support).
"""

REVUE_V2_ID = "revue_adverse_coherence_v2"
REVUE_V2_DOSSIER = "scratchpad/v2_tmp/revue_adverse_coherence_v2"
REVUE_V1_ID = "revue_adverse_coherence_v1"
RELECTURE_ID = "seconde_lecture_resolution"

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
]


def index_revue_v2():
    """{objet: entrée} pour tous les identifiants couverts (groupes compris)."""
    out = {}
    for e in REVUE_V2:
        for i in e.get("groupe", [e["objet"]]):
            out[i] = e
    return out


def index_revue_v1():
    return {e["objet"]: e for e in REVUE_V1}


def index_relecture():
    return {e["objet"]: e for e in RELECTURE}

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
