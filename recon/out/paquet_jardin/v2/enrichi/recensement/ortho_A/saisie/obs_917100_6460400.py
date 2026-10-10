from obs_lib import ob, tuile
tuile("917100_6460400")
H = "parking hors zone de travaux 2025"

ob("avaloir", "grille", (917130.5, 6460416.75), "absent_de_description", conf="haute", prec=0.1, preuve=True,
   attributs={"forme": "grille carrée ≈ 0,6 m", "support": "point bas du parking, à la jonction en V des traits ML-0097 / ML-0098 / ML-0099"},
   valide=True, raison=H)
ob("avaloir", "grille", (917148.0, 6460407.25), "absent_de_description", conf="haute", prec=0.15,
   attributs={"forme": "grille carrée ≈ 0,6 m", "support": "allée du parking S"}, valide=True, raison=H)
ob("tampon", "regard_carre", (917130.5, 6460424.7), "absent_de_description", conf="moyenne", prec=0.2,
   attributs={"forme": "regard carré ≈ 0,8 m à cadre", "support": "bande enherbée au pied du bâtiment"}, valide=True, raison=H)
ob("tampon", "tampon_rond", (917148.2, 6460428.3), "absent_de_description", conf="moyenne", prec=0.2,
   attributs={"forme": "tampon rond ≈ 0,6 m", "support": "pelouse à l'angle E du bâtiment"}, valide=True, raison=H)
ob("mobilier", "cage_metallique", (917134.0, 6460417.5), "absent_de_description", conf="moyenne", prec=0.3,
   attributs={"observe": "structure métallique cubique ≈ 1,2 m (cage ou abri technique) sur une place hachurée de blanc (≈ 917133–917135,5 / 6460413–6460416,3)"},
   valide=True, raison=H)
ob("marquage", "places_parking", (917140.0, 6460408.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"observe": "≈ 25 places perpendiculaires (traits blancs) de part et d'autre de l'allée ; seules ML-0097, ML-0098, ML-0099 (traits en V vers la grille) sont décrites",
              "etendue_l93": [[917129.4, 6460400.0], [917150.0, 6460418.0]]},
   valide=True, raison=H)
