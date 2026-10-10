# 917300_6460350 : rive N de Verdun NE (piste bidirectionnelle, accès riverain, parking arboré, pelouse)
o(T, 640, 866, "marquage", "symbole_velo", "confirme", "haute", "MS-5016",
  "figurine vélo peinte (usure 1) à 0,15 m de MS-5016 : conforme (MS-0597 de la v0.2, mal placé, retiré)", af="clair", r=10, a={"usure": "1", "id_v0_2": "MS-0597"})
o(T, 629, 921, "marquage", "symbole_velo", "absent_de_description", "moyenne", None,
  "figurine vélo très effacée (usure 3) centrée vers (629,921) : MS-5000 est 1,1 m plus au NE, sur la flèche de piste ; à poser ici", a={"usure": "3", "id_v0_2": "MS-0596"})
o(T, 650, 817, "marquage", "zone_divers_Y", "absent_sur_image", "moyenne", "MZ-5002",
  "rien de peint au point de MZ-5002 (forme en Y, « conserve ») : enrobé de piste nu en 2022 (déjà rien au point de MS-0595 v0.2)", a={"id_v0_2": "MS-0595"})
o(T, 655, 897, "marquage", "fleche_piste", "attribut_corrige", "haute", "MS-5000",
  "la peinture au point de MS-5000 est une FLÈCHE blanche de piste (≈0,8 m) orientée vers le NE, pas une figurine vélo ; la figurine est 1,1 m au SO (observation voisine)",
  af="clair", r=10, a={"classe_proposee": "fleche (piste, sens NE)"})
o(T, 580, 862, "marquage", "damier_traversee", "attribut_corrige", "moyenne", "ML-5146",
  "la traversée de la piste par l'accès riverain est un DAMIER de carrés clairs ≈0,6 m sur 2 rangs ; la v0.3 la décrit par des lignes continues (ML-5140 à ML-5146), la v0.2 par un zébra (MP-0586) : forme à remplacer par un damier",
  a={"liens": ["ML-5140", "ML-5142", "ML-5143", "ML-5144", "ML-5145", "ML-5146"], "type_propose": "traversee_cyclable (damier 2 rangs)", "id_v0_2": "MP-0586"}, bb=[548, 838, 615, 895])
o(T, 760, 150, "bordure", "arc_gazon", "absent_sur_image", "moyenne", "K-0084",
  "l'arc de cercle de bordures GAM KS-0078 à KS-0086 (rayon ≈9 m) traverse une pelouse uniforme : aucune bordure ni chemin visible en 2022 ; ressaut levé 1 à 4,5 cm (dz_mnt) : bordure arasée enfouie ou tracé de plan, à ne pas instancier en bordure vue",
  a={"liens": ["K-0078", "K-0081", "K-0082", "K-0083", "K-0084", "K-0085", "K-0086"]}, bb=[620, 0, 1000, 240], vt=400)
o(T, 597, 815, "mobilier", "objet_blanc", "incertain", "faible", None,
  "objet blanc ≈0,6 m avec partie sombre, au bord de l'accès riverain près du damier (corbeille, coffret ou personne assise)")
o(T, 820, 700, "marquage", "ligne_axe_piste", "confirme", "faible", "ML-5070",
  "axe de la piste bidirectionnelle : quelques tirets visibles hors de la couronne de l'arbre a359, le reste sous le houppier (couverture 0,00 par masquage, pas par absence)")
o(T, 316, 551, "tampon", "regard_grille", "absent_de_description", "haute", None, "regard carré à grille ≈1 m posé à 45° dans l'allée du parking de la résidence", af="sombre", r=10)
o(T, 640, 860, "bordure", "bordures_piste_accotement", "confirme", "moyenne", "K-0189",
  "bordures de la zone pilote sur la rive N de Verdun NE (K-0005, K-0008, K-0012, K-0167, K-0172, K-0174, K-0177, K-0178, K-0182, K-0189, K-0194) : tracés conformes aux limites piste / accès / bande verte de l'ortho (écart < 0,2 m) ; profil et vue non vérifiables par l'ortho",
  a={"liens": ["K-0005", "K-0008", "K-0012", "K-0167", "K-0172", "K-0174", "K-0177", "K-0178", "K-0182", "K-0189", "K-0194"]})
o(T, 300, 500, "surface", "parking_en_pelouse", "attribut_corrige", "haute", "S-0094a",
  "le parking de la résidence (allée en enrobé + places en épi, voitures garées) est inclus dans S-0094a (espace vert, gazon tondu, 11 599 m²) : ≈320 m² de revêtement clair et l'allée sous les arbres dans la seule zone encadrée",
  a={"materiau_propose": "enrobe_bbsg_ancien (parking)", "revetement_clair_m2": 316}, bb=[40, 80, 640, 980], vt=600, pr=True)
