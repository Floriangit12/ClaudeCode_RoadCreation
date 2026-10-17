"""Lois de comportement du conducteur (fonctions pures, vectorisées) — conception §§ 5 à 7.

Toutes les grandeurs sont en SI. Aucun chiffre n'est introduit ici : les constantes viennent de
parametres_modele.json ou de parametres_prototype.json et sont passées en argument.
"""
from __future__ import annotations

import numpy as np

INF = 1e9


# ----------------------------------------------------------------------------- poursuite (§ 6.1)
def iidm(v, s, dv, v0, T, s0, a, b, delta=4.0):
    """IIDM (Treiber & Kesting), forme du code SUMO MSCFModel_EIDM.cpp l. 1060-1075.
    v vitesse propre, s écart net au meneur (INF si aucun), dv = v - v_meneur."""
    v = np.asarray(v, float)
    s = np.maximum(np.asarray(s, float), 1e-3)
    sstar = s0 + np.maximum(0.0, v * T + v * dv / (2.0 * np.sqrt(a * b)))
    z = sstar / s
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        vr = np.minimum(v / np.maximum(v0, 1e-6), 10.0)
        a_free_inf = a * (1.0 - vr ** delta)
        expo = np.where(a_free_inf > 1e-9, 2.0 * a / np.maximum(a_free_inf, 1e-9), 1.0)
        cas_ge = a * (1.0 - z * z)
        cas_lt = a_free_inf * (1.0 - np.power(np.minimum(z, 1.0), np.minimum(expo, 700.0)))
        acc_inf = np.where(z >= 1.0, cas_ge, cas_lt)
        a_free_sup = -b * (1.0 - np.power(np.minimum(v0 / np.maximum(v, 1e-6), 1.0), a * delta / b))
        acc_sup = np.where(z >= 1.0, a_free_sup + a * (1.0 - z * z), a_free_sup)
    return np.where(v <= v0, acc_inf, acc_sup)


def cah(v, vl, s, al, a):
    """Heuristique « vitesse constante du meneur à accélération constante » (CAH), Kesting 2010 éq. 4."""
    v, vl, s, al = (np.asarray(x, float) for x in (v, vl, s, al))
    s = np.maximum(s, 1e-3)
    vl = np.maximum(vl, 0.0)
    alt = np.minimum(al, a)
    cond = vl * (v - vl) <= -2.0 * s * alt
    den = vl * vl - 2.0 * s * alt
    with np.errstate(divide="ignore", invalid="ignore"):
        a1 = np.where(den > 1e-9, v * v * alt / np.maximum(den, 1e-9), alt)
    a2 = alt - np.where(v > vl, (v - vl) ** 2, 0.0) / (2.0 * s)
    return np.where(cond, a1, a2)


def acc_cah(a_iidm, a_cah, b, c=0.99):
    """Combinaison IIDM + CAH (modèle ACC de Kesting 2010 éq. 5)."""
    return np.where(a_iidm >= a_cah, a_iidm,
                    (1.0 - c) * a_iidm + c * (a_cah + b * np.tanh((a_iidm - a_cah) / b)))


def poursuite(v, s, vl, al, v0, T, s0, a, b, delta=4.0, c=0.99):
    """Accélération voulue derrière un meneur (IIDM + CAH). s = INF : route libre."""
    ai = iidm(v, s, v - vl, v0, T, s0, a, b, delta)
    libre = np.asarray(s) >= INF / 2
    ac = cah(v, vl, np.where(libre, 1e6, s), al, a)
    return np.where(libre, ai, acc_cah(ai, ac, b, c))


def facteur_demarrage(tau, taccmax, mflat, mbegin):
    """Facteur de démarrage EIDM f(τ) = (tanh((2τ/taccmax - Mbegin) Mflatness) + 1)/2 ; τ < 0 -> 0."""
    tau = np.asarray(tau, float)
    f = (np.tanh((tau * 2.0 / taccmax - mbegin) * mflat) + 1.0) / 2.0
    return np.where(tau < 0, 0.0, f)


def equilibre_iidm(v, T, s0):
    """Écart net d'équilibre de l'IIDM : s0 + v T (TIV net = T + s0/v)."""
    return s0 + v * T


# ----------------------------------------------------------------------------- vitesses cibles locales
def decel_cible(v, d, v_cible):
    """Décélération cinématique constante pour atteindre v_cible à la distance d (≥ 0 ; 0 si v ≤ v_cible)."""
    v = np.asarray(v, float)
    return np.where(v > v_cible, (v * v - v_cible * v_cible) / (2.0 * np.maximum(d, 0.5)), 0.0)


def v85_setra(R, vlim_kmh):
    """V85 (km/h) en courbe, relation Sétra : Vlim / (1 + 346 / R^1,5) (Cerema 2018 p. 8)."""
    return vlim_kmh / (1.0 + 346.0 / np.power(R, 1.5))


def v_bosetti(R, alpha, alat):
    """Frontière de Bosetti 2014 : min(α R^(1/3), √(a_lat R)) (m/s)."""
    return np.minimum(alpha * np.power(R, 1.0 / 3.0), np.sqrt(alat * R))


def v_courbe(R, alpha, alat, agglo, kappa, vlim_kmh):
    """Vitesse en courbe du conducteur (conception § 7.1) en m/s.
    Hors agglomération : max(Bosetti, Sétra × κ_i), plafonnée par √(a_lat,i R) ; en agglomération et en carrefour :
    Bosetti. v0.2 : le plafond √(a_lat,i R) (accélération latérale maximale propre du conducteur) est explicite ; en
    v0.1 il était respecté de fait parce que α_i et a_lat,i avaient le même rang (corrélation intra-groupe = 1)."""
    vb = v_bosetti(R, alpha, alat)
    if agglo:
        return vb
    return np.minimum(np.maximum(vb, v85_setra(R, vlim_kmh) / 3.6 * kappa), np.sqrt(alat * R))


def kappa(alpha, alat, R0, p85_R0):
    """κ_i = v_Bosetti,i(R0) / P85[v_Bosetti(R0)] (continuité de la règle en R0)."""
    return v_bosetti(R0, alpha, alat) / p85_R0


# ----------------------------------------------------------------------------- domaine g-g (§ 7.2)
def borne_gg(a_cmd, a_lat, b_acc, c_frein, alat_max):
    """Triangle g-g du conducteur (Bosetti fig. 11), hors urgence :
    a ≥ 0 : a/b + |a_lat|/a_i ≤ 1 ; a < 0 : |a|/c + |a_lat|/a_i ≤ 1."""
    reste = np.clip(1.0 - np.abs(a_lat) / alat_max, 0.0, 1.0)
    return np.clip(a_cmd, -c_frein * reste, b_acc * reste)


# ----------------------------------------------------------------------------- urgence (§ 6.5)
def looming(v, vl, s):
    """Inverse du temps à collision τ⁻¹ = (v - v_l)/s (0 si l'écart s'ouvre)."""
    return np.where((v > vl) & (s > 0), (v - vl) / np.maximum(s, 1e-3), 0.0)


def prediction_markkula(s, v, vl, al, horizon=12.0, pas=0.02, seuil=0.2):
    """Instants futurs (depuis maintenant) t0,2 (looming ≥ seuil) et tC (collision) si le suiveur garde
    sa vitesse et que le meneur garde son accélération jusqu'à l'arrêt (scalaires).
    Renvoie (t02, tC) ; inf si l'instant n'est pas atteint dans l'horizon."""
    t = np.arange(0.0, horizon + pas, pas)
    if al < 0:
        ts = vl / -al
        tt = np.minimum(t, ts)
        xl = vl * tt + 0.5 * al * tt * tt
        vlt = np.maximum(vl + al * t, 0.0)
    else:
        xl = vl * t + 0.5 * al * t * t
        vlt = vl + al * t
    g = s + xl - v * t
    lo = np.where(g > 0, (v - vlt) / np.maximum(g, 1e-3), np.inf)
    i02 = np.flatnonzero(lo >= seuil)
    ic = np.flatnonzero(g <= 0)
    t02 = float(t[i02[0]]) if i02.size else np.inf
    tc = float(t[ic[0]]) if ic.size else np.inf
    return t02, tc


def decel_requise(s, v, vl, al, marge=0.0):
    """Décélération constante requise pour ne pas heurter le meneur (arrêt derrière son point d'arrêt
    s'il freine, sinon annulation de la vitesse relative). Scalaires ou tableaux."""
    s, v, vl, al = (np.asarray(x, float) for x in (s, v, vl, al))
    dispo = s - marge
    freine = al < -0.05
    d_arret_l = np.where(freine, vl * vl / (2.0 * np.maximum(-al, 0.05)), 0.0)
    req_arret = v * v / (2.0 * np.maximum(dispo + d_arret_l, 0.05))
    req_rel = np.where(v > vl, (v - vl) ** 2 / (2.0 * np.maximum(dispo, 0.05)), 0.0)
    return np.where(freine, req_arret, req_rel)


# ----------------------------------------------------------------------------- feu jaune (§ 5.5)
def decision_jaune(ttl, seuil, d, v, a_urgence, jaune_s, option_h11=False):
    """Décision au jaune perçue : arrêt si TTL > seuil_i et arrêt possible (décélération nécessaire ≤
    décélération d'urgence) ; option H-11 : arrêt aussi si TTL > durée du jaune et arrêt possible.
    Renvoie (arret, decel_necessaire)."""
    dec = np.where(d > 0.5, v * v / (2.0 * np.maximum(d, 0.5)), np.inf)
    possible = dec <= a_urgence
    veut = ttl > seuil
    if option_h11:
        veut = veut | (ttl > jaune_s)
    return veut & possible, dec
