"""Simulateur à pas fixe du modèle « conducteur + véhicule » (prototype v0.2, conception § 2.2).

Δt = 0,1 s, intégration balistique, déterministe à graine fixée. Tous les agents d'une simulation sont
traités en tableaux numpy ; plusieurs couloirs indépendants (réplications) partagent la même géométrie.

Couches (conception § 2) :
  PER  perception : état du meneur figé entre deux points d'action (Δ_a,i = TPR anticipé) et extrapolé
       à accélération constante ; erreurs de Wiener du HDM (V_s, r_c, τ̃) ; mise à jour immédiate si la
       situation vraie exige ε de freinage en plus (logique EIDM) ; événements (freinage du meneur au-delà
       de sa décélération habituelle) perçus après le TPR « signal inattendu » ou selon la cinématique de
       Markkula (t0,2, α_B, t_C).
  TAC  feux (rouge, décision au jaune FHWA + option H-11), STOP (3 modalités, créneau critique Certu ×
       facteur du conducteur, freinage imposé au prioritaire ≤ son b : H-10), ralentisseurs, courbes.
  LON  IIDM + CAH, T contextuel (décharge r·T_suivi puis relaxation), facteur de démarrage EIDM, départ
       après TPR anticipé, urgence de Markkula (rampe j_B = k_B τ_B⁻¹ jusqu'à a1), jerk borné hors urgence.
  LAT  vitesse en courbe (§ 7.1) et triangle g-g du conducteur (§ 7.2) ; la commande latérale est dans
       lateral.py (post-traitement, scénario de la courbe).
  VEH  a ≤ a_max(v, pente, µ) du véhicule ; décélération ≤ min(d_max, µ g) ; cercle de friction.
  COL  collisions : choc inélastique (quantité de mouvement conservée), véhicules accidentés freinés à d_max
       jusqu'à l'arrêt ; collision primaire (meneur intact) ou secondaire (meneur déjà accidenté).

v0.2 (relecture adverse du 17/10/2026) : tous les seuils sont lus dans parametres.py (conventions déclarées) ;
un conducteur ne lit plus les paramètres privés d'autrui (« inattendu » jugé avec son propre b ; H-10 avec un
prioritaire médian) ; T_i ≥ intervalle des points d'action (H-17) ; distraction liée à la vigilance (H-18) ;
pente propre à l'itinéraire de chaque agent ; feux stop au seuil de détection (convention, pas une norme).
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

import modele as M
import lois
from conducteurs import RESEAUX, T_suivi, distrait_a_l_evenement, v0_reseau
from parametres import G, Parametres
from vehicules import a_max as veh_a_max, d_max_eff

ETAT_STOP = {"hors": 0, "approche": 1, "arrete": 2, "recherche": 3, "engage": 4}


def p85_bosetti_R0(P: Parametres, R0: float, n: int = 20000, graine: int = 20261017) -> float:
    """P85 de la frontière de Bosetti au rayon R0 sur une population de référence (calcul C3)."""
    rng = np.random.default_rng(graine)
    from scipy import stats
    g = P.groupes()["courbe"]
    S = rng.standard_normal(n)
    Y = g["charge"] * S + math.sqrt(1 - g["charge"] ** 2) * rng.standard_normal(n)
    u = stats.norm.cdf(Y)
    al = np.asarray(P.quantile("LAT.courbe.alpha_deux_tiers", u))
    at = np.asarray(P.quantile("LAT.courbe.alat_max_conducteur", u))
    return float(np.quantile(M.v_bosetti(R0, al, at), 0.85))


class Simulation:
    OPTIONS = {"mode_urgence": "markkula", "hdm": True, "option_h11": False, "reaction_depart": None,
               "enregistrer": True, "t0": 0.0, "distraction": True, "facteur_a": 1.0, "h10": True,
               "ralent_variante": None, "T_min_action": None}

    def __init__(self, P: Parametres, routes: list, agents: dict, graine: int = 0, **options):
        self.P = P
        self.routes = routes
        self.opt = dict(self.OPTIONS, **options)
        if self.opt["reaction_depart"] is None:
            self.opt["reaction_depart"] = P.v("reaction_depart_feu")
        self.dt = float(P.v("pas_s"))
        self.t = float(self.opt["t0"])
        self.rng = np.random.default_rng(graine)
        self.rng_ev = np.random.default_rng([graine, 1])
        n = len(agents["route"])
        self.N = n
        self.route = np.asarray(agents["route"], int)
        self.couloir = np.asarray(agents["couloir"], int)
        self.t_insert = np.asarray(agents["t_insert"], float)
        self.s_insert = np.asarray(agents["s_insert"], float)
        self.v_insert = np.asarray(agents["v_insert"], float)
        self.force = np.asarray(agents.get("force", np.ones(n, bool)), bool)
        self.pilote = np.asarray(agents.get("pilote", np.zeros(n, bool)), bool)
        self.profil_pilote = agents.get("profil_pilote")
        self.arret_initial = np.asarray(agents.get("arret_en_file", np.zeros(n, bool)), bool)
        pop, veh = agents["pop"], agents["veh"]
        self.pop, self.veh = pop, veh
        self._parametres_agents(pop, veh)
        self._etat_initial()

    # ------------------------------------------------------------------ paramètres par agent
    def _parametres_agents(self, pop, veh):
        P, n = self.P, self.N
        self.L = np.asarray(veh["longueur"], float)
        self.v0 = np.zeros(n)
        self.Ts = np.zeros(n)
        self.b = np.zeros(n)
        self.agglo_route = np.zeros(n, bool)
        self.pente_agent = np.zeros(n)
        for r_i, r in enumerate(self.routes):
            m = self.route == r_i
            if not m.any():
                continue
            res = RESEAUX[r.reseau]
            self.v0[m] = v0_reseau(P, pop, r.reseau)[m]
            # T_suivi avec v_ref = médiane de la vitesse désirée du réseau (v0.1 : 12 m/s partout)
            self.Ts[m] = T_suivi(P, pop, r.reseau)[m]
            if res["tiv"] == "autoroute":
                self.b[m] = pop["LON.dec.max_courante_autoroute"][m]
            else:
                self.b[m] = pop["LON.dec.max_courante_urbain"][m]
            self.agglo_route[m] = res["agglo"]
            self.pente_agent[m] = r.pente                 # v0.1 : routes[0].pente pour tous les agents
        self.Ts = np.maximum(self.Ts, 0.1)
        self.s0 = pop["LON.tiv.ecart_arret"]
        self.a = pop["LON.acc.demarrage_pic"] * float(self.opt["facteur_a"])
        self.a1 = pop["LON.dec.urgence_max_markkula"]
        self.dec_equiv = pop["LON.dec.urgence_equivalente"]
        self.tpr_ant = pop["PER.tpr.anticipe"]
        self.tpr_sig = pop["PER.tpr.inattendu_signal"]
        self.tpr_jaune = pop["PER.feu.tpr_jaune"]
        self.alpha = pop["LAT.courbe.alpha_deux_tiers"]
        self.alat = pop["LAT.courbe.alat_max_conducteur"]
        self.b_gg = pop["LON.acc.max_conducteur_bosetti"]
        self.c_gg = pop["VAL.dec.max_conducteur_bosetti"]
        self.seuil_jaune = pop["TAC.feu.seuil_arret_jaune"]
        self.fac_creneau = pop["TAC.creneau.facteur_conducteur"]
        self.v_ralent = pop["TAC.ralent.vitesse_franchissement"] / 3.6
        if self.opt["ralent_variante"]:
            # variante régionale (Vias 2021 fig. 23-24) au même rang que la loi nationale
            pr = P.p("TAC.ralent.vitesse_franchissement")
            st = pr["statistiques_publiees"][self.opt["ralent_variante"]]
            u = lois.cdf("normale", pr["parametres"], pop["TAC.ralent.vitesse_franchissement"])
            sd = (st["V85"] - st["moyenne"]) / 1.0364333894937898
            self.v_ralent = np.asarray(lois.quantile("normale", {"moyenne": st["moyenne"], "ecart_type": sd},
                                                     np.clip(u, 1e-6, 1 - 1e-6))) / 3.6
        self.S = pop["S"]
        self.V = pop["V"]
        self.masse = np.asarray(veh["masse"], float)
        self.seuil_loom = float(P.v("markkula_seuil_looming_s-1"))
        kb = P.v("markkula_kB")
        self.kB = np.exp(kb["mu_log"] + kb["sigma_log"] * self.rng_ev.standard_normal(n))
        self.dmax = d_max_eff(veh)
        self.mu = veh["mu"]
        R0 = float(P.v("R0_courbe_m"))
        self.p85_R0 = p85_bosetti_R0(P, R0)
        self.kappa = M.kappa(self.alpha, self.alat, R0, self.p85_R0)
        # vitesse en courbe par agent et par courbe de son itinéraire
        self.v_courbes = {}
        for r_i, r in enumerate(self.routes):
            for c_i, c in enumerate(r.courbes):
                agglo = c.agglo if c.agglo is not None else RESEAUX[r.reseau]["agglo"]
                self.v_courbes[(r_i, c_i)] = M.v_courbe(c.R, self.alpha, self.alat, agglo, self.kappa, r.vlim_setra_kmh)
        # STOP : modalité tirée à la rencontre (facteur style conservé, conception § 5.4)
        from conducteurs import tirer_evenement
        self.stop_modalite = tirer_evenement(P, "TAC.stop.comportement", "stop", self.S, self.rng_ev).astype(int)
        self.stop_v_glisse = tirer_evenement(P, "TAC.stop.vitesse_residuelle_glisse", "stop_vitesse", self.S, self.rng_ev)
        self.stop_modalite_tiree = self.stop_modalite.copy()
        # prioritaire « générique » de H-10 : médianes de la population de chaque itinéraire (un conducteur ne
        # connaît pas les paramètres privés du prioritaire réel)
        self.generique = {}
        for r_i in range(len(self.routes)):
            m = self.route == r_i
            if m.any():
                self.generique[r_i] = {k: float(np.median(x[m])) for k, x in
                                       (("v0", self.v0), ("T", self.Ts), ("s0", self.s0), ("a", self.a), ("b", self.b))}

    def _etat_initial(self):
        n = self.N
        z = lambda dt=float: np.zeros(n, dt)
        self.actif, self.insere, self.fini = z(bool), z(bool), z(bool)
        self.s, self.v, self.a_app, self.a_eff = z(), z(), z(), z()
        self.t_next = z()
        self.snap_lid = np.full(n, -1)
        self.snap_voie = np.full(n, -1)
        self.snap_s, self.snap_v, self.snap_a, self.snap_t = z(), z(), z(), z()
        self.ws, self.wdv = self.rng.standard_normal(n), self.rng.standard_normal(n)
        # départ
        self.attente, self.t_dep, self.t_start = z(bool), np.full(n, np.inf), np.full(n, -np.inf)
        self.pre_autorise = np.full(n, -np.inf)
        self.parti = z(bool)
        self.arret_en_file = self.arret_initial.copy()
        self.decharge = z(bool)
        self.t_relax = np.full(n, np.inf)
        self.T_cur = self.Ts.copy()
        # événements et urgence
        self.ev_arme, self.ev_actif = np.ones(n, bool), z(bool)
        self.ev_t, self.ev_lid = np.full(n, np.inf), np.full(n, -1)
        self.ev_alpha, self.ev_t02, self.ev_distrait = z(), np.full(n, np.inf), z(bool)
        self.urg, self.urg_jB, self.release_jB, self.urg_cible = z(bool), z(), z(), z()
        self.t_feux_stop = np.full(n, np.inf)
        self.a_min = np.full(n, np.inf)
        self.urg_besoin = z(bool)
        self.t_entree = np.full(n, np.inf)
        self.route_feux = np.array([bool(r.feux) for r in self.routes])
        self.obst_prec = np.full(n, M.INF)
        self.lid_prec = np.full(n, -1)
        self.cible_prec = z(bool)
        self.gap_prec = np.full(n, M.INF)
        self.stop_dec_vu = z(bool)
        self.seuil_feux_stop = float(self.P.v("feux_stop_seuil_ms2"))       # convention (seuil de détection)
        # feux
        self.jaune_ttl, self.jaune_tdec, self.jaune_dec = np.full(n, np.nan), np.full(n, np.inf), np.zeros(n, np.int8)
        self.jaune_vu = z(bool)
        self.feu_vert_vu = z(bool)
        # STOP
        self.stop_etat = np.zeros(n, np.int8)
        self.stop_t_arret = np.full(n, np.inf)
        self.stop_vmin_zone = np.full(n, np.inf)
        self.stop_t_v01 = np.full(n, np.inf)        # premier instant arrêté (v < 0,1 m/s) dans la zone de 3 m
        self.point_action = z(bool)
        # journaux
        self.collisions = []
        self.journal = defaultdict(list)
        self.detections = []
        self.trace = defaultdict(list) if self.opt["enregistrer"] else None
        self.t_trace = []
        self.collision_agent = z(bool)
        self.accidente = z(bool)                    # impliqué dans une collision (suiveur ou heurté)
        self.t_accident = np.full(n, np.inf)
        self.collisions_secondaires = []

    # ------------------------------------------------------------------ outils
    def _coord(self, idx):
        """(voie effective, abscisse effective) pour la recherche du meneur (projection des jonctions)."""
        voie = np.zeros(idx.size, int)
        s_eff = self.s[idx].copy()
        for r_i, r in enumerate(self.routes):
            m = self.route[idx] == r_i
            if not m.any():
                continue
            voie[m] = r.voie
            if r.jonction is not None:
                # projection sur la voie cible : seulement pour un véhicule engagé (ou sans STOP)
                engage = (self.stop_etat[idx] >= ETAT_STOP["engage"]) if r.stops else np.ones(idx.size, bool)
                j = m & (self.s[idx] >= r.jonction.s) & engage
                voie[j] = r.jonction.voie
                s_eff[j] = self.s[idx][j] - r.jonction.s + r.jonction.s_cible
        return voie, s_eff

    def _meneurs(self, idx, voie, s_eff):
        """Meneur de chaque agent (indice global, -1 si aucun) et son abscisse dans le repère du suiveur.
        Un véhicule engagé sur une jonction reste visible sur sa voie d'origine tant que son arrière n'a pas
        dégagé le point de jonction (entrée « fantôme »)."""
        e_ag, e_voie, e_s = [idx], [voie], [s_eff]
        for r_i, r in enumerate(self.routes):
            if r.jonction is None:
                continue
            g = (self.route[idx] == r_i) & (voie == r.jonction.voie) & (self.s[idx] - self.L[idx] < r.jonction.s)
            if g.any():
                e_ag.append(idx[g]); e_voie.append(np.full(int(g.sum()), r.voie)); e_s.append(self.s[idx][g])
        e_ag, e_voie, e_s = np.concatenate(e_ag), np.concatenate(e_voie), np.concatenate(e_s)
        cle = self.couloir[e_ag] * 64 + e_voie
        ordre = np.lexsort((e_s, cle))
        nxt = np.full(e_ag.size, -1)
        meme = cle[ordre][1:] == cle[ordre][:-1]
        nxt[ordre[:-1][meme]] = ordre[1:][meme]
        n = idx.size
        k = nxt[:n]
        lid = np.where(k >= 0, e_ag[np.maximum(k, 0)], -1)
        s_l = np.where(k >= 0, e_s[np.maximum(k, 0)], np.inf)
        return lid, s_l

    def _inserer(self, t):
        cand = np.flatnonzero(~self.insere & (self.t_insert <= t + 1e-9))
        if cand.size == 0:
            return
        act = np.flatnonzero(self.actif)
        voie_a, s_a = self._coord(act) if act.size else (np.array([], int), np.array([]))
        for i in cand:
            r = self.routes[self.route[i]]
            v = self.v_insert[i]
            s = self.s_insert[i]
            if not self.force[i] and act.size:
                m = (self.couloir[act] == self.couloir[i]) & (voie_a == r.voie) & (s_a >= s)
                if m.any():
                    k = np.argmin(s_a[m])
                    j = act[m][k]
                    gap = s_a[m][k] - self.L[j] - s
                    # vitesse d'insertion sûre : s*(v, Δv) ≤ écart (IIDM), comme departSpeed="max" de SUMO
                    A = 1.0 / (2.0 * math.sqrt(self.a[i] * self.b[i]))
                    Bq = self.Ts[i] - self.v[j] * A
                    Cq = self.s0[i] - gap
                    disc = Bq * Bq - 4 * A * Cq
                    v_sure = (-Bq + math.sqrt(disc)) / (2 * A) if disc > 0 else 0.0
                    if v_sure < 1.0:
                        continue
                    v = min(v, v_sure)
            self.insere[i] = self.actif[i] = True
            self.t_entree[i] = t
            self.s[i], self.v[i] = s, v
            self.t_next[i] = t + self.rng.uniform(0, self.tpr_ant[i])
            self.stop_etat[i] = ETAT_STOP["approche"] if r.stops else 0
            act = np.append(act, i)
            voie_a = np.append(voie_a, r.voie)
            s_a = np.append(s_a, s)

    # ------------------------------------------------------------------ un pas
    def pas(self):
        P, dt, t = self.P, self.dt, self.t
        self._inserer(t)
        act = np.flatnonzero(self.actif)
        if act.size == 0:
            self.t = t + dt
            return
        n = act.size
        voie, s_eff = self._coord(act)
        self._voie_courante = voie
        lid, s_l_eff = self._meneurs(act, voie, s_eff)
        has = lid >= 0
        v = self.v[act]
        gap = np.full(n, M.INF)
        vl = v.copy()
        al = np.zeros(n)
        gap[has] = s_l_eff[has] - self.L[lid[has]] - s_eff[has]
        vl[has] = self.v[lid[has]]
        al[has] = self.a_eff[lid[has]]

        # ---------------- PER : événements (freinage du meneur au-delà de sa décélération habituelle)
        # événement inattendu : freinage du meneur au-delà de sa décélération habituelle, sauf s'il s'explique
        # (meneur au pas, < 5 m/s, ou ligne d'arrêt visible devant lui à moins de 50 m) : situation attendue,
        # la poursuite continue s'applique (conception § 3.1, TPR « anticipé »)
        lid0 = np.maximum(lid, 0)
        ll = self.lid_prec[lid0]                     # meneur du meneur (pas précédent)
        ll0 = np.maximum(ll, 0)
        # anticipation sur deux véhicules (HDM, n_a = 1 à 7, Treiber 2006) : le véhicule devant le meneur est arrêté
        # ou a ses feux stop allumés (> 1,3 m/s², R13-H) à moins de 60 m du meneur
        file_visible = (lid >= 0) & (ll >= 0) & (self.gap_prec[lid0] < P.v("h15_d_file_m")) & \
                       ((self.v[ll0] < P.v("h15_v_arrete_ms")) | np.isfinite(self.t_feux_stop[ll0]))
        explique = (vl < P.v("h15_v_meneur_lent_ms")) | (self.obst_prec[lid0] < P.v("h15_d_ligne_m")) | file_visible | self.cible_prec[lid0]
        # « inattendu » jugé avec la décélération habituelle du SUIVEUR (v0.1 : b privé du meneur)
        freine = has & (al < -self.b[act]) & (vl > 0.5) & ~explique
        pil = self.pilote[act] | self.accidente[act]
        self.ev_arme[act[~freine & ~self.ev_actif[act]]] = True
        nouv = freine & self.ev_arme[act] & ~self.ev_actif[act] & ~self.urg[act] & ~pil
        for k in np.flatnonzero(nouv):
            i = act[k]
            self.ev_actif[i], self.ev_arme[i] = True, False
            # le TPR court depuis l'allumage des feux stop du meneur (R13-H : obligatoire au-delà de 1,3 m/s²)
            t_sig = self.t_feux_stop[lid[k]]
            self.ev_t[i] = t_sig if np.isfinite(t_sig) else t
            self.ev_lid[i], self.ev_t02[i] = lid[k], np.inf
            distrait = self.opt["distraction"] and distrait_a_l_evenement(P, float(self.V[i]), self.rng_ev)
            self.ev_distrait[i] = distrait
            if distrait:
                pa = P.par("PER.tpr.markkula.alphaB_yeux_hors_route")
                self.ev_alpha[i] = math.exp(pa["mu_log"] + pa["sigma_log"] * self.rng_ev.standard_normal())
            else:
                pa = P.par("PER.tpr.markkula.alphaB_yeux_sur_menace")
                self.ev_alpha[i] = pa["moyenne"] + pa["ecart_type"] * self.rng_ev.standard_normal()
        reponse = np.zeros(n, bool)
        loom = M.looming(v, vl, gap)
        for k in np.flatnonzero(self.ev_actif[act]):
            i = act[k]
            if lid[k] != self.ev_lid[i]:
                self.ev_actif[i] = False
                continue
            if loom[k] >= self.seuil_loom and not np.isfinite(self.ev_t02[i]):
                self.ev_t02[i] = t
            # réponse ordinaire aux feux stop : TPR « signal inattendu » (NCHRP 400) ; si la situation devient
            # urgente (looming ≥ 0,2 s⁻¹) avant cette réponse, ou si le conducteur ne regarde pas la route,
            # le début du freinage suit la cinématique de Markkula 2016 : t_B = t0,2 + α_B (t_C - t0,2)
            t_tpr = self.ev_t[i] + self.tpr_sig[i]
            t_resp = t_tpr
            if self.opt["mode_urgence"] == "markkula":
                t02r, tcr = M.prediction_markkula(gap[k], v[k], vl[k], al[k], seuil=self.seuil_loom)
                t02 = self.ev_t02[i] if np.isfinite(self.ev_t02[i]) else t + t02r
                urgent = np.isfinite(t02) and (t02 <= t_tpr or self.ev_distrait[i])
                if urgent and np.isfinite(tcr):
                    tC = t + tcr
                    t_resp = max(t02 + self.ev_alpha[i] * (tC - t02), self.ev_t[i] + dt)
                elif self.ev_distrait[i]:
                    t_resp = np.inf          # yeux hors de la route : pas de réponse avant la menace
            if t >= t_resp - 1e-9:
                reponse[k] = True
                self.ev_actif[i] = False
                req = float(M.decel_requise(gap[k], v[k], vl[k], al[k]))
                self.journal["reponse"].append({"agent": int(i), "meneur": int(lid[k]), "t_ev": float(self.ev_t[i]),
                                                "t_rep": t, "delai": t - float(self.ev_t[i]), "looming": float(loom[k]),
                                                "alphaB": float(self.ev_alpha[i]), "distrait": bool(self.ev_distrait[i]),
                                                "decel_requise": req, "v": float(v[k]), "gap": float(gap[k])})
                if loom[k] >= self.seuil_loom or req > self.b[i]:
                    self._entrer_urgence(i, loom[k])
        gele = self.ev_actif[act]

        # ---------------- PER : état perçu (points d'action, ε, Wiener)
        self.point_action[act] = False
        arrete_ = v < P.v("vitesse_arret_ms")          # à l'arrêt, le conducteur guette le départ du meneur
        maj = (t >= self.t_next[act] - 1e-9) | (self.snap_lid[act] != lid) | reponse | arrete_ | (self.snap_voie[act] != voie)
        maj &= ~gele
        self._maj_snap(act, maj, lid, s_l_eff, vl, al, t)
        gap_p, vl_p, al_p = self._percu(act, lid, s_eff, t)
        # ε : la situation vraie exige nettement plus de freinage que la situation perçue
        self._gap_courant = gap
        T_i = self._T_contextuel(act, t)
        a_i = self.a[act] * np.where(self.decharge[act], P.v("facteur_a_decharge"), 1.0)
        dl, cc = P.v("idm_delta"), P.v("cah_c")
        a_true = M.poursuite(v, gap, vl, al, self.v0[act], T_i, self.s0[act], a_i, self.b[act], dl, cc)
        a_perc0 = M.poursuite(v, gap_p, vl_p, al_p, self.v0[act], T_i, self.s0[act], a_i, self.b[act], dl, cc)
        capt = (a_true < a_perc0 - P.v("epsilon_acc")) & ~gele & has
        if capt.any():
            self._maj_snap(act, capt, lid, s_l_eff, vl, al, t)
            gap_p, vl_p, al_p = self._percu(act, lid, s_eff, t)
        if self.opt["hdm"]:
            # erreurs d'estimation du HDM (appliquées en roulant, v > 1 m/s)
            e = math.exp(-dt / P.v("hdm_tau_s"))
            q = math.sqrt(1 - e * e)
            self.ws[act] = e * self.ws[act] + q * self.rng.standard_normal(n)
            self.wdv[act] = e * self.wdv[act] + q * self.rng.standard_normal(n)
            fin = (gap_p < M.INF / 2) & (v > 1.0)
            g_est = np.where(fin, gap_p * np.exp(P.v("hdm_Vs") * self.ws[act]), gap_p)
            dv_est = np.where(fin, (v - vl_p) - gap_p * P.v("hdm_rc_s-1") * self.wdv[act], 0.0)
            gap_p, vl_p = g_est, np.maximum(v - dv_est, 0.0)      # une vitesse perçue reste ≥ 0

        # ---------------- TAC + LON : contraintes
        v0_eff = self.v0[act].copy()
        a_cib = np.full(n, np.inf)              # contraintes cinématiques (vitesses cibles, arrêt au jaune)
        obst = np.full(n, M.INF)                # obstacle fixe virtuel (ligne d'arrêt) : écart pour l'IIDM
        kap = np.zeros(n)
        tp = P.v("tpreview_s")
        for r_i, r in enumerate(self.routes):
            m = self.route[act] == r_i
            if not m.any():
                continue
            sm, vm = self.s[act][m], v[m]
            kap[m] = r.courbure(sm)
            for c_i, c in enumerate(r.courbes):
                vc = self.v_courbes[(r_i, c_i)][act[m]]
                dedans = (sm >= c.s0) & (sm <= c.s1)
                v0_eff[m] = np.where(dedans, np.minimum(v0_eff[m], vc), v0_eff[m])
                d = c.s0 - sm
                av = (d > 0) & (d <= np.maximum(vm * tp, 1.0)) & (vm > vc)
                a_cib[m] = np.where(av, np.minimum(a_cib[m], -M.decel_cible(vm, d, vc)), a_cib[m])
            for rl in r.ralentisseurs:
                vr = np.minimum(self.v_ralent[act[m]], self.v0[act[m]])
                dedans = (sm >= rl.s) & (sm <= rl.s + rl.longueur)
                v0_eff[m] = np.where(dedans, np.minimum(v0_eff[m], vr), v0_eff[m])
                d = rl.s - sm
                av = (d > 0) & (d <= np.maximum(vm * tp, 1.0)) & (vm > vr)
                a_cib[m] = np.where(av, np.minimum(a_cib[m], -M.decel_cible(vm, d, vr)), a_cib[m])
            for f in r.feux:
                self._feu(act, m, f, t, v, obst, a_cib)
            for st in r.stops:
                self._stop(act, m, st, r, t, v, obst, a_cib, voie, s_eff, lid)
        a_w = M.poursuite(v, gap_p, vl_p, al_p, v0_eff, T_i, self.s0[act], a_i, self.b[act], dl, cc)
        a_obst = M.iidm(v, obst, v, v0_eff, T_i, self.s0[act], a_i, self.b[act], dl)
        a_w = np.minimum(a_w, np.where(obst < M.INF / 2, a_obst, np.inf))
        a_w = np.minimum(a_w, a_cib)

        dbg = getattr(self, "debug_agent", None)
        if dbg is not None and dbg in act and getattr(self, "debug_t0", -1) <= t <= getattr(self, "debug_t1", 1e9):
            kd = int(np.flatnonzero(act == dbg)[0])
            print("DBG", round(t, 1), "a_w", round(float(a_w[kd]), 2), "a_true", round(float(a_true[kd]), 2), "obst", round(float(obst[kd]), 1),
                  "gap", round(float(gap[kd]), 2), "gap_p", round(float(gap_p[kd]), 2), "vl", round(float(vl[kd]), 2), "vl_p", round(float(vl_p[kd]), 2),
                  "al", round(float(al[kd]), 2), "al_p", round(float(al_p[kd]), 2), "T", round(float(T_i[kd]), 2), "gele", bool(gele[kd]), "capt", bool(capt[kd]))
        # ---------------- départ après un arrêt (TPR anticipé ; facteur de démarrage EIDM)
        a_w = self._depart(act, v, a_w, has, gap, obst, t)

        # ---------------- urgence par besoin (sans événement) : freinage au-delà de b et menace
        # (meneur réel ou ligne d'arrêt : le looming d'un obstacle fixe vaut v / distance d'arrêt)
        d_obst = np.maximum(obst - self.s0[act], 0.1)
        loom_o = np.where(obst < M.INF / 2, v / d_obst, 0.0)
        self._d_obst = d_obst
        self._obst = obst
        self.obst_prec[act] = obst
        self.lid_prec[act] = lid
        self.gap_prec[act] = gap
        self.cible_prec[act] = a_cib < 0          # le meneur ralentit vers une cible visible (STOP, courbe, dispositif)
        besoin = ~self.urg[act] & ~pil & (a_w < -(self.b[act] + P.v("epsilon_acc"))) & (np.maximum(loom, loom_o) >= self.seuil_loom)
        mrg = P.v("marge_urgence_frac_s0")
        for k in np.flatnonzero(besoin):
            i = act[k]
            req_k = float(M.decel_requise(gap[k], v[k], vl[k], al[k], marge=mrg * self.s0[i]))
            if obst[k] < M.INF / 2:
                req_k = max(req_k, v[k] ** 2 / (2 * d_obst[k]))
            loom = loom.copy(); loom[k] = max(loom[k], loom_o[k])
            self._entrer_urgence(i, loom[k], req=req_k)
            self.journal["urgence_besoin"].append({"agent": int(i), "t": t, "looming": float(loom[k])})

        # ---------------- contrôle : triangle g-g, jerk, urgence
        a_lat = v * v * kap
        urg = self.urg[act]
        # triangle g-g côté accélération ; côté freinage : |a| ≤ c_i seulement (voir rapport : le couplage
        # au freinage interdirait tout freinage quand a_lat atteint a_lat,i)
        a_gg = M.borne_gg(a_w, a_lat, self.b_gg[act], self.c_gg[act], self.alat[act])
        a_gg = np.where(a_w < 0, np.maximum(a_w, -self.c_gg[act]), a_gg)
        a_cmd = np.where(urg, a_w, a_gg)
        a_prev = self.a_app[act]
        jc = P.v("jerk_confort")
        j_bas = np.full(n, jc)
        j_haut = np.full(n, jc)
        en_dem = (t - self.t_start[act]) < P.v("duree_demarrage_s")
        if not P.v("jerk_borne_au_demarrage"):
            j_haut = np.where(en_dem & (a_cmd > 0), np.inf, j_haut)
        rel = a_prev < -self.b[act]
        j_haut = np.where(rel, np.maximum(j_haut, self.release_jB[act]), j_haut)
        # capture d'attention (logique ε de l'EIDM) : si la consigne exige ε de freinage en plus et que la
        # situation est menaçante (looming ≥ 0,2 s⁻¹, meneur ou ligne), la montée du freinage suit l'échelle
        # de Markkula j = k_B τ⁻¹ (plafond 8 m/s³) au lieu du jerk de confort
        lm = np.maximum(loom, loom_o)
        capt_j = (a_cmd < a_prev - P.v("epsilon_acc")) & (lm >= self.seuil_loom)
        j_bas = np.where(capt_j, np.maximum(j_bas, np.minimum(self.kB[act] * lm, P.v("markkula_jB_plafond_ms3"))), j_bas)
        a_new = a_prev + np.clip(a_cmd - a_prev, -j_bas * dt, j_haut * dt)
        # urgence : rampe de Markkula jusqu'à a1 (borné par le véhicule), sortie quand la situation est résolue
        if urg.any():
            ku = np.flatnonzero(urg)
            i_u = act[ku]
            # urgence par besoin : rampe réévaluée à chaque pas avec le looming courant (conducteur attentif)
            bes_u = self.urg_besoin[i_u]
            jb_now = np.maximum(P.v("jerk_confort"), np.minimum(self.kB[i_u] * np.maximum(loom[ku], loom_o[ku]),
                                                                  P.v("markkula_jB_plafond_ms3")))
            self.urg_jB[i_u] = np.where(bes_u, np.maximum(self.urg_jB[i_u], jb_now), self.urg_jB[i_u])
            req = M.decel_requise(gap[ku], v[ku], vl[ku], al[ku], marge=mrg * self.s0[i_u])
            req = np.where(self._obst[ku] < M.INF / 2, np.maximum(req, v[ku] ** 2 / (2 * self._d_obst[ku])), req)
            # urgence par besoin : la cible suit le freinage requis (au moins b_i), bornée par le maximum d'urgence.
            # v0.2 : cible recalculée AVANT la rampe (v0.1 : la cible recalculée n'était jamais appliquée, le freinage
            # restait figé à la valeur d'entrée ; défaut trouvé par le test S3 de la relecture du 17/10/2026)
            bes = self.urg_besoin[i_u]
            cap = np.where(self.opt["mode_urgence"] == "markkula", self.a1[i_u], self.dec_equiv[i_u])
            besoin_dec = np.maximum(np.maximum(req, self.b[i_u]), -a_w[ku])
            self.urg_cible[i_u] = np.where(bes, np.minimum(cap, besoin_dec), self.urg_cible[i_u])
            cible = -np.minimum(self.urg_cible[i_u], self.dmax[i_u])
            a_u = np.maximum(a_prev[ku] - self.urg_jB[i_u] * dt, cible)
            a_u = np.where(a_prev[ku] < cible, np.minimum(a_prev[ku] + self.urg_jB[i_u] * dt, cible), a_u)
            sortie = (v[ku] < P.v("vitesse_arret_ms")) | ((req <= self.b[i_u]) & (a_w[ku] >= a_prev[ku]))
            a_new[ku] = np.where(sortie, a_prev[ku], a_u)
            self.urg[i_u[sortie]] = False
            self.urg_besoin[i_u[sortie]] = False
            self.release_jB[i_u[sortie]] = self.urg_jB[i_u[sortie]]
        pil_k = np.flatnonzero(self.pilote[act])
        if pil_k.size and self.profil_pilote is not None:
            a_new[pil_k] = self.profil_pilote(t, act[pil_k], v[pil_k])

        # ---------------- VEH : capacité du véhicule, adhérence, cercle de friction
        mu_g = self.mu[act] * G
        lat_dispo = np.sqrt(np.maximum(mu_g ** 2 - a_lat ** 2, 0.0))
        amax = np.minimum(veh_a_max(self.veh, v, self.pente_agent[act], idx=act), lat_dispo)
        dmax = np.minimum(self.dmax[act], lat_dispo)
        a_new = np.where(self.pilote[act], a_new, np.clip(a_new, -dmax, amax))
        # véhicules accidentés : freinage à d_max jusqu'à l'arrêt, puis immobiles
        acc_k = self.accidente[act]
        if acc_k.any():
            a_new = np.where(acc_k, np.where(v > 0.0, -dmax, 0.0), a_new)

        # ---------------- intégration balistique
        v_new = v + a_new * dt
        arret = v_new < 0
        ds = np.where(arret, np.where(a_new < 0, v * v / (2 * np.maximum(-a_new, 1e-9)), 0.0), v * dt + 0.5 * a_new * dt * dt)
        v_new = np.maximum(v_new, 0.0)
        s_old = self.s[act].copy()
        self.s[act] = s_old + ds
        self.v[act] = v_new
        self.a_eff[act] = (v_new - v) / dt
        self.a_app[act] = np.where(v_new <= 0.0, np.maximum(a_new, 0.0), a_new)
        self.a_min[act] = np.minimum(self.a_min[act], self.a_eff[act])
        allume = self.a_eff[act] < -self.seuil_feux_stop
        self.t_feux_stop[act[~allume]] = np.inf
        nv_all = act[allume & ~np.isfinite(self.t_feux_stop[act])]
        self.t_feux_stop[nv_all] = t

        # ---------------- collisions (écart net < 0 après le pas, même voie effective)
        voie2, s_eff2 = self._coord(act)
        lid2, s_l2 = self._meneurs(act, voie2, s_eff2)
        gap2 = np.full(n, M.INF)
        h2 = lid2 >= 0
        gap2[h2] = s_l2[h2] - self.L[lid2[h2]] - s_eff2[h2]
        surv = getattr(self, "surveiller", None)
        if surv:
            ids, t0s, t1s = surv
            for k in np.flatnonzero(np.isin(act, ids)):
                if t0s <= t <= t1s:
                    self.journal["surveillance"].append((round(t + dt, 1), int(act[k]), int(self.route[act[k]]), round(float(self.s[act[k]]), 2),
                                                         int(voie2[k]), round(float(s_eff2[k]), 2), round(float(self.v[act[k]]), 2),
                                                         round(float(self.a_eff[act[k]]), 2), int(lid2[k]), round(float(gap2[k]), 2),
                                                         int(self.stop_etat[act[k]]), bool(self.urg[act[k]])))
        fin_route = np.zeros(n, bool)
        for r_i, r in enumerate(self.routes):
            fin_route |= (self.route[act] == r_i) & (self.s[act] >= r.longueur - 2.0)
        col = np.flatnonzero((gap2 < 0) & ~fin_route)
        # traitées de l'avant vers l'arrière de chaque couloir (un choc devant précède le choc derrière)
        col = col[np.argsort(-s_eff2[col])] if col.size > 1 else col
        for k in col:
            i, j = act[k], lid2[k]
            if t - self.t_entree[i] < 1.0 or t - self.t_entree[j] < 1.0:
                # chevauchement à l'insertion (artefact de l'entrée du réseau) : compté à part
                self.journal["collision_insertion"].append({"t": t, "agent": int(i), "meneur": int(j)})
                self.s[i] += gap2[k] - 0.01
                self.v[i] = min(self.v[i], self.v[j])
                continue
            deja = self.accidente[i] and self.accidente[j]
            if not deja and not self.collision_agent[i]:
                # secondaire : le meneur était déjà accidenté avant ce choc
                secondaire = bool(self.accidente[j])
                dv = float(self.v[i] - self.v[j])
                rec = {"t": t + dt, "agent": int(i), "meneur": int(j), "dv": dv, "secondaire": secondaire,
                       "couloir": int(self.couloir[i]), "s": float(self.s[i]), "voie": int(voie2[k]),
                       "etat_stop": int(self.stop_etat[i]), "etat_stop_meneur": int(self.stop_etat[j]),
                       "urg": bool(self.urg[i])}
                (self.collisions_secondaires if secondaire else self.collisions).append(rec)
                self.collision_agent[i] = True
            # choc parfaitement inélastique : vitesse commune qui conserve la quantité de mouvement
            mi, mj = self.masse[i], self.masse[j]
            vc = (mi * self.v[i] + mj * self.v[j]) / (mi + mj)
            self.s[i] += gap2[k] - 0.01
            self.v[i] = self.v[j] = vc
            for x in (i, j):
                if not self.accidente[x]:
                    self.accidente[x] = True
                    self.t_accident[x] = t + dt
                    self.urg[x] = False

        # ---------------- détecteurs, journal STOP, trace, sorties
        for r_i, r in enumerate(self.routes):
            if not r.detecteurs:
                continue
            m = np.flatnonzero(self.route[act] == r_i)
            for d_i, x in enumerate(r.detecteurs):
                c = m[(s_old[m] < x) & (self.s[act][m] >= x)]
                for k in c:
                    i = act[k]
                    fr = (x - s_old[k]) / max(self.s[i] - s_old[k], 1e-9)
                    self.detections.append((int(i), r_i, d_i, t + fr * dt, float(v[k] + fr * (self.v[i] - v[k]))))
        if self.trace is not None:
            self.t_trace.append(t + dt)
            for nom, val in (("s", self.s[act]), ("v", self.v[act]), ("a", self.a_eff[act]), ("gap", gap2),
                             ("urg", self.urg[act].astype(float)), ("T", T_i), ("p08", capt_j.astype(float)),
                             ("acc", self.accidente[act].astype(float))):
                full = np.full(self.N, np.nan, np.float32)
                full[act] = val
                self.trace[nom].append(full)
        for r_i, r in enumerate(self.routes):
            m = act[(self.route[act] == r_i) & (self.s[act] >= r.longueur)]
            self.actif[m] = False
            self.fini[m] = True
        self.t = t + dt

    def _entrer_urgence(self, i, loom, req=None):
        """Freinage d'urgence. Mode « markkula » : rampe j_B = k_B τ_B⁻¹ jusqu'à a1 (Markkula 2016 fig. 10).
        Mode « tpr » : décélération constante équivalente de NCHRP 400 (0,55 ± 0,07 g, mesurée du début du
        freinage à l'arrêt, montée comprise) appliquée dès le début du freinage."""
        self.urg[i] = True
        if self.opt["mode_urgence"] == "markkula":
            self.urg_jB[i] = min(self.kB[i] * max(loom, 0.05), self.P.v("markkula_jB_plafond_ms3"))
            self.urg_cible[i] = self.a1[i]
        else:
            self.urg_jB[i] = 1e6
            self.urg_cible[i] = self.dec_equiv[i]
        self.urg_besoin[i] = req is not None
        if req is not None:
            # urgence par besoin (situation perçue en continu, sans surprise) : freinage requis, au moins b_i
            self.urg_cible[i] = min(self.urg_cible[i], max(req, self.b[i]))

    # ------------------------------------------------------------------ perception
    def _maj_snap(self, act, m, lid, s_l_eff, vl, al, t):
        k = np.flatnonzero(m)
        i = act[k]
        self.snap_voie[i] = self._voie_courante[k]
        self.snap_lid[i] = lid[k]
        self.snap_s[i], self.snap_v[i], self.snap_a[i], self.snap_t[i] = s_l_eff[k], vl[k], al[k], t
        per = np.flatnonzero(m & (t >= self.t_next[act] - 1e-9))
        self.point_action[act[per]] = True
        self.t_next[act[per]] = t + self.tpr_ant[act[per]]

    def _percu(self, act, lid, s_eff, t):
        """Meneur perçu : dernier état vu, extrapolé à accélération constante (vitesse ≥ 0)."""
        i = act
        has = self.snap_lid[i] >= 0
        dtk = t - self.snap_t[i]
        a_k, v_k = self.snap_a[i], self.snap_v[i]
        t_arret = np.where(a_k < 0, v_k / np.maximum(-a_k, 1e-9), np.inf)
        te = np.minimum(dtk, t_arret)
        s_l = self.snap_s[i] + v_k * te + 0.5 * a_k * te * te
        v_l = np.maximum(v_k + a_k * dtk, 0.0)
        a_l = np.where(v_l > 0, a_k, 0.0)
        Ll = self.L[np.maximum(self.snap_lid[i], 0)]
        gap = np.where(has, s_l - Ll - s_eff, M.INF)
        return gap, np.where(has, v_l, self.v[i]), np.where(has, a_l, 0.0)

    def _T_contextuel(self, act, t):
        """T_i(t) : r·T_suivi en décharge, puis relaxation exponentielle vers T_suivi (H-03) ; T_i ≥ Δ_a,i (H-17)."""
        P_ = self.P
        r = self.P.v("T_decharge_rapport")
        lam = self.P.v("T_relaxation_taux_s-1")
        Ts = self.Ts[act]
        Td = r * Ts
        relax = np.isfinite(self.t_relax[act])
        T = np.where(self.decharge[act], Td, Ts)
        T_cible = Ts - (Ts - Td) * np.exp(-lam * np.maximum(t - self.t_relax[act], 0.0))
        if self.P.v("relaxation_passive"):
            # relaxation passive : T ne dépasse pas l'écart temporel net observé (le conducteur n'ouvre pas
            # l'écart en freinant ; T suit l'ouverture spontanée de l'écart), et ne décroît pas
            T_obs = (self._gap_courant - self.s0[act]) / np.maximum(self.v[act], 1.0)
            T_pass = np.minimum(T_cible, np.maximum(self.T_cur[act], T_obs))
            T = np.where(relax, np.maximum(T_pass, Td), T)
        else:
            T = np.where(relax, T_cible, T)
        # fin de décharge quand le véhicule atteint 0,8 v0 (convention du prototype) : la relaxation ne
        # commence qu'une fois la vitesse de croisière presque atteinte, loin en aval de la ligne
        fin = self.decharge[act] & (self.v[act] > P_.v("fin_decharge_frac_v0") * self.v0[act])
        # ou 50 m après la ligne de feu (convention) : derrière un conducteur lent, 0,8 v0 n'est jamais atteint et
        # le T court de décharge rendait le peloton instable en aval de la ligne (collisions, rapport § 3.1)
        for r_i, r in enumerate(self.routes):
            for f in r.feux:
                fin |= self.decharge[act] & (self.route[act] == r_i) & (self.s[act] > f.s + self.P.v("fin_decharge_aval_m"))
        k = act[fin]
        self.decharge[k] = False
        self.t_relax[k] = t
        t_min = self.opt["T_min_action"] if self.opt["T_min_action"] is not None else P_.v("T_min_intervalle_action")
        if t_min:
            T = np.maximum(T, self.tpr_ant[act])       # H-17 : pas de T plus court que l'intervalle des points d'action
        self.T_cur[act] = T
        return T

    # ------------------------------------------------------------------ départ
    def _depart(self, act, v, a_w, has, gap, obst, t):
        P = self.P
        # « parti » : le véhicule a démarré et ne s'est pas encore réimmobilisé sous contrainte
        retenu = (v < P.v("vitesse_arret_ms")) & (a_w <= P.v("seuil_depart_ms2"))
        self.parti[act[retenu]] = False
        arrete = (v < P.v("vitesse_arret_ms")) & ~self.pilote[act] & ~self.parti[act]
        # arrêt en file : derrière un meneur proche ou devant une ligne
        # contexte de décharge (r·T_suivi, facteur a) : files arrêtées sur un itinéraire à feux seulement, le
        # contexte où r a été calé (Certu Feux 2010) ; aux STOP, chaque meneur s'arrête de nouveau à la ligne
        dfile = P.v("d_en_file_m")
        en_file = arrete & ((has & (gap < dfile)) | (obst < dfile)) & self.route_feux[self.route[act]]
        self.arret_en_file[act[en_file]] = True
        veut = arrete & (a_w > P.v("seuil_depart_ms2"))
        nouv = veut & ~self.attente[act]
        i_n = act[nouv]
        self.attente[i_n] = True
        self.t_dep[i_n] = t + self.tpr_ant[i_n]
        pre = np.isfinite(self.pre_autorise[i_n])
        self.t_dep[i_n[pre]] = np.maximum(t, self.pre_autorise[i_n[pre]])
        annule = arrete & self.attente[act] & (a_w <= 0)
        self.attente[act[annule]] = False
        tient = self.attente[act] & (t < self.t_dep[act] - 1e-9)
        a_w = np.where(tient, np.minimum(a_w, 0.0), a_w)
        part = self.attente[act] & (t >= self.t_dep[act] - 1e-9)
        i_p = act[part]
        self.attente[i_p] = False
        self.parti[i_p] = True
        self.t_start[i_p] = self.t_dep[i_p]
        self.decharge[i_p] = self.arret_en_file[i_p]
        self.t_relax[i_p] = np.inf
        self.arret_en_file[i_p] = False
        self.pre_autorise[i_p] = -np.inf
        self.journal["depart"].extend({"agent": int(i), "t": float(self.t_dep[i])} for i in i_p)
        # facteur de démarrage EIDM sur les accélérations positives
        f = M.facteur_demarrage(t - self.t_start[act], P.v("demarrage_taccmax"), P.v("demarrage_Mflatness"),
                                P.v("demarrage_Mbegin"))
        dem = np.isfinite(self.t_start[act]) & (t - self.t_start[act] < P.v("fenetre_facteur_demarrage_s"))
        return np.where(dem & (a_w > 0), a_w * f, a_w)

    # ------------------------------------------------------------------ feux
    def _feu(self, act, m, f, t, v, obst, a_cib):
        P = self.P
        k = np.flatnonzero(m)
        i = act[k]
        d = f.s - self.s[i]
        amont = d > 0
        etat = f.etats(t, self.couloir[i])
        arr = P.v("arret_ligne_feu_m")
        # apparition du jaune : TTL au début du jaune, décision après le TPR jaune
        nj = amont & (etat == 1) & ~self.jaune_vu[i]
        self.jaune_vu[i[nj]] = True
        tj = f.t_jaune_couloir(self.couloir[i[nj]])
        self.jaune_ttl[i[nj]] = d[nj] / np.maximum(v[k[nj]], 0.1)
        self.jaune_tdec[i[nj]] = tj + self.tpr_jaune[i[nj]]
        dec = amont & (self.jaune_dec[i] == 0) & (t >= self.jaune_tdec[i])
        if dec.any():
            arret, dnec = M.decision_jaune(self.jaune_ttl[i[dec]], self.seuil_jaune[i[dec]], d[dec] - arr, v[k[dec]],
                                           np.minimum(self.a1[i[dec]], self.dmax[i[dec]]), f.duree_jaune,
                                           self.opt["option_h11"])
            self.jaune_dec[i[dec]] = np.where(arret, 1, 2)
            for ii, ar, dn, ttl in zip(i[dec], arret, dnec, self.jaune_ttl[i[dec]]):
                self.journal["jaune"].append({"agent": int(ii), "t": t, "ttl": float(ttl), "arret": bool(ar),
                                              "decel_necessaire": float(dn), "seuil": float(self.seuil_jaune[ii])})
        stop_jaune = amont & (self.jaune_dec[i] == 1)
        rouge_ou_jaune_stop = amont & (((etat == 2) & (self.jaune_dec[i] != 2)) | stop_jaune)
        cin = stop_jaune & (v[k] > 0.5) & (d - arr > 0.3)
        a_k = -v[k] ** 2 / (2 * np.maximum(d - arr, 0.3))
        a_cib[k] = np.where(cin, np.minimum(a_cib[k], a_k), a_cib[k])
        ob = rouge_ou_jaune_stop & ~cin
        obst[k] = np.where(ob, np.minimum(obst[k], d - arr + self.s0[i]), obst[k])
        # vert : réinitialisation des décisions ; anticipation du départ (variante « vert »)
        vert = etat == 0
        if self.opt["reaction_depart"] == "vert":
            nv = vert & amont & ~self.feu_vert_vu[i] & (v[k] < 0.1)
            self.pre_autorise[i[nv]] = t + self.tpr_ant[i[nv]]
        self.feu_vert_vu[i[vert]] = True
        self.jaune_vu[i[vert]] = False
        self.jaune_dec[i[vert & amont]] = 0

    # ------------------------------------------------------------------ STOP et créneaux
    def _stop(self, act, m, st, r, t, v, obst, a_cib, voie, s_eff, lid):
        P = self.P
        k_all = np.flatnonzero(m)
        i_all = act[k_all]
        d_all = st.s - self.s[i_all]
        # suivi de la vitesse minimale dans les 3 derniers mètres (arrêt complet ou non)
        z3 = (d_all >= 0) & (d_all <= P.v("stop_zone_vmin_m"))
        self.stop_vmin_zone[i_all[z3]] = np.minimum(self.stop_vmin_zone[i_all[z3]], v[k_all[z3]])
        a01 = z3 & (v[k_all] < 0.1) & ~np.isfinite(self.stop_t_v01[i_all])
        self.stop_t_v01[i_all[a01]] = t
        # un véhicule non engagé qui a franchi la ligne (arrêt impossible après un refus tardif) est engagé de fait
        force = (d_all < -1.0) & (self.stop_etat[i_all] >= 1) & (self.stop_etat[i_all] < 4)
        for i in i_all[force]:
            self.stop_etat[i] = 4
            self.journal["stop_franchi_sans_engagement"].append({"agent": int(i), "t": t, "v": float(self.v[i])})
        sel = (d_all >= -1.0) & (d_all < P.v("stop_portee_m")) & (self.stop_etat[i_all] >= 1) & (self.stop_etat[i_all] < 4)
        arr = P.v("arret_ligne_stop_m")
        for k, i, d in zip(k_all[sel], i_all[sel], d_all[sel]):
            mod = self.stop_modalite[i]
            et = self.stop_etat[i]
            if et == 1 and mod == 0 and v[k] < P.v("stop_v_arret_ms") and d < P.v("stop_d_arret_m"):
                self.stop_etat[i] = et = 2
                self.stop_t_arret[i] = t
            if et == 2 and t >= self.stop_t_arret[i] + self.tpr_ant[i]:
                self.stop_etat[i] = et = 3
            decision = False
            if et == 3 and self.point_action[i]:
                decision = True
            if et == 1 and mod in (1, 2):
                # décision prise d'assez loin pour pouvoir s'arrêter à stop_frac_b_decision × b ; le point de décision
                # (œil à 4 m de la ligne, Certu) est ramené à l'avant du véhicule (recul de l'œil, convention)
                d_dec = (P.v("point_decision_stop_m") - P.v("recul_oeil_avant_m")
                         + v[k] ** 2 / (2 * P.v("stop_frac_b_decision") * self.b[i]))
                # le conducteur regarde en arrivant au point de décision, puis à chaque point d'action
                if d <= d_dec and (self.point_action[i] or not self.stop_dec_vu[i]):
                    decision = True
                    self.stop_dec_vu[i] = True
            if decision:
                ok, lag = self._evaluer_creneau(i, k, st, t, v[k], d, act, voie, s_eff)
                self.journal["creneau"].append({"agent": int(i), "t": t, "etat": int(et), "modalite": int(mod),
                                                "lag": float(lag), "tc": float(self.fac_creneau[i] * st.creneau_ref_s),
                                                "accepte": bool(ok), "motif": self._motif})
                if ok:
                    self.stop_etat[i] = 4
                    if v[k] < P.v("vitesse_arret_ms"):
                        self.pre_autorise[i] = t      # départ immédiat : la décision est l'action anticipée
                    continue
                if mod in (1, 2):
                    self.stop_modalite[i] = mod = 0    # créneau refusé en roulant : arrêt à la ligne
            # contraintes
            if mod == 0 or et >= 2:
                obst[k] = min(obst[k], d - arr + self.s0[i])
            elif mod == 1:
                vg = self.stop_v_glisse[i]
                if v[k] > vg and d <= max(v[k] * P.v("tpreview_s"), 1.0):
                    a_cib[k] = min(a_cib[k], -float(M.decel_cible(v[k], d, vg)))
        # arrêt glissé engagé avant la ligne : le conducteur garde sa vitesse résiduelle jusqu'à la ligne
        gl = (d_all >= 0.0) & (d_all < 30.0) & (self.stop_etat[i_all] == 4) & (self.stop_modalite_tiree[i_all] == 1) &              (self.stop_modalite[i_all] == 1)
        for k, i, d in zip(k_all[gl], i_all[gl], d_all[gl]):
            vg = self.stop_v_glisse[i]
            if v[k] > vg and d <= max(v[k] * P.v("tpreview_s"), 1.0):
                a_cib[k] = min(a_cib[k], -float(M.decel_cible(v[k], d, vg)))

    def _evaluer_creneau(self, i, k, st, t, v_i, d, act, voie, s_eff):
        """Créneau disponible au point de conflit, vu depuis le point de décision (conception § 5.3).
        Accepté si lag ≥ t_c,i = facteur_i × t_c,FR, si le prioritaire précédent a dégagé le point de
        conflit, et si le prioritaire suivant n'aura pas à freiner plus que son b (H-10, IIDM + CAH)."""
        P = self.P
        cible = st.s_conflit
        self._motif = ""
        m = (self.couloir[act] == self.couloir[i]) & (voie == st.voie_prioritaire) & (self.route[act] != self.route[i])
        if not m.any():
            return True, np.inf
        sj, kj = s_eff[m], np.flatnonzero(m)
        r = self.routes[self.route[i]]
        # zone d'insertion occupée : un prioritaire entre la position projetée du non-prioritaire à la ligne
        # (s_conflit - longueur du virage - s0 - L) et le point de conflit + 1 m (arrière)
        L_vir = self._longueur_virage(i) if r.jonction else 0.0
        vj_all = self.v[act[kj]]
        # zone de conflit occupée : prioritaire au droit du point de conflit (avant à moins de 2 m, arrière pas
        # encore dégagé de 1 m), ou prioritaire lent (< 2 m/s) entre la position projetée du non-prioritaire et
        # le point de conflit ; les prioritaires en approche sont jugés par le décalage (lag)
        zone_amont = cible - L_vir - self.s0[i] - self.L[i]
        occupe = ((sj >= cible - 2.0) & (sj - self.L[act[kj]] <= cible + 1.0)) |                  ((sj >= zone_amont) & (sj < cible - 2.0) & (vj_all < 2.0))
        amont = sj < cible - 2.0
        glisse = self.stop_modalite[i] == 1
        v_ligne = min(v_i, self.stop_v_glisse[i]) if glisse else v_i
        t_self = 0.0 if v_i < 0.5 else 2.0 * d / max(v_i + v_ligne, 0.1)
        if occupe.any():
            self._motif = "zone_occupee"
            return False, np.nan
        if not amont.any():
            return True, np.inf
        tj = (cible - sj[amont]) / np.maximum(self.v[act[kj[amont]]], 0.5)
        o = np.argmin(tj)
        lag = float(tj[o] - t_self)
        tc = self.fac_creneau[i] * st.creneau_ref_s
        if lag < tc:
            self._motif = "creneau"
            return False, lag
        # H-10 : freinage imposé au prioritaire suivant ≤ son b. Le non-prioritaire est projeté sur la voie
        # prioritaire dès la ligne (à s_conflit - longueur du virage) : on prédit son mouvement (démarrage EIDM,
        # vitesse de virage) et celui du prioritaire (vitesse constante) pendant toute la manœuvre, et l'on
        # retient le freinage IIDM + CAH le plus fort demandé au prioritaire.
        j = act[kj[amont][o]]
        sj0 = sj[amont][o]
        gen = self.generique[int(self.route[j])] if P.v("h10_prioritaire_generique") else None
        vc = min(self._v_virage(i), self.v0[i])
        a_i = self.a[i]
        x, vv, tt, a_j = 0.0, v_i, 0.0, np.inf
        x_ligne = d                     # distance restant jusqu'à la ligne
        dec_g = (v_i ** 2 - v_ligne ** 2) / (2.0 * max(d, 0.5)) if v_i > v_ligne else 0.0
        while tt < P.v("h10_horizon_s"):
            f = 1.0 if v_i >= 0.5 else float(M.facteur_demarrage(tt, P.v("demarrage_taccmax"), P.v("demarrage_Mflatness"), P.v("demarrage_Mbegin")))
            a_e = a_i * f * (1.0 - min(vv / max(vc, 0.1), 1.0) ** 4)
            if x < x_ligne and dec_g > 0:
                a_e = -dec_g if vv > v_ligne else 0.0
            vv += a_e * 0.1
            x += vv * 0.1
            tt += 0.1
            if x < x_ligne:
                continue
            s_min = cible - L_vir + (x - x_ligne)          # avant du non-prioritaire projeté
            gap_j = (s_min - self.L[i]) - (sj0 + self.v[j] * tt)
            if gap_j <= 0.5:
                a_j = -np.inf
                break
            if gen is not None:
                a_j = min(a_j, float(M.poursuite(self.v[j], gap_j, vv, a_e, max(gen["v0"], self.v[j]), gen["T"], gen["s0"],
                                                 gen["a"], gen["b"], P.v("idm_delta"), P.v("cah_c"))))
            else:
                a_j = min(a_j, float(M.poursuite(self.v[j], gap_j, vv, a_e, self.v0[j], self.Ts[j], self.s0[j], self.a[j], self.b[j])))
            if s_min > cible + P.v("h10_d_apres_conflit_m"):
                break
        b_ref = gen["b"] if gen is not None else self.b[j]
        ok = bool(a_j >= -b_ref) or (not self.opt["h10"] and a_j > -np.inf)
        self._motif = "" if ok else "H-10"
        return ok, lag

    def _longueur_virage(self, i):
        r = self.routes[self.route[i]]
        return sum(c.s1 - c.s0 for c in r.courbes if c.s0 >= r.jonction.s - 1e-6)

    def _v_virage(self, i):
        r_i = self.route[i]
        r = self.routes[r_i]
        vs = [self.v_courbes[(r_i, c_i)][i] for c_i, c in enumerate(r.courbes) if r.jonction and c.s0 >= r.jonction.s - 1e-6]
        return min(vs) if vs else self.v0[i]

    # ------------------------------------------------------------------ boucle
    def executer(self, t_fin: float, arret_si_vide: bool = False):
        while self.t < t_fin - 1e-9:
            self.pas()
            if arret_si_vide and self.insere.all() and not self.actif.any():
                break
        return self

    def traces(self) -> dict:
        if self.trace is None:
            return {}
        out = {k: np.vstack(v) for k, v in self.trace.items()}
        out["t"] = np.asarray(self.t_trace)
        return out

    def detections_tableau(self):
        if not self.detections:
            return np.zeros((0, 5))
        return np.array(self.detections, dtype=float)
