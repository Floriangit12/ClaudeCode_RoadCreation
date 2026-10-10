from obs_lib import ob, tuile
tuile("917300_6460100")

ob("autre", "hors_emprise_description", (917325.0, 6460120.0), "absent_de_description", conf="haute", prec=20.0, preuve=True,
   attributs={"observe": "80 % de la dalle hors emprise (y < 6460140) : Vercors S avec passage piéton à refuge central (bandes vers (917322, 6460131) et (917331, 6460130)), traversée de la piste O (917317, 6460131), barrière basse brune sur le refuge, mot « BUS » (917341, 6460111) et voie bus, damier de traversée cyclable blanc (917346, 6460104), flèche TD (917329, 6460110), candélabres (ombres vers (917340, 6460125) et (917310, 6460131))",
              "remarque": "zone vue par les photos IGN 2026-07 (constats p2026_07_ign) : vérifiable sur Panoramax post-travaux"},
   valide="incertain", raison="Vercors S touché par les travaux 2025-2026 (trottoirs et végétalisation, sens unique) d'après hist-08")
ob("marquage", "nez_ilot_peint", (917322.6, 6460145.5), "absent_de_description", lien=None, conf="moyenne", prec=0.3,
   attributs={"observe": "nez d'îlot peint blanc (chevron allongé ≈ 4 × 0,6 m) entre les deux voies du Vercors en 05/2022", "lien_v02": "MZ-0403 (retiré en v0.3 : retire_forme_raster)"},
   valide="incertain", raison="Vercors S retouché en 2025-2026 ; à confirmer sur photo IGN 2026-07")
