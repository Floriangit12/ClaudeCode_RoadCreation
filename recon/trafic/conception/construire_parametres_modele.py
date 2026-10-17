"""Assemble assets/specs/trafic/parametres_modele.json : paramètres et distributions retenus pour le
modèle « conducteur + véhicule » (volet 04, conception v0.1).

Principe : AUCUNE valeur des volets n'est ressaisie ici. Chaque paramètre est recopié (loi, paramètres,
source, confiance, tirage) depuis son fichier d'origine :
  volet 01 véhicules       assets/specs/trafic/vehicules_parametres.json
  volet 02 conducteurs     D:/DocRoute/17_Modele_Vehicules_Conducteurs/02_Conducteurs/conducteurs_parametres.json
                           (+ profils_conducteurs.json pour les facteurs latents et les profils)
  volet 03 modèles         assets/specs/trafic/modeles_existants_reference.json
  volet 04 cohérence       D:/DocRoute/17_Modele_Vehicules_Conducteurs/04_Conception/verification/coherence.json
Le script ajoute ensuite ce qui relève de la conception : couche du modèle, usage, règles, hypothèses
(numérotées H-xx), correspondance réseau -> loi de vitesse, lecture du modèle de route, correspondance
SUMO et cibles de validation (dont les valeurs sont elles aussi recopiées des paramètres cités).

  python recon/trafic/conception/verifier_coherence.py        # d'abord (écrit coherence.json)
  python recon/trafic/conception/construire_parametres_modele.py
  python recon/trafic/conception/test_parametres_modele.py

Bibliothèque standard uniquement.
"""
from __future__ import annotations

import copy
import hashlib
import json
import statistics
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
SPECS = DEPOT / "assets" / "specs" / "trafic"
DOC17 = Path("D:/DocRoute/17_Modele_Vehicules_Conducteurs")
F01 = SPECS / "vehicules_parametres.json"
F02 = DOC17 / "02_Conducteurs" / "conducteurs_parametres.json"
F02P = DOC17 / "02_Conducteurs" / "profils_conducteurs.json"
F03 = SPECS / "modeles_existants_reference.json"
F04C = DOC17 / "04_Conception" / "verification" / "coherence.json"
SORTIE = SPECS / "parametres_modele.json"
DOC_CONCEPTION = "D:/DocRoute/17_Modele_Vehicules_Conducteurs/04_Conception/MODELE_CONDUCTEUR_VEHICULE.md"

COUCHES = {
    "PER": "perception (retard, bruit, visibilité, distraction)",
    "STR": "décision stratégique (itinéraire, choix de voie à long terme)",
    "TAC": "décision tactique (changement de voie, créneaux, cédez, STOP, feux, piétons, ralentisseurs)",
    "LON": "contrôle opérationnel longitudinal (vitesse désirée, poursuite, freinage)",
    "LAT": "contrôle opérationnel latéral (vitesse en courbe, suivi de trajectoire, changement de voie)",
    "VEH": "dynamique et géométrie du véhicule",
    "POP": "population (composition du trafic, hétérogénéité, profils, deux-roues, cyclistes)",
    "CTX": "modulateurs de contexte (nuit, week-end)",
    "VAL": "référence de validation (norme ou mesure servant de cible)",
    "REF": "comparaison (valeurs par défaut de SUMO, CARLA, MassTraffic ; modèles de la littérature)",
}
CONF = {"haute": "elevee", "elevee": "elevee", "élevée": "elevee", "moyenne": "moyenne", "faible": "faible"}
NATURE = {"norme": "norme", "mesure": "mesure", "donnee_administrative": "donnee_administrative",
          "donnee_constructeur": "donnee_constructeur", "derive": "derive", "estimation": "estimation",
          "convention": "convention", "defaut_logiciel": "defaut_logiciel", "défaut logiciel": "defaut_logiciel",
          "calage": "calage", "mesure en simulation": "mesure_simulation", "hypothese": "hypothese"}


def charger(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def empreinte(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------ volet 01
def parametres_v01(J):
    """Parcourt le JSON véhicules ; renvoie [(chemin, param)] pour chaque objet {id, loi}."""
    out = []

    def walk(o, chemin):
        if isinstance(o, dict):
            if "id" in o and "loi" in o:
                out.append((chemin, o))
                return
            for k, v in o.items():
                walk(v, f"{chemin}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{chemin}[{i}]")

    for k, v in J.items():
        if k not in ("meta", "sources", "lacunes"):
            walk(v, k)
    return out


def role_v01(chemin, p):
    if chemin.startswith(("parc_france", "composition_trafic")):
        return "POP", "composition"
    if chemin.startswith("reglementation"):
        return "VEH", "norme_vehicule"
    if chemin.startswith("adherence"):
        return "VEH", "adherence"
    if chemin.startswith("freinage_systeme"):
        return "VEH", "parametre_vehicule"
    if p["id"].endswith(("-EXEMPLES", "-DIM-CITARO", "-DIM-URBANWAY", "-DIM-CITARO-G")):
        return "VEH", "vehicule_reference"
    if p["id"].endswith(("-PART-MARCHE", "-PART")):
        return "POP", "composition"
    return "VEH", "parametre_vehicule"


# ------------------------------------------------------------------------------------ volet 02
PREFIXE_COUCHE_V02 = [
    ("tpr.markkula", "PER"), ("tpr.", "PER"), ("feu.tpr_jaune", "PER"),
    ("dec.", "LON"), ("acc.", "LON"), ("tiv.", "LON"),
    ("vit.ecart_jour_nuit", "CTX"), ("vit.week_end", "CTX"), ("vit.contexte", "CTX"), ("vit.", "LON"),
    ("courbe.", "LAT"), ("feu.", "TAC"), ("creneau.", "TAC"), ("stop.", "TAC"), ("ralent.", "TAC"),
    ("pieton.", "TAC"), ("vdv.", "TAC"), ("hetero.", "POP"), ("velo.", "POP"), ("drm.", "POP"), ("sumo.", "REF"),
]


def couche_v02(p):
    if p.get("role") in ("norme_validation", "reference_validation"):
        return "REF" if p["id"].startswith(("sumo.", "velo.defauts_sumo")) else "VAL"
    for pre, c in PREFIXE_COUCHE_V02:
        if p["id"].startswith(pre):
            return c
    raise KeyError(p["id"])


# ------------------------------------------------------------------------------------ volet 03
def couche_v03(p):
    i = p["id"]
    if i.startswith("reference."):
        return None  # doublons des volets 02 (année non renseignée) : on garde l'original du volet 02
    if i.startswith("hdm."):
        return "PER"
    if i.startswith(("idm.treiber2000", "acc_idm.", "eidm.")):
        return "LON"
    if i.startswith("mobil."):
        return "TAC"
    if i.startswith("vehicule."):
        return "VEH"
    if i.startswith(("file.", "idm.calage", "gipps.")):
        return "VAL"
    return "REF"


# ------------------------------------------------------------------------------------ usages
USAGE = {
    # perception
    "tpr.anticipe": "délai avant action quand l'événement est attendu (démarrage au vert derrière un meneur, arrêt prévu) ; tiré par conducteur (groupe tpr, vigilance)",
    "tpr.inattendu_signal": "délai avant action pour un signal inattendu courant (feux stop du meneur, passage au rouge) ; tiré par conducteur",
    "tpr.surprise_obstacle": "délai avant freinage pour un obstacle surgissant (piéton masqué, véhicule qui coupe) ; tiré par conducteur",
    "feu.tpr_jaune": "délai entre l'allumage du jaune et l'action ; tiré par conducteur",
    "tpr.markkula.alphaB_yeux_sur_menace": "option urgence : instant de début de freinage tB = t0,2 + αB (tC - t0,2), conducteur attentif",
    "tpr.markkula.alphaB_yeux_hors_route": "option urgence : idem pour un conducteur en épisode de distraction",
    "tpr.anticipe.age": "modulateur du profil senior (TPR anticipé × 0,66/0,55)",
    "hdm.treiber2006": "structure et ordres de grandeur des erreurs d'estimation (processus de Wiener) et de l'anticipation multi-véhicules",
    # longitudinal
    "vit.artere_centre_ville_50": "vitesse désirée v0 sur les voies urbaines à 50 km/h (correspondance CR-04)",
    "vit.traversee_petite_agglo_50": "v0 en traversée de petite agglomération (CR-02)",
    "vit.entree_sortie_agglo_50": "v0 sur les sections d'entrée et de sortie d'agglomération (CR-03 ; loi bimodale en 2023)",
    "vit.route_2_3_voies_80": "v0 sur les routes bidirectionnelles à 80 km/h (CR-06)",
    "vit.route_2x2_110": "v0 sur les routes à 2x2 voies à 110 km/h (CR-08)",
    "vit.autoroute_degagement_110": "v0 sur les autoroutes urbaines de dégagement à 110 km/h (CR-09)",
    "vit.autoroute_liaison_130": "v0 sur les autoroutes de liaison à 130 km/h (CR-10)",
    "vit.zone_30_be": "v0 en zone 30 (loi belge, faute de mesure française ; CR-01)",
    "vit.poids_lourds": "v0 des poids lourds (moyennes ONISR ; écart-type dérivé, voir LON.MOD.vit_pl_*)",
    "tiv.moyen_conducteur_urbain": "TIV net moyen en suivi stable du conducteur ; donne T_suivi,i (règle R-LON-02)",
    "tiv.moyen_conducteur_autoroute": "idem sur autoroute",
    "tiv.min_conducteur_urbain": "TIV minimal habituel : borne basse des écarts acceptés hors urgence (contrôle) ; cible de validation",
    "tiv.min_conducteur_autoroute": "idem sur autoroute",
    "tiv.ecart_arret": "écart à l'arrêt s0,i de l'IIDM",
    "acc.demarrage_pic": "accélération maximale a_i de l'IIDM (pic de démarrage mesuré)",
    "acc.max_conducteur_bosetti": "sommet « b » du triangle g-g du conducteur (accélération longitudinale maximale qu'il s'autorise)",
    "acc.max_suivi_urbain": "cible de validation des accélérations en suivi (97,5e centile par conducteur)",
    "acc.max_suivi_autoroute": "idem sur autoroute",
    "dec.max_courante_urbain": "décélération « confortable » b_i de l'IIDM (freinage habituel le plus fort) en ville",
    "dec.max_courante_autoroute": "idem sur autoroute",
    "dec.urgence_max_markkula": "décélération d'urgence maximale demandée par le conducteur (bornée ensuite par µg)",
    "dec.urgence_equivalente": "décélération d'urgence équivalente (contrôle des distances d'arrêt)",
    "dec.norme_bus_debout": "plafond de décélération du profil bus (passagers debout)",
    "acc.jerk_confort": "borne de jerk de confort (accélération et freinage hors urgence)",
    "tiv.critere_libre": "seuil de vitesse libre (TIV > 5 s) utilisé pour mesurer v0 dans les validations",
    "idm.treiber2000": "exposant δ = 4 de l'IIDM",
    "acc_idm.kesting2010": "coefficient de « coolness » c = 0,99 de l'heuristique CAH (anticipation du meneur)",
    "eidm.demarrage_salles2020": "forme du démarrage (1 m/s en 0,8 s, pic à 2,3 s) : calage du facteur de démarrage",
    "eidm.amax_salles2020": "ordre de grandeur de a dans les calages IDM (comparaison)",
    # latéral
    "courbe.alpha_deux_tiers": "loi des deux tiers par conducteur : v ≤ α_i R^(1/3) (courbes serrées, R < R0)",
    "courbe.alat_max_conducteur": "sommet « a » du triangle g-g : accélération latérale maximale du conducteur",
    "courbe.enveloppe_alat": "enveloppe a_lat(v) observée (contrôle)",
    "courbe.v85_setra": "V85(R) des courbes de rase campagne : référence de la règle de vitesse en courbe pour R ≥ R0",
    "courbe.bus_alat": "plafond d'accélération latérale du profil bus",
    # tactique
    "creneau.norme_fr": "créneau critique de référence t_c(manœuvre, vitesse de la voie prioritaire) ; × facteur du conducteur",
    "creneau.norme_fr_vsa70": "créneaux critique et complémentaire sur artères à 70 km/h",
    "creneau.giratoire_meta": "créneau critique et temps de suivi en entrée de giratoire",
    "creneau.facteur_conducteur": "facteur individuel appliqué au créneau critique",
    "creneau.facteur_suivi": "facteur individuel appliqué au temps de suivi",
    "stop.comportement": "modalité tirée à chaque STOP (arrêt complet, glissé, absent), facteur style conservé",
    "stop.vitesse_residuelle_glisse": "vitesse minimale d'un arrêt glissé (proxy)",
    "feu.seuil_arret_jaune": "seuil individuel de temps à la ligne au-delà duquel le conducteur s'arrête au jaune",
    "pieton.taux_cede": "probabilité de céder à un piéton qui attend (tirée à chaque rencontre, facteur style)",
    "pieton.approche": "profil d'approche d'un passage piéton (cible de validation)",
    "ralent.vitesse_franchissement": "vitesse cible au franchissement d'un ralentisseur",
    "vdv.duree_chevauchement": "durée de la phase latérale d'un changement de voie",
    "vdv.insertion_devant": "distances et lacet des insertions devant un véhicule (validation)",
    "mobil.kesting2007": "critères de sécurité et d'incitation du changement de voie (MOBIL)",
    # population
    "hetero.novice_vitesses_max": "plafonds de vitesse du profil novice (R413-5)",
    "hetero.distraction_part_temps": "part du temps de conduite en tâche secondaire (France 8,3 %) : fréquence des épisodes de distraction",
    "velo.vitesse_traversee": "vitesse des cyclistes en carrefour au vert",
    "velo.acceleration_revue": "accélération des cyclistes (plage de la revue)",
    "hetero.cycliste_age": "vitesse désirée des cyclistes par âge et type de vélo",
    "vehicule.bicyclette_cinematique_validite": "seuil de bascule bicyclette cinématique -> dynamique (a_y ≥ 0,5 µg)",
}
USAGE_DEFAUT = {
    ("VAL", None): "référence de validation (voir validation.cibles)",
    ("REF", None): "comparaison avec un logiciel ou un modèle existant (pas utilisé tel quel)",
    ("POP", "composition"): "tirage de la classe de véhicule et de la composition du trafic",
    ("VEH", "parametre_vehicule"): "tirage ou réglage du véhicule (dynamique.py, population.py du volet 01)",
    ("VEH", "vehicule_reference"): "véhicule de référence (géométrie, braquage, performances mesurées)",
    ("VEH", "norme_vehicule"): "borne réglementaire du véhicule (contrôle et plafonds)",
    ("VEH", "adherence"): "adhérence longitudinale et transversale (cercle de friction)",
}


def usage(couche, role, pid):
    if pid in USAGE:
        return USAGE[pid]
    return USAGE_DEFAUT.get((couche, role)) or USAGE_DEFAUT.get((couche, None)) or {
        "PER": "perception", "LON": "contrôle longitudinal", "LAT": "contrôle latéral", "TAC": "décision tactique",
        "POP": "population et profils", "CTX": "modulateur de contexte", "VEH": "véhicule"}.get(couche, "")


# ------------------------------------------------------------------------------------ normalisation
def source_v01(p, cat):
    s = p["source"]
    c = cat.get(s.get("doc"), {})
    return {"doc": c.get("titre", s.get("doc")), "page": s.get("page"), "annee": s.get("annee"),
            "cle": s.get("doc"), "catalogue": f"V01:{s.get('doc')}", "url": c.get("url"), "licence": c.get("licence")}


def source_v02(p, cat):
    s = p["source"]
    c = cat.get(s.get("cle"), {})
    return {"doc": s.get("doc"), "page": s.get("page"), "annee": s.get("annee"), "cle": s.get("cle"),
            "catalogue": f"V02:{s.get('cle')}", "auteurs": s.get("auteurs"), "url": c.get("url"),
            "licence": c.get("licence"), "fichier": s.get("fichier")}


def source_v03(p):
    s = p["source"]
    return {"doc": s.get("doc"), "page": s.get("page"), "annee": s.get("annee"), "cle": None, "catalogue": "V03"}


def entree(volet, fichier, p, couche, role, src):
    e = {
        "id": f"{couche}.{p['id']}",
        "couche": couche,
        "role": role,
        "grandeur": p.get("grandeur"),
        "population": p.get("population"),
        "loi": p.get("loi"),
        "parametres": copy.deepcopy(p.get("parametres")),
        "unite": p.get("unite"),
        "conditions": p.get("conditions"),
        "nature": NATURE.get(p.get("nature"), p.get("nature")),
        "source": {k: v for k, v in src.items() if v is not None or k in ("doc", "page", "annee")},
        "confiance": CONF.get(p.get("confiance"), p.get("confiance")),
        "usage": usage(couche, role, p["id"]),
        "origine": {"volet": volet, "fichier": fichier, "id": p["id"],
                    "nature": p.get("nature"), "confiance": p.get("confiance")},
    }
    if p.get("tirage"):
        e["tirage"] = copy.deepcopy(p["tirage"])
    for k in ("statistiques_publiees", "notes"):
        if p.get(k):
            e[k] = copy.deepcopy(p[k])
    return e


# ------------------------------------------------------------------------------------ entrées de conception
def entrees_conception(C, idx02):
    """Paramètres propres au volet 04 : dérivés des calculs de cohérence ou des sources (calcul indiqué)."""
    c1 = C["C1_decharge_feu"]
    ph = c1["population_heterogene"]
    r_meneur = ph["r_cale_population_reaction_meneur"]["r"]
    r_vert = ph["r_cale_population_reaction_vert"]["r"]
    src_c = {"doc": "Calculs de cohérence de la conception (verifier_coherence.py), cibles Certu Feux 2010 p. 34-35 "
                    "(1 800 uvpd/h) et lois du volet 02", "page": "coherence.json, section C1", "annee": 2026,
             "cle": "V04_COHERENCE", "catalogue": "V04:COHERENCE"}
    out = [
        {"id": "LON.MOD.T_suivi", "couche": "LON", "role": "relation",
         "grandeur": "Temps intervéhiculaire désiré de l'IIDM en suivi stable, par conducteur",
         "population": "conducteurs VL", "loi": "fonction",
         "parametres": {"expression": "T_suivi_i = TIV_moyen_i - s0_i / v_ref", "v_ref_ms": 12.0,
                        "v_ref_prototype": "médiane de la loi de vitesse désirée du réseau (v0.2 du prototype ; v0.1 : 12 m/s partout)",
                        "TIV_moyen_i": "LON.tiv.moyen_conducteur_urbain (ou _autoroute)", "s0_i": "LON.tiv.ecart_arret"},
         "unite": "s", "conditions": "IIDM : à l'équilibre l'écart net vaut s0 + vT, donc TIV net = T + s0/v",
         "nature": "derive", "confiance": "moyenne",
         "source": {"doc": "Huang 2018 (TIV = distance radar / vitesse : écart net), IIDM (code SUMO MSCFModel_EIDM.cpp l. 1060-1075) ; "
                           "v_ref = 12 m/s est une convention (Huang : suivi à v > 10 m/s)",
                    "page": "Huang 2018 p. 5 (définition) ; coherence.json C2", "annee": 2026, "cle": "V04_COHERENCE",
                    "catalogue": "V04:COHERENCE"},
         "usage": "T de l'IIDM en suivi stable", "tirage": {"groupe": "tiv_moyen", "note": "même variable latente que le TIV moyen"},
         "valeurs_derivees": {"T_suivi_median_s": c1["T_suivi_median_s"]}},
        {"id": "LON.MOD.T_decharge_rapport", "couche": "LON", "role": "parametre_modele_a_caler",
         "grandeur": "Rapport r = T_décharge / T_suivi appliqué pendant la décharge d'une file (démarrage au vert, trafic dense)",
         "population": "conducteurs VL (population hétérogène du volet 02)", "loi": "plage",
         "parametres": {"min": r_meneur, "max": r_vert, "depart_calage": round(0.5 * (r_meneur + r_vert), 3),
                        "note": "paramètre global (même r pour tous), pas une loi tirée par conducteur ; départ du calage = milieu de la plage"},
         "unite": "-", "conditions": "IIDM + démarrage EIDM + TPR anticipé au démarrage ; r calé pour 2,0 s/véh (rangs 5-12)",
         "nature": "derive", "confiance": "faible", "source": src_c,
         "usage": "T_i = r × T_suivi,i tant que le conducteur sort d'un arrêt ou suit en file dense ; relaxation vers T_suivi,i ensuite (H-03)",
         "valeurs_derivees": {"r_reaction_au_meneur": r_meneur, "r_reaction_au_vert": r_vert,
                              "debit_si_r_1_veh_h": ph["r_1_T_suivi_reaction_meneur"]["debit_saturation_veh_h"]},
         "notes": "Bornes = deux hypothèses extrêmes de réaction au démarrage (chaîne derrière le meneur / chacun réagit au vert). "
                  "Valeur à recaler quand le modèle complet existera (cibles V-10)."},
        {"id": "LAT.MOD.R0_courbe", "couche": "LAT", "role": "relation",
         "grandeur": "Rayon de bascule entre la règle de Bosetti (courbes serrées) et la V85 Sétra (courbes de rase campagne)",
         "population": "-", "loi": "constante",
         "parametres": {"valeur": 40.0,
                        "verification": {"R_m": 40, "bosetti_p85_kmh": None, "setra_v85_Vlim102_kmh": None}},
         "unite": "m", "conditions": "rayon où la frontière P85 de Bosetti égale la V85 Sétra (Vlim 102 km/h)",
         "nature": "derive", "confiance": "faible",
         "source": {"doc": "Calculs de cohérence (verifier_coherence.py) : Bosetti 2014 tab. 5 contre Cerema 2018 p. 8",
                    "page": "coherence.json, section C3", "annee": 2026, "cle": "V04_COHERENCE", "catalogue": "V04:COHERENCE"},
         "usage": "v_courbe,i(R) = max(v_Bosetti,i(R), V85_Sétra(R)·κ_i) (règle R-LAT-01)"},
        {"id": "VEH.MOD.mu_sec", "couche": "VEH", "role": "parametre_vehicule",
         "grandeur": "Adhérence longitudinale mobilisable sur chaussée sèche (pneus en bon état)",
         "population": "VP récentes", "loi": "uniforme", "parametres": {"min": 1.0, "max": 1.11},
         "unite": "-", "conditions": "borne basse = estimation du volet 01 (dynamique.py) ; borne haute = MFDD ADAC 10,9 m/s² / g",
         "nature": "estimation", "confiance": "faible",
         "source": {"doc": "ADAC Autotests (MFDD 100-0 km/h, 10 voitures) ; volet 01 dynamique.py (mu_adherence = 1,0)",
                    "page": "VEHICULES.md § 5.2 ; adherence ADH-MESURE-ADAC-100-0", "annee": 2026, "cle": "ADAC",
                    "catalogue": "V01:ADAC"},
         "usage": "rayon du cercle de friction sur sec (règle R-VEH-03)"},
    ]
    # écart-type des vitesses PL dérivé des taux de respect publiés (même méthode que le volet 02 pour les VT)
    pl = idx02["vit.poids_lourds"]["parametres"]
    nd = statistics.NormalDist()
    for cle, vma, nom in [("autoroute_liaison_VMA90", 90.0, "autoroute_liaison"),
                          ("route_2_3_voies_VMA80", 80.0, "route_2_3_voies"),
                          ("artere_centre_ville_VMA50", 50.0, "artere_centre_ville")]:
        m = pl[cle]["jour"]
        resp = pl[cle]["respect_jour"]
        sd = (vma - m) / nd.inv_cdf(resp)
        out.append({
            "id": f"LON.MOD.vit_pl_{nom}", "couche": "LON", "role": "parametre_conducteur",
            "grandeur": f"Vitesse désirée des poids lourds, {nom.replace('_', ' ')}, de jour",
            "population": "PL du panel ONISR 2023", "loi": "normale",
            "parametres": {"moyenne": m, "ecart_type": round(sd, 2)},
            "unite": "km/h", "conditions": f"VMA PL {int(vma)} km/h ; écart-type = (VMA - moyenne) / Φ⁻¹(taux de respect {resp})",
            "nature": "estimation", "confiance": "faible",
            "source": {"doc": "ONISR, Observatoire des vitesses, résultats 2023 (moyenne et taux de respect PL)",
                       "page": "p. 7 (via volet 02 vit.poids_lourds) ; écart-type dérivé ici (hypothèse normale)",
                       "annee": 2024, "cle": "ONISR2023", "catalogue": "V02:ONISR2023"},
            "usage": "v0 des PL (profil conducteur_pl)", "tirage": {"facteur": "style", "charge": 0.6, "groupe": "vitesse"}})
    return out


# ------------------------------------------------------------------------------------ sections de conception
ARCHITECTURE = [
    {"code": "PER", "nom": COUCHES["PER"], "frequence": "chaque pas (0,1 s) ; état perçu mis à jour aux points d'action",
     "entrees": ["état vrai des usagers voisins", "géométrie visible (bâti, végétation, mobilier, véhicules)", "signaux et contrôleurs"],
     "sorties": ["état perçu retardé et bruité (écart, Δv, accélération du meneur, temps aux conflits)", "liste des objets visibles"],
     "modele": "tampon de retard (TPR selon la situation) + erreurs de Wiener (HDM) + ligne de vue géométrique + épisodes de distraction",
     "regles": ["R-PER-01", "R-PER-02", "R-PER-03", "R-PER-04"]},
    {"code": "STR", "nom": COUCHES["STR"], "frequence": "au départ puis à chaque nouveau tronçon",
     "entrees": ["origine-destination", "graphe de voies"], "sorties": ["itinéraire", "voies admissibles par tronçon"],
     "modele": "plus court chemin (duarouter ou équivalent) ; voies à atteindre avant un mouvement tournant (anticipation LC2013)",
     "regles": ["R-STR-01"]},
    {"code": "TAC", "nom": COUCHES["TAC"], "frequence": "aux points d'action et à l'approche de chaque point singulier",
     "entrees": ["état perçu", "itinéraire", "régimes de priorité, conflits, signaux, passages piétons, ralentisseurs"],
     "sorties": ["consignes : vitesse cible locale, point d'arrêt, voie visée, autorisation d'engagement"],
     "modele": "MOBIL (changement de voie) ; acceptation de créneaux probabiliste ; STOP à trois modalités ; seuil de jaune ; cession aux piétons",
     "regles": ["R-TAC-01", "R-TAC-02", "R-TAC-03", "R-TAC-04", "R-TAC-05", "R-TAC-06", "R-TAC-07"]},
    {"code": "LON", "nom": COUCHES["LON"], "frequence": "chaque pas (commande lissée par le jerk)",
     "entrees": ["état perçu", "consignes tactiques", "v0 du réseau", "vitesse en courbe à venir"],
     "sorties": ["accélération longitudinale demandée"],
     "modele": "IIDM + CAH (coolness) + points d'action + T contextuel + démarrage EIDM + urgence de Markkula ; jerk borné à l'accélération et au freinage",
     "regles": ["R-LON-01", "R-LON-02", "R-LON-03", "R-LON-04", "R-LON-05"]},
    {"code": "LAT", "nom": COUCHES["LAT"], "frequence": "chaque pas",
     "entrees": ["trajectoire de voie (centre de voie, trajectoire de carrefour)", "courbure", "voie visée"],
     "sorties": ["angle de braquage demandé", "vitesse maximale en courbe (vers LON)"],
     "modele": "suivi de trajectoire à point de visée ; vitesse en courbe par conducteur ; triangle g-g de Bosetti ; changement de voie de durée tirée",
     "regles": ["R-LAT-01", "R-LAT-02", "R-LAT-03"]},
    {"code": "VEH", "nom": COUCHES["VEH"], "frequence": "chaque pas (sous-pas possible)",
     "entrees": ["accélération et braquage demandés", "pente", "adhérence de la surface"],
     "sorties": ["état réel (position, cap, vitesse, accélérations)"],
     "modele": "bicyclette cinématique (a_y < 0,5 µg) ; enveloppe a_max(v, pente) du volet 01 ; freinage borné par µg ; cercle de friction ; retards d'actionneurs",
     "regles": ["R-VEH-01", "R-VEH-02", "R-VEH-03", "R-VEH-04"]},
]

REGLES = [
    {"id": "R-PER-01", "couche": "PER", "enonce": "Retard de perception-réaction explicite et propre au conducteur, indépendant du pas : le conducteur agit sur l'état perçu à t - τ, τ tiré selon la situation (anticipée, signal inattendu, surprise, jaune).",
     "parametres": ["PER.tpr.anticipe", "PER.tpr.inattendu_signal", "PER.tpr.surprise_obstacle", "PER.feu.tpr_jaune"],
     "nature": "mesure (lois) + convention (aiguillage par situation)", "justification": "E1 du volet 03 ; NCHRP 400 tab. 13 et p. 36 ; Green 2000 (via Markkula 2016)"},
    {"id": "R-PER-02", "couche": "PER", "enonce": "Erreurs d'estimation corrélées dans le temps (processus de Wiener) sur l'écart et la vitesse relative : s_est = s·exp(V_s·w_s), Δv_est = Δv + s·r_c·w_Δv, temps de corrélation τ̃ ; intensité multipliée selon la vigilance (H-07). Pas de bruit blanc d'accélération (sigma Krauss = 0).",
     "parametres": ["PER.hdm.treiber2006"], "nature": "estimation (valeurs d'auteur HDM)", "justification": "E3 du volet 03 ; Treiber 2006 éq. 5-7 ; S1 (jerk de Krauss)"},
    {"id": "R-PER-03", "couche": "PER", "enonce": "Visibilité géométrique : un usager n'est perçu que s'il est en ligne de vue (bâti, végétation > 0,60 m, mobilier, véhicules masquants) et à moins de la distance de visibilité ; aux STOP et cédez, la décision est prise depuis la position de l'œil des guides (4 m de la ligne au STOP, ≈ 7 m au cédez en ville).",
     "parametres": [], "nature": "norme (positions d'œil) + convention (ligne de vue)", "justification": "Certu Carrefours urbains 2010 p. 97 (RF-GV-VIS-001 de DocRoute 00) ; champ de vision et stratégie du regard : lacune"},
    {"id": "R-PER-04", "couche": "PER", "enonce": "Distraction : à chaque événement, le conducteur a les yeux hors de la menace avec une probabilité moyenne de 8,3 %, plus forte quand sa vigilance est basse (H-18) ; une urgence suit alors la loi αB « yeux hors de la route » de Markkula. Le 8,3 % est une part du temps de conduite occupée par une tâche secondaire (UDRIVE, conversations comprises), pas une part de regards hors route : c'est un proxy. Durée des épisodes : lacune (H-08).",
     "parametres": ["POP.hetero.distraction_part_temps", "PER.tpr.markkula.alphaB_yeux_hors_route"], "nature": "hypothèse (proxy d'une mesure)", "justification": "UDRIVE D41.1 p. 5 ; Markkula 2016 fig. 10 ; relecture adverse du 17/10/2026"},
    {"id": "R-STR-01", "couche": "STR", "enonce": "Itinéraire par plus court chemin pondéré par le temps ; voies à rejoindre avant un mouvement imposé selon la logique stratégique de LC2013 (urgence croissante à l'approche).",
     "parametres": ["REF.sumo.lc2013"], "nature": "convention (défaut logiciel)", "justification": "aucune donnée comportementale d'itinéraire dans les volets ; choix d'itinéraire hors du périmètre v0.1"},
    {"id": "R-TAC-01", "couche": "TAC", "enonce": "Changement de voie discrétionnaire par MOBIL : sécurité ã_n ≥ -b_safe (4 m/s²) et incitation ã_c - a_c + p_i[(ã_n - a_n) + (ã_o - a_o)] > Δa_th (0,1 m/s²), biais voie de droite 0,3 m/s² ; politesse p_i ∈ [0 ; 1] liée au style (H-09). Changements obligatoires : LC2013 stratégique. Exécution latérale de durée T_vdv,i (lognormale NGSIM).",
     "parametres": ["TAC.mobil.kesting2007", "TAC.vdv.duree_chevauchement"], "nature": "estimation + hypothèse", "justification": "Kesting 2007 tab. 1 ; Thiemann 2008 ; MOBIL dérive les décisions du modèle de poursuite (cohérence)"},
    {"id": "R-TAC-02", "couche": "TAC", "enonce": "Acceptation de créneau : le conducteur accepte le premier créneau (temps d'arrivée du prioritaire au point de conflit, vu depuis le point de décision) ≥ t_c,i = facteur_i × t_c,FR(manœuvre, vitesse de la voie prioritaire) ; temps de suivi t_f,i = facteur_suivi_i × t_f ; il n'impose pas au prioritaire un freinage supérieur à sa décélération habituelle b (borne, H-10). Effet de l'attente : non modélisé en v0.1 (lacune).",
     "parametres": ["TAC.creneau.norme_fr", "TAC.creneau.norme_fr_vsa70", "TAC.creneau.giratoire_meta", "TAC.creneau.facteur_conducteur", "TAC.creneau.facteur_suivi"],
     "nature": "norme (valeurs centrales) + estimation (dispersion)", "justification": "E6 du volet 03 ; Certu CU 2010 p. 93 (paramètre de la méthode de capacité) ; Giuffrè 2016 ; S3 (SUMO : 12,4-14,0 s depuis l'arrivée à 3 m, 12,4-13,4 s depuis l'arrêt en tête de ligne ; freinage imposé de 4,5 m/s² avec impatience)"},
    {"id": "R-TAC-03", "couche": "TAC", "enonce": "STOP : modalité tirée à chaque STOP avec le facteur style du conducteur (arrêt complet / glissé / absent) ; arrêt complet = vitesse nulle à la ligne puis recherche de créneau après le TPR anticipé ; arrêt glissé = vitesse minimale v_g,i à la ligne ; absence d'arrêt = passage à la vitesse d'approche si aucun conflit perçu. Durée minimale d'arrêt : lacune.",
     "parametres": ["TAC.stop.comportement", "TAC.stop.vitesse_residuelle_glisse"], "nature": "estimation (confiance faible)", "justification": "E7 du volet 03 ; Vaughan 2006 ; aucune observation française"},
    {"id": "R-TAC-04", "couche": "TAC", "enonce": "Feux : au début du jaune, après le TPR jaune, le conducteur s'arrête si son temps à la ligne TTL dépasse son seuil T_i (logistique, t50 = 4,0 s) ; sinon il passe. Option de faisabilité (H-11). Au vert : démarrage après le TPR anticipé, facteur de démarrage EIDM, T de décharge (LON.MOD.T_decharge_rapport).",
     "parametres": ["TAC.feu.seuil_arret_jaune", "PER.feu.tpr_jaune", "LON.MOD.T_decharge_rapport", "LON.eidm.demarrage_salles2020"],
     "nature": "estimation", "justification": "E5 du volet 03 ; FHWA 2008 p. 4-24/4-25 ; S2 ; calcul C6"},
    {"id": "R-TAC-05", "couche": "TAC", "enonce": "Piétons : céder obligatoirement au piéton engagé (art. R415-11) ; au piéton qui attend au bord d'un passage non géré, céder avec la probabilité p tirée à chaque rencontre (facteur style). Approche : ralentissement de confort vers le passage.",
     "parametres": ["TAC.pieton.taux_cede", "TAC.pieton.approche", "VAL.pieton.distance_regle_cu"], "nature": "mesure (Pologne, faible) + norme", "justification": "Dąbrowska 2021 ; Gankhuyag 2023 ; code de la route R415-11"},
    {"id": "R-TAC-06", "couche": "TAC", "enonce": "Ralentisseurs (dos-d'âne, plateau, coussin) : vitesse cible au droit du dispositif v_r,i tirée par conducteur (facteur style), imposée comme vitesse désirée locale et anticipée sur l'horizon de prévisualisation : l'IIDM ralentit au plus à b_i hors urgence ; ré-accélération ensuite.",
     "parametres": ["TAC.ralent.vitesse_franchissement", "VAL.ralent.objectif_conception"], "nature": "estimation (mesure belge 10-20 m en aval, dispositifs mêlés, confiance faible)", "justification": "Vias 2021 p. 39-40 (moyenne belge 34,0 km/h ; Bruxelles 27,6, Flandre 34,9, Wallonie 34,5) ; Certu coussins et plateaux 2010"},
    {"id": "R-TAC-07", "couche": "TAC", "enonce": "Vitesse désirée v0,i = quantile du conducteur (groupe latent « vitesse ») dans la loi du réseau (correspondance_reseaux), + écart de nuit, + écart de week-end ; plafonds des profils (novice) ; lois PL pour les PL.",
     "parametres": ["LON.vit.artere_centre_ville_50", "CTX.vit.ecart_jour_nuit", "CTX.vit.week_end", "POP.hetero.novice_vitesses_max", "LON.MOD.vit_pl_autoroute_liaison"],
     "nature": "estimation (lois ONISR)", "justification": "ONISR 2019 et 2023 ; volet 02 § 4.4"},
    {"id": "R-LON-01", "couche": "LON", "enonce": "Poursuite IIDM (Treiber & Kesting, forme du code SUMO EIDM l. 1060-1075) avec δ = 4, a_i = pic de démarrage, b_i = décélération habituelle maximale, s0_i, T_i contextuel, v0_i du réseau et de la courbe à venir ; heuristique CAH (coolness 0,99) pour l'anticipation du meneur.",
     "parametres": ["LON.acc.demarrage_pic", "LON.dec.max_courante_urbain", "LON.tiv.ecart_arret", "LON.MOD.T_suivi", "LON.idm.treiber2000", "LON.acc_idm.kesting2010"],
     "nature": "estimation (structure) + mesure (lois)", "justification": "C2 : l'IDM donne un TIV de 3,19 s à 10 m/s quand v0 = 41,2 km/h, l'IIDM 2,06 s"},
    {"id": "R-LON-02", "couche": "LON", "enonce": "Temps intervéhiculaire contextuel : T_i = T_suivi,i en suivi stable ; T_i = r·T_suivi,i pendant la décharge d'une file et en trafic dense, avec relaxation vers T_suivi,i (H-03).",
     "parametres": ["LON.MOD.T_suivi", "LON.MOD.T_decharge_rapport"], "nature": "dérivé + hypothèse", "justification": "C1 : T = T_suivi donne 1 297 véh/h contre 1 800 uvpd/h (Certu Feux 2010 p. 34)"},
    {"id": "R-LON-03", "couche": "LON", "enonce": "Points d'action : la consigne est recalculée toutes les τ_i (TPR anticipé) ou immédiatement si la décélération voulue augmente de plus de ε (logique EIDM) ; jerk borné à |j| ≤ j_confort hors urgence, à l'accélération ET au freinage.",
     "parametres": ["PER.tpr.anticipe", "LON.acc.jerk_confort", "REF.sumo.eidm.jerkmax", "REF.sumo.eidm.epsilonacc"], "nature": "défaut logiciel + recommandation d'auteur (jerk, confiance faible)", "justification": "E3 du volet 03 (l'EIDM ne borne pas le jerk des freinages de sécurité) ; T_i ≥ intervalle des points d'action (H-17)"},
    {"id": "R-LON-04", "couche": "LON", "enonce": "Urgence (option cinématique) : début du freinage tB = t0,2 + αB(tC - t0,2), jerk jB = kB·τ⁻¹, décélération maximale tirée (Markkula) puis bornée par µg (VEH).",
     "parametres": ["PER.tpr.markkula.alphaB_yeux_sur_menace", "PER.tpr.markkula.alphaB_yeux_hors_route", "LON.dec.urgence_max_markkula"], "nature": "mesure", "justification": "Markkula 2016 fig. 10 ; remplace un temps de réaction fixe"},
    {"id": "R-LON-05", "couche": "LON", "enonce": "Commande = min(accélération voulue par le conducteur, a_max du véhicule à v, pente et µ) ; le triangle g-g du conducteur (a, b, c de Bosetti) borne la combinaison avec l'accélération latérale.",
     "parametres": ["LON.acc.max_conducteur_bosetti", "LAT.courbe.alat_max_conducteur", "VAL.dec.max_conducteur_bosetti", "VEH.VP-DYN-K"], "nature": "mesure + dérivé", "justification": "C4 : à 50 km/h, 60 % des conducteurs ont un b de Bosetti supérieur à la capacité de leur voiture"},
    {"id": "R-LAT-01", "couche": "LAT", "enonce": "Vitesse en courbe : v_courbe,i(R) = max(min(α_i R^(1/3), √(a_lat,i R)), V85_Sétra(R ; Vlim)·κ_i), κ_i = v_Bosetti,i(R0) / P85[v_Bosetti(R0)] (même rang, continuité en R0 = 40 m) ; en agglomération, seul le terme de Bosetti ; v = min(v0_i, v_courbe,i).",
     "parametres": ["LAT.courbe.alpha_deux_tiers", "LAT.courbe.alat_max_conducteur", "LAT.courbe.v85_setra", "LAT.MOD.R0_courbe"],
     "nature": "dérivé + hypothèse (H-05)", "justification": "C3 : la frontière de Bosetti (piste italienne, courbes serrées) passe 17 km/h sous la V85 Sétra à R = 100 m"},
    {"id": "R-LAT-02", "couche": "LAT", "enonce": "Suivi de trajectoire à point de visée (géométrie de la voie ou de la trajectoire de carrefour), angle de braquage borné par δ_max du véhicule (Ackermann, volet 01) ; temps de visée, vitesse de braquage et errance latérale : lacunes (H-12).",
     "parametres": ["VEH.VP-BRAQUAGE-DERIVE", "VEH.BUS12-DIM-CITARO"], "nature": "convention + lacune", "justification": "aucune mesure de commande latérale humaine dans les volets"},
    {"id": "R-LAT-03", "couche": "LAT", "enonce": "Changement de voie : déplacement latéral sur T_vdv,i (durée de chevauchement, NGSIM), profil latéral lisse ; accélération latérale bornée par le triangle g-g du conducteur ; bus : a_lat ≤ 1 m/s².",
     "parametres": ["TAC.vdv.duree_chevauchement", "LAT.courbe.bus_alat"], "nature": "estimation + norme", "justification": "SUMO change de voie en un pas par défaut (volet 03 § 3.7)"},
    {"id": "R-VEH-01", "couche": "VEH", "enonce": "Enveloppe longitudinale du volet 01 : a_max(v, p) = min(a_lancement, kP/(mv), µg·part_essieu) - résistances ; décélération ≤ min(d_max véhicule, µ·g) ; vitesse ≤ vmax et limiteurs (PL 90, bus 100 km/h).",
     "parametres": ["VEH.VP-DYN-K", "VEH.VP-DYN-A-LANCEMENT", "VEH.VP-FREIN-DMAX-SEC-PARC", "VEH.VP-FREIN-DMAX-SEC", "VEH.REG-LIMITEURS"], "nature": "dérivé (calé ADAC) ; d_max du parc en circulation estimé d'après Greibe 2007", "justification": "volet 01 § 4 (validation croisée 7,7 / 8,4 / 4,0 %) et § 5.2"},
    {"id": "R-VEH-02", "couche": "VEH", "enonce": "Bicyclette cinématique tant que a_y < 0,5 µg ; au-delà, bicyclette dynamique à pneus linéaires dès que les rigidités de dérive et l'inertie seront sourcées (lacune) ; en attendant, saturation par le cercle de friction.",
     "parametres": ["VEH.vehicule.bicyclette_cinematique_validite", "VEH.MOD.mu_sec"], "nature": "estimation", "justification": "Polack 2018 ; C5 : 25 % des conducteurs ont a_lat max > 0,5 µg sur sec"},
    {"id": "R-VEH-03", "couche": "VEH", "enonce": "Cercle de friction √(a_x² + a_y²) ≤ µ g, µ selon la surface : sec µ_sec ; mouillé : relation de Greibe et CFL des revêtements ; marquages mouillés : µ × PTV_marque/PTV_enrobé (règle TQ-MQR-007 du dépôt, confiance faible).",
     "parametres": ["VEH.MOD.mu_sec", "VEH.ADH-MESURE-GREIBE-MODELE", "VEH.ADH-CFL-REVETEMENT"], "nature": "estimation", "justification": "volet 01 § 6 ; volet 03 § 7"},
    {"id": "R-VEH-04", "couche": "VEH", "enonce": "Retards d'actionneurs : freins des lourds ≤ 0,6 s (R13) ; VP : temps mort système ≤ 0,36 s (borne implicite R13-H), 0 en v0.1 avec d_max = MFDD (rampe incluse) ; la rampe propre au conducteur est portée par le jerk (R-LON-03/04).",
     "parametres": ["VEH.REG-R13-TEMPS-REPONSE", "VEH.FREIN-TEMPS-MORT-REGLEMENTAIRE", "VEH.FREIN-ETABLISSEMENT-VP", "VEH.FREIN-PEDALE-PRO-VS-NONPRO"], "nature": "norme + lacune", "justification": "volet 01 § 5.3"},
]

HYPOTHESES = [
    {"id": "H-01", "enonce": "Les paramètres d'un conducteur sont liés par deux facteurs latents (style, vigilance) avec les 19 charges du volet 02. Dans un groupe, les paramètres ne sont plus identiques en rang : chacun reçoit un bruit propre (corrélation intra-groupe des résidus λ_intra = 0,5 dans le prototype v0.2) ; les grandeurs ordonnées sont construites par incréments positifs (TPR inattendu = TPR anticipé + Δ) ou par plancher (a1 ≥ b, décélération d'urgence ≥ b, TIV minimal ≤ TIV moyen).", "statut": "hypothèse du volet 02, complétée le 17/10/2026 (la v0.1 imposait une corrélation intra-groupe de 1, d'où 4,65 % de conducteurs plus lents à l'anticipé qu'à la surprise)", "a_caler_sur": "trajectoires individuelles (highD/inD/rounD sous licence, ou relevés français)"},
    {"id": "H-02", "enonce": "Conducteur et véhicule sont tirés indépendamment (pas de lien style / puissance).", "statut": "hypothèse", "a_caler_sur": "aucune source lue ; à revoir si une enquête relie style et véhicule"},
    {"id": "H-03", "enonce": "Le temps intervéhiculaire désiré dépend du contexte : T_suivi en suivi stable, r·T_suivi en décharge de file et en trafic dense, avec relaxation entre les deux.", "statut": "hypothèse appuyée par C1 (une seule valeur de T ne reproduit pas à la fois Huang 2018 et Certu 1800 uvpd/h)", "a_caler_sur": "V-10 (saturation, TIV par rang) et V-06 (TIV en suivi)"},
    {"id": "H-04", "enonce": "La loi ONISR des vitesses pratiquées loin des carrefours sert de vitesse désirée v0. Elle n'est PAS une loi de vitesses libres au sens strict : l'ONISR 2023 (annexe 2, p. 40) ne retire que les périodes de 30 min à vitesse moyenne trop faible, sans filtre par véhicule (contrairement à Vias 2021 et au Cerema V80 : TIV > 5 s) ; sa queue basse contient des véhicules contraints. Le prototype tronque la loi sous son 5e centile (convention, sensibilité publiée).", "statut": "hypothèse + convention (corrigée le 17/10/2026 : la v0.1 affirmait que l'ONISR mesure « la vitesse désirée »)", "a_caler_sur": "V-01 à V-05 ; une source française à véhicules libres"},
    {"id": "H-05", "enonce": "En courbe, chaque conducteur garde son rang : sa vitesse est la V85 Sétra multipliée par κ_i pour R ≥ R0, et sa frontière de Bosetti pour R < R0.", "statut": "hypothèse (dispersion en courbe non mesurée en France)", "a_caler_sur": "V-15 ; mesures de vitesse en courbe (Cerema) à collecter"},
    {"id": "H-06", "enonce": "Les créneaux critiques français du Certu sont les valeurs centrales ; la dispersion (CV 0,20) vient d'Italie.", "statut": "hypothèse du volet 02", "a_caler_sur": "V-16 ; relevés de créneaux à Meylan"},
    {"id": "H-07", "enonce": "L'intensité des erreurs de perception croît quand la vigilance baisse.", "statut": "hypothèse (forme reprise du device driverstate de SUMO, sans paramétrage publié)", "a_caler_sur": "V-21 (fluctuations le long d'une file)"},
    {"id": "H-08", "enonce": "Les épisodes de distraction sont répartis au hasard dans le temps, avec une part moyenne de 8,3 %.", "statut": "hypothèse (durée des épisodes non sourcée)", "a_caler_sur": "UDRIVE (accès restreint) ou SHRP2"},
    {"id": "H-09", "enonce": "La politesse MOBIL p_i suit une loi uniforme sur [0 ; 1] et dépend du style (charge -0,4).", "statut": "hypothèse", "a_caler_sur": "fréquences et distances d'insertion (V-20)"},
    {"id": "H-10", "enonce": "Un conducteur non prioritaire n'impose pas au prioritaire une décélération supérieure à la décélération habituelle b de ce dernier.", "statut": "hypothèse (remplace le freinage maximal imposé par l'impatience SUMO)", "a_caler_sur": "V-16, S3"},
    {"id": "H-11", "enonce": "Option : au jaune, un conducteur s'arrête aussi quand TTL dépasse la durée du jaune et que l'arrêt est possible.", "statut": "option à trancher (C6 : sans elle, 14 % des véhicules présents au début du jaune franchissent la ligne au rouge avec un jaune de 3 s)", "a_caler_sur": "taux de franchissement au rouge en France (lacune)"},
    {"id": "H-12", "enonce": "Commande latérale : temps de visée, vitesse de braquage et errance latérale à caler.", "statut": "lacune", "a_caler_sur": "trajectoires (inD, rounD) ou relevés"},
    {"id": "H-13", "enonce": "Les lois belges (zones 30, routes à 70 et 90 km/h, ralentisseurs) valent pour la France faute de mesure française.", "statut": "hypothèse", "a_caler_sur": "mesures françaises (Grenoble Métropole apaisée non trouvée)"},
    {"id": "H-14", "enonce": "Dans la décharge d'une file de feu, l'accélération a_i de l'IIDM est multipliée par un facteur global (calé sur le pic du rang 1 de Salles 2020 fig. 8, drone).", "statut": "calage du prototype (P-03)", "a_caler_sur": "démarrages par rang (drone) ; autre carrefour pour la validation"},
    {"id": "H-15", "enonce": "Un freinage du meneur au-delà de la décélération habituelle b du SUIVEUR est « inattendu » sauf s'il s'explique (meneur lent, ligne d'arrêt proche, cible de vitesse visible, véhicule arrêté ou freinant devant lui). Le TPR court depuis l'allumage des feux stop du meneur ; règle d'allumage = convention (seuil de détection 1,3 m/s², repris par analogie du R13-H § 5.2.22.2 qui vise le freinage automatique ou régénératif, pas le freinage du conducteur : pour celui-ci, le § 5.2.22.1 allume les feux à toute action sur le frein de service).", "statut": "convention du prototype (P-06), corrigée le 17/10/2026 (la v0.1 lisait le b du meneur et qualifiait le seuil de norme)", "a_caler_sur": "événements non critiques de freinage (naturalistes)"},
    {"id": "H-16", "enonce": "La cinématique d'urgence de Markkula ne s'applique que si la situation devient urgente (looming ≥ 0,2 s⁻¹) avant la réponse ordinaire au TPR « signal inattendu », ou si le conducteur regarde ailleurs.", "statut": "convention du prototype (P-07) ; Markkula 2016 annexe B.3 : les lois sur-représentent les réactions lentes", "a_caler_sur": "taux de collision par freinage brusque (lacune)"},
    {"id": "H-17", "enonce": "Le temps intervéhiculaire désiré d'un conducteur ne descend pas sous l'intervalle entre ses points d'action (T_i ≥ Δ_a,i = TPR anticipé), y compris en décharge de file.", "statut": "convention de stabilité du prototype v0.2 (la v0.1 laissait T < Δ_a pour 35 % des conducteurs en décharge)", "a_caler_sur": "V-10 et V-24 (zéro collision sur 5 graines × 200 files)"},
    {"id": "H-18", "enonce": "La probabilité d'avoir les yeux hors de la menace lors d'un événement vaut en moyenne la part du temps en tâche secondaire (UDRIVE, France 8,3 %) et croît quand la vigilance baisse (charge 0,5 sur le facteur vigilance, comme le groupe TPR).", "statut": "hypothèse (proxy : la donnée UDRIVE n'est pas une part de regards hors route)", "a_caler_sur": "parts de regards hors route (SHRP2, UDRIVE, accès restreint)"},
]

CORRESPONDANCE_RESEAUX = [
    {"id": "CR-01", "condition": "contexte.zones_vitesse[type=zone30] contient la voie, ou routes[].vitesse_kmh = 30", "loi": "LON.vit.zone_30_be", "confiance": "moyenne", "nature": "hypothèse H-13"},
    {"id": "CR-02", "condition": "agglomeration = vrai, vitesse_kmh = 50, route départementale ou nationale traversant une petite agglomération (paramètre de scène)", "loi": "LON.vit.traversee_petite_agglo_50", "confiance": "faible", "nature": "convention (l'ONISR ne publie pas la taille seuil dans le rapport lu)"},
    {"id": "CR-03", "condition": "agglomeration = vrai, vitesse_kmh = 50, section entre une limite d'agglomération (EB10/EB20) et le premier carrefour", "loi": "LON.vit.entree_sortie_agglo_50", "confiance": "faible", "nature": "convention ; loi 2023 bimodale (mélange à prévoir)"},
    {"id": "CR-04", "condition": "agglomeration = vrai, vitesse_kmh = 50, autres voies (artères, rues, dessertes)", "loi": "LON.vit.artere_centre_ville_50", "confiance": "moyenne (artères) / faible (dessertes)", "nature": "convention ; aucune mesure ONISR sur les dessertes"},
    {"id": "CR-05", "condition": "vitesse_kmh = 70", "loi": "VAL.vit.route_70_be", "confiance": "faible", "nature": "hypothèse H-13 (loi belge)"},
    {"id": "CR-06", "condition": "agglomeration = faux, vitesse_kmh = 80 (ou 90 sur les sections relevées), chaussée bidirectionnelle", "loi": "LON.vit.route_2_3_voies_80", "confiance": "elevee", "nature": "mesure ONISR (réseau « routes à 2 ou 3 voies », VMA 80-90 km/h : l'ONISR 2023 mêle des sections relevées à 90, p. 7 note * et p. 39)"},
    {"id": "CR-07", "condition": "agglomeration = faux, vitesse_kmh = 90", "loi": "VAL.vit.route_90_be", "confiance": "faible", "nature": "hypothèse H-13 (loi belge) ; l'ONISR mêle quelques sections à 90 dans le réseau 2-3 voies"},
    {"id": "CR-08", "condition": "categorie = voie_express ou route à 2x2 voies hors agglomération, vitesse_kmh = 110", "loi": "LON.vit.route_2x2_110", "confiance": "elevee", "nature": "mesure ONISR"},
    {"id": "CR-09", "condition": "categorie = autoroute ou voie_express urbaine (dégagement), vitesse_kmh ≤ 110", "loi": "LON.vit.autoroute_degagement_110", "confiance": "elevee", "nature": "mesure ONISR"},
    {"id": "CR-10", "condition": "categorie = autoroute, vitesse_kmh = 130", "loi": "LON.vit.autoroute_liaison_130", "confiance": "elevee", "nature": "mesure ONISR"},
    {"id": "CR-11", "condition": "zone_rencontre (20 km/h) ou aire_pietonne", "loi": None, "confiance": "faible", "nature": "lacune : aucune loi sourcée ; v0.1 = limite réglementaire × facteur de la zone 30 belge (1,277), à signaler"},
    {"id": "CR-12", "condition": "bretelle, anneau_giratoire, trajectoire de carrefour", "loi": "loi du réseau amont, puis règle de courbe R-LAT-01", "confiance": "moyenne", "nature": "convention"},
    {"id": "CR-13", "condition": "véhicule PL", "loi": "LON.MOD.vit_pl_* (autoroute, 2-3 voies, artère)", "confiance": "faible", "nature": "estimation"},
    {"id": "CR-14", "condition": "nuit / week-end", "loi": "CTX.vit.ecart_jour_nuit (2023 de préférence), CTX.vit.week_end", "confiance": "moyenne", "nature": "mesure ONISR"},
    {"id": "CR-15", "condition": "profil novice", "loi": "POP.hetero.novice_vitesses_max (plafonds R413-5, même rang)", "confiance": "elevee", "nature": "norme"},
]

LECTURE_MODELE_ROUTE = [
    {"element": "graphe_voies.voies[] (polyligne, sens, tags, vitesse) et graphe_voies.liens[] (sortant, entrant, adjacent, gauche/droite, convergence/divergence)", "usage": "routage, suivi de voie, voisins, changements de voie possibles", "couche": ["STR", "TAC", "LAT"], "statut": "existant"},
    {"element": "routes[].categorie, agglomeration, vitesse_kmh, sens_unique, prioritaire ; contexte.agglomerations ; contexte.zones_vitesse", "usage": "réseau ONISR de la vitesse désirée (correspondance_reseaux), priorités", "couche": ["LON", "TAC"], "statut": "existant"},
    {"element": "routes[].ligne_reference.geometrie_reguliere (arcs, clothoïdes : courbure0, courbure1) ou polyligne", "usage": "courbure κ(s) le long de la voie -> vitesse en courbe (R-LAT-01), point de visée", "couche": ["LAT", "LON"], "statut": "existant (courbure à dériver de la polyligne si absente)"},
    {"element": "routes[].profil_long (s, z)", "usage": "pente -> a_max(v, pente), résistance (R-VEH-01)", "couche": ["VEH"], "statut": "existant"},
    {"element": "routes[].devers", "usage": "accélération latérale effective v²/R - g·dévers (cercle de friction)", "couche": ["VEH", "LAT"], "statut": "existant"},
    {"element": "profils[].bandes[] (type, sens, usagers, largeur)", "usage": "voies autorisées par classe (bus, vélos), largeur de voie (suivi latéral)", "couche": ["STR", "LAT"], "statut": "existant"},
    {"element": "carrefours[].regime, branches[].regime, branches[].ligne_arret (type, distance_m)", "usage": "point d'arrêt, régime de priorité, position de décision (œil à 4 m au STOP)", "couche": ["TAC"], "statut": "existant (stop_a_verifier : traiter comme cédez, ARB-19)"},
    {"element": "carrefours[].trajectoires[] (mouvement, géométrie, rayon_min_m, priorite) et conflits[] (type, point, prioritaire)", "usage": "manœuvre -> t_c FR, temps d'arrivée au point de conflit, vitesse de virage", "couche": ["TAC", "LAT"], "statut": "existant (ce que ZoneGraph n'a pas)"},
    {"element": "carrefours[].anneau (giratoire)", "usage": "créneaux de giratoire (Giuffrè), vitesse dans l'anneau", "couche": ["TAC", "LAT"], "statut": "existant"},
    {"element": "carrefours[].passages_pieton[] (regime : feux, non_gere, surélevé ; position)", "usage": "cession aux piétons, plateau surélevé = ralentisseur", "couche": ["TAC"], "statut": "existant"},
    {"element": "signaux[] (code IISR, valeur, position s/t, applicabilité) et controleurs[] (cycle, phases, états)", "usage": "limites (B14), régimes (AB3a, AB4), feux (R11v) et durées du jaune", "couche": ["TAC", "PER"], "statut": "existant"},
    {"element": "objets[] / marquages[] issus de traffic_calming (OSM-TC-001 : hump, table, cushion)", "usage": "ralentisseurs (R-TAC-06)", "couche": ["TAC"], "statut": "absent comme objet dédié : proposition à l'équipe du modèle de route (type, s, longueur, hauteur) ; ne pas modifier le schéma ici"},
    {"element": "zones[] (bâti), objets[] (végétation, mobilier), ilots[].terre_plein.plantation", "usage": "occultations et ligne de vue (R-PER-03)", "couche": ["PER"], "statut": "existant"},
    {"element": "bandes[].materiau_id (assets/specs/materiaux_sol.json)", "usage": "adhérence par surface (R-VEH-03)", "couche": ["VEH"], "statut": "absent : materiaux_sol.json ne porte pas de frottement ; proposition : champ CFL ou classe d'adhérence"},
]

CORRESPONDANCE_SUMO = {
    "principe": "Deux usages : (1) export de vTypes tirés pour comparer le modèle à SUMO avec ses propres lois ; (2) pilotage de SUMO par TraCI (setSpeed, setAcceleration, setLaneChangeMode, setSpeedFactor) pour garder le réseau, les feux et les détecteurs de SUMO tout en appliquant nos décisions. Options globales : --step-length 0.1, --step-method.ballistic, sigma = 0.",
    "lignes": [
        {"parametre": "LON.vit.* (v0 par réseau)", "sumo": "speedFactor (attribut du véhicule) ou traci.vehicle.setSpeedFactor à chaque changement de réseau", "portee": "véhicule / TraCI", "transformation": "speedFactor = v0_i / VMA", "limite": "un seul facteur par véhicule sans TraCI"},
        {"parametre": "LON.MOD.T_suivi", "sumo": "tau", "portee": "vType", "transformation": "tau = T_suivi,i (IDM, EIDM)", "limite": "T contextuel (décharge) : traci.vehicle.setTau"},
        {"parametre": "LON.tiv.ecart_arret", "sumo": "minGap", "portee": "vType", "transformation": "identique", "limite": "-"},
        {"parametre": "LON.acc.demarrage_pic", "sumo": "accel", "portee": "vType", "transformation": "identique", "limite": "capacité du véhicule : speedTable + maxAccelProfile"},
        {"parametre": "LON.dec.max_courante_urbain", "sumo": "decel (et apparentDecel)", "portee": "vType", "transformation": "identique", "limite": "pour Krauss, decel est une borne dure"},
        {"parametre": "LON.dec.urgence_max_markkula", "sumo": "emergencyDecel", "portee": "vType", "transformation": "min(valeur, µg)", "limite": "pas de cinématique de Markkula"},
        {"parametre": "PER.tpr.anticipe", "sumo": "EIDM treaction ; Krauss actionStepLength", "portee": "vType", "transformation": "identique", "limite": "un seul temps par véhicule ; actionStepLength incompatible avec EIDM"},
        {"parametre": "LON.acc.jerk_confort", "sumo": "EIDM jerkmax", "portee": "vType", "transformation": "identique", "limite": "jerk des freinages de sécurité non borné dans le code"},
        {"parametre": "LON.eidm.demarrage_salles2020", "sumo": "EIDM taccmax, Mflatness, Mbegin ; startupDelay", "portee": "vType", "transformation": "calage", "limite": "-"},
        {"parametre": "PER.hdm.treiber2006", "sumo": "EIDM sigmagap, sigmaleader, tPersEstimate ; device driverstate", "portee": "vType / device", "transformation": "calage", "limite": "driverstate incompatible avec EIDM"},
        {"parametre": "LON.acc_idm.kesting2010", "sumo": "EIDM coolness", "portee": "vType", "transformation": "identique", "limite": "-"},
        {"parametre": "TAC.feu.seuil_arret_jaune", "sumo": "aucun équivalent (jmDriveAfterYellowTime = seuil de temps depuis le jaune, déterministe)", "portee": "TraCI", "transformation": "décision prise hors SUMO, consigne par setSpeed / slowDown", "limite": "non représentable dans un vType"},
        {"parametre": "TAC.creneau.*", "sumo": "jmTimegapMinor, impatience (ne reproduisent pas les créneaux FR : S3)", "portee": "vType / TraCI", "transformation": "décision hors SUMO + setSpeedMode", "limite": "non représentable dans un vType"},
        {"parametre": "TAC.stop.comportement", "sumo": "jmStopSignWait (durée minimale) ; pas d'arrêt glissé", "portee": "vType / TraCI", "transformation": "-", "limite": "modalités non représentables"},
        {"parametre": "TAC.pieton.taux_cede", "sumo": "jmCrossingGap (distance) ; jmIgnoreFoeProb (tous les antagonistes)", "portee": "vType", "transformation": "-", "limite": "probabilité de cession non représentable"},
        {"parametre": "LAT.courbe.*", "sumo": "netconvert --junctions.limit-turn-speed (5,5 m/s² pour tous)", "portee": "réseau", "transformation": "-", "limite": "pas de vitesse en courbe par conducteur ni hors carrefour"},
        {"parametre": "TAC.vdv.duree_chevauchement", "sumo": "--lanechange.duration (global) ou SL2015 maxSpeedLat (par vType)", "portee": "option / vType", "transformation": "maxSpeedLat ≈ largeur de voie / T_vdv,i", "limite": "-"},
        {"parametre": "TAC.mobil.kesting2007", "sumo": "LC2013 lcSpeedGain, lcKeepRight, lcCooperative, lcAssertive", "portee": "vType", "transformation": "pas d'équivalence directe", "limite": "règles différentes"},
        {"parametre": "VEH.* (dimensions, masse, vmax, a_max(v))", "sumo": "length, width, mass, maxSpeed, vClass ; speedTable + maxAccelProfile ; desAccelProfile", "portee": "vType", "transformation": "a_max(v) échantillonné", "limite": "-"},
        {"parametre": "VEH.ADH-*", "sumo": "device friction (réduit seulement la vitesse)", "portee": "device", "transformation": "-", "limite": "pas d'effet sur le freinage"},
        {"parametre": "POP.hetero.distraction_part_temps", "sumo": "device driverstate (awareness)", "portee": "device", "transformation": "-", "limite": "pas de paramétrage publié"},
    ],
}

# Cibles de validation : (id, métrique, scénario, [ids de paramètres cités], tolérance (convention), [ids SUMO défaut], priorité)
CIBLES = [
    ("V-01", "Vitesse libre sur artère urbaine à 50 km/h (TIV > 5 s, section droite loin des carrefours)", "route droite ≥ 2 km, arrivées aléatoires, mesure à mi-section",
     ["LON.vit.artere_centre_ville_50", "VAL.vit.histo.artere_centre_ville_50.2023_jour"], "KS non rejeté à 5 % ; moyenne ± 1 km/h ; part > VMA ± 4 points", [], "P1"),
    ("V-02", "Vitesse libre sur route à 80 km/h et autoroute à 130 km/h", "idem hors agglomération", ["LON.vit.route_2_3_voies_80", "LON.vit.autoroute_liaison_130", "VAL.vit.route_bidirectionnelle_80_vl_24h"], "idem V-01", [], "P2"),
    ("V-03", "Vitesse libre en zone 30", "rue en zone 30 sans dispositif", ["LON.vit.zone_30_be", "VAL.vit.zone_30_bruxelles"], "moyenne ± 1 km/h ; V85 ± 2 km/h", [], "P1"),
    ("V-04", "Écart jour / nuit", "V-01 de nuit", ["CTX.vit.ecart_jour_nuit"], "écart ± 1 km/h", [], "P3"),
    ("V-05", "TIV net en suivi stable, moyenne par conducteur (ville, autoroute)", "file libre de 20 véhicules, meneur à vitesse variable, suivi > 50 s à v > 10 m/s", ["LON.tiv.moyen_conducteur_urbain", "LON.tiv.moyen_conducteur_autoroute"], "quartiles ± 0,1 s", ["REF.sim.S1.krauss_pas01s", "REF.sim.S1.eidm_pas01s"], "P1"),
    ("V-06", "TIV minimal habituel (2,5e centile par conducteur)", "idem V-05", ["LON.tiv.min_conducteur_urbain", "LON.tiv.min_conducteur_autoroute", "VAL.tiv.udrive_suivi_rapproche"], "moyenne ± 0,1 s", [], "P2"),
    ("V-07", "Distribution des TIV instantanés sur autoroute", "autoroute 2x2, trafic moyen", ["VAL.tiv.population_highD", "VAL.tiv.population_NGSIM"], "médiane ± 0,15 s ; P10, P90 ± 0,3 s", [], "P3"),
    ("V-08", "Démarrage d'un véhicule seul au vert : temps pour atteindre 1 m/s, instant et valeur du pic d'accélération", "feu isolé, véhicule seul arrêté à la ligne", ["LON.eidm.demarrage_salles2020", "LON.acc.demarrage_pic"], "1 m/s en 0,8 ± 0,2 s ; pic à 2,3 ± 0,3 s ; pic moyen 2,1 ± 0,1 m/s²", [], "P1"),
    ("V-09", "Extrêmes habituels par conducteur en suivi : 97,5e centile des accélérations et 2,5e centile des décélérations", "file libre de V-05", ["LON.acc.max_suivi_urbain", "LON.acc.max_suivi_autoroute", "LON.dec.max_courante_urbain", "LON.dec.max_courante_autoroute"], "moyennes ± 0,15 m/s²", [], "P2"),
    ("V-10", "Décharge au feu : débit de saturation, temps perdu, TIV et pic d'accélération par rang", "feu isolé, file de 15 VL au rouge, 50 km/h", ["VAL.feu.saturation_fr", "VAL.feu.saturation_hcm", "VAL.tiv.file_feu", "VAL.acc.demarrage_file", "LON.eidm.demarrage_salles2020"], "1 800 ± 90 uvpd/h ; temps perdu 2 ± 0,5 s ; TIV par rang ± 0,2 s ; pic d'accélération par rang ± 0,1 m/s² et son écart-type par rang dans [0,40 ; 0,65] m/s² (Salles fig. 8b)", ["REF.sim.S2.krauss_pas1s", "REF.sim.S2.krauss_pas01s", "REF.sim.S2.eidm_pas01s"], "P1"),
    ("V-11", "Décision au jaune : P(arrêt) selon le temps à la ligne", "feu isolé, arrivées libres à 50 km/h, jaune 3 s", ["TAC.feu.seuil_arret_jaune", "VAL.feu.duree_jaune_fr"], "P(arrêt) = 0,10 ± 0,05 à 2,5 s et 0,90 ± 0,05 à 5,5 s", ["REF.sim.S2.krauss_pas01s", "REF.sim.S2.eidm_pas01s"], "P1"),
    ("V-12", "Décélération des véhicules qui s'arrêtent au jaune", "V-11", ["VAL.feu.dec_jaune_conception", "VAL.dec.ite_confortable"], "médiane ≤ 3,05 m/s² ; aucune décélération > µg", ["REF.sim.S2.krauss_pas01s"], "P2"),
    ("V-13", "Distribution des accélérations et décélérations par classe de vitesse", "trajets urbains et périurbains mixtes", ["VAL.dec.percentiles_bosetti", "VAL.acc.percentiles_bosetti", "VAL.dec.p10_inattendu"], "P5 et P95 ± 0,3 m/s²", [], "P2"),
    ("V-14", "Jerk", "tous scénarios", ["LON.acc.jerk_confort"], "P95 |jerk| ≤ 1,5 m/s³ hors urgence", ["REF.sim.S1.krauss_pas01s", "REF.sim.S1.eidm_pas01s"], "P1"),
    ("V-15", "Vitesse en courbe", "routes à 80 km/h avec courbes de 40 à 500 m ; carrefours et giratoires", ["LAT.courbe.v85_setra", "VAL.courbe.vitesse_conventionnelle_cfts", "VAL.courbe.giratoire", "LAT.courbe.alpha_deux_tiers", "LAT.courbe.alat_max_conducteur"], "V85 ± 5 km/h de la V85 Sétra (R ≥ 40 m) ; < 30 km/h dans l'anneau. ATTENTION : avec la règle Sétra × κ_i (κ normalisé au P85), la V85 Sétra est imposée PAR CONSTRUCTION ; seule une mesure de vitesses en courbe validerait la dispersion", [], "P1"),
    ("V-16", "Créneaux acceptés (créneau critique estimé par maximum de vraisemblance)", "T et carrefour en croix, cédez et STOP, 30/50/70 km/h ; giratoire à une voie", ["TAC.creneau.norme_fr", "TAC.creneau.giratoire_meta", "VAL.creneau.dispersion", "VAL.creneau.hcm_base"], "moyenne ± 0,5 s de la valeur Certu ; écart-type 0,7-1,1 s. Le 5 s du Certu (CU 2010 p. 92-93) est un paramètre de la méthode de capacité (norme), pas une estimation par maximum de vraisemblance : cible indicative. Mesure : décalage depuis l'arrêt en tête de ligne, instants au point de conflit", ["REF.sim.S3.cedez.krauss_pas01s", "REF.sim.S3.stop.krauss_pas01s", "REF.sim.S3.sensibilite.impatience_0.5"], "P1"),
    ("V-17", "Comportement au STOP", "V-16 (STOP)", ["TAC.stop.comportement"], "parts ± 5 points ; la modalité est tirée dans la loi de Vaughan (loi d'entrée : contrôle de mise en œuvre) ; avec n ≈ 125 arrivées libres, l'intervalle de confiance à 95 % vaut ± 8,5 points ; Vaughan décrit un STOP sur toutes les branches (pertinence faible pour un STOP secondaire)", ["REF.sim.S3.stop.krauss_pas01s"], "P3"),
    ("V-18", "Cession aux piétons et profil d'approche", "passage non géré, piétons au bord", ["TAC.pieton.taux_cede", "TAC.pieton.approche", "VAL.pieton.distance_regle_cu"], "taux ± 5 points ; vitesse minimale ± 0,5 m/s", [], "P2"),
    ("V-19", "Vitesse au franchissement des ralentisseurs", "zone 30 avec coussins et plateaux", ["TAC.ralent.vitesse_franchissement", "VAL.ralent.objectif_conception"], "mesure 10-20 m après le dispositif : moyenne dans l'enveloppe des moyennes régionales belges (27,6-34,9 km/h) et ± 3 km/h de la moyenne nationale (34,0) ; V85 ± 4 km/h (41,5). Confiance faible : dispositifs mêlés (chicanes, coussins, plateaux), effet non significatif en Flandre ; la loi d'entrée vient de la même mesure", [], "P2"),
    ("V-20", "Changements de voie : durée, distances d'insertion", "2x2 voies chargée", ["TAC.vdv.duree_chevauchement", "TAC.vdv.insertion_devant"], "moyenne ± 0,5 s", [], "P3"),
    ("V-21", "Croissance des fluctuations de vitesse le long d'une file", "file de 25 véhicules à 50 km/h, meneur humain simulé", ["VAL.file.jiang2014", "VAL.file.sugiyama2008"], "écart-type par rang à ± 0,2 m/s ; croissance concave", ["REF.sim.S1.krauss_pas01s", "REF.sim.S1.eidm_pas01s"], "P2"),
    ("V-22", "Distances d'arrêt d'urgence face à la norme française", "obstacle surgissant à 30, 50, 70, 90 km/h", ["PER.tpr.surprise_obstacle", "LON.dec.urgence_equivalente", "VAL.dec.norme_arret_mouille", "VAL.tpr.norme_fr_route"], "la distance normative couvre ≥ 90 % des arrêts simulés (Cerema 2018 p. 11, γv corrigé : 46,4 m à 50 km/h, 78,8 m à 70 km/h)", [], "P2"),
    ("V-23", "Performances des véhicules tirés", "essais virtuels 0-100, 60-100, 80-120, 100-0 km/h", ["VEH.VP-DYN-ERREURS", "VEH.ADH-MESURE-ADAC-100-0", "VEH.REG-R13H-TYPE0"], "erreurs ≤ celles du volet 01 (7,7 / 8,4 / 4,0 %) ; MFDD ≥ 6,43 m/s². Les distances 100-0 km/h tirées avec la loi ADAC reproduisent l'ADAC PAR CONSTRUCTION ; avec la loi du parc (Greibe) elles sont plus longues (attendu)", [], "P1"),
    ("V-24", "Collisions en conditions nominales", "tous scénarios sans défaillance injectée ; S1 sur 5 graines × 200 files", [], "0 collision primaire (convention) ; les collisions secondaires (meneur déjà accidenté) sont comptées à part", [], "P1"),
    ("V-25", "Distribution conjointe (type WOSAC) : vitesses, accélérations, distance au plus proche, TTC", "scénarios S1-S3 et scènes de Meylan", ["REF.sim.S1.krauss_pas1s"], "méthode : vraisemblance des distributions (Montali 2023, volet 03)", [], "P3"),
]

LACUNES_CONCEPTION = [
    "Créneaux critiques, STOP, cession aux piétons, vitesse aux coussins, zone de dilemme au jaune, TIV en suivi : aucune mesure française publiée (volet 02) ; à relever à Meylan en priorité.",
    "Taux de franchissement au rouge en France : aucune donnée lue ; il conditionne l'option H-11.",
    "Commande latérale humaine : temps de visée, vitesse de braquage, errance latérale non sourcés (H-12).",
    "Bicyclette dynamique : rigidités de dérive, inertie de lacet et répartition des masses des VP non collectées (volet 01).",
    "Champ de vision et stratégie du regard (où le conducteur regarde, combien de temps) : non sourcés ; v0.1 = ligne de vue géométrique.",
    "Durée des épisodes de distraction : non sourcée (H-08).",
    "Durée minimale d'arrêt au STOP et effet du temps d'attente sur l'acceptation de créneau : non sourcés.",
    "Vitesse et comportement en zone de rencontre : aucune loi (CR-11).",
    "Dispersion des vitesses en courbe en France : seule la V85 Sétra est disponible (H-05).",
    "Corrélation style du conducteur / puissance du véhicule : non sourcée (H-02).",
    "Deux-roues motorisés : ni véhicule (volet 01) ni comportement (volet 02).",
    "Pluie : adaptation de la vitesse et des distances par les conducteurs non sourcée ; seule l'adhérence est décrite (volet 01).",
    "Poids lourds et bus : k et a_lancement non calés (volet 01) ; écart-type des vitesses PL dérivé de taux de respect (LON.MOD.vit_pl_*).",
    "Ralentisseurs : pas d'objet dédié dans le modèle de route (proposition à l'équipe concernée).",
    "Adhérence par matériau : pas de champ de frottement dans materiaux_sol.json (proposition).",
    "Vitesses libres françaises à véhicules libres (filtre par véhicule) : absentes ; la loi ONISR est tronquée sous P5 par convention (H-04).",
    "Part de regards hors route par événement (France) : absente ; proxy UDRIVE (H-18).",
    "Écart à l'arrêt en file (s0) : aucune mesure directe ; loi tirée de calages IDM (Kesting & Treiber 2008, Zhu 2018).",
    "Capacité de freinage du parc en circulation : estimée d'après 2 voitures de 2006 (Greibe 2007) ; aucune mesure française.",
]


# ------------------------------------------------------------------------------------ assemblage
def main():
    J01, J02, J02P, J03 = charger(F01), charger(F02), charger(F02P), charger(F03)
    C = charger(F04C)
    idx02 = {p["id"]: p for p in J02["parametres"]}
    params = []
    # volet 02
    for p in J02["parametres"]:
        c = couche_v02(p)
        params.append(entree("02_Conducteurs", str(F02), p, c, p.get("role"), source_v02(p, J02["sources"])))
    # volet 01
    for chemin, p in parametres_v01(J01):
        c, role = role_v01(chemin, p)
        e = entree("01_Vehicules", str(F01), p, c, role, source_v01(p, J01["sources"]))
        e["origine"]["chemin"] = chemin
        params.append(e)
    # volet 03
    for p in J03["entrees"]:
        c = couche_v03(p)
        if c is None:
            continue
        role = {"VAL": "reference_validation", "REF": "comparaison"}.get(c, "modele_litterature")
        params.append(entree("03_Modeles_Existants", str(F03), p, c, role, source_v03(p)))
    # volet 04
    conc = entrees_conception(C, idx02)
    # R0 : vérification recopiée de C3
    for ligne in C["C3_courbes"]["lignes"]:
        if ligne["R_m"] == 40:
            for e in conc:
                if e["id"] == "LAT.MOD.R0_courbe":
                    e["parametres"]["verification"] = {"R_m": 40, "bosetti_p85_kmh": ligne["bosetti_frontiere_kmh"]["p85"],
                                                       "setra_v85_Vlim102_kmh": ligne["setra_V85_kmh"]["Vlim_102"]}
    for e in conc:
        e["origine"] = {"volet": "04_Conception", "fichier": str(Path(__file__).resolve()), "id": e["id"],
                        "nature": e["nature"], "confiance": e["confiance"]}
    params += conc

    index = {e["id"]: e for e in params}
    if len(index) != len(params):
        raise SystemExit("identifiants en double")

    # cibles de validation : valeurs recopiées des paramètres cités
    cibles = []
    for cid, met, scen, refs, tol, sumo, prio in CIBLES:
        manquants = [r for r in refs + sumo if r not in index]
        if manquants:
            raise SystemExit(f"{cid} : paramètres inconnus {manquants}")
        cibles.append({"id": cid, "metrique": met, "scenario": scen, "priorite": prio,
                       "references": [{"id": r, "valeurs": index[r]["parametres"], "unite": index[r]["unite"],
                                       "source": {k: index[r]["source"].get(k) for k in ("doc", "page", "annee")},
                                       "nature": index[r]["nature"], "confiance": index[r]["confiance"]} for r in refs],
                       "tolerance_proposee": tol, "nature_tolerance": "convention de validation (à discuter)",
                       "sumo_par_defaut": [{"id": s, "resultats": index[s]["parametres"]} for s in sumo]})
    # règles : contrôle des références
    for r in REGLES:
        manquants = [x for x in r["parametres"] if x not in index]
        if manquants:
            raise SystemExit(f"{r['id']} : paramètres inconnus {manquants}")

    # facteurs latents et profils (volet 02)
    facteurs = {"facteurs": copy.deepcopy(J02P["facteurs_latents"]), "charges_par_groupe": copy.deepcopy(J02P["charges_par_groupe"]),
                "groupe_ajoute_v04": {"politesse": {"facteur": "style", "charge": -0.4, "parametres": ["MOBIL p_i"], "nature": "hypothese",
                                                     "justification": "H-09 (même signe et même valeur que le groupe vdv)"}},
                "rattachements_v04": {"VAL.dec.max_conducteur_bosetti": {"groupe": "dec_courante", "usage": "sommet c (freinage) du triangle g-g",
                                                                         "nature": "hypothese", "justification": "paramètre sans groupe au volet 02 ; même facteur et même charge que la décélération habituelle (H-01)"}},
                "methode": J02P["meta"].get("methode"), "source": "D:/DocRoute/17_Modele_Vehicules_Conducteurs/02_Conducteurs/profils_conducteurs.json"}
    profils = []
    for pr in J02P["profils"]:
        profils.append({k: copy.deepcopy(v) for k, v in pr.items() if k not in ("valeurs", "correspondance_sumo")})

    sources = {f"V01:{k}": v for k, v in J01["sources"].items()}
    sources.update({f"V02:{k}": v for k, v in J02["sources"].items()})
    sources["V03"] = {"titre": "Volet 03 — état de l'art (sources détaillées dans 03_Modeles_Existants/sources/SOURCES.md)",
                      "fichier": str(F03)}
    sources["V04:COHERENCE"] = {"titre": "Calculs de cohérence de la conception", "fichier": str(F04C),
                                "script": "recon/trafic/conception/verifier_coherence.py", "annee": 2026}

    compte = {}
    for e in params:
        compte.setdefault(e["couche"], 0)
        compte[e["couche"]] += 1
    natures = {}
    for e in params:
        natures[e["nature"]] = natures.get(e["nature"], 0) + 1

    sortie = {
        "meta": {
            "titre": "Modèle conducteur + véhicule — paramètres et distributions retenus (conception v0.1)",
            "version": "0.1.0", "date": "2026-10-17",
            "document_conception": DOC_CONCEPTION,
            "generateur": "recon/trafic/conception/construire_parametres_modele.py",
            "forme_parametre": "{id, couche, role, grandeur, population, loi, parametres, unite, conditions, nature, source{doc, page, annee, cle, catalogue}, confiance, usage, origine{volet, fichier, id}, tirage?}",
            "regle": "valeurs recopiées des volets sans ressaisie ; le test test_parametres_modele.py vérifie l'identité",
            "entrees": {"01": {"fichier": str(F01), "sha256": empreinte(F01)}, "02": {"fichier": str(F02), "sha256": empreinte(F02)},
                        "02_profils": {"fichier": str(F02P), "sha256": empreinte(F02P)}, "03": {"fichier": str(F03), "sha256": empreinte(F03)},
                        "04_coherence": {"fichier": str(F04C), "sha256": empreinte(F04C)}},
            "couches": COUCHES,
            "natures": sorted(natures.items()),
            "effectifs_par_couche": compte,
            "conventions": {"unites": "SI sauf mention (vitesses publiées en km/h)", "gev": "convention MATLAB / Huang : k = forme ; scipy genextreme(c = -k)",
                            "lois": "voir recon/trafic/conducteurs/lois.py"},
            "pas_de_temps": {"pas_s": 0.1, "integration": "balistique", "justification": "E2 du volet 03 (S1, S2)"},
        },
        "architecture": ARCHITECTURE,
        "regles": REGLES,
        "hypotheses": HYPOTHESES,
        "facteurs_latents": facteurs,
        "profils": profils,
        "correspondance_reseaux": CORRESPONDANCE_RESEAUX,
        "lecture_modele_route": LECTURE_MODELE_ROUTE,
        "correspondance_sumo": CORRESPONDANCE_SUMO,
        "validation": {"cibles": cibles,
                       "methode": "chaque cible est mesurée sur une population tirée (≥ 1 000 conducteurs) ; les distributions sont comparées par KS ou par quantiles ; les colonnes « sumo_par_defaut » rappellent ce que donne SUMO 1.27.1 avec ses valeurs par défaut (volet 03)"},
        "lacunes": {"conception": LACUNES_CONCEPTION, "vehicules_volet01": copy.deepcopy(J01.get("lacunes", [])),
                    "conducteurs_volet02": "voir CONDUCTEURS.md § 7", "modeles_volet03": "voir MODELES_EXISTANTS.md § 13"},
        "sources": sources,
        "parametres": params,
    }
    SORTIE.write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{SORTIE} : {len(params)} paramètres ({compte}) ; {len(cibles)} cibles ; {len(REGLES)} règles ; {len(HYPOTHESES)} hypothèses")
    print("natures :", sorted(natures.items()))


if __name__ == "__main__":
    main()
