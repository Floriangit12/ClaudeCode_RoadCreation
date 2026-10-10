from obs_lib import ob

# Marquages « ligne » v0.3 issus de la détection ortho 2022 qui suivent en réalité une bordure,
# une bordurette béton blanche ou un acrotère (revue visuelle des planches de vignettes à 3-4x).
FP = [
    ("917200_6460100", "ML-0148", (917210.85, 6460146.59), "bordurette béton blanche du terre-plein de stationnement (parking des Mitaillères)"),
    ("917200_6460100", "ML-0150", (917214.8, 6460147.52), "bordurette béton blanche du terre-plein de stationnement"),
    ("917200_6460100", "ML-0151", (917217.72, 6460148.15), "bordurette béton blanche (pointe enherbée du terre-plein)"),
    ("917200_6460100", "ML-0225", (917215.78, 6460141.64), "bordurette béton blanche de l'îlot triangulaire à cailloux"),
    ("917200_6460100", "ML-0226", (917217.21, 6460142.49), "bordurette béton blanche de l'îlot triangulaire à cailloux"),
    ("917150_6460150", "ML-0131", (917188.32, 6460156.27), "arête de bordure de l'îlot enherbé en L (parking SE)"),
    ("917150_6460150", "ML-0132", (917188.51, 6460167.35), "tête de bordure entre pelouse et allée de desserte"),
    ("917150_6460150", "ML-0133", (917189.28, 6460157.46), "arête de bordure de l'îlot enherbé en L (parking SE)"),
    ("917150_6460150", "ML-0135", (917191.61, 6460170.6), "tête de bordure entre pelouse et allée de desserte"),
    ("917150_6460350", "ML-0121", (917183.32, 6460383.47), "acrotère blanc de la toiture du bâtiment (pas au sol)"),
    ("917100_6460200", "ML-0102", (917137.27, 6460239.87), "bordurette de la bande centrale pavée du parking"),
    ("917100_6460200", "ML-0106", (917142.51, 6460244.65), "bordurette de la bande centrale pavée du parking"),
    ("917100_6460200", "ML-0201", (917134.94, 6460237.78), "bordurette de la bande centrale pavée du parking"),
    ("917150_6460250", "ML-0112", (917153.1, 6460250.79), "arête de bordure du massif planté (ombre)"),
]
for t, mid, xy, quoi in FP:
    ob("marquage", "faux_positif_bordure", xy, "absent_sur_image", lien=mid, conf="moyenne", prec=0.2, preuve=(mid in ("ML-0150", "ML-0121", "ML-0135")),
       attributs={"observe": f"aucune peinture : l'entité suit {quoi}", "decision_v03": "confirme ortho2022 (à tort)",
                  "action_proposee": "retirer du marquage ; la limite est déjà portée (ou à porter) par la famille bordures / surfaces"},
       valide=False, raison="artefact de détection sur l'ortho 2022 (aucun marquage réel)", tuile=t, cote=7.0)
