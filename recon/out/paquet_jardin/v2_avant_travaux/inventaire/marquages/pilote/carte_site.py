"""Carte de probabilité de peinture (blanc, jaune) sur tout le site, ortho PCRS 5 cm 2022, par dalles de 50 m
(marge de 3 m pour le fond local), et même calcul sur la BD ORTHO 2024 recalée (rééchantillonnée à 5 cm).

Sortie (cache, hors dépôt par défaut) : <cache>/carte_site_<millesime>.npz : p_blanc, p_jaune (uint8 0-255),
L (uint8), fond (uint8), geo (Xg, Yh). Usage : python -I carte_site.py [--cache DOSSIER] [--millesime 2022|2024]
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun_pilote as C  # noqa: E402
import detection as D  # noqa: E402

EMPRISE = (917129.0, 6460140.0, 917429.0, 6460440.0)
CACHE = Path(os.environ.get("PJ_CACHE_MARQUAGES", Path(tempfile.gettempdir()) / "pj_marquages_avant_travaux"))


def calculer(millesime="2022", emprise=EMPRISE, marge=3.0):
    X0, Y0, X1, Y1 = emprise
    W = int(round((X1 - X0) / C.PX))
    H = int(round((Y1 - Y0) / C.PX))
    out = {k: np.zeros((H, W), np.uint8) for k in ("p_blanc", "p_jaune", "L", "fond")}
    for tx in np.arange(X0, X1, 50.0):
        for ty in np.arange(Y0, Y1, 50.0):
            a, b, c, d = tx - marge, ty - marge, min(tx + 50, X1) + marge, min(ty + 50, Y1) + marge
            if millesime == "2022":
                rgb, geo = C.mosaique_2022(a, b, c, d)
            else:
                rgb, geo = C.mosaique_2024(a, b, c, d)
            cm = D.cartes(rgb)
            pb = D.probabilite_peinture(cm)
            pj = D.probabilite_jaune(cm)
            m = int(round(marge / C.PX))
            h = int(round((min(ty + 50, Y1) - ty) / C.PX))
            w = int(round((min(tx + 50, X1) - tx) / C.PX))
            r0 = int(round((Y1 - min(ty + 50, Y1)) / C.PX))
            c0 = int(round((tx - X0) / C.PX))
            sl = (slice(m, m + h), slice(m, m + w))
            out["p_blanc"][r0:r0 + h, c0:c0 + w] = (pb[sl] * 255).astype(np.uint8)
            out["p_jaune"][r0:r0 + h, c0:c0 + w] = (pj[sl] * 255).astype(np.uint8)
            out["L"][r0:r0 + h, c0:c0 + w] = np.clip(cm["L"][sl], 0, 255).astype(np.uint8)
            out["fond"][r0:r0 + h, c0:c0 + w] = np.clip(cm["fond"][sl], 0, 255).astype(np.uint8)
    out["geo"] = np.array([X0, Y1])
    return out


def charger(millesime="2022", cache=CACHE):
    f = Path(cache) / f"carte_site_{millesime}.npz"
    if not f.exists():
        Path(cache).mkdir(parents=True, exist_ok=True)
        d = calculer(millesime)
        np.savez_compressed(f, **d)
    z = np.load(f)
    return {k: z[k] for k in z.files}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(CACHE))
    ap.add_argument("--millesime", default="2022")
    a = ap.parse_args()
    d = charger(a.millesime, a.cache)
    print({k: v.shape for k, v in d.items()})
