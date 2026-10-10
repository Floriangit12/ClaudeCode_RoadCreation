import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
D = "2025-08-31T15:39"
def S(i): return "pnx:" + camera.photo(i).id
L = []
L.append(obs(S("dabd05a0"), "2025-08-31T15:37", "marquage", "effet_feux",
              dict(observation="31/08/2025 : toujours aucune ligne d'effet des feux sur l'approche Verdun NE (flèches et zébra visibles, reprises d'enrobé fraîches près du zébra)",
                   conclusion="ligne posée en fin de chantier (sept.-nov. 2025) : état 'neuf_2025', usure 0",
                   lien="photo à plat sans pose calée : lien par identification"),
              None, None, None, "MT-0563", "attribut_corrige", "moyenne",
              pv("dabd05a0_gauche.jpg", bbox=[480, 490, 1110, 560]),
              valide=(True, "la ligne n'existait pas encore au 31/08/2025 : peinture neuve en 2026")))
L.append(obs(S("dabd05a0"), "2025-08-31T15:37", "autre", "chantier_coeur_2025",
              dict(observation="cœur en chantier le 31/08/2025 : séparateurs plastique rouge/blanc, barrières, panneau « ROUTE BARRÉE », balise à chevrons, séparateurs K16 stockés à l'angle N (devant la jardinerie)"),
              None, None, None, None, "incertain", "haute",
              pv("dabd05a0_gauche.jpg", bbox=[0, 380, 1200, 440]),
              valide=(False, "état de chantier temporaire")))
L.append(obs(S("10ec04d5"), "2025-08-31T15:37", "panneau", "J5",
              dict(face="bleu, flèche blanche oblique vers le bas à droite (lecture de face depuis l'approche NE)", lien="photo sans pose : identification (nez du TPC NE)"),
              None, None, None, "pan_J5_1", "confirme", "haute",
              pv("10ec04d5_J5.jpg", bbox=[80, 100, 270, 300], note="extrait HD x 0-500, y 1000-1400"),
              valide=(True, "photo du 31/08/2025 ; TPC NE conservé")))
L.append(obs(S("10ec04d5"), "2025-08-31T15:37", "panneau", "arret_provisoire",
              dict(lecture="panneau orange à liseré hachuré « ARRÊT PROVISOIRE » (bus) au-dessus d'un cadre d'horaires, sur poteau gris, accotement NE de Verdun NE près de l'angle de la Revirée",
                   remarque="équipement de chantier (déplacement des quais C1/42) : à ne pas instancier en 2026"),
              None, None, None, None, "absent_de_description", "haute",
              pv("10ec04d5_arret_provisoire.jpg", bbox=[120, 0, 360, 250], note="extrait HD x 2950-3350, y 350-1000"),
              valide=(False, "équipement temporaire de chantier (août 2025)")))
L.append(obs(S("81882270"), D, "panneau", "D21_double",
              dict(observation="les deux D21 (« LA REVIRÉE / Collège L. Terray », « Commerces de LA REVIRÉE ») sont encore sur leur îlot le 31/08/2025",
                   remarque="dépose éventuelle postérieure (traversée cyclable MP-0001) : non tranché"),
              (-4.19, 6.33, 0.08), 0.5, "triangulation", "pan_D21_1", "incertain", "moyenne",
              pv("81882270_D21.jpg", bbox=[70, 70, 430, 260], note="extrait HD x 2450-3000, y 700-1100"),
              valide=("incertain", "présent au 31/08/2025, travaux du carrefour poursuivis jusqu'en novembre 2025")))
n = T.ajouter("vis_20250831", *L); print("ajoutées", n)
