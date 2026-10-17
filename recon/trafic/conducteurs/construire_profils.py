"""Construit profils_conducteurs.json : structure de corrélation (facteurs latents) et profils types.

Les profils de style (prudent, moyen, pressé, agressif) sont des TRANCHES de la population continue
du facteur « style » S ~ N(0,1) ; leur poids est la masse de probabilité de la tranche et leur
valeur représentative la moyenne conditionnelle de S dans la tranche. Les profils d'attribut
(novice, senior, distrait, PL, bus, cyclistes) modifient la population de base à partir de valeurs
sourcées (âge, réglementation, véhicule).

Pour chaque profil et chaque paramètre tiré, on publie la médiane et les centiles 10/90 conditionnels.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys

from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modele_conducteurs as mc  # noqa: E402

phi, Phi = stats.norm.pdf, stats.norm.cdf

JUSTIF = {
    "vitesse": ("style", "Hypothèse. Appuis qualitatifs : UDRIVE D41.1 tab. 3.4 (les excédants ont plus de traits négatifs et déclarent rouler vite) ; Bosetti 2014 tab. 6 (l'identité du conducteur explique la vitesse en courbe). Charge 0,6 choisie, à calibrer."),
    "tiv_moyen": ("style", "Hypothèse : les conducteurs rapides suivent de plus près. Aucune corrélation vitesse-TIV mesurée n'a été lue (lacune)."),
    "tiv_min": ("style", "Hypothèse, même sens que tiv_moyen."),
    "acc": ("style", "Bosetti 2014 tab. 6 : l'accélération longitudinale maximale dépend du conducteur et de l'expérience (p = 0,02-0,03). Valeur 0,5 : hypothèse."),
    "dec_courante": ("style", "Hypothèse modérée (0,4) : freinages habituels plus francs chez les conducteurs dynamiques ; Bosetti : effet conducteur non significatif sur le freinage maximal c."),
    "dec_urgence": ("style", "Hypothèse faible (0,2) : Markkula 2016 montre que le freinage d'urgence dépend surtout de la cinématique de la situation."),
    "courbe": ("style", "Bosetti 2014 tab. 6 : α (loi des deux tiers) et a_lat dépendent fortement du conducteur (p < 1e-5) ; 0,6 : hypothèse."),
    "ecart_arret": ("style", "Hypothèse faible (-0,3)."),
    "jaune": ("style", "Hypothèse (0,4) : les conducteurs dynamiques passent plus souvent à l'orange (seuil de TTL plus élevé). Non mesuré en France."),
    "creneau": ("style", "Hypothèse (-0,5) : créneaux acceptés plus courts chez les conducteurs dynamiques. Non mesuré (lacune)."),
    "suivi": ("style", "Hypothèse (-0,4)."),
    "stop": ("style", "Hypothèse (0,4) : modalités ordonnées arrêt complet → glissé → pas d'arrêt ; UDRIVE : lien entre excès de vitesse et déviance déclarée."),
    "stop_vitesse": ("style", "Hypothèse (0,4)."),
    "ralentisseur": ("style", "Hypothèse (0,5), cohérente avec la vitesse libre."),
    "pieton": ("style", "Hypothèse (0,4) : u élevé = ne cède pas."),
    "vdv": ("style", "Hypothèse (-0,4) : changements de voie plus brefs chez les conducteurs dynamiques."),
    "tpr": ("vigilance", "Hypothèse (-0,5) : un conducteur vif l'est dans toutes les situations ; les 4 TPR partagent le même rang. NCHRP 400 : pas d'effet d'âge sur l'objet inattendu."),
    "velo_vitesse": ("style", "Hypothèse (0,5)."),
    "velo_acc": ("style", "Hypothèse (0,5)."),
}

# tranches du facteur style
TRANCHES = [
    ("prudent", "Conducteur prudent", -math.inf, -0.674),
    ("moyen", "Conducteur moyen", -0.674, 0.674),
    ("presse", "Conducteur pressé / dynamique", 0.674, 1.5),
    ("agressif", "Conducteur agressif (minorité)", 1.5, math.inf),
]


def tranche(a, b):
    pa = Phi(a) if a != -math.inf else 0.0
    pb = Phi(b) if b != math.inf else 1.0
    fa = phi(a) if a != -math.inf else 0.0
    fb = phi(b) if b != math.inf else 0.0
    poids = pb - pa
    moy = (fa - fb) / poids
    return poids, moy


def valeurs_profil(params, grp, S, V, idx, modif=None):
    """Médiane et P10/P90 conditionnels de chaque paramètre tiré pour (S, V)."""
    res = {}
    for nom, g in grp.items():
        f = S if g["facteur"] == "style" else V
        for pid in g["ids"]:
            p = idx[pid]
            lam = g["charge"]
            sd = math.sqrt(1 - lam * lam)
            if p["loi"] in ("categorielle", "bernoulli"):
                # probabilités conditionnelles des modalités sachant le facteur
                if p["loi"] == "bernoulli":
                    mods, probs = ["oui", "non"], [p["parametres"]["p"], 1 - p["parametres"]["p"]]
                else:
                    mods, probs = list(p["parametres"]["modalites"]), list(p["parametres"]["modalites"].values())
                cum, acc = [], 0.0
                for pr in probs:
                    acc += pr
                    cum.append(min(1.0, acc / sum(probs)))
                bornes = [-math.inf] + [stats.norm.ppf(c) if c < 1 else math.inf for c in cum]
                res[pid] = {"probabilites": {m: round(float(Phi((bornes[i + 1] - lam * f) / sd) - Phi((bornes[i] - lam * f) / sd)), 3)
                                             for i, m in enumerate(mods)}}
                continue
            q = {k: mc.quantile_conditionnel(p, g["charge"], f, qq) for k, qq in (("p10", 0.1), ("mediane", 0.5), ("p90", 0.9))}
            if modif and pid in modif:
                q = {k: modif[pid](v) for k, v in q.items()}
            res[pid] = {k: round(v, 3) for k, v in q.items()}
    return res


def sumo(v):
    """Correspondance proposée vers un vType SUMO (valeurs médianes du profil)."""
    def m(pid):
        return v[pid]["mediane"] if pid in v else None
    fv = {r: round(m(f"vit.{r}") / vma, 3) for r, vma in (
        ("artere_centre_ville_50", 50), ("traversee_petite_agglo_50", 50), ("entree_sortie_agglo_50", 50),
        ("route_2_3_voies_80", 80), ("route_2x2_110", 110), ("autoroute_degagement_110", 110),
        ("autoroute_liaison_130", 130), ("zone_30_be", 30))}
    return {
        "accel": m("acc.demarrage_pic"),
        "decel": m("dec.max_courante_urbain"),
        "emergencyDecel": abs(m("dec.urgence_max_markkula")),
        "tau": m("tiv.moyen_conducteur_urbain"),
        "minGap": m("tiv.ecart_arret"),
        "treaction_EIDM": m("tpr.anticipe"),
        "speedFactor_par_reseau": fv,
        "notes": ("Dérivé des médianes du profil. accel = pic de démarrage (Salles 2020) ; decel = décélération habituelle maximale "
                  "en suivi (Huang 2018) ; emergencyDecel = a1 d'urgence (Markkula 2016) ; tau = TIV moyen urbain (Huang 2018) ; "
                  "minGap = plage de calage IDM (faible confiance). SUMO n'a qu'un speedFactor par véhicule : choisir celui du réseau "
                  "dominant ou passer par des vClass/edge types ; le prototype Python applique le facteur du réseau. "
                  "sigma (dawdling Krauss) : pas d'équivalent mesuré, laisser la valeur par défaut ou utiliser EIDM."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=mc.DOSSIER_DOC)
    a = ap.parse_args()
    params, _ = mc.charger(a.dossier)
    idx = mc.index(params)
    grp = mc.groupes(params)

    facteurs = {
        "style": {"loi": "normale", "parametres": {"moyenne": 0, "ecart_type": 1},
                  "description": "Dynamisme / prise de risque : vitesse libre, accélérations, vitesse en courbe, créneaux, comportements aux feux, STOP, piétons."},
        "vigilance": {"loi": "normale", "parametres": {"moyenne": 0, "ecart_type": 1},
                      "description": "Rapidité de perception-réaction (4 TPR liés)."},
        "correlation_style_vigilance": 0.0,
        "nature": "estimation (hypothèse de structure)",
        "justification": "Bosetti 2014 (tab. 6) : l'identité du conducteur est le premier facteur de ses accélérations et vitesses en courbe ; "
                         "UDRIVE D41.1 (tab. 3.4) : vitesse et traits déviants associés. Aucune source lue ne donne de matrice de corrélation complète : "
                         "les charges ci-dessous sont des hypothèses à calibrer (par ex. sur highD/inD sous licence, ou sur des données françaises).",
    }
    charges = {}
    for nom, g in grp.items():
        fac, j = JUSTIF.get(nom, (g["facteur"], "Hypothèse."))
        assert fac == g["facteur"], nom
        charges[nom] = {"facteur": g["facteur"], "charge": g["charge"], "parametres": g["ids"], "nature": "hypothese",
                        "justification": j}
    # corrélations de rang attendues entre groupes (Spearman)
    noms = sorted(grp)
    mat = {}
    for i, n1 in enumerate(noms):
        for n2 in noms[i + 1:]:
            g1, g2 = grp[n1], grp[n2]
            r = mc.spearman_theorique(g1["charge"], g2["charge"], g1["facteur"] == g2["facteur"])
            if abs(r) > 1e-9:
                mat[f"{n1}|{n2}"] = round(r, 3)

    profils = []
    for pid, lib, a_, b_ in TRANCHES:
        poids, Smoy = tranche(a_, b_)
        v = valeurs_profil(params, grp, Smoy, 0.0, idx)
        profils.append({"id": pid, "libelle": lib, "type": "style",
                        "facteur_style": {"intervalle": [None if a_ == -math.inf else a_, None if b_ == math.inf else b_],
                                          "valeur_representative": round(Smoy, 3)},
                        "facteur_vigilance": {"valeur_representative": 0.0, "note": "indépendant du style ; tiré N(0,1) dans le prototype"},
                        "poids_population": round(poids, 4), "valeurs": v, "correspondance_sumo": sumo(v)})

    # profil « distrait » : tranche basse de la vigilance (10 %)
    pv, Vmoy = tranche(-math.inf, -1.2816)
    v = valeurs_profil(params, grp, 0.0, Vmoy, idx)
    profils.append({"id": "distrait", "libelle": "Conducteur distrait / peu vigilant", "type": "vigilance",
                    "facteur_style": {"valeur_representative": 0.0},
                    "facteur_vigilance": {"intervalle": [None, -1.2816], "valeur_representative": round(Vmoy, 3)},
                    "poids_population": round(pv, 4), "combinable_avec_style": True,
                    "valeurs": v, "correspondance_sumo": sumo(v),
                    "comportement_specifique": {
                        "part_temps_tache_secondaire": {"population_France": 0.083, "profil": 0.194,
                                                        "source": "UDRIVE D41.1 p. 5 (France 8,3 % ; Pologne 19,4 % pris comme ordre de grandeur haut, hypothèse)"},
                        "freinage_urgence_pendant_tache": {"modele": "tpr.markkula.alphaB_yeux_hors_route", "source": "Markkula 2016 fig. 10"}}})

    # profils d'attribut (modulateurs sourcés)
    def k_anticipe(f):
        return lambda x: x * f
    novice_caps = {"autoroute_liaison_130": (130, 110), "autoroute_degagement_110": (110, 100), "route_2x2_110": (110, 100)}
    mod_novice = {"tpr.anticipe": k_anticipe(0.52 / 0.55)}
    for r, (vma, cap) in novice_caps.items():
        mod_novice[f"vit.{r}"] = (lambda vma_, cap_: (lambda x: x * cap_ / vma_))(vma, cap)
    v = valeurs_profil(params, grp, 0.0, 0.0, idx, mod_novice)
    profils.append({"id": "novice", "libelle": "Conducteur novice (permis probatoire)", "type": "attribut",
                    "facteur_style": {"valeur_representative": 0.0, "note": "aucune donnée lue sur le style des novices : neutre (lacune)"},
                    "poids_population": None, "poids_note": "part des novices dans le trafic non trouvée (lacune) : paramètre de scénario",
                    "modulations": [
                        {"parametre": "vit.* (autoroutes, 2x2)", "regle": "facteur de vitesse rapporté à la VMA probatoire : 110 au lieu de 130, 100 au lieu de 110 ; 80 hors agglomération (inchangé depuis 2018)",
                         "nature": "norme + hypothèse (même rapport à la limite que les autres conducteurs)", "source": "AN QE 8216 (art. R413-5)"},
                        {"parametre": "tpr.anticipe", "regle": "× 0,52/0,55 (jeunes vs ensemble, objet attendu)", "nature": "estimation",
                         "source": "NCHRP 400 p. 32-33"},
                        {"parametre": "courbe.*, acc.*", "regle": "l'expérience est significative (Bosetti tab. 6) mais son sens n'est pas publié : non modulé", "nature": "lacune",
                         "source": "Bosetti 2014"}],
                    "valeurs": v, "correspondance_sumo": sumo(v)})
    mod_senior = {"tpr.anticipe": k_anticipe(0.66 / 0.55)}
    v = valeurs_profil(params, grp, 0.0, 0.0, idx, mod_senior)
    profils.append({"id": "senior", "libelle": "Conducteur senior", "type": "attribut",
                    "facteur_style": {"valeur_representative": 0.0, "note": "pas de donnée française de vitesse par âge lue : neutre (lacune)"},
                    "poids_population": None, "poids_note": "paramètre de scénario",
                    "modulations": [
                        {"parametre": "tpr.anticipe", "regle": "× 0,66/0,55 (âgés vs ensemble, objet attendu)", "nature": "estimation", "source": "NCHRP 400 p. 32-33"},
                        {"parametre": "tpr.surprise_obstacle, tpr.inattendu_signal", "regle": "inchangés : pas de différence d'âge significative (Lerner ; Olson & Sivak 1,06 s âgés vs 1,10 s jeunes)",
                         "nature": "mesure", "source": "NCHRP 400 p. 24 (tableau 13)"}],
                    "valeurs": v, "correspondance_sumo": sumo(v)})
    profils.append({"id": "conducteur_pl", "libelle": "Conducteur de poids lourd", "type": "attribut", "poids_population": None,
                    "modulations": [
                        {"parametre": "vitesses", "regle": "utiliser vit.poids_lourds (84,2 km/h autoroute de liaison, 73,8 km/h hors agglomération, 36,0 km/h artères, de jour, 2023)",
                         "nature": "mesure", "source": "ONISR 2023 p. 7"},
                        {"parametre": "dec.urgence_max_markkula", "regle": "valeur absolue N(4,70 ; 1,44) m/s² (a1 = -4,70 dans la source ; camions/bus, n = 17)", "nature": "mesure", "source": "Markkula 2016 fig. 10"},
                        {"parametre": "tpr.markkula.alphaB", "regle": "yeux sur la menace N(0,27 ; 0,40) ; yeux hors route lognormale(-0,51 ; 0,85)", "nature": "mesure", "source": "Markkula 2016 fig. 10"},
                        {"parametre": "tiv.norme_fr", "regle": "50 m minimum entre PL hors agglomération", "nature": "norme", "source": "Bison Futé (R412-12)"},
                        {"parametre": "acc.*", "regle": "limité par le véhicule (volet 01_Vehicules)", "nature": "renvoi"}]})
    profils.append({"id": "conducteur_bus", "libelle": "Conducteur de bus urbain", "type": "attribut", "poids_population": None,
                    "modulations": [
                        {"parametre": "dec (arrêts)", "regle": "≤ 0,205 g (2,0 m/s²) avec passagers debout", "nature": "norme", "source": "Cerema 2018 p. 31 ; VSA70 p. 65 (2 m/s²)"},
                        {"parametre": "courbe", "regle": "a_lat ≤ 1 m/s² pour personnes debout", "nature": "norme", "source": "VSA70 2013 p. 65"}]})
    for vid, lib, cle in (("cycliste_classique", "Cycliste (vélo classique)", "velo"), ("cycliste_vae", "Cycliste à assistance électrique (25 km/h)", "VAE_25"),
                          ("cycliste_speed_pedelec", "Speed pedelec (45 km/h)", "speed_pedelec_45")):
        profils.append({"id": vid, "libelle": lib, "type": "deux_roues", "poids_population": None,
                        "vitesse_moyenne_kmh_par_age": idx["hetero.cycliste_age"]["parametres"][cle],
                        "source": "Schleinitz et al. 2017 (diapositive ETSC)",
                        "parametres_tires": ["velo.vitesse_traversee (carrefour à feux, Munich)", "velo.acceleration_revue"],
                        "notes": "Vitesse en section courante : moyenne par âge ci-dessus ; à un carrefour au vert : velo.vitesse_traversee. Facteur style commun avec les conducteurs (hypothèse)."})

    doc = {"meta": {"titre": "Profils de conducteurs corrélés (volet 02_Conducteurs)", "version": "0.1.0", "date": dt.date.today().isoformat(),
                    "generateur": "recon/trafic/conducteurs/construire_profils.py",
                    "methode": mc.__doc__.strip()},
           "facteurs_latents": facteurs, "charges_par_groupe": charges,
           "correlations_de_rang_attendues": mat,
           "profils": profils}
    chemin = os.path.join(a.dossier, "profils_conducteurs.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"{len(profils)} profils, {len(charges)} groupes, {len(mat)} corrélations attendues -> {chemin}")


if __name__ == "__main__":
    main()
