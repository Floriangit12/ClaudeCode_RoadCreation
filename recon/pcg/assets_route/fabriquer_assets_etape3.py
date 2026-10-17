"""Étape 3 de la bibliothèque « route_fr » : fabrication Houdini (hython 22, Indie) des nouveaux static meshes, des panneaux
montés sur leurs plaques, des ensembles (compositions USD) et ajout au catalogue versionné.

    hython recon/pcg/assets_route/fabriquer_assets_etape3.py                       # tout
    hython recon/pcg/assets_route/fabriquer_assets_etape3.py --familles retenue feux
    hython recon/pcg/assets_route/fabriquer_assets_etape3.py --sans-panneaux --sans-fbx
    hython recon/pcg/assets_route/fabriquer_assets_etape3.py --panneaux-seulement --codes AB4 B1

Chaîne (« Claude décrit, Houdini fabrique ») :
  1. construit/installe les HDA route::assemblage et route::panneau (hda/construire_hda_etape3.py) et installe les HDA
     de l'étape 1 (sans les reconstruire) ;
  2. assets de specs_assets_etape3.ASSETS : une instance d'HDA par asset dans la scène maîtresse
     recon/pcg/assets_route/assets_route_etape3.hiplc, cuisson LOD0 / LOD1 (50 %) / LOD2 (20 %), USD et FBX par les
     fonctions de fabriquer_assets_route (mêmes conventions que l'étape 1) ;
  3. panneaux : pour chaque signal de assets/lib/route_fr/panneaux_3d/contours_faces.json (600 plaques relevées sur les
     faces officielles), un USD par signal avec un jeu de variantes « gamme » (miniature … très grande quand la forme a
     des gammes IISR), maillage de route::panneau, face texturée par le PNG officiel (UV 0-1, opacité = alpha), revers ;
     FBX de la gamme normale ;
  4. ensembles : compositions USD (références) support + colliers + panneaux aux hauteurs IISR, mâts + têtes de feux ;
  5. catalogue : assets/specs/route/catalogue_assets_route.json est relu, les entrées existantes sont conservées telles
     quelles et les nouvelles AJOUTÉES (écriture atomique : fichier temporaire puis os.replace) ; même chose pour la copie
     locale assets/lib/route_fr/meshes/catalogue.json.
"""
import argparse
import datetime
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import hou
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI / "hda"))
import specs_assets_route as SP  # noqa: E402
import specs_assets_etape3 as SE  # noqa: E402  (complète SP.MATERIAUX_SIMPLES)
import hda_route_outils as O  # noqa: E402
import construire_hda_etape3 as C3  # noqa: E402
import fabriquer_assets_route as FA  # noqa: E402

LIB = DEPOT / "assets" / "lib" / "route_fr"
MESHES = LIB / "meshes"
PANNEAUX = LIB / "panneaux_3d"
CONTOURS = PANNEAUX / "contours_faces.json"
CAT_V = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
CAT_L = MESHES / "catalogue.json"
HIP = ICI / "assets_route_etape3.hiplc"
LODS = [(0, 100.0), (1, 50.0), (2, 20.0)]
LICENCE = ("création maison (HDA route::*, dépôt ClaudeCode_RoadCreation) ; matériaux CC0 (ambientCG, Poly Haven) ou maison ; "
           "aucune donnée City Sample ni CARLA")
LICENCE_PANNEAU = ("plaque : création maison ; face : signal officiel (Cerema / DSR, PDF détourés, Licence Ouverte 2.0 présumée, "
                   "réserve non levée — voir panneaux_fr_catalogue.json meta.licence_source) ; PNG non versionnés")

# ---------------------------------------------------------------------------------------------- matériaux simples (opacité)
_materiau_simple_e1 = FA.materiau_simple


def materiau_simple(stage, chemin, m):
    mat = _materiau_simple_e1(stage, chemin, m)
    d = SP.MATERIAUX_SIMPLES.get(m) or {}
    if d.get("opacite") is not None:
        sh = UsdShade.Shader(stage.GetPrimAtPath(chemin.AppendChild("Surface")))
        sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(d["opacite"]))
    return mat


FA.materiau_simple = materiau_simple


def ecrire_json_atomique(chemin, donnees):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=chemin.name + ".", suffix=".tmp", dir=str(chemin.parent))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=1, ensure_ascii=False)
    os.replace(tmp, chemin)


# ---------------------------------------------------------------------------------------------- assets (HDA -> USD/FBX)
def fabriquer_assets(assets, fbx=True):
    familles, bilan, erreurs = {}, [], []
    t0 = time.time()
    for a in assets:
        fam = a["famille"]
        if fam not in familles:
            familles[fam] = hou.node("/obj").createNode("geo", f"e3_{fam}")
            familles[fam].moveToGoodPosition()
        g = familles[fam]
        n = FA.instance(g, a)
        geos, srcs = {}, {}
        for lod, pct in LODS:
            if lod == 0:
                src = n
            else:
                src = FA.instance(g, a, f"{n.name()}_LOD{lod}")
                src.parm("lod_pourcentage").set(pct)
                if a["hda"].startswith("route::extrusion_profil") and src.parm("chanfrein") is not None:
                    src.parm("chanfrein").set(0.0)
                    src.parm("lod_pourcentage").set(100.0 if lod == 1 else 50.0)
            src = FA.pivot(g, a, src)
            try:
                geo = src.geometry().freeze()
            except hou.OperationFailed as e:
                erreurs.append((a["id"], str(e)))
                geo = None
            errs = [f"{c.path()}: {e}" for c in ([src] + list(n.allSubChildren())) for e in c.errors()]
            if errs or geo is None or len(geo.prims()) == 0:
                erreurs.append((a["id"], errs[:3] or "géométrie vide"))
                print("  ERREUR", a["id"], errs[:3], flush=True)
                break
            geos[lod], srcs[lod] = geo, src
        if len(geos) < 3:
            continue
        dossier = MESHES / fam / a["id"]
        usd = dossier / f"{a['id']}.usda"
        b = FA.ecrire_usd(a, geos, usd)
        stage = Usd.Stage.Open(str(usd))
        racine = stage.GetDefaultPrim()
        racine.SetCustomDataByKey("route:etape", 3)
        racine.SetCustomDataByKey("route:phase_chantier", a.get("phase_chantier", ""))
        stage.GetRootLayer().Save()
        fichiers = {"usd": usd.relative_to(LIB).as_posix()}
        if fbx:
            FA.materiaux_fbx(b["LOD0"]["materiaux"])
            for lod, _ in LODS:
                f = dossier / f"{a['id']}_LOD{lod}.fbx"
                if FA.ecrire_fbx(g, srcs[lod], f):
                    fichiers[f"fbx_LOD{lod}"] = f.relative_to(LIB).as_posix()
        vol = FA.volume(geos[0])
        ent = dict(id=a["id"], famille=fam, type=a["type"], hda=a["hda"], params=a["params"], dimensions=a.get("dimensions"),
                   profil=a.get("profil"), lecture_profil=a.get("lecture_profil"), vue_nominale_m=a.get("vue_nominale_m"),
                   materiau=a.get("materiau"), materiaux=b["LOD0"]["materiaux"], sources=a.get("sources"),
                   confiance=a.get("confiance"), note=a.get("note"), fichiers=fichiers,
                   materiaux_alternatifs=SP.MATERIAUX_ALTERNATIFS.get(a.get("materiau"), []),
                   lods={k: dict(faces=v["faces"], triangles=v["triangles"], points=v["points"]) for k, v in b.items()},
                   boite_usd_m=b["LOD0"]["extent"], volume_m3=round(vol, 6), controle_masse={}, licence=LICENCE,
                   etape=3, phase_chantier=a.get("phase_chantier"), regles=a.get("regles", []), pose=a.get("pose", {}))
        if vol <= 0:
            ent["alerte"] = "volume négatif ou nul : orientation des faces à vérifier"
        bilan.append(ent)
        print(f"{a['id']:52s} LOD0 {b['LOD0']['triangles']:6d} tri  LOD1 {b['LOD1']['triangles']:6d}  LOD2 {b['LOD2']['triangles']:6d}  "
              f"vol {vol:.5f}", flush=True)
    for g in familles.values():
        g.layoutChildren()
    print(f"{len(bilan)} assets en {time.time() - t0:.0f} s ; {len(erreurs)} erreur(s)", flush=True)
    return bilan, erreurs


# ---------------------------------------------------------------------------------------------- panneaux
def _rails(plaques_m):
    """Hauteurs (z) des rails de fixation, comme le VEX de route::panneau (2 rails si la plaque dépasse 0,45 m)."""
    zs = []
    for poly in plaques_m:
        z0, z1 = min(p[1] for p in poly), max(p[1] for p in poly)
        h = z1 - z0
        zs += [z0 + 0.25 * h, z0 + 0.75 * h] if h > 0.45 else [z0 + 0.5 * h]
    return sorted(round(z, 4) for z in zs)


def materiau_face(stage, chemin, png_rel):
    mat = UsdShade.Material.Define(stage, chemin)
    sh = UsdShade.Shader.Define(stage, chemin.AppendChild("Surface"))
    sh.CreateIdAttr("UsdPreviewSurface")
    lec = UsdShade.Shader.Define(stage, chemin.AppendChild("LecteurUV"))
    lec.CreateIdAttr("UsdPrimvarReader_float2")
    lec.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    lec.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    tex = UsdShade.Shader.Define(stage, chemin.AppendChild("Face"))
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(png_rel))
    tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(lec.ConnectableAPI(), "result")
    tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    tex.CreateOutput("a", Sdf.ValueTypeNames.Float)
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(), "rgb")
    sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(tex.ConnectableAPI(), "a")
    sh.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.5)
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.35)
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    mat.GetPrim().SetDocumentation("face officielle du signal (rétroréfléchissante de classe 1 ou 2 : non simulée)")
    return mat


def fabriquer_panneaux(codes=None, fbx=True):
    donnees = json.loads(CONTOURS.read_text(encoding="utf-8"))
    g = hou.node("/obj").createNode("geo", "e3_panneaux")
    n = g.createNode("route::panneau::1.0", "panneau")
    bilan, erreurs = [], []
    t0 = time.time()
    FA.materiaux_fbx(["face_panneau", "revers_panneau"])
    for s in donnees["signaux"]:
        if codes and s["id"] not in codes:
            continue
        idp = "panneau_" + s["id"].replace("-", "_t_").replace(".", "_")      # « - » interdit dans les noms USD ; _t_ évite
        #                                                                     la collision M8d-bis / M8d_bis
        W, H = s["png_px"]
        px, py = s["pivot_px"]
        dossier = PANNEAUX / s["famille"] / idp
        dossier.mkdir(parents=True, exist_ok=True)
        usd = dossier / f"{idp}.usda"
        if usd.exists():
            usd.unlink()
        stage = Usd.Stage.CreateNew(str(usd))
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        racine = Sdf.Path("/" + idp)
        x = UsdGeom.Xform.Define(stage, racine)
        stage.SetDefaultPrim(x.GetPrim())
        Usd.ModelAPI(x.GetPrim()).SetKind(Kind.Tokens.component)
        png_abs = DEPOT / s["png"]
        png_rel = Path(os.path.relpath(png_abs, dossier)).as_posix()
        looks = {"face_panneau": materiau_face(stage, racine.AppendChild("Looks").AppendChild("face_panneau"), png_rel),
                 "revers_panneau": materiau_simple(stage, racine.AppendChild("Looks").AppendChild("revers_panneau"), "revers_panneau")}
        vset = x.GetPrim().GetVariantSets().AddVariantSet("gamme")
        tailles, rails, tri = {}, {}, {}
        ok = True
        for gam, fac in sorted(s["gammes"].items(), key=lambda kv: kv[1]):
            e = s["m_par_px"] * fac
            # vue de face (observateur en +Y regardant −Y) : la gauche de l'image est en +X -> X = (px − x) e, img_l < 0
            plaques_m = [[((px - xx) * e, (py - yy) * e) for xx, yy in p["contour_px"]] for p in s["plaques"]]
            n.parm("contours").set(" | ".join(" ".join(f"{a:.5f} {b:.5f}" for a, b in poly) for poly in plaques_m))
            n.parm("img_x0").set(px * e)
            n.parm("img_z0").set((py - H) * e)
            n.parm("img_l").set(-W * e)
            n.parm("img_h").set(H * e)
            try:
                geo = n.geometry().freeze()
            except hou.OperationFailed as err:
                erreurs.append((s["id"], str(err)))
                ok = False
                break
            if n.errors() or len(geo.prims()) == 0:
                erreurs.append((s["id"], n.errors()[:2] or "vide"))
                ok = False
                break
            vset.AddVariant(gam)
            vset.SetVariantSelection(gam)
            with vset.GetVariantEditContext():
                b = FA.ecrire_maillage(stage, racine.AppendChild("plaque"), geo, looks)
            xs = [a for poly in plaques_m for a, _ in poly]
            zs = [b2 for poly in plaques_m for _, b2 in poly]
            tailles[gam] = [round(max(xs) - min(xs), 3), round(max(zs) - min(zs), 3), round(min(zs), 3)]
            rails[gam] = _rails(plaques_m)
            tri[gam] = b["triangles"]
            if gam == "normale" and fbx:
                f = dossier / f"{idp}_normale.fbx"
                FA.ecrire_fbx(g, n, f)
        if not ok:
            continue
        vset.SetVariantSelection("normale")
        p = x.GetPrim()
        for k, v in (("route:id", idp), ("route:famille", "panneaux"), ("route:code", s["code"]), ("route:etape", 3),
                     ("route:face_png", s["png"]), ("route:regle_echelle", s["regle_echelle"]), ("route:confiance", s["confiance"]),
                     ("route:licence", LICENCE_PANNEAU)):
            p.SetCustomDataByKey(k, v)
        p.SetDocumentation(f"{s['code']} — {s.get('nom') or ''} ; plaque(s) à bord tombé 25 mm, face vers +Y, pivot au milieu du "
                           "bord inférieur de la plaque principale")
        stage.GetRootLayer().customLayerData = {"route:script": "recon/pcg/assets_route/fabriquer_assets_etape3.py",
                                                "route:date": datetime.date.today().isoformat()}
        stage.GetRootLayer().Save()
        fichiers = {"usd": usd.relative_to(LIB).as_posix()}
        if fbx and (dossier / f"{idp}_normale.fbx").exists():
            fichiers["fbx_normale"] = (dossier / f"{idp}_normale.fbx").relative_to(LIB).as_posix()
        bilan.append(dict(id=idp, famille="panneaux", type=f"panneau {s['code']} – {(s.get('nom') or '')[:90]}", hda="route::panneau",
                          params=dict(contours="assets/lib/route_fr/panneaux_3d/contours_faces.json (id " + s["id"] + ")",
                                      bord_tombe=0.025, rebord=0.012, tole=0.002, rails=1),
                          dimensions=dict(gammes_m={k: dict(largeur=v[0], hauteur=v[1], bas_le_plus_bas=v[2]) for k, v in tailles.items()},
                                          nb_plaques=len(s["plaques"])),
                          code=s["code"], signal=s["id"], famille_signal=s["famille"], forme=s["forme"], face_png=s["png"],
                          materiau="revers_panneau", materiaux=["face_panneau", "revers_panneau"],
                          sources=[dict(doc="panneaux_cat", note=s["regle_echelle"]),
                                   dict(doc="iisr1", page=10, article="art. 5-3", note="gammes"),
                                   dict(doc="iisr1", page=17, article="art. 10", note="envers et bord tombé de couleur neutre")],
                          confiance=s["confiance"], fichiers=fichiers, lods={"LOD0": dict(triangles=tri.get("normale"))},
                          licence=LICENCE_PANNEAU, etape=3, phase_chantier="P08_signalisation",
                          regles=["RF-SV-GEN.ORIENTATION", "RF-SV-D.HAUTEURS"],
                          pose=dict(pivot="milieu du bord inférieur de la plaque principale, face Y = 0 vers +Y",
                                    rails_z_m=rails, accroche="colliers collier_panneau_D* aux hauteurs des rails, face à "
                                                              "Y = rayon du poteau + 0,06 m"),
                          note="plaque(s) relevée(s) sur l'emprise opaque de la face ; bord tombé 25 mm, rebord 12 mm, tôle 2 mm, "
                               "rails 30 × 22 mm : estimations"))
        if len(bilan) % 50 == 0:
            print(f"  {len(bilan)} panneaux ({time.time() - t0:.0f} s)", flush=True)
    print(f"{len(bilan)} panneaux en {time.time() - t0:.0f} s ; {len(erreurs)} erreur(s) {erreurs[:5]}", flush=True)
    return bilan, erreurs


# ---------------------------------------------------------------------------------------------- supports coupés à longueur
def supports_sur_mesure():
    """Pour chaque ensemble de panneaux : hauteur du haut de la dernière plaque (d'après contours_faces.json et la gamme) ;
    le support est coupé à 5 cm au-dessus, arrondi au décimètre supérieur (support_rond_D<d>_H<hh>, route::poteau).
    Renvoie (assets de supports à fabriquer, {ensemble: id du support})."""
    cont = {s["id"]: s for s in json.loads(CONTOURS.read_text(encoding="utf-8"))["signaux"]}
    existants = {a["id"] for a in SE.ASSETS} | {a["id"] for a in SP.ASSETS}
    nouveaux, choix = {}, {}
    for id_, sup, pans, z_bas, srcs in SE.ENSEMBLES_PANNEAUX:
        base = next(a for a in SE.ASSETS + SP.ASSETS if a["id"] == sup)
        d = base["params"]["d1"]
        z = z_bas
        for code, gam in pans:
            s = cont[code]
            fac = s["gammes"].get(gam, 1.0)
            ys = [y for p in s["plaques"] for _, y in p["contour_px"]]
            z += (max(ys) - min(ys)) * s["m_par_px"] * fac + 0.05
        H = math.ceil((z - 0.05 + 0.05) * 10 - 1e-6) / 10.0
        sid = f"support_rond_D{int(round(d * 1000))}_H{int(round(H * 10)):02d}"
        choix[id_.replace("-", "_")] = sid
        if sid not in existants and sid not in nouveaux:
            a = dict(base)
            a = json.loads(json.dumps(base))
            a["id"] = sid
            a["type"] = f"support rond D{int(round(d * 1000))} H{H:g} (coupé à longueur pour un ensemble)"
            a["params"]["hauteur"] = H
            a["dimensions"]["hauteur_m"] = H
            a["note"] = "support coupé à 5 cm au-dessus du haut du panneau de l'ensemble qui l'utilise"
            a["phase_chantier"] = "P08_signalisation"
            a["regles"] = ["RF-SV-D.HAUTEURS"]
            a["pose"] = dict(usage=f"ensemble {id_}", coupe="haut du panneau + 0,05 m, arrondi au décimètre supérieur")
            a["etape"] = 3
            nouveaux[sid] = a
    return list(nouveaux.values()), choix


# ---------------------------------------------------------------------------------------------- ensembles (compositions)
def _ref(stage, chemin, cible_usd, depuis, t=(0, 0, 0), rz=0.0, variantes=None):
    p = UsdGeom.Xform.Define(stage, chemin)
    p.GetPrim().GetReferences().AddReference(Path(os.path.relpath(cible_usd, depuis)).as_posix())
    p.AddTranslateOp().Set(Gf.Vec3d(*t))
    if rz:
        p.AddRotateZOp().Set(rz)
    for vs, v in (variantes or {}).items():
        p.GetPrim().GetVariantSets().AddVariantSet(vs).SetVariantSelection(v)
    return p


def fabriquer_ensembles(index, choix_supports=None):
    """index : id -> entrée de catalogue (étape 1 + 3) pour trouver les USD et les dimensions."""
    bilan = []
    choix_supports = choix_supports or {}
    dossier = MESHES / "ensembles"
    dossier.mkdir(parents=True, exist_ok=True)
    for id_, sup, pans, z_bas, srcs in SE.ENSEMBLES_PANNEAUX:
        id_ = id_.replace("-", "_")
        sup = choix_supports.get(id_, sup)
        ids_p = ["panneau_" + c.replace("-", "_t_") for c, _ in pans]
        if sup not in index or any(i not in index for i in ids_p):
            print("  ensemble ignoré (composant absent)", id_, sup, ids_p, flush=True)
            continue
        es = index[sup]
        d_pole = es["params"].get("d1", 0.06)
        usd = dossier / id_ / f"{id_}.usda"
        usd.parent.mkdir(parents=True, exist_ok=True)
        if usd.exists():
            usd.unlink()
        st = Usd.Stage.CreateNew(str(usd))
        UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(st, 1.0)
        r = UsdGeom.Xform.Define(st, "/" + id_)
        st.SetDefaultPrim(r.GetPrim())
        Usd.ModelAPI(r.GetPrim()).SetKind(Kind.Tokens.assembly)
        _ref(st, f"/{id_}/support", LIB / es["fichiers"]["usd"], usd.parent)
        z = z_bas
        y_face = d_pole / 2 + 0.06
        composants = [dict(id=sup, role="support")]
        haut = z_bas
        for k, ((code, gam), idp) in enumerate(zip(pans, ids_p)):
            ep = index[idp]
            dg = ep["dimensions"]["gammes_m"].get(gam) or ep["dimensions"]["gammes_m"]["normale"]
            gam = gam if gam in ep["dimensions"]["gammes_m"] else "normale"
            z_piv = z - dg["bas_le_plus_bas"]
            _ref(st, f"/{id_}/panneau_{k}", LIB / ep["fichiers"]["usd"], usd.parent, (0, y_face, z_piv), variantes={"gamme": gam})
            for j, zr in enumerate(ep["pose"]["rails_z_m"].get(gam, [])):
                ci = f"collier_panneau_D{int(round(d_pole * 1000)):03d}"
                if ci in index:
                    _ref(st, f"/{id_}/collier_{k}_{j}", LIB / index[ci]["fichiers"]["usd"], usd.parent, (0, 0, z_piv + zr))
            composants.append(dict(id=idp, gamme=gam, z_pivot_m=round(z_piv, 3), y_face_m=round(y_face, 3)))
            haut = z_piv + dg["bas_le_plus_bas"] + dg["hauteur"]
            z = haut + 0.05
        H_sup = es["params"].get("hauteur", 3.0)
        r.GetPrim().SetCustomDataByKey("route:etape", 3)
        st.GetRootLayer().Save()
        ent = dict(id=id_, famille="panneaux_montes", type=f"ensemble {' + '.join(c for c, _ in pans)} sur {sup}",
                   hda="composition_usd", params={}, dimensions=dict(bas_m=z_bas, haut_m=round(haut, 3), hauteur_support_m=H_sup),
                   composants=composants, sources=srcs, confiance="moyenne", materiau=None,
                   fichiers={"usd": usd.relative_to(LIB).as_posix()}, licence=LICENCE_PANNEAU, etape=3,
                   phase_chantier="P08_signalisation", regles=["RF-SV-D.HAUTEURS", "RF-SV-GEN.ORIENTATION"],
                   pose=dict(pivot="pied du support", face="+Y"))
        if haut > H_sup + 0.02:
            ent["alerte"] = f"le haut des panneaux ({haut:.2f} m) dépasse le support ({H_sup:.2f} m)"
        bilan.append(ent)
    for id_, mat, tetes, srcs in SE.ENSEMBLES_FEUX:
        if mat not in index or any(t not in index for t, _, _ in tetes):
            print("  ensemble de feux ignoré", id_, flush=True)
            continue
        em = index[mat]
        d_pole = em["params"].get("d1", 0.114) if em.get("params") else 0.114
        usd = dossier / id_ / f"{id_}.usda"
        usd.parent.mkdir(parents=True, exist_ok=True)
        if usd.exists():
            usd.unlink()
        st = Usd.Stage.CreateNew(str(usd))
        UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(st, 1.0)
        r = UsdGeom.Xform.Define(st, "/" + id_)
        st.SetDefaultPrim(r.GetPrim())
        Usd.ModelAPI(r.GetPrim()).SetKind(Kind.Tokens.assembly)
        _ref(st, f"/{id_}/mat", LIB / em["fichiers"]["usd"], usd.parent)
        comp = [dict(id=mat, role="mât")]
        for k, (t, zb, az) in enumerate(tetes):
            ab = math.radians(az)
            dist = (d_pole if isinstance(d_pole, float) else 0.114) / 2 + 0.38
            if t.startswith("feu_R11v_D200") or t.startswith("feu_repetiteur_R11v_D90"):
                dist = 0.057 + 0.30
            _ref(st, f"/{id_}/tete_{k}", LIB / index[t]["fichiers"]["usd"], usd.parent,
                 (-math.sin(ab) * dist, math.cos(ab) * dist, zb), rz=az)
            comp.append(dict(id=t, z_bas_m=zb, azimut_deg=az))
            if "feu_bras_court_L033" in index:                 # bras court entre le mât et la console de la tête
                bz = index[t].get("boite_usd_m") or [[0, 0, 0], [0, 0, 0.3]]
                zc = zb + 0.5 * (bz[0][2] + bz[1][2])
                _ref(st, f"/{id_}/bras_{k}", LIB / index["feu_bras_court_L033"]["fichiers"]["usd"], usd.parent, (0, 0, zc), rz=az)
                comp.append(dict(id="feu_bras_court_L033", z_m=round(zc, 3), azimut_deg=az))
        st.GetRootLayer().Save()
        bilan.append(dict(id=id_, famille="feux_montes", type=f"ensemble de feux sur {mat}", hda="composition_usd", params={},
                          dimensions=dict(hauteur_mat_m=em["dimensions"].get("hauteur_m")), composants=comp, sources=srcs,
                          confiance="moyenne", materiau=None, fichiers={"usd": usd.relative_to(LIB).as_posix()}, licence=LICENCE,
                          etape=3, phase_chantier="P09_feux", regles=["RF-FEU.HAUTEUR.GENERATEUR", "RF-FEU.HAUTEUR.TROTTOIR"],
                          pose=dict(pivot="pied du mât", face="+Y (azimut 0)")))
    print(len(bilan), "ensembles", flush=True)
    return bilan


# ---------------------------------------------------------------------------------------------- catalogue
def ecrire_catalogue(nouveaux, materiaux_e3, complet=False):
    cat = json.loads(CAT_V.read_text(encoding="utf-8"))
    ids_avant = [a["id"] for a in cat["assets"]]
    e1 = [a for a in cat["assets"] if a.get("etape") != 3]          # étape 1 (et autres) : jamais modifiées
    e1_ids = {a["id"] for a in e1}
    e3 = {} if complet else {a["id"]: a for a in cat["assets"] if a.get("etape") == 3}   # passe complète : l'étape 3 est remplacée
    for e in nouveaux:
        if e["id"] in e1_ids:
            print("  identifiant déjà pris par l'étape 1, entrée ignorée :", e["id"], flush=True)
            continue
        e3[e["id"]] = e
    cat["assets"] = e1 + [e3[i] for i in sorted(e3)]
    assert all(i in {a["id"] for a in cat["assets"]} for i in e1_ids), "un identifiant de l'étape 1 a disparu"
    for k, v in SE.SOURCES_E3.items():
        cat["sources"].setdefault(k, v)
    for k, v in SE.MATERIAUX_SIMPLES_E3.items():
        cat["materiaux_simples"].setdefault(k, v)
    noms_pbr = {m["nom"] for m in cat["materiaux_pbr"]}
    for m in materiaux_e3:
        if m["nom"] not in noms_pbr:
            cat["materiaux_pbr"].append(m)
    cat["etape3"] = dict(date=datetime.date.today().isoformat(),
                         fabrication="hython recon/pcg/assets_route/fabriquer_assets_etape3.py (HDA route::assemblage, route::panneau "
                                     "et HDA de l'étape 1) ; matériaux : python recon/pcg/assets_route/telecharger_materiaux_etape3.py",
                         documentation="recon/pcg/assets_route/ASSETS_ROUTE_ETAPE3.md",
                         phases_chantier=[dict(id=i, role=r) for i, r in SE.PHASES],
                         conventions=dict(objets_au_sol="pivot au pied, sol à Z = 0, face principale (feux, panneaux) vers +Y",
                                          lineaires="X le long, face côté circulation vers −Y à Y = 0, modules centrés, longueur = pas",
                                          affleurants="dessus à Z = 0 (niveau fini), corps sous le sol",
                                          panneaux="face dans le plan Y = 0 vers +Y, pivot au milieu du bord inférieur de la plaque "
                                                   "principale ; jeu de variantes USD « gamme »",
                                          ensembles="compositions USD (références relatives) : support + colliers + panneaux, mât + têtes"),
                         fiches_materiaux="recon/pcg/assets_route/fiches_materiaux_route.json",
                         correspondances_description=SE.CORRESPONDANCES,
                         nombre_ajoutes=len([a for a in cat["assets"] if a.get("etape") == 3]))
    cat["date"] = datetime.date.today().isoformat()
    ecrire_json_atomique(CAT_V, cat)
    ecrire_json_atomique(CAT_L, cat)
    print("catalogue :", len(cat["assets"]), "assets dont", cat["etape3"]["nombre_ajoutes"], "de l'étape 3", flush=True)
    return cat


def materiaux_e3_catalogue():
    m = json.loads((ICI / "manifeste_materiaux_etape3.json").read_text(encoding="utf-8"))
    out = []
    for e in m["materiaux"]:
        d = LIB / "materiaux" / e["nom"]
        if (d / "meta.json").exists():
            out.append(dict(nom=e["nom"], source=e["source"], source_id=e["id"], licence=e["licence"]["nom"], resolution=e["resolution_cible"],
                            tile_m=e["tile_m"], usd=f"materiaux/{e['nom']}/{e['nom']}.usda", etape=3, libelle=e["libelle"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--familles", nargs="*")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--codes", nargs="*", help="panneaux : identifiants de signaux")
    ap.add_argument("--sans-fbx", action="store_true")
    ap.add_argument("--sans-panneaux", action="store_true")
    ap.add_argument("--panneaux-seulement", action="store_true")
    a = ap.parse_args()
    hou.hipFile.clear(suppress_save_prompt=True)
    C3.construire()
    O.installer_tout()
    if not hou.node("/mat"):
        hou.node("/").createNode("matnet", "mat")
    nouveaux, erreurs = [], []
    sup_mesure, choix_supports = supports_sur_mesure()
    if not a.panneaux_seulement:
        assets = [x for x in SE.ASSETS + sup_mesure if (not a.familles or x["famille"] in a.familles) and (not a.ids or x["id"] in a.ids)]
        b, e = fabriquer_assets(assets, fbx=not a.sans_fbx)
        nouveaux += b
        erreurs += e
    if not a.sans_panneaux:
        b, e = fabriquer_panneaux(a.codes, fbx=not a.sans_fbx)
        nouveaux += b
        erreurs += e
    cat = json.loads(CAT_V.read_text(encoding="utf-8"))
    index = {x["id"]: x for x in cat["assets"]}
    index.update({x["id"]: x for x in nouveaux})
    if not a.familles and not a.ids and not a.codes:
        nouveaux += fabriquer_ensembles(index, choix_supports)
    if not a.familles and not a.ids and not a.codes and not a.panneaux_seulement:
        hou.hipFile.save(str(HIP))
    ecrire_catalogue(nouveaux, materiaux_e3_catalogue(),
                     complet=not (a.familles or a.ids or a.codes or a.sans_panneaux or a.panneaux_seulement))
    ecrire_json_atomique(PANNEAUX.parent / "meshes" / "erreurs_etape3.json", erreurs)
    print("erreurs :", len(erreurs), erreurs[:10])


if __name__ == "__main__":
    main()
