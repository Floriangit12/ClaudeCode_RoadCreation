#!/usr/bin/env python
"""Dates exactes d'acquisition du LiDAR HD IGN sur l'emprise du site (temps GPS des points).

Prérequis : la dalle COPC téléchargée dans data/sites/paquet_jardin/avant_travaux/lidar_hd/ (non versionnée, 151 Mo) :
  https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_PM_2025-03-25/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz
et PDAL (celui de QGIS : C:/Program Files/QGIS 4.2.3/bin/pdal.exe).
Le temps GPS est en « adjusted standard GPS time » (s depuis 1980-01-06 − 1e9) bien que le bit 0 de global_encoding
ne soit pas positionné ; UTC = GPS − 18 s.

Usage : python -I lidar_dates.py <racine_depot> <dossier_temporaire> [chemin_pdal]
Sortie : recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources/lidar_dates.json
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

RACINE = Path(sys.argv[1]).resolve()
TMP = Path(sys.argv[2]).resolve()
PDAL = sys.argv[3] if len(sys.argv) > 3 else "C:/Program Files/QGIS 4.2.3/bin/pdal.exe"
COPC = RACINE / "data/sites/paquet_jardin/avant_travaux/lidar_hd/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz"
SORTIE = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources/lidar_dates.json"
O = (917279.43, 6460289.98)
G0 = dt.datetime(1980, 1, 6, tzinfo=dt.timezone.utc)


def utc(t):
    return G0 + dt.timedelta(seconds=float(t) + 1e9 - 18)


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    csv = TMP / "lidar_site_gps.csv"
    pipe = {"pipeline": [
        {"type": "readers.copc", "filename": str(COPC), "bounds": f"([{O[0]-150},{O[0]+150}],[{O[1]-150},{O[1]+150}])"},
        {"type": "filters.decimation", "step": 5},
        {"type": "writers.text", "filename": str(csv), "order": "X,Y,GpsTime,PointSourceId,Classification",
         "keep_unspecified": False, "precision": 3}]}
    (TMP / "lidar_site.json").write_text(json.dumps(pipe), encoding="utf-8")
    subprocess.run([PDAL, "pipeline", str(TMP / "lidar_site.json")], check=True)
    a = np.loadtxt(csv, delimiter=",", skiprows=1)
    X, Y, T, P, C = a.T
    x, y = X - O[0], Y - O[1]
    coeur = (np.abs(x) <= 80) & (np.abs(y) <= 80)
    lignes = []
    for pid in np.unique(P):
        m = P == pid
        lignes.append(dict(point_source_id=int(pid), part_site=round(float(m.mean()), 4),
                           part_coeur80=round(float((m & coeur).sum() / coeur.sum()), 4),
                           debut_utc=utc(T[m].min()).isoformat(timespec="seconds"), fin_utc=utc(T[m].max()).isoformat(timespec="seconds")))
    lignes.sort(key=lambda l: l["debut_utc"])

    def parts(mask):
        c = collections.Counter(utc(t).date().isoformat() for t in T[mask])
        n = int(mask.sum())
        return {d: round(v / n, 4) for d, v in sorted(c.items())}
    res = dict(
        genere="outils/lidar_dates.py", dalle="LHD_FXX_0917_6461 (916999,75–917999,75 / 6460000,25–6461000,25)",
        source="https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_PM_2025-03-25/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz",
        metadonnees_wfs=dict(couche="IGNF_LIDAR-HD_METADONNEE:metadata", code_mission="21LHD6PM", date_debut_acquisition="2021-08-12",
                             date_fin_acquisition="2021-09-06", date_edition="2025-03-25", nombre_points_dalle=24199488,
                             capteurs="RIEGL VQ-780 II-S (H2223888, H2225035)", moe_acquisition="Sintegra", moa="IGN"),
        entete_copc=dict(gpstime_max_utc="2021-09-06T05:12:00", gpstime_min="0 (non renseigné)", logiciel="PDAL 2.8.2", creation="2025, jour 213"),
        echantillon="1 point sur 5 dans le carré ± 150 m (n = %d)" % len(T),
        parts_par_jour_site=parts(np.ones(len(T), bool)), parts_par_jour_coeur80=parts(coeur), parts_par_jour_sol_classe2=parts(C == 2),
        lignes_de_vol=lignes)
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("parts_par_jour_site", "parts_par_jour_coeur80", "parts_par_jour_sol_classe2")}, indent=1))


if __name__ == "__main__":
    main()
