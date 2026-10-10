import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "79a18815"; S = "pnx:" + camera.photo(I).id; D = "2024-08-24T15:10"
Se = "pnx:" + camera.photo("eeb2f8f1").id
L = []
L.append(obs(S, D, "cloture", "cloture_chantier_mobile",
              dict(type_observe="clôture de chantier mobile : panneaux grillagés galvanisés ≈ 3,5 × 2,0 m sur plots béton (type Heras)",
                   ligne="suit exactement cloture_gam_049 (rive SE de Verdun NE, devant la végétation des Saules Blancs)",
                   hauteur_observee_m=2.0, hauteur_description_m=1.6),
              (45.0, 28.0, 0.5), 0.5, "projection_description", "cloture_gam_049", "attribut_corrige", "haute",
              pv("79a18815_v3.jpg", bbox=[0, 405, 1200, 500]),
              valide=("incertain", "clôture temporaire en 08/2024, absente le 18/05/2025 (eeb2f8f1)")))
L.append(obs(Se, "2025-05-18T13:37", "cloture", "absente",
              dict(observation="aucune clôture le long de la ligne cloture_gam_049 le 18/05/2025 : la végétation commence au bord du cheminement",
                   proposition="ne pas instancier cloture_gam_049 sur ce tronçon (levé de la clôture de chantier 2024), ou la vérifier sur place"),
              (42.0, 30.0, 0.5), 1.0, "projection_description", "cloture_gam_049", "absent_sur_image", "moyenne",
              pv("eeb2f8f1_v3.jpg", bbox=[30, 400, 1200, 450]),
              valide=(True, "photo du 18/05/2025 hors emprise des travaux du carrefour ; aucune trace de pose ultérieure")))
L.append(obs(S, D, "surface", "chaussee_fissuree",
              dict(etat="faïençage généralisé à mailles larges (0,5-1,5 m) sur les deux sens de Verdun NE, fissures pontées au bitume (traits noirs brillants)",
                   marquage_hachures="zone hachurée (bandes obliques) au sud-est de l'axe, usure moyenne"),
              (37.5, 34.5, 0.4), 1.0, "rayon_sol", "S-0269", "absent_de_description", "haute",
              pv("79a18815_v3.jpg", bbox=[0, 560, 1200, 900]),
              valide=(True, "branche Verdun NE hors emprise des travaux ; même état le 18/05/2025 (eeb2f8f1 v3)")))
n = T.ajouter(I, *L); print("ajoutées", n)
