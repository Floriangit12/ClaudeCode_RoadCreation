import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "e27153f2"; S = "pnx:" + camera.photo(I).id; D = "2025-05-18T13:38"
L = []
L.append(obs(S, D, "candelabre", "mat_a_double_crosse",
              dict(crosses=2, lanternes=2, couleur_mat="brun-rouge (acier peint/patiné)", hauteur_estimee_m=12.1,
                   accessoire="câbles transversaux fixés aux 2/3 du mât (support de guirlandes au-dessus de la chaussée)",
                   implantation="terre-plein central de Verdun SO"),
              pos("lamp_9514795518"), 0.4, "projection_description", "lamp_9514795518", "confirme", "haute",
              pv("e27153f2_P1.jpg", pixels=[200, 200], tuile=0), etat_entite=etat("lamp_9514795518")))
L.append(obs(S, D, "candelabre", "mat_a_double_crosse",
              dict(hauteur_estimee_m=12.4, accessoire="motif lumineux en treillis + câble transversal vers le côté opposé (guirlande)",
                   implantation="TPC Verdun SO"),
              pos("lamp_9514795121"), 0.3, "projection_description", "lamp_9514795121", "confirme", "haute",
              pv("e27153f2_P1.jpg", pixels=[985, 230], tuile=2), etat_entite=etat("lamp_9514795121")))
L.append(obs(S, D, "autre", "cables_transversaux",
              dict(description="2 à 3 câbles tendus entre les candélabres du TPC et les rives (≈ 7-8 m de haut), supports de décorations de fin d'année",
                   portee_m="≈ 15-20", remarque="absents de la description ; visibles dans les vues vers Grenoble"),
              pos("lamp_9514795518"), 2.0, "projection_description", None, "absent_de_description", "moyenne",
              pv("e27153f2_v0.jpg", bbox=[310, 0, 545, 210]),
              valide=("incertain", "équipement saisonnier possible ; aucune image après mai 2025")))
L.append(obs(S, D, "panneau", "D21",
              dict(lecture="flèche blanche vers la droite : « Hôtel de Ville / Maison de la musique / Ponte-Gendarmerie » (bandeau supérieur partiellement lisible « … P+R … »)",
                   ecart_lateral_m=-1.33, rayon_sol=[-69.24, -84.38], ecart_m=1.9),
              (-69.24, -84.38, -0.45), 0.5, "rayon_sol", "pan_D21_3", "position_corrigee", "moyenne",
              pv("e27153f2_P1.jpg", pixels=[870, 745], tuile=5),
              valide=("incertain", "abords de l'entrée du P+R déplacée en 2025 : panneau peut-être déplacé")))
L.append(obs(S, D, "panneau", "B2a+AB4",
              dict(observation="poteau à panneau vu par la tranche à 1,6 m à gauche de la projection ; rien à la position décrite",
                   rayon_sol=[-68.73, -87.18]),
              (-68.73, -87.18, -0.55), 0.6, "rayon_sol", "pan_B2a_2", "position_corrigee", "faible",
              pv("e27153f2_P1.jpg", pixels=[460, 720], tuile=4),
              valide=("incertain", "sortie du P+R modifiée en 2025")))
L.append(obs(S, D, "arbre", "absent",
              dict(observation="aucun arbre à la position le 18/05/2025 (arbustes bas et poteau de panneau) : abattu avant les travaux"),
              pos("arbre_144"), 0.5, "projection_description", "arbre_144", "absent_sur_image", "haute",
              pv("e27153f2_P1.jpg", pixels=[1000, 1100], tuile=8), etat_entite="absent 2026"))
L.append(obs(S, D, "batiment", "serres_jardinerie",
              dict(description="serres vitrées à toitures en dents de scie (jardinerie Paquet Jardin) au NO de Verdun SO, visibles derrière la haie"),
              (-95.0, -70.0, 0.0), 10.0, "projection_description", None, "incertain", "moyenne",
              pv("e27153f2_P1.jpg", bbox=[500, 880, 600, 960], tuile=7),
              valide=(True, "bâti existant hors emprise des travaux")))
n = T.ajouter(I, *L); print("ajoutées", n)
