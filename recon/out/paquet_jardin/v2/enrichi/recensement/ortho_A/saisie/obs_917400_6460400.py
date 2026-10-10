from obs_lib import ob, tuile
tuile("917400_6460400")
H = "hors zone de travaux 2025 (Verdun NE conservée)"

ob("massif", "arbustes_tailles_en_blocs", (917418.5, 6460436.0), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"observe": "file d'arbustes taillés en blocs (≈ 1 m, pas 2–3 m) dans l'accotement entre le trottoir NO et Verdun NE, prolongement de ceux de la dalle 917350_6460350",
              "positions_l93": [[917427.0, 6460446.25], [917422.25, 6460442.0], [917420.5, 6460440.25], [917418.5, 6460438.0], [917417.25, 6460436.75],
                                [917415.75, 6460435.25], [917414.5, 6460434.0], [917413.0, 6460432.5], [917411.5, 6460431.0]]},
   valide=True, raison=H)
ob("candelabre", "mat_crosse", (917410.9, 6460429.1), "confirme", lien="lamp_9665416417", conf="moyenne", prec=0.3,
   attributs={"observe": "pied du mât au départ de l'ombre, à 0,8 m de la position OSM ; deux taches blanches de luminaire (917411.1, 6460429.0) et (917413.4, 6460426.9) : probablement 2 luminaires comme lamp_9665416717"},
   valide=True, raison=H)
ob("marquage", "ligne_discontinue", (917426.2, 6460437.1), "attribut_corrige", lien="ML-5136", conf="moyenne", prec=0.15, preuve=True,
   attributs={"decrit": "ligne de délimitation « continue » (GAM 136, 149, 224, 227)", "observe": "tirets ≈ 2,5–3 m (tiret de (917425.0, 6460435.9) à (917427.4, 6460438.3)) à ≤ 0,2 m de l'axe GAM : ligne discontinue (T3, cf. mesure le long de l'axe dans la dalle 917350_6460350)", "modulation_proposee": "T3",
              "note_v02": "l'axe v0.2 ML-0562 était ≈ 0,5 m trop au NO ; corrigé en v0.3 (GAM)"},
   valide=True, raison=H)
