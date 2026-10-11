"""Règles de la résolution (RES-*), seuils et stations terrain.

La résolution part de la description de base (schéma 0.3) et n'y applique que des décisions prouvées.
Chaque modification appliquée cite ses observations, ses règles et le verdict de revue ; tout ce qui reste en
conflit ou incertain est laissé tel que la base et listé avec la station terrain qui le tranchera.
"""
import math

import numpy as np

REGLES = {
    "RES-SRC-001": "Priorité des preuves : double lecture d'une revue > fusion stricte (FUS-COUV-02) > décision de cohérence "
                  "jugée juste par la revue adverse > règle de conception appliquée à un objet déduit > base. Une décision "
                  "qu'une revue juge « faux » n'est jamais appliquée.",
    "RES-CHN-001": "Chaîne : enrichi/ et coherence/ doivent avoir lu la base courante (sha256 des fichiers de base) ; sinon la "
                  "résolution s'arrête (option --forcer pour un essai).",
    "RES-EXI-001": "Retrait ou absence 2026 prouvés strictement par la fusion (statut a_retirer / absent_2026, observation "
                  "stricte) : marquage -> fabrication non_fabrique ; objet -> instancier false. Bordure : non appliqué "
                  "(références de partition), listé pour le propriétaire de bordures.py.",
    "RES-EXI-002": "Garde temporelle : une absence vue seulement avant la fin des travaux (05/12/2025) ne retire ni une entité "
                  "posée ou refaite en 2025, ni une entité levée GAM 2026 : conflit listé.",
    "RES-EXI-003": "Absence relevée par une revue adverse sur photos 2026 calées et confirmée par une seconde lecture (P16) : "
                  "instancier false ; à intégrer comme constat de revue (FUS-ARB-01) par le propriétaire de la fusion.",
    "RES-EXI-004": "absent_2026_a_verifier (FUS-EXI-04) et non-instanciations de la cohérence jugées incertaines : entité "
                  "gardée telle que la base, listée.",
    "RES-EXI-005": "Absence ou retrait portés seulement par des projections photo à plus de 15 m de la caméra (FUS-VAL-02) : "
                  "un trait fin peut y être invisible ; non appliqué, listé (cas MLY-MAR-017 de la critique de couverture).",
    "RES-POS-001": "Mesure de position (fusion « appliquer » ou cohérence « mesure ») appliquée si la revue adverse la juge "
                  "juste ; non revue : seulement une triangulation ou une ombre corroborée de déplacement ≤ 0,30 m (sous "
                  "le seuil de double lecture P16), sans drapeau.",
    "RES-POS-002": "Mesure pixel_ortho d'un objet haut (mât, poteau) : appliquée seulement si elle est corroborée (revue "
                  "juste, départ d'ombre, triangulation) (Q7) ; une mesure rejetée par la cohérence pour sa date n'est pas "
                  "appliquée.",
    "RES-POS-003": "Revue « faux » : rien n'est appliqué. Revue « incertain » : seules les composantes que la revue déclare "
                  "prouvées ou plausibles (ex. azimut) sont appliquées.",
    "RES-POS-004": "Déplacement par la règle sans mesure : appliqué à un objet déduit ou en projet (règles dures pour les a "
                  "priori, P7) dans le budget de sa source ; pour un objet existant, seulement si une revue l'a jugé juste ; "
                  "sinon listé comme violation physique non tranchée (objet ou surface à vérifier).",
    "RES-POS-005": "Groupe de support (membres_groupe) : une seule décision pour le mât ; fusion de supports prouvée (P5) : un "
                  "seul fût instancié, l'autre objet est porté.",
    "RES-POS-006": "Statut temporel : un objet existant déplacé de plus de 1 m par une mesure postérieure aux travaux passe en "
                  "« déplacé lors des travaux 2025 » (Q8).",
    "RES-ORI-001": "Réorientation appliquée si la revue la juge juste ou plausible, ou si l'azimut source est absent "
                  "(complétion par la règle, confiance faible).",
    "RES-ORI-002": "Tête de feu : réorientation par la règle fonctionnelle (FEU-05/06/07/09) appliquée si l'azimut source est "
                  "une valeur de saisie (multiple de 45°) et l'écart ≤ 60° ; sinon gardée et listée.",
    "RES-ATT-001": "Attribut : mise à jour de la fusion « appliquer » (FUS-ATT-06) si la confiance de la valeur est au moins "
                  "moyenne, si l'attribut existe dans la famille et si la valeur est dans son domaine (enum du schéma 0.3, "
                  "table des matériaux, types d'arbres du paquet) ; un azimut qui contredit de plus de 20° l'azimut résolu ou "
                  "gardé par la cohérence est un conflit ; sinon listée.",
    "RES-BOR-001": "Vue ou profil de bordure contestés (FUS-BOR-03) : jamais appliqués sans relevé ; listés avec la station.",
    "RES-MQ-001": "Flèche recentrée (MQ-FLE-006) : flèche non levée GAM, non retirée, voie bornée par deux limites décrites "
                 "(bordure ou ligne, pas OpenDRIVE seule), aucune bordure ni ligne ne coupe la boîte de la flèche (marge "
                 "0,10 m), empreinte recalée entièrement roulable (surfaces v2), revue non « faux » (Q5).",
    "RES-MQ-002": "Marque au-delà de l'arête avant d'une bordure (MQ-DET-010, TQ-MQG-014) : la partie au-delà de "
                 "l'intersection vérifiée avec la bordure devient une interruption (géométrie inchangée).",
    "RES-MQ-003": "Ajout de marquage : trait isolé (LineString) observé en confiance ≥ moyenne, σ ≤ 0,10 m, source "
                 "représentable dans src_marquage (gam, plan2025, ortho2022), sans doublon à 0,3 m ; sinon listé.",
    "RES-ADD-001": "Ajout d'objet : instancier vrai dans la fusion (FUS-ADD-03), preuve stricte probante (après travaux, ou "
                  "avant travaux hors emprise, ou dans l'emprise avec appui), confiance ≥ moyenne, σ ≤ seuil de la classe, "
                  "type non ambigu (« _ou_ ») ; surfaces : jamais (partition de surfaces.py).",
    "RES-ADD-002": "Tampons et avaloirs : écrits dans objets/ponctuels_sol_ajouts.geojson (identifiants TAM-/AVA- et ancrage "
                  "du schéma) tant que la table des matériaux du schéma 0.3 n'a pas de fonte (materiau_id obligatoire de "
                  "ponctuels_sol) ; à verser dans base/ponctuels_sol.geojson quand le propriétaire du schéma l'aura ajoutée.",
    "RES-NRE-002": "Présence 2026 non testée : objet instancié à moins de 25 m d'une photo 2026 calée sans preuve stricte "
                   "postérieure aux travaux ; listé pour un test de présence sur vignette (Q4 de la revue adverse).",
    "RES-NRE-001": "Non résolu : toute entité en conflit ou incertaine reste telle que la base et est listée avec la station "
                  "terrain la plus proche (PROTOCOLE_TERRAIN.md) ou une station à créer.",
}

RAYON_PRESENCE_2026_M = 25.0        # RES-NRE-002 (Q4)
SEUIL_DOUBLE_LECTURE_M = 0.30       # P16 : au-delà, une correction non revue n'est pas appliquée
DISTANCE_PROJECTION_MAX_M = 15.0     # RES-EXI-005 (FUS-VAL-02)
TYPES_ARBRE = {"feuillu", "arbuste", "conifere", "souche"}   # types d'arbres du paquet v1 (correspondance UE)
SIGMA_MAX_AJOUT = {"ponctuel": 0.5, "point": 0.5, "arbre": 1.5, "lineaire": 1.0}
SIGMA_MAX_MARQUAGE_AJOUT = 0.10
TRANCHES_PROBANTES = {"apres_travaux", "avant_travaux_hors_emprise", "avant_travaux_dans_emprise_appui"}
CONFIANCES_PROBANTES = {"moyenne", "haute"}
SIGMA_PLANCHER_PHOTO_UNIQUE_M = 0.30   # Q6 : σ minimal d'une mesure appuyée sur une seule photo discriminante
DEPLACE_TRAVAUX_M = 1.0                 # RES-POS-006
FIN_TRAVAUX = "2025-12-05"
OBJETS_HAUTS = {"lampadaire", "panneau", "support_feux", "mat_camera", "poteau_reseau", "poteau_arret", "totem_PR",
                "panneau_information", "mobilier_publicitaire"}

# stations terrain (recon/pcg/enrichir/PROTOCOLE_TERRAIN.md), repère local (m)
STATIONS = {
    "S1": {"type": "point", "p": (-2.0, 19.0), "libelle": "angle N, Revirée × Verdun NE"},
    "S2": {"type": "point", "p": (17.0, -2.0), "libelle": "angle E, Verdun NE × Vercors"},
    "S3": {"type": "point", "p": (-2.0, -27.0), "libelle": "angle S, Vercors × Verdun SO"},
    "S4": {"type": "point", "p": (-24.0, -15.0), "libelle": "angle O, Verdun SO × Revirée"},
    "S5": {"type": "point", "p": (-18.0, -20.0), "libelle": "refuge (TPC) de Verdun SO"},
    "S6": {"type": "point", "p": (10.0, 8.0), "libelle": "refuge (TPC) de Verdun NE"},
    "S7": {"type": "point", "p": (8.5, -15.0), "libelle": "îlot du Vercors"},
    "S8": {"type": "point", "p": (-45.0, -48.0), "libelle": "quais La Revirée, Verdun SO"},
    "S13": {"type": "point", "p": (25.0, -135.0), "libelle": "débouché des Mitaillères"},
    "S14": {"type": "ligne", "p": ((-45.0, -48.0), (-95.0, -92.0)), "libelle": "parcours Verdun SO"},
    "S15": {"type": "ligne", "p": ((22.0, -10.0), (30.0, -125.0)), "libelle": "parcours rive est du Vercors"},
    "S9": {"type": "ligne", "p": ((20.0, 10.0), (60.0, 70.0)), "libelle": "parcours rive SE de Verdun NE"},
    "S11": {"type": "ligne", "p": ((50.0, 98.0), (67.0, 105.0)), "libelle": "arc de bordures (50-67 ; 98-105)"},
    "S10b": {"type": "point", "p": (58.0, -30.0), "libelle": "sortie de la voie privée des Saules Blancs"},
    "S12": {"type": "ligne", "p": ((-3.0, 17.0), (-20.0, 40.0)), "libelle": "parcours de la Revirée"},
}
PORTEE_STATION_M = {"point": 30.0, "ligne": 15.0}


def _d_segment(p, a, b):
    p, a, b = np.asarray(p, float), np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = float(np.clip(np.dot(p - a, ab) / max(float(np.dot(ab, ab)), 1e-12), 0.0, 1.0))
    return float(np.hypot(*(p - (a + t * ab))))


def station_pour(xy):
    """(station, distance) la plus proche couvrant le point local xy, sinon (proposition de station à créer, d)."""
    if xy is None:
        return {"station": None, "distance_m": None, "note": "position inconnue"}
    best = None
    for nom in sorted(STATIONS):
        s = STATIONS[nom]
        d = math.hypot(xy[0] - s["p"][0], xy[1] - s["p"][1]) if s["type"] == "point" else _d_segment(xy, *s["p"])
        if d <= PORTEE_STATION_M[s["type"]] and (best is None or d < best[1]):
            best = (nom, d)
    if best:
        return {"station": best[0], "distance_m": round(best[1], 1), "note": STATIONS[best[0]]["libelle"]}
    cx, cy = round(xy[0] / 25.0) * 25.0, round(xy[1] / 25.0) * 25.0
    return {"station": f"nouvelle({cx:+.0f};{cy:+.0f})", "distance_m": None,
            "note": "hors de portée des stations S1-S15 : station à créer (maille de 25 m)"}


def projection_lointaine(obs_ids, observations):
    """Vrai si toutes les observations citées sont des projections photo à plus de DISTANCE_PROJECTION_MAX_M (RES-EXI-005)."""
    ds = []
    for i in obs_ids:
        o = observations.get(i) or {}
        d = o.get("distance_camera_m")
        if d is None:
            return False
        ds.append(float(d))
    return bool(ds) and min(ds) > DISTANCE_PROJECTION_MAX_M


def regrouper_stations(points, rayon=30.0):
    """Stations à créer pour des points locaux hors de portée : couverture gloutonne (rayon m), déterministe.
    points : [(cle, (x, y))] ; renvoie {cle: (nom, centre, distance)}."""
    restants = sorted(points, key=lambda kv: kv[0])
    out = {}
    k = 0
    while restants:
        P = np.array([xy for _, xy in restants], float)
        D = np.hypot(P[:, None, 0] - P[None, :, 0], P[:, None, 1] - P[None, :, 1])
        n = (D <= rayon).sum(axis=1)
        i = int(np.argmax(n))
        sel = np.where(D[i] <= rayon)[0]
        c = P[sel].mean(axis=0)
        k += 1
        nom = f"N{k}"
        for j in sel:
            out[restants[j][0]] = (nom, (round(float(c[0]), 1), round(float(c[1]), 1)),
                                   round(float(np.hypot(*(P[j] - c))), 1))
        pris = set(sel.tolist())
        restants = [kv for j, kv in enumerate(restants) if j not in pris]
    return out

