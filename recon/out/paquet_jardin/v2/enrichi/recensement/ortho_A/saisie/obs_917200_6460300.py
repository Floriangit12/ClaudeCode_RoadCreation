from obs_lib import ob, tuile
tuile("917200_6460300")
H = "hors zone de travaux 2025 (parking de la jardinerie inchangé)"

for mid, xy in [("ML-0161", (917234.23, 6460320.11)), ("ML-0162", (917235.36, 6460320.79)), ("ML-0163", (917236.9, 6460322.01)),
                ("ML-0168", (917239.47, 6460322.91))]:
    ob("marquage", "faux_positif_portail", xy, "absent_sur_image", lien=mid, conf="haute", prec=0.2, preuve=(mid == "ML-0161"),
       attributs={"observe": "pas de peinture : l'entité suit les barreaux blancs du portail coulissant de la jardinerie (917232–917241, 6460320–6460329) ou les jours clairs en arc de son ombre portée",
                  "decision_v03": "confirme ortho2022 (à tort)", "action_proposee": "retirer du marquage (comme MZ-0251..0253, déjà retirés en v0.3) ; modéliser un portail coulissant blanc (≈ 9 m, barreaux en croix et arcs) fermant l'accès du parking"},
       valide=False, raison="artefact de vectorisation de l'ortho 2022 (aucun marquage réel)")
ob("cloture", "portail_coulissant", (917236.0, 6460325.0), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"observe": "portail métallique blanc à deux vantaux/coulissant ≈ 9 m (cadre, croisillons, arcs), ouvert en 05/2022, travers l'allée du parking côté Revirée",
              "geometrie_l93_approx": [[917233.0, 6460320.5], [917241.0, 6460329.0]]},
   valide=True, raison=H, note="vérifier s'il correspond à l'un des 8 « portail » de mobilier.geojson (aucun à moins de 2 m)")
ob("marquage", "places_parking_jardinerie", (917228.0, 6460318.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"observe": "≈ 20 places perpendiculaires (traits blancs, pas ≈ 2,5 m, longueur ≈ 5 m) le long de la façade NE du bâtiment et ≈ 10 places côté Revirée",
              "etendue_l93": [[917221.0, 6460302.0], [917249.0, 6460338.0]], "decrit": "aucun trait de place (seules des entités fausses au portail)"},
   valide=True, raison=H)
ob("tampon", "regard_rectangulaire", (917244.5, 6460331.9), "absent_de_description", conf="moyenne", prec=0.15,
   attributs={"forme": "grille / regard rectangulaire sombre ≈ 1,0 × 0,6 m", "support": "trottoir de la Revirée (O), contre la bordure KS-0259-1"},
   valide=True, raison=H)
ob("mobilier", "coffret_ou_borne", (917242.5, 6460332.1), "absent_de_description", conf="faible", prec=0.3,
   attributs={"observe": "petit coffret gris ≈ 0,6 × 0,5 m avec élément noir, ombre courte (h ≈ 0,8–1 m), dans la bande enherbée"},
   valide=True, raison=H)
ob("mobilier", "poteau_incendie", (917239.5, 6460338.9), "confirme", lien="poteau_incendie_4537565593", conf="moyenne", prec=0.3,
   attributs={"observe": "petit objet rouge au bord de l'îlot enherbé d'entrée du parking"}, valide=True, raison=H)
