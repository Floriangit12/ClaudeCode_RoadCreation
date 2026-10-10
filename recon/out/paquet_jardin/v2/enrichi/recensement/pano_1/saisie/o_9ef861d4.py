import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "9ef861d4"; S = "pnx:" + camera.photo(I).id; D = "2025-08-31T15:37"
L = []
L.append(obs(S, D, "panneau", "B2a",
              dict(lecture="disque blanc à bord rouge, flèche noire tournant à GAUCHE barrée de rouge : B2a (interdiction de tourner à gauche)",
                   pile="B2a au-dessus d'AB3a (triangle) et d'un panonceau blanc « CÉDEZ LE PASSAGE » (M9c), un seul poteau gris",
                   lien="photo sans pose calée : lien par identification (seule pile B2a/AB3a de ce tronçon de Verdun NE, vue de face en roulant vers le SO)",
                   faces="vers le NE"),
              None, None, None, "pan_B2a_1", "confirme", "haute",
              pv("9ef861d4_crop_disque.jpg", bbox=[190, 90, 430, 590], note="extrait HD 3400-3750 × 350-800 px"),
              valide=(True, "photo du 31/08/2025, branche Verdun NE hors emprise des travaux")))
L.append(obs(S, D, "panneau", "M9c",
              dict(lecture="panonceau rectangulaire blanc à bord bleu foncé, texte « CÉDEZ LE PASSAGE » sous l'AB3a", code_propose="M9c"),
              None, None, None, "pan_M9_2", "attribut_corrige", "haute",
              pv("9ef861d4_crop_panneaux.jpg", bbox=[275, 700, 430, 830]),
              valide=(True, "photo du 31/08/2025, hors emprise des travaux")))
n = T.ajouter(I, *L); print("ajoutées", n)
