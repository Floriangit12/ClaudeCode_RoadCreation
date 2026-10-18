# -*- coding: utf-8 -*-
"""Accrochage à OSM pour la couche réseau (FORMAT_DESCRIPTION_RESEAU.md § 3.2 et § 3.3), en Lambert-93.

Source : l'extrait du dépôt `data/vector_gz/osm/` (ways `roads.geojson.gz` ; nœuds ponctuels `crossings`,
`traffic_signals`, `road_signs`, `kerbs`, `barriers`, `traffic_calming`, `public_transport`, `street_lamps`). L'extrait
ne porte pas les identifiants des sommets des ways : un `osm: node/N` se résout sur les couches ponctuelles ; un
`osm_pres_de` se recale sur le sommet de way routier le plus proche (de préférence un sommet partagé par deux ways,
c'est-à-dire un carrefour OSM).

Fonctions : `way(id)`, `noeud(id)`, `sommet_proche(x, y, rayon)`, `chaine([ids], depuis, vers)` (ways bout à bout,
retournés au besoin), `auto(nom, a, b)` (chemin le plus court entre deux points sur les ways de même nom ou numéro,
dans les deux sens de circulation : une chaussée séparée donne sa médiane), `mediane(aller, retour)`,
`decouper(pts, a, b)` (portion d'une polyligne entre les projections de deux points), `simplifier(pts)`.
"""
from __future__ import annotations

import gzip
import heapq
import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[3]
OSM = DEPOT / "data" / "vector_gz" / "osm"
COUCHES_NOEUDS = ("crossings", "traffic_signals", "road_signs", "kerbs", "barriers", "traffic_calming",
                  "public_transport", "street_lamps")


class ErreurOSM(ValueError):
    pass


@lru_cache(maxsize=1)
def _proj():
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)


def l93(lon, lat):
    x, y = _proj().transform(lon, lat)
    return (round(x, 3), round(y, 3))


@lru_cache(maxsize=1)
def ways() -> dict:
    d = json.load(gzip.open(OSM / "roads.geojson.gz", "rt", encoding="utf-8"))
    out = {}
    for ft in d["features"]:
        g = ft["geometry"]
        if g["type"] != "LineString":
            continue
        wid = int(str(ft["properties"].get("osm_id", ft.get("id", "w0"))).split("/")[-1].lstrip("w"))
        out[wid] = {"id": wid, "tags": ft["properties"], "pts": [l93(*c) for c in g["coordinates"]]}
    return out


@lru_cache(maxsize=1)
def noeuds_ponctuels() -> dict:
    out = {}
    for c in COUCHES_NOEUDS:
        f = OSM / f"{c}.geojson.gz"
        if not f.exists():
            continue
        d = json.load(gzip.open(f, "rt", encoding="utf-8"))
        for ft in d["features"]:
            if ft["geometry"]["type"] != "Point":
                continue
            nid = int(str(ft["properties"].get("osm_id", ft.get("id", "n0"))).split("/")[-1].lstrip("n"))
            out[nid] = {"id": nid, "tags": ft["properties"], "xy": l93(*ft["geometry"]["coordinates"]), "couche": c}
    return out


@lru_cache(maxsize=1)
def valences() -> dict:
    """Sommet (arrondi au cm) → nombre de ways routiers qui le touchent."""
    v = {}
    for w in ways().values():
        for p in {(round(x, 2), round(y, 2)) for x, y in w["pts"]}:
            v[p] = v.get(p, 0) + 1
    return v


def way(wid: int) -> dict:
    w = ways().get(int(wid))
    if w is None:
        raise ErreurOSM(f"way/{wid} absent de l'extrait OSM du dépôt ({OSM / 'roads.geojson.gz'})")
    return w


def noeud(nid: int) -> dict:
    n = noeuds_ponctuels().get(int(nid))
    if n is None:
        raise ErreurOSM(f"node/{nid} absent des couches ponctuelles de l'extrait OSM ({', '.join(COUCHES_NOEUDS)}) : "
                        "l'extrait ne porte pas les identifiants des sommets des ways ; ancrer par « position » + "
                        "« osm_pres_de »")
    return n


def sommet_proche(x: float, y: float, rayon: float, carrefour_seul: bool = False):
    """(x, y, valence, distance) du sommet routier le plus proche à moins de `rayon` m ; préférence aux sommets de
    valence ≥ 2 (sommets partagés entre ways) à distance égale à 1 m près. None si aucun."""
    best = None
    for p, val in valences().items():
        d = math.hypot(p[0] - x, p[1] - y)
        if d > rayon or (carrefour_seul and val < 2):
            continue
        cle = (round(d, 0) if val >= 2 else round(d, 0) + 0.5, d)
        if best is None or cle < best[0]:
            best = (cle, (p[0], p[1], val, d))
    return best[1] if best else None


def _norm(s) -> str:
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace("-", " ").replace("'", " ").split())


def chaine(ids: list, chemin: str) -> list:
    """Polyligne des ways donnés dans l'ordre ; un way à l'envers est retourné ; trou > 0,05 m : erreur."""
    pts = []
    for k, wid in enumerate(ids):
        p = list(way(str(wid).split("/")[-1])["pts"])
        if not pts:
            if len(ids) > 1:
                q = way(str(ids[1]).split("/")[-1])["pts"]
                fins = (q[0], q[-1])
                if min(math.dist(p[0], f) for f in fins) < min(math.dist(p[-1], f) for f in fins):
                    p.reverse()
            pts = p
            continue
        if math.dist(pts[-1], p[-1]) < math.dist(pts[-1], p[0]):
            p.reverse()
        if math.dist(pts[-1], p[0]) > 0.05:
            raise ErreurOSM(f"{chemin} : chaîne OSM interrompue entre {ids[k - 1]} et {wid} "
                            f"({math.dist(pts[-1], p[0]):.1f} m)")
        pts += p[1:]
    return pts


def projeter(pts: list, x: float, y: float):
    """(s, distance, (px, py)) de la projection du point sur la polyligne."""
    best, s0 = None, 0.0
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / L2))
        px, py = a[0] + u * dx, a[1] + u * dy
        d = math.hypot(x - px, y - py)
        if best is None or d < best[1] - 1e-9:
            best = (s0 + u * math.sqrt(L2), d, (px, py))
        s0 += math.sqrt(L2)
    return best


def longueur(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def point_a(pts, s):
    s0 = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if s0 + L >= s - 1e-9:
            u = 0.0 if L == 0 else (s - s0) / L
            return (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))
        s0 += L
    return pts[-1]


def decouper(pts, a, b, chemin: str, tolerance: float):
    """Portion de la polyligne entre les projections des points a et b (dans le sens a → b)."""
    sa, da, _ = projeter(pts, *a)
    sb, db, _ = projeter(pts, *b)
    for nom, d in (("de", da), ("vers", db)):
        if d > tolerance:
            raise ErreurOSM(f"{chemin} : le nœud « {nom} » est à {d:.1f} m du tracé OSM (tolérance {tolerance} m)")
    sens = sb >= sa
    s0, s1 = (sa, sb) if sens else (sb, sa)
    out = [point_a(pts, s0)]
    acc = 0.0
    for p, q in zip(pts, pts[1:]):
        acc += math.dist(p, q)
        if s0 + 1e-6 < acc < s1 - 1e-6:
            out.append(q)
    out.append(point_a(pts, s1))
    if not sens:
        out.reverse()
    return out


def mediane(aller: list, retour: list, pas: float = 10.0) -> list:
    """Médiane de deux chaussées : pour chaque point de l'aller rééchantillonné, milieu avec sa projection sur le retour."""
    L = longueur(aller)
    n = max(2, int(round(L / pas)) + 1)
    out = []
    for k in range(n):
        p = point_a(aller, L * k / (n - 1))
        _, _, q = projeter(retour, *p)
        out.append(((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0))
    return out


def _graphe(cands: list, sens_unique_respecte: bool, inverse: bool):
    adj = {}

    def arc(p, q, L):
        adj.setdefault(p, []).append((q, L))

    for w in cands:
        pts = [(round(x, 2), round(y, 2)) for x, y in w["pts"]]
        ow = str(w["tags"].get("oneway", "no")).lower()
        av = ow in ("yes", "true", "1")
        ar = ow == "-1"
        for p, q in zip(pts, pts[1:]):
            L = math.dist(p, q)
            fwd = not sens_unique_respecte or not ar
            bwd = not sens_unique_respecte or not av
            if inverse:
                fwd, bwd = bwd, fwd
            if fwd:
                arc(p, q, L)
            if bwd:
                arc(q, p, L)
    return adj


def _dijkstra_tout(adj, a):
    dist, prev, tas = {a: 0.0}, {}, [(0.0, a)]
    while tas:
        d, u = heapq.heappop(tas)
        if d > dist.get(u, 1e18):
            continue
        for v, L in adj.get(u, []):
            nd = d + L
            if nd < dist.get(v, 1e18):
                dist[v], prev[v] = nd, u
                heapq.heappush(tas, (nd, v))
    return dist, prev


def _dijkstra(adj, a, b):
    dist, prev, tas = {a: 0.0}, {}, [(0.0, a)]
    while tas:
        d, u = heapq.heappop(tas)
        if u == b:
            break
        if d > dist.get(u, 1e18):
            continue
        for v, L in adj.get(u, []):
            nd = d + L
            if nd < dist.get(v, 1e18):
                dist[v], prev[v] = nd, u
                heapq.heappush(tas, (nd, v))
    if b not in dist:
        return None
    out = [b]
    while out[-1] != a:
        out.append(prev[out[-1]])
    return out[::-1]


def auto(nom: str | None, ref: str | None, a: tuple, b: tuple, chemin: str, tolerance: float = 15.0):
    """(polyligne, ways retenus, nature) entre les points a et b sur les ways de même nom (ou numéro).

    1. chemin le plus court sans tenir compte des sens uniques, entre les sommets les plus proches de a et de b ;
    2. si ce chemin suit des ways à sens unique, recherche de la chaussée jumelle (ways de même nom, sens opposé, à 3 à
       25 m en travers) : présente sur au moins 70 % de la longueur, le tracé est la médiane des deux chaussées
       (RF-OSM-PRF-011) ; sinon le chemin lui-même ;
    3. découpe entre les projections de a et de b."""
    cle_nom, cle_ref = _norm(nom) if nom else None, _norm(ref) if ref else None
    cands = [w for w in ways().values()
             if (cle_nom and _norm(w["tags"].get("name")) == cle_nom)
             or (cle_ref and _norm(w["tags"].get("ref")).replace(" ", "") == cle_ref.replace(" ", ""))]
    if not cands:
        raise ErreurOSM(f"{chemin} : aucun way OSM nommé « {nom or ref} » dans l'extrait")

    def plus_proche(p):
        best = None
        for w in cands:
            for q in w["pts"]:
                d = math.dist(p, q)
                if best is None or d < best[0]:
                    best = (d, (round(q[0], 2), round(q[1], 2)))
        return best

    da, sa = plus_proche(a)
    db, sb = plus_proche(b)
    if da > tolerance or db > tolerance:
        raise ErreurOSM(f"{chemin} : nœud à {max(da, db):.1f} m des ways « {nom or ref} » (tolérance {tolerance} m)")
    # sommets de départ et d'arrivée : parmi ceux à moins de la tolérance, la paire au chemin le plus court (sur deux
    # chaussées séparées, les sommets les plus proches peuvent être sur deux chaussées différentes : demi-tour à éviter)
    adj = _graphe(cands, False, False)
    pa = sorted({(round(q[0], 2), round(q[1], 2)) for w in cands for q in w["pts"] if math.dist(a, q) <= tolerance},
                key=lambda q: math.dist(a, q))[:12]
    pb = sorted({(round(q[0], 2), round(q[1], 2)) for w in cands for q in w["pts"] if math.dist(b, q) <= tolerance},
                key=lambda q: math.dist(b, q))[:12]
    best = None
    for x in pa:
        dist, prev = _dijkstra_tout(adj, x)
        for y in pb:
            if y in dist:
                cout = dist[y] + math.dist(a, x) + math.dist(b, y)
                if best is None or cout < best[0] - 1e-9:
                    best = (cout, x, y, prev)
    if best is None:
        raise ErreurOSM(f"{chemin} : les ways « {nom or ref} » ne relient pas les deux nœuds")
    _, x, y, prev = best
    chemin_pts = [y]
    while chemin_pts[-1] != x:
        chemin_pts.append(prev[chemin_pts[-1]])
    chemin_pts.reverse()
    P = [tuple(p) for p in chemin_pts]
    utilises = sorted({w["id"] for w in cands if any((round(x, 2), round(y, 2)) in set(chemin_pts) for x, y in w["pts"])})
    sens_uniques = [w for w in cands if str(w["tags"].get("oneway", "no")).lower() in ("yes", "true", "1", "-1")]
    nature = "chaussee_unique"
    if sens_uniques and any(w["id"] in utilises for w in sens_uniques):
        # chaussée jumelle : segments des ways à sens unique non utilisés, dans l'autre sens, à 3-25 m en travers
        jum = []
        parcourus = {frozenset(((round(u[0], 2), round(u[1], 2)), (round(v[0], 2), round(v[1], 2))))
                     for u, v in zip(P, P[1:])}
        for w in sens_uniques:
            pts = w["pts"] if str(w["tags"].get("oneway")).lower() != "-1" else list(reversed(w["pts"]))
            jum += [(u, v) for u, v in zip(pts, pts[1:]) if frozenset(((round(u[0], 2), round(u[1], 2)),
                                                                      (round(v[0], 2), round(v[1], 2)))) not in parcourus]
        L = longueur(P)
        n = max(2, int(round(L / 10.0)) + 1)
        med, trouves = [], 0
        for k in range(n):
            s = L * k / (n - 1)
            p = point_a(P, s)
            q0 = point_a(P, max(0.0, s - 2.0))
            q1 = point_a(P, min(L, s + 2.0))
            d = (q1[0] - q0[0], q1[1] - q0[1])
            nd = math.hypot(*d) or 1.0
            d = (d[0] / nd, d[1] / nd)
            best = None
            for u, v in jum:
                sx, sy = v[0] - u[0], v[1] - u[1]
                ls = math.hypot(sx, sy)
                if ls < 1e-6 or abs(sx * d[0] + sy * d[1]) / ls < 0.7:     # parallèle (le chemin peut remonter un sens unique)
                    continue
                t = max(0.0, min(1.0, ((p[0] - u[0]) * sx + (p[1] - u[1]) * sy) / (ls * ls)))
                x, y = u[0] + t * sx, u[1] + t * sy
                lat = abs((x - p[0]) * d[1] - (y - p[1]) * d[0])
                lon = abs((x - p[0]) * d[0] + (y - p[1]) * d[1])
                if 3.0 <= lat <= 25.0 and lon <= 5.0 and (best is None or lat < best[0]):
                    best = (lat, (x, y))
            if best:
                trouves += 1
                med.append(((p[0] + best[1][0]) / 2.0, (p[1] + best[1][1]) / 2.0))
            else:
                med.append(p)
        if trouves >= 0.7 * n:
            P = med
            nature = f"chaussees_separees (médiane, chaussée jumelle trouvée sur {100 * trouves // n} % des points)"
        else:
            nature = "sens_unique"
    return decouper(P, a, b, chemin, tolerance), utilises, nature


def simplifier(pts: list, tolerance: float = 0.25) -> list:
    """Douglas-Peucker (tolérance en m) ; extrémités conservées."""
    if len(pts) < 3:
        return list(pts)

    def dp(i, j, garde):
        a, b = pts[i], pts[j]
        L = math.dist(a, b)
        best, k = 0.0, None
        for m in range(i + 1, j):
            p = pts[m]
            d = abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / L if L > 0 else math.dist(a, p)
            if d > best:
                best, k = d, m
        if k is not None and best > tolerance:
            garde.add(k)
            dp(i, k, garde)
            dp(k, j, garde)

    garde = {0, len(pts) - 1}
    dp(0, len(pts) - 1, garde)
    return [pts[i] for i in sorted(garde)]
