"""Lois de probabilité du modèle de conducteurs : ajustement à partir de statistiques
publiées, quantiles et tirages.

Toutes les grandeurs sont en unités SI (s, m, m/s, m/s²) sauf mention.
Les fonctions d'ajustement ne fabriquent aucune donnée : elles convertissent des statistiques
publiées (moyenne, écart-type, percentiles, taux de dépassement) en paramètres de loi.

Lois reconnues dans conducteurs_parametres.json (champ "loi") :
  normale              {moyenne, ecart_type}
  normale_tronquee     {moyenne, ecart_type, min, max}
  lognormale           {mu_log, sigma_log}            (X = exp(N(mu_log, sigma_log)))
  lognormale_decalee   {decalage, mu_log, sigma_log}  (X = decalage + exp(N(...)))
  gev                  {k, sigma, mu}                 (convention MATLAB / Huang 2018, k = forme)
  logistique           {t50, echelle}                 (probabilité croissante en fonction de x)
  bernoulli            {p}
  categorielle         {modalites: {nom: proba}}
  uniforme             {min, max}
  constante            {valeur}
  empirique_classes    {bornes: [...], frequences: [...]}  (histogramme par classes)
  fonction             {expression, ...}                 (relation déterministe, pas de tirage)

Troncature explicite (optionnelle, toute loi continue) : clés « q_min » et/ou « q_max » dans les
paramètres (ordres de quantile, ex. q_max = 0,99). La loi tronquée a pour quantile
Q(q_min + (q_max - q_min) p) et pour fonction de répartition (F(x) - q_min) / (q_max - q_min), bornée
à [0, 1]. Elle sert à couper les queues non bornées des GEV de type Fréchet (Huang 2018) et à documenter
la coupure (relecture adverse du 17/10/2026).
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, Sequence

import numpy as np
from scipy import stats

Z = stats.norm.ppf


# ---------------------------------------------------------------- ajustements
def lognormale_depuis_moyenne_ecart(moyenne: float, ecart: float) -> Dict[str, float]:
    """Lognormale de moyenne et d'écart-type donnés (méthode des moments)."""
    s2 = math.log(1.0 + (ecart / moyenne) ** 2)
    return {"mu_log": math.log(moyenne) - s2 / 2.0, "sigma_log": math.sqrt(s2)}


def lognormale_depuis_moyenne_quantile(moyenne: float, q: float, p: float) -> Dict[str, float]:
    """Lognormale de moyenne donnée dont le quantile d'ordre p vaut q.

    Résout mu + z_p sigma = ln q et mu + sigma²/2 = ln moyenne (racine la plus petite)."""
    zp = Z(p)
    a, b, c = 0.5, -zp, math.log(q) - math.log(moyenne)
    disc = b * b - 4 * a * c
    if disc < 0:
        raise ValueError("pas de lognormale compatible")
    sigma = (-b - math.sqrt(disc)) / (2 * a)
    if sigma <= 0:
        sigma = (-b + math.sqrt(disc)) / (2 * a)
    return {"mu_log": math.log(moyenne) - sigma * sigma / 2.0, "sigma_log": sigma}


def lognormale_depuis_quantiles(q1: float, p1: float, q2: float, p2: float) -> Dict[str, float]:
    z1, z2 = Z(p1), Z(p2)
    sigma = (math.log(q2) - math.log(q1)) / (z2 - z1)
    return {"mu_log": math.log(q1) - z1 * sigma, "sigma_log": sigma}


def normale_sigma_depuis_depassements(moyenne: float, seuils: Sequence[float],
                                      parts: Sequence[float]) -> Dict[str, float]:
    """Écart-type d'une normale de moyenne connue reproduisant au mieux (moindres carrés sur
    les écarts réduits) des parts de véhicules au-dessus de seuils (taux de dépassement)."""
    zs = np.array([Z(1.0 - p) for p in parts])
    ts = np.array(seuils, dtype=float) - moyenne
    sigma = float(np.dot(zs, ts) / np.dot(zs, zs))
    residus = [float(1.0 - stats.norm.cdf((t + moyenne - moyenne) / sigma) - p)
               for t, p in zip(ts, parts)]
    return {"moyenne": moyenne, "ecart_type": sigma,
            "residus_parts": [round(r, 4) for r in residus]}


def normale_depuis_v85(moyenne: float, v85: float) -> Dict[str, float]:
    return {"moyenne": moyenne, "ecart_type": (v85 - moyenne) / Z(0.85)}


def normale_depuis_v15_v85(v15: float, v85: float) -> float:
    """Écart-type d'une normale à partir de l'écart V85 - V15."""
    return (v85 - v15) / (2.0 * Z(0.85))


def logistique_depuis_p10_p90(x10: float, x90: float) -> Dict[str, float]:
    """Logistique croissante P(x) = 1 / (1 + exp(-(x - t50)/s)) passant par 10 % et 90 %."""
    t50 = 0.5 * (x10 + x90)
    s = (x90 - x10) / (2.0 * math.log(9.0))
    return {"t50": t50, "echelle": s}


# ---------------------------------------------------------------- quantiles / cdf
def _bornes_quantiles(par: Dict):
    return float(par.get("q_min", 0.0)), float(par.get("q_max", 1.0))


def quantile(loi: str, par: Dict, p):
    """Quantile d'ordre p (scalaire ou tableau) ; p dans ]0,1[. Troncature q_min / q_max si présente."""
    p = np.asarray(p, dtype=float)
    q0, q1 = _bornes_quantiles(par)
    if q0 > 0.0 or q1 < 1.0:
        p = q0 + (q1 - q0) * p
    if loi == "normale":
        return par["moyenne"] + par["ecart_type"] * Z(p)
    if loi == "normale_tronquee":
        a = (par["min"] - par["moyenne"]) / par["ecart_type"]
        b = (par["max"] - par["moyenne"]) / par["ecart_type"]
        return stats.truncnorm.ppf(p, a, b, loc=par["moyenne"], scale=par["ecart_type"])
    if loi == "lognormale":
        return np.exp(par["mu_log"] + par["sigma_log"] * Z(p))
    if loi == "lognormale_decalee":
        return par["decalage"] + np.exp(par["mu_log"] + par["sigma_log"] * Z(p))
    if loi == "gev":
        # convention MATLAB gevinv(k, sigma, mu) ; scipy genextreme utilise c = -k
        return stats.genextreme.ppf(p, -par["k"], loc=par["mu"], scale=par["sigma"])
    if loi == "uniforme":
        return par["min"] + (par["max"] - par["min"]) * p
    if loi == "logistique":
        return par["t50"] + par["echelle"] * np.log(p / (1.0 - p))
    if loi == "constante":
        return np.full_like(p, par["valeur"], dtype=float)
    if loi == "empirique_classes":
        bornes = np.asarray(par["bornes"], dtype=float)
        f = np.asarray(par["frequences"], dtype=float)
        f = f / f.sum()
        cdf = np.concatenate([[0.0], np.cumsum(f)])
        return np.interp(p, cdf, bornes)
    raise ValueError(f"quantile non défini pour la loi {loi}")


def cdf(loi: str, par: Dict, x):
    q0, q1 = _bornes_quantiles(par)
    if q0 > 0.0 or q1 < 1.0:
        brut = {k: v for k, v in par.items() if k not in ("q_min", "q_max")}
        return np.clip((cdf(loi, brut, x) - q0) / (q1 - q0), 0.0, 1.0)
    x = np.asarray(x, dtype=float)
    if loi == "normale":
        return stats.norm.cdf(x, par["moyenne"], par["ecart_type"])
    if loi == "lognormale":
        return stats.norm.cdf((np.log(np.maximum(x, 1e-12)) - par["mu_log"]) / par["sigma_log"])
    if loi == "lognormale_decalee":
        y = np.maximum(x - par["decalage"], 1e-12)
        return stats.norm.cdf((np.log(y) - par["mu_log"]) / par["sigma_log"])
    if loi == "gev":
        return stats.genextreme.cdf(x, -par["k"], loc=par["mu"], scale=par["sigma"])
    if loi == "logistique":
        return 1.0 / (1.0 + np.exp(-(x - par["t50"]) / par["echelle"]))
    if loi == "normale_tronquee":
        a = (par["min"] - par["moyenne"]) / par["ecart_type"]
        b = (par["max"] - par["moyenne"]) / par["ecart_type"]
        return stats.truncnorm.cdf(x, a, b, loc=par["moyenne"], scale=par["ecart_type"])
    raise ValueError(f"cdf non définie pour la loi {loi}")


def moments(loi: str, par: Dict) -> Dict[str, float]:
    """Moyenne et écart-type (numériques si besoin ; toujours numériques pour une loi tronquée)."""
    q0, q1 = _bornes_quantiles(par)
    if q0 > 0.0 or q1 < 1.0:
        u = np.linspace(0.00005, 0.99995, 20000)
        q = quantile(loi, par, u)
        return {"moyenne": float(np.mean(q)), "ecart_type": float(np.std(q))}
    if loi == "normale":
        return {"moyenne": par["moyenne"], "ecart_type": par["ecart_type"]}
    if loi == "lognormale":
        m = math.exp(par["mu_log"] + par["sigma_log"] ** 2 / 2)
        v = (math.exp(par["sigma_log"] ** 2) - 1) * m * m
        return {"moyenne": m, "ecart_type": math.sqrt(v)}
    if loi == "lognormale_decalee":
        m = math.exp(par["mu_log"] + par["sigma_log"] ** 2 / 2)
        v = (math.exp(par["sigma_log"] ** 2) - 1) * m * m
        return {"moyenne": par["decalage"] + m, "ecart_type": math.sqrt(v)}
    if loi == "gev":
        d = stats.genextreme(-par["k"], loc=par["mu"], scale=par["sigma"])
        return {"moyenne": float(d.mean()), "ecart_type": float(d.std())}
    u = np.linspace(0.0005, 0.9995, 2000)
    q = quantile(loi, par, u)
    return {"moyenne": float(np.mean(q)), "ecart_type": float(np.std(q))}


def tirer(loi: str, par: Dict, u: Iterable[float]):
    """Tirage par inversion à partir d'uniformes u (permet la copule gaussienne)."""
    u = np.clip(np.asarray(u, dtype=float), 1e-6, 1 - 1e-6)
    if loi == "bernoulli":
        # 1 = comportement « favorable » (ex. cède le passage) pour les u faibles
        return (u < par["p"]).astype(float)
    if loi == "categorielle":
        # modalités ordonnées de la plus prudente à la plus risquée ; renvoie l'indice
        cum = np.cumsum(list(par["modalites"].values()))
        cum = cum / cum[-1]
        return np.searchsorted(cum, u, side="right").astype(float)
    return quantile(loi, par, u)
