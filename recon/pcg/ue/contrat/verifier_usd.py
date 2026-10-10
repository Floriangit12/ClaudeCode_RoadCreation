"""Verificateur du contrat d'export Houdini -> UE (CONTRAT_EXPORT.md) : USD de geometrie de site.

Python + pxr seulement (hython, Python de l'editeur UE ou tout Python avec pxr). Usages :
    hython verifier_usd.py fichier.usd[a|c] [--json rapport.json] [--sol sol.usda]
    MCP pj_tools.run_python_file(path, '{"usd": "...", "json": "..."}')   (RESULT = rapport)
Controles (E = erreur bloquante, A = avertissement) :
  E1 metersPerUnit = 1, upAxis = Z, coordonnees du repere LOCAL (|x|,|y| < 100 km : pas de L93 brut, x > 900 km ;
     le relief lointain du contexte va jusqu'a 35 km)
  E2 normales par sommet de face (faceVarying ou vertex), unitaires, angle de rupture respecte
     (aretes de diedre > cusp + 5 deg cassees, < cusp - 5 deg lissees ; cusp = customData pj:cusp_deg, 30)
  E3 primvars:st texCoord2f[] (UV0 d'UE), en metres reels (mediane de sqrt(aire_uv / aire_3d) dans [0,9 ; 1,1]),
     aucune face d'aire 3D non nulle degeneree en UV ; transition : st1 seul est tolere (A, UE le met en UV0)
  E4 aucun autre texCoord2f que st et st1 (UE attribue les canaux UV par ordre lexicographique)
  E5 chaque face liee a un Material present dans la scene composee, dont le nom est un materiau_id
     (materiaux_sol.json ou materiau maison MATERIAUX_MAISON) ; liaison resolue comme l'import UE :
     finalite preview (material:binding:preview), repli allPurpose (material:binding)
  E6 chaque Mesh sous un prim de kind component (hierarchie de modele valide) ; subdivisionScheme = none
  E7 pas de PointInstancer
  E8 sol fabrique (/World/PJ_Sol) : aucun triangle de plus de 45 deg avec un denivele de plus de 3 cm hors talus
     (noue_plantee) et hors bord de couche (0,5 m : raccord au contexte v1) ; revue UE du 10/10, pointes de sol aux
     fins de bordure
  E9 (option --sol SOL.usda, couche portant .../bev_dalles) : dessus des dalles podotactiles 3D a moins de 5 mm du
     sol a 3 cm hors du module (affleurement)
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
# materiaux maison sans entree dans materiaux_sol.json (recon/pcg/houdini/pj_materiaux.py CONSTANTS et eclats ;
# MI_<id> crees dans UE par recon/pcg/ue/pilote/ue/materiaux_maison.py)
MATERIAUX_MAISON = {'mortier_joint', 'mortier_clair', 'bitume_pontage', 'herbe_touffe', 'eclat_brf', 'eclat_gravier'}
# materiaux du contexte v1 (recon/pcg/ue/contexte/preparer_usd.py ; MI crees par contexte/ue/materiaux_contexte.py,
# peintures par materiaux/, toits CARLA) et maillages d'echantillonnage PCG (PJ_Neutre)
MATERIAUX_MAISON |= {'bordure_v1', 'toit_terrasse', 'toit_pentes', 'PJ_Neutre', 'PJ_Facade_annexe', 'PJ_Facade_commerce',
                     'PJ_Facade_enduit_blanc', 'PJ_Facade_enduit_beige', 'PJ_Facade_enduit_gris', 'PJ_Facade_enduit_ocre'}
MATERIAUX_MAISON |= {f'PJ_Peinture_{c}_u{u}' for c in ('blanc', 'jaune') for u in ('0', '1', '2', '3', 'F')}
MATERIAUX_MAISON |= {'PJ_Relief', 'PJ_Contexte_Lointain'}    # relief et sol lointains (contexte/relief_usd.py)
SOL_RACINE = '/World/PJ_Sol'
SOL_TALUS = {'noue_plantee'}
PENTE_E8_DEG, DZ_E8_M, BORD_E8_M = 45.0, 0.03, 0.5
AFFLEUREMENT_E9_M = 0.005
FINALITE_UE = UsdShade.Tokens.preview      # pj_tools.import_usd : material_purpose = preview (repli allPurpose)
CUSP_DEFAUT = 30.0
MARGE_CUSP = 5.0
TOL_NORME = 1e-3


def _ids_materiaux(chemin=MATERIAUX):
    with open(chemin, encoding='utf-8') as f:
        return set(json.load(f)['materiaux']) | MATERIAUX_MAISON


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
    if max(max(abs(p[0]), abs(p[1])) for p in pts) > 100000.0:     # L93 brut : x > 900 km (relief lointain : 35 km)
        E('E1 coordonnees > 100 km : repere local attendu (L93 - O), pas le L93 brut')
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
    # E5 materiaux (liaison du mesh, de ses ancetres et des GeomSubsets materialBind, resolue comme l'import UE :
    # finalite preview puis allPurpose) ; cible absente = erreur explicite
    p_ = prim
    while p_ and p_.GetPath() != Sdf.Path.absoluteRootPath:
        for q in [p_] + ([s_.GetPrim() for s_ in UsdShade.MaterialBindingAPI(prim).GetMaterialBindSubsets()]
                         if p_ == prim else []):
            rel = q.GetRelationship('material:binding:preview')
            if not (rel and rel.GetTargets()):
                rel = q.GetRelationship('material:binding')
            for cible in (rel.GetTargets() if rel else []):
                if not prim.GetStage().GetPrimAtPath(cible):
                    E(f'E5 liaison vers {cible} absent de la scene composee (definir /World/Looks ou sous-couche)')
        p_ = p_.GetParent()
    api = UsdShade.MaterialBindingAPI(prim)
    subsets = UsdShade.MaterialBindingAPI(prim).GetMaterialBindSubsets()
    couvert = set()
    mats = []
    for s in subsets:
        mat = UsdShade.MaterialBindingAPI(s.GetPrim()).ComputeBoundMaterial(FINALITE_UE)[0]
        mats.append(mat.GetPrim().GetName() if mat else None)
        couvert.update(s.GetIndicesAttr().Get() or [])
    mat = api.ComputeBoundMaterial(FINALITE_UE)[0]
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


def verifier(chemin: str, chemin_materiaux: str = MATERIAUX, chemin_sol: str | None = None) -> dict:
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
    sol = st.GetPrimAtPath(SOL_RACINE)
    if sol and sol.IsValid():
        res['pentes_sol'] = verifier_pentes_sol(st)
        if res['pentes_sol']['triangles']:
            res['erreurs'].append(f"E8 {res['pentes_sol']['triangles']} triangles de sol > {PENTE_E8_DEG:.0f} deg et "
                                  f"> {DZ_E8_M * 100:.0f} cm de denivele hors talus et hors bord (ex. "
                                  f"{res['pentes_sol']['exemples'][:3]})")
    if chemin_sol:
        res['bev'] = verifier_bev(st, chemin_sol)
        if res['bev'].get('au_dela'):
            res['erreurs'].append(f"E9 {res['bev']['au_dela']} sondes de dalle BEV a plus de "
                                  f"{AFFLEUREMENT_E9_M * 1000:.0f} mm du sol (max {res['bev']['max_mm']} mm)")
    res['ok'] = not res['erreurs']
    return res


def _triangles_monde(prim):
    m = UsdGeom.Mesh(prim)
    xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    pts = [tuple(xf.Transform(p)) for p in (m.GetPointsAttr().Get() or [])]
    counts = list(m.GetFaceVertexCountsAttr().Get() or [])
    indices = list(m.GetFaceVertexIndicesAttr().Get() or [])
    out, k = [], 0
    for c in counts:
        f = indices[k:k + c]
        k += c
        out += [(pts[f[0]], pts[f[i]], pts[f[i + 1]]) for i in range(1, c - 1)]
    return out


def verifier_pentes_sol(st):
    """E8 : triangles raides du sol fabrique (pente, denivele), hors talus et hors bord de couche."""
    tris = []
    for prim in Usd.PrimRange(st.GetPrimAtPath(SOL_RACINE)):
        if prim.IsA(UsdGeom.Mesh) and prim.GetName() not in SOL_TALUS:
            tris += [(prim.GetName(), t) for t in _triangles_monde(prim)]
    if not tris:
        return {'triangles': 0, 'exemples': []}
    xs = [p[0] for _, t in tris for p in t]
    ys = [p[1] for _, t in tris for p in t]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mauvais = []
    for nom, (a, b, c) in tris:
        n = _vect(_sous(b, a), _sous(c, a))
        ln = _norme(n)
        if ln < 4e-4:                                     # aire < 2 cm2
            continue
        pente = math.degrees(math.acos(min(1.0, abs(n[2]) / ln)))
        dz = max(a[2], b[2], c[2]) - min(a[2], b[2], c[2])
        g = ((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3)
        if pente > PENTE_E8_DEG and dz > DZ_E8_M and min(g[0] - x0, x1 - g[0], g[1] - y0, y1 - g[1]) > BORD_E8_M:
            mauvais.append({'mesh': nom, 'xy': [round(g[0], 2), round(g[1], 2)], 'pente_deg': round(pente, 1),
                            'dz_m': round(dz, 3)})
    mauvais.sort(key=lambda m: -m['dz_m'])
    return {'triangles': len(mauvais), 'exemples': mauvais[:20], 'seuils': [PENTE_E8_DEG, DZ_E8_M, BORD_E8_M]}


def verifier_bev(st, chemin_sol):
    """E9 : affleurement des dalles BEV 3D (PointInstancer .../bev_dalles ; prototype : dessous a z = 0, dessus a
    z = e, demi-cote h) contre le sol (sol.usda) a 3 cm hors du module, joints entre modules exclus (sol
    bev_podotactile)."""
    pi = next((UsdGeom.PointInstancer(p) for p in st.Traverse() if p.IsA(UsdGeom.PointInstancer)
               and p.GetName() == 'bev_dalles'), None)
    if pi is None:
        return {'dalles': 0}
    proto = UsdGeom.Mesh(next(p for p in Usd.PrimRange(st.GetPrimAtPath(pi.GetPrototypesRel().GetTargets()[0]))
                              if p.IsA(UsdGeom.Mesh)))
    pp = proto.GetPointsAttr().Get()
    h = max(abs(p[0]) for p in pp)
    e = max(p[2] for p in pp if abs(p[0]) > h - 1e-4)            # chant : dessus de la dalle hors plots
    sol = Usd.Stage.Open(chemin_sol)
    tris = []
    for prim in Usd.PrimRange(sol.GetPrimAtPath(SOL_RACINE)):
        if prim.IsA(UsdGeom.Mesh):
            tris += [(prim.GetName(), t) for t in _triangles_monde(prim)]

    def z_sol(q):
        for nom, (a, b, c) in tris:
            if max(a[0], b[0], c[0]) < q[0] or min(a[0], b[0], c[0]) > q[0] or                max(a[1], b[1], c[1]) < q[1] or min(a[1], b[1], c[1]) > q[1]:
                continue
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-14:
                continue
            l1 = ((b[1] - c[1]) * (q[0] - c[0]) + (c[0] - b[0]) * (q[1] - c[1])) / d
            l2 = ((c[1] - a[1]) * (q[0] - c[0]) + (a[0] - c[0]) * (q[1] - c[1])) / d
            if l1 >= -1e-9 and l2 >= -1e-9 and 1 - l1 - l2 >= -1e-9:
                return nom, l1 * a[2] + l2 * b[2] + (1 - l1 - l2) * c[2]
        return None, None
    pos, ori = pi.GetPositionsAttr().Get(), pi.GetOrientationsAttr().Get()
    ecarts = []
    for p, q in zip(pos, ori):
        rot = Gf.Rotation(Gf.Quatd(q.GetReal(), Gf.Vec3d(q.GetImaginary())))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            haut = Gf.Vec3d(p) + rot.TransformDir(Gf.Vec3d(dx * h, dy * h, e))
            dehors = Gf.Vec3d(p) + rot.TransformDir(Gf.Vec3d(dx * (h + 0.03), dy * (h + 0.03), 0.0))
            nom, z = z_sol((dehors[0], dehors[1]))
            if z is None or nom == 'bev_podotactile':
                continue
            ecarts.append(haut[2] - z)
    au_dela = [x for x in ecarts if abs(x) > AFFLEUREMENT_E9_M]
    return {'dalles': len(pos), 'sondes': len(ecarts), 'au_dela': len(au_dela),
            'max_mm': round(1000 * max((abs(x) for x in ecarts), default=0.0), 1),
            'moyen_mm': round(1000 * sum(ecarts) / max(len(ecarts), 1), 1)}


def _principal(argv):
    chemin = argv[0]
    rapport = verifier(chemin, chemin_sol=argv[argv.index('--sol') + 1] if '--sol' in argv else None)
    if '--json' in argv:
        with open(argv[argv.index('--json') + 1], 'w', encoding='utf-8') as f:
            json.dump(rapport, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rapport.items() if k != 'meshes'}, ensure_ascii=False, indent=1)[:6000])
    return 0 if rapport['ok'] else 1


if 'ARGS' in globals():                                   # pj_tools.run_python_file
    RESULT = verifier(ARGS['usd'], ARGS.get('materiaux', MATERIAUX), ARGS.get('sol'))  # noqa: F821
    if ARGS.get('json'):  # noqa: F821
        with open(ARGS['json'], 'w', encoding='utf-8') as _f:  # noqa: F821
            json.dump(RESULT, _f, ensure_ascii=False, indent=1)
    RESULT = {k: (v if k != 'meshes' else v[:50]) for k, v in RESULT.items()}
elif __name__ == '__main__':
    sys.exit(_principal(sys.argv[1:]))
