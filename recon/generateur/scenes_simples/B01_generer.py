"""Écrit la scène B01 « nuancier des bordures » (lot bordures, 17/10/2026) : B01_nuancier_bordures.yaml (description),
B01_nuancier_bordures.vues.json (vues du rendu) et B01_nuancier_bordures.etiquettes.json (type de chaque tronçon).

    python recon/generateur/scenes_simples/B01_generer.py

Une rue de 96 m (2 × 1 voies de 3,00 m) découpée en tronçons, un type de bordure par tronçon, sur trois rangées :
  - rangée G (à gauche, trottoirs et quais) : 13 blocs de 4,50 m séparés par 1,50 m de trottoir au niveau de la
    chaussée (le bloc est fermé par deux retours : pièces d'angle sortantes) ; famille T, granit, quais, bordures béton clair et calcaire ;
  - rangée C (au centre, îlots de 2,00 m entre les deux voies) : 13 îlots de 4,50 m, zone hachurée entre deux îlots ;
    familles A et I, granit A1 et A2, TU, AC1, couronne de giratoire, refuge ;
  - rangée D (à droite, trottoir continu de 2,00 m à vue 0,16) : 6 tronçons de 13 m ; bordure T2 ou T3 (même vue
    0,16, dans leurs deux vues nominales) avec un caniveau par tronçon (CS1, CS2, CS3, CS4, CC1, CC2) ; derrière le
    trottoir, une bordurette par tronçon (P1, P2, P3, P4, GR_P1, P1_basse) devant une bande plantée 3 cm plus haute ;
    puis zone des abaissés (s = 78 à 96, sans îlot) : abaissés de traversée sur la T2 (s = 82,5 : T2_bateau) et la T3
    (s = 91,5 : T3_surbaissee, bordurette granit GR_P3), entrée charretière sur la T2 de gauche (s = 87).
Chaque bordure est posée à une vue de sa plage nominale (RF-AS-profil_* ; bordures.json vue_courante), avec les
règles par défaut du contexte de commun/bordures_catalogue.py (CONTEXTES) quand le type a un usage de contexte.
"""
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
import bordures_catalogue as BC  # noqa: E402

L_BLOC, L_ESPACE = 4.5, 1.5
PAS = L_BLOC + L_ESPACE
# (profil, vue, bande, matériau, note) — rangée G : bande haute « trottoir » ou « quai »
RANGEE_G = [("T1", 0.12, "trottoir", None, "T1 (12 × 20)"), ("T2", 0.14, "trottoir", None, "T2 : trottoir (DEF-005)"),
            ("T3", 0.18, "trottoir", None, "T3 (17 × 28)"), ("T4", 0.20, "trottoir", None, "T4 (20 × 30)"),
            ("GR_T1", 0.12, "trottoir", "granit_bordure", "granit T1"), ("GR_T2", 0.14, "trottoir", "granit_bordure", "granit T2"),
            ("T2_basse", 0.08, "trottoir", None, "T2 basse"), ("T3_basse", 0.10, "trottoir", None, "T3 basse"),
            ("PAVES_GRANIT", 0.12, "trottoir", "granit_bordure", "pavés de granit"),
            ("QUAI_BUS", 0.21, "quai", None, "quai bus (DEF-032)"), ("ACCESBUS", 0.21, "quai", None, "quai à guide-roues"),
            ("T2", 0.14, "trottoir", "beton_bordure_clair", "T2 béton clair"),
            ("T2", 0.14, "trottoir", "calcaire_bordure", "T2 calcaire")]
# rangée C : îlots (terre-plein) bordés des deux côtés
RANGEE_C = [("A1", 0.09, "A1"), ("A2", 0.07, "A2"), ("I1", 0.06, "I1 : îlot franchissable / îlot central de giratoire"),
            ("I2", 0.11, "I2 : îlot, terre-plein (DEF-005)"), ("I3", 0.06, "I3"), ("I4", 0.11, "I4"),
            ("IL", 0.03, "IL"), ("TU", 0.06, "TU"), ("AC1", 0.06, "AC1 (bordure-caniveau)"),
            ("T2_surbaissee", 0.03, "T2 surbaissée : couronne de giratoire (≤ 0,03)"), ("T2", 0.12, "T2 : refuge (≥ 0,12)"),
            ("GR_A1", 0.09, "granit A1", "granit_bordure"), ("GR_A2", 0.07, "granit A2", "granit_bordure")]
# rangée D : (bordure, caniveau, bordurette, matériau de la bordurette)
RANGEE_D = [("T2", "CS1", "P1", None), ("T2", "CS2", "P2", None), ("T3", "CS3", "P3", None),
            ("T3", "CS4", "P4", None), ("T2", "CC1", "GR_P1", "granit_bordure"), ("T2", "CC2", "P1_basse", None)]
L_D = 13.0
# zone des abaissés (s = 66 à 84) : sans îlot au centre (l'évènement « abaisse, côté droite » vise la première bordure à
# droite de la ligne de référence, qui serait celle de l'îlot) ; à gauche, trottoir T2 continu avec une entrée
# charretière ; à droite, T2 (CS2, P1) puis T3 (CS3, P3) avec un abaissé de traversée chacune
ZONE_ABAISSES = [(78.0, 87.0, ("T2", "CS2", "P1", None)), (87.0, 96.0, ("T3", "CS3", "GR_P3", "granit_bordure"))]
G_CONTINU = ("T2", 0.14, "trottoir", None, "T2 continu (entrée charretière)")
VUE_D = 0.16                      # T2 (0,12-0,16) et T3 (0,16-0,20) : borne commune des vues nominales
DZ_PLANTEE = 0.19                 # bordurette de vue 0,03 (P : 0-0,06 ; RF-AS-profil_P1)
L_NUANCIER = PAS * len(RANGEE_G)
LONGUEUR = ZONE_ABAISSES[-1][1]


def _f(x):
    return f"{x:.2f}"


def profil(sG, sC, sD):
    """Profil (liste structurée) des états des trois rangées."""
    out = []
    if sG is None:
        out.append("trottoir 2,0 enrobé niveau chaussée dévers 1,5")      # dévers du trottoir voisin (DEF-006)
    else:
        p, v, bande, mat, _n = sG
        out.append({"bande": bande, "largeur": 2.0})
        d = {"bordure": p, "vue": v}
        if mat:
            d["materiau"] = mat
        out.append(d)
    out.append("voie 3,0 ←")
    if sC is None:
        out.append("zone hachurée 2,0")
    else:
        p, v, _n, *mat = sC
        d = {"bordure": p, "vue": v, **({"materiau": mat[0]} if mat else {})}
        out += [d, "terre-plein 2,0 enrobé dévers 0", dict(d)]   # à plat, comme la zone hachurée
    out.append("voie 3,0 →")
    b, c, pp, mat = sD
    out.append({"bordure": b, "vue": VUE_D, "caniveau": c})
    out.append({"bande": "trottoir", "largeur": 2.0})
    d = {"bordure": pp}
    if mat:
        d["materiau"] = mat
    out.append(d)
    out.append({"bande": "bande plantée", "largeur": 1.5, "dz": DZ_PLANTEE})
    return out


def etat(s):
    for a, b, d in ZONE_ABAISSES:
        if a - 1e-9 <= s < b:
            return (G_CONTINU, None, d)
    k = min(int(s // PAS), len(RANGEE_G) - 1)
    dans = (s - k * PAS) < L_BLOC - 1e-9
    kd = min(int(s // L_D), len(RANGEE_D) - 1)
    return (RANGEE_G[k] if dans else None, RANGEE_C[k] if dans else None, RANGEE_D[kd])


def yaml_valeur(x):
    if isinstance(x, str):
        return x
    return "{" + ", ".join(f"{k}: {v}" for k, v in x.items()) + "}"


def ecrire():
    coupures = sorted({round(k * PAS + d, 3) for k in range(len(RANGEE_G)) for d in (0.0, L_BLOC)}
                      | {round(k * L_D, 3) for k in range(len(RANGEE_D))} | {a for a, _b, _d in ZONE_ABAISSES})
    coupures = [c for c in coupures if 0 <= c < LONGUEUR]
    L = []
    L.append("# B01 — nuancier des bordures (lot bordures) : écrit par B01_generer.py, ne pas modifier à la main.")
    L.append("# Une rue de 66 m découpée en tronçons, un type de bordure par tronçon (voir l'en-tête du générateur et")
    L.append("# B01_nuancier_bordures.etiquettes.json) ; types étendus : compiler avec commun/bordures_catalogue.py --compiler")
    L.append("# (fabriquer_bordures.py).")
    L.append("format: description_simple/0.1")
    L.append("scene: B01")
    L.append("nom: nuancier_bordures")
    L.append("titre: Nuancier des bordures — un type par tronçon (T, A, I, P, granit, quais, caniveaux)")
    L.append("description: \"Rue de démonstration : 2 voies de 3,00 m ; à gauche 11 blocs de trottoir ou de quai (T1-T4, "
             "granit, T2/T3 basses, pavés, quais) ; au centre 11 îlots (A1, A2, I1-I4, IL, TU, AC1, couronne, refuge) ; à "
             "droite trottoir continu avec bordure T2/T3, caniveaux CS1-CS4, CC1, CC2, bordurettes P1-P4, GR_P1, P1 basse, "
             "abaissés et entrée charretière.\"")
    L.append("contexte:")
    L.append("  agglomeration: true")
    L.append("  vitesse_kmh: 30")
    L.append("  categorie: rue")
    L.append("marquages: {usure: légère}")
    L.append("trace:")
    L.append(f"  - droite: {LONGUEUR:g}")
    L.append("profil:")
    for x in profil(*etat(0.0)):
        L.append(f"  - {yaml_valeur(x)}")
    L.append("evenements:")
    prec = etat(0.0)
    for c in coupures[1:]:
        e = etat(c + 1e-6)
        if e == prec:
            continue
        prec = e
        L.append("  - profil:")
        L.append(f"      a: {c:g}")
        L.append("      nouveau:")
        for x in profil(*e):
            L.append(f"        - {yaml_valeur(x)}")
    L.append("  - abaisse: {a: 82.5, cote: droite}         # T2 → T2_bateau (bordures_elements.json abaisses.traversee)")
    L.append("  - abaisse: {a: 91.5, cote: droite}         # T3 → T3_surbaissee (RF-AS-raccord_bateau)")
    L.append("  - entree_charretiere: {a: 87, cote: gauche, largeur: 3}   # RF-MA-TRO-015, RF-MA-TRO-016")
    L.append("abords: {gauche: pelouse 4, droite: pelouse 4}")
    (ICI / "B01_nuancier_bordures.yaml").write_text("\n".join(L) + "\n", encoding="utf-8")
    # étiquettes (rapport, planche annotée)
    et = []
    for k, (p, v, bande, mat, n) in enumerate(RANGEE_G):
        et.append({"rangee": "G", "s0": k * PAS, "s1": k * PAS + L_BLOC, "t": 5.0, "profil": p, "vue_m": v,
                   "bande": bande, "materiau_id": mat or "beton_bordure_gris", "note": n,
                   "vue_nominale": BC.vues_nominales().get(p), "piece_abaisse": BC.piece_abaisse(p)[0]})
    for k, (p, v, n, *mat) in enumerate(RANGEE_C):
        et.append({"rangee": "C", "s0": k * PAS, "s1": k * PAS + L_BLOC, "t": 0.0, "profil": p, "vue_m": v,
                   "bande": "terre_plein", "materiau_id": mat[0] if mat else "beton_bordure_gris", "note": n,
                   "vue_nominale": BC.vues_nominales().get(p), "piece_abaisse": BC.piece_abaisse(p)[0]})
    for k, (b, c, pp, mat) in enumerate(RANGEE_D):
        et.append({"rangee": "D", "s0": k * L_D, "s1": (k + 1) * L_D, "t": -4.0, "profil": b, "vue_m": VUE_D,
                   "caniveau": c, "bordurette": pp, "bordurette_vue_m": round(DZ_PLANTEE - VUE_D, 3),
                   "bordurette_materiau": mat or "beton_bordure_gris", "vue_nominale": BC.vues_nominales().get(b),
                   "vue_nominale_bordurette": BC.vues_nominales().get(pp), "piece_abaisse": BC.piece_abaisse(b)[0]})
    for a, b_, (b, c, pp, mat) in ZONE_ABAISSES:
        et.append({"rangee": "D", "s0": a, "s1": b_, "t": -4.0, "profil": b, "vue_m": VUE_D, "caniveau": c,
                   "bordurette": pp, "bordurette_vue_m": round(DZ_PLANTEE - VUE_D, 3),
                   "bordurette_materiau": mat or "beton_bordure_gris", "vue_nominale": BC.vues_nominales().get(b),
                   "vue_nominale_bordurette": BC.vues_nominales().get(pp), "piece_abaisse": BC.piece_abaisse(b)[0],
                   "note": "zone des abaissés"})
    et.append({"rangee": "G", "s0": ZONE_ABAISSES[0][0], "s1": LONGUEUR, "t": 5.0, "profil": "T2", "vue_m": 0.14,
               "bande": "trottoir", "materiau_id": "beton_bordure_gris", "note": "T2 continu, entrée charretière",
               "vue_nominale": BC.vues_nominales().get("T2"), "piece_abaisse": BC.piece_abaisse("T2")[0]})
    (ICI / "B01_nuancier_bordures.etiquettes.json").write_text(
        json.dumps({"scene": "B01", "longueur_m": LONGUEUR, "troncons": et,
                    "abaisses": [{"s": 82.5, "cote": "droite", "profil": "T2", "piece": "T2_bateau"},
                                 {"s": 91.5, "cote": "droite", "profil": "T3", "piece": "T3_surbaissee"},
                                 {"s": 87.0, "cote": "gauche", "profil": "T2", "piece": "T2_bateau",
                                  "type": "entree_charretiere"}]},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # vues : dessus de toute la rue (4 cm/px), conducteur (standard), quinze vues rapprochées
    vues = {"scene": "B01", "sujet_s": LONGUEUR / 2, "resolution": [1092, 683],
            "dessus": {"largeur_m": 100.0, "resolution": [2184, 480]},
            "vues": {
                # vues rapprochées : œil à 1,5 m de haut, à 2,4-3,4 m de la file, visée à 45° vers l'avant
                "G1_T1_T2_T3": [[0.0, 1.6, 1.5], [3.0, 4.6, 0.0], 24],
                "G2_T4_GR_T1_GR_T2": [[18.0, 1.6, 1.5], [21.0, 4.6, 0.0], 24],
                "G3_T2b_T3b_paves": [[36.0, 1.6, 1.5], [39.0, 4.6, 0.0], 24],
                "G4_quais": [[53.0, 1.6, 1.5], [56.0, 4.6, 0.0], 24],
                "G5_clair_calcaire": [[65.0, 1.6, 1.5], [68.0, 4.6, 0.0], 24],
                "G6_charretiere_T2": [[82.0, 1.6, 1.5], [85.0, 4.6, 0.0], 24],
                "C1_A1_A2_I1": [[0.0, -3.0, 1.5], [3.0, -0.6, 0.0], 24],
                "C2_I2_I3_I4": [[18.0, -3.0, 1.5], [21.0, -0.6, 0.0], 24],
                "C3_IL_TU_AC1": [[36.0, -3.0, 1.5], [39.0, -0.6, 0.0], 24],
                "C4_couronne_refuge": [[53.0, -3.0, 1.5], [56.0, -0.6, 0.0], 24],
                "C5_granit_A1_A2": [[65.0, -3.0, 1.5], [68.0, -0.6, 0.0], 24],
                "D1_CS1_P1_CS2_P2": [[1.0, -1.6, 1.6], [4.0, -5.0, 0.0], 24],
                "D2_CS3_P3_CS4_P4": [[27.0, -1.6, 1.6], [30.0, -5.0, 0.0], 24],
                "D3_CC1_GRP1_CC2_P1b": [[53.0, -1.6, 1.6], [56.0, -5.0, 0.0], 24],
                "D4_abaisses_T2_T3": [[78.0, -1.6, 1.6], [81.0, -5.0, 0.0], 24]}}
    (ICI / "B01_nuancier_bordures.vues.json").write_text(json.dumps(vues, ensure_ascii=False, indent=1) + "\n",
                                                          encoding="utf-8")
    return len(coupures)


if __name__ == "__main__":
    print(ecrire(), "coupures")
