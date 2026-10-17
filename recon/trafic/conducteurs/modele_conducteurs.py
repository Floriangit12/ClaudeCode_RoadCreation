"""Prototype du modèle de conducteurs : tirage d'une population hétérogène et corrélée.

Principe (copule gaussienne à deux facteurs latents) :
  - chaque conducteur i a deux facteurs latents indépendants N(0,1) :
      S_i = « style » (dynamisme / prise de risque), V_i = « vigilance » (rapidité de réaction) ;
  - chaque groupe g de paramètres (ex. « vitesse », « tiv_moyen ») a une variable latente
      Y_ig = λ_g F_i + sqrt(1 - λ_g²) ε_ig, ε_ig ~ N(0,1), F = S ou V selon le groupe ;
  - chaque paramètre p du groupe g vaut X_ip = Q_p(Φ(Y_ig)) où Q_p est le quantile de SA loi sourcée
    (conducteurs_parametres.json).
Ainsi les lois marginales restent exactement celles des sources ; seules les dépendances (λ_g)
sont des hypothèses, documentées dans profils_conducteurs.json.

Les paramètres d'un même groupe partagent Y_ig : un conducteur rapide sur une artère l'est aussi
sur autoroute (même rang dans chaque distribution).
"""
from __future__ import annotations

import json
import math
import os
import sys
from typing import Dict, Optional

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lois  # noqa: E402

DOSSIER_DOC = "D:/DocRoute/17_Modele_Vehicules_Conducteurs/02_Conducteurs"


def charger(dossier: str = DOSSIER_DOC):
    with open(os.path.join(dossier, "conducteurs_parametres.json"), encoding="utf-8") as f:
        params = json.load(f)
    prof = None
    chemin_p = os.path.join(dossier, "profils_conducteurs.json")
    if os.path.exists(chemin_p):
        with open(chemin_p, encoding="utf-8") as f:
            prof = json.load(f)
    return params, prof


def index(params) -> Dict[str, dict]:
    return {p["id"]: p for p in params["parametres"]}


def groupes(params) -> Dict[str, dict]:
    """{groupe: {facteur, charge, ids, population}} ; vérifie la cohérence des charges."""
    g = {}
    for p in params["parametres"]:
        t = p.get("tirage")
        if not t:
            continue
        nom = t["groupe"]
        if nom not in g:
            g[nom] = {"facteur": t["facteur"], "charge": t["charge"], "ids": [],
                      "population": t.get("population", "conducteur_vl")}
        else:
            if g[nom]["facteur"] != t["facteur"] or abs(g[nom]["charge"] - t["charge"]) > 1e-12:
                raise ValueError(f"charges incohérentes dans le groupe {nom}")
        g[nom]["ids"].append(p["id"])
    return g


def valeur(p: dict, u):
    """Quantile du paramètre p pour des uniformes u (loi sourcée)."""
    return lois.tirer(p["loi"], p["parametres"], u)


def tirer_population(params, n: int, rng: np.random.Generator,
                     S: Optional[np.ndarray] = None, V: Optional[np.ndarray] = None,
                     charges: Optional[Dict[str, float]] = None):
    """Tire n conducteurs. S, V : facteurs latents imposés (sinon N(0,1)).
    charges : remplace les charges λ_g (tests de sensibilité). Renvoie (valeurs, latents)."""
    idx = index(params)
    grp = groupes(params)
    if S is None:
        S = rng.standard_normal(n)
    if V is None:
        V = rng.standard_normal(n)
    fac = {"style": S, "vigilance": V}
    out, lat = {}, {"style": S, "vigilance": V}
    for nom, g in grp.items():
        lam = g["charge"] if not charges or nom not in charges else charges[nom]
        Y = lam * fac[g["facteur"]] + math.sqrt(max(0.0, 1 - lam * lam)) * rng.standard_normal(n)
        u = stats.norm.cdf(Y)
        lat[nom] = Y
        for pid in g["ids"]:
            out[pid] = valeur(idx[pid], u)
    return out, lat


def tirer_evenement(params, pid: str, facteur_conducteur: np.ndarray, rng: np.random.Generator):
    """Comportement discret à CHAQUE rencontre (STOP, jaune, piéton) : le facteur du conducteur est
    conservé, le bruit ε est retiré à chaque événement. Renvoie la valeur (indice de modalité pour
    une loi catégorielle, 0/1 pour une Bernoulli, seuil pour une logistique)."""
    p = index(params)[pid]
    lam = p["tirage"]["charge"]
    f = np.asarray(facteur_conducteur, dtype=float)
    Y = lam * f + math.sqrt(max(0.0, 1 - lam * lam)) * rng.standard_normal(f.shape)
    return valeur(p, stats.norm.cdf(Y))


def quantile_conditionnel(p: dict, charge: float, f: float, q: float = 0.5):
    """Quantile d'ordre q du paramètre p sachant le facteur latent F = f."""
    y = charge * f + math.sqrt(max(0.0, 1 - charge * charge)) * stats.norm.ppf(q)
    return float(np.asarray(valeur(p, stats.norm.cdf(y))).ravel()[0])


def spearman_theorique(l1: float, l2: float, meme_facteur: bool) -> float:
    """Corrélation de rang entre deux groupes : ρ_latent = λ1 λ2 si même facteur, 0 sinon ;
    Spearman d'une normale bivariée = 6/π asin(ρ/2)."""
    rho = l1 * l2 if meme_facteur else 0.0
    return 6.0 / math.pi * math.asin(rho / 2.0)
