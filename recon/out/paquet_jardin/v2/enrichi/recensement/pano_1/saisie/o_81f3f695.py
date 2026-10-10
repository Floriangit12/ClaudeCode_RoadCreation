import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "81f3f695"; S = "pnx:" + camera.photo(I).id; D = "2024-08-24T15:05"
L = []
L.append(obs(S, D, "candelabre", "mat_droit_residentiel",
              dict(hauteur_estimee_m=4.5, couleur_mat="gris clair", lanterne="tête plate rectangulaire en sommet",
                   implantation="trottoir de la voie privée des Saules Blancs, à la sortie sur l'avenue du Vercors",
                   remarque="aucun candélabre décrit à moins de 12 m ; pose a priori de séquence (±1,5 m)"),
              (58.11, -29.69, -1.39), 1.5, "rayon_sol", None, "absent_de_description", "moyenne",
              pv("81f3f695_v0_brut.jpg", pixels=[1022, 606], note="tête en (1030,228)")))
L.append(obs(S, D, "surface", "voie_privee_paves",
              dict(revetement="pavés béton gris clair (≈ 20 × 10 cm) en bandes et dalles carrées sur les trottoirs, bordures béton basses, massifs plantés de jeunes arbres tuteurés",
                   zone="voies et parkings privés du quartier des Saules Blancs (x 50-90, y -45…-25)"),
              (62.0, -33.0, 0.0), 3.0, "rayon_sol", None, "attribut_corrige", "moyenne",
              pv("81f3f695_v0_brut.jpg", bbox=[190, 560, 1200, 900])))
n = T.ajouter(I, *L); print("ajoutées", n)
