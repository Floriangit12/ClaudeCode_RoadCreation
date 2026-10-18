# -*- coding: utf-8 -*-
"""Vocabulaire du format de description simple : mots et expressions français → valeurs du modèle `modele_voie`.

Tout est comparé après normalisation (`norm`) : minuscules, sans accents, apostrophes droites, flèches ASCII
converties (« -> » → « → », « <- » → « ← », « <-> » → « ↔ »), virgule décimale entre chiffres → point.
La liste complète des mots reconnus est dans FORMAT_DESCRIPTION.md § 3 ; un mot inconnu est une erreur (jamais
ignoré en silence).
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------------------------------- normalisation
def sans_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    s = str(s).replace("’", "'").replace("‘", "'").replace("´", "'")
    s = sans_accents(s).lower()
    s = s.replace("<->", " ↔ ").replace("->", " → ").replace("<-", " ← ")
    s = s.replace("→", " → ").replace("←", " ← ").replace("↔", " ↔ ")
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)            # virgule décimale
    s = re.sub(r"(\d)\s*(cm|m)\b", r"\1 \2", s)       # 2.0m → 2.0 m
    s = re.sub(r"[,;()]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_cle(s: str) -> str:
    """Clé YAML → identifiant : « Dos d'âne » → « dos_d_ane », « à » → « a »."""
    s = sans_accents(str(s)).lower().strip()
    s = re.sub(r"[\s'\-]+", "_", s)
    return re.sub(r"[^a-z0-9_]", "", s)


NOMBRE = re.compile(r"^[-+]?\d+(\.\d+)?$")
MOTS_VIDES = {"de", "d", "du", "des", "en", "a", "au", "aux", "avec", "le", "la", "les", "l", "un", "une", "et",
              "sur", "m", "cote", "type", "sens", "en", "par"}

# ---------------------------------------------------------------------------------------------------- bandes
BANDES = {  # expression → (type, sous_type, attributs par défaut)
    "trottoir": ("trottoir", None, {}),
    "voie": ("voie_circulation", None, {}),
    "voie de circulation": ("voie_circulation", None, {}),
    "voie circulation": ("voie_circulation", None, {}),
    "voie generale": ("voie_circulation", None, {}),
    "voie bus": ("voie_bus", None, {}),
    "couloir bus": ("voie_bus", None, {}),
    "voie reservee bus": ("voie_bus", None, {}),
    "voie tourne-a-gauche": ("voie_tourne_gauche", None, {}),
    "voie de tourne-a-gauche": ("voie_tourne_gauche", None, {}),
    "tourne-a-gauche": ("voie_tourne_gauche", None, {}),
    "voie tourne-a-droite": ("voie_tourne_droite", None, {}),
    "voie de tourne-a-droite": ("voie_tourne_droite", None, {}),
    "tourne-a-droite": ("voie_tourne_droite", None, {}),
    "voie de stockage": ("voie_stockage", None, {}),
    "voie d'insertion": ("voie_insertion", None, {}),
    "voie d'acceleration": ("voie_insertion", None, {}),
    "voie de deceleration": ("voie_deceleration", None, {}),
    "voie tag": ("voie_tourne_gauche", None, {}),
    "voie tad": ("voie_tourne_droite", None, {}),
    "voie centrale banalisee": ("voie_centrale_banalisee", None, {}),
    "chaussee partagee": ("chaussee_partagee", None, {}),
    "bande cyclable": ("bande_cyclable", None, {}),
    "bande velo": ("bande_cyclable", None, {}),
    "piste cyclable": ("piste_cyclable", None, {}),
    "piste velo": ("piste_cyclable", None, {}),
    "piste": ("piste_cyclable", None, {}),
    "voie verte": ("voie_verte", None, {}),
    "rive cyclable": ("rive_cyclable_cvcb", None, {}),
    "cvcb": ("rive_cyclable_cvcb", None, {}),
    "stationnement": ("stationnement", None, {}),
    "parking": ("stationnement", None, {}),
    "file de stationnement": ("stationnement", None, {}),
    "livraison": ("livraison", None, {}),
    "aire de livraison": ("livraison", None, {}),
    "terre-plein": ("terre_plein", None, {}),
    "terre plein": ("terre_plein", None, {}),
    "terre-plein central": ("terre_plein", "terre_plein_central", {}),
    "tpc": ("terre_plein", "terre_plein_central", {}),
    "bande plantee": ("bande_plantee", None, {}),
    "bande verte": ("bande_plantee", None, {}),
    "bande enherbee": ("bande_plantee", None, {}),
    "separateur": ("separateur", None, {}),
    "tampon": ("zone_neutralisee", "tampon_emportierage", {}),
    "zone tampon": ("zone_neutralisee", "tampon_emportierage", {}),
    "zone neutralisee": ("zone_neutralisee", "hachures", {}),
    "zone hachuree": ("zone_neutralisee", "hachures", {}),
    "accotement": ("accotement_revetu", None, {}),
    "accotement revetu": ("accotement_revetu", None, {}),
    "accotement enherbe": ("berme", None, {"materiau": "gazon_tondu"}),
    "accotement herbe": ("berme", None, {"materiau": "herbe_haute"}),
    "berme": ("berme", None, {}),
    "bande derasee": ("bande_derasee", None, {}),
    "bdd": ("bande_derasee", None, {}),
    "bdg": ("bande_derasee", "bande_derasee_gauche", {}),
    "surlargeur": ("accotement_revetu", "surlargeur", {}),
    "bau": ("bande_arret_urgence", None, {}),
    "bande d'arret d'urgence": ("bande_arret_urgence", None, {}),
    "quai": ("quai_bus", None, {}),
    "quai bus": ("quai_bus", None, {}),
    "chemin": ("chemin_pieton", None, {}),
    "cheminement": ("chemin_pieton", None, {}),
    "fosse": ("fosse", None, {}),
    "noue": ("noue", None, {}),
    "talus": ("talus", None, {}),
}

# ---------------------------------------------------------------------------------------------------- matériaux
# expression → (materiau_id selon la classe de la bande, ou id unique) ; « enrobé » dépend de la bande
MATERIAUX = {
    "enrobe": {"chaussee": "enrobe_bbsg_ancien", "trottoir": "enrobe_trottoir", "piste": "enrobe_piste_cyclable"},
    "enrobe use": "enrobe_bbsg_ancien",
    "enrobe ancien": "enrobe_bbsg_ancien",
    "vieil enrobe": "enrobe_bbsg_ancien",
    "enrobe neuf": "enrobe_bbsg_neuf_2025",
    "enrobe recent": "enrobe_bbsg_neuf_2025",
    "enrobe rapiece": "enrobe_reprise_tranchee",
    "enrobe clair": "enrobe_clair_granulats",
    "enrobe rouge": "enrobe_colore_ocre",
    "enrobe ocre": "enrobe_colore_ocre",
    "beton": "beton_balaye",
    "beton balaye": "beton_balaye",
    "beton desactive": "beton_desactive",
    "dalles": "dalles_beton",
    "dalles beton": "dalles_beton",
    "paves": "paves_beton",
    "paves beton": "paves_beton",
    "paves granit": "paves_granit",
    "stabilise": "stabilise_beige",
    "gazon": "gazon_tondu",
    "pelouse": "gazon_tondu",
    "engazonne": "gazon_tondu",
    "herbe": "gazon_tondu",
    "herbe haute": "herbe_haute",
    "gravier": "gravier_concasse_6_10",
    "gravillons": "gravillons_ilot",
    "galets": "galets_20_40",
    "brf": "brf_bois_concasse",
    "copeaux": "brf_bois_concasse",
    "terre": "terre_nue",
    "resine verte": "resine_verte",
    "resine": "resine_verte",
}
MATERIAUX_BORDURE = {"beton": "beton_bordure_gris", "beton gris": "beton_bordure_gris",
                     "beton clair": "beton_bordure_clair", "beton blanc": "beton_bordure_clair",
                     "granit": "granit_bordure", "calcaire": "calcaire_bordure", "pierre": "calcaire_bordure"}
USURE_ENROBE = {"use": "enrobe_bbsg_ancien", "usee": "enrobe_bbsg_ancien", "ancien": "enrobe_bbsg_ancien",
                "vieux": "enrobe_bbsg_ancien", "neuf": "enrobe_bbsg_neuf_2025", "rapiece": "enrobe_reprise_tranchee"}

# usure des marquages (échelle du format, FORMAT_DESCRIPTION.md § 5) : 0 = neuf, 1 = effacé
USURE_MARQUAGES = {"neuf": 0.0, "neuve": 0.0, "neufs": 0.0, "legere": 0.2, "leger": 0.2, "peu usee": 0.2,
                   "moyenne": 0.4, "usee": 0.5, "use": 0.5, "uses": 0.5, "usees": 0.5, "forte": 0.7,
                   "tres usee": 0.7, "effacee": 0.85, "presque effacee": 0.85}

# ---------------------------------------------------------------------------------------------------- attributs
ATTRIBUTS = {  # expression → (clé, valeur)
    "niveau trottoir": ("niveau", "trottoir"),
    "au niveau du trottoir": ("niveau", "trottoir"),
    "niveau chaussee": ("niveau", "chaussee"),
    "au niveau de la chaussee": ("niveau", "chaussee"),
    "de plain-pied": ("niveau", "chaussee"),
    "sans bordure": ("niveau", "chaussee"),
    "plain-pied": ("niveau", "chaussee"),
    "niveau intermediaire": ("niveau", "intermediaire"),
    "intermediaire": ("niveau", "intermediaire"),
    "longitudinal": ("orientation", "longitudinal"),
    "en long": ("orientation", "longitudinal"),
    "lineaire": ("orientation", "longitudinal"),
    "epi": ("orientation", "epi"),
    "en epi": ("orientation", "epi"),
    "bataille": ("orientation", "bataille"),
    "en bataille": ("orientation", "bataille"),
    "places marquees": ("places_marquees", True),
    "places non marquees": ("places_marquees", False),
    "mi-trottoir": ("position", "mi_trottoir"),
    "sur trottoir": ("position", "trottoir"),
    "en encoche": ("position", "encoche"),
    "encoche": ("position", "encoche"),
    "bidirectionnelle": ("bidirectionnelle", True),
    "bi": ("bidirectionnelle", True),
    "double sens": ("bidirectionnelle", True),
    "unidirectionnelle": ("bidirectionnelle", False),
    "uni": ("bidirectionnelle", False),
    "plante": ("plante", True),
    "plantee": ("plante", True),
    "arbore": ("arbres", True),
    "avec arbres": ("arbres", True),
    "arbres": ("arbres", True),
    "hachure": ("franchissable", "peint"),
    "peint": ("franchissable", "peint"),
    "franchissable": ("franchissable", "vl_pl"),
    "franchissable pl": ("franchissable", "pl_seulement"),
    "velos admis": ("velos_admis", True),
    "ouvert aux velos": ("velos_admis", True),
    "permanent": ("permanent", True),
    "zone bleue": ("zone_bleue", True),
}

# ---------------------------------------------------------------------------------------------------- limites
PROFILS_BORDURE = {"t1": "T1", "t2": "T2", "t3": "T3", "a1": "A1", "a2": "A2", "p1": "P1", "p2": "P2", "p3": "P3",
                   "cs1": "CS1", "cs2": "CS2", "cc1": "CC1", "cc2": "CC2", "i1": "I1", "i2": "I2", "il": "IL",
                   "quai": "QUAI_BUS", "bateau": "T2_bateau", "basse": "A2", "franchissable": "A2", "haute": "T2"}
CANIVEAUX = {"cs1": "CS1", "cs2": "CS2", "cs3": "CS3", "cc1": "CC1", "cc2": "CC2"}
# types du catalogue route_fr ajoutés par le lot « bordures » (commun/bordures_catalogue.py : MOTS_PROFILS,
# MOTS_CANIVEAUX ; cotes RF-AS-profil_*) ; les mots existants ci-dessus gardent leur sens (intégration, étape 2)
for _k, _v in (("t4", "T4"), ("i3", "I3"), ("i4", "I4"), ("p4", "P4"), ("tu", "TU"), ("ac1", "AC1"),
               ("gr_t1", "GR_T1"), ("gr_t2", "GR_T2"), ("gr_p1", "GR_P1"), ("granit_t1", "GR_T1"), ("granit_t2", "GR_T2"),
               ("granit_p1", "GR_P1"), ("t2_basse", "T2_basse"), ("t3_basse", "T3_basse"),
               ("t2_surbaissee", "T2_surbaissee"), ("t3_surbaissee", "T3_surbaissee"), ("p1_basse", "P1_basse"),
               ("accesbus", "ACCESBUS"), ("quai_accessible", "ACCESBUS"), ("gr_a1", "GR_A1"), ("gr_a2", "GR_A2"),
               ("gr_p3", "GR_P3"), ("granit_a1", "GR_A1"), ("granit_a2", "GR_A2"), ("granit_p3", "GR_P3"),
               ("bordurette", "P1"), ("paves_granit", "PAVES_GRANIT"), ("quai_bus", "QUAI_BUS"), ("t2_bateau", "T2_bateau"),
               ("cs3", "CS3"), ("cs4", "CS4")):
    PROFILS_BORDURE.setdefault(_k, _v)
CANIVEAUX.setdefault("cs4", "CS4")
del _k, _v
SEPARATEURS = {"potelets": "potelets", "potelet": "potelets", "balises": "balises_J11", "balises j11": "balises_J11",
               "plots": "plots", "glissiere": "glissiere", "gba": "GBA", "muret": "muret",
               "jardinieres": "jardinieres", "bordure separatrice": "bordure_separatrice", "garde-corps": "garde_corps",
               "haie": "haie",
               # lot N1 (18/10/2026, relecture M8) : séparateur béton double face entre deux sens (Cerema ; catalogue
               # retenue_DBA_*, base 0,60) ; « GBA » reste le profil simple face (retenue_GBA_*, base 0,48)
               "dba": "DBA", "gba double face": "DBA", "separateur beton double": "DBA"}
MODULATIONS = {"t1": "T1", "t'1": "T'1", "t2": "T2", "t'2": "T'2", "t3": "T3", "t'3": "T'3", "t4": "T4",
               "continue": "continue", "continu": "continue", "pleine": "continue", "double continue": "double_continue",
               "double-continue": "double_continue", "mixte": "mixte", "aucune": "aucune", "aucun": "aucune",
               "pas de ligne": "aucune", "sans": "aucune", "sans ligne": "aucune"}
COULEURS = {"blanc": "blanc", "blanche": "blanc", "jaune": "jaune", "bleu": "bleu", "bleue": "bleu"}
SENS = {"→": "avant", "←": "arriere", "↔": "double", "avant": "avant", "arriere": "arriere", "double": "double"}

# ---------------------------------------------------------------------------------------------------- évènements
EVENEMENTS = {
    "passage pieton": "passage_pieton", "passage pietons": "passage_pieton", "passage pour pietons": "passage_pieton",
    "passage cloute": "passage_pieton", "pp": "passage_pieton",
    "dos-d'ane": "dos_d_ane", "dos d'ane": "dos_d_ane", "dos d ane": "dos_d_ane", "ralentisseur": "dos_d_ane",
    "plateau": "plateau", "plateau sureleve": "plateau", "ralentisseur trapezoidal": "plateau",
    "passage sureleve": "plateau_pieton",
    "coussin": "coussin", "coussin berlinois": "coussin", "coussins": "coussin",
    "rabattement": "rabattement", "retrecissement": "rabattement", "reduction de voie": "rabattement",
    "elargissement": "elargissement", "ajout de voie": "elargissement",
    "arret de bus": "arret_bus", "arret bus": "arret_bus", "quai bus": "arret_bus",
    "entree charretiere": "entree_charretiere", "bateau": "entree_charretiere", "acces riverain": "entree_charretiere",
    "abaisse": "abaisse", "abaissement": "abaisse",
    "panneau": "panneau",
    "nouveau profil": "profil", "changement de profil": "profil", "profil": "profil",
    "ligne continue": "zone_depassement_interdit", "zone de depassement interdit": "zone_depassement_interdit",
    "depassement interdit": "zone_depassement_interdit", "fleches": "fleches", "fleches directionnelles": "fleches",
    "inscription": "inscription", "ouverture": "ouverture", "evasement": "ouverture", "fermeture": "fermeture",
}
CLES_EVENEMENTS = {"passage_pieton", "dos_d_ane", "plateau", "plateau_pieton", "coussin", "rabattement",
                   "elargissement", "arret_bus", "entree_charretiere", "abaisse", "panneau", "profil",
                   "zone_depassement_interdit", "fleches", "inscription", "ouverture", "fermeture"}
SYNONYMES_CLES = {"passage_pietons": "passage_pieton", "passage_pour_pietons": "passage_pieton",
                  "dos_dane": "dos_d_ane", "ralentisseur": "dos_d_ane", "coussin_berlinois": "coussin",
                  "arret_de_bus": "arret_bus", "nouveau_profil": "profil", "changement_de_profil": "profil",
                  "passage_sureleve": "plateau_pieton", "abaissement": "abaisse", "acces_riverain": "entree_charretiere",
                  "ligne_continue": "zone_depassement_interdit", "depassement_interdit": "zone_depassement_interdit",
                  "fleches_directionnelles": "fleches"}

CATEGORIES = {"rue": "rue", "avenue": "rue", "boulevard": "rue", "allee": "desserte", "desserte": "desserte",
              "impasse": "desserte", "route": "route_departementale", "route departementale": "route_departementale",
              "departementale": "route_departementale", "rd": "route_departementale",
              "route nationale": "route_nationale", "nationale": "route_nationale", "rn": "route_nationale",
              "route communale": "route_communale", "chemin": "chemin", "voie express": "voie_express",
              "autoroute": "autoroute", "zone de rencontre": "zone_rencontre", "aire pietonne": "aire_pietonne",
              "piste cyclable": "piste_cyclable_independante", "voie verte": "voie_verte", "bretelle": "bretelle",
              "voie de service": "voie_service"}

OUI = {"oui", "o", "vrai", "true", "yes", "1"}
NON = {"non", "n", "faux", "false", "no", "0", "aucun", "aucune"}


def booleen(v, chemin: str) -> bool:
    if isinstance(v, bool):
        return v
    s = norm(v) if v is not None else ""
    if s in OUI:
        return True
    if s in NON:
        return False
    raise ValueError(f"{chemin} : oui / non attendu, lu « {v} »")


def nombre(v, chemin: str, unite_par_defaut: str = "m") -> float:
    """Nombre avec virgule ou point, unité m ou cm facultative (« 2,0 », « 2.0 m », « 14 cm »)."""
    if isinstance(v, bool):
        raise ValueError(f"{chemin} : nombre attendu, lu « {v} »")
    if isinstance(v, (int, float)):
        return float(v) / (100.0 if unite_par_defaut == "cm" else 1.0)
    s = norm(v).replace(" %", "").replace("%", "")
    m = re.match(r"^([-+]?\d+(?:\.\d+)?)\s*(m|cm|u)?$", s)
    if not m:
        raise ValueError(f"{chemin} : nombre attendu, lu « {v} »")
    x = float(m.group(1))
    u = m.group(2) or unite_par_defaut
    return x / 100.0 if u == "cm" else x


# ---------------------------------------------------------------------------------------------------- jetons
def jetons(s: str) -> list[str]:
    return norm(s).split(" ") if norm(s) else []


def correspondance(toks: list[str], i: int, table: dict, max_mots: int = 4):
    """Plus longue expression de `table` commençant au jeton i : (clé, nb de jetons) ou (None, 0)."""
    for n in range(min(max_mots, len(toks) - i), 0, -1):
        cle = " ".join(toks[i:i + n])
        if cle in table:
            return cle, n
    return None, 0
