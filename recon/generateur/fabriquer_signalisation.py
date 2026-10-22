"""Pilote du lot L6 (étape E14 : signalisation verticale et feux) ; hython Houdini 22.

    hython recon/generateur/fabriquer_signalisation.py SCENE [SCENE ...] [--construire-hda] [--fabriquer]
                                                       [--rendus] [--sortie DOSSIER] [--verifier-determinisme]

SCENE : une description .yaml (scenes_*/…) ou un dossier de scène déjà fabriquée (recon/out/generateur/<scene>).
Chaîne : (1) la scène est fabriquée par fabriquer_generateur.py --complet si ses sorties manquent (ou --fabriquer) ;
(2) plan de signalisation (hda/rg_signalisation/plan_signalisation.py, Python hors Houdini) et faces composées
(faces_composees.py) ; (3) rg::signalisation sur le sol fabriqué (l2/sol_*.npy), les références (l1) et les dispositifs
de retenue (autoroute/) ; (4) exports : l6/ensembles.json, l6/instances.json, l6/points/signalisation.json et
l6/points/feux.json (pj_points/0.1), l6/signalisation.usda (références aux assets route_fr, plaques composées
texturées, lentilles des feux allumées selon la première phase du contrôleur), l6/mesures_l6.json, manifest_l6.json ;
(5) rendus (--rendus) : la scène de rendu de la chaîne (rendus/scene_rendu.usda) en sous-couche + la signalisation,
3 vues (dessus, oblique 3/4, conducteur à 1,20 m face aux panneaux), planche ≤ 1092 px, tuiles natives.

Aucune date ni durée dans les sorties (sauf manifeste des rendus) ; HOUDINI_VEX_DISABLE_JIT=1 ; temporaires sur D:.
Les sorties de la chaîne (l1/ … l5/, rendus/) sont lues, jamais modifiées.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent                 # recon/generateur
DEPOT = ICI.parents[1]
TMP = ICI / "tmp" / "hython"
SORTIE_DEFAUT = DEPOT / "recon" / "out" / "generateur"
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")

if os.environ.get("RG_PILOTE_ENV") != "1":
    TMP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, RG_PILOTE_ENV="1", PYTHONDONTWRITEBYTECODE="1", TEMP=str(TMP), TMP=str(TMP),
               HOUDINI_TEMP_DIR=str(TMP).replace("\\", "/"), HOUDINI_VEX_DISABLE_JIT="1")
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=env))

import tempfile  # noqa: E402

tempfile.tempdir = str(TMP)
import hou  # noqa: E402

for p in (ICI, ICI / "hda" / "commun", ICI / "hda" / "rg_signalisation", ICI / "rendu"):
    sys.path.insert(0, str(p))
import rg_hda_outils as R  # noqa: E402
import plan_signalisation as PS  # noqa: E402
import faces_composees as FCO  # noqa: E402

VERSION = "fabriquer_signalisation/1.0 (lot L6)"
LIB = DEPOT / "assets" / "lib" / "route_fr"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(DEPOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _ecrire(f, d):
    Path(f).parent.mkdir(parents=True, exist_ok=True)
    Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _r(x, n=4):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


# ------------------------------------------------------------------------------------------- HDA
def construire_hda(forcer=False):
    d = ICI / "hda" / "rg_signalisation"
    cible = d / "rg_signalisation.hdalc"
    if forcer or not cible.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("construire_rg_signalisation", d / "construire.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cible = mod.construire(d)
    else:
        hou.hda.installFile(str(cible))
    return {f"rg::signalisation::{R.VERSION}": R.signature(cible)}


# ------------------------------------------------------------------------------------------- base
def scene_de(entree):
    e = Path(entree)
    if e.is_dir():
        return e.name, None
    sys.path.insert(0, str(ICI / "description"))
    import yaml_simple as Y
    d = Y.lire(e) or {}
    return str(d.get("scene") or e.stem), e


def fabriquer_base(yaml, sortie):
    """Chaîne de l'étape 2 (fabriquer_generateur.py --complet) dans un processus séparé : sol, bordures, marquages,
    carrefours, giratoires, autoroutes et rendus de base (scene_rendu.usda)."""
    env = {k: v for k, v in os.environ.items() if k not in ("RG_PILOTE_ENV",)}
    r = subprocess.run([sys.executable, str(ICI / "fabriquer_generateur.py"), str(yaml), "--complet", "--sortie",
                        str(sortie)], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"{yaml} : fabrication de base en échec\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


# ------------------------------------------------------------------------------------------- réseau Houdini
def reseau(dossier, plan_json):
    obj = hou.node("/obj/signalisation_l6") or hou.node("/obj").createNode("geo", "signalisation_l6")
    for c in obj.children():
        c.destroy()
    dossier = str(Path(dossier).resolve()).replace("\\", "/")
    lect = {}
    for nom, fn in (("lire_sol", "lire_sol"), ("lire_references", "lire_references"), ("lire_obstacles", "lire_obstacles")):
        py = obj.createNode("python", nom)
        py.parm("python").set(f"import lecteurs_scene as L\nL.{fn}(hou.pwd(), r'{dossier}')\n")
        lect[nom] = py
    sig = obj.createNode(R.nom_type("signalisation"), "signalisation")
    sig.setInput(0, lect["lire_sol"])
    sig.setInput(1, lect["lire_references"])
    sig.setInput(2, lect["lire_obstacles"])
    sig.parm("fichier").set(str(plan_json).replace("\\", "/"))
    sig.setDisplayFlag(True)
    obj.layoutChildren()
    return sig


def cuire(n, scene):
    try:
        n.cook(force=True)
    except hou.OperationFailed:
        pass
    err = [f"{c.path()} : {e}" for c in (n,) + n.allSubChildren() for e in c.errors()]
    if err:
        raise SystemExit(f"{scene} : erreurs de cuisson\n" + "\n".join(err[:20]))


def _val(p, nom):
    v = p.attribValue(nom)
    if isinstance(v, float):
        return _r(v, 4)
    if isinstance(v, tuple):
        return [_r(x, 5) for x in v]
    return v


ATTR_ENS = ("id", "famille", "source", "statut", "motif", "cas_arb20", "classe_sol", "d_rive_axe", "bord_rive",
            "w_cote_rive", "w_cote_facade", "cheminement_libre", "surplomb_ok", "ds", "dt", "ecart_q", "z_sol", "bas",
            "bas_reel", "haut_m", "hauteur_support", "lacet_usd", "face_dir", "trafic_dir", "n_r11", "bas_feu",
            "axe_feu_sup", "rural", "regle_hauteur", "exclusif", "support_type", "support_r", "double", "route", "s",
            "sens", "cote", "anc_type", "surface", "regles", "l_max", "q")
ATTR_INS = ("ensemble", "code", "kind", "asset", "gamme", "face", "signal", "largeur", "hauteur", "lacet_usd", "echelle",
            "face_dir", "bas_m", "haut_m")


def _usd(p):
    """Houdini (x, y, z) -> local Z haut (x, −z, y)."""
    return [_r(p[0], 4), _r(-p[2], 4), _r(p[1], 4)]


def extraire(sig):
    g_ens, g_ins = sig.geometry(0), sig.geometry(1)
    ens = []
    for p in g_ens.points():
        d = {k: _val(p, k) for k in ATTR_ENS if g_ens.findPointAttrib(k)}
        d["p"] = _usd(p.position())
        for k in ("face_dir", "trafic_dir", "q"):
            if k in d:
                d[k] = _usd(d[k])
        ens.append(d)
    ins = []
    for p in g_ins.points():
        d = {k: _val(p, k) for k in ATTR_INS if g_ins.findPointAttrib(k)}
        d["p"] = _usd(p.position())
        d["face_dir"] = _usd(d["face_dir"])
        ins.append(d)
    ens.sort(key=lambda e: e["id"])
    ins.sort(key=lambda x: (x["ensemble"], x["kind"] != "support", x["code"], x["p"]))
    det = {a.name(): g_ens.attribValue(a.name()) for a in g_ens.globalAttribs() if a.name().startswith("rg_l6")}
    return ens, ins, det


# ------------------------------------------------------------------------------------------- exports
def points_pj(ins, famille, plan):
    pts = []
    for k, x in enumerate(ins):
        if not x["asset"] and x["kind"] != "plaque_composee":
            continue
        pts.append({"id": f"{x['ensemble']}/{k:03d}", "asset": x["asset"] or f"plaque_composee:{x['face']}",
                    "p": x["p"], "rpy_deg": [0.0, 0.0, _r(x["lacet_usd"], 3)], "s": [_r(v, 4) for v in x["echelle"]],
                    "graine": int(hashlib.sha256(f"{x['ensemble']}/{k}".encode()).hexdigest()[:8], 16) % 2147483647,
                    "cd": [], "x": {"ensemble": x["ensemble"], "code": x["code"], "kind": x["kind"], "gamme": x["gamme"],
                                    "face": x["face"], "signal": x.get("signal", ""), "bas_m": x["bas_m"],
                                    "haut_m": x["haut_m"]}})
    return {"schema": "pj_points/0.1", "famille": famille, "source_hash": plan["modele"]["sha256"],
            "repere": "local (L93 − origine de la scène), m, Z haut",
            "convention_rpy": "rpy_deg = [r, p, y] ZYX intrinsèques ; y = lacet trigonométrique depuis +x (face des "
                              "plaques et optiques des feux vers +Y de l'asset)",
            "pivot": "assets route_fr : panneaux au milieu du bord inférieur de la plaque principale ; supports au pied ; "
                     "feux au bas du boîtier",
            "cd": "aucun", "bibliotheque": "asset = identifiant du catalogue route_fr (assets/specs/route/"
                                           "catalogue_assets_route.json) ; plaque_composee:<face> = plaque de la scène",
            "points": pts}


def ecrire_usd(dl6, ins, g_plaques, plan, scene):
    """l6/signalisation.usda : instances (références aux assets du catalogue, variante de gamme ou LOD0), plaques
    composées (maillages, faces texturées), lentilles des feux allumées selon la première phase du contrôleur."""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    import rendre_l2 as RL
    cat = PS.catalogue()
    f = Path(dl6) / "signalisation.usda"
    if f.exists():
        f.unlink()
    st = Usd.Stage.CreateNew(str(f))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    racine = UsdGeom.Xform.Define(st, "/Signalisation")
    st.SetDefaultPrim(racine.GetPrim())
    UsdGeom.Scope.Define(st, "/Signalisation/Looks")
    etats = {}
    m = json.loads((Path(dl6).parent / "modele_voie.json").read_text(encoding="utf-8"))
    for c in m.get("controleurs") or []:
        if c.get("phases"):
            etats.update(c["phases"][0].get("etats") or {})
    noms = {}
    for k, x in enumerate(ins):
        if x["kind"] == "plaque_composee" or not x["asset"]:
            continue
        a = cat.get(x["asset"])
        if a is None:
            raise SystemExit(f"{scene} : asset {x['asset']} absent du catalogue")
        base = "".join(c if c.isalnum() else "_" for c in x["ensemble"])
        n = noms.get(base, 0)
        noms[base] = n + 1
        chemin = f"/Signalisation/Instances/{base}/i{n:02d}_{''.join(c if c.isalnum() else '_' for c in x['code'])}"
        xf = UsdGeom.Xform.Define(st, chemin)
        xf.AddTranslateOp().Set(Gf.Vec3d(*x["p"]))
        xf.AddRotateZOp().Set(float(x["lacet_usd"]))
        xf.AddScaleOp().Set(Gf.Vec3f(*[float(v) for v in x["echelle"]]))
        cible = LIB / a["fichiers"]["usd"]
        xf.GetPrim().GetReferences().AddReference(os.path.relpath(cible, dl6).replace("\\", "/"))
        vs = xf.GetPrim().GetVariantSets()
        if x["gamme"] and "gamme" in vs.GetNames():
            vs.GetVariantSet("gamme").SetVariantSelection(x["gamme"])
        elif "LOD" in vs.GetNames():
            vs.GetVariantSet("LOD").SetVariantSelection("LOD0")
        # lentilles allumées (première phase du contrôleur ; répétiteur = son R11) : émission du catalogue (customData)
        etat = etats.get(x.get("signal") or "")
        if x["kind"] == "feu" and etat in ("rouge", "vert", "jaune"):
            asset_usd = Usd.Stage.Open(str(cible))
            mat = asset_usd.GetPrimAtPath(f"/{a['id']}/Looks/feu_lentille_{etat}")
            em = (mat.GetCustomDataByKey("route") or {}).get("emission_allumee_lineaire") if mat else None
            if em is not None:
                sh = st.OverridePrim(f"{chemin}/Looks/feu_lentille_{etat}/Surface")
                sh.CreateAttribute("inputs:emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
                    Gf.Vec3f(*[float(v) * 6.0 for v in em]))
    # plaques composées
    if g_plaques is not None and len(g_plaques.prims()):
        donnees = RL.maillages(g_plaques, "plaques")
        liaisons = {}
        for mid in sorted(donnees):
            nom = "".join(c if c.isalnum() else "_" for c in mid)
            ch = f"/Signalisation/Looks/{nom}"
            mat = UsdShade.Material.Define(st, ch)
            sh = UsdShade.Shader.Define(st, ch + "/Surface")
            sh.CreateIdAttr("UsdPreviewSurface")
            sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.45)
            sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
            if mid.startswith("face:"):
                lec = UsdShade.Shader.Define(st, ch + "/LecteurUV")
                lec.CreateIdAttr("UsdPrimvarReader_float2")
                lec.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
                tex = UsdShade.Shader.Define(st, ch + "/Face")
                tex.CreateIdAttr("UsdUVTexture")
                tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(mid[5:]))
                tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
                tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
                tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
                tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(lec.ConnectableAPI(), "result")
                sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(), "rgb")
                sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(tex.ConnectableAPI(), "a")
                sh.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.5)
            else:
                sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.42, 0.43, 0.44))
                sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.35)
            mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
            liaisons[mid] = mat
        RL.ecrire_couche(st, "/Signalisation/Plaques", donnees, liaisons)
        for mid in donnees:
            UsdGeom.Mesh(st.GetPrimAtPath("/Signalisation/Plaques/" + "".join(c if c.isalnum() else "_" for c in mid))
                         ).CreateDoubleSidedAttr(True)
    st.GetRootLayer().Save()
    return f


# ------------------------------------------------------------------------------------------- mesures
def mesurer(ens, ins, plan):
    n = len(ens)
    st = {"ok": 0, "contrainte": 0, "echec": 0}
    for e in ens:
        st[e["statut"]] = st.get(e["statut"], 0) + 1
    return {"ensembles": n, "statuts": st, "instances": len(ins),
            "plaques": sum(1 for x in ins if x["kind"] in ("plaque", "plaque_composee")),
            "feux": sum(1 for x in ins if x["kind"] == "feu"),
            "supports": sum(1 for x in ins if x["kind"] == "support"),
            "exigences": len(plan["exigences"]), "non_poses": len(plan["non_poses"]),
            "faces_composees": len(plan["faces"]), "destinations_generiques": plan.get("destinations_generiques", 0)}


# ------------------------------------------------------------------------------------------- rendus
def _vec(a):
    return [float(v) for v in a]


def cible_conducteur(ens, plan, cpl):
    """Ensemble visé par la vue du conducteur : complément (vue_conducteur.ensemble), sinon le premier ensemble
    ancré sur une route par ordre de priorité (régimes, feux, puis le reste)."""
    vc = (cpl or {}).get("vue_conducteur") or {}
    par_id = {e["id"]: e for e in ens}
    if vc.get("ensemble") in par_id:
        return par_id[vc["ensemble"]], vc
    ordre = ["AB3a", "AB4", "R11v", "EB10", "D31d", "AB25", "B14", "C24b", "D42", "C20a", "B1", "C12", "A13b", "C27"]
    for code in ordre:
        for e in ens:
            pe = next((p for p in plan["ensembles"] if p["id"] == e["id"]), None)
            if pe and pe["ancrage"]["type"] == "route" and any(code in x["code"] for x in pe["elements"]) \
                    and e["statut"] != "echec":
                return e, vc
    return ens[0], vc


def oeil_voie(dsc, route, s, sens, cote="droite"):
    """Milieu de la voie la plus proche du panneau (voie de droite du sens visé, ou de gauche pour une répétition à
    gauche) en s, d'après les limites fabriquées (l1/courbes_controle.json) : (x, y, cap du trafic)."""
    c = json.loads((Path(dsc) / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    r = next(x for x in c["routes"] if x["id"] == route)
    ref = PS.Reference(r)
    s_demande = s
    s = min(max(s, ref.s[0] + 0.5), ref.s[-1] - 0.5)
    hors = s_demande - s                                 # œil au-delà du bout du tronçon : prolongement en ligne droite
    sec = next((x for x in r["sections"] if x["s0"] - 1e-6 <= s <= x["s1"] + 1e-6), r["sections"][-1])
    k = min(range(len(sec["s"])), key=lambda j: abs(sec["s"][j] - s))
    voies = []
    sens_txt = "avant" if sens > 0 else "arriere"
    lims = {l["indice"]: l for l in sec["limites"]}
    for b in sec["bandes"]:
        if str(b["type"]).startswith("voie") and b["sens"] == sens_txt:
            t0, t1 = lims[b["rang"]]["t"][k], lims[b["rang"] + 1]["t"][k]
            voies.append(0.5 * (t0 + t1))
    if not voies:
        tc = -1.5 * sens
    else:
        droite = min(voies) if sens > 0 else max(voies)
        gauche = max(voies) if sens > 0 else min(voies)
        tc = droite if cote != "gauche" else gauche
    p = ref.pt(s)
    tg = ref.tangente(s)
    p = (p[0] + tg[0] * hors, p[1] + tg[1] * hors)
    g = (-tg[1], tg[0])                                  # t positif à gauche de la référence
    return (p[0] + g[0] * tc, p[1] + g[1] * tc), (tg[0] * sens, tg[1] * sens)


def cameras(stage, ens, plan, cpl, base_man, dsc):
    import rendu_l2b as RB
    cams = {}
    e, vc = cible_conducteur(ens, plan, cpl)
    X = _vec(e["p"])
    T = _vec(e["trafic_dir"])
    n = math.hypot(T[0], T[1]) or 1.0
    T = [T[0] / n, T[1] / n]
    recul = float(vc.get("recul", 26.0))
    h = float(vc.get("hauteur", 1.20))
    pe = next(p for p in plan["ensembles"] if p["id"] == e["id"])
    a = pe["ancrage"]
    if a["type"] == "route":
        s_oeil = float(e.get("s") or a["s"]) + float(e.get("ds") or 0.0) - a["sens"] * recul
        (ox, oy), tr = oeil_voie(dsc, a["route"], s_oeil, a["sens"], a.get("cote", "droite"))
    else:
        ox, oy = X[0] - T[0] * recul, X[1] - T[1] * recul
    oeil = (ox, oy, float(e["z_sol"]) - 0.12 + h)
    cible = (X[0] * 0.85 + (ox + T[0] * recul) * 0.15, X[1] * 0.85 + (oy + T[1] * recul) * 0.15,
             float(e["z_sol"]) + 1.6)
    foc = float(vc.get("focale", 35.0))
    RB._camera(stage, "l6_conducteur", oeil, cible, foc, RB.RES)
    cams["l6_conducteur"] = {"oeil": [round(v, 3) for v in oeil], "cible": [round(v, 3) for v in cible],
                             "focale_mm": foc, "ensemble": e["id"], "res": list(RB.RES)}
    # oblique 3/4 : en arrière et du côté de la chaussée, en hauteur, vers l'ensemble visé
    vo = (cpl or {}).get("vue_oblique") or {}
    dist, haut = float(vo.get("distance", 22.0)), float(vo.get("hauteur", 10.0))
    dx, dy = X[0] - ox, X[1] - oy
    nn = math.hypot(dx, dy) or 1.0
    ux, uy = dx / nn, dy / nn
    lat = (-uy, ux)                                      # à gauche de la visée du conducteur
    oo = (X[0] - ux * dist * 0.85 + lat[0] * dist * 0.45, X[1] - uy * dist * 0.85 + lat[1] * dist * 0.45,
          float(e["z_sol"]) + haut)
    co = (X[0] + lat[0] * 2.0, X[1] + lat[1] * 2.0, float(e["z_sol"]) + 1.2)
    RB._camera(stage, "l6_oblique", oo, co, 26.0, RB.RES)
    cams["l6_oblique"] = {"oeil": [round(v, 3) for v in oo], "cible": [round(v, 3) for v in co], "focale_mm": 26.0,
                          "ensemble": e["id"], "res": list(RB.RES)}
    return cams


def rendre(dsc, ens, plan, cpl, scene, echantillons=96):
    """Rendu : scène de rendu de la chaîne (sous-couche, inchangée) + signalisation ; vues dessus (caméra de la chaîne),
    oblique 3/4 et conducteur ; planche ≤ 1092 px ; tuiles natives (decoupe.py)."""
    from pxr import Sdf, Usd, UsdGeom
    import rendu_l2b as RB
    import rendre_l2 as RL
    import planches as PL
    base = Path(dsc) / "rendus" / "scene_rendu.usda"
    if not base.exists():
        raise SystemExit(f"{scene} : rendus/scene_rendu.usda absent (lancer avec --fabriquer)")
    d = Path(dsc) / "l6" / "rendus"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    usd = d / "scene_l6.usda"
    if usd.exists():
        usd.unlink()
    st = Usd.Stage.CreateNew(str(usd))
    st.GetRootLayer().subLayerPaths.append("../../rendus/scene_rendu.usda")
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    sig = st.DefinePrim("/Signalisation", "Xform")
    sig.GetReferences().AddReference("../signalisation.usda")
    base_man = json.loads((Path(dsc) / "rendus" / "manifest_rendus.json").read_text(encoding="utf-8")) \
        if (Path(dsc) / "rendus" / "manifest_rendus.json").exists() else {}
    cams = cameras(st, ens, plan, cpl, base_man, dsc)
    st.GetRootLayer().Save()
    res = {"dessus": tuple(base_man.get("resolutions", {}).get("dessus", (1092, 1092))),
           "l6_oblique": RB.RES, "l6_conducteur": RB.RES}
    pngs = RB.rendre(usd, res, d, echantillons=echantillons)
    tu = {}
    for nom, png in pngs.items():
        m = RL.tuiles(png, d / "tuiles" / nom)
        tu[nom] = [x["fichier"] for x in m.get("tuiles", [])]
    leg = {"dessus": "dessus (signalisation posée)", "l6_oblique": "vue oblique 3/4",
           "l6_conducteur": f"conducteur (1,20 m) face à {cams['l6_conducteur']['ensemble']}"}
    planche = PL.planche_vues(scene, pngs, ["dessus", "l6_oblique", "l6_conducteur"], d / f"planche_l6_{scene}.png",
                              legendes=leg)
    RL.nettoyer_rat()
    man = {"schema": "rg_rendus_l6/0.1", "scene": scene, "moteur": "Karma XPU (husk)", "echantillons": echantillons,
           "base": rel(base), "cameras": cams, "images": {k: Path(v).name for k, v in pngs.items()}, "tuiles": tu,
           "planche": Path(planche).name if planche else None}
    _ecrire(d / "manifest_rendus_l6.json", man)
    return man


# ------------------------------------------------------------------------------------------- scène
def complement_de(scene):
    """Complément de description de la signalisation d'une scène (scenes_signalisation/complements/<scene>.yaml), ou
    None. Intégration de l'étape 4 : la chaîne complète (fabriquer_generateur.py --complet) pose la signalisation
    verticale et les feux de toute scène qui a un complément."""
    f = PS.COMPLEMENTS / f"{scene}.yaml"
    return f if f.exists() else None


def _corriger_z(ens, ins, g_plaques, dz):
    """Intégration de l'étape 4 (couches des scènes à ouvrages) : la signalisation d'une couche est posée sur le sol
    PLAT de la couche ; dz(x, y) (profil en long de la route portée, rg::ouvrages) la remonte avec la route déformée.
    Positions locales Z haut (ensembles, instances) et points des plaques composées (Houdini : x, z = −y)."""
    for e in ens:
        d = dz(e["p"][0], e["p"][1])
        if d:
            e["p"][2] = _r(e["p"][2] + d, 4)
            e["z_sol"] = _r(float(e.get("z_sol") or 0.0) + d, 4)
    for x in ins:
        d = dz(x["p"][0], x["p"][1])
        if d:
            x["p"][2] = _r(x["p"][2] + d, 4)
    if g_plaques is None:
        return None
    g = hou.Geometry()
    g.merge(g_plaques)
    for p in g.points():
        q = p.position()
        d = dz(q[0], -q[2])
        if d:
            p.setPosition(hou.Vector3(q[0], q[1] + d, q[2]))
    return g


def fabriquer_scene(entree, sortie, sig_hda, fabriquer=False, rendus=False, echantillons=96, complement=None,
                    correction_z=None):
    """Signalisation d'une scène fabriquée. complement : complément explicite (couches d'une scène à ouvrages : celui de
    la scène) ; correction_z : dz(x, y) appliqué aux positions exportées (signalisation d'une couche remontée par le
    profil en long de sa route portée). Sans ces deux arguments : comportement du lot L6, inchangé."""
    scene, yaml = scene_de(entree)
    dsc = Path(sortie) / scene if yaml is not None else Path(entree).resolve()
    if yaml is not None and (fabriquer or not (dsc / "l2" / "sol_points.npy").exists()
                             or (rendus and not (dsc / "rendus" / "scene_rendu.usda").exists())):
        print(f"{scene} : fabrication de la chaîne (fabriquer_generateur.py --complet)")
        fabriquer_base(yaml, sortie)
    dl6 = dsc / "l6"
    dl6.mkdir(parents=True, exist_ok=True)
    cpl_f = Path(complement) if complement else PS.COMPLEMENTS / f"{scene}.yaml"
    plan = PS.construire_plan(dsc, cpl_f if cpl_f.exists() else None)
    f_plan = dl6 / "plan_signalisation.json"
    _ecrire(f_plan, plan)
    faces = FCO.dessiner(plan["faces"], dl6)
    sig = reseau(dsc, f_plan)
    cuire(sig, scene)
    ens, ins, det = extraire(sig)
    g_plaques = sig.geometry(2)
    if correction_z is not None:
        g_plaques = _corriger_z(ens, ins, g_plaques, correction_z)
    _ecrire(dl6 / "ensembles.json", {"schema": "rg_signalisation_ensembles/0.1", "scene": scene, "ensembles": ens})
    _ecrire(dl6 / "instances.json", {"schema": "rg_signalisation_instances/0.1", "scene": scene, "instances": ins})
    feux = [x for x in ins if x["ensemble"] in {e["id"] for e in ens if e["famille"] == "feu"}]
    autres = [x for x in ins if x not in feux]
    _ecrire(dl6 / "points" / "signalisation.json", points_pj(autres, "signalisation", plan))
    _ecrire(dl6 / "points" / "feux.json", points_pj(feux, "feux", plan))
    f_usd = ecrire_usd(dl6, ins, g_plaques, plan, scene)
    mes = mesurer(ens, ins, plan)
    mes["detail_houdini"] = det
    _ecrire(dl6 / "mesures_l6.json", mes)
    cpl = {}
    if cpl_f.exists():
        sys.path.insert(0, str(ICI / "description"))
        import yaml_simple as Y
        cpl = Y.lire(cpl_f) or {}
    fichiers = {p.relative_to(dl6).as_posix(): sha256(p) for p in sorted(dl6.rglob("*"))
                if p.is_file() and "rendus" not in p.parts and p.name != "manifest_l6.json"}
    _ecrire(dl6 / "manifest_l6.json", {"schema": "rg_manifest_l6/0.1", "pilote": VERSION, "scene": scene,
                                       "entree": rel(entree), "houdini": hou.applicationVersionString(),
                                       "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1", "hda": sig_hda,
                                       "plan": {"fichier": rel(f_plan), "complement": plan.get("complement")},
                                       "mesures": mes, "fichiers": fichiers})
    print(f"{scene} : {mes['ensembles']} ensembles ({mes['statuts']}), {mes['plaques']} plaques, {mes['feux']} feux, "
          f"{mes['supports']} supports, {len(faces)} faces composées -> {rel(dl6)}")
    if rendus:
        man = rendre(dsc, ens, plan, cpl, scene, echantillons=echantillons)
        print(f"{scene} : rendus {list(man['images'])} -> {rel(dsc / 'l6' / 'rendus')}")
    fabriquer_scene.dernier = {"ensembles": ens, "plan": plan, "complement": cpl, "mesures": mes}
    return dsc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrees", nargs="*")
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    ap.add_argument("--construire-hda", action="store_true")
    ap.add_argument("--fabriquer", action="store_true", help="refabriquer la chaîne de base (fabriquer_generateur --complet)")
    ap.add_argument("--rendus", action="store_true")
    ap.add_argument("--echantillons", type=int, default=96)
    ap.add_argument("--verifier-determinisme", action="store_true")
    a = ap.parse_args()
    sig = construire_hda(forcer=a.construire_hda)
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in sig.items()))
    produits = []
    for e in a.entrees:
        produits.append(fabriquer_scene(e, a.sortie, sig, fabriquer=a.fabriquer, rendus=a.rendus,
                                        echantillons=a.echantillons))
    if a.verifier_determinisme and produits:
        autre = ICI / "tmp" / "l6" / "determinisme"
        ecarts, n = [], 0
        for dsc in produits:
            # second processus : même entrée, sortie l6 dans un dossier témoin (copie des lectures de la chaîne)
            r = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(dsc), "--sortie", str(autre)],
                               env=dict(os.environ, RG_PILOTE_ENV="", RG_L6_SORTIE_TEMOIN=str(autre)),
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode:
                print(r.stdout[-2000:], r.stderr[-2000:])
                raise SystemExit("second processus en échec")
        print("déterminisme : voir validation/controler_signalisation.py --determinisme")
    return 0


if __name__ == "__main__":
    sys.exit(main())
