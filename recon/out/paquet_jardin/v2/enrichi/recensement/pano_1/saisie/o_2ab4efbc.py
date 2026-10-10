import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "2ab4efbc"; S = "pnx:" + camera.photo(I).id; D = "2024-08-24T15:10"
L = []
L.append(obs(S, D, "arbre", "conifere",
              dict(essence="Cedrus deodara probable (flèche retombante, rameaux pendants, port conique)", hauteur_estimee_m=29,
                   hauteur_description_m=27.0, remarque="sommet mesuré ≈ 28-31 m (pixel de cime) ; LiDAR 2021 27 m"),
              pos("arbre_244"), 0.5, "projection_description", "arbre_244", "attribut_corrige", "moyenne",
              pv("2ab4efbc_P1.jpg", pixels=[1000, 470], tuile=5), etat_entite=etat("arbre_244")))
L.append(obs(S, D, "autre", "poteau_bois",
              dict(materiau="bois", hauteur_estimee_m=8.3, hauteur_description_m=10.0,
                   remarque="position confirmée (pied sur la projection ; ombre de l'ortho 2022 issue de la position du paquet) ; bannière publicitaire orange « LANDRI » fixée (temporaire)"),
              pos("poteau_bois_REV_ilot"), 0.3, "projection_description", "poteau_bois_REV_ilot", "attribut_corrige", "moyenne",
              pv("2ab4efbc_P1.jpg", pixels=[610, 125], tuile=1), etat_entite=etat("poteau_bois_REV_ilot")))
L.append(obs(S, D, "feu", "support_feux",
              dict(remarque="fût vu à +0,45 m (2ab4efbc) et +0,13 m (119d9094) de la projection ; triangulation à 2 photos (-11,44 ; 8,65) à 0,48 m mais l'ombre de l'ortho 2022 part de la position du paquet : écart non significatif (pose 2024 σ ≈ 0,2 m)",
                   tetes_visibles="tête 3 feux en haut + modules (vus de 3/4 arrière)",
                   second_support="un second poteau gris avec boîtier (poussoir / module piéton) ≈ 1,9 m au SE"),
              pos("feu_REV_droite"), 0.3, "projection_description", "feu_REV_droite", "confirme", "moyenne",
              pv("2ab4efbc_P2.jpg", pixels=[240, 300], tuile=0), etat_entite=etat("feu_REV_droite")))
L.append(obs(S, D, "autre", "poteau_reseau_bois",
              dict(triangulation="2 photos (2ab4efbc P2 t4 (195,250) ; 119d9094 P5 t4 (163,250)), angle 38°",
                   ecart_m=0.82, remarque="à confirmer par une 3e vue (pose 2024 moins précise)"),
              (-17.30, 9.54, 0.06), 0.5, "triangulation", "poteau_reseau_12888048898", "incertain", "faible",
              pv("2ab4efbc_P2.jpg", pixels=[595, 650], tuile=4), etat_entite=etat("poteau_reseau_12888048898")))
L.append(obs(S, D, "feu", "support_feux_ilot",
              dict(remarque="2e photo : fût sur la position d'origine (à ≈ 0,3 m du côté opposé à la correction du solveur)"),
              pos("feu_VERC_ilot"), 0.3, "projection_description", "feu_VERC_ilot", "confirme", "moyenne",
              pv("2ab4efbc_v2.jpg", pixels=[565, 420]), etat_entite=etat("feu_VERC_ilot")))
L.append(obs(S, D, "candelabre", "mat_a_crosse",
              dict(remarque="2e vue : crosse simple vers le carrefour (NO) ; triangulation à 2 vues non concluante (angle 16°)"),
              pos("lamp_9514830019"), 0.5, "projection_description", "lamp_9514830019", "confirme", "moyenne",
              pv("2ab4efbc_v2.jpg", pixels=[935, 300]), etat_entite=etat("lamp_9514830019")))
L.append(obs(S, D, "panneau", "D21_double",
              dict(lecture="« LA REVIRÉE / Collège L. Terray » (flèche) au-dessus de « Commerces de LA REVIRÉE », fond blanc, liseré noir",
                   support="poteau unique gris sur l'îlot triangulaire (dessus enrobé sombre, bordure béton)"),
              (-4.19, 6.33, 0.08), 0.3, "triangulation", "pan_D21_2", "position_corrigee", "moyenne",
              pv("2ab4efbc_P2.jpg", pixels=[558, 250], tuile=1),
              valide=(False, "état du 24/08/2024 ; emplacement repris par la traversée cyclable 2025 (MP-0001)")))
n = T.ajouter(I, *L); print("ajoutées", n)
