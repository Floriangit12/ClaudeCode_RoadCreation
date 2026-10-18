"""Rendus Karma de la scène fabriquée depuis les poses affinées (exécuté par hython ; appelé par comparer_multivues.py).

    hython recon/generateur/comparaison/rendu_hython.py <travail.json>

Pour chaque vue du fichier de travail :
1. ciel physique (rendu/ciel.py, Preetham, ciel clair) au soleil de la date et de l'heure de la photo, avec les
   réglages de l'étape 1 de rendu/rendu_l2b.py (voile d'horizon, fond sous l'horizon à la radiance du sol neutre) ;
2. une couche USD superposée (aucune modification de la scène) : sous-couche = <scène>/rendus/scene_rendu.usda
   (route fabriquée L2 + L2b, matériaux, socle, lumières) ; surcharges : direction du soleil (Soleil, Soleil_sol),
   textures des dômes, caméra de comparaison (pose affinée, même champ et même cadrage que la vue photo), résolution ;
3. husk (Karma XPU) -> EXR -> PNG sRGB au développement de rendu_l2b.developper (épaule au-dessus de 0,8, courbe en
   S), exposition fixe calculée pour la hauteur du soleil de la photo (albédo 1 horizontal -> gain 1).
Les constantes d'éclairage sont relues dans <scène>/rendus/manifest_rendus.json quand elles y sont.

Mode « par lots » (job["par_lots"], comparaison v2) : les vues de même résolution sont rendues par UN appel husk
(au plus LOT_MAX images) : caméra, soleil et textures des dômes en échantillons temporels (image k = vue k), un ciel
par couple (hauteur, azimut) du soleil. Chargement de la scène une seule fois : ≈ 5 s par vue au lieu de 14 à 30 s
(essai du 18/10/2026 sur Paquet Jardin). Si un lot échoue, ses vues sont rendues une par une (mode historique).
"""
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

DEPOT = Path(__file__).resolve().parents[3]
RENDU = DEPOT / "recon" / "generateur" / "rendu"

# valeurs de rendu/rendu_l2b.py (étape 1, route seule), reprises si le manifeste de la scène ne les donne pas
SOLEIL = 4.2
PART_CIEL = 0.17
TURBIDITE = 2.8
CIEL_FOND = 2.2
CONTRASTE = 0.50
EXPO_GAIN = 1.0
SOL_NEUTRE = (0.50, 0.485, 0.445)
VOILE_ROUTE_SEULE = (0.90, 0.97, 1.08)
ECHANTILLONS = 128


def _ciel_module():
    spec = importlib.util.spec_from_file_location("ciel_rg", RENDU / "ciel.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def husk():
    h = Path(sys.executable).parent / "husk.exe"
    if h.exists():
        return str(h)
    return str(sorted(Path("C:/Program Files/Side Effects Software").glob("Houdini 22*/bin/husk.exe"))[-1])


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def developper(exr, png, expo, contraste):
    import OpenImageIO as oiio
    from PIL import Image
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * expo
    ep = 0.80
    y = np.where(a <= ep, a, ep + (1 - ep) * (1 - np.exp(-(a - ep) / (1 - ep))))
    v = srgb(y)
    v = np.clip(v - contraste / (2 * math.pi) * np.sin(2 * math.pi * v), 0.0, 1.0)
    Image.fromarray((v * 255 + 0.5).astype(np.uint8)).save(png)


def matrice_soleil(el, az):
    """Matrice de la DistantLight (comme rendu_l2b.lumieres : SetLookAt(d, 0, Z).GetInverse(), sans translation)."""
    e, a = math.radians(el), math.radians(az)
    d = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    f = -d
    r = np.cross(f, [0.0, 0.0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return [list(r) + [0.0], list(u) + [0.0], list(d) + [0.0], [0.0, 0.0, 0.0, 1.0]]


def _m4(m):
    return "( " + ", ".join("(" + ", ".join("%.12g" % v for v in row) + ")" for row in m) + " )"


def couche(usd, scene_usda, nom_cam, cam, el, az, ciel, ciel_fond, route_seule):
    """Écrit la couche superposée (texte USDA)."""
    rel = os.path.relpath(scene_usda, Path(usd).parent).replace("\\", "/")
    ms = _m4(matrice_soleil(el, az))
    mc = cam["matrice"]
    mc = [list(r[:3]) + [0.0] for r in mc[:3]] + [list(mc[3][:3]) + [1.0]]
    lignes = ['#usda 1.0', '(', '    defaultPrim = "Monde"', '    metersPerUnit = 1', '    upAxis = "Z"',
              '    subLayers = [', f'        @{rel}@', '    ]', ')', '', 'over "Lumieres"', '{']
    for nom in ("Soleil", "Soleil_sol"):
        lignes += [f'    over "{nom}"', '    {', f'        matrix4d xformOp:transform = {ms}', '    }']
    lignes += ['    over "Ciel"', '    {', f'        asset inputs:texture:file = @{Path(ciel).name}@', '    }']
    if route_seule:
        lignes += ['    over "Ciel_sol"', '    {', f'        asset inputs:texture:file = @{Path(ciel).name}@', '    }']
        lignes += ['    over "Ciel_fond"', '    {', f'        asset inputs:texture:file = @{Path(ciel_fond).name}@', '    }']
    lignes += ['}', '', 'over "Cameras"', '{', f'    def Camera "{nom_cam}"', '    {',
               '        float2 clippingRange = (0.05, 20000)',
               f'        float focalLength = {cam["focale_mm"]:.6f}',
               f'        float horizontalAperture = {cam["ouverture_h_mm"]:.6f}',
               f'        float verticalAperture = {cam["ouverture_v_mm"]:.6f}',
               '        token projection = "perspective"',
               f'        matrix4d xformOp:transform = {_m4(mc)}',
               '        uniform token[] xformOpOrder = ["xformOp:transform"]', '    }', '}', '',
               'over "Render"', '{', '    over "reglages"', '    {',
               f'        uniform int2 resolution = ({cam["resolution"][0]}, {cam["resolution"][1]})', '    }', '}', '']
    Path(usd).write_text("\n".join(lignes), encoding="utf-8")


LOT_MAX = 40


def _ts(vals):
    return "{ " + ", ".join(f"{k + 1}: {v}" for k, v in enumerate(vals)) + " }"


def couche_lot(usd, scene_usda, nom_cam, vues, cieux, route_seule):
    """Couche superposée d'un lot : image k (1..N) = vue k ; caméra, soleil et dômes en échantillons temporels."""
    rel = os.path.relpath(scene_usda, Path(usd).parent).replace("\\", "/")
    n = len(vues)
    soleils = [_m4(matrice_soleil(v["_el"], v["_az"])) for v in vues]
    cams = []
    for v in vues:
        mc = v["camera"]["matrice"]
        cams.append(_m4([list(r[:3]) + [0.0] for r in mc[:3]] + [list(mc[3][:3]) + [1.0]]))
    W, H = vues[0]["camera"]["resolution"]
    L = ['#usda 1.0', '(', '    defaultPrim = "Monde"', '    metersPerUnit = 1', '    upAxis = "Z"',
         '    startTimeCode = 1', f'    endTimeCode = {n}', '    subLayers = [', f'        @{rel}@', '    ]', ')', '',
         'over "Lumieres"', '{']
    for nom in ("Soleil", "Soleil_sol"):
        L += [f'    over "{nom}"', '    {', f'        matrix4d xformOp:transform.timeSamples = {_ts(soleils)}', '    }']
    ciel = _ts([f"@{Path(c[0]).name}@" for c in cieux])
    L += ['    over "Ciel"', '    {', f'        asset inputs:texture:file.timeSamples = {ciel}', '    }']
    if route_seule:
        fond = _ts([f"@{Path(c[1]).name}@" for c in cieux])
        L += ['    over "Ciel_sol"', '    {', f'        asset inputs:texture:file.timeSamples = {ciel}', '    }']
        L += ['    over "Ciel_fond"', '    {', f'        asset inputs:texture:file.timeSamples = {fond}', '    }']
    L += ['}', '', 'over "Cameras"', '{', f'    def Camera "{nom_cam}"', '    {',
          '        float2 clippingRange = (0.05, 20000)',
          f'        float focalLength.timeSamples = {_ts(["%.6f" % v["camera"]["focale_mm"] for v in vues])}',
          f'        float horizontalAperture.timeSamples = {_ts(["%.6f" % v["camera"]["ouverture_h_mm"] for v in vues])}',
          f'        float verticalAperture.timeSamples = {_ts(["%.6f" % v["camera"]["ouverture_v_mm"] for v in vues])}',
          '        token projection = "perspective"',
          f'        matrix4d xformOp:transform.timeSamples = {_ts(cams)}',
          '        uniform token[] xformOpOrder = ["xformOp:transform"]', '    }', '}', '',
          'over "Render"', '{', '    over "reglages"', '    {', f'        uniform int2 resolution = ({W}, {H})', '    }',
          '}', '']
    Path(usd).write_text("\n".join(L), encoding="utf-8")


def rendre_lots(job, vues, dossier, CI, P):
    """Rendus groupés par résolution (un appel husk par lot). P : paramètres d'éclairage. Renvoie (résultats, vues
    à reprendre une par une)."""
    resultats, reprendre = [], []
    cieux = {}
    for v in vues:
        v["_el"] = max(float(v["soleil_hauteur_deg"]), 4.0)
        v["_az"] = float(v["soleil_azimut_modele_deg"])
        cle = (round(v["_el"], 1), round(v["_az"], 1))
        if cle not in cieux:
            k = len(cieux)
            ciel, ciel_fond = dossier / f"ciel_l{k:03d}.exr", dossier / f"ciel_fond_l{k:03d}.exr"
            if P["route_seule"]:
                CI.ciel_exr(ciel, v["_el"], v["_az"], P["turb"], P["part"], P["soleil"], nuages=0.0, voile=0.92,
                            teinte_voile=VOILE_ROUTE_SEULE)
                e_tot = P["soleil"] * math.sin(math.radians(v["_el"])) * (1.0 + P["part"])
                l_sol = [c * e_tot / math.pi / CIEL_FOND * t for c, t in zip(SOL_NEUTRE, (0.985, 0.965, 0.93))]
                CI.ciel_exr(ciel_fond, v["_el"], v["_az"], P["turb"], P["part"], P["soleil"], nuages=0.0,
                            sol_radiance=l_sol, voile=0.92, teinte_voile=VOILE_ROUTE_SEULE)
            else:
                CI.ciel_exr(ciel, v["_el"], v["_az"], P["turb"], P["part"], P["soleil"])
            cieux[cle] = (ciel, ciel_fond)
        v["_ciel"] = cieux[cle]
    groupes = {}
    for v in vues:
        groupes.setdefault(tuple(v["camera"]["resolution"]), []).append(v)
    n_lot = 0
    for (W, H), lst in sorted(groupes.items()):
        for k0 in range(0, len(lst), LOT_MAX):
            lot = lst[k0:k0 + LOT_MAX]
            t0 = time.time()
            nom = f"lot{n_lot:02d}"
            n_lot += 1
            usd = dossier / f"{nom}.usda"
            couche_lot(usd, job["scene_usda"], "cmp_" + nom, lot, [v["_ciel"] for v in lot], P["route_seule"])
            exr_dir = dossier / "_exr"
            exr_dir.mkdir(parents=True, exist_ok=True)
            for f in exr_dir.glob(f"{nom}_*.exr"):
                f.unlink()
            lim = int(job.get("limite_s", 240))
            cmd = [husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/reglages", "--camera",
                   f"/Cameras/cmp_{nom}", "--res", str(W), str(H), "-f", "1", "-n", str(len(lot)), "-p",
                   str(job.get("echantillons", ECHANTILLONS)), "--output", (exr_dir / f"{nom}_$F4.exr").as_posix(),
                   "--make-output-path", "--timelimit", str(lim), "--timelimit-image", "--verbose", "1", usd.as_posix()]
            env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
            try:
                r = subprocess.run(cmd, env=env, cwd=str(dossier), capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=len(lot) * (lim + 60) + 300)
                code = r.returncode
            except subprocess.TimeoutExpired:
                code = -1
            duree = time.time() - t0
            for k, v in enumerate(lot):
                exr = exr_dir / f"{nom}_{k + 1:04d}.exr"
                if code != 0 or not exr.exists():
                    reprendre.append(v)
                    continue
                expo = math.pi / (P["soleil"] * math.sin(math.radians(v["_el"])) * (1.0 + P["part"])) * EXPO_GAIN
                png = Path(v["sortie_png"])
                png.parent.mkdir(parents=True, exist_ok=True)
                developper(exr, png, expo, P["contraste"])
                exr.unlink()
                resultats.append({"nom": v["nom"], "png": str(png), "usd": str(usd), "lot": nom, "image_du_lot": k + 1,
                                  "duree_s": round(duree / len(lot), 1), "exposition": round(expo, 5),
                                  "soleil_rendu": [round(v["_el"], 2), round(v["_az"], 2)], "contraste": P["contraste"],
                                  "route_seule": P["route_seule"]})
            print("lot", nom, len(lot), "vues", W, "x", H, round(duree, 1), "s", "code", code, flush=True)
    for v in vues:
        for k in ("_el", "_az", "_ciel"):
            v.pop(k, None)
    return resultats, reprendre


def main(travail):
    job = json.loads(Path(travail).read_text(encoding="utf-8"))
    CI = _ciel_module()
    man = json.loads(Path(job["manifest_rendus"]).read_text(encoding="utf-8")) if Path(job["manifest_rendus"]).exists() else {}
    ecl = man.get("eclairage", {})
    soleil = float(ecl.get("soleil_intensite", SOLEIL))
    part = float(ecl.get("part_ciel", PART_CIEL))
    turb = float((ecl.get("ciel") or {}).get("turbidite", TURBIDITE))
    route_seule = int(man.get("etape", 1)) == 1
    contraste = CONTRASTE
    courbe = str(ecl.get("courbe", ""))
    if "courbe en S" in courbe:
        try:
            contraste = float(courbe.split("courbe en S")[-1].strip().split()[0].replace(",", "."))
        except ValueError:
            pass
    dossier = Path(job["dossier"])
    dossier.mkdir(parents=True, exist_ok=True)
    resultats = []
    a_rendre = job["vues"]
    if job.get("par_lots"):
        P = {"soleil": soleil, "part": part, "turb": turb, "route_seule": route_seule, "contraste": contraste}
        resultats, a_rendre = rendre_lots(job, [dict(v) for v in job["vues"]], dossier, CI, P)
        if a_rendre:
            print("reprise une par une :", [v["nom"] for v in a_rendre], flush=True)
    for v in a_rendre:
        t0 = time.time()
        nom = v["nom"]
        el = max(float(v["soleil_hauteur_deg"]), 4.0)
        az = float(v["soleil_azimut_modele_deg"])
        ciel = dossier / f"ciel_{nom}.exr"
        ciel_fond = dossier / f"ciel_fond_{nom}.exr"
        if route_seule:
            CI.ciel_exr(ciel, el, az, turb, part, soleil, nuages=0.0, voile=0.92, teinte_voile=VOILE_ROUTE_SEULE)
            e_tot = soleil * math.sin(math.radians(el)) * (1.0 + part)
            l_sol = [c * e_tot / math.pi / CIEL_FOND * t for c, t in zip(SOL_NEUTRE, (0.985, 0.965, 0.93))]
            CI.ciel_exr(ciel_fond, el, az, turb, part, soleil, nuages=0.0, sol_radiance=l_sol, voile=0.92,
                        teinte_voile=VOILE_ROUTE_SEULE)
        else:
            CI.ciel_exr(ciel, el, az, turb, part, soleil)
        usd = dossier / f"vue_{nom}.usda"
        couche(usd, job["scene_usda"], "cmp_" + nom, v["camera"], el, az, ciel, ciel_fond, route_seule)
        exr = dossier / "_exr" / f"{nom}.exr"
        exr.parent.mkdir(parents=True, exist_ok=True)
        W, H = v["camera"]["resolution"]
        cmd = [husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/reglages", "--camera",
               f"/Cameras/cmp_{nom}", "--res", str(W), str(H), "--frame", "1", "-p",
               str(job.get("echantillons", ECHANTILLONS)), "--output", exr.as_posix(), "--make-output-path",
               "--timelimit", str(job.get("limite_s", 240)), "--verbose", "1", usd.as_posix()]
        env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
        r = None
        for essai in range(3):
            if exr.exists():
                exr.unlink()
            r = subprocess.run(cmd, env=env, cwd=str(dossier), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=int(job.get("limite_s", 240)) + 300)
            if r.returncode == 0 and exr.exists():
                break
            time.sleep(5)
        if r.returncode != 0 or not exr.exists():
            resultats.append({"nom": nom, "erreur": f"husk code {r.returncode} : {r.stdout[-800:]} {r.stderr[-800:]}"})
            continue
        expo = math.pi / (soleil * math.sin(math.radians(el)) * (1.0 + part)) * EXPO_GAIN
        png = Path(v["sortie_png"])
        png.parent.mkdir(parents=True, exist_ok=True)
        developper(exr, png, expo, contraste)
        exr.unlink()
        resultats.append({"nom": nom, "png": str(png), "usd": str(usd), "duree_s": round(time.time() - t0, 1),
                          "exposition": round(expo, 5), "soleil_rendu": [round(el, 2), round(az, 2)],
                          "contraste": contraste, "route_seule": route_seule})
        print("rendu", nom, round(time.time() - t0, 1), "s", flush=True)
    d_exr = dossier / "_exr"                 # dossier créé par ce script : seuls ses EXR sont effacés, puis lui s'il est vide
    if d_exr.is_dir():
        for f in d_exr.glob("*.exr"):
            f.unlink()
        try:
            d_exr.rmdir()
        except OSError:
            pass
    Path(job["resultat"]).write_text(json.dumps(resultats, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
