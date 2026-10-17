"""Dynamique longitudinale d'un véhicule pour le simulateur de trafic (volet « véhicules »).

Modèle volontairement simple, physique et vérifiable sur des mesures publiées
(tests ADAC, règlements ONU R13-H / R13 / R78, Greibe 2007) :

  accélération maximale à la vitesse v (m/s), sur une pente p (m/m, + = rampe) :
      a(v) = min(a_lancement, k * P / (m * v), a_adherence) - (F_roul + F_aero + F_pente) / m
      F_roul = m g C_r cos(atan p) ; F_aero = 1/2 rho CxS v^2 ; F_pente = m g sin(atan p)
  - P : puissance maximale déclarée (W) ; m : masse en ordre de marche + charge (kg) ;
  - k : part de la puissance réellement disponible à la roue en accélération (rendement de
        transmission, plage de régime, inertie des masses tournantes, temps de passage des
        rapports). k n'est PAS une donnée constructeur : il est calé sur les reprises mesurées
        par l'ADAC (voir valider_vehicules.py) ;
  - a_lancement : plafond d'accélération à basse vitesse (patinage, embrayage, temps de réponse
        du turbo, limitation du couple électrique), calé sur le 15-30 km/h mesuré par l'ADAC ;
  - a_adherence : mu * g * part de masse sur l'essieu moteur.

  freinage d'urgence : temps mort t_m (pédale -> début de décélération), montée linéaire de la
  décélération pendant t_e (jerk = d_max / t_e), puis décélération établie d_max.

Toutes les grandeurs sont en unités SI. Aucune dépendance hors bibliothèque standard.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional

G = 9.81  # m/s^2
# Masse volumique de l'air sec à 101 325 Pa et 20 °C : rho = p / (R_s T) = 101325 / (287.05 * 293.15)
RHO_AIR = 101325.0 / (287.05 * 293.15)  # = 1.204 kg/m^3


@dataclass
class Vehicule:
    """Paramètres d'un véhicule (une instance tirée d'une classe ou un modèle de référence)."""
    nom: str
    masse_kg: float                 # masse en ordre de marche (conducteur 75 kg inclus) + charge
    puissance_kW: float             # puissance maximale (système pour les hybrides si connue)
    # Valeurs par défaut = valeurs centrales de vehicules_parametres.json (VP) ; une instance réelle
    # doit être tirée par population.py ou construite depuis une fiche.
    k_puissance: float = 0.74       # moyenne des 10 calages ADAC (VP-DYN-K)
    a_lancement: float = 4.1        # m/s^2, 15-30 km/h mesuré des électriques (VP-DYN-A-LANCEMENT)
    cxs_m2: float = 0.67            # 0,248 x 1,80 m x 1,50 m (VP-DYN-CXS, estimation)
    c_roulement: float = 0.0085     # classe C de l'étiquette pneus UE (VP-DYN-CR, estimation)
    v_max_kmh: float = 180.0        # vitesse maximale par construction
    mu_adherence: float = 1.0       # adhérence longitudinale mobilisable, sec (estimation, >= MFDD ADAC / g)
    part_masse_essieu_moteur: float = 0.6   # estimation (traction avant)
    d_max: float = 10.9             # m/s^2, MFDD équivalente 100-0 km/h ADAC (VP-FREIN-DMAX-SEC)
    t_mort_frein: float = 0.0       # s, de l'action sur la pédale au début de décélération
    t_etab_frein: float = 0.0       # s, montée de 0 à d_max. 0 => d_max est une décélération moyenne
                                    # équivalente (rampe incluse), comme les mesures ADAC et Greibe.
                                    # Si t_etab > 0, d_max doit être la décélération ÉTABLIE (> MFDD).
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ forces
    def resistance_N(self, v: float, pente: float = 0.0) -> float:
        th = math.atan(pente)
        return (self.masse_kg * G * (self.c_roulement * math.cos(th) + math.sin(th))
                + 0.5 * RHO_AIR * self.cxs_m2 * v * v)

    def acceleration_max(self, v: float, pente: float = 0.0) -> float:
        """Accélération maximale (m/s^2) à la vitesse v (m/s). Peut être négative en forte rampe."""
        v_max = self.v_max_kmh / 3.6
        a_adh = self.mu_adherence * G * self.part_masse_essieu_moteur
        if v >= v_max:
            a_mot = 0.0
            # au-delà de v_max le moteur ne fournit plus que ce qui maintient v_max
            return min(0.0, -self.resistance_N(v, pente) / self.masse_kg + self.resistance_N(v_max, pente) / self.masse_kg)
        a_pui = self.k_puissance * self.puissance_kW * 1000.0 / (self.masse_kg * max(v, 0.1))
        a_mot = min(self.a_lancement, a_pui, a_adh)
        return a_mot - self.resistance_N(v, pente) / self.masse_kg

    def temps_acceleration(self, v1_kmh: float, v2_kmh: float, pente: float = 0.0, dt: float = 0.005) -> float:
        """Temps (s) pour passer de v1 à v2 (km/h) à pleine accélération. inf si inatteignable."""
        v, v2, t = v1_kmh / 3.6, v2_kmh / 3.6, 0.0
        while v < v2:
            a = self.acceleration_max(v, pente)
            if a <= 1e-4:
                return math.inf
            # Runge-Kutta 2 sur v(t)
            a2 = self.acceleration_max(v + 0.5 * dt * a, pente)
            v_new = v + dt * a2
            if v_new >= v2:
                t += dt * (v2 - v) / (v_new - v)
                return t
            v, t = v_new, t + dt
            if t > 600:
                return math.inf
        return t

    def distance_freinage(self, v0_kmh: float, d_max: Optional[float] = None, pente: float = 0.0) -> float:
        """Distance (m) de l'action sur le frein à l'arrêt : temps mort + montée linéaire + palier.
        La pente (+ = rampe) ajoute g sin(atan p) à la décélération (signe conservé)."""
        v = v0_kmh / 3.6
        d = self.d_max if d_max is None else d_max
        d_eff = d + G * math.sin(math.atan(pente))
        s = v * self.t_mort_frein
        te = self.t_etab_frein
        # pendant la montée linéaire, la décélération moyenne vaut d/2
        dv_montee = 0.5 * d * te
        if dv_montee >= v:  # arrêt pendant la montée : résoudre v - d t^2 / (2 te) = 0
            t_stop = math.sqrt(2 * v * te / d)
            return s + v * t_stop - d * t_stop ** 3 / (6 * te)
        s += v * te - d * te * te / 6.0
        v1 = v - dv_montee
        return s + v1 * v1 / (2 * d_eff)

    def as_dict(self) -> dict:
        return asdict(self)


def mfdd_depuis_distance(v0_kmh: float, distance_m: float) -> float:
    """Décélération moyenne équivalente v0^2 / (2 s) (m/s^2) — notion des essais de presse."""
    v = v0_kmh / 3.6
    return v * v / (2.0 * distance_m)


def distance_reglementaire_R13H(v_kmh: float) -> float:
    """Distance d'arrêt maximale ONU R13-H, essai type 0 moteur débrayé : s <= 0,1 v + 0,0060 v^2."""
    return 0.1 * v_kmh + 0.0060 * v_kmh ** 2


def distance_reglementaire_R13_lourd(v_kmh: float, moteur_embraye: bool = False) -> float:
    """Distance d'arrêt maximale ONU R13, essai type 0 (M2, M3, N) : 0,15 v + v^2/130 moteur débrayé
    (dm >= 5,0 m/s^2) ; 0,15 v + v^2/103,5 moteur embrayé (dm >= 4,0 m/s^2). R13, annexe 4, § 2.1.1."""
    return 0.15 * v_kmh + v_kmh ** 2 / (103.5 if moteur_embraye else 130.0)


def a_lancement_pour_temps(veh: Vehicule, v1_kmh: float, v2_kmh: float, t_mesure: float,
                           a_bas: float = 0.5, a_haut: float = 9.0, tol: float = 1e-4) -> float:
    """Cale le plafond a_lancement (m/s^2) pour reproduire un temps d'accélération (dichotomie)."""
    sauv = veh.a_lancement
    try:
        for _ in range(80):
            a = 0.5 * (a_bas + a_haut)
            veh.a_lancement = a
            if veh.temps_acceleration(v1_kmh, v2_kmh) > t_mesure:
                a_bas = a
            else:
                a_haut = a
            if a_haut - a_bas < tol:
                break
        return 0.5 * (a_bas + a_haut)
    finally:
        veh.a_lancement = sauv


def k_pour_temps(veh: Vehicule, v1_kmh: float, v2_kmh: float, t_mesure: float,
                 k_bas: float = 0.2, k_haut: float = 1.5, tol: float = 1e-4) -> float:
    """Cale k_puissance pour reproduire un temps d'accélération mesuré (dichotomie)."""
    sauv = veh.k_puissance
    try:
        for _ in range(80):
            k = 0.5 * (k_bas + k_haut)
            veh.k_puissance = k
            t = veh.temps_acceleration(v1_kmh, v2_kmh)
            if t > t_mesure:
                k_bas = k
            else:
                k_haut = k
            if k_haut - k_bas < tol:
                break
        return 0.5 * (k_bas + k_haut)
    finally:
        veh.k_puissance = sauv
