from obs_lib import ob, tuile
tuile("917150_6460350")
H = "hors zone de travaux 2025 (abords privés et allée de service inchangés)"

ob("mobilier", "blocs_rocheux", (917192.2, 6460378.0), "absent_de_description", conf="haute", prec=0.2, preuve=True,
   attributs={"nombre": 4, "dimension_m": "≈ 0,7–0,9", "observe": "blocs de pierre clairs posés sur les pelouses d'angle de l'allée de service (anti-stationnement)",
              "positions_l93": [[917191.25, 6460382.5], [917191.4, 6460380.25], [917194.0, 6460375.5], [917192.0, 6460374.0]]},
   valide=True, raison=H)
ob("tampon", "tampons_ronds_cour", (917156.4, 6460396.4), "absent_de_description", conf="moyenne", prec=0.2,
   attributs={"nombre": 3, "forme": "tampons ronds ≈ 0,6 m", "support": "cour de service enrobée à l'O (domaine privé)",
              "positions_l93": [[917154.5, 6460397.6], [917156.75, 6460396.25], [917157.9, 6460395.4]]},
   valide=True, raison=H)
ob("tampon", "tampon_rond", (917190.9, 6460397.15), "absent_de_description", conf="moyenne", prec=0.2,
   attributs={"forme": "anneau rond ≈ 0,6 m", "support": "parking NE"}, valide=True, raison=H)
ob("tampon", "regard_carre", (917178.25, 6460398.75), "absent_de_description", conf="faible", prec=0.2,
   attributs={"forme": "petit regard carré ≈ 0,4 m", "support": "trottoir du parking NE"}, valide=True, raison=H)
ob("avaloir", "grille", (917183.6, 6460387.9), "absent_de_description", conf="moyenne", prec=0.15,
   attributs={"forme": "grille rectangulaire ≈ 0,6 × 0,4 m", "support": "pied de bordure, parking NE"}, valide=True, raison=H)
ob("tampon", "disque_beton_clair", (917169.4, 6460380.0), "absent_de_description", conf="faible", prec=0.2,
   attributs={"forme": "disque clair ≈ 0,6 m au pied de l'angle du bâtiment (tampon béton ou socle)"}, valide=True, raison=H)
ob("mobilier", "coffret", (917163.6, 6460366.8), "absent_de_description", conf="faible", prec=0.3,
   attributs={"observe": "petit coffret clair ≈ 0,5 m en bord de pelouse, le long de l'allée de service"}, valide=True, raison=H)
ob("potelet", "potelet", (917192.4, 6460378.15), "position_corrigee", lien="potelet_12462947806", conf="faible", prec=0.3,
   attributs={"observe": "petit objet sombre ponctuel (potelet probable) à ≈ 2 m de la position OSM décrite"}, valide=True, raison=H)
