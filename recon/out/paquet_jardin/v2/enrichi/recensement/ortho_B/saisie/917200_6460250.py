# 917200_6460250 : parking de la jardinerie Paquet Jardin, rive NO de Verdun SO (zone de travaux 2025)
_L = [(662, 180, 705, 222), (598, 253, 630, 287), (565, 290, 618, 343), (628, 285, 670, 325), (660, 245, 695, 278),
      (343, 511, 400, 570), (310, 547, 378, 612),
      (278, 650, 316, 686), (176, 681, 250, 755), (235, 674, 284, 720)]
for _i, _b in enumerate(_L):
    o(T, (_b[0] + _b[2]) / 2, (_b[1] + _b[3]) / 2, "marquage", "ligne_place_stationnement", "absent_de_description",
      "haute", None,
      "trait blanc de délimitation de place (terminé en T) du parking de la jardinerie, absent de la description (seuls 9 traits ML-0224…ML-0243 y sont) ; géométrie ajustée sur la peinture",
      seg=_b, pr=(_i == 0), a={"couleur": "blanc", "rangee": "parking jardinerie"})
o(T, 188.3, 721.1, "candelabre", "lampadaire", "absent_sur_image", "haute", "lamp_12758859672",
  "aucun mât ni ombre au point décrit (au milieu d'une place du parking) alors que la zone est inchangée et que les autres mâts portent des ombres de 5 à 8 m ; nœud OSM 2025-06 : position à vérifier")
o(T, 254.4, 226.5, "candelabre", "lampadaire", "absent_sur_image", "moyenne", "lamp_12758894668",
  "rien au point décrit (bord de la serre) en 2022 ; nœud OSM 2026-03 : candélabre peut-être posé après 2022",
  va=("incertain", "objet OSM 2026, éventuellement postérieur à l'image"))
o(T, 906.6, 406.4, "candelabre", "lampadaire", "confirme", "haute", "lamp_lidar_SW_NO",
  "pied dans la haie NO et longue ombre de mât vers le NNO (≈5 m au sol) : candélabre présent en 2022 au point LiDAR")
o(T, 869, 685, "candelabre", "lampadaire", "absent_sur_image", "moyenne", "lamp_9514795519",
  "position « déduite 2026 » (candélabre déplacé par les travaux) : rien au point en 2022, comme attendu",
  va=(False, "position 2026 déduite, sans rapport avec l'état 2022"))
o(T, 327, 693, "tampon", "regard_carre", "absent_de_description", "moyenne", None,
  "cadre de regard carré ≈1 m (joints sombres) dans l'allée du parking", af="sombre", r=12)
o(T, 535, 600, "surface", "reprise_enrobe", "absent_de_description", "moyenne", None,
  "deux grandes reprises d'enrobé plus sombres dans le parking (≈4,5 x 5,5 m et ≈9 x 8 m) : teinte d'enrobé différente à porter sur la surface du parking",
  bb=[490, 470, 720, 660], vt=300)
o(T, 700, 880, "mobilier", "stationnement_trottinettes", "incertain", "moyenne", None,
  "en 2022, aire de stationnement libre-service (vélos et trottinettes, cadre peint ≈4,5 x 2,5 m) sur le trottoir NO de Verdun ; le projet 2025 prévoit une « place DOTT » dans la nouvelle bande NO : emplacement 2026 différent",
  bb=[640, 800, 740, 930], va=(False, "trottoir NO reconstruit en 2025"))
o(T, 850, 750, "autre", "etat_2022_remplace", "incertain", "haute", None,
  "rive NO de Verdun SO en 2022 : piste cyclable à logos vélo le long de la haie du parking, trottoir, quai bus en béton, chaussée à 2 voies avec flèches ; tout ce secteur est reconstruit en 2025 (bordures GAM tiretées, marquages neuf_2025 : MS-0890 à MS-0903, MZ-0920, ML-0796 à ML-0828, MF-0766/0769) : non vérifiable par l'ortho",
  bb=[500, 500, 1000, 1000], va=(False, "secteur reconstruit en 2025"))
o(T, 782, 379, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond dans le parking de la jardinerie", af="sombre", r=8)
o(T, 404, 865, "tampon", "tampon_rond", "absent_de_description", "moyenne", None, "tampon rond dans une reprise d'enrobé", af="sombre", r=8)
o(T, 592, 815, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond ≈0,7 m", af="sombre", r=8)
o(T, 523, 384, "tampon", "tampon_rond", "absent_de_description", "moyenne", None, "tampon rond dans une reprise d'enrobé", af="sombre", r=8)
o(T, 516, 758, "tampon", "regard_carre", "absent_de_description", "moyenne", None, "petit regard ≈0,4 m", af="sombre", r=6)
o(T, 344, 930, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond à anneau clair", af="sombre", r=8)
o(T, 721, 982, "tampon", "regard_carre", "absent_de_description", "haute", None, "petit regard carré ≈0,5 m", af="sombre", r=6)
o(T, 650, 665, "haie", "haie_taillee", "absent_de_description", "haute", None,
  "haie basse taillée (≈1 m de large, ≈60 m) séparant le parking de la jardinerie du trottoir de Verdun SO ; non décrite (incluse dans le parking S-0161a)",
  geom=[[300, 985], [450, 850], [650, 665], [850, 470], [1000, 345]], a={"largeur_m": 1.0, "lien_surface": "S-0161a"}, bb=[300, 330, 1000, 1000], vt=420,
  va=("incertain", "en limite de la zone des travaux 2025 de la rive NO"))
o(T, 320, 420, "surface", "pepiniere_plein_air", "attribut_corrige", "haute", "S-0161a",
  "aire de vente de végétaux en plein air (planches de plantes en pots sur gravier, allées, petits abris) de ≈1 000 m² au pied de la serre, décrite comme parking enrobé (S-0161a)",
  a={"materiau_propose": "gravier + plantes en pots (pépinière)"}, bb=[40, 150, 560, 700], vt=500)
o(T, 470, 640, "mobilier", "butees_de_roues", "absent_de_description", "moyenne", None,
  "rangée de butées de roues sombres (≈0,6 x 0,2 m, une par place) le long de la haie, côté parking",
  geom=[[340, 955], [385, 700], [500, 620], [615, 540]], bb=[330, 520, 640, 960])
