"""Contrôle visuel « photo réelle vs maquette » : rend la maquette 3D depuis la position et le cap
de photos Panoramax 360° (équirectangulaires), puis découpe le rendu en tuiles 1000x1000 aux
MÊMES origines que les tuiles de la photo : chaque paire (photo, rendu) se compare pixel pour pixel
(même direction de visée, même champ), sans aucun redimensionnement.

Usage :
  python3 recon/qa_panoramax.py --glb recon/out/paquet_jardin/package/preview/paquet_jardin_2026.glb \
      --mois 2026-07 --out recon/out/paquet_jardin/qa_panoramax
Options : --ids <id1,id2> ; --hauteur 2.0 (hauteur de la caméra au-dessus du sol, m) ;
          --dcap 0 (correction de cap, degrés) ; --dxy 0,0 (correction de position, m) ;
          --caler : recalage automatique position (±4 m) + cap (±45°) de chaque photo par
          corrélation des gradients (bande sol, latitudes -5° à -45°) entre la photo et des
          rendus basse résolution (calcul numérique uniquement ; l'analyse visuelle se fait
          ensuite sur les tuiles 1000x1000 natives).
Sortie : <out>/<id>/rendu_rXX_cYY.jpg + paires.json (photo_tuile, rendu_tuile, direction).
Limites : position GPS à quelques mètres près (horizontal_accuracy_m) et cap issu du GPS :
les décalages résiduels se lisent sur les paires et se corrigent avec --dcap / --dxy.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_recon import DTM15, O, OUT, REPO, sample_raster  # noqa: E402
from pyproj import Transformer  # noqa: E402

PANO = REPO / "data" / "raw" / "panoramax" / "paquet_jardin"
RENDER = Path(__file__).resolve().parent / "tools" / "render3d" / "render.mjs"
TILE = 1000
_t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)


def origins(n, t=TILE):
    if n <= t:
        return [0]
    o = list(range(0, n - t + 1, t))
    if o[-1] + t < n:
        o.append(n - t)
    return o


def _grad(gray):
    import cv2
    g = np.asarray(gray, np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return np.hypot(gx, gy)


def _ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def calibrer(m, eye, cap0, glb, tmp, dtm, h, W=1440, H=720, rayon=4.0, pas=1.0):
    """Renvoie (dx, dy, dcap, score, score_initial) maximisant la corrélation photo/rendu."""
    ph = Image.open(PANO / f"{m['_stem']}.jpg").convert("L").resize((W, H), Image.BILINEAR)
    r0, r1 = int((0.5 + 5 / 180) * H), int((0.5 + 45 / 180) * H)
    P = _grad(ph)[r0:r1]
    kmax = int(45 / 360 * W)

    def essai(cands):
        views = []
        for i, (dx, dy) in enumerate(cands):
            x, y = eye[0] + O[0] + dx, eye[1] + O[1] + dy
            z = float(sample_raster(dtm, [x], [y])[0]) + h - O[2]
            views.append({"nom": f"c{i:03d}", "oeil": [eye[0] + dx, eye[1] + dy, z], "cap": cap0,
                          "largeur": W, "hauteur": H, "cube": 512})
        vf = tmp / "vues_calage.json"
        vf.write_text(json.dumps(views))
        subprocess.run(["node", str(RENDER), str(glb), str(vf), str(tmp)], check=True, capture_output=True)
        res = []
        for i, (dx, dy) in enumerate(cands):
            G = _grad(Image.open(tmp / f"c{i:03d}.png").convert("L"))[r0:r1]
            best = max(((_ncc(P, np.roll(G, -k, axis=1)), k) for k in range(-kmax, kmax + 1)))
            res.append((best[0], dx, dy, best[1] * 360 / W))
            (tmp / f"c{i:03d}.png").unlink()
        return res

    n = int(round(rayon / pas))
    grille = [(i * pas, j * pas) for i in range(-n, n + 1) for j in range(-n, n + 1)]
    res = essai(grille)
    s0 = next(r for r in res if r[1] == 0 and r[2] == 0)
    best = max(res)
    fin = [(best[1] + i * 0.5, best[2] + j * 0.5) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0)]
    best = max([best] + essai(fin))
    return best[1], best[2], best[3], best[0], s0[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--mois", default="2026-07")
    ap.add_argument("--ids", default="")
    ap.add_argument("--hauteur", type=float, default=2.0)
    ap.add_argument("--dcap", type=float, default=0.0)
    ap.add_argument("--dxy", default="0,0")
    ap.add_argument("--out", default=str(OUT / "qa_panoramax"))
    ap.add_argument("--caler", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dx, dy = (float(v) for v in a.dxy.split(","))
    dtm = OUT / "relief" / "dtm_sol_10cm.tif"
    dtm = dtm if dtm.exists() else DTM15
    ids = [i for i in a.ids.split(",") if i]
    metas = []
    for f in sorted(PANO.glob("*_hd.json")):
        m = json.loads(f.read_text())
        if m.get("projection") != "equirectangular":
            continue
        if ids and m["id"] not in ids:
            continue
        if not ids and not m["datetime"].startswith(a.mois):
            continue
        m["_stem"] = f.name[:-5]
        metas.append(m)
    if not metas:
        sys.exit("aucune photo 360° retenue")
    views = []
    for m in metas:
        x, y = _t.transform(m["lon"], m["lat"])
        x, y = x + dx, y + dy
        z = float(sample_raster(dtm, [x], [y])[0]) + a.hauteur
        m["_eye"] = [x - O[0], y - O[1], z - O[2]]
        m["_cap"] = (m.get("azimuth") or 0) + a.dcap
        if a.caler:
            tmp = out / "_calage"
            tmp.mkdir(exist_ok=True)
            cdx, cdy, cdc, sc, sc0 = calibrer(m, m["_eye"], m["_cap"], Path(a.glb).resolve(), tmp, dtm, a.hauteur)
            x, y = x + cdx, y + cdy
            z = float(sample_raster(dtm, [x], [y])[0]) + a.hauteur
            m["_eye"] = [x - O[0], y - O[1], z - O[2]]
            m["_cap"] += cdc
            m["_calage"] = {"dx": cdx, "dy": cdy, "dcap": round(cdc, 2), "score": round(sc, 3), "score_initial": round(sc0, 3)}
            print(m["id"][:8], "calage", m["_calage"], flush=True)
            shutil.rmtree(tmp, ignore_errors=True)
        views.append({"nom": m["id"], "oeil": m["_eye"], "cap": m["_cap"],
                      "largeur": m["width"], "hauteur": m["height"]})
    vf = out / "vues.json"
    vf.write_text(json.dumps(views))
    raw = out / "_brut"
    subprocess.run(["node", str(RENDER), str(Path(a.glb).resolve()), str(vf), str(raw)], check=True)
    pairs = []
    for m in metas:
        img = Image.open(raw / f"{m['id']}.png").convert("RGB")
        d = out / m["id"]
        d.mkdir(exist_ok=True)
        W, H = img.size
        for r, y0 in enumerate(origins(H)):
            for c, x0 in enumerate(origins(W)):
                t = d / f"rendu_r{r:02d}_c{c:02d}.jpg"
                img.crop((x0, y0, x0 + TILE, y0 + TILE)).save(t, quality=90)
                ph = PANO / "tiles" / m["_stem"] / f"{m['_stem']}_r{r:02d}_c{c:02d}.jpg"
                lon = ((x0 + TILE / 2) / W - 0.5) * 360
                pairs.append({"photo": str(ph), "rendu": str(t),
                              "id": m["id"], "date": m["datetime"][:10],
                              "cap_centre_deg": round((m["_cap"] + lon) % 360, 1),
                              "calage": m.get("_calage"),
                              "elevation_centre_deg": round((0.5 - (y0 + TILE / 2) / H) * 180, 1),
                              "oeil_local": [round(v, 2) for v in m["_eye"]]})
        (raw / f"{m['id']}.png").unlink()
    raw.rmdir()
    (out / "paires.json").write_text(json.dumps(pairs, ensure_ascii=False, indent=1))
    print(len(metas), "photos,", len(pairs), "paires ->", out / "paires.json")


if __name__ == "__main__":
    main()
