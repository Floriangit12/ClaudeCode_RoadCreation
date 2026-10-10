from obs_lib import ob, tuile
tuile("917150_6460150")
H = "hors zone de travaux 2025 (surfaces inchangées 2022)"

ob("marquage", "damier", (917159.4, 6460154.9), "absent_de_description", conf="haute", prec=0.3, preuve=True,
   attributs={"couleur": "blanc", "motif": "damier en quinconce de carrés de 0,50 m", "emprise_m": [5.5, 2.5],
              "orientation": "rangées parallèles à l'axe de Verdun (cap ≈ 45°)", "voie": "chaussée SE de Verdun SO (sens SO→NE), au droit du nez de l'îlot à galets",
              "usure": "moyenne (2022)"},
   valide="incertain", raison="hors travaux 2025 mais absent du levé GAM 2026 (signalisation horizontale) : à confirmer sur photo",
   note="absent de marquages_2026 v1 et de la description v2 ; se prolonge vers le SO sous l'ombre de l'arbre (≈ 917155, 6460151)")
ob("mobilier", "bloc_rocheux_alignement", (917179.7, 6460165.0), "absent_de_description", conf="haute", prec=0.2, preuve=True,
   attributs={"nombre": 13, "pas_m": 3.0, "dimension_m": "≈ 0,6–0,8 (blocs calcaires gris clair)", "implantation": "sur la bande enherbée, à ≈ 0,3–0,5 m du bord de l'allée de desserte SE (anti-stationnement)",
              "positions_l93": [[917167.7, 6460153.0], [917169.9, 6460155.2], [917172.1, 6460157.4], [917174.3, 6460159.6],
                                [917176.4, 6460161.9], [917178.6, 6460164.1], [917180.8, 6460166.4], [917182.9, 6460168.6],
                                [917185.0, 6460170.8], [917186.7, 6460172.6], [917188.9, 6460174.6], [917190.7, 6460176.5], [917191.5, 6460175.9]]},
   valide=True, raison=H, note="aucune famille « blocs / rochers » dans mobilier.geojson ni dans la description")
ob("ilot", "remplissage_galets", (917166.5, 6460158.4), "attribut_corrige", lien="surf_0343", conf="haute", prec=0.5, preuve=True,
   attributs={"materiau_decrit": "enrobe", "materiau_observe": "galets / pierres roulées gris clair (≈ 5–15 cm) en lit continu, sans végétation",
              "bordures": "ceinture béton gris (KS-0118-1, KS-0124-1, KS-0295)", "nez": [917163.0, 6460155.8]},
   valide=True, raison=H, note="extrémité SO de l'îlot séparateur Verdun / allée de desserte SE ; l'extrémité NE (917190–917200, 6460183–6460193) porte le même lit de galets, la partie centrale est une bande enherbée avec haie basse")
ob("ilot", "remplissage_galets", (917196.0, 6460189.5), "attribut_corrige", lien="surf_0343", conf="haute", prec=0.5,
   attributs={"materiau_decrit": "enrobe", "materiau_observe": "galets / pierres gris clair", "bordures": "KS-0298-1, KS-0300-1 (béton gris)"},
   valide=True, raison=H)
ob("massif", "haie_basse_arbustes_tailles", (917172.0, 6460186.0), "attribut_corrige", lien="surf_0328", conf="moyenne", prec=1.0,
   attributs={"materiau_decrit": "herbe (terre_plein_vegetal)", "observe": "bande plantée d'arbustes taillés en masses (≈ 1,0–1,5 m, ombres portées ≈ 1 m) entre l'allée de stationnement NO et Verdun",
              "etendue_l93": [[917152.0, 6460171.0], [917183.0, 6460200.0]]},
   valide=True, raison=H)
ob("marquage", "t_stationnement", (917157.8, 6460173.8), "absent_de_description", conf="haute", prec=0.2, preuve=True,
   attributs={"couleur": "blanc", "type": "marques en T de stationnement longitudinal (bord SE de l'allée de stationnement NO)", "pas_m": 5.3,
              "positions_l93": [[917152.2, 6460168.2], [917156.1, 6460171.8], [917159.7, 6460175.8], [917163.4, 6460179.4]]},
   valide=True, raison=H, note="une seule marque en T (MZ-0996) existe dans la description, hors dalle")
ob("marquage", "lignes_stationnement", (917176.3, 6460195.9), "absent_de_description", conf="moyenne", prec=0.3,
   attributs={"couleur": "blanc", "type": "traits de séparation de places (stationnement longitudinal)", "positions_l93": [[917174.7, 6460194.25], [917177.9, 6460197.6]]},
   valide=True, raison=H)
ob("marquage", "hachures", (917169.0, 6460189.2), "absent_de_description", conf="moyenne", prec=0.5, preuve=True,
   attributs={"couleur": "blanc", "type": "zone hachurée triangulaire en bout de stationnement (≈ 4 × 2 m)"}, valide=True, raison=H)
ob("marquage", "hachures", (917169.0, 6460183.8), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"couleur": "blanc", "type": "zone hachurée triangulaire en bout de stationnement (≈ 4 × 2 m), au pied du candélabre lamp_9514794919"},
   valide=True, raison=H)
ob("tampon", "regard_carre", (917175.24, 6460184.83), "absent_de_description", conf="haute", prec=0.15, preuve=True,
   attributs={"forme": "cadre carré ≈ 0,9 m avec tampon rond fonte", "support": "chaussée de Verdun SO, voie NO, à ≈ 0,8 m de la bordure (KS-0676-1)"},
   valide=True, raison=H)
ob("tampon", "regard_petit", (917186.46, 6460157.9), "absent_de_description", conf="faible", prec=0.3,
   attributs={"forme": "petit carré sombre ≈ 0,3 m (bouche à clé ou regard)", "support": "angle du parking SE"}, valide=True, raison=H)
ob("tampon", "regard_rond", (917197.58, 6460156.5), "absent_de_description", conf="moyenne", prec=0.15,
   attributs={"forme": "disque gris clair ≈ 0,5 m", "support": "pelouse au pied du bâtiment (domaine privé probable)"}, valide=True, raison=H)
ob("marquage", "ligne_axe_discontinue", (917182.6, 6460169.6), "attribut_corrige", lien="ML-0212", conf="haute", prec=0.2, preuve=True,
   geom=[(917173.3, 6460160.0), (917192.0, 6460179.3)],
   attributs={"decrit": "segment continu de 4,86 m", "observe": "ligne d'axe discontinue (tirets ≈ 1 m) sur ≈ 27 m le long de l'allée de desserte SE",
              "modulation": "tirets courts (T'1 probable)"},
   valide=True, raison=H)
ob("marquage", "ligne_discontinue_stationnement", (917189.6, 6460162.2), "absent_de_description", conf="haute", prec=0.2,
   geom=[(917184.08, 6460159.17), (917195.08, 6460165.17)],
   attributs={"couleur": "blanc", "type": "ligne discontinue de fond de places (parking SE)", "modulation": "tirets ≈ 0,5 m / 0,5 m"},
   valide=True, raison=H, note="seuls des traits de séparation isolés (ML-0131, ML-0133, ML-0213) sont décrits")
ob("candelabre", "tete_lanterne", (917168.54, 6460176.71), "confirme", lien="lamp_9514794919", conf="moyenne", prec=0.3,
   attributs={"observe": "lanterne visible au-dessus de la chaussée, à ≈ 3,1 m du mât décrit (azimut ≈ 139°) : crosse orientée vers Verdun",
              "porte_a_faux_decrit_m": 1.5, "porte_a_faux_observe_m": "≈ 3 (tête – mât)"},
   valide=True, raison=H, note="pied du mât masqué par la haie ; porte-à-faux sous-estimé dans la description")
ob("candelabre", "tete_lanterne", (917188.2, 6460197.0), "confirme", lien="lamp_9514795121", conf="moyenne", prec=0.3,
   attributs={"observe": "lanterne au-dessus de la chaussée, à ≈ 3,5 m du mât décrit (917186.55, 6460199.55), crosse vers le SE", "porte_a_faux_decrit_m": 1.5},
   valide=True, raison=H)
ob("autre", "objet_vertical_blanc", (917195.1, 6460173.7), "absent_de_description", conf="faible", prec=0.3,
   attributs={"observe": "objet blanc allongé ≈ 1 × 0,4 m vu de dessus au nez du triangle enherbé, ombre ≈ 2,7 m vers le NNO (hauteur ≈ 2,5–3 m)",
              "hypothese": "panneau ou panonceau d'entrée de parking sur poteau"}, valide=True, raison=H)
ob("arbre", "arbustes_conifères", (917195.0, 6460154.0), "absent_de_description", conf="moyenne", prec=0.5,
   attributs={"nombre": 4, "hauteur_estimee_m": "2–4 (ombres)", "positions_l93": [[917193.3, 6460156.2], [917194.1, 6460154.2], [917198.1, 6460153.7], [917193.8, 6460151.7]],
              "support": "pelouse privée au pied du bâtiment"}, valide=True, raison=H)
ob("arbre", "absent_2022", (917182.45, 6460162.77), "absent_sur_image", lien="arbre_022", conf="moyenne", prec=0.5,
   attributs={"observe": "pelouse sans couronne à la position en 05/2022"},
   valide="incertain", raison="arbre levé au GAM (récolement), « jeune ou planté après 2021 » : planté après la prise de vue 2022 probable")
ob("arbre", "couronne", (917156.86, 6460180.43), "confirme", lien="arbre_047", conf="haute", prec=0.5, valide=True, raison=H)
ob("arbre", "couronne", (917166.35, 6460190.57), "confirme", lien="arbre_063", conf="haute", prec=0.5, valide=True, raison=H)
ob("marquage", "ligne_rive_usee", (917156.3, 6460161.1), "confirme", lien="ML-0939", conf="moyenne", prec=0.1, preuve=True,
   attributs={"observe": "ligne discontinue ancienne très usée, doublant à ≈ 0,45 m la ligne ML-6203 (ex ML-0938, tirets nets) : deux lignes parallèles",
              "usure": "forte (3)"},
   valide=True, raison=H, note="faible contraste automatique (tirets très effacés) mais présente")

ob("marquage", "ligne_continue", (917176.14, 6460178.15), "attribut_corrige", lien="ML-5158", conf="moyenne", prec=0.1,
   attributs={"decrit": "ligne continue GAM, etat « neuf_2025 »", "observe": "ligne continue présente en 05/2022 sur le même axe (contraste fort, décalage < 0,05 m), hors zone de travaux 2025", "etat_propose": "conserve"},
   valide=True, raison="hors zone de travaux 2025 ; levé GAM 2026")
