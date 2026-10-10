"""[hython] Contexte v1 et zones PCG pour Unreal (couches USD au contrat pj_usd/0.1, paquet v1 intact).

    hython recon/pcg/ue/contexte/preparer_usd.py [--snapshot DOSSIER] [--sortie DOSSIER]

Entrees : paquet v1 (recon/out/paquet_jardin/package, LECTURE SEULE : layers terrain, voirie, bordures, marquages,
batiments ; donnees/surfaces, objets), masque du v1 dans l'emprise pilote (fabrique_ue_snapshot/contexte/
masque_v1_pilote.usdc, pj_contexte.py : faces v1 degenerees dans l'emprise, raccords decoupes au bord, Z du sol v1 fondu
vers le sol v2 sur 3 m), sol v2 du pilote (fabrique_ue_snapshot/sol.usda) et points des bordures v2.
Sorties (dossier --sortie, defaut recon/out/paquet_jardin/v2/ue_pilote/usd, ignore par git) :
- contexte_v1.usdc : /World/Contexte (group) ; Sol_<i>_<j> (component, tuiles de 50 m) : un Mesh par materiau, la
  classe v1 du maillage affinee par le revetement du polygone de surfaces_2026.geojson (herbe, massif, terre,
  stabilise, beton, paves) ; Bordures_<i>_<j> (faces verticales v1) ; Marquages_<i>_<j> (peinture v1, Z recale sur le
  sol fondu pres de l'emprise) ; Bat_<id> (murs, toits ; UV des murs : u le long du mur, v = hauteur au-dessus du
  sol du batiment ; st1 = (hauteur a l'egout, alea du batiment) pour les fenetres de M_PJ_Facade).
  Faces masquees (aire nulle) retirees ; normales par sommet de face a cusp 30 deg ; st = (x, y) m sur le sol.
  Materiaux /World/Looks/<nom> -> info:unreal:sourceAsset (MI etalonnes /Game/PJ/Materials, MI maison du contexte).
  Arbres et mobilier v1 (volumes provisoires) NON repris.
- zones_pcg.usdc : /World/Zones/<zone> (component) : maillages d'echantillonnage du PCG (PG_Herbe : PCGMeshSampler,
  densite = couleur de sommet R) : herbe_tondu (a moins de RAYON_PROCHE_M du centre du pilote), herbe_tondu_loin,
  herbe_haute, massifs, feuilles. Densite 0 a moins de 0,15 m d'une surface dure (chaussee, trottoir, bordure v1 et
  v2, bati), rampe jusqu'a 0,35 m ; triangles redecoupes a 0,35 m pres des limites ; triangles raides (> 60 deg)
  retires. Feuilles : sous la couronne des feuillus (degressif), plus rares sur la chaussee.
- lointain.usdc (si lointain_entrees.json existe, ecrit par contexte/lointain.py) : batiments du cadastre hors du carre
  v1, extrudes par lointain_usd.py.
- z_objets.json : altitude du sol rendu (v1 fondu + v2) sous les arbres (arbres.geojson), les sommets des clotures et
  le mobilier v1 (instances.json).
- preparation.json : comptes et controles.
Deterministe (aucun alea hors graines fixes, ordre fixe).
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[3]
sys.path.insert(0, str(DEPOT / 'recon/pcg/houdini'))
sys.path.insert(0, str(ICI))
import pj_commun as K  # noqa: E402  (normales_cusp)
import pj_decals as DC  # noqa: E402  (Localisateur)

T = Sdf.ValueTypeNames
PAQUET = DEPOT / 'recon/out/paquet_jardin/package'
V2 = DEPOT / 'recon/out/paquet_jardin/v2'
EMPRISE = (-11.0, -28.0, 60.0, 72.0)
TUILE_M = 50.0
CENTRE_PILOTE = (24.5, 22.0)                    # centre de l'emprise ZP-01
RAYON_PROCHE_M = 85.0                           # gazon ras dense en deca (vues de controle)
SITE = (-150.0, -150.0, 150.0, 150.0)
COUCHES_V1 = ['marquages.usdc', 'bordures.usdc', 'voirie.usdc', 'terrain.usdc', 'batiments.usdc']
MAT = '/Game/PJ/Materials'

# ---- revetement : classe du maillage v1 (sans _2025 / _raccord_pilote) x materiau du polygone -> materiau_id
SOL = {
    'chaussee': 'enrobe_bbsg_ancien', 'parking': 'enrobe_bbsg_ancien', 'acces_riverain': 'enrobe_bbsg_ancien',
    'piste_cyclable': 'enrobe_piste_cyclable', 'quai_bus': 'beton_balaye', 'batiment': 'beton_balaye',
    'jupe_emprise': 'terre_nue',
    'trottoir': {'enrobe': 'enrobe_trottoir', 'beton': 'beton_balaye', 'paves': 'paves_beton', None: 'enrobe_trottoir'},
    'ilot': {'enrobe': 'enrobe_bbsg_ancien', 'beton': 'beton_balaye', None: 'beton_balaye'},
    'espace_vert': {'herbe': 'gazon_tondu', 'massif_plante': 'noue_plantee', 'terre': 'terre_nue', None: 'gazon_tondu'},
    'terre_plein_vegetal': {'herbe': 'herbe_haute', 'massif_plante': 'noue_plantee', None: 'herbe_haute'},
    'autre': {'stabilise': 'stabilise_beige', 'enrobe': 'enrobe_bbsg_ancien', None: 'stabilise_beige'},
}
SOL_2025 = {'chaussee': 'enrobe_bbsg_neuf_2025'}
VERTS = {'gazon_tondu': 'herbe_tondu', 'herbe_haute': 'herbe_haute', 'noue_plantee': 'massifs'}
DURS = {'enrobe_bbsg_ancien', 'enrobe_bbsg_neuf_2025', 'enrobe_trottoir', 'enrobe_piste_cyclable', 'beton_balaye',
        'paves_beton', 'stabilise_beige', 'bev_podotactile', 'enrobe_reprise_tranchee', 'gravier_concasse_6_10',
        'brf_bois_concasse'}
# materiaux du contexte -> asset UE (MI_<nom> sauf indication) ; apercu UsdPreviewSurface
APERCU = {'gazon_tondu': (0.04, 0.08, 0.02), 'herbe_haute': (0.13, 0.2, 0.05), 'noue_plantee': (0.07, 0.09, 0.05),
          'terre_nue': (0.1, 0.09, 0.07), 'stabilise_beige': (0.25, 0.23, 0.18)}
PEINTURE = {'blanc': 'PJ_Peinture_blanc_u{u}', 'jaune': 'PJ_Peinture_jaune_u{u}', 'ocre': 'enrobe_colore_ocre'}
ASSET = {'toit_terrasse': '/Game/Carla/Static/GenericMaterials/RoofBitumen/MI_RoofBitumen_01.MI_RoofBitumen_01',
         'toit_pentes': '/Game/Carla/Static/GenericMaterials/RoofBitumen/MI_RoofBitumen_02.MI_RoofBitumen_02'}
FACADES_ENDUIT = ['PJ_Facade_enduit_blanc', 'PJ_Facade_enduit_beige', 'PJ_Facade_enduit_gris', 'PJ_Facade_enduit_ocre']


def graine(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:4], 'little') & 0x7FFFFFFF


def lire_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def l93_local(c):
    return (c[0] - 917279.43, c[1] - 6460289.98)


# ======================================================================= scene de sortie
class Couche:
    def __init__(self, doc):
        self.st = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(self.st, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(self.st, 1.0)
        w = UsdGeom.Xform.Define(self.st, '/World')
        Usd.ModelAPI(w.GetPrim()).SetKind(Kind.Tokens.assembly)
        self.st.SetDefaultPrim(w.GetPrim())
        lay = self.st.GetRootLayer()
        lay.documentation = doc
        lay.customLayerData = {'pj:contrat': 'pj_usd/0.1', 'pj:cusp_deg': 30.0}
        UsdGeom.Scope.Define(self.st, '/World/Looks')
        self.mats = {}

    def groupe(self, chemin):
        g = UsdGeom.Xform.Define(self.st, chemin)
        Usd.ModelAPI(g.GetPrim()).SetKind(Kind.Tokens.group)
        return g

    def composant(self, chemin):
        c = UsdGeom.Xform.Define(self.st, chemin)
        Usd.ModelAPI(c.GetPrim()).SetKind(Kind.Tokens.component)
        return c

    def materiau(self, nom):
        if nom in self.mats:
            return self.mats[nom]
        chemin = f'/World/Looks/{nom}'
        mat = UsdShade.Material.Define(self.st, chemin)
        ap = UsdShade.Shader.Define(self.st, chemin + '/Apercu')
        ap.CreateIdAttr('UsdPreviewSurface')
        ap.CreateInput('diffuseColor', T.Color3f).Set(Gf.Vec3f(*APERCU.get(nom, (0.3, 0.3, 0.3))))
        ap.CreateInput('roughness', T.Float).Set(0.8)
        mat.CreateSurfaceOutput().ConnectToSource(ap.ConnectableAPI(), 'surface')
        ue = UsdShade.Shader.Define(self.st, chemin + '/Unreal')
        ue.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
        ue.SetSourceAsset(Sdf.AssetPath(ASSET.get(nom, f'{MAT}/MI_{nom}.MI_{nom}')), 'unreal')
        mat.CreateSurfaceOutput('unreal').ConnectToSource(ue.ConnectableAPI(), 'out')
        self.mats[nom] = mat
        return mat

    def maillage(self, chemin, P, tris, nom_mat, uv, N=None, couleur=None, st1=None):
        """P (n,3), tris (m,3) ; uv : (n,2) par sommet ou (m*3,2) par sommet de face ; N : normales par sommet de
        face (m*3,3), calculees a cusp 30 deg si None ; couleur : (n,3) displayColor par sommet ; st1 : (m*3,2)."""
        m = UsdGeom.Mesh.Define(self.st, chemin)
        P = np.asarray(P, dtype=np.float64)
        idx = np.asarray(tris, dtype=np.int64).reshape(-1)
        cnt = np.full(len(tris), 3, dtype=np.int32)
        m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(P.astype(np.float32)))
        m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(cnt))
        m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(idx.astype(np.int32)))
        m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        m.CreateDoubleSidedAttr(False)
        if N is None:
            N = K.normales_cusp(P, cnt, idx, 30.0)
        elif isinstance(N, str):                             # 'haut' : normales verticales par sommet (zones)
            N = np.tile([0.0, 0.0, 1.0], (len(P), 1))
        m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(N, dtype=np.float32)))
        m.SetNormalsInterpolation(UsdGeom.Tokens.vertex if len(N) == len(P) and len(N) != len(idx)
                                  else UsdGeom.Tokens.faceVarying)
        lo, hi = P.min(axis=0), P.max(axis=0)
        m.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, lo)), Gf.Vec3f(*map(float, hi))]))
        pv = UsdGeom.PrimvarsAPI(m)
        uv = np.asarray(uv, dtype=np.float32)
        interp = UsdGeom.Tokens.vertex if len(uv) == len(P) and len(uv) != len(idx) else UsdGeom.Tokens.faceVarying
        pv.CreatePrimvar('st', T.TexCoord2fArray, interp).Set(Vt.Vec2fArray.FromNumpy(uv))
        if st1 is not None:
            pv.CreatePrimvar('st1', T.TexCoord2fArray, UsdGeom.Tokens.faceVarying).Set(
                Vt.Vec2fArray.FromNumpy(np.asarray(st1, dtype=np.float32)))
        if couleur is not None:
            pv.CreatePrimvar('displayColor', T.Color3fArray, UsdGeom.Tokens.vertex).Set(
                Vt.Vec3fArray.FromNumpy(np.asarray(couleur, dtype=np.float32)))
        pv.CreatePrimvar('materiau_id', T.String, UsdGeom.Tokens.constant).Set(nom_mat)
        UsdShade.MaterialBindingAPI.Apply(m.GetPrim())
        UsdShade.MaterialBindingAPI(m.GetPrim()).Bind(self.materiau(nom_mat))
        return m

    def enregistrer(self, chemin):
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        if chemin.exists():
            chemin.unlink()
        self.st.GetRootLayer().Export(str(chemin))
        return chemin


# ======================================================================= lecture du v1 compose
def stage_v1(snapshot):
    root = Sdf.Layer.CreateAnonymous('.usda')
    root.subLayerPaths = [str((snapshot / 'contexte/masque_v1_pilote.usdc').as_posix())] + \
        [str((PAQUET / 'layers' / c).as_posix()) for c in COUCHES_V1]
    return Usd.Stage.Open(root)


def triangles(prim):
    """(P, tris (m,3), face d'origine (m,)) d'un Mesh compose ; faces d'aire nulle (masquees) retirees."""
    m = UsdGeom.Mesh(prim)
    P = np.array(m.GetPointsAttr().Get(), dtype=np.float64)
    fc = np.array(m.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
    fi = np.array(m.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
    off = np.r_[0, np.cumsum(fc)[:-1]]
    tl, fl = [], []
    for k in range(1, int(fc.max()) - 1):
        sel = np.where(fc > k + 1)[0]
        tl.append(np.stack([fi[off[sel]], fi[off[sel] + k], fi[off[sel] + k + 1]], axis=1))
        fl.append(sel)
    tri, face = np.concatenate(tl), np.concatenate(fl)
    a, b, c = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    aire = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    ok = aire > 1e-7
    return P, tri[ok], face[ok]


def uv_boite(P, tri):
    """UV en metres par sommet de face, projection boite par face : (x, y) si la face regarde le haut ou le bas,
    sinon (abscisse horizontale le long de la face, z) : pas d'UV degeneree sur les faces raides (jupe, talus)."""
    V = P[tri]
    n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    t = np.stack([-n[:, 1], n[:, 0]], axis=1)
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-12)[:, None]
    raide = np.abs(n[:, 2]) < 0.6
    uv = V[:, :, :2].copy()
    u = np.einsum('ikj,ij->ik', V[:, :, :2], t)
    uv[raide, :, 0] = u[raide]
    uv[raide, :, 1] = V[raide, :, 2]
    return uv.reshape(-1, 2)


def sans_raides(P, tri, u, nz_min=0.5):
    """Zones d'echantillonnage : triangles raides (faces de bordure, jupe, talus > 60 deg) retires, sommets recompactes ;
    u (indices d'origine des sommets) suivi."""
    n = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
    nz = n[:, 2] / np.maximum(np.linalg.norm(n, axis=1), 1e-12)
    P2, T2, k = compacter(P, tri[nz >= nz_min])
    return P2, T2, u[k]


def compacter(P, tri):
    u, inv = np.unique(tri.reshape(-1), return_inverse=True)
    return P[u], inv.reshape(-1, 3), u


# ======================================================================= rasters (polygones de surfaces, surfaces dures)
class Raster:
    def __init__(self, res, emprise=SITE):
        self.r = res
        self.x0, self.y0, self.x1, self.y1 = emprise
        self.n = int(round((self.x1 - self.x0) / res))
        self.m = int(round((self.y1 - self.y0) / res))

    def px(self, xy):
        xy = np.asarray(xy, dtype=np.float64)
        return np.stack([(xy[..., 0] - self.x0) / self.r, (self.y1 - xy[..., 1]) / self.r], axis=-1)

    def lire(self, a, xy):
        p = np.floor(self.px(xy)).astype(np.int64)
        i = np.clip(p[..., 1], 0, self.m - 1)
        j = np.clip(p[..., 0], 0, self.n - 1)
        return a[i, j]


def raster_surfaces(rs):
    g = lire_json(PAQUET / 'donnees/surfaces/surfaces_2026.geojson')
    feats = []
    for f in g['features']:
        geo = f['geometry']
        polys = geo['coordinates'] if geo['type'] == 'MultiPolygon' else [geo['coordinates']]
        for poly in polys:
            ext = np.array([l93_local(c) for c in poly[0]])
            aire = 0.5 * abs(np.dot(ext[:-1, 0], ext[1:, 1]) - np.dot(ext[1:, 0], ext[:-1, 1]))
            feats.append((aire, f['properties'], ext))
    feats.sort(key=lambda t: (-t[0], t[1]['id']))                  # grands d'abord : les inclus recouvrent
    im = Image.new('I', (rs.n, rs.m), -1)
    d = ImageDraw.Draw(im)
    props = []
    for k, (_, p, ext) in enumerate(feats):
        d.polygon([tuple(v) for v in rs.px(ext)], fill=k)
        props.append(p)
    return np.array(im, dtype=np.int32), props


def materiau_sol(classe_maillage, est_2025, props_poly):
    base = classe_maillage
    if est_2025 and base in SOL_2025:
        return SOL_2025[base]
    r = SOL.get(base, 'enrobe_bbsg_ancien')
    if isinstance(r, dict):
        mat = props_poly.get('materiau') if props_poly and props_poly.get('classe') == base else None
        return r.get(mat, r[None])
    return r


def dilater(a, n):
    """Dilatation binaire par un disque de rayon n pixels (decalages numpy)."""
    out = a.copy()
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            if dx * dx + dy * dy > n * n or (dx == 0 and dy == 0):
                continue
            s = np.zeros_like(a)
            ys = slice(max(dy, 0), a.shape[0] + min(dy, 0))
            yd = slice(max(-dy, 0), a.shape[0] + min(-dy, 0))
            xs = slice(max(dx, 0), a.shape[1] + min(dx, 0))
            xd = slice(max(-dx, 0), a.shape[1] + min(-dx, 0))
            s[yd, xd] = a[ys, xs]
            out |= s
    return out


def dilater_carre(a, n):
    """Dilatation par un carre de cote 2n+1 (separable : max glissant en x puis en y)."""
    out = a.copy()
    for ax in (0, 1):
        src = out.copy()
        for k in range(1, n + 1):
            for sgn in (1, -1):
                s = np.roll(src, sgn * k, axis=ax)
                if sgn > 0:
                    (s[:k] if ax == 0 else s[:, :k])[...] = False
                else:
                    (s[-k:] if ax == 0 else s[:, -k:])[...] = False
                out |= s
    return out


def orienter(P, tri, haut=None, dehors=None):
    """Triangles orientes : normale geometrique vers +Z (haut) ou vers l'exterieur (fonction dehors(milieu, n) ->
    True si le point decale est dedans : face retournee). Renvoie tri reordonne."""
    a, b, c = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    n = np.cross(b - a, c - a)
    if haut:
        inv = n[:, 2] < 0
    else:
        nn = n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        inv = dehors((a + b + c) / 3.0, nn)
    t2 = tri.copy()
    t2[inv, 1], t2[inv, 2] = tri[inv, 2], tri[inv, 1]
    return t2


# ======================================================================= decoupe adaptative (zones)
def subdiviser(P, tri, critere, pas_max, iterations=6):
    """Soupe de triangles : decoupe 1 -> 4 des triangles dont critere(centroide) est vrai et l'arete max > pas_max."""
    V = P[tri]                                           # (m, 3, 3)
    for _ in range(iterations):
        L = np.max(np.linalg.norm(V - np.roll(V, 1, axis=1), axis=2), axis=1)
        sel = (L > pas_max) & critere(V.mean(axis=1))
        if not sel.any():
            break
        A = V[sel]
        a, b, c = A[:, 0], A[:, 1], A[:, 2]
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        nv = np.concatenate([np.stack(t, axis=1) for t in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
        V = np.concatenate([V[~sel], nv])
    Pn = V.reshape(-1, 3)
    u, inv = np.unique(np.round(Pn * 1000.0).astype(np.int64), axis=0, return_index=False, return_inverse=True)
    Pw = np.zeros((len(u), 3))
    Pw[inv.reshape(-1)] = Pn                                # sommets soudes au mm
    return Pw, inv.reshape(-1, 3)


# ======================================================================= principal
def principal(snapshot, sortie):
    t0 = time.time()
    rapport = {'emprise_pilote': EMPRISE, 'tuile_m': TUILE_M}
    st = stage_v1(snapshot)
    rs = Raster(0.2)
    poly_id, props = raster_surfaces(rs)
    ctx = Couche('Contexte v1 hors emprise pilote pour UE (recon/pcg/ue/contexte/preparer_usd.py) : sol, bordures, '
                 'marquages et batiments du paquet v1 (masque du pilote applique), materiaux MI etalonnes.')
    ctx.groupe('/World/Contexte')

    # ---------------- sol v1 (Terrain, Voirie, raccords)
    sol_P, sol_T, sol_M = [], [], []                     # pour le localisateur et les zones
    tuiles = {}
    n_masq = 0
    for racine in ('/World/Voirie', '/World/Terrain'):
        for p in sorted(st.GetPrimAtPath(racine).GetChildren(), key=lambda q: q.GetName()):
            if p.GetTypeName() != 'Mesh':
                continue
            nom = p.GetName()
            classe = nom.replace('_raccord_pilote', '')
            est_2025 = classe.endswith('_2025')
            classe = classe.replace('_2025', '')
            P, tri, _ = triangles(p)
            tri = orienter(P, tri, haut=True)
            n_masq += len(UsdGeom.Mesh(p).GetFaceVertexCountsAttr().Get()) - len(tri)
            c = P[tri].mean(axis=1)
            pid = rs.lire(poly_id, c[:, :2])
            mats = np.array([materiau_sol(classe, est_2025, props[i] if i >= 0 else None) for i in pid])
            it = np.floor((c[:, :2] - np.array(SITE[:2])) / TUILE_M).astype(int)
            it = np.clip(it, 0, int((SITE[2] - SITE[0]) / TUILE_M) - 1)
            for key in sorted(set(zip(it[:, 0].tolist(), it[:, 1].tolist(), mats.tolist()))):
                sel = (it[:, 0] == key[0]) & (it[:, 1] == key[1]) & (mats == key[2])
                tuiles.setdefault((key[0], key[1]), {}).setdefault(key[2], []).append((P, tri[sel]))
            sol_P.append(P)
            sol_T.append(tri + sum(len(q) for q in sol_P[:-1]))
            sol_M.append(mats)
    PS = np.concatenate(sol_P)
    TS = np.concatenate(sol_T)
    MS = np.concatenate(sol_M)
    comptes_sol = {}
    for (i, j) in sorted(tuiles):
        comp = f'/World/Contexte/Sol_{i}_{j}'
        ctx.composant(comp)
        for mat in sorted(tuiles[(i, j)]):
            parts = tuiles[(i, j)][mat]
            Pl, Tl, o = [], [], 0
            for P, tri in parts:
                Pc, Tc, _ = compacter(P, tri)
                Pl.append(Pc)
                Tl.append(Tc + o)
                o += len(Pc)
            Pc, Tc = np.concatenate(Pl), np.concatenate(Tl)
            ctx.maillage(f'{comp}/{mat}', Pc, Tc, mat, uv_boite(Pc, Tc))
            comptes_sol[mat] = comptes_sol.get(mat, 0) + len(Tc)
    rapport['sol'] = {'tuiles': len(tuiles), 'triangles_par_materiau': comptes_sol, 'faces_masquees_retirees': int(n_masq)}

    # localisateur du sol rendu (v1 fondu + v2 pilote) pour les Z (marquages pres de l'emprise, arbres, clotures)
    st2 = Usd.Stage.Open(str(snapshot / 'sol.usda'))
    v2P, v2T, v2M = [], [], []
    for p in st2.Traverse():
        if p.GetTypeName() == 'Mesh':
            P, tri, _ = triangles(p)
            tri = orienter(P, tri, haut=True)
            v2T.append(tri + sum(len(q) for q in v2P))
            v2P.append(P)
            v2M.append(np.full(len(tri), p.GetName()))
    P2, T2, M2 = np.concatenate(v2P), np.concatenate(v2T), np.concatenate(v2M)
    PA = np.concatenate([PS, P2])
    TA = np.concatenate([TS, T2 + len(PS)])
    MA = np.concatenate([MS, M2])
    rapport['sol_v2'] = {'triangles': int(len(T2)), 'materiaux': sorted(set(M2.tolist()))}

    def localisateur(zone):
        c = PA[TA].mean(axis=1)
        x0, y0, x1, y1 = zone
        sel = (c[:, 0] > x0) & (c[:, 0] < x1) & (c[:, 1] > y0) & (c[:, 1] < y1)
        return DC.Localisateur(PA, TA[sel], cellule=1.0)

    # ---------------- bordures v1 (faces verticales) : u le long de la face, v = z
    bp = st.GetPrimAtPath('/World/Bordures/faces_verticales')
    P, tri, face = triangles(bp)
    tri = np.concatenate([tri, tri[:, [0, 2, 1]]])      # faces v1 vues des deux cotes (sens inconnu)
    a, b, c = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    n = np.cross(b - a, c - a)
    t = np.stack([-n[:, 1], n[:, 0]], axis=1)
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-12)[:, None]
    uvf = np.stack([np.einsum('ij,ij->i', P[tri[:, k], :2], t) for k in range(3)], axis=1)
    uv = np.stack([uvf, P[tri][:, :, 2]], axis=2).reshape(-1, 2)
    ctr = P[tri].mean(axis=1)
    it = np.clip(np.floor((ctr[:, :2] - np.array(SITE[:2])) / TUILE_M).astype(int), 0, 5)
    nb_bord = 0
    segments_v1 = []
    for key in sorted(set(zip(it[:, 0].tolist(), it[:, 1].tolist()))):
        sel = np.where((it[:, 0] == key[0]) & (it[:, 1] == key[1]))[0]
        comp = f'/World/Contexte/Bordures_{key[0]}_{key[1]}'
        ctx.composant(comp)
        Pc, Tc, _ = compacter(P, tri[sel])
        uvs = uv.reshape(-1, 3, 2)[sel].reshape(-1, 2)
        nn = n[sel] / np.maximum(np.linalg.norm(n[sel], axis=1), 1e-12)[:, None]
        ctx.maillage(f'{comp}/bordure_v1', Pc, Tc, 'bordure_v1', uvs, N=np.repeat(nn, 3, axis=0))
        nb_bord += len(sel)
    seg = P[tri][:, :, :2]                               # traces au sol des faces (surfaces dures des zones)
    rapport['bordures_v1'] = {'triangles': int(nb_bord)}

    # ---------------- marquages v1 : Z recale sur le sol rendu a moins de 3,5 m de l'emprise
    zone_m = (EMPRISE[0] - 4, EMPRISE[1] - 4, EMPRISE[2] + 4, EMPRISE[3] + 4)
    loc_m = localisateur(zone_m)
    nb_mq, recales = 0, 0
    mq_par_tuile = {}
    for p in sorted(st.GetPrimAtPath('/World/Marquages').GetChildren(), key=lambda q: q.GetName()):
        if p.GetTypeName() != 'Mesh':
            continue
        P, tri, _ = triangles(p)
        tri = orienter(P, tri, haut=True)
        if not len(tri):
            continue
        Pc, Tc, _ = compacter(P, tri)
        x0, y0, x1, y1 = EMPRISE
        dx = np.maximum(np.maximum(x0 - Pc[:, 0], Pc[:, 0] - x1), 0)
        dy = np.maximum(np.maximum(y0 - Pc[:, 1], Pc[:, 1] - y1), 0)
        proche = np.where(np.hypot(dx, dy) < 3.5)[0]
        if len(proche):
            _, z = loc_m.trouver(Pc[proche, :2])
            ok = np.isfinite(z)
            Pc[proche[ok], 2] = z[ok] + 0.01
            recales += int(ok.sum())
        couleur, _, u = p.GetName().partition('_usure_')
        mat = PEINTURE.get(couleur, 'PJ_Peinture_blanc_u{u}').format(u=u)
        ctrm = Pc[Tc].mean(axis=1)
        itm = np.clip(np.floor((ctrm[:, :2] - np.array(SITE[:2])) / TUILE_M).astype(int), 0, 5)
        for key in sorted(set(zip(itm[:, 0].tolist(), itm[:, 1].tolist()))):
            sel = (itm[:, 0] == key[0]) & (itm[:, 1] == key[1])
            Pk, Tk, _ = compacter(Pc, Tc[sel])
            mq_par_tuile.setdefault(key, []).append((p.GetName(), mat, Pk, Tk))
            nb_mq += int(sel.sum())
    for key in sorted(mq_par_tuile):
        comp = f'/World/Contexte/Marquages_{key[0]}_{key[1]}'
        ctx.composant(comp)
        for nom, mat, Pk, Tk in mq_par_tuile[key]:
            ctx.maillage(f'{comp}/{nom}', Pk, Tk, mat, uv_boite(Pk, Tk))
    rapport['marquages_v1'] = {'triangles': nb_mq, 'sommets_recales_pres_emprise': recales}

    # ---------------- batiments : murs et toits par batiment
    bats = lire_json(PAQUET / 'donnees/objets/batiments_local.geojson')['features']
    polys = []
    for f in bats:
        geo = f['geometry']
        rings = geo['coordinates'] if geo['type'] == 'Polygon' else geo['coordinates'][0]
        polys.append((f['properties'], np.array(rings[0], dtype=np.float64)[:, :2]))
    murs = st.GetPrimAtPath('/World/Batiments/murs')
    toits = st.GetPrimAtPath('/World/Batiments/toits')
    Pm, Tm, _ = triangles(murs)
    Pt, Tt, _ = triangles(toits)
    Tt = orienter(Pt, Tt, haut=True)
    cm = Pm[Tm].mean(axis=1)[:, :2]
    ct = Pt[Tt].mean(axis=1)[:, :2]

    def dist_bord(Q, ring):
        a, b = ring[:-1], ring[1:]
        ab = b - a
        t_ = np.clip(np.einsum('nkj,kj->nk', Q[:, None, :] - a[None], ab) / np.maximum((ab * ab).sum(1), 1e-12), 0, 1)
        proj = a[None] + t_[..., None] * ab[None]
        return np.linalg.norm(Q[:, None, :] - proj, axis=2).min(axis=1)

    def dedans(Q, ring):
        x, y = Q[:, 0], Q[:, 1]
        res = np.zeros(len(Q), dtype=bool)
        for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
            c_ = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 == y1, 1e-12, y2 - y1) + x1)
            res ^= c_
        return res

    dm = np.stack([dist_bord(cm, r) for _, r in polys], axis=1)
    bat_m = np.argmin(dm, axis=1)
    bat_t = np.full(len(ct), -1)
    for k, (_, r) in enumerate(polys):
        bat_t[(bat_t < 0) & dedans(ct, r)] = k
    ctx.groupe('/World/Contexte/Batiments')
    rapport['batiments'] = {}
    for k, (pr, ring) in enumerate(polys):
        sm, stt = np.where(bat_m == k)[0], np.where(bat_t == k)[0]
        if not len(sm) and not len(stt):
            continue
        bid = pr['id']
        comp = f'/World/Contexte/Batiments/Bat_{bid}'
        ctx.composant(comp)
        g = graine('facade', bid)
        usage = f"{pr.get('nature')} {pr.get('usage')}".lower()
        if pr.get('construction_legere') or (pr.get('hauteur_egout_m') or 0) < 3.6:
            fac = 'PJ_Facade_annexe'
        elif any(w in usage for w in ('commerc', 'retail', 'industriel', 'sportif')):
            fac = 'PJ_Facade_commerce'
        else:
            fac = FACADES_ENDUIT[g % len(FACADES_ENDUIT)]
        h_eg = float(pr.get('hauteur_egout_m') or 3.0)
        zs = float(pr.get('z_sol_local') or 0.0)
        if len(sm):
            tri = orienter(Pm, Tm[sm], dehors=lambda mid, nn: dedans(mid[:, :2] + 0.05 * nn[:, :2], ring))
            a, b, c = Pm[tri[:, 0]], Pm[tri[:, 1]], Pm[tri[:, 2]]
            nrm = np.cross(b - a, c - a)
            nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]
            tt = np.stack([-nrm[:, 1], nrm[:, 0]], axis=1)
            tt /= np.maximum(np.linalg.norm(tt, axis=1), 1e-12)[:, None]
            u = np.stack([np.einsum('ij,ij->i', Pm[tri[:, q], :2], tt) for q in range(3)], axis=1)
            v = Pm[tri][:, :, 2] - zs
            Pc, Tc, _ = compacter(Pm, tri)
            uvw = np.stack([u, v], axis=2).reshape(-1, 2)
            st1 = np.tile([h_eg, (g % 1000) / 1000.0], (len(uvw), 1))
            ctx.maillage(f'{comp}/murs', Pc, Tc, fac, uvw, N=np.repeat(nrm, 3, axis=0), st1=st1)
        if len(stt):
            Pc, Tc, _ = compacter(Pt, Tt[stt])
            toit = 'toit_pentes' if pr.get('toit') == 'pentes' else (
                'gazon_tondu' if 'végétalisée' in str(pr.get('toit')) else 'toit_terrasse')
            ctx.maillage(f'{comp}/toit', Pc, Tc, toit, Pc[:, :2])
        rapport['batiments'][bid] = {'facade': fac, 'murs_tri': int(len(sm)), 'toit_tri': int(len(stt)),
                                     'hauteur_egout_m': h_eg, 'usage': pr.get('usage'), 'toit': pr.get('toit')}
    rapport['batiments_non_affectes'] = {'murs': int((dm.min(axis=1) > 0.5).sum()), 'toits': int((bat_t < 0).sum())}
    ctx.enregistrer(sortie / 'contexte_v1.usdc')
    rapport['contexte_v1'] = str((sortie / 'contexte_v1.usdc').as_posix())
    rapport['duree_contexte_s'] = round(time.time() - t0, 1)

    # ======================================================= zones PCG
    t1 = time.time()
    rz = Raster(0.05)
    dur = Image.new('1', (rz.n, rz.m), 0)
    d = ImageDraw.Draw(dur)
    cA = PA[TA].mean(axis=1)
    est_dur = np.array([m in DURS for m in MA]) | ~np.array([m in VERTS or m in ('terre_nue', 'gazon_sec') for m in MA])
    for k in np.where(est_dur)[0]:
        d.polygon([tuple(v) for v in rz.px(PA[TA[k], :2])], fill=1)
    for q in seg.reshape(-1, 3, 2):                          # traces des bordures v1 (largeur 1 px = 5 cm)
        d.line([tuple(v) for v in rz.px(q)] + [tuple(rz.px(q[0]))], fill=1, width=2)
    pts = lire_json(snapshot / 'points/bordures.json')['points']
    index = lire_json(snapshot / 'prototypes/index.json')['prototypes']
    for p in pts:
        x_ = p.get('x') or {}
        if x_.get('type') == 'joint':
            continue
        L, W = index[p['asset']]['dims_m'][:2]
        L *= p['s'][0]
        y0_, y1_ = (-W, 0.0) if x_.get('type') == 'caniveau' else (0.0, W)
        loc = np.array([[-L / 2, y0_], [L / 2, y0_], [L / 2, y1_], [-L / 2, y1_]])
        yaw = math.radians(p['rpy_deg'][2])
        R = np.array([[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]])
        q = loc @ R.T + np.array(p['p'][:2])
        d.polygon([tuple(v) for v in rz.px(q)], fill=1)
    D = np.array(dur, dtype=bool)
    niveaux = [(3, 0.0), (5, 0.4), (7, 0.75)]                 # 0,15 / 0,25 / 0,35 m
    dens = np.ones(D.shape, dtype=np.float32)
    for npx, val in reversed(niveaux):
        dens[dilater(D, npx)] = val
    rapport['zones'] = {'surfaces_dures_px': int(D.sum())}

    def zone_couleur(Pz):
        v = rz.lire(dens, Pz[:, :2])
        return np.stack([v, v, v], axis=1)

    zon = Couche('Zones d echantillonnage PCG (PG_Herbe : PCGMeshSampler, densite = couleur de sommet R ; '
                 'recon/pcg/ue/contexte/preparer_usd.py). Non rendues.')
    zon.groupe('/World/Zones')
    # proximite d'un bord : densite < 1 a moins de 0,35 m ; on redecoupe aussi a 1 m (raster dilate)
    proche_1m = dilater_carre(D, 20)
    for zone in ('herbe_tondu', 'herbe_haute', 'massifs'):
        sel = np.where(np.array([VERTS.get(m) == zone for m in MA]))[0]
        if not len(sel):
            continue
        Pz, Tz = subdiviser(PA, TA[sel], lambda cxy: rz.lire(proche_1m, cxy[:, :2]), 0.35)
        col = zone_couleur(Pz)
        garde = col[Tz][:, :, 0].max(axis=1) > 0      # triangles entierement nuls retires
        Tz = Tz[garde]
        # gazon ras : zone proche du pilote (echantillonnage dense) et zone lointaine (plus clairsemee)
        cz = Pz[Tz].mean(axis=1)[:, :2]
        proche = np.hypot(cz[:, 0] - CENTRE_PILOTE[0], cz[:, 1] - CENTRE_PILOTE[1]) < RAYON_PROCHE_M
        parts = [(zone, np.ones(len(Tz), dtype=bool))] if zone != 'herbe_tondu' else             [(zone, proche), (zone + '_loin', ~proche)]
        for nomz, m_ in parts:
            Pz2, Tz2, u = compacter(Pz, Tz[m_])
            zon.composant(f'/World/Zones/{nomz}')
            Pz2, Tz2, u = sans_raides(Pz2, Tz2, u)
            zon.maillage(f'/World/Zones/{nomz}/zone', Pz2, Tz2, 'PJ_Neutre', uv_boite(Pz2, Tz2), couleur=col[u])
            rapport['zones'][nomz] = {'triangles': int(len(Tz2)), 'aire_m2': round(float(0.5 * np.linalg.norm(np.cross(
                Pz2[Tz2[:, 1]] - Pz2[Tz2[:, 0]], Pz2[Tz2[:, 2]] - Pz2[Tz2[:, 0]]), axis=1).sum()), 1)}

    # feuilles mortes : sous la couronne des feuillus existants
    arb = lire_json(PAQUET / 'donnees/objets/arbres.geojson')['features']
    feuillus = [(f['properties']['x_local'], f['properties']['y_local'], max(1.0, 0.5 * (f['properties']['diametre_couronne_m'] or 3.0)))
                for f in arb if f['properties']['type'] == 'feuillu' and f['properties'].get('instancier')
                and 'absent' not in str(f['properties'].get('statut_2026'))]
    F = np.array(feuillus)
    rf = Raster(0.25)
    feu = np.zeros((rf.m, rf.n), dtype=np.float32)
    gx = rf.x0 + (np.arange(rf.n) + 0.5) * rf.r
    gy = rf.y1 - (np.arange(rf.m) + 0.5) * rf.r
    for x, y, r in F:
        R_ = 1.15 * r
        j0, j1 = np.searchsorted(gx, [x - R_, x + R_])
        i0, i1 = np.searchsorted(-gy, [-(y + R_), -(y - R_)])
        if j1 <= j0 or i1 <= i0:
            continue
        dd = np.hypot(gx[None, j0:j1] - x, gy[i0:i1, None] - y) / R_
        feu[i0:i1, j0:j1] = np.maximum(feu[i0:i1, j0:j1], np.clip(1.0 - dd, 0, 1) ** 0.7)
    sous = rf.lire(feu, cA[:, :2]) > 0
    fact = np.array([1.0 if VERTS.get(m) else (0.25 if m.startswith('enrobe_bbsg') else 0.7) for m in MA])
    sel = np.where(sous)[0]
    Pz, Tz = subdiviser(PA, TA[sel], lambda cxy: np.ones(len(cxy), dtype=bool), 0.6, iterations=4)
    v = rf.lire(feu, Pz[:, :2])
    # facteur de classe : celui du triangle source le plus proche (raster de classes a 0,25 m)
    im = Image.new('F', (rf.n, rf.m), 0.0)
    di = ImageDraw.Draw(im)
    for k in sel:
        di.polygon([tuple(q) for q in rf.px(PA[TA[k], :2])], fill=float(fact[k]))
    cls = np.array(im, dtype=np.float32)
    v = v * rf.lire(cls, Pz[:, :2])
    col = np.stack([v, v, v], axis=1)
    garde = col[Tz][:, :, 0].max(axis=1) > 0.02
    Pz2, Tz2, u = compacter(Pz, Tz[garde])
    zon.composant('/World/Zones/feuilles')
    Pz2, Tz2, u = sans_raides(Pz2, Tz2, u)
    zon.maillage('/World/Zones/feuilles/zone', Pz2, Tz2, 'PJ_Neutre', uv_boite(Pz2, Tz2), couleur=col[u])
    rapport['zones']['feuilles'] = {'triangles': int(len(Tz2)), 'feuillus': len(F)}
    zon.enregistrer(sortie / 'zones_pcg.usdc')
    rapport['duree_zones_s'] = round(time.time() - t1, 1)

    # ======================================================= Z du sol rendu sous les objets
    t2 = time.time()
    loc = DC.Localisateur(PA, TA, cellule=1.0)
    z = {}
    ids = [(f['properties']['id'], f['properties']['x_local'], f['properties']['y_local']) for f in arb]
    inst = lire_json(PAQUET / 'donnees/objets/instances.json')
    for l in inst['lignes']:
        for k, (x, y) in enumerate(l['points']):
            ids.append((f"{l['id']}/{k}", x, y))
    for i in inst['instances']:                       # mobilier v1 (substituts CARLA : contexte/mobilier.py)
        if not i['prototype'].startswith(('arbre', 'arbuste', 'souche')):
            ids.append((i['id'], i['x'], i['y']))
    _, zz = loc.trouver(np.array([[x, y] for _, x, y in ids]))
    for (i, _, _), v in zip(ids, zz):
        z[i] = round(float(v), 4) if np.isfinite(v) else None
    with open(sortie / 'z_objets.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'source': 'preparer_usd.py : altitude du sol rendu (v1 fondu + v2 pilote)', 'z': z}, f,
                  ensure_ascii=False, indent=0, sort_keys=True)
    rapport['z_objets'] = {'n': len(z), 'sans_sol': sum(v is None for v in z.values()), 'duree_s': round(time.time() - t2, 1)}
    if (sortie / 'lointain_entrees.json').exists():           # batiments du cadastre hors du carre v1
        import lointain_usd
        rapport['lointain'] = lointain_usd.construire(Couche, FACADES_ENDUIT, sortie / 'lointain_entrees.json',
                                                      sortie / 'lointain.usdc')
    rapport['duree_s'] = round(time.time() - t0, 1)
    with open(sortie / 'preparation.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    return rapport


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', default=str(V2 / 'fabrique_ue_snapshot'))
    ap.add_argument('--sortie', default=str(V2 / 'ue_pilote/usd'))
    a = ap.parse_args()
    r = principal(Path(a.snapshot), Path(a.sortie))
    print(json.dumps({k: r[k] for k in r if k not in ('batiments',)}, ensure_ascii=False, indent=1))
