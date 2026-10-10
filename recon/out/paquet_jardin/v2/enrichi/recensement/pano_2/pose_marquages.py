"""pose_marquages.py : pose approchée d'une photo 360° par contraste des marquages (agent VISION-PANORAMAX-2).

Principe : les marquages blancs/jaunes de la description (états conservés, refaits et fantômes = présents
avant les travaux 2025 ; pas les marquages neufs 2025) sont échantillonnés en paires de points de part et
d'autre de leurs bords (intérieur à 0,04 m, extérieur à 0,18 m). Pour une pose candidate, on projette les
paires dans la photo (niveaux de gris HD) et on mesure le contraste moyen intérieur - extérieur (écrêté).
Recherche grossière puis fine sur (x, y, lacet), puis (tangage, roulis, z). Départ : a priori de séquence
(voisins acceptés du même jour) sinon GNSS brut. Comme le GNSS est biaisé et que les marquages se
répètent, la pose retenue est relue visuellement (overlay_pnx) avant usage ; résultat dans poses_pano2.json.

  python pose_marquages.py <id8> ... [--test] [--rayon 25]
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
from camera import camera, charger_poses, echantillonner, image_gris, intrinseques, photo, pose_brute, z_sol  # noqa: E402
import poses as PS  # noqa: E402

SORTIE = ICI / "poses_pano2.json"


def _pip(x, y, r):
    c = False
    j = len(r) - 1
    for i in range(len(r)):
        if ((r[i, 1] > y) != (r[j, 1] > y)) and (x < (r[j, 0] - r[i, 0]) * (y - r[i, 1]) / (r[j, 1] - r[i, 1] + 1e-12) + r[i, 0]):
            c = not c
        j = i
    return c


_PAIRES = None


def paires():
    """(N, 3) intérieur, (N, 3) extérieur, ids des marquages (local, z du MNT + 1 cm)."""
    global _PAIRES
    if _PAIRES is not None:
        return _PAIRES
    d = OV.lire(OV.DESC / "base/marquages.geojson")
    A, B, I = [], [], []
    for f in d["features"]:
        p = f["properties"]
        if p.get("etat") == "neuf_2025":
            continue
        g = f["geometry"]
        if g["type"] in ("Polygon", "MultiPolygon"):
            for ring in OV._anneaux(g):
                r = OV.local(np.array(ring)[:, :2])
                if len(r) < 4:
                    continue
                for a, b in zip(r[:-1], r[1:]):
                    L = float(np.linalg.norm(b - a))
                    if L < 0.08:
                        continue
                    t = (b - a) / L
                    n = np.array([t[1], -t[0]])
                    m = (a + b) / 2
                    if _pip(*(m + 0.03 * n), r):
                        n = -n
                    for s in np.arange(0.05, L - 0.02, 0.12):
                        q = a + t * s
                        A.append(q - 0.04 * n)
                        B.append(q + 0.18 * n)
                        I.append(p["id"])
        elif g["type"] in ("LineString", "MultiLineString"):
            w = float(p.get("largeur_m") or 0.15)
            for ring in OV._anneaux(g):
                r = OV.local(np.array(ring)[:, :2])
                for a, b in zip(r[:-1], r[1:]):
                    L = float(np.linalg.norm(b - a))
                    if L < 0.05:
                        continue
                    t = (b - a) / L
                    n = np.array([t[1], -t[0]])
                    for s in np.arange(0.0, L, 0.15):
                        q = a + t * s
                        for sg in (1, -1):
                            A.append(q)
                            B.append(q + sg * (w / 2 + 0.15) * n)
                            I.append(p["id"])
    A, B = np.array(A), np.array(B)
    A = np.c_[A, OV.z_mnt(A[:, 0], A[:, 1]) + 0.01]
    B = np.c_[B, OV.z_mnt(B[:, 0], B[:, 1]) + 0.01]
    _PAIRES = (A, B, np.array(I))
    return _PAIRES


def scoreur(ph, rayon=25.0, p_ref=None):
    img = image_gris(ph.id8)
    intr = intrinseques(ph)
    A, B, I = paires()
    lat_min = math.radians((ph.seq.get("lat_min") or -25.0) + 1.0)
    C0 = p_ref[:2]
    d = np.hypot(A[:, 0] - C0[0], A[:, 1] - C0[1])
    k = (d > 3.0) & (d < rayon + 6)
    A, B = A[k], B[k]

    def score(p, detail=False):
        c = camera(ph, p, intr)
        ca, cb = c.monde_vers_cam(A), c.monde_vers_cam(B)
        dist = np.hypot(A[:, 0] - p[0], A[:, 1] - p[1])
        lat = np.arctan2(ca[:, 2], np.hypot(ca[:, 0], ca[:, 1]))
        ok = (dist > 3.0) & (dist < rayon) & (lat > lat_min)
        if ok.sum() < 50:
            return -1.0
        ua, _ = c.cam_vers_pixel(ca[ok])
        ub, _ = c.cam_vers_pixel(cb[ok])
        ia = echantillonner(img, ua[:, 0], ua[:, 1], boucle=True)
        ib = echantillonner(img, ub[:, 0], ub[:, 1], boucle=True)
        dd = np.clip(ia - ib, -0.25, 0.25)
        w = 1.0 / (1.0 + dist[ok] / 10.0)
        s = float((dd * w).sum() / w.sum())
        if detail:
            return s, int(ok.sum()), float((dd > 0.03).mean())
        return s
    return score


def grille(score, p, axes, n=None):
    best_s, best_p = score(p), p.copy()
    for vals in axes:
        pass
    return best_s, best_p


def chercher(score, p0, dxy, nxy, dl, nl):
    """Recherche exhaustive (x, y, lacet) autour de p0, z suivant le MNT."""
    best = (score(p0), p0.copy())
    h = p0[2] - z_sol(p0[0], p0[1])
    for dx in np.arange(-nxy, nxy + 1) * dxy:
        for dy in np.arange(-nxy, nxy + 1) * dxy:
            q = p0.copy()
            q[0] += dx
            q[1] += dy
            q[2] = z_sol(q[0], q[1]) + h
            for da in np.arange(-nl, nl + 1) * dl:
                q2 = q.copy()
                q2[3] += da
                s = score(q2)
                if s > best[0]:
                    best = (s, q2)
    return best


def affiner(score, p, pas_angle=0.25, pas_z=0.1):
    best = score(p)
    for _ in range(2):
        for j, pas, n in ((4, pas_angle, 6), (5, pas_angle, 6), (2, pas_z, 4), (3, 0.1, 5)):
            for v in p[j] + np.arange(-n, n + 1) * pas:
                q = p.copy()
                q[j] = v
                s = score(q)
                if s > best:
                    best, p = s, q
    return best, p


def caler(pid, test=False, rayon=25.0):
    t0 = time.time()
    ph = photo(pid)
    pb = pose_brute(ph)
    p_brut = pb["pose"].copy()
    seq = PS.a_priori_sequence(ph, p_brut)
    if seq is not None:
        p0 = seq["pose"].copy()
        rxy, rl = 1.6, 3.0
    else:
        p0 = p_brut.copy()
        p0[2] = z_sol(p0[0], p0[1]) + ph.seq["h"]
        acc = float(ph.meta.get("horizontal_accuracy_m") or 5.0)
        rxy, rl = min(max(acc, 2.0), 6.0), 10.0
    score = scoreur(ph, rayon, p0)
    s0 = score(p0)
    # grossier
    s, p = chercher(score, p0, 0.4, int(round(rxy / 0.4)), 1.0, int(rl))
    s, p = affiner(score, p, 0.5, 0.15)
    s, p = chercher(score, p, 0.1, 4, 0.2, 4)
    s, p = affiner(score, p, 0.2, 0.05)
    s_fin, n_pts, frac = score(p, detail=True)
    # unicité : meilleur score à > 1,5 m ou > 3° de la solution
    rec = dict(id8=ph.id8, date=ph.date, methode="contraste_marquages" + ("+a_priori_sequence" if seq is not None else "+gnss_brut"),
               voisins=seq["voisins"] if seq else [], score_depart=round(s0, 4), score=round(s_fin, 4), n_points=n_pts,
               frac_positifs=round(frac, 3),
               pose=dict(x=round(float(p[0]), 3), y=round(float(p[1]), 3), z=round(float(p[2]), 3), lacet=round(float(p[3]), 3),
                         tangage=round(float(p[4]), 3), roulis=round(float(p[5]), 3)),
               depart=dict(x=round(float(p0[0]), 3), y=round(float(p0[1]), 3), lacet=round(float(p0[3]), 3)),
               deplacement_m=round(float(np.hypot(p[0] - p0[0], p[1] - p0[1])), 2), dlacet=round(float(p[3] - p0[3]), 2),
               duree_s=round(time.time() - t0, 1), qualite="a_verifier")
    if test:
        P = charger_poses()[ph.id8]["pose"]
        Pa = np.array([P["x"], P["y"], P["z"], P["lacet"], P["tangage"], P["roulis"]])
        rec["score_pose_calee"] = round(score(Pa), 4)
        rec["ecart_a_la_pose_calee"] = dict(dxy=round(math.hypot(p[0] - P["x"], p[1] - P["y"]), 2),
                                           dlacet=round(p[3] - P["lacet"], 2), dtangage=round(p[4] - P["tangage"], 2),
                                           depart_dxy=round(math.hypot(p0[0] - P["x"], p0[1] - P["y"]), 2),
                                           depart_dlacet=round(p0[3] - P["lacet"], 2))
    print(json.dumps(rec), flush=True)
    return rec


def enregistrer(recs):
    d = json.loads(SORTIE.read_text(encoding="utf-8")) if SORTIE.exists() else {"photos": {}}
    for r in recs:
        old = d["photos"].get(r["id8"], {})
        if old.get("qualite") not in (None, "a_verifier"):
            r["qualite"] = old["qualite"]
        d["photos"][r["id8"]] = r
    d["description"] = ("poses approchées VISION-PANORAMAX-2 (contraste des marquages pré-2025 ; a priori de séquence ou GNSS) ; "
                        "qualite = revue visuelle des superpositions ; ne remplace pas enrichi/poses/poses.json")
    SORTIE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    a = sys.argv[1:]
    test = "--test" in a
    rayon = 25.0
    if "--rayon" in a:
        rayon = float(a[a.index("--rayon") + 1])
    ids = [x for x in a if not x.startswith("--") and not x.replace('.', '').isdigit()]
    recs = [caler(i, test, rayon) for i in ids]
    if not test:
        enregistrer(recs)
