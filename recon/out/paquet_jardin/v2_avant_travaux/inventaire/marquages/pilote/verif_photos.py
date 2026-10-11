"""Vérification des repeintes 2022 -> 2024-2025 : projection des vecteurs du pilote (ajustés sur l'ortho 2022) dans
des photos 360° Panoramax datées d'avant les travaux (2024-08-24, 2025-05-18), aux poses calées de
recon/out/paquet_jardin/v2/enrichi/poses/poses.json (lecture seule).

Modèle (repris de recon/pcg/enrichir/camera.py, réécrit ici pour ne pas dépendre de modules en cours de
modification) : c = R (P - C) en (droite, avant, haut) ; équirectangulaire u = W (0,5 + lon / 2 pi),
v = H (0,5 - lat / pi). Z du sol : heightmap 10 cm du paquet (recon/out/paquet_jardin/package/donnees/relief).
Sortie : vignettes perspective (FOV 75°) avec contours projetés, dans photos_non_versionnees/ (photos de tiers,
CC-BY-SA, jamais versionnées) + verif_photos.json (identifiants, dates, cibles ; aucune image).
Usage : python -I verif_photos.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun_pilote as C  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
POSES = C.RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json"
PANO = C.RACINE / "data/raw/panoramax/paquet_jardin"
SORTIE_PH = C.SORTIE / "photos_non_versionnees"


def matrice_rotation(lacet, tangage=0.0, roulis=0.0):
    ps, th, ph = (math.radians(a) for a in (lacet, tangage, roulis))
    a0 = np.array([math.sin(ps), math.cos(ps), 0.0])
    d0 = np.array([math.cos(ps), -math.sin(ps), 0.0])
    h0 = np.array([0.0, 0.0, 1.0])
    a1 = a0 * math.cos(th) + h0 * math.sin(th)
    h1 = -a0 * math.sin(th) + h0 * math.cos(th)
    d2 = d0 * math.cos(ph) + h1 * math.sin(ph)
    h2 = -d0 * math.sin(ph) + h1 * math.cos(ph)
    return np.vstack([d2, a1, h2])


_mnt = None
HEIGHTMAP = C.RACINE / "recon/out/paquet_jardin/package/donnees/relief/heightmap_3025_10cm.json"


def z_sol(x, y):
    """z local (NGF - 216,30) du sol nu du paquet (heightmap 16 bits, pas 10 cm), bilinéaire aux points L93."""
    global _mnt
    if _mnt is None:
        meta = json.loads(HEIGHTMAP.read_text(encoding="utf-8"))
        a = np.asarray(Image.open(HEIGHTMAP.with_name(meta["fichier"])), np.float64)
        z = meta["z_min_m_NGF"] + a / 65535.0 * (meta["z_max_m_NGF"] - meta["z_min_m_NGF"])
        e = meta["emprise_noeuds_L93"]
        _mnt = (z, e["x_min"], e["y_max"], meta["taille_pixel_m"])
    z, x0, y1, pas = _mnt
    n = z.shape[0]
    fc = np.clip((np.asarray(x, float) - x0) / pas, 0, n - 1.000001)
    fr = np.clip((y1 - np.asarray(y, float)) / pas, 0, n - 1.000001)
    c, r = np.floor(fc).astype(int), np.floor(fr).astype(int)
    tc, tr = fc - c, fr - r
    v = (z[r, c] * (1 - tc) + z[r, c + 1] * tc) * (1 - tr) + (z[r + 1, c] * (1 - tc) + z[r + 1, c + 1] * tc) * tr
    return v - 216.30


def vignette(pid, cible_l93, polys, titre, fov=40.0, W=1000, H=560):
    poses = {p["id8"]: p for p in json.loads(POSES.read_text(encoding="utf-8"))["photos"]}
    p = poses[pid]
    q = p["pose"]
    Cc = np.array([q["x"], q["y"], q["z"]])
    R = matrice_rotation(q["lacet"], q["tangage"], q["roulis"])
    img = np.asarray(Image.open(PANO / p["fichier"]).convert("RGB"))
    Hi, Wi = img.shape[:2]
    tx, ty = cible_l93[0] - C.O[0], cible_l93[1] - C.O[1]
    tz = float(z_sol(np.array([cible_l93[0]]), np.array([cible_l93[1]]))[0])
    dc = R @ (np.array([tx, ty, tz]) - Cc)
    psi = math.atan2(dc[0], dc[1])
    th = math.atan2(dc[2], math.hypot(dc[0], dc[1]))
    f = np.array([math.sin(psi) * math.cos(th), math.cos(psi) * math.cos(th), math.sin(th)])
    r = np.array([math.cos(psi), -math.sin(psi), 0.0])
    u = np.cross(r, f)
    fpx = (W / 2) / math.tan(math.radians(fov / 2))
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    ray = f[None, None] + ((jj - W / 2) / fpx)[..., None] * r + (-(ii - H / 2) / fpx)[..., None] * u
    lon = np.arctan2(ray[..., 0], ray[..., 1])
    lat = np.arctan2(ray[..., 2], np.hypot(ray[..., 0], ray[..., 1]))
    U = (Wi * (0.5 + lon / (2 * math.pi))) % Wi
    V = np.clip(Hi * (0.5 - lat / math.pi), 0, Hi - 1)
    out = np.zeros((H, W, 3), np.float32)
    x0 = np.floor(U).astype(int)
    y0 = np.floor(V).astype(int)
    ax, ay = (U - x0)[..., None], (V - y0)[..., None]
    x1 = (x0 + 1) % Wi
    y1 = np.minimum(y0 + 1, Hi - 1)
    out = (img[y0, x0] * (1 - ax) + img[y0, x1] * ax) * (1 - ay) + (img[y1, x0] * (1 - ax) + img[y1, x1] * ax) * ay
    im = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    brut = im.copy()
    d = ImageDraw.Draw(im)
    for col, poly in polys:
        P = np.asarray(poly, float)
        P = np.vstack([P, P[:1]])
        seg = []
        for a, b in zip(P[:-1], P[1:]):
            n = max(2, int(np.linalg.norm(b - a) / 0.03))
            t = np.linspace(0, 1, n)[:, None]
            seg.append(a + t * (b - a))
        S = np.vstack(seg)
        z = z_sol(S[:, 0], S[:, 1]) + 0.005
        Pl = np.c_[S[:, 0] - C.O[0], S[:, 1] - C.O[1], z]
        cam = (R @ (Pl - Cc).T).T
        vf = cam @ f
        ok = vf > 0.3
        px = W / 2 + fpx * (cam @ r) / np.maximum(vf, 1e-6)
        py = H / 2 - fpx * (cam @ u) / np.maximum(vf, 1e-6)
        pts = [(a_, b_) for a_, b_, o in zip(px, py, ok) if o]
        if len(pts) > 1:
            d.line(pts, fill=col, width=2)
    d.rectangle([0, 0, W, 18], fill=(0, 0, 0))
    d.text((4, 3), f"{titre} - Panoramax {pid} {p['date']} (CC-BY-SA, {json.loads((PANO / p['fichier'].replace('.jpg', '.json')).read_text(encoding='utf-8')).get('producer', '?')}) - contours 2022 projetes", fill=(255, 255, 255))
    SORTIE_PH.mkdir(parents=True, exist_ok=True)
    nom = f"verif_{pid}_{titre.replace(' ', '_')}.jpg"
    duo = Image.new("RGB", (W, 2 * H))
    duo.paste(brut, (0, 0))
    duo.paste(im, (0, H))
    duo.save(SORTIE_PH / nom, quality=90)
    dist = float(np.linalg.norm(np.array([tx, ty]) - Cc[:2]))
    return {"photo": pid, "date": p["date"], "fichier_local": f"photos_non_versionnees/{nom}", "cible_l93": list(cible_l93), "distance_m": round(dist, 1)}


def main():
    gj = json.loads((C.SORTIE / "marquages_pilote_2022.geojson").read_text(encoding="utf-8"))
    polys = []
    for f in gj["features"]:
        if f["geometry"]["type"] != "Polygon":
            continue
        fam = f["properties"]["famille"]
        col = {"passage_pieton": (0, 255, 255), "fleche": (255, 0, 255), "damier": (255, 140, 0)}.get(fam, (255, 255, 0))
        polys.append((col, np.asarray(f["geometry"]["coordinates"][0][:-1])))
    cibles = [
        ("5c0d1d39", (917270.5, 6460278.0), "paves_jaunes_SO"),
        ("119d9094", (917270.5, 6460278.0), "paves_jaunes_SO"),
        ("2ab4efbc", (917272.0, 6460273.0), "zebras_SO"),
        ("31d16b8e", (917266.0, 6460278.0), "zebras_SO"),
        ("119d9094", (917293.5, 6460308.0), "fleches_NE"),
        ("5c0d1d39", (917290.0, 6460300.0), "zebras_NE"),
        ("119d9094", (917278.0, 6460264.0), "paves_jaunes_S"),
        ("2ab4efbc", (917262.5, 6460277.5), "fleche_TAD_SO"),
        ("31d16b8e", (917262.5, 6460277.5), "fleche_TAD_SO"),
    ]
    res = []
    for pid, c, t in cibles:
        try:
            res.append(vignette(pid, c, polys, t) | {"cible": t})
        except Exception as e:  # pragma: no cover
            res.append({"photo": pid, "cible": t, "erreur": str(e)})
    C.ecrire_json(C.SORTIE / "verif_photos.json", {"methode": __doc__.strip(), "vignettes": res})
    return res


if __name__ == "__main__":
    for r in main():
        print(r)
