"""Outils communs aux scénarios de démonstration SUMO (volet 03, état de l'art des modèles).

But : montrer concrètement, sur 3 situations simples (file sur route droite, arrêt au feu,
insertion en cédez-le-passage), ce que font les modèles de poursuite Krauss (défaut SUMO) et
EIDM (Salles et al. 2020), avec leurs paramètres PAR DÉFAUT, et où ils s'écartent du réel.

Aucune donnée inventée : les valeurs de référence « réelles » utilisées pour comparer sont
centralisées dans REFERENCES ci-dessous, chacune avec sa source (document, page, année).

Écritures : uniquement sous D:\\DocRoute\\17_Modele_Vehicules_Conducteurs\\03_Modeles_Existants\\
scenarios_sumo\\ (données, résultats) ; ce module ne touche ni recon/generateur ni assets/specs/route.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SUMO_HOME = Path(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"))
if str(SUMO_HOME / "tools") not in sys.path:
    sys.path.append(str(SUMO_HOME / "tools"))

RACINE_SORTIE = Path(r"D:\DocRoute\17_Modele_Vehicules_Conducteurs\03_Modeles_Existants\scenarios_sumo")
# Sorties brutes volumineuses (FCD .xml.gz, journaux sumo) : temporaires, régénérables par les scripts.
RACINE_BRUT = Path(r"D:\DocRoute\17_Modele_Vehicules_Conducteurs\tmp\03\sumo_brut")

# --------------------------------------------------------------------------------------------
# Configurations de modèles comparées. Paramètres PAR DÉFAUT de SUMO 1.27.1 (vClass passenger) :
# accel 2.6, decel 4.5, emergencyDecel 9, minGap 2.5, tau 1.0, length 5, speedFactor normc(1,0.1,0.2,2)
# (doc SUMO « Vehicle_Type_Parameter_Defaults » et « Definition_of_Vehicles... », tableau vType).
# Krauss : sigma 0.5 (doc vType). EIDM : treaction 0.5, tpreview 4, jerkmax 3, sigmaerror 0.04
# (code MSCFModel_EIDM.cpp l.56-71 ; la doc annonce 0.10 pour sigmaerror -> écart doc/code noté).
# --------------------------------------------------------------------------------------------
CONFIGS = {
    "krauss_pas1s": {"cf": "Krauss", "step": 1.0, "libelle": "Krauss (défaut), pas 1 s"},
    "krauss_pas01s": {"cf": "Krauss", "step": 0.1, "libelle": "Krauss (défaut), pas 0,1 s"},
    "eidm_pas01s": {"cf": "EIDM", "step": 0.1, "libelle": "EIDM (défaut), pas 0,1 s"},
}

# --------------------------------------------------------------------------------------------
# Valeurs de référence (réel ou norme) utilisées dans les graphes. Chaque entrée : valeur + source.
# --------------------------------------------------------------------------------------------
REFERENCES = {
    "saturation_fr": {
        "valeur": 1800.0, "unite": "uvpd/h/voie (=> 2,0 s/véh)", "nature": "norme (valeur moyenne de dimensionnement)",
        "source": "CERTU, Guide de conception des carrefours à feux, 2010, p. 34 (§4.8)"},
    "jaune_fr": {
        "valeur": 3.0, "unite": "s", "nature": "norme (réglementation, en agglomération)",
        "source": "CERTU, Guide de conception des carrefours à feux, 2010, p. 68"},
    "temps_perdu_demarrage": {
        "valeur": 2.0, "unite": "s", "nature": "valeur usuelle (« commonly assumed »)",
        "source": "FHWA Traffic Signal Timing Manual, FHWA-HOP-08-024, 2008, p. 3-5"},
    "zone_indecision": {
        "valeur": {"P_arret_90pc_TTS_s": 5.5, "P_arret_10pc_TTS_s": 2.5}, "unite": "s (temps jusqu'à la ligne)",
        "nature": "synthèse de mesures (Zegeer & Deen ; ITE ; Chang et al.)",
        "source": "FHWA Traffic Signal Timing Manual, 2008, p. 4-25 (fig. 4-18/4-19)"},
    "chang_85pc": {
        "valeur": {"TTS_s": 3.0, "P_arret": 0.85, "TTS_passe_s": 2.0}, "unite": "s",
        "nature": "mesure (Chang et al., cité)",
        "source": "FHWA Traffic Signal Timing Manual, 2008, p. 4-25"},
    "decel_ite_jaune": {
        "valeur": 3.05, "unite": "m/s² (10 ft/s²)", "nature": "valeur de dimensionnement souvent citée (ITE)",
        "source": "FHWA Traffic Signal Timing Manual, 2008, p. 5-13 (éq. 5-3, PDF p. 138)"},
    "decel_cerema_arret": {
        "valeur": {"30-50 km/h": 0.46 * 9.81, "70 km/h": 0.44 * 9.81}, "unite": "m/s²",
        "nature": "norme de conception (distance d'arrêt, TPR 1,8 s)",
        "source": "Cerema, Révision des règles sur la visibilité, oct. 2018, p. 13 (§3.2)"},
    "creneau_critique_fr": {
        "valeur": {"30 km/h": 4.0, "50 km/h": 5.0, "70 km/h": 6.0}, "unite": "s",
        "nature": "norme (insertion TAD/TAG, voie principale à sens unique ou TAD double sens)",
        "source": "CERTU, Carrefours urbains, 2010, p. 93"},
    "temps_inter_idm_shanghai": {
        "valeur": {"moyenne": 0.878, "ecart_type": 0.334, "p5": 0.356, "p95": 1.432}, "unite": "s",
        "nature": "mesure (paramètre T de l'IDM calé sur 42 conducteurs, SH-NDS, voies rapides urbaines)",
        "source": "Zhu, Wang, Tarko, Fang 2018, Transp. Res. C 93 (arXiv 1811.06395), tableau 2 p. 14"},
    "temps_inter_idm_stuttgart": {
        "valeur": {"min": 1.03, "max": 1.51}, "unite": "s",
        "nature": "mesure (IDM calé sur 3 trajectoires radar, Stuttgart, ville, 1995)",
        "source": "Kesting & Treiber 2008 (arXiv 0803.4063), tableau 1 p. 7"},
    "jiang_sv_50kmh": {
        "valeur": {"rang_1": 0.84, "rang_9": 1.3, "rangs_20_25": 1.5}, "unite": "m/s (écart-type de la vitesse de chaque véhicule)",
        "nature": "mesure (file de 25 voitures, meneur consigne 50 km/h, GPS ±1 km/h) — lecture graphique ±0,1 m/s",
        "source": "Jiang et al. 2014, PLoS ONE 9(4) e94351, fig. 5D (points expérimentaux), p. 7"},
    "demarrage_salles": {
        "valeur": {"t_1ms_s": 0.8, "t_amax_s": 2.3, "ecart_type_accel": 0.5}, "unite": "s ; m/s²",
        "nature": "mesure (>2000 démarrages, véhicules instrumentés ; drone Stuttgart 2018)",
        "source": "Salles, Kaufmann, Reuss 2020, SUMO User Conf. 2020, p. 14"},
}


def ecrire(path: Path, texte: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texte, encoding="utf-8")


def netconvert(dossier: Path, nom: str, extra: list[str] | None = None) -> Path:
    """Construit <nom>.net.xml à partir de <nom>.nod.xml / .edg.xml (/ .con.xml si présent)."""
    args = ["netconvert", "--node-files", str(dossier / f"{nom}.nod.xml"),
            "--edge-files", str(dossier / f"{nom}.edg.xml"),
            "--output-file", str(dossier / f"{nom}.net.xml"),
            "--no-turnarounds", "true", "--offset.disable-normalization", "true"]
    con = dossier / f"{nom}.con.xml"
    if con.exists():
        args += ["--connection-files", str(con)]
    if extra:
        args += extra
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"netconvert a échoué : {r.stderr}")
    return dossier / f"{nom}.net.xml"


def lancer_sumo(cfg: list[str], log: Path) -> None:
    r = subprocess.run(["sumo"] + cfg, capture_output=True, text=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"sumo a échoué ({log}) : {r.stderr[-2000:]}")


def lire_fcd(path: Path):
    """Itère (t, id, lane, pos, speed, accel) sur une sortie FCD (.xml ou .xml.gz)."""
    ouvre = gzip.open if str(path).endswith(".gz") else open
    with ouvre(path, "rb") as f:
        t = None
        for ev, el in ET.iterparse(f, events=("start", "end")):
            if ev == "start" and el.tag == "timestep":
                t = float(el.get("time"))
            elif ev == "end" and el.tag == "vehicle":
                yield (t, el.get("id"), el.get("lane"), float(el.get("pos")), float(el.get("speed")),
                       float(el.get("acceleration", "nan")))
                el.clear()
            elif ev == "end" and el.tag == "timestep":
                el.clear()


def percentiles(x, ps=(5, 25, 50, 75, 95)):
    import numpy as np
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {f"p{p}": None for p in ps} | {"n": 0, "moyenne": None, "ecart_type": None}
    d = {f"p{p}": round(float(np.percentile(x, p)), 3) for p in ps}
    d.update({"n": int(x.size), "moyenne": round(float(x.mean()), 3), "ecart_type": round(float(x.std(ddof=1)) if x.size > 1 else 0.0, 3),
              "min": round(float(x.min()), 3), "max": round(float(x.max()), 3)})
    return d


def json_ecrire(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def style_graphes():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 100, "font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})
    return plt


COULEURS = {"krauss_pas1s": "#d95f02", "krauss_pas01s": "#7570b3", "eidm_pas01s": "#1b9e77", "reel": "#333333"}
