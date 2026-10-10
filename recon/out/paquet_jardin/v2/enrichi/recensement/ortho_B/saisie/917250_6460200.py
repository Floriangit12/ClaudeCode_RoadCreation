# 917250_6460200 : angle SO Verdun / Vercors (rive O de Vercors), parking et bâtiment des Mitaillères
o(T, 967.5, 441, "candelabre", "mat_lampadaire_camera", "position_corrigee", "moyenne", "lamp_9514825221",
  "l'ombre fine du mât s'arrête à (967,441), 1,1 m au S du point décrit ; lanterne ovale et boîtier blanc (caméra) vus juste au SE : un seul mât portant lanterne et caméra (confirme la fusion FUS-lamp_9514825221-mat_camera_9831317323), pied à déplacer d'≈1,1 m vers le S",
  a={"liens": ["lamp_9514825221", "mat_camera_9831317323"], "deplacement_m": 1.1}, p=0.3, pr=True)
o(T, 418, 60, "mobilier", "coffre_ou_abri_conteneurs", "absent_de_description", "moyenne", None,
  "rectangle blanc ≈1,5 x 0,5 m accolé à un volume sombre avec ombre (coffre, abri de conteneurs ou banc) en lisière du parking : ancien MZ-0254 (v0.2, pris pour un marquage, retiré en v0.3 à raison) ; l'objet manque au mobilier",
  a={"id_v0_2": "MZ-0254"})
o(T, 337, 207, "marquage", "ligne_place_stationnement", "absent_de_description", "moyenne", None,
  "trait de place très effacé (usure 3), le plus à l'O du parking des Mitaillères, non décrit", seg=(322, 165, 355, 250), a={"usure": "3"})
o(T, 470, 120, "marquage", "ligne_place_stationnement", "attribut_corrige", "moyenne", "ML-0247",
  "les traits de places décrits (ML-0247 à ML-0249) ne couvrent que la moitié S des traits peints : les traits font ≈5 m (rangée en épi droite, terminaison en T côté allée)",
  seg=(452, 45, 495, 175), a={"liens": ["ML-0247", "ML-0248", "ML-0249"]})
o(T, 300, 380, "cloture", "cloture", "absent_sur_image", "haute", "cloture_gam_002",
  "le tracé GAM de cloture_gam_002 (et cloture_gam_001 dans son prolongement) traverse en ligne droite l'allée et les places du parking des Mitaillères puis le massif : aucune clôture en 2022 et une clôture y couperait les places ; limite de propriété levée comme clôture ? ne pas instancier sur le parking",
  geom=[[88, 294], [498, 114]], a={"liens": ["cloture_gam_001", "cloture_gam_002"]})
o(T, 780, 300, "autre", "etat_2022_remplace", "incertain", "haute", None,
  "rive O de Vercors en 2022 : cheminement courbe en enrobé gris bordé d'une bordure JAUNE Chronovélo, axe « • • — • » (tiret vers 793,94), bande plantée puis chaussée ; remplacé en 2025 par la piste droite (bordures GAM tiretées) : non vérifiable",
  bb=[700, 0, 950, 300], va=(False, "cheminement remplacé en 2025 par la piste droite vers Vercors"))
o(T, 40, 100, "marquage", "zigzag_arret_ancien", "incertain", "haute", None,
  "zigzag jaune d'arrêt bus et marquages de l'ancienne voie de tourne-à-droite en 2022 (angle NO de la dalle) : supprimés en 2025 avec la TAD",
  bb=[0, 0, 150, 170], va=(False, "voie de tourne-à-droite supprimée en 2025"))
o(T, 514, 247, "tampon", "regard_grille", "absent_de_description", "haute", None, "regard carré à grille ≈0,8 m posé à 45° dans l'allée du parking des Mitaillères", af="sombre", r=10)
o(T, 277, 14, "autre", "poteau_reseau", "confirme", "faible", "poteau_reseau_13624544994", "objet cylindrique clair vu de dessus à 0,5 m du point, en bord de trottoir")
o(T, 700, 300, "surface", "surface_fourre_tout", "attribut_corrige", "haute", "S-0159a",
  "S-0159a (parking enrobé, 4 101 m², pureté 0,45) englobe le bois et les pelouses à l'E du bâtiment des Mitaillères et les massifs à l'O ; ≈430 m² de végétation sur 1 200 m² vus dans la dalle : à découper",
  a={"aire_vue_m2": 1200, "vegetation_m2": 434}, bb=[0, 0, 1000, 1000], vt=700, pr=True)
