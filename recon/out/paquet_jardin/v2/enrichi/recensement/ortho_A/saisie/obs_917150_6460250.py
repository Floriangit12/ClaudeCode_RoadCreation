from obs_lib import ob, tuile
tuile("917150_6460250")
H = "parking privé de la jardinerie, hors zone de travaux 2025"

ob("marquage", "pictogrammes_pmr_bleus", (917170.0, 6460262.6), "absent_de_description", conf="haute", prec=0.2, preuve=True,
   attributs={"couleur": "bleu (fond) + blanc", "nombre": 3, "type": "pictogrammes PMR peints au sol sur 3 places adaptées",
              "positions_l93": [[917166.5, 6460262.5], [917170.0, 6460262.75], [917174.5, 6460262.5]]},
   valide=True, raison=H)
ob("marquage", "places_parking_jardinerie_o", (917172.0, 6460262.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"observe": "≈ 25 places perpendiculaires et en épi (traits blancs, pas ≈ 2,5 m), allée de circulation marquée par des lignes blanches courbes devant l'entrée",
              "etendue_l93": [[917152.0, 6460250.0], [917197.0, 6460275.0]]},
   valide=True, raison=H)
