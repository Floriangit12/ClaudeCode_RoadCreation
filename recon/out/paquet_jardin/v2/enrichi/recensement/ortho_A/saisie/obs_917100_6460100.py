from obs_lib import ob, tuile
tuile("917100_6460100")
H = "hors zone de travaux 2025"

ob("autre", "hors_emprise_description", (917125.0, 6460125.0), "absent_de_description", conf="haute", prec=25.0,
   attributs={"observe": "≈ 90 % de la dalle est hors de l'emprise décrite (x < 917129,4 ou y < 6460140) : Verdun SO 2×2 voies, allée de stationnement NO à marques en T, haie taillée, piste Chronovélo à bordure jaune, 2 candélabres à crosse (lanternes vers (917126.75, 6460135.5) et (917106.25, 6460114.1)), bosquet SE",
              "remarque": "à intégrer si l'emprise du simulateur est étendue vers le SO (continuité des marquages de Verdun)"},
   valide=True, raison=H)
ob("marquage", "hachures", (917130.0, 6460144.0), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"couleur": "blanc", "type": "triangle hachuré ≈ 4 × 2 m en bout d'allée de stationnement NO (même motif que 917169 / 6460189)",
              "autre_triangle_hors_emprise_l93": [917123.0, 6460142.5]},
   valide=True, raison=H)
ob("marquage", "ligne_discontinue", (917137.3, 6460142.41), "confirme", lien="ML-0926", conf="haute", prec=0.1, valide=True, raison=H)
