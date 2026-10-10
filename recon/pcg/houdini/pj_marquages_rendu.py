"""Rendus Karma XPU de contrôle des marquages v2 (hython Houdini 22 : husk + OpenImageIO).

    hython recon/pcg/houdini/pj_marquages_rendu.py                    # 4 caméras v1 + 4 vues -> recon/pc/rendus/v2_marquages
    hython recon/pcg/houdini/pj_marquages_rendu.py --vues t_dessus_centre --sur 1

Scènes (écrites dans fabrique/, chemins relatifs) :
- marquages_rendu_v1.usda : marquages.usda + couches v2 de la zone pilote (sol, bordures, îlots, détails,
  matériaux, masque v1) + recon/pc/houdini/rendu_controle.usda (paquet v1, 4 caméras v1, lumière et réglages
  des rendus v1) ; couche v1 /World/Marquages DÉSACTIVÉE. Rendue par recon/pc/houdini/rendre_controle.py (mêmes
  réglages que recon/pc/rendus/v1 : comparaison directe) ;
- marquages_rendu.usda : mêmes couches + décor de rendu + caméras rapprochées marquages_cameras.usda, lumière
  de la zone pilote (pj_rendu.ecrire_racine : soleil 220° / 29°, ciel clair) ; développement de
  rendre_pilote.py (exposition, épaule, balance des blancs).
Caméras rapprochées (placées depuis la description, z = sol fabriqué sous l'œil et la cible) :
- a_fleche_td_tad : conducteur (œil 1,30 m), flèche TD+TAD MF-0399 (Vercors, neuve 2025) à ~8 m devant ;
- b_zebra_verdun_sw : piéton (1,60 m) sur le refuge, regard le long du nouveau zébra de Verdun SW (MP-0863) ;
- c_traversee_cyclable : piéton (1,60 m) au bord de la traversée cyclable de Verdun SW (MP-0616 : carrés,
  pavés Chronovélo, chevrons) ;
- t_dessus_centre : vue de dessus quasi orthographique du centre (60 m de haut, champ de 40°) ;
- p_<photo> : pose d'une photo Panoramax antérieure aux travaux (marques conservées), planche photo / rendu.
Planches v1 | v2 des 4 caméras v1 : planche_<caméra>.png ; photo / rendu : planche_p_<photo>.png.
"""
import argparse
import math
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
from pxr import Gf, Sdf, Usd, UsdGeom                         # noqa: E402

import pj_commun as K                                         # noqa: E402
import pj_rendu as RD                                         # noqa: E402

RENDUS = K.RACINE / "recon/pc/rendus"
EV_CONTROLE = -0.4                # vues rapprochées : blanc neuf hors de l'épaule du développement (revue réalisme du 10/10)
DOSSIER = RENDUS / "v2_marquages"
CONTROLE = K.PC_HOUDINI / "rendu_controle.usda"
CAMERAS_V1 = ["cam1_ensemble_sud", "cam2_conducteur_verdun_so", "cam3_pieton_traversee_so", "cam4_conducteur_vercors"]
COUCHES_V2 = ["ilots_couverture.usdc", "ilots.usda", "decals_sol.usda", "bordures.usda", "sol.usda", "materiaux_v2.usda",
              "contexte/masque_v1_pilote.usdc"]
APERTURE = RD.APERTURE
PANORAMAX = K.RACINE / "data/raw/panoramax/paquet_jardin"
# photos de comparaison (marques existant avant les travaux) : pose GPS (repère local), hauteur d'œil estimée (photo
# prise d'une voiture), tangage lu sur l'horizon, champ horizontal des métadonnées ; rendu carré recadré au format
PHOTOS = {"20d1a815": {"fichier": "2025-08-31_20d1a815-ee8d-4d99-97c4-8e70270f289d_hd.jpg", "xy_gps": (50.7, 57.1),
                       "recale_sur": ("MF-0462", 5.0, 0.6), "azimut_deg": 232.0, "h": 1.30, "tangage_deg": 1.5,
                       "hfov": 72.0, "format": 4032 / 1814,
                       "doc": "2025-08-31, Verdun NE entrant vers le SO : flèches TD+TAD MF-0462 et TD+TAG MF-0463, lignes "
                              "de voie, marques conservées par les travaux"}}


def regard(oeil, cible, haut=(0, 0, 1)):
    m = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*map(float, oeil)), Gf.Vec3d(*map(float, cible)), Gf.Vec3d(*map(float, haut)))
    return m.GetInverse()


def _desc():
    import pj_marquages as PM
    d = K.lire_json(K.DESCRIPTION / "base/marquages.geojson")
    return {f["properties"]["id"]: f for f in d["features"]}, PM


def vues(fabrique):
    """[(nom, œil, cible, hfov, f, ev, haut, doc)] calculées depuis la description et le sol fabriqué."""
    ents, PM = _desc()
    sol = PM.Sol(fabrique, log=lambda *a: None)

    def z(xy):
        v, _ = sol.z_sous(np.atleast_2d(xy))
        return float(v[0]) if np.isfinite(v[0]) else 0.0
    loc = lambda c: K.repere(np.asarray(c, float)[..., :2])
    out = []
    # a : flèche TD+TAD MF-0399, conducteur 8 m avant le milieu de la flèche, 0,4 m à gauche de l'axe de voie
    p = ents["MF-0399"]["properties"]
    o = loc(np.array(p["pose"]["point_l93"])[None])[0]
    d = PM.dir_cap(p["pose"]["cap_deg"])
    g = np.array([-d[1], d[0]])
    oe = o - d * 6.0 + g * 0.4
    ci = o + d * 2.0
    out.append(("a_fleche_td_tad", np.r_[oe, z(oe) + 1.30], np.r_[ci, z(ci)], 55.0, 0.0, EV_CONTROLE, (0, 0, 1),
                "conducteur (œil 1,30 m, 0,4 m à gauche de l'axe de voie) à 8 m du milieu de la flèche TD+TAD MF-0399 "
                "(Vercors, neuve 2025, gabarit IISR B.3)"))
    # b : zébra MP-0863 (Verdun SW, neuf 2025) depuis le refuge, regard le long de l'axe
    p = ents["MP-0863"]
    A, B = loc(p["geometry"]["coordinates"])[:2]
    p2 = ents["MP-0869"]
    A2, B2 = loc(p2["geometry"]["coordinates"])[:2]
    # refuge : entre les deux zébras (extrémités les plus proches)
    paires = [(np.hypot(*(a - b)), a, b) for a in (A, B) for b in (A2, B2)]
    _, e1, e2 = min(paires, key=lambda t: t[0])
    refuge = 0.5 * (e1 + e2)
    loin = B if np.allclose(e1, A) else A
    ax = (loin - refuge) / np.hypot(*(loin - refuge))
    oe = refuge - ax * 0.6
    ci = refuge + ax * 4.5
    out.append(("b_zebra_verdun_sw", np.r_[oe, z(oe) + 1.60], np.r_[ci, z(ci)], 60.0, 0.0, EV_CONTROLE, (0, 0, 1),
                "piéton (œil 1,60 m) sur le refuge de Verdun SW, regard le long du nouveau zébra MP-0863 (bandes 0,50 au pas "
                "mesuré, neuf 2025) vers le trottoir NO"))
    # c : traversée cyclable MP-0616 (carrés, pavés Chronovélo, chevrons), vue de côté depuis le milieu des files
    p = ents["MP-0616"]["properties"]
    axes = [loc(f["axe_l93"]) for f in p["files"]]
    pts = np.vstack(axes)
    c = pts.mean(axis=0)
    w, V = np.linalg.eigh(np.cov((pts - c).T))
    u = V[:, int(np.argmax(w))]
    n = np.array([-u[1], u[0]])
    ext = (pts - c) @ u
    oe = c + u * (ext.min() - 1.2) + n * 0.6
    ci = c + u * (ext.min() + 3.5)
    out.append(("c_traversee_cyclable", np.r_[oe, z(oe) + 1.60], np.r_[ci, z(ci)], 65.0, 0.0, EV_CONTROLE, (0, 0, 1),
                "piéton (œil 1,60 m) à l'entrée de la traversée cyclable de Verdun SW MP-0616, regard le long des files : "
                "carrés 0,50, pavés Chronovélo jaunes 0,70 x 0,37 au pas 0,60, figurines et chevrons"))
    # t : vue de dessus du centre
    cc = np.array([-1.569, -5.089])
    zc = z(cc)
    out.append(("t_dessus_centre", np.r_[cc, zc + 60.0], np.r_[cc, zc], 40.0, 0.0, EV_CONTROLE, (0, 1, 0),
                "vue de dessus quasi orthographique du centre du carrefour (60 m de haut, champ de 40°, nord en haut)"))
    # p : pose de la photo Panoramax e96ea4be (2025-08-31, Verdun NE vers le SO, zébra NE conservé au premier plan)
    for pid, ph in sorted(PHOTOS.items()):
        az = math.radians(ph["azimut_deg"])
        dv = np.array([math.sin(az), math.cos(az)])
        # recalage à vue (GPS du téléphone à ±10 m) : œil à `recul` m derrière l'origine de la flèche de référence,
        # `gauche` m à gauche de l'axe de la voie (place du conducteur)
        ref, recul, gauche = ph["recale_sur"]
        pf = ents[ref]["properties"]
        of = loc(np.array(pf["pose"]["point_l93"])[None])[0]
        df = PM.dir_cap(pf["pose"]["cap_deg"])
        oe = of - df * recul + np.array([-df[1], df[0]]) * gauche
        zo = z(oe) + ph["h"]
        ci = np.r_[oe + dv * 20.0, zo + 20.0 * math.tan(math.radians(ph["tangage_deg"]))]
        out.append((f"p_{pid}", np.r_[oe, zo], ci, ph["hfov"], 0.0, EV_CONTROLE, (0, 0, 1),
                    f"pose de la photo Panoramax {ph['fichier']} ({ph['doc']}) : œil {ph['h']} m, azimut {ph['azimut_deg']}°, "
                    f"tangage {ph['tangage_deg']}°, champ {ph['hfov']}° ; pose GPS {ph['xy_gps']} recalée à vue sur "
                    f"{ref} ({recul} m derrière, {gauche} m à gauche de l'axe de voie)"))
    return out


def ecrire_cameras(chemin, vs):
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    st.GetRootLayer().documentation = (
        "Caméras rapprochées de contrôle des marquages v2 (pj_marquages_rendu.py) : repère local, m, Z haut ; ouverture "
        "36 x 36 mm notée 0,36 (dixièmes d'unité) ; rendus carrés.")
    w = st.OverridePrim("/World")
    st.SetDefaultPrim(w)
    UsdGeom.Scope.Define(st, "/World/Cameras_marquages")
    for nom, oeil, cible, hfov, f, ev, haut, doc in vs:
        cam = UsdGeom.Camera.Define(st, f"/World/Cameras_marquages/{nom}")
        cam.CreateFocalLengthAttr(round(APERTURE / (2 * math.tan(math.radians(hfov) / 2)), 6))
        cam.CreateHorizontalApertureAttr(APERTURE)
        cam.CreateVerticalApertureAttr(APERTURE)
        cam.CreateClippingRangeAttr(Gf.Vec2f(0.02, 3000))
        cam.CreateFStopAttr(float(f))
        cam.CreateFocusDistanceAttr(float(np.linalg.norm(cible - oeil)))
        cam.CreateProjectionAttr("perspective")
        UsdGeom.Xformable(cam).AddTransformOp().Set(regard(oeil, cible, haut))
        prim = cam.GetPrim()
        prim.SetDocumentation(doc)
        prim.SetCustomDataByKey("oeil_local_m", Gf.Vec3d(*map(float, np.round(oeil, 3))))
        prim.SetCustomDataByKey("cible_locale_m", Gf.Vec3d(*map(float, np.round(cible, 3))))
        prim.SetCustomDataByKey("hfov_deg", float(hfov))
        prim.SetCustomDataByKey("exposition_ev", float(ev))
    if chemin.exists():
        chemin.unlink()
    st.GetRootLayer().Export(str(chemin))


def _desactiver_v1(chemin):
    lay = Sdf.Layer.FindOrOpen(str(chemin))
    w = lay.GetPrimAtPath("/World") or Sdf.PrimSpec(lay.pseudoRoot, "World", Sdf.SpecifierOver)
    m = Sdf.PrimSpec(w, "Marquages", Sdf.SpecifierOver)
    m.active = False
    m.SetInfo("documentation", "marquages v1 (raster vectorisé) désactivés : remplacés par marquages.usda (v2)")
    lay.Save()


def ecrire_scenes(fabrique=K.FABRIQUE):
    fabrique = Path(fabrique)
    cams = fabrique / "marquages_cameras.usda"
    ecrire_cameras(cams, vues(fabrique))
    couches = [fabrique / "marquages.usda"] + [fabrique / c for c in COUCHES_V2]
    # v1 : réglages et lumière des rendus v1
    r1 = fabrique / "marquages_rendu_v1.usda"
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    lay = st.GetRootLayer()
    lay.documentation = ("Contrôle des marquages v2 aux 4 caméras v1 (pj_marquages_rendu.py) : marquages.usda + couches v2 "
                         "de la zone pilote + scène de contrôle v1 (paquet v1, caméras, lumière et réglages des rendus v1) ; "
                         "marquages v1 désactivés.")
    for c in couches + [CONTROLE]:
        lay.subLayerPaths.append(os.path.relpath(c, fabrique).replace("\\", "/"))
    st.SetDefaultPrim(st.OverridePrim("/World"))
    st.SetMetadata("renderSettingsPrimPath", "/Render/rendersettings")
    if r1.exists():
        r1.unlink()
    lay.Export(str(r1))
    _desactiver_v1(r1)
    # vues rapprochées : lumière de la zone pilote
    r2 = fabrique / "marquages_rendu.usda"
    RD.ecrire_racine(r2, cams, couches + [fabrique / "contexte/decor_rendu.usda"], CONTROLE, ref=r2,
                     ciel=fabrique / "ciel/ciel_clair.hdr")
    l2 = Sdf.Layer.FindOrOpen(str(r2))
    l2.documentation = ("Contrôle rapproché des marquages v2 (pj_marquages_rendu.py) : caméras marquages_cameras.usda, "
                        "marquages.usda + couches v2 de la zone pilote + décor + scène de contrôle v1 ; lumière de la zone "
                        "pilote (soleil 220° / 29°, ciel clair) ; marquages v1 désactivés.")
    l2.Save()
    _desactiver_v1(r2)
    return r1, r2


def husk():
    h = Path(sys.executable).parent / "husk.exe"
    return str(h) if h.exists() else "husk"


def rendre_vues(r2, noms, dossier, res=1000, sur=2, limite=900):
    import rendre_pilote as RP
    tmp = Path(tempfile.mkdtemp(prefix="pj_marquages_"))
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    lay = Usd.Stage.Open(str(r2))
    echecs = []
    try:
        for nom in noms:
            exr = tmp / f"{nom}.exr"
            r = res * sur
            cmd = [husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/rendersettings",
                   "--camera", f"/World/Cameras_marquages/{nom}", "--res", str(r), str(r), "--frame", "1",
                   "--output", exr.as_posix(), "--make-output-path", "--timelimit", str(limite), "--verbose", "1",
                   Path(r2).as_posix()]
            t = time.time()
            p = subprocess.run(cmd, env=env, cwd=str(Path(r2).parent), capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if p.returncode != 0 or not exr.exists():
                print(p.stdout[-2000:], p.stderr[-2000:])
                echecs.append(nom)
                continue
            cam = lay.GetPrimAtPath(f"/World/Cameras_marquages/{nom}")
            ev = RP.EXPOSITION_EV + float(cam.GetCustomDataByKey("exposition_ev") or 0.0)
            RP.developper(exr, Path(dossier) / f"{nom}.png", ev, res, RD.gains_balance())
            print(f"   {nom} : {time.time() - t:.0f} s -> {Path(dossier) / (nom + '.png')}", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for rat in sorted((Path(r2).parent / "ciel").glob("*.rat")):
            rat.unlink()
    return echecs


def rendre_v1(r1, cams, dossier, res=1000):
    cmd = [sys.executable, str(K.PC_HOUDINI / "rendre_controle.py"), "v2_marquages", "--usd", str(r1),
           "--dossier", str(dossier), "--cameras", ",".join(cams), "--res", str(res)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(p.stdout[-1500:], p.stderr[-1500:])
    return p.returncode


def planches(cams, dossier):
    """planche_<caméra>.png : rendu v1 (recon/pc/rendus/v1) | rendu v2 marquages, 1000 px de haut chacun."""
    for c in cams:
        a, b = RENDUS / "v1" / f"{c}.png", Path(dossier) / f"{c}.png"
        if not (a.exists() and b.exists()):
            continue
        A, B = oiio.ImageBuf(str(a)), oiio.ImageBuf(str(b))
        h = 1000
        A = oiio.ImageBufAlgo.resize(A, roi=oiio.ROI(0, h, 0, h, 0, 1, 0, 3))
        B = oiio.ImageBufAlgo.resize(B, roi=oiio.ROI(0, h, 0, h, 0, 1, 0, 3))
        out = oiio.ImageBuf(oiio.ImageSpec(2 * h + 10, h, 3, oiio.UINT8))
        oiio.ImageBufAlgo.fill(out, (1.0, 1.0, 1.0))
        oiio.ImageBufAlgo.paste(out, 0, 0, 0, 0, A)
        oiio.ImageBufAlgo.paste(out, h + 10, 0, 0, 0, B)
        out.write(str(Path(dossier) / f"planche_{c}.png"))


def planches_photos(dossier):
    """planche_p_<photo>.png : photo Panoramax (en haut) / rendu recadré au même format (en bas), 1400 px de large."""
    for pid, ph in sorted(PHOTOS.items()):
        r = Path(dossier) / f"p_{pid}.png"
        f = PANORAMAX / ph["fichier"]
        if not (r.exists() and f.exists()):
            continue
        W = 1400
        H = int(round(W / ph["format"]))
        A = oiio.ImageBufAlgo.resize(oiio.ImageBuf(str(f)), roi=oiio.ROI(0, W, 0, H, 0, 1, 0, 3))
        B = oiio.ImageBuf(str(r))
        n = B.spec().width
        hb = int(round(n / ph["format"]))
        B = oiio.ImageBufAlgo.cut(B, oiio.ROI(0, n, (n - hb) // 2, (n - hb) // 2 + hb))
        B = oiio.ImageBufAlgo.resize(B, roi=oiio.ROI(0, W, 0, H, 0, 1, 0, 3))
        out = oiio.ImageBuf(oiio.ImageSpec(W, 2 * H + 10, 3, oiio.UINT8))
        oiio.ImageBufAlgo.fill(out, (1.0, 1.0, 1.0))
        oiio.ImageBufAlgo.paste(out, 0, 0, 0, 0, A)
        oiio.ImageBufAlgo.paste(out, 0, H + 10, 0, 0, B)
        out.write(str(Path(dossier) / f"planche_p_{pid}.png"))


def main():
    ap = argparse.ArgumentParser(description="Rendus Karma de contrôle des marquages v2")
    ap.add_argument("--fabrique", default=str(K.FABRIQUE))
    ap.add_argument("--dossier", default=str(DOSSIER))
    ap.add_argument("--vues", default="a_fleche_td_tad,b_zebra_verdun_sw,c_traversee_cyclable,t_dessus_centre,"
                                      + ",".join(f"p_{k}" for k in sorted(PHOTOS)))
    ap.add_argument("--cameras-v1", default=",".join(CAMERAS_V1), help="caméras v1 (vide : aucune)")
    ap.add_argument("--res", type=int, default=1000)
    ap.add_argument("--sur", type=int, default=2)
    ap.add_argument("--scenes-seules", action="store_true")
    a = ap.parse_args()
    dossier = Path(a.dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    r1, r2 = ecrire_scenes(a.fabrique)
    if a.scenes_seules:
        return
    cams = [c for c in a.cameras_v1.split(",") if c]
    if cams:
        rendre_v1(r1, cams, dossier, a.res)
        planches(cams, dossier)
    noms = [v for v in a.vues.split(",") if v]
    if noms:
        e = rendre_vues(r2, noms, dossier, a.res, a.sur)
        planches_photos(dossier)
        if e:
            sys.exit(f"rendus en échec : {', '.join(e)}")


if __name__ == "__main__":
    main()
