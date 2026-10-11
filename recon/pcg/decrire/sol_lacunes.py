"""Lacunes du levé des bordures (site complet) : bouts de file libres, ponts entre bouts alignés
(bordures synthétiques) et fermetures géométriques des bouts restants.

Un bout de bordure libre (aucune autre ligne de la partition n'y aboutit) laisse la chaussée (côté bas)
et le trottoir (côté haut) communiquer autour du bout : la partition ne sépare plus les niveaux et le
nivellement crée des pointes (GA-BOR-005). Traitement, dans l'ordre :
1. pont : deux bouts libres de deux bordures, alignés (≤ 15 m, écart angulaire ≤ 35°, côté haut du même
   côté) sont reliés par une bordure synthétique `K-95nn` (courbe de Hermite tangente aux deux bouts) :
   - au droit d'un passage piéton ou d'une zone de traversée abaissée : bateau en vue 0,02
     (GA-ABA-001, déduit si absent) avec abaissé de type traversée ;
   - au droit d'une traversée cyclable : vue 0 (GA-ABA-010) ;
   - sinon : continuité de la file, vue interpolée entre les deux bouts (raccord, GA-BOR-005) ;
2. fermeture de bout : un bout encore libre est relié par un segment droit au point le plus proche d'une
   ligne de la partition à moins de 4 m (sans croiser d'autre ligne) : limite de partition seulement,
   signalée (`fermeture_bout`).
"""
import math

import numpy as np

import sol_site as ctx
import sol_geometrie as G
from commun import (abscisses, arrondi, coords_geojson, dans_polygone, distance_segments, point_a, repere,
                    sous_polyligne)

PONT_MAX_M = 15.0
COS_PONT = math.cos(math.radians(35.0))
FERMETURE_BOUT_MAX_M = 4.0
VUE_TRAVERSEE = 0.02


def _tangente_sortante(P, bout):
    """Tangente unitaire sortant de la polyligne à son extrémité (0 ou -1), sur ≥ 0,5 m."""
    L = float(abscisses(P)[-1])
    if bout == 0:
        a, _ = point_a(P, min(0.5, L))
        u = P[0] - a[0]
    else:
        a, _ = point_a(P, max(0.0, L - 0.5))
        u = P[-1] - a[0]
    n = math.hypot(*u)
    return u / n if n > 1e-9 else np.array([1.0, 0.0])


def bouts_libres(arr, lignes):
    """Extrémités d'arête avant de bordure sans autre ligne que celles de la même bordure :
    [(kid, bout, point)]. `arr` : arrangement de la partition (après prolongements)."""
    from collections import defaultdict
    N = arr["noeuds"]
    adj = defaultdict(set)
    grp = defaultdict(set)
    for (a, b), ls in arr["aretes"].items():
        adj[a].add(b)
        adj[b].add(a)
        for l in ls:
            g = lignes[l][1].get("groupe")
            grp[a].add(g)
            grp[b].add(g)
    cles = np.round(N / 0.001).astype(np.int64)
    index = {tuple(c): i for i, c in enumerate(cles.tolist())}
    out = []
    for (P0, e), (P, _) in zip(lignes, arr["lignes"]):
        if e.get("src") != "bordure_avant":
            continue
        for bout in (0, -1):
            if np.hypot(*(P[bout] - P0[bout])) > 1e-4:
                continue                                  # prolongée ou accrochée sur une autre ligne
            q = P[bout]
            i = index.get(tuple(np.round(q / 0.001).astype(np.int64).tolist()))
            if i is None:
                d = np.hypot(*(N - q).T)
                j = int(np.argmin(d))
                i = j if d[j] < 0.006 else None
            if i is not None and (grp[i] - {e.get("groupe")}):
                continue                                  # une autre ligne aboutit ici
            if np.abs(q).max() > ctx.DEMI - 0.05:
                continue                                  # bord du site
            out.append((e["id"], bout, q))
    out.sort(key=lambda x: (x[0], x[1]))
    return out


def _hermite(A, ta, B, tb, pas=0.25):
    d = float(np.hypot(*(B - A)))
    n = max(2, int(math.ceil(d / pas)) + 1)
    t = np.linspace(0.0, 1.0, n)[:, None]
    h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    m0, m1 = ta * d, tb * d
    return h00 * A + h10 * m0 + h01 * B + h11 * m1


def _croise(P, A, B, exclure_bouts=0.05):
    """La polyligne P coupe-t-elle un des segments [A, B] (hors voisinage de ses extrémités) ?"""
    for p, q in zip(P[:-1], P[1:]):
        r = q - p
        s_ = B - A
        den = r[0] * s_[:, 1] - r[1] * s_[:, 0]
        ap = A - p
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (ap[:, 0] * s_[:, 1] - ap[:, 1] * s_[:, 0]) / den
            u = (ap[:, 0] * r[1] - ap[:, 1] * r[0]) / den
        m = (np.abs(den) > 1e-12) & (t > 1e-6) & (t < 1 - 1e-6) & (u > 1e-6) & (u < 1 - 1e-6)
        if m.any():
            x = p + r * t[m][:, None]
            dd = np.minimum(np.hypot(*(x - P[0]).T), np.hypot(*(x - P[-1]).T))
            if (dd > exclure_bouts).any():
                return True
    return False


def ponts(libres, K, aretes):
    """Paires de bouts libres alignés -> [(kid_a, bout_a, kid_b, bout_b, polyligne locale orientée
    côté haut à gauche)]. `aretes` : segments (A, B) actifs de la partition (test de croisement)."""
    par = {f["properties"]["id"]: f for f in K}
    cand = []
    for i, (ka, ba, qa) in enumerate(libres):
        Pa = repere(np.asarray(par[ka]["geometry"]["coordinates"])[:, :2])
        ta = _tangente_sortante(Pa, ba)
        for j, (kb, bb, qb) in enumerate(libres):
            if j <= i or kb == ka or ba == bb:
                continue                                  # fin -> début seulement (côté haut cohérent)
            d = qb - qa
            L = float(np.hypot(*d))
            if L < 0.05 or L > PONT_MAX_M:
                continue
            Pb = repere(np.asarray(par[kb]["geometry"]["coordinates"])[:, :2])
            tb = _tangente_sortante(Pb, bb)
            u = d / L
            ca, cb = float(ta @ u), float(-(tb @ u))
            if ca < COS_PONT or cb < COS_PONT:
                continue
            lat = abs(float(np.cross(ta, d)))
            if lat > max(0.6, 0.25 * L):
                continue
            cand.append((L * (3.0 - ca - cb), i, j))
    cand.sort()
    pris, out = set(), []
    A, B = aretes
    for cout, i, j in cand:
        if i in pris or j in pris:
            continue
        ka, ba, qa = libres[i]
        kb, bb, qb = libres[j]
        Pa = repere(np.asarray(par[ka]["geometry"]["coordinates"])[:, :2])
        Pb = repere(np.asarray(par[kb]["geometry"]["coordinates"])[:, :2])
        ta, tb = _tangente_sortante(Pa, ba), _tangente_sortante(Pb, bb)
        # orientation : de la fin d'une bordure vers le début de l'autre (côté haut à gauche conservé)
        if ba == -1:
            P = _hermite(qa, ta, qb, -tb)
            amont, aval = (ka, -1), (kb, 0)
        else:
            P = _hermite(qb, tb, qa, -ta)
            amont, aval = (kb, -1), (ka, 0)
        if _croise(P, A, B):
            continue
        if not _pont_admissible(P, qa if ba == -1 else qb, ta if ba == -1 else tb):
            continue                                      # bout laissé libre (fermeture de bout, sans bordure)
        pris |= {i, j}
        out.append((amont, aval, P))
    return out


R_MIN_PONT_M = 1.0               # GQ-RAY-001 : pas de pièce de bordure synthétique plus serrée
DECALAGE_S_MAX_M = 0.10          # pont en S (inflexion) : décalage latéral au-delà duquel il est refusé


def _pont_admissible(P, A, ta):
    """Pont de Hermite refusé (revue réalisme du 11/10/2026 : K-9514 en S devant le zébra MP-5246) s'il passe sous
    R 1 m (GQ-RAY-001) ou s'il dessine un S (courbure des deux signes) avec un décalage latéral > 0,10 m (GA-BOR-005 :
    une file de bordures ne serpente pas ; le bout reste libre et la partition est fermée sans bordure)."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return True
    d1 = np.gradient(P, axis=0)
    d2 = np.gradient(d1, axis=0)
    num = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    den = np.maximum(np.hypot(*d1.T) ** 3, 1e-12)
    k = num / den
    if float(np.max(np.abs(k[1:-1]))) > 1.0 / R_MIN_PONT_M:
        return False
    lat = np.abs((P[:, 0] - A[0]) * ta[1] - (P[:, 1] - A[1]) * ta[0])
    s_ = k[np.abs(k) > 1.0 / 50.0]
    if len(s_) and (s_ > 0).any() and (s_ < 0).any() and float(lat.max()) > DECALAGE_S_MAX_M:
        return False
    return True


def _vue_bout(f, bout):
    its = f["properties"]["intervalles"]
    it = its[0] if bout == 0 else its[-1]
    if bout == 0:
        return it["profil"], it["vue_m"]
    return it["profil"], it.get("vue_m_fin", it["vue_m"])


def bordure_pont(nid, P, amont, aval, K, mnt):
    """Bordure synthétique d'un pont (feature L93 + NGF, même schéma que les bordures levées)."""
    from bordures import regulariser_fil_eau, bev_attendue
    from commun import densifier, normale_gauche
    par = {f["properties"]["id"]: f for f in K}
    fa, fb = par[amont[0]], par[aval[0]]
    pa, va = _vue_bout(fa, amont[1])
    pb, vb = _vue_bout(fb, aval[1])
    L = float(abscisses(P)[-1])
    # traversée ? (passage piéton prolongé, zone de traversée abaissée, traversée cyclable)
    s = np.linspace(0.0, L, max(3, int(L / 0.25) + 1))
    q, _ = point_a(P, s)
    m_pp = np.zeros(len(s), bool)
    pp_ids = set()
    for g in ctx.passages_pietons():
        d = dans_polygone(q, [g["anneau"]])
        if d.any():
            pp_ids.add(g["id"])
        m_pp |= d
    for _, _, poly in ctx.zones_relief("traversee_bordure_abaissee"):
        m_pp |= dans_polygone(q, poly)
    m_tc = np.zeros(len(s), bool)
    for g in ctx.traversees_cyclables():
        m_tc |= dans_polygone(q, [g["anneau"]])
    typ = None
    if m_pp.mean() >= 0.3:
        typ, vue_b, regle = "traversee", VUE_TRAVERSEE, "GA-ABA-001"
    elif m_tc.mean() >= 0.3:
        typ, vue_b, regle = "traversee_cyclable", 0.0, "GA-ABA-010"
    rp = fa["properties"]
    if typ:
        intervalles = [{"s0": 0.0, "s1": L, "profil": "T2_bateau", "vue_m": vue_b, "role": "bateau",
                        "abaisse": f"A-{nid[2:]}-1"}]
        abaisses = [{"id": f"A-{nid[2:]}-1", "type": typ, "s0": 0.0, "s1": L, "vue_m": vue_b, "profil": "T2_bateau",
                     "raccords": [], "bev": None, "passages": sorted(pp_ids) if typ == "traversee" else [],
                     "acces_riverains": [], "sources": [f"regle:regles_conception.{regle}", f"pont:{amont[0]}-{aval[0]}"],
                     "configuration": "a_niveau", "largeur_trottoir_m": 0.0,
                     "rampe": {"profondeur_m": 0.0, "pente_pct": 0.0, "denivele_m": 0.0, "longueur_raccord_m": 0.0,
                               "chartiere_observee": False},
                     "regles": [regle, "GA-BOR-005"]}]
        prov_int = {"src": f"regle:regles_conception.{regle}",
                    "ref": f"lacune du levé au droit d'une traversée ({', '.join(sorted(pp_ids)) or 'zone de traversée'}) : bateau déduit", "conf": "faible"}
    else:
        if abs(va - vb) >= 0.0095:
            intervalles = [{"s0": 0.0, "s1": L, "profil": pa if va >= vb else pb, "vue_m": round(va, 3),
                            "vue_m_fin": round(vb, 3), "role": "chartiere"}]
        else:
            intervalles = [{"s0": 0.0, "s1": L, "profil": pa, "vue_m": round(0.5 * (va + vb), 3), "role": "courant"}]
        abaisses = []
        prov_int = {"src": "regle:regles_conception.GA-BOR-005",
                    "ref": f"continuité de file entre {amont[0]} ({pa} {va:.3f}) et {aval[0]} ({pb} {vb:.3f}) : vues raccordées", "conf": "faible"}
    pts, sv = densifier(P, 1.0)
    _, tg = point_a(P, sv)
    nl = normale_gauche(tg)
    z_av = mnt(*(repere(pts - nl * 0.30, "l93").T))
    z_ar = mnt(*(repere(pts + nl * 0.45, "l93").T)) - np.interp(sv, [0, L], [va, vb])
    z, _ = regulariser_fil_eau(sv, z_av, z_ar)
    props = dict(rp)
    props.update({
        "id": nid, "longueur_m": L, "intervalles": intervalles, "abaisses": abaisses, "courbes": [],
        "caniveau": None, "chartieres_gam": [], "coupe_zone": {"debut": False, "fin": False},
        "source": {"ligne": None, "gam_index": None, "s_src_m": None, "sens": "direct", "doublons_supprimes": [],
                   "statut_hauteur": "synthetique", "ecart_fil_eau_2021_mnt_m": None,
                   "voisine": amont[0], "pont": [amont[0], aval[0]]},
        "prov": {"geometrie": {"src": "a_priori:pont_lacune_bordure",
                               "ref": f"courbe de Hermite tangente aux bouts libres de {amont[0]} et {aval[0]} ({L:.2f} m)", "conf": "faible"},
                 "face_vue": {"src": "a_priori:continuite_file", "ref": f"côté haut de {amont[0]} et {aval[0]}", "conf": "moyenne"},
                 "intervalles": prov_int, "materiau": rp["prov"]["materiau"], "aspect": rp["prov"]["aspect"],
                 "element_m": rp["prov"]["element_m"], "z": rp["prov"]["z"]},
    })
    feat = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords_geojson(np.c_[repere(pts, "l93"), z])},
            "properties": arrondi(props)}
    if typ == "traversee":
        f2 = feat["properties"]["abaisses"][0]
        f2["bev"] = bev_attendue(P, 0.0, L, f2["passages"], travaux=bool(rp.get("zone_travaux_2025")))
    return feat


def fermetures_bouts(libres_restants, aretes, groupes_aretes):
    """Segments droits d'un bout libre au point le plus proche d'une arête active d'un AUTRE groupe
    (≤ 4 m, sans croiser d'autre ligne) : [(polyligne, étiquette)]."""
    A, B = aretes
    out = []
    for kid, bout, q in libres_restants:
        r = FERMETURE_BOUT_MAX_M + 0.5
        sel = ((np.minimum(A[:, 0], B[:, 0]) <= q[0] + r) & (np.maximum(A[:, 0], B[:, 0]) >= q[0] - r)
               & (np.minimum(A[:, 1], B[:, 1]) <= q[1] + r) & (np.maximum(A[:, 1], B[:, 1]) >= q[1] - r))
        for i in np.nonzero(sel)[0]:
            if kid in groupes_aretes[i]:
                sel[i] = False
        if not sel.any():
            continue
        d, j, pr = distance_segments(q[None], A[sel], B[sel])
        if d[0] > FERMETURE_BOUT_MAX_M or d[0] < 0.002:
            continue
        P = np.vstack([q, pr[0]])
        autres = sel.copy()
        if _croise(P, A[autres], B[autres], exclure_bouts=0.01):
            continue
        out.append((P, {"src": "fermeture_bout", "id": f"{kid}/{'debut' if bout == 0 else 'fin'}",
                        "longueur_m": float(d[0])}))
    return out
