"""Echantillon de reference du contrat d'export Houdini -> UE (CONTRAT_EXPORT.md), ecrit avec pxr.

Trois elements de bordure (profil T2 simplifie, chanfrein 15 mm, 0,994 m + joints de 6 mm, UV depliees en metres)
et une dalle de trottoir a devers et ondulation legere (UV planaires en metres, 2 materiaux par GeomSubset),
places vers x = -100 m, y = -120 m (repere local) pour eprouver la precision des UV.
Usages : hython echantillon_contrat.py sortie.usda   |   MCP pj_tools.run_python_file(path, '{"sortie": "..."}')
"""
from __future__ import annotations

import json
import math
import os
import sys

from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt

ICI = os.path.dirname(os.path.abspath(__file__))
MATERIAUX = os.path.normpath(os.path.join(ICI, '..', '..', '..', '..', 'assets', 'specs', 'materiaux_sol.json'))
CUSP_DEG = 30.0
X0, Y0 = -100.0, -120.0
PROFIL = [(0.0, 0.0), (0.15, 0.0), (0.15, 0.25), (0.015, 0.25), (0.0, 0.235)]   # (t lateral, z), sens trigo vu de +x


def normales_cusp(pts, faces, cusp=CUSP_DEG):
    """Normales par sommet de face : moyenne (ponderee par l'aire) des faces voisines a moins de cusp degres."""
    nf = []
    for f in faces:
        n = Gf.Vec3d(0, 0, 0)
        for i in range(1, len(f) - 1):
            n += Gf.Cross(Gf.Vec3d(*pts[f[i]]) - Gf.Vec3d(*pts[f[0]]), Gf.Vec3d(*pts[f[i + 1]]) - Gf.Vec3d(*pts[f[0]]))
        nf.append(n)
    autour = {}
    for k, f in enumerate(faces):
        for v in f:
            autour.setdefault(v, []).append(k)
    c = math.cos(math.radians(cusp))
    out = []
    for k, f in enumerate(faces):
        u = nf[k].GetNormalized()
        for v in f:
            s = Gf.Vec3d(0, 0, 0)
            for j in autour[v]:
                if Gf.Dot(nf[j].GetNormalized(), u) >= c:
                    s += nf[j]
            out.append(Gf.Vec3f(s.GetNormalized()))
    return out


def bordure(n_elem=3, longueur=0.994, joint=0.006):
    pts, faces, uv = [], [], []
    perim = [0.0]
    for k in range(len(PROFIL)):
        a, b = PROFIL[k], PROFIL[(k + 1) % len(PROFIL)]
        perim.append(perim[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    for e in range(n_elem):
        xa = X0 + e * (longueur + joint)
        xb = xa + longueur
        base = len(pts)
        np_ = len(PROFIL)
        pts += [(xa, Y0 + t, z) for t, z in PROFIL] + [(xb, Y0 + t, z) for t, z in PROFIL]
        for k in range(np_):                                   # faces laterales : u = abscisse x, v = perimetre
            k2 = (k + 1) % np_
            faces.append([base + k, base + k2, base + np_ + k2, base + np_ + k])
            uv += [(xa, perim[k]), (xa, perim[k + 1]), (xb, perim[k + 1]), (xb, perim[k])]
        faces.append([base + np_ + k for k in range(np_)])                       # about +x
        uv += [(Y0 + t, z) for t, z in PROFIL]
        faces.append([base + k for k in reversed(range(np_))])                   # about -x
        uv += [(-(Y0 + t), z) for t, z in reversed(PROFIL)]
    return pts, faces, uv


def dalle(nx=12, ny=8, lx=3.0, ly=2.0):
    def z(x, y):
        return 0.25 - 0.02 * (y - Y0 - 0.15) + 0.01 * math.sin(2.0 * (x - X0))
    xs = [X0 + lx * i / nx for i in range(nx + 1)]
    ys = [Y0 + 0.15 + ly * j / ny for j in range(ny + 1)]
    pts = [(x, y, z(x, y)) for y in ys for x in xs]
    faces, uv, mat = [], [], []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            f = [a, a + 1, a + nx + 2, a + nx + 1]
            faces.append(f)
            uv += [(pts[v][0], pts[v][1]) for v in f]                 # st = (x, y) en metres
            mat.append(0 if i < nx // 2 else 1)
    return pts, faces, uv, mat


def materiau(st, chemin, mid, spec):
    m = UsdShade.Material.Define(st, chemin)
    ps = UsdShade.Shader.Define(st, f'{chemin}/Apercu')
    ps.CreateIdAttr('UsdPreviewSurface')
    ps.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*spec['albedo_cible_lineaire']))
    ps.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(float(spec['rugosite']['valeur']))
    m.CreateSurfaceOutput().ConnectToSource(ps.CreateOutput('surface', Sdf.ValueTypeNames.Token))
    ue = UsdShade.Shader.Define(st, f'{chemin}/Unreal')          # contexte de rendu 'unreal' : MI_<materiau_id>
    ue.SetSourceAsset(Sdf.AssetPath(f'/Game/PJ/Materials/MI_{mid}.MI_{mid}'), 'unreal')
    m.CreateSurfaceOutput('unreal').ConnectToSource(ue.CreateOutput('out', Sdf.ValueTypeNames.Token))
    return m


def mesh(st, chemin, pts, faces, uv, liaisons):
    g = UsdGeom.Mesh.Define(st, chemin)
    g.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
    g.CreateFaceVertexCountsAttr(Vt.IntArray([len(f) for f in faces]))
    g.CreateFaceVertexIndicesAttr(Vt.IntArray([v for f in faces for v in f]))
    g.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    g.CreateOrientationAttr(UsdGeom.Tokens.rightHanded)
    g.CreateDoubleSidedAttr(False)
    g.CreateNormalsAttr(Vt.Vec3fArray(normales_cusp(pts, faces)))
    g.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    pv = UsdGeom.PrimvarsAPI(g).CreatePrimvar('st', Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
    pv.Set(Vt.Vec2fArray([Gf.Vec2f(*p) for p in uv]))
    g.CreateExtentAttr(UsdGeom.PointBased.ComputeExtent(g.GetPointsAttr().Get()))
    api = UsdShade.MaterialBindingAPI.Apply(g.GetPrim())
    if len(liaisons) == 1:
        api.Bind(liaisons[0][1])
    else:
        for nom, mat, idx in liaisons:
            s = api.CreateMaterialBindSubset(nom, Vt.IntArray(idx), UsdGeom.Tokens.face)
            UsdShade.MaterialBindingAPI.Apply(s.GetPrim()).Bind(mat)
        api.SetMaterialBindSubsetsFamilyType(UsdGeom.Tokens.partition)
    return g


def ecrire(sortie: str) -> dict:
    with open(MATERIAUX, encoding='utf-8') as f:
        specs = json.load(f)['materiaux']
    st = Usd.Stage.CreateNew(sortie) if not os.path.exists(sortie) else Usd.Stage.Open(sortie)
    st.GetRootLayer().Clear()
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    st.GetRootLayer().customLayerData = {'pj:contrat': 'pj_usd/0.1', 'pj:cusp_deg': CUSP_DEG,
                                         'pj:source': 'recon/pcg/ue/contrat/echantillon_contrat.py'}
    monde = UsdGeom.Xform.Define(st, '/World')
    st.SetDefaultPrim(monde.GetPrim())
    Usd.ModelAPI(monde).SetKind(Kind.Tokens.assembly)
    UsdGeom.Scope.Define(st, '/World/Looks')
    mats = {mid: materiau(st, f'/World/Looks/{mid}', mid, specs[mid])
            for mid in ('beton_bordure_gris', 'enrobe_trottoir', 'beton_balaye')}
    for groupe in ('Bordures', 'Sol'):
        Usd.ModelAPI(UsdGeom.Xform.Define(st, f'/World/{groupe}')).SetKind(Kind.Tokens.group)
    k = UsdGeom.Xform.Define(st, '/World/Bordures/K_essai_0001')
    Usd.ModelAPI(k).SetKind(Kind.Tokens.component)
    p, f, uv = bordure()
    mesh(st, '/World/Bordures/K_essai_0001/geo', p, f, uv, [('beton_bordure_gris', mats['beton_bordure_gris'], None)])
    s = UsdGeom.Xform.Define(st, '/World/Sol/S_essai_0001')
    Usd.ModelAPI(s).SetKind(Kind.Tokens.component)
    p, f, uv, m = dalle()
    mesh(st, '/World/Sol/S_essai_0001/geo', p, f, uv,
         [('enrobe_trottoir', mats['enrobe_trottoir'], [i for i, x in enumerate(m) if x == 0]),
          ('beton_balaye', mats['beton_balaye'], [i for i, x in enumerate(m) if x == 1])])
    st.GetRootLayer().Save()
    return {'usd': sortie, 'prims': [str(x.GetPath()) for x in st.Traverse()]}


if 'ARGS' in globals():                                   # pj_tools.run_python_file
    RESULT = ecrire(ARGS['sortie'])  # noqa: F821
elif __name__ == '__main__':
    print(ecrire(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, 'echantillon_contrat.usda')))
