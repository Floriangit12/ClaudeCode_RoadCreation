"""Échantillonneur OpenDRIVE 1.7 (Python + numpy) : ligne de référence, laneOffset, largeurs de voie
par laneSection, bords de voie en polylignes du repère local, au pas ≤ 0,10 m, avec leur abscisse s.

Usage :
    python recon/pcg/decrire/xodr_echantillonne.py [--xodr F] [--pas 0.10] [--json RAPPORT.json]
    -> validation contre donnees/opendrive/lanes_2026.geojson (écart des bords, p50 / p95 / max)

API :
    reseau = lire_xodr(chemin)                 {id: Route}
    route.reference(s) -> (x, y, hdg)          ligne de référence (planView), s scalaire ou tableau
    route.decalage(s)  -> laneOffset(s)
    route.t_bords(s)   -> {voie: t du bord EXTÉRIEUR} pour la laneSection de s (voie 0 = laneOffset)
    bords_route(route, pas) -> [Bord]          un bord par (laneSection, voie), voie 0 compris
    Bord : route, section_s, s0, s1, voie, type_voie, voie_int (voisine intérieure), s (N,), t (N,),
           xy (N, 2) local, hdg (N,), z (N,) (élévation de la référence, superélévation ignorée)
    point_st(route, s, t) -> (x, y, hdg)       pose d'un point (s, t) du repère de route

Conventions (ASAM OpenDRIVE 1.7) : t > 0 à gauche de la référence ; voies gauches id > 0, droites
id < 0 ; le bord d'une voie id ≠ 0 est son bord EXTÉRIEUR (|t| croissant) ; le roadMark d'une voie
porte sur ce bord, celui de la voie centrale sur la référence décalée (laneOffset).
paramPoly3 pRange « normalized » : p = (s − s_geom) / longueur (correspondance linéaire, comme esmini
et CARLA) ; « arcLength » : p = s − s_geom. Le repère du .xodr est déjà le repère local (header offset
= O) : aucune conversion ici (commun.repere sert à repasser en Lambert-93).
"""
import argparse
import bisect
import json
import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import DONNEES, PAQUET, anneaux, distance_segments, lire_geojson, repere  # noqa: E402

XODR = PAQUET / "paquet_jardin_2026.xodr"
LANES = DONNEES / "opendrive/lanes_2026.geojson"
PAS = 0.10
MODE_P = "arc"            # correspondance s -> p des paramPoly3 (voir docstring)


# --------------------------------------------------------------------------- géométries planView
def _fresnel_pts(k0, k1, L, n):
    """Clothoïde de courbure k0 -> k1 sur L (repère local du début, cap 0) : intégration de Simpson."""
    s = np.linspace(0.0, L, n)
    th = k0 * s + 0.5 * (k1 - k0) / max(L, 1e-12) * s ** 2
    c, si = np.cos(th), np.sin(th)
    ds = np.diff(s)
    x = np.r_[0.0, np.cumsum(0.5 * (c[1:] + c[:-1]) * ds)]
    y = np.r_[0.0, np.cumsum(0.5 * (si[1:] + si[:-1]) * ds)]
    return s, x, y, th


@dataclass
class Geom:
    s: float
    x: float
    y: float
    hdg: float
    L: float
    genre: str
    p: dict

    def evaluer(self, ds):
        """(x, y, hdg) aux abscisses locales ds ∈ [0, L] (tableau)."""
        ds = np.clip(np.asarray(ds, dtype=np.float64), 0.0, self.L)
        c0, s0 = math.cos(self.hdg), math.sin(self.hdg)
        if self.genre == "line":
            u, v, th = ds, np.zeros_like(ds), np.zeros_like(ds)
        elif self.genre == "arc":
            k = self.p["curvature"]
            if abs(k) < 1e-12:
                u, v, th = ds, np.zeros_like(ds), np.zeros_like(ds)
            else:
                th = k * ds
                u, v = np.sin(th) / k, (1 - np.cos(th)) / k
        elif self.genre == "spiral":
            n = max(200, int(self.L / 0.01))
            sg, xg, yg, tg = _fresnel_pts(self.p["curvStart"], self.p["curvEnd"], self.L, n)
            u, v, th = np.interp(ds, sg, xg), np.interp(ds, sg, yg), np.interp(ds, sg, tg)
        elif self.genre == "poly3":
            # v(u) = a + b u + c u² + d u³ ; u obtenu par inversion de la longueur d'arc
            a, b, c, d = (self.p[k] for k in "abcd")
            ug = np.linspace(0.0, self.L * 1.5, 4000)
            dv = b + 2 * c * ug + 3 * d * ug ** 2
            sg = np.r_[0.0, np.cumsum(0.5 * (np.hypot(1, dv[1:]) + np.hypot(1, dv[:-1])) * np.diff(ug))]
            u = np.interp(ds, sg, ug)
            v = a + b * u + c * u ** 2 + d * u ** 3
            th = np.arctan(b + 2 * c * u + 3 * d * u ** 2)
        elif self.genre == "paramPoly3":
            q = self.p
            p = self._p_de_s(ds)
            u = q["aU"] + q["bU"] * p + q["cU"] * p ** 2 + q["dU"] * p ** 3
            v = q["aV"] + q["bV"] * p + q["cV"] * p ** 2 + q["dV"] * p ** 3
            du = q["bU"] + 2 * q["cU"] * p + 3 * q["dU"] * p ** 2
            dv = q["bV"] + 2 * q["cV"] * p + 3 * q["dV"] * p ** 2
            th = np.arctan2(dv, du)
        else:
            raise ValueError(f"géométrie planView non gérée : {self.genre}")
        x = self.x + u * c0 - v * s0
        y = self.y + u * s0 + v * c0
        return x, y, self.hdg + th

    def _p_de_s(self, ds):
        """Paramètre p de la paramPoly3 à l'abscisse curviligne ds (MODE_P : 'lineaire' ou 'arc')."""
        q = self.p
        norm = q.get("pRange", "normalized") == "normalized"
        pmax = 1.0 if norm else self.L
        if MODE_P == "lineaire":
            return ds / self.L * pmax
        if not hasattr(self, "_table"):
            pg = np.linspace(0.0, pmax, 4001)
            du = q["bU"] + 2 * q["cU"] * pg + 3 * q["dU"] * pg ** 2
            dv = q["bV"] + 2 * q["cV"] * pg + 3 * q["dV"] * pg ** 2
            v = np.hypot(du, dv)
            sg = np.r_[0.0, np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(pg))]
            self._table = (sg * (self.L / sg[-1]), pg)
        sg, pg = self._table
        return np.interp(ds, sg, pg)


def _poly(ds, a, b, c, d):
    return a + b * ds + c * ds ** 2 + d * ds ** 3


@dataclass
class Morceaux:
    """Fonction cubique par morceaux (laneOffset, elevation, width) : [(s_debut, a, b, c, d)]."""
    m: list = field(default_factory=list)

    def __call__(self, s, defaut=0.0):
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        if not self.m:
            return np.full(len(s), defaut)
        debuts = [x[0] for x in self.m]
        out = np.empty(len(s))
        for i, si in enumerate(s):
            k = max(0, bisect.bisect_right(debuts, si + 1e-9) - 1)
            s0, a, b, c, d = self.m[k]
            out[i] = _poly(si - s0, a, b, c, d)
        return out


@dataclass
class Voie:
    id: int
    type: str
    largeur: Morceaux          # sOffset relatif au début de la laneSection
    marques: list              # roadMark (dict d'attributs + 'lignes' [(length, space, tOffset, sOffset, width)])
    xml: object = None


@dataclass
class Section:
    s: float
    s1: float
    voies: dict                # id -> Voie (id 0 compris)


@dataclass
class Route:
    id: str
    nom: str
    longueur: float
    jonction: str
    geoms: list
    decalage_: Morceaux
    elevation_: Morceaux
    sections: list
    xml: object = None

    def _geom_index(self, s):
        debuts = [g.s for g in self.geoms]
        return np.clip(np.searchsorted(debuts, s, side="right") - 1, 0, len(self.geoms) - 1)

    def reference(self, s):
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        x, y, h = np.empty(len(s)), np.empty(len(s)), np.empty(len(s))
        idx = self._geom_index(s)
        for k in np.unique(idx):
            m = idx == k
            g = self.geoms[k]
            x[m], y[m], h[m] = g.evaluer(s[m] - g.s)
        return x, y, h

    def decalage(self, s):
        return self.decalage_(s, 0.0)

    def elevation(self, s):
        return self.elevation_(s, 0.0)

    def section(self, s):
        debuts = [sec.s for sec in self.sections]
        return self.sections[max(0, bisect.bisect_right(debuts, float(s) + 1e-9) - 1)]

    def t_bords(self, s, sec=None):
        """{voie: t du bord extérieur} aux abscisses s (tableaux), pour la laneSection `sec`
        (défaut : celle de s[0])."""
        s = np.atleast_1d(np.asarray(s, dtype=np.float64))
        sec = sec or self.section(s[0])
        off = self.decalage(s)
        out = {0: off}
        for signe in (1, -1):
            cum = off.copy()
            k = signe
            while k in sec.voies:
                cum = cum + signe * sec.voies[k].largeur(s - sec.s)
                out[k] = cum
                k += signe
        return out


def point_st(route, s, t):
    """Pose (x, y, hdg) des points (s, t) du repère de route (tableaux)."""
    x, y, h = route.reference(s)
    t = np.asarray(t, dtype=np.float64)
    return x - t * np.sin(h), y + t * np.cos(h), h


# --------------------------------------------------------------------------- lecture
def _f(e, k, d=0.0):
    v = e.get(k)
    return float(v) if v is not None else d


def _marques(lane):
    out = []
    for rm in lane.findall("roadMark"):
        d = dict(rm.attrib)
        d["sOffset"] = _f(rm, "sOffset")
        lignes = []
        ty = rm.find("type")
        if ty is not None:
            d["nom_type"] = ty.get("name")
            for li in ty.findall("line"):
                lignes.append({k: (float(v) if k in ("length", "space", "tOffset", "sOffset", "width") else v)
                               for k, v in li.attrib.items()})
        d["lignes"] = lignes
        out.append(d)
    return sorted(out, key=lambda m: m["sOffset"])


def lire_xodr(chemin=XODR):
    racine = ET.parse(chemin).getroot()
    reseau = {}
    for r in racine.findall("road"):
        geoms = []
        for g in r.find("planView").findall("geometry"):
            enf = list(g)[0]
            geoms.append(Geom(_f(g, "s"), _f(g, "x"), _f(g, "y"), _f(g, "hdg"), _f(g, "length"), enf.tag,
                              {k: (float(v) if k != "pRange" else v) for k, v in enf.attrib.items()}))
        geoms.sort(key=lambda g: g.s)
        lanes = r.find("lanes")
        dec = Morceaux(sorted((_f(o, "s"), _f(o, "a"), _f(o, "b"), _f(o, "c"), _f(o, "d"))
                              for o in lanes.findall("laneOffset")))
        ep = r.find("elevationProfile")
        elev = Morceaux(sorted((_f(o, "s"), _f(o, "a"), _f(o, "b"), _f(o, "c"), _f(o, "d"))
                               for o in (ep.findall("elevation") if ep is not None else [])))
        L = _f(r, "length")
        secs_xml = sorted(lanes.findall("laneSection"), key=lambda e: _f(e, "s"))
        sections = []
        for i, ls in enumerate(secs_xml):
            s0 = _f(ls, "s")
            s1 = _f(secs_xml[i + 1], "s") if i + 1 < len(secs_xml) else L
            voies = {}
            for cote in ("left", "center", "right"):
                c = ls.find(cote)
                if c is None:
                    continue
                for ln in c.findall("lane"):
                    lid = int(ln.get("id"))
                    larg = Morceaux(sorted((_f(w, "sOffset"), _f(w, "a"), _f(w, "b"), _f(w, "c"), _f(w, "d"))
                                           for w in ln.findall("width")))
                    voies[lid] = Voie(lid, ln.get("type"), larg, _marques(ln), ln)
            sections.append(Section(s0, s1, voies))
        reseau[r.get("id")] = Route(r.get("id"), r.get("name", ""), L, r.get("junction", "-1"), geoms, dec, elev,
                                    sections, r)
    return reseau


# --------------------------------------------------------------------------- bords de voie
@dataclass
class Bord:
    route: str
    section_s: float
    s0: float
    s1: float
    voie: int
    type_voie: str
    voie_int: object           # voisine intérieure (id) ou None pour la voie 0
    s: np.ndarray
    t: np.ndarray
    xy: np.ndarray
    hdg: np.ndarray
    z: np.ndarray

    @property
    def cle(self):
        return f"{self.route}/{self.section_s:g}/{self.voie}"


def abscisses_section(s0, s1, pas=PAS):
    n = max(1, int(math.ceil((s1 - s0) / pas - 1e-9)))
    return np.linspace(s0, s1, n + 1)


def _grille_section(route, sec, pas):
    """Abscisses de la laneSection telles que tous ses bords soient échantillonnés au pas ≤ `pas`
    (subdivision là où un bord extérieur de virage s'étire), en 3 passes au plus."""
    s = abscisses_section(sec.s, sec.s1, pas)
    for _ in range(3):
        x, y, h = route.reference(s)
        tb = route.t_bords(s, sec)
        ecart = np.zeros(len(s) - 1)
        for t in tb.values():
            ecart = np.maximum(ecart, np.hypot(np.diff(x - t * np.sin(h)), np.diff(y + t * np.cos(h))))
        k = np.ceil(ecart / pas - 1e-9).astype(int)
        if np.all(k <= 1):
            break
        s = np.unique(np.concatenate([np.linspace(a, b, n + 1) for a, b, n in zip(s[:-1], s[1:], np.maximum(k, 1))]))
    return s


def _densifier_bord(s, t, xy, h, z, pas):
    """Comble linéairement les sauts résiduels > pas (cap discontinu entre deux géométries planView)."""
    d = np.hypot(*np.diff(xy, axis=0).T)
    if np.all(d <= pas + 1e-9):
        return s, t, xy, h, z
    morceaux = [[a] for a in (s[:1], t[:1], xy[:1], h[:1], z[:1])]
    for i in range(len(s) - 1):
        n = max(1, int(math.ceil(d[i] / pas - 1e-9)))
        f = np.arange(1, n + 1) / n
        for m, a in zip(morceaux, (s, t, xy, h, z)):
            m.append(a[i] + (a[i + 1] - a[i]) * (f[:, None] if a.ndim == 2 else f))
    return tuple(np.concatenate(m) for m in morceaux)


def bords_route(route, pas=PAS):
    """Bords extérieurs de toutes les voies (et la référence décalée, voie 0) de chaque laneSection."""
    out = []
    for sec in route.sections:
        s = _grille_section(route, sec, pas)
        x, y, h = route.reference(s)
        z = route.elevation(s)
        tb = route.t_bords(s, sec)
        for v, t in sorted(tb.items()):
            vi = None if v == 0 else (v - 1 if v > 0 else v + 1)
            xy = np.c_[x - t * np.sin(h), y + t * np.cos(h)]
            sv, tv, xyv, hv, zv = _densifier_bord(s, t, xy, h, z, pas)
            out.append(Bord(route.id, sec.s, sec.s, sec.s1, v, sec.voies[v].type if v in sec.voies else "none",
                            vi, sv, tv, xyv, hv, zv))
    return out


def tous_les_bords(reseau, pas=PAS):
    return [b for rid in sorted(reseau, key=lambda k: int(k)) for b in bords_route(reseau[rid], pas)]


# --------------------------------------------------------------------------- objets
def objets(reseau):
    """Objets des routes (crosswalk, roadMark, stopLine, flèches, îlots...) : dict avec route, id, type,
    sous_type, nom, s, t, cap (rad, route + objet), longueur, largeur, anneau (contour local ou None)."""
    out = []
    for rid in sorted(reseau, key=int):
        r = reseau[rid]
        obs = r.xml.find("objects")
        if obs is None:
            continue
        for o in obs.findall("object"):
            s, t = _f(o, "s"), _f(o, "t")
            x, y, h = point_st(r, np.array([s]), np.array([t]))
            H = float(h[0]) + _f(o, "hdg")
            anneau = None
            ol = o.find("outlines")
            if ol is not None:
                coins = ol.find("outline").findall("cornerLocal")
                if coins:
                    uv = np.array([[_f(c, "u"), _f(c, "v")] for c in coins])
                    anneau = np.c_[x[0] + uv[:, 0] * math.cos(H) - uv[:, 1] * math.sin(H),
                                   y[0] + uv[:, 0] * math.sin(H) + uv[:, 1] * math.cos(H)]
            ud = {u.get("code"): u.get("value") for u in o.findall("userData")}
            out.append({"route": rid, "id": o.get("id"), "type": o.get("type"), "sous_type": o.get("subtype"),
                        "nom": o.get("name", ""), "s": s, "t": t, "xy": np.array([x[0], y[0]]), "cap": H,
                        "longueur": _f(o, "length", None), "largeur": _f(o, "width", None), "anneau": anneau,
                        "userData": ud})
    return out


def marque_active(route, section_s, voie, s):
    """roadMark actif (dict) du bord (section, voie) à l'abscisse de route s, ou None."""
    sec = next((x for x in route.sections if abs(x.s - section_s) < 1e-6), None)
    if sec is None or voie not in sec.voies:
        return None
    act = None
    for m in sec.voies[voie].marques:
        if sec.s + m["sOffset"] <= s + 1e-6:
            act = m
    return act


# --------------------------------------------------------------------------- validation
def valider(reseau, pas=PAS, chemin_lanes=LANES):
    """Écart des bords échantillonnés aux polygones de lanes_2026.geojson (même route, voie, section).
    Pour chaque voie ≠ 0 : distance de chaque échantillon de ses bords intérieur et extérieur à l'anneau
    du polygone (extrémités exclues sur 0,3 m : les côtés transversaux de l'anneau)."""
    feats = lire_geojson(chemin_lanes)
    polys = {}
    for f in feats:
        p = f["properties"]
        if p.get("type") in (None, "reference") or p.get("voie") in (None, 0):
            continue
        cle = (str(p["route"]), round(float(p.get("section_s", 0.0)), 2), int(p["voie"]))
        polys[cle] = [repere(r) for r in anneaux(f["geometry"])[0]]
    d_all, par_route, manquants = [], {}, []
    for rid in sorted(reseau, key=int):
        r = reseau[rid]
        bs = {(b.section_s, b.voie): b for b in bords_route(r, pas)}
        for (ss, v), b in sorted(bs.items()):
            if v == 0:
                continue
            cle = (rid, round(ss, 2), v)
            if cle not in polys:
                manquants.append(cle)
                continue
            A = np.vstack(polys[cle])
            B = np.vstack([np.roll(x, -1, axis=0) for x in polys[cle]])
            bi = bs[(ss, b.voie_int)]
            q = np.vstack([c.xy[(c.s > c.s0 + 0.3) & (c.s < c.s1 - 0.3)] for c in (b, bi)])
            d, _, _ = distance_segments(q, A, B)
            d_all.append(d)
            par_route.setdefault(rid, []).append(d)
    d = np.concatenate(d_all)
    pr = {k: {"n": int(sum(len(x) for x in v)), "p50_m": round(float(np.median(np.concatenate(v))), 4),
              "p95_m": round(float(np.percentile(np.concatenate(v), 95)), 4),
              "max_m": round(float(np.concatenate(v).max()), 4)} for k, v in par_route.items()}
    return {"n_echantillons": int(len(d)), "p50_m": round(float(np.median(d)), 4),
            "p95_m": round(float(np.percentile(d, 95)), 4), "max_m": round(float(d.max()), 4),
            "par_route": pr, "polygones_sans_bord": [], "bords_sans_polygone": [list(c) for c in manquants]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--xodr", default=str(XODR))
    ap.add_argument("--pas", type=float, default=PAS)
    ap.add_argument("--json", help="écrit le rapport de validation")
    a = ap.parse_args()
    reseau = lire_xodr(a.xodr)
    bs = tous_les_bords(reseau, a.pas)
    pas_max = max(float(np.max(np.hypot(*np.diff(b.xy, axis=0).T))) for b in bs if len(b.xy) > 1)
    rap = valider(reseau, a.pas)
    rap["routes"] = len(reseau)
    rap["bords"] = len(bs)
    rap["pas_max_m"] = round(pas_max, 4)
    print(json.dumps({k: v for k, v in rap.items() if k != "par_route"}, ensure_ascii=False))
    for k, v in rap["par_route"].items():
        print(f"  route {k:>4} : {v}")
    if a.json:
        Path(a.json).write_text(json.dumps(rap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
