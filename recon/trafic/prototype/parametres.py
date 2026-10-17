"""Accès aux paramètres du modèle « conducteur + véhicule » (prototype v0.2).

Point d'entrée : assets/specs/trafic/parametres_modele.json (conception, volet 04). Les valeurs sourcées sont
LUES dans ce fichier (entrées « ref » de DEFAUTS_PROTOTYPE) : aucune loi ni valeur publiée n'est recopiée ici.

Les valeurs propres au prototype sont de trois natures, chacune déclarée ci-dessous avec sa justification :
  calage      valeur ajustée par calage.py sur une cible citée (la valeur calée est relue dans
              assets/specs/trafic/parametres_prototype.json) ;
  convention  choix de modélisation ou de scénario sans source (seuils numériques, positions, durées) ;
  hypothese   hypothèse de comportement non sourcée (H-xx de la conception).
assets/specs/trafic/parametres_prototype.json est écrit par calage.py (ecrire_parametres_prototype) ; seules
les entrées « calage » y sont relues, les conventions et les références restent celles du code et du modèle.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
TRAFIC = ICI.parent
DEPOT = TRAFIC.parents[1]
for sous in ("conducteurs", "vehicules", "etat_art_sumo"):
    p = str(TRAFIC / sous)
    if p not in sys.path:
        sys.path.append(p)
import lois  # noqa: E402  (recon/trafic/conducteurs/lois.py)

F_MODELE = DEPOT / "assets" / "specs" / "trafic" / "parametres_modele.json"
F_VEHICULES = DEPOT / "assets" / "specs" / "trafic" / "vehicules_parametres.json"
F_PROTOTYPE = DEPOT / "assets" / "specs" / "trafic" / "parametres_prototype.json"
DOC17 = Path("D:/DocRoute/17_Modele_Vehicules_Conducteurs")
DOC05 = DOC17 / "05_Prototype"
TMP05 = DOC17 / "tmp" / "05"

G = 9.81


def _tpreview_ind(p):
    """Horizon de prévisualisation calé sur inD (approche d'un passage piéton sans interaction) :
    le freinage commence à LVi = 39,81 m pour Vi = 8,53 m/s, soit t = LVi / Vi."""
    s = p["sans_interaction"]
    return round(s["LVi"] / s["Vi"], 3)


# Entrées : {"valeur"} pour une valeur propre au prototype, ou {"ref": (id, chemin ou fonction)} pour une valeur
# lue dans parametres_modele.json. « nature » : calage, convention, hypothese, ou nature de la source (ref).
DEFAUTS_PROTOTYPE = {
    # ---------------------------------------------------------------- simulation
    "pas_s": {"valeur": 0.1, "nature": "convention", "source": "conception § 2.2 (exigence E2 du volet 03)"},
    "collision_traitement": {"valeur": "impulsion", "nature": "convention",
                             "source": "v0.2 : choc parfaitement inélastique (quantité de mouvement conservée, masses du volet 01), puis les deux véhicules accidentés freinent à d_max jusqu'à l'arrêt ; collisions primaires (meneur intact) et secondaires comptées à part. v0.1 : recul et vitesse ramenée à celle du meneur (décélération infinie non perçue, d'où des chocs en chaîne)"},
    "parc_vehicules": {"valeur": "circulation", "nature": "convention",
                       "source": "population.py du volet 01 : familles de motorisation ramenées au parc en circulation (SDES 2026), d_max du parc (Greibe 2007)"},
    # ---------------------------------------------------------------- poursuite (références)
    "idm_delta": {"ref": ("LON.idm.treiber2000", ["delta"])},
    "cah_c": {"ref": ("LON.acc_idm.kesting2010", ["voiture", "c"])},
    "epsilon_acc": {"ref": ("REF.sumo.eidm.epsilonacc", ["valeur"])},
    "jerk_confort": {"ref": ("LON.acc.jerk_confort", ["valeur"])},
    "tpreview_s": {"ref": ("TAC.pieton.approche", _tpreview_ind), "nature": "calage",
                   "source_calage": "calé sur inD (Gankhuyag 2023 tab. 1, approche d'un passage piéton sans interaction : début du freinage à 39,81 m pour 8,53 m/s) ; v0.1 : 4 s (défaut EIDM)"},
    "demarrage_taccmax": {"ref": ("REF.sumo.eidm.taccmax", ["valeur"])},
    "demarrage_Mflatness": {"ref": ("REF.sumo.eidm.Mflatness", ["valeur"])},
    "demarrage_Mbegin": {"ref": ("REF.sumo.eidm.Mbegin", ["valeur"])},
    "jerk_borne_au_demarrage": {"valeur": False, "nature": "convention",
                                "source": "P-02 : la phase de démarrage suit le facteur EIDM (cible V-08) ; 1 m/s en 0,8 s exige un jerk ≥ 3 m/s³"},
    "duree_demarrage_s": {"valeur": 6.0, "nature": "convention", "source": "P-02 : durée de la phase de démarrage exemptée du jerk de confort"},
    "fenetre_facteur_demarrage_s": {"valeur": 30.0, "nature": "convention", "source": "durée d'application du facteur de démarrage EIDM après un départ"},
    "facteur_a_decharge": {"valeur": 1.0, "nature": "calage",
                           "source": "H-14 : facteur sur a en décharge de file de feu ; calé sur Salles 2020 fig. 8 (pic du rang 1 : 2,67 m/s²)"},
    "reaction_depart_feu": {"valeur": "vert", "nature": "convention",
                            "source": "conception § 6.2 (« le conducteur voit aussi le feu ») : chacun peut partir un TPR anticipé après le vert, dès que l'écart s'ouvre ; variante « meneur »"},
    "T_decharge_rapport": {"ref": ("LON.MOD.T_decharge_rapport", ["depart_calage"])},
    "T_min_intervalle_action": {"valeur": True, "nature": "convention",
                                "source": "H-17 : T_i ≥ Δ_a,i (TPR anticipé, intervalle entre deux points d'action) ; stabilité de la file (v0.1 : T < Δ_a pour 35 % des conducteurs en décharge)"},
    "fin_decharge_aval_m": {"valeur": 50.0, "nature": "convention", "source": "P-05 : fin du contexte de décharge 50 m après la ligne de feu"},
    "fin_decharge_frac_v0": {"valeur": 0.8, "nature": "convention", "source": "P-05 : fin du contexte de décharge à 0,8 v0"},
    "relaxation_passive": {"valeur": True, "nature": "convention",
                           "source": "P-05 : après la décharge, T rejoint T_suivi sans dépasser l'écart temporel observé"},
    "T_relaxation_taux_s-1": {"valeur": 0.15, "nature": "convention",
                              "source": "forme du modèle 2D de Jiang 2014 (conception § 6.2, H-03) ; taux non sourcé, à caler"},
    "T_v_ref": {"valeur": "mediane_reseau", "nature": "convention",
                "source": "T_suivi = TIV_moyen - s0 / v_ref avec v_ref = médiane de la loi de vitesse désirée du réseau (v0.1 : 12 m/s pour tous, y compris hors agglomération)"},
    "d_en_file_m": {"valeur": 15.0, "nature": "convention", "source": "un véhicule arrêté à moins de 15 m de son meneur ou de la ligne est « en file » (contexte de décharge)"},
    # ---------------------------------------------------------------- perception
    "hdm_Vs": {"ref": ("PER.hdm.treiber2006", ["Vs_erreur_relative_distance"])},
    "hdm_rc_s-1": {"ref": ("PER.hdm.treiber2006", ["rc_erreur_inverse_TTC_par_s"])},
    "hdm_tau_s": {"ref": ("PER.hdm.treiber2006", ["tau_correlation_erreurs_s"])},
    "markkula_seuil_looming_s-1": {"valeur": 0.2, "nature": "mesure",
                                   "source": "Markkula 2016 éq. 2 : t0,2 = premier instant où τ⁻¹ ≥ 0,2 s⁻¹ (définition du modèle publié, PER.tpr.markkula.alphaB_*)"},
    "markkula_kB": {"ref": ("PER.tpr.markkula.kB", [])},
    "markkula_jB_plafond_ms3": {"valeur": 8.0, "nature": "estimation",
                                "source": "Markkula 2016 annexe B.3 (plafond proposé « par exemple » jB ≤ 8 m/s³)"},
    "distraction_part_temps_FR": {"ref": ("POP.hetero.distraction_part_temps", ["France"]), "nature": "hypothese",
                                  "source_usage": "H-18 : part du temps en tâche secondaire (UDRIVE D41.1 p. 5, conversations comprises) prise comme probabilité moyenne d'avoir les yeux hors de la menace : proxy, pas une mesure de regards"},
    "distraction_charge_vigilance": {"valeur": 0.5, "nature": "hypothese",
                                     "source": "H-18 : la probabilité d'être distrait croît quand la vigilance baisse ; charge 0,5 (même valeur absolue que le groupe TPR du volet 02)"},
    "feux_stop_seuil_ms2": {"valeur": 1.3, "nature": "convention",
                            "source": "seuil de détection des feux stop par le suiveur. Repris par analogie du R13-H § 5.2.22.2 (JO L 2026/502 p. 21), qui vise le freinage automatique ou régénératif ; pour le conducteur, le § 5.2.22.1 allume les feux à toute action sur le frein de service (requalifié le 17/10/2026 : ce n'est pas une norme)"},
    "h15_v_meneur_lent_ms": {"valeur": 5.0, "nature": "convention", "source": "H-15 : un freinage d'un meneur à moins de 5 m/s n'est pas une surprise"},
    "h15_d_ligne_m": {"valeur": 50.0, "nature": "convention", "source": "H-15 : ligne d'arrêt visible à moins de 50 m devant le meneur"},
    "h15_d_file_m": {"valeur": 60.0, "nature": "convention", "source": "H-15 : véhicule arrêté ou freinant à moins de 60 m devant le meneur (anticipation sur deux véhicules, n_a du HDM)"},
    "h15_v_arrete_ms": {"valeur": 2.0, "nature": "convention", "source": "H-15 : véhicule devant le meneur considéré arrêté sous 2 m/s"},
    # ---------------------------------------------------------------- urgence
    "marge_urgence_frac_s0": {"valeur": 0.5, "nature": "convention", "source": "décélération requise calculée avec une marge de 0,5 s0 derrière le meneur"},
    # ---------------------------------------------------------------- feux, STOP, créneaux
    "arret_ligne_feu_m": {"ref": ("REF.sumo.jm.jmStoplineGap", ["valeur"])},
    "arret_ligne_stop_m": {"ref": ("REF.sumo.jm.jmStoplineGapMinor", ["valeur"])},
    "point_decision_stop_m": {"valeur": 4.0, "nature": "norme",
                              "source": "Certu Carrefours urbains 2010 p. 97 : œil à 4 m de la ligne au STOP (95 % des conducteurs)"},
    "recul_oeil_avant_m": {"valeur": 2.0, "nature": "convention",
                           "source": "distance de l'œil du conducteur à l'avant du véhicule (ordre de grandeur, non sourcé) : l'avant est à 4 - 2 = 2 m de la ligne au point de décision (v0.1 : l'avant à 4 m)"},
    "stop_v_arret_ms": {"valeur": 0.3, "nature": "convention", "source": "P-11 : arrêt au STOP reconnu sous 0,3 m/s à moins de 2 m de la ligne"},
    "stop_d_arret_m": {"valeur": 2.0, "nature": "convention", "source": "P-11"},
    "stop_zone_vmin_m": {"valeur": 3.0, "nature": "convention", "source": "zone de 3 m avant la ligne où la vitesse minimale est relevée (méthode du volet 03)"},
    "stop_frac_b_decision": {"valeur": 0.5, "nature": "convention", "source": "P-11 : un conducteur en mouvement décide d'assez loin pour s'arrêter à 0,5 b_i"},
    "stop_portee_m": {"valeur": 80.0, "nature": "convention", "source": "distance à la ligne à partir de laquelle la logique STOP est active"},
    "creneau_TAD_50_s": {"ref": ("TAC.creneau.norme_fr", ["insertion_double_sens_TAD", "50"])},
    "h10_horizon_s": {"valeur": 15.0, "nature": "convention", "source": "H-10 : horizon de prédiction de la manœuvre d'insertion"},
    "h10_d_apres_conflit_m": {"valeur": 20.0, "nature": "convention", "source": "H-10 : prédiction arrêtée 20 m après le point de conflit"},
    "h10_prioritaire_generique": {"valeur": True, "nature": "convention",
                                  "source": "H-10 : le non-prioritaire prédit la réaction d'un prioritaire « médian » (médianes de la population : v0, T, s0, a, b), pas les paramètres privés du prioritaire réel (v0.1)"},
    # ---------------------------------------------------------------- vitesses, courbes
    "R0_courbe_m": {"ref": ("LAT.MOD.R0_courbe", ["valeur"])},
    "v0_quantile_min": {"valeur": 0.05, "nature": "convention",
                        "source": "H-04 : la loi ONISR contient des véhicules contraints (pas de filtre par véhicule) ; sa queue sous le 5e centile est retirée (tirage dans [P5 ; 1]). Sensibilité publiée au rapport"},
    "correlation_intra_groupe": {"valeur": 0.5, "nature": "hypothese",
                                 "source": "H-01 complétée : corrélation des résidus propres de deux paramètres d'un même groupe de la copule (v0.1 : 1, rangs identiques, ce qu'aucune source n'appuie)"},
    # ---------------------------------------------------------------- seuils numériques
    "vitesse_arret_ms": {"valeur": 0.05, "nature": "convention", "source": "seuil numérique d'arrêt"},
    "seuil_depart_ms2": {"valeur": 0.1, "nature": "convention", "source": "seuil numérique : la contrainte se relâche"},
}


def _resoudre(ix: dict, ref):
    pid, chemin = ref
    par = ix[pid]["parametres"]
    if callable(chemin):
        return chemin(par)
    v = par
    for k in chemin:
        v = v[k]
    return v


class Parametres:
    """Index des paramètres de parametres_modele.json et application des lois sourcées."""

    def __init__(self, chemin: Path = F_MODELE, chemin_proto: Path | None = F_PROTOTYPE):
        with open(chemin, encoding="utf-8") as f:
            self.J = json.load(f)
        self.ix = {p["id"]: p for p in self.J["parametres"]}
        self.proto = {}
        for k, e in DEFAUTS_PROTOTYPE.items():
            d = dict(e)
            if "ref" in e:
                pid = e["ref"][0]
                src = self.ix[pid]["source"]
                d["valeur"] = _resoudre(self.ix, e["ref"])
                d.setdefault("nature", self.ix[pid].get("nature", "mesure"))
                chem = e["ref"][1] if not callable(e["ref"][1]) else [e["ref"][1].__name__]
                d["source"] = (f"parametres_modele.json → {pid} {chem} ({src.get('doc', '')}, {src.get('page', '')}, {src.get('annee', '')})"
                               + (f" ; {e['source_calage']}" if "source_calage" in e else "")
                               + (f" ; {e['source_usage']}" if "source_usage" in e else ""))
            self.proto[k] = d
        if chemin_proto is not None and Path(chemin_proto).exists():
            with open(chemin_proto, encoding="utf-8") as f:
                jp = json.load(f)
            for e in jp.get("parametres", []):
                # seuls les calages sont relus : conventions et références restent celles du code et du modèle
                if e["id"] in self.proto and e.get("nature") == "calage" and self.proto[e["id"]].get("nature") != "convention":
                    self.proto[e["id"]]["valeur"] = e["parametres"]["valeur"]
                    self.proto[e["id"]]["nature"] = "calage"
                    self.proto[e["id"]]["source"] = e["source"]["doc"]

    # ------------------------------------------------------------------ accès
    def p(self, pid: str) -> dict:
        return self.ix[pid]

    def par(self, pid: str) -> dict:
        return self.ix[pid]["parametres"]

    def v(self, cle: str):
        """Valeur d'un paramètre propre au prototype (ou lue dans le modèle)."""
        return self.proto[cle]["valeur"]

    def quantile(self, pid: str, u):
        p = self.ix[pid]
        return lois.tirer(p["loi"], p["parametres"], u)

    def mediane(self, pid: str) -> float:
        import numpy as np
        return float(np.asarray(self.quantile(pid, [0.5])).ravel()[0])

    # ------------------------------------------------------------------ copule
    def groupes(self) -> dict:
        """{groupe: {facteur, charge, ids}} d'après les champs « tirage » et les rattachements v04."""
        g: dict = {}
        for p in self.J["parametres"]:
            t = p.get("tirage")
            if not t or "facteur" not in t or "charge" not in t:
                continue
            e = g.setdefault(t["groupe"], {"facteur": t["facteur"], "charge": t["charge"], "ids": []})
            if e["facteur"] != t["facteur"] or abs(e["charge"] - t["charge"]) > 1e-12:
                raise ValueError(f"charges incohérentes dans le groupe {t['groupe']}")
            e["ids"].append(p["id"])
        for pid, r in self.J["facteurs_latents"].get("rattachements_v04", {}).items():
            g[r["groupe"]]["ids"].append(pid)
        for nom, r in self.J["facteurs_latents"].get("groupe_ajoute_v04", {}).items():
            g.setdefault(nom, {"facteur": r["facteur"], "charge": r["charge"], "ids": []})
        return {k: g[k] for k in sorted(g)}

    def reseau(self, cle: str) -> dict:
        """Loi de vitesse désirée d'un réseau (clé du type « artere_centre_ville_50 »)."""
        for pid in (f"LON.vit.{cle}", f"VAL.vit.{cle}", f"LON.MOD.vit_{cle}"):
            if pid in self.ix:
                return self.ix[pid]
        raise KeyError(cle)


def ecrire_parametres_prototype(P: Parametres, calages: dict, chemin: Path = F_PROTOTYPE) -> None:
    """Écrit parametres_prototype.json (forme machine du projet) avec les valeurs courantes et les calages."""
    entrees = []
    for cle, e in P.proto.items():
        c = calages.get(cle, {})
        val = e["valeur"]
        entrees.append({
            "id": cle,
            "grandeur": c.get("grandeur", cle),
            "population": c.get("population", "conducteurs VL (prototype)"),
            "loi": "constante",
            "parametres": {"valeur": val},
            "unite": c.get("unite", ""),
            "conditions": c.get("conditions", ""),
            "nature": e["nature"],
            "reference_modele": list(DEFAUTS_PROTOTYPE[cle]["ref"][:1]) if "ref" in DEFAUTS_PROTOTYPE[cle] else None,
            "source": {"doc": e["source"], "page": c.get("page", ""), "annee": c.get("annee", 2026)},
            "confiance": c.get("confiance", "faible" if e["nature"] in ("calage", "convention", "hypothese") else "moyenne"),
        })
    doc = {"meta": {"titre": "Paramètres propres au prototype du modèle conducteur + véhicule (v0.2)",
                    "generateur": "recon/trafic/prototype/calage.py",
                    "entree": str(F_MODELE),
                    "note": ("calages, conventions et hypothèses du prototype ; les entrées avec « reference_modele » sont lues dans "
                             "parametres_modele.json (recopiées ici pour mémoire seulement) ; seules les entrées « calage » sont relues "
                             "par le code")},
           "parametres": entrees}
    chemin.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
