from obs_lib import ob, tuile
tuile("917200_6460100")
H = "parking des Mitaillères hors zone de travaux 2025"

ob("surface", "places_revetement_vert_gris", (917212.0, 6460142.0), "attribut_corrige", lien="surf_0153", conf="moyenne", prec=1.0, preuve=True,
   attributs={"materiau_decrit": "enrobe", "observe": "les bandes de places sont revêtues d'un matériau vert-gris à grain fin (enrobé teinté / béton drainant), cerné de bordurettes béton blanches ; allées en enrobé gris ; les « lignes » de places sont de simples joints sombres",
              "materiau_propose": "enrobe_colore_vert_gris (places) + enrobe (allées)"},
   valide=True, raison=H)
ob("ilot", "remplissage_galets", (917218.0, 6460140.0), "attribut_corrige", lien="surf_0153", conf="haute", prec=0.5,
   attributs={"observe": "îlot triangulaire entre deux rangées de places rempli de cailloux gris-bleu grossiers (≈ 5–10 cm), bordurettes béton blanches, pointe N enherbée avec un petit arbre",
              "materiau_propose": "galets_20_40 / cailloux concassés"}, valide=True, raison=H)
ob("arbre", "petit_arbre", (917215.5, 6460148.5), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"observe": "petit arbre (couronne ≈ 2,5 m) à la pointe enherbée de l'îlot"}, valide=True, raison=H)
ob("autre", "hors_emprise_description", (917225.0, 6460118.0), "absent_de_description", conf="haute", prec=20.0,
   attributs={"observe": "partie S hors emprise (y < 6460140) : allée des Mitaillères avec axe discontinu, 2 barrières levantes blanches, candélabres, tampon rond sur chaussée vers (917217.15, 6460118.35), platane taillé en tête de chat, maison et jardin"},
   valide=True, raison=H)
