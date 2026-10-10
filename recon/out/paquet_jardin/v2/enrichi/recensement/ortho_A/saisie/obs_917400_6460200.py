from obs_lib import ob, tuile
tuile("917400_6460200")
C = "abords du chantier des Saules Blancs en 05/2022 (voie provisoire, bassins, clôtures de chantier) : sol non valable pour 2026"

ob("arbre", "bosquet_conserve", (917421.5, 6460233.0), "confirme", lien="arbre_160", conf="haute", prec=1.0,
   attributs={"observe": "groupe de feuillus conservés pendant le chantier, couronne commune ≈ 12 × 10 m centrée vers (917421.5, 6460233) ; cohérent avec arbre_160, 161, 162, 163, 175, 176",
              "liens": ["arbre_160", "arbre_161", "arbre_162", "arbre_163", "arbre_175", "arbre_176"]},
   valide=True, raison="arbres existants levés au GAM")
ob("autre", "chantier_2022", (917420.0, 6460215.0), "absent_sur_image", conf="haute", prec=25.0,
   attributs={"observe": "voie de chantier gravillonnée avec passage piéton provisoire (917428, 6460227), clôtures Heras, 2 bassins de rétention provisoires (917410, 6460205) et (917427, 6460206), grue, base vie"},
   valide=False, raison=C)
