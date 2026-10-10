from obs_lib import ob, tuile
tuile("917350_6460150")
C = "dalle entièrement en chantier en 05/2022 (Saules Blancs, surfaces « construit_2023_2024 ») : l'ortho 2022 ne vaut pas pour l'état 2026"

ob("marquage", "traversee_cyclable_fausse_detection", (917375.27, 6460161.87), "absent_sur_image", lien="MP-0370", conf="haute", prec=0.5, preuve=True,
   attributs={"decrit": "traversée cyclable à pavés jaunes, etat « conserve », source v1 « ortho_2022 (rangée jaune, profil de b*) »",
              "observe": "en 05/2022 l'emplacement est un terrain de chantier (terre, gravats, herbe) sans aucun marquage : la « rangée jaune » v1 est un faux positif sur la terre ocre",
              "action_proposee": "ne pas fonder MP-0370 sur l'ortho 2022 ; etat « neuf_2023_2025 » ou retrait sauf preuve photo 2026"},
   valide="incertain", raison=C)
ob("arbre", "couronne", (917362.5, 6460162.0), "confirme", lien="arbre_033", conf="haute", prec=0.8,
   attributs={"observe": "feuillu isolé conservé au milieu du chantier (couronne ≈ 8–9 m en 05/2022)"}, valide=True, raison="arbre conservé pendant le chantier, levé au GAM")
ob("arbre", "plantations_posterieures", (917372.0, 6460183.0), "absent_sur_image", lien="arbre_054", conf="haute", prec=1.0,
   attributs={"observe": "arbres « jeunes ou plantés après 2021 » (arbre_042, 043, 054, 055, 056, 057, 069, 083) absents en 05/2022 : terrain de chantier",
              "liens": ["arbre_042", "arbre_043", "arbre_054", "arbre_055", "arbre_056", "arbre_057", "arbre_069", "arbre_083"]},
   valide=True, raison="plantations postérieures à 2022, cohérent avec la description")
