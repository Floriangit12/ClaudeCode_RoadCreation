"""Verificateur du contrat d'export Houdini -> UE (CONTRAT_EXPORT.md) : USD de geometrie de site.

Python + pxr seulement (hython, Python de l'editeur UE ou tout Python avec pxr). Usages :
    hython verifier_usd.py fichier.usd[a|c] [--json rapport.json]
    MCP pj_tools.run_python_file(path, '{"usd": "...", "json": "..."}')   (RESULT = rapport)
Controles (E = erreur bloquante, A = avertissement) :
  E1 metersPerUnit = 1, upAxis = Z, coordonnees du repere LOCAL (|x|,|y| < 5 km : pas de L93 brut)
  E2 normales par sommet de face (faceVarying ou vertex), unitaires, angle de rupture respecte
     (aretes de diedre > cusp + 5 deg cassees, < cusp - 5 deg lissees ; cusp = customData pj:cusp_deg, 30)
  E3 primvars:st texCoord2f[] (UV0 d'UE), en metres reels (mediane de sqrt(aire_uv / aire_3d) dans [0,9 ; 1,1]),
     aucune face d'aire 3D non nulle degeneree en UV ; transition : st1 seul est tolere (A, UE le met en UV0)
  E4 aucun autre texCoord2f que st et st1 (UE attribue les canaux UV par ordre lexicographique)
  E5 chaque face liee a un Material present dans la scene composee, dont le nom est un materiau_id
  E6 chaque Mesh sous un prim de kind component (hierarchie de modele valide) ; subdivisionScheme = none
  E7 pas de PointInstancer
  A  orientation leftHanded, doubleSided, extent absent
"""
from __future__ import annotations

import json
import math
import os
import sys

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade  # noqa: F401

ICI = os.path.dirname(os.path.abspath(__file__))
MATERIAUX = os.path.normpath(os.path.join(ICI, '..', '..', '..', '..', 'assets', 'specs', 'materiaux_sol.json'))
CUSP_DEFAUT = 30.0
MARGE_CUSP = 5.0
TOL_NORME = 1e-3


def _ids_materiaux(chemin=MATERIAUX):
    with open(chemin, encoding='utf-8') as f:
        return set(json.load(f)['materiaux'])


def _sous(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vect(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norme(a):
    return math.sqrt(sum(x * x for x in a))


def _angle(a, b):
    na, nb = _norme(a), _norme(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (na * nb)))))


def _valeurs_fv(primvar_ou_attr, interp, counts, indices, nb_points):
    """Valeurs par sommet de face (liste alignee sur faceVertexIndices) ou None si interpolation non geree."""
    if isinstance(primvar_ou_attr, UsdGeom.Primvar):
        vals = primvar_ou_attr.ComputeFlattened()
    else:
        vals = primvar_ou_attr.Get()
    if vals is None:
        return None
    vals = [tuple(v) for v in vals]
    if interp == UsdGeom.Tokens.faceVarying and len(vals) == len(indices):
        return vals
    if interp in (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying) and len(vals) == nb_points:
        return [vals[i] for i in indices]
    return None


def verifier_mesh(prim, ids_mat, cusp):
    m = UsdGeom.Mesh(prim)
    r = {'prim': str(prim.GetPath()), 'erreurs': [], 'avertissements': []}
    E, A = r['erreurs'].append, r['avertissements'].append
    xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    pts = [tuple(xf.Transform(p)) for p in (m.GetPointsAttr().Get() or [])]
    counts = list(m.GetFaceVertexCountsAttr().Get() or [])
    indices = list(m.GetFaceVertexIndicesAttr().Get() or [])
    r['faces'], r['points'] = len(counts), len(pts)
    if not pts or not counts:
        E('E6 mesh vide')
        return r
    if max(max(abs(p[0]), abs(p[1])) for p in pts) > 5000.0:
        E('E1 coordonnees > 5 km : repere local attendu (L93 - O), pas le L93 brut')
    if m.GetSubdivisionSchemeAttr().Get() != UsdGeom.Tokens.none:
        E(f'E6 subdivisionScheme = {m.GetSubdivisionSchemeAttr().Get()} (none exige : sinon les normales sont ignorees)')
    sens = 1.0
    if m.GetOrientationAttr().Get() == UsdGeom.Tokens.leftHanded:
        sens = -1.0
        A('A orientation leftHanded (accepte par UE, rightHanded conseille)')
    if m.GetDoubleSidedAttr().Get():
        A('A doubleSided = true (sol et bordures : faux attendu)')
    if not m.GetExtentAttr().HasAuthoredValue():
        A('A extent absent')
    # faces (sommets de face) et normales geometriques
    debut, k = [], 0
    for c in counts:
        debut.append(k)
        k += c
    if k != len(indices):
        E('E6 topologie incoherente (somme faceVertexCounts != len(faceVertexIndices))')
        return r
    nf = []
    for f, c in enumerate(counts):
        vs = [pts[indices[debut[f] + i]] for i in range(c)]
        n = (0.0, 0.0, 0.0)
        for i in range(1, c - 1):
            t = _vect(_sous(vs[i], vs[0]), _sous(vs[i + 1], vs[0]))
            n = (n[0] + t[0], n[1] + t[1], n[2] + t[2])
        nf.append((sens * n[0], sens * n[1], sens * n[2]))   # 2 x aire vectorielle, cote face avant
    # E2 normales
    pv = UsdGeom.PrimvarsAPI(prim)
    nprim = pv.GetPrimvar('normals')
    if nprim and nprim.HasAuthoredValue():
        nsrc, ninterp = nprim, nprim.GetInterpolation()
    elif m.GetNormalsAttr().HasAuthoredValue():
        nsrc, ninterp = m.GetNormalsAttr(), m.GetNormalsInterpolation()
    else:
        nsrc, ninterp = None, None
    r['normales'] = ninterp
    if nsrc is None:
        E('E2 normales absentes')
    else:
        nfv = _valeurs_fv(nsrc, ninterp, counts, indices, len(pts))
        if nfv is None:
            E(f'E2 normales : interpolation {ninterp} ou taille non geree (faceVarying ou vertex attendu)')
        else:
            mauvaises = sum(1 for n in nfv if not all(math.isfinite(x) for x in n) or abs(_norme(n) - 1.0) > TOL_NORME)
            if mauvaises:
                E(f'E2 {mauvaises} normales non unitaires ou non finies')
            if ninterp == UsdGeom.Tokens.faceVarying and sum(1 for f in range(len(counts)) for i in range(counts[f])
                                                              if _angle(nfv[debut[f] + i], nf[f]) > 90.0):
                E('E2 normales opposees a l enroulement des faces (orientation)')
            # angle de rupture : aretes partagees par 2 faces
            aretes = {}
            for f, c in enumerate(counts):
                for i in range(c):
                    a, b = indices[debut[f] + i], indices[debut[f] + (i + 1) % c]
                    aretes.setdefault((min(a, b), max(a, b)), []).append((f, i, (i + 1) % c))
            vives_lissees = douces_cassees = 0
            for (a, b), fs in aretes.items():
                if len(fs) != 2:
                    continue
                (f1, i1, j1), (f2, i2, j2) = fs
                diedre = _angle(nf[f1], nf[f2])
                # normale de chaque face au sommet a (et b) de l'arete
                n1 = {indices[debut[f1] + i1]: nfv[debut[f1] + i1], indices[debut[f1] + j1]: nfv[debut[f1] + j1]}
                n2 = {indices[debut[f2] + i2]: nfv[debut[f2] + i2], indices[debut[f2] + j2]: nfv[debut[f2] + j2]}
                ecart = max(_angle(n1[v], n2[v]) for v in (a, b))
                if diedre > cusp + MARGE_CUSP and ecart < 1.0:
                    vives_lissees += 1
                elif diedre < cusp - MARGE_CUSP and ecart > 1.0:
                    douces_cassees += 1
            r['aretes_vives_lissees'], r['aretes_douces_cassees'] = vives_lissees, douces_cassees
            if vives_lissees:
                E(f'E2 {vives_lissees} aretes de diedre > {cusp + MARGE_CUSP:.0f} deg lissees (angle de rupture non applique)')
            if douces_cassees:
                A(f'A {douces_cassees} aretes de diedre < {cusp - MARGE_CUSP:.0f} deg cassees')
    # E3 / E4 UV
    tex = [p for p in pv.GetPrimvars() if p.GetTypeName() == Sdf.ValueTypeNames.TexCoord2fArray]
    autres = sorted(p.GetPrimvarName() for p in tex if p.GetPrimvarName() not in ('st', 'st1'))
    if autres:
        E(f'E4 texCoord2f hors st/st1 : {autres}')
    r['uv'] = sorted(p.GetPrimvarName() for p in tex)
    st = pv.GetPrimvar('st')
    if (not st or not st.HasAuthoredValue()) and pv.GetPrimvar('st1') and pv.GetPrimvar('st1').HasAuthoredValue():
        st = pv.GetPrimvar('st1')                        # transition : UE affecte st1 seul a UV0
        A('A UV metriques en st1 seul (UE : UV0 ; nom canonique st, cf. CONTRAT_EXPORT.md)')
    if not st or not st.HasAuthoredValue():
        E('E3 primvars:st absent')
    elif st.GetTypeName() != Sdf.ValueTypeNames.TexCoord2fArray:
        E(f'E3 primvars:{st.GetPrimvarName()} de type {st.GetTypeName()} (texCoord2f[] attendu)')
    else:
        uv = _valeurs_fv(st, st.GetInterpolation(), counts, indices, len(pts))
        if uv is None:
            E(f'E3 st : interpolation {st.GetInterpolation()} non geree (faceVarying ou vertex attendu)')
        else:
            rapports, degen = [], 0
            for f, c in enumerate(counts):
                a3 = 0.5 * _norme(nf[f])
                u = [uv[debut[f] + i] for i in range(c)]
                auv = 0.5 * abs(sum(u[i][0] * u[(i + 1) % c][1] - u[(i + 1) % c][0] * u[i][1] for i in range(c)))
                if a3 > 1e-8:
                    if auv < 1e-10 or not all(math.isfinite(x) for p in u for x in p):
                        degen += 1
                    else:
                        rapports.append(math.sqrt(auv / a3))
            rapports.sort()
            med = rapports[len(rapports) // 2] if rapports else 0.0
            r['st_echelle_mediane'], r['st_faces_degenerees'] = round(med, 4), degen
            if degen:
                E(f'E3 {degen} faces degenerees en UV (tangentes impossibles)')
            if not 0.9 <= med <= 1.1:
                E(f'E3 st pas en metres : echelle mediane {med:.3f} (1 attendu)')
    # E5 materiaux (liaison directe du mesh et des GeomSubsets materialBind) ; cible absente = erreur explicite
    for q in [prim] + [s_.GetPrim() for s_ in UsdShade.MaterialBindingAPI(prim).GetMaterialBindSubsets()]:
        rel = q.GetRelationship('material:binding')
        for cible in (rel.GetTargets() if rel else []):
            if not prim.GetStage().GetPrimAtPath(cible):
                E(f'E5 liaison vers {cible} absent de la scene composee (definir /World/Looks ou sous-couche)')
    api = UsdShade.MaterialBindingAPI(prim)
    subsets = UsdShade.MaterialBindingAPI(prim).GetMaterialBindSubsets()
    couvert = set()
    mats = []
    for s in subsets:
        mat = UsdShade.MaterialBindingAPI(s.GetPrim()).ComputeBoundMaterial()[0]
        mats.append(mat.GetPrim().GetName() if mat else None)
        couvert.update(s.GetIndicesAttr().Get() or [])
    mat = api.ComputeBoundMaterial()[0]
    if len(couvert) < len(counts):
        mats.append(mat.GetPrim().GetName() if mat else None)
    r['materiaux'] = sorted(set(str(x) for x in mats))
    for x in set(mats):
        if x is None:
            E('E5 faces sans materiau lie')
        elif x not in ids_mat:
            E(f'E5 materiau {x!r} absent de materiaux_sol.json (nom du Material = materiau_id)')
    # E6 kind
    p, comp = prim, None
    while p and p.GetPath() != Sdf.Path.absoluteRootPath:
        if Usd.ModelAPI(p).GetKind() == 'component':
            comp = p
            break
        p = p.GetParent()
    r['component'] = str(comp.GetPath()) if comp else None
    if comp is None:
        E('E6 aucun ancetre de kind component')
    elif not comp.IsModel():
        E(f'E6 hierarchie de modele invalide au-dessus de {comp.GetPath()} (ancetres group/assembly attendus)')
    return r


def verifier(chemin: str, chemin_materiaux: str = MATERIAUX) -> dict:
    st = Usd.Stage.Open(chemin)
    if st is None:
        raise RuntimeError(f'ouverture impossible : {chemin}')
    ids = _ids_materiaux(chemin_materiaux)
    res = {'usd': chemin, 'erreurs': [], 'avertissements': [], 'meshes': []}
    mpu, up = UsdGeom.GetStageMetersPerUnit(st), UsdGeom.GetStageUpAxis(st)
    res['stage'] = {'metersPerUnit': mpu, 'upAxis': str(up), 'defaultPrim': str(st.GetDefaultPrim().GetPath())
                    if st.GetDefaultPrim() else None}
    if abs(mpu - 1.0) > 1e-9:
        res['erreurs'].append(f'E1 metersPerUnit = {mpu} (1 attendu)')
    if up != UsdGeom.Tokens.z:
        res['erreurs'].append(f'E1 upAxis = {up} (Z attendu)')
    cusp = float((st.GetRootLayer().customLayerData or {}).get('pj:cusp_deg', CUSP_DEFAUT))
    res['cusp_deg'] = cusp
    for prim in st.Traverse():
        if prim.IsA(UsdGeom.PointInstancer):
            res['erreurs'].append(f'E7 PointInstancer interdit : {prim.GetPath()} (points -> pj_points/0.1)')
        elif prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputePurpose() in (UsdGeom.Tokens.default_,
                                                                                     UsdGeom.Tokens.render):
            r = verifier_mesh(prim, ids, cusp)
            res['meshes'].append(r)
            res['erreurs'] += [f'{r["prim"]} : {e}' for e in r['erreurs']]
            res['avertissements'] += [f'{r["prim"]} : {a}' for a in r['avertissements']]
    if not res['meshes']:
        res['erreurs'].append('E6 aucun Mesh')
    res['ok'] = not res['erreurs']
    return res


def _principal(argv):
    chemin = argv[0]
    rapport = verifier(chemin)
    if '--json' in argv:
        with open(argv[argv.index('--json') + 1], 'w', encoding='utf-8') as f:
            json.dump(rapport, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rapport.items() if k != 'meshes'}, ensure_ascii=False, indent=1)[:6000])
    return 0 if rapport['ok'] else 1


if 'ARGS' in globals():                                   # pj_tools.run_python_file
    RESULT = verifier(ARGS['usd'], ARGS.get('materiaux', MATERIAUX))  # noqa: F821
    if ARGS.get('json'):  # noqa: F821
        with open(ARGS['json'], 'w', encoding='utf-8') as _f:  # noqa: F821
            json.dump(RESULT, _f, ensure_ascii=False, indent=1)
    RESULT = {k: (v if k != 'meshes' else v[:50]) for k, v in RESULT.items()}
elif __name__ == '__main__':
    sys.exit(_principal(sys.argv[1:]))
