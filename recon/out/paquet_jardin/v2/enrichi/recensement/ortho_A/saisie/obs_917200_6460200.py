from obs_lib import ob, tuile
tuile("917200_6460200")

ob("marquage", "damier", (917205.5, 6460203.5), "absent_de_description", conf="haute", prec=0.5, preuve=True,
   attributs={"couleur": "blanc", "motif": "damier de carrés de 0,50 m, étendue ≈ (917198.5, 6460196.0) → (917209.0, 6460207.0), ≈ 12 × 3 m", "voie": "Verdun SO, chaussée SE : naissance de l'ancienne 3e voie (TAD vers Vercors)"},
   valide=False, raison="chaussée refaite en 2025 (surf_0323 modifie_2025 ; 3e voie supprimée, hist-09) : marquage 2022 très probablement effacé ; à ajouter aux fantômes, pas à fabriquer",
   note="continuité du damier vu en 917199,3 / 6460196,9 ; absent des fantômes v2 (MG-*)")
ob("mobilier", "banc", (917206.2, 6460240.5), "position_corrigee", lien="banc_8360664518", conf="moyenne", prec=0.3, preuve=True,
   attributs={"observe": "banc rouge ≈ 1,9 × 0,6 m sur la pelouse au NO de la piste, axe long // piste (cap ≈ 45°), assise tournée vers le SE",
              "ecart_a_la_description_m": 4.4, "position_decrite": [917209.5, 6460243.52]},
   valide="incertain", raison="pelouse hors chaussée mais surface voisine modifiée 2025 ; OSM 2026 le place 4,4 m plus au NE (déplacement ou imprécision OSM)")
ob("marquage", "logo_velo_piste", (917210.75, 6460240.7), "absent_de_description", conf="haute", prec=0.15,
   attributs={"couleur": "blanc", "type": "figurine vélo sur la piste bidirectionnelle NO (Chronovélo) + axe en tirets bleu clair et points"},
   valide="incertain", raison="piste surf_0321 « modifie_2025 » (redessinée au plan 2025) : marquages 2022 peut-être refaits")
ob("marquage", "lignes_stationnement_parking", (917234.0, 6460209.0), "absent_de_description", conf="moyenne", prec=1.0,
   attributs={"couleur": "blanc", "type": "places perpendiculaires des deux côtés de l'allée du parking SE (pas ≈ 2,5 m, longueur ≈ 5 m)",
              "decrit": "4 traits isolés seulement (ML-0160, ML-0164, ML-0170, ML-0233)", "etendue_l93": [[917226.0, 6460201.0], [917246.0, 6460219.0]]},
   valide="incertain", raison="parking surf_0300/0301 classé modifie_2025 ; traits de 2022 nets")
ob("arbre", "couronne", (917228.18, 6460213.23), "confirme", lien="arbre_093", conf="haute", prec=1.0, valide=True, raison="arbre existant hors chaussée")
ob("arbre", "conifere", (917237.81, 6460220.01), "confirme", lien="arbre_111", conf="haute", prec=0.5, valide=True, raison="arbre existant hors chaussée")
ob("arbre", "conifere", (917241.3, 6460223.76), "confirme", lien="arbre_112", conf="haute", prec=0.5, valide=True, raison="arbre existant hors chaussée")
