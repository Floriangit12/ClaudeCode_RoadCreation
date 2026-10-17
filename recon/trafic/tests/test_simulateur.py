"""Tests du simulateur et des scénarios (prototype v0.2 ; environ 2 min).

  python -m unittest discover -s recon/trafic/tests -v

v0.2 (relecture adverse du 17/10/2026) :
  - propriétés vérifiées à l'échelle NOMINALE et sur plusieurs graines (S1 : 5 graines × 200 files) ;
  - jerk : MAXIMUM hors démarrage (P-02), hors urgence, hors capture d'attention P-08 (exclue explicitement) ;
  - collisions : choc inélastique (quantité de mouvement conservée), primaires / secondaires ;
  - un conducteur juge un freinage « inattendu » avec SON b, pas celui du meneur ;
  - pente propre à chaque itinéraire ;
  - régressions sur des sorties NON utilisées au calage (TIV des rangs 3-4, pics des rangs 2-3 : Salles 2020).
Les contrôles de mise en œuvre (vrais par construction) sont nommés « controle_* ».
"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototype"))
from parametres import Parametres  # noqa: E402
from route import Feu, Route  # noqa: E402
from simulateur import Simulation  # noqa: E402
from vehicules import a_max  # noqa: E402
import analyse as A  # noqa: E402
import scenarios as SC  # noqa: E402


def libres(P, n=50, graine=11, v_ins=None, route=None, **opt):
    route = route or Route("droite", voie=0, longueur=1500.0, reseau="artere_centre_ville_50")
    pop, veh = SC.tirer_agents(P, n, graine)
    agents = {"route": np.zeros(n, int), "couloir": np.arange(n), "t_insert": np.zeros(n), "s_insert": np.zeros(n),
              "v_insert": np.zeros(n) if v_ins is None else v_ins, "pop": pop, "veh": veh}
    return Simulation(P, [route], agents, graine=graine, **opt)


def pilotes(P, s_ins, v_ins, profils, graine=2, longueur=2000.0, reseau="route_2_3_voies_80", pilote=None, **opt):
    """Agents sur un même couloir ; profils[k] = accélération imposée (None : conducteur libre)."""
    n = len(s_ins)
    pop, veh = SC.tirer_agents(P, n, graine)
    pil = np.array([p is not None for p in profils]) if pilote is None else np.asarray(pilote)

    def profil(t, idx, v):
        return np.array([profils[i](t) if profils[i] is not None else 0.0 for i in idx])
    agents = {"route": np.zeros(n, int), "couloir": np.zeros(n, int), "t_insert": np.zeros(n), "s_insert": np.asarray(s_ins, float),
              "v_insert": np.asarray(v_ins, float), "pop": pop, "veh": veh, "pilote": pil, "profil_pilote": profil}
    opt.setdefault("hdm", False)
    return Simulation(P, [Route("d", 0, longueur, reseau)], agents, graine=graine, **opt)


class TestSimulateur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P = Parametres()

    def test_determinisme(self):
        """Même graine -> trajectoires identiques au bit près ; autre graine -> différentes."""
        a, _ = SC.s1_file_feu(self.P, n_files=5, graine=3)
        b, _ = SC.s1_file_feu(self.P, n_files=5, graine=3)
        ta, tb = a.traces(), b.traces()
        for k in ("s", "v", "a"):
            self.assertTrue(np.array_equal(ta[k], tb[k], equal_nan=True))
        c, _ = SC.s1_file_feu(self.P, n_files=5, graine=4)
        self.assertFalse(np.array_equal(ta["s"], c.traces()["s"], equal_nan=True))

    def test_vitesse_libre_et_capacite(self):
        """Route libre : la vitesse tend vers v0 sans le dépasser de plus de 0,3 m/s ; a ≤ a_max(v) du véhicule."""
        sim = libres(self.P)
        sim.executer(90.0)
        tr = sim.traces()
        v = tr["v"]
        self.assertTrue(np.all(np.nanmax(v, axis=0) <= sim.v0 + 0.3))
        for k in range(1, v.shape[0], 25):
            m = np.isfinite(v[k - 1]) & np.isfinite(tr["a"][k])
            amax = a_max(sim.veh, np.nan_to_num(v[k - 1]).astype(float))
            self.assertTrue(np.all(tr["a"][k][m] <= amax[m] + 1e-3))

    def test_pente_par_itineraire(self):
        """Chaque agent utilise la pente de SON itinéraire (v0.1 : routes[0].pente pour tous)."""
        n = 40
        pop, veh = SC.tirer_agents(self.P, n, 4)
        r0 = Route("plat", 0, 800.0, "artere_centre_ville_50", pente=0.0)
        r1 = Route("rampe", 1, 800.0, "artere_centre_ville_50", pente=0.08)
        agents = {"route": np.repeat([0, 1], n // 2), "couloir": np.arange(n), "t_insert": np.zeros(n), "s_insert": np.zeros(n),
                  "v_insert": np.zeros(n), "pop": pop, "veh": veh}
        sim = Simulation(self.P, [r0, r1], agents, graine=4)
        self.assertTrue(np.all(sim.pente_agent[: n // 2] == 0.0) and np.all(sim.pente_agent[n // 2:] == 0.08))

    def test_integration_balistique(self):
        """Pilote à accélération constante : s = v0 t + a t²/2 exactement (intégration balistique)."""
        sim = pilotes(self.P, [0.0], [10.0], [lambda t: -1.0], longueur=500.0, reseau="artere_centre_ville_50")
        sim.executer(5.0)
        self.assertAlmostEqual(float(sim.s[0]), 10 * 5 - 0.5 * 25, places=6)
        self.assertAlmostEqual(float(sim.v[0]), 5.0, places=9)

    def test_choc_inelastique_et_secondaire(self):
        """Deux pilotes : le suiveur heurte le meneur arrêté. Quantité de mouvement conservée au choc, les deux deviennent
        accidentés et freinent à d_max ; un troisième véhicule qui heurte le suiveur est compté comme collision SECONDAIRE."""
        P = self.P
        sim = pilotes(P, [200.0, 130.0, 60.0], [0.0, 15.0, 15.0], [lambda t: 0.0, lambda t: 0.0, lambda t: 0.0])
        while not sim.collisions and sim.t < 8.0:
            sim.pas()
        self.assertEqual(len(sim.collisions), 1)
        c = sim.collisions[0]
        i, j = c["agent"], c["meneur"]
        self.assertFalse(c["secondaire"])
        self.assertTrue(sim.accidente[i] and sim.accidente[j])
        # au pas du choc : vitesse commune m_i v_i / (m_i + m_j) (meneur à l'arrêt, suiveur à 15 m/s)
        vc_attendu = sim.masse[i] * 15.0 / (sim.masse[i] + sim.masse[j])
        self.assertAlmostEqual(float(sim.v[j]), vc_attendu, places=6)
        self.assertAlmostEqual(float(sim.v[i]), vc_attendu, places=6)
        sim.executer(15.0)
        self.assertEqual(len(sim.collisions), 1)
        self.assertGreaterEqual(len(sim.collisions_secondaires), 1)
        self.assertTrue(all(x["secondaire"] for x in sim.collisions_secondaires))

    def test_inattendu_juge_avec_le_b_du_suiveur(self):
        """Un meneur (pilote) freine à 3,0 m/s² depuis 20 m/s : si le b du SUIVEUR est inférieur, c'est un événement
        inattendu (réponse au TPR « signal inattendu »), même si le b privé du meneur est supérieur à 3."""
        P = self.P
        sim = pilotes(P, [300.0, 255.0], [20.0, 20.0], [lambda t: (-3.0 if t >= 10.0 else 0.0), None], distraction=False)
        sim.b[0], sim.b[1] = 5.0, 2.0
        sim.executer(16.0)
        self.assertTrue(any(r["agent"] == 1 for r in sim.journal["reponse"]))

    def test_arret_au_rouge(self):
        """Un feu rouge permanent : aucun franchissement, arrêt à 1 m de la ligne (± 1 m), aucune collision."""
        route = Route("feu", voie=0, longueur=600.0, reseau="artere_centre_ville_50", feux=[Feu(s=300.0, t_vert=np.inf)])
        sim = libres(self.P, n=40, route=route, v_ins=None)
        sim.executer(80.0)
        self.assertTrue(np.all(sim.s < 300.0))
        self.assertTrue(np.all(np.abs((300.0 - sim.s) - 1.0) < 1.0))
        self.assertEqual(len(sim.collisions), 0)

    def test_file_feu_nominale_5_graines(self):
        """V-24 à l'échelle nominale : S1, 5 graines × 200 files, aucune collision primaire ; débit 1 800 ± 90 /h."""
        for g in (1, 2, 3, 4, 5):
            sim, meta = SC.s1_file_feu(self.P, n_files=200, graine=g, enregistrer=False)
            self.assertEqual(len(sim.collisions), 0, f"graine {g}")
            self.assertTrue(np.all(sim.s > 200.0))
            det = sim.detections_tableau()
            tc = np.full(sim.N, np.nan)
            tc[det[:, 0].astype(int)] = det[:, 3]
            h = np.diff(np.concatenate([np.zeros((200, 1)), tc.reshape(200, 20)], axis=1), axis=1)
            self.assertAlmostEqual(3600.0 / float(np.nanmean(h[:, 4:12])), 1800.0, delta=90.0)

    def test_T_decharge_au_moins_intervalle_d_action(self):
        """H-17 : en décharge, T_i ≥ Δ_a,i (TPR anticipé) à chaque pas (v0.1 : T < Δ_a pour 35 % des conducteurs)."""
        sim, _ = SC.s1_file_feu(self.P, n_files=30, graine=6)
        T = sim.traces()["T"]
        m = np.isfinite(T)
        self.assertTrue(np.all((T - sim.tpr_ant[None, :])[m] >= -1e-6))

    def test_jerk_maximal_nominal(self):
        """Jerk : MAXIMUM ≤ 1,5 m/s³ hors démarrage (P-02), hors urgence, hors capture P-08 et hors accidentés (S1 nominal)."""
        sim, meta = SC.s1_file_feu(self.P, n_files=200, graine=1)
        _, _, j_nom = A.jerks(sim, sim.traces())
        self.assertGreater(j_nom.size, 10000)
        self.assertLessEqual(float(j_nom.max()), self.P.v("jerk_confort") + 1e-6)

    def test_regression_rangs_non_cales(self):
        """Sorties NON utilisées au calage (calage : pic du rang 1, TIV moyen des rangs 5-12, démarrage isolé) :
        TIV des rangs 3 et 4 dans la mesure de Salles 2020 fig. 10 ± 0,2 s ; pics des rangs 2 et 3 (fig. 8a) ± 0,15 m/s²."""
        sim, meta = SC.s1_file_feu(self.P, n_files=200, graine=2)
        r = A.s1_modele(sim, meta)
        tf = self.P.par("VAL.tiv.file_feu")
        self.assertAlmostEqual(r["tiv_moyen_par_rang_s"][2], tf["rang3"], delta=0.2)
        self.assertGreaterEqual(r["tiv_moyen_par_rang_s"][3], tf["rang4_plus"][0] - 0.2)
        self.assertLessEqual(r["tiv_moyen_par_rang_s"][3], tf["rang4_plus"][1] + 0.2)
        pk = self.P.par("VAL.acc.demarrage_file")
        self.assertAlmostEqual(r["pic_acc_moyen_par_rang_ms2"][1], pk["rang2"], delta=0.15)
        self.assertAlmostEqual(r["pic_acc_moyen_par_rang_ms2"][2], pk["rang3"], delta=0.15)

    def test_courbe_alat(self):
        """Courbe R = 60 m : aucun conducteur ne dépasse son accélération latérale maximale (Bosetti)."""
        sim, meta = SC.s4_courbe(self.P, n=150, graine=5)
        tr = sim.traces()
        mil = 0.5 * (meta["s_debut"] + meta["s_fin"])
        for i in range(sim.N):
            s, v = tr["s"][:, i], tr["v"][:, i]
            ok = np.isfinite(s)
            vm = float(np.interp(mil, s[ok], v[ok]))
            self.assertLessEqual(vm * vm / meta["R"], sim.alat[i] + 0.05)

    def test_stop_securite(self):
        """S3 (court) : aucune collision, franchissements sans engagement rares ; controle : tout créneau accepté respecte
        t_c,i (condition codée : contrôle de mise en œuvre, pas une validation)."""
        import sumo_scenarios as SS
        c = SC.CONVENTIONS["S3"]
        d0 = c["duree_s"]
        c["duree_s"] = 900.0
        try:
            sim, meta = SC.s3_stop(self.P, SS.geometrie_s3(), n_rep=2)
        finally:
            c["duree_s"] = d0
        acc = [x for x in sim.journal["creneau"] if x["accepte"]]
        self.assertGreater(len(acc), 10)
        self.assertTrue(all(x["lag"] >= x["tc"] - 1e-9 for x in acc))
        n_sec = int(np.sum(sim.route == 1))
        self.assertLessEqual(len(sim.journal["stop_franchi_sans_engagement"]), max(1, int(0.02 * n_sec)))
        self.assertEqual(len(sim.collisions), 0)


if __name__ == "__main__":
    unittest.main()
