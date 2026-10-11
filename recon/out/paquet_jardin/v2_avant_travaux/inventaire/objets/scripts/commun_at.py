"""Outils communs du recensement des objets avant travaux (lecture seule du dépôt).

Repère : local = L93 - O, O = (917279.43, 6460289.98), z = NGF - 216.30.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from pyproj import Transformer

RACINE = Path(__file__).resolve().parents[7]
O = (917279.43, 6460289.98, 216.30)
SORTIE = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/objets"
TELE = RACINE / "data/sites/paquet_jardin/avant_travaux"
EMPRISE_L93 = (917129.43, 6460139.98, 917429.43, 6460439.98)   # ±150 m autour de O

DEBUT_TRAVAUX = "2025-06-23"
FIN_TRAVAUX = "2025-12-05"
FIN_TROTTOIRS_VERCORS = "2026-01-30"
FENETRE = ("2022-01-01", DEBUT_TRAVAUX)          # « 2022 à 2025 environ », avant le chantier
FENETRE_PHOTOS = ("2023-01-01", DEBUT_TRAVAUX)   # couverture photo demandée : 2023-2025 avant travaux

_W2L = Transformer.from_crs(4326, 2154, always_xy=True)
_L2W = Transformer.from_crs(2154, 4326, always_xy=True)


def wgs_l93(lon, lat):
    x, y = _W2L.transform(lon, lat)
    return float(x), float(y)


def l93_wgs(x, y):
    lon, lat = _L2W.transform(x, y)
    return float(lon), float(lat)


def lire(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def ecrire(p, obj, indent=1):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")


def dans_emprise(x, y, marge=0.0):
    x0, y0, x1, y1 = EMPRISE_L93
    return x0 - marge <= x <= x1 + marge and y0 - marge <= y <= y1 + marge


# ----------------------------------------------------------------------------- polygones
def _anneaux(g):
    if g is None:
        return []
    if g["type"] == "Polygon":
        return [np.asarray(g["coordinates"][0], float)[:, :2]]
    if g["type"] == "MultiPolygon":
        return [np.asarray(p[0], float)[:, :2] for p in g["coordinates"]]
    return []


def dans_anneau(pt, R):
    x, y = pt
    xa, ya = R[:, 0], R[:, 1]
    xb, yb = np.roll(xa, -1), np.roll(ya, -1)
    cond = (ya > y) != (yb > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = xa + (y - ya) * (xb - xa) / (yb - ya)
    return bool(np.count_nonzero(cond & (x < xi)) % 2)


def dist_anneau(pt, R):
    A, B = R, np.roll(R, -1, axis=0)
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    P = np.asarray(pt, float)
    t = np.clip(((P - A) * AB).sum(1) / L2, 0, 1)
    Q = A + t[:, None] * AB
    return float(np.hypot(*(P - Q).T).min())


class Zones:
    """Zone des travaux 2025 (surfaces v1 « modifie_2025 » + zones de relief reprises) et
    surfaces construites 2023-2024 (secteur est), en L93."""

    def __init__(self):
        surf = lire(RACINE / "recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson")
        self.travaux, self.c23 = [], []
        for f in surf["features"]:
            e = f["properties"].get("etat")
            for R in _anneaux(f["geometry"]):
                if e == "modifie_2025":
                    self.travaux.append(R)
                elif e == "construit_2023_2024":
                    self.c23.append(R)
        rz = lire(RACINE / "recon/out/paquet_jardin/package/donnees/relief/relief_zones_2026.geojson")
        for f in rz["features"]:
            if f["properties"].get("zone") in ("ancienne_chaussee_rehaussee_2025", "traversee_bordure_abaissee",
                                               "ancienne_chaussee_trottoir_par_defaut"):
                self.travaux += _anneaux(f["geometry"])
        self._bb_t = [(R[:, 0].min(), R[:, 1].min(), R[:, 0].max(), R[:, 1].max()) for R in self.travaux]
        self._bb_c = [(R[:, 0].min(), R[:, 1].min(), R[:, 0].max(), R[:, 1].max()) for R in self.c23]

    @staticmethod
    def _dist(pt, anneaux, bbs, dmax=50.0):
        best = math.inf
        for R, bb in zip(anneaux, bbs):
            if pt[0] < bb[0] - dmax or pt[0] > bb[2] + dmax or pt[1] < bb[1] - dmax or pt[1] > bb[3] + dmax:
                continue
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and dans_anneau(pt, R):
                return 0.0
            best = min(best, dist_anneau(pt, R))
        return best

    def d_travaux(self, pt):
        return self._dist(pt, self.travaux, self._bb_t)

    def d_c23(self, pt):
        return self._dist(pt, self.c23, self._bb_c)


class Batiments:
    """Emprises de bâtiments (paquet v1, BD TOPO, repère local -> L93) pour l'occultation 2D."""

    def __init__(self):
        b = lire(RACINE / "recon/out/paquet_jardin/package/donnees/objets/batiments_local.geojson")
        self.segs = []
        for f in b["features"]:
            for R in _anneaux(f["geometry"]):
                R = R + np.array(O[:2])
                self.segs.append(np.stack([R, np.roll(R, -1, axis=0)], 1))
        self.S = np.concatenate(self.segs) if self.segs else np.zeros((0, 2, 2))

    def occulte(self, c, p, marge=0.6):
        """Vrai si le segment caméra -> objet (raccourci de `marge` m côté objet) coupe une façade."""
        c = np.asarray(c, float)
        p = np.asarray(p, float)
        d = p - c
        L = float(np.hypot(*d))
        if L < 1e-6 or len(self.S) == 0:
            return False
        p2 = c + d * max(0.0, (L - marge) / L)
        A, B = self.S[:, 0], self.S[:, 1]

        def orient(a, b, q):
            return (b[..., 0] - a[..., 0]) * (q[..., 1] - a[..., 1]) - (b[..., 1] - a[..., 1]) * (q[..., 0] - a[..., 0])

        o1 = orient(A, B, c[None])
        o2 = orient(A, B, p2[None])
        o3 = orient(c[None], p2[None], A)
        o4 = orient(c[None], p2[None], B)
        return bool(np.any((o1 * o2 < 0) & (o3 * o4 < 0)))


# ----------------------------------------------------------------------------- typologie
# type unifié -> (rayon d'association en m, hauteur par défaut en m, petit objet ?)
TYPES = {
    "arbre": (2.5, 8.0, False),
    "lampadaire": (4.0, 8.0, False),
    "feu": (4.0, 3.5, False),
    "panneau": (3.5, 2.6, True),
    "potelet": (1.5, 1.0, True),
    "barriere": (3.0, 1.1, True),
    "banc": (4.0, 0.85, True),
    "abri_bus": (6.0, 2.6, False),
    "poteau_arret": (4.0, 2.8, True),
    "borne": (3.0, 0.9, True),
    "armoire": (4.0, 1.4, True),
    "poteau": (3.5, 7.0, False),
    "corbeille": (3.0, 1.0, True),
    "arceaux_velos": (5.0, 0.8, True),
    "autre_mobilier": (4.0, 1.5, True),
}

# familles compatibles (une détection de mât générique peut porter un panneau, un feu, un lampadaire)
SUPPORTS = {"poteau", "panneau", "feu", "lampadaire", "poteau_arret"}


def type_desc_2026(p):
    """Type unifié (type, sous_type) d'un objet de la description 2026 (mobilier.geojson)."""
    t = p.get("type")
    st = p.get("sous_type")
    if t == "lampadaire":
        return "lampadaire", st or "mât"
    if t == "support_feux":
        tetes = json.dumps(p.get("tetes") or "", ensure_ascii=False)
        r = (p.get("role") or "") + " " + (p.get("id") or "")
        if "cycl" in r:
            return "feu", "cycles"
        if (p.get("nb_tetes_R11v") or 0) > 0 or "R11" in tetes:
            return "feu", "tricolore" + ("+pietons" if (p.get("nb_tetes_R12") or 0) > 0 else "")
        if (p.get("nb_tetes_R12") or 0) > 0 or "pieton" in r:
            return "feu", "pietons"
        return "feu", "indetermine"
    if t == "panneau":
        code = (p.get("code") or "")
        if code.startswith("D") or code.startswith("E"):
            return "panneau", "directionnel"
        if code.startswith(("C", "CE")):
            return "panneau", "indication"
        if code.startswith(("A", "AB", "B", "J", "M")):
            return "panneau", "police"
        return "panneau", "inconnu"
    if t == "balise_J11":
        return "panneau", "balise_J11"
    if t == "panneau_information":
        return "panneau", "information"
    if t == "potelet":
        return "potelet", None
    if t in ("barriere_levante", "portail", "chicane"):
        return "barriere", t
    if t == "cloture":
        return "barriere", "cloture"
    if t == "banc":
        return "banc", None
    if t == "abri_bus":
        return "abri_bus", None
    if t == "poteau_arret":
        return "poteau_arret", None
    if t == "poteau_incendie":
        return "borne", "incendie"
    if t in ("armoire", "abri_technique"):
        return "armoire", t
    if t == "poteau_reseau":
        return "poteau", "reseau"
    if t == "mat_camera":
        return "poteau", "mat_camera"
    if t == "corbeille":
        return "corbeille", None
    if t == "stationnement_velos":
        return "arceaux_velos", None
    return "autre_mobilier", t


def type_mapillary(v):
    """Type unifié d'une valeur Mapillary (map feature) ; None = hors champ (sol, enseignes)."""
    if v.startswith("regulatory--") or v.startswith("warning--"):
        return "panneau", "police"
    if v.startswith("information--general-directions"):
        return "panneau", "directionnel"
    if v.startswith("information--") or v.startswith("complementary--"):
        return "panneau", "indication"
    m = {
        "object--street-light": ("lampadaire", None),
        "object--support--utility-pole": ("poteau", "support_indetermine"),
        "object--traffic-sign--front": ("panneau", "generique"),
        "object--traffic-sign--back": ("panneau", "generique_dos"),
        "object--traffic-sign--direction-front": ("panneau", "directionnel"),
        "object--traffic-sign--direction-back": ("panneau", "directionnel_dos"),
        "object--traffic-sign--information-parking": ("panneau", "indication"),
        "object--sign--information": ("panneau", "information"),
        "object--traffic-light--general-upright": ("feu", "tricolore"),
        "object--traffic-light--general-upright-front": ("feu", "tricolore"),
        "object--traffic-light--general-upright-side": ("feu", "tricolore"),
        "object--traffic-light--general-single": ("feu", "tricolore"),
        "object--traffic-light--general-single-front": ("feu", "tricolore"),
        "object--traffic-light--pedestrians": ("feu", "pietons"),
        "object--traffic-light--pedestrians-front": ("feu", "pietons"),
        "object--traffic-light--pedestrians-side": ("feu", "pietons"),
        "object--traffic-light--cyclists": ("feu", "cycles"),
        "object--traffic-light--cyclists-front": ("feu", "cycles"),
        "object--trash-can": ("corbeille", None),
        "object--junction-box": ("armoire", "coffret"),
        "object--bench": ("banc", None),
        "object--bike-rack": ("arceaux_velos", None),
        "object--fire-hydrant": ("borne", "incendie"),
        "object--sign--advertisement": ("autre_mobilier", "affichage_publicitaire"),
        "construction--barrier--temporary": ("barriere", "temporaire"),
    }
    return m.get(v, (None, None))


def type_osm(t):
    """Type unifié d'un élément OSM (tags) ; None = hors champ."""
    g = t.get
    if g("highway") == "street_lamp":
        return "lampadaire", g("lamp_mount") or None
    if g("traffic_sign") and g("highway") not in ("stop", "give_way", "crossing", "traffic_signals"):
        return "panneau", "police"
    if g("highway") in ("stop", "give_way") and g("direction") is None and g("traffic_sign") is None:
        return None, None
    if g("barrier") == "bollard":
        return "potelet", None
    if g("barrier") in ("lift_gate", "gate", "swing_gate", "sliding_gate", "wicket_gate", "cycle_barrier", "chain"):
        return "barriere", {"lift_gate": "barriere_levante", "cycle_barrier": "chicane"}.get(g("barrier"), "portail")
    if g("barrier") in ("fence", "guard_rail", "handrail"):
        return "barriere", "cloture"
    if g("barrier") == "block":
        return "autre_mobilier", "bloc"
    if g("amenity") == "bench" or g("leisure") == "picnic_table":
        return "banc", None
    if g("amenity") == "waste_basket":
        return "corbeille", None
    if g("amenity") == "bicycle_parking":
        return "arceaux_velos", g("bicycle_parking")
    if g("amenity") == "shelter" and g("shelter_type") in (None, "public_transport"):
        return "abri_bus", None
    if g("public_transport") == "stop_position":
        return None, None          # nœud sur la chaussée, pas un objet
    if g("highway") == "bus_stop" or g("public_transport") in ("platform", "pole"):
        return "poteau_arret", None
    if g("emergency") == "fire_hydrant":
        return "borne", "incendie"
    if g("amenity") == "charging_station":
        return "borne", "recharge"
    if g("man_made") == "street_cabinet" or g("power") == "cabinet":
        return "armoire", g("street_cabinet") or None
    if g("man_made") in ("utility_pole", "mast") or g("power") in ("pole",):
        return "poteau", "reseau"
    if g("man_made") == "surveillance":
        if g("camera:mount") in ("pole", "street_lamp"):
            return "poteau", "mat_camera"
        return None, None          # caméras sur façade ou toit : hors champ
    if g("advertising"):
        return "autre_mobilier", "affichage_publicitaire"
    if g("tourism") == "information" and g("information") in ("board", "map", None):
        return "panneau", "information"
    if g("amenity") in ("post_box", "vending_machine", "recycling", "drinking_water", "parcel_locker"):
        return "autre_mobilier", g("amenity")
    if g("natural") == "tree":
        return "arbre", g("leaf_type")
    return None, None
