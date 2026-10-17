"""Mêmes scénarios dans SUMO 1.27.1 (Krauss et EIDM), réseaux construits par netconvert.

Quatre configurations (conception § 11.1) :
  krauss_defaut, eidm_defaut   valeurs par défaut de SUMO (vClass passenger), pas 0,1 s, intégration
                               d'Euler par défaut (mêmes réglages que le volet 03)
  krauss_nos_lois, eidm_nos_lois  un vType par conducteur tiré par notre prototype (mêmes conducteurs et
                               mêmes véhicules, appariés), correspondance du § 11.2, pas 0,1 s, sigma = 0,
                               intégration d'Euler (v0.2 : le code EIDM 1.27.1 ne borne le jerk qu'en Euler ;
                               la v0.1 lançait « nos lois » en balistique, ce qui mêlait paramètres et intégrateur)
Transferts v0.2 (relecture adverse du 17/10/2026) :
  S1  tau = f × T_suivi, f calé SÉPARÉMENT pour Krauss et pour l'EIDM sur 1 800 uvpd/h (caler_tau_s1) ; accel = a_i
      (sans le facteur H-14, calé pour notre IIDM) ;
  S2  meneur : decel = apparentDecel = b du conducteur tiré (v0.1 : 9 m/s², ce qui rendait Krauss sûr par
      construction) ; EIDM : treaction = TPR « signal inattendu » ; variantes Krauss : actionStepLength = TPR
      inattendu (arrondi au pas), device driverstate ;
  S3  nos lois : impatience 0,5 (volet 03 : créneau critique ≈ 4,7 s avec ce réglage), créneaux mesurés aussi depuis
      l'arrêt en tête de ligne et au point de conflit.
Réseaux et fichiers de routes : D:/DocRoute/17_Modele_Vehicules_Conducteurs/05_Prototype/sumo/<scénario>/ ;
sorties brutes (FCD) : D:/DocRoute/17_Modele_Vehicules_Conducteurs/tmp/05/sumo_brut/ (régénérables).
Convention de temps du volet 03 : l'état écrit au pas t est celui après le mouvement [t, t+Δ] -> t + Δ.
"""
from __future__ import annotations

import math
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np

from parametres import DOC05, TMP05
import commun as C   # recon/trafic/etat_art_sumo/commun.py (netconvert, lancer_sumo, lire_fcd)
import sumolib  # noqa: E402

DOSSIER = DOC05 / "sumo"
BRUT = TMP05 / "sumo_brut"
PAS = 0.1
CONFIGS = {
    "krauss_defaut": {"cf": "Krauss", "nos_lois": False, "libelle": "SUMO Krauss (défaut)"},
    "eidm_defaut": {"cf": "EIDM", "nos_lois": False, "libelle": "SUMO EIDM (défaut)"},
    "krauss_nos_lois": {"cf": "Krauss", "nos_lois": True, "libelle": "SUMO Krauss (nos lois)"},
    "eidm_nos_lois": {"cf": "EIDM", "nos_lois": True, "libelle": "SUMO EIDM (nos lois)"},
}


# ----------------------------------------------------------------------------- outils
def ecrire(p: Path, txt: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


CONFIGS_S2 = dict(CONFIGS, **{
    "krauss_nos_lois_asl": {"cf": "Krauss", "nos_lois": True, "asl": True, "libelle": "SUMO Krauss (nos lois, actionStepLength = TPR)"},
    "krauss_nos_lois_ds": {"cf": "Krauss", "nos_lois": True, "driverstate": True, "libelle": "SUMO Krauss (nos lois, driverstate)"},
})


def options_sumo(cfg_id):
    """Pas 0,1 s, intégration d'Euler pour toutes les configurations (v0.2)."""
    o = ["--step-length", str(PAS), "--no-step-log", "true", "--collision.action", "warn",
         "--collision.check-junctions", "true"]
    if CONFIGS_S2.get(cfg_id, {}).get("driverstate"):
        o += ["--device.driverstate.probability", "1"]
    return o


def vtype_defaut(cfg_id, vid="vp"):
    return f'  <vType id="{vid}" vClass="passenger" carFollowModel="{CONFIGS_S2[cfg_id]["cf"]}"/>'


def vtype_nos_lois(sim, i, cfg_id, vid, vma_ms, T=None, a_fac=1.0, treaction="anticipe", impatience=None):
    """vType d'un conducteur tiré (correspondance de la conception § 11.2)."""
    P = sim.P
    cfg = CONFIGS_S2[cfg_id]
    T = float(sim.Ts[i]) if T is None else float(T)
    att = {"id": vid, "vClass": "passenger", "carFollowModel": cfg["cf"],
           "length": f"{sim.L[i]:.3f}", "minGap": f"{sim.s0[i]:.3f}",
           "speedFactor": f"{max(0.2, sim.v0[i] / vma_ms):.4f}", "speedDev": "0",
           "accel": f"{sim.a[i] * a_fac:.3f}", "decel": f"{sim.b[i]:.3f}", "apparentDecel": f"{sim.b[i]:.3f}",
           "emergencyDecel": f"{max(sim.b[i], min(sim.a1[i], sim.dmax[i])):.3f}", "tau": f"{T:.3f}", "sigma": "0",
           "maxSpeed": f"{sim.veh['vmax'][i]:.2f}"}
    if cfg.get("asl"):
        att["actionStepLength"] = f"{max(PAS, round(float(sim.tpr_sig[i]) / PAS) * PAS):.1f}"
    if impatience is not None:
        att["impatience"] = f"{impatience}"
    if cfg["cf"] == "EIDM":
        tr = sim.tpr_sig[i] if treaction == "inattendu" else sim.tpr_ant[i]
        att.update({"treaction": f"{tr:.3f}", "jerkmax": f"{P.v('jerk_confort')}",
                    "taccmax": f"{P.v('demarrage_taccmax')}", "Mflatness": f"{P.v('demarrage_Mflatness')}",
                    "Mbegin": f"{P.v('demarrage_Mbegin')}", "tpreview": f"{P.v('tpreview_s')}"})
    return "  <vType " + " ".join(f'{k}="{v}"' for k, v in att.items()) + "/>"


def decalages(net, aretes):
    """{voie: abscisse de son début} le long d'un itinéraire, voies internes comprises (voie 0)."""
    off, s = {}, 0.0
    for k, e in enumerate(aretes):
        lane = net.getEdge(e).getLane(0)
        off[lane.getID()] = s
        s += lane.getLength()
        if k + 1 < len(aretes):
            cons = [c for c in lane.getOutgoing() if c.getTo().getID() == aretes[k + 1]]
            via = cons[0].getViaLaneID() if cons else ""
            while via:
                il = net.getLane(via)
                off[via] = s
                s += il.getLength()
                outs = il.getOutgoing()
                via = outs[0].getViaLaneID() if outs and outs[0].getViaLaneID() else ""
    return off, s


def trajectoires(fcd: Path, off: dict):
    """{vehicule: dict(t, s, v, a)} avec s = abscisse le long de l'itinéraire (avant du véhicule)."""
    tr = defaultdict(lambda: {"t": [], "s": [], "v": [], "a": []})
    for (t, vid, lane, pos, v, a) in C.lire_fcd(fcd):
        if lane not in off:
            continue
        d = tr[vid]
        d["t"].append(t + PAS); d["s"].append(off[lane] + pos); d["v"].append(v); d["a"].append(a)
    out = {}
    for k, d in tr.items():
        o = np.argsort(d["t"])
        out[k] = {kk: np.asarray(vv)[o] for kk, vv in d.items()}
    return out


def franchissement(d, x):
    s, t, v = d["s"], d["t"], d["v"]
    i = int(np.searchsorted(s, x))
    if i == 0 or i >= len(s):
        return np.nan, np.nan
    f = (x - s[i - 1]) / max(s[i] - s[i - 1], 1e-9)
    return float(t[i - 1] + f * (t[i] - t[i - 1])), float(v[i - 1] + f * (v[i] - v[i - 1]))


def lancer(args, log):
    C.lancer_sumo(args, log)


# ----------------------------------------------------------------------------- S1 : file au vert
def s1_reseau():
    d = DOSSIER / "S1_file_feu"
    ecrire(d / "s1.nod.xml", '<nodes>\n  <node id="A" x="0" y="0" type="priority"/>\n'
           '  <node id="J" x="200" y="0" type="traffic_light" tl="J"/>\n  <node id="B" x="400" y="0" type="priority"/>\n</nodes>\n')
    ecrire(d / "s1.edg.xml", '<edges>\n  <edge id="AJ" from="A" to="J" numLanes="1" speed="13.89"/>\n'
           '  <edge id="JB" from="J" to="B" numLanes="1" speed="13.89"/>\n</edges>\n')
    C.netconvert(d, "s1", ["--tls.discard-simple", "false"])
    ecrire(d / "s1_feux.add.xml", '<additional>\n  <tlLogic id="J" type="static" programID="vert10" offset="0">\n'
           '    <phase duration="10" state="r"/>\n    <phase duration="200" state="G"/>\n  </tlLogic>\n</additional>\n')
    net = sumolib.net.readNet(str(d / "s1.net.xml"), withInternal=True)
    return d, net


def caler_tau_s1(sim_proto, meta, cfg_id, n_rep=20, cible=2.0, iterations=9):
    """Facteur f (tau = f × T_suivi) tel que le TIV moyen des rangs 5-12 vaille la cible (1 800 uvpd/h, Certu Feux
    2010 p. 34), par dichotomie, pour un modèle SUMO donné (« nos lois »). Renvoie (f, historique)."""
    hist = []
    lo, hi = 0.1, 1.5
    for _ in range(iterations):
        f = 0.5 * (lo + hi)
        res = s1_sumo(sim_proto, meta, cfg_id, n_rep=n_rep, facteur_tau=f)
        tc = np.array([[r.get(k, {}).get("t_passage", np.nan) for k in range(1, meta["n_vehicules"] + 1)] for r in res])
        h = np.diff(np.concatenate([np.zeros((tc.shape[0], 1)), tc], axis=1), axis=1)
        x = float(np.nanmean(h[:, 4:12]))
        hist.append((round(f, 4), round(x, 4)))
        if x > cible:
            hi = f
        else:
            lo = f
    return round(0.5 * (lo + hi), 4), hist


def s1_sumo(sim_proto, meta, cfg_id, n_rep=30, graine0=0, facteur_tau=None):
    """File de 20 véhicules arrêtés, vert à t = 10 s. Renvoie {rep: {rang: (t_passage, v_passage)}} et traces.
    « nos lois » : tau = facteur_tau × T_suivi (calé par caler_tau_s1), accel = a_i (sans H-14)."""
    d, net = s1_reseau()
    off, _ = decalages(net, ["AJ", "JB"])
    L_AJ = net.getEdge("AJ").getLane(0).getLength()
    nv = meta["n_vehicules"]
    res = []
    P = sim_proto.P
    for q in range(n_rep):
        lignes = ["<routes>", '  <route id="r" edges="AJ JB"/>']
        pos = L_AJ - P.v("arret_ligne_feu_m")
        if not CONFIGS[cfg_id]["nos_lois"]:
            lignes.append(vtype_defaut(cfg_id))
            for k in range(nv):
                lignes.append(f'  <vehicle id="v{k:02d}" type="vp" route="r" depart="0" departPos="{pos:.2f}" departSpeed="0"/>')
                pos -= 5.0 + 2.5 + 0.01
        else:
            for k in range(nv):
                i = q * nv + k
                f = facteur_tau if facteur_tau is not None else P.v("T_decharge_rapport")
                T = max(0.05, f * sim_proto.Ts[i])                 # tau calé pour ce modèle SUMO (v0.2)
                lignes.append(vtype_nos_lois(sim_proto, i, cfg_id, f"t{k:02d}", 13.89, T=T))
                lignes.append(f'  <vehicle id="v{k:02d}" type="t{k:02d}" route="r" depart="0" departPos="{pos:.2f}" departSpeed="0"/>')
                if k + 1 < nv:
                    pos -= sim_proto.L[i] + sim_proto.s0[i + 1] + 0.01
        lignes.append("</routes>")
        rou = d / f"s1_{cfg_id}.rou.xml"
        ecrire(rou, "\n".join(lignes) + "\n")
        fcd = BRUT / "S1" / f"fcd_{cfg_id}_{q}.xml.gz"
        fcd.parent.mkdir(parents=True, exist_ok=True)
        lancer(["-n", str(d / "s1.net.xml"), "-r", str(rou), "-a", str(d / "s1_feux.add.xml"), "--seed", str(graine0 + q),
                "--end", "90", "--fcd-output", str(fcd), "--fcd-output.attributes", "lane,pos,speed,acceleration"]
               + options_sumo(cfg_id), BRUT / "S1" / f"log_{cfg_id}_{q}.txt")
        tr = trajectoires(fcd, off)
        rangs = {}
        for k in range(nv):
            dd = tr.get(f"v{k:02d}")
            if dd is None:
                continue
            tc, vc = franchissement(dd, L_AJ)
            amax = float(np.nanmax(dd["a"][(dd["t"] > 10.0) & (dd["t"] < 10.0 + 4.0 * nv)])) if len(dd["a"]) else np.nan
            k0 = np.flatnonzero((dd["t"] > 10.0) & (dd["v"] > 0.01))
            t_dep = float(dd["t"][k0[0]] - PAS) if k0.size else np.nan
            k1 = np.flatnonzero((dd["t"] > 10.0) & (dd["v"] >= 1.0))
            t1 = float(dd["t"][k1[0]]) - t_dep if k1.size else np.nan
            kp = (dd["t"] > 10.0) & (dd["t"] < t_dep + 8.0)
            t_pic = float(dd["t"][kp][np.argmax(dd["a"][kp])] - 0.05 - t_dep) if kp.any() else np.nan
            jerk = np.abs(np.diff(dd["a"]) / PAS)[(dd["t"][1:] > 10.0) & (dd["v"][1:] > 0.1)]
            rangs[k + 1] = {"t_passage": tc - 10.0, "v_passage": vc, "pic": amax, "t_1ms": t1, "t_pic": t_pic,
                            "jerk": jerk}
        res.append(rangs)
    return res


# ----------------------------------------------------------------------------- S2 : freinage du meneur
def s2_reseau():
    d = DOSSIER / "S2_freinage_urgence"
    ecrire(d / "s2.nod.xml", '<nodes>\n  <node id="A" x="0" y="0" type="priority"/>\n  <node id="B" x="4000" y="0" type="priority"/>\n</nodes>\n')
    ecrire(d / "s2.edg.xml", '<edges>\n  <edge id="AB" from="A" to="B" numLanes="1" speed="22.22"/>\n</edges>\n')
    C.netconvert(d, "s2")
    return d


def s2_sumo(sim_proto, meta, cfg_id, n_rep=30, decel_meneur=6.68, graine0=0, meneur_b=True):
    """Peloton de 11 VL à 60 km/h ; le meneur (piloté par TraCI, speedMode 0) freine à t = 40 s.
    Renvoie pour chaque réplication : temps d'allumage des feux stop par rang, décélération max, écart
    minimal, collisions."""
    import traci
    from scenarios import CONVENTIONS
    c = CONVENTIONS["S2"]
    d = s2_reseau()
    nv = c["n_vehicules"]
    v_p = c["v_peloton_kmh"] / 3.6
    t_f, jm = c["t_freinage_s"], c["jerk_meneur_ms3"]
    P = sim_proto.P
    out = []
    for q in range(n_rep):
        # meneur : decel = apparentDecel = b du conducteur tiré (v0.2) ; il freine à decel_meneur par TraCI
        # (speedMode 0) ; emergencyDecel 9 m/s² (défaut SUMO). v0.1 : decel = 9, donc Krauss sûr par construction.
        b_l = float(sim_proto.b[q * c["n_vehicules"]]) if meneur_b else 9.0
        lignes = ["<routes>", '  <route id="r" edges="AB"/>',
                  f'  <vType id="meneur" vClass="passenger" carFollowModel="Krauss" sigma="0" accel="5" decel="{b_l:.3f}" '
                  f'apparentDecel="{b_l:.3f}" emergencyDecel="9" speedFactor="2" speedDev="0"/>']
        pos = 800.0
        lignes.append(f'  <vehicle id="v00" type="meneur" route="r" depart="0" departPos="{pos:.2f}" departSpeed="{v_p:.3f}"/>')
        if not CONFIGS_S2[cfg_id]["nos_lois"]:
            lignes.append(vtype_defaut(cfg_id))
        for k in range(1, nv):
            i = q * nv + k
            if CONFIGS_S2[cfg_id]["nos_lois"]:
                lignes.append(vtype_nos_lois(sim_proto, i, cfg_id, f"t{k:02d}", 80 / 3.6, treaction="inattendu"))
                L_prec = sim_proto.L[i - 1]
                pos -= L_prec + sim_proto.s0[i] + v_p * sim_proto.Ts[i]
                typ = f"t{k:02d}"
            else:
                pos -= 5.0 + 2.5 + v_p * 1.0
                typ = "vp"
            v_dep = v_p if not CONFIGS_S2[cfg_id]["nos_lois"] else min(v_p, 0.999 * sim_proto.v0[i])   # SUMO refuse v > v désirée
            lignes.append(f'  <vehicle id="v{k:02d}" type="{typ}" route="r" depart="0" departPos="{pos:.2f}" departSpeed="{v_dep:.3f}"/>')
        lignes.append("</routes>")
        rou = d / f"s2_{cfg_id}.rou.xml"
        ecrire(rou, "\n".join(lignes) + "\n")
        col = BRUT / "S2" / f"col_{cfg_id}_{q}.xml"
        col.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["sumo", "-n", str(d / "s2.net.xml"), "-r", str(rou), "--seed", str(graine0 + q), "--end", str(c["duree_s"]),
               "--collision-output", str(col)] + options_sumo(cfg_id)
        traci.start(cmd, label=f"s2_{cfg_id}_{q}")
        traci.vehicle.setSpeedMode("v00", 0)
        v_l = v_p
        acc = {f"v{k:02d}": [] for k in range(nv)}
        t = 0.0
        while t < c["duree_s"] - 1e-9:
            if t >= t_f - 1e-9:
                a_l = -min(decel_meneur, jm * (t - t_f))
                v_l = max(0.0, v_l + a_l * PAS)
            traci.vehicle.setSpeed("v00", v_l)
            traci.simulationStep()
            t += PAS
            ids = set(traci.vehicle.getIDList())
            for k in range(nv):
                vid = f"v{k:02d}"
                if vid in ids:
                    acc[vid].append((t, traci.vehicle.getSpeed(vid), traci.vehicle.getAcceleration(vid),
                                     traci.vehicle.getLanePosition(vid), traci.vehicle.getLength(vid)))
        traci.close()
        n_col = 0
        try:
            import xml.etree.ElementTree as ET
            n_col = sum(1 for _ in ET.parse(col).getroot().iter("collision"))
        except Exception:
            pass
        rep = {"collisions": n_col, "rangs": {}}
        arr = {vid: np.array(x) for vid, x in acc.items() if x}
        # accélération recalculée par différence de vitesses (même définition que pour notre modèle)
        for vid, A_ in arr.items():
            A_[1:, 2] = np.diff(A_[:, 1]) / PAS
            A_[0, 2] = 0.0
        for k in range(1, nv):
            vid, lid = f"v{k:02d}", f"v{k - 1:02d}"
            if vid not in arr or lid not in arr:
                continue
            A, Bm = arr[vid], arr[lid]
            # alignement sur les instants communs (SUMO peut insérer un véhicule plus tard que prévu)
            ta, tb = np.round(A[:, 0], 3), np.round(Bm[:, 0], 3)
            comm = np.intersect1d(ta, tb)
            A, Bm = A[np.isin(ta, comm)], Bm[np.isin(tb, comm)]
            gap = Bm[:, 3] - Bm[:, 4] - A[:, 3]
            apres = A[:, 0] >= t_f
            seuil = P.v("feux_stop_seuil_ms2")
            t_on_l = A[:, 0][apres & (Bm[:, 2] < -seuil)]
            t_on_f = A[:, 0][apres & (A[:, 2] < -seuil)]
            rep["rangs"][k] = {"delai_feux_stop": float(t_on_f[0] - t_on_l[0]) if t_on_l.size and t_on_f.size else np.nan,
                               "decel_max": float(-A[apres, 2].min()), "gap_min": float(gap[apres].min()),
                               "v_choc": np.nan}
        out.append(rep)
    return out


# ----------------------------------------------------------------------------- S3 : STOP
def s3_reseau():
    d = DOSSIER / "S3_stop"
    ecrire(d / "s3.nod.xml", '<nodes>\n  <node id="W" x="-400" y="0" type="priority"/>\n'
           '  <node id="J" x="0" y="0" type="priority_stop"/>\n  <node id="E" x="300" y="0" type="priority"/>\n'
           '  <node id="S" x="0" y="-200" type="priority"/>\n</nodes>\n')
    ecrire(d / "s3.edg.xml", '<edges>\n  <edge id="WJ" from="W" to="J" numLanes="1" speed="13.89" priority="2"/>\n'
           '  <edge id="JE" from="J" to="E" numLanes="1" speed="13.89" priority="2"/>\n'
           '  <edge id="EJ" from="E" to="J" numLanes="1" speed="13.89" priority="2"/>\n'
           '  <edge id="JW" from="J" to="W" numLanes="1" speed="13.89" priority="2"/>\n'
           '  <edge id="SJ" from="S" to="J" numLanes="1" speed="13.89" priority="1"/>\n</edges>\n')
    C.netconvert(d, "s3")
    ecrire(d / "s3_filtre_fcd.txt", "edge:WJ\nedge:SJ\nedge:JE\n")
    return d, sumolib.net.readNet(str(d / "s3.net.xml"), withInternal=True)


def geometrie_s3():
    """Longueurs du réseau SUMO utilisées par notre modèle (même géométrie)."""
    d, net = s3_reseau()
    off_maj, Lm = decalages(net, ["WJ", "JE"])
    off_min, Ln = decalages(net, ["SJ", "JE"])
    L_W = net.getEdge("WJ").getLane(0).getLength()
    L_S = net.getEdge("SJ").getLane(0).getLength()
    L_E = net.getEdge("JE").getLane(0).getLength()
    L_int = off_maj["JE_0"] - L_W
    L_vir = off_min["JE_0"] - L_S
    # rayon du virage : longueur de l'arc / angle (90°)
    R = L_vir / (math.pi / 2)
    return {"L_W": L_W, "L_int_maj": L_int, "L_E": L_E, "L_S": L_S, "L_virage": L_vir, "R_virage": R,
            "decalages_majeure": off_maj, "decalages_mineure": off_min}


def s3_sumo(sim_proto, cfg_id, n_rep=3, graine0=0, n_types=300, impatience=0.5):
    from scenarios import CONVENTIONS
    c = CONVENTIONS["S3"]
    d, net = s3_reseau()
    g = geometrie_s3()
    lignes = ["<routes>"]
    if CONFIGS[cfg_id]["nos_lois"]:
        lignes.append('  <vTypeDistribution id="vp">')
        for k in range(n_types):
            lignes.append("  " + vtype_nos_lois(sim_proto, k, cfg_id, f"t{k:03d}", 13.89, impatience=impatience).replace("/>", ' probability="1"/>'))
        lignes.append("  </vTypeDistribution>")
    else:
        lignes.append(vtype_defaut(cfg_id))
    D = c["duree_s"]
    lignes += [f'  <flow id="maj_OE" type="vp" begin="0" end="{D:.0f}" period="exp({c["debit_prioritaire_veh_h"] / 3600:.6f})" from="WJ" to="JE" departSpeed="max"/>',
               f'  <flow id="min_SE" type="vp" begin="0" end="{D:.0f}" period="exp({c["debit_secondaire_veh_h"] / 3600:.6f})" from="SJ" to="JE" departSpeed="max"/>',
               "</routes>"]
    rou = d / f"s3_{cfg_id}.rou.xml"
    ecrire(rou, "\n".join(lignes) + "\n")
    rows, a_min = [], []
    for q in range(n_rep):
        fcd = BRUT / "S3" / f"fcd_{cfg_id}_{q}.xml.gz"
        fcd.parent.mkdir(parents=True, exist_ok=True)
        lancer(["-n", str(d / "s3.net.xml"), "-r", str(rou), "--seed", str(graine0 + q), "--end", str(D + 300),
                "--fcd-output", str(fcd), "--fcd-output.attributes", "lane,pos,speed,acceleration",
                "--fcd-output.filter-edges.input-file", str(d / "s3_filtre_fcd.txt")] + options_sumo(cfg_id),
               BRUT / "S3" / f"log_{cfg_id}_{q}.txt")
        tr_maj = trajectoires(fcd, g["decalages_majeure"])
        tr_min = trajectoires(fcd, {"SJ_0": 0.0, "JE_0": g["decalages_mineure"]["JE_0"]})
        P_ = sorted(t for vid, dd in tr_maj.items() if vid.startswith("maj")
                    for t in [franchissement_fin(dd, g["L_W"])] if t == t)
        s_conf_maj = g["decalages_majeure"]["JE_0"]
        P_conf = np.array(sorted(t for vid, dd in tr_maj.items() if vid.startswith("maj")
                                 for t in [franchissement(dd, s_conf_maj)[0]] if t == t))
        a_min += [float(dd["a"].min()) for vid, dd in tr_maj.items() if vid.startswith("maj") and len(dd["a"])]
        t30, td, part = {}, {}, []
        for vid, dd in tr_min.items():
            if not vid.startswith("min"):
                continue
            r = analyse_insertion(dd, g["L_S"], np.asarray(P_))
            if r and r["arret_complet"]:
                m3 = ((g["L_S"] - dd["s"]) <= 3.0) & (dd["s"] <= g["L_S"])
                arr = m3 & (dd["v"] < 0.1)
                if arr.any():
                    t_stop = float(dd["t"][arr][0])
                    cb = creneaux(t_stop, franchissement_fin(dd, g["L_S"]), np.asarray(P_), True, np.nan)
                    t_cf = franchissement(dd, g["decalages_mineure"]["JE_0"])[0]
                    cc = creneaux(t_stop, t_cf, P_conf, True, np.nan) if t_cf == t_cf else None
                    if cb:
                        r["accepte_B"], r["max_rejete_B"] = cb["accepte"], cb["max_rejete"]
                    if cc:
                        r["accepte_C"], r["max_rejete_C"] = cc["accepte"], cc["max_rejete"]
            if r:
                m3 = ((g["L_S"] - dd["s"]) <= 3.0) & (dd["s"] <= g["L_S"])
                r["vmin_3m"] = float(dd["v"][m3].min()) if m3.any() else np.nan
                t30[vid] = franchissement_fin(dd, g["L_S"] - 30.0)
                td[vid] = franchissement_fin(dd, g["L_S"])
                part.append((vid, r))
        for vid, r in part:
            r["libre"] = bool(t30[vid] == t30[vid] and not any(j != vid and t30[j] < t30[vid] < td[j] for j in td))
            rows.append(r)
    return rows, a_min


def franchissement_fin(d, L):
    """Instant où l'avant atteint s = L (extrapolé si le véhicule quitte la voie entre deux pas)."""
    s, t, v = d["s"], d["t"], d["v"]
    i = int(np.searchsorted(s, L))
    if 0 < i < len(s):
        return float(t[i - 1] + (t[i] - t[i - 1]) * (L - s[i - 1]) / max(s[i] - s[i - 1], 1e-9))
    if i >= len(s) and len(s):
        return float(t[-1] + max(L - s[-1], 0.0) / max(v[-1], 0.5))
    return np.nan


def analyse_insertion(d, L_min, P_):
    """Créneaux refusés / accepté d'un non-prioritaire (méthode du volet 03, s3_insertion_cedez.py)."""
    m3 = ((L_min - d["s"]) <= 3.0) & (d["s"] <= L_min)
    if not m3.any() or P_.size < 2:
        return None
    t_a = float(d["t"][m3][0])
    t_d = franchissement_fin(d, L_min)
    if t_d != t_d:
        return None
    arret = bool((m3 & (d["v"] < 0.1)).any())
    duree = float((m3 & (d["v"] < 0.1)).sum()) * PAS
    return creneaux(t_a, t_d, P_, arret, duree)


def creneaux(t_a, t_d, P_, arret, duree):
    k = int(np.searchsorted(P_, t_a))
    if k >= P_.size:
        return None
    rej = []
    if t_d < P_[k]:
        acc, typ = P_[k] - t_a, "lag"
    else:
        rej.append(P_[k] - t_a)
        j = k
        while j + 1 < P_.size and P_[j + 1] <= t_d:
            rej.append(P_[j + 1] - P_[j])
            j += 1
        if j + 1 >= P_.size:
            return None
        acc, typ = P_[j + 1] - P_[j], "gap"
    return {"t_a": t_a, "attente": t_d - t_a, "accepte": float(acc), "type": typ,
            "max_rejete": float(max(rej)) if rej else 0.0, "n_rejetes": len(rej), "arret_complet": arret,
            "max_rejete_creneaux": float(max(rej[1:])) if len(rej) > 1 else 0.0, "duree_arret": duree}


# ----------------------------------------------------------------------------- S4 : courbe
def s4_reseau(variante: str):
    """variante « arete » : l'arc de 60 m est la forme d'une arête, vitesse limite 80 km/h (SUMO ne ralentit
    pas dans une courbe hors carrefour) ; « limitee » : même arête limitée à √(5,5 R), la règle que netconvert
    applique aux voies internes des carrefours (--junctions.limit-turn-speed 5,5). Un nœud de rayon 60 m ne
    convient pas : netconvert en fait une voie interne de 2,6 m limitée à 14 km/h (essai du prototype)."""
    from scenarios import CONVENTIONS
    c = CONVENTIONS["S4"]
    R, La, Lb = c["R_m"], c["droite_amont_m"], c["droite_aval_m"]
    d = DOSSIER / f"S4_courbe_{variante}"
    v_c = 22.22 if variante == "arete" else math.sqrt(5.5 * R)
    pts = [(La + R * math.sin(th), R - R * math.cos(th)) for th in np.linspace(0, math.pi / 2, 31)]
    shape = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
    ecrire(d / "s4.nod.xml", f'<nodes>\n  <node id="A" x="0" y="0" type="priority"/>\n  <node id="C1" x="{La}" y="0" type="priority"/>\n'
           f'  <node id="C2" x="{La + R}" y="{R}" type="priority"/>\n  <node id="B" x="{La + R}" y="{R + Lb}" type="priority"/>\n</nodes>\n')
    ecrire(d / "s4.edg.xml", f'<edges>\n  <edge id="AC" from="A" to="C1" numLanes="1" speed="22.22"/>\n'
           f'  <edge id="CC" from="C1" to="C2" numLanes="1" speed="{v_c:.4f}" shape="{shape}"/>\n'
           f'  <edge id="CB" from="C2" to="B" numLanes="1" speed="22.22"/>\n</edges>\n')
    aretes = ["AC", "CC", "CB"]
    C.netconvert(d, "s4")
    net = sumolib.net.readNet(str(d / "s4.net.xml"), withInternal=True)
    return d, net, aretes


def libre_sumo(sim_proto, cfg_id, scen, d, net, aretes, vma_ms, n=500, periode=40.0, graine=0, add=None):
    """Véhicules isolés (un départ toutes les `periode` s) ; renvoie les trajectoires le long de l'itinéraire."""
    off, Ltot = decalages(net, aretes)
    lignes = ["<routes>", f'  <route id="r" edges="{" ".join(aretes)}"/>']
    if not CONFIGS[cfg_id]["nos_lois"]:
        lignes.append(vtype_defaut(cfg_id))
    for k in range(n):
        typ = "vp"
        if CONFIGS[cfg_id]["nos_lois"]:
            typ = f"t{k:04d}"
            lignes.append(vtype_nos_lois(sim_proto, k, cfg_id, typ, vma_ms))
        lignes.append(f'  <vehicle id="v{k:04d}" type="{typ}" route="r" depart="{k * periode:.1f}" departSpeed="desired"/>')
    lignes.append("</routes>")
    rou = d / f"{scen}_{cfg_id}.rou.xml"
    ecrire(rou, "\n".join(lignes) + "\n")
    fcd = BRUT / scen / f"fcd_{cfg_id}.xml.gz"
    fcd.parent.mkdir(parents=True, exist_ok=True)
    args = ["-n", str(next(d.glob("*.net.xml"))), "-r", str(rou), "--seed", str(graine), "--end", str(n * periode + 300),
            "--fcd-output", str(fcd), "--fcd-output.attributes", "lane,pos,speed,acceleration"] + options_sumo(cfg_id)
    if add:
        args += ["-a", str(add)]
    lancer(args, BRUT / scen / f"log_{cfg_id}.txt")
    return trajectoires(fcd, off), off, Ltot


# ----------------------------------------------------------------------------- S5 : ralentisseur
def s5_reseau(v_ralent_kmh: float, nom: str):
    from scenarios import CONVENTIONS
    c = CONVENTIONS["S5"]
    sh, lh, L = c["ralentisseur_s"], c["longueur_ralentisseur_m"], c["longueur"]
    d = DOSSIER / f"S5_ralentisseur_{nom}"
    ecrire(d / "s5.nod.xml", f'<nodes>\n  <node id="A" x="0" y="0" type="priority"/>\n  <node id="H1" x="{sh}" y="0" type="priority"/>\n'
           f'  <node id="H2" x="{sh + lh}" y="0" type="priority"/>\n  <node id="B" x="{L}" y="0" type="priority"/>\n</nodes>\n')
    ecrire(d / "s5.edg.xml", f'<edges>\n  <edge id="AH" from="A" to="H1" numLanes="1" speed="{30 / 3.6:.4f}"/>\n'
           f'  <edge id="HH" from="H1" to="H2" numLanes="1" speed="{v_ralent_kmh / 3.6:.4f}"/>\n'
           f'  <edge id="HB" from="H2" to="B" numLanes="1" speed="{30 / 3.6:.4f}"/>\n</edges>\n')
    C.netconvert(d, "s5")
    return d, sumolib.net.readNet(str(d / "s5.net.xml"), withInternal=True), ["AH", "HH", "HB"]
