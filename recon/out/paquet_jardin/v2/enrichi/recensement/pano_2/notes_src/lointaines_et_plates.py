"""360° à pose a priori de séquence (2024-08-24, 2025-05-18 ; ≈0,4-1,7 m, ≈1-2°) et photos à plat 2020/2023 (sans pose,
lecture qualitative, état ANTÉRIEUR aux travaux)."""
import sys; sys.path.insert(0, '..'); sys.path.insert(0, '.')
from note import ecrire, pos, P, V, preuve

AV = "photo antérieure aux travaux C1 (juil.-oct. 2025)"
obs = []

# ------------------------------------------------------------------ 2374105b / 034cb578 (2025-05-18, Verdun SO, a priori de séquence)
S, D = "pnx:2374105b", "2025-05-18"
obs += [
 dict(source=S, date_image=D, classe="mobilier", sous_type="totem_PR",
      attributs={"objet": "totem P+R SMMAG : bandeau bleu « P+R », « PARKING RELAIS », flèche, logo M, arc multicolore",
                 "hauteur_mesuree_m": "5,1-5,7 (2 photos ; description 2,8 m)", "largeur_estimee_m": 0.9,
                 "position_2025_05": "îlot de Verdun SO (≈(−31,2 ; −26,6), triangulation 2374105b + 034cb578, angle 8° : ±2 m)",
                 "correction": "prototype totem_PR à redimensionner (≈0,9 × 0,3 × 5,4 m) ; position 2026 (déduite, bord de trottoir NO) non vérifiable"},
      position=pos(local=[-31.22, -26.59, -0.25], precision_m=2.0, methode="triangulation"), lien_description="totem_PR", statut="attribut_corrige",
      valide_2026=V("incertain", AV + " ; îlot supprimé : totem déplacé (même objet probable, hauteur valable)"), confiance="moyenne",
      preuve=preuve("crops/2374105b_L_totem_ov.jpg", pixels=[[450, 65], [450, 400]])),
 dict(source=S, date_image=D, classe="autre", sous_type="poteau_acier_a_potence",
      attributs={"objet": "mât acier tubulaire brun foncé ≈9,9 m portant une potence horizontale ≈6 m à ≈7,4 m et des câbles aériens transversaux (au-dessus de Verdun SO)",
                 "correction": "poteau_reseau_9742811518 décrit 'poteau bois 9 m' : c'est un mât ACIER à potence + câbles (à modéliser : potence et câbles visibles dans le ciel des caméras)",
                 "serie": "même type de mâts à potence le long de Verdun SO (photos 2023 937d5401, 7bca6daa, 2fe903ee)"},
      position=P("poteau_reseau_9742811518", 0.5), lien_description="poteau_reseau_9742811518", statut="attribut_corrige",
      valide_2026=V("incertain", AV + " ; objet en zone de travaux, statut paquet 'à vérifier'"), confiance="moyenne",
      preuve=preuve("crops/2374105b_Z_poteau.jpg", pixels=[[452, 318], [445, 440], [95, 385]])),
 dict(source=S, date_image=D, classe="candelabre", sous_type="mat_double_crosse_decor",
      attributs={"crosses": "2 crosses symétriques, lanternes plates", "decor": "voile lumineuse (filet métallique) fixée au mât vers 5-8 m (décor de fin d'année laissé en place)",
                 "remarque": "même modèle que lamp_9514795520 ; type 'mât à double crosse' cohérent"},
      position=P("lamp_9514795817", 0.5), lien_description="lamp_9514795817", statut="confirme",
      valide_2026=V("incertain", AV), confiance="moyenne", preuve=preuve("crops/2374105b_Z_poteau.jpg", pixels=[[160, 180], [120, 300]])),
 dict(source=S, date_image=D, classe="marquage", sous_type="stationnement_velos_jaune",
      attributs={"objet": "emplacement de stationnement vélos peint en JAUNE (cadre + 2 logos vélo) sur le trottoir/quai NO de Verdun SO",
                 "etat": "neuf, couleur jaune Chronovélo"},
      position=pos(local=None, precision_m=2.0), lien_description=None, statut="incertain",
      valide_2026=V("incertain", AV + " ; quai NO avancé de ≈20 m en 2025"), confiance="faible",
      preuve=preuve("crops/2374105b_v2_a297_tout.jpg", bbox=[580, 530, 1020, 600])),
]

# ------------------------------------------------------------------ 5ac7eaaa (2025-05-18, Verdun NE à 78 m, a priori de séquence)
S, D = "pnx:5ac7eaaa", "2025-05-18"
obs += [
 dict(source=S, date_image=D, classe="panneau", sous_type="groupe AB3a+B2a+M9 / B1+B2b",
      attributs={"constat": "mât des panneaux de Verdun NE vu de dos : triangulation (7651c539 + 5ac7eaaa, angle 29°) en (52,15 ; 60,30), soit ≈1,2 m au SSE de la position source (52,03 ; 61,47) et ≈1,8 m de la position corrigée par la cohérence (52,99 ; 61,90)",
                 "doute": "la pose a priori de 5ac7eaaa (non calée) limite la précision (±1 m)"},
      position=pos(local=[52.152, 60.297, 0.5], precision_m=1.2, methode="triangulation"), lien_description="pan_AB3a_2;pan_B2a_1;pan_M9_2", statut="incertain",
      valide_2026=V(True, "Verdun NE hors reconstruction"), confiance="faible",
      preuve=preuve("crops/5ac7eaaa_L_signes_ov.jpg", pixels=[[585, 300]])),
 dict(source=S, date_image=D, classe="potelet", sous_type="poteau_vide",
      attributs={"objet": "poteau acier galvanisé Ø ≈60 mm, ≈3 m, SANS panneau (colliers vides), au bord de la piste NO de Verdun NE ≈20 m en amont du groupe de panneaux",
                 "interpretation": "support de panneau déposé"},
      position=pos(local=None, precision_m=3.0), lien_description=None, statut="absent_de_description",
      valide_2026=V("incertain", "vu en 2025-05 ; zone hors travaux"), confiance="faible",
      preuve=preuve("crops/5ac7eaaa_L_poteau_haut.jpg", pixels=[[450, 110], [450, 890]])),
]

# ------------------------------------------------------------------ quartier des Saules Blancs (2024-08-24, a priori de séquence)
S, D = "pnx:16dcd275", "2024-08-24"
obs += [
 dict(source=S, date_image=D, classe="arbre", sous_type="jeunes_arbres_tuteures",
      attributs={"objets": "jeunes arbres d'alignement du quartier des Saules Blancs (arbre_08x, 10x, 13x, 15x...)",
                 "hauteur_mesuree_m": "8,5-11 en 2024-08 (arbre_134 ≈8,5 ; arbre_101 ≈9-11) au lieu de 5 (valeur par défaut, LiDAR 2021 < 2,5 m)",
                 "couronne_m": "≈3-5", "tuteurage": "tripodes bois", "essence": "feuillus à feuille palmée (platane/érable probable)",
                 "projection_2026": "+1 à 2 m (≈10-12 m)"},
      position=P("arbre_134", 1.5), lien_description="arbre_134;arbre_101;arbre_102", statut="attribut_corrige",
      valide_2026=V(True, "arbres plantés vers 2022, hors travaux 2025 ; ils ont grandi depuis"), confiance="moyenne",
      preuve=preuve("crops/16dcd275_v1_a337_tout.jpg", pixels=[[905, 470], [905, 165], [560, 160]])),
]
S, D = "pnx:a150b381", "2024-08-24"
obs += [
 dict(source=S, date_image=D, classe="potelet", sous_type="file_de_potelets",
      attributs={"objet": "file de ≈10 potelets acier gris Ø ≈80 mm, ≈1,0 m, au pas ≈2,2 m, le long du bâtiment commercial (bord du parking gravillonné)",
                 "axe": "de ≈(52,8 ; −37,6) à ≈(57,1 ; −59,0) (rayons au sol, pose a priori ±1,5 m)"},
      position=pos(local=[53.26, -39.31, -1.45], precision_m=1.5, methode="rayon_sol"), lien_description=None, statut="absent_de_description",
      valide_2026=V("incertain", "quartier livré en 2024 ; plateau 2025 (dents de requin neuves) à proximité"), confiance="moyenne",
      preuve=preuve("crops/a150b381_v0_a213_tout.jpg", pixels=[[628, 690], [868, 775], [284, 545], [100, 480]])),
 dict(source=S, date_image=D, classe="marquage", sous_type="dents_de_requin",
      attributs={"constat": "MS-5120…5132 (neuf_2025) absents en 2024-08 : surface béton clair sans marquage — cohérent avec leur date"},
      position=pos(local=[51.69, -32.58, -1.45], precision_m=1.5, methode="rayon_sol"), lien_description="MS-5129", statut="absent_sur_image",
      valide_2026=V(True, "absence normale avant 2025 ; ne remet pas en cause 2026"), confiance="moyenne",
      preuve=preuve("crops/a150b381_v1_a315_tout.jpg", bbox=[100, 620, 860, 890])),
]
S, D = "pnx:20c30032", "2024-08-24"
obs += [
 dict(source=S, date_image=D, classe="cloture", sous_type="cloture_bois_ajouree",
      attributs={"objet": "clôture en lattes bois verticales peintes blanc cassé, ≈1,2 m, ajourée, le long du cheminement piéton (béton balayé) du quartier",
                 "autre": "panneau d'information sur pieds blancs (≈2 m) en bord de cheminement",
                 "description": "aucune clôture décrite à cet endroit (cloture_gam_033/036 plus loin)"},
      position=pos(local=None, precision_m=3.0), lien_description=None, statut="absent_de_description",
      valide_2026=V("incertain", "quartier récent, hors travaux"), confiance="faible",
      preuve=preuve("crops/20c30032_v0_a269_obj.jpg", bbox=[790, 480, 1200, 800])),
]

# ------------------------------------------------------------------ haies (2025-05-18, calées)
S, D = "pnx:7651c539", "2025-05-18"
obs += [
 dict(source=S, date_image=D, classe="haie", sous_type="haie_taillee",
      attributs={"objet": "haie taillée persistante (laurier/photinia) ≈1,5-2,0 m, ≈1,2 m d'épaisseur, le long du trottoir SE de Verdun NE",
                 "axe": "≈(53,4 ; 30,3) -> (59,7 ; 39,9) -> (62,8 ; 52,7) (rayons au sol)",
                 "description": "aucune famille 'haies' dans la description v2"},
      position=pos(local=[59.66, 39.86, 0.23], precision_m=1.0, methode="rayon_sol"), lien_description=None, statut="absent_de_description",
      valide_2026=V(True, "Verdun NE hors reconstruction"), confiance="moyenne",
      preuve=preuve("crops/7651c539_v1_a051_tout.jpg", pixels=[[700, 425], [900, 445], [1150, 470]])),
]
S, D = "pnx:53009a45", "2024-05-01"
obs += [
 dict(source=S, date_image=D, classe="haie", sous_type="haie_taillee",
      attributs={"objet": "haie taillée persistante ≈1,2-1,4 m doublée d'un grillage sur poteaux verts, entre la piste Chronovélo et le parking de la jardinerie (Verdun SO, côté NO)"},
      position=pos(local=None, precision_m=5.0), lien_description=None, statut="absent_de_description",
      valide_2026=V("incertain", AV + " ; domaine privé inchangé probable"), confiance="moyenne",
      preuve=preuve("crops/planche_360_53009a45.jpg", bbox=[0, 230, 800, 600])),
 dict(source=S, date_image=D, classe="bordure", sous_type="bordure_peinte_jaune_chronovelo",
      attributs={"objet": "piste bidirectionnelle Chronovélo de Verdun SO (côté NO) : bordures à dessus peint JAUNE (usé) côté chaussée, axe 'tiret bleu + points jaunes', pictogrammes vélo et texte 'Maupertuis'",
                 "vu_aussi": "2020-05-21 (a8759ccd, 98273635, 11d8fa94), 2024-05-01 (7b9a2706)",
                 "description": "matériau 'peint_jaune' absent des bordures v2 (zone pilote = NE) : à prévoir dans la description du site complet"},
      position=pos(local=None, precision_m=5.0), lien_description=None, statut="absent_de_description",
      valide_2026=V("incertain", AV + " ; partie de la piste reprise en 2025 près du quai NO"), confiance="moyenne",
      preuve=preuve("crops/planche_360_53009a45.jpg", bbox=[800, 230, 1600, 600])),
]

# ------------------------------------------------------------------ photos à plat 2020 / 2023 (sans pose)
obs += [
 dict(source="pnx:e70db9dd", date_image="2023-03-18", classe="mobilier", sous_type="totem_PR",
      attributs={"objet": "totem P+R SMMAG sur l'îlot de Verdun SO (2023) : bleu/noir, 'P+R PARKING RELAIS →', 'M', logo SMMAG, ≈5 m",
                 "remarque": "en 2020 (a8759ccd) totem d'une autre génération (P+R cyan, M dans un cercle rose)"},
      position=pos(local=None, precision_m=5.0), lien_description="totem_PR", statut="attribut_corrige",
      valide_2026=V("incertain", AV + " (2023) ; îlot supprimé, totem déplacé"), confiance="moyenne",
      preuve=preuve("crops/e70db9dd_v0_a226_brut.jpg", bbox=[630, 145, 700, 400])),
 dict(source="pnx:0fe67f82", date_image="2020-05-21", classe="feu", sous_type="supports_et_tetes",
      attributs={"mats": "tubes acier gris (RAL ≈7016/7037), Ø ≈90 mm, chapeau", "tetes": "boîtiers noirs, R12 piétons 2 feux (figurine rouge) et répétiteurs ; boutons d'appel noirs sur mâts",
                 "remarque": "teintes à reprendre pour les prototypes feu_mat / feu_tete_* (2025-05 : mêmes teintes, fourreaux jaunes rétroréfléchissants sur certains mâts)"},
      position=pos(local=None, precision_m=5.0), lien_description="feu_NE_SE_pietons", statut="attribut_corrige",
      valide_2026=V("incertain", AV + " (2020) ; mâts conservés probables pour l'apparence"), confiance="moyenne",
      preuve=preuve("crops/0fe67f82_v0_a135_brut.jpg", bbox=[655, 170, 770, 710])),
 dict(source="pnx:f05a89a5", date_image="2023-03-18", classe="panneau", sous_type="D21",
      attributs={"objet": "D21 (2 lames blanches, pointe à droite) sur l'îlot arrondi de la Revirée en 2023 + panonceau, avant travaux",
                 "remarque": "même ensemble vu en 2025-05 (e5d79de9, 5c0d1d39) ; îlot supprimé en 2025"},
      position=P("pan_D21_2", 1.5), lien_description="pan_D21_2", statut="confirme",
      valide_2026=V(False, AV + " ; îlot porteur supprimé"), confiance="moyenne",
      preuve=preuve("crops/f05a89a5_L_D21.jpg", bbox=[170, 190, 400, 320])),
]
ecrire("lointaines_et_plates", obs)
