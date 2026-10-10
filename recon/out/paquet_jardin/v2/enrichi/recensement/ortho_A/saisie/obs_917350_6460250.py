from obs_lib import ob, tuile
tuile("917350_6460250")

ob("autre", "chantier_2022", (917375.0, 6460275.0), "absent_sur_image", conf="haute", prec=25.0, preuve=True,
   attributs={"observe": "dalle entière occupée en 05/2022 par le chantier des Saules Blancs (bâtiment en gros œuvre, grue à tour, stocks de ferraillage) : aucun élément de voirie ou de végétation de l'état 2026 n'est visible",
              "entites_non_verifiables": "arbres jeunes de la dalle (arbre_186–222 « jeunes ou plantés après 2021 »), surfaces construit_2023_2024"},
   valide=False, raison="état 2022 de chantier, sans rapport avec l'état 2026 ; ne pas utiliser l'ortho 2022 sur cette dalle")
