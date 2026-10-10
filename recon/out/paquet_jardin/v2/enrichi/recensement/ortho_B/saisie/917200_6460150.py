# 917200_6460150 : parking en terrasse (toit d'un commerce), allée piétonne des Mitaillères
for _l, _u, _v in (("lamp_13539939799", 521, 583), ("lamp_13539946625", 735, 794), ("lamp_13539950055", 628, 688),
                   ("lamp_ortho_parking_terrasse_NO", 412, 480)):
    o(T, _u, _v, "candelabre", "lampadaire_terrasse", "confirme", "haute", _l,
      "pied au bord de la jardinière NO de la terrasse et ombre de mât vers le NNO")
o(T, 352, 365, "candelabre", "lampadaire_terrasse", "absent_sur_image", "moyenne", "lamp_13539965051",
  "au point décrit (extrémité NO de la terrasse) une voiture est garée et aucune ombre de mât ne dépasse : pas de candélabre en 2022 (nœud OSM récent : position à vérifier)")
o(T, 560, 600, "marquage", "lignes_places_terrasse", "absent_de_description", "moyenne", None,
  "traits de places fins et effacés (usure 2-3) le long des jardinières SO et NE de la terrasse : non décrits (seuls les traits du parking bas NE le sont)",
  bb=[380, 300, 930, 900], vt=500, a={"usure": "2-3"})
o(T, 243, 949, "tampon", "regard_carre", "absent_de_description", "haute", None, "regard carré ≈0,5 m sur le cheminement au pied d'un candélabre", af="sombre", r=8)
o(T, 78, 254, "surface", "massif_en_trottoir", "attribut_corrige", "moyenne", "S-0071b",
  "S-0071b (trottoir, enrobé, 3,6 m²) tombe dans un massif arbustif dense au bord du cheminement : végétation, pas d'enrobé",
  a={"materiau_propose": "massif"})
