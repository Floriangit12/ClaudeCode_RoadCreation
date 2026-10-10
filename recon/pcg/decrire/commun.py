"""Outils communs de la description v2 : repère, GeoJSON déterministe, MNT 2026, géométrie numpy.

Repère unique (recon/CONVENTIONS.md) : local = Lambert-93 − O, z = NGF − 216,30 ; mètres,
Z vers le haut, X à l'est, Y au nord. Toute conversion passe par `repere()` (et nulle part ailleurs).

Aucune dépendance hors numpy / Pillow (pas de shapely) : les découpes de polygones et de
polylignes sont écrites ici (demi-plans successifs pour une zone convexe).
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[3]
O = (917279.43, 6460289.98, 216.30)
CRS = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}}
SCHEMA_ID = "description_scene_v2/0.1"

PAQUET = RACINE / "recon/out/paquet_jardin/package"
DONNEES = PAQUET / "donnees"
VECTEURS = RACINE / "data/sites/paquet_jardin"
SPECS = RACINE / "assets/specs"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/description"
ZONE = RACINE / "recon/pcg/zone_pilote.geojson"
SCHEMA = RACINE / "recon/pcg/schema/description_scene_v2.schema.json"
MATERIAUX = RACINE / "recon/pcg/schema/materiaux_description.json"

ND_XY = 3          # arrondi des coordonnées (mm)
ND_Z = 3
ND_ATTR = 3


# --------------------------------------------------------------------------- repère
def repere(pts, vers="local"):
    """Seule conversion du projet : L93/NGF -> local (vers="local") ou local -> L93/NGF ("l93").
    pts : (N, 2) ou (N, 3) ; renvoie un tableau float64 de même forme."""
    a = np.array(pts, dtype=np.float64)
    o = np.array(O[:a.shape[-1]])
    if vers == "local":
        return a - o
    if vers == "l93":
        return a + o
    raise ValueError(f"repère inconnu : {vers}")


# --------------------------------------------------------------------------- IO
def rel(p):
    """Chemin relatif à la racine du dépôt (POSIX), ou absolu s'il est hors du dépôt."""
    p = Path(p).resolve()
    try:
        return p.relative_to(RACINE).as_posix()
    except ValueError:
        return p.as_posix()


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def lire_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def lire_geojson(chemin):
    return lire_json(chemin)["features"]


def arrondi(v, nd=ND_ATTR):
    """Arrondi récursif (dict, list, float, numpy) ; supprime les -0.0."""
    if isinstance(v, dict):
        return {k: arrondi(x, nd) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [arrondi(x, nd) for x in v]
    if isinstance(v, (np.floating, float)):
        if not math.isfinite(float(v)):
            return None
        return round(float(v), nd) + 0.0
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def coords_geojson(a, nd=ND_XY):
    """Tableau (N, 2|3) -> liste de listes arrondies."""
    return [[round(float(c), nd) + 0.0 for c in p] for p in np.asarray(a)]


def ecrire_json(chemin, obj):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False)
    chemin.write_text(txt + "\n", encoding="utf-8", newline="\n")


def ecrire_geojson(chemin, features, nom, entete=None):
    """FeatureCollection déterministe : entités triées par id, une entité par ligne, CRS EPSG:2154."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    feats = sorted(features, key=lambda f: f["properties"]["id"])
    tete = {"type": "FeatureCollection", "name": nom, "crs": CRS}
    if entete:
        tete["description_v2"] = entete
    d = json.dumps(tete, ensure_ascii=False)[:-1]
    lignes = [d + ',\n"features": [']
    for i, f in enumerate(feats):
        lignes.append(json.dumps(f, ensure_ascii=False, separators=(",", ":"))
                      + ("," if i < len(feats) - 1 else ""))
    lignes.append("]}")
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- MNT 2026
class MNT:
    """Sol nu octobre 2026 (heightmap_3025_10cm.png + .json du paquet), interpolation bilinéaire.
    Valeur au NŒUD : colonne c -> x_min + c·pas ; ligne r -> y_max − r·pas (ligne 0 = nord)."""

    def __init__(self, chemin_json=DONNEES / "relief/heightmap_3025_10cm.json"):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        self.meta = lire_json(chemin_json)
        self.png = Path(chemin_json).with_name(self.meta["fichier"])
        a = np.array(Image.open(self.png)).astype(np.float64)
        z0, z1 = self.meta["z_min_m_NGF"], self.meta["z_max_m_NGF"]
        self.z = z0 + a / 65535.0 * (z1 - z0)
        e = self.meta["emprise_noeuds_L93"]
        self.x0, self.y1, self.pas = e["x_min"], e["y_max"], self.meta["taille_pixel_m"]
        self.n = self.z.shape[0]

    def __call__(self, x, y):
        """Altitude NGF aux points L93 (tableaux)."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        fc = np.clip((x - self.x0) / self.pas, 0, self.n - 1.000001)
        fr = np.clip((self.y1 - y) / self.pas, 0, self.n - 1.000001)
        c, r = np.floor(fc).astype(int), np.floor(fr).astype(int)
        tc, tr = fc - c, fr - r
        z = self.z
        return ((z[r, c] * (1 - tc) + z[r, c + 1] * tc) * (1 - tr)
                + (z[r + 1, c] * (1 - tc) + z[r + 1, c + 1] * tc) * tr)


# --------------------------------------------------------------------------- polylignes
def abscisses(P):
    P = np.asarray(P)[:, :2]
    if len(P) < 2:
        return np.zeros(len(P))
    return np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]


def dedoublonner_sommets(P, tol=1e-4):
    P = np.asarray(P, dtype=np.float64)
    if len(P) < 2:
        return P
    garde = np.r_[True, np.hypot(*np.diff(P[:, :2], axis=0).T) > tol]
    return P[garde]


def point_a(P, s):
    """Points et tangentes unitaires à l'abscisse s (scalaire ou tableau), bornée à [0, L]."""
    P = np.asarray(P, dtype=np.float64)
    S = abscisses(P)
    s = np.clip(np.atleast_1d(np.asarray(s, dtype=np.float64)), 0.0, S[-1])
    i = np.clip(np.searchsorted(S, s, side="right") - 1, 0, len(P) - 2)
    L = np.maximum(S[i + 1] - S[i], 1e-12)
    t = ((s - S[i]) / L)[:, None]
    pts = P[i] * (1 - t) + P[i + 1] * t
    d = P[i + 1, :2] - P[i, :2]
    tg = d / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)[:, None]
    return pts, tg


def sous_polyligne(P, s0, s1):
    """Morceau de P entre s0 et s1 (sommets d'origine conservés)."""
    P = np.asarray(P, dtype=np.float64)
    S = abscisses(P)
    a, _ = point_a(P, s0)
    b, _ = point_a(P, s1)
    milieu = P[(S > s0 + 1e-6) & (S < s1 - 1e-6)]
    return dedoublonner_sommets(np.vstack([a, milieu, b]))


def densifier(P, pas):
    """Sommets d'origine + points tous les `pas` m (pour porter un Z par sommet)."""
    P = dedoublonner_sommets(P)
    S = abscisses(P)
    n = max(1, int(math.ceil(S[-1] / pas - 1e-9)))
    g = np.linspace(0.0, S[-1], n + 1)
    loin = np.min(np.abs(g[:, None] - S[None]), axis=1) > 0.05
    s = np.unique(np.r_[S, g[loin]])
    pts, _ = point_a(P, s)
    return pts, s


def normale_gauche(tg):
    return np.c_[-tg[:, 1], tg[:, 0]]


def decaler(P, d):
    """Polyligne décalée de d (d > 0 à gauche du sens de parcours), onglets limités."""
    P = np.asarray(P, dtype=np.float64)[:, :2]
    seg = np.diff(P, axis=0)
    n = normale_gauche(seg / np.maximum(np.hypot(seg[:, 0], seg[:, 1]), 1e-12)[:, None])
    nv = np.vstack([n[:1], n[:-1] + n[1:], n[-1:]])
    nv /= np.maximum(np.hypot(nv[:, 0], nv[:, 1]), 1e-12)[:, None]
    nn = np.vstack([n[:1], n, n[-1:]])
    cosa = np.maximum(np.einsum("ij,ij->i", nv, nn[:-1]), 0.5)
    return P + nv * (d / cosa)[:, None]


def rayon_courbure(P, s, h=1.0):
    """Rayon du cercle passant par les points à s−h, s, s+h (inf si aligné)."""
    S = abscisses(P)
    s = np.atleast_1d(s)
    a, _ = point_a(P, np.clip(s - h, 0, S[-1]))
    b, _ = point_a(P, s)
    c, _ = point_a(P, np.clip(s + h, 0, S[-1]))
    ab = np.hypot(*(b - a)[:, :2].T)
    bc = np.hypot(*(c - b)[:, :2].T)
    ca = np.hypot(*(a - c)[:, :2].T)
    cr = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    with np.errstate(divide="ignore", invalid="ignore"):
        r = ab * bc * ca / (2.0 * cr)
    r[~np.isfinite(r)] = np.inf
    return r


def projeter(P, Q):
    """Projection de points Q sur la polyligne P : (s, distance, côté) ; côté +1 = gauche."""
    P = np.asarray(P, dtype=np.float64)[:, :2]
    Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))[:, :2]
    S = abscisses(P)
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = np.maximum(np.einsum("ij,ij->i", AB, AB), 1e-18)
    s_out = np.empty(len(Q))
    d_out = np.empty(len(Q))
    c_out = np.empty(len(Q))
    for k0 in range(0, len(Q), 2048):
        q = Q[k0:k0 + 2048]
        AQ = q[:, None, :] - A[None]
        t = np.clip(np.einsum("qij,ij->qi", AQ, AB) / L2, 0, 1)
        proj = A[None] + t[..., None] * AB[None]
        d = np.hypot(*(q[:, None, :] - proj).transpose(2, 0, 1))
        j = np.argmin(d, axis=1)
        r = np.arange(len(q))
        s_out[k0:k0 + 2048] = S[j] + t[r, j] * np.sqrt(L2[j])
        d_out[k0:k0 + 2048] = d[r, j]
        cr = AB[j, 0] * AQ[r, j, 1] - AB[j, 1] * AQ[r, j, 0]
        c_out[k0:k0 + 2048] = np.where(cr >= 0, 1.0, -1.0)
    return s_out, d_out, c_out


def distance_segments(Q, A, B):
    """Point le plus proche de chaque Q sur un ensemble de segments [A, B] :
    (distance, indice du segment, point projeté)."""
    Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))[:, :2]
    if len(A) == 0:
        return np.full(len(Q), np.inf), np.full(len(Q), -1), np.full((len(Q), 2), np.nan)
    AB = B - A
    L2 = np.maximum(np.einsum("ij,ij->i", AB, AB), 1e-18)
    dmin = np.empty(len(Q))
    jmin = np.empty(len(Q), dtype=int)
    proj = np.empty((len(Q), 2))
    pas = max(1, 2_000_000 // max(len(A), 1))
    for k0 in range(0, len(Q), pas):
        q = Q[k0:k0 + pas]
        AQ = q[:, None, :] - A[None]
        t = np.clip(np.einsum("qij,ij->qi", AQ, AB) / L2, 0, 1)
        d = np.hypot(*(AQ - t[..., None] * AB[None]).transpose(2, 0, 1))
        j = np.argmin(d, axis=1)
        r = np.arange(len(q))
        jmin[k0:k0 + pas] = j
        dmin[k0:k0 + pas] = d[r, j]
        proj[k0:k0 + pas] = A[j] + t[r, j][:, None] * AB[j]
    return dmin, jmin, proj


# --------------------------------------------------------------------------- polygones
def anneaux(geom):
    """Liste de polygones [[anneau_ext, trous...], ...] (tableaux (N,2), sans point de fermeture)."""
    t = geom["type"]
    polys = [geom["coordinates"]] if t == "Polygon" else geom["coordinates"] if t == "MultiPolygon" else []
    out = []
    for p in polys:
        rs = []
        for r in p:
            a = np.asarray(r, dtype=np.float64)[:, :2]
            if len(a) > 1 and np.allclose(a[0], a[-1]):
                a = a[:-1]
            rs.append(dedoublonner_sommets(a))
        out.append(rs)
    return out


def aire_signee(r):
    r = np.asarray(r)
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def orienter(poly):
    """Anneau extérieur anti-horaire, trous horaires (convention GeoJSON RFC 7946)."""
    out = []
    for k, r in enumerate(poly):
        a = aire_signee(r)
        if (k == 0 and a < 0) or (k > 0 and a > 0):
            r = r[::-1]
        out.append(r)
    return out


def dans_polygone(Q, poly):
    """Test pair-impair (anneau extérieur + trous) pour des points Q (N, 2)."""
    Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))
    x, y = Q[:, 0], Q[:, 1]
    dedans = np.zeros(len(Q), dtype=bool)
    for r in poly:
        xa, ya = r[:, 0], r[:, 1]
        xb, yb = np.roll(xa, -1), np.roll(ya, -1)
        for k0 in range(0, len(Q), 4096):
            xx, yy = x[k0:k0 + 4096, None], y[k0:k0 + 4096, None]
            cond = (ya[None] > yy) != (yb[None] > yy)
            with np.errstate(divide="ignore", invalid="ignore"):
                xi = xa[None] + (yy - ya[None]) * (xb - xa)[None] / (yb - ya)[None]
            croise = cond & (xx < xi)
            dedans[k0:k0 + 4096] ^= (np.count_nonzero(croise, axis=1) % 2).astype(bool)
    return dedans


def dans_polygones(Q, polys):
    m = np.zeros(len(np.atleast_2d(Q)), dtype=bool)
    for p in polys:
        m |= dans_polygone(Q, p)
    return m


def aretes(poly):
    A = np.vstack(poly)
    B = np.vstack([np.roll(r, -1, axis=0) for r in poly])
    return A, B


def _couper_demi_plan(poly, n, c):
    """Partie du polygone (liste d'anneaux orientés) où n·p + c ≥ 0 ; résultat multi-polygone.
    Méthode : chaînes intérieures de chaque anneau, puis appariement des points d'intersection
    triés le long de la droite (entrée/sortie alternées), ce qui gère plusieurs morceaux et les trous."""
    n = np.asarray(n, dtype=np.float64)
    dirl = np.array([-n[1], n[0]])
    chaines, libres = [], []
    for r in poly:
        f = r @ n + c
        f = np.where(np.abs(f) < 1e-9, 1e-9, f)
        if np.all(f > 0):
            libres.append(r)
            continue
        if np.all(f < 0):
            continue
        m = len(r)
        k0 = int(np.argmax(f < 0))
        ordre = [(k0 + i) % m for i in range(m)]
        courant = None
        for i in ordre:
            j = (i + 1) % m
            if f[i] > 0:
                courant.append(r[i])
            if (f[i] > 0) != (f[j] > 0):
                t = f[i] / (f[i] - f[j])
                p = r[i] + t * (r[j] - r[i])
                if f[i] < 0:
                    courant = [p]
                else:
                    courant.append(p)
                    chaines.append(np.array(courant))
                    courant = None
    if not chaines:
        return _assembler(libres)
    entrees = np.array([ch[0] for ch in chaines])
    sorties = np.array([ch[-1] for ch in chaines])
    pts = np.vstack([entrees, sorties])
    genre = np.r_[np.zeros(len(chaines), int), np.ones(len(chaines), int)]
    idx = np.r_[np.arange(len(chaines)), np.arange(len(chaines))]
    o = np.lexsort((genre, pts @ dirl))
    suivant = {}
    for a, b in zip(o[0::2], o[1::2]):
        if genre[a] == 1 and genre[b] == 0:
            suivant[idx[a]] = idx[b]
        elif genre[a] == 0 and genre[b] == 1:
            suivant[idx[b]] = idx[a]
    vus, anneaux_ = set(), list(libres)
    for k in range(len(chaines)):
        if k in vus:
            continue
        morceaux, j = [], k
        while j not in vus and j is not None:
            vus.add(j)
            morceaux.append(chaines[j])
            j = suivant.get(j)
        a = dedoublonner_sommets(np.vstack(morceaux))
        if len(a) > 1 and np.allclose(a[0], a[-1]):
            a = a[:-1]
        if len(a) >= 3 and abs(aire_signee(a)) > 1e-6:
            anneaux_.append(a)
    return _assembler(anneaux_)


def _assembler(rs):
    """Anneaux orientés -> polygones : extérieurs (aire > 0) + trous rattachés par inclusion."""
    ext = [r for r in rs if aire_signee(r) > 0]
    trous = [r for r in rs if aire_signee(r) < 0]
    polys = [[e] for e in ext]
    for t in trous:
        for p in polys:
            if dans_polygone(t[:1], [p[0]])[0]:
                p.append(t)
                break
    return polys


def couper_polygone(poly, zone):
    """Intersection d'un polygone (anneaux) avec une zone CONVEXE (anneau anti-horaire)."""
    morceaux = [orienter(poly)]
    zone = np.asarray(zone, dtype=np.float64)
    for i in range(len(zone)):
        a, b = zone[i], zone[(i + 1) % len(zone)]
        d = b - a
        n = np.array([-d[1], d[0]])                 # intérieur à gauche (zone anti-horaire)
        c = -float(n @ a)
        nouveaux = []
        for p in morceaux:
            nouveaux += _couper_demi_plan(p, n, c)
        morceaux = nouveaux
    return [p for p in morceaux if aire_signee(p[0]) > 1e-4]


def couper_polyligne(P, poly):
    """Morceaux de la polyligne P à l'intérieur du polygone ; renvoie [(s0, s1), ...] sur P."""
    P = np.asarray(P, dtype=np.float64)[:, :2]
    S = abscisses(P)
    A, B = aretes(poly)
    coupes = [0.0, S[-1]]
    for i in range(len(P) - 1):
        p, q = P[i], P[i + 1]
        r = q - p
        s_ = B - A
        den = r[0] * s_[:, 1] - r[1] * s_[:, 0]
        ok = np.abs(den) > 1e-12
        ap = A - p
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (ap[:, 0] * s_[:, 1] - ap[:, 1] * s_[:, 0]) / den
            u = (ap[:, 0] * r[1] - ap[:, 1] * r[0]) / den
        m = ok & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
        coupes += list(S[i] + t[m] * (S[i + 1] - S[i]))
    coupes = np.unique(np.round(coupes, 6))
    morceaux = []
    for s0, s1 in zip(coupes[:-1], coupes[1:]):
        if s1 - s0 < 1e-6:
            continue
        mid, _ = point_a(P, 0.5 * (s0 + s1))
        if dans_polygone(mid, poly)[0]:
            if morceaux and abs(morceaux[-1][1] - s0) < 1e-6:
                morceaux[-1] = (morceaux[-1][0], s1)
            else:
                morceaux.append((s0, s1))
    return morceaux


def geom_polygones(polys, nd=ND_XY, z=None):
    """Polygones (anneaux sans fermeture) -> géométrie GeoJSON Polygon / MultiPolygon fermée."""
    def ferme(r):
        r = np.vstack([r, r[:1]])
        if z is not None:
            r = np.c_[r, np.full(len(r), z)]
        return coords_geojson(r, nd)
    cs = [[ferme(r) for r in orienter(p)] for p in polys]
    if len(cs) == 1:
        return {"type": "Polygon", "coordinates": cs[0]}
    return {"type": "MultiPolygon", "coordinates": cs}


def echantillons_interieurs(poly, pas):
    """Grille régulière de points intérieurs au polygone (au moins le centroïde des sommets)."""
    a = poly[0]
    x0, y0 = a.min(axis=0)
    x1, y1 = a.max(axis=0)
    xs = np.arange(math.floor(x0 / pas) * pas + pas / 2, x1, pas)
    ys = np.arange(math.floor(y0 / pas) * pas + pas / 2, y1, pas)
    if len(xs) == 0 or len(ys) == 0:
        return a.mean(axis=0, keepdims=True)
    X, Y = np.meshgrid(xs, ys)
    Q = np.c_[X.ravel(), Y.ravel()]
    Q = Q[dans_polygone(Q, poly)]
    return Q if len(Q) else a.mean(axis=0, keepdims=True)


def mediane_glissante(v, k):
    """Médiane glissante centrée de fenêtre impaire k (bords : fenêtre tronquée)."""
    v = np.asarray(v, dtype=np.float64)
    h = k // 2
    return np.array([np.nanmedian(v[max(0, i - h):i + h + 1]) for i in range(len(v))])


def intervalles_masque(m, s, debut=None, fin=None):
    """Runs de True d'un masque échantillonné aux abscisses s -> [(s_debut, s_fin), ...] ; bornes
    entre échantillons, et `debut` / `fin` (défaut : premier / dernier échantillon) aux extrémités."""
    out = []
    m = np.asarray(m, dtype=bool)
    if not m.any():
        return out
    pas = np.diff(s)
    bord_g = np.r_[s[0] if debut is None else debut, s[:-1] + pas / 2]
    bord_d = np.r_[s[:-1] + pas / 2, s[-1] if fin is None else fin]
    i = 0
    while i < len(m):
        if m[i]:
            j = i
            while j + 1 < len(m) and m[j + 1]:
                j += 1
            out.append((float(bord_g[i]), float(bord_d[j])))
            i = j + 1
        else:
            i += 1
    return out
