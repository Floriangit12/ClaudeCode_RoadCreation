# 917300_6460250 : angle SE, chantier des Saules Blancs (mai 2022) et rive E de Vercors
o(T, 650, 450, "autre", "chantier_2022", "incertain", "haute", None,
  "en mai 2022, toute la moitié E de la dalle est un chantier (sol nu, gravier, piste de chantier, matériaux) : la desserte du quartier (S-0430, S-0431), ses bordures (K-0592, K-0595, K-0600, K-0609, K-0612), ses dents de requin (MS-0379 à MS-0384) et les potelets OSM 13827066657/658 sont postérieurs à l'image : non vérifiables par l'ortho",
  a={"liens": ["S-0429a", "S-0430a", "S-0431f", "MS-5120", "MS-5132", "potelet_13827066657", "potelet_13827066658"]},
  bb=[450, 0, 1000, 1000], pr=True, vt=400)
o(T, 607.8, 223.0, "arbre", "jeune_arbre", "absent_sur_image", "haute", "arbre_226",
  "aucun des 9 arbres « h 5 m, couronne 2,5 m » de la dalle (arbre_198, 199, 200, 210, 217, 218, 225, 226, 232) n'existe en mai 2022 (sol nu de chantier) : plantations postérieures, absence normale ; hauteur 5 m à vérifier (arbres de 2 à 4 ans)",
  a={"liens": ["arbre_198", "arbre_199", "arbre_200", "arbre_210", "arbre_217", "arbre_218", "arbre_225", "arbre_226", "arbre_232"]},
  va=(False, "plantations postérieures à l'image (secteur construit 2023-2024)"))
o(T, 540, 250, "surface", "enrobe_desserte", "attribut_corrige", "moyenne", "S-0429a",
  "la chaussée de la desserte n'existe pas en mai 2022 (piste de chantier) : enrobé posé en 2023-2024, « enrobe_bbsg_ancien » à remplacer par un enrobé récent (2 à 3 ans) ; idem S-0430a et S-0431b/c",
  a={"materiau_propose": "enrobe_bbsg_recent_2023", "liens": ["S-0429a", "S-0430a", "S-0431b", "S-0431c"]},
  va=(True, "déduction de date : chaussée postérieure à mai 2022, donc récente en 2026"))
o(T, 90, 840, "cloture", "cloture_chantier_ou_definitive", "confirme", "moyenne", "cloture_gam_043",
  "clôture avec ombre continue le long du trottoir E de Vercors dès 2022 (alors clôture de chantier) ; tracé conforme à la couche",
  geom=[[45, 680], [130, 1000]])
o(T, 10, 342, "candelabre", "lampadaire", "confirme", "faible", "lamp_lidar_VERC_E", "tête ovale claire en bord de dalle au point LiDAR (houppier voisin) ; présent en 2022")
