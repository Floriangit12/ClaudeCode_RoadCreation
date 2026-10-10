from obs_lib import ob, tuile
tuile("917300_6460400")
H = "parc hors zone de travaux 2025"

ob("arbre", "cedre_absent", (917331.15, 6460422.67), "absent_sur_image", lien="arbre_435", conf="moyenne", prec=1.0, preuve=True,
   attributs={"decrit": "Cedrus atlantica, h 20,9 m, couronne 8,8 m (GAM)", "observe": "pelouse ouverte (en partie à l'ombre des arbres voisins au NO) sans couronne de conifère à la position ; un cèdre de 21 m aurait une couronne sombre de ≈ 9 m bien visible",
              "hypothese": "bloc GAM mal placé ou confusion avec arbre_449 / arbre_433 voisins"},
   valide="incertain", raison="un cèdre de cette taille ne peut pas avoir été planté après 2022 : position ou existence à vérifier sur photo")
ob("arbre", "abattu_confirme", (917339.94, 6460408.62), "confirme", lien="arbre_423", conf="moyenne", prec=0.5,
   attributs={"observe": "pas de couronne en 2022 (pelouse), cohérent avec « abattu »"}, valide=True, raison=H)
ob("arbre", "abattu_confirme", (917184.84, 6460380.19), "confirme", lien="arbre_365", conf="moyenne", prec=0.5, tuile="917150_6460350",
   attributs={"observe": "pas de couronne en 2022 (pelouse et ombre d'un mât), cohérent avec « abattu »"}, valide=True, raison=H)
ob("arbre", "present_2022", (917162.03, 6460369.15), "incertain", lien="arbre_341", conf="faible", prec=1.0, tuile="917150_6460350",
   attributs={"observe": "couronne feuillue présente en 05/2022 à la position (aubépine) alors que l'inventaire la dit abattue : abattage postérieur à 2022 ou erreur d'inventaire"},
   valide="incertain", raison="abattage éventuel postérieur à la prise de vue")
ob("autre", "anneaux_sombres_pelouse", (917337.9, 6460402.4), "absent_de_description", conf="faible", prec=0.3,
   attributs={"observe": "deux anneaux sombres ≈ 1,6 m dans la pelouse (souches arasées ou anciennes cuvettes d'arbres)", "positions_l93": [[917336.0, 6460403.0], [917339.75, 6460401.75]]},
   valide=True, raison=H)
