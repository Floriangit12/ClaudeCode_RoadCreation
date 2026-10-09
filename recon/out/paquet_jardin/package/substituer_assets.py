"""Remplace les volumes provisoires de la scène par les assets de ta librairie (sur le PC).

Chaque objet instancié de la scène (feux, panneaux, candélabres, arbres...) a un prototype nommé
comme l'asset définitif attendu (ex. feu_R11v, panneau_B14_50, arbre_platanus_acerifolia_grand ;
liste complète : assets/CAHIER_DES_CHARGES.md). Ce script cherche, dans le dossier de ta librairie,
un fichier USD portant ce nom :  <librairie>/**/<nom>/<nom>.usd(a|c|z)  ou  <librairie>/**/<nom>.usd(a|c|z)
(asset en mètres, Z vers le haut, pivot au pied, face avant vers +Y), puis écrit la couche
layers/substitutions.usda (la plus forte de la scène) qui :
  - référence l'asset dans le prototype et désactive le volume provisoire ;
  - recalcule l'échelle des instances : arbres -> hauteur mesurée (LiDAR) / hauteur de l'asset,
    mobilier -> 1.
Rien d'autre n'est modifié : supprimer layers/substitutions.usda revient à l'état initial.

Lancement (Python avec le module pxr : hython de Houdini 22, ou « pip install usd-core ») :
    hython substituer_assets.py --librairie "D:/Meylan/assets/lib"
    python substituer_assets.py --librairie ../../assets/lib --dry-run
Ensuite : recharger la scène dans Houdini (Sublayer LOP > Reload) ou Unreal (UsdStageActor > Reload).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, Vt

ICI = Path(__file__).resolve().parent
RACINE = ICI / "paquet_jardin_2026.usda" if (ICI / "paquet_jardin_2026.usda").exists() else ICI.parent / "paquet_jardin_2026.usda"
EXT = (".usd", ".usda", ".usdc", ".usdz")


def index_librairie(lib: Path):
    idx = {}
    for p in lib.rglob("*"):
        if p.suffix.lower() in EXT and (p.stem == p.parent.name or p.stem not in idx):
            idx.setdefault(p.stem, p)
            if p.stem == p.parent.name:
                idx[p.stem] = p
    return idx


def hauteur_asset(path: Path):
    st = Usd.Stage.Open(str(path))
    up = UsdGeom.GetStageUpAxis(st)
    mpu = UsdGeom.GetStageMetersPerUnit(st) or 1.0
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
        st.GetPseudoRoot()).ComputeAlignedRange()
    if bb.IsEmpty():
        return 1.0, up, mpu
    k = 2 if up == UsdGeom.Tokens.z else 1
    return float(bb.GetMax()[k] - bb.GetMin()[k]) * mpu, up, mpu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--librairie", required=True)
    ap.add_argument("--scene", default=str(RACINE))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    scene = Path(a.scene).resolve()
    lib = Path(a.librairie).resolve()
    idx = index_librairie(lib)
    print(f"{len(idx)} assets trouvés dans {lib}")

    root = Sdf.Layer.FindOrOpen(str(scene))
    sub_path = scene.parent / "layers" / "substitutions.usda"
    rel_sub = os.path.relpath(sub_path, scene.parent).replace("\\", "/")
    if rel_sub in root.subLayerPaths and not a.dry_run:      # on repart de la scène d'origine
        root.subLayerPaths.remove(rel_sub)
        root.Save()
    tmp = Usd.Stage.Open(str(scene))
    edit = None
    if not a.dry_run:
        if sub_path.exists():
            sub_path.unlink()
        edit = Usd.Stage.CreateNew(str(sub_path))
    remplaces, manquants = {}, set()
    for prim in tmp.Traverse():
        if not prim.IsA(UsdGeom.PointInstancer):
            continue
        pi = UsdGeom.PointInstancer(prim)
        protos = [Sdf.Path(t) for t in pi.GetPrototypesRel().GetTargets()]
        idxs = pi.GetProtoIndicesAttr().Get() or []
        scales = list(pi.GetScalesAttr().Get() or [Gf.Vec3f(1, 1, 1)] * len(idxs))
        pv = UsdGeom.PrimvarsAPI(prim)
        h = pv.GetPrimvar("hauteur_m").Get() if pv.HasPrimvar("hauteur_m") else None
        change = False
        for k, pp in enumerate(protos):
            nom = pp.name
            if nom not in idx:
                manquants.add(nom)
                continue
            asset = idx[nom]
            ha, up, mpu = hauteur_asset(asset)
            remplaces[nom] = str(asset)
            if a.dry_run:
                continue
            rel = os.path.relpath(asset, sub_path.parent).replace("\\", "/")
            over = edit.OverridePrim(pp)
            over.GetReferences().ClearReferences()
            ref = over.GetReferences()
            ref.AddReference(rel)
            if up != UsdGeom.Tokens.z or abs(mpu - 1.0) > 1e-6:   # asset Y-up ou en cm
                xf = UsdGeom.Xformable(over)
                if abs(mpu - 1.0) > 1e-6:
                    xf.AddScaleOp(opSuffix="unites").Set(Gf.Vec3f(mpu, mpu, mpu))
                if up != UsdGeom.Tokens.z:
                    xf.AddRotateXOp(opSuffix="vers_z_up").Set(90.0)
            for child in tmp.GetPrimAtPath(pp).GetChildren():           # volume provisoire
                if child.GetName().startswith("part"):
                    edit.OverridePrim(child.GetPath()).SetActive(False)
            for i, pidx in enumerate(idxs):
                if pidx == k:
                    s = (float(h[i]) / ha) if (h is not None and i < len(h) and h[i] > 0 and nom.startswith("arbre")) else 1.0
                    scales[i] = Gf.Vec3f(s, s, s)
                    change = True
        if change and not a.dry_run:
            UsdGeom.PointInstancer(edit.OverridePrim(prim.GetPath())).CreateScalesAttr().Set(Vt.Vec3fArray(scales))
    if not a.dry_run:
        edit.GetRootLayer().Save()
        root.subLayerPaths.insert(0, rel_sub)
        root.Save()
        print("couche écrite :", sub_path)
    print(f"remplacés ({len(remplaces)}) :")
    for n, p in sorted(remplaces.items()):
        print("  ", n, "<-", p)
    print(f"encore provisoires ({len(manquants)}) :", ", ".join(sorted(manquants)))


if __name__ == "__main__":
    main()
