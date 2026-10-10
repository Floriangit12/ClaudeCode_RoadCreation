import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "9fc8ba46"; S = "pnx:" + camera.photo(I).id; D = "2025-05-18T13:37"
S44 = "pnx:" + camera.photo("4407962b").id
L = []
L.append(obs(S, D, "panneau", "pile_B2b_B1",
              dict(lecture="disque B2b (interdiction de tourner à DROITE : flèche noire vers la droite barrée) au-dessus d'un B1 (sens interdit, disque rouge à barre blanche)",
                   hauteur_centre_m=dict(B2b=2.81, B1=1.96), hauteurs_description=dict(B2b=2.75, B1=2.1),
                   support="poteau gris dans l'accotement enherbé, entre la piste (tirets) et la voie d'accès ; faces vers l'ENE",
                   rayons_sol=dict(n9fc8ba46=[52.51, 58.49], n4407962b=[51.44, 57.65]),
                   ecart_description_m=3.5,
                   controle="depuis 9fc8ba46 (pose calée, GNSS 0,1 m, 12 m) l'azimut du poteau diffère de 14° de celui de la position décrite : écart latéral ≈ 3 m, hors de toute erreur de pose",
                   fusion_coherence="rejetée : B2b/B1 et B2a/AB3a/M9 sont deux poteaux distincts (visibles ensemble dans 4407962b)"),
              (52.0, 58.1, 0.65), 0.8, "rayon_sol", "pan_B2b_1", "position_corrigee", "moyenne",
              pv("9fc8ba46_pile_v0_brut.jpg", pixels=[437, 760], note="pied du poteau ; disques en (428,380) et (430,495)"),
              etat_entite=etat("pan_B2b_1")))
L.append(obs(S44, "2024-08-24T15:05", "panneau", "pile_B2a_AB3a_M9c",
              dict(observation="second poteau (disque B2a + triangle AB3a) juste derrière le poteau B2b/B1 depuis le NE (azimut 237,5° contre 236,5°)",
                   triangulation="azimut 237,5° (4407962b) × 40,0° (eeb2f8f1) et 38,6° (79a18815) : (47,3 ; 55,2) et (47,7 ; 55,4), angle d'intersection ≈ 18°",
                   ecart_description_m=7.0,
                   remarque="position décrite (52,0 ; 61,5) incompatible avec 4407962b et 9fc8ba46 (aucun poteau à l'azimut correspondant) ; 050fff48 (pose refusée, indicative) montre la pile disque + triangle + panonceau à 3-4 m au NNO de la caméra : estimations divergentes, à vérifier sur place"),
              (47.5, 55.3, 0.5), 2.0, "triangulation", "pan_B2a_1", "incertain", "faible",
              pv("4407962b_pile_v0_brut.jpg", pixels=[464, 450], note="disque B2a en (467,378), triangle en (470,430)"),
              etat_entite=etat("pan_B2a_1")))
n = T.ajouter(I, *L); print("ajoutées", n)
