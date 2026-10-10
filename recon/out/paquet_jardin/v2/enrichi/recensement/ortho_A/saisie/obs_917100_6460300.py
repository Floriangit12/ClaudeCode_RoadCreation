from obs_lib import ob, tuile
tuile("917100_6460300")
H = "équipement sportif privé hors zone de travaux 2025"

ob("surface", "courts_de_tennis", (917135.0, 6460325.0), "attribut_corrige", lien="surf_0246", conf="haute", prec=2.0, preuve=True,
   attributs={"materiau_decrit": "enrobe (classe autre)", "observe": "3 courts de tennis en résine/béton poreux vert-gris avec lignes blanches, filets et chaises d'arbitre, séparés par des grillages ; fissures et mousse",
              "materiau_propose": "resine_sport_verte (ou enrobé coloré vert)", "classe_proposee": "terrain_de_sport"},
   valide=True, raison=H, note="emprise en grande partie hors de l'enveloppe décrite (x < 917129,4)")
ob("cloture", "grillages_tennis", (917127.0, 6460330.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"observe": "grillages de séparation et de pourtour des courts (h ≈ 3–4 m d'après les ombres), dont la ligne (917120, 6460338) → (917137, 6460312)"},
   valide=True, raison=H)

ob("bordure", "arete_avant_decalee", (917146.85, 6460345.65), "position_corrigee", lien="KS-0227-1", conf="moyenne", prec=0.15, preuve=True,
   attributs={"decrit": "bordure GAM KS-0227-1 (carte de cohérence) de (917145.27, 6460350.73) à (917149.76, 6460341.78)",
              "observe": "la seule bordure visible (bande béton grise à joints entre pelouse et voie de service, au pied du grillage des tennis) est ≈ 0,85 m à l'OSO de la ligne décrite, qui tombe dans l'enrobé uniforme de la voie",
              "decalage_m": 0.85, "vecteur_l93_m": [-0.76, -0.38], "methode_controle": "profil de luminance médian sur 20 sections (bande claire à t = −0,85 m)"},
   valide=True, raison="hors zone de travaux 2025 ; abords inchangés")
