"""Tests unitaires des lois de comportement (recon/trafic/prototype/modele.py).

  python -m unittest discover -s recon/trafic/tests -v
"""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototype"))
import modele as M  # noqa: E402


class TestIIDM(unittest.TestCase):
    def test_equilibre_iidm(self):
        """IIDM : accélération nulle à l'écart d'équilibre s0 + vT, quelle que soit v < v0 (calcul C2)."""
        for v in (2.0, 8.0, 10.0, 11.0):
            s = M.equilibre_iidm(v, 1.88, 1.75)
            a = float(M.iidm(v, s, 0.0, 11.44, 1.88, 1.75, 2.1, 2.64))
            self.assertAlmostEqual(a, 0.0, places=6)

    def test_route_libre(self):
        self.assertAlmostEqual(float(M.iidm(0.0, M.INF, 0.0, 10.0, 1.5, 2.0, 2.1, 2.6)), 2.1, places=6)
        self.assertLess(float(M.iidm(12.0, M.INF, 0.0, 10.0, 1.5, 2.0, 2.1, 2.6)), 0.0)
        # au-dessus de v0 le freinage libre reste borné par b
        self.assertGreaterEqual(float(M.iidm(40.0, M.INF, 0.0, 10.0, 1.5, 2.0, 2.1, 2.6)), -2.6)

    def test_obstacle_freinage(self):
        a = float(M.iidm(13.9, 20.0, 13.9, 13.9, 1.5, 2.0, 2.1, 2.6))
        self.assertLess(a, -2.6)

    def test_cah(self):
        # meneur plus rapide : a_CAH = min(a_l, a)
        self.assertAlmostEqual(float(M.cah(5.0, 8.0, 20.0, 1.0, 2.0)), 1.0, places=6)
        # combinaison : si IIDM ≥ CAH, on garde l'IIDM
        self.assertAlmostEqual(float(M.acc_cah(1.0, 0.5, 2.6)), 1.0)
        self.assertGreater(float(M.acc_cah(-8.0, 0.5, 2.6)), -8.0)

    def test_poursuite_libre(self):
        self.assertAlmostEqual(float(M.poursuite(5.0, M.INF, 5.0, 0.0, 10.0, 1.5, 2.0, 2.0, 2.6)),
                               float(M.iidm(5.0, M.INF, 0.0, 10.0, 1.5, 2.0, 2.0, 2.6)))


class TestDemarrageCourbes(unittest.TestCase):
    def test_facteur_demarrage(self):
        t = np.linspace(-1, 10, 200)
        f = M.facteur_demarrage(t, 3.25, 2.0, 0.141)
        self.assertTrue(np.all(f[t < 0] == 0))
        self.assertTrue(np.all(np.diff(f[t >= 0]) >= -1e-12))
        self.assertGreater(f[-1], 0.999)

    def test_setra(self):
        self.assertAlmostEqual(float(M.v85_setra(60.0, 102.0)), 58.5, delta=0.1)   # Cerema 2018 p. 8
        self.assertAlmostEqual(float(M.v85_setra(40.0, 102.0)), 43.1, delta=0.1)   # calcul C3

    def test_v_courbe(self):
        al, at = np.array([3.33]), np.array([4.5])
        vb = M.v_bosetti(60.0, al, at)
        self.assertTrue(np.allclose(M.v_courbe(60.0, al, at, True, 1.0, 102), vb))
        self.assertTrue(np.all(M.v_courbe(60.0, al, at, False, 1.0, 102) >= vb))
        # règle continue en R0 pour κ = 1 si la frontière vaut la V85 Sétra en R0
        k = 43.1 / 3.6 / float(M.v85_setra(40.0, 102.0) / 3.6)
        self.assertAlmostEqual(k, 1.0, delta=0.01)

    def test_decel_cible(self):
        self.assertEqual(float(M.decel_cible(5.0, 10.0, 8.0)), 0.0)
        self.assertAlmostEqual(float(M.decel_cible(10.0, 25.0, 5.0)), (100 - 25) / 50.0)

    def test_borne_gg(self):
        a = M.borne_gg(np.array([3.0, -3.0]), np.array([2.0, 2.0]), np.array([3.0, 3.0]), np.array([4.0, 4.0]),
                       np.array([4.0, 4.0]))
        self.assertAlmostEqual(float(a[0]), 1.5)
        self.assertAlmostEqual(float(a[1]), -2.0)


class TestUrgenceJaune(unittest.TestCase):
    def test_looming(self):
        self.assertAlmostEqual(float(M.looming(15.0, 10.0, 25.0)), 0.2)
        self.assertEqual(float(M.looming(10.0, 15.0, 25.0)), 0.0)

    def test_prediction_markkula_obstacle_fixe(self):
        t02, tc = M.prediction_markkula(50.0, 10.0, 0.0, 0.0)
        self.assertAlmostEqual(tc, 5.0, delta=0.03)
        self.assertAlmostEqual(t02, 0.0, delta=0.03)      # 10/50 = 0,2 s⁻¹ dès maintenant

    def test_decel_requise(self):
        self.assertAlmostEqual(float(M.decel_requise(20.0, 10.0, 0.0, 0.0)), 2.5)
        # meneur qui freine jusqu'à l'arrêt
        self.assertAlmostEqual(float(M.decel_requise(20.0, 10.0, 10.0, -5.0)), 100 / (2 * 30.0))

    def test_decision_jaune(self):
        ar, dec = M.decision_jaune(np.array([1.0, 6.0, 3.5]), np.array([4.0, 4.0, 4.0]), np.array([10.0, 60.0, 35.0]),
                                   np.array([10.0, 10.0, 10.0]), np.array([6.7, 6.7, 6.7]), 3.0)
        self.assertEqual(list(ar), [False, True, False])
        ar2, _ = M.decision_jaune(np.array([3.5]), np.array([4.0]), np.array([35.0]), np.array([10.0]), np.array([6.7]), 3.0,
                                  option_h11=True)
        self.assertTrue(bool(ar2[0]))
        # arrêt physiquement impossible : passe
        ar3, _ = M.decision_jaune(np.array([6.0]), np.array([4.0]), np.array([5.0]), np.array([10.0]), np.array([6.7]), 3.0)
        self.assertFalse(bool(ar3[0]))


if __name__ == "__main__":
    unittest.main()
