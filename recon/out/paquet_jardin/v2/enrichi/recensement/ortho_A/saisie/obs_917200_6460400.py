from obs_lib import ob, tuile
tuile("917200_6460400")
H = "jardin privé et cour de résidence hors zone de travaux 2025"

ob("arbre", "grand_feuillu", (917235.5, 6460417.0), "absent_de_description", conf="haute", prec=1.0, preuve=True,
   attributs={"observe": "grand feuillu à couronne dense ≈ 11 × 14 m (deux lobes, ombre portée longue vers le NO) au centre du jardin privé ; aucune entité arbre à moins de 7 m",
              "hauteur_estimee_m": "12–15 (ombre)"},
   valide=True, raison=H, note="les arbres LiDAR « sommet du MNH » couvrent les voisins (a446, a415) mais pas celui-ci")
ob("arbre", "souche_ou_massif", (917221.2, 6460413.4), "absent_de_description", conf="moyenne", prec=0.3,
   attributs={"observe": "tache claire ronde ≈ 1,2 m (souche fraîchement coupée ou paillage au pied d'un arbuste) dans la pelouse"},
   valide=True, raison=H)
ob("mobilier", "objet_rouge", (917222.8, 6460434.0), "absent_de_description", conf="faible", prec=0.3,
   attributs={"observe": "objet orange-rouge ≈ 0,5 m dans le jardin (mobilier de jardin)"}, valide=True, raison=H)
ob("candelabre", "borne_globe", (917240.5, 6460433.5), "absent_de_description", conf="faible", prec=0.5,
   attributs={"observe": "globe blanc sur mât court au bord de l'allée de la résidence"}, valide=True, raison=H)
ob("arbre", "couronne", (917224.0, 6460407.0), "confirme", lien="arbre_415", conf="moyenne", prec=1.0, valide=True, raison=H)
ob("arbre", "couronne", (917214.2, 6460406.5), "confirme", lien="arbre_414", conf="moyenne", prec=1.0,
   attributs={"observe": "petit arbre peu feuillu (branches visibles) à la position décrite"}, valide=True, raison=H)
