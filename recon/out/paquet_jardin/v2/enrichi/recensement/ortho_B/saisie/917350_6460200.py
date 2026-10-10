# 917350_6460200 : chantier des Saules Blancs (grue, gros oeuvre) et desserte S
o(T, 600, 300, "autre", "chantier_2022", "incertain", "haute", None,
  "mai 2022 : gros oeuvre d'immeuble en cours (grue à tour, coffrages, base vie, engins) ; tout le secteur (bâtiments, cours, plantations) est livré en 2023-2024 : non vérifiable par l'ortho",
  bb=[150, 0, 1000, 700], vt=500, va=(False, "secteur construit 2023-2024"))
o(T, 600, 800, "cloture", "cloture_chantier", "incertain", "moyenne", None,
  "clôture de chantier provisoire (poteaux tous les ≈3 m) le long de la rive N de la desserte S en 2022 ; ne pas reprendre en 2026 sans autre source",
  geom=[[160, 830], [500, 760], [1000, 610]], va=(False, "clôture de chantier provisoire"))
o(T, 300, 720, "arbre", "feuillu", "confirme", "haute", "arbre_135",
  "bouquet de feuillus conservé à l'angle NO de la desserte (arbre_135, arbre_103)", a={"liens": ["arbre_135", "arbre_103"]})
o(T, 890, 938, "arbre", "jeune_arbre", "absent_sur_image", "haute", "arbre_086",
  "arbre_084, arbre_086, arbre_102 (« h 5 m ») absents en mai 2022 : plantations postérieures",
  a={"liens": ["arbre_084", "arbre_086", "arbre_102"]}, va=(False, "plantations postérieures à l'image"))
