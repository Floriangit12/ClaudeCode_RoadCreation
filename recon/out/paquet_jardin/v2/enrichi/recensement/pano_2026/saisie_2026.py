"""saisie_2026.py : observations (format OBS du recensement) tirées des photos Panoramax du 2026-07-28.

Deux sources, toutes deux postérieures aux travaux (catégorie « photo_2026 » pour la fusion) :
1. recensement visuel (Claude) sur les 3 photos calées (00c1ba9a, f8d91bb1, ded07efa ; poses de
   poses/poses_2026-07-28.json, calage_sequence.py) : découpes perspective avec la description v2
   projetée (vues/*_ov.jpg, *_proj.json), mesures par triangulation des visées (trianguler_2026.py) ou
   rayon au sol (vues_2026.py --pixel) ;
2. conversion des constats p2026_07_ign-01 à 17 (analysis/paquet_jardin/constats_verifies.md), localisés
   par ces mesures quand elles existent, sinon par les coordonnées L93 du constat (précision déclarée).
Les photos 6b2c66d7, 845de418, 05089869, ffc2e8ac ne sont pas calées (refus motivé dans poses/) :
elles ne servent qu'aux constats, sans mesure.

Sortie : ../obs_pano_2026.json (liste triée par id) et bilan_pano_2026.json. Déterministe.
  python saisie_2026.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[6]
sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
sys.dont_write_bytecode = True
from camera import O, z_sol  # noqa: E402

REL = "recon/out/paquet_jardin/v2/enrichi/recensement/pano_2026/"
UUID = {"00c1ba9a": "00c1ba9a-6c74-4cf4-9657-841219eed5fa", "05089869": "05089869-a37a-40f8-a2bc-cd764ec7d7f9",
        "6b2c66d7": "6b2c66d7-bab2-4e2c-9135-529f631109d3", "845de418": "845de418-00b4-48d5-8d74-bbe82f020ec9",
        "ded07efa": "ded07efa-75ec-4289-972a-56c9e98a1309", "f8d91bb1": "f8d91bb1-694d-47fd-b2a4-3f16b57378bb",
        "ffc2e8ac": "ffc2e8ac-50a1-422d-8a27-6514243a81e5"}
HEURE = {"ffc2e8ac": "13:38:54", "05089869": "13:38:56", "845de418": "13:38:58", "6b2c66d7": "13:39:00",
         "00c1ba9a": "13:39:02", "f8d91bb1": "13:39:04", "ded07efa": "13:39:06"}
VALIDE = {"valeur": True, "raison": "photo du 2026-07-28 (UTC), postérieure aux travaux 2025 (fin 05/12/2025, trottoirs du "
                                    "Vercors 30/01/2026) : catégorie photo_2026, prioritaire sur l'ortho 2022 et les photos 2020-2025"}
CALEES = "poses calées (calage_sequence.py, résidu moyen 0,18–0,25°) : 00c1ba9a, f8d91bb1, ded07efa"


def pos(x, y, prec, methode, **kw):
    x, y = float(x), float(y)
    d = {"local": [round(x, 3), round(y, 3), round(z_sol(x, y), 3)],
         "l93": [round(x + O[0], 2), round(y + O[1], 2)], "precision_m": prec, "methode": methode}
    d.update(kw)
    return d


def l93_local(X, Y):
    return X - O[0], Y - O[1]


def obs(n, photo, classe, sous_type, statut, lien, position, attributs, preuve, confiance="haute", valide=None,
        constat=None):
    o = {"id": f"PANO2026-{n:03d}", "source": f"pnx:{UUID[photo]}", "date_image": f"2026-07-28T{HEURE[photo]}",
         "classe": classe, "sous_type": sous_type, "attributs": attributs, "position": position,
         "lien_description": lien, "statut": statut, "valide_2026": valide or VALIDE, "confiance": confiance,
         "preuve": preuve}
    if constat:
        o["constat"] = constat
    return o


def pv(fichier, pixels=None, note=None, autres=None):
    p = {"fichier": REL + fichier}
    if pixels is not None:
        p["pixels"] = pixels
    if note:
        p["note"] = note
    if autres:
        p["autres_vues"] = [REL + a for a in autres]
    return p


O_ = []
# =========================================================================== 1. requalifications (critique)
O_.append(obs(1, "f8d91bb1", "marquage", "zebra", "attribut_corrige", "MP-0085",
              pos(22.37, -134.83, 0.15, "projection_description"),
              {"usure_observee": "0", "etat_propose": "conserve", "couleur": "blanc",
               "nb_bandes": "7 complètes + 1 partielle (vues f8d91bb1 et ded07efa)",
               "note": "zébra du débouché de l'allée blanc franc, bords nets, aucune lacune dans les traces de roues ; l'axe décrit "
                       "se projette au milieu des bandes sur les 3 photos calées. Déjà blanc net en 2020, 2024-08 et 2025-01 "
                       "(constat 03) : aucune remise en peinture 2025 démontrée, état « conservé » et non « refait_2025_identique ». "
                       "La preuve ortho 2022 seule (non valable 2026) est remplacée par cette photo 2026.",
               "requalification": "critique de complétude : non_valable_2026 -> vérifié photo_2026"},
              pv("vues/f8d91bb1_zebra_ov.jpg", [[110, 300], [1070, 370]], "bandes du zébra (y 290–370)",
                 ["vues/ded07efa_vercors_ov.jpg", "vues/00c1ba9a_jonction_ov.jpg"]), constat="p2026_07_ign-03"))
O_.append(obs(2, "f8d91bb1", "marquage", "symbole_velo", "attribut_corrige", "MS-5516",
              pos(26.42, -135.55, 0.15, "projection_description"),
              {"usure_observee": "1", "etat_propose": "conserve", "couleur": "blanc",
               "note": "logo vélo sud (voie de sortie) lisible mais plus terne que le zébra, quelques manques (usure 1, localement 2) ; "
                       "le symbole GAM se projette sur la figure. Présent et net en 2020, 2024-08, 2025-01 : pas de réfection 2025.",
               "requalification": "critique de complétude : non_valable_2026 -> vérifié photo_2026"},
              pv("vues/f8d91bb1_zebra_ov.jpg", [[650, 225], [800, 238]], "figure du logo sud entre les deux rangées jaunes",
                 ["vues/ded07efa_vercors_ov.jpg"]), constat="p2026_07_ign-05"))
O_.append(obs(3, "f8d91bb1", "marquage", "symbole_velo", "attribut_corrige", "MS-5515",
              pos(27.11, -131.37, 0.25, "projection_description"),
              {"usure_observee": "3", "etat_propose": "conserve", "couleur": "blanc",
               "note": "logo vélo nord (voie d'entrée) réduit à des vestiges très effacés à la position GAM (usure 3) ; net en 2020, "
                       "déjà grisé en 2024-08 et 2025-01 : usure antérieure aux travaux (roues, âge).",
               "requalification": "critique de complétude : non_valable_2026 -> vérifié photo_2026"},
              pv("vues/f8d91bb1_zebra_ov.jpg", [[160, 200], [300, 212]], "vestiges blanchâtres entre les rangées jaunes"),
              confiance="moyenne", constat="p2026_07_ign-05"))
O_.append(obs(4, "f8d91bb1", "marquage", "ligne_segment", "absent_sur_image", "ML-0432",
              pos(33.12, -137.56, 0.2, "projection_description"),
              {"observe": "à la position décrite (33,1 ; −137,6), herbe de l'îlot derrière le nez de bordure, sans aucune peinture, "
                          "sur les deux photos calées les plus proches (f8d91bb1 à 20 m, ded07efa à 19 m) ; la ligne d'effet du STOP 2026 "
                          "passe 0,7 à 1,5 m plus au nord-est (PANO2026-010). Tiret v1 isolé confirmé à tort par le contrôle "
                          "automatique de l'ortho 2022 (nez d'îlot ou ancienne ligne) : entité à supprimer.",
               "requalification": "critique de complétude : confirmation automatique non fiable -> absent 2026"},
              pv("vues/f8d91bb1_z_ml0432_ov.jpg", [[230, 205], [350, 212]], "projection de ML-0432 sur l'herbe de l'îlot",
                 ["vues/ded07efa_z_ml0432_ov.jpg", "vues/00c1ba9a_z_fleche_ov.jpg"])))
for n, eid, x, y in ((5, "ML-0433", 35.54, -144.81), (6, "ML-0434", 39.94, -143.86)):
    O_.append(obs(n, "f8d91bb1", "marquage", "ligne_segment", "incertain", eid, pos(x, y, 0.5, "projection_description"),
                  {"observe": "chaussée de Vercors refaite entre 2025-01 et 2026-07 (enrobé neuf, constat 13) : la peinture vue sur l'ortho "
                              "2022 a disparu sous l'enrobé, l'ortho ne prouve rien pour 2026 ; sur les photos calées le secteur est vu à "
                              "25–30 m en incidence rasante, derrière la végétation de l'îlot sud, le AB3a et le panneau blanc : ni présence "
                              "ni absence établie. Les lignes GAM 2026 voisines (ML-5400, ML-5405, ML-5404) sont la référence ; tiret v1 "
                              "isolé probablement redondant.",
                   "etat_description": "refait_2025_identique (non démontré)",
                   "requalification": "critique de complétude : non_valable_2026 -> non vérifiable sur photo 2026"},
                  pv("vues/f8d91bb1_z_vercors_sud_ov.jpg", note="ligne projetée sur la chaussée lointaine, masquée",
                     autres=["vues/00c1ba9a_z_vercors_sud_ov.jpg"]),
                  confiance="faible", valide={"valeur": "incertain", "raison": "secteur non lisible sur les photos 2026"}))
O_.append(obs(7, "ded07efa", "marquage", "fleche", "incertain", "MF-5523", pos(38.72, -135.58, 0.5, "projection_description"),
              {"observe": "masquée par la voiture rouge arrêtée au STOP sur les 3 photos calées (00c1ba9a, f8d91bb1, ded07efa) ; la partie "
                          "visible à droite de la voiture ne montre pas de peinture, non concluant. La chaussée de Vercors au droit de "
                          "l'allée a été refaite entre 2025-01 et 2026-07 (constat 13) : si la flèche existe (bloc GAM SYMBOLE_FLECHE_DROIT), "
                          "elle a été repeinte après la réfection ; état à requalifier « refait » (géométrie 2022 non probante), pas "
                          "« refait_2025_identique ».",
               "requalification": "critique de complétude : non_valable_2026 -> masquée sur photo 2026"},
              pv("vues/ded07efa_z_fleche_ov.jpg", [[300, 170], [910, 560]], "voiture arrêtée au STOP devant la flèche projetée",
                 ["vues/00c1ba9a_z_fleche_ov.jpg", "vues/f8d91bb1_z_fleche_ov.jpg"]),
              confiance="faible", valide={"valeur": "incertain", "raison": "objet masqué par un véhicule sur les photos 2026"}))

# =========================================================================== 2. marquages du débouché
for n, eid0, eid1, c, t0, t1, nom in ((8, "MQ0039", "MQ0049", (24.97, -134.0), (24.35, -131.06), (25.6, -136.93), "ouest"),
                                      (9, "MQ0385", "MQ0395", (28.43, -133.0), (27.7, -130.09), (29.16, -135.91), "est")):
    O_.append(obs(n, "f8d91bb1", "marquage", "paves_jaunes_traversee_cyclable", "absent_de_description", None,
                  pos(c[0], c[1], 0.15, "projection_description"),
                  {"couleur": "jaune", "usure_observee": "0", "etat_propose": "conserve", "nb_paves": 11,
                   "dimensions": "pavés ≈ 0,92 × 0,44 m au pas ≈ 0,6 m (paquet v1 " + eid0 + "–" + eid1 + ")",
                   "trace_local": [list(t0), list(t1)],
                   "note": f"rangée {nom} de pavés jaunes bordant la traversée de la piste cyclable bidirectionnelle (GAM : 300 cm) ; jaune "
                           "vif, blocs nets. Marquage permanent présent en 2020, 2022, 2024-08 et 2025-01 (constat 04), absent de la "
                           "description v2 (seul le paquet v1 l'a) ; géométrie du paquet cohérente avec les photos calées (coins utilisés "
                           "comme points d'appui). Axe jaune pointillé de la piste non distingué sur les vues 2026."},
                  pv("vues/f8d91bb1_zebra_ov.jpg", [[20, 250], [910, 258]] if nom == "ouest" else [[105, 190], [1095, 195]],
                     f"rangée {nom}", ["vues/ded07efa_vercors_ov.jpg"]), constat="p2026_07_ign-04"))
O_.append(obs(10, "ded07efa", "marquage", "ligne_effet_stop", "absent_de_description", None,
              pos(33.65, -134.63, 0.4, "rayon_sol", geometrie_l93=[[917312.75, 6460157.28], [917313.42, 6460153.42]]),
              {"couleur": "blanc", "usure_observee": "0", "etat_propose": "neuf_2025", "largeur_observee_m": "0.5 (probable)",
               "modulation_proposee": "continue", "trace_local": [[33.32, -132.70], [33.99, -136.56]],
               "note": "ligne d'effet du STOP transversale, continue, de l'axe de l'allée jusqu'au nez de l'îlot sud (≈ 3,9 m, demi-chaussée "
                       "de sortie), posée sur l'enrobé neuf de Vercors : repeinte après la réfection (2025-01 à 2026-07). Extrémités "
                       "mesurées par rayon au sol sur ded07efa et f8d91bb1 (écart entre photos ≤ 0,15 m) ; x ≈ 917312,7–917313,4, "
                       "1 à 2 m plus à l'est que l'estimation du constat 06."},
              pv("vues/ded07efa_z_fleche_ov.jpg", [[20, 437], [300, 433]], "ligne transversale (prolongée derrière la voiture)",
                 ["vues/f8d91bb1_zebra_ov.jpg", "vues/00c1ba9a_z_fleche_ov.jpg"]), constat="p2026_07_ign-06"))
O_.append(obs(11, "ded07efa", "marquage", "ligne_continue_axiale", "absent_de_description", None,
              pos(31.29, -133.03, 0.4, "rayon_sol", geometrie_l93=[[917308.69, 6460156.62], [917312.75, 6460157.28]]),
              {"couleur": "blanc", "usure_observee": "0", "etat_propose": "neuf_2025", "modulation_proposee": "continue",
               "trace_local": [[29.26, -133.36], [33.32, -132.70]],
               "note": "branche longitudinale du « L » : ligne axiale continue d'approche (≈ 4,1 m) prolongeant les tirets T3 jusqu'à la "
                       "ligne de STOP ; absente en 2024-08, posée sur l'enrobé neuf (constat ajout-12)."},
              pv("vues/ded07efa_z_fleche_ov.jpg", [[20, 437], [180, 545]], "branche longitudinale du L",
                 ["vues/f8d91bb1_zebra_ov.jpg"]), constat="p2026_07_ign-06"))
O_.append(obs(12, "00c1ba9a", "marquage", "ligne_discontinue_axe", "attribut_corrige", "ML-5452",
              pos(13.0, -135.6, 0.3, "projection_description"),
              {"usure_observee": "1", "etat_propose": "conserve", "modulation_proposee": "T3 (≈ 2,9 / 1,4 m)",
               "section_l93": "x ≈ 917285–917300 (débouché)",
               "note": "tirets d'axe de l'allée près du débouché : blancs, continus, minces, contraste modéré (usure 1) ; le tiret vers "
                       "x ≈ 917291–295 est fragmenté (usure 2–3 localement). Tirets alignés sur le levé GAM (ils ont servi de points "
                       "d'appui). Aucune remise en peinture : état « conservé » et non « refait_2025_identique »."},
              pv("vues/00c1ba9a_jonction_ov.jpg", [[300, 560], [440, 420]], "tirets avant",
                 ["vues/f8d91bb1_ouest_ov.jpg"]), constat="p2026_07_ign-07"))
O_.append(obs(13, "6b2c66d7", "marquage", "ligne_discontinue_axe", "attribut_corrige", "ML-5452",
              pos(-4.0, -138.6, 3.0, "constat"),
              {"usure_observee": "2", "etat_propose": "conserve",
               "section_l93": "x ≈ 917265–917285 (partie ouest)",
               "note": "tirets presque invisibles dos au soleil (usure 3 dans cette condition, 6b2c66d7 et 845de418), lisibles mais "
                       "fragmentés en contre-jour (≈ 2, f8d91bb1 vue arrière) : peinture mince et usée ; détection ADAS dépendante de "
                       "l'éclairage. Plus à l'ouest (x ≤ 917260), tirets continus (usure ≈ 1). Écart d'usure avec la section est : "
                       "l'entité devrait être découpée."},
              pv("vues/f8d91bb1_ouest_ov.jpg", [[895, 530], [945, 660]], "tiret arrière (contre-jour) vu depuis la photo calée f8d91bb1"),
              confiance="moyenne", constat="p2026_07_ign-08"))
O_.append(obs(14, "00c1ba9a", "marquage", "lignes_stationnement", "confirme",
              "ML-5337; ML-5358; ML-5338; ML-5339; ML-5340; ML-5345; ML-5344; ML-5343; ML-5342; ML-5341",
              pos(5.3, -131.3, 0.2, "projection_description"),
              {"usure_observee": "1", "couleur": "blanc",
               "note": "lignes des places perpendiculaires du parking privé « L'Horloge » : les lignes GAM se projettent sur les lignes "
                       "visibles entre les voitures (00c1ba9a, f8d91bb1) ; lisibles avec quelques manques, plus effacées vers l'ouest "
                       "(usure 1 à 2, conforme à la description)."},
              pv("vues/00c1ba9a_nord_ov.jpg", [[400, 495], [640, 445], [1150, 490]], "ML-5339, ML-5340, ML-5344",
                 ["vues/f8d91bb1_nord_ov.jpg"]), constat="p2026_07_ign-09"))

# =========================================================================== 3. signalisation verticale et mâts (triangulés)
TRI = "triangulation des visées (trianguler_2026.py, photos calées)"
O_.append(obs(15, "f8d91bb1", "panneau", "AB4", "position_corrigee", "pan_AB4_2",
              pos(32.222, -137.570, 0.3, "triangulation"),
              {"code": "AB4", "face": "face vers l'O (vers l'allée)", "gamme": "petite gamme probable",
               "triangulation": "3 visées (f8d91bb1, ded07efa, 00c1ba9a), angle d'intersection 17°, résidus ≤ 0,02 m",
               "implantation": "îlot herbeux entre la piste cyclable et Vercors, ≈ 1 m au sud-est de sa pointe nord-ouest "
                               "(nez mesuré vers (31,5–32,1 ; −136,6))",
               "note": "STOP de la sortie de l'allée, associé à la ligne d'effet PANO2026-010. Position 2026 à 0,9 m de pan_AB4_2 ; "
                       "elle contredit le déplacement proposé par ORTHO-B-123 (917308,9 / 6460153,95, 3,2 m plus à l'ouest) et le "
                       "constat 15 (poteau de l'ortho 2022 vers 917308,8 / 6460154,2) : le poteau 2022 n'est pas le STOP 2026 "
                       "(autre objet, ou îlot remodelé par les travaux : non établi)."},
              pv("vues/f8d91bb1_vercors_ov.jpg", [[625, 140], [625, 390]], "STOP et son poteau",
                 ["vues/ded07efa_vercors_ov.jpg", "vues/00c1ba9a_z_fleche_ov.jpg"]), constat="p2026_07_ign-15"))
O_.append(obs(16, "f8d91bb1", "panneau", "AB3a", "position_corrigee", "pan_AB3a_3",
              pos(25.715, -138.949, 0.15, "triangulation"),
              {"code": "AB3a", "face": "face vers l'O (vers l'allée)", "gamme": "petite gamme probable",
               "triangulation": "3 visées (f8d91bb1, ded07efa, 00c1ba9a), angle d'intersection 27°, résidus ≤ 0,01 m",
               "implantation": "petit terre-plein (refuge I-0658) à l'angle sud-ouest de la traversée cyclable, sur la dalle béton au "
                               "regard, à l'ouest de la piste",
               "note": "cédez-le-passage aux cycles de la piste bidirectionnelle (déduit). pan_AB3a_3 (29,47 ; −137,18) est placé sur le "
                       "poteau 2022 attribué au STOP : 4,1 m d'écart. Arbitrage du constat ajout-09 confirmé (AB3a à l'ouest de la piste)."},
              pv("vues/f8d91bb1_vercors_ov.jpg", [[900, 195], [885, 490]], "AB3a et son poteau",
                 ["vues/ded07efa_vercors_ov.jpg", "vues/00c1ba9a_z_fleche_ov.jpg"]), constat="p2026_07_ign-14"))
O_.append(obs(17, "f8d91bb1", "panneau", "panneau_information_2_poteaux", "absent_de_description", None,
              pos(21.899, -140.095, 0.15, "triangulation"),
              {"texte": "panneau blanc sur deux poteaux, plaque « ACCÈS » avec flèche et pictogramme (« ACCÈS 53 » lisible en 2020 et 2025-01)",
               "face": "face vers l'O", "poteaux_local": [[21.755, -139.68], [22.043, -140.51]],
               "triangulation": "chaque poteau : 3 visées, angle d'intersection 39°, résidus ≤ 0,03 m",
               "note": "à côté du AB3a, à l'ouest du refuge I-0658 (constats 14 et 16)."},
              pv("vues/f8d91bb1_z_vercors_sud_ov.jpg", [[612, 400], [852, 400]], "deux poteaux",
                 ["vues/00c1ba9a_z_vercors_sud_ov.jpg", "vues/ded07efa_jonction_ov.jpg"]), constat="p2026_07_ign-16"))
O_.append(obs(18, "f8d91bb1", "candelabre", "lampadaire_0456", "position_corrigee", "lamp_9514828517; pan_B6a1_1; pan_C13a_1",
              pos(13.250, -140.345, 0.05, "triangulation"),
              {"plaque": "n° 0456 lisible sur le fût", "couleur_mat": "gris galvanisé",
               "equipements": "B6a1 (rond) au-dessus de C13a (impasse), faces vers l'est (entrée depuis Vercors)",
               "triangulation": "3 visées (f8d91bb1 à 3,8 m, ded07efa, 00c1ba9a), angle d'intersection 88°, résidus ≤ 0,04 m ; pied "
                                "confirmé par rayon au sol (13,19–13,81 ; −140,21 à −140,47)",
               "note": "pied du fût à 0,70 m à l'est de la position du paquet (nœud OSM = lanterne vue sur l'ortho, ORTHO-B-166)."},
              pv("vues/f8d91bb1_sud_ov.jpg", [[810, 80], [806, 622]], "fût du candélabre 0456 avec B6a1 et C13a",
                 ["vues/ded07efa_z_lamp0456_ov.jpg", "vues/00c1ba9a_z_arbre015_ov.jpg"]), constat="p2026_07_ign-16"))
O_.append(obs(19, "ded07efa", "candelabre", "lampadaire_0530", "position_corrigee", "lamp_9514828431",
              pos(34.767, -141.195, 0.3, "triangulation"),
              {"triangulation": "2 visées (f8d91bb1, ded07efa), angle d'intersection 10°, résidus nuls (pas de redondance)",
               "implantation": "bord est de l'îlot herbeux entre la piste et Vercors",
               "note": "concorde à 0,7 m avec le constat ajout-05 (pied 917313,6 / 6460149,2) ; la position du paquet (32,89 ; −141,08) est "
                       "1,9 m trop à l'ouest."},
              pv("vues/ded07efa_vercors_ov.jpg", [[657, 0], [657, 375]], "mât derrière l'îlot",
                 ["vues/f8d91bb1_vercors_ov.jpg"]), confiance="moyenne"))
for n, c, nom, px0, px1, code, texte in (
        (20, (9.396, -127.022), "est", [965, 260], [735, 255], "B6a1",
         "B6a1 + panonceau « PARKING PRIVÉ L'HORLOGE — DÉFENSE DE STATIONNER »"),
        (21, (2.804, -128.121), "milieu", [593, 270], [397, 270], "panneau bleu carré (symbole effacé, C1a probable)",
         "panneau bleu + panonceau « Réservé L'HORLOGE »"),
        (22, (-3.424, -129.214), "ouest", [245, 285], [176, 268], "B6a1",
         "B6a1 + panonceau « PARKING PRIVÉ L'HORLOGE — DÉFENSE DE STATIONNER »")):
    O_.append(obs(n, "00c1ba9a", "panneau", "panneau_parking_prive", "absent_de_description", None,
                  pos(c[0], c[1], 0.3, "triangulation"),
                  {"code": code, "texte": texte, "face": "face vers le S (vers l'allée)",
                   "triangulation": "2 visées (00c1ba9a, f8d91bb1), angle d'intersection 25–38°",
                   "note": f"poteau {nom} du parking privé L'Horloge, en fond de places côté nord de l'allée ; panneau privé "
                           "(pas de pan_* du paquet à moins de 10 m ; pan_B6a1_2 est 13 m plus à l'ouest)."},
                  pv("vues/00c1ba9a_nord_ov.jpg", [px0], "panneau et poteau", ["vues/f8d91bb1_nord_ov.jpg",
                                                                              f"vues/00c1ba9a_pn_{ {'est': 'b6a1_e', 'milieu': 'reserve', 'ouest': 'b6a1_o'}[nom]}_brut.jpg"]),
                  constat="p2026_07_ign-16"))
O_.append(obs(23, "f8d91bb1", "panneau", "C13a_dos", "absent_de_description", None, pos(23.5, -129.6, 0.5, "rayon_sol"),
              {"code": "C13a", "texte": "plaque « Allée des Mitaillères » (lue sur les photos antérieures, constat ajout-10)",
               "face": "face vers l'E (vu de dos depuis l'allée)",
               "mesure": "rayon au sol du pied sur f8d91bb1 (23,66 ; −129,50) et intersection de 2 visées (angle 6°, 23,35 ; −129,69)",
               "note": "terre-plein herbeux nord-ouest (à l'ouest de la piste, sous la haie)."},
              pv("vues/f8d91bb1_pn_nord_ilot_ov.jpg", [[548, 180], [548, 585]], "poteau du C13a (dos)",
                 ["vues/00c1ba9a_pn_nord_ilot_ov.jpg"]), confiance="moyenne", constat="p2026_07_ign-16"))
O_.append(obs(24, "f8d91bb1", "panneau", "AB3a_dos", "absent_de_description", None, pos(30.7, -126.2, 1.0, "rayon_sol"),
              {"code": "AB3a", "face": "face vers l'E (vers les véhicules entrant depuis Vercors ; vu de dos)",
               "mesure": "rayon au sol du pied sur f8d91bb1 ; l'intersection avec 00c1ba9a (angle 4°) est peu fiable",
               "note": "second AB3a sur l'îlot nord (I-0673) entre la piste et Vercors (constat ajout-10)."},
              pv("vues/f8d91bb1_pn_nord_ilot_ov.jpg", [[648, 245], [648, 475]], "triangle vu de dos et son poteau"),
              confiance="moyenne", constat="p2026_07_ign-16"))

# =========================================================================== 4. végétation, îlots, surfaces
O_.append(obs(25, "ded07efa", "haie", "haie_haute", "absent_de_description", "S-0111a",
              pos(19.97, -129.7, 0.5, "rayon_sol"),
              {"hauteur_estimee_m": "3.5 (probable)", "epaisseur_estimee_m": "2 à 3",
               "trace_local": [[17.26, -126.93], [18.07, -130.04], [20.01, -131.13], [22.49, -130.94]],
               "note": "haie haute dense (feuillus taillés) sur le terre-plein nord-ouest, au nord de l'allée et à l'ouest de la piste, "
                       "se prolongeant vers le nord le long du parking ; masque la vue vers le nord pendant l'approche (constat 21). "
                       "Pieds mesurés par rayons au sol sur ded07efa et f8d91bb1."},
              pv("vues/ded07efa_jonction_ov.jpg", [[0, 0], [240, 560]], "haie à gauche",
                 ["vues/ded07efa_nord_ov.jpg", "vues/f8d91bb1_pn_nord_ilot_ov.jpg"]), confiance="moyenne"))
O_.append(obs(26, "00c1ba9a", "arbre", "absent", "absent_sur_image", "arbre_013", pos(6.112, -143.75, 0.3, "projection_description"),
              {"observe": "pelouse rase à la position du levé GAM (ARBRE_FEUILLU, hauteur par défaut), aucun arbre ni arbuste"},
              pv("vues/00c1ba9a_sud_ov.jpg", [[630, 515]], "position projetée", ["vues/f8d91bb1_ouest_ov.jpg"])))
O_.append(obs(27, "00c1ba9a", "arbre", "absent", "absent_sur_image", "arbre_015", pos(14.585, -142.079, 0.3, "projection_description"),
              {"observe": "pelouse à la position du levé GAM, aucun arbre (vu depuis 00c1ba9a et f8d91bb1)"},
              pv("vues/00c1ba9a_z_arbre015_ov.jpg", [[475, 345]], "position projetée", ["vues/f8d91bb1_sud_ov.jpg"])))
O_.append(obs(28, "00c1ba9a", "arbre", "arbuste", "confirme", "arbre_014", pos(10.353, -142.882, 0.5, "projection_description"),
              {"type_observe": "arbuste", "hauteur_estimee_m": "2.5 (probable)",
               "observe": "arbuste buissonnant feuillu à la position décrite"},
              pv("vues/00c1ba9a_z_arbre015_ov.jpg", [[650, 150], [900, 440]], "arbuste", ["vues/ded07efa_z_lamp0456_ov.jpg"]),
              confiance="moyenne"))
O_.append(obs(29, "f8d91bb1", "arbre", "jeune_arbre", "confirme", "arbre_016", pos(18.89, -141.179, 0.5, "projection_description"),
              {"hauteur_estimee_m": "3 (probable)", "observe": "jeune arbre buissonnant à la position décrite"},
              pv("vues/f8d91bb1_sud_ov.jpg", [[230, 240], [400, 430]], "jeune arbre", ["vues/00c1ba9a_z_arbre015_ov.jpg"]),
              confiance="moyenne"))
O_.append(obs(30, "ded07efa", "arbre", "absent", "absent_sur_image", "arbre_018", pos(30.339, -139.808, 0.5, "projection_description"),
              {"observe": "îlot en herbe sans arbre à la position du saule de l'inventaire, comme attendu (statut « absent 2026 » de la description)"},
              pv("vues/ded07efa_jonction_ov.jpg", [[800, 345]], "position projetée sur l'îlot")))
O_.append(obs(31, "ded07efa", "arbre", "souche", "confirme", "arbre_029", pos(15.19, -126.594, 0.3, "projection_description"),
              {"type_observe": "souche", "observe": "souche d'environ 0,4 m au fond du parking, à la position du levé GAM (SOUCHE)"},
              pv("vues/ded07efa_nord_ov.jpg", [[430, 420], [560, 480]], "souche")))
O_.append(obs(32, "ded07efa", "ilot", "refuge_terre_plein", "attribut_corrige", "I-0658", pos(25.6, -138.8, 0.3, "projection_description"),
              {"remplissage_observe": "gazon (herbe grillée par la sécheresse estivale)",
               "objets_portes_observes": "AB3a (PANO2026-016) sur une dalle béton avec regard dans la partie nord (≈ 24,7–26,3 ; "
                                         "−139,3 à −138,1, rayons au sol)",
               "note": "petit terre-plein entre le zébra et la piste cyclable (constat 17) ; contour décrit cohérent avec la photo ; le "
                       "panneau blanc à deux poteaux (PANO2026-017) est juste à l'ouest, hors de l'îlot."},
              pv("vues/ded07efa_vercors_ov.jpg", [[650, 500], [940, 550]], "dalle et regard, AB3a", ["vues/f8d91bb1_vercors_ov.jpg"]),
              confiance="moyenne", constat="p2026_07_ign-17"))
O_.append(obs(33, "f8d91bb1", "tampon", "regard_dalle", "absent_de_description", "I-0658", pos(25.5, -138.7, 0.4, "rayon_sol"),
              {"forme": "dalle béton carrée portant un regard (dimension non mesurée)",
               "note": "sur le refuge I-0658, au pied du AB3a (constat 17 : « dalle avec regard »)."},
              pv("vues/ded07efa_vercors_ov.jpg", [[700, 515], [930, 520]], "dalle", ["vues/f8d91bb1_vercors_ov.jpg"]),
              confiance="moyenne", constat="p2026_07_ign-17"))
O_.append(obs(34, "f8d91bb1", "surface", "chaussee_enrobe_neuf", "attribut_corrige", "S-0268a",
              pos(*l93_local(917317.5, 6460157.5), 7.5, "constat",
                  geometrie_l93=[[917309.0, 6460145.0], [917325.0, 6460145.0], [917325.0, 6460170.0], [917309.0, 6460170.0],
                                 [917309.0, 6460145.0]]),
              {"materiau_propose": "enrobe_bbsg_neuf_2025", "etendue_l93": [[917309.0, 6460145.0], [917325.0, 6460170.0]],
               "sous_zone": "Vercors au droit de l'allée et bouche de l'allée à l'est de la traversée cyclable (ne pas requalifier "
                            "tout le polygone)",
               "note": "enrobé neuf sombre et homogène (≈ 144/141/138 contre ≈ 207/198/188 sur l'allée, f8d91bb1) ; limite avec "
                       "l'enrobé ancien au bord est de la traversée cyclable (rangée jaune est, x ≈ 917308–309), la ligne de STOP est "
                       "posée dessus. Clair sur l'ortho 2024, gris et faïencé en 2024-08 et 2025-01 : réfection entre 2025-01 et "
                       "2026-07 (phase Vercors des travaux C1 probable, non démontrée)."},
              pv("vues/f8d91bb1_vercors_ov.jpg", [[0, 300], [1200, 400]], "chaussée sombre de Vercors au-delà de l'îlot",
                 ["vues/ded07efa_jonction_ov.jpg"]), confiance="moyenne", constat="p2026_07_ign-13"))
O_.append(obs(35, "f8d91bb1", "surface", "chaussee_enrobe_neuf", "attribut_corrige", "S-0268d; S-0268e",
              pos(30.4, -131.5, 1.0, "constat"),
              {"materiau_propose": "enrobe_bbsg_neuf_2025",
               "note": "bouche de l'allée à l'est de la rangée jaune est : enrobé neuf sombre continu avec Vercors (constat 13)."},
              pv("vues/f8d91bb1_zebra_ov.jpg", [[300, 120], [900, 180]], "enrobé sombre au-delà des pavés jaunes"),
              confiance="moyenne", constat="p2026_07_ign-13"))
O_.append(obs(36, "00c1ba9a", "surface", "chaussee_enrobe_ancien", "confirme", "S-0268b; S-0268c",
              pos(*l93_local(917282.5, 6460153.0), 15.0, "constat"),
              {"materiau_observe": "enrobe_bbsg_ancien",
               "texture": "enrobé ancien gris clair, granulats apparents, texture ouverte et sèche, sans ressuage",
               "degradation": "faïençage généralisé (maillage fin) et fissures longitudinales et transversales, surtout à l'ouest et le "
                              "long du parking ; ni nid-de-poule ni arrachement (constat 11)",
               "note": "aucune reprise ni tranchée récente sur la section vue ; teinte bien plus claire que Vercors."},
              pv("vues/00c1ba9a_jonction_ov.jpg", [[0, 420], [1200, 800]], "chaussée de l'allée", ["vues/f8d91bb1_ouest_ov.jpg"]),
              confiance="haute", constat="p2026_07_ign-10"))
O_.append(obs(37, "6b2c66d7", "surface", "degradation_taches_sombres", "incertain", None,
              pos(*l93_local(917290.0, 6460153.5), 2.0, "constat"),
              {"observe": "deux taches sombres quasi rectangulaires, symétriques, dans les traces de roues de la voie vers l'est, "
                          "≈ 8–12 m devant 6b2c66d7 (égouttures d'hydrocarbures ou petites reprises : hypothèses)",
               "etendue_l93": [[917288.0, 6460152.0], [917292.0, 6460155.0]]},
              pv("vues/00c1ba9a_jonction_ov.jpg", note="photo source du constat non calée (6b2c66d7) ; zone visible au premier plan de 00c1ba9a"),
              confiance="faible", constat="p2026_07_ign-12"))
O_.append(obs(38, "00c1ba9a", "surface", "degradation_fissuration", "attribut_corrige", "S-0268b",
              pos(*l93_local(917270.0, 6460152.0), 20.0, "constat"),
              {"degradation": "faïençage généralisé et fissures longitudinales/transversales (allée, partie ouest et bord du parking)",
               "etendue_l93": [[917250.0, 6460145.0], [917290.0, 6460160.0]]},
              pv("vues/f8d91bb1_ouest_ov.jpg", [[300, 500], [1100, 800]], "fissuration de l'allée vers l'ouest"),
              confiance="moyenne", constat="p2026_07_ign-11"))

# =========================================================================== 5. constats de contexte et mobilier non mesuré
O_.append(obs(39, "f8d91bb1", "autre", "hors_emprise_prise_de_vue", "incertain", None,
              pos(*l93_local(917290.0, 6460156.0), 12.0, "constat"),
              {"note": "lieu réel des 7 prises de vue : allée des Mitaillères et son débouché sur Vercors, ≈ 130 m au sud du carrefour ; "
                       "le carrefour à feux n'est visible sur aucune (haie et arbres au nord). Poses : " + CALEES +
                       " ; 6b2c66d7 (ambiguïté le long de l'allée), 845de418, 05089869, ffc2e8ac non calées."},
              pv("poses/poses_2026-07-28.json"), valide={"valeur": True, "raison": "contexte"}, constat="p2026_07_ign-01"))
O_.append(obs(40, "f8d91bb1", "autre", "hors_emprise_azimut_gnss", "incertain", None,
              pos(*l93_local(917290.0, 6460156.0), 12.0, "constat"),
              {"note": "azimut Panoramax faux dans le virage (trace GNSS) ; lacets calés (grille) : 00c1ba9a 84,4° (annoncé 52,0°), "
                       "f8d91bb1 56,5° (annoncé 2,0°), ded07efa 14,0° (annoncé 2,0°) ; positions GNSS décalées de 5,0 à 6,0 m. Toute "
                       "projection fondée sur les métadonnées serait fausse de 12 à 54°."},
              pv("poses/poses_2026-07-28.json"), valide={"valeur": True, "raison": "contexte"}, constat="p2026_07_ign-02"))
O_.append(obs(41, "6b2c66d7", "mobilier", "barriere_levante", "confirme", "barriere_levante_3375058657",
              pos(-16.267, -130.713, 1.0, "constat"),
              {"note": "barrière levante à l'entrée ouest du parking L'Horloge (6b2c66d7 r01_c00 ; nœud OSM lift_gate 917263,2 / 6460159,3)"},
              pv("vues/00c1ba9a_ouest_ov.jpg", note="photo source du constat non calée"), confiance="moyenne", constat="p2026_07_ign-16"))
O_.append(obs(42, "00c1ba9a", "panneau", "fleche_directionnelle_privee", "absent_de_description", None,
              pos(*l93_local(917290.0, 6460149.0), 4.0, "constat"),
              {"texte": "« ← Cabinet kinésithérapie »", "note": "panneau directionnel privé côté sud (00c1ba9a r01_c05), position non mesurée"},
              pv("vues/00c1ba9a_sud_ov.jpg"), confiance="faible", constat="p2026_07_ign-16"))
O_.append(obs(43, "05089869", "panneau", "C1a_reserve", "absent_de_description", None,
              pos(*l93_local(917258.0, 6460160.0), 3.0, "constat"),
              {"code": "C1a", "texte": "« P » + panonceau « Réservé L'Horloge »",
               "note": "plus à l'ouest que le panneau bleu PANO2026-021 (05089869 r01_c01) ; position estimée (constat 16)"},
              pv("poses/poses_2026-07-28.json", note="photo source non calée"), confiance="faible", constat="p2026_07_ign-16"))
O_.append(obs(44, "ded07efa", "bordure", "terre_pleins_jonction", "confirme", "K-0658; K-0658z; K-0513; K-0420; K-0667",
              pos(28.5, -137.5, 1.0, "projection_description"),
              {"note": "bordures des terre-pleins de l'angle sud et nord (constat 17) : refuge herbeux entre zébra et piste (I-0658), îlot "
                       "herbeux bordé entre piste et Vercors (STOP à sa pointe nord-ouest, candélabre 0530 sur son bord est), îlot nord "
                       "(AB3a dos) ; contours décrits cohérents avec les photos calées ; rien n'indique de modification côté allée "
                       "depuis 2022."},
              pv("vues/ded07efa_vercors_ov.jpg", [[300, 430], [1200, 550]], "bordures des terre-pleins",
                 ["vues/f8d91bb1_vercors_ov.jpg"]), confiance="moyenne", constat="p2026_07_ign-17"))
O_.append(obs(45, "00c1ba9a", "bordure", "bordure_basse_parking", "confirme", "K-0645; K-0670",
              pos(5.6, -133.7, 0.3, "projection_description"),
              {"note": "bordure basse en béton clair entre l'allée et le parking nord (K-0645) et fond des places (K-0670) : projetées sur "
                       "les bordures visibles (constat 17 : « bordure basse en béton clair »)."},
              pv("vues/00c1ba9a_nord_ov.jpg", [[0, 500], [1200, 505]], "bordure basse", ["vues/f8d91bb1_nord_ov.jpg"]),
              constat="p2026_07_ign-17"))
O_.append(obs(47, "00c1ba9a", "arbre", "feuillu", "confirme", "arbre_026", pos(-1.329, -127.376, 0.5, "projection_description"),
              {"observe": "grand feuillu au fond du parking L'Horloge, tronc sur la position du levé GAM"},
              pv("vues/00c1ba9a_nord_ov.jpg", [[405, 150], [410, 345]], "tronc et couronne", ["vues/f8d91bb1_nord_ov.jpg"])))
O_.append(obs(48, "f8d91bb1", "ilot", "ilot_nord", "confirme", "I-0673", pos(28.3, -127.2, 0.3, "projection_description"),
              {"remplissage_observe": "gazon (herbe sèche)",
               "objets_portes_observes": "AB3a tourné vers l'est (PANO2026-024)",
               "note": "îlot herbeux bordé entre la piste et Vercors à l'angle nord : contour décrit (K-0673) superposé au contour visible."},
              pv("vues/f8d91bb1_pn_nord_ilot_ov.jpg", [[420, 470], [760, 520]], "îlot nord", ["vues/00c1ba9a_pn_nord_ilot_ov.jpg"]),
              confiance="moyenne", constat="p2026_07_ign-17"))
O_.append(obs(46, "f8d91bb1", "autre", "chantier_absent", "incertain", None,
              pos(*l93_local(917295.0, 6460155.0), 15.0, "constat"),
              {"note": "aucun élément de chantier routier visible (ni cône, ni balise, ni marquage jaune provisoire, ni tranchée) ; seul "
                       "jaune : la traversée cyclable permanente (constat 22)."},
              pv("vues/f8d91bb1_jonction_ov.jpg"), valide={"valeur": True, "raison": "contexte"}))


def main():
    O_.sort(key=lambda o: o["id"])
    ids = [o["id"] for o in O_]
    assert len(ids) == len(set(ids)), "identifiants dupliqués"
    out = ICI.parent / "obs_pano_2026.json"
    out.write_text(json.dumps(O_, ensure_ascii=False, indent=1), encoding="utf-8")
    bilan = {"generateur": "recon/out/paquet_jardin/v2/enrichi/recensement/pano_2026/saisie_2026.py",
             "n_observations": len(O_), "statuts": dict(sorted(Counter(o["statut"] for o in O_).items())),
             "classes": dict(sorted(Counter(o["classe"] for o in O_).items())),
             "methodes": dict(sorted(Counter(o["position"]["methode"] for o in O_).items())),
             "constats_convertis": sorted({o["constat"] for o in O_ if o.get("constat")}),
             "requalifications": {o["lien_description"]: o["statut"] for o in O_
                                  if "requalification" in o["attributs"]},
             "poses": CALEES,
             "images": "Panoramax IGN (panoramax.ign.fr), collection 6aded52a-7c8e-46c2-9d7d-3600dc3c84e1, producteur "
                       "ceremadtermed-ti, licence etalab-2.0 (Licence Ouverte) ; découpes dérivées dans vues/",
             "fusion": "ajouter obs_pano_2026.json à FICHIERS_OBS de fusion_recensement.py et classer date ≥ 2025-12-05 en "
                       "catégorie photo_2026"}
    (ICI / "bilan_pano_2026.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
