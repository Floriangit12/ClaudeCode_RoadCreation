from obs_lib import ob, tuile
tuile("917250_6460250")
T = "cœur du carrefour refait en 2025 (enrobé neuf) : les tampons sont en général conservés et remis à niveau, à confirmer sur photo postérieure"

for xy, forme, note in [((917279.55, 6460294.3), "tampon rond fonte ≈ 0,7 m", "chaussée centrale, débouché de la Revirée"),
                        ((917271.87, 6460284.38), "regard carré ≈ 1,2 m (plaque striée)", "chaussée centrale, sortie Verdun SO"),
                        ((917278.2, 6460270.0), "tampon rond ≈ 0,6 m", "ancien plateau piéton angle S (chaussée 2026)"),
                        ((917276.6, 6460268.6), "regard carré ≈ 0,8 m", "ancien plateau piéton angle S (chaussée 2026)"),
                        ((917279.5, 6460267.5), "regard carré ≈ 0,6 m", "ancien plateau piéton angle S"),
                        ((917258.6, 6460271.3), "regard carré ≈ 1,4 m", "ancienne voie de TAD, Verdun SO (chaussée 2026)"),
                        ((917284.08, 6460268.08), "regard carré ≈ 0,9 m", "entrée Vercors, voie d'entrée")]:
    ob("tampon", "regard", xy, "absent_de_description", conf="moyenne", prec=0.2, preuve=(xy[0] == 917279.55),
       attributs={"forme": forme, "support": note}, valide="incertain", raison=T)
ob("marquage", "zebra", (917292.98, 6460294.56), "attribut_corrige", lien="MP-5191", conf="haute", prec=0.2, preuve=True,
   attributs={"decrit": "zébra GAM, etat « neuf_2025 »", "etat_propose": "conserve (ou refait_2025_identique)", "observe": "le même zébra (bandes de 0,5 m au pas ≈ 1,0 m, de part et d'autre du refuge du TPC) existe déjà en 05/2022 à la même place",
              "note_contraste": "contraste automatique faible car l'entité est un axe (LineString), pas les bandes"},
   valide=True, raison="zébra, refuge et flèches de la branche NE conservés (hist-13) ; levé GAM 2026")
ob("ilot", "refuge_tpc_ne", (917289.5, 6460295.8), "confirme", lien="S-0341", conf="moyenne", prec=0.3,
   attributs={"observe": "refuge semi-circulaire béton clair (≈ 2,4 m) à l'extrémité du TPC NE, panneau sur poteau ; revêtement gris clair homogène (béton balayé plausible)"},
   valide=True, raison="refuge conservé (hist-13)")
ob("marquage", "fleche_tag", (917284.8, 6460291.9), "confirme", lien="MZ-5188", conf="moyenne", prec=0.3,
   attributs={"observe": "une flèche TAG existait déjà en 2022 à ≈ 0,3 m de la pose MF-0021 (v0.2), même voie, même cap ; en v0.3 elle est absorbée dans le contour GAM MZ-5188 « zone divers » : à reposer en gabarit TAG", "etat_v3": "neuf_2025"},
   valide="incertain", raison="voie du cœur refaite en 2025 ; la pose v2 (objet .xodr) coïncide avec la flèche 2022")
ob("ilot", "remplissage_galets_2022", (917289.0, 6460272.0), "incertain", lien="I-0390", conf="faible", prec=1.0,
   attributs={"observe": "en 2022 les îlots du Vercors (anciens) portaient un lit de pierres grises grossières (texture granuleuse visible à 5 cm : éléments de plusieurs cm), comme les îlots de Verdun SO",
              "suggestion": "si le remplissage 2025 reprend l'existant : « galets_20_40 » plutôt que « gravier_concasse_6_10 »"},
   valide="incertain", raison="îlots reconstruits en 2025 (goutte d'eau) : l'ortho 2022 ne montre que l'ancien remplissage")
