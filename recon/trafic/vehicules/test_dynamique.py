"""Tests unitaires du modèle longitudinal. Lancer : python recon/trafic/vehicules/test_dynamique.py"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dynamique import (Vehicule, k_pour_temps, a_lancement_pour_temps, distance_reglementaire_R13H,  # noqa: E402
                       distance_reglementaire_R13_lourd, mfdd_depuis_distance, RHO_AIR)


def test_reglementaire():
    assert abs(distance_reglementaire_R13H(100) - 70.0) < 1e-9          # 0,1 x 100 + 0,006 x 100²
    assert abs(distance_reglementaire_R13_lourd(60) - (9 + 3600 / 130)) < 1e-9
    assert abs(mfdd_depuis_distance(100, 70.0 - 10.0) - 6.43) < 0.01    # le 2e terme de R13-H correspond à 6,43 m/s²


def test_freinage_sans_rampe():
    v = Vehicule("t", 1200, 70, d_max=8.0)
    assert abs(v.distance_freinage(100) - (100 / 3.6) ** 2 / 16.0) < 1e-6


def test_freinage_avec_rampe_plus_long():
    v = Vehicule("t", 1200, 70, d_max=8.0)
    d0 = v.distance_freinage(100)
    v.t_etab_frein = 0.3
    assert v.distance_freinage(100) > d0
    d1 = v.distance_freinage(100)
    v.t_mort_frein = 0.2
    assert abs(v.distance_freinage(100) - d1 - 0.2 * 100 / 3.6) < 1e-9


def test_pente():
    v = Vehicule("t", 1200, 70, d_max=8.0)
    assert v.distance_freinage(100, pente=-0.05) > v.distance_freinage(100, pente=0.05)
    assert v.acceleration_max(20, pente=0.08) < v.acceleration_max(20, pente=0.0)


def test_vmax_et_monotonie():
    v = Vehicule("t", 1300, 75, a_lancement=4.0, v_max_kmh=160)
    assert v.acceleration_max(160 / 3.6) <= 0.0
    vals = [v.acceleration_max(x / 3.6) for x in range(40, 160, 10)]
    assert all(b <= a + 1e-9 for a, b in zip(vals, vals[1:]))
    assert v.temps_acceleration(0, 170) == math.inf


def test_calage_aller_retour():
    v = Vehicule("t", 1500, 100, a_lancement=4.0)
    v.k_puissance = 0.7
    t = v.temps_acceleration(60, 100)
    v.k_puissance = 0.5
    assert abs(k_pour_temps(v, 60, 100, t) - 0.7) < 1e-3
    v.k_puissance = 0.7
    t0 = v.temps_acceleration(0, 100)
    assert abs(a_lancement_pour_temps(v, 0, 100, t0) - 4.0) < 1e-2


def test_rho():
    assert abs(RHO_AIR - 1.204) < 0.001


if __name__ == "__main__":
    n = 0
    for nom, f in list(globals().items()):
        if nom.startswith("test_") and callable(f):
            f(); n += 1
    print(n, "tests OK")
