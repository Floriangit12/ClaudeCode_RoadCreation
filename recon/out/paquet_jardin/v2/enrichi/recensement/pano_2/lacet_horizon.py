"""lacet_horizon.py : correction de lacet (et de tangage) d'une 360° par corrélation du paysage lointain
(lignes de crête du Vercors, de la Chartreuse et de Belledonne) avec une 360° calée de référence.

Dans la grille (azimut, élévation) du repère local, un défaut de lacet est un simple décalage de colonnes.
Bande d'élévation 3-20° (crêtes), gradients verticaux, corrélation circulaire par FFT (pas 0,05°).
  python lacet_horizon.py <id8> [--ref <id8>] [--test]   -> met à jour poses_pano2.json (lacet, tangage)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import overlay_pnx as OV  # noqa: E402
from camera import camera, camera_calee, charger_poses, image_gris, intrinseques, photo  # noqa: E402
from projection import fenetre_azel  # noqa: E402

PAS = 0.05


def grille(cam, pid, el0=2.0, el1=22.0):
    img = image_gris(pid)
    v, az, el, ok = fenetre_azel(cam, img, 0.0, 360.0 - PAS, el0, el1, PAS)
    v = np.where(ok, v, np.nan)
    g = np.diff(v, axis=0)                      # gradient vertical (lignes de crête)
    g = np.nan_to_num(g)
    g = np.abs(g)
    g = g - g.mean(axis=1, keepdims=True)
    return g


def decalage(gr, gt):
    F = np.fft.rfft(gr, axis=1)
    G = np.fft.rfft(gt, axis=1)
    c = np.fft.irfft((F * np.conj(G)).sum(axis=0), n=gr.shape[1])
    k = int(np.argmax(c))
    n = gr.shape[1]
    s = k if k < n / 2 else k - n
    c2 = np.sort(c)[::-1]
    return s * PAS, float(c[k] / (np.abs(c).mean() + 1e-12))


def ref_proche(ph, pose, exclure=()):
    P = charger_poses()
    best = None
    for k, r in P.items():
        if not r.get("accepte") or r.get("modele") != "equirect" or k in exclure or k == ph.id8:
            continue
        d = math.hypot(r["pose"]["x"] - pose[0], r["pose"]["y"] - pose[1])
        if best is None or d < best[1]:
            best = (k, d)
    return best


def corriger(pid, ref=None, test=False, perturbation=0.0):
    ph = photo(pid)
    if test:
        cam, _ = camera_calee(ph.id8)
        pose = cam.pose.copy()
        pose[3] += perturbation
    else:
        cam, st = OV.camera_photo(ph.id8)
        pose = cam.pose.copy()
    r = ref_proche(ph, pose, exclure=(ph.id8,)) if ref is None else (ref, None)
    camr, _ = camera_calee(r[0])
    gr = grille(camr, r[0])
    camt = camera(ph, pose, intrinseques(ph))
    gt = grille(camt, ph.id8)
    d, pic = decalage(gr, gt)
    # le contenu de la cible est décalé de d degrés : corriger le lacet de -d ou +d (signe vérifié en --test)
    new = pose.copy()
    new[3] = (pose[3] + d) % 360.0
    out = dict(photo=ph.id8, ref=r[0], dist_ref_m=None if r[1] is None else round(r[1], 1), decalage_deg=round(d, 2),
               pic=round(pic, 2), lacet_avant=round(float(pose[3]), 3), lacet_apres=round(float(new[3]), 3))
    if test:
        out["attendu"] = round(-perturbation, 2)
    print(json.dumps(out))
    return new, out


if __name__ == "__main__":
    a = sys.argv[1:]
    test = "--test" in a
    ref = a[a.index("--ref") + 1] if "--ref" in a else None
    pid = a[0]
    if test:
        for pert in (-4.0, 2.5, 6.0):
            corriger(pid, ref, True, pert)
    else:
        new, out = corriger(pid, ref)
        S = ICI / "poses_pano2.json"
        d = json.loads(S.read_text(encoding="utf-8"))
        r = d["photos"][photo(pid).id8]
        r["pose"]["lacet"] = round(float(new[3]), 3)
        r["methode"] = r["methode"].split("+")[0] + "+lacet_horizon"
        r["lacet_horizon"] = out
        S.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
