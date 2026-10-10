import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "3fc0ff2e"; S = "pnx:" + camera.photo(I).id; D = "2024-05-01T17:17"
L = []
P = (-10.30, -4.37, -0.08)
L.append(obs(S, D, "panneau", "D21_double",
              dict(lecture="« LA REVIRÉE / Collège L. Terray » (flèche vers le nord) au-dessus de « Commerces de LA REVIRÉE »",
                   implantation="sur l'ancien îlot de la branche Verdun O, au pied du candélabre double crosse (≈ 3 m)",
                   remarque="second jeu de D21 distinct de pan_D21_1/2 (îlot de la Revirée) ; pose refusée (indicative, ±1 m)"),
              P, 1.0, "rayon_sol", None, "absent_de_description", "faible",
              pv("3fc0ff2e_v3.jpg", pixels=[355, 668]),
              valide=(False, "ancien îlot de la branche O supprimé par les travaux 2025 (TPC neuf) : panneau déposé ou déplacé")))
L.append(obs(S, D, "autre", "chantier_2024",
              dict(observation="chantier au cœur du carrefour le 01/05/2024 : pelle Komatsu, clôtures Heras, barrières rouge/blanc, grave à l'angle NE (devant feu_NE_TPC / îlot I-0332)",
                   consequence="les photos du 01/05/2024 ne prouvent rien sur les marquages et bordures du cœur"),
              (8.0, 8.0, 0.0), 5.0, "projection_description", None, "incertain", "moyenne",
              pv("3fc0ff2e_v1.jpg", bbox=[790, 140, 1200, 400]),
              valide=(False, "état de chantier temporaire (mai 2024)")))
n = T.ajouter(I, *L); print("ajoutées", n)
