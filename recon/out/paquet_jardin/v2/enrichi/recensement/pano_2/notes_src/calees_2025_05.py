"""Observations des photos calées 5c0d1d39 (2024-08-24), 9834f494, 6e97bb8c, e540bf1d, 7651c539 (2025-05-18)
+ triangulations multi-photos (avec e5d79de9)."""
import sys; sys.path.insert(0, '..'); sys.path.insert(0, '.')
from note import ecrire, pos, P, V, preuve

AV = "photo antérieure aux travaux C1 (juil.-oct. 2025)"

# ------------------------------------------------------------------ 5c0d1d39 (2024-08-24)
S, D = "pnx:5c0d1d39", "2024-08-24"
obs = [
 dict(source=S, date_image=D, classe="mobilier", sous_type="armoire_commande_feux_probable",
      attributs={"objet": "armoire/coffret technique beige à double porte (≈0,8 × 0,5 × 1,5 m) + petit socle beige à gauche ; parement pierre clair",
                 "interpretation": "armoire de commande des feux ou coffret réseau (RES-01) à l'angle SE (Vercors / Verdun NE)",
                 "vu_aussi": "e5d79de9 (2025-05-18)"},
      position=pos(local=[17.69, -12.95, 0.07], precision_m=0.8, methode="triangulation"), lien_description=None, statut="absent_de_description",
      valide_2026=V("incertain", AV + " ; angle SE remanié en 2025 (bordures K-0411/K-0361 en zone de travaux) ; une armoire de feux est en général conservée"),
      confiance="moyenne", preuve=preuve("crops/5c0d1d39_L_bloc.jpg", pixels=[[500, 610]])),
 dict(source=S, date_image=D, classe="candelabre", sous_type="poteau_bois_equipe",
      attributs={"support": "poteau bois brun ≈9 m", "tete_2024_08": "disque clair (lanterne) + boîtier/panneau sombre rectangulaire incliné ≈0,5 × 0,3 m en tête",
                 "tete_2025_05": "sommet nu (e5d79de9, 6e97bb8c) : équipement déposé entre 2024-08 et 2025-05 ?",
                 "type_decrit": "mât à crosse longue : non confirmé (aucune crosse longue)",
                 "position": "triangulé sur 3 photos (5c0d1d39, e5d79de9, 6e97bb8c ; angle 48,6° ; résidus ≤ 1 cm) : (20,65 ; −6,47), soit 0,77 m au NO de la position décrite (21,1 ; −7,1)"},
      position=pos(local=[20.654, -6.47, -0.45], precision_m=0.15, methode="triangulation"), lien_description="lamp_lidar_VERC_E",
      statut="position_corrigee", valide_2026=V("incertain", "poteau probablement conservé (rive E) mais berge du Vercors remaniée en 2025 ; équipement de tête absent en 2025-05"),
      confiance="haute", preuve=preuve("crops/5c0d1d39_L_lampVERCEtop.jpg", pixels=[[440, 340], [490, 470]])),
 dict(source=S, date_image=D, classe="panneau", sous_type="D21",
      attributs={"lame_1": "LA REVIRÉE / Collège L. Terray (pointe à droite)", "lame_2": "Commerces de LA REVIRÉE (pointe à droite)",
                 "fond": "blanc, texte noir, liseré noir", "face": "vers le NE",
                 "position": "poteau triangulé (e5d79de9 + 5c0d1d39, angle 10,4° seulement) en (−4,37 ; 5,63), ≈1,1 m au SO de la position décrite ; à confirmer par une visée transversale"},
      position=pos(local=[-4.365, 5.628, 0.08], precision_m=1.2, methode="triangulation"), lien_description="pan_D21_2", statut="position_corrigee",
      valide_2026=V(False, AV + " ; îlot porteur supprimé par les travaux 2025 (absent du GAM 2026)"), confiance="faible",
      preuve=preuve("crops/5c0d1d39_L_D21_ov.jpg", pixels=[[467, 700]])),
 dict(source=S, date_image=D, classe="panneau", sous_type="J5",
      attributs={"code": "J5 confirmé (fond bleu, flèche oblique blanche), monté bas sur socle noir", "ecart": "pied réel ≈0,4 m à l'O de la position décrite (azimut)",
                 "support": "petit îlot arrondi en terre-pierre (bordure K-0381)"},
      position=P("pan_J5_2", 0.5), lien_description="pan_J5_2", statut="position_corrigee",
      valide_2026=V(False, AV + " ; îlot supprimé en 2025 (cohérence : non instancié)"), confiance="faible",
      preuve=preuve("crops/5c0d1d39_L_J5_2_ov.jpg", pixels=[[330, 720], [598, 735]])),
 dict(source=S, date_image=D, classe="panneau", sous_type="J5",
      attributs={"vu": "de dos (gris) sur le nez du TPC NE, plaque ≈0,5 × 0,6 m sur petit socle, catadioptre blanc",
                 "position": "triangulé (5c0d1d39 + e5d79de9, angle 13,8°) en (17,45 ; 14,73) : ≈0,8 m de la position décrite, ≈0,4 m de la position corrigée par la cohérence ; incertitude surtout le long du TPC"},
      position=pos(local=[17.459, 14.727, 0.47], precision_m=0.5, methode="triangulation"), lien_description="pan_J5_1", statut="position_corrigee",
      valide_2026=V("incertain", AV + " ; nez du TPC (K-0386) repris en 2025"), confiance="moyenne",
      preuve=preuve("crops/5c0d1d39_L_J5_1_ov.jpg", pixels=[[478, 690]])),
 dict(source=S, date_image=D, classe="candelabre", sous_type="mat_brun_bi_hauteur",
      attributs={"mat": "acier teinte brun/bronze à bagues décoratives (pas un poteau bois)", "lanterne_haute": "crosse ≈1,5 m vers la chaussée (≈135°), lanterne plate à ≈10,1 m",
                 "lanterne_basse": "2e lanterne sur console courte à ≈5,9 m côté piste/trottoir NO (≈315°) (vue en e5d79de9)",
                 "correction": "ajouter un 2e luminaire bas (éclairage piétons/cycles) ; fût ≈0,5 m derrière l arête (voir triangulation 6e97bb8c + e5d79de9)"},
      position=pos(local=[16.4, 23.6, 0.27], precision_m=0.3, methode="projection_description"), lien_description="lamp_9665416817",
      statut="attribut_corrige", valide_2026=V(True, "Verdun NE hors reconstruction ; objet vu identique en 2024-08 et 2025-05"), confiance="haute",
      preuve=preuve("crops/5c0d1d39_L_lamp9665.jpg", pixels=[[392, 268], [605, 272]])),
 dict(source=S, date_image=D, classe="panneau", sous_type="B21a1",
      attributs={"constat": "aucun panneau sur le refuge I-0332 le 24/08/2024 (il porte un disque B21a1 le 18/05/2025)"},
      position=P("pan_B21a1_1", 0.5), lien_description="pan_B21a1_1", statut="absent_sur_image",
      valide_2026=V(False, AV + " ; refuge reconstruit en 2025"), confiance="moyenne",
      preuve=preuve("crops/5c0d1d39_v1_a152_obj.jpg", pixels=[[322, 590]])),
 dict(source=S, date_image=D, classe="panneau", sous_type="C114+AB3a+M9",
      attributs={"hauteur": "même écart vertical que e5d79de9 et 9834f494 : pile ≈0,55 m plus haute que décrit (3 photos concordantes)"},
      position=P("pan_C114_1", 0.3), lien_description="pan_C114_1;pan_AB3a_1;pan_M9_1", statut="attribut_corrige",
      valide_2026=V(True, "support inchangé"), confiance="haute", preuve=preuve("crops/5c0d1d39_v3_a292_obj.jpg", pixels=[[980, 350], [972, 375]])),
]

# ------------------------------------------------------------------ 9834f494 (2025-05-18)
S, D = "pnx:9834f494", "2025-05-18"
obs += [
 dict(source=S, date_image=D, classe="panneau", sous_type="C113",
      attributs={"code": "C113 (carré bleu, cycle blanc) lu de face", "face_azimut_deg": 65, "position": "poteau à 0,03 m de la position décrite (vu à 9,9 m)",
                 "remarque": "confirme l'azimut 65° de la revue de cohérence (couche à 225° fausse)"},
      position=P("pan_C113_1", 0.1), lien_description="pan_C113_1", statut="confirme",
      valide_2026=V(True, "support inchangé (angle NO de Verdun NE)"), confiance="haute",
      preuve=preuve("crops/9834f494_L_C113_ov.jpg", bbox=[255, 70, 620, 500])),
 dict(source=S, date_image=D, classe="panneau", sous_type="C114+AB3a",
      attributs={"hauteur": "écart vertical mesuré à 24,3 m : +0,57 m (C114 et AB3a), latéral 0,23 m"},
      position=P("pan_C114_1", 0.3), lien_description="pan_C114_1;pan_AB3a_1", statut="attribut_corrige",
      valide_2026=V(True, "support inchangé"), confiance="haute", preuve=preuve("crops/9834f494_L_C114_ov.jpg", pixels=[[510, 120], [510, 390]])),
 dict(source=S, date_image=D, classe="arbre", sous_type="feuillage_pourpre",
      attributs={"essence": "feuillage pourpre confirmé (Prunus cerasifera 'Pissardii' probable vu la taille ≈10-12 m)", "hauteur_estimee_m": 11},
      position=P("arbre_273", 1.0), lien_description="arbre_273", statut="confirme", valide_2026=V(True, "hors travaux"),
      confiance="moyenne", preuve=preuve("crops/9834f494_v3_a293_obj.jpg", bbox=[700, 190, 830, 330])),
 dict(source=S, date_image=D, classe="marquage", sous_type="fleches_approche_Verdun_NE",
      attributs={"MF-0461": "TD_TAG (voie gauche)", "MF-0460": "TD_TAD (voie droite)", "etat": "usées, blanches", "centrage": "chaque flèche centrée dans sa voie"},
      position=pos(local=None, precision_m=0.5), lien_description="MF-0460;MF-0461", statut="confirme",
      valide_2026=V("incertain", AV + " ; marquages 'conserve'"), confiance="moyenne",
      preuve=preuve("crops/9834f494_v0_a223_sol.jpg", bbox=[0, 600, 780, 850])),
]

# ------------------------------------------------------------------ 6e97bb8c / e540bf1d / 7651c539 (2025-05-18)
S, D = "pnx:6e97bb8c", "2025-05-18"
obs += [
 dict(source=S, date_image=D, classe="arbre", sous_type="grand_feuillu_lierre",
      attributs={"objet": "grand feuillu (≈25 m, couronne ≈15 m), tronc couvert de lierre, en bord SE de Verdun NE devant les immeubles neufs",
                 "position": "tronc triangulé (6e97bb8c, e540bf1d, 7651c539 ; angle 10,6° ; résidus 0,1-0,2 m) en (37,2 ; 10,3) ; arbre_224 (GAM, h 24,6, couronne 14,3) est décrit en (35,4 ; 2,9), à ≈7,5 m : aucun gros tronc n'est visible à la position décrite ; l'ortho 2022 montre une couronne centrée près du point triangulé",
                 "decision": "déplacer arbre_224 vers le tronc observé (ou vérifier l'existence de deux sujets)"},
      position=pos(local=[37.204, 10.257, -1.3], precision_m=1.2, methode="triangulation"), lien_description="arbre_224", statut="position_corrigee",
      valide_2026=V(True, "arbre hors zone de travaux, vu en mai 2025"), confiance="moyenne",
      preuve=preuve("crops/7651c539_L_tronc.jpg", pixels=[[420, 450]])),
 dict(source=S, date_image=D, classe="candelabre", sous_type="poteau_bois_nu",
      attributs={"constat": "sommet du poteau lamp_lidar_VERC_E nu en mai 2025 (pas de lanterne visible)"},
      position=pos(local=[20.654, -6.47, -0.45], precision_m=0.15, methode="triangulation"), lien_description="lamp_lidar_VERC_E", statut="incertain",
      valide_2026=V("incertain", "équipement déposé ou masqué"), confiance="moyenne", preuve=preuve("crops/6e97bb8c_L_lampVERCE.jpg", pixels=[[460, 215]])),
 dict(source=S, date_image=D, classe="mobilier", sous_type="poteau_arret_bus",
      attributs={"constat": "aucun poteau d'arrêt à la position de poteau_REV_ligne42 en mai 2025 : cohérent avec son statut '2026 confirmé' (posé après)"},
      position=P("poteau_REV_ligne42", 0.5), lien_description="poteau_REV_ligne42", statut="absent_sur_image",
      valide_2026=V(True, "objet postérieur à la photo : absence normale, ne remet pas en cause 2026"), confiance="faible",
      preuve=preuve("crops/9834f494_v3_a293_obj.jpg", pixels=[[640, 420]])),
]
S, D = "pnx:7651c539", "2025-05-18"
obs += [
 dict(source=S, date_image=D, classe="panneau", sous_type="AB3a+B2a+M9 (mât Verdun NE)",
      attributs={"vu": "dos des panneaux (disque et triangle gris) depuis le SO : faces vers le NE", "position": "poteau à ≈0,2 m de la position corrigée par la cohérence (1,05 m) : correction confirmée",
                 "panonceau": "petite plaque rectangulaire sous les panneaux (M9)"},
      position=pos(local=None, precision_m=0.3), lien_description="pan_AB3a_2;pan_B2a_1;pan_M9_2", statut="confirme",
      valide_2026=V(True, "Verdun NE hors reconstruction"), confiance="moyenne", preuve=preuve("crops/7651c539_L_AB3a2_ov.jpg", pixels=[[670, 480]])),
]
ecrire("calees_2025_05", obs)
