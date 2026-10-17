"""Test d'intégration SUMO : la population exportée reproduit-elle la distribution ONISR des vitesses libres ?

Route droite de 2 km à 50 km/h, une voie, arrivées aléatoires (≈ 60 véh/h, 10 h), conducteurs tirés
par le prototype (vTypeDistribution, Krauss avec sigma = 0 pour isoler le facteur de vitesse).
Mesure à 300 m (avant que les rapides ne rattrapent les lents), véhicules libres = TIV > 5 s.
Comparaison à la loi ONISR 2023 « artères de centre-ville » (moyenne 41,2 km/h, écart-type ajusté).

Usage : python test_sumo_vitesse_libre.py [--travail DOSSIER_TEMPORAIRE]
Nécessite sumo et netconvert dans le PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
from scipy import stats

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import modele_conducteurs as mc  # noqa: E402

TRAVAIL = "D:/DocRoute/17_Modele_Vehicules_Conducteurs/tmp/conducteurs/sumo_test"


def ecrire(chemin, texte):
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(texte)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--travail", default=TRAVAIL)
    ap.add_argument("--graine", type=int, default=2)
    a = ap.parse_args()
    w = a.travail
    os.makedirs(w, exist_ok=True)
    ecrire(f"{w}/n.nod.xml", '<nodes>\n  <node id="A" x="0" y="0"/>\n  <node id="B" x="2000" y="0"/>\n</nodes>\n')
    ecrire(f"{w}/e.edg.xml", '<edges>\n  <edge id="AB" from="A" to="B" numLanes="1" speed="13.89"/>\n</edges>\n')
    ecrire(f"{w}/r2.rou.xml", '<routes>\n  <flow id="f" type="conducteurs_artere_centre_ville_50" begin="0" end="36000" '
                              'probability="0.0167" from="AB" to="AB" departSpeed="desired" departLane="best"/>\n</routes>\n')
    ecrire(f"{w}/det2.add.xml", '<additional>\n  <instantInductionLoop id="boucle" lane="AB_0" pos="300" file="boucle2.xml"/>\n</additional>\n')
    subprocess.run(["netconvert", "--node-files", f"{w}/n.nod.xml", "--edge-files", f"{w}/e.edg.xml",
                    "-o", f"{w}/net.net.xml", "--no-warnings"], check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(ICI, "exporter_sumo.py"), "--n", "1000", "--reseau", "artere_centre_ville_50",
                    "--sortie", f"{w}/vtypes.add.xml", "--sigma", "0", "--graine", str(a.graine)], check=True)
    subprocess.run(["sumo", "-n", f"{w}/net.net.xml", "-a", f"{w}/vtypes.add.xml,{w}/det2.add.xml", "-r", f"{w}/r2.rou.xml",
                    "--step-length", "0.1", "--no-step-log", "--duration-log.disable", "--no-warnings", "--seed", "7",
                    "-e", "36500"], check=True, cwd=w)
    ev = [e.attrib for e in ET.parse(f"{w}/boucle2.xml").getroot() if e.attrib.get("state") == "enter"]
    t = np.array([float(e["time"]) for e in ev])
    v = np.array([float(e["speed"]) for e in ev]) * 3.6
    o = np.argsort(t)
    t, v = t[o], v[o]
    libre = v[np.diff(t, prepend=-1e9) > 5]
    params, _ = mc.charger()
    ref = mc.index(params)["vit.artere_centre_ville_50"]["parametres"]
    ks = stats.kstest(libre, "norm", args=(ref["moyenne"], ref["ecart_type"]))
    res = {"n_vehicules": int(len(v)), "n_libres": int(len(libre)), "moyenne_kmh": round(float(libre.mean()), 2),
           "ecart_type_kmh": round(float(libre.std()), 2), "part_sup_50": round(float((libre > 50.5).mean()), 3),
           "part_sup_60": round(float((libre > 60.5).mean()), 3),
           "reference_ONISR_2023": {"moyenne": ref["moyenne"], "ecart_type_ajuste": ref["ecart_type"], "part_sup_50": 0.15, "part_sup_60": 0.01},
           "KS": round(float(ks.statistic), 4), "p_valeur": round(float(ks.pvalue), 4), "ok": bool(ks.pvalue > 0.05)}
    os.makedirs(os.path.join(mc.DOSSIER_DOC, "validation"), exist_ok=True)
    with open(os.path.join(mc.DOSSIER_DOC, "validation", "test_sumo_vitesse_libre.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
