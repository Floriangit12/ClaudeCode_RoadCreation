"""Crée recon/pc/houdini/paquet_jardin.hip et exporte rendu_controle.usda (Houdini 22, sans interface).

Lancement :
    hython recon/pc/houdini/creer_hip.py [--rotation-solaris] [--hip CHEMIN.hip]

Étapes :
  1. session vide, $HIP = recon/pc/houdini/ ;
  2. exécute recon/package_src/houdini/charger_paquet_jardin.py (source maintenue du script du
     paquet) avec les surcharges PAQUET_JARDIN_PKG / PAQUET_JARDIN_ROTATION_SOLARIS ;
  3. chemin du Sublayer du paquet converti en $HIP/../../out/paquet_jardin/package/... ;
  4. ajoute après les lumières :
       /stage/cameras             Sublayer LOP sur $HIP/cameras.usda (4 caméras /World/Cameras/*)
       /stage/rendu_karma         Karma Render Settings (/Render/rendersettings, 1000x1000, XPU)
       /stage/<caméra>            un USD Render ROP par caméra -> $HIP/../rendus/v1/<caméra>.png
                                  (Karma XPU ; pré-rendu : KARMA_XPU_DISABLE_MIPMAPS=1)
       /stage/export_rendu_controle  USD ROP -> $HIP/rendu_controle.usda (non aplati : le paquet
                                  et cameras.usda y restent des sublayers en chemins relatifs)
  5. exporte rendu_controle.usda, vérifie ses sublayers, sauve le .hip (.hiplc en licence Indie).
Les rendus de contrôle se lancent ensuite avec rendre_controle.py (husk).
"""
import argparse
import os
import runpy
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent                      # recon/pc/houdini
RECON = ICI.parents[1]                                      # recon
SCRIPT = RECON / "package_src" / "houdini" / "charger_paquet_jardin.py"
PKG = RECON / "out" / "paquet_jardin" / "package"
CAMERAS = ["cam1_ensemble_sud", "cam2_conducteur_verdun_so", "cam3_pieton_traversee_so",
           "cam4_conducteur_vercors"]
RESOLUTION = 1000
ECHANTILLONS = 64       # path traced samples (débruitage OIDN en plus)


def chemin_hip(cible, hip_dir):
    """Chemin écrit dans un paramètre : $HIP/<relatif> si possible (dépôt clonable ailleurs)."""
    try:
        return "$HIP/" + os.path.relpath(cible, hip_dir).replace("\\", "/")
    except ValueError:  # autre lecteur Windows
        return str(cible).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rotation-solaris", action="store_true", help="ROTATION_SOLARIS = True")
    ap.add_argument("--hip", default=str(ICI / "paquet_jardin.hip"), help="fichier .hip à écrire")
    a = ap.parse_args()
    hip = Path(a.hip).resolve()
    hip_dir = hip.parent

    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.setName(str(hip).replace("\\", "/"))
    os.environ["PAQUET_JARDIN_PKG"] = str(PKG).replace("\\", "/")
    os.environ["PAQUET_JARDIN_ROTATION_SOLARIS"] = "1" if a.rotation_solaris else "0"
    noeuds = runpy.run_path(str(SCRIPT))["NOEUDS"]

    stage = hou.node("/stage")
    sub = noeuds["sublayer"]
    sub.parm("filepath1").set(chemin_hip(PKG / "paquet_jardin_2026.usda", hip_dir))

    # caméras (couche à part, créée à côté du .hip ; tolérée absente le temps de la créer)
    cams = stage.createNode("sublayer", "cameras")
    cams.setInput(0, noeuds["dernier_lop"])
    cams.parm("filepath1").set("$HIP/cameras.usda")
    cams.parm("handlemissingfiles").set("allow")
    # sous les couches implicites (lumières, rotation) : sinon l'USD ROP ne peut pas les aplatir
    # dans rendu_controle.usda et voudrait les écrire à part (stage/soleil.usd)
    cams.parm("positiontype").set("strongestfile")

    # réglages Karma
    k = stage.createNode("karmarenderproperties", "rendu_karma")
    k.setInput(0, cams)
    k.parm("camera").set(f"/World/Cameras/{CAMERAS[0]}")
    k.parm("res_mode").set("manual")
    for n in ("resolutionx", "resolutiony"):
        p = k.parm(n)
        p.lock(False)            # resolutiony est verrouillé sur une expression en mode « auto »
        p.deleteAllKeyframes()
        p.set(RESOLUTION)
    k.parm("engine").set("xpu")
    k.parm("pathtracedsamples").set(ECHANTILLONS)
    k.parm("denoiser").set("oidn")
    # nom d'image neutre (sans chemin absolu) : husk et les ROP ci-dessous le remplacent
    k.parm("picture").set("rendu_controle.png")
    k.setDisplayFlag(True)

    # un USD Render ROP par caméra : le nom du nœud est le nom de la caméra
    for cam in CAMERAS:
        r = stage.createNode("usdrender_rop", cam)
        r.setInput(0, k)
        r.parm("renderer").set("BRAY_HdKarmaXPU")
        r.parm("rendersettings").set("/Render/rendersettings")
        r.parm("override_camera").set("/World/Cameras/$OS")
        r.parm("outputimage").set("$HIP/../rendus/v1/$OS.png")
        r.parm("mkpath").set(1)
        # sinon Karma XPU écrit des .rat (MIP maps) à côté des textures, dans le paquet
        r.parm("lprerender").set("python")
        r.parm("prerender").set("import os; os.environ['KARMA_XPU_DISABLE_MIPMAPS'] = '1'")

    # export non aplati pour husk
    u = stage.createNode("usd_rop", "export_rendu_controle")
    u.setInput(0, k)
    u.parm("lopoutput").set("$HIP/rendu_controle.usda")
    u.parm("savestyle").set("flattenimplicitlayers")      # lumières/réglages dans le fichier,
    u.parm("flattenfilelayers").set(0)                    # paquet et caméras en sublayers
    u.parm("savefilesfromdisk").set(0)                    # ne jamais réécrire le paquet
    u.parm("enableoutputprocessor_simplerelativepaths").set(1)
    stage.layoutChildren()

    k.cook(force=True)
    for n in stage.children():
        for msg in n.errors() + n.warnings():
            print("  [avertissement]", n.path(), msg)
    u.render()
    if u.errors():
        sys.exit(f"export USD en échec : {u.errors()}")
    usd = hip_dir / "rendu_controle.usda"
    verifier_export(usd)

    hou.hipFile.save(str(hip).replace("\\", "/"))
    print("Hip :", hou.hipFile.path())
    print("Export :", usd)


def verifier_export(usd):
    from pxr import Sdf
    lay = Sdf.Layer.FindOrOpen(str(usd))
    lay.Reload()
    print("Sublayers de", usd.name, ":", list(lay.subLayerPaths))
    for p in lay.subLayerPaths:
        if os.path.isabs(p) or ":" in p:
            print("  [attention] chemin absolu :", p)
        elif not (usd.parent / p).exists():
            print("  [attention] fichier absent pour l'instant :", p)


main()
