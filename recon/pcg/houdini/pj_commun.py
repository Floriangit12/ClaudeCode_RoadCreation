"""Outils communs de la fabrication v2 (hython Houdini 22) : chemins, description, specs, graines.

Repère : celui de la description (recon/pcg/README.md). Toute conversion L93/NGF <-> local passe
par `decrire/commun.py: repere()` (seule fonction de conversion du projet), réexportée ici.
Z : fil d'eau de la description (MNT 2026) et MNT 2026, jamais les maillages v1.

Déterminisme : graine = sha256(id | version de règle) ; aucun horodatage ; listes triées par id ;
aucune itération sur un `set` (ordre dépendant de PYTHONHASHSEED).
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent                       # recon/pcg/houdini
RACINE = ICI.parents[2]
sys.path.insert(0, str(ICI.parent / "decrire"))
import commun as C                                          # noqa: E402  (repere, MNT, géométrie)

repere = C.repere

VERSION = "pj_fabrique/0.1"
DESCRIPTION = RACINE / "recon/out/paquet_jardin/v2/description"
FABRIQUE = RACINE / "recon/out/paquet_jardin/v2/fabrique"
SPECS = RACINE / "assets/specs"
LIB_MAT = RACINE / "assets/lib/materiaux"
PAQUET_V1 = RACINE / "recon/out/paquet_jardin/package"
PC_HOUDINI = RACINE / "recon/pc/houdini"


# --------------------------------------------------------------------------- graines
def graine(*parts):
    """Graine entière (31 bits) = sha256(parts | VERSION) : stable d'une exécution à l'autre."""
    t = "|".join(str(p) for p in parts) + "|" + VERSION
    return int.from_bytes(hashlib.sha256(t.encode("utf-8")).digest()[:4], "little") & 0x7FFFFFFF


def rng(*parts):
    return np.random.default_rng(graine(*parts))


# --------------------------------------------------------------------------- IO
def lire_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def ecrire_json(chemin, obj, indent=1):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=indent)
    chemin.write_text(txt + "\n", encoding="utf-8", newline="\n")


def ecrire_points(chemin, famille, points, source_hash, entete=None):
    """Fichier pj_points/0.1 : un point par ligne (lisible, comparable), points triés par id."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tete = {"schema": "pj_points/0.1", "famille": famille, "source_hash": source_hash}
    if entete:
        tete.update(entete)
    pts = sorted(points, key=lambda p: p["id"])
    lignes = [json.dumps(tete, ensure_ascii=False)[:-1] + ',\n"points": [']
    for i, p in enumerate(pts):
        lignes.append(json.dumps(p, ensure_ascii=False, separators=(",", ":"))
                      + ("," if i < len(pts) - 1 else ""))
    lignes.append("]}")
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")


def sha256(chemin):
    return C.sha256(chemin)


def rel(p):
    return C.rel(p)


def r3(v, nd=4):
    """Arrondi (liste, tableau, scalaire) pour les sorties JSON."""
    if isinstance(v, (list, tuple, np.ndarray)):
        return [r3(x, nd) for x in v]
    return round(float(v), nd) + 0.0


# --------------------------------------------------------------------------- specs
class Specs:
    """Profils (bordures.json + bordures_elements.json), éléments, matériaux du sol."""

    def __init__(self):
        self.bordures = lire_json(SPECS / "bordures.json")
        self.elements = lire_json(SPECS / "bordures_elements.json")
        self.materiaux = lire_json(SPECS / "materiaux_sol.json")
        self.rendu = lire_json(SPECS / "materiaux_rendu_v2.json")
        self.fichiers = [SPECS / "bordures.json", SPECS / "bordures_elements.json",
                         SPECS / "materiaux_sol.json", SPECS / "materiaux_rendu_v2.json"]

    def profil(self, nom):
        p = self.bordures["profils"].get(nom) or self.elements["profils_complementaires"][nom]
        return p

    def contour(self, nom):
        """Contour (u, v) du bloc, horaire, premier point = coin avant bas ; corrections V2 et
        cassure de l'arête arrière haute (bordures_elements.json, aretes)."""
        p = self.profil(nom)
        c = [list(map(float, q)) for q in p["contour"]]
        corr = self.elements.get("corrections_profils", {}).get(nom, {}).get("remplace_sommets")
        if corr:
            for a, b in zip(corr["de"], corr["par"]):
                for i, q in enumerate(c):
                    if abs(q[0] - a[0]) < 1e-9 and abs(q[1] - a[1]) < 1e-9:
                        c[i] = list(map(float, b))
        c = np.array(c)
        # cassure de l'arête arrière haute : 5 mm (T, bateau), 3 mm (P), si le contour ne l'a pas
        txt = self.elements["aretes"].get(nom, {}).get("arete_arriere_haute", "")
        e = 0.005 if "5 x 5" in txt else 0.003 if "3 x 3" in txt or "3 mm" in txt else 0.0
        base, H = c[:, 0].max(), c[:, 1].max()
        k = np.where((np.abs(c[:, 0] - base) < 1e-9) & (np.abs(c[:, 1] - H) < 1e-9))[0]
        if e > 0 and len(k) == 1:
            k = int(k[0])
            c = np.vstack([c[:k], [[base - e, H], [base, H - e]], c[k + 1:]])
        return c

    def dims(self, nom):
        c = self.contour(nom)
        return float(c[:, 0].max()), float(c[:, 1].max())          # base, H

    def contour_caniveau(self, nom):
        """Contour d'un caniveau (CS1, CS2...) dans le repère de la bordure qu'il longe : u = −largeur
        côté chaussée, u = 0 contre la face vue ; v = 0 sous le bloc, le bord côté bordure (fil d'eau)
        à h_cote_bordure (bordures.json caniveaux)."""
        p = self.profil(nom)
        c = np.array([list(map(float, q)) for q in p["contour"]])
        c[:, 0] -= float(p["largeur"])
        return c

    def caniveau(self, nom):
        p = self.profil(nom)
        return float(p["largeur"]), float(p["h_cote_bordure"]), float(p["h_cote_chaussee"])

    def element(self):
        return self.elements["element"]

    def materiau(self, mid):
        return self.materiaux["materiaux"][mid]

    def apercu_ue(self, mid):
        """(albédo linéaire, rugosité) du UsdPreviewSurface de repli de lier_ue : materiaux_sol.json, sinon gris."""
        m = self.materiaux["materiaux"].get(mid) or {}
        return (tuple(m.get("albedo_cible_lineaire") or (0.3, 0.3, 0.3)),
                float((m.get("rugosite") or {}).get("valeur", 0.8)))

    def materiau_rendu(self, mid):
        """Spec de rendu : materiaux_sol.json + surcharges de materiaux_rendu_v2.json (source CC0,
        tile_m, albédo visé, famille)."""
        m = dict(self.materiaux["materiaux"][mid])
        s = self.rendu["surcharges"].get(mid) or {}
        if s.get("source"):
            src = self.materiaux["materiaux"][s["source"]]
            for k in ("source_cc0", "tile_m", "texture_mesuree", "rugosite"):
                if k in src:
                    m[k] = src[k]
            m["facteur_albedo"] = None
        if "tile_m" in s:
            m["tile_m"] = s["tile_m"]
        if "facteur_albedo" in s:
            m["facteur_albedo"] = s["facteur_albedo"]
        if "albedo_cible" in s:
            moy = (m.get("texture_mesuree") or {}).get("albedo_moyen_lineaire") or [0.3, 0.3, 0.3]
            f = float(s["albedo_cible"]) / max(float(np.mean(moy)), 1e-3)
            m["facteur_albedo"] = [f, f, f]
        if "gain_rvb" in s:                       # teinte (après albedo_cible ou facteur_albedo)
            fa = m.get("facteur_albedo") or [1.0, 1.0, 1.0]
            m["facteur_albedo"] = [float(a) * float(g) for a, g in zip(fa, s["gain_rvb"])]
        if s.get("famille"):
            m["famille_rendu"] = s["famille"]
        return m


# --------------------------------------------------------------------------- description
SEUIL_COIN_DEG = 40.0      # au-delà : coin vif conservé (nez d'îlot, angle)
SEUIL_REPLI_DEG = 150.0    # au-delà : repli (aller-retour) de la polyligne


def _tournants(P):
    d = np.diff(P, axis=0)
    a = np.arctan2(d[:, 1], d[:, 0])
    return np.degrees((a[1:] - a[:-1] + np.pi) % (2 * np.pi) - np.pi)   # tournant au sommet i+1


def _catmull_rom(Q, ferme, pas=0.10):
    """Spline de Catmull-Rom centripète passant par les sommets Q (m, 2) ; renvoie les points et,
    pour chaque sommet d'origine, son indice dans la sortie."""
    m = len(Q)
    if m < 3:
        return Q.copy(), np.arange(m)

    def pt(i):
        if ferme:
            return Q[i % m]
        if i < 0:
            return 2 * Q[0] - Q[1]
        if i > m - 1:
            return 2 * Q[-1] - Q[-2]
        return Q[i]
    out, pos = [], []
    nseg = m if ferme else m - 1
    for i in range(nseg):
        p0, p1, p2, p3 = pt(i - 1), pt(i), pt(i + 1), pt(i + 2)
        d01 = max(np.hypot(*(p1 - p0)) ** 0.5, 1e-6)
        d12 = max(np.hypot(*(p2 - p1)) ** 0.5, 1e-6)
        d23 = max(np.hypot(*(p3 - p2)) ** 0.5, 1e-6)
        t0, t1 = 0.0, d01
        t2, t3 = t1 + d12, t1 + d12 + d23
        n = max(1, int(np.ceil(np.hypot(*(p2 - p1)) / pas)))
        pos.append(len(out))
        for k in range(n):
            t = t1 + (t2 - t1) * k / n
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    if not ferme:
        pos.append(len(out))
        out.append(Q[-1])
    return np.array(out), np.array(pos)


def lisser_bordure(a, ferme):
    """Face vue lissée : Catmull-Rom par les sommets levés (aucun écart aux sommets), coins
    > 40° conservés vifs ; renvoie (points (n, 2), indices des sommets d'origine dans la sortie)."""
    P = a[:, :2]
    m = len(P) - 1 if ferme else len(P)          # anneau : le dernier sommet répète le premier
    if ferme:
        ext = np.vstack([P[m - 1:m], P[:m], P[:1]])
        tour = _tournants(ext)                     # tournant à chaque sommet 0..m-1
        coins = set(int(i) for i in np.where(np.abs(tour) > SEUIL_COIN_DEG)[0])
    else:
        tour = _tournants(P)
        coins = set(int(i) + 1 for i in np.where(np.abs(tour) > SEUIL_COIN_DEG)[0]) | {0, m - 1}
    if ferme and not coins:
        Q, pos = _catmull_rom(P[:m], True)
        return np.vstack([Q, Q[:1]]), np.r_[pos, len(Q)]
    cs = sorted(coins)
    if ferme:
        chaines = []
        for i, c0 in enumerate(cs):
            c1 = cs[(i + 1) % len(cs)]
            ids = list(range(c0, c1 + 1)) if c1 > c0 else list(range(c0, m)) + list(range(0, c1 + 1))
            chaines.append(ids)
    else:
        chaines = [list(range(c0, c1 + 1)) for c0, c1 in zip(cs[:-1], cs[1:])]
    entre = {}
    for ids in chaines:
        Q, pos = _catmull_rom(P[[i % m for i in ids]], False)
        for k in range(len(ids) - 1):
            entre[ids[k] % m] = Q[pos[k] + 1:pos[k + 1]]
    out, pos = [], []
    for i in range(m):
        pos.append(len(out))
        out.append(P[i])
        if i in entre and (ferme or i < m - 1):
            out += list(entre[i])
    if ferme:
        pos.append(len(out))
        out.append(P[0])
    return np.array(out), np.array(pos)


def douglas_peucker(Q, tol):
    """Indices des sommets gardés par Douglas-Peucker (itératif) pour un écart max `tol`."""
    Q = np.asarray(Q, dtype=np.float64)[:, :2]
    garde = np.zeros(len(Q), dtype=bool)
    garde[[0, -1]] = True
    pile = [(0, len(Q) - 1)]
    while pile:
        i, j = pile.pop()
        if j <= i + 1:
            continue
        a, b = Q[i], Q[j]
        d = b - a
        L = np.hypot(*d)
        if L < 1e-9:
            e = np.hypot(*(Q[i + 1:j] - a).T)
        else:
            e = np.abs((Q[i + 1:j, 0] - a[0]) * d[1] - (Q[i + 1:j, 1] - a[1]) * d[0]) / L
        k = int(np.argmax(e))
        if e[k] > tol:
            garde[i + 1 + k] = True
            pile += [(i, i + 1 + k), (i + 1 + k, j)]
    return np.where(garde)[0]


def jalonner_cordes(a, S0, a_leve, S_leve, long_min=1.2, pas=0.5, tol_droit=0.006):
    """Jalons des cordes longues laissées par le Douglas-Peucker (revue conformité r2, regle:
    pj_commun.jalons) : une spline passant par des sommets espacés de 10-20 m bombe de 13 à 22 cm. Sur
    une corde de plus de `long_min` m, si les sommets levés intermédiaires sont alignés à `tol_droit`
    près, jalons sur la corde tous les `pas` m (l'alignement reste droit) ; sinon, les sommets levés
    eux-mêmes (courbe levée). Abscisses description interpolées."""
    out, so = [a[0]], [S0[0]]
    for i in range(len(a) - 1):
        p, q = a[i], a[i + 1]
        L = float(np.hypot(*(q[:2] - p[:2])))
        if L > long_min:
            m = (S_leve > S0[i] + 0.01) & (S_leve < S0[i + 1] - 0.01)
            d = q[:2] - p[:2]
            ecart = np.abs((a_leve[m, 0] - p[0]) * d[1] - (a_leve[m, 1] - p[1]) * d[0]) / L if m.any() else np.zeros(0)
            if len(ecart) and ecart.max() > tol_droit:
                out += list(a_leve[m])
                so += list(S_leve[m])
            else:
                n = int(math.ceil(L / pas))
                for k in range(1, n):
                    t = k / n
                    out.append(p + (q - p) * t)
                    so.append(S0[i] + (S0[i + 1] - S0[i]) * t)
        out.append(q)
        so.append(S0[i + 1])
    return np.array(out), np.array(so)


RAYON_NEZ = {"T1": 0.5, "T2": 0.5, "T3": 0.5, "T2_bateau": 0.5, "A1": 0.5, "A2": 0.5,
             "P1": 0.25, "P2": 0.25, "P3": 0.25, "TU": 0.25, "I1": 0.25, "I2": 0.25, "IL": 0.25}
SEUIL_ARRONDI_DEG = 45.0   # coin convexe (vers le côté haut) au-delà duquel le nez est arrondi


def arrondir_coins(a, s_desc, ferme, profil_de, rayon_nez=None, pas=0.02):
    """Nez arrondis : chaque coin CONVEXE (tournant à gauche, la face vue à l'extérieur) de plus de 45°
    est remplacé par un arc tangent de rayon catalogue (T/A : pièce courbe R 0,5 ; P, TU, I : quart de
    rond R 0,25 ; pointe effilée de plus de 120° : R 0,20, deux bordures dos à dos), réduit si les côtés
    sont trop courts (tangente ≤ 95 % du côté, 48 % s'il est partagé avec un autre coin ; grappes de
    sommets fusionnées avant par Douglas-Peucker 15 mm) : deux éléments droits ne se chevauchent plus au nez (bordures_elements.json,
    pose.points_durs « nez d'îlot » et quarts_de_rond). Bordure de ceinture d'îlot : rayon du nez de la description
    (`rayon_nez`, ilots.nez.rayon_m ; revue conformité r2). Renvoie (sommets, abscisses description, arcs)."""
    P = a[:, :2]
    n = len(P) - 1 if ferme else len(P)
    if n < 3:
        return a, s_desc, []
    idx = lambda i: i % n if ferme else i
    tour = {}
    for k in range(n) if ferme else range(1, n - 1):
        u, v = P[idx(k)] - P[idx(k - 1)], P[idx(k + 1)] - P[idx(k)]
        lu, lv = np.hypot(*u), np.hypot(*v)
        if lu < 1e-6 or lv < 1e-6:
            continue
        tour[k] = math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v))
    coins = {k for k, t in tour.items() if t > SEUIL_ARRONDI_DEG}
    if not coins:
        return a, s_desc, []
    remplace = {}
    for k in sorted(coins):
        if ferme and k == 0:            # coin sur la fermeture d'un anneau : laissé vif (abscisses)
            continue
        V = P[idx(k)]
        A0, B0 = P[idx(k - 1)], P[idx(k + 1)]
        d1 = (V - A0) / np.hypot(*(V - A0))
        d2 = (B0 - V) / np.hypot(*(B0 - V))
        theta = math.radians(tour[k])                       # déviation
        alpha = math.pi - theta                             # angle intérieur
        R = RAYON_NEZ.get(profil_de(float(s_desc[idx(k)])), 0.5)
        if rayon_nez:
            R = max(0.25, float(rayon_nez))
        if tour[k] > 120.0:              # pointe effilée : nez au plus serré, deux bordures dos à dos
            R = min(R, 0.20)
            # recul du sommet du nez R·(1/sin(α/2) − 1) borné à 0,30 m : la pointe décrite garde sa
            # longueur (I-0629 : 1,1 m perdus avec R 0,20 sur une pointe de 20°)
            sa = math.sin(max(math.pi - math.radians(tour[k]), 1e-3) / 2)
            R = max(0.05, min(R, 0.30 / max(1.0 / sa - 1.0, 1e-6)))
        Lin = np.hypot(*(V - A0)) * (0.48 if idx(k - 1) in coins else 0.95)
        Lout = np.hypot(*(B0 - V)) * (0.48 if idx(k + 1) in coins else 0.95)
        tmax = min(Lin, Lout)
        t = R / math.tan(alpha / 2)
        if t > tmax:
            t = tmax
            R = t * math.tan(alpha / 2)
        if R < 0.05:
            continue
        T1, T2 = V - d1 * t, V + d2 * t
        nrm = np.array([-d1[1], d1[0]])                      # centre à gauche (coin convexe)
        Cc = T1 + nrm * R
        a1 = math.atan2(*(T1 - Cc)[::-1])
        a2 = math.atan2(*(T2 - Cc)[::-1])
        if a2 < a1:
            a2 += 2 * math.pi
        m = max(3, int(math.ceil(R * (a2 - a1) / pas)))
        ang = np.linspace(a1, a2, m + 1)
        arc = Cc + R * np.c_[np.cos(ang), np.sin(ang)]
        # z et abscisse description : interpolés entre T1 (sur le côté entrant) et T2 (côté sortant)
        zi = lambda Q, X, Y, za, zb: za + (zb - za) * np.hypot(*(Q - X)) / max(np.hypot(*(Y - X)), 1e-9)
        z1 = zi(T1, A0, V, a[idx(k - 1), 2], a[idx(k), 2])
        z2 = zi(T2, V, B0, a[idx(k), 2], a[idx(k + 1), 2])
        sk, sa, sb = float(s_desc[k]), float(s_desc[k - 1]), float(s_desc[k + 1])   # anneau : s_desc[n] = L
        s1 = sk - t / max(np.hypot(*(V - A0)), 1e-9) * (sk - sa)
        s2 = sk + t / max(np.hypot(*(B0 - V)), 1e-9) * (sb - sk)
        w = np.linspace(0, 1, m + 1)
        remplace[idx(k)] = (np.c_[arc, z1 + (z2 - z1) * w], s1 + (s2 - s1) * w, R, float(tour[k]))
    out, sd, arcs = [], [], []
    for i in range(n):
        if i in remplace:
            pts, ss, R, tr = remplace[i]
            out += list(pts)
            sd += list(ss)
            arcs.append({"s_desc": [round(float(ss[0]), 3), round(float(ss[-1]), 3)], "rayon_m": round(R, 3),
                         "tournant_deg": round(tr, 1)})
        else:
            out.append(a[i])
            sd.append(s_desc[i])
    if ferme:
        out.append(out[0].copy())
        sd.append(s_desc[n])
    return np.array(out), np.array(sd), arcs


class Bordure:
    """Bordure de la description en repère local : arête avant (u = 0), Z = fil d'eau.

    Fabrication (règle regle:pj_commun.lissage) : (1) un repli aller-retour de la polyligne
    (tournant > 150°, aller à < 0,25 m du retour) est réduit à une seule des deux parties ; (2) la
    face vue est lissée par une spline de Catmull-Rom passant par les sommets levés (coins > 40°
    gardés vifs ; anneaux fermés lissés à travers la fermeture) : une bordure préfabriquée ne fait
    pas de coude de 10-30° entre deux sommets GAM. Les abscisses de la description (intervalles,
    abaissés, BEV) sont reportées par les sommets d'origine (`s_nouveau`)."""

    def __init__(self, f, specs, rayon_nez=None):
        self.f = f
        self.p = f["properties"]
        self.id = self.p["id"]
        self.specs = specs
        self.corrections = []
        a = repere(np.asarray(f["geometry"]["coordinates"], dtype=np.float64), "local")
        a = C.dedoublonner_sommets(a)
        S0 = C.abscisses(a)
        # sommets à moins de 5 cm du précédent (zigzags de levé) retirés, extrémités gardées
        garde = np.r_[True, np.diff(S0) > 0.05]
        if not garde[-1]:
            garde[-1] = True
            if len(garde) > 2:
                garde[-2] = False
        a, S0 = a[garde], S0[garde]
        self._s_dec = 0.0
        tour = _tournants(a[:, :2]) if len(a) > 2 else np.zeros(0)
        for k in np.where(np.abs(tour) > SEUIL_REPLI_DEG)[0] + 1:
            A, Bq = a[:k + 1, :2], a[k:, :2]
            dA, _, _ = C.distance_segments(A, Bq[:-1], Bq[1:])
            if np.max(dA) < 0.25:
                self.corrections.append(f"repli : partie aller 0-{S0[k]:.2f} m ignorée (à {np.max(dA):.2f} m du retour)")
                a, S0 = a[k:], S0[k:]
                break
            dB, _, _ = C.distance_segments(Bq, A[:-1], A[1:])
            if np.max(dB) < 0.25:
                self.corrections.append(f"repli : partie retour {S0[k]:.2f}-{S0[-1]:.2f} m ignorée")
                a, S0 = a[:k + 1], S0[:k + 1]
                break
        ferme = len(a) > 3 and np.hypot(*(a[0, :2] - a[-1, :2])) < 0.05
        if ferme:
            a[-1, :2] = a[0, :2]

        def profil_desc(s):
            for i in self.p["intervalles"]:
                if i["s0"] - 1e-6 <= s <= i["s1"] + 1e-6:
                    return i["profil"]
            return self.p["intervalles"][-1]["profil"]
        # profil en long et tracé levé : TOUS les sommets (revue conformité r2 : le Douglas-Peucker plan
        # perdait le profil en long, K-0341 posée 26 cm trop haut ; la spline passant par les seuls
        # sommets gardés bombait de 13-22 cm sur les alignements, K-0369, K-0353)
        a_leve, S_leve = a.copy(), S0.copy()
        g = douglas_peucker(a, 0.015)             # grappes de sommets levés aux nez : un seul coin
        a, S0 = a[g], S0[g]
        a, S0, self.arrondis = arrondir_coins(a, S0, ferme, profil_desc, rayon_nez)
        for arc in self.arrondis:
            self.corrections.append(f"nez arrondi R {arc['rayon_m']} m (coin de {arc['tournant_deg']}°) "
                                    f"entre s = {arc['s_desc'][0]} et {arc['s_desc'][1]} m (description)")
        a, S0 = jalonner_cordes(a, S0, a_leve, S_leve)
        Q, pos = lisser_bordure(a, ferme)

        self.ferme = bool(ferme)
        self.P = Q
        self.S = C.abscisses(Q)
        self.L = float(self.S[-1])
        # correspondance abscisses description -> fabrication (par les sommets d'origine)
        self._s_desc = S0
        self._s_fab = self.S[np.minimum(pos, len(Q) - 1)]
        s_desc_fab = np.interp(self.S, self._s_fab, self._s_desc)
        z0 = np.interp(s_desc_fab, S_leve, a_leve[:, 2])
        # profil en long posable (regle:pj_commun.profil_en_long) : lissage gaussien (σ 0,5 m) borné à
        # ±3,5 mm du fil d'eau décrit (projections alternées) ; les coudes de 2-3 %/m du MNT ouvraient les
        # joints en coin vertical (H x Δpente), l'écart à la description reste ≤ 1 cm (jitter compris)
        dS = np.abs(self.S[:, None] - self.S[None, :])
        if ferme:                                  # anneau : distance périodique (pas de marche à la fermeture)
            dS = np.minimum(dS, self.S[-1] - dS)
        W = np.exp(-0.5 * (dS / 0.5) ** 2)
        W /= W.sum(axis=1)[:, None]
        z = z0.copy()
        for _ in range(25):
            z = np.clip(W @ z, z0 - 0.0035, z0 + 0.0035)
        self.zfe = z
        self.a_leve = a_leve
        self.iv = []
        for i in self.p["intervalles"]:
            j = dict(i)
            j["s0"], j["s1"] = float(self.s_nouveau(i["s0"])), float(self.s_nouveau(i["s1"]))
            if j["s1"] - j["s0"] > 1e-4:
                self.iv.append(j)
        self.iv[0]["s0"], self.iv[-1]["s1"] = 0.0, self.L
        self.arcs_fab = [(float(self.s_nouveau(x["s_desc"][0])), float(self.s_nouveau(x["s_desc"][1])))
                         for x in self.arrondis]
        # écart en plan face lissée - tracé levé, hors nez arrondis (écart voulu)
        d, _, _ = C.distance_segments(Q, a_leve[:-1, :2], a_leve[1:, :2])
        hors_nez = np.ones(len(Q), dtype=bool)
        for s0_, s1_ in self.arcs_fab:
            hors_nez &= ~((self.S >= s0_ - 0.3) & (self.S <= s1_ + 0.3))
        self.ecart_lissage_m = float(d[hors_nez].max()) if hors_nez.any() else 0.0
        self.ecart_nez_m = float(d[~hors_nez].max()) if (~hors_nez).any() else 0.0

    def s_nouveau(self, s_desc):
        """Abscisse de la description -> abscisse de la face lissée."""
        return np.interp(np.asarray(s_desc, dtype=np.float64), self._s_desc, self._s_fab)

    def z_fe(self, s):
        return np.interp(np.asarray(s, dtype=np.float64), self.S, self.zfe)

    def point(self, s):
        pts, tg = C.point_a(self.P, s)
        return pts, tg

    def intervalle(self, s):
        for i in self.iv:
            if i["s0"] - 1e-9 <= s <= i["s1"] + 1e-9:
                return i
        return self.iv[-1] if s > self.L / 2 else self.iv[0]

    def vue(self, s):
        """Vue (m) à l'abscisse s, linéaire dans les chartières."""
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        out = np.empty(len(s))
        for k, x in enumerate(s):
            i = self.intervalle(x)
            if "vue_m_fin" in i and i["s1"] > i["s0"]:
                t = np.clip((x - i["s0"]) / (i["s1"] - i["s0"]), 0, 1)
                out[k] = i["vue_m"] + (i["vue_m_fin"] - i["vue_m"]) * t
            else:
                out[k] = i["vue_m"]
        return out

    def profil(self, s):
        return self.intervalle(s)["profil"]

    def profil_bas(self, iv):
        """Chartière ou raccord de profil : profil de l'intervalle voisin à l'extrémité basse (bateau,
        ou profil courant plus bas) ; celui de la chartière à défaut."""
        desc = iv["vue_m"] > iv.get("vue_m_fin", iv["vue_m"])
        s_bas = iv["s1"] if desc else iv["s0"]
        for i in self.iv:
            if i is iv:
                continue
            if (desc and abs(i["s0"] - s_bas) < 1e-3) or (not desc and abs(i["s1"] - s_bas) < 1e-3):
                return i["profil"]
        return iv["profil"]

    def caniveau_a(self, s):
        """Profil de caniveau (description `caniveau`, intervalles en abscisses description) à l'abscisse
        fabriquée s, ou None."""
        cv = self.p.get("caniveau") or {}
        for a, b in cv.get("intervalles", []):
            if self.s_nouveau(a) - 1e-6 <= s <= self.s_nouveau(b) + 1e-6:
                return cv.get("profil", "CS2")
        return None


def _polys_locaux(geom):
    out = []
    for p in C.anneaux(geom):
        out.append([repere(r, "local") for r in p])
    return out


class Description:
    """Description v2 résolue (couches base/) en repère local, entités triées par id."""

    def __init__(self, dossier=DESCRIPTION, specs=None):
        self.dossier = Path(dossier)
        self.specs = specs or Specs()
        self.manifeste = lire_json(self.dossier / "description_scene_v2.json")
        lire = lambda n: sorted(C.lire_geojson(self.dossier / "base" / f"{n}.geojson"),
                                key=lambda f: f["properties"]["id"])
        nez = {}                                 # rayon de nez décrit des îlots, par bordure de ceinture
        for f in lire("ilots"):
            r = (f["properties"].get("nez") or {}).get("rayon_m")
            for bid in f["properties"].get("ceinture", []):
                if r:
                    nez[bid] = min(nez.get(bid, 9.0), float(r))
        self.bordures = [Bordure(f, self.specs, nez.get(f["properties"]["id"])) for f in lire("bordures")]
        self.par_id = {b.id: b for b in self.bordures}
        self.surfaces = []
        for f in lire("surfaces"):
            self.surfaces.append({"id": f["properties"]["id"], "p": f["properties"],
                                  "polys": _polys_locaux(f["geometry"])})
        self.ilots = []
        for f in lire("ilots"):
            self.ilots.append({"id": f["properties"]["id"], "p": f["properties"],
                               "polys": _polys_locaux(f["geometry"])})
        self.ponctuels = []
        for f in lire("ponctuels_sol"):
            g = f["geometry"]
            rings = [repere(np.asarray(r, dtype=np.float64), "local") for r in g["coordinates"]]
            self.ponctuels.append({"id": f["properties"]["id"], "p": f["properties"], "rings": rings})
        e = self.manifeste["zone_pilote"]["emprise_local_m"]
        self.zone = (e["x_min"], e["y_min"], e["x_max"], e["y_max"])
        self.hash = self.manifeste.get("hash_description") or self._hash()

    def _hash(self):
        h = hashlib.sha256()
        for n in ("bordures", "surfaces", "ilots", "ponctuels_sol"):
            h.update(Path(self.dossier / "base" / f"{n}.geojson").read_bytes())
        return h.hexdigest()

    def fichiers(self):
        return [self.dossier / "description_scene_v2.json"] + \
            [self.dossier / "base" / f"{n}.geojson" for n in ("bordures", "surfaces", "ilots", "ponctuels_sol")]


# --------------------------------------------------------------------------- MNT
_MNT = None


def mnt_local(x, y):
    """MNT 2026 (sol nu octobre 2026) aux points locaux, Z local."""
    global _MNT
    if _MNT is None:
        _MNT = C.MNT()
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    q = repere(np.c_[x.ravel(), y.ravel(), np.zeros(x.size)], "l93")
    z = _MNT(q[:, 0], q[:, 1]) - C.O[2]
    return z.reshape(x.shape)


def fichier_mnt():
    return C.DONNEES / "relief/heightmap_3025_10cm.png"


# --------------------------------------------------------------------------- géométrie
def lisser_chaikin(P, n=2, garder_bouts=True):
    P = np.asarray(P, dtype=np.float64)
    for _ in range(n):
        if len(P) < 3:
            return P
        Q = np.empty((2 * (len(P) - 1), P.shape[1]))
        Q[0::2] = 0.75 * P[:-1] + 0.25 * P[1:]
        Q[1::2] = 0.25 * P[:-1] + 0.75 * P[1:]
        if garder_bouts:
            Q = np.vstack([P[:1], Q, P[-1:]])
        P = Q
    return P


def normales_gauches(P):
    """Normales gauches (unitaires) aux sommets d'une polyligne (moyenne des segments)."""
    P = np.asarray(P, dtype=np.float64)[:, :2]
    d = np.diff(P, axis=0)
    d /= np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)[:, None]
    t = np.vstack([d[:1], d[:-1] + d[1:], d[-1:]])
    t /= np.maximum(np.hypot(t[:, 0], t[:, 1]), 1e-12)[:, None]
    return np.c_[-t[:, 1], t[:, 0]]


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def rotation_rpy(rpy_deg):
    """Matrice 3x3 de rpy_deg = [r, p, y] : ZYX intrinsèques, R = Rz(y) · Ry(p) · Rx(r), rotations
    directes (convention de recon/pcg/ue/pj_tools/pj_tools/repere.py ; p > 0 abaisse l'avant +X)."""
    r, p, y = [math.radians(a) for a in rpy_deg]
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def quat_de_matrice(R):
    """Quaternion (w, x, y, z) d'une matrice de rotation 3x3."""
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        return (0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s)
    i = int(np.argmax(np.diag(R)))
    if i == 0:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        return ((R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s)
    if i == 1:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        return ((R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s)
    s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
    return ((R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s)


# --------------------------------------------------------------------------- export vers Unreal (CONTRAT_EXPORT.md)
def q_xyzw(rpy_deg, nd=6):
    """Quaternion local [x, y, z, w] (ordre de l'attribut orient, champ `q` de pj_points/0.1) de rpy_deg."""
    w, x, y, z = quat_de_matrice(rotation_rpy(rpy_deg))
    if w < 0:                                  # représentant à w >= 0 (lecture plus simple, même rotation)
        w, x, y, z = -w, -x, -y, -z
    return r3([x, y, z, w], nd)


def typer_ue(st, composant):
    """Kinds du contrat (§ 2) : /World assembly, prims intermédiaires group, `composant` component."""
    from pxr import Kind, Sdf, Usd
    chemin = Sdf.Path(composant)
    for p in chemin.GetPrefixes():
        prim = st.GetPrimAtPath(p)
        Usd.ModelAPI(prim).SetKind(Kind.Tokens.component if p == chemin else
                                   Kind.Tokens.assembly if p.pathElementCount == 1 else Kind.Tokens.group)


def lier_ue(prim, mid, apercu=(0.3, 0.3, 0.3), rugosite=0.8):
    """Liaison lue par l'import Unreal (CONTRAT_EXPORT.md § 5), sans effet sur Karma : Material
    /<racine>/Looks/<mid> défini dans la couche (UsdPreviewSurface de repli + outputs:unreal:surface ->
    /Game/PJ/Materials/MI_<mid>) et relation material:binding:preview (finalité lue par UE, material_purpose
    = preview, repli allPurpose). La liaison material:binding (Karma : finalité full -> allPurpose, vers
    /World/Looks_v2) n'est pas touchée."""
    from pxr import Gf, Sdf, UsdShade
    st = prim.GetStage()
    looks = st.GetDefaultPrim().GetPath().AppendChild("Looks")
    if not st.GetPrimAtPath(looks):
        st.DefinePrim(looks, "Scope")
    chemin = looks.AppendChild(mid)
    mat = UsdShade.Material(st.GetPrimAtPath(chemin))
    if not mat:
        mat = UsdShade.Material.Define(st, chemin)
        ap = UsdShade.Shader.Define(st, chemin.AppendChild("Apercu"))
        ap.CreateIdAttr("UsdPreviewSurface")
        ap.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*map(float, apercu)))
        ap.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(rugosite))
        mat.CreateSurfaceOutput().ConnectToSource(ap.ConnectableAPI(), "surface")
        ue = UsdShade.Shader.Define(st, chemin.AppendChild("Unreal"))
        ue.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
        ue.SetSourceAsset(Sdf.AssetPath(f"/Game/PJ/Materials/MI_{mid}.MI_{mid}"), "unreal")
        mat.CreateSurfaceOutput("unreal").ConnectToSource(ue.ConnectableAPI(), "out")
    UsdShade.MaterialBindingAPI.Apply(prim)
    UsdShade.MaterialBindingAPI(prim).Bind(mat, UsdShade.Tokens.fallbackStrength, UsdShade.Tokens.preview)
    return mat


def normales_cusp(P, counts, idx, cusp_deg=30.0, souder=0.0):
    """Normales par sommet de face (faceVarying, alignées sur idx) avec angle de rupture (SOP Normal, cusp) :
    moyenne, pondérée par l'aire, des faces incidentes au sommet dont la normale est à moins de cusp_deg de
    celle de la face. souder > 0 : sommets confondus à `souder` m près (faces à points non partagés)."""
    P = np.asarray(P, dtype=np.float64)
    counts = np.asarray(counts, dtype=np.int64)
    idx = np.asarray(idx, dtype=np.int64)
    debut = np.r_[0, np.cumsum(counts)[:-1]]
    nf = np.zeros((len(counts), 3))
    for k in range(1, int(counts.max()) - 1):                      # éventail de triangles
        sel = counts > k + 1
        a = P[idx[debut[sel]]]
        nf[sel] += np.cross(P[idx[debut[sel] + k]] - a, P[idx[debut[sel] + k + 1]] - a)
    nu = nf / np.maximum(np.linalg.norm(nf, axis=1), 1e-30)[:, None]
    v = idx
    if souder > 0:
        _, inv = np.unique(np.round(P / souder).astype(np.int64), axis=0, return_inverse=True)
        v = inv.reshape(-1)[idx]
    face = np.repeat(np.arange(len(counts)), counts)
    ordre = np.argsort(v, kind="stable")
    uniq, debut_v, nb_v = np.unique(v[ordre], return_index=True, return_counts=True)
    iv = np.searchsorted(uniq, v)
    rep = nb_v[iv]
    coin = np.repeat(np.arange(len(v)), rep)
    off = np.arange(int(rep.sum())) - np.repeat(np.cumsum(rep) - rep, rep)
    g = face[ordre][debut_v[iv][coin] + off]
    ok = np.einsum("ij,ij->i", nu[face[coin]], nu[g]) >= math.cos(math.radians(cusp_deg)) - 1e-9
    N = np.zeros((len(v), 3))
    np.add.at(N, coin[ok], nf[g[ok]])
    n = np.linalg.norm(N, axis=1)
    N = np.where(n[:, None] > 1e-30, N / np.maximum(n, 1e-30)[:, None], nu[face])
    return N
