"""Catalogue unifié des photos à pose calée et porte géométrique des preuves photo (solveur v2, P1 et P2).

P1 — toutes les poses calées sont utilisées (et seulement elles pour MESURER) :
- Panoramax enrichi/poses/poses.json, poses acceptées (2024-08-24 : 5, 2025-05-18 : 8) ;
- Panoramax 2026-07-28 calées par séquence (calage_sequence.py, pano_2026/poses/poses_2026-07-28.json : 3) ;
- Mapillary sphériques calées (recensement/mapillary/poses/poses_mapillary.json) : « calee_gcp » (poses.py
  sur le SfM, LOO publié) et « calee_bordures » (recalage sur les bordures GAM, contrôle visuel) ; les
  « calee_panoramax » sont la même prise qu'une photo Panoramax déjà comptée ; les perspectives et les
  poses « a_priori » ne servent jamais à mesurer.
L'a priori de séquence de poses.py (--sequence) exige ≥ 2 photos acceptées de la même série : il a été
tenté sur 2374105b, 734a0da6 et 0fe2656f (toujours refusées) et ne peut pas s'appliquer aux séries
2025-08-31 (à plat), 2025-01-12 et 2024-05-01 (aucune photo acceptée). Ces photos ne servent qu'aux
TESTS ORDINAUX de la revue (nombre de mâts, plaques par mât, ordre d'occultation, présence à une date),
qui n'exigent pas de pose fine (revue_coherence.json, photo citée).

P2 — porte géométrique d'une correction A -> C (et de toute hypothèse) : pour chaque photo,
séparation angulaire horizontale A↔C vue de la caméra, rapportée au σ angulaire de la pose à cette
distance, σ(d) = √(σ_rot² + (σ_pos/d)²) ; σ_rot = max(résidu LOO, résidu moyen, 0,1°). Une photo est
« discriminante » si la séparation dépasse 3σ, « décisive » si sa pose a un LOO ≤ 0,5° (P13 : 2ab4efbc,
LOO 0,537°, n'est jamais décisive). Verdict géométrique :
- « complet » : ≥ 2 photos décisives discriminantes dont les visées se coupent sous ≥ 15° ;
- « lateral » : sinon, si ≥ 1 photo décisive discriminante : seule la composante de C − A perpendiculaire
  à la visée moyenne est validée (la profondeur n'est pas observable) ;
- « non_observable » : aucune photo discriminante.
Ces nombres sont imprimés sur chaque planche.
"""
import functools
import math
import sys

import numpy as np

from commun import RACINE, lire_json

sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
from camera import Camera, camera, charger_poses, intrinseques, photo  # noqa: E402

POSES_2026 = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/pano_2026/poses/poses_2026-07-28.json"
POSES_MLY = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/poses/poses_mapillary.json"
SEUIL_LOO_DECISIF = 0.5
SEUIL_SEPARATION = 3.0
ANGLE_INTERSECTION_MIN = 15.0
LAT_MIN_DEFAUT = -21.0


def _cam(ph, q, intr=None):
    intr = {**intrinseques(ph), **(intr or {})}
    return camera(ph, [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]], intr)


@functools.lru_cache(maxsize=1)
def catalogue():
    """Liste ordonnée de photos calées : dict(id, cle, plateforme, date, cam, sigma_rot_deg, sigma_pos_m,
    loo_deg, decisive, statut_pose, lat_min, image (fonction), attribution)."""
    out = []
    for id8, rec in sorted(charger_poses().items()):
        if not rec.get("accepte") or not rec.get("pose"):
            continue
        ph = photo(id8)
        q = rec["qualite"]
        et = rec.get("ecart_type") or {}
        out.append(dict(id=f"pnx:{id8}", cle=id8, plateforme="panoramax", date=rec["date"], cam=_cam(ph, rec["pose"], rec.get("intrinseques")),
                        sigma_rot_deg=max(float(q.get("residu_loo_moy_deg") or 0), float(q.get("residu_moy_deg") or 0), 0.1),
                        sigma_pos_m=max(float(math.hypot(et.get("x", 0.05), et.get("y", 0.05))), 0.05),
                        loo_deg=q.get("residu_loo_moy_deg"), decisive=float(q.get("residu_loo_moy_deg") or 9) <= SEUIL_LOO_DECISIF,
                        statut_pose="calee", lat_min=ph.seq.get("lat_min", LAT_MIN_DEFAUT), image=("pnx", id8),
                        attribution=f"Panoramax {ph.id} ({rec['date']})"))
    if POSES_2026.exists():
        for rec in lire_json(POSES_2026)["photos"]:
            if not rec.get("accepte") or not rec.get("pose"):
                continue
            ph = photo(rec["id8"])
            q = rec["qualite"]
            et = rec.get("ecart_type") or {}
            out.append(dict(id=f"pnx:{rec['id8']}", cle=rec["id8"], plateforme="panoramax_2026", date=rec["date"],
                            cam=_cam(ph, rec["pose"]),
                            sigma_rot_deg=max(float(q.get("residu_loo_moy_deg") or 0), float(q.get("residu_moy_deg") or 0), 0.1),
                            sigma_pos_m=max(float(math.hypot(et.get("x", 0.1), et.get("y", 0.1))), 0.05),
                            loo_deg=q.get("residu_loo_moy_deg"),
                            decisive=float(q.get("residu_loo_moy_deg") or 9) <= SEUIL_LOO_DECISIF,
                            statut_pose="calee_sequence", lat_min=ph.seq.get("lat_min", -25.0), image=("pnx", rec["id8"]),
                            attribution=f"Panoramax IGN {ph.id} (2026-07-28, Licence Ouverte)"))
    if POSES_MLY.exists():
        import mapillary as MLY
        for r in lire_json(POSES_MLY)["images"]:
            if r.get("statut") not in ("calee_gcp", "calee_bordures") or r.get("camera_type") != "spherical":
                continue
            q = r["pose"]
            cam = Camera("equirect", int(r["W"]), int(r["H"]), np.array([q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]]))
            loo = (r.get("qualite") or {}).get("residu_loo_moy_deg")
            out.append(dict(id=f"mly:{r['id']}", cle=r["id"], plateforme="mapillary", date=r["date"], cam=cam,
                            sigma_rot_deg=max(float(r.get("sigma_ang_deg") or 0.4), float(loo or 0)),
                            sigma_pos_m=float(r.get("sigma_pos_m") or 0.3), loo_deg=loo,
                            decisive=bool(r["statut"] == "calee_gcp" and loo is not None and loo <= SEUIL_LOO_DECISIF),
                            statut_pose=r["statut"], lat_min=LAT_MIN_DEFAUT, image=("mly", r["id"]),
                            attribution=f"Mapillary {r['id']} ({r['date']}, {r['attribution']['auteur']}, CC-BY-SA 4.0)"))
    out.sort(key=lambda p: (p["date"], p["id"]))
    return out


def image_rgb(p):
    kind, k = p["image"]
    if kind == "pnx":
        from camera import image_rgb as im
        return im(k)
    import mapillary as MLY
    return MLY.image_rgb_mly(k)


def comptes():
    import collections
    c = collections.Counter((p["plateforme"], p["statut_pose"], p["decisive"]) for p in catalogue())
    return [dict(plateforme=a, statut_pose=b, decisive=d, n=n) for (a, b, d), n in sorted(c.items())]


def sigma_deg(p, d):
    return math.sqrt(p["sigma_rot_deg"] ** 2 + math.degrees(p["sigma_pos_m"] / max(d, 1.0)) ** 2)


def voit(p, P3, h, dmax=40.0, dmin=1.5):
    """La photo voit-elle le pied et le sommet des positions P3 (liste (x, y, z)) ? -> distance min ou None."""
    cam = p["cam"]
    P = np.asarray(P3, float)
    pts = np.vstack([P, P + [0, 0, h]])
    uv, ok, dist = cam.projeter(pts)
    if not ok.all():
        return None
    d = float(np.hypot(*(P[:, :2] - cam.C[:2]).T).min())
    if d < dmin or d > dmax:
        return None
    c = cam.monde_vers_cam(pts)
    lat = np.degrees(np.arctan2(c[:, 2], np.hypot(c[:, 0], c[:, 1])))
    if np.any(lat < p["lat_min"] + 1.0):
        return None
    return d


def photos_pour(P3, h, valide, dmax=40.0, n=None):
    """Photos calées valides à la date de l'objet qui voient toutes les positions : [(score, p, d)]
    triées (décisives d'abord, puis résolution par mètre), n premières."""
    out = []
    for p in catalogue():
        if not valide(p["date"]):
            continue
        d = voit(p, P3, h, dmax=dmax)
        if d is None:
            continue
        res = p["cam"].px_par_rad / d / (1.0 + p["sigma_rot_deg"] / 0.2)
        out.append((round(float(res), 6), p, d))
    out.sort(key=lambda t: (not t[1]["decisive"], -t[0], t[1]["id"]))
    return out[:n] if n else out


def _relevement(C, P):
    return math.degrees(math.atan2(P[0] - C[0], P[1] - C[1])) % 360


def porte(A, C, photos):
    """Porte géométrique P2 entre deux hypothèses A et C (xy) vues par `photos` [(score, p, d)]."""
    A, C = np.asarray(A, float), np.asarray(C, float)
    lignes = []
    for _, p, d in photos:
        Cc = p["cam"].C[:2]
        ra, rc = _relevement(Cc, A), _relevement(Cc, C)
        sep = abs((rc - ra + 180) % 360 - 180)
        sg = sigma_deg(p, d)
        lignes.append(dict(photo=p["id"], date=p["date"], plateforme=p["plateforme"], statut_pose=p["statut_pose"],
                           d_m=round(d, 1), releve_deg=round((ra + rc) / 2 % 360, 1), separation_deg=round(sep, 3),
                           sigma_deg=round(sg, 3), rapport=round(sep / max(sg, 1e-6), 2), decisive=p["decisive"],
                           discriminante=bool(sep > SEUIL_SEPARATION * sg)))
    disc = [x for x in lignes if x["discriminante"] and x["decisive"]]
    ang = 0.0
    for i in range(len(disc)):
        for j in range(i + 1, len(disc)):
            a = abs((disc[i]["releve_deg"] - disc[j]["releve_deg"]) % 180)
            ang = max(ang, min(a, 180 - a))
    D = C - A
    out = dict(photos=lignes, n_photos=len(lignes), n_discriminantes=len(disc), angle_intersection_max_deg=round(ang, 1),
               d_AC_m=round(float(np.hypot(*D)), 3))
    if len(disc) >= 2 and ang >= ANGLE_INTERSECTION_MIN:
        out.update(verdict="complet", composante_validee_m=round(float(np.hypot(*D)), 3))
    elif disc:
        # visée moyenne des photos discriminantes (vecteurs unitaires, sens caméra -> objet)
        v = np.zeros(2)
        for x in disc:
            r = math.radians(x["releve_deg"])
            v += np.array([math.sin(r), math.cos(r)])
        v /= max(np.hypot(*v), 1e-9)
        lat = np.array([v[1], -v[0]])
        out.update(verdict="lateral", direction_visee=[round(float(v[0]), 4), round(float(v[1]), 4)],
                   direction_laterale=[round(float(lat[0]), 4), round(float(lat[1]), 4)],
                   composante_validee_m=round(float(D @ lat), 3), composante_profondeur_m=round(float(D @ v), 3))
    else:
        out.update(verdict="non_observable", composante_validee_m=0.0)
    return out


def projection_laterale(A, C, g):
    """Position validée par la porte : C si « complet », A + composante latérale si « lateral », A sinon."""
    A, C = np.asarray(A, float), np.asarray(C, float)
    if g["verdict"] == "complet":
        return C
    if g["verdict"] == "lateral":
        lat = np.asarray(g["direction_laterale"], float)
        return A + lat * float((C - A) @ lat)
    return A
