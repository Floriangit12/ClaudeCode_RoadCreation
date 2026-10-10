"""pose_pano2.py : pose approchée des photos 360° sans pose calée (agent VISION-PANORAMAX-2).

Départ : a priori de séquence (poses.a_priori_sequence, voisins acceptés du même jour) sinon pose brute GNSS.
Affinage : corrélation globale photo / ortho PCRS 2022 drapée sur le MNT 2026 (score de poses.recalage_sol,
étendu à x, y), descente par coordonnées (lacet, x/y, tangage/roulis/z) à pas décroissants.
Écrit pano_2/poses_pano2.json (ne touche pas enrichi/poses/). Qualité = gain de NCC + revue visuelle (overlay_pnx).
Validité : le sol doit être inchangé depuis 2022 (hors zones de travaux) pour que la corrélation ait un sens.

  python pose_pano2.py <id8> [<id8> ...] [--test]   (--test : part de la pose brute d'une photo déjà calée et compare)
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import overlay_pnx as OV  # noqa: E402
import gcp as G  # noqa: E402
from camera import camera, charger_poses, image_gris, intrinseques, photo, pose_brute, z_sol  # noqa: E402
from projection import intersection_sol, ortho_valeur  # noqa: E402
import poses as PS  # noqa: E402

SORTIE = ICI / "poses_pano2.json"


def scoreur(ph, reduction=8, dmin=2.5, dmax=30.0):
    img = image_gris(ph.id8)
    H, W = img.shape
    hr, wr = H // reduction, W // reduction
    petit = img[: hr * reduction, : wr * reduction].reshape(hr, reduction, wr, reduction).mean((1, 3))
    jj, ii = np.mgrid[0:hr, 0:wr]
    uv = np.c_[(ii.ravel() + 0.5) * reduction, (jj.ravel() + 0.5) * reduction]
    ph_hp = G.passe_haut(petit, 3).ravel()
    lat_min = G.lat_min_cam(ph)
    intr = intrinseques(ph)

    def score(p):
        c = camera(ph, p[:6], intr)
        bc = c.pixel_vers_cam(uv)
        lat = np.degrees(np.arcsin(np.clip(bc[:, 2], -1, 1)))
        sel = lat > lat_min + 1.0
        sel &= lat < -2.0
        d = bc[sel] @ c.R
        t = intersection_sol(c.C, d, n_iter=2)
        dist = t * np.hypot(d[:, 0], d[:, 1])
        ok = np.isfinite(t) & (dist > dmin) & (dist < dmax)
        if ok.sum() < 200:
            return -1.0
        X = c.C + np.nan_to_num(t)[:, None] * d
        v = np.where(ok, ortho_valeur(X[:, 0], X[:, 1]), np.nan)
        ok &= np.isfinite(v)
        full = np.full(len(uv), np.nan)
        idx = np.nonzero(sel)[0]
        full[idx[ok]] = v[ok]
        okf = np.isfinite(full)
        img_r = np.where(okf, full, np.nanmean(full[okf])).reshape(hr, wr)
        r_hp = G.passe_haut(img_r, 3).ravel()
        a, b = ph_hp[okf], r_hp[okf]
        a = a - a.mean()
        b = b - b.mean()
        return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12))
    return score


def descente(score, p0, plan):
    p = np.array(p0, float)
    best = score(p)
    for j, pas, n in plan:
        if j == "xy":
            vals = [(dx, dy) for dx in np.arange(-n, n + 1) * pas for dy in np.arange(-n, n + 1) * pas]
            sc = []
            for dx, dy in vals:
                q = p.copy()
                q[0] += dx
                q[1] += dy
                q[2] = z_sol(q[0], q[1]) + (p[2] - z_sol(p[0], p[1]))
                sc.append(score(q))
            k = int(np.argmax(sc))
            if sc[k] > best:
                best = sc[k]
                p[0] += vals[k][0]
                p[1] += vals[k][1]
                p[2] = z_sol(p[0], p[1]) + (p[2] - z_sol(p[0] - vals[k][0], p[1] - vals[k][1]))
        else:
            vals = p[j] + np.arange(-n, n + 1) * pas
            sc = []
            for v in vals:
                q = p.copy()
                q[j] = v
                sc.append(score(q))
            k = int(np.argmax(sc))
            if sc[k] > best:
                best = sc[k]
                p[j] = vals[k]
    return p, best


def caler(pid, test=False):
    t0 = time.time()
    ph = photo(pid)
    pb = pose_brute(ph)
    p_brut = pb["pose"].copy()
    seq = PS.a_priori_sequence(ph, p_brut)
    p0 = seq["pose"].copy() if seq is not None else p_brut.copy()
    if seq is None:
        p0[2] = z_sol(p0[0], p0[1]) + ph.seq["h"]
    sc = scoreur(ph)
    s0 = sc(p0)
    plan = [(3, 1.0, 6), ("xy", 0.5, 4), (3, 0.5, 3), ("xy", 0.25, 2), (4, 0.5, 3), (5, 0.5, 3), (2, 0.1, 3),
            (3, 0.2, 3), ("xy", 0.15, 2), (4, 0.2, 2), (5, 0.2, 2)]
    p, s1 = descente(sc, p0, plan)
    rec = dict(id8=ph.id8, date=ph.date, methode="a_priori_sequence+ncc_ortho2022" if seq is not None else "brute+ncc_ortho2022",
               voisins=seq["voisins"] if seq else [], ncc_depart=round(s0, 4), ncc=round(s1, 4),
               pose=dict(x=round(float(p[0]), 3), y=round(float(p[1]), 3), z=round(float(p[2]), 3), lacet=round(float(p[3]), 3),
                         tangage=round(float(p[4]), 3), roulis=round(float(p[5]), 3)),
               depart=dict(x=round(float(p0[0]), 3), y=round(float(p0[1]), 3), lacet=round(float(p0[3]), 3)),
               deplacement_m=round(float(np.hypot(p[0] - p0[0], p[1] - p0[1])), 2), dlacet=round(float(p[3] - p0[3]), 2),
               duree_s=round(time.time() - t0, 1))
    rec["qualite"] = "a_verifier"
    if test:
        P = charger_poses()[ph.id8]["pose"]
        rec["ecart_a_la_pose_calee"] = dict(dxy=round(math.hypot(p[0] - P["x"], p[1] - P["y"]), 2),
                                           dlacet=round(p[3] - P["lacet"], 2), dtangage=round(p[4] - P["tangage"], 2),
                                           depart_dxy=round(math.hypot(p0[0] - P["x"], p0[1] - P["y"]), 2),
                                           depart_dlacet=round(p0[3] - P["lacet"], 2))
    print(json.dumps(rec), flush=True)
    return rec


def enregistrer(recs):
    d = json.loads(SORTIE.read_text(encoding="utf-8")) if SORTIE.exists() else {"photos": {}}
    for r in recs:
        d["photos"][r["id8"]] = r
    d["description"] = ("poses approchées VISION-PANORAMAX-2 (a priori de séquence + NCC ortho 2022) ; "
                        "qualite = revue visuelle des superpositions ; ne remplace pas enrichi/poses/poses.json")
    SORTIE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    a = sys.argv[1:]
    test = "--test" in a
    ids = [x for x in a if not x.startswith("--")]
    recs = [caler(i, test) for i in ids]
    if not test:
        enregistrer(recs)
