import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
I = "28fea9c0"; S = "pnx:" + camera.photo(I).id; D = "2024-08-24T15:05"
L = []
L.append(obs(S, D, "arbre", "jeune_arbre_plante_bac",
              dict(essence_probable="Koelreuteria paniculata (savonnier) : feuilles composées vert-jaune, capsules vésiculeuses rose-orangé en août",
                   hauteur_estimee_m=4.1, couronne_estimee_m=2.5, fosse="bac béton surélevé ≈ 0,4 m, paillage", tuteurage="non visible",
                   description="arbre_211/arbre_212 : h 5,0 et couronne 2,5 par défaut ; pose a priori de séquence (±1,5 m) : l'appariement exact des deux sujets n'est pas établi"),
              (79.7, -19.4, -1.18), 1.5, "rayon_sol", "arbre_211", "attribut_corrige", "moyenne",
              pv("28fea9c0_v3_brut.jpg", pixels=[600, 540], note="cime en (600,255) ; second sujet en (1050,520)")))
L.append(obs(S, D, "cloture", "portail_coulissant",
              dict(type="portail coulissant à barreaudage vertical, aluminium/acier galvanisé gris clair, h ≈ 1,6-1,8 m, sur rail ; accès au parking privé"),
              None, None, None, "portail_12134406600", "confirme", "moyenne",
              pv("28fea9c0_v3_brut.jpg", bbox=[0, 450, 480, 650])))
L.append(obs(S, D, "surface", "parvis_paves_beton",
              dict(revetement="pavés béton gris clair 20 × 20 cm (appareillage droit, joints sable), bordurettes béton, bacs plantés surélevés en béton brut",
                   zone="résidence des Saules Blancs (voie privée), construite 2023-2024"),
              (85.0, -24.0, -1.1), 2.0, "rayon_sol", None, "attribut_corrige", "moyenne",
              pv("28fea9c0_v3_brut.jpg", bbox=[0, 560, 960, 900])))
n = T.ajouter("saules_" + I, *L); print("ajoutées", n)
