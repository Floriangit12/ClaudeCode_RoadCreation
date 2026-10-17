"""Tests du tirage des conducteurs (copule) et des véhicules (prototype v0.2).

  python -m unittest discover -s recon/trafic/tests -v

v0.2 (relecture adverse du 17/10/2026) : on teste des PROPRIÉTÉS, pas la formule qui a servi à construire la
valeur : ordres entre grandeurs liées, marges publiées des grandeurs construites par incrément, troncatures,
corrélation intra-groupe < 1, lien distraction-vigilance, population de véhicules (loi conjointe, parc).
"""
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototype"))
from parametres import Parametres  # noqa: E402
from conducteurs import T_suivi, distrait_a_l_evenement, profil_style, tirer_conducteurs, v0_reseau  # noqa: E402
from vehicules import a_max, d_max_eff, tirer_vehicules  # noqa: E402
import lois  # noqa: E402


class TestConducteurs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P = Parametres()
        cls.pop = tirer_conducteurs(cls.P, 100000, np.random.default_rng(123))

    def test_marges_sourcees(self):
        """Les lois marginales tirées directement sont celles de parametres_modele.json (KS < 0,01 sur 100 000)."""
        for pid in ("PER.tpr.anticipe", "LON.tiv.moyen_conducteur_urbain", "TAC.creneau.facteur_conducteur",
                    "LAT.courbe.alat_max_conducteur", "LON.acc.demarrage_pic", "LON.tiv.ecart_arret"):
            p = self.P.p(pid)
            x = np.sort(self.pop[pid])
            F = lois.cdf(p["loi"], p["parametres"], x)
            ks = float(np.max(np.abs(F - np.arange(1, x.size + 1) / x.size)))
            self.assertLess(ks, 0.01, pid)

    def test_ordres_sans_croisement(self):
        """Grandeurs ordonnées (v0.1 : 4,65 % de TPR anticipés > TPR inattendus, 0,85 % de a1 < b, 0,14 % de TIV min > moyen)."""
        ant = self.pop["PER.tpr.anticipe"]
        for pid in ("PER.tpr.inattendu_signal", "PER.feu.tpr_jaune", "PER.tpr.surprise_obstacle"):
            self.assertTrue(np.all(self.pop[pid] >= ant), pid)
        b = np.maximum(self.pop["LON.dec.max_courante_urbain"], self.pop["LON.dec.max_courante_autoroute"])
        self.assertTrue(np.all(self.pop["LON.dec.urgence_max_markkula"] >= b))
        self.assertTrue(np.all(self.pop["LON.dec.urgence_equivalente"] >= b))
        for r in ("urbain", "autoroute"):
            self.assertTrue(np.all(self.pop[f"LON.tiv.min_conducteur_{r}"] <= self.pop[f"LON.tiv.moyen_conducteur_{r}"]))
        # les planchers ne déplacent qu'une petite part de la loi publiée
        self.assertLess(self.pop["_plancher:LON.dec.urgence_max_markkula"], 0.03)
        self.assertLess(self.pop["_plancher:LON.dec.urgence_equivalente"], 0.06)

    def test_tpr_incrementes_gardent_les_moments_publies(self):
        """TPR construits par incrément : moyenne et écart-type publiés (NCHRP 400) à ± 3 % et ± 6 %."""
        for pid in ("PER.tpr.inattendu_signal", "PER.feu.tpr_jaune", "PER.tpr.surprise_obstacle"):
            m = lois.moments(self.P.p(pid)["loi"], self.P.par(pid))
            x = self.pop[pid]
            self.assertAlmostEqual(float(x.mean()), m["moyenne"], delta=0.03 * m["moyenne"], msg=pid)
            self.assertAlmostEqual(float(x.std()), m["ecart_type"], delta=0.06 * m["ecart_type"], msg=pid)

    def test_correlation_intra_groupe_inferieure_a_1(self):
        """H-01 complétée : deux paramètres d'un même groupe ne sont plus de même rang (v0.1 : Spearman = 1,000)."""
        r = stats.spearmanr(self.pop["LAT.courbe.alpha_deux_tiers"], self.pop["LAT.courbe.alat_max_conducteur"])[0]
        self.assertLess(r, 0.9)
        self.assertGreater(r, 0.4)

    def test_troncatures(self):
        """Queues coupées : GEV de Huang au 99e centile, décélération équivalente ≤ 1,0 g, v0 ≥ P5 de la loi ONISR."""
        self.assertLessEqual(float(self.pop["LON.dec.max_courante_autoroute"].max()), 5.72)
        self.assertLessEqual(float(self.pop["LON.acc.max_suivi_autoroute"].max()), 2.52)
        self.assertLessEqual(float(self.pop["LON.dec.urgence_equivalente"].max()), 10.0)
        p5 = float(self.P.quantile("LON.vit.artere_centre_ville_50", [0.05])[0])
        self.assertGreaterEqual(float(self.pop["LON.vit.artere_centre_ville_50"].min()), p5 - 1e-6)

    def test_dependances(self):
        """Signes des corrélations voulues par les charges (H-01) : vitesse-TIV négative, TPR indépendants du style."""
        r1 = stats.spearmanr(self.pop["LON.vit.artere_centre_ville_50"], self.pop["LON.tiv.moyen_conducteur_urbain"])[0]
        self.assertLess(r1, -0.1)
        r2 = stats.spearmanr(self.pop["S"], self.pop["PER.tpr.anticipe"])[0]
        self.assertLess(abs(r2), 0.02)

    def test_T_suivi_par_reseau(self):
        """T_suivi > 0 ; v_ref = médiane du réseau : à TIV égal, T est plus grand hors agglomération (s0 / v plus petit)."""
        Tu = T_suivi(self.P, self.pop, "artere_centre_ville_50")
        Tr = T_suivi(self.P, self.pop, "route_2_3_voies_80")
        self.assertTrue(np.all(Tu > 0.0))
        self.assertTrue(np.all(Tr > Tu))

    def test_distraction_liee_a_la_vigilance(self):
        """H-18 : probabilité moyenne 8,3 % (± 0,6 point sur 40 000 tirages), plus forte en vigilance basse."""
        rng = np.random.default_rng(3)
        V = np.random.default_rng(4).standard_normal(40000)
        d = np.array([distrait_a_l_evenement(self.P, float(v), rng) for v in V])
        self.assertAlmostEqual(float(d.mean()), self.P.v("distraction_part_temps_FR"), delta=0.006)
        self.assertGreater(float(d[V < -1.28].mean()), 3 * float(d[V > 1.28].mean()))

    def test_profils(self):
        lab = profil_style(self.pop["S"])
        parts = {k: float(np.mean(lab == k)) for k in ("prudent", "moyen", "presse", "agressif")}
        self.assertAlmostEqual(parts["prudent"], 0.25, delta=0.01)
        self.assertAlmostEqual(parts["agressif"], 0.0668, delta=0.005)

    def test_v0_reseau_tronque(self):
        """v0 artère : loi ONISR N(41,2 ; 8,41) tronquée sous son P5 : moyenne ≈ 42,1 km/h (calcul de la normale tronquée)."""
        v0 = v0_reseau(self.P, self.pop, "artere_centre_ville_50") * 3.6
        par = self.P.par("LON.vit.artere_centre_ville_50")
        a = stats.norm.ppf(0.05)
        m_tr = par["moyenne"] + par["ecart_type"] * stats.norm.pdf(a) / 0.95
        self.assertAlmostEqual(float(v0.mean()), m_tr, delta=0.2)


class TestVehicules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P = Parametres()
        cls.veh = tirer_vehicules(cls.P, 4000, 5, np.random.default_rng(5))

    def test_amax_identique_dynamique(self):
        """La version numpy de a_max(v) est identique à dynamique.Vehicule.acceleration_max (µ = 1)."""
        n = 200
        veh = {k: (v[:n] if isinstance(v, (np.ndarray, list)) else v) for k, v in self.veh.items()}
        for v in (0.0, 2.0, 13.9, 25.0, 45.0):
            a_vec = a_max(veh, np.full(n, v), mu=np.ones(n))
            a_ref = np.array([o.acceleration_max(v) for o in veh["objets"]])
            self.assertTrue(np.allclose(a_vec, a_ref, atol=1e-9), v)

    def test_freinage_du_parc(self):
        """Parc en circulation (VP-FREIN-DMAX-SEC-PARC, Greibe) : d_max dans [8,4 ; 10,9] et ≤ µ g ; plus faible que la loi ADAC."""
        d = d_max_eff(self.veh)
        self.assertTrue(np.all(d <= self.veh["mu"] * 9.81 + 1e-9))
        self.assertTrue(np.all((self.veh["d_max"] >= 8.4) & (self.veh["d_max"] <= 10.9)))
        adac = self.P.par("VEH.VP-FREIN-DMAX-SEC")["moyenne"]
        self.assertLess(float(self.veh["d_max"].mean()), adac - 1.0)

    def test_parts_de_familles_du_parc(self):
        """Familles ramenées au parc en circulation (SDES 2026) à ± 1,5 point sur 4 000 tirages."""
        cible = {"electrique": 0.0353, "thermique_auto_hybride": 0.0943}
        for f, p in cible.items():
            self.assertAlmostEqual(float(np.mean(self.veh["famille"] == f)), p, delta=0.015, msg=f)

    def test_loi_conjointe_masse_puissance(self):
        """Tirage conjoint : la corrélation masse - puissance des combinaisons AEE est conservée (positive) et les queues ne
        sont plus coupées à [P5 ; P95] (v0.1)."""
        m = self.veh["masse"]
        p = self.veh["puissance_W"]
        self.assertGreater(stats.spearmanr(m, p)[0], 0.3)
        self.assertGreater(float(np.mean(m < 1012.0)), 0.005)      # P5 de la masse des citadines (v0.1 : borne dure)


if __name__ == "__main__":
    unittest.main()
