from obs_lib import ob, tuile
tuile("917350_6460350")
H = "hors zone de travaux 2025 (Verdun NE conservée)"

ob("massif", "arbustes_tailles_en_blocs", (917360.0, 6460377.5), "absent_de_description", conf="haute", prec=0.3, preuve=True,
   attributs={"observe": "arbustes taillés en blocs sombres (≈ 1,2 × 1,5–2,5 m, h ≈ 1–1,5 m d'après les ombres) alignés au pas ≈ 4 m dans l'accotement enherbé entre trottoir NO et Verdun",
              "positions_l93": [[917355.9, 6460373.0], [917358.75, 6460376.25], [917361.55, 6460379.2], [917364.0, 6460381.75], [917373.5, 6460391.6], [917377.6, 6460395.25]]},
   valide=True, raison=H, note="l'accotement est décrit en herbe seule (surfaces_2026)")
ob("marquage", "ligne_rive_discontinue", (917362.0, 6460376.5), "attribut_corrige", lien="ML-0545", conf="moyenne", prec=0.2,
   attributs={"decrit": "segments isolés ML-0544, ML-0545, ML-0547, ML-0549 (≈ 1,1–1,6 m) « tiret v1 isolé »",
              "observe": "tirets d'une même ligne de rive discontinue à ≈ 0,8–1 m de la bordure NO ; un tiret supplémentaire non décrit vers (917363.5, 6460378.2)",
              "proposition": "une ligne discontinue unique (modulation T2/T'2 à mesurer) au lieu de segments"},
   valide=True, raison=H)
ob("marquage", "ligne_delimitation_discontinue", (917366.9, 6460377.4), "attribut_corrige", lien="ML-5136", conf="haute", prec=0.1,
   attributs={"decrit": "ML-5136 « continue » (GAM)", "observe": "position confirmée à ≤ 0,1 m mais la ligne est discontinue : mesure le long de l'axe (s 141–195 m, hors ombres) tirets 3,1–3,2 m / vides ≈ 1,1 m, soit une modulation T3 (3,00 / 1,33 m) entre les deux voies de Verdun NE ; même motif, plus usé, sous les ombres vers le NE", "modulation_proposee": "T3", "longueur_m": 194.7, "lien_v02": "ML-0546 (discontinue, modulation mesurée)"},
   valide=True, raison=H)
ob("candelabre", "mat_crosse", (917354.0, 6460370.75), "confirme", lien="lamp_9665416617", conf="moyenne", prec=0.3,
   attributs={"observe": "départ de l'ombre du mât au droit de la position décrite ; luminaire au-dessus de la bordure"}, valide=True, raison=H)
ob("marquage", "parking_saules_blancs", (917391.0, 6460355.0), "absent_sur_image", lien="MF-5096", conf="haute", prec=1.0,
   attributs={"observe": "en 05/2022 enrobé neuf sans aucun marquage (chantier des Saules Blancs) : flèches et pictogrammes du parking non visibles",
              "liens": ["MF-5096", "MF-5097", "MS-0264", "MS-0265", "MS-5519", "MS-5520"], "note_v03": "MS-0264 / MS-0265 restent des indices v1 « inverifiable » sans autre preuve"},
   valide=True, raison="marquages posés après 05/2022 (surface construite 2023-2024) : l'ortho 2022 ne peut pas les confirmer ; présents au levé GAM (SYMBOLE_PMR)")
