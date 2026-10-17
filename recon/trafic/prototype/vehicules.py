"""Véhicules du prototype : tirage (volet 01) et dynamique longitudinale vectorisée (conception § 8).

  a_max(v, p) = min(a_lancement, k P / (m v), µ g part_essieu) - (m g (C_r cos θ + sin θ) + ½ ρ CxS v²) / m
  décélération ≤ min(d_max, µ g) ; cercle de friction √(a_x² + a_y²) ≤ µ g

La formule est celle de recon/trafic/vehicules/dynamique.py (Vehicule.acceleration_max), réécrite en
numpy pour une population ; test_vehicules.py vérifie l'identité des deux versions.
Classes couvertes : VP (6 segments, population.py du volet 01, tirage conjoint masse / P/m / famille, parc en
circulation par défaut). µ sur sec : VEH.MOD.mu_sec ~ U(1,0 ; 1,11).
"""
from __future__ import annotations

import json
import random

import numpy as np

from parametres import F_VEHICULES, G, Parametres
from dynamique import RHO_AIR  # noqa: E402  (recon/trafic/vehicules)
from population import tirer_vp  # noqa: E402


def tirer_vehicules(P: Parametres, n: int, graine: int, rng: np.random.Generator) -> dict:
    """Tire n voitures particulières (segments, motorisation, masse, P/m, k, a_lancement, d_max, CxS)."""
    with open(F_VEHICULES, encoding="utf-8") as f:
        J = json.load(f)
    rnd = random.Random(graine)
    vs = [tirer_vp(J, rnd, parc=P.v("parc_vehicules")) for _ in range(n)]
    mu = P.par("VEH.MOD.mu_sec")
    out = {
        "masse": np.array([v.masse_kg for v in vs]),
        "puissance_W": np.array([v.puissance_kW * 1000.0 for v in vs]),
        "k": np.array([v.k_puissance for v in vs]),
        "a_lancement": np.array([v.a_lancement for v in vs]),
        "cxs": np.array([v.cxs_m2 for v in vs]),
        "cr": np.array([v.c_roulement for v in vs]),
        "vmax": np.array([v.v_max_kmh / 3.6 for v in vs]),
        "part_essieu": np.array([v.part_masse_essieu_moteur for v in vs]),
        "d_max": np.array([v.d_max for v in vs]),
        "longueur": np.array([v.meta["longueur_m"] for v in vs]),
        "largeur": np.array([v.meta["largeur_m"] for v in vs]),
        "empattement": np.array([(v.meta["empattement_mm"] or 2600) / 1000.0 for v in vs]),
        "classe": np.array([v.meta["classe"] for v in vs], dtype=object),
        "famille": np.array([v.meta["famille"] for v in vs], dtype=object),
        "mu": rng.uniform(mu["min"], mu["max"], n),
    }
    out["objets"] = vs
    return out


def resistance(veh: dict, v, pente=0.0, idx=None):
    """Force résistante / masse (m/s²)."""
    g = (lambda k: veh[k]) if idx is None else (lambda k: veh[k][idx])
    th = np.arctan(pente)
    return G * (g("cr") * np.cos(th) + np.sin(th)) + 0.5 * RHO_AIR * g("cxs") * v * v / g("masse")


def a_max(veh: dict, v, pente=0.0, idx=None, mu=None):
    """Accélération maximale (m/s²) des véhicules idx à la vitesse v (m/s). Même formule que dynamique.py."""
    g = (lambda k: veh[k]) if idx is None else (lambda k: veh[k][idx])
    v = np.asarray(v, float)
    mu_ = g("mu") if mu is None else mu
    vmax = g("vmax")
    a_pui = g("k") * g("puissance_W") / (g("masse") * np.maximum(v, 0.1))
    a_mot = np.minimum(np.minimum(g("a_lancement"), a_pui), mu_ * G * g("part_essieu"))
    a = a_mot - resistance(veh, v, pente, idx)
    # au-delà de vmax : le moteur ne fournit que ce qui maintient vmax (dynamique.py)
    a_sup = np.minimum(0.0, -resistance(veh, v, pente, idx) + resistance(veh, vmax, pente, idx))
    return np.where(v >= vmax, a_sup, a)


def d_max_eff(veh: dict, idx=None, mu=None):
    """Décélération maximale mobilisable : min(d_max du véhicule, µ g)."""
    g = (lambda k: veh[k]) if idx is None else (lambda k: veh[k][idx])
    mu_ = g("mu") if mu is None else mu
    return np.minimum(g("d_max"), mu_ * G)
