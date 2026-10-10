"""Triangulation multi-photos et vérification des positions d'objets (mâts) par les photos calées.

Fonctions :
- trianguler(observations) : point 3D (moindres carrés sur les erreurs angulaires) depuis
  [(photo_id, (u, v)), ...] ; renvoie point, covariance, écarts types, résidus (deg) ;
- trianguler_verticale(observations) : axe vertical (x, y) d'un mât depuis des pixels pris
  n'importe où sur son axe (chaque observation = plan vertical caméra-axe) ;
- pose_sans(rec, gcp_ids) : pose de la photo réajustée SANS certains GCP (validation honnête :
  un mât n'est pas jugé par des poses calées sur lui-même) ;
- verifier_mat(objet) : pointe un mât (catalogue ou mobilier « à vérifier ») sur toutes les photos
  calées qui le voient, triangule son axe (RANSAC), compare à la position du paquet et conclut
  (confirmé / déplacé de d m / non retrouvé). C'est l'outil qui répond à « l'objet qui devait être
  ici est-il plutôt là ? ».
CLI : python triangulation.py --valider [--n 5]   (validation sur des mâts levés)
      python triangulation.py --verifier-tout       (tous les mâts du mobilier, y compris à vérifier)
Sorties : enrichi/poses/triangulation.json, planches/triangulation_*.jpg
"""
import argparse
import math

import numpy as np

from camera import (DONNEES, SORTIE, arrondi, camera, camera_calee, charger_poses, ecrire_json,
                    image_gris, intrinseques, lire_json, photo, z_sol)
import gcp as G

SIG_PIX_DEG = 0.08      # incertitude d'un pointage automatique (360° : ≈ 1,3 px)
SEUIL_DEPLACEMENT_M = 0.75     # au-delà : changement de support possible -> revue visuelle obligatoire
REVUES = SORTIE / "revue_visuelle.json"
TOLERANCE_PLACEMENT_M = 0.35   # écart au-delà duquel une position du paquet est à corriger
                               # (axe de mât ; le LiDAR 2021 donne souvent la tête, décalée de 0,2-0,3 m)


# --------------------------------------------------------------------------- triangulation
def _rayons(observations, poses=None):
    poses = charger_poses() if poses is None else poses
    C, D, S = [], [], []
    for pid, uv in observations:
        cam, statut = camera_calee(pid, poses, accepte_seulement=True)
        if statut != "calee":
            continue
        C.append(cam.C)
        D.append(cam.rayons(np.asarray(uv, float)[None])[0])
        q = poses[photo(pid).id8]["qualite"]
        S.append(math.radians(math.hypot(SIG_PIX_DEG, q["residu_moy_deg"])))
    return np.array(C).reshape(-1, 3), np.array(D).reshape(-1, 3), np.array(S)


def trianguler(observations, poses=None):
    """Point 3D vu dans plusieurs photos calées : observations = [(photo_id, (u, v)), ...].
    Renvoie dict(point, covariance, ecart_type, residus_deg, n) ou None (< 2 rayons)."""
    C, D, S = _rayons(observations, poses)
    if len(C) < 2:
        return None
    # solution linéaire (point le plus proche des rayons)
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for c, d, s in zip(C, D, S):
        M = np.eye(3) - np.outer(d, d)
        A += M / s ** 2
        b += M @ c / s ** 2
    P = np.linalg.solve(A, b)
    # Gauss-Newton sur les erreurs angulaires
    for _ in range(10):
        r, J = [], []
        for c, d, s in zip(C, D, S):
            v = P - c
            n = np.linalg.norm(v)
            e1 = np.cross(d, [0, 0, 1.0])
            e1 = e1 / np.linalg.norm(e1) if np.linalg.norm(e1) > 1e-6 else np.array([1.0, 0, 0])
            e2 = np.cross(e1, d)
            u = v / n
            r += [u @ e1 / s, u @ e2 / s]
            Ju = (np.eye(3) - np.outer(u, u)) / n
            J += [e1 @ Ju / s, e2 @ Ju / s]
        r, J = np.array(r), np.array(J)
        dp = -np.linalg.lstsq(J, r, rcond=None)[0]
        P = P + dp
        if np.linalg.norm(dp) < 1e-6:
            break
    cov = np.linalg.pinv(J.T @ J)
    res = [math.degrees(math.acos(np.clip((P - c) @ d / np.linalg.norm(P - c), -1, 1))) for c, d in zip(C, D)]
    return dict(point=P.tolist(), covariance=cov.tolist(), ecart_type=np.sqrt(np.diag(cov)).tolist(),
                residus_deg=res, n=len(C))


def trianguler_verticale(observations, poses=None, rayons=None):
    """Axe vertical (x, y) depuis des pixels pris sur l'axe d'un mât dans plusieurs photos calées.
    Chaque observation définit un plan vertical contenant la caméra et l'axe."""
    C, D, S = rayons if rayons is not None else _rayons(observations, poses)
    if len(C) < 2:
        return None
    N = np.cross(D, [0, 0, 1.0])[:, :2]
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    # pondération : σ angulaire × distance (inconnue au départ -> itération)
    w = np.ones(len(C))
    X = None
    for _ in range(4):
        A = N * w[:, None]
        b = np.sum(N * C[:, :2], axis=1) * w
        X = np.linalg.lstsq(A, b, rcond=None)[0]
        dist = np.maximum(np.hypot(*(X - C[:, :2]).T), 0.5)
        w = 1.0 / (S * dist)
    resid = np.sum(N * (X - C[:, :2]), axis=1)
    dist = np.maximum(np.hypot(*(X - C[:, :2]).T), 0.5)
    ang = np.degrees(np.arcsin(np.clip(resid / dist, -1, 1)))
    Aw = N * w[:, None]
    cov = np.linalg.pinv(Aw.T @ Aw)
    # angle d'intersection des droites de visée (deux visées opposées sont parallèles : 162° -> 18°)
    az = np.degrees(np.arctan2(X[0] - C[:, 0], X[1] - C[:, 1]))
    da = np.abs(((az[:, None] - az[None, :]) + 180) % 360 - 180)
    da = np.minimum(da, 180.0 - da)
    return dict(xy=X.tolist(), covariance=cov.tolist(), ecart_type=np.sqrt(np.diag(cov)).tolist(),
                residus_deg=ang.tolist(), n=len(C), angle_intersection_deg=float(da.max()),
                distances_m=dist.tolist())


# --------------------------------------------------------------------------- pose sans certains GCP
def pose_sans(rec, gcp_ids):
    """Réajuste la pose d'une photo (enregistrement par_photo) en retirant les observations des
    GCP donnés ; renvoie la pose (np.array 6) ou None si trop peu d'observations restent."""
    from poses import Ajustement
    ph = photo(rec["id8"])
    intr = {**intrinseques(ph), **{k: v for k, v in (rec.get("intrinseques") or {}).items() if k in ("f", "cx", "cy", "k1")}}
    cat = G.gcp_par_id()
    gidx, obs = {}, []
    for o in rec.get("observations", []):
        if not o.get("inlier") or o["gcp"] in gcp_ids:
            continue
        g = cat.get(o["gcp"])
        if g is None and "gcp_def" in o:
            g = {"id": o["gcp"], "famille": "sol", **o["gcp_def"]}
        if g is None:
            continue
        gidx[o["gcp"]] = g
        obs.append(o)
    if len(obs) < 5:
        return None
    pb = rec["pose_brute"]
    p_brut = np.array([pb["x"], pb["y"], pb["z"], pb["lacet"], pb["tangage"], pb["roulis"]])
    q = rec["pose"]
    p0 = np.array([q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]])
    aj = Ajustement(ph, intr, p_brut, rec["sigma_a_priori"], obs, gidx)
    return aj.lm(p0)[:6]


# --------------------------------------------------------------------------- vérification d'un mât
def decision(r):
    """Décision de placement pour la scène 2026 (utilisée par l'amorçage des GCP et en aval) :
    'garder' | 'affiner' | 'deplacer' | 'revue_requise' | 'non_conclu'."""
    if not r.get("fiable"):
        return "non_conclu"
    rv = (r.get("revue_visuelle") or {}).get("verdict")
    if rv == "correction_rejetee":
        return "garder"
    if r["ecart_m"] <= r["tolerance_m"]:
        return "garder"
    if r["ecart_m"] <= SEUIL_DEPLACEMENT_M:
        return "affiner" if rv != "incertain" else "non_conclu"
    if rv == "correction_confirmee":
        return "deplacer"
    return "revue_requise"


def planche_comparaison(oid, p, r, taille=260):
    """Deux planches superposées : axe à la position du paquet (haut) et à la position triangulée
    (bas), mêmes photos ; support de la revue visuelle."""
    from PIL import Image
    from planche import planche_preuve, PLANCHES
    h = min(float(p.get("hauteur_m") or 3.0), 6.0)
    P = [p["x_local"], p["y_local"], p["z_local"]]
    X = r["position_triangulee"]
    a, _ = planche_preuve(oid + " paquet", P, [P[0], P[1], P[2] + h], n=3, taille=taille,
                          chemin=PLANCHES / f"_tmp_{oid}_a.jpg")
    b, _ = planche_preuve(oid + " triangule", [X[0], X[1], P[2]], [X[0], X[1], P[2] + h], n=3,
                          taille=taille, chemin=PLANCHES / f"_tmp_{oid}_b.jpg")
    if a is None or b is None:
        return None
    A, B = Image.open(a), Image.open(b)
    out = Image.new("RGB", (max(A.size[0], B.size[0]), A.size[1] + B.size[1] + 6), (255, 255, 255))
    out.paste(A, (0, 0))
    out.paste(B, (0, A.size[1] + 6))
    chemin = PLANCHES / f"triangulation_{oid}.jpg"
    out.save(chemin, quality=88)
    a.unlink()
    b.unlink()
    from camera import RACINE
    return chemin.relative_to(RACINE).as_posix()


def _objets_mobilier():
    out = {}
    for f in lire_json(DONNEES / "objets/mobilier.geojson")["features"]:
        p = f["properties"]
        if p.get("x_local") is None:
            continue
        out[p["id"]] = p
    return out


def mat_depuis_mobilier(p):
    """GCP « mât » construit depuis un objet du mobilier (même pour les statuts à vérifier)."""
    t = p["type"]
    h = float(p.get("hauteur_m") or 2.0)
    ht = h - (0.8 if t == "panneau" else 0.4)
    st = str(p.get("statut_2026") or "")
    # objets posés ou déduits pour 2026 : seules des photos postérieures aux travaux peuvent les prouver
    de = G.FIN_TRAVAUX_2025 if (st.startswith("déduit 2026") or st.startswith("2026")) else G.DATE_MIN
    return dict(id="MAT-" + p["id"], famille="mat", type=t, objets=[p["id"]],
                pied=[p["x_local"], p["y_local"], p["z_local"]],
                sommet=[p["x_local"], p["y_local"], p["z_local"] + max(ht, 0.6)],
                hauteur_m=h, diametre_m=G.DIAMETRES.get(t, 0.12),
                sigma_m=G.SIGMA_POS.get(p.get("confiance"), 1.0), poids=1.0,
                valide_de=de, valide_a=G.DATE_MAX, source="mobilier.geojson", confiance=p.get("confiance"))


def verifier_mat(g, poses=None, laisser_de_cote=True, rayon_recherche_m=1.5, dmax=30.0, graine=0):
    """Pointe le mât g dans toutes les photos calées acceptées qui le voient (fenêtre couvrant
    ± rayon_recherche_m autour de sa position du paquet), puis triangule son axe par RANSAC.
    laisser_de_cote : poses réajustées sans ce mât (validation non circulaire)."""
    from poses import FORCE_MIN, COHERENCE_MIN, PAR_PHOTO
    poses = charger_poses() if poses is None else poses
    P0 = np.array(g["pied"], float)
    obs = []
    for pid, rec in sorted(poses.items()):
        if not rec.get("accepte"):
            continue
        ph = photo(pid)
        if not G.valide(g, ph.date):
            continue            # une photo antérieure à la pose de l'objet ne prouve rien sur lui
        cam, _ = camera_calee(pid, poses, accepte_seulement=True)
        d = float(np.hypot(*(P0[:2] - cam.C[:2])))
        if d > dmax or d < 2.0:
            continue
        if laisser_de_cote and any(o["gcp"] == g["id"] for o in rec.get("observations", []) if o.get("inlier")):
            rp = lire_json(PAR_PHOTO / f"{pid}.json")
            p2 = pose_sans(rp, {g["id"]})
            if p2 is None:
                continue
            intr = {**intrinseques(ph), **{k: v for k, v in rec["intrinseques"].items() if k in ("f", "cx", "cy", "k1")}}
            cam = camera(ph, p2, intr)
        uvm, ok, _ = cam.projeter(((P0 + np.array(g["sommet"])) / 2)[None])
        if not ok[0] or G.occulte_par_batiments(cam.C, P0[None] + [0, 0, 1.0])[0]:
            continue
        fen = max(1.0, math.degrees(math.atan2(rayon_recherche_m, d)))
        pics = G.detecter_mat(ph, cam, image_gris(pid), g, fen, n_pics=3)
        sig = math.radians(math.hypot(SIG_PIX_DEG, rec["qualite"]["residu_moy_deg"]))
        for rang, o in enumerate(pics or []):
            if o["force"] < FORCE_MIN or o["coherence"] < COHERENCE_MIN:
                continue
            dirs = cam.rayons(np.array(o["uv"]))
            obs.append(dict(photo=pid, date=ph.date, rang_pic=rang, uv=o["uv"], C=cam.C.tolist(),
                            d=dirs.mean(0).tolist(), sig=sig, force=o["force"], coherence=o["coherence"],
                            distance_m=d, ecart_prediction_deg=o["ecart_prediction_deg"]))
    res = dict(id=g["id"], objets=g["objets"], type=g["type"], position_paquet=[P0[0], P0[1]],
               n_photos_pointees=len({o["photo"] for o in obs}), observations=obs)
    if not obs:
        if not any(G.valide(g, r["date"]) for r in poses.values() if r.get("accepte")):
            res.update(conclusion=f"non vérifiable : aucune photo calée dans sa période de validité "
                                  f"({g['valide_de']} -> {g['valide_a']})")
        else:
            res.update(conclusion="non vu")
        return res
    C = np.array([o["C"] for o in obs])
    D = np.array([o["d"] for o in obs])
    S = np.array([o["sig"] for o in obs])
    ph_ids = np.array([o["photo"] for o in obs])
    if len(set(ph_ids)) < 2:
        res.update(n_photos_pointees=len(set(ph_ids)), conclusion="non retrouvé (moins de 2 photos)")
        return res
    N = np.cross(D, [0, 0, 1.0])[:, :2]
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    # RANSAC sur paires de candidats de photos différentes ; chaque photo compte au plus une fois
    # (son candidat le plus cohérent) ; score = photos inliers − pénalité d'éloignement au paquet
    rng = np.random.default_rng(graine)
    paires = [(i, j) for i in range(len(obs)) for j in range(i + 1, len(obs)) if ph_ids[i] != ph_ids[j]]
    if len(paires) > 200:
        paires = [paires[k] for k in rng.choice(len(paires), 200, replace=False)]
    best = None
    for i, j in paires:
        t = trianguler_verticale(None, rayons=(C[[i, j]], D[[i, j]], S[[i, j]]))
        if t is None or t["angle_intersection_deg"] < 8:
            continue
        X = np.array(t["xy"])
        dist = np.maximum(np.hypot(*(X - C[:, :2]).T), 0.5)
        ang = np.degrees(np.abs(np.arcsin(np.clip(np.sum(N * (X - C[:, :2]), 1) / dist, -1, 1))))
        ok = ang < np.maximum(0.4, 3 * np.degrees(S))
        inl = np.zeros(len(obs), bool)
        for pid in set(ph_ids[ok]):
            ks = np.nonzero(ok & (ph_ids == pid))[0]
            inl[ks[np.argmin(ang[ks])]] = True
        n_ph = int(inl.sum())
        eloign = float(np.hypot(*(X - P0[:2])))
        sc = n_ph - 0.5 * (eloign / max(rayon_recherche_m, 0.5)) ** 2
        cle = (sc, -float(ang[inl].sum()))
        if best is None or cle > best[0]:
            best = (cle, inl, n_ph)
    if best is None or best[2] < 2:
        res.update(n_photos_pointees=len(set(ph_ids)),
                   conclusion="géométrie insuffisante (angles d'intersection < 8°)")
        return res
    inl = best[1]
    t = trianguler_verticale(None, rayons=(C[inl], D[inl], S[inl]))
    X = np.array(t["xy"])
    # stabilité leave-one-out : la position ne doit pas dépendre d'une seule photo
    idx = np.nonzero(inl)[0]
    loo = 0.0
    if len(idx) >= 3:
        for k in idx:
            m = inl.copy()
            m[k] = False
            tk = trianguler_verticale(None, rayons=(C[m], D[m], S[m]))
            if tk is None or tk["angle_intersection_deg"] < 8:
                loo = 99.0
                break
            loo = max(loo, float(np.hypot(*(np.array(tk["xy"]) - X))))
    else:
        loo = 99.0
    dxy = X - P0[:2]
    et = float(np.hypot(*t["ecart_type"]))
    ecart = float(np.hypot(*dxy))
    sig_cat = float(g.get("sigma_m", 0.6))
    tol = max(TOLERANCE_PLACEMENT_M, 3.0 * et)
    fiable = (t["n"] >= 3 and t["angle_intersection_deg"] >= 20 and et <= 0.25
              and loo <= max(0.3, 3 * et))
    azd = math.degrees(math.atan2(dxy[0], dxy[1])) % 360
    if fiable:
        if ecart <= tol:
            concl = f"position confirmée (écart {ecart:.2f} m ≤ {tol:.2f} m)"
        elif ecart <= SEUIL_DEPLACEMENT_M:
            concl = f"affinage proposé : {ecart:.2f} m vers l'azimut {azd:.0f}° (même support, axe mieux centré)"
        else:
            concl = (f"déplacement proposé : {ecart:.2f} m vers l'azimut {azd:.0f}° "
                     f"(à confirmer par revue visuelle des planches)")
    else:
        concl = ("indicatif (moins de 3 photos, angle d'intersection < 20°, σ > 0,25 m ou position "
                 "instable quand on retire une photo)")
    for k, o in enumerate(obs):
        o["inlier"] = bool(inl[k])
        o.pop("C")
        o.pop("d")
    res.update(position_triangulee=X.tolist(), ecart_type_m=t["ecart_type"], ecart_m=ecart, fiable=fiable,
               tolerance_m=tol, sigma_paquet_m=sig_cat, stabilite_loo_m=loo,
               dans_incertitude_paquet=bool(ecart <= 2.5 * math.hypot(et, sig_cat)),
               decalage_m=dxy.tolist(), n_inliers=int(t["n"]), residus_deg=t["residus_deg"],
               angle_intersection_deg=t["angle_intersection_deg"], conclusion=concl)
    return arrondi(res, 3)


# --------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Triangulation et vérification de mâts")
    ap.add_argument("--valider", action="store_true", help="mâts levés (catalogue GCP) : erreur de triangulation")
    ap.add_argument("--verifier-tout", action="store_true", help="tous les mâts du mobilier")
    ap.add_argument("--n", type=int, default=0)
    a = ap.parse_args(argv)
    poses = charger_poses()
    out = lire_json(SORTIE / "triangulation.json") if (SORTIE / "triangulation.json").exists() else {}
    if a.valider:
        # mâts levés au LiDAR 2021 (confiance haute, existants) : position du PAQUET comme vérité
        mob = _objets_mobilier()
        mats = [mat_depuis_mobilier(p) for oid, p in sorted(mob.items())
                if p["type"] in G.DIAMETRES and p.get("confiance") == "haute"
                and str(p.get("statut_2026", "")).startswith("existant") and "LiDAR" in str(p.get("source"))]
        res = []
        for g in mats:
            r = verifier_mat(g, poses, laisser_de_cote=True, rayon_recherche_m=2.0)
            res.append(r)
            print(g["id"], r.get("n_photos_pointees"), r.get("n_inliers"), r.get("ecart_m"), r.get("conclusion"))
        res = [r for r in res if r.get("position_triangulee")]
        res.sort(key=lambda r: (-r["n_inliers"], r["id"]))
        if a.n:
            res = res[: a.n]
        out["validation_mats_leves"] = dict(
            methode="pose de chaque photo réajustée sans le mât testé ; pointage automatique de l'axe ; "
                    "triangulation de l'axe vertical (RANSAC sur paires, angle d'intersection ≥ 8°)",
            resultats=res)
    if a.verifier_tout:
        mob = _objets_mobilier()
        revues = lire_json(REVUES)["revues"] if REVUES.exists() else {}
        res = []
        for oid, p in sorted(mob.items()):
            if p["type"] not in G.DIAMETRES:
                continue
            g = mat_depuis_mobilier(p)          # toujours la position du paquet comme référence
            r = verifier_mat(g, poses, laisser_de_cote=True, rayon_recherche_m=2.0)
            r["statut_2026_paquet"] = p.get("statut_2026")
            r["confiance_paquet"] = p.get("confiance")
            if r.get("fiable") and r["ecart_m"] > TOLERANCE_PLACEMENT_M:
                r["planche_comparaison"] = planche_comparaison(oid, p, r)
            rv = revues.get(oid)
            if rv:
                r["revue_visuelle"] = rv
            r["decision"] = decision(r)
            res.append(r)
            print(oid, r.get("n_photos_pointees"), r.get("ecart_m"), r.get("conclusion"))
        out["verification_mobilier"] = dict(
            methode="pointage de l'axe dans une fenêtre de ±2 m autour de la position du paquet, sur les "
                    "photos calées dont la pose est réajustée sans ce mât ; triangulation RANSAC de l'axe "
                    "vertical ; fiable si ≥ 3 photos, angle d'intersection des visées ≥ 20°, σ ≤ 0,25 m et "
                    "position stable quand on retire une photo (≤ max(0,3 m ; 3 σ)) ; "
                    "position confirmée si écart ≤ max(0,35 m ; 3 σ), sinon à corriger",
            resultats=res)
    ecrire_json(SORTIE / "triangulation.json", arrondi(out, 3))


if __name__ == "__main__":
    main()
