from obs_lib import ob, tuile
tuile("917250_6460150")
H = "hors zone de travaux 2025 (parking des Mitaillères inchangé)"

ob("marquage", "zone_jaune_croix", (917252.1, 6460176.5), "absent_de_description", conf="haute", prec=0.3, preuve=True,
   attributs={"couleur": "jaune", "type": "rectangle ≈ 4,5 × 2,8 m bordé de jaune avec croix de Saint-André (emplacement interdit / livraison) devant l'accès piéton du bâtiment",
              "orientation": "grand côté au cap ≈ 45°"},
   valide=True, raison=H)
ob("avaloir", "grille", (917256.4, 6460181.6), "absent_de_description", conf="moyenne", prec=0.15,
   attributs={"forme": "grille à barreaux ≈ 0,6 × 0,4 m", "support": "allée piétonne d'accès au bâtiment (ombre portée)"}, valide=True, raison=H)
ob("avaloir", "grille", (917253.0, 6460173.1), "absent_de_description", conf="moyenne", prec=0.2,
   attributs={"forme": "grille sombre ≈ 0,9 × 0,7 m", "support": "fond de place de stationnement, parking O"}, valide=True, raison=H)
ob("tampon", "petit_regard", (917254.5, 6460159.75), "absent_de_description", conf="faible", prec=0.2,
   attributs={"forme": "petit disque sombre ≈ 0,3 m", "support": "enrobé du parking"}, valide=True, raison=H)
ob("mobilier", "conteneurs_dechets", (917260.6, 6460154.6), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"observe": "aire de conteneurs : 2 bacs roulants noirs + 1 bac jaune/brun contre la haie, au bout des places", "nombre": 3}, valide=True, raison=H)
ob("autre", "escalier_garde_corps", (917251.9, 6460162.6), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"observe": "volée de marches avec garde-corps métalliques entre le parking et le bâtiment (≈ 4 × 2 m)",
              "source_possible": "gam_topo_sol_escalier_rampe_lin"}, valide=True, raison=H)
ob("panneau", "ombre_disque", (917259.8, 6460157.5), "incertain", lien="pan_B6a1_2", conf="faible", prec=1.0,
   attributs={"observe": "ombre d'un disque sur poteau en (917258.75, 6460159.55) : poteau probable à l'angle de la haie, à ≈ 6–7 m de la position décrite (917263.55, 6460163.8)"},
   valide=True, raison=H)
ob("marquage", "ligne_place_masquee", (917283.4, 6460158.49), "incertain", lien="ML-5340", conf="moyenne", prec=0.3,
   attributs={"observe": "trait de place masqué par un véhicule stationné (contraste nul) ; traits voisins ML-5341..ML-5344 visibles"}, valide=True, raison=H)
