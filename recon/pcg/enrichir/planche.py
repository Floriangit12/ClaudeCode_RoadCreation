"""Planches de contrôle visuel : calage d'une photo, et preuve photo d'une entité.

- planche_controle(rec) : vignettes de chaque GCP observé (projection à la pose calée en magenta,
  pixel pointé automatiquement en vert ; cadre vert = inlier, rouge = rejeté) + bandeau de la photo
  entière avec tous les GCP projetés. Sert à la validation visuelle des pointages.
- planche_preuve(entite, point) : pour une entité (id) et un point 3D local (ou un segment
  pied -> sommet), les meilleures photos calées qui le voient (score = résolution × qualité de pose
  × visibilité), chacune avec le point projeté et son incertitude. CLI :
    python planche.py --entite MAT-feu_NE_TPC --point 12.0 9.0 0.31 [--sommet 12.0 9.0 3.4] [--n 6]
    python planche.py --controle 119d9094
"""
import argparse
import math

import numpy as np
from PIL import Image, ImageDraw

from camera import SORTIE, camera_calee, charger_poses, image_rgb, photo, lire_json
import gcp as G
from projection import projeter

PLANCHES = SORTIE / "planches"


def _cadre(im, couleur, e=3):
    dr = ImageDraw.Draw(im)
    w, h = im.size
    for k in range(e):
        dr.rectangle([k, k, w - 1 - k, h - 1 - k], outline=couleur)
    return im


def _gcp_def(o, gidx):
    if o["gcp"] in gidx:
        return gidx[o["gcp"]]
    if "gcp_def" in o:
        return {"id": o["gcp"], "famille": "sol", **o["gcp_def"]}
    return None


def planche_controle(rec, taille=180, n_col=8, chemin=None):
    """Planche de validation du calage d'une photo (rec = enregistrement par_photo)."""
    ph = photo(rec["id8"])
    cam, _ = camera_calee(ph.id8, poses={ph.id8: {**rec, "accepte": True}})
    gidx = G.gcp_par_id()
    obs = sorted(rec.get("observations", []), key=lambda o: (not o["inlier"], o["gcp"]))
    vign = []
    for o in obs:
        g = _gcp_def(o, gidx)
        if g is None:
            continue
        coul = (0, 255, 0) if o["inlier"] else (255, 0, 0)
        titre = f"{o['gcp'][:22]} {o['residu_deg']:.2f}°"
        if g.get("famille") in ("mat", "tronc"):
            A, B = np.array(g["pied"]), np.array(g["sommet"])
            M = (A + B) / 2
            im = G.vignette(ph, cam, M, taille, fov=None if False else _fov_mat(cam, g), segment=(A, B),
                            obs_uv=o["uv"], titre=titre)
        else:
            P = np.array(g["point"])
            seg = (np.array(g["pied"]), np.array(g["sommet"])) if o["type"] == "ligne" else None
            ouv = o["uv"] if o["type"] == "ligne" else [o["uv"]]
            im = G.vignette(ph, cam, P, taille, fov=6.0 if ph.is360 else 4.0, segment=seg, obs_uv=ouv,
                            titre=titre)
        vign.append(_cadre(im, coul))
    # bandeau photo entière
    big = Image.fromarray(image_rgb(ph.id8))
    W = n_col * taille
    s = W / big.size[0]
    ban = big.resize((W, int(big.size[1] * s)))
    dr = ImageDraw.Draw(ban)
    for o in obs:
        g = _gcp_def(o, gidx)
        if g is None:
            continue
        coul = (255, 0, 255) if o["inlier"] else (255, 0, 0)
        if g.get("famille") in ("mat", "tronc"):
            uv, ok, _ = cam.projeter(np.array([g["pied"], g["sommet"]]))
            if ok.all() and abs(uv[0, 0] - uv[1, 0]) < cam.W / 4:
                dr.line([tuple(uv[0] * s), tuple(uv[1] * s)], fill=coul, width=2)
        elif "point" in g:
            uv, ok, _ = cam.projeter(np.array([g["point"]]))
            if ok[0]:
                u, v = uv[0] * s
                dr.ellipse([u - 3, v - 3, u + 3, v + 3], outline=coul)
    q = rec.get("qualite", {})
    txt = (f"{ph.id8} {ph.date} {rec.get('modele')}  accepte={rec.get('accepte')} ({rec.get('raison')})  "
           f"n_gcp={q.get('n_gcp')} moy={q.get('residu_moy_deg')}° max={q.get('residu_max_deg')}° "
           f"moy_px={q.get('residu_moy_px')} gps={q.get('decalage_gps_m')} m dlacet={q.get('correction_lacet_deg')}°")
    dr.rectangle([0, 0, W, 14], fill=(0, 0, 0))
    dr.text((4, 1), txt, fill=(255, 255, 255))
    n_l = max(1, math.ceil(len(vign) / n_col))
    out = Image.new("RGB", (W, ban.size[1] + n_l * taille), (30, 30, 30))
    out.paste(ban, (0, 0))
    for k, v in enumerate(vign):
        out.paste(v, ((k % n_col) * taille, ban.size[1] + (k // n_col) * taille))
    PLANCHES.mkdir(parents=True, exist_ok=True)
    chemin = chemin or PLANCHES / f"controle_{ph.id8}.jpg"
    out.save(chemin, quality=88)
    return chemin


def _fov_mat(cam, g):
    A, B = np.array(g["pied"]), np.array(g["sommet"])
    d = max(float(np.hypot(*(A[:2] - cam.C[:2]))), 0.5)
    h = float(B[2] - A[2])
    return float(np.clip(math.degrees(2 * math.atan(0.7 * h / d)), 6.0, 60.0))


# --------------------------------------------------------------------------- preuve d'entité
def meilleures_photos(P, n=6, sommet=None, dmax=40.0, date_min=None, date_max=None, poses=None):
    """Photos calées acceptées qui voient P, triées par score décroissant :
    score = (px/m à la distance) × (1 / (1 + résidu moyen en px)) ; une seule par photo."""
    poses = charger_poses() if poses is None else poses
    out = []
    for pid, rec in poses.items():
        if not rec.get("accepte"):
            continue
        if date_min and rec["date"] < date_min or date_max and rec["date"] > date_max:
            continue
        cam, _ = camera_calee(pid, poses)
        pts = np.atleast_2d(P) if sommet is None else np.array([P, sommet])
        r = projeter(pts, pid, cam=cam, dmax=dmax)
        if not r["visible"].all():
            continue
        if ph_lat_basse(pid, cam, pts):
            continue
        d = float(r["distance"].min())
        res_px = rec["qualite"]["residu_moy_px"]
        sc = cam.px_par_rad / d / (1 + res_px / 4)
        out.append((sc, pid, d, cam))
    out.sort(key=lambda t: (-t[0], t[1]))
    return out[:n]


def ph_lat_basse(pid, cam, pts):
    ph = photo(pid)
    c = cam.monde_vers_cam(pts)
    lat = np.degrees(np.arctan2(c[:, 2], np.hypot(c[:, 0], c[:, 1])))
    return bool(np.any(lat < G.lat_min_cam(ph) + 1.0))


def planche_preuve(entite, point, sommet=None, n=6, taille=320, chemin=None, **kw):
    """Planche des meilleures photos calées montrant `point` (et le segment jusqu'à `sommet`)."""
    P = np.asarray(point, dtype=np.float64)
    S = None if sommet is None else np.asarray(sommet, dtype=np.float64)
    sel = meilleures_photos(P, n=n, sommet=S, **kw)
    if not sel:
        return None, []
    vign = []
    for sc, pid, d, cam in sel:
        ph = photo(pid)
        if S is None:
            fov = float(np.clip(math.degrees(2 * math.atan(3.0 / d)), 8.0, 60.0))
            im = G.vignette(ph, cam, P, taille, fov=fov, titre=f"{pid} {ph.date} d={d:.1f} m")
        else:
            M = (P + S) / 2
            g = {"pied": P, "sommet": S}
            im = G.vignette(ph, cam, M, taille, fov=_fov_mat(cam, g) * 1.3, segment=(P, S),
                            titre=f"{pid} {ph.date} d={d:.1f} m")
        vign.append(im)
    W = taille * min(len(vign), 3)
    nl = math.ceil(len(vign) / 3)
    out = Image.new("RGB", (W, nl * taille + 16), (20, 20, 20))
    dr = ImageDraw.Draw(out)
    dr.text((4, 2), f"{entite}  P=({P[0]:.2f}, {P[1]:.2f}, {P[2]:.2f}) local", fill=(255, 255, 255))
    for k, v in enumerate(vign):
        out.paste(v, ((k % 3) * taille, 16 + (k // 3) * taille))
    PLANCHES.mkdir(parents=True, exist_ok=True)
    chemin = chemin or PLANCHES / f"preuve_{_nom(entite)}.jpg"
    out.save(chemin, quality=88)
    return chemin, [(pid, round(d, 2), round(sc, 1)) for sc, pid, d, _ in sel]


def _nom(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))[:80]


def planche_projection(photo_ids, points, chemin=None, taille=220, poses=None):
    """Validation visuelle : les mêmes points levés (liste de dict(id, P[, sommet])) projetés dans
    plusieurs photos calées. Une ligne par photo : une vignette par point (croix magenta = projection,
    segment pour un mât), « hors champ » si non visible. Renvoie (chemin, tableau des pixels)."""
    poses = charger_poses() if poses is None else poses
    lignes, tableau = [], []
    for pid in photo_ids:
        ph = photo(pid)
        cam, statut = camera_calee(pid, poses)
        rec = poses.get(ph.id8, {})
        utilises = set(rec.get("gcp_utilises", []))
        ligne = []
        for pt in points:
            P = np.asarray(pt["P"], float)
            S = np.asarray(pt["sommet"], float) if pt.get("sommet") is not None else None
            r = projeter(np.array([P]), pid, cam=cam, dmax=45.0)
            vis = bool(r["visible"][0]) and not ph_lat_basse(pid, cam, P[None])
            tableau.append(dict(photo=ph.id8, point=pt["id"], visible=vis, uv=r["uv"][0].tolist(),
                                distance_m=float(r["distance"][0]), gcp_de_calage=pt["id"] in utilises))
            if not vis:
                im = Image.new("RGB", (taille, taille), (40, 40, 40))
                ImageDraw.Draw(im).text((6, taille // 2), f"{pt['id'][:24]}\nhors champ / occulté", fill=(200, 200, 200))
            else:
                d = float(r["distance"][0])
                if S is None:
                    fov = float(np.clip(math.degrees(2 * math.atan(1.5 / d)), 4.0, 30.0))
                    im = G.vignette(ph, cam, P, taille, fov=fov, titre=f"{pt['id'][:22]} {d:.0f}m")
                else:
                    g = {"pied": P, "sommet": S}
                    im = G.vignette(ph, cam, (P + S) / 2, taille, fov=_fov_mat(cam, g), segment=(P, S),
                                    titre=f"{pt['id'][:22]} {d:.0f}m")
                if pt["id"] in utilises:
                    _cadre(im, (255, 200, 0), 2)          # jaune : point utilisé pour caler la photo
            ligne.append(im)
        lignes.append((f"{ph.id8} {ph.date} ({statut})", ligne))
    W = taille * len(points)
    out = Image.new("RGB", (W, len(lignes) * (taille + 14)), (20, 20, 20))
    dr = ImageDraw.Draw(out)
    for k, (titre, ligne) in enumerate(lignes):
        y = k * (taille + 14)
        dr.text((4, y + 1), titre + "   (cadre jaune = point utilisé pour le calage de cette photo)", fill=(255, 255, 255))
        for j, im in enumerate(ligne):
            out.paste(im, (j * taille, y + 14))
    PLANCHES.mkdir(parents=True, exist_ok=True)
    chemin = chemin or PLANCHES / "validation_projection.jpg"
    out.save(chemin, quality=88)
    return chemin, tableau


def points_leves_communs(photo_ids, n=10, poses=None):
    """Points LEVÉS (positions du paquet, pas les positions triangulées) visibles dans le plus de
    photos possible : coins de zébras GAM et pieds/axes de mâts LiDAR ; diversifiés (≥ 2 m d'écart)."""
    import os
    os.environ["PJ_SANS_TRIANGULATION"] = "1"
    G.catalogue_gcp.cache_clear()
    poses = charger_poses() if poses is None else poses
    cams = [camera_calee(pid, poses)[0] for pid in photo_ids]
    dates = [photo(pid).date for pid in photo_ids]
    cand = []
    for g in G.catalogue_gcp():
        if not all(G.valide(g, d) for d in dates):
            continue
        if g["famille"] == "mat" and g.get("confiance") == "haute":
            P, S = np.array(g["pied"]), np.array(g["sommet"])
        elif g["type"] == "coin_zebra" and "GAM" in g["source"]:
            P, S = np.array(g["point"]), None
        else:
            continue
        nvis = 0
        for pid, cam in zip(photo_ids, cams):
            r = projeter(P[None], pid, cam=cam, dmax=25.0)
            if r["visible"][0] and not ph_lat_basse(pid, cam, P[None]):
                nvis += 1
        if nvis >= 3:
            cand.append((nvis, g["famille"] == "mat", g["id"], P, S))
    cand.sort(key=lambda c: (-c[0], -c[1], c[2]))
    out = []
    for nv, est_mat, gid, P, S in cand:
        if all(np.hypot(*(P[:2] - q["P"][:2])) >= 2.0 for q in out):
            out.append(dict(id=gid, P=P, sommet=S, n_photos=nv))
        if len(out) >= n:
            break
    del os.environ["PJ_SANS_TRIANGULATION"]
    G.catalogue_gcp.cache_clear()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Planches de contrôle et de preuve (photos calées)")
    ap.add_argument("--entite")
    ap.add_argument("--point", nargs=3, type=float)
    ap.add_argument("--sommet", nargs=3, type=float)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--controle", nargs="*")
    ap.add_argument("--validation-projection", nargs="*", help="id8 des photos : 10 points levés projetés")
    a = ap.parse_args(argv)
    if a.validation_projection:
        pts = points_leves_communs(a.validation_projection)
        c, tab = planche_projection(a.validation_projection, pts)
        from camera import ecrire_json, arrondi
        ecrire_json(PLANCHES / "validation_projection.json",
                    arrondi(dict(photos=a.validation_projection,
                                 points=[dict(id=p["id"], P=p["P"].tolist(), n_photos=p["n_photos"]) for p in pts],
                                 projections=tab), 3))
        print(c, [p["id"] for p in pts])
    if a.controle:
        from poses import PAR_PHOTO
        for pid in a.controle:
            rec = lire_json(PAR_PHOTO / f"{photo(pid).id8}.json")
            print(planche_controle(rec))
    if a.entite and a.point:
        c, sel = planche_preuve(a.entite, a.point, a.sommet, n=a.n)
        print(c, sel)


if __name__ == "__main__":
    main()
