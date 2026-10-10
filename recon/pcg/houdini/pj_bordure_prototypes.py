"""pj_bordure_prototypes : éléments préfabriqués de bordure (Houdini 22, verbes SOP en hython).

Un prototype = un élément réel : contour du profil (assets/specs/bordures.json, compléments et
corrections de bordures_elements.json, cassure de l'arête arrière haute) balayé sur sa longueur
(0,994 / 0,494 m, coupes, chartières, pièces courbes), puis :
- chanfreins d'about 3 x 3 mm sur les arêtes de tête et de face vue (PolyBevel), sauf coupes
  (abouts sciés nets) ;
- épaufrures v1-v3 (Boolean : soustraction de blocs bruités sur l'arête avant haute et les angles
  d'about ; graine = hash(nom)) ;
- normales par sommet de face (cuspide 30° : arrondis lisses, arêtes vives nettes) ;
- UV `st1` en mètres (projection boîte dans le repère de l'élément) ;
- export UE (recon/pcg/ue/CONTRAT_EXPORT.md) : Material /<nom>/Looks/<id> lié en material:binding:preview
  (Karma garde la liaison des PointInstancers de bordures.usda), normales unitaires.
Repère et pivot (bordures_elements.json, repere.pivot_prototype) : X = s le long de la bordure,
Y = u (0 = face vue, + vers l'arrière, côté haut), Z = v (0 = dessous du bloc), pivot au milieu de
l'élément (X = 0), sur la face vue (Y = 0), sous le bloc (Z = 0). Chartières : Z = 0 sous le bloc
du profil courant (extrémité haute) ; le profil abaissé est posé au même fil d'eau. USD : mètres,
Z haut, sens direct (normales sortantes) ; Houdini (main gauche) : faces retournées à l'aller et au
retour.
"""
import math

import hou
import numpy as np

import pj_commun as K
import pj_usd as U
from pxr import Sdf, UsdGeom, Vt

CAT = hou.sopNodeTypeCategory()
T = Sdf.ValueTypeNames
CHANFREIN_ABOUT = 0.003
# UsdPreviewSurface de repli des Material d'export UE (albédo linéaire, rugosité ; materiaux_sol.json, pj_materiaux)
APERCU_UE = {"beton_bordure_gris": ((0.354, 0.369, 0.336), 0.75), "caniveau_beton": ((0.354, 0.369, 0.336), 0.8),
             "mortier_joint": ((0.055, 0.055, 0.052), 0.95), "mortier_clair": ((0.27, 0.265, 0.25), 0.92)}
RETRAIT_JOINT = 0.004


def verbe(nom, parms, entrees):
    out = hou.Geometry()
    v = CAT.nodeVerb(nom)
    v.setParms(parms)
    v.execute(out, entrees)
    return out


# --------------------------------------------------------------------------- contours
def indices_chaines(c):
    """Indices clés d'un contour horaire : début de la tête (premier v = H) et arête arrière haute
    (premier u = base)."""
    base, H = c[:, 0].max(), c[:, 1].max()
    i_top = int(np.argmax(c[:, 1] >= H - 1e-9))
    k_back = int(np.argmax(np.abs(c[:, 0] - base) < 1e-9))
    return i_top, k_back


def point_arete(c):
    """Arête avant haute (épaufrures) : sommet de la chaîne avant maximisant v − u/4, et bissectrice
    sortante (normale moyenne des deux côtés adjacents)."""
    i_top, _ = indices_chaines(c)
    ch = c[:i_top + 1]
    k = int(np.argmax(ch[:, 1] - 0.25 * ch[:, 0]))
    k = min(max(k, 1), len(c) - 2)
    d0 = c[k] - c[k - 1]
    d1 = c[k + 1] - c[k]
    n0 = np.array([-d0[1], d0[0]]) / max(np.hypot(*d0), 1e-9)
    n1 = np.array([-d1[1], d1[0]]) / max(np.hypot(*d1), 1e-9)
    n = n0 + n1
    return c[k], n / max(np.hypot(*n), 1e-9)


def inset(c, d):
    """Contour convexe décalé vers l'intérieur de d (onglets aux sommets)."""
    m = len(c)
    out = np.empty_like(c)
    for i in range(m):
        a, b, e = c[i - 1], c[i], c[(i + 1) % m]
        n0 = np.array([-(b - a)[1], (b - a)[0]]) / max(np.hypot(*(b - a)), 1e-12)
        n1 = np.array([-(e - b)[1], (e - b)[0]]) / max(np.hypot(*(e - b)), 1e-12)
        nm = n0 + n1
        nm /= max(np.hypot(*nm), 1e-12)
        cos = max(float(nm @ n0), 0.3)
        out[i] = b - nm * d / cos              # normales sortantes : on recule vers l'intérieur
    return out


def _abscisse(ch):
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(ch, axis=0).T))]
    return s / max(s[-1], 1e-12)


def _resample(ch, t):
    s = _abscisse(ch)
    return np.c_[np.interp(t, s, ch[:, 0]), np.interp(t, s, ch[:, 1])]


def contours_communs(ca, cb):
    """Deux contours horaires ramenés à la même topologie (chaînes avant / tête / arrière / dessous,
    échantillonnées sur l'union des abscisses relatives des deux) pour un loft."""
    def chaines(c):
        i_top, k_back = indices_chaines(c)
        m = len(c)
        return [c[:i_top + 1], c[i_top:k_back + 1], c[k_back:m], np.vstack([c[m - 1], c[0]])]
    A, B = chaines(ca), chaines(cb)
    ra, rb = [], []
    for k, (x, y) in enumerate(zip(A, B)):
        t = np.unique(np.round(np.r_[_abscisse(x), _abscisse(y)], 6))
        if k == 3:
            t = np.array([0.0, 1.0])
        xa, xb = _resample(x, t), _resample(y, t)
        if k < 2:                                  # le dernier point est le premier de la chaîne suivante
            xa, xb = xa[:-1], xb[:-1]
        elif k == 3:                               # dessous : ses deux bouts sont déjà présents
            xa, xb = xa[:0], xb[:0]
        ra.append(xa)
        rb.append(xb)
    return np.vstack(ra), np.vstack(rb)


# --------------------------------------------------------------------------- solides
def solide(sections):
    """Anneaux (K, m, 3) -> points, faces (sens direct, normales sortantes), faces d'about."""
    S = np.asarray(sections, dtype=np.float64)
    Kn, m = S.shape[0], S.shape[1]
    P = S.reshape(-1, 3)
    faces = []
    for k in range(Kn - 1):
        for i in range(m):
            j = (i + 1) % m
            faces.append((k * m + i, (k + 1) * m + i, (k + 1) * m + j, k * m + j))
    faces.append(tuple(range(m)))
    faces.append(tuple((Kn - 1) * m + i for i in reversed(range(m))))
    if volume(P, faces) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    return P, faces


def volume(P, faces):
    v = 0.0
    for f in faces:
        a = P[f[0]]
        for i in range(1, len(f) - 1):
            v += float(np.dot(a, np.cross(P[f[i]], P[f[i + 1]]))) / 6.0
    return v


def vers_hou(P, faces):
    g = hou.Geometry()
    g.createPoints([hou.Vector3(*map(float, p)) for p in P])
    g.createPolygons([tuple(reversed(f)) for f in faces])
    return g


def depuis_hou(g):
    """Géométrie Houdini -> (P, comptes, indices, N par sommet de face) en sens direct USD."""
    P = np.array(g.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
    aN = g.findVertexAttrib("N")
    counts, idx, N = [], [], []
    for pr in g.prims():
        vs = list(pr.vertices())[::-1]
        counts.append(len(vs))
        idx += [v.point().number() for v in vs]
        if aN is not None:
            N += [v.attribValue(aN) for v in vs]
    return P, np.array(counts), np.array(idx), (np.array(N) if N else None)


def uv_boite(P, counts, idx):
    """UV st1 (m) par sommet de face : projection sur le plan le plus proche de la face."""
    st = np.empty((len(idx), 2))
    o = 0
    for c in counts:
        q = P[idx[o:o + c]]
        n = np.zeros(3)
        for i in range(c):
            a, b = q[i], q[(i + 1) % c]
            n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
        ax = int(np.argmax(np.abs(n)))
        if ax == 2:
            st[o:o + c] = q[:, [0, 1]]
        elif ax == 1:
            st[o:o + c] = q[:, [0, 2]]
        else:
            st[o:o + c] = q[:, [1, 2]]
        o += c
    return st


def groupe_about(g, m, Kn, aretes):
    """Groupe d'arêtes 'about' : côtés i -> i+1 du contour (i dans `aretes`) aux deux abouts."""
    pts = g.points()
    eg = g.createEdgeGroup("about")
    for ring in (0, Kn - 1):
        for i in aretes:
            e = g.findEdge(pts[ring * m + i], pts[ring * m + (i + 1) % m])
            if e is not None:
                eg.add(e)
    return eg


def bloc_bruite(centre, rayons, r):
    """Bloc ellipsoïdal bosselé (sphère UV 7 x 12) : forme d'éclat soustraite."""
    rows, cols = 7, 12
    pts = [np.array([0, 0, -1.0])]
    for i in range(1, rows):
        th = math.pi * i / rows - math.pi / 2
        for j in range(cols):
            ph = 2 * math.pi * j / cols
            pts.append(np.array([math.cos(th) * math.cos(ph), math.cos(th) * math.sin(ph), math.sin(th)]))
    pts.append(np.array([0, 0, 1.0]))
    D = np.array(pts)
    kv = r.normal(0, 3.0, (4, 3))
    ph0 = r.uniform(0, 2 * math.pi, 4)
    f = 1.0 + 0.22 * np.mean([np.sin(D @ k + p) for k, p in zip(kv, ph0)], axis=0) * 2
    P = centre + D * f[:, None] * np.asarray(rayons)
    faces = []
    for j in range(cols):
        faces.append((0, 1 + (j + 1) % cols, 1 + j))
    for i in range(rows - 2):
        for j in range(cols):
            a = 1 + i * cols + j
            b = 1 + i * cols + (j + 1) % cols
            faces.append((a, b, b + cols, a + cols))
    top = len(P) - 1
    for j in range(cols):
        a = 1 + (rows - 2) * cols + j
        faces.append((a, 1 + (rows - 2) * cols + (j + 1) % cols, top))
    if volume(P, faces) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    return P, faces


def blocs_epaufrures(c, L, variante, graine):
    """Blocs d'épaufrures (bordures_elements.json, epaufrures.variantes)."""
    r = np.random.default_rng(graine)
    A, nb = point_arete(c)
    base, H = c[:, 0].max(), c[:, 1].max()
    blocs = []

    def arete(x, longueur, prof):
        rp = 1.6 * prof
        rx = longueur / 2.3
        ctr = np.r_[x, A + nb * (rp - prof)]
        blocs.append(bloc_bruite(ctr, (rx, rp, rp), r))

    def coin(x, longueur, prof, arriere=False):
        rp = 1.4 * prof
        if arriere:
            ctr = np.r_[x, base + 0.35 * rp, H + 0.35 * rp]
        else:
            ctr = np.r_[x, A + nb * (rp - prof)]
        blocs.append(bloc_bruite(ctr, (longueur / 2, rp, rp), r))
    bout = lambda: (L / 2) * (1 if r.uniform() < 0.5 else -1)
    if variante == 1:
        coin(bout(), r.uniform(0.015, 0.030), r.uniform(0.005, 0.010))
    elif variante == 2:
        arete(r.uniform(-L / 2 + 0.12, L / 2 - 0.12), r.uniform(0.030, 0.060), r.uniform(0.004, 0.008))
        coin(bout(), r.uniform(0.010, 0.015), r.uniform(0.004, 0.006))
    elif variante == 3:
        for _ in range(int(r.integers(2, 4))):
            arete(r.uniform(-L / 2 + 0.08, L / 2 - 0.08), r.uniform(0.020, 0.050), r.uniform(0.004, 0.008))
        coin(bout(), r.uniform(0.015, 0.025), r.uniform(0.005, 0.009), arriere=True)
    if not blocs:
        return None
    P, F, o = [], [], 0
    for p, f in blocs:
        P.append(p)
        F += [tuple(i + o for i in t) for t in f]
        o += len(p)
    return vers_hou(np.vstack(P), F)


def finir(P, faces, m, Kn, aretes_about, chanfrein, blocs):
    """Chanfreins d'about, épaufrures, polygones convexes, normales ; renvoie les tableaux USD."""
    g = vers_hou(P, faces)
    if chanfrein and aretes_about:
        groupe_about(g, m, Kn, aretes_about)
        try:
            g2 = verbe("polybevel::3.0", {"group": "about", "grouptype": 2, "offset": CHANFREIN_ABOUT,
                                          "filletshape": 3, "divisions": 1}, [g])
            if len(g2.prims()) > len(g.prims()):
                g = g2
        except hou.OperationFailed:
            pass
    if blocs is not None:
        try:
            g2 = verbe("boolean::2.0", {"asurface": 0, "bsurface": 0, "booleanop": 2, "subtractchoices": 0}, [g, blocs])
            if len(g2.prims()) > 0:
                g = g2
        except hou.OperationFailed:
            pass
    g = verbe("divide", {"convex": 1, "numsides": 4}, [g])
    g = verbe("normal", {"type": 1, "cuspangle": 30.0}, [g])
    P, counts, idx, N = depuis_hou(g)
    return P, counts, idx, N, uv_boite(P, counts, idx)


# --------------------------------------------------------------------------- types de prototypes
def droit(specs, profil, L, variante=0, coupe=False, nom="", contour=None):
    c = specs.contour(profil) if contour is None else contour
    _, k_back = indices_chaines(c)
    secs = [np.c_[np.full(len(c), x), c] for x in (-L / 2, L / 2)]
    P, F = solide(secs)
    blocs = blocs_epaufrures(c, L, variante, K.graine(nom)) if variante else None
    return finir(P, F, len(c), 2, list(range(k_back)), not coupe, blocs)


def joint(specs, profil, joint_m=0.006, retrait=RETRAIT_JOINT, contour=None):
    """Bouchon de mortier : contour du profil réduit de `retrait` (4 mm : joint sombre en retrait ;
    1 mm : mortier clair à fleur), long de joint + 2 x 2 mm (sous les abouts voisins)."""
    c = inset(specs.contour(profil) if contour is None else contour, retrait)
    L = joint_m + 0.004
    secs = [np.c_[np.full(len(c), x), c] for x in (-L / 2, L / 2)]
    P, F = solide(secs)
    return finir(P, F, len(c), 2, [], False, None)


def chartiere(specs, profil_haut, vue_haut, profil_bas, vue_bas, L, sens, chemin_xy=None, biais=(0.0, 0.0)):
    """Raccord : loft du contour courant (posé à vue_haut) vers le contour abaissé (vue_bas), au
    même fil d'eau ; repère du bloc courant ; 'desc' = haut en −X, 'asc' = haut en +X. `chemin_xy`
    (chartière sur une courbe, revue conformité r2) : loft le long de la face vue (repère de l'élément,
    origine au milieu de la corde), abouts radiaux."""
    ca = specs.contour(profil_haut)
    cb = specs.contour(profil_bas)
    _, Ha = specs.dims(profil_haut)
    _, Hb = specs.dims(profil_bas)
    cb = cb + np.array([0.0, (Ha - vue_haut) - (Hb - vue_bas)])
    a, b = contours_communs(ca, cb)
    if chemin_xy is not None:
        Q = np.asarray(chemin_xy, dtype=np.float64)
        nrm = K.normales_gauches(Q)
        ts = _abscisse(Q)
    else:
        xs = np.linspace(-L / 2, L / 2, 6)
        Q = np.c_[xs, np.zeros(len(xs))]
        nrm = np.tile([0.0, 1.0], (len(xs), 1))
        ts = (xs + L / 2) / L
    secs, us = [], []
    for q, n, t in zip(Q, nrm, ts):
        if sens == "asc":
            t = 1 - t
        cc = (1 - t) * a + t * b
        secs.append(np.c_[q[0] + cc[:, 0] * n[0], q[1] + cc[:, 0] * n[1], cc[:, 1]])
        us.append(cc[:, 0])
    for k, bb, sg in ((0, biais[0], 1.0), (-1, biais[1], -1.0)):        # abouts en onglet (coude)
        if abs(bb) > 1e-6:
            tt = np.array([nrm[k][1], -nrm[k][0]])
            secs[k][:, :2] += sg * np.outer(us[k] * math.tan(bb), tt)
    _, k_back = indices_chaines(a)
    P, F = solide(secs)
    return finir(P, F, len(a), len(secs), list(range(k_back)), True, None)


def courbe(specs, profil, chemin_xy, contour=None, biais=(0.0, 0.0)):
    """Pièce courbe sur mesure : balayage du contour le long de `chemin_xy` (face vue, repère de
    l'élément), côté haut à gauche (caniveau : contour en u < 0, devant la face). `biais` (rad) :
    abouts en onglet (angle vif) ; la normale d'about du début est tournée de −biais[0], celle de la
    fin de +biais[1] (+ = vers la gauche) : à la profondeur u, l'about recule de u·tan(biais)."""
    c = specs.contour(profil) if contour is None else contour
    _, k_back = indices_chaines(c)
    Q = np.asarray(chemin_xy, dtype=np.float64)
    nrm = K.normales_gauches(Q)
    secs = [np.c_[q[0] + c[:, 0] * n[0], q[1] + c[:, 0] * n[1], c[:, 1]] for q, n in zip(Q, nrm)]
    for k, b, sg in ((0, biais[0], 1.0), (-1, biais[1], -1.0)):
        if abs(b) > 1e-6:
            t = np.array([nrm[k][1], -nrm[k][0]])            # tangente (+s)
            secs[k][:, :2] += sg * np.outer(c[:, 0] * math.tan(b), t)
    P, F = solide(secs)
    return finir(P, F, len(c), len(secs), list(range(k_back)), True, None)


def quart_de_rond(specs, profil, R, sens="convexe"):
    """Pièce de nez d'îlot (catalogue) : quart de cercle de rayon R sur la face vue."""
    n = 16
    th = np.linspace(-math.pi / 4, math.pi / 4, n)
    if sens == "convexe":          # centre à gauche (côté haut) : nez d'îlot
        Q = np.c_[R * np.sin(th), R - R * np.cos(th)]
    else:
        Q = np.c_[R * np.sin(th), -(R - R * np.cos(th))]
    return courbe(specs, profil, Q)


# --------------------------------------------------------------------------- écriture
def _sans_faces_nulles(P, counts, idx, N, st1, aire_min=1e-10, col_rel=1e-4):
    """Retire les sommets de face confondus ou alignés avec leurs voisins (bouts de chanfrein laissés par Divide :
    triangles nuls dans la triangulation d'UE, tangentes nulles) puis les faces d'aire nulle (éclats du Boolean :
    normales nulles, CONTRAT_EXPORT.md § 3) ; normalise les normales ; tableaux par sommet de face filtrés de même."""
    P, counts, idx = np.asarray(P, dtype=np.float64), np.asarray(counts), np.asarray(idx)
    N, st1 = np.asarray(N, dtype=np.float64), np.asarray(st1, dtype=np.float64)
    garde_c = np.ones(len(idx), dtype=bool)
    o = 0
    for k, c in enumerate(counts):
        coins = list(range(o, o + c))
        change = True
        while change and len(coins) > 3:
            change = False
            for j in range(len(coins)):
                a, b, d = (P[idx[coins[(j + i) % len(coins)]]] for i in (-1, 0, 1))
                ln = max(np.linalg.norm(b - a), np.linalg.norm(d - b), 1e-12)
                if np.linalg.norm(b - a) < 1e-7 or 0.5 * np.linalg.norm(np.cross(b - a, d - b)) < col_rel * ln * ln:
                    garde_c[coins.pop(j)] = False
                    change = True
                    break
        o += c
    counts = np.array([int(garde_c[o:o + c].sum()) for o, c in zip(np.r_[0, np.cumsum(counts)[:-1]], counts)])
    idx, N, st1 = idx[garde_c], N[garde_c], st1[garde_c]
    debut = np.r_[0, np.cumsum(counts)[:-1]]
    l2 = np.array([max(float(np.sum((P[idx[d + i]] - P[idx[d + (i + 1) % c]]) ** 2)) for i in range(c))
                   for d, c in zip(debut, counts)])
    aires = _aires(P, counts, idx)
    garde_f = (aires > aire_min) & (aires > col_rel * l2)          # faces nulles et triangles en aiguille
    garde_c = np.repeat(garde_f, counts)
    counts, idx, N, st1 = counts[garde_f], idx[garde_c], N[garde_c], st1[garde_c]
    n = np.linalg.norm(N, axis=1)
    ok = np.isfinite(n) & (n > 1e-6)
    N[ok] /= n[ok, None]
    if not ok.all():
        N[~ok] = K.normales_cusp(P, counts, idx, 0.0)[~ok]
    return P, counts, idx, N, st1


def _aires(P, counts, idx):
    """Aire de chaque face (éventail de triangles)."""
    debut = np.r_[0, np.cumsum(counts)[:-1]]
    v = np.zeros((len(counts), 3))
    for k in range(1, int(np.max(counts)) - 1):
        sel = counts > k + 1
        a = P[idx[debut[sel]]]
        v[sel] += np.cross(P[idx[debut[sel] + k]] - a, P[idx[debut[sel] + k + 1]] - a)
    return 0.5 * np.linalg.norm(v, axis=1)


def ecrire_prototype(chemin, nom, donnees, meta):
    P, counts, idx, N, st1 = donnees
    st = U.scene(f"Prototype de bordure {nom} (pj_bordure_prototypes.py) : X = s, Y = u (face vue en 0, "
                 "arrière +), Z = v (dessous du bloc en 0) ; pivot au milieu de l'élément, sur la face vue, "
                 "sous le bloc ; mètres, Z haut.", racine=nom)
    root = st.GetDefaultPrim()
    from pxr import Usd
    Usd.ModelAPI(root).SetKind("component")
    for k in sorted(meta):
        root.SetCustomDataByKey(k, meta[k])
    mid = "mortier_clair" if nom.startswith("jointf_") else "mortier_joint" if nom.startswith("joint_") \
        else "caniveau_beton" if nom.startswith("caniveau_") else "beton_bordure"
    P, counts, idx, N, st1 = _sans_faces_nulles(P, counts, idx, N, st1)
    m = U.maillage(st, f"/{nom}/maillage", P, counts, idx, normales=N, st1=st1, materiau_id=mid)
    ue = "beton_bordure_gris" if mid == "beton_bordure" else mid
    m.GetPrim().CreateAttribute("unrealMaterial", T.String).Set(f"/Game/PJ/Materials/MI_{ue}.MI_{ue}")
    K.lier_ue(m.GetPrim(), ue, *APERCU_UE[ue])
    U.enregistrer(st, chemin)
    return {"faces": int(len(counts)), "points": int(len(P)),
            "dims_m": K.r3(P.max(axis=0) - P.min(axis=0), 4)}


def fabriquer(specs, demandes, dossier, log=print):
    """demandes : {nom: dict(type, profil, ...)} -> fichiers prototypes/<nom>.usda ; renvoie l'index."""
    index = {}
    for nom in sorted(demandes):
        d = demandes[nom]
        t = d["type"]
        if t == "element":
            don = droit(specs, d["profil"], d["longueur"], d.get("variante", 0), False, nom)
        elif t == "coupe":
            don = droit(specs, d["profil"], d["longueur"], 0, True, nom)
        elif t == "joint":
            don = joint(specs, d["profil"], d.get("joint", 0.006), 0.001 if d.get("affleurant") else RETRAIT_JOINT)
        elif t == "joint_caniveau":
            don = joint(specs, d["profil"], d.get("joint", 0.006), RETRAIT_JOINT, specs.contour_caniveau(d["profil"]))
        elif t == "caniveau":
            don = droit(specs, d["profil"], d["longueur"], 0, bool(d.get("coupe")), nom, specs.contour_caniveau(d["profil"]))
        elif t == "caniveau_courbe":
            don = courbe(specs, d["profil"], d["chemin"], specs.contour_caniveau(d["profil"]))
        elif t == "chartiere":
            don = chartiere(specs, d["profil"], d["vue_haut"], d["profil_bas"], d["vue_bas"], d["longueur"], d["sens"],
                            d.get("chemin"), (d.get("biais_debut", 0.0), d.get("biais_fin", 0.0)))
        elif t == "courbe":
            don = courbe(specs, d["profil"], d["chemin"], biais=(d.get("biais_debut", 0.0), d.get("biais_fin", 0.0)))
        elif t == "quart_de_rond":
            don = quart_de_rond(specs, d["profil"], d["rayon"])
        else:
            raise ValueError(t)
        sous = "courbes/" if t in ("courbe", "caniveau_courbe") else ""
        chemin = dossier / f"{sous}{nom}.usda"
        meta = {k: v for k, v in d.items() if k != "chemin" and isinstance(v, (str, int, float))}
        info = ecrire_prototype(chemin, nom, don, meta)
        index[nom] = dict(meta, fichier=f"prototypes/{sous}{nom}.usda", ue=f"/Game/PJ/Lib/Bordures/SM_{nom}", **info)
    log(f"   prototypes : {len(index)}")
    return index
