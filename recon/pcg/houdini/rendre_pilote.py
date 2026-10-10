"""Rendus Karma XPU de contrôle de la zone pilote v2 (hython Houdini 22 : husk + OpenImageIO).

    hython recon/pcg/houdini/rendre_pilote.py                      # 6 vues -> recon/pc/rendus/v2_pilote/<vue>.png
    hython recon/pcg/houdini/rendre_pilote.py --vues d_ilot_brf,e_ilot_gravier --sur 1

Chaîne par vue (caméras /World/Cameras_v2 de recon/pc/houdini/cameras_v2_pilote.usda) :
1. husk (Karma XPU, KARMA_XPU_DISABLE_MIPMAPS=1 : aucun .rat à côté des textures) rend
   fabrique/rendu_pilote.usda en EXR linéaire (Rec.709), à `--sur` x la résolution (2 : 2000 x 2000) ;
2. exposition : EXPOSITION_EV commune (tête de bordure béton au soleil vers 170-200 sRGB, enrobé vers
   105-125, photos utilisateur 1 à 3) + la correction de la vue (pj_rendu.VUES[...]["ev"]) ; balance des
   blancs (pj_rendu.gains_balance : carte grise horizontale soleil + ciel légèrement chaude, B/R ≈ 0,94) ;
3. courbe d'épaule douce (linéaire jusqu'à 0,6, puis approche exponentielle de 1 : pas d'aplat blanc
   sur la peinture et le ciel), encodage sRGB, réduction filtrée (lanczos3) à la résolution finale ;
4. PNG 8 bits. L'EXR reste dans un dossier temporaire (supprimé), sauf --garder-exr DOSSIER ; le cache
   .rat que Karma écrit à côté de la texture du ciel (fabrique/ciel) est supprimé.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.dont_write_bytecode = True

import numpy as np                                            # noqa: E402
import OpenImageIO as oiio                                    # noqa: E402

import pj_commun as K                                         # noqa: E402
import pj_rendu as RD                                         # noqa: E402

EXPOSITION_EV = 0.65        # soleil à 29° (0,35 EV à 38°) : tête de bordure au soleil vers 170-200 sRGB, enrobé vers 105-125
EPAULE = 0.6


def husk():
    h = Path(sys.executable).parent / "husk.exe"
    if h.exists():
        return str(h)
    cands = sorted(Path("C:/Program Files/Side Effects Software").glob("Houdini 22*/bin/husk.exe"), reverse=True)
    if not cands:
        sys.exit("husk.exe introuvable")
    return str(cands[0])


def courbe(x):
    """Épaule douce : identité jusqu'à EPAULE, puis EPAULE + (1 − EPAULE)(1 − exp(−(x − EPAULE)/(1 − EPAULE)))."""
    k = 1.0 - EPAULE
    return np.where(x <= EPAULE, x, EPAULE + k * (1.0 - np.exp(-(x - EPAULE) / k)))


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def developper(exr, png, ev, res, gains=(1.0, 1.0, 1.0)):
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * (2.0 ** ev) * np.asarray(gains, dtype=np.float32)
    y = srgb(courbe(np.maximum(a, 0.0))).astype(np.float32)
    b = oiio.ImageBuf(oiio.ImageSpec(y.shape[1], y.shape[0], 3, oiio.FLOAT))
    b.set_pixels(oiio.ROI(), y)
    if y.shape[0] != res:
        b = oiio.ImageBufAlgo.resize(b, "lanczos3", roi=oiio.ROI(0, res, 0, res, 0, 1, 0, 3))
    b = oiio.ImageBufAlgo.clamp(b, 0.0, 1.0)
    b.specmod().attribute("Software", "rendre_pilote.py")
    if not b.write(str(png), "uint8"):
        raise RuntimeError(b.geterror())


def main():
    ap = argparse.ArgumentParser(description="Rendus Karma XPU de la zone pilote v2")
    ap.add_argument("--usd", default=str(K.FABRIQUE / "rendu_pilote.usda"))
    ap.add_argument("--dossier", default=str(K.RACINE / "recon/pc/rendus/v2_pilote"))
    ap.add_argument("--vues", default=",".join(n for n, _ in RD.VUES))
    ap.add_argument("--res", type=int, default=1000)
    ap.add_argument("--sur", type=int, default=2, help="sur-échantillonnage (rendu à res x sur)")
    ap.add_argument("--ev", type=float, default=EXPOSITION_EV, help="exposition commune (EV)")
    ap.add_argument("--garder-exr", help="dossier où garder les EXR")
    ap.add_argument("--limite", type=int, default=900)
    a = ap.parse_args()
    vues = dict(RD.VUES)
    sortie = Path(a.dossier)
    sortie.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="pj_rendu_"))
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    echecs = []
    try:
        for nom in [v.strip() for v in a.vues.split(",") if v.strip()]:
            exr = tmp / f"{nom}.exr"
            r = a.res * a.sur
            cmd = [husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/rendersettings",
                   "--camera", f"/World/Cameras_v2/{nom}", "--res", str(r), str(r), "--frame", "1",
                   "--output", exr.as_posix(), "--make-output-path", "--timelimit", str(a.limite), "--verbose", "1",
                   Path(a.usd).as_posix()]
            t = time.time()
            res = subprocess.run(cmd, env=env, cwd=str(Path(a.usd).parent), capture_output=True, text=True,
                                 encoding="utf-8", errors="replace")
            if res.returncode != 0 or not exr.exists():
                print(res.stdout[-2000:], res.stderr[-2000:])
                echecs.append(nom)
                continue
            ev = a.ev + float(vues[nom].get("ev", 0.0))
            developper(exr, sortie / f"{nom}.png", ev, a.res, RD.gains_balance())
            if a.garder_exr:
                Path(a.garder_exr).mkdir(parents=True, exist_ok=True)
                shutil.copy2(exr, Path(a.garder_exr) / exr.name)
            print(f"   {nom} : {time.time() - t:.0f} s, EV {ev:+.2f} -> {sortie / (nom + '.png')}", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # Karma convertit la texture du dôme en .rat à côté d'elle (fabrique/ciel) : cache supprimé
        for rat in sorted((Path(a.usd).parent / "ciel").glob("*.rat")):
            rat.unlink()
    if echecs:
        sys.exit(f"rendus en échec : {', '.join(echecs)}")


if __name__ == "__main__":
    main()
