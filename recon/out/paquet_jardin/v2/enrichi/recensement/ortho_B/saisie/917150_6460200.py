# 917150_6460200 : parking du P+R / jardinerie, bassins, friche, rive NO de Verdun SO
o(T, 585, 160, "surface", "bassin_eau", "attribut_corrige", "haute", "S-0161a",
  "plan d'eau (bassin d'agrément ou de rétention, eau brune) d'≈350 m² bordé d'un enrochement de galets / blocs gris sur sa rive NE ; décrit en v0.3 comme PARKING en enrobé (S-0161a ; en v1 surf_0043 espace vert) : surface en eau absente de la description",
  a={"materiau_propose": "eau_bassin + enrochement", "aire_estimee_m2": 350}, bb=[515, 70, 690, 260], vt=260)
o(T, 300, 140, "surface", "bassin_ombrage", "incertain", "faible", "S-0161a",
  "zone très sombre et uniforme sous les conifères (≈11 x 9 m), au contour de bassin : second plan d'eau ombragé probable ; inclus dans le parking S-0161a (v0.3)",
  bb=[195, 40, 420, 240], vt=260)
o(T, 772, 119, "candelabre", "lampadaire", "absent_sur_image", "moyenne", "lamp_12887274334",
  "le point décrit tombe sur un buis taillé en boule dans la jardinière du parking ; aucune ombre de mât autour en 2022 (nœud OSM 2025)")
o(T, 150, 800, "surface", "friche", "attribut_corrige", "moyenne", "S-0161a",
  "terrain en terre nue avec dépôts et un abri blanc ≈3 x 1,5 m (mai 2022), décrit en v0.3 comme parking (S-0161a) ; état 2026 inconnu",
  bb=[60, 640, 340, 1000], vt=360, va=("incertain", "terrain privé susceptible d'avoir changé depuis 2022"))
o(T, 720, 400, "marquage", "lignes_places_parking", "confirme", "haute", "ML-0216",
  "traits de places du parking du P+R décrits et superposés à la peinture (couverture 0,76 à 1,00 ; ML-0134 et ML-0219 de la v0.2 retirés en v0.3)",
  a={"liens": ["ML-0125", "ML-0126", "ML-0128", "ML-0136", "ML-0137", "ML-0139", "ML-0214", "ML-0215", "ML-0216", "ML-0217", "ML-0218"]})
o(T, 700, 800, "marquage", "places_en_epi_contre_allee", "absent_de_description", "moyenne", None,
  "places en épi le long de l'allée de stationnement NO de Verdun (traits blancs obliques, voitures garées) entre la bande plantée et la chaussée : traits non décrits ; allée conservée à l'O de u ≈ -83 (OSM 1464893892)",
  bb=[560, 600, 920, 1000], vt=420, va=("incertain", "allée conservée selon OSM, marquage des places non revu après 2025"))
o(T, 896, 41, "tampon", "regard_carre", "absent_de_description", "haute", None, "regard carré ≈1 m (dalle plus sombre) dans l'allée du parking du P+R", af="sombre", r=10)
o(T, 450, 420, "surface", "surface_fourre_tout", "attribut_corrige", "haute", "S-0161a",
  "S-0161a (parking enrobé, 11 047 m², pureté de classe 0,41) englobe sur cette dalle deux plans d'eau, le bosquet de conifères (a108, a139-a143), des pelouses et massifs arbustifs (érables pourpres au NO), la friche SO et la haie du parking ; ≈580 m² de végétation et ≈720 m² seulement de revêtement clair sur 1 930 m² vus : polygone à découper (limites de revêtement manquantes)",
  a={"aire_vue_m2": 1934, "vegetation_m2": 583, "revetement_clair_m2": 717, "composantes": ["parking", "bassin_eau x2", "bosquet_coniferes", "pelouse", "massif_arbustif", "friche", "haie"]},
  bb=[0, 0, 1000, 1000], vt=700, pr=True)
