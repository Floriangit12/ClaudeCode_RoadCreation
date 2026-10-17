"""Tirage d'une population de conducteurs (copule gaussienne à deux facteurs, conception § 9.2) — v0.2.

  Y_ip = λ_g F_i + sqrt(1 - λ_g²) [ sqrt(ρ_w) η_ig + sqrt(1 - ρ_w) ε_ip ]
         (F = style S ou vigilance V ; η_ig bruit commun au groupe g ; ε_ip bruit propre au paramètre p)
  X_ip = Q_p(Φ(Y_ip))                       (Q_p : quantile de la loi sourcée de p dans parametres_modele.json)

Les lois marginales sont celles des sources ; les charges λ_g sont les hypothèses H-01 du volet 02.
v0.2 (relecture adverse du 17/10/2026) :
  - corrélation intra-groupe des résidus ρ_w < 1 (paramètre « correlation_intra_groupe », hypothèse H-01) :
    en v0.1 tous les paramètres d'un groupe avaient le même rang (corrélation 1) ;
  - grandeurs ordonnées construites sans croisement :
      TPR inattendu, TPR au jaune, TPR de surprise = TPR anticipé + Δ, Δ ≥ 0 lognormal dont la moyenne et
      l'écart-type sont choisis pour garder la moyenne et l'écart-type publiés de la grandeur (moments) ;
      décélérations d'urgence (Markkula a1, équivalente NCHRP) ≥ décélération habituelle b (plancher) ;
      TIV minimal habituel ≤ TIV moyen (plafond) ;
  - vitesse désirée : quantile tiré dans [q_min ; 1] (queue basse ONISR retirée, H-04) ;
  - T_suivi calculé dans le simulateur avec v_ref = médiane de la vitesse désirée du réseau.
Le groupe « politesse » (H-09) donne p_i ~ U(0, 1) (MOBIL) ; il n'est pas utilisé dans les scénarios à une voie.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

import lois
from parametres import Parametres

# Correspondance réseau -> loi de vitesse désirée (conception § 5.1, CR-01 à CR-10)
RESEAUX = {
    "zone_30_be": {"vma": 30, "id": "LON.vit.zone_30_be", "tiv": "urbain", "agglo": True},
    "artere_centre_ville_50": {"vma": 50, "id": "LON.vit.artere_centre_ville_50", "tiv": "urbain", "agglo": True},
    "traversee_petite_agglo_50": {"vma": 50, "id": "LON.vit.traversee_petite_agglo_50", "tiv": "urbain", "agglo": True},
    "route_70_be": {"vma": 70, "id": "VAL.vit.route_70_be", "tiv": "urbain", "agglo": False},
    "route_2_3_voies_80": {"vma": 80, "id": "LON.vit.route_2_3_voies_80", "tiv": "urbain", "agglo": False},
    "route_2x2_110": {"vma": 110, "id": "LON.vit.route_2x2_110", "tiv": "autoroute", "agglo": False},
    "autoroute_liaison_130": {"vma": 130, "id": "LON.vit.autoroute_liaison_130", "tiv": "autoroute", "agglo": False},
}

PROFILS_STYLE = [("prudent", -np.inf, -0.674), ("moyen", -0.674, 0.674), ("presse", 0.674, 1.5), ("agressif", 1.5, np.inf)]
# grandeurs construites par incrément sur le TPR anticipé (même groupe « tpr »)
TPR_ORDONNES = ("PER.tpr.inattendu_signal", "PER.feu.tpr_jaune", "PER.tpr.surprise_obstacle")
TPR_BASE = "PER.tpr.anticipe"


def increment_lognormal(m_base: float, s_base: float, m_cible: float, s_cible: float, rho: float) -> dict:
    """Loi lognormale de Δ ≥ 0 telle que X = base + Δ ait la moyenne et l'écart-type cibles.
    E[Δ] = m_cible - m_base ; Var(X) = s_base² + s_Δ² + 2 ρ s_base s_Δ, d'où s_Δ (racine positive).
    ρ : corrélation entre base et Δ (approximation : celle de leurs variables latentes)."""
    m_d = m_cible - m_base
    b = 2.0 * rho * s_base
    c = s_base ** 2 - s_cible ** 2
    s_d = (-b + math.sqrt(b * b - 4.0 * c)) / 2.0
    return lois.lognormale_depuis_moyenne_ecart(m_d, s_d)


def tirer_conducteurs(P: Parametres, n: int, rng: np.random.Generator, S=None, V=None) -> dict:
    """Tire n conducteurs. Renvoie {id_parametre: tableau, 'S', 'V', 'Y:<groupe>', dérivés}."""
    S = rng.standard_normal(n) if S is None else np.asarray(S, float)
    V = rng.standard_normal(n) if V is None else np.asarray(V, float)
    fac = {"style": S, "vigilance": V}
    rho_w = float(P.v("correlation_intra_groupe"))
    out = {"S": S, "V": V}
    increments = {}
    for nom, g in P.groupes().items():
        lam = g["charge"]
        eta = rng.standard_normal(n)                       # bruit commun au groupe
        Yg = lam * fac[g["facteur"]] + math.sqrt(max(0.0, 1 - lam * lam)) * eta
        out[f"Y:{nom}"] = Yg
        for pid in g["ids"]:
            eps = rng.standard_normal(n)                   # bruit propre au paramètre
            Y = lam * fac[g["facteur"]] + math.sqrt(max(0.0, 1 - lam * lam)) * (
                math.sqrt(rho_w) * eta + math.sqrt(1.0 - rho_w) * eps)
            u = stats.norm.cdf(Y)
            if pid.startswith("LON.vit.") or pid.startswith("VAL.vit."):
                q0 = float(P.v("v0_quantile_min"))
                u = q0 + (1.0 - q0) * u                    # queue basse de la loi ONISR retirée (H-04)
            if pid in TPR_ORDONNES:
                increments[pid] = u                        # tiré après le TPR anticipé
                continue
            out[pid] = np.asarray(P.quantile(pid, u), dtype=float)
        if nom == "politesse":
            out["MOBIL.politesse"] = stats.norm.cdf(Yg)    # U(0,1) au rang du groupe (H-09)
    # TPR ordonnés : X = TPR anticipé + Δ (Δ ≥ 0), mêmes moyenne et écart-type que la loi publiée
    base = out[TPR_BASE]
    mb = lois.moments(P.p(TPR_BASE)["loi"], P.par(TPR_BASE))
    lam_tpr = P.groupes()["tpr"]["charge"]
    rho_lat = lam_tpr ** 2 + (1 - lam_tpr ** 2) * rho_w
    for pid, u in increments.items():
        mc = lois.moments(P.p(pid)["loi"], P.par(pid))
        d = increment_lognormal(mb["moyenne"], mb["ecart_type"], mc["moyenne"], mc["ecart_type"], rho_lat)
        out[pid] = base + np.asarray(lois.quantile("lognormale", d, u), dtype=float)
        out[f"_increment:{pid}"] = d
    # décélérations d'urgence ≥ décélération habituelle (plancher) ; TIV minimal ≤ TIV moyen (plafond)
    b_max = np.maximum(out["LON.dec.max_courante_urbain"], out["LON.dec.max_courante_autoroute"])
    for pid in ("LON.dec.urgence_max_markkula", "LON.dec.urgence_equivalente"):
        out[f"_plancher:{pid}"] = float(np.mean(out[pid] < b_max))
        out[pid] = np.maximum(out[pid], b_max)
    for res in ("urbain", "autoroute"):
        pmin, pmoy = f"LON.tiv.min_conducteur_{res}", f"LON.tiv.moyen_conducteur_{res}"
        if pmin in out:
            out[f"_plafond:{pmin}"] = float(np.mean(out[pmin] > out[pmoy]))
            out[pmin] = np.minimum(out[pmin], out[pmoy])
    out["profil_style"] = profil_style(S)
    return out


def T_suivi(P: Parametres, pop: dict, reseau: str) -> np.ndarray:
    """T_suivi_i = TIV_moyen_i - s0_i / v_ref (LON.MOD.T_suivi), v_ref = médiane de la vitesse désirée du réseau."""
    res = RESEAUX[reseau]
    tiv = pop["LON.tiv.moyen_conducteur_autoroute"] if res["tiv"] == "autoroute" else pop["LON.tiv.moyen_conducteur_urbain"]
    v_ref = P.mediane(res["id"]) / 3.6 if P.v("T_v_ref") == "mediane_reseau" else float(P.par("LON.MOD.T_suivi")["v_ref_ms"])
    return tiv - pop["LON.tiv.ecart_arret"] / v_ref


def profil_style(S) -> np.ndarray:
    S = np.asarray(S, float)
    lab = np.empty(S.shape, dtype=object)
    for nom, lo, hi in PROFILS_STYLE:
        lab[(S >= lo) & (S < hi)] = nom
    return lab


def tirer_evenement(P: Parametres, pid: str, groupe: str, S, rng: np.random.Generator):
    """Comportement discret à chaque rencontre (STOP, piéton) : facteur style conservé, bruit retiré
    (conception § 9.3). Renvoie la valeur de la loi (indice de modalité pour une catégorielle)."""
    g = P.groupes()[groupe]
    lam = g["charge"]
    S = np.atleast_1d(np.asarray(S, float))
    Y = lam * S + math.sqrt(max(0.0, 1 - lam * lam)) * rng.standard_normal(S.shape)
    return np.asarray(P.quantile(pid, stats.norm.cdf(Y)), dtype=float)


def distrait_a_l_evenement(P: Parametres, V: float, rng: np.random.Generator) -> bool:
    """H-18 : yeux hors de la menace avec une probabilité moyenne p (UDRIVE, proxy) qui croît quand la vigilance V
    baisse : distrait si λ(-V) + sqrt(1-λ²) ε > Φ⁻¹(1 - p), ε tiré à chaque événement."""
    p = float(P.v("distraction_part_temps_FR"))
    lam = float(P.v("distraction_charge_vigilance"))
    y = lam * (-V) + math.sqrt(1.0 - lam * lam) * rng.standard_normal()
    return bool(y > stats.norm.ppf(1.0 - p))


def v0_reseau(P: Parametres, pop: dict, reseau: str) -> np.ndarray:
    """Vitesse désirée (m/s) des conducteurs sur un réseau : même rang latent « vitesse » partout."""
    pid = RESEAUX[reseau]["id"]
    if pid in pop:
        return np.maximum(pop[pid], 5.0) / 3.6
    q0 = float(P.v("v0_quantile_min"))
    u = q0 + (1.0 - q0) * stats.norm.cdf(pop["Y:vitesse"])
    return np.maximum(np.asarray(P.quantile(pid, u), float), 5.0) / 3.6
