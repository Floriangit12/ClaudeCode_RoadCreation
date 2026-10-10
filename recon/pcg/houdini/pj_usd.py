"""Écriture USD déterministe (pxr de Houdini 22) : scènes, maillages, PointInstancers.

Les couches sont construites en mémoire puis exportées en .usda (texte, diffable) : aucun
horodatage, ordre des prims fixé par le code. Repère local, mètres, Z haut.
"""
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

T = Sdf.ValueTypeNames


def scene(doc, racine="World", data=None):
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    w = UsdGeom.Xform.Define(st, f"/{racine}")
    st.SetDefaultPrim(w.GetPrim())
    lay = st.GetRootLayer()
    lay.documentation = doc
    if data:
        lay.customLayerData = data
    return st


def enregistrer(st, chemin):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists():
        chemin.unlink()
    st.GetRootLayer().Export(str(chemin))
    return chemin


def chemin_relatif(cible, depuis_fichier):
    """Chemin d'asset relatif (POSIX) de `cible` vu depuis le dossier de `depuis_fichier`."""
    import os
    try:
        return Path(os.path.relpath(Path(cible).resolve(), Path(depuis_fichier).resolve().parent)).as_posix()
    except ValueError:                       # autre lecteur : chemin absolu
        return Path(cible).resolve().as_posix()


def xform(st, path):
    return UsdGeom.Xform.Define(st, path)


def scope(st, path):
    return UsdGeom.Scope.Define(st, path)


def maillage(st, path, P, counts, indices, normales=None, st1=None, st1_interp="faceVarying",
             primvars=None, double_face=False, materiau_id=None):
    """Maillage polygonal. normales / st1 : faceVarying (une valeur par sommet de face) sauf
    st1_interp = 'vertex'. primvars : {nom: (valeurs, type Sdf, interpolation)}."""
    m = UsdGeom.Mesh.Define(st, path)
    P = np.asarray(P, dtype=np.float32)
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(P))
    m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.asarray(counts, dtype=np.int32)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(indices, dtype=np.int32)))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    m.CreateDoubleSidedAttr(bool(double_face))
    if len(P):
        m.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, P.min(axis=0))),
                                          Gf.Vec3f(*map(float, P.max(axis=0)))]))
    if normales is not None:
        m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(normales, dtype=np.float32)))
        m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying if len(normales) == len(indices)
                                  else UsdGeom.Tokens.vertex)
    api = UsdGeom.PrimvarsAPI(m)
    if st1 is not None:
        pv = api.CreatePrimvar("st1", T.TexCoord2fArray,
                               UsdGeom.Tokens.faceVarying if st1_interp == "faceVarying" else UsdGeom.Tokens.vertex)
        pv.Set(Vt.Vec2fArray.FromNumpy(np.asarray(st1, dtype=np.float32)))
    if materiau_id:
        api.CreatePrimvar("materiau_id", T.String, UsdGeom.Tokens.constant).Set(materiau_id)
    for nom, (val, typ, interp) in (primvars or {}).items():
        pv = api.CreatePrimvar(nom, typ, interp)
        pv.Set(val)
    return m


def lier(prim, materiau_path):
    UsdShade.MaterialBindingAPI.Apply(prim)
    UsdShade.MaterialBindingAPI(prim).Bind(UsdShade.Material(prim.GetStage().GetPrimAtPath(materiau_path))
                                           if prim.GetStage().GetPrimAtPath(materiau_path)
                                           else UsdShade.Material.Define(prim.GetStage(), materiau_path))


def lier_chemin(prim, materiau_path):
    """Liaison vers un matériau défini dans une autre couche (relation seule, sans 'over' de matériau)."""
    UsdShade.MaterialBindingAPI.Apply(prim)
    rel = prim.CreateRelationship("material:binding", False)
    rel.SetTargets([Sdf.Path(materiau_path)])


def instancer(st, path, protos, indices, positions, quats, echelles=None, ids=None, primvars=None):
    """PointInstancer. protos : [(nom_prim, chemin_asset | None, materiau_path | None)] ;
    quats : (N, 4) w, x, y, z ; primvars : {nom: (tableau numpy, type Sdf)} par instance."""
    pi = UsdGeom.PointInstancer.Define(st, path)
    cibles = []
    UsdGeom.Scope.Define(st, f"{path}/Prototypes")
    for nom, asset, mat in protos:
        pp = f"{path}/Prototypes/{nom}"
        x = UsdGeom.Xform.Define(st, pp)
        if asset:
            x.GetPrim().GetReferences().AddReference(asset)
        if mat:
            lier_chemin(x.GetPrim(), mat)
        cibles.append(Sdf.Path(pp))
    pi.CreatePrototypesRel().SetTargets(cibles)
    pi.CreateProtoIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(indices, dtype=np.int32)))
    pi.CreatePositionsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(positions, dtype=np.float32)))
    q = np.asarray(quats, dtype=np.float64)
    pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(float(a[0]), float(a[1]), float(a[2]), float(a[3])) for a in q]))
    if echelles is not None:
        pi.CreateScalesAttr(Vt.Vec3fArray.FromNumpy(np.asarray(echelles, dtype=np.float32)))
    if ids is not None:
        pi.CreateIdsAttr(Vt.Int64Array([int(i) for i in ids]))
    api = UsdGeom.PrimvarsAPI(pi)
    for nom, (val, typ) in (primvars or {}).items():
        pv = api.CreatePrimvar(nom, typ, UsdGeom.Tokens.vertex)
        pv.Set(val)
    return pi


def vt(tableau, typ):
    a = np.asarray(tableau)
    if typ == T.FloatArray:
        return Vt.FloatArray.FromNumpy(a.astype(np.float32))
    if typ == T.Float2Array:
        return Vt.Vec2fArray.FromNumpy(a.astype(np.float32))
    if typ in (T.Float3Array, T.Color3fArray):
        return Vt.Vec3fArray.FromNumpy(a.astype(np.float32))
    if typ == T.IntArray:
        return Vt.IntArray.FromNumpy(a.astype(np.int32))
    raise ValueError(typ)


def normales_sommets(P, tris):
    """Normales lissées par sommet (pondération par l'aire) d'un maillage triangulaire."""
    P = np.asarray(P, dtype=np.float64)
    a, b, c = P[tris[:, 0]], P[tris[:, 1]], P[tris[:, 2]]
    n = np.cross(b - a, c - a)
    N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, tris[:, k], n)
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    return N
