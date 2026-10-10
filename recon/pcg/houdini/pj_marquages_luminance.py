"""Contrôle de luminance des marquages sur les rendus Karma (revue réalisme du 10/10) : pour chaque entité visible d'une vue
rapprochée, luminance sRGB (moyenne R, V, B) médiane de l'intérieur de la marque (masque des triangles projetés, érodé de
2 px) rapportée à la médiane de l'enrobé voisin (fenêtre de 8 px autour de la marque, hors marques), comparée à la cible de
sa classe d'usure (photos Panoramax 734a, 4e72, 20d1a815, f8d91bb1 : contraste peinture / enrobé).

    hython recon/pcg/houdini/pj_marquages_luminance.py [--vues a_fleche_td_tad,...] [--dossier recon/pc/rendus/v2_marquages]

Sortie : <dossier>/luminance_marquages.json {vue: [{id, maillage, n_px, p10, p50, p90, enrobe, rapport, cible, ok}]} et
un résumé par classe d'usure (médiane des rapports, part dans la cible). Contrôle informatif (non bloquant) : le rapport
dépend de l'enrobé voisin (neuf 2025 sombre, ancien v1 plus clair) et de l'éclairage de la vue.
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.dont_write_bytecode = True

import numpy as np                                            # noqa: E402
from PIL import Image                                         # noqa: E402
from pxr import Usd, UsdGeom                                  # noqa: E402

import pj_commun as K                                         # noqa: E402

CIBLES = {"0": (1.85, 2.15), "1": (1.45, 1.65), "2": (1.30, 1.50), "3": (1.12, 1.32), "F": (1.05, 1.18)}
VUES = ["a_fleche_td_tad", "b_zebra_verdun_sw", "c_traversee_cyclable", "t_dessus_centre", "p_20d1a815"]


def mesurer(st, campath, png, n_min=40):
    cam = UsdGeom.Camera(st.GetPrimAtPath(campath)).GetCamera(Usd.TimeCode.Default())
    fr = cam.frustum
    A0 = np.array(fr.ComputeViewMatrix()) @ np.array(fr.ComputeProjectionMatrix())
    img = np.asarray(Image.open(png).convert("RGB")).astype(float).mean(2)
    H, W = img.shape
    rng = np.random.default_rng(20261010)
    idimg = np.full((H, W), -1, int)
    noms, maillages = [], []
    racine = st.GetPrimAtPath("/World/PJ_Marquages")
    for mesh in sorted(racine.GetChildren(), key=lambda p: p.GetName()):
        if not mesh.IsA(UsdGeom.Mesh):
            continue
        M = UsdGeom.Mesh(mesh)
        P = np.array(M.GetPointsAttr().Get(), dtype=np.float64)
        T = np.array(M.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
        pv = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("id")
        idv = np.array(pv.Get())
        idx = pv.GetIndices()
        if idx is not None and len(idx):
            idv = idv[np.array(idx)]
        xf = np.array(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        P = (np.c_[P, np.ones(len(P))] @ xf)[:, :3]
        Q = np.c_[P, np.ones(len(P))] @ A0
        w = Q[:, 3]
        x = np.where(w > 0, (Q[:, 0] / np.where(w > 0, w, 1) + 1) / 2 * W, -1e9)
        y = np.where(w > 0, (1 - Q[:, 1] / np.where(w > 0, w, 1)) / 2 * H, -1e9)
        for k, t in enumerate(T):
            if (w[t] <= 0).any():
                continue
            xs, ys = x[t], y[t]
            if xs.max() < 0 or xs.min() >= W or ys.max() < 0 or ys.min() >= H:
                continue
            apx = 0.5 * abs((xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0]))
            n = int(min(max(apx * 6, 3), 200000))
            u = rng.random((n, 2))
            m = u.sum(1) > 1
            u[m] = 1 - u[m]
            px = xs[0] + u[:, 0] * (xs[1] - xs[0]) + u[:, 1] * (xs[2] - xs[0])
            py = ys[0] + u[:, 0] * (ys[1] - ys[0]) + u[:, 1] * (ys[2] - ys[0])
            ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
            nm = str(idv[k])
            if nm not in noms:
                noms.append(nm)
                maillages.append(mesh.GetName())
            idimg[py[ok].astype(int), px[ok].astype(int)] = noms.index(nm)
    inner = idimg.copy()
    for dy, dx in [(1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)]:
        inner = np.where(np.roll(np.roll(idimg, dy, 0), dx, 1) == idimg, inner, -1)
    occ = idimg >= 0
    for _ in range(3):
        occ = occ | np.roll(occ, 1, 0) | np.roll(occ, -1, 0) | np.roll(occ, 1, 1) | np.roll(occ, -1, 1)
    out = []
    for j, nm in enumerate(noms):
        m = inner == j
        c = int(m.sum())
        if c < n_min:
            continue
        ys, xs = np.nonzero(m)
        v = img[m]
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        win = img[max(0, y0 - 8):y1 + 9, max(0, x0 - 8):x1 + 9]
        o = occ[max(0, y0 - 8):y1 + 9, max(0, x0 - 8):x1 + 9]
        bg = win[~o]
        if len(bg) < 30:
            continue
        usure = maillages[j].split("_u")[-1]
        r = float(np.percentile(v, 50) / max(np.median(bg), 1.0))
        cible = CIBLES.get(usure)
        out.append({"id": nm, "maillage": maillages[j], "n_px": c, "p10": round(float(np.percentile(v, 10)), 1),
                    "p50": round(float(np.percentile(v, 50)), 1), "p90": round(float(np.percentile(v, 90)), 1),
                    "enrobe": round(float(np.median(bg)), 1), "rapport": round(r, 3), "cible": cible,
                    "ok": bool(cible and cible[0] <= r <= cible[1])})
    return sorted(out, key=lambda d: (-d["n_px"], d["id"]))


def main():
    ap = argparse.ArgumentParser(description="Contrôle de luminance des marquages sur les rendus")
    ap.add_argument("--fabrique", default=str(K.FABRIQUE))
    ap.add_argument("--dossier", default=str(K.RACINE / "recon/pc/rendus/v2_marquages"))
    ap.add_argument("--vues", default=",".join(VUES))
    a = ap.parse_args()
    st = Usd.Stage.Open(str(Path(a.fabrique) / "marquages_rendu.usda"))
    res, resume = {}, {}
    for v in [x for x in a.vues.split(",") if x]:
        png = Path(a.dossier) / f"{v}.png"
        if not png.exists():
            continue
        res[v] = mesurer(st, f"/World/Cameras_marquages/{v}", png)
    for u in CIBLES:
        rs = [d["rapport"] for l in res.values() for d in l if d["maillage"].endswith("_u" + u)]
        oks = [d["ok"] for l in res.values() for d in l if d["maillage"].endswith("_u" + u)]
        if rs:
            resume[u] = {"n": len(rs), "mediane": round(float(np.median(rs)), 3), "cible": CIBLES[u],
                         "part_dans_cible": round(float(np.mean(oks)), 2)}
    sortie = Path(a.dossier) / "luminance_marquages.json"
    sortie.write_text(json.dumps({"methode": __doc__.split("\n\n")[0], "cibles": CIBLES, "resume": resume, "vues": res},
                                 ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(resume, ensure_ascii=False))


if __name__ == "__main__":
    main()
