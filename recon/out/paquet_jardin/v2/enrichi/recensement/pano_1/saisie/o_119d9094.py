import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat

D = "2025-05-18T13:37"
import camera  # noqa
S = "pnx:" + camera.photo("119d9094").id
L = []
L.append(obs(S, D, "candelabre", "mat_a_double_crosse",
              dict(nb_crosses=2, nb_lanternes=2, orientation_crosses="perpendiculaires à Verdun (vers SSE et NNO)",
                   hauteur_estimee_m=10.5, couleur_mat="gris galvanisé", lanterne="type routier (vasque plate)",
                   accessoire="motif lumineux de Noël en treillis fixé à mi-hauteur (encore en place le 18/05/2025 ; saisonnier)",
                   ecart_position_m=0.2),
              pos("lamp_9514795520"), 0.25, "projection_description", "lamp_9514795520", "confirme", "haute",
              pv("119d9094_z_lamp_9514795520_v0.jpg", pixels=[458, 400], note="fût ; lanternes en (365,178) et (548,203)"),
              etat_entite=etat("lamp_9514795520")))
L.append(obs(S, D, "feu", "support_feux_ilot",
              dict(couleur_mat="noir/anthracite", tete_haute="R11v (3 feux) en tête de mât", ecart_lateral_m=-0.12,
                   correction_coherence="déplacement de 0,35 m proposé par le solveur : rejeté (le fût est à 0,12 m de la position d'origine, du côté opposé)"),
              pos("feu_VERC_ilot"), 0.15, "projection_description", "feu_VERC_ilot", "confirme", "haute",
              pv("119d9094_P1.jpg", pixels=[592, 300], tuile=1), etat_entite=etat("feu_VERC_ilot")))
L.append(obs(S, D, "ilot", "remplissage",
              dict(materiau_observe="cailloux concassés / galets gris-beige grossiers", granulometrie_estimee_mm=[40, 80],
                   description_actuelle="gravier_concasse_6_10 (granulométrie 10-20)", bordure="béton clair, nez arrondi",
                   remarque="état avant travaux ; îlot refait en 2025 avec remplissage « reconduit » (description)"),
              (8.0, -18.5, -0.2), 1.0, "projection_description", "I-0390", "attribut_corrige", "moyenne",
              pv("119d9094_P2.jpg", pixels=[200, 1060], tuile=6),
              valide=("incertain", "îlot reconstruit en 2025 : remplissage reconduit selon la description, non observé après travaux")))
L.append(obs(S, D, "candelabre", "mat_droit_lanterne_en_tete",
              dict(hauteur_estimee_m=10.0, couleur_mat="gris clair", lanterne="tête plate en sommet de mât (LED)", crosse=False),
              pos("lamp_12882680524"), 0.3, "projection_description", "lamp_12882680524", "confirme", "haute",
              pv("119d9094_P1.jpg", pixels=[997, 200], tuile=2), etat_entite=etat("lamp_12882680524")))
L.append(obs(S, D, "candelabre", "poteau_bois",
              dict(materiau="bois (brun)", hauteur_estimee_m=8.8, crosse_visible=False, lanterne_visible=False,
                   hypothese="poteau bois sans luminaire (confirmé par eeb2f8f1 ; lanterne visible seulement sur l'ortho 2022)"),
              pos("lamp_lidar_VERC_E"), 0.4, "projection_description", "lamp_lidar_VERC_E", "attribut_corrige", "moyenne",
              pv("119d9094_P1.jpg", pixels=[205, 590], tuile=3), etat_entite=etat("lamp_lidar_VERC_E")))
L.append(obs(S, D, "mobilier", "armoire_feux",
              dict(couleur="gris clair (tôle)", hauteur_estimee_m=1.87, largeur_estimee_m=1.1, hauteur_description_m=1.5),
              pos("armoire_feux_VERC"), 0.4, "projection_description", "armoire_feux_VERC", "attribut_corrige", "moyenne",
              pv("119d9094_P1.jpg", bbox=[530, 485, 645, 660], tuile=4), etat_entite=etat("armoire_feux_VERC")))
L.append(obs(S, D, "panneau", "B6a1",
              dict(remarque="à 58 m : aucun panneau lisible à la position ; objet blanc (boîtier ou dos de panneau) à ≈ 0,8 m à gauche, clôture grillagée"),
              pos("pan_B6a1_3"), 1.5, "projection_description", "pan_B6a1_3", "incertain", "faible",
              pv("119d9094_P1.jpg", pixels=[1000, 600], tuile=5), etat_entite=etat("pan_B6a1_3")))
for pid, xy, px in (("potelet_REV_NE_1", (-3.08, 16.57, 0.03), [215, 1078]), ("potelet_REV_NE_2", (-5.15, 18.81, 0.07), [625, 1075])):
    L.append(obs(S, D, "potelet", "potelet_cylindrique",
                  dict(hauteur_visible_m=0.74, hauteur_description_m=1.0, diametre_m=0.10, couleur="gris anthracite, bague claire en tête",
                       ecart_position_m=0.11 if pid.endswith("1") else 0.17),
                  xy, 0.15, "rayon_sol", pid, "attribut_corrige", "haute",
                  pv("119d9094_P1.jpg", pixels=px, tuile=6 if pid.endswith("1") else 7), etat_entite=etat(pid)))
L.append(obs(S, D, "autre", "poteau_reseau_bois",
              dict(materiau="bois", ecart_lateral_m=-0.57, remarque="fût vu 0,57 m à gauche de la projection (pied masqué par la haie) : à trianguler"),
              (-17.85, 9.79, 0.06), 0.6, "projection_description", "poteau_reseau_12888048898", "incertain", "faible",
              pv("119d9094_P1.jpg", pixels=[985, 1000], tuile=8), etat_entite=etat("poteau_reseau_12888048898")))
L.append(obs(S, D, "panneau", "D21_double",
              dict(panneaux=["D21 flèche blanche « LA REVIRÉE / Collège L. Terray » pointée vers la Revirée",
                             "plaque blanche « Commerces de LA REVIRÉE »"],
                   support="un seul poteau gris pour les deux panneaux (pan_D21_1 et pan_D21_2 = même support)",
                   ecart_m=0.6, triangulation="119d9094 P5 t1 (47,200) + 2ab4efbc P2 t1 (158,250), angle 58° ; rayon au sol du pied (119d9094) : (-4,04 ; 6,06)", chantier="chevalet de signalisation temporaire avec fanions orange au pied (mai 2025)"),
              (-4.19, 6.33, 0.08), 0.3, "triangulation", "pan_D21_1", "position_corrigee", "moyenne",
              pv("119d9094_P1.jpg", pixels=[147, 318], tuile=0),
              valide=(False, "état du 18/05/2025 ; emplacement repris par la traversée cyclable posée en 2025 (MP-0001) : dépose probable")))
L.append(obs(S, D, "marquage", "effet_feux",
              dict(observation="aucune ligne d'effet des feux sur l'approche Verdun NE le 18/05/2025 (zébra, flèches et axe visibles)",
                   correction="etat 'conserve' -> 'neuf_2025', usure 0 (ligne ajoutée par le plan projet 2025) ; doublon dans la description régénérée : MT-8002 (ligne d'arrêt virtuelle non peinte, neuf_2025) au même endroit"),
              (10.9, 13.5, 0.1), 0.2, "projection_description", "MT-0563", "attribut_corrige", "haute",
              pv("119d9094_MT0563_v0.jpg", pixels=[700, 465]),
              valide=(True, "la correction porte sur l'état 2026 : ligne absente avant travaux donc peinte en 2025")))
L.append(obs(S, D, "marquage", "traversee_cyclable",
              dict(fond="résine verte", carres="blancs", etat_05_2025="usure moyenne", position_observee="centrée vers (-4,3 ; 10,3) (ancienne traversée de la Revirée)",
                   description_regeneree="MP-0272 (verte, conservée) a disparu ; MP-0001 (jaune Chronovélo, neuf 2025, plan 2025) est centrée vers (-3,4 ; 6,9), soit ≈ 3,5 m plus près du centre, sur l'îlot des D21",
                   remarque="le plan 2025 « conserve » la traversée en la bordant de carrés orange (hist-13) : décalage de 3,5 m et effacement de la résine verte à confirmer"),
              (-4.3, 10.3, 0.0), 0.3, "projection_description", "MP-0001", "incertain", "moyenne",
              pv("119d9094_P2.jpg", pixels=[230, 750], tuile=3),
              valide=("incertain", "image du 18/05/2025 ; traversée redessinée/recolorée par le projet 2025")))
L.append(obs(S, D, "ilot", "terre_plein_central",
              dict(dessus="enrobé sombre avec herbes dans les joints", bordure="béton gris clair chanfreiné, vue ≈ 0,14 m, nez arrondi",
                   objets=["feu_NE_TPC (mât gris, tête 3 feux + module)", "balise J5 au nez : dos gris foncé ≈ 0,8 × 0,9 m sur deux pieds blancs"]),
              (12.0, 10.0, 0.1), 0.5, "projection_description", "I-0386", "confirme", "haute",
              pv("119d9094_P2.jpg", pixels=[600, 300], tuile=1), etat_entite="existant"))
L.append(obs(S, D, "feu", "support_feux",
              dict(ecart_m=0.12, tetes_visibles="3 feux en tête + module inférieur (vus de dos)"),
              pos("feu_NE_TPC"), 0.15, "projection_description", "feu_NE_TPC", "confirme", "haute",
              pv("119d9094_P3.jpg", pixels=[1008, 1000], tuile=7), etat_entite=etat("feu_NE_TPC")))
L.append(obs(S, D, "feu", "support_feux",
              dict(fourreau="manchon jaune au pied (confirmé)", tetes="R11v + répétiteur + module, vus de dos"),
              pos("feu_NE_droite"), 0.15, "projection_description", "feu_NE_droite", "confirme", "haute",
              pv("119d9094_MT0563_v0.jpg", pixels=[292, 300]), etat_entite=etat("feu_NE_droite")))
L.append(obs(S, D, "candelabre", "mat_a_crosse_double_niveau",
              dict(couleur_mat="brun-rouille (bois ou acier patiné)", crosse_haute="vers la chaussée (E)",
                   lanterne_basse="petite lanterne côté piste, ≈ 6 m", accessoire="bannière publicitaire verticale orange/blanc (temporaire)",
                   correction_coherence="le fût n'est ni à la position d'origine ni à la position corrigée par le solveur : triangulé en (15,95 ; 24,09) (e86aa913 + 119d9094 + eeb2f8f1), 0,68 m à l'ouest de l'origine et 0,51 m de la correction"),
              (15.95, 24.09, 0.27), 0.12, "triangulation", "lamp_9665416817", "position_corrigee", "haute",
              pv("119d9094_P3.jpg", pixels=[588, 600], tuile=4), etat_entite=etat("lamp_9665416817")))
for pid, h, hd in (("pan_C114_1", 3.35, 2.7), ("pan_AB3a_1", 2.75, 2.15), ("pan_M9_1", 2.35, 1.8)):
    L.append(obs(S, D, "panneau", pid.split("_")[1],
                  dict(hauteur_centre_estimee_m=h, hauteur_description_m=hd,
                       pile="C114 (rectangle bleu, barre rouge) au-dessus d'AB3a (triangle) et du panonceau M9 (blanc), sur le mât de lamp_12894130974",
                       ecart_position_m=0.06),
                  pos(pid), 0.15, "projection_description", pid, "attribut_corrige", "moyenne",
                  pv("119d9094_P3.jpg", pixels=[1005, 460], tuile=5), etat_entite=etat(pid)))
L.append(obs(S, D, "candelabre", "mat_a_crosse",
              dict(hauteur_estimee_m=9.3, crosse="simple, lanterne côté carrefour", couleur_mat="gris",
                   accessoire="bannière publicitaire orange/blanc"),
              pos("lamp_9514830019"), 0.3, "projection_description", "lamp_9514830019", "confirme", "haute",
              pv("119d9094_P3.jpg", pixels=[1003, 960], tuile=8), etat_entite=etat("lamp_9514830019")))
L.append(obs(S, D, "surface", "chaussee_fissuree",
              dict(etat="faïençage et fissures longitudinales pontées au bitume (réseau dense), reprises d'enrobé rectangulaires",
                   zone="approche et sortie Verdun NE au droit du zébra MP-0574"),
              (3.19, 7.42, 0.01), 2.0, "rayon_sol", None, "absent_de_description", "haute",
              pv("119d9094_P2.jpg", pixels=[600, 560], tuile=4),
              valide=("incertain", "chaussée du cœur dans l'emprise des travaux 2025 (resurfaçage possible) ; branche NE hors emprise probablement inchangée")))
L.append(obs(S, D, "tampon", "regard_rond",
              dict(diametre_m=0.6, materiau="fonte"),
              (1.14, 9.92, -0.02), 0.3, "rayon_sol", None, "absent_de_description", "moyenne",
              pv("119d9094_v3_brut.jpg", pixels=[408, 588]),
              valide=("incertain", "dans l'emprise des travaux 2025 : tampon probablement conservé (remis à niveau)")))
L.append(obs(S, D, "bev", "bande_eveil_vigilance",
              dict(observation="aucune bande d'éveil de vigilance au droit de l'abaissé K-0348 le 18/05/2025"),
              (0.5, 9.0, 0.0), 0.5, "projection_description", "BEV-0348-2", "absent_sur_image", "moyenne",
              pv("119d9094_MT0563_v0.jpg", bbox=[215, 525, 330, 575]),
              valide=("incertain", "BEV peut avoir été posée en 2025 (OSM tactile_paving) : l'absence en mai 2025 ne la réfute pas")))
L.append(obs(S, D, "haie", "haie_taillee_angle_N",
              dict(essence_probable="persistant à grandes feuilles (laurier-cerine / photinia), taillée en mur",
                   hauteur_estimee_m=[2.4, 3.1], epaisseur_estimee_m=1.5,
                   trace_local=[[-2.57, 27.62], [0.28, 26.84], [1.05, 27.08], [5.9, 28.98]],
                   importance="masque la visibilité à l'angle Revirée / Verdun NE (piste cyclable) : à modéliser (famille haies absente de la description)"),
              (0.28, 26.84, -0.14), 0.4, "rayon_sol", "S-0094", "absent_de_description", "haute",
              pv("119d9094_v3_brut.jpg", bbox=[0, 380, 360, 478], note="pieds de haie aussi en v1 (1000,470) et (1150,480)"),
              valide=(True, "hors emprise des travaux 2025 ; haie persistante (taille d'entretien possible)")))
L.append(obs(S, D, "haie", "haie_taillee_parking_Reviree",
              dict(hauteur_estimee_m=[1.4, 1.7], position="bord du parking à l'ouest de la Revirée (au pied du grand cèdre)", essence_probable="persistant taillé"),
              (-25.67, 13.7, -0.14), 0.8, "rayon_sol", "surf_0161", "absent_de_description", "moyenne",
              pv("119d9094_v1_brut.jpg", bbox=[0, 410, 200, 480]),
              valide=(True, "hors emprise des travaux 2025")))
L.append(obs(S, D, "autre", "poteau_bois_reseau",
              dict(observation="à la position de lamp_lidar_SW_NO (mât « type non identifié », LiDAR 2021) : poteau BOIS avec câble aérien, sommet nu, dans la haie NO (projection exacte, écart latéral 0,0 m à 34 m)",
                   type_propose="poteau_reseau bois h ≈ 8 m (pas un lampadaire)",
                   doublon_probable="poteau_reseau_12888056356 (OSM) à 3,8 m, vu à 0,7 m du même poteau depuis 119d9094 : très probablement le même poteau (2ab4efbc : visées trop parallèles pour trianguler)"),
              pos("lamp_lidar_SW_NO"), 0.5, "projection_description", "lamp_lidar_SW_NO", "attribut_corrige", "moyenne",
              pv("119d9094_P6.jpg", pixels=[600, 200], tuile=1), etat_entite=etat("lamp_lidar_SW_NO")))
for aid, h, px, t in (("arbre_242", 13.1, [200, 520], 3), ("arbre_243", 11.8, [200, 520], 4)):
    L.append(obs(S, D, "arbre", "conifere_cedre",
                  dict(type_description="feuillu", type_observe="conifère : cèdre à rameaux retombants (Cedrus deodara probable), aiguilles bleu-vert, port pleureur",
                       hauteur_description_m=h, remarque="même alignement de cèdres que arbre_244 (Cedrus, 27 m) le long de la Revirée ; asset conifère à utiliser"),
                  pos(aid), 1.0, "projection_description", aid, "attribut_corrige", "moyenne",
                  pv("119d9094_A1.jpg", pixels=px, tuile=t), etat_entite=etat(aid)))
L.append(obs(S, D, "arbre", "non_retrouve",
              dict(observation="aux positions d'arbre_229 et arbre_230 (GAM, h 6 m par défaut, couronne 0) : aucun tronc distinct au-dessus de la haie ; le poteau bois poteau_reseau_12888048898 et la couronne d'un conifère plus lointain se trouvent dans la même visée",
                   proposition="vérifier sur place (jeunes sujets plantés après mai 2025 ou arbustes de la haie)"),
              pos("arbre_230"), 1.0, "projection_description", "arbre_230", "incertain", "faible",
              pv("119d9094_A1.jpg", pixels=[600, 200], tuile=1), etat_entite=etat("arbre_230")))
L.append(obs(S, D, "arbre", "arbuste_dans_haie",
              dict(observation="à la position d'arbre_260 (h 2,6) : haie taillée continue (≈ 2,5 m), pas d'arbre isolé : à traiter comme partie de la haie"),
              pos("arbre_260"), 0.5, "projection_description", "arbre_260", "attribut_corrige", "moyenne",
              pv("119d9094_A1.jpg", pixels=[1000, 600], tuile=5), etat_entite=etat("arbre_260")))
L.append(obs(S, D, "potelet", "rangee_potelets",
              dict(observation="seulement 2 potelets sur le trottoir de l'angle N (Revirée / Verdun NE), aux positions décrites ; le 3e poteau gris de la rangée est le support feu_REV_E_pietons (têtes piétons à 1,8-2,1 m)"),
              pos("potelet_REV_NE_1"), 0.2, "projection_description", "potelet_REV_NE_1", "confirme", "haute",
              pv("119d9094_z_potelets_v0.jpg", pixels=[580, 535]), etat_entite=etat("potelet_REV_NE_1")))
L.append(obs(S, D, "marquage", "traversee_cyclable_verte",
              dict(observation="mesure au sol de la résine verte (mai 2025) : centre ≈ (-3,4 ; 10,1), bande ≈ (-5,3 ; 11,6) -> (-2,3 ; 10,9) ; MP-0001 (jaune 2025) décrite 3,2 m plus au SE (-3,4 ; 6,9)",
                   zebra_mai_2025="bandes du zébra de la Revirée vers (-2,8 ; 13,6)"),
              (-3.43, 10.12, -0.04), 0.15, "rayon_sol", "MP-0001", "incertain", "haute",
              pv("119d9094_z_potelets_v0.jpg", pixels=[450, 720]),
              valide=(False, "état avant travaux : traversée recolorée/redessinée en 2025")))
n = T.ajouter("119d9094", *L)
print("ajoutées", n)
