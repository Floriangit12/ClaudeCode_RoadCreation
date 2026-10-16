"""Fabrique la bibliothèque de static meshes « route_fr » avec les HDA route::* (hython Houdini 22, licence Indie).

    hython recon/pcg/assets_route/fabriquer_assets_route.py                    # tout : HDA, scène .hiplc, USD, FBX, catalogue
    hython recon/pcg/assets_route/fabriquer_assets_route.py --familles feux    # une famille
    hython recon/pcg/assets_route/fabriquer_assets_route.py --ids bordure_T2_L100 --sans-fbx

Chaîne (README : « Claude décrit, Houdini fabrique ») :
  1. construit / installe les HDA (hda/construire_hda_route.py) ;
  2. pour chaque asset de specs_assets_route.ASSETS, crée une instance de l'HDA dans la scène maîtresse
     recon/pcg/assets_route/assets_route.hiplc (/obj/route_<famille>, une instance par asset, rangées en grille) ;
  3. cuit trois LOD : LOD0 (100 %), LOD1 (50 %, sans cassure d'arêtes pour les bordures), LOD2 (20 %) ;
  4. écrit l'USD (Z haut, m) : Xform « <id> » avec un jeu de variantes « LOD » (LOD0, LOD1, LOD2 ; un Mesh par
     variante, convention de l'importeur USD d'Unreal), sous-ensembles de faces par matériau liés à des matériaux
     UsdPreviewSurface (références relatives vers assets/lib/route_fr/materiaux et assets/lib/materiaux, ou matériaux
     simples définis dans le fichier), primvars st et st1 = UV en mètres ;
  5. écrit les FBX (ROP FBX de Houdini) : <id>_LOD0.fbx, _LOD1, _LOD2, emplacements de matériaux = noms des matériaux ;
  6. écrit assets/lib/route_fr/meshes/catalogue.json (local) et assets/specs/route/catalogue_assets_route.json (versionné).

Python : lecture de la table des specs, pilotage des nœuds, sérialisation USD/JSON (entrées-sorties). Aucune géométrie
n'est calculée en Python : tout sort des réseaux SOP/VEX des HDA.
"""
import argparse
import datetime
import json
import math
import sys
import time
from pathlib import Path

import hou
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI / "hda"))
import specs_assets_route as SP  # noqa: E402
import hda_route_outils as O  # noqa: E402
import construire_hda_route as C  # noqa: E402

LIB = DEPOT / "assets" / "lib"
MESHES = LIB / "route_fr" / "meshes"
MAT_ROUTE = LIB / "route_fr" / "materiaux"
MAT_SITE = LIB / "materiaux"
CATALOGUE_VERSIONNE = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
HIP = ICI / "assets_route.hiplc"
LODS = [(0, 100.0), (1, 50.0), (2, 20.0)]
VERSION = "1.0"


# ---------------------------------------------------------------------------------------------- scène
def instance(parent, a, nom=None):
    n = parent.createNode(a["hda"], nom or a["id"][:80])
    for k, v in a["params"].items():
        p = n.parm(k)
        if p is None:
            raise RuntimeError(f"{a['id']} : paramètre {k} absent de {a['hda']}")
        p.set(v)
    if n.parm("materiau") is not None and a.get("materiau") and "materiau" not in a["params"]:
        n.parm("materiau").set(a["materiau"])
    return n


def pivot(parent, a, src):
    """Pivots documentés : feux -> bas du boîtier inférieur (y = 0), axe de la tête, face avant à z = 0."""
    if a["hda"] != "route::feu::1.0" and a["hda"] != "route::feu":
        return src
    x = parent.createNode("xform", f"{src.name()}_pivot")
    x.setInput(0, src)
    p = a["params"]
    x.parm("ty").set(0.5 * p["boitier_h"] + (0.0 if p["disposition"] == 0 else 0.0))
    return x


# ---------------------------------------------------------------------------------------------- USD
def vers_usd(v):
    return Gf.Vec3f(v[0], -v[2], v[1])


def chemin_materiau(m, fichier_usd):
    """Chemin relatif (depuis le fichier USD de l'asset) du .usda du matériau, ou None (matériau simple)."""
    for base in (MAT_ROUTE, MAT_SITE):
        f = base / m / f"{m}.usda"
        if f.exists():
            return Path(_relpath(f, fichier_usd.parent)).as_posix()
    return None


def _relpath(cible, depuis):
    import os
    return os.path.relpath(str(cible), str(depuis))


def materiau_simple(stage, chemin, m):
    d = SP.MATERIAUX_SIMPLES.get(m)
    if d is None:
        base = m.split("_")
        d = dict(couleur_srgb=[128, 128, 128], rugosite=0.6, metal=0.0, note=f"matériau « {m} » non trouvé : gris de remplacement")
        for k, v in SP.MATERIAUX_SIMPLES.items():          # pictogrammes de feux : couleur de la lentille
            if m.startswith(k):
                d = v
                break
    mat = UsdShade.Material.Define(stage, chemin)
    sh = UsdShade.Shader.Define(stage, chemin.AppendChild("Surface"))
    sh.CreateIdAttr("UsdPreviewSurface")

    def lin(c):
        return [((x / 255.0) / 12.92) if x / 255.0 <= 0.04045 else (((x / 255.0) + 0.055) / 1.055) ** 2.4 for x in c]
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*lin(d["couleur_srgb"])))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(d.get("rugosite", 0.6)))
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(d.get("metal", 0.0)))
    if d.get("emission_srgb"):
        sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0, 0, 0))
        mat.GetPrim().SetCustomDataByKey("route:emission_allumee_lineaire", Gf.Vec3f(*lin(d["emission_srgb"])))
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    if d.get("note"):
        mat.GetPrim().SetDocumentation(d["note"])
    return mat


def ecrire_maillage(stage, chemin, geo, looks):
    mesh = UsdGeom.Mesh.Define(stage, chemin)
    pts = [vers_usd(p.position()) for p in geo.points()]
    counts, idx, nrm, st, mats = [], [], [], [], {}
    a_uv = geo.findVertexAttrib("uv")
    a_n = geo.findVertexAttrib("N")
    for f, pr in enumerate(geo.prims()):
        vs = list(pr.vertices())[::-1]                   # Houdini (sens horaire) -> USD rightHanded
        counts.append(len(vs))
        for v in vs:
            idx.append(v.point().number())
            n = v.attribValue(a_n) if a_n else (0.0, 1.0, 0.0)
            nrm.append(vers_usd(n))
            uv = v.attribValue(a_uv) if a_uv else (0.0, 0.0, 0.0)
            st.append(Gf.Vec2f(uv[0], uv[1]))
        m = pr.attribValue("materiau") if geo.findPrimAttrib("materiau") else ""
        mats.setdefault(m or "defaut", []).append(f)
    mesh.CreatePointsAttr(Vt.Vec3fArray(pts))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(idx))
    mesh.CreateNormalsAttr(Vt.Vec3fArray(nrm))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateOrientationAttr(UsdGeom.Tokens.rightHanded)
    pv = UsdGeom.PrimvarsAPI(mesh)
    for nom in ("st", "st1"):
        p = pv.CreatePrimvar(nom, Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        p.Set(Vt.Vec2fArray(st))
    mn = Gf.Vec3f(*[min(p[i] for p in pts) for i in range(3)])
    mx = Gf.Vec3f(*[max(p[i] for p in pts) for i in range(3)])
    mesh.CreateExtentAttr(Vt.Vec3fArray([mn, mx]))
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    if len(mats) == 1:
        UsdShade.MaterialBindingAPI(mesh).Bind(looks[next(iter(mats))])
    else:
        for m, faces in sorted(mats.items()):
            sub = UsdGeom.Subset.Define(stage, chemin.AppendChild(f"mat_{m}"))
            sub.CreateElementTypeAttr(UsdGeom.Tokens.face)
            sub.CreateIndicesAttr(Vt.IntArray(faces))
            sub.CreateFamilyNameAttr(UsdShade.Tokens.materialBind)
            UsdShade.MaterialBindingAPI.Apply(sub.GetPrim())
            UsdShade.MaterialBindingAPI(sub).Bind(looks[m])
        UsdGeom.Subset.SetFamilyType(mesh, UsdShade.Tokens.materialBind, UsdGeom.Tokens.partition)
    return dict(points=len(pts), faces=len(counts), triangles=sum(c - 2 for c in counts), extent=[list(mn), list(mx)],
                materiaux=sorted(mats))


def ecrire_usd(a, geos, fichier):
    fichier.parent.mkdir(parents=True, exist_ok=True)
    if fichier.exists():
        fichier.unlink()
    stage = Usd.Stage.CreateNew(str(fichier))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    racine = Sdf.Path("/" + a["id"])
    x = UsdGeom.Xform.Define(stage, racine)
    stage.SetDefaultPrim(x.GetPrim())
    Usd.ModelAPI(x.GetPrim()).SetKind("component")
    x.GetPrim().SetCustomDataByKey("route:id", a["id"])
    x.GetPrim().SetCustomDataByKey("route:famille", a["famille"])
    x.GetPrim().SetCustomDataByKey("route:hda", a["hda"])
    x.GetPrim().SetCustomDataByKey("route:confiance", a.get("confiance", ""))
    x.GetPrim().SetCustomDataByKey("route:licence", "création maison (dépôt ClaudeCode_RoadCreation) ; textures CC0")
    x.GetPrim().SetDocumentation(f"{a['type']} — sources : " + " ; ".join(
        f"{s.get('doc')} p. {s.get('page', '?')}" for s in a.get("sources", [])))
    # matériaux
    noms = sorted({(m or "defaut") for g in geos.values()
                   for m in (g.primStringAttribValues("materiau") if g.findPrimAttrib("materiau") else [""])})
    looks = {}
    for m in noms:
        p = racine.AppendChild("Looks").AppendChild(m if m != "defaut" else "defaut")
        rel = chemin_materiau(a.get("materiau") if m == "defaut" else m, fichier)
        if rel:
            mat = UsdShade.Material.Define(stage, p)
            mat.GetPrim().GetReferences().AddReference(rel)
        else:
            mat = materiau_simple(stage, p, a.get("materiau") if m == "defaut" else m)
        looks[m] = mat
    # variantes LOD
    vset = x.GetPrim().GetVariantSets().AddVariantSet("LOD")
    bilan = {}
    for k, g in geos.items():
        vset.AddVariant(f"LOD{k}")
        vset.SetVariantSelection(f"LOD{k}")
        with vset.GetVariantEditContext():
            bilan[f"LOD{k}"] = ecrire_maillage(stage, racine.AppendChild(f"LOD{k}"), g, looks)
    vset.SetVariantSelection("LOD0")
    stage.GetRootLayer().customLayerData = {"route:version": VERSION, "route:script": "recon/pcg/assets_route/fabriquer_assets_route.py",
                                            "route:date": datetime.date.today().isoformat()}
    stage.GetRootLayer().Save()
    return bilan


# ---------------------------------------------------------------------------------------------- FBX
def reseau_materiaux():
    mat = hou.node("/mat")
    return mat


def ecrire_fbx(parent, src, fichier):
    w = parent.createNode("attribwrangle", f"{src.name()}_shop")
    w.parm("class").set(1)
    w.parm("snippet").set('s@shop_materialpath = "/mat/" + s@materiau;')
    w.setInput(0, src)
    r = parent.createNode("rop_fbx", f"{src.name()}_fbx")
    r.setInput(0, w)
    r.parm("sopoutput").set(str(fichier).replace("\\", "/"))
    r.parm("mkpath").set(1)
    r.parm("execute").pressButton()
    for n in (r, w):
        n.destroy()
    return fichier.exists()


def materiaux_fbx(noms):
    m = hou.node("/mat")
    for n in noms:
        if not m.node(n):
            s = m.createNode("principledshader::2.0", n)
            d = SP.MATERIAUX_SIMPLES.get(n)
            if d:
                s.parmTuple("basecolor").set(tuple(x / 255.0 for x in d["couleur_srgb"]))


# ---------------------------------------------------------------------------------------------- contrôles
def volume(geo):
    v = 0.0
    for pr in geo.prims():
        pts = [p.position() for p in pr.points()]
        for i in range(1, len(pts) - 1):
            v += pts[0].dot(pts[i].cross(pts[i + 1])) / 6.0
    return -v                      # convention Houdini (faces en sens horaire vues de l'extérieur)


def controle_masse(a, vol):
    out = {}
    if a["famille"] in ("bordures", "caniveaux") and a.get("profil") in SP.MASSES_KG and a["id"].endswith("_L100"):
        m, doc, page = SP.MASSES_KG[a["profil"]]
        out = dict(masse_catalogue_kg=m, source=f"{doc} p. {page}")
    elif a["id"] in SP.MASSES_PIECES_KG:
        m, doc, page = SP.MASSES_PIECES_KG[a["id"]]
        out = dict(masse_catalogue_kg=m, source=f"{doc} p. {page}")
    if out and a.get("materiau") in ("beton_bordure",):
        mc = vol * SP.DENSITE_BETON
        out["masse_modele_kg"] = round(mc, 1)
        out["ecart_pct"] = round(100.0 * (mc - out["masse_catalogue_kg"]) / out["masse_catalogue_kg"], 1)
        out["densite_kg_m3"] = SP.DENSITE_BETON
        if abs(out["ecart_pct"]) > 8.0:
            out["alerte"] = "écart > 8 % entre la masse du modèle et celle du catalogue : voir ASSETS_ROUTE.md § contrôles"
            if a["id"] in SP.NOTES_MASSES:
                out["explication"] = SP.NOTES_MASSES[a["id"]]
    return out


# ---------------------------------------------------------------------------------------------- pilote
def fabriquer(assets, fbx=True, sauver_hip=True):
    hou.hipFile.clear(suppress_save_prompt=True)
    C.construire()
    O.installer_tout()
    if not hou.node("/mat"):
        hou.node("/").createNode("matnet", "mat")
    familles = {}
    bilan = []
    t0 = time.time()
    for a in assets:
        fam = a["famille"]
        if fam not in familles:
            familles[fam] = hou.node("/obj").createNode("geo", f"route_{fam}")
            familles[fam].moveToGoodPosition()
        geo_obj = familles[fam]
        n = instance(geo_obj, a)
        k = len(geo_obj.children())
        geos, srcs = {}, {}
        for lod, pct in LODS:
            if lod == 0:
                src = n
            else:
                src = instance(geo_obj, a, f"{n.name()}_LOD{lod}")
                src.parm("lod_pourcentage").set(pct)
                if src.parm("chanfrein") is not None and a["hda"].startswith("route::extrusion_profil"):
                    src.parm("chanfrein").set(0.0)
                    src.parm("lod_pourcentage").set(100.0 if lod == 1 else 50.0)
            src = pivot(geo_obj, a, src)
            g = src.geometry().freeze()
            errs = [f"{c.path()}: {e}" for c in ([src] + list(n.allSubChildren())) for e in c.errors()]
            if errs:
                print("  ERREURS", a["id"], errs[:3])
            geos[lod] = g
            srcs[lod] = src
        dossier = MESHES / fam / a["id"]
        usd = dossier / f"{a['id']}.usda"
        b = ecrire_usd(a, geos, usd)
        fichiers = {"usd": usd.relative_to(LIB / "route_fr").as_posix()}
        if fbx:
            materiaux_fbx(b["LOD0"]["materiaux"])
            for lod, _ in LODS:
                f = dossier / f"{a['id']}_LOD{lod}.fbx"
                if ecrire_fbx(geo_obj, srcs[lod], f):
                    fichiers[f"fbx_LOD{lod}"] = f.relative_to(LIB / "route_fr").as_posix()
        vol = volume(geos[0])
        ent = dict(id=a["id"], famille=fam, type=a["type"], hda=a["hda"], params=a["params"], dimensions=a.get("dimensions"),
                   profil=a.get("profil"), lecture_profil=a.get("lecture_profil"), vue_nominale_m=a.get("vue_nominale_m"),
                   materiau=a.get("materiau"), materiaux=b["LOD0"]["materiaux"], sources=a.get("sources"),
                   confiance=a.get("confiance"), note=a.get("note"), fichiers=fichiers,
                   materiaux_alternatifs=SP.MATERIAUX_ALTERNATIFS.get(a.get("materiau"), []),
                   lods={k: dict(faces=v["faces"], triangles=v["triangles"], points=v["points"]) for k, v in b.items()},
                   boite_usd_m=b["LOD0"]["extent"], volume_m3=round(vol, 6), controle_masse=controle_masse(a, vol),
                   licence="création maison (HDA route::*, dépôt ClaudeCode_RoadCreation) ; matériaux CC0 (ambientCG, Poly Haven) "
                           "ou maison ; aucune donnée City Sample ni CARLA")
        bilan.append(ent)
        # disposition en grille dans la scène maîtresse
        try:
            n.setPosition(hou.Vector2(0, -k))
        except Exception:  # noqa: BLE001
            pass
        print(f"{a['id']:52s} LOD0 {b['LOD0']['triangles']:6d} tri  LOD1 {b['LOD1']['triangles']:6d}  LOD2 {b['LOD2']['triangles']:6d}  "
              f"vol {vol:.5f}  {ent['controle_masse'] or ''}", flush=True)
    for g in familles.values():
        g.layoutChildren()
    if sauver_hip:
        hou.hipFile.save(str(HIP))
    print(f"{len(bilan)} assets en {time.time() - t0:.0f} s")
    return bilan


def ecrire_catalogues(bilan, fusion=True):
    cat_loc = MESHES / "catalogue.json"
    anciens = {}
    if fusion and CATALOGUE_VERSIONNE.exists():
        for e in json.loads(CATALOGUE_VERSIONNE.read_text(encoding="utf-8")).get("assets", []):
            anciens[e["id"]] = e
    for e in bilan:
        anciens[e["id"]] = e
    ids_valides = {a["id"] for a in SP.ASSETS}
    assets = [anciens[i] for i in sorted(anciens) if i in ids_valides]
    mats = json.loads((MAT_ROUTE / "catalogue.json").read_text(encoding="utf-8")) if (MAT_ROUTE / "catalogue.json").exists() else {}
    site = []
    for d in sorted(MAT_SITE.iterdir()) if MAT_SITE.exists() else []:
        mf = d / "meta.json"
        if mf.exists():
            m = json.loads(mf.read_text(encoding="utf-8"))
            lic = m.get("licence")
            site.append(dict(nom=m.get("nom", d.name), libelle=m.get("libelle"), source=m.get("source"), source_id=m.get("source_id"),
                             licence=lic.get("nom") if isinstance(lic, dict) else lic, resolution=m.get("resolution"),
                             tile_m=m.get("tile_m"), usd=f"../materiaux/{d.name}/{m.get('usd', d.name + '.usda')}"))
    cat = dict(schema="route_fr/catalogue_assets/1.0", version=VERSION, date=datetime.date.today().isoformat(),
               role="Bibliothèque d'assets de la route française (static meshes et matériaux PBR) pour le générateur procédural.",
               fabrication="hython recon/pcg/assets_route/fabriquer_assets_route.py (HDA route::* dans recon/pcg/assets_route/hda)",
               racine_fichiers="assets/lib/route_fr (non versionné, régénérable)",
               conventions=dict(usd="Z haut, mètres ; jeu de variantes LOD (LOD0-2) ; primvars st et st1 = UV en mètres ; "
                                    "sous-ensembles de faces par matériau",
                                repere="bordures : X le long, Y = u (vers l'arrière, face vue à Y = 0), Z = v ; feux : optiques vers +Y ; "
                                       "pivot au milieu de la longueur sur l'arête avant basse (éléments droits), au point d'angle de "
                                       "la face (angles, courbes), au pied (supports, potelets : sol à Z = 0), bas du boîtier "
                                       "inférieur (feux)",
                                fbx="Y haut (Houdini), un fichier par LOD ; emplacements de matériaux nommés comme les matériaux"),
               sources=SP.SOURCES, tolerances_nf_bordures=SP.TOLERANCES, materiaux_simples=SP.MATERIAUX_SIMPLES,
               materiaux_pbr=[dict(nom=m["nom"], source=m["source"], source_id=m["source_id"], licence=m["licence"],
                                   resolution=m["resolution"], tile_m=m["tile_m"], usd=f"materiaux/{m['usd']}") for m in mats.get("materiaux", [])],
               materiaux_site=site,
               regle_materiaux="élément unitaire (pavé, dalle, bordure) = matériau de matière (béton, granit) ; textures d'appareillage "
                               "(paves_*, dalles_*) réservées aux sols tuilables",
               assets=assets)
    CATALOGUE_VERSIONNE.parent.mkdir(parents=True, exist_ok=True)
    CATALOGUE_VERSIONNE.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
    cat_loc.parent.mkdir(parents=True, exist_ok=True)
    cat_loc.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
    print("catalogues :", CATALOGUE_VERSIONNE, len(assets), "assets")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--familles", nargs="*")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--sans-fbx", action="store_true")
    ap.add_argument("--sans-hip", action="store_true")
    a = ap.parse_args()
    assets = [x for x in SP.ASSETS if (not a.familles or x["famille"] in a.familles) and (not a.ids or x["id"] in a.ids)]
    bilan = fabriquer(assets, fbx=not a.sans_fbx, sauver_hip=not a.sans_hip and not a.familles and not a.ids)
    ecrire_catalogues(bilan)


if __name__ == "__main__":
    main()
