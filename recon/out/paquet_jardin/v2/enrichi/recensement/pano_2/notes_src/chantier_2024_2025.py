"""Photos sans pose exploitable (pose refusée trop fausse ou GNSS brut) : constats qualitatifs datés.
1149e115 (2024-05-01, 360°, pose refusée : lacet faux de ≈5°), ab4cfacd / 78424004 / fdc59178 / 8cb2a39c (2025-08-31, à plat, poses refusées),
4e7211a3 / d1bfc7b1 (2025-08-31, à plat, sans pose). Positions = description (identification visuelle) ou aucune."""
import sys; sys.path.insert(0, '..'); sys.path.insert(0, '.')
from note import ecrire, pos, P, V, preuve

CH = "chantier en cours (travaux C1) : état provisoire, sans valeur pour 2026"
obs = [
 dict(source="pnx:1149e115", date_image="2024-05-01", classe="autre", sous_type="chantier_2024",
      attributs={"constat": "cœur du carrefour en chantier le 01/05/2024 : pelles Komatsu et Takeuchi, clôtures Heras, balises K5a rouge/blanc, déblais ; BEV en dalles grises sur le trottoir NE",
                 "consequence": "pose non calable (marquages et mâts masqués) ; photo inutilisable pour 2026 hors bâti et grands arbres"},
      position=pos(local=None, precision_m=10.0), lien_description=None, statut="incertain", valide_2026=V(False, CH),
      confiance="haute", preuve=preuve("crops/1149e115_v1_a108_obj.jpg", bbox=[0, 40, 1200, 600])),
 dict(source="pnx:78424004", date_image="2025-08-31", classe="panneau", sous_type="C113",
      attributs={"code": "C113 (carré bleu, cycle blanc) toujours en place le 31/08/2025 sur son poteau propre, angle NO de Verdun NE ; R11v de feu_NE_droite allumé rouge"},
      position=P("pan_C113_1", 0.3), lien_description="pan_C113_1", statut="confirme",
      valide_2026=V(True, "présent pendant les travaux, support hors reconstruction"), confiance="moyenne",
      preuve=preuve("crops/78424004_L_C113.jpg")),
 dict(source="pnx:fdc59178", date_image="2025-08-31", classe="panneau", sous_type="arret_provisoire",
      attributs={"texte": "ARRÊT PROVISOIRE (panneau orange de chantier, bandes blanc/rouge)", "lieu": "Verdun NE, côté NO, ≈50 m du centre",
                 "autres": "marquage provisoire JAUNE (lignes, chevrons) sur Verdun NE ; panneau orange 'route' à droite"},
      position=pos(local=None, precision_m=5.0), lien_description=None, statut="absent_de_description",
      valide_2026=V(False, CH + " (arrêt et marquages provisoires)"), confiance="haute",
      preuve=preuve("crops/fdc59178_L_panneau.jpg", bbox=[225, 180, 710, 690])),
 dict(source="pnx:4e7211a3", date_image="2025-08-31", classe="feu", sous_type="feu_provisoire_chantier",
      attributs={"objet": "signal tricolore provisoire (boîtier clair, câble pendant) fixé sur un candélabre, côté NO de Verdun SO",
                 "chantier": "rive NO de Verdun SO décaissée (grave), séparateurs modulaires rouge/blanc, clôtures orange"},
      position=pos(local=None, precision_m=5.0), lien_description=None, statut="absent_de_description",
      valide_2026=V(False, CH), confiance="haute", preuve=preuve("crops/4e7211a3_L_feu.jpg", bbox=[380, 170, 620, 690])),
 dict(source="pnx:ab4cfacd", date_image="2025-08-31", classe="marquage", sous_type="anciens_marquages_pendant_travaux",
      attributs={"constat": "zébra et marquages 2022 encore en place au cœur le 31/08/2025, séparateurs rouge/blanc et balise à chevrons rouges sur le TPC SO",
                 "remarque": "les marquages 'fantome' de la description sont donc postérieurs à cette date"},
      position=pos(local=None, precision_m=5.0), lien_description=None, statut="incertain", valide_2026=V(False, CH),
      confiance="moyenne", preuve=preuve("crops/ab4cfacd_v0_a216_obj.jpg", bbox=[0, 330, 1200, 540])),
]
ecrire("chantier_2024_2025", obs)
