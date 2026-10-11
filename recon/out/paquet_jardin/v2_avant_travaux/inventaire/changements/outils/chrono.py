"""Chronologie photo d'un point du site : vues perspectives de toutes les prises (Panoramax et Mapillary)
qui le voient, une ou deux par séance, rangées par date. Sortie : photos_non_versionnees/ (jamais versionné).

python chrono.py <nom> <x_local> <y_local> [--h 0.5] [--taille 12] [--dmax 35] [--par-seance 1]
                  [--de 2020-01-01] [--a 2026-12-31] [--lacet-fixe AZ]

Poses : Panoramax calée (poses.json, acceptée) sinon brute (GNSS ± 4 m, azimut ± 8°) ; Mapillary
poses_mapillary.json (calée ou a priori SfM) sinon a priori SfM (mapillary.pose_mly). Le point visé est
marqué d'un cercle magenta ; il peut être décalé de quelques mètres pour une pose a priori.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from commun_chg import PHOTOS_NV, RACINE, ecrire_json, police, rel  # noqa: E402

sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
import camera as C  # noqa: E402
import mapillary as M  # noqa: E402
from projection import camera_virtuelle, reechantillonner  # noqa: E402

POSES_MLY = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/poses/poses_mapillary.json"


@functools.lru_cache(maxsize=1)
def candidats():
    out = []
    for id8, ph in C.catalogue().items():
        cam, statut = C.camera_calee(id8)
        out.append(dict(src="panoramax", id=ph.id, cle=id8, date=ph.date, dt=ph.datetime, cam=cam, statut=statut,
                        is360=ph.is360, auteur=ph.meta.get("producer"),
                        lien=f"https://panoramax.openstreetmap.fr/#focus=pic&pic={ph.id}"))
    poses = {}
    if POSES_MLY.exists():
        for im in json.loads(POSES_MLY.read_text(encoding="utf-8"))["images"]:
            if im.get("pose"):
                q = im["pose"]
                poses[str(im["id"])] = ([q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]], im.get("statut"))
    ids = {p.stem for p in M.IMG.glob("*.jpg")}
    par_id = M.images_par_id()
    for iid in sorted(ids):
        im = par_id.get(iid)
        if im is None:
            continue
        ph = M.PhotoMly({**im, "date": M._date(im) if hasattr(M, "_date") else im.get("date")})
        try:
            if iid in poses:
                pose, statut = poses[iid]
            else:
                pose, statut = list(M.pose_mly(ph)["pose"]), "a_priori_sfm"
            cam = M.camera_mly(ph, pose)
        except Exception as e:  # noqa: BLE001
            print("mapillary", iid, "ignorée :", e)
            continue
        out.append(dict(src="mapillary", id=iid, cle="m" + iid, date=ph.date, dt=ph.datetime, cam=cam, statut=statut,
                        is360=ph.is360, auteur=ph.auteur, lien=f"https://www.mapillary.com/app/?pKey={iid}"))
    return out


def image_de(c):
    if c["src"] == "panoramax":
        return C.image_rgb(c["cle"])
    return M.image_rgb_mly(c["id"])


def vue(c, P, taille_m=12.0, wh=(420, 300), lacet_fixe=None):
    cam = c["cam"]
    d = P - cam.C
    hz = math.hypot(d[0], d[1])
    lac = math.degrees(math.atan2(d[0], d[1])) % 360 if lacet_fixe is None else lacet_fixe
    tan = math.degrees(math.atan2(d[2], hz))
    fov = float(np.clip(2 * math.degrees(math.atan2(taille_m / 2, max(hz, 1.0))), 30.0, 100.0))
    cv = camera_virtuelle(cam, lac, tan, fov, wh)
    img = reechantillonner(cam, image_de(c).astype(np.float32), cv)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    uv, ok, dist = cv.projeter(P[None])
    dr = ImageDraw.Draw(im)
    if ok[0]:
        u, v = uv[0]
        dr.ellipse([u - 9, v - 9, u + 9, v + 9], outline=(255, 0, 255), width=2)
    return im, dict(lacet=round(lac, 1), tangage=round(tan, 1), fov=round(fov, 1), distance_m=round(float(dist[0]), 1))


def chrono(nom, x, y, h=0.5, taille_m=12.0, dmax=35.0, dmin=3.0, par_seance=1, de="2000-01-01", a="2100-01-01",
           lacet_fixe=None, ncol=4, dossier=None):
    z = C.z_sol(x, y) + h
    P = np.array([x, y, z])
    retenus = {}
    for c in candidats():
        if not (de <= c["date"] <= a):
            continue
        cam = c["cam"]
        uv, ok, dist = cam.projeter(P[None])
        dz = math.hypot(*(P[:2] - cam.C[:2]))
        if not ok[0] or not (dmin <= dz <= dmax):
            continue
        if not c["is360"]:
            u, v = uv[0]
            m = 0.08
            if not (m * cam.W < u < (1 - m) * cam.W and m * cam.H < v < (1 - m) * cam.H):
                continue
        score = dz + (0 if c["statut"] in ("calee", "calee_gcp", "calee_panoramax", "calee_bordures") else 4.0)
        cle_s = (c["date"], c["src"], c["auteur"])
        retenus.setdefault(cle_s, []).append((score, c))
    choix = []
    for k in sorted(retenus):
        for s, c in sorted(retenus[k], key=lambda t: t[0])[:par_seance]:
            choix.append(c)
    # une même séance publiée sur les deux plateformes : garder Panoramax (poses calées) si même date et auteur proche
    vignettes, meta = [], []
    for c in choix:
        try:
            im, info = vue(c, P, taille_m, lacet_fixe=lacet_fixe)
        except Exception as e:  # noqa: BLE001
            print("vue impossible", c["cle"], e)
            continue
        cad = Image.new("RGB", (im.width, im.height + 34), (20, 20, 20))
        cad.paste(im, (0, 34))
        dr = ImageDraw.Draw(cad)
        dr.text((3, 1), f"{c['dt'][:16].replace('T', ' ')}  {c['src']} {c['id'][:12]}", fill=(255, 255, 255), font=police(13))
        dr.text((3, 17), f"{c['statut']}  d={info['distance_m']} m  az={info['lacet']}  fov={info['fov']}", fill=(200, 200, 200), font=police(12))
        vignettes.append(cad)
        meta.append(dict(src=c["src"], id=c["id"], date=c["dt"], statut_pose=c["statut"], auteur=c["auteur"], lien=c["lien"], **info))
    if not vignettes:
        print(nom, ": aucune prise ne voit le point")
        return None
    w, hh = vignettes[0].size
    nl = math.ceil(len(vignettes) / ncol)
    planche = Image.new("RGB", (ncol * w + (ncol - 1) * 4, nl * hh + (nl - 1) * 4 + 22), (60, 60, 60))
    for k, v in enumerate(vignettes):
        planche.paste(v, ((k % ncol) * (w + 4), 22 + (k // ncol) * (hh + 4)))
    ImageDraw.Draw(planche).text((4, 3), f"{nom} : point local ({x:+.1f} ; {y:+.1f}), h={h} m — photos CC-BY-SA (Panoramax / Mapillary), non versionnées",
                                 fill=(255, 255, 255), font=police(14))
    out = Path(dossier or PHOTOS_NV / "chrono")
    out.mkdir(parents=True, exist_ok=True)
    s = out / f"chrono_{nom}.jpg"
    planche.save(s, quality=88)
    ecrire_json(out / f"chrono_{nom}.json", {"point_local": [x, y, round(float(z), 2)], "vues": meta})
    print(rel(s), len(vignettes), "vues :", ", ".join(m_["date"][:10] for m_ in meta))
    return s, meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("nom")
    ap.add_argument("x", type=float)
    ap.add_argument("y", type=float)
    ap.add_argument("--h", type=float, default=0.5)
    ap.add_argument("--taille", type=float, default=12.0)
    ap.add_argument("--dmax", type=float, default=35.0)
    ap.add_argument("--dmin", type=float, default=3.0)
    ap.add_argument("--par-seance", type=int, default=1)
    ap.add_argument("--de", default="2000-01-01")
    ap.add_argument("--a", default="2100-01-01")
    ap.add_argument("--lacet-fixe", type=float, default=None)
    ap.add_argument("--ncol", type=int, default=4)
    g = ap.parse_args()
    chrono(g.nom, g.x, g.y, g.h, g.taille, g.dmax, g.dmin, g.par_seance, g.de, g.a, g.lacet_fixe, g.ncol)
