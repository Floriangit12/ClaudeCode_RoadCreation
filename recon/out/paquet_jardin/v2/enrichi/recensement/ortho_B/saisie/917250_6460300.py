# 917250_6460300 : angle N du carrefour (Revirée / Verdun NE), jardin Paquet Jardin
o(T, 917.5, 726, "candelabre", "mat_a_crosse", "attribut_corrige", "moyenne", "lamp_9665416817",
  "deux lanternes ovales blanches vues de dessus : (895,710) côté trottoir et (940,742) au-dessus de la chaussée, écartées de 2,8 m perpendiculairement à Verdun ; la couche donne nb_crosses 1",
  a={"nb_lanternes_vues": 2, "lanterne_1_px": [895, 710], "lanterne_2_px": [940, 742], "nb_crosses_propose": 2}, p=0.5, pr=True)
o(T, 906.3, 721.0, "candelabre", "pied_mat", "incertain", "faible", "lamp_9665416817",
  "tache claire au pied de la lanterne NO (socle ?) à 0,75 m au SO de la position décrite ; les photos 2025 placent le fût sur la position corrigée : à départager par triangulation",
  af="clair", r=6)
o(T, 929.4, 919.0, "panneau", "J5", "absent_sur_image", "moyenne", "pan_J5_1",
  "aucune balise ni ombre au point décrit (extrémité NE de l'îlot I-0386) ; balise vue sur les photos 2025-05 : posée après mai 2022 ou position à revoir",
  va=("incertain", "balise attestée en 2025 par photo ; l'ortho 2022 ne la montre pas"))
o(T, 975, 834, "autre", "ligne_sombre_continue", "absent_de_description", "faible", None,
  "ligne sombre continue de 0,1 m (bordée d'un liseré clair) dans le prolongement exact de l'arête NO du TPC NE, au-delà de l'extrémité arrondie de I-0386 (u≈955) jusqu'au bord de dalle : joint longitudinal ponté ou séparateur bas ; rien dans la description",
  geom=[[955, 860], [1000, 809]], a={"largeur_m": 0.1, "longueur_vue_m": 3.4})
o(T, 807, 930, "marquage", "effet_feux", "attribut_corrige", "haute", "MT-0563",
  "aucune ligne transversale en 2022 : la ligne d'effet NE est un ajout du projet 2025 (constat etat_actuel-ajout-01) ; etat « conserve » à remplacer par « neuf_2025 » ; de plus MT-8002 (neuf_2025) décrit la même ligne à 0,08 m : doublon à fusionner",
  a={"etat_propose": "neuf_2025", "visible_2022": False, "doublon": "MT-8002"}, va=("incertain", "ajout du plan 2025, non attesté par une image"))
o(T, 661, 855, "marquage", "symbole_velo", "incertain", "moyenne", "MS-5154",
  "pas de figurine vélo en 2022 aux points de MS-5154 et MS-5218 (traversée de la piste à l'angle N, etat neuf_2025 d'après le GAM) : cohérent avec un ajout 2025, non vérifiable",
  a={"liens": ["MS-5154", "MS-5218"], "id_v0_2": ["MS-0590", "MS-0591"]}, va=(False, "zone redessinée en 2025 : l'image 2022 ne prouve rien"))
o(T, 631, 891, "marquage", "zebra_piste", "confirme", "haute", "MP-5311",
  "en 2022, 3 bandes pleines + 1 bande très effacée (vers 610,858) sur la piste, axe conforme à MP-5311 ; ce passage est noté neuf_2025 (piste redessinée à l'angle N, bandes bleues Chronovélo possibles) : couleur 2026 à confirmer",
  a={"nb_bandes_vues_2022": 4, "id_v0_2": "MP-0570"}, va=("incertain", "passage redessiné en 2025 (etat neuf_2025)"))
o(T, 847, 832, "marquage", "fleche_TD_TAD", "confirme", "haute", "MF-5043", "flèche tout droit + droite (vers la Revirée) voie NO, forme et position conformes", a={"usure": "2", "id_v0_2": "MF-0460"})
o(T, 893, 883, "marquage", "fleche_TD_TAG", "confirme", "haute", "MF-5042", "flèche tout droit + gauche (vers Vercors) voie SE", a={"usure": "2", "id_v0_2": "MF-0461"})
o(T, 291, 749, "marquage", "ligne_continue", "confirme", "haute", "ML-5233", "ligne continue large le long de la rive E de la Revirée, superposée", a={"id_v0_2": "ML-0291"})
o(T, 327, 790, "marquage", "ligne_continue", "attribut_corrige", "moyenne", "ML-5232",
  "ligne déjà peinte en 2022 (couverture 0,81) alors que ML-5232 est notée neuf_2025 : etat probable « conserve » ou « refait_2025_identique »", a={"id_v0_2": "ML-0292", "etat_propose": "conserve"})
o(T, 344, 740, "marquage", "texte_30", "confirme", "haute", "MS-0369", "« 30 » dans un anneau, entrée de la Revirée")
o(T, 556, 824, "marquage", "bande_isolee", "absent_de_description", "haute", None,
  "deux rectangles blancs ≈1,5 x 0,4 m peints sur le cheminement de l'angle N, à (542,771) et (556,824), hors zone de travaux : retirés en v0.3 (MZ-0569 « forme raster ») alors qu'ils sont nets sur l'image",
  a={"second_rectangle_px": [542, 771], "id_v0_2": "MZ-0569"}, af="clair", r=10, pr=True)
o(T, 503, 994, "marquage", "traversee_cyclable_verte", "incertain", "moyenne", "MP-0001",
  "en 2022, traversée cyclable de la Revirée en résine VERTE à carrés blancs (MP-0272 v0.2, retirée) ; la v0.3 la décrit en jaune neuf_2025 (MP-0001, plan 2025 à carrés orange) : couleur 2026 non vérifiable, résine verte peut-être conservée",
  a={"couleur_2022": "vert + carrés blancs", "id_v0_2": "MP-0272"}, va=("incertain", "traversée reprise par le projet 2025"))
o(T, 575, 980, "marquage", "zebra_fantome", "incertain", "haute", None,
  "bandes de l'ancien zébra de la Revirée bien visibles en 2022 (MG-0283 à MG-0285 de la v0.2, couverture 0,52-0,65), retirées en v0.3 : trace d'effacement (fantôme) possible en 2026",
  a={"id_v0_2": ["MG-0283", "MG-0284", "MG-0285"]}, va=(False, "zébra effacé en 2025"))
o(T, 419, 731, "candelabre", "mat_droit_porte_panneaux", "confirme", "haute", "lamp_12894130974",
  "socle blanc et longue ombre de mât au point commun du candélabre et des panneaux C114, AB3a, M9", a={"liens": ["pan_C114_1", "pan_AB3a_1", "pan_M9_1"]})
o(T, 719, 894, "feu", "support_feux", "confirme", "haute", "feu_NE_droite", "fourreau clair au pied, ombre du mât et des têtes vers le NNO")
o(T, 566, 909, "feu", "support_pietons", "confirme", "haute", "feu_REV_E_pietons", "pied et ombre du mât conformes")
o(T, 724, 864, "panneau", "C113", "confirme", "moyenne", "pan_C113_1", "ombre fine de poteau dans la bande verte, dans l'ombre des têtes de feu")
o(T, 419, 937, "autre", "poteau_bois", "confirme", "haute", "poteau_bois_REV_ilot", "ombre épaisse et très longue partant du point décrit")
o(T, 525, 868, "potelet", "potelet", "confirme", "haute", "potelet_REV_NE_1", "ombre courte de potelet")
o(T, 483, 826, "potelet", "potelet", "confirme", "haute", "potelet_REV_NE_2", "ombre courte de potelet")
o(T, 44, 152, "candelabre", "pied_mat", "incertain", "moyenne", "lamp_12894141026",
  "en 2022, socle blanc et ombre de mât (≈5 m au sol vers le NNO) à 1,6 m au NNO de la position décrite (nœud OSM créé en 2025-11) : ancien candélabre remplacé ou position OSM approximative",
  af="clair", r=8, va=("incertain", "candélabre OSM 2025-11 : remplacement possible"))
o(T, 48, 166, "tampon", "regard_carre", "absent_de_description", "moyenne", None, "regard carré ≈0,6 m au pied du mât", af="sombre", r=6)
o(T, 106, 279, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond ≈0,6 m sur le trottoir E de la Revirée", af="sombre", r=8)
o(T, 446.5, 786.5, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond sur le cheminement de l'angle N", af="sombre", r=8)
o(T, 461, 810.5, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond", af="sombre", r=8)
o(T, 434, 980, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond sur la Revirée, près du zébra", af="sombre", r=8)
o(T, 431.5, 788.5, "autre", "objet_blanc_bas", "incertain", "faible", None, "petit rectangle blanc 0,4 x 0,25 m sans ombre portée longue (socle, borne basse ?)")
o(T, 722, 793, "tampon", "regard_carre", "absent_de_description", "haute", None, "regard carré ≈0,7 m posé à 45°", af="sombre", r=8)
o(T, 776, 846, "tampon", "regard_carre", "absent_de_description", "moyenne", None, "regard carré ≈0,8 m dans la bande enherbée, au bord du trottoir")
o(T, 957.8, 893.3, "tampon", "regard_carre", "absent_de_description", "haute", None, "petit regard carré ≈0,4 m sur le TPC NE", af="sombre", r=6)
o(T, 890.3, 959.5, "tampon", "regard_carre", "absent_de_description", "haute", None, "regard carré ≈0,9 m sur le TPC NE (îlot I-0386)", af="sombre", r=10)
o(T, 398, 836.5, "surface", "reprise_enrobe", "absent_de_description", "moyenne", None,
  "reprise d'enrobé rectangulaire ≈2 x 3 m, plus sombre, sur la chaussée de la Revirée", bb=[380, 815, 420, 860])
o(T, 309, 616.5, "avaloir", "grille_avaloir", "absent_de_description", "moyenne", None,
  "grille sombre rectangulaire au fil d'eau de la rive E de la Revirée, dans une reprise ≈1,4 x 0,9 m", af="sombre", r=10)
o(T, 304.5, 535.8, "tampon", "bouche_a_cle", "absent_de_description", "faible", None, "anneau blanc ≈0,4 m dans la bande verte (bouche à clé, regard ?)", af="clair", r=6)
o(T, 287, 511, "potelet", "borne_blanche", "incertain", "faible", None, "objet blanc allongé 0,5 x 0,2 m avec ombre courte au bord du trottoir E de la Revirée (borne, potelet ou panneau vu de dessus)")
o(T, 150, 300, "massif", "massif_paille", "absent_de_description", "moyenne", None,
  "bande plantée paillée (paillage d'écorces brun-rouge, vivaces basses) entre le trottoir E de la Revirée et la haie ; non décrite (couche sol plein site à compléter)",
  geom=[[80, 165], [130, 280], [200, 390], [240, 430]], a={"remplissage": "paillage_ecorces_brun_rouge", "largeur_m": 1.0})
o(T, 700, 300, "surface", "jardin_arbore", "attribut_corrige", "moyenne", "S-0094a",
  "S-0094a est décrit en gazon tondu ; l'ortho montre surtout un couvert arboré dense (arbres a274-a278, a289-a292) avec massifs arbustifs et pelouse ombragée en lisière du bâtiment",
  a={"materiau_propose": "sous_bois_pelouse_ombragee_et_massifs"})
o(T, 458, 403, "arbre", "feuillu_pourpre", "attribut_corrige", "moyenne", "arbre_273",
  "couronne à feuillage pourpre (indice de verdure négatif) : prunus pissardii ou hêtre pourpre probable ; teinte à porter sur l'asset", a={"feuillage": "pourpre"})
o(T, 388, 379, "arbre", "petit_arbre_fleuri", "absent_de_description", "moyenne", None,
  "petit arbre à floraison rose en mai (couronne ≈3 m), jardin privé ; aucun arbre décrit à moins de 3 m", a={"couronne_m": 3.0, "floraison": "rose (mai)"})
o(T, 348, 464, "arbre", "petit_arbre_fleuri", "absent_de_description", "moyenne", None,
  "second petit arbre à floraison rose (couronne ≈2,5 m)", a={"couronne_m": 2.5, "floraison": "rose (mai)"})
o(T, 40, 328, "tampon", "tampon_rond", "absent_de_description", "haute", None, "tampon rond sur la chaussée de la Revirée", af="sombre", r=8)
o(T, 750, 700, "bordure", "bordures_angle_N", "confirme", "moyenne", "K-0341",
  "bordures de la zone pilote hors zone de travaux (K-0341, K-0346, K-0353, K-0354 hors abaissé) : tracés conformes aux limites cheminement / bande verte / chaussée de l'ortho ; K-0339, K-0348, K-0354 (partie S), K-0356 et K-0386 sont en zone de travaux 2025 : non vérifiables",
  a={"liens": ["K-0341", "K-0346", "K-0353", "K-0354"], "non_verifiables": ["K-0339", "K-0348", "K-0356", "K-0386", "K-0386z"]})
o(T, 305, 530, "ilot", "refuge_herbe", "attribut_corrige", "moyenne", "I-0368",
  "I-0368 (« refuge », remplissage enrobé de trottoir, 1,9 m²) est une petite emprise bordurée dans l'accotement enherbé de la Revirée, avec un objet blanc (support de panneau ?) à sa pointe N : herbe sur l'image, pas d'enrobé ; type « refuge » douteux",
  a={"materiau_propose": "gazon_tondu"})
