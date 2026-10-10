import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "eeb2f8f1"; S = "pnx:" + camera.photo(I).id; D = "2025-05-18T13:37"
L = []
L.append(obs(S, D, "candelabre", "mat_a_double_crosse",
              dict(remarque="3e photo (18,3 m) : le fût tombe exactement sur la position triangulée (15,95 ; 24,09)"),
              (15.95, 24.09, 0.27), 0.1, "triangulation", "lamp_9665416817", "position_corrigee", "haute",
              pv("eeb2f8f1_P1.jpg", pixels=[200, 200], tuile=0), etat_entite=etat("lamp_9665416817")))
L.append(obs(S, D, "candelabre", "poteau_bois_sans_luminaire",
              dict(observation="à la position : poteau BOIS brun ≈ 8-9 m, sommet nu (aucune crosse ni lanterne) vu sous deux angles (119d9094 à 25 m, az 112° ; eeb2f8f1 à 43 m, az 192°)",
                   ortho_2022="tête ronde claire + bras de ≈ 3,6 m vers le sud et longue ombre : lanterne à crosse longue en 2022",
                   interpretation="luminaire déposé entre 2022 et mai 2025 (ou bras démonté) : en 2026, poteau bois (réseau) sans éclairage",
                   type_propose="poteau_reseau (bois, h ≈ 8,5 m) ; ne pas instancier de lanterne",
                   voisin="le mât gris à tête plate visible 1,8 m à droite dans eeb2f8f1 est lamp_12882680524 (10 m plus loin)"),
              pos("lamp_lidar_VERC_E"), 0.3, "projection_description", "lamp_lidar_VERC_E", "attribut_corrige", "moyenne",
              pv("eeb2f8f1_P7.jpg", pixels=[300, 240], note="sommet du poteau ; 119d9094_P7.jpg (318,215) ; ortho_VERC_E.jpg (lanterne 2022)"),
              etat_entite=etat("lamp_lidar_VERC_E")))
L.append(obs(S, D, "autre", "poteau_bois",
              dict(materiau="bois", hauteur_estimee_m=10.4, remarque="position et hauteur confirmées"),
              pos("poteau_bois_NE"), 0.3, "projection_description", "poteau_bois_NE", "confirme", "haute",
              pv("eeb2f8f1_P1.jpg", pixels=[1000, 200], tuile=2), etat_entite=etat("poteau_bois_NE")))
L.append(obs(S, D, "candelabre", "mat_droit_lanterne_en_tete",
              dict(remarque="3e vue : mât fin gris à lanterne en tête sur la projection ; grand poteau bois ≈ 1,5 m plus à l'est"),
              pos("lamp_12882680524"), 0.3, "projection_description", "lamp_12882680524", "confirme", "haute",
              pv("eeb2f8f1_P1.jpg", pixels=[995, 600], tuile=5), etat_entite=etat("lamp_12882680524")))
L.append(obs(S, D, "marquage", "texte_50",
              dict(etat="anneau elliptique et chiffres « 50 » lisibles, usure moyenne (mai 2025)"),
              (21.25, 14.47, 0.1), 0.3, "projection_description", "MS-0598", "confirme", "moyenne",
              pv("eeb2f8f1_P1.jpg", pixels=[600, 1110], tuile=7), etat_entite=etat("MS-0598")))
L.append(obs(S, D, "panneau", "B21a1",
              dict(remarque="dos rond gris sur poteau bas à la projection (îlot I-0332), face vers le SO"),
              pos("pan_B21a1_1"), 0.3, "projection_description", "pan_B21a1_1", "confirme", "moyenne",
              pv("eeb2f8f1_P1.jpg", pixels=[1005, 985], tuile=8), etat_entite=etat("pan_B21a1_1")))
L.append(obs(S, D, "panneau", "pile_B2a_AB3a_M9c",
              dict(support="poteau gris : disque (centre ≈ 2,84 m), triangle AB3a (≈ 2,08 m), panonceau (≈ 1,47 m) ; dos gris vus du SO",
                   azimut_depuis_camera_deg=40.0,
                   remarque="le support B2b/B1 est un poteau DISTINCT, masqué derrière lamp_9665416717 depuis ce point de vue (voir 9fc8ba46 et 4407962b)",
                   hauteurs_description=dict(B2a=2.6, AB3a=2.0, M9=1.65)),
              None, None, None, "pan_AB3a_2", "attribut_corrige", "moyenne",
              pv("eeb2f8f1_P2.jpg", pixels=[665, 250], tuile=1), etat_entite=etat("pan_AB3a_2")))
L.append(obs(S, D, "candelabre", "mat_a_crosse",
              dict(crosse="simple vers la chaussée", accessoire="motif lumineux de Noël en treillis à mi-hauteur (mai 2025)", hauteur_estimee_m=10.3),
              pos("lamp_9665416717"), 0.3, "projection_description", "lamp_9665416717", "confirme", "haute",
              pv("eeb2f8f1_P2.jpg", pixels=[997, 200], tuile=2), etat_entite=etat("lamp_9665416717")))
L.append(obs(S, D, "arbre", "peuplier",
              dict(port="colonnaire/fastigié, très haut (> 20 m), en alignement", essence="Populus nigra (inventaire) cohérent"),
              pos("arbre_281"), 1.0, "projection_description", "arbre_281", "confirme", "moyenne",
              pv("eeb2f8f1_P2.jpg", pixels=[600, 600], tuile=4), etat_entite=etat("arbre_281")))
n = T.ajouter(I, *L); print("ajoutées", n)
