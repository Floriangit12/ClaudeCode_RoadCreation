"""S3 (volet 03) — ré-analyse des créneaux sur les sorties SUMO existantes (relecture adverse du 17/10/2026).

La v0.1 mesurait le décalage (lag) depuis l'ARRIVÉE à 3 m de la ligne (véhicule encore en mouvement, avant
l'arrêt et le temps de réaction) et les passages des prioritaires à l'ENTRÉE du carrefour. Le volet 05 a montré
que ce choix gonfle le créneau critique estimé (de l'ordre de 3 s). Ce script recalcule, pour les conducteurs
arrêtés à la ligne, trois mesures sur les MÊMES trajectoires :

  A  v0.1 : décalage depuis l'arrivée à 3 m de la ligne ; passages à l'entrée du carrefour (fin de WJ) ;
  B  décalage depuis l'arrêt en tête de ligne (premier instant à moins de 3 m de la ligne avec v < 0,1 m/s) ;
     passages à l'entrée du carrefour ;
  C  comme B, mais passages des prioritaires et du non-prioritaire au POINT DE CONFLIT (début de JE, où les deux
     flux fusionnent).

Créneau critique : maximum de vraisemblance de Troutbeck, loi lognormale (mle_lognormale de s3_insertion_cedez).
Le 5 s du Certu (Carrefours urbains 2010 p. 92-93) est un paramètre de la méthode de capacité (norme), pas une
estimation par maximum de vraisemblance : la comparaison reste indicative.

Entrées : D:/DocRoute/17_Modele_Vehicules_Conducteurs/tmp/03/sumo_brut/S3_insertion_cedez/fcd_*.xml.gz (régénérables
par s3_insertion_cedez.py). Sortie : 03_Modeles_Existants/scenarios_sumo/S3_insertion_cedez/resultats/S3_reanalyse_creneaux.json
  python recon/trafic/etat_art_sumo/s3_reanalyse_creneaux.py [--graines 6]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C  # noqa: E402
import sumolib  # noqa: E402
from s3_insertion_cedez import DOSSIER, VARIANTES, lire, mle_lognormale, t_fin_voie  # noqa: E402


def t_debut_voie(d):
    """Instant (extrapolé vers l'arrière) où l'avant du véhicule entre sur la voie (s = 0)."""
    if not len(d["t"]):
        return np.nan
    return float(d["t"][0] - d["s"][0] / max(d["v"][0], 0.5))


def creneaux(t_a, t_d, P):
    """Créneaux refusés / accepté (même définition que la v0.1, avec des instants donnés)."""
    k = int(np.searchsorted(P, t_a))
    if k >= P.size:
        return None
    rej = []
    if t_d < P[k]:
        return {"accepte": float(P[k] - t_a), "max_rejete": 0.0, "type": "lag"}
    rej.append(P[k] - t_a)
    j = k
    while j + 1 < P.size and P[j + 1] <= t_d:
        rej.append(P[j + 1] - P[j])
        j += 1
    if j + 1 >= P.size:
        return None
    return {"accepte": float(P[j + 1] - P[j]), "max_rejete": float(max(rej)), "type": "gap"}


def analyser(tr, L_maj, L_min):
    P_ent, P_conf = [], []
    for vid, ed in tr.items():
        if vid.startswith("maj_OE"):
            if "WJ" in ed:
                tc = t_fin_voie(ed["WJ"], L_maj)
                if tc == tc:
                    P_ent.append(tc)
            if "JE" in ed:
                P_conf.append(t_debut_voie(ed["JE"]))
    P_ent, P_conf = np.sort(P_ent), np.sort([x for x in P_conf if x == x])
    rows = []
    for vid, ed in tr.items():
        if not vid.startswith("min_SE") or "SJ" not in ed or "JE" not in ed:
            continue
        d = ed["SJ"]
        m3 = (L_min - d["s"]) <= 3.0
        if not m3.any():
            continue
        arret = m3 & (d["v"] < 0.1)
        if not arret.any():
            continue                      # seuls les conducteurs arrêtés à la ligne entrent dans l'estimation
        t_arr3 = float(d["t"][m3][0])
        t_stop = float(d["t"][arret][0])
        t_d_ent = t_fin_voie(d, L_min)
        t_d_conf = t_debut_voie(ed["JE"])
        if not (t_d_ent == t_d_ent and t_d_conf == t_d_conf) or P_ent.size < 2 or P_conf.size < 2:
            continue
        a = creneaux(t_arr3, t_d_ent, P_ent)
        b = creneaux(t_stop, t_d_ent, P_ent)
        c = creneaux(t_stop, t_d_conf, P_conf)
        if a and b and c:
            rows.append({"A": a, "B": b, "C": c, "decalage_arret_s": t_stop - t_arr3})
    return rows


def resume(rows, cle):
    acc = [r[cle]["accepte"] for r in rows]
    rej = [r[cle]["max_rejete"] for r in rows]
    return {"mle": mle_lognormale(acc, rej), "n": len(rows),
            "accepte_mediane_s": round(float(np.median(acc)), 2) if acc else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graines", type=int, default=6)
    a = ap.parse_args()
    out = {"note": __doc__.strip().splitlines()[0], "methodes": {"A": "v0.1 : depuis l'arrivée à 3 m ; entrée du carrefour",
                                                                  "B": "depuis l'arrêt en tête de ligne (v < 0,1 m/s) ; entrée",
                                                                  "C": "depuis l'arrêt ; point de conflit (début de JE)"},
           "resultats": {}}
    for variante in VARIANTES:
        net = sumolib.net.readNet(str(DOSSIER / f"s3_{variante}.net.xml"))
        L_maj, L_min = net.getLane("WJ_0").getLength(), net.getLane("SJ_0").getLength()
        for cfg_id in C.CONFIGS:
            rows = []
            for g in range(a.graines):
                fcd = C.RACINE_BRUT / DOSSIER.name / f"fcd_{variante}_{cfg_id}_g{g}.xml.gz"
                if fcd.exists():
                    rows += analyser(lire(fcd, C.CONFIGS[cfg_id]["step"]), L_maj, L_min)
            r = {k: resume(rows, k) for k in ("A", "B", "C")}
            r["decalage_arrivee_3m_arret_s"] = {"mediane": round(float(np.median([x["decalage_arret_s"] for x in rows])), 2) if rows else None}
            out["resultats"][f"{variante}/{cfg_id}"] = r
            print(variante, cfg_id, {k: (v["mle"] or {}).get("moyenne_s") for k, v in r.items() if k in "ABC"}, flush=True)
    C.json_ecrire(DOSSIER / "resultats" / "S3_reanalyse_creneaux.json", out)


if __name__ == "__main__":
    main()
