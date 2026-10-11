"""Contexte du SITE COMPLET (carré de 300 m centré sur O) pour les familles de sol v2 :
bordures, surfaces, îlots, ponctuels_sol et nivellement (schéma 0.3).

Même interface que `contexte.py` (zone pilote), mais toutes les lectures couvrent le carré
local [-150, 150]² (emprise du paquet v1 : L93 917129.43-917429.43 / 6460139.98-6460439.98).
Lecture seule : paquet v1 (indices sémantiques seulement), levé GAM 2026 (etat_2026, et calques
SOL_* du même Meylan_Topo.dwg en WGS84 dans vector/), OpenDRIVE, OSM, constats.

Les polygones v1 (surfaces_2026) ne servent JAMAIS de géométrie : ils ne donnent que des indices de
classe et de matériau (carte d'indices rasterisée à 0,10 m, `carte_v1`).
"""
import functools
import math

import numpy as np

import contexte as _ctx
from commun import (DONNEES, PAQUET, RACINE, VECTEURS, anneaux, aire_signee, dans_polygone,
                    lire_geojson, lire_json, repere)

CONSTATS_JSON = _ctx.CONSTATS_JSON
constats = _ctx.constats
constat = _ctx.constat
axe_local_polygone = _ctx.axe_local_polygone

DEMI = 150.0                          # demi-côté du carré du site (m, repère local)
EMPRISE = (-DEMI, -DEMI, DEMI, DEMI)
MARGE = 1.0                           # marge de lecture (m)
RES_CARTE = 0.10                      # pas des cartes d'indices (m)
ID_SITE = "SITE-300"


def anneau_site():
    x0, y0, x1, y1 = EMPRISE
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)


def zone_pilote():
    """Compatibilité avec contexte.zone_pilote() : ici l'emprise du site complet."""
    return {"anneau": anneau_site(), "emprise": EMPRISE,
            "props": {"id": ID_SITE, "emprise_local_m": dict(zip(("x_min", "y_min", "x_max", "y_max"), EMPRISE))}}


def dans_emprise(pts, marge=MARGE):
    x0, y0, x1, y1 = EMPRISE
    pts = np.atleast_2d(pts)
    return ((pts[:, 0] >= x0 - marge) & (pts[:, 0] <= x1 + marge)
            & (pts[:, 1] >= y0 - marge) & (pts[:, 1] <= y1 + marge))


def _local_polys(geom):
    return [[repere(r) for r in p] for p in anneaux(geom)]


def _lignes(geom):
    t = geom["type"]
    cs = [geom["coordinates"]] if t == "LineString" else geom["coordinates"] if t == "MultiLineString" else []
    return [np.asarray(c, dtype=np.float64)[:, :2] for c in cs if len(c) >= 2]


# --------------------------------------------------------------------------- levé GAM 2026
@functools.lru_cache(maxsize=None)
def gam_lignes(calque):
    """Polylignes locales d'un calque du levé GAM 2026 (Meylan_Topo.dwg) : [(indice, polyligne)].
    etat_2026/*_L93 pour bordure, limite_revetement, caniveau, signalisation ; sinon le même calque
    en WGS84 (vector/gam_topo_sol_*), reprojeté en Lambert-93 (pyproj)."""
    l93 = {"bordure": "bordure_lin", "limite_revetement": "limite_revetement_lin", "caniveau": "caniveau_lin",
           "signalisation_horizontale": "signalisation_horizontale_lin"}
    out = []
    if calque in l93:
        for i, f in enumerate(lire_geojson(VECTEURS / f"etat_2026/{l93[calque]}_L93.geojson")):
            for c in _lignes(f["geometry"]):
                P = repere(c)
                if dans_emprise(P, 5.0).any():
                    out.append((i, P))
        return out
    from pyproj import Transformer
    t = Transformer.from_crs(4326, 2154, always_xy=True)
    for i, f in enumerate(lire_geojson(VECTEURS / f"vector/gam_topo_sol_{calque}_lin.geojson")):
        for c in _lignes(f["geometry"]):
            x, y = t.transform(c[:, 0], c[:, 1])
            P = repere(np.c_[x, y])
            if dans_emprise(P, 5.0).any():
                out.append((i, P))
    return out


@functools.lru_cache(maxsize=None)
def chartieres_gam():
    """Blocs CHARTIERE_GAUCHE / _DROITE du levé GAM (SOL_BORDURE, points), site complet."""
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


@functools.lru_cache(maxsize=None)
def caniveaux_gam():
    """Lignes SOL_CANIVEAU du levé GAM (12 lignes) en local : [(indice, polyligne)]."""
    return [(i, P) for i, P in gam_lignes("caniveau")]


# --------------------------------------------------------------------------- paquet v1 (indices)
@functools.lru_cache(maxsize=None)
def surfaces_v1():
    """Toutes les surfaces v1 du carré (indices sémantiques seulement) : [(id, props, polys locaux)]."""
    out = []
    for f in lire_geojson(DONNEES / "surfaces/surfaces_2026.geojson"):
        polys = _local_polys(f["geometry"])
        if polys and any(dans_emprise(r, 2.0).any() for p in polys for r in p):
            out.append((f["properties"]["id"], f["properties"], polys))
    return out


def _grille():
    n = int(round(2 * DEMI / RES_CARTE))
    return n, -DEMI, DEMI          # n cellules, x0 (bord ouest), y1 (bord nord)


def rasteriser(items, defaut=-1):
    """Carte d'indices (int32, n × n, ligne 0 au nord) : items = [(valeur, polys)], peints dans
    l'ordre (les suivants recouvrent les précédents) ; trous peints à `defaut`.
    Usage : indices sémantiques (jamais de géométrie tirée de ces cartes)."""
    from PIL import Image, ImageDraw
    n, x0, y1 = _grille()
    img = Image.new("I", (n, n), defaut)
    d = ImageDraw.Draw(img)
    tp = lambda r: [((x - x0) / RES_CARTE - 0.5, (y1 - y) / RES_CARTE - 0.5) for x, y in r]
    for val, polys in items:
        for p in polys:
            if len(p[0]) >= 3:
                d.polygon(tp(p[0]), fill=int(val))
            for t in p[1:]:
                if len(t) >= 3:
                    d.polygon(tp(t), fill=int(defaut))
    return np.array(img, dtype=np.int32)


def echantillonner(carte, pts, defaut=-1):
    """Valeur de la carte (centre de cellule) sous chaque point local."""
    n, x0, y1 = _grille()
    pts = np.atleast_2d(pts)
    c = np.floor((pts[:, 0] - x0) / RES_CARTE).astype(int)
    r = np.floor((y1 - pts[:, 1]) / RES_CARTE).astype(int)
    ok = (c >= 0) & (c < n) & (r >= 0) & (r < n)
    out = np.full(len(pts), defaut, dtype=np.int64)
    out[ok] = carte[r[ok], c[ok]]
    return out


@functools.lru_cache(maxsize=None)
def carte_v1():
    """Carte d'indices des surfaces v1 (indice dans surfaces_v1(), -1 hors surfaces)."""
    sv = surfaces_v1()
    ordre = sorted(range(len(sv)), key=lambda i: -sum(abs(aire_signee(p[0])) for p in sv[i][2]))
    return rasteriser([(i, sv[i][2]) for i in ordre])


def v1_sous(pts):
    """Indice v1 (surfaces_v1) sous chaque point, -1 hors surfaces."""
    return echantillonner(carte_v1(), pts)


def classe_surface(pts):
    """Classe v1 (surfaces_2026) sous chaque point local, '' hors surfaces."""
    sv = surfaces_v1()
    idx = v1_sous(pts)
    cl = np.array([p["classe"] for _, p, _ in sv] + [""], dtype=object)
    return cl[np.where(idx >= 0, idx, len(sv))]


@functools.lru_cache(maxsize=None)
def zones_relief(nom):
    """Polygones locaux des relief_zones_2026 d'un type donné (ex. traversee_bordure_abaissee)."""
    out = []
    for i, f in enumerate(lire_geojson(DONNEES / "relief/relief_zones_2026.geojson")):
        if f["properties"]["zone"] != nom:
            continue
        for p in _local_polys(f["geometry"]):
            if any(dans_emprise(r, 2.0).any() for r in p):
                out.append((f"RZ-{i:03d}", f["properties"], p))
    return out


@functools.lru_cache(maxsize=None)
def carte_chaussee_2026():
    return rasteriser([(1, [p for _, _, p in zones_relief("chaussee_2026")])], defaut=0)


def dans_chaussee_2026(pts):
    """Points dans le masque de chaussée 2026 (relief_zones « chaussee_2026 », îlots en trous)."""
    return echantillonner(carte_chaussee_2026(), pts, 0) == 1


@functools.lru_cache(maxsize=None)
def acces_riverains():
    return [(i, p, polys) for i, p, polys in surfaces_v1() if p["classe"] == "acces_riverain"]


@functools.lru_cache(maxsize=None)
def batiments():
    """Emprises de bâtiments (batiments_local du paquet, repère local) : [(id, props, polys)]."""
    out = []
    for f in lire_geojson(DONNEES / "objets/batiments_local.geojson"):
        polys = [[np.asarray(r, dtype=np.float64) for r in p] for p in anneaux(f["geometry"])]
        if polys and any(dans_emprise(r, 2.0).any() for p in polys for r in p):
            out.append((f["properties"]["id"], f["properties"], polys))
    return sorted(out, key=lambda b: b[0])


# --------------------------------------------------------------------------- passages
def _obb(pts):
    c = pts.mean(axis=0)
    w, V = np.linalg.eigh(np.cov((pts - c).T))
    u = V[:, 1] if w[1] >= w[0] else V[:, 0]
    if u[0] < 0 or (abs(u[0]) < 1e-9 and u[1] < 0):
        u = -u
    v = np.array([-u[1], u[0]])
    pu, pv = (pts - c) @ u, (pts - c) @ v
    return c, u, v, (pu.min(), pu.max()), (pv.min(), pv.max())


def _grouper(items, lie):
    par = list(range(len(items)))

    def rac(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if lie(items[i], items[j]):
                par[rac(j)] = rac(i)
    g = {}
    for i, it in enumerate(items):
        g.setdefault(rac(i), []).append(it)
    return list(g.values())


@functools.lru_cache(maxsize=None)
def passages_pietons(ext_traversee=1.5, ext_largeur=0.0, nb_min=2):
    """Passages piétons du site (bandes `passage_pieton_bande` v1 groupées : levé GAM, plan 2025 ou
    ortho 2022) et emprise d'abaissé : boîte des bandes prolongée de `ext_traversee` m dans le sens
    de la marche. Même méthode que contexte.passages_pietons (zone pilote) : identifiants stables."""
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
            bandes.append({"id": p["id"], "pts": r, "c": c, "u": u, "long": u1 - u0, "etat": p.get("etat"),
                           "source": p.get("source", "").split(" (")[0]})
    bandes.sort(key=lambda b: b["id"])
    groupes = _grouper(bandes, lambda bi, bj: abs(bi["u"] @ bj["u"]) > 0.95 and np.hypot(*(bi["c"] - bj["c"])) < 1.6)
    out = []
    for gb in groupes:
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
        out.append({"id": f"PP-{ids[0][2:]}", "bandes": ids, "anneau": anneau, "u": u, "v": v, "c": c,
                    "nb_bandes": len(gb), "longueur_bande_m": float(np.median([b["long"] for b in gb])),
                    "largeur_m": float(pu.max() - pu.min()), "longueur_m": float(pv.max() - pv.min()),
                    "etat": sorted({b["etat"] or "" for b in gb}),
                    "sources": sorted({b["source"] for b in gb})})
    out.sort(key=lambda g: g["id"])
    return tuple(out)


@functools.lru_cache(maxsize=None)
def traversees_cyclables(ext_traversee=1.0, lien_m=2.0, n_min=3):
    """Traversées cyclables : pavés « damier » v1 des groupes traversee_cyclable_*, regroupés en grappes
    spatiales (centres à moins de 2 m) ; emprise orientée de chaque grappe prolongée de `ext_traversee`
    m dans le sens du passage (files de pavés). Règle GA-ABA-010 : franchissement sans ressaut."""
    tuiles = []
    for f in lire_geojson(DONNEES / "marquages/marquages_2026.geojson"):
        p = f["properties"]
        if p["type"] != "damier" or "traversee_cyclable" not in (p.get("groupe") or ""):
            continue
        for poly in _local_polys(f["geometry"]):
            if dans_emprise(poly[0]).any():
                tuiles.append({"id": p["id"], "groupe": p["groupe"], "r": poly[0], "c": poly[0].mean(axis=0)})
    tuiles.sort(key=lambda x: x["id"])
    grappes = [g for g in _grouper(tuiles, lambda a, b: np.hypot(*(a["c"] - b["c"])) < lien_m) if len(g) >= n_min]
    # files de pavés : les deux files d'une même traversée (parallèles, décalées de 1,5 à 6 m) sont réunies
    files = []
    for g in grappes:
        pts = np.vstack([x["r"] for x in g])
        c, u, v, (u0, u1), _ = _obb(pts)
        files.append({"g": g, "c": c, "u": u, "lu": u1 - u0, "id": min(x["id"] for x in g)})

    def paire(a, b):
        if abs(a["u"] @ b["u"]) < 0.97:
            return False
        d = b["c"] - a["c"]
        n = np.array([-a["u"][1], a["u"][0]])
        return abs(d @ a["u"]) < 0.5 * max(a["lu"], b["lu"]) and 1.0 <= abs(d @ n) <= 6.0
    out = []
    for fs in _grouper(sorted(files, key=lambda f: f["id"]), paire):
        g = [x for f in fs for x in f["g"]]
        pts = np.vstack([x["r"] for x in g])
        u = np.sum([f["u"] * (1.0 if f["u"] @ fs[0]["u"] >= 0 else -1.0) for f in fs], axis=0)
        u /= np.hypot(*u)
        v = np.array([-u[1], u[0]])
        c = pts.mean(axis=0)
        u0, u1 = ((pts - c) @ u).min(), ((pts - c) @ u).max()
        v0, v1 = ((pts - c) @ v).min(), ((pts - c) @ v).max()
        anneau = np.array([c + u * a + v * b for a, b in ((u0 - ext_traversee, v0), (u1 + ext_traversee, v0),
                                                            (u1 + ext_traversee, v1), (u0 - ext_traversee, v1))])
        ids = sorted(x["id"] for x in g)
        out.append({"id": f"TC-{ids[0][2:]}", "groupe": g[0]["groupe"], "anneau": anneau, "u": u, "v": v, "c": c,
                    "n_paves": len(g), "longueur_m": float(u1 - u0), "largeur_m": float(v1 - v0)})
    out.sort(key=lambda x: x["id"])
    return tuple(out)


@functools.lru_cache(maxsize=None)
def osm_traversees():
    """Nœuds OSM highway=crossing (tactile_paving) en local, site complet."""
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


# --------------------------------------------------------------------------- OpenDRIVE
@functools.lru_cache(maxsize=None)
def voies_xodr():
    """Polygones de voies OpenDRIVE (lanes_2026.geojson, repère L93 -> local) :
    [(route, voie, type, section_s, jonction, polys)]."""
    out = []
    for f in lire_geojson(DONNEES / "opendrive/lanes_2026.geojson"):
        p = f["properties"]
        if f["geometry"]["type"] not in ("Polygon", "MultiPolygon") or p.get("voie") in (None, 0):
            continue
        polys = _local_polys(f["geometry"])
        out.append((int(p["route"]), int(p["voie"]), p.get("type") or "", float(p.get("section_s") or 0.0),
                    bool(p.get("jonction")), polys))
    return sorted(out, key=lambda v: (v[0], v[3], v[1]))


@functools.lru_cache(maxsize=None)
def parkings_osm():
    """Aires de stationnement OSM (amenity=parking, polygones de surface ; ni silo ni souterrain) :
    [(osm_id, anneau local)]. Limites vectorielles (relevé OSM) des parkings hors levé GAM."""
    from pyproj import Transformer
    t = Transformer.from_crs(4326, 2154, always_xy=True)
    out = []
    for f in lire_geojson(VECTEURS / "vector/osm_parking.geojson"):
        p, g = f["properties"], f["geometry"]
        if g["type"] != "Polygon" or p.get("amenity") != "parking" or p.get("parking") in ("multi-storey", "underground"):
            continue
        r = np.asarray(g["coordinates"][0], dtype=np.float64)[:, :2]
        x, y = t.transform(r[:, 0], r[:, 1])
        P = repere(np.c_[x, y])
        if dans_emprise(P, 5.0).any():
            out.append((str(p.get("osm_id")), P))
    return sorted(out, key=lambda o: o[0])


TYPES_CHAUSSEE = {"driving", "bus", "biking", "parking", "stop", "shoulder", "entry", "exit", "onRamp", "offRamp"}


@functools.lru_cache(maxsize=None)
def carte_xodr():
    """Cartes d'indices OpenDRIVE (indices sémantiques) : (route, code type) par cellule.
    route : numéro de route (0 hors voies) ; type : 1 chaussée (driving/bus/biking...), 2 trottoir,
    3 bordure (curb), 4 accotement (border), 5 terre-plein (median)."""
    code = {"sidewalk": 2, "curb": 3, "border": 4, "median": 5}
    vs = voies_xodr()
    route = rasteriser([(r, polys) for r, v, t, s, j, polys in vs], defaut=0)
    typ = rasteriser([(1 if t in TYPES_CHAUSSEE else code.get(t, 4), polys) for r, v, t, s, j, polys in vs], defaut=0)
    return route, typ


def xodr_sous(pts):
    """(route, code type) OpenDRIVE sous chaque point local (0 hors voies)."""
    route, typ = carte_xodr()
    return echantillonner(route, pts, 0), echantillonner(typ, pts, 0)


# --------------------------------------------------------------------------- obstacles du cheminement
@functools.lru_cache(maxsize=None)
def obstacles_trottoir():
    """Segments (A, B) qui limitent un trottoir derrière une bordure (largeur utile, GA-ABA-003,
    GA-CHR-002/003) : toutes les arêtes de bordure GAM (double arête comprise), limites de revêtement,
    végétation, clôtures, escaliers et rampes du levé GAM 2026, emprises de bâtiments."""
    lignes = []
    for calque in ("bordure", "limite_revetement", "vegetation", "clotures", "escalier_rampe"):
        lignes += [P for _, P in gam_lignes(calque)]
    for _, _, polys in batiments():
        for p in polys:
            for r in p:
                lignes.append(np.vstack([r, r[:1]]))
    A = np.vstack([P[:-1] for P in lignes])
    B = np.vstack([P[1:] for P in lignes])
    return A, B


def rayon(o, u, A, B, dmax=10.0, dmin=1e-3):
    """Distance le long du rayon o + t·u (t ∈ ]dmin, dmax]) au premier segment [A, B] rencontré
    (dmax si aucun)."""
    s_ = B - A
    den = u[0] * s_[:, 1] - u[1] * s_[:, 0]
    ap = A - o
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (ap[:, 0] * s_[:, 1] - ap[:, 1] * s_[:, 0]) / den
        w = (ap[:, 0] * u[1] - ap[:, 1] * u[0]) / den
    m = (np.abs(den) > 1e-12) & (t > dmin) & (t <= dmax) & (w >= 0) & (w <= 1)
    return float(t[m].min()) if m.any() else float(dmax)
