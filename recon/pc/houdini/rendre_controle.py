"""Rendus Karma de contrôle (husk) des 4 caméras sur rendu_controle.usda.

Lancement (python 3 ou hython) :
    python recon/pc/houdini/rendre_controle.py [VERSION] [options]
    ex. : python recon/pc/houdini/rendre_controle.py v1
          python recon/pc/houdini/rendre_controle.py lookdev_v1 --couche recon/pc/houdini/lookdev.usda
          python recon/pc/houdini/rendre_controle.py v1 --cameras cam2_conducteur_verdun_so --cpu

Sorties : recon/pc/rendus/<VERSION>/<caméra>.png, 1000x1000 (sauf --res / --dossier).
Par défaut Karma XPU (GPU), 64 échantillons + débruitage OIDN (réglages de /Render/rendersettings
dans rendu_controle.usda, créé par creer_hip.py) : ~10-20 s par image sur RTX 5070.
--couche ajoute une ou plusieurs couches USD au-dessus de la scène (look-dev, variantes...) via
un fichier racine temporaire.
Karma XPU écrit sinon des .rat (MIP maps) à côté des textures, donc dans le paquet :
KARMA_XPU_DISABLE_MIPMAPS=1 est posé par défaut (--mipmaps pour l'autoriser).
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent                      # recon/pc/houdini
CAMERAS = ["cam1_ensemble_sud", "cam2_conducteur_verdun_so", "cam3_pieton_traversee_so",
           "cam4_conducteur_vercors"]
SETTINGS = "/Render/rendersettings"


def trouver_husk():
    candidats = [os.environ.get("HUSK", "")]
    if os.environ.get("HFS"):
        candidats.append(os.path.join(os.environ["HFS"], "bin", "husk.exe"))
    candidats.append(os.path.join(os.path.dirname(sys.executable), "husk.exe"))  # lancé par hython
    candidats += sorted(glob.glob(r"C:/Program Files/Side Effects Software/Houdini 22*/bin/husk.exe"),
                        reverse=True)
    for c in candidats:
        if c and os.path.isfile(c):
            return c
    sys.exit("husk.exe introuvable : définis HFS (dossier d'installation de Houdini) ou HUSK")


def scene_racine(usd, couches):
    """Fichier racine temporaire : couches supplémentaires (la première est la plus forte) + scène."""
    if not couches:
        return usd, None
    subs = [Path(c).resolve() for c in couches] + [usd]
    for s in subs:
        if not s.exists():
            sys.exit(f"couche introuvable : {s}")
    lignes = ",\n".join(f"        @{s.as_posix()}@" for s in subs)
    texte = ('#usda 1.0\n(\n    defaultPrim = "World"\n    metersPerUnit = 1\n    upAxis = "Z"\n'
             f'    renderSettingsPrimPath = "{SETTINGS}"\n    subLayers = [\n{lignes}\n    ]\n)\n')
    fd, tmp = tempfile.mkstemp(prefix="rendu_controle_", suffix=".usda")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(texte)
    return Path(tmp), tmp


def main():
    ap = argparse.ArgumentParser(description="Rendus husk de contrôle du carrefour Paquet Jardin")
    ap.add_argument("version", nargs="?", default="v1", help="sous-dossier de recon/pc/rendus (v1)")
    ap.add_argument("--cameras", default=",".join(CAMERAS),
                    help="noms (sous /World/Cameras) ou chemins de prims, séparés par des virgules")
    ap.add_argument("--couche", action="append", default=[],
                    help="couche USD ajoutée au-dessus de la scène (répétable)")
    ap.add_argument("--usd", default=str(ICI / "rendu_controle.usda"), help="scène à rendre")
    ap.add_argument("--dossier", help="dossier de sortie (défaut recon/pc/rendus/<version>)")
    ap.add_argument("--res", type=int, default=1000, help="résolution (carrée), défaut 1000")
    ap.add_argument("--echantillons", type=int, help="échantillons par pixel (défaut : réglages, 64)")
    ap.add_argument("--cpu", action="store_true", help="Karma CPU au lieu de Karma XPU")
    ap.add_argument("--mipmaps", action="store_true", help="laisse Karma XPU créer les .rat")
    ap.add_argument("--limite", type=int, default=600, help="temps max par image, en secondes")
    a = ap.parse_args()

    usd = Path(a.usd).resolve()
    if not usd.exists():
        sys.exit(f"introuvable : {usd} (lancer d'abord : hython {ICI / 'creer_hip.py'})")
    sortie = Path(a.dossier).resolve() if a.dossier else ICI.parent / "rendus" / a.version
    sortie.mkdir(parents=True, exist_ok=True)
    husk = trouver_husk()
    racine, tmp = scene_racine(usd, a.couche)
    env = dict(os.environ)
    if not a.mipmaps:
        env["KARMA_XPU_DISABLE_MIPMAPS"] = "1"
    moteur = ["-R", "BRAY_HdKarma", "--engine", "cpu"] if a.cpu else \
        ["-R", "BRAY_HdKarmaXPU", "--engine", "xpu"]

    echecs = []
    try:
        for cam in [c.strip() for c in a.cameras.split(",") if c.strip()]:
            prim = cam if cam.startswith("/") else f"/World/Cameras/{cam}"
            png = sortie / f"{prim.rsplit('/', 1)[-1]}.png"
            cmd = [husk, *moteur, "--settings", SETTINGS, "--camera", prim,
                   "--res", str(a.res), str(a.res), "--frame", "1", "--output", png.as_posix(),
                   "--make-output-path", "--timelimit", str(a.limite), "--verbose", "1"]
            if a.echantillons:
                cmd += ["--pixel-samples", str(a.echantillons)]
            cmd.append(racine.as_posix())
            print(">>", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
            t = time.time()
            r = subprocess.run(cmd, env=env, cwd=str(ICI))
            ok = r.returncode == 0 and png.exists() and png.stat().st_mtime >= t - 1
            print(f"   {'ok' if ok else 'ÉCHEC'} : {png} ({time.time() - t:.0f} s)", flush=True)
            if not ok:
                echecs.append(cam)
    finally:
        if tmp:
            os.remove(tmp)
    if echecs:
        sys.exit(f"rendus en échec : {', '.join(echecs)}")
    print("Images dans", sortie)


main()
