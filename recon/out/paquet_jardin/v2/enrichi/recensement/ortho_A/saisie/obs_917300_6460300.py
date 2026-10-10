from obs_lib import ob, tuile
tuile("917300_6460300")
H = "hors zone de travaux 2025 (Verdun NE conservée, hist-13)"

ob("tampon", "regard_rond", (917305.43, 6460324.17), "absent_de_description", lien="S-0121", conf="haute", prec=0.1, preuve=True,
   attributs={"forme": "tampon rond ≈ 0,8 m (anneau brun-gris), à fleur de la bande enherbée", "support": "accotement enherbé S-0121 entre piste et chaussée, à ≈ 1,2 m de la bordure K-0666/A2 côté chaussée"},
   valide=True, raison=H)
ob("candelabre", "mat_double_luminaire", (917325.0, 6460341.92), "position_corrigee", lien="lamp_9665416717", conf="moyenne", prec=0.2, preuve=True,
   attributs={"decrit": {"position": [917325.85, 6460342.14], "nb_crosses": 1, "porte_a_faux_m": 1.5},
              "observe": "pied du mât au départ de l'ombre (0,9 m à l'OSO de la position décrite), dans l'accotement enherbé ; 2 luminaires : un en tête de mât, un en bout de crosse à ≈ 2,5 m vers le SE au-dessus de la chaussée (azimut ≈ 135°)",
              "nb_luminaires": 2, "porte_a_faux_m": 2.5},
   valide=True, raison=H)
ob("marquage", "ligne_continue", (917306.6, 6460327.4), "confirme", lien="ML-5185", conf="haute", prec=0.1, preuve=True,
   attributs={"observe": "ligne continue nette en 05/2022 sur l'axe levé GAM 185-186 (contraste fort, décalage < 0,05 m) ; aucune ligne de rive contre la bordure NO : l'ancienne ML-9185 (v0.2, à 0,35 m de la bordure) n'existait pas en 2022"},
   valide=True, raison="hors travaux 2025 ; levé GAM 2026")
ob("marquage", "symbole_velo", (917324.3, 6460347.9), "incertain", lien="MS-5155", conf="faible", prec=0.5,
   attributs={"observe": "zone sous ombre portée dense : figurines MS-5155 / MS-5214 (ex MS-0593 / MS-0594) non discernables (contraste nul)"}, valide="incertain", raison="non vérifiable sur l'ortho 2022")
ob("marquage", "texte_50", (917300.6, 6460304.4), "confirme", lien="MS-0598", conf="haute", prec=0.1, valide=True, raison=H)
ob("marquage", "texte_50", (917302.8, 6460302.4), "confirme", lien="MS-0599", conf="haute", prec=0.1, valide=True, raison=H)
ob("bordure", "arete_avant", (917325.0, 6460325.0), "confirme", lien="K-0666", conf="moyenne", prec=0.1,
   attributs={"observe": "limite enrobé / accotement suivie à ≈ 0,1 m sur 15 m (ombres d'arbres)"}, valide=True, raison=H)
ob("surface", "prairie_fleurie", (917310.0, 6460330.0), "confirme", lien="S-0121", conf="moyenne", prec=1.0,
   attributs={"observe": "accotement enherbé non tondu avec nombreuses fleurs blanches (05/2022) entre piste et chaussée NO : « herbe_haute » cohérent"},
   valide=True, raison=H)
ob("bordure", "arete_avant_courbe", (917329.5, 6460346.0), "confirme", lien="K-0353", conf="moyenne", prec=0.1,
   attributs={"observe": "rayon de l'angle de l'accès (côté Revirée NE) suivi par la bordure décrite"}, valide=True, raison=H)
