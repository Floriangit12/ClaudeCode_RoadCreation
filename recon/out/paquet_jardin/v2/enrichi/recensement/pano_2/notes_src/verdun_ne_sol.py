"""Verdun NE hors zone de travaux (photos calées 2025-05-18) : bordure, ligne de rive, axe, candélabre."""
import sys; sys.path.insert(0, '..'); sys.path.insert(0, '.')
from note import ecrire, pos, P, V, preuve

S, D = "pnx:6e97bb8c", "2025-05-18"
HT = "Verdun NE hors zone de travaux 2025 (bordure K-0353 zone_travaux_2025 = false) : observation valable pour 2026"
obs = [
 dict(source=S, date_image=D, classe="candelabre", sous_type="position_axe",
      attributs={"mesure": "axe du fût à ≈0,5 m derrière l'arête avant de K-0353 (triangulation 6e97bb8c + e5d79de9, angle 28° : 0,52 m ; rayon au sol à 5,9 m : 0,29 m bord avant du fût)",
                 "comparaison": "source OSM sur l'arête (0 m) : faux ; cohérence 0,65 m : légèrement trop loin ; retenir ≈0,5 m (fût Ø ≈0,3 m dans l'herbe, ≈0,1 m derrière le dos de bordure)"},
      position=pos(local=[16.28, 24.21, 0.27], precision_m=0.15, methode="triangulation"), lien_description="lamp_9665416817", statut="position_corrigee",
      valide_2026=V(True, HT), confiance="haute", preuve=preuve("crops/6e97bb8c_L_caniveau.jpg", pixels=[[650, 300]])),
 dict(source=S, date_image=D, classe="bordure", sous_type="T2",
      attributs={"profil_observe": "face quasi verticale (fruit faible) ≈0,13-0,15 m, dessus béton gris ≈0,15 m à arête arrondie, joints d'éléments visibles (≈1 m)", "materiau": "béton gris patiné, salissures noires en pied",
                 "arriere": "herbe/couvre-sol directement derrière la bordure (pas de trottoir)", "position": "arête avant projetée sur l'arête réelle (±2 cm à 4-6 m)",
                 "pied": "bande de ≈0,10-0,15 m d'enrobé avec débris entre la ligne de rive et la bordure ; pas de caniveau béton distinct"},
      position=pos(local=[18.0, 25.5, 0.2], precision_m=0.05, methode="projection_description"), lien_description="K-0353", statut="confirme",
      valide_2026=V(True, HT), confiance="haute", preuve=preuve("crops/6e97bb8c_L_caniveau.jpg", bbox=[0, 0, 650, 900])),
 dict(source=S, date_image=D, classe="marquage", sous_type="ligne_continue_rive",
      attributs={"largeur_observee_m": "0,15-0,17 (3u, u = 5 cm) au lieu de 0,12", "position": "axe réel à ≈0,42 m de l'arête avant de la bordure ; axe décrit à ≈0,24-0,33 m : décaler de ≈+0,12 m vers la chaussée",
                 "etat": "blanc, bon état (usure 1)", "regle": "ligne de rive continue parallèle à la bordure à ≈0,25-0,3 m du fil d'eau"},
      position=pos(local=[17.99, 24.90, 0.17], precision_m=0.05, methode="rayon_sol"), lien_description="ML-5185", statut="position_corrigee",
      valide_2026=V(True, HT + " (ligne 'conserve')"), confiance="moyenne", preuve=preuve("crops/6e97bb8c_L_rive_ov.jpg", pixels=[[560, 600], [640, 600], [688, 600]])),
 dict(source=S, date_image=D, classe="marquage", sous_type="ligne_discontinue_axe_de_voie",
      attributs={"constat": "tirets blancs ≈3 m / intervalles ≈10 m (T1 ?) ; projection sur le bord gauche des tirets (≈0,05-0,08 m)", "largeur_observee_m": 0.15},
      position=pos(local=[19.17, 22.64, 0.21], precision_m=0.1, methode="rayon_sol"), lien_description="ML-5136", statut="confirme",
      valide_2026=V(True, HT), confiance="moyenne", preuve=preuve("crops/6e97bb8c_L_ligne_ov.jpg", bbox=[240, 140, 720, 790])),
]
ecrire("verdun_ne_sol", obs)
