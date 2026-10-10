from obs_lib import ob, tuile
tuile("917300_6460200")

ob("marquage", "logo_velo_piste", (917300.8, 6460205.7), "absent_de_description", conf="haute", prec=0.15, preuve=True,
   attributs={"couleur": "blanc", "type": "figurine vélo sur la piste cyclable longeant le Vercors à l'ouest (sens du logo : vers le N)"},
   valide=True, raison="hors zone de travaux 2025 ; piste du Vercors inchangée à cet endroit")
ob("marquage", "ligne_continue", (917302.02, 6460229.19), "attribut_corrige", lien="ML-5406", conf="moyenne", prec=0.1,
   attributs={"decrit": "ligne continue GAM, etat « neuf_2025 »", "observe": "ligne continue présente en 05/2022 sur le même axe (contraste fort) ; voisine ML-5401 « refait_2025_identique » également confirmée", "etat_propose": "refait_2025_identique", "liens_voisins": ["ML-5401", "ML-5399"]},
   valide=True, raison="levé GAM 2026 ; géométrie inchangée depuis 2022")
ob("marquage", "fleche_tag", (917301.0, 6460239.5), "attribut_corrige", lien="MF-5525", conf="moyenne", prec=0.3,
   attributs={"decrit": "flèche GAM SYMBOLE_FLECHE_GAUCHE, etat « neuf_2025 »", "observe": "flèche TAG déjà présente en 05/2022 dans la voie de gauche, à ≈ 0,2 m de la pose", "etat_propose": "refait_2025_identique"},
   valide=True, raison="levé GAM 2026 ; position identique à 2022")
ob("mobilier", "poteau_incendie_probable", (917311.5, 6460246.5), "incertain", lien="poteau_incendie_5948977094", conf="faible", prec=0.3,
   attributs={"observe": "objet rouge ≈ 0,4 m avec ombre (h ≈ 1 m) en bord de chantier, à 8,4 m au N de la position OSM (917309.77, 6460238.24) qui est sous l'ombre d'un arbre",
              "hypothese": "poteau incendie (ou cône de chantier)"},
   valide="incertain", raison="abords du chantier des Saules Blancs (2022) : surface modifiée depuis")
