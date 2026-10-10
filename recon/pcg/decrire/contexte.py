"""Données de contexte partagées par les convertisseurs (repère local, zone pilote comprise).

Lecture seule du paquet v1 (recon/out/paquet_jardin/package/donnees), des vecteurs GAM / OSM
(data/sites/paquet_jardin) et des constats vérifiés (analysis/paquet_jardin/constats_verifies.json).
Les géométries rendues sont en repère LOCAL (commun.repere).
"""
import functools

import numpy as np

from commun import (DONNEES, RACINE, VECTEURS, ZONE, anneaux, aire_signee, dans_polygone,
                    lire_geojson, lire_json, repere)

CONSTATS_JSON = RACINE / "analysis/paquet_jardin/constats_verifies.json"
MARGE = 12.0      # marge de lecture autour de la zone (m) : appariements et contexte aux bords


def _local_polys(geom):
    return [[repere(r) for r in p] for p in anneaux(geom)]


@functools.lru_cache(maxsize=None)
def zone_pilote():
    """Anneau local anti-horaire de la zone pilote + emprise (x0, y0, x1, y1) + propriétés."""
    f = lire_geojson(ZONE)[0]
    r = repere(np.asarray(f["geometry"]["coordinates"][0], dtype=float)[:-1, :2])
    if aire_signee(r) < 0:
        r = r[::-1]
    return {"anneau": r, "emprise": (*r.min(axis=0), *r.max(axis=0)), "props": f["properties"]}


def dans_emprise(pts, marge=MARGE):
    x0, y0, x1, y1 = zone_pilote()["emprise"]
    pts = np.atleast_2d(pts)
    return ((pts[:, 0] >= x0 - marge) & (pts[:, 0] <= x1 + marge)
            & (pts[:, 1] >= y0 - marge) & (pts[:, 1] <= y1 + marge))


def touche_emprise(polys, marge=MARGE):
    return any(dans_emprise(r, marge).any() for p in polys for r in p) or any(
        dans_polygone(zone_pilote()["anneau"][:1], p)[0] for p in polys)


@functools.lru_cache(maxsize=None)
def surfaces_v1():
    """Surfaces du paquet v1 proches de la zone : [(id, props, polys locaux)]."""
    out = []
    for f in lire_geojson(DONNEES / "surfaces/surfaces_2026.geojson"):
        polys = _local_polys(f["geometry"])
        if polys and touche_emprise(polys):
            out.append((f["properties"]["id"], f["properties"], polys))
    return out


@functools.lru_cache(maxsize=None)
def zones_relief(nom):
    """Polygones locaux des relief_zones_2026 d'un type donné (ex. traversee_bordure_abaissee)."""
    out = []
    for i, f in enumerate(lire_geojson(DONNEES / "relief/relief_zones_2026.geojson")):
        if f["properties"]["zone"] != nom:
            continue
        for p in _local_polys(f["geometry"]):
            if touche_emprise([p]):
                out.append((f"RZ-{i:03d}", f["properties"], p))
    return out


VEHICULES = {"chaussee", "piste_cyclable", "parking", "acces_riverain"}


def classe_surface(pts):
    """Classe v1 (surfaces_2026) sous chaque point local, '' hors surfaces."""
    pts = np.atleast_2d(pts)
    out = np.full(len(pts), "", dtype=object)
    for _, p, polys in surfaces_v1():
        libre = out == ""
        if not libre.any():
            break
        m = np.zeros(len(pts), bool)
        m[libre] = dans_polygones_(pts[libre], polys)
        out[m] = p["classe"]
    return out


def dans_polygones_(pts, polys):
    m = np.zeros(len(pts), bool)
    for p in polys:
        m |= dans_polygone(pts, p)
    return m


def dans_chaussee_2026(pts):
    """Points dans le masque de chaussée 2026 (relief_zones « chaussee_2026 », îlots en trous)."""
    pts = np.atleast_2d(pts)
    m = np.zeros(len(pts), bool)
    for _, _, p in zones_relief("chaussee_2026"):
        m |= dans_polygone(pts, p)
    return m


@functools.lru_cache(maxsize=None)
def acces_riverains():
    return [(i, p, polys) for i, p, polys in surfaces_v1() if p["classe"] == "acces_riverain"]


@functools.lru_cache(maxsize=None)
def chartieres_gam():
    """Blocs CHARTIERE_GAUCHE / _DROITE du levé GAM (SOL_BORDURE, points)."""
    out = []
    for f in lire_geojson(VECTEURS / "etat_2026/bordure_pct_L93.geojson"):
        bloc = f["properties"].get("bloc") or ""
        if not bloc.startswith("CHARTIERE"):
            continue
        g = f["geometry"]
        c = g["coordinates"] if g["type"] == "Point" else g["coordinates"][0]
        xy = repere(np.asarray(c[:2], dtype=float)[None])[0]
        if dans_emprise(xy[None])[0]:
            out.append({"bloc": bloc, "xy": xy, "rotation_deg": f["properties"].get("rotation"),
                        "ref": f"bordure_pct CHARTIERE ({xy[0] + 917279.43:.2f}, {xy[1] + 6460289.98:.2f})"})
    out.sort(key=lambda b: (round(b["xy"][0], 2), round(b["xy"][1], 2)))
    return out


def _obb(pts):
    """Rectangle orienté minimal approché (axes principaux) : centre, axes u (long), v, demi-étendues."""
    c = pts.mean(axis=0)
    w, V = np.linalg.eigh(np.cov((pts - c).T))
    u = V[:, 1] if w[1] >= w[0] else V[:, 0]
    if u[0] < 0 or (abs(u[0]) < 1e-9 and u[1] < 0):
        u = -u
    v = np.array([-u[1], u[0]])
    pu, pv = (pts - c) @ u, (pts - c) @ v
    return c, u, v, (pu.min(), pu.max()), (pv.min(), pv.max())


@functools.lru_cache(maxsize=None)
def passages_pietons(ext_traversee=1.5, ext_largeur=0.0, nb_min=2):
    """Passages piétons (bandes `passage_pieton_bande` groupées) et leur emprise d'abaissé.
    Bande IISR : parallèle à l'axe de la chaussée ; on traverse perpendiculairement à sa longueur.
    Emprise = boîte des bandes prolongée de `ext_traversee` m dans le sens de la traversée (jusqu'aux
    bordures) et de `ext_largeur` m dans le sens de la longueur des bandes (abaissé = largeur du
    passage). Les bandes isolées (< nb_min, restes d'ortho) ne forment pas de passage."""
    bandes = []
    for f in lire_geojson(DONNEES / "marquages/marquages_2026.geojson"):
        p = f["properties"]
        if p["type"] != "passage_pieton_bande":
            continue
        for poly in _local_polys(f["geometry"]):
            r = poly[0]
            if not dans_emprise(r).any():
                continue
            c, u, v, (u0, u1), (v0, v1) = _obb(r)
            bandes.append({"id": p["id"], "pts": r, "c": c, "u": u, "long": u1 - u0, "etat": p.get("etat")})
    bandes.sort(key=lambda b: b["id"])
    # regroupement : bandes parallèles dont les centres sont à moins de 1,6 m (pas 1,0-1,3 m)
    groupe = list(range(len(bandes)))

    def racine(i):
        while groupe[i] != i:
            groupe[i] = groupe[groupe[i]]
            i = groupe[i]
        return i
    for i in range(len(bandes)):
        for j in range(i + 1, len(bandes)):
            bi, bj = bandes[i], bandes[j]
            if abs(bi["u"] @ bj["u"]) > 0.95 and np.hypot(*(bi["c"] - bj["c"])) < 1.6:
                groupe[racine(j)] = racine(i)
    groupes = {}
    for i, b in enumerate(bandes):
        groupes.setdefault(racine(i), []).append(b)
    out = []
    for k, gb in groupes.items():
        if len(gb) < nb_min:
            continue
        pts = np.vstack([b["pts"] for b in gb])
        u = gb[0]["u"]
        v = np.array([-u[1], u[0]])
        c = pts.mean(axis=0)
        pu, pv = (pts - c) @ u, (pts - c) @ v
        u0, u1 = pu.min() - ext_largeur, pu.max() + ext_largeur
        v0, v1 = pv.min() - ext_traversee, pv.max() + ext_traversee
        anneau = np.array([c + u * a + v * b for a, b in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))])
        ids = sorted(b["id"] for b in gb)
        out.append({"id": f"PP-{ids[0][2:]}", "bandes": ids, "anneau": anneau, "u": u, "v": v,
                    "c": c, "nb_bandes": len(gb), "longueur_bande_m": float(np.median([b["long"] for b in gb])),
                    "etat": sorted({b["etat"] or "" for b in gb})})
    out.sort(key=lambda g: g["id"])
    return out


def axe_local_polygone(polys, pts, rayon=8.0):
    """Direction principale (unitaire) du contour d'un polygone autour de chaque point (ACP des
    sommets du contour rééchantillonné à 0,5 m dans un rayon donné) : axe d'un accès, d'une allée."""
    bord = []
    for p in polys:
        for r in p:
            rr = np.vstack([r, r[:1]])
            for a, b in zip(rr[:-1], rr[1:]):
                k = max(1, int(np.ceil(np.hypot(*(b - a)) / 0.5)))
                bord.append(a + (b - a) * (np.arange(k)[:, None] / k))
    bord = np.vstack(bord)
    out = np.zeros((len(pts), 2))
    for i, q in enumerate(np.atleast_2d(pts)):
        sel = bord[np.hypot(*(bord - q).T) <= rayon]
        if len(sel) < 3:
            sel = bord
        c = sel - sel.mean(axis=0)
        w, V = np.linalg.eigh(c.T @ c)
        out[i] = V[:, int(np.argmax(w))]
    return out


@functools.lru_cache(maxsize=None)
def caniveaux_gam():
    """Lignes SOL_CANIVEAU du levé GAM (12 lignes, sans attribut) en local : [(indice, polyligne)]."""
    out = []
    for i, f in enumerate(lire_geojson(VECTEURS / "etat_2026/caniveau_lin_L93.geojson")):
        P = repere(np.asarray(f["geometry"]["coordinates"], dtype=float)[:, :2])
        if dans_emprise(P).any():
            out.append((i, P))
    return out


@functools.lru_cache(maxsize=None)
def osm_traversees():
    """Nœuds OSM highway=crossing (tactile_paving) en local."""
    from pyproj import Transformer
    t = Transformer.from_crs(4326, 2154, always_xy=True)
    out = []
    for f in lire_geojson(VECTEURS / "vector/osm_crossings.geojson"):
        g = f["geometry"]
        if g["type"] != "Point":
            continue
        x, y = t.transform(*g["coordinates"][:2])
        xy = repere(np.array([[x, y]]))[0]
        if dans_emprise(xy[None])[0]:
            out.append({"osm": f["properties"].get("osm_id"), "xy": xy,
                        "tactile_paving": f["properties"].get("tactile_paving"),
                        "crossing": f["properties"].get("crossing")})
    out.sort(key=lambda o: o["osm"] or "")
    return out


@functools.lru_cache(maxsize=None)
def mobilier():
    """Supports (feux, panneaux, lampadaires...) du paquet v1 en local : [(id, catégorie, xy)]."""
    out = []
    for f in lire_geojson(DONNEES / "objets/mobilier.geojson"):
        if f["geometry"]["type"] != "Point":
            continue
        xy = repere(np.asarray(f["geometry"]["coordinates"][:2], dtype=float)[None])[0]
        if dans_emprise(xy[None])[0]:
            out.append((f["properties"]["id"], f["properties"].get("categorie"), xy))
    return sorted(out)


@functools.lru_cache(maxsize=None)
def arbres():
    out = []
    for f in lire_geojson(DONNEES / "objets/arbres.geojson"):
        if f["geometry"]["type"] != "Point":
            continue
        xy = repere(np.asarray(f["geometry"]["coordinates"][:2], dtype=float)[None])[0]
        if dans_emprise(xy[None])[0]:
            out.append((f["properties"].get("id") or f"arbre_{xy[0]:.1f}_{xy[1]:.1f}", f["properties"], xy))
    return sorted(out, key=lambda a: a[0])


@functools.lru_cache(maxsize=None)
def constats():
    """Constats vérifiés indexés par id (texte, statut, date, localisation)."""
    return {c["id"]: c for c in lire_json(CONSTATS_JSON)}


def constat(cid):
    c = constats().get(cid)
    if c is None:
        raise KeyError(f"constat absent de {CONSTATS_JSON} : {cid}")
    return c
