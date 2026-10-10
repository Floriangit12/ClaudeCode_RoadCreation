"""pj_contexte : masque du paquet v1 dans l'emprise pilote (couche de surcharge, paquet v1 intact).

Le paquet v1 (recon/out/paquet_jardin/package, LECTURE SEULE) reste le contexte hors de la zone
pilote. La couche contexte/masque_v1_pilote.usdc, empilée AU-DESSUS du paquet, surcharge :
- sol (Voirie, Terrain), bordures verticales et marquages v1 : les faces dont un sommet tombe dans
  l'emprise pilote deviennent dégénérées (leurs trois indices = le premier sommet : aire nulle,
  invisibles au rendu) ; le nombre de faces ne change pas, les primvars par face / par sommet de
  face restent valides ;
- raccord : la partie HORS emprise des faces de sol coupées est recréée (découpe exacte par le
  rectangle, primvars st / st1 et normales interpolés) dans un maillage `<nom>_raccord_pilote` lié
  au même matériau v1, si bien que le contexte s'arrête exactement au bord de l'emprise ;
- Z du sol v1 sur 3 m autour de l'emprise : fondu vers le sol v2 au bord (MNT 2026 + bordures),
  les maillages v1 des classes 2025 étant jusqu'à +1,77 m au-dessus du MNT 2026.
Végétation et mobilier v1 : dans l'emprise et sur 3 m autour (fondu), chaque instance posée au sol est
posée sur son appui v2 (max du sol v2 et des têtes de bordure sous l'empreinte, z_appui ; revue
conformité r2 : les mâts v1 étaient 15 à 21 cm au-dessus du MNT, donc flottants avec z + sol_v2 − MNT) ;
les têtes de feux et panneaux suivent leur mât ; positions surchargées, paquet intact.
"""
import numpy as np

import pj_commun as K
from pxr import Sdf, Usd, UsdGeom, UsdShade, Vt

T = Sdf.ValueTypeNames
RACINES_SOL = ["/World/Voirie", "/World/Terrain"]
RACINES_MASQUE = ["/World/Bordures", "/World/Marquages", "/World/Mobilier"]   # Mobilier : maillage des clôtures
FONDU_M = 3.0


def _dist_rect(Q, R):
    x0, y0, x1, y1 = R
    dx = np.maximum(np.maximum(x0 - Q[:, 0], Q[:, 0] - x1), 0)
    dy = np.maximum(np.maximum(y0 - Q[:, 1], Q[:, 1] - y1), 0)
    return np.hypot(dx, dy)


def _decouper_hors(tri_w, R):
    """Polygones convexes de la partie d'un triangle HORS du rectangle R. tri_w : (3, 3) poids
    barycentriques identité ; renvoie une liste de (k, 3) poids barycentriques."""
    x0, y0, x1, y1 = R

    def clip(poly, P2, n, c):          # garde n·p + c >= 0
        out = []
        m = len(poly)
        for i in range(m):
            a, b = poly[i], poly[(i + 1) % m]
            pa, pb = a @ P2, b @ P2
            fa, fb = pa @ n + c, pb @ n + c
            if fa >= 0:
                out.append(a)
            if (fa >= 0) != (fb >= 0):
                t = fa / (fa - fb)
                out.append(a + (b - a) * t)
        return out

    def regions():
        yield [(np.array([-1.0, 0.0]), x0)]                                  # x < x0
        yield [(np.array([1.0, 0.0]), -x1)]                                  # x > x1
        yield [(np.array([1.0, 0.0]), -x0), (np.array([-1.0, 0.0]), x1), (np.array([0.0, -1.0]), y0)]
        yield [(np.array([1.0, 0.0]), -x0), (np.array([-1.0, 0.0]), x1), (np.array([0.0, 1.0]), -y1)]
    return clip, regions


def masquer(stage_v1, R, sol, chemin, log=print):
    """Écrit la couche de masque (usdc) ; renvoie les comptes."""
    st = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    st.GetRootLayer().documentation = (
        "Masque du paquet v1 dans l'emprise pilote ZP-01 (pj_contexte.py) : faces v1 dégénérées dans "
        "l'emprise, raccords découpés au bord, Z du sol v1 fondu vers le sol v2 sur 3 m. À empiler "
        "au-dessus de paquet_jardin_2026.usda (le paquet n'est pas modifié).")
    st.GetRootLayer().customLayerData = {"emprise_local_m": " ".join(f"{v:g}" for v in R), "version": K.VERSION}
    comptes = {}
    racines = [(r, True) for r in RACINES_SOL] + [(r, False) for r in RACINES_MASQUE]
    for racine, est_sol in racines:
        rp = stage_v1.GetPrimAtPath(racine)
        if not rp:
            continue
        for p in sorted(rp.GetChildren(), key=lambda q: q.GetName()):
            if p.GetTypeName() != "Mesh":
                continue
            m = UsdGeom.Mesh(p)
            P = np.array(m.GetPointsAttr().Get(), dtype=np.float64)
            fc = np.array(m.GetFaceVertexCountsAttr().Get())
            fi = np.array(m.GetFaceVertexIndicesAttr().Get())
            off = np.r_[0, np.cumsum(fc)[:-1]]
            dedans = (P[:, 0] > R[0]) & (P[:, 0] < R[2]) & (P[:, 1] > R[1]) & (P[:, 1] < R[3])
            touche = np.add.reduceat(dedans[fi].astype(int), off) > 0
            d = _dist_rect(P[:, :2], R)
            proche = d < FONDU_M
            if not touche.any() and not (est_sol and proche.any()):
                continue
            o = st.OverridePrim(p.GetPath())
            om = UsdGeom.Mesh(o)
            if touche.any():
                fi2 = fi.copy()
                for k in np.where(touche)[0]:
                    fi2[off[k]:off[k] + fc[k]] = fi[off[k]]
                om.CreateFaceVertexIndicesAttr().Set(Vt.IntArray.FromNumpy(fi2.astype(np.int32)))
            n_rac = 0
            if est_sol:
                Pz = P.copy()
                if proche.any():
                    zc = sol.z_points(P[proche, :2])
                    w = 1.0 - K.smoothstep(d[proche] / FONDU_M)
                    Pz[proche, 2] = P[proche, 2] * (1 - w) + zc * w
                    om.CreatePointsAttr().Set(Vt.Vec3fArray.FromNumpy(Pz.astype(np.float32)))
                coupe = touche & (np.add.reduceat((~dedans[fi]).astype(int), off) > 0)
                if coupe.any():
                    n_rac = _raccord(st, p, m, P, fc, fi, off, np.where(coupe)[0], R, sol)
            comptes[str(p.GetPath())] = {"faces_masquees": int(touche.sum()), "faces": int(len(fc)),
                                         "sommets_fondus": int(proche.sum()) if est_sol else 0,
                                         "faces_raccord": n_rac}
    comptes["reassis"] = _reasseoir(stage_v1, st, R, sol)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists():
        chemin.unlink()
    st.GetRootLayer().Export(str(chemin))
    vals = [c for k, c in comptes.items() if k != "reassis"]
    log(f"   masque v1 : {sum(c['faces_masquees'] for c in vals)} faces masquées, "
        f"{sum(c['faces_raccord'] for c in vals)} faces de raccord, "
        f"{sum(c['instances'] for c in comptes['reassis'].values())} instances v1 réassises")
    return comptes


def z_appui(sol, xy, r=0.08):
    """Altitude d'appui d'une instance posée au sol : max du sol v2 et des têtes de bordure sous son
    empreinte (centre + 4 points à r)."""
    xy = np.atleast_2d(np.asarray(xy, dtype=np.float64))[:, :2]
    off = np.array([[0, 0], [r, 0], [-r, 0], [0, r], [0, -r]], dtype=np.float64)
    Q = (xy[:, None, :] + off[None]).reshape(-1, 2)
    if not hasattr(sol, "_loc"):
        import pj_decals as DC
        sol._loc = DC.Localisateur(sol.P3, sol.T)
    _, z = sol._loc.trouver(Q)                      # maillage fabriqué (décaissés, îlots compris)
    hors = ~np.isfinite(z)
    if hors.any():
        z[hors] = sol.z_points(Q[hors])
    for bid, m, s, dl, d, ex in sol.projections(Q, rayon=0.3):
        b = sol.bandes[bid]
        dans = (ex <= 0) & (dl > b.interp(b.uf, s)) & (dl < b.interp(b.base, s))
        z[m[dans]] = np.maximum(z[m[dans]], b.interp(b.ztop, s[dans]))
    return z.reshape(len(xy), -1).max(axis=1)


def _reasseoir(stage_v1, st, R, sol):
    """Instances v1 (mobilier, végétation) de l'emprise + 3 m (fondu) : celles posées au sol (z v1 − MNT
    < 0,3 m) sont posées sur leur appui v2 (max du sol v2 et des têtes de bordure sous l'empreinte ; revue
    conformité r2 : mâts de feux v1 posés 15 à 21 cm au-dessus du MNT, donc flottants) ; celles portées en
    hauteur (têtes de feux, panneaux) suivent le mât le plus proche (0,5 m), sinon z += sol v2 − MNT."""
    out = {}
    for racine in ("/World/Mobilier", "/World/Vegetation"):
        rp = stage_v1.GetPrimAtPath(racine)
        if not rp:
            continue
        for p in sorted(rp.GetChildren(), key=lambda q: q.GetName()):
            if not p.IsA(UsdGeom.PointInstancer):
                continue
            pi = UsdGeom.PointInstancer(p)
            P = np.array(pi.GetPositionsAttr().Get(), dtype=np.float64)
            if len(P) == 0:
                continue
            d = _dist_rect(P[:, :2], R)
            m = np.where(d < FONDU_M)[0]
            if len(m) == 0:
                continue
            mnt = K.mnt_local(P[m, 0], P[m, 1])
            au_sol = (P[m, 2] - mnt) < 0.3
            dz = sol.z_points(P[m, :2]) - mnt
            if au_sol.any():
                dz[au_sol] = z_appui(sol, P[m[au_sol], :2]) - P[m[au_sol], 2]
                for k in np.where(~au_sol)[0]:            # portée en hauteur : suit le mât voisin
                    dd = np.hypot(*(P[m[au_sol], :2] - P[m[k], :2]).T)
                    if dd.min() < 0.5:
                        dz[k] = dz[au_sol][int(np.argmin(dd))]
            w = 1.0 - K.smoothstep(d[m] / FONDU_M)
            P2 = P.copy()
            P2[m, 2] += dz * w
            UsdGeom.PointInstancer(st.OverridePrim(p.GetPath())).CreatePositionsAttr().Set(
                Vt.Vec3fArray.FromNumpy(P2.astype(np.float32)))
            out[str(p.GetPath())] = {"instances": int(len(m)), "dz_min_m": round(float((dz * w).min()), 3),
                                     "dz_max_m": round(float((dz * w).max()), 3)}
    return out


def _raccord(st, prim, m, P, fc, fi, off, faces, R, sol):
    """Parties hors emprise des faces coupées (triangles v1), primvars par sommet interpolés."""
    api = UsdGeom.PrimvarsAPI(prim)
    pv_sommet = {}
    for pv in api.GetPrimvars():
        if pv.GetInterpolation() == UsdGeom.Tokens.vertex and pv.GetName() in ("primvars:st", "primvars:st1"):
            pv_sommet[pv.GetPrimvarName()] = (np.array(pv.Get(), dtype=np.float64), pv.GetTypeName())
    N = m.GetNormalsAttr().Get()
    N = np.array(N, dtype=np.float64) if N is not None and len(N) == len(P) else None
    clip, regions = _decouper_hors(None, R)
    pts, polys, attrs, nrm = [], [], {k: [] for k in pv_sommet}, []
    for k in faces:
        ids = fi[off[k]:off[k] + fc[k]]
        if len(ids) != 3:
            continue
        P2 = P[ids, :2]
        for reg in regions():
            poly = [np.eye(3)[i] for i in range(3)]
            for n, c in reg:
                poly = clip(poly, P2, n, c)
                if len(poly) < 3:
                    break
            if len(poly) < 3:
                continue
            W = np.array(poly)
            q = W @ P[ids]
            if abs(np.cross(q[1, :2] - q[0, :2], q[2, :2] - q[0, :2])) < 1e-8 and len(q) == 3:
                continue
            o = len(pts)
            pts += list(q)
            polys.append(list(range(o, o + len(q))))
            for nm, (arr, _) in pv_sommet.items():
                attrs[nm] += list(W @ arr[ids])
            if N is not None:
                nn = W @ N[ids]
                nrm += list(nn / np.maximum(np.linalg.norm(nn, axis=1), 1e-12)[:, None])
    if not polys:
        return 0
    Pr = np.array(pts)
    d = _dist_rect(Pr[:, :2], R)
    zc = sol.z_points(Pr[:, :2])
    w = 1.0 - K.smoothstep(d / FONDU_M)
    Pr[:, 2] = Pr[:, 2] * (1 - w) + zc * w
    chemin = prim.GetPath().GetParentPath().AppendChild(prim.GetName() + "_raccord_pilote")
    r = UsdGeom.Mesh.Define(st, chemin)
    r.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(Pr.astype(np.float32)))
    r.CreateFaceVertexCountsAttr(Vt.IntArray([len(p) for p in polys]))
    r.CreateFaceVertexIndicesAttr(Vt.IntArray([i for p in polys for i in p]))
    r.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    r.CreateExtentAttr(Vt.Vec3fArray([tuple(map(float, Pr.min(axis=0))), tuple(map(float, Pr.max(axis=0)))]))
    if nrm:
        r.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.array(nrm, dtype=np.float32)))
        r.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    ra = UsdGeom.PrimvarsAPI(r)
    for nm, (arr, typ) in pv_sommet.items():
        ra.CreatePrimvar(nm, typ, UsdGeom.Tokens.vertex).Set(Vt.Vec2fArray.FromNumpy(np.array(attrs[nm], dtype=np.float32)))
    for pv in api.GetPrimvars():                    # primvars constants (classe, couleur...)
        if pv.GetInterpolation() == UsdGeom.Tokens.constant and pv.HasAuthoredValue():
            ra.CreatePrimvar(pv.GetPrimvarName(), pv.GetTypeName(), UsdGeom.Tokens.constant).Set(pv.Get())
    b = UsdShade.MaterialBindingAPI(prim).GetDirectBindingRel()
    if b and b.GetTargets():
        UsdShade.MaterialBindingAPI.Apply(r.GetPrim())
        r.GetPrim().CreateRelationship("material:binding", False).SetTargets(b.GetTargets())
    ds = m.GetDoubleSidedAttr().Get()
    if ds is not None:
        r.CreateDoubleSidedAttr(ds)
    return len(polys)
