# -*- coding: utf-8 -*-
"""Lecture des données OSM pour l'inférence OSM → modèle (lot L0, étape 1 de RF-OSM : lecture et Lambert-93).

Formats : `.osm` (XML 0.6, réponse de l'API ou export JOSM), `.osm.pbf` / `.pbf` (décodeur protobuf intégré, sans
dépendance : blocs OSMHeader / OSMData, nœuds simples et denses, ways, relations, compression zlib), GeoJSON
(FeatureCollection : LineString / MultiLineString = ways, Point = nœuds, propriétés = tags OSM ; coordonnées WGS84,
ou Lambert-93 si le membre `crs` nomme EPSG:2154 ou si `crs_l93=True`).

Sortie commune (`DonneesOSM`, dict) :
    {"noeuds": {id: {"xy": (x, y) L93, "tags": {...}}}, "ways": {id: {"noeuds": [ids], "tags": {...}}},
     "relations": {id: {"membres": [(type, ref, role)], "tags": {...}}}, "bornes_l93": (x0, y0, x1, y1) | None,
     "source": {"fichier", "format", "sha256", "octets"}}
Projection : WGS84 → Lambert-93 (EPSG:2154, RGF93 confondu avec WGS84 à mieux que le mètre) par les formules de
la projection conique conforme sécante (IGN, NTG_71 ; GRS80, φ1 = 44°, φ2 = 49°, φ0 = 46,5°, λ0 = 3°, X0 = 700 000,
Y0 = 6 600 000) : fonctions mathématiques seules, résultat identique d'une exécution à l'autre.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

# ---------------------------------------------------------------- projection Lambert-93
_A = 6378137.0
_F = 1 / 298.257222101
_E = math.sqrt(2 * _F - _F * _F)
_PHI1, _PHI2, _PHI0, _LAM0 = map(math.radians, (44.0, 49.0, 46.5, 3.0))
_X0, _Y0 = 700000.0, 6600000.0


def _m(phi):
    return math.cos(phi) / math.sqrt(1 - (_E * math.sin(phi)) ** 2)


def _t(phi):
    es = _E * math.sin(phi)
    return math.tan(math.pi / 4 - phi / 2) / ((1 - es) / (1 + es)) ** (_E / 2)


_N = (math.log(_m(_PHI1)) - math.log(_m(_PHI2))) / (math.log(_t(_PHI1)) - math.log(_t(_PHI2)))
_FF = _m(_PHI1) / (_N * _t(_PHI1) ** _N)
_RHO0 = _A * _FF * _t(_PHI0) ** _N


def wgs84_vers_l93(lon: float, lat: float) -> tuple[float, float]:
    """(lon, lat) en degrés → (X, Y) Lambert-93 en mètres."""
    phi, lam = math.radians(lat), math.radians(lon)
    rho = _A * _FF * _t(phi) ** _N
    th = _N * (lam - _LAM0)
    return _X0 + rho * math.sin(th), _Y0 + _RHO0 - rho * math.cos(th)


# ---------------------------------------------------------------- utilitaires
def _empreinte(p: Path, fmt: str) -> dict:
    o = p.read_bytes()
    return {"fichier": str(p).replace("\\", "/"), "format": fmt, "sha256": hashlib.sha256(o).hexdigest(),
            "octets": len(o)}


def vide() -> dict:
    return {"noeuds": {}, "ways": {}, "relations": {}, "bornes_l93": None, "source": {}}


def _bornes(minlon, minlat, maxlon, maxlat):
    xs, ys = zip(*(wgs84_vers_l93(lo, la) for lo, la in ((minlon, minlat), (maxlon, minlat),
                                                           (maxlon, maxlat), (minlon, maxlat))))
    # rectangle L93 inscrit dans le quadrilatère projeté (les méridiens convergent légèrement)
    return (max(xs[0], xs[3]), max(ys[0], ys[1]), min(xs[1], xs[2]), min(ys[2], ys[3]))


# ---------------------------------------------------------------- XML .osm
def lire_osm_xml(p: Path) -> dict:
    d = vide()
    racine = ET.parse(p).getroot()
    b = racine.find("bounds")
    if b is not None:
        d["bornes_l93"] = _bornes(float(b.get("minlon")), float(b.get("minlat")),
                                  float(b.get("maxlon")), float(b.get("maxlat")))
    for e in racine:
        tags = {t.get("k"): t.get("v") for t in e.findall("tag")}
        if e.tag == "node":
            d["noeuds"][int(e.get("id"))] = {"xy": wgs84_vers_l93(float(e.get("lon")), float(e.get("lat"))), "tags": tags}
        elif e.tag == "way":
            d["ways"][int(e.get("id"))] = {"noeuds": [int(n.get("ref")) for n in e.findall("nd")], "tags": tags}
        elif e.tag == "relation":
            d["relations"][int(e.get("id"))] = {
                "membres": [(m.get("type"), int(m.get("ref")), m.get("role") or "") for m in e.findall("member")],
                "tags": tags}
    d["source"] = _empreinte(p, "osm_xml")
    return d


# ---------------------------------------------------------------- PBF (protobuf minimal)
def _varint(buf, i):
    r = s = 0
    while True:
        b = buf[i]
        i += 1
        r |= (b & 0x7F) << s
        if b < 0x80:
            return r, i
        s += 7


def _zz(n):
    return (n >> 1) ^ -(n & 1)


def _champs(buf):
    """Itère (numéro, type, valeur) d'un message protobuf ; valeur = int (varint) ou bytes (longueur)."""
    i, n = 0, len(buf)
    while i < n:
        cle, i = _varint(buf, i)
        num, typ = cle >> 3, cle & 7
        if typ == 0:
            v, i = _varint(buf, i)
        elif typ == 2:
            ln, i = _varint(buf, i)
            v, i = bytes(buf[i:i + ln]), i + ln
        elif typ == 1:
            v, i = struct.unpack_from("<q", buf, i)[0], i + 8
        elif typ == 5:
            v, i = struct.unpack_from("<i", buf, i)[0], i + 4
        else:
            raise ValueError(f"type protobuf non géré : {typ}")
        yield num, typ, v


def _paquet(buf, signe=False):
    out, i = [], 0
    while i < len(buf):
        v, i = _varint(buf, i)
        out.append(_zz(v) if signe else v)
    return out


def _delta(vals):
    out, acc = [], 0
    for v in vals:
        acc += v
        out.append(acc)
    return out


def lire_pbf(p: Path) -> dict:
    d = vide()
    data = p.read_bytes()
    i = 0
    while i < len(data):
        (lg,) = struct.unpack(">I", data[i:i + 4])
        i += 4
        entete = dict((n, v) for n, _, v in _champs(data[i:i + lg]))
        i += lg
        taille = entete.get(3, 0)
        blob = dict((n, v) for n, _, v in _champs(data[i:i + taille]))
        i += taille
        if 1 in blob:
            brut = blob[1]
        elif 3 in blob:
            brut = zlib.decompress(blob[3])
        else:
            raise ValueError("bloc PBF compressé autrement que par zlib : non géré")
        typ = entete[1].decode()
        if typ == "OSMHeader":
            for n, _, v in _champs(brut):
                if n == 1:  # HeaderBBox en nanodegrés
                    bb = {k: _zz(x) if isinstance(x, int) else x for k, _, x in _champs(v)}
                    d["bornes_l93"] = _bornes(bb[1] * 1e-9, bb[4] * 1e-9, bb[2] * 1e-9, bb[3] * 1e-9)
            continue
        if typ != "OSMData":
            continue
        chaines, groupes, gran, dlat, dlon = [], [], 100, 0, 0
        for n, _, v in _champs(brut):
            if n == 1:
                chaines = [s for k, _, s in _champs(v) if k == 1]
            elif n == 2:
                groupes.append(v)
            elif n == 17:
                gran = v
            elif n == 19:
                dlat = v
            elif n == 20:
                dlon = v
        txt = [s.decode("utf-8") for s in chaines]

        def coord(la, lo):
            return wgs84_vers_l93((dlon + gran * lo) * 1e-9, (dlat + gran * la) * 1e-9)

        for g in groupes:
            for n, _, v in _champs(g):
                if n == 1:  # Node simple
                    f = {}
                    for k, _, x in _champs(v):
                        f.setdefault(k, []).append(x)
                    keys = _paquet(f.get(2, [b""])[0])
                    vals = _paquet(f.get(3, [b""])[0])
                    nid = _zz(f[1][0])
                    d["noeuds"][nid] = {"xy": coord(_zz(f[8][0]), _zz(f[9][0])),
                                        "tags": {txt[a]: txt[b] for a, b in zip(keys, vals)}}
                elif n == 2:  # DenseNodes
                    f = dict((k, x) for k, _, x in _champs(v))
                    ids = _delta(_paquet(f.get(1, b""), True))
                    lats = _delta(_paquet(f.get(8, b""), True))
                    lons = _delta(_paquet(f.get(9, b""), True))
                    kv = _paquet(f.get(10, b""))
                    j = 0
                    for nid, la, lo in zip(ids, lats, lons):
                        tags = {}
                        while j < len(kv) and kv[j] != 0:
                            tags[txt[kv[j]]] = txt[kv[j + 1]]
                            j += 2
                        j += 1
                        d["noeuds"][nid] = {"xy": coord(la, lo), "tags": tags}
                elif n == 3:  # Way
                    f = {}
                    for k, _, x in _champs(v):
                        f.setdefault(k, []).append(x)
                    keys = _paquet(f.get(2, [b""])[0])
                    vals = _paquet(f.get(3, [b""])[0])
                    d["ways"][f[1][0]] = {"noeuds": _delta(_paquet(f.get(8, [b""])[0], True)),
                                          "tags": {txt[a]: txt[b] for a, b in zip(keys, vals)}}
                elif n == 4:  # Relation
                    f = {}
                    for k, _, x in _champs(v):
                        f.setdefault(k, []).append(x)
                    keys = _paquet(f.get(2, [b""])[0])
                    vals = _paquet(f.get(3, [b""])[0])
                    roles = _paquet(f.get(8, [b""])[0])
                    mem = _delta(_paquet(f.get(9, [b""])[0], True))
                    typs = _paquet(f.get(10, [b""])[0])
                    nom = {0: "node", 1: "way", 2: "relation"}
                    d["relations"][f[1][0]] = {
                        "membres": [(nom[t], m, txt[r]) for t, m, r in zip(typs, mem, roles)],
                        "tags": {txt[a]: txt[b] for a, b in zip(keys, vals)}}
    d["source"] = _empreinte(p, "osm_pbf")
    return d


# ---------------------------------------------------------------- GeoJSON
def _id_osm(feat, prefixe):
    for v in (feat.get("properties", {}).get("@id"), feat.get("id"), feat.get("properties", {}).get("osm_id")):
        if v is None:
            continue
        s = str(v)
        if "/" in s:
            t, n = s.split("/", 1)
            if t.startswith(prefixe) and n.lstrip("-").isdigit():
                return int(n)
        elif s.lstrip("-").isdigit():
            return int(s)
    return None


def lire_geojson(p: Path | None = None, objet: dict | None = None, crs_l93: bool | None = None) -> dict:
    """GeoJSON → DonneesOSM. Les nœuds d'extrémité et intermédiaires sont identifiés par leurs coordonnées
    (arrondies au millimètre en L93) : deux lignes qui partagent un sommet partagent le nœud."""
    g = objet if objet is not None else json.loads(Path(p).read_text(encoding="utf-8"))
    if crs_l93 is None:
        crs_l93 = "2154" in json.dumps(g.get("crs", {}))
    d = vide()
    index = {}
    suivant = [-1]

    def noeud(c):
        x, y = (float(c[0]), float(c[1])) if crs_l93 else wgs84_vers_l93(float(c[0]), float(c[1]))
        cle = (round(x, 3), round(y, 3))
        if cle not in index:
            index[cle] = suivant[0]
            d["noeuds"][suivant[0]] = {"xy": (x, y), "tags": {}}
            suivant[0] -= 1
        return index[cle]

    feats = g.get("features", [])
    wid_auto = [-1]
    for f in feats:  # lignes d'abord : les points se rattachent aux sommets existants
        geo = f.get("geometry") or {}
        props = {k: str(v) for k, v in (f.get("properties") or {}).items() if v is not None and not k.startswith("@")}
        if geo.get("type") in ("LineString", "MultiLineString"):
            parties = [geo["coordinates"]] if geo["type"] == "LineString" else geo["coordinates"]
            for k, coords in enumerate(parties):
                wid = _id_osm(f, "way")
                if wid is None or k > 0:
                    wid = wid_auto[0] * 10 ** 9 if wid is None else wid * 1000 + k
                    wid_auto[0] -= 1
                d["ways"][wid] = {"noeuds": [noeud(c) for c in coords], "tags": props}
    for f in feats:
        geo = f.get("geometry") or {}
        if geo.get("type") == "Point":
            props = {k: str(v) for k, v in (f.get("properties") or {}).items() if v is not None and not k.startswith("@")}
            nid = noeud(geo["coordinates"])
            d["noeuds"][nid]["tags"].update(props)
    if p is not None:
        d["source"] = _empreinte(Path(p), "geojson")
    else:
        o = json.dumps(g, sort_keys=True, ensure_ascii=False).encode("utf-8")
        d["source"] = {"fichier": "(objet)", "format": "geojson", "sha256": hashlib.sha256(o).hexdigest(), "octets": len(o)}
    return d


def lire(p, crs_l93: bool | None = None) -> dict:
    p = Path(p)
    nom = p.name.lower()
    if nom.endswith(".pbf"):
        return lire_pbf(p)
    if nom.endswith(".osm") or nom.endswith(".xml"):
        return lire_osm_xml(p)
    if nom.endswith(".geojson") or nom.endswith(".json"):
        return lire_geojson(p, crs_l93=crs_l93)
    raise ValueError(f"format non reconnu : {p}")


# ---------------------------------------------------------------- découpe à l'emprise
def couper_segment(a, b, emprise):
    """Liang-Barsky : (t0, t1) de la partie de [a, b] dans le rectangle, ou None."""
    x0, y0, x1, y1 = emprise
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p_, q_ in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p_ == 0:
            if q_ < 0:
                return None
            continue
        r = q_ / p_
        if p_ < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    return t0, t1


def dedans(pt, emprise):
    x0, y0, x1, y1 = emprise
    return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1
