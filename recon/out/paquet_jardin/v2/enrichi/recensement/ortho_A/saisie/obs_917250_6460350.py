from obs_lib import ob, tuile
tuile("917250_6460350")
H = "cour de résidence hors zone de travaux 2025"

ob("arbre", "feuillage_pourpre", (917274.75, 6460384.75), "absent_de_description", conf="haute", prec=0.5, preuve=True,
   attributs={"observe": "arbre à feuillage pourpre (prunus / hêtre pourpre probable), couronne ≈ 3 m, au milieu de la pelouse de la cour"},
   valide=True, raison=H)
ob("arbre", "feuillu", (917273.5, 6460387.6), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"observe": "arbre vert foncé, couronne ≈ 3,5 m, accolé au précédent"}, valide=True, raison=H)
ob("arbre", "arbustes_boules", (917282.0, 6460391.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"observe": "arbustes taillés en boules (≈ 1–1,5 m) le long de la façade SO de l'immeuble", "positions_l93": [[917276.0, 6460392.5], [917279.0, 6460389.5], [917281.0, 6460387.0], [917284.5, 6460383.0]]},
   valide=True, raison=H)
ob("mobilier", "bancs", (917268.0, 6460386.5), "absent_de_description", conf="haute", prec=0.3,
   attributs={"nombre": 4, "observe": "bancs bois ≈ 1,8 × 0,6 m le long des allées de la cour",
              "positions_l93": [[917259.0, 6460395.25], [917264.25, 6460390.0], [917270.5, 6460384.0], [917278.0, 6460376.75]]},
   valide=True, raison=H)
ob("candelabre", "borne_lumineuse_globe", (917278.0, 6460380.85), "absent_de_description", conf="moyenne", prec=0.3,
   attributs={"observe": "lanterne à globe blanc sur mât court (ombre ≈ 1,5 m : h ≈ 3 m) au bord de l'allée", "autre_position_l93": [917255.25, 6460386.5]},
   valide=True, raison=H)
ob("autre", "aire_de_jeux", (917260.0, 6460378.0), "absent_de_description", conf="moyenne", prec=2.0,
   attributs={"observe": "aire de jeux sur sable (≈ 15 × 12 m) avec bac à sable, jeux et clôture basse ; abri à toit rouge (≈ 5 × 2,5 m) à l'O"},
   valide=True, raison=H)
