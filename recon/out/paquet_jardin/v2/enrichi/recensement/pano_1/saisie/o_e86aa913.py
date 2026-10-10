import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "e86aa913"; S = "pnx:" + camera.photo(I).id; D = "2024-08-24T15:10"
S119 = "pnx:" + camera.photo("119d9094").id
L = []
L.append(obs(S, D, "candelabre", "mat_a_double_crosse",
              dict(position_triangulee=[15.95, 24.09], ecart_original_m=0.68, ecart_correction_coherence_m=0.51,
                   triangulation="e86aa913 v1 (507,700) à 2,1 m + 119d9094 P3 t4 (188,200) et P5 t3 (180,250) : (15,94 ; 24,09) et (15,96 ; 24,09), angle ≈ 60°",
                   controle_ortho_2022="pied de l'ombre du mât et deux lanternes vues de dessus de part et d'autre du point triangulé",
                   crosses="double : grande crosse ≈ 1,9 m vers la chaussée (SE), petite ≈ 0,8 m vers la piste (NO), lanterne basse côté piste",
                   plaque_identification="plaque bleue, chiffres blancs verticaux « 2349 »", couleur_mat="gris anthracite patiné",
                   remarque="le déplacement du solveur (0,65 m perpendiculaire, derrière la bordure) n'est que partiellement juste : le fût est 0,68 m à l'OUEST de la position d'origine"),
              (15.95, 24.09, 0.27), 0.12, "triangulation", "lamp_9665416817", "position_corrigee", "haute",
              pv("e86aa913_v1.jpg", pixels=[507, 700], note="fût à 2,1 m ; plaque 2349 visible dans e86aa913_P1 tuile 7"),
              etat_entite=etat("lamp_9665416817")))
L.append(obs(S, D, "panneau", "J5",
              dict(face="rectangle bleu, flèche blanche oblique vers le bas à droite (contournement par la droite)",
                   dimensions_m=[0.64, 0.80], bas_du_panneau_m=0.0, support="deux pieds noirs bas", orientation="face au NE (trafic Verdun NE -> SO)",
                   correction_coherence="position corrigée (0,5 m vers la pointe) confirmée : support à 0,11 m de la position corrigée"),
              pos("pan_J5_1"), 0.15, "projection_description", "pan_J5_1", "confirme", "haute",
              pv("e86aa913_P1.jpg", bbox=[65, 140, 165, 265], tuile=0), etat_entite=etat("pan_J5_1")))
L.append(obs(S, D, "panneau", "C113",
              dict(face="carré bleu, vélo blanc (C113)", orientation="face au NE", hauteur_centre_m=2.0, ecart_m=0.09),
              pos("pan_C113_1"), 0.15, "projection_description", "pan_C113_1", "confirme", "haute",
              pv("e86aa913_P1.jpg", pixels=[987, 85], tuile=2), etat_entite=etat("pan_C113_1")))
L.append(obs(S, D, "feu", "support_feux",
              dict(ecart_m=0.12, tetes="R11v 3 feux en tête (centre ≈ 3,0 m), module répétiteur plus bas, fourreau jaune au pied ; C113 voisin à droite"),
              pos("feu_NE_droite"), 0.15, "projection_description", "feu_NE_droite", "confirme", "haute",
              pv("e86aa913_P1.jpg", pixels=[592, 600], tuile=4), etat_entite=etat("feu_NE_droite")))
L.append(obs(S, D, "candelabre", "mat_a_double_crosse",
              dict(remarque="3e vue (43 m) : fût sur la projection, deux crosses opposées perpendiculaires à Verdun, motif lumineux en treillis"),
              pos("lamp_9514795520"), 0.4, "projection_description", "lamp_9514795520", "confirme", "moyenne",
              pv("e86aa913_P1.jpg", pixels=[1000, 1000], tuile=8), etat_entite=etat("lamp_9514795520")))
L.append(obs(S119, "2025-05-18T13:37", "arbre", "feuillu_pourpre",
              dict(feuillage="pourpre sombre (confirmé en mai 2025)", essence="Prunus cerasifera 'Pissardii' probable (houppier arrondi, petites feuilles) ; Fagus 'Purpurea' non exclu",
                   hauteur_estimee_m=11),
              pos("arbre_273"), 1.0, "projection_description", "arbre_273", "confirme", "moyenne",
              pv("119d9094_v1.jpg", bbox=[850, 240, 1000, 430]), etat_entite=etat("arbre_273")))
L.append(obs(S, D, "bordure", "rive_verdun_NE",
              dict(observation="l'arête projetée de K-0354 suit le bord de chaussée visible (écart ≤ 5 px à 5-20 m, soit ≤ 3 cm) ; bordure quasi arasée côté accotement enherbé, ligne de rive blanche continue",
                   profil_description="A2/P1 vue 0,03 m : cohérent (pas de vue de bordure perceptible)"),
              (24.0, 31.0, 0.3), 0.1, "projection_description", "K-0354", "confirme", "haute",
              pv("e86aa913_v3.jpg", bbox=[300, 420, 700, 900]), etat_entite="existant"))
L.append(obs(S, D, "autre", "poteau_bois",
              dict(observation="poteau bois sombre ≈ 10 m exactement sur la projection (pied et sommet)", hauteur_estimee_m=10),
              pos("poteau_bois_NE"), 0.3, "projection_description", "poteau_bois_NE", "confirme", "haute",
              pv("e86aa913_v2.jpg", pixels=[912, 300]), etat_entite=etat("poteau_bois_NE")))
L.append(obs(S, D, "autre", "base_vie_chantier",
              dict(observation="modules préfabriqués blancs (base vie) et clôtures de chantier au SE de Verdun NE (août 2024) : chantier des Saules Blancs, temporaire"),
              None, None, None, None, "incertain", "haute",
              pv("e86aa913_v3.jpg", bbox=[930, 380, 1045, 425]),
              valide=(False, "installation de chantier temporaire (2024), absente en mai 2025 (eeb2f8f1)")))
XY = {"MF-5042": (15.1, 15.7, 0.15), "MF-5043": (12.8, 18.4, 0.15)}
for fid, txt, px in (("MF-5042", "flèche TD+TAG blanche au centre de la voie de gauche de l'approche Verdun NE : contour projeté superposé au marquage (écart < 0,1 m) ; usure moyenne (2024)", [415, 312]),
                     ("MF-5043", "flèche TD+TAD au centre de la voie de droite : contour projeté superposé au marquage (écart < 0,15 m) ; usure moyenne", [790, 355])):
    L.append(obs(S, D, "marquage", "fleche_directionnelle",
                  dict(observation=txt, centrage="centrée dans la voie (règle « flèche au milieu de la voie » respectée)"),
                  XY[fid], 0.15, "projection_description", fid, "confirme", "haute",
                  pv("e86aa913_fleches_v0.jpg", pixels=px), etat_entite="conserve"))
L.append(obs(S, D, "ilot", "terre_plein_central_nez",
              dict(observation="nez arrondi du TPC NE (K-0386, T2 vue ≈ 0,14 m) et balise J5 sur la projection ; bordure béton gris clair"),
              (12.0, 10.0, 0.1), 0.2, "projection_description", "K-0386", "confirme", "haute",
              pv("e86aa913_fleches_v0.jpg", bbox=[60, 260, 330, 360]), etat_entite="existant"))
n = T.ajouter(I, *L); print("ajoutées", n)
