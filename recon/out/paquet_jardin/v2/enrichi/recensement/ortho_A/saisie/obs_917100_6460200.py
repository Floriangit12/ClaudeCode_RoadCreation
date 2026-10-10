from obs_lib import ob, tuile
tuile("917100_6460200")
H = "parking hors zone de travaux 2025"

ob("arbre", "jeunes_arbres_alignement", (917136.0, 6460242.0), "absent_de_description", conf="haute", prec=0.5, preuve=True,
   attributs={"observe": "alignement de jeunes arbres (couronnes ≈ 2–3 m, peu feuillues en 05/2022) dans la bande centrale pavée du parking, au pas ≈ 7 m",
              "positions_l93": [[917122.75, 6460232.5], [917126.5, 6460234.75], [917130.0, 6460238.0], [917136.75, 6460243.0], [917140.5, 6460245.25]],
              "dans_emprise": "3 derniers (x > 917129,4)"},
   valide=True, raison=H)
ob("marquage", "bande_centrale_hachuree", (917135.0, 6460238.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"observe": "bande centrale de ≈ 1,5 m entre les deux rangées de places, revêtue de pavés/dalles avec hachures blanches transversales, fosses d'arbres",
              "geometrie_l93_approx": [[917121.0, 6460229.0], [917144.0, 6460247.0]]},
   valide=True, raison=H)
ob("marquage", "places_parking", (917138.0, 6460235.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"observe": "≈ 30 places en épi des deux côtés de la bande centrale (traits blancs continus) ; la description n'en porte que des fragments (ML-0105, ML-0108, ML-0109, ML-0199, ML-0203, ML-0204)",
              "etendue_l93": [[917120.0, 6460223.0], [917150.0, 6460250.0]]},
   valide=True, raison=H)
ob("autre", "hors_emprise_description", (917112.0, 6460225.0), "absent_de_description", conf="haute", prec=20.0,
   attributs={"observe": "partie O hors emprise (x < 917129,4) : allée du parking, abri à vélos couvert (≈ 917120.5, 6460229), aire de dépôt avec bennes et palettes, chemin piéton en terre"},
   valide=True, raison=H)
