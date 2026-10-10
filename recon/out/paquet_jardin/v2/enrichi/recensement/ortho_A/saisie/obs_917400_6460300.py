from obs_lib import ob, tuile
tuile("917400_6460300")
C = "terrain de chantier en 05/2022 (Saules Blancs) : sol non valable pour 2026"

ob("arbre", "couronne", (917423.0, 6460318.0), "confirme", lien="arbre_270", conf="haute", prec=1.0,
   attributs={"observe": "feuillu conservé au bord du chantier, couronne ≈ 9 × 10 m"}, valide=True, raison="arbre existant levé au GAM")
ob("arbre", "couronne", (917430.5, 6460341.5), "confirme", lien="arbre_301", conf="moyenne", prec=1.0,
   attributs={"observe": "couronne ≈ 9 m à 2,4 m à l'E du sommet LiDAR décrit (917428.18, 6460341.73)"}, valide=True, raison="arbre de la prairie E, hors chantier")
ob("arbre", "absent_2022", (917414.03, 6460321.53), "absent_sur_image", lien="arbre_269", conf="moyenne", prec=0.5,
   attributs={"decrit": "feuillu existant h 3,8 m, couronne 9,8 m", "observe": "terre nue de chantier à la position en 05/2022 (hors de la couronne de arbre_270)"},
   valide="incertain", raison="planté après 2022 possible (zone de chantier) ; diamètre de couronne 9,8 m incohérent avec h 3,8 m")
ob("autre", "chantier_2022", (917412.0, 6460325.0), "absent_sur_image", conf="haute", prec=20.0,
   attributs={"observe": "terrassement, stocks de gravats et de ferraillage, clôture de chantier le long de la prairie E (x ≈ 917425–917434)"},
   valide=False, raison=C)
